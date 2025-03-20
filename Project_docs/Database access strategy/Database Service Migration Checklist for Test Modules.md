# Database Service Migration Checklist for Test Modules

This guide explains how to update test modules to use the database service while supporting both unit test and integration test modes.

## Overview

The migration involves these key changes:
1. Always use `get_db_session()` instead of direct database sessions
2. Add support for both integration and unit test modes
3. Remove legacy code that doesn't use database service
4. Implement mocking for unit tests while maintaining consistent API usage

## Prerequisites

- Import required modules
  ```python
  import os
  import logging
  from unittest import mock
  from app.services.database_service import get_db_session
  ```

- Set up logging
  ```python
  # Set up logging for tests
  logger = logging.getLogger(__name__)
  ```

- Set up environment detection
  ```python
  # Check if running in integration or unit test mode
  INTEGRATION_MODE = os.environ.get('INTEGRATION_TEST', '1') == '1'
  ```

## Checklist

### 1. Remove Direct Session Access

- [ ] Replace all fixture-provided session parameters with `get_db_session()` context manager
- [ ] Remove all direct imports and references to `db.session`
- [ ] Remove all direct session creation/management code

### 2. Use `get_db_session()` Context Manager

- [ ] Replace all database operations with code following this pattern:
  ```python
  with get_db_session() as session:
      # Database operations
      result = session.query(Model).filter_by(field=value).first()
  ```

- [ ] Use `session.flush()` instead of `session.commit()` within the context manager

### 3. Add Integration/Unit Test Mode Support

- [ ] Add condition to check INTEGRATION_MODE for each test method
- [ ] Implement real database operations in the integration mode branch
- [ ] Implement mocked operations in the unit test mode branch

### 4. Pattern for Test Methods

```python
def test_some_functionality(self):
    """Test description"""
    
    if INTEGRATION_MODE:
        # Integration test - use real database
        with get_db_session() as session:
            # Real database operations
            entity = Model(field="value")
            session.add(entity)
            session.flush()
            
            # Query and assertions
            result = session.query(Model).filter_by(field="value").first()
            assert result is not None
            assert result.field == "value"
    else:
        # Unit test - mock database operations
        with mock.patch('app.services.database_service.get_db_session') as mock_db_session:
            # Set up mock session
            mock_session = mock.MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            
            # Set up mock returns
            mock_result = Model(field="value")
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_result
            
            # Use the mocked database service with same API
            with get_db_session() as session:
                result = session.query(Model).filter_by(field="value").first()
                assert result is not None
                assert result.field == "value"
```

### 5. Best Practices for Mocking

- [ ] Mock the correct path: `'app.services.database_service.get_db_session'`
- [ ] Set up the `__enter__` method's return value to provide the mock session
- [ ] Configure the mock session to return appropriate values for method chains
- [ ] Keep database access patterns consistent between the integration and unit test branches

### 6. Update Service Function Tests

When testing service functions that themselves use `get_db_session()`:

```python
def test_service_function(self):
    if INTEGRATION_MODE:
        # Integration test with real database
        result = service_function(param="value")
        assert result.is_valid
    else:
        # Unit test with mocks
        with mock.patch('module.path.to.service.get_db_session') as mock_db_session:
            # Setup mock session
            mock_session = mock.MagicMock()
            mock_db_session.return_value.__enter__.return_value = mock_session
            
            # Setup mock returns
            mock_result = Model(field="value")
            mock_session.query.return_value.filter_by.return_value.first.return_value = mock_result
            
            # Call the service function
            result = service_function(param="value")
            assert result.is_valid
```

### 7. Remove Legacy Code

- [ ] Delete any commented-out legacy code blocks
- [ ] Remove all database-session related test fixtures from conftest.py that aren't needed anymore
- [ ] Remove duplicate test classes that exist for both approaches (e.g., TestClass and TestClassWithDBService)

## Error Logging and Debugging

### 1. Implement Detailed Test Logging

- [ ] Add appropriate logging to test methods:
  ```python
  def test_example_operation(self):
      logger.info("Testing example operation")
      
      # Log significant values
      logger.info(f"Test parameters: param1={param1}, param2={param2}")
      
      try:
          with get_db_session() as session:
              result = session.query(Model).filter_by(field="value").first()
              logger.info(f"Query result: {result}")
              
              # Additional operations...
      except Exception as e:
          logger.error(f"Error during example operation: {str(e)}")
          logger.exception("Full exception details:")
          raise  # Re-raise to fail the test
  ```

### 2. Add SQL Query Logging for Integration Tests

- [ ] Add SQL logging option in test setup:
  ```python
  def setup_method(self):
      if INTEGRATION_MODE:
          from app.services.database_service import set_debug_mode
          set_debug_mode(True)  # Enable SQL logging
          
  def teardown_method(self):
      if INTEGRATION_MODE:
          from app.services.database_service import set_debug_mode
          set_debug_mode(False)  # Disable SQL logging
  ```

### 3. Mock Call Verification

- [ ] Add assertions to verify mock calls in unit tests:
  ```python
  # Verify that a specific method was called
  mock_session.add.assert_called_once()
  
  # Verify method was called with specific arguments
  mock_session.add.assert_called_once_with(mock.ANY)
  
  # Verify a complex chain
  mock_session.query.assert_called_once_with(User)
  mock_session.query.return_value.filter_by.assert_called_once_with(username="test")
  ```

### 4. Debug Print Helpers

- [ ] Add helper methods to standardize debug output:
  ```python
  def debug_object(obj, prefix=""):
      """Print all attributes of an object"""
      if obj is None:
          logger.debug(f"{prefix} Object is None")
          return
      
      logger.debug(f"{prefix} Object of type {type(obj)}:")
      for attr in dir(obj):
          if not attr.startswith("_") and not callable(getattr(obj, attr)):
              value = getattr(obj, attr)
              logger.debug(f"{prefix}  - {attr}: {value}")
  ```

### 5. Transaction Debugging

- [ ] Add transaction debugging for complex tests:
  ```python
  def test_complex_transaction(self):
      try:
          with get_db_session() as session:
              # First operation
              logger.debug("Starting first operation")
              session.add(Model(field="value"))
              session.flush()
              logger.debug("First operation complete")
              
              # Second operation
              logger.debug("Starting second operation")
              result = session.query(Model).filter_by(field="value").first()
              logger.debug(f"Second operation result: {result}")
      except Exception as e:
          logger.error(f"Transaction failed: {str(e)}")
          if INTEGRATION_MODE:
              # Get additional database state information
              try:
                  with get_db_session(read_only=True) as debug_session:
                      current_state = debug_session.query(Model).all()
                      logger.debug(f"Current database state: {current_state}")
              except Exception as debug_error:
                  logger.error(f"Failed to query debug state: {str(debug_error)}")
          raise
  ```

### 6. Capture Mock Interactions

- [ ] Record mock interactions for detailed debugging:
  ```python
  def test_with_mock_capture(self):
      with mock.patch('app.services.database_service.get_db_session') as mock_db_session:
          mock_session = mock.MagicMock()
          mock_db_session.return_value.__enter__.return_value = mock_session
          
          # Enable call recording
          mock_session.method_calls = []
          
          # Execute test operations
          with get_db_session() as session:
              session.query(Model).filter_by(field="value").first()
              session.add(Model(field="new_value"))
              
          # Print all captured interactions
          logger.debug("Mock interactions:")
          for i, call in enumerate(mock_session.method_calls):
              logger.debug(f"  {i}: {call}")
  ```

### 7. Integration Test Data Setup Logging

- [ ] Add clear logging around test data setup and teardown:
  ```python
  def test_with_data_setup(self):
      if INTEGRATION_MODE:
          logger.info("Setting up test data")
          test_data = []
          
          with get_db_session() as session:
              # Create test records
              for i in range(3):
                  record = Model(field=f"test_{i}")
                  session.add(record)
                  test_data.append(record)
              session.flush()
              
              # Log created records
              logger.info(f"Created {len(test_data)} test records")
              for record in test_data:
                  logger.debug(f"  id: {record.id}, field: {record.field}")
              
              # Run test logic
              # ...
              
              # Clean up
              logger.info("Cleaning up test data")
              for record in test_data:
                  session.delete(record)
      else:
          # Unit test logic
          # ...
  ```

### 8. Exception Handling with Detail Capture

- [ ] Enhance exception handling to capture more context:
  ```python
  def test_exception_handling(self):
      try:
          with get_db_session() as session:
              # Test operations that might fail
              entity = Model(invalid_field="test")  # This will cause an error
              session.add(entity)
              session.flush()
      except Exception as e:
          logger.error(f"Operation failed: {type(e).__name__}: {str(e)}")
          
          # Capture SQLAlchemy specific errors
          if hasattr(e, 'orig') and e.orig is not None:
              logger.error(f"Original DB error: {type(e.orig).__name__}: {str(e.orig)}")
          
          # For integration tests, attempt to query current state
          if INTEGRATION_MODE:
              try:
                  with get_db_session(read_only=True) as debug_session:
                      # Query related data to debug
                      debug_data = debug_session.query(Model).filter_by(partial_field="test").all()
                      logger.debug(f"Found {len(debug_data)} related records")
              except:
                  pass  # Ignore errors in debug session
          
          raise  # Re-raise the original exception
  ```

## Additional Mock Patterns

For more complex queries, use the following patterns to set up mocks:

- Simple query with result list:
  ```python
  mock_result_list = [Model(id=1), Model(id=2)]
  mock_session.query.return_value.filter.return_value.all.return_value = mock_result_list
  ```

- Query with order_by:
  ```python
  mock_query = mock.MagicMock()
  mock_session.query.return_value = mock_query
  mock_query.filter_by.return_value = mock_query
  mock_query.order_by.return_value = mock_query
  mock_query.all.return_value = mock_result_list
  ```

- Query with join:
  ```python
  mock_query = mock.MagicMock()
  mock_session.query.return_value = mock_query
  mock_query.join.return_value = mock_query
  mock_query.filter.return_value = mock_query
  mock_query.first.return_value = mock_result
  ```

## Common Issues and Solutions

1. **Issue**: Test passes in integration mode but fails in unit test mode
   **Solution**: Check mock setup - ensure all chained method calls return appropriate values

2. **Issue**: Session usage after context manager exits
   **Solution**: Keep all session operations within the `with get_db_session()` block

3. **Issue**: Excessive mocking complexity
   **Solution**: 
   - Break down complex queries into helper functions
   - Use separate test methods for different query scenarios
   - Consider using a mocking helper module for common patterns

4. **Issue**: Difficulties with SQLAlchemy 2.0 style queries in mocks
   **Solution**: 
   ```python
   # Old style: session.query(Model).get(id)
   mock_session.query.return_value.get.return_value = mock_model
   
   # New style: session.get(Model, id)
   mock_session.get.return_value = mock_model
   ```

5. **Issue**: Mocking complex joins and relationships
   **Solution**: Focus on mocking the final result rather than the intermediate steps

6. **Issue**: Difficult to trace source of database errors
   **Solution**: Use the database service's debug mode and add exception handling with detailed logging:
   ```python
   try:
       with get_db_session() as session:
           # Operations...
   except Exception as e:
       logger.error(f"Database operation failed: {str(e)}")
       logger.exception("Stack trace:")
       raise
   ```

7. **Issue**: Mysterious test failures in CI but not locally
   **Solution**: Add environment logging at test start:
   ```python
   def setup_module():
       """Log environment information when tests start"""
       from app.services.database_service import get_active_env, get_database_url
       
       logger.info(f"Running tests in environment: {get_active_env()}")
       logger.info(f"Database URL: {get_database_url()}")
       logger.info(f"Integration mode: {INTEGRATION_MODE}")
   ```

8. **Issue**: Inconsistent test behavior due to transaction isolation
   **Solution**: Ensure proper cleanup in teardown methods and use explicit transaction boundaries:
   ```python
   def teardown_method(self):
       """Ensure test data is cleaned up"""
       if INTEGRATION_MODE and hasattr(self, 'test_entities'):
           with get_db_session() as session:
               for entity in self.test_entities:
                   try:
                       db_entity = session.query(type(entity)).get(entity.id)
                       if db_entity is not None:
                           session.delete(db_entity)
                   except Exception as e:
                       logger.warning(f"Cleanup error: {str(e)}")
   ```

By following this checklist, you'll ensure consistent database access patterns across all test modules, making them both more maintainable and aligned with the new database service approach. The added logging and debugging features will help identify and resolve issues more quickly during development and testing.