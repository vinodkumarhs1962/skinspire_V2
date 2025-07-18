# app/__init__.py

from __future__ import annotations

# At the very top of app/__init__.py, before other imports
import os
import sys
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
try:
    from app.utils.filters import format_currency, dateformat, datetimeformat, timeago, register_filters
except ImportError:
    # Fallback functions if import fails
    def format_currency(value):
        return f"Rs.{float(value or 0):,.2f}"
    def dateformat(value, fmt='%Y-%m-%d'):
        return value.strftime(fmt) if value else ""
    def datetimeformat(value, fmt='%Y-%m-%d %H:%M:%S'):
        return value.strftime(fmt) if value else ""
    def timeago(value):
        return str(value) if value else ""
    def register_filters(app):
        # Basic registration
        app.jinja_env.filters['format_currency'] = format_currency
        app.jinja_env.filters['dateformat'] = dateformat
        app.jinja_env.filters['datetimeformat'] = datetimeformat
        app.jinja_env.filters['timeago'] = timeago

    def register_jinja_filters(app):
        """Wrapper function that calls register_filters"""
        return register_filters(app)


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
        
        setup_unicode_logging()
        
        # Configure logging first to ensure proper error tracking
        app.logger.setLevel(logging.INFO)
        
        fix_logging_rotation_error(app)

        # NEW: Ensure Flask app logger uses Unicode-safe formatters
        setup_flask_unicode_logging(app)

        
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
        
        # Add hasattr to Jinja globals
        app.jinja_env.globals['hasattr'] = hasattr
        
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

        # Register util filters
        register_filters(app)

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
        
        try:
            from app.services.posting_config_service import validate_posting_configuration
            config_errors = validate_posting_configuration()
            if config_errors:
                app.logger.warning("Enhanced posting configuration issues found:")
                for error in config_errors:
                    app.logger.warning(f"  - {error}")
            else:
                app.logger.info("Enhanced posting configuration validated successfully")
        except Exception as e:
            app.logger.warning(f"Could not validate posting configuration: {str(e)}")


        # Register view blueprints (for frontend)
        register_view_blueprints(app)
        
        # Register API blueprints - must happen before security initialization
        register_api_blueprints(app)
        
        # Initialize security components
        initialize_security(app)
        
        # Register error handlers
        register_error_handlers(app)

        # Register custom filters - FIXED
        try:
            # Use the imported register_filters function directly
            register_filters(app)
            app.logger.info("Successfully registered Jinja filters")
        except NameError as e:
            app.logger.error(f"register_filters not available: {e}")
            # Basic fallback registration
            app.jinja_env.filters['format_currency'] = lambda value: f"Rs.{float(value or 0):,.2f}"
            app.jinja_env.filters['dateformat'] = lambda value, fmt='%Y-%m-%d': value.strftime(fmt) if value else ""
            app.jinja_env.filters['datetimeformat'] = lambda value, fmt='%Y-%m-%d %H:%M:%S': value.strftime(fmt) if value else ""
            app.jinja_env.filters['timeago'] = lambda value: str(value) if value else ""
            app.logger.warning("Using basic filter fallback")
        except Exception as e:
            app.logger.error(f"Unexpected filter registration error: {e}")
            # Emergency minimal filters
            app.jinja_env.filters['format_currency'] = lambda v: f"Rs.{float(v or 0):,.2f}"
            app.logger.warning("Emergency filter fallback activated")
        
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
        
        
        # Add built-in functions to Jinja2 template context
        @app.template_global()
        def min_func(a, b):
            """Min function for Jinja templates"""
            return min(a, b)
        
        @app.template_global()
        def max_func(a, b):
            """Max function for Jinja templates"""
            return max(a, b)
        
        # Make built-in min/max available in templates
        app.jinja_env.globals['min'] = min
        app.jinja_env.globals['max'] = max
        
        
        app.logger.info("Application initialization completed successfully")
        def optional_database_cleanup():
            """
            Explicit method to clean up database connections.
            
            Design principles:
            - Completely optional
            - Safe to call multiple times
            - Minimal side effects
            """
            try:
                from app.services.database_service import close_db_connections
                
                # Log the cleanup attempt
                app.logger.info("Initiating optional database connection cleanup")
                
                # Close database connections
                close_db_connections()
                
                app.logger.info("Database connection cleanup completed")
            except Exception as e:
                # Log any issues without disrupting application flow
                app.logger.warning(f"Database connection cleanup encountered an issue: {e}")
        
        # Can be called explicitly if needed
        app.optional_database_cleanup = optional_database_cleanup
        return app
        
    except Exception as e:
        logging.error(f"Failed to create application: {str(e)}")
        raise
 
def format_currency(value):
    """Format a value as currency for Jinja templates"""
    if value is None:
        return " Rs.0.00"
    try:
        return f" Rs.{float(value):,.2f}"
    except (ValueError, TypeError):
        return " Rs.0.00"
   
def register_view_blueprints(app: Flask) -> None:
    """UPDATED: Register frontend view blueprints with safe logging"""
    view_blueprints = []
    
    try:
        # Import view blueprints
        from app.views.auth_views import auth_views_bp
        view_blueprints.append(auth_views_bp)
        
        # Import verification views blueprint
        from app.views.verification_views import verification_views_bp
        view_blueprints.append(verification_views_bp)

        # Import admin views blueprint
        from app.views.admin_views import admin_views_bp
        view_blueprints.append(admin_views_bp)
        
        # SAFE: Universal Views Blueprint - NO EMOJI
        try:
            app.logger.info("[PROCESS] Attempting to import universal views...")
            from app.views.universal_views import universal_bp
            view_blueprints.append(universal_bp)
            app.logger.info("[SUCCESS] Successfully imported universal views blueprint")
        except ImportError as e:
            app.logger.warning(f"[WARNING] Universal views blueprint could not be loaded: {str(e)}")
        except Exception as e:
            app.logger.error(f"[ERROR] Error importing universal views: {str(e)}")

        # Import new GL, inventory, and supplier blueprints
        try:
            # GL views
            from app.views.gl_views import gl_views_bp
            view_blueprints.append(gl_views_bp)
            app.logger.info("Successfully imported GL views blueprint")
            
            # Inventory views
            from app.views.inventory_views import inventory_views_bp
            view_blueprints.append(inventory_views_bp)
            app.logger.info("Successfully imported inventory views blueprint")
            
            # Supplier views - SAFE LOGGING
            app.logger.info("Attempting to import supplier views...")
            app.logger.info("Attempting to import supplier views...")
            from app.views.supplier_views import supplier_views_bp
            app.logger.info(f"supplier_views_bp: {supplier_views_bp}")
            view_blueprints.append(supplier_views_bp)
            app.logger.info("Successfully imported supplier views blueprint")
            
        except ImportError as e:
            app.logger.warning(f"Additional views blueprint could not be loaded: {str(e)}")
        
        try:
            # Billing views
            from app.views.billing_views import billing_views_bp
            view_blueprints.append(billing_views_bp)
            app.logger.info("Successfully imported billing views blueprint")
        except ImportError as e:
            app.logger.warning(f"Billing views blueprint could not be loaded: {str(e)}")

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

    # Debug: Check if supplier blueprint is actually registered - SAFE LOGGING
    if 'supplier_views' in app.blueprints:
        app.logger.info("supplier_views blueprint is registered")
        app.logger.info(f"  URL prefix: {app.blueprints['supplier_views'].url_prefix}")
    else:
        app.logger.error("supplier_views blueprint is NOT registered")
        app.logger.error(f"  Registered blueprints: {list(app.blueprints.keys())}")

    # Debug: Check if universal views blueprint is registered - SAFE LOGGING
    if 'universal_views' in app.blueprints:
        app.logger.info("[SUCCESS] universal_views blueprint is registered")
        app.logger.info(f"  URL prefix: {app.blueprints['universal_views'].url_prefix}")
        app.logger.info("[READY] Universal Engine is ready!")
    else:
        app.logger.error("[ERROR] universal_views blueprint is NOT registered")
        app.logger.error(f"  Registered blueprints: {list(app.blueprints.keys())}")

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
    
    # Register verification API blueprints
    try:
        from .api.routes.verification import verification_api
        from .api.routes.approval import approval_api
        app.logger.info("Successfully imported verification blueprints")
        blueprints.extend([verification_api, approval_api])
        app.logger.info("Added verification blueprints to registration list")
    except ImportError as e:
        app.logger.warning(f"Verification blueprints could not be loaded: {str(e)}")

    # Register security blueprints
    try:
        app.logger.info("Attempting to import security blueprints...")
        from .security.routes import security_bp, rbac_bp, audit_bp, auth_bp
        app.logger.info("Successfully imported security blueprints")
        blueprints.extend([security_bp, rbac_bp, audit_bp, auth_bp])
        app.logger.info("Added security blueprints to registration list")
    except ImportError as e:
        app.logger.warning(f"Security blueprints could not be loaded: {str(e)}")
    
    # Register new API blueprints for GL, inventory, and supplier
    try:
        # GL API
        from .api.routes.gl import gl_api_bp
        blueprints.append(gl_api_bp)
        app.logger.info("Added GL API blueprint to registration list")
    except ImportError as e:
        app.logger.warning(f"GL API blueprint could not be loaded: {str(e)}")
        
    try:
        # Inventory API
        from .api.routes.inventory import inventory_api_bp
        blueprints.append(inventory_api_bp)
        app.logger.info("Added inventory API blueprint to registration list")
    except ImportError as e:
        app.logger.warning(f"Inventory API blueprint could not be loaded: {str(e)}")
        
    try:
        # Supplier API
        from .api.routes.supplier import supplier_api_bp
        blueprints.append(supplier_api_bp)
        app.logger.info("Added supplier API blueprint to registration list")
    except ImportError as e:
        app.logger.warning(f"Supplier API blueprint could not be loaded: {str(e)}")
    
    try:
        # Billing API
        from .api.routes.billing import billing_api_bp
        blueprints.append(billing_api_bp)
        app.logger.info("Added billing API blueprint to registration list")
    except ImportError as e:
        app.logger.warning(f"Billing API blueprint could not be loaded: {str(e)}")

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
    
def setup_unicode_logging():
    """
    SIMPLE: Initialize Unicode logging support
    """
    from app.utils.unicode_logging import setup_unicode_logging as _setup_unicode_logging
    
    # Set up Unicode logging with logs directory
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    success = _setup_unicode_logging(logs_dir)
    
    if success:
        logger = logging.getLogger(__name__)
        logger.info("✅ Unicode logging initialized")
    else:
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ Unicode logging fallback active")
    
    return success

def setup_flask_unicode_logging(app):
    """
    TARGETED FIX: Ensure Flask app logger uses existing Unicode-safe formatters
    """
    try:
        # Import existing Unicode classes from your utils
        from app.utils.unicode_logging import UnicodeFormatter, UnicodeConsoleHandler
        
        # Only add handler if app.logger doesn't have any
        if not app.logger.handlers:
            # Add Unicode-safe console handler
            console_handler = UnicodeConsoleHandler()
            console_handler.setLevel(logging.INFO)
            
            # Use UnicodeFormatter with emoji disabled for Flask logger to prevent issues
            console_formatter = UnicodeFormatter(
                '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
                use_emoji=False  # Disable emoji for Flask logger
            )
            console_handler.setFormatter(console_formatter)
            app.logger.addHandler(console_handler)
            
            # Add Unicode-safe file handler if needed
            logs_dir = os.path.join(app.root_path, '..', 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                os.path.join(logs_dir, 'app.log'),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_formatter = UnicodeFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                use_emoji=False  # Disable emoji for file logging
            )
            file_handler.setFormatter(file_formatter)
            app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info("[SUCCESS] Flask Unicode logging configured using existing utils")
        
    except Exception as e:
        app.logger.warning(f"[WARNING] Could not setup Flask Unicode logging: {e}")

def fix_logging_rotation_error(app):
    """UPDATED: Fix Windows log rotation AND use Unicode-safe formatters"""
    import logging.handlers
    import os
    
    try:
        # Remove any existing RotatingFileHandler from app.logger
        for handler in app.logger.handlers[:]:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                app.logger.removeHandler(handler)
        
        # FIXED: Clear ALL app logger handlers to prevent duplicate/conflicting formatters
        app.logger.handlers.clear()
        
        app.logger.info("[SUCCESS] Fixed logging rotation error and cleared conflicting handlers")
        
    except Exception as e:
        app.logger.warning(f"Could not fix logging rotation: {e}")

def register_jinja_filters(app):
    """Register custom Jinja2 filters - BACKWARD COMPATIBLE FIX"""
    
    @app.template_filter('flatten')
    def flatten_filter(nested_list):
        """Flatten a nested list - FIX for missing flatten filter"""
        try:
            result = []
            for item in nested_list:
                if isinstance(item, (list, tuple)):
                    result.extend(flatten_filter(item))
                else:
                    result.append(item)
            return result
        except Exception:
            return nested_list if isinstance(nested_list, (list, tuple)) else [nested_list]
    
    @app.template_filter('selectattr_safe')
    def selectattr_safe_filter(items, attribute, value=None):
        """Safe selectattr that handles missing attributes"""
        try:
            if value is None:
                return [item for item in items if hasattr(item, attribute) and getattr(item, attribute)]
            else:
                return [item for item in items if hasattr(item, attribute) and getattr(item, attribute) == value]
        except Exception:
            return []