# scripts/copy_test_to_dev.py

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_urls():
    """Get the source and target database URLs"""
    test_db_url = settings.get_database_url_for_env('testing')
    dev_db_url = settings.get_database_url_for_env('development')
    
    if not test_db_url or not dev_db_url:
        raise ValueError("Test or development database URL not found")
    
    return test_db_url, dev_db_url

def parse_db_url(url):
    """Parse database URL into components"""
    # Expected format: postgresql://user:password@host:port/dbname
    parts = url.split('://', 1)[1]
    auth, rest = parts.split('@', 1)
    user_pass = auth.split(':', 1)
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ''
    
    host_port_db = rest.split('/', 1)
    host_port = host_port_db[0].split(':', 1)
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else '5432'
    dbname = host_port_db[1] if len(host_port_db) > 1 else ''
    
    return {
        'user': user,
        'password': password,
        'host': host,
        'port': port,
        'dbname': dbname
    }

def copy_database(source_url, target_url):
    """Copy the source database to the target database"""
    source_db = parse_db_url(source_url)
    target_db = parse_db_url(target_url)
    
    # Export source database
    logger.info(f"Exporting source database {source_db['dbname']}...")
    
    # Set up environment with password
    env = os.environ.copy()
    env['PGPASSWORD'] = source_db['password']
    
    # Create the dump file
    dump_file = Path(project_root) / 'temp' / 'db_dump.sql'
    dump_file.parent.mkdir(exist_ok=True)
    
    # Run pg_dump
    dump_cmd = [
        'pg_dump',
        '-h', source_db['host'],
        '-p', source_db['port'],
        '-U', source_db['user'],
        '-d', source_db['dbname'],
        '-f', str(dump_file),
        '--clean',
        '--if-exists'
    ]
    
    try:
        subprocess.run(dump_cmd, env=env, check=True)
        logger.info("Export completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error exporting database: {e}")
        return False
    
    # Import to target database
    logger.info(f"Importing to target database {target_db['dbname']}...")
    
    # Update environment with target password
    env['PGPASSWORD'] = target_db['password']
    
    # First drop and recreate the target database
    drop_cmd = [
        'dropdb',
        '-h', target_db['host'],
        '-p', target_db['port'],
        '-U', target_db['user'],
        '--if-exists',
        target_db['dbname']
    ]
    
    create_cmd = [
        'createdb',
        '-h', target_db['host'],
        '-p', target_db['port'],
        '-U', target_db['user'],
        target_db['dbname']
    ]
    
    # Run the import
    import_cmd = [
        'psql',
        '-h', target_db['host'],
        '-p', target_db['port'],
        '-U', target_db['user'],
        '-d', target_db['dbname'],
        '-f', str(dump_file)
    ]
    
    try:
        subprocess.run(drop_cmd, env=env, check=True)
        logger.info("Target database dropped")
        
        subprocess.run(create_cmd, env=env, check=True)
        logger.info("Target database created")
        
        subprocess.run(import_cmd, env=env, check=True)
        logger.info("Import completed successfully")
        
        # Clean up
        dump_file.unlink()
        logger.info("Temporary files cleaned up")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error importing database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database copy from test to dev...")
    try:
        source_url, target_url = get_database_urls()
        
        # Show what we're copying
        source_db = parse_db_url(source_url)
        target_db = parse_db_url(target_url)
        
        logger.info(f"Source: {source_db['dbname']} at {source_db['host']}")
        logger.info(f"Target: {target_db['dbname']} at {target_db['host']}")
        
        # Ask for confirmation
        confirm = input(f"This will REPLACE {target_db['dbname']} with a copy of {source_db['dbname']}. Continue? (y/n): ")
        if confirm.lower() != 'y':
            logger.info("Operation cancelled by user")
            sys.exit(0)
        
        # Perform the copy
        success = copy_database(source_url, target_url)
        
        if success:
            logger.info("Database copy completed successfully")
        else:
            logger.error("Database copy failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error copying database: {e}")
        sys.exit(1)