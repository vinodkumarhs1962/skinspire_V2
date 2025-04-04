# SkinSpire Database Management Strategy
## Comprehensive Schema and Data Management Across Environments

This document outlines the comprehensive strategy for managing both database schema and data across development, testing, and production environments for the SkinSpire Hospital Management System.

## Current Architecture

The existing database management system follows a well-designed layered architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE MANAGEMENT SYSTEM                          │
│                                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────┐  │
│  │ Environment   │   │ Configuration │   │   Database    │   │ Testing   │  │
│  │ Management    │   │ Management    │   │   Access      │   │ Framework │  │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └─────┬─────┘  │
│          │                   │                   │                 │        │
│          ▼                   ▼                   ▼                 ▼        │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────┐  │
│  │ environment.py│   │ db_config.py  │   │ database_     │   │ test_db_  │  │
│  │ env_setup.py  │   │ settings.py   │   │ service.py    │   │ features  │  │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └─────┬─────┘  │
│          │                   │                   │                 │        │
│          │                   │                   │                 │        │
│          └─────────┬─────────┴─────────┬─────────┘                 │        │
│                    │                   │                           │        │
│                    ▼                   ▼                           │        │
│           ┌───────────────────┐  ┌────────────────────┐           │        │
│           │  Database         │  │ Core Database      │           │        │
│           │  Operations       │◄─┤ Operations         │◄──────────┘        │
│           └────────┬──────────┘  └────────┬───────────┘                    │
│                    │                      │                                 │
│                    ▼                      ▼                                 │
│           ┌──────────────────────────────────────────┐                     │
│           │             manage_db.py                 │                     │
│           └──────────────────────────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Implementation Status

The system has successfully implemented core building blocks with the following capabilities:

1. **Environment Management**: Central system for determining and managing environments
2. **Configuration Management**: Environment-specific configuration for database connections
3. **Database Access**: Unified interface for database access (`database_service.py`)
4. **Core Database Operations**: Modules for backup, restore, copy, migration, and maintenance
5. **CLI Interface**: User-friendly command-line interface (`manage_db.py`)

## Enhanced Strategy Overview

To build upon this foundation, we will extend the system with two key capabilities:

1. **Enhanced Schema Management**: Hybrid approach for managing schema evolution
2. **Comprehensive Data Management**: Structured approach for managing data across environments

### Core Principles

1. **Developer Experience**: Optimize for developer productivity while maintaining controls
2. **Environment Integrity**: Ensure each environment has appropriate data quality and security
3. **Traceability**: Maintain history of all schema and data changes
4. **Automation**: Reduce manual processes in favor of automated solutions
5. **Compliance**: Support healthcare compliance requirements, particularly for data management

## Phased Implementation Plan

### Phase 1: Developer-Friendly Schema Management

**Objective**: Implement a hybrid schema management approach that balances developer productivity with proper schema control.

#### Key Deliverables

1. **Schema Sync Module** (`app/core/db_operations/schema_sync.py`)
   - Direct schema sync for development environment
   - Schema comparison utilities
   - Schema change detection

2. **Extended CLI Commands**
   - `sync-dev-schema`: Directly sync models to dev database
   - `detect-schema-changes`: Identify differences between models and database
   - `prepare-migration`: Generate migration files from detected changes

#### Implementation Steps

1. Create the schema sync module with core functions:
   ```python
   def sync_models_to_schema(env: str, backup: bool = True) -> bool
   def detect_model_changes() -> Dict[str, Any]
   def generate_migration_from_changes(message: str, changes: Dict[str, Any]) -> bool
   ```

2. Extend `manage_db.py` with new commands that leverage these functions

3. Document workflow for developers on when to use direct sync vs. migrations

#### Success Criteria

- Developers can rapidly iterate on model changes in development
- All changes are properly captured in migrations before promotion
- Proper schema history is maintained in migration files
- Testing and production environments use migration-only approach

### Phase 2: Reference and Configuration Data Management

**Objective**: Implement capabilities to manage reference data and configuration across environments.

#### Key Deliverables

1. **Data Management Module** (`app/core/db_operations/data_management.py`)
   - Export/import reference data
   - Export/import configuration data
   - Data synchronization between environments

2. **Extended CLI Commands**
   - `export-reference-data`: Export reference tables to file
   - `import-reference-data`: Import reference data from file
   - `sync-reference-data`: Copy reference data between environments
   - `export-configuration`: Export configuration settings
   - `import-configuration`: Import configuration settings
   - `sync-configuration`: Synchronize configuration between environments

#### Implementation Steps

1. Define reference and configuration data tables:
   - Create a registry of reference tables (e.g., blood groups, medicine categories)
   - Create a registry of configuration tables (e.g., system parameters, workflows)

2. Implement core data export/import functions:
   ```python
   def export_table_data(env: str, tables: List[str], output_file: str) -> bool
   def import_table_data(env: str, tables: List[str], input_file: str) -> bool
   def sync_table_data(source_env: str, target_env: str, tables: List[str]) -> bool
   ```

3. Implement higher-level functions using these core functions:
   ```python
   def export_reference_data(env: str, output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]
   def import_reference_data(env: str, input_file: str) -> bool
   def sync_reference_data(source_env: str, target_env: str) -> bool
   # Similar functions for configuration data
   ```

4. Extend `manage_db.py` with new commands

#### Success Criteria

- Reference data can be consistently managed across environments
- Configuration can be migrated between environments
- Data operations are properly logged and traceable
- Reduced manual effort for maintaining consistent reference data

### Phase 3: Test Data Management

**Objective**: Enhance capabilities for managing test data to support development and testing.

#### Key Deliverables

1. **Test Data Management Module** (`app/core/db_operations/test_data.py`)
   - Enhanced test data generation
   - Test data refresh capabilities
   - Scenario-based test data management

2. **Extended CLI Commands**
   - `refresh-test-data`: Refresh all test data
   - `generate-test-scenario`: Generate specific test scenario data
   - `clear-test-data`: Clear test data from specific tables

#### Implementation Steps

1. Enhance `populate_test_data.py` to support more flexible scenarios:
   - Modularize data creation by domain (patients, doctors, appointments, etc.)
   - Support scenario-based data generation
   - Add options for volume and complexity of test data

2. Implement core test data functions:
   ```python
   def refresh_test_data(env: str, modules: Optional[List[str]] = None) -> bool
   def generate_test_scenario(env: str, scenario: str) -> bool
   def clear_test_data(env: str, tables: List[str]) -> bool
   ```

3. Extend `manage_db.py` with new commands

#### Success Criteria

- Testing team can quickly refresh test data when needed
- Specific test scenarios can be easily created
- Test data is realistic enough for proper testing
- Test data is isolated from production data

### Phase 4: Healthcare-Specific Data Governance

**Objective**: Implement capabilities to support healthcare compliance requirements for data management.

#### Key Deliverables

1. **Data Governance Module** (`app/core/db_operations/data_governance.py`)
   - Data anonymization
   - Sensitive data identification
   - Audit logging for data operations

2. **Extended CLI Commands**
   - `export-anonymized-data`: Export anonymized data
   - `scan-sensitive-data`: Scan database for sensitive data
   - `show-data-audit-log`: Show audit log for data operations

#### Implementation Steps

1. Implement data anonymization functions:
   ```python
   def anonymize_patient_data(data: Dict[str, Any]) -> Dict[str, Any]
   def export_anonymized_data(env: str, tables: List[str], output_file: str) -> bool
   def scan_for_sensitive_data(env: str) -> Dict[str, Any]
   ```

2. Enhance logging for data operations:
   ```python
   def log_data_operation(operation: str, user: str, tables: List[str], record_count: int) -> bool
   def get_data_operation_logs(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]
   ```

3. Extend `manage_db.py` with new commands

#### Success Criteria

- Sensitive patient data can be properly anonymized for non-production use
- All data operations are properly logged for audit purposes
- System can identify potential sensitive data in custom fields
- Compliance with healthcare data protection requirements

## Implementation Details

### Schema Sync Module (Phase 1)

```python
# app/core/db_operations/schema_sync.py

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import inspect, MetaData, Table, Column, text
from sqlalchemy.schema import ForeignKeyConstraint, Index
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_db_config, logger, project_root
from .backup import backup_database

def sync_models_to_schema(env: str, backup: bool = True) -> bool:
    """
    Sync models directly to database schema for development
    
    Args:
        env: Target environment
        backup: Whether to create backup before sync
        
    Returns:
        True if successful, False otherwise
    """
    # Only allow in development
    if env not in ('development', 'dev'):
        logger.error("Schema sync only allowed in development environment")
        return False
    
    if backup:
        # Create backup first
        success, _ = backup_database(env)
        if not success:
            logger.warning("Failed to create backup before sync")
    
    # Get models and metadata
    from app.models import Base
    
    def _sync_models(db):
        try:
            # Disable triggers and constraints temporarily
            db.session.execute(text("SET session_replication_role = 'replica';"))
            
            # Apply schema changes directly
            Base.metadata.create_all(bind=db.engine, checkfirst=True)
            
            # Re-enable triggers and constraints
            db.session.execute(text("SET session_replication_role = 'origin';"))
            db.session.commit()
            
            logger.info("Model sync completed successfully")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing schema: {str(e)}")
            return False
    
    return _with_app_context(_sync_models)

def detect_model_changes() -> Dict[str, Any]:
    """
    Detect changes between models and current database schema
    
    Returns:
        Dictionary with detected changes
    """
    # Import models
    from app.models import Base
    
    def _detect_changes(db):
        try:
            # Get model metadata
            model_metadata = Base.metadata
            
            # Get database inspector
            inspector = inspect(db.engine)
            
            changes = []
            
            # Check tables in model but not in database
            db_tables = set(inspector.get_table_names())
            model_tables = set(model_metadata.tables.keys())
            
            # New tables
            new_tables = model_tables - db_tables
            for table_name in new_tables:
                changes.append(f"New table: {table_name}")
            
            # Tables in database but not in model (not necessarily an issue)
            extra_tables = db_tables - model_tables
            for table_name in extra_tables:
                changes.append(f"Extra table in database: {table_name}")
            
            # Check columns in model but not in database
            for table_name in model_tables.intersection(db_tables):
                model_table = model_metadata.tables[table_name]
                db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                
                # Check for new or modified columns
                for column in model_table.columns:
                    col_name = column.name
                    if col_name not in db_columns:
                        changes.append(f"New column: {table_name}.{col_name}")
                    else:
                        # Column exists, check type
                        if not column_types_match(column, db_columns[col_name]):
                            changes.append(f"Column type change: {table_name}.{col_name}")
                
                # Check for columns in db but not in model
                model_column_names = {col.name for col in model_table.columns}
                for db_col_name in db_columns:
                    if db_col_name not in model_column_names:
                        changes.append(f"Extra column in database: {table_name}.{db_col_name}")
            
            # TODO: Add checks for indices, constraints, etc.
            
            return {
                'has_changes': len(changes) > 0,
                'changes': changes
            }
            
        except Exception as e:
            logger.error(f"Error detecting schema changes: {str(e)}")
            return {
                'has_changes': False,
                'changes': [],
                'error': str(e)
            }
    
    return _with_app_context(_detect_changes)

def column_types_match(model_column, db_column) -> bool:
    """
    Compare a model column type with a database column type
    
    Args:
        model_column: SQLAlchemy model column
        db_column: Dictionary with database column info
        
    Returns:
        True if types match, False otherwise
    """
    # This is simplified - would need to be expanded for production use
    # SQLAlchemy types don't always match 1:1 with database types
    model_type = str(model_column.type)
    db_type = db_column['type']
    
    # Basic check - would need refinement
    return model_type.lower() in str(db_type).lower()

def generate_migration_from_changes(message: str, changes: Dict[str, Any]) -> bool:
    """
    Generate migration file from detected changes
    
    Args:
        message: Migration message
        changes: Dictionary with detected changes
        
    Returns:
        True if successful, False otherwise
    """
    # This would integrate with the existing migration.py module
    from .migration import create_migration
    
    # Basic implementation just creates a migration
    success, migration_file = create_migration(message, 'dev')
    
    return success
```

### Data Management Module (Phase 2)

```python
# app/core/db_operations/data_management.py

import json
import csv
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_db_config, logger, project_root
from .backup import backup_database

# Define reference data tables
REFERENCE_TABLES = [
    'role_master',
    'module_master',
    'parameter_settings',
    'blood_group',
    'medicine_category',
    'medicine_type',
    'gender',
    'marital_status',
    'city',
    'prefix',
    # Add other reference tables as needed
]

# Define configuration tables
CONFIGURATION_TABLES = [
    'hospital_config',
    'workflow_config',
    'gst_rates',
    'gl_account',
    'field_parameters_setting',
    # Add other configuration tables as needed
]

def export_table_data(env: str, tables: List[str], output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Export data from specified tables
    
    Args:
        env: Source environment
        tables: List of tables to export
        output_file: Optional output filename
        
    Returns:
        Tuple of (success, output_file_path)
    """
    # Generate default output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"data_export_{timestamp}.json"
    
    output_path = project_root / 'exports' / output_file
    os.makedirs(output_path.parent, exist_ok=True)
    
    def _export_data(db):
        try:
            exported_data = {}
            
            for table in tables:
                # Get table data
                result = db.session.execute(text(f"SELECT * FROM {table}"))
                columns = result.keys()
                
                # Convert to list of dictionaries
                rows = []
                for row in result:
                    rows.append({col: getattr(row, col) for col in columns})
                
                exported_data[table] = rows
                logger.info(f"Exported {len(rows)} rows from {table}")
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(exported_data, f, indent=2, default=str)
                
            logger.info(f"Data export completed successfully: {output_path}")
            return True, output_path
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return False, None
    
    return _with_app_context(_export_data)

def import_table_data(env: str, input_file: str, backup: bool = True) -> bool:
    """
    Import data into specified tables
    
    Args:
        env: Target environment
        input_file: Input filename
        backup: Whether to create backup before import
        
    Returns:
        True if successful, False otherwise
    """
    input_path = Path(input_file)
    if not input_path.exists():
        # Try with exports directory
        input_path = project_root / 'exports' / input_file
        if not input_path.exists():
            logger.error(f"Input file not found: {input_file}")
            return False
    
    # Create backup if requested
    if backup:
        backup_success, _ = backup_database(env)
        if not backup_success:
            logger.warning("Failed to create backup before data import")
    
    def _import_data(db):
        try:
            # Read the file
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            # Import each table
            for table, rows in data.items():
                # Clear existing data
                db.session.execute(text(f"DELETE FROM {table}"))
                
                # Insert new data
                for row in rows:
                    # Format values for SQL insertion
                    columns = list(row.keys())
                    placeholders = [f":{col}" for col in columns]
                    
                    insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    db.session.execute(text(insert_sql), row)
                
                logger.info(f"Imported {len(rows)} rows into {table}")
            
            db.session.commit()
            logger.info("Data import completed successfully")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error importing data: {str(e)}")
            return False
    
    return _with_app_context(_import_data)

def sync_table_data(source_env: str, target_env: str, tables: List[str]) -> bool:
    """
    Synchronize data between environments for specified tables
    
    Args:
        source_env: Source environment
        target_env: Target environment
        tables: List of tables to synchronize
        
    Returns:
        True if successful, False otherwise
    """
    # Export data from source environment
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_file = f"temp_sync_{source_env}_to_{target_env}_{timestamp}.json"
    
    export_success, export_path = export_table_data(source_env, tables, temp_file)
    if not export_success:
        logger.error("Failed to export data from source environment")
        return False
    
    # Import data to target environment
    import_success = import_table_data(target_env, str(export_path))
    
    # Clean up temporary file
    if export_path and export_path.exists():
        os.remove(export_path)
    
    return import_success

def export_reference_data(env: str, output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Export reference data
    
    Args:
        env: Source environment
        output_file: Optional output filename
        
    Returns:
        Tuple of (success, output_file_path)
    """
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"reference_data_{env}_{timestamp}.json"
    
    return export_table_data(env, REFERENCE_TABLES, output_file)

def import_reference_data(env: str, input_file: str) -> bool:
    """
    Import reference data
    
    Args:
        env: Target environment
        input_file: Input filename
        
    Returns:
        True if successful, False otherwise
    """
    return import_table_data(env, input_file)

def sync_reference_data(source_env: str, target_env: str) -> bool:
    """
    Synchronize reference data between environments
    
    Args:
        source_env: Source environment
        target_env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    return sync_table_data(source_env, target_env, REFERENCE_TABLES)

def export_configuration(env: str, output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Export configuration data
    
    Args:
        env: Source environment
        output_file: Optional output filename
        
    Returns:
        Tuple of (success, output_file_path)
    """
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"configuration_{env}_{timestamp}.json"
    
    return export_table_data(env, CONFIGURATION_TABLES, output_file)

def import_configuration(env: str, input_file: str) -> bool:
    """
    Import configuration data
    
    Args:
        env: Target environment
        input_file: Input filename
        
    Returns:
        True if successful, False otherwise
    """
    return import_table_data(env, input_file)

def sync_configuration(source_env: str, target_env: str) -> bool:
    """
    Synchronize configuration between environments
    
    Args:
        source_env: Source environment
        target_env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    return sync_table_data(source_env, target_env, CONFIGURATION_TABLES)
```

### Test Data Management Module (Phase 3)

```python
# app/core/db_operations/test_data.py

import logging
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_db_config, logger, project_root
from .backup import backup_database

def refresh_test_data(env: str, backup: bool = True, modules: Optional[List[str]] = None) -> bool:
    """
    Refresh test data in the specified environment
    
    Args:
        env: Target environment
        backup: Whether to create backup before refresh
        modules: Optional list of modules to refresh (e.g., ['patients', 'doctors'])
        
    Returns:
        True if successful, False otherwise
    """
    # Only allow in development or testing environments
    if env not in ('development', 'dev', 'testing', 'test'):
        logger.error("Test data refresh only allowed in development or testing environments")
        return False
    
    # Create backup if requested
    if backup:
        backup_success, _ = backup_database(env)
        if not backup_success:
            logger.warning("Failed to create backup before test data refresh")
    
    try:
        # Set environment variable
        os.environ['FLASK_ENV'] = 'development' if env in ('development', 'dev') else 'testing'
        
        # Prepare command-line arguments
        args = [sys.executable, str(project_root / 'scripts' / 'populate_test_data.py')]
        
        # Add module parameters if specified
        if modules:
            for module in modules:
                args.extend(['--module', module])
        
        # Run the script
        logger.info(f"Running populate_test_data.py for {env} environment")
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        
        # Check output
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
        
        logger.info("Test data refresh completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error refreshing test data: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error refreshing test data: {str(e)}")
        return False

def generate_test_scenario(env: str, scenario: str, backup: bool = True) -> bool:
    """
    Generate specific test scenario data
    
    Args:
        env: Target environment
        scenario: Name of scenario to generate
        backup: Whether to create backup before generating scenario
        
    Returns:
        True if successful, False otherwise
    """
    # Only allow in development or testing environments
    if env not in ('development', 'dev', 'testing', 'test'):
        logger.error("Test scenario generation only allowed in development or testing environments")
        return False
    
    # Create backup if requested
    if backup:
        backup_success, _ = backup_database(env)
        if not backup_success:
            logger.warning("Failed to create backup before generating test scenario")
    
    try:
        # Set environment variable
        os.environ['FLASK_ENV'] = 'development' if env in ('development', 'dev') else 'testing'
        
        # Prepare command-line arguments
        args = [
            sys.executable, 
            str(project_root / 'scripts' / 'populate_test_data.py'),
            '--scenario', scenario
        ]
        
        # Run the script
        logger.info(f"Running populate_test_data.py with scenario {scenario} for {env} environment")
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        
        # Check output
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
        
        logger.info(f"Test scenario '{scenario}' generated successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating test scenario: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error generating test scenario: {str(e)}")
        return False

def clear_test_data(env: str, tables: List[str], backup: bool = True) -> bool:
    """
    Clear test data from specified tables
    
    Args:
        env: Target environment
        tables: List of tables to clear
        backup: Whether to create backup before clearing data
        
    Returns:
        True if successful, False otherwise
    """
    # Only allow in development or testing environments
    if env not in ('development', 'dev', 'testing', 'test'):
        logger.error("Test data clearing only allowed in development or testing environments")
        return False
    
    # Create backup if requested
    if backup:
        backup_success, _ = backup_database(env)
        if not backup_success:
            logger.warning("Failed to create backup before clearing test data")
    
    def _clear_data(db):
        try:
            # Clear data from each table
            for table in tables:
                db.session.execute(text(f"DELETE FROM {table}"))
                logger.info(f"Cleared data from {table}")
            
            db.session.commit()
            logger.info("Test data clearing completed successfully")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing test data: {str(e)}")
            return False
    
    return _with_app_context(_clear_data)
```

### Data Governance Module (Phase 4)

```python
# app/core/db_operations/data_governance.py

import json
import os
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import text, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_db_config, logger, project_root
from .backup import backup_database

# Define sensitive data patterns
SENSITIVE_DATA_PATTERNS = {
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'phone': r'\b\d{10}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'address': r'\b\d+\s+[A-Za-z\s]+(?:Avenue|Ave|Street|St|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way)\b',
    'name': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
}

# Define tables with sensitive data
SENSITIVE_TABLES = {
    'patients': ['personal_info', 'contact_info', 'medical_info', 'emergency_contact'],
    'staff': ['personal_info', 'contact_info'],
    'users': ['password_hash']
}

def anonymize_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anonymize patient data
    
    Args:
        patient_data: Dictionary with patient data
        
    Returns:
        Dictionary with anonymized patient data
    """
    # Create a copy to avoid modifying original
    anonymized = patient_data.copy()
    
    # Anonymize personal information
    if 'personal_info' in anonymized:
        personal_info = anonymized['personal_info']
        if isinstance(personal_info, dict):
            if 'first_name' in personal_info:
                personal_info['first_name'] = f"Patient{hash(str(personal_info.get('first_name', '')))[:5]}"
            if 'last_name' in personal_info:
                personal_info['last_name'] = f"Anonymous{hash(str(personal_info.get('last_name', '')))[:5]}"
            # Keep gender, dob, etc. as they may be important for analysis
    
    # Anonymize contact information
    if 'contact_info' in anonymized:
        contact_info = anonymized['contact_info']
        if isinstance(contact_info, dict):
            if 'email' in contact_info:
                contact_info['email'] = f"patient{hash(str(contact_info.get('email', '')))[:5]}@example.com"
            if 'phone' in contact_info:
                contact_info['phone'] = f"9{hash(str(contact_info.get('phone', '')))[:9]}"
            if 'address' in contact_info and isinstance(contact_info['address'], dict):
                address = contact_info['address']
                address['street'] = f"{hash(str(address.get('street', '')))[:3]} Anonymous St"
                # Keep city, zip for demographic analysis
    
    # Completely anonymize medical information
    if 'medical_info' in anonymized:
        # Replace with notification that data was anonymized
        anonymized['medical_info'] = "[MEDICAL DATA ANONYMIZED FOR PRIVACY]"
    
    # Anonymize emergency contact
    if 'emergency_contact' in anonymized:
        emergency = anonymized['emergency_contact']
        if isinstance(emergency, dict):
            if 'name' in emergency:
                emergency['name'] = f"Emergency{hash(str(emergency.get('name', '')))[:5]}"
            if 'phone' in emergency:
                emergency['phone'] = f"9{hash(str(emergency.get('phone', '')))[:9]}"
            # Keep relationship as it may be important for analysis
    
    return anonymized

def export_anonymized_data(env: str, tables: List[str], output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Export anonymized data from specified tables
    
    Args:
        env: Source environment
        tables: List of tables to export
        output_file: Optional output filename
        
    Returns:
        Tuple of (success, output_file_path)
    """
    # Generate default output filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"anonymized_data_{timestamp}.json"
    
    output_path = project_root / 'exports' / output_file
    os.makedirs(output_path.parent, exist_ok=True)
    
    def _export_anonymized_data(db):
        try:
            exported_data = {}
            
            for table in tables:
                # Get table data
                result = db.session.execute(text(f"SELECT * FROM {table}"))
                columns = result.keys()
                
                # Convert to list of dictionaries
                rows = []
                for row in result:
                    row_dict = {col: getattr(row, col) for col in columns}
                    
                    # Apply anonymization based on table type
                    if table == 'patients':
                        row_dict = anonymize_patient_data(row_dict)
                    elif table == 'staff':
                        # Similar anonymization for staff data
                        # Implementation would be similar to anonymize_patient_data
                        pass
                    elif table == 'users':
                        # Anonymize user data
                        if 'password_hash' in row_dict:
                            row_dict['password_hash'] = '[REDACTED]'
                    
                    rows.append(row_dict)
                
                exported_data[table] = rows
                logger.info(f"Exported {len(rows)} anonymized rows from {table}")
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(exported_data, f, indent=2, default=str)
                
            logger.info(f"Anonymized data export completed successfully: {output_path}")
            return True, output_path
        except Exception as e:
            logger.error(f"Error exporting anonymized data: {str(e)}")
            return False, None
    
    return _with_app_context(_export_anonymized_data)

def scan_for_sensitive_data(env: str) -> Dict[str, Any]:
    """
    Scan database for sensitive data patterns
    
    Args:
        env: Target environment
        
    Returns:
        Dictionary with scan results
    """
    def _scan_data(db):
        results = {
            'tables_scanned': 0,
            'fields_scanned': 0,
            'sensitive_fields_found': 0,
            'findings': []
        }
        
        try:
            # Get all tables in database
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            results['tables_scanned'] = len(tables)
            
            for table in tables:
                # Get table columns
                columns = inspector.get_columns(table)
                results['fields_scanned'] += len(columns)
                
                # Check each column for sensitive data patterns
                for column in columns:
                    column_name = column['name']
                    
                    # Skip binary/blob columns
                    if 'BLOB' in str(column['type']).upper() or 'BINARY' in str(column['type']).upper():
                        continue
                    
                    # Check for sensitive field names
                    sensitive_name = False
                    for pattern in ['password', 'secret', 'key', 'token', 'ssn', 'credit']:
                        if pattern in column_name.lower():
                            results['sensitive_fields_found'] += 1
                            results['findings'].append({
                                'table': table,
                                'column': column_name,
                                'type': 'sensitive_name',
                                'pattern': pattern
                            })
                            sensitive_name = True
                            break
                    
                    if sensitive_name:
                        continue
                    
                    # Sample data to check for patterns
                    try:
                        # Get a sample of 20 rows
                        sample = db.session.execute(
                            text(f"SELECT {column_name} FROM {table} LIMIT 20")
                        ).fetchall()
                        
                        # Check each sample for sensitive patterns
                        for pattern_name, regex in SENSITIVE_DATA_PATTERNS.items():
                            pattern = re.compile(regex)
                            for row in sample:
                                value = str(row[0]) if row[0] is not None else ''
                                if pattern.search(value):
                                    results['sensitive_fields_found'] += 1
                                    results['findings'].append({
                                        'table': table,
                                        'column': column_name,
                                        'type': 'pattern_match',
                                        'pattern': pattern_name
                                    })
                                    break
                    except Exception as e:
                        logger.warning(f"Could not scan {table}.{column_name}: {e}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error scanning for sensitive data: {str(e)}")
            return {
                'error': str(e),
                'tables_scanned': results['tables_scanned'],
                'fields_scanned': results['fields_scanned'],
                'sensitive_fields_found': results['sensitive_fields_found']
            }
    
    return _with_app_context(_scan_data)

def log_data_operation(operation: str, user: str, tables: List[str], record_count: int) -> bool:
    """
    Log a data operation for audit purposes
    
    Args:
        operation: Operation type (e.g., 'export', 'import', 'anonymize')
        user: User performing the operation
        tables: Tables affected
        record_count: Number of records affected
        
    Returns:
        True if successful, False otherwise
    """
    def _log_operation(db):
        try:
            # Create log entry
            timestamp = datetime.now().isoformat()
            log_entry = {
                'timestamp': timestamp,
                'operation': operation,
                'user': user,
                'tables': ','.join(tables),
                'record_count': record_count
            }
            
            # Check if data_operation_log table exists
            inspector = db.inspect(db.engine)
            if 'data_operation_log' not in inspector.get_table_names():
                # Create table if it doesn't exist
                db.session.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_operation_log (
                        log_id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        operation VARCHAR(50) NOT NULL,
                        user_id VARCHAR(100) NOT NULL,
                        tables TEXT NOT NULL,
                        record_count INTEGER NOT NULL
                    )
                """))
                db.session.commit()
            
            # Insert log entry
            db.session.execute(text("""
                INSERT INTO data_operation_log 
                (timestamp, operation, user_id, tables, record_count)
                VALUES (:timestamp, :operation, :user, :tables, :record_count)
            """), log_entry)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging data operation: {str(e)}")
            return False
    
    return _with_app_context(_log_operation)

def get_data_operation_logs(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Get data operation logs
    
    Args:
        start_date: Optional filter by start date
        end_date: Optional filter by end date
        
    Returns:
        List of log entries
    """
    def _get_logs(db):
        try:
            # Build query
            query = "SELECT * FROM data_operation_log"
            params = {}
            
            if start_date or end_date:
                query += " WHERE"
                
                if start_date:
                    query += " timestamp >= :start_date"
                    params['start_date'] = start_date
                    
                if end_date:
                    if start_date:
                        query += " AND"
                    query += " timestamp <= :end_date"
                    params['end_date'] = end_date
            
            query += " ORDER BY timestamp DESC"
            
            # Execute query
            result = db.session.execute(text(query), params)
            
            # Convert to list of dictionaries
            logs = []
            for row in result:
                logs.append({
                    'log_id': row.log_id,
                    'timestamp': row.timestamp,
                    'operation': row.operation,
                    'user_id': row.user_id,
                    'tables': row.tables.split(','),
                    'record_count': row.record_count
                })
            
            return logs
        except Exception as e:
            logger.error(f"Error retrieving data operation logs: {str(e)}")
            return []
    
    return _with_app_context(_get_logs)
```

### CLI Extensions

To implement these modules in the `manage_db.py` CLI, we need to add new commands for each phase:

```python
# Phase 1: Schema Management Commands

@cli.command()
@click.option('--force', is_flag=True, help='Force sync without confirmation')
def sync_dev_schema(force):
    """
    Sync models directly to database schema (DEVELOPMENT ONLY)
    
    WARNING: This command is for development use only and may result in data loss.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Ensure we're in development environment
    try:
        from app.core.environment import Environment
        current_env = Environment.get_current_env()
        if current_env != 'development':
            click.echo(f"Current environment is {current_env}. Schema sync only allowed in development.")
            if not click.confirm("Do you want to switch to development environment?"):
                click.echo("Operation cancelled")
                return
            Environment.set_environment('dev')
    except ImportError:
        # Fallback check
        if os.environ.get('FLASK_ENV') not in (None, 'development'):
            click.echo("ERROR: Cannot use sync-dev-schema outside development environment")
            sys.exit(1)
    
    if not force and not click.confirm('Warning! This will modify your database schema to match models. Continue?'):
        click.echo('Operation cancelled')
        return
    
    click.echo('Syncing database schema with models...')
    from app.core.db_operations.schema_sync import sync_models_to_schema
    success = sync_models_to_schema('dev')
    
    if success:
        click.echo('SUCCESS: Database schema synced with models')
    else:
        click.echo('FAILED: Database schema sync failed')
        sys.exit(1)

@cli.command()
def detect_schema_changes():
    """
    Detect changes between models and database schema
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    click.echo('Detecting schema changes...')
    from app.core.db_operations.schema_sync import detect_model_changes
    changes = detect_model_changes()
    
    if changes['has_changes']:
        click.echo(f"\nDetected {len(changes['changes'])} changes:")
        for change in changes['changes']:
            click.echo(f"- {change}")
        
        click.echo("\nTo create a migration with these changes:")
        click.echo("  python scripts/manage_db.py prepare-migration -m \"Your migration message\"")
    else:
        click.echo("No schema changes detected")

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def prepare_migration(message):
    """
    Prepare migration files from development model changes
    
    This command detects changes made to models during development
    and creates proper migration files.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Detect model changes first
    click.echo("Detecting model changes...")
    from app.core.db_operations.schema_sync import detect_model_changes
    changes = detect_model_changes()
    
    if not changes['has_changes']:
        click.echo("No model changes detected")
        return
    
    # Show detected changes
    click.echo("\nDetected changes:")
    for change in changes['changes']:
        click.echo(f"- {change}")
    
    # Create migration
    if click.confirm("Create migration file with these changes?"):
        from app.core.db_operations.migration import create_migration
        success, migration_file = create_migration(message, 'dev', backup=True)
        
        if success:
            click.echo(f"SUCCESS: Migration created at {migration_file}")
            
            if click.confirm("Apply migration to development database?"):
                from app.core.db_operations.migration import apply_migration
                apply_success = apply_migration('dev')
                if apply_success:
                    click.echo("SUCCESS: Migration applied to development database")
                else:
                    click.echo("FAILED: Migration application failed")
        else:
            click.echo("FAILED: Migration creation failed")
            sys.exit(1)

# Phase 2: Data Management Commands

@cli.command()
@click.option('--env', default=None, help='Source environment')
@click.option('--output', help='Output filename')
def export_reference_data(env, output):
    """
    Export reference data to file
    
    This exports essential reference data such as lookup tables,
    codes, and parameters.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If env not specified, use current environment
    if env is None:
        try:
            from app.core.environment import Environment
            env = Environment.get_short_name(Environment.get_current_env())
        except ImportError:
            try:
                from app.config.db_config import DatabaseConfig
                db_env = DatabaseConfig.get_active_env()
                # Convert to short form
                env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
                env = env_map.get(db_env, 'dev')
            except Exception as e:
                click.echo(f"Failed to determine environment: {e}")
                sys.exit(1)
    
    click.echo(f"Exporting reference data from {env} environment...")
    from app.core.db_operations.data_management import export_reference_data
    success, output_path = export_reference_data(env, output)
    
    if success:
        click.echo(f"SUCCESS: Reference data exported to {output_path}")
    else:
        click.echo("FAILED: Reference data export failed")
        sys.exit(1)

@cli.command()
@click.option('--env', default=None, help='Target environment')
@click.argument('file', required=True)
def import_reference_data(env, file):
    """
    Import reference data from file
    
    This imports essential reference data such as lookup tables,
    codes, and parameters.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If env not specified, use current environment
    if env is None:
        try:
            from app.core.environment import Environment
            env = Environment.get_short_name(Environment.get_current_env())
        except ImportError:
            try:
                from app.config.db_config import DatabaseConfig
                db_env = DatabaseConfig.get_active_env()
                # Convert to short form
                env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
                env = env_map.get(db_env, 'dev')
            except Exception as e:
                click.echo(f"Failed to determine environment: {e}")
                sys.exit(1)
    
    # Confirm before import
    if not click.confirm(f'Warning! This will replace reference data in the {env} environment. Continue?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Importing reference data to {env} environment...")
    from app.core.db_operations.data_management import import_reference_data
    success = import_reference_data(env, file)
    
    if success:
        click.echo("SUCCESS: Reference data imported successfully")
    else:
        click.echo("FAILED: Reference data import failed")
        sys.exit(1)

@cli.command()
@click.argument('source', type=click.Choice(['dev', 'test', 'prod']))
@click.argument('target', type=click.Choice(['dev', 'test', 'prod']))
def sync_reference_data(source, target):
    """
    Synchronize reference data between environments
    
    This copies reference data from source to target environment.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    if source == target:
        click.echo("Source and target environments cannot be the same")
        return
    
    # Confirm before sync
    if not click.confirm(f'Warning! This will overwrite reference data in the {target} environment with data from {source}. Continue?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Synchronizing reference data from {source} to {target}...")
    from app.core.db_operations.data_management import sync_reference_data
    success = sync_reference_data(source, target)
    
    if success:
        click.echo(f"SUCCESS: Reference data synchronized from {source} to {target}")
    else:
        click.echo(f"FAILED: Reference data synchronization failed")
        sys.exit(1)

# Similar commands for configuration data...

# Phase 3: Test Data Management Commands

@cli.command()
@click.option('--env', default='test', help='Environment to refresh')
@click.option('--module', multiple=True, help='Specific module to refresh (can be used multiple times)')
def refresh_test_data(env, module):
    """
    Refresh test data in an environment
    
    This wipes and regenerates test data for the specified environment.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Only allow in development or testing environments
    if env not in ('dev', 'test'):
        click.echo("Test data refresh only allowed in development or testing environments")
        return
    
    # Confirm before refresh
    if not click.confirm(f'Warning! This will replace test data in the {env} environment. Continue?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Refreshing test data in {env} environment...")
    from app.core.db_operations.test_data import refresh_test_data
    success = refresh_test_data(env, modules=module if module else None)
    
    if success:
        click.echo(f"SUCCESS: Test data refreshed in {env} environment")
    else:
        click.echo(f"FAILED: Test data refresh failed")
        sys.exit(1)

@cli.command()
@click.option('--env', default='test', help='Environment to use')
@click.argument('scenario', required=True)
def generate_test_scenario(env, scenario):
    """
    Generate specific test scenario data
    
    This creates data for a specific test scenario.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Only allow in development or testing environments
    if env not in ('dev', 'test'):
        click.echo("Test scenario generation only allowed in development or testing environments")
        return
    
    # Confirm before generation
    if not click.confirm(f'Warning! This may modify data in the {env} environment. Continue?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Generating test scenario '{scenario}' in {env} environment...")
    from app.core.db_operations.test_data import generate_test_scenario
    success = generate_test_scenario(env, scenario)
    
    if success:
        click.echo(f"SUCCESS: Test scenario '{scenario}' generated in {env} environment")
    else:
        click.echo(f"FAILED: Test scenario generation failed")
        sys.exit(1)

# Phase 4: Data Governance Commands

@cli.command()
@click.option('--env', default=None, help='Source environment')
@click.option('--table', multiple=True, help='Table to export (can be used multiple times)')
@click.option('--output', help='Output filename')
def export_anonymized_data(env, table, output):
    """
    Export anonymized data for safe use outside production
    
    This exports data with sensitive information anonymized.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If env not specified, use current environment
    if env is None:
        try:
            from app.core.environment import Environment
            env = Environment.get_short_name(Environment.get_current_env())
        except ImportError:
            try:
                from app.config.db_config import DatabaseConfig
                db_env = DatabaseConfig.get_active_env()
                # Convert to short form
                env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
                env = env_map.get(db_env, 'dev')
            except Exception as e:
                click.echo(f"Failed to determine environment: {e}")
                sys.exit(1)
    
    # If no tables specified, use default sensitive tables
    tables = list(table) if table else ['patients', 'staff', 'users']
    
    click.echo(f"Exporting anonymized data from {env} environment...")
    from app.core.db_operations.data_governance import export_anonymized_data, log_data_operation
    success, output_path = export_anonymized_data(env, tables, output)
    
    if success:
        click.echo(f"SUCCESS: Anonymized data exported to {output_path}")
        # Log operation
        log_data_operation('export_anonymized', 'CLI User', tables, 0)
    else:
        click.echo("FAILED: Anonymized data export failed")
        sys.exit(1)

@cli.command()
@click.option('--env', default=None, help='Environment to scan')
def scan_sensitive_data(env):
    """
    Scan database for sensitive data patterns
    
    This analyzes database content to identify potential sensitive data.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If env not specified, use current environment
    if env is None:
        try:
            from app.core.environment import Environment
            env = Environment.get_short_name(Environment.get_current_env())
        except ImportError:
            try:
                from app.config.db_config import DatabaseConfig
                db_env = DatabaseConfig.get_active_env()
                # Convert to short form
                env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
                env = env_map.get(db_env, 'dev')
            except Exception as e:
                click.echo(f"Failed to determine environment: {e}")
                sys.exit(1)
    
    click.echo(f"Scanning {env} environment for sensitive data...")
    from app.core.db_operations.data_governance import scan_for_sensitive_data
    results = scan_for_sensitive_data(env)
    
    click.echo(f"\nScan Results:")
    click.echo(f"Tables scanned: {results.get('tables_scanned', 0)}")
    click.echo(f"Fields scanned: {results.get('fields_scanned', 0)}")
    click.echo(f"Sensitive fields found: {results.get('sensitive_fields_found', 0)}")
    
    if 'findings' in results and results['findings']:
        click.echo("\nDetailed Findings:")
        for finding in results['findings']:
            pattern_info = f" ({finding['pattern']})" if 'pattern' in finding else ""
            click.echo(f"- Table: {finding['table']}, Column: {finding['column']}, Type: {finding['type']}{pattern_info}")
    elif 'error' in results:
        click.echo(f"\nError during scan: {results['error']}")
    else:
        click.echo("\nNo sensitive data patterns found")
```

## Developer Guidelines

### Schema Management Workflow

To ensure consistent development and deployment, follow these guidelines for schema changes:

1. **Development Phase**
   - Make changes to model definitions in `app/models/`
   - Use `sync-dev-schema` for rapid development iteration
   - Test changes in development environment

2. **Preparing for Testing**
   - Run `detect-schema-changes` to identify all changes
   - Use `prepare-migration` to create proper migration files
   - Include migration files in code review

3. **Testing Phase**
   - Apply migrations to testing environment using `apply-migrations --env test`
   - Verify functionality in testing environment

4. **Production Deployment**
   - Apply same migrations to production using `apply-migrations --env prod`
   - Back up production database before applying migrations

### Data Management Workflow

For managing data across environments:

1. **Reference Data**
   - Maintain reference data in development environment
   - Use `export-reference-data` to capture reference data
   - Use `import-reference-data` or `sync-reference-data` to propagate to other environments
   - Include reference data exports in version control

2. **Configuration Data**
   - Maintain separate configurations for each environment
   - Use `export-configuration` to document environment-specific settings
   - Use configuration templates for new environments

3. **Test Data**
   - Use `refresh-test-data` to reset test environment
   - Create test scenarios for specific testing requirements
   - Document test data requirements for automated generation

4. **Production Data**
   - Never copy production data directly to non-production environments
   - Always use `export-anonymized-data` when production-like data is needed
   - Document and approve all production data operations

## Migration Path

To implement this strategy, follow this migration path:

1. **Initial Setup**
   - Review existing code to ensure alignment with the architecture
   - Establish clear documentation for the database management system
   - Ensure proper database backup procedures are in place

2. **Phase 1 Implementation**
   - Implement schema sync module for improved developer experience
   - Train developers on the hybrid approach for schema management
   - Document proper workflow for schema changes

3. **Phase 2 Implementation**
   - Implement data management capabilities
   - Document and catalog reference and configuration data
   - Train team on proper data management procedures

4. **Phase 3 Implementation**
   - Enhance test data generation capabilities
   - Develop scenario-based test data for specific testing requirements
   - Automate test data refresh procedures

5. **Phase 4 Implementation**
   - Implement data governance capabilities
   - Document sensitive data handling procedures
   - Train team on healthcare-specific data requirements

## Conclusion

This comprehensive strategy for database schema and data management provides a robust framework for the SkinSpire Hospital Management System. By implementing these capabilities in phases, the team can gradually enhance the system while maintaining day-to-day operations.

The hybrid approach to schema management balances developer productivity with proper control, while the structured approach to data management ensures consistency across environments while respecting healthcare data governance requirements.

By following this strategy, the SkinSpire database management system will provide a solid foundation for ongoing development and operational excellence.