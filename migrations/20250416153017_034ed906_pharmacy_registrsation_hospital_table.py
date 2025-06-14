"""
Pharmacy registrsation Hospital table

Revision ID: 034ed906
Revises: 
Create Date: 2025-04-16 15:30:17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '034ed906'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    # Modify table package_service_mapping
    op.alter_column('package_service_mapping', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('package_service_mapping', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table medicines
    op.alter_column('medicines', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('medicines', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table parameter_settings
    op.alter_column('parameter_settings', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('parameter_settings', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table test_migration_table
    op.alter_column('test_migration_table', 'rating', type_=sa.Float())
    op.alter_column('test_migration_table', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('test_migration_table', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table manufacturers
    op.alter_column('manufacturers', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('manufacturers', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table role_module_access
    op.alter_column('role_module_access', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('role_module_access', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table role_master
    op.alter_column('role_master', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('role_master', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table staff_approval_requests
    op.alter_column('staff_approval_requests', 'approved_at', type_=sa.DateTime(timezone=True), postgresql_using="approved_at::timestamptz")
    op.alter_column('staff_approval_requests', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('staff_approval_requests', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table consumable_standards
    op.alter_column('consumable_standards', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('consumable_standards', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table supplier_invoice
    op.alter_column('supplier_invoice', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('supplier_invoice', 'invoice_date', type_=sa.DateTime(timezone=True), postgresql_using="invoice_date::timestamptz")
    op.alter_column('supplier_invoice', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table staff
    op.alter_column('staff', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('staff', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('staff', 'deleted_at', type_=sa.DateTime(timezone=True), postgresql_using="deleted_at::timestamptz")

    # Modify table gl_transaction
    op.alter_column('gl_transaction', 'transaction_date', type_=sa.DateTime(timezone=True), postgresql_using="transaction_date::timestamptz")
    op.alter_column('gl_transaction', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('gl_transaction', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")

    # Modify table package_families
    op.alter_column('package_families', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('package_families', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table branches
    op.alter_column('branches', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('branches', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('branches', 'deleted_at', type_=sa.DateTime(timezone=True), postgresql_using="deleted_at::timestamptz")

    # Modify table purchase_order_header
    op.alter_column('purchase_order_header', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('purchase_order_header', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('purchase_order_header', 'po_date', type_=sa.DateTime(timezone=True), postgresql_using="po_date::timestamptz")

    # Modify table patients
    op.alter_column('patients', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('patients', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('patients', 'deleted_at', type_=sa.DateTime(timezone=True), postgresql_using="deleted_at::timestamptz")

    # Modify table hospital_settings
    op.alter_column('hospital_settings', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('hospital_settings', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table currency_master
    op.alter_column('currency_master', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('currency_master', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table invoice_line_item
    op.alter_column('invoice_line_item', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('invoice_line_item', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table supplier_invoice_line
    op.alter_column('supplier_invoice_line', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('supplier_invoice_line', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table supplier_payment
    op.alter_column('supplier_payment', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('supplier_payment', 'payment_date', type_=sa.DateTime(timezone=True), postgresql_using="payment_date::timestamptz")
    op.alter_column('supplier_payment', 'reconciliation_date', type_=sa.DateTime(timezone=True), postgresql_using="reconciliation_date::timestamptz")
    op.alter_column('supplier_payment', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table chart_of_accounts
    op.alter_column('chart_of_accounts', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('chart_of_accounts', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table users
    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('users', 'last_login', type_=sa.DateTime(timezone=True), postgresql_using="last_login::timestamptz")
    op.alter_column('users', 'deleted_at', type_=sa.DateTime(timezone=True), postgresql_using="deleted_at::timestamptz")
    op.alter_column('users', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table gst_ledger
    op.alter_column('gst_ledger', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('gst_ledger', 'transaction_date', type_=sa.DateTime(timezone=True), postgresql_using="transaction_date::timestamptz")
    op.alter_column('gst_ledger', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table purchase_order_line
    op.alter_column('purchase_order_line', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('purchase_order_line', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table invoice_header
    op.alter_column('invoice_header', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('invoice_header', 'invoice_date', type_=sa.DateTime(timezone=True), postgresql_using="invoice_date::timestamptz")
    op.alter_column('invoice_header', 'notes', type_=sa.String(None))
    op.alter_column('invoice_header', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table services
    op.alter_column('services', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('services', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table medicine_categories
    op.alter_column('medicine_categories', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('medicine_categories', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table verification_codes
    op.alter_column('verification_codes', 'expires_at', type_=sa.DateTime(timezone=True), postgresql_using="expires_at::timestamptz")
    op.alter_column('verification_codes', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('verification_codes', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table gl_entry
    op.alter_column('gl_entry', 'entry_date', type_=sa.DateTime(timezone=True), postgresql_using="entry_date::timestamptz")
    op.alter_column('gl_entry', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('gl_entry', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table login_history
    op.alter_column('login_history', 'logout_time', type_=sa.DateTime(timezone=True), postgresql_using="logout_time::timestamptz")
    op.alter_column('login_history', 'login_time', type_=sa.DateTime(timezone=True), postgresql_using="login_time::timestamptz")
    op.alter_column('login_history', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('login_history', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table inventory
    op.alter_column('inventory', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('inventory', 'transaction_date', type_=sa.DateTime(timezone=True), postgresql_using="transaction_date::timestamptz")
    op.alter_column('inventory', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table user_role_mapping
    op.alter_column('user_role_mapping', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('user_role_mapping', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table suppliers
    op.alter_column('suppliers', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('suppliers', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table module_master
    op.alter_column('module_master', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('module_master', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table payment_details
    op.alter_column('payment_details', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('payment_details', 'payment_date', type_=sa.DateTime(timezone=True), postgresql_using="payment_date::timestamptz")
    op.alter_column('payment_details', 'refund_date', type_=sa.DateTime(timezone=True), postgresql_using="refund_date::timestamptz")
    op.alter_column('payment_details', 'reconciliation_date', type_=sa.DateTime(timezone=True), postgresql_using="reconciliation_date::timestamptz")
    op.alter_column('payment_details', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table user_sessions
    op.alter_column('user_sessions', 'expires_at', type_=sa.DateTime(timezone=True), postgresql_using="expires_at::timestamptz")
    op.alter_column('user_sessions', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('user_sessions', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # Modify table hospitals
    op.add_column('hospitals', sa.Column('pharmacy_registration_valid_until', sa.Date(), nullable=True))
    op.add_column('hospitals', sa.Column('pharmacy_registration_date', sa.Date(), nullable=True))
    op.add_column('hospitals', sa.Column('pharmacy_registration_number', sa.String(50), nullable=True))
    op.alter_column('hospitals', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('hospitals', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")
    op.alter_column('hospitals', 'deleted_at', type_=sa.DateTime(timezone=True), postgresql_using="deleted_at::timestamptz")

    # Modify table packages
    op.alter_column('packages', 'created_at', type_=sa.DateTime(timezone=True), postgresql_using="created_at::timestamptz")
    op.alter_column('packages', 'updated_at', type_=sa.DateTime(timezone=True), postgresql_using="updated_at::timestamptz")

    # ### end commands ###


def downgrade():
    """Downgrade database to previous revision"""
    # ### commands auto-generated for downgrade ###
    op.alter_column('packages', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('packages', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.drop_column('hospitals', 'pharmacy_registration_valid_until')
    op.drop_column('hospitals', 'pharmacy_registration_date')
    op.drop_column('hospitals', 'pharmacy_registration_number')
    op.alter_column('hospitals', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('hospitals', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('hospitals', 'deleted_at', type_=sa.DateTime(timezone=False), postgresql_using="deleted_at::timestamp")
    op.alter_column('user_sessions', 'expires_at', type_=sa.DateTime(timezone=False), postgresql_using="expires_at::timestamp")
    op.alter_column('user_sessions', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('user_sessions', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('payment_details', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('payment_details', 'payment_date', type_=sa.DateTime(timezone=False), postgresql_using="payment_date::timestamp")
    op.alter_column('payment_details', 'refund_date', type_=sa.DateTime(timezone=False), postgresql_using="refund_date::timestamp")
    op.alter_column('payment_details', 'reconciliation_date', type_=sa.DateTime(timezone=False), postgresql_using="reconciliation_date::timestamp")
    op.alter_column('payment_details', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('module_master', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('module_master', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('suppliers', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('suppliers', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('user_role_mapping', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('user_role_mapping', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('inventory', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('inventory', 'transaction_date', type_=sa.DateTime(timezone=False), postgresql_using="transaction_date::timestamp")
    op.alter_column('inventory', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('login_history', 'logout_time', type_=sa.DateTime(timezone=False), postgresql_using="logout_time::timestamp")
    op.alter_column('login_history', 'login_time', type_=sa.DateTime(timezone=False), postgresql_using="login_time::timestamp")
    op.alter_column('login_history', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('login_history', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('gl_entry', 'entry_date', type_=sa.DateTime(timezone=False), postgresql_using="entry_date::timestamp")
    op.alter_column('gl_entry', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('gl_entry', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('verification_codes', 'expires_at', type_=sa.DateTime(timezone=False), postgresql_using="expires_at::timestamp")
    op.alter_column('verification_codes', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('verification_codes', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('medicine_categories', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('medicine_categories', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('services', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('services', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('invoice_header', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('invoice_header', 'invoice_date', type_=sa.DateTime(timezone=False), postgresql_using="invoice_date::timestamp")
    # Revert type change for invoice_header.notes
    # Please specify appropriate type for downgrade
    op.alter_column('invoice_header', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('purchase_order_line', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('purchase_order_line', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('gst_ledger', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('gst_ledger', 'transaction_date', type_=sa.DateTime(timezone=False), postgresql_using="transaction_date::timestamp")
    op.alter_column('gst_ledger', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('users', 'last_login', type_=sa.DateTime(timezone=False), postgresql_using="last_login::timestamp")
    op.alter_column('users', 'deleted_at', type_=sa.DateTime(timezone=False), postgresql_using="deleted_at::timestamp")
    op.alter_column('users', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('chart_of_accounts', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('chart_of_accounts', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('supplier_payment', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('supplier_payment', 'payment_date', type_=sa.DateTime(timezone=False), postgresql_using="payment_date::timestamp")
    op.alter_column('supplier_payment', 'reconciliation_date', type_=sa.DateTime(timezone=False), postgresql_using="reconciliation_date::timestamp")
    op.alter_column('supplier_payment', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('supplier_invoice_line', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('supplier_invoice_line', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('invoice_line_item', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('invoice_line_item', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('currency_master', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('currency_master', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('hospital_settings', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('hospital_settings', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('patients', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('patients', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('patients', 'deleted_at', type_=sa.DateTime(timezone=False), postgresql_using="deleted_at::timestamp")
    op.alter_column('purchase_order_header', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('purchase_order_header', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('purchase_order_header', 'po_date', type_=sa.DateTime(timezone=False), postgresql_using="po_date::timestamp")
    op.alter_column('branches', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('branches', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('branches', 'deleted_at', type_=sa.DateTime(timezone=False), postgresql_using="deleted_at::timestamp")
    op.alter_column('package_families', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('package_families', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('gl_transaction', 'transaction_date', type_=sa.DateTime(timezone=False), postgresql_using="transaction_date::timestamp")
    op.alter_column('gl_transaction', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('gl_transaction', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('staff', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('staff', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('staff', 'deleted_at', type_=sa.DateTime(timezone=False), postgresql_using="deleted_at::timestamp")
    op.alter_column('supplier_invoice', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('supplier_invoice', 'invoice_date', type_=sa.DateTime(timezone=False), postgresql_using="invoice_date::timestamp")
    op.alter_column('supplier_invoice', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('consumable_standards', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('consumable_standards', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('staff_approval_requests', 'approved_at', type_=sa.DateTime(timezone=False), postgresql_using="approved_at::timestamp")
    op.alter_column('staff_approval_requests', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('staff_approval_requests', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('role_master', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('role_master', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('role_module_access', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('role_module_access', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('manufacturers', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('manufacturers', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('test_migration_table', 'rating', type_=sa.Numeric(precision=10, scale=2))
    op.alter_column('test_migration_table', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('test_migration_table', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('parameter_settings', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('parameter_settings', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('medicines', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('medicines', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    op.alter_column('package_service_mapping', 'created_at', type_=sa.DateTime(timezone=False), postgresql_using="created_at::timestamp")
    op.alter_column('package_service_mapping', 'updated_at', type_=sa.DateTime(timezone=False), postgresql_using="updated_at::timestamp")
    # ### end commands ###