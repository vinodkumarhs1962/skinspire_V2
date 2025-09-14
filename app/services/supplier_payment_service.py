# File: app/services/supplier_payment_service.py (ENHANCED)

"""
Supplier Payment Service - Complete implementation with all payment-specific logic
Extends UniversalEntityService for generic functionality
Contains only payment-specific business logic
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime, date, timedelta
from flask_login import current_user
from sqlalchemy import or_, and_, desc, asc, func
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.models.transaction import SupplierPayment, SupplierInvoice
from app.models.master import Supplier
from app.engine.universal_entity_service import UniversalEntityService
from app.engine.business.line_items_handler import line_items_handler
from app.models.views import SupplierPaymentView
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierPaymentService(UniversalEntityService):
    """
    Complete supplier payment service with all unique logic
    Inherits generic functionality from UniversalEntityService
    """
    
    def __init__(self):
        """Initialize with proper model class like PurchaseOrderService"""
        # Import the view model at the top if not already imported
        from app.models.views import SupplierPaymentView
        
        # Pass BOTH entity_type AND model_class to parent (matching PurchaseOrderService pattern)
        super().__init__('supplier_payments', SupplierPaymentView)
        
        # Log initialization for debugging
        logger.info("✅ Initialized SupplierPaymentService with SupplierPaymentView")
    
    
    def get_po_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get purchase order items related to this payment
        Following the same pattern as get_invoice_items_for_payment
        """
        try:
            po_info = None  # ✅ Initialize as local variable
            # PARAMETER RESOLUTION - matching invoice method pattern
            if item_id:
                # Template calls: item_id IS the payment_id
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                # If item has payment_id field
                payment_id = item['payment_id']
            else:
                return {'items': [], 'has_po': False, 'error': 'No payment ID found'}
                
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id')
                ).first()
                
                if not payment:
                    return {'items': [], 'has_po': False}
                
                po_items = []
                po_summary = {
                    'total_amount': 0,
                    'total_gst': 0
                }
                
                # Access PO through single invoice (no loop needed)
                if payment.invoice_id:
                    invoice = session.query(SupplierInvoice).filter(
                        SupplierInvoice.invoice_id == payment.invoice_id
                    ).first()
                    
                    if invoice and invoice.po_id:
                        from app.models.transaction import PurchaseOrderHeader, PurchaseOrderLine
                        po = session.query(PurchaseOrderHeader).filter(
                            PurchaseOrderHeader.po_id == invoice.po_id
                        ).first()
                        
                        if po:
                            # Store PO info in the main data dict, similar to invoice
                            po_info = {
                                'po_no': po.po_number,
                                'po_number': po.po_number,  # Both for compatibility
                                'po_date': po.po_date,  # Keep as date object for template filter
                                'total_amount': float(po.total_amount or 0),
                                'status': po.status if hasattr(po, 'status') else 'draft'
                            }
                            
                            po_lines = session.query(PurchaseOrderLine).filter(
                                PurchaseOrderLine.po_id == po.po_id
                            ).all()
                            
                            for item in po_lines:
                                po_items.append({
                                    'item_name': item.medicine_name,
                                    'quantity': float(item.units or 0),
                                    'unit_price': float(item.pack_purchase_price or 0),
                                    'gst_amount': float(item.total_gst or 0),
                                    'total_amount': float(item.line_total or 0)
                                })
                                
                                po_summary['total_amount'] += float(item.line_total or 0)
                                po_summary['total_gst'] += float(item.total_gst or 0)
                
                # Return structure matching invoice pattern
                result = {
                    'items': po_items,
                    'summary': po_summary,
                    'has_po': bool(po_items),
                    'currency_symbol': '₹',
                    'po_info': po_info  # ✅ Always include, will be None or dict
                }

                # RIGHT BEFORE THE RETURN STATEMENT, ADD:
                logger.info("[PO_DEBUG_1] get_po_items_for_payment returning:")
                logger.info(f"  - has_po: {bool(po_items)}")
                logger.info(f"  - items count: {len(po_items)}")
                logger.info(f"  - po_info present: {po_info is not None}")
                if po_info:
                    logger.info(f"  - po_info.po_number: {po_info.get('po_number')}")
                    logger.info(f"  - po_info.po_date: {po_info.get('po_date')}")
                    logger.info(f"  - po_info.total_amount: {po_info.get('total_amount')}")

                return result
                
        except Exception as e:
            logger.error(f"Error getting PO items for payment: {str(e)}")
            return {
                'items': [],
                'summary': {},
                'has_po': False,
                'currency_symbol': '₹',
                'error': str(e)
            }

    def get_invoice_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice items being paid - delegates to centralized handler
        """
        # Get invoice ID from payment
        invoice_id = None
        if item and isinstance(item, dict):
            invoice_id = item.get('invoice_id')
        elif item_id:
            # Fetch payment to get invoice_id
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == item_id
                ).first()
                if payment:
                    invoice_id = payment.invoice_id
        
        if not invoice_id:
            return line_items_handler._empty_result('invoice', 'No invoice linked to this payment')
        
        # Call centralized function
        return line_items_handler.get_invoice_line_items(
            invoice_id=invoice_id,
            context='payment_invoice',
            **kwargs
        )

    def get_payment_items_display(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get payment items - delegates to centralized handler
        """
        payment_id = item_id or (item.get('payment_id') if item else None)
        
        # Call centralized function
        return line_items_handler.get_payment_items(
            payment_id=payment_id,
            context='payment_detail',
            **kwargs
        )


    def get_payment_workflow_timeline(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get workflow timeline for payment approval process
        Returns data for the workflow timeline custom renderer
        """
        try:
            # PARAMETER RESOLUTION for payment workflow
            if item_id:
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                payment_id = item['payment_id']
            else:
                return {'steps': [], 'has_timeline': False, 'error': 'No payment ID found'}
                
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id')
                ).first()
                
                if not payment:
                    return {'steps': [], 'current_status': 'unknown', 'has_timeline': False}
                
                # Build workflow timeline with fields that actually exist
                steps = []
                
                # Step 1: Created
                steps.append({
                    'title': 'Payment Created',
                    'status': 'completed',
                    'timestamp': payment.created_at,  # PASS DATETIME OBJECT, NOT STRING
                    'user': payment.created_by,
                    'icon': 'fas fa-plus-circle',
                    'color': 'success',
                    'description': f'Payment of ₹{payment.amount:,.2f} created'
                })
                
                # Step 2: Submitted for Approval (if applicable)
                if payment.submitted_for_approval_at:
                    steps.append({
                        'title': 'Submitted for Approval',
                        'status': 'completed',
                        'timestamp': payment.submitted_for_approval_at,  # DATETIME OBJECT
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
                        'timestamp': payment.approved_at,  # DATETIME OBJECT
                        'user': payment.approved_by,
                        'icon': 'fas fa-check-circle',
                        'color': 'success',
                        'description': 'Payment has been approved',
                        'notes': payment.approval_notes
                    })
                    
                elif payment.workflow_status == 'rejected' and payment.rejected_at:
                    steps.append({
                        'title': 'Payment Rejected',
                        'status': 'rejected',
                        'timestamp': payment.rejected_at,  # DATETIME OBJECT
                        'user': payment.rejected_by,
                        'icon': 'fas fa-times-circle',
                        'color': 'danger',
                        'description': 'Payment has been rejected',
                        'notes': payment.rejection_reason
                    })
                
                # Step 4: Completed/Processed
                if payment.workflow_status in ['completed', 'processed']:
                    steps.append({
                        'title': 'Payment Completed',
                        'status': 'completed',
                        'timestamp': payment.updated_at,  # DATETIME OBJECT
                        'user': payment.updated_by,
                        'icon': 'fas fa-flag-checkered',
                        'color': 'success',
                        'description': 'Payment has been completed and processed'
                    })
                
                # Step 5: Reconciliation (if applicable)
                if hasattr(payment, 'reconciliation_status') and payment.reconciliation_status == 'reconciled':
                    reconciled_timestamp = getattr(payment, 'reconciliation_date', payment.updated_at)
                    steps.append({
                        'title': 'Payment Reconciled',
                        'status': 'completed',
                        'timestamp': reconciled_timestamp,  # DATETIME OBJECT
                        'user': getattr(payment, 'reconciled_by', None),
                        'icon': 'fas fa-balance-scale',
                        'color': 'info',
                        'description': 'Payment has been reconciled with bank statement'
                    })
                
                return {
                    'steps': steps,
                    'current_status': payment.workflow_status,
                    'has_timeline': True,
                    'workflow_status': payment.workflow_status,
                    'requires_approval': payment.requires_approval,
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error getting workflow timeline: {str(e)}")
            return {'steps': [], 'has_timeline': False, 'error': str(e)}

    def get_supplier_payment_history_6months(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get last 6 months payment history for a supplier
        Enhanced version of get_supplier_payment_history
        """
        try:
            # PARAMETER RESOLUTION for payment entity
            if item and isinstance(item, dict) and 'supplier_id' in item:
                # Payment context: extract supplier_id from payment item
                supplier_id = item['supplier_id']
            elif item_id:
                # Direct call: might be supplier_id
                supplier_id = item_id
            else:
                return {'payments': [], 'has_history': False, 'error': 'No supplier ID found'}
            with get_db_session() as session:
                from datetime import datetime, timedelta
                
                # Calculate date 6 months ago
                six_months_ago = datetime.now() - timedelta(days=180)
                
                # Get payments for this supplier
                payments = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id'),
                    SupplierPayment.payment_date >= six_months_ago,
                    SupplierPayment.workflow_status.in_(['approved', 'completed'])
                ).order_by(desc(SupplierPayment.payment_date)).all()
                
                payment_history = []
                total_paid = 0
                
                for payment in payments:
                    # ✅ FIXED: Safely get invoice number
                    invoice_no = None
                    if payment.invoice_id:
                        # Load the invoice if we have an invoice_id
                        invoice = session.query(SupplierInvoice).filter(
                            SupplierInvoice.invoice_id == payment.invoice_id
                        ).first()
                        if invoice:
                            invoice_no = invoice.supplier_invoice_number
                    
                    payment_history.append({
                        'payment_id': str(payment.payment_id),
                        'reference_no': payment.reference_no,
                        'payment_date': payment.payment_date.strftime('%d/%b/%Y %H:%M') if payment.payment_date else None,  # ✅ Format as ISO string
                        'payment_method': payment.payment_method,
                        'amount': float(payment.amount or 0),
                        'workflow_status': payment.workflow_status,
                        'invoice_no': invoice_no  # ✅ Use safely retrieved invoice number
                    })
                    total_paid += float(payment.amount or 0)
                
                # Get supplier details for summary
                supplier = session.query(Supplier).filter(
                    Supplier.supplier_id == supplier_id
                ).first()
                
                return {
                    'payments': payment_history,
                    'summary': {
                        'total_payments': len(payment_history),
                        'total_amount': total_paid,
                        'supplier_name': supplier.supplier_name if supplier else 'Unknown',
                        'period': '6 Months'
                    },
                    'has_history': bool(payment_history),
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}")
            return {'payments': [], 'has_history': False, 'error': str(e)}
    

    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add payment-specific virtual calculated fields
        This is called automatically by parent's get_detail_data
        Maintains backward compatibility with all existing virtual fields
        """
        hospital_id = kwargs.get('hospital_id')
        if not hospital_id or not item_id:
            return result
        
        try:
            payment_id = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
            
            with get_db_session() as session:
                # Get payment record
                payment = session.query(SupplierPayment).filter_by(
                    payment_id=payment_id,
                    hospital_id=hospital_id
                ).first()
                
                if not payment:
                    return result
                
                # =========================================================
                # 1. INVOICE VIRTUAL FIELDS (from existing code)
                # =========================================================
                if payment.invoice_id:
                    try:
                        # Get invoice for basic info
                        invoice = session.query(SupplierInvoice).filter_by(
                            invoice_id=payment.invoice_id
                        ).first()
                        
                        if invoice:
                            # Get invoice line items for calculations
                            from app.models.transaction import SupplierInvoiceLine
                            
                            lines = session.query(SupplierInvoiceLine).filter_by(
                                invoice_id=payment.invoice_id
                            ).all()
                            
                            # Calculate totals from lines
                            total_items = len(lines)
                            total_gst = sum(float(line.gst_amount or 0) for line in lines)
                            grand_total = sum(float(line.total_amount or 0) for line in lines)
                            
                            # Set invoice virtual fields (backward compatible field names)
                            result['invoice_total_items'] = total_items
                            result['invoice_total_gst'] = total_gst
                            result['invoice_grand_total'] = grand_total
                            
                            # Also set basic invoice info
                            result['supplier_invoice_no'] = invoice.supplier_invoice_number
                            result['supplier_invoice_date'] = invoice.invoice_date
                            result['total_invoice_amount'] = float(invoice.total_amount or 0)
                        else:
                            # No invoice found - set defaults
                            result['invoice_total_items'] = 0
                            result['invoice_total_gst'] = 0
                            result['invoice_grand_total'] = 0
                            
                    except Exception as e:
                        logger.error(f"Error calculating invoice virtual fields: {str(e)}")
                        result['invoice_total_items'] = 0
                        result['invoice_total_gst'] = 0
                        result['invoice_grand_total'] = 0
                else:
                    # No invoice linked - set defaults
                    result['invoice_total_items'] = 0
                    result['invoice_total_gst'] = 0
                    result['invoice_grand_total'] = 0
                
                # =========================================================
                # 2. PO VIRTUAL FIELDS (from existing code)
                # =========================================================
                if payment.invoice_id:
                    try:
                        # Get invoice first to find PO
                        invoice = session.query(SupplierInvoice).filter_by(
                            invoice_id=payment.invoice_id
                        ).first()
                        
                        if invoice and invoice.po_id:
                            from app.models.transaction import PurchaseOrderHeader
                            
                            po = session.query(PurchaseOrderHeader).filter_by(
                                po_id=invoice.po_id
                            ).first()
                            
                            if po:
                                # Set PO virtual fields (exact field names from config)
                                result['purchase_order_no'] = po.po_number
                                result['po_date'] = po.po_date  # Keep as date object
                                result['po_total_amount'] = float(po.total_amount or 0)
                            else:
                                # PO not found - set defaults
                                result['purchase_order_no'] = ''
                                result['po_date'] = None
                                result['po_total_amount'] = 0
                        else:
                            # No PO linked - set defaults
                            result['purchase_order_no'] = ''
                            result['po_date'] = None
                            result['po_total_amount'] = 0
                            
                    except Exception as e:
                        logger.error(f"Error calculating PO virtual fields: {str(e)}")
                        result['purchase_order_no'] = ''
                        result['po_date'] = None
                        result['po_total_amount'] = 0
                else:
                    # No invoice/PO - set defaults
                    result['purchase_order_no'] = ''
                    result['po_date'] = None
                    result['po_total_amount'] = 0
                
                # =========================================================
                # 3. WORKFLOW VIRTUAL FIELDS (from existing code)
                # =========================================================
                result['submitted_by'] = getattr(payment, 'submitted_by', payment.created_by)
                result['workflow_updated_at'] = payment.updated_at
                
                # =========================================================
                # 4. ADDITIONAL VIRTUAL FIELDS (backward compatibility)
                # =========================================================
                
                # Total invoice amount (different from grand_total)
                if payment.invoice:
                    result['total_invoice_amount'] = float(payment.invoice.total_amount or 0)
                else:
                    result['total_invoice_amount'] = 0
                
                # Next approver (if in approval workflow)
                if hasattr(payment, 'next_approver_id') and payment.next_approver_id:
                    from app.models.master import User
                    approver = session.query(User).filter_by(
                        user_id=payment.next_approver_id
                    ).first()
                    if approver:
                        result['next_approver'] = approver.full_name or approver.username
                
                logger.debug(f"✅ Added virtual fields for payment {payment_id}:")
                logger.debug(f"  - Invoice fields: items={result.get('invoice_total_items')}, "
                            f"gst={result.get('invoice_total_gst')}, "
                            f"total={result.get('invoice_grand_total')}")
                logger.debug(f"  - PO fields: no={result.get('purchase_order_no')}, "
                            f"date={result.get('po_date')}, "
                            f"amount={result.get('po_total_amount')}")
                
        except Exception as e:
            logger.error(f"Error in _add_virtual_calculations: {str(e)}", exc_info=True)
            # Set all defaults on error to maintain backward compatibility
            result.setdefault('invoice_total_items', 0)
            result.setdefault('invoice_total_gst', 0)
            result.setdefault('invoice_grand_total', 0)
            result.setdefault('purchase_order_no', '')
            result.setdefault('po_date', None)
            result.setdefault('po_total_amount', 0)
            result.setdefault('total_invoice_amount', 0)
        
        return result
