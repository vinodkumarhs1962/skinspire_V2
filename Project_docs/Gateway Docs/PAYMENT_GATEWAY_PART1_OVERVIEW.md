# Payment Gateway Integration - Part 1: Overview & Architecture

**Part:** 1 of 5
**Focus:** Executive Summary, Architecture, Design Patterns
**Audience:** All team members, stakeholders, project managers

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Integration Requirements](#3-integration-requirements)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Gateway Abstraction Pattern](#5-gateway-abstraction-pattern)
6. [Integration Approach](#6-integration-approach)
7. [Component Interaction Flow](#7-component-interaction-flow)

---

## 1. Executive Summary

### 1.1 Objective

Integrate **Razorpay** and **Paytm** payment gateways into the existing Skinspire v2 supplier payment system to enable:

- ✅ **Digital Payouts** - Direct UPI and bank transfers via gateway APIs
- ✅ **Payment Links** - Generate secure links for supplier self-service payments
- ✅ **Automated Reconciliation** - Daily matching of gateway settlements with system records
- ✅ **Refund Management** - Handle payment reversals and refunds
- ✅ **Split Payments** - Pay multiple invoices in single gateway transaction

### 1.2 Business Benefits

**Operational Efficiency:**
- Reduce payment processing time by 50%
- Eliminate manual bank transfer entry errors (80% reduction)
- Automated reconciliation saves 2+ hours daily

**Financial Control:**
- Real-time payment status tracking
- Automated fee calculation and accounting
- Enhanced audit trail with gateway records

**Supplier Experience:**
- Faster payment delivery (instant UPI, same-day NEFT)
- Self-service payment options via links
- Transparent payment status

### 1.3 Key Constraints

**Non-Disruptive:**
- Existing manual payment flows remain unchanged
- No changes to approval workflow
- Backward compatible with current payment records

**Hybrid Model:**
- Staff can choose manual OR gateway payment
- Gateway applies only to UPI and bank transfers
- Cash and cheque remain manual-only

**Multi-Gateway:**
- Support both Razorpay and Paytm
- Configurable default per hospital/branch
- Easy to add more gateways later

---

## 2. Current State Analysis

### 2.1 Existing Payment Infrastructure

**Strengths:**
✅ Comprehensive multi-method payment support (cash, cheque, bank transfer, UPI, advance)
✅ Robust approval workflow (auto-approve < ₹10K, manual ≥ ₹10K)
✅ GL integration with automatic posting
✅ Advance payment allocation (FIFO)
✅ Soft delete with reversal support
✅ Branch-aware security
✅ **Gateway fields already in database** (unused)

**Current Payment Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Manual Payment Entry                                      │
│    - Staff enters payment details                           │
│    - Select methods: cash/cheque/bank/UPI/advance          │
│    - Link to invoice OR leave unallocated                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Approval Decision                                         │
│    Amount < ₹10K → Auto-approve + Post GL                   │
│    Amount ≥ ₹10K → Pending approval workflow                │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. GL Posting & Completion                                   │
│    - Create GL transaction                                   │
│    - Update invoice status                                   │
│    - Create AP subledger entries                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Gateway Infrastructure Already Present

The `SupplierPayment` model already contains comprehensive gateway fields (currently unused):

**Payment Categorization:**
```python
payment_category = Column(String(20), default='manual')
# Options: 'manual', 'gateway', 'upi', 'bank_transfer'

payment_source = Column(String(30), default='internal')
# Options: 'internal', 'razorpay', 'payu', 'upi', 'bank_api'
```

**Gateway Tracking Fields:**
```python
gateway_payment_id          # Gateway's payout ID (pout_xxx, ORDER_xxx)
gateway_order_id            # For payment links
gateway_transaction_id      # UTR/reference number
gateway_response_code       # HTTP status or error code
gateway_response_message    # Success/error message
gateway_fee                 # Gateway charges
gateway_tax                 # GST on charges
gateway_initiated_at        # When sent to gateway
gateway_completed_at        # When gateway confirmed
gateway_failed_at           # When gateway reported failure
gateway_metadata            # JSONB: Full response data
```

**Payment Link Fields:**
```python
payment_link_id             # Link identifier
payment_link_url            # URL sent to supplier
payment_link_expires_at     # Expiry timestamp
payment_link_status         # created, sent, expired, paid
```

### 2.3 Gaps Requiring Implementation

🔴 **No Gateway Service Layer**
- No `PaymentGatewayManager` service
- No Razorpay/Paytm adapter implementations
- No gateway API integration code

🔴 **No Webhook Infrastructure**
- No webhook receiver endpoints
- No signature verification
- No event processing logic

🔴 **No Reconciliation Engine**
- No settlement data fetching
- No transaction matching algorithm
- No discrepancy detection

🔴 **No Gateway Configuration**
- No database table for gateway settings
- No UI for managing API keys
- No test/live mode switching

🔴 **No UI Integration**
- Payment form doesn't offer gateway option
- No payment link generation UI
- No gateway status display

---

## 3. Integration Requirements

### 3.1 Functional Requirements

**FR-1: Gateway Payout Initiation**
- Staff can initiate UPI or bank transfer payout via gateway
- Select gateway provider (Razorpay/Paytm or use default)
- Select supplier's saved bank account/UPI ID
- Validate account details before submission
- Display gateway charges before confirmation

**FR-2: Payment Link Generation**
- Staff can generate payment link for supplier
- Link expires after configurable duration (24-72 hours)
- Send link via email and/or SMS
- Supplier clicks link and completes payment
- Webhook updates payment status automatically

**FR-3: Real-Time Status Tracking**
- Display current gateway payment status (pending, processing, completed, failed)
- Show UTR number when available
- Manual refresh status option
- Automatic status update via webhooks

**FR-4: Automated Reconciliation**
- Daily scheduled reconciliation job
- Fetch gateway settlement data
- Match with system payment records
- Detect and report discrepancies
- Generate reconciliation report

**FR-5: Refund Management**
- Initiate refund for completed gateway payment
- Create reverse payment record
- Track refund status
- Update GL entries for refund

**FR-6: Split Payment Support**
- Pay multiple invoices in single gateway transaction
- Allocate amounts to each invoice
- Track allocation in subledger

### 3.2 Non-Functional Requirements

**NFR-1: Security**
- Encrypt API keys at rest
- Verify webhook signatures (HMAC-SHA256)
- Use idempotency keys to prevent duplicates
- Rate limit API calls (10/minute per user)
- Log all gateway operations with IP address

**NFR-2: Performance**
- API response time < 2 seconds
- Webhook processing < 5 seconds
- Reconciliation runs within 10 minutes
- Support 100+ concurrent payouts

**NFR-3: Reliability**
- Gateway payout success rate > 95%
- Webhook retry on failure (3 attempts)
- Fallback to manual entry if gateway unavailable
- Transaction logging for audit

**NFR-4: Maintainability**
- Abstract gateway interface for easy provider addition
- Configuration-driven gateway selection
- Comprehensive error messages
- Detailed logging

**NFR-5: Compliance**
- Audit trail for all gateway operations
- PCI DSS compliance (no card data storage)
- RBI guidelines for digital payments
- Data retention policy compliance

---

## 4. High-Level Architecture

### 4.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SKINSPIRE PAYMENT SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────┐              ┌──────────────────┐                 │
│  │   Staff Portal    │              │ Supplier Portal   │                 │
│  │   (Admin UI)      │              │  (Self-Service)   │                 │
│  └────────┬──────────┘              └────────┬──────────┘                 │
│           │                                  │                            │
│           │ Manual Entry                     │ Payment Link               │
│           │ OR Gateway Payout                │ Completion                 │
│           │                                  │                            │
│           └──────────┬───────────────────────┘                            │
│                      │                                                    │
│                      ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │         Payment Controller & Service Layer                │           │
│  │  ┌────────────────────────────────────────────────────┐  │           │
│  │  │  Supplier Payment Service (Existing)               │  │           │
│  │  │  - Validation                                      │  │           │
│  │  │  - Approval Workflow                               │  │           │
│  │  │  - GL Posting                                      │  │           │
│  │  └────────────────┬───────────────────────────────────┘  │           │
│  │                   │                                       │           │
│  │                   ▼                                       │           │
│  │  ┌────────────────────────────────────────────────────┐  │           │
│  │  │  Payment Gateway Manager (NEW)                     │  │           │
│  │  │  - Gateway Selection Logic                         │  │           │
│  │  │  - Configuration Loading                           │  │           │
│  │  │  - Adapter Orchestration                           │  │           │
│  │  │  - Error Handling                                  │  │           │
│  │  │  - Transaction Logging                             │  │           │
│  │  └────────────────┬───────────────────────────────────┘  │           │
│  └───────────────────┼──────────────────────────────────────┘           │
│                      │                                                    │
│                      ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │      Gateway Abstraction Layer (Interface)                │           │
│  │      PaymentGatewayInterface (ABC)                        │           │
│  │      - create_payout()                                    │           │
│  │      - create_payment_link()                              │           │
│  │      - get_payout_status()                                │           │
│  │      - create_refund()                                    │           │
│  │      - verify_webhook_signature()                         │           │
│  │      - get_settlement_report()                            │           │
│  └──────────┬────────────────────────────────────┬───────────┘           │
│             │                                    │                       │
│             ▼                                    ▼                       │
│  ┌─────────────────────┐            ┌─────────────────────┐             │
│  │  Razorpay Adapter   │            │   Paytm Adapter     │             │
│  │  ┌───────────────┐  │            │  ┌───────────────┐ │             │
│  │  │ Payouts API   │  │            │  │ Money Transfer│ │             │
│  │  │ Payment Links │  │            │  │ API           │ │             │
│  │  │ Fund Accounts │  │            │  │ Payment Links │ │             │
│  │  │ Settlements   │  │            │  │ Settlements   │ │             │
│  │  └───────────────┘  │            │  └───────────────┘ │             │
│  └─────────┬───────────┘            └──────────┬──────────┘             │
└────────────┼──────────────────────────────────┼────────────────────────┘
             │                                   │
             │  HTTPS API Calls                  │  HTTPS API Calls
             │  (Payouts, Links)                 │  (Transfers, Links)
             │                                   │
             ▼                                   ▼
┌──────────────────────┐            ┌──────────────────────┐
│   Razorpay Service   │            │   Paytm Service      │
│                      │            │                      │
│  - Payout API        │            │  - Money Transfer    │
│  - Payment Links     │            │  - Payment Links     │
│  - Webhooks ─────────┼────┐       │  - Webhooks ─────────┼────┐
│  - Settlements       │    │       │  - Settlements       │    │
└──────────────────────┘    │       └──────────────────────┘    │
                            │                                   │
                            │  Webhook POST                     │  Webhook POST
                            │  (Payment status updates)         │  (Payment status)
                            │                                   │
                            └───────────┬───────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │         Webhook Processing Service (NEW)                  │
        │  ┌─────────────────────────────────────────────────────┐ │
        │  │  1. Signature Verification                          │ │
        │  │  2. Event Parsing                                   │ │
        │  │  3. Event Routing (success/failure/refund)          │ │
        │  │  4. Payment Status Update                           │ │
        │  │  5. GL Posting Trigger                              │ │
        │  │  6. Notification Dispatch                           │ │
        │  └─────────────────────────────────────────────────────┘ │
        └───────────────────────────────────────────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │      Reconciliation Service (NEW - Daily Job)             │
        │  ┌─────────────────────────────────────────────────────┐ │
        │  │  1. Fetch Gateway Settlements                       │ │
        │  │  2. Fetch System Payment Records                    │ │
        │  │  3. Match Transactions (UTR, Amount, Date)          │ │
        │  │  4. Identify Discrepancies                          │ │
        │  │  5. Generate Report                                 │ │
        │  │  6. Alert Finance Team                              │ │
        │  └─────────────────────────────────────────────────────┘ │
        └───────────────────────────────────────────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │              PostgreSQL Database                          │
        │  ┌────────────────────────────────────────┐              │
        │  │  Existing Tables:                       │              │
        │  │  - supplier_payment (gateway fields)    │              │
        │  │  - supplier                             │              │
        │  │  - supplier_invoice                     │              │
        │  │  - gl_transaction                       │              │
        │  └────────────────────────────────────────┘              │
        │  ┌────────────────────────────────────────┐              │
        │  │  New Tables:                            │              │
        │  │  - gateway_configuration                │              │
        │  │  - gateway_transaction_log              │              │
        │  │  - gateway_webhook                      │              │
        │  │  - gateway_reconciliation               │              │
        │  │  - gateway_reconciliation_detail        │              │
        │  └────────────────────────────────────────┘              │
        └───────────────────────────────────────────────────────────┘
```

### 4.2 Key Architectural Principles

**1. Non-Invasive Integration**
- Existing payment flows unchanged
- New gateway logic added alongside, not replacing
- Backward compatible with all existing payments

**2. Single Responsibility**
- Gateway Manager: Orchestration and configuration
- Adapters: Provider-specific API integration
- Webhook Processor: Event handling
- Reconciliation Service: Settlement matching

**3. Dependency Inversion**
- All adapters implement `PaymentGatewayInterface`
- Gateway Manager depends on interface, not concrete classes
- Easy to add new gateways without modifying existing code

**4. Fail-Safe Design**
- Gateway failure falls back to manual entry
- Webhook failure triggers manual status check
- Reconciliation discrepancies flagged for review
- All operations logged for debugging

---

## 5. Gateway Abstraction Pattern

### 5.1 Interface Design

**Abstract Base Class:**

```python
# app/services/payment_gateway/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import date, datetime

class PaymentGatewayInterface(ABC):
    """
    Abstract interface for payment gateway integrations.
    All gateway adapters must implement this interface.
    """

    @abstractmethod
    def create_payout(self, payment_data: Dict) -> 'GatewayPayoutResponse':
        """
        Initiate payout to supplier bank account/UPI.

        Args:
            payment_data: {
                'payment_id': str,  # Internal payment ID
                'supplier_id': str,
                'supplier_name': str,
                'amount': Decimal,
                'payment_method': 'upi' | 'bank_transfer',
                'account_details': {
                    # For UPI:
                    'upi_id': str,
                    # For Bank Transfer:
                    'account_holder_name': str,
                    'account_number': str,
                    'ifsc_code': str,
                    'bank_name': str
                },
                'narration': str,
                'invoice_number': str (optional),
                'hospital_id': str,
                'branch_id': str
            }

        Returns:
            GatewayPayoutResponse with status and gateway IDs

        Raises:
            GatewayException on failure
        """
        pass

    @abstractmethod
    def create_payment_link(self, payment_data: Dict) -> 'GatewayLinkResponse':
        """
        Generate payment link for supplier to complete payment.

        Args:
            payment_data: {
                'payment_id': str,
                'supplier_id': str,
                'supplier_name': str,
                'amount': Decimal,
                'description': str,
                'supplier_email': str (optional),
                'supplier_phone': str (optional),
                'expires_at': datetime,
                'callback_url': str
            }

        Returns:
            GatewayLinkResponse with link URL and ID
        """
        pass

    @abstractmethod
    def get_payout_status(self, gateway_payout_id: str) -> 'GatewayStatusResponse':
        """
        Check current status of payout.

        Args:
            gateway_payout_id: Gateway's payout identifier

        Returns:
            GatewayStatusResponse with current status
        """
        pass

    @abstractmethod
    def create_refund(
        self,
        gateway_payout_id: str,
        amount: Decimal,
        reason: str
    ) -> 'GatewayRefundResponse':
        """
        Initiate refund for completed payout.

        Args:
            gateway_payout_id: Original payout ID
            amount: Refund amount (can be partial)
            reason: Refund reason

        Returns:
            GatewayRefundResponse with refund status
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature for authenticity.

        Args:
            payload: Raw webhook payload
            signature: Signature from webhook header
            secret: Webhook secret key

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_settlement_report(
        self,
        from_date: date,
        to_date: date
    ) -> List['GatewaySettlement']:
        """
        Fetch settlement data for reconciliation.

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of GatewaySettlement objects
        """
        pass
```

### 5.2 Data Transfer Objects

**Response Classes:**

```python
# app/services/payment_gateway/base.py

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class GatewayPayoutResponse:
    """Response from gateway payout creation"""
    success: bool
    gateway_payment_id: str  # Gateway's payout ID
    transaction_id: Optional[str]  # UTR number (may be available later)
    status: str  # 'pending', 'processing', 'completed', 'failed'
    amount: Decimal
    fee: Decimal  # Gateway charges
    tax: Decimal  # GST on charges
    message: str
    raw_response: Dict[str, Any]  # Full gateway response for logging

@dataclass
class GatewayLinkResponse:
    """Response from payment link creation"""
    success: bool
    link_id: str
    link_url: str
    expires_at: datetime
    status: str  # 'created', 'sent', 'expired', 'paid'
    raw_response: Dict[str, Any]

@dataclass
class GatewayStatusResponse:
    """Response from status check"""
    gateway_payment_id: str
    status: str
    transaction_id: Optional[str]  # UTR
    updated_at: datetime
    failure_reason: Optional[str]
    raw_response: Dict[str, Any]

@dataclass
class GatewayRefundResponse:
    """Response from refund initiation"""
    success: bool
    refund_id: str
    status: str  # 'pending', 'processed', 'failed'
    amount: Decimal
    message: str
    raw_response: Dict[str, Any]

@dataclass
class GatewaySettlement:
    """Settlement data for reconciliation"""
    settlement_id: str
    settlement_date: date
    gateway_payment_id: str
    amount: Decimal
    fees: Decimal
    tax: Decimal
    utr: str
    status: str  # 'processed', 'failed', 'reversed'
    raw_data: Dict[str, Any]

@dataclass
class GatewayException(Exception):
    """Custom exception for gateway errors"""
    message: str
    error_code: str
    gateway_response: Optional[Dict] = None
```

### 5.3 Provider Adapter Skeleton

**Example: Razorpay Adapter Structure**

```python
# app/services/payment_gateway/adapters/razorpay_adapter.py

class RazorpayAdapter(PaymentGatewayInterface):
    """
    Razorpay payment gateway implementation.

    Uses:
    - Razorpay Payouts API (X product)
    - Razorpay Fund Accounts
    - Razorpay Payment Links
    - Razorpay Settlements API
    """

    def __init__(self, config: Dict):
        """Initialize with decrypted credentials"""
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.mode = config.get('mode', 'test')
        self.client = razorpay.Client(auth=(self.api_key, self.api_secret))

    def create_payout(self, payment_data: Dict) -> GatewayPayoutResponse:
        """Implementation uses Razorpay Payouts API"""
        # 1. Create/get fund account
        # 2. Create payout
        # 3. Parse response
        # 4. Return GatewayPayoutResponse
        pass

    def create_payment_link(self, payment_data: Dict) -> GatewayLinkResponse:
        """Implementation uses Razorpay Payment Links"""
        pass

    def get_payout_status(self, gateway_payout_id: str) -> GatewayStatusResponse:
        """Fetch payout by ID"""
        pass

    def create_refund(self, gateway_payout_id: str, amount: Decimal, reason: str) -> GatewayRefundResponse:
        """Note: Razorpay payout refunds handled via dashboard"""
        pass

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """HMAC-SHA256 verification"""
        pass

    def get_settlement_report(self, from_date: date, to_date: date) -> List[GatewaySettlement]:
        """Fetch settlements from Razorpay API"""
        pass

    # Helper methods
    def _get_or_create_fund_account(self, supplier_id, account_details, payment_method):
        """Manage Razorpay fund accounts"""
        pass

    def _map_razorpay_status(self, razorpay_status: str) -> str:
        """Map Razorpay status to internal status"""
        pass
```

---

## 6. Integration Approach

### 6.1 Hybrid Payment Model

Staff can choose between three payment modes:

**Mode 1: Manual Entry** (Existing - No Changes)
- Staff enters payment details manually
- Cash, cheque, bank transfer, UPI amounts
- Bank reference numbers entered by staff
- No gateway involvement

**Mode 2: Gateway Payout** (New)
- Staff initiates payment via gateway API
- System sends payout request to Razorpay/Paytm
- Gateway handles actual money transfer
- Webhook updates status automatically
- UTR populated by gateway

**Mode 3: Payment Link** (New)
- Staff generates payment link
- Link sent to supplier via email/SMS
- Supplier clicks link and completes payment
- Webhook updates status when paid
- No staff intervention after link generation

**Selection Logic:**

```
┌─────────────────────────────────────────────────────────┐
│  Payment Creation Form                                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Payment Mode:                                    │  │
│  │  ○ Manual Entry (default)                         │  │
│  │  ○ Gateway Payout                                 │  │
│  │  ○ Payment Link                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  If Manual Entry → Show existing form fields             │
│  If Gateway Payout → Show gateway options                │
│  If Payment Link → Show link generation options          │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Gateway Selection Logic

**Default Gateway:**
- Configured per hospital/branch in `gateway_configuration`
- Falls back to hospital-wide if no branch-specific config
- Can be overridden per payment

**Multi-Gateway Support:**

```python
# Example configuration
Hospital A:
    Default: Razorpay
    Branch 1: Razorpay
    Branch 2: Paytm (custom)

Payment Creation:
    - Use branch default if available
    - Else use hospital default
    - Staff can manually override
```

### 6.3 Approval Workflow Integration

Gateway payments follow the **same approval workflow** as manual payments:

**Amount < ₹10,000:**
1. Create payment record
2. Initiate gateway payout immediately
3. Auto-approve payment
4. Wait for webhook confirmation
5. Post GL entries on success

**Amount ≥ ₹10,000:**
1. Create payment record (status: draft)
2. Set `requires_approval = True`
3. Wait for manual approval
4. **On approval:** Initiate gateway payout
5. Wait for webhook confirmation
6. Post GL entries on success

**Flow Diagram:**

```
┌──────────────────────┐
│  Create Payment      │
│  (Gateway Mode)      │
└──────┬───────────────┘
       │
       ▼
  ┌─────────────────┐
  │ Amount Check    │
  └────┬────────────┘
       │
       ├─── < ₹10K ───► Auto-Approve ──► Initiate Gateway Payout
       │                                        │
       │                                        ▼
       └─── ≥ ₹10K ───► Pending Approval ──► Wait for Approver
                                                 │
                                                 ▼
                                        Approve ─► Initiate Gateway Payout
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │  Gateway API     │
                                        │  Call            │
                                        └────┬─────────────┘
                                             │
                                   ┌─────────┴─────────┐
                                   │                   │
                                   ▼                   ▼
                          ┌─────────────┐    ┌─────────────┐
                          │  Success    │    │  Failure    │
                          └──────┬──────┘    └──────┬──────┘
                                 │                   │
                                 │                   ▼
                                 │          Update payment status
                                 │          workflow_status = 'gateway_failed'
                                 │          Send alert to staff
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Webhook Received│
                        │  (Success)       │
                        └────┬─────────────┘
                             │
                             ▼
                        ┌──────────────────┐
                        │  Update Payment  │
                        │  - Status: Completed
                        │  - UTR populated│
                        │  - GL Posted    │
                        └─────────────────┘
```

---

## 7. Component Interaction Flow

### 7.1 Payout Flow (Happy Path)

```
Staff           Payment          Gateway         Gateway         Webhook        Database
Portal          Service          Manager         Adapter         Processor
  │               │                │               │               │               │
  │ Create Payment│                │               │               │               │
  │ (Gateway Mode)│                │               │               │               │
  ├──────────────►│                │               │               │               │
  │               │ Validate       │               │               │               │
  │               │ & Save         │               │               │               │
  │               ├────────────────┼───────────────┼───────────────┼──────────────►│
  │               │                │               │               │               │
  │               │ Initiate Payout│               │               │               │
  │               ├───────────────►│               │               │               │
  │               │                │ Get Adapter   │               │               │
  │               │                │ (Razorpay)    │               │               │
  │               │                ├──────────────►│               │               │
  │               │                │               │               │               │
  │               │                │ Create Payout │               │               │
  │               │                │ API Call      │               │               │
  │               │                ├──────────────►│               │               │
  │               │                │               │ POST /payouts │               │
  │               │                │               ├──────────────────────┐        │
  │               │                │               │                      │        │
  │               │                │               │◄─────────────────────┘        │
  │               │                │               │ Response: pout_xxx   │        │
  │               │                │◄──────────────┤                               │
  │               │                │ GatewayPayout │                               │
  │               │                │ Response      │                               │
  │               │◄───────────────┤               │                               │
  │               │                │               │                               │
  │               │ Update Payment │               │                               │
  │               │ with Gateway ID│               │                               │
  │               ├────────────────┼───────────────┼───────────────┼──────────────►│
  │◄──────────────┤                │               │               │               │
  │ Success        │               │               │               │               │
  │ (Pending)      │               │               │               │               │
  │                │               │               │               │               │
  │                │               │               │               │               │
  │        [Time passes - Gateway processes payment]              │               │
  │                │               │               │               │               │
  │                │               │               │   Webhook Event              │
  │                │               │               │   payout.processed           │
  │                │               │               │◄─────────────────────────────┤
  │                │               │               │               │               │
  │                │               │               │  Process      │               │
  │                │               │               │  Webhook      │               │
  │                │               │               ├──────────────►│               │
  │                │               │               │               │ Verify        │
  │                │               │               │               │ Signature     │
  │                │               │               │               │               │
  │                │               │               │               │ Find Payment  │
  │                │               │               │               ├──────────────►│
  │                │               │               │               │◄──────────────┤
  │                │               │               │               │               │
  │                │               │               │               │ Update Status │
  │                │               │               │               │ Add UTR       │
  │                │               │               │               │ Post GL       │
  │                │               │               │               ├──────────────►│
  │                │               │               │               │               │
  │                │               │               │               │ Send Notification
  │◄──────────────────────────────────────────────────────────────┤               │
  │ Email: Payment Completed                       │               │               │
  │                │               │               │               │               │
```

### 7.2 Payment Link Flow

```
Staff           Payment          Gateway         Supplier        Webhook         Database
Portal          Service          Manager         Portal          Processor
  │               │                │               │               │               │
  │ Generate Link │                │               │               │               │
  ├──────────────►│                │               │               │               │
  │               │ Create Payment │               │               │               │
  │               │ Record         │               │               │               │
  │               ├────────────────┼───────────────┼───────────────┼──────────────►│
  │               │                │               │               │               │
  │               │ Create Link    │               │               │               │
  │               ├───────────────►│               │               │               │
  │               │                │ Get Adapter   │               │               │
  │               │                │               │               │               │
  │               │                │ Create Link   │               │               │
  │               │                │ API Call      │               │               │
  │               │                ├──────────────────────┐        │               │
  │               │                │               │      │        │               │
  │               │                │◄─────────────────────┘        │               │
  │               │                │ Link: plink_xxx               │               │
  │               │◄───────────────┤               │               │               │
  │               │                │               │               │               │
  │               │ Update Payment │               │               │               │
  │               │ with Link      │               │               │               │
  │               ├────────────────┼───────────────┼───────────────┼──────────────►│
  │               │                │               │               │               │
  │               │ Send Email/SMS │               │               │               │
  │               ├───────────────────────────────►│               │               │
  │               │                │               │               │               │
  │◄──────────────┤                │               │               │               │
  │ Link Created   │               │               │               │               │
  │                │               │               │               │               │
  │                │               │               │               │               │
  │                │               │    Click Link │               │               │
  │                │               │◄──────────────┤               │               │
  │                │               │               │               │               │
  │                │               │  Payment Page │               │               │
  │                │               ├──────────────►│               │               │
  │                │               │               │ Enter Details │               │
  │                │               │               │ Complete Pay  │               │
  │                │               │◄──────────────┤               │               │
  │                │               │               │               │               │
  │                │               │   Webhook: payment_link.paid  │               │
  │                │               ├───────────────┼──────────────►│               │
  │                │               │               │               │ Update Status │
  │                │               │               │               ├──────────────►│
  │                │               │               │               │ Post GL       │
  │                │               │               │               │               │
  │◄──────────────────────────────────────────────────────────────┤               │
  │ Notification: Payment Received │               │               │               │
```

### 7.3 Reconciliation Flow

```
Scheduled         Reconciliation    Gateway         System           Database
Job               Service           API             Records
  │                 │                 │               │                 │
  │ Daily 2 AM      │                 │               │                 │
  ├────────────────►│                 │               │                 │
  │                 │ Fetch Gateway   │               │                 │
  │                 │ Settlements     │               │                 │
  │                 ├────────────────►│               │                 │
  │                 │                 │ GET /settlements                │
  │                 │◄────────────────┤               │                 │
  │                 │ Settlement Data │               │                 │
  │                 │                 │               │                 │
  │                 │ Fetch System Payments           │                 │
  │                 ├─────────────────┼───────────────┼────────────────►│
  │                 │◄────────────────┼───────────────┼─────────────────┤
  │                 │ Payment Records │               │                 │
  │                 │                 │               │                 │
  │                 │ Match Transactions             │                 │
  │                 │ (UTR, Amount, Date)            │                 │
  │                 │                 │               │                 │
  │                 │ Matched: 95     │               │                 │
  │                 │ Unmatched Gateway: 2           │                 │
  │                 │ Unmatched System: 1            │                 │
  │                 │ Amount Mismatch: 2             │                 │
  │                 │                 │               │                 │
  │                 │ Save Reconciliation            │                 │
  │                 ├─────────────────┼───────────────┼────────────────►│
  │                 │                 │               │                 │
  │                 │ Generate Report │               │                 │
  │                 │                 │               │                 │
  │                 │ Send Alert      │               │                 │
  │                 ├────────────────────────────────────────┐          │
  │                 │                 │               │      │          │
  │                 │                 │        Email: 5 Discrepancies  │
  │                 │                 │               │      │          │
  │◄────────────────┼─────────────────┼───────────────┼──────┘          │
  │ Reconciliation Complete           │               │                 │
```

---

## Summary

This overview document provides the foundation for understanding the payment gateway integration approach. Key takeaways:

✅ **Non-disruptive** - Existing flows unchanged, gateway is optional
✅ **Hybrid model** - Manual, gateway payout, or payment link
✅ **Abstracted design** - Easy to add new gateways
✅ **Webhook-driven** - Real-time status updates
✅ **Automated reconciliation** - Daily settlement matching
✅ **Existing infrastructure** - Database fields already present

**Next:** Review Part 2 for detailed database schema design.
