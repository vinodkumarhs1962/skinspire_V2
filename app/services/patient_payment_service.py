# File: app/services/patient_payment_service.py

"""
Patient Payment Service - Universal Engine integration
Extends UniversalEntityService for generic functionality
Contains only payment-specific context functions for custom renderers
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from flask_login import current_user
from sqlalchemy import or_, and_, desc, func
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.transaction import PaymentDetail, InvoiceHeader, ARSubledger, InvoiceLineItem, InstallmentPayment
from app.models.master import Patient
from app.models.views import PatientPaymentReceiptView
from app.engine.universal_entity_service import UniversalEntityService
from app.engine.business.line_items_handler import line_items_handler
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class PatientPaymentService(UniversalEntityService):
    """
    Patient payment service for Universal Engine
    Inherits search_data() and get_by_id() from UniversalEntityService
    Implements only custom renderer context functions
    """

    def __init__(self):
        """Initialize with PatientPaymentReceiptView model"""
        super().__init__('patient_payments', PatientPaymentReceiptView)
        logger.info("✅ Initialized PatientPaymentService with PatientPaymentReceiptView")

    # ==========================================================================
    # CONTEXT FUNCTIONS FOR CUSTOM RENDERERS
    # ==========================================================================

    def get_invoice_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice line items for this payment (MANY-TO-MANY)
        Shows aggregated line items from ALL invoices paid by this payment
        Queries ar_subledger to get all invoice allocations

        Args:
            item_id: Payment ID (when called from template)
            item: Payment data dict
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with aggregated invoice line items from all allocated invoices
        """
        try:
            # Parameter resolution
            if item_id:
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                payment_id = item['payment_id']
            else:
                return line_items_handler._empty_result('invoice', 'No payment ID found')

            # Convert IDs to UUID
            payment_uuid = uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
            hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

            # Get invoice IDs in a separate session scope
            with get_db_session() as session:
                # Query ar_subledger to get all LINE ITEMS paid by this payment
                # For multi-invoice payments, reference_line_item_id points to invoice line items
                ar_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == hospital_uuid,
                    ARSubledger.reference_id == payment_uuid,
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.reference_line_item_id.isnot(None)  # Only entries with line item reference
                ).all()

                if not ar_entries:
                    return line_items_handler._empty_result('invoice', 'No invoice allocations found for this payment')

                # Get all UNIQUE invoice IDs from the line items
                invoice_ids = list(set(
                    session.query(InvoiceLineItem.invoice_id).filter(
                        InvoiceLineItem.line_item_id.in_([ar.reference_line_item_id for ar in ar_entries])
                    ).distinct()
                ))
                invoice_ids = [inv_id[0] for inv_id in invoice_ids]  # Extract from tuples
            # Session closed here

            # Now aggregate line items from all invoices (each call creates its own session)
            all_items = []
            all_invoices = []
            total_subtotal = Decimal(0)
            total_discount = Decimal(0)
            total_gst = Decimal(0)
            total_grand_total = Decimal(0)

            for invoice_id in invoice_ids:
                # Get line items for each invoice (creates its own session)
                invoice_data = line_items_handler.get_patient_invoice_line_items(
                    invoice_id=invoice_id,
                    context='payment_invoice',
                    **kwargs
                )

                if invoice_data.get('has_items'):
                    # Add invoice separator info to items
                    invoice_info = invoice_data.get('header_info', {})
                    all_invoices.append(invoice_info)

                    # Add items with invoice reference
                    for item in invoice_data.get('items', []):
                        item['invoice_number'] = invoice_info.get('number')
                        item['invoice_date'] = invoice_info.get('date')
                        all_items.append(item)

                    # Aggregate totals
                    summary = invoice_data.get('summary', {})
                    total_subtotal += Decimal(str(summary.get('subtotal', 0)))
                    total_discount += Decimal(str(summary.get('total_discount', 0)))
                    total_gst += Decimal(str(summary.get('total_gst', 0)))
                    total_grand_total += Decimal(str(summary.get('grand_total', 0)))

            return {
                'items': all_items,
                'has_items': len(all_items) > 0,
                'entity_type': 'invoice',
                'currency_symbol': '₹',
                'summary': {
                    'line_count': len(all_items),
                    'subtotal': float(total_subtotal),
                    'total_discount': float(total_discount),
                    'total_gst': float(total_gst),
                    'grand_total': float(total_grand_total)
                },
                'context': 'payment_invoice_many_to_many',
                'has_medicine_items': any(item.get('item_type') == 'Medicine' for item in all_items),
                'invoice_count': len(invoice_ids),
                'invoices': all_invoices,
                'is_multi_invoice': len(invoice_ids) > 1
            }

        except Exception as e:
            logger.error(f"Error getting invoice items for payment: {e}", exc_info=True)
            return line_items_handler._empty_result('invoice', f'Error: {str(e)}')

    def get_payment_workflow_timeline(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get workflow timeline for payment approval process
        Returns data for the workflow timeline custom renderer

        Args:
            item_id: Payment ID (when called from template)
            item: Payment data dict
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with workflow timeline steps
        """
        try:
            # Parameter resolution
            if item_id:
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                payment_id = item['payment_id']
            else:
                return {'steps': [], 'has_timeline': False, 'error': 'No payment ID found'}

            with get_db_session() as session:
                # Convert IDs to UUID
                payment_uuid = uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Query payment from PaymentDetail table
                payment = session.query(PaymentDetail).filter(
                    PaymentDetail.payment_id == payment_uuid,
                    PaymentDetail.hospital_id == hospital_uuid
                ).first()

                if not payment:
                    return {'steps': [], 'current_status': 'unknown', 'has_timeline': False}

                # Build workflow timeline
                steps = []

                # Step 1: Created
                steps.append({
                    'title': 'Payment Created',
                    'status': 'completed',
                    'timestamp': payment.created_at,
                    'user': payment.created_by,
                    'icon': 'fas fa-plus-circle',
                    'color': 'success',
                    'description': f'Payment of ₹{payment.total_amount:,.2f} created'
                })

                # Step 2: Submitted for Approval (if applicable)
                if payment.submitted_at:
                    steps.append({
                        'title': 'Submitted for Approval',
                        'status': 'completed',
                        'timestamp': payment.submitted_at,
                        'user': payment.submitted_by or payment.created_by,
                        'icon': 'fas fa-paper-plane',
                        'color': 'info',
                        'description': 'Payment submitted for approval'
                    })

                # Step 3: Current Status based on workflow_status
                if payment.workflow_status == 'pending_approval':
                    steps.append({
                        'title': 'Awaiting Approval',
                        'status': 'pending',
                        'timestamp': None,
                        'user': None,
                        'icon': 'fas fa-clock',
                        'color': 'warning',
                        'description': 'Payment is pending approval'
                    })

                elif payment.workflow_status == 'approved' and payment.approved_at:
                    steps.append({
                        'title': 'Payment Approved',
                        'status': 'completed',
                        'timestamp': payment.approved_at,
                        'user': payment.approved_by,
                        'icon': 'fas fa-check-circle',
                        'color': 'success',
                        'description': 'Payment has been approved'
                    })

                elif payment.workflow_status == 'rejected' and payment.rejected_at:
                    steps.append({
                        'title': 'Payment Rejected',
                        'status': 'rejected',
                        'timestamp': payment.rejected_at,
                        'user': payment.rejected_by,
                        'icon': 'fas fa-times-circle',
                        'color': 'danger',
                        'description': 'Payment has been rejected',
                        'notes': payment.rejection_reason
                    })

                # Step 4: GL Posted
                if payment.gl_posted and payment.posting_date:
                    steps.append({
                        'title': 'GL Posted',
                        'status': 'completed',
                        'timestamp': payment.posting_date,
                        'user': payment.updated_by,
                        'icon': 'fas fa-book',
                        'color': 'info',
                        'description': 'General ledger entries posted'
                    })

                # Step 5: Reversed (if applicable)
                if payment.workflow_status == 'reversed':
                    steps.append({
                        'title': 'Payment Reversed',
                        'status': 'reversed',
                        'timestamp': payment.updated_at,
                        'user': payment.updated_by,
                        'icon': 'fas fa-undo',
                        'color': 'warning',
                        'description': 'Payment has been reversed'
                    })

                # Step 6: Reconciliation (if applicable)
                if payment.reconciliation_status == 'reconciled' and payment.reconciliation_date:
                    steps.append({
                        'title': 'Payment Reconciled',
                        'status': 'completed',
                        'timestamp': payment.reconciliation_date,
                        'user': payment.updated_by,
                        'icon': 'fas fa-balance-scale',
                        'color': 'info',
                        'description': 'Payment reconciled with bank statement'
                    })

                # Step 7: Refund (if applicable)
                if payment.refunded_amount and payment.refunded_amount > 0:
                    steps.append({
                        'title': 'Refund Processed',
                        'status': 'completed',
                        'timestamp': payment.refund_date,
                        'user': payment.updated_by,
                        'icon': 'fas fa-money-check-alt',
                        'color': 'warning',
                        'description': f'Refund of ₹{payment.refunded_amount:,.2f} processed',
                        'notes': payment.refund_reason
                    })

                return {
                    'steps': steps,
                    'current_status': payment.workflow_status,
                    'has_timeline': True,
                    'workflow_status': payment.workflow_status,
                    'requires_approval': payment.requires_approval,
                    'is_reversed': (payment.workflow_status == 'reversed'),
                    'has_refund': (payment.refunded_amount and payment.refunded_amount > 0)
                }

        except Exception as e:
            logger.error(f"Error getting workflow timeline: {e}", exc_info=True)
            return {
                'steps': [],
                'current_status': 'error',
                'has_timeline': False,
                'error': str(e)
            }

    def get_patient_payment_history(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get payment history for the patient
        Returns data for payment history custom renderer

        Args:
            item_id: Payment ID (when called from template)
            item: Payment data dict
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with patient payment history
        """
        try:
            # Get patient ID from payment
            patient_id = None
            if item and isinstance(item, dict):
                patient_id = item.get('patient_id')
            elif item_id:
                # Fetch payment to get patient_id
                with get_db_session() as session:
                    payment_uuid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id

                    # Query from view for patient_id
                    payment_view = session.query(PatientPaymentReceiptView).filter(
                        PatientPaymentReceiptView.payment_id == payment_uuid
                    ).first()

                    if payment_view:
                        patient_id = payment_view.patient_id

            if not patient_id:
                return {
                    'payments': [],
                    'summary': {
                        'total_paid': 0,
                        'payment_count': 0
                    },
                    'total_payments': 0,
                    'total_amount': 0,
                    'has_history': False,
                    'entity_type': 'patient_payments',
                    'currency_symbol': '₹',
                    'message': 'No patient ID found'
                }

            with get_db_session() as session:
                # Convert IDs to UUID
                patient_uuid = uuid.UUID(patient_id) if isinstance(patient_id, str) else patient_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Get patient payment history (last 6 months)
                six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

                payment_history = session.query(PatientPaymentReceiptView).filter(
                    PatientPaymentReceiptView.patient_id == patient_uuid,
                    PatientPaymentReceiptView.hospital_id == hospital_uuid,
                    PatientPaymentReceiptView.payment_date >= six_months_ago,
                    PatientPaymentReceiptView.is_deleted == False
                ).order_by(desc(PatientPaymentReceiptView.payment_date)).limit(10).all()

                payments = []
                total_amount = 0

                for payment in payment_history:
                    # Use payment_method_total which includes wallet + advance
                    payment_total = float(payment.payment_method_total or payment.total_amount or 0)
                    payment_dict = {
                        'payment_id': str(payment.payment_id),
                        'payment_date': payment.payment_date,
                        'reference_no': getattr(payment, 'reference_number', None) or f"PMT-{str(payment.payment_id)[:8]}",
                        'invoice_number': payment.invoice_number,
                        'total_amount': payment_total,  # ✅ Use payment_method_total (includes wallet + advance)
                        'allocated_amount': payment_total,  # ✅ Use payment_method_total
                        'payment_method': payment.payment_method_primary,
                        'workflow_status': payment.workflow_status,
                        'is_partial': False,  # Not applicable for payment history view
                        'is_reversed': (payment.workflow_status == 'reversed'),
                        'has_refund': (payment.refunded_amount and payment.refunded_amount > 0)
                    }
                    payments.append(payment_dict)

                    # Sum only approved, non-reversed payments
                    if payment.workflow_status == 'approved' and not (payment.workflow_status == 'reversed'):
                        total_amount += payment_total

                return {
                    'payments': payments,
                    'summary': {  # Match template expectation
                        'total_paid': total_amount,
                        'payment_count': len(payments)
                    },
                    'total_payments': len(payments),  # Keep for backward compatibility
                    'total_amount': total_amount,  # Keep for backward compatibility
                    'has_history': len(payments) > 0,
                    'period': '6 months',
                    'entity_type': 'patient_payments',
                    'currency_symbol': '₹'
                    # Note: No invoice_summary - template will handle this with conditional check
                }

        except Exception as e:
            logger.error(f"Error getting patient payment history: {e}", exc_info=True)
            return {
                'payments': [],
                'summary': {
                    'total_paid': 0,
                    'payment_count': 0
                },
                'total_payments': 0,
                'total_amount': 0,
                'has_history': False,
                'entity_type': 'patient_payments',
                'currency_symbol': '₹',
                'message': f'Error: {str(e)}'
            }

    def get_payment_invoice_allocations(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice allocations for this payment from ar_subledger
        Handles many-to-many relationship: one payment can pay multiple invoices

        Args:
            item_id: Payment ID (when called from template)
            item: Payment data dict
            **kwargs: Additional context (hospital_id, etc.)

        Returns:
            Dict with list of invoice allocations and amounts
        """
        try:
            # Parameter resolution
            if item_id:
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                payment_id = item['payment_id']
            else:
                return {
                    'allocations': [],
                    'has_allocations': False,
                    'total_allocated': 0,
                    'allocation_count': 0,
                    'entity_type': 'patient_invoices',
                    'currency_symbol': '₹',
                    'error': 'No payment ID found'
                }

            with get_db_session() as session:
                # Convert IDs to UUID
                payment_uuid = uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Query ar_subledger for LINE ITEM allocations from this payment
                # Group by invoice to get total allocated to each invoice
                ar_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == hospital_uuid,
                    ARSubledger.reference_id == payment_uuid,
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.reference_line_item_id.isnot(None)
                ).order_by(ARSubledger.transaction_date).all()

                # Also query for package installment entries (NULL reference_line_item_id)
                package_installment_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == hospital_uuid,
                    ARSubledger.reference_id == payment_uuid,
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.entry_type == 'package_installment',
                    ARSubledger.reference_line_item_id.is_(None)
                ).order_by(ARSubledger.transaction_date).all()

                # Calculate package installment total
                package_installment_total = sum(entry.credit_amount or Decimal(0) for entry in package_installment_entries)

                if not ar_entries and not package_installment_entries:
                    return {
                        'allocations': [],
                        'has_allocations': False,
                        'total_allocated': 0,
                        'allocation_count': 0,
                        'package_installments': [],
                        'package_installment_total': 0,
                        'entity_type': 'patient_invoices',
                        'currency_symbol': '₹',
                        'message': 'No invoice allocations found'
                    }

                # Group allocations by invoice
                invoice_allocations = {}
                for ar_entry in ar_entries:
                    # Get the invoice via line item
                    line_item = session.query(InvoiceLineItem).filter(
                        InvoiceLineItem.line_item_id == ar_entry.reference_line_item_id
                    ).first()

                    if line_item:
                        invoice_id = str(line_item.invoice_id)
                        if invoice_id not in invoice_allocations:
                            invoice_allocations[invoice_id] = {
                                'ar_entries': [],
                                'total_allocated': Decimal(0)
                            }
                        invoice_allocations[invoice_id]['ar_entries'].append(ar_entry)
                        invoice_allocations[invoice_id]['total_allocated'] += (ar_entry.credit_amount or Decimal(0))

                # ========================================================================
                # Get wallet and advance amounts from payment record FIRST
                # so we can distribute them across allocations
                # ========================================================================
                payment = session.query(PatientPaymentReceiptView).filter(
                    PatientPaymentReceiptView.payment_id == payment_uuid
                ).first()

                wallet_amount = Decimal('0')
                advance_amount = Decimal('0')

                if payment:
                    wallet_amount = Decimal(str(payment.wallet_points_amount or 0))
                    advance_amount = Decimal(str(payment.advance_adjustment_amount or 0))

                # Build allocations list with invoice details
                allocations = []
                total_ar_allocated = Decimal(0)  # Only AR-tracked amounts

                for invoice_id_str, alloc_data in invoice_allocations.items():
                    # Get invoice details
                    invoice = session.query(InvoiceHeader).filter(
                        InvoiceHeader.invoice_id == uuid.UUID(invoice_id_str)
                    ).first()

                    if invoice:
                        ar_allocated_amount = alloc_data['total_allocated']
                        first_ar_entry = alloc_data['ar_entries'][0]

                        allocation_dict = {
                            'invoice_id': invoice_id_str,
                            'invoice_number': invoice.invoice_number,
                            'invoice_date': invoice.invoice_date,
                            'invoice_total': float(invoice.grand_total or 0),
                            'ar_allocated_amount': float(ar_allocated_amount),  # Original AR amount
                            'allocated_amount': float(ar_allocated_amount),  # Will be updated below
                            'allocation_date': first_ar_entry.transaction_date,
                            'ar_entry_count': len(alloc_data['ar_entries']),  # Number of line items
                            'reference_number': first_ar_entry.reference_number,
                            'is_cancelled': invoice.is_cancelled
                        }
                        allocations.append(allocation_dict)
                        total_ar_allocated += ar_allocated_amount

                # ========================================================================
                # Distribute wallet and advance amounts proportionally across invoices
                # ========================================================================
                if total_ar_allocated > 0 and (wallet_amount > 0 or advance_amount > 0):
                    for alloc in allocations:
                        # Calculate proportion based on AR allocation
                        proportion = Decimal(str(alloc['ar_allocated_amount'])) / total_ar_allocated
                        wallet_portion = wallet_amount * proportion
                        advance_portion = advance_amount * proportion

                        # Update allocated_amount to include wallet and advance
                        alloc['allocated_amount'] = float(
                            Decimal(str(alloc['ar_allocated_amount'])) + wallet_portion + advance_portion
                        )
                        alloc['wallet_portion'] = float(wallet_portion)
                        alloc['advance_portion'] = float(advance_portion)

                # If no AR allocations but we have wallet/advance (wallet-only payment)
                elif len(allocations) == 0 and (wallet_amount > 0 or advance_amount > 0):
                    # For wallet-only payments, we may not have AR entries
                    # This is handled separately in the return
                    pass

                total_allocated = total_ar_allocated  # For backward compatibility

                # Build package installment data
                package_installments = []
                if package_installment_entries:
                    for pkg_entry in package_installment_entries:
                        # Try to get installment payment details
                        installment = session.query(InstallmentPayment).filter(
                            InstallmentPayment.payment_id == payment_uuid
                        ).first()

                        package_installments.append({
                            'amount': float(pkg_entry.credit_amount or 0),
                            'transaction_date': pkg_entry.transaction_date,
                            'installment_number': installment.installment_number if installment else None,
                            'plan_id': str(installment.plan_id) if installment else None,
                            'full_installment_amount': float(installment.amount) if installment else float(pkg_entry.credit_amount or 0),
                            'is_partial': installment and abs(float(installment.amount) - float(pkg_entry.credit_amount)) > 0.01 if installment else False
                        })

                # Calculate grand total (invoices + packages + wallet + advance)
                # NOTE: wallet_amount and advance_amount were retrieved earlier
                grand_total_allocated = total_allocated + package_installment_total + wallet_amount + advance_amount

                return {
                    'allocations': allocations,
                    'has_allocations': len(allocations) > 0 or len(package_installments) > 0,
                    'total_allocated': float(total_allocated),  # AR-tracked invoice payments (cash/card/upi)
                    'allocation_count': len(allocations),
                    'package_installments': package_installments,
                    'package_installment_total': float(package_installment_total),
                    'has_package_installments': len(package_installments) > 0,
                    # ✅ Wallet and advance amounts
                    'wallet_amount': float(wallet_amount),
                    'advance_amount': float(advance_amount),
                    'has_wallet_payment': wallet_amount > 0,
                    'has_advance_payment': advance_amount > 0,
                    # ✅ Grand total includes ALL payment methods
                    'grand_total_allocated': float(grand_total_allocated),
                    'entity_type': 'patient_invoices',  # For links to invoice detail view
                    'currency_symbol': '₹',
                    'is_multi_invoice_payment': len(allocations) > 1
                }

        except Exception as e:
            logger.error(f"Error getting payment invoice allocations: {e}", exc_info=True)
            return {
                'allocations': [],
                'has_allocations': False,
                'total_allocated': 0,
                'allocation_count': 0,
                'entity_type': 'patient_invoices',
                'currency_symbol': '₹',
                'error': str(e)
            }

    # ==========================================================================
    # VIRTUAL FIELD CALCULATIONS (if needed)
    # ==========================================================================

    def _add_virtual_calculations(self, item: Dict[str, Any], item_id: str, **kwargs) -> Dict[str, Any]:
        """
        Add calculated virtual fields to payment data
        Called by Universal Engine when rendering detail view

        Args:
            item: Payment data dict
            item_id: Payment ID (required by parent class signature)
            **kwargs: Additional context (hospital_id, branch_id, etc.)

        Returns:
            Enhanced payment data with virtual fields
        """
        try:
            # Calculate payment method breakdown percentage
            # Use payment_method_total which includes wallet + advance
            total = float(item.get('payment_method_total', 0)) or float(item.get('total_amount', 0))

            # Set payment_total_display virtual field for the breakdown section
            item['payment_total_display'] = total

            if total > 0:
                item['cash_percentage'] = round((float(item.get('cash_amount', 0)) / total) * 100, 1)
                item['card_percentage'] = round(
                    ((float(item.get('credit_card_amount', 0)) + float(item.get('debit_card_amount', 0))) / total) * 100,
                    1
                )
                item['upi_percentage'] = round((float(item.get('upi_amount', 0)) / total) * 100, 1)
                item['wallet_percentage'] = round((float(item.get('wallet_points_amount', 0)) / total) * 100, 1)
                item['advance_percentage'] = round((float(item.get('advance_adjustment_amount', 0)) / total) * 100, 1)

            # Add status badges
            status = item.get('workflow_status', 'unknown')
            item['status_badge_class'] = self._get_status_badge_class(status)
            item['status_icon'] = self._get_status_icon(status)

            # Add payment method icon
            payment_method = item.get('payment_method_primary', '')
            item['payment_method_icon'] = self._get_payment_method_icon(payment_method)

            return item

        except Exception as e:
            logger.error(f"Error adding virtual calculations: {e}")
            return item

    def _get_status_badge_class(self, status: str) -> str:
        """Get CSS class for status badge"""
        status_map = {
            'draft': 'badge-secondary',
            'pending_approval': 'badge-warning',
            'approved': 'badge-success',
            'rejected': 'badge-danger',
            'reversed': 'badge-dark'
        }
        return status_map.get(status, 'badge-secondary')

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status"""
        icon_map = {
            'draft': 'fas fa-edit',
            'pending_approval': 'fas fa-clock',
            'approved': 'fas fa-check-circle',
            'rejected': 'fas fa-times-circle',
            'reversed': 'fas fa-undo'
        }
        return icon_map.get(status, 'fas fa-question-circle')

    def _get_payment_method_icon(self, method: str) -> str:
        """Get icon for payment method"""
        icon_map = {
            'Cash': 'fas fa-money-bill',
            'Credit Card': 'fas fa-credit-card',
            'Debit Card': 'fas fa-credit-card',
            'UPI': 'fas fa-mobile-alt',
            'Multiple': 'fas fa-layer-group',
            'Advance Adjustment': 'fas fa-exchange-alt'
        }
        return icon_map.get(method, 'fas fa-money-bill-wave')

    def get_payment_reference_display(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get reference display for payment
        For multi-invoice payments (invoice_id = NULL), show all invoice numbers
        For single invoice payments, show reference_number

        Returns:
            dict with 'value' key containing display string
        """
        try:
            if not item_id and not item:
                return {'value': '-'}

            payment_uuid = uuid.UUID(item_id) if item_id else uuid.UUID(item.get('payment_id'))
            hospital_id = item.get('hospital_id') if item else None

            if not hospital_id:
                hospital_id = current_user.hospital_id if current_user and current_user.is_authenticated else None

            hospital_uuid = uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

            with get_db_session() as session:
                # Check if it's a multi-invoice payment
                payment = session.query(PaymentDetail).filter_by(payment_id=payment_uuid).first()

                if not payment:
                    return {'value': '-'}

                # If it has a reference number, always show it
                reference_display = payment.reference_number or ''

                # If it's a multi-invoice payment (invoice_id = NULL), get all invoice numbers
                if payment.invoice_id is None:
                    # Get invoice IDs from AR subledger
                    ar_entries = session.query(ARSubledger).filter(
                        ARSubledger.hospital_id == hospital_uuid,
                        ARSubledger.reference_id == payment_uuid,
                        ARSubledger.reference_type == 'payment',
                        ARSubledger.reference_line_item_id.isnot(None)
                    ).all()

                    if ar_entries:
                        # Get unique invoice IDs
                        invoice_ids = set()
                        for ar in ar_entries:
                            line_item = session.query(InvoiceLineItem).filter_by(
                                line_item_id=ar.reference_line_item_id
                            ).first()
                            if line_item:
                                invoice_ids.add(line_item.invoice_id)

                        # Get invoice numbers and dates
                        invoice_info = []
                        for inv_id in invoice_ids:
                            invoice = session.query(InvoiceHeader).filter_by(invoice_id=inv_id).first()
                            if invoice:
                                inv_date = invoice.invoice_date.strftime('%d/%b/%Y') if invoice.invoice_date else ''
                                invoice_info.append(f"{invoice.invoice_number} ({inv_date})")

                        if invoice_info:
                            invoices_str = ", ".join(sorted(invoice_info))
                            if reference_display:
                                return {'value': f"{reference_display} | Invoices: {invoices_str}"}
                            else:
                                return {'value': f"Multi-Invoice Payment: {invoices_str}"}

                # Single invoice or has reference
                return {'value': reference_display or '-'}

        except Exception as e:
            logger.error(f"Error getting payment reference display: {e}", exc_info=True)
            return {'value': '-'}
