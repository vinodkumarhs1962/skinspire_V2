"""
Package API Routes
API endpoints for package payment plan operations

Version: 1.0
Created: 2025-01-11
"""

import logging
from flask import Blueprint, request, jsonify, g
from flask_login import login_required, current_user

from app.services.package_payment_service import PackagePaymentService
from app import csrf  # Import CSRF protection

logger = logging.getLogger(__name__)

# Create blueprint
package_api_bp = Blueprint('package_api', __name__, url_prefix='/api/package')


@package_api_bp.route('/session/<session_id>/date', methods=['PATCH'])
@login_required
def update_session_date(session_id):
    """
    Update session scheduled date (rescheduling)

    PATCH /api/package/session/<session_id>/date

    Request Body:
    {
        "session_date": "2025-11-18"
    }

    Response:
    {
        "success": true,
        "session_id": "uuid",
        "message": "Session date updated successfully"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        session_date = data.get('session_date')

        if not session_date:
            return jsonify({
                'success': False,
                'error': 'Missing required field: session_date'
            }), 400

        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session'
            }), 400

        # Get service
        service = PackagePaymentService()

        # Update session date
        result = service.update_session_date(
            session_id=session_id,
            session_date=session_date,
            hospital_id=hospital_id
        )

        if result['success']:
            logger.info(f"Session {session_id} date updated by {current_user.user_id}")
            return jsonify(result), 200
        else:
            logger.error(f"Failed to update session {session_id} date: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error updating session date: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@package_api_bp.route('/installment/<installment_id>/date', methods=['PATCH'])
@login_required
def update_installment_date(installment_id):
    """
    Update installment due date (rescheduling)

    PATCH /api/package/installment/<installment_id>/date

    Request Body:
    {
        "due_date": "2025-11-18"
    }

    Response:
    {
        "success": true,
        "installment_id": "uuid",
        "message": "Installment due date updated successfully"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        due_date = data.get('due_date')

        if not due_date:
            return jsonify({
                'success': False,
                'error': 'Missing required field: due_date'
            }), 400

        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session'
            }), 400

        # Get service
        service = PackagePaymentService()

        # Update installment due date
        result = service.update_installment_due_date(
            installment_id=installment_id,
            due_date=due_date,
            hospital_id=hospital_id
        )

        if result['success']:
            logger.info(f"Installment {installment_id} due date updated by {current_user.user_id}")
            return jsonify(result), 200
        else:
            logger.error(f"Failed to update installment {installment_id} due date: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error updating installment due date: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@package_api_bp.route('/session/<session_id>/complete', methods=['POST'])
@login_required
def complete_session(session_id):
    """
    Complete a package session

    POST /api/package/session/<session_id>/complete

    Request Body:
    {
        "actual_date": "2025-01-11",
        "performed_by": "user_uuid",
        "notes": "Session details..."
    }

    Response:
    {
        "success": true,
        "session_id": "uuid",
        "message": "Session completed successfully"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        actual_date = data.get('actual_date')
        performed_by = data.get('performed_by')  # Optional until staff API is implemented

        if not actual_date:
            return jsonify({
                'success': False,
                'error': 'Missing required field: actual_date'
            }), 400

        # Use current_user as default if performed_by not provided
        if not performed_by:
            performed_by = current_user.user_id
            logger.info(f"No staff selected, using current_user: {performed_by}")

        notes = data.get('notes', '')

        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session'
            }), 400

        # Get service
        service = PackagePaymentService()

        # Complete session
        result = service.complete_session(
            session_id=session_id,
            actual_date=actual_date,
            performed_by=performed_by,
            notes=notes,
            hospital_id=hospital_id
        )

        if result['success']:
            logger.info(f"Session {session_id} completed by {current_user.user_id}")
            return jsonify(result), 200
        else:
            logger.error(f"Failed to complete session {session_id}: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error completing session: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@package_api_bp.route('/patient/<patient_id>/invoices-with-packages', methods=['GET'])
@login_required
def get_patient_invoices_with_packages(patient_id):
    """
    Get all invoices for a patient that contain package line items
    Used by package payment plan creation screen

    GET /api/package/patient/<patient_id>/invoices-with-packages

    Response:
    {
        "success": true,
        "invoices": [
            {
                "invoice_id": "uuid",
                "invoice_number": "INV-001",
                "invoice_date": "2025-01-11",
                "package_id": "uuid",
                "package_name": "Laser Hair Reduction - 5 Sessions",
                "package_price": 50000.00,
                "package_line_item_id": "uuid",
                "line_item_total": 50000.00,
                "invoice_status": "approved"
            }
        ],
        "count": 3
    }
    """
    try:
        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session',
                'invoices': [],
                'count': 0
            }), 400

        # Get service
        service = PackagePaymentService()

        # Get patient invoices with packages
        result = service.get_patient_invoices_with_packages(
            patient_id=patient_id,
            hospital_id=hospital_id
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching patient invoices: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'invoices': [],
            'count': 0
        }), 500


@package_api_bp.route('/patient/<patient_id>/pending-installments', methods=['GET'])
@login_required
def get_patient_pending_installments(patient_id):
    """
    Get all pending installments for a patient
    Used by payment recording screen

    GET /api/package/patient/<patient_id>/pending-installments

    Response:
    {
        "success": true,
        "installments": [
            {
                "installment_id": "uuid",
                "plan_id": "uuid",
                "package_name": "Package Name",
                "installment_number": 1,
                "due_date": "2025-01-15",
                "amount": 10000.00,
                "paid_amount": 0.00,
                "balance_amount": 10000.00,
                "status": "pending"
            }
        ],
        "count": 5
    }
    """
    try:
        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session',
                'installments': [],
                'count': 0
            }), 400

        # Get service
        service = PackagePaymentService()

        # Get pending installments
        result = service.get_patient_pending_installments(
            patient_id=patient_id,
            hospital_id=hospital_id
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching pending installments: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}',
            'installments': [],
            'count': 0
        }), 500


@package_api_bp.route('/plan/<plan_id>/discontinuation-preview', methods=['GET'])
@csrf.exempt  # API endpoint - no state changes, read-only
@login_required
def preview_discontinuation(plan_id):
    """
    Preview discontinuation impact before user confirms
    Calculates financial impact and lists items to be cancelled

    GET /api/package/plan/<plan_id>/discontinuation-preview

    Response:
    {
        "success": true,
        "plan_id": "uuid",
        "plan_number": "PKG-001",
        "patient_name": "John Doe",
        "package_name": "Laser Hair Reduction",
        "total_sessions": 6,
        "completed_sessions": 2,
        "remaining_sessions": 4,
        "scheduled_sessions": 3,
        "pending_installments": 2,
        "total_amount": 5900.00,
        "paid_amount": 0.00,
        "calculated_refund": 3933.33,
        "invoice_number": "SVC/2025-2026/00005",
        "invoice_id": "uuid",
        "sessions_to_cancel": [
            {
                "session_id": "uuid",
                "session_number": 3,
                "session_date": "2025-01-20",
                "status": "scheduled"
            }
        ],
        "installments_to_cancel": [
            {
                "installment_id": "uuid",
                "installment_number": 2,
                "due_date": "2025-02-15",
                "amount": 1966.67,
                "status": "pending"
            }
        ]
    }
    """
    try:
        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session'
            }), 400

        # Get service
        service = PackagePaymentService()

        # Get discontinuation preview
        result = service.preview_discontinuation(
            plan_id=plan_id,
            hospital_id=hospital_id
        )

        if result['success']:
            return jsonify(result), 200
        else:
            logger.error(f"Failed to preview discontinuation for plan {plan_id}: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error previewing discontinuation: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@package_api_bp.route('/plan/<plan_id>/discontinue', methods=['POST'])
@csrf.exempt  # API endpoint - CSRF handled by login_required
@login_required
def discontinue_plan(plan_id):
    """
    Process plan discontinuation with user-adjusted refund amount
    Creates credit note and posts AR/GL entries

    POST /api/package/plan/<plan_id>/discontinue

    Request Body:
    {
        "discontinuation_reason": "Patient requested discontinuation",
        "adjustment_amount": 3500.00  // User can edit calculated amount
    }

    Response:
    {
        "success": true,
        "plan_id": "uuid",
        "message": "Plan discontinued successfully",
        "refund_amount": 3500.00,
        "sessions_cancelled": 3,
        "installments_cancelled": 2,
        "credit_note": {
            "credit_note_id": "uuid",
            "credit_note_number": "CN/2025-2026/00001",
            "ar_entry_id": "uuid",
            "gl_transaction_id": "uuid"
        }
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        discontinuation_reason = data.get('discontinuation_reason', '').strip()
        adjustment_amount = data.get('adjustment_amount')

        if not discontinuation_reason:
            return jsonify({
                'success': False,
                'error': 'Discontinuation reason is required'
            }), 400

        if adjustment_amount is None:
            return jsonify({
                'success': False,
                'error': 'Adjustment amount is required'
            }), 400

        try:
            from decimal import Decimal
            adjustment_amount = Decimal(str(adjustment_amount))
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid adjustment amount format'
            }), 400

        # Get hospital_id from g or current_user
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id

        if not hospital_id:
            return jsonify({
                'success': False,
                'error': 'Hospital ID not found in session'
            }), 400

        # Get service
        service = PackagePaymentService()

        # Process discontinuation
        result = service.process_discontinuation(
            plan_id=plan_id,
            discontinuation_reason=discontinuation_reason,
            adjustment_amount=adjustment_amount,
            hospital_id=hospital_id,
            user_id=current_user.user_id
        )

        if result['success']:
            logger.info(f"Plan {plan_id} discontinued by {current_user.user_id}")
            logger.info(f"  Refund: ₹{result.get('refund_amount')}")
            logger.info(f"  Sessions cancelled: {result.get('sessions_cancelled')}")
            logger.info(f"  Credit note: {result.get('credit_note', {}).get('credit_note_number')}")
            return jsonify(result), 200
        else:
            logger.error(f"Failed to discontinue plan {plan_id}: {result.get('error')}")
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error discontinuing plan: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500
