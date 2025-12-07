# app/api/routes/barcode_api.py
"""
Barcode Scanner API Endpoints
Handles barcode parsing, medicine lookup, and barcode linking

Endpoints:
- POST /api/barcode/parse - Parse barcode without database lookup
- POST /api/barcode/lookup - Parse and lookup medicine by barcode
- POST /api/barcode/link - Link barcode to existing medicine
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.security.authorization.permission_validator import has_permission
from app.services.database_service import get_db_session
import uuid

barcode_api_bp = Blueprint('barcode_api', __name__, url_prefix='/api/barcode')


@barcode_api_bp.route('/parse', methods=['POST'])
@login_required
def parse_barcode():
    """
    Parse a barcode without database lookup

    Request Body:
        {
            "barcode": "(01)08901234567890(10)BATCH001(17)261231"
        }

    Response:
        {
            "success": true,
            "data": {
                "gtin": "08901234567890",
                "batch": "BATCH001",
                "expiry_date": "2026-12-31",
                "expiry_formatted": "31-Dec-2026",
                "is_valid": true,
                "format": "GS1-Parentheses"
            }
        }
    """
    try:
        from app.utils.barcode_utils import extract_medicine_info

        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({
                'success': False,
                'error': 'Barcode data is required'
            }), 400

        barcode = data['barcode'].strip()
        if not barcode:
            return jsonify({
                'success': False,
                'error': 'Barcode cannot be empty'
            }), 400

        # Parse the barcode
        parsed = extract_medicine_info(barcode)

        return jsonify({
            'success': True,
            'data': {
                'gtin': parsed.get('product_code'),
                'batch': parsed.get('batch_number'),
                'expiry_date': parsed.get('expiry_date'),
                'expiry_formatted': parsed.get('expiry_date_formatted'),
                'serial_number': parsed.get('serial_number'),
                'is_valid': parsed.get('is_valid', False),
                'format': parsed.get('format'),
                'raw_data': parsed.get('raw_data')
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error parsing barcode: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to parse barcode'
        }), 500


@barcode_api_bp.route('/lookup', methods=['POST'])
@login_required
def lookup_barcode():
    """
    Parse barcode AND lookup medicine in database

    Request Body:
        {
            "barcode": "(01)08901234567890(10)BATCH001(17)261231"
        }

    Response (Medicine Found):
        {
            "success": true,
            "parsed": { ... },
            "medicine_found": true,
            "medicine": { ... },
            "available_batches": [ ... ]
        }

    Response (Medicine NOT Found):
        {
            "success": true,
            "parsed": { ... },
            "medicine_found": false,
            "medicine": null,
            "message": "Barcode not linked to any medicine"
        }
    """
    try:
        from app.utils.barcode_utils import extract_medicine_info
        from app.models.master import Medicine
        from app.services.inventory_service import get_available_batches_for_item

        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({
                'success': False,
                'error': 'Barcode data is required'
            }), 400

        barcode = data['barcode'].strip()
        if not barcode:
            return jsonify({
                'success': False,
                'error': 'Barcode cannot be empty'
            }), 400

        # Parse the barcode
        parsed = extract_medicine_info(barcode)

        parsed_data = {
            'gtin': parsed.get('product_code'),
            'batch': parsed.get('batch_number'),
            'expiry_date': parsed.get('expiry_date'),
            'expiry_formatted': parsed.get('expiry_date_formatted'),
            'is_valid': parsed.get('is_valid', False),
            'format': parsed.get('format')
        }

        if not parsed.get('is_valid'):
            return jsonify({
                'success': True,
                'parsed': parsed_data,
                'medicine_found': False,
                'medicine': None,
                'available_batches': [],
                'message': parsed.get('error') or 'Invalid barcode format'
            }), 200

        # Lookup medicine by barcode/GTIN
        gtin = parsed.get('product_code')
        medicine_data = None
        available_batches = []

        with get_db_session() as session:
            # Try to find medicine by barcode field
            medicine = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.barcode == gtin,
                Medicine.is_deleted == False
            ).first()

            # If not found by exact barcode, try partial match (for simple barcodes)
            if not medicine and gtin:
                medicine = session.query(Medicine).filter(
                    Medicine.hospital_id == current_user.hospital_id,
                    Medicine.barcode.ilike(f'%{gtin}%'),
                    Medicine.is_deleted == False
                ).first()

            if medicine:
                medicine_data = {
                    'medicine_id': str(medicine.medicine_id),
                    'medicine_name': medicine.medicine_name,
                    'generic_name': medicine.generic_name,
                    'dosage_form': medicine.dosage_form,
                    'unit_of_measure': medicine.unit_of_measure,
                    'medicine_type': medicine.medicine_type,
                    'mrp': float(medicine.mrp) if medicine.mrp else None,
                    'selling_price': float(medicine.selling_price) if medicine.selling_price else None,
                    'cost_price': float(medicine.cost_price) if medicine.cost_price else None,
                    'last_purchase_price': float(medicine.last_purchase_price) if medicine.last_purchase_price else None,
                    'gst_rate': float(medicine.gst_rate) if medicine.gst_rate else None,
                    'cgst_rate': float(medicine.cgst_rate) if medicine.cgst_rate else None,
                    'sgst_rate': float(medicine.sgst_rate) if medicine.sgst_rate else None,
                    'hsn_code': medicine.hsn_code,
                    'current_stock': medicine.current_stock,
                    'barcode': medicine.barcode
                }

                # Get available batches (FIFO sorted)
                try:
                    batches = get_available_batches_for_item(
                        item_id=medicine.medicine_id,
                        hospital_id=current_user.hospital_id,
                        branch_id=None,
                        session=session
                    )
                    available_batches = batches if batches else []
                except Exception as batch_error:
                    current_app.logger.warning(f"Error getting batches: {str(batch_error)}")
                    available_batches = []

        if medicine_data:
            return jsonify({
                'success': True,
                'parsed': parsed_data,
                'medicine_found': True,
                'medicine': medicine_data,
                'available_batches': available_batches
            }), 200
        else:
            return jsonify({
                'success': True,
                'parsed': parsed_data,
                'medicine_found': False,
                'medicine': None,
                'available_batches': [],
                'message': 'Barcode not linked to any medicine. Please link to existing medicine.'
            }), 200

    except Exception as e:
        current_app.logger.error(f"Error looking up barcode: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to lookup barcode'
        }), 500


@barcode_api_bp.route('/link', methods=['POST'])
@login_required
def link_barcode():
    """
    Link a barcode/GTIN to an existing medicine

    Request Body:
        {
            "barcode": "08901234567890",
            "medicine_id": "uuid-of-medicine"
        }

    Response:
        {
            "success": true,
            "message": "Barcode linked to Paracetamol 500mg",
            "medicine_id": "uuid-here",
            "medicine_name": "Paracetamol 500mg"
        }
    """
    # Check permission for medicine master edit
    try:
        if not has_permission(current_user, 'medicine', 'edit'):
            return jsonify({
                'success': False,
                'error': 'Permission denied. Medicine edit permission required.'
            }), 403
    except Exception as perm_error:
        current_app.logger.warning(f"Permission check failed, allowing access: {str(perm_error)}")
        # Continue if permission check fails (e.g., if permission module has issues)

    try:
        from app.models.master import Medicine

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        barcode = data.get('barcode', '').strip()
        medicine_id = data.get('medicine_id', '').strip()

        if not barcode:
            return jsonify({
                'success': False,
                'error': 'Barcode is required'
            }), 400

        if not medicine_id:
            return jsonify({
                'success': False,
                'error': 'Medicine ID is required'
            }), 400

        # Validate medicine_id format
        try:
            medicine_uuid = uuid.UUID(medicine_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid medicine ID format'
            }), 400

        with get_db_session() as session:
            # Check if barcode is already linked to another medicine
            existing = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.barcode == barcode,
                Medicine.medicine_id != medicine_uuid,
                Medicine.is_deleted == False
            ).first()

            if existing:
                return jsonify({
                    'success': False,
                    'error': f'Barcode already linked to {existing.medicine_name}'
                }), 400

            # Find the medicine to update
            medicine = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.medicine_id == medicine_uuid,
                Medicine.is_deleted == False
            ).first()

            if not medicine:
                return jsonify({
                    'success': False,
                    'error': 'Medicine not found'
                }), 404

            # Store values before commit (to avoid closed session issues)
            medicine_name = medicine.medicine_name
            medicine_id_str = str(medicine.medicine_id)
            old_barcode = medicine.barcode

            # Update barcode
            medicine.barcode = barcode
            session.commit()

            current_app.logger.info(
                f"Barcode linked: {barcode} -> {medicine_name} "
                f"(was: {old_barcode}) by user {current_user.user_id}"
            )

            return jsonify({
                'success': True,
                'message': f'Barcode linked to {medicine_name}',
                'medicine_id': medicine_id_str,
                'medicine_name': medicine_name,
                'barcode': barcode
            }), 200

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Error linking barcode: {str(e)}\n{error_details}")
        return jsonify({
            'success': False,
            'error': f'Failed to link barcode: {str(e)}'
        }), 500


@barcode_api_bp.route('/search-medicine', methods=['GET'])
@login_required
def search_medicine_for_linking():
    """
    Search medicines for barcode linking modal

    Query Parameters:
        q: Search query (medicine name)
        limit: Max results (default 10)

    Response:
        {
            "success": true,
            "medicines": [
                {
                    "medicine_id": "uuid",
                    "medicine_name": "Paracetamol 500mg",
                    "generic_name": "Paracetamol",
                    "manufacturer": "Sun Pharma",
                    "barcode": null or "existing-barcode"
                }
            ]
        }
    """
    try:
        from app.models.master import Medicine, Manufacturer
        from sqlalchemy import or_

        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)

        if len(query) < 2:
            return jsonify({
                'success': True,
                'medicines': []
            }), 200

        with get_db_session() as session:
            # Search by name or generic name
            medicines = session.query(Medicine).outerjoin(
                Manufacturer, Medicine.manufacturer_id == Manufacturer.manufacturer_id
            ).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.is_deleted == False,
                or_(
                    Medicine.medicine_name.ilike(f'%{query}%'),
                    Medicine.generic_name.ilike(f'%{query}%')
                )
            ).limit(limit).all()

            results = []
            for med in medicines:
                manufacturer_name = None
                if med.manufacturer_id:
                    manufacturer = session.query(Manufacturer).filter(
                        Manufacturer.manufacturer_id == med.manufacturer_id
                    ).first()
                    if manufacturer:
                        manufacturer_name = manufacturer.manufacturer_name

                results.append({
                    'medicine_id': str(med.medicine_id),
                    'medicine_name': med.medicine_name,
                    'generic_name': med.generic_name,
                    'manufacturer': manufacturer_name,
                    'dosage_form': med.dosage_form,
                    'barcode': med.barcode,
                    'has_barcode': bool(med.barcode)
                })

            return jsonify({
                'success': True,
                'medicines': results
            }), 200

    except Exception as e:
        current_app.logger.error(f"Error searching medicines: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search medicines'
        }), 500
