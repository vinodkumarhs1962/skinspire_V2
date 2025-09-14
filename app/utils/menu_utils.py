# app/utils/menu_utils.py - CORRECTED VERSION
# Three-level menu structure with Universal Engine URLs

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
    
    # UPDATED: Entities configured in Universal Engine
    CONFIGURED_ENTITIES = [
        'suppliers',
        'supplier_payments',
        'supplier_invoices',  # Added
        'purchase_orders',    # Added
        'patients',
        'medicines',
        'users',
        'branches',
        'inventory'
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
    """Generate menu items based on user role - CORRECTED THREE-LEVEL VERSION"""
    
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
        # 2. PROCUREMENT & INVENTORY (THREE-LEVEL STRUCTURE)
        # =========================================================================
        menu.append({
            'name': 'Procurement & Inventory',
            'url': '#',
            'icon': 'cube',
            'icon_path': '20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
            'children': [
                {
                    'name': 'Purchase Orders',
                    'url': '#',  # No URL for second level
                    'icon': 'shopping-cart',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All POs',
                            'url': universal_url('purchase_orders', 'list'),
                            'icon': 'list',
                            'description': 'List all purchase orders'
                        },
                        {
                            'name': 'Create PO',
                            'url': safe_url_for('supplier_views.add_purchase_order'),  # Still standard
                            'icon': 'plus-circle',
                            'description': 'Create new purchase order',
                            'badge': 'Standard',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'Pending Approval',
                            'url': universal_url('purchase_orders', 'list') + '?status=pending',
                            'icon': 'clock',
                            'description': 'POs awaiting approval'
                        },
                        {
                            'name': 'Recent POs',
                            'url': universal_url('purchase_orders', 'list') + '?days=7',
                            'icon': 'calendar',
                            'description': 'Last 7 days'
                        }
                    ]
                },
                {
                    'name': 'Supplier Invoices',
                    'url': '#',  # No URL for second level
                    'icon': 'file-invoice',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All Invoices',
                            'url': universal_url('supplier_invoices', 'list'),
                            'icon': 'list',
                            'description': 'List all supplier invoices'
                        },
                        {
                            'name': 'Create Invoice',
                            'url': safe_url_for('supplier_views.add_supplier_invoice'),  # Still standard
                            'icon': 'plus-circle',
                            'description': 'Create new invoice',
                            'badge': 'Standard',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'Pending Invoices',
                            'url': universal_url('supplier_invoices', 'list') + '?payment_status=pending',
                            'icon': 'hourglass-half',
                            'description': 'Unpaid invoices'
                        },
                        {
                            'name': 'Overdue Invoices',
                            'url': universal_url('supplier_invoices', 'list') + '?payment_status=overdue',
                            'icon': 'exclamation-triangle',
                            'description': 'Past due date'
                        }
                    ]
                },
                {
                    'name': 'Inventory',
                    'url': '#',  # No URL for second level
                    'icon': 'archive',
                    'badge': 'Coming Soon',
                    'badge_color': 'warning',
                    'children': [
                        {
                            'name': 'Stock Overview',
                            'url': '#',
                            'icon': 'chart-bar',
                            'description': 'View stock levels'
                        },
                        {
                            'name': 'Stock Movement',
                            'url': '#',
                            'icon': 'exchange-alt',
                            'description': 'Track inventory flow'
                        }
                    ]
                }
            ]
        })
        
        # =========================================================================
        # 3. FINANCIAL MANAGEMENT (THREE-LEVEL STRUCTURE)
        # =========================================================================
        menu.append({
            'name': 'Financial Management',
            'url': '#',
            'icon': 'money-check-alt',
            'icon_path': '12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z',
            'children': [
                {
                    'name': 'Supplier Payments',
                    'url': '#',  # No URL for second level
                    'icon': 'hand-holding-usd',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All Payments',
                            'url': universal_url('supplier_payments', 'list'),
                            'icon': 'list',
                            'description': 'List all payments'
                        },
                        {
                            'name': 'Create Payment',
                            'url': safe_url_for('supplier_views.create_payment'),  # Still standard
                            'icon': 'plus-circle',
                            'description': 'Record new payment',
                            'badge': 'Standard',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'Pending Approval',
                            'url': universal_url('supplier_payments', 'list') + '?payment_status=pending_approval',
                            'icon': 'user-check',
                            'description': 'Awaiting approval'
                        },
                        {
                            'name': 'Today\'s Payments',
                            'url': universal_url('supplier_payments', 'list') + '?date=today',
                            'icon': 'calendar-day',
                            'description': 'Payments made today'
                        }
                    ]
                },
                {
                    'name': 'Patient Billing',
                    'url': '#',  # No URL for second level
                    'icon': 'receipt',
                    'badge': 'Standard',
                    'badge_color': 'secondary',
                    'children': [
                        {
                            'name': 'Billing List',
                            'url': safe_url_for('billing_views.invoice_list'),
                            'icon': 'list',
                            'description': 'View all bills'
                        },
                        {
                            'name': 'Create Bill',
                            'url': safe_url_for('billing_views.create_invoice_view'),
                            'icon': 'plus-circle',
                            'description': 'New patient bill'
                        },
                        {
                            'name': 'Pending Bills',
                            'url': safe_url_for('billing_views.pending_bills'),
                            'icon': 'clock',
                            'description': 'Unpaid bills'
                        }
                    ]
                },
                {
                    'name': 'Financial Reports',
                    'url': '#',  # No URL for second level
                    'icon': 'chart-line',
                    'children': [
                        {
                            'name': 'Payment Summary',
                            'url': universal_url('supplier_payments', 'list') + '?view=summary',
                            'icon': 'chart-pie',
                            'description': 'Payment analytics'
                        },
                        {
                            'name': 'Outstanding Report',
                            'url': universal_url('supplier_invoices', 'list') + '?view=outstanding',
                            'icon': 'file-invoice-dollar',
                            'description': 'Pending dues'
                        },
                        {
                            'name': 'Supplier Statement',
                            'url': universal_url('suppliers', 'list') + '?view=statement',
                            'icon': 'file-alt',
                            'description': 'Supplier-wise summary'
                        }
                    ]
                }
            ]
        })
        
        # =========================================================================
        # 4. CLINICAL OPERATIONS
        # =========================================================================
        menu.append({
            'name': 'Clinical Operations',
            'url': '#',
            'icon': 'stethoscope',
            'icon_path': 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z',
            'children': [
                {
                    'name': 'Patient Management',
                    'url': '#',
                    'icon': 'user-injured',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [
                        {
                            'name': 'All Patients',
                            'url': universal_url('patients', 'list'),
                            'icon': 'list',
                            'description': 'View all patients'
                        },
                        {
                            'name': 'Register Patient',
                            'url': universal_url('patients', 'create'),
                            'icon': 'user-plus',
                            'description': 'New patient registration'
                        },
                        {
                            'name': 'Today\'s Patients',
                            'url': universal_url('patients', 'list') + '?date=today',
                            'icon': 'calendar-check',
                            'description': 'Today\'s appointments'
                        }
                    ]
                },
                {
                    'name': 'Medicine Store',
                    'url': '#',
                    'icon': 'pills',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [
                        {
                            'name': 'Medicine List',
                            'url': universal_url('medicines', 'list'),
                            'icon': 'list',
                            'description': 'All medicines'
                        },
                        {
                            'name': 'Add Medicine',
                            'url': universal_url('medicines', 'create'),
                            'icon': 'plus',
                            'description': 'Register new medicine'
                        },
                        {
                            'name': 'Low Stock',
                            'url': universal_url('medicines', 'list') + '?stock=low',
                            'icon': 'exclamation-circle',
                            'description': 'Below reorder level'
                        }
                    ]
                }
            ]
        })
        
        # =========================================================================
        # 5. REPORTS & ANALYTICS (Optional - for admin roles)
        # =========================================================================
        if role in ['system_admin', 'hospital_admin']:
            menu.append({
                'name': 'Reports & Analytics',
                'url': '#',
                'icon': 'chart-bar',
                'icon_path': 'M3 13h2v7H3zm4-8h2v12H7zm4 4h2v8h-2zm4-2h2v10h-2z',
                'children': [
                    {
                        'name': 'Dashboard Reports',
                        'url': safe_url_for('reports.dashboard'),
                        'icon': 'tachometer-alt',
                        'badge': 'Pro',
                        'badge_color': 'success'
                    },
                    {
                        'name': 'Custom Reports',
                        'url': safe_url_for('reports.custom'),
                        'icon': 'file-excel',
                        'badge': 'Pro',
                        'badge_color': 'success'
                    }
                ]
            })
        
        # =========================================================================
        # 6. SYSTEM SETTINGS (Admin only)
        # =========================================================================
        if role == 'system_admin':
            menu.append({
                'name': 'System Settings',
                'url': '#',
                'icon': 'cogs',
                'icon_path': 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z',
                'children': [
                    {
                        'name': 'User Management',
                        'url': universal_url('users', 'list'),
                        'icon': 'users-cog',
                        'badge': 'Universal',
                        'badge_color': 'primary'
                    },
                    {
                        'name': 'Branch Setup',
                        'url': universal_url('branches', 'list'),
                        'icon': 'sitemap',
                        'badge': 'Universal',
                        'badge_color': 'primary'
                    },
                    {
                        'name': 'System Config',
                        'url': safe_url_for('settings.system'),
                        'icon': 'sliders-h',
                        'badge': 'Standard',
                        'badge_color': 'secondary'
                    }
                ]
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