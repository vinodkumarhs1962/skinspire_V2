# app/services/credit_note_service.py
# New service for credit note functionality

from datetime import datetime, timezone
import uuid
from typing import Dict, Optional, List
from decimal import Decimal
import logging

from sqlalchemy.orm import Session
from app.models.transaction import SupplierInvoice, SupplierInvoiceLine
from app.services.database_service import get_db_session, get_entity_dict
from app.services.supplier_service import _create_supplier_invoice
from app.services.posting_config_service import get_posting_config

logger = logging.getLogger(__name__)

def create_credit_note_for_paid_invoice(
    original_invoice_id: uuid.UUID,
    credit_note_data: Dict,
    current_user_id: str,
    requires_approval: bool = True,
    session: Optional[Session] = None
) -> Dict:
    """
    Create credit note to reverse a paid invoice
    IMPLEMENTS: Business requirement 5.1 - Credit note process
    """
    logger.info(f"Creating credit note for paid invoice {original_invoice_id}")
    
    if session is not None:
        return _create_credit_note_for_paid_invoice_internal(
            session, original_invoice_id, credit_note_data, 
            current_user_id, requires_approval
        )
    
    with get_db_session() as new_session:
        result = _create_credit_note_for_paid_invoice_internal(
            new_session, original_invoice_id, credit_note_data,
            current_user_id, requires_approval
        )
        new_session.commit()
        return result

def _create_credit_note_for_paid_invoice_internal(
    session: Session,
    original_invoice_id: uuid.UUID,
    credit_note_data: Dict,
    current_user_id: str,
    requires_approval: bool
) -> Dict:
    """Internal credit note creation function"""
    
    try:
        # Get and validate original invoice
        original_invoice = session.query(SupplierInvoice).filter_by(
            invoice_id=original_invoice_id
        ).first()
        
        if not original_invoice:
            raise ValueError(f"Original invoice {original_invoice_id} not found")
        
        if original_invoice.payment_status != 'paid':
            raise ValueError("Credit notes can only be created for paid invoices")
        
        if original_invoice.is_credit_note:
            raise ValueError("Cannot create credit note for another credit note")
        
        # Check if credit note already exists
        existing_credit = session.query(SupplierInvoice).filter_by(
            original_invoice_id=original_invoice_id,
            is_credit_note=True
        ).first()
        
        if existing_credit:
            raise ValueError(f"Credit note already exists for invoice {original_invoice.supplier_invoice_number}")
        
        # Prepare credit note data
        credit_note_invoice_data = _prepare_credit_note_data(
            original_invoice, credit_note_data, requires_approval, session
        )
        
        # Create credit note using existing invoice creation function
        credit_note = _create_supplier_invoice(
            session=session,
            hospital_id=original_invoice.hospital_id,
            invoice_data=credit_note_invoice_data,
            create_stock_entries=not requires_approval,  # Only create stock entries if auto-approved
            create_gl_entries=not requires_approval,     # Only create GL entries if auto-approved
            current_user_id=current_user_id
        )
        
        # Link credit note to original invoice
        _link_credit_note_to_original(
            original_invoice, credit_note, session
        )
        
        return credit_note
        
    except Exception as e:
        logger.error(f"Credit note creation failed: {str(e)}")
        raise

def _prepare_credit_note_data(
    original_invoice: SupplierInvoice,
    credit_note_data: Dict,
    requires_approval: bool,
    session: Session
) -> Dict:
    """Prepare data for credit note creation"""
    
    # Generate credit note number
    credit_note_number = credit_note_data.get(
        'supplier_invoice_number',
        f"CN-{original_invoice.supplier_invoice_number}-{datetime.now().strftime('%Y%m%d')}"
    )
    
    # Prepare credit note data
    prepared_data = {
        'supplier_id': original_invoice.supplier_id,
        'supplier_invoice_number': credit_note_number,
        'invoice_date': credit_note_data.get('invoice_date', datetime.now().date()),
        'due_date': credit_note_data.get('due_date', datetime.now().date()),
        
        # Negative amounts for credit note
        'total_amount': -original_invoice.total_amount,
        'cgst_amount': -original_invoice.cgst_amount if original_invoice.cgst_amount else Decimal('0.00'),
        'sgst_amount': -original_invoice.sgst_amount if original_invoice.sgst_amount else Decimal('0.00'),
        'igst_amount': -original_invoice.igst_amount if original_invoice.igst_amount else Decimal('0.00'),
        'total_gst_amount': -original_invoice.total_gst_amount if original_invoice.total_gst_amount else Decimal('0.00'),
        
        # Credit note specific fields
        'original_invoice_id': original_invoice.invoice_id,
        'is_credit_note': True,
        'payment_status': 'approved' if not requires_approval else 'pending',
        'workflow_status': 'approved' if not requires_approval else 'pending',
        
        # Copy relevant fields
        'currency': original_invoice.currency,
        'exchange_rate': original_invoice.exchange_rate,
        'notes': credit_note_data.get('notes', f"Credit note for invoice {original_invoice.supplier_invoice_number}"),
        
        # Line items (negative quantities/amounts)
        'line_items': _prepare_credit_note_lines(original_invoice, session)
    }
    
    return prepared_data

def _prepare_credit_note_lines(original_invoice: SupplierInvoice, session: Session) -> List[Dict]:
    """Prepare line items for credit note (negative quantities)"""
    
    original_lines = session.query(SupplierInvoiceLine).filter_by(
        invoice_id=original_invoice.invoice_id
    ).all()
    
    credit_lines = []
    
    for line in original_lines:
        credit_line = {
            'medicine_id': line.medicine_id,
            'quantity': -line.quantity,  # Negative quantity
            'pack_purchase_price': line.pack_purchase_price,
            'discount_percentage': line.discount_percentage,
            'cgst_rate': line.cgst_rate,
            'sgst_rate': line.sgst_rate,
            'igst_rate': line.igst_rate,
            
            # Calculated negative amounts
            'taxable_amount': -line.taxable_amount if line.taxable_amount else Decimal('0.00'),
            'cgst': -line.cgst if line.cgst else Decimal('0.00'),
            'sgst': -line.sgst if line.sgst else Decimal('0.00'),
            'igst': -line.igst if line.igst else Decimal('0.00'),
            'total_gst': -line.total_gst if line.total_gst else Decimal('0.00'),
            'line_total': -line.line_total if line.line_total else Decimal('0.00'),
            
            'expiry_date': line.expiry_date,
            'batch_no': line.batch_no,
            'notes': f"Credit for: {line.notes or ''}"
        }
        credit_lines.append(credit_line)
    
    return credit_lines

def _link_credit_note_to_original(
    original_invoice: SupplierInvoice,
    credit_note: Dict,
    session: Session
):
    """Link credit note to original invoice"""
    
    # Update original invoice status
    original_invoice.payment_status = 'credited'
    original_invoice.credited_by_invoice_id = uuid.UUID(credit_note['invoice_id'])
    original_invoice.updated_at = datetime.now(timezone.utc)
    
    session.flush()