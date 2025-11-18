# Package Discontinuation - Next Session Implementation

**Status**: Database and models complete, service layer needed
**Priority**: HIGH - Core revenue management feature
**Estimated Time**: 4-6 hours

---

## ✅ Already Completed

1. **Database**:
   - `patient_credit_notes` table created
   - `credit_note_id` added to `package_payment_plans`
   - All indexes and constraints in place

2. **Models**:
   - `PatientCreditNote` model created in `transaction.py`
   - Relationships configured
   - All fields mapped

3. **Documentation**:
   - Complete business logic documented
   - GL account mapping defined
   - UI/UX flow designed

---

## 🎯 Implementation Checklist (Next Session)

### Step 1: Patient Credit Note Service (2-3 hours)
**File**: `app/services/patient_credit_note_service.py` (NEW)

Use `app/services/credit_note_service.py` (supplier) as reference - it has:
- Credit note number generation
- AR/GL posting logic
- Transaction management

**Required Functions**:
```python
class PatientCreditNoteService:
    def generate_credit_note_number(hospital_id, branch_id) -> str
    def create_patient_credit_note(invoice_id, amount, reason, plan_id) -> Dict
    def post_ar_entry(credit_note) -> Dict  # Credit AR
    def post_gl_entries(credit_note) -> Dict  # Dr: Revenue, Cr: AR
```

**GL Posting**:
```
Dr: Package Revenue (4200) ₹amount
Cr: Accounts Receivable (1100) ₹amount
```

**AR Entry**:
```
Entry Type: credit_note
Credit Amount: ₹amount (reduce receivable)
```

---

### Step 2: Update Discontinuation Handler (1 hour)
**File**: `app/services/package_payment_service.py`

Update `_handle_discontinuation()` method:

```python
def _handle_discontinuation(..., user_adjusted_amount: Decimal):
    # ... existing code ...

    # NEW: Create credit note
    from app.services.patient_credit_note_service import PatientCreditNoteService
    cn_service = PatientCreditNoteService()

    credit_note_result = cn_service.create_patient_credit_note(
        hospital_id=hospital_id,
        original_invoice_id=plan.invoice_id,
        patient_id=plan.patient_id,
        plan_id=plan.plan_id,
        total_amount=user_adjusted_amount,  # USER CAN EDIT THIS
        reason_code='plan_discontinued',
        reason_description=discontinuation_reason
    )

    if credit_note_result['success']:
        plan.credit_note_id = credit_note_result['credit_note_id']
        logger.info(f"✅ Credit note created: {credit_note_result['credit_note_number']}")
```

---

### Step 3: API Endpoints (1-2 hours)
**File**: `app/api/routes/package_api.py`

**Endpoint 1: Preview Discontinuation**
```python
@package_api_bp.route('/plan/<plan_id>/discontinuation-preview', methods=['GET'])
def preview_discontinuation(plan_id):
    """
    Calculate discontinuation impact before user confirms

    Returns:
      - Sessions to cancel
      - Installments to cancel
      - Calculated adjustment amount
      - Invoice details
    """
```

**Endpoint 2: Process Discontinuation**
```python
@package_api_bp.route('/plan/<plan_id>/discontinue', methods=['POST'])
def discontinue_plan(plan_id):
    """
    Process discontinuation with user-adjusted amount

    Request Body:
    {
        "discontinuation_reason": "...",
        "adjustment_amount": 3933.33  // User can edit this
    }

    Returns:
      - Credit note details
      - AR entry ID
      - GL transaction ID
      - Sessions/installments cancelled
    """
```

---

### Step 4: UI - Confirmation Modal (1-2 hours)
**File**: `app/templates/engine/universal_edit.html`

Add JavaScript to intercept form submit when status = "discontinued":

```javascript
// Check if status changed to discontinued
if (statusField.value === 'discontinued') {
    event.preventDefault();

    // Call preview API
    fetch(`/api/package/plan/${planId}/discontinuation-preview`)
        .then(response => response.json())
        .then(data => {
            // Show modal with editable amount
            showDiscontinuationModal(data);
        });
}

function showDiscontinuationModal(data) {
    // Display modal with:
    // - Session summary
    // - Financial impact
    // - EDITABLE adjustment amount field
    // - Confirm / Cancel buttons
}

function confirmDiscontinuation() {
    const adjustedAmount = document.getElementById('adjustment_amount').value;
    const reason = document.getElementById('discontinuation_reason').value;

    fetch(`/api/package/plan/${planId}/discontinue`, {
        method: 'POST',
        body: JSON.stringify({
            discontinuation_reason: reason,
            adjustment_amount: parseFloat(adjustedAmount)
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showSuccess(result.message);
            redirectToDetailView();
        }
    });
}
```

---

## 🔍 Reference Implementation

**Supplier Credit Notes** (already implemented):
- File: `app/services/credit_note_service.py`
- Has complete GL posting logic
- Has AP subledger entries
- Use as template for patient credit notes

**Key Differences**:
| Aspect | Supplier | Patient |
|--------|----------|---------|
| Subledger | AP | AR |
| Liability Direction | Reduce AP (Debit) | Reduce AR (Credit) |
| GL Entry | Dr: AP, Cr: Expense | Dr: Revenue, Cr: AR |
| Account No | 2001 (AP) | 1100 (AR), 4200 (Revenue) |

---

## 🧪 Testing Checklist

Once implemented, test:

1. **No Payment Made**:
   - Discontinue plan with 2/6 sessions completed
   - Verify AR reduced by 4 sessions' value
   - Verify GL entries posted correctly
   - Verify credit note created

2. **Full Payment Made**:
   - Discontinue plan that was paid in full
   - Verify refund amount calculated
   - User adjusts amount (deduct cancellation fee)
   - Verify GL and AR entries

3. **Edge Cases**:
   - Plan with no invoice (should fail)
   - Plan already discontinued (should fail)
   - Zero sessions completed (full credit)

---

## 📂 Files to Create/Modify

**New Files**:
- [ ] `app/services/patient_credit_note_service.py` - Complete service

**Modified Files**:
- [ ] `app/services/package_payment_service.py` - Update _handle_discontinuation()
- [ ] `app/api/routes/package_api.py` - Add 2 endpoints
- [ ] `app/templates/engine/universal_edit.html` - Add modal + JavaScript

**Configuration**:
- [ ] `app/config/modules/package_payment_plan_config.py` - Add credit_note_id field

---

## 💡 Quick Win Approach

If time is limited, implement in this order:

**Phase A** (2 hours - Core functionality):
1. Patient credit note service (basic)
2. Update discontinuation handler to create credit note
3. Test with direct API calls

**Phase B** (2 hours - UI polish):
4. Add preview endpoint
5. Add confirmation modal
6. Test end-to-end workflow

---

## 🚀 Ready to Start

When you begin next session:

1. **Read**: `app/services/credit_note_service.py` (supplier version)
2. **Create**: `app/services/patient_credit_note_service.py` (adapt for patients)
3. **Update**: `_handle_discontinuation()` method
4. **Test**: Create credit note via discontinuation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Time Invested Today**: ~3 hours (database, models, documentation)
**Remaining Work**: ~4-6 hours (service, API, UI)
