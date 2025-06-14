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
            changes.append(f"New table: {table_name}")
        
        # Check columns in model but not in database
        for table_name in model_tables.intersection(db_tables):
            model_table = model_metadata.tables[table_name]
            db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
            
            # Check for new columns
            for column in model_table.columns:
                if column.name not in db_columns:
                    changes.append(f"New column: {table_name}.{column.name}")
        
        # Return results
        return {
            'has_changes': len(changes) > 0,
            'changes': changes
        }
    
    except Exception as e:
        logger.error(f"Error detecting schema changes: {str(e)}")
        logger.debug(traceback.format_exc())
        return {
            'has_changes': False,
            'changes': [],
            'error': str(e)
        }

def generate_migration_script(changes: Dict[str, Any], message: str) -> Tuple[bool, Optional[str]]:
    """
    Generate a migration script from detected changes
    
    Args:
        changes: Dict with detected changes
        message: Migration message
        
    Returns:
        Tuple of (success, script_content)
    """
    try:
        # Generate a migration ID
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        revision = uuid.uuid4().hex[:8]
        
        # Create script content
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
        
        # Process detected changes
        from app.models import Base
        
        # Extract missing tables from changes
        missing_tables = set()
        missing_columns = []
        
        for change in changes.get('changes', []):
            if change.startswith('New table:'):
                table_name = change.split(':', 1)[1].strip()
                missing_tables.add(table_name)
            elif change.startswith('New column:'):
                col_info = change.split(':', 1)[1].strip()
                table_name, col_name = col_info.split('.', 1)
                missing_columns.append((table_name, col_name))
        
        # Get SQLAlchemy metadata
        metadata = Base.metadata
        
        # Add table creation statements
        for table_name in missing_tables:
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
                
                script_content += f"    # Create table {table_name}\n"
                script_content += f"    op.create_table(\n"
                script_content += f"        '{table_name}',\n"
                
                # Add columns
                for column in table.columns:
                    # Format column type
                    col_type = str(column.type)
                    if 'TIMESTAMP' in col_type and 'timezone=True' in str(column):
                        col_type = "sa.DateTime(timezone=True)"
                    elif 'VARCHAR' in col_type:
                        # Get length from column type
                        length = getattr(column.type, 'length', 50)
                        col_type = f"sa.String({length})"
                    elif 'UUID' in col_type:
                        col_type = "sa.UUID()"
                    elif 'TEXT' in col_type:
                        col_type = "sa.Text()"
                    elif 'BOOLEAN' in col_type:
                        col_type = "sa.Boolean()"
                    elif 'INTEGER' in col_type:
                        col_type = "sa.Integer()"
                    elif 'JSONB' in col_type:
                        col_type = "postgresql.JSONB()"
                    
                    # Format nullable and defaults
                    nullable = "nullable=False" if not column.nullable else "nullable=True"
                    default = f", server_default=sa.text('{column.server_default.arg}')" if column.server_default else ""
                    
                    # Add to script
                    script_content += f"        sa.Column('{column.name}', {col_type}, {nullable}{default}),\n"
                
                # Add primary key
                pk_cols = [col.name for col in table.primary_key.columns]
                if pk_cols:
                    pk_str = ", ".join([f"'{col}'" for col in pk_cols])
                    script_content += f"        sa.PrimaryKeyConstraint({pk_str}),\n"
                
                # Add foreign keys
                for fk in table.foreign_keys:
                    target = f"{fk.column.table.name}.{fk.column.name}"
                    script_content += f"        sa.ForeignKeyConstraint(['{fk.parent.name}'], ['{target}']),\n"
                
                # Close table definition
                script_content = script_content.rstrip(",\n") + "\n    )\n\n"
        
        # Add column addition statements
        for table_name, col_name in missing_columns:
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
                column = next((c for c in table.columns if c.name == col_name), None)
                
                if column:
                    script_content += f"    # Add column {col_name} to {table_name}\n"
                    
                    # Format column type
                    col_type = str(column.type)
                    if 'TIMESTAMP' in col_type and 'timezone=True' in str(column):
                        col_type = "sa.DateTime(timezone=True)"
                    elif 'VARCHAR' in col_type:
                        # Get length from column type
                        length = getattr(column.type, 'length', 50)
                        col_type = f"sa.String({length})"
                    elif 'UUID' in col_type:
                        col_type = "sa.UUID()"
                    elif 'TEXT' in col_type:
                        col_type = "sa.Text()"
                    elif 'BOOLEAN' in col_type:
                        col_type = "sa.Boolean()"
                    elif 'INTEGER' in col_type:
                        col_type = "sa.Integer()"
                    elif 'JSONB' in col_type:
                        col_type = "postgresql.JSONB()"
                    
                    # Format nullable and defaults
                    nullable = "nullable=False" if not column.nullable else "nullable=True"
                    default = f", server_default=sa.text('{column.server_default.arg}')" if column.server_default else ""
                    
                    # Add to script
                    script_content += f"    op.add_column('{table_name}', sa.Column('{col_name}', {col_type}, {nullable}{default}))\n\n"
        
        # Add downgrade section
        script_content += """

def downgrade():
"""
        
        # Add table drop statements (in reverse order)
        for table_name in reversed(list(missing_tables)):
            script_content += f"    op.drop_table('{table_name}')\n"
        
        # Add column drop statements
        for table_name, col_name in missing_columns:
            script_content += f"    op.drop_column('{table_name}', '{col_name}')\n"
        
        return True, script_content
        
    except Exception as e:
        logger.error(f"Error generating migration script: {e}")
        import traceback
        traceback.print_exc()
        return False, None

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
        return _with_app_context(_sync_models)
    except ImportError:
        # Fallback if utils not available
        from app import create_app, db
        app = create_app()
        with app.app_context():
            return _sync_models(db)

def _sync_models(db):
    """Internal function to sync models with db instance"""
    try:
        # Get models and metadata
        from app.models import Base
        
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

# Add this line at the end of schema_sync.py
generate_migration_from_changes = generate_migration_script