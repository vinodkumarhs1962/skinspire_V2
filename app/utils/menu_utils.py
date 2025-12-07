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
        'patient_invoices',   # Added - Phase 4
        'patient_payments',   # Added - Patient payment receipts
        'package_payment_plans',  # Added - Package payment plans
        'patients',
        'medicines',
        'packages',  # Added - Treatment packages
        'package_bom_items',  # Added - Package BOM Items
        'package_session_plans',  # Added - Package Session Plans
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
        # 0. APPOINTMENTS (PATIENT LIFECYCLE PHASE 1)
        # =========================================================================
        menu.append({
            'name': 'Appointments',
            'url': '#',
            'icon': 'calendar-alt',
            'icon_path': 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
            'children': [
                {
                    'name': 'Dashboard',
                    'url': safe_url_for('appointment_views.dashboard'),
                    'icon': 'tachometer-alt',
                    'description': 'Today\'s appointments overview'
                },
                {
                    'name': 'Queue Management',
                    'url': safe_url_for('appointment_views.queue_view'),
                    'icon': 'users',
                    'description': 'Real-time patient queue'
                },
                {
                    'name': 'Booking',
                    'url': '#',
                    'icon': 'calendar-plus',
                    'children': [
                        {
                            'name': 'Book Appointment',
                            'url': safe_url_for('appointment_views.book_appointment'),
                            'icon': 'plus-circle',
                            'description': 'Schedule new appointment'
                        },
                        {
                            'name': 'Walk-In',
                            'url': safe_url_for('appointment_views.walk_in_booking'),
                            'icon': 'walking',
                            'description': 'Quick walk-in registration'
                        },
                        {
                            'name': 'Calendar View',
                            'url': safe_url_for('appointment_views.calendar_view'),
                            'icon': 'calendar',
                            'description': 'View appointments calendar'
                        }
                    ]
                },
                {
                    'name': 'Schedules',
                    'url': '#',
                    'icon': 'clock',
                    'children': [
                        {
                            'name': 'Doctor Schedules',
                            'url': safe_url_for('appointment_views.schedule_list'),
                            'icon': 'user-md',
                            'description': 'Manage doctor schedules'
                        },
                        {
                            'name': 'Add Schedule',
                            'url': safe_url_for('appointment_views.create_schedule'),
                            'icon': 'plus',
                            'description': 'Create new schedule'
                        },
                        {
                            'name': 'Exceptions',
                            'url': safe_url_for('appointment_views.exception_list'),
                            'icon': 'calendar-times',
                            'description': 'Leaves and holidays'
                        }
                    ]
                },
                {
                    'name': 'Reports',
                    'url': safe_url_for('appointment_views.reports'),
                    'icon': 'chart-bar',
                    'description': 'Appointment analytics'
                }
            ]
        })

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
                    'name': 'Packages',
                    'url': '#',  # No URL for second level
                    'icon': 'box',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'All Packages',
                            'url': universal_url('packages', 'list'),
                            'icon': 'list',
                            'description': 'View all treatment packages'
                        },
                        {
                            'name': 'Package BOM Items',
                            'url': universal_url('package_bom_items', 'list'),
                            'icon': 'boxes',
                            'description': 'Bill of Materials for packages'
                        },
                        {
                            'name': 'Package Session Plans',
                            'url': universal_url('package_session_plans', 'list'),
                            'icon': 'calendar-alt',
                            'description': 'Session delivery plans for packages'
                        }
                    ]
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
                    'name': 'Patient Invoices',
                    'url': '#',  # No URL for second level
                    'icon': 'file-invoice-dollar',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All Invoices',
                            'url': universal_url('patient_invoices', 'list'),
                            'icon': 'list',
                            'description': 'List all patient invoices'
                        },
                        {
                            'name': 'Create Invoice',
                            'url': safe_url_for('billing_views.create_invoice_view'),  # Still standard
                            'icon': 'plus-circle',
                            'description': 'Create new invoice',
                            'badge': 'Standard',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'All Patient Invoices',
                            'url': safe_url_for('universal_views.universal_list_view', entity_type='patient_invoices'),
                            'icon': 'file-invoice-dollar',
                            'description': 'View all patient invoices',
                            'badge': 'Universal',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'Consolidated Invoices',
                            'url': safe_url_for('universal_views.universal_list_view', entity_type='consolidated_patient_invoices'),
                            'icon': 'folder-open',
                            'description': 'View consolidated invoice groups (multi-invoice transactions)',
                            'badge': 'Phase 3',
                            'badge_color': 'info'
                        },
                        {
                            'name': 'Unpaid Invoices',
                            'url': universal_url('patient_invoices', 'list') + '?payment_status=unpaid',
                            'icon': 'clock',
                            'description': 'Unpaid invoices'
                        },
                        {
                            'name': 'Partially Paid',
                            'url': universal_url('patient_invoices', 'list') + '?payment_status=partial',
                            'icon': 'hourglass-half',
                            'description': 'Partially paid invoices'
                        }
                    ]
                },
                {
                    'name': 'Patient Payments',
                    'url': '#',  # No URL for second level
                    'icon': 'money-bill-wave',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All Payments',
                            'url': universal_url('patient_payments', 'list'),
                            'icon': 'list',
                            'description': 'List all payment receipts'
                        },
                        {
                            'name': 'Record Payment',
                            'url': safe_url_for('billing_views.payment_patient_selection'),
                            'icon': 'plus-circle',
                            'description': 'Record patient payment against invoices',
                            'badge': 'Standard',
                            'badge_color': 'secondary'
                        },
                        {
                            'name': 'Pending Approval',
                            'url': universal_url('patient_payments', 'list') + '?workflow_status=pending_approval',
                            'icon': 'user-check',
                            'description': 'Payments awaiting approval'
                        },
                        {
                            'name': 'Today\'s Payments',
                            'url': universal_url('patient_payments', 'list') + '?date=today',
                            'icon': 'calendar-day',
                            'description': 'Payments received today'
                        },
                        {
                            'name': 'Record Advance Payment',
                            'url': safe_url_for('billing_views.create_advance_payment_view'),
                            'icon': 'piggy-bank',
                            'description': 'Record patient advance payment'
                        },
                        {
                            'name': 'View Patient Advances',
                            'url': safe_url_for('billing_views.view_all_patient_advances'),
                            'icon': 'list-alt',
                            'description': 'View all patient advance balances'
                        }
                    ]
                },
                {
                    'name': 'Package Session & Payment Plans',
                    'url': '#',  # No URL for second level
                    'icon': 'calendar-alt',
                    'badge': 'Universal',
                    'badge_color': 'primary',
                    'children': [  # Third level with actual URLs
                        {
                            'name': 'View All Plans',
                            'url': universal_url('package_payment_plans', 'list'),
                            'icon': 'list',
                            'description': 'List all package payment plans'
                        },
                        {
                            'name': 'Create Plan',
                            'url': '/package/payment-plan/create',  # Custom route with cascading workflow
                            'icon': 'plus-circle',
                            'description': 'Create new payment plan'
                        },
                        {
                            'name': 'Active Plans',
                            'url': universal_url('package_payment_plans', 'list') + '?status=active',
                            'icon': 'check-circle',
                            'description': 'Active payment plans'
                        },
                        {
                            'name': 'Completed Plans',
                            'url': universal_url('package_payment_plans', 'list') + '?status=completed',
                            'icon': 'check-double',
                            'description': 'Fully paid plans'
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
        # 3.5 PROMOTIONS & DISCOUNTS
        # =========================================================================
        menu.append({
            'name': 'Promotions & Discounts',
            'url': '#',
            'icon': 'tags',
            'icon_path': '7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z',
            'children': [
                {
                    'name': 'Promotions Dashboard',
                    'url': safe_url_for('promotion_views.dashboard'),
                    'icon': 'tachometer-alt',
                    'description': 'Overview of all promotions'
                },
                {
                    'name': 'Campaign Promotions',
                    'url': '#',
                    'icon': 'bullhorn',
                    'children': [
                        {
                            'name': 'All Campaigns',
                            'url': safe_url_for('promotion_views.campaign_list'),
                            'icon': 'list',
                            'description': 'View all promotion campaigns'
                        },
                        {
                            'name': 'Create Campaign',
                            'url': safe_url_for('promotion_views.campaign_create'),
                            'icon': 'plus-circle',
                            'description': 'Create new promotion campaign'
                        },
                        {
                            'name': 'Active Campaigns',
                            'url': safe_url_for('promotion_views.campaign_list') + '?status=active',
                            'icon': 'check-circle',
                            'description': 'Currently active campaigns'
                        }
                    ]
                },
                {
                    'name': 'Bulk Discount',
                    'url': safe_url_for('promotion_views.bulk_config'),
                    'icon': 'layer-group',
                    'description': 'Configure bulk discount policy'
                },
                {
                    'name': 'Loyalty Discount',
                    'url': safe_url_for('promotion_views.loyalty_config'),
                    'icon': 'heart',
                    'description': 'Configure loyalty discount settings'
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
                        'name': 'Config to Master Sync',
                        'url': safe_url_for('admin.config_sync_page'),
                        'icon': 'sync-alt',
                        'badge': 'Admin',
                        'badge_color': 'warning',
                        'description': 'Sync pricing/GST configs to master tables'
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
    Get menu items based on user role and permissions.

    IMPORTANT: This function is called from a context processor for EVERY request.
    It must NOT open a database session to avoid nested session errors.
    Instead, use the role/entity_type directly from the current_user object
    which is already loaded by Flask-Login.
    """
    try:
        # Get role directly from current_user without database query
        # Flask-Login already provides the user object with entity_type
        role = getattr(current_user, 'entity_type', None)

        # If no entity_type, try to infer from other attributes
        if not role:
            if hasattr(current_user, 'is_admin') and current_user.is_admin:
                role = 'system_admin'
            elif hasattr(current_user, 'is_hospital_admin') and current_user.is_hospital_admin:
                role = 'hospital_admin'
            else:
                role = 'staff'  # Default to staff for authenticated users

        return generate_menu_for_role(role)
    except Exception as e:
        # Fallback to staff menu on any error
        import logging
        logging.getLogger(__name__).warning(f"Error in get_menu_items: {str(e)}")
        return generate_menu_for_role('staff')