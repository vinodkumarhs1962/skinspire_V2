# tests/test_security/test_environment.py
import os
import pytest
from unittest.mock import MagicMock

# Global flag to determine if we're running in integration mode
INTEGRATION_MODE = os.environ.get("INTEGRATION_TEST", "0") == "1"

def integration_flag():
    """Return the current integration test mode flag"""
    return INTEGRATION_MODE

def mock_if_needed(mocker, target, integration_mode=None):
    """
    Create a mock only if we're in unit test mode.
    
    Args:
        mocker: pytest's mocker fixture
        target: what to mock (e.g., 'requests.post')
        integration_mode: override integration mode flag
    
    Returns:
        A mock object in unit test mode, None in integration mode
    """
    if integration_mode is None:
        integration_mode = integration_flag()
        
    if not integration_mode:
        return mocker.patch(target)
    return None

def create_mock_response(status_code=200, json_data=None, text=None):
    """
    Create a mock response object that mimics requests.Response
    
    Args:
        status_code: HTTP status code
        json_data: Data to return from .json() method
        text: Text to return from .text property
    
    Returns:
        Mock response object
    """
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = lambda: json_data
    
    if text is not None:
        type(mock_resp).text = text
    
    return mock_resp