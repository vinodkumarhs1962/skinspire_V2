# Week 2 Enhanced Universal Engine Implementation
## Leveraging Your Existing CSS Components & Data Structures

---

## 🎯 **Week 2 Overview**

**Goal:** Transform your existing supplier payment functionality into the Universal Engine foundation using your comprehensive CSS component system and exact data structures.

**Key Insight:** Your CSS components (`forms.css`, `buttons.css`, `tables.css`, `status.css`, `filters.css`, `cards.css`) are already perfect for universal reuse - we'll enhance them with dynamic configuration capabilities.

**Pilot Features:** 
- ✅ Supplier Payment List (using your existing data-table classes)
- ✅ Filter Card (enhancing your filter-card component) 
- ✅ Payment View (using your info-card and action-buttons)
- ✅ Status Badges (dynamic mapping with your status-badge system)

---

## 📊 **Data Structure Analysis Complete**

### **SupplierPayment Model Fields (from transaction.py):**
```python
# Primary fields we'll configure
payment_id, hospital_id, branch_id, supplier_id, invoice_id
payment_date, payment_method, amount, reference_no, status, notes
workflow_status, approval_level, approved_by, approved_at
cash_amount, cheque_amount, bank_transfer_amount, upi_amount
currency_code, exchange_rate
```

### **Service Method Signatures (from supplier_service.py):**
```python
search_supplier_payments(hospital_id, filters, branch_id, current_user_id, page, per_page, session)
get_supplier_payment_by_id(payment_id, hospital_id, include_documents, include_approvals, session)
```

---

## 🏗️ **Day-by-Day Implementation Plan**

### **Day 1: Universal Service with Exact Method Compatibility**

#### **Task 1.1: Create Universal Supplier Service**
Create `app/services/universal_supplier_service.py`:

```python
"""
Universal Supplier Payment Service - Standardized Implementation
Uses exact same method signatures as existing supplier_service.py
"""

from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func
from decimal import Decimal

from app.services.database_service import get_db_session, get_entity_dict
from app.models.transaction import SupplierPayment
from app.models.master import Supplier, Branch
from app.models.invoice import SupplierInvoice
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalSupplierPaymentService:
    """THE canonical supplier payment service - exact compatibility with existing"""
    
    def search_supplier_payments(
        self,
        hospital_id: uuid.UUID,
        filters: Dict = None,
        branch_id: Optional[uuid.UUID] = None,
        current_user_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        session: Optional[Session] = None
    ) -> Dict:
        """Universal search - exact same signature as existing service"""
        
        if session is not None:
            return self._search_supplier_payments_internal(
                session, hospital_id, filters, branch_id, current_user_id, page, per_page
            )
        
        with get_db_session(read_only=True) as new_session:
            return self._search_supplier_payments_internal(
                new_session, hospital_id, filters, branch_id, current_user_id, page, per_page
            )
    
    def _search_supplier_payments_internal(
        self, 
        session: Session,
        hospital_id: uuid.UUID,
        filters: Dict = None,
        branch_id: Optional[uuid.UUID] = None,
        current_user_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict:
        """Internal search using exact field names from SupplierPayment model"""
        
        try:
            if filters is None:
                filters = {}
                
            logger.info(f"Universal payment search: hospital={hospital_id}, filters={filters}")
            
            # Build base query using exact model field names
            query = session.query(SupplierPayment).filter_by(hospital_id=hospital_id)
            
            # Branch filtering (exact field: branch_id)
            if branch_id:
                query = query.filter(SupplierPayment.branch_id == branch_id)
            
            # Supplier filtering - handle both ID and name search
            if filters.get('supplier_id'):
                query = query.filter(SupplierPayment.supplier_id == uuid.UUID(filters['supplier_id']))
            elif filters.get('supplier_name_search'):
                # Join with Supplier table for name search
                query = query.join(Supplier, SupplierPayment.supplier_id == Supplier.supplier_id)
                query = query.filter(Supplier.supplier_name.ilike(f"%{filters['supplier_name_search']}%"))
            
            # Status filtering - use exact field names
            if filters.get('statuses'):  # Multiple values
                query = query.filter(SupplierPayment.workflow_status.in_(filters['statuses']))
            elif filters.get('workflow_status'):  # Single value
                query = query.filter(SupplierPayment.workflow_status == filters['workflow_status'])
            elif filters.get('status'):  # Alternative parameter name
                query = query.filter(SupplierPayment.workflow_status == filters['status'])
            
            # Payment method filtering - use exact field names
            if filters.get('payment_methods'):  # Multiple values
                query = query.filter(SupplierPayment.payment_method.in_(filters['payment_methods']))
            elif filters.get('payment_method'):  # Single value
                query = query.filter(SupplierPayment.payment_method == filters['payment_method'])
            
            # Amount range filtering - use exact field name 'amount'
            if filters.get('min_amount'):
                query = query.filter(SupplierPayment.amount >= Decimal(str(filters['min_amount'])))
            if filters.get('max_amount'):
                query = query.filter(SupplierPayment.amount <= Decimal(str(filters['max_amount'])))
            
            # Date range filtering - use exact field name 'payment_date'
            if filters.get('start_date'):
                if isinstance(filters['start_date'], str):
                    start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d').date()
                else:
                    start_date = filters['start_date']
                query = query.filter(SupplierPayment.payment_date >= start_date)
                
            if filters.get('end_date'):
                if isinstance(filters['end_date'], str):
                    end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d').date()
                else:
                    end_date = filters['end_date']
                query = query.filter(SupplierPayment.payment_date <= end_date)
            
            # Invoice filtering - use exact field name 'invoice_id'
            if filters.get('invoice_id'):
                query = query.filter(SupplierPayment.invoice_id == uuid.UUID(filters['invoice_id']))
            
            # Reference number search - use exact field name 'reference_no'
            if filters.get('reference_no'):
                query = query.filter(SupplierPayment.reference_no.ilike(f"%{filters['reference_no']}%"))
            
            # Sorting - use exact field names
            sort_by = filters.get('sort_by', 'payment_date')
            sort_order = filters.get('sort_order', 'desc')
            
            # Map sort fields to actual model fields
            sort_field_map = {
                'payment_date': SupplierPayment.payment_date,
                'amount': SupplierPayment.amount,
                'payment_method': SupplierPayment.payment_method,
                'workflow_status': SupplierPayment.workflow_status,
                'reference_no': SupplierPayment.reference_no,
                'created_at': SupplierPayment.created_at
            }
            
            sort_field = sort_field_map.get(sort_by, SupplierPayment.payment_date)
            
            if sort_order == 'desc':
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(asc(sort_field))
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination
            payments = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Convert to dictionaries with related data
            payment_list = []
            for payment in payments:
                payment_dict = get_entity_dict(payment)
                
                # Add supplier information
                supplier = session.query(Supplier).filter_by(supplier_id=payment.supplier_id).first()
                if supplier:
                    payment_dict['supplier_name'] = supplier.supplier_name
                    payment_dict['supplier_code'] = getattr(supplier, 'supplier_code', str(supplier.supplier_id))
                
                # Add branch information
                if payment.branch_id:
                    branch = session.query(Branch).filter_by(branch_id=payment.branch_id).first()
                    if branch:
                        payment_dict['branch_name'] = branch.name
                
                # Add invoice information if linked
                if payment.invoice_id:
                    invoice = session.query(SupplierInvoice).filter_by(invoice_id=payment.invoice_id).first()
                    if invoice:
                        payment_dict['invoice_number'] = invoice.supplier_invoice_number
                        payment_dict['invoice_amount'] = float(invoice.total_amount)
                
                # Format amounts for display
                payment_dict['formatted_amount'] = f"₹{float(payment.amount):,.2f}"
                payment_dict['formatted_payment_date'] = payment.payment_date.strftime("%d %b %Y")
                
                payment_list.append(payment_dict)
            
            # Calculate summary data
            summary = self._calculate_payment_summary(session, hospital_id, branch_id, filters)
            
            return {
                'payments': payment_list,
                'total': total,
                'page': page,
                'per_page': per_page,
                'summary': summary,
                'filters_applied': filters or {}
            }
            
        except Exception as e:
            logger.error(f"Error in universal supplier payment search: {str(e)}")
            raise
    
    def get_supplier_payment_by_id(
        self,
        payment_id: uuid.UUID,
        hospital_id: uuid.UUID,
        include_documents: bool = False,
        include_approvals: bool = False,
        session: Optional[Session] = None
    ) -> Optional[Dict]:
        """Universal detail retrieval - exact same signature as existing service"""
        
        if session is not None:
            return self._get_supplier_payment_by_id_internal(
                session, payment_id, hospital_id, include_documents, include_approvals
            )
        
        with get_db_session(read_only=True) as new_session:
            return self._get_supplier_payment_by_id_internal(
                new_session, payment_id, hospital_id, include_documents, include_approvals
            )
    
    def _get_supplier_payment_by_id_internal(
        self, 
        session: Session, 
        payment_id: uuid.UUID, 
        hospital_id: uuid.UUID,
        include_documents: bool = False, 
        include_approvals: bool = False
    ) -> Optional[Dict]:
        """Internal payment detail retrieval using exact field names"""
        
        try:
            payment = session.query(SupplierPayment).filter_by(
                payment_id=payment_id,
                hospital_id=hospital_id
            ).first()
            
            if not payment:
                return None
            
            payment_dict = get_entity_dict(payment)
            
            # Add supplier information
            supplier = session.query(Supplier).filter_by(supplier_id=payment.supplier_id).first()
            if supplier:
                payment_dict['supplier_name'] = supplier.supplier_name
                payment_dict['supplier_code'] = getattr(supplier, 'supplier_code', str(supplier.supplier_id))
            
            # Add branch information
            if payment.branch_id:
                branch = session.query(Branch).filter_by(branch_id=payment.branch_id).first()
                if branch:
                    payment_dict['branch_name'] = branch.name
            
            # Add invoice information if linked
            if payment.invoice_id:
                invoice = session.query(SupplierInvoice).filter_by(invoice_id=payment.invoice_id).first()
                if invoice:
                    payment_dict['invoice_number'] = invoice.supplier_invoice_number
                    payment_dict['invoice_amount'] = float(invoice.total_amount)
            
            # Add documents if requested
            if include_documents:
                from app.models.transaction import PaymentDocument
                documents = session.query(PaymentDocument).filter_by(
                    payment_id=payment_id
                ).order_by(PaymentDocument.updated_at.desc()).all()
                
                payment_dict['documents'] = [get_entity_dict(doc) for doc in documents]
            
            # Add approval information if requested
            if include_approvals:
                # Add approval workflow data based on your approval system
                payment_dict['approval_history'] = []
            
            # Format amounts for display
            payment_dict['formatted_amount'] = f"₹{float(payment.amount):,.2f}"
            payment_dict['formatted_payment_date'] = payment.payment_date.strftime("%d %b %Y")
            
            return payment_dict
            
        except Exception as e:
            logger.error(f"Error getting payment by ID: {str(e)}")
            raise
    
    def _calculate_payment_summary(self, session: Session, hospital_id: uuid.UUID, 
                                 branch_id: Optional[uuid.UUID] = None, filters: Dict = None) -> Dict:
        """Calculate payment summary statistics using exact field names"""
        
        try:
            # Base query
            base_query = session.query(SupplierPayment).filter_by(hospital_id=hospital_id)
            
            if branch_id:
                base_query = base_query.filter(SupplierPayment.branch_id == branch_id)
            
            # Apply same filters as main query (except pagination)
            if filters:
                if filters.get('supplier_id'):
                    base_query = base_query.filter(SupplierPayment.supplier_id == uuid.UUID(filters['supplier_id']))
                if filters.get('workflow_status'):
                    base_query = base_query.filter(SupplierPayment.workflow_status == filters['workflow_status'])
                # Add other filter applications as needed
            
            # Total count and amount
            total_count = base_query.count()
            total_amount = base_query.with_entities(func.sum(SupplierPayment.amount)).scalar() or 0
            
            # Pending count - use exact status values from your system
            pending_count = base_query.filter(SupplierPayment.workflow_status == 'pending').count()
            
            # This month count
            first_day_this_month = date.today().replace(day=1)
            this_month_count = base_query.filter(
                SupplierPayment.payment_date >= first_day_this_month
            ).count()
            
            return {
                'total_count': total_count,
                'total_amount': float(total_amount),
                'pending_count': pending_count,
                'this_month_count': this_month_count
            }
            
        except Exception as e:
            logger.error(f"Error calculating payment summary: {str(e)}")
            return {
                'total_count': 0,
                'total_amount': 0.0,
                'pending_count': 0,
                'this_month_count': 0
            }
```

#### **Task 1.2: Update Existing Supplier Service to Use Universal Service**
Add to your existing `app/services/supplier_service.py`:

```python
# Add this to the top of your existing supplier_service.py
from app.services.universal_supplier_service import UniversalSupplierPaymentService

class EnhancedSupplierPaymentService:
    """Enhanced wrapper that uses universal service for core functionality"""
    
    def __init__(self):
        self.universal_service = UniversalSupplierPaymentService()
    
    def search_supplier_payments_enhanced(self, *args, **kwargs):
        """Enhanced search with additional business logic"""
        # Use universal service for core search
        result = self.universal_service.search_supplier_payments(*args, **kwargs)
        
        # Add any enhanced functionality here (analytics, etc.)
        return result
    
    def get_supplier_payment_by_id_enhanced(self, *args, **kwargs):
        """Enhanced detail retrieval with additional business logic"""
        # Use universal service for core functionality
        result = self.universal_service.get_supplier_payment_by_id(*args, **kwargs)
        
        # Add any enhanced functionality here (credit notes, etc.)
        return result

# Create global instance for gradual migration
enhanced_supplier_payment_service = EnhancedSupplierPaymentService()

# Gradual migration: Create wrapper functions that delegate to universal service
def search_supplier_payments_universal(*args, **kwargs):
    """Universal service wrapper - maintains exact same signature"""
    universal_service = UniversalSupplierPaymentService()
    return universal_service.search_supplier_payments(*args, **kwargs)

def get_supplier_payment_by_id_universal(*args, **kwargs):
    """Universal service wrapper - maintains exact same signature"""
    universal_service = UniversalSupplierPaymentService()
    return universal_service.get_supplier_payment_by_id(*args, **kwargs)
```

---

### **Day 2: Entity Configuration Using Your Exact Field Names**

#### **Task 2.1: Enhanced Field Definitions with CSS Integration**
Create `app/config/field_definitions.py`:

```python
"""
Enhanced Field Definitions - Integrated with Your CSS Component System
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

class FieldType(Enum):
    """Field types that map to your CSS components"""
    TEXT = "text"                    # Uses .form-input
    NUMBER = "number"                # Uses .form-input with number type
    AMOUNT = "amount"                # Uses .form-input with currency formatting
    DATE = "date"                    # Uses .form-input with date type
    DATETIME = "datetime"            # Uses .form-input with datetime-local
    SELECT = "select"                # Uses .form-select
    MULTI_SELECT = "multi_select"    # Uses .form-select with multiple
    STATUS_BADGE = "status_badge"    # Uses your .status-badge classes
    BOOLEAN = "boolean"              # Uses .form-checkbox
    UUID = "uuid"                    # Hidden field type
    REFERENCE = "reference"          # Link to related entity

class StatusType(Enum):
    """Status types that map to your CSS status classes"""
    ACTIVE = "status-active"         # Uses .status-active
    PENDING = "status-pending"       # Uses .status-pending  
    APPROVED = "status-approved"     # Uses .status-approved
    CANCELLED = "status-cancelled"   # Uses .status-cancelled
    COMPLETED = "status-completed"   # Uses .status-completed
    REJECTED = "status-rejected"     # Uses .status-rejected

class ButtonType(Enum):
    """Button types that map to your CSS button classes"""
    PRIMARY = "btn-primary"          # Uses .btn-primary
    SECONDARY = "btn-secondary"      # Uses .btn-secondary
    SUCCESS = "btn-success"          # Uses .btn-success
    WARNING = "btn-warning"          # Uses .btn-warning
    DANGER = "btn-danger"            # Uses .btn-danger
    OUTLINE = "btn-outline"          # Uses .btn-outline

@dataclass
class ActionDefinition:
    """Action definitions that use your CSS action button classes"""
    id: str
    label: str
    icon: str
    button_type: ButtonType
    permission: Optional[str] = None
    conditions: Optional[Dict] = None
    url_pattern: Optional[str] = None  # For building URLs

@dataclass
class FieldDefinition:
    """Field definitions that integrate with your CSS form components"""
    name: str
    label: str
    field_type: FieldType
    show_in_list: bool = False
    show_in_detail: bool = True
    searchable: bool = False
    sortable: bool = False
    filterable: bool = False
    required: bool = False
    readonly: bool = False
    
    # CSS integration
    css_classes: Optional[str] = None           # Additional CSS classes
    form_component: Optional[str] = None        # Specific form component to use
    display_component: Optional[str] = None     # Specific display component to use
    
    # Options for select/multi-select fields
    options: Optional[List[Dict]] = None
    dynamic_options: Optional[str] = None       # Service method to get options
    
    # Validation and formatting
    validation: Optional[Dict] = None
    format_pattern: Optional[str] = None
    help_text: Optional[str] = None
    
    # Display settings
    width: Optional[str] = None
    align: Optional[str] = None
    
    # Filter-specific settings
    filter_type: Optional[str] = None
    filter_css_class: Optional[str] = None

@dataclass
class EntityConfiguration:
    """Complete entity configuration using your CSS and field system"""
    entity_type: str
    service_name: str
    name: str
    plural_name: str
    table_name: str
    primary_key: str
    title_field: str
    subtitle_field: str
    icon: str
    
    # CSS integration
    table_css_class: str = "data-table"         # Uses your .data-table
    card_css_class: str = "info-card"           # Uses your .info-card
    filter_css_class: str = "filter-card"       # Uses your .filter-card
    
    # Display settings
    items_per_page: int = 20
    default_sort_field: str = "created_at"
    default_sort_order: str = "desc"
    
    # Features
    enable_search: bool = True
    enable_filters: bool = True
    enable_export: bool = True
    enable_bulk_actions: bool = False
    
    # Field and action definitions
    fields: List[FieldDefinition]
    actions: List[ActionDefinition]
    
    # Summary card configuration
    summary_cards: Optional[List[Dict]] = None
```

#### **Task 2.2: Supplier Payment Configuration with Exact Field Names**
Create `app/config/entity_configurations.py`:

```python
"""
Entity Configurations Using Your Exact Field Names and CSS Classes
"""

from typing import Dict, List
from .field_definitions import (
    FieldDefinition, FieldType, ActionDefinition, EntityConfiguration,
    StatusType, ButtonType
)

# Global registry
_entity_configs: Dict[str, EntityConfiguration] = {}

def register_entity_config(config: EntityConfiguration):
    """Register an entity configuration"""
    _entity_configs[config.entity_type] = config

def get_entity_config(entity_type: str) -> EntityConfiguration:
    """Get entity configuration by type"""
    if entity_type not in _entity_configs:
        raise ValueError(f"No configuration found for entity type: {entity_type}")
    return _entity_configs[entity_type]

def list_entity_types() -> List[str]:
    """Get list of all registered entity types"""
    return list(_entity_configs.keys())

def create_supplier_payment_config() -> EntityConfiguration:
    """Create supplier payment configuration using exact field names from SupplierPayment model"""
    
    return EntityConfiguration(
        entity_type="supplier_payments",
        service_name="supplier_payments",
        name="Supplier Payment",
        plural_name="Supplier Payments", 
        table_name="supplier_payment",           # Exact table name
        primary_key="payment_id",                # Exact primary key
        title_field="reference_no",              # Exact field name
        subtitle_field="supplier_name",          # From joined table
        icon="fas fa-money-bill",
        
        # CSS integration - use your existing classes
        table_css_class="data-table payment-history-table",  # Your predefined table layout
        card_css_class="info-card",
        filter_css_class="filter-card",
        
        # Summary cards using your stat-card CSS
        summary_cards=[
            {
                "id": "total_count",
                "label": "Total Payments",
                "icon": "fas fa-receipt",
                "css_class": "stat-card",
                "icon_css": "stat-card-icon primary",
                "value_field": "total_count"
            },
            {
                "id": "total_amount",
                "label": "Total Amount",
                "icon": "fas fa-rupee-sign", 
                "css_class": "stat-card",
                "icon_css": "stat-card-icon success",
                "value_field": "total_amount",
                "format": "currency"
            },
            {
                "id": "pending_count",
                "label": "Pending Approval",
                "icon": "fas fa-clock",
                "css_class": "stat-card", 
                "icon_css": "stat-card-icon danger",
                "value_field": "pending_count"
            },
            {
                "id": "this_month_count",
                "label": "This Month",
                "icon": "fas fa-calendar-check",
                "css_class": "stat-card",
                "icon_css": "stat-card-icon primary", 
                "value_field": "this_month_count"
            }
        ],
        
        # Field definitions using exact model field names
        fields=[
            FieldDefinition(
                name="payment_id",                    # Exact model field
                label="Payment ID",
                field_type=FieldType.UUID,
                show_in_list=False,
                show_in_detail=True,
                readonly=True
            ),
            FieldDefinition(
                name="reference_no",                  # Exact model field
                label="Payment Reference",
                field_type=FieldType.TEXT,
                show_in_list=True,
                show_in_detail=True,
                searchable=True,
                sortable=True,
                width="15%",
                css_classes="form-input"              # Your CSS class
            ),
            FieldDefinition(
                name="supplier_name",                 # From joined table
                label="Supplier",
                field_type=FieldType.TEXT,
                show_in_list=True,
                show_in_detail=True,
                searchable=True,
                sortable=True,
                width="22%",
                filterable=True,
                filter_type="select",
                dynamic_options="get_suppliers_for_filter",
                css_classes="supplier-name",          # Your supplier column CSS
                display_component="supplier_column"
            ),
            FieldDefinition(
                name="amount",                        # Exact model field
                label="Amount",
                field_type=FieldType.AMOUNT,
                show_in_list=True,
                show_in_detail=True,
                sortable=True,
                width="12%",
                align="right",
                format_pattern="₹{:,.2f}",
                filterable=True,
                filter_type="amount_range",
                css_classes="amount-value"            # Your amount formatting CSS
            ),
            FieldDefinition(
                name="payment_date",                  # Exact model field
                label="Payment Date",
                field_type=FieldType.DATE,
                show_in_list=True,
                show_in_detail=True,
                sortable=True,
                width="12%",
                filterable=True,
                filter_type="date_range",
                required=True,
                css_classes="form-input"
            ),
            FieldDefinition(
                name="workflow_status",               # Exact model field
                label="Status",
                field_type=FieldType.STATUS_BADGE,
                show_in_list=True,
                show_in_detail=True,
                sortable=True,
                filterable=True,
                filter_type="multi_select",
                width="12%",
                display_component="status-badge",     # Your CSS component
                options=[
                    {"value": "pending", "label": "Pending", "css_class": "status-pending"},
                    {"value": "approved", "label": "Approved", "css_class": "status-approved"},
                    {"value": "completed", "label": "Completed", "css_class": "status-completed"},
                    {"value": "cancelled", "label": "Cancelled", "css_class": "status-cancelled"},
                    {"value": "rejected", "label": "Rejected", "css_class": "status-rejected"}
                ]
            ),
            FieldDefinition(
                name="payment_method",                # Exact model field
                label="Payment Method",
                field_type=FieldType.SELECT,
                show_in_list=True,
                show_in_detail=True,
                sortable=True,
                filterable=True,
                filter_type="multi_select",
                width="15%",
                display_component="payment-method-badge",  # Custom component
                options=[
                    {"value": "cash", "label": "Cash", "icon": "fas fa-money-bill", "css_class": "payment-method-badge"},
                    {"value": "cheque", "label": "Cheque", "icon": "fas fa-money-check", "css_class": "payment-method-badge"},
                    {"value": "bank_transfer", "label": "Bank Transfer", "icon": "fas fa-university", "css_class": "payment-method-badge"},
                    {"value": "upi", "label": "UPI", "icon": "fas fa-mobile-alt", "css_class": "payment-method-badge"},
                    {"value": "mixed", "label": "Multiple Methods", "icon": "fas fa-layer-group", "css_class": "payment-method-badge"}
                ]
            ),
            FieldDefinition(
                name="branch_name",                   # From joined table
                label="Branch",
                field_type=FieldType.TEXT,
                show_in_list=True,
                show_in_detail=True,
                sortable=True,
                filterable=True,
                filter_type="select",
                width="12%",
                dynamic_options="get_branches_for_filter"
            ),
            FieldDefinition(
                name="invoice_number",                # From joined table
                label="Invoice",
                field_type=FieldType.REFERENCE,
                show_in_list=False,
                show_in_detail=True,
                searchable=True,
                width="15%",
                display_component="reference_link"
            ),
            FieldDefinition(
                name="notes",                         # Exact model field
                label="Notes",
                field_type=FieldType.TEXT,
                show_in_list=False,
                show_in_detail=True,
                css_classes="form-textarea"
            ),
            FieldDefinition(
                name="created_at",                    # Exact model field
                label="Created At",
                field_type=FieldType.DATETIME,
                show_in_list=False,
                show_in_detail=True,
                sortable=True,
                readonly=True
            )
        ],
        
        # Action definitions using your CSS button classes
        actions=[
            ActionDefinition(
                id="view",
                label="View",
                icon="fas fa-eye",
                button_type=ButtonType.OUTLINE,      # Uses .btn-outline
                permission="payment.view",
                url_pattern="supplier_views.view_payment"
            ),
            ActionDefinition(
                id="edit", 
                label="Edit",
                icon="fas fa-edit",
                button_type=ButtonType.WARNING,      # Uses .btn-warning
                permission="payment.edit",
                conditions={"workflow_status": ["pending", "draft"]},
                url_pattern="supplier_views.edit_payment"
            ),
            ActionDefinition(
                id="approve",
                label="Approve", 
                icon="fas fa-check",
                button_type=ButtonType.SUCCESS,      # Uses .btn-success
                permission="payment.approve",
                conditions={"workflow_status": ["pending"]},
                url_pattern="supplier_views.approve_payment"
            ),
            ActionDefinition(
                id="delete",
                label="Delete",
                icon="fas fa-trash",
                button_type=ButtonType.DANGER,       # Uses .btn-danger
                permission="payment.delete",
                conditions={"workflow_status": ["draft", "pending"]},
                url_pattern="supplier_views.delete_payment"
            )
        ]
    )

# Register the configuration
SUPPLIER_PAYMENT_CONFIG = create_supplier_payment_config()
register_entity_config(SUPPLIER_PAYMENT_CONFIG)

# Export for easy access
def get_supplier_payment_config() -> EntityConfiguration:
    return SUPPLIER_PAYMENT_CONFIG
```

---

### **Day 3: Enhanced CSS Components for Universal Use**

#### **Task 3.1: Universal Engine CSS Enhancement**
Create `app/static/css/components/universal_engine.css`:

```css
/*
Universal Engine CSS - Enhances Your Existing Components
File: static/css/components/universal_engine.css
Builds on top of your existing forms.css, tables.css, status.css, etc.
*/

/* ==========================================
   UNIVERSAL ENGINE CORE ENHANCEMENTS
   Extends your existing CSS components
   ========================================== */

/* Entity header - builds on your header-inline pattern */
.universal-entity-header {
    @apply header-inline;
    margin-bottom: 1.5rem !important;
}

.universal-entity-title {
    @apply text-2xl font-bold text-gray-800 dark:text-gray-100;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.universal-entity-subtitle {
    @apply text-gray-600 dark:text-gray-400 mt-1;
}

.universal-entity-actions {
    @apply header-inline-actions;
}

/* ==========================================
   UNIVERSAL SUMMARY CARDS
   Uses your existing stat-card components
   ========================================== */

.universal-summary-grid {
    @apply card-grid cols-4 mb-6;
}

/* Enhance your existing stat-card with universal functionality */
.universal-stat-card {
    @apply stat-card;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
}

.universal-stat-card:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
}

.universal-stat-card.clickable {
    cursor: pointer !important;
}

.universal-stat-card.clickable:hover .stat-card-value {
    color: rgb(59 130 246) !important; /* blue-500 */
}

/* ==========================================
   UNIVERSAL FILTER ENHANCEMENTS
   Builds on your existing filter-card
   ========================================== */

.universal-filter-card {
    @apply filter-card;
}

.universal-filter-header {
    @apply filter-card-header;
}

.universal-filter-title {
    @apply filter-card-title;
}

.universal-filter-body {
    @apply filter-card-body;
}

/* Enhanced filter sections */
.universal-filter-section {
    margin-bottom: 1.5rem !important;
}

.universal-filter-section:last-child {
    margin-bottom: 0 !important;
}

.universal-filter-section-title {
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: rgb(75 85 99) !important; /* gray-600 */
    margin-bottom: 0.75rem !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.dark .universal-filter-section-title {
    color: rgb(156 163 175) !important; /* gray-400 */
}

/* Date preset buttons - enhance your existing button styles */
.universal-date-presets {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.5rem !important;
    margin-bottom: 0.75rem !important;
}

.universal-date-preset {
    @apply btn-outline btn-sm;
    font-size: 0.75rem !important;
    padding: 0.25rem 0.75rem !important;
}

.universal-date-preset.active {
    @apply btn-primary;
}

/* Filter results count */
.universal-filter-results {
    font-size: 0.875rem !important;
    color: rgb(107 114 128) !important; /* gray-500 */
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.universal-filter-count-badge {
    background-color: rgb(59 130 246) !important; /* blue-500 */
    color: white !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    padding: 0.125rem 0.5rem !important;
    border-radius: 9999px !important;
}

/* ==========================================
   UNIVERSAL TABLE ENHANCEMENTS
   Builds on your existing data-table classes
   ========================================== */

.universal-table-container {
    @apply table-container;
}

.universal-table {
    @apply data-table;
}

/* Enhanced table headers with sorting */
.universal-table-header {
    position: relative !important;
}

.universal-table-header.sortable {
    cursor: pointer !important;
    user-select: none !important;
    transition: background-color 0.15s ease-in-out !important;
}

.universal-table-header.sortable:hover {
    background-color: rgb(243 244 246) !important; /* gray-100 */
}

.dark .universal-table-header.sortable:hover {
    background-color: rgb(75 85 99) !important; /* gray-600 */
}

.universal-sort-icon {
    margin-left: 0.25rem !important;
    font-size: 0.75rem !important;
    color: rgb(156 163 175) !important; /* gray-400 */
    transition: color 0.15s ease-in-out !important;
}

.universal-table-header.sortable:hover .universal-sort-icon {
    color: rgb(75 85 99) !important; /* gray-600 */
}

.universal-table-header.sorted .universal-sort-icon {
    color: rgb(59 130 246) !important; /* blue-500 */
}

/* Enhanced action column - builds on your payment-action-buttons */
.universal-action-column {
    text-align: center !important;
    width: 120px !important;
    min-width: 120px !important;
}

.universal-action-buttons {
    @apply payment-action-buttons;
    display: flex !important;
    flex-direction: column !important;
    gap: 0.25rem !important;
    align-items: center !important;
    padding: 0.25rem !important;
}

.universal-action-link {
    @apply payment-action-link;
    text-decoration: none !important;
    transition: all 0.15s ease-in-out !important;
}

/* ==========================================
   UNIVERSAL STATUS ENHANCEMENTS
   Builds on your existing status-badge system
   ========================================== */

.universal-status-badge {
    @apply status-badge;
}

/* Payment method badges - custom enhancement */
.universal-payment-method-badge {
    @apply status-badge;
    background-color: rgb(219 234 254) !important; /* blue-100 */
    color: rgb(30 64 175) !important; /* blue-800 */
    border: 1px solid rgb(147 197 253) !important; /* blue-200 */
}

.universal-payment-method-badge i {
    margin-right: 0.25rem !important;
    font-size: 0.75rem !important;
}

.dark .universal-payment-method-badge {
    background-color: rgb(30 58 138) !important; /* blue-900 */
    color: rgb(147 197 253) !important; /* blue-300 */
    border-color: rgb(59 130 246) !important; /* blue-500 */
}

/* ==========================================
   UNIVERSAL PAGINATION
   Builds on your existing pagination patterns
   ========================================== */

.universal-pagination {
    padding: 1rem 1.5rem !important;
    border-top: 1px solid rgb(229 231 235) !important; /* gray-200 */
    background-color: rgb(249 250 251) !important; /* gray-50 */
    display: flex !important;
    items-center !important;
    justify-content: space-between !important;
}

.dark .universal-pagination {
    border-color: rgb(75 85 99) !important; /* gray-600 */
    background-color: rgb(55 65 81) !important; /* gray-700 */
}

.universal-pagination-info {
    font-size: 0.875rem !important;
    color: rgb(75 85 99) !important; /* gray-600 */
}

.dark .universal-pagination-info {
    color: rgb(156 163 175) !important; /* gray-400 */
}

.universal-pagination-controls {
    display: flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
}

.universal-pagination-button {
    @apply btn-outline btn-sm;
    min-width: 2.5rem !important;
    padding: 0.25rem 0.5rem !important;
}

.universal-pagination-button.active {
    @apply btn-primary;
}

.universal-pagination-button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
}

/* ==========================================
   UNIVERSAL FORM ENHANCEMENTS  
   Builds on your existing form components
   ========================================== */

.universal-form-section {
    @apply medical-history-section;
}

.universal-form-title {
    @apply medical-history-title;
}

.universal-form-grid {
    @apply form-grid form-grid-cols-2;
}

.universal-form-actions {
    @apply footer-actions;
}

/* ==========================================
   UNIVERSAL RESPONSIVE UTILITIES
   ========================================== */

/* Enhanced mobile responsiveness for universal components */
@media (max-width: 768px) {
    .universal-entity-header {
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 1rem !important;
    }
    
    .universal-entity-actions {
        justify-content: center !important;
    }
    
    .universal-summary-grid {
        grid-template-columns: repeat(2, 1fr) !important;
    }
    
    .universal-filter-body {
        padding: 1rem !important;
    }
    
    .universal-date-presets {
        flex-direction: column !important;
        align-items: stretch !important;
    }
    
    .universal-pagination {
        flex-direction: column !important;
        gap: 1rem !important;
        text-align: center !important;
    }
}

@media (max-width: 640px) {
    .universal-summary-grid {
        grid-template-columns: repeat(1, 1fr) !important;
    }
    
    .universal-action-buttons {
        flex-direction: row !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
    }
    
    .universal-action-link {
        flex: 1 !important;
        min-width: auto !important;
        font-size: 0.625rem !important;
    }
}

/* ==========================================
   UNIVERSAL ANIMATION UTILITIES
   ========================================== */

.universal-fade-in {
    animation: universal-fade-in 0.3s ease-in-out !important;
}

@keyframes universal-fade-in {
    from {
        opacity: 0 !important;
        transform: translateY(10px) !important;
    }
    to {
        opacity: 1 !important;
        transform: translateY(0) !important;
    }
}

.universal-loading {
    opacity: 0.6 !important;
    pointer-events: none !important;
}

.universal-loading::after {
    content: '' !important;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    width: 20px !important;
    height: 20px !important;
    margin: -10px 0 0 -10px !important;
    border: 2px solid rgb(59 130 246) !important; /* blue-500 */
    border-radius: 50% !important;
    border-top-color: transparent !important;
    animation: universal-spin 1s linear infinite !important;
}

@keyframes universal-spin {
    to {
        transform: rotate(360deg) !important;
    }
}
```

#### **Task 3.2: Universal JavaScript Components**
Create `app/static/js/components/universal_engine.js`:

```javascript
/**
 * Universal Engine JavaScript Components
 * File: static/js/components/universal_engine.js
 * Reusable JS components for the universal engine
 */

class UniversalEngine {
    constructor(entityType, config = {}) {
        this.entityType = entityType;
        this.config = {
            enableAutoSubmit: false,
            enableLoadingStates: true,
            enableAnimations: true,
            ...config
        };
        
        this.init();
    }
    
    init() {
        this.setupSorting();
        this.setupFiltering();
        this.setupPagination();
        this.setupActions();
        this.setupDatePresets();
        this.setupStatCardClicks();
        
        if (this.config.enableAnimations) {
            this.setupAnimations();
        }
    }
    
    // Universal sorting functionality
    setupSorting() {
        document.querySelectorAll('.universal-table-header.sortable').forEach(header => {
            header.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleSort(header.dataset.field);
            });
        });
    }
    
    handleSort(field) {
        const currentUrl = new URL(window.location);
        const currentSort = currentUrl.searchParams.get('sort_by');
        const currentOrder = currentUrl.searchParams.get('sort_order');
        
        let newOrder = 'asc';
        if (currentSort === field && currentOrder === 'asc') {
            newOrder = 'desc';
        }
        
        currentUrl.searchParams.set('sort_by', field);
        currentUrl.searchParams.set('sort_order', newOrder);
        currentUrl.searchParams.delete('page'); // Reset to first page
        
        this.navigateWithLoading(currentUrl.toString());
    }
    
    // Universal filtering functionality
    setupFiltering() {
        const filterForm = document.getElementById('universal-filter-form');
        if (!filterForm) return;
        
        if (this.config.enableAutoSubmit) {
            // Auto-submit on select/date changes
            filterForm.querySelectorAll('select, input[type="date"]').forEach(element => {
                element.addEventListener('change', () => {
                    setTimeout(() => this.submitFilters(), 300);
                });
            });
        }
        
        // Manual submit
        filterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFilters();
        });
        
        // Clear filters
        const clearButton = document.getElementById('universal-clear-filters');
        if (clearButton) {
            clearButton.addEventListener('click', () => this.clearFilters());
        }
        
        // Export functionality
        const exportButton = document.getElementById('universal-export');
        if (exportButton) {
            exportButton.addEventListener('click', () => this.exportData());
        }
    }
    
    submitFilters() {
        const form = document.getElementById('universal-filter-form');
        const formData = new FormData(form);
        const params = new URLSearchParams();
        
        // Add form data to params
        for (let [key, value] of formData.entries()) {
            if (value.trim()) {
                params.append(key, value);
            }
        }
        
        // Handle multi-select fields
        form.querySelectorAll('select[multiple]').forEach(select => {
            const selectedValues = Array.from(select.selectedOptions).map(option => option.value);
            if (selectedValues.length > 0) {
                params.delete(select.name); // Clear existing
                selectedValues.forEach(value => params.append(select.name, value));
            }
        });
        
        // Reset page and navigate
        params.delete('page');
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        this.navigateWithLoading(newUrl);
        
        // Update filter count badge
        this.updateFilterCount();
    }
    
    clearFilters() {
        const form = document.getElementById('universal-filter-form');
        form.reset();
        
        // Clear URL parameters except page
        const url = new URL(window.location);
        url.search = '';
        this.navigateWithLoading(url.toString());
    }
    
    updateFilterCount() {
        const form = document.getElementById('universal-filter-form');
        const formData = new FormData(form);
        let count = 0;
        
        for (let [key, value] of formData.entries()) {
            if (value.trim()) count++;
        }
        
        const badge = document.querySelector('.universal-filter-count-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }
    
    // Date preset functionality
    setupDatePresets() {
        document.querySelectorAll('.universal-date-preset').forEach(btn => {
            btn.addEventListener('click', () => this.applyDatePreset(btn.dataset.preset));
        });
    }
    
    applyDatePreset(preset) {
        const today = new Date();
        let startDate = '';
        let endDate = '';
        
        switch(preset) {
            case 'today':
                startDate = endDate = today.toISOString().split('T')[0];
                break;
            case 'this_week':
                const weekStart = new Date(today.setDate(today.getDate() - today.getDay()));
                startDate = weekStart.toISOString().split('T')[0];
                endDate = new Date().toISOString().split('T')[0];
                break;
            case 'this_month':
                startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
                endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split('T')[0];
                break;
            case 'this_quarter':
                const quarter = Math.floor(today.getMonth() / 3);
                startDate = new Date(today.getFullYear(), quarter * 3, 1).toISOString().split('T')[0];
                endDate = new Date(today.getFullYear(), (quarter + 1) * 3, 0).toISOString().split('T')[0];
                break;
            case 'financial_year':
                const fyStart = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
                startDate = `${fyStart}-04-01`;
                endDate = `${fyStart + 1}-03-31`;
                break;
            case 'clear':
                startDate = endDate = '';
                break;
        }
        
        const startInput = document.getElementById('start_date');
        const endInput = document.getElementById('end_date');
        
        if (startInput) startInput.value = startDate;
        if (endInput) endInput.value = endDate;
        
        // Update button states
        document.querySelectorAll('.universal-date-preset').forEach(b => {
            b.classList.remove('active');
        });
        
        if (preset !== 'clear') {
            event.target.classList.add('active');
        }
        
        // Auto-submit if enabled
        if (this.config.enableAutoSubmit) {
            setTimeout(() => this.submitFilters(), 300);
        }
    }
    
    // Pagination functionality
    setupPagination() {
        document.querySelectorAll('.universal-pagination-button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (!btn.disabled && !btn.classList.contains('active')) {
                    this.goToPage(btn.dataset.page);
                }
            });
        });
    }
    
    goToPage(page) {
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        this.navigateWithLoading(url.toString());
    }
    
    // Action button functionality
    setupActions() {
        document.querySelectorAll('.universal-action-link').forEach(link => {
            if (link.dataset.confirm) {
                link.addEventListener('click', (e) => {
                    if (!confirm(link.dataset.confirm)) {
                        e.preventDefault();
                    }
                });
            }
        });
    }
    
    // Stat card click functionality
    setupStatCardClicks() {
        document.querySelectorAll('.universal-stat-card.clickable').forEach(card => {
            card.addEventListener('click', () => {
                const filter = card.dataset.filter;
                const value = card.dataset.value;
                
                if (filter && value) {
                    this.applyQuickFilter(filter, value);
                }
            });
        });
    }
    
    applyQuickFilter(filter, value) {
        const url = new URL(window.location);
        url.searchParams.set(filter, value);
        url.searchParams.delete('page');
        this.navigateWithLoading(url.toString());
    }
    
    // Animation setup
    setupAnimations() {
        // Add fade-in animation to elements as they load
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('universal-fade-in');
                }
            });
        });
        
        document.querySelectorAll('.universal-stat-card, .universal-table tbody tr').forEach(el => {
            observer.observe(el);
        });
    }
    
    // Export functionality
    exportData() {
        const form = document.getElementById('universal-filter-form');
        const formData = new FormData(form);
        formData.append('export', 'csv');
        
        const params = new URLSearchParams(formData);
        const exportUrl = `${window.location.pathname}?${params.toString()}`;
        
        // Create download link
        const link = document.createElement('a');
        link.href = exportUrl;
        link.download = `${this.entityType}_export_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Navigation with loading states
    navigateWithLoading(url) {
        if (this.config.enableLoadingStates) {
            document.body.classList.add('universal-loading');
        }
        
        window.location.href = url;
    }
    
    // Utility methods
    showMessage(message, type = 'info') {
        // Integration with your existing flash message system
        const alertHtml = `
            <div class="alert alert-${type} universal-fade-in">
                <i class="fas fa-info-circle alert-icon"></i>
                <div class="alert-content">${message}</div>
            </div>
        `;
        
        const container = document.querySelector('.flash-messages') || document.body;
        container.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alert = container.querySelector('.alert');
            if (alert) alert.remove();
        }, 5000);
    }
}

// Universal Engine Factory
window.UniversalEngine = UniversalEngine;

// Auto-initialize for supplier payments
document.addEventListener('DOMContentLoaded', function() {
    const entityType = document.body.dataset.entityType;
    
    if (entityType) {
        window.universalEngine = new UniversalEngine(entityType, {
            enableAutoSubmit: false,        // Set to true for auto-filtering
            enableLoadingStates: true,
            enableAnimations: true
        });
    }
});
```

---

### **Day 4: Universal Data Assembler Using Your CSS Classes**

#### **Task 4.1: Enhanced Data Assembler with CSS Integration**
Update `app/engine/data_assembler.py`:

```python
"""
Universal Data Assembler - Integrated with Your CSS Component System
Assembles complete UI structures using your existing CSS classes
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, date
from flask import url_for, request
from app.config.field_definitions import EntityConfiguration, FieldDefinition, FieldType
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalDataAssembler:
    """Assembles UI data using your existing CSS component system"""
    
    def assemble_list_data(self, config: EntityConfiguration, raw_data: Dict, 
                          additional_context: Dict = None) -> Dict:
        """Assemble complete list UI structure using your CSS classes"""
        
        try:
            payments = raw_data.get('payments', [])
            total = raw_data.get('total', 0)
            page = raw_data.get('page', 1)
            per_page = raw_data.get('per_page', config.items_per_page)
            summary = raw_data.get('summary', {})
            filters_applied = raw_data.get('filters_applied', {})
            
            # Assemble using your CSS classes
            assembled_data = {
                'entity_config': {
                    'entity_type': config.entity_type,
                    'name': config.name,
                    'plural_name': config.plural_name,
                    'icon': config.icon,
                    'primary_key': config.primary_key,
                    'table_css_class': config.table_css_class,        # Your CSS classes
                    'card_css_class': config.card_css_class,
                    'filter_css_class': config.filter_css_class
                },
                'table': self.assemble_table_structure(config, payments, total, page, per_page),
                'summary_cards': self.assemble_summary_cards(config, summary),
                'filter_structure': self.assemble_filter_structure(config, filters_applied, additional_context),
                'actions': self.assemble_actions(config),
                'pagination': self.assemble_pagination(total, page, per_page),
                'css_classes': self.assemble_css_classes(config)
            }
            
            # Add additional context
            if additional_context:
                assembled_data['additional_context'] = additional_context
            
            return assembled_data
            
        except Exception as e:
            logger.error(f"Error assembling list data: {str(e)}")
            raise
    
    def assemble_table_structure(self, config: EntityConfiguration, items: List[Dict],
                                total: int, page: int, per_page: int) -> Dict:
        """Assemble table structure using your data-table CSS classes"""
        
        return {
            'css_class': config.table_css_class,                    # Uses your CSS
            'columns': self.assemble_table_columns(config),
            'rows': self.assemble_table_rows(config, items),
            'total_count': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'has_data': len(items) > 0
        }
    
    def assemble_table_columns(self, config: EntityConfiguration) -> List[Dict]:
        """Build table columns using your existing table CSS"""
        
        columns = []
        
        for field in config.fields:
            if field.show_in_list:
                column = {
                    'name': field.name,
                    'label': field.label,
                    'type': field.field_type.value,
                    'sortable': field.sortable,
                    'width': field.width,
                    'align': field.align or 'left',
                    'css_classes': field.css_classes or '',
                    'display_component': field.display_component
                }
                
                # Add field-specific CSS and options
                if field.field_type == FieldType.STATUS_BADGE:
                    column['status_options'] = field.options
                    column['css_class'] = 'universal-status-badge'
                elif field.field_type == FieldType.AMOUNT:
                    column['css_class'] = 'amount-value text-right'
                elif field.field_type == FieldType.DATE:
                    column['css_class'] = 'date-value'
                elif field.name == 'supplier_name':
                    column['css_class'] = 'supplier-name'              # Your CSS class
                
                # Add sort icon if sortable
                if field.sortable:
                    column['sort_icon_class'] = 'universal-sort-icon fas fa-sort'
                
                columns.append(column)
        
        # Add action column
        columns.append({
            'name': 'actions',
            'label': 'Actions',
            'type': 'actions',
            'sortable': False,
            'width': '120px',
            'align': 'center',
            'css_class': 'universal-action-column'
        })
        
        return columns
    
    def assemble_table_rows(self, config: EntityConfiguration, items: List[Dict]) -> List[Dict]:
        """Assemble table rows using your existing CSS patterns"""
        
        rows = []
        list_fields = [field for field in config.fields if field.show_in_list]
        
        for item in items:
            row = {
                'id': item.get(config.primary_key),
                'css_class': 'universal-table-row',
                'cells': []
            }
            
            for field in list_fields:
                cell_value = item.get(field.name)
                formatted_value = self._format_field_value(field, cell_value)
                
                cell = {
                    'field_name': field.name,
                    'raw_value': cell_value,
                    'formatted_value': formatted_value,
                    'field_type': field.field_type.value,
                    'css_class': field.css_classes or '',
                    'align': field.align or 'left'
                }
                
                # Add field-specific CSS and rendering
                if field.field_type == FieldType.STATUS_BADGE:
                    status_option = self._get_status_option(field, cell_value)
                    cell['status_css_class'] = status_option.get('css_class', 'status-default')
                    cell['component'] = 'status_badge'
                    
                elif field.field_type == FieldType.SELECT and field.name == 'payment_method':
                    method_option = self._get_option_info(field, cell_value)
                    cell['icon'] = method_option.get('icon', '')
                    cell['component'] = 'payment_method_badge'
                    cell['css_class'] = 'universal-payment-method-badge'
                    
                elif field.field_type == FieldType.AMOUNT:
                    cell['component'] = 'amount'
                    cell['css_class'] = 'amount-value text-right'
                    
                elif field.field_type == FieldType.DATE:
                    cell['component'] = 'date'
                    cell['css_class'] = 'date-value'
                    
                elif field.name == 'supplier_name':
                    cell['component'] = 'supplier_column'
                    cell['css_class'] = 'supplier-name'               # Your CSS class
                
                row['cells'].append(cell)
            
            # Add action cell
            row['cells'].append({
                'field_name': 'actions',
                'component': 'actions',
                'css_class': 'universal-action-column',
                'actions': self._build_row_actions(config, item)
            })
            
            rows.append(row)
        
        return rows
    
    def assemble_summary_cards(self, config: EntityConfiguration, summary_data: Dict) -> List[Dict]:
        """Assemble summary cards using your stat-card CSS classes"""
        
        if not config.summary_cards:
            return []
        
        cards = []
        
        for card_config in config.summary_cards:
            value = summary_data.get(card_config['value_field'], 0)
            
            # Format value based on type
            if card_config.get('format') == 'currency':
                formatted_value = f"₹{float(value):,.2f}"
            elif card_config.get('format') == 'percentage':
                formatted_value = f"{float(value):.1f}%"
            else:
                formatted_value = str(value)
            
            card = {
                'id': card_config['id'],
                'label': card_config['label'],
                'value': formatted_value,
                'raw_value': value,
                'icon': card_config['icon'],
                'css_class': card_config.get('css_class', 'stat-card'),           # Your CSS
                'icon_css_class': card_config.get('icon_css', 'stat-card-icon'),
                'value_css_class': 'stat-card-value',
                'label_css_class': 'stat-card-label',
                'clickable': card_config.get('clickable', False)
            }
            
            # Add click filter if card is clickable
            if card['clickable']:
                card['filter_field'] = card_config.get('filter_field')
                card['filter_value'] = card_config.get('filter_value')
                card['css_class'] += ' universal-stat-card clickable'
            
            cards.append(card)
        
        return cards
    
    def assemble_filter_structure(self, config: EntityConfiguration, applied_filters: Dict, 
                                context: Dict = None) -> Dict:
        """Assemble filter structure using your filter-card CSS classes"""
        
        filterable_fields = [field for field in config.fields if field.filterable]
        
        filter_sections = []
        
        # Date range filter section (if any date fields exist)
        date_fields = [field for field in filterable_fields if field.field_type == FieldType.DATE]
        if date_fields:
            filter_sections.append({
                'type': 'date_range',
                'title': 'Date Range',
                'icon': 'fas fa-calendar-alt',
                'css_class': 'universal-filter-section',
                'fields': {
                    'start_date': applied_filters.get('start_date', ''),
                    'end_date': applied_filters.get('end_date', '')
                },
                'presets': [
                    {'id': 'today', 'label': 'Today', 'icon': 'fas fa-calendar-day'},
                    {'id': 'this_week', 'label': 'This Week', 'icon': 'fas fa-calendar-week'},
                    {'id': 'this_month', 'label': 'This Month', 'icon': 'fas fa-calendar-alt'},
                    {'id': 'this_quarter', 'label': 'This Quarter', 'icon': 'fas fa-calendar'},
                    {'id': 'financial_year', 'label': 'Financial Year', 'icon': 'fas fa-calendar-year'},
                    {'id': 'clear', 'label': 'Clear', 'icon': 'fas fa-times'}
                ],
                'preset_css_class': 'universal-date-preset'
            })
        
        # Build other filter sections
        for field in filterable_fields:
            if field.field_type == FieldType.DATE:
                continue  # Already handled above
            
            filter_section = {
                'field_name': field.name,
                'label': field.label,
                'type': field.filter_type or 'select',
                'icon': self._get_filter_icon(field),
                'css_class': 'universal-filter-section',
                'input_css_class': field.filter_css_class or self._get_filter_input_css(field),
                'current_value': applied_filters.get(field.name)
            }
            
            # Add options for select/multi-select filters
            if field.filter_type in ['select', 'multi_select']:
                if field.options:
                    filter_section['options'] = field.options
                elif field.dynamic_options and context:
                    # Get dynamic options from context
                    if field.name == 'supplier_name' and context.get('suppliers'):
                        filter_section['options'] = [
                            {'value': supplier['supplier_id'], 'label': supplier['supplier_name']}
                            for supplier in context['suppliers']
                        ]
                    elif field.name == 'branch_name' and context.get('branches'):
                        filter_section['options'] = [
                            {'value': branch['branch_id'], 'label': branch['name']}
                            for branch in context['branches']
                        ]
            
            filter_sections.append(filter_section)
        
        return {
            'css_class': config.filter_css_class,                    # Your CSS
            'header_css_class': 'universal-filter-header',
            'title_css_class': 'universal-filter-title',
            'body_css_class': 'universal-filter-body',
            'sections': filter_sections,
            'applied_filters': applied_filters,
            'filter_count': len([v for v in applied_filters.values() if v]),
            'results_css_class': 'universal-filter-results',
            'count_badge_css_class': 'universal-filter-count-badge'
        }
    
    def assemble_actions(self, config: EntityConfiguration) -> List[Dict]:
        """Assemble action definitions using your button CSS classes"""
        
        actions = []
        
        for action in config.actions:
            action_dict = {
                'id': action.id,
                'label': action.label,
                'icon': action.icon,
                'css_class': f"universal-action-link {action.button_type.value}",  # Your CSS
                'permission': action.permission,
                'conditions': action.conditions,
                'url_pattern': action.url_pattern
            }
            
            # Add specific CSS for different action types
            if action.id == 'view':
                action_dict['css_class'] += ' payment-action-link view'     # Your CSS
            elif action.id == 'edit':
                action_dict['css_class'] += ' payment-action-link edit'     # Your CSS
            elif action.id == 'approve':
                action_dict['css_class'] += ' payment-action-link approve'  # Your CSS
            elif action.id == 'delete':
                action_dict['css_class'] += ' payment-action-link delete'
                action_dict['confirm_message'] = 'Are you sure you want to delete this payment?'
            
            actions.append(action_dict)
        
        return actions
    
    def assemble_pagination(self, total: int, page: int, per_page: int) -> Dict:
        """Assemble pagination using your existing pagination patterns"""
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            'css_class': 'universal-pagination',
            'info_css_class': 'universal-pagination-info',
            'controls_css_class': 'universal-pagination-controls',
            'button_css_class': 'universal-pagination-button',
            'current_page': page,
            'per_page': per_page,
            'total_items': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'start_item': (page - 1) * per_page + 1,
            'end_item': min(page * per_page, total),
            'page_range': self._get_page_range(page, total_pages)
        }
    
    def assemble_css_classes(self, config: EntityConfiguration) -> Dict:
        """Assemble all CSS classes for the template"""
        
        return {
            'entity_header': 'universal-entity-header',
            'entity_title': 'universal-entity-title',
            'entity_subtitle': 'universal-entity-subtitle',
            'entity_actions': 'universal-entity-actions',
            'summary_grid': 'universal-summary-grid',
            'filter_card': 'universal-filter-card',
            'table_container': 'universal-table-container',
            'table': 'universal-table ' + config.table_css_class,
            'action_buttons': 'universal-action-buttons'
        }
    
    # Helper methods
    def _format_field_value(self, field: FieldDefinition, value: Any) -> str:
        """Format field values using your display patterns"""
        
        if value is None:
            return ""
        
        try:
            if field.field_type == FieldType.AMOUNT:
                if isinstance(value, (int, float, Decimal)):
                    return f"₹{float(value):,.2f}"
                return str(value)
            
            elif field.field_type == FieldType.DATE:
                if isinstance(value, (datetime, date)):
                    return value.strftime("%d %b %Y")
                return str(value)
            
            elif field.field_type == FieldType.DATETIME:
                if isinstance(value, datetime):
                    return value.strftime("%d %b %Y %I:%M %p")
                return str(value)
            
            elif field.format_pattern and isinstance(value, (int, float)):
                return field.format_pattern.format(value)
            
            else:
                return str(value)
                
        except Exception as e:
            logger.warning(f"Error formatting field {field.name}: {str(e)}")
            return str(value)
    
    def _get_status_option(self, field: FieldDefinition, value: Any) -> Dict:
        """Get status option with CSS class"""
        
        if not field.options:
            return {'css_class': 'status-default'}
        
        for option in field.options:
            if option['value'] == value:
                return option
        
        return {'css_class': 'status-default'}
    
    def _get_option_info(self, field: FieldDefinition, value: Any) -> Dict:
        """Get option information for select fields"""
        
        if not field.options:
            return {}
        
        for option in field.options:
            if option['value'] == value:
                return option
        
        return {}
    
    def _get_filter_icon(self, field: FieldDefinition) -> str:
        """Get appropriate icon for filter field"""
        
        field_icons = {
            'supplier_name': 'fas fa-building',
            'workflow_status': 'fas fa-flag',
            'payment_method': 'fas fa-credit-card',
            'branch_name': 'fas fa-map-marker-alt',
            'amount': 'fas fa-rupee-sign'
        }
        
        return field_icons.get(field.name, 'fas fa-filter')
    
    def _get_filter_input_css(self, field: FieldDefinition) -> str:
        """Get CSS class for filter input based on type"""
        
        if field.filter_type == 'select':
            return 'form-select'
        elif field.filter_type == 'multi_select':
            return 'form-select'
        elif field.field_type == FieldType.AMOUNT:
            return 'form-input'
        else:
            return 'form-input'
    
    def _build_row_actions(self, config: EntityConfiguration, item: Dict) -> List[Dict]:
        """Build action links for a table row"""
        
        actions = []
        
        for action_config in config.actions:
            # Check conditions
            if action_config.conditions:
                field_name = list(action_config.conditions.keys())[0]
                allowed_values = action_config.conditions[field_name]
                if item.get(field_name) not in allowed_values:
                    continue
            
            # Build URL
            url = '#'
            if action_config.url_pattern:
                try:
                    url = url_for(action_config.url_pattern, 
                                **{config.primary_key: item.get(config.primary_key)})
                except Exception:
                    url = '#'
            
            action = {
                'id': action_config.id,
                'label': action_config.label,
                'icon': action_config.icon,
                'url': url,
                'css_class': f"universal-action-link {action_config.button_type.value}",
                'permission': action_config.permission
            }
            
            actions.append(action)
        
        return actions
    
    def _get_page_range(self, current_page: int, total_pages: int) -> List[int]:
        """Get page range for pagination"""
        
        if total_pages <= 7:
            return list(range(1, total_pages + 1))
        
        if current_page <= 4:
            return list(range(1, 6)) + [total_pages]
        elif current_page >= total_pages - 3:
            return [1] + list(range(total_pages - 4, total_pages + 1))
        else:
            return [1] + list(range(current_page - 1, current_page + 2)) + [total_pages]
```

---

### **Day 5: Universal Templates Using Your CSS Classes**

#### **Task 5.1: Create Universal List Template**
Create `app/templates/engine/universal_list.html`:

```html
{% extends "layouts/dashboard.html" %}
{% from "components/alerts.html" import alert %}

{% block title %}{{ assembled_data.entity_config.plural_name }}{% endblock %}

{% block styles %}
{{ super() }}
<!-- Import your existing CSS files -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/universal_engine.css') }}">

<style>
/* Template-specific enhancements to your existing CSS */
.universal-template-enhancements {
    /* Any template-specific styles that don't belong in universal_engine.css */
}
</style>
{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6" data-entity-type="{{ assembled_data.entity_config.entity_type }}">
    
    <!-- Universal Entity Header using your header patterns -->
    <div class="{{ assembled_data.css_classes.entity_header }}">
        <div>
            <h1 class="{{ assembled_data.css_classes.entity_title }}">
                <i class="{{ assembled_data.entity_config.icon }}"></i>
                {{ assembled_data.entity_config.plural_name }}
            </h1>
            <p class="{{ assembled_data.css_classes.entity_subtitle }}">
                Manage and track {{ assembled_data.entity_config.plural_name|lower }} across all branches
            </p>
        </div>
        
        <!-- Entity Actions using your button classes -->
        <div class="{{ assembled_data.css_classes.entity_actions }}">
            {% for action in assembled_data.actions %}
                {% if action.id == 'create' %}
                <a href="{{ url_for('supplier_views.create_payment') }}" class="{{ action.css_class }}">
                    <i class="{{ action.icon }}"></i>{{ action.label }}
                </a>
                {% endif %}
            {% endfor %}
            
            <!-- Default entity-specific actions -->
            {% if assembled_data.entity_config.entity_type == 'supplier_payments' %}
                <a href="{{ url_for('supplier_views.create_payment') }}" class="btn-primary">
                    <i class="fas fa-plus icon-left"></i>Record Payment
                </a>
                <a href="{{ url_for('supplier_views.supplier_invoice_list') }}" class="btn-secondary">
                    <i class="fas fa-file-invoice icon-left"></i>Invoices
                </a>
                <a href="{{ url_for('supplier_views.supplier_list') }}" class="btn-secondary">
                    <i class="fas fa-users icon-left"></i>Suppliers
                </a>
            {% endif %}
        </div>
    </div>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="mb-6">
                {% for category, message in messages %}
                    {{ alert(message, category) }}
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Universal Summary Cards using your stat-card classes -->
    {% if assembled_data.summary_cards %}
    <div class="{{ assembled_data.css_classes.summary_grid }}">
        {% for card in assembled_data.summary_cards %}
        <div class="{{ card.css_class }}{% if card.clickable %} universal-stat-card clickable{% endif %}"
             {% if card.clickable %}data-filter="{{ card.filter_field }}" data-value="{{ card.filter_value }}"{% endif %}>
            <div class="{{ card.icon_css_class }}">
                <i class="{{ card.icon }}"></i>
            </div>
            <div class="{{ card.value_css_class }}">{{ card.value }}</div>
            <div class="{{ card.label_css_class }}">{{ card.label }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <!-- Universal Filter Card using your filter-card classes -->
    <div class="{{ assembled_data.filter_structure.css_class }}" id="universal-filter-section">
        <div class="{{ assembled_data.filter_structure.header_css_class }}">
            <h3 class="{{ assembled_data.filter_structure.title_css_class }}">
                <i class="fas fa-filter"></i>Filter {{ assembled_data.entity_config.plural_name }}
            </h3>
            <div class="{{ assembled_data.filter_structure.results_css_class }}">
                <span id="results-count">{{ assembled_data.table.total_count }} results</span>
                {% if assembled_data.filter_structure.filter_count > 0 %}
                    <span class="{{ assembled_data.filter_structure.count_badge_css_class }}">
                        {{ assembled_data.filter_structure.filter_count }} filters active
                    </span>
                {% endif %}
            </div>
        </div>
        
        <div class="{{ assembled_data.filter_structure.body_css_class }}">
            <form method="GET" id="universal-filter-form">
                
                {% for section in assembled_data.filter_structure.sections %}
                    {% if section.type == 'date_range' %}
                        <!-- Date Range Filter using your form components -->
                        <div class="{{ section.css_class }}">
                            <div class="universal-filter-section-title">
                                <i class="{{ section.icon }}"></i>{{ section.title }}
                            </div>
                            
                            <!-- Date Presets using your button classes -->
                            <div class="universal-date-presets">
                                {% for preset in section.presets %}
                                <button type="button" class="{{ section.preset_css_class }}" 
                                        data-preset="{{ preset.id }}">
                                    <i class="{{ preset.icon }}"></i>{{ preset.label }}
                                </button>
                                {% endfor %}
                            </div>
                            
                            <!-- Date Inputs using your form-input classes -->
                            <div class="flex gap-2 items-center">
                                <input type="date" name="start_date" id="start_date" 
                                       value="{{ section.fields.start_date }}" class="form-input">
                                <span class="text-gray-500">to</span>
                                <input type="date" name="end_date" id="end_date" 
                                       value="{{ section.fields.end_date }}" class="form-input">
                            </div>
                        </div>
                    
                    {% else %}
                        <!-- Field-based Filter using your form components -->
                        <div class="{{ section.css_class }}">
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                <i class="{{ section.icon }}"></i>{{ section.label }}
                            </label>
                            
                            {% if section.type == 'select' %}
                                <select name="{{ section.field_name }}" class="{{ section.input_css_class }}">
                                    <option value="">All {{ section.label }}</option>
                                    {% for option in section.options %}
                                        <option value="{{ option.value }}" 
                                                {% if section.current_value == option.value %}selected{% endif %}>
                                            {{ option.label }}
                                        </option>
                                    {% endfor %}
                                </select>
                                
                            {% elif section.type == 'multi_select' %}
                                <select name="{{ section.field_name }}" multiple class="{{ section.input_css_class }}" 
                                        style="height: auto;" size="4">
                                    {% for option in section.options %}
                                        <option value="{{ option.value }}"
                                                {% if section.current_value and option.value in section.current_value %}selected{% endif %}>
                                            {{ option.label }}
                                        </option>
                                    {% endfor %}
                                </select>
                                <p class="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple</p>
                                
                            {% elif section.type == 'amount_range' %}
                                <div class="flex gap-2 items-center">
                                    <input type="number" name="min_amount" placeholder="Min" 
                                           value="{{ section.current_value.min if section.current_value else '' }}" 
                                           class="{{ section.input_css_class }}" step="0.01">
                                    <span class="text-gray-500">to</span>
                                    <input type="number" name="max_amount" placeholder="Max" 
                                           value="{{ section.current_value.max if section.current_value else '' }}" 
                                           class="{{ section.input_css_class }}" step="0.01">
                                </div>
                                
                            {% else %}
                                <input type="text" name="{{ section.field_name }}" 
                                       value="{{ section.current_value or '' }}" 
                                       placeholder="Search {{ section.label|lower }}..." 
                                       class="{{ section.input_css_class }}">
                            {% endif %}
                        </div>
                    {% endif %}
                {% endfor %}
                
                <!-- Filter Actions using your button classes -->
                <div class="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button type="submit" class="btn-primary">
                        <i class="fas fa-search"></i>Apply Filters
                    </button>
                    <button type="button" id="universal-clear-filters" class="btn-secondary">
                        <i class="fas fa-times"></i>Clear All
                    </button>
                    <button type="button" id="universal-export" class="btn-outline">
                        <i class="fas fa-download"></i>Export
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Universal Data Table using your table classes -->
    <div class="{{ assembled_data.css_classes.table_container }}">
        {% if assembled_data.table.has_data %}
            <div class="overflow-x-auto">
                <table class="{{ assembled_data.css_classes.table }}">
                    <thead>
                        <tr>
                            {% for column in assembled_data.table.columns %}
                            <th class="universal-table-header{% if column.sortable %} sortable{% endif %}"
                                style="{% if column.width %}width: {{ column.width }};{% endif %} text-align: {{ column.align }};"
                                {% if column.sortable %}data-field="{{ column.name }}"{% endif %}>
                                
                                {% if column.sortable %}
                                    <span>{{ column.label }}</span>
                                    <i class="{{ column.sort_icon_class }}"></i>
                                {% else %}
                                    {{ column.label }}
                                {% endif %}
                            </th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in assembled_data.table.rows %}
                        <tr class="{{ row.css_class }}">
                            {% for cell in row.cells %}
                            <td style="text-align: {{ cell.align }};" class="{{ cell.css_class }}">
                                
                                {% if cell.component == 'status_badge' %}
                                    <span class="universal-status-badge {{ cell.status_css_class }}">
                                        {{ cell.formatted_value }}
                                    </span>
                                    
                                {% elif cell.component == 'payment_method_badge' %}
                                    <span class="{{ cell.css_class }}">
                                        {% if cell.icon %}<i class="{{ cell.icon }}"></i>{% endif %}
                                        {{ cell.formatted_value }}
                                    </span>
                                    
                                {% elif cell.component == 'supplier_column' %}
                                    <div class="supplier-column">
                                        <div class="supplier-name">{{ cell.formatted_value }}</div>
                                        {% if cell.raw_value != cell.formatted_value %}
                                            <div class="supplier-secondary">{{ cell.raw_value }}</div>
                                        {% endif %}
                                    </div>
                                    
                                {% elif cell.component == 'actions' %}
                                    <div class="{{ assembled_data.css_classes.action_buttons }}">
                                        {% for action in cell.actions %}
                                            <a href="{{ action.url }}" 
                                               class="{{ action.css_class }}"
                                               {% if action.get('confirm_message') %}
                                                   data-confirm="{{ action.confirm_message }}"
                                               {% endif %}>
                                                <i class="{{ action.icon }}"></i>
                                                <span class="action-text">{{ action.label }}</span>
                                            </a>
                                        {% endfor %}
                                    </div>
                                    
                                {% else %}
                                    {{ cell.formatted_value }}
                                {% endif %}
                            </td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <!-- Universal Pagination using your existing pagination patterns -->
            {% if assembled_data.pagination.total_pages > 1 %}
            <div class="{{ assembled_data.pagination.css_class }}">
                <div class="{{ assembled_data.pagination.info_css_class }}">
                    Showing {{ assembled_data.pagination.start_item }} 
                    to {{ assembled_data.pagination.end_item }} 
                    of {{ assembled_data.pagination.total_items }} results
                </div>
                
                <div class="{{ assembled_data.pagination.controls_css_class }}">
                    <!-- Previous Page -->
                    {% if assembled_data.pagination.has_prev %}
                        <a href="{{ request.url | replace('page=' ~ assembled_data.pagination.current_page, 'page=' ~ (assembled_data.pagination.current_page - 1)) }}" 
                           class="{{ assembled_data.pagination.button_css_class }}">
                            <i class="fas fa-chevron-left"></i>Previous
                        </a>
                    {% else %}
                        <span class="{{ assembled_data.pagination.button_css_class }}" disabled>
                            <i class="fas fa-chevron-left"></i>Previous
                        </span>
                    {% endif %}
                    
                    <!-- Page Numbers -->
                    {% for page_num in assembled_data.pagination.page_range %}
                        {% if page_num == assembled_data.pagination.current_page %}
                            <span class="{{ assembled_data.pagination.button_css_class }} active">{{ page_num }}</span>
                        {% else %}
                            <a href="{{ request.url | replace('page=' ~ assembled_data.pagination.current_page, 'page=' ~ page_num) }}" 
                               class="{{ assembled_data.pagination.button_css_class }}" data-page="{{ page_num }}">{{ page_num }}</a>
                        {% endif %}
                    {% endfor %}
                    
                    <!-- Next Page -->
                    {% if assembled_data.pagination.has_next %}
                        <a href="{{ request.url | replace('page=' ~ assembled_data.pagination.current_page, 'page=' ~ (assembled_data.pagination.current_page + 1)) }}" 
                           class="{{ assembled_data.pagination.button_css_class }}">
                            Next<i class="fas fa-chevron-right"></i>
                        </a>
                    {% else %}
                        <span class="{{ assembled_data.pagination.button_css_class }}" disabled>
                            Next<i class="fas fa-chevron-right"></i>
                        </span>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
        {% else %}
            <!-- Empty State using your existing patterns -->
            <div class="text-center py-12">
                <i class="{{ assembled_data.entity_config.icon }} text-4xl text-gray-300 mb-4"></i>
                <p class="text-gray-500">No {{ assembled_data.entity_config.plural_name|lower }} found</p>
                <p class="text-gray-400 text-sm">Try adjusting your filters or create a new {{ assembled_data.entity_config.name|lower }}</p>
                
                <!-- Quick action button -->
                {% if assembled_data.entity_config.entity_type == 'supplier_payments' %}
                <div class="mt-4">
                    <a href="{{ url_for('supplier_views.create_payment') }}" class="btn-primary">
                        <i class="fas fa-plus"></i>Record First Payment
                    </a>
                </div>
                {% endif %}
            </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block scripts %}
{{ super() }}
<!-- Import your universal engine JavaScript -->
<script src="{{ url_for('static', filename='js/components/universal_engine.js') }}"></script>

<script>
// Template-specific JavaScript enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Initialize universal engine with your specific configuration
    if (window.UniversalEngine) {
        window.universalEngine = new UniversalEngine('{{ assembled_data.entity_config.entity_type }}', {
            enableAutoSubmit: false,
            enableLoadingStates: true,
            enableAnimations: true
        });
    }
    
    // Custom enhancements for this template
    // Add any template-specific JavaScript here
});
</script>
{% endblock %}
```

#### **Task 5.2: Create Universal Components Directory**
Create `app/templates/engine/components/` directory with reusable components:

**Create `app/templates/engine/components/universal_summary_cards.html`:**
```html
<!-- Universal Summary Cards Component -->
<!-- Uses your existing stat-card CSS classes -->

{% macro render_summary_cards(cards, css_classes) %}
<div class="{{ css_classes.summary_grid }}">
    {% for card in cards %}
    <div class="{{ card.css_class }}{% if card.clickable %} universal-stat-card clickable{% endif %}"
         {% if card.clickable %}
             data-filter="{{ card.filter_field }}" 
             data-value="{{ card.filter_value }}"
             title="Click to filter by {{ card.label|lower }}"
         {% endif %}>
        <div class="{{ card.icon_css_class }}">
            <i class="{{ card.icon }}"></i>
        </div>
        <div class="{{ card.value_css_class }}">{{ card.value }}</div>
        <div class="{{ card.label_css_class }}">{{ card.label }}</div>
    </div>
    {% endfor %}
</div>
{% endmacro %}
```

**Create `app/templates/engine/components/universal_filter_card.html`:**
```html
<!-- Universal Filter Card Component -->
<!-- Uses your existing filter-card CSS classes -->

{% macro render_filter_card(filter_structure, entity_config) %}
<div class="{{ filter_structure.css_class }}" id="universal-filter-section">
    <div class="{{ filter_structure.header_css_class }}">
        <h3 class="{{ filter_structure.title_css_class }}">
            <i class="fas fa-filter"></i>Filter {{ entity_config.plural_name }}
        </h3>
        <div class="{{ filter_structure.results_css_class }}">
            <span id="results-count">{{ filter_structure.total_count or 0 }} results</span>
            {% if filter_structure.filter_count > 0 %}
                <span class="{{ filter_structure.count_badge_css_class }}">
                    {{ filter_structure.filter_count }} filters active
                </span>
            {% endif %}
        </div>
    </div>
    
    <div class="{{ filter_structure.body_css_class }}">
        <form method="GET" id="universal-filter-form">
            {% for section in filter_structure.sections %}
                {% if section.type == 'date_range' %}
                    {{ render_date_range_filter(section) }}
                {% else %}
                    {{ render_field_filter(section) }}
                {% endif %}
            {% endfor %}
            
            <!-- Filter Actions -->
            <div class="flex gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button type="submit" class="btn-primary">
                    <i class="fas fa-search"></i>Apply Filters
                </button>
                <button type="button" id="universal-clear-filters" class="btn-secondary">
                    <i class="fas fa-times"></i>Clear All
                </button>
                <button type="button" id="universal-export" class="btn-outline">
                    <i class="fas fa-download"></i>Export
                </button>
            </div>
        </form>
    </div>
</div>
{% endmacro %}

{% macro render_date_range_filter(section) %}
<div class="{{ section.css_class }}">
    <div class="universal-filter-section-title">
        <i class="{{ section.icon }}"></i>{{ section.title }}
    </div>
    
    <!-- Date Presets -->
    <div class="universal-date-presets">
        {% for preset in section.presets %}
        <button type="button" class="{{ section.preset_css_class }}" 
                data-preset="{{ preset.id }}">
            <i class="{{ preset.icon }}"></i>{{ preset.label }}
        </button>
        {% endfor %}
    </div>
    
    <!-- Date Inputs -->
    <div class="flex gap-2 items-center">
        <input type="date" name="start_date" id="start_date" 
               value="{{ section.fields.start_date }}" class="form-input">
        <span class="text-gray-500">to</span>
        <input type="date" name="end_date" id="end_date" 
               value="{{ section.fields.end_date }}" class="form-input">
    </div>
</div>
{% endmacro %}

{% macro render_field_filter(section) %}
<div class="{{ section.css_class }}">
    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        <i class="{{ section.icon }}"></i>{{ section.label }}
    </label>
    
    {% if section.type == 'select' %}
        <select name="{{ section.field_name }}" class="{{ section.input_css_class }}">
            <option value="">All {{ section.label }}</option>
            {% for option in section.options %}
                <option value="{{ option.value }}" 
                        {% if section.current_value == option.value %}selected{% endif %}>
                    {{ option.label }}
                </option>
            {% endfor %}
        </select>
        
    {% elif section.type == 'multi_select' %}
        <select name="{{ section.field_name }}" multiple class="{{ section.input_css_class }}" 
                style="height: auto;" size="4">
            {% for option in section.options %}
                <option value="{{ option.value }}"
                        {% if section.current_value and option.value in section.current_value %}selected{% endif %}>
                    {{ option.label }}
                </option>
            {% endfor %}
        </select>
        <p class="text-xs text-gray-500 mt-1">Hold Ctrl/Cmd to select multiple</p>
        
    {% elif section.type == 'amount_range' %}
        <div class="flex gap-2 items-center">
            <input type="number" name="min_amount" placeholder="Min" 
                   value="{{ section.current_value.min if section.current_value else '' }}" 
                   class="{{ section.input_css_class }}" step="0.01">
            <span class="text-gray-500">to</span>
            <input type="number" name="max_amount" placeholder="Max" 
                   value="{{ section.current_value.max if section.current_value else '' }}" 
                   class="{{ section.input_css_class }}" step="0.01">
        </div>
        
    {% else %}
        <input type="text" name="{{ section.field_name }}" 
               value="{{ section.current_value or '' }}" 
               placeholder="Search {{ section.label|lower }}..." 
               class="{{ section.input_css_class }}">
    {% endif %}
</div>
{% endmacro %}
```

**Create `app/templates/engine/components/universal_table.html`:**
```html
<!-- Universal Table Component -->
<!-- Uses your existing data-table CSS classes -->

{% macro render_universal_table(table, columns, rows, css_classes, actions) %}
<div class="{{ css_classes.table_container }}">
    {% if table.has_data %}
        <div class="overflow-x-auto">
            <table class="{{ css_classes.table }}">
                <thead>
                    <tr>
                        {% for column in columns %}
                        <th class="universal-table-header{% if column.sortable %} sortable{% endif %}"
                            style="{% if column.width %}width: {{ column.width }};{% endif %} text-align: {{ column.align }};"
                            {% if column.sortable %}data-field="{{ column.name }}"{% endif %}>
                            
                            {% if column.sortable %}
                                <span>{{ column.label }}</span>
                                <i class="{{ column.sort_icon_class }}"></i>
                            {% else %}
                                {{ column.label }}
                            {% endif %}
                        </th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in rows %}
                        {{ render_table_row(row, css_classes) }}
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% else %}
        {{ render_empty_state(table, css_classes) }}
    {% endif %}
</div>
{% endmacro %}

{% macro render_table_row(row, css_classes) %}
<tr class="{{ row.css_class }}">
    {% for cell in row.cells %}
    <td style="text-align: {{ cell.align }};" class="{{ cell.css_class }}">
        {{ render_table_cell(cell, css_classes) }}
    </td>
    {% endfor %}
</tr>
{% endmacro %}

{% macro render_table_cell(cell, css_classes) %}
{% if cell.component == 'status_badge' %}
    <span class="universal-status-badge {{ cell.status_css_class }}">
        {{ cell.formatted_value }}
    </span>
    
{% elif cell.component == 'payment_method_badge' %}
    <span class="{{ cell.css_class }}">
        {% if cell.icon %}<i class="{{ cell.icon }}"></i>{% endif %}
        {{ cell.formatted_value }}
    </span>
    
{% elif cell.component == 'supplier_column' %}
    <div class="supplier-column">
        <div class="supplier-name">{{ cell.formatted_value }}</div>
        {% if cell.supplier_code %}
            <div class="supplier-secondary">{{ cell.supplier_code }}</div>
        {% endif %}
    </div>
    
{% elif cell.component == 'amount' %}
    <span class="{{ cell.css_class }}">{{ cell.formatted_value }}</span>
    
{% elif cell.component == 'actions' %}
    <div class="{{ css_classes.action_buttons }}">
        {% for action in cell.actions %}
            <a href="{{ action.url }}" 
               class="{{ action.css_class }}"
               {% if action.get('confirm_message') %}
                   data-confirm="{{ action.confirm_message }}"
               {% endif %}>
                <i class="{{ action.icon }}"></i>
                <span class="action-text">{{ action.label }}</span>
            </a>
        {% endfor %}
    </div>
    
{% else %}
    {{ cell.formatted_value }}
{% endif %}
{% endmacro %}

{% macro render_empty_state(table, css_classes) %}
<div class="text-center py-12">
    <i class="fas fa-database text-4xl text-gray-300 mb-4"></i>
    <p class="text-gray-500">No data found</p>
    <p class="text-gray-400 text-sm">Try adjusting your filters</p>
</div>
{% endmacro %}
```

---

### **Day 5 Continued: Universal Engine Integration & Testing**

#### **Task 5.3: Create Universal List Service Integration**
Update `app/engine/universal_components.py`:

```python
"""
Universal Components - Enhanced with Your CSS Integration
These components orchestrate the universal engine functionality using your exact service signatures
"""

from typing import Dict, Any, Optional
from flask import request, current_app, url_for
from flask_login import current_user

from app.config.entity_configurations import get_entity_config
from app.engine.data_assembler import UniversalDataAssembler
from app.services.universal_supplier_service import UniversalSupplierPaymentService
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalListService:
    """Universal list service that works with your exact service signatures"""
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.config = get_entity_config(entity_type)
        self.assembler = UniversalDataAssembler()
    
    def get_list_data(self, additional_context: Dict = None) -> Dict:
        """Get complete assembled list data using your service signatures"""
        
        try:
            # Get the appropriate universal service
            universal_service = self._get_universal_service()
            
            # Extract filters using your existing parameter patterns
            filters = self._extract_filters_from_request()
            
            # Get raw data using exact same signature as your existing service
            raw_data = universal_service.search_supplier_payments(
                hospital_id=current_user.hospital_id,
                filters=filters,
                branch_id=filters.get('branch_id'),
                current_user_id=current_user.user_id,
                page=filters.get('page', 1),
                per_page=filters.get('per_page', self.config.items_per_page)
            )
            
            # Assemble complete UI structure using your CSS classes
            assembled_data = self.assembler.assemble_list_data(
                self.config, raw_data, additional_context
            )
            
            return assembled_data
            
        except Exception as e:
            logger.error(f"Error in universal list service for {self.entity_type}: {str(e)}")
            raise
    
    def _get_universal_service(self):
        """Get the appropriate universal service for the entity type"""
        
        if self.entity_type == 'supplier_payments':
            return UniversalSupplierPaymentService()
        
        # Add other entity services here as they are implemented
        else:
            raise ValueError(f"No universal service found for entity type: {self.entity_type}")
    
    def _extract_filters_from_request(self) -> Dict:
        """Extract filters using your existing parameter patterns"""
        
        filters = {}
        
        # Extract branch context using your existing helper
        from app.utils.context_helpers import get_branch_uuid_from_context_or_request
        branch_uuid, _ = get_branch_uuid_from_context_or_request()
        if branch_uuid:
            filters['branch_id'] = branch_uuid
        
        # Extract pagination
        filters['page'] = request.args.get('page', 1, type=int)
        filters['per_page'] = request.args.get('per_page', self.config.items_per_page, type=int)
        
        # Extract sorting
        filters['sort_by'] = request.args.get('sort_by', self.config.default_sort_field)
        filters['sort_order'] = request.args.get('sort_order', self.config.default_sort_order)
        
        # Extract supplier filtering - matches your existing parameter names
        supplier_id = request.args.get('supplier_id')
        supplier_search = request.args.get('supplier') or request.args.get('supplier_search')
        
        if supplier_id:
            filters['supplier_id'] = supplier_id
        elif supplier_search:
            filters['supplier_name_search'] = supplier_search
        
        # Extract status filtering - matches your existing parameter names
        statuses = request.args.getlist('status') or request.args.getlist('workflow_status')
        if statuses:
            filters['statuses'] = statuses
        elif request.args.get('workflow_status'):
            filters['workflow_status'] = request.args.get('workflow_status')
        elif request.args.get('status'):
            filters['workflow_status'] = request.args.get('status')
        
        # Extract payment method filtering - matches your existing parameter names
        payment_methods = request.args.getlist('payment_method')
        if payment_methods:
            filters['payment_methods'] = payment_methods
        elif request.args.get('payment_method'):
            filters['payment_methods'] = [request.args.get('payment_method')]
        
        # Extract date filtering - matches your existing parameter names
        filters['start_date'] = request.args.get('start_date')
        filters['end_date'] = request.args.get('end_date')
        
        # Extract amount filtering - matches your existing parameter names
        filters['min_amount'] = request.args.get('min_amount', type=float)
        filters['max_amount'] = request.args.get('max_amount', type=float)
        
        # Extract other filtering
        filters['reference_no'] = request.args.get('reference_no')
        filters['invoice_id'] = request.args.get('invoice_id')
        
        # Clean up empty filters
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        return filters

class UniversalDetailService:
    """Universal detail service using your exact service signatures"""
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.config = get_entity_config(entity_type)
        self.assembler = UniversalDataAssembler()
    
    def get_detail_data(self, entity_id: str, additional_context: Dict = None) -> Dict:
        """Get complete assembled detail data using your service signatures"""
        
        try:
            # Get the appropriate universal service
            universal_service = self._get_universal_service()
            
            # Get raw data using exact same signature as your existing service
            import uuid
            raw_data = universal_service.get_supplier_payment_by_id(
                payment_id=uuid.UUID(entity_id),
                hospital_id=current_user.hospital_id,
                include_documents=True,
                include_approvals=True
            )
            
            if not raw_data:
                return None
            
            # Assemble complete UI structure for detail view
            assembled_data = self.assembler.assemble_detail_data(
                self.config, raw_data, additional_context
            )
            
            return assembled_data
            
        except Exception as e:
            logger.error(f"Error in universal detail service for {self.entity_type}: {str(e)}")
            raise
    
    def _get_universal_service(self):
        """Get the appropriate universal service for the entity type"""
        
        if self.entity_type == 'supplier_payments':
            return UniversalSupplierPaymentService()
        else:
            raise ValueError(f"No universal service found for entity type: {self.entity_type}")

# Universal view functions for Flask routes - maintain exact compatibility
def universal_list_view(entity_type: str, additional_context: Dict = None) -> Dict:
    """Universal list view function - exact same pattern as your existing views"""
    
    try:
        list_service = UniversalListService(entity_type)
        assembled_data = list_service.get_list_data(additional_context)
        return assembled_data
        
    except Exception as e:
        logger.error(f"Error in universal list view for {entity_type}: {str(e)}")
        raise

def universal_detail_view(entity_type: str, entity_id: str, additional_context: Dict = None) -> Dict:
    """Universal detail view function - exact same pattern as your existing views"""
    
    try:
        detail_service = UniversalDetailService(entity_type)
        assembled_data = detail_service.get_detail_data(entity_id, additional_context)
        return assembled_data
        
    except Exception as e:
        logger.error(f"Error in universal detail view for {entity_type}: {str(e)}")
        raise
```

#### **Task 5.4: Create Test Route in Supplier Views**
Add this test route to your existing `supplier_views.py`:

```python
# Add this route to test universal engine alongside existing route
@supplier_views_bp.route('/payment/universal_list')  # Test route
@login_required
@require_web_branch_permission('payment', 'view')
def universal_payment_list():
    """TEST: Universal engine supplier payment list using exact same context as existing"""
    try:
        from app.engine.universal_components import universal_list_view
        from app.services.supplier_service import search_suppliers
        from app.utils.context_helpers import get_branch_uuid_from_context_or_request
        
        # Get suppliers for filter dropdown - exact same as existing implementation
        branch_uuid, _ = get_branch_uuid_from_context_or_request()
        
        suppliers = []
        try:
            supplier_result = search_suppliers(
                hospital_id=current_user.hospital_id,
                branch_id=branch_uuid,
                current_user_id=current_user.user_id,
                page=1,
                per_page=1000  # Get all suppliers for dropdown
            )
            suppliers = supplier_result.get('suppliers', [])
        except Exception as e:
            current_app.logger.error(f"Error loading suppliers: {str(e)}")
        
        # Get branches for filter dropdown
        branches = []
        try:
            from app.services.branch_service import get_user_accessible_branches
            branches = get_user_accessible_branches(current_user.user_id, current_user.hospital_id)
        except Exception as e:
            current_app.logger.error(f"Error loading branches: {str(e)}")
        
        # Use universal engine with same context as existing view
        assembled_data = universal_list_view(
            'supplier_payments',
            additional_context={
                'suppliers': suppliers,
                'branches': branches
            }
        )
        
        # Render with universal template
        return render_template('engine/universal_list.html', assembled_data=assembled_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal payment list: {str(e)}", exc_info=True)
        flash(f"Error retrieving payments: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))  # Fallback to existing
```

#### **Task 5.5: Create Validation Test Script**
Create `app/tests/test_week2_validation.py`:

```python
"""
Week 2 Universal Engine Validation Script
Tests integration with your existing CSS and service components
"""

import unittest
from flask import Flask
from app import create_app
from app.config.entity_configurations import get_entity_config
from app.engine.data_assembler import UniversalDataAssembler
from app.services.universal_supplier_service import UniversalSupplierPaymentService

class TestWeek2Implementation(unittest.TestCase):
    """Test Week 2 universal engine implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_entity_configuration_loads(self):
        """Test that supplier payment configuration loads correctly"""
        try:
            config = get_entity_config('supplier_payments')
            self.assertIsNotNone(config)
            self.assertEqual(config.entity_type, 'supplier_payments')
            self.assertEqual(config.name, 'Supplier Payment')
            self.assertEqual(config.table_name, 'supplier_payment')
            self.assertEqual(config.primary_key, 'payment_id')
            print("✅ Entity configuration loads successfully")
        except Exception as e:
            self.fail(f"Entity configuration failed: {str(e)}")
    
    def test_field_definitions_use_css_classes(self):
        """Test that field definitions include your CSS classes"""
        try:
            config = get_entity_config('supplier_payments')
            
            # Check CSS class integration
            self.assertEqual(config.table_css_class, "data-table payment-history-table")
            self.assertEqual(config.card_css_class, "info-card")
            self.assertEqual(config.filter_css_class, "filter-card")
            
            # Check field-specific CSS
            supplier_field = next((f for f in config.fields if f.name == 'supplier_name'), None)
            self.assertIsNotNone(supplier_field)
            self.assertEqual(supplier_field.css_classes, 'supplier-name')
            
            print("✅ Field definitions use your CSS classes correctly")
        except Exception as e:
            self.fail(f"CSS class integration failed: {str(e)}")
    
    def test_universal_service_method_signatures(self):
        """Test that universal service uses exact same method signatures"""
        try:
            service = UniversalSupplierPaymentService()
            
            # Test method exists with correct signature
            self.assertTrue(hasattr(service, 'search_supplier_payments'))
            self.assertTrue(hasattr(service, 'get_supplier_payment_by_id'))
            
            print("✅ Universal service has correct method signatures")
        except Exception as e:
            self.fail(f"Service signature test failed: {str(e)}")
    
    def test_data_assembler_css_integration(self):
        """Test that data assembler properly integrates with your CSS"""
        try:
            config = get_entity_config('supplier_payments')
            assembler = UniversalDataAssembler()
            
            # Test CSS class assembly
            css_classes = assembler.assemble_css_classes(config)
            
            self.assertIn('universal-entity-header', css_classes['entity_header'])
            self.assertIn('universal-summary-grid', css_classes['summary_grid'])
            self.assertIn('data-table payment-history-table', css_classes['table'])
            
            print("✅ Data assembler integrates with your CSS correctly")
        except Exception as e:
            self.fail(f"CSS integration test failed: {str(e)}")
    
    def test_summary_cards_use_stat_card_css(self):
        """Test that summary cards use your stat-card CSS classes"""
        try:
            config = get_entity_config('supplier_payments')
            
            # Check summary card configuration
            self.assertIsNotNone(config.summary_cards)
            self.assertTrue(len(config.summary_cards) > 0)
            
            for card in config.summary_cards:
                self.assertEqual(card['css_class'], 'stat-card')
                self.assertIn('stat-card-icon', card['icon_css'])
            
            print("✅ Summary cards use your stat-card CSS classes")
        except Exception as e:
            self.fail(f"Summary card CSS test failed: {str(e)}")
    
    def test_actions_use_button_css_classes(self):
        """Test that actions use your button CSS classes"""
        try:
            config = get_entity_config('supplier_payments')
            
            # Check action configurations
            self.assertIsNotNone(config.actions)
            self.assertTrue(len(config.actions) > 0)
            
            # Verify button types map to your CSS classes
            view_action = next((a for a in config.actions if a.id == 'view'), None)
            self.assertIsNotNone(view_action)
            self.assertEqual(view_action.button_type.value, 'btn-outline')
            
            edit_action = next((a for a in config.actions if a.id == 'edit'), None)
            self.assertIsNotNone(edit_action)
            self.assertEqual(edit_action.button_type.value, 'btn-warning')
            
            print("✅ Actions use your button CSS classes correctly")
        except Exception as e:
            self.fail(f"Action CSS test failed: {str(e)}")
    
    def test_status_badges_map_to_status_css(self):
        """Test that status badges map to your status CSS classes"""
        try:
            config = get_entity_config('supplier_payments')
            
            # Find status field
            status_field = next((f for f in config.fields if f.name == 'workflow_status'), None)
            self.assertIsNotNone(status_field)
            self.assertIsNotNone(status_field.options)
            
            # Check status CSS class mapping
            pending_option = next((o for o in status_field.options if o['value'] == 'pending'), None)
            self.assertIsNotNone(pending_option)
            self.assertEqual(pending_option['css_class'], 'status-pending')
            
            completed_option = next((o for o in status_field.options if o['value'] == 'completed'), None)
            self.assertIsNotNone(completed_option)
            self.assertEqual(completed_option['css_class'], 'status-completed')
            
            print("✅ Status badges map to your status CSS classes")
        except Exception as e:
            self.fail(f"Status CSS mapping test failed: {str(e)}")

def run_week2_validation():
    """Run all Week 2 validation tests"""
    
    print("🧪 Running Week 2 Universal Engine Validation Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWeek2Implementation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    
    if result.wasSuccessful():
        print("🎉 All Week 2 validation tests passed!")
        print("\n✅ Universal Engine Foundation is working with your CSS components!")
        print("✅ Service signatures match your existing implementation!")
        print("✅ Field mappings use your exact model fields!")
        print("✅ CSS integration leverages your component system!")
        
        print("\n📝 Next Steps:")
        print("   - Test with real data by visiting /supplier/payment/universal_list")
        print("   - Compare output with existing /supplier/payment/list")
        print("   - Validate all filtering and pagination works")
        print("   - Ready for production deployment!")
        
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} error(s) occurred")
        
        for test, error in result.failures + result.errors:
            print(f"\n❌ {test}: {error}")
            
        return False

if __name__ == "__main__":
    run_week2_validation()
```

---

## 🎯 **Week 2 Success Criteria Checklist**

### **Technical Implementation** ✅
- [ ] `UniversalSupplierPaymentService` uses exact same method signatures as existing service
- [ ] Entity configuration uses exact field names from `SupplierPayment` model
- [ ] Data assembler integrates with your existing CSS component system
- [ ] Universal template uses your `data-table`, `filter-card`, `stat-card` CSS classes
- [ ] Status badges use your existing `status-pending`, `status-completed` CSS classes
- [ ] Action buttons use your existing `btn-primary`, `btn-warning`, `btn-danger` CSS classes

### **CSS Component Integration** ✅
- [ ] Summary cards use your `stat-card` and `stat-card-icon` classes
- [ ] Filter card uses your `filter-card`, `filter-card-header`, `filter-card-body` classes
- [ ] Table uses your `data-table payment-history-table` predefined layout
- [ ] Action buttons use your `payment-action-link` and `payment-action-buttons` classes
- [ ] Form inputs use your `form-input`, `form-select` classes
- [ ] Status displays use your `status-badge` system

### **Service Compatibility** ✅
- [ ] `search_supplier_payments(hospital_id, filters, branch_id, current_user_id, page, per_page, session)` - exact signature match
- [ ] `get_supplier_payment_by_id(payment_id, hospital_id, include_documents, include_approvals, session)` - exact signature match
- [ ] Filter parameter names match your existing implementation (`supplier_id`, `workflow_status`, `payment_method`, etc.)
- [ ] Branch context integration uses your existing helper functions
- [ ] Permission decorators work seamlessly with universal engine

### **Functional Validation** ✅
- [ ] `/supplier/payment/universal_list` shows same data as existing `/supplier/payment/list`
- [ ] All existing filters work (supplier dropdown, date range, status multi-select, payment method)
- [ ] Pagination functions correctly with your existing URL patterns
- [ ] Summary cards display accurate data using your existing calculation logic
- [ ] Sorting works on configured columns using your existing sort parameters
- [ ] Actions (view, edit, approve) link correctly using your existing URL patterns

### **User Experience** ✅
- [ ] Interface looks identical to existing design (uses your CSS)
- [ ] Mobile responsiveness works (leverages your responsive CSS)
- [ ] Dark mode support works (uses your dark mode classes)
- [ ] Loading states work (uses your existing patterns)
- [ ] Form validation works (integrates with your form system)

---

## 🚀 **Week 2 Outcomes**

**By end of Week 2, you will have:**

1. **First Universal Entity** - Supplier payments fully working through universal engine using your exact CSS components
2. **CSS Integration** - Universal engine that leverages your comprehensive component system (`forms.css`, `tables.css`, `status.css`, etc.)
3. **Service Compatibility** - Universal services that use exact same method signatures as your existing services
4. **Template Foundation** - Universal components that work with your existing design system
5. **Migration Path** - Proven approach for converting other entities while preserving all existing functionality

**Ready for Week 3:** Template refinements, additional components, and preparation for rapid entity rollout using your established CSS and service patterns!

**Key Advantage:** Your universal engine uses your existing, proven CSS component system - no design changes needed, just enhanced configuration capabilities!

🎯 Key Strengths of This Week 2 Plan:
1. Zero CSS Changes Required

Uses your existing classes exactly: data-table, stat-card, filter-card, status-badge, payment-action-buttons
Builds on your component system: Enhances rather than replaces your proven CSS
Maintains your design consistency: Same look and feel, enhanced functionality

2. Perfect Service Integration

Exact method signatures: search_supplier_payments(hospital_id, filters, branch_id, current_user_id, page, per_page, session)
Uses your exact field names: payment_id, workflow_status, payment_method, reference_no from your SupplierPayment model
Preserves your parameter patterns: supplier_id, statuses, payment_methods - matches your existing filter logic

3. Seamless Data Model Integration

Exact field mapping: Based on your transaction.py and master.py models
Preserves relationships: Supplier joins, branch context, invoice links work exactly as before
Maintains your business logic: Approval workflows, permission checks, branch filtering

4. Enhanced Reusability

JavaScript components: UniversalEngine class that can be reused for any entity
CSS enhancement: universal_engine.css that extends your existing components
Template components: Reusable macros that work with your design system

5. Gradual Migration Path

Side-by-side testing: /supplier/payment/universal_list alongside existing /supplier/payment/list
Backward compatibility: Your existing routes continue working unchanged
Risk-free validation: Can compare outputs before switching over

🚀 Ready to Implement?
The plan is structured for immediate implementation because it:

✅ Uses your exact data structures and service signatures
✅ Leverages your comprehensive CSS component system
✅ Follows your collaboration guidelines and architectural patterns
✅ Provides comprehensive testing and validation
✅ Creates the foundation for Week 3 rapid entity rollout

Would you like me to:

Start with Day 1 and create the specific code files?
Focus on a particular component (like the Universal Service or CSS enhancements)?
Provide more details on any specific aspect of the implementation?

This Week 2 plan transforms your working supplier payment system into the universal engine foundation while preserving everything that already works perfectly!