# tests/test_security_endpoints.py

import pytest
from flask import url_for, current_app
import requests
import json
from datetime import datetime

# Part 1: The original SecurityEndpointTester class
 # These are useful for manual testing and API verification
class SecurityEndpointTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None

    def test_health_endpoints(self):
        """Test basic health check endpoints to verify services are running"""
        endpoints = [
            "/api/security/health",
            "/api/audit/health",
            "/api/rbac/health"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                results[endpoint] = {
                    "status": response.status_code,
                    "body": response.json() if response.ok else None
                }
            except Exception as e:
                results[endpoint] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return results

    def authenticate(self, username, password):
        """Authenticate and get token for subsequent requests"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={
                    "username": username,
                    "password": password
                }
            )
            if response.ok:
                self.token = response.json()["token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def test_security_config(self, hospital_id):
        """Test security configuration endpoints"""
        endpoints = [
            f"/api/security/hospital/{hospital_id}/config",
            f"/api/security/hospital/{hospital_id}/encryption/fields"
        ]
        
        results = {}
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                results[endpoint] = {
                    "status": response.status_code,
                    "body": response.json() if response.ok else None
                }
            except Exception as e:
                results[endpoint] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return results

if __name__ == "__main__":
    tester = SecurityEndpointTester()
    
    # Test health endpoints
    print("\nTesting Health Endpoints:")
    health_results = tester.test_health_endpoints()
    print(json.dumps(health_results, indent=2))
    
    # Test authentication
    print("\nTesting Authentication:")
    auth_result = tester.authenticate("admin", "admin123")
    print(json.dumps(auth_result, indent=2))
    
    # Test security config
    if tester.token:
        print("\nTesting Security Configuration:")
        config_results = tester.test_security_config("test-hospital-id")
        print(json.dumps(config_results, indent=2))

# Part 2: The new pytest-based test functions
# These are for automated testing with proper database fixtures

def test_security_health_check(client):
    """Test health check endpoints are accessible without authentication"""
    endpoints = [
        '/api/security/health',
        '/api/audit/health',
        '/api/rbac/health'
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'healthy'

def test_unauthenticated_access(client, test_hospital):
    """Test that protected endpoints require authentication"""
    protected_endpoints = [
        f'/api/security/hospital/{test_hospital.hospital_id}/config',
        f'/api/security/hospital/{test_hospital.hospital_id}/encryption/fields',
        f'/api/audit/hospital/{test_hospital.hospital_id}/logs',
        f'/api/rbac/hospital/{test_hospital.hospital_id}/roles'
    ]
    
    for endpoint in protected_endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401  # Unauthorized

def get_auth_token(client, username, password):
    """Helper function to get authentication token"""
    response = client.post('/api/auth/login', json={
        'username': username,
        'password': password
    })
    if response.status_code == 200:
        return response.json.get('token')
    return None

@pytest.mark.parametrize('role,expected_status', [
    ('admin', 200),      # Hospital admin should have access
    ('doctor', 403),     # Doctor should not have access
    ('patient', 403)     # Patient should not have access
])
def test_authenticated_access(client, test_hospital, role, expected_status):
    """Test endpoint access with different user roles"""
    # Role credentials from create_database.py and populate_test_data.py
    role_credentials = {
        'admin': ('9876543210', 'admin123'),
        'doctor': ('9811111111', 'test123'),
        'patient': ('9833333333', 'test123')
    }
    
    username, password = role_credentials[role]
    token = get_auth_token(client, username, password)
    assert token is not None, f"Failed to get token for {role}"
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test security configuration access
    response = client.get(
        f'/api/security/hospital/{test_hospital.hospital_id}/config',
        headers=headers
    )
    assert response.status_code == expected_status
    
    if expected_status == 200:
        data = response.json
        assert 'encryption_enabled' in data
        assert 'audit_enabled' in data

def test_security_config_update(client, test_hospital):
    """Test updating security configuration (admin only)"""
    # Login as admin
    token = get_auth_token(client, '9876543210', 'admin123')
    assert token is not None
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try to update security config
    new_config = {
        'encryption_enabled': True,
        'audit_enabled': True,
        'key_rotation_days': 90
    }
    
    response = client.put(
        f'/api/security/hospital/{test_hospital.hospital_id}/config',
        headers=headers,
        json=new_config
    )
    assert response.status_code == 200
    
    # Verify changes were applied
    response = client.get(
        f'/api/security/hospital/{test_hospital.hospital_id}/config',
        headers=headers
    )
    assert response.status_code == 200
    data = response.json
    assert data['encryption_enabled'] == new_config['encryption_enabled']
    assert data['audit_enabled'] == new_config['audit_enabled']

def test_audit_log_access(client, test_hospital):
    """Test audit log access and filtering"""
    # Login as admin
    token = get_auth_token(client, '9876543210', 'admin123')
    assert token is not None
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test getting audit logs with filters
    params = {
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'action': 'login',
        'page': 1,
        'per_page': 10
    }
    
    response = client.get(
        f'/api/audit/hospital/{test_hospital.hospital_id}/logs',
        headers=headers,
        query_string=params
    )
    assert response.status_code == 200
    data = response.json
    assert 'logs' in data
    assert 'total' in data
    assert 'page' in data