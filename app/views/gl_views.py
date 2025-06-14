# app/views/gl_views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.services.gl_service import (
    get_gl_transaction_by_id,
    search_gl_transactions
)
from app.forms.gl_forms import (
    GLTransactionFilterForm,
    GLReportForm,
    GSTReportForm
)
from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission, permission_required
import datetime

gl_views_bp = Blueprint('gl_views', __name__, url_prefix='/gl')

@gl_views_bp.route('/transactions', methods=['GET'])
@login_required
@permission_required('gl', 'view')
def transaction_list():
    """Display list of GL transactions with filtering."""
    form = GLTransactionFilterForm()
    
    transaction_type = request.args.get('transaction_type')
    reference_id = request.args.get('reference_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_amount = request.args.get('min_amount')
    max_amount = request.args.get('max_amount')
    account_id = request.args.get('account_id')
    reconciliation_status = request.args.get('reconciliation_status')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        with get_db_session() as session:
            transactions, total = search_gl_transactions(
                session, 
                current_user.hospital_id,
                transaction_type=transaction_type,
                reference_id=reference_id,
                start_date=start_date,
                end_date=end_date,
                min_amount=min_amount,
                max_amount=max_amount,
                account_id=account_id,
                reconciliation_status=reconciliation_status,
                page=page,
                per_page=per_page
            )
            
        return render_template(
            'gl/transaction_list.html',
            transactions=transactions,
            form=form,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Error in transaction_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving GL transactions: {str(e)}", "error")
        return render_template('gl/transaction_list.html', form=form, transactions=[])

@gl_views_bp.route('/transaction/<transaction_id>', methods=['GET'])
@login_required
@permission_required('gl', 'view')
def transaction_detail(transaction_id):
    """View GL transaction details."""
    try:
        with get_db_session() as session:
            transaction = get_gl_transaction_by_id(
                session, 
                current_user.hospital_id, 
                transaction_id,
                include_entries=True
            )
            
            if not transaction:
                flash("Transaction not found", "error")
                return redirect(url_for('gl_views.transaction_list'))
                
            return render_template('gl/transaction_detail.html', transaction=transaction)
    except Exception as e:
        current_app.logger.error(f"Error in transaction_detail: {str(e)}", exc_info=True)
        flash(f"Error retrieving transaction details: {str(e)}", "error")
        return redirect(url_for('gl_views.transaction_list'))

@gl_views_bp.route('/financial-reports', methods=['GET', 'POST'])
@login_required
@permission_required('gl', 'report')
def financial_reports():
    """Generate financial reports."""
    form = GLReportForm()
    
    if form.validate_on_submit():
        report_type = form.report_type.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        
        # Redirect to the specific report view with parameters
        return redirect(url_for(
            'gl_views.generate_report',
            report_type=report_type,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        ))
        
    return render_template('gl/financial_reports.html', form=form)

@gl_views_bp.route('/reports/<report_type>', methods=['GET'])
@login_required
@permission_required('gl', 'report')
def generate_report(report_type):
    """Generate a specific financial report."""
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        with get_db_session() as session:
            # This is a placeholder. In a real implementation, you would have different
            # report generation services for different report types
            if report_type == 'trial_balance':
                # Generate trial balance report
                # This would call a service function like gl_service.generate_trial_balance()
                report_data = {"title": "Trial Balance", "data": []}
                template = 'gl/trial_balance.html'
            elif report_type == 'profit_loss':
                # Generate profit and loss report
                # This would call a service function like gl_service.generate_profit_loss()
                report_data = {"title": "Profit and Loss", "data": []}
                template = 'gl/profit_loss.html'
            elif report_type == 'balance_sheet':
                # Generate balance sheet report
                # This would call a service function like gl_service.generate_balance_sheet()
                report_data = {"title": "Balance Sheet", "data": []}
                template = 'gl/balance_sheet.html'
            else:
                flash(f"Unknown report type: {report_type}", "error")
                return redirect(url_for('gl_views.financial_reports'))
            
        return render_template(
            template,
            report=report_data,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        current_app.logger.error(f"Error in generate_report: {str(e)}", exc_info=True)
        flash(f"Error generating report: {str(e)}", "error")
        return redirect(url_for('gl_views.financial_reports'))

@gl_views_bp.route('/gst-reports', methods=['GET', 'POST'])
@login_required
@permission_required('gl', 'report')
def gst_reports():
    """Generate GST reports."""
    form = GSTReportForm()
    
    if form.validate_on_submit():
        report_type = form.report_type.data
        month = form.month.data
        year = form.year.data
        
        # Redirect to the specific GST report view with parameters
        return redirect(url_for(
            'gl_views.generate_gst_report',
            report_type=report_type,
            month=month,
            year=year
        ))
        
    return render_template('gl/gst_reports.html', form=form)

@gl_views_bp.route('/gst-report/<report_type>', methods=['GET'])
@login_required
@permission_required('gl', 'report')
def generate_gst_report(report_type):
    """Generate a specific GST report."""
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    try:
        with get_db_session() as session:
            # This is a placeholder. In a real implementation, you would have different
            # report generation services for different report types
            if report_type == 'gstr1':
                # Generate GSTR-1 report (Outward Supplies)
                # This would call a service function like gl_service.generate_gstr1()
                report_data = {"title": "GSTR-1 Report", "data": []}
                template = 'gl/gstr1.html'
            elif report_type == 'gstr2a':
                # Generate GSTR-2A report (Inward Supplies)
                # This would call a service function like gl_service.generate_gstr2a()
                report_data = {"title": "GSTR-2A Report", "data": []}
                template = 'gl/gstr2a.html'
            elif report_type == 'gstr3b':
                # Generate GSTR-3B report (Summary Return)
                # This would call a service function like gl_service.generate_gstr3b()
                report_data = {"title": "GSTR-3B Report", "data": []}
                template = 'gl/gstr3b.html'
            else:
                flash(f"Unknown GST report type: {report_type}", "error")
                return redirect(url_for('gl_views.gst_reports'))
            
        return render_template(
            template,
            report=report_data,
            month=month,
            year=year
        )
    except Exception as e:
        current_app.logger.error(f"Error in generate_gst_report: {str(e)}", exc_info=True)
        flash(f"Error generating GST report: {str(e)}", "error")
        return redirect(url_for('gl_views.gst_reports'))

@gl_views_bp.route('/account-reconciliation', methods=['GET'])
@login_required
@permission_required('gl', 'reconcile')
def account_reconciliation():
    """Account reconciliation view."""
    account_id = request.args.get('account_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # This is a placeholder. In a real implementation, you would load transactions
    # for the selected account and date range that need reconciliation.
    try:
        with get_db_session() as session:
            # This would call a service function like gl_service.get_unreconciled_transactions()
            transactions = []
            
        return render_template(
            'gl/account_reconciliation.html',
            transactions=transactions,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        current_app.logger.error(f"Error in account_reconciliation: {str(e)}", exc_info=True)
        flash(f"Error loading reconciliation data: {str(e)}", "error")
        return render_template('gl/account_reconciliation.html', transactions=[])

@gl_views_bp.route('/reconcile-transaction', methods=['POST'])
@login_required
@permission_required('gl', 'reconcile')
def reconcile_transaction():
    """Mark a transaction as reconciled."""
    transaction_id = request.form.get('transaction_id')
    reconciled = request.form.get('reconciled', 'false') == 'true'
    
    # This is a placeholder. In a real implementation, you would update the transaction's
    # reconciliation status in the database.
    try:
        with get_db_session() as session:
            # This would call a service function like gl_service.update_reconciliation_status()
            status = "reconciled" if reconciled else "pending"
            
        return jsonify({"success": True, "status": status})
    except Exception as e:
        current_app.logger.error(f"Error in reconcile_transaction: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500