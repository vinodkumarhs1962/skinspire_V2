# app/utils/menu_utils.py - FIXED VERSION
# Corrects all URLs to match actual registered blueprints

from flask import url_for
from app.services.database_service import get_detached_copy
import logging

logger = logging.getLogger(__name__)

def safe_url_for(endpoint, **values):
    """
    Helper function to safely create URLs for potentially missing blueprints
    Returns '#' placeholder if blueprint is not registered
    """
    try:
        return url_for(endpoint, _external=False, **values)
    except Exception as e:
        logger.warning(f"Blueprint endpoint '{endpoint}' not available: {str(e)}")
        return '#'

def universal_url(entity_type, action, item_id=None, **kwargs):
    """Generate universal engine URLs - ONLY for configured entities"""
    
    # MANUAL CHECK: Only these entities are configured in Universal Engine
    CONFIGURED_ENTITIES = [
        'suppliers',
        'supplier_payments', 
        'patients',
        'medicines',
        'users',
        'branches',
        'inventory'  # If you have this configured
    ]
    
    if entity_type not in CONFIGURED_ENTITIES:
        logger.warning(f"Entity {entity_type} not configured in Universal Engine")
        return '#'
    
    try:
        if action == 'list':
            return url_for('universal_views.universal_list_view', entity_type=entity_type, **kwargs)
        elif action == 'view' and item_id:
            return url_for('universal_views.universal_detail_view', entity_type=entity_type, item_id=item_id, **kwargs)
        elif action == 'create':
            return url_for('universal_views.universal_create_view', entity_type=entity_type, **kwargs)
        elif action == 'edit' and item_id:
            return url_for('universal_views.universal_edit_view', entity_type=entity_type, item_id=item_id, **kwargs)
        elif action == 'document' and item_id:
            return url_for('universal_views.universal_document_view', entity_type=entity_type, item_id=item_id, **kwargs)
        else:
            return '#'
    except Exception as e:
        logger.warning(f"Error generating universal URL: {str(e)}")
        return '#'

def generate_menu_for_role(role):
    """Generate menu items based on user role - FIXED VERSION"""
    
    # Basic menu items available to all users
    menu = [
        {
            'name': 'Dashboard',
            'url': url_for('auth_views.dashboard'),
            'icon': 'home',
            'icon_path': '3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
        }
    ]
    
    if role in ['staff', 'system_admin', 'hospital_admin']:
        
        # =========================================================================
        # 1. MASTER DATA (UNIVERSAL ENGINE)
        # =========================================================================
        menu.append({
            'name': 'Master Data',
            'url': '#',
            'icon': 'database',
            'icon_path': '4 7v10a2 2 0 002 2h12a2 2 0 002-2V7M4 7h16M4 7l2-3h12l2 3',
            'children': [
                {
                    'name': 'Suppliers',
                    'url': universal_url('suppliers', 'list'),
                    'icon': 'truck',
                    'badge': 'Universal',
                    'badge_color': 'primary'
                },
                {
                    'name': 'Patients',
                    'url': universal_url('patients', 'list'),
                    'icon': 'users',
                    'badge': 'Universal',
                    'badge_color': 'primary'
                },
                {
                    'name': 'Medicines',
                    'url': universal_url('medicines', 'list'),
                    'icon': 'pills',
                    'badge': 'Universal',
                    'badge_color': 'primary'
                },
                {
                    'name': 'Users',
                    'url': universal_url('users', 'list'),
                    'icon': 'user-friends',
                    'badge': 'Universal',
                    'badge_color': 'primary'
                },
                {
                    'name': 'Branches',
                    'url': universal_url('branches', 'list'),
                    'icon': 'building',
                    'badge': 'Universal',
                    'badge_color': 'primary'
                }
            ]
        })
        
        # =========================================================================
        # 2. FINANCIAL MANAGEMENT (FIXED URLS)
        # =========================================================================
        menu.append({
            'name': 'Financial Management',
            'url': '#',
            'icon': 'money-check-alt',
            'icon_path': '12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z',
            'children': [
                {
                    'name': 'Supplier Payments',
                    'url': universal_url('supplier_payments', 'list'),
                    'icon': 'hand-holding-usd',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [
                        {
                            'name': 'Payment List',
                            'url': universal_url('supplier_payments', 'list'),
                            'icon': 'list',
                            'description': 'View and print payments'
                        },
                        {
                            'name': 'Create Payment',
                            'url': safe_url_for('supplier_views.create_payment'),
                            'icon': 'plus-circle',
                            'description': 'Create new payment'
                        }
                    ]
                },
                {
                    'name': 'Supplier Invoices',
                    'url': safe_url_for('supplier_views.supplier_invoice_list'),  # FIXED
                    'icon': 'file-invoice',
                    'badge': 'Standard',
                    'badge_color': 'secondary',
                    'children': [
                        {
                            'name': 'Invoice List',
                            'url': safe_url_for('supplier_views.supplier_invoice_list'),  # FIXED
                            'icon': 'list',
                            'description': 'View and print invoices'
                        },
                        {
                            'name': 'Pending Invoices',
                            'url': safe_url_for('supplier_views.pending_invoices'),  # FIXED
                            'icon': 'clock',
                            'description': 'View pending invoices'
                        }
                    ]
                },
                {
                    'name': 'Patient Billing',
                    'url': safe_url_for('billing_views.invoice_list'),  # FIXED: Uses correct endpoint
                    'icon': 'receipt',
                    'badge': 'Standard',
                    'badge_color': 'secondary',
                    'children': [
                        {
                            'name': 'Billing History',
                            'url': safe_url_for('billing_views.invoice_list'),  # FIXED
                            'icon': 'history',
                            'description': 'View and print bills'
                        },
                        {
                            'name': 'New Invoice',
                            'url': safe_url_for('billing_views.create_invoice_view'),  # FIXED
                            'icon': 'plus-circle',
                            'description': 'Create patient bill'
                        }
                    ]
                }
            ]
        })
        
        # =========================================================================
        # 3. PROCUREMENT & INVENTORY (FIXED URLS)
        # =========================================================================
        menu.append({
            'name': 'Procurement & Inventory',
            'url': '#',
            'icon': 'cube',
            'icon_path': '20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
            'children': [
                {
                    'name': 'Purchase Orders',
                    'url': safe_url_for('supplier_views.purchase_order_list'),  # FIXED
                    'icon': 'shopping-cart',
                    'badge': 'Standard',
                    'badge_color': 'secondary',
                    'children': [
                        {
                            'name': 'PO List',
                            'url': safe_url_for('supplier_views.purchase_order_list'),  # FIXED
                            'icon': 'list',
                            'description': 'View and print POs'
                        },
                        {
                            'name': 'Create PO',
                            'url': safe_url_for('supplier_views.add_purchase_order'),  # FIXED
                            'icon': 'plus-circle',
                            'description': 'Create purchase order'
                        }
                    ]
                },
                {
                    'name': 'Inventory Management',
                    'url': universal_url('inventory', 'list'),
                    'icon': 'archive',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [
                        {
                            'name': 'Stock Overview',
                            'url': universal_url('inventory', 'list'),
                            'icon': 'chart-bar',
                            'description': 'View stock reports'
                        }
                    ]
                }
            ]
        })
        
        # =========================================================================
        # 4. ADMIN FUNCTIONS
        # =========================================================================
        # if role in ['system_admin', 'hospital_admin']:
        menu.append({
            'name': 'Administration',
            'url': '#',
            'icon': 'cog',
            'icon_path': '10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37',
            'children': [
                {
                    'name': 'Hospital Settings',
                    'url': safe_url_for('admin_views.hospital_settings'),
                    'icon': 'hospital',
                    'badge': 'Admin',
                    'badge_color': 'warning'
                },
                {
                    'name': 'Staff Management',
                    'url': safe_url_for('admin_views.staff_management'),
                    'icon': 'user-tie',
                    'badge': 'Admin',
                    'badge_color': 'warning'
                },
                {
                    'name': 'User Management',
                    'url': safe_url_for('admin_views.user_list'),
                    'icon': 'users-cog',
                    'badge': 'Admin',
                    'badge_color': 'warning'
                },
                {
                    'name': 'Cache Dashboard',
                    'url': safe_url_for('cache_dashboard.cache_dashboard'),
                    'icon': 'chart-line',
                    'badge': 'System',
                    'badge_color': 'info',
                    'target': '_blank',
                    'description': 'Real-time cache performance monitoring'
                }
            ]
        })
        
        # Always have settings as the last item
        menu.append({
            'name': 'Settings',
            'url': safe_url_for('auth_views.settings'),
            'icon': 'settings',
            'icon_path': '10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
        })
    
    return menu

# KEPT: Existing functions for backward compatibility
def get_menu_items(current_user):
    """
    Get menu items based on user role and permissions
    UNCHANGED: Preserves existing functionality with Universal Engine integration
    """
    from flask import current_app
    from app.services.database_service import get_db_session, get_detached_copy
    
    try:
        with get_db_session() as session:
            from app.models.transaction import User
            user = session.query(User).filter_by(user_id=current_user.user_id).first()
            
            if not user:
                role = getattr(current_user, 'entity_type', 'patient')
                return generate_menu_for_role(role)
            
            detached_user = get_detached_copy(user)
            role = getattr(detached_user, 'entity_type', 'patient')
            return generate_menu_for_role(role)
    except Exception as e:
        current_app.logger.error(f"Error in get_menu_items: {str(e)}", exc_info=True)
        role = getattr(current_user, 'entity_type', 'staff')
        return generate_menu_for_role(role)