# File: app/services/supplier_master_service.py
"""
Supplier Master Service - Fixed version with complete data structures
"""

from typing import Dict, Optional
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import desc

from app.models.master import Supplier
from app.models.transaction import SupplierInvoice, SupplierPayment, SupplierInvoiceLine
from app.engine.universal_entity_service import UniversalEntityService
from app.engine.universal_service_cache import cache_service_method
from app.services.database_service import get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierMasterService(UniversalEntityService):
    """
    Supplier service - extends Universal Engine base
    Only custom renderer methods, no overrides
    """
    
    def __init__(self):
        super().__init__('suppliers', Supplier)
        logger.info("Initialized SupplierMasterService")
    
    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add supplier-specific virtual calculated fields
        This is called automatically by parent's get_by_id
        """
        hospital_id = kwargs.get('hospital_id')
        if not hospital_id:
            return result
        
        try:
            supplier_id = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
            
            with get_db_session() as session:
                # Calculate balance summary fields
                from sqlalchemy import func
                from app.models.transaction import SupplierInvoice, SupplierPayment
                
                # Total invoiced
                total_invoiced = session.query(
                    func.coalesce(func.sum(SupplierInvoice.total_amount), 0)
                ).filter(
                    SupplierInvoice.supplier_id == supplier_id,
                    SupplierInvoice.hospital_id == hospital_id
                ).scalar() or Decimal('0')
                
                # Total paid
                total_paid = session.query(
                    func.coalesce(func.sum(SupplierPayment.amount), 0)
                ).filter(
                    SupplierPayment.supplier_id == supplier_id,
                    SupplierPayment.hospital_id == hospital_id,
                    SupplierPayment.workflow_status.in_(['approved', 'completed'])
                ).scalar() or Decimal('0')
                
                # Add calculated fields
                result['total_invoiced'] = float(total_invoiced)
                result['total_paid'] = float(total_paid)
                result['current_balance'] = float(total_invoiced - total_paid)
                
                # Get last payment date
                last_payment = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_id,
                    SupplierPayment.hospital_id == hospital_id,
                    SupplierPayment.workflow_status.in_(['approved', 'completed'])
                ).order_by(desc(SupplierPayment.payment_date)).first()
                
                if last_payment and last_payment.payment_date:
                    result['last_payment_date'] = last_payment.payment_date.strftime('%Y-%m-%d')
                
                # Add business statistics
                from app.services.supplier_service import get_supplier_statistics
                stats = get_supplier_statistics(
                    supplier_id=supplier_id,
                    hospital_id=hospital_id,
                    branch_id=kwargs.get('branch_id'),
                    session=session
                )
                
                if stats:
                    result['total_purchases'] = stats.get('total_business_volume', 0.0)
                    result['outstanding_balance'] = stats.get('outstanding_balance', 0.0)
                
                logger.info(f"Added virtual calculations for supplier {supplier_id}")
                    
        except Exception as e:
            logger.error(f"Error calculating supplier virtual fields: {str(e)}")
            # Set defaults on error
            result.setdefault('total_invoiced', 0.0)
            result.setdefault('total_paid', 0.0)
            result.setdefault('current_balance', 0.0)
            result.setdefault('total_purchases', 0.0)
            result.setdefault('outstanding_balance', 0.0)
        
        return result

    @cache_service_method('suppliers', 'payment_history')
    def get_supplier_payment_history_6months(self, item_id: str = None, 
                                            item: dict = None, **kwargs) -> Dict:
        """
        Payment history for custom renderer
        Returns complete structure expected by payment_history_table.html
        """
        try:
            # Get supplier ID
            supplier_id = item_id if item_id else (item.get('supplier_id') if item else None)
            if not supplier_id:
                return self._empty_payment_history()
            
            if isinstance(supplier_id, str):
                supplier_id = uuid.UUID(supplier_id)
            
            with get_db_session() as session:
                # Get supplier for name
                supplier = session.query(Supplier).filter_by(supplier_id=supplier_id).first()
                supplier_name = supplier.supplier_name if supplier else "Unknown"
                
                # Get payments
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                payments = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_id,
                    SupplierPayment.payment_date >= start_date,
                    SupplierPayment.payment_date <= end_date
                ).order_by(desc(SupplierPayment.payment_date)).all()
                
                # Format payments
                payment_history = []
                total_amount = Decimal(0)
                
                for payment in payments:
                    # Convert datetime to string safely
                    if payment.payment_date:
                        if hasattr(payment.payment_date, 'isoformat'):
                            payment_date_str = payment.payment_date.isoformat()
                        else:
                            payment_date_str = str(payment.payment_date)
                    else:
                        payment_date_str = ""
                    
                    payment_history.append({
                        'payment_id': str(payment.payment_id),
                        'reference_no': payment.reference_no or '',
                        'payment_date': payment_date_str,
                        'amount': float(payment.amount or 0),
                        'payment_method': payment.payment_method or 'Unknown',
                        'workflow_status': payment.workflow_status or 'completed',
                        'invoice_number': getattr(payment, 'supplier_invoice_number', '-')
                    })
                    total_amount += Decimal(str(payment.amount or 0))
                
                # Return with complete summary
                return {
                    'payments': payment_history,
                    'has_history': bool(payment_history),
                    'summary': {
                        'supplier_name': supplier_name,
                        'total_payments': len(payment_history),
                        'total_amount': float(total_amount),
                        'period': '12 Months'
                    },
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error in payment history: {str(e)}")
            return self._empty_payment_history()
    
    @cache_service_method('suppliers', 'invoice_history')
    def get_supplier_invoice_history(self, item_id: str = None, 
                                    item: dict = None, **kwargs) -> Dict:
        """
        Invoice history for custom renderer
        Returns complete structure expected by invoice_items_table.html
        """
        try:
            # Get supplier ID
            supplier_id = item_id if item_id else (item.get('supplier_id') if item else None)
            if not supplier_id:
                return self._empty_invoice_history()
            
            if isinstance(supplier_id, str):
                supplier_id = uuid.UUID(supplier_id)
            
            with get_db_session() as session:
                # Get invoices
                invoices = session.query(SupplierInvoice).filter(
                    SupplierInvoice.supplier_id == supplier_id
                ).order_by(desc(SupplierInvoice.invoice_date)).limit(10).all()
                
                # Format invoice items
                all_items = []
                total_amount = Decimal(0)
                total_gst = Decimal(0)
                
                for invoice in invoices:
                    # Get line items
                    lines = session.query(SupplierInvoiceLine).filter(
                        SupplierInvoiceLine.invoice_id == invoice.invoice_id
                    ).all()
                    
                    for line in lines:
                        # Convert dates to strings
                        if invoice.invoice_date:
                            if hasattr(invoice.invoice_date, 'isoformat'):
                                invoice_date_str = invoice.invoice_date.isoformat()
                            else:
                                invoice_date_str = str(invoice.invoice_date)
                        else:
                            invoice_date_str = ""
                        
                        all_items.append({
                            'invoice_number': invoice.supplier_invoice_number or '',
                            'invoice_date': invoice_date_str,
                            'medicine_name': line.medicine_name or '',
                            'batch': getattr(line, 'batch_number', '-') or '-',
                            'quantity': float(line.units or 0),
                            'unit_price': float(line.pack_purchase_price or 0),
                            'line_total': float(line.line_total or 0),
                            'gst_amount': float(getattr(line, 'total_gst', 0))
                        })
                        
                        total_amount += Decimal(str(line.line_total or 0))
                        total_gst += Decimal(str(getattr(line, 'total_gst', 0)))
                
                # Return with complete summary
                return {
                    'items': all_items,  # This must be a list
                    'has_invoices': bool(all_items),
                    'summary': {
                        'total_amount': float(total_amount),
                        'total_gst': float(total_gst),
                        'total_items': len(all_items),
                        'invoice_count': len(invoices)
                    },
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error in invoice history: {str(e)}")
            return self._empty_invoice_history()
    
    def _empty_payment_history(self) -> Dict:
        """Return complete empty payment history structure"""
        return {
            'payments': [],
            'has_history': False,
            'summary': {
                'supplier_name': '',
                'total_payments': 0,
                'total_amount': 0,
                'period': '12 Months'
            },
            'currency_symbol': '₹'
        }
    
    def _empty_invoice_history(self) -> Dict:
        """Return complete empty invoice history structure"""
        return {
            'items': [],  # Must be a list
            'has_invoices': False,
            'summary': {
                'total_amount': 0,
                'total_gst': 0,
                'total_items': 0,
                'invoice_count': 0
            },
            'currency_symbol': '₹'
        }
    