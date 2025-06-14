# app/views/inventory_views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.services.inventory_service import (
    record_opening_stock,
    record_stock_adjustment,
    get_stock_details,
    get_low_stock_medicines,
    get_expiring_medicines,
    get_inventory_movement,
    get_medicine_consumption_report
)
from app.forms.inventory_forms import (
    OpeningStockForm,
    StockAdjustmentForm,
    InventoryFilterForm,
    BatchManagementForm
)
from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission, permission_required

inventory_views_bp = Blueprint('inventory_views', __name__, url_prefix='/inventory')

@inventory_views_bp.route('/', methods=['GET'])
@login_required
@permission_required('inventory', 'view')
def inventory_list():
    """Display the current inventory stock levels."""
    form = InventoryFilterForm()
    
    medicine_id = request.args.get('medicine_id')
    batch = request.args.get('batch')
    
    try:
        with get_db_session() as session:
            stock_details = get_stock_details(
                session, 
                current_user.hospital_id,
                medicine_id=medicine_id,
                batch=batch
            )
            
        return render_template(
            'inventory/stock_list.html',
            stock_details=stock_details,
            form=form
        )
    except Exception as e:
        current_app.logger.error(f"Error in inventory_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving inventory: {str(e)}", "error")
        return render_template('inventory/stock_list.html', form=form, stock_details=[])

@inventory_views_bp.route('/movement', methods=['GET'])
@login_required
@permission_required('inventory', 'view')
def inventory_movement():
    """Display inventory movement history with filtering."""
    form = InventoryFilterForm()
    
    medicine_id = request.args.get('medicine_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    stock_type = request.args.get('stock_type')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        with get_db_session() as session:
            movements, total = get_inventory_movement(
                session, 
                current_user.hospital_id,
                medicine_id=medicine_id,
                start_date=start_date,
                end_date=end_date,
                stock_type=stock_type,
                page=page,
                per_page=per_page
            )
            
        return render_template(
            'inventory/stock_movement.html',
            movements=movements,
            form=form,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Error in inventory_movement: {str(e)}", exc_info=True)
        flash(f"Error retrieving inventory movements: {str(e)}", "error")
        return render_template('inventory/stock_movement.html', form=form, movements=[])

@inventory_views_bp.route('/opening-stock', methods=['GET', 'POST'])
@login_required
@permission_required('inventory', 'add')
def add_opening_stock():
    """Add opening stock for a medicine."""
    form = OpeningStockForm()
    
    if form.validate_on_submit():
        try:
            with get_db_session() as session:
                record_opening_stock(
                    session,
                    current_user.hospital_id,
                    medicine_id=form.medicine_id.data,
                    batch=form.batch.data,
                    expiry=form.expiry_date.data,
                    quantity=form.quantity.data,
                    pack_purchase_price=form.pack_purchase_price.data,
                    pack_mrp=form.pack_mrp.data,
                    units_per_pack=form.units_per_pack.data,
                    location=form.location.data,
                    created_by=current_user.user_id
                )
                
            flash("Opening stock recorded successfully", "success")
            return redirect(url_for('inventory_views.inventory_list'))
        except Exception as e:
            current_app.logger.error(f"Error in add_opening_stock: {str(e)}", exc_info=True)
            flash(f"Error recording opening stock: {str(e)}", "error")
    
    return render_template('inventory/adjustment_form.html', form=form, title="Record Opening Stock")

@inventory_views_bp.route('/adjustment', methods=['GET', 'POST'])
@login_required
@permission_required('inventory', 'add')
def stock_adjustment():
    """Record stock adjustment (increase/decrease)."""
    form = StockAdjustmentForm()
    
    if form.validate_on_submit():
        try:
            with get_db_session() as session:
                record_stock_adjustment(
                    session,
                    current_user.hospital_id,
                    medicine_id=form.medicine_id.data,
                    batch=form.batch.data,
                    adjustment_quantity=form.quantity.data,
                    reason=form.reason.data,
                    adjustment_type=form.adjustment_type.data,
                    location=form.location.data,
                    created_by=current_user.user_id
                )
                
            flash("Stock adjustment recorded successfully", "success")
            return redirect(url_for('inventory_views.inventory_list'))
        except Exception as e:
            current_app.logger.error(f"Error in stock_adjustment: {str(e)}", exc_info=True)
            flash(f"Error recording stock adjustment: {str(e)}", "error")
    
    return render_template('inventory/adjustment_form.html', form=form, title="Record Stock Adjustment")

@inventory_views_bp.route('/batch-management', methods=['GET', 'POST'])
@login_required
@permission_required('inventory', 'manage')
def batch_management():
    """Manage medicine batches and expiry."""
    form = BatchManagementForm()
    
    medicine_id = request.args.get('medicine_id')
    
    try:
        with get_db_session() as session:
            if medicine_id:
                batches = get_stock_details(session, current_user.hospital_id, medicine_id=medicine_id)
            else:
                batches = []
            
        return render_template(
            'inventory/batch_management.html',
            batches=batches,
            form=form
        )
    except Exception as e:
        current_app.logger.error(f"Error in batch_management: {str(e)}", exc_info=True)
        flash(f"Error retrieving batch information: {str(e)}", "error")
        return render_template('inventory/batch_management.html', form=form, batches=[])

@inventory_views_bp.route('/low-stock', methods=['GET'])
@login_required
@permission_required('inventory', 'view')
def low_stock():
    """Display medicines with stock below safety level."""
    try:
        with get_db_session() as session:
            low_stock_items = get_low_stock_medicines(session, current_user.hospital_id)
            
        return render_template(
            'inventory/low_stock.html',
            items=low_stock_items
        )
    except Exception as e:
        current_app.logger.error(f"Error in low_stock: {str(e)}", exc_info=True)
        flash(f"Error retrieving low stock information: {str(e)}", "error")
        return render_template('inventory/low_stock.html', items=[])

@inventory_views_bp.route('/expiring', methods=['GET'])
@login_required
@permission_required('inventory', 'view')
def expiring_stock():
    """Display medicines approaching expiry."""
    days = request.args.get('days', 90, type=int)
    
    try:
        with get_db_session() as session:
            expiring_items = get_expiring_medicines(session, current_user.hospital_id, days=days)
            
        return render_template(
            'inventory/expiring_stock.html',
            items=expiring_items,
            days=days
        )
    except Exception as e:
        current_app.logger.error(f"Error in expiring_stock: {str(e)}", exc_info=True)
        flash(f"Error retrieving expiry information: {str(e)}", "error")
        return render_template('inventory/expiring_stock.html', items=[], days=days)

@inventory_views_bp.route('/consumption-report', methods=['GET'])
@login_required
@permission_required('inventory', 'view')
def consumption_report():
    """Generate medicine consumption report."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    medicine_id = request.args.get('medicine_id')
    
    try:
        with get_db_session() as session:
            report_data = get_medicine_consumption_report(
                session,
                current_user.hospital_id,
                start_date=start_date,
                end_date=end_date,
                medicine_id=medicine_id
            )
            
        return render_template(
            'inventory/consumption_report.html',
            report_data=report_data,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        current_app.logger.error(f"Error in consumption_report: {str(e)}", exc_info=True)
        flash(f"Error generating consumption report: {str(e)}", "error")
        return render_template('inventory/consumption_report.html', report_data=[], start_date=start_date, end_date=end_date)

# API endpoints for AJAX requests
@inventory_views_bp.route('/api/medicine-batches', methods=['GET'])
@login_required
def get_medicine_batches():
    """API endpoint to get batches for a specific medicine."""
    medicine_id = request.args.get('medicine_id')
    
    if not medicine_id:
        return jsonify({'error': 'Medicine ID is required'}), 400
    
    try:
        with get_db_session() as session:
            batches = get_stock_details(session, current_user.hospital_id, medicine_id=medicine_id)
            batch_data = [{'batch': b.batch, 'expiry': b.expiry.isoformat(), 'stock': b.current_stock} for b in batches]
            
        return jsonify({'batches': batch_data})
    except Exception as e:
        current_app.logger.error(f"Error in get_medicine_batches: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500