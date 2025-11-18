Skinspire Clinic HMS Technical Development Guidelines
System Architecture Overview
Multi-Tenant Architecture
Skinspire HMS is designed as a multi-tenant system with the following characteristics:
Tenant Isolation: Each hospital operates as an independent tenant
Data Partitioning: Data separation by hospital_id at database level
Shared Infrastructure: Single codebase serving multiple tenants
Branch Support: Multiple branches can exist within a single tenant
Environment Architecture
The system operates across three separate environments:
Development Environment
Purpose: Active development and initial testing
Database: skinspire_dev
Configuration: More verbose logging, debug features enabled
Testing Environment
Purpose: Integration testing and QA
Database: skinspire_test
Configuration: Test-specific settings, isolated from development
Production Environment
Purpose: Live operation
Database: skinspire_prod
Configuration: Performance optimized, minimal logging, security hardened
Technical Stack
Backend: Python 3.12.8 + Flask 3.1.0
Database: PostgreSQL with SQLAlchemy ORM
Frontend: HTML/JavaScript with Tailwind CSS
Authentication: Custom JWT + Flask-Login hybrid system
Additional Tools: Polars (data analysis), ReportLab (reporting)
Centralized Environment Management
The system uses a centralized environment management approach:
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ENVIRONMENT MANAGEMENT SYSTEM                         │
│                                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────┐  │
│  │ Environment   │   │ Configuration │   │   Database    │   │ Testing   │  │
│  │ Detection     │   │ Management    │   │   Access      │   │ Framework │  │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └─────┬─────┘  │
│          │                   │                   │                 │        │
│          ▼                   ▼                   ▼                 ▼        │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────┐  │
│  │ environment.py│   │ db_config.py  │   │ database_     │   │ test_db_  │  │
│  │ env_setup.py  │   │ settings.py   │   │ service.py    │   │ setup.py  │  │
│  └───────────────┘   └───────────────┘   └───────────────┘   └───────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Environment detection occurs in app/core/environment.py
Configuration loading in app/config/db_config.py and app/config/settings.py
Database URLs and other settings are environment-specific
Switch environment using scripts/manage_db.py switch-env [env_name]
Project Structure and Organization
Key Directories
skinspire_v2/
├── app/                            # Main application package
│   ├── api/                        # API endpoints
│   │   ├── routes/                 # API route definitions by module
│   ├── config/                     # Configuration files
│   ├── core/                       # Core system functionality
│   │   ├── environment.py          # Environment management
│   │   ├── db_operations/          # Database operations
│   ├── database/                   # Database connection and SQL
│   │   ├── triggers/               # SQL trigger definitions
│   ├── forms/                      # Form definitions by module
│   ├── models/                     # SQLAlchemy models
│   │   ├── base.py                 # Base classes and mixins
│   │   ├── master.py               # Master data models
│   │   ├── transaction.py          # Transaction models
│   ├── security/                   # Security components
│   │   ├── authentication/         # Authentication logic
│   │   ├── authorization/          # Authorization/RBAC
│   │   ├── encryption/             # Data encryption
│   ├── services/                   # Business logic services
│   ├── static/                     # Frontend assets
│   ├── templates/                  # Jinja2 templates
│   │   ├── components/             # Reusable UI components
│   │   ├── layouts/                # Page layouts
│   ├── utils/                      # Utility functions
│   ├── views/                      # Web view handlers
├── migrations/                     # Alembic migrations
├── scripts/                        # Management scripts
│   ├── manage_db.py                # Database management CLI
├── tests/                          # Test suite
│   ├── test_environment.py         # Testing environment setup
│   ├── conftest.py                 # Test fixtures
Key Files Reference
FilePurposeUsageapp/core/environment.pyEnvironment detectionImport first in any module needing environment infoapp/config/db_config.pyDatabase configurationUse for database URL and connection settingsapp/services/database_service.pyDatabase accessUse for all database operationsapp/security/authentication/auth_manager.pyAuthenticationCentral point for authentication logicapp/security/authorization/permission_validator.pyPermission checkingUse for RBAC implementationapp/security/encryption/hospital_encryption.pyData encryptionUse for field-level encryptionscripts/manage_db.pyDatabase managementCLI for database operations
Database Layer Guidelines
Model Organization
Base Models (app/models/base.py): Reusable base classes and mixins
Master Data (app/models/master.py): Reference data models
Transaction Data (app/models/transaction.py): Operational data models
Database Access Pattern
Always use the centralized database service:
pythonfrom app.services.database_service import get_db_session

def my_function():
    with get_db_session() as session:
        # Database operations
        user = session.query(User).filter_by(user_id=user_id).first()
        # Modifications...
        session.flush()  # Make changes visible within transaction
        
        # Don't call session.commit() - handled by context manager
Session Management Patterns
Context Manager Pattern (for services and background tasks):
pythondef some_service():
    with get_db_session() as session:
        # Database operations
        # Automatically commits on success or rolls back on exception
Decorator-Based Pattern (for web routes with authentication):
python@app.route('/endpoint')
@token_required  # This creates and provides a session
def endpoint(current_user, session):
    # Use the provided session
    data = session.query(Model).filter_by(user_id=current_user.user_id).all()
Service Function Pattern (for reusable logic):
pythondef service_function(data, session=None):
    # Support both patterns above
    if session is not None:
        return _perform_operation(session, data)
    
    with get_db_session() as new_session:
        return _perform_operation(new_session, data)
Session Management Best Practices
Commit and Transaction Management
Proper commit and transaction management is critical for maintaining data integrity. The following guidelines help prevent common issues with database updates:
Understanding Commit Behavior in Session Patterns
Each session management pattern handles commits differently:

Context Manager Pattern:
pythonwith get_db_session() as session:
    # Database operations
    session.flush()  # Make changes visible within transaction
    # Don't call session.commit() - handled by context manager
The context manager should automatically commit on successful exit, but in complex operations, explicit commits may be necessary.
Service Function Pattern Modification:
For operations that must ensure commits occur properly:
pythondef service_function(data, session=None):
    if session is not None:
        # Running within an existing session - don't commit
        return _perform_operation(session, data)
    
    with get_db_session() as new_session:
        result = _perform_operation(new_session, data)
        # Explicit commit for critical operations
        new_session.commit()
        return result


Commit Troubleshooting Example
Here's an example of fixing a void invoice function where database changes weren't being committed:
Problem: The invoice is being marked as cancelled in the session, but changes aren't persisting to the database.
Before (problematic implementation):
pythondef void_invoice(hospital_id, invoice_id, reason, current_user_id=None, session=None):
    if session is not None:
        return _void_invoice(session, hospital_id, invoice_id, reason, current_user_id)
    
    with get_db_session() as new_session:
        result = _void_invoice(new_session, hospital_id, invoice_id, reason, current_user_id)
        # Missing explicit commit! Context manager might not be sufficient
        return result

def _void_invoice(session, hospital_id, invoice_id, reason, current_user_id=None):
    # Get the invoice
    invoice = session.query(InvoiceHeader).filter_by(
        hospital_id=hospital_id, invoice_id=invoice_id
    ).first()
    
    # Update invoice data
    invoice.is_cancelled = True
    invoice.cancellation_reason = reason
    invoice.cancelled_at = datetime.now(timezone.utc)
    
    # Only flush changes (make visible within transaction)
    session.flush()
    
    return get_entity_dict(invoice)
After (fixed implementation):
pythondef void_invoice(hospital_id, invoice_id, reason, current_user_id=None, session=None):
    if session is not None:
        return _void_invoice(session, hospital_id, invoice_id, reason, current_user_id)
    
    with get_db_session() as new_session:
        result = _void_invoice(new_session, hospital_id, invoice_id, reason, current_user_id)
        # Add explicit commit for critical operations
        new_session.commit()
        return result

def _void_invoice(session, hospital_id, invoice_id, reason, current_user_id=None):
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        # Update invoice data
        invoice.is_cancelled = True
        invoice.cancellation_reason = reason
        invoice.cancelled_at = datetime.now(timezone.utc)
        
        # Make changes visible within transaction
        session.flush()
        
        return get_entity_dict(invoice)
    except Exception as e:
        # Proper error handling with rollback
        session.rollback()
        logger.error(f"Error voiding invoice: {str(e)}")
        raise
When to Use Explicit Commits
Add explicit commits in the following scenarios:

Critical Updates: When updating important business entities (invoices, payments, inventory)
Multiple Related Changes: When multiple tables must be updated together
Complex Operations: When operations involve multiple steps that must succeed together
Transaction Isolation: When changes need immediate visibility to other sessions

Signs of Commit Issues
Watch for these signs of session/commit issues:

Records appear to update but revert when queried again
Logs show successful operations but database doesn't reflect changes
Operations work in development but fail in production
Intermittent data consistency problems

Testing Transaction Behavior
Always test critical data operations with:

Concurrent access scenarios
Process interruptions during transactions
Explicit verification after operations complete

Common Pitfalls to Avoid

Assuming Automatic Commits: Don't assume context managers always commit - use explicit commits for critical operations.
Nested Transaction Confusion: Be aware of transaction isolation levels when working with nested operations.
Missing Error Handling: Always include try/except with proper rollbacks to avoid partial commits.
Detached Entity Updates: Don't try to update entities after the session has closed.

Entity Lifecycle Management
When entities need to exist outside their session:
python# Create detached copy that won't try to lazy-load
from app.services.database_service import get_detached_copy
detached_entity = get_detached_copy(entity)

# Or convert to dictionary
from app.services.database_service import get_entity_dict
entity_dict = get_entity_dict(entity)
Handling Detached Entity Issues
Identifying Detached Entity Errors
Common error patterns that indicate detached entity issues:

DetachedInstanceError: Instance <Model at 0x...> is not bound to a Session
Accessing lazy-loaded attributes after a session closes
Errors occurring in test assertions after with get_db_session() blocks
Unexpected None values when accessing relationships outside their originating function

Root causes:

Accessing entity attributes after its session is closed
Returning entities from functions where sessions are locally scoped
Using entities across requests or transactions
Storing entity objects for later use

Solution Approaches

Use Entity Lifecycle Helper Functions

python# In database_service.py
def get_detached_copy(entity):
    """Create safe detached copy of entity"""
    if entity is None:
        return None
    EntityClass = entity.__class__
    detached = EntityClass()
    for key, value in entity.__dict__.items():
        if not key.startswith('_'):
            setattr(detached, key, value)
    return detached

def get_entity_dict(entity):
    """Convert entity to dictionary"""
    if entity is None:
        return None
    return {
        key: value for key, value in entity.__dict__.items()
        if not key.startswith('_')
    }

Extract Primitive Values Within Session

pythondef get_user_info(user_id):
    with get_db_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        # Extract primitives within session
        return {
            "id": user.id,
            "name": user.name,
            "status": user.status
        }

Use Eager Loading for Related Entities

pythonfrom sqlalchemy.orm import joinedload

def get_user_with_roles(user_id):
    with get_db_session() as session:
        user = session.query(User).options(
            joinedload(User.roles)
        ).filter_by(id=user_id).first()
        
        # Create detached copies while in session
        user_copy = get_detached_copy(user)
        role_copies = [get_detached_copy(role) for role in user.roles]
        
        # Build complete result with relationship preserved
        user_copy.roles = role_copies
        return user_copy

Test Fixture Pattern

python@pytest.fixture
def test_entity():
    with get_db_session() as session:
        entity = Entity(name="Test")
        session.add(entity)
        session.flush()
        
        # Safe copy for use after session closes
        detached_copy = get_detached_copy(entity)
        
        yield detached_copy
When to Use Each Approach

Detached Copy (get_detached_copy): For test fixtures, returning simple entity snapshots to clients
Dictionary Conversion (get_entity_dict): For API responses, serialization, when relationship traversal isn't needed
Primitive Extraction: When only specific attributes are needed
Eager Loading: For complex entity relationships that must be preserved outside the session

Common Patterns by Context
Web Routes:
python@app.route('/api/user/<user_id>')
def get_user(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        return jsonify(get_entity_dict(user))
Test Fixtures:
python@pytest.fixture
def test_user():
    with get_db_session() as session:
        user = create_user(session)
        return get_detached_copy(user)
Service Functions:
pythondef get_user_details(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        # Process within session context
        return process_user_data(user)
Model-Driven Database Migration
Define or modify models in appropriate files
Generate migrations: flask db migrate -m "Description"
Review the generated migration file in migrations/versions/
Apply migrations: flask db upgrade
Database Operations Using CLI
bash# Backup database
python scripts/manage_db.py create-backup

# Restore from backup
python scripts/manage_db.py restore-backup [backup_name]

# Copy database between environments
python scripts/manage_db.py copy-db --source dev --target test

# Apply triggers
python scripts/manage_db.py apply-db-triggers
Security Implementation
Authentication System
The application implements a dual-pattern authentication system:
API Authentication (auth.py):
Token-based (JWT) authentication
@token_required decorator for protection
Used for programmatic/AJAX access
Web UI Authentication (auth_views.py):
Session-based using Flask-Login
@login_required decorator for protection
Used for direct browser access
Authorization / RBAC
Permission definitions in permission_validator.py
Role-based access control implementation
Permission checking via:
pythonfrom app.security.authorization.permission_validator import has_permission
if has_permission(current_user, 'module_name', 'action'):
    # Perform protected operation
Encryption System
Field-level encryption for sensitive data
Implementation in app/security/encryption/hospital_encryption.py
Usage:
pythonfrom app.security.encryption.hospital_encryption import encrypt_field, decrypt_field

# Encrypt sensitive data
encrypted = encrypt_field(plaintext)

# Decrypt when needed
plaintext = decrypt_field(encrypted)
Frontend Development Guidelines
Template Structure
app/templates/
├── base.html                     # Base template with common structure
├── components/                   # Reusable UI components
│   ├── navigation.html           # Navigation components
│   ├── forms/                    # Form component templates
│   ├── tables/                   # Table component templates
├── layouts/                      # Page layouts
│   ├── dashboard.html            # Dashboard layout
│   ├── public.html               # Public pages layout
├── pages/                        # Page templates by module
│   ├── admin/                    # Admin pages
│   ├── patient/                  # Patient management pages
CSS Organization
app/static/css/
├── tailwind.css                  # Generated Tailwind CSS
├── components/                   # Component-specific styles
│   ├── buttons.css
│   ├── cards.css
│   ├── forms.css
│   ├── tables.css
JavaScript Organization
app/static/js/
├── common/                       # Shared utilities
│   ├── validation.js
│   ├── ajax-helpers.js
├── components/                   # Component behaviors
│   ├── datepicker.js
│   ├── modal.js
├── pages/                        # Page-specific scripts
├── appointment.js
Form Handling Pattern
python@app.route('/endpoint', methods=['GET', 'POST'])
@login_required
def endpoint():
    form = FormClass()
    
    if form.validate_on_submit():  # Includes CSRF validation
        try:
            with get_db_session() as session:
                # Process form data
                # ...
                
            flash('Operation successful', 'success')
            return redirect(url_for('some.endpoint'))
        except Exception as e:
            flash(f'Operation failed: {str(e)}', 'error')
            current_app.logger.error(f"Error: {str(e)}", exc_info=True)
    
    return render_template('template.html', form=form)
Component-Based Architecture
Create reusable templates in templates/components/
Use Jinja2 macros for complex components:
html{% macro input_field(field, label_class='', input_class='') %}
  <div class="form-group">
    {{ field.label(class=label_class) }}
    {{ field(class="form-control " + input_class) }}
    {% if field.errors %}
      <div class="error">{{ field.errors[0] }}</div>
    {% endif %}
  </div>
{% endmacro %}
Responsive Design Strategy
Use Tailwind's responsive utilities consistently
Follow mobile-first approach with progressive enhancement
Implement adaptive layouts for different screen sizes:
html<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <!-- Content adapts to screen size -->
</div>
Testing Guidelines
Environment Setup
Every test file should begin with:
python# At the top of each test file
from tests.test_environment import setup_test_environment

# Now safe to import app modules
import pytest
from app import create_app
Test Database Configuration
Tests automatically use the test database thanks to test_environment.py, which:
Sets FLASK_ENV=testing
Configures the test database URL
Disables nested transactions for testing
Testing Patterns
Unit Testing:
pythondef test_function():
    # Arrange
    test_data = {"field": "value"}
    
    # Act
    result = function_under_test(test_data)
    
    # Assert
    assert result.field == "value"
Database Testing:
pythondef test_database_operation():
    with get_db_session() as session:
        # Setup test data
        entity = Entity(name="Test")
        session.add(entity)
        session.flush()
        
        # Exercise function
        result = function_under_test(entity.id)
        
        # Verify
        assert result.name == "Test"
API Testing:
pythondef test_api_endpoint(client):
    # client is a pytest fixture
    response = client.post('/api/endpoint', 
                          json={"data": "value"},
                          headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    assert response.json["result"] == "expected"
Test Fixture Usage
Use fixtures from conftest.py for common test data:
python@pytest.fixture
def test_user():
    """Create a test user for authentication tests"""
    with get_db_session() as session:
        user = User(user_id="test_user", name="Test User")
        user.set_password("password")
        session.add(user)
        session.flush()
        
        # Create a detached copy for use after session closes
        return get_detached_copy(user)
Common Development Patterns
Adding a New Entity
Define Model:
python# app/models/transaction.py
class NewEntity(Base, TimestampMixin):
    __tablename__ = 'new_entities'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_gen)
    name = Column(String(100), nullable=False)
    # Other fields...
Create Migration:
bashflask db migrate -m "Add new entity"
flask db upgrade
Create Service:
python# app/services/new_entity_service.py
def create_entity(data, session=None):
    if session is not None:
        return _create_entity(session, data)
    
    with get_db_session() as new_session:
        return _create_entity(new_session, data)
        
def _create_entity(session, data):
    entity = NewEntity(**data)
    session.add(entity)
    session.flush()
    return entity
Create API Endpoint (if needed):
python# app/api/routes/new_entity.py
@api_bp.route('/new-entity', methods=['POST'])
@token_required
def create_new_entity(current_user, session):
    data = request.get_json()
    entity = _create_entity(session, data)
    return jsonify(get_entity_dict(entity)), 201
Create Web Route (if needed):
python# app/views/new_entity_views.py
@app.route('/new-entity/create', methods=['GET', 'POST'])
@login_required
def create_new_entity():
    form = NewEntityForm()
    
    if form.validate_on_submit():
        try:
            with get_db_session() as session:
                data = {
                    'name': form.name.data,
                    # Other fields...
                }
                entity = _create_entity(session, data)
                
            flash('Entity created successfully', 'success')
            return redirect(url_for('new_entity.list'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
            
    return render_template('new_entity/create.html', form=form)
Create Tests:
python# tests/test_new_entity.py
from tests.test_environment import setup_test_environment

def test_create_entity():
    with get_db_session() as session:
        # Test entity creation
        entity = _create_entity(session, {'name': 'Test Entity'})
        assert entity.name == 'Test Entity'
Error Handling Pattern
Always implement consistent error handling:
pythontry:
    # Operation that might fail
    with get_db_session() as session:
        # Database operations
except Exception as e:
    # Log the error with context
    logger.error(f"Error in module_name.function_name: {str(e)}", exc_info=True)
    
    # For API routes, return error response
    return jsonify({'error': str(e)}), 500
    
    # For web routes, show user-friendly message
    flash(f'Operation failed: {str(e)}', 'error')
    return redirect(url_for('fallback.route'))
Pitfalls to Avoid
Direct Session Creation: Never create database sessions directly
python# WRONG
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()

# RIGHT
from app.services.database_service import get_db_session
with get_db_session() as session:
    # Use session
Manual Transaction Control: Don't call commit/rollback directly
python# WRONG
session.commit()

# RIGHT
session.flush()  # When needed within a transaction
Global Session Storage: Never store sessions in global variables
Detached Entity Usage: Be careful with entities across session boundaries
python# WRONG
with get_db_session() as session:
    user = session.query(User).first()
# Session closed, user is detached
print(user.roles)  # This will fail!

# RIGHT
with get_db_session() as session:
    user = session.query(User).first()
    # Either use within session
    roles = [role.name for role in user.roles]
    # Or create detached copy
    user_copy = get_detached_copy(user)
Direct Database URL Access: Always use the database service
python# WRONG
from app.config.db_config import get_database_url
url = get_database_url()

# RIGHT
from app.services.database_service import get_db_session
with get_db_session() as session:
    # Use session
Inconsistent Form Validation: Always use WTForms validation for CSRF protection
Permission Bypassing: Always check permissions before sensitive operations
Development Workflow & Checklist
New Feature Implementation Checklist
Requirements Review
Understand functional requirements
Review relevant existing code
Identify required database changes
Database Layer
Add/modify models in appropriate files
Generate and review migrations
Apply migrations to development database
Service Layer
Implement business logic in service functions
Follow session management patterns
Include proper error handling
API Layer (if needed)
Create API endpoints with authentication/authorization
Implement input validation
Return appropriate status codes and responses
Web Interface (if needed)
Create/modify form classes
Implement view functions
Create/update templates
Testing
Write unit tests for service functions
Create API tests for endpoints
Test web interface if applicable
Documentation
Update relevant documentation
Add inline comments for complex logic
Environment Management
Development Environment: Default for local development
bash# Set to development
python scripts/manage_db.py switch-env development
Testing Environment: Used for automated tests
bash# Set to testing
python scripts/manage_db.py switch-env testing
Production Environment: Used only for production deployments
bash# Set to production
python scripts/manage_db.py switch-env production

Pattern Library: Core Implementation Patterns
1. Patient Search Implementation
The patient search functionality provides an intuitive, responsive search mechanism used throughout the application for patient selection. This pattern is used in forms, reports, and anywhere patient selection is required.
Key Components
Backend Service (patient_service.py)
pythondef search_patients(
    hospital_id: uuid.UUID,
    search_term: str = None,
    limit: int = 20,
    offset: int = 0
) -> List[Dict]:
    """
    Search patients with hybrid approach (dedicated fields + JSON fields)
    Returns consistently formatted patient information
    """
    # Implementation handles both dedicated fields and JSON fields
    # Uses SQLAlchemy for efficient queries
    # Falls back to JSON field searches for backward compatibility
API Endpoint
python@billing_views_bp.route('/web_api/patient/search', methods=['GET'])
@login_required
def web_api_patient_search():
    """Patient search API endpoint"""
    # Works with both new and old frontend implementations
    # Maintains consistent response format
    # Includes error handling with fallback mechanism
Frontend Component (patient_search.js)
javascriptclass PatientSearch {
    constructor(options) {
        this.options = Object.assign({
            containerSelector: 'form',
            inputSelector: '#patient-search',
            resultsSelector: '#patient-search-results',
            patientIdField: 'patient_id',
            searchEndpoint: '/invoice/web_api/patient/search',
            minSearchLength: 1,
            searchDelay: 300,
            onSelect: null,
            onSearch: null,
            onError: null
        }, options);
        // Initialize component...
    }
}
Implementation Pattern
HTML Structure
html<div class="mb-4">
    <label class="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2">
        Patient
    </label>
    <div class="relative">
        <input type="text" id="patient-search" 
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 dark:text-gray-300 dark:bg-gray-700 leading-tight focus:outline-none focus:shadow-outline" 
            placeholder="Search patient..."
            autocomplete="off">
        
        <!-- Hidden fields for form submission -->
        <input type="hidden" id="patient_id" name="patient_id">
        <input type="hidden" id="patient_name" name="patient_name">
    </div>
    <div id="patient-search-results" class="absolute z-10 bg-white dark:bg-gray-700 shadow-md rounded w-full overflow-y-auto hidden" 
         style="max-width: 400px; max-height: 300px !important; border: 1px solid #ddd;">
    </div>
</div>
JavaScript Initialization
javascriptdocument.addEventListener('DOMContentLoaded', function() {
    new PatientSearch({
        containerSelector: '#your-form-id',
        inputSelector: '#patient-search',
        resultsSelector: '#patient-search-results',
        searchEndpoint: '/invoice/web_api/patient/search',
        onSelect: function(patient) {
            // Handle patient selection
            console.log("Patient selected:", patient.name, "ID:", patient.id);
        }
    });
});
Key Considerations

Database Optimization

Maintain indexes on search columns
Use dedicated columns (first_name, last_name) when possible
Implement proper limits (default 20 items)


Frontend Behavior

Debounced search (300ms delay by default)
Shows recent patients on initial focus
Supports keyboard navigation
Handles edge cases in patient selection


Form Submission Safety
javascriptform.addEventListener('submit', function(e) {
    // Ensure patient_name is set if needed
    if (!patientNameInput.value && patientSearchInput.value) {
        patientNameInput.value = patientSearchInput.value;
    }
});

Backward Compatibility

Works with existing JSON-based personal_info fields
Supports both old and new frontend implementations
Maintains consistent response format



2. Centralized Form Submission Framework
The centralized form submission framework provides a standardized approach to handling forms across the application, ensuring consistent validation, error handling, and user experience.
Framework Architecture
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FORM SUBMISSION FRAMEWORK                          │
│                                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────┐  │
│  │ FormController│   │ WTForms Form │   │  FormHandler  │   │   Form    │  │
│  │   (Backend)   │   │  Definition  │   │ (JavaScript)  │   │  Macros   │  │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └─────┬─────┘  │
│          │                   │                   │                 │        │
│          ▼                   ▼                   ▼                 ▼        │
│    Form Processing    Validation Rules    Client Validation    UI Rendering │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
Core Components
Base FormController (form_controller.py)
pythonclass FormController:
    """Base class for form handling controllers"""
    
    def __init__(
        self, 
        form_class, 
        template_path, 
        success_url=None,
        success_message="Form submitted successfully",
        page_title=None,
        additional_context=None
    ):
        self.form_class = form_class
        self.template_path = template_path
        self.success_url = success_url
        self.success_message = success_message
        self.page_title = page_title
        self.additional_context = additional_context or {}
    
    def handle_request(self, *args, **kwargs):
        """Handle GET/POST request"""
        form = self.get_form(*args, **kwargs)
        
        if request.method == 'POST':
            return self.handle_post(form, *args, **kwargs)
        else:
            return self.handle_get(form, *args, **kwargs)
    
    def process_form(self, form, *args, **kwargs):
        """Process the form data after validation (must be overridden)"""
        raise NotImplementedError("Subclasses must implement process_form")
Form Field Macros (field_macros.html)
html{% macro form_field(field, label_class="", input_class="", container_class="mb-4") %}
<div class="{{ container_class }}">
    <label class="{{ label_class if label_class else 'block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2' }}" 
           for="{{ field.id }}">
        {{ field.label.text }}
    </label>
    {{ field(class=input_class if input_class else "shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 dark:text-gray-300 dark:bg-gray-700 leading-tight focus:outline-none focus:shadow-outline") }}
    <div class="text-red-500 text-xs mt-1 hidden" data-error-for="{{ field.id }}"></div>
    {% if field.errors %}
        <div class="text-red-500 text-xs mt-1">{{ field.errors[0] }}</div>
    {% endif %}
</div>
{% endmacro %}

{% macro patient_search_field(form, field_name="patient_id", label_class="", container_class="mb-8") %}
<!-- Patient search specific macro -->
{% endmacro %}
JavaScript FormHandler (form_handler.js)
javascriptclass FormHandler {
    constructor(options) {
        this.options = Object.assign({
            formSelector: 'form',
            patientSearchOptions: null,
            patientIdField: 'patient_id',
            toggles: [],
            calculations: [],
            validations: [],
            onBeforeSubmit: null,
            onValidationFailed: null,
            onSubmitSuccess: null
        }, options);
        
        this.form = document.querySelector(this.options.formSelector);
        this.init();
    }
    
    init() {
        this.initToggles();
        this.initCalculations();
        this.initValidations();
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
    }
}
Implementation Pattern Example
Step 1: Create Form Definition
pythonclass AdvancePaymentForm(FlaskForm):
    """Form for recording advance payments"""
    patient_id = HiddenField('Patient', validators=[DataRequired(), ValidPatient()])
    payment_date = DateField('Payment Date', format='%Y-%m-%d', validators=[DataRequired()])
    cash_amount = DecimalField('Cash Amount', validators=[Optional()], default=0)
    # ... other fields
Step 2: Create Controller
pythonclass AdvancePaymentController(FormController):
    """Controller for handling advance payment forms"""
    
    def __init__(self):
        super().__init__(
            form_class=AdvancePaymentForm,
            template_path='billing/advance_payment.html',
            success_url=self.get_success_url,
            success_message="Advance payment recorded successfully",
            page_title="Record Advance Payment"
        )
    
    def process_form(self, form, *args, **kwargs):
        """Process advance payment form submission"""
        patient_id = uuid.UUID(form.patient_id.data)
        # Process the payment...
        return result
Step 3: Create Route
python@billing_views_bp.route('/advance/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def create_advance_payment_view():
    """View for creating a new advance payment"""
    controller = AdvancePaymentController()
    return controller.handle_request()
Step 4: Create Template
html{% extends 'layouts/dashboard.html' %}
{% from 'components/forms/field_macros.html' import form_field, patient_search_field, submit_button %}

{% block content %}
<form id="advance-payment-form" method="POST">
    {{ form.csrf_token }}
    {{ patient_search_field(form) }}
    {{ form_field(form.payment_date) }}
    <!-- Other fields... -->
    {{ submit_button("Record Advance Payment") }}
</form>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/components/patient_search.js') }}"></script>
<script src="{{ url_for('static', filename='js/components/form_handler.js') }}"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        new FormHandler({
            formSelector: '#advance-payment-form',
            patientSearchOptions: {
                // Patient search configuration
            },
            toggles: [
                // Field toggle configurations
            ],
            calculations: [
                // Calculation configurations
            ],
            validations: [
                // Validation rules
            ]
        });
    });
</script>
{% endblock %}
Key Benefits

Separation of Concerns

FormController handles HTTP requests/responses
Forms handle data validation and structure
JavaScript handles client-side interaction
Templates handle rendering


Reusability

Components can be reused across different forms
Patient search works consistently everywhere
Standard validation patterns


Maintainability

Centralized logic reduces duplication
Clear responsibilities for each component
Easy to update or extend


Consistent User Experience

Standard interaction patterns
Responsive feedback
Graceful error handling



Pattern Integration Guidelines
When implementing new features that require patient selection or form submission:

For Patient Selection:

Use the patient_search_field macro in templates
Initialize PatientSearch JavaScript component
Handle patient selection in the onSelect callback
Ensure hidden fields are populated before submission


For Form Processing:

Extend FormController for the specific form
Create WTForms form class with validation
Use form field macros for consistent rendering
Initialize FormHandler for client-side behavior


Testing Patterns:
pythondef test_patient_search(client):
    """Test patient search functionality"""
    response = client.get('/invoice/web_api/patient/search?q=John')
    assert response.status_code == 200
    data = response.json
    assert len(data) <= 20  # Check limit

def test_form_submission(client):
    """Test form submission pattern"""
    data = {
        'patient_id': str(test_patient_id),
        'payment_date': '2024-01-15',
        'cash_amount': '100.00'
    }
    response = client.post('/advance/create', data=data)
    assert response.status_code == 302  # Redirect on success


Reference Documentation
For more detailed information, refer to these project documents:
Database Management: Project_docs/Database Management Master Document.md
Database Access: Project_docs/Developer Guide-Using database_service.py V5.md
Migration Strategy: Project_docs/Model-Driven Database Migration Strategy.md
Frontend Development: Project_docs/Front end Approach and Design.md
Testing Strategy: Project_docs/Technical Guide - Managing Database Environments in Flask Testing.md
By adhering to these guidelines, you ensure that your contributions to the Skinspire Clinic HMS maintain consistency with the established architecture, enabling smooth integration and long-term maintainability.