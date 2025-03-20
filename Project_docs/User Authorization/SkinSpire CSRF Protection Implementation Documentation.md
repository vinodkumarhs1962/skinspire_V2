SkinSpire CSRF Protection Implementation Documentation
Project-Specific CSRF Implementation Analysis
Core Configuration Location
The CSRF protection in the SkinSpire Hospital Management System is primarily configured in app/__init__.py, leveraging Flask-WTF's CSRFProtect extension.
Initialization Code
pythonCopyfrom flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app():
    # ... other configurations
    csrf.init_app(app)
    
    # Selectively exempt API endpoints
    csrf.exempt(r"/api/*")
Key Implementation Characteristics
Protection Scope

Applies CSRF protection to all non-API routes
Provides an exemption mechanism for API endpoints
Integrated with the application's core initialization process

Form Protection Mechanism
In app/forms/auth_forms.py, forms inherit from FlaskForm, which automatically enables CSRF protection:
pythonCopyfrom flask_wtf import FlaskForm
from wtforms import StringField, PasswordField

class LoginForm(FlaskForm):
    username = StringField('Phone Number')
    password = PasswordField('Password')
Template Integration
Templates leverage the form.hidden_tag() method to render CSRF tokens:
htmlCopy<form method="POST">
    {{ form.hidden_tag() }}  <!-- Renders CSRF token automatically -->
    <!-- Other form fields -->
</form>
Test Environment Configuration
In tests/conftest.py, CSRF handling is currently configured with:
pythonCopyapp.config.update({
    'TESTING': True,
    'SECRET_KEY': 'test_secret_key',
    'WTF_CSRF_ENABLED': False  # Currently disabled in tests
})
Current Test Token Extraction Method
pythonCopydef get_csrf_token(response):
    """Extract CSRF token from response data"""
    match = re.search(r'name="csrf_token" value="(.+?)"', response.data.decode())
    return match.group(1) if match else None
Observations and Potential Improvement Areas

Test environment currently disables CSRF protection
Token extraction relies on a specific HTML pattern
No explicit handling of token generation during testing