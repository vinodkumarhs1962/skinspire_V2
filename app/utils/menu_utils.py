# app/utils/menu_utils.py
from flask import url_for

def generate_menu_for_role(role):
    """Generate menu items based on user role"""
    # Basic menu items available to all users
    menu = [
        {
            'name': 'Dashboard',
            'url': url_for('auth_views.dashboard'),
            'icon': 'home',
            'icon_path': '3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
        },
        {
            'name': 'Settings',
            'url': url_for('auth_views.settings'),
            'icon': 'settings',
            'icon_path': '10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
        }
    ]
    
    # Add role-specific menu items
    if role == 'staff':
        # Insert menu items before settings (which is the last item)
        menu.insert(1, {
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
        
        menu.insert(2, {
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
        
        # Admin-only items for staff with admin role
        # In a real app, you'd check specific permissions
        menu.insert(3, {
            'name': 'Administration',
            'url': '#',
            'icon': 'cog',
            'icon_path': '12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4',
            'children': [
                {
                    'name': 'User Management',
                    'url': '#',
                    'icon': 'users'
                },
                {
                    'name': 'Role Management',
                    'url': '#',
                    'icon': 'shield'
                },
                {
                    'name': 'System Settings',
                    'url': '#',
                    'icon': 'cog'
                }
            ]
        })
    elif role == 'patient':
        menu.insert(1, {
            'name': 'My Appointments',
            'url': '#',
            'icon': 'calendar',
            'icon_path': '8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z'
        })
        
        menu.insert(2, {
            'name': 'My Health Records',
            'url': '#',
            'icon': 'clipboard',
            'icon_path': '9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2'
        })
        
        menu.insert(3, {
            'name': 'My Prescriptions',
            'url': '#',
            'icon': 'pill',
            'icon_path': '19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z'
        })
    
    return menu