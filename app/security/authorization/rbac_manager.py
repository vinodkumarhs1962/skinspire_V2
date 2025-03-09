# app/security/authorization/rbac_manager.py

from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ...models.user import RoleMaster, RoleModuleAccess, ModuleMaster
from ...core.security import SecurityManager

class RBACManager:
    """Manages Role Based Access Control"""
    
    def __init__(self, session: Session):
        self.session = session
        self._permission_cache: Dict[str, Dict] = {}
        
    def _clear_cache(self, user_id: Optional[str] = None):
        """Clear permission cache"""
        if user_id:
            self._permission_cache.pop(user_id, None)
        else:
            self._permission_cache.clear()
    
    def get_user_permissions(self, user_id: str, hospital_id: str) -> Dict:
        """Get all permissions for a user"""
        cache_key = f"{user_id}:{hospital_id}"
        
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
            
        # Query user's roles
        roles = self.session.query(RoleMaster).join(
            RoleModuleAccess
        ).filter(
            RoleMaster.hospital_id == hospital_id,
            RoleMaster.status == 'active'
        ).all()
        
        # Aggregate permissions
        permissions = {}
        for role in roles:
            for access in role.module_access:
                module = access.module.name
                if module not in permissions:
                    permissions[module] = set()
                
                # Add permissions based on access levels
                if access.can_view:
                    permissions[module].add('view')
                if access.can_add:
                    permissions[module].add('add')
                if access.can_edit:
                    permissions[module].add('edit')
                if access.can_delete:
                    permissions[module].add('delete')
                    
        # Convert sets to lists for JSON serialization
        result = {
            module: list(actions) 
            for module, actions in permissions.items()
        }
        
        # Cache the results
        self._permission_cache[cache_key] = result
        return result
    
    def check_permission(self, user_id: str, hospital_id: str, 
                        module: str, action: str) -> bool:
        """Check if user has specific permission"""
        permissions = self.get_user_permissions(user_id, hospital_id)
        return module in permissions and action in permissions[module]
    
    def assign_role(self, user_id: str, role_id: int, 
                   hospital_id: str) -> bool:
        """Assign a role to a user"""
        try:
            # Verify role belongs to hospital
            role = self.session.query(RoleMaster).filter_by(
                role_id=role_id,
                hospital_id=hospital_id,
                status='active'
            ).first()
            
            if not role:
                raise ValueError("Invalid role")
            
            # Create role assignment
            assignment = RoleAssignment(
                user_id=user_id,
                role_id=role_id,
                assigned_at=datetime.now(timezone.utc)
            )
            
            self.session.add(assignment)
            self.session.commit()
            
            # Clear user's permission cache
            self._clear_cache(user_id)
            return True
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to assign role: {str(e)}")
    
    def remove_role(self, user_id: str, role_id: int) -> bool:
        """Remove a role from a user"""
        try:
            assignment = self.session.query(RoleAssignment).filter_by(
                user_id=user_id,
                role_id=role_id
            ).first()
            
            if assignment:
                self.session.delete(assignment)
                self.session.commit()
                self._clear_cache(user_id)
                
            return True
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to remove role: {str(e)}")
    
    def create_role(self, hospital_id: str, role_data: Dict) -> Dict:
        """Create a new role"""
        try:
            role = RoleMaster(
                hospital_id=hospital_id,
                role_name=role_data['name'],
                description=role_data.get('description', ''),
                status='active'
            )
            
            self.session.add(role)
            self.session.commit()
            
            return {
                'role_id': role.role_id,
                'name': role.role_name,
                'description': role.description
            }
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to create role: {str(e)}")
    
    def update_role_permissions(self, role_id: int, 
                              permissions: Dict[str, List[str]]) -> bool:
        """Update role permissions"""
        try:
            # Remove existing permissions
            self.session.query(RoleModuleAccess).filter_by(
                role_id=role_id
            ).delete()
            
            # Add new permissions
            for module_name, actions in permissions.items():
                module = self.session.query(ModuleMaster).filter_by(
                    module_name=module_name
                ).first()
                
                if not module:
                    continue
                    
                access = RoleModuleAccess(
                    role_id=role_id,
                    module_id=module.module_id,
                    can_view='view' in actions,
                    can_add='add' in actions,
                    can_edit='edit' in actions,
                    can_delete='delete' in actions
                )
                
                self.session.add(access)
            
            self.session.commit()
            self._clear_cache()  # Clear all cache as role permissions changed
            return True
            
        except Exception as e:
            self.session.rollback()
            raise ValueError(f"Failed to update permissions: {str(e)}")
    
    def get_role_hierarchy(self, hospital_id: str) -> Dict:
        """Get role hierarchy for a hospital"""
        roles = self.session.query(RoleMaster).filter_by(
            hospital_id=hospital_id,
            status='active'
        ).all()
        
        hierarchy = {}
        for role in roles:
            hierarchy[role.role_id] = {
                'name': role.role_name,
                'description': role.description,
                'permissions': self._get_role_permissions(role.role_id)
            }
            
        return hierarchy
    
    def _get_role_permissions(self, role_id: int) -> Dict[str, List[str]]:
        """Get permissions for a specific role"""
        access_list = self.session.query(RoleModuleAccess).filter_by(
            role_id=role_id
        ).all()
        
        permissions = {}
        for access in access_list:
            module = access.module.name
            actions = []
            
            if access.can_view:
                actions.append('view')
            if access.can_add:
                actions.append('add')
            if access.can_edit:
                actions.append('edit')
            if access.can_delete:
                actions.append('delete')
                
            permissions[module] = actions
            
        return permissions