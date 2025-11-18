# Invoice Line Item Status - Design Decision
**Date**: 2025-01-13
**Question**: Should we add a status field to invoice_line_item, or just use visual indicators?

## User's Question

> "We are not tracking status of invoice line item. Will it help to add status field to line item as well? Or we just mark the line with different color in patient invoice detailed view invoice line item table. It is more a visual indication."

## Recommendation: **Visual Indicator Only** ✅

### Do NOT add status field to invoice_line_item table

## Why NOT Add Status Field?

### 1. Violates Invoice Immutability Principle ❌

```python
# BAD: Modifying posted invoice line items
invoice_line_item.status = 'discontinued'  # ❌ Changes posted invoice!

# Problem: What if invoice was already:
# - Printed and given to patient?
# - Sent to insurance company?
# - Submitted for audit?
# - Archived for compliance?
```

**Accounting Rule**: Once invoice is posted, it should be immutable. Changes violate GAAP/IFRS.

### 2. Data Redundancy ❌

```python
# Status already exists in package_payment_plans
package_payment_plans.status = 'discontinued'  # ✅ Already tracked here!

# Adding to invoice_line_item creates:
invoice_line_item.status = 'discontinued'      # ❌ Duplicate!

# Now you have TWO sources of truth:
# - What if they get out of sync?
# - Which one is correct?
# - How do you maintain consistency?
```

### 3. Semantic Mismatch ❌

```python
# Consider a composite invoice:
Invoice #INV-001
├─ Line 1: Consultation Service  # ← What status? (No package plan)
├─ Line 2: Laser Package         # ← Can be discontinued (Has plan)
└─ Line 3: Medicine              # ← What status? (No package plan)

# Only PACKAGE line items can be discontinued
# Service and Medicine line items don't have plans
# So what would their status mean?
```

### 4. Breaks Normalized Design ❌

```
invoice_line_item (Base Transaction - Immutable)
  ↑ Should not know about
package_payment_plans (Business Logic - Mutable)
  ↑ Should control
Discontinuation Status
```

**Proper Design**: Status belongs to the business logic layer (plan), not the transaction layer (invoice).

## Best Practice: Computed Status + Visual Indicator ✅

### Option A: Query with Join (Recommended) ✅

**Backend Service Layer**:

```python
def get_invoice_line_items_with_status(invoice_id, hospital_id):
    """Get invoice line items with computed discontinuation status"""

    with get_db_session() as session:
        # Query with LEFT JOIN to get package plan status
        results = session.query(
            InvoiceLineItem,
            PackagePaymentPlan.status.label('package_plan_status'),
            PackagePaymentPlan.discontinued_at,
            PackagePaymentPlan.discontinuation_reason,
            PatientCreditNote.credit_note_number,
            PatientCreditNote.total_amount.label('refund_amount')
        ).outerjoin(
            PackagePaymentPlan,
            and_(
                InvoiceLineItem.invoice_id == PackagePaymentPlan.invoice_id,
                InvoiceLineItem.package_id == PackagePaymentPlan.package_id
            )
        ).outerjoin(
            PatientCreditNote,
            and_(
                PatientCreditNote.plan_id == PackagePaymentPlan.plan_id,
                PatientCreditNote.reason_code == 'plan_discontinued'
            )
        ).filter(
            InvoiceLineItem.invoice_id == invoice_id
        ).all()

        line_items = []
        for item, plan_status, discontinued_at, reason, cn_number, refund in results:
            item_dict = to_dict(item)

            # Compute status (not stored!)
            if plan_status == 'discontinued':
                item_dict['display_status'] = 'discontinued'
                item_dict['status_badge'] = 'warning'
                item_dict['status_text'] = 'Discontinued'
                item_dict['discontinuation_reason'] = reason
                item_dict['credit_note_number'] = cn_number
                item_dict['refund_amount'] = float(refund) if refund else 0
            elif plan_status == 'completed':
                item_dict['display_status'] = 'completed'
                item_dict['status_badge'] = 'success'
                item_dict['status_text'] = 'Completed'
            elif plan_status == 'active':
                item_dict['display_status'] = 'active'
                item_dict['status_badge'] = 'info'
                item_dict['status_text'] = 'Active'
            else:
                # Service or Medicine (no package plan)
                item_dict['display_status'] = 'active'
                item_dict['status_badge'] = 'secondary'
                item_dict['status_text'] = 'Active'

            line_items.append(item_dict)

        return line_items
```

**Frontend Template**:

```html
<!-- app/templates/billing/view_invoice.html -->
<table class="invoice-line-items-table">
    <thead>
        <tr>
            <th>Item</th>
            <th>Type</th>
            <th>Quantity</th>
            <th>Amount</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        {% for item in line_items %}
        <tr class="line-item-row {% if item.display_status == 'discontinued' %}bg-yellow-50{% endif %}">
            <td>
                {{ item.item_name }}
                {% if item.display_status == 'discontinued' %}
                    <br>
                    <small class="text-xs text-gray-600">
                        Credit Note:
                        <a href="{{ url_for('billing_views.view_credit_note', credit_note_id=item.credit_note_id) }}"
                           class="text-blue-600 hover:underline">
                            {{ item.credit_note_number }}
                        </a>
                    </small>
                {% endif %}
            </td>
            <td>
                <span class="badge badge-{{ 'primary' if item.item_type == 'Package' else 'secondary' }}">
                    {{ item.item_type }}
                </span>
            </td>
            <td>{{ item.quantity }}</td>
            <td class="text-right">
                <div>₹{{ '{:,.2f}'.format(item.line_total) }}</div>
                {% if item.refund_amount and item.refund_amount > 0 %}
                    <div class="text-sm text-red-600">
                        Refund: -₹{{ '{:,.2f}'.format(item.refund_amount) }}
                    </div>
                    <div class="text-sm font-semibold text-gray-700">
                        Net: ₹{{ '{:,.2f}'.format(item.line_total - item.refund_amount) }}
                    </div>
                {% endif %}
            </td>
            <td>
                <span class="badge badge-{{ item.status_badge }}">
                    {{ item.status_text }}
                </span>
                {% if item.display_status == 'discontinued' %}
                    <button type="button"
                            class="text-xs text-blue-600 hover:underline"
                            onclick="showDiscontinuationDetails('{{ item.line_item_id }}')">
                        Details
                    </button>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<!-- Discontinuation Details Modal -->
<div id="discontinuation-modal" class="hidden modal">
    <div class="modal-content">
        <h3>Package Discontinuation Details</h3>
        <div id="discontinuation-details"></div>
    </div>
</div>
```

**CSS for Visual Indicators**:

```css
/* app/static/css/invoice.css */

/* Discontinued line item - subtle yellow background */
.line-item-row.bg-yellow-50 {
    background-color: #fffbeb;
}

/* Hover effect for discontinued items */
.line-item-row.bg-yellow-50:hover {
    background-color: #fef3c7;
}

/* Status badges */
.badge-warning {
    background-color: #fbbf24;
    color: #78350f;
}

.badge-success {
    background-color: #10b981;
    color: #ffffff;
}

.badge-info {
    background-color: #3b82f6;
    color: #ffffff;
}

.badge-secondary {
    background-color: #6b7280;
    color: #ffffff;
}

/* Credit note link styling */
.credit-note-link {
    font-size: 0.75rem;
    color: #2563eb;
    text-decoration: underline;
}

/* Icon for discontinued status */
.discontinued-icon::before {
    content: "⚠️";
    margin-right: 4px;
}
```

### Option B: Database View (For Complex Reporting) ✅

If you need to query this frequently for reports, create a read-only view:

```sql
-- Migration: create_invoice_line_items_with_status_view.sql
CREATE OR REPLACE VIEW invoice_line_items_with_status AS
SELECT
    ili.*,

    -- Package plan info
    ppp.plan_id,
    ppp.status AS package_plan_status,
    ppp.discontinued_at,
    ppp.discontinued_by,
    ppp.discontinuation_reason,
    ppp.refund_amount AS plan_refund_amount,

    -- Credit note info
    cn.credit_note_id,
    cn.credit_note_number,
    cn.total_amount AS credit_note_amount,

    -- Computed status (for easy querying)
    CASE
        WHEN ppp.status = 'discontinued' THEN 'discontinued'
        WHEN ppp.status = 'completed' THEN 'completed'
        WHEN ppp.status = 'active' THEN 'active'
        WHEN ppp.status = 'suspended' THEN 'suspended'
        ELSE 'active'  -- For non-package items
    END AS computed_status,

    -- Visual indicator flag
    CASE
        WHEN ppp.status = 'discontinued' THEN true
        ELSE false
    END AS is_discontinued,

    -- Net amount after credit notes
    ili.line_total - COALESCE(cn.total_amount, 0) AS net_amount

FROM invoice_line_item ili

-- LEFT JOIN to package plan (only package items have plans)
LEFT JOIN package_payment_plans ppp
    ON ili.invoice_id = ppp.invoice_id
    AND ili.package_id = ppp.package_id

-- LEFT JOIN to credit notes
LEFT JOIN patient_credit_notes cn
    ON cn.plan_id = ppp.plan_id
    AND cn.reason_code = 'plan_discontinued';

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_ili_with_status_invoice
    ON invoice_line_item(invoice_id);
```

**Usage**:

```python
# Query the view instead of base table
line_items = session.query(InvoiceLineItemWithStatus).filter(
    InvoiceLineItemWithStatus.invoice_id == invoice_id
).all()

# Now you have computed_status without manual joins!
for item in line_items:
    if item.is_discontinued:
        print(f"Discontinued: {item.item_name}, Refund: {item.credit_note_amount}")
```

**Model for the View**:

```python
# app/models/views.py

class InvoiceLineItemWithStatus(Base):
    """
    Read-only view combining invoice line items with package discontinuation status
    For easier querying and reporting
    """
    __tablename__ = 'invoice_line_items_with_status'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view

    # Primary key (from base table)
    line_item_id = Column(UUID(as_uuid=True), primary_key=True)

    # All columns from invoice_line_item
    hospital_id = Column(UUID(as_uuid=True))
    invoice_id = Column(UUID(as_uuid=True))
    package_id = Column(UUID(as_uuid=True))
    service_id = Column(UUID(as_uuid=True))
    medicine_id = Column(UUID(as_uuid=True))
    item_type = Column(String(20))
    item_name = Column(String(100))
    quantity = Column(Numeric(10, 2))
    unit_price = Column(Numeric(12, 2))
    line_total = Column(Numeric(12, 2))

    # Computed columns from view
    plan_id = Column(UUID(as_uuid=True))
    package_plan_status = Column(String(20))
    discontinued_at = Column(DateTime(timezone=True))
    discontinuation_reason = Column(Text)
    plan_refund_amount = Column(Numeric(12, 2))
    credit_note_id = Column(UUID(as_uuid=True))
    credit_note_number = Column(String(50))
    credit_note_amount = Column(Numeric(12, 2))
    computed_status = Column(String(20))
    is_discontinued = Column(Boolean)
    net_amount = Column(Numeric(12, 2))
```

## Visual Design Examples

### Example 1: Subtle Background Color

```html
<tr class="{% if item.is_discontinued %}bg-yellow-50 border-l-4 border-yellow-500{% endif %}">
    <td>{{ item.item_name }}</td>
    <td>₹{{ item.line_total }}</td>
    <td>
        {% if item.is_discontinued %}
            <span class="badge badge-warning">
                <i class="fas fa-exclamation-triangle"></i> Discontinued
            </span>
        {% else %}
            <span class="badge badge-success">Active</span>
        {% endif %}
    </td>
</tr>
```

### Example 2: Strikethrough + Credit Note Link

```html
<tr>
    <td>
        <div class="{% if item.is_discontinued %}text-gray-500 line-through{% endif %}">
            {{ item.item_name }}
        </div>
        {% if item.is_discontinued %}
            <div class="text-sm mt-1">
                <span class="text-red-600">⚠️ Discontinued</span>
                <a href="{{ url_for('billing_views.view_credit_note', credit_note_id=item.credit_note_id) }}"
                   class="text-blue-600 hover:underline ml-2">
                    See Credit Note: {{ item.credit_note_number }}
                </a>
            </div>
        {% endif %}
    </td>
    <td class="text-right">
        {% if item.is_discontinued %}
            <div class="text-gray-400 line-through">₹{{ '{:,.2f}'.format(item.line_total) }}</div>
            <div class="text-sm text-red-600">-₹{{ '{:,.2f}'.format(item.credit_note_amount) }}</div>
            <div class="font-semibold">₹{{ '{:,.2f}'.format(item.net_amount) }}</div>
        {% else %}
            <div>₹{{ '{:,.2f}'.format(item.line_total) }}</div>
        {% endif %}
    </td>
</tr>
```

### Example 3: Icon-Based Indicator

```html
<tr>
    <td>
        <div class="flex items-center">
            {% if item.is_discontinued %}
                <span class="mr-2 text-yellow-600 text-lg" title="Package Discontinued">⚠️</span>
            {% elif item.package_plan_status == 'completed' %}
                <span class="mr-2 text-green-600 text-lg" title="Package Completed">✓</span>
            {% elif item.package_plan_status == 'active' %}
                <span class="mr-2 text-blue-600 text-lg" title="Package Active">▶</span>
            {% endif %}
            <div>
                {{ item.item_name }}
                {% if item.is_discontinued %}
                    <span class="text-xs text-gray-600 block">{{ item.discontinuation_reason[:50] }}...</span>
                {% endif %}
            </div>
        </div>
    </td>
</tr>
```

## Comparison: Status Field vs Visual Indicator

| Aspect | Add Status Field ❌ | Visual Indicator ✅ |
|--------|-------------------|-------------------|
| **Invoice Immutability** | Violates principle | Maintains immutability |
| **Data Redundancy** | Duplicate status | Single source of truth |
| **Audit Compliance** | Non-compliant | Compliant |
| **Implementation** | Database migration required | No schema change |
| **Query Complexity** | Simple (direct field) | Requires JOIN |
| **Semantic Correctness** | Wrong (not all items have status) | Correct (computed per item type) |
| **Maintenance** | Must sync two sources | Automatic from plan status |
| **Performance** | Slightly faster query | Minimal impact with index |
| **Reporting** | Easy | Use database view |

## Implementation Steps

### Step 1: Create Database View (Optional)

```bash
# Run migration
psql -U username -d skinspire_dev -f migrations/create_invoice_line_items_with_status_view.sql
```

### Step 2: Add Model for View (If using view)

```python
# app/models/views.py - Add InvoiceLineItemWithStatus class
```

### Step 3: Update Service Layer

```python
# app/services/billing_service.py

def get_invoice_with_line_status(invoice_id, hospital_id):
    """Get invoice with computed line item status"""

    with get_db_session() as session:
        # Option A: Use view
        line_items = session.query(InvoiceLineItemWithStatus).filter(
            InvoiceLineItemWithStatus.invoice_id == invoice_id
        ).all()

        # Option B: Manual join (if not using view)
        # line_items = session.query(...).join(...).all()

        return [to_dict(item) for item in line_items]
```

### Step 4: Update Template

```html
<!-- app/templates/billing/view_invoice.html -->
<!-- Add visual indicators as shown in examples above -->
```

### Step 5: Add CSS Styling

```css
/* app/static/css/invoice.css */
/* Add styling for discontinued items */
```

## Summary

### ✅ Recommended Approach: Visual Indicator Only

**What to do**:
1. **Do NOT add status field** to invoice_line_item table
2. **Compute status** at query time (via JOIN)
3. **Use visual indicators** in UI (color, badges, icons)
4. **Optional**: Create database view for easier queries

**Why**:
- ✅ Maintains invoice immutability
- ✅ Preserves audit trail
- ✅ Single source of truth (package_payment_plans.status)
- ✅ GAAP/IFRS compliant
- ✅ No data redundancy
- ✅ Semantically correct

**Benefits**:
- Package line items: Show discontinued status from plan
- Service line items: Show as active (no plan to discontinue)
- Medicine line items: Show as active (no plan to discontinue)
- Invoice remains immutable
- Visual feedback for users
- Proper accounting practices

### Visual Indicator Design

**Recommended Styling**:
- **Background color**: Light yellow (#fffbeb) for discontinued items
- **Badge**: Yellow warning badge with "Discontinued" text
- **Icon**: ⚠️ warning icon
- **Link**: Credit note number as clickable link
- **Amount**: Show original (strikethrough) + credit + net

**Result**: Users get clear visual feedback without modifying posted invoices! ✅
