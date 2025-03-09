skinspire_v2/
├── .env                    # Environment configuration
├── .flaskenv               # Flask-specific environment settings
├── pyproject.toml          # Project configuration
├── pytest.ini              # Pytest configuration
├── requirements.txt        # Project dependencies
├── wsgi.py                 # WSGI entry point for deployment
├── run.py                  # Development server run script

├── app/                    # Main application package
│   ├── __init__.py         # Application factory
│   ├── api/                # API route blueprints
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── admin.py
│   │       ├── patient.py
│   │       └── auth.py
│   
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   
│   ├── database/           # Database management
│   │   ├── __init__.py
│   │   ├── context.py
│   │   ├── functions.sql
│   │   └── manager.py
│   
│   ├── models/             # Database models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── config.py
│   │   ├── master.py
│   │   └── transaction.py
│   
│   ├── security/           # Security-related components
│   │   ├── __init__.py
│   │   ├── authentication/
│   │   │   ├── __init__.py
│   │   │   ├── auth_manager.py
│   │   │   └── session_manager.py
│   │   ├── authorization/
│   │   │   ├── __init__.py
│   │   │   └── rbac_manager.py
│   │   ├── encryption/
│   │   │   ├── __init__.py
│   │   │   ├── field_encryption.py
│   │   │   └── model_encryption.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── security_management.py
│   
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html       # Base template
│   │   ├── components/     # Reusable template components
│   │   │   ├── sidebar.html
│   │   │   ├── topbar.html
│   │   │   └── modals/
│   │   ├── auth/           # Authentication templates
│   │   │   ├── login.html
│   │   │   └── password_reset.html
│   │   └── modules/        # Role-specific module templates
│   │       ├── dashboard/
│   │       │   ├── admin.html
│   │       │   ├── doctor.html
│   │       │   └── patient.html
│   │       ├── patient/
│   │       │   ├── profile.html
│   │       │   └── medical_history.html
│   │       └── staff/
│   │           └── profile.html
│   
│   ├── static/             # Static assets
│   │   ├── css/            # Stylesheets
│   │   │   ├── tailwind.css
│   │   │   └── custom.css
│   │   ├── js/             # JavaScript files
│   │   │   ├── core/
│   │   │   │   ├── navigation.js
│   │   │   │   └── role_access.js
│   │   │   └── modules/
│   │   │       ├── patient.js
│   │   │       ├── staff.js
│   │   │       └── appointment.js
│   │   └── images/
│   │       ├── icons/
│   │       └── logos/
│   
│   └── utils/              # Utility modules
│       ├── __init__.py
│       ├── menu_generator.py
│       └── validators.py
│   
├── migrations/             # Database migration scripts
│   ├── versions/
│   ├── alembic.ini
│   └── env.py
│   
├── scripts/                # Utility and management scripts
│   ├── create_database.py
│   ├── manage_db.py
│   ├── populate_test_data.py
│   └── setup_test_db.py
│   
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_db_setup.py
│   └── test_security/
│       ├── test_authentication.py
│       └── test_encryption.py
│   
└── Project_docs/           # Project documentation
    ├── encryption/
    └── security/