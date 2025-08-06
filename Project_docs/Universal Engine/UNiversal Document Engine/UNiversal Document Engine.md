Summary
Yes, this receipt feature can absolutely be broadened into a Universal Document Engine that handles:
1. Financial Documents

Supplier Invoices: Multi-page with line items, tax calculations, payment terms
Purchase Orders: Approval workflows, delivery terms, supplier communications
Patient Bills: Service categorization, insurance calculations, payment summaries
Statements: Account statements, payment histories, aging reports

2. Master Records

Supplier Lists: Filterable, exportable master data reports
Item Catalogs: Product listings with categories and pricing
Patient Registries: Demographic reports with statistics
Employee Rosters: Staff lists with departments and roles

3. Operational Documents

Stock Reports: Inventory valuations, movement reports
Lab Reports: Formatted test results with normal ranges
Prescriptions: Medication lists with dosage instructions
Certificates: Medical certificates, discharge summaries

Key Enhancements:
1. Multi-Page Support

Automatic pagination
Header/footer repetition
Page numbering

2. Complex Layouts

Sender/receiver sections
Multi-column tables
Grouped data with subtotals
Dynamic calculations

3. Advanced Features

Batch document generation
Email integration
Excel export
Version control
Digital signatures

4. Configuration-Driven

No coding for new documents
Reusable section templates
Formula support in tables
Conditional display logic

The beauty is that this builds on the same Universal Engine principles - everything is configuration-driven, backend-heavy, and reusable across entities. A supplier invoice configuration is just as easy to create as a receipt configuration, but with more powerful features for complex business documents.
This transforms document generation from a development task to a configuration exercise, enabling rapid deployment while maintaining consistency across all document types in your hospital management system.

Summary
Yes, I've built comprehensive print/export options into the Universal Document Engine! Here's what's included:
Export Formats Supported:

PDF ✅

Custom page sizes (A4, A5, Letter, Legal)
Portrait/Landscape orientation
Watermarks (DRAFT, CONFIDENTIAL, etc.)
Password protection
Headers and footers
Multi-page support


Excel (XLSX/XLS) ✅

Formatted spreadsheets with styling
Formulas preserved
Multiple sheets for grouped data
Conditional formatting
Frozen headers
Auto column width


Word (DOCX) ✅

Editable documents
Tables and formatting
Custom templates
Track changes option


CSV ✅

Plain data export
Custom delimiters
Excel-compatible format
Headers optional



Export Methods:

Quick Export - One-click with defaults
Advanced Export - Modal with format-specific options
Batch Export - Multiple documents (ZIP or combined PDF)
Direct Print - Browser print functionality

Key Features:

User-Friendly UI: Dropdown menus and option modals
Progress Indicators: For large exports
Security: Password protection, watermarks, audit trails
Performance: Streaming for large files, background processing
Configuration-Driven: Set allowed formats per document type


# Universal Document Engine - Implementation Guide

## Overview
The Universal Document Engine extends the receipt system to handle all types of business documents including invoices, purchase orders, bills, and master reports.

## Key Enhancements Over Receipt System

### 1. **Multi-Page Support**
- Automatic pagination for long documents
- Page break controls
- Header/footer repetition on each page
- Page numbering

### 2. **Complex Layouts**
- Sender/Receiver sections for business documents
- Table support with calculations
- Grouped data with subtotals
- Conditional formatting

### 3. **Document Types**
- Each type has specific formatting rules
- Legal/compliance text support
- Signature blocks with multiple signatories
- Watermarks and security features

## Implementation for Different Document Types

### 1. **Supplier Invoice**

```python
# Configuration in financial_transactions.py
def configure_supplier_invoice(invoice):
    """Configure invoice document from supplier invoice data"""
    
    # Auto-calculate line items
    line_items = []
    for item in invoice.items:
        line_items.append({
            'description': item.product_name,
            'hsn_code': item.hsn_code,
            'quantity': item.quantity,
            'rate': item.rate,
            'amount': item.quantity * item.rate,
            'gst_rate': item.gst_rate
        })
    
    # Calculate taxes
    subtotal = sum(item['amount'] for item in line_items)
    gst_amount = subtotal * 0.18  # 18% GST
    
    return {
        'invoice': invoice,
        'line_items': line_items,
        'subtotal': subtotal,
        'cgst_amount': gst_amount / 2,
        'sgst_amount': gst_amount / 2,
        'total_amount': subtotal + gst_amount,
        'amount_in_words': num_to_words(subtotal + gst_amount)
    }

# Route
@universal_bp.route('/<entity_type>/invoice/<item_id>')
def print_invoice(entity_type, item_id):
    config = get_entity_config(entity_type)
    document_config = config.invoice_config  # New property
    
    # Get and prepare data
    invoice_data = service.get_invoice(item_id)
    prepared_data = configure_supplier_invoice(invoice_data)
    
    return render_template('engine/universal_document.html',
                         document_config=document_config,
                         item=prepared_data,
                         entity_config=config)
```

### 2. **Purchase Order**

```python
# Action button configuration
ActionDefinition(
    id="generate_po",
    label="Generate PO",
    icon="fas fa-file-alt",
    url_pattern="/universal/{entity_type}/purchase_order/{id}",
    button_type=ButtonType.PRIMARY,
    permission="purchase_order_create",
    show_in_list=False,
    show_in_detail=True,
    conditions={
        "status": ["draft", "pending"]
    }
)

# PO Generation
def generate_purchase_order(requisition_id):
    """Generate PO from requisition"""
    requisition = get_requisition(requisition_id)
    
    po_data = {
        'po_number': generate_po_number(),
        'po_date': datetime.now(),
        'supplier_name': requisition.suggested_supplier,
        'items': requisition.items,
        'delivery_date': requisition.required_by,
        'terms': get_standard_terms(),
        'approval_status': 'pending'
    }
    
    return po_data
```

### 3. **Patient Billing**

```python
# Complex billing with multiple service categories
PATIENT_BILL_CONFIG = DocumentConfiguration(
    document_type=DocumentType.INVOICE,
    title="Patient Bill",
    
    body_sections={
        "services": TableConfig(
            columns=[...],
            group_by="service_category",  # Groups by category
            show_subtotals=True,  # Shows category subtotals
            calculate_totals=["amount"],  # Auto-calculates
            
            # Custom grouping logic
            group_order=["Consultation", "Laboratory", "Pharmacy", "Procedures", "Room Charges"]
        )
    }
)

# Billing calculation engine
def calculate_patient_bill(admission_id):
    """Calculate comprehensive patient bill"""
    
    services = get_all_services(admission_id)
    
    # Group services by category
    grouped_services = {}
    for service in services:
        category = service.category
        if category not in grouped_services:
            grouped_services[category] = []
        grouped_services[category].append(service)
    
    # Apply discounts, insurance
    final_amount = apply_billing_rules(grouped_services)
    
    return {
        'services': services,
        'grouped_services': grouped_services,
        'total_amount': final_amount,
        'insurance_coverage': calculate_insurance(),
        'patient_payable': calculate_patient_share()
    }
```

### 4. **Master Lists/Reports**

```python
# Supplier Master List
@universal_bp.route('/reports/supplier_master')
def supplier_master_report():
    """Generate supplier master list"""
    
    # Get filters from request
    filters = {
        'category': request.args.get('category'),
        'status': request.args.get('status'),
        'date_range': request.args.get('date_range')
    }
    
    # Fetch data
    suppliers = get_filtered_suppliers(filters)
    
    # Prepare summary
    summary = {
        'total_suppliers': len(suppliers),
        'active_suppliers': len([s for s in suppliers if s.status == 'active']),
        'categories_count': len(set(s.category for s in suppliers))
    }
    
    document_config = SUPPLIER_MASTER_LIST_CONFIG
    
    return render_template('engine/universal_document.html',
                         document_config=document_config,
                         item={
                             'supplier_list': suppliers,
                             'summary': summary,
                             'filters': filters
                         })

# Inventory Valuation Report
INVENTORY_VALUATION_CONFIG = DocumentConfiguration(
    document_type=DocumentType.SUMMARY_REPORT,
    title="Inventory Valuation Report",
    orientation="landscape",
    
    body_sections={
        "inventory": TableConfig(
            columns=[
                ColumnConfig("item_code", "Code", width="10%"),
                ColumnConfig("item_name", "Item", width="30%"),
                ColumnConfig("unit", "Unit", width="8%"),
                ColumnConfig("quantity", "Stock", width="10%", align="right"),
                ColumnConfig("avg_cost", "Avg Cost", width="12%", align="right", format_type="currency"),
                ColumnConfig("total_value", "Value", width="15%", align="right", 
                           format_type="currency", formula="quantity * avg_cost"),
                ColumnConfig("expiry_date", "Expiry", width="15%", format_type="date"),
            ],
            group_by="category",
            show_subtotals=True,
            calculate_totals=["total_value"],
            rows_per_page=40
        )
    }
)
```

## Advanced Features

### 1. **Batch Document Generation**

```python
def batch_generate_documents(document_type, item_ids, config):
    """Generate multiple documents in one go"""
    
    documents = []
    for item_id in item_ids:
        doc_data = prepare_document_data(document_type, item_id)
        documents.append(doc_data)
    
    # Generate combined PDF or separate files
    if config.combine_documents:
        return generate_combined_pdf(documents, config)
    else:
        return generate_separate_pdfs(documents, config)
```

### 2. **Email Integration**

```python
def email_document(document_type, item_id, recipient_email):
    """Generate and email document"""
    
    # Generate PDF
    pdf_content = generate_document_pdf(document_type, item_id)
    
    # Send email
    send_email(
        to=recipient_email,
        subject=f"{document_type.title} - {item_id}",
        body="Please find attached document.",
        attachments=[{
            'filename': f"{document_type}_{item_id}.pdf",
            'content': pdf_content
        }]
    )
```

### 3. **Export to Excel**

```python
def export_master_list_excel(entity_type, filters):
    """Export master list to Excel with formatting"""
    
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    
    wb = Workbook()
    ws = wb.active
    
    # Add headers with styling
    headers = get_table_headers(entity_type)
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", fill_type="solid")
    
    # Add data
    data = get_entity_data(entity_type, filters)
    for row_num, item in enumerate(data, 2):
        for col, field in enumerate(get_fields(entity_type), 1):
            ws.cell(row=row_num, column=col, value=getattr(item, field))
    
    # Auto-adjust columns
    for column in ws.columns:
        max_length = max(len(str(cell.value)) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = max_length + 2
    
    return wb
```

### 4. **Document Versioning**

```python
@dataclass
class DocumentVersion:
    """Track document versions"""
    version_number: int
    generated_date: datetime
    generated_by: str
    changes: Optional[str] = None
    file_path: Optional[str] = None

# Track document generation
def track_document_generation(document_type, item_id, user):
    version = DocumentVersion(
        version_number=get_next_version(document_type, item_id),
        generated_date=datetime.now(),
        generated_by=user.username,
        file_path=generate_file_path(document_type, item_id)
    )
    save_version(version)
```

## Benefits of Universal Document Engine

### 1. **Consistency**
- All documents follow same structure
- Unified branding across all document types
- Standardized data formatting

### 2. **Flexibility**
- Easy to add new document types
- Configurable layouts without code changes
- Support for custom templates

### 3. **Compliance**
- Audit trail for all document generation
- Version control
- Legal text management

### 4. **Efficiency**
- Batch processing
- Automated calculations
- Template reuse

### 5. **Integration**
- Email delivery
- Multiple export formats
- API access for external systems

## Configuration Best Practices

### 1. **Modular Sections**
```python
# Reusable section configurations
STANDARD_HEADER = DocumentHeaderConfig(...)
STANDARD_FOOTER = FooterConfig(...)
STANDARD_TERMS = "Payment due within 30 days..."

# Apply to multiple documents
INVOICE_CONFIG.header_config = STANDARD_HEADER
PO_CONFIG.header_config = STANDARD_HEADER
```

### 2. **Dynamic Calculations**
```python
# Formula support in columns
ColumnConfig(
    field_name="line_total",
    formula="(quantity * rate) - (quantity * rate * discount_percent / 100)"
)
```

### 3. **Conditional Display**
```python
# Show sections based on conditions
"discount_section": {
    "condition": "item.total_discount > 0",
    "fields": [...]
}
```

This Universal Document Engine transforms simple receipt printing into a comprehensive document management system that handles all business documentation needs while maintaining the simplicity and configurability of the Universal Engine architecture.

# Enhanced Document Engine - Extending Receipt System
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# =============================================================================
# DOCUMENT TYPE DEFINITIONS
# =============================================================================

class DocumentType(Enum):
    """Extended document types beyond receipts"""
    # Transactional Documents
    RECEIPT = "receipt"
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    QUOTATION = "quotation"
    DELIVERY_NOTE = "delivery_note"
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    
    # Clinical Documents
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    MEDICAL_CERTIFICATE = "medical_certificate"
    
    # Reports & Listings
    MASTER_LIST = "master_list"
    TRANSACTION_REPORT = "transaction_report"
    SUMMARY_REPORT = "summary_report"
    DETAILED_STATEMENT = "detailed_statement"
    
    # Administrative
    CERTIFICATE = "certificate"
    LETTER = "letter"
    FORM = "form"
    LABEL = "label"

class PageSize(Enum):
    """Extended page sizes"""
    A4 = "A4"
    A5 = "A5"
    LETTER = "letter"
    LEGAL = "legal"
    THERMAL_80MM = "thermal_80"
    THERMAL_58MM = "thermal_58"
    LABEL_4X6 = "label_4x6"
    LABEL_2X1 = "label_2x1"
    CUSTOM = "custom"

# =============================================================================
# ENHANCED DOCUMENT CONFIGURATION
# =============================================================================

@dataclass
class DocumentHeaderConfig:
    """Enhanced header configuration for complex documents"""
    logo_position: str = "left"  # left, center, right, none
    show_watermark: bool = False
    watermark_text: Optional[str] = None
    
    # Multi-entity headers (for POs, Invoices)
    sender_section: Optional['SectionConfig'] = None
    receiver_section: Optional['SectionConfig'] = None
    
    # Document identification
    document_number_field: str = "document_no"
    document_date_field: str = "document_date"
    show_barcode: bool = False
    show_qrcode: bool = False

@dataclass
class TableConfig:
    """Configuration for table sections (line items)"""
    columns: List['ColumnConfig'] = field(default_factory=list)
    show_row_numbers: bool = False
    show_totals_row: bool = True
    group_by: Optional[str] = None
    sort_by: Optional[str] = None
    
    # Pagination for long tables
    rows_per_page: Optional[int] = None
    repeat_header: bool = True
    
    # Calculations
    calculate_totals: List[str] = field(default_factory=list)
    show_subtotals: bool = False

@dataclass
class ColumnConfig:
    """Table column configuration"""
    field_name: str
    label: str
    width: Optional[str] = None
    align: str = "left"
    format_type: Optional[str] = None
    
    # Advanced formatting
    formula: Optional[str] = None  # e.g., "quantity * rate"
    conditional_format: Optional[Dict] = None

@dataclass
class FooterConfig:
    """Enhanced footer configuration"""
    show_terms: bool = True
    terms_text: Optional[str] = None
    show_bank_details: bool = False
    show_signatures: List['SignatureConfig'] = field(default_factory=list)
    show_page_numbers: bool = True
    show_print_info: bool = True
    
    # Legal/Compliance text
    legal_text: Optional[str] = None
    registration_numbers: Optional[Dict[str, str]] = None

@dataclass
class SignatureConfig:
    """Signature block configuration"""
    label: str
    position: str = "right"  # left, center, right
    show_name: bool = True
    show_designation: bool = True
    show_date: bool = False

@dataclass
class DocumentConfiguration:
    """Complete document configuration - extends ReceiptConfiguration"""
    enabled: bool = True
    document_type: DocumentType = DocumentType.RECEIPT
    title: str = "Document"
    subtitle: Optional[str] = None
    
    # Page setup
    page_size: PageSize = PageSize.A4
    orientation: str = "portrait"
    margins: Dict[str, str] = field(default_factory=lambda: {
        "top": "15mm", "right": "15mm", 
        "bottom": "15mm", "left": "15mm"
    })
    
    # Enhanced sections
    header_config: DocumentHeaderConfig = field(default_factory=DocumentHeaderConfig)
    body_sections: Dict[str, 'SectionConfig'] = field(default_factory=dict)
    footer_config: FooterConfig = field(default_factory=FooterConfig)
    
    # Multi-page support
    max_items_per_page: Optional[int] = None
    page_break_sections: List[str] = field(default_factory=list)
    
    # Templates
    template_override: Optional[str] = None  # Custom template path
    css_override: Optional[str] = None  # Custom CSS path
    
    # Export options
    allow_pdf: bool = True
    allow_excel: bool = False
    allow_email: bool = True
    
    # Validation
    require_approval: bool = False
    approval_field: Optional[str] = None

# =============================================================================
# SUPPLIER INVOICE CONFIGURATION EXAMPLE
# =============================================================================

SUPPLIER_INVOICE_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.INVOICE,
    title="Tax Invoice",
    
    header_config=DocumentHeaderConfig(
        sender_section=SectionConfig(
            title=None,
            fields=[
                FieldConfig("hospital_name", "", bold=True, size="large"),
                FieldConfig("hospital_address", ""),
                FieldConfig("hospital_gst", "GST No:"),
            ]
        ),
        receiver_section=SectionConfig(
            title="Bill To:",
            fields=[
                FieldConfig("supplier_name", "", bold=True),
                FieldConfig("supplier_address", ""),
                FieldConfig("supplier_gst", "GST No:"),
            ]
        ),
        show_barcode=True
    ),
    
    body_sections={
        "invoice_details": SectionConfig(
            title=None,
            layout="horizontal",
            fields=[
                FieldConfig("invoice_no", "Invoice No", bold=True),
                FieldConfig("invoice_date", "Date", format_type="date"),
                FieldConfig("po_reference", "PO Ref"),
                FieldConfig("payment_terms", "Terms"),
            ]
        ),
        
        "line_items": TableConfig(
            columns=[
                ColumnConfig("sno", "#", width="5%"),
                ColumnConfig("description", "Description", width="35%"),
                ColumnConfig("hsn_code", "HSN", width="10%"),
                ColumnConfig("quantity", "Qty", width="10%", align="right"),
                ColumnConfig("rate", "Rate", width="15%", align="right", format_type="currency"),
                ColumnConfig("amount", "Amount", width="15%", align="right", 
                           format_type="currency", formula="quantity * rate"),
                ColumnConfig("gst_rate", "GST%", width="10%", align="right"),
            ],
            show_row_numbers=True,
            calculate_totals=["amount"],
            rows_per_page=20
        ),
        
        "summary": SectionConfig(
            layout="summary_box",
            fields=[
                FieldConfig("subtotal", "Subtotal", format_type="currency", align="right"),
                FieldConfig("cgst_amount", "CGST", format_type="currency", align="right"),
                FieldConfig("sgst_amount", "SGST", format_type="currency", align="right"),
                FieldConfig("total_amount", "Total", format_type="currency", 
                          bold=True, size="large", align="right"),
                FieldConfig("amount_in_words", "Amount in Words", bold=True),
            ]
        )
    },
    
    footer_config=FooterConfig(
        show_terms=True,
        terms_text="Payment due within 30 days",
        show_bank_details=True,
        show_signatures=[
            SignatureConfig("For Supplier", position="left"),
            SignatureConfig("Authorized Signatory", position="right")
        ],
        legal_text="This is a computer generated invoice"
    )
)

# =============================================================================
# PURCHASE ORDER CONFIGURATION
# =============================================================================

PURCHASE_ORDER_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.PURCHASE_ORDER,
    title="Purchase Order",
    
    body_sections={
        "items": TableConfig(
            columns=[
                ColumnConfig("item_code", "Code", width="15%"),
                ColumnConfig("item_name", "Description", width="40%"),
                ColumnConfig("quantity", "Qty", width="10%", align="center"),
                ColumnConfig("unit", "Unit", width="10%"),
                ColumnConfig("rate", "Rate", width="12%", align="right", format_type="currency"),
                ColumnConfig("amount", "Amount", width="13%", align="right", format_type="currency"),
            ],
            rows_per_page=25
        ),
        
        "terms": SectionConfig(
            title="Terms & Conditions",
            fields=[
                FieldConfig("delivery_terms", "Delivery"),
                FieldConfig("payment_terms", "Payment"),
                FieldConfig("warranty_terms", "Warranty"),
            ]
        )
    },
    
    require_approval=True,
    approval_field="approved_by"
)

# =============================================================================
# MASTER LIST CONFIGURATION (e.g., Supplier List)
# =============================================================================

SUPPLIER_MASTER_LIST_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.MASTER_LIST,
    title="Supplier Master List",
    subtitle="As on {current_date}",
    
    page_size=PageSize.A4,
    orientation="landscape",  # Better for lists
    
    body_sections={
        "filters": SectionConfig(
            title="Applied Filters",
            layout="horizontal",
            fields=[
                FieldConfig("category_filter", "Category"),
                FieldConfig("status_filter", "Status"),
                FieldConfig("date_range", "Period"),
            ]
        ),
        
        "supplier_list": TableConfig(
            columns=[
                ColumnConfig("supplier_code", "Code", width="10%"),
                ColumnConfig("supplier_name", "Name", width="25%"),
                ColumnConfig("category", "Category", width="15%"),
                ColumnConfig("contact_person", "Contact", width="15%"),
                ColumnConfig("phone", "Phone", width="12%"),
                ColumnConfig("email", "Email", width="15%"),
                ColumnConfig("status", "Status", width="8%", 
                           conditional_format={
                               "active": "text-green",
                               "inactive": "text-red"
                           }),
            ],
            show_row_numbers=True,
            rows_per_page=30,
            group_by="category",
            sort_by="supplier_name"
        ),
        
        "summary": SectionConfig(
            title="Summary",
            fields=[
                FieldConfig("total_suppliers", "Total Suppliers", format_type="number"),
                FieldConfig("active_suppliers", "Active", format_type="number"),
                FieldConfig("categories_count", "Categories", format_type="number"),
            ]
        )
    },
    
    allow_excel=True  # Allow export to Excel
)

# =============================================================================
# BILLING DOCUMENT CONFIGURATION
# =============================================================================

PATIENT_BILL_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.INVOICE,
    title="Patient Bill",
    
    body_sections={
        "patient_info": SectionConfig(
            fields=[
                FieldConfig("patient_name", "Patient", bold=True),
                FieldConfig("patient_id", "ID"),
                FieldConfig("admission_date", "Admitted", format_type="date"),
                FieldConfig("discharge_date", "Discharged", format_type="date"),
            ]
        ),
        
        "services": TableConfig(
            columns=[
                ColumnConfig("service_date", "Date", width="12%", format_type="date"),
                ColumnConfig("service_code", "Code", width="10%"),
                ColumnConfig("service_name", "Service", width="35%"),
                ColumnConfig("doctor_name", "Doctor", width="18%"),
                ColumnConfig("quantity", "Qty", width="7%", align="center"),
                ColumnConfig("rate", "Rate", width="9%", align="right", format_type="currency"),
                ColumnConfig("amount", "Amount", width="9%", align="right", format_type="currency"),
            ],
            group_by="service_category",
            show_subtotals=True,
            rows_per_page=40
        ),
        
        "payment_summary": SectionConfig(
            fields=[
                FieldConfig("total_amount", "Total Bill", format_type="currency", size="large"),
                FieldConfig("advance_paid", "Advance Paid", format_type="currency"),
                FieldConfig("insurance_amount", "Insurance", format_type="currency"),
                FieldConfig("balance_due", "Balance Due", format_type="currency", bold=True),
            ]
        )
    }
)

# =============================================================================
# LAB REPORT CONFIGURATION
# =============================================================================

LAB_REPORT_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.LAB_REPORT,
    title="Laboratory Report",
    
    body_sections={
        "test_results": TableConfig(
            columns=[
                ColumnConfig("test_name", "Test", width="30%"),
                ColumnConfig("result", "Result", width="20%", bold=True),
                ColumnConfig("unit", "Unit", width="15%"),
                ColumnConfig("normal_range", "Normal Range", width="20%"),
                ColumnConfig("flag", "Flag", width="15%",
                           conditional_format={
                               "H": "text-red bold",
                               "L": "text-blue bold"
                           }),
            ]
        )
    },
    
    footer_config=FooterConfig(
        show_signatures=[
            SignatureConfig("Lab Technician", position="left"),
            SignatureConfig("Pathologist", position="right", show_designation=True)
        ]
    )
)

<!-- Enhanced Universal Document Template -->
<!-- File: app/templates/engine/universal_document.html -->

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ document_config.title }} - {{ item[entity_config.title_field] }}</title>
    
    <!-- Base styles -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components/documents.css') }}">
    
    <!-- Document type specific styles -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/documents/' + document_config.document_type.value + '.css') }}">
    
    <!-- Custom CSS if specified -->
    {% if document_config.css_override %}
        <link rel="stylesheet" href="{{ document_config.css_override }}">
    {% endif %}
    
    <style>
        @page {
            size: {{ document_config.page_size.value }} {{ document_config.orientation }};
            margin: {{ document_config.margins.top }} {{ document_config.margins.right }} 
                    {{ document_config.margins.bottom }} {{ document_config.margins.left }};
        }
    </style>
</head>
<body class="document-body document-{{ document_config.document_type.value }}">
    
    <!-- Document Container -->
    <div class="document-container">
        
        <!-- ENHANCED HEADER FOR COMPLEX DOCUMENTS -->
        <header class="document-header">
            {% if document_config.header_config.show_watermark %}
                <div class="watermark">{{ document_config.header_config.watermark_text }}</div>
            {% endif %}
            
            <!-- Sender/Receiver Layout for Invoices/POs -->
            {% if document_config.header_config.sender_section or document_config.header_config.receiver_section %}
                <div class="header-entities">
                    <!-- Sender (Hospital/Company) -->
                    {% if document_config.header_config.sender_section %}
                        <div class="sender-section">
                            {% if document_config.header_config.logo_position != 'none' %}
                                <img src="{{ url_for('static', filename='images/logo.png') }}" 
                                     class="entity-logo logo-{{ document_config.header_config.logo_position }}">
                            {% endif %}
                            
                            {% for field in document_config.header_config.sender_section.fields %}
                                <div class="entity-field {% if field.bold %}bold{% endif %} {% if field.size %}text-{{ field.size }}{% endif %}">
                                    {% if field.label %}{{ field.label }}{% endif %}
                                    {{ item[field.field_name] }}
                                </div>
                            {% endfor %}
                        </div>
                    {% endif %}
                    
                    <!-- Receiver (Supplier/Patient) -->
                    {% if document_config.header_config.receiver_section %}
                        <div class="receiver-section">
                            <h3>{{ document_config.header_config.receiver_section.title }}</h3>
                            {% for field in document_config.header_config.receiver_section.fields %}
                                <div class="entity-field {% if field.bold %}bold{% endif %}">
                                    {% if field.label %}{{ field.label }}{% endif %}
                                    {{ item[field.field_name] }}
                                </div>
                            {% endfor %}
                        </div>
                    {% endif %}
                </div>
            {% endif %}
            
            <!-- Document Title and Number -->
            <div class="document-title-section">
                <h1 class="document-title">{{ document_config.title }}</h1>
                {% if document_config.subtitle %}
                    <h2 class="document-subtitle">{{ document_config.subtitle|format(current_date=current_date) }}</h2>
                {% endif %}
                
                <div class="document-identifiers">
                    <div class="document-number">
                        <span class="label">{{ document_config.header_config.document_number_field|title|replace('_', ' ') }}:</span>
                        <span class="value">{{ item[document_config.header_config.document_number_field] }}</span>
                    </div>
                    <div class="document-date">
                        <span class="label">Date:</span>
                        <span class="value">{{ item[document_config.header_config.document_date_field]|dateformat }}</span>
                    </div>
                </div>
                
                <!-- Barcode/QR Code -->
                {% if document_config.header_config.show_barcode %}
                    <div class="barcode">
                        <img src="{{ generate_barcode(item[document_config.header_config.document_number_field]) }}">
                    </div>
                {% endif %}
            </div>
        </header>
        
        <!-- DOCUMENT BODY WITH ENHANCED SECTIONS -->
        <main class="document-body">
            {% for section_key, section in document_config.body_sections.items() %}
                
                <!-- TABLE SECTIONS (Line Items, Lists) -->
                {% if section.__class__.__name__ == 'TableConfig' %}
                    <section class="document-section table-section">
                        {% if section.title %}
                            <h3 class="section-title">{{ section.title }}</h3>
                        {% endif %}
                        
                        <table class="document-table">
                            <thead>
                                <tr>
                                    {% if section.show_row_numbers %}
                                        <th class="row-number">#</th>
                                    {% endif %}
                                    {% for column in section.columns %}
                                        <th style="width: {{ column.width }}; text-align: {{ column.align }}">
                                            {{ column.label }}
                                        </th>
                                    {% endfor %}
                                </tr>
                            </thead>
                            <tbody>
                                {% set items = item[section_key] if section_key in item else [] %}
                                {% set current_group = None %}
                                
                                {% for row_item in items %}
                                    <!-- Group Headers -->
                                    {% if section.group_by and row_item[section.group_by] != current_group %}
                                        {% set current_group = row_item[section.group_by] %}
                                        <tr class="group-header">
                                            <td colspan="{{ section.columns|length + (1 if section.show_row_numbers else 0) }}">
                                                <strong>{{ current_group }}</strong>
                                            </td>
                                        </tr>
                                    {% endif %}
                                    
                                    <tr>
                                        {% if section.show_row_numbers %}
                                            <td class="row-number">{{ loop.index }}</td>
                                        {% endif %}
                                        
                                        {% for column in section.columns %}
                                            <td style="text-align: {{ column.align }}" 
                                                class="{% if column.conditional_format %}{{ get_conditional_class(row_item[column.field_name], column.conditional_format) }}{% endif %}">
                                                {% if column.formula %}
                                                    {{ evaluate_formula(column.formula, row_item) }}
                                                {% else %}
                                                    {{ format_field(row_item[column.field_name], column.format_type) }}
                                                {% endif %}
                                            </td>
                                        {% endfor %}
                                    </tr>
                                    
                                    <!-- Page break after specified rows -->
                                    {% if section.rows_per_page and loop.index % section.rows_per_page == 0 and not loop.last %}
                                        </tbody></table>
                                        <div class="page-break"></div>
                                        <table class="document-table">
                                        {% if section.repeat_header %}
                                            <thead>
                                                <tr>
                                                    {% if section.show_row_numbers %}<th>#</th>{% endif %}
                                                    {% for column in section.columns %}
                                                        <th style="width: {{ column.width }}; text-align: {{ column.align }}">
                                                            {{ column.label }}
                                                        </th>
                                                    {% endfor %}
                                                </tr>
                                            </thead>
                                        {% endif %}
                                        <tbody>
                                    {% endif %}
                                {% endfor %}
                                
                                <!-- Totals Row -->
                                {% if section.show_totals_row and section.calculate_totals %}
                                    <tr class="totals-row">
                                        {% if section.show_row_numbers %}
                                            <td></td>
                                        {% endif %}
                                        {% for column in section.columns %}
                                            <td style="text-align: {{ column.align }}">
                                                {% if column.field_name in section.calculate_totals %}
                                                    <strong>{{ calculate_total(items, column.field_name, column.format_type) }}</strong>
                                                {% elif loop.first %}
                                                    <strong>Total</strong>
                                                {% endif %}
                                            </td>
                                        {% endfor %}
                                    </tr>
                                {% endif %}
                            </tbody>
                        </table>
                    </section>
                    
                <!-- REGULAR SECTIONS -->
                {% else %}
                    <section class="document-section {{ section.layout }}-section">
                        {% if section.title %}
                            <h3 class="section-title">{{ section.title }}</h3>
                        {% endif %}
                        
                        <div class="section-content layout-{{ section.layout }}">
                            {% for field in section.fields %}
                                <div class="document-field {% if field.css_class %}{{ field.css_class }}{% endif %}"
                                     style="{% if field.align %}text-align: {{ field.align }};{% endif %}">
                                    {% if field.show_label and field.label %}
                                        <span class="field-label">{{ field.label }}:</span>
                                    {% endif %}
                                    <span class="field-value {% if field.bold %}bold{% endif %} {% if field.size %}text-{{ field.size }}{% endif %}">
                                        {{ format_field(item[field.field_name], field.format_type) }}
                                    </span>
                                </div>
                            {% endfor %}
                        </div>
                    </section>
                {% endif %}
                
                <!-- Page break for specified sections -->
                {% if section_key in document_config.page_break_sections %}
                    <div class="page-break"></div>
                {% endif %}
            {% endfor %}
        </main>
        
        <!-- ENHANCED FOOTER -->
        <footer class="document-footer">
            <!-- Terms & Conditions -->
            {% if document_config.footer_config.show_terms and document_config.footer_config.terms_text %}
                <div class="terms-section">
                    <h4>Terms & Conditions:</h4>
                    <p>{{ document_config.footer_config.terms_text }}</p>
                </div>
            {% endif %}
            
            <!-- Bank Details (for invoices) -->
            {% if document_config.footer_config.show_bank_details %}
                <div class="bank-details">
                    <h4>Bank Details:</h4>
                    <p>{{ bank_details|safe }}</p>
                </div>
            {% endif %}
            
            <!-- Legal Text -->
            {% if document_config.footer_config.legal_text %}
                <div class="legal-text">
                    {{ document_config.footer_config.legal_text }}
                </div>
            {% endif %}
            
            <!-- Signatures -->
            {% if document_config.footer_config.show_signatures %}
                <div class="signatures-section">
                    {% for sig in document_config.footer_config.show_signatures %}
                        <div class="signature-block signature-{{ sig.position }}">
                            <div class="signature-line"></div>
                            <p class="signature-label">{{ sig.label }}</p>
                            {% if sig.show_name %}<p class="signature-name">{{ item[sig.name_field] if sig.name_field else '' }}</p>{% endif %}
                            {% if sig.show_designation %}<p class="signature-designation">{{ item[sig.designation_field] if sig.designation_field else '' }}</p>{% endif %}
                            {% if sig.show_date %}<p class="signature-date">Date: _____________</p>{% endif %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
            
            <!-- Page Numbers -->
            {% if document_config.footer_config.show_page_numbers %}
                <div class="page-numbers">
                    Page <span class="page-number"></span> of <span class="total-pages"></span>
                </div>
            {% endif %}
            
            <!-- Print Info -->
            {% if document_config.footer_config.show_print_info %}
                <div class="print-info">
                    Printed on: {{ current_datetime|dateformat('%d-%m-%Y %H:%M') }} by {{ current_user.username }}
                </div>
            {% endif %}
        </footer>
    </div>
    
    <!-- JavaScript for page numbers and calculations -->
    <script>
        // Page numbering
        window.onload = function() {
            var pages = document.querySelectorAll('.page-break');
            var totalPages = pages.length + 1;
            
            // Update page numbers
            document.querySelectorAll('.total-pages').forEach(el => {
                el.textContent = totalPages;
            });
            
            // Auto print if requested
            if (window.location.search.includes('autoprint=true')) {
                setTimeout(function() {
                    window.print();
                }, 500);
            }
        };
    </script>
</body>
</html>

# Add to universal_views.py

@universal_bp.route('/<entity_type>/receipt/<item_id>')
@login_required
@require_web_branch_permission('universal', 'view')
def universal_receipt_view(entity_type: str, item_id: str):
    """
    Universal receipt view - configuration driven
    """
    try:
        # Validate entity type
        if not is_valid_entity_type(entity_type):
            flash(f"Entity type '{entity_type}' not found", 'error')
            return redirect(url_for('auth_views.dashboard'))
        
        # Get configuration
        config = get_entity_config(entity_type)
        
        # Check if receipts are enabled
        if not config.receipt_config or not config.receipt_config.enabled:
            flash(f"Receipts are not enabled for {config.name}", 'warning')
            return redirect(url_for('universal_views.universal_detail_view', 
                                  entity_type=entity_type, item_id=item_id))
        
        # Check permissions
        if not has_entity_permission(current_user, entity_type, 'view'):
            flash(f"You don't have permission to view {config.plural_name} receipts", 'warning')
            return redirect(url_for('auth_views.dashboard'))
        
        # Get service and fetch item
        service = get_universal_service(entity_type)
        item_data = service.get_by_id(item_id)
        
        if not item_data or not item_data.get('success'):
            flash(f"{config.name} not found", 'error')
            return redirect(url_for('universal_views.universal_list_view', entity_type=entity_type))
        
        # Assemble receipt data
        assembler = EnhancedUniversalDataAssembler()
        receipt_data = assembler.assemble_receipt_data(
            config=config,
            item_data=item_data,
            user=current_user,
            branch_context=get_branch_context()
        )
        
        # Render receipt template
        return render_template(
            'engine/universal_receipt.html',
            **receipt_data
        )
        
    except Exception as e:
        logger.error(f"Error generating receipt for {entity_type}/{item_id}: {str(e)}")
        flash("Error generating receipt", 'error')
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type=entity_type, item_id=item_id))

# =============================================================================
# Add to data_assembler.py
# =============================================================================

def assemble_receipt_data(self, config: EntityConfiguration, item_data: Dict, **kwargs) -> Dict:
    """
    Assemble data for receipt printing
    Following universal engine principles - configuration driven
    """
    try:
        item = item_data.get('item')
        if not item:
            raise ValueError("No item found in data")
        
        receipt_config = config.receipt_config
        if not receipt_config:
            raise ValueError("No receipt configuration found")
        
        # Convert item to dict if needed
        if hasattr(item, '__dict__'):
            from app.services.database_service import get_entity_dict
            item_dict = get_entity_dict(item)
        else:
            item_dict = item if isinstance(item, dict) else {}
        
        # Get hospital/branch info
        branch_context = kwargs.get('branch_context', {})
        user = kwargs.get('user')
        
        # Prepare receipt data
        receipt_data = {
            # Configuration
            'receipt_config': receipt_config,
            'entity_config': self._make_template_safe_config(config),
            'entity_type': config.entity_type,
            
            # Item data
            'item': item_dict,
            
            # Hospital/Branch info
            'hospital_name': branch_context.get('hospital_name', 'Hospital Name'),
            'hospital_address': branch_context.get('hospital_address', ''),
            'hospital_phone': branch_context.get('hospital_phone', ''),
            'hospital_email': branch_context.get('hospital_email', ''),
            'hospital_gst': branch_context.get('hospital_gst', ''),
            'branch_name': branch_context.get('branch_name', ''),
            
            # Additional data
            'current_user': user,
            'current_datetime': datetime.now(),
            
            # Process special fields (like items table)
            'processed_data': self._process_receipt_fields(receipt_config, item_dict, config)
        }
        
        # Add any computed fields
        receipt_data.update(self._compute_receipt_totals(item_dict, receipt_config))
        
        return receipt_data
        
    except Exception as e:
        logger.error(f"Error assembling receipt data: {str(e)}")
        raise

def _process_receipt_fields(self, receipt_config: ReceiptConfiguration, 
                          item: Dict, config: EntityConfiguration) -> Dict:
    """
    Process special fields for receipt display
    """
    processed = {}
    
    # Process table sections (like line items)
    for section_key, section in receipt_config.sections.items():
        if section.layout == 'table' and section_key in item:
            # Process table data
            table_items = item.get(section_key, [])
            if isinstance(table_items, str):
                # Parse JSON if needed
                try:
                    import json
                    table_items = json.loads(table_items)
                except:
                    table_items = []
            
            processed[section_key] = table_items
    
    return processed

def _compute_receipt_totals(self, item: Dict, receipt_config: ReceiptConfiguration) -> Dict:
    """
    Compute any totals or calculated fields for receipt
    """
    computed = {}
    
    # Example: Calculate totals from line items
    if 'items' in item:
        items = item.get('items', [])
        if isinstance(items, str):
            try:
                import json
                items = json.loads(items)
            except:
                items = []
        
        subtotal = sum(float(item.get('amount', 0)) for item in items)
        tax_rate = float(item.get('tax_rate', 0.18))  # Default 18% GST
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount
        
        computed.update({
            'computed_subtotal': subtotal,
            'computed_tax_amount': tax_amount,
            'computed_total': total
        })
    
    return computed

# =============================================================================
# Helper function to evaluate conditions (add to template filters)
# =============================================================================

def eval_condition(condition: str, context: Dict) -> bool:
    """
    Safely evaluate a condition string
    """
    try:
        # Simple conditions like "item.status == 'paid'"
        # Create safe evaluation context
        safe_context = {'item': context}
        
        # Only allow simple comparisons
        allowed_operators = ['==', '!=', '>', '<', '>=', '<=', 'in', 'not in']
        
        # Basic safety check
        if any(op in condition for op in allowed_operators):
            return eval(condition, {"__builtins__": {}}, safe_context)
        
        return True
    except:
        return True  # Default to showing section if evaluation fails

# Universal Export Feature - Complete Implementation Guide

## Overview

The Universal Document Engine now includes comprehensive export functionality supporting multiple formats:

### Supported Export Formats

1. **PDF** - Using WeasyPrint/pdfkit
   - Custom page sizes and orientation
   - Watermarks
   - Headers/footers
   - Password protection

2. **Excel (XLSX/XLS)** - Using openpyxl
   - Multiple sheets
   - Formulas and calculations
   - Conditional formatting
   - Charts and graphs
   - Frozen headers

3. **Word (DOCX)** - Using python-docx
   - Custom templates
   - Table of contents
   - Track changes
   - Rich formatting

4. **CSV** - Using Python csv
   - Custom delimiters
   - Headers optional
   - Excel-compatible

5. **Additional Formats**
   - HTML
   - JSON
   - XML
   - Direct Print

## Implementation Components

### 1. **Export Engine** (`export_engine.py`)
Core engine that handles all format conversions:
- Format-specific exporters
- Common options handling
- Post-processing (compression, encryption)

### 2. **Export Routes** (`universal_views.py`)
- `/universal/<entity_type>/export/<item_id>` - Single document export
- `/universal/<entity_type>/export/batch` - Batch export
- `/reports/<report_type>/export` - Report export

### 3. **UI Components**
- Export button dropdown
- Advanced options modal
- Batch export controls
- Progress indicators

### 4. **JavaScript Manager** (`universal_export.js`)
- Format selection
- Options management
- Progress tracking
- File download handling

## Configuration

### Document-Level Export Configuration

```python
# In entity configuration
SUPPLIER_INVOICE_CONFIG = DocumentConfiguration(
    # ... other config ...
    
    # Export settings
    allowed_export_formats=[
        ExportFormat.PDF,
        ExportFormat.EXCEL,
        ExportFormat.WORD,
        ExportFormat.CSV
    ],
    default_export_format=ExportFormat.PDF,
    
    # Format-specific defaults
    export_options={
        ExportFormat.PDF: ExportOptions(
            pdf_page_size="A4",
            pdf_orientation="portrait",
            pdf_watermark="ORIGINAL"
        ),
        ExportFormat.EXCEL: ExportOptions(
            excel_include_formulas=True,
            excel_freeze_headers=True
        )
    }
)
```

## Usage Examples

### 1. **Quick Export (Default Settings)**

```javascript
// PDF export with defaults
quickExport('pdf');

// Excel export
quickExport('excel');
```

### 2. **Advanced Export (With Options)**

```javascript
// Show modal for user to select options
showExportModal();

// Or programmatically with options
exportWithOptions({
    format: 'pdf',
    page_size: 'A3',
    orientation: 'landscape',
    watermark: 'CONFIDENTIAL'
});
```

### 3. **Batch Export**

```javascript
// Select multiple items
const selectedIds = ['INV001', 'INV002', 'INV003'];

// Export as separate files (ZIP)
batchExport(selectedIds, 'pdf', false);

// Export as combined PDF
batchExport(selectedIds, 'pdf', true);
```

### 4. **Report Export**

```javascript
// Export supplier master list to Excel
exportReport('supplier_master', 'excel');

// Export with current filters
exportReport('inventory_valuation', 'csv');
```

## Feature Integration

### In Universal View (Detail Page)

```html
<!-- Add to action buttons -->
<div class="export-button-group">
    <div class="dropdown">
        <button class="btn-outline dropdown-toggle" type="button" data-toggle="dropdown">
            <i class="fas fa-download"></i> Export
        </button>
        <div class="dropdown-menu">
            <a class="dropdown-item" href="#" onclick="quickExport('pdf')">
                <i class="fas fa-file-pdf text-danger"></i> Export as PDF
            </a>
            <a class="dropdown-item" href="#" onclick="quickExport('excel')">
                <i class="fas fa-file-excel text-success"></i> Export as Excel
            </a>
            <!-- More options -->
        </div>
    </div>
</div>
```

### In Universal List (Multiple Selection)

```html
<!-- Batch export controls -->
<button class="btn-outline" onclick="initBatchExport()">
    <i class="fas fa-download"></i> Export Selected
</button>
```

## Advanced Features

### 1. **Conditional Export Formats**

```python
# Only allow PDF for finalized documents
if document.status == 'finalized':
    allowed_formats = [ExportFormat.PDF]
else:
    allowed_formats = [ExportFormat.PDF, ExportFormat.WORD, ExportFormat.EXCEL]
```

### 2. **Custom Export Templates**

```python
# Use different templates for different scenarios
if export_format == ExportFormat.PDF and document_type == 'invoice':
    template = 'exports/invoice_professional.html'
elif export_format == ExportFormat.EXCEL:
    template = 'exports/data_analysis.xlsx'
```

### 3. **Dynamic Watermarks**

```python
# Add dynamic watermarks based on status
if document.status == 'draft':
    watermark = "DRAFT - NOT FOR DISTRIBUTION"
elif document.is_confidential:
    watermark = "CONFIDENTIAL"
```

### 4. **Export Permissions**

```python
# Check export permissions
@require_permission('export_sensitive_data')
def export_with_sensitive_data():
    # Include sensitive fields
    pass
```

## Performance Optimization

### 1. **Async Export for Large Documents**

```python
@celery.task
def export_large_report_async(report_type, filters, format):
    # Generate in background
    result = generate_report(report_type, filters, format)
    
    # Send email with download link
    send_export_ready_email(user_email, download_url)
```

### 2. **Export Caching**

```python
@cache_export(timeout=3600)
def export_document(doc_id, format):
    # Cache generated exports
    pass
```

### 3. **Streaming Large Files**

```python
def stream_large_csv(query):
    def generate():
        yield ','.join(headers) + '\n'
        for row in query.yield_per(1000):
            yield ','.join(row) + '\n'
    
    return Response(generate(), mimetype='text/csv')
```

## Security Considerations

### 1. **Access Control**
- Export permissions separate from view permissions
- Audit trail for all exports
- Watermarking for sensitive documents

### 2. **Data Protection**
- Optional password protection
- Encryption for sensitive exports
- Secure temporary file handling

### 3. **Rate Limiting**
- Prevent export abuse
- Queue management for large exports
- Resource usage monitoring

## Testing Export Features

### 1. **Test Different Formats**
```python
# Test each format
for format in ['pdf', 'excel', 'word', 'csv']:
    response = client.get(f'/universal/invoices/export/INV001?format={format}')
    assert response.status_code == 200
    assert response.content_type == get_mimetype(format)
```

### 2. **Test Options**
```python
# Test PDF options
response = client.get('/universal/invoices/export/INV001', {
    'format': 'pdf',
    'page_size': 'A3',
    'orientation': 'landscape',
    'watermark': 'TEST'
})
```

### 3. **Test Batch Export**
```python
# Test batch with combination
response = client.post('/universal/invoices/export/batch', json={
    'item_ids': ['INV001', 'INV002'],
    'format': 'pdf',
    'combine': True
})
```

## Installation Requirements

```bash
# PDF Generation
pip install weasyprint
# or
pip install pdfkit wkhtmltopdf

# Excel Generation
pip install openpyxl

# Word Generation
pip install python-docx

# Additional
pip install Pillow  # For images
pip install qrcode  # For QR codes
pip install python-barcode  # For barcodes
```

## Troubleshooting

### Common Issues

1. **PDF Generation Fails**
   - Check WeasyPrint installation
   - Verify fonts are available
   - Check memory limits for large documents

2. **Excel Formula Errors**
   - Ensure formula syntax is Excel-compatible
   - Check cell references are correct

3. **Large File Timeouts**
   - Implement async export
   - Use streaming for CSV
   - Increase timeout limits

### Debug Mode

```python
# Enable export debugging
EXPORT_DEBUG = True

# Log all export requests
@export_logger
def export_document():
    pass
```

## Next Steps

1. **Add More Formats**
   - RTF for compatibility
   - Markdown for documentation
   - LaTeX for academic papers

2. **Enhanced Features**
   - Email delivery integration
   - Cloud storage integration
   - Scheduled exports

3. **Template Designer**
   - Visual template builder
   - Custom styling interface
   - Preview before export

This comprehensive export system transforms the Universal Document Engine into a complete document management solution with professional-grade export capabilities.

# Export Feature Summary

## Yes, I've Built Comprehensive Export Options! ✅

### Export Formats Supported

| Format | Features | Best For |
|--------|----------|----------|
| **PDF** | • Multiple page sizes (A4, Letter, Legal)<br>• Portrait/Landscape<br>• Watermarks<br>• Password protection<br>• Headers/footers | Printing, archiving, sharing |
| **Excel** | • Multiple sheets<br>• Formulas preserved<br>• Conditional formatting<br>• Frozen headers<br>• Auto column width | Data analysis, reporting |
| **Word** | • Editable documents<br>• Custom templates<br>• Table of contents<br>• Track changes | Editing, collaboration |
| **CSV** | • Custom delimiters<br>• Excel compatible<br>• Plain data export | Data import, integration |

### Export Methods

1. **Quick Export** - One-click export with default settings
   ```javascript
   quickExport('pdf')  // Instant PDF download
   ```

2. **Advanced Export** - Modal with format-specific options
   - Page size, orientation, watermarks for PDF
   - Formula inclusion, sheet separation for Excel
   - Template selection for Word

3. **Batch Export** - Multiple documents at once
   - Individual files in ZIP
   - Combined PDF (merge multiple documents)

4. **Report Export** - Master lists and reports
   - Optimized for large datasets
   - Maintains filters and grouping

### Key Features

✅ **Configuration-Driven**
- Each document type can specify allowed formats
- Default options per format
- Permission-based access

✅ **User-Friendly UI**
- Dropdown menu for quick access
- Modal for advanced options
- Progress indicators
- Format-specific options

✅ **Performance Optimized**
- Streaming for large files
- Background processing option
- Export caching

✅ **Security**
- Password protection
- Watermarking
- Audit trail
- Permission checks

### Implementation Overview

```python
# Backend: Universal Export Engine
export_engine = UniversalExportEngine()
output = export_engine.export_document(
    document_config=config,
    document_data=data,
    export_options=ExportOptions(
        format=ExportFormat.PDF,
        pdf_watermark="CONFIDENTIAL"
    )
)

# Frontend: Simple UI
<button onclick="quickExport('excel')">
    Export to Excel
</button>

# Advanced: With options
showExportModal()  // Opens option dialog
```

### Business Benefits

1. **No More Manual Exports** - Everything automated
2. **Format Flexibility** - Users choose their preferred format
3. **Professional Output** - Properly formatted documents
4. **Data Portability** - Easy integration with other systems
5. **Compliance Ready** - Audit trails and security features

The export feature is fully integrated with the Universal Document Engine, providing a complete solution for all document export needs in your hospital management system!