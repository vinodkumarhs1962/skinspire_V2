# Helett HT20 Barcode Scanner Integration Guide for SkinSpire HMS

**Version:** 1.0
**Date:** November 2025
**Author:** SkinSpire Development Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Hardware Specifications](#2-hardware-specifications)
3. [GS1 Barcode Format for Medicines](#3-gs1-barcode-format-for-medicines)
4. [System Architecture](#4-system-architecture)
5. [Database Schema Changes](#5-database-schema-changes)
6. [Backend Implementation](#6-backend-implementation)
7. [API Reference](#7-api-reference)
8. [Frontend Implementation](#8-frontend-implementation)
9. [Module Integration Points](#9-module-integration-points)
10. [Testing Guide](#10-testing-guide)
11. [Troubleshooting](#11-troubleshooting)
12. [Go-Live Checklist](#12-go-live-checklist)

---

## 1. Overview

### 1.1 Purpose

This document outlines the integration of Helett HT20 Wireless 2D/1D Barcode Scanner with the SkinSpire Clinic HMS for capturing medicine barcodes containing product code, batch number, and expiry date.

### 1.2 Scope

- Scan and parse GS1-128/DataMatrix medicine barcodes
- Extract Product Code (GTIN), Batch Number, and Expiry Date
- Auto-populate fields in billing and inventory modules
- Support FIFO batch selection based on expiry
- Enable quick medicine lookup during billing

### 1.3 Key Benefits

| Benefit | Description |
|---------|-------------|
| **Speed** | Instant medicine identification vs manual search |
| **Accuracy** | Eliminates manual entry errors for batch/expiry |
| **FIFO Compliance** | Auto-select earliest expiring batch |
| **Audit Trail** | Track exact batch dispensed to patient |
| **Efficiency** | Reduce billing time by 50-70% |

### 1.4 Use Cases

| Module | Use Case |
|--------|----------|
| **Patient Billing** | Scan medicine to add to invoice with batch info |
| **Inventory Receiving** | Scan items when receiving stock from suppliers |
| **Stock Take** | Quick inventory counting and verification |
| **Product Lookup** | Find medicine details by scanning package |
| **Batch Verification** | Verify correct batch before dispensing |

---

## 2. Hardware Specifications

### 2.1 Helett HT20 Scanner Specifications

| Specification | Value |
|---------------|-------|
| **Model** | Helett HT20 |
| **Connection** | Wireless 2.4GHz USB Receiver |
| **Barcode Types** | 1D (EAN-13, Code128, etc.) + 2D (QR, DataMatrix) |
| **Interface** | USB HID (Keyboard Emulation) |
| **Range** | Up to 100m wireless range |
| **Battery** | Built-in rechargeable |
| **Scan Speed** | ~300 scans/second |

### 2.2 How It Works

The HT20 operates in **Keyboard Emulation Mode (HID)**:

```
┌──────────────┐    Wireless 2.4GHz    ┌──────────────┐
│   Scanner    │ ──────────────────▶   │ USB Receiver │
│   (HT20)     │                       │ (Dongle)     │
└──────────────┘                       └──────┬───────┘
                                              │
                                              │ USB HID
                                              ▼
                                       ┌──────────────┐
                                       │   Computer   │
                                       │  (Keyboard)  │
                                       └──────┬───────┘
                                              │
                                              │ Keystrokes
                                              ▼
                                       ┌──────────────┐
                                       │  Input Field │
                                       │  (Focused)   │
                                       └──────────────┘
```

**Key Points:**
- **No drivers required** - Plug-and-play USB receiver
- **Acts as keyboard** - Scanned data is "typed" into focused input
- **Suffix: Enter key** - Scanner sends Enter after barcode (configurable)
- **Fast input** - Characters arrive in rapid succession (~50ms intervals)

### 2.3 Scanner Setup

1. **Plug USB receiver** into computer USB port
2. **Power on scanner** - Automatic pairing with receiver
3. **Test in Notepad** - Scan any barcode to verify output
4. **Configure suffix** (if needed) - Use scanner manual's programming barcodes

---

## 3. GS1 Barcode Format for Medicines

### 3.1 Understanding GS1 Barcodes

Pharmaceutical products use **GS1-128** or **GS1 DataMatrix** barcodes that encode multiple data elements using **Application Identifiers (AIs)**.

### 3.2 Common Application Identifiers

| AI Code | Field Name | Length | Format | Example |
|---------|------------|--------|--------|---------|
| **(01)** | GTIN (Product Code) | 14 digits | Fixed | 08901234567890 |
| **(10)** | Batch/Lot Number | Up to 20 chars | Variable | BATCH001 |
| **(17)** | Expiry Date | 6 digits | YYMMDD | 261231 |
| **(21)** | Serial Number | Up to 20 chars | Variable | SN12345 |
| **(11)** | Production Date | 6 digits | YYMMDD | 250115 |

### 3.3 Barcode Format Examples

**Format 1: With Parentheses (Human-readable)**
```
(01)08901234567890(10)BATCH001(17)261231
```

**Format 2: Raw GS1 (Scanner output)**
```
010890123456789010BATCH001⌂17261231
```
Note: ⌂ represents FNC1/Group Separator character (ASCII 29)

**Format 3: With Symbology Identifier**
```
]d2010890123456789010BATCH001⌂17261231
```

### 3.4 Date Format Rules

GS1 dates use **YYMMDD** format with special rules:

| Component | Rule |
|-----------|------|
| **YY (Year)** | 00-50 = 2000-2050, 51-99 = 1951-1999 |
| **MM (Month)** | 01-12 |
| **DD (Day)** | 01-31, or **00** = last day of month |

**Examples:**
- `261231` = December 31, 2026
- `270100` = January 31, 2027 (day 00 = last day)
- `251015` = October 15, 2025

### 3.5 Indian Pharmaceutical Barcodes

Most Indian medicines use:
- **Primary barcode**: EAN-13 (product identification only)
- **Secondary barcode**: GS1-128 or DataMatrix (with batch/expiry)

Some manufacturers print:
- Separate barcodes for product code and batch/expiry
- Combined GS1 DataMatrix with all information

---

## 4. System Architecture

### 4.1 Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SKINSPIRE HMS (Flask)                               │
│                                                                              │
│  ┌──────────────┐     ┌─────────────────┐     ┌──────────────────────────┐  │
│  │  Frontend    │     │  Barcode API    │     │  Inventory/Billing       │  │
│  │  JavaScript  │────▶│  Endpoints      │────▶│  Services                │  │
│  │  Handler     │     │                 │     │                          │  │
│  └──────────────┘     └─────────────────┘     └──────────────────────────┘  │
│        │                      │                          │                   │
│        │                      ▼                          ▼                   │
│        │              ┌─────────────────┐        ┌──────────────────┐       │
│        │              │  Barcode Parser │        │  Database        │       │
│        │              │  Utility        │        │  (PostgreSQL)    │       │
│        │              │  (GS1 Decoder)  │        │                  │       │
│        │              └─────────────────┘        └──────────────────┘       │
│        │                                                                     │
└────────┼─────────────────────────────────────────────────────────────────────┘
         │
         │ Keyboard Input (Fast keystrokes)
         │
┌────────┴────────┐
│  HT20 Scanner   │
│  (USB HID)      │
└─────────────────┘
```

### 4.2 Component Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| **Barcode Parser** | `app/utils/barcode_utils.py` | Parse GS1 barcodes, extract fields |
| **API Endpoints** | `app/api/routes/inventory.py` | REST endpoints for barcode operations |
| **JS Handler** | `app/static/js/components/barcode_scanner.js` | Detect scanner input, call APIs |
| **Database** | `medicines.barcode` column | Store product barcodes for lookup |

### 4.3 Data Flow

```
1. User scans medicine barcode
         │
         ▼
2. Scanner sends keystrokes rapidly to browser
         │
         ▼
3. JavaScript detects fast input pattern (not manual typing)
         │
         ▼
4. On Enter key, JS sends barcode to /api/inventory/barcode/lookup
         │
         ▼
5. Backend parses GS1 format, extracts GTIN, batch, expiry
         │
         ▼
6. Backend looks up medicine by barcode/GTIN
         │
         ▼
7. Returns medicine details + matching batch info
         │
         ▼
8. Frontend auto-fills form fields (medicine, batch, expiry, price)
```

---

## 5. Database Schema Changes

### 5.1 Add Barcode Field to Medicines Table

```sql
-- Migration: Add barcode field to medicines table
ALTER TABLE medicines ADD COLUMN barcode VARCHAR(50);

-- Create index for fast lookup
CREATE INDEX idx_medicines_barcode ON medicines(barcode);

-- Optional: Add unique constraint (if each medicine has unique barcode)
-- ALTER TABLE medicines ADD CONSTRAINT uq_medicines_barcode UNIQUE (barcode);
```

### 5.2 Updated Medicine Model

```python
# In app/models/master.py - Medicine class

class Medicine(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Medicine master data"""
    __tablename__ = 'medicines'

    # ... existing fields ...

    # Barcode field (NEW)
    barcode = Column(String(50))  # GTIN or internal barcode

    # ... rest of model ...
```

### 5.3 Existing Batch/Expiry Fields

The Inventory model already has batch tracking:

```python
# In app/models/transaction.py - Inventory class

class Inventory(Base, TimestampMixin, TenantMixin):
    """Inventory movement tracking"""
    __tablename__ = 'inventory'

    # ... existing fields ...

    # Batch Information (already exists)
    batch = Column(String(20), nullable=False)
    expiry = Column(Date, nullable=False)

    # ... rest of model ...
```

---

## 6. Backend Implementation

### 6.1 Barcode Parser Utility

**File:** `app/utils/barcode_utils.py`

```python
"""
GS1 Barcode Parser Utility for Medicine Barcodes
Parses GS1-128 and GS1 DataMatrix barcodes containing:
- GTIN/Product Code (AI 01)
- Batch/Lot Number (AI 10)
- Expiry Date (AI 17)
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
import re

# GS1 Application Identifiers
GS1_APPLICATION_IDENTIFIERS = {
    '01': {'name': 'GTIN', 'length': 14},
    '10': {'name': 'BATCH_LOT', 'length': None},  # Variable
    '17': {'name': 'EXPIRY_DATE', 'length': 6},
    '21': {'name': 'SERIAL', 'length': None},  # Variable
    '11': {'name': 'PROD_DATE', 'length': 6},
}

def parse_gs1_date(date_str: str) -> Optional[date]:
    """Parse GS1 date format (YYMMDD)"""
    if not date_str or len(date_str) != 6:
        return None

    year = int(date_str[0:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])

    # Year conversion
    full_year = 2000 + year if year <= 50 else 1900 + year

    # Day 00 = last day of month
    if day == 0:
        if month == 12:
            return date(full_year + 1, 1, 1) - timedelta(days=1)
        return date(full_year, month + 1, 1) - timedelta(days=1)

    return date(full_year, month, day)

def extract_medicine_info(barcode_data: str) -> Dict[str, Any]:
    """
    Extract medicine info from barcode

    Returns:
        {
            'product_code': GTIN or simple barcode,
            'batch_number': Batch/Lot number,
            'expiry_date': ISO date string,
            'expiry_date_formatted': DD-Mon-YYYY,
            'is_valid': True/False,
            'error': Error message if failed
        }
    """
    # Implementation handles multiple formats:
    # - Parentheses: (01)xxx(10)xxx(17)xxx
    # - Raw GS1: 01xxx10xxx17xxx
    # - Simple: Just product code

    # See full implementation in app/utils/barcode_utils.py
```

### 6.2 Key Parser Features

| Feature | Description |
|---------|-------------|
| **Multi-format support** | Parentheses, raw GS1, simple barcodes |
| **Auto-detection** | Automatically detects barcode format |
| **Date parsing** | Handles GS1 YYMMDD with day-00 rule |
| **Variable fields** | Handles variable-length batch numbers |
| **Error handling** | Returns structured error information |

---

## 7. API Reference

### 7.1 Parse Barcode

**Endpoint:** `POST /api/inventory/barcode/parse`

**Purpose:** Parse a barcode without database lookup

**Request:**
```json
{
    "barcode": "(01)08901234567890(10)BATCH001(17)261231"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "product_code": "08901234567890",
        "batch_number": "BATCH001",
        "expiry_date": "2026-12-31",
        "expiry_date_formatted": "31-Dec-2026",
        "serial_number": null,
        "is_valid": true,
        "error": null,
        "format": "GS1-Parentheses",
        "raw_data": "(01)08901234567890(10)BATCH001(17)261231"
    }
}
```

### 7.2 Lookup by Barcode

**Endpoint:** `POST /api/inventory/barcode/lookup`

**Purpose:** Parse barcode AND lookup medicine in database

**Request:**
```json
{
    "barcode": "(01)08901234567890(10)BATCH001(17)261231"
}
```

**Response:**
```json
{
    "success": true,
    "parsed": {
        "product_code": "08901234567890",
        "batch_number": "BATCH001",
        "expiry_date": "2026-12-31",
        "expiry_date_formatted": "31-Dec-2026"
    },
    "medicine_found": true,
    "medicine": {
        "medicine_id": "uuid-here",
        "medicine_name": "Paracetamol 500mg",
        "generic_name": "Paracetamol",
        "manufacturer": "Sun Pharma",
        "category": "Analgesic",
        "medicine_type": "OTC",
        "mrp": 25.00,
        "selling_price": 22.50,
        "gst_rate": 12.00,
        "hsn_code": "30049099",
        "current_stock": 150
    },
    "batches": [
        {
            "batch": "BATCH001",
            "expiry_date": "2026-12-31",
            "expiry_formatted": "31-Dec-2026",
            "available_qty": 50
        },
        {
            "batch": "BATCH002",
            "expiry_date": "2027-06-30",
            "expiry_formatted": "30-Jun-2027",
            "available_qty": 100
        }
    ]
}
```

### 7.3 Simple Barcode Lookup

**Endpoint:** `GET /api/inventory/medicine/by-barcode/<barcode>`

**Purpose:** Quick lookup by exact barcode match

**Response:**
```json
{
    "success": true,
    "medicine": {
        "medicine_id": "uuid-here",
        "medicine_name": "Paracetamol 500mg",
        "mrp": 25.00,
        "selling_price": 22.50,
        "current_stock": 150,
        "medicine_type": "OTC"
    }
}
```

---

## 8. Frontend Implementation

### 8.1 Barcode Scanner JavaScript Handler

**File:** `app/static/js/components/barcode_scanner.js`

```javascript
/**
 * Barcode Scanner Handler for Helett HT20
 * Detects barcode scanner input vs manual keyboard typing
 * and processes scanned barcodes automatically.
 */

class BarcodeScanner {
    constructor(options = {}) {
        this.buffer = '';
        this.lastKeyTime = 0;
        this.SCAN_TIMEOUT = options.timeout || 50;  // ms between keystrokes
        this.MIN_LENGTH = options.minLength || 6;   // Minimum barcode length
        this.onScan = options.onScan || this.defaultHandler;
        this.enabled = true;

        this.init();
    }

    init() {
        document.addEventListener('keypress', (e) => this.handleKeyPress(e));
    }

    handleKeyPress(e) {
        if (!this.enabled) return;

        const currentTime = Date.now();

        // Reset buffer if too much time passed (manual typing)
        if (currentTime - this.lastKeyTime > this.SCAN_TIMEOUT && this.buffer.length > 0) {
            this.buffer = '';
        }
        this.lastKeyTime = currentTime;

        // Enter key signals end of barcode
        if (e.key === 'Enter' && this.buffer.length >= this.MIN_LENGTH) {
            e.preventDefault();
            e.stopPropagation();
            this.processScan(this.buffer);
            this.buffer = '';
            return;
        }

        // Accumulate printable characters
        if (e.key.length === 1) {
            this.buffer += e.key;
        }
    }

    async processScan(barcode) {
        console.log('Barcode scanned:', barcode);

        try {
            const response = await fetch('/api/inventory/barcode/lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ barcode: barcode })
            });

            const data = await response.json();

            if (data.success) {
                this.onScan(data);
            } else {
                this.showError(data.error || 'Barcode not found');
            }
        } catch (error) {
            console.error('Barcode lookup failed:', error);
            this.showError('Failed to process barcode');
        }
    }

    defaultHandler(data) {
        console.log('Barcode data:', data);
        // Override this with custom handler
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    showError(message) {
        // Use your notification system
        alert(message);
    }

    enable() { this.enabled = true; }
    disable() { this.enabled = false; }
}

// Export for use
window.BarcodeScanner = BarcodeScanner;
```

### 8.2 Usage in Templates

**Billing Page Example:**

```html
<!-- Include the scanner script -->
<script src="{{ url_for('static', filename='js/components/barcode_scanner.js') }}"></script>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Initialize barcode scanner
    const scanner = new BarcodeScanner({
        timeout: 50,
        minLength: 6,
        onScan: function(data) {
            if (data.medicine_found) {
                // Auto-fill the medicine selection
                addMedicineToInvoice({
                    medicine_id: data.medicine.medicine_id,
                    medicine_name: data.medicine.medicine_name,
                    mrp: data.medicine.mrp,
                    selling_price: data.medicine.selling_price,
                    gst_rate: data.medicine.gst_rate,
                    // Auto-select first batch (FIFO - earliest expiry)
                    batch: data.batches[0]?.batch,
                    expiry_date: data.batches[0]?.expiry_date,
                    available_qty: data.batches[0]?.available_qty
                });

                showNotification('success',
                    `Added: ${data.medicine.medicine_name} (Batch: ${data.batches[0]?.batch})`);
            } else {
                showNotification('warning',
                    `Medicine not found. Barcode: ${data.parsed.product_code}`);
            }
        }
    });

    // Disable scanner when modal is open
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('show.bs.modal', () => scanner.disable());
        modal.addEventListener('hidden.bs.modal', () => scanner.enable());
    });
});
</script>
```

### 8.3 Manual Barcode Input Field

For cases where scanner doesn't work or for manual entry:

```html
<div class="barcode-input-group">
    <label for="barcode_input">Scan/Enter Barcode:</label>
    <input type="text"
           id="barcode_input"
           class="form-control"
           placeholder="Scan barcode or enter manually"
           autocomplete="off">
    <button type="button"
            id="barcode_lookup_btn"
            class="btn btn-primary">
        Lookup
    </button>
</div>

<script>
document.getElementById('barcode_lookup_btn').addEventListener('click', function() {
    const barcode = document.getElementById('barcode_input').value.trim();
    if (barcode) {
        scanner.processScan(barcode);
    }
});

// Also handle Enter key in manual input
document.getElementById('barcode_input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('barcode_lookup_btn').click();
    }
});
</script>
```

---

## 9. Module Integration Points

### 9.1 Patient Billing Module

**File:** `app/templates/billing/create_invoice.html`

**Integration:**
1. Add barcode scanner initialization
2. When medicine scanned:
   - Add to invoice line items
   - Auto-select FIFO batch
   - Calculate pricing with GST
   - Update totals

**Flow:**
```
Scan Medicine → Lookup API → Add to Line Item → Auto-fill Batch/Expiry → Calculate Price
```

### 9.2 Inventory Receiving (GRN)

**File:** `app/templates/inventory/grn_create.html`

**Integration:**
1. Scan each item being received
2. Verify batch/expiry matches supplier invoice
3. Auto-populate item details
4. Alert if batch already exists in system

**Flow:**
```
Scan Item → Parse Batch/Expiry → Validate → Add to GRN → Update Stock
```

### 9.3 Stock Take / Physical Inventory

**File:** `app/templates/inventory/stock_take.html`

**Integration:**
1. Scan item to count
2. Display expected vs scanned batch
3. Flag discrepancies
4. Quick quantity entry

### 9.4 Purchase Order Receiving

**File:** `app/templates/purchase/receive_po.html`

**Integration:**
1. Scan items against PO line items
2. Match product code to ordered items
3. Capture actual batch/expiry received
4. Highlight variances

---

## 10. Testing Guide

### 10.1 Sample Test Barcodes

Use these for testing (generate QR codes or type manually):

| Test Case | Barcode String | Expected Result |
|-----------|----------------|-----------------|
| **Full GS1 with parentheses** | `(01)08901234567890(10)BATCH001(17)261231` | GTIN: 08901234567890, Batch: BATCH001, Expiry: 2026-12-31 |
| **Full GS1 raw format** | `0108901234567890102026ABC17261231` | Same as above |
| **Expiry with day 00** | `(01)08901234567890(17)270100` | Expiry: 2027-01-31 (last day) |
| **Simple EAN-13** | `8901234567890` | Product code only, no batch/expiry |
| **Batch only** | `(10)BATCH123` | Batch: BATCH123, no GTIN |

### 10.2 Unit Tests

**File:** `tests/test_barcode_scanner.py`

```python
import pytest
from app.utils.barcode_utils import extract_medicine_info, parse_gs1_date
from datetime import date

class TestBarcodeParser:

    def test_parse_full_gs1_parentheses(self):
        """Test parsing GS1 barcode with parentheses"""
        barcode = "(01)08901234567890(10)BATCH001(17)261231"
        result = extract_medicine_info(barcode)

        assert result['is_valid'] == True
        assert result['product_code'] == "08901234567890"
        assert result['batch_number'] == "BATCH001"
        assert result['expiry_date'] == "2026-12-31"

    def test_parse_gs1_raw_format(self):
        """Test parsing raw GS1 barcode"""
        barcode = "0108901234567890102026ABC17261231"
        result = extract_medicine_info(barcode)

        assert result['is_valid'] == True
        assert result['product_code'] == "08901234567890"

    def test_parse_simple_barcode(self):
        """Test parsing simple EAN-13 barcode"""
        barcode = "8901234567890"
        result = extract_medicine_info(barcode)

        assert result['is_valid'] == True
        assert result['product_code'] == "8901234567890"
        assert result['batch_number'] is None

    def test_gs1_date_day_zero(self):
        """Test GS1 date with day 00 (last day of month)"""
        result = parse_gs1_date("270100")  # Jan 00, 2027
        assert result == date(2027, 1, 31)

    def test_gs1_date_future_year(self):
        """Test year conversion for years 00-50"""
        result = parse_gs1_date("301015")  # Oct 15, 2030
        assert result.year == 2030

    def test_empty_barcode(self):
        """Test empty barcode handling"""
        result = extract_medicine_info("")
        assert result['is_valid'] == False
        assert result['error'] is not None
```

### 10.3 Integration Testing

1. **Scanner Hardware Test:**
   - Open Notepad
   - Scan any barcode
   - Verify text appears with Enter at end

2. **API Test:**
   ```bash
   curl -X POST http://localhost:5000/api/inventory/barcode/lookup \
        -H "Content-Type: application/json" \
        -d '{"barcode": "(01)08901234567890(10)TEST01(17)261231"}'
   ```

3. **End-to-End Test:**
   - Login to SkinSpire
   - Go to Patient Billing
   - Scan a medicine with known barcode
   - Verify auto-fill works correctly

### 10.4 Test Checklist

| Test | Pass/Fail |
|------|-----------|
| Scanner connects and pairs |  |
| Barcode appears in Notepad |  |
| API returns parsed data |  |
| Medicine lookup works |  |
| FIFO batch selection works |  |
| Billing auto-fill works |  |
| Unknown barcode shows warning |  |
| Manual entry works as fallback |  |

---

## 11. Troubleshooting

### 11.1 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| **Scanner not detected** | USB receiver not connected | Check USB connection, try different port |
| **No output when scanning** | Scanner not paired | Power cycle scanner, re-pair with receiver |
| **Barcode not recognized** | Wrong barcode format | Check if GS1 format, test with simple barcode |
| **Medicine not found** | Barcode not in database | Add barcode to medicine master data |
| **Wrong batch selected** | FIFO logic issue | Check inventory has correct batch records |
| **Duplicate characters** | Scanner speed too fast | Increase SCAN_TIMEOUT in JS handler |
| **Missing Enter key** | Scanner suffix not configured | Configure scanner to send Enter suffix |

### 11.2 Scanner Configuration

If scanner needs reconfiguration, use programming barcodes from the Helett HT20 manual:

1. **Set keyboard mode** (default)
2. **Set suffix to Enter** (Carriage Return)
3. **Set inter-character delay** if needed
4. **Enable GS1 parsing** (if supported)

### 11.3 Debugging

**Enable console logging:**
```javascript
// In barcode_scanner.js
console.log('Buffer:', this.buffer);
console.log('Time diff:', currentTime - this.lastKeyTime);
```

**Test barcode parsing:**
```python
# In Python shell
from app.utils.barcode_utils import extract_medicine_info
result = extract_medicine_info("(01)08901234567890(10)BATCH001(17)261231")
print(result)
```

---

## 12. Go-Live Checklist

### 12.1 Pre-Deployment

| Task | Status |
|------|--------|
| Database migration applied (barcode column added) |  |
| Barcode parser utility tested |  |
| API endpoints deployed |  |
| Frontend JS handler deployed |  |
| Templates updated |  |
| Scanner hardware received and tested |  |
| Medicine barcodes populated in database |  |

### 12.2 Deployment Steps

1. **Run database migration:**
   ```sql
   ALTER TABLE medicines ADD COLUMN barcode VARCHAR(50);
   CREATE INDEX idx_medicines_barcode ON medicines(barcode);
   ```

2. **Deploy code changes:**
   - `app/utils/barcode_utils.py`
   - `app/api/routes/inventory.py` (updated)
   - `app/static/js/components/barcode_scanner.js`
   - Updated templates

3. **Configure scanner:**
   - Plug in USB receiver
   - Power on scanner
   - Test in application

4. **Populate barcodes:**
   - Update medicine master with barcode values
   - Can be done via import or manual entry

### 12.3 Post-Deployment Verification

| Check | Status |
|-------|--------|
| Scanner connects successfully |  |
| Barcode lookup API works |  |
| Billing page detects scans |  |
| Medicine auto-fills correctly |  |
| Batch selection works (FIFO) |  |
| Staff trained on usage |  |

---

## Appendix A: File Locations Summary

| Component | File Path |
|-----------|-----------|
| Barcode Parser | `app/utils/barcode_utils.py` |
| API Routes | `app/api/routes/inventory.py` |
| JS Handler | `app/static/js/components/barcode_scanner.js` |
| Medicine Model | `app/models/master.py` |
| Inventory Model | `app/models/transaction.py` |
| Migration | `migrations/add_barcode_field.sql` |
| Tests | `tests/test_barcode_scanner.py` |
| Documentation | `Project_docs/Implementation Plan/Barcode_Scanner_Integration.md` |

---

## Appendix B: GS1 Application Identifier Reference

| AI | Name | Format | Length |
|----|------|--------|--------|
| 00 | SSCC | N18 | 18 |
| 01 | GTIN | N14 | 14 |
| 02 | CONTENT | N14 | 14 |
| 10 | BATCH/LOT | X..20 | Variable |
| 11 | PROD DATE | N6 (YYMMDD) | 6 |
| 13 | PACK DATE | N6 (YYMMDD) | 6 |
| 15 | BEST BEFORE | N6 (YYMMDD) | 6 |
| 17 | EXPIRY DATE | N6 (YYMMDD) | 6 |
| 21 | SERIAL | X..20 | Variable |
| 30 | VAR COUNT | N..8 | Variable |
| 37 | COUNT | N..8 | Variable |

---

**Document End**
