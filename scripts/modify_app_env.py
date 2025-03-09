#!/usr/bin/env python
# scripts/modify_app_env.py
# Quick tool to temporarily modify the app's environment
# Usage: python scripts/modify_app_env.py test

import os
import sys
from pathlib import Path

def create_env_file(env_type='test'):
    """Create a temporary FLASK_ENV_TYPE file to signal which database to use"""
    env_type = env_type.lower()
    
    if env_type not in ['dev', 'test', 'prod']:
        print(f"Invalid environment type: {env_type}")
        print("Please specify 'dev', 'test', or 'prod'")
        return False
    
    # Create the env type file
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.flask_env_type'
    
    with open(env_file, 'w') as f:
        f.write(env_type)
    
    print(f"✓ Set Flask environment type to '{env_type}'")
    print(f"  Database scripts will now use the {env_type.upper()} database")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/modify_app_env.py [dev|test|prod]")
        sys.exit(1)
    
    env_type = sys.argv[1]
    if create_env_file(env_type):
        print(f"Flask environment set to: {env_type}")
    else:
        sys.exit(1)