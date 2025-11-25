"""
Package BOM and Session Plan Tables
Migration: 20251118162539_package_bom_and_session_plan
Created: 2025-11-18

Creates:
1. package_bom_items - Bill of Materials (polymorphic item reference)
2. package_session_plan - Delivery session planning with resource requirements
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '20251118162539'
down_revision = None  # Update this with your latest migration revision
branch_labels = None
depends_on = None


def upgrade():
    """Create Package BOM and Session Plan tables"""

    # =========================================================================
    # TABLE 1: package_bom_items
    # =========================================================================
    op.create_table(
        'package_bom_items',

        # Primary Keys
        sa.Column('bom_item_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hospital_id', UUID(as_uuid=True), sa.ForeignKey('hospitals.hospital_id'), nullable=False),
        sa.Column('package_id', UUID(as_uuid=True), sa.ForeignKey('packages.package_id'), nullable=False),

        # Polymorphic Item Reference (THE KEY DESIGN)
        sa.Column('item_type', sa.String(20), nullable=False, comment="service, medicine, product, consumable"),
        sa.Column('item_id', UUID(as_uuid=True), nullable=False, comment="Points to services, medicines, etc."),
        sa.Column('item_name', sa.String(200), comment="Denormalized for quick display"),

        # Quantity & Specifications
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False, server_default='1'),
        sa.Column('unit_of_measure', sa.String(50)),

        # Delivery Method
        sa.Column('supply_method', sa.String(20), server_default='per_package',
                  comment="per_package, per_session, session_1, session_2, etc."),

        # Display & Ordering
        sa.Column('display_sequence', sa.Integer),
        sa.Column('is_optional', sa.Boolean, server_default='false'),
        sa.Column('notes', sa.Text),

        # Audit Trail
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(100)),
        sa.Column('modified_at', sa.DateTime(timezone=True)),
        sa.Column('modified_by', sa.String(100)),
        sa.Column('is_deleted', sa.Boolean, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Indexes for package_bom_items
    op.create_index('idx_package_bom_package', 'package_bom_items', ['package_id', 'is_deleted'])
    op.create_index('idx_package_bom_item', 'package_bom_items', ['item_type', 'item_id'])
    op.create_index('idx_package_bom_hospital', 'package_bom_items', ['hospital_id'])

    # =========================================================================
    # TABLE 2: package_session_plan
    # =========================================================================
    op.create_table(
        'package_session_plan',

        # Primary Keys
        sa.Column('session_plan_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('hospital_id', UUID(as_uuid=True), sa.ForeignKey('hospitals.hospital_id'), nullable=False),
        sa.Column('package_id', UUID(as_uuid=True), sa.ForeignKey('packages.package_id'), nullable=False),

        # Session Identification
        sa.Column('session_number', sa.Integer, nullable=False),
        sa.Column('session_name', sa.String(100)),

        # Duration
        sa.Column('estimated_duration_minutes', sa.Integer),

        # Resource Requirements (JSON Array)
        sa.Column('resource_requirements', JSONB,
                  comment='[{"resource_type":"doctor","role":"dermatologist","duration_minutes":30,"quantity":1}]'),

        # Scheduling
        sa.Column('recommended_gap_days', sa.Integer, comment="Gap from previous session"),
        sa.Column('is_mandatory', sa.Boolean, server_default='true'),
        sa.Column('scheduling_notes', sa.Text),

        # Display
        sa.Column('display_sequence', sa.Integer),

        # Audit Trail
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(100)),
        sa.Column('modified_at', sa.DateTime(timezone=True)),
        sa.Column('modified_by', sa.String(100)),
        sa.Column('is_deleted', sa.Boolean, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Indexes for package_session_plan
    op.create_index('idx_session_plan_package', 'package_session_plan', ['package_id', 'is_deleted'])
    op.create_index('idx_session_plan_hospital', 'package_session_plan', ['hospital_id'])
    op.create_index('idx_session_plan_number', 'package_session_plan', ['package_id', 'session_number'])

    # Unique constraint: one session number per package (excluding deleted)
    op.create_index(
        'idx_session_plan_unique',
        'package_session_plan',
        ['package_id', 'session_number'],
        unique=True,
        postgresql_where=sa.text('is_deleted = false')
    )


def downgrade():
    """Drop Package BOM and Session Plan tables"""

    # Drop indexes first
    op.drop_index('idx_session_plan_unique', 'package_session_plan')
    op.drop_index('idx_session_plan_number', 'package_session_plan')
    op.drop_index('idx_session_plan_hospital', 'package_session_plan')
    op.drop_index('idx_session_plan_package', 'package_session_plan')

    op.drop_index('idx_package_bom_hospital', 'package_bom_items')
    op.drop_index('idx_package_bom_item', 'package_bom_items')
    op.drop_index('idx_package_bom_package', 'package_bom_items')

    # Drop tables
    op.drop_table('package_session_plan')
    op.drop_table('package_bom_items')
