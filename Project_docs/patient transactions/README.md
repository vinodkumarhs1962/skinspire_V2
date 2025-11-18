# Patient Transactions Documentation

This folder contains comprehensive documentation for the Patient Payment System in SkinSpire Clinic HMS.

## Documents

### 1. Patient_Payment_System_Complete_Guide.md

**Comprehensive technical guide covering:**

- Business logic and payment processing flow
- Many-to-many relationship architecture between payments and invoices
- Payment types: single invoice, multi-invoice, package installments
- Complete accounting entries (AR Subledger + GL Posting)
- Package payment plan integration
- Database schema and relationships
- Service layer architecture and key functions
- Configuration files and Universal Engine setup
- 3 detailed sample transactions with complete database entries
- Workflow and approval process
- Integration points with invoices and packages
- Business rules and best practices

**Key Sections:**

1. **Overview** - System capabilities and features
2. **Business Logic** - Payment processing flow and core principles
3. **Many-to-Many Architecture** - How payments link to multiple invoices
4. **Payment Types** - Single, multi-invoice, package installments
5. **Accounting Entries** - AR and GL double-entry bookkeeping
6. **Package Integration** - Installment payment handling
7. **Database Schema** - Tables, views, indexes
8. **Service Layer** - Key service files and functions
9. **Configuration** - Universal Engine configuration
10. **Sample Transactions** - 3 real-world examples with all entries
11. **Workflow** - Approval process and state transitions
12. **Integration Points** - Connections with other modules
13. **Business Rules** - Key rules and constraints

**Sample Transactions Included:**

1. **Simple Single Invoice Payment** (₹5,000)
   - Payment: Cash
   - Creates 3 AR entries (line-item level)
   - Creates 2 GL entries (balanced)
   - Auto-approved workflow

2. **Multi-Invoice Payment** (₹10,000)
   - Payment: Credit Card + UPI
   - Pays 3 invoices (2 full, 1 partial)
   - Creates 7 AR entries across 3 invoices
   - Creates 3 GL entries (multi-method payment)

3. **Package Installment Payment** (₹10,646.67) - REAL EXAMPLE
   - Payment: Cash + Credit Card
   - Breakdown:
     - Invoice payments: ₹7,500 (5 AR entries)
     - Package installment: ₹3,146.67 (1 AR entry)
   - Creates installment_payments record
   - Updates package_payment_plan
   - Creates 3 GL entries
   - Complete verification queries

**Technical Depth:**

- Actual SQL table definitions with all columns
- Service function signatures with parameters
- Code snippets from actual implementation
- Database queries for verification
- GL account mappings
- AR balance calculations
- Workflow state machine

**Use Cases:**

- **For Developers**: Understanding the architecture, service layer, database design
- **For Business Analysts**: Understanding payment flows, business rules, accounting impact
- **For Testers**: Sample transactions to verify system behavior
- **For Support**: Troubleshooting payment issues, understanding data relationships
- **For Auditors**: Understanding accounting entries and audit trail

## Quick Reference

### Key Tables

- `payment_details` - Main payment records
- `ar_subledger` - Accounts receivable tracking (junction table)
- `gl_transaction` - General ledger transactions
- `gl_entry` - GL debit/credit entries
- `installment_payments` - Package installment tracking
- `package_payment_plans` - Package payment plans
- `invoice_header` - Patient invoices
- `invoice_line_item` - Invoice line items

### Key Service Files

- `app/services/billing_service.py` - Main payment recording
- `app/services/subledger_service.py` - AR operations
- `app/services/gl_service.py` - GL posting
- `app/services/package_payment_service.py` - Package installments
- `app/services/patient_invoice_service.py` - Invoice operations

### Key Configuration

- `app/config/modules/patient_payment_config.py` - Universal Engine config
- `app/config/entity_registry.py` - Entity registration
- `app/database/view scripts/patient_payment_receipts_view v1.0.sql` - Main view

### Critical Business Rules

1. **AR is ALWAYS created** - Even for draft/pending payments
2. **GL posting is conditional** - Only for approved payments
3. **Line-item allocation** - Payment allocated at line-item level
4. **Payment priority** - Medicine → Service → Package
5. **Package dual tracking** - installment_payments + ar_subledger

### Recent Changes (2025-11-15)

**Bug Fixes:**
- ✅ Fixed AR creation (now ALWAYS created, not conditional)
- ✅ Fixed GL posting (corrected undefined variable)
- ✅ Added traceability fields population

**Enhancements:**
- ✅ Added 11 traceability fields to payment_details
- ✅ Added payment_number auto-generation
- ✅ Enhanced audit trail
- ✅ Improved bank reconciliation tracking

**Database Migration:**
- ✅ migrations/add_payment_traceability_fields.sql executed
- ✅ All 104 existing payments backfilled

## Support

For questions, refer to:
- The comprehensive guide in this folder
- Service files in `app/services/`
- Configuration in `app/config/modules/`
- Database views in `app/database/view scripts/`

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-15 | Initial documentation creation |
| 2.0 | 2025-11-15 | Added comprehensive guide with real examples |
