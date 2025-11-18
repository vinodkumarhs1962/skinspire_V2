# Payment Gateway Integration - Part 5: Implementation Guide

**Part:** 5 of 5
**Focus:** Implementation Phases, Testing, Deployment, Monitoring
**Audience:** Project managers, QA team, DevOps

---

## Table of Contents

1. [Implementation Timeline](#1-implementation-timeline)
2. [Phase-by-Phase Deliverables](#2-phase-by-phase-deliverables)
3. [Testing Strategy](#3-testing-strategy)
4. [Security Checklist](#4-security-checklist)
5. [Deployment Plan](#5-deployment-plan)
6. [Monitoring & Alerts](#6-monitoring--alerts)
7. [Staff Training](#7-staff-training)

---

## 1. Implementation Timeline

**Total Duration:** 12 Weeks

```
Week 1-2    ████████  Foundation & Database Setup
Week 3-4    ████████  Razorpay Integration
Week 5      ████████  Paytm Integration
Week 6      ████████  Webhook Processing
Week 7-8    ████████  UI Integration
Week 9-10   ████████  Reconciliation
Week 11     ████████  Refunds & Advanced Features
Week 12     ████████  Testing & Production Prep
```

### Milestones

| Week | Milestone | Success Criteria |
|------|-----------|------------------|
| 2 | Foundation Complete | Database migrations done, configs created |
| 4 | Razorpay Live | Test payouts working in sandbox |
| 5 | Multi-Gateway Support | Can switch between Razorpay/Paytm |
| 6 | Webhooks Active | Automatic status updates working |
| 8 | UI Complete | Staff can use gateway from UI |
| 10 | Reconciliation Automated | Daily job running successfully |
| 11 | Feature Complete | All requirements implemented |
| 12 | Production Ready | Testing complete, documentation done |

---

## 2. Phase-by-Phase Deliverables

### Phase 1: Foundation (Week 1-2)

**Objective:** Set up database schema and configuration infrastructure.

**Tasks:**
1. Create database migrations
   - Alter `supplier` table (add gateway fields)
   - Create `gateway_configuration` table
   - Create `gateway_transaction_log` table
   - Create `gateway_webhook` table
   - Create reconciliation tables (2)
   - Update `supplier_payment_view`

2. Create SQLAlchemy models
   - `GatewayConfiguration`
   - `GatewayTransactionLog`
   - `GatewayWebhook`
   - `GatewayReconciliation` & `GatewayReconciliationDetail`

3. Build gateway configuration UI
   - Admin page for gateway settings
   - Credential encryption/storage
   - Test/live mode switching
   - Enable/disable gateways

4. Create credential manager
   - `GatewayCredentialManager` class
   - Encrypt/decrypt using `EncryptionService`

**Deliverables:**
- [ ] All migrations executed successfully
- [ ] Models created and tested
- [ ] Gateway config UI accessible
- [ ] Can save encrypted credentials
- [ ] Unit tests for models (5+ tests)

**Testing:**
```bash
# Test migrations
psql -d skinspire_test -f migrations/create_gateway_configuration.sql

# Test models
pytest tests/test_models/test_gateway_models.py -v

# Test credential encryption
pytest tests/test_services/test_gateway_credentials.py -v
```

---

### Phase 2: Razorpay Integration (Week 3-4)

**Objective:** Implement complete Razorpay adapter with payout and payment link support.

**Tasks:**
1. Install Razorpay SDK
   ```bash
   pip install razorpay==1.3.0
   ```

2. Create gateway abstraction
   - `PaymentGatewayInterface` (ABC)
   - Data transfer objects (DTOs)
   - Custom exceptions

3. Implement Razorpay adapter
   - `RazorpayAdapter` class
   - Payout creation
   - Payment link generation
   - Status checking
   - Fund account management
   - Contact creation
   - Settlement report fetching

4. Build gateway manager
   - `PaymentGatewayManager` class
   - Gateway selection logic
   - Configuration loading
   - Transaction logging
   - Error handling

5. Integrate with supplier payment service
   - Add gateway payout method
   - Update payment creation workflow
   - Handle gateway responses

**Deliverables:**
- [ ] Razorpay adapter fully implemented
- [ ] Can create test payout in sandbox
- [ ] Can generate payment link
- [ ] Fund accounts created successfully
- [ ] Transaction logs saved
- [ ] Unit tests for adapter (10+ tests)
- [ ] Integration tests (3+ tests)

**Testing:**
```python
# Test Razorpay payout creation
def test_razorpay_create_payout(test_config):
    adapter = RazorpayAdapter(test_config)
    result = adapter.create_payout(test_payment_data)
    assert result.success == True
    assert result.gateway_payment_id.startswith('pout_')

# Test fund account creation
def test_razorpay_fund_account(test_supplier):
    adapter = RazorpayAdapter(test_config)
    fund_account_id = adapter._get_or_create_fund_account(
        test_supplier.supplier_id,
        {'upi_id': 'test@okaxis'},
        'upi'
    )
    assert fund_account_id.startswith('fa_')
```

---

### Phase 3: Paytm Integration (Week 5)

**Objective:** Add Paytm gateway support using same abstraction interface.

**Tasks:**
1. Install Paytm SDK (if available)
2. Implement `PaytmAdapter`
   - Money transfer API
   - Payment link (if supported)
   - Status check
   - Beneficiary management
3. Test provider switching
4. Validate abstraction pattern

**Deliverables:**
- [ ] Paytm adapter implemented
- [ ] Can create test transfer
- [ ] Can switch between Razorpay/Paytm
- [ ] Unit tests for Paytm (8+ tests)

---

### Phase 4: Webhook Processing (Week 6)

**Objective:** Implement webhook receiver and processor for automatic status updates.

**Tasks:**
1. Create webhook routes
   - `/api/gateway/webhook/razorpay`
   - `/api/gateway/webhook/paytm`

2. Implement `WebhookProcessor` service
   - Signature verification
   - Event parsing
   - Event routing
   - Payment status update
   - GL posting trigger

3. Create webhook handlers
   - Payout success
   - Payout failure
   - Payment link paid
   - Payment link expired

4. Set up webhook URLs in gateway dashboards
   - Razorpay dashboard webhook config
   - Paytm dashboard webhook config

5. Implement webhook retry mechanism
   - Retry failed webhooks (3 attempts)
   - Exponential backoff

**Deliverables:**
- [ ] Webhook routes working
- [ ] Signature verification passes
- [ ] Payment status updates automatically
- [ ] GL entries posted on success
- [ ] Webhook logs saved
- [ ] Integration tests (5+ tests)

**Testing:**
```python
def test_webhook_signature_verification():
    processor = WebhookProcessor()
    payload = b'{"event":"payout.processed"}'
    signature = generate_test_signature(payload, secret)
    assert processor.verify_signature(payload, signature, 'razorpay') == True

def test_webhook_payout_success():
    webhook_data = load_test_webhook('razorpay_payout_success.json')
    result = processor.process_webhook('razorpay', webhook_data, signature, {})
    assert result['success'] == True

    # Verify payment updated
    payment = SupplierPayment.query.get(test_payment_id)
    assert payment.gateway_completed_at is not None
    assert payment.gl_posted == True
```

---

### Phase 5: UI Integration (Week 7-8)

**Objective:** Enable staff to use gateway payments from web interface.

**Tasks:**
1. Update payment form template
   - Add payment mode selector (manual/gateway/link)
   - Gateway payout section
   - Payment link section
   - Account selection dropdown

2. Update payment view template
   - Gateway status display
   - UTR/transaction ID
   - Refresh status button
   - Refund button
   - Timeline display

3. Create JavaScript handlers
   - Mode switching
   - Account loading (AJAX)
   - Fee calculation
   - Status refresh
   - Link resend

4. Add API endpoints
   - `/api/gateway/initiate-payout`
   - `/api/gateway/create-payment-link`
   - `/api/gateway/check-status/<id>`
   - `/api/supplier/<id>/bank-accounts`

5. Create modal dialogs
   - Add bank account modal
   - Refund confirmation modal
   - Payment link preview modal

**Deliverables:**
- [ ] Payment form shows gateway options
- [ ] Staff can initiate gateway payout
- [ ] Staff can generate payment link
- [ ] Gateway status visible in payment view
- [ ] Manual status refresh works
- [ ] Fee preview accurate
- [ ] UI/UX testing complete

**Manual Testing Checklist:**
- [ ] Select gateway payout mode
- [ ] Choose Razorpay/Paytm
- [ ] Select UPI account
- [ ] See fee calculation
- [ ] Submit payment
- [ ] View payment status
- [ ] Refresh status manually
- [ ] Generate payment link
- [ ] Copy link to clipboard
- [ ] Resend link

---

### Phase 6: Reconciliation (Week 9-10)

**Objective:** Implement automated daily reconciliation with settlement matching.

**Tasks:**
1. Create `GatewayReconciliationService`
   - Fetch gateway settlements
   - Fetch system payments
   - Match by UTR, amount, date
   - Identify discrepancies
   - Generate reports

2. Implement matching algorithm
   - Exact match (UTR + amount)
   - Fuzzy match (amount + date range)
   - Discrepancy categorization

3. Create reconciliation dashboard UI
   - Summary cards
   - Discrepancy table
   - Resolution workflow
   - Export to Excel

4. Set up scheduled job
   - Daily 2 AM reconciliation
   - Use Celery or cron
   - Email report to finance team

5. Create discrepancy resolution UI
   - Mark as resolved
   - Add resolution notes
   - Link to manual payment

**Deliverables:**
- [ ] Reconciliation service working
- [ ] Can fetch settlements from both gateways
- [ ] Matching algorithm > 95% accuracy
- [ ] Reconciliation dashboard accessible
- [ ] Daily job scheduled
- [ ] Email reports sent
- [ ] Unit tests (8+ tests)

**Testing:**
```python
def test_reconciliation_matching():
    gateway_settlements = load_test_settlements()
    system_payments = load_test_payments()

    service = GatewayReconciliationService()
    results = service.match_transactions(gateway_settlements, system_payments)

    matched = [r for r in results if r['match_status'] == 'matched']
    assert len(matched) == 18  # Out of 20 transactions

def test_reconciliation_run():
    result = service.run_daily_reconciliation(
        hospital_id='test-hospital',
        reconciliation_date=date.today(),
        provider='razorpay'
    )

    assert result['success'] == True
    assert result['summary']['matched_count'] > 0
```

---

### Phase 7: Refunds & Advanced Features (Week 11)

**Objective:** Add refund support and advanced features.

**Tasks:**
1. Implement refund workflow
   - Refund initiation
   - Create reverse payment
   - Update GL entries
   - Track refund status

2. Add split payment support
   - Pay multiple invoices in one transaction
   - Allocate amounts
   - Track allocations

3. Implement retry mechanism
   - Retry failed gateway payments
   - Manual retry button
   - Automatic retry (configurable)

4. Add batch payment support
   - Select multiple invoices
   - Create batch payout
   - Track batch status

5. Enhanced reporting
   - Gateway fee summary
   - Settlement timeline
   - Success rate metrics

**Deliverables:**
- [ ] Refund workflow complete
- [ ] Can initiate refunds
- [ ] Split payments working
- [ ] Retry mechanism functional
- [ ] Batch payments supported
- [ ] Reports accessible

---

### Phase 8: Testing & Production Prep (Week 12)

**Objective:** Comprehensive testing and production deployment preparation.

**Tasks:**
1. End-to-end testing
   - Full payout flow (UPI, bank transfer)
   - Payment link flow
   - Webhook processing
   - Reconciliation
   - Refunds

2. Security audit
   - Credential encryption verified
   - Webhook signature validation
   - SQL injection prevention
   - XSS prevention
   - Rate limiting

3. Performance testing
   - Load test (100 concurrent payouts)
   - Response time < 2 seconds
   - Webhook processing < 5 seconds
   - Database query optimization

4. Documentation
   - API documentation (Swagger)
   - User manual for staff
   - Admin guide
   - Troubleshooting guide

5. Production configuration
   - Live mode credentials
   - Production webhook URLs
   - Monitoring setup
   - Backup procedures

6. Staff training
   - Training sessions (2 hours)
   - User guide distribution
   - Q&A session
   - Recorded demo videos

**Deliverables:**
- [ ] All tests passing (100+ tests)
- [ ] Security audit complete
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Production configs ready
- [ ] Staff trained
- [ ] Go-live checklist approved

---

## 3. Testing Strategy

### 3.1 Unit Tests

**Target:** 100+ unit tests, 80%+ coverage

**Framework:** pytest

**Test Categories:**
1. Model tests (10 tests)
2. Gateway adapter tests (30 tests)
3. Webhook processor tests (15 tests)
4. Reconciliation service tests (20 tests)
5. API endpoint tests (25 tests)
6. Helper function tests (10 tests)

**Example Test Structure:**

```python
# tests/test_payment_gateway/test_razorpay_adapter.py

class TestRazorpayAdapter:
    def test_create_payout_success(self, test_config):
        """Test successful payout creation"""
        adapter = RazorpayAdapter(test_config)
        result = adapter.create_payout(test_payment_data)
        assert result.success == True
        assert result.gateway_payment_id.startswith('pout_')

    def test_create_payout_insufficient_balance(self, mock_razorpay):
        """Test payout failure due to insufficient balance"""
        mock_razorpay.payout.create.side_effect = BadRequestError()
        adapter = RazorpayAdapter(test_config)

        with pytest.raises(GatewayAPIError):
            adapter.create_payout(test_payment_data)

    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification"""
        adapter = RazorpayAdapter(test_config)
        payload = b'{"event":"payout.processed"}'
        signature = generate_signature(payload, secret)

        assert adapter.verify_webhook_signature(payload, signature, secret) == True

    def test_verify_webhook_signature_invalid(self):
        """Test invalid webhook signature"""
        adapter = RazorpayAdapter(test_config)
        assert adapter.verify_webhook_signature(b'payload', 'invalid', secret) == False
```

### 3.2 Integration Tests

**Target:** 25+ integration tests

**Test Scenarios:**
1. Complete payout flow (create → webhook → GL posting)
2. Payment link flow (create → paid → webhook)
3. Refund flow
4. Reconciliation flow
5. Multi-gateway switching

**Example:**

```python
def test_end_to_end_payout_flow(test_db, test_user):
    """Test complete payout flow from creation to completion"""
    # 1. Create payment
    payment = create_test_payment(amount=5000, payment_mode='gateway_payout')

    # 2. Initiate gateway payout
    gateway_manager = PaymentGatewayManager(test_user.hospital_id)
    result = gateway_manager.create_gateway_payout(
        payment_id=payment.payment_id,
        supplier_id=payment.supplier_id,
        amount=payment.amount,
        payment_method='upi',
        account_details={'upi_id': 'test@okaxis'}
    )

    assert result['success'] == True

    # 3. Simulate webhook
    webhook_payload = create_webhook_payload('payout.processed', result['gateway_payment_id'])
    webhook_processor = WebhookProcessor()
    webhook_result = webhook_processor.process_webhook('razorpay', webhook_payload, signature, {})

    assert webhook_result['success'] == True

    # 4. Verify payment updated
    updated_payment = SupplierPayment.query.get(payment.payment_id)
    assert updated_payment.gateway_completed_at is not None
    assert updated_payment.gl_posted == True
    assert updated_payment.workflow_status == 'completed'
```

### 3.3 Manual Testing Checklist

**Gateway Payout Flow:**
- [ ] Select gateway payout mode
- [ ] Choose Razorpay provider
- [ ] Select UPI method
- [ ] Choose supplier account
- [ ] Verify fee calculation
- [ ] Submit payment
- [ ] Check transaction log created
- [ ] Verify payment status "pending"
- [ ] Simulate webhook (dev tools)
- [ ] Verify status updated to "completed"
- [ ] Check GL entries posted
- [ ] Verify UTR number populated

**Payment Link Flow:**
- [ ] Select payment link mode
- [ ] Enter supplier email/phone
- [ ] Set expiry (48 hours)
- [ ] Generate link
- [ ] Copy link URL
- [ ] Open link in browser
- [ ] Complete payment (test mode)
- [ ] Verify webhook received
- [ ] Check payment status updated
- [ ] Verify GL posted

**Reconciliation:**
- [ ] Run manual reconciliation for test date
- [ ] Verify matched transactions
- [ ] Check discrepancy detection
- [ ] Mark discrepancy as resolved
- [ ] Export reconciliation report
- [ ] Verify email sent

**Error Scenarios:**
- [ ] Invalid account details → Error message
- [ ] Insufficient gateway balance → Error handled
- [ ] Invalid webhook signature → Rejected
- [ ] Duplicate payout request → Prevented
- [ ] Network timeout → Retry works

---

## 4. Security Checklist

### 4.1 Pre-Deployment Security Audit

**Credential Management:**
- [ ] API keys encrypted at rest using `EncryptionService`
- [ ] Keys decrypted only when needed
- [ ] No keys in logs or error messages
- [ ] Separate test and live credentials
- [ ] Credential rotation procedure documented

**Webhook Security:**
- [ ] Signature verification mandatory
- [ ] HMAC-SHA256 verification implemented
- [ ] Invalid signatures rejected (HTTP 401)
- [ ] IP whitelisting (optional)
- [ ] Rate limiting on webhook endpoints

**API Security:**
- [ ] All gateway endpoints require authentication
- [ ] Permission checks using `@require_api_branch_permission`
- [ ] Rate limiting (10 payouts/minute per user)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (input sanitization)

**Data Security:**
- [ ] Bank account details not logged
- [ ] UPI IDs masked in UI
- [ ] Transaction logs exclude sensitive data
- [ ] HTTPS required for all API calls
- [ ] Secure session management

**Idempotency:**
- [ ] Payment ID used as idempotency key
- [ ] Duplicate payout requests prevented
- [ ] Database constraints enforce uniqueness

---

## 5. Deployment Plan

### 5.1 Pre-Deployment Checklist

**Code:**
- [ ] All tests passing (unit + integration)
- [ ] Code reviewed and approved
- [ ] Security audit complete
- [ ] Performance benchmarks met

**Database:**
- [ ] All migrations tested on staging
- [ ] Backup of production database taken
- [ ] Rollback scripts ready

**Configuration:**
- [ ] Production gateway credentials obtained
- [ ] Webhook URLs configured in gateway dashboards
- [ ] Environment variables set
- [ ] Redis/Celery configured (if using)

**Monitoring:**
- [ ] Application logs configured
- [ ] Error tracking (Sentry) set up
- [ ] Monitoring alerts configured
- [ ] Dashboard created

**Documentation:**
- [ ] User manual complete
- [ ] API documentation published
- [ ] Troubleshooting guide ready
- [ ] Rollback procedure documented

### 5.2 Deployment Steps

**Phase 1: Staging Deployment** (Day 1)
1. Deploy to staging environment
2. Run full test suite
3. Test with live gateway sandbox mode
4. Verify webhooks working
5. Test reconciliation
6. UAT with select staff members

**Phase 2: Production Deployment** (Day 3)
1. Deploy during maintenance window (2 AM)
2. Run database migrations
3. Deploy application code
4. Restart services
5. Smoke tests
6. Monitor for 2 hours

**Phase 3: Gradual Rollout** (Week 1)
1. Enable for single hospital/branch
2. Monitor for 2 days
3. Enable for 3 more branches
4. Monitor for 3 days
5. Enable for all users

### 5.3 Rollback Procedure

**If Critical Issue Detected:**

1. Disable gateway payments (feature flag)
   ```python
   # Set in gateway_configuration
   UPDATE gateway_configuration SET is_active = false;
   ```

2. Rollback code (if needed)
   ```bash
   git revert <commit-hash>
   git push
   ```

3. Rollback database (if needed)
   ```bash
   psql -d skinspire_db -f migrations/rollback_gateway_integration.sql
   ```

4. Notify users via email
5. Investigate issue
6. Fix and redeploy

---

## 6. Monitoring & Alerts

### 6.1 Application Logging

**File:** `app/core/logging_config.py`

```python
GATEWAY_LOGGING = {
    'version': 1,
    'handlers': {
        'gateway_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/gateway.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'app.services.payment_gateway': {
            'handlers': ['gateway_file'],
            'level': 'INFO'
        }
    }
}
```

**Log All:**
- Gateway API requests (without sensitive data)
- Gateway API responses
- Webhook receipts
- Reconciliation runs
- Errors and exceptions

### 6.2 Metrics to Monitor

**Operational Metrics:**
- Payout success rate (target: > 95%)
- Average payout time (target: < 2 seconds)
- Webhook processing time (target: < 5 seconds)
- Reconciliation match rate (target: > 98%)

**Business Metrics:**
- Total payouts per day
- Total amount disbursed
- Gateway fees paid
- Refund rate

**Error Metrics:**
- Failed payout count
- Webhook failures
- Reconciliation discrepancies
- API errors

### 6.3 Alert Configuration

```python
# app/services/notification_service.py

GATEWAY_ALERTS = {
    'payout_failed': {
        'threshold': 5,  # Alert if 5+ failures in 1 hour
        'recipients': ['finance@skinspire.com'],
        'severity': 'high'
    },
    'reconciliation_discrepancy': {
        'threshold': 3,  # Alert if 3+ discrepancies
        'recipients': ['accounting@skinspire.com'],
        'severity': 'medium'
    },
    'webhook_failure': {
        'threshold': 10,  # Alert if 10+ webhook failures
        'recipients': ['tech@skinspire.com'],
        'severity': 'high'
    },
    'gateway_api_error': {
        'threshold': 20,  # Alert if 20+ API errors
        'recipients': ['tech@skinspire.com'],
        'severity': 'critical'
    }
}
```

---

## 7. Staff Training

### 7.1 Training Sessions

**Session 1: Overview (1 hour)**
- What is payment gateway integration?
- Benefits for staff and suppliers
- High-level workflow overview
- Demo: Creating gateway payment

**Session 2: Hands-On (1.5 hours)**
- Creating gateway payout (UPI, bank transfer)
- Generating payment link
- Checking payment status
- Handling failures
- Initiating refunds
- Practice exercises

**Session 3: Reconciliation (30 mins)**
- Understanding reconciliation dashboard
- Reviewing discrepancies
- Marking as resolved
- Exporting reports

### 7.2 User Guide (Quick Reference)

**How to Create Gateway Payout:**
1. Go to Supplier → Record Payment
2. Select "Gateway Payout" mode
3. Choose gateway provider (or use default)
4. Select transfer method (UPI/NEFT/IMPS/RTGS)
5. Select supplier account
6. Review gateway fees
7. Submit payment
8. Payment status will update automatically via webhook

**How to Generate Payment Link:**
1. Go to Supplier → Record Payment
2. Select "Payment Link" mode
3. Verify supplier email/phone
4. Set link expiry (24/48/72 hours)
5. Click "Generate Link"
6. Link sent to supplier automatically
7. Monitor payment status

**How to Check Payment Status:**
1. Go to payment detail page
2. View "Gateway Payment Details" section
3. Check status badge
4. Click "Refresh Status" if needed
5. UTR number available when completed

---

## Summary

Implementation guide provides:
✅ 12-week phased timeline
✅ Detailed deliverables per phase
✅ Comprehensive testing strategy (100+ tests)
✅ Security audit checklist
✅ Deployment plan with rollback
✅ Monitoring and alerting setup
✅ Staff training materials

**Success Criteria:**
- All 8 phases completed on time
- 100+ tests passing
- Security audit cleared
- Performance benchmarks met
- Staff trained
- Production deployment successful
- Zero critical issues in first week

**Next Steps:**
1. Review all 5 parts with stakeholders
2. Get approval to proceed
3. Assign team members to phases
4. Set up development environment
5. Begin Phase 1 implementation

---

**END OF PAYMENT GATEWAY INTEGRATION DOCUMENTATION**

For questions or clarifications, contact the development team.
