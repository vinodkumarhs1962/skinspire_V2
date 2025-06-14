# app/models/business.py
"""
This file contains additional models specific to business processes that may be
referenced from both master.py and transaction.py to avoid circular imports.
"""

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, TenantMixin, generate_uuid

# Add additional business-specific models here if needed in the future
# This file helps avoid circular import dependencies between master.py and transaction.py