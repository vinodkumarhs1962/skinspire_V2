"""
Patient Credit Note Service
Service layer for patient credit note operations

Handles:
- Credit note creation for package discontinuations and adjustments
- AR subledger credit entries
- GL transaction and entry posting
- Credit note number generation

Version: 1.0
Created: 2025-11-12
"""

import logging
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional, Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from app.models.transaction import PatientCreditNote, InvoiceHeader, PackagePaymentPlan, GLTransaction, GLEntry, ARSubledger
from app.models.master import Patient, ChartOfAccounts
from app.services.database_service import get_db_session

logger = logging.getLogger(__name__)


class PatientCreditNoteService:
    """Service for managing patient credit notes"""

    def generate_credit_note_number(self, hospital_id: str, branch_id: Optional[str] = None, session=None) -> str:
        """
        Generate next credit note number for the hospital
        Format: CN/YYYY-YYYY/NNNNN (e.g., CN/2025-2026/00001)

        Args:
            hospital_id: Hospital ID
            branch_id: Optional branch ID
            session: Optional database session (if called from within a transaction)

        Returns:
            Credit note number string
        """
        def _generate_number(db_session):
            # Get current financial year
            today = date.today()
            if today.month >= 4:  # April onwards = current FY
                fy_start = today.year
                fy_end = today.year + 1
            else:  # Jan-Mar = previous FY
                fy_start = today.year - 1
                fy_end = today.year

            fy_string = f"{fy_start}-{fy_end}"

            # Get last credit note number for this FY
            last_credit_note = db_session.query(PatientCreditNote).filter(
                and_(
                    PatientCreditNote.hospital_id == hospital_id,
                    PatientCreditNote.credit_note_number.like(f'CN/{fy_string}/%')
                )
            ).order_by(PatientCreditNote.credit_note_number.desc()).first()

            if last_credit_note:
                # Extract sequence number and increment
                last_number = last_credit_note.credit_note_number.split('/')[-1]
                next_sequence = int(last_number) + 1
            else:
                next_sequence = 1

            credit_note_number = f"CN/{fy_string}/{next_sequence:05d}"
            logger.info(f"Generated credit note number: {credit_note_number}")

            return credit_note_number

        try:
            # If session provided, use it directly (avoid nested session)
            if session is not None:
                return _generate_number(session)
            else:
                # Open new session only if not provided
                with get_db_session() as new_session:
                    return _generate_number(new_session)

        except Exception as e:
            logger.error(f"Error generating credit note number: {str(e)}", exc_info=True)
            # Fallback to UUID-based number
            return f"CN/TEMP/{str(uuid.uuid4())[:8].upper()}"

    def create_credit_note(
        self,
        hospital_id: str,
        branch_id: Optional[str],
        original_invoice_id: str,
        patient_id: str,
        total_amount: Decimal,
        reason_code: str,
        reason_description: str,
        plan_id: Optional[str] = None,
        user_id: Optional[str] = None,
        credit_note_date: Optional[date] = None,
        auto_post: bool = True,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Create a credit note against a patient invoice

        Args:
            hospital_id: Hospital ID
            branch_id: Branch ID
            original_invoice_id: Original invoice ID
            patient_id: Patient ID
            total_amount: Credit note amount
            reason_code: Reason code (plan_discontinued, etc.)
            reason_description: Detailed reason
            plan_id: Optional package plan ID
            user_id: User creating credit note
            credit_note_date: Credit note date (defaults to today)
            auto_post: Whether to auto-post GL entries
            session: Database session (optional, to avoid nested sessions)

        Returns:
            {
                'success': bool,
                'credit_note_id': str,
                'credit_note_number': str,
                'ar_entry_id': str,
                'gl_transaction_id': str,
                'message': str
            }
        """
        try:
            with get_db_session() as session:
                # Validate invoice exists
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == original_invoice_id
                ).first()

                if not invoice:
                    return {
                        'success': False,
                        'error': 'Original invoice not found'
                    }

                # Generate credit note number
                credit_note_number = self.generate_credit_note_number(hospital_id, branch_id)

                # Create credit note
                credit_note = PatientCreditNote(
                    credit_note_id=uuid.uuid4(),
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    credit_note_number=credit_note_number,
                    original_invoice_id=original_invoice_id,
                    plan_id=plan_id,
                    patient_id=patient_id,
                    credit_note_date=credit_note_date or date.today(),
                    total_amount=total_amount,
                    reason_code=reason_code,
                    reason_description=reason_description,
                    status='draft',
                    created_at=datetime.utcnow(),
                    created_by=user_id
                )

                session.add(credit_note)
                session.flush()  # Get credit_note_id

                logger.info(f" Created credit note {credit_note_number} for �{total_amount}")

                # Post AR and GL if auto_post enabled
                ar_entry_id = None
                gl_transaction_id = None

                if auto_post:
                    # Create AR credit entry
                    ar_result = self._create_ar_credit_entry(
                        credit_note=credit_note,
                        invoice=invoice,
                        session=session,
                        user_id=user_id
                    )

                    if ar_result['success']:
                        ar_entry_id = ar_result['entry_id']
                        logger.info(f" Created AR credit entry: {ar_entry_id}")
                    else:
                        logger.error(f"Failed to create AR entry: {ar_result.get('error')}")

                    # Create GL transaction
                    gl_result = self._create_gl_transaction(
                        credit_note=credit_note,
                        invoice=invoice,
                        session=session,
                        user_id=user_id
                    )

                    if gl_result['success']:
                        gl_transaction_id = gl_result['transaction_id']

                        # Update credit note with GL reference
                        credit_note.gl_posted = True
                        credit_note.gl_transaction_id = gl_transaction_id
                        credit_note.posted_at = datetime.utcnow()
                        credit_note.posted_by = user_id
                        credit_note.status = 'posted'

                        logger.info(f" Created GL transaction: {gl_transaction_id}")
                    else:
                        logger.error(f"Failed to create GL transaction: {gl_result.get('error')}")
                        credit_note.status = 'approved'  # Approved but not posted

                session.commit()

                return {
                    'success': True,
                    'credit_note_id': str(credit_note.credit_note_id),
                    'credit_note_number': credit_note_number,
                    'ar_entry_id': ar_entry_id,
                    'gl_transaction_id': gl_transaction_id,
                    'message': f'Credit note {credit_note_number} created successfully'
                }

        except Exception as e:
            logger.error(f"Error creating credit note: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to create credit note: {str(e)}'
            }

    def _create_ar_credit_entry(
        self,
        credit_note: PatientCreditNote,
        invoice: InvoiceHeader,
        session,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create AR subledger credit entry for credit note
        This reduces the patient's receivable balance
        """
        try:
            # Get current patient balance
            current_balance = session.query(
                func.coalesce(func.sum(ARSubledger.debit_amount), 0) -
                func.coalesce(func.sum(ARSubledger.credit_amount), 0)
            ).filter(
                and_(
                    ARSubledger.hospital_id == credit_note.hospital_id,
                    ARSubledger.patient_id == credit_note.patient_id
                )
            ).scalar() or Decimal('0')

            # Calculate new balance after credit
            new_balance = current_balance - credit_note.total_amount

            ar_entry = ARSubledger(
                entry_id=uuid.uuid4(),
                hospital_id=credit_note.hospital_id,
                branch_id=credit_note.branch_id,
                transaction_date=credit_note.credit_note_date,
                entry_type='credit_note',
                reference_id=str(credit_note.credit_note_id),
                reference_type='credit_note',
                reference_number=credit_note.credit_note_number,
                patient_id=credit_note.patient_id,
                debit_amount=Decimal('0.00'),
                credit_amount=credit_note.total_amount,
                current_balance=new_balance,
                gl_transaction_id=None,  # Will be updated when GL is posted
                created_at=datetime.utcnow(),
                created_by=user_id
            )

            session.add(ar_entry)
            session.flush()

            logger.info(f" AR credit entry created: �{credit_note.total_amount}, New balance: �{new_balance}")
            return {
                'success': True,
                'entry_id': str(ar_entry.entry_id),
                'previous_balance': float(current_balance),
                'new_balance': float(new_balance)
            }

        except Exception as e:
            logger.error(f"Error creating AR entry: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _create_gl_transaction(
        self,
        credit_note: PatientCreditNote,
        invoice: InvoiceHeader,
        session,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create GL transaction and entries for credit note

        GL Entries:
          Dr: Package Revenue (4200) - Reduce income
          Cr: Accounts Receivable (1100) - Reduce receivable
        """
        try:
            # Find Package Revenue account (4200)
            revenue_account = session.query(ChartOfAccounts).filter(
                and_(
                    ChartOfAccounts.hospital_id == credit_note.hospital_id,
                    ChartOfAccounts.gl_account_no == '4200',
                    ChartOfAccounts.is_active == True
                )
            ).first()

            # Find AR account (1100 - Accounts Receivable)
            ar_account = session.query(ChartOfAccounts).filter(
                and_(
                    ChartOfAccounts.hospital_id == credit_note.hospital_id,
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
                        ChartOfAccounts.hospital_id == credit_note.hospital_id,
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
                created_by=user_id,
                updated_by=user_id
            )

            session.add(gl_transaction)
            session.flush()

            # Create GL entries
            gl_entries = []

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
                created_by=user_id
            )
            session.add(revenue_entry)
            gl_entries.append(revenue_entry)

            # Entry 2: Credit AR (reduce receivable)
            ar_entry = GLEntry(
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
                created_by=user_id
            )
            session.add(ar_entry)
            gl_entries.append(ar_entry)

            session.flush()

            logger.info(f" GL entries created: Dr {revenue_account.account_name} �{credit_note.total_amount}, Cr {ar_account.account_name} �{credit_note.total_amount}")
            return {
                'success': True,
                'transaction_id': str(gl_transaction.transaction_id),
                'entries_count': len(gl_entries),
                'revenue_account': revenue_account.account_name,
                'ar_account': ar_account.account_name
            }

        except Exception as e:
            logger.error(f"Error creating GL transaction: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_credit_note_by_id(
        self,
        credit_note_id: str,
        hospital_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get credit note by ID"""
        try:
            with get_db_session() as session:
                credit_note = session.query(PatientCreditNote).filter(
                    and_(
                        PatientCreditNote.credit_note_id == credit_note_id,
                        PatientCreditNote.hospital_id == hospital_id
                    )
                ).first()

                if not credit_note:
                    return None

                from app.services.database_service import to_dict
                return to_dict(credit_note)

        except Exception as e:
            logger.error(f"Error fetching credit note: {str(e)}", exc_info=True)
            return None
