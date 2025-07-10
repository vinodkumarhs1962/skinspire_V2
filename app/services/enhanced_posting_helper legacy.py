# app/services/enhanced_posting_helper.py - CONSOLIDATED VERSION
# Eliminates duplicate functions and provides unified posting interface

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.transaction import SupplierInvoice, SupplierPayment, GLEntry, GLTransaction, APSubledger
from app.models.master import ChartOfAccounts
from app.services.posting_config_service import (
    get_posting_config, 
    is_enhanced_posting_enabled,
    get_default_gl_account,
    get_payment_method_account,
    is_strict_posting_mode  # NEW IMPORT
)

from app.utils.unicode_logging import get_unicode_safe_logger

class EnhancedPostingHelper:
    """
    CONSOLIDATED: Enhanced posting helper with unified interface
    Eliminates duplicate functions and provides consistent posting for both invoices and payments
    UPDATED: Now supports strict accounting mode for transactional integrity
    """
    
    def __init__(self, logger=None):
        self.enabled = is_enhanced_posting_enabled()
        self.strict_mode = is_strict_posting_mode()  # NEW: Detect strict mode
        self.logger = logger or get_unicode_safe_logger(__name__)
        
        # Log the current operating mode for debugging
        if self.enabled and self.strict_mode:
            self.logger.info("🔒 Enhanced Posting Helper initialized in STRICT ACCOUNTING MODE")
        elif self.enabled:
            self.logger.info("📋 Enhanced Posting Helper initialized in LEGACY MODE")
        else:
            self.logger.info("🚫 Enhanced Posting Helper initialized - DISABLED")
    # ===================================================================
    # MAIN POSTING METHODS - Unified Interface
    # ===================================================================

    def create_enhanced_invoice_posting(
    self,
    invoice_id: uuid.UUID,
    current_user_id: str,
    session: Optional[Session] = None
) -> Dict:
        """
        UNIFIED: Create enhanced GL/AP entries for invoice
        Supports both session patterns using the WORKING 13.06 approach
        """
        
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}

        # Pattern 1: Use provided session (existing transaction)
        if session is not None:
            self.logger.info(f"🔄 Using provided session for invoice {invoice_id}")
            return self._create_enhanced_invoice_posting_internal(
                invoice_id, current_user_id, session
            )
        
        # Pattern 2: Create completely independent session (WORKING 13.06 APPROACH)
        self.logger.info(f"🔄 Creating fresh session for invoice {invoice_id}")
        try:
            # SESSION FIX: Create completely independent session (bypasses Flask-SQLAlchemy issues)
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from app.services.database_service import get_database_url
            
            # Fresh engine (bypasses Flask-SQLAlchemy context issues)
            fresh_engine = create_engine(get_database_url())
            FreshSession = sessionmaker(bind=fresh_engine)
            
            with FreshSession() as fresh_session:
                self.logger.info("✅ Created independent session for enhanced posting")
                
                result = self._create_enhanced_invoice_posting_internal(
                    invoice_id, current_user_id, fresh_session
                )
                
                # Explicit commit (not handled by Flask-SQLAlchemy context manager)
                fresh_session.commit()
                self.logger.info(f"✅ SESSIONLESS: Enhanced posting completed")
                return result
                
        except Exception as e:
            self.logger.error(f"❌ SESSIONLESS: Enhanced posting failed: {str(e)}")
            
            # Try to mark as failed with a separate independent session
            try:
                fresh_engine2 = create_engine(get_database_url())
                FreshSession2 = sessionmaker(bind=fresh_engine2)
                
                with FreshSession2() as error_session:
                    self._mark_posting_failed(invoice_id, error_session, str(e))
                    error_session.commit()
            except Exception as mark_error:
                self.logger.error(f"❌ Failed to mark posting as failed: {str(mark_error)}")
                
            return {'status': 'error', 'error': str(e)}

    def _create_enhanced_invoice_posting_internal(
    self,
    invoice_id: uuid.UUID,
    current_user_id: str,
    session: Session
) -> Dict:
        """
        INTERNAL: Use existing unified posting methods instead of manual creation
        """
        
        try:
            # Get invoice
            invoice = session.query(SupplierInvoice).filter_by(invoice_id=invoice_id).first()
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")

            self.logger.info(f"Processing enhanced posting for {invoice.supplier_invoice_number}")
            
            # Use your existing unified posting method!
            return self._create_posting_entries(
                document_type='invoice',
                document=invoice,
                session=session,
                current_user_id=current_user_id
            )
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced invoice posting failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def create_enhanced_payment_posting(
        self,
        payment_id: uuid.UUID,
        session: Session,
        current_user_id: str
    ) -> Dict:
        """
        CONSOLIDATED: Create enhanced GL entries for payment
        Uses unified posting interface for consistency
        """
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}
        
        try:
            # Get payment
            payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")

            # Create posting using unified method
            return self._create_posting_entries(
                document_type='payment',
                document=payment,
                session=session,
                current_user_id=current_user_id
            )
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced payment posting failed: {str(e)}")
            self._mark_payment_posting_failed(payment_id, session, str(e))
            return {'status': 'error', 'error': str(e)}




    # ===================================================================
    # UNIFIED POSTING LOGIC - Eliminates Duplication
    # ===================================================================

    def _create_posting_entries(
        self,
        document_type: str,
        document,  # Either SupplierInvoice or SupplierPayment
        session: Session,
        current_user_id: str
    ) -> Dict:
        """
        UNIFIED: Create posting entries for both invoices and payments
        This method replaces all the duplicate posting logic
        """
        try:
            # Generate posting reference - FIXED to respect database field length limit
            doc_prefix = 'INV' if document_type == 'invoice' else 'PAY'
            doc_number = document.supplier_invoice_number if document_type == 'invoice' else document.reference_no
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            # CRITICAL FIX: Ensure posting reference fits in VARCHAR(50) database field
            base_reference = f"ENH-{doc_prefix}-{doc_number}-{timestamp}"
            
            # Truncate to 50 characters if too long (database constraint)
            if len(base_reference) > 50:
                # Keep the timestamp (14 chars) and truncate the middle part
                # Format: ENH-{PREFIX}-{TRUNCATED_DOC}-{TIMESTAMP}
                available_for_doc = 50 - len(f"ENH-{doc_prefix}--{timestamp}")  # Account for prefixes and separators
                if available_for_doc > 0:
                    truncated_doc = doc_number[:available_for_doc] if doc_number else ""
                    posting_reference = f"ENH-{doc_prefix}-{truncated_doc}-{timestamp}"
                else:
                    # Fallback: Use just prefix and timestamp
                    posting_reference = f"ENH-{doc_prefix}-{timestamp}"
                
                # Final safety check: ensure it's exactly 50 chars or less
                posting_reference = posting_reference[:50]
                
                self.logger.warning(f"Posting reference truncated from {len(base_reference)} to {len(posting_reference)} chars: {posting_reference}")
            else:
                posting_reference = base_reference
            
            # Create GL Transaction
            gl_transaction = self._create_gl_transaction(document_type, document, posting_reference, current_user_id)
            session.add(gl_transaction)
            session.flush()
            
            # Create entries based on document type
            all_entries = []
            
            if document_type == 'invoice':
                all_entries.extend(self._create_invoice_entries(document, gl_transaction, session, posting_reference, current_user_id))
            elif document_type == 'payment':
                all_entries.extend(self._create_payment_entries(document, gl_transaction, session, posting_reference, current_user_id))
            
            # Update transaction totals
            self._update_transaction_totals(gl_transaction, all_entries)
            
            # Mark as posted
            self._mark_document_as_posted(document_type, document, session, posting_reference)
            
            return {
                'status': 'success',
                'posting_reference': posting_reference,
                'transaction_id': str(gl_transaction.transaction_id),
                'entries_created': len(all_entries),
                'document_type': document_type,
                'message': f'Enhanced posting completed for {doc_number}'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Unified posting failed: {str(e)}")
            raise

    def _create_invoice_entries(
    self,
    invoice: SupplierInvoice,
    gl_transaction: GLTransaction,
    session: Session,
    posting_reference: str,
    current_user_id: str
) -> List[Dict]:
        """
        FIXED: Create all invoice-related entries with proper taxable amount calculation
        """
        entries = []
        hospital_id_str = str(invoice.hospital_id)
        
        # CRITICAL FIX: Calculate amounts instead of accessing non-existent fields
        total_amount = invoice.total_amount or Decimal('0')
        cgst_amount = invoice.cgst_amount or Decimal('0')
        sgst_amount = invoice.sgst_amount or Decimal('0')
        igst_amount = invoice.igst_amount or Decimal('0')
        
        # FIXED: Calculate taxable amount (this was the error)
        taxable_amount = total_amount - cgst_amount - sgst_amount - igst_amount
        
        # 1. Inventory/Expense Debit
        if taxable_amount > 0:
            inventory_entry = self._create_single_entry(
                session, gl_transaction, 'inventory', hospital_id_str,
                invoice.hospital_id, taxable_amount, Decimal('0'),
                f"Enhanced Inventory - {invoice.supplier_invoice_number}",
                'SUPPLIER_INVOICE', invoice.invoice_id, invoice.invoice_date,
                posting_reference, current_user_id
            )
            if inventory_entry:
                entries.append(inventory_entry)
        
        # 2. CGST Debit
        if cgst_amount > 0:
            cgst_entry = self._create_single_entry(
                session, gl_transaction, 'cgst', hospital_id_str,
                invoice.hospital_id, cgst_amount, Decimal('0'),
                f"Enhanced CGST - {invoice.supplier_invoice_number}",
                'SUPPLIER_INVOICE', invoice.invoice_id, invoice.invoice_date,
                posting_reference, current_user_id
            )
            if cgst_entry:
                entries.append(cgst_entry)
        
        # 3. SGST Debit
        if sgst_amount > 0:
            sgst_entry = self._create_single_entry(
                session, gl_transaction, 'sgst', hospital_id_str,
                invoice.hospital_id, sgst_amount, Decimal('0'),
                f"Enhanced SGST - {invoice.supplier_invoice_number}",
                'SUPPLIER_INVOICE', invoice.invoice_id, invoice.invoice_date,
                posting_reference, current_user_id
            )
            if sgst_entry:
                entries.append(sgst_entry)
        
        # 4. IGST Debit
        if igst_amount > 0:
            igst_entry = self._create_single_entry(
                session, gl_transaction, 'igst', hospital_id_str,
                invoice.hospital_id, igst_amount, Decimal('0'),
                f"Enhanced IGST - {invoice.supplier_invoice_number}",
                'SUPPLIER_INVOICE', invoice.invoice_id, invoice.invoice_date,
                posting_reference, current_user_id
            )
            if igst_entry:
                entries.append(igst_entry)
        
        # 5. AP Credit
        if total_amount > 0:
            ap_entry = self._create_single_entry(
                session, gl_transaction, 'ap', hospital_id_str,
                invoice.hospital_id, Decimal('0'), total_amount,
                f"Enhanced AP - {invoice.supplier_invoice_number}",
                'SUPPLIER_INVOICE', invoice.invoice_id, invoice.invoice_date,
                posting_reference, current_user_id
            )
            if ap_entry:
                entries.append(ap_entry)
                
                # Create AP Subledger
                self._create_ap_subledger(invoice, total_amount, session, posting_reference, current_user_id)
        
        return entries

    def _create_payment_entries(
    self,
    payment: SupplierPayment,
    gl_transaction: GLTransaction,
    session: Session,
    posting_reference: str,
    current_user_id: str
) -> List[Dict]:
        """
        CONSOLIDATED: Create all payment-related entries
        Replaces duplicate payment methods
        """
        entries = []
        hospital_id_str = str(payment.hospital_id)
        payment_amount = payment.amount or Decimal('0')
        
        # 1. AP Debit (reduce liability) - YOUR EXISTING CODE
        ap_entry = self._create_single_entry(
            session, gl_transaction, 'ap', hospital_id_str,
            payment.hospital_id, payment_amount, Decimal('0'),
            f"Enhanced AP Payment - {payment.reference_no}",
            'SUPPLIER_PAYMENT', payment.payment_id, payment.payment_date,
            posting_reference, current_user_id
        )
        if ap_entry:
            entries.append(ap_entry)
        
        # 2. Bank Credit (reduce asset) - YOUR EXISTING CODE
        bank_account_type = self._get_bank_account_type(payment.payment_method)
        bank_entry = self._create_single_entry(
            session, gl_transaction, bank_account_type, hospital_id_str,
            payment.hospital_id, Decimal('0'), payment_amount,
            f"Enhanced Payment - {payment.reference_no}",
            'SUPPLIER_PAYMENT', payment.payment_id, payment.payment_date,
            posting_reference, current_user_id
        )
        if bank_entry:
            entries.append(bank_entry)
        
        # *** NEW: ADD THIS ONE LINE to create AP subledger entry ***
        self._create_ap_subledger_payment_entry(session, payment, gl_transaction, posting_reference, current_user_id)
        
        return entries  # YOUR EXISTING RETURN

    def _create_ap_subledger_payment_entry(
    self,
    session: Session,
    payment: SupplierPayment,
    gl_transaction: GLTransaction,
    posting_reference: str,
    current_user_id: str
):
        """
        Create AP subledger entry for payment - CORRECTED for your model structure
        """
        try:
            from app.models.transaction import APSubledger
            from datetime import datetime, timezone
            from sqlalchemy import func
            
            payment_amount = payment.amount or Decimal('0')
            
            self.logger.info(f"🔄 AP SUBLEDGER: Creating payment entry for supplier {payment.supplier_id}")
            self.logger.info(f"🔄 AP SUBLEDGER: Payment amount: {payment_amount}")
            
            # Calculate current AP balance for this supplier
            current_balance = session.query(func.coalesce(func.sum(
                APSubledger.credit_amount - APSubledger.debit_amount
            ), 0)).filter_by(
                hospital_id=payment.hospital_id,
                supplier_id=payment.supplier_id
            ).scalar() or Decimal('0')
            
            # New balance after payment (reduces what we owe)
            new_balance = current_balance - payment_amount
            
            self.logger.info(f"🔄 AP SUBLEDGER: Current balance: {current_balance}")
            self.logger.info(f"🔄 AP SUBLEDGER: New balance after payment: {new_balance}")
            
            # Create AP subledger entry for payment - CORRECTED to match your model
            ap_entry = APSubledger(
                hospital_id=payment.hospital_id,
                branch_id=payment.branch_id,
                
                # Transaction details
                transaction_date=payment.payment_date or datetime.now(timezone.utc),
                entry_type='payment',  # Matches your model: 'invoice', 'payment', 'adjustment', 'advance'
                
                # Reference information - CORRECTED to use your model fields
                reference_id=payment.payment_id,      # Payment UUID
                reference_type='payment',             # 'invoice', 'payment', or 'advance'
                reference_number=payment.reference_no or str(payment.payment_id)[:8],  # Payment reference
                
                # Supplier Information
                supplier_id=payment.supplier_id,
                
                # Amount Information - PAYMENT = DEBIT (reduces what we owe)
                debit_amount=payment_amount,
                credit_amount=Decimal('0'),
                
                # Balance tracking
                current_balance=new_balance,
                
                # GL Reference - link to the GL transaction
                gl_transaction_id=gl_transaction.transaction_id,
                
                # Audit fields
                created_by=current_user_id,
                created_at=datetime.now(timezone.utc)
            )
            
            session.add(ap_entry)
            session.flush()
            
            self.logger.info(f"✅ AP SUBLEDGER: Created payment entry")
            self.logger.info(f"   - Reference ID: {payment.payment_id}")
            self.logger.info(f"   - Reference Type: payment")
            self.logger.info(f"   - Debit Amount: {payment_amount}")
            self.logger.info(f"   - New Balance: {new_balance}")
            
        except Exception as e:
            self.logger.error(f"❌ AP SUBLEDGER: Error creating payment entry: {str(e)}")
            self.logger.error(f"❌ AP SUBLEDGER: Full traceback:", exc_info=True)
            # Don't re-raise - we don't want to fail the entire posting

    # ===================================================================
    # UNIFIED HELPER METHODS - No More Duplication
    # ===================================================================

    def _create_single_entry(
        self,
        session: Session,
        gl_transaction: GLTransaction,
        account_type: str,
        hospital_id_str: str,
        hospital_id: uuid.UUID,
        debit_amount: Decimal,
        credit_amount: Decimal,
        description: str,
        source_document_type: str,
        source_document_id: uuid.UUID,
        entry_date,
        posting_reference: str,
        current_user_id: str
    ) -> Optional[Dict]:
        """
        UNIFIED: Create a single GL entry
        This method replaces all the duplicate entry creation logic
        """
        try:
            # Get account using smart lookup (now fixed!)
            account_no = get_default_gl_account(account_type, hospital_id_str)
            
            account = session.query(ChartOfAccounts).filter_by(
                hospital_id=hospital_id,
                gl_account_no=account_no,
                is_active=True
            ).first()
            
            if not account:
                self.logger.error(f"❌ Account {account_no} for type {account_type} not found")
                return None
            
            # Create GL entry
            gl_entry = GLEntry(
                hospital_id=hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=account.account_id,
                entry_date=entry_date,
                description=description,
                debit_amount=debit_amount,
                credit_amount=credit_amount,
                source_document_type=source_document_type,
                source_document_id=source_document_id,
                posting_reference=posting_reference,
                created_by=current_user_id
            )
            
            session.add(gl_entry)
            session.flush()
            
            self.logger.info(f"✅ Created {account_type} entry: {account_no} - Debit: {debit_amount}, Credit: {credit_amount}")
            
            return {
                'type': account_type,
                'account_no': account_no,
                'account_name': account.account_name,
                'debit_amount': float(debit_amount),
                'credit_amount': float(credit_amount),
                'entry_id': str(gl_entry.entry_id)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error creating {account_type} entry: {str(e)}")
            return None

    def _create_gl_transaction(
    self,
    document_type: str,
    document,
    posting_reference: str,
    current_user_id: str
) -> GLTransaction:
        """
        FIXED: Create GL transaction with proper total initialization
        Maintains separation of concerns - this method only handles GL transaction creation
        """
        # CRITICAL FIX: Calculate and set totals immediately based on document type
        if document_type == 'invoice':
            total_amount = document.total_amount or Decimal('0')
            
            return GLTransaction(
                hospital_id=document.hospital_id,
                transaction_date=document.invoice_date,
                transaction_type='SUPPLIER_INVOICE_ENHANCED',
                reference_id=str(document.invoice_id),
                description=f"Enhanced Invoice - {document.supplier_invoice_number}",
                source_document_type='SUPPLIER_INVOICE',
                source_document_id=document.invoice_id,
                total_debit=total_amount,    # FIXED: Initialize with actual amount
                total_credit=total_amount,   # FIXED: Initialize with actual amount
                created_by=current_user_id
            )
        else:  # payment
            payment_amount = document.amount or Decimal('0')
            
            return GLTransaction(
                hospital_id=document.hospital_id,
                transaction_date=document.payment_date or datetime.now().date(),
                transaction_type='SUPPLIER_PAYMENT_ENHANCED',
                reference_id=str(document.payment_id),
                description=f"Enhanced Payment - {document.reference_no}",
                source_document_type='SUPPLIER_PAYMENT',
                source_document_id=document.payment_id,
                total_debit=payment_amount,   # FIXED: Initialize with actual amount
                total_credit=payment_amount,  # FIXED: Initialize with actual amount
                created_by=current_user_id
            )

    def _create_ap_subledger(
    self,
    invoice: SupplierInvoice,
    amount: Decimal,
    session: Session,
    posting_reference: str,
    current_user_id: str
):
        """
        FIXED: Create AP subledger entry with correct field names
        Based on working enhanced_posting_helper 13.06.py
        """
        try:
            # Get the GL transaction for linking (if needed)
            gl_transaction = session.query(GLTransaction).filter_by(
                source_document_id=invoice.invoice_id,
                source_document_type='SUPPLIER_INVOICE'
            ).order_by(GLTransaction.created_at.desc()).first()
            
            ap_subledger_entry = APSubledger(
                hospital_id=invoice.hospital_id,
                branch_id=invoice.branch_id,  # FIXED: Use branch_id instead of supplier_id
                transaction_date=invoice.invoice_date,  # FIXED: Use transaction_date instead of entry_date
                entry_type='invoice',  # FIXED: Add entry_type
                reference_id=invoice.invoice_id,  # FIXED: Use reference_id instead of invoice_id
                reference_type='invoice',  # FIXED: Add reference_type
                reference_number=invoice.supplier_invoice_number,  # FIXED: Add reference_number
                supplier_id=invoice.supplier_id,  # Keep supplier_id
                debit_amount=Decimal('0'),
                credit_amount=amount,
                current_balance=amount,  # FIXED: Use current_balance instead of balance_amount
                gl_transaction_id=gl_transaction.transaction_id if gl_transaction else None,  # FIXED: Link to GL transaction
                created_by=current_user_id
            )
            
            session.add(ap_subledger_entry)
            session.flush()
            
            self.logger.info(f"✅ Created AP subledger entry: {amount}")
            
        except Exception as e:
            self.logger.error(f"❌ AP Subledger creation failed: {str(e)}")

    def _update_transaction_totals(self, gl_transaction: GLTransaction, entries: List[Dict]):
        """
        OPTIONAL: Fine-tune GL transaction totals based on actual entries created
        This is now optional since we initialize with correct amounts
        """
        if not entries:
            return
            
        total_debits = sum(Decimal(str(entry.get('debit_amount', 0))) for entry in entries)
        total_credits = sum(Decimal(str(entry.get('credit_amount', 0))) for entry in entries)
        
        # Only update if there's a significant difference (precision adjustment)
        if abs(gl_transaction.total_debit - total_debits) > Decimal('0.01'):
            gl_transaction.total_debit = total_debits
            
        if abs(gl_transaction.total_credit - total_credits) > Decimal('0.01'):
            gl_transaction.total_credit = total_credits

    def _mark_document_as_posted(
        self,
        document_type: str,
        document,
        session: Session,
        posting_reference: str
    ):
        """
        UNIFIED: Mark document as posted
        """
        if document_type == 'invoice':
            self._mark_invoice_as_posted(document.invoice_id, session, posting_reference)
        else:  # payment
            self._mark_payment_as_posted(document.payment_id, session, posting_reference)

    def _get_bank_account_type(self, payment_method: str) -> str:
        """
        UNIFIED: Get bank account type for payment method
        """
        method_mapping = {
            'cash': 'cash',
            'bank_transfer': 'bank',
            'cheque': 'bank',
            'credit_card': 'bank',
            'digital_wallet': 'bank',
        }
        return method_mapping.get(payment_method, 'bank')

    # ===================================================================
    # LEGACY METHODS - Keep for backward compatibility
    # ===================================================================

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

    # ===================================================================
    # RETIRED METHODS - Remove these from your code
    # ===================================================================
    
    # ❌ create_enhanced_invoice_posting_fixed() - RETIRED
    # ❌ _create_ap_entries_with_transaction() - RETIRED  
    # ❌ _create_ap_entries_with_fresh_session() - RETIRED
    # ❌ Multiple duplicate helper methods - RETIRED
    
    # All functionality is now handled by the unified methods above

    def create_enhanced_payment_posting_debug(
    self,
    payment_id: uuid.UUID,
    session: Session,
    current_user_id: str
) -> Dict:
        """
        DEBUGGING VERSION: Create enhanced GL entries for payment with extensive logging
        """
        self.logger.info(f"🔄 ENHANCED POSTING DEBUG: Starting payment posting for {payment_id}")
        
        if not self.enabled:
            self.logger.info("ℹ️ ENHANCED POSTING DEBUG: Enhanced posting disabled in configuration")
            return {'status': 'disabled', 'message': 'Enhanced posting disabled'}
        
        try:
            # Get payment with detailed logging
            self.logger.info(f"🔍 ENHANCED POSTING DEBUG: Fetching payment {payment_id}")
            payment = session.query(SupplierPayment).filter_by(payment_id=payment_id).first()
            if not payment:
                self.logger.error(f"❌ ENHANCED POSTING DEBUG: Payment {payment_id} not found")
                raise ValueError(f"Payment {payment_id} not found")
            
            self.logger.info(f"✅ ENHANCED POSTING DEBUG: Found payment:")
            self.logger.info(f"   - Amount: {payment.amount}")
            self.logger.info(f"   - Method: {payment.payment_method}")
            self.logger.info(f"   - Hospital: {payment.hospital_id}")
            self.logger.info(f"   - Branch: {payment.branch_id}")
            self.logger.info(f"   - Status: {payment.workflow_status}")

            # Check configuration
            from app.services.posting_config_service import get_posting_config
            config = get_posting_config(str(payment.hospital_id))
            self.logger.info(f"🔍 ENHANCED POSTING DEBUG: Configuration:")
            self.logger.info(f"   - ENABLE_ENHANCED_POSTING: {config.get('ENABLE_ENHANCED_POSTING')}")
            self.logger.info(f"   - DEFAULT_AP_ACCOUNT: {config.get('DEFAULT_AP_ACCOUNT')}")
            self.logger.info(f"   - DEFAULT_CASH_ACCOUNT: {config.get('DEFAULT_CASH_ACCOUNT')}")

            # Create posting using unified method
            self.logger.info(f"🔄 ENHANCED POSTING DEBUG: Creating posting entries")
            result = self._create_posting_entries(
                document_type='payment',
                document=payment,
                session=session,
                current_user_id=current_user_id
            )
            
            self.logger.info(f"✅ ENHANCED POSTING DEBUG: Posting completed successfully")
            self.logger.info(f"✅ ENHANCED POSTING DEBUG: Result: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ ENHANCED POSTING DEBUG: Payment posting failed: {str(e)}")
            self.logger.error("❌ ENHANCED POSTING DEBUG: Full traceback:", exc_info=True)
            self._mark_payment_posting_failed(payment_id, session, str(e))
            return {'status': 'error', 'error': str(e)}


# 2. ADD THIS FUNCTION AT THE END of enhanced_posting_helper.py (outside the class)
def check_enhanced_posting_config():
    """
    Check if enhanced posting is properly configured
    """
    logger = get_unicode_safe_logger(__name__)
    
    try:
        from app.services.posting_config_service import get_posting_config, is_enhanced_posting_enabled
        
        config = get_posting_config()
        logger.info("🔍 CONFIG CHECK: Enhanced posting configuration:")
        logger.info(f"🔍 CONFIG CHECK:   ENABLE_ENHANCED_POSTING = {config.get('ENABLE_ENHANCED_POSTING')}")
        logger.info(f"🔍 CONFIG CHECK:   DEFAULT_AP_ACCOUNT = {config.get('DEFAULT_AP_ACCOUNT')}")
        logger.info(f"🔍 CONFIG CHECK:   DEFAULT_CASH_ACCOUNT = {config.get('DEFAULT_CASH_ACCOUNT')}")
        logger.info(f"🔍 CONFIG CHECK:   DEFAULT_BANK_ACCOUNT = {config.get('DEFAULT_BANK_ACCOUNT')}")
        
        # Check if helper is enabled
        helper = EnhancedPostingHelper()
        logger.info(f"🔍 CONFIG CHECK:   EnhancedPostingHelper.enabled = {helper.enabled}")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ CONFIG CHECK: Error checking configuration: {str(e)}")
        return None