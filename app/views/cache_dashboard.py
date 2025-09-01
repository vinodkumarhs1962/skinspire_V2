# app/views/cache_dashboard.py
# Cache Dashboard Routes and API Endpoints

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps  # CRITICAL: This import is REQUIRED
import logging

# Import your existing decorators and utilities
from app.security.authorization.permission_validator import has_permission
from app.utils.menu_utils import get_menu_items

logger = logging.getLogger(__name__)

# Create cache dashboard blueprint
cache_dashboard_bp = Blueprint('cache_dashboard', __name__, url_prefix='/admin')

def get_user_display_name(user):
    """Get a display-friendly name for the user"""
    try:
        # Try to get full name first
        if hasattr(user, 'full_name') and user.full_name:
            return user.full_name
        # Fall back to user_id (phone number)
        return user.user_id
    except Exception:
        return user.user_id if hasattr(user, 'user_id') else 'Unknown User'

def require_admin_permission(f):
    """Decorator to require admin permissions for cache dashboard access"""
    @wraps(f)  # CRITICAL: This decorator is REQUIRED to prevent endpoint conflicts
    def decorated_function(*args, **kwargs):
        if not has_permission(current_user, 'system', 'admin'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# DASHBOARD VIEW ROUTES
# ============================================================================

@cache_dashboard_bp.route('/cache-dashboard')
@login_required
@require_admin_permission
def cache_dashboard():
    """
    Main cache dashboard view - renders the HTML template with auto-refresh
    """
    try:
        # Get menu items for navigation
        menu_items = get_menu_items(current_user)
        
        # FIXED: Use helper function instead of .username
        logger.info(f"Cache dashboard accessed by user: {get_user_display_name(current_user)}")
        
        return render_template(
            'admin/cache_dashboard.html',
            menu_items=menu_items,
            current_date=datetime.now().strftime('%Y-%m-%d'),
            page_title='Cache Performance Dashboard'
        )
        
    except Exception as e:
        logger.error(f"Error rendering cache dashboard: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

# ============================================================================
# API ENDPOINTS FOR DASHBOARD DATA
# ============================================================================

@cache_dashboard_bp.route('/cache-dashboard/api/stats')
@login_required
@require_admin_permission
def api_cache_stats():
    """
    API endpoint to get current cache statistics
    Returns JSON data for the dashboard auto-refresh
    """
    try:
        # Import cache managers (handle import errors gracefully)
        try:
            from app.engine.universal_service_cache import get_service_cache_manager
            from app.engine.universal_config_cache import get_cached_configuration_loader
        except ImportError as import_error:
            logger.warning(f"Cache modules not available: {import_error}")
            return jsonify({
                'error': 'Cache system not available',
                'service_cache': _get_dummy_stats('service'),
                'config_cache': _get_dummy_stats('config')
            })
        
        # Get cache managers
        service_cache = get_service_cache_manager()
        config_cache = get_cached_configuration_loader()
        
        # Get statistics
        service_stats = service_cache.get_cache_statistics() if service_cache else _get_dummy_stats('service')
        config_stats = config_cache.get_cache_statistics() if config_cache else _get_dummy_stats('config')
        
        # Calculate additional metrics
        overall_hit_ratio = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
        performance_grade = _calculate_performance_grade(service_stats, config_stats)
        
        # Prepare response data
        response_data = {
            'timestamp': datetime.now().isoformat(),
            'service_cache': service_stats,
            'config_cache': config_stats,
            'overall_performance': {
                'hit_ratio': overall_hit_ratio,
                'grade': performance_grade,
                'status': _get_performance_status(overall_hit_ratio)
            },
            'recommendations': _generate_recommendations(service_stats, config_stats)
        }
        
        logger.debug(f"Cache stats API called - Service: {service_stats['hit_ratio']:.2%}, Config: {config_stats['hit_ratio']:.2%}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting cache statistics: {str(e)}")
        return jsonify({
            'error': str(e),
            'service_cache': _get_dummy_stats('service'),
            'config_cache': _get_dummy_stats('config')
        }), 500

@cache_dashboard_bp.route('/cache-dashboard/api/clear', methods=['POST'])
@login_required
@require_admin_permission
def api_clear_caches():
    """
    API endpoint to clear all caches
    """
    try:
        cleared_entries = 0
        
        # Clear service cache
        try:
            from app.engine.universal_service_cache import get_service_cache_manager
            service_cache = get_service_cache_manager()
            if service_cache:
                service_entries = service_cache.clear_all_cache()
                cleared_entries += service_entries
                logger.info(f"Cleared {service_entries} service cache entries")
        except ImportError:
            pass
        
        # Clear config cache
        try:
            from app.engine.universal_config_cache import get_cached_configuration_loader
            config_cache = get_cached_configuration_loader()
            if config_cache and hasattr(config_cache, 'clear_all_config_cache'):
                config_entries = config_cache.clear_all_config_cache()
                cleared_entries += config_entries
                logger.info(f"Cleared {config_entries} config cache entries")
        except ImportError:
            pass
        
        # FIXED: Use helper function instead of .username
        logger.info(f"Cache clear requested by user: {get_user_display_name(current_user)}, cleared {cleared_entries} entries")
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {cleared_entries} cache entries',
            'cleared_entries': cleared_entries
        })
        
    except Exception as e:
        logger.error(f"Error clearing caches: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to clear caches: {str(e)}'
        }), 500

@cache_dashboard_bp.route('/cache-dashboard/api/warmup', methods=['POST'])
@login_required
@require_admin_permission
def api_warmup_caches():
    """
    API endpoint to warm up caches
    """
    try:
        warmed_count = 0
        
        # Warm up config cache
        try:
            from app.engine.universal_config_cache import preload_common_configurations
            config_count = preload_common_configurations()
            warmed_count += config_count
            logger.info(f"Warmed {config_count} configuration entries")
        except ImportError:
            pass
        
        # FIXED: Use helper function instead of .username
        logger.info(f"Cache warmup requested by user: {get_user_display_name(current_user)}, warmed {warmed_count} entries")
        
        return jsonify({
            'success': True,
            'message': f'Successfully warmed {warmed_count} cache entries. Service cache will warm naturally with requests.',
            'warmed_entries': warmed_count
        })
        
    except Exception as e:
        logger.error(f"Error warming caches: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to warm caches: {str(e)}'
        }), 500

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_dummy_stats(cache_type):
    """Generate dummy statistics when cache is not available"""
    return {
        'cache_type': cache_type,
        'total_hits': 0,
        'total_misses': 0,
        'hit_ratio': 0.0,
        'cache_size': 0,
        'memory_usage': '0 KB',
        'last_cleared': None,
        'status': 'unavailable'
    }

def _calculate_performance_grade(service_stats, config_stats):
    """Calculate overall performance grade based on cache statistics"""
    avg_hit_ratio = (service_stats['hit_ratio'] + config_stats['hit_ratio']) / 2
    
    if avg_hit_ratio >= 0.9:
        return 'A+'
    elif avg_hit_ratio >= 0.8:
        return 'A'
    elif avg_hit_ratio >= 0.7:
        return 'B'
    elif avg_hit_ratio >= 0.6:
        return 'C'
    elif avg_hit_ratio >= 0.5:
        return 'D'
    else:
        return 'F'

def _get_performance_status(hit_ratio):
    """Get performance status based on hit ratio"""
    if hit_ratio >= 0.8:
        return 'excellent'
    elif hit_ratio >= 0.6:
        return 'good'
    elif hit_ratio >= 0.4:
        return 'fair'
    else:
        return 'poor'

def _generate_recommendations(service_stats, config_stats):
    """Generate recommendations based on cache performance"""
    recommendations = []
    
    # Service cache recommendations
    if service_stats['hit_ratio'] < 0.5:
        recommendations.append({
            'type': 'warning',
            'message': 'Service cache hit ratio is low. Consider warming the cache.',
            'action': 'warmup'
        })
    
    # Config cache recommendations
    if config_stats['hit_ratio'] < 0.7:
        recommendations.append({
            'type': 'info',
            'message': 'Configuration cache could be optimized. Review frequently accessed configs.',
            'action': 'optimize'
        })
    
    # Memory usage recommendations
    if service_stats.get('cache_size', 0) > 1000:
        recommendations.append({
            'type': 'info',
            'message': 'Service cache is large. Consider clearing old entries.',
            'action': 'clear'
        })
    
    # If everything is good
    if not recommendations:
        recommendations.append({
            'type': 'success',
            'message': 'Cache performance is optimal!',
            'action': None
        })
    
    return recommendations