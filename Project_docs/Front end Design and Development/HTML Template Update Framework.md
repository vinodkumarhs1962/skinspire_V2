# HTML Template Update Framework

## Backward Compatible CSS Migration Strategy

### Phase 1: Preparation
Before updating templates, ensure the centralized CSS file includes backward compatibility:

```css
/* Legacy class mappings for backward compatibility */
.btn, .button { @apply btn-primary; }
.btn-default { @apply btn-secondary; }
.btn-success { @apply btn-primary; }
.btn-warning { @apply btn-secondary; }
.btn-danger { @apply bg-red-600 text-white; }

/* Legacy table classes */
.table-striped { @apply table; }
.table-bordered { @apply table-container; }

/* Legacy form classes */
.form-control { @apply form-input; }
.form-group { @apply mb-4; }
```

## Template Update Priority Order

### 1. Supplier Invoice View
**Key Updates Needed:**
- Replace inline styles with centralized classes
- Implement card-based layout
- Add responsive design
- Standardize button styling
- Implement consistent color coding

**Template Structure:**
```html
{% extends "base.html" %}

{% block content %}
<div class="page-header">
    <div class="flex justify-between items-center">
        <h1 class="page-title">Supplier Invoice #{{ invoice.number }}</h1>
        <div class="btn-group">
            <a href="{{ url_for('supplier.invoice_edit', id=invoice.id) }}" class="btn-primary">Edit</a>
            <a href="{{ url_for('supplier.invoice_print', id=invoice.id) }}" class="btn-secondary print-hide">Print</a>
            <a href="{{ url_for('supplier.invoice_list') }}" class="btn-secondary">Back to List</a>
        </div>
    </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Invoice Details Card -->
    <div class="lg:col-span-2">
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Invoice Details</h2>
                <span class="status-{{ invoice.status|lower }}">{{ invoice.status }}</span>
            </div>
            <div class="card-body">
                <!-- Invoice details content -->
            </div>
        </div>
    </div>
    
    <!-- Supplier Information Card -->
    <div>
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Supplier Information</h2>
            </div>
            <div class="card-body">
                <!-- Supplier details content -->
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 2. Supplier Invoice List
**Key Updates Needed:**
- Implement responsive table design
- Add filtering and search functionality
- Standardize action buttons
- Implement pagination styling

**Template Structure:**
```html
{% extends "base.html" %}

{% block content %}
<div class="page-header">
    <div class="flex justify-between items-center">
        <h1 class="page-title">Supplier Invoices</h1>
        <a href="{{ url_for('supplier.invoice_add') }}" class="btn-primary">Add New Invoice</a>
    </div>
</div>

<!-- Filters -->
<div class="card mb-6">
    <div class="card-body">
        <form method="GET" class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="form-group">
                <label class="form-label">Supplier</label>
                <select name="supplier_id" class="form-select">
                    <option value="">All Suppliers</option>
                    <!-- Options -->
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Status</label>
                <select name="status" class="form-select">
                    <option value="">All Status</option>
                    <!-- Options -->
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Search</label>
                <input type="text" name="search" class="form-input" placeholder="Invoice number...">
            </div>
            <div class="form-group flex items-end">
                <button type="submit" class="btn-primary w-full">Filter</button>
            </div>
        </form>
    </div>
</div>

<!-- Data Table -->
<div class="card">
    <div class="table-container">
        <table class="table">
            <thead class="table-header">
                <tr>
                    <th class="table-header-cell">Invoice #</th>
                    <th class="table-header-cell">Supplier</th>
                    <th class="table-header-cell">Date</th>
                    <th class="table-header-cell">Amount</th>
                    <th class="table-header-cell">Status</th>
                    <th class="table-header-cell">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
                {% for invoice in invoices %}
                <tr class="table-row">
                    <td class="table-cell font-medium">{{ invoice.number }}</td>
                    <td class="table-cell">{{ invoice.supplier.name }}</td>
                    <td class="table-cell">{{ invoice.date|date }}</td>
                    <td class="table-cell">{{ invoice.amount|currency }}</td>
                    <td class="table-cell">
                        <span class="status-{{ invoice.status|lower }}">{{ invoice.status }}</span>
                    </td>
                    <td class="table-cell">
                        <div class="btn-group">
                            <a href="{{ url_for('supplier.invoice_view', id=invoice.id) }}" class="btn-sm btn-secondary">View</a>
                            <a href="{{ url_for('supplier.invoice_edit', id=invoice.id) }}" class="btn-sm btn-primary">Edit</a>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

### 3-9. Similar Pattern for Other Templates
Each template will follow similar patterns with specific adaptations:

**Purchase Order List/View:**
- Similar structure to invoice templates
- Add PO-specific status colors
- Include approval workflow buttons

**Payment View/History:**
- Focus on transaction details
- Include payment method indicators
- Add reconciliation status

**Supplier Form/List/View:**
- Contact information layout
- Document upload sections
- Credit terms display

## Migration Script Template

```python
# migration_helper.py
def update_template_classes(html_content):
    """
    Helper function to automatically update common class names
    """
    replacements = {
        'class="btn btn-primary"': 'class="btn-primary"',
        'class="btn btn-secondary"': 'class="btn-secondary"',
        'class="btn btn-danger"': 'class="btn-danger"',
        'class="table table-striped"': 'class="table"',
        'class="form-control"': 'class="form-input"',
        # Add more mappings as needed
    }
    
    for old, new in replacements.items():
        html_content = html_content.replace(old, new)
    
    return html_content
```

## Testing Checklist for Each Template

### Functional Testing:
- [ ] All existing functionality preserved
- [ ] Form submissions work correctly
- [ ] Links and navigation functional
- [ ] CSRF tokens included
- [ ] Validation messages display properly

### Visual Testing:
- [ ] Consistent with design system
- [ ] Responsive on all screen sizes
- [ ] Print styles work correctly
- [ ] Color coding is consistent
- [ ] Icons display properly

### Accessibility Testing:
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Proper ARIA labels
- [ ] Color contrast meets standards
- [ ] Focus indicators visible

## Implementation Steps

1. **Backup existing templates**
2. **Update CSS file with legacy compatibility classes**
3. **Update templates one by one in specified order**
4. **Test each template thoroughly**
5. **Deploy to QA environment**
6. **Conduct user acceptance testing**
7. **Deploy to production**

## Next Steps Required

To proceed with the actual template updates, please provide:

1. The current HTML content of each template file
2. Any existing CSS files being used
3. Screenshots of current layouts (if available)
4. Specific design requirements or mockups
5. Any custom JavaScript functionality that needs to be preserved

Once I have access to the actual template content, I can provide specific, detailed code changes for each file while ensuring backward compatibility.