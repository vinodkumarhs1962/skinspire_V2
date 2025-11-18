# Prescription Item Breakdown Implementation - Complete
**Date:** 2025-11-08
**Status:** ✅ Core Implementation Complete - Ready for Testing

## Overview
Successfully implemented a system to store prescription items individually in the database while supporting conditional consolidated printing based on hospital drug license status. This ensures full data preservation, audit compliance, and flexible display formats.

---

## Problem Statement
Previously, when a hospital lacked pharmacy registration, prescription items were physically consolidated into a single "Doctor's Examination and Treatment" line item in the database, losing individual medicine details permanently.

## Solution Implemented
**Database Storage:** Individual prescription items with consolidation flags
**Print Logic:** Hospital drug license determines display format
**Detail View:** Always shows complete breakdown
**Document Storage:** PDF snapshots preserve exact printed format

---

## Business Logic - Inventory Tracking

**CRITICAL: Prescription drug inventory is ALWAYS tracked regardless of pharmacy license status.**

### Pharmacy License ONLY Affects Display Format:

| Aspect | WITH Pharmacy License | WITHOUT Pharmacy License |
|--------|----------------------|-------------------------|
| **Storage** | Individual line items in DB | Individual line items in DB |
| **Print Format** | Individual medicines with batch/expiry | Consolidated "Doctor's Examination & Treatment" |
| **Detail View** | Individual items in main table | Individual items + Breakdown section |
| **Inventory Tracking** | ✅ Yes (batch, expiry, stock) | ✅ Yes (batch, expiry, stock) |
| **Stock Validation** | ✅ Required | ✅ Required |
| **Batch Validation** | ✅ Required | ✅ Required |
| **Expiry Validation** | ✅ Required | ✅ Required |

### Inventory Validation (Same for ALL Prescription Items):
```python
def _update_prescription_inventory():
    # Validates for EVERY prescription item:
    ✅ Batch number must be provided
    ✅ Batch must exist in inventory
    ✅ Sufficient stock available (raises error if insufficient)
    ✅ Expiry date must exist
    ✅ FIFO allocation applied
    ✅ Stock deducted and tracked in Inventory table
```

**Reason:** Prescription drugs are physical inventory that must be tracked for:
- Stock management and reordering
- Batch tracking for recalls
- Expiry date monitoring
- Audit compliance
- Cost accounting

**Pharmacy License Impact:** ONLY changes how the patient invoice is printed/billed, NOT how inventory is managed internally.

---

## Implementation Details

### Phase 1: Database Schema ✅

#### Migration: `add_prescription_consolidation_flags.sql`
Added 3 new columns to `invoice_line_item` table:

| Column | Type | Purpose |
|--------|------|---------|
| `is_prescription_item` | BOOLEAN | Marks PRESCRIPTION_COMPOSITE category items |
| `consolidation_group_id` | UUID | Groups items for consolidated printing |
| `print_as_consolidated` | BOOLEAN | Snapshot: hospital drug license at creation |

**Status:** ✅ Applied to database
**Indexes:** Created for performance on prescription queries

#### Migration: `create_invoice_documents_table.sql`
Created `invoice_documents` table for PDF storage:

**Key Fields:**
- Document metadata: type, category, status
- File information: path, size, mime_type
- Version control: parent_document_id, version_number
- Snapshot metadata: hospital_had_drug_license, prescription_items_count, consolidated_prescription
- Access tracking: last_accessed_at, access_count

**Status:** ✅ Table created with indexes and triggers

---

### Phase 2: Service Logic ✅

#### File: `app/services/billing_service.py`

**Changes:**
1. **Removed** `_consolidate_prescription_items()` function
2. **Updated** `_create_invoice()` to flag items instead of consolidating:
   ```python
   # Without drug license:
   for item in prescription_items:
       item['is_prescription_item'] = True
       item['consolidation_group_id'] = <same UUID for all Rx items>
       item['print_as_consolidated'] = True

   # Call inventory validation (ALWAYS, regardless of license)
   _update_prescription_inventory(session, hospital_id, prescription_items, ...)

   # With drug license:
   for item in prescription_items:
       item['is_prescription_item'] = True
       item['print_as_consolidated'] = False
   ```

3. **Added** `_update_prescription_inventory()` with full validation:
   - ✅ Validates batch number exists in inventory
   - ✅ Validates sufficient stock available
   - ✅ Validates expiry date exists
   - ✅ Creates inventory transaction with stock deduction
   - ✅ Raises ValueError with clear message if validation fails

4. **Updated** `_process_invoice_line_item()` to pass through flags
5. **Updated** `InvoiceLineItem` creation to save consolidation fields

**Result:** Prescription items stored individually with metadata flags + inventory tracking

---

### Phase 3: Display Logic ✅

#### File: `app/services/patient_invoice_service.py`

**Method:** `get_invoice_lines()`

**Enhancements:**
- Added prescription consolidation flags to each line item dict
- Added batch and expiry date to item display
- Calculated `consolidated_groups` metadata:
  ```python
  consolidated_groups = {
      '<group_id>': {
          'group_id': '<uuid>',
          'item_count': 3,
          'total_amount': 225.00,
          'print_as_consolidated': True,
          'items': [<item1>, <item2>, <item3>]
      }
  }
  ```

**Return Value:**
```python
{
    'items': [...],  # All line items with flags
    'consolidated_groups': {...},  # Grouped prescription items
    'has_consolidated_groups': bool
}
```

---

### Phase 4: Templates ✅

#### File: `app/templates/engine/business/universal_line_items_table.html`

**Detail View Enhancements:**

1. **Visual Indicators:**
   - Yellow highlighting for consolidated prescription items
   - "Consolidated" badge on each item
   - Warning color left border

2. **Breakdown Section:**
   - New card showing "Prescription Item Breakdown"
   - Table listing all individual medicines:
     - Medicine name, batch, expiry, qty, rate, total
   - Group total calculation
   - Print format indicator: "Prints as: Doctor's Examination and Treatment"

**Example Display:**
```
┌─ Prescription Item Breakdown ─────────────────────┐
│ Note: Items stored individually but print as      │
│ "Doctor's Examination and Treatment"              │
│                                                     │
│ Consolidated Group (3 items) - Total: ₹225.00     │
│ ┌──────────────────────────────────────────┐      │
│ │ 1. Aspirin 100mg    BATCH-001  15-Jan-25 │      │
│ │    Qty: 10  @₹5.00 = ₹50.00               │      │
│ │ 2. Paracetamol      BATCH-002  20-Feb-25  │      │
│ │    Qty: 20  @₹2.00 = ₹40.00               │      │
│ │ 3. Ibuprofen        BATCH-003  10-Mar-25  │      │
│ │    Qty: 15  @₹9.00 = ₹135.00              │      │
│ └──────────────────────────────────────────┘      │
│ Prints as: Doctor's Examination - ₹225.00         │
└────────────────────────────────────────────────────┘
```

#### File: `app/templates/billing/print_invoice.html`

**Print Logic:**

1. **Categorization** (lines 144-172):
   ```python
   # Group items by consolidation status
   - service_items: []
   - medicine_items: []
   - consolidated_groups: {group_id: {items, total}}
   ```

2. **Conditional Display** (lines 314-351):
   - **WITH drug license:** Prescription items in "Medicines" table
   - **WITHOUT drug license:** New section "Doctor's Examination and Treatment"

   ```html
   Doctor's Examination and Treatment
   ───────────────────────────────────────
   1. Doctor's Examination and Treatment
      Includes: 3 prescription medicine(s)
      Qty: 1    Amount: ₹225.00

   Note: GST exempted as per medical consultation services
   ```

---

### Phase 5: Document Storage Model ✅

#### File: `app/models/transaction.py`

**Model:** `InvoiceDocument`

**Purpose:** Store generated invoice PDFs for audit compliance

**Key Features:**
- Links to `invoice_id`
- Stores file_path, file_size, mime_type
- Version control (parent_document_id, version_number)
- **Snapshot metadata:**
  - `hospital_had_drug_license`: Drug license status at generation
  - `prescription_items_count`: Count of Rx items
  - `consolidated_prescription`: Whether consolidated in this print
- Access tracking (last_accessed_at, access_count)

**Relationships:**
```python
# InvoiceHeader
documents = relationship("InvoiceDocument", back_populates="invoice")

# InvoiceDocument
invoice = relationship("InvoiceHeader", back_populates="documents")
parent_document = relationship("InvoiceDocument")  # For versions
```

---

## Data Flow

### Invoice Creation (WITHOUT Drug License)

```
User creates invoice with 3 prescription items
           ↓
billing_service.py: _create_invoice()
  - Check hospital pharmacy registration: FALSE
  - Generate consolidation_group_id: <UUID>
  - Flag each prescription item:
      • is_prescription_item = TRUE
      • consolidation_group_id = <UUID>
      • print_as_consolidated = TRUE
           ↓
Database: 3 INDIVIDUAL line_item records saved
  ┌────────────────────────────────────────────┐
  │ Line Item 1: Aspirin                       │
  │   is_prescription_item: true               │
  │   consolidation_group_id: abc-123          │
  │   print_as_consolidated: true              │
  ├────────────────────────────────────────────┤
  │ Line Item 2: Paracetamol                   │
  │   is_prescription_item: true               │
  │   consolidation_group_id: abc-123          │
  │   print_as_consolidated: true              │
  ├────────────────────────────────────────────┤
  │ Line Item 3: Ibuprofen                     │
  │   is_prescription_item: true               │
  │   consolidation_group_id: abc-123          │
  │   print_as_consolidated: true              │
  └────────────────────────────────────────────┘
           ↓
Detail View (Universal Engine):
  - Shows ALL 3 items in main table (yellow highlighted)
  - Shows "Prescription Breakdown" card below
           ↓
Print View:
  - Checks print_as_consolidated flag
  - Groups by consolidation_group_id
  - Displays as:
    "Doctor's Examination and Treatment - ₹225"
```

### Invoice Creation (WITH Drug License)

```
User creates invoice with 3 prescription items
           ↓
billing_service.py: _create_invoice()
  - Check hospital pharmacy registration: TRUE
  - Flag each prescription item:
      • is_prescription_item = TRUE
      • print_as_consolidated = FALSE
           ↓
Database: 3 INDIVIDUAL line_item records saved
           ↓
Detail View:
  - Shows ALL 3 items in main table
  - NO consolidation badge
  - NO breakdown section
           ↓
Print View:
  - Checks print_as_consolidated flag: FALSE
  - Shows in "Medicines & Prescriptions" table:
    1. Aspirin - Batch-001 - Exp: 15-Jan-25 - ₹50
    2. Paracetamol - Batch-002 - Exp: 20-Feb-25 - ₹40
    3. Ibuprofen - Batch-003 - Exp: 10-Mar-25 - ₹135
```

---

## Benefits

### ✅ Data Integrity
- All prescription items stored individually
- Complete medicine details preserved
- Batch and expiry information retained
- Can query on specific medicines

### ✅ Regulatory Compliance
- Hospital drug license status controls display
- WITHOUT license: Prints as "Doctor's Examination" (compliant)
- WITH license: Prints individual medicines (compliant)
- Snapshot flags preserve original print format

### ✅ Audit Trail
- Full breakdown always visible in system
- Can trace exact medicines dispensed
- Document storage records what was printed
- Version control for revised invoices

### ✅ Flexible Reporting
- Query: "All invoices containing Drug X"
- Query: "Invoices with consolidated prescriptions"
- Query: "Prescription usage by medicine"
- All possible even when printed consolidated

### ✅ Future-Proof
- If hospital gets license later, can change print format
- Existing data remains intact
- No data migration needed
- Historical invoices remain accurate

---

## Files Modified

### Database
1. ✅ `migrations/add_prescription_consolidation_flags.sql`
2. ✅ `migrations/create_invoice_documents_table.sql`

### Models
3. ✅ `app/models/transaction.py`
   - Updated `InvoiceLineItem` (3 new fields)
   - Added `InvoiceDocument` model
   - Updated `InvoiceHeader` relationships

### Services
4. ✅ `app/services/billing_service.py`
   - Refactored `_create_invoice()` (flagging instead of consolidation)
   - Updated `_process_invoice_line_item()` (pass through flags)
   - Removed `_consolidate_prescription_items()` function

5. ✅ `app/services/patient_invoice_service.py`
   - Enhanced `get_invoice_lines()` (added grouping metadata)

### Templates
6. ✅ `app/templates/engine/business/universal_line_items_table.html`
   - Added visual indicators for consolidated items
   - Added "Prescription Item Breakdown" section
   - Added CSS styling

7. ✅ `app/templates/billing/print_invoice.html`
   - Added consolidated prescription categorization logic
   - Added "Doctor's Examination and Treatment" section
   - Conditional rendering based on `print_as_consolidated` flag

---

## Testing Requirements

### Test Case 1: Hospital WITHOUT Drug License ⏳
**Steps:**
1. Set hospital pharmacy_registration_number = NULL
2. Create invoice with 3 prescription medicines
3. Verify database:
   - 3 individual line_item records exist
   - All have `is_prescription_item = TRUE`
   - All share same `consolidation_group_id`
   - All have `print_as_consolidated = TRUE`
4. Check detail view:
   - All 3 items visible in main table
   - Yellow highlighting applied
   - "Consolidated" badge shown
   - Breakdown section displays below
5. Check print view:
   - Consolidated as "Doctor's Examination and Treatment"
   - Shows total ₹225
   - Note about GST exemption

**Expected Result:** Items stored individually, printed consolidated

### Test Case 2: Hospital WITH Drug License ⏳
**Steps:**
1. Set valid pharmacy_registration_number
2. Create invoice with 3 prescription medicines
3. Verify database:
   - 3 individual line_item records exist
   - All have `is_prescription_item = TRUE`
   - All have `print_as_consolidated = FALSE`
4. Check detail view:
   - All 3 items visible
   - No consolidation indicators
5. Check print view:
   - Shows in "Medicines & Prescriptions" table
   - Each medicine listed individually
   - Batch, expiry shown

**Expected Result:** Items stored and printed individually

### Test Case 3: Mixed Invoice ⏳
**Steps:**
1. Hospital WITHOUT drug license
2. Create invoice with:
   - 2 Services
   - 3 Prescription medicines
   - 2 OTC medicines
3. Verify categorization:
   - Services in service_items
   - OTC in medicine_items
   - Prescriptions flagged and grouped
4. Check print:
   - Services table
   - Medicines table (OTC only)
   - Doctor's Examination section (Rx only)

**Expected Result:** Correct categorization and display

---

## Phase 6: PDF Generation Service ✅

**File:** `app/services/invoice_document_service.py`

**Status:** ✅ COMPLETE

**Implementation:**

1. **PDF Generation** using WeasyPrint:
   ```python
   def _render_invoice_pdf(invoice_id, hospital_id, session) -> bytes:
       """
       Render invoice as PDF using existing print template
       - Retrieves invoice with relationships
       - Gets hospital and branch information
       - Renders print_invoice.html template
       - Converts HTML to PDF using WeasyPrint
       Returns: PDF bytes
       """
   ```

2. **Document Storage**:
   ```python
   def generate_and_store_invoice_pdf(invoice_id, hospital_id, user_id, trigger) -> InvoiceDocument:
       """
       Generate PDF and store in database with snapshot metadata
       - Generates PDF from template
       - Saves to filesystem: static/invoice_documents/YYYY/MM/<hospital_id>/
       - Creates InvoiceDocument record with metadata
       - Tracks drug license status, prescription count, consolidation flag
       Returns: InvoiceDocument record
       """
   ```

3. **Version Control**:
   ```python
   def regenerate_invoice_pdf(invoice_id, hospital_id, user_id, reason) -> InvoiceDocument:
       """
       Regenerate PDF and mark previous version as superseded
       - Marks existing document status as 'superseded'
       - Generates new version with incremented version_number
       - Links to parent document via parent_document_id
       Returns: New InvoiceDocument
       """
   ```

**File Storage Structure:**
```
static/invoice_documents/
  └── 2025/
      └── 01/
          └── <hospital_id>/
              └── INV-ABC-001-20250108_143052_a1b2c3d4.pdf
```

**Filename Pattern:** `INV-{invoice_number}_{timestamp}_{uuid8}.pdf`

**Integration Points:**
- Ready to integrate with invoice creation workflow
- Can be called manually for regeneration
- Supports audit trail with version history

---

## Summary

✅ **Database:** Individual storage with flags
✅ **Service Layer:** Flagging logic instead of consolidation
✅ **Detail View:** Complete breakdown always visible
✅ **Print Template:** Conditional rendering based on flags
✅ **Document Storage:** Model and service complete with PDF generation

🔜 **Remaining:** Integration with invoice creation + Testing

---

## Contact / Support
For questions about this implementation, refer to:
- This document
- Code comments in modified files
- Git history for change rationale
