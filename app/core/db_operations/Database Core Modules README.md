# Database Management CLI

The `manage_db.py` script provides a comprehensive command-line interface for managing Skinspire's database operations across different environments (development, testing, production).

## Overview

This CLI serves as a unified interface for all database management tasks, including:

- Database backup and restore operations
- Database copying between environments
- Migration management
- Database schema and trigger management
- Schema management with developer-friendly workflow
- General database maintenance tasks
- Environment switching
- Database inspection and analysis

## Architecture

The script follows a modular design pattern:
- It acts as a thin adapter over the core database operation modules in `app/core/db_operations/`
- It handles CLI argument parsing, user interaction, and command routing
- It delegates the actual implementation to specialized core modules

## Usage

### General Usage

```bash
python scripts/manage_db.py [COMMAND] [OPTIONS]
```

### Available Commands

#### Schema Management

```bash
# Directly sync models to database schema (DEVELOPMENT ONLY)
python scripts/manage_db.py sync-dev-schema

# Detect changes between models and database schema
python scripts/manage_db.py detect-schema-changes

# Prepare migration files from model changes
python scripts/manage_db.py prepare-migration -m "Description of changes"
```

#### Environment Management

```bash
# Switch to a different environment
python scripts/manage_db.py switch-env dev
python scripts/manage_db.py switch-env test
python scripts/manage_db.py switch-env prod

# Show current environment status
python scripts/manage_db.py switch-env --status
```

#### Database Inspection

```bash
# General database overview
python scripts/manage_db.py inspect-db

# Inspect a specific environment
python scripts/manage_db.py inspect-db test

# List all tables
python scripts/manage_db.py inspect-db --tables

# Filter by schema
python scripts/manage_db.py inspect-db --schema public

# Show details for a specific table
python scripts/manage_db.py inspect-db --table users

# List all triggers
python scripts/manage_db.py inspect-db --triggers

# List all functions
python scripts/manage_db.py inspect-db --functions
```

#### Backup and Restore

```bash
# Create a backup of the current environment's database
python scripts/manage_db.py create-backup

# Create a backup of a specific environment
python scripts/manage_db.py create-backup --env dev

# List all available backups
python scripts/manage_db.py list-all-backups

# Restore from a backup
python scripts/manage_db.py restore-backup [BACKUP_FILE]
```

#### Database Copy

```bash
# Copy database from one environment to another
python scripts/manage_db.py copy-db dev test

# Copy only schema (no data)
python scripts/manage_db.py copy-db dev test --schema-only

# Copy only data (preserve schema)
python scripts/manage_db.py copy-db dev test --data-only
```

#### Migration Management

```bash
# Create a new migration
python scripts/manage_db.py create-db-migration -m "Migration message"

# Show all migrations
python scripts/manage_db.py show-all-migrations

# Roll back migrations
python scripts/manage_db.py rollback-db-migration
```

#### Trigger Management

```bash
# Apply database triggers
python scripts/manage_db.py apply-db-triggers

# Apply only base triggers
python scripts/manage_db.py apply-base-db-triggers

# Apply triggers to all schemas
python scripts/manage_db.py apply-all-db-schema-triggers

# Verify trigger installation
python scripts/manage_db.py verify-db-triggers

# Test trigger functionality
python scripts/manage_db.py test-db-triggers
```

#### Database Maintenance

```bash
# Check database connection and configuration
python scripts/manage_db.py check-database

# Show database configuration
python scripts/manage_db.py show-db-config

# Initialize database
python scripts/manage_db.py initialize-db

# Reset database (drop and recreate tables)
python scripts/manage_db.py reset-database

# Drop all tables
python scripts/manage_db.py drop-all-db-tables

# Reset and initialize database
python scripts/manage_db.py reset-and-initialize
```

## Schema Management Workflow

The database management system now supports a hybrid approach to schema management:

1. **Development Phase**:
   - Modify model definitions in `app/models/`
   - Use `sync-dev-schema` for immediate database updates
   - Rapidly iterate on schema changes

2. **Preparing for Testing/Production**:
   - Run `detect-schema-changes` to see what's changed
   - Use `prepare-migration` to create proper migration files
   - Review migration files before committing

3. **Testing and Production**:
   - Apply migrations using existing migration commands
   - Never use `sync-dev-schema` outside development

## Core Module Integration

This CLI script integrates with the core database operation modules located in `app/core/db_operations/`. These modules implement the actual functionality, while the CLI script provides the user interface.

The script automatically:

1. Imports core modules when available
2. Falls back to internal implementations if core modules aren't found (for backward compatibility)
3. Passes command-line arguments to the appropriate core functions
4. Formats and displays the results

## Environment Handling

The script automatically detects and respects the current environment:

- It reads environment settings from `.env` and `.flask_env_type` files
- It uses the appropriate database URL for the detected environment
- It allows environment override via command-line arguments for most commands
- It provides the `switch-env` command to explicitly change the active environment

## Database Inspection

The `inspect-db` command provides comprehensive database inspection capabilities:

- Overview of database structure, size, and version
- Table listing with row counts and sizes
- Detailed table inspection with columns, constraints, and indexes
- Trigger and function listing with filtering options
- Schema-specific filtering

## Best Practices

1. Always create backups before destructive operations:
   ```bash
   python scripts/manage_db.py create-backup
   ```

2. Use `sync-dev-schema` for development only:
   ```bash
   # Development only!
   python scripts/manage_db.py sync-dev-schema
   ```

3. Generate proper migrations for changes:
   ```bash
   python scripts/manage_db.py prepare-migration -m "Added user preferences"
   ```

4. Always include migration files in code reviews

5. Never use direct schema sync in testing or production:
   ```bash
   # For testing and production, always use migrations
   python scripts/manage_db.py apply-migrations --env test
   ```

6. Verify database triggers after application upgrades:
   ```bash
   python scripts/manage_db.py verify-db-triggers
   ```

7. Before restoring a database, ensure you have a backup of the current state:
   ```bash
   python scripts/manage_db.py create-backup
   python scripts/manage_db.py restore-backup path/to/backup.sql
   ```

8. When copying databases, be aware of potential data loss in the target environment:
   ```bash
   # Safer approach - create a backup first
   python scripts/manage_db.py create-backup --env test
   python scripts/manage_db.py copy-db dev test
   ```

9. When switching environments, verify the current status:
   ```bash
   python scripts/manage_db.py switch-env --status
   ```

10. Use database inspection before making schema changes:
   ```bash
   python scripts/manage_db.py inspect-db --table users
   ```

## Environment Consistency

The CLI maintains environment consistency by:

1. Reading from `.flask_env_type` for the current environment
2. Using the environment specified in command-line arguments when provided
3. Respecting the `FLASK_ENV` environment variable for operations
4. Providing clear feedback about the active environment during operations

## Notes

- This CLI maintains backward compatibility with existing scripts and processes
- Commands provide interactive confirmation for potentially destructive operations
- Error handling ensures clean exit codes for automation and CI/CD integration
- Environment switching ensures consistent behavior across operations