# app/__init__.py

from __future__ import annotations

# At the very top of app/__init__.py, before other imports
import os
import sys
import logging
# Set up logging early with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# Enable detailed tracebacks in development
import sys
if hasattr(sys, 'ps1') or os.environ.get('FLASK_ENV') == 'development':
    # Enhanced exception handling for development
    def excepthook(type, value, traceback_obj):
        """Custom exception handler with full traceback"""
        import traceback as tb
        logger.critical("=" * 80)
        logger.critical("UNHANDLED EXCEPTION:")
        logger.critical("=" * 80)
        logger.critical(''.join(tb.format_exception(type, value, traceback_obj)))
        logger.critical("=" * 80)

    sys.excepthook = excepthook

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
    from app.utils.filters import format_currency, format_number, format_date, dateformat, datetimeformat, timeago, register_filters
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
        app.jinja_env.filters['format_number'] = format_number

    def register_jinja_filters(app):
        """Wrapper function that calls register_filters"""
        return register_filters(app)

from app.utils.template_filters import register_document_filters

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

def initialize_cache_system(app):
    """Initialize both service and config cache layers"""
    
    # Service Cache Settings
    app.config.setdefault('SERVICE_CACHE_ENABLED', True)
    app.config.setdefault('SERVICE_CACHE_MAX_MEMORY_MB', 500)
    app.config.setdefault('SERVICE_CACHE_DEFAULT_TTL', 1800)  # 30 minutes
    app.config.setdefault('SERVICE_CACHE_MAX_ENTRIES', 10000)
    
    # Config Cache Settings
    app.config.setdefault('CONFIG_CACHE_ENABLED', True)
    app.config.setdefault('CONFIG_CACHE_PRELOAD', True)
    app.config.setdefault('CONFIG_CACHE_TTL', 3600)  # 1 hour
    
    # Initialize Service Cache
    if app.config.get('SERVICE_CACHE_ENABLED'):
        try:
            from app.engine.universal_service_cache import init_service_cache
            init_service_cache(app)
            app.logger.info("✅ Service cache initialized")
        except Exception as e:
            app.logger.error(f"Service cache init failed: {e}")
            app.config['SERVICE_CACHE_ENABLED'] = False
    
    # Initialize Config Cache
    if app.config.get('CONFIG_CACHE_ENABLED'):
        try:
            from app.engine.universal_config_cache import init_config_cache
            init_config_cache(app)
            app.logger.info("✅ Config cache initialized")
            
            # Preload common configurations
            if app.config.get('CONFIG_CACHE_PRELOAD'):
                from app.engine.universal_config_cache import preload_common_configurations
                preload_common_configurations()
                app.logger.info("✅ Common configurations preloaded")
                
        except Exception as e:
            app.logger.error(f"Config cache init failed: {e}")
            app.config['CONFIG_CACHE_ENABLED'] = False
    
    app.logger.info("✅ Dual-layer caching system initialized")


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

        configure_werkzeug_logging(app)
        
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
        initialize_cache_system(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        csrf.init_app(app)
        
        # Add hasattr and attribute to Jinja globals
        app.jinja_env.globals['hasattr'] = hasattr
        app.jinja_env.globals['attribute'] = getattr
        
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
        register_document_filters(app)

        initialize_document_engine(app)

        # Initialize Redis session management if available
        if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
            try:
                import redis
                redis_client = redis.from_url(settings.REDIS_URL)
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
        except NameError as e:
            app.logger.error(f"register_filters not available: {e}")
            # Basic fallback registration
            app.jinja_env.filters['format_currency'] = lambda value: f"Rs.{float(value or 0):,.2f}"
            app.jinja_env.filters['timeago'] = lambda value: str(value) if value else ""
            app.jinja_env.filters['date_format'] = lambda value, fmt='%b %d, %Y': value.strftime(fmt) if value else ""
            app.jinja_env.filters['datetime_format'] = lambda value, fmt='%b %d, %Y %I:%M %p': value.strftime(fmt) if value else ""
            app.jinja_env.filters['dateformat'] = lambda value, fmt='%Y-%m-%d': value.strftime(fmt) if value else ""
            app.jinja_env.filters['datetimeformat'] = lambda value, fmt='%Y-%m-%d %H:%M:%S': value.strftime(fmt) if value else ""
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
            from app.views.universal_views import universal_bp
            view_blueprints.append(universal_bp)
        except ImportError as e:
            app.logger.warning(f"[WARNING] Universal views blueprint could not be loaded: {str(e)}")
        except Exception as e:
            app.logger.error(f"[ERROR] Error importing universal views: {str(e)}")

        # Import new GL, inventory, and supplier blueprints
        try:
            # GL views
            from app.views.gl_views import gl_views_bp
            view_blueprints.append(gl_views_bp)
            
            # Inventory views
            from app.views.inventory_views import inventory_views_bp
            view_blueprints.append(inventory_views_bp)
            
            # Supplier views - SAFE LOGGING
            from app.views.supplier_views import supplier_views_bp
            view_blueprints.append(supplier_views_bp)
            
        except ImportError as e:
            app.logger.warning(f"Additional views blueprint could not be loaded: {str(e)}")
        
        try:
            # Billing views
            from app.views.billing_views import billing_views_bp
            view_blueprints.append(billing_views_bp)
        except ImportError as e:
            app.logger.warning(f"Billing views blueprint could not be loaded: {str(e)}")

        try:
            # Package views
            from app.views.package_views import package_views_bp
            view_blueprints.append(package_views_bp)
        except ImportError as e:
            app.logger.warning(f"Package views blueprint could not be loaded: {str(e)}")

        app.logger.info("Registered view blueprints")
    except ImportError as e:
        app.logger.warning(f"View blueprints could not be loaded: {str(e)}")
    
    # Register each blueprint
    for blueprint in view_blueprints:
        if blueprint is None:
            continue
        try:
            app.register_blueprint(blueprint)
        except Exception as e:
            app.logger.error(f"Failed to register view blueprint {getattr(blueprint, 'name', 'unknown')}: {str(e)}")


def register_api_blueprints(app: Flask) -> None:
    """Register API blueprints"""
    blueprints = []
    
    # Register core API blueprints
    try:
        from .api.routes import admin_bp, patient_bp
        blueprints.extend([admin_bp, patient_bp])
    except ImportError as e:
        app.logger.warning(f"Core blueprints could not be loaded: {str(e)}")
    
    # Register verification API blueprints
    try:
        from .api.routes.verification import verification_api
        from .api.routes.approval import approval_api
        blueprints.extend([verification_api, approval_api])
    except ImportError as e:
        app.logger.warning(f"Verification blueprints could not be loaded: {str(e)}")

    # Register security blueprints
    try:
        from .security.routes import security_bp, rbac_bp, audit_bp, auth_bp
        blueprints.extend([security_bp, rbac_bp, audit_bp, auth_bp])
        app.logger.info("Added security blueprints to registration list")
    except ImportError as e:
        app.logger.warning(f"Security blueprints could not be loaded: {str(e)}")
    
    # Register new API blueprints for GL, inventory, and supplier
    try:
        # GL API
        from .api.routes.gl import gl_api_bp
        blueprints.append(gl_api_bp)
    except ImportError as e:
        app.logger.warning(f"GL API blueprint could not be loaded: {str(e)}")
        
    try:
        # Inventory API
        from .api.routes.inventory import inventory_api_bp
        blueprints.append(inventory_api_bp)
    except ImportError as e:
        app.logger.warning(f"Inventory API blueprint could not be loaded: {str(e)}")
        
    try:
        # Supplier API
        from .api.routes.supplier import supplier_api_bp
        blueprints.append(supplier_api_bp)
    except ImportError as e:
        app.logger.warning(f"Supplier API blueprint could not be loaded: {str(e)}")
    
    try:
        # Billing API
        from .api.routes.billing import billing_api_bp
        blueprints.append(billing_api_bp)
    except ImportError as e:
        app.logger.warning(f"Billing API blueprint could not be loaded: {str(e)}")

    try:
        # Package API
        from .api.routes.package_api import package_api_bp
        blueprints.append(package_api_bp)
    except ImportError as e:
        app.logger.warning(f"Package API blueprint could not be loaded: {str(e)}")

    try:
        # Staff API
        from .api.routes.staff import staff_api_bp
        blueprints.append(staff_api_bp)
    except ImportError as e:
        app.logger.warning(f"Staff API blueprint could not be loaded: {str(e)}")

    try:
        # cache dashboard
        from app.views.cache_dashboard import cache_dashboard_bp
        blueprints.append(cache_dashboard_bp)
    except ImportError as e:
        app.logger.warning(f"cache dashboard blueprint could not be loaded: {str(e)}")

    # Register universal API blueprint
    try:
        from app.api.routes.universal_api import universal_api_bp
        blueprints.append(universal_api_bp)
    except ImportError as e:
        app.logger.warning(f"Universal API blueprint could not be loaded: {str(e)}")

    # Register patient info API blueprint
    try:
        from app.api.routes.patient_api_enhancement import patient_info_bp
        blueprints.append(patient_info_bp)
    except ImportError as e:
        app.logger.warning(f"Patient info API blueprint could not be loaded: {str(e)}")

    # Register each blueprint
    for blueprint in blueprints:
        if blueprint is None:
            continue
        try:
            app.register_blueprint(blueprint)
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
                maxBytes=5*1024*1024,  # 5MB
                backupCount=0,
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
        
def initialize_document_engine(app):
    """
    Initialize document engine for Universal Engine
    Call this in create_app() after blueprint registration
    """
    try:
        from app.engine.document_service import get_document_service
        
        # Register document service
        app.document_service = get_document_service()
        
        # Ensure required filters are registered
        ensure_document_filters(app)
        
        app.logger.info("✅ Document Engine initialized successfully")
        return True
        
    except Exception as e:
        app.logger.error(f"Failed to initialize Document Engine: {str(e)}")
        return False

def ensure_document_filters(app):
    """Ensure all required Jinja filters for documents are registered"""
    
    # Check and add format_currency
    if 'format_currency' not in app.jinja_env.filters:
        try:
            from app.utils.filters import format_currency
            app.jinja_env.filters['format_currency'] = format_currency
        except ImportError:
            # Fallback implementation
            app.jinja_env.filters['format_currency'] = lambda x: f"Rs.{float(x or 0):,.2f}"
    
    # Check and add date filters
    if 'dateformat' not in app.jinja_env.filters:
        try:
            from app.utils.filters import dateformat
            app.jinja_env.filters['dateformat'] = dateformat
        except ImportError:
            # Fallback implementation
            from datetime import datetime
            app.jinja_env.filters['dateformat'] = lambda x: x.strftime('%d/%m/%Y') if x else ''
    
    if 'datetimeformat' not in app.jinja_env.filters:
        try:
            from app.utils.filters import datetimeformat
            app.jinja_env.filters['datetimeformat'] = datetimeformat
        except ImportError:
            # Fallback implementation
            from datetime import datetime
            app.jinja_env.filters['datetimeformat'] = lambda x: x.strftime('%d/%m/%Y %H:%M') if x else ''
    
    # Add sum filter for tables
    if 'sum' not in app.jinja_env.filters:
        def sum_filter(items, attribute):
            """Sum values from a list of dictionaries"""
            if not items:
                return 0
            total = 0
            for item in items:
                if isinstance(item, dict):
                    value = item.get(attribute, 0)
                    try:
                        total += float(value) if value else 0
                    except (ValueError, TypeError):
                        continue
            return total
        
        app.jinja_env.filters['sum'] = sum_filter

def configure_werkzeug_logging(app):
    """Configure Werkzeug to reduce static file logging noise"""
    import logging
    
    # Get werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    
    if app.debug:
        # In debug mode, keep werkzeug at INFO but filter static files
        werkzeug_logger.setLevel(logging.INFO)
        
        # Add custom filter to reduce static file noise
        class StaticFileFilter(logging.Filter):
            def filter(self, record):
                # Filter out static file requests (304 responses are cached files)
                if hasattr(record, 'getMessage'):
                    message = record.getMessage()
                    # Skip logging for static files with 304 (Not Modified) responses
                    if '/static/' in message and '" 304 -' in message:
                        return False
                    # Skip common static file extensions
                    static_extensions = ['.css', '.js', '.jpg', '.png', '.ico', '.woff', '.ttf']
                    if any(ext in message for ext in static_extensions) and '" 304 -' in message:
                        return False
                return True
        
        # Apply filter to werkzeug logger
        static_filter = StaticFileFilter()
        werkzeug_logger.addFilter(static_filter)
        
    else:
        # In production, set werkzeug to WARNING level to reduce noise
        werkzeug_logger.setLevel(logging.WARNING)
    
    app.logger.info("Werkzeug logging configured for production")