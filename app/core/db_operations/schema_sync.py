# app/core/db_operations/schema_sync.py

import logging
import traceback
from datetime import datetime
import uuid
import re
from sqlalchemy import inspect, MetaData, text
from typing import Dict, List, Any, Tuple, Set, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# Import utils (adjust path as needed)
try:
    from .utils import get_db_config, logger, project_root
except ImportError:
    # Fallback if utils module not available
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent  # Adjust as needed

def detect_model_changes():
    """
    Detect differences between models and current database schema
    
    Returns:
        Dictionary with detected changes
    """
    # Use _with_app_context if available, otherwise use direct app context
    try:
        from .utils import _with_app_context
        return _with_app_context(_detect_changes)
    except ImportError:
        # Fallback if utils not available
        from app import create_app, db
        app = create_app()
        with app.app_context():
            return _detect_changes(db)

def _detect_changes(db):
    """Internal function to detect changes with db instance"""
    try:
        # Import models
        from app.models import Base
        
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
            changes.append({
                'type': 'add_table',
                'table': table_name,
                'details': 'New table'
            })
        
        # Tables in database but not in model (possible drops)
        # These are detected but not automatically executed
        removed_tables = db_tables - model_tables
        for table_name in removed_tables:
            # Skip internal PostgreSQL tables
            if table_name.startswith('pg_') or table_name.startswith('sql_'):
                continue
            
            changes.append({
                'type': 'remove_table',
                'table': table_name,
                'details': 'Table removed from models',
                'auto_apply': False  # Flag to indicate this won't be auto-applied
            })
        
        # Check columns in existing tables
        for table_name in model_tables.intersection(db_tables):
            model_table = model_metadata.tables[table_name]
            db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
            model_column_names = set(c.name for c in model_table.columns)
            db_column_names = set(db_columns.keys())
            
            # New columns
            for col_name in model_column_names - db_column_names:
                column = model_table.columns[col_name]
                changes.append({
                    'type': 'add_column',
                    'table': table_name,
                    'column': col_name,
                    'details': f"New column: {str(column.type)}"
                })
            
            # Columns in database but not in model (possible drops)
            # These are detected but not automatically executed
            for col_name in db_column_names - model_column_names:
                changes.append({
                    'type': 'remove_column',
                    'table': table_name,
                    'column': col_name,
                    'details': 'Column removed from model',
                    'auto_apply': False  # Flag to indicate this won't be auto-applied
                })
            
            # Modified columns
            for col_name in model_column_names.intersection(db_column_names):
                model_col = model_table.columns[col_name]
                db_col = db_columns[col_name]
                
                # Check type changes
                model_type = model_col.type
                db_type = db_col['type']
                
                if not types_are_equivalent(model_type, db_type):
                    changes.append({
                        'type': 'alter_column_type',
                        'table': table_name,
                        'column': col_name,
                        'details': f"Type change: {db_type} -> {model_type}"
                    })
                
                # Check nullable constraint
                if model_col.nullable != db_col['nullable']:
                    new_state = "NULL" if model_col.nullable else "NOT NULL"
                    changes.append({
                        'type': 'alter_column_nullable',
                        'table': table_name,
                        'column': col_name,
                        'details': f"Nullable change: {new_state}"
                    })
                
                # Check default value
                model_default = model_col.server_default.arg if model_col.server_default else None
                db_default = db_col.get('default')
                
                if model_default != db_default and not (model_default is None and db_default is None):
                    changes.append({
                        'type': 'alter_column_default',
                        'table': table_name,
                        'column': col_name,
                        'details': f"Default change: {db_default} -> {model_default}"
                    })
        
        # For backward compatibility - convert new structured format to old format
        # This ensures existing code that uses the old format continues to work
        old_format_changes = []
        for change in changes:
            if change['type'] == 'add_table':
                old_format_changes.append(f"New table: {change['table']}")
            elif change['type'] == 'add_column':
                old_format_changes.append(f"New column: {change['table']}.{change['column']}")
            elif 'column' in change:
                # For column alterations, still include in the old format
                old_format_changes.append(f"{change['type']}: {change['table']}.{change['column']}")
            else:
                old_format_changes.append(f"{change['type']}: {change['table']}")
        
        return {
            'has_changes': len(changes) > 0,
            'changes': changes,
            'old_format_changes': old_format_changes  # For backward compatibility
        }
    
    except Exception as e:
        logger.error(f"Error detecting schema changes: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            'has_changes': False,
            'changes': [],
            'error': str(e)
        }

def types_are_equivalent(model_type, db_type):
    """
    Compare SQLAlchemy and database types for equivalence
    """
    # Convert types to strings for comparison
    model_type_str = str(model_type).lower()
    db_type_str = str(db_type).lower()
    
    # Handle common PostgreSQL type mappings
    if 'varchar' in model_type_str and 'character varying' in db_type_str:
        # Compare lengths if available
        model_length = getattr(model_type, 'length', None)
        db_length = None
        
        # Try to extract length from DB type string like "character varying(100)"
        import re
        length_match = re.search(r'\((\d+)\)', db_type_str)
        if length_match:
            db_length = int(length_match.group(1))
        
        return model_length == db_length
    
    # UUID comparison
    if 'uuid' in model_type_str and 'uuid' in db_type_str:
        return True
    
    # JSONB comparison
    if 'jsonb' in model_type_str and 'jsonb' in db_type_str:
        return True
    
    # Boolean comparison
    if 'boolean' in model_type_str and 'boolean' in db_type_str:
        return True
    
    # Integer comparison
    if 'integer' in model_type_str and 'integer' in db_type_str:
        return True
    
    # Text comparison
    if 'text' in model_type_str and 'text' in db_type_str:
        return True
    
    # Timestamp comparison
    if 'timestamp' in model_type_str and 'timestamp' in db_type_str:
        # Check timezone
        model_tz = 'timezone' in model_type_str
        db_tz = 'timezone' in db_type_str
        return model_tz == db_tz
    
    # For other types, do a simple string comparison
    # This could be enhanced for specific type comparisons
    model_base_type = model_type_str.split('(')[0].strip()
    db_base_type = db_type_str.split('(')[0].strip()
    
    return model_base_type == db_base_type

def generate_migration_script(changes, message):
    """
    Generate a detailed migration script from detected changes
    
    Args:
        changes: Dict with detailed detected changes
        message: Migration message
        
    Returns:
        Tuple of (success, script_content)
    """
    try:
        # Import SQLAlchemy components
        import sqlalchemy as sa
        from sqlalchemy.dialects import postgresql
        
        # Generate a migration ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        revision = uuid.uuid4().hex[:8]
        
        # Create script template
        script_content = f"""\"\"\"
{message}

Revision ID: {revision}
Revises: 
Create Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

\"\"\"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{revision}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
"""
        
        # Process detected changes - handle both old and new format
        from app.models import Base
        metadata = Base.metadata
        
        # Check if using old format or new format
        changes_list = []
        if 'changes' in changes:
            if isinstance(changes['changes'], list):
                if len(changes['changes']) > 0:
                    if isinstance(changes['changes'][0], str):
                        # Old format - convert to new format
                        for change in changes['changes']:
                            if change.startswith('New table:'):
                                table_name = change.split(':', 1)[1].strip()
                                changes_list.append({
                                    'type': 'add_table',
                                    'table': table_name,
                                    'details': 'New table'
                                })
                            elif change.startswith('New column:'):
                                col_info = change.split(':', 1)[1].strip()
                                try:
                                    table_name, col_name = col_info.split('.', 1)
                                    changes_list.append({
                                        'type': 'add_column',
                                        'table': table_name,
                                        'column': col_name,
                                        'details': f"New column"
                                    })
                                except ValueError:
                                    # Malformed column info, just skip this one
                                    pass
                    else:
                        # New format
                        changes_list = changes['changes']
            else:
                # Empty or invalid changes
                changes_list = []
        else:
            # Invalid structure
            changes_list = []   
        
        # Group changes by table for better organization
        tables_changes = {}
        for change in changes_list:
            # Skip changes marked as not auto-applicable
            if change.get('auto_apply') is False:
                continue
                
            table = change['table']
            if table not in tables_changes:
                tables_changes[table] = []
            tables_changes[table].append(change)
        
        # Process table additions first
        for table, table_changes in tables_changes.items():
            # Find table creation
            table_adds = [c for c in table_changes if c['type'] == 'add_table']
            if table_adds:
                script_content += f"\n    # Create table {table}\n"
                script_content += generate_create_table_script(table, metadata)
        
        # Process column changes for existing tables
        for table, table_changes in tables_changes.items():
            column_changes = [c for c in table_changes if c['type'] != 'add_table']
            
            if column_changes:
                script_content += f"\n    # Modify table {table}\n"
                
                # Add columns
                for change in [c for c in column_changes if c['type'] == 'add_column']:
                    script_content += generate_add_column_script(table, change['column'], metadata)
                
                # Alter column types
                for change in [c for c in column_changes if c['type'] == 'alter_column_type']:
                    script_content += generate_alter_column_type_script(table, change['column'], metadata)
                
                # Alter nullable constraints
                for change in [c for c in column_changes if c['type'] == 'alter_column_nullable']:
                    script_content += generate_alter_column_nullable_script(table, change['column'], metadata)
                
                # Alter default values
                for change in [c for c in column_changes if c['type'] == 'alter_column_default']:
                    script_content += generate_alter_column_default_script(table, change['column'], metadata)
        
        script_content += "\n    # ### end commands ###\n"
        
        # Add downgrade section with reverse operations - Replace the problematic downgrade section in generate_migration_script function

        script_content += (
            "\n\ndef downgrade():\n"
            "    \"\"\"Downgrade database to previous revision\"\"\"\n"
            "    # ### commands auto-generated for downgrade ###\n"
        )
        
        # Process in reverse order for downgrade
        for table, table_changes in reversed(list(tables_changes.items())):
            # Drop tables
            table_adds = [c for c in table_changes if c['type'] == 'add_table']
            if table_adds:
                script_content += f"    op.drop_table('{table}')\n"
            
            # Revert column changes
            column_changes = [c for c in table_changes if c['type'] != 'add_table']
            for change in column_changes:
                if change['type'] == 'add_column':
                    script_content += f"    op.drop_column('{table}', '{change['column']}')\n"
                elif change['type'] == 'alter_column_type':
                    # For datetime changes, handle timezone conversion
                    if "datetime" in change['details'].lower() or "timestamp" in change['details'].lower():
                        # Determine original type based on the change details
                        if "->" in change['details']:
                            parts = change['details'].split("->")
                            old_type = parts[0].strip().lower()
                            
                            # Default to non-timezone aware
                            if "timestamptz" in old_type or "timezone=true" in old_type:
                                script_content += f"    op.alter_column('{table}', '{change['column']}', type_=sa.DateTime(timezone=True), postgresql_using=\"{change['column']}::timestamptz\")\n"
                            else:
                                script_content += f"    op.alter_column('{table}', '{change['column']}', type_=sa.DateTime(timezone=False), postgresql_using=\"{change['column']}::timestamp\")\n"
                        else:
                            # Fallback when we can't determine original type
                            script_content += f"    # Revert type change for {table}.{change['column']}\n"
                            script_content += f"    # op.alter_column('{table}', '{change['column']}', type_=sa.DateTime(timezone=False))\n"
                    # Handle float to numeric conversion
                    elif "float" in change['details'].lower() and "double precision" in change['details'].lower():
                        script_content += f"    op.alter_column('{table}', '{change['column']}', type_=sa.Numeric(precision=10, scale=2))\n"
                    # For other types, provide a commented example
                    else:
                        script_content += f"    # Revert type change for {table}.{change['column']}\n"
                        script_content += f"    # Please specify appropriate type for downgrade\n"
                elif change['type'] == 'alter_column_nullable':
                    # Get the opposite of the current state
                    if "NULL" in change['details']:
                        script_content += f"    op.alter_column('{table}', '{change['column']}', nullable=False)\n"
                    else:
                        script_content += f"    op.alter_column('{table}', '{change['column']}', nullable=True)\n"
                elif change['type'] == 'alter_column_default':
                    script_content += f"    op.alter_column('{table}', '{change['column']}', server_default=None)\n"

        script_content += "    # ### end commands ###"
        return True, script_content
    except Exception as e:
        logger.error(f"Error generating migration script: {e}")
        return False, None
         
def generate_create_table_script(table_name, metadata):
    """Generate Alembic script for creating a table"""
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    
    if table_name not in metadata.tables:
        return f"    # Error: Table {table_name} not found in metadata\n"
    
    table = metadata.tables[table_name]
    
    script = f"    op.create_table(\n"
    script += f"        '{table_name}',\n"
    
    # Add columns
    for column in table.columns:
        col_type = get_column_type_script(column)
        nullable = "nullable=True" if column.nullable else "nullable=False"
        default = f", server_default=sa.text('{column.server_default.arg}')" if column.server_default else ""
        pk = ", primary_key=True" if column.primary_key else ""
        
        script += f"        sa.Column('{column.name}', {col_type}, {nullable}{default}{pk}),\n"
    
    script += "    )\n"
    
    # Add indices
    for index in table.indexes:
        cols = ", ".join([f"'{c.name}'" for c in index.columns])
        unique = ", unique=True" if index.unique else ""
        script += f"    op.create_index('{index.name}', '{table_name}', [{cols}]{unique})\n"
    
    return script

def generate_add_column_script(table_name, column_name, metadata):
    """Generate Alembic script for adding a column"""
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    
    if table_name not in metadata.tables:
        return f"    # Error: Table {table_name} not found in metadata\n"
    
    table = metadata.tables[table_name]
    if column_name not in table.columns:
        return f"    # Error: Column {column_name} not found in table {table_name}\n"
    
    column = table.columns[column_name]
    col_type = get_column_type_script(column)
    nullable = "nullable=True" if column.nullable else "nullable=False"
    default = f", server_default=sa.text('{column.server_default.arg}')" if column.server_default else ""
    
    return f"    op.add_column('{table_name}', sa.Column('{column_name}', {col_type}, {nullable}{default}))\n"

def generate_alter_column_type_script(table_name, column_name, metadata):
    """Generate Alembic script for altering column type with improved PostgreSQL type handling"""
    if table_name not in metadata.tables:
        return f"    # Error: Table {table_name} not found in metadata\n"
    
    table = metadata.tables[table_name]
    if column_name not in table.columns:
        return f"    # Error: Column {column_name} not found in table {table_name}\n"
    
    column = table.columns[column_name]
    col_type = get_column_type_script(column)
    
    # Special handling for DateTime with timezone
    if "DateTime" in col_type:
        # Check if timezone parameter is specified
        if "timezone=True" in col_type:
            # For PostgreSQL, use USING clause for timestamptz conversion
            return f"    op.alter_column('{table_name}', '{column_name}', type_={col_type}, postgresql_using=\"{column_name}::timestamptz\")\n"
        elif "timezone=False" in col_type:
            # For conversion to non-timezone timestamp
            return f"    op.alter_column('{table_name}', '{column_name}', type_={col_type}, postgresql_using=\"{column_name}::timestamp\")\n"
    
    # For all other types, use standard alter column
    return f"    op.alter_column('{table_name}', '{column_name}', type_={col_type})\n"

def generate_alter_column_nullable_script(table_name, column_name, metadata):
    """Generate Alembic script for altering column nullable constraint"""
    if table_name not in metadata.tables:
        return f"    # Error: Table {table_name} not found in metadata\n"
    
    table = metadata.tables[table_name]
    if column_name not in table.columns:
        return f"    # Error: Column {column_name} not found in table {table_name}\n"
    
    column = table.columns[column_name]
    nullable = column.nullable
    
    return f"    op.alter_column('{table_name}', '{column_name}', nullable={nullable})\n"

def generate_alter_column_default_script(table_name, column_name, metadata):
    """Generate Alembic script for altering column default value"""
    if table_name not in metadata.tables:
        return f"    # Error: Table {table_name} not found in metadata\n"
    
    table = metadata.tables[table_name]
    if column_name not in table.columns:
        return f"    # Error: Column {column_name} not found in table {table_name}\n"
    
    column = table.columns[column_name]
    
    if column.server_default:
        return f"    op.alter_column('{table_name}', '{column_name}', server_default=sa.text('{column.server_default.arg}'))\n"
    else:
        return f"    op.alter_column('{table_name}', '{column_name}', server_default=None)\n"

def get_column_type_script(column):
    """Convert SQLAlchemy column type to appropriate script representation"""
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    
    col_type = column.type
    
    # Handle different column types
    if isinstance(col_type, sa.String):
        return f"sa.String({col_type.length})"
    elif isinstance(col_type, sa.Integer):
        return "sa.Integer()"
    elif isinstance(col_type, sa.Boolean):
        return "sa.Boolean()"
    elif isinstance(col_type, sa.Text):
        return "sa.Text()"
    elif isinstance(col_type, sa.DateTime):
        timezone = getattr(col_type, 'timezone', False)
        return f"sa.DateTime(timezone={timezone})"
    elif isinstance(col_type, sa.Float):
        return "sa.Float()"
    elif isinstance(col_type, postgresql.UUID):
        as_uuid = getattr(col_type, 'as_uuid', False)
        return f"postgresql.UUID(as_uuid={as_uuid})"
    elif isinstance(col_type, postgresql.JSONB):
        return "postgresql.JSONB()"
    else:
        # Default fallback - may need to be expanded
        return f"sa.{col_type.__class__.__name__}()"

def save_migration_script(script_content: str, message: str) -> Tuple[bool, Optional[Path]]:
    """
    Save migration script to a file
    
    Args:
        script_content: Migration script content
        message: Migration message
        
    Returns:
        Tuple of (success, file_path)
    """
    try:
        # Create directory if it doesn't exist
        migrations_dir = project_root / 'migrations' / 'versions'
        migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure __init__.py exists
        init_file = migrations_dir / '__init__.py'
        if not init_file.exists():
            with open(init_file, 'w') as f:
                f.write('')
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Extract revision from script_content
        revision_match = re.search(r"revision = '([a-f0-9]+)'", script_content)
        revision = revision_match.group(1) if revision_match else uuid.uuid4().hex[:8]
        
        filename = f"{timestamp}_{revision}_{message.lower().replace(' ', '_')}.py"
        
        # Write file
        file_path = migrations_dir / filename
        with open(file_path, 'w') as f:
            f.write(script_content)
            
        logger.info(f"Created migration file: {file_path}")
        return True, file_path
        
    except Exception as e:
        logger.error(f"Error saving migration script: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def create_model_based_migration(message: str, env: str) -> Tuple[bool, Optional[Path]]:
    """
    Create and save a migration script based on model changes
    
    Args:
        message: Migration message
        env: Environment name
        
    Returns:
        Tuple of (success, file_path)
    """
    # Detect changes
    changes = detect_model_changes()
    
    # Check if there are any changes
    if not changes.get('has_changes', False):
        logger.info("No schema changes detected")
        return True, None
    
    # Generate migration script
    success, script_content = generate_migration_script(changes, message)
    if not success or not script_content:
        logger.error("Failed to generate migration script")
        return False, None
    
    # Save migration script
    return save_migration_script(script_content, message)

def sync_models_to_schema(env: str, backup: bool = True, allow_drops: bool = False) -> bool:
    """
    Sync models directly to database schema for development
    
    Args:
        env: Target environment
        backup: Whether to create backup before sync
        allow_drops: Whether to allow dropping tables/columns that aren't in the models
        
    Returns:
        True if successful, False otherwise
    """
    # Only allow in development
    if env not in ('development', 'dev'):
        logger.error("Schema sync only allowed in development environment")
        return False
    
    if backup:
        # Create backup first
        try:
            from .backup import backup_database
            success, _ = backup_database(env)
            if not success:
                logger.warning("Failed to create backup before sync")
        except ImportError:
            logger.warning("Backup module not available")
    
    # Use _with_app_context if available, otherwise use direct app context
    try:
        from .utils import _with_app_context
        return _with_app_context(lambda db: _sync_models(db, allow_drops))
    except ImportError:
        # Fallback if utils not available
        from app import create_app, db
        app = create_app()
        with app.app_context():
            return _sync_models(db, allow_drops)

def _sync_models(db, allow_drops: bool = False):
    """Internal function to sync models with db instance"""
    try:
        from app.models import Base
        from sqlalchemy import text
        import sqlalchemy as sa
        
        # Get changes to know what specifically to update
        changes = _detect_changes(db)
        
        # If no changes, return early
        if not changes.get('has_changes'):
            logger.info("No changes detected, skipping sync")
            return True
        
        # Get changes list - handle both old and new format
        changes_list = changes.get('changes', [])
        if changes_list and isinstance(changes_list[0], str):
            # Convert old format to new format
            new_format_changes = []
            for change in changes_list:
                if change.startswith('New table:'):
                    table_name = change.split(':', 1)[1].strip()
                    new_format_changes.append({
                        'type': 'add_table',
                        'table': table_name,
                        'details': 'New table'
                    })
                elif change.startswith('New column:'):
                    col_info = change.split(':', 1)[1].strip()
                    try:
                        table_name, col_name = col_info.split('.', 1)
                        new_format_changes.append({
                            'type': 'add_column',
                            'table': table_name,
                            'column': col_name,
                            'details': f"New column"
                        })
                    except ValueError:
                        # Malformed column info, skip this one
                        pass
            changes_list = new_format_changes
        
        # Begin transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        try:
            # Disable triggers and constraints temporarily
            connection.execute(text("SET session_replication_role = 'replica'"))
            
            # Group changes by table
            tables_to_create = set()
            tables_to_drop = set()
            column_changes = []
            
            for change in changes_list:
                if change['type'] == 'add_table':
                    tables_to_create.add(change['table'])
                elif change['type'] == 'remove_table' and allow_drops:
                    tables_to_drop.add(change['table'])
                else:
                    # Filter column drops if not allowed
                    if change['type'] == 'remove_column' and not allow_drops:
                        continue
                    column_changes.append(change)
            
            # Create new tables
            for table_name in tables_to_create:
                if table_name in Base.metadata.tables:
                    table = Base.metadata.tables[table_name]
                    table.create(connection, checkfirst=True)
                    logger.info(f"Created table {table_name}")
            
            # Apply column changes
            for change in column_changes:
                table_name = change['table']
                
                if change['type'] == 'add_column':
                    column_name = change['column']
                    
                    # Only process if table exists in models
                    if table_name not in Base.metadata.tables:
                        logger.warning(f"Table {table_name} doesn't exist in models, skipping column {column_name}")
                        continue
                    
                    if column_name not in Base.metadata.tables[table_name].columns:
                        logger.warning(f"Column {column_name} not found in table {table_name} model")
                        continue
                        
                    column = Base.metadata.tables[table_name].columns[column_name]
                    
                    # Generate SQL for adding column
                    column_type = column.type.compile(dialect=db.engine.dialect)
                    nullable = "" if column.nullable else "NOT NULL"
                    
                    # Handle default
                    default = ""
                    if column.server_default:
                        default = f"DEFAULT {column.server_default.arg}"
                    elif column.default is not None:
                        # Try to get Python default value
                        if hasattr(column.default, 'arg'):
                            default_val = column.default.arg
                            if default_val is not None:
                                if isinstance(default_val, bool):
                                    default = f"DEFAULT {'true' if default_val else 'false'}"
                                elif isinstance(default_val, (int, float)):
                                    default = f"DEFAULT {default_val}"
                                elif isinstance(default_val, str):
                                    default = f"DEFAULT '{default_val}'"
                    
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {nullable} {default}"
                    connection.execute(text(sql))
                    logger.info(f"Added column {table_name}.{column_name}")
                    
                elif change['type'] == 'alter_column_type':
                    column_name = change['column']
                    
                    # Only process if table exists in models
                    if table_name not in Base.metadata.tables:
                        logger.warning(f"Table {table_name} doesn't exist in models, skipping column {column_name}")
                        continue
                    
                    if column_name not in Base.metadata.tables[table_name].columns:
                        logger.warning(f"Column {column_name} not found in table {table_name} model")
                        continue
                        
                    column = Base.metadata.tables[table_name].columns[column_name]
                    
                    column_type = column.type.compile(dialect=db.engine.dialect)
                    sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {column_type} USING {column_name}::{column_type}"
                    connection.execute(text(sql))
                    logger.info(f"Altered type for {table_name}.{column_name}")
                    
                elif change['type'] == 'alter_column_nullable':
                    column_name = change['column']
                    
                    # Only process if table exists in models
                    if table_name not in Base.metadata.tables:
                        logger.warning(f"Table {table_name} doesn't exist in models, skipping column {column_name}")
                        continue
                        
                    if column_name not in Base.metadata.tables[table_name].columns:
                        logger.warning(f"Column {column_name} not found in table {table_name} model")
                        continue
                        
                    column = Base.metadata.tables[table_name].columns[column_name]
                    
                    if column.nullable:
                        sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP NOT NULL"
                    else:
                        sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET NOT NULL"
                    
                    connection.execute(text(sql))
                    logger.info(f"Modified nullable constraint for {table_name}.{column_name}")
                    
                elif change['type'] == 'alter_column_default':
                    column_name = change['column']
                    
                    # Only process if table exists in models
                    if table_name not in Base.metadata.tables:
                        logger.warning(f"Table {table_name} doesn't exist in models, skipping column {column_name}")
                        continue
                        
                    if column_name not in Base.metadata.tables[table_name].columns:
                        logger.warning(f"Column {column_name} not found in table {table_name} model")
                        continue
                        
                    column = Base.metadata.tables[table_name].columns[column_name]
                    
                    if column.server_default:
                        sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT {column.server_default.arg}"
                    else:
                        sql = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} DROP DEFAULT"
                    
                    connection.execute(text(sql))
                    logger.info(f"Modified default value for {table_name}.{column_name}")
                
                elif change['type'] == 'remove_column' and allow_drops:
                    column_name = change['column']
                    sql = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
                    connection.execute(text(sql))
                    logger.info(f"Dropped column {table_name}.{column_name}")
            
            # Drop tables (only if explicitly allowed)
            if allow_drops:
                for table_name in tables_to_drop:
                    sql = f"DROP TABLE IF EXISTS {table_name} CASCADE"
                    connection.execute(text(sql))
                    logger.info(f"Dropped table {table_name}")
            
            # Re-enable triggers and constraints
            connection.execute(text("SET session_replication_role = 'origin'"))
            
            # Commit transaction
            transaction.commit()
            logger.info("Model sync completed successfully")
            return True
            
        except Exception as e:
            # Rollback on error
            transaction.rollback()
            logger.error(f"Error executing schema changes: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
        finally:
            # Cleanup
            connection.close()
            
    except Exception as e:
        logger.error(f"Error syncing schema: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

# Function aliases for backward compatibility
generate_migration_from_changes = generate_migration_script
