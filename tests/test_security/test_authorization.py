# tests/test_security/test_authorization.py
# pytest tests/test_security/test_authorization.py

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
import uuid
import os
import traceback
from unittest import mock
from app.models import User, UserRoleMapping, RoleMaster, RoleModuleAccess, ModuleMaster
from app.security.authorization.permission_validator import has_permission, get_user_permissions
from app.services.database_service import get_db_session, set_debug_mode

# Set up logging for tests
logger = logging.getLogger(__name__)

# Check if running in integration or unit test mode
INTEGRATION_MODE = os.environ.get('INTEGRATION_TEST', '1') == '1'

class TestAuthorization:
    """Test suite for authorization and permission functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        logger.info(f"Starting test in {'INTEGRATION' if INTEGRATION_MODE else 'UNIT TEST'} mode")
        
        # Enable SQL query logging in integration mode
        if INTEGRATION_MODE:
            set_debug_mode(True)
            
        # Store test entities for cleanup
        self.test_entities = []
    
    def teardown_method(self):
        """Teardown after each test method"""
        # Disable SQL query logging
        if INTEGRATION_MODE:
            set_debug_mode(False)
            
            # Clean up any test entities
            logger.info("Cleaning up test data")
            try:
                with get_db_session() as session:
                    for entity in self.test_entities:
                        try:
                            entity_type = type(entity)
                            if hasattr(entity, 'module_id'):
                                db_entity = session.query(entity_type).get(entity.module_id)
                            elif hasattr(entity, 'role_id'):
                                db_entity = session.query(entity_type).get(entity.role_id)
                            elif hasattr(entity, 'user_id'):
                                db_entity = session.query(entity_type).filter_by(user_id=entity.user_id).first()
                            else:
                                logger.warning(f"Unknown entity type for cleanup: {entity_type}")
                                continue
                                
                            if db_entity is not None:
                                session.delete(db_entity)
                        except Exception as e:
                            logger.warning(f"Cleanup error: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to clean up test data: {str(e)}")
        
        logger.info("Test completed")
    
    def debug_entity(self, entity, prefix=""):
        """Print all attributes of an entity"""
        if entity is None:
            logger.debug(f"{prefix} Entity is None")
            return
        
        logger.debug(f"{prefix} Entity of type {type(entity).__name__}:")
        for attr in dir(entity):
            if not attr.startswith("_") and not callable(getattr(entity, attr)):
                value = getattr(entity, attr)
                logger.debug(f"{prefix}  - {attr}: {value}")
    
    def test_module_creation(self):
        """
        Test module creation for permissions
        
        This test verifies:
        1. New modules can be created in the database
        2. Module properties are correctly stored
        3. Modules can be retrieved by name
        """
        logger.info("Testing module creation")
        
        # Create a test module with unique name to avoid conflicts
        module_name = f"test_module_{uuid.uuid4().hex[:8]}"
        logger.info(f"Using test module name: {module_name}")
        
        if INTEGRATION_MODE:
            # Integration test - use real database
            try:
                with get_db_session() as session:
                    logger.debug("Creating module entity")
                    module = ModuleMaster(
                        module_name=module_name,
                        description="Test module for permissions",
                        route=f"/test/{module_name}",
                        sequence=999  # High sequence to avoid conflicts
                    )
                    
                    session.add(module)
                    session.flush()  # Make changes visible within transaction
                    logger.debug(f"Module created with ID: {module.module_id}")
                    
                    # Add to test entities for cleanup
                    self.test_entities.append(module)
                    
                    # Verify module creation
                    logger.debug("Querying for created module")
                    created_module = session.query(ModuleMaster).filter_by(module_name=module_name).first()
                    
                    # Debug output for module entity
                    self.debug_entity(created_module, "Retrieved module:")
                    
                    assert created_module is not None, "Module should be created"
                    assert created_module.module_name == module_name, "Module name should match"
                    assert created_module.description == "Test module for permissions", "Description should match"
                    
                    logger.info(f"Successfully created and verified module: {module_name}")
            except Exception as e:
                logger.error(f"Error in test_module_creation: {type(e).__name__}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
        else:
            # Unit test - mock database calls
            with mock.patch('app.security.authorization.permission_validator.get_db_session') as mock_db_session:
                logger.debug("Setting up mocks for database session")
                mock_session = mock.MagicMock()
                mock_db_session.return_value.__enter__.return_value = mock_session
                
                # Setup mock module
                mock_module = ModuleMaster(
                    module_name=module_name,
                    description="Test module for permissions",
                    route=f"/test/{module_name}",
                    sequence=999
                )
                mock_module.module_id = 1  # Simulate auto-assigned ID
                
                # Mock session.add and query behavior
                mock_session.add.return_value = None
                mock_session.query.return_value.filter_by.return_value.first.return_value = mock_module
                
                try:
                    # Create module in mocked session
                    with get_db_session() as session:
                        logger.debug("Creating module entity with mock session")
                        module = ModuleMaster(
                            module_name=module_name,
                            description="Test module for permissions",
                            route=f"/test/{module_name}",
                            sequence=999
                        )
                        session.add(module)
                        session.flush()
                        
                        # Verify using mocked query
                        logger.debug("Querying for created module with mock session")
                        created_module = session.query(ModuleMaster).filter_by(module_name=module_name).first()
                        
                        assert created_module is not None, "Module should be created"
                        assert created_module.module_name == module_name, "Module name should match"
                        assert created_module.description == "Test module for permissions", "Description should match"
                        
                        logger.info(f"Successfully verified mocked module: {module_name}")
                    
                    # Verify mock calls
                    logger.debug("Verifying mock calls")
                    mock_session.add.assert_called_once()
                    mock_session.query.assert_called_with(ModuleMaster)
                    mock_session.query.return_value.filter_by.assert_called_with(module_name=module_name)
                    
                except Exception as e:
                    logger.error(f"Error in mock test: {type(e).__name__}: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Capture mock interaction details for debugging
                    logger.debug("Mock interactions:")
                    if hasattr(mock_session, 'method_calls'):
                        for i, call in enumerate(mock_session.method_calls):
                            logger.debug(f"  {i}: {call}")
                    
                    raise