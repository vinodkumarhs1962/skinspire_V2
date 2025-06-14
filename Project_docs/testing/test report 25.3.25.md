(skinspire_v2_env) C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2>python -m tests.test_security.verify_core
INFO:app:Using centralized environment: development
INFO:app.core.environment:Environment set to: testing (test)
INFO:tests.test_environment:Environment set to: development
INFO:tests.test_environment:Disabled nested transactions for testing
INFO:tests.test_environment:Default INTEGRATION_TEST=1 (integration mode)
INFO:tests.test_environment:CSRF Bypass configured: True
INFO:tests.test_environment:Test environment configured: True
INFO:tests.test_environment:Integration mode is ENABLED
INFO:app.services.database_service:Database initialized successfully
INFO:app.services.database_service:Nested transactions disabled
INFO:__main__:=== Environment Information ===
INFO:__main__:Python version: 3.13.2 (tags/v3.13.2:4f8bb39, Feb  4 2025, 15:23:48) [MSC v.1942 64 bit (AMD64)]
INFO:__main__:Python executable: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe
INFO:__main__:Working directory: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2
INFO:__main__:Database environment: development
INFO:__main__:Database URL: postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev
INFO:__main__:Environment variables:
INFO:__main__:  FLASK_ENV: testing
INFO:__main__:  FLASK_APP: Not set
INFO:__main__:  PYTHONPATH: C:\Users\vinod\AppData\Local\Programs\skinspire-env\Scripts
INFO:__main__:Integration mode: ENABLED
INFO:__main__:Database service: ENABLED
INFO:__main__:===============================
INFO:__main__:Starting core system verification...
INFO:__main__:Integration mode: ENABLED
INFO:__main__:Database service: ENABLED
INFO:__main__:Verifying environment setup...
INFO:__main__:Running tests: tests/test_security/test_setup_verification.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_setup_verification.py --cov=tests --cov-report=term      
INFO:__main__:Executing main test command: pytest tests/test_security/test_setup_verification.py -v
INFO:__main__:Test execution completed in 1.30 seconds
INFO:__main__:[OK] Environment setup verification passed
INFO:__main__:Verifying database setup...
INFO:__main__:Database connection successful. Version: PostgreSQL 17.2 on x86_64-windows, compiled by msvc-19.42.34435, 64-bit
INFO:__main__:Running tests: tests/test_db_setup.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_db_setup.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_db_setup.py -v
INFO:__main__:Test execution completed in 1.54 seconds
INFO:__main__:[OK] Database verification passed
INFO:__main__:Verifying encryption functionality...
INFO:__main__:Running tests: tests/test_security/test_encryption.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_encryption.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_encryption.py -v
INFO:__main__:Test execution completed in 1.35 seconds
INFO:__main__:[OK] Encryption verification passed
INFO:__main__:Verifying authentication functionality...
INFO:__main__:Running tests: tests/test_security/test_authentication.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_authentication.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_authentication.py -v
INFO:__main__:Test execution completed in 2.92 seconds
INFO:__main__:[OK] Authentication verification passed
INFO:__main__:Verifying user management...
INFO:__main__:Running tests: tests/test_security/test_user_management.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_user_management.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_user_management.py -v
INFO:__main__:Test execution completed in 2.22 seconds
INFO:__main__:[OK] User management verification passed in 2.23s
INFO:__main__:Verifying authorization...
INFO:__main__:Pre-test diagnostic: 101 roles, 88 modules in database
INFO:__main__:Running tests: tests/test_security/test_authorization.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_authorization.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_authorization.py -v
INFO:__main__:Test execution completed in 1.32 seconds
INFO:__main__:[OK] Authorization verification passed
INFO:__main__:Verifying frontend authentication views...
INFO:__main__:Running tests: tests/test_security/test_auth_views.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_auth_views.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_auth_views.py -v
INFO:__main__:Test execution completed in 5.43 seconds
INFO:__main__:[OK] Authentication views verification passed
INFO:__main__:Verifying end-to-end authentication flow...
INFO:__main__:Running tests: tests/test_security/test_auth_end_to_end.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_auth_end_to_end.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_auth_end_to_end.py -v
INFO:__main__:Test execution completed in 9.79 seconds
INFO:__main__:[OK] End-to-end authentication verification passed
INFO:__main__:Verifying authentication UI components...
INFO:__main__:Running tests: tests/test_security/test_auth_ui.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_auth_ui.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_auth_ui.py -v
INFO:__main__:Test execution completed in 1.35 seconds
INFO:__main__:[OK] Authentication UI verification passed
INFO:__main__:Verifying authentication flow...
INFO:__main__:Running tests: tests/test_security/test_auth_flow.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Added coverage reporting: tests/test_security/test_auth_flow.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_auth_flow.py -v
INFO:__main__:Test execution completed in 13.84 seconds
INFO:__main__:[OK] Authentication flow verification passed
INFO:__main__:Verifying complete authentication system...
INFO:__main__:This could take a few minutes. Please be patient...
INFO:__main__:Running tests: tests/test_security/test_auth_system.py
INFO:__main__:Running in INTEGRATION mode
INFO:__main__:Using DATABASE SERVICE for tests
INFO:__main__:Running account_lockout test with detailed logging
INFO:__main__:Detailed output for account_lockout test:
INFO:__main__:============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.3.4, pluggy-1.5.0 -- C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe
cachedir: C:\Users\vinod\.pytest_cache
rootdir: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2
configfile: pytest.ini
plugins: mock-3.14.0
collecting ... collected 0 items

============================ no tests ran in 0.08s ============================

ERROR:__main__:Detailed errors:
ERROR:__main__:ERROR: not found: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\tests\test_security\test_auth_system.py::TestAuthenticationWithDBService::test_account_lockout
(no match in any of [<Module test_auth_system.py>])


INFO:__main__:Added coverage reporting: tests/test_security/test_auth_system.py --cov=tests --cov-report=term
INFO:__main__:Executing main test command: pytest tests/test_security/test_auth_system.py -v
INFO:__main__:Test execution completed in 8.35 seconds
INFO:__main__:[OK] Complete authentication system verification passed
INFO:__main__:All verifications completed in 49.56 seconds
INFO:__main__:Results saved to verification_status.json

============= VERIFICATION SUMMARY =============
Run Time: 2025-03-25T13:27:51.040594
Integration Mode: ENABLED
Database Service: ENABLED
Total Components: 11
Passed: 11
Failed: 0
Total Execution Time: 49.56 seconds

Component Status:
  [OK] Setup Verification: PASS in 1.30s (2 passed, 0 failed, 0 skipped)
  [OK] Database: PASS in 1.54s (7 passed, 0 failed, 0 skipped)
  [OK] Encryption: PASS in 1.35s (3 passed, 0 failed, 0 skipped)
  [OK] Authentication: PASS in 2.92s (12 passed, 0 failed, 0 skipped)
  [OK] User Management: PASS in 2.22s (4 passed, 0 failed, 0 skipped)
  [OK] Authorization: PASS in 1.32s (1 passed, 0 failed, 0 skipped)
  [OK] Auth Views: PASS in 5.43s (5 passed, 0 failed, 0 skipped)
  [OK] Auth End To End: PASS in 9.79s (1 passed, 0 failed, 1 skipped)
  [OK] Auth Ui: PASS in 1.35s (4 passed, 0 failed, 0 skipped)
  [OK] Auth Flow: PASS in 13.84s (3 passed, 0 failed, 1 skipped)
  [OK] Auth System: PASS in 8.35s (12 passed, 0 failed, 0 skipped)
=================================================

(skinspire_v2_env) C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2>python scripts/test_db_features.py
Starting enhanced database test script (using manage_db.py for operations)...
2025-03-25 13:42:20,666 - INFO - Running tests with configuration:
2025-03-25 13:42:20,666 - INFO -   all: True
2025-03-25 13:42:20,666 - INFO -   config: False
2025-03-25 13:42:20,666 - INFO -   backup: False
2025-03-25 13:42:20,668 - INFO -   copy: False
2025-03-25 13:42:20,668 - INFO -   triggers: False
2025-03-25 13:42:20,669 - INFO -   switch_env: False
2025-03-25 13:42:20,669 - INFO -   inspect_db: False
2025-03-25 13:42:20,669 - INFO -
============================================================
2025-03-25 13:42:20,670 - INFO -                   TESTING CONFIGURATION
2025-03-25 13:42:20,670 - INFO - ============================================================
2025-03-25 13:42:20,673 - INFO - Reading database URLs from .env file
2025-03-25 13:42:20,673 - INFO - Found database URLs:
2025-03-25 13:42:20,673 - INFO -   FLASK_ENV: test
2025-03-25 13:42:20,674 - INFO -   DEV_DATABASE_URL: postgresql://skinspire_admin:***@localhost:5432/skinspire_dev        
2025-03-25 13:42:20,674 - INFO -   TEST_DATABASE_URL: postgresql://skinspire_admin:***@localhost:5432/skinspire_test      
2025-03-25 13:42:20,674 - INFO -   PROD_DATABASE_URL: postgresql://skinspire_admin:***@localhost:5432/skinspire_prod      
2025-03-25 13:42:20,674 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_dev
2025-03-25 13:42:20,967 - INFO - Database connection successful for dev environment
2025-03-25 13:42:20,968 - INFO - PASS: Configuration - Dev Database Connection
2025-03-25 13:42:20,968 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_test
2025-03-25 13:42:21,003 - INFO - Database connection successful for test environment
2025-03-25 13:42:21,003 - INFO - PASS: Configuration - Test Database Connection
2025-03-25 13:42:21,003 - INFO -
============================================================
2025-03-25 13:42:21,004 - INFO -                 TESTING BACKUP AND RESTORE
2025-03-25 13:42:21,004 - INFO - ============================================================
2025-03-25 13:42:21,004 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_test
2025-03-25 13:42:21,039 - INFO - Database connection successful for test environment
2025-03-25 13:42:21,079 - INFO - PASS: Backup - Create Test Table
2025-03-25 13:42:21,082 - INFO - PASS: Backup - Insert Test Data
2025-03-25 13:42:21,083 - INFO - Test data verified: [(1, 'test_value', datetime.datetime(2025, 3, 25, 13, 42, 21, 73556))]
2025-03-25 13:42:21,083 - INFO - PASS: Backup - Verify Test Data
2025-03-25 13:42:21,085 - INFO -
============================================================
2025-03-25 13:42:21,085 - INFO -                  BACKING UP TEST DATABASE
2025-03-25 13:42:21,085 - INFO - ============================================================
2025-03-25 13:42:21,085 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py create-backup --env test --output test_backup_20250325_134221.sql
2025-03-25 13:42:21,881 - INFO - manage_db.py: Creating backup of test database...
2025-03-25 13:42:21,881 - INFO - manage_db.py: SUCCESS: Backup created successfully: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\backups\test_backup_20250325_134221.sql
2025-03-25 13:42:21,882 - INFO - Backup created successfully: backups\test_backup_20250325_134221.sql
2025-03-25 13:42:21,882 - INFO - PASS: Backup test Database
2025-03-25 13:42:21,884 - INFO - PASS: Backup - Modify Table
2025-03-25 13:42:21,889 - INFO - Column 'extra' was added successfully
2025-03-25 13:42:21,889 - INFO - PASS: Backup - Verify Column Added
2025-03-25 13:42:21,892 - INFO - 
============================================================
2025-03-25 13:42:21,892 - INFO -                  RESTORING TEST DATABASE
2025-03-25 13:42:21,892 - INFO - ============================================================
2025-03-25 13:42:21,892 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py restore-backup backups\test_backup_20250325_134221.sql
2025-03-25 13:42:21,893 - INFO - Updated .flask_env_type with 'test'
2025-03-25 13:42:23,451 - INFO - manage_db.py: Using environment from centralized configuration: test (testing)
2025-03-25 13:42:23,452 - INFO - manage_db.py: Warning! This will restore the test database from backups\test_backup_20250325_134221.sql. Are you sure? [y/N]: Restoring test database from backups\test_backup_20250325_134221.sql...
2025-03-25 13:42:23,452 - INFO - manage_db.py: SUCCESS: Database restored successfully
2025-03-25 13:42:23,452 - INFO - Successfully restored test database from backups\test_backup_20250325_134221.sql
2025-03-25 13:42:23,453 - INFO - PASS: Restore test Database
2025-03-25 13:42:23,456 - INFO - Column 'extra' was removed successfully during restore
2025-03-25 13:42:23,456 - INFO - PASS: Backup - Verify Restore
2025-03-25 13:42:23,457 - INFO - Cleaned up test table
2025-03-25 13:42:23,459 - INFO -
============================================================
2025-03-25 13:42:23,460 - INFO -                   TESTING DATABASE COPY
2025-03-25 13:42:23,460 - INFO - ============================================================
2025-03-25 13:42:23,460 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_dev
2025-03-25 13:42:23,493 - INFO - Database connection successful for dev environment
2025-03-25 13:42:23,493 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_test
2025-03-25 13:42:23,528 - INFO - Database connection successful for test environment
2025-03-25 13:42:23,529 - INFO - 
============================================================
2025-03-25 13:42:23,530 - INFO -                  BACKING UP DEV DATABASE
2025-03-25 13:42:23,530 - INFO - ============================================================
2025-03-25 13:42:23,531 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py create-backup --env dev --output dev_backup_20250325_134223.sql  
2025-03-25 13:42:24,321 - INFO - manage_db.py: Creating backup of dev database...
2025-03-25 13:42:24,322 - INFO - manage_db.py: SUCCESS: Backup created successfully: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\backups\dev_backup_20250325_134223.sql
2025-03-25 13:42:24,322 - INFO - Backup created successfully: backups\dev_backup_20250325_134223.sql
2025-03-25 13:42:24,323 - INFO - PASS: Backup dev Database
2025-03-25 13:42:24,323 - INFO -
============================================================
2025-03-25 13:42:24,323 - INFO -                  BACKING UP TEST DATABASE
2025-03-25 13:42:24,323 - INFO - ============================================================
2025-03-25 13:42:24,324 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py create-backup --env test --output test_backup_20250325_134224.sql
2025-03-25 13:42:25,068 - INFO - manage_db.py: Creating backup of test database...
2025-03-25 13:42:25,069 - INFO - manage_db.py: SUCCESS: Backup created successfully: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\backups\test_backup_20250325_134224.sql
2025-03-25 13:42:25,069 - INFO - Backup created successfully: backups\test_backup_20250325_134224.sql
2025-03-25 13:42:25,070 - INFO - PASS: Backup test Database
2025-03-25 13:42:25,109 - INFO - PASS: DB Copy - Create Dev Test Table
2025-03-25 13:42:25,110 - INFO - PASS: DB Copy - Insert Dev Test Data
2025-03-25 13:42:25,111 - INFO - Dev test data verified: [(1, 'dev', 100)]
2025-03-25 13:42:25,111 - INFO - PASS: DB Copy - Verify Dev Test Data
2025-03-25 13:42:25,113 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py copy-db dev test
2025-03-25 13:42:26,901 - INFO - manage_db.py: Warning! This will copy database from dev to test. Are you sure? [y/N]: Starting database copy from dev to test...
2025-03-25 13:42:26,902 - INFO - manage_db.py: SUCCESS: Database copied successfully from dev to test
2025-03-25 13:42:26,902 - INFO - PASS: DB Copy - Copy Dev to Test
2025-03-25 13:42:26,937 - INFO - Test database data verified: [(1, 'dev', 100)]
2025-03-25 13:42:26,937 - INFO - PASS: DB Copy - Verify Test Data
2025-03-25 13:42:26,938 - INFO - PASS: DB Copy - Modify Test Data
2025-03-25 13:42:26,943 - INFO - PASS: DB Copy - Modify Dev Schema
2025-03-25 13:42:26,943 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py copy-db dev test --schema-only
2025-03-25 13:42:28,528 - INFO - manage_db.py: Warning! This will copy database from dev to test. Are you sure? [y/N]: Starting database copy from dev to test...
2025-03-25 13:42:28,528 - INFO - manage_db.py: Copy options: schema only
2025-03-25 13:42:28,529 - INFO - manage_db.py: SUCCESS: Database copied successfully from dev to test
2025-03-25 13:42:28,529 - INFO - PASS: DB Copy - Schema-Only Copy
2025-03-25 13:42:28,529 - INFO - Schema-only copy behavior verified
2025-03-25 13:42:28,529 - INFO - PASS: DB Copy - Verify Schema Update
2025-03-25 13:42:28,530 - INFO - Data preserved during schema copy
2025-03-25 13:42:28,531 - INFO - PASS: DB Copy - Verify Data Preserved
2025-03-25 13:42:28,532 - INFO - Cleaned up test table in dev database
2025-03-25 13:42:28,536 - INFO - Cleaned up test table in test database
2025-03-25 13:42:28,538 - INFO - Restoring databases to original state
2025-03-25 13:42:28,538 - INFO -
============================================================
2025-03-25 13:42:28,538 - INFO -                   RESTORING DEV DATABASE
2025-03-25 13:42:28,539 - INFO - ============================================================
2025-03-25 13:42:28,539 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py restore-backup backups\dev_backup_20250325_134223.sql
2025-03-25 13:42:28,539 - INFO - Updated .flask_env_type with 'dev'
2025-03-25 13:42:30,270 - INFO - manage_db.py: Using environment from centralized configuration: dev (development)
2025-03-25 13:42:30,270 - INFO - manage_db.py: Warning! This will restore the dev database from backups\dev_backup_20250325_134223.sql. Are you sure? [y/N]: Restoring dev database from backups\dev_backup_20250325_134223.sql...
2025-03-25 13:42:30,270 - INFO - manage_db.py: SUCCESS: Database restored successfully
2025-03-25 13:42:30,271 - INFO - Successfully restored dev database from backups\dev_backup_20250325_134223.sql
2025-03-25 13:42:30,271 - INFO - PASS: Restore dev Database
2025-03-25 13:42:30,271 - INFO -
============================================================
2025-03-25 13:42:30,271 - INFO -                  RESTORING TEST DATABASE
2025-03-25 13:42:30,272 - INFO - ============================================================
2025-03-25 13:42:30,272 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py restore-backup backups\test_backup_20250325_134224.sql
2025-03-25 13:42:30,272 - INFO - Updated .flask_env_type with 'test'
2025-03-25 13:42:31,867 - INFO - manage_db.py: Using environment from centralized configuration: test (testing)
2025-03-25 13:42:31,868 - INFO - manage_db.py: Warning! This will restore the test database from backups\test_backup_20250325_134224.sql. Are you sure? [y/N]: Restoring test database from backups\test_backup_20250325_134224.sql...
2025-03-25 13:42:31,869 - INFO - manage_db.py: SUCCESS: Database restored successfully
2025-03-25 13:42:31,869 - INFO - Successfully restored test database from backups\test_backup_20250325_134224.sql
2025-03-25 13:42:31,869 - INFO - PASS: Restore test Database
2025-03-25 13:42:31,870 - INFO -
============================================================
2025-03-25 13:42:31,870 - INFO -                 TESTING TRIGGER MANAGEMENT
2025-03-25 13:42:31,870 - INFO - ============================================================
2025-03-25 13:42:31,870 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_test
2025-03-25 13:42:31,903 - INFO - Database connection successful for test environment
2025-03-25 13:42:31,904 - INFO - 
============================================================
2025-03-25 13:42:31,904 - INFO -                  BACKING UP TEST DATABASE
2025-03-25 13:42:31,904 - INFO - ============================================================
2025-03-25 13:42:31,904 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py create-backup --env test --output test_backup_20250325_134231.sql
2025-03-25 13:42:32,751 - INFO - manage_db.py: Creating backup of test database...
2025-03-25 13:42:32,751 - INFO - manage_db.py: SUCCESS: Backup created successfully: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\backups\test_backup_20250325_134231.sql
2025-03-25 13:42:32,752 - INFO - Backup created successfully: backups\test_backup_20250325_134231.sql
2025-03-25 13:42:32,752 - INFO - PASS: Backup test Database
2025-03-25 13:42:32,791 - INFO - PASS: Triggers - Create Test Table
2025-03-25 13:42:32,792 - INFO - PASS: Triggers - Use/Create Trigger Function
2025-03-25 13:42:32,793 - INFO - PASS: Triggers - Create Trigger
2025-03-25 13:42:32,795 - INFO - PASS: Triggers - Insert Test Data
2025-03-25 13:42:32,795 - INFO - Timestamp was set correctly: 2025-03-25 13:42:32.785942
2025-03-25 13:42:32,796 - INFO - PASS: Triggers - Verify Created Timestamp
2025-03-25 13:42:32,796 - INFO - PASS: Triggers - Update Test Data
2025-03-25 13:42:32,796 - INFO - Updated timestamp was set correctly: 2025-03-25 08:12:32.785942
2025-03-25 13:42:32,797 - INFO - PASS: Triggers - Verify Updated Timestamp
2025-03-25 13:42:32,798 - INFO - Cleaned up test table and trigger function
2025-03-25 13:42:32,805 - INFO - Restoring test database to original state
2025-03-25 13:42:32,805 - INFO -
============================================================
2025-03-25 13:42:32,805 - INFO -                  RESTORING TEST DATABASE
2025-03-25 13:42:32,805 - INFO - ============================================================
2025-03-25 13:42:32,805 - INFO - Running command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py restore-backup backups\test_backup_20250325_134231.sql
2025-03-25 13:42:32,806 - INFO - Updated .flask_env_type with 'test'
2025-03-25 13:42:34,392 - INFO - manage_db.py: Using environment from centralized configuration: test (testing)
2025-03-25 13:42:34,393 - INFO - manage_db.py: Warning! This will restore the test database from backups\test_backup_20250325_134231.sql. Are you sure? [y/N]: Restoring test database from backups\test_backup_20250325_134231.sql...
2025-03-25 13:42:34,393 - INFO - manage_db.py: SUCCESS: Database restored successfully
2025-03-25 13:42:34,394 - INFO - Successfully restored test database from backups\test_backup_20250325_134231.sql
2025-03-25 13:42:34,394 - INFO - PASS: Restore test Database
2025-03-25 13:42:34,395 - INFO -
============================================================
2025-03-25 13:42:34,395 - INFO -               TESTING ENVIRONMENT SWITCHING
2025-03-25 13:42:34,396 - INFO - ============================================================
2025-03-25 13:42:34,396 - INFO - Original environment: test
2025-03-25 13:42:34,396 - INFO - Original FLASK_ENV in .env: test
2025-03-25 13:42:34,397 - INFO - Running status command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py switch-env --status
2025-03-25 13:42:35,008 - INFO - Environment status:
2025-03-25 13:42:35,009 - INFO -   Current environment: testing
2025-03-25 13:42:35,009 - INFO -   Short name: test
2025-03-25 13:42:35,010 - INFO -   Environment type file (.flask_env_type): test
2025-03-25 13:42:35,010 - INFO -   FLASK_ENV in .env file: test
2025-03-25 13:42:35,010 - INFO -   FLASK_ENV environment variable: test
2025-03-25 13:42:35,011 - INFO -   SKINSPIRE_ENV environment variable: Not set
2025-03-25 13:42:35,011 - INFO -
2025-03-25 13:42:35,011 - INFO -   Database URLs:
2025-03-25 13:42:35,011 - INFO -     development: postgresql://skinspire_admin:****@localhost:5432/skinspire_dev
2025-03-25 13:42:35,011 - INFO -     testing: postgresql://skinspire_admin:****@localhost:5432/skinspire_test
2025-03-25 13:42:35,011 - INFO -     production: postgresql://skinspire_admin:****@localhost:5432/skinspire_prod
2025-03-25 13:42:35,011 - INFO - PASS: Switch Env - Status Check
2025-03-25 13:42:35,011 - INFO - Running switch command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py switch-env test
2025-03-25 13:42:35,608 - INFO - Environment switch output:
2025-03-25 13:42:35,608 - INFO -   Environment switched to: testing
2025-03-25 13:42:35,608 - INFO -   Database URL: postgresql://skinspire_admin:****@localhost:5432/skinspire_test
2025-03-25 13:42:35,609 - INFO - PASS: Switch Env - Switch to Test
2025-03-25 13:42:35,609 - INFO - Environment type file updated to 'test'
2025-03-25 13:42:35,609 - INFO - PASS: Switch Env - Verify File Update
2025-03-25 13:42:35,610 - INFO - Running switch command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py switch-env dev
2025-03-25 13:42:36,215 - INFO - Environment switch output:
2025-03-25 13:42:36,215 - INFO -   Environment switched to: development
2025-03-25 13:42:36,216 - INFO -   Database URL: postgresql://skinspire_admin:****@localhost:5432/skinspire_test
2025-03-25 13:42:36,216 - INFO - PASS: Switch Env - Switch to Dev
2025-03-25 13:42:36,217 - INFO - Environment type file updated to 'dev'
2025-03-25 13:42:36,217 - INFO - PASS: Switch Env - Verify Second File Update
2025-03-25 13:42:36,218 - INFO - Restoring original FLASK_ENV in .env file: test
2025-03-25 13:42:36,218 - INFO - Environment switch tests completed successfully
2025-03-25 13:42:36,219 - INFO -
============================================================
2025-03-25 13:42:36,219 - INFO -                TESTING DATABASE INSPECTION
2025-03-25 13:42:36,219 - INFO - ============================================================
2025-03-25 13:42:36,219 - INFO - Testing connection to database: postgresql://skinspire_admin:***@localhost:5432/skinspire_test
2025-03-25 13:42:36,253 - INFO - Database connection successful for test environment
2025-03-25 13:42:36,295 - INFO - PASS: DB Inspect - Create Test Table
2025-03-25 13:42:36,301 - INFO - Running inspect command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py inspect-db test
2025-03-25 13:42:37,050 - INFO - Database inspection output:
2025-03-25 13:42:37,051 - INFO -   Connecting to database: postgresql://skinspire_admin:****@localhost:5432/skinspire_test
2025-03-25 13:42:37,051 - INFO -
2025-03-25 13:42:37,052 - INFO -   === CONNECTING TO DATABASE ===
2025-03-25 13:42:37,052 - INFO -
2025-03-25 13:42:37,052 - INFO -   === DATABASE OVERVIEW ===
2025-03-25 13:42:37,052 - INFO -   Found 2 user-defined schemas:
2025-03-25 13:42:37,053 - INFO -     - application: 0 tables
2025-03-25 13:42:37,053 - INFO -     - public: 13 tables
2025-03-25 13:42:37,053 - INFO -
2025-03-25 13:42:37,053 - INFO -   Database: skinspire_test
2025-03-25 13:42:37,053 - INFO -   Version: PostgreSQL 17.2 on x86_64-windows, compiled by msvc-19.42.34435, 64-bit       
2025-03-25 13:42:37,053 - INFO -   Size: 11 MB (11357331 bytes)
2025-03-25 13:42:37,054 - INFO -   Total tables: 13
2025-03-25 13:42:37,054 - INFO -   Total functions: 55
2025-03-25 13:42:37,054 - INFO -   Total triggers: 81
2025-03-25 13:42:37,054 - INFO - PASS: DB Inspect - General Overview
2025-03-25 13:42:37,054 - INFO - Running tables command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py inspect-db test --tables
2025-03-25 13:42:37,799 - INFO - PASS: DB Inspect - Tables Listing
2025-03-25 13:42:37,799 - INFO - Running table detail command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py inspect-db test --table _test_inspect_table
2025-03-25 13:42:38,523 - INFO - Table inspection output:
2025-03-25 13:42:38,523 - INFO -   Connecting to database: postgresql://skinspire_admin:****@localhost:5432/skinspire_test
2025-03-25 13:42:38,524 - INFO -
2025-03-25 13:42:38,524 - INFO -   === CONNECTING TO DATABASE ===
2025-03-25 13:42:38,525 - INFO -
2025-03-25 13:42:38,525 - INFO -   === TABLE DETAILS: public._test_inspect_table ===
2025-03-25 13:42:38,525 - INFO -
2025-03-25 13:42:38,525 - INFO -   Columns (6):
2025-03-25 13:42:38,526 - INFO -     id INTEGER NOT NULL DEFAULT nextval('"public"._test_inspect_table_id_seq'::regclass) 
2025-03-25 13:42:38,526 - INFO -     name VARCHAR(100) NOT NULL
2025-03-25 13:42:38,526 - INFO -     description TEXT NULL
2025-03-25 13:42:38,526 - INFO -     is_active BOOLEAN NULL DEFAULT true
2025-03-25 13:42:38,526 - INFO -     created_at TIMESTAMP NULL DEFAULT now()
2025-03-25 13:42:38,527 - INFO -     value NUMERIC(10, 2) NULL
2025-03-25 13:42:38,527 - INFO -
2025-03-25 13:42:38,527 - INFO -   Primary Key: id
2025-03-25 13:42:38,527 - INFO -
2025-03-25 13:42:38,527 - INFO -   Indexes (1):
2025-03-25 13:42:38,527 - INFO -     idx_test_inspect_name: (name)
2025-03-25 13:42:38,527 - INFO -
2025-03-25 13:42:38,527 - INFO -   Statistics:
2025-03-25 13:42:38,528 - INFO -     Row count: 2
2025-03-25 13:42:38,528 - INFO -     Total size: 48 kB
2025-03-25 13:42:38,528 - INFO -     Table size: 8192 bytes
2025-03-25 13:42:38,528 - INFO -     Index size: 32 kB
2025-03-25 13:42:38,528 - INFO - PASS: DB Inspect - Table Detail
2025-03-25 13:42:38,528 - INFO - PASS: DB Inspect - Index Information
2025-03-25 13:42:38,528 - INFO - Running functions command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py inspect-db test --functions
2025-03-25 13:42:39,222 - INFO - PASS: DB Inspect - Functions Listing
2025-03-25 13:42:39,223 - INFO - Running triggers command: C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env\Scripts\python.exe scripts/manage_db.py inspect-db test --triggers
2025-03-25 13:42:39,928 - INFO - PASS: DB Inspect - Triggers Listing
2025-03-25 13:42:39,932 - INFO - Cleaned up test table
2025-03-25 13:42:39,936 - INFO - Database inspection tests completed successfully

======== TEST SUMMARY ========
PASSED:  45
FAILED:  0
SKIPPED: 0
============================

2025-03-25 13:42:39,938 - INFO - Test results saved to db_test_results_20250325_134239.json
2025-03-25 13:42:39,938 - INFO - All tests passed or skipped.

(skinspire_v2_env) C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2>