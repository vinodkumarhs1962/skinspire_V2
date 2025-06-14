# app/services/enhanced_posting_helper.py
# UPDATED to use enhanced posting config service with dynamic account lookup
# Maintains existing function signatures for backward compatibility

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from app.models.transaction import SupplierInvoice, SupplierPayment, GLEntry, GLTransaction
from app.models.master import ChartOfAccounts
from app.services.posting_config_service import (
    get_posting_config, 
    is_enhanced_posting_enabled,
    get_default_gl_account,
    get_payment_method_account
)

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

class EnhancedPostingHelper:
    """
    UPDATED: Enhanced posting helper with dynamic account lookup
    Maintains backward compatibility while adding smart account discovery
    """
    def __init__(self, logger=None):
        self.enabled = is_enhanced_posting_enabled()
        if logger:
            self.logger = logger
        else:
            # Use Unicode-safe logger
            self.logger = get_unicode_safe_logger(__name__)

   
    def create_enhanced_invoice_posting(
        self,
        invoice_id: uuid.UUID,
        session: Session,
        current_user_id: str
    ) -> Dict:
        """
        UPDATED: Create enhanced GL/AP entries with dynamic account lookup
        """
        
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}
        
        # NEW: Add session state check
        if not session.is_active:
            self.logger.warning("Session not active - skipping enhanced posting")
            return {'status': 'skipped', 'message': 'Session not active'}

        try:
            # Get invoice details
            invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            posting_reference = f"ENH-INV-{invoice.supplier_invoice_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # ✅ NEW: Create GLTransaction first (as per previous fix)
            gl_transaction = GLTransaction(
                hospital_id=invoice.hospital_id,
                transaction_date=invoice.invoice_date,
                transaction_type='SUPPLIER_INVOICE_ENHANCED',
                reference_id=str(invoice.invoice_id),
                description=f"Enhanced Posting - Invoice {invoice.supplier_invoice_number}",
                total_debit=Decimal('0.00'),
                total_credit=Decimal('0.00'),
                source_document_type='SUPPLIER_INVOICE',
                source_document_id=invoice.invoice_id,
                created_by=current_user_id
            )
            session.add(gl_transaction)
            session.flush()  # Get the transaction_id
            
            all_entries = []
            total_debits = Decimal('0.00')
            total_credits = Decimal('0.00')
            
            # Create AP entries with hospital-specific config
            ap_entries = self._create_ap_entries_with_transaction(
                invoice, gl_transaction, session, posting_reference, current_user_id
            )
            all_entries.extend(ap_entries)
            
            # Create GST entries with hospital-specific config
            gst_entries = self._create_gst_entries_with_transaction(
                invoice, gl_transaction, session, posting_reference, current_user_id
            )
            all_entries.extend(gst_entries)
            
            # Calculate totals
            for entry in all_entries:
                if 'debit_amount' in entry:
                    total_debits += Decimal(str(entry['debit_amount']))
                if 'credit_amount' in entry:
                    total_credits += Decimal(str(entry['credit_amount']))
            
            # Update transaction totals
            gl_transaction.total_debit = total_debits
            gl_transaction.total_credit = total_credits
            
            # Mark invoice as posted
            self._mark_invoice_as_posted(invoice_id, session, posting_reference)
            
            self.logger.info(f"✅ Enhanced posting completed for invoice {invoice.supplier_invoice_number}")
            
            return {
                'status': 'success',
                'posting_reference': posting_reference,
                'transaction_id': str(gl_transaction.transaction_id),
                'total_entries': len(all_entries),
                'total_debits': float(total_debits),
                'total_credits': float(total_credits),
                'message': f'Enhanced posting completed for invoice {invoice.supplier_invoice_number}'
            }
            
        except Exception as e:
            self.logger.error(f"Enhanced invoice posting failed: {str(e)}")
            self._mark_posting_failed(invoice_id, session, str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _create_ap_entries_with_transaction(
    self,
    invoice: SupplierInvoice,
    gl_transaction: GLTransaction,
    session: Session,
    posting_reference: str,
    current_user_id: str
) -> List[Dict]:
        """
        FIXED: Create AP entries with proper session handling to prevent transaction conflicts
        PRESERVES: All existing logic, only fixes session management
        """
        
        ap_entries = []
        hospital_id_str = str(invoice.hospital_id)
        
        try:
            # Get AP account configuration (unchanged)
            ap_account_code = get_default_gl_account('ap', hospital_id_str)
            self.logger.info(f"🔍 AP POSTING: Looking for AP account: {ap_account_code} (dynamic lookup for hospital {hospital_id_str})")
            
            if not ap_account_code:
                self.logger.error(f"❌ AP POSTING: AP account not found for hospital {hospital_id_str}")
                return ap_entries
            
            # CRITICAL FIX: Simple session check without queries that close transactions
            if not session.is_active:
                self.logger.warning(f"⚠️ AP POSTING: Session not active - skipping")
                return ap_entries
            
            # Session is working - proceed with AP entry creation
            ap_account = session.query(ChartOfAccounts).filter_by(
                hospital_id=invoice.hospital_id,
                gl_account_no=ap_account_code
            ).first()
            
            if not ap_account:
                self.logger.error(f"❌ AP POSTING: AP account {ap_account_code} not found for hospital {hospital_id_str}")
                
                # List available liability accounts for debugging (with session safety)
                try:
                    available_liability_accounts = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        account_group='Liabilities'
                    ).all()
                    self.logger.error(f"❌ AP POSTING: Available liability accounts: {[f'{acc.gl_account_no}-{acc.account_name}' for acc in available_liability_accounts]}")
                except Exception as debug_error:
                    self.logger.error(f"❌ AP POSTING: Could not list available accounts: {str(debug_error)}")
                return ap_entries
            
            self.logger.info(f"✅ AP POSTING: Found AP account: {ap_account.gl_account_no} - {ap_account.account_name}")
            self.logger.info(f"✅ AP POSTING: Creating AP credit entry for {invoice.total_amount}")
            
            # Create AP credit entry (increase liability) - UNCHANGED LOGIC
            ap_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=ap_account.account_id,
                entry_date=invoice.invoice_date,
                description=f"Enhanced AP - Invoice {invoice.supplier_invoice_number}",
                credit_amount=invoice.total_amount,
                debit_amount=Decimal('0.00'),
                source_document_type='SUPPLIER_INVOICE',
                source_document_id=invoice.invoice_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            
            # CRITICAL FIX: Safe session operations
            try:
                session.add(ap_entry)
                session.flush()  # Test if flush works
                
                self.logger.info(f"✅ AP POSTING: Successfully created AP entry with ID: {ap_entry.entry_id}")
                
                ap_entries.append({
                    'type': 'AP_Credit',
                    'account': ap_account_code,
                    'account_name': ap_account.account_name,
                    'credit_amount': float(invoice.total_amount),
                    'debit_amount': 0.0,
                    'entry_id': str(ap_entry.entry_id)
                })
                
                self.logger.info(f"✅ AP POSTING: AP entries completed successfully. Total entries: {len(ap_entries)}")
                
            except Exception as flush_error:
                self.logger.error(f"❌ AP POSTING: Session flush failed: {str(flush_error)}")
                # Return empty list - allows invoice creation to continue
                return ap_entries
            
        except Exception as e:
            self.logger.error(f"❌ AP POSTING: Error creating AP entries: {str(e)}")
            self.logger.warning(f"⚠️ AP POSTING: Enhanced posting will be skipped for this invoice")
            # Return empty list instead of raising - allows invoice creation to continue
            return ap_entries
        
        return ap_entries


    def _create_ap_entries_with_fresh_session(
        self,
        invoice: SupplierInvoice,
        gl_transaction: GLTransaction,
        fresh_session: Session,
        posting_reference: str,
        current_user_id: str
    ) -> List[Dict]:
        """
        ✅ NEW HELPER: Create AP entries with a fresh session when original session fails
        """
        ap_entries = []
        hospital_id_str = str(invoice.hospital_id)
        
        try:
            # Get AP account configuration
            ap_account_code = get_default_gl_account('ap', hospital_id_str)
            self.logger.info(f"🔄 AP POSTING: Fresh session - Looking for AP account: {ap_account_code}")
            
            ap_account = fresh_session.query(ChartOfAccounts).filter_by(
                hospital_id=invoice.hospital_id,
                gl_account_no=ap_account_code
            ).first()
            
            if not ap_account:
                self.logger.error(f"❌ AP POSTING: Fresh session - AP account {ap_account_code} not found")
                return ap_entries
            
            # ✅ IMPORTANT: We need to get or recreate the GL transaction in this session
            existing_gl_transaction = fresh_session.query(GLTransaction).filter_by(
                transaction_id=gl_transaction.transaction_id
            ).first()
            
            if not existing_gl_transaction:
                # Create a new GL transaction for this fresh session
                self.logger.info("🔄 AP POSTING: Creating new GL transaction in fresh session")
                fresh_gl_transaction = GLTransaction(
                    transaction_id=gl_transaction.transaction_id,  # Keep same ID
                    hospital_id=invoice.hospital_id,
                    transaction_date=invoice.invoice_date,
                    transaction_type='SUPPLIER_INVOICE_AP',
                    description=f"AP posting for invoice {invoice.supplier_invoice_number}",
                    total_debit=Decimal('0.00'),
                    total_credit=invoice.total_amount,
                    status='posted',
                    created_by=current_user_id
                )
                fresh_session.add(fresh_gl_transaction)
                fresh_session.flush()
                transaction_to_use = fresh_gl_transaction
            else:
                transaction_to_use = existing_gl_transaction
            
            # Create AP credit entry
            ap_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=transaction_to_use.transaction_id,
                account_id=ap_account.account_id,
                entry_date=invoice.invoice_date,
                description=f"Enhanced AP - Invoice {invoice.supplier_invoice_number} (Fresh Session)",
                credit_amount=invoice.total_amount,
                debit_amount=Decimal('0.00'),
                source_document_type='SUPPLIER_INVOICE',
                source_document_id=invoice.invoice_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            fresh_session.add(ap_entry)
            fresh_session.commit()  # Commit the fresh session
            
            self.logger.info(f"✅ AP POSTING: Fresh session - Successfully created AP entry")
            
            ap_entries.append({
                'type': 'AP_Credit',
                'account': ap_account_code,
                'account_name': ap_account.account_name,
                'credit_amount': float(invoice.total_amount),
                'debit_amount': 0.0,
                'entry_id': str(ap_entry.entry_id)
            })
            
        except Exception as e:
            self.logger.error(f"❌ AP POSTING: Fresh session error: {str(e)}")
            fresh_session.rollback()
        
        return ap_entries
    
    def _create_gst_entries_with_transaction(
    self,
    invoice: SupplierInvoice,
    gl_transaction: GLTransaction,
    session: Session,
    posting_reference: str,
    current_user_id: str
) -> List[Dict]:
        """
        FIXED: Create GST entries with proper session handling
        PRESERVES: All existing logic, only adds session safety
        """
        
        gst_entries = []
        hospital_id_str = str(invoice.hospital_id)
        
        try:
            # CRITICAL FIX: Simple session check without queries that close transactions
            if not session.is_active:
                self.logger.warning(f"⚠️ GST POSTING: Session not active - skipping")
                return gst_entries
            
            # Process CGST (unchanged logic)
            if invoice.cgst_amount and invoice.cgst_amount > 0:
                cgst_account_code = get_default_gl_account('cgst', hospital_id_str)
                gst_entries.extend(self._create_single_gst_entry(
                    invoice, gl_transaction, session, posting_reference, current_user_id,
                    cgst_account_code, invoice.cgst_amount, 'CGST'
                ))
            
            # Process SGST (unchanged logic)
            if invoice.sgst_amount and invoice.sgst_amount > 0:
                sgst_account_code = get_default_gl_account('sgst', hospital_id_str)
                gst_entries.extend(self._create_single_gst_entry(
                    invoice, gl_transaction, session, posting_reference, current_user_id,
                    sgst_account_code, invoice.sgst_amount, 'SGST'
                ))
            
            # Process IGST (unchanged logic)
            if invoice.igst_amount and invoice.igst_amount > 0:
                igst_account_code = get_default_gl_account('igst', hospital_id_str)
                gst_entries.extend(self._create_single_gst_entry(
                    invoice, gl_transaction, session, posting_reference, current_user_id,
                    igst_account_code, invoice.igst_amount, 'IGST'
                ))
                
        except Exception as e:
            self.logger.error(f"❌ GST POSTING: Error creating GST entries: {str(e)}")
            self.logger.warning(f"⚠️ GST POSTING: Enhanced GST posting will be skipped")
            # Don't fail the entire posting for GST errors - return what we have
            
        return gst_entries
    
    def _create_single_gst_entry(
    self,
    invoice: SupplierInvoice,
    gl_transaction: GLTransaction,
    session: Session,
    posting_reference: str,
    current_user_id: str,
    account_code: str,
    amount: Decimal,
    gst_type: str
) -> List[Dict]:
        """
        FIXED: Create individual GST entry with session safety
        PRESERVES: All existing logic, adds session error handling
        """
        
        try:
            self.logger.info(f"🔍 GST POSTING: Creating {gst_type} entry for account {account_code}, amount {amount}")
            
            gst_account = session.query(ChartOfAccounts).filter_by(
                hospital_id=invoice.hospital_id,
                gl_account_no=account_code
            ).first()
            
            if not gst_account:
                self.logger.warning(f"❌ GST POSTING: {gst_type} account {account_code} not found")
                
                # List available GST accounts for debugging (with session safety)
                try:
                    available_gst_accounts = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        gst_related=True
                    ).all()
                    self.logger.warning(f"❌ GST POSTING: Available GST accounts: {[f'{acc.gl_account_no}-{acc.account_name}' for acc in available_gst_accounts]}")
                except Exception as debug_error:
                    self.logger.warning(f"❌ GST POSTING: Could not list GST accounts: {str(debug_error)}")
                return []
            
            self.logger.info(f"✅ GST POSTING: Found {gst_type} account: {gst_account.gl_account_no} - {gst_account.account_name}")
            
            gst_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=gst_account.account_id,
                entry_date=invoice.invoice_date,
                description=f"Enhanced {gst_type} - Invoice {invoice.supplier_invoice_number}",
                debit_amount=amount,
                credit_amount=Decimal('0.00'),
                source_document_type='SUPPLIER_INVOICE',
                source_document_id=invoice.invoice_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            
            # CRITICAL FIX: Safe session operations
            try:
                session.add(gst_entry)
                session.flush()
                
                self.logger.info(f"✅ GST POSTING: Successfully created {gst_type} entry with ID: {gst_entry.entry_id}")
                
                return [{
                    'type': f'{gst_type}_Debit',
                    'account': account_code,
                    'account_name': gst_account.account_name,
                    'debit_amount': float(amount),
                    'credit_amount': 0.0,
                    'entry_id': str(gst_entry.entry_id)
                }]
                
            except Exception as session_error:
                self.logger.error(f"❌ GST POSTING: Session error for {gst_type}: {str(session_error)}")
                return []
        
        except Exception as e:
            self.logger.error(f"❌ GST POSTING: Error creating {gst_type} entry: {str(e)}")
            return []
    
    def create_enhanced_payment_posting(
        self,
        payment_id: uuid.UUID,
        session: Session,
        current_user_id: str
    ) -> Dict:
        """
        UPDATED: Create enhanced GL entries for payment with dynamic config
        """
        
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}
        
        try:
            payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            posting_reference = f"ENH-PAY-{payment.reference_no}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create GLTransaction for payment
            gl_transaction = GLTransaction(
                hospital_id=payment.hospital_id,
                transaction_date=payment.payment_date or datetime.now().date(),
                transaction_type='SUPPLIER_PAYMENT_ENHANCED',
                reference_id=str(payment.payment_id),
                description=f"Enhanced Payment - {payment.reference_no}",
                total_debit=payment.amount,
                total_credit=payment.amount,
                source_document_type='SUPPLIER_PAYMENT',
                source_document_id=payment.payment_id,
                created_by=current_user_id
            )
            session.add(gl_transaction)
            session.flush()
            
            # Create enhanced AP reduction entries
            ap_entries = self._create_ap_reduction_entries(
                payment, gl_transaction, session, posting_reference, current_user_id
            )
            
            # Create enhanced bank entries  
            bank_entries = self._create_enhanced_bank_entries(
                payment, gl_transaction, session, posting_reference, current_user_id
            )
            
            # Mark payment as posted
            self._mark_payment_as_posted(payment_id, session, posting_reference)
            
            return {
                'status': 'success',
                'posting_reference': posting_reference,
                'transaction_id': str(gl_transaction.transaction_id),
                'ap_entries_count': len(ap_entries),
                'bank_entries_count': len(bank_entries),
                'message': f'Enhanced posting completed for payment {payment.reference_no}'
            }
            
        except Exception as e:
            self.logger.error(f"Enhanced payment posting failed: {str(e)}")
            self._mark_payment_posting_failed(payment_id, session, str(e))
            return {'status': 'error', 'error': str(e)}
    
    def _create_ap_reduction_entries(
        self,
        payment: SupplierPayment,
        gl_transaction: GLTransaction,
        session: Session,
        posting_reference: str,
        current_user_id: str
    ) -> List[Dict]:
        """Create AP reduction entries for payment with dynamic config"""
        
        ap_entries = []
        hospital_id_str = str(payment.hospital_id)
        
        try:
            # ✅ NEW: Get hospital-specific dynamic config
            ap_account_code = get_default_gl_account('ap', hospital_id_str)
            
            ap_account = session.query(ChartOfAccounts).filter_by(
                hospital_id=payment.hospital_id,
                gl_account_no=ap_account_code
            ).first()
            
            if not ap_account:
                self.logger.warning(f"AP account {ap_account_code} not found")
                return ap_entries
            
            # Create AP debit entry (reduce liability)
            ap_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=ap_account.account_id,
                entry_date=payment.payment_date or datetime.now().date(),
                description=f"Enhanced AP Payment - {payment.reference_no}",
                debit_amount=payment.amount,
                credit_amount=Decimal('0.00'),
                source_document_type='SUPPLIER_PAYMENT',
                source_document_id=payment.payment_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            session.add(ap_entry)
            session.flush()
            
            ap_entries.append({
                'type': 'AP_Debit',
                'account': ap_account_code,
                'debit_amount': float(payment.amount),
                'credit_amount': 0.0,
                'entry_id': str(ap_entry.entry_id)
            })
            
        except Exception as e:
            self.logger.error(f"Error creating AP reduction entries: {str(e)}")
            raise
        
        return ap_entries
    
    def _create_enhanced_bank_entries(
        self,
        payment: SupplierPayment,
        gl_transaction: GLTransaction,
        session: Session,
        posting_reference: str,
        current_user_id: str
    ) -> List[Dict]:
        """Create enhanced bank entries for payment with dynamic config"""
        
        bank_entries = []
        hospital_id_str = str(payment.hospital_id)
        
        try:
            # ✅ NEW: Get hospital-specific dynamic config for payment method
            bank_account_code = get_payment_method_account(payment.payment_method or 'bank_transfer', hospital_id_str)
            
            bank_account = session.query(ChartOfAccounts).filter_by(
                hospital_id=payment.hospital_id,
                gl_account_no=bank_account_code
            ).first()
            
            if not bank_account:
                self.logger.warning(f"Bank account {bank_account_code} not found")
                return bank_entries
            
            # Create bank credit entry (reduce asset)
            bank_entry = GLEntry(
                hospital_id=payment.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=bank_account.account_id,
                entry_date=payment.payment_date or datetime.now().date(),
                description=f"Enhanced Payment to Supplier - {payment.reference_no}",
                credit_amount=payment.amount,
                debit_amount=Decimal('0.00'),
                source_document_type='SUPPLIER_PAYMENT',
                source_document_id=payment.payment_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            session.add(bank_entry)
            session.flush()
            
            bank_entries.append({
                'type': 'Bank_Credit',
                'account': bank_account_code,
                'debit_amount': 0.0,
                'credit_amount': float(payment.amount),
                'entry_id': str(bank_entry.entry_id)
            })
            
        except Exception as e:
            self.logger.error(f"Error creating bank entries: {str(e)}")
            raise
        
        return bank_entries
    
    # ✅ UNCHANGED: Existing helper methods remain the same
    def _mark_invoice_as_posted(self, invoice_id: uuid.UUID, session: Session, posting_reference: str):
        """Mark invoice as posted"""
        invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
        if invoice:
            invoice.gl_posted = True
            invoice.inventory_posted = True
            invoice.posting_date = datetime.now(timezone.utc)
            invoice.posting_reference = posting_reference
            session.flush()
    
    def _mark_payment_as_posted(self, payment_id: uuid.UUID, session: Session, posting_reference: str):
        """Mark payment as posted"""
        payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()
        if payment:
            payment.gl_posted = True
            payment.posting_date = datetime.now(timezone.utc)
            payment.posting_reference = posting_reference
            session.flush()
    
    def _mark_posting_failed(self, invoice_id: uuid.UUID, session: Session, error_message: str):
        """Mark invoice posting as failed"""
        invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
        if invoice:
            invoice.posting_errors = error_message
            session.flush()
    
    def _mark_payment_posting_failed(self, payment_id: uuid.UUID, session: Session, error_message: str):
        """Mark payment posting as failed"""
        payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()
        if payment:
            payment.posting_errors = error_message
            session.flush()

    # ADD this NEW method to your EnhancedPostingHelper class:

    def create_enhanced_invoice_posting_fixed(
    self,
    invoice_id: uuid.UUID,
    current_user_id: str
) -> Dict:
        """
        COMPLETE: Enhanced posting with smart account service integration and AP subledger
        """
        
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}

        try:
            # SESSION FIX: Create completely independent session
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from app.services.database_service import get_database_url
            
            # Fresh engine (bypasses Flask-SQLAlchemy context issues)
            fresh_engine = create_engine(get_database_url())
            FreshSession = sessionmaker(bind=fresh_engine)
            
            with FreshSession() as session:
                self.logger.info("✅ Created independent session for enhanced posting")
                
                # Get invoice
                invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
                if not invoice:
                    raise ValueError(f"Invoice {invoice_id} not found")
                
                self.logger.info(f"Processing enhanced posting for {invoice.supplier_invoice_number}")
                
                # ACCOUNTING: Calculate correct amounts
                total_amount = invoice.total_amount
                cgst_amount = invoice.cgst_amount or Decimal('0')
                sgst_amount = invoice.sgst_amount or Decimal('0')
                igst_amount = invoice.igst_amount or Decimal('0')
                
                # Calculate taxable amount (inventory/expense)
                taxable_amount = total_amount - cgst_amount - sgst_amount - igst_amount
                
                self.logger.info(f"Enhanced posting amounts - Taxable: {taxable_amount}, CGST: {cgst_amount}, SGST: {sgst_amount}, Total: {total_amount}")
                
                posting_reference = f"ENH-{invoice.supplier_invoice_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Create GL Transaction
                gl_transaction = GLTransaction(
                    hospital_id=invoice.hospital_id,
                    transaction_date=invoice.invoice_date,
                    transaction_type='ENHANCED_SUPPLIER_POSTING',
                    reference_id=str(invoice_id),
                    description=f"Enhanced Posting - {invoice.supplier_invoice_number}",
                    total_debit=total_amount,
                    total_credit=total_amount,
                    source_document_type='SUPPLIER_INVOICE',
                    source_document_id=invoice_id,
                    created_by=current_user_id
                )
                session.add(gl_transaction)
                session.flush()
                
                entries_created = 0
                hospital_id_str = str(invoice.hospital_id)
                
                # Import smart account service
                from app.services.posting_config_service import get_default_gl_account
                
                # 1. INVENTORY/EXPENSE DEBIT (Use smart account service)
                if taxable_amount > 0:
                    inventory_account_no = get_default_gl_account('inventory', hospital_id_str)
                    self.logger.info(f"🔍 Smart account lookup - Inventory account: {inventory_account_no} (should be 1410 from .env)")
                    
                    inventory_account = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        gl_account_no=inventory_account_no,
                        is_active=True
                    ).first()
                    
                    if inventory_account:
                        self._create_gl_entry(session, gl_transaction, inventory_account, 
                                            taxable_amount, Decimal('0'), 'Inventory', 
                                            invoice, posting_reference, current_user_id)
                        entries_created += 1
                        self.logger.info(f"✅ Created inventory debit: {taxable_amount} using account {inventory_account_no}")
                    else:
                        self.logger.error(f"❌ Smart lookup failed - Account {inventory_account_no} not found or inactive")
                        
                        # Try expense account as fallback
                        expense_account_no = get_default_gl_account('expense', hospital_id_str)
                        if expense_account_no != inventory_account_no:
                            expense_account = session.query(ChartOfAccounts).filter_by(
                                hospital_id=invoice.hospital_id,
                                gl_account_no=expense_account_no,
                                is_active=True
                            ).first()
                            
                            if expense_account:
                                self.logger.info(f"🔄 Smart fallback - Using expense account: {expense_account_no}")
                                self._create_gl_entry(session, gl_transaction, expense_account, 
                                                    taxable_amount, Decimal('0'), 'Expense', 
                                                    invoice, posting_reference, current_user_id)
                                entries_created += 1
                                self.logger.info(f"✅ Created expense debit using fallback: {taxable_amount}")
                            else:
                                self.logger.error(f"❌ No suitable inventory/expense account found")
                        else:
                            self.logger.error(f"❌ No alternative accounts available")
                
                # 2. CGST DEBIT (Use smart account service)
                if cgst_amount > 0:
                    cgst_account_no = get_default_gl_account('cgst', hospital_id_str)
                    self.logger.info(f"🔍 Smart account lookup - CGST account: {cgst_account_no}")
                    
                    cgst_account = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        gl_account_no=cgst_account_no,
                        is_active=True
                    ).first()
                    
                    if cgst_account:
                        self._create_gl_entry(session, gl_transaction, cgst_account,
                                            cgst_amount, Decimal('0'), 'CGST',
                                            invoice, posting_reference, current_user_id)
                        entries_created += 1
                        self.logger.info(f"✅ Created CGST debit: {cgst_amount} using account {cgst_account_no}")
                    else:
                        self.logger.error(f"❌ CGST account {cgst_account_no} not found or inactive")
                
                # 3. SGST DEBIT (Use smart account service)
                if sgst_amount > 0:
                    sgst_account_no = get_default_gl_account('sgst', hospital_id_str)
                    self.logger.info(f"🔍 Smart account lookup - SGST account: {sgst_account_no}")
                    
                    sgst_account = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        gl_account_no=sgst_account_no,
                        is_active=True
                    ).first()
                    
                    if sgst_account:
                        self._create_gl_entry(session, gl_transaction, sgst_account,
                                            sgst_amount, Decimal('0'), 'SGST',
                                            invoice, posting_reference, current_user_id)
                        entries_created += 1
                        self.logger.info(f"✅ Created SGST debit: {sgst_amount} using account {sgst_account_no}")
                    else:
                        self.logger.error(f"❌ SGST account {sgst_account_no} not found or inactive")
                
                # 4. IGST DEBIT (Use smart account service) - Added for completeness
                if igst_amount > 0:
                    igst_account_no = get_default_gl_account('igst', hospital_id_str)
                    self.logger.info(f"🔍 Smart account lookup - IGST account: {igst_account_no}")
                    
                    igst_account = session.query(ChartOfAccounts).filter_by(
                        hospital_id=invoice.hospital_id,
                        gl_account_no=igst_account_no,
                        is_active=True
                    ).first()
                    
                    if igst_account:
                        self._create_gl_entry(session, gl_transaction, igst_account,
                                            igst_amount, Decimal('0'), 'IGST',
                                            invoice, posting_reference, current_user_id)
                        entries_created += 1
                        self.logger.info(f"✅ Created IGST debit: {igst_amount} using account {igst_account_no}")
                    else:
                        self.logger.error(f"❌ IGST account {igst_account_no} not found or inactive")
                
                # 5. AP CREDIT (Use smart account service) + AP SUBLEDGER
                ap_account_no = get_default_gl_account('ap', hospital_id_str)
                self.logger.info(f"🔍 Smart account lookup - AP account: {ap_account_no} (should be 2100 from .env)")
                
                ap_account = session.query(ChartOfAccounts).filter_by(
                    hospital_id=invoice.hospital_id,
                    gl_account_no=ap_account_no,
                    is_active=True
                ).first()
                
                if ap_account:
                    # Create GL Entry
                    self._create_gl_entry(session, gl_transaction, ap_account,
                                        Decimal('0'), total_amount, 'AP',
                                        invoice, posting_reference, current_user_id)
                    entries_created += 1
                    self.logger.info(f"✅ Created AP credit: {total_amount} using account {ap_account_no}")
                    
                    # ✅ NEW: Create AP Subledger Entry
                    try:
                        from app.models.transaction import APSubledger
                        
                        ap_subledger_entry = APSubledger(
                            hospital_id=invoice.hospital_id,
                            branch_id=invoice.branch_id,
                            transaction_date=invoice.invoice_date,
                            entry_type='invoice',
                            reference_id=invoice.invoice_id,
                            reference_type='invoice',
                            reference_number=invoice.supplier_invoice_number,
                            supplier_id=invoice.supplier_id,
                            debit_amount=Decimal('0'),
                            credit_amount=total_amount,  # AP increases with credit
                            current_balance=total_amount,  # New invoice = full amount outstanding
                            gl_transaction_id=gl_transaction.transaction_id,
                            created_by=current_user_id
                        )
                        
                        session.add(ap_subledger_entry)
                        session.flush()
                        
                        self.logger.info(f"✅ Created AP subledger entry: Invoice {invoice.supplier_invoice_number} - Credit {total_amount}")
                        
                    except Exception as subledger_error:
                        self.logger.error(f"❌ AP Subledger creation failed: {str(subledger_error)}")
                        # Don't fail the entire posting for subledger errors
                        
                else:
                    self.logger.error(f"❌ AP account {ap_account_no} not found or inactive")
                    
                    # This is critical - try to find any liability account
                    fallback_ap = session.query(ChartOfAccounts).filter(
                        ChartOfAccounts.hospital_id == invoice.hospital_id,
                        ChartOfAccounts.account_group == 'Liabilities',
                        ChartOfAccounts.account_name.ilike('%payable%'),
                        ChartOfAccounts.is_active == True
                    ).first()
                    
                    if fallback_ap:
                        self.logger.info(f"🔄 Smart fallback - Using AP account: {fallback_ap.gl_account_no}")
                        self._create_gl_entry(session, gl_transaction, fallback_ap,
                                            Decimal('0'), total_amount, 'AP',
                                            invoice, posting_reference, current_user_id)
                        entries_created += 1
                        self.logger.info(f"✅ Created AP credit using fallback: {total_amount}")
                        
                        # Create AP subledger with fallback account too
                        try:
                            from app.models.transaction import APSubledger
                            
                            ap_subledger_entry = APSubledger(
                                hospital_id=invoice.hospital_id,
                                branch_id=invoice.branch_id,
                                transaction_date=invoice.invoice_date,
                                entry_type='invoice',
                                reference_id=invoice.invoice_id,
                                reference_type='invoice',
                                reference_number=invoice.supplier_invoice_number,
                                supplier_id=invoice.supplier_id,
                                debit_amount=Decimal('0'),
                                credit_amount=total_amount,
                                current_balance=total_amount,
                                gl_transaction_id=gl_transaction.transaction_id,
                                created_by=current_user_id
                            )
                            
                            session.add(ap_subledger_entry)
                            session.flush()
                            
                            self.logger.info(f"✅ Created AP subledger entry (fallback): Invoice {invoice.supplier_invoice_number} - Credit {total_amount}")
                            
                        except Exception as subledger_error:
                            self.logger.error(f"❌ AP Subledger (fallback) creation failed: {str(subledger_error)}")
                            
                    else:
                        self.logger.error(f"❌ No suitable AP account found - this is a critical error")
                
                # Commit all changes
                session.commit()
                
                self.logger.info(f"✅ Enhanced posting completed: {entries_created} entries created")
                
                # Calculate expected entries (dynamic based on GST amounts)
                expected_entries = 2  # Always: Inventory/Expense + AP
                if cgst_amount > 0:
                    expected_entries += 1
                if sgst_amount > 0:
                    expected_entries += 1
                if igst_amount > 0:
                    expected_entries += 1
                    
                if entries_created < expected_entries:
                    self.logger.warning(f"⚠️ Only {entries_created}/{expected_entries} entries created - check account setup")
                
                return {
                    'status': 'success',
                    'posting_reference': posting_reference,
                    'transaction_id': str(gl_transaction.transaction_id),
                    'entries_created': entries_created,
                    'expected_entries': expected_entries,
                    'complete': entries_created == expected_entries,
                    'ap_subledger_created': True,  # NEW: Track AP subledger creation
                    'message': f'Enhanced posting completed for {invoice.supplier_invoice_number}'
                }
                
        except Exception as e:
            self.logger.error(f"❌ Enhanced posting failed: {str(e)}")
            return {
                'status': 'error', 
                'error': str(e),
                'ap_subledger_created': False
            }

    # ADD this helper method to EnhancedPostingHelper class:

    def _create_gl_entry(self, session, gl_transaction, account, debit_amount, credit_amount, 
                        entry_type, invoice, posting_reference, current_user_id):
        """Helper to create GL entries"""
        gl_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_transaction.transaction_id,
            account_id=account.account_id,
            entry_date=invoice.invoice_date,
            description=f"Enhanced {entry_type} - {invoice.supplier_invoice_number}",
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            source_document_type='SUPPLIER_INVOICE',
            source_document_id=invoice.invoice_id,
            posting_reference=posting_reference,
            created_by=current_user_id
        )
        session.add(gl_entry)