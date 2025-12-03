# File: app/services/patient_invoice_service.py

"""
Patient Invoice Service - Universal Engine wrapper for billing operations
Extends UniversalEntityService for generic list/search functionality
Wraps existing billing_service.py functions for backward compatibility
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import desc, asc, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from flask_login import current_user

from app.models.transaction import InvoiceHeader, InvoiceLineItem, PaymentDetail, ARSubledger
from app.models.master import Patient
from app.models.views import PatientInvoiceView, PatientPaymentReceiptView
from app.engine.universal_entity_service import UniversalEntityService
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

# Import existing billing service functions for backward compatibility
from app.services import billing_service

logger = get_unicode_safe_logger(__name__)


class PatientInvoiceService(UniversalEntityService):
    """
    Patient Invoice Service with Universal Engine integration

    - List/Search/View operations use PatientInvoiceView (read-only)
    - Create/Edit/Delete operations use existing billing_service functions
    - Maintains full backward compatibility with existing code
    """

    def __init__(self):
        """Initialize with PatientInvoiceView for list/search operations"""
        # Pass entity_type and model_class to parent
        super().__init__('patient_invoices', PatientInvoiceView)

        logger.info("✅ Initialized PatientInvoiceService with PatientInvoiceView")

    # =========================================================================
    # OVERRIDE: Add virtual field computation for list view
    # =========================================================================

    def _convert_items_to_dict(self, items: list, session) -> list:
        """
        Override parent method to add virtual fields for list view.
        Adds has_free_items and has_sample_items flags for each invoice.
        """
        # First, call parent method to get base dictionaries
        items_dict = super()._convert_items_to_dict(items, session)

        if not items_dict:
            return items_dict

        # Get all invoice IDs from the batch
        invoice_ids = []
        for item_dict in items_dict:
            invoice_id = item_dict.get('invoice_id')
            if invoice_id:
                try:
                    invoice_ids.append(uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id)
                except (ValueError, TypeError):
                    pass

        if not invoice_ids:
            return items_dict

        # Efficient batch query: Get free/sample status for all invoices at once
        try:
            from sqlalchemy import func

            # Query to find which invoices have free items
            free_items_query = session.query(
                InvoiceLineItem.invoice_id
            ).filter(
                InvoiceLineItem.invoice_id.in_(invoice_ids),
                InvoiceLineItem.is_free_item == True
            ).distinct().all()

            free_invoice_ids = {str(row[0]) for row in free_items_query}

            # Query to find which invoices have sample items
            sample_items_query = session.query(
                InvoiceLineItem.invoice_id
            ).filter(
                InvoiceLineItem.invoice_id.in_(invoice_ids),
                InvoiceLineItem.is_sample == True
            ).distinct().all()

            sample_invoice_ids = {str(row[0]) for row in sample_items_query}

            # Add virtual fields to each item
            for item_dict in items_dict:
                invoice_id_str = str(item_dict.get('invoice_id', ''))
                item_dict['has_free_items'] = 'true' if invoice_id_str in free_invoice_ids else 'false'
                item_dict['has_sample_items'] = 'true' if invoice_id_str in sample_invoice_ids else 'false'

            logger.debug(f"Added has_free_items/has_sample_items to {len(items_dict)} invoices. "
                        f"Free: {len(free_invoice_ids)}, Sample: {len(sample_invoice_ids)}")

        except Exception as e:
            logger.error(f"Error computing free/sample virtual fields: {str(e)}")
            # Fallback: Set all to false
            for item_dict in items_dict:
                item_dict['has_free_items'] = 'false'
                item_dict['has_sample_items'] = 'false'

        return items_dict

    # =========================================================================
    # UNIVERSAL ENGINE INTERFACE METHODS
    # =========================================================================

    def get_by_id(self, item_id: str, **kwargs) -> Optional[Dict]:
        """
        Get single invoice by ID - queries PatientInvoiceView for calculated fields

        Matches UniversalEntityService signature for compatibility with Universal Engine.

        Args:
            item_id: Invoice UUID (string or uuid.UUID)
            **kwargs: Additional context (hospital_id, branch_id, current_user, etc.)

        Returns:
            Invoice dict with all calculated fields (payment_status, aging_bucket, etc.)
        """
        try:
            # Extract hospital_id from kwargs
            hospital_id = kwargs.get('hospital_id')
            if not hospital_id:
                logger.error("hospital_id is required in kwargs")
                return None

            # Convert string to UUID if needed
            invoice_uuid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
            hospital_uuid = uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

            # Query PatientInvoiceView to get calculated fields (payment_status, aging_bucket, etc.)
            with get_db_session() as session:
                invoice = session.query(PatientInvoiceView).filter(
                    PatientInvoiceView.invoice_id == invoice_uuid,
                    PatientInvoiceView.hospital_id == hospital_uuid
                ).first()

                if invoice:
                    # Convert to dict using database_service helper
                    invoice_data = get_entity_dict(invoice)

                    # Ensure ALL fields exist with safe defaults to prevent template formatting errors
                    # (prevents "unsupported format string passed to Undefined.__format__" errors)

                    # Currency fields - must have Decimal values, not None
                    currency_fields = [
                        'grand_total', 'balance_due', 'paid_amount', 'total_amount',
                        'total_discount', 'total_taxable_value', 'total_cgst_amount',
                        'total_sgst_amount', 'total_igst_amount', 'total_gst_amount',
                        'exchange_rate'
                    ]
                    for field in currency_fields:
                        if field not in invoice_data or invoice_data[field] is None:
                            invoice_data[field] = Decimal('0.00') if field != 'exchange_rate' else Decimal('1.00')

                    # String fields - must exist with non-empty values
                    string_defaults = {
                        'patient_name': 'Unknown Patient',
                        'patient_mrn': 'N/A',
                        'patient_title': '',
                        'patient_first_name': '',
                        'patient_last_name': '',
                        'patient_phone': '',
                        'patient_mobile': '',
                        'patient_email': '',
                        'payment_status': 'unpaid',
                        'invoice_number': 'N/A',
                        'invoice_type': 'Service',
                        'branch_name': '',
                        'hospital_name': '',
                        'currency_code': 'INR',
                        'notes': '',
                        'cancellation_reason': '',
                        'aging_bucket': '0-30 days',
                        'aging_status': 'Current'
                    }
                    for field, default_value in string_defaults.items():
                        if field not in invoice_data or not invoice_data[field]:
                            invoice_data[field] = default_value

                    # Boolean fields - must exist with explicit True/False
                    boolean_defaults = {
                        'is_gst_invoice': False,
                        'is_cancelled': False,
                        'is_interstate': False,
                        'reverse_charge': False,
                        'patient_is_active': True,
                        'branch_is_active': True
                    }
                    for field, default_value in boolean_defaults.items():
                        if field not in invoice_data:
                            invoice_data[field] = default_value

                    # Date fields - can be None but must exist in dict
                    date_fields = [
                        'invoice_date', 'cancelled_at', 'created_at', 'updated_at',
                        'deleted_at'
                    ]
                    for field in date_fields:
                        if field not in invoice_data:
                            invoice_data[field] = None

                    # Integer fields
                    if 'invoice_age_days' not in invoice_data:
                        invoice_data['invoice_age_days'] = 0
                    if 'status_order' not in invoice_data:
                        invoice_data['status_order'] = 1

                    # UUID fields - convert to strings for URL substitution in actions
                    # (ActionDefinition.get_url() needs string values for {placeholder} replacement)
                    uuid_fields = [
                        'invoice_id', 'patient_id', 'branch_id', 'hospital_id',
                        'parent_transaction_id'  # CRITICAL: For "Back to Parent Invoice" button
                    ]

                    # Debug logging BEFORE conversion
                    logger.info(f"🔍 [UUID_DEBUG] BEFORE conversion - parent_transaction_id: {invoice_data.get('parent_transaction_id')} (type: {type(invoice_data.get('parent_transaction_id'))})")

                    for field in uuid_fields:
                        if field in invoice_data and invoice_data[field] is not None:
                            original_value = invoice_data[field]
                            # Convert UUID to string
                            invoice_data[field] = str(invoice_data[field])

                            if field == 'parent_transaction_id':
                                logger.info(f"🔍 [UUID_DEBUG] Converted parent_transaction_id from {original_value} ({type(original_value)}) to {invoice_data[field]} ({type(invoice_data[field])})")

                    # Compute has_free_items and has_sample_items virtual fields
                    invoice_data = self._compute_free_sample_flags(session, invoice_uuid, invoice_data)

                    logger.info(f"Retrieved invoice {item_id} from view with payment_status={invoice_data.get('payment_status')}, parent_transaction_id={invoice_data.get('parent_transaction_id')}")
                    return invoice_data
                else:
                    logger.warning(f"Invoice {item_id} not found in view")
                    return None

        except Exception as e:
            logger.error(f"Error getting invoice by ID {item_id}: {str(e)}", exc_info=True)
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Hospital ID: {kwargs.get('hospital_id')}")
            return None

    # =========================================================================
    # CUSTOM RENDERER CONTEXT FUNCTIONS
    # =========================================================================

    def get_invoice_lines(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice line items for custom renderer display

        This method is called by the Universal Engine to populate the
        invoice_lines_display custom renderer in the detail view.

        Args:
            item_id: Invoice ID (when called with explicit ID)
            item: Invoice dict (when called from template context)
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with line items data:
            {
                'items': [list of line items],
                'summary': {totals},
                'has_items': bool,
                'currency_symbol': '₹'
            }
        """
        try:
            # Parameter resolution - get invoice_id from either source
            if item_id:
                invoice_id = item_id
            elif item and isinstance(item, dict) and 'invoice_id' in item:
                invoice_id = item['invoice_id']
            else:
                return self._empty_line_items_result('No invoice ID provided')

            with get_db_session() as session:
                # Convert to UUID if needed
                invoice_uuid = uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Query invoice header
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == invoice_uuid,
                    InvoiceHeader.hospital_id == hospital_uuid
                ).first()

                if not invoice:
                    return self._empty_line_items_result('Invoice not found')

                # Query line items
                line_items = session.query(InvoiceLineItem).filter(
                    InvoiceLineItem.invoice_id == invoice_uuid
                ).order_by(InvoiceLineItem.created_at).all()

                if not line_items:
                    return self._empty_line_items_result('No line items found')

                # Convert line items to dicts
                items_list = []
                summary = {
                    'total_quantity': 0,
                    'total_amount': Decimal('0'),
                    'total_discount': Decimal('0'),
                    'total_taxable': Decimal('0'),
                    'total_gst': Decimal('0'),
                    'grand_total': Decimal('0')
                }

                for item in line_items:
                    # Calculate individual GST amounts
                    cgst_amt = float(item.cgst_amount or 0)
                    sgst_amt = float(item.sgst_amount or 0)
                    igst_amt = float(item.igst_amount or 0)

                    # Calculate GST rate percentage (for display)
                    cgst_rate = float(item.cgst_rate or 0)
                    sgst_rate = float(item.sgst_rate or 0)
                    igst_rate = float(item.igst_rate or 0)

                    # Total GST% = CGST% + SGST% (intrastate) or IGST% (interstate)
                    gst_rate = igst_rate if igst_rate > 0 else (cgst_rate + sgst_rate)

                    item_dict = {
                        'line_item_id': str(item.line_item_id),
                        'item_type': item.item_type,
                        'item_name': item.item_name,
                        'hsn_sac_code': item.hsn_sac_code,
                        'batch': item.batch,
                        'expiry_date': item.expiry_date.strftime('%d-%b-%Y') if item.expiry_date else None,
                        'quantity': float(item.quantity or 0),
                        'unit_price': float(item.unit_price or 0),
                        'discount_percent': float(item.discount_percent or 0),
                        'discount_amount': float(item.discount_amount or 0),
                        'taxable_amount': float(item.taxable_amount or 0),  # FIXED: was taxable_value
                        'cgst_rate': cgst_rate,
                        'sgst_rate': sgst_rate,
                        'igst_rate': igst_rate,
                        'gst_rate': gst_rate,  # ADDED: Total GST% for template display
                        'cgst_amount': cgst_amt,
                        'sgst_amount': sgst_amt,
                        'igst_amount': igst_amt,
                        'gst_amount': cgst_amt + sgst_amt + igst_amt,  # ADDED: Total GST for template
                        'line_total': float(item.line_total or 0),  # FIXED: was total_amount
                        # Prescription consolidation metadata
                        'is_prescription_item': item.is_prescription_item or False,
                        'consolidation_group_id': str(item.consolidation_group_id) if item.consolidation_group_id else None,
                        'print_as_consolidated': item.print_as_consolidated or False,
                        # Free Item support (promotional - GST on MRP, 100% discount)
                        'is_free_item': item.is_free_item or False,
                        'free_item_reason': item.free_item_reason or '',
                        # Sample/Trial item support (no GST, no charge)
                        'is_sample': item.is_sample or False,
                        'sample_reason': item.sample_reason or ''
                    }

                    items_list.append(item_dict)

                    # Update summary
                    summary['total_quantity'] += item_dict['quantity']
                    # DO NOT add pre-discount amount here - only use line_total
                    summary['total_discount'] += Decimal(str(item_dict['discount_amount']))
                    summary['total_taxable'] += Decimal(str(item_dict['taxable_amount']))
                    summary['total_gst'] += Decimal(str(
                        item_dict['cgst_amount'] +
                        item_dict['sgst_amount'] +
                        item_dict['igst_amount']
                    ))
                    summary['total_amount'] += Decimal(str(item_dict['line_total']))

                # Convert summary decimals to float for JSON serialization
                summary_float = {
                    'total_quantity': float(summary['total_quantity']),
                    'total_amount': float(summary['total_amount']),
                    'total_discount': float(summary['total_discount']),
                    'total_taxable': float(summary['total_taxable']),
                    'subtotal': float(summary['total_taxable']),  # Subtotal = taxable amount (before GST)
                    'total_gst': float(summary['total_gst']),
                    'grand_total': float(invoice.grand_total or 0)
                }

                # Analyze invoice items to determine if it contains medicines
                # (for conditional display of batch/expiry columns)
                # NOTE: item_type values include: 'Package', 'Service', 'Medicine', 'Prescription', 'OTC', 'Product', 'Consumable'
                # Check all items and log their types for debugging
                item_types_found = [item.get('item_type') for item in items_list]
                has_medicine_items = any(
                    item.get('item_type') in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']
                    for item in items_list
                )

                logger.info(f"📦 Invoice {invoice_id}: Found item types: {set(item_types_found)}, has_medicine_items: {has_medicine_items}")

                # Additional check: if any item has batch or expiry data, it's likely a medicine
                # This handles edge cases where item_type might be incorrectly set
                has_batch_expiry_data = any(
                    item.get('batch') or item.get('expiry_date')
                    for item in items_list
                )

                if has_batch_expiry_data and not has_medicine_items:
                    logger.warning(f"⚠️ Invoice {invoice_id}: Found batch/expiry data but no medicine item_type. Forcing has_medicine_items=True")
                    has_medicine_items = True

                # FALLBACK: For split invoices, check invoice_type
                # invoice_type "Product" is used for both GST and GST-exempt medicine invoices
                if not has_medicine_items and invoice.invoice_type == 'Product':
                    logger.info(f"📦 Invoice {invoice_id}: invoice_type is 'Product', setting has_medicine_items=True")
                    has_medicine_items = True

                # Calculate consolidated group metadata
                consolidated_groups = {}
                for item in items_list:
                    if item['consolidation_group_id']:
                        group_id = item['consolidation_group_id']
                        if group_id not in consolidated_groups:
                            consolidated_groups[group_id] = {
                                'group_id': group_id,
                                'item_count': 0,
                                'total_amount': 0,
                                'print_as_consolidated': item['print_as_consolidated'],
                                'items': []
                            }
                        consolidated_groups[group_id]['item_count'] += 1
                        consolidated_groups[group_id]['total_amount'] += item['line_total']
                        consolidated_groups[group_id]['items'].append(item)

                # Debug logging
                logger.info(f"🔍 consolidated_groups type: {type(consolidated_groups)}")
                logger.info(f"🔍 consolidated_groups value: {consolidated_groups}")
                logger.info(f"🔍 has_consolidated_groups: {len(consolidated_groups) > 0}")
                logger.info(f"🔍 has_medicine_items: {has_medicine_items}")

                result = {
                    'items': items_list,
                    'summary': summary_float,
                    'has_items': True,
                    'currency_symbol': '₹',
                    'invoice_type': invoice.invoice_type,
                    'is_gst_invoice': invoice.is_gst_invoice,
                    'entity_type': 'invoice',  # Mark as invoice for batch/expiry display
                    'has_medicine_items': has_medicine_items,  # Flag for conditional batch/expiry display
                    # Consolidated group metadata for template
                    'consolidated_groups': consolidated_groups,
                    'has_consolidated_groups': len(consolidated_groups) > 0
                }

                # Verify the result before returning
                logger.info(f"🔍 Returning result with consolidated_groups type: {type(result['consolidated_groups'])}")

                return result

        except Exception as e:
            logger.error(f"Error getting invoice line items: {str(e)}", exc_info=True)
            return self._empty_line_items_result(f'Error: {str(e)}')

    def get_payment_history(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get payment history for custom renderer display

        This method is called by the Universal Engine to populate the
        payment_history_display custom renderer in the detail view.

        Args:
            item_id: Invoice ID (when called with explicit ID)
            item: Invoice dict (when called from template context)
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with payment history data:
            {
                'payments': [list of payments],
                'summary': {totals},
                'has_payments': bool,
                'currency_symbol': '₹'
            }
        """
        try:
            # Parameter resolution - get invoice_id from either source
            if item_id:
                invoice_id = item_id
            elif item and isinstance(item, dict) and 'invoice_id' in item:
                invoice_id = item['invoice_id']
            else:
                return self._empty_payment_history_result('No invoice ID provided')

            with get_db_session() as session:
                # Convert to UUID if needed
                invoice_uuid = uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Query invoice to get basic info
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == invoice_uuid,
                    InvoiceHeader.hospital_id == hospital_uuid
                ).first()

                if not invoice:
                    return self._empty_payment_history_result('Invoice not found')

                # DUAL-PATH LOGIC: Support both single-invoice and multi-invoice payments
                # Path 1: Direct invoice_id link (for single-invoice payments)
                # Path 2: AR subledger traversal (for multi-invoice payments)

                # Try Path 1 first: Direct invoice_id relationship
                payments_data = session.query(PatientPaymentReceiptView).filter(
                    PatientPaymentReceiptView.invoice_id == invoice_uuid,
                    PatientPaymentReceiptView.hospital_id == hospital_uuid
                ).order_by(PatientPaymentReceiptView.payment_date.desc()).all()

                # If no direct payments found, try Path 2: AR subledger traversal via LINE ITEMS
                ar_payment_ids = []
                if not payments_data:
                    # Multi-invoice payments store AR entries at LINE ITEM level
                    # Step 1: Get all line items for this invoice
                    from app.models.transaction import InvoiceLineItem
                    line_items = session.query(InvoiceLineItem).filter(
                        InvoiceLineItem.invoice_id == invoice_uuid
                    ).all()

                    if line_items:
                        line_item_ids = [li.line_item_id for li in line_items]

                        # Step 2: Find AR payment entries that reference these line items
                        # Include both regular payments and installment payments
                        ar_payments = session.query(ARSubledger).filter(
                            ARSubledger.hospital_id == hospital_uuid,
                            ARSubledger.entry_type == 'payment',
                            ARSubledger.reference_type.in_(['payment', 'installment_payment']),  # Include installment payments
                            ARSubledger.reference_line_item_id.in_(line_item_ids)
                        ).all()

                        if ar_payments:
                            # Step 3: Get unique payment IDs
                            ar_payment_ids = list(set([p.reference_id for p in ar_payments]))

                            # Step 4: Query payment details from payment_details table directly
                            # (these will have invoice_id = NULL for multi-invoice payments)
                            from app.models.transaction import PaymentDetail
                            payments_raw = session.query(PaymentDetail).filter(
                                PaymentDetail.payment_id.in_(ar_payment_ids),
                                PaymentDetail.hospital_id == hospital_uuid
                            ).order_by(PaymentDetail.payment_date.desc()).all()

                            # Step 5: Convert to dict format similar to view
                            payments_data = []
                            for p in payments_raw:
                                payments_data.append(type('obj', (object,), {
                                    'payment_id': p.payment_id,
                                    'payment_date': p.payment_date,
                                    'payment_method_primary': self._get_primary_payment_method(p),
                                    'total_amount': p.total_amount,
                                    'reference_number': p.reference_number,
                                    'receipt_number': p.reference_number,  # Fallback
                                    'workflow_status': p.workflow_status,
                                    'created_by': p.created_by if hasattr(p, 'created_by') else '',
                                    'created_at': p.created_at if hasattr(p, 'created_at') else None,
                                    'notes': p.notes if hasattr(p, 'notes') else ''
                                })())

                if not payments_data:
                    # Check if invoice appears to be paid but has no payment records
                    if invoice.paid_amount and invoice.paid_amount > 0:
                        return self._empty_payment_history_result(
                            f'Invoice shows paid amount of ₹{invoice.paid_amount:.2f} but payment records are not linked. '
                            'AR subledger entries may be missing.'
                        )
                    return self._empty_payment_history_result('No payments recorded for this invoice')

                # Build payments list
                payments_list = []
                summary = {
                    'total_paid': Decimal('0'),
                    'payment_count': len(payments_data)
                }

                for payment in payments_data:
                    # Calculate allocated amount for THIS invoice
                    # For single-invoice payments: use total_amount
                    # For multi-invoice payments: sum AR entries for this invoice's line items

                    # Check if this is from Path 1 (direct link) or Path 2 (AR traversal)
                    if hasattr(payment, 'invoice_id') and payment.invoice_id == invoice_uuid:
                        # Path 1: Single-invoice payment - use total amount
                        allocated_amount = Decimal(str(payment.total_amount or 0))
                    else:
                        # Path 2: Multi-invoice payment - calculate from AR entries
                        # Get line items for this invoice again
                        from app.models.transaction import InvoiceLineItem
                        invoice_line_items = session.query(InvoiceLineItem.line_item_id).filter(
                            InvoiceLineItem.invoice_id == invoice_uuid
                        ).all()
                        invoice_line_item_ids = [li[0] for li in invoice_line_items]

                        # Sum AR credit entries for this payment that reference this invoice's line items
                        # Include both regular payments and installment payments
                        ar_credits = session.query(ARSubledger).filter(
                            and_(
                                ARSubledger.reference_id == payment.payment_id,
                                ARSubledger.reference_type.in_(['payment', 'installment_payment']),  # Include installment payments
                                ARSubledger.entry_type == 'payment',
                                ARSubledger.reference_line_item_id.in_(invoice_line_item_ids)
                            )
                        ).all()

                        allocated_amount = sum([ar.credit_amount or Decimal('0') for ar in ar_credits])

                    payment_dict = {
                        'payment_id': str(payment.payment_id),
                        'payment_date': payment.payment_date,
                        'payment_method': payment.payment_method_primary,
                        'allocated_amount': float(allocated_amount),  # Amount allocated to THIS invoice
                        'total_amount': float(payment.total_amount or 0),  # Total payment amount
                        'reference_no': getattr(payment, 'reference_number', None) or f"PMT-{str(payment.payment_id)[:8]}",
                        'notes': getattr(payment, 'notes', '') or '',
                        # Status
                        'workflow_status': payment.workflow_status,
                        'is_partial': allocated_amount < Decimal(str(payment.total_amount or 0)),
                        # Audit
                        'created_by': getattr(payment, 'created_by', '') or '',
                        'created_at': getattr(payment, 'created_at', None)
                    }

                    payments_list.append(payment_dict)
                    summary['total_paid'] += allocated_amount

                # Build invoice summary
                invoice_summary = {
                    'invoice_number': invoice.invoice_number,
                    'invoice_date': invoice.invoice_date,
                    'grand_total': float(invoice.grand_total or 0),
                    'paid_amount': float(invoice.paid_amount or 0),
                    'balance_due': float(invoice.balance_due or 0),
                    'is_fully_paid': float(invoice.balance_due or 0) <= 0.01
                }

                return {
                    'payments': payments_list,
                    'summary': {
                        'total_paid': float(summary['total_paid']),
                        'payment_count': summary['payment_count']
                    },
                    'invoice_summary': invoice_summary,
                    'has_history': True,  # Changed from has_payments to match template
                    'has_payments': True,  # Keep for backward compatibility
                    'currency_symbol': '₹',
                    'entity_type': 'patient_payments',  # For template links
                    'total_payments': summary['payment_count'],
                    'total_amount': float(summary['total_paid'])
                }

        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}", exc_info=True)
            return self._empty_payment_history_result(f'Error: {str(e)}')

    def get_child_invoices(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get child invoices for parent invoice (for custom renderer)

        This method is called by the Universal Engine to populate the
        child_invoices_display custom renderer in the Split Invoices tab.

        Args:
            item_id: Parent invoice ID (when called with explicit ID)
            item: Parent invoice dict (when called from template context)
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with child invoices data:
            {
                'children': [list of child invoice dicts],
                'count': int,
                'total_amount': float,
                'total_paid': float,
                'total_balance': float,
                'has_children': bool
            }
        """
        try:
            # Parameter resolution - get invoice_id from either source
            if item_id:
                invoice_id = item_id
            elif item and isinstance(item, dict) and 'invoice_id' in item:
                invoice_id = item['invoice_id']
            else:
                return {
                    'children': [],
                    'count': 0,
                    'has_children': False,
                    'error': 'No invoice ID provided'
                }

            with get_db_session() as session:
                # Convert to UUID if needed
                invoice_uuid = uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id
                hospital_id = kwargs.get('hospital_id')
                hospital_uuid = uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

                # Query child invoices using PatientInvoiceView
                from app.models.views import PatientInvoiceView

                query = session.query(PatientInvoiceView).filter(
                    PatientInvoiceView.parent_transaction_id == invoice_uuid,
                    PatientInvoiceView.hospital_id == hospital_uuid
                ).order_by(PatientInvoiceView.split_sequence)

                children = query.all()

                if not children:
                    return {
                        'children': [],
                        'count': 0,
                        'total_amount': 0,
                        'total_paid': 0,
                        'total_balance': 0,
                        'has_children': False
                    }

                # Convert to dicts using get_entity_dict
                from app.services.database_service import get_entity_dict
                children_data = [get_entity_dict(child) for child in children]

                # Calculate totals
                total_amount = sum(float(child.grand_total or 0) for child in children)
                total_paid = sum(float(child.paid_amount or 0) for child in children)
                total_balance = sum(float(child.balance_due or 0) for child in children)

                return {
                    'children': children_data,
                    'count': len(children),
                    'total_amount': total_amount,
                    'total_paid': total_paid,
                    'total_balance': total_balance,
                    'has_children': True,
                    'currency_symbol': '₹'
                }

        except Exception as e:
            logger.error(f"Error loading child invoices: {str(e)}", exc_info=True)
            return {
                'children': [],
                'count': 0,
                'error': str(e),
                'has_children': False
            }

    # =========================================================================
    # BACKWARD COMPATIBILITY WRAPPERS
    # =========================================================================

    def create_invoice(self, hospital_id: uuid.UUID, branch_id: uuid.UUID,
                      patient_id: uuid.UUID, invoice_date: datetime,
                      line_items: List[Dict], notes: Optional[str] = None,
                      current_user_id: Optional[str] = None) -> Dict:
        """
        Wrapper for existing create_invoice function
        Maintains backward compatibility with existing code
        """
        return billing_service.create_invoice(
            hospital_id=hospital_id,
            branch_id=branch_id,
            patient_id=patient_id,
            invoice_date=invoice_date,
            line_items=line_items,
            notes=notes,
            current_user_id=current_user_id
        )

    def record_payment(self, invoice_id: uuid.UUID, hospital_id: uuid.UUID,
                      branch_id: uuid.UUID, payment_date: datetime,
                      amount: Decimal, payment_method: str,
                      **kwargs) -> Dict:
        """
        Wrapper for existing record_payment function
        Maintains backward compatibility with existing code
        """
        return billing_service.record_payment(
            invoice_id=invoice_id,
            hospital_id=hospital_id,
            branch_id=branch_id,
            payment_date=payment_date,
            amount=amount,
            payment_method=payment_method,
            **kwargs
        )

    def void_invoice(self, invoice_id: uuid.UUID, hospital_id: uuid.UUID,
                    reason: str, current_user_id: Optional[str] = None) -> Dict:
        """
        Wrapper for existing void_invoice function
        Maintains backward compatibility with existing code
        """
        return billing_service.void_invoice(
            invoice_id=invoice_id,
            hospital_id=hospital_id,
            reason=reason,
            current_user_id=current_user_id
        )

    def search_invoices(self, hospital_id: uuid.UUID, filters: Dict = None,
                       page: int = 1, per_page: int = 20, **kwargs) -> Dict:
        """
        Wrapper for existing search_invoices function
        Maintains backward compatibility with existing code

        Note: Universal Engine calls search_data() instead
        This is here for backward compatibility with existing views
        """
        return billing_service.search_invoices(
            hospital_id=hospital_id,
            filters=filters,
            page=page,
            per_page=per_page,
            **kwargs
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _compute_free_sample_flags(self, session, invoice_uuid: uuid.UUID, invoice_data: Dict) -> Dict:
        """
        Compute has_free_items and has_sample_items virtual fields for a single invoice.
        Used by get_by_id for detail view display.
        """
        try:
            # Query to check if invoice has any free items
            has_free = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.invoice_id == invoice_uuid,
                InvoiceLineItem.is_free_item == True
            ).first() is not None

            # Query to check if invoice has any sample items
            has_sample = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.invoice_id == invoice_uuid,
                InvoiceLineItem.is_sample == True
            ).first() is not None

            invoice_data['has_free_items'] = 'true' if has_free else 'false'
            invoice_data['has_sample_items'] = 'true' if has_sample else 'false'

            logger.debug(f"Computed free/sample flags for invoice {invoice_uuid}: "
                        f"has_free_items={invoice_data['has_free_items']}, "
                        f"has_sample_items={invoice_data['has_sample_items']}")

        except Exception as e:
            logger.error(f"Error computing free/sample flags: {str(e)}")
            invoice_data['has_free_items'] = 'false'
            invoice_data['has_sample_items'] = 'false'

        return invoice_data

    def _empty_line_items_result(self, message: str = '') -> Dict:
        """Return empty result structure for line items"""
        return {
            'items': [],
            'summary': {
                'total_quantity': 0,
                'total_amount': 0,
                'total_discount': 0,
                'total_taxable': 0,
                'total_gst': 0,
                'grand_total': 0
            },
            'has_items': False,
            'currency_symbol': '₹',
            'entity_type': 'invoice',
            'has_medicine_items': False,  # No items means no medicine items
            'message': message,
            # Consolidated group metadata (empty for no items)
            'consolidated_groups': {},
            'has_consolidated_groups': False
        }

    def _get_primary_payment_method(self, payment) -> str:
        """Determine primary payment method from payment record"""
        cash = Decimal(str(payment.cash_amount or 0))
        credit_card = Decimal(str(payment.credit_card_amount or 0))
        debit_card = Decimal(str(payment.debit_card_amount or 0))
        upi = Decimal(str(payment.upi_amount or 0))

        # Single payment method
        if cash > 0 and credit_card == 0 and debit_card == 0 and upi == 0:
            return 'Cash'
        elif credit_card > 0 and cash == 0 and debit_card == 0 and upi == 0:
            return 'Credit Card'
        elif debit_card > 0 and cash == 0 and credit_card == 0 and upi == 0:
            return 'Debit Card'
        elif upi > 0 and cash == 0 and credit_card == 0 and debit_card == 0:
            return 'UPI'
        else:
            return 'Multiple'

    def get_patient_payment_history(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get patient's payment history for the last 6 months

        Args:
            item_id: Invoice ID (to extract patient_id from)
            item: Invoice dict (when called from template context)
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with patient payment history data for last 6 months
        """
        try:
            from datetime import datetime, timedelta
            from app.models.views import PatientPaymentReceiptView

            # Get invoice_id to extract patient_id
            if item_id:
                invoice_id = item_id
            elif item and isinstance(item, dict) and 'invoice_id' in item:
                invoice_id = item['invoice_id']
            else:
                return self._empty_payment_history_result('No invoice ID provided')

            with get_db_session() as session:
                # Convert to UUID
                invoice_uuid = uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Get patient_id from invoice
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == invoice_uuid,
                    InvoiceHeader.hospital_id == hospital_uuid
                ).first()

                if not invoice:
                    return self._empty_payment_history_result('Invoice not found')

                patient_id = invoice.patient_id

                # Get patient name - query from Patient model
                from app.models.master import Patient
                patient = session.query(Patient).filter(
                    Patient.patient_id == patient_id
                ).first()

                if patient:
                    patient_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
                else:
                    patient_name = 'Unknown Patient'

                # Calculate 6 months ago
                six_months_ago = datetime.now() - timedelta(days=180)

                # Query all payments for this patient in last 6 months
                payments_data = session.query(PatientPaymentReceiptView).filter(
                    PatientPaymentReceiptView.patient_id == patient_id,
                    PatientPaymentReceiptView.hospital_id == hospital_uuid,
                    PatientPaymentReceiptView.payment_date >= six_months_ago
                ).order_by(PatientPaymentReceiptView.payment_date.desc()).all()

                if not payments_data:
                    return {
                        'payments': [],
                        'summary': {'total_paid': 0, 'payment_count': 0},
                        'has_payments': False,
                        'currency_symbol': '₹',
                        'patient_name': patient_name,
                        'date_range': f"{six_months_ago.strftime('%d-%b-%Y')} to {datetime.now().strftime('%d-%b-%Y')}",
                        'message': 'No payments in last 6 months'
                    }

                # Convert to dicts
                payments_list = []
                total_paid = 0

                for payment in payments_data:
                    payment_dict = {
                        'payment_id': str(payment.payment_id),
                        'receipt_number': payment.reference_number or f"PAY-{str(payment.payment_id)[:8]}",
                        'payment_date': payment.payment_date.strftime('%d-%b-%Y') if payment.payment_date else '',
                        'invoice_number': payment.invoice_number or '-',
                        'invoice_id': str(payment.invoice_id) if payment.invoice_id else None,
                        'amount': float(payment.total_amount) if payment.total_amount else 0.0,
                        'payment_mode': payment.payment_method_primary or 'Cash',
                        'notes': payment.notes or '',
                        'status': payment.workflow_status or 'completed'
                    }
                    payments_list.append(payment_dict)
                    total_paid += payment_dict['amount']

                return {
                    'payments': payments_list,
                    'summary': {'total_paid': total_paid, 'payment_count': len(payments_list)},
                    'has_payments': True,
                    'currency_symbol': '₹',
                    'patient_name': patient_name,
                    'date_range': f"{six_months_ago.strftime('%d-%b-%Y')} to {datetime.now().strftime('%d-%b-%Y')}"
                }

        except Exception as e:
            logger.error(f"Error fetching patient payment history: {str(e)}", exc_info=True)
            return self._empty_payment_history_result(f'Error: {str(e)}')

    def _empty_payment_history_result(self, message: str = '') -> Dict:
        """Return empty result structure for payment history"""
        return {
            'payments': [],
            'summary': {
                'total_paid': 0,
                'payment_count': 0
            },
            'invoice_summary': {},
            'has_history': False,  # Changed from has_payments to match template
            'has_payments': False,  # Keep for backward compatibility
            'currency_symbol': '₹',
            'message': message
        }


# =============================================================================
# MODULE-LEVEL INSTANCE (Singleton pattern)
# =============================================================================

# Create a module-level instance for easy import
_service_instance = None


def get_patient_invoice_service() -> PatientInvoiceService:
    """
    Get singleton instance of PatientInvoiceService

    Usage:
        from app.services.patient_invoice_service import get_patient_invoice_service

        service = get_patient_invoice_service()
        invoices = service.search_data(filters, hospital_id=hospital_id)
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = PatientInvoiceService()
    return _service_instance


# =============================================================================
# BACKWARD COMPATIBILITY EXPORTS
# =============================================================================

# Export the service instance and key methods for easy access
patient_invoice_service = get_patient_invoice_service()

# Export common methods at module level for convenience
search_invoices = patient_invoice_service.search_invoices
get_invoice_by_id = patient_invoice_service.get_by_id
create_invoice = patient_invoice_service.create_invoice
record_payment = patient_invoice_service.record_payment
void_invoice = patient_invoice_service.void_invoice
