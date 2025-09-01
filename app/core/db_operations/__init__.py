# app/core/db_operations/__init__.py
"""
Core database operations module for Skinspire HMS.

This package contains core database management functions that are used by
the CLI interfaces and other application components.
"""

from pathlib import Path

# Export common utility functions
from .utils import normalize_env_name, get_short_env_name, get_db_config, ensure_backup_dir

# Export core functionality
from .backup import backup_database, list_backups
from .restore import restore_database
from .migration import create_migration, apply_migration, rollback_migration, show_migrations
from .copy import copy_database
from .triggers import apply_base_triggers, apply_triggers, apply_all_schema_triggers, verify_triggers
from .maintenance import check_db, reset_db, init_db, drop_all_tables

# Schema sync functionality
from .schema_sync import sync_models_to_schema, detect_model_changes, generate_migration_from_changes

# Define the project root globally for use in all submodules
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent