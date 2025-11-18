"""
Package Payment Service
Service layer for package payment plans with installment schedules

Handles:
- Payment plan creation with auto-generated installments
- Installment payment recording
- Session tracking and completion
- Plan status management

Version: 1.0
Created: 2025-01-11
"""

import logging
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from sqlalchemy import and_, or_, cast, String
from app.engine.universal_entity_service import UniversalEntityService
from app.models.transaction import PackagePaymentPlan, InstallmentPayment, PackageSession, InvoiceHeader, InvoiceLineItem
from app.models.views import PackagePaymentPlanView  # Import view model for search operations
from app.models.master import Package  # Import Package model
from app.services.database_service import get_db_session
from app.engine.universal_service_cache import invalidate_service_cache_for_entity
from app.services.patient_credit_note_service import PatientCreditNoteService

logger = logging.getLogger(__name__)


class PackagePaymentService(UniversalEntityService):
    """Service for managing package payment plans"""

    def __init__(self):
        """Initialize with view model for list/search operations"""
        # Use view model for list/search operations (includes joined patient, package, invoice data)
        super().__init__('package_payment_plans', PackagePaymentPlanView)

        logger.info("✅ Initialized PackagePaymentService with PackagePaymentPlanView")

    # ==========================================
    # CUSTOM SEARCH WITH FILTERS AND SUMMARY
    # ==========================================
    # Override default Universal Engine search to:
    # 1. Apply filters properly (patient_name, status, search)
    # 2. Return summary data (count, total_amount, balance_amount)
    # 3. Enrich results with patient and package information

    def search_data(self, filters: Dict, hospital_id: str, branch_id: Optional[str] = None,
                    page: int = 1, per_page: int = 20, **kwargs) -> Dict[str, Any]:
        """
        Override removed - using default Universal Engine search with PackagePaymentPlanView.

        The view includes joined data:
        - patient_name (from patients table)
        - package_name (from packages table)
        - balance_amount (computed field)
        """
        try:
            logger.info(f"[package_payment_plans] search_data: Querying VIEW for hospital_id={hospital_id}")

            with get_db_session() as session:
                from app.models.master import Patient
                from app.models.transaction import InvoiceHeader

                # Query the VIEW instead of base table to get computed balance_amount
                # First, do a raw count to see total records in view (no filters)
                raw_count = session.query(PackagePaymentPlanView).filter(
                    PackagePaymentPlanView.hospital_id == hospital_id
                ).count()
                logger.info(f"[DEBUG] Total records in view for hospital (no filters): {raw_count}")

                # Base query on VIEW (has balance_amount, patient_name, package_name)
                query = session.query(PackagePaymentPlanView).filter(
                    and_(
                        PackagePaymentPlanView.hospital_id == hospital_id,
                        PackagePaymentPlanView.is_deleted == False
                    )
                )

                # Count after is_deleted filter
                base_count = query.count()
                logger.info(f"[DEBUG] Records after is_deleted=False filter: {base_count}")

                # Apply branch filter if provided (include NULL branch_id records - hospital-level plans)
                if branch_id:
                    logger.info(f"[DEBUG] Applying branch_id filter: {branch_id}")
                    query = query.filter(
                        or_(
                            PackagePaymentPlanView.branch_id == branch_id,
                            PackagePaymentPlanView.branch_id == None  # Include hospital-level plans
                        )
                    )
                    logger.info(f"[DEBUG] Records after branch filter (includes NULL): {query.count()}")

                # Apply patient filter - check if patient_name is a UUID (from autocomplete) or text search
                patient_name = filters.get('patient_name')
                patient_id = filters.get('patient_id')  # Legacy support

                if patient_name:
                    # Try to parse as UUID first (autocomplete selection)
                    try:
                        patient_uuid = uuid.UUID(patient_name)
                        logger.info(f"[DEBUG] patient_name is UUID, filtering by patient_id: {patient_uuid}")
                        query = query.filter(PackagePaymentPlanView.patient_id == patient_uuid)
                        logger.info(f"[DEBUG] Records after patient_id filter: {query.count()}")
                    except ValueError:
                        # Not a UUID, treat as text search
                        logger.info(f"[DEBUG] Applying patient_name text filter: {patient_name}")
                        query = query.filter(PackagePaymentPlanView.patient_name.ilike(f'%{patient_name}%'))
                        logger.info(f"[DEBUG] Records after patient_name filter: {query.count()}")
                elif patient_id:
                    # Legacy support: direct patient_id filter
                    logger.info(f"[DEBUG] Applying patient_id filter (legacy): {patient_id}")
                    try:
                        if isinstance(patient_id, str):
                            patient_id = uuid.UUID(patient_id)
                        query = query.filter(PackagePaymentPlanView.patient_id == patient_id)
                        logger.info(f"[DEBUG] Records after patient_id filter: {query.count()}")
                    except ValueError:
                        logger.warning(f"[WARNING] Invalid patient_id UUID format: {patient_id}")

                # Apply package filter - check if package_name is a UUID (from autocomplete) or text search
                package_name = filters.get('package_name')
                package_id = filters.get('package_id')  # Legacy support

                if package_name:
                    # Try to parse as UUID first (autocomplete selection)
                    try:
                        package_uuid = uuid.UUID(package_name)
                        logger.info(f"[DEBUG] package_name is UUID, filtering by package_id: {package_uuid}")
                        query = query.filter(PackagePaymentPlanView.package_id == package_uuid)
                        logger.info(f"[DEBUG] Records after package_id filter: {query.count()}")
                    except ValueError:
                        # Not a UUID, treat as text search
                        logger.info(f"[DEBUG] Applying package_name text filter: {package_name}")
                        query = query.filter(PackagePaymentPlanView.package_name.ilike(f'%{package_name}%'))
                        logger.info(f"[DEBUG] Records after package_name filter: {query.count()}")
                elif package_id:
                    # Legacy support: direct package_id filter
                    logger.info(f"[DEBUG] Applying package_id filter (legacy): {package_id}")
                    try:
                        if isinstance(package_id, str):
                            package_id = uuid.UUID(package_id)
                        query = query.filter(PackagePaymentPlanView.package_id == package_id)
                        logger.info(f"[DEBUG] Records after package_id filter: {query.count()}")
                    except ValueError:
                        logger.warning(f"[WARNING] Invalid package_id UUID format: {package_id}")

                # Apply search filter if provided (general search)
                search_text = filters.get('search') or filters.get('q')
                if search_text:
                    logger.info(f"[DEBUG] Applying search filter: {search_text}")
                    query = query.filter(
                        or_(
                            PackagePaymentPlanView.patient_name.ilike(f'%{search_text}%'),
                            PackagePaymentPlanView.package_name.ilike(f'%{search_text}%'),
                            cast(PackagePaymentPlanView.plan_id, String).ilike(f'%{search_text}%')  # Cast UUID to text for ILIKE
                        )
                    )
                    logger.info(f"[DEBUG] Records after search filter: {query.count()}")

                # Apply status filter if provided
                if filters.get('status'):
                    logger.info(f"[DEBUG] Applying status filter: {filters.get('status')}")
                    query = query.filter(PackagePaymentPlanView.status == filters.get('status'))
                    logger.info(f"[DEBUG] Records after status filter: {query.count()}")

                # Count total before pagination
                total_count = query.count()
                logger.info(f"[DEBUG] FINAL total_count before pagination: {total_count}")

                # Apply sorting (default: newest first)
                sort_field = filters.get('sort', 'created_at')
                sort_direction = filters.get('direction', 'desc')

                if hasattr(PackagePaymentPlanView, sort_field):
                    sort_column = getattr(PackagePaymentPlanView, sort_field)
                    query = query.order_by(sort_column.desc() if sort_direction == 'desc' else sort_column.asc())
                else:
                    query = query.order_by(PackagePaymentPlanView.created_at.desc())

                # Apply pagination
                offset = (page - 1) * per_page
                plans = query.limit(per_page).offset(offset).all()

                logger.info(f"[package_payment_plans] Found {len(plans)} plans (total: {total_count})")

                # Convert to dictionaries - view already has patient_name, package_name, balance_amount
                from app.services.database_service import get_entity_dict
                items = []
                for plan in plans:
                    plan_dict = get_entity_dict(plan)
                    # View provides: patient_name, package_name, balance_amount automatically
                    # No manual enrichment needed!
                    items.append(plan_dict)

                # Calculate summary statistics matching the summary_cards configuration
                total_amount = sum(plan.total_amount or 0 for plan in plans)
                total_paid = sum(plan.paid_amount or 0 for plan in plans)
                total_balance = sum(plan.balance_amount or 0 for plan in plans)

                # Count by status
                status_counts = {}
                active_count = 0
                for plan in plans:
                    status = plan.status or 'unknown'
                    status_counts[status] = status_counts.get(status, 0) + 1
                    if status == 'active':
                        active_count += 1

                # Calculate pagination
                total_pages = (total_count + per_page - 1) // per_page
                has_prev = page > 1
                has_next = page < total_pages

                result = {
                    'items': items,
                    'total': total_count,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_count': total_count,
                        'total_pages': total_pages,
                        'has_prev': has_prev,
                        'has_next': has_next
                    },
                    'summary': {
                        # Match field names from PACKAGE_PAYMENT_PLAN_SUMMARY_CARDS
                        'count': total_count,                    # Total Plans card
                        'active_count': active_count,            # Active Plans card
                        'total_amount': float(total_amount),     # Total Revenue card
                        'balance_amount': float(total_balance),  # Outstanding Balance card
                        'status_counts': status_counts,
                        'total_paid': float(total_paid)
                    },
                    'applied_filters': list(filters.keys()),
                    'success': True
                }

                logger.info(f"[package_payment_plans] Returning {len(items)} items with summary: count={total_count}, active={active_count}, total_amount={total_amount}, balance={total_balance}")
                return result

        except Exception as e:
            logger.error(f"Error in search_data: {str(e)}", exc_info=True)
            return {
                'items': [],
                'total': 0,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False
                },
                'success': False,
                'error': str(e)
            }

    # ==========================================
    # OVERRIDE CREATE TO AUTO-GENERATE INSTALLMENTS AND SESSIONS
    # ==========================================

    def create(self, data: Dict, hospital_id: str, branch_id: Optional[str] = None, **context) -> Dict[str, Any]:
        """
        Override create to:
        1. Fetch package details and auto-populate fields
        2. Auto-generate installments and sessions

        Called by Universal Engine create form

        Args:
            data: Form data from Universal Engine
            hospital_id: Hospital ID
            branch_id: Branch ID (optional)
            **context: Additional context (created_by, etc.)

        Returns:
            {
                'success': bool,
                'data': dict,  # Created plan
                'message': str,
                'plan_id': str
            }
        """
        try:
            # Step 1: Fetch package details and enrich data
            package_id = data.get('package_id')
            if package_id:
                logger.info(f"Fetching package details for package_id: {package_id}")
                package_data = self._fetch_package_details(package_id, hospital_id)

                if not package_data:
                    return {
                        'success': False,
                        'error': f'Package not found: {package_id}',
                        'message': 'Selected package does not exist'
                    }

                # Auto-populate fields from package if not provided
                if 'total_amount' not in data or not data['total_amount']:
                    data['total_amount'] = package_data['price']
                    logger.info(f"Auto-populated total_amount: {package_data['price']}")

                # Store deprecated fields for backward compatibility
                data['package_name'] = package_data['package_name']
                data['package_description'] = package_data.get('description', '')
                data['package_code'] = package_data.get('package_code', '')

                logger.info(f"Package details populated: {package_data['package_name']}")
            else:
                # Backward compatibility: If no package_id, require manual entry
                if not data.get('package_name'):
                    return {
                        'success': False,
                        'error': 'Package selection is required',
                        'message': 'Please select a package from the master list'
                    }

            # Create the payment plan record in a single session with installments and sessions
            with get_db_session() as session:
                # Generate plan_id
                plan_id = str(uuid.uuid4())

                # Get created_by from context
                created_by = context.get('created_by', 'system')

                # Convert first_installment_date to date object if string
                first_installment_date = data.get('first_installment_date')
                if isinstance(first_installment_date, str):
                    first_installment_date = datetime.strptime(first_installment_date, '%Y-%m-%d').date()

                # Calculate allocated payment for this package from the invoice
                # Implements payment allocation rule: Services first, then packages
                invoice_paid_amount = Decimal('0.00')
                invoice_id = data.get('invoice_id')
                package_id = data.get('package_id')

                if invoice_id and package_id:
                    try:
                        invoice_paid_amount = self._calculate_package_allocated_payment(
                            session=session,
                            invoice_id=invoice_id,
                            package_id=package_id
                        )
                        logger.info(f"Package {package_id} allocated payment from invoice: ₹{invoice_paid_amount}")
                    except Exception as inv_err:
                        logger.warning(f"Could not calculate allocated payment: {inv_err}")

                # Create plan record
                plan = PackagePaymentPlan(
                    plan_id=plan_id,
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    patient_id=data.get('patient_id'),
                    invoice_id=invoice_id,
                    package_id=data.get('package_id'),
                    package_name=data.get('package_name'),
                    package_description=data.get('package_description', ''),
                    package_code=data.get('package_code', ''),
                    total_sessions=int(data.get('total_sessions', 1)),
                    total_amount=Decimal(str(data.get('total_amount', 0))),
                    paid_amount=invoice_paid_amount,  # Set directly in constructor
                    installment_count=int(data.get('installment_count', 1)),
                    installment_frequency=data.get('installment_frequency', 'monthly'),
                    first_installment_date=first_installment_date,
                    status='active',
                    notes=data.get('notes', ''),
                    is_deleted=False,  # Explicitly set to False to ensure query can find it
                    created_by=created_by,
                    updated_by=created_by,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )

                logger.info(f"Package payment plan created with paid_amount = ₹{invoice_paid_amount}")

                session.add(plan)
                logger.info(f"Package payment plan created: {plan_id}")

                # Generate sessions FIRST (so we can sync installments with session dates if needed)
                # Default: Use first_installment_date as first session date, same frequency as installments
                total_sessions = int(data.get('total_sessions', 1))
                first_session_date = data.get('first_session_date', first_installment_date)  # Can be overridden in form
                if isinstance(first_session_date, str):
                    first_session_date = datetime.strptime(first_session_date, '%Y-%m-%d').date()

                # Use same frequency as installments by default (user can override)
                session_frequency = data.get('session_frequency', 'monthly')  # Default monthly

                sessions_result = self._generate_sessions_in_session(
                    session=session,
                    plan_id=plan_id,
                    total_sessions=total_sessions,
                    hospital_id=hospital_id,
                    created_by=created_by,
                    first_session_date=first_session_date,
                    session_frequency=session_frequency
                )

                # Get generated session dates for potential sync with installments
                session_dates = []
                if sessions_result['success'] and 'session_objects' in sessions_result:
                    session_dates = [s.session_date for s in sessions_result['session_objects']]

                # Generate installments (optionally synced with session dates)
                total_amount = Decimal(str(data.get('total_amount', 0)))
                installment_count = int(data.get('installment_count', 1))
                installment_frequency = data.get('installment_frequency', 'monthly')
                sync_with_sessions = data.get('sync_with_sessions', 'true').lower() == 'true'  # Default: sync enabled

                installments_result = self._generate_installments_in_session(
                    session=session,
                    plan_id=plan_id,
                    total_amount=total_amount,
                    installment_count=installment_count,
                    frequency=installment_frequency,
                    first_date=first_installment_date,
                    hospital_id=hospital_id,
                    session_dates=session_dates if sync_with_sessions else None
                )

                # Commit all at once
                session.commit()

                # Build success result (inside session context to avoid DetachedInstanceError)
                result = {
                    'success': True,
                    'data': {'plan_id': plan_id},
                    'message': f"Payment plan created with {installment_count} installments and {total_sessions} sessions",
                    'plan_id': plan_id
                }

                if not installments_result['success']:
                    logger.error(f"Failed to generate installments: {installments_result.get('error')}")
                    result['message'] += f" Warning: {installments_result.get('error')}"

                if not sessions_result['success']:
                    logger.error(f"Failed to generate sessions: {sessions_result.get('error')}")
                    result['message'] += f" Warning: {sessions_result.get('error')}"

            # Invalidate cache (outside session context - cache operations are independent)
            invalidate_service_cache_for_entity('package_payment_plans', cascade=False)

            return result

        except Exception as e:
            logger.error(f"Error creating package payment plan: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to create payment plan: {str(e)}',
                'message': 'Error creating payment plan'
            }

    # ==========================================
    # INSTALLMENT GENERATION
    # ==========================================

    def _generate_installments_in_session(
        self,
        session,
        plan_id: str,
        total_amount: Decimal,
        installment_count: int,
        frequency: str,
        first_date: date,
        hospital_id: str,
        session_dates: list = None
    ) -> Dict[str, Any]:
        """
        Auto-generate installment records in existing session
        Called from create() to avoid nested transactions

        Args:
            session: Database session
            plan_id: Plan ID
            total_amount: Total amount to split across installments
            installment_count: Number of installments
            frequency: Frequency (weekly, biweekly, monthly, custom)
            first_date: First installment date
            hospital_id: Hospital ID
            session_dates: Optional list of session dates to sync with (default: None)
        """
        try:
            # Calculate amount per installment
            amount_per_installment = total_amount / Decimal(installment_count)
            amount_per_installment = amount_per_installment.quantize(Decimal('0.01'))

            # Handle rounding - add remainder to last installment
            total_allocated = amount_per_installment * (installment_count - 1)
            last_installment_amount = total_amount - total_allocated

            installments = []

            for i in range(installment_count):
                # Calculate due date - use session dates if provided and available
                if session_dates and i < len(session_dates):
                    # Sync with session dates: Distribute installments across sessions
                    # If fewer installments than sessions, spread them evenly
                    session_index = int(i * len(session_dates) / installment_count)
                    due_date = session_dates[session_index]
                    logger.info(f"Installment {i+1} synced with session {session_index+1}: {due_date}")
                elif frequency == 'weekly':
                    due_date = first_date + timedelta(weeks=i)
                elif frequency == 'biweekly':
                    due_date = first_date + timedelta(weeks=i * 2)
                elif frequency == 'monthly':
                    due_date = first_date + timedelta(days=i * 30)
                else:  # custom
                    due_date = first_date

                # Determine amount (last installment gets remainder)
                installment_amount = last_installment_amount if i == installment_count - 1 else amount_per_installment

                installment = InstallmentPayment(
                    installment_id=str(uuid.uuid4()),
                    hospital_id=hospital_id,
                    plan_id=plan_id,
                    installment_number=i + 1,
                    due_date=due_date,
                    amount=installment_amount,
                    paid_amount=Decimal('0.00'),
                    status='pending',
                    created_at=datetime.utcnow()
                )
                session.add(installment)
                installments.append(installment)

            logger.info(f"Generated {len(installments)} installments for plan {plan_id}")

            return {
                'success': True,
                'installments': [inst.installment_id for inst in installments],
                'count': len(installments)
            }

        except Exception as e:
            logger.error(f"Error generating installments in session: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate installments: {str(e)}'
            }

    # ==========================================
    # SESSION GENERATION
    # ==========================================

    def _generate_sessions_in_session(
        self,
        session,
        plan_id: str,
        total_sessions: int,
        hospital_id: str,
        created_by: str,
        first_session_date: date = None,
        session_frequency: str = 'monthly'
    ) -> Dict[str, Any]:
        """
        Auto-generate session records in existing session with scheduled dates
        Called from create() to avoid nested transactions

        Args:
            session: Database session
            plan_id: Plan ID
            total_sessions: Number of sessions to create
            hospital_id: Hospital ID
            created_by: User ID
            first_session_date: Date of first session (default: today)
            session_frequency: Session frequency (default: 'monthly')
        """
        try:
            # Default to today if no first session date provided
            if not first_session_date:
                first_session_date = date.today()

            sessions_created = []

            for i in range(total_sessions):
                # Calculate session date based on frequency
                if session_frequency == 'weekly':
                    session_date = first_session_date + timedelta(weeks=i)
                elif session_frequency == 'biweekly':
                    session_date = first_session_date + timedelta(weeks=i * 2)
                elif session_frequency == 'monthly':
                    session_date = first_session_date + timedelta(days=i * 30)
                else:  # custom or default
                    session_date = first_session_date + timedelta(days=i * 30)  # Default to monthly

                pkg_session = PackageSession(
                    session_id=str(uuid.uuid4()),
                    hospital_id=hospital_id,
                    plan_id=plan_id,
                    session_number=i + 1,
                    session_date=session_date,  # ✅ Scheduled date
                    session_status='scheduled',
                    created_at=datetime.utcnow(),
                    created_by=created_by,
                    updated_by=created_by
                )
                session.add(pkg_session)
                sessions_created.append(pkg_session)

            logger.info(f"Generated {len(sessions_created)} sessions for plan {plan_id} (frequency: {session_frequency}, start: {first_session_date})")

            return {
                'success': True,
                'sessions': [s.session_id for s in sessions_created],
                'session_objects': sessions_created,  # Return session objects for date extraction
                'count': len(sessions_created)
            }

        except Exception as e:
            logger.error(f"Error generating sessions in session: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to generate sessions: {str(e)}'
            }

    # ==========================================
    # OVERRIDE GET_BY_ID TO QUERY ACTUAL TABLE
    # Fix: Query table directly, not view (view has join issues immediately after creation)
    # ==========================================

    def get_by_id(self, item_id: str, **kwargs) -> Optional[Dict]:
        """
        Override get_by_id to query the actual PackagePaymentPlan table instead of the view.

        The view (PackagePaymentPlanView) has INNER JOINs that might fail immediately after creation.
        Querying the table directly ensures we can retrieve the newly created plan.

        Args:
            item_id: Plan ID (plan_id)
            **kwargs: hospital_id, branch_id, user

        Returns:
            Plan dictionary with all fields, or None if not found
        """
        try:
            hospital_id = kwargs.get('hospital_id')
            if not hospital_id:
                logger.error("get_by_id: hospital_id required")
                return None

            logger.info(f"[package_payment_plans] get_by_id: Querying table for plan_id={item_id}")

            with get_db_session() as session:
                # First, do a raw check to see if the record exists at all (ignore filters)
                raw_check = session.query(PackagePaymentPlan).filter(
                    PackagePaymentPlan.plan_id == item_id
                ).first()

                if raw_check:
                    logger.info(f"[DEBUG] Record EXISTS in DB: plan_id={item_id}, hospital_id={raw_check.hospital_id}, branch_id={raw_check.branch_id}, is_deleted={raw_check.is_deleted}")
                else:
                    logger.warning(f"[DEBUG] Record DOES NOT EXIST in DB at all: plan_id={item_id}")

                # Query the actual table, not the view
                query = session.query(PackagePaymentPlan).filter(
                    and_(
                        PackagePaymentPlan.plan_id == item_id,
                        PackagePaymentPlan.hospital_id == hospital_id,
                        PackagePaymentPlan.is_deleted == False
                    )
                )

                # Apply branch filter if provided (include NULL branch_id - hospital-level plans)
                branch_id = kwargs.get('branch_id')
                if branch_id:
                    logger.info(f"[DEBUG] Applying branch filter: branch_id={branch_id}")
                    query = query.filter(
                        or_(
                            PackagePaymentPlan.branch_id == branch_id,
                            PackagePaymentPlan.branch_id == None  # Include hospital-level plans
                        )
                    )

                plan = query.first()

                if not plan:
                    logger.warning(f"âŒ Plan not found in table: {item_id}")
                    return None

                logger.info(f"âœ… Found plan in table: {item_id}")

                # Convert to dictionary using database_service
                from app.services.database_service import get_entity_dict
                plan_dict = get_entity_dict(plan)

                # Enrich with related data
                plan_dict = self._enrich_plan_with_related_data(plan_dict, session)

                return plan_dict

        except Exception as e:
            logger.error(f"Error in get_by_id for plan {item_id}: {str(e)}", exc_info=True)
            return None

    def _enrich_plan_with_related_data(self, plan_dict: Dict, session) -> Dict:
        """
        Enrich plan data with related patient, package, and invoice information.
        Mimics what the view provides, but done manually from the table query.
        """
        try:
            from app.models.master import Patient
            from app.models.transaction import InvoiceHeader

            # Get patient info
            patient_id = plan_dict.get('patient_id')
            if patient_id:
                patient = session.query(Patient).filter(Patient.patient_id == patient_id).first()
                if patient:
                    plan_dict['patient_name'] = patient.full_name
                    plan_dict['mrn'] = patient.mrn
                    plan_dict['patient_display'] = f"{patient.full_name} ({patient.mrn})"

            # Get package info
            package_id = plan_dict.get('package_id')
            if package_id:
                package = session.query(Package).filter(Package.package_id == package_id).first()
                if package:
                    plan_dict['package_name'] = package.package_name
                    plan_dict['package_price'] = package.price
                    plan_dict['package_display'] = f"{package.package_name} - ₹{package.price:,.2f}"

            # Get invoice info
            invoice_id = plan_dict.get('invoice_id')
            if invoice_id:
                invoice = session.query(InvoiceHeader).filter(InvoiceHeader.invoice_id == invoice_id).first()
                if invoice:
                    plan_dict['invoice_number'] = invoice.invoice_number
                    plan_dict['invoice_date'] = invoice.invoice_date
                    plan_dict['invoice_total'] = invoice.grand_total

                    # Compute invoice status
                    if invoice.is_cancelled:
                        plan_dict['invoice_status'] = 'cancelled'
                    elif invoice.balance_due == 0:
                        plan_dict['invoice_status'] = 'paid'
                    elif invoice.paid_amount > 0:
                        plan_dict['invoice_status'] = 'partial'
                    else:
                        plan_dict['invoice_status'] = 'pending'

            # Compute derived fields for edit form
            total_amount = plan_dict.get('total_amount', 0) or 0
            paid_amount = plan_dict.get('paid_amount', 0) or 0
            plan_dict['balance_amount'] = float(total_amount) - float(paid_amount)

            total_sessions = plan_dict.get('total_sessions', 0) or 0
            completed_sessions = plan_dict.get('completed_sessions', 0) or 0
            plan_dict['remaining_sessions'] = int(total_sessions) - int(completed_sessions)

            return plan_dict

        except Exception as e:
            logger.error(f"Error enriching plan data: {str(e)}", exc_info=True)
            return plan_dict

    # ==========================================
    # INSTALLMENT PAYMENT RECORDING
    # ==========================================

    def record_installment_payment(
        self,
        installment_id: str,
        paid_amount: Decimal,
        payment_id: str,
        hospital_id: str,
        session=None
    ) -> Dict[str, Any]:
        """
        Record payment against an installment
        Called from payment recording screen

        Args:
            installment_id: Installment ID
            paid_amount: Amount paid
            payment_id: Payment details record ID
            hospital_id: Hospital ID
            session: Database session (optional - if provided, caller manages commit/rollback)

        Returns:
            {'success': bool, 'installment_id': str}
        """
        # If session provided, use internal method and let caller manage transaction
        if session is not None:
            return self._record_installment_payment_internal(
                session, installment_id, paid_amount, payment_id, hospital_id
            )

        # Otherwise create new session and commit
        try:
            with get_db_session() as new_session:
                result = self._record_installment_payment_internal(
                    new_session, installment_id, paid_amount, payment_id, hospital_id
                )

                if result['success']:
                    new_session.commit()
                    logger.info("✅ Installment payment transaction committed successfully")

                    # Invalidate cache (after successful commit)
                    invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                    invalidate_service_cache_for_entity('installment_payments', cascade=False)

                return result

        except Exception as e:
            logger.error(f"Error recording installment payment: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to record installment payment: {str(e)}'
            }

    def _record_installment_payment_internal(
        self,
        session,
        installment_id: str,
        paid_amount: Decimal,
        payment_id: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Internal method to record installment payment
        Session management is handled by caller

        NOTE: This method ONLY updates installment records (paid_amount, status).
        AR entries are created by the invoice payment flow since package plans
        are linked to invoices. The payment is recorded against the invoice's
        package line item, not as a separate package_installment AR entry.

        Args:
            session: Database session (required)
            installment_id: Installment ID
            paid_amount: Amount paid
            payment_id: Payment details record ID
            hospital_id: Hospital ID

        Returns:
            {'success': bool, 'installment_id': str}
        """
        try:
            # Fetch installment
            installment = session.query(InstallmentPayment).filter(
                and_(
                    InstallmentPayment.installment_id == installment_id,
                    InstallmentPayment.hospital_id == hospital_id
                )
            ).first()

            if not installment:
                return {
                    'success': False,
                    'error': 'Installment not found'
                }

            # Get payment plan details
            plan = session.query(PackagePaymentPlan).filter(
                PackagePaymentPlan.plan_id == installment.plan_id
            ).first()

            if not plan:
                return {
                    'success': False,
                    'error': 'Payment plan not found'
                }

            # Get payment details to verify it exists
            from app.models.transaction import PaymentDetail
            payment = session.query(PaymentDetail).filter(
                PaymentDetail.payment_id == payment_id
            ).first()

            if not payment:
                return {
                    'success': False,
                    'error': 'Payment record not found'
                }

            # ✅ Update installment paid amount and status
            old_paid_amount = installment.paid_amount or Decimal('0.00')
            installment.paid_amount = old_paid_amount + Decimal(str(paid_amount))
            installment.payment_id = payment_id

            # Update status based on paid amount
            if installment.paid_amount >= installment.amount:
                installment.status = 'paid'
                installment.paid_date = datetime.now().date()
                logger.info(f"Installment {installment_id} fully paid")
            elif installment.paid_amount > Decimal('0.00'):
                installment.status = 'partial'
                logger.info(f"Installment {installment_id} partially paid: {installment.paid_amount}/{installment.amount}")

            # ✅ CREATE AR SUBLEDGER ENTRY FOR INSTALLMENT PAYMENT
            # When payments are allocated directly to installments (not through invoice),
            # we need to create AR subledger entries to track the receivable properly
            try:
                from app.models.transaction import ARSubledger
                from app.models.config import Branch

                # Get patient_id from plan
                patient_id = plan.patient_id

                # Get branch_id from payment or hospital
                branch_id = payment.branch_id if hasattr(payment, 'branch_id') and payment.branch_id else None
                if not branch_id:
                    # Get default branch for hospital
                    default_branch = session.query(Branch).filter(
                        Branch.hospital_id == hospital_id
                    ).first()
                    branch_id = default_branch.branch_id if default_branch else hospital_id

                # Create AR credit entry for installment payment
                ar_entry = ARSubledger(
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    transaction_date=payment.payment_date,
                    entry_type='payment',
                    reference_id=payment_id,  # Payment ID
                    reference_type='installment_payment',  # Distinguish from invoice payments
                    reference_number=f"Installment #{installment.installment_number}",
                    patient_id=patient_id,
                    debit_amount=Decimal('0'),
                    credit_amount=Decimal(str(paid_amount)),
                    gl_transaction_id=payment.gl_entry_id if hasattr(payment, 'gl_entry_id') else None,
                    reference_line_item_id=plan.invoice_line_item_id if hasattr(plan, 'invoice_line_item_id') and plan.invoice_line_item_id else None,
                    item_type='Package Installment',
                    item_name=f"Installment #{installment.installment_number} - Plan {plan.plan_id}"
                )
                session.add(ar_entry)
                logger.info(f"✓ Created AR subledger entry for installment payment: ₹{paid_amount}")

            except Exception as ar_error:
                logger.error(f"Error creating AR subledger entry for installment: {str(ar_error)}", exc_info=True)
                # Don't fail the entire payment if AR creation fails - log and continue
                # The installment is still recorded correctly

            logger.info(f"✓ Updated installment {installment_id}: paid ₹{paid_amount}, status={installment.status}")

            return {
                'success': True,
                'installment_id': installment_id,
                'new_status': installment.status,
                'total_paid': float(installment.paid_amount)
            }

        except Exception as e:
            logger.error(f"Error in internal installment payment: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to record installment payment: {str(e)}'
            }

    # ==========================================
    # SESSION COMPLETION
    # ==========================================

    def complete_session(
        self,
        session_id: str,
        actual_date: date,
        performed_by: str,
        notes: Optional[str],
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Mark a session as completed
        Called from detail view action

        Args:
            session_id: Session ID
            actual_date: Date session was performed
            performed_by: User ID of person who performed service
            notes: Service notes
            hospital_id: Hospital ID

        Returns:
            {'success': bool, 'session_id': str}
        """
        try:
            with get_db_session() as session:
                # Fetch session
                pkg_session = session.query(PackageSession).filter(
                    and_(
                        PackageSession.session_id == session_id,
                        PackageSession.hospital_id == hospital_id
                    )
                ).first()

                if not pkg_session:
                    return {
                        'success': False,
                        'error': 'Session not found'
                    }

                # Convert actual_date to date object if string
                if isinstance(actual_date, str):
                    actual_date = datetime.strptime(actual_date, '%Y-%m-%d').date()

                # Update session - keep session_date (scheduled), set actual_completion_date
                pkg_session.actual_completion_date = actual_date
                pkg_session.session_status = 'completed'
                pkg_session.performed_by = performed_by
                pkg_session.service_notes = notes
                pkg_session.updated_at = datetime.utcnow()

                # CRITICAL: Update parent plan's completed_sessions count
                plan_id = pkg_session.plan_id
                completed_count = session.query(PackageSession).filter(
                    and_(
                        PackageSession.plan_id == plan_id,
                        PackageSession.session_status == 'completed',
                        PackageSession.hospital_id == hospital_id
                    )
                ).count()

                # Update plan
                plan = session.query(PackagePaymentPlan).filter(
                    PackagePaymentPlan.plan_id == plan_id
                ).first()

                if plan:
                    plan.completed_sessions = completed_count
                    plan.updated_at = datetime.utcnow()
                    logger.info(f"Updated plan {plan_id} completed_sessions to {completed_count}")

                session.commit()

                # Invalidate cache
                invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                invalidate_service_cache_for_entity('package_sessions', cascade=False)

                logger.info(f"Session {session_id} marked as completed, plan updated with {completed_count} completed sessions")

                return {
                    'success': True,
                    'session_id': session_id,
                    'message': 'Session completed successfully'
                }

        except Exception as e:
            logger.error(f"Error completing session: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to complete session: {str(e)}'
            }

    def update_session_date(
        self,
        session_id: str,
        session_date: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Update session scheduled date (rescheduling)

        Args:
            session_id: Session ID
            session_date: New scheduled date (YYYY-MM-DD)
            hospital_id: Hospital ID

        Returns:
            {'success': bool, 'session_id': str, 'message': str}
        """
        try:
            with get_db_session() as session:
                # Fetch session
                pkg_session = session.query(PackageSession).filter(
                    and_(
                        PackageSession.session_id == session_id,
                        PackageSession.hospital_id == hospital_id
                    )
                ).first()

                if not pkg_session:
                    return {
                        'success': False,
                        'error': 'Session not found'
                    }

                # Check if already completed
                if pkg_session.session_status == 'completed':
                    return {
                        'success': False,
                        'error': 'Cannot reschedule completed session'
                    }

                # Convert date string to date object
                if isinstance(session_date, str):
                    session_date = datetime.strptime(session_date, '%Y-%m-%d').date()

                # Update scheduled date
                pkg_session.session_date = session_date
                pkg_session.updated_at = datetime.utcnow()

                session.commit()

                # Invalidate cache
                invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                invalidate_service_cache_for_entity('package_sessions', cascade=False)

                logger.info(f"Session {session_id} date updated to {session_date}")

                return {
                    'success': True,
                    'session_id': str(session_id),
                    'message': 'Session date updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating session date: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to update session date: {str(e)}'
            }

    def update_installment_due_date(
        self,
        installment_id: str,
        due_date: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Update installment due date (rescheduling)

        Args:
            installment_id: Installment ID
            due_date: New due date (YYYY-MM-DD)
            hospital_id: Hospital ID

        Returns:
            {'success': bool, 'installment_id': str, 'message': str}
        """
        try:
            with get_db_session() as session:
                # Fetch installment
                installment = session.query(InstallmentPayment).filter(
                    and_(
                        InstallmentPayment.installment_id == installment_id,
                        InstallmentPayment.hospital_id == hospital_id
                    )
                ).first()

                if not installment:
                    return {
                        'success': False,
                        'error': 'Installment not found'
                    }

                # Check if already paid
                if installment.status == 'paid':
                    return {
                        'success': False,
                        'error': 'Cannot reschedule paid installment'
                    }

                # Convert date string to date object
                if isinstance(due_date, str):
                    due_date = datetime.strptime(due_date, '%Y-%m-%d').date()

                # Update due date
                installment.due_date = due_date
                installment.updated_at = datetime.utcnow()

                session.commit()

                # Invalidate cache
                invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                invalidate_service_cache_for_entity('installment_payments', cascade=False)

                logger.info(f"Installment {installment_id} due date updated to {due_date}")

                return {
                    'success': True,
                    'installment_id': str(installment_id),
                    'message': 'Installment due date updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating installment due date: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to update installment due date: {str(e)}'
            }

    # ==========================================
    # HELPER METHODS
    # ==========================================

    def _fetch_package_details(self, package_id: str, hospital_id: str) -> Optional[Dict]:
        """
        Fetch package details from packages table

        Args:
            package_id: Package UUID
            hospital_id: Hospital ID for tenant filtering

        Returns:
            Dict with package details or None if not found
        """
        try:
            with get_db_session() as session:
                package = session.query(Package).filter(
                    and_(
                        Package.package_id == package_id,
                        Package.hospital_id == hospital_id,
                        Package.is_deleted == False  # Exclude soft-deleted packages
                    )
                ).first()

                if not package:
                    logger.warning(f"Package not found: {package_id}")
                    return None

                # Return package details as dict
                return {
                    'package_id': str(package.package_id),
                    'package_name': package.package_name,
                    'price': package.price,
                    'description': package.package_name,  # Package model may not have description field
                    'package_code': '',  # Package model may not have code field
                    'gst_rate': package.gst_rate,
                    'is_gst_exempt': package.is_gst_exempt
                }

        except Exception as e:
            logger.error(f"Error fetching package details: {str(e)}", exc_info=True)
            return None

    # ==========================================
    # QUERY METHODS
    # ==========================================

    def get_patient_invoices_with_packages(
        self,
        patient_id: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Get all invoices for a patient that contain package line items
        Used by package payment plan creation screen

        Args:
            patient_id: Patient ID
            hospital_id: Hospital ID

        Returns:
            {
                'success': bool,
                'invoices': [
                    {
                        'invoice_id': str,
                        'invoice_number': str,
                        'invoice_date': str,
                        'package_id': str,
                        'package_name': str,
                        'package_price': Decimal,
                        'line_item_total': Decimal,
                        'invoice_status': str
                    }
                ],
                'count': int
            }
        """
        try:
            from app.models.transaction import InvoiceHeader, InvoiceLineItem
            from app.models.master import Package
            from sqlalchemy import case

            with get_db_session() as session:
                # Compute invoice status from is_cancelled and balance_due
                invoice_status_expr = case(
                    (InvoiceHeader.is_cancelled == True, 'cancelled'),
                    (InvoiceHeader.balance_due == 0, 'paid'),
                    (InvoiceHeader.paid_amount > 0, 'partial'),
                    else_='pending'
                ).label('invoice_status')

                # Query invoices with package line items
                query = session.query(
                    InvoiceHeader.invoice_id,
                    InvoiceHeader.invoice_number,
                    InvoiceHeader.invoice_date,
                    invoice_status_expr,
                    InvoiceLineItem.line_item_id,
                    InvoiceLineItem.package_id,
                    InvoiceLineItem.line_total,  # ✅ Correct field name
                    Package.package_name,
                    Package.price.label('package_price')
                ).join(
                    InvoiceLineItem,
                    InvoiceHeader.invoice_id == InvoiceLineItem.invoice_id
                ).join(
                    Package,
                    InvoiceLineItem.package_id == Package.package_id
                ).filter(
                    and_(
                        InvoiceHeader.patient_id == patient_id,
                        InvoiceHeader.hospital_id == hospital_id,
                        InvoiceLineItem.package_id.isnot(None),  # Only package line items
                        InvoiceHeader.is_cancelled == False  # Exclude cancelled invoices (InvoiceHeader has NO is_deleted field)
                    )
                ).order_by(
                    InvoiceHeader.invoice_date.desc()
                ).all()

                # Format results
                invoices = []
                for row in query:
                    invoices.append({
                        'invoice_id': str(row.invoice_id),
                        'invoice_number': row.invoice_number,
                        'invoice_date': row.invoice_date.strftime('%Y-%m-%d') if row.invoice_date else None,
                        'invoice_status': row.invoice_status,
                        'line_item_id': str(row.line_item_id),
                        'package_id': str(row.package_id),
                        'package_name': row.package_name,
                        'package_price': float(row.package_price) if row.package_price else 0.0,
                        'line_item_total': float(row.line_total) if row.line_total else 0.0  # ✅ Correct field
                    })

                logger.info(f"Found {len(invoices)} invoices with packages for patient {patient_id}")

                return {
                    'success': True,
                    'invoices': invoices,
                    'count': len(invoices)
                }

        except Exception as e:
            logger.error(f"Error fetching patient invoices with packages: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to fetch invoices: {str(e)}',
                'invoices': [],
                'count': 0
            }

    def get_patient_pending_installments(
        self,
        patient_id: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Get all pending installments for a patient
        Used by payment recording screen

        Args:
            patient_id: Patient ID
            hospital_id: Hospital ID

        Returns:
            {
                'success': bool,
                'installments': list,
                'count': int
            }
        """
        try:
            with get_db_session() as session:
                # Query installments
                installments = session.query(InstallmentPayment).join(
                    PackagePaymentPlan,
                    InstallmentPayment.plan_id == PackagePaymentPlan.plan_id
                ).filter(
                    and_(
                        PackagePaymentPlan.patient_id == patient_id,
                        PackagePaymentPlan.hospital_id == hospital_id,
                        PackagePaymentPlan.status == 'active',
                        InstallmentPayment.status.in_(['pending', 'partial', 'overdue'])
                    )
                ).order_by(InstallmentPayment.due_date.asc()).all()

                # Convert to dict
                installments_data = []
                for inst in installments:
                    plan = inst.plan
                    installments_data.append({
                        'installment_id': inst.installment_id,
                        'plan_id': inst.plan_id,
                        'package_name': plan.package_name if plan else 'N/A',
                        'installment_number': inst.installment_number,
                        'due_date': inst.due_date.isoformat() if inst.due_date else None,
                        'amount': float(inst.amount) if inst.amount else 0,
                        'paid_amount': float(inst.paid_amount) if inst.paid_amount else 0,
                        'balance_amount': float(inst.balance_amount) if hasattr(inst, 'balance_amount') else float(inst.amount - (inst.paid_amount or 0)),
                        'status': inst.status
                    })

                return {
                    'success': True,
                    'installments': installments_data,
                    'count': len(installments_data)
                }

        except Exception as e:
            logger.error(f"Error fetching pending installments: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to fetch installments: {str(e)}',
                'installments': [],
                'count': 0
            }

    # =============================================================================
    # CONTEXT FUNCTIONS FOR DETAIL VIEW TEMPLATES
    # =============================================================================

    def get_plan_installments(self, item_id: str, item: Dict = None,
                              hospital_id: str = None, branch_id: str = None) -> Dict[str, Any]:
        """
        Get installments for a plan - used by detail view template

        Args:
            item_id: Plan ID
            item: Plan item dict (optional)
            hospital_id: Hospital ID
            branch_id: Branch ID

        Returns:
            {'child_items': list of installment dicts, 'plan_status': str, 'is_discontinued': bool}
        """
        try:
            logger.info(f"[get_plan_installments] plan_id={item_id}")

            with get_db_session() as session:
                # Get the plan to check status
                plan = session.query(PackagePaymentPlan).filter(
                    PackagePaymentPlan.plan_id == item_id
                ).first()

                plan_status = plan.status if plan else 'active'
                is_discontinued = (plan_status == 'discontinued')

                # Query installments
                installments = session.query(InstallmentPayment).filter(
                    InstallmentPayment.plan_id == item_id
                ).order_by(InstallmentPayment.installment_number).all()

                # Convert to template-friendly format
                child_items = []
                for inst in installments:
                    # For discontinued plans, balance should be 0 for unpaid installments
                    paid_amount = inst.paid_amount or 0
                    balance_amount = 0 if is_discontinued else ((inst.amount or 0) - paid_amount)

                    child_items.append({
                        'installment_id': str(inst.installment_id),
                        'installment_number': inst.installment_number,
                        'due_date': inst.due_date,
                        'amount': inst.amount,
                        'paid_amount': paid_amount,
                        'balance_amount': balance_amount,  # Zero for discontinued plans
                        'paid_date': inst.paid_date,
                        'status': 'discontinued' if is_discontinued and inst.status != 'paid' else (inst.status or 'pending'),
                        # Audit fields (TimestampMixin)
                        'created_at': inst.created_at,
                        'created_by': inst.created_by,
                        'updated_at': inst.updated_at,
                        'updated_by': inst.updated_by
                    })

                logger.info(f"[get_plan_installments] Found {len(child_items)} installments, plan_status={plan_status}")
                return {
                    'child_items': child_items,
                    'plan_status': plan_status,
                    'is_discontinued': is_discontinued
                }

        except Exception as e:
            logger.error(f"Error fetching plan installments: {str(e)}", exc_info=True)
            return {
                'child_items': [],
                'plan_status': 'active',
                'is_discontinued': False
            }

    def get_plan_sessions(self, item_id: str, item: Dict = None,
                          hospital_id: str = None, branch_id: str = None) -> Dict[str, Any]:
        """
        Get sessions for a plan - used by detail view template

        Args:
            item_id: Plan ID
            item: Plan item dict (optional)
            hospital_id: Hospital ID
            branch_id: Branch ID

        Returns:
            {'child_items': list of session dicts}
        """
        try:
            logger.info(f"[get_plan_sessions] plan_id={item_id}")

            with get_db_session() as session:
                # Query sessions
                sessions = session.query(PackageSession).filter(
                    PackageSession.plan_id == item_id
                ).order_by(PackageSession.session_number).all()

                # Convert to template-friendly format
                child_items = []
                for sess in sessions:
                    child_items.append({
                        'session_id': str(sess.session_id),
                        'session_number': sess.session_number,
                        'session_date': sess.session_date,  # Scheduled date (can be rescheduled)
                        'actual_completion_date': sess.actual_completion_date,  # When actually completed
                        'service_name': sess.service_name,
                        'session_status': sess.session_status or 'scheduled',
                        'performed_by': sess.performed_by,
                        'service_notes': sess.service_notes,
                        # Audit fields
                        'created_at': sess.created_at,
                        'created_by': sess.created_by,
                        'updated_at': sess.updated_at,
                        'updated_by': sess.updated_by
                    })

                logger.info(f"[get_plan_sessions] Found {len(child_items)} sessions")
                return {'child_items': child_items}

        except Exception as e:
            logger.error(f"Error fetching plan sessions: {str(e)}", exc_info=True)
            return {'child_items': []}

    # ==========================================
    # UPDATE WITH REPLANNING LOGIC
    # ==========================================

    def update_package_payment_plan(
        self,
        package_payment_plan_id: str,
        package_payment_plan_data: Dict,
        hospital_id: str,
        current_user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update package payment plan with intelligent replanning logic

        Handles:
        - Session count changes (add/remove sessions)
        - Installment count changes (recalculate amounts)
        - Status changes (discontinued triggers refund)

        Args:
            package_payment_plan_id: Plan ID
            package_payment_plan_data: Update data
            hospital_id: Hospital ID
            current_user_id: User ID making the change

        Returns:
            {'success': bool, 'data': dict, 'replanning_summary': dict}
        """
        try:
            with get_db_session() as db_session:
                # Get existing plan
                plan = db_session.query(PackagePaymentPlan).filter(
                    and_(
                        PackagePaymentPlan.plan_id == package_payment_plan_id,
                        PackagePaymentPlan.hospital_id == hospital_id
                    )
                ).first()

                if not plan:
                    return {
                        'success': False,
                        'error': 'Package payment plan not found'
                    }

                # Store original values for comparison
                original_total_sessions = plan.total_sessions
                original_installment_count = plan.installment_count

                replanning_summary = {
                    'sessions_changed': False,
                    'installments_changed': False,
                    'sessions_added': 0,
                    'sessions_removed': 0,
                    'installments_recalculated': False,
                    'warnings': []
                }

                # Check if total_sessions changed
                new_total_sessions = package_payment_plan_data.get('total_sessions')
                if new_total_sessions and int(new_total_sessions) != original_total_sessions:
                    logger.info(f"Session count changed: {original_total_sessions} → {new_total_sessions}")

                    # Validate: Cannot reduce below completed sessions
                    if int(new_total_sessions) < plan.completed_sessions:
                        return {
                            'success': False,
                            'error': f'Cannot reduce total sessions to {new_total_sessions}. Already completed {plan.completed_sessions} sessions.'
                        }

                    # Replan sessions
                    replan_result = self._replan_sessions(
                        plan,
                        original_total_sessions,
                        int(new_total_sessions),
                        db_session,
                        hospital_id,
                        current_user_id
                    )

                    replanning_summary['sessions_changed'] = True
                    replanning_summary['sessions_added'] = replan_result.get('added', 0)
                    replanning_summary['sessions_removed'] = replan_result.get('removed', 0)
                    replanning_summary['warnings'].extend(replan_result.get('warnings', []))

                # Check if installment_count changed
                new_installment_count = package_payment_plan_data.get('installment_count')
                if new_installment_count and int(new_installment_count) != original_installment_count:
                    logger.info(f"Installment count changed: {original_installment_count} → {new_installment_count}")

                    # Validate: Cannot reduce below paid installments
                    paid_count = db_session.query(InstallmentPayment).filter(
                        and_(
                            InstallmentPayment.plan_id == package_payment_plan_id,
                            InstallmentPayment.status == 'paid'
                        )
                    ).count()

                    if int(new_installment_count) < paid_count:
                        return {
                            'success': False,
                            'error': f'Cannot reduce installments to {new_installment_count}. Already paid {paid_count} installments.'
                        }

                    # Replan installments
                    replan_result = self._replan_installments(
                        plan,
                        original_installment_count,
                        int(new_installment_count),
                        db_session,
                        hospital_id,
                        current_user_id
                    )

                    replanning_summary['installments_changed'] = True
                    replanning_summary['installments_recalculated'] = replan_result.get('recalculated', False)
                    replanning_summary['warnings'].extend(replan_result.get('warnings', []))

                # Check if status changed to 'discontinued'
                original_status = plan.status
                new_status = package_payment_plan_data.get('status')
                discontinuation_summary = None

                if new_status == 'discontinued' and original_status != 'discontinued':
                    logger.info(f"Status changing to discontinued: {original_status} → {new_status}")

                    # Get discontinuation reason
                    discontinuation_reason = package_payment_plan_data.get('discontinuation_reason', '')

                    if not discontinuation_reason or discontinuation_reason.strip() == '':
                        return {
                            'success': False,
                            'error': 'Discontinuation reason is required when changing status to Discontinued'
                        }

                    # Handle discontinuation
                    discontinuation_result = self._handle_discontinuation(
                        plan,
                        discontinuation_reason,
                        db_session,
                        hospital_id,
                        current_user_id
                    )

                    if not discontinuation_result['success']:
                        return {
                            'success': False,
                            'error': discontinuation_result['message']
                        }

                    discontinuation_summary = discontinuation_result
                    logger.info(f"✅ Discontinuation handled: {discontinuation_result['message']}")

                    # Don't update status field again - already set in _handle_discontinuation
                    # Remove status from data to prevent overwrite
                    package_payment_plan_data = {k: v for k, v in package_payment_plan_data.items() if k != 'status'}

                # Update plan fields
                for field, value in package_payment_plan_data.items():
                    if hasattr(plan, field) and field not in ['plan_id', 'hospital_id', 'branch_id', 'created_at', 'created_by']:
                        setattr(plan, field, value)

                plan.updated_at = datetime.utcnow()
                plan.updated_by = current_user_id

                db_session.commit()

                # Invalidate cache
                invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                invalidate_service_cache_for_entity('package_sessions', cascade=False)
                invalidate_service_cache_for_entity('installment_payments', cascade=False)

                logger.info(f"✅ Updated package plan {package_payment_plan_id} with replanning")

                # Build success message
                if discontinuation_summary:
                    message = discontinuation_summary['message']
                else:
                    message = 'Package payment plan updated successfully'

                result = {
                    'success': True,
                    'data': {'plan_id': package_payment_plan_id},
                    'replanning_summary': replanning_summary,
                    'message': message
                }

                # Add discontinuation summary if applicable
                if discontinuation_summary:
                    result['discontinuation_summary'] = discontinuation_summary

                return result

        except Exception as e:
            logger.error(f"Error updating package payment plan: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to update plan: {str(e)}'
            }

    def _replan_sessions(
        self,
        plan: PackagePaymentPlan,
        old_count: int,
        new_count: int,
        db_session,
        hospital_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Add or remove sessions based on total_sessions change

        Returns:
            {'added': int, 'removed': int, 'warnings': [str]}
        """
        result = {'added': 0, 'removed': 0, 'warnings': []}

        try:
            if new_count > old_count:
                # ADD SESSIONS
                sessions_to_add = new_count - old_count
                logger.info(f"Adding {sessions_to_add} sessions to plan {plan.plan_id}")

                for i in range(sessions_to_add):
                    new_session_number = old_count + i + 1
                    new_session = PackageSession(
                        session_id=uuid.uuid4(),
                        plan_id=plan.plan_id,
                        hospital_id=hospital_id,
                        branch_id=plan.branch_id,
                        session_number=new_session_number,
                        session_status='scheduled',
                        created_at=datetime.utcnow(),
                        created_by=user_id
                    )
                    db_session.add(new_session)
                    result['added'] += 1

                logger.info(f"✅ Added {result['added']} sessions")

            elif new_count < old_count:
                # REMOVE SESSIONS
                sessions_to_remove = old_count - new_count
                logger.info(f"Removing {sessions_to_remove} sessions from plan {plan.plan_id}")

                # Delete only scheduled sessions beyond new count
                sessions = db_session.query(PackageSession).filter(
                    and_(
                        PackageSession.plan_id == plan.plan_id,
                        PackageSession.session_number > new_count,
                        PackageSession.session_status == 'scheduled'
                    )
                ).all()

                for sess in sessions:
                    db_session.delete(sess)
                    result['removed'] += 1

                # Check if there are completed sessions beyond new count (shouldn't happen due to validation)
                completed_beyond = db_session.query(PackageSession).filter(
                    and_(
                        PackageSession.plan_id == plan.plan_id,
                        PackageSession.session_number > new_count,
                        PackageSession.session_status == 'completed'
                    )
                ).count()

                if completed_beyond > 0:
                    result['warnings'].append(f'{completed_beyond} completed sessions exist beyond new total. Consider reviewing.')

                logger.info(f"✅ Removed {result['removed']} scheduled sessions")

            return result

        except Exception as e:
            logger.error(f"Error replanning sessions: {str(e)}")
            result['warnings'].append(f'Session replanning error: {str(e)}')
            return result

    def _replan_installments(
        self,
        plan: PackagePaymentPlan,
        old_count: int,
        new_count: int,
        db_session,
        hospital_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Recalculate installment amounts when count changes

        Returns:
            {'recalculated': bool, 'warnings': [str]}
        """
        result = {'recalculated': False, 'warnings': []}

        try:
            # Get paid amount
            paid_amount = plan.paid_amount or Decimal('0')
            total_amount = plan.total_amount or Decimal('0')
            balance_amount = total_amount - paid_amount

            # Count paid installments
            paid_installments = db_session.query(InstallmentPayment).filter(
                and_(
                    InstallmentPayment.plan_id == plan.plan_id,
                    InstallmentPayment.status == 'paid'
                )
            ).count()

            remaining_installments = new_count - paid_installments

            if remaining_installments <= 0:
                result['warnings'].append('All installments already paid. No recalculation needed.')
                return result

            # Calculate new installment amount
            new_installment_amount = balance_amount / remaining_installments

            if new_count > old_count:
                # ADD INSTALLMENTS
                installments_to_add = new_count - old_count
                logger.info(f"Adding {installments_to_add} installments to plan {plan.plan_id}")

                # Get last installment for date calculation
                last_installment = db_session.query(InstallmentPayment).filter(
                    InstallmentPayment.plan_id == plan.plan_id
                ).order_by(InstallmentPayment.installment_number.desc()).first()

                last_due_date = last_installment.due_date if last_installment else plan.first_installment_date
                frequency = plan.installment_frequency or 'monthly'

                for i in range(installments_to_add):
                    new_installment_number = old_count + i + 1
                    new_due_date = self._calculate_next_due_date(last_due_date, frequency)

                    new_installment = InstallmentPayment(
                        installment_id=uuid.uuid4(),
                        plan_id=plan.plan_id,
                        hospital_id=hospital_id,
                        branch_id=plan.branch_id,
                        installment_number=new_installment_number,
                        due_date=new_due_date,
                        amount=new_installment_amount,
                        status='pending',
                        created_at=datetime.utcnow(),
                        created_by=user_id
                    )
                    db_session.add(new_installment)
                    last_due_date = new_due_date

                result['recalculated'] = True

            elif new_count < old_count:
                # REMOVE INSTALLMENTS & RECALCULATE
                installments_to_remove = old_count - new_count
                logger.info(f"Removing {installments_to_remove} installments from plan {plan.plan_id}")

                # Delete pending installments beyond new count
                installments = db_session.query(InstallmentPayment).filter(
                    and_(
                        InstallmentPayment.plan_id == plan.plan_id,
                        InstallmentPayment.installment_number > new_count,
                        InstallmentPayment.status == 'pending'
                    )
                ).all()

                for inst in installments:
                    db_session.delete(inst)

            # Recalculate amounts for all pending/partial installments
            pending_installments = db_session.query(InstallmentPayment).filter(
                and_(
                    InstallmentPayment.plan_id == plan.plan_id,
                    InstallmentPayment.status.in_(['pending', 'partial'])
                )
            ).all()

            for inst in pending_installments:
                inst.amount = new_installment_amount
                inst.updated_at = datetime.utcnow()
                inst.updated_by = user_id

            result['recalculated'] = True
            logger.info(f"✅ Recalculated {len(pending_installments)} installments with new amount: {new_installment_amount}")

            return result

        except Exception as e:
            logger.error(f"Error replanning installments: {str(e)}")
            result['warnings'].append(f'Installment replanning error: {str(e)}')
            return result

    def _calculate_next_due_date(self, last_date: date, frequency: str) -> date:
        """Calculate next installment due date based on frequency"""
        if frequency == 'weekly':
            return last_date + timedelta(days=7)
        elif frequency == 'biweekly':
            return last_date + timedelta(days=14)
        elif frequency == 'monthly':
            # Add approximately 30 days
            return last_date + timedelta(days=30)
        else:  # custom
            return last_date + timedelta(days=30)  # Default to monthly

    def _calculate_package_allocated_payment(
        self,
        session,
        invoice_id: str,
        package_id: str
    ) -> Decimal:
        """
        Calculate allocated payment for a specific package from a mixed invoice

        Payment Allocation Priority (Point-of-Sale First):
        1. Services get paid first (consultations, procedures - already delivered)
        2. Medicines get paid second (already dispensed, cannot return easily)
        3. Packages get paid last (have installment plans, easier to collect)

        This implements the business rule: "Individual services and medicines are
        point-of-sale items. Packages will most likely have installments, it will
        be easy to collect."

        Args:
            session: Database session
            invoice_id: Invoice ID
            package_id: Package ID to calculate allocation for

        Returns:
            Allocated payment amount for this package

        Example:
            Invoice Total: ₹9,700
            - Service 1 (Consultation): ₹2,000
            - Service 2 (Lab Test): ₹1,500
            - Medicine (Paracetamol): ₹300
            - Package 1 (Hair Restoration): ₹5,900

            Payment Made: ₹4,000

            Allocation (Priority: Services → Medicines → Packages):
            - Service 1: ₹2,000 (fully paid) ✅
            - Service 2: ₹1,500 (fully paid) ✅
            - Medicine: ₹300 (fully paid) ✅
            - Package 1: ₹200 (remaining from ₹4,000 payment)

            Package payment plan should have paid_amount = ₹200 (not ₹4,000!)
        """
        try:
            logger.info(f"🔍 Calculating package allocated payment: invoice_id={invoice_id}, package_id={package_id}")

            # Find the line item for this package
            line_item = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.invoice_id == invoice_id,
                InvoiceLineItem.package_id == package_id,
                InvoiceLineItem.item_type == 'Package'
            ).first()

            if not line_item:
                logger.warning(f"❌ Package {package_id} not found in invoice {invoice_id}")
                return Decimal('0.00')

            logger.info(f"✓ Found package line item: {line_item.line_item_id}, amount=₹{line_item.line_total}")

            # Query actual AR entries for this line item to get real payment allocation
            # This is more accurate than calculating - we read actual posted AR entries
            from app.models.transaction import ARSubledger
            from sqlalchemy import cast, String

            # First, try with UUID comparison
            ar_entries = session.query(ARSubledger).filter(
                ARSubledger.reference_line_item_id == line_item.line_item_id
            ).all()

            logger.info(f"📊 Found {len(ar_entries)} AR entries for line item {line_item.line_item_id} (UUID comparison)")

            # If no entries found, try with string casting (diagnostic)
            if len(ar_entries) == 0:
                logger.warning(f"⚠️ No AR entries with UUID comparison, trying string cast...")
                ar_entries_str = session.query(ARSubledger).filter(
                    cast(ARSubledger.reference_line_item_id, String) == str(line_item.line_item_id)
                ).all()
                logger.info(f"📊 Found {len(ar_entries_str)} AR entries with string cast")
                ar_entries = ar_entries_str

            # If still no entries, check if ANY AR entries exist for this invoice
            if len(ar_entries) == 0:
                invoice_ar_entries = session.query(ARSubledger).filter(
                    ARSubledger.reference_id == invoice_id,
                    ARSubledger.reference_type == 'invoice'
                ).all()
                logger.warning(f"⚠️ No AR entries for line item, but found {len(invoice_ar_entries)} AR entries for invoice {invoice_id}")

                # Check if any have NULL reference_line_item_id
                null_line_item_count = sum(1 for e in invoice_ar_entries if e.reference_line_item_id is None)
                logger.warning(f"⚠️ {null_line_item_count} of {len(invoice_ar_entries)} AR entries have NULL reference_line_item_id")

                if null_line_item_count > 0:
                    logger.error(f"❌ AR entries for this invoice don't have line item references! Invoice was created with OLD AR posting logic.")

            if not ar_entries:
                logger.warning(f"⚠️ No AR entries found for package line item {line_item.line_item_id} - paid_amount: ₹0")
                logger.info(f"💡 This usually means: (1) Invoice not posted to AR yet, or (2) No payments allocated to this package")
                return Decimal('0.00')

            # Log each AR entry for debugging
            for idx, entry in enumerate(ar_entries, 1):
                logger.debug(f"  AR Entry {idx}: type={entry.entry_type}, debit=₹{entry.debit_amount or 0}, credit=₹{entry.credit_amount or 0}, ref_id={entry.reference_id}")

            # Calculate total debits and credits from actual AR postings
            total_debits = sum(e.debit_amount or Decimal('0') for e in ar_entries if e.entry_type == 'invoice')
            total_credits = sum(e.credit_amount or Decimal('0') for e in ar_entries if e.entry_type == 'payment')

            # Paid amount = total credits (payments allocated to this line item)
            paid_amount = total_credits

            logger.info(f"✓ Package {package_id} AR calculation: Debits=₹{total_debits} (invoice), Credits=₹{total_credits} (payments), Paid=₹{paid_amount}")

            return paid_amount

        except Exception as e:
            logger.error(f"Error getting package allocated payment from AR: {str(e)}", exc_info=True)
            # Return 0 on error to be safe - better to under-allocate than over-allocate
            return Decimal('0.00')

    def _handle_discontinuation(
        self,
        plan: PackagePaymentPlan,
        discontinuation_reason: str,
        db_session,
        hospital_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Handle plan discontinuation with refund calculation

        Process:
        1. Validate discontinuation eligibility
        2. Calculate refund amount
        3. Cancel scheduled sessions
        4. Cancel pending installments
        5. Update plan with discontinuation details

        Args:
            plan: PackagePaymentPlan instance
            discontinuation_reason: User-provided reason
            db_session: Database session
            hospital_id: Hospital ID
            user_id: User ID performing discontinuation

        Returns:
            {
                'success': bool,
                'refund_amount': Decimal,
                'sessions_cancelled': int,
                'installments_cancelled': int,
                'message': str
            }
        """
        result = {
            'success': False,
            'refund_amount': Decimal('0.00'),
            'sessions_cancelled': 0,
            'installments_cancelled': 0,
            'message': ''
        }

        try:
            # 1. VALIDATE DISCONTINUATION ELIGIBILITY
            if plan.status in ['completed', 'cancelled']:
                result['message'] = f'Cannot discontinue a {plan.status} plan'
                return result

            if not discontinuation_reason or discontinuation_reason.strip() == '':
                result['message'] = 'Discontinuation reason is required'
                return result

            # 2. CALCULATE CREDIT NOTE AMOUNT
            # New logic: Credit note = Paid Amount - Patient Liability
            # Patient liability = completed sessions × per-session cost
            remaining_sessions = plan.total_sessions - plan.completed_sessions
            if plan.total_sessions > 0:
                session_value = plan.total_amount / plan.total_sessions
                unused_sessions_value = remaining_sessions * session_value
            else:
                session_value = Decimal('0.00')
                unused_sessions_value = Decimal('0.00')

            # Calculate patient liability (completed sessions only)
            patient_liability = plan.completed_sessions * session_value

            # Calculate net position (paid vs liability)
            net_position = plan.paid_amount - patient_liability

            # CREDIT NOTE AMOUNT = Full unused sessions value (reverses AR/GL)
            # This is the amount to reverse from the original invoice
            credit_note_amount = unused_sessions_value

            # CASH REFUND AMOUNT = Only the portion of unused value that was already paid
            # This is the actual money to refund to the patient
            if net_position > 0:
                # Patient overpaid - refund the excess
                cash_refund_amount = net_position
            else:
                # Patient underpaid or exact - no cash refund
                cash_refund_amount = Decimal('0.00')

            result['refund_amount'] = credit_note_amount  # For AR/GL reversal
            result['cash_refund'] = cash_refund_amount   # For actual patient refund

            logger.info(f"Discontinuation calculation:")
            logger.info(f"  Total sessions: {plan.total_sessions}")
            logger.info(f"  Completed sessions: {plan.completed_sessions} × ₹{session_value} = ₹{patient_liability}")
            logger.info(f"  Remaining sessions: {remaining_sessions}")
            logger.info(f"  Unused sessions value: ₹{unused_sessions_value}")
            logger.info(f"  Paid amount: ₹{plan.paid_amount}")
            logger.info(f"  Net position (Paid - Liability): ₹{net_position}")
            logger.info(f"  Credit note (AR/GL reversal): ₹{credit_note_amount}")
            logger.info(f"  Cash refund to patient: ₹{cash_refund_amount}")

            # 3. CANCEL SCHEDULED SESSIONS
            scheduled_sessions = db_session.query(PackageSession).filter(
                and_(
                    PackageSession.plan_id == plan.plan_id,
                    PackageSession.session_status == 'scheduled',
                    PackageSession.hospital_id == hospital_id
                )
            ).all()

            for session in scheduled_sessions:
                session.session_status = 'cancelled'
                session.service_notes = 'Cancelled due to plan discontinuation'
                session.updated_at = datetime.utcnow()
                session.updated_by = user_id

            result['sessions_cancelled'] = len(scheduled_sessions)
            logger.info(f"✅ Cancelled {len(scheduled_sessions)} scheduled sessions")

            # 4. CANCEL PENDING INSTALLMENTS
            pending_installments = db_session.query(InstallmentPayment).filter(
                and_(
                    InstallmentPayment.plan_id == plan.plan_id,
                    InstallmentPayment.status == 'pending'
                )
            ).all()

            for installment in pending_installments:
                installment.status = 'waived'  # Valid statuses: pending, partial, paid, overdue, waived
                installment.notes = 'Waived due to plan discontinuation'
                installment.updated_at = datetime.utcnow()
                installment.updated_by = user_id

            result['installments_cancelled'] = len(pending_installments)
            logger.info(f"✅ Waived {len(pending_installments)} pending installments")

            # 5. UPDATE PLAN WITH DISCONTINUATION DETAILS
            plan.status = 'discontinued'
            plan.discontinued_at = datetime.utcnow()
            plan.discontinued_by = user_id
            plan.discontinuation_reason = discontinuation_reason
            plan.refund_amount = credit_note_amount  # Store credit note amount (AR/GL reversal)

            # Set refund status based on CASH refund amount (not credit note amount)
            if cash_refund_amount == 0:
                plan.refund_status = 'none'  # No cash refund needed
            elif cash_refund_amount > Decimal('10000.00'):
                plan.refund_status = 'pending'  # Requires approval
            else:
                plan.refund_status = 'approved'  # Auto-approved for small amounts

            plan.updated_at = datetime.utcnow()
            plan.updated_by = user_id

            # 6. CREATE CREDIT NOTE (directly in same session for atomicity)
            # Extract all values FIRST (avoid DetachedInstanceError from lazy loading)
            plan_invoice_id = plan.invoice_id
            plan_patient_id = plan.patient_id
            plan_branch_id = getattr(plan, 'branch_id', None)
            plan_plan_id = plan.plan_id

            credit_note_info = None
            if plan_invoice_id and credit_note_amount > 0:
                logger.info(f"📝 Creating credit note for ₹{credit_note_amount} in same transaction")
                try:
                    # Import models
                    from app.models.transaction import PatientCreditNote
                    import uuid

                    # Generate credit note number (pass session to avoid nested session)
                    from app.services.patient_credit_note_service import PatientCreditNoteService
                    cn_service = PatientCreditNoteService()
                    credit_note_number = cn_service.generate_credit_note_number(hospital_id, plan_branch_id, session=db_session)

                    # Create credit note record DIRECTLY (no nested session)
                    credit_note = PatientCreditNote(
                        credit_note_id=uuid.uuid4(),
                        hospital_id=hospital_id,
                        branch_id=plan_branch_id,
                        credit_note_number=credit_note_number,
                        original_invoice_id=plan_invoice_id,
                        plan_id=plan_plan_id,
                        patient_id=plan_patient_id,
                        credit_note_date=date.today(),
                        total_amount=credit_note_amount,
                        reason_code='plan_discontinued',
                        reason_description=f"{discontinuation_reason} | Cash refund: ₹{cash_refund_amount}",
                        status='draft',
                        created_at=datetime.utcnow(),
                        created_by=user_id
                    )

                    db_session.add(credit_note)
                    db_session.flush()  # Get credit_note_id assigned

                    # Update plan with credit note reference
                    plan.credit_note_id = credit_note.credit_note_id

                    credit_note_info = {
                        'credit_note_id': str(credit_note.credit_note_id),
                        'credit_note_number': credit_note_number,
                        'needs_gl_posting': True  # Flag to post GL/AR after commit
                    }
                    logger.info(f"✅ Credit note created (GL pending): {credit_note_number}")

                except Exception as cn_error:
                    logger.error(f"❌ Error creating credit note: {str(cn_error)}", exc_info=True)
                    # Don't fail the entire discontinuation just because credit note failed
                    result['warnings'] = [f"Credit note creation error: {str(cn_error)}"]

            # Set success and return data
            result['success'] = True
            result['cash_refund'] = cash_refund_amount
            result['credit_note_info'] = credit_note_info  # Pass to caller for GL posting

            if cash_refund_amount == 0:
                result['message'] = f'Plan discontinued. AR liability reduced by ₹{credit_note_amount:,.2f} for unused sessions. No cash refund needed.'
            else:
                result['message'] = f'Plan discontinued. Credit note: ₹{credit_note_amount:,.2f} | Cash refund: ₹{cash_refund_amount:,.2f} (Status: {plan.refund_status})'

            logger.info(f"✅ Plan {plan.plan_id} discontinued successfully")
            logger.info(f"   Credit note (AR/GL reversal): ₹{credit_note_amount}")
            logger.info(f"   Cash refund to patient: ₹{cash_refund_amount} (Status: {plan.refund_status})")
            logger.info(f"   Sessions cancelled: {result['sessions_cancelled']}")
            logger.info(f"   Installments cancelled: {result['installments_cancelled']}")

            return result

        except Exception as e:
            logger.error(f"Error handling discontinuation: {str(e)}", exc_info=True)
            result['message'] = f'Discontinuation failed: {str(e)}'
            return result

    def preview_discontinuation(
        self,
        plan_id: str,
        hospital_id: str
    ) -> Dict[str, Any]:
        """
        Preview discontinuation impact before user confirms
        Calculates financial impact and lists items to be cancelled

        Args:
            plan_id: Package payment plan ID
            hospital_id: Hospital ID

        Returns:
            {
                'success': bool,
                'plan_id': str,
                'plan_number': str,
                'patient_name': str,
                'package_name': str,
                'total_sessions': int,
                'completed_sessions': int,
                'remaining_sessions': int,
                'scheduled_sessions': int,
                'pending_installments': int,
                'total_amount': Decimal,
                'paid_amount': Decimal,
                'calculated_refund': Decimal,
                'invoice_number': str,
                'invoice_id': str,
                'sessions_to_cancel': list,
                'installments_to_cancel': list
            }
        """
        result = {
            'success': False,
            'error': None
        }

        try:
            with get_db_session() as session:
                # Get plan with relationships
                from sqlalchemy.orm import joinedload
                plan = session.query(PackagePaymentPlan).options(
                    joinedload(PackagePaymentPlan.invoice)
                ).filter(
                    and_(
                        PackagePaymentPlan.plan_id == plan_id,
                        PackagePaymentPlan.hospital_id == hospital_id
                    )
                ).first()

                if not plan:
                    result['error'] = 'Package payment plan not found'
                    return result

                # Validate discontinuation eligibility
                if plan.status in ['completed', 'cancelled', 'discontinued']:
                    result['error'] = f'Cannot discontinue a {plan.status} plan'
                    return result

                # Calculate per-session cost
                # Ideally from service master, but for now use package price / sessions
                if plan.total_sessions > 0:
                    session_value = plan.total_amount / plan.total_sessions
                else:
                    session_value = Decimal('0.00')

                # Calculate patient liability (completed sessions only)
                patient_liability = plan.completed_sessions * session_value

                # Calculate net position (paid vs liability)
                net_position = plan.paid_amount - patient_liability

                # REVERSAL VALUE = Full unused sessions value (reverses AR/GL)
                remaining_sessions = plan.total_sessions - plan.completed_sessions
                unused_sessions_value = remaining_sessions * session_value
                calculated_reversal_value = unused_sessions_value

                # CASH REFUND AMOUNT = Only the portion of unused value that was already paid
                if net_position > 0:
                    # Patient overpaid - refund the excess
                    cash_refund_amount = net_position
                else:
                    # Patient underpaid or exact - no cash refund
                    cash_refund_amount = Decimal('0.00')

                # Get sessions to cancel
                scheduled_sessions = session.query(PackageSession).filter(
                    and_(
                        PackageSession.plan_id == plan.plan_id,
                        PackageSession.session_status == 'scheduled'
                    )
                ).all()

                sessions_to_cancel = [
                    {
                        'session_id': str(s.session_id),
                        'session_number': s.session_number,
                        'session_date': s.session_date.isoformat() if s.session_date else None,
                        'status': s.session_status
                    }
                    for s in scheduled_sessions
                ]

                # Get installments to cancel
                pending_installments = session.query(InstallmentPayment).filter(
                    and_(
                        InstallmentPayment.plan_id == plan.plan_id,
                        InstallmentPayment.status == 'pending'
                    )
                ).all()

                installments_to_cancel = [
                    {
                        'installment_id': str(i.installment_id),
                        'installment_number': i.installment_number,
                        'due_date': i.due_date.isoformat() if i.due_date else None,
                        'amount': float(i.amount),
                        'status': i.status
                    }
                    for i in pending_installments
                ]

                # Get patient and package names
                from app.models.master import Patient, Package
                patient = session.query(Patient).filter(Patient.patient_id == plan.patient_id).first()
                package = session.query(Package).filter(Package.package_id == plan.package_id).first()

                # Build result
                result['success'] = True
                result['plan_id'] = str(plan.plan_id)
                result['plan_number'] = str(plan.plan_id)[:8] + '...'  # Use plan_id since no plan_number field
                result['patient_name'] = patient.full_name if patient else 'Unknown'
                result['package_name'] = package.package_name if package else plan.package_name or 'Unknown'
                result['total_sessions'] = plan.total_sessions
                result['completed_sessions'] = plan.completed_sessions
                result['remaining_sessions'] = remaining_sessions
                result['scheduled_sessions'] = len(scheduled_sessions)
                result['pending_installments'] = len(pending_installments)
                result['total_amount'] = float(plan.total_amount)
                result['paid_amount'] = float(plan.paid_amount)
                result['session_value'] = float(session_value)  # Per-session cost (editable by user)
                result['patient_liability'] = float(patient_liability)  # Completed sessions value
                result['net_position'] = float(net_position)  # Paid - Liability
                result['unused_sessions_value'] = float(unused_sessions_value)  # To be reversed
                result['calculated_reversal_value'] = float(calculated_reversal_value)  # AR/GL reversal amount
                result['cash_refund'] = float(cash_refund_amount)  # Actual cash refund to patient

                # Safely get invoice number
                invoice_number = 'N/A'
                if plan.invoice_id:
                    try:
                        invoice_number = plan.invoice.invoice_number if plan.invoice else 'N/A'
                    except Exception:
                        invoice_number = 'N/A'

                result['invoice_number'] = invoice_number
                result['invoice_id'] = str(plan.invoice_id) if plan.invoice_id else None
                result['sessions_to_cancel'] = sessions_to_cancel
                result['installments_to_cancel'] = installments_to_cancel

                logger.info(f"Discontinuation preview for plan {plan_id}:")
                logger.info(f"  Per-session cost: ₹{session_value}")
                logger.info(f"  Completed sessions: {plan.completed_sessions} × ₹{session_value} = ₹{patient_liability}")
                logger.info(f"  Paid amount: ₹{plan.paid_amount}")
                logger.info(f"  Net position (Paid - Liability): ₹{net_position}")
                logger.info(f"  Reversal value (AR/GL): ₹{calculated_reversal_value}")
                logger.info(f"  Cash refund to patient: ₹{cash_refund_amount}")
                logger.info(f"  Sessions to cancel: {len(scheduled_sessions)}")
                logger.info(f"  Installments to cancel: {len(pending_installments)}")

                return result

        except Exception as e:
            logger.error(f"Error previewing discontinuation: {str(e)}", exc_info=True)
            result['error'] = f'Preview error: {str(e)}'
            return result

    def process_discontinuation(
        self,
        plan_id: str,
        discontinuation_reason: str,
        adjustment_amount: Decimal,
        hospital_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process plan discontinuation with user-adjusted refund amount
        Creates credit note and posts AR/GL entries

        Args:
            plan_id: Package payment plan ID
            discontinuation_reason: User-provided reason
            adjustment_amount: User-adjusted refund amount (can be different from calculated)
            hospital_id: Hospital ID
            user_id: User ID performing discontinuation

        Returns:
            {
                'success': bool,
                'plan_id': str,
                'message': str,
                'refund_amount': Decimal,
                'sessions_cancelled': int,
                'installments_cancelled': int,
                'credit_note': {
                    'credit_note_id': str,
                    'credit_note_number': str,
                    'ar_entry_id': str,
                    'gl_transaction_id': str
                }
            }
        """
        result = {
            'success': False,
            'error': None
        }

        try:
            with get_db_session() as session:
                # Get plan
                plan = session.query(PackagePaymentPlan).filter(
                    and_(
                        PackagePaymentPlan.plan_id == plan_id,
                        PackagePaymentPlan.hospital_id == hospital_id
                    )
                ).first()

                if not plan:
                    result['error'] = 'Package payment plan not found'
                    return result

                # Call discontinuation handler with user-adjusted amount
                discontinuation_result = self._handle_discontinuation(
                    plan=plan,
                    discontinuation_reason=discontinuation_reason,
                    db_session=session,
                    hospital_id=hospital_id,
                    user_id=user_id
                )

                if not discontinuation_result['success']:
                    result['error'] = discontinuation_result['message']
                    return result

                # Extract plan values BEFORE calling external services (avoid DetachedInstanceError)
                plan_refund_amount = plan.refund_amount
                plan_branch_id = getattr(plan, 'branch_id', None)
                plan_invoice_id = plan.invoice_id
                plan_patient_id = plan.patient_id
                plan_plan_id = plan.plan_id

                # Override the calculated refund with user-adjusted amount
                if adjustment_amount != plan_refund_amount:
                    logger.info(f"Adjusting refund from ₹{plan_refund_amount} to ₹{adjustment_amount}")
                    plan.refund_amount = adjustment_amount

                    # Re-create credit note with adjusted amount if credit note was created
                    if 'credit_note' in discontinuation_result and adjustment_amount > 0:
                        # Delete the auto-created credit note
                        old_credit_note_id = discontinuation_result['credit_note']['credit_note_id']
                        from app.models.transaction import PatientCreditNote
                        old_cn = session.query(PatientCreditNote).filter(
                            PatientCreditNote.credit_note_id == old_credit_note_id
                        ).first()
                        if old_cn:
                            session.delete(old_cn)
                            session.flush()

                        # Flush plan changes
                        session.flush()

                        # Generate credit note number (pass session to avoid nested session)
                        cn_service = PatientCreditNoteService()
                        credit_note_number = cn_service.generate_credit_note_number(
                            hospital_id,
                            plan_branch_id,
                            session=session
                        )

                        # Create new credit note directly in same session (avoid nested session)
                        import uuid
                        new_credit_note = PatientCreditNote(
                            credit_note_id=uuid.uuid4(),
                            hospital_id=hospital_id,
                            branch_id=plan_branch_id,
                            credit_note_number=credit_note_number,
                            original_invoice_id=plan_invoice_id,
                            plan_id=plan_plan_id,
                            patient_id=plan_patient_id,
                            credit_note_date=date.today(),
                            total_amount=adjustment_amount,
                            reason_code='plan_discontinued',
                            reason_description=discontinuation_reason,
                            status='draft',
                            created_at=datetime.utcnow(),
                            created_by=user_id
                        )

                        session.add(new_credit_note)
                        session.flush()  # Get credit_note_id

                        # Update plan with new credit note reference
                        plan.credit_note_id = new_credit_note.credit_note_id

                        # Store credit note info for GL posting (before commit)
                        discontinuation_result['credit_note_info'] = {
                            'credit_note_id': str(new_credit_note.credit_note_id),
                            'credit_note_number': credit_note_number,
                            'needs_gl_posting': True
                        }

                        logger.info(f"✅ Adjusted credit note created: {credit_note_number} (GL pending)")

                # Build response (inside session context to avoid DetachedInstanceError)
                result['success'] = True
                result['plan_id'] = str(plan.plan_id)
                result['message'] = f'Plan discontinued successfully. Refund of ₹{adjustment_amount:,.2f} processed.'
                result['refund_amount'] = float(adjustment_amount)
                result['sessions_cancelled'] = discontinuation_result['sessions_cancelled']
                result['installments_cancelled'] = discontinuation_result['installments_cancelled']

                if 'credit_note' in discontinuation_result:
                    result['credit_note'] = discontinuation_result['credit_note']

                logger.info(f"✅ Plan {plan_id} discontinuation processed successfully")
                logger.info(f"   Final refund: ₹{adjustment_amount}")
                if 'credit_note' in result:
                    logger.info(f"   Credit note: {result['credit_note']['credit_note_number']}")

                # Post GL entries for credit note BEFORE commit (atomic transaction)
                if discontinuation_result.get('credit_note_info') and discontinuation_result['credit_note_info'].get('needs_gl_posting'):
                    cn_info = discontinuation_result['credit_note_info']
                    logger.info(f"📊 Posting GL entries for credit note {cn_info['credit_note_number']}")

                    from app.services.gl_service import create_patient_credit_note_gl_entries
                    gl_result = create_patient_credit_note_gl_entries(
                        credit_note_id=cn_info['credit_note_id'],
                        hospital_id=hospital_id,
                        current_user_id=user_id,
                        session=session  # ← Pass session for atomic transaction
                    )

                    if not gl_result.get('success'):
                        # GL posting failed - raise exception to trigger automatic rollback
                        error_msg = f"GL posting failed: {gl_result.get('error')}"
                        logger.error(f"❌ {error_msg}")
                        logger.error(f"🔄 Transaction will be rolled back automatically")
                        raise Exception(error_msg)

                    # GL succeeded - update result
                    result['credit_note'] = {
                        'credit_note_id': cn_info['credit_note_id'],
                        'credit_note_number': cn_info['credit_note_number'],
                        'ar_entry_id': gl_result.get('ar_entry_id'),
                        'gl_transaction_id': gl_result.get('gl_transaction_id')
                    }
                    logger.info(f"✅ GL entries posted: AR={gl_result.get('ar_entry_id')}, GL={gl_result.get('gl_transaction_id')}")

                # Commit changes ONLY after GL posting succeeds (atomic transaction)
                logger.info(f"🔄 About to commit discontinuation changes for plan {plan_id}")
                session.commit()
                logger.info(f"✅ Discontinuation changes committed successfully for plan {plan_id}")

            # Invalidate cache (outside session context - cache operations are independent)
            logger.info(f"🧹 Invalidating cache for package_payment_plans")
            invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
            logger.info(f"✅ Cache invalidated successfully")

            logger.info(f"📤 Returning success result for plan {plan_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Error processing discontinuation: {str(e)}", exc_info=True)
            logger.info(f"🔄 SQLAlchemy will automatically rollback all changes (plan, sessions, installments, credit note)")
            # SQLAlchemy automatically rolls back transaction on exception within 'with get_db_session()'
            result['error'] = f'Processing error: {str(e)}'
            return result


# =============================================================================
# MODULE-LEVEL FUNCTIONS (CRUD Convention)
# =============================================================================
# These functions expose the service methods for UniversalCRUDService
# Convention: create_{entity}, update_{entity}, delete_{entity}

def update_package_payment_plan(
    package_payment_plan_id: str,
    package_payment_plan_data: Dict,
    hospital_id: str,
    current_user_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Module-level function for updating package payment plan
    Exposes PackagePaymentService.update_package_payment_plan for CRUD service

    This function is called by UniversalCRUDService when editing package plans.
    It includes custom business logic for:
    - Session replanning (add/remove sessions)
    - Installment replanning (recalculate amounts)
    - Discontinuation handling (refund calculation, cancel sessions/installments)
    """
    service = PackagePaymentService()
    return service.update_package_payment_plan(
        package_payment_plan_id=package_payment_plan_id,
        package_payment_plan_data=package_payment_plan_data,
        hospital_id=hospital_id,
        current_user_id=current_user_id,
        **kwargs
    )
