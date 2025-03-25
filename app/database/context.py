# app/database/context.py
"""
Database context management utilities.
These utilities manage database session context like user tracking and schema initialization.
"""

import logging
from contextlib import contextmanager
from sqlalchemy import text

# Try to import centralized database service
try:
    from app.services.database_service import get_db_session
    DATABASE_SERVICE_AVAILABLE = True
except ImportError:
    DATABASE_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

def initialize_schema(session):
    """
    Initialize application schema and extensions
    
    Args:
        session: SQLAlchemy session
    """
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

def initialize_application_schema():
    """
    Initialize application schema using the centralized database service
    
    This function uses the database service to get a session, making it easier
    to use in application code.
    """
    if not DATABASE_SERVICE_AVAILABLE:
        logger.warning("Database service not available, cannot initialize schema automatically")
        return False
    
    try:
        with get_db_session() as session:
            initialize_schema(session)
            logger.info("Application schema initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Error initializing application schema: {str(e)}")
        return False

@contextmanager
def user_context(session, user_id):
    """
    Context manager to track current user for database operations
    
    Args:
        session: SQLAlchemy session
        user_id: User ID to set in the context
        
    Yields:
        None
    """
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

def with_user_context(user_id):
    """
    Decorator factory for adding user context to database operations
    
    This decorator uses the centralized database service to get a session
    and sets up the user context.
    
    Args:
        user_id: User ID to set in the context
        
    Returns:
        Decorator function
    """
    if not DATABASE_SERVICE_AVAILABLE:
        logger.warning("Database service not available, cannot use user context decorator")
        # Return a no-op decorator
        def dummy_decorator(func):
            return func
        return dummy_decorator
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if a session is already provided
            session = None
            for arg in args:
                if hasattr(arg, 'execute') and hasattr(arg, 'commit'):
                    session = arg
                    break
            
            if 'session' in kwargs:
                session = kwargs['session']
            
            if session:
                # Use the provided session with user context
                with user_context(session, user_id):
                    return func(*args, **kwargs)
            else:
                # Get a new session and use it with user context
                with get_db_session() as new_session:
                    with user_context(new_session, user_id):
                        # Add session to kwargs
                        kwargs['session'] = new_session
                        return func(*args, **kwargs)
        
        return wrapper
    
    return decorator