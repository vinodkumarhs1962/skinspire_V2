"""
Discount Service - Handles all discount calculations for services
Supports bulk discounts, loyalty discounts, and campaign-based discounts
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import logging

logger = logging.getLogger(__name__)

from app.models.master import (
    Service, Hospital, Medicine, Package, LoyaltyCardType,
    DiscountApplicationLog, PromotionCampaign, PromotionUsageLog, Patient,
    PromotionCampaignGroup, PromotionGroupItem
)
from app.models.transaction import PatientLoyaltyWallet
# NOTE: CampaignHookConfig removed - now using promotion_campaigns table for all promotions
# NOTE: PatientLoyaltyCard removed - now using PatientLoyaltyWallet from NEW wallet system


class DiscountCalculationResult:
    """Data class to hold discount calculation results"""
    def __init__(
        self,
        discount_type: str,  # 'bulk', 'loyalty', 'promotion', 'standard', 'none'
        discount_percent: Decimal,
        discount_amount: Decimal,
        final_price: Decimal,
        original_price: Decimal,
        metadata: Dict = None,
        card_type_id: str = None,
        promotion_id: str = None  # RENAMED from campaign_hook_id
    ):
        self.discount_type = discount_type
        self.discount_percent = discount_percent
        self.discount_amount = discount_amount
        self.final_price = final_price
        self.original_price = original_price
        self.metadata = metadata or {}
        self.card_type_id = card_type_id
        self.promotion_id = promotion_id  # RENAMED from campaign_hook_id

    def to_dict(self) -> Dict:
        """Convert to dictionary for easy serialization"""
        return {
            'discount_type': self.discount_type,
            'discount_percent': float(self.discount_percent),
            'discount_amount': float(self.discount_amount),
            'final_price': float(self.final_price),
            'original_price': float(self.original_price),
            'metadata': self.metadata,
            'card_type_id': str(self.card_type_id) if self.card_type_id else None,
            'promotion_id': str(self.promotion_id) if self.promotion_id else None  # RENAMED
        }


class DiscountService:
    """Service class for handling all discount-related calculations"""

    @staticmethod
    def calculate_bulk_discount(
        session: Session,
        hospital_id: str,
        service_id: str,
        total_service_count: int,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate bulk service discount based on hospital policy and service configuration

        Args:
            session: Database session
            hospital_id: Hospital ID
            service_id: Service ID
            total_service_count: Total number of services in the invoice
            unit_price: Unit price of the service
            quantity: Quantity of this service

        Returns:
            DiscountCalculationResult if bulk discount applies, None otherwise
        """
        # Get hospital bulk discount policy
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital or not hospital.bulk_discount_enabled:
            return None

        # Check if service count meets minimum threshold
        if total_service_count < hospital.bulk_discount_min_service_count:
            return None

        # Check if policy is effective (date-based)
        if hospital.bulk_discount_effective_from:
            if date.today() < hospital.bulk_discount_effective_from:
                return None

        # Get service bulk discount percentage
        service = session.query(Service).filter_by(service_id=service_id).first()
        if not service:
            return None

        # Check if service is eligible for bulk discount (Added 2025-11-27)
        if not getattr(service, 'bulk_discount_eligible', True):
            # If bulk_discount_eligible is explicitly False, skip
            # Default to True for backward compatibility if field doesn't exist
            if hasattr(service, 'bulk_discount_eligible') and not service.bulk_discount_eligible:
                return None

        if not service.bulk_discount_percent or service.bulk_discount_percent == 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_percent = service.bulk_discount_percent
        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='bulk',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            metadata={
                'service_count': total_service_count,
                'min_threshold': hospital.bulk_discount_min_service_count,
                'service_name': service.service_name
            }
        )

    @staticmethod
    def calculate_medicine_bulk_discount(
        session: Session,
        hospital_id: str,
        medicine_id: str,
        total_medicine_count: int,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate bulk medicine discount based on hospital policy and medicine configuration

        Args:
            session: Database session
            hospital_id: Hospital ID
            medicine_id: Medicine ID
            total_medicine_count: Total number of medicines in the invoice
            unit_price: Unit price of the medicine
            quantity: Quantity of this medicine

        Returns:
            DiscountCalculationResult if bulk discount applies, None otherwise
        """
        # Get hospital bulk discount policy
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital or not hospital.bulk_discount_enabled:
            return None

        # Check if medicine count meets minimum threshold
        # Using same threshold as services for consistency
        if total_medicine_count < hospital.bulk_discount_min_service_count:
            return None

        # Check if policy is effective (date-based)
        if hospital.bulk_discount_effective_from:
            if date.today() < hospital.bulk_discount_effective_from:
                return None

        # Get medicine bulk discount percentage
        medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
        if not medicine:
            return None

        # Check if medicine is eligible for bulk discount (Added 2025-11-27)
        if hasattr(medicine, 'bulk_discount_eligible') and not medicine.bulk_discount_eligible:
            return None

        if not medicine.bulk_discount_percent or medicine.bulk_discount_percent == 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_percent = medicine.bulk_discount_percent

        # Apply max_discount cap if set
        if medicine.max_discount is not None and discount_percent > medicine.max_discount:
            discount_percent = medicine.max_discount
            logger.info(f"Medicine {medicine.medicine_name} bulk discount capped at max_discount: {medicine.max_discount}%")

        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='bulk',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            metadata={
                'medicine_count': total_medicine_count,
                'min_threshold': hospital.bulk_discount_min_service_count,
                'medicine_name': medicine.medicine_name
            }
        )

    @staticmethod
    def calculate_bulk_discount_simulation(
        session: Session,
        hospital_id: str,
        item_type: str,  # 'Service' or 'Medicine'
        item_id: str,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate bulk discount for SIMULATION mode.

        Unlike calculate_bulk_discount(), this does NOT check actual quantities.
        It assumes the item is eligible if it has bulk_discount_percent > 0.

        Used by promotion dashboard to show potential savings.

        Args:
            session: Database session
            hospital_id: Hospital ID
            item_type: 'Service' or 'Medicine'
            item_id: Item ID
            unit_price: Unit price of the item
            quantity: Quantity of this item

        Returns:
            DiscountCalculationResult if item has bulk_discount_percent configured
            None if item doesn't have bulk discount configured
        """
        # Check if bulk discount is enabled at hospital level
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital or not hospital.bulk_discount_enabled:
            return None

        # Get the item based on type (case-insensitive)
        item = None
        item_name = None
        item_type_normalized = item_type.title() if item_type else ''

        if item_type_normalized == 'Service':
            item = session.query(Service).filter_by(service_id=item_id).first()
            item_name = item.service_name if item else None
        elif item_type_normalized == 'Medicine':
            item = session.query(Medicine).filter_by(medicine_id=item_id).first()
            item_name = item.medicine_name if item else None
        else:
            return None  # Packages don't support bulk discount

        if not item:
            return None

        # Check if item has bulk discount configured
        if not hasattr(item, 'bulk_discount_percent') or not item.bulk_discount_percent:
            return None

        if item.bulk_discount_percent == 0:
            return None

        # Check bulk_discount_eligible flag if exists
        if hasattr(item, 'bulk_discount_eligible') and not item.bulk_discount_eligible:
            return None

        # Calculate discount (assuming eligible)
        original_price = unit_price * quantity
        discount_percent = item.bulk_discount_percent

        # Apply max_discount cap if set
        if hasattr(item, 'max_discount') and item.max_discount is not None:
            if discount_percent > item.max_discount:
                discount_percent = item.max_discount

        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='bulk',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            metadata={
                'item_type': item_type,
                'item_name': item_name,
                'min_threshold': hospital.bulk_discount_min_service_count,
                'simulation': True,  # Flag to indicate this is simulated
                'reason': f'Requires min {hospital.bulk_discount_min_service_count} items'
            }
        )

    @staticmethod
    def calculate_standard_discount(
        session: Session,
        item_type: str,  # 'Service', 'Medicine', 'Package'
        item_id: str,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate standard discount for an item (fallback discount)

        Business Rules:
        - Only applies when no other discounts are active
        - Reads item.standard_discount_percent from Service/Medicine/Package model
        - Applies max_discount cap if set
        - Priority: 4 (lowest)

        Args:
            session: Database session
            item_type: Type of item ('Service', 'Medicine', 'Package')
            item_id: Item ID (service_id, medicine_id, or package_id)
            unit_price: Unit price of the item
            quantity: Quantity of this item

        Returns:
            DiscountCalculationResult if item has standard_discount_percent > 0
            None if no standard discount configured
        """
        # Get the item based on type
        item = None
        item_name = None

        if item_type == 'Service':
            item = session.query(Service).filter_by(service_id=item_id).first()
            item_name = item.service_name if item else None
        elif item_type == 'Medicine':
            item = session.query(Medicine).filter_by(medicine_id=item_id).first()
            item_name = item.medicine_name if item else None
        elif item_type == 'Package':
            item = session.query(Package).filter_by(package_id=item_id).first()
            item_name = item.package_name if item else None
        else:
            logger.warning(f"Unknown item_type: {item_type}")
            return None

        if not item:
            logger.warning(f"{item_type} not found: {item_id}")
            return None

        # Check if item has standard_discount_percent configured
        if not hasattr(item, 'standard_discount_percent') or not item.standard_discount_percent:
            return None

        if item.standard_discount_percent == 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_percent = item.standard_discount_percent

        # Apply max_discount cap if set
        if hasattr(item, 'max_discount') and item.max_discount is not None:
            if discount_percent > item.max_discount:
                discount_percent = item.max_discount
                logger.info(f"{item_type} {item_name} standard discount capped at max_discount: {item.max_discount}%")

        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='standard',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            metadata={
                'item_type': item_type,
                'item_name': item_name,
                'priority': 4  # Lowest priority
            }
        )

    @staticmethod
    def calculate_loyalty_percentage_discount(
        session: Session,
        hospital_id: str,
        patient_id: str,
        item_type: str,  # 'Service', 'Medicine', 'Package'
        item_id: str,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate loyalty percentage discount for patients with active loyalty cards

        Business Rules:
        - Requires patient to have active loyalty card
        - Uses card_type.discount_percent (card-level, published discount)
        - Same discount applies to ALL services/medicines for the card type
        - Priority: 2 (medium-high)
        - Can combine with bulk discount based on hospital.loyalty_discount_mode

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            item_type: Type of item ('Service', 'Medicine', 'Package')
            item_id: Item ID (service_id, medicine_id, or package_id)
            unit_price: Unit price of the item
            quantity: Quantity of this item

        Returns:
            DiscountCalculationResult if patient has loyalty card with discount configured
            None if patient doesn't have loyalty card or card has no discount
        """
        # Check if patient has active loyalty wallet
        patient_wallet = session.query(PatientLoyaltyWallet).join(
            LoyaltyCardType, PatientLoyaltyWallet.card_type_id == LoyaltyCardType.card_type_id
        ).filter(
            and_(
                PatientLoyaltyWallet.patient_id == patient_id,
                PatientLoyaltyWallet.hospital_id == hospital_id,
                PatientLoyaltyWallet.wallet_status == 'active',
                PatientLoyaltyWallet.is_active == True,
                LoyaltyCardType.is_active == True,
                LoyaltyCardType.is_deleted == False
            )
        ).first()

        if not patient_wallet or not patient_wallet.card_type:
            return None

        card_type = patient_wallet.card_type

        # Use card type's discount_percent (published, same for all items)
        if not card_type.discount_percent or card_type.discount_percent == 0:
            return None

        # Get item name for metadata (optional, for logging/display)
        item_name = None
        if item_type == 'Service':
            item = session.query(Service).filter_by(service_id=item_id).first()
            item_name = item.service_name if item else None
        elif item_type == 'Medicine':
            item = session.query(Medicine).filter_by(medicine_id=item_id).first()
            item_name = item.medicine_name if item else None
        elif item_type == 'Package':
            item = session.query(Package).filter_by(package_id=item_id).first()
            item_name = item.package_name if item else None

        # Calculate discount using card type's discount_percent
        original_price = unit_price * quantity
        discount_percent = Decimal(str(card_type.discount_percent))

        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        logger.info(f"Loyalty discount: {card_type.card_type_name} card gives {discount_percent}% off")

        return DiscountCalculationResult(
            discount_type='loyalty',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            card_type_id=card_type.card_type_id,
            metadata={
                'item_type': item_type,
                'item_name': item_name,
                'card_type_code': card_type.card_type_code,
                'card_type_name': card_type.card_type_name,
                'wallet_id': str(patient_wallet.wallet_id),
                'priority': 2  # Medium-high priority
            }
        )

    @staticmethod
    def calculate_vip_discount(
        session: Session,
        hospital_id: str,
        patient_id: str,
        item_type: str,  # 'Service', 'Medicine', 'Package'
        item_id: str,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate VIP discount for patients marked as VIP or Special Group.

        IMPORTANT: VIP discounts should be created as CAMPAIGNS with target_special_group=True.
        This method is kept for backward compatibility but VIP campaigns are the preferred approach.

        Business Rules:
        - Patient must be marked as VIP (is_vip=True) or Special Group (is_special_group=True)
        - VIP discount percent comes from VIP-targeted campaigns (preferred) or legacy item-level settings
        - Priority: Configured in stacking_config (can be exclusive, incremental, or absolute)

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            item_type: Type of item ('Service', 'Medicine', 'Package')
            item_id: Item ID
            unit_price: Unit price of the item
            quantity: Quantity of this item

        Returns:
            DiscountCalculationResult if VIP discount applies, None otherwise
        """
        if not patient_id:
            return None

        # Check if patient is VIP or Special Group
        patient = session.query(Patient).filter_by(patient_id=patient_id).first()
        if not patient:
            return None

        # Check VIP status (is_vip or is_special_group flag)
        is_vip = getattr(patient, 'is_vip', False) or getattr(patient, 'is_special_group', False)
        if not is_vip:
            return None

        # VIP discount percent should come from VIP-targeted campaigns
        # This legacy method only checks item-level or patient-level VIP percent
        vip_discount_percent = None

        # 1. Check patient-level VIP discount (legacy)
        if hasattr(patient, 'vip_discount_percent') and patient.vip_discount_percent:
            vip_discount_percent = Decimal(str(patient.vip_discount_percent))

        # 2. Check item-level VIP discount (legacy)
        if vip_discount_percent is None or vip_discount_percent == 0:
            item = None
            if item_type == 'Service':
                item = session.query(Service).filter_by(service_id=item_id).first()
            elif item_type == 'Medicine':
                item = session.query(Medicine).filter_by(medicine_id=item_id).first()
            elif item_type == 'Package':
                item = session.query(Package).filter_by(package_id=item_id).first()

            if item and hasattr(item, 'vip_discount_percent') and item.vip_discount_percent:
                vip_discount_percent = Decimal(str(item.vip_discount_percent))

        # If no VIP discount configured, return None
        # Note: VIP campaigns are handled separately in get_best_discount_multi
        if not vip_discount_percent or vip_discount_percent <= 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_amount = (original_price * vip_discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='vip',
            discount_percent=vip_discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            metadata={
                'item_type': item_type,
                'patient_id': str(patient_id),
                'is_vip': getattr(patient, 'is_vip', False),
                'is_special_group': getattr(patient, 'is_special_group', False),
                'priority': 'Configured in stacking_config'
            }
        )

    @staticmethod
    def calculate_loyalty_discount(
        session: Session,
        hospital_id: str,
        patient_id: str,
        service_id: str,
        unit_price: Decimal,
        quantity: int = 1
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate loyalty card discount for a patient

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            service_id: Service ID
            unit_price: Unit price of the service
            quantity: Quantity of this service

        Returns:
            DiscountCalculationResult if loyalty discount applies, None otherwise
        """
        # Get patient's active loyalty wallet
        patient_wallet = session.query(PatientLoyaltyWallet).join(
            LoyaltyCardType, PatientLoyaltyWallet.card_type_id == LoyaltyCardType.card_type_id
        ).filter(
            and_(
                PatientLoyaltyWallet.patient_id == patient_id,
                PatientLoyaltyWallet.hospital_id == hospital_id,
                PatientLoyaltyWallet.wallet_status == 'active',
                PatientLoyaltyWallet.is_active == True,
                LoyaltyCardType.is_active == True,
                LoyaltyCardType.is_deleted == False
            )
        ).first()

        if not patient_wallet or not patient_wallet.card_type:
            return None

        # Get discount percent from card_type
        card_type = patient_wallet.card_type
        if not card_type.discount_percent or card_type.discount_percent == 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_percent = Decimal(str(card_type.discount_percent))  # Keep as Decimal
        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='loyalty',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            card_type_id=card_type.card_type_id,
            metadata={
                'card_type_code': card_type.card_type_code,
                'card_type_name': card_type.card_type_name,
                'wallet_id': str(patient_wallet.wallet_id)
            }
        )

    # NOTE: calculate_campaign_discount() removed - replaced by calculate_promotion_discount()
    # Old campaign hooks system deprecated in favor of database-driven promotion_campaigns table

    @staticmethod
    def calculate_promotion_discount(
        session: Session,
        hospital_id: str,
        patient_id: str,
        item_type: str,  # 'Service', 'Medicine', 'Package'
        item_id: str,
        unit_price: Decimal,
        quantity: int = 1,
        invoice_date: date = None,
        invoice_items: List[Dict] = None  # NEW: Full invoice context for buy_x_get_y
    ) -> Optional[DiscountCalculationResult]:
        """
        Calculate promotion/campaign discount from promotion_campaigns table

        Business Rules:
        - Checks for active promotions applicable to this item
        - Can be fixed_amount OR percentage discount
        - Enforces campaign constraints (dates, usage limits, min purchase)
        - Priority: 1 (highest)
        - Tracks usage in promotion_usage_log

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            item_type: Type of item ('Service', 'Medicine', 'Package')
            item_id: Item ID (service_id, medicine_id, or package_id)
            unit_price: Unit price of the item
            quantity: Quantity of this item
            invoice_date: Invoice date (defaults to today)

        Returns:
            DiscountCalculationResult if promotion applies
            None if no active promotion found
        """
        if invoice_date is None:
            invoice_date = date.today()

        # Get active promotions applicable to this item type
        # NOTE: Personalized promotions (is_personalized=True) are excluded from auto-apply
        # They require manual code entry by staff at billing counter
        promotions = session.query(PromotionCampaign).filter(
            and_(
                PromotionCampaign.hospital_id == hospital_id,
                PromotionCampaign.is_active == True,
                PromotionCampaign.is_deleted == False,
                PromotionCampaign.is_personalized == False,  # Skip personalized promos - require manual entry
                PromotionCampaign.status == 'approved',  # Only approved promotions
                PromotionCampaign.start_date <= invoice_date,
                PromotionCampaign.end_date >= invoice_date,
                or_(
                    PromotionCampaign.applies_to == 'all',
                    PromotionCampaign.applies_to == item_type.lower() + 's'  # 'services', 'medicines', 'packages'
                )
            )
        ).all()

        if not promotions:
            return None

        # Check if patient is in special group (Added 2025-11-27)
        patient_is_special_group = False
        if patient_id:
            patient = session.query(Patient).filter_by(patient_id=patient_id).first()
            if patient and hasattr(patient, 'is_special_group'):
                patient_is_special_group = patient.is_special_group

        # Check each promotion for eligibility
        for promotion in promotions:
            # Check special group targeting (Added 2025-11-27)
            if hasattr(promotion, 'target_special_group') and promotion.target_special_group:
                # This promotion only applies to special group patients
                if not patient_is_special_group:
                    continue  # Skip - patient is not in special group
            # NEW: Dispatch based on promotion_type
            if promotion.promotion_type == 'buy_x_get_y':
                # Handle Buy X Get Y promotions
                if invoice_items is None:
                    logger.debug(f"Skipping buy_x_get_y promotion {promotion.campaign_name} - no invoice context provided")
                    continue  # Need invoice context for buy_x_get_y

                # Check if campaign targets specific groups (Added 2025-11-28)
                if promotion.target_groups:
                    target_group_ids = promotion.target_groups.get('group_ids', [])
                    if target_group_ids:
                        # Check if item belongs to any of the target groups
                        item_in_group = session.query(PromotionGroupItem).join(
                            PromotionCampaignGroup,
                            PromotionGroupItem.group_id == PromotionCampaignGroup.group_id
                        ).filter(
                            PromotionCampaignGroup.is_active == True,
                            PromotionGroupItem.group_id.in_(target_group_ids),
                            PromotionGroupItem.item_type == item_type.lower(),
                            PromotionGroupItem.item_id == item_id
                        ).first()

                        if not item_in_group:
                            continue  # Item not in any target group

                result = DiscountService.handle_buy_x_get_y(
                    session=session,
                    promotion=promotion,
                    invoice_items=invoice_items,
                    current_item_type=item_type,
                    current_item_id=item_id,
                    unit_price=unit_price,
                    quantity=quantity
                )
                if result:
                    return result

            elif promotion.promotion_type == 'simple_discount' or promotion.promotion_type is None:
                # Handle simple discount promotions (original logic)

                # Check if campaign targets specific groups (Added 2025-11-28)
                if promotion.target_groups:
                    target_group_ids = promotion.target_groups.get('group_ids', [])
                    if target_group_ids:
                        # Check if item belongs to any of the target groups
                        item_in_group = session.query(PromotionGroupItem).join(
                            PromotionCampaignGroup,
                            PromotionGroupItem.group_id == PromotionCampaignGroup.group_id
                        ).filter(
                            PromotionCampaignGroup.is_active == True,
                            PromotionGroupItem.group_id.in_(target_group_ids),
                            PromotionGroupItem.item_type == item_type.lower(),
                            PromotionGroupItem.item_id == item_id
                        ).first()

                        if not item_in_group:
                            continue  # Item not in any target group

                # Check if specific items list (if set) - for fine-grained override
                if promotion.specific_items:
                    specific_item_ids = promotion.specific_items.get('item_ids', [])
                    if specific_item_ids and item_id not in specific_item_ids:
                        continue  # This promotion doesn't apply to this specific item

                # Check max total uses
                if promotion.max_total_uses and promotion.current_uses >= promotion.max_total_uses:
                    continue  # Campaign usage limit reached

                # Check max uses per patient
                if promotion.max_uses_per_patient:
                    patient_usage_count = session.query(PromotionUsageLog).filter(
                        and_(
                            PromotionUsageLog.campaign_id == promotion.campaign_id,
                            PromotionUsageLog.patient_id == patient_id
                        )
                    ).count()
                    if patient_usage_count >= promotion.max_uses_per_patient:
                        continue  # Patient has reached usage limit for this campaign

                # Calculate discount
                original_price = unit_price * quantity

                if promotion.discount_type == 'percentage':
                    discount_percent = promotion.discount_value
                    discount_amount = (original_price * discount_percent) / 100
                elif promotion.discount_type == 'fixed_amount':
                    discount_amount = promotion.discount_value
                    discount_percent = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0')
                else:
                    logger.warning(f"Unknown promotion discount type: {promotion.discount_type}")
                    continue

                # Apply max_discount_amount cap if set
                if promotion.max_discount_amount and discount_amount > promotion.max_discount_amount:
                    discount_amount = promotion.max_discount_amount
                    discount_percent = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0')

                final_price = original_price - discount_amount

                # This promotion is eligible - return it (highest priority)
                return DiscountCalculationResult(
                    discount_type='promotion',
                    discount_percent=discount_percent,
                    discount_amount=discount_amount,
                    final_price=final_price,
                    original_price=original_price,
                    promotion_id=str(promotion.campaign_id),  # RENAMED from campaign_hook_id
                    metadata={
                        'promotion_type': 'simple_discount',
                        'item_type': item_type,
                        'campaign_id': str(promotion.campaign_id),
                        'campaign_name': promotion.campaign_name,
                        'campaign_code': promotion.campaign_code,
                        'discount_type': promotion.discount_type,
                        'discount_value': float(promotion.discount_value),
                        'priority': 1,  # Highest priority
                        'auto_applied': promotion.auto_apply,
                        'end_date': promotion.end_date.strftime('%d-%b-%Y') if promotion.end_date else ''
                    }
                )

            # TODO: Future promotion types (tiered_discount, bundle) can be added here
            else:
                logger.warning(f"Unknown promotion_type: {promotion.promotion_type} for campaign {promotion.campaign_name}")

        # No eligible promotion found
        return None

    @staticmethod
    def handle_buy_x_get_y(
        session: Session,
        promotion: PromotionCampaign,
        invoice_items: List[Dict],
        current_item_type: str,
        current_item_id: str,
        unit_price: Decimal,
        quantity: int
    ) -> Optional[DiscountCalculationResult]:
        """
        Handle Buy X Get Y Free promotions

        Logic:
        1. Parse promotion_rules JSON
        2. Check if trigger condition is met (invoice contains X)
        3. Check if current item is the reward item (Y)
        4. If yes, return discount (usually 100% for "free")

        Args:
            session: Database session
            promotion: PromotionCampaign object with buy_x_get_y type
            invoice_items: Full invoice line items for checking trigger
            current_item_type: Type of current item being evaluated
            current_item_id: ID of current item being evaluated
            unit_price: Unit price of current item
            quantity: Quantity of current item

        Returns:
            DiscountCalculationResult if this is a reward item and trigger is met
            None otherwise
        """
        rules = promotion.promotion_rules
        if not rules:
            logger.warning(f"Promotion {promotion.campaign_name} has no promotion_rules")
            return None

        trigger = rules.get('trigger', {})
        reward = rules.get('reward', {})

        # Step 1: Check if trigger condition is met
        trigger_met = False

        if trigger.get('type') == 'item_purchase':
            conditions = trigger.get('conditions', {})
            trigger_item_ids = conditions.get('item_ids', [])
            trigger_item_type = conditions.get('item_type')
            min_amount = Decimal(str(conditions.get('min_amount', 0)))
            min_quantity = int(conditions.get('min_quantity', 0))

            # Check each item in invoice to see if trigger condition is met
            for item in invoice_items:
                item_id = item.get('item_id') or item.get('service_id') or item.get('medicine_id') or item.get('package_id')
                item_type = item.get('item_type')

                # Check if item type matches
                if trigger_item_type and item_type != trigger_item_type:
                    continue

                # Check if specific item_ids required (if list is not empty)
                if trigger_item_ids and item_id not in trigger_item_ids:
                    continue

                # Calculate item total
                item_unit_price = Decimal(str(item.get('unit_price', 0)))
                item_quantity = int(item.get('quantity', 1))
                item_total = item_unit_price * item_quantity

                # Check if minimum amount requirement met
                if min_amount > 0 and item_total >= min_amount:
                    trigger_met = True
                    logger.info(f"Buy X Get Y trigger met: {item_type} item_id={item_id} amount={item_total} >= {min_amount}")
                    break

                # Check if minimum quantity requirement met
                if min_quantity > 0 and item_quantity >= min_quantity:
                    trigger_met = True
                    logger.info(f"Buy X Get Y trigger met: {item_type} item_id={item_id} quantity={item_quantity} >= {min_quantity}")
                    break

                # If no min_amount or min_quantity specified, just matching item type/id is enough
                if min_amount == 0 and min_quantity == 0:
                    trigger_met = True
                    logger.info(f"Buy X Get Y trigger met: {item_type} item_id={item_id} (no amount/quantity requirement)")
                    break

        if not trigger_met:
            return None

        # Step 2: Check if current item is a reward item
        reward_items = reward.get('items', [])
        for reward_item in reward_items:
            if (reward_item.get('item_id') == current_item_id and
                reward_item.get('item_type') == current_item_type):

                # Calculate discount (usually 100% for "free")
                discount_percent = Decimal(str(reward_item.get('discount_percent', 100)))
                original_price = unit_price * quantity
                discount_amount = (original_price * discount_percent) / 100
                final_price = original_price - discount_amount

                logger.info(f"Buy X Get Y reward applied: {current_item_type} {current_item_id} - {discount_percent}% off (campaign: {promotion.campaign_name})")

                return DiscountCalculationResult(
                    discount_type='promotion',
                    discount_percent=discount_percent,
                    discount_amount=discount_amount,
                    final_price=final_price,
                    original_price=original_price,
                    promotion_id=str(promotion.campaign_id),
                    metadata={
                        'promotion_type': 'buy_x_get_y',
                        'campaign_id': str(promotion.campaign_id),
                        'campaign_name': promotion.campaign_name,
                        'campaign_code': promotion.campaign_code,
                        'trigger_met': True,
                        'reward_item': True,
                        'priority': 1
                    }
                )

        # Current item is not a reward item
        return None

    @staticmethod
    def get_best_discount(
        session: Session,
        hospital_id: str,
        service_id: str,
        patient_id: str,
        unit_price: Decimal,
        quantity: int,
        total_service_count: int,
        invoice_date: date = None
    ) -> DiscountCalculationResult:
        """
        Calculate all applicable discounts and return the best one

        Args:
            session: Database session
            hospital_id: Hospital ID
            service_id: Service ID
            patient_id: Patient ID
            unit_price: Unit price of the service
            quantity: Quantity of this service
            total_service_count: Total services in invoice (for bulk discount)
            invoice_date: Invoice date (defaults to today)

        Returns:
            DiscountCalculationResult with the best discount (or no discount)
        """
        original_price = unit_price * quantity

        # Calculate all applicable discounts
        discounts = []

        # 1. Bulk discount
        bulk_discount = DiscountService.calculate_bulk_discount(
            session, hospital_id, service_id, total_service_count, unit_price, quantity
        )
        if bulk_discount:
            discounts.append(bulk_discount)

        # 2. Loyalty discount
        loyalty_discount = DiscountService.calculate_loyalty_discount(
            session, hospital_id, patient_id, service_id, unit_price, quantity
        )
        if loyalty_discount:
            discounts.append(loyalty_discount)

        # 3. Campaign discount - REMOVED (now using calculate_promotion_discount in get_best_discount_multi)
        # Old get_best_discount() kept for backward compatibility but deprecated

        # If no discounts apply, return zero discount
        if not discounts:
            return DiscountCalculationResult(
                discount_type='none',
                discount_percent=Decimal('0'),
                discount_amount=Decimal('0'),
                final_price=original_price,
                original_price=original_price,
                metadata={'reason': 'No applicable discounts found'}
            )

        # Select the discount with the highest percentage
        best_discount = max(discounts, key=lambda d: d.discount_percent)

        # Add metadata about competing discounts
        best_discount.metadata['competing_discounts'] = [
            {
                'type': d.discount_type,
                'percent': float(d.discount_percent),
                'amount': float(d.discount_amount)
            }
            for d in discounts if d.discount_type != best_discount.discount_type
        ]
        best_discount.metadata['selection_reason'] = 'Highest discount percentage'

        return best_discount

    @staticmethod
    def get_best_discount_multi(
        session: Session,
        hospital_id: str,
        patient_id: str,
        item_type: str,  # 'Service', 'Medicine', 'Package'
        item_id: str,
        unit_price: Decimal,
        quantity: int,
        total_item_count: int,  # For bulk discount eligibility
        invoice_date: date = None,
        invoice_items: List[Dict] = None,  # Full invoice context for buy_x_get_y
        exclude_bulk: bool = False,  # Staff manually unchecked bulk discount
        exclude_loyalty: bool = False,  # Staff manually unchecked loyalty discount
        exclude_standard: bool = False,  # Staff manually unchecked standard discount
        simulation_mode: bool = False,  # If True, assume bulk eligible (for dashboard simulation)
        manual_promo_code: Dict = None,  # Manually entered promo code from staff
        staff_discretionary: Dict = None,  # Staff discretionary discount - stacks incrementally (Added 2025-11-29)
        exclude_campaign: bool = False,  # Staff unchecked ALL campaign discounts (Added 2025-11-29)
        excluded_campaign_ids: List[str] = None,  # Per-campaign exclusion list
        exclude_vip: bool = False  # Staff manually unchecked VIP discount (Added 2025-11-29)
    ) -> DiscountCalculationResult:
        """
        Calculate all applicable discounts using CENTRALIZED stacking configuration.

        This is the SINGLE SOURCE OF TRUTH for discount calculation.
        Used by both Invoice (actual) and Dashboard (simulation) contexts.

        The stacking behavior is controlled by hospital's discount_stacking_config:
        - Each discount type can be: exclusive, incremental, or absolute
        - Exclusive: Only that discount applies, all others excluded
        - Incremental: Adds to total
        - Absolute: Competes with other absolutes (highest wins)

        Context Differences:
        - Invoice Mode (simulation_mode=False):
          * Bulk discount checked against actual total_item_count
          * Staff overrides (exclude_bulk, exclude_loyalty) apply
          * Staff Discretionary discount can be applied
        - Simulation Mode (simulation_mode=True):
          * Bulk discount assumed eligible if item has bulk_discount_percent > 0
          * Staff overrides ignored (no checkboxes in simulation)
          * VIP discount IS included (patient attribute)
          * Staff Discretionary is EXCLUDED (manual intervention only)

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            item_type: Type of item ('Service', 'Medicine', 'Package')
            item_id: Item ID (service_id, medicine_id, or package_id)
            unit_price: Unit price of the item
            quantity: Quantity of this item
            total_item_count: Total count of items of this type in invoice (for bulk discount)
            invoice_date: Invoice date (defaults to today)
            invoice_items: Full invoice context for buy_x_get_y
            exclude_bulk: If True, skip bulk discount (staff manually unchecked) - ignored in simulation_mode
            exclude_loyalty: If True, skip loyalty discount (staff manually unchecked) - ignored in simulation_mode
            simulation_mode: If True, assume bulk eligible and ignore staff overrides

        Returns:
            DiscountCalculationResult with the calculated discount based on stacking config
        """
        original_price = unit_price * quantity

        # Get hospital's stacking configuration
        stacking_config = DiscountService.get_stacking_config(session, hospital_id)

        # =================================================================
        # STEP 1: Calculate all individual discounts
        # =================================================================
        discount_data = {}
        all_eligible = []

        # 1. PROMOTION/CAMPAIGN DISCOUNT
        # Skip if exclude_campaign is True (Added 2025-11-29)
        # Or if specific campaign is in excluded_campaign_ids
        auto_promotion_discount = None
        if not exclude_campaign:
            # Check for automatic promotions
            auto_promotion_discount = DiscountService.calculate_promotion_discount(
                session, hospital_id, patient_id, item_type, item_id, unit_price, quantity, invoice_date,
                invoice_items=invoice_items
            )
            # Check if this specific campaign is excluded
            if auto_promotion_discount and excluded_campaign_ids:
                campaign_id = auto_promotion_discount.promotion_id
                if campaign_id and str(campaign_id) in [str(cid) for cid in excluded_campaign_ids]:
                    logger.info(f"Campaign {campaign_id} excluded by user selection")
                    auto_promotion_discount = None

        # Then, calculate manual promo code discount if provided
        manual_promotion_discount = None
        if manual_promo_code:
            logger.info(f"Processing manual promo code: {manual_promo_code.get('campaign_code')}")
            original_price = unit_price * quantity
            promo_discount_type = manual_promo_code.get('discount_type', 'percentage')
            promo_discount_value = Decimal(str(manual_promo_code.get('discount_value', 0)))

            if promo_discount_type == 'percentage':
                discount_amount = (original_price * promo_discount_value) / 100
                discount_percent = promo_discount_value
            else:
                discount_amount = promo_discount_value
                discount_percent = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0')

            manual_promotion_discount = DiscountCalculationResult(
                discount_type='promotion',
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                final_price=original_price - discount_amount,
                original_price=original_price,
                promotion_id=manual_promo_code.get('campaign_id'),
                metadata={
                    'campaign_id': manual_promo_code.get('campaign_id'),
                    'campaign_code': manual_promo_code.get('campaign_code'),
                    'campaign_name': manual_promo_code.get('campaign_code', 'Manual Promo'),
                    'discount_type': promo_discount_type,
                    'manual_entry': True
                }
            )

        # Pick the MAX discount between automatic and manual
        promotion_discount = None
        if auto_promotion_discount and manual_promotion_discount:
            if auto_promotion_discount.discount_percent >= manual_promotion_discount.discount_percent:
                promotion_discount = auto_promotion_discount
                logger.info(f"Using automatic promotion ({auto_promotion_discount.discount_percent}%) over manual ({manual_promotion_discount.discount_percent}%)")
            else:
                promotion_discount = manual_promotion_discount
                logger.info(f"Using manual promotion ({manual_promotion_discount.discount_percent}%) over automatic ({auto_promotion_discount.discount_percent}%)")
        elif auto_promotion_discount:
            promotion_discount = auto_promotion_discount
            logger.info(f"Using automatic promotion: {auto_promotion_discount.discount_percent}%")
        elif manual_promotion_discount:
            promotion_discount = manual_promotion_discount
            logger.info(f"Using manual promotion: {manual_promotion_discount.discount_percent}%")

        if promotion_discount:
            campaign_type = promotion_discount.metadata.get('discount_type', 'percentage')
            discount_data['campaign'] = {
                'percent': float(promotion_discount.discount_percent),
                'amount': float(promotion_discount.discount_amount),
                'type': campaign_type,
                'name': promotion_discount.metadata.get('campaign_name', 'Promotion Campaign'),
                'promotion_id': promotion_discount.promotion_id,
                'applicable': True
            }
            # For buy_x_get_y, use effective_percent if available
            if campaign_type == 'buy_x_get_y':
                discount_data['campaign']['effective_percent'] = promotion_discount.metadata.get('effective_percent', float(promotion_discount.discount_percent))

            all_eligible.append({
                'type': 'campaign',
                'percent': float(promotion_discount.discount_percent),
                'amount': float(promotion_discount.discount_amount),
                'campaign_name': promotion_discount.metadata.get('campaign_name', 'Promotion Campaign'),
                'campaign_code': promotion_discount.metadata.get('campaign_code', ''),
                'end_date': promotion_discount.metadata.get('end_date', ''),
                'promotion_id': promotion_discount.promotion_id
            })

        # 2. BULK DISCOUNT
        # In simulation mode: ignore exclude_bulk, assume eligible if item has bulk_discount_percent
        # In invoice mode: check actual total_item_count and respect exclude_bulk flag
        bulk_discount = None
        should_calc_bulk = simulation_mode or not exclude_bulk

        if should_calc_bulk:
            if simulation_mode:
                # Simulation: Assume eligible, calculate based on item's bulk_discount_percent
                bulk_discount = DiscountService.calculate_bulk_discount_simulation(
                    session, hospital_id, item_type, item_id, unit_price, quantity
                )
            else:
                # Invoice: Check actual quantities
                if item_type == 'Service':
                    bulk_discount = DiscountService.calculate_bulk_discount(
                        session, hospital_id, item_id, total_item_count, unit_price, quantity
                    )
                elif item_type == 'Medicine':
                    bulk_discount = DiscountService.calculate_medicine_bulk_discount(
                        session, hospital_id, item_id, total_item_count, unit_price, quantity
                    )
        elif exclude_bulk:
            logger.info(f"Bulk discount excluded by staff override for {item_type} {item_id}")

        if bulk_discount:
            discount_data['bulk'] = {
                'percent': float(bulk_discount.discount_percent),
                'amount': float(bulk_discount.discount_amount)
            }
            all_eligible.append({
                'type': 'bulk',
                'percent': float(bulk_discount.discount_percent),
                'amount': float(bulk_discount.discount_amount)
            })

        # 3. LOYALTY DISCOUNT
        # In simulation mode: ignore exclude_loyalty flag
        # In invoice mode: respect exclude_loyalty flag
        loyalty_discount = None
        should_calc_loyalty = simulation_mode or not exclude_loyalty

        if should_calc_loyalty:
            loyalty_discount = DiscountService.calculate_loyalty_percentage_discount(
                session, hospital_id, patient_id, item_type, item_id, unit_price, quantity
            )
        elif exclude_loyalty:
            logger.info(f"Loyalty discount excluded by staff override for {item_type} {item_id}")

        if loyalty_discount:
            discount_data['loyalty'] = {
                'percent': float(loyalty_discount.discount_percent),
                'amount': float(loyalty_discount.discount_amount),
                'card_type': loyalty_discount.metadata.get('card_type_name', 'Loyalty Card'),
                'card_type_id': str(loyalty_discount.card_type_id) if loyalty_discount.card_type_id else None
            }
            all_eligible.append({
                'type': 'loyalty',
                'percent': float(loyalty_discount.discount_percent),
                'amount': float(loyalty_discount.discount_amount),
                'card_type_name': loyalty_discount.metadata.get('card_type_name', 'Loyalty Card')
            })

        # 4. VIP DISCOUNT
        # Skip VIP discount if staff manually unchecked it (Added 2025-11-29)
        vip_discount = None
        if not exclude_vip:
            vip_discount = DiscountService.calculate_vip_discount(
                session, hospital_id, patient_id, item_type, item_id, unit_price, quantity
            )
        else:
            logger.info(f"VIP discount excluded by staff override for {item_type} {item_id}")

        if vip_discount:
            discount_data['vip'] = {
                'percent': float(vip_discount.discount_percent),
                'amount': float(vip_discount.discount_amount)
            }
            all_eligible.append({
                'type': 'vip',
                'percent': float(vip_discount.discount_percent),
                'amount': float(vip_discount.discount_amount)
            })

        # 5. STANDARD DISCOUNT (Fallback)
        # Skip standard discount if staff manually unchecked it
        standard_discount = None
        if not exclude_standard:
            standard_discount = DiscountService.calculate_standard_discount(
                session, item_type, item_id, unit_price, quantity
            )
        elif exclude_standard:
            logger.info(f"Standard discount excluded by staff override for {item_type} {item_id}")
        if standard_discount:
            discount_data['standard'] = {
                'percent': float(standard_discount.discount_percent),
                'amount': float(standard_discount.discount_amount)
            }
            all_eligible.append({
                'type': 'standard',
                'percent': float(standard_discount.discount_percent),
                'amount': float(standard_discount.discount_amount)
            })

        # =================================================================
        # STEP 2: Use centralized stacking calculator
        # =================================================================
        stacked_result = DiscountService.calculate_stacked_discount(
            discount_data, stacking_config, item_price=float(original_price)
        )

        # =================================================================
        # STEP 3: Convert result to DiscountCalculationResult
        # =================================================================
        total_percent = Decimal(str(stacked_result.get('total_percent', 0)))
        discount_amount = (original_price * total_percent) / 100
        final_price = original_price - discount_amount

        # Determine primary discount type for compatibility
        applied_discounts = stacked_result.get('applied_discounts', [])
        if not applied_discounts:
            discount_type = 'none'
        elif len(applied_discounts) == 1:
            source = applied_discounts[0].get('source', 'none')
            # Map 'campaign' to 'promotion' for backward compatibility
            discount_type = 'promotion' if source == 'campaign' else source
        else:
            # Multiple discounts applied - use 'stacked' type
            discount_type = 'stacked'

        # Get promotion_id and card_type_id if applicable
        promotion_id = None
        card_type_id = None

        if 'campaign' in discount_data:
            promotion_id = discount_data['campaign'].get('promotion_id')
        if 'loyalty' in discount_data:
            card_type_id = discount_data['loyalty'].get('card_type_id')

        # Mark which discounts were applied vs excluded
        for eligible in all_eligible:
            eligible_source = eligible['type']
            if eligible_source == 'campaign':
                eligible_source = 'campaign'  # Normalize

            is_applied = any(
                a.get('source') == eligible_source or
                (eligible['type'] == 'campaign' and a.get('source') == 'campaign')
                for a in applied_discounts
            )
            eligible['applied'] = is_applied

            if not is_applied:
                # Find exclusion reason
                excluded_list = stacked_result.get('excluded_discounts', [])
                for excl in excluded_list:
                    if excl.get('source') == eligible_source:
                        eligible['reason'] = excl.get('reason', 'Excluded by stacking config')
                        break
                else:
                    eligible['reason'] = 'Not applied'

        # Determine if stacking was applied (multiple discounts combined)
        stacking_applied = len(applied_discounts) > 1

        # NOTE: Staff discretionary is now an INVOICE-LEVEL discount (2025-11-29)
        # It is NOT applied at line-item level anymore
        # The staff_discretionary parameter is ignored here - handled at invoice total level in API

        return DiscountCalculationResult(
            discount_type=discount_type,
            discount_percent=total_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            card_type_id=card_type_id,
            promotion_id=promotion_id,
            metadata={
                'selection_reason': f'Calculated using hospital stacking config',
                'stacking_config': stacking_config,
                'stacking_applied': stacking_applied,  # True when bulk + loyalty combined
                'breakdown': stacked_result.get('breakdown', []),
                'applied_discounts': applied_discounts,
                'excluded_discounts': stacked_result.get('excluded_discounts', []),
                'all_eligible_discounts': all_eligible,
                'capped': stacked_result.get('capped', False),
                'cap_applied': stacked_result.get('cap_applied')
            }
        )

    @staticmethod
    def validate_discount(
        session: Session,
        service_id: str,
        discount_percent: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that discount doesn't exceed service's max_discount

        Args:
            session: Database session
            service_id: Service ID
            discount_percent: Proposed discount percentage

        Returns:
            Tuple of (is_valid, error_message)
        """
        service = session.query(Service).filter_by(service_id=service_id).first()
        if not service:
            return False, "Service not found"

        if not service.max_discount:
            # No max limit set, any discount is allowed
            return True, None

        if discount_percent > service.max_discount:
            return False, (
                f"Discount of {discount_percent}% exceeds maximum allowed "
                f"discount of {service.max_discount}% for service '{service.service_name}'"
            )

        return True, None

    @staticmethod
    def apply_discounts_to_invoice_items(
        session: Session,
        hospital_id: str,
        patient_id: str,
        line_items: List[Dict],
        invoice_date: date = None,
        respect_max_discount: bool = True
    ) -> List[Dict]:
        """
        Apply best available discount to all service and medicine items in an invoice

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            line_items: List of line item dictionaries (Services and Medicines)
            invoice_date: Invoice date (defaults to today)
            respect_max_discount: Whether to enforce max_discount

        Returns:
            Updated line_items with discount_percent and discount_metadata populated
        """
        # Count total services in the invoice (sum of quantities, not just line items)
        service_items = [item for item in line_items if item.get('item_type') == 'Service']

        # IMPORTANT: Count TOTAL QUANTITY of services, not just number of line items
        # Example: 1 line item with quantity=5 should count as 5 services
        total_service_count = sum(int(item.get('quantity', 1)) for item in service_items)

        logger.info(f"Total service count: {total_service_count} ({len(service_items)} line items)")

        # Count total medicines in the invoice (same logic as services)
        medicine_items = [item for item in line_items if item.get('item_type') == 'Medicine']
        total_medicine_count = sum(int(item.get('quantity', 1)) for item in medicine_items)

        logger.info(f"Total medicine count: {total_medicine_count} ({len(medicine_items)} line items)")

        # Apply discount to each service item
        for item in service_items:
            service_id = item.get('item_id') or item.get('service_id')
            if not service_id:
                continue

            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))

            # Get best discount
            best_discount = DiscountService.get_best_discount(
                session=session,
                hospital_id=hospital_id,
                service_id=service_id,
                patient_id=patient_id,
                unit_price=unit_price,
                quantity=quantity,
                total_service_count=total_service_count,
                invoice_date=invoice_date
            )

            # Validate discount if required
            if respect_max_discount and best_discount.discount_percent > 0:
                is_valid, error_msg = DiscountService.validate_discount(
                    session, service_id, best_discount.discount_percent
                )
                if not is_valid:
                    # Fallback to max allowed discount
                    service = session.query(Service).filter_by(service_id=service_id).first()
                    if service and service.max_discount:
                        original_price = unit_price * quantity
                        capped_percent = service.max_discount
                        best_discount.discount_percent = capped_percent
                        best_discount.discount_amount = (original_price * capped_percent) / 100
                        best_discount.final_price = original_price - best_discount.discount_amount
                        best_discount.metadata['capped'] = True
                        best_discount.metadata['cap_reason'] = error_msg

            # Update line item with discount
            item['discount_percent'] = float(best_discount.discount_percent)
            item['discount_amount'] = float(best_discount.discount_amount)
            item['discount_type'] = best_discount.discount_type
            item['discount_metadata'] = best_discount.metadata
            item['card_type_id'] = best_discount.card_type_id
            item['promotion_id'] = best_discount.promotion_id  # RENAMED from campaign_hook_id

        # Apply discount to each medicine item
        for item in medicine_items:
            medicine_id = item.get('item_id') or item.get('medicine_id')
            if not medicine_id:
                continue

            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))

            # Calculate bulk discount for medicine
            medicine_discount = DiscountService.calculate_medicine_bulk_discount(
                session=session,
                hospital_id=hospital_id,
                medicine_id=medicine_id,
                total_medicine_count=total_medicine_count,
                unit_price=unit_price,
                quantity=quantity
            )

            # If no bulk discount, create a "no discount" result
            if not medicine_discount:
                original_price = unit_price * quantity
                medicine_discount = DiscountCalculationResult(
                    discount_type='none',
                    discount_percent=Decimal('0'),
                    discount_amount=Decimal('0'),
                    final_price=original_price,
                    original_price=original_price,
                    metadata={}
                )

            # Validate discount if required
            if respect_max_discount and medicine_discount.discount_percent > 0:
                medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
                if medicine and medicine.max_discount:
                    if medicine_discount.discount_percent > medicine.max_discount:
                        original_price = unit_price * quantity
                        capped_percent = medicine.max_discount
                        medicine_discount.discount_percent = capped_percent
                        medicine_discount.discount_amount = (original_price * capped_percent) / 100
                        medicine_discount.final_price = original_price - medicine_discount.discount_amount
                        medicine_discount.metadata['capped'] = True
                        medicine_discount.metadata['cap_reason'] = f'Exceeded max_discount ({medicine.max_discount}%)'

            # Update line item with discount
            item['discount_percent'] = float(medicine_discount.discount_percent)
            item['discount_amount'] = float(medicine_discount.discount_amount)
            item['discount_type'] = medicine_discount.discount_type
            item['discount_metadata'] = medicine_discount.metadata
            item['card_type_id'] = medicine_discount.card_type_id
            item['promotion_id'] = medicine_discount.promotion_id  # RENAMED from campaign_hook_id

        return line_items

    @staticmethod
    def apply_discounts_to_invoice_items_multi(
        session: Session,
        hospital_id: str,
        patient_id: str,
        line_items: List[Dict],
        invoice_date: date = None,
        respect_max_discount: bool = True,
        respect_staff_override: bool = True,
        exclude_bulk: bool = False,
        exclude_loyalty: bool = False,
        exclude_standard: bool = False,
        exclude_campaign: bool = False,  # Added 2025-11-29
        excluded_campaign_ids: List[str] = None,  # Per-campaign exclusion
        manual_promo_code: Dict = None,
        staff_discretionary: Dict = None,  # Added 2025-11-29
        exclude_vip: bool = False  # Added 2025-11-29: Staff manually unchecked VIP discount
    ) -> List[Dict]:
        """
        Apply multi-discount logic to all items (Services, Medicines, Packages) in an invoice

        Uses the new 4-discount system:
        - Standard (fallback)
        - Bulk (services/medicines only, based on quantity)
        - Loyalty % (all types, requires loyalty card)
        - Promotion (all types, highest priority)

        Staff Override:
        - If item has 'discount_override' = True, skip automatic discount calculation
        - Staff can uncheck discount checkboxes to override the proposed discount
        - The manually set discount_percent will be preserved

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            line_items: List of line item dictionaries (Services, Medicines, Packages)
            invoice_date: Invoice date (defaults to today)
            respect_max_discount: Whether to enforce max_discount
            respect_staff_override: Whether to respect staff's manual discount overrides
            exclude_bulk: If True, skip bulk discount calculation (staff manually unchecked)
            exclude_loyalty: If True, skip loyalty discount calculation (staff manually unchecked)

        Returns:
            Updated line_items with discount_percent and discount_metadata populated
        """
        # Separate items by type
        service_items = [item for item in line_items if item.get('item_type') == 'Service']
        medicine_items = [item for item in line_items if item.get('item_type') == 'Medicine']
        package_items = [item for item in line_items if item.get('item_type') == 'Package']

        # Count total quantities (for bulk discount eligibility)
        total_service_count = sum(int(item.get('quantity', 1)) for item in service_items)
        total_medicine_count = sum(int(item.get('quantity', 1)) for item in medicine_items)

        logger.info(f"Multi-discount: Service count={total_service_count} ({len(service_items)} items), "
                    f"Medicine count={total_medicine_count} ({len(medicine_items)} items), "
                    f"Package count={len(package_items)} items, exclude_bulk={exclude_bulk}, exclude_loyalty={exclude_loyalty}")

        # Process each SERVICE item
        for item in service_items:
            service_id = item.get('item_id') or item.get('service_id')
            if not service_id:
                continue

            # Check for staff override - if staff manually set/cleared the discount, respect it
            if respect_staff_override and item.get('discount_override'):
                logger.info(f"Staff override detected for service {item.get('item_name')} - preserving manual discount of {item.get('discount_percent', 0)}%")
                # Preserve the staff's manually set discount
                item['discount_type'] = item.get('discount_type', 'manual')
                item['discount_metadata'] = item.get('discount_metadata', {'source': 'staff_override'})
                continue

            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))

            # Use multi-discount logic
            best_discount = DiscountService.get_best_discount_multi(
                session=session,
                hospital_id=hospital_id,
                patient_id=patient_id,
                item_type='Service',
                item_id=service_id,
                unit_price=unit_price,
                quantity=quantity,
                total_item_count=total_service_count,
                invoice_date=invoice_date,
                invoice_items=line_items,  # Pass full invoice context for buy_x_get_y
                exclude_bulk=exclude_bulk,  # Staff manually unchecked bulk discount
                exclude_loyalty=exclude_loyalty,  # Staff manually unchecked loyalty discount
                exclude_standard=exclude_standard,  # Staff manually unchecked standard discount
                manual_promo_code=manual_promo_code,  # Manually entered promo code
                staff_discretionary=staff_discretionary,  # Staff discretionary discount (Added 2025-11-29)
                exclude_campaign=exclude_campaign,  # Exclude ALL campaigns
                excluded_campaign_ids=excluded_campaign_ids,  # Per-campaign exclusion
                exclude_vip=exclude_vip  # Staff manually unchecked VIP discount (Added 2025-11-29)
            )

            # Apply max_discount cap (EXCEPT for promotions and stacked discounts)
            # Promotions (especially Buy X Get Y) should not be capped by max_discount
            # Stacked discounts (bulk + loyalty) should not be capped - stacking is a hospital-level decision
            is_stacked = best_discount.metadata.get('stacking_applied', False)
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion' and not is_stacked:
                service = session.query(Service).filter_by(service_id=service_id).first()
                if service and service.max_discount:
                    if best_discount.discount_percent > service.max_discount:
                        original_price = unit_price * quantity
                        capped_percent = service.max_discount
                        best_discount.discount_percent = capped_percent
                        best_discount.discount_amount = (original_price * capped_percent) / 100
                        best_discount.final_price = original_price - best_discount.discount_amount
                        best_discount.metadata['capped'] = True
                        best_discount.metadata['cap_reason'] = f'Exceeded max_discount ({service.max_discount}%)'
                        logger.info(f"Discount capped to max_discount: {service.service_name} {capped_percent}%")

            # Update line item
            item['discount_percent'] = float(best_discount.discount_percent)
            item['discount_amount'] = float(best_discount.discount_amount)
            item['discount_type'] = best_discount.discount_type
            item['discount_metadata'] = best_discount.metadata
            item['card_type_id'] = best_discount.card_type_id
            item['promotion_id'] = best_discount.promotion_id  # RENAMED from campaign_hook_id

        # Process each MEDICINE item
        for item in medicine_items:
            medicine_id = item.get('item_id') or item.get('medicine_id')
            if not medicine_id:
                continue

            # Check for staff override
            if respect_staff_override and item.get('discount_override'):
                logger.info(f"Staff override detected for medicine {item.get('item_name')} - preserving manual discount of {item.get('discount_percent', 0)}%")
                item['discount_type'] = item.get('discount_type', 'manual')
                item['discount_metadata'] = item.get('discount_metadata', {'source': 'staff_override'})
                continue

            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))

            # Use multi-discount logic
            best_discount = DiscountService.get_best_discount_multi(
                session=session,
                hospital_id=hospital_id,
                patient_id=patient_id,
                item_type='Medicine',
                item_id=medicine_id,
                unit_price=unit_price,
                quantity=quantity,
                total_item_count=total_medicine_count,
                invoice_date=invoice_date,
                invoice_items=line_items,  # Pass full invoice context for buy_x_get_y
                exclude_bulk=exclude_bulk,  # Staff manually unchecked bulk discount
                exclude_loyalty=exclude_loyalty,  # Staff manually unchecked loyalty discount
                exclude_standard=exclude_standard,  # Staff manually unchecked standard discount
                manual_promo_code=manual_promo_code,  # Manually entered promo code
                staff_discretionary=staff_discretionary,  # Staff discretionary discount (Added 2025-11-29)
                exclude_campaign=exclude_campaign,  # Exclude ALL campaigns
                excluded_campaign_ids=excluded_campaign_ids,  # Per-campaign exclusion
                exclude_vip=exclude_vip  # Staff manually unchecked VIP discount (Added 2025-11-29)
            )

            # Apply max_discount cap (EXCEPT for promotions and stacked discounts)
            is_stacked = best_discount.metadata.get('stacking_applied', False)
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion' and not is_stacked:
                medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
                if medicine and medicine.max_discount:
                    if best_discount.discount_percent > medicine.max_discount:
                        original_price = unit_price * quantity
                        capped_percent = medicine.max_discount
                        best_discount.discount_percent = capped_percent
                        best_discount.discount_amount = (original_price * capped_percent) / 100
                        best_discount.final_price = original_price - best_discount.discount_amount
                        best_discount.metadata['capped'] = True
                        best_discount.metadata['cap_reason'] = f'Exceeded max_discount ({medicine.max_discount}%)'

            # Update line item
            item['discount_percent'] = float(best_discount.discount_percent)
            item['discount_amount'] = float(best_discount.discount_amount)
            item['discount_type'] = best_discount.discount_type
            item['discount_metadata'] = best_discount.metadata
            item['card_type_id'] = best_discount.card_type_id
            item['promotion_id'] = best_discount.promotion_id  # RENAMED from campaign_hook_id

        # Process each PACKAGE item
        for item in package_items:
            package_id = item.get('item_id') or item.get('package_id')
            if not package_id:
                continue

            # Check for staff override
            if respect_staff_override and item.get('discount_override'):
                logger.info(f"Staff override detected for package {item.get('item_name')} - preserving manual discount of {item.get('discount_percent', 0)}%")
                item['discount_type'] = item.get('discount_type', 'manual')
                item['discount_metadata'] = item.get('discount_metadata', {'source': 'staff_override'})
                continue

            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))

            # Use multi-discount logic (packages don't support bulk discount)
            best_discount = DiscountService.get_best_discount_multi(
                session=session,
                hospital_id=hospital_id,
                patient_id=patient_id,
                item_type='Package',
                item_id=package_id,
                unit_price=unit_price,
                quantity=quantity,
                total_item_count=0,  # Not used for packages (no bulk discount)
                invoice_date=invoice_date,
                invoice_items=line_items,  # Pass full invoice context for buy_x_get_y
                exclude_bulk=True,  # Packages don't support bulk discount
                exclude_loyalty=exclude_loyalty,  # Staff manually unchecked loyalty discount
                staff_discretionary=staff_discretionary,  # Staff discretionary discount (Added 2025-11-29)
                exclude_campaign=exclude_campaign,  # Exclude ALL campaigns
                excluded_campaign_ids=excluded_campaign_ids,  # Per-campaign exclusion
                exclude_vip=exclude_vip  # Staff manually unchecked VIP discount (Added 2025-11-29)
            )

            # Apply max_discount cap (EXCEPT for promotions and stacked discounts)
            is_stacked = best_discount.metadata.get('stacking_applied', False)
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion' and not is_stacked:
                package = session.query(Package).filter_by(package_id=package_id).first()
                if package and package.max_discount:
                    if best_discount.discount_percent > package.max_discount:
                        original_price = unit_price * quantity
                        capped_percent = package.max_discount
                        best_discount.discount_percent = capped_percent
                        best_discount.discount_amount = (original_price * capped_percent) / 100
                        best_discount.final_price = original_price - best_discount.discount_amount
                        best_discount.metadata['capped'] = True
                        best_discount.metadata['cap_reason'] = f'Exceeded max_discount ({package.max_discount}%)'

            # Update line item
            item['discount_percent'] = float(best_discount.discount_percent)
            item['discount_amount'] = float(best_discount.discount_amount)
            item['discount_type'] = best_discount.discount_type
            item['discount_metadata'] = best_discount.metadata
            item['card_type_id'] = best_discount.card_type_id
            item['promotion_id'] = best_discount.promotion_id  # RENAMED from campaign_hook_id

        return line_items

    @staticmethod
    def build_campaigns_applied_json(
        session: Session,
        line_items: List[Dict]
    ) -> Optional[Dict]:
        """
        Build campaigns_applied JSONB structure from line items with promotions

        Extracts promotion information from line items and builds a summary
        for campaign effectiveness tracking.

        Args:
            session: Database session
            line_items: List of line items (after discount application)

        Returns:
            Dict in format:
            {
                "applied_promotions": [
                    {
                        "promotion_id": "uuid",
                        "campaign_name": "Premium Service - Free Consultation",
                        "campaign_code": "PREMIUM_CONSULT",
                        "promotion_type": "buy_x_get_y",
                        "items_affected": ["item-id-1", "item-id-2"],
                        "total_discount": 500.00
                    }
                ]
            }

            Returns None if no promotions were applied
        """
        promotions_map = {}  # promotion_id -> promotion info

        # Scan line items for promotion discounts
        for item in line_items:
            if item.get('discount_type') == 'promotion' and item.get('promotion_id'):
                promotion_id = item.get('promotion_id')
                item_id = item.get('item_id') or item.get('service_id') or item.get('medicine_id')
                discount_amount = Decimal(str(item.get('discount_amount', 0)))

                if promotion_id not in promotions_map:
                    # Fetch promotion details
                    promotion = session.query(PromotionCampaign).filter_by(
                        campaign_id=promotion_id
                    ).first()

                    if promotion:
                        promotions_map[promotion_id] = {
                            'promotion_id': str(promotion_id),
                            'campaign_name': promotion.campaign_name,
                            'campaign_code': promotion.campaign_code,
                            'promotion_type': promotion.promotion_type or 'simple_discount',
                            'items_affected': [],
                            'total_discount': Decimal('0')
                        }

                # Add item to affected items
                if promotion_id in promotions_map:
                    if item_id:
                        promotions_map[promotion_id]['items_affected'].append(str(item_id))
                    promotions_map[promotion_id]['total_discount'] += discount_amount

        if not promotions_map:
            return None

        # Convert to list and format for JSON
        applied_promotions = []
        for promo_info in promotions_map.values():
            applied_promotions.append({
                'promotion_id': promo_info['promotion_id'],
                'campaign_name': promo_info['campaign_name'],
                'campaign_code': promo_info['campaign_code'],
                'promotion_type': promo_info['promotion_type'],
                'items_affected': promo_info['items_affected'],
                'total_discount': float(promo_info['total_discount'])
            })

        return {
            'applied_promotions': applied_promotions
        }

    @staticmethod
    def record_promotion_usage(
        session: Session,
        hospital_id: str,
        invoice_id: str,
        line_items: List[Dict],
        patient_id: str,
        invoice_date: date
    ):
        """
        Record promotion usage in promotion_usage_log and update promotion counters

        This method:
        1. Creates PromotionUsageLog entries for each promotion used
        2. Increments promotion_campaigns.current_uses counter

        Args:
            session: Database session
            hospital_id: Hospital UUID
            invoice_id: Invoice UUID
            line_items: List of line items (after discount application)
            patient_id: Patient UUID
            invoice_date: Invoice date
        """
        promotions_used = {}  # promotion_id -> {discount_amount, items_count}

        # Collect promotion usage from line items
        for item in line_items:
            if item.get('discount_type') == 'promotion' and item.get('promotion_id'):
                promotion_id = item.get('promotion_id')
                discount_amount = Decimal(str(item.get('discount_amount', 0)))

                if promotion_id not in promotions_used:
                    promotions_used[promotion_id] = {
                        'discount_amount': Decimal('0'),
                        'items_count': 0
                    }

                promotions_used[promotion_id]['discount_amount'] += discount_amount
                promotions_used[promotion_id]['items_count'] += 1

        # Record usage for each promotion
        for promotion_id, usage_info in promotions_used.items():
            try:
                # Create usage log entry
                usage_log = PromotionUsageLog(
                    campaign_id=promotion_id,
                    hospital_id=hospital_id,
                    patient_id=patient_id,
                    invoice_id=invoice_id,
                    discount_amount=usage_info['discount_amount']
                )
                session.add(usage_log)

                # Increment promotion current_uses counter
                promotion = session.query(PromotionCampaign).filter_by(
                    campaign_id=promotion_id
                ).first()

                if promotion:
                    promotion.current_uses = (promotion.current_uses or 0) + 1
                    logger.info(
                        f"Promotion usage recorded: {promotion.campaign_name} "
                        f"(total uses: {promotion.current_uses})"
                    )

            except Exception as e:
                logger.error(
                    f"Error recording promotion usage for {promotion_id}: {str(e)}",
                    exc_info=True
                )
                # Continue processing other promotions even if one fails
                continue

    @staticmethod
    def log_discount_application(
        session: Session,
        hospital_id: str,
        invoice_id: str,
        line_item_id: str,
        service_id: str,
        patient_id: str,
        discount_result: DiscountCalculationResult,
        service_count_in_invoice: int,
        applied_by: str = None
    ) -> DiscountApplicationLog:
        """
        Create audit log entry for discount application

        Args:
            session: Database session
            hospital_id: Hospital ID
            invoice_id: Invoice ID
            line_item_id: Line item ID
            service_id: Service ID
            patient_id: Patient ID
            discount_result: DiscountCalculationResult object
            service_count_in_invoice: Total service count in invoice
            applied_by: User ID who applied the discount

        Returns:
            Created DiscountApplicationLog object
        """
        log_entry = DiscountApplicationLog(
            hospital_id=hospital_id,
            invoice_id=invoice_id,
            line_item_id=line_item_id,
            service_id=service_id,
            patient_id=patient_id,
            discount_type=discount_result.discount_type,
            card_type_id=discount_result.card_type_id,
            campaign_id=discount_result.promotion_id,  # RENAMED from campaign_hook_id
            original_price=discount_result.original_price,
            discount_percent=discount_result.discount_percent,
            discount_amount=discount_result.discount_amount,
            final_price=discount_result.final_price,
            applied_at=date.today(),
            applied_by=applied_by,
            calculation_metadata=discount_result.metadata,
            service_count_in_invoice=service_count_in_invoice
        )

        session.add(log_entry)
        return log_entry

    @staticmethod
    def get_discount_summary(
        session: Session,
        hospital_id: str,
        start_date: date,
        end_date: date,
        discount_type: str = None
    ) -> Dict:
        """
        Get summary of discount applications for reporting

        Args:
            session: Database session
            hospital_id: Hospital ID
            start_date: Start date for the report
            end_date: End date for the report
            discount_type: Optional filter by discount type

        Returns:
            Dictionary with discount summary statistics
        """
        query = session.query(DiscountApplicationLog).filter(
            and_(
                DiscountApplicationLog.hospital_id == hospital_id,
                DiscountApplicationLog.applied_at >= start_date,
                DiscountApplicationLog.applied_at <= end_date
            )
        )

        if discount_type:
            query = query.filter(DiscountApplicationLog.discount_type == discount_type)

        logs = query.all()

        total_discount_amount = sum(log.discount_amount for log in logs)
        total_original_amount = sum(log.original_price for log in logs)

        by_type = {}
        for log in logs:
            if log.discount_type not in by_type:
                by_type[log.discount_type] = {
                    'count': 0,
                    'total_discount': Decimal('0'),
                    'total_original': Decimal('0')
                }
            by_type[log.discount_type]['count'] += 1
            by_type[log.discount_type]['total_discount'] += log.discount_amount
            by_type[log.discount_type]['total_original'] += log.original_price

        return {
            'period': {'start_date': start_date, 'end_date': end_date},
            'total_discount_applications': len(logs),
            'total_discount_amount': float(total_discount_amount),
            'total_original_amount': float(total_original_amount),
            'discount_percentage_overall': float(
                (total_discount_amount / total_original_amount * 100)
                if total_original_amount > 0 else 0
            ),
            'by_discount_type': {
                dtype: {
                    'count': data['count'],
                    'total_discount': float(data['total_discount']),
                    'total_original': float(data['total_original']),
                    'avg_discount_percent': float(
                        (data['total_discount'] / data['total_original'] * 100)
                        if data['total_original'] > 0 else 0
                    )
                }
                for dtype, data in by_type.items()
            }
        }

    # ==================== MANUAL PROMO CODE VALIDATION (Added 2025-11-25) ====================

    @staticmethod
    def validate_promo_code(
        session: Session,
        hospital_id: str,
        promo_code: str,
        patient_id: str = None,
        invoice_date: date = None
    ) -> Dict:
        """
        Validate a manually entered promotion code.

        This is used when staff enters a promo code at billing counter.
        Works for both personalized and public promotions.

        Args:
            session: Database session
            hospital_id: Hospital UUID
            promo_code: The promotion code entered by staff
            patient_id: Patient UUID (for checking per-patient usage limits)
            invoice_date: Invoice date for validity check (defaults to today)

        Returns:
            Dict with:
                - valid: True/False
                - promotion: Promotion details if valid
                - error: Error message if invalid
        """
        if invoice_date is None:
            invoice_date = date.today()

        if not promo_code or not promo_code.strip():
            return {
                'valid': False,
                'error': 'Promotion code is required',
                'promotion': None
            }

        promo_code = promo_code.strip().upper()

        # Find promotion by code
        promotion = session.query(PromotionCampaign).filter(
            and_(
                PromotionCampaign.hospital_id == hospital_id,
                func.upper(PromotionCampaign.campaign_code) == promo_code,
                PromotionCampaign.is_deleted == False
            )
        ).first()

        if not promotion:
            logger.warning(f"Promo code not found: {promo_code}")
            return {
                'valid': False,
                'error': f'Invalid promotion code: {promo_code}',
                'promotion': None
            }

        # Check if promotion is active
        if not promotion.is_active:
            logger.info(f"Promo code inactive: {promo_code}")
            return {
                'valid': False,
                'error': 'This promotion is no longer active',
                'promotion': None
            }

        # Check validity period
        if invoice_date < promotion.start_date:
            logger.info(f"Promo code not yet started: {promo_code}, starts {promotion.start_date}")
            return {
                'valid': False,
                'error': f'This promotion starts on {promotion.start_date.strftime("%d-%b-%Y")}',
                'promotion': None
            }

        if invoice_date > promotion.end_date:
            logger.info(f"Promo code expired: {promo_code}, ended {promotion.end_date}")
            return {
                'valid': False,
                'error': f'This promotion expired on {promotion.end_date.strftime("%d-%b-%Y")}',
                'promotion': None
            }

        # Check max total uses
        if promotion.max_total_uses and promotion.current_uses >= promotion.max_total_uses:
            logger.info(f"Promo code usage limit reached: {promo_code}")
            return {
                'valid': False,
                'error': 'This promotion has reached its maximum usage limit',
                'promotion': None
            }

        # Check max uses per patient
        if patient_id and promotion.max_uses_per_patient:
            patient_usage_count = session.query(PromotionUsageLog).filter(
                and_(
                    PromotionUsageLog.campaign_id == promotion.campaign_id,
                    PromotionUsageLog.patient_id == patient_id
                )
            ).count()

            if patient_usage_count >= promotion.max_uses_per_patient:
                logger.info(f"Patient usage limit reached for promo: {promo_code}, patient: {patient_id}")
                return {
                    'valid': False,
                    'error': 'You have already used this promotion the maximum number of times',
                    'promotion': None
                }

        # Promotion is valid - return details
        logger.info(f"Promo code validated successfully: {promo_code}, campaign: {promotion.campaign_name}")

        return {
            'valid': True,
            'error': None,
            'promotion': {
                'campaign_id': str(promotion.campaign_id),
                'campaign_code': promotion.campaign_code,
                'campaign_name': promotion.campaign_name,
                'description': promotion.description,
                'promotion_type': promotion.promotion_type,
                'discount_type': promotion.discount_type,
                'discount_value': float(promotion.discount_value),
                'applies_to': promotion.applies_to,
                'specific_items': promotion.specific_items,
                'start_date': promotion.start_date.strftime('%d-%b-%Y'),
                'end_date': promotion.end_date.strftime('%d-%b-%Y'),
                'is_personalized': promotion.is_personalized,
                'min_purchase_amount': float(promotion.min_purchase_amount) if promotion.min_purchase_amount else None,
                'max_discount_amount': float(promotion.max_discount_amount) if promotion.max_discount_amount else None,
                'terms_and_conditions': promotion.terms_and_conditions,
                'remaining_uses': (promotion.max_total_uses - promotion.current_uses) if promotion.max_total_uses else None
            }
        }

    @staticmethod
    def get_promotion_by_code(
        session: Session,
        hospital_id: str,
        promo_code: str
    ) -> Optional[PromotionCampaign]:
        """
        Get promotion campaign by code (for applying manually entered code).

        Args:
            session: Database session
            hospital_id: Hospital UUID
            promo_code: The promotion code

        Returns:
            PromotionCampaign object or None
        """
        if not promo_code:
            return None

        return session.query(PromotionCampaign).filter(
            and_(
                PromotionCampaign.hospital_id == hospital_id,
                func.upper(PromotionCampaign.campaign_code) == promo_code.strip().upper(),
                PromotionCampaign.is_active == True,
                PromotionCampaign.is_deleted == False
            )
        ).first()

    # =========================================================================
    # CENTRALIZED DISCOUNT STACKING CONFIGURATION & CALCULATION
    # =========================================================================
    # These methods provide a single source of truth for discount calculation
    # logic, used by invoicing, dashboard, simulation, and all other modules.
    # =========================================================================

    @staticmethod
    def get_stacking_config(session: Session, hospital_id: str) -> Dict:
        """
        Get discount stacking configuration for a hospital.
        Returns default config if not set.

        Args:
            session: Database session
            hospital_id: Hospital UUID

        Returns:
            Stacking configuration dictionary
        """
        default_config = {
            'campaign': {
                'mode': 'exclusive',           # 'exclusive' or 'incremental'
                'buy_x_get_y_exclusive': True  # X items always at list price
            },
            'loyalty': {
                'mode': 'incremental'          # 'incremental' or 'absolute'
            },
            'bulk': {
                'mode': 'incremental',         # 'incremental' or 'absolute'
                'exclude_with_campaign': True  # No bulk if campaign applies
            },
            'vip': {
                'mode': 'absolute'             # 'incremental' or 'absolute'
            },
            'max_total_discount': None         # Optional cap (e.g., 50)
        }

        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital:
            return default_config

        config = hospital.discount_stacking_config
        if not config:
            return default_config

        # Merge with defaults to ensure all keys exist
        merged = default_config.copy()
        for key in ['campaign', 'loyalty', 'bulk', 'vip']:
            if key in config:
                merged[key] = {**default_config.get(key, {}), **config[key]}
        if 'max_total_discount' in config:
            merged['max_total_discount'] = config['max_total_discount']

        return merged

    @staticmethod
    def calculate_stacked_discount(
        discounts: Dict[str, Dict],
        stacking_config: Dict,
        item_price: Decimal = None
    ) -> Dict:
        """
        Calculate the final discount based on stacking configuration.

        This is the SINGLE SOURCE OF TRUTH for discount stacking logic.
        All modules (invoicing, dashboard, simulation) should use this.

        Args:
            discounts: Dictionary of available discounts, each with:
                {
                    'campaign': {'percent': X, 'amount': Y, 'type': 'percentage'|'fixed'|'buy_x_get_y', ...},
                    'bulk': {'percent': X, ...},
                    'loyalty': {'percent': X, ...},
                    'vip': {'percent': X, ...},
                    'standard': {'percent': X, ...}
                }
            stacking_config: Hospital's stacking configuration
            item_price: Item price (needed to convert fixed amount to %)

        Returns:
            {
                'total_percent': X,
                'breakdown': [...],
                'applied_discounts': [...],
                'excluded_discounts': [...],
                'capped': True/False,
                'cap_applied': X
            }
        """
        breakdown = []
        applied = []
        excluded = []
        total_percent = Decimal('0')

        campaign = discounts.get('campaign', {})
        bulk = discounts.get('bulk', {})
        loyalty = discounts.get('loyalty', {})
        vip = discounts.get('vip', {})
        standard = discounts.get('standard', {})

        campaign_config = stacking_config.get('campaign', {})
        loyalty_config = stacking_config.get('loyalty', {})
        bulk_config = stacking_config.get('bulk', {})
        vip_config = stacking_config.get('vip', {})

        # =====================================================================
        # STEP 0: Calculate actual percentages for each discount type
        # =====================================================================
        discount_values = {}

        # Campaign discount
        campaign_percent = Decimal('0')
        if campaign.get('applicable') or campaign.get('percent', 0) > 0:
            campaign_type = campaign.get('type', 'percentage')
            if campaign_type == 'buy_x_get_y':
                campaign_percent = Decimal(str(campaign.get('effective_percent', 0)))
            elif campaign_type == 'fixed' and item_price and item_price > 0:
                amount = Decimal(str(campaign.get('amount', 0)))
                campaign_percent = (amount / item_price) * 100
            else:
                campaign_percent = Decimal(str(campaign.get('percent', 0)))
        discount_values['campaign'] = {
            'percent': campaign_percent,
            'config': campaign_config,
            'name': campaign.get('name', 'Campaign'),
            'type': campaign.get('type', 'percentage')
        }

        # Bulk discount
        bulk_percent = Decimal(str(bulk.get('percent', 0)))
        discount_values['bulk'] = {
            'percent': bulk_percent,
            'config': bulk_config,
            'name': 'Bulk Discount'
        }

        # Loyalty discount
        loyalty_percent = Decimal(str(loyalty.get('percent', 0)))
        if not loyalty.get('is_valid_today', True):
            loyalty_percent = Decimal('0')
        discount_values['loyalty'] = {
            'percent': loyalty_percent,
            'config': loyalty_config,
            'name': loyalty.get('card_type', 'Loyalty Card')
        }

        # VIP discount
        vip_percent = Decimal(str(vip.get('percent', 0)))
        discount_values['vip'] = {
            'percent': vip_percent,
            'config': vip_config,
            'name': 'VIP Discount'
        }

        # =====================================================================
        # DEBUG: Log discount values and modes (Added 2025-11-29)
        # =====================================================================
        logger.info(f"=== calculate_stacked_discount DEBUG ===")
        for source, data in discount_values.items():
            logger.info(f"  {source}: percent={data['percent']}, mode={data['config'].get('mode', 'N/A')}, name={data.get('name', 'N/A')}")

        # =====================================================================
        # STEP 1: Check for EXCLUSIVE mode (any type can be exclusive)
        # If multiple exclusives, highest one wins
        # =====================================================================
        exclusive_candidates = []
        for source, data in discount_values.items():
            if data['percent'] > 0 and data['config'].get('mode') == 'exclusive':
                exclusive_candidates.append({
                    'source': source,
                    'percent': data['percent'],
                    'name': data['name']
                })

        logger.info(f"  Exclusive candidates: {exclusive_candidates}")

        if exclusive_candidates:
            # Pick highest exclusive discount
            best_exclusive = max(exclusive_candidates, key=lambda x: x['percent'])
            logger.info(f"  Best exclusive: {best_exclusive['source']} at {best_exclusive['percent']}%")
            total_percent = best_exclusive['percent']
            breakdown.append({
                'source': best_exclusive['source'],
                'percent': float(best_exclusive['percent']),
                'mode': 'exclusive'
            })
            applied.append({
                'source': best_exclusive['source'],
                'percent': float(best_exclusive['percent']),
                'name': best_exclusive['name']
            })

            # Mark all others as excluded
            for source, data in discount_values.items():
                if source != best_exclusive['source'] and data['percent'] > 0:
                    excluded.append({
                        'source': source,
                        'reason': f"{best_exclusive['source'].title()} is exclusive"
                    })

            # Skip to max cap check (handled at the end)
            pass

        else:
            # =====================================================================
            # No EXCLUSIVE discount - process INCREMENTAL and ABSOLUTE modes
            # =====================================================================

            # Check if campaign is applied (for bulk exclusion check)
            campaign_applied = discount_values['campaign']['percent'] > 0

            # -----------------------------------------------------------------
            # STEP 2: Handle INCREMENTAL discounts (they all add up)
            # -----------------------------------------------------------------
            for source in ['campaign', 'bulk', 'loyalty', 'vip']:
                data = discount_values[source]
                if data['percent'] <= 0:
                    continue

                mode = data['config'].get('mode', 'incremental')

                # Check bulk exclusion with campaign
                if source == 'bulk' and campaign_applied and data['config'].get('exclude_with_campaign', False):
                    excluded.append({'source': 'bulk', 'reason': 'Excluded when campaign applies'})
                    continue

                if mode == 'incremental':
                    total_percent += data['percent']
                    breakdown.append({
                        'source': source,
                        'percent': float(data['percent']),
                        'mode': 'incremental'
                    })
                    applied.append({
                        'source': source,
                        'percent': float(data['percent']),
                        'name': data['name']
                    })

            # -----------------------------------------------------------------
            # STEP 3: Handle ABSOLUTE discounts (best one wins)
            # -----------------------------------------------------------------
            absolute_candidates = []

            for source in ['campaign', 'bulk', 'loyalty', 'vip']:
                data = discount_values[source]
                if data['percent'] <= 0:
                    continue

                mode = data['config'].get('mode', 'incremental')

                # Check bulk exclusion with campaign
                if source == 'bulk' and campaign_applied and data['config'].get('exclude_with_campaign', False):
                    continue  # Already excluded above

                if mode == 'absolute':
                    absolute_candidates.append({
                        'source': source,
                        'percent': data['percent'],
                        'name': data['name']
                    })

            # Pick the best absolute discount and ADD to incrementals
            # ABSOLUTE mode: Best absolute discount STACKS with incrementals (Updated 2025-11-29)
            # - Multiple absolutes compete among themselves (best one wins)
            # - The winning absolute then ADDS to the incremental total
            logger.info(f"  Absolute candidates: {absolute_candidates}")
            logger.info(f"  Incremental total after STEP 2: {total_percent}%")

            if absolute_candidates:
                best_absolute = max(absolute_candidates, key=lambda x: x['percent'])
                logger.info(f"  Best absolute: {best_absolute['source']} at {best_absolute['percent']}%")

                # ABSOLUTE mode: Add best absolute to incrementals (they stack)
                total_percent += best_absolute['percent']
                logger.info(f"  --> Absolute STACKS with incrementals: {total_percent}%")

                breakdown.append({
                    'source': best_absolute['source'],
                    'percent': float(best_absolute['percent']),
                    'mode': 'absolute (stacked)'
                })
                applied.append({
                    'source': best_absolute['source'],
                    'percent': float(best_absolute['percent']),
                    'name': best_absolute['name']
                })

                # Mark non-winning absolute candidates as excluded
                for candidate in absolute_candidates:
                    if candidate['source'] != best_absolute['source']:
                        excluded.append({
                            'source': candidate['source'],
                            'reason': f"Lower than {best_absolute['source']} ({float(candidate['percent'])}% < {float(best_absolute['percent'])}%)"
                        })

        # =====================================================================
        # STEP 6: Apply Standard Discount (Fallback)
        # =====================================================================
        standard_percent = Decimal(str(standard.get('percent', 0)))
        if total_percent == 0 and standard_percent > 0:
            total_percent = standard_percent
            breakdown.append({
                'source': 'standard',
                'percent': float(standard_percent),
                'mode': 'fallback'
            })
            applied.append({
                'source': 'standard',
                'percent': float(standard_percent),
                'name': 'Standard Discount'
            })

        # =====================================================================
        # STEP 7: Apply Max Discount Cap
        # =====================================================================
        capped = False
        cap_applied = None
        max_cap = stacking_config.get('max_total_discount')

        if max_cap is not None and total_percent > Decimal(str(max_cap)):
            cap_applied = float(total_percent)
            total_percent = Decimal(str(max_cap))
            capped = True
            breakdown.append({
                'source': 'cap',
                'percent': float(max_cap),
                'mode': f'capped from {cap_applied}%'
            })

        logger.info(f"  === FINAL RESULT ===")
        logger.info(f"  Total percent: {total_percent}%")
        logger.info(f"  Applied: {applied}")
        logger.info(f"  Excluded: {excluded}")
        logger.info(f"  Capped: {capped}")

        return {
            'total_percent': float(total_percent),
            'breakdown': breakdown,
            'applied_discounts': applied,
            'excluded_discounts': excluded,
            'capped': capped,
            'cap_applied': cap_applied
        }

    @staticmethod
    def get_max_discount_preview(
        session: Session,
        hospital_id: str,
        patient_id: str = None,
        item_type: str = None,
        item_id: str = None,
        item_price: Decimal = None,
        campaigns: List[Dict] = None
    ) -> Dict:
        """
        Get maximum possible discount preview for dashboard/simulation.

        This method uses the SAME stacking logic as actual invoice calculation,
        ensuring consistency across all modules.

        Args:
            session: Database session
            hospital_id: Hospital UUID
            patient_id: Patient UUID (for loyalty/VIP)
            item_type: 'Service', 'Medicine', 'Package' (optional)
            item_id: Item UUID (optional)
            item_price: Item price for amount-to-% conversion
            campaigns: List of applicable campaign dicts (optional, pre-fetched)

        Returns:
            {
                'max_discount_percent': X,
                'breakdown': [...],
                'stacking_config': {...},
                'discounts_available': {...}
            }
        """
        from app.models.master import Patient

        # Get stacking configuration
        stacking_config = DiscountService.get_stacking_config(session, hospital_id)

        # Collect all available discounts
        discounts = {
            'campaign': {'percent': 0, 'applicable': False},
            'bulk': {'percent': 0, 'applicable': False},
            'loyalty': {'percent': 0, 'applicable': False, 'is_valid_today': False},
            'vip': {'percent': 0, 'applicable': False},
            'standard': {'percent': 0, 'applicable': False}
        }

        # Get best campaign discount
        if campaigns:
            best_campaign = None
            best_value = 0
            for c in campaigns:
                if c.get('auto_apply') and not c.get('is_personalized'):
                    value = c.get('discount_value', 0)
                    if c.get('discount_type') == 'percentage' and value > best_value:
                        best_value = value
                        best_campaign = c

            if best_campaign:
                discounts['campaign'] = {
                    'percent': best_value,
                    'applicable': True,
                    'type': best_campaign.get('discount_type', 'percentage'),
                    'name': best_campaign.get('campaign_name', 'Campaign'),
                    'promotion_type': best_campaign.get('promotion_type', 'simple_discount')
                }

        # Get bulk discount (if item selected)
        if item_type and item_id:
            if item_type.lower() in ['service', 'services']:
                service = session.query(Service).filter_by(service_id=item_id).first()
                if service and getattr(service, 'bulk_discount_eligible', False):
                    bulk_percent = float(service.bulk_discount_percent or 0)
                    if bulk_percent > 0:
                        discounts['bulk'] = {
                            'percent': bulk_percent,
                            'applicable': True,
                            'name': 'Bulk Discount'
                        }
            elif item_type.lower() in ['medicine', 'medicines']:
                medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
                if medicine and getattr(medicine, 'bulk_discount_eligible', False):
                    bulk_percent = float(medicine.bulk_discount_percent or 0)
                    if bulk_percent > 0:
                        discounts['bulk'] = {
                            'percent': bulk_percent,
                            'applicable': True,
                            'name': 'Bulk Discount'
                        }

        # Get loyalty discount (if patient selected)
        if patient_id:
            loyalty_wallet = session.query(PatientLoyaltyWallet).filter(
                PatientLoyaltyWallet.patient_id == patient_id,
                PatientLoyaltyWallet.is_active == True
            ).first()

            if loyalty_wallet:
                card_type = session.query(LoyaltyCardType).filter_by(
                    card_type_id=loyalty_wallet.card_type_id,
                    is_active=True
                ).first()

                if card_type:
                    today = date.today()
                    valid_from = getattr(loyalty_wallet, 'valid_from', None)
                    valid_to = getattr(loyalty_wallet, 'valid_to', None)
                    is_valid = True
                    if valid_from and today < valid_from:
                        is_valid = False
                    if valid_to and today > valid_to:
                        is_valid = False

                    discounts['loyalty'] = {
                        'percent': float(card_type.discount_percent or 0),
                        'applicable': True,
                        'is_valid_today': is_valid,
                        'card_type': card_type.card_type_name
                    }

            # Get VIP status
            patient = session.query(Patient).filter_by(patient_id=patient_id).first()
            if patient and getattr(patient, 'is_special_group', False):
                # TODO: Get VIP discount from hospital settings
                # For now, VIP is just a flag for campaign targeting
                discounts['vip'] = {
                    'percent': 0,  # VIP discount percentage should be configurable
                    'applicable': False
                }

        # Get standard discount (if item selected)
        if item_type and item_id:
            if item_type.lower() in ['service', 'services']:
                service = session.query(Service).filter_by(service_id=item_id).first()
                if service and service.standard_discount_percent:
                    discounts['standard'] = {
                        'percent': float(service.standard_discount_percent),
                        'applicable': True,
                        'name': 'Standard Discount'
                    }

        # Calculate stacked discount
        result = DiscountService.calculate_stacked_discount(
            discounts, stacking_config, item_price
        )

        return {
            'max_discount_percent': result['total_percent'],
            'breakdown': result['breakdown'],
            'applied_discounts': result['applied_discounts'],
            'excluded_discounts': result['excluded_discounts'],
            'stacking_config': stacking_config,
            'discounts_available': discounts,
            'capped': result['capped']
        }
