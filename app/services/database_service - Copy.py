# app/services/database_service.py
"""
Database Service - Centralized Database Access Layer

This module provides a unified interface for database access throughout the application.
It automatically handles the appropriate connection method (Flask-SQLAlchemy or direct SQLAlchemy)
based on the execution context.

Usage:
    from app.services.database_service import get_db_session
    
    with get_db_session() as session:
        user = session.query(User).filter_by(name='John').first()
"""

import os
import logging
import traceback
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator, Union
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app, has_app_context

# Setup logging
logger = logging.getLogger(__name__)

# Track initialization status
_initialized = False
_standalone_engine = None
_standalone_session_factory = None
_debug_mode = os.environ.get("DB_SERVICE_DEBUG", "False").lower() in ("true", "1", "yes")
# Add a flag to control nested transaction behavior
_use_nested_transactions = os.environ.get("USE_NESTED_TRANSACTIONS", "True").lower() in ("true", "1", "yes")

class DatabaseService:
    """
    Service that provides database connections based on context and requirements.
    Acts as a facade over both Flask-SQLAlchemy and standalone connections.
    
    This class handles:
    - Environment detection and configuration
    - Connection management
    - Session creation and lifecycle
    - Transaction boundaries
    - Error handling and logging
    """
    
    @classmethod
    def initialize_database(cls, force: bool = False) -> bool:
        """
        Initialize the database connection if not already done
        
        Args:
            force: Force reinitialization even if already initialized
            
        Returns:
            True if initialization successful, False otherwise
        """
        global _initialized, _standalone_engine, _standalone_session_factory
        
        # Skip if already initialized and not forced
        if _initialized and not force:
            if _debug_mode:
                logger.debug("Database already initialized, skipping")
            return True
            
        try:
            # Get the database URL for the active environment
            env = cls.get_active_environment()
            db_url = cls.get_database_url_for_env(env)
            
            if _debug_mode:
                logger.info(f"Initializing database for environment: {env}")
                logger.info(f"Database URL: {db_url}")
            
            # Initialize standalone engine for non-Flask contexts
            _standalone_engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                echo=_debug_mode  # Echo SQL statements when in debug mode
            )
            
            _standalone_session_factory = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=_standalone_engine
                )
            )
            
            _initialized = True
            logger.info("Database initialized successfully")
            return True
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if _debug_mode:
                logger.debug(f"Stack trace: {traceback.format_exc()}")
            return False
    
    @classmethod
    def get_session(cls, connection_type: str = 'auto', read_only: bool = False) -> Generator[Session, None, None]:
        """
        Get the appropriate database session based on context and requirements.
        
        Args:
            connection_type: 'auto', 'flask', or 'standalone' - determines connection method
                             'auto' will use Flask-SQLAlchemy if in a Flask app context, 
                             otherwise standalone SQLAlchemy
            read_only: Whether the session is for read-only operations
            
        Returns:
            A session context manager that can be used in a 'with' statement
        
        Example:
            with get_db_session() as session:
                user = session.query(User).filter_by(name='John').first()
        """
        # Ensure database is initialized first
        if not _initialized:
            cls.initialize_database()
        
        # Determine connection type if auto
        if connection_type == 'auto':
            if has_app_context():
                connection_type = 'flask'
            else:
                connection_type = 'standalone'
        
        if _debug_mode:
            logger.debug(f"Using {connection_type} database connection (read_only={read_only})")
        
        # Return the appropriate session
        if connection_type == 'flask' and has_app_context():
            return cls._get_flask_session(read_only)
        else:
            return cls._get_standalone_session(read_only)
    
    @classmethod
    @contextmanager
    def _get_flask_session(cls, read_only: bool = False) -> Generator[Session, None, None]:
        """
        Get a Flask-SQLAlchemy session with proper transaction management
        
        Args:
            read_only: Whether the session is for read-only operations
            
        Yields:
            An active database session
        """
        from app import db
        from sqlalchemy.orm import Session as SQLAlchemySession
        from sqlalchemy.exc import SQLAlchemyError
        
        # Create a new session
        session = db.session.registry()
        
        session_id = id(session)
        if _debug_mode:
            logger.debug(f"Created Flask-SQLAlchemy session {session_id}")
        
        try:
            # Only use nested transactions if enabled
            if _use_nested_transactions:
                # Use nested transaction
                with session.begin_nested() as transaction:
                    # Set session to read-only if requested
                    if read_only:
                        cls._set_read_only_mode(session)
                        if _debug_mode:
                            logger.debug(f"Session {session_id} set to read-only mode")
                    
                    # Yield the session
                    yield session
                    # Transaction will be automatically committed or rolled back
            else:
                # No nested transaction - just yield the session directly
                # Set session to read-only if requested
                if read_only:
                    cls._set_read_only_mode(session)
                    if _debug_mode:
                        logger.debug(f"Session {session_id} set to read-only mode")
                
                # Yield the session
                yield session
                
                # Commit if not read-only
                if not read_only:
                    if _debug_mode:
                        logger.debug(f"Committing Flask-SQLAlchemy session {session_id}")
                    session.commit()
        except SQLAlchemyError as e:
            # Rollback on database error
            if _debug_mode:
                logger.debug(f"Rolling back Flask-SQLAlchemy session {session_id} due to SQLAlchemy error")
            session.rollback()
            logger.error(f"Database error in Flask-SQLAlchemy session: {str(e)}")
            raise
        except Exception as e:
            # Rollback on other errors
            if _debug_mode:
                logger.debug(f"Rolling back Flask-SQLAlchemy session {session_id} due to unexpected error")
            session.rollback()
            logger.error(f"Unexpected error in Flask-SQLAlchemy session: {str(e)}")
            raise
        finally:
            # Clean up resources
            if _debug_mode:
                logger.debug(f"Closing Flask-SQLAlchemy session {session_id}")
            
            # Ensure session is closed
            try:
                session.close()
            except Exception as close_error:
                logger.warning(f"Error closing session: {close_error}")

    @classmethod
    @contextmanager
    def _get_standalone_session(cls, read_only: bool = False) -> Generator[Session, None, None]:
        """
        Get a standalone SQLAlchemy session with proper transaction management
        
        Args:
            read_only: Whether the session is for read-only operations
            
        Yields:
            An active database session
        """
        global _standalone_session_factory
        from sqlalchemy.orm import Session as SQLAlchemySession
        from sqlalchemy.exc import SQLAlchemyError
        
        # Ensure session factory exists
        if _standalone_session_factory is None:
            cls.initialize_database()
        
        # Create a new session
        session = _standalone_session_factory()
        session_id = id(session)
        
        if _debug_mode:
            logger.debug(f"Created standalone SQLAlchemy session {session_id}")
        
        try:
            # Only use nested transactions if enabled
            if _use_nested_transactions:
                # Use nested transaction
                with session.begin_nested() as transaction:
                    # Set session to read-only if requested
                    if read_only:
                        cls._set_read_only_mode(session)
                        if _debug_mode:
                            logger.debug(f"Session {session_id} set to read-only mode")
                    
                    # Yield the session
                    yield session
                    # Transaction will be automatically committed or rolled back
            else:
                # No nested transaction - just yield the session directly
                # Set session to read-only if requested
                if read_only:
                    cls._set_read_only_mode(session)
                    if _debug_mode:
                        logger.debug(f"Session {session_id} set to read-only mode")
                
                # Yield the session
                yield session
                
                # Commit if not read-only
                if not read_only:
                    if _debug_mode:
                        logger.debug(f"Committing standalone session {session_id}")
                    session.commit()
        except SQLAlchemyError as e:
            # Rollback on database error
            if _debug_mode:
                logger.debug(f"Rolling back standalone session {session_id} due to SQLAlchemy error")
            session.rollback()
            logger.error(f"Database error in standalone session: {str(e)}")
            raise
        except Exception as e:
            # Rollback on other errors
            if _debug_mode:
                logger.debug(f"Rolling back standalone session {session_id} due to unexpected error")
            session.rollback()
            logger.error(f"Unexpected error in standalone session: {str(e)}")
            raise
        finally:
            # Clean up resources
            if _debug_mode:
                logger.debug(f"Closing standalone session {session_id}")
            
            # Ensure session is closed
            try:
                session.close()
            except Exception as close_error:
                logger.warning(f"Error closing session: {close_error}")
    
    @classmethod
    def get_engine(cls) -> Engine:
        """
        Get the SQLAlchemy engine for the current context
        
        Returns:
            SQLAlchemy engine instance
        """
        # Ensure database is initialized first
        if not _initialized:
            cls.initialize_database()
            
        # Return appropriate engine
        if has_app_context():
            from app import db
            return db.engine
        else:
            global _standalone_engine
            return _standalone_engine
    
    @classmethod
    def get_active_environment(cls) -> str:
        """
        Get the currently active database environment
        
        Returns:
            String representing the environment ('development', 'testing', or 'production')
        """
        env = os.environ.get('FLASK_ENV', 'development')
        
        # Check for environment override file
        env_type_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   '.flask_env_type')
        if os.path.exists(env_type_file):
            with open(env_type_file, 'r') as f:
                env_override = f.read().strip()
                if env_override in ['dev', 'test', 'prod']:
                    env = env_override
        
        return env
    
    @classmethod
    def get_database_url_for_env(cls, env: str) -> str:
        """
        Get the database URL for the specified environment
        
        Args:
            env: Environment name ('development'/'dev', 'testing'/'test', 'production'/'prod')
            
        Returns:
            Database URL string
        """
        if env == 'production' or env == 'prod':
            return os.environ.get('PROD_DATABASE_URL')
        elif env == 'testing' or env == 'test':
            return os.environ.get('TEST_DATABASE_URL')
        else:
            return os.environ.get('DEV_DATABASE_URL')
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Get the database URL for the active environment
        
        Returns:
            Database URL string
        """
        env = cls.get_active_environment()
        return cls.get_database_url_for_env(env)
    
    @classmethod
    def set_debug_mode(cls, debug: bool = True) -> None:
        """
        Set debug mode for the database service
        
        Args:
            debug: True to enable debug mode, False to disable
        """
        global _debug_mode
        _debug_mode = debug
        logger.info(f"Database service debug mode {'enabled' if debug else 'disabled'}")
    
    @classmethod
    def use_nested_transactions(cls, use_nested: bool = True) -> None:
        """
        Enable or disable nested transactions
        
        Args:
            use_nested: True to enable nested transactions, False to disable
        """
        global _use_nested_transactions
        _use_nested_transactions = use_nested
        logger.info(f"Nested transactions {'enabled' if use_nested else 'disabled'}")

    @classmethod
    def _set_read_only_mode(cls, session):
        """Set session to read-only mode"""
        session.execute(text('SET TRANSACTION READ ONLY'))

# Convenience functions - public API

def get_db_session(connection_type: str = 'auto', read_only: bool = False) -> Generator[Session, None, None]:
    """
    Get a database session context manager
    
    This is the primary function for accessing the database. All database operations
    should be performed within the context of a session obtained from this function.
    
    Args:
        connection_type: 'auto', 'flask', or 'standalone'
        read_only: Whether the session is for read-only operations
        
    Returns:
        A session context manager that can be used in a 'with' statement
        
    Example:
        # Basic usage
        from app.services.database_service import get_db_session
        
        with get_db_session() as session:
            user = session.query(User).filter_by(name='John').first()
        
        # Read-only usage (for queries that don't modify data)
        with get_db_session(read_only=True) as session:
            users = session.query(User).all()
    """
    return DatabaseService.get_session(connection_type, read_only)

def get_db_engine() -> Engine:
    """
    Get the SQLAlchemy engine
    
    This function automatically ensures the database is initialized
    before providing the engine.
    
    Returns:
        SQLAlchemy engine instance
    """
    return DatabaseService.get_engine()

def get_active_env() -> str:
    """
    Get the active database environment
    
    Returns:
        String representing the current environment ('development', 'testing', or 'production')
    """
    return DatabaseService.get_active_environment()

def get_database_url() -> str:
    """
    Get the database URL for the active environment
    
    Returns:
        Database URL string
    """
    return DatabaseService.get_database_url()

def initialize_database(force: bool = False) -> bool:
    """
    Initialize the database connection
    
    This function can be called explicitly, but is also automatically
    called by other database service functions as needed.
    
    Args:
        force: Force reinitialization even if already initialized
        
    Returns:
        True if initialization successful, False otherwise
    """
    return DatabaseService.initialize_database(force)

def set_debug_mode(debug: bool = True) -> None:
    """
    Set debug mode for the database service
    
    When debug mode is enabled, detailed logging of database operations is provided.
    This is useful for development and troubleshooting but should be disabled in production.
    
    Args:
        debug: True to enable debug mode, False to disable
    """
    DatabaseService.set_debug_mode(debug)

def use_nested_transactions(use_nested: bool = True) -> None:
    """
    Enable or disable nested transactions
    
    Args:
        use_nested: True to enable nested transactions, False to disable
    """
    DatabaseService.use_nested_transactions(use_nested)

# Auto-initialize the database when the module is imported
initialize_database()

# For testing, disable nested transactions
if os.environ.get('FLASK_ENV', '') == 'testing':
    use_nested_transactions(False)