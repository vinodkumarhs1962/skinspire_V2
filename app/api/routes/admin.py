# skinspire_v2/app/api/routes/admin.py

from flask import Blueprint, jsonify, request, render_template
from app.services.database_service import get_db_session
from app.services.config_master_sync_service import sync_config_to_masters, generate_sync_report
from flask_login import login_required
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'})


@admin_bp.route('/sync-config-to-masters', methods=['POST'])
@login_required
def sync_config_to_masters_endpoint():
    """
    Sync currently effective pricing/GST configs from entity_pricing_tax_config to master tables.

    Request Body:
    {
        "hospital_id": "uuid or null for all",
        "entity_type": "medicine|service|package or null for all",
        "dry_run": true/false (default: true),
        "update_pricing": true/false (default: true),
        "update_gst": true/false (default: true)
    }

    Returns:
    {
        "success": true/false,
        "summary": {
            "total_updated": 5,
            "medicines_updated": 3,
            "services_updated": 2,
            "packages_updated": 0,
            "total_skipped": 10,
            "total_errors": 0
        },
        "changes": [...],
        "errors": [...],
        "report_html": "...",
        "report_text": "..."
    }
    """
    try:
        data = request.get_json() or {}

        hospital_id = data.get('hospital_id')
        entity_type = data.get('entity_type')
        dry_run = data.get('dry_run', True)
        update_pricing = data.get('update_pricing', True)
        update_gst = data.get('update_gst', True)

        logger.info(f"Sync config to masters: hospital_id={hospital_id}, entity_type={entity_type}, "
                   f"dry_run={dry_run}, update_pricing={update_pricing}, update_gst={update_gst}")

        with get_db_session() as session:
            result = sync_config_to_masters(
                session=session,
                hospital_id=hospital_id,
                entity_type=entity_type,
                dry_run=dry_run,
                update_pricing=update_pricing,
                update_gst=update_gst,
                current_user_id=request.user_id if hasattr(request, 'user_id') else None
            )

            if not dry_run:
                session.commit()
                logger.info(f"Sync committed: {result.total_updated} records updated")
            else:
                session.rollback()
                logger.info(f"Dry run completed: Would update {result.total_updated} records")

            # Generate reports
            report_text = generate_sync_report(result, format='text')
            report_html = generate_sync_report(result, format='html')

            return jsonify({
                'success': True,
                'dry_run': dry_run,
                'summary': {
                    'total_updated': result.total_updated,
                    'medicines_updated': result.medicines_updated,
                    'services_updated': result.services_updated,
                    'packages_updated': result.packages_updated,
                    'total_skipped': result.total_skipped,
                    'total_errors': len(result.errors)
                },
                'changes': result.changes,
                'errors': result.errors,
                'report_text': report_text,
                'report_html': report_html
            })

    except Exception as e:
        logger.error(f"Error in sync_config_to_masters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/config-sync', methods=['GET'])
@login_required
def config_sync_page():
    """Render the config-to-master sync UI page"""
    return render_template('admin/config_sync.html')