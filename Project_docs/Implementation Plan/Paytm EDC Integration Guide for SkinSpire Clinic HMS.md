# Paytm EDC Integration Guide for SkinSpire Clinic HMS

**Version:** 1.0  
**Date:** November 2025  
**Author:** SkinSpire Development Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Integration Options](#2-integration-options)
3. [Recommended Approach for HMS](#3-recommended-approach-for-hms)
4. [Credentials and Setup](#4-credentials-and-setup)
5. [API Reference](#5-api-reference)
6. [Integration Flow](#6-integration-flow)
7. [Implementation Plan](#7-implementation-plan)
8. [Database Schema](#8-database-schema)
9. [Service Module Design](#9-service-module-design)
10. [Error Handling](#10-error-handling)
11. [Testing Strategy](#11-testing-strategy)
12. [Go-Live Checklist](#12-go-live-checklist)

---

## 1. Overview

### 1.1 Purpose

This document outlines the integration of Paytm EDC (Electronic Data Capture) card machines with the SkinSpire Clinic HMS billing module. The integration enables seamless card and UPI payment collection at billing counters.

### 1.2 Scope

- Accept payments via Credit/Debit cards
- Accept payments via UPI/QR code
- Real-time payment status updates
- Transaction reconciliation
- Void and refund processing

### 1.3 Key Benefits

| Benefit | Description |
|---------|-------------|
| **Seamless Billing** | Payment requests sent directly from HMS to EDC machine |
| **No Manual Entry** | Amount auto-populated on EDC, reducing errors |
| **Real-time Updates** | Payment status reflects immediately in HMS |
| **Audit Trail** | Complete transaction history with bank references |
| **Reconciliation** | Easy matching of HMS records with Paytm settlements |

---

## 2. Integration Options

Paytm provides multiple integration methods for EDC machines:

### 2.1 Comparison Matrix

| Method | Connection | Best For | Complexity |
|--------|------------|----------|------------|
| **Wireless API** | Internet (REST API) | Web-based HMS like Flask | Medium |
| **Bluetooth** | Bluetooth SDK | Android mobile apps | High |
| **Wired USB** | Physical USB cable | Low connectivity areas | Medium |
| **Payment Request Queue** | Internet API | Multiple billing counters | Medium |
| **App Invoke** | Android deep links | Apps on Paytm EDC device | High |

### 2.2 Selected Approach: Wireless API

For SkinSpire HMS, we recommend **Wireless API Integration** because:

- HMS is web-based (Flask application)
- Clinic has reliable internet connectivity
- Simple REST API integration
- No additional hardware/SDK required
- Supports multiple EDC devices with same MID

---

## 3. Recommended Approach for HMS

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SKINSPIRE HMS (Flask)                            │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐    │
│  │   Billing   │───▶│  Paytm EDC       │───▶│  Payment            │    │
│  │   Module    │    │  Service         │    │  Recording          │    │
│  └─────────────┘    └──────────────────┘    └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS REST API
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PAYTM SERVER                                    │
│                  (securegw-edc.paytm.in)                                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Internet
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PAYTM EDC MACHINE                                  │
│              (At Billing Counter / Reception)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Payment Flow

```
Patient at Billing Counter
         │
         ▼
┌─────────────────────┐
│ 1. Create Invoice   │  HMS generates patient invoice
│    in HMS           │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 2. Select "Pay via  │  Staff clicks Paytm payment option
│    Paytm EDC"       │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 3. HMS calls Sale   │  POST /ecr/payment/request
│    API              │  Amount, Invoice No, Patient Name
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 4. Paytm returns    │  Request accepted, routed to EDC
│    ACCEPTED_SUCCESS │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 5. EDC shows        │  Staff accepts on EDC
│    payment popup    │  Patient taps/inserts card or scans QR
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 6. HMS polls Status │  Every 10 seconds until final status
│    API              │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 7. Update HMS       │  Mark invoice as paid
│    records          │  Store transaction references
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ 8. Print Receipt    │  HMS prints billing receipt
│                     │  EDC prints card slip
└─────────────────────┘
```

---

## 4. Credentials and Setup

### 4.1 Required Credentials

| Credential | Description | Where to Get |
|------------|-------------|--------------|
| **MID** | Merchant ID (20 chars) | Paytm Dashboard → Developer Settings |
| **Merchant Key** | Secret key for checksums | Paytm Dashboard → API Keys |
| **TID** | Terminal ID (8 digits) | Allocated per EDC device |
| **Channel ID** | Integration channel identifier | Provided during onboarding |

### 4.2 Environment URLs

| Environment | Base URL | Purpose |
|-------------|----------|---------|
| **Staging** | `https://securegw-stage.paytm.in` | Development & Testing |
| **Production** | `https://securegw-edc.paytm.in` | Live Transactions |

### 4.3 Onboarding Steps

#### Step 1: Register as Paytm Business Merchant

1. Visit: https://business.paytm.com
2. Click "Sign Up" or "Get Started"
3. Complete registration with:
   - Business name and type
   - Owner/authorized signatory details
   - Contact information

#### Step 2: Complete KYC Verification

Submit the following documents:
- Business PAN card
- GST registration certificate (if applicable)
- Bank account details (cancelled cheque / bank statement)
- Business address proof
- Identity proof of authorized signatory

#### Step 3: Request EDC Machine

1. Contact Paytm sales team or apply through dashboard
2. Specify requirement: **Wireless API Integration**
3. Mention number of devices needed
4. Provide installation location details

#### Step 4: Obtain API Credentials

1. Login to Paytm Merchant Dashboard: https://dashboard.paytm.com
2. Navigate to **Developer Settings** → **API Keys**
3. Copy credentials:
   - **Test Mode**: For staging environment
   - **Production Mode**: After account activation

#### Step 5: Receive TID Allocation

- Each EDC device receives a unique TID
- Staging TID for testing
- Production TID for live transactions
- TID is activated when device is set up

#### Step 6: Integration Support

Contact Paytm integration team:
- Email: integrations@paytm.com
- Request: Checksum library, sample code, technical documentation
- Assigned: Key Account Manager (KAM) for support

---

## 5. API Reference

### 5.1 Sale API - Initiate Payment

**Endpoint:** `POST /ecr/payment/request`

**Purpose:** Send payment request from HMS to EDC machine

#### Request Structure

```json
{
  "head": {
    "requestTimeStamp": "2024-11-24 14:30:00",
    "channelId": "SKINSPIRE",
    "checksum": "GENERATED_CHECKSUM_VALUE",
    "version": "3.1"
  },
  "body": {
    "paytmMid": "SKINSPIRE_MID_HERE",
    "paytmTid": "12345678",
    "transactionDateTime": "2024-11-24 14:30:00",
    "merchantTransactionId": "BILL20241124001",
    "merchantReferenceNo": "INV-2024-0001",
    "transactionAmount": "250000",
    "merchantExtendedInfo": {
      "PaymentMode": "All"
    },
    "displayInfo": {
      "Patient": "Ramesh Kumar",
      "Invoice": "INV-2024-0001"
    },
    "printInfo": {
      "InvoiceNo": "INV-2024-0001",
      "PatientName": "Ramesh Kumar",
      "ClinicName": "SkinSpire Clinic"
    }
  }
}
```

#### Request Parameters

**Head Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `requestTimeStamp` | string(25) | Yes | Format: yyyy-MM-dd HH:mm:ss |
| `channelId` | string(32) | Yes | Provided by Paytm |
| `checksum` | string(108) | Yes | HMAC-SHA256 signature of body |
| `version` | string(64) | No | API version (default: 3.1) |

**Body Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `paytmMid` | string(20) | Yes | Merchant ID |
| `paytmTid` | string(8) | No | Terminal ID (if specific device) |
| `transactionDateTime` | string(25) | Yes | Transaction initiation time |
| `merchantTransactionId` | string(8-32) | Yes | Unique ID per transaction |
| `merchantReferenceNo` | string(32) | No | Invoice/bill reference |
| `transactionAmount` | string(12) | Yes | Amount in **paise** |
| `merchantExtendedInfo` | object | No | PaymentMode: All/CARD/QR |
| `displayInfo` | object(3) | No | Shown on EDC screen |
| `printInfo` | object | No | Printed on EDC receipt |

#### Response Structure

**Success Response:**

```json
{
  "head": {
    "responseTimeStamp": "2024-11-24 14:30:01",
    "channelId": "SKINSPIRE",
    "version": "3.1"
  },
  "body": {
    "merchantTransactionId": "BILL20241124001",
    "paytmMid": "SKINSPIRE_MID_HERE",
    "paytmTid": "12345678",
    "resultInfo": {
      "resultCode": "0009",
      "resultStatus": "ACCEPTED_SUCCESS",
      "resultMsg": "ACCEPTED_SUCCESS"
    }
  }
}
```

**Error Response:**

```json
{
  "body": {
    "resultInfo": {
      "resultCode": "0233",
      "resultStatus": "FAIL",
      "resultMsg": "Duplicate Order Id..!"
    }
  }
}
```

#### Response Codes

| Code | Status | Message | Action |
|------|--------|---------|--------|
| `0009` | ACCEPTED_SUCCESS | Request accepted | Proceed to status check |
| `0002` | FAIL | Invalid parameters | Check request format |
| `0007` | FAIL | Terminal not active | Verify TID/device status |
| `0233` | FAIL | Duplicate Order Id | Use unique transaction ID |
| `0330` | FAIL | Invalid checksum | Regenerate checksum |
| `0333` | FAIL | Multiple requests | Wait for current txn |

---

### 5.2 Status Enquiry API - Check Payment Status

**Endpoint:** `POST /ecr/V2/payment/status`

**Purpose:** Poll transaction status after initiating payment

#### Request Structure

```json
{
  "head": {
    "requestTimeStamp": "2024-11-24 14:30:15",
    "channelId": "SKINSPIRE",
    "checksum": "GENERATED_CHECKSUM_VALUE",
    "version": "3.1"
  },
  "body": {
    "paytmMid": "SKINSPIRE_MID_HERE",
    "paytmTid": "12345678",
    "transactionDateTime": "2024-11-24 14:30:00",
    "merchantTransactionId": "BILL20241124001"
  }
}
```

#### Response Structure (Success)

```json
{
  "head": {
    "responseTimeStamp": "2024-11-24 14:31:00",
    "channelId": "SKINSPIRE",
    "version": "3.1"
  },
  "body": {
    "merchantTransactionId": "BILL20241124001",
    "paytmMid": "SKINSPIRE_MID_HERE",
    "paytmTid": "12345678",
    "transactionAmount": "250000",
    "transactionDateTime": "2024-11-24 14:30:00",
    "rrn": "432109876543",
    "authCode": "123456",
    "bankTransactionId": "HDFC123456789",
    "paymentMode": "CREDIT_CARD",
    "cardType": "VISA",
    "maskedCardNo": "XXXX-XXXX-XXXX-1234",
    "terminalId": "12345678",
    "resultInfo": {
      "resultCode": "0000",
      "resultStatus": "TXN_SUCCESS",
      "resultMsg": "Transaction Successful"
    }
  }
}
```

#### Transaction Status Values

| Status | Description | HMS Action |
|--------|-------------|------------|
| `TXN_SUCCESS` | Payment completed | Mark invoice paid, store references |
| `TXN_FAILURE` | Payment failed | Show error, allow retry |
| `PENDING` | Awaiting completion | Continue polling |
| `ACCEPTED` | Request accepted by EDC | Continue polling |

---

### 5.3 Void API - Cancel Same-Day Transaction

**Endpoint:** `POST /ecr/void/request`

**Purpose:** Cancel/reverse a transaction made on the same day

#### Request Structure

```json
{
  "head": {
    "requestTimeStamp": "2024-11-24 16:00:00",
    "channelId": "SKINSPIRE",
    "checksum": "GENERATED_CHECKSUM_VALUE",
    "version": "3.1"
  },
  "body": {
    "paytmMid": "SKINSPIRE_MID_HERE",
    "paytmTid": "12345678",
    "transactionDateTime": "2024-11-24 16:00:00",
    "merchantTransactionId": "VOID20241124001",
    "originalMerchantTransactionId": "BILL20241124001",
    "transactionAmount": "250000"
  }
}
```

**Note:** Void is only available for same-day transactions. For previous day refunds, use Refund API or Paytm Dashboard.

---

### 5.4 Payment Request Queue API (Alternative)

For multi-counter setups, use the Payment Request Queue:

**Create Payment Request:** `POST /edc-integration-service/payment/request`

```json
{
  "head": {
    "clientId": "SKINSPIRE",
    "reqHash": "HASH_VALUE"
  },
  "body": {
    "txnDate": "2024-11-24 15:10:07",
    "merchantTxnId": "BILL20241124002",
    "txnAmount": "150000",
    "txnNumber": "INV-2024-0002",
    "mid": "SKINSPIRE_MID_HERE"
  }
}
```

**Response:**
```json
{
  "body": {
    "cpayId": "123456",
    "status": "IN_QUEUE"
  }
}
```

The 6-digit `cpayId` is displayed to patient. Staff enters this on any EDC machine with same MID to collect payment.

**Check Status:** `GET /edc-integration-service/txn/status?cpayId={cpayId}&storeId={storeId}&txnDate={txnDate}`

---

## 6. Integration Flow

### 6.1 Normal Payment Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         HMS BILLING UI                           │
│                                                                  │
│  Patient: Ramesh Kumar          Invoice: INV-2024-0001          │
│  ─────────────────────────────────────────────────────────────  │
│  Consultation Fee                              ₹ 500.00          │
│  Medicine (Tretinoin Cream)                    ₹ 250.00          │
│  Procedure (Chemical Peel)                   ₹ 1,750.00          │
│  ─────────────────────────────────────────────────────────────  │
│  Total Amount                                ₹ 2,500.00          │
│                                                                  │
│  Payment Method:                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐                  │
│  │  Cash   │  │  UPI    │  │  Paytm EDC Card │ ← Selected       │
│  └─────────┘  └─────────┘  └─────────────────┘                  │
│                                                                  │
│                    [ Process Payment ]                           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ Click "Process Payment"
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    HMS BACKEND (Flask)                           │
│                                                                  │
│  1. Generate unique merchantTransactionId                        │
│  2. Convert amount to paise (2500.00 → 250000)                  │
│  3. Generate checksum                                            │
│  4. Call Paytm Sale API                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ POST /ecr/payment/request
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       PAYTM SERVER                               │
│                                                                  │
│  - Validate request                                              │
│  - Return ACCEPTED_SUCCESS                                       │
│  - Route to EDC machine                                          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PAYTM EDC MACHINE                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    PAYMENT REQUEST                         │ │
│  │                                                            │ │
│  │   Amount: ₹ 2,500.00                                       │ │
│  │   Ref: INV-2024-0001                                       │ │
│  │   Patient: Ramesh Kumar                                    │ │
│  │                                                            │ │
│  │   ┌──────────┐         ┌──────────┐                       │ │
│  │   │  Accept  │         │  Reject  │                       │ │
│  │   └──────────┘         └──────────┘                       │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ Staff clicks Accept
                              │ Patient taps/inserts card
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    HMS BACKEND (Polling)                         │
│                                                                  │
│  - Wait 10 seconds                                               │
│  - Call Status Enquiry API                                       │
│  - If PENDING, retry every 10 seconds                           │
│  - If SUCCESS, update records                                    │
│  - If FAILURE, show error                                        │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ TXN_SUCCESS received
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    HMS DATABASE UPDATE                           │
│                                                                  │
│  - Create payment record                                         │
│  - Link to invoice                                               │
│  - Store: RRN, Auth Code, Card details                          │
│  - Update invoice status: PAID                                   │
│  - Log audit trail                                               │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       HMS BILLING UI                             │
│                                                                  │
│  ✅ Payment Successful                                           │
│                                                                  │
│  Transaction ID: BILL20241124001                                 │
│  RRN: 432109876543                                               │
│  Card: VISA XXXX-1234                                            │
│  Amount: ₹ 2,500.00                                              │
│                                                                  │
│                    [ Print Receipt ]                             │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Status Polling Logic

```python
# Pseudocode for status polling

def poll_payment_status(merchant_transaction_id, max_attempts=30):
    """
    Poll payment status with exponential backoff
    Max wait: ~5 minutes (30 attempts × 10 seconds)
    """
    
    attempt = 0
    initial_delay = 10  # seconds
    
    while attempt < max_attempts:
        # Wait before checking
        time.sleep(initial_delay)
        
        # Call Status API
        response = paytm_service.check_status(merchant_transaction_id)
        status = response['body']['resultInfo']['resultStatus']
        
        if status == 'TXN_SUCCESS':
            return {
                'success': True,
                'data': response['body']
            }
        
        elif status == 'TXN_FAILURE':
            return {
                'success': False,
                'error': response['body']['resultInfo']['resultMsg']
            }
        
        elif status in ['PENDING', 'ACCEPTED']:
            attempt += 1
            continue
        
        else:
            # Unknown status
            attempt += 1
            continue
    
    # Timeout - transaction status unknown
    return {
        'success': False,
        'error': 'Payment timeout. Please check EDC machine.'
    }
```

---

## 7. Implementation Plan

### 7.1 Phase 1: Foundation (Week 1)

| Task | Description | Files |
|------|-------------|-------|
| Create service module | Paytm API integration service | `paytm_edc_service.py` |
| Add configuration | Environment-based credentials | `config.py` |
| Database schema | Payment transaction tables | Migration script |
| Checksum utility | HMAC-SHA256 signature generation | `paytm_utils.py` |

### 7.2 Phase 2: Core Integration (Week 2)

| Task | Description | Files |
|------|-------------|-------|
| Sale API integration | Initiate payment requests | `paytm_edc_service.py` |
| Status polling | Background status checks | `paytm_edc_service.py` |
| Payment recording | Store transaction details | `billing_service.py` |
| Error handling | Comprehensive error management | All modules |

### 7.3 Phase 3: UI Integration (Week 3)

| Task | Description | Files |
|------|-------------|-------|
| Payment method UI | Add Paytm EDC option | `billing_create.html` |
| Status display | Real-time payment status | JavaScript/AJAX |
| Receipt printing | Include Paytm transaction details | Receipt template |
| Void/Cancel UI | Same-day transaction reversal | `billing_edit.html` |

### 7.4 Phase 4: Testing & Go-Live (Week 4)

| Task | Description |
|------|-------------|
| Staging testing | Test all scenarios with test credentials |
| Integration testing | End-to-end billing flow |
| Production setup | Switch to production credentials |
| Staff training | Train billing staff on new flow |
| Go-live | Deploy to production |

---

## 8. Database Schema

### 8.1 New Table: paytm_transactions

```sql
CREATE TABLE paytm_transactions (
    -- Primary Key
    paytm_transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign Keys
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),
    billing_invoice_id UUID REFERENCES billing_invoices(invoice_id),
    patient_id UUID REFERENCES patients(patient_id),
    
    -- Paytm Identifiers
    merchant_transaction_id VARCHAR(32) NOT NULL UNIQUE,
    paytm_mid VARCHAR(20) NOT NULL,
    paytm_tid VARCHAR(8),
    
    -- Transaction Details
    transaction_amount DECIMAL(12, 2) NOT NULL,
    transaction_amount_paise BIGINT NOT NULL,
    transaction_datetime TIMESTAMP NOT NULL,
    
    -- Paytm Response Data
    rrn VARCHAR(20),                    -- Retrieval Reference Number
    auth_code VARCHAR(10),              -- Authorization Code
    bank_transaction_id VARCHAR(50),    -- Bank's transaction ID
    paytm_transaction_id_ref VARCHAR(50), -- Paytm's transaction ID
    
    -- Payment Details
    payment_mode VARCHAR(20),           -- CREDIT_CARD, DEBIT_CARD, UPI, etc.
    card_type VARCHAR(20),              -- VISA, MASTERCARD, RUPAY, etc.
    masked_card_no VARCHAR(20),         -- XXXX-XXXX-XXXX-1234
    bank_name VARCHAR(50),
    gateway_name VARCHAR(50),
    
    -- Status Tracking
    request_status VARCHAR(20) NOT NULL DEFAULT 'INITIATED',
    transaction_status VARCHAR(20),      -- TXN_SUCCESS, TXN_FAILURE, PENDING
    result_code VARCHAR(10),
    result_message VARCHAR(200),
    
    -- Void/Refund
    is_voided BOOLEAN DEFAULT FALSE,
    void_transaction_id VARCHAR(32),
    void_datetime TIMESTAMP,
    void_reason VARCHAR(200),
    
    -- Metadata
    request_payload JSONB,              -- Full request sent
    response_payload JSONB,             -- Full response received
    status_check_count INTEGER DEFAULT 0,
    last_status_check TIMESTAMP,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(user_id),
    
    -- Indexes
    CONSTRAINT fk_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id),
    CONSTRAINT chk_amount_positive CHECK (transaction_amount > 0)
);

-- Indexes for common queries
CREATE INDEX idx_paytm_txn_hospital ON paytm_transactions(hospital_id);
CREATE INDEX idx_paytm_txn_invoice ON paytm_transactions(billing_invoice_id);
CREATE INDEX idx_paytm_txn_status ON paytm_transactions(transaction_status);
CREATE INDEX idx_paytm_txn_date ON paytm_transactions(transaction_datetime);
CREATE INDEX idx_paytm_txn_merchant_id ON paytm_transactions(merchant_transaction_id);
```

### 8.2 Extend payment_methods Table

```sql
-- Add Paytm EDC as payment method
INSERT INTO payment_methods (
    payment_method_id,
    method_name,
    method_code,
    is_active,
    requires_reference,
    reference_label
) VALUES (
    gen_random_uuid(),
    'Paytm EDC Card',
    'PAYTM_EDC',
    true,
    true,
    'RRN / Auth Code'
);
```

### 8.3 Extend billing_payments Table

```sql
-- Add column for Paytm transaction reference
ALTER TABLE billing_payments
ADD COLUMN paytm_transaction_id UUID REFERENCES paytm_transactions(paytm_transaction_id);
```

---

## 9. Service Module Design

### 9.1 Module Structure

```
app/
├── services/
│   ├── paytm_edc_service.py      # Main Paytm integration service
│   └── paytm_utils.py            # Checksum and utility functions
├── controllers/
│   └── paytm_controller.py       # API routes for Paytm operations
└── config/
    └── paytm_config.py           # Paytm credentials configuration
```

### 9.2 Service Class Design

```python
# paytm_edc_service.py - Service class outline

class PaytmEDCService:
    """
    Service class for Paytm EDC integration
    Follows SkinSpire HMS service architecture patterns
    """
    
    def __init__(self, hospital_id: UUID):
        self.hospital_id = hospital_id
        self.config = self._load_config()
    
    # ==================== Core Payment Methods ====================
    
    def initiate_payment(
        self,
        invoice_id: UUID,
        amount: Decimal,
        patient_name: str,
        invoice_number: str,
        terminal_id: str = None
    ) -> Dict:
        """
        Initiate payment request to Paytm EDC
        
        Args:
            invoice_id: Billing invoice UUID
            amount: Payment amount in rupees
            patient_name: Patient name for display
            invoice_number: Invoice reference number
            terminal_id: Specific TID (optional)
        
        Returns:
            Dict with transaction_id and status
        """
        pass
    
    def check_payment_status(
        self,
        merchant_transaction_id: str
    ) -> Dict:
        """
        Check status of a payment transaction
        
        Args:
            merchant_transaction_id: Unique transaction ID
        
        Returns:
            Dict with current status and transaction details
        """
        pass
    
    def poll_until_complete(
        self,
        merchant_transaction_id: str,
        max_attempts: int = 30,
        interval_seconds: int = 10
    ) -> Dict:
        """
        Poll payment status until final state
        
        Args:
            merchant_transaction_id: Unique transaction ID
            max_attempts: Maximum polling attempts
            interval_seconds: Delay between polls
        
        Returns:
            Dict with final status and transaction details
        """
        pass
    
    def void_transaction(
        self,
        original_transaction_id: str,
        reason: str
    ) -> Dict:
        """
        Void a same-day transaction
        
        Args:
            original_transaction_id: Original transaction to void
            reason: Reason for voiding
        
        Returns:
            Dict with void status
        """
        pass
    
    # ==================== Helper Methods ====================
    
    def _generate_transaction_id(self, invoice_number: str) -> str:
        """Generate unique merchant transaction ID"""
        pass
    
    def _amount_to_paise(self, amount: Decimal) -> int:
        """Convert rupees to paise"""
        pass
    
    def _build_sale_request(self, **kwargs) -> Dict:
        """Build Sale API request payload"""
        pass
    
    def _call_api(self, endpoint: str, payload: Dict) -> Dict:
        """Make API call to Paytm server"""
        pass
    
    # ==================== Database Methods ====================
    
    def _save_transaction(self, transaction_data: Dict) -> UUID:
        """Save transaction to database"""
        pass
    
    def _update_transaction_status(
        self,
        transaction_id: UUID,
        status_data: Dict
    ) -> bool:
        """Update transaction status in database"""
        pass
    
    def get_transaction_by_invoice(
        self,
        invoice_id: UUID
    ) -> Optional[Dict]:
        """Get Paytm transaction for an invoice"""
        pass
```

### 9.3 Configuration Structure

```python
# paytm_config.py

import os

class PaytmConfig:
    """Paytm EDC Configuration"""
    
    # Environment
    ENVIRONMENT = os.getenv('PAYTM_ENVIRONMENT', 'staging')  # staging or production
    
    # Credentials
    MERCHANT_ID = os.getenv('PAYTM_MERCHANT_ID')
    MERCHANT_KEY = os.getenv('PAYTM_MERCHANT_KEY')
    CHANNEL_ID = os.getenv('PAYTM_CHANNEL_ID', 'SKINSPIRE')
    
    # Terminal IDs (can be multiple for multiple devices)
    DEFAULT_TERMINAL_ID = os.getenv('PAYTM_DEFAULT_TID')
    
    # API URLs
    STAGING_BASE_URL = 'https://securegw-stage.paytm.in'
    PRODUCTION_BASE_URL = 'https://securegw-edc.paytm.in'
    
    @classmethod
    def get_base_url(cls):
        if cls.ENVIRONMENT == 'production':
            return cls.PRODUCTION_BASE_URL
        return cls.STAGING_BASE_URL
    
    # API Endpoints
    SALE_ENDPOINT = '/ecr/payment/request'
    STATUS_ENDPOINT = '/ecr/V2/payment/status'
    VOID_ENDPOINT = '/ecr/void/request'
    
    # Polling Configuration
    STATUS_POLL_INTERVAL = 10  # seconds
    STATUS_POLL_MAX_ATTEMPTS = 30  # ~5 minutes max wait
    
    # Transaction ID Prefix
    TXN_ID_PREFIX = 'SS'  # SkinSpire prefix
```

---

## 10. Error Handling

### 10.1 Error Categories

| Category | Examples | HMS Action |
|----------|----------|------------|
| **Network Errors** | Timeout, connection refused | Retry with backoff, show connectivity error |
| **Validation Errors** | Invalid params, duplicate ID | Show specific error, allow correction |
| **Terminal Errors** | Device offline, busy | Check device, retry |
| **Payment Errors** | Card declined, insufficient funds | Show failure reason, allow retry |
| **System Errors** | Paytm server error | Log, notify admin, allow retry |

### 10.2 Error Code Mapping

```python
PAYTM_ERROR_MESSAGES = {
    '0002': 'Invalid request parameters. Please try again.',
    '0007': 'EDC terminal is not active. Please check device.',
    '0012': 'Paytm system error. Please try again.',
    '0022': 'Merchant account blocked. Contact administrator.',
    '0029': 'Transaction not found.',
    '0233': 'Duplicate transaction. Please use a new invoice.',
    '0330': 'Security validation failed. Please retry.',
    '0333': 'Another payment is in progress. Please wait.',
    '0902': 'Merchant account suspended. Contact support.',
    '1809': 'Invalid payment amount.',
    '9001': 'Merchant configuration error. Contact support.',
}

def get_user_friendly_error(result_code: str, default_message: str) -> str:
    """Convert Paytm error code to user-friendly message"""
    return PAYTM_ERROR_MESSAGES.get(result_code, default_message)
```

### 10.3 Retry Strategy

```python
def execute_with_retry(api_call, max_retries=3, backoff_factor=2):
    """
    Execute API call with exponential backoff retry
    
    Args:
        api_call: Function to execute
        max_retries: Maximum retry attempts
        backoff_factor: Multiplier for delay between retries
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return api_call()
        
        except requests.exceptions.Timeout:
            last_exception = 'Connection timeout'
            delay = backoff_factor ** attempt
            time.sleep(delay)
        
        except requests.exceptions.ConnectionError:
            last_exception = 'Connection error'
            delay = backoff_factor ** attempt
            time.sleep(delay)
        
        except Exception as e:
            # Don't retry on other errors
            raise
    
    raise PaytmAPIError(f'API call failed after {max_retries} attempts: {last_exception}')
```

---

## 11. Testing Strategy

### 11.1 Test Credentials

| Parameter | Staging Value |
|-----------|---------------|
| Base URL | `https://securegw-stage.paytm.in` |
| MID | Obtain from Paytm Dashboard (Test Mode) |
| Merchant Key | Obtain from Paytm Dashboard |
| Test Card | Any valid Visa/Mastercard |
| Test UPI | Use Paytm test wallet app |

### 11.2 Test Scenarios

#### Happy Path Tests

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| Card Payment Success | Initiate → Accept on EDC → Insert card → PIN | TXN_SUCCESS |
| UPI Payment Success | Initiate → Accept → Scan QR → Approve in app | TXN_SUCCESS |
| Status Polling | Initiate → Poll status | Final status received |

#### Error Path Tests

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| Card Declined | Initiate → Use declined card | TXN_FAILURE with reason |
| Transaction Timeout | Initiate → Don't complete on EDC | PENDING → Timeout message |
| Duplicate Transaction | Send same transaction ID twice | Error: Duplicate Order |
| Device Offline | Initiate with offline EDC | Error: Terminal not active |
| Network Failure | Disconnect during API call | Retry mechanism triggered |

#### Edge Case Tests

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| Void Same-Day | Complete payment → Void | Void successful |
| Very Large Amount | ₹10,00,000 payment | Success (within limits) |
| Special Characters | Invoice with special chars | Sanitized, success |
| Concurrent Payments | Two payments same TID | Second queued/rejected |

### 11.3 Test Wallet App

For UPI testing, use Paytm's test wallet app:
- Download from: Paytm GitHub repository
- Test Mobile: 77777 77777
- Test Password: Paytm12345

---

## 12. Go-Live Checklist

### 12.1 Pre-Production Checklist

- [ ] **Credentials**
  - [ ] Production MID received and verified
  - [ ] Production Merchant Key secured
  - [ ] Production TID(s) allocated for all EDC devices
  - [ ] Channel ID confirmed with Paytm

- [ ] **Configuration**
  - [ ] Environment variables set for production
  - [ ] Base URL changed to production endpoint
  - [ ] SSL certificates valid
  - [ ] Firewall rules allow Paytm server IPs

- [ ] **Testing**
  - [ ] All test scenarios passed in staging
  - [ ] Integration testing completed
  - [ ] UAT sign-off received
  - [ ] Load testing completed (if high volume expected)

- [ ] **Database**
  - [ ] Production database schema updated
  - [ ] Indexes created
  - [ ] Backup procedures in place

- [ ] **Monitoring**
  - [ ] Logging configured for production
  - [ ] Error alerting set up
  - [ ] Transaction monitoring dashboard ready

### 12.2 Go-Live Day Checklist

- [ ] **Deployment**
  - [ ] Code deployed to production
  - [ ] Configuration verified
  - [ ] Health checks passing

- [ ] **Verification**
  - [ ] Small test transaction successful
  - [ ] Status polling working
  - [ ] Receipt printing correct
  - [ ] Database records created

- [ ] **Staff Readiness**
  - [ ] Billing staff trained
  - [ ] Quick reference guide provided
  - [ ] Support contact shared

- [ ] **Rollback Plan**
  - [ ] Previous version ready for rollback
  - [ ] Rollback procedure documented
  - [ ] Team on standby

### 12.3 Post Go-Live Monitoring

| Metric | Threshold | Action if Breached |
|--------|-----------|-------------------|
| Success Rate | > 95% | Investigate failures |
| Response Time | < 30 seconds | Check network/Paytm status |
| Timeout Rate | < 2% | Adjust polling intervals |
| Void Rate | < 5% | Review with billing team |

---

## Appendix A: Checksum Generation

### A.1 Algorithm

Paytm uses HMAC-SHA256 for request signing:

```python
import hashlib
import hmac
import base64
import json

def generate_checksum(body: dict, merchant_key: str) -> str:
    """
    Generate Paytm checksum for request body
    
    Args:
        body: Request body dictionary
        merchant_key: Merchant secret key
    
    Returns:
        Base64 encoded checksum string
    """
    # Convert body to JSON string (sorted keys for consistency)
    body_string = json.dumps(body, separators=(',', ':'), sort_keys=True)
    
    # Generate HMAC-SHA256
    signature = hmac.new(
        merchant_key.encode('utf-8'),
        body_string.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Base64 encode
    checksum = base64.b64encode(signature).decode('utf-8')
    
    return checksum
```

### A.2 Checksum Library

Paytm provides official checksum libraries:
- Python: Available from Paytm integration team
- Node.js: npm package available
- Java: Maven artifact available

Request from: integrations@paytm.com

---

## Appendix B: Sample Code Snippets

### B.1 Complete Sale Request Example

```python
import requests
import json
from datetime import datetime
from decimal import Decimal

def initiate_paytm_payment(
    invoice_id: str,
    amount: Decimal,
    patient_name: str,
    invoice_number: str
) -> dict:
    """
    Initiate payment request to Paytm EDC
    """
    # Configuration
    base_url = 'https://securegw-stage.paytm.in'  # Change for production
    mid = 'YOUR_MERCHANT_ID'
    merchant_key = 'YOUR_MERCHANT_KEY'
    tid = 'YOUR_TERMINAL_ID'
    channel_id = 'YOUR_CHANNEL_ID'
    
    # Generate unique transaction ID
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    merchant_txn_id = f'SS{timestamp}{invoice_id[:8]}'
    
    # Convert amount to paise
    amount_paise = int(amount * 100)
    
    # Current timestamp
    txn_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Build request body
    body = {
        'paytmMid': mid,
        'paytmTid': tid,
        'transactionDateTime': txn_datetime,
        'merchantTransactionId': merchant_txn_id,
        'merchantReferenceNo': invoice_number,
        'transactionAmount': str(amount_paise),
        'merchantExtendedInfo': {
            'PaymentMode': 'All'
        },
        'displayInfo': {
            'Patient': patient_name,
            'Invoice': invoice_number
        },
        'printInfo': {
            'InvoiceNo': invoice_number,
            'PatientName': patient_name
        }
    }
    
    # Generate checksum
    checksum = generate_checksum(body, merchant_key)
    
    # Build full request
    request_payload = {
        'head': {
            'requestTimeStamp': txn_datetime,
            'channelId': channel_id,
            'checksum': checksum,
            'version': '3.1'
        },
        'body': body
    }
    
    # Make API call
    response = requests.post(
        f'{base_url}/ecr/payment/request',
        json=request_payload,
        headers={'Content-Type': 'application/json'},
        timeout=30
    )
    
    response_data = response.json()
    
    return {
        'merchant_transaction_id': merchant_txn_id,
        'request': request_payload,
        'response': response_data,
        'success': response_data.get('body', {}).get('resultInfo', {}).get('resultStatus') == 'ACCEPTED_SUCCESS'
    }
```

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **EDC** | Electronic Data Capture - Card swipe machine |
| **MID** | Merchant Identifier - Unique ID for your business |
| **TID** | Terminal Identifier - Unique ID for each EDC device |
| **RRN** | Retrieval Reference Number - Bank's transaction reference |
| **Auth Code** | Authorization Code - Approval code from card issuer |
| **Checksum** | Digital signature for request validation |
| **Void** | Cancel a same-day transaction |
| **Refund** | Return money for previous day transactions |
| **CPay** | Customer Payment ID - Used in queue-based flow |

---

## Appendix D: Support Contacts

| Contact | Details |
|---------|---------|
| **Paytm Integration Support** | integrations@paytm.com |
| **Paytm Business Support** | 1800-1800-1234 |
| **Paytm Developer Portal** | https://business.paytm.com/docs |
| **Paytm Dashboard** | https://dashboard.paytm.com |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Nov 2025 | SkinSpire Dev Team | Initial version |

---

*End of Document*