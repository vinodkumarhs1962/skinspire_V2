"""
Add core business process models

Revision ID: 68931bed
Revises: 
Create Date: 2025-04-11 08:50:22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '68931bed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    # Create table services
    op.create_table(
        'services',
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('sac_code', sa.String(10), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('is_gst_exempt', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('service_owner', sa.String(100), nullable=True),
        sa.Column('max_discount', sa.Numeric(), nullable=True),
        sa.Column('default_gl_account', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table supplier_invoice_line
    op.create_table(
        'supplier_invoice_line',
        sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_name', sa.String(100), nullable=False),
        sa.Column('units', sa.Numeric(), nullable=False),
        sa.Column('pack_purchase_price', sa.Numeric(), nullable=False),
        sa.Column('pack_mrp', sa.Numeric(), nullable=False),
        sa.Column('units_per_pack', sa.Numeric(), nullable=False),
        sa.Column('unit_price', sa.Numeric(), nullable=True),
        sa.Column('is_free_item', sa.Boolean(), nullable=True),
        sa.Column('referenced_line_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('discount_percent', sa.Numeric(), nullable=True),
        sa.Column('discount_amount', sa.Numeric(), nullable=True),
        sa.Column('pre_gst_discount', sa.Boolean(), nullable=True),
        sa.Column('taxable_amount', sa.Numeric(), nullable=True),
        sa.Column('hsn_code', sa.String(10), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst', sa.Numeric(), nullable=True),
        sa.Column('sgst', sa.Numeric(), nullable=True),
        sa.Column('igst', sa.Numeric(), nullable=True),
        sa.Column('total_gst', sa.Numeric(), nullable=True),
        sa.Column('line_total', sa.Numeric(), nullable=True),
        sa.Column('batch_number', sa.String(20), nullable=True),
        sa.Column('manufacturing_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('itc_eligible', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table gl_entry
    op.create_table(
        'gl_entry',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('debit_amount', sa.Numeric(), nullable=True),
        sa.Column('credit_amount', sa.Numeric(), nullable=True),
        sa.Column('entry_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('profit_center', sa.String(50), nullable=True),
        sa.Column('cost_center', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table invoice_line_item
    op.create_table(
        'invoice_line_item',
        sa.Column('line_item_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('package_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('item_type', sa.String(20), nullable=False),
        sa.Column('item_name', sa.String(100), nullable=False),
        sa.Column('hsn_sac_code', sa.String(10), nullable=True),
        sa.Column('batch', sa.String(20), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('included_in_consultation', sa.Boolean(), nullable=True),
        sa.Column('quantity', sa.Numeric(), nullable=False),
        sa.Column('unit_price', sa.Numeric(), nullable=False),
        sa.Column('discount_percent', sa.Numeric(), nullable=True),
        sa.Column('discount_amount', sa.Numeric(), nullable=True),
        sa.Column('taxable_amount', sa.Numeric(), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_amount', sa.Numeric(), nullable=True),
        sa.Column('sgst_amount', sa.Numeric(), nullable=True),
        sa.Column('igst_amount', sa.Numeric(), nullable=True),
        sa.Column('total_gst_amount', sa.Numeric(), nullable=True),
        sa.Column('line_total', sa.Numeric(), nullable=False),
        sa.Column('cost_price', sa.Numeric(), nullable=True),
        sa.Column('profit_margin', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table chart_of_accounts
    op.create_table(
        'chart_of_accounts',
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_group', sa.String(20), nullable=False),
        sa.Column('gl_account_no', sa.String(20), nullable=False),
        sa.Column('account_name', sa.String(100), nullable=False),
        sa.Column('parent_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('opening_balance', sa.Numeric(), nullable=True),
        sa.Column('opening_balance_date', sa.Date(), nullable=True),
        sa.Column('is_posting_account', sa.Boolean(), nullable=True),
        sa.Column('invoice_type_mapping', sa.String(50), nullable=True),
        sa.Column('gst_related', sa.Boolean(), nullable=True),
        sa.Column('gst_component', sa.String(10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table gst_ledger
    op.create_table(
        'gst_ledger',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transaction_type', sa.String(30), nullable=False),
        sa.Column('transaction_reference', sa.String(50), nullable=True),
        sa.Column('cgst_output', sa.Numeric(), nullable=True),
        sa.Column('sgst_output', sa.Numeric(), nullable=True),
        sa.Column('igst_output', sa.Numeric(), nullable=True),
        sa.Column('cgst_input', sa.Numeric(), nullable=True),
        sa.Column('sgst_input', sa.Numeric(), nullable=True),
        sa.Column('igst_input', sa.Numeric(), nullable=True),
        sa.Column('itc_claimed', sa.Boolean(), nullable=True),
        sa.Column('claim_reference', sa.String(50), nullable=True),
        sa.Column('gl_reference', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('entry_month', sa.Integer(), nullable=True),
        sa.Column('entry_year', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table suppliers
    op.create_table(
        'suppliers',
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_name', sa.String(100), nullable=False),
        sa.Column('supplier_category', sa.String(50), nullable=True),
        sa.Column('supplier_address', postgresql.JSONB(), nullable=True),
        sa.Column('contact_person_name', sa.String(100), nullable=True),
        sa.Column('contact_info', postgresql.JSONB(), nullable=True),
        sa.Column('manager_name', sa.String(100), nullable=True),
        sa.Column('manager_contact_info', postgresql.JSONB(), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('black_listed', sa.Boolean(), nullable=True),
        sa.Column('performance_rating', sa.Integer(), nullable=True),
        sa.Column('payment_terms', sa.String(100), nullable=True),
        sa.Column('gst_registration_number', sa.String(15), nullable=True),
        sa.Column('pan_number', sa.String(10), nullable=True),
        sa.Column('tax_type', sa.String(20), nullable=True),
        sa.Column('state_code', sa.String(2), nullable=True),
        sa.Column('bank_details', postgresql.JSONB(), nullable=True),
        sa.Column('remarks', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table medicines
    op.create_table(
        'medicines',
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_name', sa.String(100), nullable=False),
        sa.Column('manufacturer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('preferred_supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('generic_name', sa.String(100), nullable=True),
        sa.Column('dosage_form', sa.String(50), nullable=True),
        sa.Column('unit_of_measure', sa.String(20), nullable=True),
        sa.Column('medicine_type', sa.String(20), nullable=False),
        sa.Column('hsn_code', sa.String(10), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('is_gst_exempt', sa.Boolean(), nullable=True),
        sa.Column('gst_inclusive', sa.Boolean(), nullable=True),
        sa.Column('safety_stock', sa.Integer(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('current_stock', sa.Integer(), nullable=True),
        sa.Column('prescription_required', sa.Boolean(), nullable=True),
        sa.Column('is_consumable', sa.Boolean(), nullable=True),
        sa.Column('default_gl_account', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table manufacturers
    op.create_table(
        'manufacturers',
        sa.Column('manufacturer_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manufacturer_name', sa.String(100), nullable=False),
        sa.Column('manufacturer_address', postgresql.JSONB(), nullable=True),
        sa.Column('specialization', sa.String(100), nullable=True),
        sa.Column('gst_registration_number', sa.String(15), nullable=True),
        sa.Column('pan_number', sa.String(10), nullable=True),
        sa.Column('tax_type', sa.String(20), nullable=True),
        sa.Column('state_code', sa.String(2), nullable=True),
        sa.Column('remarks', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table currency_master
    op.create_table(
        'currency_master',
        sa.Column('currency_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=False),
        sa.Column('currency_name', sa.String(50), nullable=False),
        sa.Column('currency_symbol', sa.String(5), nullable=False),
        sa.Column('exchange_rate', sa.Numeric(), nullable=False),
        sa.Column('is_base_currency', sa.Boolean(), nullable=True),
        sa.Column('decimal_places', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table packages
    op.create_table(
        'packages',
        sa.Column('package_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('package_family_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('package_name', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(), nullable=False),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('is_gst_exempt', sa.Boolean(), nullable=True),
        sa.Column('service_owner', sa.String(100), nullable=True),
        sa.Column('max_discount', sa.Numeric(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table gl_transaction
    op.create_table(
        'gl_transaction',
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.String(50), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('total_debit', sa.Numeric(), nullable=False),
        sa.Column('total_credit', sa.Numeric(), nullable=False),
        sa.Column('reconciliation_status', sa.String(20), nullable=True),
        sa.Column('invoice_header_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supplier_invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table supplier_invoice
    op.create_table(
        'supplier_invoice',
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_invoice_number', sa.String(50), nullable=False),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('supplier_gstin', sa.String(15), nullable=True),
        sa.Column('place_of_supply', sa.String(2), nullable=True),
        sa.Column('reverse_charge', sa.Boolean(), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_amount', sa.Numeric(), nullable=True),
        sa.Column('sgst_amount', sa.Numeric(), nullable=True),
        sa.Column('igst_amount', sa.Numeric(), nullable=True),
        sa.Column('total_gst_amount', sa.Numeric(), nullable=True),
        sa.Column('total_amount', sa.Numeric(), nullable=False),
        sa.Column('itc_eligible', sa.Boolean(), nullable=True),
        sa.Column('payment_status', sa.String(20), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table payment_details
    op.create_table(
        'payment_details',
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cash_amount', sa.Numeric(), nullable=True),
        sa.Column('credit_card_amount', sa.Numeric(), nullable=True),
        sa.Column('debit_card_amount', sa.Numeric(), nullable=True),
        sa.Column('upi_amount', sa.Numeric(), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('card_number_last4', sa.String(4), nullable=True),
        sa.Column('card_type', sa.String(20), nullable=True),
        sa.Column('upi_id', sa.String(50), nullable=True),
        sa.Column('reference_number', sa.String(50), nullable=True),
        sa.Column('total_amount', sa.Numeric(), nullable=False),
        sa.Column('refunded_amount', sa.Numeric(), nullable=True),
        sa.Column('refund_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refund_reason', sa.String(255), nullable=True),
        sa.Column('gl_entry_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reconciliation_status', sa.String(20), nullable=True),
        sa.Column('reconciliation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table purchase_order_line
    op.create_table(
        'purchase_order_line',
        sa.Column('line_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_name', sa.String(100), nullable=False),
        sa.Column('units', sa.Numeric(), nullable=False),
        sa.Column('pack_purchase_price', sa.Numeric(), nullable=False),
        sa.Column('pack_mrp', sa.Numeric(), nullable=False),
        sa.Column('units_per_pack', sa.Numeric(), nullable=False),
        sa.Column('unit_price', sa.Numeric(), nullable=True),
        sa.Column('hsn_code', sa.String(10), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst_rate', sa.Numeric(), nullable=True),
        sa.Column('sgst_rate', sa.Numeric(), nullable=True),
        sa.Column('igst_rate', sa.Numeric(), nullable=True),
        sa.Column('cgst', sa.Numeric(), nullable=True),
        sa.Column('sgst', sa.Numeric(), nullable=True),
        sa.Column('igst', sa.Numeric(), nullable=True),
        sa.Column('total_gst', sa.Numeric(), nullable=True),
        sa.Column('line_total', sa.Numeric(), nullable=True),
        sa.Column('expected_delivery_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table inventory
    op.create_table(
        'inventory',
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stock_type', sa.String(30), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('distributor_invoice_no', sa.String(50), nullable=True),
        sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('medicine_name', sa.String(100), nullable=False),
        sa.Column('medicine_category', sa.String(50), nullable=True),
        sa.Column('batch', sa.String(20), nullable=False),
        sa.Column('expiry', sa.Date(), nullable=False),
        sa.Column('pack_purchase_price', sa.Numeric(), nullable=True),
        sa.Column('pack_mrp', sa.Numeric(), nullable=True),
        sa.Column('units_per_pack', sa.Numeric(), nullable=True),
        sa.Column('unit_price', sa.Numeric(), nullable=True),
        sa.Column('sale_price', sa.Numeric(), nullable=True),
        sa.Column('units', sa.Numeric(), nullable=False),
        sa.Column('percent_discount', sa.Numeric(), nullable=True),
        sa.Column('cgst', sa.Numeric(), nullable=True),
        sa.Column('sgst', sa.Numeric(), nullable=True),
        sa.Column('igst', sa.Numeric(), nullable=True),
        sa.Column('total_gst', sa.Numeric(), nullable=True),
        sa.Column('procedure_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('current_stock', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(50), nullable=True),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table package_families
    op.create_table(
        'package_families',
        sa.Column('package_family_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('package_family', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table invoice_header
    op.create_table(
        'invoice_header',
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invoice_type', sa.String(50), nullable=False),
        sa.Column('is_gst_invoice', sa.Boolean(), nullable=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('place_of_supply', sa.String(2), nullable=True),
        sa.Column('reverse_charge', sa.Boolean(), nullable=True),
        sa.Column('e_invoice_irn', sa.String(100), nullable=True),
        sa.Column('is_interstate', sa.Boolean(), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('total_amount', sa.Numeric(), nullable=False),
        sa.Column('total_discount', sa.Numeric(), nullable=True),
        sa.Column('total_taxable_value', sa.Numeric(), nullable=True),
        sa.Column('total_cgst_amount', sa.Numeric(), nullable=True),
        sa.Column('total_sgst_amount', sa.Numeric(), nullable=True),
        sa.Column('total_igst_amount', sa.Numeric(), nullable=True),
        sa.Column('grand_total', sa.Numeric(), nullable=False),
        sa.Column('paid_amount', sa.Numeric(), nullable=True),
        sa.Column('balance_due', sa.Numeric(), nullable=True),
        sa.Column('gl_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.String(None), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table purchase_order_header
    op.create_table(
        'purchase_order_header',
        sa.Column('po_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_number', sa.String(20), nullable=False),
        sa.Column('po_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_id', sa.String(50), nullable=True),
        sa.Column('quotation_date', sa.Date(), nullable=True),
        sa.Column('expected_delivery_date', sa.Date(), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('deleted_flag', sa.Boolean(), nullable=True),
        sa.Column('approved_by', sa.String(50), nullable=True),
        sa.Column('total_amount', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table package_service_mapping
    op.create_table(
        'package_service_mapping',
        sa.Column('mapping_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('package_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sessions', sa.Integer(), nullable=True),
        sa.Column('is_optional', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table supplier_payment
    op.create_table(
        'supplier_payment',
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payment_method', sa.String(20), nullable=True),
        sa.Column('currency_code', sa.String(3), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(), nullable=True),
        sa.Column('amount', sa.Numeric(), nullable=False),
        sa.Column('reference_no', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('notes', sa.String(255), nullable=True),
        sa.Column('gl_entry_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reconciliation_status', sa.String(20), nullable=True),
        sa.Column('reconciliation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table medicine_categories
    op.create_table(
        'medicine_categories',
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('gst_rate', sa.Numeric(), nullable=True),
        sa.Column('requires_prescription', sa.Boolean(), nullable=True),
        sa.Column('category_type', sa.String(20), nullable=True),
        sa.Column('procedure_linked', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Create table consumable_standards
    op.create_table(
        'consumable_standards',
        sa.Column('standard_id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('standard_quantity', sa.Numeric(), nullable=False),
        sa.Column('unit_of_measure', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=True),
        sa.Column('updated_by', sa.String(50), nullable=True),
    )

    # Modify table branches
    op.add_column('branches', sa.Column('state_code', sa.String(2), nullable=True))
    op.add_column('branches', sa.Column('timezone', sa.String(50), nullable=True))
    op.add_column('branches', sa.Column('gst_registration_number', sa.String(15), nullable=True))
    op.alter_column('branches', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('branches', 'deleted_at', type_=sa.DateTime(timezone=True))
    op.alter_column('branches', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table module_master
    op.alter_column('module_master', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('module_master', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table hospitals
    op.add_column('hospitals', sa.Column('pan_number', sa.String(10), nullable=True))
    op.add_column('hospitals', sa.Column('return_filing_period', sa.String(10), nullable=True))
    op.add_column('hospitals', sa.Column('state_code', sa.String(2), nullable=True))
    op.add_column('hospitals', sa.Column('default_currency', sa.String(3), nullable=True))
    op.add_column('hospitals', sa.Column('bank_account_details', postgresql.JSONB(), nullable=True))
    op.add_column('hospitals', sa.Column('timezone', sa.String(50), nullable=True))
    op.add_column('hospitals', sa.Column('gst_registration_number', sa.String(15), nullable=True))
    op.alter_column('hospitals', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('hospitals', 'deleted_at', type_=sa.DateTime(timezone=True))
    op.alter_column('hospitals', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table role_master
    op.alter_column('role_master', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('role_master', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table role_module_access
    op.alter_column('role_module_access', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('role_module_access', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table hospital_settings
    op.alter_column('hospital_settings', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('hospital_settings', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table user_role_mapping
    op.alter_column('user_role_mapping', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('user_role_mapping', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table login_history
    op.alter_column('login_history', 'logout_time', type_=sa.DateTime(timezone=True))
    op.alter_column('login_history', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('login_history', 'login_time', type_=sa.DateTime(timezone=True))
    op.alter_column('login_history', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table verification_codes
    op.alter_column('verification_codes', 'expires_at', type_=sa.DateTime(timezone=True))
    op.alter_column('verification_codes', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('verification_codes', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table staff_approval_requests
    op.alter_column('staff_approval_requests', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('staff_approval_requests', 'created_at', type_=sa.DateTime(timezone=True))
    op.alter_column('staff_approval_requests', 'approved_at', type_=sa.DateTime(timezone=True))

    # Modify table users
    op.add_column('users', sa.Column('last_currency', sa.String(3), nullable=True))
    op.add_column('users', sa.Column('ui_preferences', postgresql.JSONB(), nullable=True))
    op.alter_column('users', 'deleted_at', type_=sa.DateTime(timezone=True))
    op.alter_column('users', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('users', 'created_at', type_=sa.DateTime(timezone=True))
    op.alter_column('users', 'last_login', type_=sa.DateTime(timezone=True))

    # Modify table user_sessions
    op.alter_column('user_sessions', 'expires_at', type_=sa.DateTime(timezone=True))
    op.alter_column('user_sessions', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('user_sessions', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table test_migration_table
    op.alter_column('test_migration_table', 'rating', type_=sa.Float())
    op.alter_column('test_migration_table', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('test_migration_table', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table staff
    op.alter_column('staff', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('staff', 'deleted_at', type_=sa.DateTime(timezone=True))
    op.alter_column('staff', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table patients
    op.alter_column('patients', 'deleted_at', type_=sa.DateTime(timezone=True))
    op.alter_column('patients', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('patients', 'created_at', type_=sa.DateTime(timezone=True))

    # Modify table parameter_settings
    op.alter_column('parameter_settings', 'updated_at', type_=sa.DateTime(timezone=True))
    op.alter_column('parameter_settings', 'created_at', type_=sa.DateTime(timezone=True))

    # ### end commands ###


def downgrade():
    """Downgrade database to previous revision"""
    # Revert type changes for datetime fields
    timestamp_tables = [
        'parameter_settings', 'patients', 'staff', 'test_migration_table',
        'user_sessions', 'users', 'staff_approval_requests', 'verification_codes',
        'login_history', 'user_role_mapping', 'hospital_settings', 'role_module_access',
        'role_master', 'hospitals', 'module_master', 'branches'
    ]
    
    timestamp_columns = [
        'created_at', 'updated_at', 'deleted_at', 'expires_at', 'approved_at', 
        'last_login', 'logout_time', 'login_time'
    ]
    
    for table in timestamp_tables:
        for column in timestamp_columns:
            try:
                # Not all tables have all columns, so we use try/except
                op.alter_column(table, column, type_=sa.DateTime(timezone=False), nullable=True)
            except:
                pass  # Column doesn't exist in this table or already handled

    # Revert type change for test_migration_table.rating
    op.alter_column('test_migration_table', 'rating', type_=sa.Numeric(precision=10, scale=2))
    
    # Drop new columns from existing tables
    # Users
    op.drop_column('users', 'ui_preferences')
    op.drop_column('users', 'last_currency')
    
    # Hospitals
    op.drop_column('hospitals', 'gst_registration_number')
    op.drop_column('hospitals', 'timezone')
    op.drop_column('hospitals', 'bank_account_details')
    op.drop_column('hospitals', 'default_currency')
    op.drop_column('hospitals', 'state_code')
    op.drop_column('hospitals', 'return_filing_period')
    op.drop_column('hospitals', 'pan_number')
    
    # Branches
    op.drop_column('branches', 'gst_registration_number')
    op.drop_column('branches', 'timezone')
    op.drop_column('branches', 'state_code')
    
    # Drop tables in reverse order (respecting foreign key constraints)
    tables_to_drop = [
        'consumable_standards',
        'medicine_categories',
        'supplier_payment',
        'package_service_mapping',
        'purchase_order_header',
        'invoice_header',
        'package_families',
        'inventory',
        'purchase_order_line',
        'payment_details',
        'supplier_invoice',
        'gl_transaction',
        'packages',
        'currency_master',
        'manufacturers',
        'medicines',
        'suppliers',
        'gst_ledger',
        'chart_of_accounts',
        'invoice_line_item',
        'gl_entry',
        'supplier_invoice_line',
        'services'
    ]
    
    for table in tables_to_drop:
        op.drop_table(table)