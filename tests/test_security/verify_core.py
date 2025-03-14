#!/usr/bin/env python
# verify_core.py - Enhanced system verification script
# python tests/test_security/verify_core.py
# python tests/test_security/verify_core.py --unit-test

import os
import sys
import logging
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemVerifier:
    """Runs system verification tests and tracks results"""
    
    def __init__(self, integration_mode=True):
        self.status_file = Path("verification_status.json")
        self.results = {
            "last_run": datetime.now().isoformat(),
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
        
        # Set integration mode for testing
        self.integration_mode = integration_mode
        
    def run_pytest(self, test_path: str) -> Dict:
        """Run pytest on specified test module and capture results"""
        logger.info(f"Running tests: {test_path}")
        
        result = {
            "command": f"pytest {test_path} -v",
            "exit_code": None,
            "output": "",
            "error": "",
            "passed": 0,
            "failed": 0,
            "skipped": 0
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
            
            # For the problematic test, run with more specific focus
            if test_path == "tests/test_security/test_auth_system.py" and self.integration_mode:
                # Run only the specific failing test with very verbose output
                test_cmd = [self.python_path, "-m", "pytest", 
                        "tests/test_security/test_auth_system.py::TestAuthentication::test_account_lockout", 
                        "-vv"]
                
                # Execute the specific test first to get detailed output
                detail_process = subprocess.Popen(
                    test_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                
                detailed_stdout, detailed_stderr = detail_process.communicate()
                
                # Log detailed output for debugging
                logger.info("Detailed output for account_lockout test:")
                logger.info(detailed_stdout)
                if detailed_stderr:
                    logger.error("Detailed errors:")
                    logger.error(detailed_stderr)
            
            # Run all tests as normal
            process = subprocess.Popen(
                [self.python_path, "-m", "pytest", test_path, "-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env  # Pass environment variables
            )
            
            # Capture output
            stdout, stderr = process.communicate()
            result["exit_code"] = process.returncode
            result["output"] = stdout
            result["error"] = stderr
            
            # Parse basic test summary from output
            result.update(self._parse_test_summary(stdout))
            
            # Display detailed error information for failing components
            if result["exit_code"] != 0:
                if "test_account_lockout" in stdout:
                    logger.error("Test account_lockout details:")
                    
                    # Extract just the relevant part of the output
                    import re
                    lockout_test_output = re.search(r"test_account_lockout.*?(?=\n=+)", 
                                                stdout, re.DOTALL)
                    if lockout_test_output:
                        logger.error(lockout_test_output.group(0))
                        
                # Show the test summary 
                error_summary = stdout.split("short test summary info")[1].strip() if "short test summary info" in stdout else "No summary available"
                logger.error(f"Error summary: {error_summary}")
                
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            result["exit_code"] = 1
            result["error"] = str(e)
            
        return result
    
    def _parse_test_summary(self, output: str) -> Dict:
        """Extract basic test statistics from pytest output"""
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

    def verify_setup(self) -> Dict:
        """Verify test environment setup"""
        logger.info("Verifying environment setup...")
        results = self.run_pytest("tests/test_security/test_setup_verification.py")
        
        self.results["components"]["setup_verification"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Environment setup verification passed")
        else:
            logger.error("❌ Environment setup verification failed")
            
        return results

    def verify_database_setup(self) -> Dict:
        """Verify database setup and schema"""
        logger.info("Verifying database setup...")
        results = self.run_pytest("tests/test_db_setup.py")
        
        self.results["components"]["database"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Database verification passed")
        else:
            logger.error("❌ Database verification failed")
            
        return results

    def verify_encryption(self) -> Dict:
        """Verify encryption functionality"""
        logger.info("Verifying encryption functionality...")
        results = self.run_pytest("tests/test_security/test_encryption.py")
        
        self.results["components"]["encryption"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Encryption verification passed")
        else:
            logger.error("❌ Encryption verification failed")
            
        return results

    def verify_authentication(self) -> Dict:
        """Verify authentication functionality"""
        logger.info("Verifying authentication functionality...")
        results = self.run_pytest("tests/test_security/test_authentication.py")
        
        self.results["components"]["authentication"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Authentication verification passed")
        else:
            logger.error("❌ Authentication verification failed")
            
        return results

    def verify_user_management(self) -> Dict:
        """Verify user management functionality"""
        logger.info("Verifying user management...")
        results = self.run_pytest("tests/test_security/test_user_management.py")
        
        self.results["components"]["user_management"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ User management verification passed")
        else:
            logger.error("❌ User management verification failed")
            
        return results
    
    def verify_authorization(self) -> Dict:
        """Verify authorization/RBAC functionality"""
        logger.info("Verifying authorization...")
        results = self.run_pytest("tests/test_security/test_authorization.py")
        
        self.results["components"]["authorization"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Authorization verification passed")
        else:
            logger.error("❌ Authorization verification failed")
            
        return results

    def verify_auth_views(self) -> Dict:
        """Verify frontend authentication views"""
        logger.info("Verifying frontend authentication views...")
        results = self.run_pytest("tests/test_security/test_auth_views.py")
        
        self.results["components"]["auth_views"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Authentication views verification passed")
        else:
            logger.error("❌ Authentication views verification failed")
            
        return results
    
    def verify_auth_end_to_end(self) -> Dict:
        """Verify end-to-end authentication flow"""
        logger.info("Verifying end-to-end authentication flow...")
        results = self.run_pytest("tests/test_security/test_auth_end_to_end.py")
        
        self.results["components"]["auth_end_to_end"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ End-to-end authentication verification passed")
        else:
            logger.error("❌ End-to-end authentication verification failed")
            logger.error(f"Error details: {results['error']}")
            
        return results
    
    def verify_auth_ui(self) -> Dict:
        """Verify authentication UI components"""
        logger.info("Verifying authentication UI components...")
        results = self.run_pytest("tests/test_security/test_auth_ui.py")
        
        self.results["components"]["auth_ui"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Authentication UI verification passed")
        else:
            logger.error("❌ Authentication UI verification failed")
            
        return results
            
    def verify_auth_flow(self) -> Dict:
        """Verify authentication flow"""
        logger.info("Verifying authentication flow...")
        results = self.run_pytest("tests/test_security/test_auth_flow.py")
        
        self.results["components"]["auth_flow"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Authentication flow verification passed")
        else:
            logger.error("❌ Authentication flow verification failed")
            
        return results
    
    def verify_auth_system(self) -> Dict:
        """Verify complete authentication system"""
        logger.info("Verifying complete authentication system...")
        results = self.run_pytest("tests/test_security/test_auth_system.py")
        
        self.results["components"]["auth_system"] = {
            "status": "PASS" if results["exit_code"] == 0 else "FAIL",
            "details": results
        }
        
        if results["exit_code"] == 0:
            logger.info("✅ Complete authentication system verification passed")
        else:
            logger.error("❌ Complete authentication system verification failed")
            
        return results

    def verify_all(self):
        """Run all verification checks"""
        logger.info("Starting core system verification...")
        logger.info(f"Integration mode: {'ENABLED' if self.integration_mode else 'DISABLED'}")
        
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
        
        # Save results
        self.save_results()
        self.print_summary()
        
        # Return overall status code
        return self.results["summary"]["failed"] == 0
    
    def save_results(self):
        """Save verification results"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Results saved to {self.status_file}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
    
    def print_summary(self):
        """Print verification summary"""
        summary = self.results["summary"]
        
        print("\n============= VERIFICATION SUMMARY =============")
        print(f"Run Time: {self.results['last_run']}")
        print(f"Integration Mode: {'ENABLED' if self.integration_mode else 'DISABLED'}")
        print(f"Total Components: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        
        print("\nComponent Status:")
        for component, result in self.results["components"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            component_name = component.replace("_", " ").title()
            passed = result["details"]["passed"]
            failed = result["details"]["failed"]
            skipped = result["details"].get("skipped", 0)
            print(f"  {status_icon} {component_name}: {result['status']} ({passed} passed, {failed} failed, {skipped} skipped)")
        
        if summary["failed"] > 0:
            print("\nFailed Components:")
            for component, result in self.results["components"].items():
                if result["status"] == "FAIL":
                    print(f"  - {component.replace('_', ' ').title()}")
                    for test in result["details"].get("failed_tests", []):
                        print(f"    * {test}")
        
        print("=================================================")

def main():
    """Main entry point"""
    # Check for command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Run system verification tests')
    parser.add_argument('--unit-test', action='store_true', help='Run in unit test mode with mocked dependencies')
    args = parser.parse_args()
    
    # Default to integration test mode, but allow override from command line
    integration_mode = not args.unit_test
    
    verifier = SystemVerifier(integration_mode=integration_mode)
    success = verifier.verify_all()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()