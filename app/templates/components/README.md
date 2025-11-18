# Reusable Template Components

This directory contains reusable Jinja2 template components that can be used across the application for consistent styling and behavior.

## Available Components

### 1. Patient Info Header (`patient_info_header.jinja`)

A reusable header component that displays patient information in a consistent format across all patient-related pages.

**Location:** `app/templates/components/patient_info_header.jinja`

#### Features:
- Displays page title with icon
- Shows patient name and MRN
- Displays phone and email if available
- Includes a "Back" button
- Uses Bootstrap styling for consistency
- Handles both patient objects and invoice dicts with patient fields

#### Usage:

```jinja
{% from 'components/patient_info_header.jinja' import patient_info_header %}

{{ patient_info_header(
    title='Record Payment',
    icon='fas fa-money-check-alt',
    patient=patient,
    back_url=url_for('billing_views.view_invoice', invoice_id=invoice.invoice_id),
    back_text='Back to Invoice'
) }}
```

#### Parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Page title to display (e.g., 'Record Payment', 'Invoice Details') |
| `icon` | string | Yes | FontAwesome icon class (e.g., 'fas fa-money-check-alt') |
| `patient` | dict/object | Yes | Patient data (see below for supported formats) |
| `back_url` | string | Yes | URL for the back button |
| `back_text` | string | No | Text for back button (default: 'Back') |

#### Patient Data Formats:

The component supports two data formats:

**Format 1: Patient Object**
```python
patient = {
    'full_name': 'John Doe',              # OR
    'first_name': 'John',                 # first_name + last_name
    'last_name': 'Doe',
    'mrn': 'MRN12345',
    'contact_info': {
        'phone': '+91 9876543210',
        'email': 'john.doe@example.com'
    }
}
```

**Format 2: Invoice Dict with Patient Fields**
```python
invoice = {
    'patient_name': 'John Doe',
    'patient_mrn': 'MRN12345',
    'patient_phone': '+91 9876543210',    # Optional
    'patient_email': 'john.doe@example.com'  # Optional
}
```

#### Examples:

**Payment Form:**
```jinja
{{ patient_info_header(
    title='Record Payment',
    icon='fas fa-money-check-alt',
    patient=patient,
    back_url=url_for('billing_views.view_invoice', invoice_id=invoice.invoice_id),
    back_text='Back to Invoice'
) }}
```

**Consolidated Invoice Detail:**
```jinja
{{ patient_info_header(
    title=parent_invoice.invoice_number,
    icon='fas fa-folder-open',
    patient=parent_invoice,
    back_url=url_for('universal_views.universal_list_view', entity_type='consolidated_patient_invoices'),
    back_text='Back to List'
) }}
```

**Invoice View:**
```jinja
{{ patient_info_header(
    title='Invoice ' ~ invoice.invoice_number,
    icon='fas fa-file-invoice',
    patient=patient,
    back_url=url_for('universal_views.universal_list_view', entity_type='patient_invoices'),
    back_text='Back to Invoices'
) }}
```

#### Visual Output:

```
┌──────────────────────────────────────────────────────────────┐
│  💰 Record Payment                          [Back to Invoice] │
│  Patient: John Doe (MRN: MRN12345) | 📞 +91 9876543210 | ✉ john.doe@example.com │
└──────────────────────────────────────────────────────────────┘
```

#### Currently Used In:

1. **Payment Form Enhanced** (`billing/payment_form_enhanced.html`)
   - Shows "Record Payment" header
   - Back to invoice button

2. **Consolidated Invoice Detail** (`engine/business/consolidated_invoice_detail.html`)
   - Shows invoice number as title
   - Back to list button

#### Benefits:

✅ **Single Source of Truth** - All patient headers look identical
✅ **Easy Maintenance** - Update in one place, changes everywhere
✅ **Consistency** - Same styling across all pages
✅ **Flexible** - Works with different data formats
✅ **Bootstrap Compatible** - Uses Bootstrap classes for styling

#### Future Enhancements:

Potential additions to this component:
- Optional avatar/photo display
- Additional patient metadata (age, gender, etc.)
- Alert badges (overdue payments, pending tasks)
- Quick action buttons
- Print/export functionality

---

## Creating New Components

When creating new reusable components, follow these guidelines:

1. **File Naming**: Use descriptive names with `.jinja` extension
2. **Documentation**: Include detailed comments in the component file
3. **Flexibility**: Support multiple data formats where applicable
4. **Consistency**: Match existing Bootstrap/Tailwind styling
5. **Parameters**: Use clear, descriptive parameter names
6. **Defaults**: Provide sensible defaults for optional parameters
7. **Examples**: Include usage examples in comments

## Contributing

When adding a new component:
1. Create the component file in this directory
2. Add documentation to this README
3. Update all relevant templates to use the component
4. Test with different data formats
5. Document any edge cases or limitations
