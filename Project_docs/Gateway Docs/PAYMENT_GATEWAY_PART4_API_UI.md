# Payment Gateway Integration - Part 4: API & UI Design

**Part:** 4 of 5
**Focus:** API Endpoints, UI Components, Frontend Integration
**Audience:** Full-stack developers, frontend team

---

## Table of Contents

1. [API Design](#1-api-design)
2. [UI Components](#2-ui-components)
3. [JavaScript Integration](#3-javascript-integration)
4. [Templates](#4-templates)

---

## 1. API Design

### 1.1 Gateway Management Endpoints

**File:** `app/api/routes/payment_gateway.py`

#### POST /api/gateway/initiate-payout

Initiate direct payout via gateway.

**Request:**
```json
{
    "payment_id": "uuid-string",
    "gateway_provider": "razorpay",  // optional
    "payment_method": "upi",  // or "bank_transfer"
    "account_details": {
        // For UPI:
        "upi_id": "supplier@okaxis",

        // For Bank Transfer:
        "account_holder_name": "Supplier Name",
        "account_number": "123456789",
        "ifsc_code": "SBIN0001234",
        "bank_name": "State Bank of India"
    }
}
```

**Response:**
```json
{
    "success": true,
    "gateway_payment_id": "pout_KmKvgS3ZqY2345",
    "status": "pending",
    "message": "Payout initiated successfully",
    "gateway_fee": 5.00,
    "gateway_tax": 0.90,
    "estimated_settlement": "2 business days"
}
```

#### POST /api/gateway/create-payment-link

Generate payment link for supplier.

**Request:**
```json
{
    "payment_id": "uuid-string",
    "gateway_provider": "razorpay",
    "supplier_email": "supplier@example.com",
    "supplier_phone": "+919876543210",
    "send_notification": true,
    "expires_in_hours": 48
}
```

**Response:**
```json
{
    "success": true,
    "payment_link_id": "plink_KmKvgS3ZqY2345",
    "payment_link_url": "https://rzp.io/i/abc123",
    "expires_at": "2025-11-05T12:00:00Z",
    "qr_code_url": "https://api.razorpay.com/qr/plink_KmKvgS3ZqY2345.png"
}
```

#### GET /api/gateway/check-status/<payment_id>

Check current gateway payment status.

**Response:**
```json
{
    "success": true,
    "payment_id": "uuid-string",
    "gateway_payment_id": "pout_KmKvgS3ZqY2345",
    "status": "completed",
    "transaction_id": "UTR123456789",
    "updated_at": "2025-11-03T10:30:00Z",
    "gateway_fee": 5.00,
    "gateway_tax": 0.90
}
```

#### POST /api/gateway/create-refund

Initiate refund for gateway payment.

**Request:**
```json
{
    "payment_id": "uuid-string",
    "refund_amount": 5000.00,
    "reason": "Overpayment"
}
```

**Response:**
```json
{
    "success": true,
    "refund_id": "rfnd_KmKvgS3ZqY2345",
    "refund_payment_id": "uuid-new-payment",
    "status": "pending",
    "message": "Refund initiated successfully"
}
```

#### POST /api/gateway/webhook/<provider>

Receive webhook from gateway (no auth required - signature verified).

**Headers:**
- Razorpay: `X-Razorpay-Signature`
- Paytm: `X-Paytm-Signature`

**Response:**
```json
{
    "success": true,
    "message": "Webhook processed"
}
```

---

## 2. UI Components

### 2.1 Payment Form Enhancement

**File:** `app/templates/supplier/payment_form.html`

Add gateway payment mode selection:

```html
<!-- Payment Mode Selection -->
<div class="form-group">
    <label class="form-label">Payment Mode</label>
    <div class="payment-mode-selector">
        <div class="mode-option">
            <input type="radio" id="mode_manual" name="payment_mode" value="manual" checked>
            <label for="mode_manual">
                <i class="icon-edit"></i>
                <span class="mode-title">Manual Entry</span>
                <span class="mode-desc">Enter payment details manually</span>
            </label>
        </div>

        <div class="mode-option">
            <input type="radio" id="mode_gateway" name="payment_mode" value="gateway_payout">
            <label for="mode_gateway">
                <i class="icon-zap"></i>
                <span class="mode-title">Gateway Payout</span>
                <span class="mode-desc">Direct bank transfer via payment gateway</span>
            </label>
        </div>

        <div class="mode-option">
            <input type="radio" id="mode_link" name="payment_mode" value="payment_link">
            <label for="mode_link">
                <i class="icon-link"></i>
                <span class="mode-title">Payment Link</span>
                <span class="mode-desc">Send payment link to supplier</span>
            </label>
        </div>
    </div>
</div>

<!-- Gateway Payout Section (Conditional) -->
<div id="gateway-payout-section" class="payment-section hidden">
    <h3>Gateway Payout Details</h3>

    <div class="form-row">
        <div class="form-group col-md-6">
            <label>Gateway Provider</label>
            <select name="gateway_provider" class="form-control">
                <option value="">Use Default</option>
                <option value="razorpay">Razorpay</option>
                <option value="paytm">Paytm</option>
            </select>
        </div>

        <div class="form-group col-md-6">
            <label>Transfer Method</label>
            <select name="transfer_method" class="form-control" required>
                <option value="upi">UPI</option>
                <option value="neft">NEFT</option>
                <option value="imps">IMPS</option>
                <option value="rtgs">RTGS</option>
            </select>
        </div>
    </div>

    <div class="form-group">
        <label>Supplier Account</label>
        <select name="supplier_account_id" class="form-control" id="supplier-account-select">
            <option value="">Select Account</option>
            <!-- Populated via AJAX -->
        </select>
        <button type="button" class="btn btn-link" onclick="showAddAccountModal()">
            + Add New Account
        </button>
    </div>

    <!-- Gateway Fee Preview -->
    <div class="alert alert-info gateway-fee-preview">
        <strong>Gateway Charges:</strong> <span id="fee-amount">₹0.00</span> + GST <span id="tax-amount">₹0.00</span>
        <br><strong>Net to Supplier:</strong> <span id="net-amount">₹0.00</span>
        <br><strong>Settlement Time:</strong> <span id="settlement-time">1-2 business days</span>
    </div>
</div>

<!-- Payment Link Section (Conditional) -->
<div id="payment-link-section" class="payment-section hidden">
    <h3>Payment Link Details</h3>

    <div class="form-row">
        <div class="form-group col-md-6">
            <label>Supplier Email</label>
            <input type="email" name="supplier_email" class="form-control" value="{{ supplier.email }}">
        </div>

        <div class="form-group col-md-6">
            <label>Supplier Phone</label>
            <input type="tel" name="supplier_phone" class="form-control" value="{{ supplier.phone }}">
        </div>
    </div>

    <div class="form-row">
        <div class="form-group col-md-6">
            <label>Link Expiry</label>
            <select name="link_expiry_hours" class="form-control">
                <option value="24">24 Hours</option>
                <option value="48" selected>48 Hours</option>
                <option value="72">72 Hours</option>
            </select>
        </div>

        <div class="form-group col-md-6">
            <label>Gateway Provider</label>
            <select name="gateway_provider_link" class="form-control">
                <option value="">Use Default</option>
                <option value="razorpay">Razorpay</option>
                <option value="paytm">Paytm</option>
            </select>
        </div>
    </div>

    <div class="form-check">
        <input type="checkbox" name="send_notification" class="form-check-input" id="send-notification" checked>
        <label class="form-check-label" for="send-notification">
            Send link via Email & SMS
        </label>
    </div>
</div>
```

### 2.2 Payment View Enhancement

**File:** `app/templates/supplier/payment_view.html`

Display gateway payment status:

```html
{% if payment.payment_category == 'gateway' %}
<div class="card mt-4">
    <div class="card-header bg-primary text-white">
        <h4 class="mb-0">
            <i class="icon-zap"></i> Gateway Payment Details
        </h4>
    </div>
    <div class="card-body">
        <!-- Status Badge -->
        <div class="mb-3">
            <span class="badge badge-lg badge-{{ payment.effective_status | status_class }}">
                {{ payment.effective_status | upper }}
            </span>
        </div>

        <!-- Gateway Information Table -->
        <table class="table table-borderless details-table">
            <tr>
                <td class="detail-label">Gateway Provider:</td>
                <td class="detail-value">
                    <strong>{{ payment.gateway_provider_display }}</strong>
                </td>
            </tr>
            <tr>
                <td class="detail-label">Gateway Payment ID:</td>
                <td class="detail-value">
                    <code class="copy-text">{{ payment.gateway_payment_id }}</code>
                    <button class="btn-icon" onclick="copyToClipboard('{{ payment.gateway_payment_id }}')">
                        <i class="icon-copy"></i>
                    </button>
                </td>
            </tr>
            {% if payment.gateway_transaction_id %}
            <tr>
                <td class="detail-label">UTR Number:</td>
                <td class="detail-value">
                    <code class="copy-text">{{ payment.gateway_transaction_id }}</code>
                    <button class="btn-icon" onclick="copyToClipboard('{{ payment.gateway_transaction_id }}')">
                        <i class="icon-copy"></i>
                    </button>
                </td>
            </tr>
            {% endif %}
            <tr>
                <td class="detail-label">Gateway Charges:</td>
                <td class="detail-value">
                    ₹{{ payment.gateway_fee | format_currency }} + GST ₹{{ payment.gateway_tax | format_currency }}
                    <br><small class="text-muted">Total: ₹{{ payment.total_gateway_charges | format_currency }}</small>
                </td>
            </tr>
            <tr>
                <td class="detail-label">Net Amount to Supplier:</td>
                <td class="detail-value">
                    <strong>₹{{ payment.net_amount_to_supplier | format_currency }}</strong>
                </td>
            </tr>
            <tr>
                <td class="detail-label">Status Timeline:</td>
                <td class="detail-value">
                    <ul class="timeline">
                        <li class="completed">
                            <i class="icon-check-circle"></i>
                            Initiated: {{ payment.gateway_initiated_at | format_datetime }}
                        </li>
                        {% if payment.gateway_completed_at %}
                        <li class="completed">
                            <i class="icon-check-circle text-success"></i>
                            Completed: {{ payment.gateway_completed_at | format_datetime }}
                        </li>
                        {% elif payment.gateway_failed_at %}
                        <li class="failed">
                            <i class="icon-x-circle text-danger"></i>
                            Failed: {{ payment.gateway_failed_at | format_datetime }}
                            <br><small>{{ payment.gateway_response_message }}</small>
                        </li>
                        {% else %}
                        <li class="pending">
                            <i class="icon-clock text-warning"></i>
                            Processing...
                        </li>
                        {% endif %}
                    </ul>
                </td>
            </tr>
        </table>

        <!-- Action Buttons -->
        <div class="gateway-actions mt-3">
            {% if payment.gateway_initiated_at and not payment.gateway_completed_at and not payment.gateway_failed_at %}
            <button class="btn btn-secondary" onclick="refreshGatewayStatus('{{ payment.payment_id }}')">
                <i class="icon-refresh-cw"></i> Refresh Status
            </button>
            {% endif %}

            {% if payment.gateway_completed_at and user_has_permission('supplier_payments', 'approve') %}
            <button class="btn btn-warning" onclick="showRefundModal('{{ payment.payment_id }}')">
                <i class="icon-rotate-ccw"></i> Initiate Refund
            </button>
            {% endif %}

            {% if payment.gateway_failed_at %}
            <button class="btn btn-primary" onclick="retryGatewayPayment('{{ payment.payment_id }}')">
                <i class="icon-repeat"></i> Retry Payment
            </button>
            {% endif %}
        </div>
    </div>
</div>
{% elif payment.payment_link_id %}
<div class="card mt-4">
    <div class="card-header bg-info text-white">
        <h4 class="mb-0">
            <i class="icon-link"></i> Payment Link Details
        </h4>
    </div>
    <div class="card-body">
        <table class="table table-borderless">
            <tr>
                <td>Link ID:</td>
                <td><code>{{ payment.payment_link_id }}</code></td>
            </tr>
            <tr>
                <td>Link URL:</td>
                <td>
                    <a href="{{ payment.payment_link_url }}" target="_blank" class="link-url">
                        {{ payment.payment_link_url }}
                    </a>
                    <button class="btn-icon" onclick="copyToClipboard('{{ payment.payment_link_url }}')">
                        <i class="icon-copy"></i>
                    </button>
                </td>
            </tr>
            <tr>
                <td>Expires At:</td>
                <td>
                    {{ payment.payment_link_expires_at | format_datetime }}
                    {% if payment.payment_link_expired %}
                    <span class="badge badge-danger ml-2">EXPIRED</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Status:</td>
                <td>
                    <span class="badge badge-{{ payment.payment_link_status }}">
                        {{ payment.payment_link_status | upper }}
                    </span>
                </td>
            </tr>
        </table>

        <div class="payment-link-actions mt-3">
            <button class="btn btn-primary" onclick="resendPaymentLink('{{ payment.payment_id }}')">
                <i class="icon-mail"></i> Resend Link
            </button>

            {% if payment.payment_link_status == 'created' and not payment.payment_link_expired %}
            <button class="btn btn-secondary" onclick="extendLinkExpiry('{{ payment.payment_id }}')">
                <i class="icon-clock"></i> Extend Expiry
            </button>
            {% endif %}

            {% if payment.payment_link_expired or payment.payment_link_status == 'expired' %}
            <button class="btn btn-primary" onclick="regeneratePaymentLink('{{ payment.payment_id }}')">
                <i class="icon-refresh-cw"></i> Regenerate Link
            </button>
            {% endif %}
        </div>
    </div>
</div>
{% endif %}
```

---

## 3. JavaScript Integration

**File:** `app/static/js/gateway_payments.js`

```javascript
// Payment mode switching
document.querySelectorAll('input[name="payment_mode"]').forEach(radio => {
    radio.addEventListener('change', function() {
        // Hide all sections
        document.getElementById('manual-payment-section').classList.toggle('hidden', this.value !== 'manual');
        document.getElementById('gateway-payout-section').classList.toggle('hidden', this.value !== 'gateway_payout');
        document.getElementById('payment-link-section').classList.toggle('hidden', this.value !== 'payment_link');

        // Load supplier accounts if gateway payout selected
        if (this.value === 'gateway_payout') {
            loadSupplierAccounts();
            calculateGatewayFees();
        }
    });
});

// Load supplier bank accounts/UPI IDs
function loadSupplierAccounts() {
    const supplierId = document.getElementById('supplier_id').value;
    if (!supplierId) return;

    fetch(`/api/supplier/${supplierId}/bank-accounts`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('supplier-account-select');
            select.innerHTML = '<option value="">Select Account</option>';

            data.accounts.forEach(account => {
                const option = document.createElement('option');
                option.value = account.account_id;
                option.textContent = account.account_type === 'upi'
                    ? `UPI: ${account.upi_id}`
                    : `Bank: ${account.account_number} (${account.bank_name})`;
                option.dataset.accountType = account.account_type;
                option.dataset.accountDetails = JSON.stringify(account);
                select.appendChild(option);
            });
        });
}

// Calculate and display gateway fees
function calculateGatewayFees() {
    const amount = parseFloat(document.getElementById('amount').value) || 0;
    const method = document.querySelector('select[name="transfer_method"]').value;

    // Fee calculation (example - should come from gateway config)
    let fee = 0;
    let tax = 0;

    if (method === 'upi') {
        fee = 5;  // Fixed ₹5
        tax = fee * 0.18;  // 18% GST
    } else {
        fee = 10;  // Fixed ₹10 for NEFT/IMPS/RTGS
        tax = fee * 0.18;
    }

    const netAmount = amount - fee - tax;

    document.getElementById('fee-amount').textContent = `₹${fee.toFixed(2)}`;
    document.getElementById('tax-amount').textContent = `₹${tax.toFixed(2)}`;
    document.getElementById('net-amount').textContent = `₹${netAmount.toFixed(2)}`;

    // Settlement time
    const settlementTimes = {
        'upi': 'Instant to 2 hours',
        'imps': 'Instant to 2 hours',
        'neft': 'Same day or next business day',
        'rtgs': 'Real-time (30 mins)'
    };
    document.getElementById('settlement-time').textContent = settlementTimes[method] || '1-2 business days';
}

// Refresh gateway payment status
function refreshGatewayStatus(paymentId) {
    const button = event.target;
    button.disabled = true;
    button.innerHTML = '<i class="icon-refresh-cw spin"></i> Refreshing...';

    fetch(`/api/gateway/check-status/${paymentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload page to show updated status
                window.location.reload();
            } else {
                alert('Failed to refresh status: ' + data.error);
                button.disabled = false;
                button.innerHTML = '<i class="icon-refresh-cw"></i> Refresh Status';
            }
        })
        .catch(error => {
            alert('Error refreshing status');
            button.disabled = false;
            button.innerHTML = '<i class="icon-refresh-cw"></i> Refresh Status';
        });
}

// Show refund modal
function showRefundModal(paymentId) {
    // Implementation for refund modal
    document.getElementById('refund-payment-id').value = paymentId;
    $('#refundModal').modal('show');
}

// Initiate refund
function submitRefund() {
    const paymentId = document.getElementById('refund-payment-id').value;
    const refundAmount = document.getElementById('refund-amount').value;
    const refundReason = document.getElementById('refund-reason').value;

    fetch('/api/gateway/create-refund', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            payment_id: paymentId,
            refund_amount: parseFloat(refundAmount),
            reason: refundReason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Refund initiated successfully');
            window.location.reload();
        } else {
            alert('Refund failed: ' + data.error);
        }
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show tooltip or toast notification
        showToast('Copied to clipboard!');
    });
}

// Resend payment link
function resendPaymentLink(paymentId) {
    if (!confirm('Resend payment link via Email/SMS?')) return;

    fetch(`/api/gateway/resend-link/${paymentId}`, {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Payment link resent successfully');
            } else {
                alert('Failed to resend link: ' + data.error);
            }
        });
}
```

---

## Summary

API & UI provides:
✅ RESTful gateway endpoints
✅ Enhanced payment form with modes
✅ Gateway status display
✅ Payment link management
✅ JavaScript for dynamic interactions
✅ Real-time fee calculation

**Next:** Review Part 5 for implementation timeline and testing strategy.
