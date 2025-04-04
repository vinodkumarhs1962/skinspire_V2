# app/core/db_operations/schema_sync.py

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from sqlalchemy import inspect, text
from sqlalchemy.schema import ForeignKeyConstraint, Index
from sqlalchemy.exc import SQLAlchemyError

from .utils import get_db_config, logger, project_root, _with_app_context
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
                if not table_name.startswith(('pg_', 'sql_')):  # Skip system tables
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
            
            # Check indexes
            for table_name in model_tables.intersection(db_tables):
                model_table = model_metadata.tables[table_name]
                db_indexes = {idx['name']: idx for idx in inspector.get_indexes(table_name)}
                
                # Check for new indexes
                for idx in model_table.indexes:
                    if idx.name not in db_indexes:
                        changes.append(f"New index: {idx.name} on {table_name}")
            
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
    model_type = str(model_column.type).lower()
    db_type = str(db_column['type']).lower()
    
    # Basic type equivalence checking
    if 'int' in model_type and 'int' in db_type:
        return True
    if 'varchar' in model_type and 'varchar' in db_type:
        return True
    if 'text' in model_type and 'text' in db_type:
        return True
    if 'bool' in model_type and 'bool' in db_type:
        return True
    if 'timestamp' in model_type and 'timestamp' in db_type:
        return True
    if 'date' in model_type and 'date' in db_type:
        return True
    if 'json' in model_type and 'json' in db_type:
        return True
    if 'float' in model_type and 'float' in db_type:
        return True
    
    # For exact matching
    return model_type == db_type

def generate_migration_from_changes(message: str, env: str) -> bool:
    """
    Generate migration file from detected changes
    
    Args:
        message: Migration message
        env: Environment name
        
    Returns:
        True if successful, False otherwise
    """
    # This integrates with the existing migration.py module
    from .migration import create_migration
    
    # Create a migration
    success, migration_file = create_migration(message, env)
    
    return success