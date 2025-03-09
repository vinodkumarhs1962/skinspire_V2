# skinspire_v2/app/api/routes/patient.py

from flask import Blueprint, jsonify

patient_bp = Blueprint('patient', __name__, url_prefix='/api/patient')

@patient_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'})