# tests/conftest.py

# Standard library imports
import logging
import uuid
from datetime import datetime, timezone
import os
import sys

# Third-party imports
import pytest
from flask import Flask
from sqlalchemy.orm import Session
from sqlalchemy import text
from werkzeug.security import generate_password_hash

# Application imports - Core functionality
from app.database import init_db
from app.config.settings import settings

# Application imports - Models
from app.models import (
    Hospital,
    User, 
    UserSession,
    LoginHistory
)

# Application imports - Security
from app.security.routes import auth_bp  # Import from __init__.py is preferred

# Set up logging
logger = logging.getLogger(__name__)

@pytest.fixture
def session(db_session):
    """Alias for db_session for backward compatibility"""
    return db_session

@pytest.fixture(scope='session')
def app():
    import os
     # Create test application with proper configuration and routes
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'templates'))
    
    # """Create test application with proper configuration and routes"""
    # app = Flask(__name__)
    
    # Configure application
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': settings.get_database_url_for_env('testing'),
        'SECRET_KEY': 'test_secret_key',
        'WTF_CSRF_ENABLED': False  # Disable CSRF for testing
    })
    
    # Initialize Flask-Login
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    # Set up user loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        db_manager = get_db()
        with db_manager.get_session() as session:
            return session.query(User).get(user_id)
    
    # Register blueprints
    from app.security.routes import auth_bp
    from app.views.auth_views import auth_views_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(auth_views_bp)

    # Log successful setup
    app.logger.info("Test application created with auth blueprint registered")
    
    return app

@pytest.fixture(scope='session')
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope='session')
def db_manager(app):
    """Get database manager instance"""
    with app.app_context():
        db_manager = init_db(settings.get_database_url_for_env('testing'))
        return db_manager

@pytest.fixture(scope='function')
def db_session(db_manager):
    """Create a fresh database session for each test"""
    session = db_manager.Session()
    try:
        # Initialize schema for test database
        from app.database.context import initialize_schema
        initialize_schema(session)
        
        # Ensure required trigger functions exist for trigger testing
        ensure_test_triggers_exist(session)
        
        yield session
    finally:
        session.rollback()
        session.close()

# Function to ensure test trigger functions exist
def ensure_test_triggers_exist(session):
    """Ensure that required trigger functions exist for testing"""
    try:
        # Check if update_timestamp function exists
        function_exists = session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
            "WHERE n.nspname = 'public' AND p.proname = 'update_timestamp')"
        )).scalar()
        
        if not function_exists:
            # Basic function needed for timestamp tests
            session.execute(text("""
                CREATE OR REPLACE FUNCTION update_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))
            session.commit()
            logger.info("Created update_timestamp trigger function for testing")
        
        # Initialize variable before the if statement
        extension_exists = False

        # Check if hash_password function exists (needed for password trigger tests)
        function_exists = session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
            "WHERE n.nspname = 'public' AND p.proname = 'hash_password')"
        )).scalar()
        


        if not function_exists:
            # Check if pgcrypto extension exists
            extension_exists = session.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto')"
            )).scalar()
            
        if extension_exists:
        # Create hash_password function using pgcrypto
            session.execute(text("""
                CREATE OR REPLACE FUNCTION hash_password()
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Determine which column contains the password
                    DECLARE
                        password_column TEXT := NULL;
                    BEGIN
                        -- Check for common password column names
                        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password_hash') THEN
                            password_column := 'password_hash';
                        ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password') THEN
                            password_column := 'password';
                        END IF;
                        
                        -- Only proceed if we found a password column
                        IF password_column IS NOT NULL THEN
                            -- For password_hash column
                            IF password_column = 'password_hash' THEN
                                -- Only hash if not already hashed
                                IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
                                NEW.password_hash IS NOT NULL THEN # Remove length check from here
                                    -- Use pgcrypto
                                    NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
                                END IF;
                            -- For password column
                            ELSIF password_column = 'password' THEN
                                -- Only hash if not already hashed
                                IF (TG_OP = 'INSERT' OR NEW.password <> OLD.password) AND 
                                NEW.password IS NOT NULL THEN # Remove length check from here
                                    -- Use pgcrypto
                                    NEW.password = crypt(NEW.password, gen_salt('bf', 10));
                                END IF;
                            END IF;
                        END IF;
                    END;
                    
                    RETURN NEW;
                EXCEPTION WHEN OTHERS THEN
                    -- Fail gracefully
                    RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))
        session.commit()
        logger.info("Created hash_password trigger function using pgcrypto for testing")
            # else:
            #     # Create simple mock function for testing if pgcrypto is not available
            #     session.execute(text("""
            #         CREATE OR REPLACE FUNCTION hash_password()
            #         RETURNS TRIGGER AS $$
            #         BEGIN
            #             -- Determine which column contains the password
            #             DECLARE
            #                 password_column TEXT := NULL;
            #             BEGIN
            #                 -- Check for common password column names
            #                 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password_hash') THEN
            #                     password_column := 'password_hash';
            #                 ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password') THEN
            #                     password_column := 'password';
            #                 END IF;
                            
            #                 -- Only proceed if we found a password column
            #                 IF password_column IS NOT NULL THEN
            #                     -- For password_hash column
            #                     IF password_column = 'password_hash' THEN
            #                         -- Only hash if not already hashed
            #                         IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
            #                            NEW.password_hash IS NOT NULL AND 
            #                            NOT (NEW.password_hash LIKE '$2%' OR length(NEW.password_hash) > 50) THEN
            #                             -- Mock hash prefix
            #                             NEW.password_hash = '$2a$10$mock_hash_' || NEW.password_hash;
            #                         END IF;
            #                     -- For password column
            #                     ELSIF password_column = 'password' THEN
            #                         -- Only hash if not already hashed
            #                         IF (TG_OP = 'INSERT' OR NEW.password <> OLD.password) AND 
            #                            NEW.password IS NOT NULL AND 
            #                            NOT (NEW.password LIKE '$2%' OR length(NEW.password) > 50) THEN
            #                             -- Mock hash prefix
            #                             NEW.password = '$2a$10$mock_hash_' || NEW.password;
            #                         END IF;
            #                     END IF;
            #                 END IF;
            #             END;
                        
            #             RETURN NEW;
            #         EXCEPTION WHEN OTHERS THEN
            #             -- Fail gracefully
            #             RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
            #             RETURN NEW;
            #         END;
            #         $$ LANGUAGE plpgsql;
            #     """))
            #     session.commit()
            #     logger.info("Created mock hash_password trigger function for testing")
        
        # Apply these functions as triggers to users table if it exists
        users_table_exists = session.execute(text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
        )).scalar()
        
        if users_table_exists:
            # Add update_timestamp trigger if it doesn't exist
            trigger_exists = session.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.triggers WHERE trigger_schema = 'public' "
                "AND event_object_table = 'users' AND trigger_name = 'update_timestamp')"
            )).scalar()
            
            if not trigger_exists:
                # Check if updated_at column exists
                if session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
                    "AND table_name = 'users' AND column_name = 'updated_at')"
                )).scalar():
                    session.execute(text("""
                        DROP TRIGGER IF EXISTS update_timestamp ON users;
                        CREATE TRIGGER update_timestamp
                        BEFORE UPDATE ON users
                        FOR EACH ROW
                        EXECUTE FUNCTION update_timestamp();
                    """))
                    session.commit()
                    logger.info("Applied update_timestamp trigger to users table for testing")
            
            # Add hash_password trigger if it doesn't exist
            trigger_exists = session.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.triggers WHERE trigger_schema = 'public' "
                "AND event_object_table = 'users' AND trigger_name = 'hash_password')"
            )).scalar()
            
            if not trigger_exists:
                # Check if password column exists
                has_password = session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
                    "AND table_name = 'users' AND column_name IN ('password', 'password_hash'))"
                )).scalar()
                
                if has_password:
                    session.execute(text("""
                        DROP TRIGGER IF EXISTS hash_password ON users;
                        CREATE TRIGGER hash_password
                        BEFORE INSERT OR UPDATE ON users
                        FOR EACH ROW
                        EXECUTE FUNCTION hash_password();
                    """))
                    session.commit()
                    logger.info("Applied hash_password trigger to users table for testing")
                
    except Exception as e:
        logger.warning(f"Error ensuring test triggers exist: {e}")
        session.rollback()

@pytest.fixture
def test_hospital(session):
    """Get test hospital from database"""
    # Query within this session to ensure the instance is attached
    hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
    if not hospital:
        raise ValueError("Test hospital not found - please run setup_test_db.py first")
    
    # Simply return the instance - it's already attached to the session
    return hospital

@pytest.fixture(scope='function')
def test_user(db_session, test_hospital):
    """Create test user with proper cleanup"""
    try:
        # First, we clean up any existing test data in the correct order
        # to avoid foreign key constraint violations
        cleanup_queries = [
            (LoginHistory, "user_id", "test_user"),
            (UserSession, "user_id", "test_user"),
            (User, "user_id", "test_user")
        ]
        
        for model, field, value in cleanup_queries:
            try:
                db_session.query(model).filter_by(**{field: value}).delete()
            except Exception as e:
                logger.warning(f"Cleanup warning for {model.__name__}: {e}")
        
        db_session.commit()
        
        # Create fresh test user
        user = User(
            user_id="test_user",
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True,
            password_hash=generate_password_hash("test_password")
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        yield user
        
        # Cleanup after test, again in the correct order
        for model, field, value in cleanup_queries:
            try:
                db_session.query(model).filter_by(**{field: value}).delete()
            except Exception as e:
                logger.warning(f"Post-test cleanup warning for {model.__name__}: {e}")
        
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Test user fixture error: {str(e)}")
        db_session.rollback()
        raise

@pytest.fixture(scope='function', autouse=True)
def reset_login_attempts(session):
    """Reset failed login attempts before each test"""
    try:
        # Reset the admin user's failed login attempts
        user = session.query(User).filter_by(user_id='9876543210').first()
        if user:
            user.failed_login_attempts = 0
            session.commit()
    except Exception as e:
        print(f"Error resetting login attempts: {e}")
        session.rollback()

# Add to tests/conftest.py

@pytest.fixture
def admin_user(session):
    """Get admin user for testing"""
    user = session.query(User).filter_by(user_id="9876543210").first()
    assert user is not None, "Admin user not found in test database"
    return user

@pytest.fixture
def logged_in_client(client, admin_user, monkeypatch):
    """A client that is logged in as admin"""
    
    # Mock Flask-Login's current_user
    class MockUser:
        is_authenticated = True
        is_active = True
        is_anonymous = False
        
        @property
        def user_id(self):
            return admin_user.user_id
    
    from flask_login import current_user
    monkeypatch.setattr('flask_login.current_user', MockUser())
    
    # Set session token
    with client.session_transaction() as sess:
        sess['auth_token'] = 'test_token_123'
    
    return client