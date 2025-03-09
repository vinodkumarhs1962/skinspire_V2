#!/usr/bin/env python
# skinspire_v2/scripts/manage_db.py
# python scripts/manage_db.py apply-triggers
# python scripts/manage_db.py apply-all-schema-triggers

import os
import sys
import click
from flask.cli import with_appcontext
from sqlalchemy import text
from pathlib import Path

# Add project root to Python path - using absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Debug imports
print(f"Python path: {sys.path}")
print(f"Looking for app module in: {project_root}")
print(f"Files in directory: {os.listdir(project_root)}")

# Optional: Check if app directory exists
app_dir = os.path.join(project_root, 'app')
if os.path.exists(app_dir):
    print(f"app directory exists at: {app_dir}")
    print(f"Files in app directory: {os.listdir(app_dir)}")
else:
    print(f"app directory does not exist at expected location: {app_dir}")
    sys.exit(1)

try:
    from app import create_app, db
    print("Successfully imported app module")
except ImportError as e:
    print(f"Error importing app module: {e}")
    sys.exit(1)

# Global app instance
_app = None

def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app

def get_db():
    return db

@click.group()
def cli():
    """Database management commands"""
    pass

@cli.command()
@with_appcontext
def apply_base_triggers():
    """Apply only base database trigger functionality (without table-specific triggers)"""
    app = get_app()
    click.echo('Starting to apply base trigger functions...')
    
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            # Read functions.sql
            sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = Path(__file__).parent.parent / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    raise click.ClickException(f'functions.sql not found')
                
            click.echo(f'✓ Found functions.sql at {sql_path}')
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Extract only base functions (before Authentication Triggers section)
            base_sections = []
            current_section = []
            for line in sql_content.split('\n'):
                if "Authentication Triggers" in line:
                    break
                current_section.append(line)
            
            base_sql = '\n'.join(current_section)
            
            # Apply only base functions
            click.echo('Creating base database functions...')
            db.session.execute(text(base_sql))
            db.session.commit()
            
            # Apply basic trigger functions to all tables
            click.echo('Applying triggers to existing tables...')
            db.session.execute(text("SELECT create_audit_triggers('public')"))
            db.session.commit()
            
            click.echo('✓ Base trigger functions applied successfully')
            
        except Exception as e:
            db.session.rollback()
            click.echo(f'✗ Error applying base database functions: {str(e)}')
            raise

@cli.command()
@with_appcontext
def apply_triggers():
    """Apply all database triggers and functions - handles missing tables gracefully"""
    app = get_app()
    click.echo('Starting to apply database triggers and functions...')
    
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            # Read functions.sql
            sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = Path(__file__).parent.parent / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    raise click.ClickException(f'functions.sql not found')
            
            click.echo(f'✓ Found functions.sql at {sql_path}')
            with open(sql_path, 'r') as f:
                sql = f.read()
            
            # Check if required tables exist
            tables_exist = True
            try:
                # Try to query login_history table
                db.session.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'login_history'"))
                login_history_exists = db.session.scalar() == 1
                
                # Try to query user_sessions table
                db.session.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name = 'user_sessions'"))
                user_sessions_exists = db.session.scalar() == 1
                
                tables_exist = login_history_exists and user_sessions_exists
            except Exception:
                tables_exist = False
            
            if not tables_exist:
                click.echo("⚠️ Required tables don't exist yet - applying only base trigger functions")
                ctx = click.get_current_context()
                ctx.invoke(apply_base_triggers)
                return
            
            # All tables exist, try to apply full SQL
            try:
                click.echo('Applying all database functions and triggers...')
                
                # Split SQL into statements and execute each separately
                statements = []
                current_statement = []
                
                # Simple SQL parser to split on semicolons that aren't in functions
                in_function = False
                for line in sql.split('\n'):
                    # Check if we're entering/exiting a function body
                    if '$$' in line:
                        in_function = not in_function
                    
                    # Add line to current statement
                    current_statement.append(line)
                    
                    # If semicolon outside function, end statement
                    if ';' in line and not in_function:
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                
                # Execute each statement separately for better error handling
                for i, stmt in enumerate(statements):
                    if not stmt.strip():
                        continue
                    
                    try:
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        click.echo(f"⚠️ Error in statement {i+1}: {str(e)}")
                        
                        # Continue with other statements
                        continue
                
                click.echo('✓ Database functions and triggers applied successfully')
                
            except Exception as e:
                db.session.rollback()
                click.echo(f'✗ Error applying full SQL: {str(e)}')
                
                # Fall back to base triggers
                click.echo("Falling back to base trigger functions only")
                ctx = click.get_current_context()
                ctx.invoke(apply_base_triggers)
                
        except Exception as e:
            db.session.rollback()
            click.echo(f'✗ Error applying database functions: {str(e)}')
            raise


@cli.command()
@with_appcontext
def apply_all_schema_triggers():
    """Apply base database trigger functionality to all schemas"""
    app = get_app()
    click.echo('Starting to apply triggers to all schemas...')
    
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            # First, make sure the base trigger functions are created
            click.echo('Ensuring base trigger functions exist...')
            
            # Read functions.sql to ensure functions exist
            sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = Path(__file__).parent.parent / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    raise click.ClickException(f'functions.sql not found')
                
            click.echo(f'✓ Found functions.sql at {sql_path}')
            
            # Read the file and extract just the base functions
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Extract only base functions (before Authentication Triggers section)
            base_sections = []
            current_section = []
            for line in sql_content.split('\n'):
                if "Authentication Triggers" in line:
                    break
                current_section.append(line)
            
            base_sql = '\n'.join(current_section)
            
            # Apply base functions first
            click.echo('Creating base database functions...')
            db.session.execute(text(base_sql))
            db.session.commit()
            
            # Then define the multi-schema function
            click.echo('Creating multi-schema function...')
            
            multi_schema_function = """
            -- Function to apply triggers to all schemas
            CREATE OR REPLACE FUNCTION create_audit_triggers_all_schemas()
            RETURNS void AS $$
            DECLARE
                schema_record RECORD;
                schema_count INTEGER := 0;
                table_count INTEGER := 0;
                trigger_count INTEGER := 0;
            BEGIN
                -- Loop through all schemas (excluding system schemas)
                FOR schema_record IN 
                    SELECT nspname AS schema_name
                    FROM pg_namespace
                    WHERE nspname NOT LIKE 'pg_%' 
                      AND nspname != 'information_schema'
                LOOP
                    -- Log which schema we're processing
                    RAISE NOTICE 'Processing schema: %', schema_record.schema_name;
                    schema_count := schema_count + 1;
                    
                    -- Count tables in this schema before processing
                    SELECT COUNT(*) INTO table_count 
                    FROM pg_tables 
                    WHERE schemaname = schema_record.schema_name;
                    
                    RAISE NOTICE 'Found % tables in schema %', table_count, schema_record.schema_name;
                    
                    -- Apply triggers to all tables in this schema
                    PERFORM create_audit_triggers(schema_record.schema_name);
                    
                    -- Count triggers created (just the base audit triggers)
                    SELECT COUNT(*) INTO trigger_count
                    FROM information_schema.triggers
                    WHERE trigger_schema = schema_record.schema_name
                      AND (trigger_name = 'update_timestamp' OR trigger_name = 'track_user_changes');
                    
                    RAISE NOTICE 'Created/verified % triggers in schema %', trigger_count, schema_record.schema_name;
                END LOOP;
                
                RAISE NOTICE 'Processed % schemas in total', schema_count;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # Setting message level to NOTICE to see the detailed logs
            db.session.execute(text("SET client_min_messages TO NOTICE"))
            
            # Create the function in the database
            db.session.execute(text(multi_schema_function))
            db.session.commit()
            
            click.echo('Function created successfully')
            
            # Now call the function to apply triggers to all schemas
            click.echo('Applying triggers to all schemas...')
            db.session.execute(text("SELECT create_audit_triggers_all_schemas()"))
            db.session.commit()
            
            click.echo('✓ Applied triggers to all schemas successfully')
            
        except Exception as e:
            db.session.rollback()
            click.echo(f'✗ Error applying triggers to all schemas: {str(e)}')
            raise

@cli.command()
@with_appcontext
def drop_all_tables():
    """Drop all tables in correct order"""
    app = get_app()
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            # Drop tables in correct order
            sql = """
            DO $$ 
            BEGIN
                -- Disable triggers temporarily
                SET CONSTRAINTS ALL DEFERRED;
                
                -- Drop tables in order
                DROP TABLE IF EXISTS staff CASCADE;
                DROP TABLE IF EXISTS branches CASCADE;
                DROP TABLE IF EXISTS login_history CASCADE;
                DROP TABLE IF EXISTS user_sessions CASCADE;
                DROP TABLE IF EXISTS user_role_mapping CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS hospitals CASCADE;
                DROP TABLE IF EXISTS role_master CASCADE;
                DROP TABLE IF EXISTS module_master CASCADE;
                DROP TABLE IF EXISTS parameter_settings CASCADE;
                DROP TABLE IF EXISTS role_module_access CASCADE;
                DROP TABLE IF EXISTS patients CASCADE;
                
                -- Add any other tables that need to be dropped
                
                -- Re-enable triggers
                SET CONSTRAINTS ALL IMMEDIATE;
            END $$;
            """
            db.session.execute(text(sql))
            db.session.commit()
            click.echo('✓ All tables dropped successfully')
        except Exception as e:
            db.session.rollback()
            click.echo(f'✗ Error dropping tables: {str(e)}')
            raise

@cli.command()
@with_appcontext
def check_db():
    """Comprehensive database connection check"""
    app = get_app()
    click.echo('Starting database checks...')
    
    # 1. Check database URL
    click.echo(f'\nDatabase URL: {app.config["SQLALCHEMY_DATABASE_URI"]}')
    
    # 2. Test connection
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            conn = db.engine.connect()
            click.echo('✓ Database connection successful!')
            
            # 3. Test query
            result = db.session.execute(text('SELECT 1'))
            value = result.scalar()
            click.echo(f'✓ Test query successful (result: {value})')
            
            # 4. Check if we can create a test table
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS _test_table (
                    id SERIAL PRIMARY KEY,
                    test_column VARCHAR(50)
                )
            '''))
            click.echo('✓ Table creation test successful')
            
            # 5. Clean up test table
            db.session.execute(text('DROP TABLE IF EXISTS _test_table'))
            db.session.commit()
            click.echo('✓ Clean-up successful')
            
            conn.close()
            click.echo('\nAll database checks passed successfully!')
            
        except Exception as e:
            click.echo(f'\n✗ Database check failed: {str(e)}')
            db.session.rollback()
            raise click.ClickException('Database checks failed')

@cli.command()
@with_appcontext
def reset_db():
    """Remove existing migrations and reinitialize"""
    click.echo('Starting database reset...')
    
    # First check database connection
    ctx = click.get_current_context()
    ctx.invoke(check_db)
    
    # Drop all tables first
    ctx.invoke(drop_all_tables)
    
    # Remove existing migrations
    if os.path.exists('migrations'):
        import shutil
        shutil.rmtree('migrations')
        click.echo('✓ Removed existing migrations directory')
    
    # Initialize migrations
    if os.system('flask db init') == 0:
        click.echo('✓ Initialized new migrations directory')
    else:
        raise click.ClickException('Failed to initialize migrations')
    
    # Create migration
    if os.system('flask db migrate -m "initial migration"') == 0:
        click.echo('✓ Created initial migration')
    else:
        raise click.ClickException('Failed to create migration')
    
    # Apply migration
    if os.system('flask db upgrade') == 0:
        click.echo('✓ Applied migrations to database')
    else:
        raise click.ClickException('Failed to apply migrations')
    
    click.echo('\nDatabase reset completed successfully!')

@cli.command()
@with_appcontext
def init_db():
    """Initialize database tables without migrations"""
    click.echo('Starting database initialization...')
    
    # First check database connection
    ctx = click.get_current_context()
    ctx.invoke(check_db)
    
    app = get_app()
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            db.create_all()
            click.echo('✓ Created all database tables')
            click.echo('\nDatabase initialization completed successfully!')
        except Exception as e:
            click.echo(f'\n✗ Database initialization failed: {str(e)}')
            raise click.ClickException('Failed to initialize database')

@cli.command()
@with_appcontext
def show_config():
    """Show current database configuration"""
    app = get_app()
    click.echo('\nDatabase Configuration:')
    click.echo('-' * 50)
    for key, value in app.config.items():
        if 'DATABASE' in key or 'SQL' in key:
            click.echo(f'{key}: {value}')
    click.echo('-' * 50)

@cli.command()
@with_appcontext
def reset_and_init():
    """Reset database (drop all tables) and reinitialize with create_database.py"""
    import subprocess
    
    click.echo('Starting database reset and initialization...')
    
    # First check database connection
    ctx = click.get_current_context()
    ctx.invoke(check_db)
    
    # Drop all tables first
    click.echo('\nDropping all existing tables...')
    ctx.invoke(drop_all_tables)
    
    # Initialize empty tables using SQLAlchemy models
    click.echo('\nCreating empty tables from models...')
    ctx.invoke(init_db)
    
    # Apply triggers
    click.echo('\nApplying database triggers...')
    ctx.invoke(apply_triggers)
    
    # Run create_database.py script to initialize data
    click.echo('\nInitializing database with data...')
    create_db_script = Path(__file__).parent.parent / "scripts" / "create_database.py"
    
    try:
        # Use subprocess to run the create_database.py script
        result = subprocess.run(
            ["python", str(create_db_script)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Output from create_database.py
        click.echo("Output from create_database.py:")
        for line in result.stdout.splitlines():
            click.echo(f"  {line}")
        
        click.echo('\nDatabase reset and initialization completed successfully!')
        
    except subprocess.CalledProcessError as e:
        click.echo(f'\n✗ Error running create_database.py: {e.stderr}')
        raise click.ClickException('Failed to initialize database with data')

if __name__ == '__main__':
    cli()