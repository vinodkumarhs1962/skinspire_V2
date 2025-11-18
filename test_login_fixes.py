#!/usr/bin/env python
"""
Test script to verify login fixes
Run this after restarting Flask server
"""
import requests
import sys

BASE_URL = "http://localhost:5000"

def test_logo_accessibility():
    """Test if logo files are accessible"""
    print("=" * 60)
    print("TEST 1: Logo File Accessibility")
    print("=" * 60)

    # Test hospital logo
    hospital_logo_url = f"{BASE_URL}/static/uploads/hospital_logos/98131652-293b-405b-a5e2-a301244efd0a/medium_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg"
    print(f"\nTesting hospital logo: {hospital_logo_url}")

    try:
        response = requests.get(hospital_logo_url)
        if response.status_code == 200:
            print(f"[OK] Hospital logo accessible (Size: {len(response.content)} bytes)")
        else:
            print(f"[FAIL] Hospital logo failed (Status: {response.status_code})")
    except Exception as e:
        print(f"[FAIL] Error accessing hospital logo: {e}")

    # Test fallback SVG logo
    svg_logo_url = f"{BASE_URL}/static/images/logo.svg"
    print(f"\nTesting fallback SVG logo: {svg_logo_url}")

    try:
        response = requests.get(svg_logo_url)
        if response.status_code == 200:
            print(f"[OK] SVG logo accessible (Size: {len(response.content)} bytes)")
        else:
            print(f"[FAIL] SVG logo failed (Status: {response.status_code})")
    except Exception as e:
        print(f"[FAIL] Error accessing SVG logo: {e}")

    print()

def test_login_page():
    """Test if login page renders correctly"""
    print("=" * 60)
    print("TEST 2: Login Page Rendering")
    print("=" * 60)

    try:
        response = requests.get(f"{BASE_URL}/login")
        if response.status_code == 200:
            print("[OK] Login page accessible")

            # Check if logo is in HTML
            if 'medium_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg' in response.text:
                print("[OK] Hospital logo found in HTML")
            elif 'logo.svg' in response.text:
                print("[WARN] Using fallback SVG logo")
            else:
                print("[FAIL] No logo found in HTML")
        else:
            print(f"[FAIL] Login page failed (Status: {response.status_code})")
    except Exception as e:
        print(f"[FAIL] Error accessing login page: {e}")

    print()

def test_password_bypass():
    """Test password bypass for user 7777777777"""
    print("=" * 60)
    print("TEST 3: Password Bypass for User 7777777777")
    print("=" * 60)
    print("\n[INFO] Manual test required:")
    print("1. Open browser to http://localhost:5000/login")
    print("2. Enter username: 7777777777")
    print("3. Leave password BLANK or enter anything")
    print("4. Click 'Sign in'")
    print("5. You should be logged in successfully")
    print("\nCheck logs/app.log for this line:")
    print("   'Test user 7777777777 attempting login - bypassing form validation'")
    print()

def main():
    print("\n" + "=" * 60)
    print("SKINSPIRE LOGIN FIXES VERIFICATION")
    print("=" * 60)
    print()

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/login", timeout=2)
        print("[OK] Flask server is running")
    except requests.exceptions.ConnectionError:
        print("[FAIL] Flask server is NOT running!")
        print("\nPlease start the Flask server first:")
        print("   python run.py")
        print()
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Error connecting to server: {e}")
        sys.exit(1)

    print()

    # Run tests
    test_logo_accessibility()
    test_login_page()
    test_password_bypass()

    print("=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
