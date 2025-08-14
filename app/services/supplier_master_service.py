# Enhanced Supplier Master Service - Transaction History Implementation
# File: app/services/supplier_master_service.py

"""
Enhanced implementation that reuses existing payment history functionality
from supplier_payment_service.py
"""

from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from app.models.master import Supplier
from app.models.transaction import SupplierInvoice, SupplierPayment, SupplierInvoiceLine
from app.engine.universal_entity_service import UniversalEntityService
from app.services.database_service import get_entity_dict, get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierMasterService(UniversalEntityService):
    """
    Enhanced Supplier service that reuses existing payment service methods
    """
    
    def __init__(self):
        super().__init__('suppliers', Supplier)
    
    def get_detail_data(self, item_id: str, hospital_id: uuid.UUID, 
               branch_id: Optional[uuid.UUID] = None,
               include_calculations: bool = True) -> Optional[Dict]:
        """
        Override to add transaction history data using existing service methods
        """
        # Get base data from parent
        data = super().get_detail_data(item_id, hospital_id, branch_id, include_calculations)
        
        if not data or not include_calculations:
            return data
        
        supplier_id = uuid.UUID(item_id)
        
        # Add supplier_id for custom renderers
        data['supplier_id'] = str(supplier_id)
        
        # Calculate balance summary
        with get_db_session() as session:
            balance_summary = self._calculate_balance_summary(session, supplier_id, hospital_id)
            
            # FIXED: Always update the 'item' key which contains the actual entity data
            if 'item' in data and isinstance(data['item'], dict):
                data['item'].update(balance_summary)
                logger.info(f"Added balance summary to item: {balance_summary}")
            else:
                # Fallback: create item structure if missing
                data['item'] = data.get('item', {})
                if isinstance(data['item'], dict):
                    data['item'].update(balance_summary)
                else:
                    # If item is not a dict (object), create a new structure
                    original_item = data['item']
                    data['item'] = balance_summary
                    logger.warning(f"Item was not a dict, replaced with balance summary")
            
        return data
    
    def get_supplier_payment_history_6months(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get last 6 months payment history for a supplier
        This method signature matches what the payment_history_table.html template expects
        Returns the same structure as supplier_payment_service.py
        """
        try:
            # PARAMETER RESOLUTION
            if item_id:
                # Template calls: item_id IS the supplier_id for supplier master
                supplier_id = item_id
            elif item and isinstance(item, dict) and 'supplier_id' in item:
                # Template calls from payment context
                supplier_id = item['supplier_id']  
            else:
                return {'payments': [], 'has_history': False, 'error': 'No supplier ID provided'}
        
            # FIXED: Add debugging and parameter validation
            logger.info(f"Fetching payment history for supplier_id: {supplier_id}")
            logger.info(f"Kwargs received: {kwargs}")
            
            with get_db_session() as session:
                # FIXED: Extend date range to 12 months for better data availability
                twelve_months_ago = datetime.now() - timedelta(days=365)
                
                # FIXED: Convert supplier_id to UUID if it's a string
                if isinstance(supplier_id, str):
                    supplier_uuid = uuid.UUID(supplier_id)
                else:
                    supplier_uuid = supplier_id
                
                # FIXED: Add hospital_id filter if provided for data isolation
                query = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_uuid,
                    SupplierPayment.payment_date >= twelve_months_ago
                )
                
                # FIXED: Add hospital filter if provided in kwargs
                if 'hospital_id' in kwargs and kwargs['hospital_id']:
                    query = query.filter(SupplierPayment.hospital_id == kwargs['hospital_id'])
                
                # FIXED: Expand workflow status filter to include more statuses
                query = query.filter(
                    SupplierPayment.workflow_status.in_(['approved', 'completed', 'pending'])
                )
                
                payments = query.order_by(desc(SupplierPayment.payment_date)).limit(50).all()
                
                logger.info(f"Found {len(payments)} payments for supplier {supplier_id}")
                
                payment_history = []
                total_paid = Decimal('0')
                
                for payment in payments:
                    # FIXED: Add better error handling for invoice lookup
                    invoice_no = 'N/A'
                    try:
                        if payment.invoice_id:
                            invoice = session.query(SupplierInvoice).filter(
                                SupplierInvoice.invoice_id == payment.invoice_id
                            ).first()
                            if invoice and invoice.supplier_invoice_number:
                                invoice_no = invoice.supplier_invoice_number
                    except Exception as inv_error:
                        logger.warning(f"Error getting invoice for payment {payment.payment_id}: {inv_error}")
                    
                    payment_data = {
                        'payment_id': str(payment.payment_id),
                        'reference_no': payment.reference_no or 'N/A',
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'payment_method': payment.payment_method or 'Unknown',
                        'amount': float(payment.amount or 0),
                        'workflow_status': payment.workflow_status or 'Unknown',
                        'invoice_no': invoice_no
                    }
                    payment_history.append(payment_data)
                    total_paid += payment.amount or Decimal('0')
                
                # Get supplier details for summary
                supplier = session.query(Supplier).filter(
                    Supplier.supplier_id == supplier_uuid
                ).first()
                
                result = {
                    'payments': payment_history,
                    'summary': {
                        'total_payments': len(payment_history),
                        'total_amount': float(total_paid),
                        'supplier_name': supplier.supplier_name if supplier else 'Unknown',
                        'period': '12 Months'  # Updated to reflect actual period
                    },
                    'has_history': bool(payment_history),
                    'currency_symbol': '₹'
                }
                
                logger.info(f"Returning payment history with {len(payment_history)} payments, total: ₹{total_paid}")
                return result
                
        except Exception as e:
            logger.error(f"Error getting payment history for supplier {supplier_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'payments': [], 
                'has_history': False, 
                'error': str(e),
                'summary': {
                    'total_payments': 0,
                    'total_amount': 0,
                    'supplier_name': 'Error',
                    'period': '12 Months'
                },
                'currency_symbol': '₹'
            }
    
    def get_supplier_invoice_history(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice history for a supplier
        Returns structure compatible with invoice_items_table.html template
        """
        try:
            # PARAMETER RESOLUTION
            if item_id:
                # Template calls: item_id IS the supplier_id for supplier master
                supplier_id = item_id
            elif item and isinstance(item, dict) and 'supplier_id' in item:
                # Template calls from payment context
                supplier_id = item['supplier_id']  
            else:
                return {'items': [], 'has_invoices': False, 'error': 'No supplier ID provided'}
            with get_db_session() as session:
                # Get last 10 invoices for this supplier
                invoices = session.query(SupplierInvoice).filter(
                    SupplierInvoice.supplier_id == supplier_id
                ).order_by(
                    desc(SupplierInvoice.invoice_date)
                ).limit(10).all()
                
                all_items = []
                invoice_summary = {
                    'total_amount': Decimal('0'),
                    'total_gst': Decimal('0'),
                    'total_items': 0
                }
                
                for invoice in invoices:
                    # Get invoice line items
                    invoice_lines = session.query(SupplierInvoiceLine).filter(
                        SupplierInvoiceLine.invoice_id == invoice.invoice_id
                    ).all()
                    
                    for line in invoice_lines:
                        all_items.append({
                            'invoice_no': invoice.supplier_invoice_number,
                            'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else '',
                            'item_name': line.medicine_name,
                            'batch_no': line.batch_number,
                            'quantity': float(item.units or 0), 
                            'unit_price': float(line.unit_price or 0),
                            'discount_percent': float(line.discount_percentage or 0),
                            'gst_amount': float(line.gst_amount or 0),
                            'total': float(line.line_total or 0),
                            'expiry_date': line.expiry_date.strftime('%Y-%m-%d') if line.expiry_date else None
                        })
                        
                        invoice_summary['total_amount'] += line.line_total or Decimal('0')
                        invoice_summary['total_gst'] += line.gst_amount or Decimal('0')
                        invoice_summary['total_items'] += 1
                
                return {
                    'items': all_items,
                    'invoice_summary': {
                        'total_amount': float(invoice_summary['total_amount']),
                        'total_gst': float(invoice_summary['total_gst']),
                        'total_items': invoice_summary['total_items']
                    },
                    'has_invoices': bool(all_items),
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error getting invoice history: {str(e)}")
            return {'items': [], 'has_invoices': False, 'error': str(e)}
    
    def _calculate_balance_summary(self, session: Session, supplier_id: uuid.UUID, hospital_id: uuid.UUID = None) -> Dict:
        try:
            # Total invoiced amount (all time) - WITH HOSPITAL FILTER
            invoice_query = session.query(func.sum(SupplierInvoice.total_amount)).filter(
                SupplierInvoice.supplier_id == supplier_id
            )
            if hospital_id:
                invoice_query = invoice_query.join(Supplier).filter(Supplier.hospital_id == hospital_id)
            total_invoiced = invoice_query.scalar() or Decimal('0')
            
            # Total paid amount (approved payments only) - WITH HOSPITAL FILTER  
            payment_query = session.query(func.sum(SupplierPayment.amount)).filter(
                SupplierPayment.supplier_id == supplier_id
                # SupplierPayment.workflow_status.in_(['approved', 'completed'])
            )
            if hospital_id:
                payment_query = payment_query.filter(SupplierPayment.hospital_id == hospital_id)
            total_paid = payment_query.scalar() or Decimal('0')
            
            # Current balance
            current_balance = total_invoiced - total_paid
            
            # Last payment date
            last_payment = session.query(SupplierPayment).filter(
                SupplierPayment.supplier_id == supplier_id,
                SupplierPayment.workflow_status.in_(['approved', 'completed'])
            ).order_by(
                desc(SupplierPayment.payment_date)
            ).first()
            
            last_payment_date = None
            if last_payment and last_payment.payment_date:
                last_payment_date = last_payment.payment_date.strftime('%Y-%m-%d')
            
            return {
                'total_invoiced': float(total_invoiced),
                'total_paid': float(total_paid),
                'current_balance': float(current_balance),
                'last_payment_date': last_payment_date
            }
            
        except Exception as e:
            logger.error(f"Error calculating balance summary: {str(e)}")
            return {
                'total_invoiced': 0.0,
                'total_paid': 0.0,
                'current_balance': 0.0,
                'last_payment_date': None
            }
    
    def _calculate_summary(self, session: Session, hospital_id: uuid.UUID,
                          branch_id: Optional[uuid.UUID], filters: Dict,
                          total_count: int, applied_filters: set = None) -> Dict:
        """
        Override to add transaction-related summary statistics
        """
        # Get base summary from parent
        summary = super()._calculate_summary(
            session, hospital_id, branch_id, filters, total_count, applied_filters
        )
        
        # Add transaction statistics
        base_query = self._get_base_query(session, hospital_id, branch_id)
        
        # Suppliers with pending payments
        suppliers_with_pending = session.query(
            func.count(func.distinct(SupplierInvoice.supplier_id))
        ).join(
            Supplier, Supplier.supplier_id == SupplierInvoice.supplier_id
        ).filter(
            Supplier.hospital_id == hospital_id,
            SupplierInvoice.payment_status != 'paid'
        )
        
        if branch_id:
            suppliers_with_pending = suppliers_with_pending.filter(
                Supplier.branch_id == branch_id
            )
        
        summary['suppliers_with_pending_invoices'] = suppliers_with_pending.scalar() or 0
        
        # Total outstanding amount across all suppliers
        total_outstanding = session.query(
            func.sum(SupplierInvoice.total_amount) - func.coalesce(
                func.sum(SupplierPayment.amount), 0
            )
        ).select_from(SupplierInvoice).outerjoin(
            SupplierPayment,
            and_(
                SupplierPayment.invoice_id == SupplierInvoice.invoice_id,
                SupplierPayment.workflow_status.in_(['approved', 'completed'])
            )
        ).join(
            Supplier, Supplier.supplier_id == SupplierInvoice.supplier_id
        ).filter(
            Supplier.hospital_id == hospital_id
        )
        
        if branch_id:
            total_outstanding = total_outstanding.filter(
                Supplier.branch_id == branch_id
            )
        
        summary['total_outstanding_amount'] = float(total_outstanding.scalar() or 0)
        
        return summary
    
    def _convert_items_to_dict(self, items: List, session: Session) -> List[Dict]:
        """Override to extract phone from contact_info JSONB and ensure all fields"""
        items_dict = []
        
        for item in items:
            # Get base dictionary
            item_dict = get_entity_dict(item)
            
            # ✅ Extract phone from contact_info JSONB
            if hasattr(item, 'contact_info') and item.contact_info:
                contact_info = item.contact_info
                if isinstance(contact_info, dict):
                    # Try to get phone in order of preference
                    phone = contact_info.get('phone') or contact_info.get('mobile') or contact_info.get('telephone', '')
                    item_dict['phone'] = phone
                else:
                    item_dict['phone'] = ''
            else:
                item_dict['phone'] = ''
            
            # ✅ Ensure all required fields are present
            # Some fields might be None, but we need them as empty strings for display
            if item_dict.get('supplier_category') is None:
                item_dict['supplier_category'] = ''
            if item_dict.get('contact_person_name') is None:
                item_dict['contact_person_name'] = ''
            if item_dict.get('email') is None:
                item_dict['email'] = ''
            if item_dict.get('gst_registration_number') is None:
                item_dict['gst_registration_number'] = ''
            
            # Add any relationships if needed
            self._add_relationships(item_dict, item, session)
            
            items_dict.append(item_dict)
            
        logger.info(f"✅ Converted {len(items_dict)} supplier items with phone extraction")
        return items_dict
        
    def _add_relationships(self, item_dict: Dict, item: Supplier, session: Session):
        """Add supplier-specific relationships if needed"""
        # For now, suppliers don't need additional relationships
        # But this is where you'd add branch name, etc. if needed
        pass

    def get_po_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Placeholder for PO items - not applicable for supplier master
        """
        return {
            'items': [], 
            'has_po': False, 
            'error': 'PO items not applicable for supplier master'
        }

    def get_invoice_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Placeholder for invoice items - not applicable for supplier master  
        """
        return {
            'items': [], 
            'has_invoices': False, 
            'error': 'Invoice items not applicable for supplier master'
        }

    def get_payment_workflow_timeline(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Placeholder for payment workflow - not applicable for supplier master
        """
        return {
            'steps': [], 
            'has_timeline': False, 
            'error': 'Payment workflow not applicable for supplier master'
        }

    def get_supplier_payment_summary(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Placeholder for payment summary - not applicable for supplier master
        """
        return {
            'summary': {}, 
            'error': 'Payment summary not applicable for supplier master'
        }
