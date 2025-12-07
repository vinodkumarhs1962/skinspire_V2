# app/services/menu_service.py

class MenuService:
    """Service for generating menus based on user roles and permissions."""
    
    @staticmethod
    def get_menu_for_user(user):
        """
        Get menu items for a user based on their role and permissions.
        
        Args:
            user: The current user object
            
        Returns:
            list: List of menu items with appropriate sections
        """
        # If user is not authenticated, return minimal menu
        if not user or not user.is_authenticated:
            return [
                {
                    "name": "Authentication",
                    "items": [
                        {"name": "Login", "url": "/login", "icon": "login"}
                    ]
                }
            ]
        
        # Get user role
        role = user.role if hasattr(user, 'role') else 'user'
        
        # Generate menu based on role
        if role == 'admin':
            return MenuService._get_admin_menu()
        elif role == 'hospital_admin':
            return MenuService._get_hospital_admin_menu()
        elif role == 'doctor':
            return MenuService._get_doctor_menu()
        elif role == 'receptionist':
            return MenuService._get_receptionist_menu()
        else:
            return MenuService._get_default_menu()
    
    @staticmethod
    def _get_admin_menu():
        """Generate menu for admin users."""
        return [
            {
                "name": "Dashboard",
                "items": [
                    {"name": "Overview", "url": "/admin/dashboard", "icon": "dashboard"}
                ]
            },
            {
                "name": "User Management",
                "items": [
                    {"name": "Users", "url": "/admin/users", "icon": "users"},
                    {"name": "Roles", "url": "/admin/roles", "icon": "shield"}
                ]
            },
            {
                "name": "Hospital Management",
                "items": [
                    {"name": "Hospital Settings", "url": "/admin/hospital-settings", "icon": "settings"},
                    {"name": "Hospitals", "url": "/admin/hospitals", "icon": "building"}
                ]
            },
            {
                "name": "Patient Management",
                "items": [
                    {"name": "Patients", "url": "/admin/patients", "icon": "user-plus"},
                    {"name": "Appointments", "url": "/admin/appointments", "icon": "calendar"}
                ]
            },
            {
                "name": "System",
                "items": [
                    {"name": "Global Settings", "url": "/admin/system-settings", "icon": "cog"},
                    {"name": "Logs", "url": "/admin/logs", "icon": "clipboard"}
                ]
            }
        ]

    @staticmethod
    def _get_hospital_admin_menu():
        """Generate menu for hospital admin users."""
        return [
            {
                "name": "Dashboard",
                "items": [
                    {"name": "Overview", "url": "/hospital-admin/dashboard", "icon": "dashboard"}
                ]
            },
            {
                "name": "User Management",
                "items": [
                    {"name": "Staff", "url": "/hospital-admin/staff", "icon": "users"},
                    {"name": "Approvals", "url": "/hospital-admin/approvals", "icon": "user-check"}
                ]
            },
            {
                "name": "Hospital Configuration",
                "items": [
                    {"name": "Hospital Settings", "url": "/hospital-admin/settings", "icon": "settings"},
                    {"name": "Branches", "url": "/hospital-admin/branches", "icon": "building"}
                ]
            }
        ]
    
    @staticmethod
    def _get_doctor_menu():
        """Generate menu for doctor users."""
        return [
            {
                "name": "Dashboard",
                "items": [
                    {"name": "Overview", "url": "/doctor/dashboard", "icon": "dashboard"}
                ]
            },
            {
                "name": "Patient Care",
                "items": [
                    {"name": "My Patients", "url": "/doctor/patients", "icon": "users"},
                    {"name": "Appointments", "url": "/doctor/appointments", "icon": "calendar"},
                    {"name": "Consultations", "url": "/doctor/consultations", "icon": "clipboard"}
                ]
            },
            {
                "name": "Prescriptions",
                "items": [
                    {"name": "Create New", "url": "/doctor/prescriptions/new", "icon": "edit"},
                    {"name": "History", "url": "/doctor/prescriptions", "icon": "clipboard-list"}
                ]
            }
        ]
    
    @staticmethod
    def _get_receptionist_menu():
        """Generate menu for receptionist users."""
        return [
            {
                "name": "Front Desk",
                "items": [
                    {"name": "Dashboard", "url": "/reception/dashboard", "icon": "dashboard"},
                    {"name": "Appointments", "url": "/reception/appointments", "icon": "calendar"},
                    {"name": "Patients", "url": "/reception/patients", "icon": "users"}
                ]
            },
            {
                "name": "Billing",
                "items": [
                    {"name": "New Invoice", "url": "/reception/invoices/new", "icon": "document-add"},
                    {"name": "Invoices", "url": "/reception/invoices", "icon": "document-text"}
                ]
            }
        ]
    
    @staticmethod
    def _get_default_menu():
        """Generate default menu for standard users."""
        return [
            {
                "name": "Dashboard",
                "items": [
                    {"name": "Overview", "url": "/dashboard", "icon": "dashboard"}
                ]
            },
            {
                "name": "Account",
                "items": [
                    {"name": "Profile", "url": "/profile", "icon": "user"},
                    {"name": "Settings", "url": "/settings", "icon": "cog"},
                    {"name": "Logout", "url": "/logout", "icon": "logout"}
                ]
            }
        ]

def register_menu_context_processor(app):
    """Register menu context processor with Flask app.

    IMPORTANT: This now uses the menu_utils.py functions which contain
    the complete three-level menu structure including Appointments,
    Master Data, Procurement, Financial Management, etc.
    """

    @app.context_processor
    def inject_menu():
        from flask_login import current_user
        from app.utils.menu_utils import get_menu_items

        # Use the correct menu function from menu_utils.py
        # which includes all the proper menu items including Appointments
        if current_user and current_user.is_authenticated:
            return {
                'menu_items': get_menu_items(current_user)
            }
        else:
            # Fallback for unauthenticated users
            return {
                'menu_items': MenuService.get_menu_for_user(current_user)
            }