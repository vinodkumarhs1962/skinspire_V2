# SkinSpire Database Creation and Testing Documentation

## Table of Contents
1. [Database Architecture Overview](#database-architecture-overview)
2. [Environment Setup](#environment-setup)
3. [Database Creation Process](#database-creation-process)
4. [Test Database Setup](#test-database-setup)
5. [Data Population](#data-population)
6. [Data Verification](#data-verification)
7. [Testing Workflow](#testing-workflow)
8. [Troubleshooting](#troubleshooting)

## Database Architecture Overview

The SkinSpire application uses a PostgreSQL database with the following key features:

### Entity Relationship Structure
- **Hospitals**: Top-level entities (tenants)
- **Branches**: Belong to hospitals
- **Staff**: Employees associated with hospitals/branches
- **Patients**: Individuals receiving services
- **Users**: Authentication entities linked to staff or patients
- **Roles & Permissions**: Access control system

### Schema Design
All database tables include timestamp tracking columns from the `TimestampMixin`:
- `created_at`: When the record was created
- `updated_at`: When the record was last updated 
- `created_by`: User who created the record
- `updated_by`: User who last updated the record

Key models also include the `SoftDeleteMixin`, providing:
- `deleted_at`: When the record was soft-deleted
- `deleted_by`: User who deleted the record

### Audit System
Database triggers automatically maintain timestamp columns:
- `update_timestamp`: Updates the `updated_at` timestamp on record changes
- `track_user_changes`: Sets the `created_by` and `updated_by` fields based on application context

## Environment Setup

### Prerequisites
- PostgreSQL 12+ installed and running
- Python 3.8+ with pip
- Virtual environment for isolation

### Environment Variables
Create or configure `.env` file with database connection strings:

```
# Development database
DEV_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev

# Test database (separate from dev database)
TEST_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test

# Production database
PROD_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod
```

### Virtual Environment Setup
```bash
# Windows
python -m venv skinspire-env
skinspire-env\Scripts\activate

# Linux/Mac
python -m venv skinspire-env
source skinspire-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Database Creation Process

### SQLAlchemy Models
The database schema is defined through SQLAlchemy models located in:
- `app/models/base.py`: Base classes and mixins
- `app/models/config.py`: Configuration-related models
- `app/models/master.py`: Master data models
- `app/models/transaction.py`: Transaction-related models

All models inherit from `TimestampMixin` defined in `base.py`.

### Database Initialization
The database initialization process follows these steps:

1. **Database Connection**: 
   The `DatabaseManager` in `app/db/__init__.py` establishes connection using SQLAlchemy:
   ```python
   db_manager = init_db(settings.DATABASE_URL)
   ```

2. **Table Creation**: 
   Tables are created based on SQLAlchemy model definitions:
   ```python
   db_manager.create_tables()
   ```

3. **Trigger Functions**: 
   SQL triggers are created to automatically update timestamp fields:
   ```python
   # In create_tables()
   sql_file = Path(__file__).parent / 'functions.sql'
   with open(sql_file, 'r') as f:
       sql = f.read()
       with self.engine.connect() as conn:
           conn.execute(text(sql))
           conn.execute(text("SELECT create_audit_triggers('public')"))
   ```

4. **Initial Data Creation**: 
   The `create_database.py` script populates essential data:
   - Default modules and roles
   - System administrator
   - Default hospital and branch

## Test Database Setup

### Reset and Initialize Test Database
Use `reset_database.py` to create a clean test database:

```bash
cd scripts
python reset_database.py
```

This script performs the following operations:
1. Drops all existing tables
2. Creates new tables from SQLAlchemy models
3. Applies database triggers for timestamp tracking
4. Runs `create_database.py` to initialize essential data

### Batch Script for Test Database Setup
For Windows environments, use the `setup_db.bat` script:

```bash
cd scripts
setup_db.bat
```

This batch file:
1. Sets environment variables (FLASK_APP, FLASK_ENV, PYTHONPATH)
2. Activates the virtual environment
3. Runs the reset_database.py script

## Data Population

After setting up the database structure, populate it with test data using `populate_test_data.py`:

```bash
cd scripts
python populate_test_data.py
```

This script creates:
- Test doctors with different specializations
- Support staff (nurses, receptionists, pharmacy staff)
- Test patients with varied demographics
- User accounts for all created entities
- Role assignments based on entity types

Important: `populate_test_data.py` has been configured to explicitly use the test database URL to ensure data is created in the correct database.

## Data Verification

Verify the database structure and populated data using `verify_test_data.py`:

```bash
cd scripts
python verify_test_data.py
```

This script performs comprehensive verification:
1. **Timestamp Column Verification**: Checks that all tables have the required timestamp columns
2. **System Setup Verification**: Validates modules, roles, and permissions
3. **Hospital Data Verification**: Checks hospital and branch information
4. **Staff Verification**: Validates staff records and grouping by specialization
5. **Patient Verification**: Checks patient records and demographics
6. **User Account Verification**: Validates user accounts and role assignments

## Testing Workflow

### Unit and Integration Testing
The application uses pytest for testing. Key testing files:

- `tests/test_db_setup.py`: Validates database connection and basic schema
- `tests/conftest.py`: Contains pytest fixtures for testing

### Complete Testing Workflow

1. **Set Up Test Environment**:
   ```bash
   # Set environment variables
   set FLASK_ENV=testing
   set FLASK_APP=wsgi.py
   ```

2. **Reset and Initialize Test Database**:
   ```bash
   cd scripts
   setup_db.bat
   # or
   python reset_database.py
   ```

3. **Populate Test Data**:
   ```bash
   python populate_test_data.py
   ```

4. **Verify Database Structure and Data**:
   ```bash
   python verify_test_data.py
   ```

5. **Run Tests**:
   ```bash
   cd ..  # Back to project root
   pytest tests/test_db_setup.py -v
   ```

6. **Run All Tests**:
   ```bash
   pytest
   ```

### Test-Specific Database Considerations

- Tests use function-scoped fixtures to ensure isolation
- Each test receives a fresh database session
- Tests include proper cleanup to avoid test data accumulation
- Direct SQL queries are used for cleanup when needed to bypass ORM constraints

## Troubleshooting

### Common Issues and Solutions

1. **Missing Tables**:
   - **Symptom**: `relation "table_name" does not exist`
   - **Solution**: Ensure you're connecting to the correct database and run `reset_database.py`

2. **Environment Mismatch**:
   - **Symptom**: Scripts using wrong database URL
   - **Solution**: Set `FLASK_ENV=testing` before running scripts, or update scripts to explicitly use test database URL

3. **Timestamp Column Issues**:
   - **Symptom**: SQLAlchemy errors about missing columns
   - **Solution**: Run `reset_database.py` to recreate tables with all required columns

4. **Trigger Function Errors**:
   - **Symptom**: Errors related to trigger functions
   - **Solution**: Check that `functions.sql` was properly executed during database setup

5. **Data Population Errors**:
   - **Symptom**: Foreign key constraints during data population
   - **Solution**: Run scripts in correct order (reset → create → populate)

### Advanced Troubleshooting

For deeper database issues, you can:

1. **Examine Database Schema**:
   ```sql
   SELECT table_name, column_name 
   FROM information_schema.columns 
   WHERE table_schema = 'public' 
   ORDER BY table_name, column_name;
   ```

2. **Check Triggers**:
   ```sql
   SELECT trigger_name, event_object_table 
   FROM information_schema.triggers 
   WHERE trigger_schema = 'public';
   ```

3. **Manually Reset Database**:
   ```sql
   DROP SCHEMA public CASCADE;
   CREATE SCHEMA public;
   GRANT ALL ON SCHEMA public TO skinspire_admin;
   ```
