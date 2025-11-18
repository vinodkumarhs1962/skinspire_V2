# Patient API Enhancement for Payment Form Header
# This creates a new endpoint for fetching detailed patient info for payment form

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.services.database_service import get_db_session, get_entity_dict
from app.models.master import Patient
from sqlalchemy import func
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

patient_info_bp = Blueprint('patient_info_api', __name__, url_prefix='/api/patient')


@patient_info_bp.route('/<patient_id>/payment-summary', methods=['GET'])
@login_required
def get_patient_payment_summary(patient_id):
    """
    Get comprehensive patient information for payment form header

    Returns:
        - Basic patient info (name, MRN, contact)
        - Financial summary (total outstanding, advance balance)
        - Outstanding invoices count
        - Pending installments count
    """
    try:
        from app.services.billing_service import get_patient_advance_balance
        from app.models.transaction import InvoiceHeader, PackagePaymentPlan, InstallmentPayment

        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            # Get patient details
            patient = session.query(Patient).filter_by(
                hospital_id=hospital_id,
                patient_id=patient_id
            ).first()

            if not patient:
                return jsonify({
                    'success': False,
                    'error': 'Patient not found'
                }), 404

            # Get basic patient info
            patient_dict = get_entity_dict(patient)

            # Get financial summary
            # 1. Total outstanding invoices
            total_outstanding = session.query(
                func.sum(InvoiceHeader.balance_due)
            ).filter(
                InvoiceHeader.hospital_id == hospital_id,
                InvoiceHeader.patient_id == patient_id,
                InvoiceHeader.is_cancelled == False,
                InvoiceHeader.balance_due > 0
            ).scalar() or Decimal('0')

            # 2. Outstanding invoices count
            outstanding_count = session.query(InvoiceHeader).filter(
                InvoiceHeader.hospital_id == hospital_id,
                InvoiceHeader.patient_id == patient_id,
                InvoiceHeader.is_cancelled == False,
                InvoiceHeader.balance_due > 0
            ).count()

            # 3. Pending installments count
            pending_installments = session.query(InstallmentPayment).join(
                PackagePaymentPlan,
                InstallmentPayment.plan_id == PackagePaymentPlan.plan_id
            ).filter(
                PackagePaymentPlan.patient_id == patient_id,
                PackagePaymentPlan.status == 'active',
                InstallmentPayment.status.in_(['pending', 'partial', 'overdue'])
            ).count()

        # 4. Advance balance (use existing service)
        advance_balance = get_patient_advance_balance(
            hospital_id=hospital_id,
            patient_id=patient_id
        )

        # Extract contact info
        contact_info = patient_dict.get('contact_info', {})
        if isinstance(contact_info, str):
            import json
            try:
                contact_info = json.loads(contact_info)
            except:
                contact_info = {}

        personal_info = patient_dict.get('personal_info', {})
        if isinstance(personal_info, str):
            import json
            try:
                personal_info = json.loads(personal_info)
            except:
                personal_info = {}

        return jsonify({
            'success': True,
            'patient': {
                'patient_id': str(patient_dict['patient_id']),
                'mrn': patient_dict.get('mrn', 'N/A'),
                'name': patient.full_name,  # Using hybrid property
                'phone': contact_info.get('phone', 'N/A'),
                'email': contact_info.get('email', 'N/A'),
                'age': personal_info.get('age'),
                'gender': personal_info.get('gender'),
            },
            'financial_summary': {
                'total_outstanding': float(total_outstanding),
                'advance_balance': float(advance_balance),
                'net_due': float(total_outstanding - advance_balance),
                'outstanding_invoices_count': outstanding_count,
                'pending_installments_count': pending_installments
            }
        })

    except Exception as e:
        logger.error(f"Error fetching patient payment summary: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch patient summary',
            'message': str(e)
        }), 500
