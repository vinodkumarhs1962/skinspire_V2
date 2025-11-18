# app/services/subledger_service.py

from decimal import Decimal
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Tuple

from sqlalchemy import func, and_, or_, text
from sqlalchemy.orm import Session

from app.models.transaction import ARSubledger, APSubledger, GLTransaction, InvoiceHeader
from app.models.master import Patient, Supplier, Branch
from app.services.database_service import get_db_session, get_entity_dict

logger = logging.getLogger(__name__)

def get_patient_ar_balance(
    hospital_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> Decimal:
    """
    Calculate current AR balance for a patient
    
    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        branch_id: Optional branch UUID to filter by branch
        as_of_date: Optional date to calculate balance as of
        session: Database session (optional)
        
    Returns:
        Current AR balance for the patient
    """
    if session is not None:
        return _get_patient_ar_balance(session, hospital_id, patient_id, branch_id, as_of_date)
    
    with get_db_session() as new_session:
        return _get_patient_ar_balance(new_session, hospital_id, patient_id, branch_id, as_of_date)

def _get_patient_ar_balance(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None
) -> Decimal:
    """Internal function to calculate AR balance within a session"""
    try:
        # Convert ALL UUIDs to UUID objects FIRST to ensure consistency
        hospital_id = uuid.UUID(str(hospital_id)) if not isinstance(hospital_id, uuid.UUID) else hospital_id
        patient_id = uuid.UUID(str(patient_id)) if not isinstance(patient_id, uuid.UUID) else patient_id
        if branch_id:
            branch_id = uuid.UUID(str(branch_id)) if not isinstance(branch_id, uuid.UUID) else branch_id

        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)

        # Build query with properly typed UUID parameters
        # Use .from_self() or create fresh queries to avoid identity map issues
        base_filter_args = {
            'hospital_id': hospital_id,
            'patient_id': patient_id
        }

        # Get latest entry with balance for this patient
        query = session.query(ARSubledger).filter(
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.patient_id == patient_id,
            ARSubledger.transaction_date <= as_of_date
        )

        if branch_id:
            query = query.filter(ARSubledger.branch_id == branch_id)

        # Order by transaction_date and entry_id (PK) to avoid comparison issues
        latest_entry = query.order_by(
            ARSubledger.transaction_date.desc(),
            ARSubledger.entry_id.desc()
        ).first()

        if latest_entry and latest_entry.current_balance is not None:
            # Detach from session to avoid identity map issues
            session.expunge(latest_entry)
            return latest_entry.current_balance

        # If no entry with balance, calculate from scratch using fresh query
        sum_query = session.query(
            func.sum(ARSubledger.debit_amount).label('debits'),
            func.sum(ARSubledger.credit_amount).label('credits')
        ).filter(
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.patient_id == patient_id,
            ARSubledger.transaction_date <= as_of_date
        )

        if branch_id:
            sum_query = sum_query.filter(ARSubledger.branch_id == branch_id)

        result = sum_query.first()
        debits = result.debits or Decimal('0')
        credits = result.credits or Decimal('0')

        return debits - credits

    except Exception as e:
        logger.error(f"Error calculating patient AR balance: {str(e)}", exc_info=True)
        raise

def get_line_item_ar_balance(
    hospital_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    line_item_id: Union[str, uuid.UUID],
    session: Optional[Session] = None
) -> Decimal:
    """
    Calculate AR balance for a specific invoice line item

    This function calculates the outstanding balance for a specific line item
    by summing debits and credits in AR entries that reference this line item.

    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        line_item_id: Invoice line item UUID
        session: Database session (optional)

    Returns:
        Outstanding AR balance for this line item (positive = amount owed)

    Example:
        Line item total: ₹5,900
        AR entries:
          - Debit ₹5,900 (invoice created)
          - Credit ₹500 (payment allocated)
        Balance: ₹5,400 (outstanding amount)
    """
    if session is not None:
        return _get_line_item_ar_balance(session, hospital_id, patient_id, line_item_id)

    with get_db_session() as new_session:
        return _get_line_item_ar_balance(new_session, hospital_id, patient_id, line_item_id)

def _get_line_item_ar_balance(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    line_item_id: Union[str, uuid.UUID]
) -> Decimal:
    """Internal function to calculate line item AR balance within a session"""
    try:
        # Convert UUIDs to UUID objects for consistency
        hospital_id = uuid.UUID(str(hospital_id)) if not isinstance(hospital_id, uuid.UUID) else hospital_id
        patient_id = uuid.UUID(str(patient_id)) if not isinstance(patient_id, uuid.UUID) else patient_id
        line_item_id = uuid.UUID(str(line_item_id)) if not isinstance(line_item_id, uuid.UUID) else line_item_id

        # Query all AR entries for this line item
        entries = session.query(ARSubledger).filter(
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.patient_id == patient_id,
            ARSubledger.reference_line_item_id == line_item_id
        ).all()

        # Calculate balance: debits increase AR, credits decrease AR
        total_debits = sum(e.debit_amount or Decimal('0') for e in entries)
        total_credits = sum(e.credit_amount or Decimal('0') for e in entries)
        balance = total_debits - total_credits

        logger.debug(f"Line item {line_item_id}: Debits=₹{total_debits}, Credits=₹{total_credits}, Balance=₹{balance}")

        return balance

    except Exception as e:
        logger.error(f"Error calculating line item AR balance: {str(e)}", exc_info=True)
        raise

def get_supplier_ap_balance(
    hospital_id: Union[str, uuid.UUID],
    supplier_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> Decimal:
    """
    Calculate current AP balance for a supplier
    
    Args:
        hospital_id: Hospital UUID
        supplier_id: Supplier UUID
        branch_id: Optional branch UUID to filter by branch
        as_of_date: Optional date to calculate balance as of
        session: Database session (optional)
        
    Returns:
        Current AP balance for the supplier
    """
    if session is not None:
        return _get_supplier_ap_balance(session, hospital_id, supplier_id, branch_id, as_of_date)
    
    with get_db_session() as new_session:
        return _get_supplier_ap_balance(new_session, hospital_id, supplier_id, branch_id, as_of_date)

def _get_supplier_ap_balance(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    supplier_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None
) -> Decimal:
    """Internal function to calculate AP balance within a session"""
    try:
        # Convert ALL UUIDs to UUID objects FIRST to ensure consistency
        hospital_id = uuid.UUID(str(hospital_id)) if not isinstance(hospital_id, uuid.UUID) else hospital_id
        supplier_id = uuid.UUID(str(supplier_id)) if not isinstance(supplier_id, uuid.UUID) else supplier_id
        if branch_id:
            branch_id = uuid.UUID(str(branch_id)) if not isinstance(branch_id, uuid.UUID) else branch_id

        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)

        # Build query with properly typed UUID parameters
        query = session.query(APSubledger).filter(
            APSubledger.hospital_id == hospital_id,
            APSubledger.supplier_id == supplier_id,
            APSubledger.transaction_date <= as_of_date
        )

        if branch_id:
            query = query.filter(APSubledger.branch_id == branch_id)

        # Order by transaction_date and entry_id (PK) to avoid comparison issues
        latest_entry = query.order_by(
            APSubledger.transaction_date.desc(),
            APSubledger.entry_id.desc()
        ).first()

        if latest_entry and latest_entry.current_balance is not None:
            # Detach from session to avoid identity map issues
            session.expunge(latest_entry)
            return latest_entry.current_balance

        # If no entry with balance, calculate from scratch using fresh query
        sum_query = session.query(
            func.sum(APSubledger.credit_amount).label('credits'),
            func.sum(APSubledger.debit_amount).label('debits')
        ).filter(
            APSubledger.hospital_id == hospital_id,
            APSubledger.supplier_id == supplier_id,
            APSubledger.transaction_date <= as_of_date
        )

        if branch_id:
            sum_query = sum_query.filter(APSubledger.branch_id == branch_id)

        result = sum_query.first()
        credits = result.credits or Decimal('0')
        debits = result.debits or Decimal('0')

        return credits - debits

    except Exception as e:
        logger.error(f"Error calculating supplier AP balance: {str(e)}", exc_info=True)
        raise

def create_ar_subledger_entry(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    entry_type: str,
    reference_id: Union[str, uuid.UUID],
    reference_type: str,
    reference_number: str,
    debit_amount: Decimal = Decimal('0'),
    credit_amount: Decimal = Decimal('0'),
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    reference_line_item_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None,
    item_type: Optional[str] = None,
    item_name: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create an AR subledger entry

    Args:
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        entry_type: Type of entry ('invoice', 'payment', 'adjustment', 'refund', 'advance', 'advance_adjustment')
        reference_id: Reference ID (invoice_id, payment_id, or advance_id)
        reference_type: Reference type ('invoice', 'payment', 'advance', or 'adjustment')
        reference_number: Reference number (invoice number, payment reference, etc.)
        debit_amount: Debit amount
        credit_amount: Credit amount
        transaction_date: Date of transaction
        gl_transaction_id: GL transaction ID
        reference_line_item_id: Invoice line item ID for payment allocation tracking (optional)
        current_user_id: User creating the entry
        session: Database session (optional)

    Returns:
        Created AR subledger entry as dictionary
    """
    if session is not None:
        return _create_ar_subledger_entry(
            session, hospital_id, branch_id, patient_id, entry_type, reference_id,
            reference_type, reference_number, debit_amount, credit_amount,
            transaction_date, gl_transaction_id, reference_line_item_id, current_user_id,
            item_type, item_name
        )

    with get_db_session() as new_session:
        result = _create_ar_subledger_entry(
            new_session, hospital_id, branch_id, patient_id, entry_type, reference_id,
            reference_type, reference_number, debit_amount, credit_amount,
            transaction_date, gl_transaction_id, reference_line_item_id, current_user_id,
            item_type, item_name
        )
        
        # Explicitly commit for this critical operation
        new_session.commit()
        
        return result

def _create_ar_subledger_entry(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    entry_type: str,
    reference_id: Union[str, uuid.UUID],
    reference_type: str,
    reference_number: str,
    debit_amount: Decimal = Decimal('0'),
    credit_amount: Decimal = Decimal('0'),
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    reference_line_item_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None,
    item_type: Optional[str] = None,
    item_name: Optional[str] = None
) -> Dict:
    """Internal function to create AR subledger entry within a session"""
    try:
        # Convert ALL UUIDs to UUID objects FIRST to ensure consistency
        hospital_id = uuid.UUID(str(hospital_id)) if not isinstance(hospital_id, uuid.UUID) else hospital_id
        branch_id = uuid.UUID(str(branch_id)) if not isinstance(branch_id, uuid.UUID) else branch_id
        patient_id = uuid.UUID(str(patient_id)) if not isinstance(patient_id, uuid.UUID) else patient_id
        reference_id = uuid.UUID(str(reference_id)) if not isinstance(reference_id, uuid.UUID) else reference_id
        if gl_transaction_id:
            gl_transaction_id = uuid.UUID(str(gl_transaction_id)) if not isinstance(gl_transaction_id, uuid.UUID) else gl_transaction_id
        if reference_line_item_id:
            reference_line_item_id = uuid.UUID(str(reference_line_item_id)) if not isinstance(reference_line_item_id, uuid.UUID) else reference_line_item_id

        if transaction_date is None:
            transaction_date = datetime.now(timezone.utc)

        # Calculate current balance using the SAME session (UUID fix ensures no sort errors)
        try:
            previous_balance = _get_patient_ar_balance(
                session, hospital_id, patient_id, branch_id, transaction_date
            )
        except Exception as e:
            logger.error(f"Error calculating AR balance: {str(e)}")
            # Use zero as previous balance to allow payment to proceed
            previous_balance = Decimal('0')
            logger.warning(f"Using zero as previous AR balance for patient {patient_id}")

        current_balance = previous_balance + (debit_amount - credit_amount)

        # If item details not provided, try to fetch from line item
        if reference_line_item_id and (not item_type or not item_name):
            from app.models.transaction import InvoiceLineItem
            line_item = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.line_item_id == reference_line_item_id
            ).first()
            if line_item:
                if not item_type:
                    item_type = line_item.item_type
                if not item_name:
                    item_name = line_item.item_name

        # Create subledger entry
        ar_entry = ARSubledger(
            hospital_id=hospital_id,
            branch_id=branch_id,
            patient_id=patient_id,
            entry_type=entry_type,
            reference_id=reference_id,
            reference_type=reference_type,
            reference_number=reference_number,
            reference_line_item_id=reference_line_item_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            transaction_date=transaction_date,
            gl_transaction_id=gl_transaction_id,
            current_balance=current_balance,
            item_type=item_type,
            item_name=item_name
        )

        # Audit fields (created_by, updated_by) set automatically by Event Listeners

        session.add(ar_entry)
        # Don't flush here - let parent transaction handle it to avoid UUID sort issues
        # session.flush()

        return get_entity_dict(ar_entry)

    except Exception as e:
        logger.error(f"Error creating AR subledger entry: {str(e)}", exc_info=True)
        # Don't rollback here - let the calling function handle transaction management
        raise

def create_ap_subledger_entry(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    supplier_id: Union[str, uuid.UUID],
    entry_type: str,
    reference_id: Union[str, uuid.UUID],
    reference_type: str,
    reference_number: str,
    debit_amount: Decimal = Decimal('0'),
    credit_amount: Decimal = Decimal('0'),
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create an AP subledger entry
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        supplier_id: Supplier UUID
        entry_type: Type of entry ('invoice', 'payment', 'adjustment', 'advance')
        reference_id: Reference ID (supplier_invoice_id, payment_id, or advance_id)
        reference_type: Reference type ('invoice', 'payment', 'advance', or 'adjustment')
        reference_number: Reference number (invoice number, payment reference, etc.)
        debit_amount: Debit amount
        credit_amount: Credit amount
        transaction_date: Date of transaction
        gl_transaction_id: GL transaction ID
        current_user_id: User creating the entry
        session: Database session (optional)
        
    Returns:
        Created AP subledger entry as dictionary
    """
    if session is not None:
        return _create_ap_subledger_entry(
            session, hospital_id, branch_id, supplier_id, entry_type, reference_id,
            reference_type, reference_number, debit_amount, credit_amount,
            transaction_date, gl_transaction_id, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_ap_subledger_entry(
            new_session, hospital_id, branch_id, supplier_id, entry_type, reference_id,
            reference_type, reference_number, debit_amount, credit_amount,
            transaction_date, gl_transaction_id, current_user_id
        )
        
        # Explicitly commit for this critical operation
        new_session.commit()
        
        return result

def _create_ap_subledger_entry(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    supplier_id: Union[str, uuid.UUID],
    entry_type: str,
    reference_id: Union[str, uuid.UUID],
    reference_type: str,
    reference_number: str,
    debit_amount: Decimal = Decimal('0'),
    credit_amount: Decimal = Decimal('0'),
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to create AP subledger entry within a session"""
    try:
        # Convert ALL UUIDs to UUID objects FIRST to ensure consistency
        hospital_id = uuid.UUID(str(hospital_id)) if not isinstance(hospital_id, uuid.UUID) else hospital_id
        branch_id = uuid.UUID(str(branch_id)) if not isinstance(branch_id, uuid.UUID) else branch_id
        supplier_id = uuid.UUID(str(supplier_id)) if not isinstance(supplier_id, uuid.UUID) else supplier_id
        reference_id = uuid.UUID(str(reference_id)) if not isinstance(reference_id, uuid.UUID) else reference_id
        if gl_transaction_id:
            gl_transaction_id = uuid.UUID(str(gl_transaction_id)) if not isinstance(gl_transaction_id, uuid.UUID) else gl_transaction_id

        if transaction_date is None:
            transaction_date = datetime.now(timezone.utc)

        # Calculate current balance using the SAME session (UUID fix ensures no sort errors)
        try:
            previous_balance = _get_supplier_ap_balance(
                session, hospital_id, supplier_id, branch_id, transaction_date
            )
        except Exception as e:
            logger.error(f"Error calculating AP balance: {str(e)}")
            # Use zero as previous balance to allow payment to proceed
            previous_balance = Decimal('0')
            logger.warning(f"Using zero as previous AP balance for supplier {supplier_id}")

        current_balance = previous_balance + (credit_amount - debit_amount)
        
        # Create subledger entry
        ap_entry = APSubledger(
            hospital_id=hospital_id,
            branch_id=branch_id,
            supplier_id=supplier_id,
            entry_type=entry_type,
            reference_id=reference_id,
            reference_type=reference_type,
            reference_number=reference_number,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            transaction_date=transaction_date,
            gl_transaction_id=gl_transaction_id,
            current_balance=current_balance
        )
        
        if current_user_id:
            ap_entry.created_by = current_user_id

        session.add(ap_entry)
        # Don't flush here - let parent transaction handle it to avoid UUID sort issues
        # session.flush()

        return get_entity_dict(ap_entry)

    except Exception as e:
        logger.error(f"Error creating AP subledger entry: {str(e)}", exc_info=True)
        # Don't rollback here - let the calling function handle transaction management
        raise

def create_advance_payment_ar_entry(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    advance_id: Union[str, uuid.UUID],
    amount: Decimal,
    reference_number: str,
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create an AR subledger entry for an advance payment
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        advance_id: Advance payment UUID
        amount: Advance amount
        reference_number: Advance payment reference
        transaction_date: Date of transaction
        gl_transaction_id: GL transaction ID
        current_user_id: User creating the entry
        session: Database session (optional)
        
    Returns:
        Created AR subledger entry as dictionary
    """
    if session is not None:
        return _create_advance_payment_ar_entry(
            session, hospital_id, branch_id, patient_id, advance_id, amount,
            reference_number, transaction_date, gl_transaction_id, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_advance_payment_ar_entry(
            new_session, hospital_id, branch_id, patient_id, advance_id, amount,
            reference_number, transaction_date, gl_transaction_id, current_user_id
        )
        
        # Explicitly commit for this critical operation
        new_session.commit()
        
        return result

def _create_advance_payment_ar_entry(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    advance_id: Union[str, uuid.UUID],
    amount: Decimal,
    reference_number: str,
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to create AR subledger entry for advance payment"""
    # For an advance payment in AR:
    # - Credit the AR account (reducing receivables) since payment received before invoice
    # - This will show as a negative balance or credit balance in AR
    
    return create_ar_subledger_entry(
        session=session,
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        entry_type='advance',
        reference_id=advance_id,
        reference_type='advance',
        reference_number=reference_number,
        debit_amount=Decimal('0'),
        credit_amount=amount,  # Credit AR for advance payment
        transaction_date=transaction_date,
        gl_transaction_id=gl_transaction_id,
        current_user_id=current_user_id
    )

def create_advance_adjustment_ar_entries(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    adjustment_id: Union[str, uuid.UUID],
    invoice_id: Union[str, uuid.UUID],
    amount: Decimal,
    invoice_number: str,
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Tuple[Dict, Dict]:
    """
    Create AR subledger entries for an advance payment adjustment
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        adjustment_id: Advance adjustment UUID
        invoice_id: Invoice UUID being paid with advance
        amount: Adjustment amount
        invoice_number: Invoice number being paid
        transaction_date: Date of transaction
        gl_transaction_id: GL transaction ID
        current_user_id: User creating the entry
        session: Database session (optional)
        
    Returns:
        Tuple of created AR subledger entries (adjustment entry, payment entry)
    """
    if session is not None:
        return _create_advance_adjustment_ar_entries(
            session, hospital_id, branch_id, patient_id, adjustment_id, invoice_id,
            amount, invoice_number, transaction_date, gl_transaction_id, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_advance_adjustment_ar_entries(
            new_session, hospital_id, branch_id, patient_id, adjustment_id, invoice_id,
            amount, invoice_number, transaction_date, gl_transaction_id, current_user_id
        )
        
        # Explicitly commit for this critical operation
        new_session.commit()
        
        return result

def _create_advance_adjustment_ar_entries(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    adjustment_id: Union[str, uuid.UUID],
    invoice_id: Union[str, uuid.UUID],
    amount: Decimal,
    invoice_number: str,
    transaction_date: Optional[datetime] = None,
    gl_transaction_id: Optional[Union[str, uuid.UUID]] = None,
    current_user_id: Optional[str] = None
) -> Tuple[Dict, Dict]:
    """Internal function to create AR subledger entries for advance adjustment"""
    # For an advance adjustment in AR:
    # - Debit AR to reduce the advance credit balance
    # - Credit AR separately in a payment entry to reduce the invoice receivable
    
    # This entry handles the advance reduction
    advance_adjustment = create_ar_subledger_entry(
        session=session,
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        entry_type='advance_adjustment',
        reference_id=adjustment_id,
        reference_type='adjustment',
        reference_number=f"Adj-{invoice_number}",
        debit_amount=amount,  # Debit AR to use the advance
        credit_amount=Decimal('0'),
        transaction_date=transaction_date,
        gl_transaction_id=gl_transaction_id,
        current_user_id=current_user_id
    )
    
    # Also record as a payment against the invoice
    payment_entry = create_ar_subledger_entry(
        session=session,
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        entry_type='payment',
        reference_id=invoice_id,
        reference_type='invoice',
        reference_number=f"Adv-{invoice_number}",
        debit_amount=Decimal('0'),
        credit_amount=amount,  # Credit AR to reduce invoice receivable
        transaction_date=transaction_date,
        gl_transaction_id=gl_transaction_id,
        current_user_id=current_user_id
    )
    
    return (advance_adjustment, payment_entry)

def get_ar_aging_by_branch(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Generate AR aging report by branch
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Optional branch UUID to filter by branch
        as_of_date: Optional date to calculate aging as of
        session: Database session (optional)
        
    Returns:
        Dictionary with aging report data by branch
    """
    if session is not None:
        return _get_ar_aging_by_branch(session, hospital_id, branch_id, as_of_date)
    
    with get_db_session() as new_session:
        return _get_ar_aging_by_branch(new_session, hospital_id, branch_id, as_of_date)

def _get_ar_aging_by_branch(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None
) -> Dict:
    """Internal function to generate AR aging report by branch"""
    try:
        # Convert string UUIDs to UUID objects if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if branch_id and isinstance(branch_id, str):
            branch_id = uuid.UUID(branch_id)
            
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)
            
        # Prepare base query filters
        filters = [
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.transaction_date <= as_of_date
        ]
        
        # Add branch filter if specified
        if branch_id:
            filters.append(ARSubledger.branch_id == branch_id)
        
        # Query to get latest balance by patient and branch
        subquery = session.query(
            ARSubledger.patient_id,
            ARSubledger.branch_id,
            func.max(ARSubledger.transaction_date).label('latest_date')
        ).filter(
            *filters
        ).group_by(
            ARSubledger.patient_id,
            ARSubledger.branch_id
        ).subquery()
        
        # Join with original table to get balances
        latest_entries = session.query(
            ARSubledger
        ).join(
            subquery,
            and_(
                ARSubledger.patient_id == subquery.c.patient_id,
                ARSubledger.branch_id == subquery.c.branch_id,
                ARSubledger.transaction_date == subquery.c.latest_date
            )
        ).filter(
            ARSubledger.current_balance > 0  # Only show patients with balance due
        ).all()
        
        # Organize by branch
        result = {}
        
        for entry in latest_entries:
            # Get branch name
            branch = session.query(Branch).filter_by(
                branch_id=entry.branch_id
            ).first()
            
            branch_name = branch.name if branch else f"Branch {entry.branch_id}"
            
            # Get patient details
            patient = session.query(Patient).filter_by(
                patient_id=entry.patient_id
            ).first()
            
            patient_name = patient.full_name if patient else f"Patient {entry.patient_id}"
            
            # Calculate days outstanding
            days_outstanding = (as_of_date - entry.transaction_date).days
            
            # Determine aging bucket
            if days_outstanding <= 30:
                aging_bucket = '0-30'
            elif days_outstanding <= 60:
                aging_bucket = '31-60'
            elif days_outstanding <= 90:
                aging_bucket = '61-90'
            else:
                aging_bucket = '90+'
            
            # Add to branch data
            if branch_name not in result:
                result[branch_name] = {
                    'branch_id': str(entry.branch_id),
                    'branch_name': branch_name,
                    'total_ar': Decimal('0'),
                    'aging_buckets': {
                        '0-30': Decimal('0'),
                        '31-60': Decimal('0'),
                        '61-90': Decimal('0'),
                        '90+': Decimal('0')
                    },
                    'patients': []
                }
            
            # Update branch totals
            result[branch_name]['total_ar'] += entry.current_balance
            result[branch_name]['aging_buckets'][aging_bucket] += entry.current_balance
            
            # Add patient details
            result[branch_name]['patients'].append({
                'patient_id': str(entry.patient_id),
                'patient_name': patient_name,
                'current_balance': float(entry.current_balance),
                'days_outstanding': days_outstanding,
                'aging_bucket': aging_bucket,
                'last_transaction_date': entry.transaction_date.isoformat() if entry.transaction_date else None
            })
        
        # Calculate summary totals for all branches
        summary = {
            'total_ar': sum(branch_data['total_ar'] for branch_data in result.values()),
            'aging_buckets': {
                '0-30': sum(branch_data['aging_buckets']['0-30'] for branch_data in result.values()),
                '31-60': sum(branch_data['aging_buckets']['31-60'] for branch_data in result.values()),
                '61-90': sum(branch_data['aging_buckets']['61-90'] for branch_data in result.values()),
                '90+': sum(branch_data['aging_buckets']['90+'] for branch_data in result.values())
            }
        }
        
        # Convert Decimal values to float for JSON serialization
        for branch_name, branch_data in result.items():
            branch_data['total_ar'] = float(branch_data['total_ar'])
            for bucket, amount in branch_data['aging_buckets'].items():
                branch_data['aging_buckets'][bucket] = float(amount)
        
        for bucket, amount in summary['aging_buckets'].items():
            summary['aging_buckets'][bucket] = float(amount)
        summary['total_ar'] = float(summary['total_ar'])
        
        return {
            'branches': result,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error generating AR aging report by branch: {str(e)}")
        raise

def get_ap_aging_by_branch(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Generate AP aging report by branch
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Optional branch UUID to filter by branch
        as_of_date: Optional date to calculate aging as of
        session: Database session (optional)
        
    Returns:
        Dictionary with aging report data by branch
    """
    if session is not None:
        return _get_ap_aging_by_branch(session, hospital_id, branch_id, as_of_date)
    
    with get_db_session() as new_session:
        return _get_ap_aging_by_branch(new_session, hospital_id, branch_id, as_of_date)

def _get_ap_aging_by_branch(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    as_of_date: Optional[datetime] = None
) -> Dict:
    """Internal function to generate AP aging report by branch"""
    try:
        # Convert string UUIDs to UUID objects if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if branch_id and isinstance(branch_id, str):
            branch_id = uuid.UUID(branch_id)
            
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc)
            
        # Prepare base query filters
        filters = [
            APSubledger.hospital_id == hospital_id,
            APSubledger.transaction_date <= as_of_date
        ]
        
        # Add branch filter if specified
        if branch_id:
            filters.append(APSubledger.branch_id == branch_id)
        
        # Query to get latest balance by supplier and branch
        subquery = session.query(
            APSubledger.supplier_id,
            APSubledger.branch_id,
            func.max(APSubledger.transaction_date).label('latest_date')
        ).filter(
            *filters
        ).group_by(
            APSubledger.supplier_id,
            APSubledger.branch_id
        ).subquery()
        
        # Join with original table to get balances
        latest_entries = session.query(
            APSubledger
        ).join(
            subquery,
            and_(
                APSubledger.supplier_id == subquery.c.supplier_id,
                APSubledger.branch_id == subquery.c.branch_id,
                APSubledger.transaction_date == subquery.c.latest_date
            )
        ).filter(
            APSubledger.current_balance > 0  # Only show suppliers with balance due
        ).all()
        
        # Organize by branch
        result = {}
        
        for entry in latest_entries:
            # Get branch name
            branch = session.query(Branch).filter_by(
                branch_id=entry.branch_id
            ).first()
            
            branch_name = branch.name if branch else f"Branch {entry.branch_id}"
            
            # Get supplier details
            supplier = session.query(Supplier).filter_by(
                supplier_id=entry.supplier_id
            ).first()
            
            supplier_name = supplier.supplier_name if supplier else f"Supplier {entry.supplier_id}"
            
            # Calculate days outstanding
            days_outstanding = (as_of_date - entry.transaction_date).days
            
            # Determine aging bucket
            if days_outstanding <= 30:
                aging_bucket = '0-30'
            elif days_outstanding <= 60:
                aging_bucket = '31-60'
            elif days_outstanding <= 90:
                aging_bucket = '61-90'
            else:
                aging_bucket = '90+'
            
            # Add to branch data
            if branch_name not in result:
                result[branch_name] = {
                    'branch_id': str(entry.branch_id),
                    'branch_name': branch_name,
                    'total_ap': Decimal('0'),
                    'aging_buckets': {
                        '0-30': Decimal('0'),
                        '31-60': Decimal('0'),
                        '61-90': Decimal('0'),
                        '90+': Decimal('0')
                    },
                    'suppliers': []
                }
            
            # Update branch totals
            result[branch_name]['total_ap'] += entry.current_balance
            result[branch_name]['aging_buckets'][aging_bucket] += entry.current_balance
            
            # Add supplier details
            result[branch_name]['suppliers'].append({
                'supplier_id': str(entry.supplier_id),
                'supplier_name': supplier_name,
                'current_balance': float(entry.current_balance),
                'days_outstanding': days_outstanding,
                'aging_bucket': aging_bucket,
                'last_transaction_date': entry.transaction_date.isoformat() if entry.transaction_date else None
            })
        
        # Calculate summary totals for all branches
        summary = {
            'total_ap': sum(branch_data['total_ap'] for branch_data in result.values()),
            'aging_buckets': {
                '0-30': sum(branch_data['aging_buckets']['0-30'] for branch_data in result.values()),
                '31-60': sum(branch_data['aging_buckets']['31-60'] for branch_data in result.values()),
                '61-90': sum(branch_data['aging_buckets']['61-90'] for branch_data in result.values()),
                '90+': sum(branch_data['aging_buckets']['90+'] for branch_data in result.values())
            }
        }
        
        # Convert Decimal values to float for JSON serialization
        for branch_name, branch_data in result.items():
            branch_data['total_ap'] = float(branch_data['total_ap'])
            for bucket, amount in branch_data['aging_buckets'].items():
                branch_data['aging_buckets'][bucket] = float(amount)
        
        for bucket, amount in summary['aging_buckets'].items():
            summary['aging_buckets'][bucket] = float(amount)
        summary['total_ap'] = float(summary['total_ap'])
        
        return {
            'branches': result,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error generating AP aging report by branch: {str(e)}")
        raise

def get_patient_advance_balances(
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get all patients with advance payment balances
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Optional branch UUID to filter by branch
        session: Database session (optional)
        
    Returns:
        List of patients with advance balances
    """
    if session is not None:
        return _get_patient_advance_balances(session, hospital_id, branch_id)
    
    with get_db_session() as new_session:
        return _get_patient_advance_balances(new_session, hospital_id, branch_id)

def _get_patient_advance_balances(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    branch_id: Optional[Union[str, uuid.UUID]] = None
) -> List[Dict]:
    """Internal function to get patients with advance balances"""
    try:
        # Convert string UUIDs to UUID objects if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if branch_id and isinstance(branch_id, str):
            branch_id = uuid.UUID(branch_id)
        
        # Prepare base query filters
        filters = [
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.current_balance < 0  # Negative balance indicates advance payment
        ]
        
        # Add branch filter if specified
        if branch_id:
            filters.append(ARSubledger.branch_id == branch_id)
        
        # Query to get latest balance by patient and branch
        subquery = session.query(
            ARSubledger.patient_id,
            ARSubledger.branch_id,
            func.max(ARSubledger.transaction_date).label('latest_date')
        ).filter(
            *filters
        ).group_by(
            ARSubledger.patient_id,
            ARSubledger.branch_id
        ).subquery()
        
        # Join with original table to get balances
        latest_entries = session.query(
            ARSubledger
        ).join(
            subquery,
            and_(
                ARSubledger.patient_id == subquery.c.patient_id,
                ARSubledger.branch_id == subquery.c.branch_id,
                ARSubledger.transaction_date == subquery.c.latest_date
            )
        ).all()
        
        # Prepare result
        results = []
        
        for entry in latest_entries:
            # Get branch name
            branch = session.query(Branch).filter_by(
                branch_id=entry.branch_id
            ).first()
            
            branch_name = branch.name if branch else f"Branch {entry.branch_id}"
            
            # Get patient details
            patient = session.query(Patient).filter_by(
                patient_id=entry.patient_id
            ).first()
            
            if not patient:
                continue
                
            # Add patient with advance balance
            results.append({
                'patient_id': str(entry.patient_id),
                'patient_name': patient.full_name,
                'branch_id': str(entry.branch_id),
                'branch_name': branch_name,
                'advance_balance': float(abs(entry.current_balance)),  # Convert negative balance to positive amount
                'last_transaction_date': entry.transaction_date.isoformat() if entry.transaction_date else None
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting patient advance balances: {str(e)}")
        raise

def get_invoice_for_subledger(
    hospital_id: Union[str, uuid.UUID],
    invoice_id: Union[str, uuid.UUID],
    session: Optional[Session] = None
) -> Dict:
    """
    Get invoice details necessary for subledger entry creation
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        session: Database session (optional)
        
    Returns:
        Dictionary with invoice details for subledger
    """
    if session is not None:
        return _get_invoice_for_subledger(session, hospital_id, invoice_id)
    
    with get_db_session() as new_session:
        return _get_invoice_for_subledger(new_session, hospital_id, invoice_id)

def _get_invoice_for_subledger(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    invoice_id: Union[str, uuid.UUID]
) -> Dict:
    """Internal function to get invoice details for subledger"""
    try:
        # Convert string UUIDs to UUID objects if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if isinstance(invoice_id, str):
            invoice_id = uuid.UUID(invoice_id)
        
        # Get invoice details
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Get GL transaction if available
        gl_transaction = session.query(GLTransaction).filter_by(
            invoice_header_id=invoice_id
        ).first()
        
        # Prepare result
        result = {
            'invoice_id': str(invoice.invoice_id),
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.invoice_date,
            'patient_id': str(invoice.patient_id),
            'branch_id': str(invoice.branch_id),
            'grand_total': float(invoice.grand_total),
            'gl_transaction_id': str(gl_transaction.transaction_id) if gl_transaction else None
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting invoice for subledger: {str(e)}")
        raise

def create_subledger_entries_for_existing_transactions(
    hospital_id: Union[str, uuid.UUID],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create subledger entries for existing transactions (invoices and payments)
    
    This function is useful for initializing the subledger system with historical data.
    
    Args:
        hospital_id: Hospital UUID
        from_date: Start date for transactions to process
        to_date: End date for transactions to process
        current_user_id: User creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary with counts of entries created
    """
    if session is not None:
        return _create_subledger_entries_for_existing_transactions(
            session, hospital_id, from_date, to_date, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_subledger_entries_for_existing_transactions(
            new_session, hospital_id, from_date, to_date, current_user_id
        )
        
        # Explicitly commit for this critical operation
        new_session.commit()
        
        return result

def _create_subledger_entries_for_existing_transactions(
    session: Session,
    hospital_id: Union[str, uuid.UUID],
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create subledger entries for existing transactions
    
    This is a one-time utility function to populate the subledger tables
    with historical data from existing invoices and payments.
    """
    try:
        # Convert string UUID to UUID object if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        # Set default date range if not provided
        if from_date is None:
            from_date = datetime(2000, 1, 1, tzinfo=timezone.utc)  # Start from a long time ago
        
        if to_date is None:
            to_date = datetime.now(timezone.utc)
        
        # Prepare counters
        counts = {
            'invoices_processed': 0,
            'payments_processed': 0,
            'advances_processed': 0,
            'ar_entries_created': 0,
            'ap_entries_created': 0,
            'errors': 0
        }
        
        # Process invoices
        invoices = session.query(InvoiceHeader).filter(
            InvoiceHeader.hospital_id == hospital_id,
            InvoiceHeader.invoice_date >= from_date,
            InvoiceHeader.invoice_date <= to_date
        ).order_by(InvoiceHeader.invoice_date).all()
        
        for invoice in invoices:
            try:
                # Skip cancelled invoices
                if getattr(invoice, 'is_cancelled', False):
                    continue
                
                # Get GL transaction if available
                gl_transaction = session.query(GLTransaction).filter_by(
                    invoice_header_id=invoice.invoice_id
                ).first()
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Create AR subledger entry
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    entry_type='invoice',
                    reference_id=invoice.invoice_id,
                    reference_type='invoice',
                    reference_number=invoice.invoice_number,
                    debit_amount=invoice.grand_total,
                    credit_amount=Decimal('0'),
                    transaction_date=invoice.invoice_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                counts['invoices_processed'] += 1
                counts['ar_entries_created'] += 1
                
            except Exception as e:
                logger.error(f"Error processing invoice {invoice.invoice_id}: {str(e)}")
                counts['errors'] += 1
        
        # Process payments
        from app.models.transaction import PaymentDetail
        
        payments = session.query(PaymentDetail).filter(
            PaymentDetail.hospital_id == hospital_id,
            PaymentDetail.payment_date >= from_date,
            PaymentDetail.payment_date <= to_date
        ).order_by(PaymentDetail.payment_date).all()
        
        for payment in payments:
            try:
                # Get the invoice
                invoice = session.query(InvoiceHeader).filter_by(
                    invoice_id=payment.invoice_id
                ).first()
                
                if not invoice:
                    logger.warning(f"Invoice not found for payment {payment.payment_id}")
                    continue
                
                # Skip payments for cancelled invoices
                if getattr(invoice, 'is_cancelled', False):
                    continue
                
                # Get GL transaction if available
                gl_transaction = session.query(GLTransaction).filter_by(
                    transaction_id=payment.gl_entry_id
                ).first() if payment.gl_entry_id else None
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Create AR subledger entry
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    entry_type='payment',
                    reference_id=payment.payment_id,
                    reference_type='payment',
                    reference_number=payment.reference_number or f"Payment-{payment.payment_id}",
                    debit_amount=Decimal('0'),
                    credit_amount=payment.total_amount,
                    transaction_date=payment.payment_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                counts['payments_processed'] += 1
                counts['ar_entries_created'] += 1
                
            except Exception as e:
                logger.error(f"Error processing payment {payment.payment_id}: {str(e)}")
                counts['errors'] += 1
        
        # Process advance payments
        from app.models.transaction import PatientAdvancePayment
        
        advances = session.query(PatientAdvancePayment).filter(
            PatientAdvancePayment.hospital_id == hospital_id,
            PatientAdvancePayment.payment_date >= from_date,
            PatientAdvancePayment.payment_date <= to_date,
            PatientAdvancePayment.is_active == True
        ).order_by(PatientAdvancePayment.payment_date).all()
        
        for advance in advances:
            try:
                # Get patient info to get branch_id
                patient = session.query(Patient).filter_by(
                    patient_id=advance.patient_id
                ).first()
                
                if not patient:
                    logger.warning(f"Patient not found for advance payment {advance.advance_id}")
                    continue
                
                # Use patient's branch_id or a default
                branch_id = getattr(patient, 'branch_id', None)
                
                # If patient doesn't have branch_id, use a default branch
                if not branch_id:
                    # Get any branch for this hospital
                    branch = session.query(Branch).filter_by(
                        hospital_id=hospital_id,
                        is_active=True
                    ).first()
                    
                    branch_id = branch.branch_id if branch else None
                
                if not branch_id:
                    logger.warning(f"No branch found for advance payment {advance.advance_id}")
                    continue
                
                # Get GL transaction if available
                gl_transaction = session.query(GLTransaction).filter_by(
                    transaction_id=advance.gl_entry_id
                ).first() if advance.gl_entry_id else None
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Create AR subledger entry for advance
                create_advance_payment_ar_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    patient_id=advance.patient_id,
                    advance_id=advance.advance_id,
                    amount=advance.amount,
                    reference_number=advance.reference_number or f"Advance-{advance.advance_id}",
                    transaction_date=advance.payment_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                counts['advances_processed'] += 1
                counts['ar_entries_created'] += 1
                
            except Exception as e:
                logger.error(f"Error processing advance payment {advance.advance_id}: {str(e)}")
                counts['errors'] += 1
        
        # Process advance adjustments (if needed)
        # This would be similar to the above, but for AdvanceAdjustment records
        
        # Return counts
        return counts
        
    except Exception as e:
        logger.error(f"Error creating subledger entries for existing transactions: {str(e)}")
        session.rollback()
        raise