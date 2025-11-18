"""
Consolidated Patient Invoice Service
Phase 3: Tax Compliance - Multi-Invoice Transactions

This service provides read-only access to consolidated invoice groups
(parent invoices with split children). Uses the v_consolidated_patient_invoices view.
"""

import logging
from typing import Dict, Any
from app.engine.universal_entity_service import UniversalEntityService
from app.models.views import ConsolidatedPatientInvoiceView

logger = logging.getLogger(__name__)


class ConsolidatedPatientInvoiceService(UniversalEntityService):
    """
    Service for consolidated patient invoices (Phase 3)

    Features:
    - Read-only view of parent invoices with split children
    - Aggregated totals across all invoices in group
    - Category breakdown (service, medicine, exempt, prescription)
    - Payment status and aging information

    Usage:
        from app.services.consolidated_patient_invoice_service import get_consolidated_invoice_service

        service = get_consolidated_invoice_service()
        result = service.search_data(filters, hospital_id=hospital_id)
    """

    def __init__(self):
        """Initialize service with consolidated invoice view"""
        super().__init__(
            entity_type='consolidated_patient_invoices',
            model_class=ConsolidatedPatientInvoiceView
        )
        logger.info("ConsolidatedPatientInvoiceService initialized")

    # ==========================================================================
    # INHERITED METHODS (From UniversalEntityService)
    # ==========================================================================
    # The following methods are automatically available:
    #
    # - search_data(filters, hospital_id, branch_id=None, page=1, per_page=20)
    #   Returns paginated list of consolidated invoices with filters
    #
    # - get_by_id(item_id, hospital_id, **kwargs)
    #   Returns single consolidated invoice by invoice_id
    #
    # Note: create(), update(), delete() are NOT supported as this is a read-only view
    # ==========================================================================

    def _calculate_summary(self, session, hospital_id, branch_id, filters, total_count, applied_filters=None):
        """
        Override to calculate GST summary from parent invoices
        """
        from sqlalchemy import func

        # Call parent to get base summary
        summary = super()._calculate_summary(session, hospital_id, branch_id, filters, total_count, applied_filters)

        # Get filtered query for GST calculation
        base_query = self._get_base_query(session, hospital_id, branch_id)
        filtered_query, _, _ = self.filter_processor.process_entity_filters(
            self.entity_type,
            filters,
            base_query,
            self.model_class,
            session,
            hospital_id,
            branch_id,
            self.config
        )

        # Calculate total GST (CGST + SGST + IGST from parent invoices)
        total_cgst = filtered_query.with_entities(func.sum(self.model_class.parent_cgst)).scalar() or 0
        total_sgst = filtered_query.with_entities(func.sum(self.model_class.parent_sgst)).scalar() or 0
        total_igst = filtered_query.with_entities(func.sum(self.model_class.parent_igst)).scalar() or 0

        summary['total_gst_sum'] = int(round(float(total_cgst) + float(total_sgst) + float(total_igst)))

        # Convert currency values to integers (no decimal places)
        if 'consolidated_grand_total_sum' in summary:
            summary['consolidated_grand_total_sum'] = int(round(summary['consolidated_grand_total_sum']))
        if 'consolidated_balance_due_sum' in summary:
            summary['consolidated_balance_due_sum'] = int(round(summary['consolidated_balance_due_sum']))

        return summary

    def get_child_invoices(self, item_id: str = None, item: dict = None, **kwargs) -> Dict[str, Any]:
        """
        Get all child invoices for a parent consolidated invoice

        Universal Engine compatible method for custom renderer context function.

        Args:
            item_id: Parent invoice ID (when called with explicit ID)
            item: Parent invoice dict (when called from template context)
            **kwargs: Additional context (hospital_id, parent_invoice_id, etc.)

        Returns:
            Dict with child invoices list
        """
        try:
            from app.services.database_service import get_db_session, get_entity_dict
            from app.models.views import PatientInvoiceView
            import uuid

            # Extract parent invoice ID from parameters
            parent_invoice_id = item_id or (item.get('invoice_id') if isinstance(item, dict) else None) or kwargs.get('parent_invoice_id')

            if not parent_invoice_id:
                logger.warning("No parent invoice ID provided to get_child_invoices")
                return {'success': False, 'children': [], 'count': 0, 'error': 'No parent invoice ID'}

            # Extract hospital ID
            hospital_id = kwargs.get('hospital_id') or (item.get('hospital_id') if isinstance(item, dict) else None)

            if not hospital_id:
                logger.warning("No hospital ID provided to get_child_invoices")
                return {'success': False, 'children': [], 'count': 0, 'error': 'No hospital ID'}

            with get_db_session() as session:
                invoice_uuid = uuid.UUID(parent_invoice_id) if isinstance(parent_invoice_id, str) else parent_invoice_id
                hospital_uuid = uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id

                # Query child invoices
                query = session.query(PatientInvoiceView).filter(
                    PatientInvoiceView.parent_transaction_id == invoice_uuid,
                    PatientInvoiceView.hospital_id == hospital_uuid
                ).order_by(PatientInvoiceView.split_sequence)

                children = query.all()

                if not children:
                    return {'success': True, 'children': [], 'count': 0, 'has_children': False}

                # Convert to dicts
                children_data = [get_entity_dict(child) for child in children]

                return {
                    'success': True,
                    'children': children_data,
                    'count': len(children),
                    'has_children': True
                }

        except Exception as e:
            logger.error(f"Error loading child invoices: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e), 'children': [], 'count': 0, 'has_children': False}

    def get_summary_stats(self, hospital_id: str, branch_id: str = None, **filters) -> Dict[str, Any]:
        """
        Get summary statistics for consolidated invoices

        Args:
            hospital_id: Hospital ID to filter by
            branch_id: Optional branch ID
            **filters: Additional filters (payment_status, date_range, etc.)

        Returns:
            Dict with summary statistics for summary cards:
            {
                'total_count': int,        # Number of consolidated invoice groups
                'total_amount': Decimal,   # Sum of consolidated_grand_total
                'total_gst': Decimal,      # Sum of parent CGST + SGST + IGST
                'total_balance': Decimal   # Sum of consolidated_balance_due
            }
        """
        try:
            # Use search_data to get all records (with high per_page)
            result = self.search_data(
                filters=filters,
                hospital_id=hospital_id,
                branch_id=branch_id,
                page=1,
                per_page=10000  # Get all for stats
            )

            if not result.get('success'):
                return {'error': 'Failed to fetch data for stats'}

            items = result.get('items', [])

            # Calculate statistics
            total_count = len(items)
            total_amount = sum(item.get('consolidated_grand_total', 0) for item in items)
            total_balance = sum(item.get('consolidated_balance_due', 0) for item in items)

            # Calculate total GST (CGST + SGST + IGST from parent invoices)
            total_gst = sum(
                (item.get('parent_cgst', 0) or 0) +
                (item.get('parent_sgst', 0) or 0) +
                (item.get('parent_igst', 0) or 0)
                for item in items
            )

            return {
                'success': True,
                'total_count': total_count,
                'total_amount': float(total_amount),
                'total_gst': float(total_gst),
                'total_balance': float(total_balance)
            }

        except Exception as e:
            logger.error(f"Error calculating summary stats: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================

_service_instance = None


def get_consolidated_invoice_service() -> ConsolidatedPatientInvoiceService:
    """
    Get singleton instance of ConsolidatedPatientInvoiceService

    Returns:
        ConsolidatedPatientInvoiceService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ConsolidatedPatientInvoiceService()
    return _service_instance


# Export for convenient access
consolidated_invoice_service = get_consolidated_invoice_service()
