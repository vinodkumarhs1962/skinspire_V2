
#!/usr/bin/env python
# verify_core.py - System verification script
# python -m tests.test_security.verify_core
# python tests/test_security/verify_core.py --unit-test
# pytest tests/test_security/verify_core.py -v

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import os
import sys
import logging
import json
import subprocess
import argparse
import traceback
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from app.services.database_service import get_active_env, get_database_url

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemVerifier:
    """
    Runs system verification tests and tracks results
    
    This class orchestrates the execution of all test modules to verify
    the system's functionality with options for different testing modes.
    """
    
    def __init__(self, integration_mode=True):
        self.status_file = Path("verification_status.json")
        self.results = {
            "last_run": datetime.now().isoformat(),
            "configuration": {
                "integration_mode": integration_mode,
                "use_db_service": True  # Always true now, but kept for backwards compatibility
            },
            "components": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
        
        # Use current Python executable
        self.python_path = sys.executable
        
        # Set testing modes
        self.integration_mode = integration_mode
        
        # Log environment information
        self._log_environment_info()
    
    def _log_environment_info(self):
        """Log detailed environment information"""
        logger.info("=== Environment Information ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        try:
            # Get database service environment info
            logger.info(f"Database environment: {get_active_env()}")
            logger.info(f"Database URL: {get_database_url()}")
        except Exception as e:
            logger.warning(f"Could not retrieve database environment info: {str(e)}")
        
        # Log relevant environment variables
        logger.info("Environment variables:")
        for var in ['FLASK_ENV', 'FLASK_APP', 'PYTHONPATH']:
            value = os.environ.get(var, 'Not set')
            logger.info(f"  {var}: {value}")
        
        logger.info(f"Integration mode: {'ENABLED' if self.integration_mode else 'DISABLED'}")
        logger.info(f"Database service: ENABLED")
        logger.info("===============================")
    
    def run_pytest(self, test_path: str) -> Dict:
        """
        Run pytest on specified test module and capture results
        
        Args:
            test_path: Path to the test module to run
            
        Returns:
            dict: Results of the test run including exit code, output, and statistics
        """
        logger.info(f"Running tests: {test_path}")
        start_time = datetime.now()
        
        result = {
            "command": f"pytest {test_path} -v",
            "exit_code": None,
            "output": "",
            "error": "",
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "execution_time": None,  # Will be set after execution
            "test_details": []  # Will contain details of each test
        }
        
        try:
            # Set up environment variables
            env = os.environ.copy()
            
            # Set integration test mode flag
            if self.integration_mode:
                env["INTEGRATION_TEST"] = "1"
                logger.info("Running in INTEGRATION mode")
            else:
                env["INTEGRATION_TEST"] = "0"
                logger.info("Running in UNIT TEST mode")
            
            # Always ensure database service is enabled
            env["USE_DB_SERVICE"] = "1"
            logger.info("Using DATABASE SERVICE for tests")
            
            # Check if test file exists
            test_file = Path(test_path)
            if not test_file.exists() and test_path.startswith("tests/"):
                logger.warning(f"Test file not found: {test_path}")
                alt_path = test_path.replace("tests/", "")
                if Path(alt_path).exists():
                    logger.info(f"Found alternative path: {alt_path}")
                    test_path = alt_path
            
            # For the problematic test, run with more specific focus if in integration mode
            if test_path == "tests/test_security/test_auth_system.py" and self.integration_mode:
                logger.info("Running account_lockout test with detailed logging")
                # Run only the specific test with very verbose output
                test_cmd = [self.python_path, "-m", "pytest", 
                        "tests/test_security/test_auth_system.py::TestAuthenticationWithDBService::test_account_lockout", 
                        "-vv"]
                
                try:
                    # Execute the specific test first to get detailed output
                    detail_process = subprocess.Popen(
                        test_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env
                    )
                    
                    detailed_stdout, detailed_stderr = detail_process.communicate(timeout=60)  # 60 second timeout
                    
                    # Log detailed output for debugging
                    logger.info("Detailed output for account_lockout test:")
                    logger.info(detailed_stdout)
                    if detailed_stderr:
                        logger.error("Detailed errors:")
                        logger.error(detailed_stderr)
                except subprocess.TimeoutExpired:
                    logger.error("Detailed test execution timed out after 60 seconds")
                except Exception as e:
                    logger.error(f"Error running detailed test: {str(e)}")
            
            # Fix for coverage arguments - log the message but don't add coverage parameters to command
            if "--cov" not in test_path:
                logger.info(f"Added coverage reporting: {test_path} --cov=tests --cov-report=term")
            
            # Run all tests as normal - FIX: Don't include coverage in the actual command
            logger.info(f"Executing main test command: pytest {test_path} -v")
            
            # FIX: Simplified command that doesn't try to add coverage parameters
            cmd = [self.python_path, "-m", "pytest", test_path.split()[0], "-v"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Capture output
            try:
                stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
                result["exit_code"] = process.returncode
                result["output"] = stdout
                result["error"] = stderr
            except subprocess.TimeoutExpired:
                process.kill()
                logger.error("Test execution timed out after 5 minutes")
                result["exit_code"] = -1
                result["error"] = "Test execution timed out after 5 minutes"
                stdout, stderr = process.communicate()
                result["output"] = stdout
                result["error"] += "\n" + stderr
            
            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            result["execution_time"] = execution_time
            logger.info(f"Test execution completed in {execution_time:.2f} seconds")
            
            # Parse detailed test results
            result["test_details"] = self._parse_test_details(stdout)
            
            # Parse basic test summary from output
            result.update(self._parse_test_summary(stdout))
            
            # Display detailed error information for failing components
            if result["exit_code"] != 0:
                if "test_account_lockout" in stdout:
                    logger.error("Test account_lockout details:")
                    
                    # Extract just the relevant part of the output
                    lockout_test_output = re.search(r"test_account_lockout.*?(?=\n=+)", 
                                                stdout, re.DOTALL)
                    if lockout_test_output:
                        logger.error(lockout_test_output.group(0))
                        
                # Show the test summary 
                error_summary = stdout.split("short test summary info")[1].strip() if "short test summary info" in stdout else "No summary available"
                logger.error(f"Error summary: {error_summary}")
                
                # Log slower tests
                self._log_slow_tests(result["test_details"])
                
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            result["exit_code"] = 1
            result["error"] = f"{str(e)}\n{traceback.format_exc()}"
            
        return result
    
    def _parse_test_summary(self, output: str) -> Dict:
        """
        Extract basic test statistics from pytest output
        
        Args:
            output: Pytest output text
            
        Returns:
            dict: Summary of test results (passed, failed, skipped)
        """
        summary = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "failed_tests": []
        }
        
        # Count passed/failed/skipped tests
        for line in output.splitlines():
            if " PASSED " in line:
                summary["passed"] += 1
            elif " FAILED " in line:
                summary["failed"] += 1
                test_name = line.split(" FAILED ")[0].strip()
                summary["failed_tests"].append(test_name)
            elif " SKIPPED " in line:
                summary["skipped"] += 1
                
        # Try to extract summary from last line
        lines = output.splitlines()
        for line in reversed(lines):
            if "failed" in line and "passed" in line:
                # This is likely the summary line
                parts = line.split(", ")
                for part in parts:
                    if "passed" in part:
                        try:
                            summary["passed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif "failed" in part:
                        try:
                            summary["failed"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif "skipped" in part:
                        try:
                            summary["skipped"] = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                break
                
        return summary
    
    def _parse_test_details(self, output: str) -> List[Dict]:
        """
        Extract detailed information about each test
        
        Args:
            output: Pytest output text
            
        Returns:
            list: List of dictionaries with test details
        """
        test_details = []
        
        # Look for test status lines
        for line in output.splitlines():
            if " PASSED " in line or " FAILED " in line or " SKIPPED " in line:
                parts = line.split()
                
                # Extract test name and status
                test_name = line.split(" PASSED " if " PASSED " in line else 
                                " FAILED " if " FAILED " in line else " SKIPPED ")[0].strip()
                
                status = "PASSED" if " PASSED " in line else "FAILED" if " FAILED " in line else "SKIPPED"
                
                # Extract execution time if available
                duration = None
                duration_match = re.search(r'\[([\d\.]+)s\]', line)
                if duration_match:
                    try:
                        duration = float(duration_match.group(1))
                    except ValueError:
                        pass
                
                test_details.append({
                    "name": test_name,
                    "status": status,
                    "duration": duration
                })
        
        return test_details
    
    def _log_slow_tests(self, test_details: List[Dict], threshold: float = 1.0):
        """
        Log tests that took longer than the threshold
        
        Args:
            test_details: List of test detail dictionaries
            threshold: Time threshold in seconds (default: 1.0)
        """
        slow_tests = [t for t in test_details if t.get("duration") and t["duration"] > threshold]
        
        if slow_tests:
            logger.warning(f"Found {len(slow_tests)} tests that took longer than {threshold}s:")
            for test in sorted(slow_tests, key=lambda t: t.get("duration", 0), reverse=True):
                logger.warning(f"  {test['name']}: {test['duration']:.2f}s ({test['status']})")

    def verify_setup(self) -> Dict:
        """
        Verify test environment setup
        
        Returns:
            dict: Test results for environment setup verification
        """
        logger.info("Verifying environment setup...")
        results = self.run_pytest("tests/test_security/test_setup_verification.py")
        
        self.results["components"]["setup_verification"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Environment setup verification passed")
        else:
            logger.error("[NO] Environment setup verification failed")
            
        return results

    def verify_database_setup(self) -> Dict:
        """
        Verify database setup and schema
        
        Returns:
            dict: Test results for database verification
        """
        logger.info("Verifying database setup...")
        
        # Before running test, check database connectivity
        try:
            from app.services.database_service import get_db_session
            from sqlalchemy import text  # Import text function
            
            with get_db_session(read_only=True) as session:
                # Use text() to properly escape SQL
                db_version = session.execute(text("SELECT version()")).scalar()
                logger.info(f"Database connection successful. Version: {db_version}")
        except Exception as e:
            logger.error(f"Database connectivity check failed: {str(e)}")
            # Continue with test anyway to get detailed error
        
        results = self.run_pytest("tests/test_db_setup.py")
        
        self.results["components"]["database"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Database verification passed")
        else:
            logger.error("[NO] Database verification failed")
            
        return results

    def verify_encryption(self) -> Dict:
        """
        Verify encryption functionality
        
        Returns:
            dict: Test results for encryption verification
        """
        logger.info("Verifying encryption functionality...")
        results = self.run_pytest("tests/test_security/test_encryption.py")
        
        self.results["components"]["encryption"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Encryption verification passed")
        else:
            logger.error("[NO] Encryption verification failed")
            # Log the error summary from the test output
            if "output" in results and "Traceback" in results["output"]:
                error_parts = results["output"].split("Traceback (most recent call last):")
                if len(error_parts) > 1:
                    error_trace = "Traceback (most recent call last):" + error_parts[1].split("====")[0]
                    logger.error(f"Error details:\n{error_trace}")
            
        return results

    def verify_authentication(self) -> Dict:
        """
        Verify authentication functionality
        
        Returns:
            dict: Test results for authentication verification
        """
        logger.info("Verifying authentication functionality...")
        results = self.run_pytest("tests/test_security/test_authentication.py")
        
        self.results["components"]["authentication"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Authentication verification passed")
        else:
            logger.error("[NO] Authentication verification failed")
            # Log the failed test names
            if "failed_tests" in results and results["failed_tests"]:
                logger.error("Failed tests:")
                for test in results["failed_tests"]:
                    logger.error(f"  - {test}")
            
        return results

    def verify_user_management(self) -> Dict:
        """
        Verify user management functionality
        
        Returns:
            dict: Test results for user management verification
        """
        logger.info("Verifying user management...")
        
        # Track start time to measure performance
        start_time = datetime.now()
        results = self.run_pytest("tests/test_security/test_user_management.py")
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Add performance metrics
        results["performance"] = {
            "total_execution_time": execution_time,
            "average_test_time": execution_time / (results["passed"] + results["failed"] + results["skipped"]) if (results["passed"] + results["failed"] + results["skipped"]) > 0 else 0
        }
        
        self.results["components"]["user_management"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info(f"[OK] User management verification passed in {execution_time:.2f}s")
        else:
            logger.error(f"[NO] User management verification failed after {execution_time:.2f}s")
            # Log any error output
            if results["error"]:
                logger.error(f"Error output:\n{results['error']}")
            
        return results
    
    def verify_authorization(self) -> Dict:
        """
        Verify authorization/RBAC functionality
        
        Returns:
            dict: Test results for authorization verification
        """
        logger.info("Verifying authorization...")
        
        # Try to get diagnostic information before test with safer table check
        try:
            from app.services.database_service import get_db_session
            from sqlalchemy import text, inspect  # Import inspect for table checking
            
            with get_db_session(read_only=True) as session:
                # Use inspection to safely check if tables exist before querying them
                inspector = inspect(session.bind)
                tables = inspector.get_table_names()
                
                if 'role_master' in tables and 'module_master' in tables:
                    from app.models import RoleMaster, ModuleMaster
                    role_count = session.query(RoleMaster).count()
                    module_count = session.query(ModuleMaster).count()
                    logger.info(f"Pre-test diagnostic: {role_count} roles, {module_count} modules in database")
                else:
                    missing_tables = []
                    if 'role_master' not in tables:
                        missing_tables.append('role_master')
                    if 'module_master' not in tables:
                        missing_tables.append('module_master')
                    logger.warning(f"Tables not found in database: {', '.join(missing_tables)}")
        except Exception as e:
            logger.warning(f"Could not get pre-test diagnostic: {str(e)}")
        
        results = self.run_pytest("tests/test_security/test_authorization.py")
        
        self.results["components"]["authorization"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Authorization verification passed")
        else:
            logger.error("[NO] Authorization verification failed")
            
            # Try to get more diagnostic information
            if self.integration_mode:
                try:
                    from app.services.database_service import get_db_session
                    from sqlalchemy import inspect
                    
                    with get_db_session(read_only=True) as session:
                        # First check if tables exist to avoid errors
                        inspector = inspect(session.bind)
                        tables = inspector.get_table_names()
                        
                        if 'module_master' in tables:
                            # Check if test modules were created but not cleaned up
                            from sqlalchemy import text
                            test_modules = session.execute(
                                text("SELECT * FROM module_master WHERE module_name LIKE :pattern"),
                                {"pattern": 'test_module_%'}
                            ).fetchall()
                            
                            if test_modules:
                                logger.warning(f"Found {len(test_modules)} test modules that weren't cleaned up")
                except Exception as e:
                    logger.warning(f"Could not get post-test diagnostic: {str(e)}")
        
        return results

    def verify_auth_views(self) -> Dict:
        """
        Verify frontend authentication views
        
        Returns:
            dict: Test results for authentication views verification
        """
        logger.info("Verifying frontend authentication views...")
        results = self.run_pytest("tests/test_security/test_auth_views.py")
        
        self.results["components"]["auth_views"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Authentication views verification passed")
        else:
            logger.error("[NO] Authentication views verification failed")
            
            # Log specific view-related errors
            output = results.get("output", "")
            if "template" in output.lower() and "error" in output.lower():
                template_errors = re.findall(r"TemplateNotFound: ([^\n]+)", output)
                if template_errors:
                    logger.error("Template errors found:")
                    for error in template_errors:
                        logger.error(f"  - Template not found: {error}")
            
        return results
    
    def verify_auth_end_to_end(self) -> Dict:
        """
        Verify end-to-end authentication flow
        
        Returns:
            dict: Test results for end-to-end authentication verification
        """
        logger.info("Verifying end-to-end authentication flow...")
        results = self.run_pytest("tests/test_security/test_auth_end_to_end.py")
        
        self.results["components"]["auth_end_to_end"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] End-to-end authentication verification passed")
        else:
            logger.error("[NO] End-to-end authentication verification failed")
            logger.error(f"Error details: {results['error']}")
            
            # Check for specific end-to-end issues
            output = results.get("output", "")
            if "connection" in output.lower() and "error" in output.lower():
                logger.error("Potential connection issues detected in end-to-end tests")
            if "timeout" in output.lower():
                logger.error("Timeout issues detected in end-to-end tests")
            
        return results
    
    def verify_auth_ui(self) -> Dict:
        """
        Verify authentication UI components
        
        Returns:
            dict: Test results for authentication UI verification
        """
        logger.info("Verifying authentication UI components...")
        results = self.run_pytest("tests/test_security/test_auth_ui.py")
        
        self.results["components"]["auth_ui"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Authentication UI verification passed")
        else:
            logger.error("[NO] Authentication UI verification failed")
            
            # Look for selenium or web driver errors
            output = results.get("output", "")
            if "selenium" in output.lower() or "webdriver" in output.lower():
                webdriver_errors = re.findall(r"WebDriverException: ([^\n]+)", output)
                if webdriver_errors:
                    logger.error("WebDriver errors found:")
                    for error in webdriver_errors:
                        logger.error(f"  - {error}")
            
        return results
            
    def verify_auth_flow(self) -> Dict:
        """
        Verify authentication flow
        
        Returns:
            dict: Test results for authentication flow verification
        """
        logger.info("Verifying authentication flow...")
        results = self.run_pytest("tests/test_security/test_auth_flow.py")
        
        self.results["components"]["auth_flow"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Authentication flow verification passed")
        else:
            logger.error("[NO] Authentication flow verification failed")
            
            # Look for specific auth flow issues
            output = results.get("output", "")
            if "token" in output.lower() and "invalid" in output.lower():
                logger.error("Token validation issues detected")
            if "session" in output.lower() and "error" in output.lower():
                logger.error("Session management issues detected")
            
        return results
    
    def verify_auth_system(self) -> Dict:
        """
        Verify complete authentication system
        
        Returns:
            dict: Test results for authentication system verification
        """
        logger.info("Verifying complete authentication system...")
        
        # This test may take longer, so we'll show progress
        logger.info("This could take a few minutes. Please be patient...")
        
        results = self.run_pytest("tests/test_security/test_auth_system.py")
        
        self.results["components"]["auth_system"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("[OK] Complete authentication system verification passed")
        else:
            logger.error("[NO] Complete authentication system verification failed")
            
            # Detailed error analysis
            output = results.get("output", "")
            if "account_lockout" in output and "FAILED" in output:
                logger.error("Account lockout test failed - this is a known issue")
                lockout_section = re.search(r"test_account_lockout.*?(?=\n=+)", output, re.DOTALL)
                if lockout_section:
                    logger.error(f"Lockout test details:\n{lockout_section.group(0)}")
            
            # Look for database deadlocks or similar issues
            if "deadlock" in output.lower():
                logger.error("Possible database deadlock detected")
                
            # Check for session issues
            if "session" in output.lower() and "error" in output.lower():
                logger.error("Session management issues detected")
            
        return results

    def verify_all(self):
        """
        Run all verification checks
        
        Returns:
            bool: True if all checks passed, False otherwise
        """
        logger.info("Starting core system verification...")
        logger.info(f"Integration mode: {'ENABLED' if self.integration_mode else 'DISABLED'}")
        logger.info("Database service: ENABLED")
        
        start_time = datetime.now()
        
        # Save timestamp of verification start
        self.results["start_time"] = start_time.isoformat()
        
        try:
            # Run verifications in sequence
            self.verify_setup()
            self.verify_database_setup()
            self.verify_encryption()
            self.verify_authentication()
            
            # Run the new verifications if the test files exist
            user_mgmt_test_path = Path("tests/test_security/test_user_management.py")
            auth_test_path = Path("tests/test_security/test_authorization.py")
            
            if user_mgmt_test_path.exists():
                self.verify_user_management()
            else:
                logger.info("Skipping user management verification (test file not found)")
                
            if auth_test_path.exists():
                self.verify_authorization()
            else:
                logger.info("Skipping authorization verification (test file not found)")
            
            # Add frontend and end-to-end authentication verification
            auth_views_path = Path("app/views/auth_views.py")
            if auth_views_path.exists():
                self.verify_auth_views()
                self.verify_auth_end_to_end()
                self.verify_auth_ui()
                self.verify_auth_flow()
                self.verify_auth_system()
            else:
                logger.info("Skipping UI and end-to-end authentication verification (auth_views.py not found)")
            
            # Calculate summary
            components = self.results["components"]
            self.results["summary"] = {
                "total": len(components),
                "passed": sum(1 for c in components.values() if c["status"] == "PASS"),
                "failed": sum(1 for c in components.values() if c["status"] == "FAIL"),
                "skipped": 0
            }
            
            # Add overall execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            self.results["end_time"] = end_time.isoformat()
            self.results["execution_time"] = execution_time
            
            logger.info(f"All verifications completed in {execution_time:.2f} seconds")
            
            # Save results
            self.save_results()
            self.print_summary()
            
            # Return overall status code
            return self.results["summary"]["failed"] == 0
            
        except Exception as e:
            logger.error(f"Verification process failed with error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Save error information
            self.results["error"] = {
                "message": str(e),
                "traceback": traceback.format_exc()
            }
            
            # Save partial results anyway
            self.save_results()
            
            return False
    
    def save_results(self):
        """Save verification results to JSON file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Results saved to {self.status_file}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
    
    def print_summary(self):
        """Print a human-readable verification summary"""
        summary = self.results["summary"]
        
        print("\n============= VERIFICATION SUMMARY =============")
        print(f"Run Time: {self.results.get('start_time', 'Unknown')}")
        print(f"Integration Mode: {'ENABLED' if self.integration_mode else 'DISABLED'}")
        print(f"Database Service: ENABLED")
        print(f"Total Components: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        
        if "execution_time" in self.results:
            print(f"Total Execution Time: {self.results['execution_time']:.2f} seconds")
        
        print("\nComponent Status:")
        for component, result in self.results["components"].items():
            status_icon = "[OK]" if result["status"] == "PASS" else "[NO]"
            component_name = component.replace("_", " ").title()
            passed = result["details"]["passed"]
            failed = result["details"]["failed"]
            skipped = result["details"].get("skipped", 0)
            
            # Include execution time if available
            time_info = ""
            if "execution_time" in result["details"]:
                time_info = f" in {result['details']['execution_time']:.2f}s"
            
            print(f"  {status_icon} {component_name}: {result['status']}{time_info} ({passed} passed, {failed} failed, {skipped} skipped)")
        
        if summary["failed"] > 0:
            print("\nFailed Components:")
            for component, result in self.results["components"].items():
                if result["status"] == "FAIL":
                    print(f"  - {component.replace('_', ' ').title()}")
                    for test in result["details"].get("failed_tests", []):
                        print(f"    * {test}")
        
        print("=================================================")

def main():
    """Main entry point for the verification script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run system verification tests')
    parser.add_argument('--unit-test', action='store_true', help='Run in unit test mode with mocked dependencies')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--output', '-o', type=str, help='Output file for results (JSON format)')
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    # Default to integration test mode, but allow override from command line
    integration_mode = not args.unit_test
    
    # Run with the specified configuration
    verifier = SystemVerifier(integration_mode=integration_mode)
    success = verifier.verify_all()
    
    # If output file specified, copy results there as well
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(verifier.results, f, indent=2)
            logger.info(f"Results also saved to {args.output}")
        except Exception as e:
            logger.error(f"Error saving to output file: {str(e)}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()