# Custom Renderer Implementation Complete Guide

## Table of Contents
1. [Business Purpose & Use Cases](#business-purpose--use-cases)
2. [Architecture Overview](#architecture-overview)
3. [Configuration Guide](#configuration-guide)
4. [Service Method Implementation](#service-method-implementation)
5. [Template Integration](#template-integration)
6. [Real-World Examples](#real-world-examples)
7. [Troubleshooting](#troubleshooting)

---

## Business Purpose & Use Cases

### What are Custom Renderers?
Custom renderers allow fields to display complex, dynamic content that goes beyond simple value display. They enable:
- **Dynamic data fetching** from multiple sources
- **Complex visualizations** (tables, charts, timelines)
- **Aggregated information** (summaries, calculations)
- **Interactive components** (expandable sections, modals)

### Common Business Use Cases

#### 1. **Master-Detail Display**
**Purpose:** Show related line items within a parent record
```
Example: Display all purchase order line items within the PO detail view
Business Value: Users see complete information without navigation
```

#### 2. **Transaction History**
**Purpose:** Show historical transactions related to an entity
```
Example: 6-month payment history for a supplier
Business Value: Quick financial overview for decision making
```

#### 3. **Workflow Visualization**
**Purpose:** Display process status and history
```
Example: Approval workflow timeline for payments
Business Value: Clear visibility of process bottlenecks
```

#### 4. **Aggregated Summaries**
**Purpose:** Calculate and display summary information
```
Example: Outstanding balance across all supplier invoices
Business Value: Instant financial position awareness
```

#### 5. **Cross-Entity Data**
**Purpose:** Combine data from multiple entities
```
Example: Show invoices and payments for a purchase order
Business Value: Complete transaction trail in one view
```

---

## Architecture Overview

### Data Flow
```
Configuration → Data Assembler → Service Method → Template → Display
     ↓              ↓                ↓              ↓          ↓
  Define field   Detect renderer  Fetch data   Format HTML  User sees
```

### Components

1. **Configuration (Python)**
   - Defines field with CustomRenderer
   - Specifies template and context function

2. **Data Assembler (Python)**
   - Detects custom renderer fields
   - Extracts configuration for template

3. **Service Method (Python)**
   - Fetches and processes data
   - Returns structured data dict

4. **Template (Jinja2/HTML)**
   - Calls service method
   - Renders data using specified template

---

## Configuration Guide

### Step 1: Import Required Classes
```python
from app.config.core_definitions import (
    FieldDefinition, 
    FieldType, 
    CustomRenderer
)
```

### Step 2: Define Custom Renderer Field
```python
FieldDefinition(
    name="po_line_items_display",           # Unique field identifier
    label="Purchase Order Items",           # Display label
    field_type=FieldType.CUSTOM,           # Must be CUSTOM type
    
    # Display control
    show_in_list=False,                    # Not in list view
    show_in_detail=True,                   # Show in detail view
    show_in_form=False,                    # Not in forms
    readonly=True,                          # Display only
    virtual=True,                           # Not stored in DB
    
    # Layout configuration
    tab_group="line_items",                 # Tab placement
    section="items_display",                # Section within tab
    view_order=10,                          # Display order
    
    # Custom Renderer Configuration
    custom_renderer=CustomRenderer(
        template="components/business/po_items_table.html",
        context_function="get_po_line_items_display",
        css_classes="table-responsive po-items-table"
    )
)
```

### Configuration Parameters Explained

#### CustomRenderer Parameters
| Parameter | Purpose | Required | Example |
|-----------|---------|----------|---------|
| `template` | Path to HTML template | Yes | `"components/business/table.html"` |
| `context_function` | Service method name | Yes | `"get_payment_history"` |
| `css_classes` | Additional CSS classes | No | `"table-responsive striped"` |
| `javascript` | Associated JS function | No | `"initDataTable"` |

#### Field Parameters for Custom Renderers
| Parameter | Recommended Value | Why |
|-----------|------------------|-----|
| `field_type` | `FieldType.CUSTOM` | Identifies as custom renderer |
| `virtual` | `True` | Data not stored in database |
| `readonly` | `True` | Display only, not editable |
| `show_in_form` | `False` | Custom renderers are for display |

---

## Service Method Implementation

### Method Signature
```python
def get_[context_function_name](self, 
                                item_id: str = None, 
                                item: dict = None, 
                                hospital_id: str = None,
                                branch_id: str = None,
                                **kwargs) -> Dict:
    """
    Fetch and prepare data for custom renderer
    
    Args:
        item_id: Primary key of current entity
        item: Current entity data dict
        hospital_id: Current hospital context
        branch_id: Current branch context
        **kwargs: Additional parameters
        
    Returns:
        Dict with data for template
    """
```

### Basic Implementation Pattern
```python
def get_po_line_items_display(self, item_id: str = None, 
                              item: dict = None, **kwargs) -> Dict:
    """Get purchase order line items for display"""
    try:
        # 1. Get the ID to work with
        po_id = None
        if item and isinstance(item, dict):
            po_id = item.get('po_id')
        elif item_id:
            po_id = item_id
            
        if not po_id:
            return self._empty_result()
        
        # 2. Convert to proper type if needed
        if isinstance(po_id, str):
            po_id = uuid.UUID(po_id)
        
        # 3. Fetch data from database
        with get_db_session() as session:
            # Main entity
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=po_id
            ).first()
            
            if not po:
                return self._empty_result()
            
            # Related data
            lines = session.query(PurchaseOrderLine).filter_by(
                po_id=po_id
            ).order_by(PurchaseOrderLine.line_number).all()
            
            # 4. Process and format data
            items = []
            total_amount = 0
            total_gst = 0
            
            for line in lines:
                item_dict = {
                    'line_number': line.line_number,
                    'item_name': line.medicine_name,
                    'hsn_code': line.hsn_code or '-',
                    'quantity': float(line.units or 0),
                    'unit_price': float(line.pack_purchase_price or 0),
                    'gst_rate': float(line.gst_rate or 0),
                    'gst_amount': float(line.total_gst or 0),
                    'total_amount': float(line.line_total or 0)
                }
                items.append(item_dict)
                total_amount += item_dict['total_amount']
                total_gst += item_dict['gst_amount']
            
            # 5. Return structured data
            return {
                'items': items,                    # Main data
                'has_items': bool(items),          # Control flag
                'currency_symbol': '₹',            # Display config
                'summary': {                       # Aggregated data
                    'total_items': len(items),
                    'total_amount': total_amount,
                    'total_gst': total_gst,
                    'subtotal': total_amount - total_gst
                },
                'metadata': {                      # Additional info
                    'po_number': po.po_number,
                    'po_date': po.po_date,
                    'status': po.status
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting PO line items: {str(e)}")
        return self._error_result(str(e))
    
def _empty_result(self) -> Dict:
    """Standard empty result structure"""
    return {
        'items': [],
        'has_items': False,
        'summary': {},
        'metadata': {}
    }

def _error_result(self, error: str) -> Dict:
    """Standard error result structure"""
    return {
        'items': [],
        'has_error': True,
        'error_message': error,
        'summary': {},
        'metadata': {}
    }
```

### Advanced Patterns

#### 1. **Aggregation Pattern**
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

#### 2. **Time-Based Pattern**
```python
def get_payment_history_6months(self, item_id: str = None, **kwargs) -> Dict:
    """Get 6 months payment history"""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    with get_db_session() as session:
        payments = session.query(Payment).filter(
            Payment.supplier_id == item_id,
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).order_by(desc(Payment.payment_date)).all()
        
        # Group by month for visualization
        monthly_data = {}
        for payment in payments:
            month_key = payment.payment_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': payment.payment_date.strftime('%B %Y'),
                    'payments': [],
                    'total': 0
                }
            
            monthly_data[month_key]['payments'].append({
                'date': payment.payment_date,
                'amount': float(payment.amount),
                'reference': payment.payment_number
            })
            monthly_data[month_key]['total'] += float(payment.amount)
        
        return {
            'monthly_data': list(monthly_data.values()),
            'has_history': bool(monthly_data),
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
```

#### 3. **Cross-Entity Pattern**
```python
def get_po_financial_summary(self, item_id: str = None, **kwargs) -> Dict:
    """Combine PO, Invoice, and Payment data"""
    
    with get_db_session() as session:
        # Get PO
        po = session.query(PurchaseOrder).get(item_id)
        
        # Get related invoices
        invoices = session.query(Invoice).filter_by(
            po_id=item_id
        ).all()
        
        # Get payments through invoices
        invoice_ids = [inv.invoice_id for inv in invoices]
        payments = session.query(Payment).filter(
            Payment.invoice_id.in_(invoice_ids)
        ).all() if invoice_ids else []
        
        # Calculate summaries
        po_amount = float(po.total_amount or 0)
        invoiced_amount = sum(float(inv.total_amount or 0) for inv in invoices)
        paid_amount = sum(float(pay.amount or 0) for pay in payments)
        
        return {
            'po_summary': {
                'number': po.po_number,
                'amount': po_amount,
                'status': po.status
            },
            'invoice_summary': {
                'count': len(invoices),
                'total': invoiced_amount,
                'pending': invoiced_amount - paid_amount
            },
            'payment_summary': {
                'count': len(payments),
                'total': paid_amount,
                'outstanding': po_amount - paid_amount
            },
            'has_financials': bool(invoices or payments)
        }
```

---

## Template Integration

### Basic Template Structure
```html
<!-- components/business/po_items_table.html -->
{% if data.has_items %}
<div class="po-items-container {{ data.css_classes }}">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>#</th>
                <th>Item</th>
                <th>HSN</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>GST</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data.items %}
            <tr>
                <td>{{ item.line_number }}</td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.hsn_code }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ data.currency_symbol }}{{ item.unit_price|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ item.gst_amount|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ item.total_amount|format_number }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr class="font-weight-bold">
                <td colspan="5">Total</td>
                <td>{{ data.currency_symbol }}{{ data.summary.total_gst|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ data.summary.total_amount|format_number }}</td>
            </tr>
        </tfoot>
    </table>
</div>
{% else %}
<div class="alert alert-info">
    <i class="fas fa-info-circle"></i> No items found
</div>
{% endif %}
```

### Advanced Template Patterns

#### 1. **Conditional Display**
```html
{% if data.has_error %}
    <div class="alert alert-danger">
        {{ data.error_message }}
    </div>
{% elif data.has_items %}
    <!-- Main content -->
{% else %}
    <div class="text-muted">No data available</div>
{% endif %}
```

#### 2. **Nested Data Display**
```html
{% for month in data.monthly_data %}
<div class="month-section">
    <h5>{{ month.month }}</h5>
    <table class="table">
        {% for payment in month.payments %}
        <tr>
            <td>{{ payment.date|format_date }}</td>
            <td>{{ payment.reference }}</td>
            <td class="text-right">{{ payment.amount|format_currency }}</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
            <td colspan="2">Monthly Total</td>
            <td class="text-right font-weight-bold">
                {{ month.total|format_currency }}
            </td>
        </tr>
    </table>
</div>
{% endfor %}
```

#### 3. **Interactive Elements**
```html
<div class="expandable-section">
    {% for item in data.items %}
    <div class="item-row" onclick="toggleDetails('{{ item.id }}')">
        <span>{{ item.name }}</span>
        <span class="badge">{{ item.count }}</span>
    </div>
    <div id="details-{{ item.id }}" class="item-details" style="display:none;">
        <!-- Detailed information -->
    </div>
    {% endfor %}
</div>

<script>
function toggleDetails(id) {
    var details = document.getElementById('details-' + id);
    details.style.display = details.style.display === 'none' ? 'block' : 'none';
}
</script>
```

---

## Real-World Examples

### Example 1: Purchase Order Line Items

**Business Need:** Display all items in a purchase order with totals

**Configuration:**
```python
FieldDefinition(
    name="po_line_items_display",
    label="Order Items",
    field_type=FieldType.CUSTOM,
    virtual=True,
    show_in_detail=True,
    tab_group="items",
    custom_renderer=CustomRenderer(
        template="components/business/po_items_table.html",
        context_function="get_po_line_items_display",
        css_classes="table-responsive"
    )
)
```

**Service Method:**
```python
def get_po_line_items_display(self, item_id=None, item=None, **kwargs):
    po_id = item.get('po_id') if item else item_id
    
    with get_db_session() as session:
        lines = session.query(POLine).filter_by(po_id=po_id).all()
        
        items = []
        for line in lines:
            items.append({
                'product': line.product_name,
                'quantity': line.quantity,
                'price': line.unit_price,
                'total': line.quantity * line.unit_price
            })
        
        return {
            'items': items,
            'has_items': bool(items),
            'total': sum(i['total'] for i in items)
        }
```

### Example 2: Payment History Timeline

**Business Need:** Show payment history as a timeline

**Configuration:**
```python
FieldDefinition(
    name="payment_timeline",
    label="Payment Timeline",
    field_type=FieldType.CUSTOM,
    virtual=True,
    custom_renderer=CustomRenderer(
        template="components/timeline.html",
        context_function="get_payment_timeline",
        css_classes="timeline-vertical"
    )
)
```

**Service Method:**
```python
def get_payment_timeline(self, item_id=None, **kwargs):
    with get_db_session() as session:
        payments = session.query(Payment).filter_by(
            supplier_id=item_id
        ).order_by(desc(Payment.date)).limit(10).all()
        
        timeline_events = []
        for payment in payments:
            timeline_events.append({
                'date': payment.date,
                'title': f'Payment #{payment.number}',
                'amount': payment.amount,
                'status': payment.status,
                'icon': 'fa-check' if payment.status == 'completed' else 'fa-clock',
                'color': 'success' if payment.status == 'completed' else 'warning'
            })
        
        return {
            'events': timeline_events,
            'has_events': bool(timeline_events)
        }
```

### Example 3: Summary Cards

**Business Need:** Display key metrics as cards

**Configuration:**
```python
FieldDefinition(
    name="supplier_metrics",
    label="Key Metrics",
    field_type=FieldType.CUSTOM,
    virtual=True,
    custom_renderer=CustomRenderer(
        template="components/metric_cards.html",
        context_function="get_supplier_metrics"
    )
)
```

**Service Method:**
```python
def get_supplier_metrics(self, item_id=None, **kwargs):
    with get_db_session() as session:
        # Various calculations
        metrics = {
            'total_orders': session.query(Order).filter_by(supplier_id=item_id).count(),
            'pending_amount': session.query(func.sum(Invoice.amount)).filter_by(
                supplier_id=item_id, status='pending'
            ).scalar() or 0,
            'last_order_date': session.query(func.max(Order.date)).filter_by(
                supplier_id=item_id
            ).scalar()
        }
        
        return {
            'metrics': [
                {
                    'label': 'Total Orders',
                    'value': metrics['total_orders'],
                    'icon': 'fa-shopping-cart',
                    'color': 'primary'
                },
                {
                    'label': 'Pending Amount',
                    'value': f"₹{metrics['pending_amount']:,.2f}",
                    'icon': 'fa-rupee-sign',
                    'color': 'warning'
                },
                {
                    'label': 'Last Order',
                    'value': metrics['last_order_date'].strftime('%d %b %Y') if metrics['last_order_date'] else 'Never',
                    'icon': 'fa-calendar',
                    'color': 'info'
                }
            ]
        }
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. **Context Function Not Found**
**Error:** `Unknown context function: get_po_items`

**Causes:**
- Method doesn't exist in service
- Method name mismatch
- Service not properly initialized

**Solution:**
```python
# Verify method exists
class PurchaseOrderService(UniversalEntityService):
    def get_po_items(self, item_id=None, item=None, **kwargs):
        # Implementation
        pass
```

#### 2. **Template Not Found**
**Error:** `Template 'components/table.html' not found`

**Causes:**
- Wrong path in configuration
- Template file doesn't exist

**Solution:**
```python
# Check template path
custom_renderer=CustomRenderer(
    template="components/business/table.html"  # Full path from templates/
)
```

#### 3. **No Data Displayed**
**Symptom:** Custom renderer area is blank

**Debug Steps:**
```python
# 1. Add logging to service method
def get_data(self, item_id=None, **kwargs):
    logger.info(f"get_data called with item_id={item_id}")
    result = {...}
    logger.info(f"Returning: {result}")
    return result

# 2. Check template receives data
<!-- In template -->
<div>Debug: {{ data|tojson }}</div>

# 3. Verify configuration
print(field.custom_renderer.context_function)  # Should match method name
```

#### 4. **Performance Issues**
**Symptom:** Slow page load with custom renderers

**Solutions:**
```python
# 1. Use eager loading
query = query.options(joinedload(Model.relationship))

# 2. Limit data
items = query.limit(100).all()

# 3. Cache results
@cache_service_method('entity', 'method')
def get_data(self, ...):
    pass

# 4. Use pagination
def get_data(self, page=1, per_page=20, **kwargs):
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
```

### Debug Checklist

- [ ] Configuration has correct `context_function` name
- [ ] Service method exists with exact name match
- [ ] Service method returns dict (not None)
- [ ] Template file exists at specified path
- [ ] Template handles empty data case
- [ ] Field has `virtual=True` for calculated data
- [ ] Field has `show_in_detail=True` to appear
- [ ] No Python errors in service method
- [ ] No template syntax errors

### Testing Custom Renderers

```python
# Test service method directly
from app.services.purchase_order_service import PurchaseOrderService

service = PurchaseOrderService()
result = service.get_po_line_items_display(
    item_id='test-id',
    item={'po_id': 'test-id'}
)

print("Result keys:", result.keys())
print("Has items:", result.get('has_items'))
print("Item count:", len(result.get('items', [])))
```

---

## Best Practices

### Do's
- ✅ Return consistent data structure
- ✅ Handle empty/null cases
- ✅ Include control flags (has_data, has_error)
- ✅ Use database sessions efficiently
- ✅ Format data in service, not template
- ✅ Log errors with context
- ✅ Cache expensive operations

### Don'ts
- ❌ Don't return None (return empty dict)
- ❌ Don't do complex logic in templates
- ❌ Don't fetch unnecessary data
- ❌ Don't hardcode entity IDs
- ❌ Don't forget error handling
- ❌ Don't mix presentation logic in service

### Performance Guidelines
1. **Limit data fetched** - Use pagination/limits
2. **Use joins wisely** - Avoid N+1 queries
3. **Cache when possible** - Especially for summaries
4. **Aggregate in database** - Use SQL functions
5. **Lazy load relationships** - Unless needed immediately

---

## Summary

Custom renderers provide a powerful way to display complex, dynamic data in your application. By following this guide:

1. **Configure** fields with CustomRenderer
2. **Implement** service methods to fetch data
3. **Create** templates to display data
4. **Test** thoroughly with various data scenarios

The system is designed to be:
- **Flexible** - Any data structure supported
- **Reusable** - Templates can be shared
- **Maintainable** - Clear separation of concerns
- **Performant** - With proper optimization

Remember: Custom renderers are for **display only**. For data entry, use standard form fields.