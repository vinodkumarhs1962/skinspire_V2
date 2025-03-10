# app/__init__.py

from __future__ import annotations  # Enable future annotations
from flask import Flask, Blueprint, session, request, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from .config.settings import settings
from .security.bridge import initialize_security
from app.views.test import test_bp
import logging
import os
from pathlib import Path

# Initialize extensions
db = SQLAlchemy()
# print(f"Type of db: {type(db)}")
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
        
        # Check for environment type override
        env_type_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.flask_env_type')
        if os.path.exists(env_type_file):
            with open(env_type_file, 'r') as f:
                env_type = f.read().strip()
            
            if env_type in ['dev', 'test', 'prod']:
                app.logger.info(f"Using {env_type.upper()} environment from .flask_env_type file")
                # Get appropriate database URL from settings
                if hasattr(settings, 'get_database_url_for_env'):
                    database_url = settings.get_database_url_for_env(env_type)
                    app.logger.info(f"Database URL set to {env_type} environment")
                else:
                    # Fallback if settings doesn't have the method
                    database_url = settings.DATABASE_URL
                    app.logger.warning(f"Could not switch to {env_type} database (method not available)")
            else:
                database_url = settings.DATABASE_URL
        else:
            database_url = settings.DATABASE_URL
        
        # Configure essential Flask settings
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = settings.SECRET_KEY
        
        # Initialize core Flask extensions
        db.init_app(app)
        migrate.init_app(app, db)
        login_manager.init_app(app)
        csrf.init_app(app)
        
        # Configure login manager
        login_manager.login_view = 'auth_views.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        
        # Set up user loader for Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            # Import here to avoid circular imports
            from app.models.transaction import User
            return User.query.filter_by(user_id=user_id).first()
        
        # Register menu context processor
        from app.services.menu_service import register_menu_context_processor
        register_menu_context_processor(app)

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
        db.session.rollback()
        if request.path.startswith('/api/'):
            return {"error": "Internal server error"}, 500
        # For frontend routes, render an error template
        return render_template('errors/500.html'), 500

def init_security_tables() -> None:
    """Initialize security-related database tables"""
    try:
        from .security.models import (
            AuditLog,
            SecurityConfiguration,
            PasswordHistory,
            UserSession,
            SecurityEvent
        )
        
        app = create_app()
        with app.app_context():
            tables = [
                AuditLog.__table__,
                SecurityConfiguration.__table__,
                PasswordHistory.__table__,
                UserSession.__table__,
                SecurityEvent.__table__
            ]
            
            for table in tables:
                if not table.exists(db.engine):
                    table.create(db.engine)
            
    except ImportError:
        print("Security models not found. Skipping security table initialization.")
    except Exception as e:
        print(f"Error initializing security tables: {str(e)}")
        raise