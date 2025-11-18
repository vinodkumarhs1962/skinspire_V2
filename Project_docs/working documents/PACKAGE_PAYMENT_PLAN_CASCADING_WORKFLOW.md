# Package Payment Plan - Cascading Workflow Implementation

**Date:** 2025-01-11
**Status:** Backend ✅ Complete | Frontend 🔄 Custom Template Needed

---

## Correct Workflow

### User Experience Flow:
```
1. Select Patient (Autocomplete)
   ↓
2. Select Invoice (Only invoices with packages for this patient)
   ↓
3. Auto-populate all details from invoice
   ↓
4. Configure installment schedule
   ↓
5. Submit → Auto-generate installments and sessions
```

### Why This Workflow?
- Payment plans are created **AFTER** an invoice with a package is generated
- The invoice already contains the package, patient, and amount
- No need to manually re-enter package details
- Ensures data consistency and traceability

---

## Backend Implementation ✅ COMPLETE

### 1. Database Schema ✅
**Tables Updated:**
- `package_payment_plans`:
  - `invoice_id` UUID FK → `invoice_header.invoice_id` ✅
  - `package_id` UUID FK → `packages.package_id` ✅
  - `patient_id` UUID FK → `patients.patient_id` ✅
  - Indexes created for performance ✅

### 2. Model Updates ✅
**File:** `app/models/transaction.py`

```python
class PackagePaymentPlan(Base, TimestampMixin, TenantMixin):
    # References
    patient_id = Column(UUID, ForeignKey('patients.patient_id'), nullable=False)
    invoice_id = Column(UUID, ForeignKey('invoice_header.invoice_id'))  # ✅ NEW
    package_id = Column(UUID, ForeignKey('packages.package_id'))

    # Relationships
    patient = relationship("Patient")
    invoice = relationship("InvoiceHeader", foreign_keys=[invoice_id])  # ✅ NEW
    package = relationship("Package")
    installments = relationship("InstallmentPayment", ...)
    sessions = relationship("PackageSession", ...)
```

### 3. API Endpoints ✅
**File:** `app/api/routes/package_api.py`

**Endpoint 1: Get Patient Invoices with Packages**
```
GET /api/package/patient/<patient_id>/invoices-with-packages

Response:
{
    "success": true,
    "invoices": [
        {
            "invoice_id": "uuid",
            "invoice_number": "INV-001",
            "invoice_date": "2025-01-11",
            "package_id": "uuid",
            "package_name": "Laser Hair Reduction - 5 Sessions",
            "package_price": 50000.00,
            "line_item_total": 50000.00,
            "invoice_status": "approved"
        }
    ],
    "count": 3
}
```

**Endpoint 2: Complete Session** (Already implemented)
```
POST /api/package/session/<session_id>/complete
```

**Endpoint 3: Get Pending Installments** (Already implemented)
```
GET /api/package/patient/<patient_id>/pending-installments
```

### 4. Service Layer ✅
**File:** `app/services/package_payment_service.py`

**Method 1: Get Patient Invoices with Packages**
```python
def get_patient_invoices_with_packages(self, patient_id, hospital_id):
    """
    Queries:
    - invoice_header
    - invoice_line_item (where package_id is not null)
    - packages (join to get package details)

    Filters:
    - patient_id matches
    - hospital_id matches
    - invoice status in ['approved', 'paid', 'partial']
    - invoice not deleted

    Returns: List of invoices with package line items
    """
```

**Method 2: Fetch Package Details** (Already implemented)
```python
def _fetch_package_details(self, package_id, hospital_id):
    """Fetches package from packages master table"""
```

**Method 3: Create with Auto-population** (Already enhanced)
```python
def create(self, data, hospital_id, branch_id, **context):
    """
    1. Fetch package details if package_id provided
    2. Auto-populate total_amount from package.price
    3. Call parent create
    4. Auto-generate installments
    5. Auto-generate sessions
    """
```

---

## Frontend Implementation 🔄 TODO

### Current Issue:
Universal Engine auto-generates a form, but we need a **custom form** with:
1. Patient autocomplete (like payment screen)
2. Cascading invoice dropdown (filtered by patient)
3. Auto-population of fields when invoice is selected

### Solution: Create Custom Create Route & Template

#### Option 1: Override Universal Create Route
Create custom route that bypasses Universal Engine's auto-generated form:

**File:** `app/views/universal_views.py` or separate blueprint

```python
@app.route('/package-payment-plans/create', methods=['GET', 'POST'])
@login_required
def create_package_payment_plan():
    """Custom create form with cascading workflow"""
    if request.method == 'GET':
        return render_template('package/create_payment_plan.html')

    # POST - Handle form submission
    data = request.form.to_dict()
    service = PackagePaymentService()
    result = service.create(data, g.hospital_id, g.branch_id, created_by=current_user.user_id)

    if result['success']:
        flash('Payment plan created successfully', 'success')
        return redirect(url_for('universal_views.universal_detail_view',
                                entity_type='package_payment_plans',
                                item_id=result['data']['plan_id']))
    else:
        flash(f"Error: {result.get('error')}", 'error')
        return render_template('package/create_payment_plan.html', error=result.get('error'))
```

#### Option 2: Custom Template with JavaScript

**File:** `app/templates/package/create_payment_plan.html` (TODO - CREATE THIS)

**Structure:**
```html
{% extends "layouts/dashboard.html" %}

{% block content %}
<div class="container-fluid">
    <!-- Step 1: Patient Selection -->
    <div class="patient-selection">
        <input type="text" id="patient-search" placeholder="Search patient...">
        <div id="patient-results"></div>
        <div id="selected-patient-card" class="hidden"></div>
    </div>

    <!-- Step 2: Invoice Selection (shown after patient selected) -->
    <div id="invoice-selection" class="hidden">
        <label>Select Invoice</label>
        <select id="invoice-select">
            <option value="">Select invoice with package...</option>
        </select>
    </div>

    <!-- Step 3: Auto-populated Plan Details (shown after invoice selected) -->
    <div id="plan-details" class="hidden">
        <!-- Package info (readonly, auto-populated) -->
        <input type="hidden" id="invoice_id">
        <input type="hidden" id="package_id">

        <div class="form-group">
            <label>Package</label>
            <input type="text" id="package_name" readonly>
        </div>

        <div class="form-group">
            <label>Total Amount</label>
            <input type="number" id="total_amount" readonly>
        </div>

        <div class="form-group">
            <label>Total Sessions</label>
            <input type="number" id="total_sessions" min="1" required>
        </div>

        <!-- Installment Configuration -->
        <div class="form-group">
            <label>Number of Installments</label>
            <input type="number" id="installment_count" min="1" max="12" required>
        </div>

        <div class="form-group">
            <label>Installment Frequency</label>
            <select id="installment_frequency">
                <option value="monthly">Monthly</option>
                <option value="biweekly">Bi-weekly</option>
                <option value="weekly">Weekly</option>
            </select>
        </div>

        <div class="form-group">
            <label>First Installment Date</label>
            <input type="date" id="first_installment_date" required>
        </div>

        <button type="submit" class="btn btn-primary">Create Payment Plan</button>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/package_payment_plan_create.js') }}"></script>
{% endblock %}
```

**File:** `app/static/js/package_payment_plan_create.js` (TODO - CREATE THIS)

**JavaScript Logic:**
```javascript
// Step 1: Patient Search (Reuse from payment_patient_selection.html)
const searchInput = document.getElementById('patient-search');
searchInput.addEventListener('input', debounce(searchPatients, 300));

async function searchPatients(query) {
    const response = await fetch(`/api/universal/patients/search?q=${query}`);
    const data = await response.json();
    displayPatientResults(data.results);
}

function selectPatient(patientId) {
    selectedPatientId = patientId;

    // Show invoice selection
    document.getElementById('invoice-selection').classList.remove('hidden');

    // Load invoices for this patient
    loadPatientInvoices(patientId);
}

// Step 2: Load Invoices
async function loadPatientInvoices(patientId) {
    const response = await fetch(`/api/package/patient/${patientId}/invoices-with-packages`);
    const data = await response.json();

    const select = document.getElementById('invoice-select');
    select.innerHTML = '<option value="">Select invoice...</option>';

    data.invoices.forEach(inv => {
        const option = document.createElement('option');
        option.value = inv.invoice_id;
        option.textContent = `${inv.invoice_number} - ${inv.package_name} - ₹${inv.line_item_total}`;
        option.dataset.packageId = inv.package_id;
        option.dataset.packageName = inv.package_name;
        option.dataset.totalAmount = inv.line_item_total;
        select.appendChild(option);
    });
}

// Step 3: Invoice Selected → Auto-populate
document.getElementById('invoice-select').addEventListener('change', function() {
    const selectedOption = this.options[this.selectedIndex];

    if (!selectedOption.value) return;

    // Auto-populate hidden fields
    document.getElementById('invoice_id').value = selectedOption.value;
    document.getElementById('package_id').value = selectedOption.dataset.packageId;

    // Auto-populate visible fields (readonly)
    document.getElementById('package_name').value = selectedOption.dataset.packageName;
    document.getElementById('total_amount').value = selectedOption.dataset.totalAmount;

    // Show plan details section
    document.getElementById('plan-details').classList.remove('hidden');
});

// Step 4: Form Submit
document.getElementById('payment-plan-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = {
        patient_id: selectedPatientId,
        invoice_id: document.getElementById('invoice_id').value,
        package_id: document.getElementById('package_id').value,
        total_amount: document.getElementById('total_amount').value,
        total_sessions: document.getElementById('total_sessions').value,
        installment_count: document.getElementById('installment_count').value,
        installment_frequency: document.getElementById('installment_frequency').value,
        first_installment_date: document.getElementById('first_installment_date').value
    };

    const response = await fetch('/package-payment-plans/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    });

    const result = await response.json();

    if (result.success) {
        window.location.href = `/universal/package_payment_plans/detail/${result.plan_id}`;
    } else {
        alert('Error: ' + result.error);
    }
});
```

---

## Data Flow Diagram

```
User Action                     Backend API                          Database
─────────────────────────────────────────────────────────────────────────────
1. Types "John"              → GET /api/universal/patients/search
                                                                  → patients table
                             ← Returns: [{patient_id, name, mrn}]

2. Selects "John Doe"        → GET /api/package/patient/xxx/invoices-with-packages
                                                                  → invoice_header
                                                                     invoice_line_item
                                                                     packages
                             ← Returns: [{invoice_id, inv_number,
                                         package_id, package_name,
                                         total_amount}]

3. Selects "INV-001"         → JavaScript auto-populates:
                                - invoice_id (hidden)
                                - package_id (hidden)
                                - package_name (readonly)
                                - total_amount (readonly)

4. Enters installment config → User fills:
                                - total_sessions: 5
                                - installment_count: 3
                                - frequency: monthly
                                - first_date: 2025-02-01

5. Clicks "Create"           → POST /package-payment-plans/create
                                with complete form data
                                                                  → package_payment_plans
                                                                     installment_payments (x3)
                                                                     package_sessions (x5)
                             ← Returns: {success, plan_id}

6. Redirect to detail view   → /universal/package_payment_plans/detail/{plan_id}
```

---

## Implementation Checklist

### ✅ Backend (COMPLETE)
- [x] Add invoice_id column to database
- [x] Create FK constraint to invoice_header
- [x] Update PackagePaymentPlan model with invoice_id
- [x] Add invoice relationship to model
- [x] Create API endpoint: GET /api/package/patient/<id>/invoices-with-packages
- [x] Implement service method: get_patient_invoices_with_packages()
- [x] Enhance create service to handle invoice-based data

### 🔄 Frontend (TODO)
- [ ] Create custom route: `/package-payment-plans/create`
- [ ] Create template: `app/templates/package/create_payment_plan.html`
- [ ] Create JavaScript: `app/static/js/package_payment_plan_create.js`
- [ ] Copy patient autocomplete logic from `payment_patient_selection.html`
- [ ] Implement cascading invoice dropdown
- [ ] Implement auto-population on invoice selection
- [ ] Test complete workflow end-to-end

---

## Testing Workflow

### Prerequisites:
1. Patient exists (e.g., John Doe)
2. Package exists in master (e.g., "Laser Hair Reduction - 5 Sessions")
3. Invoice created for patient with package line item
4. Invoice status = 'approved'

### Test Steps:
1. Navigate to `/package-payment-plans/create`
2. Search for patient "John"
3. Select "John Doe"
4. Verify invoice dropdown populates
5. Select invoice "INV-001"
6. Verify fields auto-populate:
   - Package name: "Laser Hair Reduction - 5 Sessions"
   - Total amount: ₹50,000
7. Enter installment config:
   - Total sessions: 5
   - Installments: 3
   - Frequency: monthly
   - First date: 2025-02-01
8. Click "Create Payment Plan"
9. Verify redirect to detail view
10. Verify 3 installments auto-generated
11. Verify 5 sessions auto-generated

---

## Next Steps

**Priority 1: Create Custom Form (HIGH)**
1. Create the custom route in `app/views/` (new blueprint or add to universal_views.py)
2. Create the template `app/templates/package/create_payment_plan.html`
3. Create the JavaScript `app/static/js/package_payment_plan_create.js`
4. Copy patient autocomplete from `payment_patient_selection.html`
5. Test complete workflow

**Priority 2: Update Menu (MEDIUM)**
- Change "Create Plan" menu link to point to custom route instead of Universal Engine route
- File: `app/utils/menu_utils.py`

**Priority 3: Documentation (LOW)**
- User guide for creating package payment plans
- Training video/screenshots

---

## Files Modified/Created

### Modified ✅
1. `app/models/transaction.py` - Added invoice_id, invoice relationship
2. `app/services/package_payment_service.py` - Added get_patient_invoices_with_packages()
3. `app/api/routes/package_api.py` - Added new API endpoint

### Created ✅
4. `migrations/add_invoice_reference_to_payment_plans.sql` - Database migration

### TODO 🔄
5. `app/views/package_views.py` (NEW) - Custom create route
6. `app/templates/package/create_payment_plan.html` (NEW) - Custom form template
7. `app/static/js/package_payment_plan_create.js` (NEW) - Cascading JavaScript
8. `app/utils/menu_utils.py` - Update menu link

---

## Conclusion

**Backend Implementation:** ✅ COMPLETE
- Database schema updated
- Models enhanced
- API endpoints created
- Service methods implemented

**Frontend Implementation:** 🔄 PENDING
- Custom create form template needed
- Cascading JavaScript needed
- Patient autocomplete integration needed

**Status:** Ready for frontend development. All backend infrastructure is in place and tested.
