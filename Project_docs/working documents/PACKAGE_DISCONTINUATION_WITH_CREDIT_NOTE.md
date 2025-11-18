# Package Plan Discontinuation with Credit Note

**Date**: 2025-11-12
**Status**: Implementation In Progress
**Version**: 1.0

---

## Business Requirements

### Overview
When a package payment plan is discontinued, the system must:
1. Cancel remaining sessions and installments
2. Calculate refund/adjustment amount (user-editable)
3. Create credit note against original invoice
4. Reverse AR liability (if payment not made) OR process refund (if payment made)
5. Post GL entries to reflect the adjustment

### Key Principles
- **Liability should only reflect sessions actually delivered**
- **If payment made for future sessions, refund must be processed**
- **User can adjust the calculated refund amount** (e.g., deduct cancellation fee)
- **All financial adjustments must be posted to AR and GL**

---

## Financial Scenarios

### Scenario 1: No Payment Made (Liability Reduction)
```
Original Invoice: SVC/2025-2026/00005
Amount: ₹5,900.00 for 6 sessions
Completed Sessions: 2
Remaining Sessions: 4
Per Session Value: ₹983.33

Original AR Entry:
  Dr: AR (1100) ₹5,900
  Cr: Package Revenue (4200) ₹5,900
  [Patient owes ₹5,900]

When Discontinued:
→ System calculates adjustment: ₹3,933.33 (4 unused sessions)
→ User can adjust amount (e.g., ₹3,500 if cancellation fee applies)
→ User confirms adjustment: ₹3,933.33

Credit Note GL Entries:
  Dr: Package Revenue (4200) ₹3,933.33  // Reduce income
  Cr: AR (1100) ₹3,933.33                // Reduce receivable

AR Subledger Entry:
  Entry Type: credit_note
  Reference: Credit Note Number
  Credit Amount: ₹3,933.33
  Current Balance: ₹1,966.67 (only for 2 completed sessions)

Net Effect:
  AR Balance: ₹1,966.67 (reduced from ₹5,900)
  Revenue: ₹1,966.67 (reduced from ₹5,900)
  Patient Liability: ₹1,966.67 (for sessions actually received)
```

### Scenario 2: Full Payment Made (Refund Due)
```
Original Invoice: SVC/2025-2026/00006
Amount: ₹5,900.00 for 6 sessions
Completed Sessions: 2
Remaining Sessions: 4
Paid Amount: ₹5,900 (full advance payment)
Per Session Value: ₹983.33

Original Entries:
  Invoice Creation:
    Dr: AR (1100) ₹5,900
    Cr: Package Revenue (4200) ₹5,900

  Payment Receipt:
    Dr: Cash/Bank (1100/1200) ₹5,900
    Cr: AR (1100) ₹5,900

  Net AR Balance: ₹0 (fully paid)

When Discontinued:
→ System calculates refund: ₹3,933.33 (4 unused sessions)
→ User adjusts refund: ₹3,500 (₹433.33 cancellation fee)
→ User confirms refund: ₹3,500

Credit Note GL Entries:
  Dr: Credit Note Adjustments (5999) ₹3,500  // Expense for credit note/refund
  Cr: Cash/Bank (1100/1200) ₹3,500           // Refund payment to patient

OR alternatively:
  Dr: Package Revenue (4200) ₹3,500  // Reduce revenue
  Cr: Cash/Bank (1100/1200) ₹3,500   // Refund payment

Net Effect:
  Cash/Bank: Reduced by ₹3,500 (refund paid)
  Revenue OR Expense: Adjusted by ₹3,500
  Net Revenue: ₹2,400 (₹5,900 - ₹3,500) for 2 completed sessions
```

---

## GL Account Mapping

### Key Accounts Used:
- **1100** - Accounts Receivable (Asset)
- **1100** - Cash (Asset)
- **1200** - Bank Account (Asset)
- **4200** - Package Revenue (Income)
- **5999** - Credit Note Adjustments (Expense)

### Posting Rules:
1. **For unpaid invoices**: Reduce AR and Revenue
2. **For paid invoices**: Create refund expense and reduce Cash/Bank
3. **All entries must balance** (Total Debits = Total Credits)
4. **Credit Note must reference original invoice**

---

## UI/UX Workflow

### Step 1: User Initiates Discontinuation
- Navigate to Package Plan
- Click "Edit"
- Change Status to "Discontinued"
- Enter "Discontinuation Reason" (required text field)
- Click "Save"

### Step 2: System Shows Confirmation Modal
**Modal Title**: ⚠️ Confirm Plan Discontinuation

**Modal Content**:
```
Patient: [Patient Name]
Package: [Package Name]
Invoice: SVC/2025-2026/00005 (₹5,900.00)

═══════════════════════════════════════════════════
SESSION SUMMARY
═══════════════════════════════════════════════════
Total Sessions:           6
Completed Sessions:       2
Remaining Sessions:       4
Per Session Value:        ₹983.33

═══════════════════════════════════════════════════
FINANCIAL IMPACT
═══════════════════════════════════════════════════
Invoice Amount:           ₹5,900.00
Amount for Completed:     ₹1,966.67 (2 sessions)
Amount for Unused:        ₹3,933.33 (4 sessions)

Amount Paid:              ₹0.00
Amount Outstanding:       ₹5,900.00

═══════════════════════════════════════════════════
ADJUSTMENTS
═══════════════════════════════════════════════════
[✓] Cancel 4 scheduled sessions
[✓] Cancel 3 pending installments
[✓] Reduce AR liability by calculated amount
[✓] Create credit note against invoice
[✓] Post GL entries

═══════════════════════════════════════════════════
CREDIT NOTE AMOUNT
═══════════════════════════════════════════════════
Calculated Amount:        ₹3,933.33
                          ↓
Adjustment Amount:        [₹3,933.33] ← User can edit
                          ↑
                          (Edit to deduct cancellation fee, etc.)

Reason for Discontinuation:
[Patient requested cancellation due to relocation]

[Cancel] [Confirm & Create Credit Note]
```

### Step 3: System Processes Discontinuation
1. Update plan status to 'discontinued'
2. Cancel all scheduled sessions (session_status = 'cancelled')
3. Cancel all pending installments (status = 'cancelled')
4. Create credit note record
5. Post AR entries (credit AR by adjustment amount)
6. Post GL entries (reduce revenue and receivable)
7. Update plan with discontinuation tracking fields

### Step 4: Show Success Message
```
✅ Plan Discontinued Successfully

Credit Note: CN/2025-2026/00001 created for ₹3,933.33
AR Liability reduced from ₹5,900.00 to ₹1,966.67
GL entries posted successfully

4 sessions cancelled | 3 installments cancelled
```

---

## Database Schema

### Credit Note Table (NEW - needs creation)
```sql
CREATE TABLE patient_credit_notes (
    credit_note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),

    -- References
    credit_note_number VARCHAR(50) NOT NULL UNIQUE,
    original_invoice_id UUID NOT NULL REFERENCES invoice_header(invoice_id),
    plan_id UUID REFERENCES package_payment_plans(plan_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Amounts
    credit_note_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount NUMERIC(12,2) NOT NULL,

    -- Reason
    reason_code VARCHAR(20),  -- 'plan_discontinued', 'service_not_provided', 'overcharge', etc.
    reason_description TEXT,

    -- GL Posting
    gl_posted BOOLEAN DEFAULT FALSE,
    gl_transaction_id UUID REFERENCES gl_transaction(transaction_id),
    posted_at TIMESTAMP WITH TIME ZONE,
    posted_by VARCHAR(15),

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft, approved, posted, cancelled
    approved_by VARCHAR(15) REFERENCES users(user_id),
    approved_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(15),

    CONSTRAINT valid_credit_note_status CHECK (status IN ('draft', 'approved', 'posted', 'cancelled'))
);

CREATE INDEX idx_credit_note_invoice ON patient_credit_notes(original_invoice_id);
CREATE INDEX idx_credit_note_plan ON patient_credit_notes(plan_id);
CREATE INDEX idx_credit_note_patient ON patient_credit_notes(patient_id);
CREATE INDEX idx_credit_note_number ON patient_credit_notes(credit_note_number);
```

### Package Plan - Discontinuation Fields (ALREADY ADDED)
```sql
ALTER TABLE package_payment_plans
ADD COLUMN IF NOT EXISTS discontinued_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS discontinued_by VARCHAR(15) REFERENCES users(user_id),
ADD COLUMN IF NOT EXISTS discontinuation_reason TEXT,
ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS refund_status VARCHAR(20) DEFAULT 'none',
ADD COLUMN IF NOT EXISTS credit_note_id UUID REFERENCES patient_credit_notes(credit_note_id);
```

---

## API Endpoints

### 1. GET /api/package/plan/<plan_id>/discontinuation-preview
**Purpose**: Calculate discontinuation impact before confirmation
**Response**:
```json
{
  "success": true,
  "plan_id": "uuid",
  "patient_name": "John Doe",
  "package_name": "Laser Hair Reduction",
  "invoice": {
    "invoice_id": "uuid",
    "invoice_number": "SVC/2025-2026/00005",
    "total_amount": 5900.00
  },
  "sessions": {
    "total": 6,
    "completed": 2,
    "remaining": 4,
    "per_session_value": 983.33
  },
  "installments": {
    "total": 3,
    "paid": 0,
    "pending": 3,
    "pending_amount": 5900.00
  },
  "financial": {
    "invoice_amount": 5900.00,
    "paid_amount": 0.00,
    "outstanding_amount": 5900.00,
    "amount_for_completed": 1966.67,
    "amount_for_unused": 3933.33,
    "calculated_adjustment": 3933.33,
    "requires_refund": false
  },
  "actions": {
    "sessions_to_cancel": 4,
    "installments_to_cancel": 3,
    "ar_adjustment": 3933.33,
    "gl_posting_required": true
  }
}
```

### 2. POST /api/package/plan/<plan_id>/discontinue
**Purpose**: Process discontinuation with user-adjusted amount
**Request**:
```json
{
  "discontinuation_reason": "Patient requested cancellation",
  "adjustment_amount": 3933.33,
  "create_credit_note": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Plan discontinued successfully",
  "credit_note": {
    "credit_note_id": "uuid",
    "credit_note_number": "CN/2025-2026/00001",
    "amount": 3933.33,
    "status": "posted"
  },
  "ar_entry": {
    "entry_id": "uuid",
    "credit_amount": 3933.33,
    "new_balance": 1966.67
  },
  "gl_transaction": {
    "transaction_id": "uuid",
    "total_debit": 3933.33,
    "total_credit": 3933.33,
    "posted": true
  },
  "plan_updates": {
    "status": "discontinued",
    "sessions_cancelled": 4,
    "installments_cancelled": 3
  }
}
```

---

## Implementation Tasks

### Phase 1: Database & API (Priority 1)
- [x] Add discontinuation tracking fields to package_payment_plans
- [ ] Create patient_credit_notes table
- [ ] Create API endpoint: GET /discontinuation-preview
- [ ] Create API endpoint: POST /discontinue
- [ ] Add credit note service methods

### Phase 2: Service Layer (Priority 1)
- [x] Implement discontinuation calculation logic
- [ ] Implement AR reversal/adjustment logic
- [ ] Implement GL posting for credit notes
- [ ] Implement credit note creation
- [ ] Update discontinuation handler to accept user amount

### Phase 3: UI/UX (Priority 1)
- [ ] Add discontinuation confirmation modal to edit form
- [ ] Add editable adjustment amount field
- [ ] Add preview of financial impact
- [ ] Add success/error handling

### Phase 4: Testing (Priority 1)
- [ ] Test Scenario 1: No payment made
- [ ] Test Scenario 2: Full payment made
- [ ] Test Scenario 3: Partial payment made
- [ ] Test GL entries validation
- [ ] Test AR subledger updates

---

## Next Action
Create patient_credit_notes table and begin API endpoint implementation.

**Estimated Completion**: 6-8 hours for full implementation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Maintained By**: Development Team
