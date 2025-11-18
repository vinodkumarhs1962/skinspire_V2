# Rollback Behavior Analysis: Triggers vs Event Listeners

## The Question

When a database transaction is rolled back, what happens to audit fields set by:
1. Database triggers?
2. SQLAlchemy event listeners?

---

## Short Answer

**Both handle rollback IDENTICALLY - they're part of the same transaction.**

But there are important nuances to understand...

---

## How Database Transactions Work

```
BEGIN TRANSACTION
  ↓
  INSERT/UPDATE operation
  ↓
  Trigger fires (sets audit fields)
  ↓
  Event listener fires (sets audit fields)
  ↓
COMMIT or ROLLBACK?
```

**On COMMIT:**
- All changes are saved (data + audit fields)
- Both trigger and event listener changes persist

**On ROLLBACK:**
- ALL changes are discarded (data + audit fields)
- Both trigger and event listener changes are lost

---

## Detailed Analysis

### Scenario 1: Simple Rollback

```python
with get_db_session() as session:
    # Event listener sets created_by='7777777777'
    invoice = InvoiceHeader(...)
    session.add(invoice)
    session.flush()  # Trigger fires here

    # Something goes wrong
    raise Exception("Payment failed!")

    # session.rollback() called automatically
```

**What happens:**
1. Event listener sets `created_by='7777777777'` on Python object
2. Flush sends INSERT to database
3. Trigger sets `created_by='7777777777'` (or validates existing)
4. Exception raised
5. **ROLLBACK** - entire transaction discarded
6. Invoice NOT created
7. Audit fields NOT saved

**Result:** ✅ BOTH rolled back correctly - no orphaned audit data

---

### Scenario 2: Partial Commit (SAVEPOINT)

```python
with get_db_session() as session:
    # Create invoice (works)
    invoice = InvoiceHeader(...)
    session.add(invoice)
    session.flush()  # Committed to DB

    # Create payment (works)
    payment = PaymentDetail(...)
    session.add(payment)
    session.flush()  # Committed to DB

    # Create AR entry (fails)
    ar_entry = ARSubledger(...)
    session.add(ar_entry)
    session.flush()  # FAILS - foreign key violation

    session.rollback()  # Rolls back EVERYTHING
```

**What happens:**
- Event listeners set audit fields on all three objects
- Triggers fire on first two successful flushes
- Third flush fails
- **ROLLBACK discards ALL changes** (invoice, payment, AR)
- Audit fields from all three are lost

**Result:** ✅ BOTH rolled back correctly - transaction atomicity maintained

---

### Scenario 3: Nested Transaction with SAVEPOINT

```python
with get_db_session() as session:
    # Create invoice
    invoice = InvoiceHeader(...)
    session.add(invoice)
    session.flush()

    # SAVEPOINT
    savepoint = session.begin_nested()

    try:
        # Try to create payment
        payment = PaymentDetail(...)
        session.add(payment)
        session.flush()
        savepoint.commit()  # Payment saved
    except:
        savepoint.rollback()  # Only payment rolled back

    session.commit()  # Invoice still committed
```

**What happens:**
- Invoice: Event listener + trigger set audit fields → COMMITTED
- Payment (if successful): Event listener + trigger set audit fields → COMMITTED
- Payment (if failed): Event listener + trigger set audit fields → ROLLED BACK

**Result:** ✅ BOTH handle nested transactions correctly

---

## Key Differences in Rollback Behavior

### Database Triggers

**Timing:**
- Fire DURING transaction (BEFORE/AFTER INSERT/UPDATE)
- Changes are part of the same transaction
- Rolled back with the transaction

**Visibility:**
```python
ar_entry = ARSubledger(...)
session.add(ar_entry)
session.flush()  # Trigger fires NOW

# Python object doesn't see trigger's changes yet!
print(ar_entry.created_by)  # Still None or old value in Python

session.refresh(ar_entry)  # Fetch from DB
print(ar_entry.created_by)  # NOW shows trigger's value

session.rollback()  # Trigger's changes lost
```

**Issue:** Python object and database can be out of sync until refresh.

---

### SQLAlchemy Event Listeners

**Timing:**
- Fire BEFORE data sent to database
- Changes made to Python object FIRST
- Then sent to database as part of INSERT/UPDATE

**Visibility:**
```python
ar_entry = ARSubledger(...)
session.add(ar_entry)
# Event listener fires BEFORE flush

print(ar_entry.created_by)  # Shows '7777777777' immediately

session.flush()  # Now sent to database

session.rollback()  # Changes lost from DB
print(ar_entry.created_by)  # Still shows '7777777777' in Python!
```

**Issue:** After rollback, Python object still has values that weren't committed.

---

## Rollback Gotchas

### Gotcha 1: Stale Python Objects (Event Listeners)

```python
with get_db_session() as session:
    ar_entry = ARSubledger(...)
    session.add(ar_entry)
    # Event listener sets created_by='7777777777'

    session.flush()
    session.rollback()

    # ar_entry is now DETACHED from session
    # But it still has created_by='7777777777' in memory!
    print(ar_entry.created_by)  # '7777777777' (WRONG - was rolled back!)
```

**Solution:** Don't use objects after rollback. SQLAlchemy marks them as detached.

---

### Gotcha 2: No Visibility of Trigger Changes (Triggers)

```python
with get_db_session() as session:
    ar_entry = ARSubledger(...)
    # Intentionally NOT setting created_by

    session.add(ar_entry)
    session.flush()
    # Trigger sets created_by='system'

    # But Python object doesn't know!
    print(ar_entry.created_by)  # None

    session.refresh(ar_entry)  # Must refresh
    print(ar_entry.created_by)  # 'system'
```

**Solution:** Use RETURNING clause or refresh after flush.

---

## Transaction Isolation Levels

Both mechanisms respect transaction isolation:

```python
# Session 1
session1.add(invoice)
session1.flush()  # Audit fields set (trigger or event)
# NOT YET COMMITTED

# Session 2 (different connection)
invoice = session2.query(InvoiceHeader).filter_by(invoice_id=...).first()
# Returns None - not committed yet

# Session 1
session1.commit()  # NOW visible to session2
```

**Result:** ✅ Both mechanisms respect ACID properties

---

## Complex Rollback Scenarios

### Scenario: Multi-Table Transaction Failure

```python
try:
    with get_db_session() as session:
        # Step 1: Create invoice (succeeds)
        invoice = InvoiceHeader(...)
        session.add(invoice)
        session.flush()
        # Audit: created_by='7777777777', created_at=NOW

        # Step 2: Create line items (succeeds)
        for item in items:
            line_item = InvoiceLineItem(...)
            session.add(line_item)
        session.flush()
        # Audit: created_by='7777777777', created_at=NOW

        # Step 3: Create AR entries (succeeds)
        for line_item in line_items:
            ar_entry = ARSubledger(...)
            session.add(ar_entry)
        session.flush()
        # Audit: created_by='7777777777', created_at=NOW

        # Step 4: Create GL transaction (FAILS - duplicate entry)
        gl_transaction = GLTransaction(...)
        session.add(gl_transaction)
        session.flush()  # RAISES EXCEPTION

        session.commit()  # Never reached

except Exception as e:
    # Automatic rollback
    # ALL changes lost:
    # - Invoice (not saved)
    # - Line items (not saved)
    # - AR entries (not saved)
    # - All audit fields (not saved)
    pass
```

**Result with Event Listeners:**
- ✅ All audit fields set correctly before rollback
- ✅ Transaction atomicity maintained
- ✅ No orphaned audit data
- ⚠️ Python objects still have audit values (but detached)

**Result with Triggers:**
- ✅ All audit fields set correctly before rollback
- ✅ Transaction atomicity maintained
- ✅ No orphaned audit data
- ⚠️ Python objects don't reflect trigger changes (needs refresh)

**Winner:** TIE - Both handle rollback correctly

---

## Edge Case: Background Thread Rollback

```python
# Main thread
def create_invoice():
    with get_db_session() as session:
        invoice = InvoiceHeader(...)
        session.add(invoice)
        session.commit()  # COMMITTED

        # Spawn background thread
        thread = Thread(target=create_payment, args=(invoice.invoice_id,))
        thread.start()

# Background thread
def create_payment(invoice_id):
    with get_db_session() as session:  # NEW session
        payment = PaymentDetail(invoice_id=invoice_id, ...)
        session.add(payment)
        session.flush()
        # Audit fields set

        # Something fails
        raise Exception()
        # Automatic rollback
```

**Result:**
- Invoice: ✅ Committed (with audit fields)
- Payment: ✅ Rolled back (audit fields lost)
- No data corruption

**Winner:** TIE - Both handle correctly

---

## Comparison Summary

| Aspect | Event Listeners | Triggers | Winner |
|--------|----------------|----------|--------|
| Transaction rollback | ✅ Rolled back | ✅ Rolled back | **TIE** |
| Nested transactions | ✅ Works | ✅ Works | **TIE** |
| Multi-table rollback | ✅ Atomic | ✅ Atomic | **TIE** |
| ACID compliance | ✅ Yes | ✅ Yes | **TIE** |
| Python object state | ⚠️ Stale after rollback | ✅ Detached (safe) | **TRIGGERS** |
| Visibility of audit values | ✅ Immediate | ⚠️ Needs refresh | **EVENT LISTENERS** |
| Cross-session isolation | ✅ Correct | ✅ Correct | **TIE** |
| Savepoint support | ✅ Yes | ✅ Yes | **TIE** |

---

## Practical Example: Payment Processing with Rollback

```python
def process_payment(invoice_id, amount):
    """
    Payment processing with proper rollback handling
    """
    try:
        with get_db_session() as session:
            # 1. Get invoice
            invoice = session.query(InvoiceHeader).filter_by(
                invoice_id=invoice_id
            ).first()

            # 2. Create payment
            payment = PaymentDetail(
                invoice_id=invoice_id,
                amount=amount
            )
            session.add(payment)
            session.flush()
            # Audit: created_by set by event listener OR trigger

            # 3. Create AR entries (line-item level)
            for line_item in invoice.line_items:
                ar_entry = ARSubledger(
                    reference_id=payment.payment_id,
                    reference_line_item_id=line_item.line_item_id,
                    credit_amount=allocated_amount
                )
                session.add(ar_entry)
            session.flush()
            # Audit: created_by set for each AR entry

            # 4. Create GL transaction
            gl_transaction = create_gl_transaction(session, payment)
            session.flush()
            # Audit: created_by set for GL entries

            # 5. Update invoice status
            invoice.payment_status = 'paid'
            session.flush()
            # Audit: updated_by set by event listener OR trigger

            # COMMIT - All or nothing
            session.commit()

            logger.info(f"Payment processed: {payment.payment_id}")
            return {"success": True, "payment_id": payment.payment_id}

    except Exception as e:
        # ROLLBACK - All changes discarded
        logger.error(f"Payment processing failed: {e}")
        # payment NOT saved
        # AR entries NOT saved
        # GL transaction NOT saved
        # Invoice status NOT updated
        # All audit fields NOT saved
        return {"success": False, "error": str(e)}
```

**With Event Listeners:**
- ✅ Audit fields set immediately
- ✅ Visible in Python objects
- ✅ Rolled back atomically on failure
- ⚠️ After rollback, objects still have audit values (but detached)

**With Triggers:**
- ✅ Audit fields set at database level
- ⚠️ Not visible in Python until refresh
- ✅ Rolled back atomically on failure
- ✅ Python objects properly detached

---

## The Verdict

### For Rollback Handling: **TRIGGERS ARE SLIGHTLY BETTER**

**Why:**
1. **Cleaner object state** after rollback (objects detached, no stale values)
2. **Database-level atomicity** (more explicit)
3. **No confusion** about what's committed vs what's in memory

**However:**
The difference is MINIMAL because:
- Both are part of the same transaction
- Both rolled back atomically
- Both maintain ACID properties
- Both work correctly in practice

---

## Best Practice Recommendation

**Use BOTH (for defense-in-depth), but rely on TRIGGERS for critical audit:**

```python
# Event listener sets audit fields (convenience)
# ALSO sets session variable for trigger
@event.listens_for(TimestampMixin, 'before_insert', propagate=True)
def set_audit_fields(mapper, connection, target):
    user_id = get_current_user_id()
    target.created_by = user_id
    target.updated_by = user_id

    # Set session variable for trigger (safety net)
    connection.execute(text(f"SET LOCAL app.current_user = '{user_id}'"))
```

**Benefits:**
- ✅ Event listener provides convenience + visibility
- ✅ Trigger provides safety net if event fails
- ✅ Both rolled back atomically
- ✅ Best of both worlds

**After rollback:**
- Discard Python objects (don't reuse)
- Trigger ensures no orphaned audit data
- Transaction atomicity maintained

---

## Answer to Your Question

> "Which can handle rollback better?"

**Answer: BOTH handle rollback identically (both part of same transaction), but TRIGGERS are slightly cleaner because:**

1. ✅ **No stale object state** - Python objects properly detached
2. ✅ **Database-level enforcement** - more explicit atomicity
3. ✅ **Works for ALL rollback scenarios** (ORM, raw SQL, migrations)

**However, for healthcare applications, use BOTH:**
- Triggers = PRIMARY (compliance, safety net)
- Event Listeners = SECONDARY (convenience, better UX)

Both rolled back atomically, no data corruption possible.
