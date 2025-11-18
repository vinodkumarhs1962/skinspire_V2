# Phase 1 Complete: Database Schema for Split Invoice Tracking

**Date Completed**: 2025-01-06
**Status**: ✅ Complete - Ready for Migration

## Overview

Phase 1 has successfully extended the database schema to support split invoice tracking for the new medicine batch allocation and invoice splitting workflow.

## Completed Tasks

### 1. ✅ Database Migration Script Created
**File**: `migrations/add_split_invoice_tracking.sql`

Added four new fields to `invoice_header` table:
- `parent_transaction_id` (UUID) - Links to parent invoice when split
- `split_sequence` (INTEGER) - Order of split invoices (1, 2, 3...)
- `is_split_invoice` (BOOLEAN) - Flag indicating this is part of a split
- `split_reason` (VARCHAR(100)) - Reason for split (BATCH_ALLOCATION, GST_SPLIT, PRESCRIPTION_CONSOLIDATION)

**Features**:
- Self-referencing foreign key constraint
- Indexes for efficient querying of related invoices
- Column comments for documentation
- Verification query included

### 2. ✅ InvoiceHeader Model Updated
**File**: `app/models/transaction.py` (lines 460-464)

Added fields to InvoiceHeader class:
```python
# Split Invoice Tracking (for batch allocation, GST split, etc.)
parent_transaction_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
split_sequence = Column(Integer, default=1)
is_split_invoice = Column(Boolean, default=False)
split_reason = Column(String(100))  # BATCH_ALLOCATION, GST_SPLIT, PRESCRIPTION_CONSOLIDATION
```

Added relationships (lines 481-484):
```python
# Split invoice relationships
parent_invoice = relationship("InvoiceHeader", remote_side=[invoice_id],
                               foreign_keys=[parent_transaction_id],
                               backref=backref("child_invoices", lazy="dynamic"))
```

### 3. ✅ Patient Invoices View Updated
**File**: `app/database/view scripts/patient invoices view v2.0.sql`

Created v2.0 of patient_invoices_view with:
- All split invoice tracking fields from header
- Parent invoice information (number, date, grand_total)
- Child invoice aggregation (count, total)
- Updated search_text to include parent invoice number
- Left join to parent invoice for context

**New Columns in View**:
```sql
-- Direct fields
parent_transaction_id
split_sequence
is_split_invoice
split_reason

-- Parent invoice context
parent_invoice_number
parent_invoice_date
parent_grand_total

-- Child invoice aggregation
split_invoice_count
split_invoices_total
```

### 4. ✅ PatientInvoiceView Model Updated
**File**: `app/models/views.py` (lines 503-516)

Added all new columns to the SQLAlchemy view model:
```python
# Split Invoice Tracking (NEW in v2.0)
parent_transaction_id = Column(PostgresUUID(as_uuid=True))
split_sequence = Column(Integer)
is_split_invoice = Column(Boolean)
split_reason = Column(String(100))

# Parent invoice information
parent_invoice_number = Column(String(50))
parent_invoice_date = Column(DateTime(timezone=True))
parent_grand_total = Column(Numeric(12, 2))

# Child invoice aggregation
split_invoice_count = Column(Integer)
split_invoices_total = Column(Numeric(12, 2))
```

### 5. ✅ FIFO Service Verified
**File**: `app/services/inventory_service.py` (lines 694-797)

Existing FIFO batch selection service verified:
- Function: `get_batch_selection_for_invoice()`
- Implements FIFO based on expiry date
- Handles multi-batch allocation
- Returns batch, expiry, quantity, unit_price, sale_price

**Potential Enhancement Needed**:
Add GST rate, MRP, and HSN/SAC code to return data (for Phase 2 - FIFO modal display)

## Migration Instructions

### Step 1: Run Database Migration
```bash
# Connect to your PostgreSQL database
psql -U username -d skinspire_dev

# Run the migration
\i migrations/add_split_invoice_tracking.sql

# Expected output:
# ALTER TABLE
# ALTER TABLE
# ALTER TABLE
# ALTER TABLE
# CREATE INDEX
# CREATE INDEX
# COMMENT
# COMMENT
# COMMENT
```

### Step 2: Update Database View
```bash
# Run the view update script
\i "app/database/view scripts/patient invoices view v2.0.sql"

# Expected output:
# DROP VIEW
# CREATE VIEW
# (Multiple CREATE INDEX statements)
# GRANT
```

### Step 3: Verify Migration
```sql
-- Verify new columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'invoice_header'
  AND column_name IN ('parent_transaction_id', 'split_sequence', 'is_split_invoice', 'split_reason')
ORDER BY column_name;

-- Verify view columns
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'patient_invoices_view'
AND column_name IN (
    'parent_transaction_id', 'split_sequence', 'is_split_invoice', 'split_reason',
    'parent_invoice_number', 'split_invoice_count', 'split_invoices_total'
)
ORDER BY column_name;
```

### Step 4: Restart Application
```bash
# Models have been updated, restart Flask application
# to load the new schema definitions
python run.py
```

## Usage Scenarios

### Single Invoice (No Split)
```python
invoice = {
    'is_split_invoice': False,
    'parent_transaction_id': None,
    'split_sequence': 1,
    'split_reason': None
}
# Query: split_invoice_count = 0
```

### Parent Invoice (Has Children)
```python
parent_invoice = {
    'is_split_invoice': False,  # Parent is NOT itself a split
    'parent_transaction_id': None,
    'split_sequence': 1,
    'split_reason': None
}
# Query: split_invoice_count > 0
# Query: split_invoices_total = sum of child grand_totals
```

### Child Split Invoice
```python
child_invoice = {
    'is_split_invoice': True,
    'parent_transaction_id': '<parent_invoice_id>',
    'split_sequence': 1,  # or 2, 3, 4...
    'split_reason': 'BATCH_ALLOCATION'  # or GST_SPLIT, PRESCRIPTION_CONSOLIDATION
}
```

## Split Reason Codes

Standard codes for `split_reason` field:
- `BATCH_ALLOCATION` - Invoice split due to multiple batches for medicine
- `GST_SPLIT` - Invoice split to separate GST and non-GST items
- `PRESCRIPTION_CONSOLIDATION` - Prescription items consolidated separately
- `INTERSTATE_GST` - Split due to interstate vs intrastate GST

## Database Indexes

Indexes created for optimal query performance:
1. `idx_invoice_parent_transaction` - Find all child invoices of a parent
2. `idx_invoice_is_split` - Find all split invoices

Existing indexes continue to work:
- `idx_ih_hospital_id`, `idx_ih_branch_id`, `idx_ih_patient_id`
- `idx_ih_invoice_date`, `idx_ih_invoice_number`
- `idx_ih_invoice_type`, `idx_ih_is_cancelled`

## Next Phase: Phase 2 - FIFO Allocation Modal

**Upcoming Tasks**:
1. Create FIFO allocation modal component (`app/static/js/components/fifo_allocation_modal.js`)
2. Add API endpoint for FIFO batch preview (`/invoice/web_api/medicine/{id}/fifo-allocation`)
3. Enhance invoice_item.js to trigger modal on Enter key
4. Display batch breakdown with edit capabilities
5. Update invoice.js form submission to handle multi-batch line items

**Estimated Timeline**: Week 2 (7-10 days)

## Notes

- All changes are backward compatible
- Existing invoices will have `is_split_invoice=FALSE` and `parent_transaction_id=NULL`
- No data migration required for existing records
- Views automatically show correct values for old invoices (split_invoice_count=0, etc.)
- Model changes are automatically picked up by SQLAlchemy ORM

## Testing Checklist

After migration, verify:
- [ ] Migration script runs without errors
- [ ] View script runs without errors
- [ ] Application starts without errors
- [ ] Existing invoices display correctly in list view
- [ ] Existing invoice detail view shows no errors
- [ ] New fields appear as NULL/FALSE/0 for existing invoices

## Files Modified Summary

**Database**:
- ✅ `migrations/add_split_invoice_tracking.sql` (NEW)
- ✅ `app/database/view scripts/patient invoices view v2.0.sql` (NEW)

**Models**:
- ✅ `app/models/transaction.py` (InvoiceHeader class - lines 460-464, 481-484)
- ✅ `app/models/views.py` (PatientInvoiceView class - lines 503-516)

**Documentation**:
- ✅ This file: `Project_docs/billing_migration/PHASE_1_DATABASE_SCHEMA_COMPLETE.md`

---

**Phase 1 Status**: ✅ COMPLETE - Ready for migration and Phase 2 development
