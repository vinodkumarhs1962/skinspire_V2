# File: app/services/supplier_payment_service.py (ENHANCED)

"""
Supplier Payment Service - Complete implementation with all payment-specific logic
Extends UniversalEntityService for generic functionality
Contains only payment-specific business logic
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime, date, timedelta, timezone
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
                # ✅ FIX: Convert string IDs to UUID before querying
                payment_uuid = uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_uuid,
                    SupplierPayment.hospital_id == hospital_uuid
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
                # ✅ FIX: Convert string IDs to UUID before querying
                payment_uuid = uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_uuid,
                    SupplierPayment.hospital_id == hospital_uuid
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

                # ✅ FIX: Convert string IDs to UUID before querying
                supplier_uuid = uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id
                hospital_uuid = uuid.UUID(kwargs.get('hospital_id')) if isinstance(kwargs.get('hospital_id'), str) else kwargs.get('hospital_id')

                # Calculate date 6 months ago
                six_months_ago = datetime.now() - timedelta(days=180)

                # Get payments for this supplier
                payments = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_uuid,
                    SupplierPayment.hospital_id == hospital_uuid,
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
                            total_gst = sum(float(line.total_gst or 0) for line in lines)
                            grand_total = sum(float(line.line_total or 0) for line in lines)
                            
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

    # ==========================================================================
    # PAYMENT CRUD OPERATIONS
    # ==========================================================================

    def create_payment(self, data: Dict, hospital_id: str, branch_id: str, **context) -> Dict:
        """
        Create new supplier payment with validation and workflow

        Args:
            data: Payment data dictionary
            hospital_id: Hospital ID
            branch_id: Branch ID
            context: Additional context (user_id, etc.)

        Returns:
            Dict with success status, payment data, and message
        """
        try:
            user_id = context.get('user_id')

            # 1. Validate invoice if provided (BEFORE opening session to avoid transaction conflicts)
            if data.get('invoice_id'):
                from app.services.supplier_invoice_service import SupplierInvoiceService
                invoice_service = SupplierInvoiceService()
                is_valid, msg = invoice_service.validate_invoice_for_payment(
                    uuid.UUID(data['invoice_id']) if isinstance(data['invoice_id'], str) else data['invoice_id']
                )
                if not is_valid:
                    return {'success': False, 'error': msg}

            # Store variables that will be used after session closes
            invoice_id_for_update = None
            advance_only_payment = False

            with get_db_session() as session:
                # 2. Validate multi-method amounts (includes advance allocation)
                if not self._validate_multi_method_amounts(data):
                    return {
                        'success': False,
                        'error': 'Sum of payment method amounts must equal total amount'
                    }

                # 3. Process advance allocation if provided
                advance_allocation = Decimal(str(data.get('advance_allocation_amount', 0)))
                if advance_allocation > 0 and data.get('invoice_id'):
                    allocation_result = self._allocate_advance_to_invoice(
                        supplier_id=data['supplier_id'],
                        invoice_id=data['invoice_id'],
                        allocation_amount=advance_allocation,
                        hospital_id=hospital_id,
                        user_id=user_id,
                        session=session
                    )
                    if not allocation_result['success']:
                        return {
                            'success': False,
                            'error': f'Advance allocation failed: {allocation_result.get("error")}'
                        }
                    logger.info(f"Allocated ₹{advance_allocation} from advance balance to invoice")

                # 4. Calculate net new payment amount (excluding advance allocation)
                total_amount = Decimal(str(data['amount']))
                net_new_payment = total_amount - advance_allocation

                # If only advance allocation (no new payment), commit and flag for post-processing
                if net_new_payment <= Decimal('0.01'):
                    invoice_id_for_update = data.get('invoice_id')
                    advance_only_payment = True
                    session.commit()
                    # Will continue outside session context

            # OUTSIDE SESSION: Handle advance-only payment post-processing
            if advance_only_payment:
                # Update invoice payment status (opens its own session)
                if invoice_id_for_update:
                    try:
                        from app.services.supplier_invoice_service import SupplierInvoiceService
                        invoice_service = SupplierInvoiceService()
                        invoice_service.update_payment_status(
                            uuid.UUID(invoice_id_for_update) if isinstance(invoice_id_for_update, str) else invoice_id_for_update,
                            None
                        )
                    except Exception as inv_error:
                        logger.error(f"Error updating invoice status: {str(inv_error)}")

                # Invalidate caches
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('supplier_payments', cascade=False)
                if invoice_id_for_update:
                    invalidate_service_cache_for_entity('supplier_invoices', cascade=False)

                return {
                    'success': True,
                    'message': f'Payment completed using advance allocation of ₹{advance_allocation:.2f}',
                    'advance_only': True
                }

            # CONTINUE WITH REGULAR PAYMENT: Open new session for payment creation
            with get_db_session() as session:

                # 5. Create payment record - CRITICAL FIX: Include FULL amount (advance + other methods)
                payment = SupplierPayment(
                    payment_id=uuid.uuid4(),
                    hospital_id=uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id,
                    branch_id=uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id,
                    supplier_id=uuid.UUID(data['supplier_id']) if isinstance(data['supplier_id'], str) else data['supplier_id'],
                    invoice_id=uuid.UUID(data['invoice_id']) if data.get('invoice_id') and isinstance(data['invoice_id'], str) else data.get('invoice_id'),

                    # Payment details - FIXED: Use TOTAL amount (includes advance + all other methods)
                    amount=total_amount,  # CRITICAL FIX: Was net_new_payment, now total_amount
                    payment_date=data['payment_date'],
                    payment_method=data.get('payment_method', 'cash'),
                    payment_category=data.get('payment_category', 'manual'),
                    payment_source=data.get('payment_source', 'internal'),
                    reference_no=data.get('reference_no'),
                    notes=data.get('notes'),

                    # Multi-method amounts - CRITICAL FIX: Added advance_amount
                    cash_amount=Decimal(str(data.get('cash_amount', 0))),
                    cheque_amount=Decimal(str(data.get('cheque_amount', 0))),
                    bank_transfer_amount=Decimal(str(data.get('bank_transfer_amount', 0))),
                    upi_amount=Decimal(str(data.get('upi_amount', 0))),
                    advance_amount=advance_allocation,  # CRITICAL FIX: Added advance_amount field

                    # Cheque details
                    cheque_number=data.get('cheque_number'),
                    cheque_date=data.get('cheque_date'),
                    cheque_bank=data.get('cheque_bank'),
                    cheque_branch=data.get('cheque_branch'),
                    cheque_status=data.get('cheque_status', 'pending') if data.get('cheque_amount', 0) > 0 else None,

                    # Bank transfer details
                    bank_name=data.get('bank_name'),
                    bank_branch=data.get('bank_branch'),
                    bank_account_name=data.get('bank_account_name'),
                    bank_reference_number=data.get('bank_reference_number'),
                    ifsc_code=data.get('ifsc_code'),
                    transfer_mode=data.get('transfer_mode'),

                    # UPI details
                    upi_id=data.get('upi_id'),
                    upi_app_name=data.get('upi_app_name'),
                    upi_transaction_id=data.get('upi_transaction_id'),
                    upi_reference_id=data.get('upi_reference_id'),

                    # Gateway details (if applicable)
                    gateway_payment_id=data.get('gateway_payment_id'),

                    # TDS
                    tds_applicable=data.get('tds_applicable', False),
                    tds_rate=Decimal(str(data.get('tds_rate', 0))) if data.get('tds_rate') else Decimal('0'),
                    tds_amount=Decimal(str(data.get('tds_amount', 0))) if data.get('tds_amount') else Decimal('0'),
                    tds_reference=data.get('tds_reference'),

                    # Workflow - initially draft
                    workflow_status='draft',
                    gl_posted=False,
                    created_by=user_id
                )

                session.add(payment)
                session.flush()

                # 6a. NEW: Create DEBIT subledger entry for advance payment (no invoice)
                # This creates the double-entry: DEBIT when advance is paid, CREDIT when allocated
                if not data.get('invoice_id'):
                    # This is an advance payment (no invoice) - create DEBIT entry
                    from app.models.transaction import SupplierAdvanceAdjustment

                    debit_entry = SupplierAdvanceAdjustment(
                        adjustment_id=uuid.uuid4(),
                        hospital_id=uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id,
                        branch_id=uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id,
                        source_payment_id=payment.payment_id,  # The advance payment itself
                        target_payment_id=None,  # No target yet (not allocated)
                        invoice_id=None,  # No invoice
                        supplier_id=payment.supplier_id,
                        amount=payment.amount,  # Full payment amount is the advance
                        adjustment_date=datetime.now(timezone.utc),
                        adjustment_type='advance_receipt',  # NEW type: receipt of advance
                        notes=f"Advance payment received: ₹{payment.amount}",
                        created_by=user_id,
                        updated_by=user_id
                    )
                    session.add(debit_entry)
                    logger.info(f"Created DEBIT subledger entry for advance payment: {payment.payment_id}, amount: ₹{payment.amount}")

                # 6b. Create CREDIT subledger entries for advance allocation (if any)
                if advance_allocation > 0 and allocation_result.get('payments'):
                    from app.models.transaction import SupplierAdvanceAdjustment

                    allocated_payments = allocation_result.get('payments', [])
                    logger.info(f"Creating {len(allocated_payments)} subledger entries for advance allocation")

                    for alloc in allocated_payments:
                        # CRITICAL FIX: Always use original_payment_id as the source
                        # This is the actual advance payment that's being reduced/used
                        source_id = uuid.UUID(alloc['original_payment_id'])

                        adjustment = SupplierAdvanceAdjustment(
                            adjustment_id=uuid.uuid4(),
                            hospital_id=uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id,
                            branch_id=uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id,
                            source_payment_id=source_id,  # FIXED: Use original_payment_id (the actual advance payment)
                            target_payment_id=payment.payment_id,  # Link to the new payment (invoice payment)
                            invoice_id=payment.invoice_id,
                            supplier_id=payment.supplier_id,
                            amount=Decimal(str(alloc['amount'])),
                            adjustment_date=datetime.now(timezone.utc),
                            adjustment_type='allocation',
                            notes=f"Allocated ₹{alloc['amount']} from {'full' if alloc['allocation_type'] == 'full' else 'partial'} advance payment",
                            created_by=user_id,
                            updated_by=user_id
                        )
                        session.add(adjustment)
                        logger.info(f"Created subledger entry: {adjustment.adjustment_id} for ₹{alloc['amount']} from source {source_id}")

                    session.flush()
                    logger.info(f"All subledger entries created successfully")

                # 7. Check if saving as draft or requires approval
                save_as_draft = data.get('save_as_draft', False)

                if save_as_draft:
                    # User explicitly chose to save as draft - keep workflow_status as 'draft'
                    payment.workflow_status = 'draft'
                    logger.info(f"Payment saved as draft per user request: {payment.payment_id}")
                else:
                    # Normal submission flow - check if requires approval
                    requires_approval = self._requires_approval(payment, session)

                    if requires_approval:
                        payment.requires_approval = True
                        payment.workflow_status = 'pending_approval'
                        payment.submitted_for_approval_at = datetime.now(timezone.utc)
                        payment.submitted_by = user_id
                        payment.next_approver_id = self._get_next_approver(payment, session)
                    else:
                        # Auto-approve for amounts below threshold
                        payment.workflow_status = 'approved'
                        payment.approved_by = user_id
                        payment.approved_at = datetime.now(timezone.utc)

                        # Post GL entries for auto-approved payments
                        from app.services.gl_service import create_supplier_payment_gl_entries
                        try:
                            gl_result = create_supplier_payment_gl_entries(
                                payment.payment_id, user_id, session
                            )
                            payment.gl_posted = True
                            payment.gl_entry_id = gl_result.get('transaction_id')
                            payment.posting_date = datetime.now(timezone.utc)
                        except Exception as gl_error:
                            logger.error(f"GL posting failed but payment will be created without GL: {str(gl_error)}")
                            payment.posting_errors = str(gl_error)
                            payment.gl_posted = False
                            # Don't rollback - just continue without GL posting

                # CRITICAL FIX: Cache values BEFORE commit to avoid session access after commit
                payment_id_str = str(payment.payment_id)
                invoice_id_cached = payment.invoice_id  # Cache before commit
                payment_dict = get_entity_dict(payment)  # Get dict before commit

                # Commit payment
                session.commit()

            # END OF SESSION CONTEXT - Now outside the 'with' block

            # Update invoice payment status AFTER session closes (opens its own session)
            if invoice_id_cached:
                try:
                    from app.services.supplier_invoice_service import SupplierInvoiceService
                    invoice_service = SupplierInvoiceService()
                    # This opens its own session, so it's safe
                    invoice_service.update_payment_status(invoice_id_cached, None)
                except Exception as inv_error:
                    logger.error(f"Error updating invoice status: {str(inv_error)}")
                    # Continue anyway - payment is saved

            # 5. Invalidate caches
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('supplier_payments', cascade=False)
            if invoice_id_cached:
                invalidate_service_cache_for_entity('supplier_invoices', cascade=False)

            # Build success message
            workflow_msg = "and submitted for approval" if requires_approval else "and approved"
            advance_msg = f" (₹{advance_allocation:.2f} allocated from advance)" if advance_allocation > 0 else ""

            return {
                'success': True,
                'data': payment_dict,  # Use cached dict
                'payment_id': payment_id_str,  # Use cached ID
                'message': f'Payment of ₹{net_new_payment:.2f} created successfully {workflow_msg}{advance_msg}',
                'advance_allocated': float(advance_allocation) if advance_allocation > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def update_payment(self, payment_id: str, data: Dict, hospital_id: str, **context) -> Dict:
        """
        Update existing payment (only if draft or rejected status)

        Args:
            payment_id: Payment ID to update
            data: Updated payment data
            hospital_id: Hospital ID
            context: Additional context (user_id, etc.)

        Returns:
            Dict with success status and message
        """
        try:
            user_id = context.get('user_id')

            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter_by(
                    payment_id=uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id,
                    hospital_id=uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id
                ).first()

                if not payment:
                    return {'success': False, 'error': 'Payment not found'}

                # Validate status - only draft or rejected can be edited
                if payment.workflow_status not in ['draft', 'rejected']:
                    return {
                        'success': False,
                        'error': f'Cannot edit payment with status: {payment.workflow_status}'
                    }

                # Validate multi-method amounts
                if not self._validate_multi_method_amounts(data):
                    return {
                        'success': False,
                        'error': 'Sum of payment method amounts must equal total amount'
                    }

                # Update editable fields
                payment.amount = Decimal(str(data.get('amount', payment.amount)))
                payment.payment_date = data.get('payment_date', payment.payment_date)
                payment.payment_method = data.get('payment_method', payment.payment_method)
                payment.reference_no = data.get('reference_no', payment.reference_no)
                payment.notes = data.get('notes', payment.notes)

                # Update multi-method amounts
                payment.cash_amount = Decimal(str(data.get('cash_amount', 0)))
                payment.cheque_amount = Decimal(str(data.get('cheque_amount', 0)))
                payment.bank_transfer_amount = Decimal(str(data.get('bank_transfer_amount', 0)))
                payment.upi_amount = Decimal(str(data.get('upi_amount', 0)))

                # Update method-specific details
                if data.get('cheque_number'):
                    payment.cheque_number = data.get('cheque_number')
                    payment.cheque_date = data.get('cheque_date')
                    payment.cheque_bank = data.get('cheque_bank')
                    payment.cheque_branch = data.get('cheque_branch')

                if data.get('bank_reference_number'):
                    payment.bank_name = data.get('bank_name')
                    payment.bank_branch = data.get('bank_branch')
                    payment.bank_reference_number = data.get('bank_reference_number')
                    payment.ifsc_code = data.get('ifsc_code')
                    payment.transfer_mode = data.get('transfer_mode')

                if data.get('upi_transaction_id'):
                    payment.upi_id = data.get('upi_id')
                    payment.upi_app_name = data.get('upi_app_name')
                    payment.upi_transaction_id = data.get('upi_transaction_id')
                    payment.upi_reference_id = data.get('upi_reference_id')

                # Update TDS
                if 'tds_applicable' in data:
                    payment.tds_applicable = data.get('tds_applicable')
                    payment.tds_rate = Decimal(str(data.get('tds_rate', 0))) if data.get('tds_rate') else Decimal('0')
                    payment.tds_amount = Decimal(str(data.get('tds_amount', 0))) if data.get('tds_amount') else Decimal('0')
                    payment.tds_reference = data.get('tds_reference')

                # Reset workflow status to draft if it was rejected
                if payment.workflow_status == 'rejected':
                    payment.workflow_status = 'draft'
                    payment.rejected_by = None
                    payment.rejected_at = None
                    payment.rejection_reason = None

                payment.updated_by = user_id
                payment.updated_at = datetime.now(timezone.utc)

                session.commit()

                # Invalidate caches
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('supplier_payments', cascade=False)

                return {
                    'success': True,
                    'message': 'Payment updated successfully',
                    'data': get_entity_dict(payment)
                }

        except Exception as e:
            logger.error(f"Error updating payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==========================================================================
    # APPROVAL WORKFLOW OPERATIONS
    # ==========================================================================

    def approve_payment(self, payment_id: str, approver_id: str, notes: str = None, **context) -> Dict:
        """
        Approve payment and post GL entries

        NOTE: This service method is deprecated. Use ApprovalMixin pattern in supplier_views.approve_payment instead.

        Args:
            payment_id: Payment ID to approve
            approver_id: User ID of approver
            notes: Optional approval notes
            context: Additional context

        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter_by(
                    payment_id=uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                ).first()

                if not payment:
                    return {'success': False, 'error': 'Payment not found'}

                if payment.workflow_status != 'pending_approval':
                    return {
                        'success': False,
                        'error': f'Payment is not pending approval (current status: {payment.workflow_status})'
                    }

                # Update payment status
                payment.workflow_status = 'approved'
                payment.approved_by = approver_id
                payment.approved_at = datetime.now(timezone.utc)
                payment.approval_notes = notes

                # Post GL entries
                from app.services.gl_service import create_supplier_payment_gl_entries
                try:
                    gl_result = create_supplier_payment_gl_entries(
                        payment.payment_id, approver_id, session
                    )
                    payment.gl_posted = True
                    payment.gl_entry_id = gl_result.get('transaction_id')
                    payment.posting_date = datetime.now(timezone.utc)

                    logger.info(f"GL entries posted successfully for payment {payment_id}")
                except Exception as gl_error:
                    logger.error(f"GL posting failed during approval: {str(gl_error)}", exc_info=True)
                    return {
                        'success': False,
                        'error': f'Payment approved but GL posting failed: {str(gl_error)}'
                    }

                # Update invoice payment status if applicable
                if payment.invoice_id:
                    from app.services.supplier_invoice_service import SupplierInvoiceService
                    invoice_service = SupplierInvoiceService()
                    invoice_service.update_payment_status(payment.invoice_id, session)

                session.commit()

                # Invalidate caches
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('supplier_payments', cascade=False)
                if payment.invoice_id:
                    invalidate_service_cache_for_entity('supplier_invoices', cascade=False)

                return {
                    'success': True,
                    'message': 'Payment approved and GL entries posted successfully'
                }

        except Exception as e:
            logger.error(f"Error approving payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def reject_payment(self, payment_id: str, rejector_id: str, reason: str, **context) -> Dict:
        """
        Reject payment

        Args:
            payment_id: Payment ID to reject
            rejector_id: User ID of rejector
            reason: Rejection reason
            context: Additional context

        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter_by(
                    payment_id=uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                ).first()

                if not payment:
                    return {'success': False, 'error': 'Payment not found'}

                if payment.workflow_status != 'pending_approval':
                    return {
                        'success': False,
                        'error': f'Payment is not pending approval (current status: {payment.workflow_status})'
                    }

                # Update payment status
                payment.workflow_status = 'rejected'
                payment.rejected_by = rejector_id
                payment.rejected_at = datetime.now(timezone.utc)
                payment.rejection_reason = reason

                session.commit()

                # Invalidate cache
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('supplier_payments', cascade=False)

                return {
                    'success': True,
                    'message': 'Payment rejected. It can now be edited and resubmitted for approval.'
                }

        except Exception as e:
            logger.error(f"Error rejecting payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==========================================================================
    # SOFT DELETE & RESTORE OPERATIONS
    # ==========================================================================

    def delete_payment(self, payment_id: str, user_id: str, reason: str = None, reversal_type: str = 'entry_error', **context) -> Dict:
        """
        Soft delete payment with GL reversal if needed

        Args:
            payment_id: Payment ID to delete
            user_id: User ID performing deletion
            reason: Deletion reason
            reversal_type: Type of reversal ('entry_error', 'overpayment', 'duplicate')
                          - 'entry_error': Simple reversal, money not transferred
                          - 'overpayment'/'duplicate': Creates supplier advance (money already with supplier)
            context: Additional context

        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter_by(
                    payment_id=uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id
                ).first()

                if not payment:
                    return {'success': False, 'error': 'Payment not found'}

                # Validate can be deleted (only draft or rejected)
                if payment.workflow_status not in ['draft', 'rejected']:
                    return {
                        'success': False,
                        'error': f'Only draft or rejected payments can be deleted (current status: {payment.workflow_status})'
                    }

                # If GL was posted, reverse it first
                if payment.gl_posted and payment.gl_entry_id:
                    from app.services.gl_service import reverse_supplier_payment_gl_entries
                    try:
                        reverse_supplier_payment_gl_entries(
                            payment.payment_id, user_id, session
                        )
                        logger.info(f"GL entries reversed for payment {payment_id}")
                    except Exception as gl_error:
                        logger.error(f"GL reversal failed: {str(gl_error)}", exc_info=True)
                        return {
                            'success': False,
                            'error': f'GL reversal failed: {str(gl_error)}'
                        }

                # ✅ NEW: Create supplier advance if money was physically transferred
                # Best Practice: Track as advance to adjust in future payments
                if reversal_type in ['overpayment', 'duplicate']:
                    from app.models.transaction import SupplierAdvanceAdjustment
                    from datetime import datetime, timezone

                    advance_entry = SupplierAdvanceAdjustment(
                        adjustment_id=uuid.uuid4(),
                        hospital_id=payment.hospital_id,
                        branch_id=payment.branch_id,
                        source_payment_id=payment.payment_id,  # Reference to reversed payment
                        target_payment_id=None,  # Not allocated yet
                        invoice_id=payment.invoice_id if payment.invoice_id else None,
                        supplier_id=payment.supplier_id,
                        amount=payment.amount,
                        adjustment_date=datetime.now(timezone.utc),
                        adjustment_type='reversal',  # ✅ FIXED: Use 'reversal' not 'payment_reversal'
                        notes=f"Payment deletion/reversal - {reversal_type}: {reason or 'No reason specified'}. Original payment: {payment.reference_no or payment.payment_id}",
                        created_by=user_id,
                        updated_by=user_id
                    )
                    session.add(advance_entry)
                    logger.info(f"Created supplier advance from payment reversal: ₹{payment.amount} for supplier {payment.supplier_id}")

                # Soft delete using model mixin method
                payment.soft_delete(user_id, reason, cascade_to_children=False)

                # ✅ CRITICAL FIX: Cache values BEFORE commit to avoid detached instance access
                invoice_id_cached = payment.invoice_id
                amount_cached = float(payment.amount)

                # Update invoice payment status if applicable
                if invoice_id_cached:
                    from app.services.supplier_invoice_service import SupplierInvoiceService
                    invoice_service = SupplierInvoiceService()
                    invoice_service.update_payment_status(invoice_id_cached, session)

                session.commit()

            # ✅ OUTSIDE SESSION: Use cached values to avoid detached instance errors
            # Invalidate caches
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('supplier_payments', cascade=False)
            if invoice_id_cached:
                invalidate_service_cache_for_entity('supplier_invoices', cascade=False)

            success_msg = 'Payment deleted successfully'
            if reversal_type in ['overpayment', 'duplicate']:
                success_msg += f'. Supplier advance of ₹{amount_cached} created for future adjustment.'

            return {
                'success': True,
                'message': success_msg
            }

        except Exception as e:
            logger.error(f"Error deleting payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def restore_payment(self, payment_id: str, user_id: str, **context) -> Dict:
        """
        Restore soft-deleted payment

        Args:
            payment_id: Payment ID to restore
            user_id: User ID performing restoration
            context: Additional context

        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == uuid.UUID(payment_id) if isinstance(payment_id, str) else payment_id,
                    SupplierPayment.is_deleted == True
                ).first()

                if not payment:
                    return {'success': False, 'error': 'Deleted payment not found'}

                # Restore using model mixin method
                payment.undelete(user_id)

                session.commit()

                # Invalidate cache
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('supplier_payments', cascade=False)

                return {
                    'success': True,
                    'message': 'Payment restored successfully. You may need to resubmit for approval if required.'
                }

        except Exception as e:
            logger.error(f"Error restoring payment: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_supplier_advance_balance(self, supplier_id: str, hospital_id: str) -> Dict:
        """
        Get total unallocated payments (advances) for a supplier

        Args:
            supplier_id: Supplier ID
            hospital_id: Hospital ID

        Returns:
            Dict with advance_balance, payment_count, and payment_details
        """
        try:
            from sqlalchemy import func

            logger.info(f"[GET_ADVANCE] Getting advance balance for supplier={supplier_id}")

            # Use regular session instead of read_only to ensure we see committed changes
            with get_db_session(read_only=False) as session:
                # Query all approved payments without invoice_id (unallocated/advances)
                query = session.query(
                    func.sum(SupplierPayment.amount).label('total_advance'),
                    func.count(SupplierPayment.payment_id).label('payment_count')
                ).filter(
                    SupplierPayment.supplier_id == uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id,
                    SupplierPayment.hospital_id == hospital_id,
                    SupplierPayment.invoice_id.is_(None),  # Unallocated payments
                    SupplierPayment.workflow_status == 'approved',  # Only approved
                    SupplierPayment.is_deleted == False  # Not deleted
                )

                result = query.first()
                total_advance = float(result.total_advance) if result.total_advance else 0.0
                payment_count = result.payment_count or 0

                logger.info(f"[GET_ADVANCE] Query result: total_advance=₹{total_advance:.2f}, payment_count={payment_count}")

                # Get individual payment details
                payments = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id,
                    SupplierPayment.hospital_id == hospital_id,
                    SupplierPayment.invoice_id.is_(None),
                    SupplierPayment.workflow_status == 'approved',
                    SupplierPayment.is_deleted == False
                ).order_by(SupplierPayment.payment_date.desc()).all()

                payment_details = []
                for payment in payments:
                    logger.info(f"[GET_ADVANCE] Found unallocated payment: {payment.payment_id}, amount=₹{payment.amount}, invoice_id={payment.invoice_id}")
                    payment_details.append({
                        'payment_id': str(payment.payment_id),
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'amount': float(payment.amount),
                        'payment_method': payment.payment_method,
                        'reference_no': payment.reference_no
                    })

                logger.info(f"[GET_ADVANCE] ✅ Returning advance_balance=₹{total_advance:.2f}, payment_count={payment_count}")

                return {
                    'success': True,
                    'advance_balance': total_advance,
                    'payment_count': payment_count,
                    'payments': payment_details
                }

        except Exception as e:
            logger.error(f"Error getting supplier advance balance: {str(e)}", exc_info=True)
            return {
                'success': False,
                'advance_balance': 0.0,
                'payment_count': 0,
                'payments': [],
                'error': str(e)
            }

    def _allocate_advance_to_invoice(
        self,
        supplier_id: str,
        invoice_id: str,
        allocation_amount: Decimal,
        hospital_id: str,
        user_id: str,
        session: Session
    ) -> Dict:
        """
        Allocate unallocated payments (advances) to an invoice using FIFO method

        Args:
            supplier_id: Supplier ID
            invoice_id: Invoice ID to allocate to
            allocation_amount: Amount to allocate
            hospital_id: Hospital ID
            user_id: User performing allocation
            session: Database session

        Returns:
            Dict with success status and details
        """
        try:
            logger.info(f"[ADVANCE_ALLOC] Starting allocation: supplier={supplier_id}, invoice={invoice_id}, amount=₹{allocation_amount}")

            # Query unallocated payments for this supplier (oldest first - FIFO)
            unallocated_payments = session.query(SupplierPayment).filter(
                SupplierPayment.supplier_id == uuid.UUID(supplier_id) if isinstance(supplier_id, str) else supplier_id,
                SupplierPayment.hospital_id == hospital_id,
                SupplierPayment.invoice_id.is_(None),  # Unallocated
                SupplierPayment.workflow_status == 'approved',  # Only approved payments
                SupplierPayment.is_deleted == False  # Not deleted
            ).order_by(SupplierPayment.payment_date.asc()).all()  # FIFO - oldest first

            logger.info(f"[ADVANCE_ALLOC] Found {len(unallocated_payments)} unallocated payments")

            if not unallocated_payments:
                return {
                    'success': False,
                    'error': 'No unallocated payments found for this supplier'
                }

            # Calculate total available advance
            total_available = sum(float(p.amount) for p in unallocated_payments)
            logger.info(f"[ADVANCE_ALLOC] Total available advance: ₹{total_available:.2f}")

            if Decimal(str(total_available)) < allocation_amount:
                return {
                    'success': False,
                    'error': f'Insufficient advance balance. Available: ₹{total_available:.2f}, Required: ₹{allocation_amount:.2f}'
                }

            # Allocate payments using FIFO until we reach the allocation amount
            # Support PARTIAL allocation by splitting payments if needed
            allocated_total = Decimal('0')
            allocated_payments = []
            remaining_to_allocate = allocation_amount

            for payment in unallocated_payments:
                if remaining_to_allocate <= Decimal('0.01'):
                    break

                logger.info(f"[ADVANCE_ALLOC] Processing payment {payment.payment_id}: ₹{payment.amount}, remaining to allocate: ₹{remaining_to_allocate}")

                # Check if we need full or partial allocation
                if payment.amount <= remaining_to_allocate:
                    # Allocate the ENTIRE payment
                    logger.info(f"[ADVANCE_ALLOC] Full allocation: Linking entire payment ₹{payment.amount} to invoice")
                    payment.invoice_id = uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id
                    payment.updated_by = user_id
                    payment.updated_at = datetime.now(timezone.utc)

                    allocated_total += payment.amount
                    remaining_to_allocate -= payment.amount

                    allocated_payments.append({
                        'payment_id': str(payment.payment_id),
                        'original_payment_id': str(payment.payment_id),  # ADDED: For consistency, same as payment_id for full allocation
                        'amount': float(payment.amount),
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'allocation_type': 'full'
                    })

                    logger.info(f"[ADVANCE_ALLOC] ✓ Fully allocated payment {payment.payment_id} (₹{payment.amount})")

                else:
                    # PARTIAL allocation - need to split the payment
                    logger.info(f"[ADVANCE_ALLOC] Partial allocation: Splitting payment ₹{payment.amount} into ₹{remaining_to_allocate} (allocated) and ₹{payment.amount - remaining_to_allocate} (remaining)")

                    # Create new payment for the allocated portion
                    # Keep reference_no under 50 chars limit
                    orig_ref = payment.reference_no or str(payment.payment_id)[:8]
                    new_reference = f"ADV-{orig_ref}"[:50]  # Truncate to 50 chars

                    allocated_portion = SupplierPayment(
                        payment_id=uuid.uuid4(),
                        hospital_id=payment.hospital_id,
                        branch_id=payment.branch_id,
                        supplier_id=payment.supplier_id,
                        invoice_id=uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id,
                        amount=remaining_to_allocate,
                        payment_date=payment.payment_date,
                        payment_method=payment.payment_method,
                        payment_category='advance_allocation',
                        payment_source=payment.payment_source,
                        reference_no=new_reference,
                        notes=f"Allocated from advance payment {payment.payment_id}",
                        workflow_status='approved',  # Inherit approved status
                        gl_posted=payment.gl_posted,  # GL already posted from original
                        created_by=user_id,
                        updated_by=user_id
                    )
                    session.add(allocated_portion)

                    # Reduce the original payment amount to the remaining unallocated portion
                    original_amount = payment.amount
                    payment.amount = payment.amount - remaining_to_allocate
                    payment.updated_by = user_id
                    payment.updated_at = datetime.now(timezone.utc)

                    # FIXED: Prevent notes field overflow (255 char limit)
                    # Keep only the latest split info to avoid accumulation
                    split_note = f"Split: ₹{remaining_to_allocate} to inv {str(invoice_id)[:8]}"
                    existing_notes = (payment.notes or '').strip()

                    # If existing notes are too long, truncate the beginning
                    max_length = 220  # Leave room for new split note
                    if len(existing_notes) > max_length:
                        existing_notes = "..." + existing_notes[-(max_length-3):]

                    # Append new split note, ensuring total doesn't exceed 255
                    payment.notes = f"{existing_notes} | {split_note}".strip()[:255]

                    allocated_total += remaining_to_allocate
                    allocated_payments.append({
                        'payment_id': str(allocated_portion.payment_id),
                        'original_payment_id': str(payment.payment_id),
                        'amount': float(remaining_to_allocate),
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'allocation_type': 'partial',
                        'original_amount': float(original_amount),
                        'remaining_amount': float(payment.amount)
                    })

                    logger.info(f"[ADVANCE_ALLOC] ✓ Split payment: Created new payment {allocated_portion.payment_id} for ₹{remaining_to_allocate}, reduced original to ₹{payment.amount}")

                    remaining_to_allocate = Decimal('0')
                    break  # We're done

            # Verify we allocated the correct amount (within tolerance)
            if abs(allocated_total - allocation_amount) > Decimal('0.01'):
                logger.error(f"[ADVANCE_ALLOC] Allocation mismatch! Allocated: ₹{allocated_total:.2f}, Required: ₹{allocation_amount:.2f}")
                return {
                    'success': False,
                    'error': f'Allocation mismatch. Allocated: ₹{allocated_total:.2f}, Required: ₹{allocation_amount:.2f}'
                }

            # Flush changes to ensure they're in the session
            session.flush()

            logger.info(f"[ADVANCE_ALLOC] ✅ Successfully allocated ₹{allocated_total:.2f} from {len(allocated_payments)} payments to invoice {invoice_id}")

            return {
                'success': True,
                'allocated_amount': float(allocated_total),
                'payment_count': len(allocated_payments),
                'payments': allocated_payments
            }

        except Exception as e:
            logger.error(f"Error allocating advance to invoice: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    # ==========================================================================
    # VALIDATION HELPER METHODS
    # ==========================================================================

    def _validate_multi_method_amounts(self, data: Dict) -> bool:
        """
        Validate that sum of payment method amounts equals total amount
        Includes advance allocation as a payment method

        Args:
            data: Payment data dictionary

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            total = Decimal(str(data.get('amount', 0)))
            method_sum = (
                Decimal(str(data.get('advance_allocation_amount', 0))) +
                Decimal(str(data.get('cash_amount', 0))) +
                Decimal(str(data.get('cheque_amount', 0))) +
                Decimal(str(data.get('bank_transfer_amount', 0))) +
                Decimal(str(data.get('upi_amount', 0)))
            )

            # Allow small rounding differences (1 paisa = 0.01)
            return abs(total - method_sum) <= Decimal('0.01')

        except Exception as e:
            logger.error(f"Error validating multi-method amounts: {str(e)}")
            return False

    def _requires_approval(self, payment: SupplierPayment, session: Session) -> bool:
        """
        Check if payment requires approval based on amount threshold

        Args:
            payment: SupplierPayment instance
            session: Database session

        Returns:
            bool: True if requires approval, False otherwise
        """
        try:
            # TODO: Get approval threshold from posting_config_service
            # For now, use a default threshold of 10,000
            approval_threshold = Decimal('10000.00')

            return payment.amount >= approval_threshold

        except Exception as e:
            logger.error(f"Error checking approval requirement: {str(e)}")
            # Default to requiring approval on error for safety
            return True

    def _get_next_approver(self, payment: SupplierPayment, session: Session) -> Optional[str]:
        """
        Get next approver from approval hierarchy

        Args:
            payment: SupplierPayment instance
            session: Database session

        Returns:
            Optional[str]: User ID of next approver or None
        """
        try:
            # TODO: Implement approval hierarchy logic
            # For now, return None (manual assignment required)
            return None

        except Exception as e:
            logger.error(f"Error getting next approver: {str(e)}")
            return None
