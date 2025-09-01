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
Entity Lifecycle Management
When entities need to exist outside their session:
python# Create detached copy that won't try to lazy-load
from app.services.database_service import get_detached_copy
detached_entity = get_detached_copy(entity)

# Or convert to dictionary
from app.services.database_service import get_entity_dict
entity_dict = get_entity_dict(entity)
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


Reference Documentation
For more detailed information, refer to these project documents:

Database Management: Project_docs/Database Management Master Document.md
Database Access: Project_docs/Developer Guide-Using database_service.py V5.md
Migration Strategy: Project_docs/Model-Driven Database Migration Strategy.md
Frontend Development: Project_docs/Front end Approach and Design.md
Testing Strategy: Project_docs/Technical Guide - Managing Database Environments in Flask Testing.md

By adhering to these guidelines, you ensure that your contributions to the Skinspire Clinic HMS maintain consistency with the established architecture, enabling smooth integration and long-term maintainability.