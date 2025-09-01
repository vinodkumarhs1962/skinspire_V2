# =============================================================================
# UNIVERSAL VIEWS - INTEGRATED WITH EXISTING VIEW PATTERNS
# Following Skinspire HMS Existing View Structure and Patterns
# =============================================================================

# =============================================================================
# FILE: app/views/universal_views.py
# PURPOSE: Universal view handlers following your existing view patterns
# =============================================================================

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, g, abort
from flask_login import login_required, current_user
from datetime import datetime
import uuid
from typing import Dict, Any, Optional

# Import your existing patterns and services
from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission
from app.security.authorization.decorators import require_web_branch_permission

# Import universal architecture components
from app.config.entity_configurations import EntityType
from app.core.entity_registry import EntityConfigurationRegistry
from app.services.universal_search_service import UniversalSearchService
from app.services.universal_list_service import UniversalListService
from app.services.entity_integration_service import EntityIntegrationService

# Import your existing service integration helpers
from app.services.branch_service import get_branch_from_user_and_request
from app.services.permission_service import get_user_branch_context

# Create blueprint following your existing blueprint pattern
universal_bp = Blueprint('universal', __name__, url_prefix='/universal')

# =============================================================================
# HELPER FUNCTIONS - Following your existing helper patterns
# =============================================================================

def get_branch_context():
    """Helper function to get branch context - delegates to your existing service layer"""
    return get_user_branch_context(current_user.user_id, current_user.hospital_id, 'universal')

def get_branch_uuid_from_context_or_request():
    """Helper function to get branch UUID - delegates to your existing service layer"""
    return get_branch_from_user_and_request(current_user.user_id, current_user.hospital_id, 'universal')

def validate_entity_access(entity_type: str, action: str = 'view') -> tuple:
    """Validate entity access using your existing permission patterns"""
    try:
        # Get entity configuration
        entity_enum = EntityType(entity_type)
        config = EntityConfigurationRegistry.get_config(entity_enum)
        
        if not config:
            current_app.logger.error(f"No configuration found for entity type: {entity_type}")
            abort(404)
        
        # Check permissions using your existing permission system
        permission_module = config.permissions.module_name
        if not has_permission(current_user, permission_module, action):
            current_app.logger.warning(f"Permission denied for user {current_user.user_id} accessing {entity_type}/{action}")
            abort(403)
        
        return config, entity_enum
        
    except ValueError:
        current_app.logger.error(f"Invalid entity type: {entity_type}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error validating entity access: {str(e)}", exc_info=True)
        abort(500)

# =============================================================================
# ENTITY LIST ROUTES - Following your existing list route patterns
# =============================================================================

@universal_bp.route('/<entity_type>')
@login_required
def entity_list(entity_type):
    """
    Universal entity list handler following your existing list view patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get branch context using your existing patterns
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        # Prepare search filters (following your existing filter pattern)
        filters = request.args.to_dict()
        filters.update({
            'hospital_id': current_user.hospital_id,
            'branch_id': branch_uuid
        })
        
        # Get pagination parameters (following your existing pagination pattern)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', config.display.items_per_page, type=int)
        
        # Use universal search service (delegates to your existing services)
        search_service = UniversalSearchService(config)
        search_result = search_service.search(filters, page, per_page)
        
        # Use universal list service for formatting
        list_service = UniversalListService(config)
        template_data = list_service.prepare_list_data(search_result, filters)
        
        # Add branch context (following your existing pattern)
        template_data['branch_context'] = branch_context
        
        # Check for export request
        if request.args.get('export'):
            return handle_export(config, search_result, request.args.get('export'))
        
        # Render template (following your existing template pattern)
        return render_template('pages/universal/entity_list.html', **template_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal entity list for {entity_type}: {str(e)}", exc_info=True)
        flash(f"Error loading {entity_type}: {str(e)}", "error")
        return redirect(url_for('dashboard.index'))

@universal_bp.route('/<entity_type>/search')
@login_required  
def entity_search(entity_type):
    """
    Universal entity search page following your existing search patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get branch context
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        # Prepare search form data
        from app.forms.universal_forms import UniversalSearchForm
        form = UniversalSearchForm(config)
        
        template_data = {
            'config': config,
            'form': form,
            'branch_context': branch_context,
            'entity_type': entity_type
        }
        
        return render_template('pages/universal/entity_search.html', **template_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal entity search for {entity_type}: {str(e)}", exc_info=True)
        flash(f"Error loading search for {entity_type}: {str(e)}", "error")
        return redirect(url_for('universal.entity_list', entity_type=entity_type))

# =============================================================================
# ENTITY DETAIL ROUTES - Following your existing detail view patterns
# =============================================================================

@universal_bp.route('/<entity_type>/<entity_id>')
@login_required
def entity_view(entity_type, entity_id):
    """
    Universal entity detail view following your existing detail view patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get entity details using your existing database patterns
        with get_db_session() as session:
            entity = session.query(config.model_class).filter(
                getattr(config.model_class, config.primary_key) == entity_id,
                config.model_class.hospital_id == current_user.hospital_id
            ).first()
            
            if not entity:
                flash(f"{config.name} not found", "error")
                return redirect(url_for('universal.entity_list', entity_type=entity_type))
            
            # Format entity data for template
            entity_data = {}
            for field in config.fields:
                if field.show_in_view and hasattr(entity, field.name):
                    value = getattr(entity, field.name)
                    entity_data[field.name] = format_field_value(value, field)
            
            # Add primary key and title fields
            entity_data[config.primary_key] = getattr(entity, config.primary_key)
            entity_data['_title'] = getattr(entity, config.title_field) if config.title_field else ""
            entity_data['_subtitle'] = getattr(entity, config.subtitle_field) if config.subtitle_field else ""
            
            # Get related entities if configured
            related_data = {}
            if config.related_entities:
                related_data = get_related_entities(entity, config)
            
            # Get branch context
            branch_context = get_branch_context()
            
            template_data = {
                'config': config,
                'entity': entity_data,
                'related_data': related_data,
                'branch_context': branch_context,
                'entity_type': entity_type,
                'entity_id': entity_id
            }
            
            return render_template('pages/universal/entity_view.html', **template_data)
            
    except Exception as e:
        current_app.logger.error(f"Error in universal entity view for {entity_type}/{entity_id}: {str(e)}", exc_info=True)
        flash(f"Error loading {config.name if 'config' in locals() else entity_type}: {str(e)}", "error")
        return redirect(url_for('universal.entity_list', entity_type=entity_type))

# =============================================================================
# ENTITY CRUD ROUTES - Following your existing CRUD patterns
# =============================================================================

@universal_bp.route('/<entity_type>/create', methods=['GET', 'POST'])
@login_required
def entity_create(entity_type):
    """
    Universal entity creation following your existing create patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'create')
        
        # Import and create form dynamically
        from app.forms.universal_forms import UniversalEntityForm
        form = UniversalEntityForm(config)
        
        if request.method == 'POST' and form.validate_on_submit():
            # Handle entity creation using your existing patterns
            return handle_entity_creation(config, form.data)
        
        # Get branch context
        branch_context = get_branch_context()
        
        template_data = {
            'config': config,
            'form': form,
            'branch_context': branch_context,
            'entity_type': entity_type,
            'mode': 'create'
        }
        
        return render_template('pages/universal/entity_form.html', **template_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal entity create for {entity_type}: {str(e)}", exc_info=True)
        flash(f"Error creating {entity_type}: {str(e)}", "error")
        return redirect(url_for('universal.entity_list', entity_type=entity_type))

@universal_bp.route('/<entity_type>/<entity_id>/edit', methods=['GET', 'POST'])
@login_required
def entity_edit(entity_type, entity_id):
    """
    Universal entity editing following your existing edit patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'edit')
        
        # Get existing entity using your database patterns
        with get_db_session() as session:
            entity = session.query(config.model_class).filter(
                getattr(config.model_class, config.primary_key) == entity_id,
                config.model_class.hospital_id == current_user.hospital_id
            ).first()
            
            if not entity:
                flash(f"{config.name} not found", "error")
                return redirect(url_for('universal.entity_list', entity_type=entity_type))
            
            # Create form with existing data
            from app.forms.universal_forms import UniversalEntityForm
            form = UniversalEntityForm(config, obj=entity)
            
            if request.method == 'POST' and form.validate_on_submit():
                # Handle entity update using your existing patterns
                return handle_entity_update(config, entity, form.data)
            
            # Get branch context
            branch_context = get_branch_context()
            
            template_data = {
                'config': config,
                'form': form,
                'entity': entity,
                'branch_context': branch_context,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'mode': 'edit'
            }
            
            return render_template('pages/universal/entity_form.html', **template_data)
            
    except Exception as e:
        current_app.logger.error(f"Error in universal entity edit for {entity_type}/{entity_id}: {str(e)}", exc_info=True)
        flash(f"Error editing {entity_type}: {str(e)}", "error")
        return redirect(url_for('universal.entity_view', entity_type=entity_type, entity_id=entity_id))

# =============================================================================
# CUSTOM ACTION ROUTES - Following your existing custom action patterns
# =============================================================================

@universal_bp.route('/<entity_type>/<entity_id>/action/<action_id>', methods=['GET', 'POST'])
@login_required
def entity_action(entity_type, entity_id, action_id):
    """
    Universal custom action handler following your existing action patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Find the action definition
        action_def = None
        for action in config.actions:
            if action.action_id == action_id:
                action_def = action
                break
        
        if not action_def:
            flash(f"Action {action_id} not found", "error")
            return redirect(url_for('universal.entity_view', entity_type=entity_type, entity_id=entity_id))
        
        # Check action-specific permissions
        if action_def.permission_required:
            if not has_permission(current_user, config.permissions.module_name, action_def.permission_required):
                flash("Permission denied", "error")
                return redirect(url_for('universal.entity_view', entity_type=entity_type, entity_id=entity_id))
        
        # Handle custom actions using integration service
        user_context = {
            'user_id': current_user.user_id,
            'hospital_id': current_user.hospital_id,
            'branch_context': get_branch_context()
        }
        
        result = EntityIntegrationService.handle_custom_action(
            entity_enum, action_id, entity_id, user_context
        )
        
        if result.get('success'):
            if result.get('redirect_url'):
                return redirect(result['redirect_url'])
            else:
                flash(f"Action {action_id} completed successfully", "success")
        else:
            flash(f"Action {action_id} failed: {result.get('error', 'Unknown error')}", "error")
        
        return redirect(url_for('universal.entity_view', entity_type=entity_type, entity_id=entity_id))
        
    except Exception as e:
        current_app.logger.error(f"Error in universal entity action {action_id} for {entity_type}/{entity_id}: {str(e)}", exc_info=True)
        flash(f"Error executing action: {str(e)}", "error")
        return redirect(url_for('universal.entity_view', entity_type=entity_type, entity_id=entity_id))

# =============================================================================
# AJAX ROUTES - Following your existing AJAX patterns
# =============================================================================

@universal_bp.route('/api/<entity_type>/search')
@login_required
def api_entity_search(entity_type):
    """
    Universal entity search API following your existing API patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get search parameters
        search_term = request.args.get('q', '')
        limit = request.args.get('limit', 10, type=int)
        
        # Get branch context
        branch_uuid, _ = get_branch_uuid_from_context_or_request()
        
        # Prepare filters
        filters = {
            'search': search_term,
            'hospital_id': current_user.hospital_id,
            'branch_id': branch_uuid
        }
        
        # Use universal search service
        search_service = UniversalSearchService(config)
        result = search_service.search(filters, page=1, per_page=limit)
        
        # Format for API response
        api_result = {
            'success': True,
            'data': [
                {
                    'id': item.get(config.primary_key),
                    'text': item.get('_title', ''),
                    'subtitle': item.get('_subtitle', ''),
                    'data': item
                }
                for item in result['items']
            ],
            'total': result['total']
        }
        
        return jsonify(api_result)
        
    except Exception as e:
        current_app.logger.error(f"Error in API entity search for {entity_type}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@universal_bp.route('/api/<entity_type>/<entity_id>')
@login_required
def api_entity_get(entity_type, entity_id):
    """
    Universal entity get API following your existing API patterns
    """
    try:
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get entity using your existing database patterns
        with get_db_session() as session:
            entity = session.query(config.model_class).filter(
                getattr(config.model_class, config.primary_key) == entity_id,
                config.model_class.hospital_id == current_user.hospital_id
            ).first()
            
            if not entity:
                return jsonify({
                    'success': False,
                    'error': f"{config.name} not found"
                }), 404
            
            # Format entity data
            entity_data = {}
            for field in config.fields:
                if hasattr(entity, field.name):
                    value = getattr(entity, field.name)
                    entity_data[field.name] = format_field_value(value, field)
            
            entity_data[config.primary_key] = getattr(entity, config.primary_key)
            
            return jsonify({
                'success': True,
                'data': entity_data
            })
            
    except Exception as e:
        current_app.logger.error(f"Error in API entity get for {entity_type}/{entity_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# MIGRATION AND TESTING ROUTES - For parallel implementation testing
# =============================================================================

@universal_bp.route('/migration/<entity_type>/compare')
@login_required
def migration_compare(entity_type):
    """
    Migration testing route for side-by-side comparison
    """
    try:
        # Only available in development/staging
        if current_app.config.get('ENV') == 'production':
            abort(404)
        
        # Validate access and get configuration
        config, entity_enum = validate_entity_access(entity_type, 'view')
        
        # Get both old and new implementations
        # This would call both your existing service and universal service
        filters = request.args.to_dict()
        filters.update({
            'hospital_id': current_user.hospital_id
        })
        
        # Universal implementation
        universal_service = UniversalSearchService(config)
        universal_result = universal_service.search(filters)
        
        # Legacy implementation (if available)
        legacy_result = get_legacy_implementation_result(entity_type, filters)
        
        template_data = {
            'config': config,
            'universal_result': universal_result,
            'legacy_result': legacy_result,
            'entity_type': entity_type,
            'filters': filters
        }
        
        return render_template('migration/side_by_side.html', **template_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in migration compare for {entity_type}: {str(e)}", exc_info=True)
        flash(f"Error in migration compare: {str(e)}", "error")
        return redirect(url_for('universal.entity_list', entity_type=entity_type))

# =============================================================================
# HELPER FUNCTIONS - Following your existing helper patterns
# =============================================================================

def format_field_value(value, field):
    """Format field value for display following your existing formatting patterns"""
    if value is None:
        return ""
    
    if field.field_type.value == 'date':
        return value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
    elif field.field_type.value == 'datetime':
        return value.strftime('%Y-%m-%d %H:%M') if hasattr(value, 'strftime') else str(value)
    elif field.field_type.value == 'amount':
        return float(value) if value else 0.0
    elif field.field_type.value == 'boolean':
        return bool(value)
    else:
        return str(value)

def get_related_entities(entity, config):
    """Get related entities for display"""
    related_data = {}
    
    # This would be expanded based on your specific relationship needs
    for related_entity_type in config.related_entities:
        try:
            # Get related entities using your existing patterns
            related_data[related_entity_type] = get_related_entity_data(entity, related_entity_type)
        except Exception as e:
            current_app.logger.warning(f"Error getting related entity {related_entity_type}: {str(e)}")
            related_data[related_entity_type] = []
    
    return related_data

def get_related_entity_data(entity, related_entity_type):
    """Get related entity data using your existing relationship patterns"""
    # This would delegate to your existing services
    # Example implementation for supplier invoices -> payments
    if related_entity_type == 'supplier_payments' and hasattr(entity, 'invoice_id'):
        from app.services.supplier_service import get_payments_for_invoice
        return get_payments_for_invoice(entity.invoice_id)
    
    return []

def handle_entity_creation(config, form_data):
    """Handle entity creation using your existing creation patterns"""
    try:
        with get_db_session() as session:
            # Create new entity instance
            entity = config.model_class()
            
            # Set form data
            for field in config.fields:
                if field.name in form_data and hasattr(entity, field.name):
                    setattr(entity, field.name, form_data[field.name])
            
            # Set standard fields
            if hasattr(entity, 'hospital_id'):
                entity.hospital_id = current_user.hospital_id
            if hasattr(entity, 'created_by'):
                entity.created_by = current_user.user_id
            if hasattr(entity, 'created_at'):
                entity.created_at = datetime.utcnow()
            
            session.add(entity)
            session.flush()  # Get the ID
            
            flash(f"{config.name} created successfully", "success")
            return redirect(url_for('universal.entity_view', 
                                  entity_type=config.entity_type.value, 
                                  entity_id=getattr(entity, config.primary_key)))
            
    except Exception as e:
        current_app.logger.error(f"Error creating entity: {str(e)}", exc_info=True)
        flash(f"Error creating {config.name}: {str(e)}", "error")
        return redirect(url_for('universal.entity_list', entity_type=config.entity_type.value))

def handle_entity_update(config, entity, form_data):
    """Handle entity update using your existing update patterns"""
    try:
        with get_db_session() as session:
            # Update entity with form data
            for field in config.fields:
                if field.name in form_data and hasattr(entity, field.name):
                    setattr(entity, field.name, form_data[field.name])
            
            # Set modification fields
            if hasattr(entity, 'modified_by'):
                entity.modified_by = current_user.user_id
            if hasattr(entity, 'modified_at'):
                entity.modified_at = datetime.utcnow()
            
            session.merge(entity)
            
            flash(f"{config.name} updated successfully", "success")
            return redirect(url_for('universal.entity_view', 
                                  entity_type=config.entity_type.value, 
                                  entity_id=getattr(entity, config.primary_key)))
            
    except Exception as e:
        current_app.logger.error(f"Error updating entity: {str(e)}", exc_info=True)
        flash(f"Error updating {config.name}: {str(e)}", "error")
        return redirect(url_for('universal.entity_view', 
                              entity_type=config.entity_type.value, 
                              entity_id=getattr(entity, config.primary_key)))

def handle_export(config, search_result, export_format):
    """Handle data export following your existing export patterns"""
    try:
        if export_format == 'csv':
            return export_to_csv(config, search_result)
        elif export_format == 'excel':
            return export_to_excel(config, search_result)
        else:
            flash("Unsupported export format", "error")
            return redirect(request.referrer or url_for('universal.entity_list', entity_type=config.entity_type.value))
            
    except Exception as e:
        current_app.logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        flash(f"Error exporting data: {str(e)}", "error")
        return redirect(request.referrer or url_for('universal.entity_list', entity_type=config.entity_type.value))

def export_to_csv(config, search_result):
    """Export to CSV following your existing export patterns"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = [field.label for field in config.fields if field.show_in_list]
    writer.writerow(headers)
    
    # Write data
    for item in search_result['items']:
        row = []
        for field in config.fields:
            if field.show_in_list:
                value = item.get(field.name, '')
                row.append(str(value) if value else '')
        writer.writerow(row)
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={config.plural_name.lower()}.csv'
        }
    )

def get_legacy_implementation_result(entity_type, filters):
    """Get result from legacy implementation for comparison"""
    # This would call your existing implementation
    # Example for supplier invoices
    if entity_type == 'supplier_invoices':
        try:
            from app.services.supplier_service import search_supplier_invoices
            return search_supplier_invoices(
                hospital_id=filters.get('hospital_id'),
                supplier_id=filters.get('supplier_id'),
                # ... map other filters
            )
        except Exception as e:
            current_app.logger.warning(f"Error getting legacy result: {str(e)}")
            return {'items': [], 'total': 0}
    
    return {'items': [], 'total': 0}

# =============================================================================
# ERROR HANDLERS - Following your existing error handling patterns
# =============================================================================

@universal_bp.errorhandler(403)
def handle_forbidden(e):
    """Handle 403 errors following your existing error patterns"""
    flash("Access denied", "error")
    return redirect(url_for('dashboard.index'))

@universal_bp.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors following your existing error patterns"""
    flash("Resource not found", "error")
    return redirect(url_for('dashboard.index'))

@universal_bp.errorhandler(500)
def handle_server_error(e):
    """Handle 500 errors following your existing error patterns"""
    current_app.logger.error(f"Universal views server error: {str(e)}", exc_info=True)
    flash("An unexpected error occurred", "error")
    return redirect(url_for('dashboard.index'))

# =============================================================================
# REGISTER BLUEPRINT - Following your existing blueprint registration pattern
# =============================================================================

def register_universal_blueprint(app):
    """Register universal blueprint with the app"""
    app.register_blueprint(universal_bp)

# =============================================================================
# INTEGRATION WITH EXISTING VIEWS - Enhancement examples
# =============================================================================

"""
Example integration with your existing supplier_views.py:

# In app/views/supplier_views.py (add these routes alongside existing ones)

@supplier_views_bp.route('/invoices/universal', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view')
def supplier_invoice_list_universal():
    '''Universal implementation of supplier invoice list'''
    return universal_bp.view_functions['entity_list']('supplier_invoices')

@supplier_views_bp.route('/universal', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view')
def supplier_list_universal():
    '''Universal implementation of supplier list'''
    return universal_bp.view_functions['entity_list']('suppliers')

# This allows testing universal implementation alongside existing implementation
"""