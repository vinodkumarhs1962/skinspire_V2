# Patient Billing Module - Technical Specifications

**Version:** 1.0
**Date:** January 2025
**Status:** Planning

---

## Overview

This document provides detailed technical specifications for implementing the Patient Billing Module migration to Universal Engine. It serves as a technical reference for developers, covering database views, entity configurations, service architecture, and implementation patterns.

**Reference Implementations:**
- Supplier Module (app/config/modules/supplier_invoice_config.py)
- Supplier Module (app/config/modules/supplier_payment_config.py)
- Universal Engine guides (v6.0, v3.0)

---

## 1. Database View Specifications

### 1.1 Patient Invoices View

**View Name:** `patient_invoices_view`
**Purpose:** Denormalized view for invoice list and detail operations
**Source Tables:** `invoice_header`, `patients`, `branches`, `hospitals`, `payment_details` (aggregated)

#### **Column Specifications**

**Primary Fields:**
```
invoice_id              UUID            Primary key
invoice_number          VARCHAR(50)     Unique invoice number
invoice_date            TIMESTAMP       Invoice creation date
invoice_type            VARCHAR(50)     Service/Product/Prescription/Miscellaneous
is_gst_invoice          BOOLEAN         GST applicable flag
hospital_id             UUID            Hospital identifier
branch_id               UUID            Branch identifier
```

**Patient Information (Joined from `patients`):**
```
patient_id              UUID            Patient identifier
patient_name            VARCHAR(200)    Patient full name
patient_mrn             VARCHAR(50)     Medical record number
patient_phone           VARCHAR(20)     Contact phone
patient_email           VARCHAR(100)    Contact email
patient_age             INTEGER         Calculated age
patient_gender          VARCHAR(10)     Gender
```

**Amount Fields:**
```
total_amount            NUMERIC(12,2)   Subtotal before tax
tax_amount              NUMERIC(12,2)   GST amount
grand_total             NUMERIC(12,2)   Total including tax
paid_amount             NUMERIC(12,2)   Amount paid
balance_due             NUMERIC(12,2)   Outstanding balance
discount_amount         NUMERIC(12,2)   Total discount
```

**Status and Calculated Fields:**
```
payment_status          VARCHAR(20)     Calculated: paid/partial/unpaid/cancelled
is_cancelled            BOOLEAN         Cancellation flag
cancellation_reason     TEXT            Cancellation notes
cancellation_date       TIMESTAMP       When cancelled
cancelled_by            UUID            User who cancelled
```

**Time-based Calculations:**
```
invoice_year            INTEGER         EXTRACT(YEAR FROM invoice_date)
invoice_month           INTEGER         EXTRACT(MONTH FROM invoice_date)
invoice_age_days        INTEGER         Days since invoice date
invoice_quarter         INTEGER         Fiscal quarter
financial_year          VARCHAR(10)     FY 2024-25 format
```

**Aggregated Payment Information:**
```
payment_count           INTEGER         Number of payments made
last_payment_date       TIMESTAMP       Most recent payment date
last_payment_amount     NUMERIC(12,2)   Last payment amount
```

**Branch and Hospital (Joined):**
```
branch_name             VARCHAR(200)    Branch name
hospital_name           VARCHAR(200)    Hospital name
```

**Audit Fields:**
```
created_at              TIMESTAMP       Creation timestamp
created_by              UUID            Creator user ID
created_by_name         VARCHAR(200)    Creator name (joined)
updated_at              TIMESTAMP       Last update
updated_by              UUID            Last updater
updated_by_name         VARCHAR(200)    Updater name
```

#### **View Query Structure**
```sql
CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    -- Primary fields from invoice_header
    ih.invoice_id,
    ih.invoice_number,
    ...

    -- Patient info (LEFT JOIN patients)
    p.patient_id,
    p.full_name AS patient_name,
    ...

    -- Payment status calculation
    CASE
        WHEN ih.is_cancelled THEN 'cancelled'
        WHEN ih.balance_due <= 0 THEN 'paid'
        WHEN ih.paid_amount > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS payment_status,

    -- Time calculations
    EXTRACT(YEAR FROM ih.invoice_date) AS invoice_year,
    DATE_PART('day', CURRENT_DATE - ih.invoice_date::DATE) AS invoice_age_days,

    -- Aggregated payment info (LEFT JOIN with GROUP BY)
    COUNT(pd.payment_id) AS payment_count,
    MAX(pd.payment_date) AS last_payment_date,

    -- Branch and hospital (LEFT JOIN)
    b.name AS branch_name,
    h.name AS hospital_name,

    -- Creator info (LEFT JOIN users)
    u.full_name AS created_by_name

FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id
LEFT JOIN payment_details pd ON ih.invoice_id = pd.invoice_id
LEFT JOIN branches b ON ih.branch_id = b.branch_id
LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id
LEFT JOIN users u ON ih.created_by = u.user_id
WHERE ih.hospital_id IS NOT NULL
GROUP BY ih.invoice_id, p.patient_id, b.branch_id, h.hospital_id, u.user_id;
```

#### **Indexes Required**
```sql
CREATE INDEX idx_patient_invoices_view_hospital ON invoice_header(hospital_id);
CREATE INDEX idx_patient_invoices_view_branch ON invoice_header(branch_id);
CREATE INDEX idx_patient_invoices_view_patient ON invoice_header(patient_id);
CREATE INDEX idx_patient_invoices_view_date ON invoice_header(invoice_date);
CREATE INDEX idx_patient_invoices_view_status ON invoice_header(is_cancelled, balance_due);
CREATE INDEX idx_patient_invoices_view_number ON invoice_header(invoice_number);
```

---

### 1.2 Patient Payments View

**View Name:** `patient_payments_view`
**Purpose:** Denormalized view for payment list and detail operations
**Source Tables:** `payment_details`, `invoice_header`, `patients`, `branches`, `hospitals`

#### **Column Specifications**

**Primary Fields:**
```
payment_id              UUID            Primary key
payment_date            TIMESTAMP       Payment date
payment_reference       VARCHAR(50)     Payment reference number
total_amount            NUMERIC(12,2)   Total payment amount
hospital_id             UUID            Hospital identifier
branch_id               UUID            Branch identifier
```

**Payment Methods:**
```
cash_amount             NUMERIC(12,2)   Cash payment
credit_card_amount      NUMERIC(12,2)   Credit card payment
debit_card_amount       NUMERIC(12,2)   Debit card payment
upi_amount              NUMERIC(12,2)   UPI payment
cheque_amount           NUMERIC(12,2)   Cheque payment (if applicable)
bank_transfer_amount    NUMERIC(12,2)   Bank transfer (if applicable)
```

**Payment Method Summary:**
```
payment_methods_used    TEXT[]          Array of methods used
primary_payment_method  VARCHAR(20)     Method with highest amount
payment_method_count    INTEGER         Number of methods used
```

**Invoice Information (Joined):**
```
invoice_id              UUID            Related invoice ID
invoice_number          VARCHAR(50)     Invoice number
invoice_date            TIMESTAMP       Invoice date
invoice_total           NUMERIC(12,2)   Invoice grand total
invoice_type            VARCHAR(50)     Invoice type
```

**Patient Information (Joined):**
```
patient_id              UUID            Patient ID
patient_name            VARCHAR(200)    Patient name
patient_mrn             VARCHAR(50)     MRN
patient_phone           VARCHAR(20)     Phone
```

**Payment Status:**
```
payment_status          VARCHAR(20)     completed/refunded/partially_refunded
refunded_amount         NUMERIC(12,2)   Amount refunded
refund_date             TIMESTAMP       Refund date
refund_reason           TEXT            Refund reason
```

**Reconciliation:**
```
reconciliation_status   VARCHAR(20)     pending/reconciled
reconciled_by           UUID            User who reconciled
reconciled_at           TIMESTAMP       Reconciliation timestamp
reconciliation_notes    TEXT            Notes
```

**Audit Fields:**
```
created_at              TIMESTAMP       Creation timestamp
created_by              UUID            Creator user ID
created_by_name         VARCHAR(200)    Creator name
```

---

### 1.3 Patient Advances View

**View Name:** `patient_advances_view`
**Purpose:** Denormalized view for advance payment tracking
**Source Tables:** `patient_advance_payments`, `patients`, `branches`, `hospitals`, `advance_applications` (aggregated)

#### **Column Specifications**

**Primary Fields:**
```
advance_payment_id      UUID            Primary key
payment_date            TIMESTAMP       Advance payment date
advance_reference       VARCHAR(50)     Reference number
amount                  NUMERIC(12,2)   Original advance amount
available_balance       NUMERIC(12,2)   Remaining balance
hospital_id             UUID            Hospital identifier
branch_id               UUID            Branch identifier
```

**Patient Information (Joined):**
```
patient_id              UUID            Patient ID
patient_name            VARCHAR(200)    Patient name
patient_mrn             VARCHAR(50)     MRN
patient_phone           VARCHAR(20)     Phone
patient_email           VARCHAR(100)    Email
```

**Advance Status:**
```
status                  VARCHAR(20)     active/applied/refunded/expired
is_active               BOOLEAN         Currently usable
expiry_date             TIMESTAMP       Advance expiry (if applicable)
```

**Usage Summary (Aggregated):**
```
total_applied           NUMERIC(12,2)   Total amount applied to invoices
total_refunded          NUMERIC(12,2)   Total amount refunded
remaining_balance       NUMERIC(12,2)   = amount - total_applied - total_refunded
applications_count      INTEGER         Number of times applied
last_applied_date       TIMESTAMP       Most recent application
last_applied_invoice    VARCHAR(50)     Last invoice number
```

**Payment Method:**
```
payment_method          VARCHAR(20)     How advance was paid
transaction_reference   VARCHAR(100)    Bank/UPI reference
```

**Audit Fields:**
```
created_at              TIMESTAMP       Creation timestamp
created_by              UUID            Creator user ID
created_by_name         VARCHAR(200)    Creator name
```

---

## 2. View Model Definitions

### 2.1 PatientInvoiceView Model

**File:** `app/models/views.py`

**Structure:**
```python
class PatientInvoiceView(Base):
    """
    Read-only view model for patient invoices
    Used by Universal Engine for list and detail operations
    """
    __tablename__ = 'patient_invoices_view'
    __table_args__ = {'info': {'is_view': True}}

    # Primary fields
    invoice_id = Column(UUID(as_uuid=True), primary_key=True)
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime)
    invoice_type = Column(String(50))
    is_gst_invoice = Column(Boolean)
    hospital_id = Column(UUID(as_uuid=True))
    branch_id = Column(UUID(as_uuid=True))

    # Patient information
    patient_id = Column(UUID(as_uuid=True))
    patient_name = Column(String(200))
    patient_mrn = Column(String(50))
    patient_phone = Column(String(20))
    patient_email = Column(String(100))
    patient_age = Column(Integer)
    patient_gender = Column(String(10))

    # Amount fields
    total_amount = Column(Numeric(12, 2))
    tax_amount = Column(Numeric(12, 2))
    grand_total = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2))
    balance_due = Column(Numeric(12, 2))
    discount_amount = Column(Numeric(12, 2))

    # Status fields
    payment_status = Column(String(20))
    is_cancelled = Column(Boolean)
    cancellation_reason = Column(Text)
    cancellation_date = Column(DateTime)
    cancelled_by = Column(UUID(as_uuid=True))

    # Calculated fields
    invoice_year = Column(Integer)
    invoice_month = Column(Integer)
    invoice_age_days = Column(Integer)

    # Aggregated fields
    payment_count = Column(Integer)
    last_payment_date = Column(DateTime)
    last_payment_amount = Column(Numeric(12, 2))

    # Branch and hospital
    branch_name = Column(String(200))
    hospital_name = Column(String(200))

    # Audit fields
    created_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True))
    created_by_name = Column(String(200))
    updated_at = Column(DateTime)
    updated_by = Column(UUID(as_uuid=True))
    updated_by_name = Column(String(200))
```

**Registration in `get_view_model()` function:**
```python
def get_view_model(view_name: str):
    view_models = {
        'patient_invoices_view': PatientInvoiceView,
        'patient_payments_view': PatientPaymentView,
        'patient_advances_view': PatientAdvanceView,
        # ... existing views
    }
    return view_models.get(view_name)
```

---

### 2.2 PatientPaymentView Model

**Structure:**
```python
class PatientPaymentView(Base):
    """Read-only view model for patient payments"""
    __tablename__ = 'patient_payments_view'
    __table_args__ = {'info': {'is_view': True}}

    # Primary fields
    payment_id = Column(UUID(as_uuid=True), primary_key=True)
    payment_date = Column(DateTime)
    payment_reference = Column(String(50))
    total_amount = Column(Numeric(12, 2))

    # Payment methods
    cash_amount = Column(Numeric(12, 2))
    credit_card_amount = Column(Numeric(12, 2))
    debit_card_amount = Column(Numeric(12, 2))
    upi_amount = Column(Numeric(12, 2))

    # Invoice information
    invoice_id = Column(UUID(as_uuid=True))
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime)
    invoice_total = Column(Numeric(12, 2))

    # Patient information
    patient_id = Column(UUID(as_uuid=True))
    patient_name = Column(String(200))
    patient_mrn = Column(String(50))

    # Status and reconciliation
    payment_status = Column(String(20))
    refunded_amount = Column(Numeric(12, 2))
    reconciliation_status = Column(String(20))
    reconciled_at = Column(DateTime)

    # Audit
    created_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True))
    created_by_name = Column(String(200))
```

---

### 2.3 PatientAdvanceView Model

**Structure:**
```python
class PatientAdvanceView(Base):
    """Read-only view model for patient advances"""
    __tablename__ = 'patient_advances_view'
    __table_args__ = {'info': {'is_view': True}}

    # Primary fields
    advance_payment_id = Column(UUID(as_uuid=True), primary_key=True)
    payment_date = Column(DateTime)
    advance_reference = Column(String(50))
    amount = Column(Numeric(12, 2))
    available_balance = Column(Numeric(12, 2))

    # Patient information
    patient_id = Column(UUID(as_uuid=True))
    patient_name = Column(String(200))
    patient_mrn = Column(String(50))

    # Status
    status = Column(String(20))
    is_active = Column(Boolean)

    # Usage summary
    total_applied = Column(Numeric(12, 2))
    total_refunded = Column(Numeric(12, 2))
    remaining_balance = Column(Numeric(12, 2))
    applications_count = Column(Integer)
    last_applied_date = Column(DateTime)

    # Audit
    created_at = Column(DateTime)
    created_by = Column(UUID(as_uuid=True))
    created_by_name = Column(String(200))
```

---

## 3. Entity Registry Configuration

**File:** `app/config/entity_registry.py`

**Registration Structure:**
```python
from app.models.views import PatientInvoiceView, PatientPaymentView, PatientAdvanceView

ENTITY_REGISTRY = {
    # ... existing entities

    # Patient Billing Entities
    "patient_invoices": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.patient_invoice_config",
        service_class="app.services.billing_service.PatientInvoiceService",
        model_class="app.models.views.PatientInvoiceView"
    ),

    "patient_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.patient_payment_config",
        service_class="app.services.billing_service.PatientPaymentService",
        model_class="app.models.views.PatientPaymentView"
    ),

    "patient_advances": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.patient_advance_config",
        service_class="app.services.billing_service.PatientAdvanceService",
        model_class="app.models.views.PatientAdvanceView"
    ),
}
```

**Entity Configuration Export:**
Each module must export its configuration:
```python
# In patient_invoice_config.py
from app.config.entity_registry import register_entity_config

config = EntityConfiguration(
    entity_type="patient_invoices",
    # ... configuration
)

# Export for registry
def get_config():
    return config
```

---

## 4. Entity Configuration Blueprint

### 4.1 Patient Invoice Configuration

**File:** `app/config/modules/patient_invoice_config.py`
**Estimated Size:** ~1,500 lines

#### **Configuration Structure Overview**
```python
from app.config.core_definitions import (
    EntityConfiguration, EntityCategory,
    FieldDefinition, FieldType, TabDefinition,
    SectionDefinition, ActionDefinition, FilterDefinition
)

PATIENT_INVOICE_CONFIG = EntityConfiguration(
    entity_type="patient_invoices",
    entity_category=EntityCategory.TRANSACTION,
    table_name="patient_invoices_view",
    primary_key_field="invoice_id",
    display_name_field="invoice_number",

    # Field definitions
    fields=PATIENT_INVOICE_FIELDS,

    # View layout (tabs and sections)
    view_layout=PATIENT_INVOICE_VIEW_LAYOUT,

    # List configuration
    list_config=PATIENT_INVOICE_LIST_CONFIG,

    # Actions
    actions=PATIENT_INVOICE_ACTIONS,

    # Filters
    filters=PATIENT_INVOICE_FILTERS,

    # Summary cards
    summary_cards=PATIENT_INVOICE_SUMMARY_CARDS,

    # Document configurations
    document_configs=PATIENT_INVOICE_DOCUMENT_CONFIGS,

    # CRUD settings
    universal_crud_enabled=False,  # Transaction entity
    allowed_operations=[READ, LIST, EXPORT, DOCUMENT],

    # Caching
    enable_caching=True,
    cache_ttl=1800,  # 30 minutes
)
```

#### **Field Definitions Structure**
**Total Fields:** 50-60 fields

**Primary Fields (10 fields):**
```python
FieldDefinition(
    name="invoice_id",
    label="Invoice ID",
    field_type=FieldType.UUID,
    is_primary_key=True,
    show_in_list=False,
    show_in_detail=True,
    tab_group="system_info"
),
FieldDefinition(
    name="invoice_number",
    label="Invoice Number",
    field_type=FieldType.STRING,
    searchable=True,
    show_in_list=True,
    show_in_detail=True,
    tab_group="invoice_details",
    section="primary_info",
    list_order=1
),
# ... invoice_date, invoice_type, etc.
```

**Patient Fields (8 fields):**
```python
FieldDefinition(
    name="patient_name",
    label="Patient Name",
    field_type=FieldType.STRING,
    searchable=True,
    show_in_list=True,
    show_in_detail=True,
    tab_group="invoice_details",
    section="patient_info",
    list_order=2
),
# ... patient_mrn, patient_phone, etc.
```

**Amount Fields (8 fields):**
```python
FieldDefinition(
    name="grand_total",
    label="Grand Total",
    field_type=FieldType.CURRENCY,
    show_in_list=True,
    show_in_detail=True,
    tab_group="invoice_details",
    section="amount_details",
    list_order=4,
    format_pattern="₹{:,.2f}"
),
# ... total_amount, tax_amount, paid_amount, balance_due, etc.
```

**Status Fields (6 fields):**
```python
FieldDefinition(
    name="payment_status",
    label="Payment Status",
    field_type=FieldType.SELECT,
    options=["paid", "partial", "unpaid", "cancelled"],
    show_in_list=True,
    show_in_detail=True,
    tab_group="invoice_details",
    section="status_info",
    list_order=5,
    renderer=StatusBadgeRenderer(
        color_map={
            'paid': 'success',
            'partial': 'warning',
            'unpaid': 'danger',
            'cancelled': 'secondary'
        }
    )
),
```

**Custom Renderer Fields (2 fields):**
```python
FieldDefinition(
    name="line_items_display",
    label="Invoice Line Items",
    field_type=FieldType.CUSTOM,
    virtual=True,
    show_in_detail=True,
    tab_group="line_items",
    section="items",
    custom_renderer=CustomRenderer(
        template="engine/business/invoice_line_items_table.html",
        context_function="get_invoice_lines",
        css_classes="w-100"
    )
),
FieldDefinition(
    name="payment_history_display",
    label="Payment History",
    field_type=FieldType.CUSTOM,
    virtual=True,
    show_in_detail=True,
    tab_group="payments",
    section="payment_list",
    custom_renderer=CustomRenderer(
        template="engine/business/payment_history_table.html",
        context_function="get_payment_history",
        css_classes="w-100"
    )
),
```

#### **Tab Definitions Structure**
```python
PATIENT_INVOICE_VIEW_LAYOUT = ViewLayout(
    tabs=[
        TabDefinition(
            id="invoice_details",
            label="Invoice Details",
            icon="fas fa-file-invoice",
            order=1,
            is_default=True
        ),
        TabDefinition(
            id="line_items",
            label="Line Items",
            icon="fas fa-list",
            order=2
        ),
        TabDefinition(
            id="payments",
            label="Payments",
            icon="fas fa-money-bill",
            order=3
        ),
        TabDefinition(
            id="system_info",
            label="System Information",
            icon="fas fa-info-circle",
            order=4
        ),
    ]
)
```

#### **Section Definitions Structure**
```python
# Within each tab, define sections
sections=[
    SectionDefinition(
        id="primary_info",
        label="Invoice Information",
        tab_id="invoice_details",
        order=1,
        columns=2  # Two-column layout
    ),
    SectionDefinition(
        id="patient_info",
        label="Patient Information",
        tab_id="invoice_details",
        order=2,
        columns=2
    ),
    SectionDefinition(
        id="amount_details",
        label="Amount Details",
        tab_id="invoice_details",
        order=3,
        columns=3  # Three-column layout
    ),
    # ... more sections
]
```

#### **Action Definitions Structure**
```python
PATIENT_INVOICE_ACTIONS = [
    ActionDefinition(
        id="view",
        label="View Invoice",
        icon="fas fa-eye",
        url_pattern="/universal/patient_invoices/detail/{invoice_id}",
        button_type=ButtonType.PRIMARY,
        show_in_list=True,
        show_in_detail=False,
        order=100
    ),
    ActionDefinition(
        id="print",
        label="Print Invoice",
        icon="fas fa-print",
        url_pattern="/billing/invoice/{invoice_id}/print",
        button_type=ButtonType.SECONDARY,
        show_in_detail=True,
        order=110
    ),
    ActionDefinition(
        id="record_payment",
        label="Record Payment",
        icon="fas fa-money-bill",
        url_pattern="/billing/invoice/{invoice_id}/payment",
        button_type=ButtonType.SUCCESS,
        show_in_detail=True,
        conditions={
            "payment_status": ["unpaid", "partial"],
            "is_cancelled": [False]
        },
        order=120
    ),
    ActionDefinition(
        id="void",
        label="Void Invoice",
        icon="fas fa-ban",
        url_pattern="/billing/invoice/{invoice_id}/void",
        button_type=ButtonType.DANGER,
        show_in_detail=True,
        conditions={
            "is_cancelled": [False]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to void this invoice? This action cannot be undone.",
        order=130
    ),
    ActionDefinition(
        id="send_email",
        label="Email Invoice",
        icon="fas fa-envelope",
        url_pattern="/billing/invoice/{invoice_id}/send-email",
        button_type=ButtonType.INFO,
        show_in_detail=True,
        order=140
    ),
    ActionDefinition(
        id="send_whatsapp",
        label="Send via WhatsApp",
        icon="fab fa-whatsapp",
        url_pattern="/billing/invoice/{invoice_id}/send-whatsapp",
        button_type=ButtonType.SUCCESS,
        show_in_detail=True,
        order=150
    ),
]
```

#### **Filter Definitions Structure**
```python
PATIENT_INVOICE_FILTERS = [
    FilterDefinition(
        name="payment_status",
        label="Payment Status",
        field_type=FieldType.SELECT,
        options=["paid", "partial", "unpaid", "cancelled"],
        multi_select=True,
        category="Status"
    ),
    FilterDefinition(
        name="invoice_type",
        label="Invoice Type",
        field_type=FieldType.SELECT,
        options=["Service", "Product", "Prescription", "Miscellaneous"],
        multi_select=True,
        category="Type"
    ),
    FilterDefinition(
        name="patient_name",
        label="Patient",
        field_type=FieldType.ENTITY_SEARCH,
        entity_type="patients",
        search_fields=["full_name", "mrn", "contact_info->>'phone'"],
        display_field="full_name",
        category="Patient"
    ),
    FilterDefinition(
        name="date_range",
        label="Invoice Date",
        field_type=FieldType.DATE_RANGE,
        presets=[
            {"label": "Today", "value": "today"},
            {"label": "Last 7 Days", "value": "last_7_days"},
            {"label": "Last 30 Days", "value": "last_30_days"},
            {"label": "This Month", "value": "this_month"},
            {"label": "Current FY", "value": "current_fy"},
        ],
        category="Date"
    ),
    FilterDefinition(
        name="amount_range",
        label="Amount Range",
        field_type=FieldType.NUMBER_RANGE,
        min_field="amount_min",
        max_field="amount_max",
        category="Amount"
    ),
    # ... more filters
]
```

#### **Summary Card Definitions**
```python
PATIENT_INVOICE_SUMMARY_CARDS = [
    SummaryCardDefinition(
        id="total_revenue",
        label="Total Revenue",
        icon="fas fa-rupee-sign",
        value_field="grand_total",
        aggregation="sum",
        format_pattern="₹{:,.2f}",
        color="primary",
        order=1
    ),
    SummaryCardDefinition(
        id="outstanding_amount",
        label="Outstanding",
        icon="fas fa-exclamation-circle",
        value_field="balance_due",
        aggregation="sum",
        format_pattern="₹{:,.2f}",
        color="warning",
        order=2,
        filter_condition={"payment_status": ["unpaid", "partial"]}
    ),
    SummaryCardDefinition(
        id="cancelled_invoices",
        label="Cancelled",
        icon="fas fa-ban",
        value_field="invoice_id",
        aggregation="count",
        color="danger",
        order=3,
        filter_condition={"is_cancelled": [True]}
    ),
    SummaryCardDefinition(
        id="monthly_revenue",
        label="This Month",
        icon="fas fa-calendar",
        value_field="grand_total",
        aggregation="sum",
        format_pattern="₹{:,.2f}",
        color="success",
        order=4,
        filter_condition={"invoice_date": "current_month"}
    ),
]
```

#### **Document Configurations**
```python
PATIENT_INVOICE_DOCUMENT_CONFIGS = {
    "invoice_print": DocumentConfiguration(
        enabled=True,
        document_type="invoice",
        title="Patient Invoice",
        print_layout_type=PrintLayoutType.DETAILED_WITH_HEADER,
        visible_tabs=["invoice_details", "line_items"],
        hidden_sections=["system_info"],
        show_terms=True,
        terms_content=[
            "Payment is due within 7 days of invoice date.",
            "Please retain this invoice for insurance claims.",
            "For queries, contact billing department."
        ],
        allowed_formats=["pdf", "print", "preview"]
    ),
    "payment_receipt": DocumentConfiguration(
        enabled=True,
        document_type="receipt",
        title="Payment Receipt",
        print_layout_type=PrintLayoutType.SIMPLE_WITH_HEADER,
        visible_tabs=["invoice_details", "payments"],
        signature_fields=[
            {"label": "Received By", "width": "200px"},
        ],
        allowed_formats=["pdf", "print"]
    ),
}
```

---

### 4.2 Patient Payment Configuration

**File:** `app/config/modules/patient_payment_config.py`
**Estimated Size:** ~800 lines

**Key Differences from Invoice Config:**
- Fewer fields (~40-50 vs. 60)
- Focus on payment methods and reconciliation
- Different actions (refund, reconcile vs. void, email)
- Different filters (payment method, reconciliation status)

**Unique Features:**
- Payment methods breakdown display
- Reconciliation workflow
- Refund tracking

---

### 4.3 Patient Advance Configuration

**File:** `app/config/modules/patient_advance_config.py`
**Estimated Size:** ~600 lines

**Key Differences:**
- Simplest of the three (~30-40 fields)
- Focus on balance tracking and applications
- Actions: apply to invoice, refund
- Custom renderer for application history

---

## 5. Service Layer Architecture

### 5.1 PatientInvoiceService

**File:** `app/services/billing_service.py`

**Class Structure:**
```python
from app.engine.universal_entity_service import UniversalEntityService
from app.models.views import PatientInvoiceView
from app.models.transaction import InvoiceHeader, InvoiceLineItem, PaymentDetail
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import invalidate_service_cache_for_entity

class PatientInvoiceService(UniversalEntityService):
    """
    Service for patient invoices
    Extends UniversalEntityService for list/view operations
    Preserves custom methods for complex business logic
    """

    def __init__(self):
        super().__init__('patient_invoices', PatientInvoiceView)

    # ==========================================
    # INHERITED METHODS (from UniversalEntityService)
    # ==========================================

    # def search_data(self, filters, hospital_id, branch_id, page, per_page, **kwargs):
    #     """
    #     Inherited - automatically uses patient_invoices_view
    #     Handles filtering, sorting, pagination
    #     Returns: {items, total, pagination, summary, applied_filters, success}
    #     """

    # def get_by_id(self, item_id, hospital_id, **kwargs):
    #     """
    #     Inherited - fetches from patient_invoices_view
    #     Returns: entity dict
    #     """

    # ==========================================
    # CUSTOM METHODS (preserve existing logic)
    # ==========================================

    def create_invoice(self, data, hospital_id, branch_id, user_id):
        """
        Create patient invoice with line items
        KEEP EXISTING LOGIC - Complex multi-type invoice creation
        """
        # Existing implementation preserved
        with get_db_session() as session:
            # Validation, inventory checks, GST calculation
            # Create invoice header and line items
            # Update inventory
            # Post GL entries if required

            # NEW: Invalidate cache after creation
            invalidate_service_cache_for_entity('patient_invoices', cascade=False)

            return {"success": True, "data": invoice_dict, "message": "Invoice created"}

    def void_invoice(self, invoice_id, reason, user_id, hospital_id):
        """
        Void/cancel invoice
        KEEP EXISTING LOGIC - GL reversal, inventory reversal
        """
        # Existing implementation preserved
        with get_db_session() as session:
            # Validation
            # Update invoice status
            # Reverse GL entries
            # Reverse inventory changes

            # NEW: Invalidate cache
            invalidate_service_cache_for_entity('patient_invoices', cascade=False)

            return {"success": True, "message": "Invoice voided"}

    # ==========================================
    # NEW METHODS (for custom renderers)
    # ==========================================

    def get_invoice_lines(self, invoice_id, hospital_id):
        """
        Get invoice line items for custom renderer
        Called by Universal Engine when rendering detail view
        """
        with get_db_session() as session:
            lines = session.query(InvoiceLineItem).filter_by(
                invoice_id=invoice_id,
                hospital_id=hospital_id
            ).order_by(InvoiceLineItem.line_number).all()

            return [get_entity_dict(line) for line in lines]

    def get_payment_history(self, invoice_id, hospital_id):
        """
        Get payment history for invoice
        Called by Universal Engine for custom renderer
        """
        with get_db_session() as session:
            payments = session.query(PaymentDetail).filter_by(
                invoice_id=invoice_id,
                hospital_id=hospital_id
            ).order_by(PaymentDetail.payment_date.desc()).all()

            return [get_entity_dict(payment) for payment in payments]
```

**Key Points:**
- Extends `UniversalEntityService` to get list/view functionality
- Preserves ALL existing custom methods (create_invoice, void_invoice, etc.)
- Adds cache invalidation to custom methods
- Adds new methods for custom renderers (get_invoice_lines, get_payment_history)

---

### 5.2 PatientPaymentService

**Structure:**
```python
class PatientPaymentService(UniversalEntityService):
    """Service for patient payments"""

    def __init__(self):
        super().__init__('patient_payments', PatientPaymentView)

    # Inherited: search_data(), get_by_id()

    # Custom methods (keep existing):
    def record_payment(self, invoice_id, payment_data, user_id, hospital_id):
        """KEEP EXISTING - Multi-method validation, GL posting"""
        # Existing logic preserved
        invalidate_service_cache_for_entity('patient_payments', cascade=False)
        invalidate_service_cache_for_entity('patient_invoices', cascade=False)  # Invoice paid_amount changes

    def issue_refund(self, payment_id, refund_amount, reason, user_id, hospital_id):
        """KEEP EXISTING - Refund processing, GL reversal"""
        # Existing logic preserved
        invalidate_service_cache_for_entity('patient_payments', cascade=False)
```

---

### 5.3 PatientAdvanceService

**Structure:**
```python
class PatientAdvanceService(UniversalEntityService):
    """Service for patient advances"""

    def __init__(self):
        super().__init__('patient_advances', PatientAdvanceView)

    # Inherited: search_data(), get_by_id()

    # Custom methods (keep existing):
    def create_advance(self, data, hospital_id, branch_id, user_id):
        """KEEP EXISTING - Advance payment recording"""
        # Existing logic preserved
        invalidate_service_cache_for_entity('patient_advances', cascade=False)

    def apply_advance(self, advance_id, invoice_id, amount, user_id, hospital_id):
        """KEEP EXISTING - Complex advance application logic"""
        # Existing logic preserved
        invalidate_service_cache_for_entity('patient_advances', cascade=False)
        invalidate_service_cache_for_entity('patient_invoices', cascade=False)  # Invoice paid_amount changes

    # New method:
    def get_advance_applications(self, advance_id, hospital_id):
        """Get advance application history for custom renderer"""
        # Query advance_applications table
        return [application_dicts]
```

---

## 6. Route Mapping & URL Structure

### 6.1 Universal Engine Routes (New)

**Automatic Routes (provided by Universal Engine):**
```python
# List views
/universal/patient_invoices/list
/universal/patient_payments/list
/universal/patient_advances/list

# Detail views
/universal/patient_invoices/detail/<invoice_id>
/universal/patient_payments/detail/<payment_id>
/universal/patient_advances/detail/<advance_id>

# Export
/universal/patient_invoices/export?format=excel&filters=...
/universal/patient_payments/export?format=csv&filters=...

# Print preview
/universal/patient_invoices/print/<invoice_id>?document_type=invoice_print
```

**Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `filters`: JSON-encoded filter object
- `sort`: Sort field (default: from config)
- `direction`: asc/desc (default: desc)

---

### 6.2 Custom Routes (Existing, Preserve)

**Invoice Routes:**
```python
# Create invoice (complex wizard)
@billing_views_bp.route('/invoice/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def create_invoice():
    # Existing implementation
    # On success: redirect to /universal/patient_invoices/detail/<invoice_id>

# Void invoice
@billing_views_bp.route('/invoice/<invoice_id>/void', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'void')
def void_invoice(invoice_id):
    # Existing implementation
    # On success: redirect to /universal/patient_invoices/detail/<invoice_id>

# Record payment
@billing_views_bp.route('/invoice/<invoice_id>/payment', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'payment')
def record_payment(invoice_id):
    # Existing implementation
    # On success: redirect to /universal/patient_invoices/detail/<invoice_id>

# Email invoice
@billing_views_bp.route('/invoice/<invoice_id>/send-email', methods=['POST'])
@login_required
def send_invoice_email(invoice_id):
    # Existing implementation

# WhatsApp invoice
@billing_views_bp.route('/invoice/<invoice_id>/send-whatsapp', methods=['POST'])
@login_required
def send_invoice_whatsapp(invoice_id):
    # Existing implementation
```

**Payment Routes:**
```python
# Refund payment
@billing_views_bp.route('/payment/<payment_id>/refund', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'refund')
def refund_payment(payment_id):
    # Existing implementation
    # On success: redirect to /universal/patient_payments/detail/<payment_id>
```

**Advance Routes:**
```python
# Create advance
@billing_views_bp.route('/advance/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'advance')
def create_advance():
    # Existing implementation
    # On success: redirect to /universal/patient_advances/detail/<advance_id>

# Apply advance to invoice
@billing_views_bp.route('/advance/apply/<invoice_id>', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'advance')
def apply_advance(invoice_id):
    # Existing implementation
    # On success: redirect to /universal/patient_invoices/detail/<invoice_id>
```

---

### 6.3 Backward Compatibility Redirects

**Add these routes to maintain compatibility:**
```python
# Old invoice list → Universal Engine list
@billing_views_bp.route('/invoice/list')
@login_required
def invoice_list_redirect():
    return redirect(url_for('universal_views.universal_list_view', entity_type='patient_invoices'))

# Old invoice detail → Universal Engine detail
@billing_views_bp.route('/invoice/<invoice_id>')
@login_required
def invoice_detail_redirect(invoice_id):
    return redirect(url_for('universal_views.universal_detail_view',
                            entity_type='patient_invoices',
                            item_id=invoice_id))

# Old advance list → Universal Engine list
@billing_views_bp.route('/invoice/advance/list')
@login_required
def advance_list_redirect():
    return redirect(url_for('universal_views.universal_list_view', entity_type='patient_advances'))
```

**Deprecation Timeline:**
- Keep redirects active for 6 months
- Add deprecation warnings to old routes
- Remove after full migration verified

---

## 7. Custom Renderer Templates

### 7.1 Invoice Line Items Renderer

**Template:** `app/templates/engine/business/invoice_line_items_table.html`

**Purpose:** Display invoice line items in detail view

**Structure:**
```html
<!-- Called by Universal Engine with context_data from get_invoice_lines() -->
<div class="invoice-line-items">
    <table class="table table-sm table-hover">
        <thead class="table-light">
            <tr>
                <th style="width: 5%">#</th>
                <th style="width: 15%">Item Type</th>
                <th style="width: 25%">Item Name</th>
                <th style="width: 10%">Batch/Expiry</th>
                <th style="width: 10%">Quantity</th>
                <th style="width: 10%">Unit Price</th>
                <th style="width: 10%">GST %</th>
                <th style="width: 10%">Discount</th>
                <th style="width: 15%">Line Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in context_data %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>
                    <span class="badge bg-{{ item.item_type_color }}">
                        {{ item.item_type }}
                    </span>
                </td>
                <td>{{ item.item_name }}</td>
                <td>
                    {% if item.batch %}
                        <small>Batch: {{ item.batch }}</small><br>
                        <small>Exp: {{ item.expiry_date|date }}</small>
                    {% else %}
                        -
                    {% endif %}
                </td>
                <td class="text-end">{{ item.quantity }}</td>
                <td class="text-end">₹{{ item.unit_price|number_format }}</td>
                <td class="text-end">{{ item.gst_rate }}%</td>
                <td class="text-end">₹{{ item.discount_amount|number_format }}</td>
                <td class="text-end fw-bold">₹{{ item.line_total|number_format }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot class="table-light">
            <tr>
                <td colspan="8" class="text-end fw-bold">Subtotal:</td>
                <td class="text-end fw-bold">₹{{ context_data|sum('line_total')|number_format }}</td>
            </tr>
        </tfoot>
    </table>
</div>
```

---

### 7.2 Payment History Renderer

**Template:** `app/templates/engine/business/payment_history_table.html`

**Purpose:** Display payment history in invoice detail view

**Structure:**
```html
<div class="payment-history">
    {% if context_data %}
        <table class="table table-sm table-striped">
            <thead class="table-light">
                <tr>
                    <th>Payment Date</th>
                    <th>Reference</th>
                    <th>Cash</th>
                    <th>Card</th>
                    <th>UPI</th>
                    <th>Total</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for payment in context_data %}
                <tr>
                    <td>{{ payment.payment_date|datetime }}</td>
                    <td>{{ payment.payment_reference }}</td>
                    <td class="text-end">{% if payment.cash_amount %}₹{{ payment.cash_amount|number_format }}{% else %}-{% endif %}</td>
                    <td class="text-end">{% if payment.credit_card_amount or payment.debit_card_amount %}₹{{ (payment.credit_card_amount + payment.debit_card_amount)|number_format }}{% else %}-{% endif %}</td>
                    <td class="text-end">{% if payment.upi_amount %}₹{{ payment.upi_amount|number_format }}{% else %}-{% endif %}</td>
                    <td class="text-end fw-bold">₹{{ payment.total_amount|number_format }}</td>
                    <td>
                        <span class="badge bg-{{ payment.status_color }}">
                            {{ payment.payment_status }}
                        </span>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <div class="alert alert-info">
            No payments recorded yet.
        </div>
    {% endif %}
</div>
```

---

### 7.3 Advance Application History Renderer

**Template:** `app/templates/engine/business/advance_application_history.html`

**Purpose:** Display advance usage history

**Structure:**
```html
<div class="advance-applications">
    {% if context_data %}
        <table class="table table-sm">
            <thead class="table-light">
                <tr>
                    <th>Application Date</th>
                    <th>Invoice Number</th>
                    <th>Invoice Date</th>
                    <th>Amount Applied</th>
                    <th>Applied By</th>
                </tr>
            </thead>
            <tbody>
                {% for app in context_data %}
                <tr>
                    <td>{{ app.application_date|datetime }}</td>
                    <td>
                        <a href="{{ url_for('universal_views.universal_detail_view',
                                           entity_type='patient_invoices',
                                           item_id=app.invoice_id) }}">
                            {{ app.invoice_number }}
                        </a>
                    </td>
                    <td>{{ app.invoice_date|date }}</td>
                    <td class="text-end">₹{{ app.amount_applied|number_format }}</td>
                    <td>{{ app.applied_by_name }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <div class="alert alert-info">
            Advance has not been applied to any invoice yet.
        </div>
    {% endif %}
</div>
```

---

## 8. Cache Invalidation Strategy

### 8.1 Cache Invalidation Points

**When to Invalidate:**
- After invoice creation → Invalidate `patient_invoices`
- After payment recording → Invalidate `patient_payments` AND `patient_invoices` (paid_amount changed)
- After advance application → Invalidate `patient_advances` AND `patient_invoices`
- After void/cancel → Invalidate `patient_invoices`
- After refund → Invalidate `patient_payments`

**Import:**
```python
from app.engine.universal_service_cache import invalidate_service_cache_for_entity
```

**Usage:**
```python
# In service methods after DB commit
invalidate_service_cache_for_entity('patient_invoices', cascade=False)
```

**Cascade Parameter:**
- `cascade=False` (default) - Only invalidate the specified entity
- `cascade=True` - Invalidate related entities (use carefully)

---

## 9. Performance Considerations

### 9.1 Database Optimization

**Indexes Required:**
```sql
-- invoice_header table
CREATE INDEX IF NOT EXISTS idx_invoice_hospital_id ON invoice_header(hospital_id);
CREATE INDEX IF NOT EXISTS idx_invoice_branch_id ON invoice_header(branch_id);
CREATE INDEX IF NOT EXISTS idx_invoice_patient_id ON invoice_header(patient_id);
CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoice_header(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoice_header(is_cancelled, balance_due);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice_header(invoice_number);

-- payment_details table
CREATE INDEX IF NOT EXISTS idx_payment_invoice_id ON payment_details(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payment_hospital_id ON payment_details(hospital_id);
CREATE INDEX IF NOT EXISTS idx_payment_date ON payment_details(payment_date);

-- patient_advance_payments table
CREATE INDEX IF NOT EXISTS idx_advance_patient_id ON patient_advance_payments(patient_id);
CREATE INDEX IF NOT EXISTS idx_advance_hospital_id ON patient_advance_payments(hospital_id);
CREATE INDEX IF NOT EXISTS idx_advance_status ON patient_advance_payments(status, is_active);
```

**View Performance:**
- Test views with 10,000+ records
- Monitor query execution time
- Consider materialized views if refresh strategy defined
- Use EXPLAIN ANALYZE to optimize view queries

---

### 9.2 Caching Strategy

**Cache TTL:**
- List views: 30 minutes (frequent updates)
- Detail views: 30 minutes
- Configuration cache: 1 hour (rarely changes)

**Cache Keys Include:**
- Entity type
- Hospital ID
- Branch ID (if applicable)
- Filters (JSON-encoded)
- Sort field and direction
- Page number and size
- User ID (for permission-based caching)

**Cache Invalidation:**
- Automatic on create/update/delete
- Manual invalidation after bulk operations
- Clear all entity caches: `invalidate_service_cache_for_entity('patient_invoices')`

---

## 10. Testing Requirements

### 10.1 Unit Tests

**Service Tests:**
```python
# test_patient_invoice_service.py
def test_search_invoices_uses_view():
    """Verify search_data uses patient_invoices_view"""

def test_get_invoice_by_id_returns_complete_data():
    """Verify get_by_id returns all required fields"""

def test_create_invoice_invalidates_cache():
    """Verify cache cleared after invoice creation"""

def test_void_invoice_updates_status():
    """Verify void operation updates is_cancelled flag"""
```

**Configuration Tests:**
```python
# test_patient_invoice_config.py
def test_config_loads_without_errors():
    """Verify configuration imports successfully"""

def test_all_fields_defined():
    """Verify all view columns have field definitions"""

def test_actions_have_valid_routes():
    """Verify action URL patterns are correct"""
```

---

### 10.2 Integration Tests

**View Tests:**
```python
# test_patient_invoice_views.py
def test_list_view_accessible():
    """Test /universal/patient_invoices/list loads"""

def test_detail_view_accessible():
    """Test /universal/patient_invoices/detail/<id> loads"""

def test_filters_return_correct_results():
    """Test payment_status filter works"""

def test_custom_renderers_display():
    """Test line items table renders correctly"""
```

**Workflow Tests:**
```python
def test_create_invoice_to_detail_view_redirect():
    """Test invoice creation redirects to Universal detail view"""

def test_void_action_button_visible():
    """Test void button shows for non-cancelled invoices"""
```

---

### 10.3 Performance Tests

**Load Tests:**
```python
def test_list_view_performance_1000_records():
    """Verify list view loads in < 2s with 1000 invoices"""

def test_search_performance_with_filters():
    """Verify filtered search completes in < 1s"""

def test_export_performance_1000_records():
    """Verify export completes in < 5s for 1000 records"""
```

---

## 11. Migration Execution

### 11.1 Pre-Migration

- [ ] Back up production database
- [ ] Create test environment copy
- [ ] Verify all existing functionality works
- [ ] Document current performance baselines

### 11.2 Migration Steps

**Phase 1:**
1. Apply database view migrations
2. Test view queries
3. Verify performance
4. Add indexes

**Phase 2:**
1. Create configuration files
2. Test configurations load
3. Verify Universal list/detail views work
4. Review with stakeholders

**Phase 3:**
1. Refactor service classes
2. Run unit tests
3. Verify inherited methods work
4. Test cache invalidation

**Phase 4:**
1. Update routes (remove old, add redirects)
2. Update navigation
3. Run integration tests
4. User acceptance testing

**Phase 5:**
1. Implement custom renderers
2. Configure document layouts
3. Performance testing
4. Final validation

### 11.3 Post-Migration

- [ ] Monitor production logs
- [ ] Track performance metrics
- [ ] Gather user feedback
- [ ] Document lessons learned

---

## Appendix A: Reference Files

**Supplier Module References:**
- `app/config/modules/supplier_invoice_config.py` (1,421 lines)
- `app/config/modules/supplier_payment_config.py` (2,455 lines)
- `app/services/supplier_invoice_service.py`
- `app/services/supplier_payment_service.py`
- `app/database/view scripts/supplier payment view v2.0.sql`
- `app/models/views.py` (SupplierInvoiceView, SupplierPaymentView)

**Universal Engine Documentation:**
- Universal Engine Entity Configuration Complete Guide v6.0
- Universal Engine Entity Service Implementation Guide v3.0
- Entity Configuration Checklist for Universal Engine

**Migration Documents:**
- BILLING_MIGRATION_APPROACH.md (strategic approach)
- BILLING_MIGRATION_CHECKLIST.md (phase-based checklist)

---

## Appendix B: Key Contacts & Resources

**Technical Leads:**
- Development Lead: [Name]
- Database Administrator: [Name]
- QA Lead: [Name]

**Reference Implementations:**
- Supplier Module: Complete reference implementation
- Purchase Order Module: Transaction entity example
- Inventory Module: Master entity example

**Support Resources:**
- Universal Engine documentation in Project_docs/
- CLAUDE.md (project guidelines)
- SkinSpire Clinic HMS Technical Development Guidelines v3.0

---

## Appendix C: Critical Development Constraints

### MANDATORY Rules for Migration

**See Section 10 in BILLING_MIGRATION_APPROACH.md for complete details**

This appendix provides a quick reference to CRITICAL development constraints that MUST be followed:

#### **1. Model Mixins (REQUIRED)**

- ✅ Use `SoftDeleteMixin` for all deletion operations
  - NEVER use `session.delete()` for entities with soft delete
  - Use `entity.soft_delete(user_id, reason)` method
  - Update database views to include `is_deleted`, `deleted_at`, `deleted_by`
  - Update view models to include soft delete columns

- ✅ Use `ApprovalMixin` for approval workflows
  - Use fields: `approval_status`, `approved_by`, `approved_at`, `rejected_by`, `rejected_at`
  - Update database views to include approval fields
  - Implement workflow routes: approve, reject

#### **2. Database View Management (MANDATORY)**

- ✅ ALWAYS update `app/models/views.py` when creating/modifying database views
  - Step 1: Create SQL script in `migrations/`
  - Step 2: Add/update view model class in `app/models/views.py`
  - Step 3: Register in `get_view_model()` function
  - Step 4: Apply SQL script, test queries

#### **3. Security (MANDATORY)**

- ✅ ALL routes MUST have security decorators:
  ```python
  @login_required
  @require_web_branch_permission('module', 'action')
  ```
- ✅ ALL queries MUST filter by `hospital_id`
- ✅ Optionally filter by `branch_id` where applicable

#### **4. Universal Engine Artifacts (DO NOT MODIFY)**

- ❌ NEVER modify Universal Engine core files:
  - `app/engine/universal_entity_service.py`
  - `app/engine/universal_crud_service.py`
  - `app/views/universal_views.py`
  - `app/templates/engine/universal_*.html`

- ✅ Instead: Extend classes, use custom renderers, use custom routes

#### **5. Database Service Methods (REQUIRED)**

- ✅ ALWAYS use:
  - `get_db_session()` - Context manager for sessions
  - `get_entity_dict()` - Convert entity to dict
  - `get_detached_copy()` - Get detached copy for use outside session

#### **6. SQL Guidelines**

- ✅ PostgreSQL-compatible SQL only
- ✅ Simple, readable queries (avoid complex nesting)
- ✅ Views and indexes: ALLOWED
- ❌ Triggers: NOT ALLOWED (business logic belongs in Python)

#### **7. Business Logic Location**

- ✅ ALL business logic in Python services/controllers
- ❌ NO business logic in:
  - Database (triggers, stored procedures)
  - Templates (Jinja2)
  - JavaScript (frontend)

#### **8. Validation**

- ✅ Major validations in backend (MANDATORY)
- ✅ Frontend validations for UX only (optional)
- ✅ Backend MUST revalidate everything

#### **9. Code Verification (CRITICAL)**

Before writing code, VERIFY:
- [ ] Model fields exist in model definition
- [ ] View columns exist in both SQL view and view model
- [ ] Methods exist with correct signatures
- [ ] Configuration field names match model columns

#### **10. Backward Compatibility**

- ✅ Add optional parameters with defaults
- ✅ Keep existing method signatures working
- ❌ NEVER break existing calls with required parameters
- ✅ Use deprecation pattern if breaking change necessary

---

### Quick Reference Checklists

**Database View Checklist:**
- [ ] SQL script created in `migrations/`
- [ ] PostgreSQL-compatible, simple structure
- [ ] Includes soft delete fields (if applicable)
- [ ] Includes approval fields (if applicable)
- [ ] View model created in `app/models/views.py`
- [ ] ALL columns match exactly
- [ ] Registered in `get_view_model()`
- [ ] Indexes created on filtered columns

**Service Checklist:**
- [ ] Extends `UniversalEntityService`
- [ ] Uses `get_db_session()` context manager
- [ ] Uses `get_entity_dict()` for serialization
- [ ] Uses `get_detached_copy()` when needed
- [ ] Cache invalidation after modifications
- [ ] SoftDeleteMixin methods for deletion
- [ ] ApprovalMixin fields for workflows
- [ ] Security decorators on routes
- [ ] Hospital/branch filtering
- [ ] Backward compatibility maintained

**Quality Assurance:**
- [ ] All fields/methods verified to exist
- [ ] Security decorators on ALL routes
- [ ] Hospital_id filtering in ALL queries
- [ ] Cache invalidation implemented
- [ ] No Universal Engine core modifications
- [ ] Business logic in services only
- [ ] Backend validation complete
- [ ] Tests written and passing

---

**Document Version History:**
- v1.0 (January 2025) - Initial technical specifications

**Last Updated:** [Date]
**Next Review:** After Phase 2 completion
