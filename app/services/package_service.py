# Package Service: Universal Engine Integration + Business Logic
# File: app/services/package_service.py

"""
Package Service - Complete Implementation
Extends Universal Entity Service with virtual field calculations

Features:
- Package search/autocomplete for dropdown filters
- Virtual field calculations (active_plans_count, total_revenue, avg_completion_rate)
- Basic package queries

Version: 2.0 - Universal Engine Integration
Updated: 2025-11-18
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy import and_, or_, cast, String, func
from sqlalchemy.orm import Session
from app.engine.universal_entity_service import UniversalEntityService
from app.models.master import Package, PackageBOMItem, PackageSessionPlan, Service, Medicine
from app.models.transaction import PackagePaymentPlan
from app.services.database_service import get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)


class PackageService(UniversalEntityService):
    """
    Service for Package entity operations
    Extends Universal Entity Service for consistent autocomplete behavior
    Also handles package_bom_items and package_session_plans
    """

    def __init__(self, entity_type='packages'):
        # Handle multiple entity types
        if entity_type == 'package_bom_items':
            from app.models.master import PackageBOMItem
            super().__init__('package_bom_items', PackageBOMItem)
            self.entity_name = 'package_bom_items'
            self.model = PackageBOMItem
        elif entity_type == 'package_session_plans':
            from app.models.master import PackageSessionPlan
            super().__init__('package_session_plans', PackageSessionPlan)
            self.entity_name = 'package_session_plans'
            self.model = PackageSessionPlan
        else:
            super().__init__('packages', Package)
            self.entity_name = 'packages'
            self.model = Package

    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Override search_data to handle BOM items with package_name
        """
        if self.entity_name == 'package_bom_items':
            # For BOM items, we need to join with Package table to get package_name
            try:
                hospital_id = kwargs.get('hospital_id')
                branch_id = kwargs.get('branch_id')
                page = kwargs.get('page', 1)
                per_page = kwargs.get('per_page', 20)

                from app.services.database_service import get_db_session
                with get_db_session() as session:
                    # Build query with Package join
                    query = session.query(PackageBOMItem).join(Package)

                    # Apply hospital filter
                    if hospital_id:
                        query = query.filter(PackageBOMItem.hospital_id == hospital_id)

                    # Apply branch filter if provided
                    if branch_id and hasattr(PackageBOMItem, 'branch_id'):
                        query = query.filter(PackageBOMItem.branch_id == branch_id)

                    # Soft delete filter - Include deleted items (they will be styled differently in UI)
                    # query = query.filter(PackageBOMItem.deleted_at.is_(None))

                    # Apply additional filters
                    if filters:
                        for key, value in filters.items():
                            if hasattr(PackageBOMItem, key) and value:
                                query = query.filter(getattr(PackageBOMItem, key) == value)

                    # Get total count before pagination
                    total_count = query.count()

                    # Calculate summary counts by status
                    draft_count = session.query(PackageBOMItem).join(Package).filter(
                        PackageBOMItem.hospital_id == hospital_id,
                        PackageBOMItem.deleted_at.is_(None),
                        PackageBOMItem.status == 'draft'
                    ).count()

                    pending_approval_count = session.query(PackageBOMItem).join(Package).filter(
                        PackageBOMItem.hospital_id == hospital_id,
                        PackageBOMItem.deleted_at.is_(None),
                        PackageBOMItem.status == 'pending_approval'
                    ).count()

                    approved_count = session.query(PackageBOMItem).join(Package).filter(
                        PackageBOMItem.hospital_id == hospital_id,
                        PackageBOMItem.deleted_at.is_(None),
                        PackageBOMItem.status == 'approved'
                    ).count()

                    # Apply sorting - by package_name, then item_type
                    query = query.order_by(Package.package_name, PackageBOMItem.item_type)

                    # Apply pagination
                    offset = (page - 1) * per_page
                    items = query.offset(offset).limit(per_page).all()

                    # Convert to dictionaries with package_name
                    items_dict = []
                    for item in items:
                        item_dict = {
                            'bom_item_id': str(item.bom_item_id),
                            'package_id': str(item.package_id),
                            'package_name': item.package.package_name if item.package else '',
                            'package_created_at': item.package.created_at.strftime('%d/%b/%y') if item.package and item.package.created_at else '',
                            'item_type': item.item_type,
                            'item_id': str(item.item_id)[:8] if item.item_id else '',  # Show first 8 chars only
                            'item_name': item.item_name,
                            'quantity': float(item.quantity) if item.quantity else 0,
                            'unit_of_measure': item.unit_of_measure,
                            'supply_method': item.supply_method,
                            'current_price': float(item.current_price) if item.current_price else 0,
                            'line_total': float(item.line_total) if item.line_total else 0,
                            'is_optional': item.is_optional,
                            'display_sequence': item.display_sequence,
                            'notes': item.notes,
                            'status': item.status if hasattr(item, 'status') else 'draft',
                            'approved_by': item.approved_by if hasattr(item, 'approved_by') else None,
                            'approved_at': item.approved_at.isoformat() if hasattr(item, 'approved_at') and item.approved_at else None,
                            'rejection_reason': item.rejection_reason if hasattr(item, 'rejection_reason') else None,
                            'deleted_at': item.deleted_at.isoformat() if hasattr(item, 'deleted_at') and item.deleted_at else None,
                            'created_by': item.created_by if hasattr(item, 'created_by') else None,
                            'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
                            'updated_by': item.updated_by if hasattr(item, 'updated_by') else None,
                            'updated_at': item.updated_at.isoformat() if hasattr(item, 'updated_at') and item.updated_at else None
                        }
                        items_dict.append(item_dict)

                    # Build result
                    return {
                        'items': items_dict,
                        'total': total_count,
                        'pagination': {
                            'total_count': total_count,
                            'page': page,
                            'per_page': per_page,
                            'total_pages': (total_count + per_page - 1) // per_page
                        },
                        'summary': {
                            'total_count': total_count,
                            'draft_count': draft_count,
                            'pending_approval_count': pending_approval_count,
                            'approved_count': approved_count
                        },
                        'success': True
                    }

            except Exception as e:
                logger.error(f"Error in BOM items search: {str(e)}")
                return {
                    'items': [],
                    'total': 0,
                    'pagination': {'total_count': 0},
                    'summary': {},
                    'success': False,
                    'error': str(e)
                }
        else:
            # For packages and session plans, use parent class method
            return super().search_data(filters=filters, **kwargs)

    def list(
        self,
        filters: Dict = None,
        hospital_id: uuid.UUID = None,
        branch_id: uuid.UUID = None,
        page: int = 1,
        per_page: int = 50,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Override list method to handle BOM items with package_name
        """
        if self.entity_name == 'package_bom_items':
            return self.list_package_bom_items(
                filters=filters,
                hospital_id=hospital_id,
                branch_id=branch_id,
                page=page,
                per_page=per_page
            )
        else:
            # Use parent class list method for packages
            return super().list(
                filters=filters,
                hospital_id=hospital_id,
                branch_id=branch_id,
                page=page,
                per_page=per_page,
                **kwargs
            )

    def autocomplete_search(
        self,
        search_term: str,
        hospital_id: uuid.UUID,
        branch_id: Optional[uuid.UUID] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search packages for autocomplete dropdown

        Args:
            search_term: Search query string
            hospital_id: Hospital context
            branch_id: Optional branch filter
            limit: Maximum results to return

        Returns:
            List of package dictionaries with id, label, and package_name
        """
        try:
            with get_db_session() as session:
                # Base query - active packages for this hospital
                query = session.query(Package).filter(
                    and_(
                        Package.hospital_id == hospital_id,
                        Package.is_deleted == False,
                        Package.status == 'active'
                    )
                )

                # Apply search filter if provided
                if search_term:
                    query = query.filter(
                        Package.package_name.ilike(f'%{search_term}%')
                    )

                # Order by name and limit results
                query = query.order_by(Package.package_name).limit(limit)

                # Execute query
                packages = query.all()

                # Format results for autocomplete
                results = []
                for package in packages:
                    results.append({
                        'value': str(package.package_id),  # UUID for filtering
                        'label': package.package_name,  # Display name
                        'package_name': package.package_name,  # For filtering
                        'package_id': str(package.package_id),  # For reference
                        'price': float(package.price) if package.price else 0,
                        'status': package.status
                    })

                logger.info(f"Package autocomplete search: '{search_term}' returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Error in package autocomplete search: {str(e)}")
            return []

    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add virtual/calculated fields to package item

        Virtual fields calculated:
        - active_plans_count: Number of active payment plans for this package
        - total_revenue: Total revenue generated from this package
        - avg_completion_rate: Average completion rate for package payment plans
        - total_bom_items: Count of BOM items
        - bom_cost_estimate: Estimated cost from BOM
        - total_sessions: Count of delivery sessions
        - total_duration_hours: Total session duration

        Args:
            result: Package dict (already serialized)
            item_id: Package ID (primary key)
            **kwargs: Additional parameters (hospital_id, etc.)

        Returns:
            Dict with virtual field calculations added
        """
        try:
            # Get hospital_id from kwargs or from result
            hospital_id = kwargs.get('hospital_id') or result.get('hospital_id')
            if not hospital_id:
                logger.warning(f"No hospital_id provided for package {item_id} virtual calculations")
                return result

            # Get database session
            with get_db_session() as session:
                # Query the package object
                import uuid as uuid_module
                package_uuid = uuid_module.UUID(item_id) if isinstance(item_id, str) else item_id
                hospital_uuid = uuid_module.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

                item = session.query(Package).filter(
                    Package.package_id == package_uuid
                ).filter(
                    Package.hospital_id == hospital_uuid
                ).first()

                if not item:
                    logger.warning(f"Package {item_id} not found for virtual calculations")
                    return result

                virtual_data = {}

                # ==============================================================
                # 1. ACTIVE PLANS COUNT - Count of active payment plans
                # ==============================================================
                try:
                    active_plans_count = session.query(
                        func.count(PackagePaymentPlan.plan_id)
                    ).filter(
                        PackagePaymentPlan.package_id == item.package_id,
                        PackagePaymentPlan.hospital_id == item.hospital_id,
                        PackagePaymentPlan.status == 'active'
                    ).scalar()

                    virtual_data['active_plans_count'] = int(active_plans_count or 0)

                except Exception as e:
                    logger.warning(f"Error calculating active_plans_count for {item.package_id}: {str(e)}")
                    virtual_data['active_plans_count'] = 0

                # ==============================================================
                # 2. TOTAL REVENUE - Sum of all completed payment plan amounts
                # ==============================================================
                try:
                    total_revenue_result = session.query(
                        func.sum(PackagePaymentPlan.total_amount)
                    ).filter(
                        PackagePaymentPlan.package_id == item.package_id,
                        PackagePaymentPlan.hospital_id == item.hospital_id,
                        PackagePaymentPlan.status.in_(['active', 'completed'])
                    ).scalar()

                    total_revenue = float(total_revenue_result or 0)
                    virtual_data['total_revenue'] = round(total_revenue, 2)

                except Exception as e:
                    logger.warning(f"Error calculating total_revenue for {item.package_id}: {str(e)}")
                    virtual_data['total_revenue'] = 0

                # ==============================================================
                # 3. AVG COMPLETION RATE - Average completion percentage
                # ==============================================================
                try:
                    # Get all plans for this package with their completion status
                    plans = session.query(
                        PackagePaymentPlan.plan_id,
                        PackagePaymentPlan.status
                    ).filter(
                        PackagePaymentPlan.package_id == item.package_id,
                        PackagePaymentPlan.hospital_id == item.hospital_id
                    ).all()

                    if plans and len(plans) > 0:
                        completed_count = sum(1 for plan in plans if plan[1] == 'completed')
                        avg_completion_rate = (completed_count / len(plans)) * 100
                        virtual_data['avg_completion_rate'] = round(avg_completion_rate, 2)
                    else:
                        virtual_data['avg_completion_rate'] = 0

                except Exception as e:
                    logger.warning(f"Error calculating avg_completion_rate for {item.package_id}: {str(e)}")
                    virtual_data['avg_completion_rate'] = 0

                # ==============================================================
                # 4. BOM METRICS - Bill of Materials calculations
                # ==============================================================
                try:
                    # Get full BOM items data
                    bom_items = self.get_package_bom_items(str(item.package_id), session)
                    virtual_data['bom_items'] = bom_items
                    virtual_data['total_bom_items'] = len(bom_items)

                    # BOM cost estimate
                    bom_cost = self._calculate_bom_cost(item, session)
                    virtual_data['bom_cost_estimate'] = round(bom_cost, 2)

                    # Add summary for BOM display
                    virtual_data['summary'] = {
                        'total_cost': round(bom_cost, 2),
                        'total_items': len(bom_items)
                    }

                except Exception as e:
                    logger.warning(f"Error calculating BOM metrics for {item.package_id}: {str(e)}")
                    virtual_data['bom_items'] = []
                    virtual_data['total_bom_items'] = 0
                    virtual_data['bom_cost_estimate'] = 0
                    virtual_data['summary'] = {'total_cost': 0, 'total_items': 0}

                # ==============================================================
                # 5. SESSION PLAN METRICS - Delivery session calculations
                # ==============================================================
                try:
                    # Get full session plan data
                    session_plans = self.get_package_session_plans(str(item.package_id), session)
                    virtual_data['session_plans'] = session_plans
                    virtual_data['total_sessions'] = len(session_plans)

                    # Total duration in hours
                    total_minutes = sum(plan.get('estimated_duration_minutes', 0) or 0 for plan in session_plans)
                    total_hours = float(total_minutes) / 60.0
                    virtual_data['total_duration_hours'] = round(total_hours, 2)

                    # Update or create summary with session plan data
                    if 'summary' not in virtual_data:
                        virtual_data['summary'] = {}
                    virtual_data['summary']['total_duration_hours'] = round(total_hours, 2)
                    virtual_data['summary']['total_sessions'] = len(session_plans)

                except Exception as e:
                    logger.warning(f"Error calculating session metrics for {item.package_id}: {str(e)}")
                    virtual_data['session_plans'] = []
                    virtual_data['total_sessions'] = 0
                    virtual_data['total_duration_hours'] = 0
                    if 'summary' not in virtual_data:
                        virtual_data['summary'] = {}
                    virtual_data['summary']['total_duration_hours'] = 0
                    virtual_data['summary']['total_sessions'] = 0

                logger.debug(f"Virtual calculations for package {item_id}: {virtual_data}")

                # Update result dict with virtual data
                result.update(virtual_data)
                return result

        except Exception as e:
            logger.error(f"Error in _add_virtual_calculations for package {item_id}: {str(e)}")
            # Return result with default values on error
            result.update({
                'active_plans_count': 0,
                'total_revenue': 0,
                'avg_completion_rate': 0,
                'bom_items': [],
                'total_bom_items': 0,
                'bom_cost_estimate': 0,
                'session_plans': [],
                'total_sessions': 0,
                'total_duration_hours': 0
            })
            return result

    # =========================================================================
    # BOM METHODS - Bill of Materials Operations
    # =========================================================================

    def get_package_bom_items(self, package_id: str, session: Session) -> List[Dict]:
        """
        Get all BOM items for a package with resolved item details

        Args:
            package_id: Package UUID
            session: Database session

        Returns:
            List of BOM item dicts with resolved details
        """
        try:
            import uuid as uuid_module
            pkg_uuid = uuid_module.UUID(package_id) if isinstance(package_id, str) else package_id

            bom_items = session.query(PackageBOMItem).filter(
                PackageBOMItem.package_id == pkg_uuid,
                PackageBOMItem.is_deleted == False
            ).order_by(PackageBOMItem.display_sequence).all()

            result = []
            for item in bom_items:
                item_dict = {
                    'bom_item_id': str(item.bom_item_id),
                    'item_type': item.item_type,
                    'item_name': item.item_name,
                    'quantity': float(item.quantity or 0),
                    'unit_of_measure': item.unit_of_measure,
                    'supply_method': item.supply_method,
                    'current_price': float(item.current_price or 0),
                    'line_total': float(item.line_total or 0),
                    'is_optional': item.is_optional,
                    'notes': item.notes,
                    'display_sequence': item.display_sequence
                }
                result.append(item_dict)

            return result

        except Exception as e:
            logger.error(f"Error getting BOM items for package {package_id}: {str(e)}")
            return []

    def get_package_session_plans(self, package_id: str, session: Session) -> List[Dict]:
        """
        Get all session plans for a package

        Args:
            package_id: Package UUID
            session: Database session

        Returns:
            List of session plan dicts
        """
        try:
            import uuid as uuid_module
            pkg_uuid = uuid_module.UUID(package_id) if isinstance(package_id, str) else package_id

            session_plans = session.query(PackageSessionPlan).filter(
                PackageSessionPlan.package_id == pkg_uuid,
                PackageSessionPlan.is_deleted == False
            ).order_by(PackageSessionPlan.session_number).all()

            result = []
            for plan in session_plans:
                plan_dict = {
                    'session_plan_id': str(plan.session_plan_id),
                    'session_number': plan.session_number,
                    'session_name': plan.session_name,
                    'session_description': plan.session_description,
                    'estimated_duration_minutes': plan.estimated_duration_minutes,
                    'recommended_gap_days': plan.recommended_gap_days,
                    'is_mandatory': plan.is_mandatory,
                    'resource_requirements': plan.resource_requirements,
                    'scheduling_notes': plan.scheduling_notes,
                    'prerequisites': plan.prerequisites,
                    'display_sequence': plan.display_sequence
                }
                result.append(plan_dict)

            return result

        except Exception as e:
            logger.error(f"Error getting session plans for package {package_id}: {str(e)}")
            return []

    def _calculate_bom_cost(self, package: Package, session: Session) -> float:
        """
        Calculate total cost estimate from BOM items

        Resolves polymorphic item references to get current prices:
        - service -> Service.price
        - medicine -> Medicine.mrp or Medicine.selling_price
        - product -> (future implementation)
        - consumable -> (future implementation)

        Args:
            package: Package instance
            session: Database session

        Returns:
            Total estimated cost from BOM
        """
        try:
            total_cost = 0.0

            # Get all BOM items for this package
            bom_items = session.query(PackageBOMItem).filter(
                PackageBOMItem.package_id == package.package_id,
                PackageBOMItem.hospital_id == package.hospital_id,
                PackageBOMItem.is_deleted == False
            ).all()

            for bom_item in bom_items:
                item_price = 0.0
                quantity = float(bom_item.quantity or 0)

                # Resolve polymorphic reference
                if bom_item.item_type == 'service':
                    # Get service price
                    service = session.query(Service).filter(
                        Service.service_id == bom_item.item_id,
                        Service.is_deleted == False
                    ).first()
                    if service and service.price:
                        item_price = float(service.price)

                elif bom_item.item_type == 'medicine':
                    # Get medicine price (prefer selling_price over mrp)
                    medicine = session.query(Medicine).filter(
                        Medicine.medicine_id == bom_item.item_id,
                        Medicine.is_deleted == False
                    ).first()
                    if medicine:
                        if medicine.selling_price:
                            item_price = float(medicine.selling_price)
                        elif medicine.mrp:
                            item_price = float(medicine.mrp)

                # Add to total cost
                total_cost += (item_price * quantity)

            return total_cost

        except Exception as e:
            logger.error(f"Error calculating BOM cost for package {package.package_id}: {str(e)}")
            return 0.0

    def get_package_bom_details(
        self,
        item_id: str,
        item: Dict = None,
        hospital_id: str = None,
        branch_id: str = None
    ) -> Dict[str, Any]:
        """
        Get complete BOM breakdown with session plan - used by detail view template

        Args:
            item_id: Package ID
            item: Package item dict (optional)
            hospital_id: Hospital ID
            branch_id: Branch ID

        Returns:
            {
                'package_id': str,
                'package_name': str,
                'bom_items': [formatted BOM items],
                'session_plan': [formatted session plans],
                'summary': {
                    'total_items': int,
                    'total_sessions': int,
                    'total_cost': float,
                    'total_duration_hours': float
                }
            }
        """
        try:
            # Convert string IDs to UUID
            package_uuid = uuid.UUID(item_id) if isinstance(item_id, str) else item_id

            # Get hospital_id from item if not provided
            if not hospital_id and item:
                hospital_id = item.get('hospital_id')

            if not hospital_id:
                logger.warning(f"No hospital_id provided for package BOM details {item_id}")
                return {'error': 'hospital_id required', 'bom_items': [], 'session_plan': [], 'summary': {}}

            hospital_uuid = uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

            with get_db_session() as session:
                # Get package
                package = session.query(Package).filter(
                    Package.package_id == package_uuid,
                    Package.hospital_id == hospital_uuid,
                    Package.is_deleted == False
                ).first()

                if not package:
                    return {
                        'error': 'Package not found',
                        'bom_items': [],
                        'session_plan': [],
                        'summary': {}
                    }

                # Get BOM items
                bom_items = session.query(PackageBOMItem).filter(
                    PackageBOMItem.package_id == package_uuid,
                    PackageBOMItem.hospital_id == hospital_uuid,
                    PackageBOMItem.is_deleted == False
                ).order_by(PackageBOMItem.display_sequence).all()

                # Get session plans
                session_plans = session.query(PackageSessionPlan).filter(
                    PackageSessionPlan.package_id == package_uuid,
                    PackageSessionPlan.hospital_id == hospital_uuid,
                    PackageSessionPlan.is_deleted == False
                ).order_by(PackageSessionPlan.session_number).all()

                # Format BOM items
                formatted_bom = [self._format_bom_item(item, session) for item in bom_items]

                # Format session plans
                formatted_sessions = [self._format_session_plan(plan) for plan in session_plans]

                # Calculate summary
                total_cost = self._calculate_bom_cost(package, session)
                total_duration_minutes = sum(
                    plan.estimated_duration_minutes or 0
                    for plan in session_plans
                )

                return {
                    'package_id': str(package_uuid),
                    'package_name': package.package_name,
                    'bom_items': formatted_bom,
                    'session_plan': formatted_sessions,  # Keep for backward compatibility
                    'session_plans': formatted_sessions,  # Add plural version for template
                    'summary': {
                        'total_items': len(bom_items),
                        'total_sessions': len(session_plans),
                        'total_cost': round(total_cost, 2),
                        'total_duration_hours': round(total_duration_minutes / 60.0, 2)
                    }
                }

        except Exception as e:
            logger.error(f"Error getting BOM details for package {item_id}: {str(e)}")
            return {
                'error': str(e),
                'bom_items': [],
                'session_plan': [],
                'summary': {}
            }

    def _format_bom_item(self, bom_item: PackageBOMItem, session: Session) -> Dict[str, Any]:
        """
        Format BOM item with resolved item details

        Args:
            bom_item: PackageBOMItem instance
            session: Database session

        Returns:
            Formatted BOM item dict with resolved details
        """
        try:
            # Base item data
            item_data = {
                'bom_item_id': str(bom_item.bom_item_id),
                'item_type': bom_item.item_type,
                'item_id': str(bom_item.item_id),
                'item_name': bom_item.item_name,
                'quantity': float(bom_item.quantity) if bom_item.quantity else 0,
                'unit_of_measure': bom_item.unit_of_measure,
                'supply_method': bom_item.supply_method,
                'is_optional': bom_item.is_optional,
                'notes': bom_item.notes,
                'resolved_item': None,
                'current_price': 0.0
            }

            # Resolve polymorphic reference to get current details
            if bom_item.item_type == 'service':
                service = session.query(Service).filter(
                    Service.service_id == bom_item.item_id,
                    Service.is_deleted == False
                ).first()
                if service:
                    item_data['resolved_item'] = {
                        'name': service.service_name,
                        'code': service.code,
                        'service_type': service.service_type if hasattr(service, 'service_type') else None
                    }
                    item_data['current_price'] = float(service.price) if service.price else 0.0

            elif bom_item.item_type == 'medicine':
                medicine = session.query(Medicine).filter(
                    Medicine.medicine_id == bom_item.item_id,
                    Medicine.is_deleted == False
                ).first()
                if medicine:
                    item_data['resolved_item'] = {
                        'name': medicine.medicine_name,
                        'generic_name': medicine.generic_name,
                        'manufacturer_id': str(medicine.manufacturer_id) if medicine.manufacturer_id else None
                    }
                    # Use selling_price if available, else mrp
                    if hasattr(medicine, 'selling_price') and medicine.selling_price:
                        item_data['current_price'] = float(medicine.selling_price)
                    elif hasattr(medicine, 'mrp') and medicine.mrp:
                        item_data['current_price'] = float(medicine.mrp)

            # Calculate line total
            item_data['line_total'] = round(
                item_data['current_price'] * item_data['quantity'],
                2
            )

            return item_data

        except Exception as e:
            logger.error(f"Error formatting BOM item {bom_item.bom_item_id}: {str(e)}")
            return {
                'bom_item_id': str(bom_item.bom_item_id),
                'item_type': bom_item.item_type,
                'error': str(e)
            }

    def _format_session_plan(self, session_plan: PackageSessionPlan) -> Dict[str, Any]:
        """
        Format session plan with resource requirements

        Args:
            session_plan: PackageSessionPlan instance

        Returns:
            Formatted session plan dict
        """
        try:
            return {
                'session_plan_id': str(session_plan.session_plan_id),
                'session_number': session_plan.session_number,
                'session_name': session_plan.session_name,
                'session_description': session_plan.session_description,
                'estimated_duration_minutes': session_plan.estimated_duration_minutes,
                'estimated_duration_hours': round(
                    (session_plan.estimated_duration_minutes or 0) / 60.0,
                    2
                ),
                'resource_requirements': session_plan.resource_requirements or [],
                'recommended_gap_days': session_plan.recommended_gap_days,
                'is_mandatory': session_plan.is_mandatory,
                'scheduling_notes': session_plan.scheduling_notes,
                'prerequisites': session_plan.prerequisites
            }

        except Exception as e:
            logger.error(f"Error formatting session plan {session_plan.session_plan_id}: {str(e)}")
            return {
                'session_plan_id': str(session_plan.session_plan_id),
                'error': str(e)
            }

    def list_package_bom_items(
        self,
        filters: Dict = None,
        hospital_id: uuid.UUID = None,
        branch_id: uuid.UUID = None,
        page: int = 1,
        per_page: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List Package BOM Items with package_name populated
        Used by Universal Engine list view

        Args:
            filters: Filter criteria
            hospital_id: Hospital UUID
            branch_id: Branch UUID (optional)
            page: Page number
            per_page: Items per page

        Returns:
            List of BOM item dictionaries with package_name
        """
        with get_db_session() as session:
            query = session.query(PackageBOMItem).join(Package)

            # Apply hospital filter
            if hospital_id:
                query = query.filter(PackageBOMItem.hospital_id == hospital_id)

            # Apply additional filters
            if filters:
                for key, value in filters.items():
                    if hasattr(PackageBOMItem, key) and value:
                        query = query.filter(getattr(PackageBOMItem, key) == value)

            # Order by package_name, then item_type (as configured)
            query = query.order_by(Package.package_name, PackageBOMItem.item_type)

            # Pagination
            offset = (page - 1) * per_page
            bom_items = query.offset(offset).limit(per_page).all()

            # Convert to dictionaries and add package_name
            result = []
            for item in bom_items:
                item_dict = {
                    'bom_item_id': str(item.bom_item_id),
                    'package_id': str(item.package_id),
                    'package_name': item.package.package_name if item.package else '',  # Virtual field
                    'item_type': item.item_type,
                    'item_id': str(item.item_id),
                    'item_name': item.item_name,
                    'quantity': float(item.quantity) if item.quantity else 0,
                    'unit_of_measure': item.unit_of_measure,
                    'supply_method': item.supply_method,
                    'current_price': float(item.current_price) if item.current_price else 0,
                    'line_total': float(item.line_total) if item.line_total else 0,
                    'is_optional': item.is_optional,
                    'display_sequence': item.display_sequence,
                    'notes': item.notes,
                    # Workflow fields
                    'status': item.status if hasattr(item, 'status') else 'draft',
                    'approved_by': item.approved_by if hasattr(item, 'approved_by') else None,
                    'approved_at': item.approved_at.isoformat() if hasattr(item, 'approved_at') and item.approved_at else None,
                    'rejection_reason': item.rejection_reason if hasattr(item, 'rejection_reason') else None,
                    # Soft delete
                    'deleted_at': item.deleted_at.isoformat() if hasattr(item, 'deleted_at') and item.deleted_at else None,
                    # Audit fields
                    'created_by': item.created_by if hasattr(item, 'created_by') else None,
                    'created_at': item.created_at.isoformat() if hasattr(item, 'created_at') and item.created_at else None,
                    'updated_by': item.updated_by if hasattr(item, 'updated_by') else None,
                    'updated_at': item.updated_at.isoformat() if hasattr(item, 'updated_at') and item.updated_at else None
                }
                result.append(item_dict)

            return result
