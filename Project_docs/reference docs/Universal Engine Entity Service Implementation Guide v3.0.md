# Universal Engine Entity Service Implementation Guide v2.0 (Audited)

*Last Updated: [Current Date] - Added Hidden Card Pattern for Filtered Aggregations*

---

## Table of Contents
1. [Overview](#overview)
2. [Configuration Structure](#configuration-structure)
3. [Summary Cards & Calculations (UPDATED)](#summary-cards--calculations)
4. [Service Implementation](#service-implementation)
5. [Custom Renderers](#custom-renderers)
6. [Virtual Fields](#virtual-fields)
7. [Filter System](#filter-system)
8. [Caching Strategy](#caching-strategy)
9. [Database Design](#database-design)
10. [Best Practices](#best-practices)
11. [Configuration vs Code](#configuration-vs-code)
12. [Complete Examples](#complete-examples)
13. [Advanced Patterns](#advanced-patterns)
14. [Troubleshooting](#troubleshooting)
15. [Migration Guide](#migration-guide)

---

## Overview

The Universal Engine provides a configuration-driven approach to entity management, minimizing custom code while maximizing performance and maintainability.

### Key Principles
- **Configuration over Code**: Define behavior through configuration
- **Performance First**: Single optimized queries over multiple calls
- **Consistency**: Uniform patterns across all entities
- **Maintainability**: Framework handles complexity

---

## Configuration Structure

### 1. Field Definitions

```python
{ENTITY}_FIELDS = [
    FieldDefinition(
        name="field_name",           # Field identifier
        label="Display Label",        # UI label
        field_type=FieldType.TEXT,    # Data type from core_definitions.py
        db_column="database_column",  # Database column (if different from name)
        virtual=True,                 # Calculated field (not in DB)
        show_in_list=True,           # Display flags
        show_in_detail=True,
        show_in_form=True,
        filterable=True,             # Can be filtered
        filter_operator=FilterOperator.CONTAINS,  # Filter behavior
        custom_renderer=CustomRenderer(  # Custom display logic
            template="components/template.html",
            context_function="get_field_display"
        )
    )
]
```

### 2. Filter Category Mapping

```python
{ENTITY}_FILTER_CATEGORY_MAPPING = {
    "status": FilterCategory.SELECTION,
    "supplier_id": FilterCategory.RELATIONSHIP,
    "payment_date": FilterCategory.DATE,
    "amount": FilterCategory.AMOUNT,
    "name": FilterCategory.SEARCH
}
```

### 3. Main Configuration

```python
{ENTITY}_CONFIG = EntityConfiguration(
    entity_type="{entity_type}",
    model_class="app.models.views.{Entity}View",  # String path to model
    primary_key="{entity}_id",
    title_field="name",
    fields={ENTITY}_FIELDS,
    summary_cards={ENTITY}_SUMMARY_CARDS,
    filter_category_mapping={ENTITY}_FILTER_CATEGORY_MAPPING,
    view_layout=ViewLayoutConfiguration(
        type=LayoutType.TABBED,
        tabs={...}
    )
)
```

---

## Summary Cards & Calculations

### 🎯 Key Insight: Use Hidden Cards Instead of Service Overrides

The Universal Engine supports powerful filtered aggregations through hidden cards with `filter_condition`. This eliminates the need for most service overrides and provides better performance.

### Configuration-Based Summary Calculations (Recommended)

#### Pattern 1: Direct Column Aggregation
```python
# Simple sum of a database column - Universal Engine handles automatically
{
    "id": "total_amount",
    "field": "invoice_total_amount",  # Direct DB column
    "label": "Total Amount",
    "icon": "fas fa-rupee-sign",
    "type": "currency",  # Triggers SUM aggregation
    "visible": True
}
```

#### Pattern 2: Filtered Aggregation with Hidden Cards (NEW!)
```python
# THIS IS THE KEY PATTERN - No service override needed!
SUMMARY_CARDS = [
    # Step 1: Hidden calculation card with filter
    {
        "id": "pending_calc",  # Unique ID for calculation
        "field": "invoice_total_amount",  # Column to aggregate
        "type": "currency",  # Triggers SUM
        "visible": False,  # HIDDEN - just for calculation
        "filter_condition": {  # Universal Engine applies this filter!
            "payment_status": ["pending", "partial"]  # WHERE clause
        }
    },
    
    # Step 2: Visible card references the calculation
    {
        "id": "pending_amount",
        "field": "pending_calc",  # References hidden card ID
        "label": "Pending Payment",
        "icon": "fas fa-clock",
        "type": "currency",
        "visible": True  # This one is shown
    }
]
```

#### Pattern 3: Complex Breakdown Cards
```python
SUMMARY_CARDS = [
    # Multiple hidden calculations for breakdown
    {"id": "cash_sum", "field": "cash_amount", "type": "currency", "visible": False},
    {"id": "cheque_sum", "field": "cheque_amount", "type": "currency", "visible": False},
    {"id": "bank_sum", "field": "bank_transfer_amount", "type": "currency", "visible": False},
    {"id": "upi_sum", "field": "upi_amount", "type": "currency", "visible": False},
    
    # Detail card showing breakdown
    {
        "id": "payment_breakdown",
        "label": "Payment Methods",
        "icon": "fas fa-chart-pie",
        "type": "detail",
        "card_type": "detail",  # Special rendering
        "visible": True,
        "breakdown_fields": {
            "cash_sum": {
                "label": "Cash",
                "icon": "fas fa-money-bill",
                "color": "text-green-600"
            },
            "cheque_sum": {
                "label": "Cheque", 
                "icon": "fas fa-money-check",
                "color": "text-blue-600"
            },
            "bank_sum": {
                "label": "Bank",
                "icon": "fas fa-university",
                "color": "text-purple-600"
            },
            "upi_sum": {
                "label": "UPI",
                "icon": "fas fa-mobile",
                "color": "text-orange-600"
            }
        }
    }
]
```

### Performance Comparison

#### ✅ Configuration-Only (Recommended)
```sql
-- Universal Engine generates ONE optimized query:
SELECT 
    COUNT(*) as total_count,
    SUM(amount) as total_amount,
    SUM(CASE WHEN status IN ('pending','partial') THEN amount ELSE 0 END) as pending_calc,
    SUM(CASE WHEN payment_method = 'cash' THEN amount ELSE 0 END) as cash_sum
FROM entity_table
WHERE [filters]
```
**Performance: ~50ms, 1 query**

#### ❌ Service Override (Avoid)
```python
def calculate_summary_fields(self, ...):
    # Multiple separate queries - SLOWER!
    total = session.query(func.sum(Model.amount)).scalar()  # Query 1
    pending = session.query(func.sum(Model.amount)).filter(...).scalar()  # Query 2
    cash = session.query(func.sum(Model.amount)).filter(...).scalar()  # Query 3
```
**Performance: ~200ms, 3+ queries**

### Enhanced Summary Hook (Only When Necessary)

```python
def calculate_summary_fields(self, session: Session, filtered_query,
                            summary: Dict, config, filters: Dict,
                            hospital_id: UUID, branch_id: Optional[UUID],
                            **kwargs) -> Dict:
    """
    Hook for complex summary calculations
    Called AFTER configuration-based calculations
    
    ⚠️ ONLY use for:
    1. Complex calculations not possible in SQL
    2. External API integration
    3. Multi-step dependent calculations
    
    DO NOT use for simple filtered aggregations - use hidden cards!
    
    Args:
        session: Database session
        filtered_query: Query with all filters applied
        summary: Current summary with config calculations
        config: Entity configuration
        filters: Applied filters dict
        hospital_id, branch_id: Context
        
    Returns:
        Enhanced summary dict
    """
    # Example: Weighted average (can't be done with simple SQL)
    items = filtered_query.all()
    if items:
        weighted_sum = sum(item.amount * item.weight for item in items)
        total_weight = sum(item.weight for item in items)
        summary['weighted_avg'] = weighted_sum / total_weight if total_weight else 0
    
    return summary
```

---

## Service Implementation

### Basic Service Structure

```python
from app.services.universal_entity_service import UniversalEntityService
from app.models.views import EntityNameView
import uuid
from typing import Dict, List, Optional, Any

class EntityNameService(UniversalEntityService):
    """
    Service implementation for EntityName
    Inherits all CRUD operations from UniversalEntityService
    
    IMPORTANT: Only add custom methods for complex business logic
    Standard aggregations should use configuration!
    """
    
    def __init__(self):
        """Initialize with model class and entity type"""
        super().__init__(
            model_class=EntityNameView,  # Use view for denormalized data
            entity_type='entity_name'
        )
    
    # =========================================================================
    # Lifecycle Hooks (Optional)
    # =========================================================================
    
    def before_create(self, data: Dict, **kwargs) -> Dict:
        """Pre-create data validation/transformation"""
        # Add custom validation or data transformation
        return data
    
    def after_create(self, entity: Any, **kwargs) -> None:
        """Post-create operations (notifications, etc.)"""
        pass
    
    def before_update(self, entity_id: uuid.UUID, data: Dict, **kwargs) -> Dict:
        """Pre-update validation"""
        return data
    
    def after_update(self, entity: Any, **kwargs) -> None:
        """Post-update operations"""
        pass
    
    def before_delete(self, entity_id: uuid.UUID, **kwargs) -> bool:
        """Pre-delete validation - return False to prevent deletion"""
        return True
    
    def after_delete(self, entity_id: uuid.UUID, **kwargs) -> None:
        """Post-delete cleanup"""
        pass
    
    # =========================================================================
    # Query Hooks (Optional)
    # =========================================================================
    
    def after_filters_applied(self, query, filters: Dict, **kwargs):
        """Additional query modifications after standard filters"""
        # Add complex joins or additional filters if needed
        return query
    
    # =========================================================================
    # DON'T override calculate_summary_fields unless absolutely necessary!
    # Use hidden cards with filter_condition instead
    # =========================================================================
```

---

## Custom Renderers

### Configuration

```python
FieldDefinition(
    name="payment_history",
    field_type=FieldType.CUSTOM,
    virtual=True,
    show_in_detail=True,
    custom_renderer=CustomRenderer(
        template="components/payment_history.html",
        context_function="get_payment_history_display",  # Service method
        css_classes="table-responsive"
    )
)
```

### Service Method

```python
@cache_service_method('{entity_type}', 'payment_history')
def get_payment_history_display(self, item_id=None, item=None, **kwargs) -> Dict:
    """
    Called by template when rendering custom field
    Returns data structure for the template
    """
    entity_id = item_id or item.get('{primary_key}')
    
    with get_db_session() as session:
        payments = session.query(Payment).filter(
            Payment.entity_id == entity_id
        ).order_by(Payment.date.desc()).limit(10).all()
        
        return {
            'payments': [get_entity_dict(p) for p in payments],
            'total': sum(p.amount for p in payments),
            'count': len(payments),
            'has_data': len(payments) > 0,
            'currency_symbol': '₹'
        }
```

---

## Virtual Fields

### Adding Virtual/Calculated Fields

```python
def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
    """
    Add virtual/calculated fields to detail view data
    Called automatically by parent for detail views
    """
    try:
        # Calculate age
        if result.get('created_date'):
            created = result['created_date']
            if isinstance(created, str):
                created = datetime.strptime(created, '%Y-%m-%d')
            age_delta = datetime.now() - created
            result['age_days'] = age_delta.days
        
        # Calculate derived values
        if result.get('amount') and result.get('quantity'):
            result['unit_price'] = result['amount'] / result['quantity']
        
        return result
        
    except Exception as e:
        logger.error(f"Error in virtual calculations: {str(e)}")
        return result
```

---

## Filter System

### Filter Categories

```python
class FilterCategory(Enum):
    DATE = "date"           # Date range filters
    AMOUNT = "amount"       # Numeric range filters  
    SEARCH = "search"       # Text search filters
    SELECTION = "selection" # Dropdown filters
    RELATIONSHIP = "relationship"  # Foreign key filters
```

### Category-Based Processing

```python
# Each category has specialized processing:
DATE: {
    'presets': ['today', 'this_week', 'this_month', 'financial_year'],
    'range_support': True,
    'operators': ['on_or_before', 'on_or_after', 'between']
}

SEARCH: {
    'case_sensitive': False,
    'min_length': 2,
    'operators': ['contains', 'starts_with', 'ends_with']
}

SELECTION: {
    'multiple': True,
    'empty_means_all': True,
    'operators': ['equals', 'in', 'not_in']
}
```

---

## Caching Strategy

### Service Method Caching

```python
from app.utils.cache_decorator import cache_service_method

@cache_service_method('entity_type', 'cache_key')
def expensive_calculation(self, **kwargs):
    """
    Cached for performance
    Cache key pattern: {entity_type}:{cache_key}:{param_hash}
    """
    # Complex calculation here
    return result
```

### Cache Invalidation

```python
def after_update(self, entity, **kwargs):
    """Invalidate relevant caches after update"""
    from app.utils.cache import cache_manager
    cache_manager.delete_pattern(f'{self.entity_type}:*:{entity.id}:*')
```

---

## Database Design

### Using Views for Complex Data

```sql
-- Use views for denormalized/aggregated data
CREATE VIEW supplier_payments_view AS
SELECT 
    p.*,
    s.supplier_name,
    -- Pre-calculate breakdown columns for summary cards
    CASE WHEN payment_method = 'cash' THEN payment_amount ELSE 0 END as cash_amount,
    CASE WHEN payment_method = 'cheque' THEN payment_amount ELSE 0 END as cheque_amount,
    CASE WHEN payment_method = 'bank_transfer' THEN payment_amount ELSE 0 END as bank_transfer_amount,
    CASE WHEN payment_method = 'upi' THEN payment_amount ELSE 0 END as upi_amount
FROM supplier_payments p
LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id;
```

### Model Definition

```python
class EntityView(Base):
    """
    View-based model for denormalized data
    """
    __tablename__ = 'entity_view'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view
    
    # Primary key (required even for views)
    entity_id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Denormalized fields (no relationships needed)
    supplier_name = Column(String(200))
    
    # Pre-calculated fields for summary cards
    cash_amount = Column(Numeric(12, 2))
    cheque_amount = Column(Numeric(12, 2))
```

---

## Best Practices

### ✅ DO:
1. **Use hidden cards for filtered aggregations** - Better performance
2. **Use direct DB columns when possible** - Simplest approach
3. **Create database views for complex joins** - Pre-calculate at DB level
4. **Cache expensive operations** - Use @cache_service_method
5. **Let Universal Engine optimize queries** - It's smarter than manual SQL
6. **Keep calculations in configuration** - Easier to maintain
7. **Use db_column mapping for legacy databases** - Map to existing columns
8. **Test with realistic data volumes** - Performance matters

### ❌ DON'T:
1. **Don't override calculate_summary_fields for simple aggregations** - Use hidden cards
2. **Don't write multiple queries** - Universal Engine combines them
3. **Don't calculate in Python what SQL can do** - Database is faster
4. **Don't mix patterns** - Be consistent within an entity
5. **Don't forget error handling** - Return safe defaults
6. **Don't bypass the framework** - Work with it, not against it
7. **Don't ignore caching** - It's essential for performance

---

## Configuration vs Code

### Decision Matrix

| Use Configuration | Use Code (Hooks) |
|-------------------|------------------|
| Simple SUM, COUNT, AVG | Complex business rules |
| Status filtering | External API calls |
| Date range calculations | Multi-step calculations |
| Field visibility | Conditional logic |
| Basic relationships | Recursive operations |
| Filtered aggregations (hidden cards) | Weighted calculations |
| Standard CRUD | Custom workflows |

---

## Complete Examples

### Example 1: Payment Service with Breakdown (Configuration Only)

```python
# Configuration (supplier_payment_config.py)
SUPPLIER_PAYMENT_SUMMARY_CARDS = [
    # Visible total
    {"id": "total", "field": "payment_amount", "type": "currency", "visible": True},
    
    # Hidden calculation cards for breakdown
    {"id": "cash_sum", "field": "cash_amount", "type": "currency", "visible": False},
    {"id": "cheque_sum", "field": "cheque_amount", "type": "currency", "visible": False},
    {"id": "bank_sum", "field": "bank_transfer_amount", "type": "currency", "visible": False},
    {"id": "upi_sum", "field": "upi_amount", "type": "currency", "visible": False},
    
    # Detail card showing breakdown
    {
        "id": "payment_breakdown",
        "label": "Payment Methods",
        "type": "detail",
        "card_type": "detail",
        "visible": True,
        "breakdown_fields": {
            "cash_sum": {"label": "Cash", "icon": "fas fa-money-bill"},
            "cheque_sum": {"label": "Cheque", "icon": "fas fa-money-check"},
            "bank_sum": {"label": "Bank", "icon": "fas fa-university"},
            "upi_sum": {"label": "UPI", "icon": "fas fa-mobile"}
        }
    }
]

# Service (supplier_payment_service.py)
class SupplierPaymentService(UniversalEntityService):
    def __init__(self):
        super().__init__('supplier_payments')
    # No override needed! Configuration handles everything
```

### Example 2: Invoice Service with Status Filtering

```python
# Configuration only - no service override!
SUPPLIER_INVOICE_SUMMARY_CARDS = [
    # Direct aggregations
    {"id": "total", "field": "invoice_total_amount", "type": "currency", "visible": True},
    
    # Hidden cards for filtered sums
    {"id": "pending_calc", "field": "invoice_total_amount", "type": "currency",
     "visible": False, "filter_condition": {"payment_status": ["pending", "partial"]}},
    
    {"id": "overdue_calc", "field": "invoice_total_amount", "type": "currency",
     "visible": False, "filter_condition": {"payment_status": "overdue"}},
    
    # Visible cards referencing calculations
    {"id": "pending", "field": "pending_calc", "label": "Pending", "visible": True},
    {"id": "overdue", "field": "overdue_calc", "label": "Overdue", "visible": True}
]
```

---

## Advanced Patterns

### Aggregation Pattern

```python
def get_payment_summary(self, item_id: str = None, **kwargs) -> Dict:
    """Calculate payment summary across multiple invoices"""
    
    with get_db_session() as session:
        # Use SQL aggregation for performance
        result = session.query(
            func.count(Payment.payment_id).label('count'),
            func.sum(Payment.amount).label('total'),
            func.avg(Payment.amount).label('average'),
            func.max(Payment.payment_date).label('latest')
        ).filter(
            Payment.supplier_id == item_id
        ).first()
        
        return {
            'summary': {
                'payment_count': result.count or 0,
                'total_paid': float(result.total or 0),
                'average_payment': float(result.average or 0),
                'last_payment_date': result.latest
            },
            'has_payments': result.count > 0
        }
```

### Hierarchical Data Pattern

```python
def get_category_tree(self, parent_id: Optional[str] = None, **kwargs) -> List[Dict]:
    """Build hierarchical category structure"""
    
    with get_db_session() as session:
        categories = session.query(Category).filter(
            Category.parent_id == parent_id
        ).order_by(Category.name).all()
        
        result = []
        for category in categories:
            cat_dict = get_entity_dict(category)
            cat_dict['children'] = self.get_category_tree(category.id)
            result.append(cat_dict)
        
        return result
```

---

## Troubleshooting

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Virtual field not showing | `virtual=True` not set | Ensure virtual flag and implement `_add_virtual_calculations()` |
| Custom renderer not working | Method name mismatch | Check `context_function` matches service method exactly |
| Detail card blank | Hidden cards missing | Define hidden calculation cards with correct field names |
| Summary shows zero | Using calculated field without hidden card | Use DB column or hidden card pattern |
| Summary wrong after filter | Override not using filtered query | Remove override, use hidden cards |
| Slow performance | Multiple queries | Use configuration-only approach |
| Service not loading | Registration missing | Check `entity_registry.py` has correct service_class path |
| Filter not working | Category not mapped | Add to `filter_category_mapping` |
| Cache not invalidating | Pattern mismatch | Check cache key patterns |

### Debug Checklist

- [ ] Entity registered in `entity_registry.py` with correct paths
- [ ] Service class inherits from `UniversalEntityService`
- [ ] Database view exists if using complex data
- [ ] Field names in config match database columns or use `db_column` mapping
- [ ] Hidden cards have `visible: False`
- [ ] Visible cards reference hidden card IDs correctly
- [ ] Custom renderer methods return correct data structure
- [ ] Virtual fields marked with `virtual=True`
- [ ] Summary cards configuration includes hidden calculation cards
- [ ] Cache decorators used for expensive operations
- [ ] Filter category mapping defined in config
- [ ] Error handling returns safe defaults

### Performance Monitoring

```python
# Enable SQL logging to see generated queries
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Add timing to service methods
import time
def timed_method(self, **kwargs):
    start = time.time()
    result = self.expensive_operation(**kwargs)
    logger.info(f"Operation took {time.time() - start:.2f}s")
    return result
```

---

## Migration Guide

### Migrating from Override to Configuration

#### Step 1: Analyze Current Override
```python
# OLD: Service with override
def calculate_summary_fields(self, ...):
    summary['pending'] = query.filter(status='pending').sum()
    summary['overdue'] = query.filter(status='overdue').sum()
    return summary
```

#### Step 2: Convert to Hidden Cards
```python
# NEW: Configuration only
SUMMARY_CARDS = [
    # Hidden calculations
    {"id": "pending_calc", "field": "amount", "type": "currency",
     "visible": False, "filter_condition": {"status": "pending"}},
    {"id": "overdue_calc", "field": "amount", "type": "currency",
     "visible": False, "filter_condition": {"status": "overdue"}},
    
    # Visible references
    {"id": "pending", "field": "pending_calc", "label": "Pending", "visible": True},
    {"id": "overdue", "field": "overdue_calc", "label": "Overdue", "visible": True}
]
```

#### Step 3: Remove Override
```python
# DELETE the calculate_summary_fields method entirely!
```

#### Step 4: Test and Verify
1. Check summary values match
2. Monitor query performance
3. Verify filters still work
4. Test with large datasets

### When to Keep Overrides

Keep overrides ONLY for:
1. **External API calls** - Getting exchange rates, credit scores
2. **Complex algorithms** - Risk calculations, ML predictions
3. **Multi-entity aggregations** - Combining data from multiple sources
4. **Recursive calculations** - Hierarchical rollups
5. **Time-sensitive data** - Real-time stock prices

---

## Summary

The Universal Engine provides a powerful, configuration-driven approach that eliminates most custom code needs. The discovery of the hidden card pattern with `filter_condition` is a game-changer that:

- **Improves performance** by 4x or more
- **Reduces code** to zero for most aggregations
- **Simplifies maintenance** to configuration changes
- **Ensures consistency** across all entities

**Remember: If you're writing a service override for simple aggregations, you're probably doing it wrong. Use hidden cards instead!**

### Quick Reference

| Pattern | Use Case | Performance | Maintenance |
|---------|----------|-------------|-------------|
| Direct Column | Simple sum/count | Excellent | None |
| Hidden Card | Filtered aggregation | Excellent | Configuration only |
| Service Override | Complex logic | Variable | High |

**Default to configuration. Override only when absolutely necessary.**