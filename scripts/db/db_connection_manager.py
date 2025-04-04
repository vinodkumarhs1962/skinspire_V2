# scripts/db/db_connection_manager.py
"""
Standalone script for explicit database connection management.
Provides detailed database connection status and management with force close capabilities.

Usage:
    python -m scripts.db.db_connection_manager status
    python -m scripts.db.db_connection_manager close
    python -m scripts.db.db_connection_manager close --force
    python -m scripts.db.db_connection_manager reinitialize
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any

# Explicitly add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_connection_status() -> Dict[str, Any]:
    """
    Comprehensively check database connection status
    
    Returns:
        Dictionary with detailed connection status
    """
    try:
        # Dynamically import to avoid circular imports
        from app.config.db_config import DatabaseConfig
        from app.services.database_service import get_active_env, get_database_url
        import sqlalchemy
        
        # Get environment and configuration details
        current_env = get_active_env()
        config = DatabaseConfig.get_config(current_env)
        db_url = get_database_url()
        
        # Check database engine
        try:
            # Create a new engine specifically for status check
            engine = sqlalchemy.create_engine(
                db_url,
                pool_pre_ping=True,  # Validate connection before use
                pool_size=1,
                max_overflow=0
            )
            
            # Test connection with a short timeout
            try:
                with engine.connect() as connection:
                    # Perform a simple query to verify connection
                    connection.execute(sqlalchemy.text('SELECT 1'))
                    connection_status = 'Open'
            except Exception as conn_error:
                connection_status = f'Closed/Error: {str(conn_error)}'
            
            # Immediately dispose of the test engine
            engine.dispose(close=True)
        except Exception as engine_error:
            connection_status = 'Unable to create engine'
        
        return {
            'environment': current_env,
            'database_url': db_url,
            'database_name': db_url.split('/')[-1] if '/' in db_url else 'Unknown',
            'connection_status': connection_status,
            'configuration': {
                'pool_size': config.get('pool_size', 'Default'),
                'echo_sql': config.get('echo', False),
                'nested_transactions': config.get('use_nested_transactions', False)
            }
        }
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return {
            'error': 'Could not import database modules',
            'details': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error checking database status: {e}")
        return {
            'error': 'Unexpected error',
            'details': str(e)
        }

def print_force_close_warning():
    """
    Print a comprehensive warning about force close implications
    """
    warning_message = """
    !!!! FORCE CLOSE DATABASE CONNECTIONS - CRITICAL WARNING !!!!

    Force close will:
    - Immediately terminate ALL active database connections
    - Potentially interrupt ongoing transactions
    - Risk data integrity and consistency
    - May cause unexpected application behavior

    RECOMMENDED ACTIONS:
    1. Ensure no critical transactions are in progress
    2. Notify all users to stop database operations
    3. Have a recovery plan ready
    4. Consider potential data loss risks

    Use force close ONLY in emergency scenarios:
    - Unresponsive database connections
    - Debugging complex connection issues
    - System-wide shutdown procedures

    Press 'Y' to confirm force close, or any other key to cancel.
    """
    print(warning_message)

def get_force_close_confirmation() -> bool:
    """
    Get user confirmation for force close operation
    
    Returns:
        bool: Whether user confirmed force close
    """
    try:
        user_input = input("Confirm force close (Y/N): ").strip().upper()
        return user_input == 'Y'
    except Exception:
        return False

def manage_database_connections(action: str, force: bool = False) -> bool:
    """
    Manage database connections based on specified action
    
    Args:
        action (str): Action to perform ('close', 'reinitialize')
        force (bool): Force close connections
    
    Returns:
        bool: Whether the operation was successful
    """
    try:
        # Import database service dynamically
        from app.services.database_service import manage_database_connections as db_manage
        
        # If force close is requested, show warning and get confirmation
        if force:
            print_force_close_warning()
            if not get_force_close_confirmation():
                logger.info("Force close cancelled by user.")
                return False
        
        # Perform the specified action
        return db_manage(action, force)
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error managing database connections: {e}")
        return False

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Database Connection Management Utility')
    parser.add_argument(
        'action', 
        choices=['status', 'close', 'reinitialize'], 
        help='Action to perform on database connections'
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Force close connections, even if in use'
    )
    parser.add_argument(
        '--env', 
        choices=['development', 'testing', 'production', 'dev', 'test', 'prod'],
        help='Specify environment explicitly'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle environment specification if provided
    if args.env:
        try:
            from app.core.environment import Environment
            
            # Normalize environment name
            target_env = Environment.normalize_env(args.env)
            
            # Set environment
            os.environ['FLASK_ENV'] = target_env
            logger.info(f"Setting environment to: {target_env}")
        except Exception as e:
            logger.error(f"Error setting environment: {e}")
    
    # Perform the specified action
    if args.action == 'status':
        # Display database connection status
        status = check_database_connection_status()
        
        print("\n--- Detailed Database Connection Status ---")
        for key, value in status.items():
            if isinstance(value, dict):
                print(f"{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key.replace('_', ' ').title()}: {sub_value}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
        print("-------------------------------------------\n")
        
        sys.exit(0)
    else:
        # Manage database connections (close or reinitialize)
        success = manage_database_connections(
            action=args.action, 
            force=args.force
        )
        
        if success:
            logger.info(f"Database connection {args.action} successful")
            sys.exit(0)
        else:
            logger.error(f"Database connection {args.action} failed")
            sys.exit(1)

if __name__ == '__main__':
    main()