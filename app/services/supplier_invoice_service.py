"""
Supplier Invoice Service
File: app/services/supplier_invoice_service.py

Extends UniversalEntityService for generic functionality
Contains only invoice-specific business logic
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask_login import current_user
from sqlalchemy import or_, and_, desc, asc, func
from sqlalchemy.orm import Session, joinedload

from app.engine.universal_entity_service import UniversalEntityService
from app.engine.business.line_items_handler import line_items_handler
from app.models.views import SupplierInvoiceView, PurchaseOrderView
from app.models.transaction import SupplierInvoice, SupplierInvoiceLine, SupplierPayment
from app.models.master import Supplier
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)


class SupplierInvoiceService(UniversalEntityService):
    """
    Supplier Invoice service with invoice-specific logic
    Inherits generic functionality from UniversalEntityService
    """
    
    def __init__(self):
        # Use the view model for better performance
        super().__init__('supplier_invoices')
        
        # Ensure config is loaded
        if not self.config:
            from app.config.modules.supplier_invoice_config import SUPPLIER_INVOICE_CONFIG
            self.config = SUPPLIER_INVOICE_CONFIG
    
    # ==========================================================================
    # CUSTOM RENDERER METHODS (for complex display components)
    # ==========================================================================
    
    def get_invoice_lines(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice line items - delegates to centralized handler
        """
        # Extract invoice ID from parameters
        invoice_id = item_id or (item.get('invoice_id') if item else None)
        
        # Call centralized function with context
        return line_items_handler.get_invoice_line_items(
            invoice_id=invoice_id,
            context='invoice_detail',
            **kwargs
        )
    
    def get_po_line_items(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get PO line items for comparison - delegates to centralized handler
        """
        # Get PO ID from invoice
        po_id = None
        if item and isinstance(item, dict):
            po_id = item.get('po_id')
        elif item_id:
            # Fetch invoice to get po_id
            with get_db_session() as session:
                invoice = session.query(SupplierInvoice).filter(
                    SupplierInvoice.invoice_id == item_id
                ).first()
                if invoice:
                    po_id = invoice.po_id
        
        if not po_id:
            return line_items_handler._empty_result('po', 'No PO linked to this invoice')
        
        # Call centralized function
        return line_items_handler.get_po_line_items(
            po_id=po_id,
            context='invoice_comparison',
            **kwargs
        )
    
    def _empty_line_items_result(self) -> Dict:
        """Return empty result structure for line items"""
        return {
            'items': [],
            'has_lines': False,
            'has_items': False,
            'summary': {
                'line_count': 0,
                'total_items': 0,
                'subtotal': 0,
                'total_amount': 0,
                'total_discount': 0,
                'total_gst': 0,
                'grand_total': 0
            },
            'line_count': 0,
            'total_amount': 0,
            'total_gst': 0,
            'total_discount': 0,
            'grand_total': 0,
            'currency_symbol': '₹',
            'show_summary': True,
            'show_gst_breakup': True,
            'message': 'No line items found'
        }
    
    def _error_line_items_result(self, error: str) -> Dict:
        """Return error result structure for line items"""
        result = self._empty_line_items_result()
        result['error'] = error
        result['has_error'] = True
        result['message'] = f'Error loading line items: {error}'
        return result
    
    

    # ==========================================================================
    # VIRTUAL FIELD CALCULATIONS
    # ==========================================================================
    
    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add virtual/calculated fields to detail view data
        Called automatically by parent for detail views
        """
        try:
            # Calculate invoice age
            if result.get('invoice_date'):
                invoice_date = result['invoice_date']
                if isinstance(invoice_date, str):
                    invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
                elif hasattr(invoice_date, 'date'):
                    # Convert datetime to date to avoid timezone issues
                    invoice_date = invoice_date.date()

                # ✅ FIX: Use date.today() to avoid offset-naive/offset-aware mismatch
                age_delta = date.today() - invoice_date
                result['invoice_age_days'] = age_delta.days
                
                # Calculate days overdue if applicable
                if result.get('due_date'):
                    due_date = result['due_date']
                    if isinstance(due_date, str):
                        due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                    
                    if date.today() > due_date:
                        overdue_delta = date.today() - due_date
                        result['days_overdue'] = overdue_delta.days
                    else:
                        result['days_overdue'] = 0
                else:
                    result['days_overdue'] = 0
            
            # Add payment summary
            payment_info = self.get_payment_history(item_id=item_id, **kwargs)
            if payment_info and not payment_info.get('error'):
                result['total_paid'] = payment_info.get('total_paid', 0)
                result['balance_due'] = payment_info.get('balance_due', 0)
                result['is_fully_paid'] = payment_info.get('is_fully_paid', False)
            
            # Add line items summary
            lines_info = self.get_invoice_lines(item_id=item_id, **kwargs)
            if lines_info and not lines_info.get('error'):
                # Populate virtual fields for items_summary section
                result['line_items_count'] = lines_info.get('summary', {}).get('line_count', 0)
                result['line_items_subtotal'] = lines_info.get('summary', {}).get('total_amount', 0)
                result['line_items_discount'] = lines_info.get('summary', {}).get('total_discount', 0)
                result['line_items_gst'] = lines_info.get('summary', {}).get('total_gst', 0)
                result['line_items_total'] = lines_info.get('summary', {}).get('grand_total', 0)
            else:
                # Set defaults if no line items
                result['line_items_count'] = 0
                result['line_items_subtotal'] = 0
                result['line_items_discount'] = 0
                result['line_items_gst'] = 0
                result['line_items_total'] = 0
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating virtual fields: {str(e)}")
            # Set defaults on error
            result.setdefault('line_items_count', 0)
            result.setdefault('line_items_subtotal', 0)
            result.setdefault('line_items_discount', 0)
            result.setdefault('line_items_gst', 0)
            result.setdefault('line_items_total', 0)
            return result
    
    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================
    
    def _get_status_badge(self, status: str) -> str:
        """Get HTML badge class for payment status"""
        status_badges = {
            'pending': 'badge-warning',
            'approved': 'badge-success',
            'completed': 'badge-success',
            'rejected': 'badge-danger',
            'cancelled': 'badge-secondary'
        }
        return status_badges.get(status, 'badge-secondary')
    
    # ==========================================================================
    # BUSINESS LOGIC METHODS (Invoice-specific operations)
    # ==========================================================================
    
    @cache_service_method('supplier_invoices', 'outstanding_by_supplier')
    def get_outstanding_by_supplier(self, supplier_id: uuid.UUID, hospital_id: uuid.UUID) -> Dict:
        """
        Get outstanding invoice summary for a specific supplier
        Used in payment creation and supplier analysis
        """
        try:
            with get_db_session() as session:
                # Get all unpaid/partially paid invoices
                invoices = session.query(SupplierInvoice).filter(
                    SupplierInvoice.supplier_id == supplier_id,
                    SupplierInvoice.hospital_id == hospital_id,
                    SupplierInvoice.payment_status.in_(['pending', 'partial', 'overdue'])
                ).all()
                
                total_outstanding = Decimal('0')
                overdue_amount = Decimal('0')
                invoice_list = []
                
                for invoice in invoices:
                    # Calculate paid amount for this invoice
                    paid_amount = session.query(
                        func.coalesce(func.sum(SupplierPayment.payment_amount), 0)
                    ).filter(
                        SupplierPayment.invoice_id == invoice.invoice_id,
                        SupplierPayment.payment_status.in_(['approved', 'completed'])
                    ).scalar() or Decimal('0')
                    
                    balance = invoice.invoice_total_amount - paid_amount
                    
                    if balance > 0:
                        total_outstanding += balance
                        
                        if invoice.due_date and date.today() > invoice.due_date:
                            overdue_amount += balance
                        
                        invoice_list.append({
                            'invoice_id': str(invoice.invoice_id),
                            'invoice_number': invoice.supplier_invoice_number,
                            'invoice_date': invoice.invoice_date,
                            'due_date': invoice.due_date,
                            'total_amount': float(invoice.invoice_total_amount),
                            'paid_amount': float(paid_amount),
                            'balance_due': float(balance),
                            'is_overdue': invoice.due_date and date.today() > invoice.due_date
                        })
                
                return {
                    'supplier_id': str(supplier_id),
                    'total_outstanding': float(total_outstanding),
                    'overdue_amount': float(overdue_amount),
                    'invoice_count': len(invoice_list),
                    'invoices': invoice_list
                }
                
        except Exception as e:
            logger.error(f"Error getting outstanding by supplier: {str(e)}")
            return {
                'supplier_id': str(supplier_id),
                'total_outstanding': 0,
                'overdue_amount': 0,
                'invoice_count': 0,
                'invoices': []
            }
    
    def validate_invoice_for_payment(self, invoice_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Validate if an invoice can accept payments
        Returns (is_valid, message)
        """
        try:
            with get_db_session() as session:
                invoice = session.query(SupplierInvoice).filter(
                    SupplierInvoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    return False, "Invoice not found"
                
                if invoice.payment_status == 'paid':
                    return False, "Invoice is already fully paid"
                
                if invoice.payment_status == 'cancelled':
                    return False, "Cannot make payment for cancelled invoice"
                
                if invoice.is_reversed:
                    return False, "Cannot make payment for reversed invoice"
                
                return True, "Invoice is valid for payment"
                
        except Exception as e:
            logger.error(f"Error validating invoice for payment: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def update_payment_status(self, invoice_id: uuid.UUID, session: Session = None) -> bool:
        """
        Update invoice payment status based on payments received
        Can be called after payment creation/update/deletion
        """
        try:
            def _update_status(db_session):
                invoice = db_session.query(SupplierInvoice).filter(
                    SupplierInvoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    return False
                
                # Calculate total paid - use workflow_status and amount fields
                # Exclude soft-deleted payments
                total_paid = db_session.query(
                    func.coalesce(func.sum(SupplierPayment.amount), 0)
                ).filter(
                    SupplierPayment.invoice_id == invoice_id,
                    SupplierPayment.workflow_status == 'approved',
                    SupplierPayment.is_deleted == False
                ).scalar() or Decimal('0')

                # Get invoice total (handle None)
                invoice_total = invoice.total_amount or Decimal('0')

                # Update payment status with logging
                old_status = invoice.payment_status
                if total_paid >= invoice_total and invoice_total > 0:
                    invoice.payment_status = 'paid'
                elif total_paid > 0:
                    invoice.payment_status = 'partial'
                elif invoice.due_date and date.today() > invoice.due_date:
                    invoice.payment_status = 'overdue'
                else:
                    invoice.payment_status = 'unpaid'

                logger.info(f"Updated invoice {invoice_id} payment status: {old_status} -> {invoice.payment_status} (paid: ₹{total_paid}, total: ₹{invoice_total})")

                db_session.flush()
                return True
            
            if session:
                return _update_status(session)
            else:
                with get_db_session() as new_session:
                    return _update_status(new_session)
                    
        except Exception as e:
            logger.error(f"Error updating payment status: {str(e)}")
            return False
    
    # ==========================================================================
    # AGING ANALYSIS
    # ==========================================================================
    
    @cache_service_method('supplier_invoices', 'aging_analysis')
    def get_aging_analysis(self, hospital_id: uuid.UUID, supplier_id: uuid.UUID = None) -> Dict:
        """
        Get aging analysis for invoices
        Optionally filtered by supplier
        """
        try:
            with get_db_session() as session:
                query = session.query(SupplierInvoice).filter(
                    SupplierInvoice.hospital_id == hospital_id,
                    SupplierInvoice.payment_status.in_(['pending', 'partial', 'overdue'])
                )
                
                if supplier_id:
                    query = query.filter(SupplierInvoice.supplier_id == supplier_id)
                
                invoices = query.all()
                
                buckets = {
                    '0-30': {'count': 0, 'amount': Decimal('0')},
                    '31-60': {'count': 0, 'amount': Decimal('0')},
                    '61-90': {'count': 0, 'amount': Decimal('0')},
                    '90+': {'count': 0, 'amount': Decimal('0')}
                }
                
                today = date.today()
                
                for invoice in invoices:
                    age_days = (today - invoice.invoice_date.date()).days if invoice.invoice_date else 0
                    
                    # Calculate balance due
                    paid_amount = session.query(
                        func.coalesce(func.sum(SupplierPayment.payment_amount), 0)
                    ).filter(
                        SupplierPayment.invoice_id == invoice.invoice_id,
                        SupplierPayment.payment_status.in_(['approved', 'completed'])
                    ).scalar() or Decimal('0')
                    
                    balance = invoice.invoice_total_amount - paid_amount
                    
                    if balance > 0:
                        if age_days <= 30:
                            bucket = '0-30'
                        elif age_days <= 60:
                            bucket = '31-60'
                        elif age_days <= 90:
                            bucket = '61-90'
                        else:
                            bucket = '90+'
                        
                        buckets[bucket]['count'] += 1
                        buckets[bucket]['amount'] += balance
                
                # Convert to float for JSON serialization
                for bucket in buckets:
                    buckets[bucket]['amount'] = float(buckets[bucket]['amount'])
                
                return {
                    'buckets': buckets,
                    'total_outstanding': sum(b['amount'] for b in buckets.values()),
                    'total_invoices': sum(b['count'] for b in buckets.values())
                }
                
        except Exception as e:
            logger.error(f"Error in aging analysis: {str(e)}")
            return {
                'buckets': {
                    '0-30': {'count': 0, 'amount': 0},
                    '31-60': {'count': 0, 'amount': 0},
                    '61-90': {'count': 0, 'amount': 0},
                    '90+': {'count': 0, 'amount': 0}
                },
                'total_outstanding': 0,
                'total_invoices': 0
            }
        
    def get_payment_history(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get payment history for invoice display
        Used by custom renderer for 'payment_history_display' field
        """
        try:
            # Parameter resolution - same pattern as get_invoice_lines
            if item_id:
                invoice_id = item_id
            elif item and isinstance(item, dict) and 'invoice_id' in item:
                invoice_id = item['invoice_id']
            else:
                return {'payments': [], 'has_payments': False}
            
            with get_db_session() as session:
                # Get payments linked to this invoice
                payments = session.query(SupplierPayment)\
                    .filter(SupplierPayment.invoice_id == invoice_id)\
                    .order_by(desc(SupplierPayment.payment_date))\
                    .all()
                
                payment_list = []
                total_paid = Decimal('0')
                
                for payment in payments:
                    payment_list.append({
                        'payment_id': str(payment.payment_id),
                        'reference_no': payment.reference_no,
                        'payment_date': payment.payment_date,
                        'payment_amount': float(payment.payment_amount),
                        'payment_method': payment.payment_method,
                        'status': payment.workflow_status,
                        'created_by': payment.created_by,
                        'notes': payment.notes
                    })
                    if payment.workflow_status != 'cancelled':
                        total_paid += payment.payment_amount
                
                return {
                    'payments': payment_list,
                    'has_payments': bool(payment_list),
                    'payment_count': len(payment_list),
                    'total_paid': float(total_paid),
                    'currency': 'INR'
                }
                
        except Exception as e:
            logger.error(f"Error getting payment history for invoice {invoice_id}: {str(e)}")
            return {'payments': [], 'has_payments': False, 'error': str(e)}

    def get_po_details(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get purchase order details for invoice
        Used by custom renderer for 'po_details_display' field
        """
        try:
            # Get PO ID from item
            po_id = item.get('po_id') if item else None
            if not po_id:
                return {'has_po': False}
            
            with get_db_session() as session:
                # CORRECTED: Use PurchaseOrderView from views module
                po = session.query(PurchaseOrderView).filter_by(po_id=po_id).first()
                
                if not po:
                    return {'has_po': False}
                
                return {
                    'has_po': True,
                    'po_number': po.po_number,
                    'po_date': po.po_date,
                    'po_status': po.po_status,  # or po.status if using standardized field
                    'supplier_name': po.supplier_name,
                    'total_amount': float(po.total_amount) if po.total_amount else 0,
                    'expected_delivery': po.expected_delivery_date,
                    'quotation_id': po.quotation_id if hasattr(po, 'quotation_id') else None
                }
                
        except Exception as e:
            logger.error(f"Error getting PO details for po_id {po_id}: {str(e)}")
            return {'has_po': False, 'error': str(e)}

    def get_summary_stats(self, filters: Dict = None, **kwargs) -> Dict:
        """
        Get summary statistics for supplier invoices
        This method is called by Universal Engine for summary cards
        """
        try:
            with get_db_session() as session:
                # Base query using the view
                query = session.query(SupplierInvoiceView)\
                    .filter_by(hospital_id=kwargs.get('hospital_id'))
                
                # Apply branch filter if provided
                if kwargs.get('branch_id'):
                    query = query.filter_by(branch_id=kwargs.get('branch_id'))
                
                # Apply filters if provided
                if filters:
                    query = self.apply_filters(query, filters)
                
                # Get all invoices for aggregation
                invoices = query.all()
                
                # Calculate statistics
                total_count = len(invoices)
                total_amount_sum = sum(inv.invoice_total_amount or 0 for inv in invoices)
                balance_amount_sum = sum(inv.balance_amount or 0 for inv in invoices)
                
                # Count overdue invoices
                from datetime import date
                today = date.today()
                overdue_count = sum(
                    1 for inv in invoices 
                    if inv.due_date and inv.due_date < today and inv.payment_status != 'paid'
                )
                
                return {
                    'total_count': total_count,
                    'total_amount_sum': float(total_amount_sum),
                    'balance_amount_sum': float(balance_amount_sum),
                    'overdue_count': overdue_count
                }
                
        except Exception as e:
            logger.error(f"Error getting summary stats: {str(e)}")
            return {
                'total_count': 0,
                'total_amount_sum': 0,
                'balance_amount_sum': 0,
                'overdue_count': 0
            }