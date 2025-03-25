#!/usr/bin/env python
# scripts/test_db_festuresdummy.py

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"db_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(sys.stdout)  # Print to console
    ]
)
logger = logging.getLogger("DB_TESTS")

# Print a starting message to confirm the script is running
print("Starting database test script...")

# Define test result tracking
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def add_pass(self):
        self.passed += 1
    
    def add_fail(self, test_name, error_msg):
        self.failed += 1
        self.failures.append((test_name, error_msg))
    
    def add_skip(self):
        self.skipped += 1
    
    def summary(self):
        return (f"\n======== TEST SUMMARY ========\n"
                f"PASSED:  {self.passed}\n"
                f"FAILED:  {self.failed}\n"
                f"SKIPPED: {self.skipped}\n"
                f"============================\n")
    
    def failures_summary(self):
        if not self.failures:
            return "No failures detected."
        
        result = "\n======= FAILURES DETAIL =======\n"
        for i, (test, error) in enumerate(self.failures, 1):
            result += f"{i}. {test}: {error}\n"
        result += "============================\n"
        return result

# Initialize test results
results = TestResults()

def read_env_file():
    """Read database URLs from .env file"""
    db_urls = {}
    
    # Try to read from .env file
    env_path = Path('.env')
    if env_path.exists():
        logger.info("Reading database URLs from .env file")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key in ('FLASK_ENV', 'DEV_DATABASE_URL', 'TEST_DATABASE_URL', 'PROD_DATABASE_URL'):
                            db_urls[key] = value
    
    # Set some default values if not found
    if 'DEV_DATABASE_URL' not in db_urls:
        db_urls['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
    if 'TEST_DATABASE_URL' not in db_urls:
        db_urls['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
    
    logger.info(f"Found database URLs:")
    for key in db_urls:
        if key.endswith('DATABASE_URL'):
            masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_urls[key])
            logger.info(f"  {key}: {masked_url}")
        else:
            logger.info(f"  {key}: {db_urls[key]}")
    
    return db_urls

def test_database_connection(db_url):
    """Test database connection using SQLAlchemy"""
    logger.info(f"Testing connection to database: {re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)}")
    
    try:
        # Try to import SQLAlchemy
        import sqlalchemy
        from sqlalchemy import create_engine, text
        
        # Create engine
        engine = create_engine(db_url)
        
        # Test connection with a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test_connection"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("Database connection successful")
                return True
            else:
                logger.error("Database connection failed - unexpected result")
                return False
    except ImportError:
        logger.error("SQLAlchemy not installed. Please install it with 'pip install sqlalchemy'")
        return False
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def test_configuration():
    """Test configuration and database connectivity"""
    print_section_header("TESTING CONFIGURATION")
    
    # Read database URLs from .env file
    db_urls = read_env_file()
    
    # Test dev database connection
    if 'DEV_DATABASE_URL' in db_urls:
        dev_connected = test_database_connection(db_urls['DEV_DATABASE_URL'])
        if dev_connected:
            results.add_pass()
        else:
            results.add_fail("Configuration - Dev Database Connection", "Failed to connect to dev database")
    else:
        logger.warning("DEV_DATABASE_URL not found")
        results.add_skip()
    
    # Test test database connection
    if 'TEST_DATABASE_URL' in db_urls:
        test_connected = test_database_connection(db_urls['TEST_DATABASE_URL'])
        if test_connected:
            results.add_pass()
        else:
            results.add_fail("Configuration - Test Database Connection", "Failed to connect to test database")
    else:
        logger.warning("TEST_DATABASE_URL not found")
        results.add_skip()

def print_section_header(title):
    """Print a section header to make test output more readable"""
    section_width = 60
    padding = (section_width - len(title) - 2) // 2
    logger.info("\n" + "=" * section_width)
    logger.info(" " * padding + title + " " * padding)
    logger.info("=" * section_width)

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Test database connectivity')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--config', action='store_true', help='Test configuration')
    
    args = parser.parse_args()
    
    # If no specific tests are selected, run all tests
    run_all = args.all or not args.config
    
    try:
        # Track start time
        start_time = time.time()
        
        logger.info(f"Starting database tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run selected tests
        if run_all or args.config:
            test_configuration()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Display test results
        logger.info(results.summary())
        
        if results.failures:
            logger.error(results.failures_summary())
        
        logger.info(f"Tests completed in {execution_time:.2f} seconds")
        
        return 0 if results.failed == 0 else 1
    
    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unhandled exception during tests: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())