"""
Wallet GL Service - General Ledger posting for wallet transactions
Handles GL entries for: Load, Redeem, Refund, Expire, Close
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
import uuid
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.transaction import (
    GLTransaction, GLEntry, WalletTransaction, PatientLoyaltyWallet,
    ARSubledger, InvoiceHeader
)
from app.models.master import ChartOfAccounts, Patient
from app.services.database_service import get_db_session

logger = logging.getLogger(__name__)


class WalletGLService:
    """Service for creating GL entries for wallet transactions"""

    @staticmethod
    def get_wallet_gl_accounts(session: Session, hospital_id: uuid.UUID) -> Dict[str, uuid.UUID]:
        """
        Get GL account IDs for wallet transactions

        Returns dict with:
        - wallet_liability: Customer Loyalty Wallet (2350) - Liability
        - cash: Cash/Bank account - Asset
        - revenue: Service Revenue (4100) - Income
        """
        accounts = {}

        # Get Customer Loyalty Wallet account (Liability)
        wallet_account = session.query(ChartOfAccounts).filter(
            and_(
                ChartOfAccounts.hospital_id == hospital_id,
                ChartOfAccounts.gl_account_no == '2350',
                ChartOfAccounts.is_active == True
            )
        ).first()

        if not wallet_account:
            raise ValueError(f"Wallet GL account (2350) not found for hospital {hospital_id}")

        accounts['wallet_liability'] = wallet_account.account_id

        # Get Cash account (Asset) - typically 1050
        cash_account = session.query(ChartOfAccounts).filter(
            and_(
                ChartOfAccounts.hospital_id == hospital_id,
                ChartOfAccounts.gl_account_no == '1050',
                ChartOfAccounts.is_active == True
            )
        ).first()

        if not cash_account:
            # Fallback to any cash account
            cash_account = session.query(ChartOfAccounts).filter(
                and_(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_name.ilike('%cash%'),
                    ChartOfAccounts.is_active == True
                )
            ).first()

        if cash_account:
            accounts['cash'] = cash_account.account_id

        # Get Service Revenue account (Income) - 4100
        revenue_account = session.query(ChartOfAccounts).filter(
            and_(
                ChartOfAccounts.hospital_id == hospital_id,
                ChartOfAccounts.gl_account_no == '4100',
                ChartOfAccounts.is_active == True
            )
        ).first()

        if revenue_account:
            accounts['revenue'] = revenue_account.account_id

        return accounts

    @staticmethod
    def create_wallet_load_gl_entries(
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict:
        """
        Create GL entries for wallet point loading

        Accounting Entry:
        DR Cash/Bank           Rs.X
            CR Wallet Liability     Rs.X

        (Customer pays cash, we owe them points - liability increases)
        """
        if session is not None:
            return WalletGLService._create_wallet_load_gl_entries_internal(
                session, wallet_transaction_id, current_user_id
            )

        with get_db_session() as new_session:
            return WalletGLService._create_wallet_load_gl_entries_internal(
                new_session, wallet_transaction_id, current_user_id
            )

    @staticmethod
    def _create_wallet_load_gl_entries_internal(
        session: Session,
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None
    ) -> Dict:
        """Internal method to create wallet load GL entries"""
        try:
            # Get wallet transaction
            wallet_txn = session.query(WalletTransaction).filter_by(
                transaction_id=wallet_transaction_id
            ).first()

            if not wallet_txn:
                raise ValueError(f"Wallet transaction {wallet_transaction_id} not found")

            if wallet_txn.transaction_type != 'load':
                raise ValueError(f"Transaction is not a load type: {wallet_txn.transaction_type}")

            # Get wallet to find hospital_id
            wallet = session.query(PatientLoyaltyWallet).filter_by(
                wallet_id=wallet_txn.wallet_id
            ).first()

            if not wallet:
                raise ValueError(f"Wallet {wallet_txn.wallet_id} not found")

            # Get GL accounts
            accounts = WalletGLService.get_wallet_gl_accounts(session, wallet.hospital_id)

            if 'cash' not in accounts:
                logger.warning(f"No cash account found for hospital {wallet.hospital_id}")
                return {'success': False, 'message': 'Cash account not configured'}

            amount = wallet_txn.amount_paid or Decimal('0')

            if amount == 0:
                logger.warning(f"Wallet load transaction {wallet_transaction_id} has zero amount")
                return {'success': False, 'message': 'Zero amount transaction'}

            # Create GL Transaction
            gl_transaction = GLTransaction(
                hospital_id=wallet.hospital_id,
                transaction_date=wallet_txn.transaction_date,
                transaction_type="WALLET_LOAD",
                reference_id=str(wallet_transaction_id),
                description=f"Wallet load - {wallet_txn.total_points_loaded} points",
                currency_code='INR',
                exchange_rate=Decimal('1.0'),
                total_debit=amount,
                total_credit=amount,
                created_by=current_user_id
            )

            session.add(gl_transaction)
            session.flush()

            # Entry 1: DR Cash
            cash_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['cash'],
                debit_amount=amount,
                credit_amount=Decimal('0'),
                entry_date=wallet_txn.transaction_date,
                description=f"Wallet load payment received",
                created_by=current_user_id
            )
            session.add(cash_entry)

            # Entry 2: CR Wallet Liability
            wallet_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['wallet_liability'],
                debit_amount=Decimal('0'),
                credit_amount=amount,
                entry_date=wallet_txn.transaction_date,
                description=f"Wallet liability - {wallet_txn.total_points_loaded} points loaded",
                created_by=current_user_id
            )
            session.add(wallet_entry)

            # Update wallet transaction with GL reference
            wallet_txn.journal_entry_id = gl_transaction.transaction_id

            session.commit()

            logger.info(f"Created GL entries for wallet load {wallet_transaction_id}")

            return {
                'success': True,
                'gl_transaction_id': gl_transaction.transaction_id,
                'amount': amount,
                'message': 'GL entries created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating wallet load GL entries: {str(e)}")
            session.rollback()
            raise

    @staticmethod
    def create_wallet_redemption_gl_entries(
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict:
        """
        Create GL entries for wallet point redemption

        Accounting Entry:
        DR Wallet Liability    Rs.X
            CR Revenue              Rs.X

        (Customer redeems points, we reduce liability and recognize revenue)
        """
        if session is not None:
            return WalletGLService._create_wallet_redemption_gl_entries_internal(
                session, wallet_transaction_id, current_user_id
            )

        with get_db_session() as new_session:
            return WalletGLService._create_wallet_redemption_gl_entries_internal(
                new_session, wallet_transaction_id, current_user_id
            )

    @staticmethod
    def _create_wallet_redemption_gl_entries_internal(
        session: Session,
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None
    ) -> Dict:
        """Internal method to create wallet redemption GL entries"""
        try:
            # Get wallet transaction
            wallet_txn = session.query(WalletTransaction).filter_by(
                transaction_id=wallet_transaction_id
            ).first()

            if not wallet_txn:
                raise ValueError(f"Wallet transaction {wallet_transaction_id} not found")

            if wallet_txn.transaction_type != 'redeem':
                raise ValueError(f"Transaction is not a redeem type: {wallet_txn.transaction_type}")

            # Get wallet
            wallet = session.query(PatientLoyaltyWallet).filter_by(
                wallet_id=wallet_txn.wallet_id
            ).first()

            if not wallet:
                raise ValueError(f"Wallet {wallet_txn.wallet_id} not found")

            # Get GL accounts
            accounts = WalletGLService.get_wallet_gl_accounts(session, wallet.hospital_id)

            if 'revenue' not in accounts:
                logger.warning(f"No revenue account found for hospital {wallet.hospital_id}")
                return {'success': False, 'message': 'Revenue account not configured'}

            amount = wallet_txn.redemption_value or Decimal('0')

            if amount == 0:
                logger.warning(f"Wallet redemption {wallet_transaction_id} has zero value")
                return {'success': False, 'message': 'Zero amount redemption'}

            # Create GL Transaction
            gl_transaction = GLTransaction(
                hospital_id=wallet.hospital_id,
                transaction_date=wallet_txn.transaction_date,
                transaction_type="WALLET_REDEEM",
                reference_id=str(wallet_transaction_id),
                description=f"Wallet redemption - {wallet_txn.points_redeemed} points",
                currency_code='INR',
                exchange_rate=Decimal('1.0'),
                total_debit=amount,
                total_credit=amount,
                created_by=current_user_id
            )

            session.add(gl_transaction)
            session.flush()

            # Entry 1: DR Wallet Liability
            wallet_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['wallet_liability'],
                debit_amount=amount,
                credit_amount=Decimal('0'),
                entry_date=wallet_txn.transaction_date,
                description=f"Wallet liability reduced - {wallet_txn.points_redeemed} points redeemed",
                created_by=current_user_id
            )
            session.add(wallet_entry)

            # Entry 2: CR Revenue
            revenue_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['revenue'],
                debit_amount=Decimal('0'),
                credit_amount=amount,
                entry_date=wallet_txn.transaction_date,
                description=f"Revenue recognized from wallet redemption",
                created_by=current_user_id
            )
            session.add(revenue_entry)

            # Update wallet transaction with GL reference
            wallet_txn.journal_entry_id = gl_transaction.transaction_id

            # Update AR Subledger if this redemption is linked to an invoice
            if wallet_txn.invoice_id:
                WalletGLService._update_ar_for_wallet_payment(
                    session, wallet_txn.invoice_id, amount, wallet_txn.transaction_date, current_user_id
                )

            session.commit()

            logger.info(f"Created GL entries for wallet redemption {wallet_transaction_id}")

            return {
                'success': True,
                'gl_transaction_id': gl_transaction.transaction_id,
                'amount': amount,
                'message': 'GL entries created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating wallet redemption GL entries: {str(e)}")
            session.rollback()
            raise

    @staticmethod
    def _update_ar_for_wallet_payment(
        session: Session,
        invoice_id: uuid.UUID,
        payment_amount: Decimal,
        payment_date: datetime,
        current_user_id: Optional[str] = None
    ):
        """
        Update AR Subledger when wallet points are used for payment

        Creates a PAYMENT entry in AR subledger to reduce outstanding balance
        """
        try:
            # Get invoice
            invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()

            if not invoice:
                logger.warning(f"Invoice {invoice_id} not found for AR update")
                return

            # Get wallet
            wallet_txn = session.query(WalletTransaction).filter_by(invoice_id=invoice_id).first()
            if wallet_txn:
                wallet = session.query(PatientLoyaltyWallet).filter_by(
                    wallet_id=wallet_txn.wallet_id
                ).first()

                if wallet:
                    # Create AR Subledger entry for wallet payment
                    ar_entry = ARSubledger(
                        hospital_id=invoice.hospital_id,
                        patient_id=wallet.patient_id,
                        invoice_id=invoice_id,
                        transaction_type='PAYMENT',
                        transaction_date=payment_date,
                        debit_amount=Decimal('0'),
                        credit_amount=payment_amount,
                        balance=Decimal('0'),  # Will be calculated by trigger/service
                        payment_mode='WALLET',
                        reference_number=f"WALLET-{str(wallet_txn.transaction_id)[:8]}",
                        notes=f"Wallet point redemption - {wallet_txn.points_redeemed} points",
                        created_by=current_user_id
                    )

                    session.add(ar_entry)
                    logger.info(f"Created AR subledger entry for wallet payment on invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Error updating AR for wallet payment: {str(e)}")
            # Don't raise - this is supplementary tracking
            pass

    @staticmethod
    def create_wallet_refund_gl_entries(
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict:
        """
        Create GL entries for wallet refund (service refund or wallet closure)

        For service refund (points credited back):
        DR Revenue             Rs.X
            CR Wallet Liability     Rs.X

        For wallet closure (cash refund):
        DR Wallet Liability    Rs.X
            CR Cash                 Rs.X
        """
        if session is not None:
            return WalletGLService._create_wallet_refund_gl_entries_internal(
                session, wallet_transaction_id, current_user_id
            )

        with get_db_session() as new_session:
            return WalletGLService._create_wallet_refund_gl_entries_internal(
                new_session, wallet_transaction_id, current_user_id
            )

    @staticmethod
    def _create_wallet_refund_gl_entries_internal(
        session: Session,
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None
    ) -> Dict:
        """Internal method to create wallet refund GL entries"""
        try:
            # Get wallet transaction
            wallet_txn = session.query(WalletTransaction).filter_by(
                transaction_id=wallet_transaction_id
            ).first()

            if not wallet_txn:
                raise ValueError(f"Wallet transaction {wallet_transaction_id} not found")

            if wallet_txn.transaction_type not in ['refund_service', 'refund_wallet']:
                raise ValueError(f"Transaction is not a refund type: {wallet_txn.transaction_type}")

            # Get wallet
            wallet = session.query(PatientLoyaltyWallet).filter_by(
                wallet_id=wallet_txn.wallet_id
            ).first()

            if not wallet:
                raise ValueError(f"Wallet {wallet_txn.wallet_id} not found")

            # Get GL accounts
            accounts = WalletGLService.get_wallet_gl_accounts(session, wallet.hospital_id)

            if wallet_txn.transaction_type == 'refund_service':
                # Service refund - points credited back
                if 'revenue' not in accounts:
                    return {'success': False, 'message': 'Revenue account not configured'}

                amount = wallet_txn.redemption_value or Decimal('0')
                txn_type = "WALLET_REFUND_SERVICE"
                dr_account = accounts['revenue']
                dr_desc = "Revenue reversed - service refund"
                cr_desc = f"Wallet liability increased - {wallet_txn.points_credited_back} points credited"

            else:  # refund_wallet
                # Wallet closure - cash refund
                if 'cash' not in accounts:
                    return {'success': False, 'message': 'Cash account not configured'}

                amount = wallet_txn.wallet_closure_amount or Decimal('0')
                txn_type = "WALLET_CLOSURE"
                dr_account = accounts['wallet_liability']
                dr_desc = f"Wallet liability cleared - wallet closed"
                cr_desc = f"Cash refund - {wallet_txn.points_forfeited} points forfeited"
                # Swap accounts for wallet closure
                cr_account = accounts['cash']

            if amount == 0:
                logger.warning(f"Wallet refund {wallet_transaction_id} has zero value")
                return {'success': False, 'message': 'Zero amount refund'}

            # Create GL Transaction
            gl_transaction = GLTransaction(
                hospital_id=wallet.hospital_id,
                transaction_date=wallet_txn.transaction_date,
                transaction_type=txn_type,
                reference_id=str(wallet_transaction_id),
                description=f"Wallet {wallet_txn.transaction_type}",
                currency_code='INR',
                exchange_rate=Decimal('1.0'),
                total_debit=amount,
                total_credit=amount,
                created_by=current_user_id
            )

            session.add(gl_transaction)
            session.flush()

            if wallet_txn.transaction_type == 'refund_service':
                # Entry 1: DR Revenue
                debit_entry = GLEntry(
                    hospital_id=wallet.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=dr_account,
                    debit_amount=amount,
                    credit_amount=Decimal('0'),
                    entry_date=wallet_txn.transaction_date,
                    description=dr_desc,
                    created_by=current_user_id
                )
                session.add(debit_entry)

                # Entry 2: CR Wallet Liability
                credit_entry = GLEntry(
                    hospital_id=wallet.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=accounts['wallet_liability'],
                    debit_amount=Decimal('0'),
                    credit_amount=amount,
                    entry_date=wallet_txn.transaction_date,
                    description=cr_desc,
                    created_by=current_user_id
                )
                session.add(credit_entry)

            else:  # wallet closure
                # Entry 1: DR Wallet Liability
                debit_entry = GLEntry(
                    hospital_id=wallet.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=dr_account,
                    debit_amount=amount,
                    credit_amount=Decimal('0'),
                    entry_date=wallet_txn.transaction_date,
                    description=dr_desc,
                    created_by=current_user_id
                )
                session.add(debit_entry)

                # Entry 2: CR Cash
                credit_entry = GLEntry(
                    hospital_id=wallet.hospital_id,
                    transaction_id=gl_transaction.transaction_id,
                    account_id=cr_account,
                    debit_amount=Decimal('0'),
                    credit_amount=amount,
                    entry_date=wallet_txn.transaction_date,
                    description=cr_desc,
                    created_by=current_user_id
                )
                session.add(credit_entry)

            # Update wallet transaction with GL reference
            wallet_txn.journal_entry_id = gl_transaction.transaction_id

            session.commit()

            logger.info(f"Created GL entries for wallet refund {wallet_transaction_id}")

            return {
                'success': True,
                'gl_transaction_id': gl_transaction.transaction_id,
                'amount': amount,
                'message': 'GL entries created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating wallet refund GL entries: {str(e)}")
            session.rollback()
            raise

    @staticmethod
    def create_wallet_expiry_gl_entries(
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict:
        """
        Create GL entries for wallet point expiry

        Accounting Entry:
        DR Wallet Liability    Rs.X
            CR Other Income/Revenue Rs.X

        (Points expired, liability reduced, recognized as income)
        """
        if session is not None:
            return WalletGLService._create_wallet_expiry_gl_entries_internal(
                session, wallet_transaction_id, current_user_id
            )

        with get_db_session() as new_session:
            return WalletGLService._create_wallet_expiry_gl_entries_internal(
                new_session, wallet_transaction_id, current_user_id
            )

    @staticmethod
    def _create_wallet_expiry_gl_entries_internal(
        session: Session,
        wallet_transaction_id: uuid.UUID,
        current_user_id: Optional[str] = None
    ) -> Dict:
        """Internal method to create wallet expiry GL entries"""
        try:
            # Get wallet transaction
            wallet_txn = session.query(WalletTransaction).filter_by(
                transaction_id=wallet_transaction_id
            ).first()

            if not wallet_txn:
                raise ValueError(f"Wallet transaction {wallet_transaction_id} not found")

            if wallet_txn.transaction_type != 'expire':
                raise ValueError(f"Transaction is not an expire type: {wallet_txn.transaction_type}")

            # Get wallet
            wallet = session.query(PatientLoyaltyWallet).filter_by(
                wallet_id=wallet_txn.wallet_id
            ).first()

            if not wallet:
                raise ValueError(f"Wallet {wallet_txn.wallet_id} not found")

            # Get GL accounts
            accounts = WalletGLService.get_wallet_gl_accounts(session, wallet.hospital_id)

            if 'revenue' not in accounts:
                logger.warning(f"No revenue account found for hospital {wallet.hospital_id}")
                return {'success': False, 'message': 'Revenue account not configured'}

            # Calculate value of expired points (assuming 1:1 ratio)
            amount = Decimal(str(wallet_txn.points_redeemed or 0))  # Points expired stored in points_redeemed

            if amount == 0:
                logger.warning(f"Wallet expiry {wallet_transaction_id} has zero expired points")
                return {'success': False, 'message': 'Zero points expired'}

            # Create GL Transaction
            gl_transaction = GLTransaction(
                hospital_id=wallet.hospital_id,
                transaction_date=wallet_txn.transaction_date,
                transaction_type="WALLET_EXPIRY",
                reference_id=str(wallet_transaction_id),
                description=f"Wallet point expiry - {amount} points",
                currency_code='INR',
                exchange_rate=Decimal('1.0'),
                total_debit=amount,
                total_credit=amount,
                created_by=current_user_id
            )

            session.add(gl_transaction)
            session.flush()

            # Entry 1: DR Wallet Liability
            wallet_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['wallet_liability'],
                debit_amount=amount,
                credit_amount=Decimal('0'),
                entry_date=wallet_txn.transaction_date,
                description=f"Wallet liability reduced - {amount} points expired",
                created_by=current_user_id
            )
            session.add(wallet_entry)

            # Entry 2: CR Revenue (Other Income)
            revenue_entry = GLEntry(
                hospital_id=wallet.hospital_id,
                transaction_id=gl_transaction.transaction_id,
                account_id=accounts['revenue'],
                debit_amount=Decimal('0'),
                credit_amount=amount,
                entry_date=wallet_txn.transaction_date,
                description=f"Income recognized from expired points",
                created_by=current_user_id
            )
            session.add(revenue_entry)

            # Update wallet transaction with GL reference
            wallet_txn.journal_entry_id = gl_transaction.transaction_id

            session.commit()

            logger.info(f"Created GL entries for wallet expiry {wallet_transaction_id}")

            return {
                'success': True,
                'gl_transaction_id': gl_transaction.transaction_id,
                'amount': amount,
                'message': 'GL entries created successfully'
            }

        except Exception as e:
            logger.error(f"Error creating wallet expiry GL entries: {str(e)}")
            session.rollback()
            raise
