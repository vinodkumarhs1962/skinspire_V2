"""
Promotion Views
Routes and handlers for the Promotions Dashboard
Handles campaign CRUD, timeline visualization, simulation, and configuration
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal

from flask import (
    Blueprint, render_template, request, jsonify, redirect,
    url_for, flash, current_app, session as flask_session
)
from flask_login import login_required, current_user

from sqlalchemy import or_

from app.services.promotion_dashboard_service import PromotionDashboardService
from app.services.database_service import get_db_session
from app.utils.menu_utils import get_menu_items
from app.models.master import Service, Medicine, Package, LoyaltyCardType, Hospital

logger = logging.getLogger(__name__)

# Create blueprint
promotion_views_bp = Blueprint('promotion_views', __name__, url_prefix='/promotions')


def get_user_hospital_id():
    """Get hospital_id from current user context"""
    # Use current_user.hospital_id directly (consistent with other views)
    if current_user and current_user.is_authenticated:
        return getattr(current_user, 'hospital_id', None)
    return None


# =============================================================================
# DASHBOARD VIEWS
# =============================================================================

@promotion_views_bp.route('/dashboard')
@login_required
def dashboard():
    """Main promotions dashboard view"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Auto-deactivate expired campaigns
    deactivated = PromotionDashboardService.deactivate_expired_campaigns(hospital_id)
    if deactivated > 0:
        logger.info(f"Auto-deactivated {deactivated} expired campaign(s)")

    # Get hospital state code for state-specific holidays
    # Campaigns are at hospital level, so use hospital's state code
    hospital_state_code = None
    if hospital_id:
        with get_db_session() as session:
            hospital = session.query(Hospital).filter(
                Hospital.hospital_id == hospital_id
            ).first()
            if hospital:
                hospital_state_code = hospital.state_code

    # Get dashboard summary
    summary = PromotionDashboardService.get_dashboard_summary(hospital_id)

    # Get timeline data for default 3-month view
    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=60)
    timeline_data = PromotionDashboardService.get_timeline_data(
        hospital_id, start_date, end_date
    )

    return render_template(
        'promotions/dashboard.html',
        summary=summary,
        timeline_data=timeline_data,
        today=today.isoformat(),
        hospital_state_code=hospital_state_code,
        menu_items=get_menu_items(current_user),
        page_title='Promotions Dashboard'
    )


@promotion_views_bp.route('/timeline')
@login_required
def timeline_fullpage():
    """Full-page timeline view"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Get timeline data for default view (6 months)
    today = date.today()
    start_date = today - timedelta(days=60)
    end_date = today + timedelta(days=120)
    timeline_data = PromotionDashboardService.get_timeline_data(
        hospital_id, start_date, end_date
    )

    return render_template(
        'promotions/timeline.html',
        timeline_data=timeline_data,
        today=today.isoformat(),
        menu_items=get_menu_items(current_user),
        page_title='Promotions Timeline'
    )


# =============================================================================
# CAMPAIGN CRUD VIEWS
# =============================================================================

@promotion_views_bp.route('/campaigns')
@login_required
def campaign_list():
    """List all campaigns"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Auto-deactivate expired campaigns
    PromotionDashboardService.deactivate_expired_campaigns(hospital_id)

    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active')
    promotion_type = request.args.get('promotion_type')
    applies_to = request.args.get('applies_to')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    filters = {}
    if search:
        filters['search'] = search
    if is_active is not None and is_active != '':
        filters['is_active'] = is_active.lower() == 'true'
    if promotion_type:
        filters['promotion_type'] = promotion_type
    if applies_to:
        filters['applies_to'] = applies_to
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date

    # Get campaigns
    result = PromotionDashboardService.get_all_campaigns(
        hospital_id=hospital_id,
        filters=filters,
        page=page,
        per_page=per_page
    )

    # Get summary for cards
    summary = PromotionDashboardService.get_campaign_summary(hospital_id=hospital_id)

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    return render_template(
        'promotions/campaigns/list.html',
        campaigns=result['items'],
        total=result['total'],
        page=page,
        per_page=per_page,
        pages=result['pages'],
        filters=filters,
        summary=summary,
        today=today.isoformat(),  # For JS date comparisons
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Campaign Promotions'
    )


@promotion_views_bp.route('/campaigns/create', methods=['GET', 'POST'])
@login_required
def campaign_create():
    """Create new campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    # Get campaign groups for targeting (exclude deleted groups)
    campaign_groups = PromotionDashboardService.get_campaign_groups(
        hospital_id,
        include_inactive=False,
        include_deleted=False
    )
    # Map total_items to item_count for template
    for group in campaign_groups:
        group['item_count'] = group.get('total_items', 0)

    if request.method == 'POST':
        try:
            # Get target group IDs (campaign groups for item targeting)
            target_group_ids = request.form.getlist('target_group_ids')
            target_groups = {'group_ids': target_group_ids} if target_group_ids else None

            # Determine is_personalized and auto_apply
            is_personalized = request.form.get('is_personalized') == 'on'
            auto_apply = not is_personalized  # Auto-apply if not personalized

            # Parse form data
            data = {
                'campaign_code': request.form.get('campaign_code', '').strip().upper(),
                'campaign_name': request.form.get('campaign_name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'promotion_type': request.form.get('promotion_type', 'simple_discount'),
                'discount_type': request.form.get('discount_type'),
                'discount_value': request.form.get('discount_value'),
                'start_date': datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date() if request.form.get('start_date') else None,
                'end_date': datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get('end_date') else None,
                'is_active': request.form.get('is_active') == 'on',
                'is_personalized': is_personalized,
                'auto_apply': auto_apply,
                'target_special_group': request.form.get('target_special_group') == 'on',
                'applies_to': request.form.get('applies_to', 'all'),
                'target_groups': target_groups,
                'min_purchase_amount': request.form.get('min_purchase_amount') or None,
                'max_discount_amount': request.form.get('max_discount_amount') or None,
                'max_uses_per_patient': int(request.form.get('max_uses_per_patient')) if request.form.get('max_uses_per_patient') else None,
                'max_total_uses': int(request.form.get('max_total_uses')) if request.form.get('max_total_uses') else None,
                'terms_and_conditions': request.form.get('terms_and_conditions', '').strip()
            }

            # Validate required fields
            if not data['campaign_code']:
                flash('Campaign code is required', 'error')
                return render_template(
                    'promotions/campaigns/create.html',
                    data=data,
                    campaign_groups=campaign_groups,
                    today_display=today_display,
                    today_day=today_day,
                    menu_items=get_menu_items(current_user),
                    page_title='Create Campaign'
                )

            if not data['campaign_name']:
                flash('Campaign name is required', 'error')
                return render_template(
                    'promotions/campaigns/create.html',
                    data=data,
                    campaign_groups=campaign_groups,
                    today_display=today_display,
                    today_day=today_day,
                    menu_items=get_menu_items(current_user),
                    page_title='Create Campaign'
                )

            success, message, campaign_id = PromotionDashboardService.create_campaign(
                hospital_id, data
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('promotion_views.campaign_list'))
            else:
                flash(message, 'error')

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            flash(f'Error creating campaign: {str(e)}', 'error')

        return render_template(
            'promotions/campaigns/create.html',
            data=request.form,
            campaign_groups=campaign_groups,
            today_display=today_display,
            today_day=today_day,
            menu_items=get_menu_items(current_user),
            page_title='Create Campaign'
        )

    # GET request - show empty form
    return render_template(
        'promotions/campaigns/create.html',
        data={},
        campaign_groups=campaign_groups,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Create Campaign'
    )


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """View campaign details"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    campaign = PromotionDashboardService.get_campaign_by_id(hospital_id, str(campaign_id))

    if not campaign:
        flash('Campaign not found', 'error')
        return redirect(url_for('promotion_views.campaign_list'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    return render_template(
        'promotions/campaigns/detail.html',
        campaign=campaign,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title=f'Campaign: {campaign["campaign_name"]}'
    )


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/edit', methods=['GET', 'POST'])
@login_required
def campaign_edit(campaign_id):
    """Edit campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    campaign = PromotionDashboardService.get_campaign_by_id(hospital_id, str(campaign_id))

    if not campaign:
        flash('Campaign not found', 'error')
        return redirect(url_for('promotion_views.campaign_list'))

    # Get campaign groups for targeting (exclude deleted groups)
    campaign_groups = PromotionDashboardService.get_campaign_groups(
        hospital_id,
        include_inactive=False,
        include_deleted=False
    )
    # Map total_items to item_count for template
    for group in campaign_groups:
        group['item_count'] = group.get('total_items', 0)

    if request.method == 'POST':
        try:
            # Get target group IDs (campaign groups for item targeting)
            target_group_ids = request.form.getlist('target_group_ids')
            target_groups = {'group_ids': target_group_ids} if target_group_ids else None

            # Determine is_personalized and auto_apply
            is_personalized = request.form.get('is_personalized') == 'on'
            auto_apply = not is_personalized  # Auto-apply if not personalized

            data = {
                'campaign_code': request.form.get('campaign_code', '').strip().upper(),
                'campaign_name': request.form.get('campaign_name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'promotion_type': request.form.get('promotion_type', 'simple_discount'),
                'discount_type': request.form.get('discount_type'),
                'discount_value': request.form.get('discount_value'),
                'start_date': datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date() if request.form.get('start_date') else None,
                'end_date': datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get('end_date') else None,
                'is_active': request.form.get('is_active') == 'on',
                'is_personalized': is_personalized,
                'auto_apply': auto_apply,
                'target_special_group': request.form.get('target_special_group') == 'on',
                'applies_to': request.form.get('applies_to', 'all'),
                'target_groups': target_groups,
                'min_purchase_amount': request.form.get('min_purchase_amount') or None,
                'max_discount_amount': request.form.get('max_discount_amount') or None,
                'max_uses_per_patient': int(request.form.get('max_uses_per_patient')) if request.form.get('max_uses_per_patient') else None,
                'max_total_uses': int(request.form.get('max_total_uses')) if request.form.get('max_total_uses') else None,
                'terms_and_conditions': request.form.get('terms_and_conditions', '').strip()
            }

            success, message = PromotionDashboardService.update_campaign(
                hospital_id, str(campaign_id), data
            )

            if success:
                flash(message, 'success')
                return redirect(url_for('promotion_views.campaign_detail', campaign_id=campaign_id))
            else:
                flash(message, 'error')
                campaign.update(data)  # Update campaign dict with form data for display

        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            flash(f'Error updating campaign: {str(e)}', 'error')

    return render_template(
        'promotions/campaigns/edit.html',
        campaign=campaign,
        campaign_groups=campaign_groups,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title=f'Edit Campaign: {campaign["campaign_name"]}'
    )


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/toggle', methods=['POST'])
@login_required
def campaign_toggle(campaign_id):
    """Toggle campaign active status"""
    logger.info(f"[TOGGLE] Campaign toggle requested for ID: {campaign_id}")
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        logger.warning("[TOGGLE] Hospital context not found")
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    logger.info(f"[TOGGLE] Hospital ID: {hospital_id}")
    success, message = PromotionDashboardService.toggle_campaign_status(
        hospital_id, str(campaign_id)
    )
    logger.info(f"[TOGGLE] Result: success={success}, message={message}")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_list'))


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/duplicate', methods=['POST'])
@login_required
def campaign_duplicate(campaign_id):
    """Duplicate campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message, new_id = PromotionDashboardService.duplicate_campaign(
        hospital_id, str(campaign_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message, 'new_campaign_id': new_id})

    flash(message, 'success' if success else 'error')
    if success and new_id:
        return redirect(url_for('promotion_views.campaign_edit', campaign_id=new_id))
    return redirect(url_for('promotion_views.campaign_list'))


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/delete', methods=['POST'])
@login_required
def campaign_delete(campaign_id):
    """Delete campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.delete_campaign(
        hospital_id, str(campaign_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_list'))


# =============================================================================
# CAMPAIGN APPROVAL WORKFLOW
# =============================================================================

@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/submit-for-approval', methods=['POST'])
@login_required
def campaign_submit_for_approval(campaign_id):
    """Submit campaign for approval"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.submit_campaign_for_approval(
        hospital_id, str(campaign_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_detail', campaign_id=campaign_id))


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/approve', methods=['POST'])
@login_required
def campaign_approve(campaign_id):
    """Approve campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    data = request.get_json() if request.is_json else request.form
    notes = data.get('notes', '')

    success, message = PromotionDashboardService.approve_campaign(
        hospital_id, str(campaign_id), current_user.user_id, notes
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_detail', campaign_id=campaign_id))


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/reject', methods=['POST'])
@login_required
def campaign_reject(campaign_id):
    """Reject campaign"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    data = request.get_json() if request.is_json else request.form
    reason = data.get('reason', '')

    if not reason:
        return jsonify({'success': False, 'message': 'Rejection reason is required'}), 400

    success, message = PromotionDashboardService.reject_campaign(
        hospital_id, str(campaign_id), current_user.user_id, reason
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_detail', campaign_id=campaign_id))


@promotion_views_bp.route('/campaigns/<uuid:campaign_id>/resubmit', methods=['POST'])
@login_required
def campaign_resubmit(campaign_id):
    """Resubmit rejected campaign for approval"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.resubmit_campaign(
        hospital_id, str(campaign_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.campaign_detail', campaign_id=campaign_id))


@promotion_views_bp.route('/campaigns/pending-approval')
@login_required
def campaigns_pending_approval():
    """View campaigns pending approval"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    campaigns = PromotionDashboardService.get_campaigns_pending_approval(hospital_id)

    return render_template(
        'promotions/campaigns_pending_approval.html',
        campaigns=campaigns,
        menu_items=get_menu_items()
    )


@promotion_views_bp.route('/api/campaigns/pending-approval')
@login_required
def api_campaigns_pending_approval():
    """JSON: Get campaigns pending approval"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    campaigns = PromotionDashboardService.get_campaigns_pending_approval(hospital_id)
    return jsonify({'campaigns': campaigns, 'count': len(campaigns)})


# =============================================================================
# CONFIGURATION VIEWS
# =============================================================================

@promotion_views_bp.route('/bulk/config', methods=['GET', 'POST'])
@login_required
def bulk_config():
    """Bulk discount configuration page"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    if request.method == 'POST':
        try:
            data = {
                'enabled': request.form.get('enabled') == 'on',
                'min_service_count': int(request.form.get('min_service_count', 5)),
                'effective_from': datetime.strptime(request.form.get('effective_from'), '%Y-%m-%d').date() if request.form.get('effective_from') else None
            }

            success, message = PromotionDashboardService.update_bulk_config(hospital_id, data)
            flash(message, 'success' if success else 'error')

        except Exception as e:
            logger.error(f"Error updating bulk config: {e}")
            flash(f'Error updating configuration: {str(e)}', 'error')

    config = PromotionDashboardService.get_bulk_config(hospital_id)
    eligible_services = PromotionDashboardService.get_bulk_eligible_items(hospital_id, 'service')
    eligible_medicines = PromotionDashboardService.get_bulk_eligible_items(hospital_id, 'medicine')

    return render_template(
        'promotions/bulk/config.html',
        config=config,
        eligible_services=eligible_services,
        eligible_medicines=eligible_medicines,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Bulk Discount Configuration'
    )


@promotion_views_bp.route('/loyalty/config', methods=['GET', 'POST'])
@login_required
def loyalty_config():
    """Loyalty discount configuration page"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    if request.method == 'POST':
        mode = request.form.get('loyalty_discount_mode', 'absolute')
        success, message = PromotionDashboardService.update_loyalty_mode(hospital_id, mode)
        flash(message, 'success' if success else 'error')

    config = PromotionDashboardService.get_loyalty_config(hospital_id)
    card_types = PromotionDashboardService.get_card_types(hospital_id)

    return render_template(
        'promotions/loyalty/config.html',
        config=config,
        card_types=card_types,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Loyalty Discount Configuration'
    )


# =============================================================================
# CAMPAIGN GROUP VIEWS
# =============================================================================

@promotion_views_bp.route('/groups')
@login_required
def group_list():
    """List all campaign groups"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    # Get filter parameters
    show_inactive = request.args.get('show_inactive', 'false') == 'true'

    groups = PromotionDashboardService.get_campaign_groups(
        hospital_id,
        include_inactive=show_inactive
    )
    summary = PromotionDashboardService.get_groups_summary(hospital_id)

    return render_template(
        'promotions/groups/list.html',
        groups=groups,
        summary=summary,
        show_inactive=show_inactive,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Campaign Groups'
    )


@promotion_views_bp.route('/groups/create', methods=['GET', 'POST'])
@login_required
def group_create():
    """Create new campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Hospital context not found'})
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            json_data = request.get_json()
            data = {
                'group_code': json_data.get('group_code', '').strip().upper(),
                'group_name': json_data.get('group_name', '').strip(),
                'description': json_data.get('description', '').strip(),
                'is_active': json_data.get('is_active', True)
            }
        else:
            data = {
                'group_code': request.form.get('group_code', '').strip().upper(),
                'group_name': request.form.get('group_name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'is_active': request.form.get('is_active') == 'on'
            }

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not data['group_code']:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Group code is required'})
            flash('Group code is required', 'error')
            return render_template(
                'promotions/groups/create.html',
                data=data,
                today_display=today_display,
                today_day=today_day,
                menu_items=get_menu_items(current_user),
                page_title='Create Campaign Group'
            )

        if not data['group_name']:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Group name is required'})
            flash('Group name is required', 'error')
            return render_template(
                'promotions/groups/create.html',
                data=data,
                today_display=today_display,
                today_day=today_day,
                menu_items=get_menu_items(current_user),
                page_title='Create Campaign Group'
            )

        success, message, group_id = PromotionDashboardService.create_campaign_group(
            hospital_id, data
        )

        if is_ajax:
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'group_id': group_id,
                    'redirect': url_for('promotion_views.group_detail', group_id=group_id)
                })
            else:
                return jsonify({'success': False, 'message': message})

        if success:
            flash(message, 'success')
            return redirect(url_for('promotion_views.group_detail', group_id=group_id))
        else:
            flash(message, 'error')

    return render_template(
        'promotions/groups/create.html',
        data={},
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title='Create Campaign Group'
    )


@promotion_views_bp.route('/groups/<uuid:group_id>')
@login_required
def group_detail(group_id):
    """View campaign group details"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    group = PromotionDashboardService.get_campaign_group_by_id(hospital_id, str(group_id))

    if not group:
        flash('Campaign group not found', 'error')
        return redirect(url_for('promotion_views.group_list'))

    # Prepare items list combining all item types with item_type field
    items = []
    for svc in group.get('services', []):
        svc['item_type'] = 'service'
        svc['item_price'] = svc.get('price', 0)
        items.append(svc)
    for med in group.get('medicines', []):
        med['item_type'] = 'medicine'
        med['item_price'] = med.get('price', 0)
        items.append(med)
    for pkg in group.get('packages', []):
        pkg['item_type'] = 'package'
        pkg['item_price'] = pkg.get('price', 0)
        items.append(pkg)

    # Prepare item counts
    item_counts = {
        'service': len(group.get('services', [])),
        'medicine': len(group.get('medicines', [])),
        'package': len(group.get('packages', []))
    }

    return render_template(
        'promotions/groups/detail.html',
        group=group,
        items=items,
        item_counts=item_counts,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title=f'Group: {group["group_name"]}'
    )


@promotion_views_bp.route('/groups/<uuid:group_id>/edit', methods=['GET', 'POST'])
@login_required
def group_edit(group_id):
    """Edit campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        flash('Hospital context not found', 'error')
        return redirect(url_for('auth_views.dashboard'))

    # Format today's date for display
    today = date.today()
    today_display = today.strftime('%d %b %Y')
    today_day = today.strftime('%A')

    group = PromotionDashboardService.get_campaign_group_by_id(hospital_id, str(group_id))

    if not group:
        flash('Campaign group not found', 'error')
        return redirect(url_for('promotion_views.group_list'))

    # Prepare item counts for template
    item_counts = {
        'service': len(group.get('services', [])),
        'medicine': len(group.get('medicines', [])),
        'package': len(group.get('packages', []))
    }

    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            json_data = request.get_json()
            data = {
                'group_name': json_data.get('group_name', '').strip(),
                'description': json_data.get('description', '').strip(),
                'is_active': json_data.get('is_active', True)
            }
        else:
            data = {
                'group_name': request.form.get('group_name', '').strip(),
                'description': request.form.get('description', '').strip(),
                'is_active': request.form.get('is_active') == 'on'
            }

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        success, message = PromotionDashboardService.update_campaign_group(
            hospital_id, str(group_id), data
        )

        if is_ajax:
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'redirect': url_for('promotion_views.group_detail', group_id=group_id)
                })
            else:
                return jsonify({'success': False, 'message': message})

        if success:
            flash(message, 'success')
            return redirect(url_for('promotion_views.group_detail', group_id=group_id))
        else:
            flash(message, 'error')
            group.update(data)

    return render_template(
        'promotions/groups/edit.html',
        group=group,
        item_counts=item_counts,
        today_display=today_display,
        today_day=today_day,
        menu_items=get_menu_items(current_user),
        page_title=f'Edit Group: {group["group_name"]}'
    )


@promotion_views_bp.route('/groups/<uuid:group_id>/toggle', methods=['POST'])
@login_required
def group_toggle(group_id):
    """Toggle campaign group active status"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.toggle_campaign_group_status(
        hospital_id, str(group_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.group_list'))


@promotion_views_bp.route('/groups/<uuid:group_id>/delete', methods=['POST'])
@login_required
def group_delete(group_id):
    """Delete campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.delete_campaign_group(
        hospital_id, str(group_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.group_list'))


@promotion_views_bp.route('/groups/<uuid:group_id>/undelete', methods=['POST'])
@login_required
def group_undelete(group_id):
    """Restore a deleted campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    success, message = PromotionDashboardService.undelete_campaign_group(
        hospital_id, str(group_id)
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    flash(message, 'success' if success else 'error')
    return redirect(url_for('promotion_views.group_list'))


@promotion_views_bp.route('/api/groups/<uuid:group_id>/items', methods=['POST'])
@login_required
def api_group_add_items(group_id):
    """API: Add items to a campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    try:
        data = request.get_json()
        items = data.get('items', [])

        if not items:
            return jsonify({'success': False, 'message': 'No items provided'}), 400

        success, message, count = PromotionDashboardService.add_items_to_group(
            hospital_id, str(group_id), items
        )

        return jsonify({'success': success, 'message': message, 'items_added': count})

    except Exception as e:
        logger.error(f"Error adding items to group: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@promotion_views_bp.route('/api/groups/<uuid:group_id>/items', methods=['DELETE'])
@login_required
def api_group_remove_items(group_id):
    """API: Remove items from a campaign group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    try:
        data = request.get_json()
        group_item_ids = data.get('group_item_ids', [])

        if not group_item_ids:
            return jsonify({'success': False, 'message': 'No items specified'}), 400

        success, message, count = PromotionDashboardService.remove_items_from_group(
            hospital_id, str(group_id), group_item_ids
        )

        return jsonify({'success': success, 'message': message, 'items_removed': count})

    except Exception as e:
        logger.error(f"Error removing items from group: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@promotion_views_bp.route('/api/groups/<uuid:group_id>/available-items')
@login_required
def api_group_available_items(group_id):
    """API: Get items available to add to a group"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    item_type = request.args.get('item_type', 'service')
    search = request.args.get('search', '')

    items = PromotionDashboardService.get_available_items_for_group(
        hospital_id, str(group_id), item_type, search
    )

    return jsonify({'items': items})


@promotion_views_bp.route('/api/groups')
@login_required
def api_groups_list():
    """API: Get all campaign groups (for dropdowns)"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    groups = PromotionDashboardService.get_campaign_groups(
        hospital_id,
        include_inactive=False,
        include_item_counts=False
    )

    return jsonify({'groups': groups})


# =============================================================================
# API ENDPOINTS
# =============================================================================

@promotion_views_bp.route('/api/timeline-data')
@login_required
def api_timeline_data():
    """JSON: Timeline chart data"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    # Parse date parameters
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    try:
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        else:
            start_date = date.today() - timedelta(days=30)

        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = date.today() + timedelta(days=60)

    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    data = PromotionDashboardService.get_timeline_data(hospital_id, start_date, end_date)
    return jsonify(data)


@promotion_views_bp.route('/api/timeline-update', methods=['POST'])
@login_required
def api_timeline_update():
    """JSON: Update campaign dates (drag-resize)"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'message': 'Hospital context not found'}), 400

    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()

        success, message, status_changed = PromotionDashboardService.update_campaign_dates(
            hospital_id, campaign_id, start_date, end_date
        )

        return jsonify({
            'success': success,
            'message': message,
            'status_changed': status_changed
        })

    except Exception as e:
        logger.error(f"Error updating timeline: {e}")
        return jsonify({'success': False, 'message': str(e), 'status_changed': False}), 500


@promotion_views_bp.route('/api/simulate', methods=['POST'])
@login_required
def api_simulate():
    """JSON: Simulate promotions for item"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    try:
        data = request.get_json()
        item_type = data.get('item_type', 'service')
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        patient_id = data.get('patient_id')
        simulation_date_str = data.get('simulation_date')
        include_draft = data.get('include_draft', False)

        # Debug logging
        logger.info(f"[SIMULATE] item_type={item_type}, item_id={item_id}, patient_id={patient_id}, include_draft={include_draft}")

        # Convert patient_id to proper format if provided
        if patient_id and patient_id.strip():
            # Ensure it's a valid UUID string (not patient name)
            import uuid as uuid_module
            try:
                # Validate UUID format
                uuid_module.UUID(patient_id)
            except ValueError:
                logger.warning(f"[SIMULATE] Invalid patient_id format: {patient_id}")
                patient_id = None
        else:
            patient_id = None

        simulation_date = None
        if simulation_date_str:
            simulation_date = datetime.strptime(simulation_date_str, '%Y-%m-%d').date()

        result = PromotionDashboardService.simulate_promotions(
            hospital_id=str(hospital_id),  # Ensure string
            item_id=item_id,
            item_type=item_type,
            quantity=quantity,
            patient_id=patient_id,
            simulation_date=simulation_date,
            include_draft=include_draft
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in simulation: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@promotion_views_bp.route('/api/summary')
@login_required
def api_summary():
    """JSON: Dashboard summary cards"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    summary = PromotionDashboardService.get_dashboard_summary(hospital_id)
    return jsonify(summary)


@promotion_views_bp.route('/api/analytics')
@login_required
def api_analytics():
    """JSON: Analytics charts data"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    # Parse date parameters
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    try:
        if start_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        else:
            start_date = date.today().replace(day=1)  # Start of month

        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = date.today()

    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    breakdown = PromotionDashboardService.get_discount_breakdown(hospital_id, start_date, end_date)
    trends = PromotionDashboardService.get_usage_trends(hospital_id, start_date, end_date)
    top_campaigns = PromotionDashboardService.get_top_campaigns(hospital_id, start_date, end_date)

    return jsonify({
        'breakdown': breakdown,
        'trends': trends,
        'top_campaigns': top_campaigns
    })


@promotion_views_bp.route('/api/overlaps')
@login_required
def api_overlaps():
    """JSON: Overlap detection results"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    # Get timeline data to detect overlaps
    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=90)

    data = PromotionDashboardService.get_timeline_data(hospital_id, start_date, end_date)
    return jsonify({'overlaps': data.get('overlaps', [])})


@promotion_views_bp.route('/api/applicable-campaigns')
@login_required
def api_applicable_campaigns():
    """
    JSON: Get applicable campaigns for a patient/service/medicine selection
    Used by timeline filter to show only relevant campaigns
    """
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'error': 'Hospital context not found'}), 400

    # Get filter parameters
    patient_id = request.args.get('patient_id')
    service_id = request.args.get('service_id')
    medicine_id = request.args.get('medicine_id')
    package_id = request.args.get('package_id')

    try:
        result = PromotionDashboardService.get_applicable_campaigns(
            hospital_id=hospital_id,
            patient_id=patient_id,
            service_id=service_id,
            medicine_id=medicine_id,
            package_id=package_id
        )

        return jsonify({
            'success': True,
            'campaigns': result.get('campaigns', []),
            'applicable_discounts': result.get('applicable_discounts', {}),
            'patient_context': result.get('patient_context'),  # VIP status, loyalty card info
            'item_context': result.get('item_context'),        # Service/medicine info
            'filters_applied': {
                'patient_id': patient_id,
                'service_id': service_id,
                'medicine_id': medicine_id
            }
        })

    except Exception as e:
        logger.error(f"Error getting applicable campaigns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# SUMMARY CARD DETAILS API ENDPOINTS
# =============================================================================

@promotion_views_bp.route('/api/card-details/<card_type>')
@login_required
def api_card_details(card_type):
    """JSON: Get details for summary card popups"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'success': False, 'error': 'Hospital context not found'}), 400

    try:
        result = PromotionDashboardService.get_card_details(hospital_id, card_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting card details for {card_type}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@promotion_views_bp.route('/api/items/<item_type>')
@login_required
def api_items_list(item_type):
    """JSON: Get items for simulation dropdown"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    search = request.args.get('search', '')
    limit = min(int(request.args.get('limit', 50)), 100)

    try:
        with get_db_session(read_only=True) as session:
            items = []

            if item_type == 'service':
                # Service model: code, service_name, price, is_active, is_deleted
                query = session.query(Service).filter(
                    Service.hospital_id == hospital_id,
                    Service.is_active == True,
                    Service.is_deleted == False
                )
                if search:
                    query = query.filter(
                        or_(
                            Service.service_name.ilike(f'%{search}%'),
                            Service.code.ilike(f'%{search}%')
                        )
                    )
                services = query.order_by(Service.service_name).limit(limit).all()
                items = [
                    {
                        'id': str(s.service_id),
                        'name': s.service_name,
                        'code': s.code,
                        'price': float(s.price or 0),
                        'service_type': s.service_type
                    }
                    for s in services
                ]

            elif item_type == 'medicine':
                # Medicine model: medicine_name, mrp, status (no code field)
                query = session.query(Medicine).filter(
                    Medicine.hospital_id == hospital_id,
                    Medicine.status == 'active',
                    Medicine.is_deleted == False
                )
                if search:
                    query = query.filter(
                        or_(
                            Medicine.medicine_name.ilike(f'%{search}%'),
                            Medicine.generic_name.ilike(f'%{search}%')
                        )
                    )
                medicines = query.order_by(Medicine.medicine_name).limit(limit).all()
                items = [
                    {
                        'id': str(m.medicine_id),
                        'name': m.medicine_name,
                        'code': m.generic_name,  # Use generic_name as secondary identifier
                        'price': float(m.mrp or m.selling_price or 0),
                        'category': m.medicine_type
                    }
                    for m in medicines
                ]

            elif item_type == 'package':
                # Package model: package_name, package_code, selling_price, status
                query = session.query(Package).filter(
                    Package.hospital_id == hospital_id,
                    Package.status == 'active',
                    Package.is_deleted == False
                )
                if search:
                    query = query.filter(
                        or_(
                            Package.package_name.ilike(f'%{search}%'),
                            Package.package_code.ilike(f'%{search}%')
                        )
                    )
                packages = query.order_by(Package.package_name).limit(limit).all()
                items = [
                    {
                        'id': str(p.package_id),
                        'name': p.package_name,
                        'code': p.package_code,
                        'price': float(p.selling_price or p.price or 0)
                    }
                    for p in packages
                ]

            return jsonify({'items': items})

    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        return jsonify({'error': str(e)}), 500


@promotion_views_bp.route('/api/campaigns')
@login_required
def api_campaigns_list():
    """JSON: Get campaigns list for AJAX"""
    hospital_id = get_user_hospital_id()
    if not hospital_id:
        return jsonify({'error': 'Hospital context not found'}), 400

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active')

    filters = {}
    if search:
        filters['search'] = search
    if is_active is not None and is_active != '':
        filters['is_active'] = is_active.lower() == 'true'

    result = PromotionDashboardService.get_all_campaigns(
        hospital_id=hospital_id,
        filters=filters,
        page=page,
        per_page=per_page
    )

    return jsonify(result)
