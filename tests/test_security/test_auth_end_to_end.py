# tests/test_security/test_auth_end_to_end.py
# End-to-end authentication testing

import pytest
import json
from app.models import User, UserSession, LoginHistory

class TestAuthEndToEnd:
    """End-to-end authentication testing with backend API"""
    
    def test_api_authentication_flow(self, client, session, test_hospital):
        """Test complete authentication flow via API endpoints"""
        # Clear any existing sessions
        session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).update({'is_active': False})
        session.commit()
        
        # Step 1: Test health check endpoint
        status_response = client.get('/api/auth/status')
        assert status_response.status_code == 200
        assert status_response.json['status'] == 'healthy'
        
        # Step 2: Login with API endpoint
        login_response = client.post(
            '/api/auth/login',
            json={
                'username': '9876543210',
                'password': 'admin123'
            },
            headers={'Content-Type': 'application/json'}
        )
        assert login_response.status_code == 200
        assert 'token' in login_response.json
        token = login_response.json['token']
        assert 'user' in login_response.json
        assert login_response.json['user']['id'] == '9876543210'
        
        # Step 3: Verify session was created in database
        user_session = session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).first()
        assert user_session is not None
        assert user_session.token == token
        
        # Step 4: Validate token
        validate_response = client.get(
            '/api/auth/validate',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert validate_response.status_code == 200
        assert validate_response.json['valid'] == True
        
        # Step 5: Access protected endpoint
        users_response = client.get(
            '/api/auth/users',
            headers={'Authorization': f'Bearer {token}'}
        )
        # We may or may not have permission for this endpoint, just check it returns
        assert users_response.status_code in [200, 403]
        
        # Step 6: Logout
        logout_response = client.post(
            '/api/auth/logout',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert logout_response.status_code == 200
        assert 'message' in logout_response.json
        assert 'Successfully logged out' in logout_response.json['message']
        
        # Step 7: Verify session was deactivated in database
        session.expire_all()
        active_session = session.query(UserSession).filter_by(
            token=token,
            is_active=True
        ).first()
        assert active_session is None
        
        # Step 8: Verify token is no longer valid
        invalid_response = client.get(
            '/api/auth/validate',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert invalid_response.status_code == 401