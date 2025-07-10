# app/services/creditnote_service.py
"""
Centralized Credit Note Service
Handles both invoice-based and payment-based credit notes
"""

from datetime import datetime, timezone, date
import uuid
from typing import Dict, Optional, List
from decimal import Decimal

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.master import Supplier, Medicine
from app.models.transaction import SupplierInvoice, SupplierInvoiceLine, SupplierPayment, GLTransaction, GLEntry, APSubledger
from app.services.database_service import get_db_session, get_entity_dict
from app.services.posting_config_service import get_posting_config

# Import utilities
from app.utils.credit_note_utils import (
    is_credit_note_enabled, 
    generate_credit_note_number,
    validate_credit_amount,
    get_credit_note_description
)

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

# =============================================================================
# EXISTING FUNCTIONS: Invoice-Based Credit Notes (Full Invoice Reversal)
# =============================================================================

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
    EXISTING FUNCTION - Invoice reversal credit notes
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
    """Internal credit note creation function for invoice reversal"""
    
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
        from app.services.supplier_service import _create_supplier_invoice
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
    """Prepare data for credit note creation (invoice reversal)"""
    
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
        'currency_code': original_invoice.currency_code,
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
            'units': -line.units,  # Negative quantity
            'pack_purchase_price': line.pack_purchase_price,
            'discount_percent': line.discount_percent,
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
            'batch_number': line.batch_number,
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

# =============================================================================
# NEW FUNCTIONS: Payment-Based Credit Notes (Phase 1 - Payment Adjustments)
# =============================================================================

def get_supplier_payment_by_id_with_credits(
    payment_id: uuid.UUID,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Optional[Dict]:
    """
    Phase 1: Get supplier payment with basic credit note information
    NEW FUNCTION - Payment adjustment credit notes
    """
    logger.info(f"Fetching payment {payment_id} with credit note information")
    
    if session is not None:
        return _get_supplier_payment_with_credits(session, payment_id, hospital_id, current_user_id)
    
    with get_db_session(read_only=True) as new_session:
        return _get_supplier_payment_with_credits(new_session, payment_id, hospital_id, current_user_id)

def _get_supplier_payment_with_credits(
    session: Session,
    payment_id: uuid.UUID,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Optional[Dict]:
    """Internal function to get payment with credit note details"""
    try:
        # Get payment details
        payment = session.query(SupplierPayment).filter_by(
            payment_id=payment_id,
            hospital_id=hospital_id
        ).first()
        
        if not payment:
            return None
        
        # Get supplier details
        supplier = session.query(Supplier).filter_by(
            supplier_id=payment.supplier_id,
            hospital_id=hospital_id
        ).first()
        
        # Get existing credit notes for this payment
        # Using reference in notes field to link payment-based credit notes
        existing_credits = session.query(SupplierInvoice).filter(
            and_(
                SupplierInvoice.hospital_id == hospital_id,
                SupplierInvoice.is_credit_note == True,
                SupplierInvoice.notes.contains(str(payment_id))
            )
        ).all()
        
        # Calculate net payment amount
        total_credited = sum(abs(float(cn.total_amount)) for cn in existing_credits)
        net_amount = float(payment.amount) - total_credited
        
        # Build payment data using entity dict pattern
        payment_data = get_entity_dict(payment)
        
        # Add credit note specific fields
        payment_data.update({
            'supplier_name': supplier.supplier_name if supplier else 'Unknown',
            'total_credited': total_credited,
            'net_payment_amount': net_amount,
            'can_create_credit_note': _can_create_credit_note_simple(payment, net_amount),
            'existing_credit_notes': [
                {
                    'credit_note_id': str(cn.invoice_id),
                    'credit_note_number': cn.supplier_invoice_number,
                    'credit_amount': abs(float(cn.total_amount)),
                    'credit_date': cn.invoice_date.isoformat() if cn.invoice_date else None
                }
                for cn in existing_credits
            ]
        })
        
        return payment_data
        
    except Exception as e:
        logger.error(f"Error getting payment with credits: {str(e)}")
        raise

def _can_create_credit_note_simple(payment: SupplierPayment, net_amount: float) -> bool:
    """Phase 1: Simple check if credit note can be created"""
    # Must be approved/completed
    workflow_status = getattr(payment, 'workflow_status', 'completed')
    if workflow_status not in ['approved', 'completed']:
        return False
    
    # Must have remaining amount to credit
    if net_amount <= 0:
        return False
    
    # Check if feature is enabled
    if not is_credit_note_enabled():
        return False
    
    return True

def create_simple_credit_note(
    hospital_id: uuid.UUID,
    credit_note_data: Dict,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Phase 1: Create a simple credit note for payment adjustment
    NEW FUNCTION - Payment adjustment credit notes
    """
    logger.info(f"Creating payment adjustment credit note for payment {credit_note_data.get('payment_id')}")
    
    if session is not None:
        return _create_simple_credit_note_transaction(
            session, hospital_id, credit_note_data, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_simple_credit_note_transaction(
            new_session, hospital_id, credit_note_data, current_user_id
        )
        new_session.commit()
        logger.info(f"Successfully created credit note: {result.get('credit_note_number')}")
        return result

def _create_simple_credit_note_transaction(
    session: Session,
    hospital_id: uuid.UUID,
    credit_note_data: Dict,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to create payment adjustment credit note within transaction"""
    try:
        # Step 1: Validate payment
        payment_id = credit_note_data.get('payment_id')
        payment = session.query(SupplierPayment).filter_by(
            payment_id=payment_id,
            hospital_id=hospital_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Step 2: Get supplier
        supplier = session.query(Supplier).filter_by(
            supplier_id=payment.supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError("Supplier not found")
        
        # Step 3: Validate credit amount
        credit_amount = Decimal(str(credit_note_data.get('credit_amount')))
        
        # Get current net amount
        payment_with_credits = _get_supplier_payment_with_credits(
            session, payment_id, hospital_id, current_user_id
        )
        available_amount = payment_with_credits['net_payment_amount']
        
        validation_result = validate_credit_amount(float(credit_amount), available_amount)
        if not validation_result['valid']:
            raise ValueError(validation_result['error'])
        
        # Step 4: Create credit note invoice
        credit_note = SupplierInvoice(
            hospital_id=hospital_id,
            branch_id=credit_note_data.get('branch_id') or payment.branch_id,
            supplier_id=payment.supplier_id,
            supplier_invoice_number=credit_note_data.get('credit_note_number'),
            invoice_date=credit_note_data.get('credit_note_date', date.today()),
            
            # Credit note specific
            is_credit_note=True,
            original_invoice_id=payment.invoice_id,  # Reference original invoice if exists
            
            # Supplier details
            supplier_gstin=supplier.gst_registration_number,
            place_of_supply=supplier.state_code,
            currency_code='INR',
            exchange_rate=Decimal('1.0'),
            
            # Amounts (negative for credit)
            total_amount=-credit_amount,
            cgst_amount=Decimal('0'),
            sgst_amount=Decimal('0'),
            igst_amount=Decimal('0'),
            total_gst_amount=Decimal('0'),
            
            # Status
            payment_status='paid',
            itc_eligible=False,
            
            # Notes and audit - IMPORTANT: Include payment_id for linking
            notes=f"Credit note for payment {payment.reference_no} (Payment ID: {payment_id}): {credit_note_data.get('credit_reason', '')}",
            created_by=current_user_id
        )
        
        session.add(credit_note)
        session.flush()
        
        # Step 5: Create simple line item
        credit_line = _create_credit_note_line_item(
            session, credit_note, credit_amount, credit_note_data, current_user_id
        )
        
        session.add(credit_line)
        
        # Step 6: Update payment notes
        _update_payment_with_credit_reference(session, payment, credit_note, current_user_id)
        
        session.flush()
        
        # =====================================================================
        # NEW STEP 6.5: CREATE GL ENTRIES FOR CREDIT NOTE (ADD THIS CODE)
        # =====================================================================
        logger.info("Creating GL entries for credit note")
        gl_posting_result = _create_credit_note_gl_entries(
            session, credit_note, payment, credit_amount, current_user_id
        )
        
        # =====================================================================
        # NEW STEP 6.6: CREATE PAYMENT ENTRY FOR CREDIT ADJUSTMENT (ADD THIS CODE) 
        # =====================================================================
        logger.info("Creating payment entry for credit adjustment")
        payment_result = _create_credit_note_payment_entry(
            session, credit_note, payment, credit_amount, current_user_id
        )
        
        # =====================================================================
        # NEW Step 6.7: Update Related Invoice (ADD THIS CODE)
        # =====================================================================
        logger.info("Updating related invoice for credit note")
        invoice_update_result = _update_related_invoice_for_credit_note(
            session, payment, credit_note, credit_amount, current_user_id
        )

        # Step 7: Return result (MODIFY EXISTING RETURN TO INCLUDE NEW DATA)
        result = {
            'credit_note_id': str(credit_note.invoice_id),
            'credit_note_number': credit_note.supplier_invoice_number,
            'credit_amount': float(credit_amount),
            'payment_id': str(payment_id),
            'supplier_name': supplier.supplier_name,
            'created_successfully': True,
            
            # NEW: Add GL posting information
            'gl_posted': True,
            'gl_transaction_id': gl_posting_result['gl_transaction_id'],
            'posting_reference': gl_posting_result['posting_reference'],
            'gl_entries_created': gl_posting_result['gl_entries_count'],
            'ap_subledger_updated': gl_posting_result['ap_balance_updated'],
            
            # NEW: Add payment information
            'credit_payment_created': True,
            'credit_payment_id': payment_result['credit_payment_id'],
            'credit_payment_reference': payment_result['credit_payment_reference'],
            'original_payment_method': payment_result['payment_method'],
            'payment_method_breakdown': {
                'cash_amount': payment_result['cash_amount'],
                'cheque_amount': payment_result['cheque_amount'],
                'bank_amount': payment_result['bank_amount'],
                'upi_amount': payment_result['upi_amount'],
                'related_invoice_updated': invoice_update_result['invoice_updated'],
                'invoice_update_details': invoice_update_result
            }
        }
        
        logger.info(f"Created payment adjustment credit note {credit_note.supplier_invoice_number} for payment {payment.reference_no}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in payment credit note transaction: {str(e)}")
        session.rollback()
        raise


def _create_credit_note_gl_entries(
    session: Session,
    credit_note: SupplierInvoice,
    payment: SupplierPayment,
    credit_amount: Decimal,
    current_user_id: str
) -> Dict:
    """
    Create GL entries for payment adjustment credit note
    This implements the missing accounting treatment for credit notes
    
    Accounting Treatment:
    Dr. Accounts Payable    $XXX  (Reduce liability to supplier)
        Cr. Credit Note Expense   $XXX  (Record the adjustment)
    """
    try:
        logger.info(f"Creating GL entries for credit note {credit_note.supplier_invoice_number}")
        
        # Step 1: Create GL Transaction
        posting_reference = f"CN-{credit_note.supplier_invoice_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Truncate if too long for database constraint
        if len(posting_reference) > 50:
            posting_reference = posting_reference[:50]
        
        gl_transaction = GLTransaction(
            hospital_id=credit_note.hospital_id,
            transaction_date=credit_note.invoice_date,
            transaction_type='CREDIT_NOTE_PAYMENT_ADJ',  # New transaction type
            reference_id=str(credit_note.invoice_id),
            description=f"Payment Adjustment Credit Note - {credit_note.supplier_invoice_number}",
            source_document_type='CREDIT_NOTE',
            source_document_id=credit_note.invoice_id,
            total_debit=credit_amount,
            total_credit=credit_amount,
            created_by=current_user_id
        )
        
        session.add(gl_transaction)
        session.flush()  # Get transaction_id
        
        # Step 2: Get account mappings
        from app.services.posting_config_service import get_posting_config
        config = get_posting_config(str(credit_note.hospital_id))
        
        ap_account_no = config.get('DEFAULT_AP_ACCOUNT', '2001')
        credit_note_expense_account_no = config.get('CREDIT_NOTE_EXPENSE_ACCOUNT', '5999')  # New account for credit note adjustments
        
        # Step 3: Get account records
        from app.models.master import ChartOfAccounts
        
        ap_account = session.query(ChartOfAccounts).filter_by(
            hospital_id=credit_note.hospital_id,
            gl_account_no=ap_account_no,
            is_active=True
        ).first()
        
        credit_note_account = session.query(ChartOfAccounts).filter_by(
            hospital_id=credit_note.hospital_id,
            gl_account_no=credit_note_expense_account_no,
            is_active=True
        ).first()
        
        if not ap_account:
            raise ValueError(f"AP Account {ap_account_no} not found in chart of accounts")
        if not credit_note_account:
            logger.warning(f"Credit Note Expense Account {credit_note_expense_account_no} not found, using default expense account")
            # Use a default expense account if credit note account doesn't exist
            default_expense_account_no = config.get('DEFAULT_EXPENSE_ACCOUNT', '5001')
            credit_note_account = session.query(ChartOfAccounts).filter_by(
                hospital_id=credit_note.hospital_id,
                gl_account_no=default_expense_account_no,
                is_active=True
            ).first()
            
            if not credit_note_account:
                raise ValueError(f"Neither Credit Note Expense Account nor Default Expense Account found")
        
        # Step 4: Create GL Entries
        gl_entries = []
        
        # Entry 1: Debit Accounts Payable (reduce liability to supplier)
        ap_entry = GLEntry(
            hospital_id=credit_note.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=ap_account.account_id,
            entry_date=credit_note.invoice_date,
            description=f"AP Credit Note - {credit_note.supplier_invoice_number}",
            debit_amount=credit_amount,
            credit_amount=Decimal('0'),
            source_document_type='CREDIT_NOTE',
            source_document_id=credit_note.invoice_id,
            posting_reference=posting_reference,
            created_by=current_user_id
        )
        session.add(ap_entry)
        gl_entries.append(ap_entry)
        
        # Entry 2: Credit Credit Note Expense (record the adjustment)
        expense_entry = GLEntry(
            hospital_id=credit_note.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=credit_note_account.account_id,
            entry_date=credit_note.invoice_date,
            description=f"Credit Note Expense - {credit_note.supplier_invoice_number}",
            debit_amount=Decimal('0'),
            credit_amount=credit_amount,
            source_document_type='CREDIT_NOTE',
            source_document_id=credit_note.invoice_id,
            posting_reference=posting_reference,
            created_by=current_user_id
        )
        session.add(expense_entry)
        gl_entries.append(expense_entry)
        
        # Step 5: Update AP Subledger
        from sqlalchemy import func
        
        # Get current supplier balance
        current_supplier_balance = session.query(
            func.sum(APSubledger.credit_amount) - func.sum(APSubledger.debit_amount)
        ).filter_by(
            hospital_id=credit_note.hospital_id,
            supplier_id=credit_note.supplier_id
        ).scalar() or Decimal('0')
        
        new_balance = current_supplier_balance - credit_amount  # Reduce supplier balance
        
        ap_subledger_entry = APSubledger(
            hospital_id=credit_note.hospital_id,
            branch_id=getattr(credit_note, 'branch_id', None),
            transaction_date=credit_note.invoice_date,
            entry_type='credit_note',
            reference_id=str(credit_note.invoice_id),
            reference_type='credit_note',
            reference_number=credit_note.supplier_invoice_number,
            supplier_id=credit_note.supplier_id,
            debit_amount=credit_amount,  # Debit reduces the balance
            credit_amount=Decimal('0'),
            current_balance=new_balance,
            gl_transaction_id=gl_transaction.transaction_id,
            created_by=current_user_id
        )
        session.add(ap_subledger_entry)
        
        # Step 6: Update credit note with GL posting info
        credit_note.gl_posted = True
        credit_note.posting_reference = posting_reference
        
        logger.info(f"Created {len(gl_entries)} GL entries for credit note {credit_note.supplier_invoice_number}")
        logger.info(f"GL Transaction ID: {gl_transaction.transaction_id}")
        logger.info(f"Posting Reference: {posting_reference}")
        
        return {
            'gl_transaction_id': str(gl_transaction.transaction_id),
            'gl_entries_count': len(gl_entries),
            'posting_reference': posting_reference,
            'ap_balance_updated': True,
            'gl_posted': True
        }
        
    except Exception as e:
        logger.error(f"Error creating GL entries for credit note: {str(e)}")
        raise

# Create payment entry for credit note adjustment
def _create_credit_note_payment_entry(
    session: Session,
    credit_note: SupplierInvoice,
    original_payment: SupplierPayment,
    credit_amount: Decimal,
    current_user_id: str
) -> Dict:
    """
    Create corresponding payment entry for credit note adjustment
    This creates a negative payment entry with same payment method as original
    """
    try:
        logger.info(f"Creating payment entry for credit note {credit_note.supplier_invoice_number}")
        
        # Generate credit payment reference
        credit_payment_ref = f"CN-ADJ-{original_payment.reference_no}-{datetime.now().strftime('%Y%m%d')}"
        
        # Calculate proportional payment method breakdown
        original_total = original_payment.amount
        credit_ratio = credit_amount / original_total
        
        # Apply same payment method distribution as original payment
        cash_amount = -(original_payment.cash_amount or Decimal('0')) * credit_ratio
        cheque_amount = -(original_payment.cheque_amount or Decimal('0')) * credit_ratio
        bank_amount = -(original_payment.bank_transfer_amount or Decimal('0')) * credit_ratio
        upi_amount = -(original_payment.upi_amount or Decimal('0')) * credit_ratio
        
        # Ensure amounts add up correctly (handle rounding)
        total_methods = abs(cash_amount + cheque_amount + bank_amount + upi_amount)
        if abs(total_methods - credit_amount) > Decimal('0.01'):
            # Adjust the largest component to ensure exact match
            amounts = [
                ('cash_amount', abs(cash_amount)),
                ('cheque_amount', abs(cheque_amount)), 
                ('bank_amount', abs(bank_amount)),
                ('upi_amount', abs(upi_amount))
            ]
            largest_method = max(amounts, key=lambda x: x[1])[0]
            
            if largest_method == 'cash_amount':
                cash_amount = -credit_amount + cheque_amount + bank_amount + upi_amount
            elif largest_method == 'cheque_amount':
                cheque_amount = -credit_amount + cash_amount + bank_amount + upi_amount
            elif largest_method == 'bank_amount':
                bank_amount = -credit_amount + cash_amount + cheque_amount + upi_amount
            elif largest_method == 'upi_amount':
                upi_amount = -credit_amount + cash_amount + cheque_amount + bank_amount
        
        # Create credit payment entry
        credit_payment = SupplierPayment(
            hospital_id=credit_note.hospital_id,
            branch_id=original_payment.branch_id,
            supplier_id=credit_note.supplier_id,
            invoice_id=credit_note.invoice_id,  # Link to credit note
            payment_date=credit_note.invoice_date,
            payment_method=original_payment.payment_method,  # Same method as original
            amount=-credit_amount,  # Negative amount
            reference_no=credit_payment_ref,
            notes=f"Credit note adjustment for {original_payment.reference_no}: {credit_note.supplier_invoice_number}",
            
            # Payment method breakdown (negative amounts)
            cash_amount=cash_amount,
            cheque_amount=cheque_amount,
            bank_transfer_amount=bank_amount,
            upi_amount=upi_amount,
            
            # Copy payment method details from original (if applicable)
            cheque_number=f"CN-REV-{original_payment.cheque_number}" if original_payment.cheque_number and cheque_amount != 0 else None,
            cheque_date=original_payment.cheque_date if original_payment.cheque_date and cheque_amount != 0 else None,
            cheque_bank=original_payment.cheque_bank if original_payment.cheque_bank and cheque_amount != 0 else None,
            bank_reference_number=f"CN-REV-{original_payment.bank_reference_number}" if original_payment.bank_reference_number and bank_amount != 0 else None,
            bank_account_name=original_payment.bank_account_name if original_payment.bank_account_name and bank_amount != 0 else None,
            ifsc_code=original_payment.ifsc_code if original_payment.ifsc_code and bank_amount != 0 else None,
            upi_transaction_id=f"CN-REV-{original_payment.upi_transaction_id}" if original_payment.upi_transaction_id and upi_amount != 0 else None,
            upi_app_name=original_payment.upi_app_name if original_payment.upi_app_name and upi_amount != 0 else None,
            
            # Status and workflow
            workflow_status='completed',  # Credit adjustments are auto-approved
            requires_approval=False,
            currency_code=original_payment.currency_code or 'INR',
            exchange_rate=original_payment.exchange_rate or Decimal('1.0'),
            
            # Audit fields
            created_by=current_user_id
        )
        
        session.add(credit_payment)
        session.flush()
        
        # Create GL entries for the credit payment (reverse of original payment GL entries)
        payment_gl_result = _create_credit_payment_gl_entries(
            session, credit_payment, credit_amount, current_user_id
        )
        
        logger.info(f"Created credit payment entry {credit_payment_ref} for {credit_amount}")
        
        return {
            'credit_payment_id': str(credit_payment.payment_id),
            'credit_payment_reference': credit_payment_ref,
            'payment_method': original_payment.payment_method,
            'cash_amount': float(cash_amount),
            'cheque_amount': float(cheque_amount),
            'bank_amount': float(bank_amount),
            'upi_amount': float(upi_amount),
            'payment_gl_posted': payment_gl_result['gl_posted']
        }
        
    except Exception as e:
        logger.error(f"Error creating credit payment entry: {str(e)}")
        raise

def _create_credit_payment_gl_entries(
    session: Session,
    credit_payment: SupplierPayment,
    credit_amount: Decimal,
    current_user_id: str
) -> Dict:
    """
    Create GL entries for credit payment (reverse of normal payment)
    Normal Payment: Dr. AP, Cr. Bank
    Credit Payment: Dr. Bank, Cr. AP
    """
    try:
        # Generate posting reference
        posting_reference = f"CN-PAY-{credit_payment.reference_no}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if len(posting_reference) > 50:
            posting_reference = posting_reference[:50]
        
        # Create GL Transaction for payment
        gl_transaction = GLTransaction(
            hospital_id=credit_payment.hospital_id,
            transaction_date=credit_payment.payment_date,
            transaction_type='CREDIT_NOTE_PAYMENT',
            reference_id=str(credit_payment.payment_id),
            description=f"Credit Note Payment Adjustment - {credit_payment.reference_no}",
            source_document_type='CREDIT_PAYMENT',
            source_document_id=credit_payment.payment_id,
            total_debit=credit_amount,
            total_credit=credit_amount,
            created_by=current_user_id
        )
        
        session.add(gl_transaction)
        session.flush()
        
        # Get account mappings
        from app.services.posting_config_service import get_posting_config
        from app.models.master import ChartOfAccounts
        
        config = get_posting_config(str(credit_payment.hospital_id))
        ap_account_no = config.get('DEFAULT_AP_ACCOUNT', '2001')
        
        # Determine bank account based on payment method
        if credit_payment.cash_amount and credit_payment.cash_amount != 0:
            bank_account_no = config.get('DEFAULT_CASH_ACCOUNT', '1002')
        else:
            bank_account_no = config.get('DEFAULT_BANK_ACCOUNT', '1001')
        
        # Get accounts
        ap_account = session.query(ChartOfAccounts).filter_by(
            hospital_id=credit_payment.hospital_id,
            gl_account_no=ap_account_no,
            is_active=True
        ).first()
        
        bank_account = session.query(ChartOfAccounts).filter_by(
            hospital_id=credit_payment.hospital_id,
            gl_account_no=bank_account_no,
            is_active=True
        ).first()
        
        if not ap_account or not bank_account:
            raise ValueError(f"Required accounts not found: AP={ap_account_no}, Bank={bank_account_no}")
        
        # Create GL entries (reverse of normal payment)
        gl_entries = []
        
        # Entry 1: Debit Bank (money coming back)
        bank_entry = GLEntry(
            hospital_id=credit_payment.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=bank_account.account_id,
            entry_date=credit_payment.payment_date,
            description=f"Credit Payment Adjustment - {credit_payment.reference_no}",
            debit_amount=credit_amount,
            credit_amount=Decimal('0'),
            source_document_type='CREDIT_PAYMENT',
            source_document_id=credit_payment.payment_id,
            posting_reference=posting_reference,
            created_by=current_user_id
        )
        session.add(bank_entry)
        gl_entries.append(bank_entry)
        
        # Entry 2: Credit AP (increase liability)
        ap_entry = GLEntry(
            hospital_id=credit_payment.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=ap_account.account_id,
            entry_date=credit_payment.payment_date,
            description=f"Credit Payment AP Adjustment - {credit_payment.reference_no}",
            debit_amount=Decimal('0'),
            credit_amount=credit_amount,
            source_document_type='CREDIT_PAYMENT',
            source_document_id=credit_payment.payment_id,
            posting_reference=posting_reference,
            created_by=current_user_id
        )
        session.add(ap_entry)
        gl_entries.append(ap_entry)
        
        # Update payment with GL info
        credit_payment.gl_posted = True
        credit_payment.posting_reference = posting_reference
        
        logger.info(f"Created {len(gl_entries)} GL entries for credit payment")
        
        return {
            'gl_posted': True,
            'gl_transaction_id': str(gl_transaction.transaction_id),
            'posting_reference': posting_reference
        }
        
    except Exception as e:
        logger.error(f"Error creating credit payment GL entries: {str(e)}")
        raise

def _update_related_invoice_for_credit_note(
    session: Session,
    payment: SupplierPayment,
    credit_note: SupplierInvoice,
    credit_amount: Decimal,
    current_user_id: str
) -> Dict:
    """
    Update related invoice when credit note is created - FIXED to include current credit
    """
    try:
        # Check if payment was linked to an invoice
        if not payment.invoice_id:
            logger.info("Payment not linked to invoice - no invoice update needed")
            return {'invoice_updated': False, 'reason': 'No linked invoice'}
        
        # Get the related invoice
        related_invoice = session.query(SupplierInvoice).filter_by(
            invoice_id=payment.invoice_id,
            hospital_id=payment.hospital_id
        ).first()
        
        if not related_invoice:
            logger.warning(f"Related invoice {payment.invoice_id} not found")
            return {'invoice_updated': False, 'reason': 'Invoice not found'}
        
        logger.info(f"Updating invoice {related_invoice.supplier_invoice_number} for credit note {credit_note.supplier_invoice_number}")
        
        # FIXED: Calculate payment totals correctly INCLUDING current credit
        from sqlalchemy import func
        
        # Get POSITIVE payments only (original payments)
        positive_payments_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
            invoice_id=related_invoice.invoice_id,
            workflow_status='approved'
        ).filter(
            SupplierPayment.amount > 0  # Only positive payments
        ).scalar() or Decimal('0')
        
        # Get existing NEGATIVE payments (credit adjustments) - convert to positive
        existing_credits = session.query(func.sum(SupplierPayment.amount)).filter_by(
            invoice_id=related_invoice.invoice_id,
            workflow_status='approved'
        ).filter(
            SupplierPayment.amount < 0  # Only negative credit payments
        ).scalar() or Decimal('0')
        
        # CRITICAL FIX: Add current credit amount to total credits
        # (since the credit payment hasn't been committed yet)
        total_credit_adjustments = abs(existing_credits) + credit_amount
        
        # FIXED: Calculate NET effective payment amount
        effective_payment_total = positive_payments_total - total_credit_adjustments
        invoice_total = related_invoice.total_amount
        
        # FIXED: Recalculate payment status based on NET effective payments
        old_status = related_invoice.payment_status
        
        if effective_payment_total >= invoice_total:
            new_status = 'paid'
        elif effective_payment_total > 0:
            new_status = 'partial'
        else:
            new_status = 'unpaid'
        
        # Update invoice fields
        related_invoice.payment_status = new_status
        related_invoice.updated_at = datetime.now(timezone.utc)
        related_invoice.updated_by = current_user_id
        
        # Add credit note reference to invoice notes
        credit_reference = f"Credit Note: {credit_note.supplier_invoice_number} (₹{credit_amount})"
        if related_invoice.notes:
            if credit_reference not in related_invoice.notes:
                related_invoice.notes = f"{related_invoice.notes}\n{credit_reference}"
        else:
            related_invoice.notes = credit_reference
        
        # Add custom fields if they exist in your schema
        try:
            if hasattr(related_invoice, 'has_credit_notes'):
                related_invoice.has_credit_notes = True
            
            if hasattr(related_invoice, 'credit_notes_total'):
                related_invoice.credit_notes_total = total_credit_adjustments
        except Exception as e:
            logger.debug(f"Optional credit note fields not available: {str(e)}")
        
        session.flush()
        
        # FIXED: Log with correct values INCLUDING current credit
        logger.info(f"Updated invoice {related_invoice.supplier_invoice_number}: "
                   f"Status {old_status} -> {new_status}, "
                   f"Positive Payments: ₹{positive_payments_total}, "
                   f"Credit Adjustments: ₹{total_credit_adjustments}, "
                   f"NET Effective Payment: ₹{effective_payment_total}")
        
        return {
            'invoice_updated': True,
            'invoice_id': str(related_invoice.invoice_id),
            'invoice_number': related_invoice.supplier_invoice_number,
            'old_status': old_status,
            'new_status': new_status,
            'positive_payments': float(positive_payments_total),
            'credit_adjustments': float(total_credit_adjustments),
            'effective_payment_total': float(effective_payment_total),
            'invoice_total': float(invoice_total),
            'balance_due': float(invoice_total - effective_payment_total) if effective_payment_total < invoice_total else 0.0
        }
        
    except Exception as e:
        logger.error(f"Error updating related invoice: {str(e)}")
        raise


def _create_credit_note_line_item(
    session: Session, 
    credit_note: SupplierInvoice, 
    credit_amount: Decimal,
    credit_note_data: Dict,
    current_user_id: str
) -> SupplierInvoiceLine:
    """Create credit note line item for payment adjustment"""
    
    # Try to find any existing medicine to use as required by model
    medicine_id = _get_any_medicine_id(session, credit_note.hospital_id)
    
    # Create description using utility function
    reason_code = credit_note_data.get('reason_code', 'adjustment')
    description = get_credit_note_description(reason_code, credit_note_data.get('credit_reason', ''))
    
    # Create line item
    credit_line = SupplierInvoiceLine(
        hospital_id=credit_note.hospital_id,
        invoice_id=credit_note.invoice_id,
        
        # Medicine reference (use any available)
        medicine_id=medicine_id,
        medicine_name=description,
        
        # Quantities (negative for credit)
        units=Decimal('1'),
        pack_purchase_price=-credit_amount,
        pack_mrp=Decimal('0'),
        units_per_pack=Decimal('1'),
        unit_price=-credit_amount,
        
        # Line totals
        taxable_amount=-credit_amount,
        line_total=-credit_amount,
        
        # No GST on adjustments
        gst_rate=Decimal('0'),
        cgst_rate=Decimal('0'),
        sgst_rate=Decimal('0'),
        igst_rate=Decimal('0'),
        cgst=Decimal('0'),
        sgst=Decimal('0'),
        igst=Decimal('0'),
        total_gst=Decimal('0'),
        
        # Additional fields
        is_free_item=False,
        discount_percent=Decimal('0'),
        discount_amount=Decimal('0'),
        
        # Audit
        created_by=current_user_id
    )
    
    return credit_line

def _get_any_medicine_id(session: Session, hospital_id: uuid.UUID) -> Optional[uuid.UUID]:
    """Get any available medicine ID for line item requirement"""
    try:
        # Try to find any medicine in the system
        any_medicine = session.query(Medicine).filter_by(
            hospital_id=hospital_id,
            status='active'
        ).first()
        
        return any_medicine.medicine_id if any_medicine else None
        
    except Exception:
        # If no medicine found, we'll handle this in the line item creation
        return None

def _update_payment_with_credit_reference(
    session: Session,
    payment: SupplierPayment,
    credit_note: SupplierInvoice,
    current_user_id: str
):
    """Update payment with reference to credit note"""
    payment_notes = payment.notes or ''
    credit_reference = f"Credit Note: {credit_note.supplier_invoice_number}"
    
    if credit_reference not in payment_notes:
        payment.notes = f"{payment_notes}\n{credit_reference}".strip()
        payment.updated_by = current_user_id
        payment.updated_at = datetime.now(timezone.utc)

def validate_credit_note_creation_simple(
    payment_id: uuid.UUID,
    credit_amount: float,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Phase 1: Simple validation for credit note creation
    NEW FUNCTION - Payment adjustment validation
    """
    logger.info(f"Validating payment adjustment credit note creation for payment {payment_id}")
    
    if session is not None:
        return _validate_credit_note_creation(
            session, payment_id, credit_amount, hospital_id, current_user_id
        )
    
    with get_db_session(read_only=True) as new_session:
        return _validate_credit_note_creation(
            new_session, payment_id, credit_amount, hospital_id, current_user_id
        )

def _validate_credit_note_creation(
    session: Session,
    payment_id: uuid.UUID,
    credit_amount: float,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal validation function for payment credit notes"""
    try:
        # Get payment with credit info
        payment = _get_supplier_payment_with_credits(session, payment_id, hospital_id, current_user_id)
        
        if not payment:
            return {
                'valid': False,
                'error': 'Payment not found',
                'error_code': 'PAYMENT_NOT_FOUND'
            }
        
        # Check if credit notes can be created
        if not payment.get('can_create_credit_note', False):
            return {
                'valid': False,
                'error': 'Credit notes cannot be created for this payment',
                'error_code': 'CREDIT_NOT_ALLOWED'
            }
        
        # Validate amount using utility function
        available_amount = payment.get('net_payment_amount', 0)
        validation_result = validate_credit_amount(credit_amount, available_amount)
        
        if not validation_result['valid']:
            return {
                'valid': False,
                'error': validation_result['error'],
                'error_code': validation_result['error_code']
            }
        
        # All validations passed
        return {
            'valid': True,
            'payment': payment,
            'available_amount': available_amount,
            'requested_amount': credit_amount
        }
        
    except Exception as e:
        logger.error(f"Error validating payment credit note creation: {str(e)}")
        return {
            'valid': False,
            'error': f'Validation error: {str(e)}',
            'error_code': 'VALIDATION_ERROR'
        }

# =============================================================================
# UTILITY FUNCTIONS: Common functions for both types of credit notes
# =============================================================================

def get_credit_notes_list(
    hospital_id: uuid.UUID,
    credit_note_type: str = 'all',  # 'all', 'invoice_reversal', 'payment_adjustment'
    limit: int = 50,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get list of credit notes with filtering
    UTILITY FUNCTION - Works for both types
    """
    if session is not None:
        return _get_credit_notes_list(session, hospital_id, credit_note_type, limit, current_user_id)
    
    with get_db_session(read_only=True) as new_session:
        return _get_credit_notes_list(new_session, hospital_id, credit_note_type, limit, current_user_id)

def _get_credit_notes_list(
    session: Session,
    hospital_id: uuid.UUID,
    credit_note_type: str = 'all',
    limit: int = 50,
    current_user_id: Optional[str] = None
) -> List[Dict]:
    """Internal function to get credit notes list"""
    try:
        # Base query for all credit notes
        query = session.query(
            SupplierInvoice.invoice_id,
            SupplierInvoice.supplier_invoice_number,
            SupplierInvoice.invoice_date,
            SupplierInvoice.total_amount,
            SupplierInvoice.payment_status,
            SupplierInvoice.created_at,
            SupplierInvoice.original_invoice_id,
            SupplierInvoice.notes,
            Supplier.supplier_name
        ).join(
            Supplier, SupplierInvoice.supplier_id == Supplier.supplier_id
        ).filter(
            and_(
                SupplierInvoice.hospital_id == hospital_id,
                SupplierInvoice.is_credit_note == True
            )
        )
        
        # Filter by credit note type if specified
        if credit_note_type == 'invoice_reversal':
            # Invoice reversal credit notes have original_invoice_id and don't contain "Payment ID:" in notes
            query = query.filter(
                and_(
                    SupplierInvoice.original_invoice_id.isnot(None),
                    ~SupplierInvoice.notes.contains("Payment ID:")
                )
            )
        elif credit_note_type == 'payment_adjustment':
            # Payment adjustment credit notes contain "Payment ID:" in notes
            query = query.filter(SupplierInvoice.notes.contains("Payment ID:"))
        
        # Order and limit
        query = query.order_by(desc(SupplierInvoice.created_at)).limit(limit)
        
        credit_notes = query.all()
        
        # Format for return
        formatted_credit_notes = []
        for cn in credit_notes:
            # Determine credit note type
            if "Payment ID:" in (cn.notes or ''):
                cn_type = 'payment_adjustment'
            elif cn.original_invoice_id:
                cn_type = 'invoice_reversal'
            else:
                cn_type = 'unknown'
            
            formatted_credit_notes.append({
                'credit_note_id': str(cn.invoice_id),
                'credit_note_number': cn.supplier_invoice_number,
                'credit_date': cn.invoice_date,
                'credit_amount': abs(float(cn.total_amount)),
                'supplier_name': cn.supplier_name,
                'status': cn.payment_status,
                'created_at': cn.created_at,
                'credit_note_type': cn_type,
                'original_invoice_id': str(cn.original_invoice_id) if cn.original_invoice_id else None
            })
        
        return formatted_credit_notes
        
    except Exception as e:
        logger.error(f"Error getting credit notes list: {str(e)}")
        raise

# =============================================================================
# SUMMARY FUNCTIONS: Get credit note statistics
# =============================================================================

def get_credit_note_summary(
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Get summary statistics for credit notes
    UTILITY FUNCTION - Summary for both types
    """
    if session is not None:
        return _get_credit_note_summary(session, hospital_id, current_user_id)
    
    with get_db_session(read_only=True) as new_session:
        return _get_credit_note_summary(new_session, hospital_id, current_user_id)

def _get_credit_note_summary(
    session: Session,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to get credit note summary"""
    try:
        # Get all credit notes
        all_credits = session.query(SupplierInvoice).filter(
            and_(
                SupplierInvoice.hospital_id == hospital_id,
                SupplierInvoice.is_credit_note == True
            )
        ).all()
        
        # Calculate statistics
        total_count = len(all_credits)
        total_amount = sum(abs(float(cn.total_amount)) for cn in all_credits)
        
        # Separate by type
        invoice_reversals = [cn for cn in all_credits 
                           if cn.original_invoice_id and "Payment ID:" not in (cn.notes or '')]
        payment_adjustments = [cn for cn in all_credits 
                             if "Payment ID:" in (cn.notes or '')]
        
        return {
            'total_credit_notes': total_count,
            'total_credit_amount': total_amount,
            'invoice_reversal_count': len(invoice_reversals),
            'invoice_reversal_amount': sum(abs(float(cn.total_amount)) for cn in invoice_reversals),
            'payment_adjustment_count': len(payment_adjustments),
            'payment_adjustment_amount': sum(abs(float(cn.total_amount)) for cn in payment_adjustments)
        }
        
    except Exception as e:
        logger.error(f"Error getting credit note summary: {str(e)}")
        raise