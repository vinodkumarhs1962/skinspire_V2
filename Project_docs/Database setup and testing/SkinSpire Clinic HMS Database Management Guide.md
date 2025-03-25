# SkinSpire Clinic HMS Database Management Guide

## Introduction

The SkinSpire Clinic Hospital Management System relies on a robust database architecture that's essential for proper system operation. This document provides a comprehensive guide to managing the database across development, testing, and production environments using our centralized database access approach.

The database management system follows these key principles:

1. **Centralized Database Access**: All database operations use the `database_service.py` module to ensure consistent connection management.
2. **Environment-Aware Configuration**: The system automatically adapts to the current environment (development, testing, or production).
3. **Consistent Transaction Management**: Database transactions follow standardized patterns for reliability.
4. **Version-Controlled Schema**: Database structure evolves with application models.
5. **Incremental Updates**: Changes can be applied incrementally without disrupting existing data.

## Core Database Architecture

### The Database Service Approach

Our system uses a unified database service layer (`database_service.py`) that provides several benefits:

- Consistent connection management across all application components
- Automatic environment detection and configuration
- Standardized transaction boundaries and error handling
- Session lifecycle management for preventing leaked connections
- Utility functions for detached entity handling

This approach ensures that:

1. All code follows the same database access patterns
2. Environment-specific configuration happens automatically
3. Connection resources are properly managed
4. Transactions are handled consistently

### Database Service API Overview

The key functions in our database service are:

- `get_db_session()`: Main function for database access, returns a session context manager
- `get_db_engine()`: Get the SQLAlchemy engine instance directly
- `get_active_env()`: Identify the current environment (dev/test/prod)
- `get_database_url()`: Get the database URL for the current environment
- `get_detached_copy()`: Safe way to use entities outside a session
- `use_nested_transactions()`: Control transaction nesting behavior

These functions provide a complete interface to the database system, handling all connection and session management concerns.

## Key Management Scripts

The system includes several scripts for database management:

| Script | Purpose | Primary Use |
|--------|---------|------------|
| `create_database.py` | Creates tables and populates initial data | Setting up a new database |
| `reset_database.py` | Drops and recreates all tables | Completely resetting database |
| `install_triggers.py` | Installs PostgreSQL triggers | Adding database-level functionality |
| `populate_test_data.py` | Creates sample data for testing | Setting up test environments |
| `verify_db_service.py` | Checks database connectivity | Validating configuration |
| `db_inspector.py` | Shows database structure | Diagnostics and troubleshooting |
| `copy_test_to_dev.py` | Copies database between environments | Propagating changes across environments |
| `manage_db.py` | CLI for database management tasks | Comprehensive management tool |
| `switch_env.py` | Changes current environment | Selecting target environment |

Each script works with the centralized database service to ensure consistent database access patterns.

## Cookbook: Step-by-Step Procedures

### 1. Creating a Database from Scratch

To create a completely new database with tables, triggers, and initial data:

```bash
# Step 1: Set the target environment
python scripts/switch_env.py dev  # Options: dev, test, prod

# Step 2: Reset the database (drop and recreate tables)
python scripts/reset_database.py --env dev

# Step 3: Create initial database structure and core data
python scripts/create_database.py --env dev

# Step 4: Install database triggers
python scripts/install_triggers.py dev --verify

# Step 5: Verify database setup
python scripts/verify_db_service.py --env dev
```

For Windows users, a simplified approach using the batch file:

```bash
# Create database in one step
scripts\setup_db.bat dev  # Options: dev, test, prod
```

The `setup_db.bat` script automatically runs steps 1-4 above.

### 2. Creating a Database as a Copy of Another

To create a new development database as a copy of your test database:

```bash
# Method 1: Direct copy (fastest)
# This will copy the entire database structure and data
python scripts/copy_test_to_dev.py

# Method 2: Manually recreate with same structure
python scripts/reset_database.py --env dev
python scripts/create_database.py --env dev
python scripts/install_triggers.py dev
```

The `copy_test_to_dev.py` script uses PostgreSQL's `pg_dump` and `psql` utilities to create an exact copy of the test database. This approach ensures all tables, data, constraints, and triggers are preserved.

**Example:** Copy the test database to development with verification:

```bash
python scripts/copy_test_to_dev.py
python scripts/verify_db_service.py --env dev
```

### 3. Populating Standard Test Data

To populate a database with standardized test data:

```bash
# Add test data to the development database
python scripts/populate_test_data.py --env dev

# Or add test data to the test database
python scripts/populate_test_data.py --env test
```

The `populate_test_data.py` script creates:
- A set of test doctors with different specialties
- Support staff members (nurses, receptionists, pharmacy staff)
- Test patients with diverse demographics
- User accounts for all created entities
- Role assignments based on entity types

**Example:** Create 20 test patients and 5 doctors in the development database:

```bash
python scripts/populate_test_data.py --env dev
```

### 4. Adding Database Triggers

Triggers provide database-level functionality for operations like:
- Automatic timestamps on record creation/update
- Password hashing
- User tracking
- Session management

To install or update triggers:

```bash
# Install triggers in development database
python scripts/install_triggers.py dev

# Install and verify triggers
python scripts/install_triggers.py dev --verify

# Verify triggers separately
python scripts/verify_triggers.py verify-functions
python scripts/verify_triggers.py verify-critical-triggers
```

**Example:** Install triggers and verify their functionality:

```bash
python scripts/install_triggers.py dev --verify
```

### 5. Incrementally Updating Tables

When you modify your SQLAlchemy models, you can update the database schema to match:

```bash
# Option 1: Using create_database with incremental option
python scripts/create_database.py --env dev --update-only

# Option 2: Using Flask-Migrate (if configured)
flask db migrate -m "Description of changes"
flask db upgrade
```

The `create_database.py` script checks for existing tables and only creates missing ones when used with `--update-only`. This allows for incremental schema updates without disrupting existing data.

**Example:** Add a new model class and update the database:

1. Add a new model in `app/models/transaction.py`:
   ```python
   class Appointment(Base, TimestampMixin, TenantMixin):
       """Patient appointment information"""
       __tablename__ = 'appointments'
       
       appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
       patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
       # Add other columns...
   ```

2. Update the database schema:
   ```bash
   python scripts/create_database.py --env dev --update-only
   ```

### 6. Verifying Database Setup

To verify database connectivity and structure:

```bash
# Basic connectivity verification
python scripts/verify_db_service.py --env dev

# Detailed database inspection
python scripts/db_inspector.py dev

# Check database tables and triggers
python scripts/manage_db.py verify-triggers
```

These verification tools help ensure that:
- Database connection is working properly
- Required tables exist
- Triggers are properly installed
- The right environment is being used

**Example:** Comprehensive database verification:

```bash
# Check connection, tables, and run a test transaction
python scripts/verify_db_service.py --env dev -v

# Inspect the database structure
python scripts/db_inspector.py dev

# Verify critical triggers
python scripts/verify_triggers.py verify-critical-triggers
```

## Common Scenarios and Their Solutions

### Scenario 1: Setting Up a New Developer Environment

A new developer needs to set up their local development database:

```bash
# Clone the repository
git clone [repository-url]
cd skinspire_v2

# Install dependencies
pip install -r requirements.txt

# Set up the database
scripts\setup_db.bat dev

# Add test data
python scripts/populate_test_data.py --env dev

# Verify setup
python scripts/verify_db_service.py --env dev
```

### Scenario 2: Resetting a Corrupted Database

If a database becomes corrupted during development:

```bash
# Reset the database completely
python scripts/reset_database.py --env dev

# Recreate structure and initial data
python scripts/create_database.py --env dev

# Reinstall triggers
python scripts/install_triggers.py dev

# Add test data if needed
python scripts/populate_test_data.py --env dev
```

### Scenario 3: Updating the Database After Model Changes

After modifying SQLAlchemy models:

```bash
# Update database schema to match models
python scripts/create_database.py --env dev --update-only

# Verify new tables/columns
python scripts/db_inspector.py dev
```

### Scenario 4: Preparing for Testing After Development

To create a test database that matches the development environment:

```bash
# Copy the development database to test
python scripts/copy_test_to_dev.py dev test

# Or set up a fresh test database
scripts\setup_db.bat test
python scripts/populate_test_data.py --env test
```

### Scenario 5: Diagnosing Database Connection Issues

If database connections are failing:

```bash
# Verify database connection
python scripts/verify_db_service.py --env dev -v

# Check environment configuration
python scripts/switch_env.py status

# Inspect database URL
python -c "from app.services.database_service import get_database_url; print(get_database_url())"
```

## Best Practices and Guidelines

### Do's

1. **DO** use the database service for all database access:
   ```python
   from app.services.database_service import get_db_session
   
   with get_db_session() as session:
       # Database operations
       user = session.query(User).filter_by(id=123).first()
   ```

2. **DO** check for existing records before creating them:
   ```python
   existing_user = session.query(User).filter_by(user_id=username).first()
   if not existing_user:
       # Create new user
       user = User(user_id=username, ...)
       session.add(user)
   ```

3. **DO** use `session.flush()` instead of `session.commit()` within transaction blocks:
   ```python
   with get_db_session() as session:
       user = User(...)
       session.add(user)
       session.flush()  # Makes changes visible within transaction
       # The commit happens automatically when leaving the context
   ```

4. **DO** specify the environment explicitly:
   ```bash
   python scripts/create_database.py --env dev
   ```

5. **DO** verify database setup after major changes:
   ```bash
   python scripts/verify_db_service.py --env dev
   ```

### Don'ts

1. **DON'T** create database sessions directly:
   ```python
   # WRONG
   from sqlalchemy.orm import sessionmaker
   Session = sessionmaker(bind=engine)
   session = Session()
   ```

2. **DON'T** commit or rollback explicitly in most cases:
   ```python
   # WRONG
   session.commit()  # Let the context manager handle this
   ```

3. **DON'T** access detached entities outside their session:
   ```python
   # WRONG
   with get_db_session() as session:
       user = session.query(User).get(1)
   
   # Error: user is now detached
   print(user.roles)  # Will likely fail
   ```

4. **DON'T** mix database access methods:
   ```python
   # WRONG: Using both Flask-SQLAlchemy and direct database access
   user = User.query.get(1)  # Flask-SQLAlchemy style
   
   with get_db_session() as session:  # database_service style
       session.add(user)  # Mixing styles can cause errors
   ```

5. **DON'T** forget to handle detached entities:
   ```python
   # CORRECT: Use get_detached_copy for entities used outside session
   from app.services.database_service import get_db_session, get_detached_copy
   
   with get_db_session() as session:
       user = session.query(User).get(1)
       detached_user = get_detached_copy(user)
   
   # Safe to use outside session
   print(detached_user.user_id)
   ```

## Understanding the Database Structure

The SkinSpire database follows a multi-tenant architecture with these key entity types:

1. **Hospital**: Top-level tenant entity representing a healthcare facility
2. **Branch**: Facility within a hospital
3. **Staff**: Healthcare providers and administrative personnel
4. **Patient**: Individuals receiving care
5. **User**: Authentication accounts for staff and patients
6. **Role**: Permission groups for authorization

Relations are managed through foreign keys with proper constraints to ensure data integrity.

## Maintaining Database Backup Hygiene

Regular backups should be performed to prevent data loss:

```bash
# Back up development database
pg_dump -U skinspire_admin -d skinspire_dev > backup_dev_$(date +%Y%m%d).sql

# Back up test database
pg_dump -U skinspire_admin -d skinspire_test > backup_test_$(date +%Y%m%d).sql

# Restore from backup
psql -U skinspire_admin -d skinspire_dev < backup_dev_20250320.sql
```

It's advisable to back up databases before major schema changes or migrations.

## Conclusion

This guide provides a comprehensive overview of database management for the SkinSpire Clinic HMS. By following these procedures and best practices, you can ensure reliable database operations across development, testing, and production environments.

The centralized database access approach via `database_service.py` is the foundation of our database architecture, providing consistent and reliable database operations throughout the application.

Remember that all database access should go through the database service layer to maintain consistency and reliability. This approach ensures proper connection management, transaction boundaries, and error handling throughout the application.

# Analyzing Trade-offs in the Database Management Approach

The revised approach of enhancing existing scripts instead of creating standalone modules offers excellent backward compatibility, but it does come with some trade-offs. Let me walk you through the areas that might not be fully covered and where you might encounter challenges.

## Areas Not Fully Covered in the Revised Approach

### 1. Clean Separation of Concerns

In the standalone module approach, I had proposed a cleaner separation between different database management functions. The revised approach maintains the existing structure where some scripts handle multiple responsibilities. For example, `create_database.py` handles both schema creation and data population, which could ideally be separated for better modularity.

This means the single-responsibility principle isn't as strictly enforced. Scripts tend to have broader functionality rather than being focused on specific tasks. While this maintains compatibility, it can make the codebase slightly harder to maintain as it grows.

### 2. Comprehensive Configuration Management

The standalone approach would have introduced more robust configuration management with dedicated settings for different environments. The revised approach relies more on environment variables and command-line parameters, which works but might be less centralized and consistent across all tools.

A more sophisticated configuration system might include:
- Environment-specific validation rules
- Preset configurations for different deployment scenarios
- Configuration inheritance and overrides

### 3. Formalized Error Recovery

The standalone approach could have implemented more sophisticated error recovery mechanisms with standardized ways to roll back failed operations. The current approach handles errors, but recovery strategies are more script-specific rather than following a unified pattern.

This means that error handling might be inconsistent across different scripts, and some edge cases might not be handled as robustly as they could be with a more standardized approach.

### 4. Comprehensive Migration Framework

While the revised approach supports incremental updates to some degree, it doesn't offer a full-featured migration framework with versioning, dependencies, and rollback capabilities like you'd find in frameworks like Alembic (used by Flask-Migrate).

This creates a limitation when you need to:
- Apply complex schema changes that require data transformation
- Track which migrations have been applied
- Roll back problematic migrations

### 5. Advanced Testing Integration

The standalone approach could have built testing capabilities more directly into the database tools. The current approach keeps database management and testing more separate, which works but doesn't provide as tight integration between them.

A more integrated approach might include:
- Database fixtures directly generated by database tools
- Test data management integrated with the database scripts
- Automated validation of database state for tests

## Potential Problem Areas Due to Backward Compatibility

### 1. Parameter Handling Complexity

As we add new parameters to existing scripts while maintaining backward compatibility, the parameter handling logic becomes increasingly complex. This can lead to:

- Confusing default behaviors
- Parameter interactions that are hard to predict
- Difficulty in adding new features without breaking existing usage patterns

For example, maintaining compatibility with both `--env dev` and positional parameters can lead to ambiguous cases where it's not clear which takes precedence.

### 2. Inconsistent API Patterns

Different scripts developed at different times might follow different patterns for similar operations. As we enhance them, maintaining backward compatibility means we can't fully standardize these patterns, leading to an inconsistent API across the tools.

You might see some scripts using:
- Positional arguments for environments
- Named arguments for environments
- Environment variables for configuration
- Different default behaviors for similar operations

### 3. Error Handling Discrepancies

Different scripts might handle errors differently, and maintaining backward compatibility limits our ability to standardize error handling across all tools. This can make troubleshooting more difficult as errors from different scripts might need to be interpreted differently.

Some scripts might:
- Return error codes
- Raise exceptions
- Log errors but continue execution
- Have different verbosity levels for similar error conditions

### 4. Documentation Fragmentation

As features are added to existing scripts, documentation becomes more complex. With a standalone module, documentation could be more structured and comprehensive. The current approach might lead to documentation that's more fragmented across different script files.

This makes it harder for new developers to understand the system as a whole and might lead to confusion about which script to use for which purpose.

### 5. Testing Challenges

The existing scripts might not have been designed with comprehensive testing in mind. As you enhance them, maintaining backward compatibility might limit your ability to make them more testable. This could make it harder to ensure that changes don't introduce regressions.

Testing challenges might include:
- Difficulty mocking dependencies
- Side effects that are hard to isolate
- Complex state management across function calls
- Limited ability to run tests in isolation

## Mitigating These Challenges

Despite these challenges, there are ways to mitigate the issues while still maintaining backward compatibility:

1. **Documentation**: Comprehensive documentation (like the guide I provided) helps developers understand how to use the tools effectively despite their complexities.

2. **Gradual Standardization**: While maintaining backward compatibility, gradually standardize the API patterns where possible, using deprecation warnings to guide users toward the preferred approach.

3. **Test Coverage**: Develop comprehensive tests for the scripts, focusing on their enhanced functionality. This helps catch regressions despite the complexity.

4. **Wrapper Interfaces**: Consider creating higher-level wrapper functions or classes that provide a more consistent interface while using the existing scripts internally.

5. **Code Comments**: Thoroughly document complex parameter handling and decision logic within the code itself to help future maintainers understand the rationale.

The approach you've chosen – enhancing existing scripts rather than creating new ones – is pragmatic and addresses your immediate needs while minimizing disruption. The challenges I've outlined are manageable with good practices, and the benefits of backward compatibility often outweigh the drawbacks, especially in an actively used system.