# Package Payment Plans - Master Reference Document

**Version:** 1.0
**Date:** 2025-01-11
**Author:** Development Team
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Business Requirements](#business-requirements)
3. [System Architecture](#system-architecture)
4. [Database Schema](#database-schema)
5. [Entity Configuration](#entity-configuration)
6. [Service Layer](#service-layer)
7. [API Endpoints](#api-endpoints)
8. [Frontend Implementation](#frontend-implementation)
9. [Workflow & Business Logic](#workflow--business-logic)
10. [Security & Permissions](#security--permissions)
11. [Testing Guide](#testing-guide)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)

---

## Overview

### What is Package Payment Plans?

Package Payment Plans is a module that allows clinics to sell service packages (e.g., "Laser Hair Reduction - 5 Sessions") to patients with flexible installment payment schedules. The system automatically manages:

- **Installment Tracking** - Split package cost into multiple payments with due dates
- **Session Scheduling** - Track service sessions as they are completed
- **Payment Integration** - Link to patient invoices and payment receipts
- **Status Management** - Handle active, completed, cancelled, and suspended plans

### Key Features

✅ **Invoice-based Creation** - Plans are created from approved invoices containing packages
✅ **Auto-generation** - Installments and sessions automatically created on plan creation
✅ **Cascading Workflow** - Patient → Invoice → Auto-populate package details
✅ **Flexible Installments** - Weekly, bi-weekly, or monthly payment schedules (up to 12 installments)
✅ **Session Tracking** - Mark sessions as scheduled, completed, cancelled, or no-show
✅ **Soft Delete Support** - Plans can be soft deleted and restored
✅ **Multi-tenant** - Hospital and branch scoped
✅ **Universal Engine Integration** - Uses standard CRUD patterns

### Use Cases

**Use Case 1: Sell Package to Patient**
1. Create invoice with package line item (e.g., Laser Hair Reduction - 5 Sessions, ₹50,000)
2. Approve invoice
3. Create payment plan from the invoice
4. System auto-generates 3 monthly installments and 5 scheduled sessions

**Use Case 2: Track Session Completion**
1. Patient comes for Session 1
2. Staff marks Session 1 as "Completed"
3. System updates: `completed_sessions = 1`, `remaining_sessions = 4`
4. Progress tracked automatically

**Use Case 3: Record Installment Payment**
1. Patient pays 1st installment of ₹16,666.67
2. Staff records payment against installment
3. System updates: `paid_amount` increases, `balance_amount` decreases
4. Installment status changes from "pending" to "paid"

---

## Business Requirements

### Functional Requirements

**FR-1: Plan Creation**
- User shall be able to create payment plans from approved invoices containing packages
- System shall auto-populate package details from the selected invoice
- User shall configure total sessions, installment count, frequency, and start date
- System shall automatically generate installment records and session records

**FR-2: Installment Management**
- System shall split total amount equally across installments
- System shall calculate due dates based on frequency (weekly, bi-weekly, monthly)
- System shall track installment status (pending, partial, paid, overdue)
- System shall link installment payments to payment receipts

**FR-3: Session Management**
- System shall generate session records with sequential numbering
- User shall be able to mark sessions as completed, cancelled, or no-show
- System shall track completed vs remaining sessions
- System shall calculate session completion percentage

**FR-4: Status Management**
- Plan status: active, completed, cancelled, suspended
- System shall update status based on payment and session completion
- User shall be able to cancel or suspend plans with reason
- System shall support soft delete with restore capability

**FR-5: Reporting & Views**
- System shall provide list view with patient, package, and financial details
- System shall show overdue installments
- System shall calculate plan age and payment percentage
- System shall support filtering by status, patient, date range

### Non-Functional Requirements

**NFR-1: Performance**
- Database view shall optimize list queries with joins
- Service cache shall reduce repeated database queries
- List view shall paginate (20 records per page)

**NFR-2: Data Integrity**
- Foreign key constraints to patient, invoice, package
- Cascade delete for installments and sessions
- Computed columns for remaining sessions and balance amount
- Audit trail for all changes

**NFR-3: Security**
- Permission-based access (view, create, edit, delete)
- Hospital and branch scoping for multi-tenancy
- Audit fields (created_by, updated_by, deleted_by)

**NFR-4: Usability**
- Cascading dropdowns for easy data entry
- Auto-population to reduce manual entry
- Clear error messages for validation failures
- Responsive design for mobile/tablet access

---

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  - Custom Create Form (Cascading Workflow)                      │
│  - Universal List View                                           │
│  - Universal Detail View                                         │
│  - JavaScript: Patient Autocomplete + Invoice Dropdown           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  - GET /api/universal/patients/search                           │
│  - GET /api/package/patient/{id}/invoices-with-packages         │
│  - POST /api/package/session/{id}/complete                      │
│  - GET /api/package/patient/{id}/pending-installments           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│  PackagePaymentService (extends UniversalEntityService)         │
│  - create() → Auto-generate installments and sessions           │
│  - get_patient_invoices_with_packages()                         │
│  - complete_session()                                            │
│  - get_pending_installments()                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  Models:                                                         │
│  - PackagePaymentPlan (table model)                             │
│  - PackagePaymentPlanView (view model for list operations)      │
│  - InstallmentPayment                                            │
│  - PackageSession                                                │
│                                                                  │
│  Database:                                                       │
│  - package_payment_plans (table)                                │
│  - package_payment_plans_view (view with joins)                 │
│  - installment_payments (table)                                 │
│  - package_sessions (table)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

**Create Payment Plan Flow:**
```
User Input (Browser)
   ↓
Custom Form (/package/payment-plan/create)
   ↓
JavaScript: Validate & Submit
   ↓
POST /package/payment-plan/create
   ↓
package_views.create_payment_plan()
   ↓
PackagePaymentService.create()
   ├─→ 1. Fetch package details
   ├─→ 2. Create plan record
   ├─→ 3. Auto-generate installments
   └─→ 4. Auto-generate sessions
   ↓
Database (package_payment_plans, installment_payments, package_sessions)
   ↓
Redirect to Detail View
   ↓
Display Plan with Installments & Sessions
```

**List View Data Flow:**
```
User Request
   ↓
GET /universal/package_payment_plans/list
   ↓
universal_views.universal_list_view()
   ↓
PackagePaymentService.search_data()
   ↓
Query: package_payment_plans_view (includes patient, package, invoice joins)
   ↓
Apply Filters (status, date range, patient)
   ↓
Apply Pagination (20 per page)
   ↓
Return Results
   ↓
Render List Template
```

---

## Database Schema

### Tables

#### 1. package_payment_plans

**Purpose:** Main table storing payment plan records

**Schema:**
```sql
CREATE TABLE package_payment_plans (
    -- Primary Keys
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(branch_id) ON DELETE SET NULL,

    -- Foreign Keys
    patient_id UUID NOT NULL REFERENCES patients(patient_id) ON DELETE RESTRICT,
    invoice_id UUID REFERENCES invoice_header(invoice_id) ON DELETE RESTRICT,
    package_id UUID REFERENCES packages(package_id) ON DELETE RESTRICT,

    -- Package Information (DEPRECATED - Use package relationship)
    package_name VARCHAR(255),
    package_description TEXT,
    package_code VARCHAR(50),

    -- Session Information
    total_sessions INTEGER NOT NULL,
    completed_sessions INTEGER NOT NULL DEFAULT 0,
    remaining_sessions INTEGER GENERATED ALWAYS AS (total_sessions - completed_sessions) STORED,

    -- Financial Information
    total_amount NUMERIC(12,2) NOT NULL,
    paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    balance_amount NUMERIC(12,2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,

    -- Installment Configuration
    installment_count INTEGER NOT NULL,
    installment_frequency VARCHAR(20) NOT NULL CHECK (installment_frequency IN ('weekly', 'biweekly', 'monthly')),
    first_installment_date DATE NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'suspended')),

    -- Cancellation
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by VARCHAR(15) REFERENCES users(user_id),
    cancellation_reason TEXT,

    -- Suspension
    suspended_at TIMESTAMP WITH TIME ZONE,
    suspended_by VARCHAR(15) REFERENCES users(user_id),
    suspension_reason TEXT,

    -- Notes
    notes TEXT,

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) NOT NULL REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),

    -- Soft Delete
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(15) REFERENCES users(user_id)
);
```

**Indexes:**
```sql
CREATE INDEX idx_package_plans_hospital ON package_payment_plans(hospital_id) WHERE is_deleted = false;
CREATE INDEX idx_package_plans_patient ON package_payment_plans(patient_id) WHERE is_deleted = false;
CREATE INDEX idx_package_plans_status ON package_payment_plans(status) WHERE is_deleted = false;
CREATE INDEX idx_package_plans_created_at ON package_payment_plans(created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_package_plans_package ON package_payment_plans(package_id);
CREATE INDEX idx_package_plans_invoice ON package_payment_plans(invoice_id);
```

**Foreign Key Constraints:**
- `patient_id` → `patients.patient_id` (RESTRICT - Cannot delete patient with active plans)
- `invoice_id` → `invoice_header.invoice_id` (RESTRICT - Cannot delete invoice with linked plans)
- `package_id` → `packages.package_id` (RESTRICT - Cannot delete package with active plans)
- `hospital_id` → `hospitals.hospital_id` (CASCADE - Delete plans when hospital deleted)
- `branch_id` → `branches.branch_id` (SET NULL - Nullify branch when branch deleted)

#### 2. installment_payments

**Purpose:** Stores individual installment records for each payment plan

**Schema:**
```sql
CREATE TABLE installment_payments (
    -- Primary Keys
    installment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,

    -- Foreign Key to Plan
    plan_id UUID NOT NULL REFERENCES package_payment_plans(plan_id) ON DELETE CASCADE,

    -- Installment Details
    installment_number INTEGER NOT NULL,
    due_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    paid_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    balance_amount NUMERIC(12,2) GENERATED ALWAYS AS (amount - paid_amount) STORED,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'partial', 'paid', 'overdue')),

    -- Payment Reference
    payment_id UUID REFERENCES payment_details(payment_id),
    payment_date TIMESTAMP WITH TIME ZONE,

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) NOT NULL REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),

    -- Constraint: Unique installment number per plan
    CONSTRAINT uq_plan_installment_number UNIQUE (plan_id, installment_number)
);
```

**Indexes:**
```sql
CREATE INDEX idx_installment_plan ON installment_payments(plan_id, installment_number);
CREATE INDEX idx_installment_status ON installment_payments(status);
CREATE INDEX idx_installment_due_date ON installment_payments(due_date) WHERE status IN ('pending', 'partial', 'overdue');
```

#### 3. package_sessions

**Purpose:** Stores individual session records for each payment plan

**Schema:**
```sql
CREATE TABLE package_sessions (
    -- Primary Keys
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,

    -- Foreign Key to Plan
    plan_id UUID NOT NULL REFERENCES package_payment_plans(plan_id) ON DELETE CASCADE,

    -- Session Details
    session_number INTEGER NOT NULL,
    session_date DATE,
    session_status VARCHAR(20) NOT NULL DEFAULT 'scheduled' CHECK (session_status IN ('scheduled', 'completed', 'cancelled', 'no_show')),

    -- Service Details
    service_name VARCHAR(255),
    service_notes TEXT,
    performed_by VARCHAR(15) REFERENCES users(user_id),

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) NOT NULL REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),

    -- Constraint: Unique session number per plan
    CONSTRAINT uq_plan_session_number UNIQUE (plan_id, session_number)
);
```

**Indexes:**
```sql
CREATE INDEX idx_package_sessions_plan ON package_sessions(plan_id, session_number);
CREATE INDEX idx_package_sessions_status ON package_sessions(session_status);
CREATE INDEX idx_package_sessions_date ON package_sessions(session_date) WHERE session_date IS NOT NULL;
```

### Views

#### package_payment_plans_view

**Purpose:** Denormalized view with patient, package, invoice, and computed fields for efficient list queries

**Location:** `app/database/view scripts/package_payment_plans_view v1.0.sql`

**Key Columns:**
- Patient Information: `patient_name`, `mrn`, `patient_phone`, `patient_email`, `patient_dob`, `patient_gender`
- Invoice Information: `invoice_number`, `invoice_date`, `invoice_status`, `invoice_total`, `invoice_paid`, `invoice_balance`
- Package Information: `package_name`, `package_price`, `package_code`, `package_description`
- Session Tracking: `total_sessions`, `completed_sessions`, `remaining_sessions`, `session_completion_percentage`
- Financial: `total_amount`, `paid_amount`, `balance_amount`, `payment_percentage`
- Computed Fields: `plan_age_days`, `next_due_date`, `next_session_date`, `has_overdue_installments`
- Status: `status`, `status_badge_color`

**Joins:**
```sql
FROM package_payment_plans ppp
INNER JOIN patients p ON ppp.patient_id = p.patient_id
LEFT JOIN packages pkg ON ppp.package_id = pkg.package_id
LEFT JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
LEFT JOIN branches b ON ppp.branch_id = b.branch_id
INNER JOIN hospitals h ON ppp.hospital_id = h.hospital_id
WHERE ppp.is_deleted = false
```

---

## Entity Configuration

### File Location
`app/config/modules/package_payment_plan_config.py`

### Key Configuration Elements

**Entity Type:** `package_payment_plans`

**Category:** `EntityCategory.MASTER` (supports full CRUD)

**Primary Key:** `plan_id`

**Searchable Fields:** `plan_id`, `patient_name`, `package_name`, `invoice_number`

**Default Sort:** `created_at DESC`

### Field Definitions

**Core Fields:**
```python
FieldDefinition(
    name='patient_id',
    label='Patient',
    field_type=FieldType.REFERENCE,
    required=True,
    autocomplete_enabled=True,
    entity_search_config=EntitySearchConfiguration(
        target_entity='patients',
        search_fields=['full_name', 'mrn', 'phone'],
        display_template='{full_name} ({mrn})',
        value_field='patient_id'
    )
)

FieldDefinition(
    name='package_id',
    label='Package',
    field_type=FieldType.REFERENCE,
    required=True,
    autocomplete_enabled=True,
    entity_search_config=EntitySearchConfiguration(
        target_entity='packages',
        search_fields=['package_name', 'package_code'],
        display_template='{package_name} - ₹{price}',
        value_field='package_id'
    )
)

FieldDefinition(
    name='invoice_id',
    label='Invoice',
    field_type=FieldType.REFERENCE,
    required=True
)
```

**Financial Fields:**
```python
FieldDefinition(name='total_amount', label='Total Amount', field_type=FieldType.CURRENCY, required=True),
FieldDefinition(name='paid_amount', label='Paid Amount', field_type=FieldType.CURRENCY, readonly=True),
FieldDefinition(name='balance_amount', label='Balance Amount', field_type=FieldType.CURRENCY, readonly=True),
```

**Session Fields:**
```python
FieldDefinition(name='total_sessions', label='Total Sessions', field_type=FieldType.INTEGER, required=True),
FieldDefinition(name='completed_sessions', label='Completed Sessions', field_type=FieldType.INTEGER, readonly=True),
FieldDefinition(name='remaining_sessions', label='Remaining Sessions', field_type=FieldType.INTEGER, readonly=True),
```

**Installment Fields:**
```python
FieldDefinition(name='installment_count', label='Number of Installments', field_type=FieldType.INTEGER, required=True),
FieldDefinition(
    name='installment_frequency',
    label='Installment Frequency',
    field_type=FieldType.SELECT,
    required=True,
    select_options=[
        {'value': 'weekly', 'label': 'Weekly'},
        {'value': 'biweekly', 'label': 'Bi-weekly'},
        {'value': 'monthly', 'label': 'Monthly'}
    ]
),
FieldDefinition(name='first_installment_date', label='First Installment Date', field_type=FieldType.DATE, required=True),
```

### Section Definitions

**Detail View Sections:**
```python
PACKAGE_PAYMENT_PLAN_SECTIONS = [
    SectionDefinition(
        id="basic_info",
        title="Basic Information",
        fields=['patient_id', 'invoice_id', 'package_id', 'status'],
        collapsible=False
    ),
    SectionDefinition(
        id="financial_info",
        title="Financial Details",
        fields=['total_amount', 'paid_amount', 'balance_amount'],
        collapsible=True
    ),
    SectionDefinition(
        id="session_info",
        title="Session Tracking",
        fields=['total_sessions', 'completed_sessions', 'remaining_sessions'],
        collapsible=True
    ),
    SectionDefinition(
        id="installment_config",
        title="Installment Configuration",
        fields=['installment_count', 'installment_frequency', 'first_installment_date'],
        collapsible=True
    )
]
```

### Actions

**List Actions:**
```python
ActionDefinition(
    id='view',
    label='View',
    action_type=ActionType.NAVIGATE,
    icon='fas fa-eye',
    button_class='btn-info',
    url_pattern='/universal/package_payment_plans/detail/{plan_id}'
)

ActionDefinition(
    id='cancel',
    label='Cancel Plan',
    action_type=ActionType.CUSTOM,
    icon='fas fa-ban',
    button_class='btn-warning',
    url_pattern='/package/payment-plan/cancel/{plan_id}',
    confirmation_required=True,
    confirmation_message='Are you sure you want to cancel this payment plan?'
)
```

### Soft Delete Configuration

```python
enable_soft_delete=True,
soft_delete_field='is_deleted',
soft_delete_cascade=['installments', 'sessions']
```

---

## Service Layer

### File Location
`app/services/package_payment_service.py`

### Class: PackagePaymentService

**Inheritance:** Extends `UniversalEntityService`

**Initialization:**
```python
def __init__(self):
    from app.models.views import PackagePaymentPlanView

    # Use view model for list/search operations
    super().__init__('package_payment_plans', PackagePaymentPlanView)
```

### Key Methods

#### 1. create()

**Purpose:** Create payment plan and auto-generate installments and sessions

**Signature:**
```python
def create(self, data: Dict, hospital_id: str, branch_id: Optional[str] = None, **context) -> Dict[str, Any]
```

**Parameters:**
- `data`: Form data containing patient_id, invoice_id, package_id, total_sessions, installment_count, etc.
- `hospital_id`: Current hospital ID (from g.hospital_id)
- `branch_id`: Current branch ID (from g.branch_id)
- `**context`: Additional context (created_by, etc.)

**Returns:**
```python
{
    'success': True,
    'data': {
        'plan_id': 'uuid',
        'patient_id': 'uuid',
        'package_id': 'uuid',
        'total_amount': 50000.00,
        'installments_generated': 3,
        'sessions_generated': 5
    },
    'message': 'Payment plan created successfully'
}
```

**Logic Flow:**
```python
1. Fetch package details from packages table
2. Auto-populate total_amount from package.price
3. Call parent create() to save plan record
4. Auto-generate installments:
   - Calculate installment amount = total_amount / installment_count
   - Calculate due dates based on frequency
   - Create installment_payments records
5. Auto-generate sessions:
   - Create package_sessions records with sequential numbering
   - Set status = 'scheduled'
6. Return success with plan_id
```

**Example:**
```python
service = PackagePaymentService()
result = service.create(
    data={
        'patient_id': 'patient-uuid',
        'invoice_id': 'invoice-uuid',
        'package_id': 'package-uuid',
        'total_sessions': 5,
        'installment_count': 3,
        'installment_frequency': 'monthly',
        'first_installment_date': '2025-02-01'
    },
    hospital_id='hospital-uuid',
    branch_id='branch-uuid',
    created_by='user001'
)
```

#### 2. get_patient_invoices_with_packages()

**Purpose:** Get all approved invoices for a patient that contain package line items

**Signature:**
```python
def get_patient_invoices_with_packages(self, patient_id: str, hospital_id: str) -> Dict[str, Any]
```

**Returns:**
```python
{
    'success': True,
    'invoices': [
        {
            'invoice_id': 'uuid',
            'invoice_number': 'INV-001',
            'invoice_date': '2025-01-11',
            'package_id': 'uuid',
            'package_name': 'Laser Hair Reduction - 5 Sessions',
            'package_price': 50000.00,
            'line_item_total': 50000.00
        }
    ],
    'count': 1
}
```

**Query:**
```python
SELECT
    ih.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ili.package_id,
    pkg.package_name,
    pkg.price AS package_price,
    ili.total AS line_item_total
FROM invoice_header ih
JOIN invoice_line_item ili ON ih.invoice_id = ili.invoice_id
JOIN packages pkg ON ili.package_id = pkg.package_id
WHERE
    ih.patient_id = :patient_id
    AND ih.hospital_id = :hospital_id
    AND ili.package_id IS NOT NULL
    AND ih.is_cancelled = false
    AND ih.is_deleted = false
ORDER BY ih.invoice_date DESC
```

#### 3. _fetch_package_details()

**Purpose:** Fetch package details from packages master table

**Signature:**
```python
def _fetch_package_details(self, package_id: str, hospital_id: str) -> Optional[Dict]
```

**Returns:**
```python
{
    'package_id': 'uuid',
    'package_name': 'Laser Hair Reduction - 5 Sessions',
    'price': 50000.00,
    'gst_rate': 18.00,
    'is_gst_exempt': False
}
```

#### 4. _auto_generate_installments()

**Purpose:** Generate installment records based on plan configuration

**Logic:**
```python
1. Calculate installment_amount = total_amount / installment_count
2. For each installment (1 to installment_count):
   - Calculate due_date based on frequency:
     - Weekly: first_date + (i-1) * 7 days
     - Biweekly: first_date + (i-1) * 14 days
     - Monthly: Add (i-1) months to first_date
   - Create InstallmentPayment record:
     - installment_number = i
     - due_date = calculated_date
     - amount = installment_amount
     - status = 'pending'
3. Save all installments to database
```

**Example Output:**
```
Installment 1: Due 2025-02-01, Amount ₹16,666.67, Status: pending
Installment 2: Due 2025-03-01, Amount ₹16,666.67, Status: pending
Installment 3: Due 2025-04-01, Amount ₹16,666.66, Status: pending
Total: ₹50,000.00
```

#### 5. _auto_generate_sessions()

**Purpose:** Generate session records based on total_sessions

**Logic:**
```python
1. For each session (1 to total_sessions):
   - Create PackageSession record:
     - session_number = i
     - session_status = 'scheduled'
     - session_date = NULL (to be scheduled later)
2. Save all sessions to database
```

**Example Output:**
```
Session 1: Status: scheduled
Session 2: Status: scheduled
Session 3: Status: scheduled
Session 4: Status: scheduled
Session 5: Status: scheduled
```

#### 6. complete_session()

**Purpose:** Mark a session as completed

**Signature:**
```python
def complete_session(self, session_id: str, hospital_id: str, **context) -> Dict[str, Any]
```

**Logic:**
```python
1. Fetch session record
2. Validate: session_status = 'scheduled'
3. Update:
   - session_status = 'completed'
   - session_date = today
   - performed_by = current_user
4. Update parent plan:
   - completed_sessions += 1
   - remaining_sessions = total_sessions - completed_sessions
5. Check if all sessions completed:
   - If yes, update plan.status = 'completed'
6. Invalidate cache
7. Return success
```

#### 7. get_pending_installments()

**Purpose:** Get all pending/partial installments for a patient

**Signature:**
```python
def get_pending_installments(self, patient_id: str, hospital_id: str) -> Dict[str, Any]
```

**Returns:**
```python
{
    'success': True,
    'installments': [
        {
            'installment_id': 'uuid',
            'plan_id': 'uuid',
            'package_name': 'Laser Hair Reduction - 5 Sessions',
            'installment_number': 1,
            'due_date': '2025-02-01',
            'amount': 16666.67,
            'paid_amount': 0.00,
            'balance_amount': 16666.67,
            'status': 'pending'
        }
    ],
    'total_pending_amount': 50000.00,
    'count': 3
}
```

---

## API Endpoints

### File Location
`app/api/routes/package_api.py`

### Endpoints

#### 1. Get Patient Invoices with Packages

**Method:** GET

**Route:** `/api/package/patient/<patient_id>/invoices-with-packages`

**Purpose:** Fetch all approved invoices for a patient that contain packages

**Authentication:** Required (`@login_required`)

**Request:**
```http
GET /api/package/patient/550e8400-e29b-41d4-a716-446655440000/invoices-with-packages
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "invoices": [
    {
      "invoice_id": "650e8400-e29b-41d4-a716-446655440001",
      "invoice_number": "INV-2025-001",
      "invoice_date": "2025-01-11",
      "package_id": "750e8400-e29b-41d4-a716-446655440002",
      "package_name": "Laser Hair Reduction - 5 Sessions",
      "package_price": 50000.00,
      "line_item_total": 50000.00
    }
  ],
  "count": 1
}
```

**Response (404 Not Found):**
```json
{
  "success": false,
  "error": "Patient not found",
  "invoices": [],
  "count": 0
}
```

**Used By:** Create payment plan form - Invoice dropdown population

#### 2. Complete Session

**Method:** POST

**Route:** `/api/package/session/<session_id>/complete`

**Purpose:** Mark a session as completed

**Authentication:** Required (`@login_required`)

**Request:**
```http
POST /api/package/session/850e8400-e29b-41d4-a716-446655440003/complete
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_date": "2025-01-11",
  "service_notes": "Patient completed session successfully",
  "performed_by": "user001"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Session marked as completed",
  "session": {
    "session_id": "850e8400-e29b-41d4-a716-446655440003",
    "session_number": 1,
    "session_status": "completed",
    "session_date": "2025-01-11"
  },
  "plan_updated": {
    "completed_sessions": 1,
    "remaining_sessions": 4
  }
}
```

**Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Session is already completed"
}
```

#### 3. Get Pending Installments

**Method:** GET

**Route:** `/api/package/patient/<patient_id>/pending-installments`

**Purpose:** Get all pending/partial installments for a patient

**Authentication:** Required (`@login_required`)

**Request:**
```http
GET /api/package/patient/550e8400-e29b-41d4-a716-446655440000/pending-installments
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "success": true,
  "installments": [
    {
      "installment_id": "950e8400-e29b-41d4-a716-446655440004",
      "plan_id": "a50e8400-e29b-41d4-a716-446655440005",
      "package_name": "Laser Hair Reduction - 5 Sessions",
      "installment_number": 1,
      "due_date": "2025-02-01",
      "amount": 16666.67,
      "paid_amount": 0.00,
      "balance_amount": 16666.67,
      "status": "pending",
      "is_overdue": false
    }
  ],
  "total_pending_amount": 50000.00,
  "overdue_count": 0,
  "count": 3
}
```

---

## Frontend Implementation

### Custom Create Form

#### Template Location
`app/templates/package/create_payment_plan.html`

#### JavaScript Location
`app/static/js/package_payment_plan_create.js`

#### Route
**Blueprint:** `package_views`
**URL:** `/package/payment-plan/create`
**Methods:** GET, POST
**Permission:** `require_web_branch_permission('package_payment_plan', 'create')`

#### UI Flow

**Step 1: Patient Selection**
```html
<!-- Patient Search Input -->
<input type="text" id="patient-search"
       placeholder="Type patient name, MRN, or phone number..."
       autocomplete="off">

<!-- Patient Results Dropdown (Dynamic) -->
<div id="patient-results" class="hidden">
  <!-- JavaScript populates results -->
</div>

<!-- Selected Patient Card (Hidden until selection) -->
<div id="selected-patient-card" class="hidden">
  <!-- Shows patient name, MRN, phone, email -->
</div>
```

**JavaScript:**
```javascript
// Debounced search (300ms)
searchInput.addEventListener('input', debounce(searchPatients, 300));

async function searchPatients(query) {
    const response = await fetch(`/api/universal/patients/search?q=${query}`);
    const data = await response.json();
    displayPatientResults(data.results);
}

function selectPatient(patientId) {
    selectedPatientId = patientId;
    // Show selected patient card
    // Hide search results
    // Load invoices for patient
    loadPatientInvoices(patientId);
}
```

**Step 2: Invoice Selection**
```html
<!-- Invoice Dropdown (Hidden until patient selected) -->
<div id="invoice-selection-section" class="hidden">
  <select id="invoice-select">
    <option value="">Select invoice with package...</option>
    <!-- JavaScript populates options -->
  </select>
</div>

<!-- No Invoices Message (Conditional) -->
<div id="no-invoices-message" class="hidden">
  This patient has no approved invoices containing package items.
</div>
```

**JavaScript:**
```javascript
async function loadPatientInvoices(patientId) {
    const response = await fetch(`/api/package/patient/${patientId}/invoices-with-packages`);
    const data = await response.json();

    if (data.invoices.length === 0) {
        // Show "No invoices" message
        select.innerHTML = '<option value="">No invoices with packages found</option>';
        select.disabled = true;
    } else {
        // Populate dropdown
        data.invoices.forEach(inv => {
            const option = `<option value="${inv.invoice_id}"
                                    data-package-id="${inv.package_id}"
                                    data-package-name="${inv.package_name}"
                                    data-total-amount="${inv.line_item_total}">
                ${inv.invoice_number} - ${inv.package_name} - ₹${inv.line_item_total}
            </option>`;
        });
    }
}
```

**Step 3: Auto-populate & Configure**
```html
<!-- Package Info (Auto-populated, Read-only) -->
<div class="bg-gray-50 rounded-lg p-4">
  <input type="text" id="package_name_display" readonly>
  <input type="text" id="total_amount_display" readonly>
</div>

<!-- Session Configuration -->
<input type="number" id="total_sessions" name="total_sessions" min="1" required>

<!-- Installment Configuration -->
<input type="number" id="installment_count" name="installment_count" min="1" max="12" required>
<select id="installment_frequency" name="installment_frequency" required>
  <option value="monthly">Monthly</option>
  <option value="biweekly">Bi-weekly</option>
  <option value="weekly">Weekly</option>
</select>
<input type="date" id="first_installment_date" name="first_installment_date" required>
```

**JavaScript:**
```javascript
function handleInvoiceSelection(e) {
    const selectedOption = e.target.options[e.target.selectedIndex];

    // Get data from option
    const packageId = selectedOption.dataset.packageId;
    const packageName = selectedOption.dataset.packageName;
    const totalAmount = selectedOption.dataset.totalAmount;

    // Update hidden fields
    document.getElementById('package_id').value = packageId;
    document.getElementById('total_amount').value = totalAmount;

    // Update display fields
    document.getElementById('package_name_display').value = packageName;
    document.getElementById('total_amount_display').value = '₹' + formatCurrency(totalAmount);

    // Show Step 3 section
    document.getElementById('plan-details-section').classList.remove('hidden');

    // Enable submit button
    document.getElementById('submit-button').disabled = false;
}
```

**Form Submission:**
```javascript
function handleFormSubmit(e) {
    // Validate all required fields
    if (!patientId || !invoiceId || !totalSessions || !installmentCount) {
        e.preventDefault();
        showError('Please fill all required fields');
        return false;
    }

    // Disable button to prevent double submission
    document.getElementById('submit-button').disabled = true;
    document.getElementById('submit-button').innerHTML =
        '<i class="fas fa-spinner fa-spin mr-2"></i>Creating...';

    return true; // Allow form submit
}
```

### Universal List View

**Route:** `/universal/package_payment_plans/list`

**Template:** `app/templates/engine/universal_list.html` (Generic)

**Data Source:** `PackagePaymentPlanView` (Database view)

**Columns Displayed:**
- Patient Name (with MRN)
- Package Name
- Invoice Number
- Total Amount
- Paid Amount
- Balance Amount
- Total Sessions
- Completed Sessions
- Status (badge)
- Created Date
- Actions (View, Cancel)

**Filters:**
- Status (active, completed, cancelled, suspended)
- Date Range (created_at)
- Patient (autocomplete)
- Package (autocomplete)

**Pagination:** 20 records per page

### Universal Detail View

**Route:** `/universal/package_payment_plans/detail/<plan_id>`

**Template:** `app/templates/engine/universal_view.html` (Generic)

**Data Source:** `PackagePaymentPlan` (Table model)

**Sections:**
1. **Basic Information** - Patient, Invoice, Package, Status
2. **Financial Details** - Total, Paid, Balance, Payment %
3. **Session Tracking** - Total, Completed, Remaining, Completion %
4. **Installment Configuration** - Count, Frequency, First Date
5. **Installments Table** - Custom template showing all installments
6. **Sessions Table** - Custom template showing all sessions
7. **Audit Trail** - Created by/at, Updated by/at

**Custom Templates:**
- `app/templates/engine/business/installment_payments_table.html`
- `app/templates/engine/business/package_sessions_table.html`

---

## Workflow & Business Logic

### Creating a Payment Plan

**Workflow Steps:**

1. **User navigates to create form**
   - URL: `/package/payment-plan/create`
   - Permission checked: `package_payment_plan_create`

2. **User searches for patient**
   - Types name/MRN/phone (min 2 characters)
   - JavaScript calls `/api/universal/patients/search?q={query}`
   - Results displayed in dropdown
   - User clicks to select patient

3. **System loads invoices**
   - JavaScript calls `/api/package/patient/{patient_id}/invoices-with-packages`
   - Only approved invoices with package line items returned
   - Dropdown populated with invoice options

4. **User selects invoice**
   - Package details auto-populate from selected invoice
   - Step 3 (Configure Plan) section appears

5. **User configures plan**
   - Enters total sessions (e.g., 5)
   - Enters installment count (e.g., 3)
   - Selects frequency (monthly)
   - Selects first installment date
   - Optionally adds notes

6. **User submits form**
   - JavaScript validates required fields
   - Form posts to `/package/payment-plan/create`

7. **Backend processes request**
   - `package_views.create_payment_plan()` called
   - `PackagePaymentService.create()` executed
   - Plan record created
   - Installments auto-generated (3 records)
   - Sessions auto-generated (5 records)

8. **User redirected to detail view**
   - URL: `/universal/package_payment_plans/detail/{plan_id}`
   - Shows created plan with installments and sessions

**Example Scenario:**

**Input:**
- Patient: John Doe (MRN: MRN001)
- Invoice: INV-2025-001
- Package: Laser Hair Reduction - 5 Sessions, ₹50,000
- Total Sessions: 5
- Installments: 3
- Frequency: Monthly
- First Date: 2025-02-01

**Output:**

**Plan Record:**
```
plan_id: a50e8400-e29b-41d4-a716-446655440005
patient_id: 550e8400-e29b-41d4-a716-446655440000
invoice_id: 650e8400-e29b-41d4-a716-446655440001
package_id: 750e8400-e29b-41d4-a716-446655440002
total_amount: 50000.00
paid_amount: 0.00
balance_amount: 50000.00
total_sessions: 5
completed_sessions: 0
remaining_sessions: 5
installment_count: 3
installment_frequency: monthly
first_installment_date: 2025-02-01
status: active
```

**Installments Generated:**
```
Installment 1: Due 2025-02-01, ₹16,666.67, Status: pending
Installment 2: Due 2025-03-01, ₹16,666.67, Status: pending
Installment 3: Due 2025-04-01, ₹16,666.66, Status: pending
```

**Sessions Generated:**
```
Session 1: Status: scheduled
Session 2: Status: scheduled
Session 3: Status: scheduled
Session 4: Status: scheduled
Session 5: Status: scheduled
```

### Recording Installment Payment

**Workflow Steps:**

1. **Patient pays installment**
   - Patient comes to clinic
   - Pays 1st installment amount (₹16,666.67)

2. **Staff records payment**
   - Navigate to Installment Payments screen
   - Select pending installment
   - Record payment with method (cash/card/UPI)

3. **System updates records**
   - Installment status: pending → paid
   - Installment paid_amount: 0 → 16666.67
   - Installment balance_amount: 16666.67 → 0
   - Plan paid_amount: 0 → 16666.67
   - Plan balance_amount: 50000 → 33333.33

4. **Payment receipt generated**
   - Receipt number assigned
   - Payment details recorded
   - GL entries posted (if applicable)

### Completing a Session

**Workflow Steps:**

1. **Patient arrives for session**
   - Patient comes for Session 1

2. **Staff marks session as completed**
   - Navigate to package plan detail view
   - Click "Complete" on Session 1
   - Enter session date and notes
   - Select staff who performed service

3. **System updates records**
   - Session status: scheduled → completed
   - Session date: set to today
   - Session performed_by: current user
   - Plan completed_sessions: 0 → 1
   - Plan remaining_sessions: 5 → 4

4. **Session completion percentage updated**
   - Calculation: (1 / 5) * 100 = 20%

5. **Plan status check**
   - If all sessions completed: Plan status → completed
   - If sessions remaining: Plan status remains active

### Cancelling a Payment Plan

**Workflow Steps:**

1. **User initiates cancellation**
   - Navigate to plan detail view
   - Click "Cancel Plan" action
   - Confirmation modal appears

2. **User confirms cancellation**
   - Enter cancellation reason
   - Click "Confirm"

3. **System processes cancellation**
   - Plan status: active → cancelled
   - Cancelled_at: set to now
   - Cancelled_by: current user
   - Cancellation_reason: saved

4. **Installments updated**
   - All pending installments: status → cancelled
   - Paid installments: remain as paid

5. **Sessions updated**
   - All scheduled sessions: status → cancelled
   - Completed sessions: remain as completed

### Suspending a Payment Plan

**Workflow Steps:**

1. **User initiates suspension**
   - Navigate to plan detail view
   - Click "Suspend Plan" action

2. **User provides reason**
   - Enter suspension reason (e.g., "Patient requested pause")
   - Click "Suspend"

3. **System processes suspension**
   - Plan status: active → suspended
   - Suspended_at: set to now
   - Suspended_by: current user
   - Suspension_reason: saved

4. **Installments and sessions**
   - No status change
   - Remain as-is but no actions allowed on suspended plan

5. **Resuming plan**
   - User clicks "Resume Plan"
   - Plan status: suspended → active
   - Suspension fields cleared

### Soft Deleting a Payment Plan

**Workflow Steps:**

1. **User initiates deletion**
   - Navigate to plan detail view
   - Click "Delete Plan" action
   - Confirmation modal with warning appears

2. **User confirms deletion**
   - Enter deletion reason
   - Click "Confirm Delete"

3. **System processes soft delete**
   - Plan is_deleted: false → true
   - Plan deleted_at: set to now
   - Plan deleted_by: current user
   - Cascade: All installments is_deleted = true
   - Cascade: All sessions is_deleted = true

4. **Plan hidden from list views**
   - Default filter: `WHERE is_deleted = false`
   - Plan no longer appears in list

5. **Restoring deleted plan**
   - Admin user accesses "Deleted Plans" view
   - Click "Restore" on plan
   - Plan is_deleted: true → false
   - Plan deleted_at: cleared
   - Cascade: All installments restored
   - Cascade: All sessions restored

---

## Security & Permissions

### Permission Modules

**Module Name:** `package_payment_plan`

**Actions:**
- `view` - View payment plans and details
- `create` - Create new payment plans
- `edit` - Edit existing payment plans
- `delete` - Soft delete payment plans
- `complete_session` - Mark sessions as completed
- `cancel_plan` - Cancel payment plans
- `suspend_plan` - Suspend payment plans
- `restore_plan` - Restore soft-deleted plans

### Role-Based Access

**Example Role Configuration:**

**Clinic Manager:**
- package_payment_plan_view: ✅
- package_payment_plan_create: ✅
- package_payment_plan_edit: ✅
- package_payment_plan_delete: ✅
- package_payment_plan_complete_session: ✅
- package_payment_plan_cancel_plan: ✅
- package_payment_plan_suspend_plan: ✅
- package_payment_plan_restore_plan: ✅

**Front Desk Staff:**
- package_payment_plan_view: ✅
- package_payment_plan_create: ✅
- package_payment_plan_edit: ❌
- package_payment_plan_delete: ❌
- package_payment_plan_complete_session: ❌
- package_payment_plan_cancel_plan: ❌
- package_payment_plan_suspend_plan: ❌
- package_payment_plan_restore_plan: ❌

**Therapist:**
- package_payment_plan_view: ✅
- package_payment_plan_create: ❌
- package_payment_plan_edit: ❌
- package_payment_plan_delete: ❌
- package_payment_plan_complete_session: ✅
- package_payment_plan_cancel_plan: ❌
- package_payment_plan_suspend_plan: ❌
- package_payment_plan_restore_plan: ❌

### Multi-Tenancy

**Hospital Scoping:**
- All queries MUST filter by `hospital_id = g.hospital_id`
- Users can only see plans for their hospital
- Cross-hospital access prevented at database and service layer

**Branch Scoping:**
- Optional filtering by `branch_id = g.branch_id`
- If user has branch restrictions, only see plans for assigned branches
- If user has hospital-wide access, see all branches

**Example Query:**
```python
query = session.query(PackagePaymentPlan)
query = query.filter(PackagePaymentPlan.hospital_id == g.hospital_id)

if g.branch_id and user_has_branch_restrictions:
    query = query.filter(PackagePaymentPlan.branch_id == g.branch_id)
```

### Audit Trail

**Tracked Fields:**
- `created_by` - User who created the plan
- `created_at` - Timestamp of creation
- `updated_by` - User who last updated the plan
- `updated_at` - Timestamp of last update
- `deleted_by` - User who soft deleted the plan
- `deleted_at` - Timestamp of soft deletion
- `cancelled_by` - User who cancelled the plan
- `cancelled_at` - Timestamp of cancellation
- `suspended_by` - User who suspended the plan
- `suspended_at` - Timestamp of suspension

**Database Triggers:**
- `track_user_changes` - Automatically populates created_by/updated_by
- `update_timestamp` - Automatically updates updated_at on any change

---

## Testing Guide

### Test Data Setup

**1. Create Test Hospital & Branch**
```sql
-- Hospital
INSERT INTO hospitals (hospital_id, name, license_no)
VALUES ('test-hospital-uuid', 'Test Clinic', 'LIC001');

-- Branch
INSERT INTO branches (branch_id, hospital_id, name)
VALUES ('test-branch-uuid', 'test-hospital-uuid', 'Main Branch');
```

**2. Create Test Patient**
```sql
INSERT INTO patients (patient_id, hospital_id, first_name, last_name, mrn, full_name, personal_info, contact_info)
VALUES (
    'test-patient-uuid',
    'test-hospital-uuid',
    'John',
    'Doe',
    'MRN001',
    'John Doe',
    '{"date_of_birth": "1990-01-01", "gender": "Male"}',
    '{"phone": "9876543210", "email": "john@test.com"}'
);
```

**3. Create Test Package**
```sql
INSERT INTO packages (package_id, hospital_id, package_name, package_code, price, gst_rate, is_gst_exempt)
VALUES (
    'test-package-uuid',
    'test-hospital-uuid',
    'Laser Hair Reduction - 5 Sessions',
    'PKG001',
    50000.00,
    18.00,
    false
);
```

**4. Create Test Invoice with Package**
```sql
-- Invoice Header
INSERT INTO invoice_header (
    invoice_id, hospital_id, branch_id, patient_id,
    invoice_number, invoice_date, grand_total, paid_amount, balance_due,
    is_cancelled, is_deleted
)
VALUES (
    'test-invoice-uuid',
    'test-hospital-uuid',
    'test-branch-uuid',
    'test-patient-uuid',
    'INV-TEST-001',
    '2025-01-11',
    50000.00,
    0.00,
    50000.00,
    false,
    false
);

-- Invoice Line Item (Package)
INSERT INTO invoice_line_item (
    line_item_id, invoice_id, hospital_id,
    package_id, item_name, quantity, price, total
)
VALUES (
    'test-line-item-uuid',
    'test-invoice-uuid',
    'test-hospital-uuid',
    'test-package-uuid',
    'Laser Hair Reduction - 5 Sessions',
    1,
    50000.00,
    50000.00
);
```

### Test Cases

#### TC-01: Create Payment Plan - Happy Path

**Preconditions:**
- Test patient exists
- Test package exists
- Test invoice with package exists and is approved

**Steps:**
1. Navigate to `/package/payment-plan/create`
2. Search for patient "John Doe"
3. Select patient from dropdown
4. Select invoice "INV-TEST-001" from dropdown
5. Verify package name auto-populates: "Laser Hair Reduction - 5 Sessions"
6. Verify total amount auto-populates: ₹50,000
7. Enter total sessions: 5
8. Enter installment count: 3
9. Select frequency: Monthly
10. Select first installment date: 2025-02-01
11. Click "Create Payment Plan"

**Expected Results:**
- Plan created successfully
- Redirected to detail view
- Plan record exists in database
- 3 installment records created:
  - Installment 1: Due 2025-02-01, ₹16,666.67
  - Installment 2: Due 2025-03-01, ₹16,666.67
  - Installment 3: Due 2025-04-01, ₹16,666.66
- 5 session records created (all status: scheduled)
- Plan status: active

**SQL Verification:**
```sql
SELECT * FROM package_payment_plans WHERE patient_id = 'test-patient-uuid';
SELECT * FROM installment_payments WHERE plan_id = '<created-plan-id>' ORDER BY installment_number;
SELECT * FROM package_sessions WHERE plan_id = '<created-plan-id>' ORDER BY session_number;
```

#### TC-02: Patient Autocomplete Search

**Steps:**
1. Navigate to `/package/payment-plan/create`
2. Type "Joh" in patient search
3. Wait 300ms (debounce)

**Expected Results:**
- API call to `/api/universal/patients/search?q=Joh`
- Dropdown appears with matching patients
- "John Doe (MRN001)" displayed

#### TC-03: Invoice Dropdown Filtering

**Preconditions:**
- Patient has 2 invoices:
  - Invoice A: Contains package (approved)
  - Invoice B: No package (approved)
  - Invoice C: Contains package (cancelled)

**Steps:**
1. Navigate to create form
2. Select patient

**Expected Results:**
- Invoice dropdown shows only Invoice A
- Invoice B not shown (no package)
- Invoice C not shown (cancelled)

#### TC-04: No Invoices with Packages

**Preconditions:**
- Patient has no approved invoices with packages

**Steps:**
1. Navigate to create form
2. Select patient

**Expected Results:**
- Invoice dropdown shows: "No invoices with packages found"
- Invoice dropdown disabled
- Warning message displayed: "This patient has no approved invoices containing package items"

#### TC-05: Complete Session

**Preconditions:**
- Payment plan exists with 5 sessions (all scheduled)

**Steps:**
1. Navigate to plan detail view
2. Click "Complete" on Session 1
3. Enter session date: Today
4. Enter notes: "Session completed successfully"
5. Click "Save"

**Expected Results:**
- Session 1 status: scheduled → completed
- Session 1 date: set to today
- Plan completed_sessions: 0 → 1
- Plan remaining_sessions: 5 → 4
- Session completion %: 0% → 20%

**SQL Verification:**
```sql
SELECT session_status, session_date FROM package_sessions WHERE session_number = 1 AND plan_id = '<plan-id>';
SELECT completed_sessions, remaining_sessions FROM package_payment_plans WHERE plan_id = '<plan-id>';
```

#### TC-06: Soft Delete Payment Plan

**Preconditions:**
- Payment plan exists

**Steps:**
1. Navigate to plan detail view
2. Click "Delete Plan"
3. Enter reason: "Test deletion"
4. Click "Confirm Delete"

**Expected Results:**
- Plan is_deleted: false → true
- Plan deleted_at: set to now
- Plan deleted_by: current user
- Plan no longer appears in list view
- Installments cascade deleted (is_deleted = true)
- Sessions cascade deleted (is_deleted = true)

**SQL Verification:**
```sql
SELECT is_deleted, deleted_at, deleted_by FROM package_payment_plans WHERE plan_id = '<plan-id>';
SELECT COUNT(*) FROM installment_payments WHERE plan_id = '<plan-id>' AND is_deleted = true;
SELECT COUNT(*) FROM package_sessions WHERE plan_id = '<plan-id>' AND is_deleted = true;
```

#### TC-07: Installment Due Date Calculation

**Test Data:**
```
First Date: 2025-02-01
Installments: 4
```

**Test Cases:**

**Weekly:**
- Installment 1: 2025-02-01
- Installment 2: 2025-02-08 (+7 days)
- Installment 3: 2025-02-15 (+7 days)
- Installment 4: 2025-02-22 (+7 days)

**Biweekly:**
- Installment 1: 2025-02-01
- Installment 2: 2025-02-15 (+14 days)
- Installment 3: 2025-03-01 (+14 days)
- Installment 4: 2025-03-15 (+14 days)

**Monthly:**
- Installment 1: 2025-02-01
- Installment 2: 2025-03-01 (+1 month)
- Installment 3: 2025-04-01 (+1 month)
- Installment 4: 2025-05-01 (+1 month)

**Verification:**
```sql
SELECT installment_number, due_date
FROM installment_payments
WHERE plan_id = '<plan-id>'
ORDER BY installment_number;
```

#### TC-08: Permission-Based Access

**Test Cases:**

**User with `package_payment_plan_view` only:**
- ✅ Can view list
- ✅ Can view detail
- ❌ Cannot create plan (redirect or 403)
- ❌ Cannot edit plan
- ❌ Cannot delete plan

**User with `package_payment_plan_create`:**
- ✅ Can access create form
- ✅ Can submit create form
- ✅ Plan created successfully

#### TC-09: Multi-Tenant Isolation

**Test Data:**
- Hospital A: Patient A, Package A, Invoice A
- Hospital B: Patient B, Package B, Invoice B

**Test Case 1: User from Hospital A**
1. Login as Hospital A user
2. Navigate to create form
3. Search for patients

**Expected Result:**
- Only Patient A appears in search results
- Patient B NOT visible

**Test Case 2: Cross-Hospital Access**
1. Login as Hospital A user
2. Manually access plan from Hospital B: `/universal/package_payment_plans/detail/<hospital-b-plan-id>`

**Expected Result:**
- 403 Forbidden or "Plan not found"
- No access to Hospital B data

### Performance Testing

**Test Case: List View Performance**

**Test Data:**
- 1000 payment plans in database
- 3000 installments (avg 3 per plan)
- 5000 sessions (avg 5 per plan)

**Test:**
1. Navigate to `/universal/package_payment_plans/list`
2. Measure page load time

**Expected Result:**
- Page loads in < 2 seconds
- View query uses package_payment_plans_view (pre-joined)
- No N+1 query issues
- Pagination limits to 20 records

**SQL Query Check:**
```sql
EXPLAIN ANALYZE
SELECT * FROM package_payment_plans_view
WHERE hospital_id = '<hospital-uuid>'
  AND is_deleted = false
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;
```

---

## Troubleshooting

### Issue 1: Patient Autocomplete Not Working

**Symptoms:**
- Search box not showing results
- No API call visible in Network tab

**Checks:**
1. **JavaScript loaded?**
   ```
   View page source → Check for:
   <script src="/static/js/package_payment_plan_create.js"></script>
   ```

2. **API endpoint accessible?**
   ```bash
   curl http://localhost:5000/api/universal/patients/search?q=John
   ```

3. **Browser console errors?**
   ```
   F12 → Console tab → Check for errors
   ```

**Common Fixes:**
- Clear browser cache
- Check file path in template
- Verify API route registered

### Issue 2: Invoice Dropdown Empty

**Symptoms:**
- Patient selected but invoice dropdown shows "No invoices found"

**Checks:**
1. **Does patient have approved invoices with packages?**
   ```sql
   SELECT ih.invoice_id, ih.invoice_number, ih.invoice_date,
          ili.package_id, pkg.package_name
   FROM invoice_header ih
   JOIN invoice_line_item ili ON ih.invoice_id = ili.invoice_id
   JOIN packages pkg ON ili.package_id = pkg.package_id
   WHERE ih.patient_id = '<patient-uuid>'
     AND ih.hospital_id = '<hospital-uuid>'
     AND ili.package_id IS NOT NULL
     AND ih.is_cancelled = false
     AND ih.is_deleted = false;
   ```

2. **API endpoint returning data?**
   ```bash
   curl http://localhost:5000/api/package/patient/<patient-uuid>/invoices-with-packages
   ```

3. **Check invoice status:**
   - Invoice must be approved (not draft)
   - Invoice must not be cancelled
   - Invoice must not be deleted

**Common Fixes:**
- Approve invoice if in draft status
- Ensure package_id in invoice line item
- Check hospital_id matches

### Issue 3: Installments Not Generated

**Symptoms:**
- Plan created but no installments in detail view

**Checks:**
1. **Check installments table:**
   ```sql
   SELECT * FROM installment_payments WHERE plan_id = '<plan-uuid>';
   ```

2. **Check service logs:**
   ```bash
   grep "Auto-generate installments" logs/app.log
   ```

3. **Check for exceptions:**
   ```sql
   SELECT * FROM error_logs WHERE context LIKE '%installment%' ORDER BY created_at DESC LIMIT 10;
   ```

**Common Fixes:**
- Check `_auto_generate_installments()` method for errors
- Verify installment_count > 0
- Verify first_installment_date is valid date
- Check database triggers not blocking insert

### Issue 4: Sessions Not Generated

**Symptoms:**
- Plan created but no sessions in detail view

**Checks:**
1. **Check sessions table:**
   ```sql
   SELECT * FROM package_sessions WHERE plan_id = '<plan-uuid>';
   ```

2. **Check total_sessions value:**
   ```sql
   SELECT total_sessions FROM package_payment_plans WHERE plan_id = '<plan-uuid>';
   ```

3. **Check service logs:**
   ```bash
   grep "Auto-generate sessions" logs/app.log
   ```

**Common Fixes:**
- Check `_auto_generate_sessions()` method for errors
- Verify total_sessions > 0
- Check database constraints on package_sessions table

### Issue 5: Permission Denied

**Symptoms:**
- User gets "Access Denied" or 403 error

**Checks:**
1. **Check user permissions:**
   ```sql
   SELECT rma.can_add, rma.can_edit, rma.can_delete, rma.can_view
   FROM users u
   JOIN role_master rm ON u.role_id = rm.role_id
   JOIN role_module_access rma ON rm.role_id = rma.role_id
   JOIN module_master mm ON rma.module_id = mm.module_id
   WHERE u.user_id = '<user-id>'
     AND mm.module_name = 'package_payment_plan';
   ```

2. **Check decorator:**
   ```python
   @require_web_branch_permission('package_payment_plan', 'create')
   ```

3. **Check session:**
   ```python
   print(g.hospital_id)
   print(g.branch_id)
   print(current_user.user_id)
   ```

**Common Fixes:**
- Grant appropriate permissions to user role
- Check module name spelling
- Verify user has active session

### Issue 6: Soft Delete Not Working

**Symptoms:**
- Deleted plans still appear in list view

**Checks:**
1. **Check is_deleted flag:**
   ```sql
   SELECT plan_id, is_deleted, deleted_at FROM package_payment_plans WHERE plan_id = '<plan-uuid>';
   ```

2. **Check list view query:**
   ```python
   # Should have: WHERE is_deleted = false
   ```

3. **Check view model:**
   ```python
   # PackagePaymentPlanView should filter is_deleted in SQL view definition
   ```

**Common Fixes:**
- Ensure view SQL has `WHERE ppp.is_deleted = false`
- Refresh materialized view if using one
- Check service query includes is_deleted filter

### Issue 7: Database View Out of Sync

**Symptoms:**
- Columns missing in view
- Query errors on view

**Checks:**
1. **Check view exists:**
   ```sql
   SELECT viewname FROM pg_views WHERE viewname = 'package_payment_plans_view';
   ```

2. **Check view definition:**
   ```sql
   \d+ package_payment_plans_view
   ```

3. **Compare with model:**
   ```python
   # app/models/views.py - PackagePaymentPlanView columns
   # Should match SQL view columns
   ```

**Common Fixes:**
- Re-run view SQL script:
  ```bash
  psql -f "app/database/view scripts/package_payment_plans_view v1.0.sql"
  ```
- Update model to match view columns
- Restart application

### Issue 8: Form Validation Errors

**Symptoms:**
- Form submission shows validation errors

**Common Validations:**
- Patient required
- Invoice required
- Total sessions >= 1
- Installment count 1-12
- First installment date >= today

**Checks:**
1. **Check browser console:**
   ```javascript
   // JavaScript validation errors
   ```

2. **Check server logs:**
   ```bash
   grep "validation" logs/app.log
   ```

3. **Check form data:**
   ```python
   print(request.form.to_dict())
   ```

**Common Fixes:**
- Ensure all required fields filled
- Check date format (YYYY-MM-DD)
- Verify numbers are positive
- Check hidden fields have values

---

## Future Enhancements

### Phase 2: Enhanced Features

**1. Installment Payment Integration**
- Link installments directly to payment receipts
- Auto-update installment status when payment recorded
- Show payment history per installment

**2. Session Scheduling**
- Calendar view for scheduling sessions
- Auto-schedule sessions based on frequency
- Send reminders to patients for upcoming sessions

**3. Overdue Installment Alerts**
- Dashboard widget showing overdue installments
- Automated SMS/email reminders
- Overdue aging report (0-30, 31-60, 61-90, 90+ days)

**4. Package Customization**
- Allow modification of package sessions for specific plans
- Add/remove sessions as needed
- Adjust installment amounts manually

**5. Partial Refunds**
- Handle refunds for cancelled plans
- Prorate refunds based on completed sessions
- Track refund amounts and reasons

**6. Reports & Analytics**
- Revenue by package type
- Session completion rate by therapist
- Installment collection efficiency
- Patient retention analysis

### Phase 3: Advanced Features

**1. Multi-Package Plans**
- Allow multiple packages in single plan
- Complex installment structures
- Combined session tracking

**2. Loyalty Integration**
- Apply loyalty points to installments
- Earn points on session completion
- Discount packages for loyal patients

**3. Mobile App Integration**
- Patients can view their plans via mobile app
- Session booking through app
- Payment reminders and history

**4. Insurance Integration**
- Link plans to insurance claims
- Track approved vs out-of-pocket amounts
- Insurance reimbursement tracking

**5. Staff Commission Tracking**
- Track commission per session completed
- Commission reports by staff member
- Payout management

---

## Appendix

### A. Database Migration Scripts

**Location:** `migrations/`

**Scripts:**
1. `add_package_reference_to_payment_plans.sql` - Add package_id FK
2. `add_invoice_reference_to_payment_plans.sql` - Add invoice_id FK
3. `add_soft_delete_to_package_payment_plans.sql` - Add soft delete fields
4. `create_package_payment_plans_view.sql` - Create database view

### B. File Structure

```
app/
├── config/
│   └── modules/
│       └── package_payment_plan_config.py
├── models/
│   ├── transaction.py (PackagePaymentPlan, InstallmentPayment, PackageSession)
│   └── views.py (PackagePaymentPlanView)
├── services/
│   └── package_payment_service.py
├── api/
│   └── routes/
│       └── package_api.py
├── views/
│   └── package_views.py
├── templates/
│   └── package/
│       └── create_payment_plan.html
├── static/
│   └── js/
│       └── package_payment_plan_create.js
└── database/
    └── view scripts/
        └── package_payment_plans_view v1.0.sql

migrations/
├── add_package_reference_to_payment_plans.sql
├── add_invoice_reference_to_payment_plans.sql
└── add_soft_delete_to_package_payment_plans.sql
```

### C. Quick Reference Commands

**Create Database View:**
```bash
PGPASSWORD='Skinspire123$' psql -h localhost -U skinspire_admin -d skinspire_dev -f "app/database/view scripts/package_payment_plans_view v1.0.sql"
```

**Run Migration:**
```bash
PGPASSWORD='Skinspire123$' psql -h localhost -U skinspire_admin -d skinspire_dev -f "migrations/add_soft_delete_to_package_payment_plans.sql"
```

**Check Plan Count:**
```sql
SELECT COUNT(*) FROM package_payment_plans WHERE is_deleted = false;
```

**Check Installments for Plan:**
```sql
SELECT installment_number, due_date, amount, status
FROM installment_payments
WHERE plan_id = '<plan-uuid>'
ORDER BY installment_number;
```

**Check Sessions for Plan:**
```sql
SELECT session_number, session_status, session_date
FROM package_sessions
WHERE plan_id = '<plan-uuid>'
ORDER BY session_number;
```

---

## Document Change History

| Version | Date       | Author           | Changes                                   |
|---------|------------|------------------|-------------------------------------------|
| 1.0     | 2025-01-11 | Development Team | Initial comprehensive reference document  |

---

**End of Document**
