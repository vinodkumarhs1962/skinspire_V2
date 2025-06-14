# app/api/routes/billing.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user  # Add this import
from app.services.database_service import get_db_session  # Add this import
from app.security.authorization.decorators import token_required
from app.security.authorization.permission_validator import has_permission
from app.models.master import Patient, Medicine, Package, Service
from app.models.transaction import User
from app.services.billing_service import get_batch_selection_for_invoice
from decimal import Decimal
import uuid

billing_api_bp = Blueprint('billing_api', __name__)

@billing_api_bp.route('/patient/search', methods=['GET'])
# @token_required
@login_required 
def api_patient_search(user_id, session):
    """API endpoint to search for patients"""
    try:
        # Get current user from user_id
        current_user = session.query(User).filter_by(user_id=user_id).first()
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        query = request.args.get('q', '')
        if len(query) < 1:
            return jsonify([])
        
        # Search by name, MRN, or phone
        patients = session.query(Patient).filter(
            Patient.hospital_id == current_user.hospital_id,
            Patient.is_active == True
        ).filter(
            (Patient.mrn.ilike(f'%{query}%')) |
            (Patient.personal_info['first_name'].astext.ilike(f'%{query}%')) |
            (Patient.personal_info['last_name'].astext.ilike(f'%{query}%')) |
            (Patient.contact_info['phone'].astext.ilike(f'%{query}%'))
        ).limit(10).all()
        
        results = []
        for patient in patients:
            results.append({
                'id': str(patient.patient_id),
                'mrn': patient.mrn,
                'name': patient.full_name,
                'contact': patient.contact_info.get('phone', '')
            })
        
        return jsonify(results)
    
    except Exception as e:
        current_app.logger.error(f"Error searching patients: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@billing_api_bp.route('/item/search', methods=['GET'])
# @token_required
@login_required 
def api_item_search(user_id, session):
    """API endpoint to search for billable items (services, packages, medicines)"""
    try:
        # Get current user from user_id
        current_user = session.query(User).filter_by(user_id=user_id).first()
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        query = request.args.get('q', '')
        item_type = request.args.get('type', 'all')
        
        if len(query) < 2:
            return jsonify([])
        
        results = []
        
        # Search packages
        if item_type in ['all', 'Package']:
            packages = session.query(Package).filter(
                Package.hospital_id == current_user.hospital_id,
                Package.status == 'active',
                Package.package_name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for package in packages:
                results.append({
                    'id': str(package.package_id),
                    'name': package.package_name,
                    'type': 'Package',
                    'price': float(package.price),
                    'gst_rate': float(package.gst_rate or 0),
                    'is_gst_exempt': package.is_gst_exempt
                })
        
        # Search services
        if item_type in ['all', 'Service']:
            services = session.query(Service).filter(
                Service.hospital_id == current_user.hospital_id,
                Service.service_name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for service in services:
                results.append({
                    'id': str(service.service_id),
                    'name': service.service_name,
                    'type': 'Service',
                    'price': float(service.price),
                    'gst_rate': float(service.gst_rate or 0),
                    'is_gst_exempt': service.is_gst_exempt,
                    'sac_code': service.sac_code
                })
        
        # Search medicines
        if item_type in ['all', 'Medicine']:
            medicines = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.status == 'active',
                Medicine.medicine_name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for medicine in medicines:
                results.append({
                    'id': str(medicine.medicine_id),
                    'name': medicine.medicine_name,
                    'type': 'Medicine',
                    'gst_rate': float(medicine.gst_rate or 0),
                    'is_gst_exempt': medicine.is_gst_exempt,
                    'hsn_code': medicine.hsn_code
                })
        
        return jsonify(results)
    
    except Exception as e:
        current_app.logger.error(f"Error searching items: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@billing_api_bp.route('/medicine/<uuid:medicine_id>/batches', methods=['GET'])
# @token_required
@login_required 
def api_medicine_batches(user_id, session, medicine_id):
    """API endpoint to get available batches for a medicine"""
    try:
        # Get current user from user_id
        current_user = session.query(User).filter_by(user_id=user_id).first()
        if not current_user:
            return jsonify({'error': 'User not found'}), 404

        quantity_needed = Decimal(request.args.get('quantity', '1'))
        
        # Get batch selection based on FIFO
        batches = get_batch_selection_for_invoice(
            hospital_id=current_user.hospital_id,
            medicine_id=medicine_id,
            quantity_needed=quantity_needed
        )
        
        return jsonify(batches)
    
    except Exception as e:
        current_app.logger.error(f"Error getting medicine batches: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500