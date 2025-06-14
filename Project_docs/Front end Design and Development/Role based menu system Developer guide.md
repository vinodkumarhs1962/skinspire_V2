Development Guide: Role-Based Menu System Implementation
This development guide outlines how to implement a comprehensive role-based menu system that integrates with your existing authorization structure while adding menu-specific functionality. The guide includes an ER diagram, implementation details, and explains how data access control works with the menu system.
1. Entity-Relationship Diagram
                                   ┌─────────────────┐
                                   │   Hospital      │
                                   │  (Tenant)       │
                                   └────────┬────────┘
                                            │
                ┌───────────────────────────┼───────────────────────────┐
                │                           │                           │
        ┌───────┴────────┐         ┌───────┴────────┐         ┌────────┴────────┐
        │     User       │         │  RoleMaster    │         │  ModuleMaster   │
        └───────┬────────┘         └───────┬────────┘         └────────┬────────┘
                │                          │                           │
                │                          │                           │
        ┌───────┴────────┐         ┌───────┴────────┐         ┌────────┴────────┐
        │ UserRoleMapping│◄────────┤RoleModuleAccess│         │  MenuCategory   │
        └────────────────┘         └───────┬────────┘         └────────┬────────┘
                                           │                           │
                                           │                           │
                                   ┌───────┴────────┐         ┌────────┴────────┐
                                   │  DataSlicer    │         │    MenuItem     │◄─┐
                                   │  (new)         │         └────────┬────────┘  │
                                   └────────────────┘                  │           │
                                                                       │           │
                                                              ┌────────┴────────┐  │
                                                              │  RoleMenuAccess │  │
                                                              └────────┬────────┘  │
                                                                       │           │
                                                              ┌────────┴────────┐  │
                                                              │ Parent-Child    ├──┘
                                                              │ Relationship    │
                                                              └─────────────────┘
2. Existing Table Structure (Used by Menu System)
These tables already exist in your system:
Hospital
hospital_id: UUID (PK)
name: String
...other fields
User
user_id: String (PK) 
hospital_id: UUID (FK)
entity_type: String
entity_id: UUID
...other fields
RoleMaster
role_id: UUID (PK)
hospital_id: UUID (FK)
role_name: String
role_description: String
is_active: Boolean
UserRoleMapping
mapping_id: UUID (PK)
hospital_id: UUID (FK)
user_id: String (FK)
role_id: UUID (FK)
is_active: Boolean
ModuleMaster
module_id: UUID (PK)
module_name: String
module_description: String
is_active: Boolean
RoleModuleAccess
access_id: UUID (PK)
hospital_id: UUID (FK) 
role_id: UUID (FK)
module_id: UUID (FK)
can_view: Boolean
can_add: Boolean
can_edit: Boolean
can_delete: Boolean
can_export: Boolean
3. New Tables for Menu System
These are the new tables we'll create specifically for the menu system:
MenuCategory
pythonclass MenuCategory(Base, TimestampMixin, TenantMixin):
    """Menu categories for grouping menu items"""
    __tablename__ = 'menu_categories'
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(255))
    order_index = Column(Integer, default=0)  # For sorting
    icon = Column(String(50))  # Optional category icon
    is_active = Column(Boolean, default=True)
    
    # Relationships
    hospital = relationship("Hospital")
    menu_items = relationship("MenuItem", back_populates="category")
MenuItem
pythonclass MenuItem(Base, TimestampMixin, TenantMixin):
    """Menu items configuration"""
    __tablename__ = 'menu_items'
    
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey('menu_categories.category_id'), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.item_id'), nullable=True)  # For nested menus
    name = Column(String(100), nullable=False)
    url = Column(String(255))  # Can be direct URL or view_name-based
    icon = Column(String(50))
    icon_path = Column(String(255))  # For SVG paths
    order_index = Column(Integer, default=0)  # For sorting
    is_active = Column(Boolean, default=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey('module_master.module_id'))  # Link to permission system
    
    # For dynamic URL generation
    view_name = Column(String(100))  # 'blueprint.function_name' format
    
    # Relationships
    hospital = relationship("Hospital")
    category = relationship("MenuCategory", back_populates="menu_items")
    parent = relationship("MenuItem", remote_side=[item_id], backref="children")
    module = relationship("ModuleMaster")
RoleMenuAccess
pythonclass RoleMenuAccess(Base, TimestampMixin, TenantMixin):
    """Role-based menu access"""
    __tablename__ = 'role_menu_access'
    
    access_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('role_master.role_id'), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.item_id'), nullable=False)
    can_access = Column(Boolean, default=True)
    
    # Relationships
    hospital = relationship("Hospital")
    role = relationship("RoleMaster")
    menu_item = relationship("MenuItem")
DataSlicer (Optional - For Advanced Data Access Control)
pythonclass DataSlicer(Base, TimestampMixin, TenantMixin):
    """Controls which data slices users can access"""
    __tablename__ = 'data_slicer'
    
    slicer_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('role_master.role_id'), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey('module_master.module_id'), nullable=False)
    
    # Data access rules
    access_type = Column(String(50), nullable=False)  # 'all', 'own', 'department', 'assigned'
    filter_condition = Column(JSONB)  # JSON rule for filtering data
    
    # Relationships
    hospital = relationship("Hospital")
    role = relationship("RoleMaster")
    module = relationship("ModuleMaster")
4. Creating Database Migrations
Create an Alembic migration to add the new tables:
bashflask db migrate -m "Add menu system tables"
flask db upgrade
5. Menu Service Implementation
Create a menu_service.py file:
python# app/services/menu_service.py

from flask import current_app, url_for
import redis
import json
from app.services.database_service import get_db_session, get_detached_copy
from app.models.transaction import User, UserRoleMapping
from app.models.menu import MenuItem, RoleMenuAccess, MenuCategory
from app.utils.redis_client import get_redis_client

class MenuService:
    """Service for generating menus based on user roles and permissions"""
    
    CACHE_TIMEOUT = 3600  # 1 hour cache
    
    @staticmethod
    def get_menu_for_user(user):
        """Get menu items for a user based on roles and permissions"""
        if not user or not user.is_authenticated:
            return []
            
        # Check cache first if available
        try:
            redis_client = get_redis_client()
            cache_key = f"menu:user:{user.user_id}:hospital:{user.hospital_id}"
            cached_menu = redis_client.get(cache_key)
            
            if cached_menu:
                return json.loads(cached_menu)
        except Exception as e:
            current_app.logger.warning(f"Redis cache error: {str(e)}")
            # Continue without cache on error
        
        # If not in cache, generate menu
        try:
            with get_db_session() as session:
                # Get user's roles
                role_mappings = session.query(UserRoleMapping).filter_by(
                    user_id=user.user_id,
                    hospital_id=user.hospital_id,
                    is_active=True
                ).all()
                
                if not role_mappings:
                    return []
                    
                role_ids = [str(rm.role_id) for rm in role_mappings]
                
                # Get categorized menu items
                categories = session.query(MenuCategory).filter_by(
                    hospital_id=user.hospital_id,
                    is_active=True
                ).order_by(MenuCategory.order_index).all()
                
                menu = []
                
                for category in categories:
                    # Get root menu items for this category that the user can access
                    root_items_query = """
                        SELECT DISTINCT mi.*
                        FROM menu_items mi
                        JOIN role_menu_access rma ON mi.item_id = rma.item_id
                        WHERE rma.role_id IN :role_ids
                        AND rma.can_access = true
                        AND mi.is_active = true
                        AND mi.parent_id IS NULL
                        AND mi.category_id = :category_id
                        AND mi.hospital_id = :hospital_id
                        ORDER BY mi.order_index
                    """
                    
                    root_items = session.execute(root_items_query, {
                        'role_ids': tuple(role_ids),
                        'category_id': str(category.category_id),
                        'hospital_id': str(user.hospital_id)
                    }).fetchall()
                    
                    # Skip empty categories
                    if not root_items:
                        continue
                    
                    category_menu = {
                        'name': category.name,
                        'icon': category.icon,
                        'items': []
                    }
                    
                    # Process each root item
                    for item in root_items:
                        menu_item = MenuService._process_menu_item(
                            session, item, role_ids, user.hospital_id)
                        if menu_item:
                            category_menu['items'].append(menu_item)
                    
                    if category_menu['items']:
                        menu.append(category_menu)
                
                # Cache the result if Redis is available
                try:
                    redis_client = get_redis_client()
                    redis_client.setex(
                        cache_key,
                        MenuService.CACHE_TIMEOUT,
                        json.dumps(menu)
                    )
                except Exception as e:
                    current_app.logger.warning(f"Redis cache set error: {str(e)}")
                
                return menu
        except Exception as e:
            current_app.logger.error(f"Error generating menu: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def _process_menu_item(session, item, role_ids, hospital_id):
        """Process a menu item and its children"""
        # Convert row to dict
        if hasattr(item, '_asdict'):
            item = item._asdict()
        elif not isinstance(item, dict):
            item = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        
        # Create menu item dict
        menu_item = {
            'name': item['name'],
            'icon': item['icon'],
            'icon_path': item['icon_path']
        }
        
        # Handle URL based on type
        if item['url']:
            menu_item['url'] = item['url']
        elif item['view_name']:
            try:
                menu_item['url'] = url_for(item['view_name'])
            except Exception:
                menu_item['url'] = '#'
        else:
            menu_item['url'] = '#'
        
        # Get children if any
        children_query = """
            SELECT DISTINCT mi.*
            FROM menu_items mi
            JOIN role_menu_access rma ON mi.item_id = rma.item_id
            WHERE rma.role_id IN :role_ids
            AND rma.can_access = true
            AND mi.is_active = true
            AND mi.parent_id = :parent_id
            AND mi.hospital_id = :hospital_id
            ORDER BY mi.order_index
        """
        
        children = session.execute(children_query, {
            'role_ids': tuple(role_ids),
            'parent_id': str(item['item_id']),
            'hospital_id': str(hospital_id)
        }).fetchall()
        
        if children:
            menu_item['children'] = []
            for child in children:
                child_item = MenuService._process_menu_item(
                    session, child, role_ids, hospital_id)
                if child_item:
                    menu_item['children'].append(child_item)
        
        return menu_item
        
    @staticmethod
    def clear_user_menu_cache(user_id, hospital_id):
        """Clear menu cache for a specific user"""
        try:
            redis_client = get_redis_client()
            cache_key = f"menu:user:{user_id}:hospital:{hospital_id}"
            redis_client.delete(cache_key)
        except Exception as e:
            current_app.logger.warning(f"Redis cache clear error: {str(e)}")
    
    @staticmethod
    def clear_role_menu_cache(role_id, hospital_id):
        """Clear menu cache for all users with a specific role"""
        try:
            redis_client = get_redis_client()
            
            # Get all users with this role
            with get_db_session() as session:
                users = session.query(UserRoleMapping).filter_by(
                    role_id=role_id,
                    hospital_id=hospital_id,
                    is_active=True
                ).all()
                
                # Clear cache for each user
                for user_mapping in users:
                    cache_key = f"menu:user:{user_mapping.user_id}:hospital:{hospital_id}"
                    redis_client.delete(cache_key)
        except Exception as e:
            current_app.logger.error(f"Error clearing role menu cache: {str(e)}", exc_info=True)
6. DataAccessService for Row-Level Security
This service enforces data access control based on user roles:
python# app/services/data_access_service.py

from flask import current_app
from app.services.database_service import get_db_session
from app.models.menu import DataSlicer

class DataAccessService:
    """Service for controlling data access based on roles"""
    
    @staticmethod
    def get_filter_conditions(user, module_name):
        """
        Get filter conditions for a user and module
        
        Args:
            user: User object
            module_name: The module name to get filter conditions for
            
        Returns:
            dict: Filter conditions to apply to queries
        """
        if not user or not user.is_authenticated:
            return {'access_denied': True}
            
        try:
            with get_db_session() as session:
                # Get module ID
                from app.models.config import ModuleMaster
                module = session.query(ModuleMaster).filter_by(
                    module_name=module_name,
                    is_active=True
                ).first()
                
                if not module:
                    return {'access_denied': True}
                
                # Get user's roles
                from app.models.config import UserRoleMapping
                role_mappings = session.query(UserRoleMapping).filter_by(
                    user_id=user.user_id,
                    hospital_id=user.hospital_id,
                    is_active=True
                ).all()
                
                if not role_mappings:
                    return {'access_denied': True}
                
                role_ids = [rm.role_id for rm in role_mappings]
                
                # Check if the user has any data access rules
                data_slicers = session.query(DataSlicer).filter(
                    DataSlicer.role_id.in_(role_ids),
                    DataSlicer.module_id == module.module_id,
                    DataSlicer.hospital_id == user.hospital_id
                ).all()
                
                # If no specific rules, use default behavior
                if not data_slicers:
                    # Check if user has admin role
                    from app.models.config import RoleMaster
                    admin_roles = session.query(RoleMaster).filter(
                        RoleMaster.role_id.in_(role_ids),
                        RoleMaster.role_name.like('%admin%')
                    ).first()
                    
                    if admin_roles:
                        # Admins can see all data
                        return {'hospital_id': user.hospital_id}
                    
                    # Default: users can only see their own data
                    if user.entity_type == 'staff':
                        return {
                            'hospital_id': user.hospital_id,
                            'staff_id': user.entity_id
                        }
                    elif user.entity_type == 'patient':
                        return {
                            'hospital_id': user.hospital_id,
                            'patient_id': user.entity_id
                        }
                    else:
                        return {'hospital_id': user.hospital_id}
                
                # Process data access rules
                access_conditions = {'hospital_id': user.hospital_id}
                
                for slicer in data_slicers:
                    if slicer.access_type == 'all':
                        # Can see all data in this module
                        continue
                    elif slicer.access_type == 'own':
                        # Can only see own data
                        if user.entity_type == 'staff':
                            access_conditions['staff_id'] = user.entity_id
                        elif user.entity_type == 'patient':
                            access_conditions['patient_id'] = user.entity_id
                    elif slicer.access_type == 'department':
                        # Can see data for their department
                        if user.entity_type == 'staff':
                            # Get staff department
                            from app.models.master import Staff
                            staff = session.query(Staff).filter_by(
                                staff_id=user.entity_id
                            ).first()
                            
                            if staff and 'department' in staff.employment_info:
                                dept = staff.employment_info.get('department')
                                access_conditions['department'] = dept
                    elif slicer.access_type == 'assigned':
                        # Can see data assigned to them
                        access_conditions['assigned_to'] = user.entity_id
                    
                    # Apply any custom filter conditions
                    if slicer.filter_condition:
                        for key, value in slicer.filter_condition.items():
                            access_conditions[key] = value
                
                return access_conditions
        
        except Exception as e:
            current_app.logger.error(f"Error in data access service: {str(e)}", exc_info=True)
            return {'access_denied': True}
    
    @staticmethod
    def apply_filters(query, user, module_name):
        """
        Apply data access filters to a query
        
        Args:
            query: SQLAlchemy query
            user: User object
            module_name: Module name
            
        Returns:
            SQLAlchemy query with filters applied
        """
        filters = DataAccessService.get_filter_conditions(user, module_name)
        
        if 'access_denied' in filters:
            # Return empty query if access is denied
            return query.filter(False)
        
        # Apply filters to query
        for key, value in filters.items():
            if hasattr(query.column_descriptions[0]['entity'], key):
                query = query.filter(getattr(query.column_descriptions[0]['entity'], key) == value)
        
        return query
7. Admin Interface for Menu Management
Create views to manage the menu system:
python# app/views/admin_menu_views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.security.authorization.permission_validator import permission_required
from app.services.database_service import get_db_session, get_detached_copy
from app.services.menu_service import MenuService
from app.models.menu import MenuCategory, MenuItem, RoleMenuAccess
from app.models.config import RoleMaster, ModuleMaster
import uuid

menu_admin_bp = Blueprint('menu_admin', __name__, url_prefix='/admin/menu')

@menu_admin_bp.route('/')
@login_required
@permission_required('admin', 'view')
def menu_dashboard():
    """Menu management dashboard"""
    try:
        with get_db_session() as session:
            categories = session.query(MenuCategory).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(MenuCategory.order_index).all()
            
            # Make detached copies
            categories = [get_detached_copy(c) for c in categories]
            
            return render_template(
                'admin/menu/dashboard.html',
                categories=categories
            )
    except Exception as e:
        current_app.logger.error(f"Error in menu dashboard: {str(e)}", exc_info=True)
        flash(f"Error loading menu dashboard: {str(e)}", "error")
        return redirect(url_for('admin_views.dashboard'))

@menu_admin_bp.route('/categories')
@login_required
@permission_required('admin', 'view')
def category_list():
    """List menu categories"""
    try:
        with get_db_session() as session:
            categories = session.query(MenuCategory).filter_by(
                hospital_id=current_user.hospital_id
            ).order_by(MenuCategory.order_index).all()
            
            # Make detached copies
            categories = [get_detached_copy(c) for c in categories]
            
            return render_template(
                'admin/menu/category_list.html',
                categories=categories
            )
    except Exception as e:
        current_app.logger.error(f"Error in category list: {str(e)}", exc_info=True)
        flash(f"Error loading categories: {str(e)}", "error")
        return redirect(url_for('menu_admin.menu_dashboard'))

@menu_admin_bp.route('/category/add', methods=['GET', 'POST'])
@login_required
@permission_required('admin', 'add')
def add_category():
    """Add a new menu category"""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            icon = request.form.get('icon')
            order_index = request.form.get('order_index', 0, type=int)
            
            with get_db_session() as session:
                category = MenuCategory(
                    category_id=uuid.uuid4(),
                    hospital_id=current_user.hospital_id,
                    name=name,
                    description=description,
                    icon=icon,
                    order_index=order_index,
                    is_active=True
                )
                
                session.add(category)
                session.commit()
                
                flash(f"Category '{name}' added successfully", "success")
                return redirect(url_for('menu_admin.category_list'))
        except Exception as e:
            current_app.logger.error(f"Error adding category: {str(e)}", exc_info=True)
            flash(f"Error adding category: {str(e)}", "error")
    
    return render_template('admin/menu/category_form.html')

# Similar routes for editing and deleting categories

@menu_admin_bp.route('/items/<category_id>')
@login_required
@permission_required('admin', 'view')
def item_list(category_id):
    """List menu items for a category"""
    try:
        with get_db_session() as session:
            category = session.query(MenuCategory).filter_by(
                category_id=category_id,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not category:
                flash("Category not found", "error")
                return redirect(url_for('menu_admin.category_list'))
            
            # Get root items
            root_items = session.query(MenuItem).filter_by(
                category_id=category_id,
                hospital_id=current_user.hospital_id,
                parent_id=None
            ).order_by(MenuItem.order_index).all()
            
            # Make detached copies
            category = get_detached_copy(category)
            root_items = [get_detached_copy(i) for i in root_items]
            
            # Get child items for each root item
            for item in root_items:
                children = session.query(MenuItem).filter_by(
                    parent_id=item.item_id,
                    hospital_id=current_user.hospital_id
                ).order_by(MenuItem.order_index).all()
                
                item.child_items = [get_detached_copy(c) for c in children]
            
            return render_template(
                'admin/menu/item_list.html',
                category=category,
                items=root_items
            )
    except Exception as e:
        current_app.logger.error(f"Error in item list: {str(e)}", exc_info=True)
        flash(f"Error loading menu items: {str(e)}", "error")
        return redirect(url_for('menu_admin.category_list'))

@menu_admin_bp.route('/item/add', methods=['GET', 'POST'])
@login_required
@permission_required('admin', 'add')
def add_item():
    """Add a new menu item"""
    try:
        with get_db_session() as session:
            # Get categories for dropdown
            categories = session.query(MenuCategory).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(MenuCategory.name).all()
            
            # Get modules for dropdown
            modules = session.query(ModuleMaster).filter_by(
                is_active=True
            ).order_by(ModuleMaster.module_name).all()
            
            # Get parent items for dropdown
            parent_items = session.query(MenuItem).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True,
                parent_id=None
            ).order_by(MenuItem.name).all()
            
            # Make detached copies
            categories = [get_detached_copy(c) for c in categories]
            modules = [get_detached_copy(m) for m in modules]
            parent_items = [get_detached_copy(p) for p in parent_items]
            
            if request.method == 'POST':
                name = request.form.get('name')
                category_id = request.form.get('category_id')
                parent_id = request.form.get('parent_id') or None
                url = request.form.get('url')
                view_name = request.form.get('view_name')
                icon = request.form.get('icon')
                icon_path = request.form.get('icon_path')
                module_id = request.form.get('module_id') or None
                order_index = request.form.get('order_index', 0, type=int)
                
                # Create new menu item
                menu_item = MenuItem(
                    item_id=uuid.uuid4(),
                    hospital_id=current_user.hospital_id,
                    category_id=category_id,
                    parent_id=parent_id,
                    name=name,
                    url=url,
                    view_name=view_name,
                    icon=icon,
                    icon_path=icon_path,
                    module_id=module_id,
                    order_index=order_index,
                    is_active=True
                )
                
                session.add(menu_item)
                
                # Get all roles for access control
                roles = session.query(RoleMaster).filter_by(
                    hospital_id=current_user.hospital_id,
                    is_active=True
                ).all()
                
                # Create role access entries for each role
                for role in roles:
                    # Get role ID from form checkbox
                    can_access = request.form.get(f'role_{role.role_id}') == 'on'
                    
                    role_access = RoleMenuAccess(
                        access_id=uuid.uuid4(),
                        hospital_id=current_user.hospital_id,
                        role_id=role.role_id,
                        item_id=menu_item.item_id,
                        can_access=can_access
                    )
                    
                    session.add(role_access)
                
                session.commit()
                
                # Clear menu cache for affected roles
                for role in roles:
                    if request.form.get(f'role_{role.role_id}') == 'on':
                        MenuService.clear_role_menu_cache(
                            role.role_id, current_user.hospital_id)
                
                flash(f"Menu item '{name}' added successfully", "success")
                return redirect(url_for(
                    'menu_admin.item_list', 
                    category_id=category_id
                ))
            
            return render_template(
                'admin/menu/item_form.html',
                categories=categories,
                modules=modules,
                parent_items=parent_items,
                roles=roles
            )
    except Exception as e:
        current_app.logger.error(f"Error in add item: {str(e)}", exc_info=True)
        flash(f"Error adding menu item: {str(e)}", "error")
        return redirect(url_for('menu_admin.category_list'))

# Similar routes for editing and deleting menu items

@menu_admin_bp.route('/role-access/<item_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin', 'edit')
def role_access(item_id):
    """Manage role access for a menu item"""