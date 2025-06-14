# app/services/approval_service.py
import json
import uuid
from datetime import datetime
from flask import current_app
from app.services.database_service import get_db_session, get_detached_copy
from app.models.transaction import StaffApprovalRequest, User
from app.models.master import Staff
from app.models.config import RoleMaster

class ApprovalService:
    @classmethod
    def submit_approval_request(cls, user_id, request_data):
        """Submit a new staff approval request"""
        try:
            with get_db_session() as session:
                # Find the user
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user or user.entity_type != 'staff':
                    return {'success': False, 'message': 'Invalid user'}
                
                # Check for existing pending requests
                existing_request = session.query(StaffApprovalRequest).filter(
                    StaffApprovalRequest.staff_id == user.entity_id,
                    StaffApprovalRequest.status == 'pending'
                ).first()
                
                if existing_request:
                    return {'success': False, 'message': 'A pending approval request already exists'}
                
                # Create new approval request
                new_request = StaffApprovalRequest(
                    request_id=str(uuid.uuid4()),
                    user_id=user_id,  # Include user_id
                    staff_id=user.entity_id,
                    hospital_id=user.hospital_id,
                    branch_id=request_data.get('branch_id'),
                    status='pending',
                    request_data=json.dumps(request_data),
                    created_at=datetime.now()
                )
                
                session.add(new_request)
                
                # Create a detached copy before committing and closing the session
                detached_request = get_detached_copy(new_request)
                
                session.commit()
                
                return {
                    'success': True, 
                    'message': 'Approval request submitted successfully',
                    'request_id': detached_request.request_id
                }
        except Exception as e:
            current_app.logger.error(f"Error submitting approval request: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def approve_request(cls, request_id, approver_id, notes=None, role_id=None):
        """Approve a staff approval request"""
        try:
            with get_db_session() as session:
                # Find the request
                approval_request = session.query(StaffApprovalRequest).filter(
                    StaffApprovalRequest.request_id == request_id
                ).first()
                
                if not approval_request or approval_request.status != 'pending':
                    return {'success': False, 'message': 'Invalid or already processed request'}
                
                # Find the staff and user
                staff = session.query(Staff).filter(
                    Staff.staff_id == approval_request.staff_id
                ).first()
                
                user = session.query(User).filter(
                    User.entity_id == approval_request.staff_id,
                    User.entity_type == 'staff'
                ).first()
                
                if not staff or not user:
                    return {'success': False, 'message': 'Staff or user not found'}
                
                # Update staff record
                # Parse and update staff information from request data
                request_data = json.loads(approval_request.request_data) if approval_request.request_data else {}
                
                # Update employment info
                employment_info = json.loads(staff.employment_info) if staff.employment_info else {}
                employment_info.update({
                    'approval_date': datetime.now().isoformat(),
                    'status': 'active'
                })
                staff.employment_info = json.dumps(employment_info)
                
                # Update role if specified
                if role_id and role_id != '0':
                    role = session.query(RoleMaster).filter(
                        RoleMaster.role_id == role_id,
                        RoleMaster.hospital_id == approval_request.hospital_id
                    ).first()
                    
                    if role:
                        # Update staff role information
                        professional_info = json.loads(staff.professional_info) if staff.professional_info else {}
                        professional_info['role_id'] = role.role_id
                        professional_info['role_name'] = role.role_name
                        staff.professional_info = json.dumps(professional_info)
                
                # Activate the user
                user.is_active = True
                
                # Update approval request
                approval_request.status = 'approved'
                approval_request.approved_at = datetime.now()
                approval_request.approver_id = approver_id
                approval_request.notes = notes
                
                # Make detached copies before committing
                detached_user = get_detached_copy(user)
                detached_staff = get_detached_copy(staff)
                
                # Commit changes
                session.commit()
                
                # Trigger notifications (placeholder - implement actual notification logic)
                cls._send_approval_notification(detached_user, detached_staff)
                
                return {
                    'success': True, 
                    'message': 'Staff request approved successfully'
                }
        except Exception as e:
            current_app.logger.error(f"Error approving request: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def reject_request(cls, request_id, approver_id, notes=None):
        """Reject a staff approval request"""
        try:
            with get_db_session() as session:
                # Find the request
                approval_request = session.query(StaffApprovalRequest).filter(
                    StaffApprovalRequest.request_id == request_id
                ).first()
                
                if not approval_request or approval_request.status != 'pending':
                    return {'success': False, 'message': 'Invalid or already processed request'}
                
                # Update approval request
                approval_request.status = 'rejected'
                approval_request.approved_at = datetime.now()
                approval_request.approver_id = approver_id
                approval_request.notes = notes
                
                # Find the user
                user = session.query(User).filter(
                    User.entity_id == approval_request.staff_id,
                    User.entity_type == 'staff'
                ).first()
                
                # Optional: Mark user as inactive
                if user:
                    user.is_active = False
                    # Make detached copy before committing
                    detached_user = get_detached_copy(user)
                
                # Commit changes
                session.commit()
                
                # Trigger rejection notification (placeholder)
                if user:
                    cls._send_rejection_notification(detached_user, notes)
                
                return {
                    'success': True, 
                    'message': 'Staff request rejected successfully'
                }
        except Exception as e:
            current_app.logger.error(f"Error rejecting request: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def _send_approval_notification(cls, user, staff):
        """Send approval notification (placeholder method)"""
        try:
            # Implement email/SMS notification logic here
            contact_info = json.loads(staff.contact_info) if staff.contact_info else {}
            email = contact_info.get('email')
            phone = contact_info.get('phone')
            
            # Log the notification attempt
            current_app.logger.info(f"Approval notification sent to: {email} / {phone}")
        except Exception as e:
            current_app.logger.error(f"Error sending approval notification: {str(e)}")
    
    @classmethod
    def _send_rejection_notification(cls, user, notes):
        """Send rejection notification (placeholder method)"""
        try:
            # Implement email/SMS notification logic here
            # Include rejection notes in the notification
            current_app.logger.info(f"Rejection notification sent to user {user.user_id}")
        except Exception as e:
            current_app.logger.error(f"Error sending rejection notification: {str(e)}")
    
    @classmethod
    def get_request_status(cls, user_id):
        """Get latest approval request status for a user"""
        try:
            with get_db_session() as session:
                # Find the user
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user or user.entity_type != 'staff':
                    return {'status': 'not_applicable'}
                
                # Get latest request
                latest_request = session.query(StaffApprovalRequest).filter(
                    StaffApprovalRequest.staff_id == user.entity_id
                ).order_by(
                    StaffApprovalRequest.created_at.desc()
                ).first()
                
                if not latest_request:
                    return {'status': 'no_request'}
                
                # Create detached copy or extract necessary data
                detached_request = get_detached_copy(latest_request)
                
                return {
                    'status': detached_request.status,
                    'request_id': detached_request.request_id,
                    'created_at': detached_request.created_at,
                    'notes': detached_request.notes
                }
        except Exception as e:
            current_app.logger.error(f"Error getting request status: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}   