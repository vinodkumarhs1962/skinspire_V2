# app/api/routes/discount_api.py
"""
Discount API Routes
Provides real-time discount configuration and calculation for invoice UI
"""

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Dict, List
import logging

from app.services.database_service import get_db_session
from app.models.master import Hospital, Service, LoyaltyCardType
from app.models.transaction import PatientLoyaltyWallet
from app.services.discount_service import DiscountService

# Configure logger
logger = logging.getLogger(__name__)

discount_bp = Blueprint('discount_api', __name__, url_prefix='/api/discount')


# ========================================================================
# HEALTH CHECK & DEBUG ENDPOINTS
# ========================================================================

@discount_bp.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint
    Returns 200 OK if API is responsive
    """
    return jsonify({
        'status': 'ok',
        'message': 'Discount API is running',
        'endpoints': [
            '/api/discount/health',
            '/api/discount/debug',
            '/api/discount/config/<hospital_id>',
            '/api/discount/calculate',
            '/api/discount/patient-loyalty/<patient_id>'
        ]
    }), 200


@discount_bp.route('/debug', methods=['GET'])
def debug_info():
    """
    Debug endpoint - returns system information
    """
    import sys
    from datetime import datetime

    try:
        # Test database connection
        with get_db_session() as session:
            # Quick query to test DB
            hospital_count = session.query(Hospital).count()
            service_count = session.query(Service).count()

            db_status = 'connected'
            db_info = {
                'hospitals': hospital_count,
                'services': service_count
            }
    except Exception as e:
        db_status = 'error'
        db_info = {'error': str(e)}

    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'python_version': sys.version,
        'database': {
            'status': db_status,
            'info': db_info
        },
        'discount_service': {
            'imported': 'DiscountService' in dir(),
            'methods': [m for m in dir(DiscountService) if not m.startswith('_')]
        }
    }), 200


@discount_bp.route('/test-config/<hospital_id>', methods=['GET'])
def test_config(hospital_id: str):
    """
    Test endpoint - simplified version of config endpoint for debugging
    """
    try:
        with get_db_session() as session:
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

            if not hospital:
                return jsonify({
                    'success': False,
                    'error': 'Hospital not found',
                    'hospital_id': hospital_id
                }), 404

            return jsonify({
                'success': True,
                'hospital': {
                    'id': str(hospital.hospital_id),
                    'name': hospital.name,
                    'bulk_discount_enabled': hospital.bulk_discount_enabled or False,
                    'bulk_discount_min_service_count': hospital.bulk_discount_min_service_count or 5
                }
            }), 200

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ========================================================================
# PRODUCTION ENDPOINTS
# ========================================================================

@discount_bp.route('/config/<hospital_id>', methods=['GET'])
def get_discount_config(hospital_id: str):
    """
    Get discount configuration for a hospital
    Returns hospital policy and service-level discount rates

    Used by invoice creation UI for real-time discount calculations
    """
    logger.info(f"Discount config request received for hospital: {hospital_id}")

    try:
        logger.debug("Opening database session...")
        with get_db_session() as session:
            logger.debug("Database session opened successfully")

            # Get hospital configuration
            logger.debug(f"Querying hospital: {hospital_id}")
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

            if not hospital:
                logger.warning(f"Hospital not found: {hospital_id}")
                return jsonify({'error': 'Hospital not found'}), 404

            logger.debug(f"Hospital found: {hospital.name}")

            # Get all active services with discount config
            logger.debug(f"Querying services for hospital: {hospital_id}")
            services = session.query(Service).filter(
                Service.hospital_id == hospital_id,
                Service.is_active == True,
                Service.is_deleted == False
            ).all()

            logger.info(f"Found {len(services)} active services")

            # Build service discount map
            service_discounts = {}
            for service in services:
                service_discounts[str(service.service_id)] = {
                    'service_id': str(service.service_id),
                    'service_name': service.service_name,
                    'price': float(service.price),
                    'bulk_discount_percent': float(service.bulk_discount_percent or 0),
                    'max_discount': float(service.max_discount or 100),
                    'has_bulk_discount': service.bulk_discount_percent > 0 if service.bulk_discount_percent else False
                }

            logger.debug(f"Built service discount map with {len(service_discounts)} entries")

            response_data = {
                'success': True,
                'hospital_config': {
                    'hospital_id': str(hospital.hospital_id),
                    'hospital_name': hospital.name,
                    'bulk_discount_enabled': hospital.bulk_discount_enabled or False,
                    'bulk_discount_min_service_count': hospital.bulk_discount_min_service_count or 5,
                    'bulk_discount_effective_from': hospital.bulk_discount_effective_from.isoformat() if hospital.bulk_discount_effective_from else None
                },
                'service_discounts': service_discounts
            }

            logger.info(f"Returning discount config for {hospital.name}")
            return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in get_discount_config: {str(e)}", exc_info=True)
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@discount_bp.route('/calculate', methods=['POST'])
def calculate_discounts():
    """
    Calculate discounts for a set of line items in real-time
    Used by invoice UI to show pricing before submission

    Request Body:
    {
        "hospital_id": "uuid",
        "patient_id": "uuid",
        "line_items": [
            {"service_id": "uuid", "quantity": 1, "unit_price": 5000.00},
            ...
        ]
    }

    Response:
    {
        "success": true,
        "line_items": [...],  // With discount fields populated
        "summary": {
            "total_services": 5,
            "bulk_discount_eligible": true,
            "total_original_price": 25000.00,
            "total_discount": 2500.00,
            "total_final_price": 22500.00,
            "potential_savings": {...}
        }
    }
    """
    logger.info("Discount calculation request received")

    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")

        hospital_id = data.get('hospital_id')
        patient_id = data.get('patient_id')
        line_items = data.get('line_items', [])
        exclude_bulk = data.get('exclude_bulk', False)  # Staff manually unchecked bulk discount
        exclude_loyalty = data.get('exclude_loyalty', False)  # Staff manually unchecked loyalty discount
        exclude_standard = data.get('exclude_standard', False)  # Staff manually unchecked standard discount
        exclude_campaign = data.get('exclude_campaign', False)  # Staff unchecked campaign discount (Added 2025-11-29)
        excluded_campaign_ids = data.get('excluded_campaign_ids', [])  # Specific campaign IDs to exclude
        manual_promo_code = data.get('manual_promo_code')  # Manually entered promo code
        staff_discretionary = data.get('staff_discretionary')  # Staff discretionary discount (Added 2025-11-29)
        vip_discount = data.get('vip_discount')  # VIP discount (Added 2025-11-29)
        # Determine if VIP should be excluded at line-item level (Added 2025-11-29)
        # VIP is excluded if: vip_discount is provided and enabled is False
        exclude_vip = False
        if vip_discount and vip_discount.get('enabled') == False:
            exclude_vip = True
            logger.info("VIP discount disabled by user - will exclude VIP from line-item calculations")

        logger.info(f"Parsed: hospital_id={hospital_id}, patient_id={patient_id}, line_items count={len(line_items)}, exclude_bulk={exclude_bulk}, exclude_loyalty={exclude_loyalty}, exclude_standard={exclude_standard}, exclude_campaign={exclude_campaign}, excluded_campaign_ids={excluded_campaign_ids}, manual_promo={manual_promo_code}, staff_discretionary={staff_discretionary}, vip_discount={vip_discount}")

        if not hospital_id or not line_items:
            logger.error(f"Validation failed: hospital_id={hospital_id}, line_items={len(line_items) if line_items else 0}")
            return jsonify({'error': 'Missing required fields', 'success': False}), 400

        with get_db_session() as session:
            # Get hospital config early for stacking configuration - Added 2025-11-29
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

            # Apply discounts using multi-discount service (supports stacking)
            discounted_items = DiscountService.apply_discounts_to_invoice_items_multi(
                session=session,
                hospital_id=hospital_id,
                patient_id=patient_id,
                line_items=line_items,
                respect_max_discount=True,
                exclude_bulk=exclude_bulk,  # Pass to service
                exclude_loyalty=exclude_loyalty,  # Pass to service
                exclude_standard=exclude_standard,  # Pass to service
                exclude_campaign=exclude_campaign,  # Pass to service (Added 2025-11-29)
                excluded_campaign_ids=excluded_campaign_ids,  # Per-campaign exclusion
                manual_promo_code=manual_promo_code,  # Manually entered promo code
                staff_discretionary=staff_discretionary,  # Staff discretionary discount (Added 2025-11-29)
                exclude_vip=exclude_vip  # Staff disabled VIP discount (Added 2025-11-29)
            )

            # Calculate summary for services (including Package) - Updated 2025-11-29
            service_types = ['Service', 'Package']
            service_items = [item for item in discounted_items if item.get('item_type') in service_types]
            total_service_count = sum(int(item.get('quantity', 1)) for item in service_items)

            service_original_price = sum(
                float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
                for item in service_items
            )

            service_discount = sum(
                float(item.get('discount_amount', 0))
                for item in service_items
            )

            # Calculate bulk and loyalty discounts separately
            bulk_discount_amount = 0
            loyalty_discount_amount = 0
            for item in service_items:
                metadata = item.get('discount_metadata', {})
                if 'bulk_percent' in metadata and 'loyalty_percent' in metadata:
                    # Stacked discount - calculate each component
                    original = float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
                    bulk_discount_amount += (original * float(metadata['bulk_percent'])) / 100
                    loyalty_discount_amount += (original * float(metadata['loyalty_percent'])) / 100
                elif item.get('discount_type') == 'bulk':
                    bulk_discount_amount += float(item.get('discount_amount', 0))
                elif item.get('discount_type') in ['loyalty', 'loyalty_percent']:
                    loyalty_discount_amount += float(item.get('discount_amount', 0))

            # Calculate summary for medicines (including OTC, Prescription, Product, Consumable) - Updated 2025-11-29
            medicine_types = ['Medicine', 'OTC', 'Prescription', 'Product', 'Consumable']
            medicine_items = [item for item in discounted_items if item.get('item_type') in medicine_types]
            total_medicine_count = sum(int(item.get('quantity', 1)) for item in medicine_items)

            medicine_original_price = sum(
                float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
                for item in medicine_items
            )

            medicine_discount = sum(
                float(item.get('discount_amount', 0))
                for item in medicine_items
            )

            # Combined totals (line-item level discounts)
            total_original_price = service_original_price + medicine_original_price
            line_item_discount = service_discount + medicine_discount
            subtotal_after_line_discounts = total_original_price - line_item_discount

            # =================================================================
            # INVOICE-LEVEL DISCOUNTS (VIP and Staff Discretionary) - Added 2025-11-29
            # These are applied based on hospital's stacking configuration
            # =================================================================
            vip_discount_amount = 0
            vip_discount_percent = 0
            staff_discretionary_amount = 0
            staff_discretionary_percent = 0
            vip_stacking_mode = 'incremental'  # Default mode

            # Get VIP stacking mode from hospital's discount_stacking_config
            if hospital and hospital.discount_stacking_config:
                vip_config = hospital.discount_stacking_config.get('vip', {})
                vip_stacking_mode = vip_config.get('mode', 'incremental')
                logger.info(f"VIP stacking mode from config: {vip_stacking_mode}")

            # VIP Discount - Added 2025-11-29
            # Mode 'exclusive': VIP replaces ALL line-item discounts (only VIP applies)
            # Mode 'absolute': VIP competes with line-item discounts (better discount wins)
            # Mode 'incremental': VIP stacks on top of line-item discounts
            if vip_discount and vip_discount.get('enabled'):
                vip_discount_percent = float(vip_discount.get('percent', 0))
                if vip_discount_percent > 0:
                    if vip_stacking_mode == 'exclusive':
                        # EXCLUSIVE MODE: VIP replaces ALL line-item discounts
                        # VIP discount is calculated on original price, line-item discounts are zeroed
                        vip_on_original = (total_original_price * vip_discount_percent) / 100

                        # Zero out line-item discounts - VIP is the ONLY discount
                        logger.info(f"VIP (exclusive): Replacing line-item discounts Rs.{line_item_discount:.2f} with VIP {vip_discount_percent}% = Rs.{vip_on_original:.2f}")

                        # Clear line-item discounts from items
                        for item in discounted_items:
                            item['discount_amount'] = 0
                            item['discount_percent'] = 0
                            item['discount_type'] = None
                            item['final_price'] = float(item.get('unit_price', 0)) * int(item.get('quantity', 1))

                        # Reset line-item totals
                        line_item_discount = 0
                        bulk_discount_amount = 0
                        loyalty_discount_amount = 0
                        subtotal_after_line_discounts = total_original_price

                        # Set VIP discount as the only discount
                        vip_discount_amount = vip_on_original
                        logger.info(f"VIP (exclusive): Only VIP discount applies: Rs.{vip_discount_amount:.2f} on Rs.{total_original_price:.2f}")

                    elif vip_stacking_mode == 'absolute':
                        # Calculate VIP on original price (competes with line-item discounts)
                        vip_on_original = (total_original_price * vip_discount_percent) / 100

                        # Compare: VIP discount vs line-item discounts - better one wins
                        if vip_on_original > line_item_discount:
                            # VIP is better - replace line-item discounts
                            vip_discount_amount = vip_on_original - line_item_discount
                            logger.info(f"VIP (absolute): {vip_discount_percent}% on Rs.{total_original_price:.2f} = Rs.{vip_on_original:.2f} > line discounts Rs.{line_item_discount:.2f}. Additional VIP: Rs.{vip_discount_amount:.2f}")
                        else:
                            # Line-item discounts are better - VIP doesn't add anything
                            vip_discount_amount = 0
                            logger.info(f"VIP (absolute): {vip_discount_percent}% = Rs.{vip_on_original:.2f} <= line discounts Rs.{line_item_discount:.2f}. Line discounts win.")
                    else:
                        # Incremental mode (default): VIP stacks on top of line-item discounts
                        vip_discount_amount = (subtotal_after_line_discounts * vip_discount_percent) / 100
                        logger.info(f"VIP (incremental): {vip_discount_percent}% on Rs.{subtotal_after_line_discounts:.2f} = Rs.{vip_discount_amount:.2f}")

            # Staff Discretionary Discount (applied on subtotal after VIP)
            subtotal_after_vip = subtotal_after_line_discounts - vip_discount_amount
            if staff_discretionary and staff_discretionary.get('enabled'):
                staff_discretionary_percent = float(staff_discretionary.get('percent', 0))
                if staff_discretionary_percent > 0:
                    staff_discretionary_amount = (subtotal_after_vip * staff_discretionary_percent) / 100
                    logger.info(f"Invoice-level Staff Discretionary: {staff_discretionary_percent}% = Rs.{staff_discretionary_amount:.2f}")

            # Total invoice-level discount
            invoice_level_discount = vip_discount_amount + staff_discretionary_amount

            # Final totals
            total_discount = line_item_discount + invoice_level_discount
            total_final_price = total_original_price - total_discount

            # Get min threshold from hospital (hospital already queried earlier)
            min_threshold = hospital.bulk_discount_min_service_count if hospital else 5

            # Calculate potential savings if user adds more services/medicines
            potential_savings_services = calculate_potential_savings(
                session, hospital_id, patient_id, service_items, min_threshold, 'Service'
            )
            potential_savings_medicines = calculate_potential_savings(
                session, hospital_id, patient_id, medicine_items, min_threshold, 'Medicine'
            )

            # DEBUG: Log metadata for first item
            if discounted_items:
                first_item = discounted_items[0]
                logger.info(f"First item metadata: {first_item.get('discount_metadata', {})}")
                if 'all_eligible_discounts' in first_item.get('discount_metadata', {}):
                    logger.info(f"all_eligible_discounts found: {first_item['discount_metadata']['all_eligible_discounts']}")
                else:
                    logger.warning(f"all_eligible_discounts NOT found in metadata")

            # Extract eligible campaigns from discount metadata (Added 2025-11-29)
            eligible_campaigns = []
            for item in discounted_items:
                metadata = item.get('discount_metadata', {})
                all_eligible = metadata.get('all_eligible_discounts', [])
                for disc in all_eligible:
                    if disc.get('type') == 'campaign':
                        # Check if already in list
                        campaign_id = disc.get('promotion_id')
                        if not any(c.get('campaign_id') == campaign_id for c in eligible_campaigns):
                            eligible_campaigns.append({
                                'campaign_id': campaign_id,
                                'campaign_code': disc.get('campaign_code', disc.get('name', '')),
                                'campaign_name': disc.get('campaign_name', disc.get('name', 'Campaign')),
                                'discount_type': 'percentage',
                                'discount_value': disc.get('percent', 0),
                                'applied': disc.get('applied', False),
                                'reason': disc.get('reason', ''),
                                'end_date': disc.get('end_date', '')
                            })

            return jsonify({
                'success': True,
                'line_items': discounted_items,
                'summary': {
                    # Service summary
                    'total_services': total_service_count,
                    'service_discount_eligible': total_service_count >= min_threshold,
                    'services_needed': max(0, min_threshold - total_service_count),

                    # Medicine summary
                    'total_medicines': total_medicine_count,
                    'medicine_discount_eligible': total_medicine_count >= min_threshold,
                    'medicines_needed': max(0, min_threshold - total_medicine_count),

                    # Combined summary
                    'bulk_discount_threshold': min_threshold,
                    'total_original_price': round(total_original_price, 2),
                    'line_item_discount': round(line_item_discount, 2),  # Added 2025-11-29
                    'subtotal_after_line_discounts': round(subtotal_after_line_discounts, 2),  # Added 2025-11-29
                    'total_discount': round(total_discount, 2),
                    'bulk_discount_amount': round(bulk_discount_amount, 2),
                    'loyalty_discount_amount': round(loyalty_discount_amount, 2),
                    'total_final_price': round(total_final_price, 2),
                    'discount_percentage': round((total_discount / total_original_price * 100), 2) if total_original_price > 0 else 0,

                    # Invoice-level discounts (Added 2025-11-29)
                    'invoice_level_discounts': {
                        'vip_discount_percent': vip_discount_percent,
                        'vip_discount_amount': round(vip_discount_amount, 2),
                        'vip_stacking_mode': vip_stacking_mode,  # 'absolute' or 'incremental'
                        'staff_discretionary_percent': staff_discretionary_percent,
                        'staff_discretionary_amount': round(staff_discretionary_amount, 2),
                        'total_invoice_discount': round(invoice_level_discount, 2)
                    },

                    # Potential savings by type
                    'potential_savings_services': potential_savings_services,
                    'potential_savings_medicines': potential_savings_medicines
                },
                'eligible_campaigns': eligible_campaigns  # Added 2025-11-29
            })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def calculate_potential_savings(
    session: Session,
    hospital_id: str,
    patient_id: str,
    current_items: List[Dict],
    min_count: int,
    item_type: str = 'Service'
) -> Dict:
    """
    Calculate potential savings if user adds more services or medicines

    Args:
        session: Database session
        hospital_id: Hospital ID
        patient_id: Patient ID
        current_items: Current line items (services or medicines)
        min_count: Minimum quantity threshold
        item_type: 'Service' or 'Medicine'
    """
    # Count total quantity, not just line items
    current_count = sum(int(item.get('quantity', 1)) for item in current_items)

    if current_count >= min_count:
        # Already eligible, no potential savings
        return {
            'applicable': False,
            'message': f'Bulk discount already applied for {item_type.lower()}s'
        }

    # Calculate how much they could save if they add more items
    items_needed = min_count - current_count

    # Estimate potential savings based on current average item price
    if current_items:
        avg_price = sum(
            float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
            for item in current_items
        ) / current_count

        # Estimate discount (assume 10% average)
        current_total = sum(
            float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
            for item in current_items
        )

        # Get actual discount percentages from Service or Medicine model
        total_potential_discount = 0
        for item in current_items:
            item_id = item.get('service_id') or item.get('medicine_id') or item.get('item_id')
            if item_id:
                if item_type == 'Service':
                    entity = session.query(Service).filter_by(service_id=item_id).first()
                else:  # Medicine
                    from app.models.master import Medicine
                    entity = session.query(Medicine).filter_by(medicine_id=item_id).first()

                if entity and entity.bulk_discount_percent:
                    item_total = float(item.get('unit_price', 0)) * int(item.get('quantity', 1))
                    item_discount = (item_total * float(entity.bulk_discount_percent)) / 100
                    total_potential_discount += item_discount

        item_name_plural = item_type.lower() + 's'
        item_name_singular = item_type.lower()

        return {
            'applicable': True,
            'items_needed': items_needed,
            'estimated_savings': round(total_potential_discount, 2),
            'estimated_additional_spend': round(avg_price * items_needed, 2),
            'message': f'Add {items_needed} more {item_name_singular}{"s" if items_needed > 1 else ""} to save ₹{total_potential_discount:,.0f}'
        }

    return {
        'applicable': True,
        'items_needed': items_needed,
        'message': f'Add {items_needed} more {item_type.lower()}{"s" if items_needed > 1 else ""} to unlock bulk discount'
    }


@discount_bp.route('/patient-loyalty/<patient_id>', methods=['GET'])
def get_patient_loyalty(patient_id: str):
    """
    Get patient's loyalty card information
    """
    try:
        with get_db_session() as session:
            # Get patient's active loyalty wallet
            patient_wallet = session.query(PatientLoyaltyWallet).join(
                LoyaltyCardType, PatientLoyaltyWallet.card_type_id == LoyaltyCardType.card_type_id
            ).filter(
                PatientLoyaltyWallet.patient_id == patient_id,
                PatientLoyaltyWallet.wallet_status == 'active',
                PatientLoyaltyWallet.is_active == True,
                LoyaltyCardType.is_active == True
            ).first()

            if not patient_wallet:
                return jsonify({
                    'success': True,
                    'has_loyalty_card': False,
                    'message': 'No active loyalty wallet'
                })

            card_type = patient_wallet.card_type

            return jsonify({
                'success': True,
                'has_loyalty_card': True,
                'card': {
                    'wallet_id': str(patient_wallet.wallet_id),
                    'card_type_name': card_type.card_type_name,
                    'card_type_code': card_type.card_type_code,
                    'discount_percent': float(card_type.discount_percent),
                    'card_color': card_type.card_color,
                    'points_balance': patient_wallet.points_balance,
                    'wallet_status': patient_wallet.wallet_status
                }
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================================================
# SAVINGS TIPS ENDPOINT (Added Nov 22, 2025)
# ========================================================================

@discount_bp.route('/savings-tips', methods=['GET'])
def get_savings_tips():
    """
    Get personalized savings tips for the patient
    Shows opportunities for bulk discounts, loyalty membership, and promotions

    Query Parameters:
        patient_id (str): Patient ID
        current_cart_value (float): Current invoice total
        service_count (int): Number of services in cart

    Returns:
        JSON with savings tips
    """
    try:
        patient_id = request.args.get('patient_id')
        current_cart_value = float(request.args.get('current_cart_value', 0))
        service_count = int(request.args.get('service_count', 0))

        tips = {}

        with get_db_session() as session:
            # Tip 1: Bulk Discount Opportunity
            bulk_threshold = 5
            bulk_discount_percent = 10

            if service_count > 0 and service_count < bulk_threshold:
                services_needed = bulk_threshold - service_count
                potential_savings = (current_cart_value * bulk_discount_percent) / 100

                tips['bulk_discount_tip'] = {
                    'services_needed': services_needed,
                    'potential_savings': float(potential_savings),
                    'threshold': bulk_threshold,
                    'discount_percent': bulk_discount_percent
                }

            # Tip 2: Loyalty Wallet Opportunity
            if patient_id:
                patient_wallet = session.query(PatientLoyaltyWallet).filter_by(
                    patient_id=patient_id,
                    wallet_status='active',
                    is_active=True
                ).first()

                if not patient_wallet:
                    # Patient doesn't have a loyalty wallet
                    tips['loyalty_tip'] = {
                        'show': True,
                        'membership_type': 'Gold',
                        'discount_percent': 5,
                        'annual_fee': 2000,
                        'estimated_savings': 5000
                    }

            # Tip 3: Available Promotions
            from app.models.master import PromotionCampaign
            from datetime import date

            active_promotions = session.query(PromotionCampaign).filter(
                PromotionCampaign.is_active == True,
                PromotionCampaign.start_date <= date.today(),
                PromotionCampaign.end_date >= date.today()
            ).limit(3).all()

            if active_promotions:
                tips['available_promotions'] = []
                for promo in active_promotions:
                    # Parse promotion rules to determine trigger condition
                    trigger_condition = "Check with staff"
                    if promo.promotion_rules and 'trigger' in promo.promotion_rules:
                        trigger_data = promo.promotion_rules['trigger']
                        if trigger_data.get('type') == 'item_purchase':
                            conditions = trigger_data.get('conditions', {})
                            min_amount = conditions.get('min_amount')
                            if min_amount:
                                remaining = max(0, min_amount - current_cart_value)
                                if remaining > 0:
                                    trigger_condition = f"Add Rs.{remaining} more to qualify"
                                else:
                                    trigger_condition = "You qualify!"

                    tips['available_promotions'].append({
                        'name': promo.campaign_name,
                        'description': promo.description or 'Special promotional offer',
                        'trigger_condition': trigger_condition
                    })

        return jsonify(tips), 200

    except Exception as e:
        logger.error(f"Error getting savings tips: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500
