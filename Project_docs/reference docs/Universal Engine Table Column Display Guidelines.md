# Universal Engine Table Column Display Guidelines v1.0

## Document Overview

| **Attribute** | **Details** |
|---------------|-------------|
| **Version** | v1.0 |
| **Status** | **PRODUCTION READY** |
| **Last Updated** | January 2025 |
| **Purpose** | Guide for configuring table column display behavior in Universal Engine |

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Column Display Modes](#column-display-modes)
3. [Configuration Parameters](#configuration-parameters)
4. [CSS Classes Reference](#css-classes-reference)
5. [Width Configuration](#width-configuration)
6. [Alignment Options](#alignment-options)
7. [Real-World Examples](#real-world-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Universal Engine provides flexible column display options for list views. Understanding how to configure columns ensures optimal user experience with readable, well-formatted tables.

### Key Concepts

1. **Default Behavior**: Text truncates at end with ellipsis ("...")
2. **Configurable Behavior**: Use `css_classes` to override default
3. **Backward Compatibility**: Existing configurations remain unchanged
4. **Configuration-Driven**: Template and CSS respect field configuration

---

## Column Display Modes

### Mode 1: End Truncation (Default)

**When to Use:**
- IDs, reference numbers, codes
- Short text fields
- Fields where full content is not critical for list view
- Space-constrained columns

**How It Works:**
- Text longer than column width shows "..." at end
- Hover shows full text in tooltip
- Single line display
- Clean, compact appearance

**Configuration:**
```python
FieldDefinition(
    name='reference_number',
    label='Reference #',
    field_type=FieldType.TEXT,
    show_in_list=True,
    width='120px',
    # No css_classes or empty css_classes = default truncation
)
```

**Visual Example:**
```
Reference #
-----------------
PO/2024/001234...  ← Truncated with ellipsis
```

---

### Mode 2: Text Wrapping

**When to Use:**
- Names (patient, supplier, product)
- Descriptions
- Fields where full content must be visible
- User-critical information

**How It Works:**
- Text wraps at word boundaries
- Multiple lines within cell
- No truncation
- Full content visible

**Configuration:**
```python
FieldDefinition(
    name='patient_name',
    label='Patient Name',
    field_type=FieldType.TEXT,
    show_in_list=True,
    css_classes='text-wrap align-top',  # ← Enable wrapping
    width='180px',  # ← Wider to accommodate wrapped text
)
```

**Visual Example:**
```
Patient Name
-----------------
Christopher      ← Wraps at word boundary
Anderson
```

---

### Mode 3: Middle Truncation

**When to Use:**
- Long reference numbers where both start and end are important
- UUIDs in development/debugging
- File paths or URLs (when needed)

**How It Works:**
- Shows first 10 characters
- Shows "..." in middle
- Shows last 4 characters
- Preserves important context from both ends

**Configuration:**
```python
FieldDefinition(
    name='transaction_id',
    label='Transaction ID',
    field_type=FieldType.TEXT,
    show_in_list=True,
    width='150px',
    # Default behavior applies automatically for text > 15 chars
)
```

**Visual Example:**
```
Transaction ID
-----------------
PO/2024/00...1234  ← Shows start and end
```

**Note**: This is automatically applied by the template for text fields > 15 characters unless `text-wrap` is configured.

---

## Configuration Parameters

### FieldDefinition Parameters for Column Display

| Parameter | Type | Purpose | Default |
|-----------|------|---------|---------|
| `name` | str | Database column name | Required |
| `label` | str | Column header display | Required |
| `field_type` | FieldType | Data type (affects formatting) | Required |
| `show_in_list` | bool | Show in list view table | False |
| `width` | str | Column width (px, %, auto) | 'auto' |
| `css_classes` | str | Space-separated CSS classes | '' |
| `align` | str | Text alignment (left/center/right) | 'left' |
| `sortable` | bool | Enable column sorting | False |
| `searchable` | bool | Include in text search | False |

---

## CSS Classes Reference

### Display Control Classes

#### `text-wrap`
**Purpose**: Enable natural text wrapping at word boundaries

**Effect**:
- Overrides default truncation
- Allows multiple lines
- Text wraps at spaces/hyphens
- Full content visible

**Use With**: Names, descriptions, addresses

**Example**:
```python
css_classes='text-wrap align-top'
```

---

#### `align-top`
**Purpose**: Align cell content to top

**Effect**:
- Content starts at top of cell
- Better for multi-line wrapped text
- Consistent baseline across row

**Use With**: Wrapped text, variable-height content

**Example**:
```python
css_classes='text-wrap align-top'  # Common combination
```

---

#### `text-truncate`
**Purpose**: Force end truncation (explicit)

**Effect**:
- Ensures ellipsis at end
- Single line only
- Overrides other settings

**Use With**: When you explicitly want truncation

**Example**:
```python
css_classes='text-truncate'
```

---

#### `text-end` / `text-center`
**Purpose**: Align text within cell

**Effect**:
- `text-end`: Right-align text
- `text-center`: Center-align text

**Use With**:
- `text-end`: Numbers, amounts, dates
- `text-center`: Status badges, icons

**Example**:
```python
css_classes='text-end'  # For currency fields
```

---

### ⚠️ Classes to AVOID

#### ❌ `word-break-all`
**Problem**: Breaks words in the middle (ugly)

**Example**: "Christopher" → "Christo-<br>pher"

**Instead Use**: `text-wrap` (breaks at word boundaries)

---

#### ❌ `text-break`
**Problem**: Too aggressive word breaking

**Instead Use**: `text-wrap` for natural wrapping

---

## Width Configuration

### Width Guidelines

| Content Type | Recommended Width | Rationale |
|-------------|-------------------|-----------|
| **ID/Code** | 80px - 120px | Fixed-width identifiers |
| **Reference Number** | 120px - 150px | Codes with prefixes |
| **Name (Truncated)** | 150px - 180px | Short names with ellipsis |
| **Name (Wrapped)** | 180px - 220px | Full names with wrapping |
| **Description** | 200px - 300px | Longer text content |
| **Date** | 100px - 120px | Date format (DD-MMM-YYYY) |
| **Currency** | 100px - 120px | Formatted amounts |
| **Status Badge** | 90px - 110px | Status indicators |
| **Actions** | 100px - 160px | Action buttons |

### Width Syntax

```python
# Absolute pixels (recommended)
width='180px'

# Percentage (use cautiously)
width='20%'

# Auto (table decides)
width='auto'
```

### ✅ DO's for Width

```python
# ✅ CORRECT: Increase width when enabling wrapping
FieldDefinition(
    name='patient_name',
    css_classes='text-wrap align-top',
    width='180px',  # Wider for wrapped text
)

# ✅ CORRECT: Narrower for truncated text
FieldDefinition(
    name='reference_id',
    css_classes='',  # Default truncation
    width='120px',  # Narrower is OK
)
```

### ❌ DON'Ts for Width

```python
# ❌ WRONG: Text wrap with narrow width (causes excessive wrapping)
FieldDefinition(
    name='patient_name',
    css_classes='text-wrap align-top',
    width='100px',  # TOO NARROW! Every word wraps
)

# ❌ WRONG: Truncation with excessive width (wastes space)
FieldDefinition(
    name='code',
    css_classes='',  # Truncated
    width='400px',  # TOO WIDE! Wastes space
)
```

---

## Alignment Options

### Horizontal Alignment

#### Left Align (Default)
**Use For**: Text, names, descriptions, IDs

```python
align='left'  # Or omit (default)
# OR
css_classes='text-start'
```

#### Right Align
**Use For**: Numbers, currency, amounts, quantities

```python
align='right'
# OR
css_classes='text-end'
```

#### Center Align
**Use For**: Status badges, icons, actions

```python
align='center'
# OR
css_classes='text-center'
```

### Vertical Alignment

#### Top Align
**Use For**: Wrapped text, multi-line content

```python
css_classes='text-wrap align-top'
```

#### Middle Align (Default)
**Use For**: Single-line content, status badges

```python
# Default behavior - no configuration needed
```

---

## Real-World Examples

### Example 1: Patient Name (Text Wrapping)

**File**: `app/config/modules/package_payment_plan_config.py`

```python
FieldDefinition(
    name='patient_name',
    label='Patient Name',
    field_type=FieldType.TEXT,
    readonly=True,
    filterable=True,
    filter_type=FilterType.ENTITY_DROPDOWN,
    filter_operator=FilterOperator.EQUALS,
    show_in_list=True,
    show_in_detail=True,
    searchable=True,
    sortable=True,

    # ✅ KEY CONFIGURATION FOR WRAPPING
    css_classes='text-wrap align-top',  # Enable wrapping, top-align
    width='180px',  # Wider to accommodate wrapped text

    tab_group="overview",
    section="basic_info",
    view_order=1
)
```

**Result**:
- Full patient names visible
- Wraps at word boundaries
- No truncation
- Top-aligned for consistency

---

### Example 2: Package Name (Text Wrapping)

**File**: `app/config/modules/package_payment_plan_config.py`

```python
FieldDefinition(
    name='package_name',
    label='Package Name',
    field_type=FieldType.TEXT,
    readonly=True,
    filterable=True,
    filter_type=FilterType.ENTITY_DROPDOWN,
    show_in_list=True,
    searchable=True,
    sortable=True,

    # ✅ KEY CONFIGURATION FOR WRAPPING
    css_classes='text-wrap align-top',  # Enable wrapping
    width='200px',  # Even wider for longer package names

    tab_group="overview",
    section="basic_info",
    view_order=2
)
```

**Result**:
- Full package names visible
- Natural word wrapping
- Clean multi-line display

---

### Example 3: Supplier Name (End Truncation)

**File**: `app/config/modules/supplier_payment_config.py`

```python
FieldDefinition(
    name="supplier_name",
    label="Supplier",
    field_type=FieldType.TEXT,
    filterable=True,
    filter_type=FilterType.ENTITY_DROPDOWN,
    show_in_list=True,
    searchable=True,
    sortable=True,
    readonly=True,

    # ✅ NO text-wrap = Default truncation
    css_classes='',  # Empty or omit for default behavior
    width='150px',

    view_order=2
)
```

**Result**:
- Supplier name truncates at end with "..."
- Hover shows full name
- Single line, compact display

---

### Example 4: Currency Field (Right Aligned)

**File**: `app/config/modules/package_payment_plan_config.py`

```python
FieldDefinition(
    name='total_amount',
    label='Total Amount',
    field_type=FieldType.CURRENCY,  # ← Automatically right-aligned
    required=True,
    show_in_list=True,
    show_in_detail=True,
    sortable=True,

    # Currency fields auto-align right
    css_classes='text-end align-top',  # Right-align, top-align
    width='120px',

    tab_group="overview",
    section="basic_info",
    view_order=4
)
```

**Result**:
- Right-aligned for easy comparison
- Formatted with currency symbol
- Monospace font (CSS automatic)

---

### Example 5: Plan ID (Middle Truncation)

**File**: `app/config/modules/package_payment_plan_config.py`

```python
FieldDefinition(
    name='plan_id',
    label='Plan ID',
    field_type=FieldType.UUID,
    primary_key=True,
    show_in_list=True,
    show_in_detail=True,
    sortable=True,

    # Default behavior = middle truncation for long text
    css_classes='',
    width='140px',

    tab_group="overview",
    section="basic_info",
    view_order=0
)
```

**Result**:
- Long UUIDs show as "PLAN/2024/...1234"
- First 10 chars visible
- Last 4 chars visible
- Middle replaced with "..."

---

## Best Practices

### 1. Choose the Right Display Mode

| Content Type | Recommended Mode | Configuration |
|--------------|------------------|---------------|
| **Names** | Text Wrapping | `css_classes='text-wrap align-top'` |
| **IDs/Codes** | End Truncation | `css_classes=''` (default) |
| **Long References** | Middle Truncation | Automatic (default for text > 15 chars) |
| **Descriptions** | Text Wrapping | `css_classes='text-wrap align-top'` |
| **Amounts** | No Truncation | `field_type=FieldType.CURRENCY` |
| **Dates** | No Truncation | `field_type=FieldType.DATE` |

---

### 2. Width Sizing Strategy

**For Wrapped Text**:
```python
# Calculate: Average word length × 2-3 words per line
# Example: "Christopher Anderson" = ~20 chars
# Need: 180-200px to display 2 words per line
width='180px'
```

**For Truncated Text**:
```python
# Calculate: Expected display length + 20%
# Example: "PO/2024/001" = ~12 chars
# Need: 100-120px
width='120px'
```

---

### 3. Consistency Across Entity

```python
# ✅ GOOD: Consistent name field configuration across all entities
# Package Payment Plans
FieldDefinition(name='patient_name', css_classes='text-wrap align-top', width='180px')

# Supplier Invoices
FieldDefinition(name='supplier_name', css_classes='text-wrap align-top', width='180px')

# Patient Invoices
FieldDefinition(name='patient_name', css_classes='text-wrap align-top', width='180px')
```

---

### 4. Performance Considerations

**Text Wrapping**:
- ✅ Use for 1-5 columns per table
- ⚠️ Avoid for 10+ columns (table becomes tall)
- ✅ Increase row spacing (`line-height`) for readability

**Truncation**:
- ✅ Use for most columns
- ✅ Better table density
- ✅ Faster rendering

---

### 5. Accessibility

```python
# Always provide hover tooltip (automatic with title attribute)
# Template automatically sets title="{{ cell_value }}"

# For screen readers, meaningful labels
FieldDefinition(
    name='patient_name',
    label='Patient Name',  # ← Clear label for screen readers
)
```

---

## Troubleshooting

### Issue 1: Text Still Truncating Despite `text-wrap`

**Symptoms**: Configuration has `css_classes='text-wrap'` but text still shows "..." at end

**Causes & Fixes**:

#### Cause 1: Browser Cache
```bash
# Solution: Hard refresh browser
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

#### Cause 2: CSS Not Applied
**Check**: Inspect element in browser DevTools

```html
<!-- ❌ WRONG: text-wrap class missing -->
<td class="align-top">Christopher Anderson...</td>

<!-- ✅ CORRECT: text-wrap class present -->
<td class="text-wrap align-top">Christopher Anderson</td>
```

**Fix**: Verify field configuration in entity config file

#### Cause 3: CSS Override Missing
**Check**: `app/static/css/components/tables.css` must have:

```css
/* Must be present (added in v1.0) */
.universal-data-table td.text-wrap {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: normal !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    line-height: 1.4 !important;
}
```

**Fix**: Ensure CSS file has this rule (lines 1479-1486)

---

### Issue 2: Excessive Wrapping (Every Word on New Line)

**Symptoms**: Each word wraps to a new line, column too narrow

**Cause**: Column width too small for wrapped text

**Fix**:
```python
# ❌ BEFORE
FieldDefinition(
    name='patient_name',
    css_classes='text-wrap align-top',
    width='100px',  # TOO NARROW
)

# ✅ AFTER
FieldDefinition(
    name='patient_name',
    css_classes='text-wrap align-top',
    width='180px',  # Appropriate width
)
```

---

### Issue 3: Column Width Not Applying

**Symptoms**: Set `width='200px'` but column is different size

**Possible Causes**:

#### Cause 1: Table Layout
```css
/* Check if table uses fixed layout */
.universal-data-table {
    table-layout: fixed !important;  /* ✅ Respects width */
    /* OR */
    table-layout: auto !important;   /* ❌ Ignores width */
}
```

#### Cause 2: Min/Max Width CSS
**Check**: Browser DevTools → Computed styles

**Fix**: Ensure no conflicting CSS rules

---

### Issue 4: Middle Truncation Not Working

**Symptoms**: Expect "PO/2024/...1234" but see "PO/2024/001234..."

**Cause**: Text length ≤ 15 characters

**How Middle Truncation Works**:
```python
# Template logic (universal_list.html):
{% if cell_text|length > 15 %}
    # Apply middle truncation
{% else %}
    # Show full text
{% endif %}
```

**Fix**: Middle truncation only applies to text > 15 characters

---

### Issue 5: Alignment Not Working

**Symptoms**: Set `align='right'` but text is left-aligned

**Check Order of Priority**:
1. `field_type` auto-alignment (CURRENCY → right)
2. `align` parameter
3. `css_classes` (text-start, text-end, text-center)

**Fix**:
```python
# ✅ CORRECT: Explicit alignment
FieldDefinition(
    name='custom_field',
    field_type=FieldType.TEXT,
    css_classes='text-end',  # Force right-align
)
```

---

## Technical Implementation Details

### Template Flow (`universal_list.html`)

```jinja2
<!-- Line 632: Apply CSS classes from configuration -->
<td class="{{ column.css_class }} {{ column.css_classes }}"
    style="width: {{ column.width }}; text-align: {{ column.align|default('left') }};">

    <!-- Line 716: Check for text-wrap configuration -->
    {% if column.css_classes and 'text-wrap' in column.css_classes %}
        <!-- Show full text, let CSS handle wrapping -->
        {{ cell_value }}
    {% else %}
        <!-- Apply middle truncation for long text -->
        {% if cell_text|length > 15 %}
            <span class="truncate-middle-wrapper">
                {{ start_chars }}...{{ end_chars }}
            </span>
        {% else %}
            {{ cell_value }}
        {% endif %}
    {% endif %}
</td>
```

### CSS Priority (`tables.css`)

```css
/* Priority 1: Default for ALL cells */
.universal-data-table td {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
}

/* Priority 2: Override for text-wrap cells */
.universal-data-table td.text-wrap {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: normal !important;
    word-wrap: break-word !important;
}
```

**Order**: More specific selector (`.universal-data-table td.text-wrap`) wins

---

## Migration Guide

### Migrating Existing Entity to Use Wrapping

**Before**:
```python
FieldDefinition(
    name='supplier_name',
    label='Supplier',
    field_type=FieldType.TEXT,
    show_in_list=True,
    width='150px',
)
```

**After**:
```python
FieldDefinition(
    name='supplier_name',
    label='Supplier',
    field_type=FieldType.TEXT,
    show_in_list=True,
    css_classes='text-wrap align-top',  # ← Add this
    width='180px',  # ← Increase width
)
```

**Steps**:
1. Add `css_classes='text-wrap align-top'`
2. Increase `width` by 20-30%
3. Test with long names
4. Adjust width if needed

---

## Quick Reference Card

### Text Wrapping Configuration

```python
FieldDefinition(
    name='field_name',
    label='Field Label',
    field_type=FieldType.TEXT,
    show_in_list=True,
    css_classes='text-wrap align-top',  # ← Enable wrapping
    width='180px',  # ← Set appropriate width
)
```

### Default Truncation (No Config Needed)

```python
FieldDefinition(
    name='field_name',
    label='Field Label',
    field_type=FieldType.TEXT,
    show_in_list=True,
    # css_classes=''  # ← Default truncation
    width='120px',
)
```

### Currency/Numbers (Right Aligned)

```python
FieldDefinition(
    name='amount_field',
    label='Amount',
    field_type=FieldType.CURRENCY,  # ← Auto right-align
    show_in_list=True,
    width='120px',
)
```

---

## Conclusion

Universal Engine table column display is flexible and configuration-driven. Key principles:

1. **Default = Truncate**: Safe, compact, backward compatible
2. **Opt-in Wrapping**: Use `css_classes='text-wrap'` when full content is critical
3. **Width Matters**: Increase width when enabling wrapping
4. **Consistency**: Use same approach for similar fields across entities
5. **Test**: Always test with real data (long names, edge cases)

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or consult the development team.

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Maintained By**: Development Team
**Related Documents**:
- Entity Dropdown Enhancement - Complete Implementation v3.0.md
- Universal Engine Entity Configuration Complete Guide v6.0.md
