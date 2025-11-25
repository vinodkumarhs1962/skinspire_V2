"""
Discount Service - Handles all discount calculations for services
Supports bulk discounts, loyalty discounts, and campaign-based discounts
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)

from app.models.master import (
    Service, Hospital, Medicine, Package, LoyaltyCardType,
    DiscountApplicationLog, PromotionCampaign, PromotionUsageLog
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
        if not service or not service.bulk_discount_percent or service.bulk_discount_percent == 0:
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
        if not medicine or not medicine.bulk_discount_percent or medicine.bulk_discount_percent == 0:
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
        - Reads item.loyalty_discount_percent from Service/Medicine/Package model
        - Applies max_discount cap if set
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
            DiscountCalculationResult if patient has loyalty card and item has loyalty_discount_percent
            None if patient doesn't have loyalty card or no loyalty discount configured
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

        # Check if item has loyalty_discount_percent configured
        if not hasattr(item, 'loyalty_discount_percent') or not item.loyalty_discount_percent:
            return None

        if item.loyalty_discount_percent == 0:
            return None

        # Calculate discount
        original_price = unit_price * quantity
        discount_percent = item.loyalty_discount_percent

        # Apply max_discount cap if set
        if hasattr(item, 'max_discount') and item.max_discount is not None:
            if discount_percent > item.max_discount:
                discount_percent = item.max_discount
                logger.info(f"{item_type} {item_name} loyalty discount capped at max_discount: {item.max_discount}%")

        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        card_type = patient_wallet.card_type

        return DiscountCalculationResult(
            discount_type='loyalty_percent',
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
        promotions = session.query(PromotionCampaign).filter(
            and_(
                PromotionCampaign.hospital_id == hospital_id,
                PromotionCampaign.is_active == True,
                PromotionCampaign.is_deleted == False,
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

        # Check each promotion for eligibility
        for promotion in promotions:
            # NEW: Dispatch based on promotion_type
            if promotion.promotion_type == 'buy_x_get_y':
                # Handle Buy X Get Y promotions
                if invoice_items is None:
                    logger.debug(f"Skipping buy_x_get_y promotion {promotion.campaign_name} - no invoice context provided")
                    continue  # Need invoice context for buy_x_get_y

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

                # Check if specific items list (if set)
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
                        'auto_applied': promotion.auto_apply
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
        invoice_items: List[Dict] = None  # NEW: Full invoice context for buy_x_get_y
    ) -> DiscountCalculationResult:
        """
        Calculate all applicable discounts using priority-based selection

        Priority Logic:
        1. Promotion (priority 1) - Always wins if active
        2. Bulk (priority 2) OR Loyalty % (priority 2) - Depends on loyalty_discount_mode
           - 'absolute': Pick the higher discount
           - 'additional': Add bulk% + loyalty% together
        3. Standard (priority 4) - Fallback when no other discounts apply

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

        Returns:
            DiscountCalculationResult with the best discount (or no discount)
        """
        original_price = unit_price * quantity

        # Get hospital loyalty_discount_mode
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        loyalty_mode = hospital.loyalty_discount_mode if hospital else 'absolute'

        # Calculate all applicable discounts
        discounts = {}

        # 1. PROMOTION (Priority 1 - Highest)
        promotion_discount = DiscountService.calculate_promotion_discount(
            session, hospital_id, patient_id, item_type, item_id, unit_price, quantity, invoice_date,
            invoice_items=invoice_items  # NEW: Pass invoice context for buy_x_get_y
        )
        if promotion_discount:
            discounts['promotion'] = promotion_discount

            # Before returning promotion, collect all other eligible discounts for transparency
            all_eligible = [
                {
                    'type': 'promotion',
                    'percent': float(promotion_discount.discount_percent),
                    'amount': float(promotion_discount.discount_amount),
                    'applied': True,
                    'reason': 'Highest priority - applied',
                    'campaign_name': promotion_discount.metadata.get('campaign_name', 'Promotion Campaign')
                }
            ]

            # Check bulk discount eligibility
            bulk_discount_check = None
            if item_type == 'Service':
                bulk_discount_check = DiscountService.calculate_bulk_discount(
                    session, hospital_id, item_id, total_item_count, unit_price, quantity
                )
            elif item_type == 'Medicine':
                bulk_discount_check = DiscountService.calculate_medicine_bulk_discount(
                    session, hospital_id, item_id, total_item_count, unit_price, quantity
                )

            if bulk_discount_check:
                all_eligible.append({
                    'type': 'bulk',
                    'percent': float(bulk_discount_check.discount_percent),
                    'amount': float(bulk_discount_check.discount_amount),
                    'applied': False,
                    'reason': 'Lower priority - not applied'
                })

            # Check loyalty discount eligibility
            loyalty_discount_check = DiscountService.calculate_loyalty_percentage_discount(
                session, hospital_id, patient_id, item_type, item_id, unit_price, quantity
            )
            if loyalty_discount_check:
                all_eligible.append({
                    'type': 'loyalty',
                    'percent': float(loyalty_discount_check.discount_percent),
                    'amount': float(loyalty_discount_check.discount_amount),
                    'applied': False,
                    'reason': 'Lower priority - not applied',
                    'card_type_name': loyalty_discount_check.metadata.get('card_type_name', 'Loyalty Card')
                })

            # Check standard discount eligibility
            standard_discount_check = DiscountService.calculate_standard_discount(
                session, item_type, item_id, unit_price, quantity
            )
            if standard_discount_check:
                all_eligible.append({
                    'type': 'standard',
                    'percent': float(standard_discount_check.discount_percent),
                    'amount': float(standard_discount_check.discount_amount),
                    'applied': False,
                    'reason': 'Lower priority - not applied'
                })

            # Promotion wins - return it with all eligible discounts metadata
            promotion_discount.metadata['selection_reason'] = 'Promotion has highest priority (1)'
            promotion_discount.metadata['all_eligible_discounts'] = all_eligible
            return promotion_discount

        # 2. BULK DISCOUNT (Priority 2)
        bulk_discount = None
        if item_type == 'Service':
            bulk_discount = DiscountService.calculate_bulk_discount(
                session, hospital_id, item_id, total_item_count, unit_price, quantity
            )
        elif item_type == 'Medicine':
            bulk_discount = DiscountService.calculate_medicine_bulk_discount(
                session, hospital_id, item_id, total_item_count, unit_price, quantity
            )
        # Note: Packages don't support bulk discount

        if bulk_discount:
            discounts['bulk'] = bulk_discount

        # 3. LOYALTY % DISCOUNT (Priority 2)
        loyalty_discount = DiscountService.calculate_loyalty_percentage_discount(
            session, hospital_id, patient_id, item_type, item_id, unit_price, quantity
        )
        if loyalty_discount:
            discounts['loyalty_percent'] = loyalty_discount

        # Handle bulk + loyalty based on loyalty_discount_mode
        if 'bulk' in discounts and 'loyalty_percent' in discounts:
            if loyalty_mode == 'additional':
                # Add both percentages together
                combined_percent = bulk_discount.discount_percent + loyalty_discount.discount_percent

                # Apply max_discount cap
                item = None
                if item_type == 'Service':
                    item = session.query(Service).filter_by(service_id=item_id).first()
                elif item_type == 'Medicine':
                    item = session.query(Medicine).filter_by(medicine_id=item_id).first()
                elif item_type == 'Package':
                    item = session.query(Package).filter_by(package_id=item_id).first()

                if item and hasattr(item, 'max_discount') and item.max_discount is not None:
                    if combined_percent > item.max_discount:
                        combined_percent = item.max_discount
                        logger.info(f"Combined discount capped at max_discount: {item.max_discount}%")

                combined_amount = (original_price * combined_percent) / 100
                combined_price = original_price - combined_amount

                return DiscountCalculationResult(
                    discount_type='bulk_plus_loyalty',
                    discount_percent=combined_percent,
                    discount_amount=combined_amount,
                    final_price=combined_price,
                    original_price=original_price,
                    card_type_id=loyalty_discount.card_type_id,
                    metadata={
                        'selection_reason': 'Combined bulk + loyalty (additional mode)',
                        'loyalty_mode': 'additional',
                        'bulk_percent': float(bulk_discount.discount_percent),
                        'loyalty_percent': float(loyalty_discount.discount_percent),
                        'bulk_amount': float(bulk_discount.discount_amount),
                        'loyalty_amount': float(loyalty_discount.discount_amount),
                        'priority': 2,
                        'all_eligible_discounts': [
                            {
                                'type': 'bulk',
                                'percent': float(bulk_discount.discount_percent),
                                'amount': float(bulk_discount.discount_amount),
                                'applied': True,
                                'reason': f'Quantity {total_item_count} meets threshold'
                            },
                            {
                                'type': 'loyalty',
                                'percent': float(loyalty_discount.discount_percent),
                                'amount': float(loyalty_discount.discount_amount),
                                'applied': True,
                                'card_type_name': loyalty_discount.metadata.get('card_type_name', 'Loyalty Card')
                            }
                        ]
                    }
                )
            else:  # 'absolute' mode
                # Pick the higher discount
                best = bulk_discount if bulk_discount.discount_percent >= loyalty_discount.discount_percent else loyalty_discount
                best.metadata['selection_reason'] = f'Higher discount (absolute mode): {best.discount_type}'
                best.metadata['other_eligible_discounts'] = [
                    {
                        'type': 'bulk' if best.discount_type != 'bulk' else 'loyalty_percent',
                        'percent': float(bulk_discount.discount_percent if best.discount_type != 'bulk' else loyalty_discount.discount_percent),
                        'amount': float(bulk_discount.discount_amount if best.discount_type != 'bulk' else loyalty_discount.discount_amount)
                    }
                ]
                return best

        # Only one of bulk or loyalty applies
        if 'bulk' in discounts:
            bulk_discount.metadata['selection_reason'] = 'Bulk discount (no loyalty available)'

            # Add all eligible discounts info
            all_eligible = [
                {
                    'type': 'bulk',
                    'percent': float(bulk_discount.discount_percent),
                    'amount': float(bulk_discount.discount_amount),
                    'applied': True,
                    'reason': f'Quantity {total_item_count} meets threshold'
                }
            ]

            # Check if loyalty exists but not applied
            if 'loyalty_percent' in discounts:
                all_eligible.append({
                    'type': 'loyalty',
                    'percent': float(loyalty_discount.discount_percent),
                    'amount': float(loyalty_discount.discount_amount),
                    'applied': False,
                    'reason': 'Available but bulk discount is higher',
                    'card_type_name': loyalty_discount.metadata.get('card_type_name', 'Loyalty Card')
                })

            # Check for standard discount
            standard_discount = DiscountService.calculate_standard_discount(
                session, item_type, item_id, unit_price, quantity
            )
            if standard_discount:
                all_eligible.append({
                    'type': 'standard',
                    'percent': float(standard_discount.discount_percent),
                    'amount': float(standard_discount.discount_amount),
                    'applied': False,
                    'reason': 'Lower priority - not applied'
                })

            bulk_discount.metadata['all_eligible_discounts'] = all_eligible
            return bulk_discount

        if 'loyalty_percent' in discounts:
            loyalty_discount.metadata['selection_reason'] = 'Loyalty discount (no bulk available)'

            # Add all eligible discounts info
            all_eligible = [
                {
                    'type': 'loyalty',
                    'percent': float(loyalty_discount.discount_percent),
                    'amount': float(loyalty_discount.discount_amount),
                    'applied': True,
                    'card_type_name': loyalty_discount.metadata.get('card_type_name', 'Loyalty Card')
                }
            ]

            # Check for standard discount
            standard_discount = DiscountService.calculate_standard_discount(
                session, item_type, item_id, unit_price, quantity
            )
            if standard_discount:
                all_eligible.append({
                    'type': 'standard',
                    'percent': float(standard_discount.discount_percent),
                    'amount': float(standard_discount.discount_amount),
                    'applied': False,
                    'reason': 'Lower priority - not applied'
                })

            loyalty_discount.metadata['all_eligible_discounts'] = all_eligible
            return loyalty_discount

        # 4. STANDARD DISCOUNT (Priority 4 - Fallback)
        standard_discount = DiscountService.calculate_standard_discount(
            session, item_type, item_id, unit_price, quantity
        )
        if standard_discount:
            standard_discount.metadata['selection_reason'] = 'Standard discount (fallback)'
            standard_discount.metadata['all_eligible_discounts'] = [
                {
                    'type': 'standard',
                    'percent': float(standard_discount.discount_percent),
                    'amount': float(standard_discount.discount_amount),
                    'applied': True,
                    'reason': 'Only available discount'
                }
            ]
            return standard_discount

        # No discounts apply
        return DiscountCalculationResult(
            discount_type='none',
            discount_percent=Decimal('0'),
            discount_amount=Decimal('0'),
            final_price=original_price,
            original_price=original_price,
            metadata={'reason': 'No applicable discounts found'}
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
        respect_max_discount: bool = True
    ) -> List[Dict]:
        """
        Apply multi-discount logic to all items (Services, Medicines, Packages) in an invoice

        Uses the new 4-discount system:
        - Standard (fallback)
        - Bulk (services/medicines only, based on quantity)
        - Loyalty % (all types, requires loyalty card)
        - Promotion (all types, highest priority)

        Args:
            session: Database session
            hospital_id: Hospital ID
            patient_id: Patient ID
            line_items: List of line item dictionaries (Services, Medicines, Packages)
            invoice_date: Invoice date (defaults to today)
            respect_max_discount: Whether to enforce max_discount

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
                    f"Package count={len(package_items)} items")

        # Process each SERVICE item
        for item in service_items:
            service_id = item.get('item_id') or item.get('service_id')
            if not service_id:
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
                invoice_items=line_items  # NEW: Pass full invoice context for buy_x_get_y
            )

            # Apply max_discount cap (EXCEPT for promotions - they have priority)
            # Promotions (especially Buy X Get Y) should not be capped by max_discount
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion':
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
                invoice_items=line_items  # NEW: Pass full invoice context for buy_x_get_y
            )

            # Apply max_discount cap (EXCEPT for promotions - they have priority)
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion':
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
                invoice_items=line_items  # NEW: Pass full invoice context for buy_x_get_y
            )

            # Apply max_discount cap (EXCEPT for promotions - they have priority)
            if respect_max_discount and best_discount.discount_percent > 0 and best_discount.discount_type != 'promotion':
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
