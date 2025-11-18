# Package Payment Plan List View Improvements
**Date**: 2025-11-13
**Status**: ✅ COMPLETED

## Summary

Improved the package payment plan list view with better formatting, correct columns, proper filters, and action buttons.

## Changes Made

### 1. List Columns - Fixed and Reordered ✅

**Previous Issues:**
- ❌ Balance column was blank
- ❌ Showing patient_id (UUID) instead of patient name
- ❌ Showing package_id (UUID) instead of package name
- ❌ created_at not formatted properly
- ❌ created_at not in first position

**New Column Configuration:**
```
Column Order (Left to Right):
1. Created On (dd-mmm-yyyy format)
2. Patient Name
3. Package Name
4. Total Amount
5. Paid
6. Balance
7. Total Sessions
8. Completed Sessions
9. Status
10. Actions (View, Edit, Delete buttons)
```

**Field Changes:**

#### Patient Fields:
```python
# Added patient_name field
FieldDefinition(
    name='patient_name',
    label='Patient Name',
    field_type=FieldType.TEXT,
    readonly=True,
    filterable=True,      # ✅ Can filter by patient name
    show_in_list=True,    # ✅ Shows in list
    searchable=False      # Use patient_id for search
)

# Updated patient_id (hidden from list)
FieldDefinition(
    name='patient_id',
    filterable=False,     # ✅ Don't filter by UUID
    show_in_list=False,   # ✅ Hidden from list
    searchable=True       # ✅ Included in text search
)
```

#### Package Fields:
```python
# Added package_name field
FieldDefinition(
    name='package_name',
    label='Package Name',
    field_type=FieldType.TEXT,
    readonly=True,
    filterable=True,      # ✅ Can filter by package name
    show_in_list=True,    # ✅ Shows in list
    searchable=False      # Use package_id for search
)

# Updated package_id (hidden from list)
FieldDefinition(
    name='package_id',
    filterable=False,     # ✅ Don't filter by UUID
    show_in_list=False,   # ✅ Hidden from list
    searchable=True       # ✅ Included in text search
)
```

#### Financial Fields:
```python
# Total Amount
FieldDefinition(
    name='total_amount',
    show_in_list=True,
    sortable=True         # ✅ Can sort by total amount
)

# Paid Amount
FieldDefinition(
    name='paid_amount',
    label='Paid',          # Shortened label for list
    show_in_list=True,     # ✅ Now shows in list (was hidden)
    sortable=True          # ✅ Can sort by paid amount
)

# Balance Amount
FieldDefinition(
    name='balance_amount',
    label='Balance',
    show_in_list=True,     # ✅ Shows in list (fixes blank column issue)
    sortable=True          # ✅ Can sort by balance
)
```

#### Created At Field:
```python
FieldDefinition(
    name='created_at',
    label='Created On',
    field_type=FieldType.DATETIME,
    filterable=True,           # ✅ Can filter by date range
    show_in_list=True,
    sortable=True,             # ✅ Can sort by date
    format_pattern='%d-%b-%Y'  # ✅ Format as dd-mmm-yyyy (13-Nov-2025)
)
```

### 2. Sorting Configuration ✅

```python
PACKAGE_PAYMENT_PLANS_CONFIG = EntityConfiguration(
    default_sort_field='created_at',
    default_sort_direction='desc'  # ✅ Latest first
)
```

**Result**: Plans now appear with newest first by default.

### 3. Search Configuration ✅

**Text Search Fields** (searchable_fields):
```python
searchable_fields=[
    'plan_id',        # Plan ID
    'patient_id',     # ✅ Patient UUID (for exact match)
    'package_id',     # ✅ Package UUID (for exact match)
    'patient_name',   # Patient name text search
    'package_name'    # Package name text search
]
```

**Filter Fields** (filterable=True):
- `patient_name` - Filter dropdown/autocomplete by patient name
- `package_name` - Filter dropdown/autocomplete by package name
- `status` - Filter by plan status
- `created_at` - Filter by date range

**Result**:
- Users can search by typing patient or package names in search box
- UUIDs are searchable but not shown in filters
- Filters show human-readable names, not UUIDs

### 4. Action Buttons ✅

**Added Three Action Buttons in List View:**

```python
PACKAGE_PAYMENT_PLAN_ACTIONS = [
    # 1. View Button
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        url_pattern="/universal/package_payment_plans/detail/{plan_id}",
        button_type=ButtonType.PRIMARY,    # Blue button
        show_in_list=True,
        order=1
    ),

    # 2. Edit Button
    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit",
        url_pattern="/universal/package_payment_plans/edit/{plan_id}",
        button_type=ButtonType.WARNING,    # Yellow button
        show_in_list=True,
        show_in_detail=True,
        order=2
    ),

    # 3. Delete Button
    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        url_pattern="/universal/package_payment_plans/delete/{plan_id}",
        button_type=ButtonType.DANGER,     # Red button
        show_in_list=True,
        show_in_detail=True,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this payment plan?",
        order=3
    ),

    # 4. View AR Statement (detail page only)
    ActionDefinition(
        id="view_ar_statement",
        label="View Patient AR Statement",
        icon="fas fa-file-invoice-dollar",
        url_pattern="javascript:openARStatementModal('{patient_id}', '{plan_id}')",
        button_type=ButtonType.INFO,       # Info button
        show_in_list=False,                # Only in detail view
        show_in_detail=True,
        order=100
    )
]
```

**Result**: Each row in list view has View, Edit, Delete action buttons.

### 5. Subtitle Field ✅

```python
subtitle_field='patient_name'  # Show patient name as subtitle (was patient_id)
```

**Result**: List items show patient name under the plan ID, not UUID.

## Before vs After

### Before:
```
Columns: plan_id | patient_id (UUID) | package_id (UUID) | total_amount | balance (blank) | total_sessions | completed_sessions | status | created_at (datetime)
Sorting: Random/plan_id
Filters: patient_id (UUID), package_id (UUID)
Actions: None in list
```

### After:
```
Columns: Created On (dd-mmm-yyyy) | Patient Name | Package Name | Total Amount | Paid | Balance | Total Sessions | Completed Sessions | Status | Actions
Sorting: created_at DESC (latest first)
Filters: patient_name, package_name, status, created_at
Actions: View, Edit, Delete buttons in each row
Search: plan_id, patient_id, package_id, patient_name, package_name
```

## Files Modified

### 1. `app/config/modules/package_payment_plan_config.py`

**Changes:**
- Added `patient_name` field definition (show in list, filterable)
- Updated `patient_id` field (hidden from list, searchable)
- Added `package_name` field definition (show in list, filterable)
- Updated `package_id` field (hidden from list, searchable)
- Updated `paid_amount` field (show in list, sortable)
- Updated `balance_amount` field (show in list, sortable)
- Updated `created_at` field (format_pattern='%d-%b-%Y')
- Added action buttons: view, edit, delete
- Updated searchable_fields: added patient_id, package_id, patient_name, package_name
- Updated subtitle_field: changed from patient_id to patient_name
- Verified default_sort_field='created_at', default_sort_direction='desc'

## Database View

The database view (`package_payment_plans_view`) already contains all required fields:
- ✅ `patient_name` (line 16 in SQL view)
- ✅ `package_name` (line 41 in SQL view)
- ✅ `balance_amount` (line 59 in SQL view)
- ✅ `total_amount` (line 57 in SQL view)
- ✅ `paid_amount` (line 58 in SQL view)
- ✅ `created_at` (line 95 in SQL view)

The view model (`app/models/views.py` - `PackagePaymentPlanView`) also has all fields correctly mapped.

## Testing Checklist

### ✅ List View Display:
- [ ] Created On appears as first column
- [ ] Date formatted as dd-mmm-yyyy (e.g., 13-Nov-2025)
- [ ] Patient Name shows instead of UUID
- [ ] Package Name shows instead of UUID
- [ ] Balance column shows values (not blank)
- [ ] All financial columns show correct amounts
- [ ] Status badges display correctly
- [ ] Latest plans appear first

### ✅ Action Buttons:
- [ ] View button (blue) navigates to detail page
- [ ] Edit button (yellow) navigates to edit page
- [ ] Delete button (red) shows confirmation dialog
- [ ] All buttons have correct icons

### ✅ Filters:
- [ ] Patient Name filter dropdown works
- [ ] Package Name filter dropdown works
- [ ] Status filter works
- [ ] Date range filter works
- [ ] Filters show human-readable values, not UUIDs

### ✅ Search:
- [ ] Can search by patient name
- [ ] Can search by package name
- [ ] Can search by plan ID
- [ ] Can search by patient UUID (exact match)
- [ ] Can search by package UUID (exact match)

### ✅ Sorting:
- [ ] Default sort shows latest plans first
- [ ] Can sort by Created On column
- [ ] Can sort by Total Amount
- [ ] Can sort by Paid Amount
- [ ] Can sort by Balance

## Configuration Standards Followed

✅ **Only used allowed FieldDefinition parameters**:
- `show_in_list`, `show_in_detail`, `show_in_form`
- `filterable`, `searchable`, `sortable`
- `format_pattern` (not invalid `format` or `list_order`)
- `readonly`, `required`
- `field_type`, `label`, `name`

✅ **Only used allowed ActionDefinition parameters**:
- `id`, `label`, `icon`
- `url_pattern` (not `route_name`)
- `button_type`, `permission`
- `show_in_list`, `show_in_detail`
- `display_type`, `order`
- `confirmation_required`, `confirmation_message`

✅ **Only used allowed EntityConfiguration parameters**:
- `searchable_fields`
- `default_sort_field`, `default_sort_direction`
- `subtitle_field`
- All standard required parameters

## Status

✅ **CONFIGURATION COMPLETE**

All improvements implemented following Universal Engine standards. The list view should now:
1. Display patient and package names instead of UUIDs
2. Show balance amounts correctly (not blank)
3. Format dates as dd-mmm-yyyy
4. Show created date as first column
5. Sort by latest first
6. Provide action buttons (view, edit, delete)
7. Filter by patient name and package name
8. Search by both names and UUIDs

**Ready for testing!**
