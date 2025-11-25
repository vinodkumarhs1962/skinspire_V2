"""
Check what routes are available on the RUNNING Flask server
This will tell us if the server has loaded the new code
"""
import requests

print("="*70)
print("CHECKING YOUR RUNNING FLASK SERVER")
print("="*70)

tests = [
    ("Services", "http://127.0.0.1:5000/api/universal/services/search?q=test"),
    ("Medicines", "http://127.0.0.1:5000/api/universal/medicines/search?q=test"),
    ("Patients", "http://127.0.0.1:5000/api/universal/patients/search?q=test"),
]

print("\nTesting routes (should get 302 redirect to /login, NOT 404):\n")

for name, url in tests:
    try:
        r = requests.get(url, allow_redirects=False, timeout=3)
        status = "OK (Route exists)" if r.status_code in [200, 302] else f"FAIL (404 Not Found)"
        print(f"  {name:15} -> Status {r.status_code} -> {status}")
    except requests.exceptions.Timeout:
        print(f"  {name:15} -> TIMEOUT (server hung)")
    except requests.exceptions.ConnectionError:
        print(f"  {name:15} -> CONNECTION ERROR (server not running)")
    except Exception as e:
        print(f"  {name:15} -> ERROR: {e}")

print("\n" + "="*70)
print("RESULT:")
print("="*70)
print("If medicines shows 404, your Flask server has NOT loaded the new code.")
print("You MUST restart the Flask server:")
print("  1. Press Ctrl+C in Flask terminal")
print("  2. Run: python run.py")
print("  3. Wait for 'Application initialization completed successfully'")
print("  4. Run this script again to verify")
print("="*70)
