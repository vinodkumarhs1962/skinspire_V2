# app/database/__init__.py

"""
Database Initialization Module

DEPRECATED: This module is deprecated. 
Please use app.services.database_service for all database access.
"""

import logging
logger = logging.getLogger(__name__)

logger.warning("The app.database module is deprecated. Please use app.services.database_service instead.")