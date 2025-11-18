# Payment Gateway Integration - Addendum: Incoming Payments

**Document Type:** Addendum
**Focus:** Patient/Customer Payment Collections via Gateway
**Related To:** Payment Gateway Integration Parts 1-5
**Date:** 2025-11-03

---

## Overview

This addendum addresses the **incoming payment side** of the payment gateway integration - collecting payments FROM patients, customers, and other revenue sources.

**Important Note:** The main documentation (Parts 1-5) focused on **outgoing payments** (payouts to suppliers). This addendum covers the reverse flow - **incoming payments** (collections from patients).

---

## Table of Contents

1. [Incoming vs Outgoing Payments](#1-incoming-vs-outgoing-payments)
2. [Use Cases for Incoming Payments](#2-use-cases-for-incoming-payments)
3. [Gateway Capabilities](#3-gateway-capabilities)
4. [Architecture for Collections](#4-architecture-for-collections)
5. [Implementation Approach](#5-implementation-approach)
6. [Integration with Billing Module](#6-integration-with-billing-module)

---

## 1. Incoming vs Outgoing Payments

### Comparison Table

| Aspect | Outgoing (Supplier Payouts) | Incoming (Patient Collections) |
|--------|----------------------------|--------------------------------|
| **Direction** | Skinspire → Supplier | Patient → Skinspire |
| **Gateway API** | Payouts API | Payments API, Payment Links |
| **Initiation** | Staff initiates | Patient initiates |
| **Use Case** | Pay supplier invoices | Collect consultation fees, bills |
| **Settlement** | Money leaves account | Money enters account |
| **Razorpay API** | Razorpay Payouts (X) | Razorpay Payment Gateway |
| **Paytm API** | Money Transfer | Payment Gateway |
| **Typical Amount** | ₹5,000 - ₹50,000 | ₹500 - ₹10,000 |
| **Volume** | Lower (10-50/day) | Higher (100-500/day) |

### Key Differences

**Outgoing Payments (Covered in Main Docs):**
- **Workflow:** Staff creates payment → Gateway sends money → Supplier receives
- **Control:** Hospital has full control (when to pay, how much)
- **Risk:** Ensure funds reach correct supplier
- **GL Impact:** Decrease payables, decrease cash

**Incoming Payments (This Addendum):**
- **Workflow:** Patient initiates → Gateway processes → Hospital receives
- **Control:** Patient decides when to pay (within due date)
- **Risk:** Payment failures, refund requests
- **GL Impact:** Increase cash, decrease receivables

---

## 2. Use Cases for Incoming Payments

### 2.1 Healthcare Revenue Streams

**Primary Use Cases:**

1. **Consultation Fees**
   - Online appointment booking payments
   - Advance payment to confirm slot
   - Typically ₹500 - ₹2,000

2. **Treatment Advance**
   - Advance payment before treatment
   - Partial billing (pay upfront, balance later)
   - Typically ₹5,000 - ₹50,000

3. **Bill Payment**
   - Final bill payment after treatment
   - Discharge bill settlement
   - Typically ₹2,000 - ₹100,000

4. **OPD Pharmacy Sales**
   - Medicine purchases from hospital pharmacy
   - Typically ₹200 - ₹5,000

5. **Package Purchases**
   - Health checkup packages
   - Annual wellness packages
   - Typically ₹3,000 - ₹20,000

6. **Outstanding Bill Collection**
   - Collecting overdue patient bills
   - Payment links sent via email/SMS
   - Variable amounts

### 2.2 Payment Methods Supported

**Via Razorpay/Paytm:**
- ✅ Credit/Debit Cards (Visa, Mastercard, RuPay)
- ✅ UPI (GPay, PhonePe, Paytm, etc.)
- ✅ Net Banking (All major banks)
- ✅ Wallets (Paytm, PhonePe, Mobikwik)
- ✅ EMI (for higher amounts)
- ✅ Buy Now Pay Later (LazyPay, Simpl)

**Cash/Manual (Existing):**
- ✅ Cash at reception
- ✅ Cheque
- ✅ Bank transfer
- ✅ Card swipe (POS machine)

---

## 3. Gateway Capabilities

### 3.1 Razorpay Payment Gateway

**Features for Incoming Payments:**

1. **Payment Gateway Integration**
   - Checkout form for website/app
   - Supports all payment methods
   - PCI DSS compliant
   - Mobile responsive

2. **Payment Links**
   - Generate payment link with amount
   - Send via email/SMS
   - Expires after set duration
   - No coding required

3. **Payment Pages**
   - Hosted payment page
   - Customizable with logo
   - Shareable URL

4. **QR Codes**
   - Dynamic QR codes with amount
   - UPI QR codes
   - Print on invoices

5. **Recurring Payments**
   - Subscription billing
   - Auto-debit for packages
   - Standing instructions

6. **Webhooks**
   - payment.captured
   - payment.failed
   - refund.created

**Fees:** ~2% of transaction amount + ₹0 (varies by payment method)

### 3.2 Paytm Payment Gateway

**Similar features:**
- Payment gateway API
- Payment links
- QR codes
- Subscriptions
- Webhooks

**Fees:** ~2-3% of transaction amount

---

## 4. Architecture for Collections

### 4.1 Incoming Payment Flow

```
Patient                Skinspire           Payment          Gateway
                       System              Gateway
  │                      │                   │                 │
  │ View Bill           │                   │                 │
  ├────────────────────►│                   │                 │
  │                      │                   │                 │
  │ Click "Pay Online"  │                   │                 │
  ├────────────────────►│                   │                 │
  │                      │                   │                 │
  │                      │ Create Order      │                 │
  │                      ├──────────────────►│                 │
  │                      │                   │ Create Order    │
  │                      │                   ├────────────────►│
  │                      │                   │                 │
  │                      │                   │ Order ID        │
  │                      │                   │◄────────────────┤
  │                      │ Order ID          │                 │
  │                      │◄──────────────────┤                 │
  │                      │                   │                 │
  │ Redirect to Gateway  │                   │                 │
  │◄─────────────────────┤                   │                 │
  │                      │                   │                 │
  │────────────────────────────────────────────────────────────►│
  │ Payment Page (Gateway hosted)                              │
  │                      │                   │                 │
  │ Enter Card/UPI       │                   │                 │
  │ Submit Payment       │                   │                 │
  │─────────────────────────────────────────────────────────────►
  │                      │                   │                 │
  │                      │                   │ Process Payment │
  │                      │                   │                 │
  │ Success/Failure      │                   │                 │
  │◄─────────────────────────────────────────────────────────────
  │                      │                   │                 │
  │ Redirect to Success  │                   │                 │
  │◄─────────────────────┤                   │                 │
  │                      │                   │                 │
  │                      │   Webhook Event (payment.captured)  │
  │                      │◄──────────────────┼─────────────────┤
  │                      │                   │                 │
  │                      │ Update Bill Status│                 │
  │                      │ Post GL Entries   │                 │
  │                      │ Send Receipt      │                 │
  │                      │                   │                 │
```

### 4.2 Database Schema for Incoming Payments

**New Table: `patient_payment`**

```sql
CREATE TABLE patient_payment (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id VARCHAR(36) NOT NULL,
    branch_id VARCHAR(36),

    -- Patient & Bill
    patient_id VARCHAR(36) NOT NULL,
    bill_id VARCHAR(36),  -- Billing module invoice ID
    appointment_id VARCHAR(36),  -- If appointment payment

    -- Payment details
    amount NUMERIC(12,2) NOT NULL,
    payment_method VARCHAR(30),  -- 'card', 'upi', 'netbanking', 'wallet', 'cash', 'cheque'
    payment_category VARCHAR(20) DEFAULT 'manual',  -- 'manual', 'gateway'
    payment_source VARCHAR(30) DEFAULT 'internal',  -- 'internal', 'razorpay', 'paytm'

    -- Gateway tracking (similar to supplier_payment)
    gateway_payment_id VARCHAR(100),  -- pay_xxx (Razorpay)
    gateway_order_id VARCHAR(100),    -- order_xxx
    gateway_transaction_id VARCHAR(100),  -- Bank transaction ID
    gateway_response_code VARCHAR(10),
    gateway_response_message VARCHAR(255),
    gateway_fee NUMERIC(12,2) DEFAULT 0,  -- Gateway charges (deducted from settlement)
    gateway_tax NUMERIC(12,2) DEFAULT 0,
    gateway_initiated_at TIMESTAMP WITH TIME ZONE,
    gateway_captured_at TIMESTAMP WITH TIME ZONE,  -- When payment captured
    gateway_failed_at TIMESTAMP WITH TIME ZONE,
    gateway_metadata JSONB,

    -- Payment link (for outstanding bill collection)
    payment_link_id VARCHAR(100),
    payment_link_url VARCHAR(500),
    payment_link_expires_at TIMESTAMP WITH TIME ZONE,
    payment_link_status VARCHAR(20),

    -- Status
    payment_status VARCHAR(20) DEFAULT 'pending',
    -- Values: 'pending', 'captured', 'failed', 'refunded', 'partial_refund'

    -- GL & Reconciliation
    gl_posted BOOLEAN DEFAULT false,
    gl_entry_id VARCHAR(36),
    posting_date TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,
    updated_by VARCHAR(15),

    CONSTRAINT fk_patient_payment_patient FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    CONSTRAINT fk_patient_payment_bill FOREIGN KEY (bill_id) REFERENCES billing_invoice(invoice_id)
);
```

---

## 5. Implementation Approach

### 5.1 Gateway Adapter Extension

**Extend existing `PaymentGatewayInterface`:**

```python
# app/services/payment_gateway/base.py

class PaymentGatewayInterface(ABC):
    # ... existing methods for outgoing payments ...

    # NEW: Methods for incoming payments
    @abstractmethod
    def create_order(self, order_data: Dict) -> 'GatewayOrderResponse':
        """
        Create payment order for customer to pay.

        Args:
            order_data: {
                'amount': Decimal,
                'currency': 'INR',
                'receipt': str,  # Internal invoice/bill number
                'notes': Dict,
                'customer': {
                    'name': str,
                    'email': str,
                    'phone': str
                }
            }

        Returns:
            GatewayOrderResponse with order_id
        """
        pass

    @abstractmethod
    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str
    ) -> bool:
        """
        Verify payment signature after customer completes payment.
        Prevents payment tampering.
        """
        pass

    @abstractmethod
    def capture_payment(self, payment_id: str, amount: Decimal) -> 'GatewayPaymentResponse':
        """
        Capture authorized payment (for two-step payments).
        """
        pass

    @abstractmethod
    def create_refund(self, payment_id: str, amount: Decimal, reason: str) -> 'GatewayRefundResponse':
        """
        Refund customer payment.
        """
        pass
```

### 5.2 Razorpay Incoming Payment Implementation

```python
# app/services/payment_gateway/adapters/razorpay_adapter.py

class RazorpayAdapter(PaymentGatewayInterface):
    # ... existing outgoing payment methods ...

    def create_order(self, order_data: Dict) -> GatewayOrderResponse:
        """Create Razorpay order for patient payment"""
        try:
            amount_paise = int(order_data['amount'] * 100)

            order_params = {
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': order_data.get('receipt', str(uuid.uuid4())),
                'notes': order_data.get('notes', {}),
                'partial_payment': False
            }

            order = self.client.order.create(order_params)

            return GatewayOrderResponse(
                success=True,
                order_id=order['id'],  # order_xxx
                amount=Decimal(order['amount']) / 100,
                currency=order['currency'],
                status=order['status'],  # 'created'
                raw_response=order
            )

        except razorpay.errors.BadRequestError as e:
            raise GatewayAPIError(str(e))

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature"""
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            self.client.utility.verify_payment_signature(params_dict)
            return True

        except razorpay.errors.SignatureVerificationError:
            return False

    def capture_payment(self, payment_id: str, amount: Decimal) -> GatewayPaymentResponse:
        """Capture authorized payment"""
        try:
            amount_paise = int(amount * 100)
            payment = self.client.payment.capture(payment_id, amount_paise)

            return GatewayPaymentResponse(
                success=True,
                payment_id=payment['id'],
                status=payment['status'],  # 'captured'
                amount=Decimal(payment['amount']) / 100,
                method=payment['method'],  # 'card', 'upi', 'netbanking'
                raw_response=payment
            )

        except razorpay.errors.BadRequestError as e:
            raise GatewayAPIError(str(e))
```

### 5.3 Patient Payment Service

**New Service:** `app/services/patient_payment_service.py`

```python
from app.services.payment_gateway.gateway_manager import PaymentGatewayManager

class PatientPaymentService:
    """Service for handling patient payment collections"""

    def create_gateway_order(
        self,
        patient_id: str,
        bill_id: str,
        amount: Decimal,
        hospital_id: str,
        branch_id: str,
        gateway_provider: str = None
    ) -> Dict:
        """
        Create gateway order for patient to pay bill.

        Returns:
            {
                'success': True,
                'order_id': 'order_xxx',
                'gateway_payment_id': 'pay_xxx',
                'checkout_url': 'https://...',
                'key_id': 'rzp_xxx'  # For frontend checkout
            }
        """
        # Get bill details
        bill = self._get_bill(bill_id)
        patient = self._get_patient(patient_id)

        # Create payment record
        payment = self._create_payment_record(
            patient_id, bill_id, amount, hospital_id, branch_id
        )

        # Initialize gateway manager
        gateway_manager = PaymentGatewayManager(hospital_id, branch_id)
        adapter = gateway_manager.get_gateway_adapter(gateway_provider)

        # Create order
        order_data = {
            'amount': amount,
            'receipt': bill.bill_number,
            'notes': {
                'patient_id': patient_id,
                'bill_id': bill_id,
                'payment_id': str(payment.payment_id)
            },
            'customer': {
                'name': patient.patient_name,
                'email': patient.email,
                'phone': patient.phone
            }
        }

        order_result = adapter.create_order(order_data)

        # Update payment record with order details
        payment.gateway_order_id = order_result.order_id
        payment.gateway_initiated_at = datetime.now(timezone.utc)
        payment.payment_category = 'gateway'
        payment.payment_source = gateway_provider or 'razorpay'
        db.session.commit()

        return {
            'success': True,
            'order_id': order_result.order_id,
            'payment_id': str(payment.payment_id),
            'amount': float(amount),
            'key_id': adapter.api_key  # For Razorpay checkout.js
        }

    def verify_and_capture_payment(
        self,
        payment_id: str,
        gateway_order_id: str,
        gateway_payment_id: str,
        signature: str
    ) -> Dict:
        """
        Verify payment signature and capture payment.
        Called from frontend callback after successful payment.
        """
        payment = self._get_payment(payment_id)

        # Get gateway adapter
        gateway_manager = PaymentGatewayManager(payment.hospital_id, payment.branch_id)
        adapter = gateway_manager.get_gateway_adapter(payment.payment_source)

        # Verify signature
        if not adapter.verify_payment_signature(gateway_order_id, gateway_payment_id, signature):
            raise GatewayException("Invalid payment signature")

        # Capture payment
        capture_result = adapter.capture_payment(gateway_payment_id, payment.amount)

        # Update payment record
        payment.gateway_payment_id = gateway_payment_id
        payment.gateway_captured_at = datetime.now(timezone.utc)
        payment.payment_status = 'captured'
        payment.payment_method = capture_result.method
        payment.gateway_metadata = capture_result.raw_response

        # Post GL entries
        self._post_gl_entries(payment)

        # Update bill status
        self._update_bill_status(payment.bill_id, 'paid')

        # Send receipt
        self._send_payment_receipt(payment)

        db.session.commit()

        return {
            'success': True,
            'payment_id': str(payment.payment_id),
            'status': 'captured',
            'message': 'Payment successful'
        }
```

---

## 6. Integration with Billing Module

### 6.1 Bill Payment Flow

**Scenario:** Patient receives treatment, bill generated, wants to pay online.

**Steps:**

1. **Bill Generation** (Existing)
   - Treatment completed
   - Bill created in billing module
   - Bill amount: ₹5,000
   - Status: 'unpaid'

2. **Payment Initiation**
   - Patient clicks "Pay Online" on bill
   - System creates gateway order
   - Frontend shows Razorpay checkout

3. **Payment Completion**
   - Patient enters card details
   - Razorpay processes payment
   - Success/failure callback

4. **Payment Verification**
   - Verify signature
   - Capture payment
   - Update bill status to 'paid'
   - Post GL entries:
     - Debit: Bank/Gateway account
     - Credit: Patient receivables

5. **Receipt Generation**
   - Generate payment receipt
   - Send via email/SMS
   - Print option

### 6.2 Frontend Integration

**File:** `app/templates/billing/bill_payment.html`

```html
<!-- Razorpay Checkout Integration -->
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>

<script>
function initiateGatewayPayment(billId, amount) {
    // Create order via backend API
    fetch('/api/patient-payment/create-order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            bill_id: billId,
            amount: amount,
            gateway_provider: 'razorpay'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Open Razorpay checkout
            var options = {
                "key": data.key_id,
                "amount": data.amount * 100,  // Amount in paise
                "currency": "INR",
                "name": "Skinspire Clinic",
                "description": "Bill Payment",
                "order_id": data.order_id,
                "handler": function (response) {
                    // Payment successful callback
                    verifyPayment(
                        data.payment_id,
                        response.razorpay_order_id,
                        response.razorpay_payment_id,
                        response.razorpay_signature
                    );
                },
                "prefill": {
                    "name": "{{ patient.patient_name }}",
                    "email": "{{ patient.email }}",
                    "contact": "{{ patient.phone }}"
                },
                "theme": {
                    "color": "#3399cc"
                }
            };

            var rzp = new Razorpay(options);
            rzp.open();
        }
    });
}

function verifyPayment(paymentId, orderId, razorpayPaymentId, signature) {
    // Verify and capture payment
    fetch('/api/patient-payment/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            payment_id: paymentId,
            gateway_order_id: orderId,
            gateway_payment_id: razorpayPaymentId,
            signature: signature
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/billing/payment-success/' + paymentId;
        } else {
            alert('Payment verification failed');
        }
    });
}
</script>

<button class="btn btn-primary" onclick="initiateGatewayPayment('{{ bill.bill_id }}', {{ bill.amount }})">
    Pay Online
</button>
```

---

## Summary

### Key Differences: Outgoing vs Incoming

| Feature | Outgoing (Supplier) | Incoming (Patient) |
|---------|--------------------|--------------------|
| **API** | Payouts API | Payment Gateway API |
| **Initiation** | Staff clicks "Pay" | Patient clicks "Pay Online" |
| **UI** | Admin interface | Patient-facing checkout |
| **Verification** | Webhook only | Signature + Webhook |
| **Capture** | Auto (payout sent) | Manual (capture after auth) |
| **Refund** | Reverse payout | Refund to source |
| **Fees** | Fixed per transaction | Percentage of amount |
| **Settlement** | Money out | Money in |

### Implementation Priority

**If implementing both:**

1. **Phase 1:** Outgoing payments (supplier payouts) - Main docs
   - Reason: More critical for vendor relationships
   - Lower volume, easier testing

2. **Phase 2:** Incoming payments (patient collections) - This addendum
   - Reason: Higher volume, more complex integration
   - Requires frontend checkout integration

**Shared Components:**
- Gateway configuration (same table)
- Transaction logging (same pattern)
- Webhook processing (extend existing)
- Reconciliation (combine both directions)

---

## Recommendation

**For Skinspire v2:**

1. **Start with outgoing payments** (follow Parts 1-5)
   - Establish gateway infrastructure
   - Build webhook processing
   - Set up reconciliation

2. **Add incoming payments later** (use this addendum)
   - Extend existing gateway adapters
   - Add patient payment service
   - Integrate with billing module

3. **Unified reconciliation**
   - Reconcile both payouts and collections
   - Net settlement calculation
   - Single dashboard for finance team

---

**For questions about incoming payment implementation, refer to:**
- Razorpay Payment Gateway Docs: https://razorpay.com/docs/payment-gateway/
- Razorpay Checkout Integration: https://razorpay.com/docs/checkout/
- This addendum covers architectural approach; detailed implementation would be Phase 2.
