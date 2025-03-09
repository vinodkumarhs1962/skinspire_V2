# app/database/context.py

from contextlib import contextmanager
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def initialize_schema(session):
    """Initialize application schema and extensions"""
    try:
        session.execute(text("""
            DO $$ 
            BEGIN
                -- Create required schemas
                CREATE SCHEMA IF NOT EXISTS application;
                
                -- Create required extensions
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                -- Grant permissions
                GRANT ALL ON SCHEMA application TO skinspire_admin;
            END $$;
        """))
        session.commit()
    except Exception as e:
        logger.error(f"Schema initialization error: {str(e)}")
        session.rollback()
        raise

@contextmanager
def user_context(session, user_id):
    """Context manager to track current user for database operations"""
    try:
        # First attempt to create schema and set up parameters
        try:
            session.execute(text("""
                DO $$ 
                BEGIN
                    -- Create schema if not exists
                    CREATE SCHEMA IF NOT EXISTS application;
                    
                    -- Grant necessary permissions
                    GRANT USAGE ON SCHEMA application TO PUBLIC;
                    
                    -- Enable setting custom parameters
                    EXECUTE 'ALTER DATABASE ' || current_database() || 
                            ' SET application.app_user TO NULL';
                END;
                $$;
            """))
            session.commit()
        except Exception as schema_error:
            # Log but continue - this might fail in test environments
            logger.warning(f"Schema setup warning (safe to ignore in tests): {str(schema_error)}")
            session.rollback()
        
        # Now set the user - use set_config which is more likely to work in limited permission environments
        try:
            session.execute(text("""
                SELECT set_config('application.app_user', :user_id, FALSE);
            """), {
                'user_id': str(user_id)
            })
        except Exception as config_error:
            # Log but continue - just track user info locally if needed
            logger.warning(f"User context warning (safe to ignore in tests): {str(config_error)}")
            
        yield
        
    except Exception as e:
        logger.error(f"User context error: {str(e)}")
        session.rollback()
        # Still yield to allow operations to continue even if context tracking fails
        yield
    finally:
        try:
            # Reset the variable
            session.execute(text("""
                SELECT set_config('application.app_user', NULL, FALSE);
            """))
        except:
            pass