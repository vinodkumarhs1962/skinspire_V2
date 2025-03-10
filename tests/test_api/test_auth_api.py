# tests/test_api/test_auth_api.py
# pytest tests/test_api/test_auth_api.py -v
import pytest
import json

def test_login_api(client, admin_user):
    """Test login API endpoint"""
    response = client.post('/api/auth/login',
                         json={'username': admin_user.user_id, 'password': 'admin123'},
                         headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'token' in data
    
def test_session_validation(client, admin_user):
    """Test token validation"""
    # First login to get token
    login_response = client.post('/api/auth/login',
                              json={'username': admin_user.user_id, 'password': 'admin123'},
                              headers={'Content-Type': 'application/json'})
    
    token = json.loads(login_response.data)['token']
    
    # Test token validation
    validate_response = client.get('/api/auth/validate',
                                headers={'Authorization': f'Bearer {token}'})
    
    assert validate_response.status_code == 200
    data = json.loads(validate_response.data)
    assert data['valid'] is True