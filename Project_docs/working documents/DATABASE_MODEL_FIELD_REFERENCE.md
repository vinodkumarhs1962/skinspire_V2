# Database Model Field Reference

**Quick reference for actual database model field names**
**Always check this before writing queries!**

---

## Invoice Models

### InvoiceHeader (`invoice_header` table)

**Primary Keys:**
- `invoice_id` - UUID

**Basic Fields:**
- `invoice_number` - String(50)
- `invoice_date` - DateTime(timezone=True)
- `invoice_type` - String(50) - Service, Product, Prescription, Misc
- `is_gst_invoice` - Boolean

**Patient Reference:**
- `patient_id` - UUID FK

**Amounts:**
- `total_amount` - Numeric(12,2) - Gross total
- `total_discount` - Numeric(12,2)
- `total_taxable_value` - Numeric(12,2)
- `total_cgst_amount` - Numeric(12,2)
- `total_sgst_amount` - Numeric(12,2)
- `total_igst_amount` - Numeric(12,2)
- `grand_total` - Numeric(12,2) - Final amount with tax
- `paid_amount` - Numeric(12,2)
- `balance_due` - Numeric(12,2)

**Status Fields:**
- `is_cancelled` - Boolean
- `cancellation_reason` - String(255)
- `cancelled_at` - DateTime

**⚠️ CRITICAL: InvoiceHeader has NO SoftDelete fields!**
- ❌ NO `is_deleted` column
- ❌ NO `deleted_at` column
- ❌ NO `deleted_by` column
- InvoiceHeader uses `TimestampMixin, TenantMixin` (NO SoftDeleteMixin)
- Use `is_cancelled` for marking invoices as cancelled

**⚠️ NO `status` COLUMN!**
Status must be computed:
```python
case(
    (InvoiceHeader.is_cancelled == True, 'cancelled'),
    (InvoiceHeader.balance_due == 0, 'paid'),
    (InvoiceHeader.paid_amount > 0, 'partial'),
    else_='pending'
)
```

---

### InvoiceLineItem (`invoice_line_item` table)

**Primary Keys:**
- `line_item_id` - UUID

**References:**
- `invoice_id` - UUID FK
- `package_id` - UUID FK (nullable)
- `service_id` - UUID FK (nullable)
- `medicine_id` - UUID FK (nullable)

**Item Details:**
- `item_type` - String(20) - Package, Service, Medicine
- `item_name` - String(100)
- `hsn_sac_code` - String(10)

**Quantities and Amounts:**
- `quantity` - Numeric(10,2)
- `unit_price` - Numeric(12,2)
- `discount_percent` - Numeric(5,2)
- `discount_amount` - Numeric(12,2)
- `taxable_amount` - Numeric(12,2)

**GST:**
- `gst_rate` - Numeric(5,2)
- `cgst_rate` - Numeric(5,2)
- `sgst_rate` - Numeric(5,2)
- `igst_rate` - Numeric(5,2)
- `cgst_amount` - Numeric(12,2)
- `sgst_amount` - Numeric(12,2)
- `igst_amount` - Numeric(12,2)
- `total_gst_amount` - Numeric(12,2)

**Line Total:**
- `line_total` - Numeric(12,2) ✅ **USE THIS, NOT `total`**

**⚠️ NO `total` COLUMN! Use `line_total` instead**

---

## Package Models

### Package (`packages` table)

**Primary Keys:**
- `package_id` - UUID

**Basic Fields:**
- `package_name` - String(100)
- `price` - Numeric(10,2) - Base price excluding GST
- `currency_code` - String(3)

**GST:**
- `gst_rate` - Numeric(5,2)
- `cgst_rate` - Numeric(5,2)
- `sgst_rate` - Numeric(5,2)
- `igst_rate` - Numeric(5,2)
- `is_gst_exempt` - Boolean

**Status:**
- `status` - String(20) - active/discontinued
- `is_deleted` - Boolean

---

## Patient Model

### Patient (`patients` table)

**Primary Keys:**
- `patient_id` - UUID

**Basic Fields:**
- `mrn` - String(20)
- `first_name` - String(100)
- `last_name` - String(100)
- `full_name` - String(200) ✅ **USE THIS, NOT `patient_name`**

**⚠️ NO `patient_name` COLUMN! Use `full_name` instead**

**JSONB Fields:**
- `personal_info` - JSONB
  - Access: `(personal_info->>'date_of_birth')::DATE`
  - Access: `(personal_info->>'gender')::VARCHAR`
- `contact_info` - JSONB
  - Access: `(contact_info->>'phone')::VARCHAR`
  - Access: `(contact_info->>'email')::VARCHAR`

---

## Package Payment Plan Models

### PackagePaymentPlan (`package_payment_plans` table)

**Primary Keys:**
- `plan_id` - UUID

**References:**
- `patient_id` - UUID FK
- `invoice_id` - UUID FK
- `package_id` - UUID FK

**Session Fields:**
- `total_sessions` - Integer
- `completed_sessions` - Integer
- `remaining_sessions` - Integer (GENERATED COLUMN)

**Financial Fields:**
- `total_amount` - Numeric(12,2)
- `paid_amount` - Numeric(12,2)
- `balance_amount` - Numeric(12,2) (GENERATED COLUMN)

**Installment Config:**
- `installment_count` - Integer
- `installment_frequency` - String(20) - weekly, biweekly, monthly
- `first_installment_date` - Date

**Status:**
- `status` - String(20) - active, completed, cancelled, suspended
- `is_deleted` - Boolean

---

### InstallmentPayment (`installment_payments` table)

**Primary Keys:**
- `installment_id` - UUID

**References:**
- `plan_id` - UUID FK

**Details:**
- `installment_number` - Integer
- `due_date` - Date
- `amount` - Numeric(12,2)
- `paid_amount` - Numeric(12,2)
- `balance_amount` - Numeric(12,2) (GENERATED COLUMN)
- `status` - String(20) - pending, partial, paid, overdue

---

### PackageSession (`package_sessions` table)

**Primary Keys:**
- `session_id` - UUID

**References:**
- `plan_id` - UUID FK

**Details:**
- `session_number` - Integer
- `session_date` - Date ✅ **USE THIS, NOT `scheduled_date`**
- `session_status` - String(20) - scheduled, completed, cancelled, no_show

**⚠️ NO `scheduled_date` COLUMN! Use `session_date` instead**

---

## Hospital & Branch Models

### Hospital (`hospitals` table)

**Primary Keys:**
- `hospital_id` - UUID

**Basic Fields:**
- `name` - String(100) ✅ **USE THIS, NOT `hospital_name`**
- `license_no` - String(50)

**⚠️ NO `hospital_name` COLUMN! Use `name` instead**

---

### Branch (`branches` table)

**Primary Keys:**
- `branch_id` - UUID

**Basic Fields:**
- `name` - String(100) ✅ **USE THIS, NOT `branch_name`**

**⚠️ NO `branch_name` COLUMN! Use `name` instead**

---

## Common Patterns

### Computing Invoice Status
```python
from sqlalchemy import case

invoice_status = case(
    (InvoiceHeader.is_cancelled == True, 'cancelled'),
    (InvoiceHeader.balance_due == 0, 'paid'),
    (InvoiceHeader.paid_amount > 0, 'partial'),
    else_='pending'
).label('invoice_status')
```

### Accessing JSONB Fields
```python
# Patient phone
(Patient.contact_info->>'phone')::VARCHAR

# Patient date of birth
(Patient.personal_info->>'date_of_birth')::DATE

# Patient gender
(Patient.personal_info->>'gender')::VARCHAR
```

### Query Example with Correct Fields
```python
query = session.query(
    InvoiceHeader.invoice_id,
    InvoiceHeader.invoice_number,
    InvoiceHeader.invoice_date,
    InvoiceLineItem.line_total,  # ✅ NOT 'total'
    Package.package_name,
    Package.price,
    Patient.full_name  # ✅ NOT 'patient_name'
).join(...)
```

---

## Quick Checklist Before Writing Queries

✅ **ALWAYS check model definitions in:**
- `app/models/transaction.py` - Invoice, Payment models
- `app/models/master.py` - Patient, Package, Hospital, Branch models
- `app/models/views.py` - Database view models

✅ **Common mistakes to avoid:**
- ❌ `InvoiceHeader.status` → Use computed case expression
- ❌ `InvoiceHeader.is_deleted` → InvoiceHeader has NO is_deleted (no SoftDeleteMixin)
- ❌ `InvoiceLineItem.total` → Use `InvoiceLineItem.line_total`
- ❌ `Patient.patient_name` → Use `Patient.full_name`
- ❌ `Hospital.hospital_name` → Use `Hospital.name`
- ❌ `Branch.branch_name` → Use `Branch.name`
- ❌ `PackageSession.scheduled_date` → Use `PackageSession.session_date`

---

**Always verify field names against the actual model before writing queries!**
