# File: app/services/purchase_order_service.py
# SIMPLIFIED VERSION - Using Universal Engine's configuration-driven approach

from typing import Dict, Optional, Any
import uuid
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.master import Supplier
from app.models.transaction import PurchaseOrderHeader, PurchaseOrderLine
from app.engine.universal_entity_service import UniversalEntityService
from app.services.database_service import get_db_session
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class PurchaseOrderService(UniversalEntityService):
    """
    Simplified Purchase Order service - leverages Universal Engine capabilities
    No more unnecessary overrides!
    """
    
    def __init__(self):
        """Initialize with purchase_orders entity type"""
        super().__init__('purchase_orders', PurchaseOrderHeader)
        logger.info("✅ Initialized PurchaseOrderService")
    
    # =========================================================================
    # Only override what's TRULY specific to Purchase Orders
    # =========================================================================
    
    @cache_service_method('purchase_orders', 'search_entity_data')
    def search_entity_data(self, filters: dict, **kwargs) -> dict:
        """
        Just call parent - Universal Engine handles everything!
        """
        return super().search_data(filters, **kwargs)
    
    
    @cache_service_method('purchase_orders', 'search_data')
    def search_data(self, filters: dict, **kwargs) -> dict:
        """Override to add debug logging"""
        logger.info(f"PurchaseOrderService.search_data called with filters: {filters}")
        result = super().search_data(filters, **kwargs)
        
        # Debug: Check if calculated fields are present
        if result.get('items'):
            first_item = result['items'][0] if result['items'] else None
            if first_item:
                logger.info(f"First item keys: {list(first_item.keys())}")
                logger.info(f"supplier_name: {first_item.get('supplier_name', 'NOT FOUND')}")
                logger.info(f"total_amount: {first_item.get('total_amount', 'NOT FOUND')}")
        
        return result
    
    def _add_relationships(self, item_dict: Dict, item: Any, session: Session):
        """Override parent method - adds supplier name and fixes Decimal conversion"""
        try:
            from decimal import Decimal
            
            # DEBUG: Log what we receive
            logger.info(f"[DEBUG] _add_relationships called")
            logger.info(f"[DEBUG] item type: {type(item)}")
            logger.info(f"[DEBUG] item_dict keys: {list(item_dict.keys())}")
            
            # Check if total_amount exists
            if 'total_amount' in item_dict:
                logger.info(f"[DEBUG] total_amount in dict: {item_dict['total_amount']}, type: {type(item_dict['total_amount'])}")
            
            if hasattr(item, 'total_amount'):
                logger.info(f"[DEBUG] item.total_amount: {item.total_amount}, type: {type(item.total_amount)}")
            
            # Add supplier name if supplier_id exists
            if hasattr(item, 'supplier_id') and item.supplier_id:
                # Try eager-loaded relationship first
                if hasattr(item, 'supplier') and item.supplier:
                    item_dict['supplier_name'] = item.supplier.supplier_name
                    item_dict['supplier_category'] = getattr(item.supplier, 'supplier_category', '')
                    # Also add supplier object for virtual field
                    item_dict['supplier'] = {'supplier_name': item.supplier.supplier_name}
                else:
                    # Fallback: Query supplier
                    from app.models.master import Supplier
                    supplier = session.query(Supplier).filter_by(
                        supplier_id=item.supplier_id
                    ).first()
                    
                    if supplier:
                        item_dict['supplier_name'] = supplier.supplier_name
                        item_dict['supplier_category'] = getattr(supplier, 'supplier_category', '')
                        # Also add supplier object for virtual field
                        item_dict['supplier'] = {'supplier_name': supplier.supplier_name}
                    else:
                        item_dict['supplier_name'] = 'Unknown Supplier'
            else:
                item_dict['supplier_name'] = 'N/A'
            
            # Fix: Convert Decimal to float for total_amount
            if 'total_amount' in item_dict:
                value = item_dict['total_amount']
                logger.info(f"[DEBUG] Converting total_amount from dict: {value}, type: {type(value)}")
                if value is not None:
                    if isinstance(value, Decimal):
                        item_dict['total_amount'] = float(value)
                        logger.info(f"[DEBUG] Converted Decimal to float: {item_dict['total_amount']}")
                    elif isinstance(value, (int, float)):
                        item_dict['total_amount'] = float(value)
                        logger.info(f"[DEBUG] Converted to float: {item_dict['total_amount']}")
                    else:
                        item_dict['total_amount'] = 0.0
                        logger.info(f"[DEBUG] Set to 0.0 due to unexpected type")
                else:
                    item_dict['total_amount'] = 0.0
                    logger.info(f"[DEBUG] Set to 0.0 due to None value")
            elif hasattr(item, 'total_amount'):
                # Get directly from entity if not in dict
                value = item.total_amount
                logger.info(f"[DEBUG] Getting total_amount from entity: {value}, type: {type(value)}")
                if value is not None:
                    if isinstance(value, Decimal):
                        item_dict['total_amount'] = float(value)
                        logger.info(f"[DEBUG] Converted entity Decimal to float: {item_dict['total_amount']}")
                    elif isinstance(value, (int, float)):
                        item_dict['total_amount'] = float(value)
                        logger.info(f"[DEBUG] Converted entity value to float: {item_dict['total_amount']}")
                    else:
                        item_dict['total_amount'] = 0.0
                        logger.info(f"[DEBUG] Set to 0.0 due to unexpected entity type")
                else:
                    item_dict['total_amount'] = 0.0
                    logger.info(f"[DEBUG] Set to 0.0 due to None entity value")
            else:
                logger.info(f"[DEBUG] No total_amount found in dict or entity")
            
            # DEBUG: Final value
            logger.info(f"[DEBUG] Final total_amount: {item_dict.get('total_amount', 'NOT SET')}")
            
            return item_dict
            
        except Exception as e:
            logger.error(f"Error adding PO relationships: {str(e)}")
            return item_dict

    def add_relationships(self, item_dict: Dict, item: Any, session: Session):
        """Keep this for categorized processor compatibility"""
        return self._add_relationships(item_dict, item, session)

    # def _entity_to_dict(self, entity, session: Session = None) -> Dict:
    #     """Convert entity to dict with relationships"""
    #     result = super()._entity_to_dict(entity, session)
        
    #     # Add supplier name - properly handle supplier relationship
    #     if hasattr(entity, 'supplier') and entity.supplier:
    #         result['supplier_name'] = entity.supplier.supplier_name
    #         result['supplier'] = {'supplier_name': entity.supplier.supplier_name}  # Add for virtual field
    #     elif hasattr(entity, 'supplier_id') and entity.supplier_id and session:
    #         supplier = session.query(Supplier).filter_by(supplier_id=entity.supplier_id).first()
    #         if supplier:
    #             result['supplier_name'] = supplier.supplier_name
    #             result['supplier'] = {'supplier_name': supplier.supplier_name}  # Add for virtual field
    #         else:
    #             result['supplier_name'] = 'Unknown'
    #     else:
    #         result['supplier_name'] = 'N/A'
        
    #     # Ensure total_amount is a float
    #     if hasattr(entity, 'total_amount'):
    #         result['total_amount'] = float(entity.total_amount) if entity.total_amount else 0.0
        
    #     return result

    def _get_base_query(self, session: Session, hospital_id: uuid.UUID, 
                    branch_id: Optional[uuid.UUID] = None,
                    user: Optional[Any] = None):
        """Override to eager load supplier relationship"""
        from sqlalchemy.orm import joinedload
        
        # Start with base query with eager loading
        query = session.query(self.model_class).options(
            joinedload(self.model_class.supplier)
        )
        
        # Apply hospital filter (matching parent pattern)
        if hasattr(self.model_class, 'hospital_id'):
            query = query.filter(self.model_class.hospital_id == hospital_id)
        
        # Apply branch filter (matching parent pattern)
        if branch_id and hasattr(self.model_class, 'branch_id'):
            query = query.filter(self.model_class.branch_id == branch_id)
        
        return query

    def get_summary_stats(self, filters: Dict, hospital_id: uuid.UUID, 
                         branch_id: Optional[uuid.UUID] = None) -> Dict:
        """ADD THIS: Calculate summary statistics for dashboard cards"""
        try:
            with get_db_session() as session:
                # Base query
                query = session.query(PurchaseOrderHeader).filter(
                    PurchaseOrderHeader.hospital_id == hospital_id
                )
                
                if branch_id:
                    query = query.filter(PurchaseOrderHeader.branch_id == branch_id)
                
                # Total count
                total_count = query.count()
                
                # Total amount sum
                total_amount = session.query(
                    func.sum(PurchaseOrderHeader.total_amount)
                ).filter(
                    PurchaseOrderHeader.hospital_id == hospital_id
                ).scalar() or 0
                
                # Pending (draft) count
                pending_count = query.filter(
                    PurchaseOrderHeader.status == 'draft'
                ).count()
                
                # This month count
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
                this_month_count = query.filter(
                    PurchaseOrderHeader.po_date >= month_start
                ).count()
                
                return {
                    'total_count': total_count,
                    'total_amount_sum': float(total_amount),
                    'draft_count': pending_count,
                    'current_month_count': this_month_count
                }
                
        except Exception as e:
            logger.error(f"Error calculating summary stats: {str(e)}")
            return {
                'total_count': 0,
                'total_amount_sum': 0,
                'draft_count': 0,
                'current_month_count': 0
            }
    
    def _calculate_summary(self, session: Session, hospital_id: uuid.UUID,
                          branch_id: Optional[uuid.UUID], filters: Dict,
                          total_count: int, applied_filters: set = None) -> Dict:
        """ADD THIS: Override to use our get_summary_stats"""
        stats = self.get_summary_stats(filters, hospital_id, branch_id)
        
        # Use the actual filtered count for total_count
        stats['total_count'] = total_count
        
        return stats
    
    def get_calculated_fields(self, item: Any, config: Any = None) -> Dict:
        """Calculate fields for list view - called by categorized processor"""
        calculated = {}
        
        try:
            # Ensure total_amount is a float
            if hasattr(item, 'total_amount'):
                calculated['total_amount'] = float(item.total_amount) if item.total_amount else 0.0
            else:
                calculated['total_amount'] = 0.0
            
            # Add supplier_name
            if hasattr(item, 'supplier') and item.supplier:
                calculated['supplier_name'] = item.supplier.supplier_name
            elif hasattr(item, 'supplier_id') and item.supplier_id:
                # Will be handled by add_relationships if needed
                pass
            else:
                calculated['supplier_name'] = 'N/A'
                
        except Exception as e:
            logger.error(f"Error calculating PO fields: {str(e)}")
            calculated['total_amount'] = 0.0
            calculated['supplier_name'] = 'Error'
            
        return calculated
    # def _get_calculated_fields(self, item: Any, session: Session = None) -> Dict:
    #     """Fix supplier_name and total_amount display in list view"""
    #     calculated = {}
        
    #     # Fix supplier_name showing as "–"
    #     if hasattr(item, 'supplier') and item.supplier:
    #         calculated['supplier_name'] = item.supplier.supplier_name
    #     elif hasattr(item, 'supplier_id') and item.supplier_id:
    #         if not session:
    #             with get_db_session() as new_session:
    #                 supplier = new_session.query(Supplier).filter_by(
    #                     supplier_id=item.supplier_id
    #                 ).first()
    #         else:
    #             supplier = session.query(Supplier).filter_by(
    #                 supplier_id=item.supplier_id
    #             ).first()
    #         if supplier:
    #             calculated['supplier_name'] = supplier.supplier_name
    #         else:
    #             calculated['supplier_name'] = 'N/A'
    #     else:
    #         calculated['supplier_name'] = 'N/A'
        
    #     # Fix total_amount showing as zero
    #     if hasattr(item, 'total_amount'):
    #         calculated['total_amount'] = float(item.total_amount or 0)
    #     else:
    #         calculated['total_amount'] = 0.0
        
    #     # Add line count
    #     if hasattr(item, 'po_lines'):
    #         calculated['line_count'] = len(item.po_lines)
    #     else:
    #         calculated['line_count'] = 0
        
    #     return calculated
    
    def get_po_line_items_display(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """Get PO line items for display in detail view"""
        try:
            # Get PO ID from parameters
            po_id = None
            if item and isinstance(item, dict):
                po_id = item.get('po_id')
            elif item_id:
                po_id = item_id
                
            if not po_id:
                return {'items': [], 'has_po': False, 'po_info': {}}
            
            # Convert to UUID if string
            if isinstance(po_id, str):
                po_id = uuid.UUID(po_id)
            
            with get_db_session() as session:
                po = session.query(PurchaseOrderHeader).filter_by(
                    po_id=po_id
                ).first()
                
                if not po:
                    return {'items': [], 'has_po': False, 'po_info': {}}
                
                # Get line items
                lines = session.query(PurchaseOrderLine).filter_by(
                    po_id=po_id
                ).all()
                
                items = []
                total_amount = 0
                total_gst = 0
                
                for line in lines:
                    item_dict = {
                        'item_name': line.medicine_name,
                        'medicine_name': line.medicine_name,
                        'hsn_code': getattr(line, 'hsn_code', '-'),
                        'quantity': float(line.units or 0),
                        'unit_price': float(line.pack_purchase_price or 0),
                        'gst_amount': float(line.total_gst or 0),
                        'total_amount': float(line.line_total or 0)
                    }
                    items.append(item_dict)
                    total_amount += float(line.line_total or 0)
                    total_gst += float(line.total_gst or 0)
                
                po_info = {
                    'po_number': po.po_number,
                    'po_date': po.po_date,
                    'total_amount': float(po.total_amount or 0),
                    'status': po.status or 'draft'
                }
                
                return {
                    'items': items,
                    'summary': {
                        'total_amount': total_amount,
                        'total_gst': total_gst
                    },
                    'has_po': True,
                    'currency_symbol': '₹',
                    'po_info': po_info
                }
                
        except Exception as e:
            logger.error(f"Error getting PO line items: {str(e)}")
            return {'items': [], 'has_po': False, 'po_info': {}}

    def get_po_invoices(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """Get invoices linked to this PO for financials tab"""
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
                from app.models.transaction import SupplierInvoice
                
                invoices = session.query(SupplierInvoice).filter_by(
                    po_id=po_id
                ).all()
                
                invoice_list = []
                total_invoice_amount = 0
                
                for inv in invoices:
                    inv_dict = {
                        'invoice_number': inv.supplier_invoice_number,
                        'invoice_date': inv.invoice_date,
                        'total_amount': float(inv.total_amount or 0),
                        'payment_status': getattr(inv, 'payment_status', 'pending'),
                        'invoice_id': str(inv.invoice_id)
                    }
                    invoice_list.append(inv_dict)
                    total_invoice_amount += inv_dict['total_amount']
                    
                return {
                    'items': invoice_list,
                    'has_invoices': bool(invoice_list),
                    'currency_symbol': '₹',
                    'summary': {
                        'total_invoices': len(invoice_list),
                        'total_amount': total_invoice_amount
                    }
                }
        except Exception as e:
            logger.error(f"Error getting PO invoices: {str(e)}")
            return {'items': [], 'has_invoices': False}


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
                from app.models.transaction import SupplierInvoice, SupplierPayment
                
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
                    ).order_by(SupplierPayment.payment_date.desc()).all()  # Sort in query
                    
                    for pay in payments:
                        # Convert everything to safe types immediately
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
# That's it! No more overrides needed for:
# - _apply_filters (Universal Engine handles based on field.filterable)
# - _entity_to_dict (Universal Engine handles based on field_type)
# - _add_relationships (Universal Engine handles based on field_type=FOREIGN_KEY)
# - get_complete_filter_data (Universal Engine generates from field config)
# - add_relationships (Universal Engine handles this)