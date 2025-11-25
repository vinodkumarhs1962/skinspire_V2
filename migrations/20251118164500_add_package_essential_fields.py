"""
Add Essential Package Fields
Migration: 20251118164500_add_package_essential_fields
Created: 2025-11-18

Adds 3 essential fields to packages table:
1. package_code - Unique code for search/autocomplete
2. selling_price - Actual selling price (can differ from base price)
3. hsn_code - HSN/SAC code for GST compliance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '20251118164500'
down_revision = '20251118162539'  # Previous migration (BOM tables)
branch_labels = None
depends_on = None


def upgrade():
    """Add essential fields to packages table"""

    # Add package_code column
    op.add_column(
        'packages',
        sa.Column('package_code', sa.String(50), nullable=True,
                  comment="Unique code for search and autocomplete")
    )

    # Add selling_price column
    op.add_column(
        'packages',
        sa.Column('selling_price', sa.Numeric(10, 2), nullable=True,
                  comment="Actual selling price (can differ from base price)")
    )

    # Add hsn_code column
    op.add_column(
        'packages',
        sa.Column('hsn_code', sa.String(10), nullable=True,
                  comment="HSN/SAC code for GST compliance")
    )

    # Create index on package_code for faster searches
    op.create_index(
        'idx_packages_package_code',
        'packages',
        ['package_code']
    )


def downgrade():
    """Remove essential fields from packages table"""

    # Drop index
    op.drop_index('idx_packages_package_code', 'packages')

    # Drop columns
    op.drop_column('packages', 'hsn_code')
    op.drop_column('packages', 'selling_price')
    op.drop_column('packages', 'package_code')
