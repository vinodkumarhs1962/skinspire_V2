"""
Wallet Views
Flask routes for loyalty wallet management (UI layer only)
All business logic delegated to WalletService
"""

import logging
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app.services.wallet_service import WalletService, WalletError, InsufficientPointsError
from app.services.database_service import get_db_session
from app.models.master import Patient, LoyaltyCardType
from app.models.transaction import PatientLoyaltyWallet
from app.security.authorization.permission_validator import permission_required

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')


# ============================================================================
# TIER MANAGEMENT VIEWS
# ============================================================================

@wallet_bp.route('/tier-management/<patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def wallet_tier_management(patient_id):
    """
    Tier selection and purchase page
    Displays available tiers and current wallet status
    """
    try:
        with get_db_session(read_only=True) as session:
            # Get patient
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                flash('Patient not found', 'error')
                return redirect(url_for('billing.patient_search'))

            # Get available tiers
            available_tiers = session.query(LoyaltyCardType).filter(
                LoyaltyCardType.hospital_id == patient.hospital_id,
                LoyaltyCardType.is_active == True,
                LoyaltyCardType.min_payment_amount.isnot(None)
            ).order_by(LoyaltyCardType.min_payment_amount.asc()).all()

            # Get current wallet (if exists)
            wallet_data = WalletService.get_available_balance(
                patient_id=patient_id,
                hospital_id=str(patient.hospital_id)
            )

            wallet = None
            if wallet_data.get('has_wallet'):
                wallet = wallet_data

            return render_template(
                'billing/wallet_tier_management.html',
                patient=patient,
                available_tiers=available_tiers,
                wallet=wallet,
                csrf_token=None  # TODO: Add CSRF token
            )

    except Exception as e:
        logger.error(f"Error loading tier management page: {str(e)}")
        flash(f'Error loading page: {str(e)}', 'error')
        return redirect(url_for('billing.patient_search'))


@wallet_bp.route('/process-tier-purchase', methods=['POST'])
@login_required
@permission_required('billing', 'create')
def process_tier_purchase():
    """
    Process tier purchase or upgrade
    Delegates all business logic to WalletService
    """
    try:
        # Get form data
        patient_id = request.form.get('patient_id')
        card_type_id = request.form.get('card_type_id')
        payment_mode = request.form.get('payment_mode')
        payment_reference = request.form.get('payment_reference', '')
        notes = request.form.get('notes', '')
        is_upgrade = request.form.get('is_upgrade', 'false') == 'true'

        # Get tier details for amount
        with get_db_session(read_only=True) as session:
            card_type = session.query(LoyaltyCardType).filter(
                LoyaltyCardType.card_type_id == UUID(card_type_id)
            ).first()

            if not card_type:
                flash('Invalid tier selected', 'error')
                return redirect(url_for('wallet.wallet_tier_management', patient_id=patient_id))

            # Calculate amount to pay
            if is_upgrade:
                # Get current tier
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.is_active == True
                ).first()

                if not wallet or not wallet.card_type_id:
                    flash('No current tier found for upgrade', 'error')
                    return redirect(url_for('wallet.wallet_tier_management', patient_id=patient_id))

                current_tier = session.query(LoyaltyCardType).filter(
                    LoyaltyCardType.card_type_id == wallet.card_type_id
                ).first()

                amount_paid = card_type.min_payment_amount - current_tier.min_payment_amount
            else:
                amount_paid = card_type.min_payment_amount

        # Process through WalletService
        if is_upgrade:
            result = WalletService.upgrade_tier(
                patient_id=patient_id,
                new_card_type_id=card_type_id,
                amount_paid=Decimal(str(amount_paid)),
                payment_mode=payment_mode,
                payment_reference=payment_reference,
                user_id=current_user.user_id
            )
            flash(f'Successfully upgraded to {result["new_tier"]}! {result["additional_points"]:,} points added.', 'success')
        else:
            result = WalletService.load_tier(
                patient_id=patient_id,
                card_type_id=card_type_id,
                amount_paid=Decimal(str(amount_paid)),
                payment_mode=payment_mode,
                payment_reference=payment_reference,
                user_id=current_user.user_id
            )
            flash(f'Successfully purchased {result["tier_name"]}! {result["points_credited"]:,} points credited.', 'success')

        return redirect(url_for('wallet.wallet_dashboard', patient_id=patient_id))

    except WalletError as e:
        logger.error(f"Wallet error in tier purchase: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('wallet.wallet_tier_management', patient_id=request.form.get('patient_id')))

    except Exception as e:
        logger.error(f"Error processing tier purchase: {str(e)}")
        flash(f'Error processing purchase: {str(e)}', 'error')
        return redirect(url_for('wallet.wallet_tier_management', patient_id=request.form.get('patient_id')))


# ============================================================================
# DASHBOARD AND SUMMARY VIEWS
# ============================================================================

@wallet_bp.route('/dashboard/<patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def wallet_dashboard(patient_id):
    """
    Wallet dashboard with complete summary
    Delegates data retrieval to WalletService
    """
    try:
        with get_db_session(read_only=True) as session:
            # Get patient
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                flash('Patient not found', 'error')
                return redirect(url_for('billing.patient_search'))

            # Get wallet summary from service
            wallet_summary = WalletService.get_wallet_summary(
                patient_id=patient_id,
                hospital_id=str(patient.hospital_id)
            )

            if not wallet_summary.get('has_wallet'):
                flash('No wallet found for this patient. Please purchase a tier first.', 'info')
                return redirect(url_for('wallet.wallet_tier_management', patient_id=patient_id))

            # Format data for display
            # Add calculated fields for expiry batches
            if wallet_summary.get('expiring_batches'):
                for batch in wallet_summary['expiring_batches']:
                    expiry_date = datetime.strptime(batch['expiry_date'], '%Y-%m-%d').date()
                    batch['days_to_expiry'] = (expiry_date - date.today()).days
                    batch['load_date'] = expiry_date.strftime('%d %b %Y')  # Format for display
                    batch['expiry_date'] = expiry_date.strftime('%d %b %Y')

            # Format transaction dates
            if wallet_summary.get('recent_transactions'):
                for txn in wallet_summary['recent_transactions']:
                    txn_date = datetime.fromisoformat(txn['date'].replace('Z', '+00:00'))
                    txn['date'] = txn_date.strftime('%d %b %Y %I:%M %p')

            return render_template(
                'billing/wallet_dashboard.html',
                patient=patient,
                wallet=wallet_summary,
                csrf_token=None  # TODO: Add CSRF token
            )

    except Exception as e:
        logger.error(f"Error loading wallet dashboard: {str(e)}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('billing.patient_search'))


# ============================================================================
# TRANSACTION HISTORY VIEW
# ============================================================================

@wallet_bp.route('/transactions/<patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def wallet_transactions(patient_id):
    """
    Complete transaction history page
    Pagination and filtering support
    """
    try:
        from app.models.transaction import WalletTransaction, PatientLoyaltyWallet
        from sqlalchemy import desc

        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page_param = request.args.get('per_page', '20')
        per_page = 1000000 if per_page_param == 'all' else int(per_page_param)
        txn_type = request.args.get('type', None)
        from_date = request.args.get('from_date', None)
        to_date = request.args.get('to_date', None)

        with get_db_session(read_only=True) as session:
            # Get patient
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                flash('Patient not found', 'error')
                return redirect(url_for('billing.patient_search'))

            # Get wallet
            wallet = session.query(PatientLoyaltyWallet).filter(
                PatientLoyaltyWallet.patient_id == UUID(patient_id),
                PatientLoyaltyWallet.hospital_id == patient.hospital_id
            ).first()

            if not wallet:
                flash('No wallet found for this patient', 'info')
                return redirect(url_for('wallet.wallet_tier_management', patient_id=patient_id))

            # Get wallet info
            wallet_info = WalletService.get_available_balance(
                patient_id=patient_id,
                hospital_id=str(patient.hospital_id)
            )

            # Build query for transactions
            query = session.query(WalletTransaction).filter(
                WalletTransaction.wallet_id == wallet.wallet_id
            )

            # Apply filters
            if txn_type:
                query = query.filter(WalletTransaction.transaction_type == txn_type)

            if from_date:
                from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                query = query.filter(WalletTransaction.transaction_date >= from_datetime)

            if to_date:
                to_datetime = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(WalletTransaction.transaction_date <= to_datetime)

            # Order by date descending
            query = query.order_by(desc(WalletTransaction.transaction_date))

            # Get total count
            total_transactions = query.count()

            # Apply pagination (if not "all")
            if per_page_param != 'all':
                query = query.offset((page - 1) * per_page).limit(per_page)

            # Get transactions
            txn_records = query.all()

            # Format transactions for display
            transactions = []
            for txn in txn_records:
                # Calculate points based on transaction type
                if txn.transaction_type == 'load':
                    points = txn.total_points_loaded or 0
                    value = float(txn.amount_paid or 0)
                elif txn.transaction_type == 'redeem':
                    points = txn.points_redeemed or 0
                    value = float(txn.redemption_value or 0)
                elif txn.transaction_type == 'refund_service':
                    points = txn.points_credited_back or 0
                    value = float(points)  # 1:1 ratio
                elif txn.transaction_type == 'refund_wallet':
                    points = txn.points_forfeited or 0
                    value = float(txn.wallet_closure_amount or 0)
                elif txn.transaction_type == 'expire':
                    points = txn.points_redeemed or 0  # Stored in points_redeemed for expiry
                    value = float(points)
                else:  # adjustment
                    points = abs(txn.balance_after - txn.balance_before)
                    value = float(points)

                transactions.append({
                    'transaction_id': str(txn.transaction_id),
                    'type': txn.transaction_type,
                    'date': txn.transaction_date.strftime('%d %b %Y'),
                    'time': txn.transaction_date.strftime('%I:%M %p'),
                    'points': points,
                    'value': value,
                    'balance_after': txn.balance_after,
                    'invoice_number': txn.invoice_number or '',
                    'payment_reference': txn.payment_reference or '',
                    'payment_mode': txn.payment_mode or '',
                    'notes': txn.notes or ''
                })

            return render_template(
                'billing/wallet_transactions.html',
                patient=patient,
                wallet=wallet_info,
                transactions=transactions,
                page=page,
                per_page=per_page,
                total_transactions=total_transactions,
                now=datetime.now(),
                hospital_name=session.query(Patient).filter(Patient.patient_id == UUID(patient_id)).first().hospital.name if patient else 'Hospital'
            )

    except Exception as e:
        logger.error(f"Error loading transaction history: {str(e)}")
        flash(f'Error loading transactions: {str(e)}', 'error')
        return redirect(url_for('wallet.wallet_dashboard', patient_id=patient_id))


# ============================================================================
# WALLET CLOSURE VIEW
# ============================================================================

@wallet_bp.route('/close-wallet', methods=['POST'])
@login_required
@permission_required('billing', 'delete')
def close_wallet():
    """
    Close wallet and process refund
    Requires approval permission
    """
    try:
        patient_id = request.form.get('patient_id')
        closure_reason = request.form.get('closure_reason')

        if not closure_reason:
            flash('Closure reason is required', 'error')
            return redirect(url_for('wallet.wallet_dashboard', patient_id=patient_id))

        with get_db_session(read_only=True) as session:
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                flash('Patient not found', 'error')
                return redirect(url_for('billing.patient_search'))

            hospital_id = str(patient.hospital_id)

        # Process closure through WalletService
        result = WalletService.close_wallet(
            patient_id=patient_id,
            hospital_id=hospital_id,
            reason=closure_reason,
            user_id=current_user.user_id
        )

        if result['cash_refund'] > 0:
            flash(
                f'Wallet closed successfully. Cash refund: ₹{result["cash_refund"]:,.2f}. '
                f'{result["points_forfeited"]:,} points forfeited.',
                'success'
            )
        else:
            flash(
                f'Wallet closed successfully. No refund due. '
                f'{result["points_forfeited"]:,} points forfeited.',
                'info'
            )

        return redirect(url_for('billing.patient_detail', patient_id=patient_id))

    except WalletError as e:
        logger.error(f"Wallet error in closure: {str(e)}")
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('wallet.wallet_dashboard', patient_id=request.form.get('patient_id')))

    except Exception as e:
        logger.error(f"Error closing wallet: {str(e)}")
        flash(f'Error closing wallet: {str(e)}', 'error')
        return redirect(url_for('wallet.wallet_dashboard', patient_id=request.form.get('patient_id')))


# ============================================================================
# AJAX/API ENDPOINTS FOR UI COMPONENTS
# ============================================================================

@wallet_bp.route('/api/check-balance/<patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def api_check_balance(patient_id):
    """
    AJAX endpoint to check wallet balance
    Used by payment form component
    """
    try:
        with get_db_session(read_only=True) as session:
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                return jsonify({'error': 'Patient not found'}), 404

            balance_info = WalletService.get_available_balance(
                patient_id=patient_id,
                hospital_id=str(patient.hospital_id)
            )

            return jsonify({
                'success': True,
                'has_wallet': balance_info.get('has_wallet', False),
                'points_balance': balance_info.get('points_balance', 0),
                'points_value': float(balance_info.get('points_value', 0)),
                'tier_name': balance_info.get('tier_name', ''),
                'tier_discount_percent': float(balance_info.get('tier_discount_percent', 0)),
                'is_expired': balance_info.get('is_expired', False),
                'is_expiring_soon': balance_info.get('is_expiring_soon', False),
                'expiry_date': balance_info.get('expiry_date', '')
            })

    except Exception as e:
        logger.error(f"Error checking wallet balance: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wallet_bp.route('/api/validate-redemption/<patient_id>', methods=['POST'])
@login_required
@permission_required('billing', 'view')
def api_validate_redemption(patient_id):
    """
    AJAX endpoint to validate point redemption
    Used by payment form before submission
    """
    try:
        data = request.get_json()
        points_amount = data.get('points_amount', 0)

        with get_db_session(read_only=True) as session:
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                return jsonify({'error': 'Patient not found'}), 404

            validation = WalletService.validate_redemption(
                patient_id=patient_id,
                points_amount=int(points_amount),
                hospital_id=str(patient.hospital_id)
            )

            return jsonify({
                'success': True,
                'valid': validation['valid'],
                'message': validation['message'],
                'available': validation['available']
            })

    except Exception as e:
        logger.error(f"Error validating redemption: {str(e)}")
        return jsonify({'error': str(e)}), 500


@wallet_bp.route('/api/tier-discount/<patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def api_tier_discount(patient_id):
    """
    AJAX endpoint to get tier discount percentage
    Used by invoice creation to apply automatic discount
    """
    try:
        with get_db_session(read_only=True) as session:
            patient = session.query(Patient).filter(
                Patient.patient_id == UUID(patient_id)
            ).first()

            if not patient:
                return jsonify({'error': 'Patient not found'}), 404

            discount = WalletService.get_tier_discount(
                patient_id=patient_id,
                hospital_id=str(patient.hospital_id)
            )

            return jsonify({
                'success': True,
                'discount_percent': float(discount)
            })

    except Exception as e:
        logger.error(f"Error getting tier discount: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@wallet_bp.errorhandler(WalletError)
def handle_wallet_error(error):
    """Handle wallet-specific errors"""
    flash(f'Wallet Error: {str(error)}', 'error')
    return redirect(url_for('billing.patient_search'))


@wallet_bp.errorhandler(InsufficientPointsError)
def handle_insufficient_points(error):
    """Handle insufficient points errors"""
    flash(f'Insufficient Points: {str(error)}', 'error')
    return redirect(request.referrer or url_for('billing.patient_search'))
