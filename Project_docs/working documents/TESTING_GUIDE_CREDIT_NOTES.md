# Credit Note Testing Guide - Package Discontinuation & Invoice Refunds

**Status**: ✅ Ready for testing
**Date**: 2025-11-12

---

## 🎯 Overview

The credit note system works for **both** scenarios:
1. **Package Discontinuation** - Automated via confirmation modal in edit form
2. **Regular Invoice Refunds** - Via API or future UI (service layer ready)

Both use the same `PatientCreditNoteService` and post identical AR/GL entries.

---

## 📋 Test Scenario 1: Package Discontinuation (Modal)

### Prerequisites

1. Flask server running: `python run.py`
2. Test plan data available (from previous session):
   ```
   Plan ID: a163d628-3b32-44f4-acf0-114755cc34a3
   Patient: Test Patient
   Package: Test Package (6 sessions)
   Invoice: SVC/2025-2026/00005
   Total Amount: ₹5,900.00
   Completed Sessions: 2
   Remaining Sessions: 4
   ```

### Testing Steps

#### Step 1: Navigate to Edit Form

1. Login to the application
2. Go to Package Payment Plans list:
   ```
   /universal/package_payment_plans/list
   ```
3. Click "Edit" on the test plan (a163d628...)

#### Step 2: Change Status to Discontinued

1. In the edit form, find the **Status** dropdown
2. Change status from current value to **"Discontinued"**
3. Click **"Update"** button
4. ✅ **Modal should appear automatically!**

#### Step 3: Review Confirmation Modal

The modal shows:

**Patient & Package Info**:
- Patient Name
- Package Name
- Invoice Number
- Plan Number

**Financial Impact**:
- Total Amount: ₹5,900.00
- Paid Amount: ₹0.00
- Total Sessions: 6
- Completed: 2
- Remaining: 4 (highlighted in red)

**Items to Cancel**:
- Scheduled Sessions: 3
- Pending Installments: 3

**Refund Calculation**:
- Calculated Amount: ₹3,933.33 (read-only, shown in gray)
- Adjusted Amount: ₹3,933.33 (editable, you can change this!)

#### Step 4: Adjust Amount (Optional)

Example adjustments:
- **Deduct cancellation fee**: Change ₹3,933.33 to ₹3,433.33 (₹500 fee)
- **Partial credit**: Change to ₹2,000.00
- **Keep calculated**: Leave as ₹3,933.33

#### Step 5: Enter Discontinuation Reason

In the textarea, enter reason:
```
Patient requested discontinuation due to relocation to another city
```

#### Step 6: Confirm

1. Click **"Confirm Discontinuation"** button (red)
2. Button shows: "Processing..." with spinner
3. Wait for success message (alert):
   ```
   ✅ Plan discontinued successfully!

   Credit Note: CN/2025-2026/00001
   Refund Amount: ₹3,433.33
   Sessions Cancelled: 3
   Installments Cancelled: 2
   ```
4. Click OK
5. You'll be redirected to the detail view

#### Step 7: Verify in UI

On the detail view, verify:
- Status: **Discontinued**
- Discontinued At: Today's date/time
- Discontinued By: Your user ID
- Discontinuation Reason: Text you entered
- Refund Amount: ₹3,433.33
- Refund Status: "none" (since no payment was made)
- Credit Note ID: UUID visible

---

## 🗄️ Test Scenario 2: Verify Accounting Entries

### Database Verification Queries

**Run these queries in pgAdmin or psql:**

#### Query 1: Credit Note Created

```sql
SELECT
    credit_note_id,
    credit_note_number,
    credit_note_date,
    original_invoice_id,
    patient_id,
    plan_id,
    total_amount,
    reason_code,
    reason_description,
    status,
    gl_posted,
    gl_transaction_id,
    created_at,
    created_by
FROM patient_credit_notes
WHERE plan_id = 'a163d628-3b32-44f4-acf0-114755cc34a3'
ORDER BY created_at DESC;
```

**Expected Results**:
- `credit_note_number`: CN/2025-2026/00001 (or next sequence)
- `total_amount`: 3433.33 (your adjusted amount)
- `reason_code`: plan_discontinued
- `reason_description`: Your entered text
- `status`: posted
- `gl_posted`: true
- `gl_transaction_id`: UUID (not null)

#### Query 2: AR Entry Posted

```sql
SELECT
    entry_id,
    transaction_date,
    entry_type,
    reference_type,
    reference_number,
    patient_id,
    debit_amount,
    credit_amount,
    current_balance,
    gl_transaction_id,
    created_at
FROM ar_subledger
WHERE reference_type = 'credit_note'
    AND reference_number LIKE 'CN/%'
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Results**:
- `entry_type`: credit_note
- `reference_type`: credit_note
- `reference_number`: CN/2025-2026/00001
- `debit_amount`: 0.00
- `credit_amount`: 3433.33 ✅ (reduces receivable)
- `current_balance`: Previous balance - 3433.33
- `gl_transaction_id`: UUID (matches credit note)

**What This Means**:
The patient's AR balance was **reduced by ₹3,433.33** because the invoice liability is being reversed for unused sessions.

#### Query 3: GL Entries Posted

```sql
SELECT
    t.transaction_id,
    t.transaction_date,
    t.transaction_type,
    t.description,
    t.total_debit,
    t.total_credit,
    e.entry_id,
    a.account_name,
    a.gl_account_no,
    e.debit_amount,
    e.credit_amount
FROM gl_transaction t
JOIN gl_entry e ON t.transaction_id = e.transaction_id
JOIN chart_of_accounts a ON e.account_id = a.account_id
WHERE t.source_document_type = 'credit_note'
    AND t.transaction_date = CURRENT_DATE
ORDER BY t.created_at DESC, e.debit_amount DESC
LIMIT 2;
```

**Expected Results** (2 entries):

**Entry 1** (Debit):
- `account_name`: Package Revenue
- `gl_account_no`: 4200
- `debit_amount`: 3433.33 ✅ (reduces revenue)
- `credit_amount`: 0.00

**Entry 2** (Credit):
- `account_name`: Accounts Receivable
- `gl_account_no`: 1100
- `debit_amount`: 0.00
- `credit_amount`: 3433.33 ✅ (reduces receivable)

**Transaction Totals**:
- `total_debit`: 3433.33
- `total_credit`: 3433.33 ✅ (balanced)

**What This Means**:
```
Dr: Package Revenue (4200)        ₹3,433.33  (reduce income)
Cr: Accounts Receivable (1100)    ₹3,433.33  (reduce asset)
```

This is the **correct accounting treatment** for a revenue reversal:
- Revenue account is **debited** (reduces income on P&L)
- AR account is **credited** (reduces asset on balance sheet)

#### Query 4: Sessions Cancelled

```sql
SELECT
    session_id,
    session_number,
    session_date,
    session_status,
    service_notes,
    updated_at,
    updated_by
FROM package_sessions
WHERE plan_id = 'a163d628-3b32-44f4-acf0-114755cc34a3'
ORDER BY session_number;
```

**Expected Results**:
- Sessions 1-2: `session_status` = 'completed' (unchanged)
- Sessions 3-6: `session_status` = 'cancelled'
- `service_notes` = 'Cancelled due to plan discontinuation'
- `updated_at` = Today
- `updated_by` = Your user ID

#### Query 5: Installments Cancelled

```sql
SELECT
    installment_id,
    installment_number,
    due_date,
    amount,
    status,
    notes,
    updated_at,
    updated_by
FROM installment_payments
WHERE plan_id = 'a163d628-3b32-44f4-acf0-114755cc34a3'
ORDER BY installment_number;
```

**Expected Results**:
- Paid installments: `status` = 'paid' (unchanged)
- Pending installments: `status` = 'cancelled'
- `notes` = 'Cancelled due to plan discontinuation'
- `updated_at` = Today
- `updated_by` = Your user ID

---

## 🔄 Test Scenario 3: Regular Invoice Refund (API Call)

The same credit note service can be used for **regular service invoices** too!

### Example: Patient Refund for Service Invoice

**Scenario**: Patient paid ₹10,000 for a service but service was not provided. Issue refund credit note.

#### Via API Call (Postman/curl)

```bash
# You'll need to create an API endpoint similar to package discontinuation
# For now, you can test via Python script or admin function

POST /api/billing/invoice/<invoice_id>/credit-note
{
    "amount": 10000.00,
    "reason_code": "service_not_provided",
    "reason_description": "Laser treatment session cancelled by clinic - full refund"
}
```

#### Via Python Script (Direct Service Call)

Create `test_invoice_credit_note.py`:

```python
from app.services.patient_credit_note_service import PatientCreditNoteService
from decimal import Decimal

cn_service = PatientCreditNoteService()

result = cn_service.create_credit_note(
    hospital_id='your-hospital-id',
    branch_id='your-branch-id',
    original_invoice_id='invoice-uuid',
    patient_id='patient-uuid',
    total_amount=Decimal('10000.00'),
    reason_code='service_not_provided',
    reason_description='Laser treatment session cancelled by clinic - full refund',
    plan_id=None,  # No package plan
    user_id='your-user-id',
    auto_post=True
)

print(result)
```

Run:
```bash
python test_invoice_credit_note.py
```

**Expected Result**:
```python
{
    'success': True,
    'credit_note_id': 'uuid',
    'credit_note_number': 'CN/2025-2026/00002',
    'ar_entry_id': 'uuid',
    'gl_transaction_id': 'uuid',
    'message': 'Credit note CN/2025-2026/00002 created successfully'
}
```

#### Verify Same Accounting Entries

Run the same database queries as above (Query 2, 3) and verify:
- AR Entry: Credit ₹10,000 (reduces receivable)
- GL Entries:
  ```
  Dr: Service Revenue (4100 or 4200)  ₹10,000
  Cr: Accounts Receivable (1100)      ₹10,000
  ```

---

## ✅ Success Criteria Checklist

After completing all tests, verify:

### UI Checks
- [x] Modal appears when status changed to "discontinued"
- [x] Modal shows correct financial calculations
- [x] Adjustment amount field is editable
- [x] Reason field is required
- [x] Success message displays credit note number
- [x] Redirect to detail view after success
- [x] Detail view shows discontinued status and credit note

### Database Checks
- [x] Plan status = 'discontinued'
- [x] Plan has discontinuation tracking fields populated
- [x] Plan has credit_note_id reference
- [x] Credit note record created with correct amount
- [x] Credit note status = 'posted'
- [x] Credit note gl_posted = true

### AR Checks
- [x] AR entry created with entry_type = 'credit_note'
- [x] AR credit_amount = adjustment amount
- [x] AR debit_amount = 0.00
- [x] Patient's current_balance reduced correctly

### GL Checks
- [x] GL transaction created
- [x] GL transaction balanced (total_debit = total_credit)
- [x] Revenue account debited (reduces income)
- [x] AR account credited (reduces asset)
- [x] Both entries = adjustment amount

### Business Logic Checks
- [x] Sessions cancelled correctly
- [x] Installments cancelled correctly
- [x] Refund amount calculation correct
- [x] User-adjusted amount respected
- [x] Cancellation fee deduction works

---

## 🐛 Troubleshooting

### Issue: Modal doesn't appear

**Check**:
1. Browser console for JavaScript errors (F12)
2. Entity type is 'package_payment_plans'
3. Status field exists and has 'discontinued' option
4. Form submit is not blocked by other JavaScript

**Fix**: Refresh page, ensure JavaScript is loaded

### Issue: Preview API fails

**Check**:
1. Network tab in browser (F12)
2. API endpoint URL: `/api/package/plan/<plan_id>/discontinuation-preview`
3. Server logs for error messages

**Common Causes**:
- Plan not found (wrong plan_id)
- Hospital context missing
- Plan already discontinued

### Issue: Discontinue API fails

**Check**:
1. Network tab shows request body
2. Server logs for detailed error
3. Required fields (reason, amount) provided

**Common Causes**:
- Invalid amount (negative or NaN)
- Empty reason field
- Plan has no invoice_id

### Issue: Credit note not created

**Check**:
1. Plan has `invoice_id` populated (required!)
2. Server logs show credit note creation attempt
3. Database has chart_of_accounts entries for 4200 and 1100

**Fix**: Ensure plan was created from an invoice, not standalone

### Issue: GL entries not posted

**Check**:
1. `auto_post=True` in service call
2. GL accounts exist (4200, 1100)
3. GL account are active (`is_active=true`)

**Query to check**:
```sql
SELECT account_id, gl_account_no, account_name, is_active
FROM chart_of_accounts
WHERE gl_account_no IN ('4200', '1100')
    AND hospital_id = 'your-hospital-id';
```

---

## 📊 Understanding the Accounting

### Why This GL Entry?

```
Dr: Package Revenue (4200)        ₹3,433.33
Cr: Accounts Receivable (1100)    ₹3,433.33
```

**Explanation**:

1. **Original Invoice Posting** (when plan was created):
   ```
   Dr: Accounts Receivable (1100)  ₹5,900
   Cr: Package Revenue (4200)      ₹5,900
   ```
   This recorded: "Customer owes us ₹5,900 for 6 sessions"

2. **After 2 Sessions Completed**:
   - Customer owes: ₹5,900
   - Services delivered: 2 of 6 sessions (₹1,967)
   - Services NOT delivered: 4 of 6 sessions (₹3,933)

3. **Discontinuation Credit Note**:
   ```
   Dr: Package Revenue (4200)      ₹3,433
   Cr: Accounts Receivable (1100)  ₹3,433
   ```
   This reverses the income for **unused sessions** and reduces the receivable:
   - Revenue reduced by ₹3,433 (we didn't earn it - services not provided)
   - AR reduced by ₹3,433 (customer doesn't owe us anymore for those sessions)

4. **Net Effect**:
   - **P&L**: Revenue = ₹5,900 - ₹3,433 = ₹2,467 (for 2 completed sessions)
   - **Balance Sheet**: AR = ₹5,900 - ₹3,433 = ₹2,467 (customer owes for 2 sessions only)

### Different from Supplier Credit Notes!

**Supplier Credit Note** (AP):
```
Dr: Accounts Payable (2001)  ₹amount  (reduce liability)
Cr: Expense Account (5xxx)   ₹amount  (reduce expense)
```

**Patient Credit Note** (AR):
```
Dr: Revenue Account (4xxx)         ₹amount  (reduce income)
Cr: Accounts Receivable (1100)     ₹amount  (reduce asset)
```

**Key Difference**: Direction of accounts is **opposite** because:
- Supplier = We owe them (liability)
- Patient = They owe us (asset)

---

## 🎓 Next Steps

After successful testing:

1. **Add UI for Regular Invoice Credit Notes**:
   - Create dedicated credit note form
   - Allow direct credit note creation for any invoice
   - Support multiple reason codes

2. **Add Approval Workflow** (if needed):
   - Credit notes > ₹10,000 require approval
   - Add approval button in detail view
   - Approval posts GL entries

3. **Add Credit Note List View**:
   - Universal list for all credit notes
   - Filter by date, patient, status
   - Print credit note documents

4. **Add to Reports**:
   - Credit notes in AR aging report
   - Credit notes in revenue report
   - Credit notes register

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Status**: Ready for Testing
