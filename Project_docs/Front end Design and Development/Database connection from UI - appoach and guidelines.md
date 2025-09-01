# Database Connection & Access Patterns in Skinspire Clinic System

## Overview

The Skinspire Clinic System uses a dual-approach database access pattern that serves both testing needs and UI operations. Understanding when to use each approach is crucial for maintaining application consistency, security, and testability.

## Core Database Access Patterns

Our application employs two primary patterns for database access:

### 1. Direct Database Access (get_db pattern)

This pattern uses a database manager that provides session management for direct database interactions.

```python
from app.database import get_db

db_manager = get_db()
with db_manager.get_session() as session:
    # Database operations
    users = session.query(User).filter_by(is_active=True).all()
    # More operations...
```

**Key characteristics:**
- Provides transaction management with automatic commits and rollbacks
- Uses the correct database URL based on environment (dev/test/prod)
- Matches the database access pattern used in integration tests
- Maintains connection pooling and resource management
- Used primarily for direct database interactions where API calls aren't necessary

### 2. API-based Access (HTTP pattern)

This pattern makes HTTP requests to internal API endpoints.

```python
import requests

response = requests.post(
    url_for('auth.login', _external=True),
    json={'username': username, 'password': password},
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 200:
    # Handle successful response
```

**Key characteristics:**
- Uses HTTP requests to communicate with API endpoints
- Maintains separation of concerns between UI and business logic
- Provides a clear interface contract through API endpoints
- Requires handling of HTTP-specific concerns like status codes and CSRF
- Used primarily for operations that need to go through the API layer for validation or processing

## When to Use Each Pattern

### Use Direct Database Access (get_db) When:

1. Creating core records that don't require complex validation or business logic
2. Performing operations that match exactly what tests do
3. Working with UI components that need quick database lookups
4. Building administrative tools that directly manage database records
5. Implementing operations where the API isn't needed for additional validation

### Use API-based Access (HTTP) When:

1. The operation involves complex business logic best kept in the API layer
2. Multiple related database operations need to happen together as a unit
3. The operation requires special validation available in the API endpoint
4. The functionality needs to be accessible from external systems later
5. The operation already has a well-defined API endpoint

## Implementation Guidelines for New UI Components

When adding a new UI component that requires database access, follow these guidelines:

### 1. Initial Analysis

First, determine if your operation primarily needs:
- Simple database access (create, read, update, delete operations)
- Complex business logic or validation
- Integration with other systems

### 2. Implementation Decision

Based on your analysis:

**For simple database operations:**
- Use the direct database access pattern (get_db)
- Follow the example from the registration function implementation
- Keep transaction scope as narrow as possible
- Include appropriate error handling

**For operations requiring business logic:**
- Consider moving the logic to a service layer function
- Allow the service function to be called from both UI and API
- Keep the business logic independent of HTTP concerns
- Use the API access pattern where existing endpoints handle your needs

### 3. Code Structure

**For direct database access:**
```python
@blueprint.route('/endpoint', methods=['GET', 'POST'])
def endpoint_function():
    form = FormClass()
    
    if form.validate_on_submit():
        try:
            from app.database import get_db
            
            db_manager = get_db()
            with db_manager.get_session() as session:
                # Database operations
                session.commit()
                
            flash('Operation successful', 'success')
            return redirect(url_for('some.endpoint'))
        except Exception as e:
            flash(f'Operation failed: {str(e)}', 'error')
            current_app.logger.error(f"Error: {str(e)}", exc_info=True)
    
    return render_template('template.html', form=form)
```

**For API-based access:**
```python
@blueprint.route('/endpoint', methods=['GET', 'POST'])
def endpoint_function():
    form = FormClass()
    
    if form.validate_on_submit():
        try:
            data = {
                'field1': form.field1.data,
                'field2': form.field2.data
            }
            
            response = requests.post(
                url_for('api.endpoint', _external=True),
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                flash('Operation successful', 'success')
                return redirect(url_for('some.endpoint'))
            else:
                error_msg = response.json().get('error', 'Operation failed')
                flash(error_msg, 'error')
        except Exception as e:
            flash(f'Connection error: {str(e)}', 'error')
    
    return render_template('template.html', form=form)
```

## Database Table Creation and Migration

When adding new database tables or modifying existing ones:

### 1. Model Definition

Define your SQLAlchemy models in the appropriate module:
- Base tables in `app/models/base.py`
- Master data tables in `app/models/master.py`
- Transaction tables in `app/models/transaction.py`

Follow the existing patterns using Base, TimestampMixin, etc.

```python
class NewEntity(Base, TimestampMixin, SoftDeleteMixin):
    """Description of the new entity"""
    __tablename__ = 'new_entities'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    # Other fields...
    
    # Relationships
    parent = relationship("ParentEntity", back_populates="children")
```

### 2. Migration Generation

After defining your models, generate migrations:

```bash
flask db migrate -m "Add new entity table"
```

Review the generated migration file in the `migrations/versions/` directory to ensure it correctly represents your changes.

### 3. Migration Application

Apply the migration to your development database:

```bash
flask db upgrade
```

### 4. Testing Setup

Ensure your test database also receives these changes:

```bash
FLASK_ENV=test flask db upgrade
```

Or use your test setup scripts to recreate test databases with the new schema.

## Special Considerations for Testing

Your test environment should follow these guidelines:

1. **Test Database**: Always use a separate test database with proper isolation
2. **Test Data**: Populate test data using the same database access patterns used in application code
3. **Integration Tests**: Use the direct database access pattern for setup and verification
4. **API Tests**: Test API endpoints with HTTP requests similar to those from the UI
5. **Fixtures**: Use fixtures to set up common test data and database states

## Best Practices

1. **Session Management**: Always use the `with` statement with database sessions to ensure proper cleanup
2. **Error Handling**: Catch and log database exceptions with appropriate user feedback
3. **Transactions**: Keep transactions as short as possible to reduce lock contention
4. **Validation**: Perform input validation at both the form and database level
5. **Logging**: Log database errors with sufficient context for debugging
6. **Security**: Never trust user input directly in database queries
7. **Consistency**: Follow the established patterns for database access throughout the application

## Example Implementation: New Table and UI

Let's walk through adding a new feature with both database and UI components:

### 1. Define the Model

```python
# app/models/transaction.py
class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    """Patient appointments"""
    __tablename__ = 'appointments'
    
    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, completed, canceled
    notes = Column(Text)
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    staff = relationship("Staff", back_populates="appointments")
```

### 2. Create the Form

```python
# app/forms/appointment_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, SelectField
from wtforms.validators import DataRequired

class AppointmentForm(FlaskForm):
    """Form for creating and editing appointments"""
    patient_id = SelectField('Patient', validators=[DataRequired()])
    staff_id = SelectField('Doctor/Staff', validators=[DataRequired()])
    appointment_date = DateTimeField('Appointment Date/Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    notes = TextAreaField('Notes')
```

### 3. Implement the UI View

```python
# app/views/appointment_views.py
@appointment_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_appointment():
    """Create a new appointment"""
    form = AppointmentForm()
    
    # Populate dropdown options
    from app.database import get_db
    
    db_manager = get_db()
    with db_manager.get_session() as session:
        patients = session.query(Patient).filter_by(is_active=True).all()
        staff = session.query(Staff).filter_by(is_active=True).all()
        
        form.patient_id.choices = [(str(p.patient_id), p.full_name) for p in patients]
        form.staff_id.choices = [(str(s.staff_id), s.full_name) for s in staff]
    
    if form.validate_on_submit():
        try:
            # Using direct database access pattern
            appointment = Appointment(
                patient_id=form.patient_id.data,
                staff_id=form.staff_id.data,
                appointment_date=form.appointment_date.data,
                status='scheduled',
                notes=form.notes.data
            )
            
            db_manager = get_db()
            with db_manager.get_session() as session:
                session.add(appointment)
                session.commit()
            
            flash('Appointment created successfully', 'success')
            return redirect(url_for('appointment.list_appointments'))
        except Exception as e:
            flash(f'Error creating appointment: {str(e)}', 'error')
            current_app.logger.error(f"Appointment creation error: {str(e)}", exc_info=True)
    
    return render_template('appointments/create.html', form=form)
```

## Conclusion

By following these guidelines consistently, the Skinspire Clinic system will maintain clean database access patterns that work well for both UI components and testing. The dual approach allows flexibility while ensuring code remains testable and maintainable.

Remember the key principles:
- Use direct database access for simple operations and testing compatibility
- Use API access for complex business logic and well-defined interfaces
- Keep your database transactions short and well-managed
- Follow consistent patterns throughout the application
- Properly handle errors and provide appropriate feedback

With these guidelines in place, new developers can quickly understand how to interact with the database, and the application will grow with a consistent, maintainable architecture.