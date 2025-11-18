# Patient Autocomplete Filter Implementation Guide

## Document Overview

| **Attribute** | **Details** |
|---------------|-------------|
| **Version** | v1.0 |
| **Date** | 2025-11-10 |
| **Status** | PRODUCTION READY |
| **Purpose** | Implement patient autocomplete filter in Universal Engine list views |

---

## Overview

This guide explains how to add a patient autocomplete dropdown filter to Universal Engine list views (like Consolidated Invoices, Patient Invoices, etc.). The implementation shows an initial list of recent patients that gets shorter as the user types.

## Key Features

✅ **Initial Patient List**: Shows 20 most recent patients on focus (no typing required)
✅ **Progressive Filtering**: List narrows down as user types
✅ **Fast Search**: Uses GET API with caching
✅ **Universal Pattern**: Same implementation works for all entity list views
✅ **No CSRF Issues**: Uses simple GET requests
✅ **Responsive UI**: Dark mode support, loading indicators, smooth transitions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Universal List Template (universal_list.html)          │
│  - Filter Card with Patient Autocomplete Field          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript (inline in template)                        │
│  - Detects patient autocomplete filters                 │
│  - Initializes PatientAutocompleteFilter class          │
│  - Handles search, selection, form submission           │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  GET API: /api/universal/patients/search                │
│  - Query params: ?q=searchterm&limit=20                 │
│  - Returns: {success, results, count}                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Service applies filter to entity search                │
│  - Filters by patient_id or patient_name                │
│  - Returns filtered list of invoices/records            │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Update Entity Configuration

**File**: `app/config/modules/[entity]_config.py`

**For Consolidated Patient Invoices**:

```python
# In consolidated_patient_invoices_config.py

# BEFORE (Line 124-137):
FieldDefinition(
    name="patient_name",
    label="Patient Name",
    field_type=FieldType.TEXT,
    show_in_list=True,
    show_in_detail=True,
    filterable=True,
    searchable=True,
    sortable=True,
    readonly=True,
    view_order=3,
    filter_type=FilterType.TEXT,  # OLD: Simple text filter
    filter_operator=FilterOperator.CONTAINS
),

# AFTER:
FieldDefinition(
    name="patient_name",
    label="Patient Name",
    field_type=FieldType.TEXT,
    show_in_list=True,
    show_in_detail=True,
    filterable=True,
    searchable=True,
    sortable=True,
    readonly=True,
    view_order=3,
    filter_type=FilterType.AUTOCOMPLETE,  # NEW: Autocomplete filter
    filter_operator=FilterOperator.EQUALS,
    autocomplete_config={
        'entity_type': 'patients',
        'api_endpoint': '/api/universal/patients/search',
        'value_field': 'patient_id',        # Field to filter on (hidden)
        'display_field': 'label',           # Field to display
        'placeholder': 'Search patients...',
        'min_chars': 0,                     # 0 = show initial list on focus
        'initial_load_limit': 20,           # Number of recent patients to show
        'search_limit': 10                  # Results when searching
    }
),

# Also update patient_id field to support filtering
FieldDefinition(
    name="patient_id",
    label="Patient ID",
    field_type=FieldType.TEXT,
    show_in_list=False,
    show_in_detail=False,
    filterable=True,  # NEW: Enable filtering by patient_id
    readonly=True
),
```

**Key Configuration Options**:

| Option | Type | Description |
|--------|------|-------------|
| `filter_type` | Enum | Set to `FilterType.AUTOCOMPLETE` |
| `entity_type` | str | Entity to search (e.g., 'patients', 'suppliers') |
| `api_endpoint` | str | GET API endpoint for search |
| `value_field` | str | Field name to use as filter value (UUID) |
| `display_field` | str | Field name to display in input |
| `min_chars` | int | Minimum characters to trigger search (0 = show on focus) |
| `initial_load_limit` | int | Number of items to show initially |
| `search_limit` | int | Number of results when searching |

---

### Step 2: Add FilterType.AUTOCOMPLETE to core_definitions.py

**File**: `app/config/core_definitions.py` (around line 100)

```python
class FilterType(Enum):
    """Filter input types for Universal Engine filters"""
    DEFAULT = "default"
    TEXT = "text"
    SELECT = "select"
    DATE_RANGE = "date_range"
    ENTITY_DROPDOWN = "entity_dropdown"
    AUTOCOMPLETE = "autocomplete"  # NEW: Autocomplete filter
    MULTI_SELECT = "multi_select"
    NUMERIC_RANGE = "numeric_range"
```

---

### Step 3: Update Filter Processor

**File**: `app/engine/categorized_filter_processor.py`

**Update `get_template_filter_fields` method** (around line 1624):

```python
def get_template_filter_fields(self, current_filters: Dict, hospital_id: uuid.UUID,
                               branch_id: Optional[uuid.UUID] = None) -> List[Dict]:
    """Generate filter fields for template rendering"""
    filter_fields = []

    for field_name, field in self.filterable_fields.items():
        # ... existing code ...

        # NEW: Handle autocomplete filter type
        if (hasattr(field, 'filter_type') and
            field.filter_type == FilterType.AUTOCOMPLETE and
            hasattr(field, 'autocomplete_config')):

            config = field.autocomplete_config
            current_value = current_filters.get(config.get('value_field', field_name), '')

            filter_fields.append({
                'name': config.get('value_field', field_name),
                'display_name': field_name,  # For display in search input
                'label': base_label,
                'type': 'autocomplete',
                'value': current_value,
                'placeholder': config.get('placeholder', f"Search {base_label}..."),
                'required': False,
                'autocomplete_config': config
            })
            continue  # Skip normal processing

        # ... rest of existing code ...
```

**Update `_map_field_to_input_type` method** (around line 1660):

```python
def _map_field_to_input_type(self, field) -> str:
    from app.config.core_definitions import FieldType, FilterType

    # Check explicit filter_type first
    if hasattr(field, 'filter_type') and field.filter_type:
        if field.filter_type == FilterType.ENTITY_DROPDOWN:
            return 'entity_dropdown'
        elif field.filter_type == FilterType.AUTOCOMPLETE:  # NEW
            return 'autocomplete'
        elif field.filter_type != FilterType.DEFAULT:
            return field.filter_type.value

    # ... rest of existing code ...
```

---

### Step 4: Update Universal List Template

**File**: `app/templates/engine/universal_list.html`

**Add autocomplete filter rendering** (around line 2155, in filter fields loop):

```html
{% if field.type == 'autocomplete' %}
    <div class="universal-form-group">
        <label class="universal-form-label">{{ field.label }}</label>
        <div class="patient-autocomplete-wrapper" style="position: relative;">
            <!-- Display input (visible) -->
            <input type="text"
                   id="{{ field.display_name }}_search"
                   class="universal-form-input patient-autocomplete-search"
                   placeholder="{{ field.placeholder }}"
                   autocomplete="off"
                   data-autocomplete-type="patient"
                   data-value-field="{{ field.name }}"
                   data-display-field="{{ field.display_name }}"
                   data-config='{{ field.autocomplete_config | tojson }}'>

            <!-- Hidden field for actual value (UUID) -->
            <input type="hidden"
                   name="{{ field.name }}"
                   id="{{ field.name }}"
                   value="{{ field.value }}">

            <!-- Dropdown results -->
            <div id="{{ field.display_name }}_dropdown"
                 class="patient-autocomplete-dropdown absolute z-50 w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg hidden mt-1 max-h-60 overflow-y-auto">
            </div>

            <!-- Loading indicator -->
            <div id="{{ field.display_name }}_loading"
                 class="absolute right-3 top-3 hidden">
                <i class="fas fa-spinner fa-spin text-gray-400"></i>
            </div>
        </div>
    </div>

{% elif field.type == 'entity_dropdown' %}
    <!-- Existing entity dropdown code -->

{% elif field.type == 'select' and field.options|length > 0 %}
    <!-- Existing select code -->
```

**Add CSS styles** (in `<style>` block or separate CSS file):

```html
<style>
/* Patient Autocomplete Filter Styles */
.patient-autocomplete-wrapper {
    position: relative;
}

.patient-autocomplete-dropdown {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    max-height: 300px;
    overflow-y: auto;
}

.patient-autocomplete-item {
    padding: 0.5rem 0.75rem;
    cursor: pointer;
    transition: background-color 0.15s ease-in-out;
    border-bottom: 1px solid #e5e7eb;
}

.dark .patient-autocomplete-item {
    border-bottom-color: #374151;
}

.patient-autocomplete-item:last-child {
    border-bottom: none;
}

.patient-autocomplete-item:hover {
    background-color: #f3f4f6;
}

.dark .patient-autocomplete-item:hover {
    background-color: #374151;
}

.patient-autocomplete-item .patient-name {
    font-weight: 500;
    color: #111827;
}

.dark .patient-autocomplete-item .patient-name {
    color: #f9fafb;
}

.patient-autocomplete-item .patient-mrn {
    font-size: 0.875rem;
    color: #6b7280;
}

.dark .patient-autocomplete-item .patient-mrn {
    color: #9ca3af;
}
</style>
```

**Add JavaScript initialization** (before `{% endblock content %}`):

```html
<script>
// Patient Autocomplete Filter Implementation
class PatientAutocompleteFilter {
    constructor(searchInput) {
        this.searchInput = searchInput;
        this.config = JSON.parse(searchInput.dataset.config);
        this.valueField = searchInput.dataset.valueField;
        this.displayField = searchInput.dataset.displayField;

        this.hiddenInput = document.getElementById(this.valueField);
        this.dropdown = document.getElementById(`${this.displayField}_dropdown`);
        this.loadingIcon = document.getElementById(`${this.displayField}_loading`);

        this.searchTimeout = null;
        this.searchCache = new Map();

        this.init();
    }

    init() {
        // Handle input with debounce
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            clearTimeout(this.searchTimeout);

            if (query.length === 0) {
                // Show initial list when cleared
                this.searchTimeout = setTimeout(() => {
                    this.performSearch('', this.config.initial_load_limit);
                }, 200);
            } else if (query.length >= this.config.min_chars) {
                this.searchTimeout = setTimeout(() => {
                    this.performSearch(query, this.config.search_limit);
                }, 300);
            } else {
                this.hideDropdown();
            }
        });

        // Show initial list on focus
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.trim().length === 0) {
                this.performSearch('', this.config.initial_load_limit);
            }
        });

        // Hide dropdown on outside click
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.hideDropdown();
            }
        });

        console.log(`✅ Patient autocomplete filter initialized for ${this.displayField}`);
    }

    async performSearch(query, limit) {
        const cacheKey = `${query}_${limit}`;

        // Check cache
        if (this.searchCache.has(cacheKey)) {
            this.displayResults(this.searchCache.get(cacheKey));
            return;
        }

        this.showLoading();

        try {
            const url = `${this.config.api_endpoint}?q=${encodeURIComponent(query)}&limit=${limit}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.success && data.results) {
                this.searchCache.set(cacheKey, data.results);
                this.displayResults(data.results);
            } else {
                this.showNoResults();
            }
        } catch (error) {
            console.error('Patient search error:', error);
            this.showError();
        } finally {
            this.hideLoading();
        }
    }

    displayResults(results) {
        if (!results || results.length === 0) {
            this.showNoResults();
            return;
        }

        this.dropdown.innerHTML = '';

        results.forEach(patient => {
            const item = document.createElement('div');
            item.className = 'patient-autocomplete-item';

            item.innerHTML = `
                <div class="patient-name">${patient.label}</div>
                ${patient.mrn ? `<div class="patient-mrn">MRN: ${patient.mrn}</div>` : ''}
            `;

            item.addEventListener('click', () => {
                this.selectPatient(patient);
            });

            this.dropdown.appendChild(item);
        });

        this.showDropdown();
    }

    selectPatient(patient) {
        // Set display value
        this.searchInput.value = patient.label;

        // Set hidden value (UUID or patient_id)
        this.hiddenInput.value = patient[this.config.value_field] || patient.value;

        this.hideDropdown();

        console.log(`✅ Patient selected: ${patient.label}`);
    }

    showLoading() {
        this.loadingIcon?.classList.remove('hidden');
    }

    hideLoading() {
        this.loadingIcon?.classList.add('hidden');
    }

    showDropdown() {
        this.dropdown.classList.remove('hidden');
    }

    hideDropdown() {
        this.dropdown.classList.add('hidden');
    }

    showNoResults() {
        this.dropdown.innerHTML = '<div class="patient-autocomplete-item text-center text-gray-500 dark:text-gray-400">No patients found</div>';
        this.showDropdown();
    }

    showError() {
        this.dropdown.innerHTML = '<div class="patient-autocomplete-item text-center text-red-500">Search failed. Please try again.</div>';
        this.showDropdown();
    }
}

// Auto-initialize all patient autocomplete filters
document.addEventListener('DOMContentLoaded', function() {
    const patientSearchInputs = document.querySelectorAll('.patient-autocomplete-search');

    patientSearchInputs.forEach(input => {
        new PatientAutocompleteFilter(input);
    });

    if (patientSearchInputs.length > 0) {
        console.log(`✅ Initialized ${patientSearchInputs.length} patient autocomplete filter(s)`);
    }
});
</script>
```

---

## Step 5: Update Patient Search API (Optional Enhancement)

**File**: `app/api/routes/universal_api.py`

**Enhance to support initial load** (already done, but verify):

```python
@universal_api_bp.route('/<entity_type>/search', methods=['GET'])
@login_required
def entity_search(entity_type: str):
    """
    Universal entity search endpoint for dropdown searches

    Query Parameters:
        q: Search query string (empty = return recent items)
        limit: Maximum results to return (default 10, max 50)
    """
    try:
        # ... existing validation code ...

        search_term = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)

        # ... existing search code ...

        if entity_type == 'patients':
            results = search_patients(search_term, hospital_id, branch_id, limit)

        # ... rest of code ...
```

**In `search_patients` function** (around line 213):

```python
def search_patients(search_term: str, hospital_id: uuid.UUID,
                   branch_id: uuid.UUID, limit: int) -> List[Dict]:
    """
    Search patients - returns name for display and filtering
    Supports initial load (empty search_term) for recent patients
    """
    try:
        from app.models.master import Patient

        with get_db_session() as session:
            query = session.query(Patient).filter(
                Patient.hospital_id == hospital_id
            )

            # Apply soft delete filter
            if hasattr(Patient, 'deleted_at'):
                query = query.filter(Patient.deleted_at.is_(None))
            elif hasattr(Patient, 'is_deleted'):
                query = query.filter(Patient.is_deleted == False)

            # Add search filter ONLY if search term provided
            if search_term and search_term.strip():
                search_pattern = f'%{search_term}%'
                # ... existing search logic ...

            # Order by most recent first (for initial load)
            if hasattr(Patient, 'created_at'):
                query = query.order_by(Patient.created_at.desc())
            elif hasattr(Patient, 'first_name'):
                query = query.order_by(Patient.first_name, Patient.last_name)

            # Apply limit
            patients = query.limit(limit).all()

            # Format results
            results = []
            for patient in patients:
                # ... existing formatting ...
                results.append({
                    'value': str(patient.patient_id),
                    'label': display_name,
                    'subtitle': patient.mrn,
                    'patient_id': str(patient.patient_id),
                    'patient_name': patient_name,
                    'mrn': patient.mrn or '',
                    # ... other fields ...
                })

            return results
```

---

## Implementation Checklist

### For Each Entity List View:

- [ ] **Step 1**: Update entity configuration file
  - [ ] Import `FilterType` enum
  - [ ] Change patient field `filter_type` to `FilterType.AUTOCOMPLETE`
  - [ ] Add `autocomplete_config` dictionary
  - [ ] Enable `filterable=True` on patient_id field

- [ ] **Step 2**: Update core_definitions.py (ONE TIME)
  - [ ] Add `AUTOCOMPLETE` to `FilterType` enum

- [ ] **Step 3**: Update categorized_filter_processor.py (ONE TIME)
  - [ ] Add autocomplete handling in `get_template_filter_fields`
  - [ ] Add autocomplete case in `_map_field_to_input_type`

- [ ] **Step 4**: Update universal_list.html (ONE TIME)
  - [ ] Add HTML template for autocomplete filter
  - [ ] Add CSS styles
  - [ ] Add JavaScript PatientAutocompleteFilter class
  - [ ] Add auto-initialization code

- [ ] **Step 5**: Test implementation
  - [ ] Navigate to list view
  - [ ] Click patient filter - should show initial list
  - [ ] Type search term - list should filter
  - [ ] Select patient - form should submit with patient_id
  - [ ] Results should be filtered by selected patient

---

## Entities to Update

### Priority 1 (Patient-Related):
1. ✅ **Patient Invoices** (`patient_invoice_config.py`)
2. ✅ **Consolidated Patient Invoices** (`consolidated_patient_invoices_config.py`)
3. **Patient Payments** (if exists)
4. **Patient Appointments** (if exists)

### Priority 2 (Other Entities with Patient):
5. **Prescriptions** (if exists)
6. **Lab Reports** (if exists)
7. **Medical Records** (if exists)

---

## Testing Guide

### Manual Testing Steps:

1. **Initial Load Test**:
   - Navigate to Consolidated Invoice List
   - Click on Patient Name filter field
   - **Expected**: Dropdown shows 20 most recent patients immediately
   - **Verify**: No API errors in console

2. **Progressive Filter Test**:
   - With dropdown open, type "Jo"
   - **Expected**: List filters to patients matching "Jo"
   - **Verify**: API call made after 300ms debounce

3. **Selection Test**:
   - Click on a patient from dropdown
   - **Expected**: Patient name appears in input, dropdown closes
   - **Verify**: Hidden field has patient_id UUID

4. **Filter Submission Test**:
   - Click "Apply Filters" button
   - **Expected**: Page reloads with filtered results
   - **Verify**: URL contains patient_id parameter
   - **Verify**: List shows only invoices for selected patient

5. **Clear Filter Test**:
   - Clear patient field
   - Click "Apply Filters"
   - **Expected**: All invoices shown (no patient filter)

### Automated Testing (Optional):

```python
# tests/test_patient_autocomplete_filter.py

def test_patient_search_api_initial_load(client, auth_headers):
    """Test API returns initial patient list"""
    response = client.get(
        '/api/universal/patients/search?q=&limit=20',
        headers=auth_headers
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['results']) <= 20

def test_patient_search_api_with_query(client, auth_headers):
    """Test API filters patients by search query"""
    response = client.get(
        '/api/universal/patients/search?q=John&limit=10',
        headers=auth_headers
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data['success'] is True
    assert all('John' in result['label'] for result in data['results'])

def test_patient_filter_in_invoice_list(client, auth_headers, test_patient):
    """Test invoice list filters by patient"""
    response = client.get(
        f'/universal/consolidated_patient_invoices/list?patient_id={test_patient.patient_id}',
        headers=auth_headers
    )

    assert response.status_code == 200
    # Verify all invoices belong to test_patient
```

---

## Performance Considerations

### 1. **Caching Strategy**:
```javascript
// Client-side cache (5 minutes)
this.searchCache = new Map();
const CACHE_TTL = 5 * 60 * 1000;

// Add timestamp to cache entries
this.searchCache.set(cacheKey, {
    data: data.results,
    timestamp: Date.now()
});

// Check cache expiry
const cached = this.searchCache.get(cacheKey);
if (cached && (Date.now() - cached.timestamp) < CACHE_TTL) {
    return cached.data;
}
```

### 2. **Database Query Optimization**:
```python
# Add index for patient search
CREATE INDEX idx_patient_name_search ON patients(first_name, last_name);
CREATE INDEX idx_patient_mrn ON patients(mrn);
CREATE INDEX idx_patient_created_at ON patients(created_at DESC);
```

### 3. **API Rate Limiting** (Optional):
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: current_user.id)

@universal_api_bp.route('/<entity_type>/search', methods=['GET'])
@limiter.limit("60 per minute")  # Max 60 searches per minute
def entity_search(entity_type: str):
    # ... existing code ...
```

---

## Troubleshooting

### Issue 1: Dropdown Not Showing Initial List
**Symptom**: Clicking patient field shows nothing
**Cause**: API not returning results for empty query
**Fix**: Verify `search_patients` handles empty `search_term`

```python
# In search_patients function
if search_term and search_term.strip():
    # Add search filter
    query = query.filter(...)
else:
    # No search term = return recent patients
    pass  # Don't filter, just apply limit
```

### Issue 2: Filter Not Applied After Selection
**Symptom**: Selecting patient doesn't filter list
**Cause**: Wrong field name in hidden input
**Fix**: Ensure hidden input name matches filter parameter

```html
<!-- Make sure name matches the filterable field -->
<input type="hidden"
       name="patient_id"  <!-- Must match field in config -->
       value="{{ patient_uuid }}">
```

### Issue 3: CSRF Token Error
**Symptom**: Console shows "CSRF token missing"
**Cause**: Using POST instead of GET
**Fix**: Ensure API endpoint uses GET method

```python
@universal_api_bp.route('/<entity_type>/search', methods=['GET'])  # Not POST
```

### Issue 4: Dark Mode Styling Issues
**Symptom**: Dropdown unreadable in dark mode
**Fix**: Add dark mode CSS classes

```html
<div class="bg-white dark:bg-gray-800">
    <div class="text-gray-900 dark:text-gray-100">...</div>
</div>
```

---

## Extension: Supplier Autocomplete Filter

The same pattern works for supplier filters:

```python
# In purchase_orders_config.py
FieldDefinition(
    name="supplier_name",
    label="Supplier",
    field_type=FieldType.TEXT,
    filterable=True,
    filter_type=FilterType.AUTOCOMPLETE,
    autocomplete_config={
        'entity_type': 'suppliers',
        'api_endpoint': '/api/universal/suppliers/search',
        'value_field': 'supplier_id',
        'display_field': 'label',
        'placeholder': 'Search suppliers...',
        'min_chars': 0,
        'initial_load_limit': 20,
        'search_limit': 10
    }
),
```

---

## Summary

This implementation provides:
- ✅ **Universal Pattern**: Works for any entity (patients, suppliers, medicines, etc.)
- ✅ **Initial List**: Shows recent items on focus (no typing required)
- ✅ **Progressive Filtering**: Narrows down as user types
- ✅ **Fast Performance**: Client-side caching, debounced search
- ✅ **Clean UX**: Loading indicators, error handling, dark mode
- ✅ **Maintainable**: Configuration-driven, minimal code duplication

**Estimated Implementation Time per Entity**: 15-20 minutes

**One-Time Setup (Steps 2-4)**: 30-45 minutes

**Total for 4 Entities**: ~2 hours

---

## Next Steps

1. Implement for **Consolidated Patient Invoices** (highest priority)
2. Implement for **Patient Invoices**
3. Test both implementations thoroughly
4. Apply to other patient-related entities
5. Consider extending to supplier/medicine filters

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-11-10 | Initial document created |

---

## References

- Universal Engine Entity Configuration Guide v6.0
- Entity Dropdown Enhancement v2.0
- Patient Search API: `app/api/routes/universal_api.py:213`
- Create Invoice Implementation: `app/templates/billing/create_invoice.html:834-964`
