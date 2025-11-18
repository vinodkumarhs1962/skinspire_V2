# app/services/gl_service.py

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal
import logging

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.master import Patient, ChartOfAccounts, Supplier
from app.models.transaction import (
    InvoiceHeader, InvoiceLineItem, PaymentDetail,
    SupplierInvoice, SupplierInvoiceLine, SupplierPayment,
    GLTransaction, GLEntry, GSTLedger, PatientAdvancePayment,
    PatientCreditNote, ARSubledger
)
from app.services.database_service import get_db_session, get_entity_dict

logger = logging.getLogger(__name__)

def create_invoice_gl_entries(
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a customer invoice
    
    Args:
        invoice_id: Invoice UUID
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_invoice_gl_entries(session, invoice_id, current_user_id)
    
    with get_db_session() as new_session:
        return _create_invoice_gl_entries(new_session, invoice_id, current_user_id)

def _create_invoice_gl_entries(
    session: Session,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for a customer invoice within a session
    """
    try:
        # Get the invoice with line items
        invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        line_items = session.query(InvoiceLineItem).filter_by(invoice_id=invoice_id).all()
        
        if not line_items:
            raise ValueError(f"No line items found for invoice ID {invoice_id}")
        
        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_invoice(session, invoice)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=invoice.invoice_date,
            transaction_type="SALES_INVOICE",
            reference_id=str(invoice.invoice_id),
            description=f"Invoice {invoice.invoice_number}",
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_debit=invoice.grand_total,
            total_credit=invoice.grand_total
        )
        
        if current_user_id:
            gl_transaction.created_by = current_user_id
            
        session.add(gl_transaction)
        session.flush()  # To get the transaction_id
        
        # Create entries for the transaction
        entries = []
        
        # 1. Accounts Receivable debit entry (DR A/R, CR Revenue)
        ar_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['accounts_receivable'],
            debit_amount=invoice.grand_total,
            credit_amount=Decimal('0'),
            entry_date=invoice.invoice_date,
            description=f"Invoice {invoice.invoice_number} - Accounts Receivable"
        )
        
        if current_user_id:
            ar_entry.created_by = current_user_id
            
        session.add(ar_entry)
        entries.append(ar_entry)
        
        # 2. Revenue entries by type - grouped by GL account
        revenue_by_account = {}
        
        for item in line_items:
            # Determine the revenue account based on item type
            revenue_account_id = None
            
            if item.item_type == 'Service':
                revenue_account_id = accounts['service_revenue']
            elif item.item_type == 'Package':
                revenue_account_id = accounts['package_revenue']
            elif item.item_type == 'Medicine':
                revenue_account_id = accounts['medicine_revenue']
            else:
                revenue_account_id = accounts['general_revenue']
            
            # Add the taxable amount to the account total
            if revenue_account_id not in revenue_by_account:
                revenue_by_account[revenue_account_id] = Decimal('0')
                
            revenue_by_account[revenue_account_id] += item.taxable_amount
        
        # Create revenue entries
        for account_id, amount in revenue_by_account.items():
            revenue_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=account_id,
                debit_amount=Decimal('0'),
                credit_amount=amount,
                entry_date=invoice.invoice_date,
                description=f"Invoice {invoice.invoice_number} - Revenue"
            )
            
            if current_user_id:
                revenue_entry.created_by = current_user_id
                
            session.add(revenue_entry)
            entries.append(revenue_entry)
        
        # 3. Tax liability entries
        if invoice.is_gst_invoice:
            # Calculate totals
            cgst_total = invoice.total_cgst_amount
            sgst_total = invoice.total_sgst_amount
            igst_total = invoice.total_igst_amount
            
            # CGST liability
            if cgst_total > 0:
                cgst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['cgst_output'],
                    debit_amount=Decimal('0'),
                    credit_amount=cgst_total,
                    entry_date=invoice.invoice_date,
                    description=f"Invoice {invoice.invoice_number} - CGST Output"
                )
                
                if current_user_id:
                    cgst_entry.created_by = current_user_id
                    
                session.add(cgst_entry)
                entries.append(cgst_entry)
            
            # SGST liability
            if sgst_total > 0:
                sgst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['sgst_output'],
                    debit_amount=Decimal('0'),
                    credit_amount=sgst_total,
                    entry_date=invoice.invoice_date,
                    description=f"Invoice {invoice.invoice_number} - SGST Output"
                )
                
                if current_user_id:
                    sgst_entry.created_by = current_user_id
                    
                session.add(sgst_entry)
                entries.append(sgst_entry)
            
            # IGST liability
            if igst_total > 0:
                igst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['igst_output'],
                    debit_amount=Decimal('0'),
                    credit_amount=igst_total,
                    entry_date=invoice.invoice_date,
                    description=f"Invoice {invoice.invoice_number} - IGST Output"
                )
                
                if current_user_id:
                    igst_entry.created_by = current_user_id
                    
                session.add(igst_entry)
                entries.append(igst_entry)
                
            # Create GST Ledger entry
            gst_ledger_entry = GSTLedger(
                hospital_id=invoice.hospital_id,
                transaction_date=invoice.invoice_date,
                transaction_type="SALES",
                transaction_reference=invoice.invoice_number,
                cgst_output=cgst_total,
                sgst_output=sgst_total,
                igst_output=igst_total,
                gl_reference=gl_transaction.transaction_id,
                entry_month=invoice.invoice_date.month,
                entry_year=invoice.invoice_date.year
            )
            
            if current_user_id:
                gst_ledger_entry.created_by = current_user_id
                
            session.add(gst_ledger_entry)
            
        session.flush()
        
        # Return the created transaction
        return get_entity_dict(gl_transaction)
        
    except Exception as e:
        logger.error(f"Error creating invoice GL entries: {str(e)}")
        session.rollback()
        raise

def _get_gl_accounts_for_invoice(session: Session, invoice: InvoiceHeader) -> Dict:
    """
    Get the GL accounts needed for an invoice
    
    Args:
        session: Database session
        invoice: Invoice header object
        
    Returns:
        Dictionary of account IDs by purpose
    """
    hospital_id = invoice.hospital_id
    accounts = {}
    
    # Get the Accounts Receivable account
    ar_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Accounts Receivable%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not ar_account:
        raise ValueError("Accounts Receivable GL account not found")
        
    accounts['accounts_receivable'] = ar_account.account_id
    
    # Get revenue accounts by type
    # Service Revenue
    service_revenue = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Service Revenue%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not service_revenue:
        raise ValueError("Service Revenue GL account not found")
        
    accounts['service_revenue'] = service_revenue.account_id
    
    # Package Revenue
    package_revenue = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Package Revenue%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not package_revenue:
        # Fall back to service revenue
        accounts['package_revenue'] = service_revenue.account_id
    else:
        accounts['package_revenue'] = package_revenue.account_id
    
    # Medicine Revenue
    medicine_revenue = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Medicine Revenue%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not medicine_revenue:
        raise ValueError("Medicine Revenue GL account not found")
        
    accounts['medicine_revenue'] = medicine_revenue.account_id
    
    # General Revenue (fallback)
    general_revenue = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%General Revenue%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not general_revenue:
        # Fall back to service revenue
        accounts['general_revenue'] = service_revenue.account_id
    else:
        accounts['general_revenue'] = general_revenue.account_id
    
    # GST accounts (if applicable)
    if invoice.is_gst_invoice:
        # CGST Output
        cgst_output = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%CGST Output%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not cgst_output:
            raise ValueError("CGST Output GL account not found")
            
        accounts['cgst_output'] = cgst_output.account_id
        
        # SGST Output
        sgst_output = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%SGST Output%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not sgst_output:
            raise ValueError("SGST Output GL account not found")
            
        accounts['sgst_output'] = sgst_output.account_id
        
        # IGST Output
        igst_output = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%IGST Output%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not igst_output:
            raise ValueError("IGST Output GL account not found")
            
        accounts['igst_output'] = igst_output.account_id
    
    return accounts

def get_gl_transaction_by_id(
    transaction_id: uuid.UUID,
    include_entries: bool = True,
    hospital_id: Optional[uuid.UUID] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Get a GL transaction by ID with its entries
    
    Args:
        transaction_id: GL Transaction UUID
        include_entries: Whether to include GL entries
        hospital_id: Hospital ID for multi-tenant security
        session: Database session (optional)
        
    Returns:
        Dictionary containing GL transaction details
    """
    if session is not None:
        return _get_gl_transaction_by_id(session, transaction_id, include_entries, hospital_id)
    
    with get_db_session() as new_session:
        return _get_gl_transaction_by_id(new_session, transaction_id, include_entries, hospital_id)

def _get_gl_transaction_by_id(
    session: Session,
    transaction_id: uuid.UUID,
    include_entries: bool = True,
    hospital_id: Optional[uuid.UUID] = None
) -> Dict:
    """
    Internal function to get a GL transaction by ID with its entries within a session
    """
    try:
        # Get the transaction
        query = session.query(GLTransaction).filter_by(transaction_id=transaction_id)
        
        # Apply hospital_id filter if provided (for multi-tenant security)
        if hospital_id:
            query = query.filter_by(hospital_id=hospital_id)
            
        transaction = query.first()
        
        if not transaction:
            raise ValueError(f"GL transaction with ID {transaction_id} not found")
            
        # Convert to dictionary
        result = get_entity_dict(transaction)
        
        # Include entries if requested
        if include_entries:
            entries = session.query(GLEntry).filter_by(
                transaction_id=transaction_id
            ).all()
            
            entry_dicts = [get_entity_dict(entry) for entry in entries]
            
            # Add account names to entries
            for entry_dict in entry_dicts:
                account = session.query(ChartOfAccounts).filter_by(
                    account_id=entry_dict['account_id']
                ).first()
                
                if account:
                    entry_dict['account_name'] = account.account_name
                    entry_dict['account_number'] = account.gl_account_no
            
            result['entries'] = entry_dicts
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting GL transaction: {str(e)}")
        raise

def search_gl_transactions(
    hospital_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    page: int = 1,
    per_page: int = 20,
    include_entries: bool = False,
    session: Optional[Session] = None
) -> Dict:
    """
    Search GL transactions with filtering and pagination
    
    Args:
        hospital_id: Hospital ID for multi-tenant security
        start_date: Filter transactions on or after this date
        end_date: Filter transactions on or before this date
        transaction_type: Filter by transaction type
        reference_id: Filter by reference ID
        account_id: Filter by GL account ID (will search entries)
        min_amount: Filter by minimum transaction amount
        max_amount: Filter by maximum transaction amount
        page: Page number for pagination
        per_page: Number of items per page
        include_entries: Whether to include GL entries in results
        session: Database session (optional)
        
    Returns:
        Dictionary containing transaction list, pagination info
    """
    if session is not None:
        return _search_gl_transactions(
            session, hospital_id, start_date, end_date, transaction_type,
            reference_id, account_id, min_amount, max_amount, page, per_page, include_entries
        )
    
    with get_db_session() as new_session:
        return _search_gl_transactions(
            new_session, hospital_id, start_date, end_date, transaction_type,
            reference_id, account_id, min_amount, max_amount, page, per_page, include_entries
        )

def _search_gl_transactions(
    session: Session,
    hospital_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_type: Optional[str] = None,
    reference_id: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    page: int = 1,
    per_page: int = 20,
    include_entries: bool = False
) -> Dict:
    """
    Internal function to search GL transactions within a session
    """
    try:
        # Base query
        query = session.query(GLTransaction).filter_by(hospital_id=hospital_id)
        
        # Apply filters
        if start_date:
            query = query.filter(GLTransaction.transaction_date >= start_date)
            
        if end_date:
            query = query.filter(GLTransaction.transaction_date <= end_date)
            
        if transaction_type:
            query = query.filter(GLTransaction.transaction_type == transaction_type)
            
        if reference_id:
            query = query.filter(GLTransaction.reference_id.like(f"%{reference_id}%"))
            
        if min_amount:
            query = query.filter(GLTransaction.total_debit >= min_amount)
            
        if max_amount:
            query = query.filter(GLTransaction.total_debit <= max_amount)
            
        # If account_id is specified, we need to filter by entries
        if account_id:
            entry_subquery = session.query(GLEntry.transaction_id).filter_by(
                account_id=account_id
            ).subquery()
            
            query = query.filter(GLTransaction.transaction_id.in_(entry_subquery))
            
        # Count total for pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(desc(GLTransaction.transaction_date))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        transactions = query.all()
        
        # Convert to dictionaries
        results = []
        for transaction in transactions:
            transaction_dict = get_entity_dict(transaction)
            
            # Include entries if requested
            if include_entries:
                entries = session.query(GLEntry).filter_by(
                    transaction_id=transaction.transaction_id
                ).all()
                
                entry_dicts = [get_entity_dict(entry) for entry in entries]
                
                # Add account names to entries
                for entry_dict in entry_dicts:
                    account = session.query(ChartOfAccounts).filter_by(
                        account_id=entry_dict['account_id']
                    ).first()
                    
                    if account:
                        entry_dict['account_name'] = account.account_name
                        entry_dict['account_number'] = account.gl_account_no
                
                transaction_dict['entries'] = entry_dicts
                
            results.append(transaction_dict)
            
        # Prepare pagination info
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page
        }
        
        return {
            'transactions': results,
            'pagination': pagination
        }
        
    except Exception as e:
        logger.error(f"Error searching GL transactions: {str(e)}")
        raise

def create_payment_gl_entries(
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a customer payment
    
    Args:
        payment_id: Payment UUID
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_payment_gl_entries(session, payment_id, current_user_id)
    
    with get_db_session() as new_session:
        return _create_payment_gl_entries(new_session, payment_id, current_user_id)

def _create_payment_gl_entries(
    session: Session,
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for a customer payment within a session
    """
    try:
        # Get the payment record
        payment = session.query(PaymentDetail).filter_by(payment_id=payment_id).first()
        
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
        
        # Get the related invoice
        invoice = session.query(InvoiceHeader).filter_by(invoice_id=payment.invoice_id).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {payment.invoice_id} not found")
        
        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_payment(session, payment)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=payment.hospital_id,
            transaction_date=payment.payment_date,
            transaction_type="PAYMENT_RECEIPT",
            reference_id=str(payment.payment_id),
            description=f"Payment for Invoice {invoice.invoice_number}",
            currency_code=payment.currency_code,
            exchange_rate=payment.exchange_rate,
            total_debit=payment.total_amount,
            total_credit=payment.total_amount
        )
        
        if current_user_id:
            gl_transaction.created_by = current_user_id
            
        session.add(gl_transaction)
        session.flush()  # To get the transaction_id
        
        # Create entries for the transaction
        entries = []
        
        # 1. Accounts Receivable credit entry (CR A/R)
        ar_entry = GLEntry(
            hospital_id=payment.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['accounts_receivable'],
            debit_amount=Decimal('0'),
            credit_amount=payment.total_amount,
            entry_date=payment.payment_date,
            description=f"Payment Receipt - Invoice {invoice.invoice_number}"
        )
        
        if current_user_id:
            ar_entry.created_by = current_user_id
            
        session.add(ar_entry)
        entries.append(ar_entry)
        
        # 2. Payment method debit entries
        # Cash
        if payment.cash_amount > 0:
            cash_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=payment.cash_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Cash Receipt - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                cash_entry.created_by = current_user_id
                
            session.add(cash_entry)
            entries.append(cash_entry)
        
        # Credit Card
        if payment.credit_card_amount > 0:
            cc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['credit_card'],
                debit_amount=payment.credit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Credit Card Receipt - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                cc_entry.created_by = current_user_id
                
            session.add(cc_entry)
            entries.append(cc_entry)
        
        # Debit Card
        if payment.debit_card_amount > 0:
            dc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['debit_card'],
                debit_amount=payment.debit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Debit Card Receipt - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                dc_entry.created_by = current_user_id
                
            session.add(dc_entry)
            entries.append(dc_entry)
        
        # UPI
        if payment.upi_amount > 0:
            upi_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['upi'],
                debit_amount=payment.upi_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"UPI Receipt - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                upi_entry.created_by = current_user_id
                
            session.add(upi_entry)
            entries.append(upi_entry)
            
        session.flush()
        
        # Update payment record with GL reference
        payment.gl_entry_id = gl_transaction.transaction_id
        
        # Return the created transaction
        return get_entity_dict(gl_transaction)
        
    except Exception as e:
        logger.error(f"Error creating payment GL entries: {str(e)}")
        session.rollback()
        raise

def _get_gl_accounts_for_payment(session: Session, payment: PaymentDetail) -> Dict:
    """
    Get the GL accounts needed for a payment
    
    Args:
        session: Database session
        payment: Payment detail object
        
    Returns:
        Dictionary of account IDs by purpose
    """
    hospital_id = payment.hospital_id
    accounts = {}
    
    # Get the Accounts Receivable account
    ar_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Accounts Receivable%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not ar_account:
        raise ValueError("Accounts Receivable GL account not found")
        
    accounts['accounts_receivable'] = ar_account.account_id
    
    # Cash account
    cash_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Cash%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not cash_account:
        raise ValueError("Cash GL account not found")
        
    accounts['cash'] = cash_account.account_id
    
    # Credit Card account
    cc_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Credit Card%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not cc_account:
        raise ValueError("Credit Card GL account not found")
        
    accounts['credit_card'] = cc_account.account_id
    
    # Debit Card account
    dc_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Debit Card%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not dc_account:
        # Fall back to credit card account
        accounts['debit_card'] = cc_account.account_id
    else:
        accounts['debit_card'] = dc_account.account_id
    
    # UPI account
    upi_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%UPI%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not upi_account:
        # Fall back to bank account
        bank_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%Bank%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not bank_account:
            raise ValueError("Bank GL account not found for UPI fallback")
            
        accounts['upi'] = bank_account.account_id
    else:
        accounts['upi'] = upi_account.account_id

    return accounts


def create_multi_invoice_payment_gl_entries(
    payment_id: uuid.UUID,
    invoice_count: int,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create GL entries for multi-invoice patient payment

    Args:
        payment_id: Payment UUID
        invoice_count: Number of invoices paid
        current_user_id: ID of user creating entries
        session: Database session (optional)

    Returns:
        Dict with success status and transaction_id
    """
    if session:
        return _create_multi_invoice_payment_gl_entries(session, payment_id, invoice_count, current_user_id)

    with get_db_session() as new_session:
        return _create_multi_invoice_payment_gl_entries(new_session, payment_id, invoice_count, current_user_id)


def _create_multi_invoice_payment_gl_entries(
    session: Session,
    payment_id: uuid.UUID,
    invoice_count: int,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create GL entries for multi-invoice payment

    GL Posting Logic:
    - Debit: Cash/Credit Card/Debit Card/UPI (based on payment methods)
    - Credit: Accounts Receivable (total payment amount)
    """
    try:
        # Get the payment record
        payment = session.query(PaymentDetail).filter_by(payment_id=payment_id).first()

        if not payment:
            return {'success': False, 'error': f'Payment {payment_id} not found'}

        # Get GL accounts
        accounts = _get_gl_accounts_for_payment(session, payment)

        # Create GL transaction
        gl_transaction = GLTransaction(
            hospital_id=payment.hospital_id,
            transaction_date=payment.payment_date,
            transaction_type="PAYMENT_RECEIPT",
            reference_id=str(payment.payment_id),
            description=f"Multi-Invoice Payment ({invoice_count} invoices)",
            currency_code=payment.currency_code or 'INR',
            exchange_rate=payment.exchange_rate or Decimal('1.0'),
            total_debit=payment.total_amount,
            total_credit=payment.total_amount
        )

        if current_user_id:
            gl_transaction.created_by = current_user_id

        session.add(gl_transaction)
        session.flush()  # Get transaction_id

        # Create GL entries
        entries = []

        # 1. CREDIT: Accounts Receivable (total payment reduces A/R)
        ar_entry = GLEntry(
            hospital_id=payment.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['accounts_receivable'],
            debit_amount=Decimal('0'),
            credit_amount=payment.total_amount,
            entry_date=payment.payment_date,
            description=f"Multi-Invoice Payment - {invoice_count} invoices"
        )

        if current_user_id:
            ar_entry.created_by = current_user_id

        session.add(ar_entry)
        entries.append(ar_entry)

        # 2. DEBIT: Payment method accounts (cash, cards, UPI)
        if payment.cash_amount and payment.cash_amount > 0:
            cash_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=payment.cash_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Cash Receipt - Multi-Invoice Payment"
            )

            if current_user_id:
                cash_entry.created_by = current_user_id

            session.add(cash_entry)
            entries.append(cash_entry)

        if payment.credit_card_amount and payment.credit_card_amount > 0:
            cc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['credit_card'],
                debit_amount=payment.credit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Credit Card Receipt - Multi-Invoice Payment"
            )

            if current_user_id:
                cc_entry.created_by = current_user_id

            session.add(cc_entry)
            entries.append(cc_entry)

        if payment.debit_card_amount and payment.debit_card_amount > 0:
            dc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['debit_card'],
                debit_amount=payment.debit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Debit Card Receipt - Multi-Invoice Payment"
            )

            if current_user_id:
                dc_entry.created_by = current_user_id

            session.add(dc_entry)
            entries.append(dc_entry)

        if payment.upi_amount and payment.upi_amount > 0:
            upi_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['upi'],
                debit_amount=payment.upi_amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"UPI Receipt - Multi-Invoice Payment"
            )

            if current_user_id:
                upi_entry.created_by = current_user_id

            session.add(upi_entry)
            entries.append(upi_entry)

        session.flush()

        return {
            'success': True,
            'transaction_id': gl_transaction.transaction_id,
            'entries_count': len(entries),
            'total_amount': float(payment.total_amount)
        }

    except Exception as e:
        logger.error(f"Error creating multi-invoice payment GL entries: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def create_supplier_invoice_gl_entries(
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a supplier invoice
    
    Args:
        invoice_id: Supplier Invoice UUID
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_supplier_invoice_gl_entries(session, invoice_id, current_user_id)
    
    with get_db_session() as new_session:
        return _create_supplier_invoice_gl_entries(new_session, invoice_id, current_user_id)

def _create_supplier_invoice_gl_entries(
    session: Session,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for a supplier invoice within a session
    """
    try:
        # Get the supplier invoice with line items
        invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
        
        if not invoice:
            raise ValueError(f"Supplier invoice with ID {invoice_id} not found")
        
        line_items = session.query(SupplierInvoiceLine).filter_by(invoice_id=invoice_id).all()
        
        if not line_items:
            raise ValueError(f"No line items found for supplier invoice ID {invoice_id}")
        
        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_supplier_invoice(session, invoice)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=invoice.invoice_date,
            transaction_type="PURCHASE_INVOICE",
            reference_id=str(invoice.invoice_id),
            description=f"Supplier Invoice {invoice.supplier_invoice_number}",
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_debit=invoice.total_amount,
            total_credit=invoice.total_amount
        )
        
        if current_user_id:
            gl_transaction.created_by = current_user_id
            
        session.add(gl_transaction)
        session.flush()  # To get the transaction_id
        
        # Create entries for the transaction
        entries = []
        
        # 1. Accounts Payable credit entry (CR A/P, DR Purchase)
        ap_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['accounts_payable'],
            debit_amount=Decimal('0'),
            credit_amount=invoice.total_amount,
            entry_date=invoice.invoice_date,
            description=f"Supplier Invoice {invoice.supplier_invoice_number} - Accounts Payable"
        )
        
        if current_user_id:
            ap_entry.created_by = current_user_id
            
        session.add(ap_entry)
        entries.append(ap_entry)
        
        # 2. Purchase entries by type
        # Separate purchase amount and tax
        purchase_amount = invoice.total_amount - invoice.total_gst_amount
        
        purchase_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['purchase'],
            debit_amount=purchase_amount,
            credit_amount=Decimal('0'),
            entry_date=invoice.invoice_date,
            description=f"Supplier Invoice {invoice.supplier_invoice_number} - Purchase"
        )
        
        if current_user_id:
            purchase_entry.created_by = current_user_id
            
        session.add(purchase_entry)
        entries.append(purchase_entry)
        
        # 3. Input tax entries
        if invoice.itc_eligible:
            # Calculate totals
            cgst_total = invoice.cgst_amount
            sgst_total = invoice.sgst_amount
            igst_total = invoice.igst_amount
            
            # CGST input credit
            if cgst_total > 0:
                cgst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['cgst_input'],
                    debit_amount=cgst_total,
                    credit_amount=Decimal('0'),
                    entry_date=invoice.invoice_date,
                    description=f"Supplier Invoice {invoice.supplier_invoice_number} - CGST Input"
                )
                
                if current_user_id:
                    cgst_entry.created_by = current_user_id
                    
                session.add(cgst_entry)
                entries.append(cgst_entry)
            
            # SGST input credit
            if sgst_total > 0:
                sgst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['sgst_input'],
                    debit_amount=sgst_total,
                    credit_amount=Decimal('0'),
                    entry_date=invoice.invoice_date,
                    description=f"Supplier Invoice {invoice.supplier_invoice_number} - SGST Input"
                )
                
                if current_user_id:
                    sgst_entry.created_by = current_user_id
                    
                session.add(sgst_entry)
                entries.append(sgst_entry)
            
            # IGST input credit
            if igst_total > 0:
                igst_entry = GLEntry(
                    hospital_id=invoice.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['igst_input'],
                    debit_amount=igst_total,
                    credit_amount=Decimal('0'),
                    entry_date=invoice.invoice_date,
                    description=f"Supplier Invoice {invoice.supplier_invoice_number} - IGST Input"
                )
                
                if current_user_id:
                    igst_entry.created_by = current_user_id
                    
                session.add(igst_entry)
                entries.append(igst_entry)
                
            # Create GST Ledger entry
            gst_ledger_entry = GSTLedger(
                hospital_id=invoice.hospital_id,
                transaction_date=invoice.invoice_date,
                transaction_type="PURCHASE",
                transaction_reference=invoice.supplier_invoice_number,
                cgst_input=cgst_total,
                sgst_input=sgst_total,
                igst_input=igst_total,
                itc_claimed=(True if invoice.itc_eligible else False),
                gl_reference=gl_transaction.transaction_id,
                entry_month=invoice.invoice_date.month,
                entry_year=invoice.invoice_date.year
            )
            
            if current_user_id:
                gst_ledger_entry.created_by = current_user_id
                
            session.add(gst_ledger_entry)
            
        session.flush()
        
        # Return the created transaction
        return get_entity_dict(gl_transaction)
        
    except Exception as e:
        logger.error(f"Error creating supplier invoice GL entries: {str(e)}")
        session.rollback()
        raise

def _get_gl_accounts_for_supplier_invoice(session: Session, invoice: SupplierInvoice) -> Dict:
    """
    Get the GL accounts needed for a supplier invoice
    
    Args:
        session: Database session
        invoice: Supplier invoice object
        
    Returns:
        Dictionary of account IDs by purpose
    """
    hospital_id = invoice.hospital_id
    accounts = {}
    
    # Get the Accounts Payable account
    ap_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Accounts Payable%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not ap_account:
        raise ValueError("Accounts Payable GL account not found")
        
    accounts['accounts_payable'] = ap_account.account_id
    
    # Get purchase account
    purchase_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Purchase%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not purchase_account:
        raise ValueError("Purchase GL account not found")
        
    accounts['purchase'] = purchase_account.account_id
    
    # GST accounts
    # CGST Input
    cgst_input = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%CGST Input%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not cgst_input:
        raise ValueError("CGST Input GL account not found")
        
    accounts['cgst_input'] = cgst_input.account_id
    
    # SGST Input
    sgst_input = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%SGST Input%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not sgst_input:
        raise ValueError("SGST Input GL account not found")
        
    accounts['sgst_input'] = sgst_input.account_id
    
    # IGST Input
    igst_input = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%IGST Input%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not igst_input:
        raise ValueError("IGST Input GL account not found")
        
    accounts['igst_input'] = igst_input.account_id
    
    return accounts

def create_supplier_payment_gl_entries(
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a payment to a supplier
    
    Args:
        payment_id: Supplier Payment UUID
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_supplier_payment_gl_entries(session, payment_id, current_user_id)
    
    with get_db_session() as new_session:
        return _create_supplier_payment_gl_entries(new_session, payment_id, current_user_id)

def _create_supplier_payment_gl_entries(
    session: Session,
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for a supplier payment within a session
    """
    try:
        # Get the payment record
        payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()

        if not payment:
            raise ValueError(f"Supplier payment with ID {payment_id} not found")

        # Get the supplier invoice if available
        invoice = None
        if payment.invoice_id:
            invoice = session.query(SupplierInvoice).filter_by(invoice_id=payment.invoice_id).first()

        # Get the supplier
        supplier = None
        if payment.supplier_id:
            supplier = session.query(Supplier).filter_by(supplier_id=payment.supplier_id).first()

        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_supplier_payment(session, payment)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=payment.hospital_id,
            transaction_date=payment.payment_date,
            transaction_type="SUPPLIER_PAYMENT",
            reference_id=str(payment.payment_id),
            description=f"Payment to supplier {supplier.supplier_name if supplier else ''} {invoice.supplier_invoice_number if invoice else ''}",
            currency_code=payment.currency_code,
            exchange_rate=payment.exchange_rate,
            total_debit=payment.amount,
            total_credit=payment.amount
        )

        if current_user_id:
            gl_transaction.created_by = current_user_id

        session.add(gl_transaction)
        session.flush()  # To get the transaction_id

        # Create entries for the transaction
        entries = []

        # CRITICAL LOGIC: Different GL entries for advance payment vs invoice payment
        # 1. DEBIT ENTRY - Check if this is an advance payment or invoice payment
        if payment.invoice_id:
            # This is a payment AGAINST AN INVOICE
            # Debit: Accounts Payable (reduce liability)
            debit_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['accounts_payable'],
                debit_amount=payment.amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Payment to supplier {supplier.supplier_name if supplier else ''} invoice {invoice.supplier_invoice_number if invoice else ''}"
            )
        else:
            # This is an ADVANCE payment (no invoice yet)
            # Debit: Supplier Advance (create asset)
            # CRITICAL FIX: Only create if account exists
            if not accounts.get('supplier_advance'):
                raise ValueError("Cannot post GL for advance payment: Supplier Advance account not configured")

            debit_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['supplier_advance'],
                debit_amount=payment.amount,
                credit_amount=Decimal('0'),
                entry_date=payment.payment_date,
                description=f"Advance payment to supplier {supplier.supplier_name if supplier else ''}"
            )

        if current_user_id:
            debit_entry.created_by = current_user_id

        session.add(debit_entry)
        entries.append(debit_entry)

        # 2. MULTI-METHOD PAYMENT CREDIT ENTRIES
        # Create separate GL entry for each payment method used

        # 2a. Cash payment (if any)
        if payment.cash_amount and payment.cash_amount > 0:
            cash_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=Decimal('0'),
                credit_amount=payment.cash_amount,
                entry_date=payment.payment_date,
                description=f"Cash payment to supplier {supplier.supplier_name if supplier else ''}"
            )
            if current_user_id:
                cash_entry.created_by = current_user_id
            session.add(cash_entry)
            entries.append(cash_entry)

        # 2b. Cheque payment (if any)
        if payment.cheque_amount and payment.cheque_amount > 0:
            cheque_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['bank'],  # Cheques go to bank
                debit_amount=Decimal('0'),
                credit_amount=payment.cheque_amount,
                entry_date=payment.payment_date,
                description=f"Cheque payment to supplier {supplier.supplier_name if supplier else ''} - Cheque# {payment.cheque_number if payment.cheque_number else 'N/A'}"
            )
            if current_user_id:
                cheque_entry.created_by = current_user_id
            session.add(cheque_entry)
            entries.append(cheque_entry)

        # 2c. Bank transfer payment (if any)
        if payment.bank_transfer_amount and payment.bank_transfer_amount > 0:
            bank_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['bank'],
                debit_amount=Decimal('0'),
                credit_amount=payment.bank_transfer_amount,
                entry_date=payment.payment_date,
                description=f"Bank transfer to supplier {supplier.supplier_name if supplier else ''} - Ref# {payment.bank_reference_number if payment.bank_reference_number else 'N/A'}"
            )
            if current_user_id:
                bank_entry.created_by = current_user_id
            session.add(bank_entry)
            entries.append(bank_entry)

        # 2d. UPI payment (if any)
        if payment.upi_amount and payment.upi_amount > 0:
            upi_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['bank'],  # UPI goes through bank
                debit_amount=Decimal('0'),
                credit_amount=payment.upi_amount,
                entry_date=payment.payment_date,
                description=f"UPI payment to supplier {supplier.supplier_name if supplier else ''} - UPI# {payment.upi_transaction_id if payment.upi_transaction_id else 'N/A'}"
            )
            if current_user_id:
                upi_entry.created_by = current_user_id
            session.add(upi_entry)
            entries.append(upi_entry)

        # 2e. ADVANCE ALLOCATION (if any) - CRITICAL FIX
        # This is an internal transfer from Supplier Advance (Asset) to reduce AP
        if payment.advance_amount and payment.advance_amount > 0:
            # CRITICAL FIX: Only create GL entry if Supplier Advance account exists
            if accounts.get('supplier_advance'):
                advance_entry = GLEntry(
                    hospital_id=payment.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['supplier_advance'],  # Credit the Supplier Advance account
                    debit_amount=Decimal('0'),
                    credit_amount=payment.advance_amount,
                    entry_date=payment.payment_date,
                    description=f"Advance allocation to supplier {supplier.supplier_name if supplier else ''} invoice {invoice.supplier_invoice_number if invoice else 'N/A'}"
                )
                if current_user_id:
                    advance_entry.created_by = current_user_id
                session.add(advance_entry)
                entries.append(advance_entry)
            else:
                logger.warning(f"Skipping GL entry for advance allocation of ₹{payment.advance_amount} - Supplier Advance account not configured")

        session.flush()

        # Update payment record with GL reference
        payment.gl_entry_id = gl_transaction.transaction_id

        # ✅ CRITICAL FIX: Create AP Subledger entry for ALL supplier payments
        # Best Practice: AP Subledger should track ALL supplier transactions
        try:
            from app.services.subledger_service import create_ap_subledger_entry
            from decimal import Decimal

            if payment.invoice_id:
                # Payment AGAINST INVOICE - Debit AP (reduces liability)
                create_ap_subledger_entry(
                    session=session,
                    hospital_id=payment.hospital_id,
                    branch_id=payment.branch_id,
                    supplier_id=payment.supplier_id,
                    entry_type='payment',
                    reference_type='payment',
                    reference_id=payment.payment_id,
                    reference_number=payment.reference_no,
                    transaction_date=payment.payment_date,
                    debit_amount=payment.amount,  # Payment = Debit (reduces liability)
                    credit_amount=Decimal('0'),
                    gl_transaction_id=gl_transaction.transaction_id,
                    current_user_id=current_user_id
                )
                logger.info(f"Created AP subledger entry for invoice payment {payment.payment_id}, amount: ₹{payment.amount}")
            else:
                # ADVANCE PAYMENT - Debit AP (advance payment)
                create_ap_subledger_entry(
                    session=session,
                    hospital_id=payment.hospital_id,
                    branch_id=payment.branch_id,
                    supplier_id=payment.supplier_id,
                    entry_type='advance',
                    reference_type='payment',
                    reference_id=payment.payment_id,
                    reference_number=payment.reference_no,
                    transaction_date=payment.payment_date,
                    debit_amount=payment.amount,  # Advance = Debit
                    credit_amount=Decimal('0'),
                    gl_transaction_id=gl_transaction.transaction_id,
                    current_user_id=current_user_id
                )
                logger.info(f"Created AP subledger entry for advance payment {payment.payment_id}, amount: ₹{payment.amount}")
        except Exception as ap_error:
            # Don't fail the entire transaction if AP subledger creation fails
            # But log it prominently
            logger.error(f"Failed to create AP subledger entry for payment {payment.payment_id}: {str(ap_error)}", exc_info=True)
            # Continue - GL entries are more critical

        # Return just the transaction_id (avoid session access issues with get_entity_dict)
        return {'transaction_id': gl_transaction.transaction_id}
        
    except Exception as e:
        logger.error(f"Error creating supplier payment GL entries: {str(e)}")
        # CRITICAL FIX: Don't rollback when using a shared session
        # The caller should handle rollback
        # session.rollback()  # REMOVED - causes "closed transaction" error
        raise

def _get_gl_accounts_for_supplier_payment(session: Session, payment: SupplierPayment) -> Dict:
    """
    Get the GL accounts needed for a supplier payment

    Args:
        session: Database session
        payment: Supplier payment object

    Returns:
        Dictionary of account IDs by purpose
    """
    hospital_id = payment.hospital_id
    accounts = {}

    # Get the Accounts Payable account
    ap_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Accounts Payable%'),
        ChartOfAccounts.is_active == True
    ).first()

    if not ap_account:
        raise ValueError("Accounts Payable GL account not found")

    accounts['accounts_payable'] = ap_account.account_id

    # Cash account
    cash_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Cash%'),
        ChartOfAccounts.is_active == True
    ).first()

    if not cash_account:
        raise ValueError("Cash GL account not found")

    accounts['cash'] = cash_account.account_id

    # Bank account
    bank_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Bank%'),
        ChartOfAccounts.is_active == True
    ).first()

    if not bank_account:
        raise ValueError("Bank GL account not found")

    accounts['bank'] = bank_account.account_id

    # Supplier Advance account (Asset account) - OPTIONAL for advance allocations
    supplier_advance_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Supplier Advance%'),
        ChartOfAccounts.is_active == True
    ).first()

    if not supplier_advance_account:
        # Try alternative name
        supplier_advance_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%Advance to Suppliers%'),
            ChartOfAccounts.is_active == True
        ).first()

    # CRITICAL FIX: Make this optional - if not found, set to None
    # The GL posting will skip advance entries if this is None
    if supplier_advance_account:
        accounts['supplier_advance'] = supplier_advance_account.account_id
        logger.info(f"Found Supplier Advance GL account: {supplier_advance_account.account_name}")
    else:
        accounts['supplier_advance'] = None
        logger.warning("Supplier Advance GL account not found. Advance allocations will not have GL entries. Please create an asset account named 'Supplier Advance'.")

    return accounts

def reverse_supplier_payment_gl_entries(
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Reverse GL entries for a supplier payment (used when deleting payment)

    Args:
        payment_id: Supplier Payment UUID
        current_user_id: ID of the user creating the reversal
        session: Database session (optional)

    Returns:
        Dictionary containing reversal transaction details
    """
    if session is not None:
        return _reverse_supplier_payment_gl_entries(session, payment_id, current_user_id)

    with get_db_session() as new_session:
        return _reverse_supplier_payment_gl_entries(new_session, payment_id, current_user_id)

def _reverse_supplier_payment_gl_entries(
    session: Session,
    payment_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to reverse GL entries for a supplier payment
    """
    try:
        # Get the payment record
        payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()

        if not payment:
            raise ValueError(f"Supplier payment with ID {payment_id} not found")

        # Find the original GL transaction
        original_gl = session.query(GLTransaction).filter_by(
            reference_id=str(payment_id),
            transaction_type="SUPPLIER_PAYMENT"
        ).first()

        if not original_gl:
            raise ValueError(f"Original GL transaction not found for payment {payment_id}")

        # Create reversal GL transaction
        reversal_gl = GLTransaction(
            hospital_id=payment.hospital_id,
            transaction_date=datetime.now(),
            transaction_type="SUPPLIER_PAYMENT_REVERSAL",
            reference_id=str(payment.payment_id),
            description=f"Reversal of payment {payment.reference_no or payment.payment_id}",
            currency_code=payment.currency_code,
            exchange_rate=payment.exchange_rate,
            total_debit=original_gl.total_debit,
            total_credit=original_gl.total_credit,
            is_reversal=True
        )

        if current_user_id:
            reversal_gl.created_by = current_user_id

        session.add(reversal_gl)
        session.flush()

        # Reverse all original GL entries (swap debit and credit)
        original_entries = session.query(GLEntry).filter_by(
            transaction_id=original_gl.transaction_id
        ).all()

        for original_entry in original_entries:
            reversal_entry = GLEntry(
                hospital_id=original_entry.hospital_id,
                transaction_id=reversal_gl.transaction_id,
                account_id=original_entry.account_id,
                debit_amount=original_entry.credit_amount,  # Swap
                credit_amount=original_entry.debit_amount,  # Swap
                entry_date=datetime.now(),
                description=f"Reversal: {original_entry.description}"
            )

            if current_user_id:
                reversal_entry.created_by = current_user_id

            session.add(reversal_entry)

        session.flush()

        # ✅ CRITICAL FIX: Reverse AP Subledger entries
        # Best Practice: Maintain complete audit trail in subledgers
        try:
            from app.services.subledger_service import create_ap_subledger_entry
            from app.models.transaction import APSubledger, SupplierAdvanceAdjustment
            from decimal import Decimal

            # Find original AP subledger entry
            original_ap_entry = session.query(APSubledger).filter_by(
                reference_id=payment.payment_id,
                reference_type='payment'
            ).first()

            if original_ap_entry:
                # Create offsetting AP subledger entry
                create_ap_subledger_entry(
                    session=session,
                    hospital_id=payment.hospital_id,
                    branch_id=payment.branch_id,
                    supplier_id=payment.supplier_id,
                    entry_type='adjustment',  # Reversal is an adjustment
                    reference_type='payment',  # ✅ FIXED: Use 'payment' not 'payment_reversal'
                    reference_id=payment.payment_id,
                    reference_number=f"REV-{payment.reference_no or payment.payment_id}",
                    transaction_date=datetime.now(),
                    debit_amount=original_ap_entry.credit_amount,  # Swap
                    credit_amount=original_ap_entry.debit_amount,  # Swap
                    gl_transaction_id=reversal_gl.transaction_id,
                    current_user_id=current_user_id
                )
                logger.info(f"Reversed AP subledger entry for payment {payment_id}")

            # Reverse Supplier Advance subledger entries (if advance payment)
            if not payment.invoice_id:
                original_advance_entry = session.query(SupplierAdvanceAdjustment).filter_by(
                    payment_id=payment.payment_id
                ).first()

                if original_advance_entry:
                    # Create offsetting advance entry
                    reversal_advance_entry = SupplierAdvanceAdjustment(
                        hospital_id=payment.hospital_id,
                        branch_id=payment.branch_id,
                        supplier_id=payment.supplier_id,
                        adjustment_date=datetime.now(),
                        adjustment_type='reversal',
                        payment_id=payment.payment_id,
                        invoice_id=None,
                        debit_amount=original_advance_entry.credit_amount or Decimal('0'),  # Swap
                        credit_amount=original_advance_entry.debit_amount or Decimal('0'),  # Swap
                        description=f"Reversal of advance payment {payment.reference_no or payment.payment_id}",
                        gl_transaction_id=reversal_gl.transaction_id
                    )
                    if current_user_id:
                        reversal_advance_entry.created_by = current_user_id

                    session.add(reversal_advance_entry)
                    logger.info(f"Reversed Supplier Advance subledger entry for payment {payment_id}")

        except Exception as subledger_error:
            # Log but don't fail - GL reversal is more critical
            logger.error(f"Failed to reverse subledger entries for payment {payment_id}: {str(subledger_error)}", exc_info=True)

        # Return the reversal transaction
        return get_entity_dict(reversal_gl)

    except Exception as e:
        logger.error(f"Error reversing supplier payment GL entries: {str(e)}")
        session.rollback()
        raise

# Functions to add to app/services/gl_service.py

def create_refund_gl_entries(
    payment_id: uuid.UUID,
    refund_amount: Decimal,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a payment refund
    
    Args:
        payment_id: Payment UUID
        refund_amount: Amount being refunded
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_refund_gl_entries(session, payment_id, refund_amount, current_user_id)
    
    with get_db_session() as new_session:
        return _create_refund_gl_entries(new_session, payment_id, refund_amount, current_user_id)

def _create_refund_gl_entries(
    session: Session,
    payment_id: uuid.UUID,
    refund_amount: Decimal,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for a payment refund within a session
    """
    try:
        # Get the payment record
        payment = session.query(PaymentDetail).filter_by(payment_id=payment_id).first()
        
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
        
        # Get the related invoice
        invoice = session.query(InvoiceHeader).filter_by(invoice_id=payment.invoice_id).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {payment.invoice_id} not found")
        
        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_payment(session, payment)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=payment.hospital_id,
            transaction_date=payment.refund_date or datetime.now(timezone.utc),
            transaction_type="PAYMENT_REFUND",
            reference_id=str(payment.payment_id),
            description=f"Refund for Invoice {invoice.invoice_number}",
            currency_code=payment.currency_code,
            exchange_rate=payment.exchange_rate,
            total_debit=refund_amount,
            total_credit=refund_amount
        )
        
        if current_user_id:
            gl_transaction.created_by = current_user_id
            
        session.add(gl_transaction)
        session.flush()  # To get the transaction_id
        
        # Create entries for the transaction
        entries = []
        
        # 1. Accounts Receivable debit entry (DR A/R - reverse the payment)
        ar_entry = GLEntry(
            hospital_id=payment.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['accounts_receivable'],
            debit_amount=refund_amount,
            credit_amount=Decimal('0'),
            entry_date=payment.refund_date or datetime.now(timezone.utc),
            description=f"Refund - Invoice {invoice.invoice_number}"
        )
        
        if current_user_id:
            ar_entry.created_by = current_user_id
            
        session.add(ar_entry)
        entries.append(ar_entry)
        
        # 2. Payment method credit entries - use the same payment method proportion as original payment
        # Calculate proportions of each payment method
        total_payment = payment.total_amount
        
        # Cash refund
        if payment.cash_amount > 0:
            cash_proportion = payment.cash_amount / total_payment
            cash_refund = (refund_amount * cash_proportion).quantize(Decimal('0.01'))
            
            cash_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=Decimal('0'),
                credit_amount=cash_refund,
                entry_date=payment.refund_date or datetime.now(timezone.utc),
                description=f"Cash Refund - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                cash_entry.created_by = current_user_id
                
            session.add(cash_entry)
            entries.append(cash_entry)
        
        # Credit Card refund
        if payment.credit_card_amount > 0:
            cc_proportion = payment.credit_card_amount / total_payment
            cc_refund = (refund_amount * cc_proportion).quantize(Decimal('0.01'))
            
            cc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['credit_card'],
                debit_amount=Decimal('0'),
                credit_amount=cc_refund,
                entry_date=payment.refund_date or datetime.now(timezone.utc),
                description=f"Credit Card Refund - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                cc_entry.created_by = current_user_id
                
            session.add(cc_entry)
            entries.append(cc_entry)
        
        # Debit Card refund
        if payment.debit_card_amount > 0:
            dc_proportion = payment.debit_card_amount / total_payment
            dc_refund = (refund_amount * dc_proportion).quantize(Decimal('0.01'))
            
            dc_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['debit_card'],
                debit_amount=Decimal('0'),
                credit_amount=dc_refund,
                entry_date=payment.refund_date or datetime.now(timezone.utc),
                description=f"Debit Card Refund - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                dc_entry.created_by = current_user_id
                
            session.add(dc_entry)
            entries.append(dc_entry)
        
        # UPI refund
        if payment.upi_amount > 0:
            upi_proportion = payment.upi_amount / total_payment
            upi_refund = (refund_amount * upi_proportion).quantize(Decimal('0.01'))
            
            upi_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['upi'],
                debit_amount=Decimal('0'),
                credit_amount=upi_refund,
                entry_date=payment.refund_date or datetime.now(timezone.utc),
                description=f"UPI Refund - Invoice {invoice.invoice_number}"
            )
            
            if current_user_id:
                upi_entry.created_by = current_user_id
                
            session.add(upi_entry)
            entries.append(upi_entry)
            
        session.flush()
        
        # Return the created transaction
        return get_entity_dict(gl_transaction)
        
    except Exception as e:
        logger.error(f"Error creating refund GL entries: {str(e)}")
        session.rollback()
        raise

def process_void_invoice_gl_entries(
    void_invoice_id: uuid.UUID,
    original_invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Process GL entries for a voided invoice
    
    Args:
        void_invoice_id: Void Invoice UUID
        original_invoice_id: Original Invoice UUID being voided
        current_user_id: ID of the user voiding the invoice
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _process_void_invoice_gl_entries(session, void_invoice_id, original_invoice_id, current_user_id)
    
    with get_db_session() as new_session:
        return _process_void_invoice_gl_entries(new_session, void_invoice_id, original_invoice_id, current_user_id)

def _process_void_invoice_gl_entries(
    session: Session,
    void_invoice_id: uuid.UUID,
    original_invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to process GL entries for a voided invoice within a session
    """
    try:
        # Get the void invoice
        void_invoice = session.query(InvoiceHeader).filter_by(invoice_id=void_invoice_id).first()
        
        if not void_invoice:
            raise ValueError(f"Void invoice with ID {void_invoice_id} not found")
        
        # Get the original invoice
        original_invoice = session.query(InvoiceHeader).filter_by(invoice_id=original_invoice_id).first()
        
        if not original_invoice:
            raise ValueError(f"Original invoice with ID {original_invoice_id} not found")
        
        # Create GL entries for the void invoice - this will create reverse entries
        # using the same approach as for normal invoices but with negative amounts
        return create_invoice_gl_entries(void_invoice_id, current_user_id, session)
        
    except Exception as e:
        logger.error(f"Error processing void invoice GL entries: {str(e)}")
        session.rollback()
        raise

def create_advance_payment_gl_entries(
    advance_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a patient advance payment
    
    Args:
        advance_id: Advance Payment UUID
        current_user_id: ID of the user creating the entries
        session: Database session (optional)
        
    Returns:
        Dictionary containing created GL transaction details
    """
    if session is not None:
        return _create_advance_payment_gl_entries(session, advance_id, current_user_id)
    
    with get_db_session() as new_session:
        return _create_advance_payment_gl_entries(new_session, advance_id, current_user_id)

def _create_advance_payment_gl_entries(
    session: Session,
    advance_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create general ledger entries for an advance payment within a session
    """
    try:
        # Get the advance payment record
        advance = session.query(PatientAdvancePayment).filter_by(advance_id=advance_id).first()
        
        if not advance:
            raise ValueError(f"Advance payment with ID {advance_id} not found")
        
        # Get the patient
        patient = session.query(Patient).filter_by(patient_id=advance.patient_id).first()
        
        if not patient:
            raise ValueError(f"Patient with ID {advance.patient_id} not found")
        
        # Get the GL accounts to use
        accounts = _get_gl_accounts_for_advance_payment(session, advance)
        
        # Create a GL transaction
        gl_transaction = GLTransaction(
            hospital_id=advance.hospital_id,
            transaction_date=advance.payment_date,
            transaction_type="ADVANCE_PAYMENT",
            reference_id=str(advance.advance_id),
            description=f"Advance payment from {patient.full_name}",
            currency_code=advance.currency_code,
            exchange_rate=advance.exchange_rate,
            total_debit=advance.amount,
            total_credit=advance.amount
        )
        
        if current_user_id:
            gl_transaction.created_by = current_user_id
            
        session.add(gl_transaction)
        session.flush()  # To get the transaction_id
        
        # Create entries for the transaction
        entries = []
        
        # 1. Patient Advances account credit entry (CR Patient Advances)
        advances_entry = GLEntry(
            hospital_id=advance.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=accounts['patient_advances'],
            debit_amount=Decimal('0'),
            credit_amount=advance.amount,
            entry_date=advance.payment_date,
            description=f"Advance payment from {patient.full_name}"
        )
        
        if current_user_id:
            advances_entry.created_by = current_user_id
            
        session.add(advances_entry)
        entries.append(advances_entry)
        
        # 2. Payment method debit entries
        # Cash
        if advance.cash_amount > 0:
            cash_entry = GLEntry(
                hospital_id=advance.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=advance.cash_amount,
                credit_amount=Decimal('0'),
                entry_date=advance.payment_date,
                description=f"Cash advance payment from {patient.full_name}"
            )
            
            if current_user_id:
                cash_entry.created_by = current_user_id
                
            session.add(cash_entry)
            entries.append(cash_entry)
        
        # Credit Card
        if advance.credit_card_amount > 0:
            cc_entry = GLEntry(
                hospital_id=advance.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['credit_card'],
                debit_amount=advance.credit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=advance.payment_date,
                description=f"Credit Card advance payment from {patient.full_name}"
            )
            
            if current_user_id:
                cc_entry.created_by = current_user_id
                
            session.add(cc_entry)
            entries.append(cc_entry)
        
        # Debit Card
        if advance.debit_card_amount > 0:
            dc_entry = GLEntry(
                hospital_id=advance.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['debit_card'],
                debit_amount=advance.debit_card_amount,
                credit_amount=Decimal('0'),
                entry_date=advance.payment_date,
                description=f"Debit Card advance payment from {patient.full_name}"
            )
            
            if current_user_id:
                dc_entry.created_by = current_user_id
                
            session.add(dc_entry)
            entries.append(dc_entry)
        
        # UPI
        if advance.upi_amount > 0:
            upi_entry = GLEntry(
                hospital_id=advance.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['upi'],
                debit_amount=advance.upi_amount,
                credit_amount=Decimal('0'),
                entry_date=advance.payment_date,
                description=f"UPI advance payment from {patient.full_name}"
            )
            
            if current_user_id:
                upi_entry.created_by = current_user_id
                
            session.add(upi_entry)
            entries.append(upi_entry)
            
        session.flush()
        
        # Update advance payment record with GL reference
        advance.gl_entry_id = gl_transaction.transaction_id
        
        # Return the created transaction
        return get_entity_dict(gl_transaction)
        
    except Exception as e:
        logger.error(f"Error creating advance payment GL entries: {str(e)}")
        session.rollback()
        raise

def _get_gl_accounts_for_advance_payment(session: Session, advance: PatientAdvancePayment) -> Dict:
    """
    Get the GL accounts needed for an advance payment
    
    Args:
        session: Database session
        advance: Advance payment object
        
    Returns:
        Dictionary of account IDs by purpose
    """
    hospital_id = advance.hospital_id
    accounts = {}
    
    # Get the Patient Advances account
    advances_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Patient Advances%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not advances_account:
        # Fall back to accounts payable if patient advances doesn't exist
        advances_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%Accounts Payable%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not advances_account:
            raise ValueError("Patient Advances or Accounts Payable GL account not found")
            
    accounts['patient_advances'] = advances_account.account_id
    
    # Cash account
    cash_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Cash%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not cash_account:
        raise ValueError("Cash GL account not found")
        
    accounts['cash'] = cash_account.account_id
    
    # Credit Card account
    cc_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Credit Card%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not cc_account:
        raise ValueError("Credit Card GL account not found")
        
    accounts['credit_card'] = cc_account.account_id
    
    # Debit Card account
    dc_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%Debit Card%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not dc_account:
        # Fall back to credit card account
        accounts['debit_card'] = cc_account.account_id
    else:
        accounts['debit_card'] = dc_account.account_id
    
    # UPI account
    upi_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.account_name.like('%UPI%'),
        ChartOfAccounts.is_active == True
    ).first()
    
    if not upi_account:
        # Fall back to bank account
        bank_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name.like('%Bank%'),
            ChartOfAccounts.is_active == True
        ).first()
        
        if not bank_account:
            raise ValueError("Bank GL account not found for UPI fallback")
            
        accounts['upi'] = bank_account.account_id
    else:
        accounts['upi'] = upi_account.account_id
    
    return accounts

def create_advance_adjustment_gl_entries(
    session: Session,
    hospital_id: uuid.UUID,
    advance_id: uuid.UUID,
    invoice_id: uuid.UUID,
    adjustment_amount: Decimal,
    adjustment_date: datetime,
    invoice_number: str,
    current_user_id: Optional[str] = None
) -> uuid.UUID:
    """
    Create GL entries for advance payment adjustment

    Entries:
    - DR Accounts Receivable (reduce AR)
    - CR Patient Advance (reduce advance liability)

    Args:
        session: Database session
        hospital_id: Hospital UUID
        advance_id: Advance payment UUID
        invoice_id: Invoice UUID
        adjustment_amount: Amount being adjusted
        adjustment_date: Date of adjustment
        invoice_number: Invoice number for description
        current_user_id: User creating the entries

    Returns:
        GL transaction UUID
    """
    try:
        # Get GL accounts
        ar_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name == 'Accounts Receivable'
        ).first()

        if not ar_account:
            raise ValueError("Accounts Receivable GL account not found")

        advance_account = session.query(ChartOfAccounts).filter(
            ChartOfAccounts.hospital_id == hospital_id,
            ChartOfAccounts.account_name == 'Advance from Patients'
        ).first()

        if not advance_account:
            raise ValueError("Advance from Patients GL account not found")

        # Create GL transaction
        gl_transaction = GLTransaction(
            hospital_id=hospital_id,
            transaction_date=adjustment_date,
            transaction_type="ADVANCE_ADJUSTMENT",
            reference_id=str(invoice_id),
            description=f"Advance adjustment for Invoice {invoice_number}",
            currency_code='INR',
            exchange_rate=Decimal('1.00'),
            total_debit=adjustment_amount,
            total_credit=adjustment_amount
        )

        if current_user_id:
            gl_transaction.created_by = current_user_id

        session.add(gl_transaction)
        session.flush()

        # Create DR entry for Accounts Receivable (reduce AR)
        ar_entry = GLEntry(
            hospital_id=hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=ar_account.account_id,
            debit_amount=adjustment_amount,
            credit_amount=Decimal('0'),
            entry_date=adjustment_date,
            description=f"Advance adjustment - Invoice {invoice_number}"
        )

        if current_user_id:
            ar_entry.created_by = current_user_id

        session.add(ar_entry)

        # Create CR entry for Patient Advance (reduce liability)
        advance_entry = GLEntry(
            hospital_id=hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=advance_account.account_id,
            debit_amount=Decimal('0'),
            credit_amount=adjustment_amount,
            entry_date=adjustment_date,
            description=f"Advance adjustment - Invoice {invoice_number}"
        )

        if current_user_id:
            advance_entry.created_by = current_user_id

        session.add(advance_entry)
        session.flush()

        logger.info(f"Created GL entries for advance adjustment: Transaction {gl_transaction.transaction_id}")

        return gl_transaction.transaction_id

    except Exception as e:
        logger.error(f"Error creating GL entries for advance adjustment: {str(e)}")
        raise

def create_patient_credit_note_gl_entries(
    credit_note_id: str,
    hospital_id: str,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create GL and AR entries for a patient credit note (package discontinuation)

    GL Entries:
      Dr: Package Revenue (4200) - Reduce income
      Cr: Accounts Receivable (1100) - Reduce receivable

    AR Entry:
      Credit AR Subledger - Reduce patient's receivable balance

    Args:
        credit_note_id: Credit note ID (UUID as string)
        hospital_id: Hospital ID (UUID as string)
        current_user_id: User creating the entries
        session: Database session (optional)

    Returns:
        {
            'success': bool,
            'ar_entry_id': str,
            'gl_transaction_id': str,
            'message': str
        }
    """
    if session is not None:
        return _create_patient_credit_note_gl_entries(session, credit_note_id, hospital_id, current_user_id)

    with get_db_session() as new_session:
        return _create_patient_credit_note_gl_entries(new_session, credit_note_id, hospital_id, current_user_id)

def _create_patient_credit_note_gl_entries(
    session: Session,
    credit_note_id: str,
    hospital_id: str,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create GL and AR entries for a patient credit note
    """
    try:
        # Get the credit note
        credit_note = session.query(PatientCreditNote).filter(
            and_(
                PatientCreditNote.credit_note_id == credit_note_id,
                PatientCreditNote.hospital_id == hospital_id
            )
        ).first()

        if not credit_note:
            return {
                'success': False,
                'error': f'Credit note {credit_note_id} not found'
            }

        # Check if already posted (fully completed)
        if credit_note.gl_posted and credit_note.gl_transaction_id:
            logger.info(f"✅ Credit note {credit_note.credit_note_number} already posted to GL")

            # Get existing AR entry ID
            existing_ar = session.query(ARSubledger).filter(
                and_(
                    ARSubledger.reference_type == 'credit_note',
                    ARSubledger.reference_id == str(credit_note.credit_note_id)
                )
            ).first()

            return {
                'success': True,
                'message': 'Credit note already posted',
                'ar_entry_id': str(existing_ar.entry_id) if existing_ar else None,
                'gl_transaction_id': str(credit_note.gl_transaction_id)
            }

        # Check for partial posting (entries exist but flag not set)
        # This handles retry scenarios where posting partially succeeded
        existing_ar = session.query(ARSubledger).filter(
            and_(
                ARSubledger.reference_type == 'credit_note',
                ARSubledger.reference_id == str(credit_note.credit_note_id)
            )
        ).first()

        existing_gl = session.query(GLTransaction).filter(
            and_(
                GLTransaction.source_document_type == 'credit_note',
                GLTransaction.source_document_id == credit_note.credit_note_id
            )
        ).first()

        if existing_ar and existing_gl:
            # Both AR and GL exist - just update the flag (idempotent retry)
            logger.info(f"🔄 Found existing GL entries for credit note {credit_note.credit_note_number}, updating status")
            credit_note.gl_posted = True
            credit_note.gl_transaction_id = existing_gl.transaction_id
            credit_note.posted_at = datetime.utcnow()
            credit_note.posted_by = current_user_id
            credit_note.status = 'posted'

            session.flush()

            return {
                'success': True,
                'ar_entry_id': str(existing_ar.entry_id),
                'gl_transaction_id': str(existing_gl.transaction_id),
                'message': f'GL entries found and status updated for credit note {credit_note.credit_note_number}'
            }

        # If partial entries exist, log warning (should not happen in normal flow)
        if existing_ar or existing_gl:
            logger.warning(f"⚠️ Partial posting detected - AR: {bool(existing_ar)}, GL: {bool(existing_gl)}")
            # Continue to create missing entries below

        # 1. CREATE AR SUBLEDGER ENTRY (Credit entry to reduce AR balance)
        ar_entry_id = None

        # Skip AR creation if already exists
        if existing_ar:
            logger.info(f"✅ AR entry already exists, skipping creation")
            ar_entry_id = str(existing_ar.entry_id)
        else:
            # Get branch_id from original invoice (credit_note.branch_id might be None)
            ar_branch_id = credit_note.branch_id
            if not ar_branch_id and credit_note.original_invoice_id:
                # Fetch branch_id from original invoice
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == credit_note.original_invoice_id
                ).first()
                if invoice:
                    ar_branch_id = invoice.branch_id
                    logger.info(f"Using invoice branch_id: {ar_branch_id}")

            if not ar_branch_id:
                logger.error("Cannot create AR entry: branch_id is required but not found")
                return {
                    'success': False,
                    'error': 'branch_id is required for AR entry but not found in credit note or invoice'
                }

            # Get current patient balance
            current_balance = session.query(
                func.coalesce(func.sum(ARSubledger.debit_amount), 0) -
                func.coalesce(func.sum(ARSubledger.credit_amount), 0)
            ).filter(
                and_(
                    ARSubledger.hospital_id == hospital_id,
                    ARSubledger.patient_id == credit_note.patient_id
                )
            ).scalar() or Decimal('0')

            # Calculate new balance after credit
            new_balance = current_balance - credit_note.total_amount

            ar_entry = ARSubledger(
                entry_id=uuid.uuid4(),
                hospital_id=credit_note.hospital_id,
                branch_id=ar_branch_id,  # Use fetched branch_id
                transaction_date=credit_note.credit_note_date,
                entry_type='credit_note',
                reference_id=str(credit_note.credit_note_id),
                reference_type='credit_note',
                reference_number=credit_note.credit_note_number,
                patient_id=credit_note.patient_id,
                debit_amount=Decimal('0.00'),
                credit_amount=credit_note.total_amount,
                current_balance=new_balance,
                gl_transaction_id=None,  # Will be updated after GL posting
                created_at=datetime.utcnow(),
                created_by=current_user_id
            )

            session.add(ar_entry)
            session.flush()
            ar_entry_id = str(ar_entry.entry_id)

            logger.info(f"✅ AR credit entry created: ₹{credit_note.total_amount}, New balance: ₹{new_balance}")

        # 2. CREATE GL TRANSACTION AND ENTRIES

        # Skip GL creation if already exists
        if existing_gl:
            logger.info(f"✅ GL transaction already exists, skipping creation")

            # Link AR entry to existing GL transaction if not already linked
            if ar_entry_id and not existing_ar:
                # Update newly created AR entry with GL transaction ID
                ar_entry = session.query(ARSubledger).filter(
                    ARSubledger.entry_id == ar_entry_id
                ).first()
                if ar_entry:
                    ar_entry.gl_transaction_id = existing_gl.transaction_id
                    session.flush()

            # Update credit note with GL posting info
            credit_note.gl_posted = True
            credit_note.gl_transaction_id = existing_gl.transaction_id
            credit_note.posted_at = datetime.utcnow()
            credit_note.posted_by = current_user_id
            credit_note.status = 'posted'

            session.flush()

            return {
                'success': True,
                'ar_entry_id': ar_entry_id,
                'gl_transaction_id': str(existing_gl.transaction_id),
                'message': f'GL entries already exist, status updated for credit note {credit_note.credit_note_number}'
            }

        # Find Package Revenue account (4200)
        revenue_account = session.query(ChartOfAccounts).filter(
            and_(
                ChartOfAccounts.hospital_id == hospital_id,
                ChartOfAccounts.gl_account_no == '4200',
                ChartOfAccounts.is_active == True
            )
        ).first()

        # Find AR account (1100 - Accounts Receivable)
        ar_account = session.query(ChartOfAccounts).filter(
            and_(
                ChartOfAccounts.hospital_id == hospital_id,
                ChartOfAccounts.gl_account_no == '1100',
                ChartOfAccounts.account_name == 'Accounts Receivable',
                ChartOfAccounts.is_active == True
            )
        ).first()

        if not revenue_account:
            logger.warning("Package Revenue account (4200) not found, using general revenue")
            # Fallback to Service Revenue (4100)
            revenue_account = session.query(ChartOfAccounts).filter(
                and_(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.gl_account_no == '4100',
                    ChartOfAccounts.is_active == True
                )
            ).first()

        if not revenue_account or not ar_account:
            return {
                'success': False,
                'error': f'GL accounts not found (Revenue: {revenue_account}, AR: {ar_account})'
            }

        # Create GL transaction
        gl_transaction = GLTransaction(
            transaction_id=uuid.uuid4(),
            hospital_id=credit_note.hospital_id,
            transaction_date=credit_note.credit_note_date,
            transaction_type='credit_note',
            reference_id=str(credit_note.credit_note_id),
            description=f"Credit Note {credit_note.credit_note_number} - {credit_note.reason_description[:100]}",
            source_document_type='credit_note',
            source_document_id=credit_note.credit_note_id,
            total_debit=credit_note.total_amount,
            total_credit=credit_note.total_amount,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            created_by=current_user_id,
            updated_by=current_user_id
        )

        session.add(gl_transaction)
        session.flush()

        # Entry 1: Debit Package Revenue (reduce income)
        revenue_entry = GLEntry(
            entry_id=uuid.uuid4(),
            hospital_id=credit_note.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=revenue_account.account_id,
            entry_date=credit_note.credit_note_date,
            description=f"Reduce revenue - Credit Note {credit_note.credit_note_number}",
            debit_amount=credit_note.total_amount,
            credit_amount=Decimal('0.00'),
            source_document_type='credit_note',
            source_document_id=credit_note.credit_note_id,
            created_at=datetime.utcnow(),
            created_by=current_user_id
        )
        session.add(revenue_entry)

        # Entry 2: Credit AR (reduce receivable)
        ar_gl_entry = GLEntry(
            entry_id=uuid.uuid4(),
            hospital_id=credit_note.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=ar_account.account_id,
            entry_date=credit_note.credit_note_date,
            description=f"Reduce AR - Credit Note {credit_note.credit_note_number}",
            debit_amount=Decimal('0.00'),
            credit_amount=credit_note.total_amount,
            source_document_type='credit_note',
            source_document_id=credit_note.credit_note_id,
            created_at=datetime.utcnow(),
            created_by=current_user_id
        )
        session.add(ar_gl_entry)

        session.flush()

        # Update AR entry with GL transaction reference
        ar_entry.gl_transaction_id = gl_transaction.transaction_id

        # Update credit note with GL posting info
        credit_note.gl_posted = True
        credit_note.gl_transaction_id = gl_transaction.transaction_id
        credit_note.posted_at = datetime.utcnow()
        credit_note.posted_by = current_user_id
        credit_note.status = 'posted'

        session.flush()

        logger.info(f"✅ GL entries created: Dr {revenue_account.account_name} ₹{credit_note.total_amount}, Cr {ar_account.account_name} ₹{credit_note.total_amount}")

        return {
            'success': True,
            'ar_entry_id': ar_entry_id,
            'gl_transaction_id': str(gl_transaction.transaction_id),
            'message': f'GL/AR entries posted for credit note {credit_note.credit_note_number}'
        }

    except Exception as e:
        logger.error(f"Error creating GL entries for credit note: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

# Modify the import statement in billing_service.py to add these functions
# from app.services.gl_service import create_invoice_gl_entries, create_payment_gl_entries, create_refund_gl_entries, process_void_invoice_gl_entries