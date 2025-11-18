# Patient Billing Module - Universal Engine Migration Approach

**Version:** 1.0
**Date:** January 2025
**Status:** Planning
**Author:** Development Team

---

## Executive Summary

### Purpose
This document outlines the strategic approach for migrating the Patient Billing Module from a custom-built implementation to the Universal Engine architecture, following the successful patterns established in the Supplier Module.

### Current State
- **2,855 lines** of custom service code
- **2,235 lines** of custom view code
- **12+ custom templates** for billing operations
- **18 routes** (15 frontend + 3 API)
- **NO Universal Engine integration**
- **NO database views** for optimized queries

### Target State
- **List and Detail Views** powered by Universal Engine (configuration-driven)
- **Database Views** for optimized querying (patient_invoices_view, patient_payments_view, patient_advances_view)
- **Unified UI/UX** consistent with Supplier Module gold standard
- **Custom Routes** retained for complex operations (create, edit, workflow actions)
- **Estimated 40% reduction** in view/template code
- **Enhanced features**: Advanced filtering, sorting, export, print configurations

### Migration Scope
Three billing entities will be migrated:
1. **Patient Invoices** (primary entity)
2. **Patient Payments** (separate entity)
3. **Patient Advances** (separate entity)

### Strategic Approach
**Hybrid Architecture:**
- ✅ **Universal Engine** for: List views, Detail views, Filtering, Sorting, Export, Print, Caching
- ✅ **Custom Routes** for: Invoice creation, Payment recording, Advance management, Void/Cancel, Refunds

### Benefits
- **Consistency:** Unified UX across all modules
- **Maintainability:** Configuration changes vs. code changes
- **Performance:** Database views eliminate app-level joins
- **Features:** Advanced filtering, caching, document generation "for free"
- **Scalability:** Easy to extend with new fields/filters

### Risks & Mitigation
| Risk | Mitigation |
|------|------------|
| Complex database views | Incremental development, start simple |
| Breaking existing workflows | URL redirects, backward compatibility |
| Performance regression | Index view columns, load testing |
| User retraining | Minimal UX changes (consistent with supplier module) |

---

## 1. Current State Analysis

### 1.1 Billing Module Components

#### **Routes** (app/views/billing_views.py)
| Route | Type | Complexity | Migration Target |
|-------|------|------------|------------------|
| `/invoice/list` | List View | Medium | **→ Universal Engine** |
| `/invoice/<id>` | Detail View | Medium | **→ Universal Engine** |
| `/invoice/create` | Create | **High** | **Keep Custom** |
| `/invoice/<id>/payment` | Workflow | Medium | **Keep Custom** |
| `/invoice/<id>/void` | Workflow | Medium | **Keep Custom** |
| `/invoice/<id>/print` | Document | Low | **→ Document Config** |
| `/invoice/<id>/send-email` | Action | Low | **Keep Custom** |
| `/invoice/<id>/send-whatsapp` | Action | Low | **Keep Custom** |
| `/invoice/advance/create` | Create | Medium | **Keep Custom** |
| `/invoice/advance/list` | List View | Medium | **→ Universal Engine** |
| `/invoice/advance/apply/<id>` | Workflow | **High** | **Keep Custom** |

#### **Templates** (app/templates/billing/)
- `invoice_list.html` → **Replaced by** `engine/universal_list.html`
- `view_invoice.html` → **Replaced by** `engine/universal_view.html`
- `create_invoice.html` → **Keep** (complex wizard)
- `payment_form.html` → **Keep** (multi-method validation)
- `advance_payment.html` → **Keep** (advance logic)
- `advance_payment_list.html` → **Replaced by** `engine/universal_list.html`
- `print_invoice.html` → **Migrate to** Document Configuration

#### **Models** (app/models/transaction.py)
- `InvoiceHeader` - Main invoice table ✅
- `InvoiceLineItem` - Line items ✅
- `PaymentDetail` - Payments ✅
- `PatientAdvancePayment` - Advances ✅

**Missing:** Database views for list/detail operations

#### **Services** (app/services/billing_service.py - 2,855 lines)
**Current Structure:**
```
BillingService (custom class)
├── create_invoice() - Complex multi-invoice logic
├── get_invoice_by_id() - Custom query with joins
├── search_invoices() - Custom search logic
├── record_payment() - Multi-method validation
├── void_invoice() - GL reversal logic
├── issue_refund() - Refund workflow
├── create_advance_payment() - Advance recording
├── apply_advance_payment() - Complex adjustment
└── generate_invoice_pdf() - PDF generation
```

**Target Structure:**
```
PatientInvoiceService(UniversalEntityService)
├── search_data() - Inherited (uses view)
├── get_by_id() - Inherited (uses view)
├── create_invoice() - Keep custom
├── void_invoice() - Keep custom
├── get_invoice_lines() - Custom renderer
└── get_payment_history() - Custom renderer

PatientPaymentService(UniversalEntityService)
├── search_data() - Inherited
├── get_by_id() - Inherited
├── record_payment() - Keep custom
└── issue_refund() - Keep custom

PatientAdvanceService(UniversalEntityService)
├── search_data() - Inherited
├── get_by_id() - Inherited
├── create_advance() - Keep custom
└── apply_advance() - Keep custom
```

### 1.2 Supplier Module Reference (Gold Standard)

#### **Universal Engine Integration**
The Supplier Module successfully migrated to Universal Engine with:

1. **Database Views:**
   - `supplier_invoices_view` (denormalized invoice data)
   - `supplier_payments_view` (payment data with invoice info)

2. **Entity Configurations:**
   - `supplier_invoice_config.py` (1,421 lines - comprehensive field definitions)
   - `supplier_payment_config.py` (2,455 lines - including workflow)

3. **Hybrid Routes:**
   - **Universal Engine:** `/universal/supplier_invoices/list`, `/universal/supplier_invoices/detail/<id>`
   - **Custom Routes:** `/supplier/invoice/create`, `/supplier/payment/record`, `/supplier/payment/approve/<id>`

4. **Key Features:**
   - Tabbed detail views (Invoice Details, Line Items, Payments, GL Posting)
   - Custom renderers for complex data (line items table, payment history)
   - Action buttons (approve, reject, delete, restore, print)
   - Summary cards (Total Invoices, Outstanding Amount, Overdue)
   - Advanced filters (payment status, aging buckets, supplier, date ranges)
   - Document configurations (print receipt, voucher, statement)

#### **UI/UX Standards Established:**
- Modern TailwindCSS styling
- Responsive layouts
- Advanced search with entity dropdowns
- Real-time filtering and sorting
- Export to Excel/PDF
- Print preview functionality
- Workflow status indicators
- Audit trail visibility

---

## 2. Universal Engine Benefits for Billing

### 2.1 Feature Enhancements

#### **Advanced Filtering** (Configuration-Driven)
**Current:** Basic text search + status dropdown
**After Migration:**
- Payment Status: `paid`, `partial`, `unpaid`, `cancelled`
- Invoice Type: `Service`, `Product`, `Prescription`, `Miscellaneous`
- Patient Search: Entity autocomplete with MRN/name/phone
- Date Ranges: `Today`, `Last 7 days`, `Last 30 days`, `Current FY`, `Custom`
- Amount Ranges: Min/Max filters
- Branch Filter: Multi-branch support
- Created By: User filter

#### **Summary Cards** (Real-Time Metrics)
**Current:** Static counts
**After Migration:**
- Total Invoices (count)
- Total Revenue (₹)
- Outstanding Amount (₹)
- Cancelled Invoices (count)
- This Month Revenue (₹)
- Average Invoice Value (₹)

#### **Export Capabilities** (Built-In)
**Current:** None
**After Migration:**
- Export to Excel
- Export to CSV
- Export to PDF
- Filtered results export
- Custom column selection

#### **Print Configurations** (Document Configs)
**Current:** Custom PDF generation
**After Migration:**
- Print Invoice (standard format)
- Print Receipt (payment receipt)
- Print Statement (patient statement)
- Print Summary (batch summary)
- Configurable headers/footers
- Signature fields
- Terms and conditions

### 2.2 Performance Improvements

#### **Database Views** (Optimized Queries)
**Current Approach:**
```python
# Multiple queries with app-level joins
invoices = session.query(InvoiceHeader).all()
for invoice in invoices:
    patient = session.query(Patient).get(invoice.patient_id)
    payments = session.query(PaymentDetail).filter_by(invoice_id=invoice.invoice_id).all()
    # N+1 query problem
```

**Universal Engine Approach:**
```sql
-- Single optimized query
CREATE VIEW patient_invoices_view AS
SELECT
    ih.*,
    p.full_name AS patient_name,
    p.mrn AS patient_mrn,
    COUNT(pd.payment_id) AS payment_count,
    SUM(pd.total_amount) AS total_paid
FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id
LEFT JOIN payment_details pd ON ih.invoice_id = pd.invoice_id
GROUP BY ih.invoice_id, p.patient_id;
```

**Performance Impact:**
- **Reduced Queries:** 1 query vs. N+1 queries
- **Faster Response:** Database-level joins vs. app-level
- **Better Caching:** View results cached by Universal Engine
- **Indexed Columns:** View columns can be indexed

#### **Caching Strategy**
**Current:** No caching
**After Migration:**
- Service-level caching (30-minute TTL)
- Configuration caching (1-hour TTL)
- Cache invalidation on create/update/delete
- Cache keys include: entity, filters, hospital, branch, user

### 2.3 Maintainability Improvements

#### **Configuration vs. Code**
**Adding a New Filter (Current):**
1. Update template HTML (invoice_list.html)
2. Update view function (billing_views.py)
3. Update service query (billing_service.py)
4. Update JavaScript (if AJAX)
**Total:** 4 files modified, ~100 lines of code

**Adding a New Filter (After Migration):**
1. Update entity configuration (patient_invoice_config.py)
```python
FilterDefinition(
    name="invoice_type",
    label="Invoice Type",
    field_type=FieldType.SELECT,
    options=["Service", "Product", "Prescription", "Misc"]
)
```
**Total:** 1 file modified, ~5 lines of configuration

#### **Code Reduction Estimate**
| Component | Current Lines | After Migration | Reduction |
|-----------|---------------|-----------------|-----------|
| View Functions | 800 | 200 | **75%** |
| Templates | 1,200 | 400 | **67%** |
| Service (search) | 300 | 50 | **83%** |
| **Total** | **2,300** | **650** | **72%** |

**Note:** Complex business logic (create invoice, payments, advances) remains unchanged.

---

## 3. Migration Strategy: Three Entities

### 3.1 Entity Breakdown

#### **Entity 1: Patient Invoices**
**Purpose:** Patient billing invoices
**Complexity:** High (multi-type invoices, line items, GST)
**Operations:**
- **Universal Engine:** List, View, Print
- **Custom Routes:** Create, Void, Email, WhatsApp

**Database View:** `patient_invoices_view`
**Key Fields:**
- Invoice: invoice_id, invoice_number, invoice_date, invoice_type
- Patient: patient_id, patient_name, patient_mrn, patient_phone
- Amounts: total_amount, grand_total, paid_amount, balance_due
- Status: payment_status (paid/partial/unpaid/cancelled)
- Calculated: invoice_age_days, invoice_year, invoice_month

**Configuration Highlights:**
- **Tabs:** Invoice Details, Line Items, Payments, System Info
- **Actions:** view, print, record_payment, void, send_email, send_whatsapp
- **Filters:** payment_status, invoice_type, patient, date_range, amount_range
- **Summary Cards:** Total Revenue, Outstanding, Cancelled, Monthly Revenue

#### **Entity 2: Patient Payments**
**Purpose:** Payment transactions against invoices
**Complexity:** Medium (multi-method payments, refunds)
**Operations:**
- **Universal Engine:** List, View, Print
- **Custom Routes:** Record (integrated with invoice), Refund

**Database View:** `patient_payments_view`
**Key Fields:**
- Payment: payment_id, payment_date, total_amount
- Methods: cash_amount, credit_card_amount, debit_card_amount, upi_amount
- Invoice: invoice_number, invoice_date, invoice_total
- Patient: patient_name, patient_mrn
- Status: payment_status (completed/refunded)
- Reconciliation: reconciliation_status, reconciled_by, reconciled_at

**Configuration Highlights:**
- **Tabs:** Payment Details, Invoice Details, Reconciliation, Documents
- **Actions:** view, print_receipt, refund, reconcile
- **Filters:** payment_status, payment_method, date_range, amount_range
- **Summary Cards:** Total Collected, Pending Reconciliation, Refunded

#### **Entity 3: Patient Advances**
**Purpose:** Advance payments from patients
**Complexity:** Medium (advance tracking, application logic)
**Operations:**
- **Universal Engine:** List, View, Print
- **Custom Routes:** Create, Apply (to invoice)

**Database View:** `patient_advances_view`
**Key Fields:**
- Advance: advance_payment_id, payment_date, amount, available_balance
- Patient: patient_name, patient_mrn, patient_phone
- Status: status (active/applied/refunded)
- Usage: total_applied, total_refunded, remaining_balance
- Applications: applied_invoices_count, last_applied_date

**Configuration Highlights:**
- **Tabs:** Advance Details, Application History, Patient Info
- **Actions:** view, print_receipt, apply_to_invoice, refund
- **Filters:** status, patient, date_range, available_balance
- **Summary Cards:** Total Advances, Available Balance, Applied Amount

### 3.2 Entity Relationships

```
Patient
   ├── Patient Invoices (1:N)
   │   ├── Invoice Line Items (1:N)
   │   └── Patient Payments (1:N)
   └── Patient Advances (1:N)
       └── Advance Applications (1:N) → Links to Invoices
```

**Impact on Migration:**
- Each entity has separate view, configuration, service
- Cross-entity features (apply advance to invoice) remain custom routes
- Detail views can show related entities via custom renderers

---

## 4. Phase-by-Phase Migration Approach

### Phase 1: Foundation (Database Infrastructure)

**Objective:** Create database views and model definitions

**Deliverables:**
1. **Database Views** (3 SQL scripts)
   - `migrations/create_patient_invoices_view.sql`
   - `migrations/create_patient_payments_view.sql`
   - `migrations/create_patient_advances_view.sql`

2. **View Models** (app/models/views.py)
   - `class PatientInvoiceView(Base)`
   - `class PatientPaymentView(Base)`
   - `class PatientAdvanceView(Base)`

3. **Entity Registry** (app/config/entity_registry.py)
   - Register all 3 entities

**Success Criteria:**
- Views created in database successfully
- View models mapped correctly
- Can query view models from Python
- No performance degradation on existing queries

**Rollback:** Drop views if issues detected

---

### Phase 2: Entity Configuration

**Objective:** Create comprehensive entity configurations

**Deliverables:**
1. **Configuration Files** (app/config/modules/)
   - `patient_invoice_config.py` (~1,500 lines)
   - `patient_payment_config.py` (~800 lines)
   - `patient_advance_config.py` (~600 lines)

2. **Configuration Components per Entity:**
   - Field Definitions (50-90 fields)
   - Tab Definitions (3-5 tabs)
   - Section Definitions (10-15 sections)
   - Action Definitions (5-8 actions)
   - Filter Definitions (8-12 filters)
   - Summary Card Definitions (4-6 cards)
   - Document Configurations (2-4 documents)

**Success Criteria:**
- All configurations load without errors
- Fields render correctly in detail view
- Filters work on list view
- Actions appear with correct conditions
- Summary cards display accurate data

**Rollback:** Revert configuration files

---

### Phase 3: Service Layer Refactoring

**Objective:** Extend UniversalEntityService while preserving custom logic

**Deliverables:**
1. **New Service Classes** (app/services/)
   - `class PatientInvoiceService(UniversalEntityService)` in billing_service.py
   - `class PatientPaymentService(UniversalEntityService)` in billing_service.py
   - `class PatientAdvanceService(UniversalEntityService)` in billing_service.py

2. **Service Methods:**
   - **Inherited:** `search_data()`, `get_by_id()`
   - **Custom:** `create_invoice()`, `void_invoice()`, `record_payment()`, `issue_refund()`, `create_advance()`, `apply_advance()`
   - **New:** `get_invoice_lines()`, `get_payment_history()` (custom renderers)

3. **Cache Invalidation:**
   - Update all custom methods to invalidate caches
   - Use `invalidate_service_cache_for_entity()`

**Success Criteria:**
- Search returns correct results from view
- Get by ID returns complete invoice data
- Custom methods still work
- Cache invalidation works correctly

**Rollback:** Keep old service class, comment out new classes

---

### Phase 4: Routes & UI Migration

**Objective:** Switch list/detail views to Universal Engine

**Deliverables:**
1. **Route Changes** (app/views/billing_views.py)
   - **Remove:** `/invoice/list`, `/invoice/<id>` (detail)
   - **Remove:** `/invoice/advance/list`
   - **Keep:** All create/edit/workflow routes
   - **Update:** Action routes to redirect to Universal Engine detail view

2. **Navigation Updates** (app/templates/base.html, menu configs)
   - Update menu links to Universal Engine routes
   - Add URL redirects for old routes (backward compatibility)

3. **Template Cleanup:**
   - Archive old list/detail templates
   - Keep custom form templates (create, payment, advance)

4. **Testing:**
   - Verify list view loads at `/universal/patient_invoices/list`
   - Verify detail view loads at `/universal/patient_invoices/detail/<id>`
   - Verify filters work
   - Verify actions work (buttons navigate to custom routes)
   - Verify print works

**Success Criteria:**
- All list views accessible via Universal Engine
- All detail views accessible via Universal Engine
- Custom routes still work (create, void, payment)
- No broken links in navigation
- Print/export works

**Rollback:** Restore old routes, revert navigation

---

### Phase 5: Advanced Features & Polish

**Objective:** Implement advanced features and optimize

**Deliverables:**
1. **Custom Renderers:**
   - Line items table renderer
   - Payment history renderer
   - Advance application history renderer

2. **Document Configurations:**
   - Invoice print layout
   - Payment receipt layout
   - Advance receipt layout

3. **Performance Optimization:**
   - Index view columns
   - Optimize view queries
   - Load testing with large datasets

4. **User Training:**
   - Document new features
   - Train staff on new UI
   - Gather feedback

**Success Criteria:**
- Custom renderers display correctly
- Print layouts match requirements
- Performance meets targets (< 2s load time)
- Users can perform all existing tasks

**Rollback:** Disable custom renderers, use fallback display

---

## 5. Feature Mapping: What Goes Where

### 5.1 Universal Engine Features

| Feature | Invoice | Payment | Advance | Notes |
|---------|---------|---------|---------|-------|
| **List View** | ✅ | ✅ | ✅ | Configuration-driven |
| **Detail View** | ✅ | ✅ | ✅ | Tabbed layout |
| **Search/Filter** | ✅ | ✅ | ✅ | Advanced filters |
| **Sort** | ✅ | ✅ | ✅ | Multi-column |
| **Export** | ✅ | ✅ | ✅ | Excel/CSV/PDF |
| **Print** | ✅ | ✅ | ✅ | Document configs |
| **Summary Cards** | ✅ | ✅ | ✅ | Real-time metrics |
| **Pagination** | ✅ | ✅ | ✅ | Configurable page size |
| **Caching** | ✅ | ✅ | ✅ | Auto cache invalidation |

### 5.2 Custom Route Features

| Feature | Route | Entity | Notes |
|---------|-------|--------|-------|
| **Create Invoice** | `/billing/invoice/create` | Invoice | Complex wizard, multi-type |
| **Void Invoice** | `/billing/invoice/<id>/void` | Invoice | GL reversal required |
| **Record Payment** | `/billing/invoice/<id>/payment` | Payment | Multi-method validation |
| **Refund Payment** | `/billing/payment/<id>/refund` | Payment | GL reversal required |
| **Create Advance** | `/billing/advance/create` | Advance | Patient advance recording |
| **Apply Advance** | `/billing/advance/apply/<invoice_id>` | Advance | Complex adjustment logic |
| **Send Email** | `/billing/invoice/<id>/send-email` | Invoice | Email service integration |
| **Send WhatsApp** | `/billing/invoice/<id>/send-whatsapp` | Invoice | Messaging integration |

### 5.3 Hybrid Features (Mix of Both)

| Feature | Universal Engine Part | Custom Route Part |
|---------|------------------------|-------------------|
| **Print Invoice** | Document configuration, template | Custom PDF generation if needed |
| **Payment History** | Custom renderer in detail view | Payment list view |
| **Line Items Display** | Custom renderer in detail view | Line item data service |
| **Advance Application** | Advance list view | Apply advance workflow |

---

## 6. Risk Assessment & Mitigation

### 6.1 Technical Risks

#### **Risk 1: Complex Database Views**
**Impact:** Medium
**Probability:** Medium
**Description:** Views with 40+ columns, multiple joins may be slow

**Mitigation:**
- Start with minimal view (core fields only)
- Add columns incrementally
- Index frequently queried columns
- Use materialized views if needed (refresh strategy)
- Load testing with production-like data volumes

#### **Risk 2: Breaking Existing Workflows**
**Impact:** High
**Probability:** Low
**Description:** URL changes may break bookmarks, external links

**Mitigation:**
- Implement URL redirects for old routes
- Maintain backward compatibility for 6 months
- Communicate changes to users in advance
- Provide updated documentation

#### **Risk 3: Performance Regression**
**Impact:** High
**Probability:** Low
**Description:** New architecture may be slower than current implementation

**Mitigation:**
- Performance testing at each phase
- Rollback plan if targets not met
- Database query optimization
- Caching strategy validation
- Load testing before production deployment

#### **Risk 4: Lost Features**
**Impact:** High
**Probability:** Low
**Description:** Some custom features may not translate to Universal Engine

**Mitigation:**
- Comprehensive feature inventory before migration
- Custom renderers for complex displays
- Keep custom routes for unique workflows
- User acceptance testing

### 6.2 Business Risks

#### **Risk 5: User Resistance**
**Impact:** Medium
**Probability:** Medium
**Description:** Users may resist new UI/UX

**Mitigation:**
- Maintain similar UX to current implementation
- Leverage familiar patterns from Supplier Module
- Provide training before rollout
- Phased rollout with feedback loops
- Quick response to user feedback

#### **Risk 6: Extended Development Time**
**Impact:** Medium
**Probability:** Medium
**Description:** Migration may take longer than estimated

**Mitigation:**
- Detailed phase planning with buffers
- Parallel development where possible
- Prioritize critical features
- Phased deployment (invoices first, then payments, then advances)

### 6.3 Data Risks

#### **Risk 7: Data Migration Issues**
**Impact:** Low
**Probability:** Low
**Description:** No data migration required, but views may expose data issues

**Mitigation:**
- This is a UI/architecture migration, not data migration
- Views query existing tables
- Data validation during testing
- Rollback plan maintains data integrity

---

## 7. Success Criteria & Validation

### 7.1 Technical Success Criteria

#### **Performance Metrics**
- **List View Load Time:** < 2 seconds (for 100 invoices)
- **Detail View Load Time:** < 1 second
- **Search Response Time:** < 1 second
- **Filter Application:** < 500ms
- **Export Time:** < 5 seconds (for 1,000 records)

#### **Code Quality Metrics**
- **Code Reduction:** 60%+ for list/detail views
- **Test Coverage:** 80%+ for new services
- **Configuration Coverage:** 100% of fields defined
- **Documentation:** Complete for all new features

#### **Functional Metrics**
- **Feature Parity:** 100% of existing features available
- **Enhanced Features:** Filtering, sorting, export, print
- **Bug-Free:** Zero critical bugs in production
- **Uptime:** No downtime during migration

### 7.2 User Acceptance Criteria

#### **Usability**
- Users can find all existing features
- New features are intuitive
- Reduced clicks for common tasks
- Faster navigation
- Better search/filter capabilities

#### **Training**
- Users trained on new UI within 1 week
- Documentation updated and accessible
- Support team ready to handle queries

#### **Feedback**
- User satisfaction score: 8/10 or higher
- Reduced support tickets
- Positive feedback on new features

### 7.3 Validation Approach

#### **Phase Validation**
Each phase must pass validation before proceeding:

**Phase 1 Validation:**
- [ ] Database views created successfully
- [ ] View models query correctly
- [ ] No performance impact on existing queries
- [ ] DBA review and approval

**Phase 2 Validation:**
- [ ] All configurations load without errors
- [ ] Fields render correctly in test environment
- [ ] Filters return correct results
- [ ] Actions display with correct conditions
- [ ] Code review approval

**Phase 3 Validation:**
- [ ] Service methods return expected data
- [ ] Cache invalidation works
- [ ] No regression in custom methods
- [ ] Unit tests pass
- [ ] Integration tests pass

**Phase 4 Validation:**
- [ ] All routes accessible
- [ ] Navigation works correctly
- [ ] No broken links
- [ ] Custom routes still functional
- [ ] User acceptance testing passed

**Phase 5 Validation:**
- [ ] Custom renderers display correctly
- [ ] Print layouts approved
- [ ] Performance targets met
- [ ] Load testing passed
- [ ] Production readiness review

#### **Final Validation Checklist**
Before production deployment:
- [ ] All phases completed and validated
- [ ] User training completed
- [ ] Documentation updated
- [ ] Rollback plan tested
- [ ] Stakeholder sign-off
- [ ] Production deployment plan approved

---

## 8. Universal Engine Principles: Do's and Don'ts

### 8.1 CRITICAL Do's

#### ✅ **DO: Keep Universal Engine Components Entity-Agnostic**

**Principle:** Universal Engine artifacts must work for ANY entity without hardcoding entity-specific logic.

**Examples:**

**In Entity Configuration (CORRECT):**
```python
# ✅ CORRECT: Generic field definition
FieldDefinition(
    name="grand_total",
    label="Grand Total",
    field_type=FieldType.CURRENCY,
    show_in_list=True
)

# ✅ CORRECT: Custom renderer uses context function
FieldDefinition(
    name="line_items_display",
    field_type=FieldType.CUSTOM,
    custom_renderer=CustomRenderer(
        template="engine/business/universal_line_items_table.html",
        context_function="get_invoice_lines"  # Service method provides data
    )
)
```

**In Service Layer (CORRECT):**
```python
# ✅ CORRECT: Extend UniversalEntityService
class PatientInvoiceService(UniversalEntityService):
    def __init__(self):
        super().__init__('patient_invoices', PatientInvoiceView)

    # Inherited methods work automatically
    # Add custom methods for business logic
```

#### ✅ **DO: Use Database Views for List/Detail Operations**

**Principle:** Database views optimize queries and eliminate N+1 problems.

**Benefits:**
- Single query instead of multiple joins
- Database-level optimization
- Simplified service code
- Better caching

**Example:**
```sql
-- ✅ CORRECT: Denormalized view with all required data
CREATE VIEW patient_invoices_view AS
SELECT
    ih.*,
    p.full_name AS patient_name,
    p.mrn AS patient_mrn,
    COUNT(pd.payment_id) AS payment_count
FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id
LEFT JOIN payment_details pd ON ih.invoice_id = pd.invoice_id
GROUP BY ih.invoice_id, p.patient_id;
```

#### ✅ **DO: Invalidate Caches After Data Changes**

**Principle:** Always clear caches after create/update/delete operations.

**Example:**
```python
# ✅ CORRECT: Invalidate cache after operation
def create_invoice(self, data, hospital_id, branch_id, user_id):
    with get_db_session() as session:
        # Create invoice logic
        session.commit()

        # CRITICAL: Invalidate cache
        invalidate_service_cache_for_entity('patient_invoices', cascade=False)

    return {"success": True, "data": invoice_dict}
```

**IMPORTANT:** Invalidate ALL affected entities:
```python
# Payment affects BOTH patient_payments AND patient_invoices
def record_payment(self, invoice_id, payment_data, user_id):
    # ... payment logic ...

    invalidate_service_cache_for_entity('patient_payments', cascade=False)
    invalidate_service_cache_for_entity('patient_invoices', cascade=False)  # Invoice paid_amount changed
```

#### ✅ **DO: Use Configuration-Driven Filters**

**Principle:** Add filters via configuration, not code.

**Example:**
```python
# ✅ CORRECT: Filter definition in config
FilterDefinition(
    name="payment_status",
    label="Payment Status",
    field_type=FieldType.SELECT,
    options=["paid", "partial", "unpaid", "cancelled"],
    multi_select=True,
    category="Status"
)
```

**Result:** Universal Engine handles filter UI, query building, and application automatically.

#### ✅ **DO: Use Custom Renderers for Complex Displays**

**Principle:** For complex data displays (tables, charts, custom layouts), use custom renderers.

**Example:**
```python
# ✅ CORRECT: Custom renderer for line items table
FieldDefinition(
    name="line_items_display",
    field_type=FieldType.CUSTOM,
    show_in_detail=True,
    tab_group="line_items",
    custom_renderer=CustomRenderer(
        template="engine/business/invoice_line_items_table.html",
        context_function="get_invoice_lines"  # Service method
    )
)
```

**Service Method:**
```python
def get_invoice_lines(self, invoice_id, hospital_id):
    """Called by Universal Engine"""
    with get_db_session() as session:
        lines = session.query(InvoiceLineItem).filter_by(
            invoice_id=invoice_id,
            hospital_id=hospital_id
        ).all()
        return [get_entity_dict(line) for line in lines]
```

#### ✅ **DO: Keep Custom Routes for Complex Business Logic**

**Principle:** Use Universal Engine for read operations, custom routes for complex workflows.

**Example:**
```python
# ✅ CORRECT: Complex invoice creation stays custom
@billing_views_bp.route('/invoice/create', methods=['GET', 'POST'])
def create_invoice():
    # Complex wizard, multi-type logic, inventory checks
    # After creation: redirect to Universal detail view
    return redirect(url_for('universal_views.universal_detail_view',
                            entity_type='patient_invoices',
                            item_id=invoice_id))
```

---

### 8.2 CRITICAL Don'ts

#### ❌ **DON'T: Hardcode Entity-Specific Logic in Universal Components**

**Problem:** Breaks reusability, creates tight coupling.

**Examples:**

**In Templates (WRONG):**
```html
<!-- ❌ WRONG: Hardcoded field names in universal template -->
<div class="invoice-total">
    Total: {{ item.grand_total }}  <!-- Entity-specific field! -->
</div>

<!-- ✅ CORRECT: Use generic field rendering -->
<div class="field-display">
    {{ render_field(item, field_config) }}  <!-- Configuration-driven -->
</div>
```

**In Service (WRONG):**
```python
# ❌ WRONG: Entity-specific query in universal service
class UniversalEntityService:
    def search_data(self, filters):
        # NEVER do this:
        if self.entity_type == 'patient_invoices':
            query = query.filter(InvoiceHeader.is_cancelled == False)
```

#### ❌ **DON'T: Use App-Level Joins Instead of Database Views**

**Problem:** N+1 queries, poor performance, complex code.

**Example:**

**WRONG Approach:**
```python
# ❌ WRONG: App-level joins
def get_invoices():
    invoices = session.query(InvoiceHeader).all()
    for invoice in invoices:
        invoice.patient = session.query(Patient).get(invoice.patient_id)  # N+1!
        invoice.payments = session.query(Payment).filter_by(invoice_id=invoice.invoice_id).all()  # N+1!
```

**CORRECT Approach:**
```sql
-- ✅ CORRECT: Database view with joins
CREATE VIEW patient_invoices_view AS
SELECT ih.*, p.full_name AS patient_name, COUNT(pd.payment_id) AS payment_count
FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id
LEFT JOIN payment_details pd ON ih.invoice_id = pd.invoice_id
GROUP BY ih.invoice_id;
```

#### ❌ **DON'T: Forget Cache Invalidation**

**Problem:** Stale data displayed, users don't see changes.

**Example:**

**WRONG:**
```python
# ❌ WRONG: No cache invalidation
def create_invoice(self, data):
    # ... create invoice ...
    session.commit()
    return {"success": True}  # Cache still has old list!
```

**CORRECT:**
```python
# ✅ CORRECT: Invalidate cache
def create_invoice(self, data):
    # ... create invoice ...
    session.commit()
    invalidate_service_cache_for_entity('patient_invoices', cascade=False)
    return {"success": True}
```

**CRITICAL:** Single record invalidation does NOT clear list caches:
```python
# ❌ WRONG: Only clears single record cache
invoice_service.invalidate_cache(invoice_id)

# ✅ CORRECT: Clears ALL entity caches (list, detail, filters)
invalidate_service_cache_for_entity('patient_invoices', cascade=False)
```

#### ❌ **DON'T: Add Custom Routes for Simple Read Operations**

**Problem:** Code duplication, inconsistent UX.

**Example:**

**WRONG:**
```python
# ❌ WRONG: Custom route for list view
@billing_views_bp.route('/invoice/list')
def invoice_list():
    # Custom HTML, custom filters, custom pagination
    # Duplicates Universal Engine functionality!
```

**CORRECT:**
```python
# ✅ CORRECT: Use Universal Engine
# Route: /universal/patient_invoices/list
# Configuration handles filters, pagination, sorting
```

#### ❌ **DON'T: Mix Master and Transaction CRUD Patterns**

**Problem:** Confusion, inconsistent behavior.

**Rule:**
- **Master Entities:** Use Universal Engine for FULL CRUD (list, view, create, edit, delete)
- **Transaction Entities:** Use Universal Engine for LIST/VIEW only, custom routes for create/edit/workflow

**Example:**

**For Patient Invoices (Transaction):**
```python
# ✅ CORRECT
# List: /universal/patient_invoices/list (Universal Engine)
# View: /universal/patient_invoices/detail/<id> (Universal Engine)
# Create: /billing/invoice/create (Custom route)
# Void: /billing/invoice/<id>/void (Custom route)

# ❌ WRONG: Don't use Universal Engine create for transactions
# /universal/patient_invoices/create  ← DON'T DO THIS!
```

**For Suppliers (Master):**
```python
# ✅ CORRECT: Use Universal Engine for everything
# List: /universal/suppliers/list
# View: /universal/suppliers/detail/<id>
# Create: /universal/suppliers/create
# Edit: /universal/suppliers/edit/<id>
# Delete: /universal/suppliers/delete/<id>
```

#### ❌ **DON'T: Modify Universal Engine Core Files**

**Problem:** Breaks future updates, creates technical debt.

**Rule:** NEVER modify:
- `app/engine/universal_entity_service.py`
- `app/engine/universal_crud_service.py`
- `app/views/universal_views.py`
- `app/templates/engine/universal_list.html`
- `app/templates/engine/universal_view.html`

**If you need custom behavior:**
- Extend classes (inheritance)
- Use custom renderers
- Use custom routes
- Configure via entity config

---

### 8.3 Best Practices Summary

| Scenario | DO | DON'T |
|----------|-----|-------|
| **List View** | Use Universal Engine with config | Create custom list template |
| **Detail View** | Use Universal Engine with tabs | Create custom detail template |
| **Complex Display** | Use custom renderer | Hardcode in universal template |
| **Filtering** | Add filter definition to config | Write custom filter logic |
| **Sorting** | Configure sortable fields | Implement custom sorting |
| **Export** | Use Universal Engine export | Write custom export code |
| **Create (Transaction)** | Custom route + redirect to Universal detail | Use Universal Engine create |
| **Create (Master)** | Use Universal Engine create | Custom route |
| **Read Operations** | Database view + inherited methods | App-level joins |
| **Cache Management** | Invalidate after changes | Assume auto-refresh |
| **Custom Logic** | Extend service, keep custom methods | Modify universal service |

---

## 9. UI/UX Guidelines (Based on Supplier Module Gold Standard)

### 9.1 List View Standards

#### **Layout Structure**

**Header Section:**
```
+------------------------------------------------------------------+
|  📊 Patient Invoices                    [+ Create Invoice] [Export] |
+------------------------------------------------------------------+
|  Filters:  [Status ▼] [Type ▼] [Patient Search] [Date Range]     |
+------------------------------------------------------------------+
|  Summary Cards:                                                   |
|  +-------------+  +-------------+  +-------------+  +-------------+
|  | Total       |  | Outstanding |  | Cancelled   |  | This Month  |
|  | Revenue     |  | Amount      |  | Invoices    |  | Revenue     |
|  | ₹1,250,000  |  | ₹85,000     |  | 12          |  | ₹320,000    |
|  +-------------+  +-------------+  +-------------+  +-------------+
+------------------------------------------------------------------+
```

**Table Section:**
```
+------------------------------------------------------------------+
| # | Invoice No | Date       | Patient   | Type   | Amount | Status |
+------------------------------------------------------------------+
| ☐ | INV-001    | 03-Jan-25  | John Doe  | Service| ₹5,000 | Paid   |
| ☐ | INV-002    | 03-Jan-25  | Jane Smith| Product| ₹8,500 | Partial|
+------------------------------------------------------------------+
|                        Showing 1-20 of 245     [Prev] [1][2][3] [Next] |
+------------------------------------------------------------------+
```

#### **Visual Design Standards**

**Color Scheme (TailwindCSS):**
- **Primary Blue:** `bg-blue-600` for primary actions
- **Success Green:** `bg-green-600` for paid status, positive actions
- **Warning Yellow:** `bg-yellow-500` for partial status, pending items
- **Danger Red:** `bg-red-600` for cancelled status, void actions
- **Secondary Gray:** `bg-gray-600` for neutral actions
- **Info Blue:** `bg-blue-500` for informational elements

**Status Badges:**
```html
<!-- Paid -->
<span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
    Paid
</span>

<!-- Partial -->
<span class="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
    Partial
</span>

<!-- Unpaid -->
<span class="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
    Unpaid
</span>

<!-- Cancelled -->
<span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
    Cancelled
</span>
```

**Currency Display:**
```html
<!-- Large amounts (summary cards) -->
<span class="text-2xl font-bold text-gray-900">₹1,250,000</span>

<!-- Table amounts -->
<span class="text-sm font-medium text-gray-900">₹5,000</span>

<!-- Outstanding amounts (highlight) -->
<span class="text-sm font-semibold text-red-600">₹85,000</span>
```

#### **Interactive Elements**

**Search Box:**
```html
<div class="relative">
    <input type="text"
           placeholder="Search invoices by number, patient name, MRN..."
           class="w-full px-4 py-2 pl-10 pr-4 text-gray-700 bg-white border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500">
    <span class="absolute left-3 top-2.5 text-gray-400">
        <i class="fas fa-search"></i>
    </span>
</div>
```

**Filter Dropdowns:**
```html
<select class="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500">
    <option value="">All Status</option>
    <option value="paid">Paid</option>
    <option value="partial">Partial</option>
    <option value="unpaid">Unpaid</option>
    <option value="cancelled">Cancelled</option>
</select>
```

**Action Buttons:**
```html
<!-- Primary Action -->
<button class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
    <i class="fas fa-plus mr-2"></i>Create Invoice
</button>

<!-- Secondary Action -->
<button class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500">
    <i class="fas fa-download mr-2"></i>Export
</button>
```

---

### 9.2 Detail View Standards

#### **Tabbed Layout Structure**

```
+------------------------------------------------------------------+
|  Invoice Details: INV-001                                         |
|  Status: Paid     Date: 03-Jan-2025     Patient: John Doe        |
+------------------------------------------------------------------+
|  [Invoice Details] [Line Items] [Payments] [System Info]         |
+------------------------------------------------------------------+
|                                                                   |
|  Invoice Details Tab (Active):                                   |
|                                                                   |
|  ┌─ Invoice Information ──────────────┐                          |
|  │ Invoice Number: INV-001            │                          |
|  │ Invoice Date: 03-Jan-2025          │                          |
|  │ Invoice Type: Service              │                          |
|  └────────────────────────────────────┘                          |
|                                                                   |
|  ┌─ Patient Information ──────────────┐                          |
|  │ Name: John Doe                      │                          |
|  │ MRN: MRN-12345                      │                          |
|  │ Phone: +91 98765 43210             │                          |
|  └────────────────────────────────────┘                          |
|                                                                   |
|  ┌─ Amount Details ────────────────────┐                         |
|  │ Subtotal:    ₹4,500                 │                          |
|  │ GST (18%):   ₹810                   │                          |
|  │ Grand Total: ₹5,310                 │                          |
|  │ Paid:        ₹5,310  ✓              │                          |
|  │ Balance:     ₹0                     │                          |
|  └────────────────────────────────────┘                          |
|                                                                   |
+------------------------------------------------------------------+
|  Actions: [Print] [Record Payment] [Void] [Email] [WhatsApp]    |
+------------------------------------------------------------------+
```

#### **Section Design Standards**

**Section Headers:**
```html
<div class="mb-4">
    <h3 class="text-lg font-semibold text-gray-900 border-b-2 border-blue-500 pb-2">
        <i class="fas fa-file-invoice mr-2 text-blue-600"></i>
        Invoice Information
    </h3>
</div>
```

**Field Display (Two-Column):**
```html
<div class="grid grid-cols-2 gap-4">
    <div>
        <label class="text-sm font-medium text-gray-600">Invoice Number</label>
        <p class="text-base font-semibold text-gray-900">INV-001</p>
    </div>
    <div>
        <label class="text-sm font-medium text-gray-600">Invoice Date</label>
        <p class="text-base font-semibold text-gray-900">03-Jan-2025</p>
    </div>
</div>
```

**Field Display (Three-Column for Amounts):**
```html
<div class="grid grid-cols-3 gap-4">
    <div class="text-center">
        <label class="text-sm font-medium text-gray-600">Subtotal</label>
        <p class="text-xl font-bold text-gray-900">₹4,500</p>
    </div>
    <div class="text-center">
        <label class="text-sm font-medium text-gray-600">GST</label>
        <p class="text-xl font-bold text-gray-900">₹810</p>
    </div>
    <div class="text-center bg-blue-50 p-3 rounded-lg">
        <label class="text-sm font-medium text-blue-600">Grand Total</label>
        <p class="text-2xl font-bold text-blue-900">₹5,310</p>
    </div>
</div>
```

#### **Tab Design Standards**

**Tab Navigation:**
```html
<div class="border-b border-gray-200">
    <nav class="flex space-x-4">
        <!-- Active Tab -->
        <a href="#invoice-details"
           class="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
            <i class="fas fa-file-invoice mr-2"></i>Invoice Details
        </a>

        <!-- Inactive Tab -->
        <a href="#line-items"
           class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 border-b-2 border-transparent hover:border-gray-300">
            <i class="fas fa-list mr-2"></i>Line Items
        </a>

        <a href="#payments"
           class="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 border-b-2 border-transparent hover:border-gray-300">
            <i class="fas fa-money-bill mr-2"></i>Payments
        </a>
    </nav>
</div>
```

#### **Custom Renderer Tables**

**Line Items Table:**
```html
<table class="w-full text-sm text-left text-gray-700">
    <thead class="text-xs text-gray-700 uppercase bg-gray-100">
        <tr>
            <th class="px-4 py-3">#</th>
            <th class="px-4 py-3">Item</th>
            <th class="px-4 py-3">Qty</th>
            <th class="px-4 py-3 text-right">Price</th>
            <th class="px-4 py-3 text-right">GST</th>
            <th class="px-4 py-3 text-right">Total</th>
        </tr>
    </thead>
    <tbody class="divide-y divide-gray-200">
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-3">1</td>
            <td class="px-4 py-3 font-medium">Consultation - General</td>
            <td class="px-4 py-3">1</td>
            <td class="px-4 py-3 text-right">₹500</td>
            <td class="px-4 py-3 text-right">₹90</td>
            <td class="px-4 py-3 text-right font-semibold">₹590</td>
        </tr>
    </tbody>
    <tfoot class="bg-gray-50">
        <tr>
            <td colspan="5" class="px-4 py-3 text-right font-bold">Subtotal:</td>
            <td class="px-4 py-3 text-right font-bold text-lg">₹5,310</td>
        </tr>
    </tfoot>
</table>
```

---

### 9.3 Action Button Standards

#### **Button Placement**

**Detail View Actions (Bottom of Page):**
```html
<div class="flex justify-between items-center mt-6 pt-4 border-t border-gray-200">
    <!-- Left Side: Navigation -->
    <a href="/universal/patient_invoices/list"
       class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
        <i class="fas fa-arrow-left mr-2"></i>Back to List
    </a>

    <!-- Right Side: Actions -->
    <div class="flex space-x-2">
        <button class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            <i class="fas fa-print mr-2"></i>Print
        </button>
        <button class="px-4 py-2 text-white bg-green-600 rounded-lg hover:bg-green-700">
            <i class="fas fa-money-bill mr-2"></i>Record Payment
        </button>
        <button class="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700">
            <i class="fas fa-ban mr-2"></i>Void
        </button>
    </div>
</div>
```

#### **Conditional Button Display**

**Show/Hide Based on Status:**
```html
<!-- Show "Record Payment" only for unpaid/partial invoices -->
{% if item.payment_status in ['unpaid', 'partial'] and not item.is_cancelled %}
<button class="px-4 py-2 text-white bg-green-600 rounded-lg hover:bg-green-700">
    <i class="fas fa-money-bill mr-2"></i>Record Payment
</button>
{% endif %}

<!-- Show "Void" only for non-cancelled invoices -->
{% if not item.is_cancelled %}
<button class="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700">
    <i class="fas fa-ban mr-2"></i>Void
</button>
{% endif %}
```

#### **Confirmation Dialogs**

**Destructive Actions (Void, Delete):**
```javascript
// Modern confirmation modal
function confirmVoid(invoiceId) {
    Swal.fire({
        title: 'Void Invoice?',
        text: 'This action cannot be undone. The invoice will be marked as cancelled.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc2626',
        cancelButtonColor: '#6b7280',
        confirmButtonText: 'Yes, void it',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = `/billing/invoice/${invoiceId}/void`;
        }
    });
}
```

---

### 9.4 Responsive Design Standards

#### **Mobile Breakpoints**

**List View (Mobile):**
```html
<!-- Desktop: Table -->
<div class="hidden md:block">
    <table class="w-full">...</table>
</div>

<!-- Mobile: Cards -->
<div class="block md:hidden">
    <div class="space-y-3">
        <div class="p-4 bg-white rounded-lg shadow">
            <div class="flex justify-between items-start">
                <div>
                    <p class="font-semibold text-gray-900">INV-001</p>
                    <p class="text-sm text-gray-600">John Doe</p>
                </div>
                <span class="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                    Paid
                </span>
            </div>
            <div class="mt-3 flex justify-between items-center">
                <span class="text-lg font-bold text-gray-900">₹5,310</span>
                <a href="/universal/patient_invoices/detail/..." class="text-blue-600">
                    View <i class="fas fa-chevron-right"></i>
                </a>
            </div>
        </div>
    </div>
</div>
```

**Action Buttons (Mobile):**
```html
<!-- Desktop: Inline buttons -->
<div class="hidden md:flex space-x-2">
    <button>Print</button>
    <button>Payment</button>
    <button>Void</button>
</div>

<!-- Mobile: Dropdown menu -->
<div class="block md:hidden">
    <button class="px-4 py-2 bg-blue-600 text-white rounded-lg" onclick="toggleMenu()">
        Actions <i class="fas fa-chevron-down"></i>
    </button>
    <div id="action-menu" class="hidden absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg">
        <a href="#print" class="block px-4 py-2 hover:bg-gray-100">Print</a>
        <a href="#payment" class="block px-4 py-2 hover:bg-gray-100">Record Payment</a>
        <a href="#void" class="block px-4 py-2 hover:bg-gray-100">Void</a>
    </div>
</div>
```

---

### 9.5 Typography Standards

**Headings:**
```html
<!-- Page Title -->
<h1 class="text-3xl font-bold text-gray-900">Patient Invoices</h1>

<!-- Section Title -->
<h2 class="text-xl font-semibold text-gray-900">Invoice Information</h2>

<!-- Subsection Title -->
<h3 class="text-lg font-medium text-gray-700">Payment Details</h3>
```

**Body Text:**
```html
<!-- Label -->
<label class="text-sm font-medium text-gray-600">Patient Name</label>

<!-- Value -->
<p class="text-base font-semibold text-gray-900">John Doe</p>

<!-- Helper Text -->
<p class="text-sm text-gray-500">Enter patient details accurately</p>
```

**Numbers and Currency:**
```html
<!-- Large Amount (Summary Card) -->
<span class="text-2xl font-bold text-gray-900">₹1,250,000</span>

<!-- Medium Amount (Table) -->
<span class="text-base font-semibold text-gray-900">₹5,310</span>

<!-- Small Amount (Breakdown) -->
<span class="text-sm text-gray-700">₹90</span>
```

---

### 9.6 Icon Standards

**Font Awesome Icons (Consistent Usage):**

| Category | Icon | Usage |
|----------|------|-------|
| **Invoice** | `fas fa-file-invoice` | Invoice-related actions |
| **Payment** | `fas fa-money-bill` | Payment actions |
| **Print** | `fas fa-print` | Print/PDF actions |
| **Email** | `fas fa-envelope` | Email actions |
| **WhatsApp** | `fab fa-whatsapp` | WhatsApp actions |
| **View** | `fas fa-eye` | View details |
| **Edit** | `fas fa-edit` | Edit actions |
| **Delete/Void** | `fas fa-ban` | Destructive actions |
| **Success** | `fas fa-check-circle` | Success indicators |
| **Warning** | `fas fa-exclamation-triangle` | Warning indicators |
| **Info** | `fas fa-info-circle` | Informational |
| **Search** | `fas fa-search` | Search functionality |
| **Filter** | `fas fa-filter` | Filter functionality |
| **Export** | `fas fa-download` | Export actions |
| **Calendar** | `fas fa-calendar` | Date-related |
| **User** | `fas fa-user` | Patient/user-related |

---

### 9.7 Loading and Empty States

**Loading State:**
```html
<div class="flex justify-center items-center h-64">
    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
    <p class="ml-3 text-gray-600">Loading invoices...</p>
</div>
```

**Empty State:**
```html
<div class="flex flex-col justify-center items-center h-64">
    <i class="fas fa-file-invoice text-6xl text-gray-300 mb-4"></i>
    <h3 class="text-lg font-medium text-gray-900 mb-2">No invoices found</h3>
    <p class="text-sm text-gray-500 mb-4">Get started by creating your first invoice</p>
    <a href="/billing/invoice/create" class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">
        <i class="fas fa-plus mr-2"></i>Create Invoice
    </a>
</div>
```

---

### 9.8 Form Standards (Custom Create/Edit Routes)

**Form Layout:**
```html
<form class="space-y-6">
    <!-- Section 1 -->
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Patient Information</h3>

        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Patient Name *
                </label>
                <input type="text" required
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>

            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    MRN *
                </label>
                <input type="text" required
                       class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
        </div>
    </div>

    <!-- Submit Section -->
    <div class="flex justify-end space-x-3">
        <button type="button" class="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
            Cancel
        </button>
        <button type="submit" class="px-6 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700">
            Create Invoice
        </button>
    </div>
</form>
```

---

## 10. Development Guidelines and Constraints

### 10.1 CRITICAL Development Rules

This section outlines **mandatory** development guidelines that MUST be followed during the migration. These rules ensure code quality, maintainability, security, and alignment with the SkinSpire HMS architecture.

---

#### **10.1.1 Model Mixins (MANDATORY)**

##### **SoftDeleteMixin (Required for Deletion Operations)**

**Rule:** All entities that support deletion MUST use `SoftDeleteMixin` instead of hard deletes.

**Import:**
```python
from app.models.base import SoftDeleteMixin
```

**Model Definition:**
```python
class InvoiceHeader(db.Model, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = 'invoice_header'

    # SoftDeleteMixin provides:
    # - is_deleted: Boolean (default False)
    # - deleted_at: DateTime
    # - deleted_by: UUID
    # - soft_delete(user_id, reason): Method
    # - restore(user_id): Method
```

**Service Implementation:**
```python
def delete_invoice(self, invoice_id, user_id, reason, hospital_id):
    """
    Soft delete invoice using SoftDeleteMixin
    NEVER use session.delete() for entities with SoftDeleteMixin
    """
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).filter_by(
            invoice_id=invoice_id,
            hospital_id=hospital_id
        ).first()

        if not invoice:
            return {"success": False, "message": "Invoice not found"}

        # ✅ CORRECT: Use soft_delete method
        invoice.soft_delete(user_id=user_id, reason=reason)
        session.commit()

        # Invalidate cache
        invalidate_service_cache_for_entity('patient_invoices', cascade=False)

        return {"success": True, "message": "Invoice deleted successfully"}
```

**Database View Update (CRITICAL):**
When adding soft delete to an entity, you MUST update:
1. **SQL View Script**: Add `is_deleted`, `deleted_at`, `deleted_by` columns
2. **Python View Model**: Add corresponding Column definitions

```sql
-- ✅ CORRECT: Include soft delete fields in view
CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    ih.*,
    ih.is_deleted,
    ih.deleted_at,
    ih.deleted_by,
    -- ... other fields
FROM invoice_header ih
WHERE ih.hospital_id IS NOT NULL;
```

```python
# ✅ CORRECT: Add soft delete columns to view model
class PatientInvoiceView(Base):
    __tablename__ = 'patient_invoices_view'

    # ... other columns
    is_deleted = Column(Boolean)
    deleted_at = Column(DateTime)
    deleted_by = Column(UUID(as_uuid=True))
```

**Configuration:**
```python
# In patient_invoice_config.py
config = EntityConfiguration(
    # ... other settings
    enable_soft_delete=True,
    soft_delete_field="is_deleted",
    cascade_delete=False,
    delete_confirmation_message="Are you sure you want to delete this invoice?"
)
```

---

##### **ApprovalMixin (Required for Approval Workflows)**

**Rule:** All entities requiring approval workflows MUST use `ApprovalMixin`.

**Import:**
```python
from app.models.base import ApprovalMixin
```

**Model Definition:**
```python
class PaymentDetail(db.Model, TimestampMixin, TenantMixin, ApprovalMixin):
    __tablename__ = 'payment_details'

    # ApprovalMixin provides:
    # - approval_status: String (draft/pending/approved/rejected)
    # - approved_by: UUID
    # - approved_at: DateTime
    # - rejected_by: UUID
    # - rejected_at: DateTime
    # - approval_notes: Text
```

**Service Implementation:**
```python
def approve_payment(self, payment_id, approver_id, notes, hospital_id):
    """
    Approve payment using ApprovalMixin
    """
    with get_db_session() as session:
        payment = session.query(PaymentDetail).filter_by(
            payment_id=payment_id,
            hospital_id=hospital_id
        ).first()

        if payment.approval_status != 'pending':
            return {"success": False, "message": "Payment is not pending approval"}

        # ✅ CORRECT: Update approval fields
        payment.approval_status = 'approved'
        payment.approved_by = approver_id
        payment.approved_at = datetime.utcnow()
        payment.approval_notes = notes

        # Post GL entries after approval
        self._post_gl_entries(payment)

        session.commit()

        invalidate_service_cache_for_entity('patient_payments', cascade=False)

        return {"success": True, "message": "Payment approved successfully"}
```

---

#### **10.1.2 Database View Management (MANDATORY)**

**Rule:** Every time you create or modify a database view, you MUST update `app/models/views.py`.

**Process:**
1. Create SQL view script in `migrations/`
2. Add/update view model class in `app/models/views.py`
3. Register in `get_view_model()` function if new view
4. Apply SQL script to database
5. Test view model queries

**Example:**

**Step 1: Create SQL Script**
```sql
-- migrations/create_patient_invoices_view.sql
CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    ih.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    -- ... all required fields
FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id;
```

**Step 2: Add View Model**
```python
# app/models/views.py
class PatientInvoiceView(Base):
    """MUST match SQL view structure exactly"""
    __tablename__ = 'patient_invoices_view'
    __table_args__ = {'info': {'is_view': True}}

    # Define ALL columns from the view
    invoice_id = Column(UUID(as_uuid=True), primary_key=True)
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime)
    # ... all other columns
```

**Step 3: Register View (if new)**
```python
# app/models/views.py
def get_view_model(view_name: str):
    view_models = {
        # ... existing views
        'patient_invoices_view': PatientInvoiceView,  # ✅ ADD THIS
    }
    return view_models.get(view_name)
```

---

#### **10.1.3 Security and Permissions (MANDATORY)**

**Rule:** ALL routes MUST have security decorators. No exceptions.

**Required Decorators:**
```python
from flask_login import login_required
from app.security.decorators import require_web_branch_permission

# ✅ CORRECT: All routes protected
@billing_views_bp.route('/invoice/create', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('billing', 'create')
def create_invoice():
    # Implementation
```

**Permission Levels:**
- `can_view`: View list and detail
- `can_add`: Create new records
- `can_edit`: Modify existing records
- `can_delete`: Delete records
- `approve`: Approve workflows (if ApprovalMixin used)

**Hospital and Branch Scoping (CRITICAL):**
```python
# ✅ CORRECT: Always filter by hospital_id
def get_invoices(self, hospital_id, branch_id=None):
    with get_db_session() as session:
        query = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id
        )

        # Optional branch filtering
        if branch_id:
            query = query.filter_by(branch_id=branch_id)

        return query.all()
```

---

#### **10.1.4 Universal Engine Artifacts (DO NOT MODIFY)**

**Rule:** NEVER modify Universal Engine core files. Extend instead.

**Files that MUST NOT be modified:**
- `app/engine/universal_entity_service.py`
- `app/engine/universal_crud_service.py`
- `app/engine/universal_services.py`
- `app/views/universal_views.py`
- `app/templates/engine/universal_list.html`
- `app/templates/engine/universal_view.html`

**If you need custom behavior:**

**✅ CORRECT Approach 1: Extend Classes**
```python
# ✅ CORRECT: Inherit and extend
class PatientInvoiceService(UniversalEntityService):
    def __init__(self):
        super().__init__('patient_invoices', PatientInvoiceView)

    # Add custom methods, don't override inherited ones
    def create_invoice(self, data, hospital_id, branch_id, user_id):
        # Custom implementation
```

**✅ CORRECT Approach 2: Use Custom Renderers**
```python
# In configuration
FieldDefinition(
    name="line_items_display",
    field_type=FieldType.CUSTOM,
    custom_renderer=CustomRenderer(
        template="engine/business/invoice_line_items_table.html",
        context_function="get_invoice_lines"
    )
)
```

**✅ CORRECT Approach 3: Use Custom Routes**
```python
# Keep complex operations in custom routes
@billing_views_bp.route('/invoice/create', methods=['GET', 'POST'])
def create_invoice():
    # Custom implementation
```

---

#### **10.1.5 Database Service Methods (MANDATORY)**

**Rule:** Always use database service utility methods for session management and entity operations.

**Required Import:**
```python
from app.services.database_service import (
    get_db_session,
    get_entity_dict,
    get_detached_copy
)
```

**Session Management:**
```python
# ✅ CORRECT: Use context manager
def create_invoice(self, data, hospital_id, branch_id):
    with get_db_session() as session:
        invoice = InvoiceHeader(**data)
        session.add(invoice)
        session.commit()

        # Get detached copy before session closes
        invoice_dict = get_entity_dict(invoice)

    return {"success": True, "data": invoice_dict}

# ❌ WRONG: Manual session management
def create_invoice(self, data):
    session = Session()
    try:
        invoice = InvoiceHeader(**data)
        session.add(invoice)
        session.commit()
    finally:
        session.close()
```

**Detached Copy (For Passing Data Outside Session):**
```python
# ✅ CORRECT: Get detached copy for returning data
def get_invoice_by_id(self, invoice_id, hospital_id):
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).filter_by(
            invoice_id=invoice_id,
            hospital_id=hospital_id
        ).first()

        if not invoice:
            return None

        # Get detached copy before session closes
        detached_invoice = get_detached_copy(invoice)

    # Safe to use outside session
    return detached_invoice
```

**Entity to Dict Conversion:**
```python
# ✅ CORRECT: Use get_entity_dict for serialization
def search_invoices(self, filters, hospital_id):
    with get_db_session() as session:
        invoices = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id
        ).all()

        # Convert to dicts for JSON response
        invoice_dicts = [get_entity_dict(inv) for inv in invoices]

    return invoice_dicts
```

---

#### **10.1.6 SQL Guidelines (PostgreSQL)**

**Rule:** All SQL scripts MUST be PostgreSQL-compatible and avoid complex nesting.

**✅ CORRECT: Simple, Readable SQL**
```sql
-- Good: Simple joins, clear structure
CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    ih.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.grand_total,
    ih.paid_amount,
    ih.balance_due,
    p.full_name AS patient_name,
    p.mrn AS patient_mrn,
    b.name AS branch_name
FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id
LEFT JOIN branches b ON ih.branch_id = b.branch_id
WHERE ih.hospital_id IS NOT NULL;
```

**❌ WRONG: Complex Nested Queries**
```sql
-- Bad: Nested subqueries, hard to maintain
CREATE VIEW patient_invoices_view AS
SELECT *,
    (SELECT full_name FROM patients WHERE patient_id = (
        SELECT patient_id FROM invoice_header WHERE invoice_id = ih.invoice_id
    )) AS patient_name  -- ❌ Too complex!
FROM invoice_header ih;
```

**Views and Indexes: Allowed**
```sql
-- ✅ ALLOWED: Create views
CREATE VIEW patient_invoices_view AS ...

-- ✅ ALLOWED: Create indexes
CREATE INDEX idx_invoice_hospital_id ON invoice_header(hospital_id);
CREATE INDEX idx_invoice_date ON invoice_header(invoice_date);
```

**Triggers: NOT Allowed**
```sql
-- ❌ NOT ALLOWED: Avoid triggers
CREATE TRIGGER update_timestamp BEFORE UPDATE ON invoice_header ...
```

**Why?** Business logic belongs in Python services, not database triggers.

---

#### **10.1.7 Business Logic Location (MANDATORY)**

**Rule:** ALL business logic MUST be in Python services/controllers. NO business logic in database, templates, or JavaScript.

**✅ CORRECT Architecture:**

**Python Service (Business Logic):**
```python
def create_invoice(self, data, hospital_id, branch_id, user_id):
    """
    ✅ CORRECT: All validation and business logic in service
    """
    with get_db_session() as session:
        # Validation
        if data['grand_total'] <= 0:
            return {"success": False, "message": "Invoice total must be positive"}

        # Business rule: Check inventory
        for line_item in data['line_items']:
            if line_item['item_type'] == 'Medicine':
                available = self._check_medicine_stock(line_item['medicine_id'])
                if available < line_item['quantity']:
                    return {"success": False, "message": "Insufficient stock"}

        # Business rule: Calculate GST
        if data['is_gst_invoice']:
            data['tax_amount'] = data['total_amount'] * 0.18
            data['grand_total'] = data['total_amount'] + data['tax_amount']

        # Create invoice
        invoice = InvoiceHeader(**data)
        session.add(invoice)

        # Business rule: Update inventory
        self._update_inventory(data['line_items'], session)

        session.commit()
        invalidate_service_cache_for_entity('patient_invoices', cascade=False)

        return {"success": True, "data": get_entity_dict(invoice)}
```

**Template (Presentation ONLY):**
```html
<!-- ✅ CORRECT: Only display, no business logic -->
<div class="invoice-total">
    <label>Grand Total:</label>
    <span>₹{{ invoice.grand_total|number_format }}</span>
</div>

<!-- ❌ WRONG: Business logic in template -->
{% if invoice.grand_total > 10000 %}  <!-- Don't calculate thresholds here! -->
    <span class="requires-approval">Requires Approval</span>
{% endif %}
```

**JavaScript (Presentation/UX ONLY):**
```javascript
// ✅ CORRECT: UI behavior only
function toggleSection(sectionId) {
    document.getElementById(sectionId).classList.toggle('hidden');
}

// ❌ WRONG: Business logic in JavaScript
function calculateInvoiceTotal() {
    // Don't calculate totals in frontend!
    // This should be done in backend service
}
```

---

#### **10.1.8 Validation (Backend-First)**

**Rule:** Major validations MUST be in backend. Frontend validations are for UX only.

**✅ CORRECT: Backend Validation (Mandatory)**
```python
def record_payment(self, invoice_id, payment_data, user_id, hospital_id):
    """Backend validation is MANDATORY"""

    # Validation 1: Check invoice exists
    invoice = self._get_invoice(invoice_id, hospital_id)
    if not invoice:
        return {"success": False, "message": "Invoice not found"}

    # Validation 2: Check invoice not cancelled
    if invoice.is_cancelled:
        return {"success": False, "message": "Cannot pay cancelled invoice"}

    # Validation 3: Check payment amount
    total_methods = (
        payment_data.get('cash_amount', 0) +
        payment_data.get('credit_card_amount', 0) +
        payment_data.get('upi_amount', 0)
    )
    if abs(total_methods - payment_data['total_amount']) > 0.01:
        return {"success": False, "message": "Payment methods must sum to total amount"}

    # Validation 4: Check balance due
    if total_methods > invoice.balance_due:
        return {"success": False, "message": "Payment exceeds balance due"}

    # All validations passed, proceed with payment
    # ...
```

**✅ ALLOWED: Frontend Validation (UX Enhancement)**
```javascript
// Optional: Improve UX with frontend validation
function validatePaymentForm() {
    const cash = parseFloat(document.getElementById('cash_amount').value) || 0;
    const card = parseFloat(document.getElementById('card_amount').value) || 0;
    const upi = parseFloat(document.getElementById('upi_amount').value) || 0;
    const total = parseFloat(document.getElementById('total_amount').value);

    if (Math.abs((cash + card + upi) - total) > 0.01) {
        alert('Payment methods must sum to total amount');
        return false;
    }
    return true;
}
```

**IMPORTANT:** Frontend validation is for user experience ONLY. Backend MUST revalidate everything.

---

#### **10.1.9 Code Verification Before Implementation (CRITICAL)**

**Rule:** Before writing code, VERIFY that all fields, methods, and variables exist in the codebase.

**Checklist Before Coding:**

1. **✅ Verify Model Fields Exist**
```python
# Before using invoice.grand_total, check:
# 1. Open app/models/transaction.py
# 2. Find InvoiceHeader class
# 3. Confirm grand_total = Column(Numeric(12, 2)) exists

# ✅ CORRECT: Field exists in model
invoice.grand_total = data['grand_total']

# ❌ WRONG: Using non-existent field
invoice.invoice_amount = data['amount']  # No such field!
```

2. **✅ Verify View Model Columns Match View**
```python
# Before querying patient_invoices_view:
# 1. Check SQL view script has the column
# 2. Check PatientInvoiceView model has Column definition

# ✅ CORRECT: Both SQL view and model have patient_name
query = session.query(PatientInvoiceView).filter_by(patient_name="John")

# ❌ WRONG: Using column not in view
query = session.query(PatientInvoiceView).filter_by(patient_full_name="John")
```

3. **✅ Verify Methods Exist**
```python
# Before calling service.get_invoice_by_id():
# 1. Open app/services/billing_service.py
# 2. Confirm method exists
# 3. Check method signature matches

# ✅ CORRECT: Method exists with correct signature
result = invoice_service.get_invoice_by_id(invoice_id, hospital_id)

# ❌ WRONG: Method doesn't exist
result = invoice_service.get_invoice(invoice_id)  # No such method!
```

4. **✅ Verify Configuration Fields**
```python
# Before using configuration:
# 1. Check FieldDefinition name matches view column
# 2. Check field_type is appropriate

# ✅ CORRECT: Field name matches view column
FieldDefinition(
    name="grand_total",  # Matches PatientInvoiceView.grand_total
    field_type=FieldType.CURRENCY
)

# ❌ WRONG: Field name doesn't match model
FieldDefinition(
    name="total_amount",  # View has grand_total, not total_amount!
    field_type=FieldType.CURRENCY
)
```

---

#### **10.1.10 Backward Compatibility (MANDATORY)**

**Rule:** When modifying existing methods, maintain backward compatibility.

**✅ CORRECT: Backward Compatible Modification**
```python
# Original method
def get_invoices(self, hospital_id):
    # ... implementation

# ✅ CORRECT: Add optional parameter with default
def get_invoices(self, hospital_id, branch_id=None, include_cancelled=False):
    # New parameters are optional, existing calls still work
    query = session.query(InvoiceHeader).filter_by(hospital_id=hospital_id)

    if branch_id:
        query = query.filter_by(branch_id=branch_id)

    if not include_cancelled:
        query = query.filter_by(is_cancelled=False)

    return query.all()

# Old code still works:
invoices = service.get_invoices(hospital_id)  # ✅ Still valid

# New code can use new features:
invoices = service.get_invoices(hospital_id, branch_id=branch_id)  # ✅ Also valid
```

**❌ WRONG: Breaking Change**
```python
# Original method
def get_invoices(self, hospital_id):
    # ... implementation

# ❌ WRONG: Required parameter breaks existing code
def get_invoices(self, hospital_id, branch_id):  # branch_id now required!
    # ... implementation

# Old code breaks:
invoices = service.get_invoices(hospital_id)  # ❌ ERROR: Missing branch_id!
```

**Deprecation Pattern (If Breaking Change Necessary):**
```python
# Step 1: Create new method, keep old one
def get_invoices_by_branch(self, hospital_id, branch_id, include_cancelled=False):
    """New method with enhanced functionality"""
    # ... implementation

def get_invoices(self, hospital_id):
    """
    DEPRECATED: Use get_invoices_by_branch() instead
    This method will be removed in version 3.0
    """
    import warnings
    warnings.warn(
        "get_invoices() is deprecated. Use get_invoices_by_branch()",
        DeprecationWarning,
        stacklevel=2
    )
    return self.get_invoices_by_branch(hospital_id, branch_id=None)

# Step 2: Update all callers to use new method
# Step 3: Remove old method in next major version
```

---

### 10.2 Migration-Specific Guidelines

#### **10.2.1 Database View Creation Checklist**

For each view created, complete ALL steps:

- [ ] Create SQL script in `migrations/create_<view_name>.sql`
- [ ] Verify SQL is PostgreSQL-compatible
- [ ] Avoid complex nested queries
- [ ] Include all required columns
- [ ] Include soft delete fields if entity uses SoftDeleteMixin
- [ ] Include approval fields if entity uses ApprovalMixin
- [ ] Test view query performance (< 2s for 1000 records)
- [ ] Create view model class in `app/models/views.py`
- [ ] Match ALL columns exactly (name, type)
- [ ] Mark as read-only: `__table_args__ = {'info': {'is_view': True}}`
- [ ] Register in `get_view_model()` function
- [ ] Apply SQL script to test database
- [ ] Test view model queries from Python
- [ ] Create indexes on frequently filtered columns
- [ ] Document view purpose and usage

#### **10.2.2 Entity Configuration Checklist**

For each entity configuration:

- [ ] Verify ALL field names match view model columns
- [ ] Verify field types are appropriate (CURRENCY for amounts, etc.)
- [ ] Include soft delete fields if using SoftDeleteMixin
- [ ] Include approval fields if using ApprovalMixin
- [ ] Configure tabs logically (Details, Line Items, Workflow, System)
- [ ] Group fields into sections appropriately
- [ ] Define actions with correct permissions
- [ ] Use `url_pattern` not `route_name` in ActionDefinition
- [ ] Add confirmation for destructive actions
- [ ] Configure filters matching user needs
- [ ] Add summary cards for key metrics
- [ ] Configure document layouts
- [ ] Test configuration loads without errors
- [ ] Validate in Universal Engine list/detail views

#### **10.2.3 Service Refactoring Checklist**

When refactoring services:

- [ ] Extend `UniversalEntityService` (don't modify base class)
- [ ] Initialize with correct entity_type and view model
- [ ] Keep ALL existing custom methods unchanged
- [ ] Add cache invalidation to custom methods
- [ ] Use `invalidate_service_cache_for_entity()`
- [ ] Invalidate ALL affected entities (e.g., payments + invoices)
- [ ] Use database service methods (`get_db_session`, `get_entity_dict`, `get_detached_copy`)
- [ ] Verify all model fields exist before using
- [ ] Maintain backward compatibility
- [ ] Add security decorators to all routes
- [ ] Filter by hospital_id in all queries
- [ ] Filter by branch_id where applicable
- [ ] Use SoftDeleteMixin methods for deletion
- [ ] Use ApprovalMixin fields for workflows
- [ ] Write unit tests for new/modified methods

#### **10.2.4 Route Migration Checklist**

When migrating routes:

- [ ] Identify routes to migrate to Universal Engine (list, detail)
- [ ] Identify routes to keep custom (create, edit, workflow)
- [ ] Remove old list/detail routes
- [ ] Add URL redirects for backward compatibility
- [ ] Update navigation links to Universal Engine routes
- [ ] Ensure custom routes redirect to Universal detail view after operations
- [ ] Add security decorators to all custom routes
- [ ] Test all route transitions
- [ ] Verify no 404 errors
- [ ] Test backward compatibility redirects

---

### 10.3 Quality Assurance Checklist

Before committing code:

- [ ] All model fields used exist in model definition
- [ ] All view columns used exist in SQL view and view model
- [ ] All service methods called exist and have correct signatures
- [ ] All routes have security decorators
- [ ] All queries filter by hospital_id
- [ ] Cache invalidation added after data modifications
- [ ] SoftDeleteMixin used for deletions (not hard delete)
- [ ] ApprovalMixin fields used for approval workflows
- [ ] Database service methods used (get_db_session, etc.)
- [ ] SQL is PostgreSQL-compatible
- [ ] No business logic in templates or JavaScript
- [ ] Backend validations implemented
- [ ] Backward compatibility maintained
- [ ] No modifications to Universal Engine core files
- [ ] Code follows existing patterns from Supplier Module
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Documentation updated

---

## 11. Next Steps

### Immediate Actions (Week 1)
1. **Review this document** with development team
2. **Validate approach** with stakeholders
3. **Estimate effort** for each phase
4. **Assign resources** (developers, DBA, QA)
5. **Set timeline** with milestones

### Development Planning (Week 2)
1. **Create detailed task breakdown** (from high-level checklist)
2. **Set up development environment** (test database, test data)
3. **Review supplier module** implementations in detail
4. **Create prototype** for patient_invoices_view
5. **Validate prototype** with team

### Execution (Weeks 3-8)
1. **Phase 1:** Foundation (Week 3)
2. **Phase 2:** Configuration (Week 4-5)
3. **Phase 3:** Services (Week 6)
4. **Phase 4:** Routes/UI (Week 7)
5. **Phase 5:** Advanced Features (Week 8)

### Deployment (Week 9-10)
1. **Testing** in staging environment
2. **User training** and documentation
3. **Phased rollout** (soft launch → full deployment)
4. **Monitoring** and issue resolution

---

## 12. Conclusion

The migration of the Patient Billing Module to Universal Engine is a strategic initiative that will:

**Align** the billing module with the established architectural patterns
**Enhance** user experience with modern UI and advanced features
**Improve** maintainability through configuration-driven development
**Optimize** performance with database views and caching
**Reduce** technical debt and code duplication

The **hybrid approach** ensures that complex business logic remains in custom routes while leveraging Universal Engine for list/view operations. This migration follows the proven patterns from the Supplier Module, reducing risk and accelerating development.

**Recommended Decision:** Proceed with migration using the phased approach outlined in this document.

---

**Document Version History:**
- v1.0 (January 2025) - Initial migration approach document

**References:**
- Universal Engine Entity Configuration Complete Guide v6.0
- Universal Engine Entity Service Implementation Guide v3.0
- SkinSpire Clinic HMS Technical Development Guidelines v3.0
- Supplier Module Implementation (reference)
