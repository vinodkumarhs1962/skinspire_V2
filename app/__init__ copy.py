# app/__init__.py

from __future__ import annotations  # Enable future annotations
from flask import Flask, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .config.settings import settings
from .security.bridge import initialize_security
from app.views.test import test_bp
import logging
import os
from pathlib import Path

# Initialize extensions
db = SQLAlchemy()
print(f"Type of db: {type(db)}")
migrate = Migrate()
login_manager = LoginManager()

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
        
        # Register menu context processor
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
        
        # Register blueprints - must happen before security initialization
        register_blueprints(app)
        
        # Initialize security components
        initialize_security(app)
        
        # Register error handlers
        register_error_handlers(app)
        
        app.logger.info("Application initialization completed successfully")
        return app
        
    except Exception as e:
        logging.error(f"Failed to create application: {str(e)}")
        raise

def register_blueprints(app: Flask) -> None:
    """Register all application blueprints"""
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
            app.logger.info(f"Successfully registered blueprint: {blueprint.name}")
        except Exception as e:
            app.logger.error(f"Failed to register blueprint {getattr(blueprint, 'name', 'unknown')}: {str(e)}")
            raise
    app.register_blueprint(test_bp)

def register_error_handlers(app: Flask) -> None:
    """Register application error handlers"""
    @app.errorhandler(404)
    def not_found_error(error):
        return {"error": "Resource not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {"error": "Internal server error"}, 500

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