"""
Package Payment Plan Custom Views
Handles custom routes for package payment plan creation with cascading workflow
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required, current_user
from app.services.package_payment_service import PackagePaymentService
from app.security.authorization.decorators import require_web_branch_permission
import logging

logger = logging.getLogger(__name__)

# Create blueprint
package_views_bp = Blueprint('package_views', __name__, url_prefix='/package')

@package_views_bp.route('/payment-plan/create', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('package_payment_plan', 'create')
def create_payment_plan():
    """
    Custom create route for package payment plans
    Provides cascading workflow: Patient → Invoice → Auto-populate

    GET: Display custom create form with patient autocomplete
    POST: Create payment plan (delegates to Universal Engine create logic)
    """

    if request.method == 'GET':
        # Render custom template with cascading workflow
        return render_template('package/create_payment_plan.html')

    # POST - Handle form submission
    try:
        # Get form data
        data = request.form.to_dict()

        # Get hospital_id and branch_id with fallback
        hospital_id = getattr(g, 'hospital_id', None) or current_user.hospital_id
        branch_id = getattr(g, 'branch_id', None)

        if not hospital_id:
            flash('Hospital ID not found in session', 'error')
            return render_template('package/create_payment_plan.html', error='Hospital ID not found')

        # Initialize service
        service = PackagePaymentService()

        # Create payment plan (service handles installment and session generation)
        result = service.create(
            data=data,
            hospital_id=hospital_id,
            branch_id=branch_id,
            created_by=current_user.user_id
        )

        if result['success']:
            flash('Payment plan created successfully', 'success')

            # Redirect to detail view
            plan_id = result['data'].get('plan_id')
            return redirect(url_for('universal_views.universal_detail_view',
                                  entity_type='package_payment_plans',
                                  item_id=plan_id))
        else:
            flash(f"Error: {result.get('error', 'Unknown error')}", 'error')
            return render_template('package/create_payment_plan.html', error=result.get('error'))

    except Exception as e:
        logger.error(f"Error creating payment plan: {str(e)}", exc_info=True)
        flash(f"Error creating payment plan: {str(e)}", 'error')
        return render_template('package/create_payment_plan.html', error=str(e))
