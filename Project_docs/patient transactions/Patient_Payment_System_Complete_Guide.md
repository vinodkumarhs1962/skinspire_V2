# Patient Payment System - Complete Technical Guide
## SkinSpire Clinic HMS

**Version:** 2.0
**Date:** November 15, 2025
**Author:** System Documentation
**Module:** Patient Billing & Payments

---

## Table of Contents

1. [Overview](#overview)
2. [Business Logic](#business-logic)
3. [Many-to-Many Relationship Architecture](#many-to-many-relationship-architecture)
4. [Payment Types and Scenarios](#payment-types-and-scenarios)
5. [Accounting Entries](#accounting-entries)
6. [Package Payment Integration](#package-payment-integration)
7. [Database Schema](#database-schema)
8. [Service Layer Architecture](#service-layer-architecture)
9. [Configuration Files](#configuration-files)
10. [Sample Transactions with Complete Entries](#sample-transactions)
11. [Workflow and Approval Process](#workflow-and-approval-process)
12. [Integration Points](#integration-points)
13. [Key Business Rules](#key-business-rules)

---

## 1. Overview

The Patient Payment System in SkinSpire HMS handles all payment receipts from patients, including:
- Single invoice payments
- Multi-invoice payments (one payment across multiple invoices)
- Package installment payments
- Advance payments
- Mixed payment methods (cash, card, UPI)

**Key Features:**
- ✅ Many-to-many relationship between payments and invoices
- ✅ Line-item level AR (Accounts Receivable) tracking
- ✅ Double-entry GL (General Ledger) posting
- ✅ Package payment plan integration
- ✅ Workflow-based approval system
- ✅ Complete audit trail and traceability

---

## 2. Business Logic

### 2.1 Payment Processing Flow

```
Patient makes payment
    ↓
Select invoices to pay (one or more)
    ↓
Allocate payment amount across invoices
    ↓
Allocate at LINE-ITEM level (Medicine → Service → Package priority)
    ↓
Create Payment Record (payment_details table)
    ↓
Create AR Subledger Entries (one per line item paid)
    ↓
[If payment includes package installment]
    → Create Installment Payment record
    → Create AR entry for installment amount
    ↓
[If payment > approval threshold OR save_as_draft=True]
    → workflow_status = 'pending_approval'
    → AR entries created but GL NOT posted
    ↓
[If auto-approved]
    → workflow_status = 'approved'
    → Create GL Transaction
    → Create GL Entries (Debit: Cash/Card/UPI, Credit: AR)
    → Update AR entries with GL transaction ID
    ↓
Update invoice paid amounts and balances
    ↓
Payment Complete
```

### 2.2 Core Principles

1. **AR is Always Created**: AR subledger entries are created IMMEDIATELY for all payments, regardless of approval status. AR tracks patient liabilities.

2. **GL Posting is Conditional**: GL entries are only created when:
   - Payment is auto-approved (below threshold)
   - Payment is manually approved by authorized user
   - NOT created for draft or pending approval payments

3. **Line-Item Level Allocation**: Payments are allocated to individual invoice line items (not invoice headers) to track exactly what was paid for.

4. **Payment Priority**: When allocating payment across line items:
   - **Priority 1**: Medicine items (highest priority)
   - **Priority 2**: Service items
   - **Priority 3**: Package items (lowest priority)

5. **Package Installments**: Package payments are tracked in TWO places:
   - `installment_payments` table (informational tracking)
   - `ar_subledger` table (accounting entry)

---

## 3. Many-to-Many Relationship Architecture

### 3.1 The Challenge

Traditional payment systems have a one-to-one relationship:
```
Payment → Invoice (single relationship)
```

SkinSpire supports **multi-invoice payments**:
```
One Payment can pay for Multiple Invoices
One Invoice can have Multiple Payments
```

### 3.2 Solution: AR Subledger as Junction Table

The `ar_subledger` table acts as the junction table connecting payments to invoices:

```
payment_details (payment_id)
    ↓
    ├─→ ar_subledger (reference_id = payment_id, reference_type = 'payment')
    │       ↓
    │       └─→ invoice_line_item (reference_line_item_id)
    │               ↓
    │               └─→ invoice_header (invoice_id)
    │
    └─→ installment_payments (payment_id) [for package payments]
            ↓
            └─→ package_payment_plans (plan_id)
```

### 3.3 Payment-Invoice Relationship Model

**Entity Relationship:**

```
┌─────────────────────┐         ┌──────────────────────┐
│  payment_details    │         │  invoice_header      │
│  ─────────────────  │         │  ──────────────────  │
│  payment_id (PK)    │         │  invoice_id (PK)     │
│  invoice_id (NULL)  │◄────┐   │  patient_id          │
│  patient_id         │     │   │  grand_total         │
│  total_amount       │     │   │  paid_amount         │
│  workflow_status    │     │   │  balance_due         │
│  payment_source     │     │   └──────────────────────┘
│  invoice_count      │     │            │
└─────────────────────┘     │            │
         │                  │            ▼
         │                  │   ┌──────────────────────┐
         │                  │   │ invoice_line_item    │
         │                  │   │ ───────────────────  │
         │                  │   │ line_item_id (PK)    │
         │                  │   │ invoice_id (FK)      │
         │                  │   │ item_type            │
         │                  │   │ item_name            │
         │                  │   │ line_total           │
         │                  │   └──────────────────────┘
         │                  │            ▲
         │                  │            │
         ▼                  │            │
┌──────────────────────────┴────────────┴──────┐
│         ar_subledger (JUNCTION TABLE)        │
│  ──────────────────────────────────────────  │
│  entry_id (PK)                               │
│  patient_id                                  │
│  entry_type ('invoice' or 'payment')         │
│  reference_id (payment_id or invoice_id)     │
│  reference_type ('payment' or 'invoice')     │
│  reference_line_item_id → line_item_id (FK)  │
│  debit_amount                                │
│  credit_amount                               │
│  gl_transaction_id                           │
└──────────────────────────────────────────────┘
```

**Key Field: `invoice_id` in payment_details**
- For **single invoice payments**: Contains the invoice_id
- For **multi-invoice payments**: NULL (payment spans multiple invoices)
- For **package installments**: NULL (payment for package plan, not invoice)

---

## 4. Payment Types and Scenarios

### 4.1 Single Invoice Payment

**Scenario:** Patient pays ₹5,000 for Invoice INV-001

**Payment Record:**
```sql
payment_details:
  payment_id: uuid-123
  invoice_id: inv-001-uuid  -- ✅ Single invoice reference
  patient_id: patient-uuid
  total_amount: 5000.00
  payment_source: 'single_invoice'
  invoice_count: 1
```

**AR Entries:**
```sql
ar_subledger: (3 entries - one per line item)
  Entry 1: Medicine item, credit ₹1,500
  Entry 2: Service item, credit ₹2,000
  Entry 3: Service item, credit ₹1,500
  Total Credits: ₹5,000 (matches payment amount)
```

### 4.2 Multi-Invoice Payment

**Scenario:** Patient pays ₹10,000 to partially pay 3 invoices

**Payment Record:**
```sql
payment_details:
  payment_id: uuid-456
  invoice_id: NULL  -- ✅ Multi-invoice, no single reference
  patient_id: patient-uuid
  total_amount: 10000.00
  payment_source: 'multi_invoice'
  invoice_count: 3
```

**AR Entries:**
```sql
ar_subledger: (8 entries across 3 invoices)
  -- Invoice 1 (INV-001): ₹4,000
  Entry 1: reference_line_item_id=line-1, credit ₹1,500
  Entry 2: reference_line_item_id=line-2, credit ₹2,500

  -- Invoice 2 (INV-002): ₹3,500
  Entry 3: reference_line_item_id=line-3, credit ₹2,000
  Entry 4: reference_line_item_id=line-4, credit ₹1,500

  -- Invoice 3 (INV-003): ₹2,500
  Entry 5: reference_line_item_id=line-5, credit ₹1,000
  Entry 6: reference_line_item_id=line-6, credit ₹1,500

  Total Credits: ₹10,000 (matches payment amount)
```

### 4.3 Package Installment Payment

**Scenario:** Patient pays ₹10,646.67 split between invoices and package installment

**Payment Record:**
```sql
payment_details:
  payment_id: 3b90a765-0957-49c3-b3d5-e0f5afee30e1
  invoice_id: NULL  -- Mixed payment type
  patient_id: a8580b45-0833-4d2d-ab04-c15268b5f8c1
  total_amount: 10646.67
  payment_source: 'multi_invoice'  -- Could also be 'package_installment'
  invoice_count: 2
  cash_amount: 5646.67
  credit_card_amount: 5000.00
```

**AR Entries:**
```sql
ar_subledger: (6 entries)
  -- Invoice line items: ₹7,500
  Entry 1: line_item Medicine, credit ₹94.40
  Entry 2: line_item Service, credit ₹37.76
  Entry 3: line_item Service, credit ₹2,950.00
  Entry 4: line_item Package (partial), credit ₹917.84
  Entry 5: line_item Package, credit ₹3,500.00

  -- Package installment: ₹3,146.67
  Entry 6: reference_line_item_id=NULL,
           entry_type='package_installment',
           credit ₹3,146.67

  Total Credits: ₹10,646.67 ✅ MATCHES PAYMENT
```

**Installment Payment Record:**
```sql
installment_payments:
  installment_id: 4f302fe7-1ac5-49ad-84ac-1f6011275427
  plan_id: 4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf
  payment_id: 3b90a765-0957-49c3-b3d5-e0f5afee30e1
  amount: 3146.67  -- ✅ INFORMATIONAL tracking
  installment_number: 1

package_payment_plans:
  plan_id: 4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf
  package_id: 82214350-1a7c-4d93-991a-6a5a0fd62ecb
  total_amount: 9440.00
  paid_amount: 3146.67  -- Updated after payment
  balance_amount: 6293.33
```

---

## 5. Accounting Entries

### 5.1 AR (Accounts Receivable) Subledger

**Purpose:** Track patient-level receivables at line-item granularity

**Entry Types:**

1. **Invoice Creation** (Debit AR)
```sql
entry_type: 'invoice'
reference_type: 'invoice'
reference_id: invoice_id
debit_amount: line_total  -- Increases AR (patient owes)
credit_amount: 0
```

2. **Payment Receipt** (Credit AR)
```sql
entry_type: 'payment'
reference_type: 'payment'
reference_id: payment_id
reference_line_item_id: line_item_id
debit_amount: 0
credit_amount: allocated_amount  -- Decreases AR (patient paid)
```

3. **Package Installment** (Credit AR)
```sql
entry_type: 'package_installment'
reference_type: 'payment'
reference_id: payment_id
reference_line_item_id: NULL  -- No specific line item
debit_amount: 0
credit_amount: installment_amount
```

**AR Balance Calculation:**
```sql
SELECT
  patient_id,
  SUM(debit_amount) - SUM(credit_amount) as ar_balance
FROM ar_subledger
WHERE patient_id = ?
GROUP BY patient_id;

-- Positive balance = Patient owes money
-- Zero balance = Fully paid
-- Negative balance = Overpayment/Advance
```

### 5.2 GL (General Ledger) Entries

**Purpose:** Double-entry bookkeeping for financial statements

**Created When:**
- Payment workflow_status = 'approved'
- Payment is auto-approved (below approval threshold)

**NOT Created When:**
- Payment is draft (save_as_draft=True)
- Payment is pending approval

**GL Transaction Structure:**

```sql
gl_transaction:
  transaction_id: uuid
  transaction_date: payment_date
  transaction_type: 'payment_receipt'
  reference_id: payment_id (as VARCHAR)
  reference_type: 'payment_receipt'
  total_debit: sum of all debits
  total_credit: sum of all credits
  description: "Payment receipt from Patient..."
```

**GL Entries for Multi-Method Payment:**

Example: ₹10,646.67 paid via Cash (₹5,646.67) + Credit Card (₹5,000)

```sql
gl_entry:
  -- Debit: Cash Account
  Entry 1:
    account_id: CASH_ACCOUNT (e.g., '1010-Cash')
    debit_amount: 5646.67
    credit_amount: 0
    description: "Cash portion of payment PMT-2025-000104"

  -- Debit: Credit Card Account
  Entry 2:
    account_id: CREDIT_CARD_ACCOUNT (e.g., '1020-Card')
    debit_amount: 5000.00
    credit_amount: 0
    description: "Credit card portion of payment PMT-2025-000104"

  -- Credit: Accounts Receivable
  Entry 3:
    account_id: AR_ACCOUNT (e.g., '1200-AR')
    debit_amount: 0
    credit_amount: 10646.67
    description: "AR payment from patient"

Total Debits: ₹10,646.67
Total Credits: ₹10,646.67  ✅ BALANCED
```

**Account Mapping (from `gl_account_config.py`):**

```python
PAYMENT_RECEIPT_ACCOUNTS = {
    'cash': '1010-Cash',
    'credit_card': '1020-Credit Card',
    'debit_card': '1020-Debit Card',
    'upi': '1025-UPI',
    'accounts_receivable': '1200-Accounts Receivable'
}
```

### 5.3 Double-Entry Accounting Rules

**Fundamental Equation:**
```
Assets = Liabilities + Equity
```

**For Patient Payments:**

**When Invoice is Created:**
- **Debit AR** (Asset increases - patient owes money)
- **Credit Revenue** (Equity increases - we earned revenue)

**When Payment is Received:**
- **Debit Cash/Card/UPI** (Asset increases - we got cash)
- **Credit AR** (Asset decreases - patient no longer owes that amount)

**Net Effect:** Cash replaces AR, total assets unchanged

---

## 6. Package Payment Integration

### 6.1 Package Payment Plan Structure

```
patient
  └─→ package_payment_plans (one plan per package purchased)
        ├─ total_amount: Total package cost
        ├─ paid_amount: Amount paid so far
        ├─ balance_amount: Remaining balance
        ├─ installment_frequency: 'weekly', 'monthly', etc.
        ├─ number_of_installments: Total installments planned
        └─→ installment_payments (multiple installments)
              ├─ installment_number: 1, 2, 3...
              ├─ due_date: When installment is due
              ├─ amount: Installment amount
              ├─ payment_id: Link to actual payment
              └─ status: 'pending', 'paid', 'overdue'
```

### 6.2 Package Payment Flow

```
Patient purchases package (₹9,440 for Advanced Skin Treatment)
    ↓
Create package_payment_plan:
  - total_amount: 9440.00
  - paid_amount: 0
  - balance_amount: 9440.00
  - installment_frequency: 'monthly'
  - number_of_installments: 3
    ↓
[Optional] Auto-generate installment schedule:
  - Installment 1: ₹3,146.67, due 2025-11-15
  - Installment 2: ₹3,146.67, due 2025-12-15
  - Installment 3: ₹3,146.66, due 2026-01-15
    ↓
Patient makes payment (₹10,646.67 total)
    ↓
Allocate payment:
  - Invoice line items: ₹7,500.00
  - Package installment: ₹3,146.67
    ↓
Create installment_payments record:
  - installment_id: new UUID
  - plan_id: package plan UUID
  - payment_id: payment UUID
  - amount: 3146.67
  - installment_number: 1
  - status: 'paid'
    ↓
Update package_payment_plan:
  - paid_amount: 0 + 3146.67 = 3146.67
  - balance_amount: 9440 - 3146.67 = 6293.33
    ↓
Create AR subledger entry:
  - entry_type: 'package_installment'
  - reference_id: payment_id
  - reference_line_item_id: NULL
  - credit_amount: 3146.67
```

### 6.3 Why Two Tables?

**`installment_payments`** (Operational/Informational)
- Tracks payment plan progress
- Manages due dates and schedules
- Shows which installments are paid/pending
- Used for customer service and reminders

**`ar_subledger`** (Accounting/Financial)
- Records actual accounting impact
- Tracks receivables balances
- Used for financial reporting
- Integrated with GL posting

**Example Query - Get Package Payment Status:**
```sql
SELECT
  ppp.plan_id,
  ppp.total_amount,
  ppp.paid_amount,
  ppp.balance_amount,
  COUNT(ip.installment_id) as installments_paid,
  SUM(ip.amount) as total_paid_via_installments
FROM package_payment_plans ppp
LEFT JOIN installment_payments ip ON ppp.plan_id = ip.plan_id
WHERE ppp.patient_id = ?
GROUP BY ppp.plan_id;
```

---

## 7. Database Schema

### 7.1 Core Tables

**payment_details** (Main payment records)
```sql
CREATE TABLE payment_details (
  -- Primary Key
  payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References
  hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
  invoice_id UUID REFERENCES invoice_header(invoice_id),  -- NULL for multi-invoice
  patient_id UUID REFERENCES patients(patient_id),  -- Added for traceability
  branch_id UUID REFERENCES branches(branch_id),  -- Added for traceability

  -- Payment Information
  payment_date TIMESTAMP WITH TIME ZONE NOT NULL,
  payment_number VARCHAR(50) UNIQUE,  -- Auto-generated: PMT-YYYY-NNNNNN

  -- Payment Methods
  cash_amount NUMERIC(12,2) DEFAULT 0,
  credit_card_amount NUMERIC(12,2) DEFAULT 0,
  debit_card_amount NUMERIC(12,2) DEFAULT 0,
  upi_amount NUMERIC(12,2) DEFAULT 0,
  total_amount NUMERIC(12,2) NOT NULL,

  -- Payment Details
  card_number_last4 VARCHAR(4),
  card_type VARCHAR(20),
  upi_id VARCHAR(50),
  reference_number VARCHAR(50),

  -- Traceability (Added 2025-11-15)
  recorded_by VARCHAR(15) REFERENCES users(user_id),
  payment_source VARCHAR(20),  -- 'single_invoice', 'multi_invoice', 'package_installment'
  invoice_count INTEGER DEFAULT 1,
  advance_adjustment_amount NUMERIC(12,2),
  last_modified_by VARCHAR(15) REFERENCES users(user_id),
  last_modified_at TIMESTAMP WITH TIME ZONE,

  -- Workflow
  workflow_status VARCHAR(20) DEFAULT 'approved',
  requires_approval BOOLEAN DEFAULT FALSE,
  submitted_by VARCHAR(15) REFERENCES users(user_id),
  submitted_at TIMESTAMP WITH TIME ZONE,
  approved_by VARCHAR(15) REFERENCES users(user_id),
  approved_at TIMESTAMP WITH TIME ZONE,
  rejected_by VARCHAR(15) REFERENCES users(user_id),
  rejected_at TIMESTAMP WITH TIME ZONE,
  rejection_reason TEXT,

  -- GL Posting
  gl_posted BOOLEAN DEFAULT FALSE,
  posting_date TIMESTAMP WITH TIME ZONE,
  gl_entry_id UUID REFERENCES gl_transaction(transaction_id),

  -- Reversal
  is_reversed BOOLEAN DEFAULT FALSE,
  reversed_at TIMESTAMP WITH TIME ZONE,
  reversed_by VARCHAR(15),
  reversal_reason TEXT,
  reversal_gl_entry_id UUID REFERENCES gl_transaction(transaction_id),

  -- Bank Reconciliation
  bank_reconciled BOOLEAN DEFAULT FALSE,
  bank_reconciled_date TIMESTAMP WITH TIME ZONE,
  bank_reconciled_by VARCHAR(15) REFERENCES users(user_id),

  -- Soft Delete
  is_deleted BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMP WITH TIME ZONE,
  deleted_by VARCHAR(15),
  deletion_reason TEXT,

  -- Audit
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(15),
  updated_at TIMESTAMP WITH TIME ZONE,
  updated_by VARCHAR(15)
);

-- Indexes
CREATE INDEX idx_payment_details_patient ON payment_details(patient_id);
CREATE INDEX idx_payment_details_invoice ON payment_details(invoice_id);
CREATE INDEX idx_payment_details_date ON payment_details(payment_date);
CREATE INDEX idx_payment_details_status ON payment_details(workflow_status);
CREATE INDEX idx_payment_details_number ON payment_details(payment_number);
```

**ar_subledger** (Patient receivables tracking)
```sql
CREATE TABLE ar_subledger (
  -- Primary Key
  entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References
  hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
  branch_id UUID NOT NULL REFERENCES branches(branch_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),

  -- Entry Information
  entry_type VARCHAR(50) NOT NULL,  -- 'invoice', 'payment', 'package_installment'
  reference_id UUID NOT NULL,  -- invoice_id or payment_id
  reference_type VARCHAR(50) NOT NULL,  -- 'invoice' or 'payment'
  reference_number VARCHAR(50),
  reference_line_item_id UUID REFERENCES invoice_line_item(line_item_id),

  -- Amounts (Debit/Credit)
  debit_amount NUMERIC(12,2) DEFAULT 0,  -- Invoice creates debit (patient owes)
  credit_amount NUMERIC(12,2) DEFAULT 0,  -- Payment creates credit (patient paid)

  -- GL Integration
  gl_transaction_id UUID REFERENCES gl_transaction(transaction_id),

  -- Transaction Details
  transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
  description TEXT,

  -- Audit
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(15)
);

-- Indexes
CREATE INDEX idx_ar_patient ON ar_subledger(patient_id);
CREATE INDEX idx_ar_reference ON ar_subledger(reference_id, reference_type);
CREATE INDEX idx_ar_line_item ON ar_subledger(reference_line_item_id);
CREATE INDEX idx_ar_date ON ar_subledger(transaction_date);
```

**installment_payments** (Package installment tracking)
```sql
CREATE TABLE installment_payments (
  -- Primary Key
  installment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References
  plan_id UUID NOT NULL REFERENCES package_payment_plans(plan_id),
  payment_id UUID REFERENCES payment_details(payment_id),

  -- Installment Information
  installment_number INTEGER NOT NULL,
  due_date DATE,
  amount NUMERIC(12,2) NOT NULL,
  paid_date TIMESTAMP WITH TIME ZONE,
  status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'paid', 'overdue', 'cancelled'

  -- Audit
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(15),
  updated_at TIMESTAMP WITH TIME ZONE,
  updated_by VARCHAR(15),

  UNIQUE(plan_id, installment_number)
);
```

**package_payment_plans**
```sql
CREATE TABLE package_payment_plans (
  -- Primary Key
  plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- References
  hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
  patient_id UUID NOT NULL REFERENCES patients(patient_id),
  package_id UUID NOT NULL REFERENCES packages(package_id),

  -- Payment Plan Details
  total_amount NUMERIC(12,2) NOT NULL,
  paid_amount NUMERIC(12,2) DEFAULT 0,
  balance_amount NUMERIC(12,2) NOT NULL,

  -- Installment Configuration
  installment_frequency VARCHAR(20),  -- 'weekly', 'monthly', 'quarterly'
  number_of_installments INTEGER,
  start_date DATE,

  -- Plan Status
  status VARCHAR(20) DEFAULT 'active',  -- 'active', 'completed', 'cancelled'

  -- Audit
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(15)
);
```

### 7.2 Database Views

**v_patient_payment_receipts** (Main list view)
```sql
CREATE OR REPLACE VIEW v_patient_payment_receipts AS
SELECT
  -- Payment Details
  pd.payment_id,
  pd.hospital_id,
  pd.invoice_id,
  pd.patient_id,
  pd.branch_id,
  pd.payment_date,
  pd.payment_number,
  pd.total_amount,
  pd.cash_amount,
  pd.credit_card_amount,
  pd.debit_card_amount,
  pd.upi_amount,
  pd.workflow_status,
  pd.gl_posted,
  pd.payment_source,
  pd.invoice_count,
  pd.recorded_by,

  -- Patient Information
  TRIM(CONCAT_WS(' ', p.title, p.first_name, p.last_name)) as patient_name,
  p.mrn as patient_mrn,
  (p.contact_info->>'primary_phone') as patient_phone,
  (p.contact_info->>'email') as patient_email,
  p.is_active as patient_status,

  -- Invoice Information (for single invoice payments)
  ih.invoice_number,
  ih.invoice_date,
  ih.invoice_type,
  ih.grand_total as invoice_total,
  ih.paid_amount as invoice_paid_amount,
  ih.balance_due as invoice_balance_due,

  -- Branch Information
  b.branch_name,

  -- Hospital Information
  h.hospital_name,

  -- Payment Method (derived)
  CASE
    WHEN pd.cash_amount > 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0
      THEN 'Cash'
    WHEN pd.credit_card_amount > 0 AND pd.cash_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0
      THEN 'Credit Card'
    WHEN pd.debit_card_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.upi_amount = 0
      THEN 'Debit Card'
    WHEN pd.upi_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0
      THEN 'UPI'
    WHEN pd.advance_adjustment_amount > 0
      THEN 'Advance Adjustment'
    ELSE 'Multiple'
  END as payment_method_primary,

  -- Audit Fields
  pd.created_at,
  pd.created_by,
  pd.updated_at,
  pd.updated_by

FROM payment_details pd
LEFT JOIN patients p ON pd.patient_id = p.patient_id
LEFT JOIN invoice_header ih ON pd.invoice_id = ih.invoice_id
LEFT JOIN branches b ON pd.branch_id = b.branch_id
LEFT JOIN hospitals h ON pd.hospital_id = h.hospital_id
WHERE pd.is_deleted = FALSE;
```

---

## 8. Service Layer Architecture

### 8.1 Key Service Files

**File Structure:**
```
app/services/
├── billing_service.py          # Main payment recording logic
├── patient_payment_service.py  # Patient-specific payment operations
├── subledger_service.py        # AR subledger operations
├── gl_service.py               # GL transaction/entry creation
├── package_payment_service.py  # Package installment handling
└── patient_invoice_service.py  # Invoice operations
```

### 8.2 billing_service.py

**Primary Function:** `record_multi_invoice_payment()`

**Location:** `app/services/billing_service.py:2600-2865`

**Purpose:** Records payment across one or more invoices with line-item allocation

**Parameters:**
```python
def record_multi_invoice_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_allocations: List[Dict],  # [{'invoice_id': uuid, 'allocated_amount': Decimal}]
    payment_date: datetime,
    cash_amount: Decimal = Decimal('0'),
    credit_card_amount: Decimal = Decimal('0'),
    debit_card_amount: Decimal = Decimal('0'),
    upi_amount: Decimal = Decimal('0'),
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
    recorded_by: str = 'system',
    save_as_draft: bool = False,
    approval_threshold: Decimal = Decimal('10000'),
    session: Optional[Session] = None
) -> Dict:
```

**Key Logic Steps:**

1. **Validation**
```python
# Validate invoices exist and belong to patient
first_invoice = session.query(InvoiceHeader).filter_by(
    hospital_id=hospital_id,
    invoice_id=invoice_allocations[0]['invoice_id']
).first()

if not first_invoice:
    raise ValueError("Invoice not found")

if first_invoice.patient_id != patient_id:
    raise ValueError("Invoice does not belong to patient")
```

2. **Determine Workflow Status**
```python
total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount

if save_as_draft:
    workflow_status = 'draft'
    requires_approval = False
    should_post_gl = False
elif total_payment >= approval_threshold:
    workflow_status = 'pending_approval'
    requires_approval = True
    should_post_gl = False
else:
    workflow_status = 'approved'
    requires_approval = False
    should_post_gl = True
```

3. **Create Payment Record**
```python
payment = PaymentDetail(
    hospital_id=hospital_id,
    invoice_id=first_invoice.invoice_id if len(invoice_allocations) == 1 else None,
    payment_date=payment_date,
    cash_amount=cash_amount,
    credit_card_amount=credit_card_amount,
    debit_card_amount=debit_card_amount,
    upi_amount=upi_amount,
    total_amount=total_payment,
    reference_number=reference_number,
    notes=notes,
    workflow_status=workflow_status,
    requires_approval=requires_approval,
    gl_posted=False,
    is_deleted=False
)

session.add(payment)
session.flush()  # Get payment_id

# Populate traceability fields (Added 2025-11-15)
payment.patient_id = patient_id
payment.branch_id = first_invoice.branch_id
payment.payment_source = 'multi_invoice'
payment.invoice_count = len(invoice_allocations)
payment.recorded_by = recorded_by
```

4. **Post GL Entries (if auto-approved)**
```python
gl_transaction_id = None
if should_post_gl:
    try:
        from app.services.gl_service import create_multi_invoice_payment_gl_entries

        gl_result = create_multi_invoice_payment_gl_entries(
            payment_id=payment.payment_id,
            invoice_count=len(invoice_allocations),
            current_user_id=recorded_by,
            session=session
        )

        if gl_result and gl_result.get('success'):
            gl_transaction_id = gl_result.get('transaction_id')
    except Exception as e:
        logger.error(f"GL posting failed: {e}")
        gl_transaction_id = None
```

5. **Create AR Subledger Entries (ALWAYS, even for drafts)**
```python
# CRITICAL FIX: AR entries must ALWAYS be created, regardless of GL posting status
try:
    from app.services.subledger_service import create_ar_subledger_entry

    with session.no_autoflush:
        for alloc in invoice_allocations:
            invoice_id = alloc['invoice_id']
            allocated_amount_for_invoice = Decimal(str(alloc['allocated_amount']))

            # Get invoice line items with PAYMENT PRIORITY
            line_items = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.invoice_id == invoice_id
            ).order_by(
                case(
                    (InvoiceLineItem.item_type == 'Medicine', 1),  # Priority 1
                    (InvoiceLineItem.item_type == 'Service', 2),   # Priority 2
                    (InvoiceLineItem.item_type == 'Package', 3),   # Priority 3
                    else_=4
                ),
                InvoiceLineItem.line_item_id
            ).all()

            remaining_for_invoice = allocated_amount_for_invoice

            # Allocate payment across LINE ITEMS in priority order
            for line_item in line_items:
                if remaining_for_invoice <= 0:
                    break

                # Get current AR balance for this line item
                line_balance = get_line_item_ar_balance(
                    hospital_id=hospital_id,
                    patient_id=invoice.patient_id,
                    line_item_id=line_item.line_item_id,
                    session=session
                )

                if line_balance <= 0:
                    continue  # Already paid

                # Allocate to this line item
                allocated_to_line = min(line_balance, remaining_for_invoice)

                # Create AR credit entry for this LINE ITEM
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    entry_type='payment',
                    reference_id=payment.payment_id,
                    reference_type='payment',
                    reference_number=reference_number or f"PAY-{payment.payment_id}",
                    reference_line_item_id=line_item.line_item_id,
                    debit_amount=Decimal('0'),
                    credit_amount=allocated_to_line,
                    transaction_date=payment_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=recorded_by
                )

                remaining_for_invoice -= allocated_to_line

            # Update invoice paid amount and balance
            actual_allocated = allocated_amount_for_invoice - remaining_for_invoice
            invoice.paid_amount = (invoice.paid_amount or Decimal('0')) + actual_allocated
            invoice.balance_due = invoice.grand_total - invoice.paid_amount

except Exception as e:
    logger.error(f"Error creating AR subledger entries: {str(e)}")
    raise

return {
    'success': True,
    'payment_id': str(payment.payment_id),
    'total_amount': float(total_payment),
    'workflow_status': workflow_status,
    'requires_approval': requires_approval,
    'gl_posted': payment.gl_posted,
    'invoice_count': len(invoice_allocations),
    'allocations': allocation_results
}
```

### 8.3 subledger_service.py

**Primary Function:** `create_ar_subledger_entry()`

**Location:** `app/services/subledger_service.py`

**Purpose:** Creates individual AR subledger entries

```python
def create_ar_subledger_entry(
    session: Session,
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    entry_type: str,  # 'invoice', 'payment', 'package_installment'
    reference_id: uuid.UUID,
    reference_type: str,  # 'invoice', 'payment'
    reference_number: str,
    reference_line_item_id: Optional[uuid.UUID],
    debit_amount: Decimal,
    credit_amount: Decimal,
    transaction_date: datetime,
    gl_transaction_id: Optional[uuid.UUID],
    current_user_id: str,
    description: Optional[str] = None
) -> Dict:
    """
    Creates AR subledger entry

    Examples:
      Invoice: debit_amount > 0, credit_amount = 0 (patient owes)
      Payment: debit_amount = 0, credit_amount > 0 (patient paid)
    """

    entry = ARSubledger(
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        entry_type=entry_type,
        reference_id=reference_id,
        reference_type=reference_type,
        reference_number=reference_number,
        reference_line_item_id=reference_line_item_id,
        debit_amount=debit_amount,
        credit_amount=credit_amount,
        transaction_date=transaction_date,
        gl_transaction_id=gl_transaction_id,
        created_by=current_user_id,
        description=description
    )

    session.add(entry)

    return {
        'success': True,
        'entry_id': str(entry.entry_id)
    }
```

**Helper Function:** `get_line_item_ar_balance()`

```python
def get_line_item_ar_balance(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    line_item_id: uuid.UUID,
    session: Session
) -> Decimal:
    """
    Get AR balance for specific line item

    Returns:
      Positive = Patient owes (invoice > payments)
      Zero = Fully paid
      Negative = Overpaid
    """

    result = session.execute(text("""
        SELECT
          COALESCE(SUM(debit_amount), 0) - COALESCE(SUM(credit_amount), 0) as balance
        FROM ar_subledger
        WHERE hospital_id = :hospital_id
          AND patient_id = :patient_id
          AND reference_line_item_id = :line_item_id
    """), {
        'hospital_id': hospital_id,
        'patient_id': patient_id,
        'line_item_id': line_item_id
    }).first()

    return Decimal(str(result.balance)) if result else Decimal('0')
```

### 8.4 gl_service.py

**Primary Function:** `create_multi_invoice_payment_gl_entries()`

**Location:** `app/services/gl_service.py`

**Purpose:** Creates GL transaction and entries for multi-invoice payments

```python
def create_multi_invoice_payment_gl_entries(
    payment_id: uuid.UUID,
    invoice_count: int,
    current_user_id: str,
    session: Session
) -> Dict:
    """
    Create GL entries for multi-invoice payment

    Structure:
      Debit: Cash/Card/UPI accounts (assets increase)
      Credit: Accounts Receivable (assets decrease)
    """

    # Get payment details
    payment = session.query(PaymentDetail).filter_by(
        payment_id=payment_id
    ).first()

    if not payment:
        return {'success': False, 'error': 'Payment not found'}

    # Create GL Transaction
    gl_transaction = GLTransaction(
        hospital_id=payment.hospital_id,
        branch_id=payment.branch_id,
        transaction_date=payment.payment_date,
        transaction_type='payment_receipt',
        reference_id=str(payment.payment_id),
        reference_type='payment_receipt',
        description=f"Payment receipt from patient across {invoice_count} invoice(s)",
        total_debit=payment.total_amount,
        total_credit=payment.total_amount,
        created_by=current_user_id
    )

    session.add(gl_transaction)
    session.flush()

    entries = []

    # Debit entries for payment methods used
    if payment.cash_amount and payment.cash_amount > 0:
        cash_entry = GLEntry(
            transaction_id=gl_transaction.transaction_id,
            account_id=get_account_id('cash'),  # '1010-Cash'
            debit_amount=payment.cash_amount,
            credit_amount=Decimal('0'),
            description=f"Cash portion of payment {payment.payment_number}",
            created_by=current_user_id
        )
        entries.append(cash_entry)

    if payment.credit_card_amount and payment.credit_card_amount > 0:
        card_entry = GLEntry(
            transaction_id=gl_transaction.transaction_id,
            account_id=get_account_id('credit_card'),  # '1020-Credit Card'
            debit_amount=payment.credit_card_amount,
            credit_amount=Decimal('0'),
            description=f"Credit card portion of payment {payment.payment_number}",
            created_by=current_user_id
        )
        entries.append(card_entry)

    if payment.debit_card_amount and payment.debit_card_amount > 0:
        debit_entry = GLEntry(
            transaction_id=gl_transaction.transaction_id,
            account_id=get_account_id('debit_card'),  # '1020-Debit Card'
            debit_amount=payment.debit_card_amount,
            credit_amount=Decimal('0'),
            description=f"Debit card portion of payment {payment.payment_number}",
            created_by=current_user_id
        )
        entries.append(debit_entry)

    if payment.upi_amount and payment.upi_amount > 0:
        upi_entry = GLEntry(
            transaction_id=gl_transaction.transaction_id,
            account_id=get_account_id('upi'),  # '1025-UPI'
            debit_amount=payment.upi_amount,
            credit_amount=Decimal('0'),
            description=f"UPI portion of payment {payment.payment_number}",
            created_by=current_user_id
        )
        entries.append(upi_entry)

    # Credit entry for AR
    ar_entry = GLEntry(
        transaction_id=gl_transaction.transaction_id,
        account_id=get_account_id('accounts_receivable'),  # '1200-AR'
        debit_amount=Decimal('0'),
        credit_amount=payment.total_amount,
        description=f"AR payment across {invoice_count} invoice(s)",
        created_by=current_user_id
    )
    entries.append(ar_entry)

    # Add all entries
    for entry in entries:
        session.add(entry)

    # Update payment GL reference
    payment.gl_entry_id = gl_transaction.transaction_id
    payment.gl_posted = True
    payment.posting_date = datetime.now(timezone.utc)

    return {
        'success': True,
        'transaction_id': gl_transaction.transaction_id,
        'entries_count': len(entries)
    }
```

### 8.5 package_payment_service.py

**Primary Function:** `record_package_installment_payment()`

**Purpose:** Records payment that includes package installment

```python
def record_package_installment_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    plan_id: uuid.UUID,
    installment_amount: Decimal,
    invoice_allocations: List[Dict],  # Optional invoice payments
    payment_date: datetime,
    cash_amount: Decimal = Decimal('0'),
    credit_card_amount: Decimal = Decimal('0'),
    debit_card_amount: Decimal = Decimal('0'),
    upi_amount: Decimal = Decimal('0'),
    recorded_by: str = 'system',
    session: Optional[Session] = None
) -> Dict:
    """
    Records payment that includes package installment

    Total payment = invoice_allocations total + installment_amount

    Creates:
      1. Payment record in payment_details
      2. AR entries for invoice line items
      3. AR entry for package installment (reference_line_item_id = NULL)
      4. Installment payment record
      5. Update package payment plan paid_amount
      6. GL entries (if auto-approved)
    """

    total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount
    invoice_total = sum(Decimal(str(a['allocated_amount'])) for a in invoice_allocations)

    # Validate: invoice_total + installment_amount = total_payment
    if abs(invoice_total + installment_amount - total_payment) > Decimal('0.01'):
        raise ValueError("Payment allocation mismatch")

    # Get package payment plan
    plan = session.query(PackagePaymentPlan).filter_by(
        plan_id=plan_id
    ).first()

    if not plan:
        raise ValueError("Package payment plan not found")

    # Create payment record
    payment = PaymentDetail(
        hospital_id=hospital_id,
        invoice_id=None,  # Mixed payment type
        patient_id=patient_id,
        payment_date=payment_date,
        cash_amount=cash_amount,
        credit_card_amount=credit_card_amount,
        debit_card_amount=debit_card_amount,
        upi_amount=upi_amount,
        total_amount=total_payment,
        payment_source='package_installment',
        invoice_count=len(invoice_allocations),
        workflow_status='approved',  # Package payments auto-approved
        gl_posted=False
    )

    session.add(payment)
    session.flush()

    # Create AR entries for invoice line items
    for alloc in invoice_allocations:
        # ... (similar to multi_invoice_payment logic)
        pass

    # Create AR entry for package installment
    create_ar_subledger_entry(
        session=session,
        hospital_id=hospital_id,
        branch_id=plan.branch_id,
        patient_id=patient_id,
        entry_type='package_installment',
        reference_id=payment.payment_id,
        reference_type='payment',
        reference_number=f"PKG-{plan.plan_id}",
        reference_line_item_id=None,  # No specific line item
        debit_amount=Decimal('0'),
        credit_amount=installment_amount,
        transaction_date=payment_date,
        gl_transaction_id=None,  # Set after GL creation
        current_user_id=recorded_by,
        description=f"Package installment payment for plan {plan.plan_id}"
    )

    # Create installment payment record
    installment = InstallmentPayment(
        plan_id=plan_id,
        payment_id=payment.payment_id,
        installment_number=get_next_installment_number(plan_id, session),
        amount=installment_amount,
        paid_date=payment_date,
        status='paid'
    )

    session.add(installment)

    # Update package payment plan
    plan.paid_amount = (plan.paid_amount or Decimal('0')) + installment_amount
    plan.balance_amount = plan.total_amount - plan.paid_amount

    if plan.balance_amount <= Decimal('0'):
        plan.status = 'completed'

    # Create GL entries
    gl_result = create_multi_invoice_payment_gl_entries(
        payment_id=payment.payment_id,
        invoice_count=len(invoice_allocations) + 1,  # +1 for package
        current_user_id=recorded_by,
        session=session
    )

    return {
        'success': True,
        'payment_id': str(payment.payment_id),
        'installment_id': str(installment.installment_id),
        'total_amount': float(total_payment),
        'invoice_amount': float(invoice_total),
        'installment_amount': float(installment_amount)
    }
```

---

## 9. Configuration Files

### 9.1 patient_payment_config.py

**Location:** `app/config/modules/patient_payment_config.py`

**Purpose:** Universal Engine configuration for patient payments

**Key Components:**

1. **Field Definitions** (84 fields)
```python
PATIENT_PAYMENT_FIELDS = [
    FieldDefinition(
        name="payment_number",
        label="Payment Number",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        searchable=True,
        sortable=True,
        width="150px"
    ),
    # ... 83 more fields
]
```

2. **Tab Definitions**
```python
PATIENT_PAYMENT_TABS = {
    "payment_details": TabDefinition(...),
    "invoice_details": TabDefinition(...),
    "patient_info": TabDefinition(...),
    "workflow": TabDefinition(...),
    "payment_history": TabDefinition(...),
    "system_info": TabDefinition(...)
}
```

3. **View Layout**
```python
PATIENT_PAYMENT_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=PATIENT_PAYMENT_TABS,
    default_tab='payment_details',
    header_config={
        "primary_field": "payment_id",
        "title_field": "patient_name",
        "status_field": "workflow_status",
        "secondary_fields": [...]
    }
)
```

4. **Actions**
```python
PATIENT_PAYMENT_ACTIONS = [
    ActionDefinition(id="create", ...),
    ActionDefinition(id="edit", ...),
    ActionDefinition(id="approve", ...),
    ActionDefinition(id="reverse", ...),
    # ... more actions
]
```

5. **Main Configuration**
```python
PATIENT_PAYMENT_CONFIG = EntityConfiguration(
    entity_type="patient_payments",
    table_name="v_patient_payment_receipts",
    primary_key="payment_id",
    fields=PATIENT_PAYMENT_FIELDS,
    view_layout=PATIENT_PAYMENT_VIEW_LAYOUT,
    actions=PATIENT_PAYMENT_ACTIONS,
    # ... more config
)
```

### 9.2 Entity Registry

**Location:** `app/config/entity_registry.py`

```python
ENTITY_REGISTRY = {
    'patient_payments': {
        'config_module': 'app.config.modules.patient_payment_config',
        'config_class': 'PATIENT_PAYMENT_CONFIG',
        'service_module': 'app.services.patient_payment_service',
        'view_name': 'v_patient_payment_receipts',
        'primary_key': 'payment_id'
    }
}
```

---

## 10. Sample Transactions with Complete Entries

### Sample Transaction 1: Simple Single Invoice Payment

**Scenario:**
- Patient: John Doe (MRN: MRN-001)
- Invoice: INV-2025-001 (₹5,000)
  - Medicine: Facial Cream (₹1,500)
  - Service: Consultation (₹2,000)
  - Service: Laser Treatment (₹1,500)
- Payment: ₹5,000 (Cash)
- Workflow: Auto-approved (below threshold)

**Step 1: Create Payment**
```sql
INSERT INTO payment_details (
  payment_id, hospital_id, patient_id, branch_id, invoice_id,
  payment_date, payment_number, cash_amount, total_amount,
  payment_source, invoice_count, recorded_by,
  workflow_status, requires_approval, gl_posted
) VALUES (
  '11111111-1111-1111-1111-111111111111',
  '00000000-0000-0000-0000-000000000000',
  'patient-001-uuid',
  'branch-001-uuid',
  'invoice-001-uuid',
  '2025-11-15 10:30:00+05:30',
  'PMT-2025-000001',
  5000.00,
  5000.00,
  'single_invoice',
  1,
  'skinspire_Admin',
  'approved',
  FALSE,
  TRUE
);
```

**Step 2: Create AR Subledger Entries**
```sql
-- Entry 1: Medicine line item
INSERT INTO ar_subledger (
  entry_id, hospital_id, branch_id, patient_id,
  entry_type, reference_id, reference_type, reference_line_item_id,
  debit_amount, credit_amount, transaction_date, created_by
) VALUES (
  'ar-001-uuid', '00000000-0000-0000-0000-000000000000', 'branch-001-uuid', 'patient-001-uuid',
  'payment', '11111111-1111-1111-1111-111111111111', 'payment', 'line-item-001-uuid',
  0, 1500.00, '2025-11-15 10:30:00+05:30', 'skinspire_Admin'
);

-- Entry 2: Service line item (Consultation)
INSERT INTO ar_subledger (
  entry_id, hospital_id, branch_id, patient_id,
  entry_type, reference_id, reference_type, reference_line_item_id,
  debit_amount, credit_amount, transaction_date, created_by
) VALUES (
  'ar-002-uuid', '00000000-0000-0000-0000-000000000000', 'branch-001-uuid', 'patient-001-uuid',
  'payment', '11111111-1111-1111-1111-111111111111', 'payment', 'line-item-002-uuid',
  0, 2000.00, '2025-11-15 10:30:00+05:30', 'skinspire_Admin'
);

-- Entry 3: Service line item (Laser Treatment)
INSERT INTO ar_subledger (
  entry_id, hospital_id, branch_id, patient_id,
  entry_type, reference_id, reference_type, reference_line_item_id,
  debit_amount, credit_amount, transaction_date, created_by
) VALUES (
  'ar-003-uuid', '00000000-0000-0000-0000-000000000000', 'branch-001-uuid', 'patient-001-uuid',
  'payment', '11111111-1111-1111-1111-111111111111', 'payment', 'line-item-003-uuid',
  0, 1500.00, '2025-11-15 10:30:00+05:30', 'skinspire_Admin'
);

-- Total AR Credits: ₹5,000 ✓
```

**Step 3: Create GL Transaction**
```sql
INSERT INTO gl_transaction (
  transaction_id, hospital_id, branch_id, transaction_date,
  transaction_type, reference_id, reference_type,
  total_debit, total_credit, description, created_by
) VALUES (
  'gl-trans-001-uuid', '00000000-0000-0000-0000-000000000000', 'branch-001-uuid',
  '2025-11-15 10:30:00+05:30',
  'payment_receipt', '11111111-1111-1111-1111-111111111111', 'payment_receipt',
  5000.00, 5000.00,
  'Payment receipt PMT-2025-000001 from patient John Doe',
  'skinspire_Admin'
);
```

**Step 4: Create GL Entries**
```sql
-- Debit: Cash Account
INSERT INTO gl_entry (
  entry_id, transaction_id, account_id,
  debit_amount, credit_amount, description, created_by
) VALUES (
  'gl-entry-001-uuid', 'gl-trans-001-uuid', '1010',
  5000.00, 0,
  'Cash receipt for payment PMT-2025-000001',
  'skinspire_Admin'
);

-- Credit: Accounts Receivable
INSERT INTO gl_entry (
  entry_id, transaction_id, account_id,
  debit_amount, credit_amount, description, created_by
) VALUES (
  'gl-entry-002-uuid', 'gl-trans-001-uuid', '1200',
  0, 5000.00,
  'AR payment for invoice INV-2025-001',
  'skinspire_Admin'
);

-- GL Balance: Debits (₹5,000) = Credits (₹5,000) ✓
```

**Step 5: Update AR Entries with GL Transaction ID**
```sql
UPDATE ar_subledger
SET gl_transaction_id = 'gl-trans-001-uuid'
WHERE reference_id = '11111111-1111-1111-1111-111111111111'
  AND reference_type = 'payment';
```

**Step 6: Update Invoice**
```sql
UPDATE invoice_header
SET
  paid_amount = 5000.00,
  balance_due = grand_total - 5000.00,
  payment_status = CASE
    WHEN grand_total - 5000.00 = 0 THEN 'paid'
    ELSE 'partially_paid'
  END
WHERE invoice_id = 'invoice-001-uuid';
```

**Final State:**

| Table | Records | Total Amount |
|-------|---------|--------------|
| payment_details | 1 | ₹5,000 |
| ar_subledger | 3 | ₹5,000 (credits) |
| gl_transaction | 1 | ₹5,000 (balanced) |
| gl_entry | 2 | ₹5,000 debit, ₹5,000 credit |
| invoice_header | 1 updated | paid_amount=₹5,000 |

---

### Sample Transaction 2: Multi-Invoice Payment

**Scenario:**
- Patient: Jane Smith (MRN: MRN-002)
- Invoice 1: INV-2025-002 (₹3,000, Balance: ₹3,000)
- Invoice 2: INV-2025-003 (₹4,500, Balance: ₹4,500)
- Invoice 3: INV-2025-004 (₹6,000, Balance: ₹6,000)
- Payment: ₹10,000 (Credit Card: ₹6,000 + UPI: ₹4,000)
- Allocation:
  - Invoice 1: ₹3,000 (full payment)
  - Invoice 2: ₹4,500 (full payment)
  - Invoice 3: ₹2,500 (partial payment)
- Workflow: Auto-approved

**Step 1: Create Payment**
```sql
INSERT INTO payment_details (
  payment_id, hospital_id, patient_id, branch_id,
  invoice_id,  -- NULL for multi-invoice
  payment_date, payment_number,
  credit_card_amount, upi_amount, total_amount,
  payment_source, invoice_count, recorded_by,
  workflow_status, gl_posted
) VALUES (
  '22222222-2222-2222-2222-222222222222',
  '00000000-0000-0000-0000-000000000000',
  'patient-002-uuid',
  'branch-001-uuid',
  NULL,  -- ✅ Multi-invoice payment
  '2025-11-15 14:00:00+05:30',
  'PMT-2025-000002',
  6000.00, 4000.00, 10000.00,
  'multi_invoice',
  3,  -- ✅ Paying 3 invoices
  'skinspire_Admin',
  'approved',
  TRUE
);
```

**Step 2: Create AR Subledger Entries**

*Invoice 1 (INV-2025-002): ₹3,000*
```sql
-- Assume Invoice 1 has 2 line items: Medicine (₹1,000), Service (₹2,000)

INSERT INTO ar_subledger VALUES
  ('ar-201-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-201-uuid', 0, 1000.00, ...),  -- Medicine
  ('ar-202-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-202-uuid', 0, 2000.00, ...);  -- Service
```

*Invoice 2 (INV-2025-003): ₹4,500*
```sql
-- Assume Invoice 2 has 3 line items

INSERT INTO ar_subledger VALUES
  ('ar-203-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-203-uuid', 0, 1500.00, ...),  -- Medicine
  ('ar-204-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-204-uuid', 0, 2000.00, ...),  -- Service
  ('ar-205-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-205-uuid', 0, 1000.00, ...);  -- Package
```

*Invoice 3 (INV-2025-004): ₹2,500 (partial)*
```sql
-- Assume Invoice 3 has 4 line items totaling ₹6,000, but only ₹2,500 paid
-- Allocation follows priority: Medicine → Service → Package

INSERT INTO ar_subledger VALUES
  ('ar-206-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-206-uuid', 0, 800.00, ...),   -- Medicine (fully paid)
  ('ar-207-uuid', ..., 'payment', '22222222-2222-2222-2222-222222222222', 'payment',
   'line-item-207-uuid', 0, 1700.00, ...);  -- Service (fully paid)
  -- Remaining line items not paid yet
```

**Total AR Credits: ₹10,000** ✓
- Invoice 1: ₹3,000
- Invoice 2: ₹4,500
- Invoice 3: ₹2,500

**Step 3: Create GL Transaction**
```sql
INSERT INTO gl_transaction VALUES (
  'gl-trans-002-uuid', ...,
  'payment_receipt', '22222222-2222-2222-2222-222222222222', 'payment_receipt',
  10000.00, 10000.00,
  'Payment receipt PMT-2025-000002 across 3 invoices',
  'skinspire_Admin'
);
```

**Step 4: Create GL Entries**
```sql
-- Debit: Credit Card
INSERT INTO gl_entry VALUES (
  'gl-entry-201-uuid', 'gl-trans-002-uuid', '1020',
  6000.00, 0, 'Credit card payment', 'skinspire_Admin'
);

-- Debit: UPI
INSERT INTO gl_entry VALUES (
  'gl-entry-202-uuid', 'gl-trans-002-uuid', '1025',
  4000.00, 0, 'UPI payment', 'skinspire_Admin'
);

-- Credit: AR
INSERT INTO gl_entry VALUES (
  'gl-entry-203-uuid', 'gl-trans-002-uuid', '1200',
  0, 10000.00, 'AR payment across 3 invoices', 'skinspire_Admin'
);

-- GL Balance: Debits (₹10,000) = Credits (₹10,000) ✓
```

**Step 5: Update Invoices**
```sql
-- Invoice 1: Fully paid
UPDATE invoice_header
SET paid_amount = 3000.00, balance_due = 0, payment_status = 'paid'
WHERE invoice_id = 'invoice-002-uuid';

-- Invoice 2: Fully paid
UPDATE invoice_header
SET paid_amount = 4500.00, balance_due = 0, payment_status = 'paid'
WHERE invoice_id = 'invoice-003-uuid';

-- Invoice 3: Partially paid
UPDATE invoice_header
SET paid_amount = 2500.00, balance_due = 3500.00, payment_status = 'partially_paid'
WHERE invoice_id = 'invoice-004-uuid';
```

**Final State:**

| Table | Records | Total Amount |
|-------|---------|--------------|
| payment_details | 1 | ₹10,000 |
| ar_subledger | 7 | ₹10,000 (credits) |
| gl_transaction | 1 | ₹10,000 (balanced) |
| gl_entry | 3 | Debit: ₹10,000, Credit: ₹10,000 |
| invoice_header | 3 updated | INV-002: paid, INV-003: paid, INV-004: partial |

---

### Sample Transaction 3: Package Installment Payment (Real Example)

**Scenario:**
- Patient: Patient-a8580b45 (from actual system)
- Payment Number: PMT-2025-000104
- Total Payment: ₹10,646.67
- Payment Methods:
  - Cash: ₹5,646.67
  - Credit Card: ₹5,000.00
- Breakdown:
  - Invoice Payments: ₹7,500.00 across 2 invoices
  - Package Installment: ₹3,146.67 (for Advanced Skin Treatment plan)

**Invoice Details:**
- Invoice 1 (GST/2025-2026/00004): ₹4,852.16
  - Medicine: Facial Sheet Masks (₹94.40)
  - Service: Doctor's Examination (₹37.76)
  - Service: Laser Hair Removal (₹2,950.00)
  - Package: Basic Facial Package (₹1,770.00, partial payment ₹917.84)
- Invoice 2 (NGS/2025-2026/00002): ₹3,500.00
  - Package: Advanced Skin Treatment (₹3,500.00, full payment)

**Package Payment Plan:**
- Plan ID: 4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf
- Package: Advanced Skin Treatment (₹9,440 total)
- Previously Paid: ₹0
- This Payment: ₹3,146.67
- Remaining Balance: ₹6,293.33

**Step 1: Create Payment**
```sql
INSERT INTO payment_details (
  payment_id,
  hospital_id,
  patient_id,
  branch_id,
  invoice_id,  -- NULL for mixed payment
  payment_date,
  payment_number,
  cash_amount,
  credit_card_amount,
  total_amount,
  payment_source,
  invoice_count,
  recorded_by,
  workflow_status,
  gl_posted
) VALUES (
  '3b90a765-0957-49c3-b3d5-e0f5afee30e1',
  '00000000-0000-0000-0000-000000000000',
  'a8580b45-0833-4d2d-ab04-c15268b5f8c1',
  '2ebc5166-d5d4-4d20-b164-d6ed6aa3251b',
  NULL,  -- ✅ Mixed: invoices + package
  '2025-11-15 00:00:00+05:30',
  'PMT-2025-000104',
  5646.67,
  5000.00,
  10646.67,
  'multi_invoice',  -- Could also be 'package_installment'
  2,
  'skinspire_Admin',
  'approved',
  TRUE
);
```

**Step 2: Create AR Subledger Entries**

*Invoice Line Items (₹7,500.00):*
```sql
-- Invoice 1, Line 1: Medicine - Facial Sheet Masks
INSERT INTO ar_subledger (
  entry_id, ...,
  entry_type, reference_id, reference_type,
  reference_line_item_id,
  credit_amount, ...
) VALUES (
  '1e4bea3d-4a15-414d-8ed5-cac93859819f',
  ...,
  'payment', '3b90a765-0957-49c3-b3d5-e0f5afee30e1', 'payment',
  'e8b13711-af69-445a-ab80-0f0e50d07cbe',
  94.40, ...
);

-- Invoice 1, Line 2: Service - Doctor's Examination
INSERT INTO ar_subledger VALUES (
  '5a08ef42-d394-4f44-9cfa-f0f4c6411d42', ...,
  'payment', '3b90a765-0957-49c3-b3d5-e0f5afee30e1', 'payment',
  '437a3258-c0bf-4b19-b8d3-b926365dc7cd',
  37.76, ...
);

-- Invoice 1, Line 3: Service - Laser Hair Removal
INSERT INTO ar_subledger VALUES (
  '9dadd4f1-01c6-4fd4-a839-028ac650bde0', ...,
  'payment', '3b90a765-0957-49c3-b3d5-e0f5afee30e1', 'payment',
  '592be8de-50f4-45de-901d-79557ef30126',
  2950.00, ...
);

-- Invoice 1, Line 4: Package - Basic Facial (PARTIAL)
INSERT INTO ar_subledger VALUES (
  'd4fd2dca-5e08-4f24-93b1-2fd7b45b91be', ...,
  'payment', '3b90a765-0957-49c3-b3d5-e0f5afee30e1', 'payment',
  '4dd436a3-fff9-46de-9a34-c1b784508be2',
  917.84, ...  -- Partial: ₹917.84 of ₹1,770 total
);

-- Invoice 2, Line 1: Package - Advanced Skin Treatment
INSERT INTO ar_subledger VALUES (
  '3c2f9d3e-ad71-441e-8e78-b101875d9d03', ...,
  'payment', '3b90a765-0957-49c3-b3d5-e0f5afee30e1', 'payment',
  'ea917b3b-1ec6-4453-846c-34a18579f573',
  3500.00, ...
);

-- Subtotal Invoice Payments: ₹7,500.00
```

*Package Installment (₹3,146.67):*
```sql
INSERT INTO ar_subledger (
  entry_id, ...,
  entry_type, reference_id, reference_type,
  reference_line_item_id,  -- ✅ NULL for package installment
  credit_amount,
  description, ...
) VALUES (
  'ar-package-installment-uuid',
  ...,
  'package_installment',
  '3b90a765-0957-49c3-b3d5-e0f5afee30e1',
  'payment',
  NULL,  -- ✅ No specific line item for installment
  3146.67,
  'Package installment for plan 4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf',
  ...
);

-- Total AR Credits: ₹10,646.67 ✓
-- (₹7,500 invoice + ₹3,146.67 installment)
```

**Step 3: Create Installment Payment Record**
```sql
INSERT INTO installment_payments (
  installment_id,
  plan_id,
  payment_id,
  installment_number,
  amount,
  paid_date,
  status,
  created_by
) VALUES (
  '4f302fe7-1ac5-49ad-84ac-1f6011275427',
  '4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf',
  '3b90a765-0957-49c3-b3d5-e0f5afee30e1',
  1,  -- First installment
  3146.67,
  '2025-11-15 00:00:00+05:30',
  'paid',
  'skinspire_Admin'
);
```

**Step 4: Update Package Payment Plan**
```sql
UPDATE package_payment_plans
SET
  paid_amount = 0 + 3146.67,  -- ₹3,146.67
  balance_amount = 9440.00 - 3146.67,  -- ₹6,293.33
  updated_at = CURRENT_TIMESTAMP,
  updated_by = 'skinspire_Admin'
WHERE plan_id = '4fe17378-2f6a-4c7d-8f58-cc5614e0a9bf';
```

**Step 5: Create GL Transaction**
```sql
INSERT INTO gl_transaction (
  transaction_id,
  hospital_id,
  branch_id,
  transaction_date,
  transaction_type,
  reference_id,
  reference_type,
  total_debit,
  total_credit,
  description,
  created_by
) VALUES (
  '0e658430-4155-45cc-a4d2-1ba9152ec791',
  '00000000-0000-0000-0000-000000000000',
  '2ebc5166-d5d4-4d20-b164-d6ed6aa3251b',
  '2025-11-15 00:00:00+05:30',
  'payment_receipt',
  '3b90a765-0957-49c3-b3d5-e0f5afee30e1',
  'payment_receipt',
  10646.67,
  10646.67,
  'Payment receipt PMT-2025-000104 (2 invoices + package installment)',
  'skinspire_Admin'
);
```

**Step 6: Create GL Entries**
```sql
-- Debit: Cash
INSERT INTO gl_entry VALUES (
  'gl-entry-cash-uuid',
  '0e658430-4155-45cc-a4d2-1ba9152ec791',
  '1010',  -- Cash account
  5646.67,
  0,
  'Cash portion of PMT-2025-000104',
  'skinspire_Admin'
);

-- Debit: Credit Card
INSERT INTO gl_entry VALUES (
  'gl-entry-card-uuid',
  '0e658430-4155-45cc-a4d2-1ba9152ec791',
  '1020',  -- Credit Card account
  5000.00,
  0,
  'Credit card portion of PMT-2025-000104',
  'skinspire_Admin'
);

-- Credit: Accounts Receivable
INSERT INTO gl_entry VALUES (
  'gl-entry-ar-uuid',
  '0e658430-4155-45cc-a4d2-1ba9152ec791',
  '1200',  -- AR account
  0,
  10646.67,
  'AR payment: 2 invoices + package installment',
  'skinspire_Admin'
);

-- GL Balance Check:
-- Total Debits: ₹5,646.67 + ₹5,000.00 = ₹10,646.67
-- Total Credits: ₹10,646.67
-- ✅ BALANCED
```

**Step 7: Update AR Entries with GL Transaction ID**
```sql
UPDATE ar_subledger
SET gl_transaction_id = '0e658430-4155-45cc-a4d2-1ba9152ec791'
WHERE reference_id = '3b90a765-0957-49c3-b3d5-e0f5afee30e1'
  AND reference_type = 'payment';

-- All 6 AR entries now linked to GL transaction
```

**Step 8: Update Invoices**
```sql
-- Invoice 1 (GST/2025-2026/00004): Partially paid
UPDATE invoice_header
SET
  paid_amount = (paid_amount OR 0) + 4000.00,
  balance_due = grand_total - paid_amount,
  payment_status = 'partially_paid'
WHERE invoice_id = '5b07ea5f-ce05-4e10-9570-d78fd4db5087';

-- Invoice 2 (NGS/2025-2026/00002): Fully paid
UPDATE invoice_header
SET
  paid_amount = 3500.00,
  balance_due = 0,
  payment_status = 'paid'
WHERE invoice_id = '6aa464f7-d290-4914-82b6-6cb7989bb901';
```

**Final State:**

| Table | Records | Amount | Details |
|-------|---------|--------|---------|
| payment_details | 1 | ₹10,646.67 | Cash + Credit Card |
| ar_subledger | **6** | ₹10,646.67 | 5 invoice items + 1 installment |
| installment_payments | 1 | ₹3,146.67 | Informational tracking |
| package_payment_plans | 1 updated | Paid: ₹3,146.67 | Balance: ₹6,293.33 |
| gl_transaction | 1 | ₹10,646.67 | Balanced |
| gl_entry | 3 | Debits: ₹10,646.67<br>Credits: ₹10,646.67 | Cash + Card → AR |
| invoice_header | 2 updated | INV-1: Partial<br>INV-2: Paid | Balances updated |

**Verification Queries:**

```sql
-- 1. Check AR balance equals payment
SELECT SUM(credit_amount) as total_ar_credits
FROM ar_subledger
WHERE reference_id = '3b90a765-0957-49c3-b3d5-e0f5afee30e1'
  AND reference_type = 'payment';
-- Result: ₹10,646.67 ✓

-- 2. Check GL is balanced
SELECT
  SUM(debit_amount) as total_debits,
  SUM(credit_amount) as total_credits
FROM gl_entry
WHERE transaction_id = '0e658430-4155-45cc-a4d2-1ba9152ec791';
-- Result: Debits ₹10,646.67, Credits ₹10,646.67 ✓

-- 3. Check payment breakdown
SELECT
  SUM(CASE WHEN reference_line_item_id IS NOT NULL THEN credit_amount ELSE 0 END) as invoice_payments,
  SUM(CASE WHEN reference_line_item_id IS NULL THEN credit_amount ELSE 0 END) as package_payments
FROM ar_subledger
WHERE reference_id = '3b90a765-0957-49c3-b3d5-e0f5afee30e1';
-- Result: Invoice ₹7,500, Package ₹3,146.67 ✓
```

---

## 11. Workflow and Approval Process

### 11.1 Workflow States

```
draft
  ↓ (Submit)
pending_approval
  ↓ (Approve)         ↓ (Reject)
approved            rejected
  ↓ (Reverse)
reversed
```

### 11.2 State Transitions

**Draft → Pending Approval**
- Trigger: User clicks "Submit for Approval"
- Actions:
  - Set workflow_status = 'pending_approval'
  - Set submitted_by = current_user
  - Set submitted_at = current_timestamp
  - AR entries: Already created (in draft state)
  - GL entries: NOT created yet

**Pending Approval → Approved**
- Trigger: Authorized user approves
- Actions:
  - Set workflow_status = 'approved'
  - Set approved_by = current_user
  - Set approved_at = current_timestamp
  - Create GL transaction and entries
  - Update AR entries with gl_transaction_id
  - Set gl_posted = TRUE

**Pending Approval → Rejected**
- Trigger: Authorized user rejects
- Actions:
  - Set workflow_status = 'rejected'
  - Set rejected_by = current_user
  - Set rejected_at = current_timestamp
  - Set rejection_reason = user input
  - AR entries remain (for audit trail)
  - No GL entries created

**Approved → Reversed**
- Trigger: Authorized user reverses payment
- Actions:
  - Set workflow_status = 'reversed'
  - Set is_reversed = TRUE
  - Set reversed_by = current_user
  - Set reversed_at = current_timestamp
  - Create reversal GL transaction (opposite entries)
  - Create reversal AR entries (opposite amounts)
  - Update invoice balances

### 11.3 Approval Threshold Logic

```python
# In record_multi_invoice_payment()

total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount

if save_as_draft:
    workflow_status = 'draft'
    requires_approval = False
    should_post_gl = False

elif total_payment >= approval_threshold:
    workflow_status = 'pending_approval'
    requires_approval = True
    should_post_gl = False

else:
    # Auto-approve small payments
    workflow_status = 'approved'
    requires_approval = False
    should_post_gl = True
```

**Default Approval Threshold:** ₹10,000

**Example:**
- Payment ₹5,000: Auto-approved, GL posted immediately
- Payment ₹15,000: Pending approval, GL posted after approval
- Payment ₹50,000 (draft): Draft, no GL until submitted and approved

---

## 12. Integration Points

### 12.1 Invoice Integration

**When Invoice is Created:**
```python
# In patient_invoice_service.py

def create_patient_invoice(...):
    # 1. Create invoice_header
    invoice = InvoiceHeader(...)
    session.add(invoice)
    session.flush()

    # 2. Create invoice_line_item records
    for item in line_items:
        line_item = InvoiceLineItem(...)
        session.add(line_item)
        session.flush()

        # 3. Create AR debit entry (patient owes)
        create_ar_subledger_entry(
            entry_type='invoice',
            reference_id=invoice.invoice_id,
            reference_type='invoice',
            reference_line_item_id=line_item.line_item_id,
            debit_amount=line_item.line_total,  # Debit AR
            credit_amount=Decimal('0'),
            ...
        )

    # 4. Update invoice totals
    invoice.grand_total = sum(item.line_total for item in line_items)
    invoice.balance_due = invoice.grand_total
```

**Invoice Status Updates:**
```python
def update_invoice_payment_status(invoice_id, session):
    invoice = session.query(InvoiceHeader).filter_by(
        invoice_id=invoice_id
    ).first()

    # Calculate paid amount from AR
    paid = session.execute(text("""
        SELECT COALESCE(SUM(credit_amount), 0) as paid
        FROM ar_subledger ar
        JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
        WHERE ili.invoice_id = :invoice_id
          AND ar.reference_type = 'payment'
    """), {'invoice_id': invoice_id}).first()

    invoice.paid_amount = paid.paid
    invoice.balance_due = invoice.grand_total - invoice.paid_amount

    # Update status
    if invoice.balance_due <= 0:
        invoice.payment_status = 'paid'
    elif invoice.paid_amount > 0:
        invoice.payment_status = 'partially_paid'
    else:
        invoice.payment_status = 'unpaid'
```

### 12.2 Package Integration

**Package Purchase Creates Payment Plan:**
```python
def create_package_payment_plan(
    patient_id,
    package_id,
    total_amount,
    installment_frequency='monthly',
    number_of_installments=3
):
    plan = PackagePaymentPlan(
        patient_id=patient_id,
        package_id=package_id,
        total_amount=total_amount,
        paid_amount=Decimal('0'),
        balance_amount=total_amount,
        installment_frequency=installment_frequency,
        number_of_installments=number_of_installments,
        status='active'
    )

    session.add(plan)
    session.flush()

    # Optional: Auto-generate installment schedule
    installment_amount = total_amount / number_of_installments

    for i in range(1, number_of_installments + 1):
        installment = InstallmentPayment(
            plan_id=plan.plan_id,
            installment_number=i,
            amount=installment_amount,
            due_date=calculate_due_date(i, installment_frequency),
            status='pending'
        )
        session.add(installment)

    return plan
```

**Package Payment Links to Payment:**
```python
# When payment is recorded
installment = session.query(InstallmentPayment).filter_by(
    plan_id=plan_id,
    installment_number=next_number,
    status='pending'
).first()

installment.payment_id = payment.payment_id
installment.paid_date = payment.payment_date
installment.status = 'paid'
```

### 12.3 GL Integration

**Account Mapping:**
```python
# From gl_service.py

ACCOUNT_MAPPING = {
    'cash': '1010',                    # Cash Account
    'credit_card': '1020',             # Credit Card Account
    'debit_card': '1020',              # Debit Card Account
    'upi': '1025',                     # UPI Account
    'accounts_receivable': '1200',     # AR Account
    'revenue_service': '4010',         # Service Revenue
    'revenue_medicine': '4020',        # Medicine Revenue
    'revenue_package': '4030'          # Package Revenue
}
```

**GL Transaction Types:**
```python
TRANSACTION_TYPES = {
    'payment_receipt': {
        'debit_accounts': ['cash', 'credit_card', 'debit_card', 'upi'],
        'credit_accounts': ['accounts_receivable']
    },
    'payment_reversal': {
        'debit_accounts': ['accounts_receivable'],
        'credit_accounts': ['cash', 'credit_card', 'debit_card', 'upi']
    },
    'invoice_revenue': {
        'debit_accounts': ['accounts_receivable'],
        'credit_accounts': ['revenue_service', 'revenue_medicine', 'revenue_package']
    }
}
```

---

## 13. Key Business Rules

### 13.1 Payment Allocation Rules

1. **Line-Item Priority:**
   - Medicine items paid first (highest priority)
   - Service items paid second
   - Package items paid last (lowest priority)

2. **Partial Payment Allocation:**
   - If payment < invoice total, allocate by priority
   - Track which specific line items are paid
   - Invoice remains "partially_paid" status

3. **Multi-Invoice Allocation:**
   - User specifies allocation per invoice
   - System allocates at line-item level within each invoice
   - Total payment must equal sum of allocations

### 13.2 AR Recording Rules

1. **Always Create AR:**
   - AR entries created for ALL payments (draft, pending, approved)
   - AR tracks customer liability regardless of GL posting
   - Enables accurate aging and collection reports

2. **Line-Item Granularity:**
   - Each AR entry links to specific line_item_id
   - Exception: Package installments have NULL line_item_id
   - Enables detailed payment tracking

3. **Invoice vs Payment Perspective:**
   - Invoice creates AR Debit (patient owes)
   - Payment creates AR Credit (patient paid)
   - Balance = Debits - Credits

### 13.3 GL Posting Rules

1. **Conditional GL Posting:**
   - Draft payments: NO GL
   - Pending approval: NO GL
   - Approved: YES GL
   - Ensures financial statements only show approved transactions

2. **Double-Entry Requirement:**
   - Total debits must equal total credits
   - System validates before committing
   - Prevents unbalanced entries

3. **GL-AR Linkage:**
   - AR entries store gl_transaction_id
   - Links subledger to general ledger
   - Enables reconciliation

### 13.4 Package Payment Rules

1. **Dual Tracking:**
   - `installment_payments`: Operational tracking
   - `ar_subledger`: Financial tracking
   - Both must be updated for package payments

2. **Plan Status:**
   - Active: balance_amount > 0
   - Completed: balance_amount = 0
   - Cancelled: user-initiated cancellation

3. **Installment Flexibility:**
   - Pre-defined schedule (recommended)
   - Ad-hoc payments allowed
   - Overpayment creates credit balance

### 13.5 Workflow Rules

1. **Approval Requirements:**
   - Amount >= threshold: Requires approval
   - Amount < threshold: Auto-approved
   - Draft: No approval until submitted

2. **Reversal Requirements:**
   - Only approved payments can be reversed
   - Reversal creates opposite GL entries
   - Original payment remains for audit trail

3. **Edit/Delete Rules:**
   - Draft/Rejected: Can edit or delete
   - Pending Approval: Cannot edit (must approve/reject first)
   - Approved: Cannot edit or delete (must reverse)

---

## Conclusion

The Patient Payment System in SkinSpire HMS is a sophisticated financial management module that handles complex payment scenarios while maintaining accounting integrity through double-entry bookkeeping and detailed audit trails.

**Key Takeaways:**

1. **Many-to-Many Architecture:** AR subledger enables flexible payment-invoice relationships
2. **Line-Item Tracking:** Granular allocation ensures accurate payment tracking
3. **Dual Recording:** AR (always) + GL (conditional) provides both operational and financial views
4. **Package Integration:** Seamless handling of installment payments alongside invoice payments
5. **Workflow Control:** Approval process ensures proper authorization
6. **Complete Audit Trail:** Every transaction fully traceable

**For Developers:**

- Always create AR entries, regardless of GL posting
- Follow payment priority when allocating (Medicine → Service → Package)
- Ensure GL entries are balanced before committing
- Link AR entries to GL transactions for reconciliation
- Handle package installments separately but include in AR

**For Business Users:**

- Payment can cover multiple invoices in one transaction
- Package installments tracked separately but appear in AR
- Draft payments allow saving work without financial impact
- Approval workflow ensures proper oversight
- Complete payment history visible through AR subledger

---

**Document Version History:**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-15 | Initial comprehensive guide | System Documentation |
| 2.0 | 2025-11-15 | Added package installment details, sample transactions, bug fixes | System Documentation |

---

**Related Documents:**

- `Patient_Invoice_System_Guide.md`
- `Package_Management_System_Guide.md`
- `GL_Accounting_System_Guide.md`
- `Universal_Engine_Configuration_Guide.md`

---

**Support:**

For questions or clarifications, refer to:
- Service files in `app/services/`
- Configuration in `app/config/modules/patient_payment_config.py`
- Database schema in `app/database/view scripts/`
