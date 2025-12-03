# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skinspire v2 is a healthcare management system built on Flask with a sophisticated **Universal Engine** architecture that enables rapid development of entity CRUD operations through configuration rather than code duplication.

**Tech Stack:**
- Backend: Flask 3.1.0, SQLAlchemy 2.0.36, PostgreSQL 17
- Frontend: Jinja2 templates, TailwindCSS, vanilla JavaScript
- Authentication: Flask-Login, PyJWT, Redis (session management)
- Security: Custom RBAC system, field-level encryption (cryptography 42.0.2)
- Testing: pytest 8.3.4

## Key Reference Documents

The following master documents provide comprehensive guidance for working with this system. Always refer to these documents when working on specific areas:

### System Documentation
1. **Hospital Management System Master document v 4.0 16.01.2025**
   - Complete system architecture and design specifications
   - Business requirements and use cases
   - Module-wise functional specifications

2. **SkinSpire Clinic HMS Technical Development Guidelines v3.0**
   - Comprehensive development standards and best practices
   - Code organization and structure guidelines
   - Security and performance requirements

### Universal Engine Documentation
3. **Universal Engine Entity Configuration Complete Guide v6.0**
   - Detailed guide for creating and configuring entities
   - Field definitions, validation rules, and UI layout
   - Configuration examples and patterns

4. **Universal Engine Entity Service Implementation Guide v3.0**
   - Service layer implementation standards
   - Database operations and caching strategies
   - Standard service interface and conventions

5. **Entity Configuration Checklist for Universal Engine**
   - Step-by-step checklist for adding new entities
   - Validation and testing requirements
   - Common pitfalls and troubleshooting

**IMPORTANT**: Always consult these documents before:
- Adding new entities or modules
- Modifying core Universal Engine components
- Implementing new business logic or workflows
- Making architectural decisions

## Collaboration Guidelines

### Development Guidelines
- Follow comprehensive development guidelines described in **SkinSpire Clinic HMS Technical Development Guidelines v3.0**
- For a quick ready reckoner, follow **Project background and collaboration guidelines v2.md**

### Core Communication Principles
- Prioritize incremental, backward-compatible improvements
- Preserve existing code structure and functionality
- Provide minimal invasive, targeted solutions
- Maintain clear, precise communication

### Context and Understanding
- Carefully review all provided modules in attachments or in Project knowledge area
- Ask for clarification if context is unclear
- Verify project structure before suggesting changes
- Reference attached modules in recommendations
- Do not assume variable names, routes, methods in other artifacts
- Ask if you do not find information in attached documents or Project knowledge

### CRITICAL: Field Name and Configuration Verification
**NEVER assume or imagine field names, configuration parameters, or model attributes!**

Before writing ANY code that references database fields or configuration parameters:

1. **Database Model Fields** - ALWAYS verify against actual model definitions:
   - Check `app/models/transaction.py` for transaction models (Invoice, Payment, etc.)
   - Check `app/models/master.py` for master data models (Patient, Package, Supplier, etc.)
   - Check `app/models/views.py` for database view models
   - Check `app/models/base.py` for mixin fields (Timestamp, SoftDelete, Approval, Tenant)
   - **Reference**: `DATABASE_MODEL_FIELD_REFERENCE.md` - Quick reference for common fields

2. **Configuration Parameters** - ALWAYS verify against core definitions:
   - Check `app/config/core_definitions.py` for valid parameters in:
     - `FieldDefinition` - field configuration parameters
     - `ActionDefinition` - action button parameters
     - `TabDefinition`, `SectionDefinition` - UI layout parameters
   - DO NOT use parameters that don't exist in dataclass definitions

3. **Model Mixins** - Understand what fields are available:
   - `TimestampMixin`: `created_at`, `updated_at`, `created_by`, `updated_by`
   - `SoftDeleteMixin`: `is_deleted`, `deleted_at`, `deleted_by`
   - `TenantMixin`: `hospital_id` (via tenant_id property)
   - `ApprovalMixin`: `approved_by`, `approved_at`, `approval_status`
   - NOT ALL models have ALL mixins - check the class definition!

**Example Critical Mistakes:**
```python
# ❌ WRONG - Assuming field exists without checking
InvoiceHeader.is_deleted  # InvoiceHeader has NO SoftDeleteMixin!
InvoiceHeader.status      # InvoiceHeader has NO status column!
InvoiceLineItem.total     # Field is called line_total, not total!
Patient.patient_number    # Field is called mrn, not patient_number!
Patient.phone_number      # Phone is in contact_info JSONB field, not direct column!

# ✅ CORRECT - Verified against model
InvoiceHeader.is_cancelled  # Checked transaction.py:456
InvoiceLineItem.line_total  # Checked transaction.py:line_total field
Patient.mrn                 # Checked master.py:179 - Medical Record Number
Patient.contact_info.get('phone')  # Checked master.py:188 - JSONB field
```

**MANDATORY Verification Process (NO EXCEPTIONS):**
1. **Before writing ANY code**: Open and READ the actual model file
2. **List all Column() definitions**: Write down every field name you see
3. **Check class definition**: See which mixins are included
4. **Verify JSONB fields**: Check structure of JSON data (personal_info, contact_info, etc.)
5. **Only then write code**: Use ONLY the field names you verified in steps 1-4

**Common JSONB Fields (Require Extraction):**
- `Patient.personal_info` → Contains: first_name, last_name, dob, gender, marital_status
- `Patient.contact_info` → Contains: phone, email, address
- `Patient.emergency_contact` → Contains: name, relation, contact
- Extract using: `patient.contact_info.get('phone', '')` or handle as dict/string

**Import Verification:**
```python
# ❌ WRONG - Importing non-existent function
from app.services.database_service import to_dict  # Does NOT exist!

# ✅ CORRECT - Verify import exists before using
from app.services.database_service import get_entity_dict  # Verified in database_service.py:662
```

**Reference Documents:**
- `DATABASE_MODEL_FIELD_REFERENCE.md` - Quick field reference
- `app/models/transaction.py` - Transaction models
- `app/models/master.py` - Master data models
- `app/models/views.py` - Database views
- `app/models/base.py` - Mixin definitions
- `app/config/core_definitions.py` - Configuration parameters

**Consequences of Ignoring This Process:**
- ❌ Runtime AttributeError crashes application
- ❌ ImportError prevents application startup
- ❌ Feature fails when users try to use it
- ❌ Time wasted debugging preventable errors
- ❌ Loss of user trust and credibility

---

### CRITICAL: Configuration Validation and Testing ⚠️

**MANDATORY: Test EVERY configuration change before saying "done"**

#### Rule 1: Always Test Config Loading

```bash
cd "/path/to/project"
python -c "from app.config.modules.MODULE_NAME import config, filter_config, search_config; print('Config OK')"
```

**If this test FAILS, the configuration is BROKEN. Fix immediately!**

#### Rule 2: Verify Parameters Against core_definitions.py

**BEFORE adding ANY parameter to a configuration dataclass:**

1. Open `app/config/core_definitions.py`
2. Search for the class definition (FieldDefinition, ActionDefinition, SectionDefinition, etc.)
3. Verify the parameter EXISTS in the dataclass
4. Check the TYPE (str? bool? Optional[str]? Enum?)

**Common Critical Mistakes:**

```python
# ❌ WRONG - 'target' does NOT exist in ActionDefinition
ActionDefinition(
    id="print",
    target="_blank"  # ERROR!
)

# ❌ WRONG - 'display_condition' does NOT exist in SectionDefinition
SectionDefinition(
    conditional_display=True,
    display_condition="field > 0"  # ERROR!
)

# ❌ WRONG - ComplexDisplayType.BADGE does NOT exist
custom_renderer=CustomRenderer(
    type=ComplexDisplayType.BADGE  # ERROR!
)

# ✅ CORRECT - Verified in core_definitions.py
ActionDefinition(id="print")  # No target parameter

SectionDefinition(
    conditional_display="field > 0"  # Takes STRING directly, not boolean!
)

field_type=FieldType.STATUS_BADGE  # Use this for badges, not ComplexDisplayType
```

#### Rule 3: CustomRenderer ALWAYS Requires 'template'

```python
# ❌ WRONG - Missing required 'template' parameter
custom_renderer=CustomRenderer(
    context_function="get_data"
)

# ✅ CORRECT - template is REQUIRED
custom_renderer=CustomRenderer(
    template="components/fields/text_display.html",  # Required!
    context_function="get_data"
)
```

#### Rule 4: Valid Enum Values

**ComplexDisplayType** (from core_definitions.py):
- `MULTI_METHOD_PAYMENT`
- `BREAKDOWN_AMOUNTS`
- `CONDITIONAL_DISPLAY`
- `DYNAMIC_CONTENT`
- `ENTITY_REFERENCE`

**There is NO `BADGE` value!** Use `FieldType.STATUS_BADGE` instead.

#### Rule 5: Mandatory Module Exports

**EVERY entity config module MUST export THREE objects:**

```python
# At END of config file
config = ENTITY_CONFIG                    # Main configuration
filter_config = ENTITY_FILTER_CONFIG      # REQUIRED for filters to work!
search_config = ENTITY_SEARCH_CONFIG      # REQUIRED for search to work!
```

**Missing exports = Silent failures** (no errors, but filters/search don't work)

#### Rule 6: Field Type Selection

```python
# ❌ WRONG - FieldType.DATETIME with date-only format doesn't work
FieldDefinition(
    field_type=FieldType.DATETIME,
    format_pattern="%d/%b"  # Ignored!
)

# ✅ CORRECT - Use FieldType.DATE for date-only display
FieldDefinition(
    field_type=FieldType.DATE,
    format_pattern="%d/%b"
)

# ❌ WRONG - Shows "true"/"false"
field_type=FieldType.BOOLEAN

# ✅ CORRECT - Shows "Active"/"Inactive" badges
field_type=FieldType.STATUS_BADGE,
options=[
    {"value": "true", "label": "Active", "color": "success"},
    {"value": "false", "label": "Inactive", "color": "secondary"}
]
```

#### Validation Checklist (Before Completing ANY Config Work)

- [ ] Ran config loading test command
- [ ] Verified ALL parameters exist in `core_definitions.py`
- [ ] CustomRenderer includes `template` parameter
- [ ] Used correct enum values (checked source)
- [ ] All three exports present: `config`, `filter_config`, `search_config`
- [ ] Field types match intended display (DATE vs DATETIME)
- [ ] `conditional_display` is STRING, not boolean

**Reference Documents:**
- `app/config/core_definitions.py` - ALL valid configuration parameters
- `Universal Engine Entity Configuration Complete Guide v6.0.md` - Section 18A: Configuration Validation Rules
- Existing config modules - Search for examples before guessing

**Process When Unsure:**
```bash
# Search existing configs for examples
grep -r "conditional_display" app/config/modules/
grep -r "STATUS_BADGE" app/config/modules/
grep -r "CustomRenderer" app/config/modules/
```

---

### Separation of Concerns
- **Presentation layer**: HTML. Use JavaScript only where essential to deliver required user experience
- **Forms**: Should define structure and validation rules
- **Controllers**: Should handle data population and business logic
- **Services**: Should handle database operations
- **Universal Engine**: Leverage for building view, list, search, and create functions for a new entity

### Database Schema Management
**CRITICAL RULE: Database and Model Synchronization**

When modifying database schema (tables, views, columns, constraints), you MUST update the corresponding model files:

**For Tables:**
- SQL: Modify table in migration script (`migrations/*.sql`)
- Model: Update corresponding model in `app/models/*.py`
- **Both changes required before deployment**

**For Views:**
- SQL: Create/modify view in migration script (`migrations/*.sql`)
- Model: Update/create view model in `app/models/views.py`
- **Both changes required before deployment**

**Example - Adding a new view:**
```
1. Create SQL view: migrations/create_new_view.sql
2. Add model: app/models/views.py (class NewView)
3. Register: Update get_view_model() function
```

**Example - Adding a column:**
```
1. SQL: ALTER TABLE table_name ADD COLUMN new_column TYPE;
2. Model: Add Column definition to model class
```

**Why this matters:**
- SQLAlchemy uses model definitions to map database objects
- Missing model definitions cause runtime errors
- View queries fail if model doesn't match database schema
- Services cannot access new fields without model updates

**NEVER:**
- ❌ Create database tables/views without model definitions
- ❌ Modify database schema without updating models
- ❌ Change view column names without updating view model
- ❌ Add columns without adding to model class

### Database Policy: Python-Only Business Logic

**CRITICAL POLICY: All business logic MUST be in Python code. NO database triggers or stored procedures.**

**✅ ALLOWED in Database:**
1. **Tables**: Standard table definitions with constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL, CHECK)
2. **Indexes**: For performance optimization
   ```sql
   CREATE INDEX idx_invoice_patient ON invoice_header(patient_id);
   CREATE INDEX idx_payment_date ON payments(payment_date);
   ```
3. **Views** (Special Cases Only): Read-only database views for complex queries
   ```sql
   CREATE VIEW supplier_invoice_view AS
   SELECT i.*, s.supplier_name, s.contact_person
   FROM supplier_invoices i
   JOIN suppliers s ON i.supplier_id = s.supplier_id;
   ```
   - Use views ONLY for complex joins or denormalization
   - Never use views for business logic or calculations
   - Always create corresponding Python model in `app/models/views.py`

**❌ NEVER ALLOWED in Database:**
1. **Triggers**: NO triggers for ANY purpose (insert, update, delete)
   ```sql
   -- ❌ FORBIDDEN - Do NOT create triggers
   CREATE TRIGGER trg_update_status ...
   DROP FUNCTION IF EXISTS update_status();
   ```
2. **Stored Procedures**: NO stored procedures or functions with business logic
   ```sql
   -- ❌ FORBIDDEN - Do NOT create stored procedures
   CREATE FUNCTION calculate_total() ...
   CREATE PROCEDURE process_payment() ...
   ```
3. **Database-Level Calculations**: NO computed columns or generated columns with business logic
4. **Database-Level Workflows**: NO status updates, validations, or state machines in database

**WHY This Policy:**
- ✅ **Single Source of Truth**: All business logic in one place (Python)
- ✅ **Testable**: Can unit test business logic
- ✅ **Debuggable**: Can step through code, add logging
- ✅ **Version Controlled**: Changes tracked in git
- ✅ **Reviewable**: Code reviews catch bugs
- ✅ **Atomic Transactions**: Python controls transaction boundaries with proper rollback
- ❌ **Triggers Hide Logic**: Hard to debug, silent failures, no logging
- ❌ **Triggers Cause Issues**: Premature commits, nested transactions, rollback problems

**Example - WRONG (Trigger) vs CORRECT (Python):**

```sql
-- ❌ WRONG: Database trigger
CREATE OR REPLACE FUNCTION update_package_plan_status()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE package_payment_plans
    SET status = 'completed'
    WHERE plan_id = NEW.plan_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_package_status
AFTER UPDATE ON installment_payments
FOR EACH ROW EXECUTE FUNCTION update_package_plan_status();
```

```python
# ✅ CORRECT: Python service layer
class PackagePaymentService:
    def update_plan_status(self, plan_id, session):
        """Update plan status based on installments"""
        # Check installments
        all_paid = self._check_all_installments_paid(plan_id, session)

        # Update status in controlled transaction
        plan = session.query(PackagePaymentPlan).filter(
            PackagePaymentPlan.plan_id == plan_id
        ).first()

        if all_paid:
            plan.status = 'completed'
            logger.info(f"Plan {plan_id} marked as completed")

        # Transaction commits only when function completes successfully
        # Automatic rollback on any exception
```

**How to Remove Existing Triggers:**
```sql
-- Remove trigger and function
DROP TRIGGER IF EXISTS trigger_name ON table_name;
DROP FUNCTION IF EXISTS function_name();

-- Verify removal
SELECT trigger_name FROM information_schema.triggers
WHERE trigger_schema = 'public';
```

**Migration from Triggers to Python:**
1. Identify business logic in trigger
2. Implement same logic in Python service
3. Add proper error handling and logging
4. Test transaction rollback scenarios
5. Drop trigger from database
6. Document change in migration file

**Real Example from This Project:**
- ❌ Had: `trg_update_package_status` trigger auto-updating plan status
- ✅ Problem: Trigger overwrote 'discontinued' status to 'completed'
- ✅ Fix: Removed trigger, added status update logic to `PackagePaymentService`
- ✅ Result: Full control, proper rollback, debuggable code

### Database Service Methods for Detached Sessions

**CRITICAL: Understanding SQLAlchemy Session Lifecycle**

SQLAlchemy entities are attached to a session and become **detached** when the session closes. Accessing attributes of detached entities causes errors. Use these utility methods to safely work with entities outside session context.

**File**: `app/services/database_service.py`

#### Method 1: `get_entity_dict(entity)` - Convert to Dictionary

**Use When:**
- Returning data from API endpoints (JSON responses)
- Passing data to templates
- Serializing entity for cache storage
- Need dictionary representation for data manipulation

**Function Signature:**
```python
from app.services.database_service import get_entity_dict

def get_entity_dict(entity) -> Dict[str, Any]:
    """
    Convert entity to a dictionary with all non-internal attributes.
    Safe to use after the session closes.

    Args:
        entity: SQLAlchemy model instance

    Returns:
        Dictionary with entity attributes (excludes attributes starting with '_')
    """
```

**Example Usage:**
```python
# ✅ CORRECT: Convert to dict before session closes
from app.services.database_service import get_db_session, get_entity_dict

with get_db_session() as session:
    patient = session.query(Patient).filter_by(patient_id=patient_id).first()
    patient_dict = get_entity_dict(patient)  # Convert while session is open

# Session closed here - patient_dict is still usable
return jsonify({
    'success': True,
    'data': patient_dict
})

# ❌ WRONG: Accessing entity after session closes
with get_db_session() as session:
    patient = session.query(Patient).first()

# Session closed - accessing patient.full_name will cause DetachedInstanceError
return jsonify({'name': patient.full_name})  # ERROR!
```

**What It Returns:**
```python
# For a Patient entity, returns:
{
    'patient_id': '123e4567-e89b-12d3-a456-426614174000',
    'hospital_id': '789e4567-e89b-12d3-a456-426614174111',
    'mrn': 'PAT-00123',
    'full_name': 'John Doe',
    'contact_info': {'phone': '+91-9876543210', 'email': 'john@example.com'},
    'personal_info': {'dob': '1990-01-01', 'gender': 'M'},
    'is_active': True,
    'created_at': datetime(2025, 1, 1, 12, 0, 0),
    # ... all other non-internal attributes
}
```

#### Method 2: `get_detached_copy(entity)` - Create Detached Copy

**Use When:**
- Need to continue using the entity object after session closes
- Passing entity to functions that expect object attribute access
- Need hybrid property access (properties defined with @hybrid_property)
- Working with entity relationships that were already loaded

**Function Signature:**
```python
from app.services.database_service import get_detached_copy

def get_detached_copy(entity: T) -> T:
    """
    Create a detached copy of an entity with all loaded attributes.
    This creates a new instance that's safe to use after the session closes.

    Args:
        entity: SQLAlchemy model instance

    Returns:
        A new instance of the same class with copied attributes
    """
```

**Example Usage:**
```python
# ✅ CORRECT: Create detached copy before session closes
from app.services.database_service import get_db_session, get_detached_copy

with get_db_session() as session:
    invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()
    detached_invoice = get_detached_copy(invoice)  # Copy while session is open

# Session closed - detached_invoice is still usable
print(detached_invoice.invoice_number)  # Works!
print(detached_invoice.total_amount)    # Works!

# Can pass to other functions
result = process_invoice(detached_invoice)
```

**Important Limitations:**
- ⚠️ Only copies **loaded** attributes (attributes that were accessed while session was open)
- ⚠️ Does NOT copy relationships unless they were explicitly loaded
- ⚠️ Does NOT support lazy loading (relationships that load on access)

```python
# ✅ CORRECT: Load relationships before detaching
with get_db_session() as session:
    invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()

    # Access relationships to load them
    _ = invoice.line_items  # Force load
    _ = invoice.patient     # Force load

    detached_invoice = get_detached_copy(invoice)

# ❌ WRONG: Relationship not loaded
with get_db_session() as session:
    invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()
    detached_invoice = get_detached_copy(invoice)

# This will fail because line_items was never loaded
print(detached_invoice.line_items)  # ERROR! Relationship not loaded
```

#### Comparison: When to Use Which Method

| Scenario | Use `get_entity_dict` | Use `get_detached_copy` |
|----------|----------------------|------------------------|
| API JSON response | ✅ YES | ❌ No (use dict) |
| Template data | ✅ YES | ❌ No (use dict) |
| Cache storage | ✅ YES | ❌ No (use dict) |
| Need object attributes | ❌ No (use copy) | ✅ YES |
| Need hybrid properties | ❌ No (use copy) | ✅ YES |
| Simple attribute access | ✅ Either works | ✅ Either works |
| Working with relationships | ❌ No (relationships not in dict) | ✅ YES (if pre-loaded) |

#### Common Patterns

**Pattern 1: Service Layer Returns Dict**
```python
# In service layer (app/services/patient_service.py)
class PatientService:
    def get_patient_by_id(self, patient_id, hospital_id):
        with get_db_session() as session:
            patient = session.query(Patient).filter(
                Patient.patient_id == patient_id,
                Patient.hospital_id == hospital_id
            ).first()

            if not patient:
                return None

            # Convert to dict before returning
            return get_entity_dict(patient)
```

**Pattern 2: API Endpoint Returns JSON**
```python
# In API route (app/api/routes/billing.py)
@billing_bp.route('/api/invoice/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).filter_by(
            invoice_id=invoice_id
        ).first()

        if not invoice:
            return jsonify({'success': False, 'error': 'Not found'}), 404

        # Convert to dict for JSON response
        invoice_data = get_entity_dict(invoice)

    return jsonify({'success': True, 'data': invoice_data})
```

**Pattern 3: Multiple Entities to List of Dicts**
```python
# Convert query results to list of dicts
with get_db_session() as session:
    invoices = session.query(InvoiceHeader).filter(
        InvoiceHeader.hospital_id == hospital_id
    ).all()

    # Convert all to dicts
    invoice_list = [get_entity_dict(inv) for inv in invoices]

# Use invoice_list after session closes
return jsonify({'invoices': invoice_list})
```

#### Verification Before Using

**ALWAYS verify the function exists in database_service.py:**

```python
# ✅ CORRECT: Verified imports
from app.services.database_service import get_db_session, get_entity_dict, get_detached_copy

# ❌ WRONG: Non-existent function
from app.services.database_service import to_dict  # Does NOT exist!
```

**Available Functions** (`app/services/database_service.py`):
- `get_db_session()` - Get database session context manager (line 548)
- `get_entity_dict(entity)` - Convert entity to dict (line 662)
- `get_detached_copy(entity)` - Create detached copy (line 641)
- `get_db_engine()` - Get SQLAlchemy engine (line 575)
- `initialize_database()` - Initialize database connection (line 605)
- `close_db_connections()` - Close all connections (line 683)

#### Session Context Manager Pattern

**ALWAYS use context manager for database sessions:**

```python
# ✅ CORRECT: Context manager ensures proper cleanup
from app.services.database_service import get_db_session, get_entity_dict

def get_patient_data(patient_id):
    with get_db_session() as session:
        patient = session.query(Patient).filter_by(patient_id=patient_id).first()

        if not patient:
            return None

        # Convert to dict BEFORE session closes
        patient_dict = get_entity_dict(patient)

    # Session is closed here, but patient_dict is still usable
    return patient_dict

# ❌ WRONG: Manual session management (error-prone)
session = get_db_session()  # Wrong! This is a context manager, not a session
patient = session.query(Patient).first()  # Will fail
```

### Universal Engine Usage Guidelines
**References**:
- **Universal Engine Entity Configuration Complete Guide v6.0** (Configuration)
- **Universal Engine Entity Service Implementation Guide v3.0** (Service layer)
- **Entity Configuration Checklist for Universal Engine** (Quick reference)

**CRITICAL PRINCIPLE: Entity-Agnostic Code in Universal Engine**

Universal Engine artifacts (templates, views, services, data assemblers) MUST remain entity-agnostic:

✓ **DO:**
- Evaluate conditional logic in configuration-driven backend code (data assembler)
- Use generic field/section evaluation based on configuration
- Pass only processed, ready-to-display data to templates
- Keep templates completely generic with no entity-specific field names

✗ **DON'T:**
- Add entity-specific field names in universal templates (e.g., `cash_amount`, `supplier_name`)
- Add entity-specific conditions in universal views
- Hardcode entity-specific logic in universal services
- Use entity-specific queries in universal data assemblers

**Example - Conditional Section Display:**

```python
# ✅ CORRECT: Backend evaluation (entity-agnostic)
# In data_assembler.py - evaluates ANY conditional_display expression
def _should_display_section(self, section: Dict, item: Any) -> bool:
    conditional = section.get('conditional_display')
    if conditional:
        return eval(conditional, safe_namespace, item_attributes)
    return True

# ✗ WRONG: Template evaluation (entity-specific)
# In template - hardcoded entity fields
{% if item.cash_amount > 0 %}  <!-- DON'T DO THIS! -->
```

**CRITICAL: Universal Engine Usage by Model Type**

✓ **Master Models** (Suppliers, Patients, Medicines, Staff, etc.)
- Use Universal Engine for **FULL CRUD**: List, View, Create, Edit, Delete
- Routes: `/universal/<entity_type>/{list,detail,create,edit,delete}/<item_id>`
- All operations handled through Universal Engine
- Custom workflow actions only if needed (approve, archive, etc.)

✓ **Transaction Models** (Payments, Invoices, Purchase Orders, etc.)
- Use Universal Engine for **LIST and VIEW ONLY**
- Routes: `/universal/<entity_type>/{list,detail}/<item_id>`
- Create, Edit, Delete, Workflow Actions: Use **custom routes** in entity-specific blueprint
- Custom routes handle business logic, validations, approvals, GL posting

**Example: Supplier Payments (Transaction Model)**
```
✓ List:    /universal/supplier_payments/list (Universal Engine)
✓ View:    /universal/supplier_payments/detail/<id> (Universal Engine)
✗ Create:  /supplier/payment/record (Custom route - supplier_views.create_payment)
✗ Edit:    /supplier/payment/edit/<id> (Custom route - supplier_views.edit_payment)
✗ Approve: /supplier/payment/approve/<id> (Custom workflow route)
✗ Reject:  /supplier/payment/reject/<id> (Custom workflow route)
✗ Delete:  /supplier/payment/delete/<id> (Custom workflow route)
```

**Architecture Guidelines:**

✓ **Universal & Reusable**
- One component works for suppliers, patients, medicines, any entity
- Configuration drives all behavior
- No entity-specific code duplication

✓ **Backend-Heavy**
- Search logic in backend service
- Database queries optimized
- Results cached and formatted server-side

✓ **Configuration-Driven**
- Search fields, display format, filters all configured
- Easy to add new entity types
- Minimal code changes for new requirements

✓ **Minimal JavaScript**
- Only handles UI interactions
- Backend API provides all data
- Progressive enhancement

### Error Handling
- Fix ONLY the specific error
- No bundled improvements or refactoring
- Modify only error-related lines
- Provide minimal, targeted solutions

### CRITICAL: Debugging Approach

**MANDATORY: Trace Data Flow BEFORE Blaming Cache or Environment**

When debugging issues where data is not being saved or displayed correctly, follow this systematic approach:

#### Step 1: Map the Complete Data Flow (FIRST!)

Before making ANY changes, trace the full path:

```
Frontend (HTML/JS) → Form Submission → Flask Form Class → View Function → Service Layer → Database
```

**For the Free Item issue, the correct trace would have been:**
1. HTML hidden field: `.is-free-item` in template
2. JavaScript: `setFreeItem()` sets hidden field value
3. Form submission: `line_items-0-is_free_item=true` in POST data
4. **Flask Form Class**: `InvoiceLineItemForm` - DOES IT HAVE THIS FIELD?
5. Form processing: `form.process_line_items()` - DOES IT EXTRACT THIS FIELD?
6. View function: `billing_views.py` - extracts line items
7. Service layer: `billing_service.py` - saves to database
8. Database: `invoice_line_item.is_free_item` column

#### Step 2: Identify WHERE Data is Lost

Check each layer systematically:

```python
# Layer 1: Is form data being submitted?
# Check browser DevTools → Network → Form Data
# Look for: line_items-0-is_free_item=true

# Layer 2: Is Flask Form receiving it?
# Check: Does InvoiceLineItemForm have is_free_item field?
grep -n "is_free_item" app/forms/billing_forms.py

# Layer 3: Is form.process_line_items() extracting it?
# Read the function - does it include is_free_item in the dict?

# Layer 4: Is the view passing it to service?
# Check billing_views.py line item extraction

# Layer 5: Is the service saving it?
# Check billing_service.py InvoiceLineItem creation
```

#### Step 3: Fix at the Correct Layer

**Common Mistake**: Adding field extraction in view when the form class doesn't define the field!

```python
# ❌ WRONG: Adding extraction code without checking form class
# billing_views.py
item['is_free_item'] = request.form.get(f'line_items-{index}-is_free_item')
# This WON'T WORK if InvoiceLineItemForm doesn't have is_free_item field!

# ✅ CORRECT: First add field to form class
# billing_forms.py - InvoiceLineItemForm
is_free_item = HiddenField('Is Free Item', default='false')

# THEN the form will include it in line_items.data
```

#### Step 4: Cache is LAST Resort, Not First

**DO NOT blame cache until you've verified:**
1. The code logic is correct
2. The data flow is complete
3. All required fields are defined in form classes
4. All layers are processing the data correctly

**Cache issues are RARE. Logic errors are COMMON.**

```bash
# Only clear cache AFTER verifying code is correct:
find app/ -name "*.pyc" -delete
find app/ -type d -name "__pycache__" -exec rm -rf {} +
```

#### Debugging Checklist

Before asking user to "restart and try again":

- [ ] Traced complete data flow from frontend to database
- [ ] Verified form class defines all required fields
- [ ] Verified form processing method extracts all fields
- [ ] Verified view function passes all fields to service
- [ ] Verified service saves all fields to model
- [ ] Verified database column exists
- [ ] ONLY THEN consider cache issues

#### Real Example: Free Item Bug (December 2025)

**What went wrong:**
1. Kept blaming cache and asking for server restarts
2. Added debug logs in multiple places
3. Made fixes in billing_views.py (wrong layer)
4. Made fixes in billing_service.py (wrong layer)
5. Finally discovered: `InvoiceLineItemForm` was missing `is_free_item` field

**What should have been done:**
1. Trace: HTML → JS → Form Class → View → Service → DB
2. Check: `InvoiceLineItemForm` has `is_free_item`? NO!
3. Fix: Add `is_free_item = HiddenField(...)` to form class
4. Done in ONE fix instead of 10+ iterations

**Time wasted**: ~1 hour
**Time if done correctly**: ~5 minutes

### Problem-Solving Method
1. Understand current implementation
2. Identify precise issue
3. Propose minimal solution
4. Explain rationale
5. Highlight potential consequences

### Key Guiding Phrases
- "Incrementally improve"
- "Maintain existing structure"
- "Backward compatible enhancement"

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source C:/Users/vinod/AppData/Local/Programs/skinspire-env/Scripts/activate  # Git Bash
# OR
C:\Users\vinod\AppData\Local\Programs\skinspire-env\Scripts\activate.bat     # Windows CMD

# Install dependencies
pip install -r requirements.txt

# Install Tailwind (Node.js required)
npm install
```

### Database Operations
```bash
# Create/reset database with schema
python scripts/create_database.py

# Populate test data
python scripts/populate_test_data.py

# Apply database triggers (PostgreSQL)
python -c "from app.core.db_operations.triggers import apply_triggers; apply_triggers()"

# Database migrations (Alembic)
flask db migrate -m "migration message"
flask db upgrade
```

### Running the Application
```bash
# Development server (default: localhost:5000)
python run.py

# With specific host/port
FLASK_HOST=0.0.0.0 FLASK_PORT=5000 python run.py

# Debug mode
FLASK_DEBUG=1 python run.py
```

### TailwindCSS
```bash
# Build CSS once
npm run build:css

# Watch mode (auto-rebuild on changes)
npm run watch:css
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_security/test_authentication.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_login"
```

## High-Level Architecture

### Universal Engine Pattern

The core architectural innovation is the **Universal Engine** - a configuration-driven system that eliminates code duplication for entity management.

**Flow:**
```
Request → Universal View → Service Registry → Entity Service → Database
                ↓
         Entity Configuration (metadata)
```

**Key Components:**

1. **Entity Registry** (`app/config/entity_registry.py`)
   - Central registry mapping entity types to services, models, and configurations
   - Example: `'suppliers'`, `'purchase_orders'`, `'supplier_payments'`

2. **Entity Configurations** (`app/config/modules/*.py`)
   - Define fields, filters, validation, forms, and UI layout per entity
   - Uses dataclasses: `EntityConfiguration`, `FieldDefinition`, `TabDefinition`

3. **Universal Service Registry** (`app/engine/universal_services.py`)
   - Routes entity operations to appropriate service classes
   - Provides global functions: `get_universal_service()`, `search_universal_entity_data()`

4. **Universal Views** (`app/views/universal_views.py`)
   - Entity-agnostic routes: `/universal/<entity_type>/list`, `/universal/<entity_type>/detail/<id>`
   - Handles list, detail, create, edit operations for ANY registered entity

5. **Service Layer** (`app/services/*.py`)
   - Entity-specific services extend `UniversalEntityService`
   - Standard interface: `search_data()`, `get_by_id()`, `create()`, `update()`, `delete()`

6. **CRUD Convention** (`app/engine/universal_crud_service.py`)
   - Convention-based function naming: `create_supplier()`, `update_supplier()`, `delete_supplier()`
   - Automatically routes to correct service method

### Multi-Tenant Architecture

All operations are **hospital-scoped** with optional **branch-scoping**:

```python
# Context always includes:
hospital_id = current_user.hospital_id  # Required
branch_id = session.get('branch_id')    # Optional

# Database queries MUST filter by hospital:
query = query.filter(Model.hospital_id == hospital_id)
if branch_id and hasattr(Model, 'branch_id'):
    query = query.filter(Model.branch_id == branch_id)
```

### Model Mixins

Core mixins provide standard functionality (`app/models/base.py`):

- **TimestampMixin**: `created_at`, `updated_at`, `created_by`, `updated_by`
- **TenantMixin**: `tenant_id` property (maps to `hospital_id`)
- **SoftDeleteMixin**: `is_deleted`, `deleted_at`, `deleted_by` with cascade support
- **ApprovalMixin**: `approved_by`, `approved_at`, `approval_status`

### Blueprint Organization

**Frontend Views** (`app/views/`):
- `universal_views.py` - Generic entity views
- `supplier_views.py`, `gl_views.py`, `inventory_views.py`, `billing_views.py` - Domain-specific views
- `auth_views.py` - Login/logout pages

**API Routes** (`app/api/routes/`):
- `universal_api.py` - `/api/universal/<entity>/search`, `/api/universal/<entity>/autocomplete`
- Domain-specific APIs: `supplier.py`, `gl.py`, `inventory.py`, `billing.py`

**Security Routes** (`app/security/routes/`):
- `auth.py` - `/api/auth/*` (login, logout, validate, status)
- `security_management.py` - `/api/security/*` (encryption endpoints)
- `rbac.py` - Role-based access control
- `audit.py` - Audit logging

### Database Triggers

PostgreSQL triggers handle business logic at the database level (`app/core/db_operations/triggers.py`):
- **Audit trails**: Auto-populate timestamps and user fields
- **Validation**: Check business rules before data modification
- **Calculations**: Auto-calculate totals, due dates, outstanding amounts
- **Status updates**: Update entity status based on related records

Apply triggers: `python -c "from app.core.db_operations.triggers import apply_triggers; apply_triggers()"`

### Caching System

**Dual-layer caching** for performance:

1. **Service Cache** (`app/engine/universal_service_cache.py`)
   - Caches service method results (searches, queries)
   - TTL: 30 minutes (configurable)
   - Keys include: entity, operation, hospital, branch, filters, user
   - Decorator: `@cache_service_method()`

2. **Config Cache** (`app/engine/universal_config_cache.py`)
   - Caches entity configurations, field definitions
   - TTL: 1 hour (configurable)
   - Preloaded on app startup
   - Decorator: `@cache_universal(cache_type, operation_name)`

### Security System

**Authentication** (`app/security/authentication/`):
- Phone number as `user_id` (primary key)
- Password hashing with database triggers (pgcrypto)
- Session management with Redis support
- Login history tracking

**Authorization** (`app/security/authorization/`):
- Role-based access control (RBAC)
- Permissions: `can_view`, `can_add`, `can_edit`, `can_delete` per module
- Permission cache with invalidation
- Decorators: `@require_web_branch_permission(module, action)`

**Context Flow**:
```python
g.user = current_user
g.hospital_id = current_user.hospital_id
g.branch_id = session.get('branch_id')
g.branch_context = {...}  # Full branch metadata
```

## Conventions & Patterns

### Entity Naming
- **Plural form in code**: `purchase_orders`, `supplier_payments`, `suppliers`
- URL paths use plural: `/universal/purchase_orders/list`
- Configuration keys match entity type exactly

### Service Interface
All services implement this standard interface:
```python
def search_data(self, filters, hospital_id, branch_id=None, page=1, per_page=20, **kwargs):
    """Returns: {items, total, pagination, summary, applied_filters, success}"""

def get_by_id(self, item_id, hospital_id, **kwargs):
    """Returns single entity dict"""

def create(self, data, hospital_id, branch_id, **context):
    """Returns: {success, data/error, message}"""

def update(self, item_id, data, hospital_id, **context):
    """Returns: {success, data/error, message}"""

def delete(self, item_id, hospital_id, **context):
    """Returns: {success, message}"""
```

### CRUD Function Naming
Convention for `UniversalCRUDService`:
```python
create_supplier(data, hospital_id, branch_id, **context)
update_supplier(supplier_id, data, hospital_id, **context)
delete_supplier(supplier_id, hospital_id, **context)
```

### Standard Response Format
```python
# API responses
{
    'success': bool,
    'data': any,
    'message': str,
    'errors': [str],
    'timestamp': datetime,
    'metadata': {...}
}

# Service search responses
{
    'items': [dict],
    'total': int,
    'pagination': {
        'page': int,
        'per_page': int,
        'total_count': int,
        'total_pages': int,
        'has_prev': bool,
        'has_next': bool
    },
    'summary': {
        'total_count': int,
        'status_counts': dict,
        'total_amount': Decimal
    },
    'applied_filters': [str],
    'success': bool
}
```

### Filter Parameters
```python
filters = {
    'search': 'text',           # Text search
    'status': 'active',         # Status filter
    'date_from': '2024-01-01',  # Date range
    'date_to': '2024-12-31',
    'amount_min': 1000,         # Amount range
    'amount_max': 50000,
    'sort': 'po_date',          # Sorting
    'direction': 'desc'
}
```

### Database Views
Use read-only database views for complex queries (`app/models/views.py`):
- `PurchaseOrderView` - Denormalized PO data with supplier info
- `SupplierInvoiceView` - Invoice data with aging calculations
- `SupplierPaymentView` - Payment data with invoice summaries

Benefits: No app-level joins, faster queries, simpler code

### Transaction Model CRUD Workflow

**Example: Supplier Payments** (Complete implementation reference)

Transaction models use a hybrid approach combining Universal Engine (list/view) with custom routes (create/edit/workflow):

**1. List View** (Universal Engine)
- Route: `/universal/supplier_payments/list`
- Template: `supplier/payment_list.html`
- Service: `SupplierPaymentService.search_data()`
- Access: Sidebar menu, direct navigation

**2. Detail View** (Universal Engine)
- Route: `/universal/supplier_payments/detail/<payment_id>`
- Template: `supplier/payment_detail.html`
- Service: `SupplierPaymentService.get_by_id()`
- Access: From list view, invoice history, after workflow actions

**3. Create** (Custom Route)
- Route: `/supplier/payment/record` (`supplier_views.create_payment`)
- Template: `supplier/payment_create.html`
- Service: `SupplierPaymentService.create_payment()`
- Workflow:
  - Validate multi-method amounts (must sum to total within 0.01 tolerance)
  - Check approval threshold (₹10,000)
  - If amount < ₹10K: Auto-approve + post GL entries
  - If amount ≥ ₹10K: Set `workflow_status='pending_approval'`
  - Invalidate both `supplier_payments` and `supplier_invoices` caches

**4. Edit** (Custom Route)
- Route: `/supplier/payment/edit/<payment_id>` (`supplier_views.edit_payment`)
- Template: `supplier/payment_edit.html`
- Service: `SupplierPaymentService.update_payment()`
- Conditions: Only draft or rejected payments can be edited

**5. Approve** (Custom Workflow Route)
- Route: `/supplier/payment/approve/<payment_id>` (`supplier_views.approve_payment`)
- GET Template: `supplier/payment_approval_new.html`
- POST Service: `SupplierPaymentService.approve_payment()`
- Workflow:
  - Update `workflow_status='approved'`
  - Post GL entries via `create_supplier_payment_gl_entries()`
  - Set `gl_posted=True`, record approver and timestamp
  - Invalidate caches

**6. Reject** (Custom Workflow Route)
- Route: `/supplier/payment/reject/<payment_id>` (`supplier_views.reject_payment`)
- Template: `supplier/payment_approval_new.html` (action='reject')
- Service: `SupplierPaymentService.reject_payment()`
- Workflow: Set `workflow_status='rejected'`, record rejector and reason

**7. Delete** (Custom Workflow Route - Soft Delete)
- Route: `/supplier/payment/delete/<payment_id>` (`supplier_views.delete_payment`)
- Template: `supplier/payment_delete_confirm.html`
- Service: `SupplierPaymentService.delete_payment()`
- Workflow:
  - Check if GL posted: If yes, reverse GL entries first via `reverse_supplier_payment_gl_entries()`
  - Soft delete using `SoftDeleteMixin`: `payment.soft_delete(user_id, reason)`
  - Sets `is_deleted=True`, `deleted_at`, `deleted_by`
  - Conditions: Only draft or rejected payments can be deleted

**8. Restore** (Custom Workflow Route)
- Route: `/supplier/payment/restore/<payment_id>` (`supplier_views.restore_payment`)
- Service: `SupplierPaymentService.restore_payment()`
- Workflow: Set `is_deleted=False`, clear `deleted_at` and `deleted_by`

**Key Implementation Notes:**
- **Approval Threshold**: ₹10,000
- **GL Posting**: On approval, not creation (for payments requiring approval)
- **Cache Invalidation**: CRITICAL - Invalidate BOTH `supplier_payments` AND `supplier_invoices` caches using `invalidate_service_cache_for_entity(entity_type, cascade=False)`
- **Multi-Method Validation**: Cash + Cheque + Bank Transfer + UPI must equal total amount (0.01 tolerance)
- **Soft Delete**: Uses `SoftDeleteMixin` with cascade support, GL reversal before delete

## Adding a New Entity

To add a new entity to the Universal Engine:

1. **Create Model** (`app/models/master.py` or `transaction.py`):
   ```python
   class NewEntity(db.Model, TimestampMixin, TenantMixin, SoftDeleteMixin):
       __tablename__ = 'new_entities'
       entity_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
       hospital_id = db.Column(db.String(36), db.ForeignKey('hospital.hospital_id'))
       # ... other fields
   ```

2. **Create Configuration** (`app/config/modules/new_entity_config.py`):
   ```python
   config = EntityConfiguration(
       entity_type='new_entities',
       entity_category=EntityCategory.MASTER,
       fields=[...],
       sections=[...],
       tabs=[...],
       # ... other settings
   )
   ```

3. **Register Entity** (`app/config/entity_registry.py`):
   ```python
   'new_entities': EntityRegistration(
       category=EntityCategory.MASTER,
       module='app.config.modules.new_entity_config',
       service_class='app.services.new_entity_service.NewEntityService',
       model_class='app.models.master.NewEntity'
   )
   ```

4. **Create Service** (`app/services/new_entity_service.py`):
   ```python
   class NewEntityService(UniversalEntityService):
       def __init__(self):
           super().__init__('new_entities', NewEntity)

       def create_new_entity(self, data, hospital_id, branch_id, **context):
           # Implementation
   ```

5. **Create Form** (optional, `app/forms/new_entity_forms.py`):
   ```python
   class NewEntityForm(FlaskForm):
       # Field definitions
   ```

6. **Access**: Routes automatically available at:
   - `/universal/new_entities/list`
   - `/universal/new_entities/detail/<id>`
   - `/universal/new_entities/create`
   - `/universal/new_entities/edit/<id>`

## Important File Locations

### Core Engine
- `app/config/entity_registry.py` - Entity registration
- `app/config/modules/*.py` - Entity configurations
- `app/engine/universal_services.py` - Service registry
- `app/engine/universal_entity_service.py` - Base service class
- `app/engine/universal_crud_service.py` - CRUD operations
- `app/views/universal_views.py` - Generic views

### Models
- `app/models/base.py` - Mixins (Timestamp, Tenant, SoftDelete, Approval)
- `app/models/master.py` - Master data (Hospital, Branch, Staff, Patient, Supplier, Medicine)
- `app/models/transaction.py` - Transactions (User, PO, Invoice, Payment)
- `app/models/views.py` - Read-only database views
- `app/models/config.py` - Configuration tables

### Services
- `app/services/database_service.py` - DB session management, entity dict conversion
- `app/services/branch_service.py` - Branch context, user branch access
- `app/services/permission_service.py` - Permission checking
- `app/services/menu_service.py` - Dynamic menu generation
- `app/services/purchase_order_service.py` - PO operations
- `app/services/supplier_master_service.py` - Supplier CRUD
- `app/services/supplier_invoice_service.py` - Invoice management
- `app/services/supplier_payment_service.py` - Payment processing

### Security
- `app/security/authentication/auth_manager.py` - Authentication logic
- `app/security/authentication/session_manager.py` - Session management
- `app/security/authorization/rbac_manager.py` - RBAC implementation
- `app/security/routes/auth.py` - Auth endpoints
- `app/security/encryption/field_encryption.py` - Field-level encryption

### Database
- `app/core/db_operations/triggers.py` - PostgreSQL trigger management
- `scripts/create_database.py` - Database schema creation
- `scripts/populate_test_data.py` - Test data population

## Environment Variables

Required in `.env`:
```
# Database
DEV_DATABASE_URL=postgresql://user:pass@localhost:5432/skinspire_dev
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/skinspire_test
PROD_DATABASE_URL=postgresql://user:pass@localhost:5432/skinspire_prod

# Flask
SECRET_KEY=your-secret-key
FLASK_ENV=development
FLASK_DEBUG=1

# Redis (optional, for session management)
REDIS_URL=redis://localhost:6379/0
```

## Testing Approach

- Tests in `tests/` directory
- Use `conftest.py` for shared fixtures
- Database fixtures create isolated test data
- Security tests in `tests/test_security/`
- Run with `pytest -v`

## Common Pitfalls

1. **Always include hospital_id in queries** - Multi-tenant system requires hospital filtering on all queries
2. **Use context managers for DB sessions** - Always use `with get_db_session() as session:`
3. **Clear cache after updates** - Call cache invalidation after create/update/delete operations
4. **Apply database triggers** - Run trigger setup after schema changes
5. **Convention-based CRUD naming** - Follow `create_{entity}`, `update_{entity}` patterns exactly
6. **Entity type naming** - Always use plural form in configurations and registry
7. **Soft deletes** - Use `soft_delete()` method, not direct deletion
8. **Permission checks** - Always use `@require_web_branch_permission` decorator on views
9. **ActionDefinition parameters** - Only use parameters defined in `core_definitions.py`:
   - Use `url_pattern` (NOT `route_name`/`route_params`)
   - Use `confirmation_required=True` + `confirmation_message` together
   - NO `requires_post` parameter exists
10. **Route methods for actions** - Action routes must accept both GET and POST: `methods=['GET', 'POST']`
11. **Soft delete in database views** - When adding soft delete to an entity, update BOTH:
    - SQL view script in `app/database/view scripts/` (add `is_deleted`, `deleted_at`, `deleted_by` columns)
    - Python model in `app/models/views.py` (add corresponding Column definitions)
    - Run the SQL script to update the database view
12. **Soft delete configuration checklist**:
    - Add field definitions to entity config (`is_deleted`, `deleted_at`, `deleted_by`)
    - Set `enable_soft_delete=True` in entity configuration
    - Add soft delete configuration (`soft_delete_field`, `cascade_delete`, `delete_confirmation_message`)
    - Update database view SQL and Python model
    - Service functions handle the business logic
    - Routes accept both GET and POST methods
    - Action buttons use correct `ActionDefinition` parameters
13. **Cache invalidation for entity operations** - CRITICAL for list view refresh:
    - **WRONG**: `invoice_service.invalidate_cache(invoice_id)` - Only clears single record cache
    - **CORRECT**: `invalidate_service_cache_for_entity('entity_type', cascade=False)` - Clears ALL caches
    - Import: `from app.engine.universal_service_cache import invalidate_service_cache_for_entity`
    - Use after create/update/delete/restore operations to ensure list views refresh
    - List views have different cache keys (filters, pagination, sort) than detail views
    - Single record invalidation does NOT clear list view caches
14. **NEVER assume field names or configuration parameters** - ALWAYS verify before writing code:
    - ❌ DON'T write `InvoiceHeader.is_deleted` → InvoiceHeader has NO SoftDeleteMixin
    - ❌ DON'T write `InvoiceHeader.status` → No status column, must compute with case()
    - ❌ DON'T write `InvoiceLineItem.total` → Field is called `line_total`
    - ❌ DON'T write `Patient.patient_name` → Field is called `full_name`
    - ✅ DO check model definition in `app/models/transaction.py`, `app/models/master.py`
    - ✅ DO check `DATABASE_MODEL_FIELD_REFERENCE.md` for quick reference
    - ✅ DO verify which mixins the model has (SoftDelete, Approval, Timestamp, Tenant)
    - ✅ DO check `app/config/core_definitions.py` for valid configuration parameters
    - This prevents runtime AttributeError and saves debugging time

## CRITICAL: Database Migration & Model Development Checklist

**MANDATORY PROCESS - NO EXCEPTIONS**

When creating new database tables or models, follow this EXACT checklist to avoid preventable errors:

### ✅ Step 1: Research BEFORE Writing Code (15 minutes)

**DO NOT skip this step!** Time spent here saves hours of debugging later.

1. **Check if similar models exist**:
   ```bash
   # Search for similar table names
   grep -r "class Package" app/models/
   grep -r "__tablename__ = 'package" app/models/
   ```

2. **Read existing model files completely**:
   - Open `app/models/master.py` or `app/models/transaction.py`
   - Find similar models (e.g., if creating `PackageBOMItem`, look at `InvoiceLineItem`)
   - Note which mixins are used: `TimestampMixin`, `SoftDeleteMixin`, `TenantMixin`, `ApprovalMixin`

3. **Verify mixin requirements** in `app/models/base.py`:
   ```python
   # SoftDeleteMixin requires:
   is_deleted = Column(Boolean, default=False)
   deleted_at = Column(DateTime)
   deleted_by = Column(String(50))

   # TimestampMixin requires:
   created_at = Column(DateTime, default=datetime.now)
   updated_at = Column(DateTime, onupdate=datetime.now)
   created_by = Column(String(50))
   updated_by = Column(String(50))

   # TenantMixin requires:
   hospital_id = Column(UUID, ForeignKey('hospitals.hospital_id'))
   ```

4. **Check database schema for actual column names**:
   ```bash
   # Connect to database and check existing tables
   PGPASSWORD='password' psql -h localhost -U user -d database -c "\d table_name"

   # Look for actual column names (service_code vs code, mrp vs current_price)
   # Verify relationship column names
   ```

5. **Document your findings** - Write down:
   - ✓ Which mixins you need
   - ✓ Actual database column names
   - ✓ Required fields from mixins
   - ✓ Relationship column names

### ✅ Step 2: Create Migration Script

**Use consistent column naming:**

```sql
-- ❌ WRONG: Inconsistent naming
CREATE TABLE package_bom_items (
    sequence_order INTEGER  -- Model uses display_sequence!
);

-- ✅ CORRECT: Match model exactly
CREATE TABLE package_bom_items (
    display_sequence INTEGER  -- Matches model Column name
);
```

**Include ALL mixin fields:**

```sql
-- ❌ WRONG: Missing soft delete fields
CREATE TABLE package_bom_items (
    -- ... fields ...
    is_deleted BOOLEAN DEFAULT FALSE
    -- Missing: deleted_at, deleted_by
);

-- ✅ CORRECT: Complete soft delete fields
CREATE TABLE package_bom_items (
    -- ... fields ...
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50)
);
```

### ✅ Step 3: Create/Update Model Class

**Match migration exactly:**

```python
# ❌ WRONG: Column name doesn't match migration
class PackageBOMItem(Base, SoftDeleteMixin):
    sequence_order = Column(Integer)  # Migration has display_sequence!

# ✅ CORRECT: Exact match
class PackageBOMItem(Base, SoftDeleteMixin):
    display_sequence = Column(Integer)  # Matches migration
```

**Include all fields from migration:**

```python
# ❌ WRONG: Missing fields that exist in database
class PackageBOMItem(Base):
    item_name = Column(String(200))
    # Missing: current_price, line_total from migration

# ✅ CORRECT: All fields from migration
class PackageBOMItem(Base):
    item_name = Column(String(200))
    current_price = Column(Numeric(10, 2))
    line_total = Column(Numeric(10, 2))
```

### ✅ Step 4: Create Service Methods

**Critical: Database session scope**

```python
# ❌ WRONG: Session closed too early
def _add_virtual_calculations(self, result, item_id, **kwargs):
    with get_db_session() as session:
        item = session.query(Model).filter(...).first()
        virtual_data = {}

    # Session closed here! Following queries will fail:
    count = session.query(Model).count()  # ERROR!

# ✅ CORRECT: All queries inside session context
def _add_virtual_calculations(self, result, item_id, **kwargs):
    with get_db_session() as session:
        item = session.query(Model).filter(...).first()
        virtual_data = {}

        # All queries inside with block:
        count = session.query(Model).count()  # Works!
        virtual_data['count'] = count

    # Session closed here - safe
    return virtual_data
```

**Verify actual database field names:**

```python
# ❌ WRONG: Assuming field names
service = session.query(Service).first()
code = service.service_code  # Field is actually 'code'!
category = service.category  # Field is actually 'service_type'!

# ✅ CORRECT: Verified field names
service = session.query(Service).first()
code = service.code  # Checked in \d services
category = service.service_type  # Checked in \d services
```

### ✅ Step 5: Test BEFORE Declaring Complete

**MANDATORY: Run these tests**

1. **Test migration**:
   ```bash
   # Run migration
   psql -f migrations/file.sql

   # Verify table structure
   \d table_name

   # Check all columns exist
   SELECT * FROM table_name LIMIT 0;
   ```

2. **Test model import**:
   ```bash
   python -c "from app.models.master import NewModel; print('Model OK')"
   ```

3. **Test service methods**:
   ```bash
   # Test basic query
   python -c "
   from app.services.database_service import get_db_session
   from app.models.master import NewModel
   with get_db_session() as session:
       item = session.query(NewModel).first()
       print(f'Query OK: {item}')
   "
   ```

4. **Test in browser**:
   - Navigate to list view
   - Open detail view
   - Check browser console for errors
   - Check `logs/app.log` for database errors

### ✅ Step 6: Verify Checklist

**Before saying "complete", verify:**

- [ ] Migration column names EXACTLY match model Column() definitions
- [ ] ALL mixin fields included in migration (deleted_at, deleted_by, etc.)
- [ ] ALL fields from migration exist in model class
- [ ] Database session context manager includes ALL queries (check indentation!)
- [ ] Field references use ACTUAL database column names (verified with `\d`)
- [ ] Ran migration successfully (`psql -f migrations/file.sql`)
- [ ] Tested model import (`from app.models...`)
- [ ] Tested basic service query (verified no DetachedInstanceError)
- [ ] Tested in browser (list view + detail view work)
- [ ] Checked `logs/app.log` for any errors

### Real Example: Package BOM Implementation Mistakes

**What Went Wrong (November 2025):**

1. ❌ Migration used `sequence_order` but model had `display_sequence`
2. ❌ Forgot `deleted_at` and `deleted_by` required by `SoftDeleteMixin`
3. ❌ Model missing `current_price`, `line_total`, `session_description`, `prerequisites`
4. ❌ Service method referenced `service.service_code` (actual: `service.code`)
5. ❌ Database session closed too early - all virtual calculations failed
6. ❌ Declared "complete" without testing in browser

**Impact:**
- 4-5 error cycles debugging preventable issues
- User had to point out each error through logs
- Wasted 2+ hours on issues that should have been caught in 15 minutes of verification

**What Should Have Been Done:**

1. ✅ Read `PackagePaymentPlan` model to see BOM-like pattern
2. ✅ Checked `\d services` to see column names before writing code
3. ✅ Verified `SoftDeleteMixin` requirements in `base.py`
4. ✅ Tested migration before writing service code
5. ✅ Tested in browser before declaring complete

### Key Principle

**"Measure twice, cut once"** - 15 minutes of verification prevents hours of debugging.

---

## Git Workflow

Recent commits show focus on:
- Purchase Order (PO) module development
- Supplier invoice creation
- Universal engine enhancements

Main branch: `master`
