# Phase 3: Invoice Splitting Implementation

**Date**: 2025-01-07 00:30
**Status**: 🚧 In Progress

---

## Overview

Phase 3 implements 4-way invoice splitting for tax compliance. A single patient transaction is split into 4 separate auditable tax documents based on item type and GST status.

## Invoice Categories

### 1. Service & Package Invoice (Prefix: `SVC`)
- **Item Types**: Service, Package
- **GST Status**: Both GST and non-GST allowed
- **Serial Number**: Separate sequence per financial year

### 2. GST Medicines/Products Invoice (Prefix: `MED`)
- **Item Types**: OTC, Product, Consumable, Medicine
- **GST Status**: GST applicable only
- **Serial Number**: Separate sequence per financial year

### 3. GST Exempt Medicines Invoice (Prefix: `EXM`)
- **Item Types**: OTC, Product, Consumable, Medicine
- **GST Status**: GST exempt only
- **Serial Number**: Separate sequence per financial year

### 4. Prescription/Composite Invoice (Prefix: `RX`)
- **Item Types**: Prescription
- **Consolidation Logic**:
  - **With pharmacy registration**: Individual line items printed
  - **Without pharmacy registration**: Consolidate to "Doctor's Examination" (single line)
- **Serial Number**: Separate sequence per financial year

## Implementation Changes

### Files Modified

1. **`app/config/core_definitions.py`** (Lines 217-258)
   - Added `InvoiceSplitCategory` enum
   - Added `InvoiceSplitConfig` dataclass
   - Added `matches_item()` method for category matching

2. **`app/config/modules/patient_invoice_config.py`** (Lines 20, 1495-1580)
   - Imported split configuration classes
   - Added `INVOICE_SPLIT_CONFIGS` list
   - Added `get_invoice_split_config()` helper
   - Added `categorize_line_item()` helper

3. **`app/services/billing_service.py`** (Pending)
   - Modify `_create_invoice()` to group by 4 categories
   - Update `generate_invoice_number()` to use category prefixes
   - Add parent_transaction_id linking

### Key Features

- **Configurable Prefixes**: Each category has configurable prefix and starting number
- **Automatic Categorization**: Line items automatically routed to correct invoice
- **Parent Linking**: All 4 invoices linked via `parent_transaction_id`
- **Split Sequence**: `split_sequence` field tracks invoice order (1-4)
- **Split Reason**: `split_reason` field set to "TAX_COMPLIANCE_SPLIT"

## Database Fields Used

From `InvoiceHeader` model (transaction.py lines 461-464):
```python
parent_transaction_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
split_sequence = Column(Integer, default=1)
is_split_invoice = Column(Boolean, default=False)
split_reason = Column(String(100))  # TAX_COMPLIANCE_SPLIT
```

## Invoice Number Format

```
{PREFIX}/{FIN_YEAR}/{SEQ}
```

**Examples**:
- Service: `SVC/2024-2025/00001`
- GST Medicines: `MED/2024-2025/00001`
- GST Exempt: `EXM/2024-2025/00001`
- Prescription: `RX/2024-2025/00001`

## Workflow

```
User creates invoice with line items
           ↓
Group items by category
           ↓
Create parent invoice (first category with items)
           ↓
Create child invoices (remaining categories)
           ↓
Link all invoices with parent_transaction_id
           ↓
Return all invoice IDs
```

## Next Steps

1. ✅ Define split categories (core_definitions.py)
2. ✅ Add configuration (patient_invoice_config.py)
3. 🚧 Modify billing_service.py
4. ⏳ Test 4-way split
5. ⏳ Update UI to display linked invoices
6. ⏳ Update print templates

---

**Last Updated**: 2025-01-07 00:30
**Status**: Configuration Complete | Service Implementation In Progress
