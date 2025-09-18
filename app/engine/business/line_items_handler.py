# File: app/engine/business/line_items_handler.py
"""
Centralized Line Items Handler for Universal Engine
Provides reusable functions for displaying line items from any entity
Standard input/output contracts for PO, Invoice, and Payment line items
"""

from typing import Dict, Any, Optional, List
import uuid
from decimal import Decimal
from datetime import datetime
from app.services.database_service import get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)


class LineItemsHandler:
    """
    Universal handler for line items display across all entities
    Single source of truth for line items rendering logic
    """
    
    @staticmethod
    def get_po_line_items(po_id: Any, context: str = 'default', **kwargs) -> Dict:
        """
        Get Purchase Order line items in standard format
        
        Args:
            po_id: Purchase Order ID (UUID or string)
            context: Context of call ('invoice', 'payment', 'default')
            **kwargs: Additional parameters (hospital_id, branch_id, etc.)
        
        Returns:
            Standardized line items dictionary
        """
        try:
            if not po_id:
                return LineItemsHandler._empty_result('po', 'No Purchase Order ID provided')
            
            # Convert to UUID if string
            if isinstance(po_id, str):
                try:
                    po_id = uuid.UUID(po_id)
                except ValueError:
                    return LineItemsHandler._error_result('po', f'Invalid PO ID format: {po_id}')
            
            with get_db_session() as session:
                from app.models.transaction import PurchaseOrderHeader, PurchaseOrderLine
                
                # Get PO header
                po_header = session.query(PurchaseOrderHeader).filter(
                    PurchaseOrderHeader.po_id == po_id
                ).first()
                
                if not po_header:
                    return LineItemsHandler._empty_result('po', 'Purchase Order not found')
                
                # Get line items
                lines = session.query(PurchaseOrderLine).filter(
                    PurchaseOrderLine.po_id == po_id
                ).order_by(PurchaseOrderLine.line_id).all()
                
                if not lines:
                    return LineItemsHandler._empty_result(
                        'po', 
                        'No line items found',
                        header_info={
                            'number': po_header.po_number,
                            'date': po_header.po_date,
                            'status': po_header.status
                        }
                    )
                
                # Format line items
                formatted_lines = []
                totals = {'subtotal': Decimal(0), 'discount': Decimal(0), 'gst': Decimal(0)}
                
                for idx, line in enumerate(lines, 1):
                    formatted_line = LineItemsHandler._format_po_line(line, idx)
                    formatted_lines.append(formatted_line)
                    
                    # Update totals
                    totals['subtotal'] += Decimal(str(formatted_line['taxable_amount']))
                    totals['discount'] += Decimal(str(formatted_line['discount_amount']))
                    totals['gst'] += Decimal(str(formatted_line['gst_amount']))
                
                # Calculate grand total
                totals['grand_total'] = totals['subtotal'] + totals['gst']
                
                return {
                    'items': formatted_lines,
                    'has_items': True,
                    'entity_type': 'po',
                    'currency_symbol': '₹',
                    'header_info': {
                        'number': po_header.po_number,
                        'date': po_header.po_date.strftime('%d %b %Y') if po_header.po_date else '',
                        'status': po_header.status or 'pending',
                        'supplier_name': getattr(po_header, 'supplier_name', ''),
                        'total_amount': float(po_header.total_amount or 0)
                    },
                    'summary': {
                        'line_count': len(formatted_lines),
                        'subtotal': float(totals['subtotal']),
                        'total_discount': float(totals['discount']),
                        'total_gst': float(totals['gst']),
                        'grand_total': float(totals['grand_total'])
                    },
                    'context': context
                }
                
        except Exception as e:
            logger.error(f"Error fetching PO line items: {str(e)}")
            return LineItemsHandler._error_result('po', str(e))
    
    @staticmethod
    def get_invoice_line_items(invoice_id: Any, context: str = 'default', **kwargs) -> Dict:
        """
        Get Invoice line items in standard format
        
        Args:
            invoice_id: Invoice ID (UUID or string)
            context: Context of call ('payment', 'reconciliation', 'default')
            **kwargs: Additional parameters
        
        Returns:
            Standardized line items dictionary
        """
        try:
            if not invoice_id:
                return LineItemsHandler._empty_result('invoice', 'No Invoice ID provided')
            
            # Convert to UUID if string
            if isinstance(invoice_id, str):
                try:
                    invoice_id = uuid.UUID(invoice_id)
                except ValueError:
                    return LineItemsHandler._error_result('invoice', f'Invalid Invoice ID format')
            
            with get_db_session() as session:
                from app.models.transaction import SupplierInvoice, SupplierInvoiceLine
                
                # Get invoice header
                invoice = session.query(SupplierInvoice).filter(
                    SupplierInvoice.invoice_id == invoice_id
                ).first()
                
                if not invoice:
                    return LineItemsHandler._empty_result('invoice', 'Invoice not found')
                
                # Get line items
                lines = session.query(SupplierInvoiceLine).filter(
                    SupplierInvoiceLine.invoice_id == invoice_id
                ).order_by(SupplierInvoiceLine.line_id).all()
                
                if not lines:
                    return LineItemsHandler._empty_result(
                        'invoice',
                        'No line items found',
                        header_info={
                            'number': invoice.supplier_invoice_number,
                            'date': invoice.invoice_date,
                            'status': invoice.payment_status
                        }
                    )
                
                # Format line items
                formatted_lines = []
                totals = {'subtotal': Decimal(0), 'discount': Decimal(0), 'gst': Decimal(0)}
                
                for idx, line in enumerate(lines, 1):
                    formatted_line = LineItemsHandler._format_invoice_line(line, idx)
                    formatted_lines.append(formatted_line)
                    
                    # Update totals (skip free items)
                    if not formatted_line.get('is_free'):
                        totals['subtotal'] += Decimal(str(formatted_line['taxable_amount']))
                        totals['discount'] += Decimal(str(formatted_line['discount_amount']))
                        totals['gst'] += Decimal(str(formatted_line['gst_amount']))
                
                # Calculate grand total
                totals['grand_total'] = totals['subtotal'] + totals['gst']
                
                return {
                    'items': formatted_lines,
                    'has_items': True,
                    'entity_type': 'invoice',
                    'currency_symbol': '₹',
                    'header_info': {
                        'number': invoice.supplier_invoice_number,
                        'date': invoice.invoice_date.strftime('%d %b %Y') if invoice.invoice_date else '',
                        'status': invoice.payment_status or 'unpaid',
                        'supplier_name': getattr(invoice, 'supplier_name', ''),
                        'total_amount': float(invoice.total_amount or 0),
                        'po_id': str(invoice.po_id) if invoice.po_id else None
                    },
                    'summary': {
                        'line_count': len(formatted_lines),
                        'subtotal': float(totals['subtotal']),
                        'total_discount': float(totals['discount']),
                        'total_gst': float(totals['gst']),
                        'grand_total': float(totals['grand_total'])
                    },
                    'context': context
                }
                
        except Exception as e:
            logger.error(f"Error fetching invoice line items: {str(e)}")
            return LineItemsHandler._error_result('invoice', str(e))
    
    @staticmethod
    def get_payment_items(payment_id: Any, context: str = 'default', **kwargs) -> Dict:
        """
        Get Payment related items (invoices being paid)
        
        Args:
            payment_id: Payment ID (UUID or string)
            context: Context of call
            **kwargs: Additional parameters
        
        Returns:
            Standardized payment items dictionary
        """
        try:
            if not payment_id:
                return LineItemsHandler._empty_result('payment', 'No Payment ID provided')
            
            # Convert to UUID if string
            if isinstance(payment_id, str):
                try:
                    payment_id = uuid.UUID(payment_id)
                except ValueError:
                    return LineItemsHandler._error_result('payment', 'Invalid Payment ID format')
            
            with get_db_session() as session:
                from app.models.transaction import SupplierPayment, SupplierInvoice
                
                # Get payment
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id
                ).first()
                
                if not payment:
                    return LineItemsHandler._empty_result('payment', 'Payment not found')
                
                # Get associated invoice(s)
                items = []
                if payment.invoice_id:
                    invoice = session.query(SupplierInvoice).filter(
                        SupplierInvoice.invoice_id == payment.invoice_id
                    ).first()
                    
                    if invoice:
                        items.append({
                            'invoice_number': invoice.supplier_invoice_number,
                            'invoice_date': invoice.invoice_date.strftime('%d %b %Y') if invoice.invoice_date else '',
                            'invoice_amount': float(invoice.total_amount or 0),
                            'payment_amount': float(payment.amount or 0),
                            'balance': float((invoice.total_amount or 0) - (payment.amount or 0))
                        })
                
                return {
                    'items': items,
                    'has_items': bool(items),
                    'entity_type': 'payment',
                    'currency_symbol': '₹',
                    'header_info': {
                        'reference_no': payment.reference_no,
                        'payment_date': payment.payment_date.strftime('%d %b %Y') if payment.payment_date else '',
                        'payment_method': payment.payment_method,
                        'amount': float(payment.amount or 0),
                        'status': payment.status or 'completed'
                    },
                    'summary': {
                        'total_paid': float(payment.amount or 0),
                        'invoice_count': len(items)
                    },
                    'context': context
                }
                
        except Exception as e:
            logger.error(f"Error fetching payment items: {str(e)}")
            return LineItemsHandler._error_result('payment', str(e))
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @staticmethod
    def _format_po_line(line: Any, index: int) -> Dict:
        """Format a PO line item with safe attribute access"""
        quantity = line.units or Decimal(0)
        unit_price = line.pack_purchase_price or Decimal(0)
        base_amount = quantity * unit_price
        
        # FIXED: Use getattr with defaults for fields that may not exist
        discount_percent = getattr(line, 'discount_percent', Decimal(0))
        discount_amount = getattr(line, 'discount_amount', Decimal(0))
        
        # Only calculate discount_amount if not already present but discount_percent exists
        if discount_percent > 0 and not discount_amount:
            discount_amount = base_amount * (discount_percent / 100)
        
        # Use taxable_amount if it exists, otherwise calculate
        taxable_amount = getattr(line, 'taxable_amount', base_amount - discount_amount)
        
        # GST calculation
        gst_amount = line.total_gst or Decimal(0)
        if not gst_amount and line.gst_rate:
            gst_amount = (taxable_amount * line.gst_rate) / 100
        
        # Line total
        line_total = line.line_total or (taxable_amount + gst_amount)
        
        return {
            'line_no': index,
            'item_name': line.medicine_name or 'Unknown Item',
            'hsn_code': getattr(line, 'hsn_code', '-'),
            'quantity': float(quantity),
            'unit_price': float(unit_price),
            'mrp': float(line.pack_mrp or 0),
            'discount_percent': float(discount_percent),
            'discount_amount': float(discount_amount),
            'gst_rate': float(line.gst_rate or 0),
            'gst_amount': float(gst_amount),
            'taxable_amount': float(taxable_amount),
            'line_total': float(line_total),
            'expected_delivery': line.expected_delivery_date.strftime('%d %b %Y') if hasattr(line, 'expected_delivery_date') and line.expected_delivery_date else '-'
        }
    
    @staticmethod
    def _format_invoice_line(line: Any, index: int) -> Dict:
        """Format an invoice line item"""
        quantity = line.units or Decimal(0)
        unit_price = line.pack_purchase_price or Decimal(0)
        base_amount = quantity * unit_price
        
        discount_percent = line.discount_percent or Decimal(0)
        discount_amount = line.discount_amount or Decimal(0)
        if discount_percent and not discount_amount:
            discount_amount = (base_amount * discount_percent) / 100
        
        taxable_amount = base_amount - discount_amount
        gst_amount = line.total_gst or Decimal(0)
        if not gst_amount and line.gst_rate:
            gst_amount = (taxable_amount * line.gst_rate) / 100
        
        line_total = line.line_total or (taxable_amount + gst_amount)
        
        return {
            'line_no': index,
            'item_name': line.medicine_name or 'Unknown Item',
            'batch_number': getattr(line, 'batch_number', '-'),
            'expiry_date': line.expiry_date.strftime('%b %Y') if hasattr(line, 'expiry_date') and line.expiry_date else '-',
            'quantity': float(quantity),
            'unit_price': float(unit_price),
            'mrp': float(line.pack_mrp or 0),
            'discount_percent': float(discount_percent),
            'discount_amount': float(discount_amount),
            'gst_rate': float(line.gst_rate or 0),
            'gst_amount': float(gst_amount),
            'taxable_amount': float(taxable_amount),
            'line_total': float(line_total),
            'is_free': getattr(line, 'is_free_item', False)
        }
    
    @staticmethod
    def _empty_result(entity_type: str, message: str, header_info: Dict = None) -> Dict:
        """Return empty result structure"""
        return {
            'items': [],
            'has_items': False,
            'entity_type': entity_type,
            'currency_symbol': '₹',
            'header_info': header_info or {},
            'summary': {
                'line_count': 0,
                'subtotal': 0,
                'total_discount': 0,
                'total_gst': 0,
                'grand_total': 0
            },
            'message': message
        }
    
    @staticmethod
    def _error_result(entity_type: str, error: str) -> Dict:
        """Return error result structure"""
        result = LineItemsHandler._empty_result(entity_type, f'Error: {error}')
        result['has_error'] = True
        result['error'] = error
        return result


# Create singleton instance for easy import
line_items_handler = LineItemsHandler()