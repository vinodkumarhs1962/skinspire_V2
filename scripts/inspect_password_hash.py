#!/usr/bin/env python
# scripts/inspect_password_hash.py

import os
import sys
import random
import uuid
from sqlalchemy import text

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Create a test user with a random ID
    user_id = f"hashtest{random.randint(1000, 9999)}"
    
    # Get a hospital ID
    hospital_id = db.session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).scalar()
    
    # Create a user
    user = User(
        user_id=user_id,
        hospital_id=hospital_id,
        entity_type="staff",
        entity_id=str(uuid.uuid4()),
        is_active=True,
        password_hash="test_password123"
    )
    
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    
    # Examine the generated hash
    print("\n======== Password Hash Inspection ========")
    print(f"Hash: {user.password_hash}")
    print(f"Hash length: {len(user.password_hash)}")
    print(f"Hash encoding: {user.password_hash.encode()}")
    print(f"Hash starts with $2: {user.password_hash.startswith('$2')}")
    
    # Try different verification methods
    from werkzeug.security import check_password_hash
    werkzeug_verify = check_password_hash(user.password_hash, "test_password123")
    print(f"Werkzeug verification: {werkzeug_verify}")
    
    # Try manual pgcrypto verification
    try:
        result = db.session.execute(text(
            "SELECT crypt(:password, :hash) = :hash"
        ), {"password": "test_password123", "hash": user.password_hash}).scalar()
        print(f"pgcrypto verification: {result}")
    except Exception as e:
        print(f"pgcrypto error: {e}")
    
    # Try manual bcrypt verification if available
    try:
        import bcrypt
        encoded_hash = user.password_hash.encode('utf-8')
        encoded_pwd = "test_password123".encode('utf-8')
        bcrypt_verify = bcrypt.checkpw(encoded_pwd, encoded_hash)
        print(f"bcrypt verification: {bcrypt_verify}")
    except ImportError:
        print("bcrypt module not available")
    except Exception as e:
        print(f"bcrypt error: {e}")
    
    # Test the User model's check_password method
    model_verify = user.check_password("test_password123")
    print(f"Model check_password: {model_verify}")
    
    # Clean up
    db.session.delete(user)
    db.session.commit()
    print("Test user deleted")