"""
Test script to see what the API returns for patient payments
Run this and then access: http://localhost:5555/test-patient-payments
"""
from app import create_app
from flask import jsonify

app = create_app()

@app.route('/test-patient-payments')
def test_patient_payments():
    from app.services.patient_payment_service import PatientPaymentService
    from flask import request

    service = PatientPaymentService()
    result = service.search_data(
        filters={},
        hospital_id='ee18f62c-0607-400f-8b88-a5c58c5a82e8',
        branch_id=None,
        page=1,
        per_page=5
    )

    # Extract just patient names for easy viewing
    summary = []
    for item in result.get('items', []):
        summary.append({
            'patient_mrn': item.get('patient_mrn'),
            'patient_name': item.get('patient_name'),
            'payment_method_primary': item.get('payment_method_primary'),
            'total_amount': float(item.get('total_amount', 0))
        })

    return jsonify({
        'success': result.get('success'),
        'total': result.get('total'),
        'items_count': len(result.get('items', [])),
        'summary': summary
    })

if __name__ == '__main__':
    print("=" * 80)
    print("TEST SERVER STARTING ON http://localhost:5555/test-patient-payments")
    print("=" * 80)
    app.run(host='localhost', port=5555, debug=False)
