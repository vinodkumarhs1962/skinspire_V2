# File: app/services/purchase_order_service.py
# SIMPLIFIED VERSION - Using Universal Engine with Database View

from typing import Dict, Optional, List
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.views import PurchaseOrderView
from app.models.transaction import (
    PurchaseOrderHeader, PurchaseOrderLine, 
    SupplierInvoice, SupplierPayment
)
from app.engine.universal_entity_service import UniversalEntityService
from app.engine.business.line_items_handler import line_items_handler
from app.services.database_service import get_db_session
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class PurchaseOrderService(UniversalEntityService):
    """
    Purchase Order service - leverages Universal Engine with database view
    Only contains PO-specific business logic methods
    """
    
    def __init__(self):
        """Initialize with purchase_orders entity type and view model"""
        super().__init__('purchase_orders', PurchaseOrderView)
        logger.info("✅ Initialized PurchaseOrderService with PurchaseOrderView")
    
    
    # =========================================================================
    # LINE ITEMS DISPLAY - Required for detail view
    # =========================================================================
    
    def get_po_line_items_display(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get PO line items - delegates to centralized handler
        """
        po_id = item_id or (item.get('po_id') if item else None)
        
        # Call centralized function
        return line_items_handler.get_po_line_items(
            po_id=po_id,
            context='po_detail',
            **kwargs
        )

    # =========================================================================
    # INVOICES DISPLAY - Required for financials tab
    # =========================================================================
    
    @cache_service_method('purchase_orders', 'has_invoice')
    def _check_po_has_invoice(self, po_id: str, include_deleted: bool = False) -> bool:
        """
        Check if PO has any invoices
        
        Args:
            po_id: Purchase order ID
            include_deleted: If True, include soft-deleted invoices in check
        
        Returns:
            Boolean indicating if PO has invoices
        """
        try:
            if isinstance(po_id, str):
                po_id = uuid.UUID(po_id)
                
            with get_db_session() as session:
                from app.models.transaction import SupplierInvoice
                
                query = session.query(SupplierInvoice).filter_by(po_id=po_id)
                
                # Apply soft delete filter if needed
                if not include_deleted:
                    query = query.filter(SupplierInvoice.is_deleted == False)
                
                return query.count() > 0
                
        except Exception as e:
            logger.error(f"Error checking invoices for PO {po_id}: {str(e)}")
            return False

    # ✅ ENHANCED: Update the existing get_po_invoices method for consistency
    def get_po_invoices(self, item_id: str = None, item: dict = None, include_deleted: bool = False, **kwargs) -> Dict:
        """
        Get invoices linked to this PO for financials tab
        ✅ ENHANCED: Added soft delete support parameter
        """
        try:
            po_id = None
            if item and isinstance(item, dict):
                po_id = item.get('po_id')
            elif item_id:
                po_id = item_id
                
            if not po_id:
                return {'items': [], 'has_invoices': False}
            
            if isinstance(po_id, str):
                po_id = uuid.UUID(po_id)
                
            with get_db_session() as session:
                query = session.query(SupplierInvoice).filter_by(po_id=po_id)
                
                # ✅ NEW: Soft delete filtering
                if not include_deleted:
                    query = query.filter(SupplierInvoice.is_deleted == False)
                
                invoices = query.all()
                
                invoice_list = []
                total_invoice_amount = 0
                
                for inv in invoices:
                    inv_dict = {
                        'invoice_number': inv.supplier_invoice_number,
                        'invoice_date': inv.invoice_date,
                        'total_amount': float(inv.total_amount or 0),
                        'payment_status': getattr(inv, 'payment_status', 'pending'),
                        'invoice_id': str(inv.invoice_id),
                        'is_deleted': bool(getattr(inv, 'is_deleted', False)),  # ✅ NEW: Include deletion status
                        'deleted_at': getattr(inv, 'deleted_at', None),
                        'deleted_by': getattr(inv, 'deleted_by', None)
                    }
                    invoice_list.append(inv_dict)
                    total_invoice_amount += inv_dict['total_amount']
                    
                return {
                    'items': invoice_list,
                    'has_invoices': bool(invoice_list),
                    'currency_symbol': '₹',
                    'summary': {
                        'total_invoices': len(invoice_list),
                        'active_invoices': len([i for i in invoice_list if not i['is_deleted']]),  # ✅ NEW
                        'deleted_invoices': len([i for i in invoice_list if i['is_deleted']]),     # ✅ NEW
                        'total_amount': total_invoice_amount
                    }
                }
        except Exception as e:
            logger.error(f"Error getting PO invoices: {str(e)}")
            return {'items': [], 'has_invoices': False}

    # ✅ NEW: Add helper methods for action conditions
    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add virtual/calculated fields to detail view data
        ✅ ENHANCED: Uses the new _check_po_has_invoice method
        """
        try:
            po_id = item_id or result.get('po_id')
            if po_id:
                # Check invoice existence with soft delete awareness
                has_invoice = self._check_po_has_invoice(po_id, include_deleted=False)
                has_any_invoice = self._check_po_has_invoice(po_id, include_deleted=True)
                
                result['has_invoice'] = has_invoice
                result['has_any_invoice'] = has_any_invoice  # ✅ NEW: Including deleted invoices
                
                # Enhanced invoice count
                invoice_count = self._get_po_invoice_count(po_id)
                result['invoice_count'] = invoice_count
                
                # ✅ NEW: Approval status calculations
                result.update(self._calculate_approval_status(result))
                
                # ✅ NEW: Action visibility calculations
                result.update(self._calculate_action_conditions(result, has_invoice))
                
                # ✅ NEW: Business analytics
                result.update(self._calculate_business_metrics(result))

            return result
            
        except Exception as e:
            logger.warning(f"Error adding virtual calculations for PO {item_id}: {str(e)}")
            return result

    def _calculate_approval_status(self, result: Dict) -> Dict:
        """
        Calculate approval-related virtual fields
        ✅ NEW: Comprehensive approval tracking
        """
        calculations = {}
        
        # Basic approval status
        if result.get('approved_by') and result.get('approved_at'):
            calculations['approval_status'] = 'Approved'
            
            # Calculate days since approval
            if result.get('approved_at'):
                try:
                    from datetime import datetime, timezone
                    approved_date = result['approved_at']
                    if isinstance(approved_date, str):
                        # Parse ISO format datetime string
                        approved_date = datetime.fromisoformat(approved_date.replace('Z', '+00:00'))
                    
                    days_since = (datetime.now(timezone.utc) - approved_date).days
                    calculations['days_since_approval'] = days_since
                except Exception as e:
                    logger.warning(f"Error calculating days since approval: {str(e)}")
                    calculations['days_since_approval'] = 0
        elif result.get('status') == 'draft':
            calculations['approval_status'] = 'Pending Approval'
        else:
            calculations['approval_status'] = 'Draft'
        
        return calculations
    
    def _calculate_action_conditions(self, result: Dict, has_invoice: bool) -> Dict:
        """
        Calculate action visibility conditions
        ✅ NEW: Dynamic action control based on business rules
        """
        calculations = {}
        
        status = result.get('status', '').lower()
        is_deleted = result.get('is_deleted', False)
        
        # Can be edited: Draft status, not deleted, no invoices
        calculations['can_be_edited'] = (
            status == 'draft' and 
            not is_deleted and 
            not has_invoice
        )
        
        # Can be approved: Draft status, not deleted, not already approved
        calculations['can_be_approved'] = (
            status == 'draft' and 
            not is_deleted and
            not result.get('approved_by')
        )
        
        # Can be unapproved: Approved status, not deleted, no invoices
        calculations['can_be_unapproved'] = (
            status == 'approved' and 
            not is_deleted and 
            not has_invoice
        )
        
        # Can be deleted: Draft status, not deleted, no invoices
        calculations['can_be_deleted'] = (
            status == 'draft' and 
            not is_deleted and 
            not has_invoice
        )
        
        # Can be cancelled: Draft or approved status, not deleted, no invoices  
        calculations['can_be_cancelled'] = (
            status in ['draft', 'approved'] and 
            not is_deleted and 
            not has_invoice
        )
        
        return calculations
    
    def _calculate_business_metrics(self, result: Dict) -> Dict:
        """
        Calculate business analytics and metrics
        ✅ NEW: Enhanced business intelligence
        """
        calculations = {}
        
        try:
            # Days since PO creation
            if result.get('po_date'):
                po_date = result['po_date']
                if isinstance(po_date, str):
                    from datetime import datetime
                    po_date = datetime.fromisoformat(po_date.replace('Z', '+00:00'))
                
                days_since_po = (datetime.now(timezone.utc) - po_date).days
                calculations['days_since_po'] = days_since_po
                
                # Categorize by age
                if days_since_po <= 7:
                    calculations['po_age_category'] = 'Recent'
                elif days_since_po <= 30:
                    calculations['po_age_category'] = 'Current'
                elif days_since_po <= 90:
                    calculations['po_age_category'] = 'Aging'
                else:
                    calculations['po_age_category'] = 'Old'
            
            # Expected delivery status
            if result.get('expected_delivery_date'):
                expected_date = result['expected_delivery_date']
                if isinstance(expected_date, str):
                    from datetime import datetime, date
                    expected_date = datetime.strptime(expected_date, '%Y-%m-%d').date()
                
                today = date.today()
                days_until_delivery = (expected_date - today).days
                calculations['days_until_delivery'] = days_until_delivery
                
                if days_until_delivery < 0:
                    calculations['delivery_status'] = 'Overdue'
                elif days_until_delivery <= 3:
                    calculations['delivery_status'] = 'Due Soon'
                elif days_until_delivery <= 7:
                    calculations['delivery_status'] = 'This Week'
                else:
                    calculations['delivery_status'] = 'Future'
            
            # Total amount categorization
            total_amount = float(result.get('total_amount', 0))
            if total_amount >= 100000:
                calculations['amount_category'] = 'High Value'
            elif total_amount >= 25000:
                calculations['amount_category'] = 'Medium Value'
            else:
                calculations['amount_category'] = 'Low Value'
                
        except Exception as e:
            logger.warning(f"Error calculating business metrics: {str(e)}")
        
        return calculations

    @cache_service_method('purchase_orders', 'invoice_count')
    def _get_po_invoice_count(self, po_id: str, include_deleted: bool = False) -> int:
        """
        Get count of invoices for this PO
        ✅ ENHANCED: With soft delete awareness
        """
        try:
            if isinstance(po_id, str):
                po_id = uuid.UUID(po_id)
                
            with get_db_session() as session:
                from app.models.transaction import SupplierInvoice
                
                query = session.query(SupplierInvoice).filter_by(po_id=po_id)
                
                if not include_deleted:
                    query = query.filter(SupplierInvoice.is_deleted == False)
                
                return query.count()
                
        except Exception as e:
            logger.error(f"Error getting invoice count for PO {po_id}: {str(e)}")
            return 0


    # =========================================================================
    # CACHE INVALIDATION - Clear cache after status changes
    # =========================================================================
    
    def invalidate_cache(self, po_id: str = None):
        """
        Invalidate all caches for purchase orders after status change
        This ensures list view shows updated status immediately
        """
        try:
            # Use the centralized cache invalidation method
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            
            # This method exists and works properly
            count = invalidate_service_cache_for_entity('purchase_orders', cascade=True)
            
            if count > 0:
                logger.info(f"✅ Successfully invalidated {count} cache entries for purchase_orders")
            else:
                logger.info(f"No cache entries to invalidate for purchase_orders")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to invalidate purchase order cache: {e}")
            return False
    
    def after_status_change(self, po_id: str, new_status: str, **kwargs):
        """
        Hook called after any status change (approve/unapprove/delete)
        Ensures cache is cleared so list view reflects changes
        """
        logger.info(f"📝 PO {po_id} status changed to: {new_status}")
        
        # Invalidate all caches
        self.invalidate_cache(po_id)
        
        # Additional cleanup if needed
        if new_status == 'approved':
            logger.info(f"✅ PO {po_id} approved - cache cleared")
        elif new_status == 'draft':
            logger.info(f"↩️ PO {po_id} unapproved - cache cleared")
        elif new_status == 'deleted':
            logger.info(f"🗑️ PO {po_id} deleted - cache cleared")

    # =========================================================================
    # PAYMENTS DISPLAY - Required for financials tab
    # =========================================================================

    def get_po_payments(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """Get payments for this PO through linked invoices"""
        try:
            po_id = None
            if item and isinstance(item, dict):
                po_id = item.get('po_id')
            elif item_id:
                po_id = item_id
                
            if not po_id:
                return {'payments': [], 'has_history': False}
            
            if isinstance(po_id, str):
                po_id = uuid.UUID(po_id)
                
            with get_db_session() as session:
                # Get all invoices for this PO
                invoices = session.query(SupplierInvoice).filter_by(
                    po_id=po_id
                ).all()
                
                payment_list = []
                total_paid = 0
                
                for inv in invoices:
                    # Get payments for each invoice
                    payments = session.query(SupplierPayment).filter_by(
                        invoice_id=inv.invoice_id
                    ).order_by(SupplierPayment.payment_date.desc()).all()
                    
                    for pay in payments:
                        pay_dict = {
                            'payment_date': pay.payment_date.strftime('%Y-%m-%d') if pay.payment_date else '',
                            'payment_date_display': pay.payment_date.strftime('%d %b %Y') if pay.payment_date else 'N/A',
                            'reference_no': str(pay.reference_no or ''),
                            'amount': float(pay.amount or 0),
                            'payment_method': str(pay.payment_method or 'Unknown'),
                            'status': str(getattr(pay, 'workflow_status', 'completed')),
                            'payment_id': str(pay.payment_id),
                            'invoice_number': str(inv.supplier_invoice_number or 'N/A'),
                            'display_number': str(pay.reference_no) if pay.reference_no else f"PAY-{str(pay.payment_id)[:8].upper()}"
                        }
                        
                        payment_list.append(pay_dict)
                        total_paid += pay_dict['amount']
                
                return {
                    'payments': payment_list,
                    'has_history': bool(payment_list),
                    'currency_symbol': '₹',
                    'summary': {
                        'total_payments': len(payment_list),
                        'total_amount': round(total_paid, 2),
                        'total_invoices': len(invoices)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting PO payments: {str(e)}")
            return {
                'payments': [], 
                'has_history': False,
                'error': str(e)
            }
    
    # Backward compatibility - keep old method name too
    def get_po_payments_history(self, po_id: str) -> Dict:
        """Alias for get_po_payments for backward compatibility"""
        return self.get_po_payments(item_id=po_id)