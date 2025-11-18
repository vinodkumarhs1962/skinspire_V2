# Patient AR Statement Implementation Plan
**Date**: 2025-11-13
**Feature**: Patient AR (Accounts Receivable) Statement/Breakdown

## Overview

Add a "View AR Statement" button accessible from:
1. **Patient Detail Page** - View complete patient account
2. **Invoice Detail Page** - See invoice in context of patient's full account
3. **Payment Detail Page** - See payment in context of patient's full account
4. **Package Payment Plan Detail Page** - See plan in context of patient's full account

## User Experience

### Button Behavior
- Click "View AR Statement" button
- Modal popup displays patient's complete transaction history
- Shows all invoices, payments, credit notes with running balance
- Highlights current transaction (if opened from invoice/payment/plan)
- Calculates total outstanding/credit balance

### AR Statement Display

**Header:**
```
Patient AR Statement
Patient: John Doe (#PAT-12345)
As of: 13-Nov-2025
Current Balance: -₹4,982.00 (Credit)
```

**Transaction Table:**
```
Date       | Type        | Reference Number       | Debit    | Credit   | Balance
-----------|-------------|------------------------|----------|----------|----------
12-May-25  | Payment     | Adv #xyz123           | -        | 8,840.00 | -8,840.00
12-May-25  | Invoice     | GST/2025-2026/00142   | 9,440.00 | -        | 600.00
12-May-25  | Payment     | PAY-abc123            | -        | 3,146.67 | -2,546.67
13-Nov-25  | Credit Note | CN/2025-2026/00001    | -        | 7,552.00 | -4,982.00 ← HIGHLIGHTED
-----------|-------------|------------------------|----------|----------|----------
TOTALS:                                           | 9,440.00 | 19,538.67| -4,982.00
```

**Summary Section:**
```
Total Invoiced:        ₹32,446.00
Total Paid:            ₹29,876.00
Total Credit Notes:    ₹7,552.00
Net Balance:           -₹4,982.00 (Patient has credit)
```

## Technical Implementation

### 1. Service Layer

**File**: `app/services/ar_statement_service.py`

**Class**: `ARStatementService`

**Methods**:
```python
def get_patient_ar_statement(
    self,
    patient_id: str,
    hospital_id: str,
    highlight_reference_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get complete AR statement for a patient

    Args:
        patient_id: Patient ID
        hospital_id: Hospital ID
        highlight_reference_id: Optional ID to highlight (invoice/payment/credit note)

    Returns:
        {
            'patient_info': {
                'patient_id': str,
                'full_name': str,
                'patient_number': str
            },
            'transactions': [
                {
                    'transaction_date': date,
                    'entry_type': str,
                    'reference_type': str,
                    'reference_number': str,
                    'reference_id': str,
                    'debit_amount': Decimal,
                    'credit_amount': Decimal,
                    'current_balance': Decimal,
                    'is_highlighted': bool
                }
            ],
            'summary': {
                'total_invoiced': Decimal,
                'total_paid': Decimal,
                'total_credit_notes': Decimal,
                'current_balance': Decimal
            },
            'as_of_date': date
        }
    """
```

**Query Logic**:
```python
# Get all AR subledger entries for patient
entries = session.query(ARSubledger).filter(
    and_(
        ARSubledger.patient_id == patient_id,
        ARSubledger.hospital_id == hospital_id
    )
).order_by(
    ARSubledger.transaction_date,
    ARSubledger.created_at
).all()

# Calculate totals by type
total_invoiced = sum(e.debit_amount for e in entries if e.entry_type == 'invoice')
total_paid = sum(e.credit_amount for e in entries if e.entry_type == 'payment')
total_credit_notes = sum(e.credit_amount for e in entries if e.entry_type == 'credit_note')
```

### 2. API Route

**File**: `app/api/routes/billing.py` (add to existing file)

**Route**: `/api/billing/ar-statement/<patient_id>`

**Method**: GET

**Query Parameters**:
- `highlight_id` (optional): Transaction ID to highlight

**Implementation**:
```python
@billing_api.route('/ar-statement/<patient_id>', methods=['GET'])
@login_required
def get_ar_statement(patient_id):
    """Get patient AR statement"""
    try:
        hospital_id = current_user.hospital_id
        highlight_id = request.args.get('highlight_id')

        service = ARStatementService()
        result = service.get_patient_ar_statement(
            patient_id=patient_id,
            hospital_id=hospital_id,
            highlight_reference_id=highlight_id
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"Error fetching AR statement: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### 3. Frontend Template

**File**: `app/templates/billing/ar_statement_modal.html`

**Modal Structure**:
```html
<!-- Modal Overlay -->
<div id="arStatementModal" class="modal hidden">
    <div class="modal-content">
        <!-- Header -->
        <div class="modal-header">
            <h2>Patient AR Statement</h2>
            <button class="close-btn" onclick="closeARStatementModal()">×</button>
        </div>

        <!-- Patient Info -->
        <div class="patient-info-section">
            <div>Patient: <strong id="ar-patient-name"></strong></div>
            <div>As of: <strong id="ar-as-of-date"></strong></div>
            <div>Current Balance: <strong id="ar-current-balance" class="balance-amount"></strong></div>
        </div>

        <!-- Transactions Table -->
        <div class="transactions-section">
            <table id="ar-transactions-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Reference</th>
                        <th class="text-right">Debit</th>
                        <th class="text-right">Credit</th>
                        <th class="text-right">Balance</th>
                    </tr>
                </thead>
                <tbody id="ar-transactions-body">
                    <!-- Populated by JavaScript -->
                </tbody>
                <tfoot>
                    <tr class="totals-row">
                        <td colspan="3"><strong>TOTALS</strong></td>
                        <td class="text-right" id="ar-total-debit"></td>
                        <td class="text-right" id="ar-total-credit"></td>
                        <td class="text-right" id="ar-total-balance"></td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <!-- Summary Section -->
        <div class="summary-section">
            <div class="summary-row">
                <span>Total Invoiced:</span>
                <span id="ar-summary-invoiced"></span>
            </div>
            <div class="summary-row">
                <span>Total Paid:</span>
                <span id="ar-summary-paid"></span>
            </div>
            <div class="summary-row">
                <span>Total Credit Notes:</span>
                <span id="ar-summary-credit-notes"></span>
            </div>
            <div class="summary-row total">
                <span><strong>Net Balance:</strong></span>
                <span id="ar-summary-balance"></span>
            </div>
        </div>

        <!-- Actions -->
        <div class="modal-actions">
            <button class="btn-secondary" onclick="closeARStatementModal()">Close</button>
            <button class="btn-primary" onclick="printARStatement()">Print Statement</button>
        </div>
    </div>
</div>
```

### 4. JavaScript

**File**: `app/static/js/ar_statement.js`

**Functions**:
```javascript
/**
 * Open AR statement modal for a patient
 * @param {string} patientId - Patient UUID
 * @param {string} highlightId - Optional transaction ID to highlight
 */
function openARStatementModal(patientId, highlightId = null) {
    const url = `/api/billing/ar-statement/${patientId}${highlightId ? `?highlight_id=${highlightId}` : ''}`;

    fetch(url)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                populateARStatementModal(result.data);
                document.getElementById('arStatementModal').classList.remove('hidden');
            } else {
                showError('Failed to load AR statement: ' + result.error);
            }
        })
        .catch(error => {
            console.error('Error loading AR statement:', error);
            showError('Failed to load AR statement');
        });
}

/**
 * Populate modal with AR statement data
 */
function populateARStatementModal(data) {
    // Patient info
    document.getElementById('ar-patient-name').textContent =
        `${data.patient_info.full_name} (${data.patient_info.patient_number})`;
    document.getElementById('ar-as-of-date').textContent =
        formatDate(data.as_of_date);

    // Current balance (with color coding)
    const balanceElement = document.getElementById('ar-current-balance');
    const balance = parseFloat(data.summary.current_balance);
    balanceElement.textContent = formatCurrency(balance);
    balanceElement.className = balance < 0 ? 'text-success' : 'text-danger';

    // Transactions table
    const tbody = document.getElementById('ar-transactions-body');
    tbody.innerHTML = '';

    data.transactions.forEach(txn => {
        const row = document.createElement('tr');
        if (txn.is_highlighted) {
            row.classList.add('highlighted-row');
        }

        row.innerHTML = `
            <td>${formatDate(txn.transaction_date)}</td>
            <td>${formatEntryType(txn.entry_type)}</td>
            <td>${txn.reference_number}</td>
            <td class="text-right">${formatCurrency(txn.debit_amount)}</td>
            <td class="text-right">${formatCurrency(txn.credit_amount)}</td>
            <td class="text-right ${txn.current_balance < 0 ? 'text-success' : 'text-danger'}">
                ${formatCurrency(txn.current_balance)}
            </td>
        `;

        tbody.appendChild(row);
    });

    // Totals
    document.getElementById('ar-total-debit').textContent =
        formatCurrency(data.summary.total_invoiced);
    document.getElementById('ar-total-credit').textContent =
        formatCurrency(parseFloat(data.summary.total_paid) + parseFloat(data.summary.total_credit_notes));
    document.getElementById('ar-total-balance').textContent =
        formatCurrency(data.summary.current_balance);

    // Summary
    document.getElementById('ar-summary-invoiced').textContent =
        formatCurrency(data.summary.total_invoiced);
    document.getElementById('ar-summary-paid').textContent =
        formatCurrency(data.summary.total_paid);
    document.getElementById('ar-summary-credit-notes').textContent =
        formatCurrency(data.summary.total_credit_notes);
    document.getElementById('ar-summary-balance').textContent =
        formatCurrency(data.summary.current_balance);
}

/**
 * Close AR statement modal
 */
function closeARStatementModal() {
    document.getElementById('arStatementModal').classList.add('hidden');
}

/**
 * Print AR statement
 */
function printARStatement() {
    window.print(); // Or create print-specific view
}

/**
 * Format entry type for display
 */
function formatEntryType(entryType) {
    const types = {
        'invoice': 'Invoice',
        'payment': 'Payment',
        'credit_note': 'Credit Note',
        'debit_note': 'Debit Note'
    };
    return types[entryType] || entryType;
}
```

### 5. CSS Styling

**File**: `app/static/css/ar_statement.css`

```css
/* AR Statement Modal */
#arStatementModal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

#arStatementModal.hidden {
    display: none;
}

.modal-content {
    background: white;
    border-radius: 8px;
    padding: 24px;
    max-width: 900px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
}

.patient-info-section {
    background: #f8f9fa;
    padding: 16px;
    border-radius: 4px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
}

#ar-transactions-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

#ar-transactions-table th,
#ar-transactions-table td {
    padding: 12px;
    border: 1px solid #ddd;
    text-align: left;
}

#ar-transactions-table thead {
    background: #f8f9fa;
}

.highlighted-row {
    background: #fff3cd;
    font-weight: 600;
}

.totals-row {
    background: #e9ecef;
    font-weight: bold;
}

.summary-section {
    background: #f8f9fa;
    padding: 16px;
    border-radius: 4px;
    margin-bottom: 20px;
}

.summary-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
}

.summary-row.total {
    border-top: 2px solid #333;
    margin-top: 8px;
    padding-top: 12px;
    font-size: 1.1em;
}

.text-success {
    color: #28a745;
}

.text-danger {
    color: #dc3545;
}

.text-right {
    text-align: right;
}
```

### 6. Action Button Configuration

**Add to Entity Configurations**

#### 6a. Patient Detail Configuration
**File**: `app/config/modules/patient_config.py` (or wherever patient config is)

```python
# In detail_actions list
ActionDefinition(
    name='view_ar_statement',
    label='View AR Statement',
    icon='receipt',
    action_type='custom',
    url_pattern='javascript:openARStatementModal("{patient_id}")',
    style='secondary',
    position='right'
)
```

#### 6b. Invoice Detail Configuration
**File**: `app/config/modules/patient_invoice_config.py`

```python
# In detail_actions list
ActionDefinition(
    name='view_patient_ar',
    label='View Patient AR Statement',
    icon='account_balance',
    action_type='custom',
    url_pattern='javascript:openARStatementModal("{patient_id}", "{invoice_id}")',
    style='secondary',
    position='right'
)
```

#### 6c. Payment Detail Configuration
**File**: Create or update payment configuration

```python
# In detail_actions list
ActionDefinition(
    name='view_patient_ar',
    label='View Patient AR Statement',
    icon='account_balance',
    action_type='custom',
    url_pattern='javascript:openARStatementModal("{patient_id}", "{payment_id}")',
    style='secondary',
    position='right'
)
```

#### 6d. Package Payment Plan Detail Configuration
**File**: `app/config/modules/package_payment_plan_config.py`

```python
# In detail_actions list
ActionDefinition(
    name='view_patient_ar',
    label='View Patient AR Statement',
    icon='account_balance',
    action_type='custom',
    url_pattern='javascript:openARStatementModal("{patient_id}", "{plan_id}")',
    style='secondary',
    position='right'
)
```

### 7. Template Integration

**Include modal and JS in base template or relevant pages**

**File**: `app/templates/layouts/base.html`

Add before closing `</body>`:
```html
<!-- AR Statement Modal -->
{% include 'billing/ar_statement_modal.html' %}

<!-- AR Statement JavaScript -->
<script src="{{ url_for('static', filename='js/ar_statement.js') }}"></script>
<link rel="stylesheet" href="{{ url_for('static', filename='css/ar_statement.css') }}">
```

## Implementation Order

1. ✅ Create `ARStatementService` (backend logic)
2. ✅ Create API route `/api/billing/ar-statement/<patient_id>`
3. ✅ Create modal template `ar_statement_modal.html`
4. ✅ Create JavaScript `ar_statement.js`
5. ✅ Create CSS `ar_statement.css`
6. ✅ Add modal to base template
7. ✅ Add action button to Patient detail config
8. ✅ Add action button to Invoice detail config
9. ✅ Add action button to Payment detail config
10. ✅ Add action button to Package Plan detail config
11. ✅ Test from all 4 locations

## Testing Scenarios

### Test 1: From Patient Detail
1. Navigate to patient detail page
2. Click "View AR Statement" button
3. Modal opens showing all patient transactions
4. Verify totals match
5. Close modal

### Test 2: From Invoice Detail
1. Navigate to invoice detail page
2. Click "View Patient AR Statement" button
3. Modal opens with invoice row highlighted
4. Verify invoice appears in list
5. Close modal

### Test 3: From Payment Detail
1. Navigate to payment detail page
2. Click "View Patient AR Statement" button
3. Modal opens with payment row highlighted
4. Verify payment appears in list
5. Close modal

### Test 4: From Package Plan Detail
1. Navigate to package payment plan detail page
2. Click "View Patient AR Statement" button
3. Modal opens with related invoice/credit note highlighted
4. Verify plan transactions appear
5. Close modal

### Test 5: Patient with Credit Balance
1. Open AR statement for patient with credit (like our example -₹4,982)
2. Verify balance shows as negative (green)
3. Verify summary calculations are correct
4. Verify credit notes included

### Test 6: Patient with Debit Balance
1. Open AR statement for patient with outstanding balance
2. Verify balance shows as positive (red)
3. Verify unpaid invoices listed

## Benefits

1. **Complete Visibility**: See patient's entire account history at a glance
2. **Context Awareness**: Understand any transaction in context of full account
3. **Quick Access**: Available from multiple pages (patient, invoice, payment, plan)
4. **Audit Trail**: Complete chronological transaction history
5. **Balance Clarity**: Immediate understanding of credit/debit position
6. **Decision Support**: Helps determine refund amounts, outstanding balances
7. **Patient Communication**: Clear statement to share with patients

## Future Enhancements

1. **Print/Export**: Generate PDF statement for patient
2. **Date Range Filter**: View statement for specific period
3. **Transaction Drill-down**: Click transaction to open detail view
4. **Email Statement**: Send statement to patient email
5. **Outstanding Only**: Filter to show only unpaid invoices
6. **Payment Plan**: Show installment schedule alongside transactions
7. **Reconciliation**: Match payments to specific invoices

## Success Criteria

✅ Modal opens from all 4 locations (patient, invoice, payment, plan)
✅ All transactions displayed in chronological order
✅ Running balance calculated correctly
✅ Totals match AR subledger
✅ Current transaction highlighted when opened from detail pages
✅ Color coding for credit (green) and debit (red) balances
✅ Modal is responsive and accessible
✅ No performance issues with large transaction histories

---

**Ready to implement?** This feature will significantly improve visibility into patient accounts and make the discontinuation workflow (and all AR operations) much clearer.
