# app/utils/menu_utils.py
from flask import url_for
from app.services.database_service import get_detached_copy

def generate_menu_for_role(role):
    """Generate menu items based on user role"""
    # Basic menu items available to all users
    menu = [
        {
            'name': 'Dashboard',
            'url': url_for('auth_views.dashboard'),
            'icon': 'home',
            'icon_path': '3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
        }
    ]
    
    # Add role-specific menu items
    if role == 'staff':
        # Core Business Processes - Add these immediately after Dashboard
        
        # 1. Billing & Finance
        try:
            from flask import current_app
            
            # Hardcode the URLs to match the actual routes in billing_views.py
            invoice_list_url = '/invoice/list'  # Match the blueprint prefix + route
            create_invoice_url = '/invoice/create'  # Match the blueprint prefix + route
            
            menu.append({
                'name': 'Billing & Finance',
                'url': '#',
                'icon': 'document-text',
                'icon_path': '9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
                'children': [
                    {
                        'name': 'Invoices',
                        'url': invoice_list_url,
                        'icon': 'document-text'
                    },
                    {
                        'name': 'Create Invoice',
                        'url': create_invoice_url,
                        'icon': 'plus'
                    },
                    {
                        'name': 'Advance Payments',
                        'url': '/invoice/advance/list',  # New URL for advance payments list
                        'icon': 'cash'
                    },
                    {
                        'name': 'New Advance Payment',
                        'url': '/invoice/advance/create',  # New URL for creating advance payment
                        'icon': 'plus-circle'
                    },
                    {
                        'name': 'Payment History',
                        'url': '#',  # Replace with actual URL when implemented
                        'icon': 'credit-card'
                    },
                    {
                        'name': 'Pending Payments',
                        'url': '#',  # Replace with actual URL when implemented
                        'icon': 'exclamation'
                    }
                ]
            })
        except Exception as e:
            # Log the exception instead of silently passing
            from flask import current_app
            current_app.logger.error(f"Error adding Billing menu: {str(e)}", exc_info=True)
        
        # 2. Inventory Management
        menu.append({
            'name': 'Inventory',
            'url': '#',
            'icon': 'cube',
            'icon_path': '20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
            'children': [
                {
                    'name': 'Stock List',
                    'url': url_for('inventory_views.inventory_list', _external=False),
                    'icon': 'archive'
                },
                {
                    'name': 'Stock Movement',
                    'url': url_for('inventory_views.inventory_movement', _external=False),
                    'icon': 'arrow-right'
                },
                {
                    'name': 'Stock Adjustment',
                    'url': url_for('inventory_views.stock_adjustment', _external=False),
                    'icon': 'pencil'
                },
                {
                    'name': 'Low Stock',
                    'url': url_for('inventory_views.low_stock', _external=False),
                    'icon': 'exclamation'
                },
                {
                    'name': 'Expiring Stock',
                    'url': url_for('inventory_views.expiring_stock', _external=False),
                    'icon': 'clock'
                },
                {
                    'name': 'Batch Management',
                    'url': url_for('inventory_views.batch_management', _external=False),
                    'icon': 'tag'
                }
            ]
        })
        
        # 3. Supplier Management
        menu.append({
            'name': 'Suppliers',
            'url': '/supplier/',  # Direct URL instead of url_for
            'icon': 'truck',
            'icon_path': '8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
            'children': [
                {
                    'name': 'Supplier List',
                    'url': '/supplier/',
                    'icon': 'view-list'
                },
                {
                    'name': 'New Supplier',
                    'url': '/supplier/add',
                    'icon': 'plus'
                },
                {
                    'name': 'Supplier Invoices',
                    'url': '/supplier/invoices',
                    'icon': 'document-text'
                }
            ]
        })
        # try:
        #     menu.append({
        #         'name': 'Suppliers',
        #         'url': url_for('supplier_views.supplier_list', _external=False),
        #         'icon': 'truck',
        #         'icon_path': '8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
        #         'children': [
        #             {
        #                 'name': 'Supplier List',
        #                 'url': url_for('supplier_views.supplier_list', _external=False),
        #                 'icon': 'view-list'
        #             },
        #             {
        #                 'name': 'New Supplier',
        #                 'url': url_for('supplier_views.add_supplier', _external=False),
        #                 'icon': 'plus'
        #             },
        #             {
        #                 'name': 'Purchase Orders',
        #                 'url': url_for('supplier_views.purchase_order_list', _external=False),
        #                 'icon': 'clipboard-list'
        #             },
        #             {
        #                 'name': 'Supplier Invoices',
        #                 'url': url_for('supplier_views.supplier_invoice_list', _external=False),
        #                 'icon': 'document-text'
        #             },
        #             {
        #                 'name': 'Payment History',
        #                 'url': '#',  # Placeholder - requires supplier_id
        #                 'icon': 'credit-card'
        #             },
        #             {
        #                 'name': 'Pending Invoices',
        #                 'url': url_for('supplier_views.pending_invoices', _external=False),
        #                 'icon': 'exclamation'
        #             }
        #         ]
        #     })
        # except Exception:
        #     # Skip supplier menu if routes are not available
        #     pass
        
        # 4. Financial Reports
        menu.append({
            'name': 'Financial Reports',
            'url': '#',
            'icon': 'cash',
            'icon_path': '17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z',
            'children': [
                {
                    'name': 'Balance Sheet',
                    'url': url_for('gl_views.generate_report', report_type='balance_sheet', _external=False),
                    'icon': 'document'
                },
                {
                    'name': 'Profit & Loss',
                    'url': url_for('gl_views.generate_report', report_type='profit_loss', _external=False),
                    'icon': 'chart-bar'
                },
                {
                    'name': 'Trial Balance',
                    'url': url_for('gl_views.generate_report', report_type='trial_balance', _external=False),
                    'icon': 'calculator'
                },
                {
                    'name': 'GST Reports',
                    'url': url_for('gl_views.gst_reports', _external=False),
                    'icon': 'document-report'
                },
                {
                    'name': 'Account Reconciliation',
                    'url': url_for('gl_views.account_reconciliation', _external=False),
                    'icon': 'check-circle'
                }
            ]
        })
        
        # 5. Patient Management
        menu.append({
            'name': 'Patients',
            'url': '#',
            'icon': 'users',
            'icon_path': '16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
            'children': [
                {
                    'name': 'Patient List',
                    'url': '#', 
                    'icon': 'list'
                },
                {
                    'name': 'New Patient', 
                    'url': '#', 
                    'icon': 'user-plus'
                }
            ]
        })
        
        # 6. Appointments
        menu.append({
            'name': 'Appointments',
            'url': '#',
            'icon': 'calendar',
            'icon_path': '8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
            'children': [
                {
                    'name': 'View Schedule', 
                    'url': '#', 
                    'icon': 'clock'
                },
                {
                    'name': 'New Appointment', 
                    'url': '#', 
                    'icon': 'plus'
                }
            ]
        })
        
        # 7. Administration
        menu.append({
            'name': 'Administration',
            'url': '#',
            'icon': 'cog',
            'icon_path': '12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4',
            'children': [
                {
                    'name': 'Hospital Settings',
                    'url': url_for('admin_views.hospital_settings'),
                    'icon': 'cog'
                },
                {
                    'name': 'System Admin Dashboard',
                    'url': url_for('admin_views.system_admin_dashboard'),
                    'icon': 'server'
                },
                {
                    'name': 'Hospital Admin Dashboard',
                    'url': url_for('admin_views.hospital_admin_dashboard'),
                    'icon': 'building'
                },
                {
                    'name': 'User Management',
                    'url': '#',
                    'icon': 'users'
                },
                {
                    'name': 'Role Management',
                    'url': '#',
                    'icon': 'shield'
                }
            ]
        })
        
        # Always have settings as the last item
        menu.append({
            'name': 'Settings',
            'url': url_for('auth_views.settings'),
            'icon': 'settings',
            'icon_path': '10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
        })
    elif role == 'patient':
        # Patient-specific menu items
        menu.append({
            'name': 'My Appointments',
            'url': '#',
            'icon': 'calendar',
            'icon_path': '8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'
        })
        
        menu.append({
            'name': 'My Health Records',
            'url': '#',
            'icon': 'clipboard',
            'icon_path': '9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
        })
        
        menu.append({
            'name': 'My Prescriptions',
            'url': '#',
            'icon': 'pill',
            'icon_path': '19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z'
        })
        
        # Patient Billing
        try:
            menu.append({
                'name': 'My Billing',
                'url': '#',
                'icon': 'cash',
                'icon_path': '17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z',
                'children': [
                    {
                        'name': 'My Invoices',
                        'url': '#',  # Replace with actual URL when implemented
                        'icon': 'document-text'
                    },
                    {
                        'name': 'Payment History',
                        'url': '#',  # Replace with actual URL when implemented
                        'icon': 'credit-card'
                    }
                ]
            })
        except Exception:
            pass
        
        # Always have settings as the last item
        menu.append({
            'name': 'Settings',
            'url': url_for('auth_views.settings'),
            'icon': 'settings',
            'icon_path': '10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
        })
    
    return menu

# Add a new function while maintaining backward compatibility with your existing code
def get_menu_items(current_user):
    """
    Get menu items based on user role and permissions
    
    Args:
        current_user: Current user object
        
    Returns:
        List of menu items with children
    """
    from flask import current_app
    from app.services.database_service import get_db_session, get_detached_copy
    
    try:
        # Get a fresh copy of the user with session
        with get_db_session() as session:
            # Find user in the database
            from app.models.transaction import User
            user = session.query(User).filter_by(user_id=current_user.user_id).first()
            
            if not user:
                # Fall back to entity_type if user can't be found
                role = getattr(current_user, 'entity_type', 'patient')
                return generate_menu_for_role(role)
            
            # Create a detached copy with loaded relationships
            detached_user = get_detached_copy(user)
            
            # Now you can access user.roles outside the session
            # Here you could use permission logic based on roles
            
            # For simplicity, still using entity_type to determine menu
            role = getattr(detached_user, 'entity_type', 'patient')
            return generate_menu_for_role(role)
    except Exception as e:
        current_app.logger.error(f"Error in get_menu_items: {str(e)}", exc_info=True)
        # Fall back to staff role for safety
        role = getattr(current_user, 'entity_type', 'staff')
        return generate_menu_for_role(role)