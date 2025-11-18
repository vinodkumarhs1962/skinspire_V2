"""
AR Statement Service
Service layer for patient AR (Accounts Receivable) statement operations

Handles:
- Fetching complete patient transaction history
- Calculating AR balances and totals
- Formatting AR statement data for display

Version: 1.0
Created: 2025-11-13
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, Any, List

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.transaction import ARSubledger, InvoiceHeader, PatientCreditNote
from app.models.master import Patient
from app.services.database_service import get_db_session, get_entity_dict

logger = logging.getLogger(__name__)


class ARStatementService:
    """Service for managing patient AR statements"""

    def get_patient_ar_statement(
        self,
        patient_id: str,
        hospital_id: str,
        highlight_reference_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete AR statement for a patient with all transactions

        Args:
            patient_id: Patient ID
            hospital_id: Hospital ID
            highlight_reference_id: Optional transaction ID to highlight
                (invoice_id, payment_id, credit_note_id, or plan_id)

        Returns:
            {
                'patient_info': {
                    'patient_id': str,
                    'full_name': str,
                    'patient_number': str,
                    'phone_number': str
                },
                'transactions': [
                    {
                        'transaction_date': str (ISO format),
                        'entry_type': str,
                        'reference_type': str,
                        'reference_number': str,
                        'reference_id': str,
                        'debit_amount': str (formatted),
                        'credit_amount': str (formatted),
                        'current_balance': str (formatted),
                        'is_highlighted': bool
                    }
                ],
                'summary': {
                    'total_invoiced': str,
                    'total_paid': str,
                    'total_credit_notes': str,
                    'current_balance': str,
                    'balance_type': 'credit' or 'debit'
                },
                'as_of_date': str (ISO format),
                'success': bool
            }
        """
        try:
            with get_db_session() as session:
                # Get patient info
                patient = session.query(Patient).filter(
                    and_(
                        Patient.patient_id == patient_id,
                        Patient.hospital_id == hospital_id
                    )
                ).first()

                if not patient:
                    return {
                        'success': False,
                        'error': 'Patient not found'
                    }

                # Extract phone number from contact_info JSONB field
                phone_number = ''
                if patient.contact_info:
                    if isinstance(patient.contact_info, dict):
                        phone_number = patient.contact_info.get('phone', '')
                    elif isinstance(patient.contact_info, str):
                        try:
                            import json
                            contact_info = json.loads(patient.contact_info)
                            phone_number = contact_info.get('phone', '')
                        except:
                            pass

                patient_info = {
                    'patient_id': str(patient.patient_id),
                    'full_name': patient.full_name,
                    'patient_number': patient.mrn or '',  # MRN is the patient number
                    'phone_number': phone_number
                }

                # Get all AR transactions for patient
                ar_entries = session.query(ARSubledger).filter(
                    and_(
                        ARSubledger.patient_id == patient_id,
                        ARSubledger.hospital_id == hospital_id
                    )
                ).order_by(
                    ARSubledger.transaction_date,
                    ARSubledger.created_at
                ).all()

                # Format transactions for display
                transactions = []
                total_invoiced = Decimal('0.00')
                total_paid = Decimal('0.00')
                total_credit_notes = Decimal('0.00')

                for entry in ar_entries:
                    # Determine if this transaction should be highlighted
                    is_highlighted = False
                    if highlight_reference_id:
                        # Check if this AR entry matches the highlight ID
                        if entry.reference_id == highlight_reference_id:
                            is_highlighted = True
                        # For package plans, highlight the related invoice or credit note
                        elif entry.reference_type == 'invoice':
                            # Check if invoice is related to package plan
                            invoice = session.query(InvoiceHeader).filter(
                                InvoiceHeader.invoice_id == entry.reference_id
                            ).first()
                            if invoice and hasattr(invoice, 'package_plan_id'):
                                if str(invoice.package_plan_id) == highlight_reference_id:
                                    is_highlighted = True
                        elif entry.reference_type == 'credit_note':
                            # Check if credit note is related to package plan
                            credit_note = session.query(PatientCreditNote).filter(
                                PatientCreditNote.credit_note_id == entry.reference_id
                            ).first()
                            if credit_note and credit_note.plan_id:
                                if str(credit_note.plan_id) == highlight_reference_id:
                                    is_highlighted = True

                    # Accumulate totals
                    if entry.entry_type == 'invoice':
                        total_invoiced += entry.debit_amount
                    elif entry.entry_type == 'payment':
                        total_paid += entry.credit_amount
                    elif entry.entry_type == 'credit_note':
                        total_credit_notes += entry.credit_amount

                    # Format transaction
                    transaction = {
                        'transaction_date': entry.transaction_date.isoformat() if entry.transaction_date else '',
                        'entry_type': entry.entry_type,
                        'reference_type': entry.reference_type,
                        'reference_number': entry.reference_number or '',
                        'reference_id': str(entry.reference_id) if entry.reference_id else '',
                        'debit_amount': str(entry.debit_amount) if entry.debit_amount else '0.00',
                        'credit_amount': str(entry.credit_amount) if entry.credit_amount else '0.00',
                        'current_balance': str(entry.current_balance) if entry.current_balance else '0.00',
                        'is_highlighted': is_highlighted
                    }
                    transactions.append(transaction)

                # Calculate current balance
                current_balance = total_invoiced - total_paid - total_credit_notes
                balance_type = 'credit' if current_balance < 0 else 'debit'

                # Format summary
                summary = {
                    'total_invoiced': str(total_invoiced),
                    'total_paid': str(total_paid),
                    'total_credit_notes': str(total_credit_notes),
                    'current_balance': str(current_balance),
                    'balance_type': balance_type
                }

                return {
                    'success': True,
                    'patient_info': patient_info,
                    'transactions': transactions,
                    'summary': summary,
                    'as_of_date': date.today().isoformat()
                }

        except Exception as e:
            logger.error(f"Error fetching AR statement for patient {patient_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to fetch AR statement: {str(e)}'
            }

    def get_patient_balance(
        self,
        patient_id: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Get current balance for a patient (quick query)

        Args:
            patient_id: Patient ID
            hospital_id: Hospital ID

        Returns:
            {
                'success': bool,
                'current_balance': Decimal,
                'balance_type': 'credit' or 'debit'
            }
        """
        try:
            with get_db_session() as session:
                # Get most recent AR entry
                latest_entry = session.query(ARSubledger).filter(
                    and_(
                        ARSubledger.patient_id == patient_id,
                        ARSubledger.hospital_id == hospital_id
                    )
                ).order_by(
                    ARSubledger.transaction_date.desc(),
                    ARSubledger.created_at.desc()
                ).first()

                if not latest_entry:
                    return {
                        'success': True,
                        'current_balance': Decimal('0.00'),
                        'balance_type': 'none'
                    }

                current_balance = latest_entry.current_balance or Decimal('0.00')
                balance_type = 'credit' if current_balance < 0 else 'debit'

                return {
                    'success': True,
                    'current_balance': current_balance,
                    'balance_type': balance_type
                }

        except Exception as e:
            logger.error(f"Error fetching patient balance: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
