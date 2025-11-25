"""
Comprehensive test suite for Discount API endpoints
Tests health check, debug, and production endpoints
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5000"
HOSPITAL_ID = "4ef72e18-e65d-4766-b9eb-0308c42485ca"

def print_test_header(test_name):
    """Print test section header"""
    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print("=" * 70)

def print_result(success, message, response=None):
    """Print test result"""
    status = "PASS" if success else "FAIL"
    symbol = "[OK]" if success else "[X]"
    print(f"{symbol} {status}: {message}")
    if response and not success:
        print(f"    Response: {response}")

def test_health_check():
    """Test 1: Health check endpoint"""
    print_test_header("Health Check Endpoint")

    try:
        url = f"{BASE_URL}/api/discount/health"
        print(f"URL: {url}")

        response = requests.get(url, timeout=5)
        status_code = response.status_code

        if status_code == 200:
            data = response.json()
            print_result(True, f"Health check passed - Status: {data.get('status')}")
            print(f"    Message: {data.get('message')}")
            print(f"    Available endpoints: {len(data.get('endpoints', []))}")
            return True
        else:
            print_result(False, f"Unexpected status code: {status_code}", response.text)
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print_result(False, "Connection failed - Is the server running?")
        return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_debug_endpoint():
    """Test 2: Debug endpoint"""
    print_test_header("Debug Endpoint")

    try:
        url = f"{BASE_URL}/api/discount/debug"
        print(f"URL: {url}")

        response = requests.get(url, timeout=10)
        status_code = response.status_code

        if status_code == 200:
            data = response.json()
            print_result(True, "Debug endpoint passed")
            print(f"    Status: {data.get('status')}")
            print(f"    Timestamp: {data.get('timestamp')}")

            db_info = data.get('database', {})
            print(f"    Database status: {db_info.get('status')}")
            if db_info.get('status') == 'connected':
                print(f"    Hospitals: {db_info.get('info', {}).get('hospitals', 0)}")
                print(f"    Services: {db_info.get('info', {}).get('services', 0)}")

            discount_service = data.get('discount_service', {})
            print(f"    DiscountService imported: {discount_service.get('imported', False)}")
            print(f"    Methods: {len(discount_service.get('methods', []))}")

            return True
        else:
            print_result(False, f"Unexpected status code: {status_code}", response.text)
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_test_config():
    """Test 3: Test config endpoint (simplified)"""
    print_test_header("Test Config Endpoint (Simplified)")

    try:
        url = f"{BASE_URL}/api/discount/test-config/{HOSPITAL_ID}"
        print(f"URL: {url}")

        response = requests.get(url, timeout=10)
        status_code = response.status_code

        if status_code == 200:
            data = response.json()
            if data.get('success'):
                hospital = data.get('hospital', {})
                print_result(True, "Test config passed")
                print(f"    Hospital: {hospital.get('name')}")
                print(f"    Bulk discount enabled: {hospital.get('bulk_discount_enabled')}")
                print(f"    Min service count: {hospital.get('bulk_discount_min_service_count')}")
                return True
            else:
                print_result(False, f"API returned success=False: {data.get('error')}")
                return False
        else:
            print_result(False, f"Unexpected status code: {status_code}", response.text)
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_full_config():
    """Test 4: Full discount config endpoint (production)"""
    print_test_header("Full Discount Config Endpoint (Production)")

    try:
        url = f"{BASE_URL}/api/discount/config/{HOSPITAL_ID}"
        print(f"URL: {url}")

        response = requests.get(url, timeout=15)
        status_code = response.status_code

        if status_code == 200:
            data = response.json()
            if data.get('success'):
                hospital_config = data.get('hospital_config', {})
                service_discounts = data.get('service_discounts', {})

                print_result(True, "Full config passed")
                print(f"    Hospital: {hospital_config.get('hospital_name')}")
                print(f"    Bulk discount enabled: {hospital_config.get('bulk_discount_enabled')}")
                print(f"    Min service count: {hospital_config.get('bulk_discount_min_service_count')}")
                print(f"    Total services: {len(service_discounts)}")

                # Count services with bulk discount
                eligible_count = sum(1 for s in service_discounts.values() if s.get('has_bulk_discount'))
                print(f"    Services with bulk discount: {eligible_count}")

                # Show sample services
                print(f"\n    Sample services with bulk discount:")
                count = 0
                for service in service_discounts.values():
                    if service.get('has_bulk_discount') and count < 3:
                        print(f"      - {service.get('service_name')}: {service.get('bulk_discount_percent')}%")
                        count += 1

                return True
            else:
                print_result(False, f"API returned success=False")
                return False
        else:
            print_result(False, f"Unexpected status code: {status_code}", response.text[:200])
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out - This is the main issue!")
        return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_calculate_discounts():
    """Test 5: Calculate discounts endpoint"""
    print_test_header("Calculate Discounts Endpoint")

    try:
        url = f"{BASE_URL}/api/discount/calculate"
        print(f"URL: {url}")

        # Sample request with 5 services (should trigger bulk discount)
        payload = {
            "hospital_id": HOSPITAL_ID,
            "patient_id": None,  # No patient (no loyalty discount)
            "line_items": [
                {"item_type": "Service", "service_id": "sample-service-1", "quantity": 1, "unit_price": 5000.00},
                {"item_type": "Service", "service_id": "sample-service-2", "quantity": 1, "unit_price": 6000.00},
                {"item_type": "Service", "service_id": "sample-service-3", "quantity": 1, "unit_price": 7000.00},
                {"item_type": "Service", "service_id": "sample-service-4", "quantity": 1, "unit_price": 8000.00},
                {"item_type": "Service", "service_id": "sample-service-5", "quantity": 1, "unit_price": 9000.00}
            ]
        }

        print(f"    Sending {len(payload['line_items'])} line items...")

        response = requests.post(url, json=payload, timeout=15)
        status_code = response.status_code

        if status_code == 200:
            data = response.json()
            if data.get('success'):
                summary = data.get('summary', {})
                print_result(True, "Calculate discounts passed")
                print(f"    Total services: {summary.get('total_services')}")
                print(f"    Bulk discount eligible: {summary.get('bulk_discount_eligible')}")
                print(f"    Original price: Rs.{summary.get('total_original_price', 0):,.2f}")
                print(f"    Total discount: Rs.{summary.get('total_discount', 0):,.2f}")
                print(f"    Final price: Rs.{summary.get('total_final_price', 0):,.2f}")
                return True
            else:
                print_result(False, f"API returned success=False")
                return False
        else:
            print_result(False, f"Unexpected status code: {status_code}", response.text[:200])
            return False

    except requests.exceptions.Timeout:
        print_result(False, "Request timed out")
        return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("DISCOUNT API ENDPOINT TEST SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"Hospital ID: {HOSPITAL_ID}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {
        "Health Check": test_health_check(),
        "Debug Endpoint": test_debug_endpoint(),
        "Test Config": test_test_config(),
        "Full Config": test_full_config(),
        "Calculate Discounts": test_calculate_discounts()
    }

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[X]"
        print(f"{symbol} {test_name}: {status}")

    print("-" * 70)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\nSUCCESS: All tests passed!")
        print("The bulk discount system is ready for use.")
        return 0
    else:
        print(f"\nFAILURE: {total - passed} test(s) failed.")
        print("Please check the failed tests above for details.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
