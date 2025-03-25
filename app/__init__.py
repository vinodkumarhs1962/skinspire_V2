# app/__init__.py

from __future__ import annotations

# At the very top of app/__init__.py, before other imports
import os
import logging
# Set up logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import centralized environment module first
try:
    from app.core.environment import Environment, current_env
    logger.info(f"Using centralized environment: {current_env}")
    
    # Set up environment variables using centralized Environment
    def setup_environment():
        """Set up environment variables for database operations"""
        if current_env == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
            os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        elif current_env == 'development' and not os.environ.get('DEV_DATABASE_URL'):
            os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
        elif current_env == 'production' and not os.environ.get('PROD_DATABASE_URL'):
            os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'
        
        return True
    
    # Execute environment setup
    setup_environment()
    ENVIRONMENT_MODULE_AVAILABLE = True
except ImportError:
    # Fall back to legacy environment setup if Environment module not available
    ENVIRONMENT_MODULE_AVAILABLE = False
    logger.warning("Centralized Environment module not available, falling back to legacy approach")
    
    # Set up environment variables for database operations
    def setup_environment():
        """Set up environment variables for database operations"""
        if os.environ.get('FLASK_ENV') == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
            os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        elif os.environ.get('FLASK_ENV') == 'development' and not os.environ.get('DEV_DATABASE_URL'):
            os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
        elif os.environ.get('FLASK_ENV') == 'production' and not os.environ.get('PROD_DATABASE_URL'):
            os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'
    
    # Set up environment before other imports
    setup_environment()

from flask_wtf.csrf import CSRFProtect
from flask import Flask, Blueprint, session, request, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from .security.bridge import initialize_security
from app.views.test import test_bp
from pathlib import Path

# Try to load settings, with improved error handling
try:
    from .config.settings import settings
except Exception as e:
    logger.warning(f"Settings initialization failed: {e}")
    # Create a fallback minimal settings object
    from types import SimpleNamespace
    settings = SimpleNamespace()
    settings.SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
    settings.SQLALCHEMY_DATABASE_URI = None


# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app() -> Flask:
    """
    Create and configure the Flask application.
    Returns a configured Flask application instance.
    """
    try:
        # Create the Flask application instance
        app = Flask(__name__)
        
        # Configure logging first to ensure proper error tracking
        app.logger.setLevel(logging.INFO)
        
        # Get database URL - use centralized Environment if available
        if ENVIRONMENT_MODULE_AVAILABLE:
            try:
                from app.config.db_config import DatabaseConfig
                db_url = DatabaseConfig.get_database_url()
                app.logger.info(f"Using database URL from centralized configuration for environment: {current_env}")
            except ImportError:
                # Fall back to database_service if db_config not available
                from app.services.database_service import get_database_url
                db_url = get_database_url()
                app.logger.info("Using database URL from database_service")
        else:
            # Traditional approach
            from app.services.database_service import get_database_url
            db_url = get_database_url()
            app.logger.info("Using database URL from database_service")
        
        # Configure database and other settings
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = settings.SECRET_KEY
        
        # Initialize core Flask extensions
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        csrf.init_app(app)
        
        # Exempt API endpoints from CSRF
        csrf.exempt(r"/api/*")

        # Configure login manager
        login_manager.login_view = 'auth_views.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        
        # Set up user loader for Flask-Login using database_service
        @login_manager.user_loader
        def load_user(user_id):
            from app.models.transaction import User
            from app.services.database_service import get_db_session
            with get_db_session() as session:
                return session.query(User).filter_by(user_id=user_id).first()
        
        # Register menu context processor
        from app.services.menu_service import register_menu_context_processor
        register_menu_context_processor(app)

        # Register admin views
        from app.views.admin_views import admin_views_bp
        app.register_blueprint(admin_views_bp)

        # Initialize Redis session management if available
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            try:
                import redis
                redis_client = redis.from_url(settings.REDIS_URL)
                app.logger.info("Redis initialized successfully")
            except ImportError:
                app.logger.warning("Redis package not installed. Session management will use alternative storage.")
            except Exception as e:
                app.logger.warning(f"Redis connection failed: {str(e)}")
        
        # Register view blueprints (for frontend)
        register_view_blueprints(app)
        
        # Register API blueprints - must happen before security initialization
        register_api_blueprints(app)
        
        # Initialize security components
        initialize_security(app)
        
        # Register error handlers
        register_error_handlers(app)
        
        # Add request middleware for authentication token
        @app.before_request
        def before_request():
            # Skip for static files
            if request.endpoint and 'static' in request.endpoint:
                return
                
            # Store current user in g for easy access
            g.user = current_user
            
            # Add auth token to requests if available in session
            if 'auth_token' in session and request.endpoint:
                auth_token = session.get('auth_token')
                # Add authorization header to environment
                if 'HTTP_AUTHORIZATION' not in request.environ:
                    request.environ['HTTP_AUTHORIZATION'] = f'Bearer {auth_token}'
        
        app.logger.info("Application initialization completed successfully")
        return app
        
    except Exception as e:
        logging.error(f"Failed to create application: {str(e)}")
        raise
 
   
def register_view_blueprints(app: Flask) -> None:
    """Register frontend view blueprints"""
    view_blueprints = []
    
    try:
        # Import view blueprints
        from app.views.auth_views import auth_views_bp
        view_blueprints.append(auth_views_bp)
        
        # Import other view blueprints as they're developed
        # from app.views.user_views import user_views_bp
        # view_blueprints.append(user_views_bp)
        
        app.logger.info("Registered view blueprints")
    except ImportError as e:
        app.logger.warning(f"View blueprints could not be loaded: {str(e)}")
    
    # Register each blueprint
    for blueprint in view_blueprints:
        if blueprint is None:
            continue
        try:
            app.register_blueprint(blueprint)
            app.logger.info(f"Successfully registered view blueprint: {blueprint.name}")
        except Exception as e:
            app.logger.error(f"Failed to register view blueprint {getattr(blueprint, 'name', 'unknown')}: {str(e)}")

def register_api_blueprints(app: Flask) -> None:
    """Register API blueprints"""
    blueprints = []
    
    # Register core API blueprints
    try:
        from .api.routes import admin_bp, patient_bp
        app.logger.info("Successfully imported core blueprints")
        blueprints.extend([admin_bp, patient_bp])
        app.logger.info("Added core blueprints to registration list")
    except ImportError as e:
        app.logger.warning(f"Core blueprints could not be loaded: {str(e)}")
    
    # Register security blueprints
    try:
        app.logger.info("Attempting to import security blueprints...")
        from .security.routes import security_bp, rbac_bp, audit_bp, auth_bp
        app.logger.info("Successfully imported security blueprints")
        blueprints.extend([security_bp, rbac_bp, audit_bp, auth_bp])
        app.logger.info("Added security blueprints to registration list")
    except ImportError as e:
        app.logger.warning(f"Security blueprints could not be loaded: {str(e)}")
    
    # Register each blueprint
    for blueprint in blueprints:
        if blueprint is None:
            continue
        try:
            app.register_blueprint(blueprint)
            app.logger.info(f"Successfully registered API blueprint: {blueprint.name}")
        except Exception as e:
            app.logger.error(f"Failed to register API blueprint {getattr(blueprint, 'name', 'unknown')}: {str(e)}")
            raise
    app.register_blueprint(test_bp)

def register_error_handlers(app: Flask) -> None:
    """Register application error handlers"""
    # API error handlers (JSON responses)
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return {"error": "Resource not found"}, 404
        # For frontend routes, render an error template
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return {"error": "Internal server error"}, 500
        # For frontend routes, render an error template
        return render_template('errors/500.html'), 500  