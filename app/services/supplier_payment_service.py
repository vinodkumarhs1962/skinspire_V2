# File: app/services/supplier_payment_service.py (ENHANCED)

"""
Supplier Payment Service - Complete implementation with all payment-specific logic
Extends UniversalEntityService for generic functionality
Contains only payment-specific business logic
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime, date, timedelta
from flask_login import current_user
from sqlalchemy import or_, and_, desc, asc, func
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from app.models.transaction import SupplierPayment, SupplierInvoice
from app.models.master import Supplier
from app.engine.universal_entity_service import UniversalEntityService
from app.services.database_service import get_db_session, get_entity_dict
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierPaymentService(UniversalEntityService):
    """
    Complete supplier payment service with all unique logic
    Inherits generic functionality from UniversalEntityService
    """
    
    def __init__(self):
        super().__init__('supplier_payments', SupplierPayment)
    
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Override to handle payment-specific search logic
        """
        try:
            # Extract parameters
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            if not hospital_id:
                return self._get_error_result("Hospital ID required")
            
            with get_db_session() as session:
                # Build payment-specific query with joins
                query = self._build_payment_query(session, hospital_id, branch_id)
                
                # Apply payment-specific filters
                query, applied_filters = self._apply_payment_filters(
                    query, filters, session
                )
                
                # Get total count
                total_count = query.count()
                
                # Apply sorting
                query = self._apply_payment_sorting(query, filters)
                
                # Apply pagination
                query = self._apply_pagination(query, page, per_page)
                
                # Execute query
                payments = query.all()
                
                # Convert to dictionaries with payment-specific fields
                payments_dict = self._convert_items_to_dict(payments, session)
                
                logger.info("🔍 [DEBUG SUPPLIER NAME - SERVICE LEVEL]")
                if payments_dict:
                    first_payment = payments_dict[0]
                    logger.info(f"✅ First payment dict keys: {list(first_payment.keys())}")
                    logger.info(f"✅ supplier_name in dict: {'supplier_name' in first_payment}")
                    logger.info(f"✅ supplier_name value: {first_payment.get('supplier_name', 'NOT FOUND')}")
                    logger.info(f"✅ Full payment dict sample: {first_payment}")

                # Calculate payment-specific summary
                summary = self._calculate_payment_summary(
                    session, hospital_id, branch_id, filters, total_count
                )
                
                # Get supplier list for dropdowns
                suppliers = self._get_active_suppliers(session, hospital_id, branch_id)
                
                # Build pagination info
                pagination = self._build_pagination_info(total_count, page, per_page)
                
                # Build result
                return {
                    'items': payments_dict,
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': pagination['total_pages'],
                    'pagination': pagination,
                    'summary': summary,
                    'suppliers': suppliers,
                    'applied_filters': list(applied_filters),
                    'filter_count': len(applied_filters),
                    'success': True,
                    'entity_type': self.entity_type
                }
                
        except Exception as e:
            logger.error(f"Error in payment search: {str(e)}", exc_info=True)
            return self._get_error_result(str(e))

    def search_payments_with_form_integration(self, form_class, **kwargs) -> dict:
        """
        Keep specialized method for backward compatibility
        Used by views that expect this method
        """
        return self._legacy_service.search_payments_with_form_integration(form_class, **kwargs)
    
    def get_payment_breakdown(self, filters: Dict) -> Dict:
        """
        Get payment method breakdown for supplier payments
        Uses EXACT same filters and query logic as main search_data method
        """
        try:
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from app.models.master import Supplier
            from sqlalchemy import func, or_, and_
            from flask_login import current_user
            from decimal import Decimal
            import uuid
            
            # USE THE EXACT FILTERS PASSED TO THIS METHOD - NOT REQUEST.ARGS
            # This ensures we use the same filters as the main query
            logger.info(f"get_payment_breakdown using filters: {filters}")
            
            # Get hospital_id from filters or current_user
            hospital_id = filters.get('hospital_id') or (current_user.hospital_id if current_user else None)
            if not hospital_id:
                logger.error("No hospital_id available for payment breakdown")
                return {'cash_amount': 0.0, 'cheque_amount': 0.0, 'bank_amount': 0.0, 'upi_amount': 0.0}
            
            branch_id = filters.get('branch_id')
            
            with get_db_session() as session:
                # Build query with EXACT same logic as _build_payment_query
                query = session.query(
                    func.sum(SupplierPayment.cash_amount).label('total_cash'),
                    func.sum(SupplierPayment.cheque_amount).label('total_cheque'),
                    func.sum(SupplierPayment.bank_transfer_amount).label('total_bank'),
                    func.sum(SupplierPayment.upi_amount).label('total_upi')
                ).filter(
                    SupplierPayment.hospital_id == hospital_id
                )
                
                # Apply branch filter if provided (same as main query)
                if branch_id:
                    query = query.filter(SupplierPayment.branch_id == branch_id)
                
               
                # Now apply the EXACT SAME filters using the filters dict passed to this method
                # This ensures consistency with the main query
                
                # Date range filter
                if filters.get('start_date'):
                    query = query.filter(SupplierPayment.payment_date >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.filter(SupplierPayment.payment_date <= filters['end_date'])
                
                # Supplier filter
                if filters.get('supplier_id'):
                    query = query.filter(SupplierPayment.supplier_id == filters['supplier_id'])
                
                # Supplier name search
                supplier_search = filters.get('supplier_name_search') or filters.get('search')
                if supplier_search:
                    supplier_subquery = session.query(Supplier.supplier_id).filter(
                        Supplier.hospital_id == hospital_id,
                        Supplier.supplier_name.ilike(f'%{supplier_search}%')
                    ).subquery()
                    query = query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))
                
                # Workflow status filter
                workflow_status = filters.get('workflow_status') or filters.get('status')
                if workflow_status:
                    # Handle both single value and list
                    if isinstance(workflow_status, list):
                        query = query.filter(SupplierPayment.workflow_status.in_(workflow_status))
                    else:
                        query = query.filter(SupplierPayment.workflow_status == workflow_status)
                
                # Reference number filter
                ref_no = filters.get('reference_no') or filters.get('reference_no_search')
                if ref_no:
                    query = query.filter(SupplierPayment.reference_no.ilike(f'%{ref_no}%'))
                
                # Payment method filter (including special handling for mixed payments)
                payment_method = filters.get('payment_method')
                if payment_method:
                    if payment_method == 'bank_transfer_inclusive':
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'cash':
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cash',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cash_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'cheque':
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cheque',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cheque_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'bank_transfer':
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'upi':
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'upi',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.upi_amount > 0
                                )
                            )
                        )
                    else:
                        query = query.filter(SupplierPayment.payment_method == payment_method)
                
                # Amount range filter - using exact field names from _apply_payment_filters
                if filters.get('amount_min'):
                    try:
                        query = query.filter(SupplierPayment.amount >= Decimal(str(filters['amount_min'])))
                    except (ValueError, TypeError):
                        pass
                if filters.get('amount_max'):
                    try:
                        query = query.filter(SupplierPayment.amount <= Decimal(str(filters['amount_max'])))
                    except (ValueError, TypeError):
                        pass
                
                # Invoice ID filter
                if filters.get('invoice_id'):
                    query = query.filter(SupplierPayment.invoice_id == filters['invoice_id'])
                
                # Execute query
                result = query.first()
                
                breakdown_amounts = {
                    'cash_amount': float(result.total_cash or 0),
                    'cheque_amount': float(result.total_cheque or 0),
                    'bank_amount': float(result.total_bank or 0),
                    'upi_amount': float(result.total_upi or 0)
                }
                
                logger.info(f"✅ Payment breakdown calculated with same filters as main query: {breakdown_amounts}")
                return breakdown_amounts
                
        except Exception as e:
            logger.error(f"Error calculating payment breakdown: {str(e)}")
            return {'cash_amount': 0.0, 'cheque_amount': 0.0, 'bank_amount': 0.0, 'upi_amount': 0.0}
        
    def _build_payment_query(self, session: Session, hospital_id: uuid.UUID,
                           branch_id: Optional[uuid.UUID]):
        """
        Build payment-specific query with necessary joins
        """
        # Start with base query including supplier join
        query = session.query(SupplierPayment).join(
            Supplier,
            SupplierPayment.supplier_id == Supplier.supplier_id
        ).options(
            joinedload(SupplierPayment.supplier),
        )
        
        # Apply hospital filter
        query = query.filter(SupplierPayment.hospital_id == hospital_id)
        
        # Apply branch filter if provided
        if branch_id:
            query = query.filter(SupplierPayment.branch_id == branch_id)
               
        return query
    
    def _apply_payment_filters(self, query, filters: Dict, session: Session) -> Tuple:
        """
        Apply payment-specific filters including special cases
        """
        applied_filters = set()
        
        # Supplier filter
        supplier_id = filters.get('supplier_id')
        if supplier_id:
            query = query.filter(SupplierPayment.supplier_id == supplier_id)
            applied_filters.add('supplier_id')
        
        # Supplier name search
        supplier_search = filters.get('supplier_name_search')
        if supplier_search:
            search_term = f"%{supplier_search.lower()}%"
            query = query.filter(
                func.lower(Supplier.supplier_name).like(search_term)
            )
            applied_filters.add('supplier_name_search')
        
        # Reference number search
        ref_search = filters.get('reference_no_search')
        if ref_search:
            search_term = f"%{ref_search.lower()}%"
            query = query.filter(
                func.lower(SupplierPayment.reference_no).like(search_term)
            )
            applied_filters.add('reference_no_search')
        
        # Payment method filter (including special bank_transfer_inclusive)
        if filters.get('bank_transfer_inclusive'):
            # Include both pure bank transfers and mixed payments with bank component
            query = query.filter(
                or_(
                    SupplierPayment.payment_method == 'bank_transfer',
                    and_(
                        SupplierPayment.payment_method == 'mixed',
                        SupplierPayment.bank_transfer_amount > 0
                    )
                )
            )
            applied_filters.add('bank_transfer_inclusive')
        elif filters.get('payment_methods'):
            methods = filters['payment_methods']
            if isinstance(methods, str):
                methods = [methods]
            query = query.filter(SupplierPayment.payment_method.in_(methods))
            applied_filters.add('payment_methods')
        
        # Workflow status filter
        if filters.get('workflow_status'):
            statuses = filters['workflow_status']
            if isinstance(statuses, str):
                statuses = [statuses]
            query = query.filter(SupplierPayment.workflow_status.in_(statuses))
            applied_filters.add('workflow_status')
        
        # Date range filter
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date:
            query = query.filter(SupplierPayment.payment_date >= start_date)
            applied_filters.add('start_date')
        if end_date:
            query = query.filter(SupplierPayment.payment_date <= end_date)
            applied_filters.add('end_date')
        
        # Amount range filter
        amount_min = filters.get('amount_min')
        amount_max = filters.get('amount_max')
        if amount_min:
            query = query.filter(SupplierPayment.amount >= Decimal(str(amount_min)))
            applied_filters.add('amount_min')
        if amount_max:
            query = query.filter(SupplierPayment.amount <= Decimal(str(amount_max)))
            applied_filters.add('amount_max')
        
        return query, applied_filters
    
    def _apply_payment_sorting(self, query, filters: Dict):
        """
        Apply payment-specific sorting
        """
        sort_by = filters.get('sort_by', 'payment_date')
        sort_order = filters.get('sort_order', 'desc')
        
        # Map sort fields
        sort_mapping = {
            'payment_date': SupplierPayment.payment_date,
            'reference_no': SupplierPayment.reference_no,
            'supplier_name': Supplier.supplier_name,
            'amount': SupplierPayment.amount,
            'workflow_status': SupplierPayment.workflow_status
        }
        
        sort_field = sort_mapping.get(sort_by, SupplierPayment.payment_date)
        
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))
        
        return query
    
    def _convert_items_to_dict(self, items: List, session: Session) -> List[Dict]:
        """
        Convert payment entities to dictionaries
        FIXED: Removed incorrect iteration over single invoice
        """
        from decimal import Decimal
        from app.services.database_service import get_entity_dict
        
        items_dict = []
        
        for payment in items:
            payment_dict = get_entity_dict(payment)
            
            # Add supplier information
            if payment.supplier:
                payment_dict['supplier'] = {
                    'supplier_id': str(payment.supplier.supplier_id),
                    'supplier_name': payment.supplier.supplier_name,
                    'contact_person_name': payment.supplier.contact_person_name,
                    'email': payment.supplier.email,
                    'phone': getattr(payment.supplier, 'phone', '')
                }
                payment_dict['supplier_name'] = payment.supplier.supplier_name
            
            # ✅ FIXED: Handle single invoice (no loop needed)
            payment_dict['linked_invoices'] = []
            payment_dict['total_invoice_amount'] = Decimal('0')
            
            if payment.invoice:
                invoice_info = {
                    'invoice_id': str(payment.invoice.invoice_id),
                    'invoice_no': payment.invoice.supplier_invoice_number,
                    'invoice_date': payment.invoice.invoice_date.isoformat() if payment.invoice.invoice_date else None,
                    'total_amount': float(payment.invoice.total_amount) if payment.invoice.total_amount else 0
                }
                payment_dict['linked_invoices'] = [invoice_info]
                payment_dict['total_invoice_amount'] = float(payment.invoice.total_amount or 0)
                payment_dict['supplier_invoice_no'] = payment.invoice.supplier_invoice_number
            else:
                payment_dict['total_invoice_amount'] = 0
            
            # Add branch name if available
            if payment.branch:
                payment_dict['branch_name'] = payment.branch.name
            
            # Add any additional virtual fields
            payment_dict = self._add_virtual_fields_to_payment(payment_dict, payment)
            
            items_dict.append(payment_dict)
        
        return items_dict
    
    def _calculate_payment_summary(self, session: Session, hospital_id: uuid.UUID,
                                 branch_id: Optional[uuid.UUID], filters: Dict,
                                 total_count: int) -> Dict:
        """
        Calculate payment-specific summary statistics
        """
        # Start with base query for summary
        base_query = session.query(SupplierPayment).filter(
            SupplierPayment.hospital_id == hospital_id
        )
        
        if branch_id:
            base_query = base_query.filter(SupplierPayment.branch_id == branch_id)
        
        # Total amount
        total_amount = base_query.with_entities(
            func.sum(SupplierPayment.amount)
        ).scalar() or 0
        
        # Status counts
        status_counts = base_query.with_entities(
            SupplierPayment.workflow_status,
            func.count(SupplierPayment.payment_id)
        ).group_by(SupplierPayment.workflow_status).all()
        
        summary = {
            'total_count': total_count,
            'total_amount': float(total_amount),
            'pending_count': 0,
            'approved_count': 0,
            'completed_count': 0,
            'rejected_count': 0
        }
        
        for status, count in status_counts:
            if status:
                summary[f'{status.lower()}_count'] = count
        
        # Payment method breakdown
        method_amounts = base_query.with_entities(
            SupplierPayment.payment_method,
            func.sum(SupplierPayment.amount),
            func.count(SupplierPayment.payment_id)
        ).group_by(SupplierPayment.payment_method).all()
        
        for method, amount, count in method_amounts:
            if method:
                summary[f'{method}_amount'] = float(amount or 0)
                summary[f'{method}_count'] = count
        
        # Bank transfer amount (including mixed payments)
        bank_amount = base_query.filter(
            or_(
                SupplierPayment.payment_method == 'bank_transfer',
                and_(
                    SupplierPayment.payment_method == 'mixed',
                    SupplierPayment.bank_transfer_amount > 0
                )
            )
        ).with_entities(
            func.sum(
                func.case(
                    [(SupplierPayment.payment_method == 'bank_transfer', 
                      SupplierPayment.amount)],
                    else_=SupplierPayment.bank_transfer_amount
                )
            )
        ).scalar() or 0
        
        summary['bank_transfer_inclusive_amount'] = float(bank_amount)
        
        return summary
    
    def _get_active_suppliers(self, session: Session, hospital_id: uuid.UUID,
                            branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """
        Get list of active suppliers for dropdowns
        """
        query = session.query(Supplier).filter(
            Supplier.hospital_id == hospital_id,
            Supplier.status == 'active'
        )
        
        if branch_id:
            query = query.filter(Supplier.branch_id == branch_id)
        
        query = query.order_by(Supplier.supplier_name)
        
        suppliers = []
        for supplier in query.all():
            suppliers.append({
                'supplier_id': str(supplier.supplier_id),
                'supplier_name': supplier.supplier_name,
                'contact_person': supplier.contact_person_name,
                'email': supplier.email,
                'phone': supplier.phone or ''
            })
        
        return suppliers
    
    def add_relationships(self, entity_dict: Dict, entity, session) -> Dict:
        """Public wrapper for relationship addition - called by categorized processor"""
        return self._add_relationships(entity_dict, entity, session)

    def _add_relationships(self, entity_dict: Dict, entity, session) -> Dict:
        """Add payment-specific relationships"""
        try:
            # Add supplier relationship data - preserve object structure for template
            if hasattr(entity, 'supplier') and entity.supplier:
                # Create supplier object for template compatibility with ENTITY_REFERENCE display
                entity_dict['supplier'] = {
                    'supplier_id': str(entity.supplier.supplier_id),
                    'supplier_name': entity.supplier.supplier_name,
                    'contact_person_name': getattr(entity.supplier, 'contact_person_name', ''),
                    'email': getattr(entity.supplier, 'email', '')
                }
                # Also add flat field for backward compatibility
                entity_dict['supplier_name'] = entity.supplier.supplier_name
                logger.info(f"[DEBUG] Added supplier object and flat fields from relationship: {entity.supplier.supplier_name}")
            elif hasattr(entity, 'supplier_id') and entity.supplier_id:
                # Fallback: Load supplier if not already loaded
                from app.models.master import Supplier
                supplier = session.query(Supplier).filter_by(supplier_id=entity.supplier_id).first()
                if supplier:
                    # Create supplier object for template compatibility
                    entity_dict['supplier'] = {
                        'supplier_id': str(supplier.supplier_id),
                        'supplier_name': supplier.supplier_name,
                        'contact_person_name': getattr(supplier, 'contact_person_name', ''),
                        'email': getattr(supplier, 'email', '')
                    }
                    # Also add flat field for backward compatibility
                    entity_dict['supplier_name'] = supplier.supplier_name
                    logger.info(f"[DEBUG] Added supplier object and flat fields from query: {supplier.supplier_name}")
                else:
                    logger.warning(f"[DEBUG] Supplier not found for supplier_id: {entity.supplier_id}")
            
            # ✅ CORRECTED: Handle SINGLE invoice relationship (NOT payment_invoice_links)
            if hasattr(entity, 'invoice') and entity.invoice:
                # Single invoice relationship
                entity_dict['invoice_no'] = entity.invoice.supplier_invoice_number
                entity_dict['supplier_invoice_no'] = entity.invoice.supplier_invoice_number
                entity_dict['invoice_date'] = entity.invoice.invoice_date.isoformat() if entity.invoice.invoice_date else None
                
                # Add other useful invoice fields that actually exist in your model
                if hasattr(entity.invoice, 'total_amount'):
                    entity_dict['invoice_total'] = float(entity.invoice.total_amount)
                
                if hasattr(entity.invoice, 'payment_status'):
                    entity_dict['invoice_status'] = entity.invoice.payment_status
                
                if hasattr(entity.invoice, 'notes'):
                    entity_dict['invoice_notes'] = entity.invoice.notes
                
                # Create linked_invoices array with single invoice for template compatibility
                entity_dict['linked_invoices'] = [{
                    'invoice_id': str(entity.invoice.invoice_id),
                    'invoice_no': entity.invoice.supplier_invoice_number,
                    'supplier_invoice_no': entity.invoice.supplier_invoice_number,
                    'invoice_date': entity.invoice.invoice_date.isoformat() if entity.invoice.invoice_date else None,
                    'total_amount': float(entity.invoice.total_amount) if entity.invoice.total_amount else 0
                }]
            elif hasattr(entity, 'invoice_id') and entity.invoice_id:
                # ✅ NEW: If invoice not loaded but we have invoice_id, try to load it
                invoice = session.query(SupplierInvoice).filter_by(invoice_id=entity.invoice_id).first()
                if invoice:
                    entity_dict['invoice_no'] = invoice.supplier_invoice_number
                    entity_dict['supplier_invoice_no'] = invoice.supplier_invoice_number
                    entity_dict['invoice_date'] = invoice.invoice_date.isoformat() if invoice.invoice_date else None
                    
                    if hasattr(invoice, 'total_amount'):
                        entity_dict['invoice_total'] = float(invoice.total_amount)
                    
                    entity_dict['linked_invoices'] = [{
                        'invoice_id': str(invoice.invoice_id),
                        'invoice_no': invoice.supplier_invoice_number,
                        'supplier_invoice_no': invoice.supplier_invoice_number,
                        'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
                        'total_amount': float(invoice.total_amount) if invoice.total_amount else 0
                    }]
                else:
                    entity_dict['linked_invoices'] = []
            else:
                # No invoice linked
                entity_dict['linked_invoices'] = []

            # ✅ FIXED: Using correct field name 'name' instead of 'branch_name'
            if hasattr(entity, 'branch') and entity.branch:
                entity_dict['branch_name'] = entity.branch.name
            
            logger.info(f"[DEBUG] Final entity_dict has supplier_name: {'supplier_name' in entity_dict}")
            logger.info(f"[DEBUG] Final entity_dict has supplier object: {'supplier' in entity_dict}")
            
            return entity_dict
            
        except Exception as e:
            logger.error(f"Error adding relationships: {str(e)}")
            return entity_dict
        
    def _get_base_query(self, session: Session, hospital_id: uuid.UUID, 
                   branch_id: Optional[uuid.UUID] = None):
        """
        Override base query to include supplier relationship only
        """
        query = session.query(SupplierPayment).options(
            joinedload(SupplierPayment.supplier)
        ).filter(
            SupplierPayment.hospital_id == hospital_id,
        )
        
        if branch_id:
            query = query.filter(SupplierPayment.branch_id == branch_id)
        
        return query
    
    def get_detail_data(self, item_id: str, hospital_id: uuid.UUID, 
                   branch_id: Optional[uuid.UUID] = None,
                   include_calculations: bool = True) -> Optional[Dict]:
        '''
        Override to add PO and invoice virtual fields for detail view
        This is what Universal Engine actually calls!
        '''
        # Get base data from parent
        data = super().get_detail_data(item_id, hospital_id, branch_id, include_calculations)
        
        if not data or not include_calculations:
            return data
        
        # Extract payment data we need OUTSIDE of session context
        payment_data_for_virtual_fields = None
        
        try:
            # Use session in a limited scope
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == item_id,
                    SupplierPayment.hospital_id == hospital_id
                ).first()
                
                if payment:
                    # Extract only the data we need while session is open
                    payment_data_for_virtual_fields = {
                        'payment_id': str(payment.payment_id),
                        'invoice_id': str(payment.invoice_id) if payment.invoice_id else None,
                        'hospital_id': payment.hospital_id,
                        'branch_id': str(payment.branch_id) if payment.branch_id else None
                    }
            # Session is now closed
            
            # Now add virtual fields OUTSIDE of session context
            if payment_data_for_virtual_fields and 'item' in data and isinstance(data['item'], dict):
                # Create a simple object to pass to _add_detail_virtual_fields
                # This mimics the SupplierPayment object but without session attachment
                class PaymentData:
                    def __init__(self, data_dict):
                        self.payment_id = data_dict['payment_id']
                        self.invoice_id = data_dict['invoice_id']
                        self.hospital_id = data_dict['hospital_id']
                        self.branch_id = data_dict['branch_id']
                
                payment_obj = PaymentData(payment_data_for_virtual_fields)
                
                # Add expensive detail virtual fields to the item
                data['item'] = self._add_detail_virtual_fields(data['item'], payment_obj)
                
                # Debug log to verify
                logger.info(f"[PO_FIX] get_detail_data - Added virtual fields:")
                logger.info(f"  - purchase_order_no: {data['item'].get('purchase_order_no')}")
                logger.info(f"  - po_date: {data['item'].get('po_date')}")
                logger.info(f"  - po_total_amount: {data['item'].get('po_total_amount')}")
                
        except Exception as e:
            logger.error(f"Error adding virtual fields in get_detail_data: {str(e)}")
        
        return data

    def get_po_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get purchase order items related to this payment
        Following the same pattern as get_invoice_items_for_payment
        """
        try:
            po_info = None  # ✅ Initialize as local variable
            # PARAMETER RESOLUTION - matching invoice method pattern
            if item_id:
                # Template calls: item_id IS the payment_id
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                # If item has payment_id field
                payment_id = item['payment_id']
            else:
                return {'items': [], 'has_po': False, 'error': 'No payment ID found'}
                
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id')
                ).first()
                
                if not payment:
                    return {'items': [], 'has_po': False}
                
                po_items = []
                po_summary = {
                    'total_amount': 0,
                    'total_gst': 0
                }
                
                # Access PO through single invoice (no loop needed)
                if payment.invoice_id:
                    invoice = session.query(SupplierInvoice).filter(
                        SupplierInvoice.invoice_id == payment.invoice_id
                    ).first()
                    
                    if invoice and invoice.po_id:
                        from app.models.transaction import PurchaseOrderHeader, PurchaseOrderLine
                        po = session.query(PurchaseOrderHeader).filter(
                            PurchaseOrderHeader.po_id == invoice.po_id
                        ).first()
                        
                        if po:
                            # Store PO info in the main data dict, similar to invoice
                            po_info = {
                                'po_no': po.po_number,
                                'po_number': po.po_number,  # Both for compatibility
                                'po_date': po.po_date,  # Keep as date object for template filter
                                'total_amount': float(po.total_amount or 0),
                                'status': po.status if hasattr(po, 'status') else 'draft'
                            }
                            
                            po_lines = session.query(PurchaseOrderLine).filter(
                                PurchaseOrderLine.po_id == po.po_id
                            ).all()
                            
                            for item in po_lines:
                                po_items.append({
                                    'item_name': item.medicine_name,
                                    'quantity': float(item.units or 0),
                                    'unit_price': float(item.pack_purchase_price or 0),
                                    'gst_amount': float(item.total_gst or 0),
                                    'total_amount': float(item.line_total or 0)
                                })
                                
                                po_summary['total_amount'] += float(item.line_total or 0)
                                po_summary['total_gst'] += float(item.total_gst or 0)
                
                # Return structure matching invoice pattern
                result = {
                    'items': po_items,
                    'summary': po_summary,
                    'has_po': bool(po_items),
                    'currency_symbol': '₹',
                    'po_info': po_info  # ✅ Always include, will be None or dict
                }

                # RIGHT BEFORE THE RETURN STATEMENT, ADD:
                logger.info("[PO_DEBUG_1] get_po_items_for_payment returning:")
                logger.info(f"  - has_po: {bool(po_items)}")
                logger.info(f"  - items count: {len(po_items)}")
                logger.info(f"  - po_info present: {po_info is not None}")
                if po_info:
                    logger.info(f"  - po_info.po_number: {po_info.get('po_number')}")
                    logger.info(f"  - po_info.po_date: {po_info.get('po_date')}")
                    logger.info(f"  - po_info.total_amount: {po_info.get('total_amount')}")

                return result
                
        except Exception as e:
            logger.error(f"Error getting PO items for payment: {str(e)}")
            return {
                'items': [],
                'summary': {},
                'has_po': False,
                'currency_symbol': '₹',
                'error': str(e)
            }

    def get_invoice_items_for_payment(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get invoice line items for this payment
        FIXED: Removed incorrect iteration over single invoice
        """
        # Extract payment_id from universal engine pattern
        payment_id = item_id
        try:
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id')
                ).first()
                
                if not payment:
                    return {'items': [], 'has_invoices': False}
                
                invoice_items = []
                invoice_summary = {
                    'total_amount': 0,
                    'total_discount': 0,
                    'total_gst': 0
                }
                
                # ✅ FIXED: Access invoice directly (no loop needed)
                if payment.invoice_id:
                    invoice = session.query(SupplierInvoice).filter(
                        SupplierInvoice.invoice_id == payment.invoice_id
                    ).first()
                    
                    if invoice:
                        from app.models.transaction import SupplierInvoiceLine
                        invoice_lines = session.query(SupplierInvoiceLine).filter(
                            SupplierInvoiceLine.invoice_id == invoice.invoice_id
                        ).all()
                        
                        for item in invoice_lines:
                            invoice_items.append({
                                # 'invoice_no' REMOVED - not needed for line items
                                'item_name': item.medicine_name,  # This is correct field
                                'batch_no': item.batch_number,
                                'quantity': float(item.units or 0),
                                'unit_price': float(item.pack_purchase_price or 0),
                                'discount_percent': float(item.discount_percent or 0),  # Add percentage
                                'discount_amount': float(item.discount_amount or 0),
                                'gst_rate': float(item.gst_rate or 0),
                                'gst_amount': float(item.total_gst or 0),
                                'total_amount': float(item.line_total or 0)  # Renamed for consistency
                            })
                            
                            invoice_summary['total_amount'] += float(item.line_total or 0)
                            invoice_summary['total_discount'] += float(item.discount_amount or 0)
                            invoice_summary['total_gst'] += float(item.total_gst or 0)
                
                # CRITICAL FIX: Ensure 'items' is always a list, never None
                result = {
                    'items': invoice_items if invoice_items is not None else [],  # <-- FIX: Ensure list
                    'summary': invoice_summary if invoice_summary is not None else {},  # <-- FIX: Ensure dict
                    'has_invoices': bool(invoice_items),
                    'currency_symbol': '₹'
                }
                
                # Debug log to verify structure
                logger.debug(f"Invoice items data: type={type(result)}, has items key={('items' in result)}, items type={type(result.get('items'))}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting invoice items for payment: {str(e)}")
            # CRITICAL: Always return proper structure with 'items' as a list
            return {
                'items': [],  # <-- Must be a list, not None
                'summary': {},  # <-- Must be a dict, not None
                'has_invoices': False,
                'currency_symbol': '₹',
                'error': str(e)
            }

    def get_payment_workflow_timeline(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get workflow timeline for payment approval process
        Returns data for the workflow timeline custom renderer
        """
        try:
            # PARAMETER RESOLUTION for payment workflow
            if item_id:
                payment_id = item_id
            elif item and isinstance(item, dict) and 'payment_id' in item:
                payment_id = item['payment_id']
            else:
                return {'steps': [], 'has_timeline': False, 'error': 'No payment ID found'}
                
            with get_db_session() as session:
                payment = session.query(SupplierPayment).filter(
                    SupplierPayment.payment_id == payment_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id')
                ).first()
                
                if not payment:
                    return {'steps': [], 'current_status': 'unknown', 'has_timeline': False}
                
                # Build workflow timeline with fields that actually exist
                steps = []
                
                # Step 1: Created
                steps.append({
                    'title': 'Payment Created',
                    'status': 'completed',
                    'timestamp': payment.created_at,  # PASS DATETIME OBJECT, NOT STRING
                    'user': payment.created_by,
                    'icon': 'fas fa-plus-circle',
                    'color': 'success',
                    'description': f'Payment of ₹{payment.amount:,.2f} created'
                })
                
                # Step 2: Submitted for Approval (if applicable)
                if payment.submitted_for_approval_at:
                    steps.append({
                        'title': 'Submitted for Approval',
                        'status': 'completed',
                        'timestamp': payment.submitted_for_approval_at,  # DATETIME OBJECT
                        'user': payment.submitted_by or payment.created_by,
                        'icon': 'fas fa-paper-plane',
                        'color': 'info',
                        'description': 'Payment submitted for approval'
                    })
                
                # Step 3: Current Status based on workflow_status
                if payment.workflow_status == 'pending_approval':
                    steps.append({
                        'title': 'Awaiting Approval',
                        'status': 'pending',
                        'timestamp': None,
                        'user': None,
                        'icon': 'fas fa-clock',
                        'color': 'warning',
                        'description': 'Payment is pending approval'
                    })
                    
                elif payment.workflow_status == 'approved' and payment.approved_at:
                    steps.append({
                        'title': 'Payment Approved',
                        'status': 'completed',
                        'timestamp': payment.approved_at,  # DATETIME OBJECT
                        'user': payment.approved_by,
                        'icon': 'fas fa-check-circle',
                        'color': 'success',
                        'description': 'Payment has been approved',
                        'notes': payment.approval_notes
                    })
                    
                elif payment.workflow_status == 'rejected' and payment.rejected_at:
                    steps.append({
                        'title': 'Payment Rejected',
                        'status': 'rejected',
                        'timestamp': payment.rejected_at,  # DATETIME OBJECT
                        'user': payment.rejected_by,
                        'icon': 'fas fa-times-circle',
                        'color': 'danger',
                        'description': 'Payment has been rejected',
                        'notes': payment.rejection_reason
                    })
                
                # Step 4: Completed/Processed
                if payment.workflow_status in ['completed', 'processed']:
                    steps.append({
                        'title': 'Payment Completed',
                        'status': 'completed',
                        'timestamp': payment.updated_at,  # DATETIME OBJECT
                        'user': payment.updated_by,
                        'icon': 'fas fa-flag-checkered',
                        'color': 'success',
                        'description': 'Payment has been completed and processed'
                    })
                
                # Step 5: Reconciliation (if applicable)
                if hasattr(payment, 'reconciliation_status') and payment.reconciliation_status == 'reconciled':
                    reconciled_timestamp = getattr(payment, 'reconciliation_date', payment.updated_at)
                    steps.append({
                        'title': 'Payment Reconciled',
                        'status': 'completed',
                        'timestamp': reconciled_timestamp,  # DATETIME OBJECT
                        'user': getattr(payment, 'reconciled_by', None),
                        'icon': 'fas fa-balance-scale',
                        'color': 'info',
                        'description': 'Payment has been reconciled with bank statement'
                    })
                
                return {
                    'steps': steps,
                    'current_status': payment.workflow_status,
                    'has_timeline': True,
                    'workflow_status': payment.workflow_status,
                    'requires_approval': payment.requires_approval,
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error getting workflow timeline: {str(e)}")
            return {'steps': [], 'has_timeline': False, 'error': str(e)}

    def get_supplier_payment_history_6months(self, item_id: str = None, item: dict = None, **kwargs) -> Dict:
        """
        Get last 6 months payment history for a supplier
        Enhanced version of get_supplier_payment_history
        """
        try:
            # PARAMETER RESOLUTION for payment entity
            if item and isinstance(item, dict) and 'supplier_id' in item:
                # Payment context: extract supplier_id from payment item
                supplier_id = item['supplier_id']
            elif item_id:
                # Direct call: might be supplier_id
                supplier_id = item_id
            else:
                return {'payments': [], 'has_history': False, 'error': 'No supplier ID found'}
            with get_db_session() as session:
                from datetime import datetime, timedelta
                
                # Calculate date 6 months ago
                six_months_ago = datetime.now() - timedelta(days=180)
                
                # Get payments for this supplier
                payments = session.query(SupplierPayment).filter(
                    SupplierPayment.supplier_id == supplier_id,
                    SupplierPayment.hospital_id == kwargs.get('hospital_id'),
                    SupplierPayment.payment_date >= six_months_ago,
                    SupplierPayment.workflow_status.in_(['approved', 'completed'])
                ).order_by(desc(SupplierPayment.payment_date)).all()
                
                payment_history = []
                total_paid = 0
                
                for payment in payments:
                    # ✅ FIXED: Safely get invoice number
                    invoice_no = None
                    if payment.invoice_id:
                        # Load the invoice if we have an invoice_id
                        invoice = session.query(SupplierInvoice).filter(
                            SupplierInvoice.invoice_id == payment.invoice_id
                        ).first()
                        if invoice:
                            invoice_no = invoice.supplier_invoice_number
                    
                    payment_history.append({
                        'payment_id': str(payment.payment_id),
                        'reference_no': payment.reference_no,
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,  # ✅ Format as ISO string
                        'payment_method': payment.payment_method,
                        'amount': float(payment.amount or 0),
                        'workflow_status': payment.workflow_status,
                        'invoice_no': invoice_no  # ✅ Use safely retrieved invoice number
                    })
                    total_paid += float(payment.amount or 0)
                
                # Get supplier details for summary
                supplier = session.query(Supplier).filter(
                    Supplier.supplier_id == supplier_id
                ).first()
                
                return {
                    'payments': payment_history,
                    'summary': {
                        'total_payments': len(payment_history),
                        'total_amount': total_paid,
                        'supplier_name': supplier.supplier_name if supplier else 'Unknown',
                        'period': '6 Months'
                    },
                    'has_history': bool(payment_history),
                    'currency_symbol': '₹'
                }
                
        except Exception as e:
            logger.error(f"Error getting payment history: {str(e)}")
            return {'payments': [], 'has_history': False, 'error': str(e)}
        
    def _add_virtual_fields_to_payment(self, payment_dict: Dict, payment: SupplierPayment) -> Dict:
        """
        Add virtual/calculated fields to payment dictionary
        FIXED: Removed incorrect iteration over single invoice
        """
        from decimal import Decimal
        
        # ✅ FIXED: Calculate total from single invoice (no loop needed)
        total_invoice_amount = Decimal('0')
        if payment.invoice:
            total_invoice_amount = payment.invoice.total_amount or Decimal('0')
        
        payment_dict['total_invoice_amount'] = float(total_invoice_amount)
        payment_dict['submitted_by'] = getattr(payment, 'submitted_by', payment.created_by)
        payment_dict['workflow_updated_at'] = payment.modified_at
        
        return payment_dict
    

    def _add_detail_virtual_fields(self, payment_dict: Dict, payment: Any) -> Dict:
        """
        Add expensive virtual fields only for detail views
        Called separately from the main conversion to avoid slowing down list views
        Note: payment is now a simple object, not a SQLAlchemy model
        """
        
        # ✅ Add invoice summary virtual fields using existing computation
        if payment.invoice_id:
            try:
                # Get invoice summary using existing method
                invoice_data = self.get_invoice_items_for_payment(
                    str(payment.payment_id),
                    hospital_id=payment.hospital_id,
                    branch_id=payment.branch_id
                )
                
                if invoice_data and invoice_data.get('summary'):
                    summary = invoice_data['summary']
                    items = invoice_data.get('items', [])
                    
                    # ✅ Populate virtual fields using existing calculations
                    payment_dict['invoice_total_items'] = len(items)
                    payment_dict['invoice_total_gst'] = summary.get('total_gst', 0)
                    payment_dict['invoice_grand_total'] = summary.get('total_amount', 0)
                else:
                    payment_dict['invoice_total_items'] = 0
                    payment_dict['invoice_total_gst'] = 0
                    payment_dict['invoice_grand_total'] = 0
                    
            except Exception as e:
                logger.error(f"Error calculating invoice summary: {str(e)}")
                payment_dict['invoice_total_items'] = 0
                payment_dict['invoice_total_gst'] = 0
                payment_dict['invoice_grand_total'] = 0
                
            # ✅ Add PO summary virtual fields - EXACT SAME PATTERN AS INVOICE
            try:
                # Call with extracted values - no session conflicts
                po_data = self.get_po_items_for_payment(
                    item_id=str(payment.payment_id),
                    hospital_id=payment.hospital_id,
                    branch_id=payment.branch_id
                )
                
                if po_data and po_data.get('po_info'):
                    po_info = po_data['po_info']
                    
                    # Populate PO virtual fields matching field names exactly
                    payment_dict['purchase_order_no'] = po_info.get('po_number') or po_info.get('po_no', '')
                    payment_dict['po_date'] = po_info.get('po_date')  # Keep as date/string
                    payment_dict['po_total_amount'] = float(po_info.get('total_amount', 0))
                else:
                    payment_dict['purchase_order_no'] = ''
                    payment_dict['po_date'] = None
                    payment_dict['po_total_amount'] = 0
                    
            except Exception as e:
                logger.error(f"Error calculating PO summary: {str(e)}")
                payment_dict['purchase_order_no'] = ''
                payment_dict['po_date'] = None
                payment_dict['po_total_amount'] = 0
        else:
            # No invoice linked
            payment_dict['invoice_total_items'] = 0
            payment_dict['invoice_total_gst'] = 0
            payment_dict['invoice_grand_total'] = 0
            
            # No PO fields either
            payment_dict['purchase_order_no'] = ''
            payment_dict['po_date'] = None
            payment_dict['po_total_amount'] = 0
        
        return payment_dict

    def get_by_id(self, item_id: str, **kwargs) -> Optional[Dict]:
        """Override to add detail virtual fields"""
        # Call parent method first
        result = super().get_by_id(item_id, **kwargs)
        
        if result:
            # Extract payment data we need OUTSIDE of session context
            payment_data_for_virtual_fields = None
            
            try:
                # Use session in a limited scope
                with get_db_session() as session:
                    payment = session.query(SupplierPayment).filter(
                        SupplierPayment.payment_id == item_id,
                        SupplierPayment.hospital_id == kwargs.get('hospital_id')
                    ).first()
                    
                    if payment:
                        # Extract only the data we need while session is open
                        payment_data_for_virtual_fields = {
                            'payment_id': str(payment.payment_id),
                            'invoice_id': str(payment.invoice_id) if payment.invoice_id else None,
                            'hospital_id': payment.hospital_id,
                            'branch_id': str(payment.branch_id) if payment.branch_id else None
                        }
                # Session is now closed
                
                # Now add virtual fields OUTSIDE of session context
                if payment_data_for_virtual_fields:
                    # Create a simple object to pass to _add_detail_virtual_fields
                    # This mimics the SupplierPayment object but without session attachment
                    class PaymentData:
                        def __init__(self, data_dict):
                            self.payment_id = data_dict['payment_id']
                            self.invoice_id = data_dict['invoice_id']
                            self.hospital_id = data_dict['hospital_id']
                            self.branch_id = data_dict['branch_id']
                    
                    payment_obj = PaymentData(payment_data_for_virtual_fields)
                    
                    # Add expensive detail virtual fields
                    result = self._add_detail_virtual_fields(result, payment_obj)
                    
                    # Debug log to verify
                    logger.info(f"[PO_FIX] get_by_id - Added virtual fields:")
                    logger.info(f"  - purchase_order_no: {result.get('purchase_order_no')}")
                    logger.info(f"  - po_date: {result.get('po_date')}")
                    logger.info(f"  - po_total_amount: {result.get('po_total_amount')}")
                    
            except Exception as e:
                logger.error(f"Error adding detail virtual fields in get_by_id: {str(e)}")
        
        return result