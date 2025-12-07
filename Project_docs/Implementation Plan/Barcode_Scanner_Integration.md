# Helett HT20 Pro Barcode Scanner Integration Guide for SkinSpire HMS

**Version:** 2.1 (Implementation Complete)
**Date:** December 3, 2025
**Author:** SkinSpire Development Team
**Scanner Model:** Helett HT20 Pro
**Status:** IMPLEMENTED

---

## Table of Contents

1. [Overview](#1-overview)
2. [Hardware Specifications](#2-hardware-specifications)
3. [GS1 Barcode Format](#3-gs1-barcode-format)
4. [Implementation Summary](#4-implementation-summary)
5. [Database Changes](#5-database-changes)
6. [API Endpoints](#6-api-endpoints)
7. [Frontend Components](#7-frontend-components)
8. [Supplier Invoice Integration](#8-supplier-invoice-integration)
9. [Patient Invoice Integration](#9-patient-invoice-integration)
10. [Medicine-Manufacturer-Barcode Relationship](#10-medicine-manufacturer-barcode-relationship)
11. [Testing Guide](#11-testing-guide)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Overview

### 1.1 What Was Implemented

The Helett HT20 Pro barcode scanner has been integrated with SkinSpire HMS to:

- **Parse GS1-128/DataMatrix barcodes** containing GTIN, batch, and expiry
- **Pre-populate invoice line items** from scanned data
- **Link barcodes to medicines** on first scan
- **Support FIFO batch selection** for patient invoices
- **Maintain backward compatibility** - manual entry unchanged

### 1.2 Core Design Principle

> **Pre-populate Only, Zero Disruption to Existing Flows**

| What Scanner Does | What Scanner Does NOT Do |
|-------------------|--------------------------|
| Fills form fields | Change validation logic |
| Adds line items | Modify autocomplete |
| Triggers existing handlers | Alter promotion module |
| Shows link modal for unknown | Break manual entry |

### 1.3 Key Design Decision: One Barcode Per Medicine

Each medicine record stores **one barcode/GTIN**. Since GTIN is unique per manufacturer+product+pack:

```
Same medicine from different manufacturers = Different medicine records

Example:
┌─────────────────────┬──────────────┬─────────────────┐
│ Medicine Record     │ Manufacturer │ Barcode/GTIN    │
├─────────────────────┼──────────────┼─────────────────┤
│ Paracetamol 500mg   │ Sun Pharma   │ 08901234500001  │
│ Paracetamol 500mg   │ Cipla        │ 08905678500001  │
│ Paracetamol 500mg   │ GSK          │ 08907890500001  │
└─────────────────────┴──────────────┴─────────────────┘
```

---

## 2. Hardware Specifications

### 2.1 Helett HT20 Pro

| Specification | Value |
|---------------|-------|
| **Model** | Helett HT20 Pro |
| **Connection** | Wireless 2.4GHz USB Receiver |
| **Barcode Types** | 1D (EAN-13, Code128) + 2D (QR, DataMatrix) |
| **Interface** | USB HID (Keyboard Emulation) |
| **Output** | Types barcode as keystrokes + Enter |

### 2.2 How It Works

```
┌─────────────┐   Wireless   ┌─────────────┐   USB HID   ┌─────────────┐
│   Scanner   │ ──────────▶  │ USB Dongle  │ ──────────▶ │  Computer   │
└─────────────┘              └─────────────┘             └──────┬──────┘
                                                                │
                                                    Keystrokes (fast)
                                                                │
                                                                ▼
                                                    ┌─────────────────┐
                                                    │ Browser detects │
                                                    │ fast input as   │
                                                    │ scanner, not    │
                                                    │ manual typing   │
                                                    └─────────────────┘
```

---

## 3. GS1 Barcode Format

### 3.1 Application Identifiers

| AI | Name | Length | Example |
|----|------|--------|---------|
| (01) | GTIN/Product Code | 14 digits | 08901234567890 |
| (10) | Batch/Lot Number | Variable | BATCH001 |
| (17) | Expiry Date | 6 digits (YYMMDD) | 261231 |

### 3.2 Barcode Examples

**Full GS1 with all data:**
```
(01)08901234500001(10)PCM2024A(17)261231
```
Parses to:
- GTIN: `08901234500001`
- Batch: `PCM2024A`
- Expiry: `2026-12-31`

**Simple EAN-13 (product only):**
```
8901234500001
```
Parses to:
- GTIN: `8901234500001`
- Batch: (none)
- Expiry: (none)

### 3.3 Expiry Date Rules

| YYMMDD | Interpreted As |
|--------|----------------|
| 261231 | December 31, 2026 |
| 270100 | January 31, 2027 (day 00 = last day) |
| 251015 | October 15, 2025 |

---

## 4. Implementation Summary

### 4.1 Files Created

| File | Purpose |
|------|---------|
| `migrations/20251203_add_barcode_to_medicines.sql` | Database migration |
| `app/api/routes/barcode_api.py` | REST API endpoints |
| `app/static/js/components/barcode_scanner.js` | Scanner detection + Link modal JS |
| `app/templates/components/barcode_link_modal.html` | Link modal HTML |
| `scripts/generate_test_barcodes.py` | Test barcode generator |
| `scripts/test_barcodes/test_barcodes.html` | Printable test barcodes |

### 4.2 Files Modified

| File | Change |
|------|--------|
| `app/models/master.py` | Added `barcode` field to Medicine model |
| `app/__init__.py` | Registered barcode_api_bp blueprint |
| `app/config/modules/medicine_config.py` | Added barcode to form fields |
| `app/templates/supplier/create_supplier_invoice.html` | Scanner integration |
| `app/templates/billing/create_invoice.html` | Scanner integration |

### 4.3 Files NOT Modified (Preserved)

| File | Reason |
|------|--------|
| `app/static/js/components/invoice_item.js` | Existing validation intact |
| `app/static/js/components/invoice_bulk_discount.js` | Promotion logic intact |
| `app/static/js/components/buy_x_get_y_handler.js` | Promotion logic intact |
| `app/services/billing_service.py` | Business logic unchanged |
| `app/services/inventory_service.py` | FIFO logic unchanged |

---

## 5. Database Changes

### 5.1 Migration Applied

```sql
-- File: migrations/20251203_add_barcode_to_medicines.sql
ALTER TABLE medicines ADD COLUMN IF NOT EXISTS barcode VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_medicines_barcode ON medicines(barcode);
```

### 5.2 Medicine Model Field

```python
# In app/models/master.py (line 669-671)
class Medicine(Base, ...):
    # ...
    # Barcode/GTIN for scanner integration (Added 2025-12-03)
    barcode = Column(String(50), nullable=True)
```

### 5.3 Verify in Database

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'medicines' AND column_name = 'barcode';
```

---

## 6. API Endpoints

### 6.1 Parse Barcode

**Endpoint:** `POST /api/barcode/parse`

Parses barcode without database lookup.

**Request:**
```json
{
    "barcode": "(01)08901234500001(10)PCM2024A(17)261231"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "gtin": "08901234500001",
        "batch": "PCM2024A",
        "expiry_date": "2026-12-31",
        "expiry_formatted": "31-Dec-2026",
        "is_valid": true,
        "format": "GS1-Parentheses"
    }
}
```

### 6.2 Lookup Barcode

**Endpoint:** `POST /api/barcode/lookup`

Parses barcode AND looks up medicine in database.

**Request:**
```json
{
    "barcode": "(01)08901234500001(10)PCM2024A(17)261231"
}
```

**Response (Medicine Found):**
```json
{
    "success": true,
    "parsed": {
        "gtin": "08901234500001",
        "batch": "PCM2024A",
        "expiry_date": "2026-12-31"
    },
    "medicine_found": true,
    "medicine": {
        "medicine_id": "uuid-here",
        "medicine_name": "Paracetamol 500mg",
        "selling_price": 25.00,
        "gst_rate": 12.00,
        "hsn_code": "30049099"
    },
    "available_batches": [
        {"batch": "PCM2024A", "expiry_date": "2026-12-31", "available_qty": 500}
    ]
}
```

**Response (Medicine NOT Found):**
```json
{
    "success": true,
    "parsed": { ... },
    "medicine_found": false,
    "medicine": null,
    "message": "Barcode not linked to any medicine."
}
```

### 6.3 Link Barcode

**Endpoint:** `POST /api/barcode/link`

Links a barcode/GTIN to an existing medicine.

**Request:**
```json
{
    "barcode": "08901234500001",
    "medicine_id": "uuid-of-medicine"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Barcode linked to Paracetamol 500mg",
    "medicine_id": "uuid-here",
    "medicine_name": "Paracetamol 500mg"
}
```

### 6.4 Search Medicine (for Link Modal)

**Endpoint:** `GET /api/barcode/search-medicine?q=paracetamol&limit=10`

**Response:**
```json
{
    "success": true,
    "medicines": [
        {
            "medicine_id": "uuid",
            "medicine_name": "Paracetamol 500mg",
            "manufacturer": "Sun Pharma",
            "barcode": null,
            "has_barcode": false
        }
    ]
}
```

---

## 7. Frontend Components

### 7.1 BarcodeScanner Class

**File:** `app/static/js/components/barcode_scanner.js`

```javascript
// Usage
const scanner = new BarcodeScanner({
    timeout: 50,        // ms between keystrokes (scanner is fast)
    minLength: 6,       // minimum barcode length
    onScan: function(data) {
        // Called when medicine found
        // data.medicine, data.parsed, data.available_batches
    },
    onNotFound: function(data) {
        // Called when barcode not linked
        // Show link modal
    },
    onError: function(message) {
        // Called on errors
    }
});

scanner.enable();   // Enable scanning
scanner.disable();  // Disable (e.g., when modal open)
```

### 7.2 BarcodeLinkModal Class

**File:** `app/static/js/components/barcode_scanner.js`

```javascript
// Usage
const linkModal = new BarcodeLinkModal({
    onLinked: function(linkedData) {
        // Called after barcode linked successfully
        // linkedData.medicine_id, linkedData.medicine_name, linkedData.barcode
    }
});

linkModal.show(parsedData);  // Show modal with parsed barcode data
```

### 7.3 Link Modal HTML

**File:** `app/templates/components/barcode_link_modal.html`

Include in templates that need barcode linking:
```html
{% include 'components/barcode_link_modal.html' %}
```

---

## 8. Supplier Invoice Integration

### 8.1 Location

**File:** `app/templates/supplier/create_supplier_invoice.html`

### 8.2 Scanner Mode Toggle

Added toggle in quick actions bar:

```html
<!-- Barcode Scanner Mode Toggle -->
<div class="btn-group">
    <input type="radio" name="scannerMode" id="validateMode" checked>
    <label for="validateMode">Validate</label>

    <input type="radio" name="scannerMode" id="addMode">
    <label for="addMode">Add</label>
</div>
```

### 8.3 Two Modes

| Mode | Use Case | Behavior |
|------|----------|----------|
| **Validate** | PO-based invoices | Updates batch/expiry on existing lines |
| **Add** | Fresh invoices | Adds new line items |

### 8.4 Validate Mode Workflow

```
1. Line items pre-populated from PO (no batch/expiry)
2. Scan medicine barcode
3. System finds matching line by medicine_id
4. Updates ONLY batch and expiry fields
5. Shows success message
```

### 8.5 Add Mode Workflow

```
1. Empty or partial invoice
2. Scan medicine barcode
3. If barcode linked: Add new line with all fields
4. If not linked: Show link modal → link → add line
5. User edits quantity as needed
```

---

## 9. Patient Invoice Integration

### 9.1 Location

**File:** `app/templates/billing/create_invoice.html`

### 9.2 Workflow

```
1. Patient selected
2. Scan medicine barcode
3. If barcode linked:
   - Add new line using invoiceItemComponent.addLineItem()
   - Set medicine, price, GST from master
   - Select FIFO batch (earliest expiry)
   - Set quantity = 1
   - Trigger existing validation/promotion logic
4. If not linked:
   - Show link modal
   - User selects medicine
   - Barcode saved to medicine
   - Line item added
```

### 9.3 Key Implementation Detail

```javascript
// Uses EXISTING component - no changes to invoice_item.js
var row = window.invoiceItemComponent.addLineItem();
// Then populate fields and trigger events
```

### 9.4 What Stays Unchanged

- `invoice_item.js` - All validation intact
- `invoice_bulk_discount.js` - Bulk discounts still apply
- `buy_x_get_y_handler.js` - Promotions still apply
- All autocomplete functionality
- All manual entry workflows

---

## 10. Medicine-Manufacturer-Barcode Relationship

### 10.1 Design Decision

**One barcode per medicine record.** Since GTIN is manufacturer-specific:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MEDICINE RECORDS IN SKINSPIRE                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Medicine: Paracetamol 500mg                                       │
│  ├── Record 1: Sun Pharma   → Barcode: 08901234500001             │
│  ├── Record 2: Cipla        → Barcode: 08905678500001             │
│  └── Record 3: GSK          → Barcode: 08907890500001             │
│                                                                     │
│  Each record has:                                                  │
│  - Different barcode (GTIN)                                        │
│  - Different price (potentially)                                   │
│  - Different stock/batches                                         │
│  - Same generic name                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.2 Inventory Implications

Same medicine from different manufacturers = **separate inventory lines**:

```
┌────────────────────────┬──────────────┬──────────┬────────┐
│ Medicine               │ Manufacturer │ Batch    │ Stock  │
├────────────────────────┼──────────────┼──────────┼────────┤
│ Paracetamol 500mg      │ Sun Pharma   │ SUN2024A │ 500    │
│ Paracetamol 500mg      │ Cipla        │ CIP2024X │ 300    │
│ Paracetamol 500mg      │ GSK          │ GSK2025A │ 150    │
└────────────────────────┴──────────────┴──────────┴────────┘
                                            Total: 950
```

### 10.3 FIFO Behavior

Currently: FIFO within same medicine record (manufacturer-specific).

```
Scan Sun Pharma barcode → Only Sun Pharma batches shown (FIFO)
Scan Cipla barcode → Only Cipla batches shown (FIFO)
```

---

## 11. Testing Guide

### 11.1 Test Barcodes Generated

**Location:** `scripts/test_barcodes/`

| File | Purpose |
|------|---------|
| `test_barcodes.html` | Printable page with all test barcodes |
| `gs1_*.png` | GS1-128 barcode images (GTIN + batch + expiry) |
| `ean_*.png` | EAN-13 barcode images (product code only) |

### 11.2 Generate Test Barcodes

```bash
python scripts/generate_test_barcodes.py
```

Opens HTML page with 8 printable test barcodes.

### 11.3 Test Barcode Data

| Medicine | GTIN | Batch | Expiry |
|----------|------|-------|--------|
| Paracetamol 500mg | 08901234500001 | PCM2024A | 31-Dec-2026 |
| Amoxicillin 250mg | 08901234500002 | AMX2024B | 30-Nov-2025 |
| Vitamin D3 1000IU | 08901234500003 | VTD2025X | 30-Jun-2027 |
| Omeprazole 20mg | 08901234500004 | OMP2024C | 15-Mar-2026 |
| Cetirizine 10mg | 08901234500005 | CTZ2024D | 31-Dec-2025 |
| Metformin 500mg | 08901234500006 | MTF2024E | 30-Sep-2026 |
| Amlodipine 5mg | 08901234500007 | AML2024F | 28-Feb-2027 |
| Pantoprazole 40mg | 08901234500008 | PNT2024G | 31-Jan-2026 |

### 11.4 Copy-Paste Testing (Without Scanner)

Paste these into invoice page and press Enter:

```
(01)08901234500001(10)PCM2024A(17)261231
```

```
(01)08901234500002(10)AMX2024B(17)251130
```

### 11.5 Test Checklist

| Test | Expected | Status |
|------|----------|--------|
| Scanner outputs to Notepad | Barcode text appears | ✅ Verified |
| Scan on Supplier Invoice | Line added or updated | Test |
| Scan on Patient Invoice | Line added with FIFO batch | Test |
| Unknown barcode | Link modal appears | Test |
| Link barcode to medicine | Success, future scans work | Test |
| Manual entry still works | No change | Test |
| Promotions apply after scan | Discounts calculated | Test |

### 11.6 Browser Console Testing

```javascript
// Test API directly
fetch('/api/barcode/lookup', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value
    },
    body: JSON.stringify({
        barcode: '(01)08901234500001(10)PCM2024A(17)261231'
    })
})
.then(r => r.json())
.then(console.log);
```

---

## 12. Troubleshooting

### 12.1 Scanner Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No output when scanning | Not paired | Power cycle scanner |
| Random characters | Wrong mode | Configure scanner to HID mode |
| Missing Enter key | Scanner config | Program suffix as Enter (CR) |

### 12.2 Application Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Nothing happens on scan | JS not loaded | Check console, refresh page |
| "BarcodeScanner undefined" | Script not loaded | Verify script tag in template |
| CSRF token error | Token expired | Refresh page |
| Link modal doesn't appear | HTML not included | Check {% include %} |
| Medicine not found after link | Barcode not saved | Check medicine master |

### 12.3 Debug Mode

Enable scanner debug logging:

```javascript
const scanner = new BarcodeScanner({
    debug: true,  // Logs all keystrokes and timing
    // ...
});
```

### 12.4 Verify Database

```sql
-- Check if barcode is saved
SELECT medicine_name, barcode
FROM medicines
WHERE barcode IS NOT NULL;
```

---

## Appendix A: Quick Reference

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/barcode/parse` | Parse barcode only |
| POST | `/api/barcode/lookup` | Parse + lookup medicine |
| POST | `/api/barcode/link` | Link barcode to medicine |
| GET | `/api/barcode/search-medicine?q=` | Search for linking |

### Files Summary

```
app/
├── api/routes/
│   └── barcode_api.py          # API endpoints
├── models/
│   └── master.py               # Medicine.barcode field
├── static/js/components/
│   └── barcode_scanner.js      # Scanner + Link modal JS
├── templates/
│   ├── components/
│   │   └── barcode_link_modal.html
│   ├── billing/
│   │   └── create_invoice.html # Patient invoice (modified)
│   └── supplier/
│       └── create_supplier_invoice.html # Supplier invoice (modified)
├── utils/
│   └── barcode_utils.py        # GS1 parser (existing)
└── config/modules/
    └── medicine_config.py      # Barcode field in form

migrations/
└── 20251203_add_barcode_to_medicines.sql

scripts/
├── generate_test_barcodes.py
└── test_barcodes/
    ├── test_barcodes.html
    ├── gs1_*.png
    └── ean_*.png
```

---

**Document End**

*Last Updated: December 3, 2025*
*Implementation Status: Complete*
