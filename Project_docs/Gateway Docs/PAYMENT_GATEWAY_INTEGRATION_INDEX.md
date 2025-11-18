# Payment Gateway Integration - Documentation Index

**Version:** 1.0
**Date:** 2025-11-03
**Project:** Skinspire v2 - Supplier Payment Gateway Integration
**Scope:** Razorpay & Paytm Integration for Supplier Payments

---

## Overview

This documentation set provides a comprehensive approach for integrating Razorpay and Paytm payment gateways into the Skinspire v2 supplier payment system. The integration enables digital payments via gateway APIs, payment link generation, automated reconciliation, and refund management.

---

## Documentation Structure

### **Part 1: Overview & Architecture**
**File:** `PAYMENT_GATEWAY_PART1_OVERVIEW.md`

- Executive Summary
- Current State Analysis
- High-Level Architecture
- Gateway Abstraction Pattern
- Component Interaction Diagrams
- Integration Requirements

**Read this first** to understand the overall approach and architectural decisions.

---

### **Part 2: Database Design**
**File:** `PAYMENT_GATEWAY_PART2_DATABASE.md`

- Existing Gateway Fields Analysis
- New Tables Required:
  - Gateway Configuration
  - Gateway Transaction Log
  - Gateway Webhooks
  - Reconciliation Tables
- Database Views Updates
- Migration Scripts
- Model Definitions

**Essential for** database administrators and backend developers.

---

### **Part 3: Service Layer Design**
**File:** `PAYMENT_GATEWAY_PART3_SERVICES.md`

- Gateway Interface (Abstract Base Class)
- Gateway Manager Service
- Razorpay Adapter Implementation
- Paytm Adapter Implementation
- Webhook Processor Service
- Reconciliation Service
- Complete Code Examples

**Critical for** backend developers implementing gateway logic.

---

### **Part 4: API & UI Design**
**File:** `PAYMENT_GATEWAY_PART4_API_UI.md`

- Gateway Management API Endpoints
- Enhanced Payment APIs
- Payment Form UI Changes
- Payment View Enhancements
- Reconciliation Dashboard
- JavaScript Integration
- HTML/CSS Components

**Important for** full-stack developers and frontend team.

---

### **Part 5: Implementation Guide**
**File:** `PAYMENT_GATEWAY_PART5_IMPLEMENTATION.md`

- 8-Phase Implementation Timeline (12 weeks)
- Phase-by-Phase Deliverables
- Testing Strategy (Unit, Integration, Manual)
- Security Considerations
- Monitoring & Alerts Setup
- Deployment Checklist
- Staff Training Materials

**Must-read for** project managers, QA team, and DevOps.

---

## Quick Start Guide

### For Project Managers:
1. Read **Part 1** for overview
2. Review **Part 5** for timeline and phases
3. Assign team members to specific parts

### For Backend Developers:
1. Read **Part 1** for architecture context
2. Study **Part 2** for database changes
3. Implement following **Part 3** service patterns

### For Frontend Developers:
1. Read **Part 1** for integration flow
2. Review **Part 4** for UI/API specifications
3. Implement UI components

### For QA Team:
1. Read **Part 1** for feature understanding
2. Review **Part 5** testing strategy
3. Prepare test cases based on manual checklist

### For DevOps:
1. Read **Part 2** for database migrations
2. Review **Part 5** for deployment requirements
3. Set up monitoring and alerts

---

## Key Integration Features

### Supported Payment Gateways:
- ✅ **Razorpay** (Payouts API, Payment Links)
- ✅ **Paytm** (Money Transfer, Payment Links)

### Payment Flows:
- ✅ **Direct API Payouts** - Staff initiates payment via gateway
- ✅ **Payment Links** - Generate links for supplier self-service

### Payment Methods:
- ✅ UPI Transfers
- ✅ Bank Transfers (NEFT, RTGS, IMPS)

### Advanced Features:
- ✅ Split Payments across multiple invoices
- ✅ Refund Management
- ✅ Automated Daily Reconciliation
- ✅ Webhook Processing for real-time updates
- ✅ Gateway Fee Tracking

---

## Implementation Timeline

**Total Duration:** 12 Weeks

| Phase | Duration | Focus Area |
|-------|----------|------------|
| Phase 1 | Week 1-2 | Foundation & Database Setup |
| Phase 2 | Week 3-4 | Razorpay Integration |
| Phase 3 | Week 5 | Paytm Integration |
| Phase 4 | Week 6 | Webhook Processing |
| Phase 5 | Week 7-8 | UI Integration |
| Phase 6 | Week 9-10 | Reconciliation |
| Phase 7 | Week 11 | Refunds & Advanced Features |
| Phase 8 | Week 12 | Testing & Production Prep |

---

## Key Architectural Decisions

### 1. Gateway Abstraction Layer
**Decision:** Use abstract interface pattern with provider-specific adapters.
**Rationale:** Enables easy addition of new gateways without modifying core logic.

### 2. Hybrid Payment Model
**Decision:** Staff can choose manual entry OR gateway payment.
**Rationale:** Maintains flexibility for cash/cheque while enabling digital payments.

### 3. Webhook-Driven Status Updates
**Decision:** Rely on webhooks for payment status updates, with manual refresh option.
**Rationale:** Real-time updates without polling; reduces API calls.

### 4. Daily Reconciliation
**Decision:** Automated daily batch reconciliation with manual trigger option.
**Rationale:** Ensures data consistency; catches discrepancies early.

### 5. Existing Workflow Integration
**Decision:** Gateway payments follow same approval workflow as manual payments.
**Rationale:** Consistent business logic; reuses existing GL posting mechanism.

---

## Technology Stack

### Backend:
- **Python 3.x** - Core service implementation
- **SQLAlchemy 2.0** - Database ORM
- **PostgreSQL 17** - Database with JSONB support
- **Razorpay Python SDK** - Official SDK
- **Paytm Python SDK** - Official SDK

### Frontend:
- **Jinja2 Templates** - Server-side rendering
- **JavaScript (Vanilla)** - Dynamic form handling
- **TailwindCSS** - Styling

### Infrastructure:
- **Redis** - Webhook queue (optional)
- **Celery** - Background jobs for reconciliation (optional)
- **PostgreSQL Triggers** - Audit logging

---

## Security Highlights

### API Key Management:
- Encrypted storage using existing `EncryptionService`
- Keys decrypted only when needed
- Separate test and live mode configurations

### Webhook Security:
- Mandatory signature verification
- HMAC-SHA256 verification for Razorpay
- Request logging with IP tracking

### Idempotency:
- Payment ID used as idempotency key
- Prevents duplicate payouts
- Gateway-level duplicate detection

### Rate Limiting:
- 10 payouts per minute per user
- Configurable per hospital/branch

---

## Database Impact Summary

### New Tables: 5
1. `gateway_configuration` - Gateway settings
2. `gateway_transaction_log` - All API calls logged
3. `gateway_webhook` - Webhook receipts
4. `gateway_reconciliation` - Daily reconciliation runs
5. `gateway_reconciliation_detail` - Transaction-level matching

### Updated Tables: 1
1. `supplier_payment_view` - Add gateway columns

### Updated Models: 2
1. `Supplier` - Add Razorpay contact/fund account IDs
2. `SupplierPayment` - Already has gateway fields (no changes)

---

## API Endpoints Summary

### New Endpoints: 8
- `POST /api/gateway/initiate-payout` - Start gateway payout
- `POST /api/gateway/create-payment-link` - Generate payment link
- `GET /api/gateway/check-status/<payment_id>` - Check status
- `POST /api/gateway/create-refund` - Initiate refund
- `POST /api/gateway/webhook/<provider>` - Receive webhooks
- `POST /api/gateway/reconciliation/run` - Manual reconciliation
- `GET /api/gateway/reconciliation/<id>` - Get report
- `GET/POST /api/gateway/config` - Manage configuration

### Enhanced Endpoints: 2
- `GET /api/supplier/<id>/bank-accounts` - Get saved accounts
- `POST /api/supplier/<id>/add-bank-account` - Add/verify account

---

## UI Pages Summary

### Enhanced Pages: 2
1. **Payment Form** (`supplier/payment_form.html`)
   - Add gateway payment mode option
   - Add payment link option
   - Dynamic account selection

2. **Payment View** (`supplier/payment_view.html`)
   - Display gateway status
   - Show UTR/transaction ID
   - Refresh status button
   - Refund button

### New Pages: 1
1. **Reconciliation Dashboard** (`gateway/reconciliation_dashboard.html`)
   - Date/provider selection
   - Summary cards
   - Discrepancy table
   - Resolution workflow

---

## Testing Requirements

### Unit Tests: 30+
- Gateway adapter methods
- Webhook signature verification
- Transaction matching logic
- Error handling scenarios

### Integration Tests: 10+
- End-to-end payout flow
- Webhook processing flow
- Reconciliation matching
- Refund flow

### Manual Tests: 20+
- Gateway payout (UPI, bank transfer)
- Payment link generation
- Webhook updates
- Reconciliation run
- Error scenarios

---

## Dependencies

### Python Packages (Add to requirements.txt):
```
razorpay==1.3.0
paytm-python==1.0.0  # If official SDK available, else custom
cryptography==42.0.2  # Already in project
celery==5.3.0  # Optional, for background jobs
redis==5.0.0  # Optional, for Celery
```

### External Services:
- Razorpay Account (Test & Live)
- Paytm Merchant Account (Test & Live)
- SMS Gateway (for payment link notifications) - Optional
- Email Service (already configured in project)

---

## Risk Mitigation

### Technical Risks:
| Risk | Mitigation |
|------|------------|
| Gateway downtime | Manual fallback option; retry mechanism |
| Webhook failure | Status polling API; manual refresh |
| Amount mismatch | Reconciliation alerts; automated matching |
| Duplicate payout | Idempotency keys; database constraints |
| Security breach | Encrypted credentials; signature verification |

### Business Risks:
| Risk | Mitigation |
|------|------------|
| High gateway fees | Cost analysis; threshold-based routing |
| Supplier resistance | Payment link option; manual fallback |
| Settlement delays | Clear communication; status tracking |
| Reconciliation effort | Automated daily reconciliation |

---

## Success Metrics

### Technical Metrics:
- Gateway payout success rate > 95%
- Webhook processing < 5 seconds
- Reconciliation match rate > 98%
- API response time < 2 seconds

### Business Metrics:
- Payment processing time reduced by 50%
- Manual entry errors reduced by 80%
- Supplier payment satisfaction improved
- Reconciliation time reduced by 70%

---

## Support & Maintenance

### Monitoring:
- Gateway API health checks
- Webhook processing queue
- Failed payment alerts
- Daily reconciliation reports

### Maintenance Tasks:
- Weekly reconciliation review
- Monthly gateway fee analysis
- Quarterly security audit
- Annual credential rotation

---

## Related Documentation

### Existing Project Docs:
- `CLAUDE.md` - Project guidelines
- `SUPPLIER_ADVANCE_CHANGES_SUMMARY.md` - Advance payment system
- `CRITICAL_FIXES_SUMMARY.md` - Recent fixes
- `Project_docs/supplier_docs/` - Supplier module documentation

### External References:
- [Razorpay Payouts API Documentation](https://razorpay.com/docs/payouts/)
- [Razorpay Payment Links Documentation](https://razorpay.com/docs/payment-links/)
- [Paytm Money Transfer API](https://business.paytm.com/docs/api/)

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | Claude Code | Initial comprehensive documentation created |

---

## Next Steps

1. **Review Phase**: Share documentation with stakeholders
2. **Planning Phase**: Assign team members to phases
3. **Setup Phase**: Create development environment
4. **Implementation Phase**: Follow Part 5 timeline
5. **Testing Phase**: Execute test plans
6. **Deployment Phase**: Production rollout

---

**For questions or clarifications, refer to the specific part documentation or contact the development team.**
