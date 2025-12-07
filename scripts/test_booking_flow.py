"""
End-to-end test for Appointment Booking Flow
Tests all autocomplete dropdowns and booking APIs
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000"

# Create a session to maintain cookies
session = requests.Session()

def print_result(test_name, success, response=None, details=None):
    status = "PASS" if success else "FAIL"
    print(f"\n{'='*60}")
    print(f"[{status}] {test_name}")
    if response:
        print(f"  Status Code: {response.status_code}")
    if details:
        print(f"  Details: {details}")
    print('='*60)

def login():
    """Login to get a session"""
    print("\n--- Attempting login ---")
    # Use test user credentials
    login_data = {
        "mobile_number": "7777777777",
        "password": "test123"
    }
    try:
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        print(f"Login response: {response.status_code}")
        if response.status_code in [200, 302]:
            return True
    except Exception as e:
        print(f"Login error: {e}")
    return False

def test_patient_autocomplete():
    """Test patient autocomplete API"""
    print("\n--- Testing Patient Autocomplete ---")
    try:
        response = session.get(f"{BASE_URL}/api/appointment/web/patients/search", params={"query": "a", "limit": 5})
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                patients = data.get('patients', [])
                print_result("Patient Autocomplete", True, response, f"Found {len(patients)} patients")
                if patients:
                    print(f"  Sample patient: {patients[0].get('name', 'N/A')}")
                return patients[0] if patients else None
            else:
                print_result("Patient Autocomplete", False, response, data.get('error'))
        else:
            print_result("Patient Autocomplete", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Patient Autocomplete", False, details=str(e))
    return None

def test_service_dropdown():
    """Test service dropdown API"""
    print("\n--- Testing Service Dropdown ---")
    try:
        response = session.get(f"{BASE_URL}/api/appointment/web/services")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                services = data.get('services', [])
                print_result("Service Dropdown", True, response, f"Found {len(services)} services")
                if services:
                    print(f"  Sample service: {services[0].get('name', 'N/A')} - Duration: {services[0].get('duration_minutes', 'N/A')} min")
                return services[0] if services else None
            else:
                print_result("Service Dropdown", False, response, data.get('error'))
        else:
            print_result("Service Dropdown", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Service Dropdown", False, details=str(e))
    return None

def test_package_dropdown():
    """Test package dropdown API"""
    print("\n--- Testing Package Dropdown ---")
    try:
        response = session.get(f"{BASE_URL}/api/appointment/web/packages")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                packages = data.get('packages', [])
                print_result("Package Dropdown", True, response, f"Found {len(packages)} packages")
                if packages:
                    print(f"  Sample package: {packages[0].get('name', 'N/A')}")
                return packages[0] if packages else None
            else:
                print_result("Package Dropdown", False, response, data.get('error'))
        else:
            print_result("Package Dropdown", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Package Dropdown", False, details=str(e))
    return None

def test_specialization_dropdown():
    """Test specialization dropdown API"""
    print("\n--- Testing Specialization Dropdown ---")
    try:
        response = session.get(f"{BASE_URL}/api/appointment/web/specializations")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                specializations = data.get('specializations', [])
                print_result("Specialization Dropdown", True, response, f"Found {len(specializations)} specializations")
                return specializations[0] if specializations else None
            else:
                print_result("Specialization Dropdown", False, response, data.get('error'))
        else:
            print_result("Specialization Dropdown", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Specialization Dropdown", False, details=str(e))
    return None

def test_doctor_dropdown(specialization=None):
    """Test doctor dropdown API"""
    print("\n--- Testing Doctor Dropdown ---")
    try:
        params = {}
        if specialization:
            params['specialization'] = specialization
        response = session.get(f"{BASE_URL}/api/appointment/web/doctors", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                doctors = data.get('doctors', [])
                print_result("Doctor Dropdown", True, response, f"Found {len(doctors)} doctors")
                if doctors:
                    print(f"  Sample doctor: {doctors[0].get('name', 'N/A')} - {doctors[0].get('specialization', 'N/A')}")
                return doctors[0] if doctors else None
            else:
                print_result("Doctor Dropdown", False, response, data.get('error'))
        else:
            print_result("Doctor Dropdown", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Doctor Dropdown", False, details=str(e))
    return None

def test_available_slots(doctor_id, booking_type='consultation', service_id=None):
    """Test available slots API"""
    print("\n--- Testing Available Slots ---")
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        params = {
            'doctor_id': doctor_id,
            'date': tomorrow,
            'booking_type': booking_type
        }
        if service_id:
            params['service_id'] = service_id

        response = session.get(f"{BASE_URL}/api/appointment/web/slots/available", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                slots = data.get('slots', [])
                print_result("Available Slots", True, response, f"Found {len(slots)} slots for {tomorrow}")
                if slots:
                    print(f"  Sample slot: {slots[0].get('start_time', 'N/A')} - {slots[0].get('end_time', 'N/A')}")
                return slots[0] if slots else None
            else:
                print_result("Available Slots", False, response, data.get('error'))
        else:
            print_result("Available Slots", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Available Slots", False, details=str(e))
    return None

def test_rooms_available(date, start_time, end_time):
    """Test available rooms API"""
    print("\n--- Testing Room Availability ---")
    try:
        params = {
            'date': date,
            'start_time': start_time,
            'end_time': end_time
        }
        response = session.get(f"{BASE_URL}/api/appointment/web/rooms/available", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                rooms = data.get('rooms', [])
                print_result("Room Availability", True, response, f"Found {len(rooms)} available rooms")
                if rooms:
                    print(f"  Sample room: {rooms[0].get('room_name', 'N/A')} ({rooms[0].get('room_type', 'N/A')})")
                return rooms[0] if rooms else None
            else:
                print_result("Room Availability", False, response, data.get('error'))
        else:
            print_result("Room Availability", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Room Availability", False, details=str(e))
    return None

def test_therapists_available(date, start_time, end_time):
    """Test available therapists API"""
    print("\n--- Testing Therapist Availability ---")
    try:
        params = {
            'date': date,
            'start_time': start_time,
            'end_time': end_time
        }
        response = session.get(f"{BASE_URL}/api/appointment/web/therapists/available", params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                therapists = data.get('therapists', [])
                print_result("Therapist Availability", True, response, f"Found {len(therapists)} available therapists")
                if therapists:
                    print(f"  Sample therapist: {therapists[0].get('name', 'N/A')}")
                return therapists[0] if therapists else None
            else:
                print_result("Therapist Availability", False, response, data.get('error'))
        else:
            print_result("Therapist Availability", False, response, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("Therapist Availability", False, details=str(e))
    return None

def test_booking_flow(patient, doctor, slot, service=None, room=None, therapist=None):
    """Test full booking API"""
    print("\n--- Testing Full Booking Flow ---")
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        booking_data = {
            'patient_id': patient.get('patient_id'),
            'staff_id': doctor.get('staff_id'),
            'booking_source': 'front_desk',
            'appointment_purpose': 'consultation',
            'appointment_date': tomorrow,
            'start_time': slot.get('start_time'),
            'end_time': slot.get('end_time'),
            'chief_complaint': 'Test booking via API'
        }

        if service:
            booking_data['service_id'] = service.get('service_id')
            booking_data['appointment_purpose'] = 'service'

        response = session.post(
            f"{BASE_URL}/api/appointment/web/book",
            json=booking_data,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointment = data.get('appointment', {})
                apt_id = appointment.get('appointment_id')
                print_result("Booking Created", True, response, f"Appointment ID: {apt_id}")

                # If we have room/therapist, try to allocate resources
                if apt_id and (room or therapist):
                    print("\n--- Testing Resource Allocation ---")
                    alloc_data = {}
                    if room:
                        alloc_data['room_id'] = room.get('room_id')
                    if therapist:
                        alloc_data['therapist_id'] = therapist.get('staff_id')
                    alloc_data['approve'] = False

                    alloc_response = session.post(
                        f"{BASE_URL}/api/appointment/web/appointment/{apt_id}/allocate-resources",
                        json=alloc_data,
                        headers={'Content-Type': 'application/json'}
                    )

                    if alloc_response.status_code == 200:
                        alloc_result = alloc_response.json()
                        if alloc_result.get('success'):
                            print_result("Resource Allocation", True, alloc_response,
                                        f"Room: {alloc_result.get('room_allocated')}, Therapist: {alloc_result.get('therapist_allocated')}")
                        else:
                            print_result("Resource Allocation", False, alloc_response, alloc_result.get('error'))
                    else:
                        print_result("Resource Allocation", False, alloc_response, f"HTTP {alloc_response.status_code}")

                return appointment
            else:
                print_result("Booking Created", False, response, data.get('error'))
        else:
            print_result("Booking Created", False, response, f"HTTP {response.status_code}")
            try:
                print(f"  Response: {response.text[:500]}")
            except:
                pass
    except Exception as e:
        print_result("Booking Created", False, details=str(e))
    return None


if __name__ == "__main__":
    print("\n" + "="*70)
    print("      APPOINTMENT BOOKING - END TO END TEST")
    print("="*70)

    # Login first
    if not login():
        print("Warning: Could not login, some tests may fail")

    # Test dropdowns
    patient = test_patient_autocomplete()
    service = test_service_dropdown()
    package = test_package_dropdown()
    specialization = test_specialization_dropdown()
    doctor = test_doctor_dropdown()

    # Test slots
    if doctor:
        slot = test_available_slots(doctor.get('staff_id'), 'service', service.get('service_id') if service else None)
    else:
        slot = None
        print_result("Available Slots", False, details="No doctor available to test")

    # Test resource availability
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_time = "10:00"
    end_time = "11:00"
    room = test_rooms_available(tomorrow, start_time, end_time)
    therapist = test_therapists_available(tomorrow, start_time, end_time)

    # Test full booking flow
    if patient and doctor and slot:
        test_booking_flow(patient, doctor, slot, service, room, therapist)
    else:
        missing = []
        if not patient: missing.append("patient")
        if not doctor: missing.append("doctor")
        if not slot: missing.append("slot")
        print_result("Full Booking Flow", False, details=f"Missing: {', '.join(missing)}")

    print("\n" + "="*70)
    print("      TEST COMPLETE")
    print("="*70)
