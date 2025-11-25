"""
Wallet Service
Handles all loyalty wallet operations including tier management, points loading,
redemption, refunds, and expiry management.
"""

from decimal import Decimal
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Optional, List
from uuid import UUID
import uuid

from sqlalchemy import and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

from app.models.transaction import (
    PatientLoyaltyWallet,
    WalletTransaction,
    WalletPointsBatch,
    LoyaltyCardTierHistory
)
from app.models.master import LoyaltyCardType, Patient
from app.services.database_service import get_db_session
from flask import current_app


class WalletError(Exception):
    """Base wallet exception"""
    pass


class InsufficientPointsError(WalletError):
    """Raised when wallet has insufficient points"""
    pass


class ExpiredPointsError(WalletError):
    """Raised when trying to use expired points"""
    pass


class InvalidTierUpgradeError(WalletError):
    """Raised when tier upgrade is invalid"""
    pass


class WalletService:
    """
    Service for managing patient loyalty wallets

    Responsibilities:
    - Wallet CRUD operations
    - Tier management and upgrades
    - Point load/redeem/refund operations
    - Balance validation and checks
    - FIFO batch tracking
    - GL integration calls
    """

    @staticmethod
    def get_or_create_wallet(patient_id: str, hospital_id: str, user_id: str = None) -> Dict:
        """
        Get existing wallet or create new one for patient

        Args:
            patient_id: UUID of patient
            hospital_id: UUID of hospital
            user_id: User creating wallet (optional)

        Returns:
            Dict with wallet details
        """
        try:
            with get_db_session() as session:
                # Try to get existing wallet
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.hospital_id == UUID(hospital_id)
                ).first()

                if wallet:
                    return {
                        'wallet_id': str(wallet.wallet_id),
                        'patient_id': str(wallet.patient_id),
                        'points_balance': wallet.points_balance,
                        'points_value': float(wallet.points_value),
                        'wallet_status': wallet.wallet_status,
                        'is_active': wallet.is_active,
                        'card_type_id': str(wallet.card_type_id) if wallet.card_type_id else None,
                        'total_amount_loaded': float(wallet.total_amount_loaded),
                        'total_points_loaded': wallet.total_points_loaded,
                        'total_points_redeemed': wallet.total_points_redeemed,
                        'exists': True
                    }

                # Create new wallet
                new_wallet = PatientLoyaltyWallet(
                    patient_id=UUID(patient_id),
                    hospital_id=UUID(hospital_id),
                    points_balance=0,
                    points_value=Decimal('0'),
                    wallet_status='active',
                    is_active=True,
                    created_by=user_id
                )
                session.add(new_wallet)
                session.commit()

                return {
                    'wallet_id': str(new_wallet.wallet_id),
                    'patient_id': str(new_wallet.patient_id),
                    'points_balance': 0,
                    'points_value': 0.0,
                    'wallet_status': 'active',
                    'is_active': True,
                    'card_type_id': None,
                    'total_amount_loaded': 0.0,
                    'total_points_loaded': 0,
                    'total_points_redeemed': 0,
                    'exists': False
                }

        except Exception as e:
            current_app.logger.error(f"Error in get_or_create_wallet: {str(e)}")
            raise WalletError(f"Failed to get/create wallet: {str(e)}")

    @staticmethod
    def load_tier(
        patient_id: str,
        card_type_id: str,
        amount_paid: Decimal,
        payment_mode: str,
        payment_reference: str = None,
        user_id: str = None
    ) -> Dict:
        """
        Load wallet with tier points
        - Validates tier requirements
        - Credits base + bonus points
        - Creates tier history record
        - Creates FIFO batch with 12-month expiry

        Args:
            patient_id: UUID of patient
            card_type_id: UUID of loyalty card type
            amount_paid: Amount paid by patient
            payment_mode: Payment method (cash, card, upi, etc.)
            payment_reference: Payment reference number
            user_id: User performing the operation

        Returns:
            Dict with transaction details
        """
        try:
            with get_db_session() as session:
                # Get tier configuration
                card_type = session.query(LoyaltyCardType).filter(
                    LoyaltyCardType.card_type_id == UUID(card_type_id)
                ).first()

                if not card_type:
                    raise WalletError(f"Card type {card_type_id} not found")

                # Validate payment amount
                if amount_paid < card_type.min_payment_amount:
                    raise WalletError(
                        f"Payment amount ₹{amount_paid} is less than required "
                        f"₹{card_type.min_payment_amount} for {card_type.card_type_name}"
                    )

                # Get or create wallet
                wallet_info = WalletService.get_or_create_wallet(
                    patient_id=patient_id,
                    hospital_id=str(card_type.hospital_id),
                    user_id=user_id
                )

                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.wallet_id == UUID(wallet_info['wallet_id'])
                ).first()

                # Calculate points
                base_points = int(amount_paid)  # 1:1 ratio
                bonus_points = card_type.total_points_credited - int(card_type.min_payment_amount)
                total_points = card_type.total_points_credited

                # Calculate expiry date (12 months)
                load_date = date.today()
                expiry_date = load_date + timedelta(days=card_type.validity_months * 30)

                # Get next batch sequence
                max_sequence = session.query(func.max(WalletPointsBatch.batch_sequence)).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id
                ).scalar() or 0

                # Create wallet transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='load',
                    transaction_date=datetime.now(timezone.utc),
                    amount_paid=amount_paid,
                    base_points=base_points,
                    bonus_points=bonus_points,
                    total_points_loaded=total_points,
                    expiry_date=expiry_date,
                    balance_before=wallet.points_balance,
                    balance_after=wallet.points_balance + total_points,
                    payment_mode=payment_mode,
                    payment_reference=payment_reference,
                    created_by=user_id,
                    notes=f"Tier load: {card_type.card_type_name} - ₹{amount_paid}"
                )
                session.add(transaction)
                session.flush()

                # Create points batch for FIFO tracking
                batch = WalletPointsBatch(
                    wallet_id=wallet.wallet_id,
                    load_transaction_id=transaction.transaction_id,
                    points_loaded=total_points,
                    points_remaining=total_points,
                    points_redeemed=0,
                    points_expired=0,
                    load_date=load_date,
                    expiry_date=expiry_date,
                    is_expired=False,
                    batch_sequence=max_sequence + 1
                )
                session.add(batch)

                # Update wallet
                wallet.points_balance += total_points
                wallet.points_value += Decimal(str(total_points))
                wallet.total_amount_loaded += amount_paid
                wallet.total_points_loaded += total_points
                wallet.total_bonus_points += bonus_points
                wallet.card_type_id = UUID(card_type_id)
                wallet.updated_by = user_id
                wallet.updated_at = datetime.now(timezone.utc)

                # Create tier history
                tier_history = LoyaltyCardTierHistory(
                    wallet_id=wallet.wallet_id,
                    patient_id=wallet.patient_id,
                    hospital_id=wallet.hospital_id,
                    card_type_id=UUID(card_type_id),
                    previous_card_type_id=None,
                    change_type='new',
                    amount_paid=amount_paid,
                    points_credited=total_points,
                    bonus_points=bonus_points,
                    valid_from=load_date,
                    valid_until=expiry_date,
                    transaction_id=transaction.transaction_id,
                    created_by=user_id
                )
                session.add(tier_history)

                session.commit()

                # TODO: Call GL service to create wallet load GL entries
                # gl_service.create_wallet_load_gl_entries(...)

                return {
                    'success': True,
                    'transaction_id': str(transaction.transaction_id),
                    'batch_id': str(batch.batch_id),
                    'wallet_id': str(wallet.wallet_id),
                    'points_credited': total_points,
                    'base_points': base_points,
                    'bonus_points': bonus_points,
                    'new_balance': wallet.points_balance,
                    'expiry_date': expiry_date.isoformat(),
                    'tier_name': card_type.card_type_name,
                    'tier_discount_percent': float(card_type.discount_percent)
                }

        except WalletError:
            raise
        except Exception as e:
            current_app.logger.error(f"Error in load_tier: {str(e)}")
            raise WalletError(f"Failed to load tier: {str(e)}")

    @staticmethod
    def upgrade_tier(
        patient_id: str,
        new_card_type_id: str,
        amount_paid: Decimal,
        payment_mode: str,
        payment_reference: str = None,
        user_id: str = None
    ) -> Dict:
        """
        Upgrade patient to higher tier
        - Validates upgrade path
        - Calculates balance payment
        - Credits additional points
        - Extends validity period

        Args:
            patient_id: UUID of patient
            new_card_type_id: UUID of new tier
            amount_paid: Balance amount paid
            payment_mode: Payment method
            payment_reference: Payment reference
            user_id: User performing operation

        Returns:
            Dict with upgrade details
        """
        try:
            with get_db_session() as session:
                # Get wallet
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.is_active == True
                ).first()

                if not wallet:
                    raise WalletError(f"No active wallet found for patient {patient_id}")

                if not wallet.card_type_id:
                    raise InvalidTierUpgradeError("Patient has no current tier. Use load_tier instead.")

                # Get current and new tier details
                current_tier = session.query(LoyaltyCardType).filter(
                    LoyaltyCardType.card_type_id == wallet.card_type_id
                ).first()

                new_tier = session.query(LoyaltyCardType).filter(
                    LoyaltyCardType.card_type_id == UUID(new_card_type_id)
                ).first()

                if not new_tier:
                    raise WalletError(f"New tier {new_card_type_id} not found")

                # Validate upgrade (new tier should have higher payment requirement)
                if new_tier.min_payment_amount <= current_tier.min_payment_amount:
                    raise InvalidTierUpgradeError(
                        f"Cannot upgrade from {current_tier.card_type_name} to "
                        f"{new_tier.card_type_name}. New tier must have higher requirements."
                    )

                # Calculate expected balance payment
                expected_balance = new_tier.min_payment_amount - current_tier.min_payment_amount
                if amount_paid < expected_balance:
                    raise WalletError(
                        f"Upgrade requires ₹{expected_balance}. Paid: ₹{amount_paid}"
                    )

                # Calculate additional points
                additional_points = new_tier.total_points_credited - current_tier.total_points_credited
                base_points = int(amount_paid)
                bonus_points = additional_points - base_points

                # Calculate new expiry (12 months from upgrade)
                load_date = date.today()
                expiry_date = load_date + timedelta(days=new_tier.validity_months * 30)

                # Get next batch sequence
                max_sequence = session.query(func.max(WalletPointsBatch.batch_sequence)).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id
                ).scalar() or 0

                # Create transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='load',
                    transaction_date=datetime.now(timezone.utc),
                    amount_paid=amount_paid,
                    base_points=base_points,
                    bonus_points=bonus_points,
                    total_points_loaded=additional_points,
                    expiry_date=expiry_date,
                    balance_before=wallet.points_balance,
                    balance_after=wallet.points_balance + additional_points,
                    payment_mode=payment_mode,
                    payment_reference=payment_reference,
                    created_by=user_id,
                    notes=f"Tier upgrade: {current_tier.card_type_name} → {new_tier.card_type_name}"
                )
                session.add(transaction)
                session.flush()

                # Create points batch
                batch = WalletPointsBatch(
                    wallet_id=wallet.wallet_id,
                    load_transaction_id=transaction.transaction_id,
                    points_loaded=additional_points,
                    points_remaining=additional_points,
                    load_date=load_date,
                    expiry_date=expiry_date,
                    batch_sequence=max_sequence + 1
                )
                session.add(batch)

                # Update wallet
                previous_tier_id = wallet.card_type_id
                wallet.points_balance += additional_points
                wallet.points_value += Decimal(str(additional_points))
                wallet.total_amount_loaded += amount_paid
                wallet.total_points_loaded += additional_points
                wallet.total_bonus_points += bonus_points
                wallet.card_type_id = UUID(new_card_type_id)
                wallet.updated_by = user_id

                # Create tier history
                tier_history = LoyaltyCardTierHistory(
                    wallet_id=wallet.wallet_id,
                    patient_id=wallet.patient_id,
                    hospital_id=wallet.hospital_id,
                    card_type_id=UUID(new_card_type_id),
                    previous_card_type_id=previous_tier_id,
                    change_type='upgrade',
                    amount_paid=amount_paid,
                    points_credited=additional_points,
                    bonus_points=bonus_points,
                    valid_from=load_date,
                    valid_until=expiry_date,
                    transaction_id=transaction.transaction_id,
                    created_by=user_id
                )
                session.add(tier_history)

                session.commit()

                return {
                    'success': True,
                    'transaction_id': str(transaction.transaction_id),
                    'previous_tier': current_tier.card_type_name,
                    'new_tier': new_tier.card_type_name,
                    'additional_points': additional_points,
                    'new_balance': wallet.points_balance,
                    'new_discount_percent': float(new_tier.discount_percent)
                }

        except (WalletError, InvalidTierUpgradeError):
            raise
        except Exception as e:
            current_app.logger.error(f"Error in upgrade_tier: {str(e)}")
            raise WalletError(f"Failed to upgrade tier: {str(e)}")

    @staticmethod
    def get_available_balance(patient_id: str, hospital_id: str) -> Dict:
        """
        Get current wallet balance with expiry info

        Returns: {
            'wallet_id': str,
            'points_balance': int,
            'points_value': float,
            'expiry_date': date,  # Nearest expiry
            'is_expiring_soon': bool,  # Expires within 30 days
            'is_expired': bool,
            'tier_name': str,
            'tier_code': str,
            'tier_discount_percent': float
        }
        """
        try:
            with get_db_session(read_only=True) as session:
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.hospital_id == UUID(hospital_id),
                    PatientLoyaltyWallet.is_active == True
                ).first()

                if not wallet:
                    return {
                        'wallet_id': None,
                        'points_balance': 0,
                        'points_value': 0.0,
                        'has_wallet': False
                    }

                # Get nearest expiry date from active batches
                nearest_batch = session.query(WalletPointsBatch).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id,
                    WalletPointsBatch.is_expired == False,
                    WalletPointsBatch.points_remaining > 0
                ).order_by(WalletPointsBatch.expiry_date.asc()).first()

                expiry_date = nearest_batch.expiry_date if nearest_batch else None
                is_expired = expiry_date < date.today() if expiry_date else False
                is_expiring_soon = (
                    expiry_date <= (date.today() + timedelta(days=30))
                    if expiry_date and not is_expired
                    else False
                )

                # Get tier info
                tier_info = {}
                if wallet.card_type_id:
                    card_type = session.query(LoyaltyCardType).filter(
                        LoyaltyCardType.card_type_id == wallet.card_type_id
                    ).first()
                    if card_type:
                        tier_info = {
                            'tier_name': card_type.card_type_name,
                            'tier_code': card_type.card_type_code,
                            'tier_discount_percent': float(card_type.discount_percent)
                        }

                return {
                    'wallet_id': str(wallet.wallet_id),
                    'points_balance': wallet.points_balance,
                    'points_value': float(wallet.points_value),
                    'expiry_date': expiry_date.isoformat() if expiry_date else None,
                    'is_expiring_soon': is_expiring_soon,
                    'is_expired': is_expired,
                    'has_wallet': True,
                    **tier_info
                }

        except Exception as e:
            current_app.logger.error(f"Error in get_available_balance: {str(e)}")
            raise WalletError(f"Failed to get wallet balance: {str(e)}")

    @staticmethod
    def validate_redemption(patient_id: str, points_amount: int, hospital_id: str = None) -> Dict:
        """
        Validate if redemption is possible
        - Check sufficient balance
        - Check expiry status

        Returns:
            Dict with validation result: {'valid': bool, 'message': str, 'available': int}
        """
        try:
            balance_info = WalletService.get_available_balance(patient_id, hospital_id)

            if not balance_info.get('has_wallet'):
                return {
                    'valid': False,
                    'message': 'No active wallet found',
                    'available': 0
                }

            if balance_info.get('is_expired'):
                return {
                    'valid': False,
                    'message': 'Wallet points have expired',
                    'available': 0
                }

            available_points = balance_info['points_balance']

            if points_amount > available_points:
                return {
                    'valid': False,
                    'message': f'Insufficient points. Available: {available_points}, Required: {points_amount}',
                    'available': available_points
                }

            if points_amount <= 0:
                return {
                    'valid': False,
                    'message': 'Points amount must be greater than zero',
                    'available': available_points
                }

            return {
                'valid': True,
                'message': 'Redemption valid',
                'available': available_points
            }

        except Exception as e:
            current_app.logger.error(f"Error in validate_redemption: {str(e)}")
            return {
                'valid': False,
                'message': f'Validation error: {str(e)}',
                'available': 0
            }

    @staticmethod
    def redeem_points(
        patient_id: str,
        points_amount: int,
        invoice_id: str,
        invoice_number: str = None,
        user_id: str = None
    ) -> str:
        """
        Redeem points for invoice payment (FIFO)
        - Deducts points from oldest batches first
        - Creates wallet transaction
        - Updates wallet balance

        Args:
            patient_id: UUID of patient
            points_amount: Points to redeem
            invoice_id: UUID of invoice
            invoice_number: Invoice number for reference
            user_id: User performing redemption

        Returns:
            transaction_id (str)
        """
        try:
            with get_db_session() as session:
                # Get wallet
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.is_active == True
                ).first()

                if not wallet:
                    raise WalletError(f"No active wallet found for patient {patient_id}")

                # Validate redemption
                validation = WalletService.validate_redemption(
                    patient_id=patient_id,
                    points_amount=points_amount,
                    hospital_id=str(wallet.hospital_id)
                )

                if not validation['valid']:
                    raise InsufficientPointsError(validation['message'])

                # Get active batches in FIFO order
                active_batches = session.query(WalletPointsBatch).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id,
                    WalletPointsBatch.is_expired == False,
                    WalletPointsBatch.points_remaining > 0
                ).order_by(WalletPointsBatch.batch_sequence.asc()).all()

                # Redeem points from batches (FIFO)
                points_to_redeem = points_amount
                for batch in active_batches:
                    if points_to_redeem == 0:
                        break

                    points_from_batch = min(batch.points_remaining, points_to_redeem)
                    batch.points_remaining -= points_from_batch
                    batch.points_redeemed += points_from_batch
                    points_to_redeem -= points_from_batch

                # Create transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='redeem',
                    transaction_date=datetime.now(timezone.utc),
                    points_redeemed=points_amount,
                    redemption_value=Decimal(str(points_amount)),  # 1:1 ratio
                    invoice_id=UUID(invoice_id),
                    invoice_number=invoice_number,
                    balance_before=wallet.points_balance,
                    balance_after=wallet.points_balance - points_amount,
                    created_by=user_id,
                    notes=f"Points redeemed for invoice {invoice_number}"
                )
                session.add(transaction)
                session.flush()

                # Update wallet
                wallet.points_balance -= points_amount
                wallet.points_value -= Decimal(str(points_amount))
                wallet.total_points_redeemed += points_amount
                wallet.updated_by = user_id

                session.commit()

                # TODO: Call GL service to create redemption GL entries
                # gl_service.create_wallet_redemption_gl_entries(...)

                return str(transaction.transaction_id)

        except (WalletError, InsufficientPointsError):
            raise
        except Exception as e:
            current_app.logger.error(f"Error in redeem_points: {str(e)}")
            raise WalletError(f"Failed to redeem points: {str(e)}")

    @staticmethod
    def refund_service(
        invoice_id: str,
        points_amount: int,
        refund_reason: str,
        user_id: str = None
    ) -> Dict:
        """
        Refund points for canceled service
        - Credits points back to wallet
        - Creates new batch with 12-month expiry from refund date
        - Creates wallet transaction (type: refund_service)

        Args:
            invoice_id: UUID of canceled invoice
            points_amount: Points to credit back
            refund_reason: Reason for refund
            user_id: User performing refund

        Returns:
            Dict with refund details
        """
        try:
            with get_db_session() as session:
                # Find original redemption transaction
                original_txn = session.query(WalletTransaction).filter(
                    WalletTransaction.invoice_id == UUID(invoice_id),
                    WalletTransaction.transaction_type == 'redeem'
                ).first()

                if not original_txn:
                    raise WalletError(f"No redemption transaction found for invoice {invoice_id}")

                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.wallet_id == original_txn.wallet_id
                ).first()

                # Calculate new expiry (12 months from refund date)
                load_date = date.today()
                expiry_date = load_date + timedelta(days=365)

                # Get next batch sequence
                max_sequence = session.query(func.max(WalletPointsBatch.batch_sequence)).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id
                ).scalar() or 0

                # Create refund transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='refund_service',
                    transaction_date=datetime.now(timezone.utc),
                    points_credited_back=points_amount,
                    refund_reason=refund_reason,
                    original_transaction_id=original_txn.transaction_id,
                    invoice_id=UUID(invoice_id),
                    balance_before=wallet.points_balance,
                    balance_after=wallet.points_balance + points_amount,
                    created_by=user_id,
                    notes=f"Service refund: {refund_reason}"
                )
                session.add(transaction)
                session.flush()

                # Create new batch with new expiry
                batch = WalletPointsBatch(
                    wallet_id=wallet.wallet_id,
                    load_transaction_id=transaction.transaction_id,
                    points_loaded=points_amount,
                    points_remaining=points_amount,
                    load_date=load_date,
                    expiry_date=expiry_date,
                    batch_sequence=max_sequence + 1
                )
                session.add(batch)

                # Update wallet
                wallet.points_balance += points_amount
                wallet.points_value += Decimal(str(points_amount))
                wallet.total_points_redeemed -= points_amount  # Reverse redemption
                wallet.updated_by = user_id

                session.commit()

                # TODO: Call GL service to create service refund GL entries
                # gl_service.create_wallet_refund_service_gl_entries(...)

                return {
                    'success': True,
                    'transaction_id': str(transaction.transaction_id),
                    'points_refunded': points_amount,
                    'new_balance': wallet.points_balance,
                    'new_expiry_date': expiry_date.isoformat(),
                    'batch_id': str(batch.batch_id)
                }

        except WalletError:
            raise
        except Exception as e:
            current_app.logger.error(f"Error in refund_service: {str(e)}")
            raise WalletError(f"Failed to refund service: {str(e)}")

    @staticmethod
    def close_wallet(
        patient_id: str,
        hospital_id: str,
        reason: str,
        user_id: str = None
    ) -> Dict:
        """
        Close wallet and calculate cash refund
        - Calculate: amount_loaded - points_consumed
        - Forfeit bonus points
        - Create refund transaction
        - Mark wallet as closed

        Formula: refund_amount = total_amount_loaded - (total_points_redeemed)

        Args:
            patient_id: UUID of patient
            hospital_id: UUID of hospital
            reason: Closure reason
            user_id: User closing wallet

        Returns:
            Dict with closure details and refund amount
        """
        try:
            with get_db_session() as session:
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.hospital_id == UUID(hospital_id),
                    PatientLoyaltyWallet.is_active == True
                ).first()

                if not wallet:
                    raise WalletError(f"No active wallet found for patient {patient_id}")

                # Calculate refund
                # Refund = cash loaded - points consumed (in cash terms)
                # Bonus points are forfeited
                total_cash_loaded = float(wallet.total_amount_loaded)
                points_consumed = wallet.total_points_redeemed

                # Cash refund cannot be negative
                cash_refund = max(0, total_cash_loaded - points_consumed)

                # Calculate forfeited points (remaining balance)
                points_forfeited = wallet.points_balance

                # Create closure transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='refund_wallet',
                    transaction_date=datetime.now(timezone.utc),
                    wallet_closure_amount=Decimal(str(cash_refund)),
                    points_forfeited=points_forfeited,
                    balance_before=wallet.points_balance,
                    balance_after=0,
                    created_by=user_id,
                    notes=f"Wallet closure: {reason}"
                )
                session.add(transaction)

                # Mark all batches as expired
                active_batches = session.query(WalletPointsBatch).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id,
                    WalletPointsBatch.is_expired == False
                ).all()

                for batch in active_batches:
                    batch.points_expired = batch.points_remaining
                    batch.points_remaining = 0
                    batch.is_expired = True
                    batch.expired_at = datetime.now(timezone.utc)

                # Close wallet
                wallet.wallet_status = 'closed'
                wallet.is_active = False
                wallet.points_balance = 0
                wallet.points_value = Decimal('0')
                wallet.closed_at = datetime.now(timezone.utc)
                wallet.closed_by = user_id

                session.commit()

                # TODO: Call GL service to create wallet closure GL entries
                # gl_service.create_wallet_closure_gl_entries(...)

                return {
                    'success': True,
                    'transaction_id': str(transaction.transaction_id),
                    'cash_refund': cash_refund,
                    'points_forfeited': points_forfeited,
                    'total_loaded': total_cash_loaded,
                    'total_consumed': points_consumed,
                    'wallet_status': 'closed'
                }

        except WalletError:
            raise
        except Exception as e:
            current_app.logger.error(f"Error in close_wallet: {str(e)}")
            raise WalletError(f"Failed to close wallet: {str(e)}")

    @staticmethod
    def get_tier_discount(patient_id: str, hospital_id: str) -> Decimal:
        """
        Get current tier discount percentage
        - Check tier validity
        - Return discount_percent or 0

        Args:
            patient_id: UUID of patient
            hospital_id: UUID of hospital

        Returns:
            Decimal: Discount percentage (e.g., 2.00 for 2%)
        """
        try:
            balance_info = WalletService.get_available_balance(patient_id, hospital_id)

            if not balance_info.get('has_wallet'):
                return Decimal('0')

            tier_discount = balance_info.get('tier_discount_percent', 0)
            return Decimal(str(tier_discount))

        except Exception as e:
            current_app.logger.error(f"Error in get_tier_discount: {str(e)}")
            return Decimal('0')

    @staticmethod
    def expire_points_batch(batch_id: str, user_id: str = 'SYSTEM') -> Dict:
        """
        Expire a points batch (called by background job)
        - Mark batch as expired
        - Deduct from wallet balance
        - Create expire transaction

        Args:
            batch_id: UUID of batch to expire
            user_id: User/system expiring batch

        Returns:
            Dict with expiry details
        """
        try:
            with get_db_session() as session:
                batch = session.query(WalletPointsBatch).filter(
                    WalletPointsBatch.batch_id == UUID(batch_id)
                ).first()

                if not batch:
                    raise WalletError(f"Batch {batch_id} not found")

                if batch.is_expired:
                    return {
                        'success': False,
                        'message': 'Batch already expired',
                        'points_expired': 0
                    }

                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.wallet_id == batch.wallet_id
                ).first()

                points_to_expire = batch.points_remaining

                # Create expiry transaction
                transaction = WalletTransaction(
                    wallet_id=wallet.wallet_id,
                    transaction_type='expire',
                    transaction_date=datetime.now(timezone.utc),
                    points_redeemed=points_to_expire,  # Use redeemed field for expiry
                    balance_before=wallet.points_balance,
                    balance_after=wallet.points_balance - points_to_expire,
                    created_by=user_id,
                    notes=f"Points expired from batch {batch_id}"
                )
                session.add(transaction)

                # Update batch
                batch.points_expired = points_to_expire
                batch.points_remaining = 0
                batch.is_expired = True
                batch.expired_at = datetime.now(timezone.utc)

                # Update wallet
                wallet.points_balance -= points_to_expire
                wallet.points_value -= Decimal(str(points_to_expire))
                wallet.updated_by = user_id

                session.commit()

                # TODO: Call GL service to create expiry GL entries
                # gl_service.create_wallet_expiry_gl_entries(...)

                return {
                    'success': True,
                    'transaction_id': str(transaction.transaction_id),
                    'points_expired': points_to_expire,
                    'batch_id': str(batch.batch_id),
                    'new_wallet_balance': wallet.points_balance
                }

        except WalletError:
            raise
        except Exception as e:
            current_app.logger.error(f"Error in expire_points_batch: {str(e)}")
            raise WalletError(f"Failed to expire batch: {str(e)}")

    @staticmethod
    def get_wallet_summary(patient_id: str, hospital_id: str) -> Dict:
        """
        Get comprehensive wallet summary for patient

        Returns:
            Dict with complete wallet information including:
            - Current balance
            - Tier information
            - Recent transactions
            - Expiring batches
            - Lifetime statistics
        """
        try:
            with get_db_session(read_only=True) as session:
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == UUID(patient_id),
                    PatientLoyaltyWallet.hospital_id == UUID(hospital_id)
                ).first()

                if not wallet:
                    return {'has_wallet': False}

                # Get tier info
                tier_info = {}
                if wallet.card_type_id:
                    card_type = session.query(LoyaltyCardType).filter(
                        LoyaltyCardType.card_type_id == wallet.card_type_id
                    ).first()
                    if card_type:
                        tier_info = {
                            'tier_name': card_type.card_type_name,
                            'tier_code': card_type.card_type_code,
                            'tier_discount_percent': float(card_type.discount_percent),
                            'tier_color': card_type.card_color
                        }

                # Get recent transactions (last 10)
                recent_txns = session.query(WalletTransaction).filter(
                    WalletTransaction.wallet_id == wallet.wallet_id
                ).order_by(WalletTransaction.transaction_date.desc()).limit(10).all()

                transactions = [
                    {
                        'transaction_id': str(txn.transaction_id),
                        'type': txn.transaction_type,
                        'date': txn.transaction_date.isoformat(),
                        'points': txn.total_points_loaded or txn.points_redeemed or 0,
                        'balance_after': txn.balance_after
                    }
                    for txn in recent_txns
                ]

                # Get expiring batches (next 30 days)
                expiring_soon = session.query(WalletPointsBatch).filter(
                    WalletPointsBatch.wallet_id == wallet.wallet_id,
                    WalletPointsBatch.is_expired == False,
                    WalletPointsBatch.points_remaining > 0,
                    WalletPointsBatch.expiry_date <= date.today() + timedelta(days=30)
                ).all()

                expiring_batches = [
                    {
                        'batch_id': str(batch.batch_id),
                        'points': batch.points_remaining,
                        'expiry_date': batch.expiry_date.isoformat()
                    }
                    for batch in expiring_soon
                ]

                return {
                    'has_wallet': True,
                    'wallet_id': str(wallet.wallet_id),
                    'wallet_status': wallet.wallet_status,
                    'is_active': wallet.is_active,
                    'points_balance': wallet.points_balance,
                    'points_value': float(wallet.points_value),
                    'total_amount_loaded': float(wallet.total_amount_loaded),
                    'total_points_loaded': wallet.total_points_loaded,
                    'total_points_redeemed': wallet.total_points_redeemed,
                    'total_bonus_points': wallet.total_bonus_points,
                    **tier_info,
                    'recent_transactions': transactions,
                    'expiring_batches': expiring_batches,
                    'points_expiring_soon': sum(b['points'] for b in expiring_batches)
                }

        except Exception as e:
            current_app.logger.error(f"Error in get_wallet_summary: {str(e)}")
            raise WalletError(f"Failed to get wallet summary: {str(e)}")
