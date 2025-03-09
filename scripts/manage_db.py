#!/usr/bin/env python
# skinspire_v2/scripts/manage_db.py
# python scripts/manage_db.py apply-triggers
# python scripts/manage_db.py apply-all-schema-triggers
# python scripts/manage_db.py verify-triggers

import os
import sys
import click
from flask.cli import with_appcontext
from sqlalchemy import text
from pathlib import Path
import subprocess

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
    """Apply all database triggers and functions with progressive fallbacks"""
    app = get_app()
    click.echo('Starting to apply database triggers and functions...')
    
    with app.app_context():
        try:
            # Get db from the app context
            db = get_db()
            
            # Step 1: Try to find functions.sql (original approach)
            sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = Path(__file__).parent.parent / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    raise click.ClickException(f'functions.sql not found')
            
            click.echo(f'✓ Found functions.sql at {sql_path}')
            with open(sql_path, 'r') as f:
                sql = f.read()
            
            # Step 2: Try applying full SQL script (original approach)
            click.echo('Attempting to apply full functions.sql...')
            success = False
            try:
                # Split SQL into statements and execute each separately
                statements = []
                current_statement = []
                
                # Simple SQL parser to split on semicolons that aren't in functions
                in_function = False
                in_do_block = False
                nesting_level = 0
                
                for line in sql.split('\n'):
                    # Track function and DO block boundaries
                    if 'DO $$' in line:
                        in_do_block = True
                        nesting_level += 1
                    elif '$$' in line and not in_function:
                        if in_do_block:
                            nesting_level -= 1
                            if nesting_level == 0:
                                in_do_block = False
                        else:
                            in_function = not in_function
                    
                    # Add line to current statement
                    current_statement.append(line)
                    
                    # If semicolon outside function/block, end statement
                    if ';' in line and not in_function and not in_do_block:
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                
                # Add any remaining statement
                if current_statement:
                    statements.append('\n'.join(current_statement))
                
                # Execute each statement separately
                error_count = 0
                for i, stmt in enumerate(statements):
                    if not stmt.strip():
                        continue
                    
                    try:
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        click.echo(f"⚠️ Error in statement {i+1}: {str(e)}")
                        error_count += 1
                
                if error_count == 0:
                    click.echo('✓ Applied all database functions and triggers successfully')
                    success = True
                else:
                    click.echo(f'⚠️ Applied with {error_count} errors - may need fallback approach')
            except Exception as e:
                db.session.rollback()
                click.echo(f'⚠️ Error applying full SQL: {str(e)}')
            
            # Step 3: If full script failed, try just the base functions from functions.sql
            if not success:
                click.echo('Attempting to apply only base trigger functions from functions.sql...')
                try:
                    # Extract only base functions (before Authentication Triggers section)
                    base_sections = []
                    current_section = []
                    for line in sql.split('\n'):
                        if "Authentication Triggers" in line:
                            break
                        current_section.append(line)
                    
                    base_sql = '\n'.join(current_section)
                    
                    # Apply only base functions
                    db.session.execute(text(base_sql))
                    db.session.commit()
                    
                    # Apply basic trigger functions to all tables
                    db.session.execute(text("SELECT create_audit_triggers('public')"))
                    db.session.commit()
                    
                    click.echo('✓ Base trigger functions applied successfully')
                    success = True
                except Exception as e:
                    db.session.rollback()
                    click.echo(f'⚠️ Error applying base functions: {str(e)}')
            
            # Step 4: Final fallback - try core_trigger_functions.sql if it exists
            if not success:
                click.echo('Attempting to use core_trigger_functions.sql as fallback...')
                core_sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'core_trigger_functions.sql'
                
                if core_sql_path.exists():
                    try:
                        with open(core_sql_path, 'r') as f:
                            core_sql = f.read()
                        
                        # Split and execute each statement separately for better error handling
                        statements = []
                        current_statement = []
                        in_block = False
                        
                        for line in core_sql.split('\n'):
                            if line.strip().startswith('--'):
                                continue
                                
                            if '$$' in line:
                                in_block = not in_block
                                
                            current_statement.append(line)
                            
                            if ';' in line and not in_block:
                                statements.append('\n'.join(current_statement))
                                current_statement = []
                        
                        # Execute each statement
                        for stmt in statements:
                            if not stmt.strip():
                                continue
                                
                            try:
                                db.session.execute(text(stmt))
                                db.session.commit()
                            except Exception as e:
                                db.session.rollback()
                                click.echo(f'⚠️ Error in core function: {str(e)}')
                        
                        # Apply core triggers to all tables
                        try:
                            db.session.execute(text("SELECT create_audit_triggers_all_schemas()"))
                            db.session.commit()
                            click.echo('✓ Applied core audit triggers to all tables')
                        except Exception as e:
                            db.session.rollback()
                            click.echo(f'⚠️ Error applying core audit triggers: {str(e)}')
                        
                        click.echo('✓ Core trigger functions applied successfully')
                        success = True
                    except Exception as e:
                        db.session.rollback()
                        click.echo(f'⚠️ Error applying core trigger functions: {str(e)}')
                else:
                    click.echo('⚠️ core_trigger_functions.sql not found - cannot use fallback')
            
            # Step 5: Apply hash_password trigger to users table specifically if needed
            try:
                # Check if users table exists
                users_exist = db.session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
                )).scalar()
                
                if users_exist:
                    # Check if hash_password function exists
                    hash_func_exists = db.session.execute(text(
                        "SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                        "WHERE n.nspname = 'public' AND p.proname = 'hash_password')"
                    )).scalar()
                    
                    if hash_func_exists:
                        # Check if trigger already exists
                        trigger_exists = db.session.execute(text(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.triggers "
                            "WHERE trigger_schema = 'public' AND event_object_table = 'users' AND trigger_name = 'hash_password')"
                        )).scalar()
                        
                        if not trigger_exists:
                            click.echo('Applying hash_password trigger to users table...')
                            db.session.execute(text("""
                                DROP TRIGGER IF EXISTS hash_password ON users;
                                CREATE TRIGGER hash_password
                                BEFORE INSERT OR UPDATE ON users
                                FOR EACH ROW
                                EXECUTE FUNCTION hash_password();
                            """))
                            db.session.commit()
                            click.echo('✓ Applied hash_password trigger to users table')
            except Exception as e:
                db.session.rollback()
                click.echo(f'⚠️ Error applying hash_password trigger: {str(e)}')
            
            # Final status report
            if success:
                click.echo('\n✓ Database triggers applied successfully via one of the available methods')
            else:
                click.echo('\n⚠️ All methods to apply triggers failed')
                click.echo('  Try running: python scripts/install_triggers.py')
                
        except Exception as e:
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
def verify_triggers():
    """Verify trigger installation"""
    verify_script = Path(__file__).parent / 'verify_triggers.py'
    
    if verify_script.exists():
        # Use dedicated verification script if available
        click.echo("Using dedicated verification script...")
        try:
            # Check functions first
            result = subprocess.run(
                ["python", str(verify_script), "verify-functions"],
                check=True,
                capture_output=True,
                text=True
            )
            for line in result.stdout.splitlines():
                click.echo(line)
            
            # Check critical triggers
            result = subprocess.run(
                ["python", str(verify_script), "verify-critical-triggers"],
                check=True,
                capture_output=True,
                text=True
            )
            for line in result.stdout.splitlines():
                click.echo(line)
                
        except subprocess.CalledProcessError as e:
            click.echo(f'Error in verification: {e.stderr}')
    else:
        # Legacy verification if verify_triggers.py is not available
        app = get_app()
        click.echo('Verifying trigger installation (legacy method)...')
        
        with app.app_context():
            db = get_db()
            
            # Check for core trigger functions
            core_functions = ['update_timestamp', 'track_user_changes', 'hash_password']
            for func in core_functions:
                result = db.session.execute(text(
                    f"SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                    f"WHERE n.nspname = 'public' AND p.proname = '{func}')"
                )).scalar()
                
                if result:
                    click.echo(f"✓ Function '{func}' exists")
                else:
                    click.echo(f"⚠️ Function '{func}' is missing")
            
            # Check triggers on key tables
            tables = ['users', 'login_history', 'user_sessions']
            for table in tables:
                # First check if table exists
                table_exists = db.session.execute(text(
                    f"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    f"WHERE table_schema = 'public' AND table_name = '{table}')"
                )).scalar()
                
                if not table_exists:
                    click.echo(f"⚠️ Table '{table}' does not exist - skipping trigger check")
                    continue
                
                # Count triggers on this table
                trigger_count = db.session.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.triggers "
                    f"WHERE trigger_schema = 'public' AND event_object_table = '{table}'"
                )).scalar()
                
                click.echo(f"Table '{table}' has {trigger_count} triggers")

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

@cli.command()
@with_appcontext
def test_triggers():
    """Run trigger tests to verify functionality"""
    try:
        # Check if the test script exists
        test_script = Path(__file__).parent / 'test_triggers.py'
        if not test_script.exists():
            # Try in tests directory
            test_script = Path(__file__).parent.parent / 'tests' / 'test_security' / 'test_database_triggers.py'
            if not test_script.exists():
                click.echo("⚠️ Could not find trigger test script")
                return
        
        click.echo("Running trigger functionality tests...")
        
        # Run the tests using pytest
        result = subprocess.run(
            ["pytest", str(test_script), "-v"],
            check=False,  # Don't raise exception on test failure
            capture_output=True,
            text=True
        )
        
        # Display test output
        for line in result.stdout.splitlines():
            click.echo(line)
        
        if result.returncode == 0:
            click.echo("✓ All trigger tests passed!")
        else:
            click.echo("⚠️ Some trigger tests failed. Please check the output for details.")
            
    except Exception as e:
        click.echo(f"Error running trigger tests: {e}")
        
if __name__ == '__main__':
    cli()