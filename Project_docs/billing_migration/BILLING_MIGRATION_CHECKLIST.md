# Patient Billing Module - Universal Engine Migration Checklist

**Version:** 1.0
**Date:** January 2025
**Status:** Planning

---

## Overview

This checklist provides a high-level, phase-based tracking system for the Patient Billing Module migration to Universal Engine. Each phase has clear entry criteria, deliverables, and exit criteria.

**Migration Entities:**
1. Patient Invoices (primary)
2. Patient Payments (secondary)
3. Patient Advances (tertiary)

**Estimated Timeline:** 8-10 weeks

---

## Pre-Migration Preparation

### ☐ Planning & Setup
- [ ] Review BILLING_MIGRATION_APPROACH.md with entire team
- [ ] Review BILLING_TECHNICAL_SPECS.md for implementation details
- [ ] Get stakeholder approval for migration approach
- [ ] Assign team roles (Developer, DBA, QA, UX)
- [ ] Set up project timeline with milestones
- [ ] Create dedicated development branch (`feature/billing-universal-engine`)

### ☐ Environment Preparation
- [ ] Set up test database with copy of production data
- [ ] Configure test environment matching production
- [ ] Verify supplier module reference implementations work
- [ ] Set up monitoring for performance testing
- [ ] Prepare rollback scripts for each phase

### ☐ Knowledge Transfer
- [ ] Study supplier module implementations
- [ ] Review Universal Engine documentation (v6.0)
- [ ] Review entity configuration patterns
- [ ] Review service implementation patterns
- [ ] Understand custom renderer implementations

**Exit Criteria:** Team ready, environment prepared, knowledge acquired

---

## Phase 1: Foundation (Database Infrastructure)

**Estimated Duration:** 1 week
**Dependencies:** None
**Risk Level:** Low

### ☐ Database Views - Patient Invoices
- [ ] Create `patient_invoices_view.sql` migration script
- [ ] Include all required fields (invoice, patient, amounts, status)
- [ ] Add calculated fields (payment_status, invoice_age_days)
- [ ] Test view query performance (< 2s for 1000 records)
- [ ] Apply migration to test database
- [ ] Verify view returns correct data

### ☐ Database Views - Patient Payments
- [ ] Create `patient_payments_view.sql` migration script
- [ ] Include payment methods breakdown
- [ ] Join invoice and patient data
- [ ] Add payment status calculations
- [ ] Apply migration to test database
- [ ] Verify view returns correct data

### ☐ Database Views - Patient Advances
- [ ] Create `patient_advances_view.sql` migration script
- [ ] Include advance balance calculations
- [ ] Join patient data
- [ ] Add advance status fields
- [ ] Apply migration to test database
- [ ] Verify view returns correct data

### ☐ View Models (app/models/views.py)
- [ ] Add `class PatientInvoiceView(Base)` with all columns
- [ ] Add `class PatientPaymentView(Base)` with all columns
- [ ] Add `class PatientAdvanceView(Base)` with all columns
- [ ] Mark as read-only views (`__table_args__ = {'info': {'is_view': True}}`)
- [ ] Test view models can be queried from Python
- [ ] Update `get_view_model()` function if needed

### ☐ Entity Registry (app/config/entity_registry.py)
- [ ] Register `patient_invoices` entity
- [ ] Register `patient_payments` entity
- [ ] Register `patient_advances` entity
- [ ] Link to correct service classes
- [ ] Link to correct view models
- [ ] Set entity category to `TRANSACTION`

### ☐ Phase 1 Testing
- [ ] All views created successfully in database
- [ ] All view models query correctly from Python
- [ ] No errors when importing models
- [ ] No performance degradation on existing queries
- [ ] DBA review completed

**Exit Criteria:**
- All database views operational
- View models functional
- Entities registered
- Performance validated
- No errors in test environment

**Rollback Plan:** Drop views, remove view models, remove registry entries

---

## Phase 2: Entity Configuration

**Estimated Duration:** 2 weeks
**Dependencies:** Phase 1 complete
**Risk Level:** Medium

### ☐ Patient Invoice Configuration (patient_invoice_config.py)
- [ ] Create configuration file in `app/config/modules/`
- [ ] Define 50-60 field definitions (invoice, patient, amounts, status)
- [ ] Define 4-5 tabs (Invoice Details, Line Items, Payments, System Info)
- [ ] Define 10-15 sections within tabs
- [ ] Define 6-8 action definitions (view, print, void, payment, email, whatsapp)
- [ ] Define 8-12 filter definitions (status, type, patient, date, amount)
- [ ] Define 5-6 summary card definitions (revenue, outstanding, cancelled)
- [ ] Define document configurations (invoice print, receipt)
- [ ] Test configuration loads without errors

### ☐ Patient Payment Configuration (patient_payment_config.py)
- [ ] Create configuration file
- [ ] Define 40-50 field definitions (payment, invoice, patient, methods)
- [ ] Define 3-4 tabs (Payment Details, Invoice Info, Reconciliation)
- [ ] Define 8-12 sections within tabs
- [ ] Define 4-6 action definitions (view, print, refund, reconcile)
- [ ] Define 6-10 filter definitions (status, method, date, amount)
- [ ] Define 4-5 summary card definitions (collected, pending, refunded)
- [ ] Define document configurations (receipt, statement)
- [ ] Test configuration loads without errors

### ☐ Patient Advance Configuration (patient_advance_config.py)
- [ ] Create configuration file
- [ ] Define 30-40 field definitions (advance, patient, balance, applications)
- [ ] Define 3 tabs (Advance Details, Application History, Patient Info)
- [ ] Define 6-10 sections within tabs
- [ ] Define 4-5 action definitions (view, print, apply, refund)
- [ ] Define 6-8 filter definitions (status, patient, date, balance)
- [ ] Define 4 summary card definitions (total, available, applied)
- [ ] Test configuration loads without errors

### ☐ Custom Renderers (Preparation)
- [ ] Identify complex data displays needing custom renderers
- [ ] Plan line items table renderer (invoice line items)
- [ ] Plan payment history renderer (payment list in invoice detail)
- [ ] Plan advance application renderer (advance usage history)
- [ ] Document custom renderer requirements

### ☐ Phase 2 Testing
- [ ] All configurations load without errors
- [ ] Universal list views display correctly
- [ ] Universal detail views display correctly
- [ ] Tabs and sections render properly
- [ ] Filters work and return correct results
- [ ] Actions appear with correct visibility conditions
- [ ] Summary cards show accurate data
- [ ] No JavaScript errors in browser console
- [ ] Code review completed

**Exit Criteria:**
- All 3 entity configurations complete
- List/detail views functional
- Filters, actions, summaries working
- No configuration errors
- Code review approved

**Rollback Plan:** Revert configuration files

---

## Phase 3: Service Layer Refactoring

**Estimated Duration:** 1 week
**Dependencies:** Phase 2 complete
**Risk Level:** Medium

### ☐ Patient Invoice Service
- [ ] Refactor `BillingService` to `PatientInvoiceService(UniversalEntityService)`
- [ ] Initialize with `'patient_invoices'` entity type and `PatientInvoiceView` model
- [ ] Verify inherited `search_data()` uses view correctly
- [ ] Verify inherited `get_by_id()` returns complete data
- [ ] Keep `create_invoice()` as custom method (no changes)
- [ ] Keep `void_invoice()` as custom method (no changes)
- [ ] Add `get_invoice_lines()` method for custom renderer
- [ ] Add `get_payment_history()` method for custom renderer
- [ ] Add cache invalidation to all custom methods

### ☐ Patient Payment Service
- [ ] Create `PatientPaymentService(UniversalEntityService)`
- [ ] Initialize with `'patient_payments'` entity type and `PatientPaymentView` model
- [ ] Verify inherited methods work correctly
- [ ] Keep `record_payment()` as custom method
- [ ] Keep `issue_refund()` as custom method
- [ ] Add cache invalidation to custom methods

### ☐ Patient Advance Service
- [ ] Create `PatientAdvanceService(UniversalEntityService)`
- [ ] Initialize with `'patient_advances'` entity type and `PatientAdvanceView` model
- [ ] Verify inherited methods work correctly
- [ ] Keep `create_advance()` as custom method
- [ ] Keep `apply_advance()` as custom method
- [ ] Add `get_advance_applications()` method for custom renderer
- [ ] Add cache invalidation to custom methods

### ☐ Cache Strategy
- [ ] Review cache invalidation approach
- [ ] Update create operations to invalidate entity cache
- [ ] Update update operations to invalidate entity cache
- [ ] Update delete operations to invalidate entity cache
- [ ] Use `invalidate_service_cache_for_entity('entity_type', cascade=False)`
- [ ] Test cache invalidation works correctly

### ☐ Phase 3 Testing
- [ ] Service classes instantiate correctly
- [ ] `search_data()` returns correct results from view
- [ ] `get_by_id()` returns complete entity data
- [ ] Custom methods (create, void, payment, etc.) still work
- [ ] Cache invalidation triggers correctly
- [ ] Unit tests pass (existing + new)
- [ ] Integration tests pass
- [ ] No regressions in existing functionality

**Exit Criteria:**
- All 3 service classes operational
- Inherited methods functional
- Custom methods preserved
- Cache strategy working
- Tests passing
- No regressions

**Rollback Plan:** Keep old service classes, comment out new service classes

---

## Phase 4: Routes & UI Migration

**Estimated Duration:** 1 week
**Dependencies:** Phase 3 complete
**Risk Level:** High

### ☐ Route Changes (app/views/billing_views.py)
- [ ] Remove old list route: `/invoice/list`
- [ ] Remove old detail route: `/invoice/<id>`
- [ ] Remove old advance list route: `/invoice/advance/list`
- [ ] Keep create route: `/invoice/create`
- [ ] Keep payment route: `/invoice/<id>/payment`
- [ ] Keep void route: `/invoice/<id>/void`
- [ ] Keep email route: `/invoice/<id>/send-email`
- [ ] Keep whatsapp route: `/invoice/<id>/send-whatsapp`
- [ ] Keep advance create route: `/invoice/advance/create`
- [ ] Keep advance apply route: `/invoice/advance/apply/<id>`

### ☐ URL Redirects (Backward Compatibility)
- [ ] Add redirect: `/invoice/list` → `/universal/patient_invoices/list`
- [ ] Add redirect: `/invoice/<id>` → `/universal/patient_invoices/detail/<id>`
- [ ] Add redirect: `/invoice/advance/list` → `/universal/patient_advances/list`
- [ ] Test old URLs redirect correctly
- [ ] Add deprecation warnings to old routes

### ☐ Navigation Updates
- [ ] Update sidebar menu: Invoices → `/universal/patient_invoices/list`
- [ ] Update sidebar menu: Payments → `/universal/patient_payments/list`
- [ ] Update sidebar menu: Advances → `/universal/patient_advances/list`
- [ ] Update dashboard links if applicable
- [ ] Update breadcrumbs in custom templates
- [ ] Test all navigation paths

### ☐ Action Route Updates
- [ ] Update void action to redirect to `/universal/patient_invoices/detail/<id>` after completion
- [ ] Update payment action to redirect to Universal detail view
- [ ] Update advance apply action to redirect to Universal detail view
- [ ] Ensure all action success messages redirect to correct view
- [ ] Test all action flows (void, payment, advance)

### ☐ Template Cleanup
- [ ] Archive old list template: `invoice_list.html`
- [ ] Archive old detail template: `view_invoice.html`
- [ ] Archive old advance list template: `advance_payment_list.html`
- [ ] Keep custom form templates (create, payment, advance)
- [ ] Update custom templates to reference Universal detail view
- [ ] Remove unused template includes

### ☐ Phase 4 Testing
- [ ] List view accessible at `/universal/patient_invoices/list`
- [ ] Detail view accessible at `/universal/patient_invoices/detail/<id>`
- [ ] Payment list view accessible
- [ ] Advance list view accessible
- [ ] All filters work correctly
- [ ] All actions work (buttons navigate to custom routes)
- [ ] Custom routes (create, void, payment) still work
- [ ] No broken links in navigation
- [ ] No 404 errors
- [ ] Print/export functions work
- [ ] User acceptance testing passed

**Exit Criteria:**
- Universal Engine routes operational
- Custom routes functional
- Navigation updated
- No broken links
- All features accessible
- User acceptance approved

**Rollback Plan:** Restore old routes, revert navigation changes

---

## Phase 5: Advanced Features & Polish

**Estimated Duration:** 1 week
**Dependencies:** Phase 4 complete
**Risk Level:** Low

### ☐ Custom Renderers Implementation
- [ ] Implement line items table renderer
- [ ] Create template for line items display
- [ ] Implement payment history renderer
- [ ] Create template for payment history display
- [ ] Implement advance application history renderer
- [ ] Update entity configurations to use custom renderers
- [ ] Test custom renderers display correctly in detail view

### ☐ Document Configurations
- [ ] Configure invoice print layout (header, body, footer)
- [ ] Configure payment receipt layout
- [ ] Configure advance receipt layout
- [ ] Add signature fields to documents
- [ ] Add terms and conditions to documents
- [ ] Test print preview functionality
- [ ] Test PDF generation
- [ ] Review print layouts with business users

### ☐ Performance Optimization
- [ ] Create indexes on view columns (frequently filtered/sorted)
- [ ] Optimize view queries if needed
- [ ] Test with large datasets (10,000+ records)
- [ ] Measure list view load time (target: < 2s)
- [ ] Measure detail view load time (target: < 1s)
- [ ] Measure filter response time (target: < 1s)
- [ ] Measure export time (target: < 5s for 1,000 records)
- [ ] Address any performance issues

### ☐ User Training & Documentation
- [ ] Create user guide for new features
- [ ] Document differences from old UI
- [ ] Create training materials (screenshots, videos)
- [ ] Conduct training sessions with key users
- [ ] Gather feedback from training sessions
- [ ] Update internal wiki/documentation

### ☐ Final Testing
- [ ] Full regression testing (all billing features)
- [ ] Cross-browser testing (Chrome, Firefox, Edge)
- [ ] Mobile responsiveness testing
- [ ] Performance testing under load
- [ ] Security testing (permissions, access control)
- [ ] User acceptance testing (UAT)
- [ ] Gather and address UAT feedback

### ☐ Phase 5 Validation
- [ ] All custom renderers working
- [ ] All print layouts approved
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Training completed
- [ ] UAT passed
- [ ] Stakeholder sign-off obtained

**Exit Criteria:**
- Advanced features functional
- Performance optimized
- Users trained
- Documentation updated
- UAT approved
- Production ready

**Rollback Plan:** Disable custom renderers (use fallback), revert document configs

---

## Production Deployment

**Estimated Duration:** 1-2 weeks (phased rollout)
**Dependencies:** All phases complete
**Risk Level:** Medium

### ☐ Pre-Deployment Preparation
- [ ] Create production deployment plan
- [ ] Schedule deployment window (low-traffic period)
- [ ] Notify all stakeholders of deployment schedule
- [ ] Prepare rollback scripts
- [ ] Back up production database
- [ ] Verify staging environment matches production
- [ ] Final smoke test in staging

### ☐ Database Migration (Production)
- [ ] Apply database view migrations
- [ ] Verify views created successfully
- [ ] Test view performance on production data
- [ ] Create indexes on view columns
- [ ] Verify no impact on existing queries
- [ ] DBA sign-off

### ☐ Code Deployment
- [ ] Merge feature branch to main
- [ ] Deploy code to production
- [ ] Run post-deployment smoke tests
- [ ] Verify Universal Engine routes accessible
- [ ] Verify custom routes functional
- [ ] Verify no errors in application logs

### ☐ Phased Rollout (Optional)
- [ ] Phase 1: Enable for admin users only (1-2 days)
- [ ] Gather feedback from admin users
- [ ] Address any issues
- [ ] Phase 2: Enable for pilot group (3-5 days)
- [ ] Gather feedback from pilot users
- [ ] Address any issues
- [ ] Phase 3: Full rollout to all users
- [ ] Monitor closely for 1 week

### ☐ Post-Deployment Monitoring
- [ ] Monitor application logs for errors
- [ ] Monitor database performance
- [ ] Monitor user feedback/support tickets
- [ ] Track key metrics (page load times, error rates)
- [ ] Address any issues immediately
- [ ] Conduct post-deployment review

### ☐ Final Validation
- [ ] All features working in production
- [ ] No critical bugs reported
- [ ] Performance targets met
- [ ] User satisfaction acceptable
- [ ] Support team trained
- [ ] Migration complete

**Exit Criteria:**
- Production deployment successful
- All features operational
- No critical issues
- Users satisfied
- Migration project closed

**Rollback Plan:**
- Revert code deployment
- Keep database views (no data changes)
- Restore old routes and templates

---

## Post-Migration Activities

### ☐ Documentation & Knowledge Transfer
- [ ] Update technical documentation
- [ ] Update user documentation
- [ ] Create troubleshooting guide
- [ ] Document lessons learned
- [ ] Share knowledge with team
- [ ] Archive migration project documents

### ☐ Cleanup
- [ ] Remove old template files (after 3 months)
- [ ] Remove old route redirects (after 6 months)
- [ ] Clean up test data
- [ ] Archive migration branch
- [ ] Remove deprecated code

### ☐ Continuous Improvement
- [ ] Gather ongoing user feedback
- [ ] Monitor performance metrics
- [ ] Identify enhancement opportunities
- [ ] Plan future improvements
- [ ] Apply learnings to other modules

---

## Summary Statistics

### Phase Timeline
| Phase | Duration | Risk Level | Dependencies |
|-------|----------|------------|--------------|
| Phase 1: Foundation | 1 week | Low | None |
| Phase 2: Configuration | 2 weeks | Medium | Phase 1 |
| Phase 3: Services | 1 week | Medium | Phase 2 |
| Phase 4: Routes & UI | 1 week | High | Phase 3 |
| Phase 5: Advanced | 1 week | Low | Phase 4 |
| **Total Development** | **6 weeks** | | |
| Testing & UAT | 1 week | | Phase 5 |
| Deployment | 1 week | | UAT |
| **Total Project** | **8 weeks** | | |

### Deliverables Count
- Database Views: 3
- View Models: 3
- Entity Configurations: 3 (~2,900 lines total)
- Service Classes: 3 (refactored)
- Custom Renderers: 3
- Document Configurations: 6
- Test Cases: 50+
- Documentation Pages: 10+

### Success Metrics
- **Code Reduction:** 60-70% for list/view operations
- **Performance Improvement:** 30-50% faster queries (via views)
- **Feature Enhancement:** 10+ new features (filters, export, etc.)
- **User Satisfaction:** 8/10 or higher
- **Zero Downtime:** No production outages during migration

---

## Appendix: Quick Reference

### Key Files to Create/Modify
**New Files:**
- `migrations/create_patient_invoices_view.sql`
- `migrations/create_patient_payments_view.sql`
- `migrations/create_patient_advances_view.sql`
- `app/config/modules/patient_invoice_config.py`
- `app/config/modules/patient_payment_config.py`
- `app/config/modules/patient_advance_config.py`

**Modified Files:**
- `app/models/views.py` (add 3 view models)
- `app/config/entity_registry.py` (register 3 entities)
- `app/services/billing_service.py` (refactor to 3 service classes)
- `app/views/billing_views.py` (remove old routes, add redirects)
- `app/templates/base.html` or menu config (update navigation)

### Reference Documents
- BILLING_MIGRATION_APPROACH.md (this strategic document)
- BILLING_TECHNICAL_SPECS.md (implementation details)
- Universal Engine Entity Configuration Complete Guide v6.0
- Universal Engine Entity Service Implementation Guide v3.0
- Supplier Module implementations (reference patterns)

### Key Contacts
- Development Lead: [Name]
- Database Administrator: [Name]
- QA Lead: [Name]
- Business Analyst: [Name]
- Project Manager: [Name]

---

**Checklist Version History:**
- v1.0 (January 2025) - Initial migration checklist

**Last Updated:** [Date]
**Next Review:** After Phase 3 completion
