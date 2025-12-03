"""
GS1 Barcode Parser Utility for Medicine Barcodes
Parses GS1-128 and GS1 DataMatrix barcodes containing:
- GTIN/Product Code (AI 01)
- Batch/Lot Number (AI 10)
- Expiry Date (AI 17)
- Serial Number (AI 21)

Helett HT20 Scanner Integration Support
"""

import re
from datetime import datetime, date
from typing import Optional, Dict, Any


# GS1 Application Identifiers with their fixed lengths (if applicable)
GS1_APPLICATION_IDENTIFIERS = {
    '00': {'name': 'SSCC', 'length': 18},
    '01': {'name': 'GTIN', 'length': 14},
    '02': {'name': 'CONTENT', 'length': 14},
    '10': {'name': 'BATCH_LOT', 'length': None},  # Variable length
    '11': {'name': 'PROD_DATE', 'length': 6},
    '13': {'name': 'PACK_DATE', 'length': 6},
    '15': {'name': 'BEST_BEFORE', 'length': 6},
    '17': {'name': 'EXPIRY_DATE', 'length': 6},
    '20': {'name': 'VARIANT', 'length': 2},
    '21': {'name': 'SERIAL', 'length': None},  # Variable length
    '30': {'name': 'VAR_COUNT', 'length': None},
    '310': {'name': 'NET_WEIGHT_KG', 'length': 6},
    '37': {'name': 'COUNT', 'length': None},
    '240': {'name': 'ADDITIONAL_ID', 'length': None},
    '241': {'name': 'CUSTOMER_PART_NO', 'length': None},
    '250': {'name': 'SECONDARY_SERIAL', 'length': None},
    '251': {'name': 'REF_TO_SOURCE', 'length': None},
    '400': {'name': 'ORDER_NUMBER', 'length': None},
    '410': {'name': 'SHIP_TO_LOC', 'length': 13},
    '414': {'name': 'LOC_NO', 'length': 13},
    '420': {'name': 'SHIP_TO_POSTAL', 'length': None},
    '421': {'name': 'SHIP_TO_COUNTRY', 'length': None},
    '8020': {'name': 'PAYMENT_SLIP_REF', 'length': None},
}

# Group Separator character (used to separate variable-length fields)
GS = '\x1d'  # ASCII 29


class BarcodeParseResult:
    """Result of parsing a GS1 barcode"""

    def __init__(self):
        self.gtin: Optional[str] = None
        self.batch_number: Optional[str] = None
        self.expiry_date: Optional[date] = None
        self.serial_number: Optional[str] = None
        self.production_date: Optional[date] = None
        self.raw_data: str = ''
        self.parsed_fields: Dict[str, Any] = {}
        self.is_valid: bool = False
        self.error_message: Optional[str] = None
        self.barcode_format: str = 'unknown'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'gtin': self.gtin,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'serial_number': self.serial_number,
            'production_date': self.production_date.isoformat() if self.production_date else None,
            'raw_data': self.raw_data,
            'parsed_fields': self.parsed_fields,
            'is_valid': self.is_valid,
            'error_message': self.error_message,
            'barcode_format': self.barcode_format
        }


def parse_gs1_date(date_str: str) -> Optional[date]:
    """
    Parse GS1 date format (YYMMDD)

    Rules:
    - If day is 00, it means last day of month
    - YY 00-50 = 2000-2050, YY 51-99 = 1951-1999
    """
    if not date_str or len(date_str) != 6:
        return None

    try:
        year = int(date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])

        # Year conversion (00-50 = 2000-2050, 51-99 = 1951-1999)
        if year <= 50:
            full_year = 2000 + year
        else:
            full_year = 1900 + year

        # Day 00 means last day of month
        if day == 0:
            # Get last day of month
            if month == 12:
                next_month = date(full_year + 1, 1, 1)
            else:
                next_month = date(full_year, month + 1, 1)
            from datetime import timedelta
            last_day = next_month - timedelta(days=1)
            return last_day

        return date(full_year, month, day)
    except (ValueError, TypeError):
        return None


def parse_gs1_barcode(barcode_data: str) -> BarcodeParseResult:
    """
    Parse a GS1-128 or GS1 DataMatrix barcode

    Supports formats:
    1. With parentheses: (01)08901234567890(10)ABC123(17)261130
    2. Without parentheses: 010890123456789010ABC123<GS>17261130
    3. FNC1 separated: ]d201089012345678901017261130ABC123

    Args:
        barcode_data: Raw barcode string from scanner

    Returns:
        BarcodeParseResult with parsed fields
    """
    result = BarcodeParseResult()
    result.raw_data = barcode_data

    if not barcode_data:
        result.error_message = 'Empty barcode data'
        return result

    # Clean the barcode data
    cleaned_data = barcode_data.strip()

    # Remove symbology identifiers if present
    if cleaned_data.startswith(']d2') or cleaned_data.startswith(']C1'):
        cleaned_data = cleaned_data[3:]
        result.barcode_format = 'GS1-DataMatrix' if barcode_data.startswith(']d2') else 'GS1-128'

    # Try parsing with parentheses format first
    if '(' in cleaned_data:
        result = _parse_parentheses_format(cleaned_data, result)
    else:
        # Parse raw GS1 format
        result = _parse_raw_gs1_format(cleaned_data, result)

    # Set validity
    result.is_valid = bool(result.gtin or result.batch_number)

    return result


def _parse_parentheses_format(data: str, result: BarcodeParseResult) -> BarcodeParseResult:
    """Parse GS1 barcode with explicit parentheses around AIs"""
    result.barcode_format = 'GS1-Parentheses'

    # Pattern to match (AI)Value pairs
    pattern = r'\((\d{2,4})\)([^(]+)'
    matches = re.findall(pattern, data)

    for ai, value in matches:
        value = value.strip().rstrip(GS)
        result.parsed_fields[ai] = value

        if ai == '01':
            result.gtin = value
        elif ai == '10':
            result.batch_number = value
        elif ai == '17':
            result.expiry_date = parse_gs1_date(value)
        elif ai == '21':
            result.serial_number = value
        elif ai == '11':
            result.production_date = parse_gs1_date(value)

    return result


def _parse_raw_gs1_format(data: str, result: BarcodeParseResult) -> BarcodeParseResult:
    """Parse raw GS1 format without parentheses"""
    result.barcode_format = 'GS1-Raw'

    # Replace common separator characters
    data = data.replace(GS, '|').replace('\x00', '|')

    pos = 0
    while pos < len(data):
        # Skip separators
        if data[pos] == '|':
            pos += 1
            continue

        # Try to match AIs (2, 3, or 4 digit)
        matched = False

        for ai_len in [4, 3, 2]:
            if pos + ai_len > len(data):
                continue

            potential_ai = data[pos:pos + ai_len]

            if potential_ai in GS1_APPLICATION_IDENTIFIERS:
                ai_info = GS1_APPLICATION_IDENTIFIERS[potential_ai]
                pos += ai_len

                if ai_info['length']:
                    # Fixed length field
                    value = data[pos:pos + ai_info['length']]
                    pos += ai_info['length']
                else:
                    # Variable length - read until separator or end
                    end_pos = data.find('|', pos)
                    if end_pos == -1:
                        # Check for next AI
                        end_pos = _find_next_ai(data, pos)
                    value = data[pos:end_pos]
                    pos = end_pos

                value = value.strip()
                result.parsed_fields[potential_ai] = value

                # Map to result fields
                if potential_ai == '01':
                    result.gtin = value
                elif potential_ai == '10':
                    result.batch_number = value
                elif potential_ai == '17':
                    result.expiry_date = parse_gs1_date(value)
                elif potential_ai == '21':
                    result.serial_number = value
                elif potential_ai == '11':
                    result.production_date = parse_gs1_date(value)

                matched = True
                break

        if not matched:
            pos += 1

    return result


def _find_next_ai(data: str, start_pos: int) -> int:
    """Find position of next Application Identifier in data"""
    for i in range(start_pos, len(data)):
        for ai_len in [4, 3, 2]:
            if i + ai_len <= len(data):
                potential_ai = data[i:i + ai_len]
                if potential_ai in GS1_APPLICATION_IDENTIFIERS:
                    return i
    return len(data)


def parse_simple_barcode(barcode_data: str) -> BarcodeParseResult:
    """
    Parse simple barcodes that are not GS1 format
    (e.g., just a product code or internal barcode)

    Args:
        barcode_data: Raw barcode string

    Returns:
        BarcodeParseResult with the barcode as GTIN
    """
    result = BarcodeParseResult()
    result.raw_data = barcode_data
    result.barcode_format = 'Simple'

    if barcode_data:
        result.gtin = barcode_data.strip()
        result.is_valid = True
    else:
        result.error_message = 'Empty barcode data'

    return result


def detect_and_parse_barcode(barcode_data: str) -> BarcodeParseResult:
    """
    Auto-detect barcode format and parse accordingly

    Detects:
    - GS1-128/DataMatrix (contains AIs)
    - Simple barcodes (EAN-13, UPC, internal codes)

    Args:
        barcode_data: Raw barcode string from scanner

    Returns:
        BarcodeParseResult with parsed fields
    """
    if not barcode_data:
        result = BarcodeParseResult()
        result.error_message = 'Empty barcode data'
        return result

    cleaned = barcode_data.strip()

    # Check for GS1 format indicators
    has_parentheses = '(' in cleaned and ')' in cleaned
    has_symbology_id = cleaned.startswith(']d2') or cleaned.startswith(']C1')
    has_gs_separator = GS in cleaned or '\x00' in cleaned

    # Check if it starts with common GS1 AIs
    starts_with_ai = (
        cleaned.startswith('01') or
        cleaned.startswith('10') or
        cleaned.startswith('17') or
        cleaned.startswith('21')
    )

    # Determine format
    if has_parentheses or has_symbology_id or has_gs_separator:
        return parse_gs1_barcode(cleaned)
    elif starts_with_ai and len(cleaned) > 16:
        # Likely GS1 without separators
        return parse_gs1_barcode(cleaned)
    else:
        # Simple barcode
        return parse_simple_barcode(cleaned)


# Convenience function for common use case
def extract_medicine_info(barcode_data: str) -> Dict[str, Any]:
    """
    Extract medicine-specific information from barcode

    Returns dict with:
    - product_code: GTIN or simple barcode
    - batch_number: Batch/Lot number (if present)
    - expiry_date: Expiry date as ISO string (if present)
    - is_valid: Whether parsing was successful
    - error: Error message if parsing failed
    """
    result = detect_and_parse_barcode(barcode_data)

    return {
        'product_code': result.gtin,
        'batch_number': result.batch_number,
        'expiry_date': result.expiry_date.isoformat() if result.expiry_date else None,
        'expiry_date_formatted': result.expiry_date.strftime('%d-%b-%Y') if result.expiry_date else None,
        'serial_number': result.serial_number,
        'is_valid': result.is_valid,
        'error': result.error_message,
        'format': result.barcode_format,
        'raw_data': result.raw_data
    }
