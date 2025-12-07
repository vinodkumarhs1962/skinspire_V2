#!/usr/bin/env python
"""
Test Barcode Generator for Helett HT20 Pro Scanner Testing
Generates printable GS1-128 and EAN-13 barcodes for testing barcode scanner integration.

Usage:
    python scripts/generate_test_barcodes.py

Output:
    - Creates barcode images in scripts/test_barcodes/
    - Creates an HTML file for easy printing

Requirements:
    pip install python-barcode pillow

Author: SkinSpire Development Team
Date: 2025-12-03
"""

import os
import sys
from datetime import datetime, timedelta

# Check for required packages
try:
    import barcode
    from barcode.writer import ImageWriter
except ImportError:
    print("Required package not found. Installing...")
    os.system("pip install python-barcode pillow")
    import barcode
    from barcode.writer import ImageWriter

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "test_barcodes")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =============================================================================
# TEST BARCODE DATA
# =============================================================================

TEST_BARCODES = [
    {
        "name": "Paracetamol 500mg",
        "gtin": "08901234500001",
        "batch": "PCM2024A",
        "expiry": "261231",  # Dec 31, 2026
        "description": "Common painkiller - OTC"
    },
    {
        "name": "Amoxicillin 250mg",
        "gtin": "08901234500002",
        "batch": "AMX2024B",
        "expiry": "251130",  # Nov 30, 2025
        "description": "Antibiotic - Prescription"
    },
    {
        "name": "Vitamin D3 1000IU",
        "gtin": "08901234500003",
        "batch": "VTD2025X",
        "expiry": "270630",  # Jun 30, 2027
        "description": "Supplement - OTC"
    },
    {
        "name": "Omeprazole 20mg",
        "gtin": "08901234500004",
        "batch": "OMP2024C",
        "expiry": "260315",  # Mar 15, 2026
        "description": "Antacid - OTC"
    },
    {
        "name": "Cetirizine 10mg",
        "gtin": "08901234500005",
        "batch": "CTZ2024D",
        "expiry": "251231",  # Dec 31, 2025
        "description": "Antihistamine - OTC"
    },
    {
        "name": "Metformin 500mg",
        "gtin": "08901234500006",
        "batch": "MTF2024E",
        "expiry": "260930",  # Sep 30, 2026
        "description": "Diabetes medication - Prescription"
    },
    {
        "name": "Amlodipine 5mg",
        "gtin": "08901234500007",
        "batch": "AML2024F",
        "expiry": "270228",  # Feb 28, 2027
        "description": "Blood pressure - Prescription"
    },
    {
        "name": "Pantoprazole 40mg",
        "gtin": "08901234500008",
        "batch": "PNT2024G",
        "expiry": "260100",  # Jan 31, 2026 (day 00 = last day)
        "description": "PPI - Prescription"
    },
]


def format_gs1_barcode(gtin, batch, expiry):
    """Format GS1-128 barcode string with Application Identifiers"""
    # AI 01 = GTIN (14 digits), AI 10 = Batch, AI 17 = Expiry (YYMMDD)
    return f"(01){gtin}(10){batch}(17){expiry}"


def format_gs1_raw(gtin, batch, expiry):
    """Format raw GS1 string (what scanner might output)"""
    # GS character (ASCII 29) separates variable-length fields
    GS = chr(29)
    return f"01{gtin}10{batch}{GS}17{expiry}"


def parse_expiry(expiry_str):
    """Parse YYMMDD expiry to readable format"""
    try:
        year = int(expiry_str[0:2])
        month = int(expiry_str[2:4])
        day = int(expiry_str[4:6])

        # Year conversion
        full_year = 2000 + year if year <= 50 else 1900 + year

        # Day 00 means last day of month
        if day == 0:
            if month == 12:
                next_month = datetime(full_year + 1, 1, 1)
            else:
                next_month = datetime(full_year, month + 1, 1)
            last_day = next_month - timedelta(days=1)
            return last_day.strftime("%d-%b-%Y")

        return datetime(full_year, month, day).strftime("%d-%b-%Y")
    except:
        return expiry_str


def generate_code128_barcode(data, filename, label=""):
    """Generate Code128 barcode image"""
    try:
        # Code128 can encode the full GS1 string
        code128 = barcode.get_barcode_class('code128')

        # Create barcode with ImageWriter for PNG output
        # Smaller size for easier scanning
        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.25,
            'module_height': 8.0,
            'font_size': 8,
            'text_distance': 3.0,
            'quiet_zone': 4.0,
        })

        # Generate barcode
        bc = code128(data, writer=writer)

        # Save (adds .png extension automatically)
        filepath = os.path.join(OUTPUT_DIR, filename)
        saved_path = bc.save(filepath)

        print(f"  Created: {saved_path}")
        return saved_path

    except Exception as e:
        print(f"  Error creating Code128: {e}")
        return None


def generate_ean13_barcode(gtin, filename):
    """Generate EAN-13 barcode image (13 digits only)"""
    try:
        # EAN-13 requires exactly 13 digits (12 + check digit)
        ean_code = gtin[-13:] if len(gtin) >= 13 else gtin.zfill(13)

        # Remove check digit if present (barcode library calculates it)
        ean_code = ean_code[:12]

        ean13 = barcode.get_barcode_class('ean13')

        # Smaller size for easier scanning
        writer = ImageWriter()
        writer.set_options({
            'module_width': 0.25,
            'module_height': 8.0,
            'font_size': 8,
            'text_distance': 3.0,
            'quiet_zone': 4.0,
        })

        bc = ean13(ean_code, writer=writer)

        filepath = os.path.join(OUTPUT_DIR, filename)
        saved_path = bc.save(filepath)

        print(f"  Created: {saved_path}")
        return saved_path

    except Exception as e:
        print(f"  Error creating EAN-13: {e}")
        return None


def generate_html_page(barcodes_info):
    """Generate HTML page with all barcodes for printing"""

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Barcodes - SkinSpire HMS</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .instructions {
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 30px;
        }
        .instructions h3 {
            margin-top: 0;
            color: #0056b3;
        }
        .instructions ul {
            margin-bottom: 0;
        }
        .barcode-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        .barcode-card {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .barcode-card:hover {
            border-color: #007bff;
        }
        .medicine-name {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .medicine-desc {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
        }
        .barcode-image {
            text-align: center;
            margin: 15px 0;
            padding: 10px;
            background: #fff;
            border: 1px solid #eee;
        }
        .barcode-image img {
            max-width: 100%;
            height: auto;
        }
        .barcode-info {
            font-size: 12px;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .barcode-info table {
            width: 100%;
            border-collapse: collapse;
        }
        .barcode-info td {
            padding: 3px 5px;
        }
        .barcode-info td:first-child {
            font-weight: bold;
            width: 80px;
            color: #555;
        }
        .barcode-string {
            font-family: monospace;
            font-size: 11px;
            background: #fff3cd;
            padding: 8px;
            border-radius: 4px;
            margin-top: 10px;
            word-break: break-all;
        }
        .barcode-string strong {
            display: block;
            margin-bottom: 3px;
            color: #856404;
        }
        .print-button {
            display: block;
            width: 200px;
            margin: 30px auto;
            padding: 12px 24px;
            font-size: 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .print-button:hover {
            background: #0056b3;
        }
        @media print {
            .instructions, .print-button {
                display: none;
            }
            .barcode-card {
                break-inside: avoid;
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <h1>Test Barcodes - Helett HT20 Pro Scanner</h1>

    <div class="instructions">
        <h3>Testing Instructions</h3>
        <ul>
            <li><strong>Print this page</strong> and scan barcodes with Helett HT20 Pro</li>
            <li><strong>GS1-128 barcodes</strong> contain GTIN + Batch + Expiry (full medicine info)</li>
            <li><strong>EAN-13 barcodes</strong> contain only product code (no batch/expiry)</li>
            <li>First scan will show "Link Barcode" modal (barcodes not yet linked to medicines)</li>
            <li>After linking, future scans will auto-populate invoice line items</li>
        </ul>
    </div>

    <div class="barcode-grid">
"""

    for info in barcodes_info:
        gs1_string = format_gs1_barcode(info['gtin'], info['batch'], info['expiry'])
        expiry_formatted = parse_expiry(info['expiry'])

        html_content += f"""
        <div class="barcode-card">
            <div class="medicine-name">{info['name']}</div>
            <div class="medicine-desc">{info['description']}</div>

            <div class="barcode-image">
                <img src="{info['code128_file']}" alt="GS1-128 Barcode">
                <div style="font-size: 10px; color: #666; margin-top: 5px;">GS1-128 (Full Info)</div>
            </div>

            <div class="barcode-image">
                <img src="{info['ean13_file']}" alt="EAN-13 Barcode">
                <div style="font-size: 10px; color: #666; margin-top: 5px;">EAN-13 (Product Only)</div>
            </div>

            <div class="barcode-info">
                <table>
                    <tr><td>GTIN:</td><td>{info['gtin']}</td></tr>
                    <tr><td>Batch:</td><td>{info['batch']}</td></tr>
                    <tr><td>Expiry:</td><td>{expiry_formatted}</td></tr>
                </table>
            </div>

            <div class="barcode-string">
                <strong>GS1 String (for manual testing):</strong>
                {gs1_string}
            </div>
        </div>
"""

    html_content += """
    </div>

    <button class="print-button" onclick="window.print()">Print Barcodes</button>

    <div class="instructions" style="margin-top: 30px;">
        <h3>Linking Barcodes to Medicines</h3>
        <p>To use these test barcodes with your actual medicines:</p>
        <ol>
            <li>Go to <strong>Supplier Invoice</strong> or <strong>Patient Invoice</strong></li>
            <li>Scan a barcode from this page</li>
            <li>In the "Link Barcode" modal, search for the medicine</li>
            <li>Select the medicine and click "Link & Continue"</li>
            <li>The GTIN is now saved to that medicine record</li>
        </ol>
        <p><strong>Or</strong> add barcodes directly in Medicine Master:</p>
        <ol>
            <li>Go to <strong>Inventory → Medicines</strong></li>
            <li>Edit a medicine record</li>
            <li>Enter the GTIN in the "Barcode/GTIN" field</li>
            <li>Save the medicine</li>
        </ol>
    </div>
</body>
</html>
"""

    html_path = os.path.join(OUTPUT_DIR, "test_barcodes.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nHTML page created: {html_path}")
    return html_path


def main():
    print("=" * 60)
    print("Test Barcode Generator for SkinSpire HMS")
    print("=" * 60)
    print(f"\nOutput directory: {OUTPUT_DIR}\n")

    barcodes_info = []

    for i, med in enumerate(TEST_BARCODES, 1):
        print(f"\n[{i}/{len(TEST_BARCODES)}] {med['name']}")

        # Generate GS1-128 barcode (Code128 with GS1 data)
        gs1_data = format_gs1_barcode(med['gtin'], med['batch'], med['expiry'])
        # Remove parentheses for Code128 encoding
        code128_data = gs1_data.replace('(', '').replace(')', '')
        code128_file = generate_code128_barcode(
            code128_data,
            f"gs1_{med['gtin']}"
        )

        # Generate simple EAN-13 barcode
        ean13_file = generate_ean13_barcode(
            med['gtin'],
            f"ean_{med['gtin']}"
        )

        barcodes_info.append({
            **med,
            'code128_file': os.path.basename(code128_file) if code128_file else '',
            'ean13_file': os.path.basename(ean13_file) if ean13_file else '',
        })

    # Generate HTML page
    html_path = generate_html_page(barcodes_info)

    print("\n" + "=" * 60)
    print("GENERATION COMPLETE!")
    print("=" * 60)
    print(f"\nBarcode images saved to: {OUTPUT_DIR}")
    print(f"Open in browser: file:///{html_path.replace(os.sep, '/')}")
    print("\nNext steps:")
    print("1. Open the HTML file in a browser")
    print("2. Print the page")
    print("3. Scan barcodes with Helett HT20 Pro")
    print("4. Link barcodes to medicines in SkinSpire")

    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")
        print("\n(Opening in browser...)")
    except:
        pass


if __name__ == "__main__":
    main()
