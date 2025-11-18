# Payment Gateway Integration - Part 2: Database Design

**Part:** 2 of 5
**Focus:** Database Schema, Tables, Views, Migrations, Models
**Audience:** Database administrators, backend developers

---

## Table of Contents

1. [Database Overview](#1-database-overview)
2. [Existing Gateway Fields](#2-existing-gateway-fields)
3. [New Tables](#3-new-tables)
4. [View Updates](#4-view-updates)
5. [Model Definitions](#5-model-definitions)
6. [Migration Scripts](#6-migration-scripts)
7. [Indexes and Constraints](#7-indexes-and-constraints)

---

## 1. Database Overview

### 1.1 Schema Changes Summary

**Existing Tables Modified:** 0
- No changes to existing tables (gateway fields already present in `supplier_payment`)

**New Tables Created:** 5
1. `gateway_configuration` - Gateway provider settings and credentials
2. `gateway_transaction_log` - All gateway API call logs
3. `gateway_webhook` - Incoming webhook records
4. `gateway_reconciliation` - Daily reconciliation run summary
5. `gateway_reconciliation_detail` - Transaction-level matching details

**Views Updated:** 1
- `supplier_payment_view` - Add gateway-specific columns

**Models Updated:** 2
- `Supplier` - Add gateway contact/fund account IDs
- Existing gateway fields in `SupplierPayment` will be utilized (no model changes needed)

### 1.2 Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Payment Creation                                              │
│  ┌────────────────┐                                          │
│  │ supplier_payment│                                          │
│  │ (gateway fields)│                                          │
│  └────────┬───────┘                                          │
│           │                                                   │
│           │ Uses credentials from                             │
│           ▼                                                   │
│  ┌────────────────────┐                                      │
│  │ gateway_configuration│                                      │
│  └────────┬───────────┘                                      │
│           │                                                   │
│           │ Logs API call to                                  │
│           ▼                                                   │
│  ┌──────────────────────┐                                    │
│  │gateway_transaction_log│                                    │
│  └──────────────────────┘                                    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Webhook Receipt                                               │
│  ┌────────────────┐                                          │
│  │ gateway_webhook │                                          │
│  └────────┬───────┘                                          │
│           │                                                   │
│           │ Updates                                           │
│           ▼                                                   │
│  ┌────────────────┐                                          │
│  │ supplier_payment│                                          │
│  │ (status, UTR)  │                                          │
│  └────────────────┘                                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Reconciliation                                                │
│  ┌────────────────────────┐                                  │
│  │gateway_reconciliation  │                                  │
│  └────────┬───────────────┘                                  │
│           │                                                   │
│           │ Contains details                                  │
│           ▼                                                   │
│  ┌──────────────────────────────┐                            │
│  │gateway_reconciliation_detail │                            │
│  │ (matching results)           │                            │
│  └──────────┬───────────────────┘                            │
│             │                                                 │
│             │ Links to                                        │
│             ▼                                                 │
│  ┌────────────────┐                                          │
│  │ supplier_payment│                                          │
│  └────────────────┘                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Existing Gateway Fields

### 2.1 SupplierPayment Model (NO CHANGES NEEDED)

The `supplier_payment` table already contains all necessary gateway fields:

**Location:** `app/models/transaction.py` lines 991-1118

```python
# Categorization
payment_category = Column(String(20), default='manual')
# Values: 'manual', 'gateway', 'upi', 'bank_transfer'

payment_source = Column(String(30), default='internal')
# Values: 'internal', 'razorpay', 'paytm', 'upi', 'bank_api'

# Gateway tracking
gateway_payment_id = Column(String(100))        # pout_xxx, ORDER_xxx
gateway_order_id = Column(String(100))          # For payment links
gateway_transaction_id = Column(String(100))    # UTR number
gateway_response_code = Column(String(10))      # HTTP status/error code
gateway_response_message = Column(String(255))  # Success/error message
gateway_fee = Column(Numeric(12, 2), default=0) # Gateway charges
gateway_tax = Column(Numeric(12, 2), default=0) # GST on charges
gateway_initiated_at = Column(DateTime(timezone=True))
gateway_completed_at = Column(DateTime(timezone=True))
gateway_failed_at = Column(DateTime(timezone=True))
gateway_metadata = Column(JSONB)                # Full response

# Payment link
payment_link_id = Column(String(100))
payment_link_url = Column(String(500))
payment_link_expires_at = Column(DateTime(timezone=True))
payment_link_status = Column(String(20))        # created, sent, expired, paid
```

**✅ No Migration Needed** - These fields are already in production.

### 2.2 Supplier Model (Minor Addition)

**Location:** `app/models/master.py`

Add gateway contact/fund account caching:

```python
class Supplier(db.Model, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = 'supplier'

    # ... existing fields ...

    # NEW: Gateway integration fields
    razorpay_contact_id = Column(String(50))       # cont_xxx
    razorpay_fund_account_id = Column(String(50))  # fa_xxx
    paytm_beneficiary_id = Column(String(50))      # Paytm beneficiary ID

    # Stores which gateway provider is preferred for this supplier
    preferred_gateway = Column(String(20))  # 'razorpay', 'paytm', null (use default)
```

**Migration Required:** Add these 4 columns to `supplier` table.

---

## 3. New Tables

### 3.1 Gateway Configuration Table

**Purpose:** Store gateway provider settings, credentials, and preferences per hospital/branch.

```sql
-- Migration: migrations/create_gateway_configuration.sql

CREATE TABLE gateway_configuration (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id VARCHAR(36) NOT NULL REFERENCES hospital(hospital_id),
    branch_id VARCHAR(36) REFERENCES branch(branch_id),  -- NULL = hospital-wide

    -- Gateway selection
    gateway_provider VARCHAR(20) NOT NULL,  -- 'razorpay', 'paytm'
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,       -- Default gateway for hospital/branch

    -- Credentials (encrypted using EncryptionService)
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    merchant_id VARCHAR(100),               -- Paytm specific
    webhook_secret TEXT,                    -- For signature verification

    -- Settings
    mode VARCHAR(10) DEFAULT 'test',        -- 'test' or 'live'
    auto_approve_gateway_payments BOOLEAN DEFAULT false,
    max_payout_amount NUMERIC(12,2) DEFAULT 100000.00,
    min_payout_amount NUMERIC(12,2) DEFAULT 1.00,

    -- Capabilities (what this gateway config supports)
    supports_payouts BOOLEAN DEFAULT true,
    supports_payment_links BOOLEAN DEFAULT true,
    supports_upi BOOLEAN DEFAULT true,
    supports_bank_transfer BOOLEAN DEFAULT true,
    supports_refunds BOOLEAN DEFAULT false,

    -- Fee configuration
    upi_fee_fixed NUMERIC(10,2) DEFAULT 0,
    upi_fee_percentage NUMERIC(5,2) DEFAULT 0,
    bank_transfer_fee_fixed NUMERIC(10,2) DEFAULT 0,
    bank_transfer_fee_percentage NUMERIC(5,2) DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,
    updated_by VARCHAR(15),
    notes TEXT,

    CONSTRAINT unique_gateway_per_branch UNIQUE(hospital_id, branch_id, gateway_provider),
    CONSTRAINT valid_mode CHECK (mode IN ('test', 'live')),
    CONSTRAINT valid_provider CHECK (gateway_provider IN ('razorpay', 'paytm'))
);

-- Indexes
CREATE INDEX idx_gateway_config_hospital ON gateway_configuration(hospital_id);
CREATE INDEX idx_gateway_config_branch ON gateway_configuration(branch_id);
CREATE INDEX idx_gateway_config_active ON gateway_configuration(is_active, is_default);
CREATE INDEX idx_gateway_config_provider ON gateway_configuration(gateway_provider);

-- Comments
COMMENT ON TABLE gateway_configuration IS 'Payment gateway provider configurations per hospital/branch';
COMMENT ON COLUMN gateway_configuration.api_key_encrypted IS 'Encrypted API key using EncryptionService';
COMMENT ON COLUMN gateway_configuration.mode IS 'test mode for sandbox, live for production';
```

### 3.2 Gateway Transaction Log Table

**Purpose:** Log all API interactions with payment gateways for debugging and audit.

```sql
-- Migration: migrations/create_gateway_transaction_log.sql

CREATE TABLE gateway_transaction_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id VARCHAR(36) REFERENCES supplier_payment(payment_id),
    hospital_id VARCHAR(36) NOT NULL REFERENCES hospital(hospital_id),

    -- Gateway information
    gateway_provider VARCHAR(20) NOT NULL,
    gateway_operation VARCHAR(30) NOT NULL,
    -- Operations: 'create_payout', 'create_payment_link', 'get_status',
    --             'create_refund', 'fetch_settlement'

    gateway_request_id VARCHAR(100),  -- Idempotency key

    -- Request details
    request_url VARCHAR(500),
    request_method VARCHAR(10),  -- POST, GET, etc.
    request_payload JSONB,
    request_headers JSONB,

    -- Response details
    response_payload JSONB,
    response_status_code INTEGER,
    response_time_ms INTEGER,  -- Response time in milliseconds

    -- Tracking
    initiated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    success BOOLEAN,
    error_message TEXT,
    error_code VARCHAR(50),

    -- Context
    user_id VARCHAR(15),
    ip_address INET,
    user_agent TEXT,

    CONSTRAINT fk_gateway_log_payment FOREIGN KEY (payment_id)
        REFERENCES supplier_payment(payment_id) ON DELETE SET NULL,
    CONSTRAINT valid_operation CHECK (gateway_operation IN (
        'create_payout', 'create_payment_link', 'get_status',
        'create_refund', 'fetch_settlement', 'verify_account'
    ))
);

-- Indexes
CREATE INDEX idx_gateway_log_payment ON gateway_transaction_log(payment_id);
CREATE INDEX idx_gateway_log_provider_op ON gateway_transaction_log(gateway_provider, gateway_operation);
CREATE INDEX idx_gateway_log_date ON gateway_transaction_log(initiated_at DESC);
CREATE INDEX idx_gateway_log_success ON gateway_transaction_log(success, gateway_provider);
CREATE INDEX idx_gateway_log_hospital ON gateway_transaction_log(hospital_id);

-- Partitioning (Optional - for high volume)
-- Partition by initiated_at monthly for better performance

COMMENT ON TABLE gateway_transaction_log IS 'Audit log of all gateway API interactions';
COMMENT ON COLUMN gateway_transaction_log.response_time_ms IS 'API response time for performance monitoring';
```

### 3.3 Gateway Webhook Table

**Purpose:** Store incoming webhooks from payment gateways for processing.

```sql
-- Migration: migrations/create_gateway_webhook.sql

CREATE TABLE gateway_webhook (
    webhook_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Gateway information
    gateway_provider VARCHAR(20) NOT NULL,
    gateway_event_type VARCHAR(50) NOT NULL,
    -- Razorpay: 'payout.processed', 'payout.failed', 'payment_link.paid', etc.
    -- Paytm: 'PAYMENT_SUCCESS', 'PAYMENT_FAILED', etc.

    gateway_event_id VARCHAR(100),  -- Gateway's event ID
    gateway_entity_id VARCHAR(100), -- Payout ID or payment ID

    -- Payload
    raw_payload JSONB NOT NULL,
    signature VARCHAR(500),
    signature_verified BOOLEAN DEFAULT false,

    -- HTTP context
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    source_ip INET,
    headers JSONB,

    -- Processing
    processing_status VARCHAR(20) DEFAULT 'pending',
    -- Values: 'pending', 'processing', 'processed', 'failed', 'ignored'

    processed_at TIMESTAMP WITH TIME ZONE,
    processing_error TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP WITH TIME ZONE,

    -- Linked entities
    payment_id VARCHAR(36),  -- Matched payment record

    CONSTRAINT fk_webhook_payment FOREIGN KEY (payment_id)
        REFERENCES supplier_payment(payment_id) ON DELETE SET NULL,
    CONSTRAINT valid_processing_status CHECK (processing_status IN (
        'pending', 'processing', 'processed', 'failed', 'ignored'
    ))
);

-- Indexes
CREATE INDEX idx_webhook_processing ON gateway_webhook(processing_status, received_at);
CREATE INDEX idx_webhook_payment ON gateway_webhook(payment_id);
CREATE INDEX idx_webhook_event ON gateway_webhook(gateway_provider, gateway_event_type);
CREATE INDEX idx_webhook_entity ON gateway_webhook(gateway_entity_id);
CREATE INDEX idx_webhook_retry ON gateway_webhook(retry_count, processing_status)
    WHERE processing_status = 'failed';

COMMENT ON TABLE gateway_webhook IS 'Incoming webhook events from payment gateways';
COMMENT ON COLUMN gateway_webhook.signature_verified IS 'HMAC signature verification result';
COMMENT ON COLUMN gateway_webhook.retry_count IS 'Number of processing retry attempts';
```

### 3.4 Gateway Reconciliation Table

**Purpose:** Store daily reconciliation run summaries.

```sql
-- Migration: migrations/create_gateway_reconciliation.sql

CREATE TABLE gateway_reconciliation (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id VARCHAR(36) NOT NULL REFERENCES hospital(hospital_id),

    -- Reconciliation scope
    gateway_provider VARCHAR(20) NOT NULL,
    reconciliation_date DATE NOT NULL,  -- Date being reconciled
    settlement_date DATE NOT NULL,      -- Gateway settlement date

    -- Summary amounts
    gateway_settlement_amount NUMERIC(12,2),
    system_payment_amount NUMERIC(12,2),
    gateway_fee_total NUMERIC(12,2),
    gateway_tax_total NUMERIC(12,2),
    net_settlement_amount NUMERIC(12,2),
    difference_amount NUMERIC(12,2),

    -- Matching statistics
    matched_count INTEGER DEFAULT 0,
    unmatched_gateway_count INTEGER DEFAULT 0,  -- In gateway but not in system
    unmatched_system_count INTEGER DEFAULT 0,   -- In system but not in gateway
    discrepancy_count INTEGER DEFAULT 0,         -- Amount/data mismatches

    total_transactions_gateway INTEGER DEFAULT 0,
    total_transactions_system INTEGER DEFAULT 0,

    -- Status
    reconciliation_status VARCHAR(20) DEFAULT 'in_progress',
    -- Values: 'in_progress', 'completed', 'needs_review', 'reviewed'

    reconciled_by VARCHAR(15),
    reconciled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(15),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Output
    reconciliation_report_url TEXT,
    reconciliation_report_data JSONB,
    notes TEXT,

    CONSTRAINT unique_recon_date_provider UNIQUE(hospital_id, gateway_provider, reconciliation_date),
    CONSTRAINT valid_recon_status CHECK (reconciliation_status IN (
        'in_progress', 'completed', 'needs_review', 'reviewed'
    ))
);

-- Indexes
CREATE INDEX idx_recon_hospital_date ON gateway_reconciliation(hospital_id, reconciliation_date DESC);
CREATE INDEX idx_recon_status ON gateway_reconciliation(reconciliation_status);
CREATE INDEX idx_recon_provider ON gateway_reconciliation(gateway_provider, settlement_date);
CREATE INDEX idx_recon_discrepancy ON gateway_reconciliation(discrepancy_count)
    WHERE discrepancy_count > 0;

COMMENT ON TABLE gateway_reconciliation IS 'Daily reconciliation run summaries';
COMMENT ON COLUMN gateway_reconciliation.difference_amount IS 'System amount - Gateway amount';
```

### 3.5 Gateway Reconciliation Detail Table

**Purpose:** Transaction-level matching details for each reconciliation run.

```sql
-- Migration: migrations/create_gateway_reconciliation_detail.sql

CREATE TABLE gateway_reconciliation_detail (
    detail_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID NOT NULL REFERENCES gateway_reconciliation(reconciliation_id) ON DELETE CASCADE,

    -- Payment information
    payment_id VARCHAR(36) REFERENCES supplier_payment(payment_id),
    gateway_transaction_id VARCHAR(100),
    gateway_payout_id VARCHAR(100),

    -- Matching status
    match_status VARCHAR(30) NOT NULL,
    -- Values: 'matched', 'unmatched_gateway', 'unmatched_system',
    --         'amount_mismatch', 'date_mismatch', 'status_mismatch'

    -- Amounts
    system_amount NUMERIC(12,2),
    gateway_amount NUMERIC(12,2),
    difference_amount NUMERIC(12,2),

    -- Gateway details
    gateway_settlement_id VARCHAR(100),
    gateway_utr VARCHAR(50),         -- Unique Transaction Reference
    gateway_status VARCHAR(30),
    gateway_settled_at TIMESTAMP WITH TIME ZONE,

    -- System details
    system_status VARCHAR(30),
    system_completed_at TIMESTAMP WITH TIME ZONE,

    -- Discrepancy
    discrepancy_reason TEXT,
    discrepancy_type VARCHAR(30),
    -- Types: 'amount', 'status', 'date', 'missing_gateway', 'missing_system', 'fee'

    -- Resolution
    resolved BOOLEAN DEFAULT false,
    resolved_by VARCHAR(15),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    resolution_action VARCHAR(50),
    -- Actions: 'manual_entry', 'gateway_update', 'amount_adjustment',
    --          'ignore', 'refund_initiated'

    CONSTRAINT fk_recon_detail_reconciliation FOREIGN KEY (reconciliation_id)
        REFERENCES gateway_reconciliation(reconciliation_id) ON DELETE CASCADE,
    CONSTRAINT fk_recon_detail_payment FOREIGN KEY (payment_id)
        REFERENCES supplier_payment(payment_id) ON DELETE SET NULL,
    CONSTRAINT valid_match_status CHECK (match_status IN (
        'matched', 'unmatched_gateway', 'unmatched_system',
        'amount_mismatch', 'date_mismatch', 'status_mismatch'
    ))
);

-- Indexes
CREATE INDEX idx_recon_detail_reconciliation ON gateway_reconciliation_detail(reconciliation_id);
CREATE INDEX idx_recon_detail_payment ON gateway_reconciliation_detail(payment_id);
CREATE INDEX idx_recon_detail_match_status ON gateway_reconciliation_detail(match_status, resolved);
CREATE INDEX idx_recon_detail_gateway_txn ON gateway_reconciliation_detail(gateway_transaction_id);
CREATE INDEX idx_recon_detail_unresolved ON gateway_reconciliation_detail(resolved, match_status)
    WHERE resolved = false;

COMMENT ON TABLE gateway_reconciliation_detail IS 'Transaction-level reconciliation matching details';
COMMENT ON COLUMN gateway_reconciliation_detail.difference_amount IS 'System amount - Gateway amount';
```

---

## 4. View Updates

### 4.1 Supplier Payment View (Enhanced)

**Location:** `app/database/view scripts/supplier_payment_view_v3.0.sql`

Add gateway-specific computed columns:

```sql
-- Migration: migrations/update_supplier_payment_view_v3.sql

CREATE OR REPLACE VIEW supplier_payment_view AS
SELECT
    sp.*,

    -- Supplier information
    s.supplier_name,
    s.supplier_code,
    s.supplier_gstin,
    s.phone AS supplier_phone,
    s.email AS supplier_email,

    -- Invoice information
    si.invoice_number,
    si.invoice_date,
    si.invoice_amount,
    si.outstanding_amount AS invoice_outstanding_amount,

    -- Branch information
    b.branch_name,
    b.branch_code,

    -- Gateway computed fields
    CASE
        WHEN sp.payment_category = 'gateway' THEN sp.payment_source
        ELSE 'manual'
    END as payment_type_display,

    CASE
        WHEN sp.payment_link_id IS NOT NULL THEN 'Payment Link'
        WHEN sp.gateway_payment_id IS NOT NULL THEN 'Gateway Payout'
        ELSE 'Manual Entry'
    END as payment_mode_display,

    -- Effective status considering gateway status
    CASE
        WHEN sp.gateway_failed_at IS NOT NULL THEN 'gateway_failed'
        WHEN sp.gateway_completed_at IS NOT NULL AND sp.gl_posted THEN 'completed'
        WHEN sp.gateway_completed_at IS NOT NULL AND NOT sp.gl_posted THEN 'gateway_success_pending_gl'
        WHEN sp.gateway_initiated_at IS NOT NULL THEN 'gateway_pending'
        WHEN sp.payment_link_id IS NOT NULL AND sp.payment_link_status = 'expired' THEN 'link_expired'
        WHEN sp.payment_link_id IS NOT NULL AND sp.payment_link_status = 'paid' THEN 'link_paid'
        WHEN sp.payment_link_id IS NOT NULL THEN 'link_created'
        ELSE sp.workflow_status
    END as effective_status,

    -- Gateway provider display
    CASE
        WHEN sp.payment_source = 'razorpay' THEN 'Razorpay'
        WHEN sp.payment_source = 'paytm' THEN 'Paytm'
        WHEN sp.payment_source = 'internal' THEN 'Internal'
        ELSE 'Other'
    END as gateway_provider_display,

    -- Net amount after gateway fees
    (sp.amount - COALESCE(sp.gateway_fee, 0) - COALESCE(sp.gateway_tax, 0)) as net_amount_to_supplier,

    -- Total gateway charges
    (COALESCE(sp.gateway_fee, 0) + COALESCE(sp.gateway_tax, 0)) as total_gateway_charges,

    -- Days since gateway initiation (for monitoring)
    CASE
        WHEN sp.gateway_initiated_at IS NOT NULL AND sp.gateway_completed_at IS NULL
        THEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - sp.gateway_initiated_at))
        ELSE NULL
    END as days_since_gateway_initiated,

    -- Payment link status indicator
    CASE
        WHEN sp.payment_link_id IS NOT NULL AND sp.payment_link_expires_at < CURRENT_TIMESTAMP
        THEN true
        ELSE false
    END as payment_link_expired,

    -- User information
    cu.full_name as created_by_name,
    uu.full_name as updated_by_name,
    au.full_name as approved_by_name

FROM supplier_payment sp
LEFT JOIN supplier s ON sp.supplier_id = s.supplier_id
LEFT JOIN supplier_invoice si ON sp.invoice_id = si.invoice_id
LEFT JOIN branch b ON sp.branch_id = b.branch_id
LEFT JOIN users cu ON sp.created_by = cu.user_id
LEFT JOIN users uu ON sp.updated_by = uu.user_id
LEFT JOIN users au ON sp.approved_by = au.approved_by
WHERE sp.is_deleted = false;

-- Grant permissions
GRANT SELECT ON supplier_payment_view TO app_user;

COMMENT ON VIEW supplier_payment_view IS 'Enhanced supplier payment view with gateway-specific columns v3.0';
```

---

## 5. Model Definitions

### 5.1 Gateway Configuration Model

**Location:** `app/models/config.py`

```python
from sqlalchemy import Column, String, Boolean, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import db
from app.models.base import TimestampMixin
import uuid

class GatewayConfiguration(db.Model, TimestampMixin):
    """
    Payment gateway configuration per hospital/branch.
    Stores encrypted API credentials and gateway settings.
    """
    __tablename__ = 'gateway_configuration'

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(String(36), ForeignKey('hospital.hospital_id'), nullable=False)
    branch_id = Column(String(36), ForeignKey('branch.branch_id'), nullable=True)

    # Gateway selection
    gateway_provider = Column(String(20), nullable=False)  # 'razorpay', 'paytm'
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Encrypted credentials
    api_key_encrypted = Column(Text, nullable=False)
    api_secret_encrypted = Column(Text, nullable=False)
    merchant_id = Column(String(100), nullable=True)
    webhook_secret = Column(Text, nullable=True)

    # Settings
    mode = Column(String(10), default='test')  # 'test' or 'live'
    auto_approve_gateway_payments = Column(Boolean, default=False)
    max_payout_amount = Column(Numeric(12, 2), default=100000.00)
    min_payout_amount = Column(Numeric(12, 2), default=1.00)

    # Capabilities
    supports_payouts = Column(Boolean, default=True)
    supports_payment_links = Column(Boolean, default=True)
    supports_upi = Column(Boolean, default=True)
    supports_bank_transfer = Column(Boolean, default=True)
    supports_refunds = Column(Boolean, default=False)

    # Fee configuration
    upi_fee_fixed = Column(Numeric(10, 2), default=0)
    upi_fee_percentage = Column(Numeric(5, 2), default=0)
    bank_transfer_fee_fixed = Column(Numeric(10, 2), default=0)
    bank_transfer_fee_percentage = Column(Numeric(5, 2), default=0)

    # Metadata
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<GatewayConfiguration {self.gateway_provider} - {self.mode} - Hospital: {self.hospital_id}>"

    def to_dict(self):
        """Convert to dictionary (excludes encrypted credentials)"""
        return {
            'config_id': str(self.config_id),
            'hospital_id': self.hospital_id,
            'branch_id': self.branch_id,
            'gateway_provider': self.gateway_provider,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'mode': self.mode,
            'supports_payouts': self.supports_payouts,
            'supports_payment_links': self.supports_payment_links,
            'supports_upi': self.supports_upi,
            'supports_bank_transfer': self.supports_bank_transfer,
            'supports_refunds': self.supports_refunds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
```

### 5.2 Gateway Transaction Log Model

**Location:** `app/models/transaction.py` (add to existing file)

```python
class GatewayTransactionLog(db.Model):
    """Audit log of all gateway API interactions"""
    __tablename__ = 'gateway_transaction_log'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String(36), ForeignKey('supplier_payment.payment_id'), nullable=True)
    hospital_id = Column(String(36), ForeignKey('hospital.hospital_id'), nullable=False)

    # Gateway information
    gateway_provider = Column(String(20), nullable=False)
    gateway_operation = Column(String(30), nullable=False)
    gateway_request_id = Column(String(100), nullable=True)

    # Request details
    request_url = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_payload = Column(JSONB, nullable=True)
    request_headers = Column(JSONB, nullable=True)

    # Response details
    response_payload = Column(JSONB, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Tracking
    initiated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Context
    user_id = Column(String(15), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)

    def __repr__(self):
        return f"<GatewayTransactionLog {self.gateway_provider} - {self.gateway_operation}>"
```

### 5.3 Gateway Webhook Model

**Location:** `app/models/transaction.py`

```python
class GatewayWebhook(db.Model):
    """Incoming webhook events from payment gateways"""
    __tablename__ = 'gateway_webhook'

    webhook_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Gateway information
    gateway_provider = Column(String(20), nullable=False)
    gateway_event_type = Column(String(50), nullable=False)
    gateway_event_id = Column(String(100), nullable=True)
    gateway_entity_id = Column(String(100), nullable=True)

    # Payload
    raw_payload = Column(JSONB, nullable=False)
    signature = Column(String(500), nullable=True)
    signature_verified = Column(Boolean, default=False)

    # HTTP context
    received_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    source_ip = Column(String(50), nullable=True)
    headers = Column(JSONB, nullable=True)

    # Processing
    processing_status = Column(String(20), default='pending')
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Linked entities
    payment_id = Column(String(36), ForeignKey('supplier_payment.payment_id'), nullable=True)

    def __repr__(self):
        return f"<GatewayWebhook {self.gateway_provider} - {self.gateway_event_type}>"
```

### 5.4 Reconciliation Models

**Location:** `app/models/transaction.py`

```python
class GatewayReconciliation(db.Model):
    """Daily reconciliation run summaries"""
    __tablename__ = 'gateway_reconciliation'

    reconciliation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(String(36), ForeignKey('hospital.hospital_id'), nullable=False)

    # Scope
    gateway_provider = Column(String(20), nullable=False)
    reconciliation_date = Column(Date, nullable=False)
    settlement_date = Column(Date, nullable=False)

    # Summary amounts
    gateway_settlement_amount = Column(Numeric(12, 2), nullable=True)
    system_payment_amount = Column(Numeric(12, 2), nullable=True)
    gateway_fee_total = Column(Numeric(12, 2), nullable=True)
    gateway_tax_total = Column(Numeric(12, 2), nullable=True)
    net_settlement_amount = Column(Numeric(12, 2), nullable=True)
    difference_amount = Column(Numeric(12, 2), nullable=True)

    # Statistics
    matched_count = Column(Integer, default=0)
    unmatched_gateway_count = Column(Integer, default=0)
    unmatched_system_count = Column(Integer, default=0)
    discrepancy_count = Column(Integer, default=0)
    total_transactions_gateway = Column(Integer, default=0)
    total_transactions_system = Column(Integer, default=0)

    # Status
    reconciliation_status = Column(String(20), default='in_progress')
    reconciled_by = Column(String(15), nullable=True)
    reconciled_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    reviewed_by = Column(String(15), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Output
    reconciliation_report_url = Column(Text, nullable=True)
    reconciliation_report_data = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationship
    details = db.relationship('GatewayReconciliationDetail', back_populates='reconciliation', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<GatewayReconciliation {self.gateway_provider} - {self.reconciliation_date}>"


class GatewayReconciliationDetail(db.Model):
    """Transaction-level reconciliation matching details"""
    __tablename__ = 'gateway_reconciliation_detail'

    detail_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(UUID(as_uuid=True), ForeignKey('gateway_reconciliation.reconciliation_id', ondelete='CASCADE'), nullable=False)

    # Payment information
    payment_id = Column(String(36), ForeignKey('supplier_payment.payment_id'), nullable=True)
    gateway_transaction_id = Column(String(100), nullable=True)
    gateway_payout_id = Column(String(100), nullable=True)

    # Matching status
    match_status = Column(String(30), nullable=False)

    # Amounts
    system_amount = Column(Numeric(12, 2), nullable=True)
    gateway_amount = Column(Numeric(12, 2), nullable=True)
    difference_amount = Column(Numeric(12, 2), nullable=True)

    # Gateway details
    gateway_settlement_id = Column(String(100), nullable=True)
    gateway_utr = Column(String(50), nullable=True)
    gateway_status = Column(String(30), nullable=True)
    gateway_settled_at = Column(DateTime(timezone=True), nullable=True)

    # System details
    system_status = Column(String(30), nullable=True)
    system_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Discrepancy
    discrepancy_reason = Column(Text, nullable=True)
    discrepancy_type = Column(String(30), nullable=True)

    # Resolution
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String(15), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolution_action = Column(String(50), nullable=True)

    # Relationship
    reconciliation = db.relationship('GatewayReconciliation', back_populates='details')

    def __repr__(self):
        return f"<GatewayReconciliationDetail {self.match_status} - Payment: {self.payment_id}>"
```

---

## 6. Migration Scripts

### 6.1 Complete Migration Execution Order

```bash
# Execute in this order:

# 1. Add columns to supplier table
psql -d skinspire_db -f migrations/alter_supplier_add_gateway_fields.sql

# 2. Create gateway configuration table
psql -d skinspire_db -f migrations/create_gateway_configuration.sql

# 3. Create gateway transaction log table
psql -d skinspire_db -f migrations/create_gateway_transaction_log.sql

# 4. Create gateway webhook table
psql -d skinspire_db -f migrations/create_gateway_webhook.sql

# 5. Create gateway reconciliation tables
psql -d skinspire_db -f migrations/create_gateway_reconciliation.sql
psql -d skinspire_db -f migrations/create_gateway_reconciliation_detail.sql

# 6. Update supplier payment view
psql -d skinspire_db -f migrations/update_supplier_payment_view_v3.sql
```

### 6.2 Supplier Table Migration

**File:** `migrations/alter_supplier_add_gateway_fields.sql`

```sql
-- Add gateway integration fields to supplier table

ALTER TABLE supplier
ADD COLUMN razorpay_contact_id VARCHAR(50),
ADD COLUMN razorpay_fund_account_id VARCHAR(50),
ADD COLUMN paytm_beneficiary_id VARCHAR(50),
ADD COLUMN preferred_gateway VARCHAR(20);

-- Add check constraint for preferred_gateway
ALTER TABLE supplier
ADD CONSTRAINT check_preferred_gateway
CHECK (preferred_gateway IS NULL OR preferred_gateway IN ('razorpay', 'paytm'));

-- Add indexes for quick lookups
CREATE INDEX idx_supplier_razorpay_contact ON supplier(razorpay_contact_id) WHERE razorpay_contact_id IS NOT NULL;
CREATE INDEX idx_supplier_razorpay_fund_account ON supplier(razorpay_fund_account_id) WHERE razorpay_fund_account_id IS NOT NULL;
CREATE INDEX idx_supplier_paytm_beneficiary ON supplier(paytm_beneficiary_id) WHERE paytm_beneficiary_id IS NOT NULL;

-- Comments
COMMENT ON COLUMN supplier.razorpay_contact_id IS 'Razorpay contact ID for this supplier (cont_xxx)';
COMMENT ON COLUMN supplier.razorpay_fund_account_id IS 'Razorpay fund account ID for bank/UPI (fa_xxx)';
COMMENT ON COLUMN supplier.paytm_beneficiary_id IS 'Paytm beneficiary ID for money transfer';
COMMENT ON COLUMN supplier.preferred_gateway IS 'Preferred gateway provider for this supplier';
```

### 6.3 Rollback Scripts

**File:** `migrations/rollback_gateway_integration.sql`

```sql
-- Rollback gateway integration changes (use with caution!)

-- Drop views first
DROP VIEW IF EXISTS supplier_payment_view;

-- Recreate original view (v2.0)
-- (Insert original view SQL here)

-- Drop new tables
DROP TABLE IF EXISTS gateway_reconciliation_detail CASCADE;
DROP TABLE IF EXISTS gateway_reconciliation CASCADE;
DROP TABLE IF EXISTS gateway_webhook CASCADE;
DROP TABLE IF EXISTS gateway_transaction_log CASCADE;
DROP TABLE IF EXISTS gateway_configuration CASCADE;

-- Remove columns from supplier table
ALTER TABLE supplier
DROP COLUMN IF EXISTS razorpay_contact_id,
DROP COLUMN IF EXISTS razorpay_fund_account_id,
DROP COLUMN IF EXISTS paytm_beneficiary_id,
DROP COLUMN IF EXISTS preferred_gateway;

-- Note: supplier_payment gateway fields are NOT removed as they're part of core schema
```

---

## 7. Indexes and Constraints

### 7.1 Performance Optimization Indexes

```sql
-- Additional indexes for query optimization

-- Gateway configuration - fast lookup by hospital
CREATE INDEX idx_gateway_config_hospital_active
ON gateway_configuration(hospital_id, is_active, is_default)
WHERE is_active = true;

-- Transaction log - find recent errors
CREATE INDEX idx_gateway_log_recent_errors
ON gateway_transaction_log(initiated_at DESC, gateway_provider)
WHERE success = false;

-- Webhook - pending processing
CREATE INDEX idx_webhook_pending_processing
ON gateway_webhook(received_at ASC)
WHERE processing_status = 'pending';

-- Reconciliation - find open discrepancies
CREATE INDEX idx_recon_detail_open_discrepancies
ON gateway_reconciliation_detail(reconciliation_id, match_status)
WHERE resolved = false AND match_status != 'matched';
```

### 7.2 Data Integrity Constraints

```sql
-- Add foreign key constraints with appropriate actions

-- Gateway transaction log - cascade delete with payment
ALTER TABLE gateway_transaction_log
ADD CONSTRAINT fk_gateway_log_hospital
FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id) ON DELETE CASCADE;

-- Webhook - nullify payment_id if payment deleted
ALTER TABLE gateway_webhook
ADD CONSTRAINT fk_webhook_hospital
FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id) ON DELETE CASCADE
-- (implicit from payment_id foreign key);

-- Reconciliation - cascade delete with hospital
ALTER TABLE gateway_reconciliation
ADD CONSTRAINT fk_recon_hospital
FOREIGN KEY (hospital_id) REFERENCES hospital(hospital_id) ON DELETE CASCADE;
```

---

## Summary

**Database changes required:**

✅ **1 table altered:** `supplier` (4 columns added)
✅ **5 tables created:** Gateway configuration, transaction log, webhook, reconciliation (2)
✅ **1 view updated:** `supplier_payment_view` (v3.0)
✅ **6 models created/updated:** Configuration, logs, webhooks, reconciliation
✅ **30+ indexes created:** Optimized for common queries
✅ **10+ constraints added:** Data integrity and validation

**Next:** Review Part 3 for service layer implementation with these database models.
