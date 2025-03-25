# app/core/db_operations/copy.py
"""
Database copy operations.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union

from .utils import (
    get_db_config, normalize_env_name, get_short_env_name,
    get_db_url_components, setup_env_vars, ensure_backup_dir,
    logger, project_root
)
from .backup import backup_database
from .triggers import apply_triggers

def copy_database(source_env: str, target_env: str, schema_only: bool = False, 
                  data_only: bool = False) -> bool:
    """
    Copy database between environments.
    
    Args:
        source_env: Source environment
        target_env: Target environment
        schema_only: Copy only schema
        data_only: Copy only data
        
    Returns:
        True if successful, False otherwise
    """
    if source_env == target_env:
        logger.error("Source and target environments cannot be the same")
        return False
    
    if schema_only and data_only:
        logger.error("Cannot use both schema_only and data_only options")
        return False
    
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment names
    source_full_env = normalize_env_name(source_env)
    target_full_env = normalize_env_name(target_env)
    source_short_env = get_short_env_name(source_full_env)
    target_short_env = get_short_env_name(target_full_env)
    
    # Get database URLs
    source_url = db_config.get_database_url_for_env(source_full_env)
    target_url = db_config.get_database_url_for_env(target_full_env)
    
    if not source_url or not target_url:
        logger.error("Failed to get database URLs")
        return False
    
    logger.info(f'Starting database copy from {source_short_env} to {target_short_env}...')
    
    try:
        # Parse source URL
        source_components = get_db_url_components(source_url)
        
        # Parse target URL
        target_components = get_db_url_components(target_url)
        
        # Create backup of target database first
        backup_dir = ensure_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Backup target database first
        logger.info(f"Creating backup of target database...")
        backup_success, target_backup = backup_database(env=target_short_env, 
                                                     output_file=f"{target_short_env}_{timestamp}_pre_copy.sql")
        
        if not backup_success:
            logger.warning("Failed to create backup of target database")
        
        # Create temporary file for dump
        temp_dump = backup_dir / f"temp_{source_short_env}_to_{target_short_env}_{timestamp}.sql"
        
        # Set environment variables for source database
        source_env_vars = setup_env_vars(source_components)
        
        try:
            # Build pg_dump command with appropriate options
            dump_cmd = [
                'pg_dump',
                '-h', source_components['host'],
                '-p', source_components['port'],
                '-U', source_components['user'],
                '-d', source_components['dbname'],
                '-f', str(temp_dump)
            ]
            
            if schema_only:
                dump_cmd.append('--schema-only')
            elif data_only:
                dump_cmd.append('--data-only')
            
            # Step 1: Dump source database
            logger.info(f"Dumping {source_short_env} database...")
            subprocess.run(dump_cmd, env=source_env_vars, check=True, capture_output=True)
            
            # Set environment variables for target database
            target_env_vars = setup_env_vars(target_components)
            
            # Step 2: If full copy (not schema_only and not data_only), drop and recreate schema in target
            if not data_only and not schema_only:
                logger.info(f"Preparing {target_short_env} database by dropping and recreating schema...")
                reset_cmd = [
                    'psql',
                    '-h', target_components['host'],
                    '-p', target_components['port'],
                    '-U', target_components['user'],
                    '-d', target_components['dbname'],
                    '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
                ]
                
                subprocess.run(reset_cmd, env=target_env_vars, check=True, capture_output=True)
            elif schema_only:
                logger.info(f"Schema-only copy will preserve data in {target_short_env} database")
                
                # For schema-only copy, we need to handle it differently
                # First, create a special command to drop all functions and triggers 
                # without dropping tables and data
                clean_schema_cmd = [
                    'psql',
                    '-h', target_components['host'],
                    '-p', target_components['port'],
                    '-U', target_components['user'],
                    '-d', target_components['dbname'],
                    '-c', """
                    DO $$
                    DECLARE
                        func_record RECORD;
                        trigger_record RECORD;
                    BEGIN
                        -- Drop all triggers in public schema
                        FOR trigger_record IN 
                            SELECT tgname, relname 
                            FROM pg_trigger t 
                            JOIN pg_class c ON t.tgrelid = c.oid 
                            JOIN pg_namespace n ON c.relnamespace = n.oid 
                            WHERE n.nspname = 'public' AND NOT tgisinternal
                        LOOP
                            EXECUTE 'DROP TRIGGER IF EXISTS ' || trigger_record.tgname || ' ON ' || trigger_record.relname || ' CASCADE;';
                        END LOOP;
                        
                        -- Drop all functions in public schema
                        FOR func_record IN 
                            SELECT p.proname, p.oid, p.pronargs, 
                                pg_get_function_identity_arguments(p.oid) as args
                            FROM pg_proc p
                            JOIN pg_namespace n ON p.pronamespace = n.oid
                            WHERE n.nspname = 'public'
                        LOOP
                            BEGIN
                                EXECUTE 'DROP FUNCTION IF EXISTS ' || func_record.proname || '(' || func_record.args || ') CASCADE;';
                            EXCEPTION WHEN OTHERS THEN
                                -- Ignore errors when dropping functions
                                RAISE NOTICE 'Error dropping function %(%): %', func_record.proname, func_record.args, SQLERRM;
                            END;
                        END LOOP;
                    END$$;
                    """
                ]
                
                # Execute the clean schema command
                subprocess.run(clean_schema_cmd, env=target_env_vars, check=True, capture_output=True)
            
            # Step 3: Restore to target database
            logger.info(f"Restoring to {target_short_env} database...")
            restore_cmd = [
                'psql',
                '-h', target_components['host'],
                '-p', target_components['port'],
                '-U', target_components['user'],
                '-d', target_components['dbname'],
                '-f', str(temp_dump)
            ]
            
            subprocess.run(restore_cmd, env=target_env_vars, check=True, capture_output=True)
            
            # Step 4: Re-apply triggers
            logger.info(f"Re-applying database triggers...")
            
            # Save current environment
            current_env = os.environ.get('FLASK_ENV')
            
            # Set environment to target
            os.environ['FLASK_ENV'] = target_full_env
            
            # Apply triggers
            triggers_success = apply_triggers(env=target_short_env)
            
            if not triggers_success:
                logger.warning("Failed to re-apply database triggers")
            
            # Restore original environment
            if current_env:
                os.environ['FLASK_ENV'] = current_env
            else:
                os.environ.pop('FLASK_ENV', None)
            
            logger.info(f"Database copied successfully from {source_short_env} to {target_short_env}")
            
            # Clean up temp file
            if temp_dump.exists():
                temp_dump.unlink()
                
            return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Database copy failed: {e}")
            if hasattr(e, 'stdout') and e.stdout:
                logger.debug(f"Output: {e.stdout}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"Error: {e.stderr}")
            
            if backup_success:
                logger.info(f"You can restore the target database from backup: {target_backup}")
            
            return False
        finally:
            # Clean up temp files
            if temp_dump.exists():
                try:
                    temp_dump.unlink()
                except:
                    pass
            
            # Clean up passwords from environment
            if 'source_env_vars' in locals() and 'PGPASSWORD' in source_env_vars:
                del source_env_vars['PGPASSWORD']
            if 'target_env_vars' in locals() and 'PGPASSWORD' in target_env_vars:
                del target_env_vars['PGPASSWORD']
    
    except Exception as e:
        logger.error(f"Error during database copy: {str(e)}")
        return False