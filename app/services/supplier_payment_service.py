# File: app/services/supplier_payment_service.py (ENHANCED)

"""
Supplier Payment Service - Complete implementation with all payment-specific logic
Extends UniversalEntityService for generic functionality
Contains only payment-specific business logic
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
from datetime import datetime, date
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
                payments_dict = self._convert_payments_to_dict(payments, session)
                
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
                        query = query.filter(SupplierPayment.payment_amount >= Decimal(str(filters['amount_min'])))
                    except (ValueError, TypeError):
                        pass
                if filters.get('amount_max'):
                    try:
                        query = query.filter(SupplierPayment.payment_amount <= Decimal(str(filters['amount_max'])))
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
            joinedload(SupplierPayment.payment_invoice_links)
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
            query = query.filter(SupplierPayment.payment_amount >= Decimal(str(amount_min)))
            applied_filters.add('amount_min')
        if amount_max:
            query = query.filter(SupplierPayment.payment_amount <= Decimal(str(amount_max)))
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
            'payment_amount': SupplierPayment.payment_amount,
            'workflow_status': SupplierPayment.workflow_status
        }
        
        sort_field = sort_mapping.get(sort_by, SupplierPayment.payment_date)
        
        if sort_order.lower() == 'asc':
            query = query.order_by(asc(sort_field))
        else:
            query = query.order_by(desc(sort_field))
        
        return query
    
    def _convert_payments_to_dict(self, payments: List[SupplierPayment], 
                                session: Session) -> List[Dict]:
        """
        Convert payment entities to dictionaries with all required fields
        """
        payments_dict = []
        
        for payment in payments:
            # Get base dictionary
            payment_dict = get_entity_dict(payment)
            
            # Add supplier information
            if payment.supplier:
                payment_dict['supplier'] = {
                    'supplier_id': str(payment.supplier.supplier_id),
                    'supplier_name': payment.supplier.supplier_name,
                    'contact_person_name': payment.supplier.contact_person_name,
                    'email': payment.supplier.email,
                    'phone': payment.supplier.phone or ''
                }
                payment_dict['supplier_name'] = payment.supplier.supplier_name
            
            # Add invoice information
            payment_dict['linked_invoices'] = []
            payment_dict['total_invoice_amount'] = Decimal('0')
            
            if payment.payment_invoice_links:
                for link in payment.payment_invoice_links:
                    if link.invoice and not link.invoice.is_deleted:
                        invoice_info = {
                            'invoice_id': str(link.invoice.invoice_id),
                            'invoice_no': link.invoice.invoice_no,
                            'invoice_date': link.invoice.invoice_date.isoformat() if link.invoice.invoice_date else None,
                            'total_amount': float(link.invoice.total_amount) if link.invoice.total_amount else 0,
                            'amount_paid': float(link.amount_paid) if link.amount_paid else 0
                        }
                        payment_dict['linked_invoices'].append(invoice_info)
                        payment_dict['total_invoice_amount'] += link.invoice.total_amount or 0
            
            # Format amounts
            payment_dict['payment_amount'] = float(payment_dict.get('payment_amount', 0))
            payment_dict['cash_amount'] = float(payment_dict.get('cash_amount', 0))
            payment_dict['bank_transfer_amount'] = float(payment_dict.get('bank_transfer_amount', 0))
            payment_dict['total_invoice_amount'] = float(payment_dict['total_invoice_amount'])
            
            # Calculate balance
            payment_dict['balance_amount'] = payment_dict['payment_amount'] - payment_dict['total_invoice_amount']
            
            payments_dict.append(payment_dict)
        
        return payments_dict
    
    def _calculate_payment_summary(self, session: Session, hospital_id: uuid.UUID,
                                 branch_id: Optional[uuid.UUID], filters: Dict,
                                 total_count: int) -> Dict:
        """
        Calculate payment-specific summary statistics
        """
        # Start with base query for summary
        base_query = session.query(SupplierPayment).filter(
            SupplierPayment.hospital_id == hospital_id,
            SupplierPayment.is_deleted == False
        )
        
        if branch_id:
            base_query = base_query.filter(SupplierPayment.branch_id == branch_id)
        
        # Total amount
        total_amount = base_query.with_entities(
            func.sum(SupplierPayment.payment_amount)
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
            func.sum(SupplierPayment.payment_amount),
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
                      SupplierPayment.payment_amount)],
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
            Supplier.status == 'active',
            Supplier.is_deleted == False
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
        """Add payment-specific relationships"""
        # Move the supplier/branch/invoice relationship logic here
        if hasattr(entity, 'supplier_id') and entity.supplier_id:
            from app.models.master import Supplier
            supplier = session.query(Supplier).filter_by(supplier_id=entity.supplier_id).first()
            if supplier:
                entity_dict['supplier_name'] = supplier.supplier_name
        return entity_dict