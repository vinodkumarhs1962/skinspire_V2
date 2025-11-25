"""
Quick test script to verify Flask routes are registered
Run this while your Flask server is running
"""
import requests

BASE_URL = "http://127.0.0.1:5000"

print("=" * 60)
print("Testing Flask Routes")
print("=" * 60)

# Test routes
routes_to_test = [
    "/api/universal/services/search?q=test",
    "/api/universal/medicines/search?q=test",
    "/api/universal/patients/search?q=test",
]

for route in routes_to_test:
    url = BASE_URL + route
    print(f"\nTesting: {url}")
    try:
        response = requests.get(url, allow_redirects=False, timeout=5)
        print(f"  Status: {response.status_code}")

        if response.status_code == 302:
            print(f"  [OK] Route exists (redirects to: {response.headers.get('Location')})")
        elif response.status_code == 200:
            print(f"  [OK] Route exists and returned data")
        elif response.status_code == 404:
            print(f"  [FAIL] Route NOT FOUND")
        else:
            print(f"  [?] Unexpected status: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Could not connect - Is Flask server running on {BASE_URL}?")
        break
    except Exception as e:
        print(f"  [ERROR] Error: {e}")

print("\n" + "=" * 60)
print("If you see 404 for medicines, your Flask server needs restart")
print("=" * 60)
