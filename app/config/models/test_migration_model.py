# Test migration model (updated with new columns)
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, generate_uuid

class TestMigrationTable(Base, TimestampMixin):
    """Test table for migration strategy testing"""
    __tablename__ = 'test_migration_table'

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    
    # New columns for testing column additions
    priority = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    extra_data = Column(JSONB, default={})
