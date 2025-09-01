Database Operations Guide for Skinspire HMS
This guide covers the essential database operations available through the manage_db.py script in the Skinspire Hospital Management System.
Basic Environment Setup
Before using these commands, ensure your environment is properly configured:
bashCopy# View current environment
python scripts/manage_db.py switch-env --status

# Switch to development environment
python scripts/manage_db.py switch-env dev

# Switch to test environment
python scripts/manage_db.py switch-env test

# Switch to production environment (use with caution)
python scripts/manage_db.py switch-env prod
Checking Database Status
bashCopy# Perform database connection checks
python scripts/manage_db.py check-database

# Show current database configuration
python scripts/manage_db.py show-db-config

# Inspect database structure
python scripts/manage_db.py inspect-db

# List specific tables
python scripts/manage_db.py inspect-db --tables

# Show details for a specific table
python scripts/manage_db.py inspect-db --table hospital_settings
Model-Driven Schema Management
These commands use your SQLAlchemy models as the source of truth for the database schema:
bashCopy# Detect changes between models and database
python scripts/manage_db.py detect-schema-changes

# Create migration from detected model changes
python scripts/manage_db.py create-model-migration -m "Add hospital settings table"

# Create and apply in one step
python scripts/manage_db.py create-model-migration -m "Add hospital settings table" --apply

# Directly sync models to database (dev environment only)
python scripts/manage_db.py sync-models-to-db
Traditional Migration Management
bashCopy# Create a new migration
python scripts/manage_db.py create-db-migration -m "Your migration message"

# Create migration and apply it immediately
python scripts/manage_db.py create-db-migration -m "Your migration message" --apply

# Apply pending migrations
python scripts/manage_db.py apply-db-migration

# Roll back the most recent migration
python scripts/manage_db.py rollback-db-migration

# Roll back multiple migrations
python scripts/manage_db.py rollback-db-migration --steps 3

# Show migration history
python scripts/manage_db.py show-all-migrations

# Reset migration tracking (advanced)
python scripts/manage_db.py reset-migration-tracking

# Clean up old migration files
python scripts/manage_db.py clean-migration-files

# Mark migrations as applied without database changes
python scripts/manage_db.py stamp-migrations
Database Backup and Restore
bashCopy# Create a backup of current environment's database
python scripts/manage_db.py create-backup

# Create a backup of a specific environment
python scripts/manage_db.py create-backup --env test

# List all available backups
python scripts/manage_db.py list-all-backups

# Restore a database from backup (interactive)
python scripts/manage_db.py restore-backup

# Restore from a specific backup file
python scripts/manage_db.py restore-backup path/to/backup.sql
Database Copying Between Environments
bashCopy# Copy development database to test environment
python scripts/manage_db.py copy-db dev test

# Copy only schema (no data)
python scripts/manage_db.py copy-db dev test --schema-only

# Copy only data (preserve schema)
python scripts/manage_db.py copy-db dev test --data-only
Trigger Management
bashCopy# Apply base database triggers
python scripts/manage_db.py apply-base-db-triggers

# Apply all database triggers
python scripts/manage_db.py apply-db-triggers

# Apply triggers to all schemas
python scripts/manage_db.py apply-all-db-schema-triggers

# Verify trigger installation
python scripts/manage_db.py verify-db-triggers

# Test trigger functionality
python scripts/manage_db.py test-db-triggers
Database Reset and Initialization
bashCopy# Reset database (drops all tables)
python scripts/manage_db.py reset-database

# Initialize database tables
python scripts/manage_db.py initialize-db

# Reset and initialize database in one step
python scripts/manage_db.py reset-and-initialize

# Drop all tables
python scripts/manage_db.py drop-all-db-tables
Direct SQL Execution
bashCopy# Execute SQL from a file
python scripts/manage_db.py execute-sql path/to/sql_file.sql

# Execute SQL to create a specific table
python scripts/manage_db.py execute-sql --table hospital_settings
Best Practices

Development Workflow:

Use sync-models-to-db during active development
Use create-model-migration before committing changes
Use detect-schema-changes to verify what will change


Testing to Production:

Always check changes with detect-schema-changes first
Create explicit migrations with create-model-migration
Test migrations in the test environment before production


Backups:

Create backups before applying migrations to production
Regularly create backups using create-backup
Test restore operations in development environment


Troubleshooting:

Use check-database to verify connectivity
Use inspect-db to examine database structure
Use reset-migration-tracking if migrations get out of sync



This comprehensive set of commands should cover most database management needs for the Skinspire HMS project.