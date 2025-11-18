# Supplier Payment Management - Comprehensive Guide

**Version:** 2.0
**Last Updated:** November 3, 2025
**Module:** Supplier Payments
**Framework:** Skinspire HMS v2 - Universal Engine

---

## Table of Contents

1. [Overview](#overview)
2. [Payment Workflow](#payment-workflow)
3. [Payment States](#payment-states)
4. [Creating Payments](#creating-payments)
5. [Approval Process](#approval-process)
6. [Payment Reversal](#payment-reversal)
7. [Payment Deletion](#payment-deletion)
8. [Multi-Method Payments](#multi-method-payments)
9. [Advance Payments](#advance-payments)
10. [GL Integration](#gl-integration)
11. [User Interface](#user-interface)
12. [Technical Reference](#technical-reference)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The Supplier Payment module manages all payments to suppliers in the Skinspire HMS system. It supports multi-method payments, approval workflows, advance payments, supplier advance tracking, GL integration, and comprehensive audit trails.

### Key Features

- **Draft & Submit Workflow**: Save payments as drafts for later completion
- **Approval Threshold**: Payments ≥₹10,000 require approval
- **Multi-Method Payments**: Cash, Cheque, Bank Transfer, UPI in a single payment
- **Advance Payment Tracking**: Track and allocate supplier advances
- **Payment Reversal**: Handle overpayments and corrections
- **GL Integration**: Automatic double-entry accounting
- **AP Subledger**: Complete supplier liability tracking
- **Soft Delete**: Recoverable deletion for draft payments
- **Comprehensive Audit**: Track who created, approved, rejected, reversed, or deleted

### Approval Bypass User

**User ID:** `7777777777`
This special bypass user is exempt from approval thresholds and can directly approve/reverse payments regardless of amount.

---

## Payment Workflow

### Standard Payment Flow

```
┌─────────────┐     Save as Draft     ┌────────┐
│   Create    ├──────────────────────>│  DRAFT │
│   Payment   │                       └────┬───┘
└─────┬───────┘                            │
      │                                    │ Submit
      │ Record Payment                     │
      │ (< ₹10,000)                        │
      ▼                                    ▼
┌──────────┐                         ┌─────────────────┐
│ APPROVED │◄────────────────────────┤ PENDING_APPROVAL│
│ (Auto)   │    Approve (≥₹10K)      │   (≥ ₹10,000)   │
└────┬─────┘                         └────┬────────────┘
     │                                    │ Reject
     │ GL Posted                          ▼
     │                              ┌──────────┐
     ▼                              │ REJECTED │
┌──────────┐                        └──────────┘
│COMPLETED │
└──────────┘
```

### Payment State Transitions

| From State | To State | Trigger | Permission Required |
|------------|----------|---------|---------------------|
| - | DRAFT | Save as Draft | payment_add |
| DRAFT | PENDING_APPROVAL | Submit (≥₹10K) | payment_add |
| DRAFT | APPROVED | Submit (<₹10K) | payment_add |
| PENDING_APPROVAL | APPROVED | Approve | payment_approve |
| PENDING_APPROVAL | REJECTED | Reject | payment_approve |
| APPROVED | REVERSED | Reverse Payment | payment_approve |
| DRAFT | DELETED | Delete | payment_delete |
| REJECTED | DELETED | Delete | payment_delete |

---

## Payment States

### 1. DRAFT
**Description:** Payment saved but not submitted
**Characteristics:**
- workflow_status: `draft`
- No GL entries posted
- Can be edited
- Can be deleted (soft delete)
- Can be submitted for approval

**Actions Available:**
- Edit
- Delete
- Submit (converts to PENDING_APPROVAL or APPROVED)

### 2. PENDING_APPROVAL
**Description:** Payment submitted, awaiting approval (amount ≥₹10,000)
**Characteristics:**
- workflow_status: `pending_approval`
- requires_approval: `true`
- No GL entries posted yet
- Cannot be edited
- Cannot be deleted

**Actions Available:**
- Approve → APPROVED
- Reject → REJECTED

### 3. APPROVED
**Description:** Payment approved and GL posted
**Characteristics:**
- workflow_status: `approved`
- gl_posted: `true`
- GL entries created
- AP subledger updated
- Cannot be edited
- Cannot be deleted

**Actions Available:**
- Reverse (creates reversal GL entries)

### 4. REJECTED
**Description:** Payment rejected by approver
**Characteristics:**
- workflow_status: `rejected`
- rejection_reason recorded
- rejected_by and rejected_at tracked
- No GL entries posted
- Can be deleted (soft delete)

**Alert Display:**
```
⚠️ This Payment Has Been Rejected
This payment was rejected on [date] by [user]
Reason: [rejection_reason]
```

**Actions Available:**
- Delete

### 5. REVERSED
**Description:** Approved payment reversed
**Characteristics:**
- workflow_status: `reversed`
- is_reversed: `true`
- Original GL entries reversed
- AP subledger adjusted
- Optional supplier advance created

**Alert Display:**
```
ℹ️ This Payment Has Been Reversed
This payment was reversed on [date] by [user]
Reason: [reversal_reason]
```

**Actions Available:** None (final state)

### 6. DELETED (Soft Delete)
**Description:** Payment soft-deleted
**Characteristics:**
- is_deleted: `true`
- deleted_at and deleted_by tracked
- Only applicable to DRAFT and REJECTED states
- Can be restored

**Alert Display:**
```
🗑️ This Record Has Been Deleted
This record was deleted on [date] by [user]
```

**Actions Available:**
- Restore (only for soft-deleted records)

---

## Creating Payments

### Entry Points

1. **From Payment List**
   Route: `/supplier/payment/record`
   Menu: Suppliers → Payments → Record Payment

2. **From Invoice Detail**
   Route: `/supplier/payment/record?invoice_id={invoice_id}`
   Button: "Record Payment" on invoice detail page

### Form Fields

#### Basic Information
- **Supplier**: Required (dropdown with search)
- **Invoice**: Optional for advance payments, auto-filled when from invoice
- **Branch**: Required (user's default branch or entity branch)
- **Payment Date**: Required (defaults to today)

#### Payment Amount
- **Total Amount**: Required (must sum to payment method amounts)

#### Payment Methods (Multi-Method Support)
- **Cash Amount**: ₹0.00
- **Cheque Amount**: ₹0.00
- **Bank Transfer Amount**: ₹0.00
- **UPI Amount**: ₹0.00
- **Advance Allocation**: Auto-calculated if using supplier advance

**Validation Rule:**
```
cash_amount + cheque_amount + bank_transfer_amount + upi_amount + advance_amount = total_amount
(Tolerance: ₹0.01)
```

#### Cheque Details (if cheque_amount > 0)
- Cheque Number
- Cheque Date
- Cheque Bank
- Cheque Branch

#### Bank Transfer Details (if bank_transfer_amount > 0)
- Bank Name
- Bank Reference Number
- IFSC Code
- Transfer Mode (NEFT/RTGS/IMPS)

#### UPI Details (if upi_amount > 0)
- UPI ID
- UPI App Name
- UPI Transaction ID

#### Additional Fields
- **Reference Number**: Optional payment reference
- **Notes**: Optional payment notes
- **TDS Applicable**: Yes/No
- **TDS Rate**: % (if applicable)
- **TDS Amount**: Auto-calculated or manual

### Save Options

#### 1. Save as Draft
**Button:** "Save as Draft"
**Behavior:**
- workflow_status: `draft`
- No GL posting
- No approval check
- Can edit later

**Use Cases:**
- Incomplete payment information
- Pending document verification
- Payment scheduled for future date

#### 2. Record Payment
**Button:** "Record Payment"
**Behavior:**
- If amount < ₹10,000:
  - workflow_status: `approved`
  - GL entries posted immediately
  - Payment complete
- If amount ≥ ₹10,000:
  - workflow_status: `pending_approval`
  - No GL posting
  - Requires approval

### Example Scenarios

#### Scenario 1: Small Cash Payment
```
Amount: ₹5,000
Cash: ₹5,000
Action: Record Payment
Result: Auto-approved, GL posted, status = approved
```

#### Scenario 2: Large Payment Requiring Approval
```
Amount: ₹25,000
Bank Transfer: ₹25,000
Action: Record Payment
Result: Pending approval, status = pending_approval
```

#### Scenario 3: Multi-Method Payment
```
Amount: ₹15,000
Cash: ₹5,000
Cheque: ₹10,000
Action: Record Payment
Result: Pending approval (total ≥ ₹10K)
```

#### Scenario 4: Draft Payment
```
Amount: ₹20,000
Bank Transfer: ₹20,000
Action: Save as Draft
Result: Saved as draft, no approval check, status = draft
```

---

## Approval Process

### Approval Threshold

**Threshold:** ₹10,000
**Logic:** `payment.amount >= 10000`

### Approval Workflow

#### For Payments ≥ ₹10,000

1. **User Creates Payment**
   - Clicks "Record Payment"
   - System checks amount
   - Sets workflow_status = `pending_approval`
   - No GL posting

2. **Approver Reviews**
   - Navigates to payment detail
   - Clicks "Approve" button
   - Popup appears with payment details

3. **Approval Popup**
   ```
   Approve/Reject Payment

   Payment: PAY-2024-001
   Supplier: ABC Suppliers
   Amount: ₹25,000.00

   Notes (optional):
   [                           ]

   [Cancel]  [Reject]  [Approve]
   ```

4. **On Approval**
   - workflow_status: `pending_approval` → `approved`
   - approved_by: Current user ID
   - approved_at: Current timestamp
   - GL entries posted
   - AP subledger updated
   - Email notification sent (if configured)

5. **On Rejection**
   - workflow_status: `pending_approval` → `rejected`
   - rejected_by: Current user ID
   - rejected_at: Current timestamp
   - rejection_reason: From notes field
   - No GL posting

### Approval Routes

**Approve Route:** `/supplier/payment/approve/<payment_id>`
**Methods:** GET (show popup), POST (process)
**Permission:** `payment_approve`

### Bypass User

**User ID:** `7777777777`

**Behavior:**
- All payments auto-approved regardless of amount
- Bypasses ₹10,000 threshold
- Used for testing and administrative overrides

---

## Payment Reversal

### When to Reverse

**Use Case:** Payment was approved and GL posted, but needs to be undone

**Common Scenarios:**
1. Overpayment to supplier
2. Duplicate payment
3. Wrong supplier
4. Wrong amount
5. Invoice correction needed

### Reversal Types

#### 1. Entry Error (Money NOT Transferred)
**Scenario:** Accounting entry made, but money never left bank

**Process:**
1. Click "Reverse Payment"
2. Select: "No - Simple reversal"
3. Enter reason
4. Click "Reverse Payment"

**Result:**
- workflow_status: `approved` → `reversed`
- is_reversed: `true`
- GL entries reversed
- AP subledger adjusted
- NO supplier advance created

#### 2. Overpayment / Duplicate (Money ALREADY with Supplier)
**Scenario:** Money physically transferred to supplier, need to track as advance

**Process:**
1. Click "Reverse Payment"
2. Select: "Yes - Create supplier advance"
3. Enter reason
4. Click "Reverse Payment"

**Result:**
- workflow_status: `approved` → `reversed`
- is_reversed: `true`
- GL entries reversed
- AP subledger adjusted
- **Supplier advance created** (tracks money with supplier)

### Reversal Popup

```
Reverse Payment

Payment: PAY-2024-001
Amount: ₹25,000.00

Was money transferred to supplier?

○ No - Simple reversal
   Money was not transferred, just reverse the entry

● Yes - Create supplier advance
   Money is with supplier, create advance for future use

Reason (required):
[                                                    ]

[Cancel]  [Reverse Payment]
```

### Reversal GL Entries

#### Original Payment GL (Example)
```
Dr  Accounts Payable          25,000
    Cr  Bank - HDFC                    25,000
```

#### Reversal GL Entries
```
Dr  Bank - HDFC              25,000
    Cr  Accounts Payable                25,000
```

#### If Supplier Advance Created
```
Dr  Supplier Advance         25,000
    Cr  Accounts Payable                25,000
```

### Reversal Route

**Route:** `/supplier/payment/reverse/<payment_id>`
**Methods:** GET (show popup), POST (process)
**Permission:** `payment_approve`

---

## Payment Deletion

### When to Delete

**Applicable States:**
- DRAFT
- REJECTED

**NOT Applicable:**
- APPROVED (use Reversal instead)
- PENDING_APPROVAL (reject first, then delete)

### Deletion Types

**IMPORTANT:** Deletion popup differs based on payment status:

#### For DRAFT Payments
**Simple Confirmation:** No reversal type selection needed

**Reason:** Draft payments are just saved entries - no money has moved yet.

**Popup:**
```
Delete Payment

Payment: PAY-2024-001
Amount: ₹5,000.00
Status: Draft

ℹ️ Are you sure?
This draft payment will be soft deleted.
You can restore it later if needed.

Reason (optional):
[                                                    ]

[Cancel]  [Delete Payment]
```

**Result:**
- Soft delete (is_deleted = true)
- No GL reversal needed
- No supplier advance
- reversal_type automatically set to 'entry_error'

#### For REJECTED Payments
**Reversal Type Selection:** Ask if money was transferred before rejection

**Reason:** Rejected payments might have been physically made before being rejected in the system.

**Popup:**
```
Delete Payment

Payment: PAY-2024-002
Amount: ₹15,000.00
Status: Rejected

⚠️ This rejected payment will be deleted. If money was
already transferred, we'll create a supplier advance.

Was money transferred to supplier before rejection?

● No - Entry Error
   Simple mistake, money NOT transferred to supplier

○ Yes - Overpayment
   Wrong amount paid, money ALREADY with supplier (creates advance)

○ Yes - Duplicate Payment
   Payment made twice, money ALREADY with supplier (creates advance)

Reason (optional):
[                                                    ]

[Cancel]  [Delete Payment]
```

**Results:**

1. **Entry Error** (Default)
   - Soft delete only
   - No supplier advance

2. **Overpayment**
   - Soft delete
   - Creates supplier advance
   - Tracks money with supplier for future use

3. **Duplicate Payment**
   - Soft delete
   - Creates supplier advance
   - Prevents future duplicate processing

### Soft Delete Details

**Fields Updated:**
- is_deleted: `true`
- deleted_at: Current timestamp
- deleted_by: Current user ID
- deletion_reason: User-provided reason

**Restoration:**
- Deleted payments can be restored
- Click "Restore" button on deleted payment detail
- Sets is_deleted = `false`

### Deletion Route

**Route:** `/supplier/payment/delete/<payment_id>`
**Methods:** GET (show popup), POST (process)
**Permission:** `payment_delete`

---

## Multi-Method Payments

### Supported Payment Methods

1. **Cash**
2. **Cheque**
3. **Bank Transfer**
4. **UPI**
5. **Advance Allocation** (uses existing supplier advance)

### Multi-Method Payment Entry

#### Example: ₹50,000 Payment with Multiple Methods

```
Total Amount: ₹50,000.00

Payment Methods:
├─ Cash:           ₹10,000.00
├─ Cheque:         ₹15,000.00
├─ Bank Transfer:  ₹20,000.00
└─ UPI:            ₹5,000.00
                   ──────────
   Total:          ₹50,000.00 ✓
```

### Validation

**Rule:** Sum of all method amounts must equal total amount

```javascript
const validation = (cash + cheque + bank + upi + advance) === total;
const tolerance = 0.01; // Allow ₹0.01 difference for rounding

if (Math.abs((cash + cheque + bank + upi + advance) - total) > tolerance) {
    error("Payment method amounts must equal total amount");
}
```

### Method-Specific Fields

#### Cheque Payment
- Cheque Number (required if cheque_amount > 0)
- Cheque Date
- Cheque Bank
- Cheque Branch
- Cheque Status (pending/cleared/bounced)

#### Bank Transfer
- Bank Name
- Bank Reference Number
- IFSC Code
- Transfer Mode (NEFT/RTGS/IMPS/SWIFT)

#### UPI Payment
- UPI ID (e.g., user@paytm)
- UPI App Name (PhonePe/GooglePay/Paytm)
- UPI Transaction ID

### Payment Method Determination

**Automatic Logic:**
```python
def determine_payment_method(cash, cheque, bank, upi, advance):
    methods_used = []
    if cash > 0: methods_used.append('cash')
    if cheque > 0: methods_used.append('cheque')
    if bank > 0: methods_used.append('bank_transfer')
    if upi > 0: methods_used.append('upi')
    if advance > 0: methods_used.append('advance')

    if len(methods_used) == 0:
        return 'cash'  # Default
    elif len(methods_used) == 1:
        return methods_used[0]
    else:
        return 'mixed'
```

---

## Advance Payments

### Overview

Advance payments are payments made to suppliers without a specific invoice. The advance can later be allocated against future invoices.

### Creating Advance Payment

**Process:**
1. Create payment WITHOUT selecting invoice
2. Select supplier
3. Enter amount and payment method
4. Click "Record Payment"

**Result:**
- Payment created with invoice_id = NULL
- SupplierAdvanceAdjustment record created (adjustment_type = 'advance_receipt')
- Advance available for future allocation

### Using Supplier Advance

**From Invoice Payment Form:**

```
Invoice Balance: ₹50,000.00
Available Advance: ₹20,000.00

Payment Allocation:
├─ From Advance:   ₹20,000.00
├─ Cash:           ₹15,000.00
└─ Bank Transfer:  ₹15,000.00
                   ──────────
   Total:          ₹50,000.00
```

### Advance Allocation Logic

**Service Method:** `_allocate_advance_to_invoice()`

**Process:**
1. Get unallocated advance payments for supplier
2. Sort by payment_date (oldest first - FIFO)
3. Allocate until requested amount met or no more advances
4. Create SupplierAdvanceAdjustment records (adjustment_type = 'allocation')

**Example:**
```
Available Advances:
- Payment A: ₹10,000 (oldest)
- Payment B: ₹15,000
- Payment C: ₹8,000

Request: Allocate ₹22,000

Allocation:
1. Use full ₹10,000 from Payment A → ₹12,000 remaining
2. Use full ₹12,000 from Payment B → ₹0 remaining

Result: ₹22,000 allocated
```

### Supplier Advance Adjustment Types

| Type | Description | Debit/Credit |
|------|-------------|--------------|
| advance_receipt | Advance payment received | Debit |
| allocation | Advance allocated to invoice | Credit |
| reversal | Payment reversal creating advance | Debit |
| refund | Advance refunded to supplier | Credit |

---

## GL Integration

### GL Entry Creation

**Trigger:** Payment approval (auto or manual)

**Service:** `create_supplier_payment_gl_entries()`

**Location:** `app/services/gl_service.py`

### GL Entry Structure

#### Payment Against Invoice

```
Dr  Accounts Payable (Supplier)    Amount
    Cr  Bank Account                        Amount
```

#### Advance Payment (No Invoice)

```
Dr  Supplier Advance                Amount
    Cr  Bank Account                        Amount
```

#### Payment with TDS

```
Dr  Accounts Payable                Amount + TDS
    Cr  Bank Account                        Amount
    Cr  TDS Payable                         TDS
```

### AP Subledger Entries

**Created for ALL payments** (invoice and advance)

#### Payment Against Invoice
```python
create_ap_subledger_entry(
    entry_type='payment',
    reference_type='payment',
    debit_amount=payment.amount,
    credit_amount=0,
    supplier_id=payment.supplier_id,
    invoice_id=payment.invoice_id
)
```

#### Advance Payment
```python
create_ap_subledger_entry(
    entry_type='advance',
    reference_type='payment',
    debit_amount=payment.amount,
    credit_amount=0,
    supplier_id=payment.supplier_id
)
```

### GL Reversal

**Trigger:** Payment reversal

**Service:** `reverse_supplier_payment_gl_entries()`

**Process:**
1. Find original GL transaction
2. Create reversing GL entries (swap Dr/Cr)
3. Update AP subledger (reverse amounts)
4. Link reversal to original transaction

**Example:**
```
Original:
Dr  Accounts Payable    25,000
    Cr  Bank                    25,000

Reversal:
Dr  Bank                25,000
    Cr  Accounts Payable        25,000
```

### GL Posting Status

**Fields:**
- gl_posted: Boolean
- gl_entry_id: UUID (link to GLTransaction)
- posting_date: Timestamp
- posting_errors: Text (if posting failed)

**Logic:**
```python
if payment.gl_posted:
    logger.warning("GL already posted, skipping")
else:
    gl_result = create_supplier_payment_gl_entries(...)
    payment.gl_posted = True
    payment.gl_entry_id = gl_result['transaction_id']
    payment.posting_date = datetime.now()
```

---

## User Interface

### Payment List View

**Route:** `/universal/supplier_payments/list`

**Features:**
- Filterable by supplier, status, date range, amount range
- Sortable columns
- Status badges (Draft, Pending, Approved, Rejected, Reversed)
- Quick actions dropdown
- Pagination

**Columns:**
- Reference No
- Payment Date
- Supplier Name
- Invoice Number (if applicable)
- Amount
- Payment Method
- Status
- Actions

### Payment Detail View

**Route:** `/universal/supplier_payments/detail/<payment_id>`

**Sections:**

#### 1. Header
- Payment Reference
- Supplier Name
- Amount (prominent)
- Status Badge

#### 2. Alert Banners
- Deleted Alert (red) - if is_deleted
- Rejected Alert (yellow) - if workflow_status = rejected
- Reversed Alert (blue) - if is_reversed

#### 3. Payment Information Tab
- Basic Details
- Payment Methods Breakdown
- Method-Specific Details (cheque, bank, UPI)

#### 4. Invoice Information Tab (if invoice_id)
- Invoice Number
- Invoice Date
- Invoice Amount
- Payment Allocation

#### 5. Approval Information Tab
- Approval Status
- Submitted By / Date
- Approved By / Date
- Rejected By / Date / Reason

#### 6. GL Information Tab
- GL Posted Status
- GL Transaction ID
- Posting Date
- AP Subledger Entries

#### 7. Action Buttons

**Conditional Visibility:**

| Button | Visible When | Permission |
|--------|--------------|------------|
| Edit | status = draft | payment_edit |
| Delete | status = draft OR rejected | payment_delete |
| Approve | status = pending_approval | payment_approve |
| Reject | status = pending_approval | payment_approve |
| Reverse | status = approved | payment_approve |
| Restore | is_deleted = true | payment_delete |

### Alert Banner Styles

#### Deleted (Red)
```html
<div class="alert alert-danger">
    <i class="fas fa-trash-alt"></i>
    This Record Has Been Deleted
    This record was deleted on 01/Nov/2025 at 14:30 by john@hospital.com
</div>
```

#### Rejected (Yellow)
```html
<div class="alert alert-warning">
    <i class="fas fa-times-circle"></i>
    This Payment Has Been Rejected
    This payment was rejected on 02/Nov/2025 at 10:15 by manager@hospital.com
    Reason: Incorrect invoice amount
</div>
```

#### Reversed (Blue)
```html
<div class="alert alert-info">
    <i class="fas fa-exchange-alt"></i>
    This Payment Has Been Reversed
    This payment was reversed on 03/Nov/2025 at 16:45 by admin@hospital.com
    Reason: Overpayment - created supplier advance
</div>
```

---

## Technical Reference

### Database Schema

**Table:** `supplier_payment`

#### Core Fields
```sql
payment_id              UUID PRIMARY KEY
hospital_id             UUID NOT NULL
branch_id               UUID NOT NULL
supplier_id             UUID NOT NULL
invoice_id              UUID (nullable)
```

#### Payment Details
```sql
payment_date            TIMESTAMP NOT NULL
amount                  NUMERIC(12,2) NOT NULL
payment_method          VARCHAR(20)
reference_no            VARCHAR(50)
notes                   VARCHAR(255)
```

#### Multi-Method Amounts
```sql
cash_amount             NUMERIC(12,2) DEFAULT 0
cheque_amount           NUMERIC(12,2) DEFAULT 0
bank_transfer_amount    NUMERIC(12,2) DEFAULT 0
upi_amount              NUMERIC(12,2) DEFAULT 0
advance_amount          NUMERIC(12,2) DEFAULT 0
```

#### Workflow Fields
```sql
workflow_status         VARCHAR(20) DEFAULT 'draft'
requires_approval       BOOLEAN DEFAULT FALSE
approved_by             VARCHAR(15)
approved_at             TIMESTAMP
rejected_by             VARCHAR(15)
rejected_at             TIMESTAMP
rejection_reason        TEXT
```

#### Reversal Fields
```sql
is_reversed             BOOLEAN DEFAULT FALSE
reversed_by             VARCHAR(15)
reversed_at             TIMESTAMP
reversal_reason         VARCHAR(255)
```

#### Soft Delete Fields (via SoftDeleteMixin)
```sql
is_deleted              BOOLEAN DEFAULT FALSE
deleted_by              VARCHAR(50)
deleted_at              TIMESTAMP
```

#### GL Fields
```sql
gl_posted               BOOLEAN DEFAULT FALSE
gl_entry_id             UUID
posting_date            TIMESTAMP
posting_errors          TEXT
```

### Service Layer

**File:** `app/services/supplier_payment_service.py`

**Class:** `SupplierPaymentService`

**Key Methods:**

```python
def create_payment(data, hospital_id, branch_id, **context) -> Dict
def update_payment(payment_id, data, hospital_id, **context) -> Dict
def delete_payment(payment_id, user_id, reason, reversal_type, **context) -> Dict
def restore_payment(payment_id, user_id) -> Dict
def approve_payment(payment_id, user_id, notes) -> Dict
def reject_payment(payment_id, user_id, reason) -> Dict
def get_by_id(payment_id, hospital_id, **kwargs) -> Dict
def search_data(filters, hospital_id, branch_id, page, per_page, **kwargs) -> Dict
```

### Controller Layer

**File:** `app/controllers/supplier_controller.py`

**Class:** `SupplierPaymentController`

**Responsibilities:**
- Form handling
- Data validation
- Service delegation
- Context preparation
- Success/error handling

### Routes

**File:** `app/views/supplier_views.py`

**Blueprint:** `supplier_views_bp`

#### Payment Routes

| Route | Methods | Function | Purpose |
|-------|---------|----------|---------|
| `/payment/record` | GET, POST | create_payment | Create new payment |
| `/payment/edit/<id>` | GET, POST | edit_payment | Edit draft payment |
| `/payment/approve/<id>` | GET, POST | approve_payment | Approve/reject payment |
| `/payment/reverse/<id>` | GET, POST | reverse_payment | Reverse approved payment |
| `/payment/delete/<id>` | GET, POST | delete_payment | Delete draft/rejected payment |
| `/payment/restore/<id>` | POST | restore_payment | Restore deleted payment |

### Configuration

**File:** `app/config/modules/supplier_payment_config.py`

**Key Settings:**

```python
# Approval threshold
APPROVAL_THRESHOLD = Decimal('10000.00')

# Action button visibility
actions = [
    ActionDefinition(
        id="approve",
        conditions={"workflow_status": ["pending_approval"]}
    ),
    ActionDefinition(
        id="delete",
        conditions={"workflow_status": ["draft", "rejected"]}
    ),
    ActionDefinition(
        id="reverse",
        conditions={
            "workflow_status": ["approved"],
            "is_reversed": [False]
        }
    )
]
```

### Cache Invalidation

**Critical for List View Refresh:**

```python
from app.engine.universal_service_cache import invalidate_service_cache_for_entity

# After create/update/delete/restore
invalidate_service_cache_for_entity('supplier_payments', cascade=False)

# If invoice involved
invalidate_service_cache_for_entity('supplier_invoices', cascade=False)
```

---

## Troubleshooting

### Common Issues

#### 1. Payment Not Showing in List

**Symptom:** Payment created but not visible in list view

**Cause:** Cache not invalidated

**Solution:**
```python
from app.engine.universal_service_cache import invalidate_service_cache_for_entity
invalidate_service_cache_for_entity('supplier_payments', cascade=False)
```

#### 2. Approval Not Working

**Symptom:** Click approve, but workflow_status not changing

**Cause:** Transaction rollback or ApprovalMixin conflict

**Solution:**
```python
# Use db.session directly instead of nested transaction
payment = db.session.query(SupplierPayment).filter_by(...).first()
payment.approve(approver_id=user_id, notes="Approved")
payment.workflow_status = 'approved'  # Explicitly set
db.session.commit()
```

#### 3. Duplicate GL Entries

**Symptom:** Multiple GL transactions for single payment

**Cause:** No gl_posted check before posting

**Solution:**
```python
if payment.gl_posted:
    logger.warning("GL already posted, skipping")
else:
    gl_result = create_supplier_payment_gl_entries(...)
    payment.gl_posted = True
```

#### 4. Constraint Violation on Reversal

**Symptom:** `adjustment_type_check` constraint violation

**Cause:** Using invalid adjustment_type value

**Solution:**
```python
# WRONG
adjustment_type='payment_reversal'

# CORRECT
adjustment_type='reversal'

# Valid values: 'allocation', 'reversal', 'refund', 'advance_receipt'
```

#### 5. Action Buttons Not Visible

**Symptom:** Delete/Reverse buttons not showing

**Cause:** Condition evaluation mismatch

**Debug:**
```python
# Enable debug logging in data_assembler.py
logger.info(f"Action {action.id}: workflow_status={item.get('workflow_status')}, is_deleted={item.get('is_deleted')}")
```

**Solution:** Check action configuration conditions match actual field values

### Logging

**Enable detailed logging:**

```python
import logging
logger = logging.getLogger('app.services.supplier_payment_service')
logger.setLevel(logging.DEBUG)
```

**Key log points:**
- Payment creation
- Approval/rejection
- GL posting
- Cache invalidation
- Advance allocation

### Testing Checklist

- [ ] Create draft payment
- [ ] Edit draft payment
- [ ] Delete draft payment
- [ ] Submit payment < ₹10K (auto-approve)
- [ ] Submit payment ≥ ₹10K (pending approval)
- [ ] Approve pending payment
- [ ] Reject pending payment
- [ ] Reverse approved payment (no advance)
- [ ] Reverse approved payment (with advance)
- [ ] Multi-method payment
- [ ] Advance payment (no invoice)
- [ ] Payment with advance allocation
- [ ] Verify GL entries for each scenario
- [ ] Verify AP subledger for each scenario
- [ ] Check alert banners display correctly
- [ ] Restore deleted payment

---

## Appendix

### Workflow Status Values

| Value | Description |
|-------|-------------|
| draft | Payment saved but not submitted |
| pending_approval | Submitted, awaiting approval |
| approved | Approved and GL posted |
| rejected | Rejected by approver |
| reversed | Approved payment reversed |

### Adjustment Types (SupplierAdvanceAdjustment)

| Type | Usage |
|------|-------|
| advance_receipt | Advance payment received |
| allocation | Advance allocated to invoice |
| reversal | Payment reversal creating advance |
| refund | Advance refunded to supplier |

### Entry Types (APSubledger)

| Type | Usage |
|------|-------|
| invoice | Supplier invoice booking |
| payment | Payment against invoice |
| advance | Advance payment |
| adjustment | AP adjustments and reversals |

### Permission Codes

| Permission | Action |
|------------|--------|
| payment_view | View payments |
| payment_add | Create payments |
| payment_edit | Edit draft payments |
| payment_delete | Delete draft/rejected payments |
| payment_approve | Approve/reject/reverse payments |

---

**End of Document**
