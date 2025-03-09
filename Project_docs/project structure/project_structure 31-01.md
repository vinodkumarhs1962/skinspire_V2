Programs/
├── path_config.json
├── requirements.txt
├── setup_logs.json
├── Skinspire Repository/
│   ├── .gitconfig
│   ├── .gitignore
│   ├── .lesshst
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── skinspire_v2/
│   │   ├── .env
│   │   ├── .flaskenv
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── routes/
│   │   │   │   │   ├── admin.py
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── patient.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── __init__.py
│   │   │   ├── config/
│   │   │   │   ├── settings.py
│   │   │   │   ├── __init__.py
│   │   │   ├── db/
│   │   │   │   ├── context.py
│   │   │   │   ├── functions.sql
│   │   │   │   ├── manager.py
│   │   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── base.py
│   │   │   │   ├── config.py
│   │   │   │   ├── master.py
│   │   │   │   ├── transaction.py
│   │   │   │   ├── __init__.py
│   │   │   ├── security/
│   │   │   │   ├── audit/
│   │   │   │   │   ├── audit_logger.py
│   │   │   │   │   ├── error_tracker.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── authentication/
│   │   │   │   │   ├── auth_manager.py
│   │   │   │   │   ├── password_policy.py
│   │   │   │   │   ├── session_manager.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── authorization/
│   │   │   │   │   ├── permission_validator.py
│   │   │   │   │   ├── rbac_manager.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── bridge.py
│   │   │   │   ├── config.py
│   │   │   │   ├── db/
│   │   │   │   │   ├── functions.sql
│   │   │   │   │   ├── migrations/
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── encryption/
│   │   │   │   │   ├── field_encryption.py
│   │   │   │   │   ├── hospital_encryption.py
│   │   │   │   │   ├── model_encryption.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py
│   │   │   │   ├── routes/
│   │   │   │   │   ├── audit.py
│   │   │   │   │   ├── rbac.py
│   │   │   │   │   ├── security_management.py
│   │   │   │   │   ├── __init__.py
│   │   │   │   ├── __init__.py
│   │   │   ├── __init__.py
│   │   ├── migrations/
│   │   │   ├── alembic.ini
│   │   │   ├── env.py
│   │   │   ├── README
│   │   │   ├── script.py.mako
│   │   │   ├── versions/
│   │   ├── path_config.json
│   │   ├── Project_docs/
│   │   │   ├── encryption/
│   │   │   │   ├── 01_concept.md
│   │   │   │   ├── 02_implementation.md
│   │   │   │   ├── 03_models.md
│   │   │   │   ├── 04_testing.md
│   │   │   │   ├── 05_key_rotation.md
│   │   │   │   ├── 06_lessons.md
│   │   │   │   ├── index.md
│   │   │   │   ├── README.md
│   │   │   ├── index.md
│   │   │   ├── README.md
│   │   ├── pyproject.toml
│   │   ├── pytest.ini
│   │   ├── requirements.txt
│   │   ├── run.py
│   │   ├── scripts/
│   │   │   ├── create_database.py
│   │   │   ├── install.py
│   │   │   ├── manage_db.py
│   │   │   ├── populate_test_data.py
│   │   │   ├── setup_test_db.py
│   │   │   ├── setup_venv.py
│   │   │   ├── verify_test_data.py
│   │   ├── setup.py.bak
│   │   ├── skinspire_v2.egg-info/
│   │   │   ├── dependency_links.txt
│   │   │   ├── PKG-INFO
│   │   │   ├── requires.txt
│   │   │   ├── SOURCES.txt
│   │   │   ├── top_level.txt
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── test_security/
│   │   │   │   ├── test_authentication.py
│   │   │   │   ├── test_encryption.py
│   │   │   │   ├── test_security_endpoints.py
│   │   │   │   ├── test_setup_verification.py
│   │   │   │   ├── __init__.py
│   │   │   ├── __init__.py
│   │   ├── wsgi.py
│   ├── tailwind.config.js
│   ├── vs code workspace/
│   │   ├── Skinspire Repository.code-workspace



path_config.json:

{
    "VENV_PATH": "C:\\Users\\vinod\\AppData\\Local\\Programs\\skinspire-env",
    "SCRIPTS_PATH": "C:\\Users\\vinod\\AppData\\Local\\Programs\\skinspire-env\\Scripts",
    "PYTHON_PATH": "C:\\Users\\vinod\\AppData\\Local\\Programs\\skinspire-env\\Scripts\\python.exe",
    "PIP_PATH": "C:\\Users\\vinod\\AppData\\Local\\Programs\\skinspire-env\\Scripts\\pip.exe",
    "PROJECT_ROOT": "C:\\Users\\vinod\\AppData\\Local\\Programs"
}


requirements.txt:

# requirements.txt
Flask==3.1.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Migrate==4.0.5
# psycopg2==2.9.10
cryptography==42.0.2
PyJWT==2.8.0
python-dotenv==1.0.1
Werkzeug==3.1.3
polars==0.19.19
reportlab==4.0.8
SQLAlchemy==2.0.36
pytest==8.3.4
pytest-mock==3.14.0
schedule==1.2.2
setuptools==75.8.0
# Removed functools as it's built into Python
# Removed pathlib as it's built into Python

            



setup_logs.json:

[
  {
    "message": "Starting setup process...",
    "is_error": false
  },
  {
    "message": "Using existing virtual environment at: C:\\Users\\vinod\\AppData\\Local\\Programs\\skinspire-env",
    "is_error": false
  },
  {
    "message": "Found Visual C++ Build Tools at: C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.42.34433\\bin\\Hostx64\\x64\\cl.exe",
    "is_error": false
  },
  {
    "message": "Found PostgreSQL 17 at: C:\\Program Files\\PostgreSQL\\17",
    "is_error": false
  },
  {
    "message": "PostgreSQL config verification: PostgreSQL 17.2",
    "is_error": false
  },
  {
    "message": "\nInstalling/Updating required packages...",
    "is_error": false
  },
  {
    "message": "Installing Flask version 3.1.0",
    "is_error": false
  },
  {
    "message": "Installing Flask-SQLAlchemy version 3.1.1",
    "is_error": false
  },
  {
    "message": "Installing Flask-Login version 0.6.3",
    "is_error": false
  },
  {
    "message": "Installing Flask-Migrate version 4.0.5",
    "is_error": false
  },
  {
    "message": "Installing cryptography version 42.0.2",
    "is_error": false
  },
  {
    "message": "Installing PyJWT version 2.8.0",
    "is_error": false
  },
  {
    "message": "Installing python-dotenv version 1.0.1",
    "is_error": false
  },
  {
    "message": "Installing Werkzeug version 3.1.3",
    "is_error": false
  },
  {
    "message": "Installing polars version 0.19.19",
    "is_error": false
  },
  {
    "message": "Installing reportlab version 4.0.8",
    "is_error": false
  },
  {
    "message": "Installing SQLAlchemy version 2.0.36",
    "is_error": false
  },
  {
    "message": "Installing pytest version 8.3.4",
    "is_error": false
  },
  {
    "message": "Installing pytest-mock version 3.14.0",
    "is_error": false
  },
  {
    "message": "Installing schedule version 1.2.2",
    "is_error": false
  },
  {
    "message": "Installing setuptools version 75.8.0",
    "is_error": false
  },
  {
    "message": "Path variables have been set and saved to C:\\Users\\vinod\\AppData\\Local\\Programs\\path_config.json",
    "is_error": false
  },
  {
    "message": "\nSetting up Tailwind CSS...",
    "is_error": false
  },
  {
    "message": "\nSetting up Tailwind CSS...",
    "is_error": false
  },
  {
    "message": "Node.js version: v22.13.1",
    "is_error": false
  },
  {
    "message": "Node.js or npm not found. Please install Node.js from https://nodejs.org/",
    "is_error": true
  },
  {
    "message": "Tailwind CSS setup failed. Please check the logs.",
    "is_error": true
  }
]

