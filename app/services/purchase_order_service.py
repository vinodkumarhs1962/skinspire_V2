# File: app/services/purchase_order_service.py
# SIMPLIFIED VERSION - Using Universal Engine with Database View

from typing import Dict, Optional, List
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.views import PurchaseOrderView
from app.models.transaction import (
    PurchaseOrderHeader, PurchaseOrderLine, 
    SupplierInvoice, SupplierPayment
)
from app.engine.universal_entity_service import UniversalEntityService
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
                    'status': po.status or 'pending'
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

    # =========================================================================
    # INVOICES DISPLAY - Required for financials tab
    # =========================================================================
    
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