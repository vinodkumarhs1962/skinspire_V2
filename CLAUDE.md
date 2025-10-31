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

## Collaboration Guidelines

### Development Guidelines
- Follow comprehensive development guidelines described in **SkinSpire Clinic HMS Technical Development Guidelines v2.0**
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

### Separation of Concerns
- **Presentation layer**: HTML. Use JavaScript only where essential to deliver required user experience
- **Forms**: Should define structure and validation rules
- **Controllers**: Should handle data population and business logic
- **Services**: Should handle database operations
- **Universal Engine**: Leverage for building view, list, search, and create functions for a new entity

### Universal Engine for Entity List, View, Search and Create
Reference: **Universal Engine Master Architecture Revised Implementation Guide v2.0**

**Architecture Guidelines to Adhere to While Developing:**

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

## Git Workflow

Recent commits show focus on:
- Purchase Order (PO) module development
- Supplier invoice creation
- Universal engine enhancements

Main branch: `master`
