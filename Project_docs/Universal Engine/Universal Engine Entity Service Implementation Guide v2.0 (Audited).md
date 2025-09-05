# Universal Engine Entity Service Implementation Guide v2.0 (Audited)

## Table of Contents
1. [Overview](#overview)
2. [Core Architecture](#core-architecture)
3. [Entity Service Implementation](#entity-service-implementation)
4. [Configuration Patterns](#configuration-patterns)
5. [Virtual Fields & Custom Renderers](#virtual-fields--custom-renderers)
6. [Summary Cards & Calculations](#summary-cards--calculations)
7. [Service Template](#service-template)
8. [Complete Examples](#complete-examples)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Universal Engine is a **Configuration-Driven Architecture** that minimizes code duplication by defining entity behavior through configuration rather than custom code. Entity services should contain only business logic that cannot be expressed through configuration.

### Core Principles

1. **Configuration First** - Define behavior in configuration files
2. **Don't Override Core Methods** - Use provided hooks and patterns
3. **Database Views for Complex Data** - Use views for denormalized/calculated columns
4. **Minimal Service Code** - Only implement entity-specific business logic
5. **Cache Everything** - Use caching decorators for expensive operations

### Architecture Flow

```
Request → Universal Engine → Configuration → Service Hooks → Response
                ↓                               ↓
         Standard CRUD                  Custom Logic
         Filter/Sort/Page               Virtual Fields
         Summary Calc                   Custom Renderers
```

---

## Core Architecture

### Universal Engine Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `UniversalEntityService` | Base service class | `app/engine/universal_entity_service.py` |
| `EntityConfiguration` | Entity definition | `app/config/modules/{entity}_config.py` |
| `DataAssembler` | View/List data assembly | `app/engine/data_assembler.py` |
| `CategorizedFilterProcessor` | Query filtering | `app/engine/categorized_filter_processor.py` |
| `UniversalViews` | Route handlers | `app/views/universal_views.py` |
| `UniversalServiceRegistry` | Service management | `app/engine/universal_services.py` |

### Data Flow

1. **List View**: `search_data()` → `_calculate_summary()` → `DataAssembler` → Template
2. **Detail View**: `get_by_id()` → `_add_virtual_calculations()` → `DataAssembler` → Template
3. **Custom Fields**: Configuration → `custom_renderer` → Service method → Template

---

## Entity Service Implementation

### Service Class Structure

```python
class {EntityName}Service(UniversalEntityService):
    """
    Service for {entity} following Universal Engine patterns
    Inherits all standard CRUD from UniversalEntityService
    """
    
    def __init__(self):
        # Initialize with entity type matching configuration
        super().__init__('{entity_type}')  # e.g., 'supplier_payments'
    
    # Hook Methods (called by Universal Engine)
    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict
    def calculate_summary_fields(self, session: Session, filtered_query, 
                                summary: Dict, config, filters: Dict, **kwargs) -> Dict
    def get_{field_name}_display(self, item_id=None, item=None, **kwargs) -> Dict
    
    # Business Logic Methods (called by controllers/views)
    def process_{action}(self, entity_id: UUID, **params) -> Dict
```

### Available Hook Methods

| Method | Called By | When | Purpose |
|--------|-----------|------|---------|
| `_add_virtual_calculations()` | `get_by_id()` | Detail view load | Add calculated fields to detail data |
| `calculate_summary_fields()` | `_calculate_summary()` | After config calculations | Complex summary calculations |
| `get_{field}_display()` | Template via `attribute()` | Custom field rendering | Provide data for custom renderer |
| `_add_relationships()` | `search_data()` & `get_by_id()` | After data fetch | Load foreign key relationships |

**IMPORTANT**: The `calculate_summary_fields()` method receives:
- `session`: Active database session
- `filtered_query`: Query with all filters applied (full dataset, no pagination)
- `summary`: Current summary dict with config-based calculations
- `config`: Entity configuration object
- `filters`: Applied filters dictionary
- `hospital_id`, `branch_id`: Context parameters

### Methods You Should NOT Override

- `search_data()` - Use hooks or configuration instead
- `get_by_id()` - Use `_add_virtual_calculations()` hook
- `_calculate_summary()` - Use `calculate_summary_fields()` hook or config
- `create()`, `update()`, `delete()` - Unless special validation needed

---

## Configuration Patterns

### Entity Configuration Structure

```python
# app/config/modules/{entity_name}_config.py

from app.config.core_definitions import (
    FieldDefinition, FieldType, FilterOperator, 
    EntityConfiguration, ViewLayoutConfiguration,
    CustomRenderer, FilterCategory
)

# 1. Field Definitions
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

# 2. Summary Cards Configuration
{ENTITY}_SUMMARY_CARDS = [
    # Visible cards
    {
        "id": "total_count",
        "field": "total_count",
        "label": "Total",
        "icon": "fas fa-list",
        "type": "number",
        "visible": True
    },
    
    # Hidden calculation cards (for breakdowns)
    {
        "id": "cash_sum",
        "field": "cash_amount",     # Database column
        "type": "currency",          # Triggers SUM
        "visible": False            # Hidden, just for calculation
    },
    
    # Detail card (shows breakdown)
    {
        "id": "payment_breakdown",
        "label": "Payment Breakdown",
        "type": "detail",
        "card_type": "detail",      # Special rendering
        "visible": True,
        "breakdown_fields": {
            "cash_amount": {        # Must match hidden card field
                "label": "Cash",
                "icon": "fas fa-dollar",
                "color": "text-green-600"
            }
        }
    }
]

# 3. Filter Category Mapping
{ENTITY}_FILTER_CATEGORY_MAPPING = {
    "status": FilterCategory.ENUM,
    "supplier_id": FilterCategory.UUID,
    "payment_date": FilterCategory.DATE,
    "amount": FilterCategory.NUMERIC
}

# 4. Main Configuration
{ENTITY}_CONFIG = EntityConfiguration(
    entity_type="{entity_type}",
    model_class="app.models.views.{Entity}View",  # String path to model
    primary_key="{entity}_id",
    title_field="name",
    fields={ENTITY}_FIELDS,
    summary_cards={ENTITY}_SUMMARY_CARDS,
    view_layout=ViewLayoutConfiguration(
        type=LayoutType.TABBED,
        tabs={...}
    )
)

# 5. Module Registration
def get_module_configs():
    return {'{entity_type}': {ENTITY}_CONFIG}

def get_module_filter_configs():
    return {'{entity_type}': {ENTITY}_FILTER_CATEGORY_MAPPING}
```

### Entity Registry Registration

```python
# app/config/entity_registry.py
from app.config.entity_registry import EntityRegistration, EntityCategory

ENTITY_REGISTRY = {
    '{entity_type}': EntityRegistration(
        category=EntityCategory.TRANSACTION,  # or MASTER
        module="app.config.modules.{entity}_config",
        service_class="app.services.{entity}_service.{Entity}Service",  # String path
        model_class="app.models.views.{Entity}View"  # String path
    )
}
```

---

## Virtual Fields & Custom Renderers

### Virtual Fields Pattern

Virtual fields are calculated at runtime and don't exist in the database.

#### Simple Virtual Field
```python
# Configuration
FieldDefinition(
    name="full_name",
    virtual=True,
    field_type=FieldType.TEXT,
    show_in_detail=True
)

# Service Implementation
def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
    """Called automatically for detail views"""
    result['full_name'] = f"{result.get('first_name')} {result.get('last_name')}"
    return result
```

#### Aggregated Virtual Field
```python
# Configuration
FieldDefinition(
    name="total_spent",
    virtual=True,
    field_type=FieldType.CURRENCY,
    show_in_detail=True
)

# Service Implementation  
def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
    hospital_id = kwargs.get('hospital_id')
    if not hospital_id or not item_id:
        return result
        
    with get_db_session() as session:
        total = session.query(func.sum(Payment.amount)).filter(
            Payment.customer_id == uuid.UUID(item_id),
            Payment.hospital_id == hospital_id
        ).scalar() or 0
        result['total_spent'] = float(total)
    return result
```

### Custom Renderer Pattern

Custom renderers allow complex display logic with custom templates.

#### Configuration
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

#### Service Method
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

## Summary Cards & Calculations

### Configuration-Driven Summary Calculations

The Universal Engine automatically calculates summary values based on configuration:

```python
# Hidden cards for automatic calculation
{
    "id": "cash_sum",
    "field": "cash_amount",  # Column to SUM
    "type": "currency",       # Triggers aggregation
    "visible": False         # Hidden from display
}
```

### Enhanced Summary Hook

For complex calculations beyond configuration:

```python
def calculate_summary_fields(self, session: Session, filtered_query,
                            summary: Dict, config, filters: Dict,
                            hospital_id: UUID, branch_id: Optional[UUID],
                            **kwargs) -> Dict:
    """
    Hook for complex summary calculations
    Called AFTER configuration-based calculations
    
    Args:
        session: Database session
        filtered_query: Query with all filters applied (full dataset)
        summary: Current summary with config calculations
        config: Entity configuration
        filters: Applied filters dict
        hospital_id, branch_id: Context
        
    Returns:
        Enhanced summary dict
    """
    # Example: Weighted average
    items = filtered_query.all()
    if items:
        weighted_sum = sum(item.amount * item.weight for item in items)
        total_weight = sum(item.weight for item in items)
        summary['weighted_avg'] = weighted_sum / total_weight if total_weight else 0
    
    return summary
```

---

## Service Template

### Complete Service Template

```python
# app/services/{entity}_service.py

"""
{Entity} Service - Universal Engine Implementation
"""

from typing import Dict, Optional, List
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.engine.universal_entity_service import UniversalEntityService
from app.models.views import {Entity}View  # Or model
from app.services.database_service import get_db_session, get_entity_dict
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class {Entity}Service(UniversalEntityService):
    """
    {Entity} service following Universal Engine patterns
    Most functionality inherited from UniversalEntityService
    """
    
    def __init__(self):
        # Initialize with entity type from configuration
        super().__init__('{entity_type}')
        
        # Ensure config is loaded if needed
        if not self.config:
            from app.config.modules.{entity}_config import {ENTITY}_CONFIG
            self.config = {ENTITY}_CONFIG
    
    # =========================================================================
    # HOOK: Virtual Field Calculations (Detail Views)
    # =========================================================================
    
    def _add_virtual_calculations(self, result: Dict, item_id: str, **kwargs) -> Dict:
        """
        Add calculated fields to detail view data
        Called automatically by parent's get_by_id()
        """
        hospital_id = kwargs.get('hospital_id')
        if not hospital_id or not item_id:
            return result
        
        try:
            entity_id = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
            
            with get_db_session() as session:
                # Add your calculations here
                pass
                
        except Exception as e:
            logger.error(f"Error in _add_virtual_calculations: {str(e)}")
        
        return result
    
    # =========================================================================
    # HOOK: Complex Summary Calculations (List Views)
    # =========================================================================
    
    def calculate_summary_fields(self, session: Session, filtered_query,
                                summary: Dict, config, filters: Dict,
                                hospital_id: UUID, branch_id: Optional[UUID],
                                **kwargs) -> Dict:
        """
        Optional hook for complex summary calculations
        Called after configuration-based summary calculations
        """
        # Add complex calculations here
        return summary
    
    # =========================================================================
    # Custom Renderer Methods
    # =========================================================================
    
    @cache_service_method('{entity_type}', 'field_display')
    def get_{field}_display(self, item_id=None, item=None, **kwargs) -> Dict:
        """
        Provide data for custom field renderer
        Called by template when rendering field with custom_renderer
        """
        # Return data structure for the template
        return {}
    
    # =========================================================================
    # Entity-Specific Operations
    # =========================================================================
    
    def process_{action}(self, entity_id: uuid.UUID, **params) -> Dict:
        """
        Custom business operation
        Called from controllers/views
        """
        try:
            with get_db_session() as session:
                # Your business logic here
                pass
                
        except Exception as e:
            logger.error(f"Error in process_{action}: {str(e)}")
            raise
```

---

## Complete Examples

### Example 1: Payment Service with Breakdown

```python
# Configuration (supplier_payment_config.py)
SUPPLIER_PAYMENT_SUMMARY_CARDS = [
    # Hidden calculation cards
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
        "card_type": "detail",
        "visible": True,
        "breakdown_fields": {
            "cash_amount": {"label": "Cash", "icon": "fas fa-money-bill"},
            "cheque_amount": {"label": "Cheque", "icon": "fas fa-money-check"},
            "bank_transfer_amount": {"label": "Bank", "icon": "fas fa-university"},
            "upi_amount": {"label": "UPI", "icon": "fas fa-mobile"}
        }
    }
]

# Service (supplier_payment_service.py)
class SupplierPaymentService(UniversalEntityService):
    def __init__(self):
        super().__init__('supplier_payments')
    
    # No override needed! Configuration handles the breakdown
```

---

## Best Practices

### 1. Database Design

```sql
-- Use views for complex/denormalized data
CREATE VIEW supplier_payments_view AS
SELECT 
    p.*,
    s.supplier_name,
    -- Pre-calculate breakdown columns
    CASE WHEN payment_method = 'cash' THEN payment_amount ELSE 0 END as cash_amount,
    CASE WHEN payment_method = 'cheque' THEN payment_amount ELSE 0 END as cheque_amount,
    CASE WHEN payment_method = 'bank_transfer' THEN payment_amount ELSE 0 END as bank_transfer_amount,
    CASE WHEN payment_method = 'upi' THEN payment_amount ELSE 0 END as upi_amount
FROM supplier_payments p
LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id;
```

### 2. Caching Strategy

```python
# Always cache expensive operations
@cache_service_method('entity_type', 'cache_key')
def expensive_calculation(self, **kwargs):
    # Complex calculation here
    pass
```

### 3. Error Handling

```python
def any_hook_method(self, **kwargs):
    try:
        # Your logic
        pass
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        # Return safe defaults
        return {...}
```

### 4. Configuration vs Code

| Use Configuration | Use Code (Hooks) |
|-------------------|------------------|
| Simple SUM, COUNT, AVG | Complex business rules |
| Status filtering | External API calls |
| Date range calculations | Multi-step calculations |
| Field visibility | Conditional logic |
| Basic relationships | Recursive operations |

---

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Virtual field not showing | Ensure `virtual=True` in config and implement `_add_virtual_calculations()` |
| Custom renderer not working | Check `context_function` matches service method name exactly |
| Detail card blank | Verify hidden summary cards defined with correct field names |
| Summary wrong after filter | Ensure not overriding `_calculate_summary()`, use `calculate_summary_fields()` hook instead |
| Slow performance | Add database view with pre-calculated columns |
| Service not loading | Check `entity_registry.py` has correct service_class string path |

### Debug Checklist

- [ ] Entity registered in `entity_registry.py` with correct paths
- [ ] Service class inherits from `UniversalEntityService`
- [ ] Database view exists if using complex data
- [ ] Field names in config match database columns or use `db_column` mapping
- [ ] Custom renderer methods return correct data structure
- [ ] Virtual fields marked with `virtual=True`
- [ ] Summary cards configuration includes hidden calculation cards
- [ ] Cache decorators used for expensive operations
- [ ] Filter category mapping defined in config

---

## Migration Guide

When migrating an existing entity to Universal Engine:

1. **Create Database View** (if needed)
   ```sql
   CREATE VIEW {entity}_view AS ...
   ```

2. **Define Configuration**
   ```python
   # app/config/modules/{entity}_config.py
   {ENTITY}_FIELDS = [...]
   {ENTITY}_SUMMARY_CARDS = [...]
   {ENTITY}_FILTER_CATEGORY_MAPPING = {...}
   {ENTITY}_CONFIG = EntityConfiguration(...)
   ```

3. **Create Minimal Service** (if custom logic needed)
   ```python
   # app/services/{entity}_service.py
   class {Entity}Service(UniversalEntityService):
       def __init__(self):
           super().__init__('{entity_type}')
   ```

4. **Register in Entity Registry**
   ```python
   # app/config/entity_registry.py
   ENTITY_REGISTRY['{entity_type}'] = EntityRegistration(
       category=EntityCategory.TRANSACTION,
       module="app.config.modules.{entity}_config",
       service_class="app.services.{entity}_service.{Entity}Service",
       model_class="app.models.views.{Entity}View"
   )
   ```

5. **Add Custom Logic** (only if needed)
   - Virtual fields in `_add_virtual_calculations()`
   - Complex summary in `calculate_summary_fields()`
   - Custom renderers as `get_{field}_display()`

6. **Test**
   - List view with filtering
   - Detail view with virtual fields
   - Summary calculations
   - Custom field rendering

---

## Key Differences from v1.0

1. **Entity Registry**: Now uses `EntityRegistration` dataclass with string paths
2. **Service Registry**: Managed by `UniversalServiceRegistry` with caching
3. **Filter Processor**: Changed from `FilterProcessor` to `CategorizedFilterProcessor`
4. **Field Types**: All field types now imported from `core_definitions.py`
5. **Filter Categories**: Must define `FILTER_CATEGORY_MAPPING` for proper filtering
6. **Model Paths**: All model/service references are string paths, not direct imports
7. **Config Loading**: Services can ensure config is loaded in `__init__`

---

*This guide represents the Universal Engine patterns as audited and verified against actual production code. Version 2.0 - December 2024*