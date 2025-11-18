# Patient Payment Receipts Feature - Complete Design Document

**Version:** 1.0
**Date:** January 10, 2025
**Status:** In Development
**Author:** Claude Code (Design Assistant)

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Analysis](#requirements-analysis)
3. [Current State Assessment](#current-state-assessment)
4. [Architecture & Design](#architecture--design)
5. [Phase-by-Phase Implementation Plan](#phase-by-phase-implementation-plan)
6. [Database Schema](#database-schema)
7. [Service Layer Design](#service-layer-design)
8. [UI/UX Design](#uiux-design)
9. [API Endpoints](#api-endpoints)
10. [Testing Strategy](#testing-strategy)
11. [Deployment Guide](#deployment-guide)
12. [Appendix](#appendix)

---

## 📋 Executive Summary

### Project Overview

Build a comprehensive Patient Payment Receipts feature by **extending and enhancing the existing legacy billing payment system** (~50% reusable code) and adopting the **Supplier Payment UI pattern** for professional look and feel.

### Key Strategy: EXTEND, DON'T REBUILD

- ✅ Extend existing `PaymentDetail`, `PatientAdvancePayment`, `AdvanceAdjustment` tables
- ✅ Reuse working FIFO allocation logic from `apply_advance_payment()`
- ✅ Reuse GL posting functions (with approval gate added)
- ✅ Enhance existing templates following Supplier Payment UI pattern
- ✅ Add approval workflow (threshold: ₹100,000)
- ✅ Add package installment tracking (NEW feature)
- ✅ Add refund/reversal support

### Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Code Reuse | ~50% from legacy system | ✅ Achieved |
| Implementation Time | 5-6 weeks | 🟡 In Progress |
| Approval Threshold | ₹100,000 | ✅ Defined |
| UI Quality | Match Supplier Payment | 🟡 Planned |
| Test Coverage | >80% | 🔴 Pending |

---

## 🎯 Requirements Analysis

### Functional Requirements

#### FR-1: Payment Recording
- **FR-1.1**: User can record payments with multiple payment methods (Cash, Credit Card, Debit Card, UPI, Cheque, Bank Transfer)
- **FR-1.2**: System validates payment methods sum equals total amount (tolerance: ₹0.01)
- **FR-1.3**: User can save payment as draft or submit for approval/recording
- **FR-1.4**: System captures card details (last 4 digits, card type) for card payments
- **FR-1.5**: System captures UPI ID and transaction ID for UPI payments

#### FR-2: Multi-Invoice Payment Allocation
- **FR-2.1**: User sees all outstanding invoices for a patient in one screen
- **FR-2.2**: User can manually select invoices and specify amount for each (Manual Mode)
- **FR-2.3**: System can auto-allocate payment to oldest invoices first (FIFO Mode)
- **FR-2.4**: User can toggle between Manual and Auto-FIFO allocation modes
- **FR-2.5**: System shows real-time allocation summary

#### FR-3: Advance Payment Management
- **FR-3.1**: User can record advance payments (unallocated to invoices)
- **FR-3.2**: System tracks available advance balance per patient
- **FR-3.3**: System auto-allocates advance to future invoices (FIFO)
- **FR-3.4**: User can view advance payment history and current balance
- **FR-3.5**: System shows advance balance in payment recording screen

#### FR-4: Approval Workflow
- **FR-4.1**: Payments ≥ ₹100,000 require approval before GL posting
- **FR-4.2**: Approver can approve or reject pending payments with reason
- **FR-4.3**: System tracks approval history (who, when, reason)
- **FR-4.4**: Payments < ₹100,000 are auto-approved and posted immediately
- **FR-4.5**: Rejected payments can be edited and resubmitted

#### FR-5: Package Installment Plans
- **FR-5.1**: User can create installment plans for packages (e.g., 5-session Laser Hair Reduction)
- **FR-5.2**: System tracks installment schedule (installment number, due date, amount)
- **FR-5.3**: User can record payment against specific installments
- **FR-5.4**: System tracks paid vs. pending installments
- **FR-5.5**: System alerts on overdue installments

#### FR-6: Receipt Generation
- **FR-6.1**: System generates "Invoice cum Receipt" (invoice with payment details)
- **FR-6.2**: Receipt shows payment method breakdown
- **FR-6.3**: Receipt displays PAID stamp if fully paid
- **FR-6.4**: Receipt shows balance due if partially paid
- **FR-6.5**: Receipt includes signature blocks (Received By, Authorized By)

#### FR-7: Payment Reversal
- **FR-7.1**: User can reverse approved payments with reason
- **FR-7.2**: System creates reversing GL entries (opposite signs)
- **FR-7.3**: System restores invoice balance upon reversal
- **FR-7.4**: System tracks reversal history
- **FR-7.5**: Reversed payments cannot be reversed again

#### FR-8: Paytm Integration (Phase 2)
- **FR-8.1**: System integrates with Paytm card machine API
- **FR-8.2**: User can push payment request to machine
- **FR-8.3**: System auto-captures successful payment response
- **FR-8.4**: System handles failed/cancelled transactions
- **FR-8.5**: Manual entry fallback if machine unavailable

### Non-Functional Requirements

#### NFR-1: Performance
- Payment recording completes within 2 seconds
- List view loads within 1 second for 1000+ records
- Search/filter response within 500ms

#### NFR-2: Security
- Payment data encrypted in transit (HTTPS)
- Card details masked (only last 4 digits stored)
- Approval workflow audit trail immutable
- User permissions enforced (create, approve, view, reverse)

#### NFR-3: Usability
- UI follows Supplier Payment pattern (professional, intuitive)
- Real-time validation with helpful error messages
- Auto-allocation suggests optimal payment distribution
- Mobile-responsive design

#### NFR-4: Reliability
- Transaction consistency (all-or-nothing for GL posting)
- Automatic cache invalidation on data changes
- Error logging for troubleshooting
- Graceful degradation if services unavailable

#### NFR-5: Maintainability
- Code reuse from existing billing system (~50%)
- Follow Universal Engine patterns
- Comprehensive documentation
- Unit and integration tests

---

## 📊 Current State Assessment

### Existing Code Inventory

#### ✅ GREEN: Reusable As-Is (~50%)

| Component | Location | Status | Reuse Strategy |
|-----------|----------|--------|----------------|
| **PaymentDetail schema** | `app/models/transaction.py:632` | ✅ Good | Extend with workflow fields |
| **PatientAdvancePayment schema** | `app/models/transaction.py:1656` | ✅ Good | Extend with workflow fields |
| **AdvanceAdjustment schema** | `app/models/transaction.py:1700` | ✅ Good | Extend with GL tracking |
| **FIFO Allocation Logic** | `billing_service.py:apply_advance_payment()` | ✅ Works | Reuse as-is |
| **GL Posting Functions** | `gl_service.py:576, 1845` | ✅ Works | Add approval gate |
| **PaymentForm** | `billing_forms.py:223` | ✅ Good | Minor additions |
| **AdvancePaymentForm** | `billing_forms.py:303` | ✅ Good | Minor additions |
| **get_patient_advance_balance()** | `billing_service.py:3077` | ✅ Works | Reuse as-is |
| **get_patient_advance_payments()** | `billing_service.py:3121` | ✅ Works | Reuse as-is |

#### 🟡 YELLOW: Needs Modification (~30%)

| Component | Location | Issue | Modification Needed |
|-----------|----------|-------|---------------------|
| **record_payment()** | `billing_service.py:1960` | Auto-posts to GL | Add approval workflow logic |
| **create_advance_payment()** | `billing_service.py:2892` | Auto-posts to GL | Add approval workflow logic |
| **apply_advance_payment()** | `billing_service.py:3166` | No GL posting | Add GL adjustment posting |
| **record_invoice_payment route** | `billing_views.py:1025` | Complex redirects | Simplify + add approval UI |
| **payment_form.html** | `templates/billing/payment_form.html` | Basic styling | Enhance to match supplier UI |
| **advance_payment.html** | `templates/billing/advance_payment.html` | Basic styling | Enhance to match supplier UI |

#### 🔴 RED: Build From Scratch (~20%)

| Feature | Status | What Needs Building |
|---------|--------|---------------------|
| **Package Installment Tracking** | ❌ Not exists | NEW: PackagePaymentPlan + InstallmentPayment tables/models/service |
| **Approval Workflow** | ❌ Not exists | NEW: workflow_status fields, approve/reject functions, approval routes |
| **Draft Payment Support** | ❌ Not exists | NEW: Save without GL posting, edit before submission |
| **Payment Reversal** | ❌ Not exists | NEW: reverse_payment(), create reversing GL entries |
| **Advance Reversal** | ❌ Not exists | NEW: reverse_advance(), mark as inactive |
| **Payment Approval Template** | ❌ Not exists | NEW: payment_approval.html (follow supplier pattern) |
| **Payment View Template** | ❌ Not exists | NEW: payment_view.html (detail view with actions) |
| **Enhanced Payment Form** | ❌ Not exists | NEW: Redesign to 1200+ lines (supplier pattern) |

### Code Reuse Analysis

**Overall Reuse Ratio:**
- **GREEN (Reuse As-Is):** ~48%
- **YELLOW (Modify):** ~28%
- **RED (Build New):** ~24%

**Conclusion:** Nearly **50% code reuse** achieved, significantly reducing development time and risk.

---

## 🏗️ Architecture & Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                       │
│  (Enhanced Payment Form, Approval View, Receipt Print)           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Views & Controllers Layer                    │
│  billing_views.py: record_payment_enhanced(), approve_payment()   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                              │
│  billing_service.py: record_payment(), approve_payment(),         │
│                      reverse_payment()                            │
│  package_payment_service.py: create_installment_plan()            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Access Layer (ORM)                       │
│  Models: PaymentDetail, PatientAdvancePayment,                   │
│          AdvanceAdjustment, PackagePaymentPlan                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Database (PostgreSQL)                       │
│  Tables: payment_details, patient_advance_payments,               │
│          advance_adjustments, package_payment_plans               │
│  Views: v_patient_payment_receipts                                │
└─────────────────────────────────────────────────────────────────┘
```

### Workflow State Machine

#### Payment Workflow

```
         ┌─────────┐
         │  DRAFT  │ (save_as_draft=True)
         └────┬────┘
              │ submit
              ▼
    ┌──────────────────┐
    │ PENDING_APPROVAL │ (amount ≥ ₹100K)
    └────┬────────┬────┘
         │        │
    approve   reject
         │        │
         ▼        ▼
   ┌──────────┐ ┌──────────┐
   │ APPROVED │ │ REJECTED │
   └────┬─────┘ └────┬─────┘
        │            │ edit & resubmit
        │            └──────────┐
        │ reverse               │
        ▼                       ▼
   ┌──────────┐           ┌─────────┐
   │ REVERSED │◄──────────┤  DRAFT  │
   └──────────┘           └─────────┘

   Auto-path for small payments:
   DRAFT → APPROVED (if amount < ₹100K)
```

### Data Flow Diagrams

#### Payment Recording Flow

```
User Input (Form)
    │
    ├─ Invoice Selection
    ├─ Payment Date
    ├─ Payment Methods (Cash, Card, UPI)
    ├─ Card/UPI Details
    └─ Allocation Mode (Manual/Auto-FIFO)
    │
    ▼
Validation
    │
    ├─ Methods sum = Total? ✓
    ├─ Card details if card payment? ✓
    ├─ UPI ID if UPI payment? ✓
    └─ Amount > 0? ✓
    │
    ▼
Service Layer (record_payment)
    │
    ├─ Calculate total_amount
    ├─ Determine workflow_status
    │   ├─ If amount ≥ ₹100K → pending_approval
    │   └─ If amount < ₹100K → approved
    ├─ Create PaymentDetail record
    └─ If approved:
        ├─ Update invoice balances
        ├─ Post GL entries
        └─ Create AR subledger entry
    │
    ▼
Cache Invalidation
    │
    ├─ invalidate_service_cache_for_entity('payment_details')
    └─ invalidate_service_cache_for_entity('patient_invoices')
    │
    ▼
Response
    │
    ├─ Success → Redirect to payment detail view
    └─ Error → Show validation errors
```

#### Approval Workflow Flow

```
Pending Payment
    │
    ▼
Approver Reviews
    │
    ├─ View payment details
    ├─ View invoice details
    └─ Decide: Approve or Reject
    │
    ▼
Approve Path                    Reject Path
    │                               │
    ├─ Update status → approved     ├─ Update status → rejected
    ├─ Set approved_by, approved_at ├─ Set rejected_by, rejected_at
    ├─ Update invoice balances      ├─ Set rejection_reason
    ├─ Post GL entries              └─ END (can edit & resubmit)
    ├─ Set gl_posted = TRUE
    └─ Create AR subledger entry
    │
    ▼
Cache Invalidation
    │
    └─ invalidate_service_cache_for_entity('payment_details')
```

---

## 📅 Phase-by-Phase Implementation Plan

### Phase 1: Database Schema Extensions ✅ COMPLETED

**Duration:** Week 1
**Status:** ✅ Complete

#### Deliverables

1. ✅ **Migration Script:** `add_payment_receipt_workflow_fields.sql`
   - Extends `payment_details` with 20+ workflow fields
   - Extends `patient_advance_payments` with workflow + branch fields
   - Extends `advance_adjustments` with GL tracking
   - Creates 8 performance indexes
   - Sets defaults for existing data

2. ✅ **Database View:** `create_patient_payment_receipts_view.sql`
   - Creates `v_patient_payment_receipts` view
   - Joins 6 tables (payment_details, invoice_header, patient, hospital, branches, users)
   - Provides 50+ fields for comprehensive reporting
   - Includes aging buckets and audit trail

#### Files Created

- ✅ `migrations/add_payment_receipt_workflow_fields.sql`
- ✅ `migrations/create_patient_payment_receipts_view.sql`

#### Next Steps

- User applies migration scripts to database
- Verify migrations with provided verification queries

---

### Phase 2: Model Updates (Week 1-2)

**Duration:** Week 1-2
**Status:** 🟡 Ready to Start

#### Objectives

- Update Python models to reflect new database schema
- Add ApprovalMixin to payment models
- Create view model for PatientPaymentReceiptView
- Ensure backward compatibility

#### Tasks

1. **Update PaymentDetail Model**
   - File: `app/models/transaction.py` (lines 632-688)
   - Add `ApprovalMixin` inheritance
   - Add workflow fields (workflow_status, requires_approval, etc.)
   - Add reversal tracking fields
   - Add soft delete fields

2. **Update PatientAdvancePayment Model**
   - File: `app/models/transaction.py` (lines 1656-1698)
   - Add `ApprovalMixin` inheritance
   - Add workflow fields
   - Add branch_id field

3. **Update AdvanceAdjustment Model**
   - File: `app/models/transaction.py` (lines 1700-1720)
   - Add gl_entry_id field
   - Add reversal tracking fields

4. **Create PatientPaymentReceiptView Model**
   - File: `app/models/views.py`
   - Map to `v_patient_payment_receipts` view
   - Define all 50+ fields
   - Mark as read-only view

5. **Update get_view_model() Function**
   - File: `app/models/views.py`
   - Register PatientPaymentReceiptView

#### Acceptance Criteria

- [ ] Models successfully load without errors
- [ ] ORM can query payment_details with new fields
- [ ] View model can query v_patient_payment_receipts
- [ ] Backward compatibility maintained (existing code doesn't break)

---

### Phase 3: Service Layer Enhancements (Week 2-3)

**Duration:** Week 2-3
**Status:** 🔴 Pending

#### Objectives

- Modify `record_payment()` to add approval workflow
- Create new approval workflow functions
- Add reversal support
- Maintain backward compatibility

#### Tasks

1. **Modify record_payment() Function**
   - File: `app/services/billing_service.py` (lines 1960-2010)
   - Add parameters: `save_as_draft`, `approval_threshold`
   - Add workflow status determination logic
   - Conditional GL posting (only if approved)
   - Update invoice balances only if approved

2. **Create approve_payment() Function**
   - File: `app/services/billing_service.py` (new)
   - Validate payment is pending_approval
   - Update workflow_status to approved
   - Update invoice balances
   - Post GL entries
   - Create AR subledger entry
   - Invalidate caches

3. **Create reject_payment() Function**
   - File: `app/services/billing_service.py` (new)
   - Validate payment is pending_approval
   - Update workflow_status to rejected
   - Record rejection reason
   - Invalidate caches

4. **Create reverse_payment() Function**
   - File: `app/services/billing_service.py` (new)
   - Validate payment is approved and gl_posted
   - Create reversing GL entries
   - Restore invoice balances
   - Mark payment as reversed
   - Invalidate caches

5. **Modify create_advance_payment() Function**
   - File: `app/services/billing_service.py` (lines 2892-2951)
   - Add approval workflow logic (similar to record_payment)

6. **Create create_reversing_gl_entries() Function**
   - File: `app/services/gl_service.py` (new)
   - Copy original GL entries
   - Reverse signs (DR ↔ CR)
   - Link to original transaction
   - Mark original as reversed

#### Acceptance Criteria

- [ ] record_payment() supports draft and approval workflow
- [ ] Payments < ₹100K are auto-approved
- [ ] Payments ≥ ₹100K are pending_approval
- [ ] approve_payment() successfully posts GL entries
- [ ] reject_payment() records rejection reason
- [ ] reverse_payment() creates reversing GL entries
- [ ] All functions have proper error handling
- [ ] Cache invalidation works correctly

---

### Phase 4: Routes & Controllers (Week 2-3)

**Duration:** Week 2-3
**Status:** 🔴 Pending

#### Objectives

- Create new routes for approval workflow
- Create new routes for reversal
- Enhance existing payment recording route
- Add payment detail view route

#### Tasks

1. **Create Enhanced Payment Recording Route**
   - File: `app/views/billing_views.py` (new)
   - Route: `/billing/payment/record` [GET, POST]
   - Route: `/billing/payment/record/<invoice_id>` [GET, POST]
   - Support multi-invoice payment
   - Support draft saving
   - Support allocation mode selection

2. **Create Approval Route**
   - File: `app/views/billing_views.py` (new)
   - Route: `/billing/payment/approve/<payment_id>` [GET, POST]
   - GET: Show approval confirmation page
   - POST: Call approve_payment() service
   - Permission required: `billing.approve`

3. **Create Rejection Route**
   - File: `app/views/billing_views.py` (new)
   - Route: `/billing/payment/reject/<payment_id>` [POST]
   - Require rejection_reason parameter
   - Call reject_payment() service
   - Permission required: `billing.approve`

4. **Create Reversal Route**
   - File: `app/views/billing_views.py` (new)
   - Route: `/billing/payment/reverse/<payment_id>` [GET, POST]
   - GET: Show reversal confirmation page
   - POST: Call reverse_payment() service
   - Permission required: `billing.reverse`

5. **Create Payment Detail View Route**
   - File: `app/views/billing_views.py` (new)
   - Route: `/billing/payment/view/<payment_id>` [GET]
   - Show comprehensive payment details
   - Show workflow status and history
   - Show action buttons (Approve, Reject, Reverse, Print)

6. **Create Payment List Route**
   - Route: `/universal/patient_payment_receipts/list`
   - Use Universal Engine
   - Configure filters (date range, status, patient, amount)

#### Acceptance Criteria

- [ ] Enhanced payment form loads without errors
- [ ] User can save payment as draft
- [ ] User can submit payment for approval/recording
- [ ] Approver can approve/reject pending payments
- [ ] User can reverse approved payments
- [ ] Payment detail view shows all information
- [ ] All routes enforce proper permissions

---

### Phase 5: UI Enhancement (Week 3-4)

**Duration:** Week 3-4
**Status:** 🔴 Pending

#### Objectives

- Redesign payment form following Supplier Payment pattern
- Create approval view template
- Create payment detail view template
- Enhance existing templates

#### Tasks

1. **Create Enhanced Payment Form**
   - File: `app/templates/billing/payment_form_enhanced.html` (new, 1200+ lines)
   - Follow `supplier/payment_form.html` pattern
   - Sections:
     - Enhanced header with status badge
     - Quick actions bar
     - Patient outstanding invoices section (NEW)
     - Advance balance section
     - Payment method distribution
     - Invoice allocation summary
     - Payment summary
     - Bottom action buttons
   - JavaScript features:
     - Fetch patient outstanding invoices
     - Calculate total dues
     - Auto-allocate logic (advance first, then cash)
     - Manual allocation mode (checkboxes + amount fields)
     - Auto-FIFO mode (system allocates to oldest)
     - Real-time validation
     - Payment summary updates

2. **Create Payment Approval Template**
   - File: `app/templates/billing/payment_approval.html` (new)
   - Follow `supplier/payment_approval_new.html` pattern
   - Show payment details
   - Show invoice details
   - Show payment method breakdown
   - Approval/Reject buttons
   - Reason textarea (for rejection)

3. **Create Payment Detail View Template**
   - File: `app/templates/billing/payment_view.html` (new)
   - Follow `supplier/payment_view.html` pattern
   - Comprehensive payment details
   - Workflow status badges
   - Approval history timeline
   - Action buttons (Reverse, Print Receipt)
   - GL entry reference

4. **Create Payment Reversal Template**
   - File: `app/templates/billing/payment_reversal.html` (new)
   - Confirmation page
   - Show payment details
   - Reversal reason textarea
   - Confirm/Cancel buttons

5. **Enhance Existing Advance Payment Template**
   - File: `app/templates/billing/advance_payment.html` (modify)
   - Add professional styling
   - Add advance balance display
   - Add validation feedback

#### UI Components Breakdown

**Enhanced Payment Form Structure:**

```html
<div class="payment-enhanced-container">
  <!-- Header -->
  <div class="payment-header">
    <h1>Record Payment</h1>
    <span class="badge badge-draft">New Payment</span>
  </div>

  <!-- Quick Actions -->
  <div class="quick-actions-bar">
    <button>Back</button>
    <button>Reset</button>
  </div>

  <!-- Section 1: Basic Information -->
  <div class="universal-filter-card">
    <div class="universal-filter-card-header">
      <h3>Basic Information</h3>
    </div>
    <div class="universal-filter-card-body">
      <!-- Invoice selection, payment date -->
    </div>
  </div>

  <!-- Section 2: Outstanding Invoices (NEW) -->
  <div class="universal-filter-card">
    <div class="universal-filter-card-header">
      <h3>Outstanding Invoices</h3>
      <toggle>Manual / Auto-FIFO</toggle>
    </div>
    <div class="universal-filter-card-body">
      <table>
        <thead>
          <tr>
            <th>Select</th>
            <th>Invoice Number</th>
            <th>Invoice Date</th>
            <th>Total Amount</th>
            <th>Paid Amount</th>
            <th>Balance Due</th>
            <th>Allocate Amount</th>
          </tr>
        </thead>
        <tbody>
          <!-- Populated via JavaScript -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- Section 3: Advance Balance (conditional) -->
  <div id="advance-balance-section" style="display: none;">
    <div class="universal-filter-card advance-info-section">
      <div class="universal-filter-card-header">
        <h3><i class="fas fa-piggy-bank"></i> Available Advance Balance</h3>
      </div>
      <div class="universal-filter-card-body">
        <div class="advance-balance-display">
          ₹<span id="advance-balance-amount">0.00</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Section 4: Payment Method Distribution -->
  <div class="universal-filter-card">
    <div class="universal-filter-card-header">
      <h3>Payment Method Distribution</h3>
    </div>
    <div class="universal-filter-card-body">
      <!-- Advance allocation field (conditional) -->
      <div id="advance-allocation-field" style="display: none;">
        <label>Allocate from Advance Balance</label>
        <input type="number" name="advance_allocation_amount">
      </div>

      <!-- Payment methods (2x2 grid) -->
      <div class="payment-two-column-grid">
        <div><input type="number" name="cash_amount"></div>
        <div><input type="number" name="credit_card_amount"></div>
        <div><input type="number" name="debit_card_amount"></div>
        <div><input type="number" name="upi_amount"></div>
      </div>

      <!-- Conditional card details -->
      <div id="card-details" style="display: none;">
        <input type="text" name="card_number_last4">
        <select name="card_type">...</select>
      </div>

      <!-- Conditional UPI details -->
      <div id="upi-details" style="display: none;">
        <input type="text" name="upi_id">
      </div>

      <!-- Payment summary -->
      <div id="payment-summary">
        <h4>Payment Summary</h4>
        <div id="summary-content">
          <!-- Populated via JavaScript -->
        </div>
      </div>

      <!-- Validation message -->
      <div id="validation-message"></div>
    </div>
  </div>

  <!-- Section 5: Invoice Line Items (conditional) -->
  <div id="invoice-items-section" style="display: none;">
    <table>
      <!-- Invoice line items preview -->
    </table>
  </div>

  <!-- Bottom Actions -->
  <div class="bottom-actions">
    <button class="btn-secondary">Cancel</button>
    <button type="submit" name="save_as" value="draft" class="btn-outline">
      Save as Draft
    </button>
    <button type="submit" name="save_as" value="submit" class="btn-primary">
      Record Payment
    </button>
  </div>
</div>
```

#### JavaScript Logic

```javascript
// Key JavaScript functions
- handleInvoiceChange()           // Fetch invoice data when selected
- fetchPatientOutstandingInvoices() // Load all outstanding invoices
- fetchPatientAdvanceBalance()     // Check advance balance
- toggleAllocationMode()           // Switch Manual ↔ Auto-FIFO
- autoAllocatePayment()            // FIFO allocation logic
- manualAllocationUpdate()         // Manual checkbox/amount handling
- toggleMethodDetails()            // Show/hide card/UPI details
- updateSummary()                  // Recalculate payment summary
- validateAmounts()                // Real-time validation
```

#### Acceptance Criteria

- [ ] Enhanced payment form loads with professional styling
- [ ] User can see all outstanding invoices
- [ ] User can toggle Manual/Auto-FIFO allocation mode
- [ ] Advance balance section shows when advance available
- [ ] Auto-allocation logic works correctly
- [ ] Manual allocation allows checkbox selection
- [ ] Payment method details show/hide correctly
- [ ] Real-time validation provides helpful feedback
- [ ] Payment summary updates in real-time
- [ ] Approval template shows all payment details
- [ ] Reversal template requires reason
- [ ] UI matches Supplier Payment quality

---

### Phase 6: Package Installment Tracking (Week 4)

**Duration:** Week 4
**Status:** 🔴 Pending

#### Objectives

- Create database tables for package installments
- Create models for package payment plans
- Create service functions for installment management
- Create UI for installment plan creation and payment

#### Tasks

1. **Create Database Tables**
   - File: `migrations/create_package_installment_tables.sql` (new)
   - Table: `package_payment_plans`
     - plan_id, hospital_id, branch_id, patient_id
     - package_name, package_description, total_sessions
     - total_amount, paid_amount, balance_amount
     - installment_count, first_payment_date, frequency
     - status (active, completed, cancelled)
   - Table: `installment_payments`
     - installment_id, hospital_id, plan_id
     - installment_number, due_date, amount
     - paid_date, paid_amount, payment_id
     - status (pending, paid, overdue, waived)

2. **Create Models**
   - File: `app/models/transaction.py` (add at end)
   - Model: `PackagePaymentPlan`
   - Model: `InstallmentPayment`

3. **Create Service**
   - File: `app/services/package_payment_service.py` (new)
   - Function: `create_package_payment_plan()`
   - Function: `record_installment_payment()`
   - Function: `get_package_payment_plans()`
   - Function: `get_overdue_installments()`

4. **Create Routes**
   - File: `app/views/billing_views.py` (add)
   - Route: `/billing/package/installment/create` [GET, POST]
   - Route: `/billing/package/installment/<plan_id>/pay/<installment_number>` [GET, POST]
   - Route: `/billing/package/installment/<plan_id>` [GET]

5. **Create Templates**
   - File: `app/templates/billing/package_installment_create.html` (new)
   - File: `app/templates/billing/package_installment_pay.html` (new)
   - File: `app/templates/billing/package_installment_view.html` (new)

#### Installment Plan Structure

```
Package: Laser Hair Reduction (5 sessions)
Total Amount: ₹50,000
Installments: 3

Installment Schedule:
┌───────────────┬──────────────┬────────────┬─────────────┬──────────┐
│ Installment # │ Due Date     │ Amount     │ Status      │ Paid On  │
├───────────────┼──────────────┼────────────┼─────────────┼──────────┤
│ 1             │ 2025-01-15   │ ₹20,000    │ PAID        │ Jan 15   │
│ 2             │ 2025-02-15   │ ₹15,000    │ PAID        │ Feb 10   │
│ 3             │ 2025-03-15   │ ₹15,000    │ PENDING     │ -        │
└───────────────┴──────────────┴────────────┴─────────────┴──────────┘

Sessions Completed: 3 / 5
```

#### Acceptance Criteria

- [ ] Package installment plan can be created
- [ ] Installment schedule is auto-generated
- [ ] User can pay specific installment
- [ ] Payment links to installment_payment record
- [ ] Plan status updates when all installments paid
- [ ] Overdue installments are highlighted
- [ ] Sessions completed tracked separately from payments

---

### Phase 7: Universal Engine Integration (Week 4-5)

**Duration:** Week 4-5
**Status:** 🔴 Pending

#### Objectives

- Create entity configuration for patient_payment_receipts
- Register entity in entity_registry
- Configure fields, sections, tabs, actions, filters
- Test list/detail views

#### Tasks

1. **Create Entity Configuration**
   - File: `app/config/modules/patient_payment_receipt_config.py` (new, 2000+ lines)
   - Based on: `supplier_payment_config.py` pattern
   - Define 60+ fields
   - Define 6 sections
   - Define 10 actions
   - Define 10 summary cards
   - Define comprehensive filters

2. **Register Entity**
   - File: `app/config/entity_registry.py` (modify)
   - Add `patient_payment_receipts` registration
   - Link to PatientPaymentReceiptView model
   - Link to billing_service (reuse existing)

3. **Configure Fields**
   - Payment identification fields
   - Payment method fields
   - Workflow status fields
   - Approval tracking fields
   - GL posting fields
   - Reversal tracking fields
   - Audit fields

4. **Configure Sections**
   - Receipt Details
   - Invoice Allocation
   - Payment Methods
   - Advance Payment
   - Workflow
   - GL Posting
   - Documents
   - System Info

5. **Configure Actions**
   - View (Universal Engine)
   - Approve (Custom route)
   - Reject (Custom route)
   - Reverse (Custom route)
   - Print Receipt (Custom route)
   - Email Receipt (Custom route)
   - Export (Excel, PDF)

6. **Configure Filters**
   - Date range (payment_date)
   - Payment method (cash, card, UPI)
   - Patient (autocomplete)
   - Workflow status
   - Amount range
   - GL posted (yes/no)
   - Reversed (yes/no)

7. **Configure Summary Cards**
   - Total Receipts
   - Total Amount
   - By Status (Approved, Pending, Rejected, Reversed)
   - By Method (Cash, Card, UPI)
   - GL Posted Count
   - Reversal Count

#### Acceptance Criteria

- [ ] Entity registered successfully
- [ ] List view loads with records
- [ ] Filters work correctly
- [ ] Summary cards show accurate counts
- [ ] Detail view shows all sections
- [ ] Actions buttons visible and working
- [ ] Search/sort works
- [ ] Export works (Excel, PDF)

---

### Phase 8: Receipt Printing (Week 5)

**Duration:** Week 5
**Status:** 🔴 Pending

#### Objectives

- Extend existing invoice print template to add payment section
- Generate "Invoice cum Receipt" document
- Support PDF generation
- Support email sending

#### Tasks

1. **Extend Invoice Print Template**
   - File: `app/templates/billing/print_invoice.html` (modify)
   - Add PAID watermark (if fully paid)
   - Add "Payment Received" section:
     - Receipt number (payment_id or generated)
     - Receipt date (payment_date)
     - Payment method breakdown table
     - Total Paid: ₹XX,XXX.XX
     - Balance Due: ₹X,XXX.XX (if partial)
   - Add signature blocks: Received By, Authorized By
   - Add footer: "This is a computer-generated receipt"

2. **Create Print Route**
   - File: `app/views/billing_views.py` (add)
   - Route: `/billing/payment/<payment_id>/print` [GET]
   - Fetch payment and invoice data
   - Render print_invoice.html with payment data

3. **Create PDF Generation Service**
   - File: `app/services/invoice_document_service.py` (modify)
   - Function: `generate_invoice_cum_receipt_pdf()`
   - Use existing PDF generation logic
   - Add payment section to PDF

4. **Create Email Service**
   - File: `app/services/email_service.py` (modify)
   - Function: `send_payment_receipt_email()`
   - Attach PDF receipt
   - Email to patient email address

#### Receipt Layout

```
┌─────────────────────────────────────────────────────────────┐
│                      HOSPITAL LOGO                           │
│                   Hospital Name, Address                     │
│                   GSTIN: XXXXXXXXXXXXXXX                     │
├─────────────────────────────────────────────────────────────┤
│                    INVOICE CUM RECEIPT                       │
├─────────────────────────────────────────────────────────────┤
│ Invoice No: INV-2025-01-001    Date: 10-Jan-2025           │
│ Patient: John Doe              MRN: PAT0001                 │
├─────────────────────────────────────────────────────────────┤
│ LINE ITEMS                                                   │
│                                                              │
│ Sr  Item Name          Qty  Price    Disc%  GST    Total   │
│ ──────────────────────────────────────────────────────────  │
│ 1   Consultation       1    ₹500     0%     18%    ₹590    │
│ 2   Medicine ABC       2    ₹100     10%    12%    ₹202    │
│ ──────────────────────────────────────────────────────────  │
│                                          Subtotal:  ₹680    │
│                                          CGST:      ₹61     │
│                                          SGST:      ₹61     │
│                                          ──────────────────  │
│                                          GRAND TOTAL: ₹802  │
├─────────────────────────────────────────────────────────────┤
│                    PAYMENT RECEIVED                          │
│ ──────────────────────────────────────────────────────────  │
│ Receipt Date: 10-Jan-2025                                   │
│ Payment Method Breakdown:                                    │
│   Cash:         ₹500                                        │
│   Credit Card:  ₹302 (XXXX1234 - Visa)                     │
│   Total Paid:   ₹802                                        │
│   Balance Due:  ₹0                       ┌─────────────────┐│
│                                          │      PAID       ││
│ ──────────────────────────────────────  │  [WATERMARK]    ││
│ Received By: ______________             └─────────────────┘│
│ Authorized By: ____________                                 │
├─────────────────────────────────────────────────────────────┤
│ This is a computer-generated receipt.                        │
│ Generated on: 10-Jan-2025 14:30:15                          │
└─────────────────────────────────────────────────────────────┘
```

#### Acceptance Criteria

- [ ] Invoice cum receipt prints correctly
- [ ] Payment section shows all payment methods
- [ ] PAID watermark appears if fully paid
- [ ] Balance due shown if partially paid
- [ ] Signature blocks present
- [ ] PDF generation works
- [ ] Email sending works
- [ ] Print button in detail view works

---

### Phase 9: Testing & Quality Assurance (Week 5-6)

**Duration:** Week 5-6
**Status:** 🔴 Pending

#### Objectives

- Write unit tests for service functions
- Write integration tests for workflows
- Perform user acceptance testing (UAT)
- Fix bugs and edge cases

#### Test Categories

1. **Unit Tests**
   - Test `record_payment()` with various inputs
   - Test `approve_payment()` workflow
   - Test `reject_payment()` workflow
   - Test `reverse_payment()` with GL reversal
   - Test FIFO allocation logic
   - Test multi-method validation

2. **Integration Tests**
   - Test end-to-end payment recording flow
   - Test approval workflow (pending → approved → GL posted)
   - Test rejection workflow (pending → rejected → edit → resubmit)
   - Test reversal workflow (approved → reversed → GL reversed)
   - Test advance payment application
   - Test package installment payment

3. **UI/UX Tests**
   - Test payment form validation
   - Test real-time calculation updates
   - Test allocation mode switching
   - Test advance balance display
   - Test approval page rendering
   - Test reversal confirmation

4. **Performance Tests**
   - Test payment recording with 1000+ payments
   - Test list view load time
   - Test search/filter performance
   - Test cache invalidation effectiveness

5. **Security Tests**
   - Test permission enforcement (create, approve, reverse)
   - Test SQL injection prevention
   - Test XSS prevention in templates
   - Test sensitive data masking (card numbers)

#### Test Data

Create comprehensive test data:
- 10 patients with varying dues
- 50 invoices (paid, partial, unpaid)
- 20 advance payments
- 5 package installment plans
- 100 payment receipts (various statuses)

#### Bug Tracking

Use GitHub Issues or similar:
- Label: `bug`, `enhancement`, `question`
- Priority: `critical`, `high`, `medium`, `low`
- Milestone: `Phase 9 - Testing`

#### Acceptance Criteria

- [ ] >80% code coverage for service functions
- [ ] All critical paths tested
- [ ] No critical bugs remaining
- [ ] Performance meets requirements (<2s payment recording)
- [ ] Security vulnerabilities addressed
- [ ] User acceptance testing passed

---

### Phase 10: Documentation & Training (Week 6)

**Duration:** Week 6
**Status:** 🔴 Pending

#### Objectives

- Create user documentation
- Create administrator documentation
- Create developer documentation
- Conduct user training

#### Deliverables

1. **User Documentation**
   - How to record payment receipts
   - How to use manual vs. auto-FIFO allocation
   - How to record advance payments
   - How to create package installment plans
   - How to approve/reject payments
   - How to reverse payments
   - How to print receipts
   - FAQs

2. **Administrator Documentation**
   - System configuration
   - Approval threshold settings
   - Permission management
   - Database maintenance
   - Troubleshooting guide

3. **Developer Documentation**
   - Architecture overview
   - Database schema
   - Service layer API
   - UI component library
   - Testing guide
   - Deployment guide

4. **Training Materials**
   - User training video (15-20 minutes)
   - Administrator training video (10 minutes)
   - Quick reference guide (PDF)
   - Training exercises

#### Acceptance Criteria

- [ ] All documentation completed
- [ ] Training materials created
- [ ] User training conducted
- [ ] Administrator training conducted
- [ ] Feedback collected and incorporated

---

### Phase 11: Paytm Integration (Future)

**Duration:** 2-3 weeks
**Status:** 🔴 Future Enhancement

#### Objectives

- Integrate with Paytm card machine API
- Push payment requests to machine
- Auto-capture successful payments
- Handle failed transactions

#### Prerequisites

- Paytm merchant credentials
- Paytm SDK/API documentation
- Test Paytm machine access

#### Tasks

1. **Paytm API Integration**
   - Install Paytm SDK/library
   - Configure merchant credentials
   - Implement payment request function
   - Implement payment status check function

2. **Payment Form Enhancement**
   - Add "Send to Paytm Machine" button
   - Implement payment request flow
   - Show machine status (waiting for payment)
   - Handle success/failure responses

3. **Auto-Capture Logic**
   - On success: Auto-populate payment form
   - On success: Auto-submit payment
   - On failure: Show error, allow retry
   - On timeout: Show error, allow manual entry

4. **Testing**
   - Test with Paytm test environment
   - Test various payment scenarios
   - Test error handling
   - Test network failure scenarios

#### Acceptance Criteria

- [ ] Paytm API integration working
- [ ] Payment can be pushed to machine
- [ ] Success response auto-creates payment
- [ ] Failure handled gracefully
- [ ] Timeout handled gracefully
- [ ] Manual entry fallback works

---

## 💾 Database Schema

### Extended Tables

#### 1. payment_details (EXTENDED)

**Purpose:** Records payments against invoices with approval workflow

**New Fields Added:**

| Field Name | Type | Description |
|------------|------|-------------|
| workflow_status | VARCHAR(20) | draft, pending_approval, approved, rejected, reversed |
| requires_approval | BOOLEAN | TRUE if payment >= threshold |
| submitted_by | VARCHAR(15) | User who submitted for approval |
| submitted_at | TIMESTAMP | When submitted for approval |
| approved_by | VARCHAR(15) | User who approved |
| approved_at | TIMESTAMP | When approved |
| rejected_by | VARCHAR(15) | User who rejected |
| rejected_at | TIMESTAMP | When rejected |
| rejection_reason | TEXT | Why rejected |
| gl_posted | BOOLEAN | TRUE if GL entries posted |
| posting_date | TIMESTAMP | When GL posted |
| is_deleted | BOOLEAN | Soft delete flag |
| deleted_at | TIMESTAMP | When deleted |
| deleted_by | VARCHAR(15) | User who deleted |
| deletion_reason | TEXT | Why deleted |
| is_reversed | BOOLEAN | TRUE if reversed |
| reversed_at | TIMESTAMP | When reversed |
| reversed_by | VARCHAR(15) | User who reversed |
| reversal_reason | TEXT | Why reversed |
| reversal_gl_entry_id | UUID | GL entry for reversal |

#### 2. patient_advance_payments (EXTENDED)

**Purpose:** Tracks advance payments with workflow

**New Fields Added:**

| Field Name | Type | Description |
|------------|------|-------------|
| workflow_status | VARCHAR(20) | draft, pending_approval, approved, rejected |
| requires_approval | BOOLEAN | TRUE if amount >= threshold |
| approved_by | VARCHAR(15) | User who approved |
| approved_at | TIMESTAMP | When approved |
| rejected_by | VARCHAR(15) | User who rejected |
| rejected_at | TIMESTAMP | When rejected |
| rejection_reason | TEXT | Why rejected |
| gl_posted | BOOLEAN | TRUE if GL entries posted |
| posting_date | TIMESTAMP | When GL posted |
| branch_id | UUID | Branch reference (multi-branch support) |

#### 3. advance_adjustments (EXTENDED)

**Purpose:** Tracks advance allocation to invoices

**New Fields Added:**

| Field Name | Type | Description |
|------------|------|-------------|
| gl_entry_id | UUID | GL entry for adjustment |
| is_reversed | BOOLEAN | TRUE if reversed |
| reversed_at | TIMESTAMP | When reversed |
| reversed_by | VARCHAR(15) | User who reversed |

### New Tables

#### 4. package_payment_plans (NEW)

**Purpose:** Tracks package installment plans

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| plan_id | UUID | PK | Plan identifier |
| hospital_id | UUID | FK, NOT NULL | Hospital reference |
| branch_id | UUID | FK | Branch reference |
| patient_id | UUID | FK, NOT NULL | Patient reference |
| package_name | VARCHAR(255) | NOT NULL | Package name |
| package_description | TEXT | | Package description |
| total_sessions | INTEGER | NOT NULL | Total sessions in package |
| completed_sessions | INTEGER | DEFAULT 0 | Sessions completed |
| total_amount | NUMERIC(12,2) | NOT NULL | Total package cost |
| paid_amount | NUMERIC(12,2) | DEFAULT 0 | Amount paid so far |
| balance_amount | NUMERIC(12,2) | | Remaining balance |
| installment_count | INTEGER | NOT NULL | Number of installments |
| first_payment_date | DATE | NOT NULL | First installment due date |
| installment_frequency | VARCHAR(20) | DEFAULT 'custom' | monthly, weekly, custom |
| status | VARCHAR(20) | DEFAULT 'active' | active, completed, cancelled |
| created_at | TIMESTAMP | DEFAULT NOW() | When created |
| created_by | VARCHAR(15) | NOT NULL | User who created |
| updated_at | TIMESTAMP | | When updated |
| updated_by | VARCHAR(15) | | User who updated |

#### 5. installment_payments (NEW)

**Purpose:** Tracks individual installment payments

| Field Name | Type | Constraints | Description |
|------------|------|-------------|-------------|
| installment_id | UUID | PK | Installment identifier |
| hospital_id | UUID | FK, NOT NULL | Hospital reference |
| plan_id | UUID | FK, NOT NULL | Plan reference |
| installment_number | INTEGER | NOT NULL | Installment sequence (1, 2, 3...) |
| due_date | DATE | NOT NULL | When installment is due |
| amount | NUMERIC(12,2) | NOT NULL | Installment amount |
| paid_date | DATE | | When actually paid |
| paid_amount | NUMERIC(12,2) | DEFAULT 0 | Amount actually paid |
| payment_id | UUID | FK | Link to payment_details |
| status | VARCHAR(20) | DEFAULT 'pending' | pending, paid, overdue, waived |
| created_at | TIMESTAMP | DEFAULT NOW() | When created |

### Database View

#### v_patient_payment_receipts (NEW)

**Purpose:** Comprehensive view for payment receipts with workflow details

**Joins:**
- payment_details
- invoice_header
- patient
- hospital
- branches
- users (multiple joins for audit trail)

**Key Fields:**
- Payment identification (payment_id, invoice_number, patient_name)
- Payment details (date, amount, methods)
- Workflow status (workflow_status, approved_by, rejected_by)
- GL posting status (gl_posted, posting_date, gl_entry_id)
- Reversal status (is_reversed, reversed_at, reversal_reason)
- Aging information (payment_age_days, aging_bucket)
- Complete audit trail (created_by_name, approved_by_name, etc.)

---

## 🔧 Service Layer Design

### Core Service Functions

#### 1. record_payment() - MODIFIED

**File:** `app/services/billing_service.py`

**Signature:**
```python
def record_payment(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_date: datetime.date,
    cash_amount: Decimal = 0,
    credit_card_amount: Decimal = 0,
    debit_card_amount: Decimal = 0,
    upi_amount: Decimal = 0,
    card_number_last4: Optional[str] = None,
    card_type: Optional[str] = None,
    upi_id: Optional[str] = None,
    reference_number: Optional[str] = None,
    handle_excess: bool = True,
    save_as_draft: bool = False,  # NEW
    approval_threshold: Decimal = Decimal('100000'),  # NEW
    recorded_by: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict
```

**New Logic:**
1. Calculate total_amount
2. Determine workflow_status:
   - If `save_as_draft=True` → 'draft'
   - Elif `total_amount >= approval_threshold` → 'pending_approval'
   - Else → 'approved'
3. Create PaymentDetail record
4. If workflow_status == 'approved':
   - Update invoice balances
   - Post GL entries
   - Create AR subledger entry
   - Handle excess if applicable
5. Else:
   - Skip GL posting
   - Skip invoice balance update
6. Invalidate caches
7. Return payment dict

**Returns:**
```python
{
    'success': True,
    'payment_id': '...',
    'workflow_status': 'approved',
    'requires_approval': False,
    'gl_posted': True,
    'message': 'Payment recorded successfully'
}
```

#### 2. approve_payment() - NEW

**File:** `app/services/billing_service.py`

**Signature:**
```python
def approve_payment(
    payment_id: uuid.UUID,
    approved_by: str,
    session: Optional[Session] = None
) -> Dict
```

**Logic:**
1. Fetch payment by payment_id
2. Validate workflow_status == 'pending_approval'
3. Update workflow_status = 'approved'
4. Set approved_by, approved_at
5. Update invoice balances
6. Post GL entries
7. Set gl_posted = True, posting_date
8. Create AR subledger entry
9. Invalidate caches
10. Return success dict

**Returns:**
```python
{
    'success': True,
    'payment_id': '...',
    'message': 'Payment approved and posted successfully'
}
```

#### 3. reject_payment() - NEW

**File:** `app/services/billing_service.py`

**Signature:**
```python
def reject_payment(
    payment_id: uuid.UUID,
    rejected_by: str,
    reason: str,
    session: Optional[Session] = None
) -> Dict
```

**Logic:**
1. Fetch payment by payment_id
2. Validate workflow_status == 'pending_approval'
3. Update workflow_status = 'rejected'
4. Set rejected_by, rejected_at, rejection_reason
5. Invalidate caches
6. Return success dict

**Returns:**
```python
{
    'success': True,
    'payment_id': '...',
    'message': 'Payment rejected'
}
```

#### 4. reverse_payment() - NEW

**File:** `app/services/billing_service.py`

**Signature:**
```python
def reverse_payment(
    payment_id: uuid.UUID,
    reversed_by: str,
    reason: str,
    session: Optional[Session] = None
) -> Dict
```

**Logic:**
1. Fetch payment by payment_id
2. Validate workflow_status == 'approved'
3. Validate gl_posted == True
4. Validate is_reversed == False
5. Create reversing GL entries (call `create_reversing_gl_entries()`)
6. Restore invoice balances (subtract payment amount)
7. Update payment:
   - is_reversed = True
   - reversed_at, reversed_by, reversal_reason
   - workflow_status = 'reversed'
   - reversal_gl_entry_id
8. Invalidate caches
9. Return success dict

**Returns:**
```python
{
    'success': True,
    'payment_id': '...',
    'reversal_entry_id': '...',
    'message': 'Payment reversed successfully'
}
```

#### 5. create_reversing_gl_entries() - NEW

**File:** `app/services/gl_service.py`

**Signature:**
```python
def create_reversing_gl_entries(
    original_entry_id: uuid.UUID,
    reversed_by: str,
    reason: str,
    session: Optional[Session] = None
) -> uuid.UUID
```

**Logic:**
1. Fetch original GL transaction
2. Fetch all GL entries (line items) for original transaction
3. Create new GL transaction:
   - transaction_type = 'reversal'
   - description = f"Reversal: {original.description}"
   - reversal_of_id = original_entry_id
4. For each original GL entry:
   - Create new entry with opposite sign (DR ↔ CR)
   - Same account, same amount, opposite debit_credit_indicator
   - Link to new transaction
5. Mark original transaction as reversed
6. Return new transaction_id

**Returns:**
```python
uuid.UUID  # New reversal transaction ID
```

### Package Payment Service

#### 6. create_package_payment_plan() - NEW

**File:** `app/services/package_payment_service.py`

**Signature:**
```python
def create_package_payment_plan(
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    package_name: str,
    total_amount: Decimal,
    total_sessions: int,
    installment_count: int,
    first_payment_date: datetime.date,
    installment_frequency: str = 'monthly',
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict
```

**Logic:**
1. Create PackagePaymentPlan record
2. Calculate installment_amount = total_amount / installment_count
3. Generate installment schedule:
   - For i in range(1, installment_count + 1):
     - Create InstallmentPayment record
     - installment_number = i
     - due_date = first_payment_date + (i-1) * frequency_delta
     - amount = installment_amount
     - status = 'pending'
4. Return plan dict

**Returns:**
```python
{
    'success': True,
    'plan_id': '...',
    'installment_count': 3,
    'installments': [
        {
            'installment_number': 1,
            'due_date': '2025-01-15',
            'amount': 16666.67,
            'status': 'pending'
        },
        ...
    ]
}
```

#### 7. record_installment_payment() - NEW

**File:** `app/services/package_payment_service.py`

**Signature:**
```python
def record_installment_payment(
    installment_id: uuid.UUID,
    payment_date: datetime.date,
    cash_amount: Decimal = 0,
    credit_card_amount: Decimal = 0,
    debit_card_amount: Decimal = 0,
    upi_amount: Decimal = 0,
    ...,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict
```

**Logic:**
1. Fetch installment by installment_id
2. Fetch plan by plan_id
3. Call `record_payment()` to create payment record
4. Update installment:
   - paid_date = payment_date
   - paid_amount = payment['total_amount']
   - payment_id = payment['payment_id']
   - status = 'paid' if paid_amount >= amount else 'partial'
5. Update plan:
   - paid_amount += installment.amount
   - balance_amount = total_amount - paid_amount
   - If all installments paid: status = 'completed'
6. Return payment dict

**Returns:**
```python
{
    'success': True,
    'payment_id': '...',
    'installment_id': '...',
    'plan_status': 'active',
    'remaining_installments': 2
}
```

---

## 🎨 UI/UX Design

### Design Principles

1. **Follow Supplier Payment Pattern**
   - Professional card-based layout
   - Status badges with color coding
   - Collapsible sections
   - Real-time validation feedback

2. **Progressive Enhancement**
   - Core functionality works without JavaScript
   - Enhanced experience with JavaScript enabled
   - Mobile-responsive design

3. **User-Centric**
   - Minimize clicks to complete task
   - Provide helpful validation messages
   - Auto-calculate and suggest allocations
   - Show progress indicators

### Color Scheme

| Status | Badge Color | Hex Code |
|--------|-------------|----------|
| Draft | Gray | #6B7280 |
| Pending Approval | Orange | #F59E0B |
| Approved | Green | #10B981 |
| Rejected | Red | #EF4444 |
| Reversed | Purple | #8B5CF6 |
| PAID Stamp | Green | #10B981 |

### Component Library

#### 1. Status Badge

```html
<span class="badge badge-pending-approval">
    <i class="fas fa-clock"></i> Pending Approval
</span>
```

**Variants:**
- `badge-draft` - Gray
- `badge-pending-approval` - Orange
- `badge-approved` - Green
- `badge-rejected` - Red
- `badge-reversed` - Purple

#### 2. Payment Method Input Group

```html
<div class="payment-method-group">
    <label>
        <i class="fas fa-money-bill-wave"></i>
        Cash Amount
    </label>
    <input type="number"
           name="cash_amount"
           class="payment-amount-input"
           step="0.01"
           min="0"
           placeholder="0.00">
</div>
```

#### 3. Advance Balance Card

```html
<div class="advance-balance-card">
    <div class="advance-balance-header">
        <i class="fas fa-piggy-bank"></i>
        Available Advance Balance
    </div>
    <div class="advance-balance-amount">
        ₹<span id="advance-balance-value">5,000.00</span>
    </div>
    <div class="advance-balance-footer">
        <button onclick="allocateAdvance()" class="btn-link">
            Allocate to Payment
        </button>
    </div>
</div>
```

#### 4. Payment Summary Panel

```html
<div class="payment-summary-panel">
    <h4>Payment Summary</h4>
    <div class="summary-row">
        <span>Advance Allocation:</span>
        <span class="summary-amount">₹1,000.00</span>
    </div>
    <div class="summary-row">
        <span>Cash:</span>
        <span class="summary-amount">₹500.00</span>
    </div>
    <div class="summary-row">
        <span>Credit Card:</span>
        <span class="summary-amount">₹302.00</span>
    </div>
    <hr>
    <div class="summary-row summary-total">
        <span>Total Payment:</span>
        <span class="summary-amount">₹1,802.00</span>
    </div>
</div>
```

#### 5. Validation Message

```html
<div class="validation-message validation-success">
    <i class="fas fa-check-circle"></i>
    Payment amount matches invoice balance
</div>

<div class="validation-message validation-warning">
    <i class="fas fa-exclamation-triangle"></i>
    Missing ₹198.00 - Add more payment or adjust allocation
</div>

<div class="validation-message validation-error">
    <i class="fas fa-times-circle"></i>
    Card details required for card payment
</div>
```

### Responsive Breakpoints

| Device | Width | Layout Changes |
|--------|-------|----------------|
| Mobile | <640px | Single column, stacked sections |
| Tablet | 640px-1024px | 2-column grid collapses to 1 column |
| Desktop | >1024px | Full 2-column grid, side panels |

---

## 🌐 API Endpoints

### Payment Receipts API

#### 1. Record Payment

**Endpoint:** `POST /billing/payment/record`

**Request Body:**
```json
{
    "invoice_id": "uuid",
    "payment_date": "2025-01-10",
    "cash_amount": 500.00,
    "credit_card_amount": 302.00,
    "debit_card_amount": 0,
    "upi_amount": 0,
    "card_number_last4": "1234",
    "card_type": "visa",
    "upi_id": null,
    "reference_number": "REF123",
    "save_as_draft": false,
    "allocation_mode": "auto_fifo"
}
```

**Response (Success):**
```json
{
    "success": true,
    "payment_id": "uuid",
    "workflow_status": "approved",
    "requires_approval": false,
    "gl_posted": true,
    "message": "Payment recorded successfully"
}
```

**Response (Requires Approval):**
```json
{
    "success": true,
    "payment_id": "uuid",
    "workflow_status": "pending_approval",
    "requires_approval": true,
    "gl_posted": false,
    "message": "Payment submitted for approval"
}
```

#### 2. Approve Payment

**Endpoint:** `POST /billing/payment/approve/<payment_id>`

**Request Body:**
```json
{
    "approved_by": "user_id"
}
```

**Response:**
```json
{
    "success": true,
    "payment_id": "uuid",
    "message": "Payment approved and posted successfully"
}
```

#### 3. Reject Payment

**Endpoint:** `POST /billing/payment/reject/<payment_id>`

**Request Body:**
```json
{
    "rejected_by": "user_id",
    "reason": "Incorrect amount"
}
```

**Response:**
```json
{
    "success": true,
    "payment_id": "uuid",
    "message": "Payment rejected"
}
```

#### 4. Reverse Payment

**Endpoint:** `POST /billing/payment/reverse/<payment_id>`

**Request Body:**
```json
{
    "reversed_by": "user_id",
    "reason": "Duplicate payment"
}
```

**Response:**
```json
{
    "success": true,
    "payment_id": "uuid",
    "reversal_entry_id": "uuid",
    "message": "Payment reversed successfully"
}
```

#### 5. Get Patient Outstanding Invoices

**Endpoint:** `GET /api/patient/<patient_id>/outstanding-invoices`

**Response:**
```json
{
    "success": true,
    "patient_id": "uuid",
    "patient_name": "John Doe",
    "total_outstanding": 5000.00,
    "invoices": [
        {
            "invoice_id": "uuid",
            "invoice_number": "INV-001",
            "invoice_date": "2025-01-01",
            "total_amount": 3000.00,
            "paid_amount": 1000.00,
            "balance_due": 2000.00,
            "aging_days": 10
        },
        ...
    ]
}
```

#### 6. Get Patient Advance Balance

**Endpoint:** `GET /api/patient/<patient_id>/advance-balance`

**Response:**
```json
{
    "success": true,
    "patient_id": "uuid",
    "advance_balance": 5000.00,
    "advance_count": 2,
    "advances": [
        {
            "advance_id": "uuid",
            "amount": 3000.00,
            "available_balance": 3000.00,
            "payment_date": "2025-01-05"
        },
        ...
    ]
}
```

### Package Installment API

#### 7. Create Package Plan

**Endpoint:** `POST /billing/package/installment/create`

**Request Body:**
```json
{
    "patient_id": "uuid",
    "package_name": "Laser Hair Reduction - 5 Sessions",
    "total_amount": 50000.00,
    "total_sessions": 5,
    "installment_count": 3,
    "first_payment_date": "2025-01-15",
    "installment_frequency": "monthly"
}
```

**Response:**
```json
{
    "success": true,
    "plan_id": "uuid",
    "installment_count": 3,
    "installments": [
        {
            "installment_number": 1,
            "due_date": "2025-01-15",
            "amount": 16666.67,
            "status": "pending"
        },
        ...
    ]
}
```

#### 8. Pay Installment

**Endpoint:** `POST /billing/package/installment/<plan_id>/pay/<installment_number>`

**Request Body:**
```json
{
    "payment_date": "2025-01-15",
    "cash_amount": 16666.67,
    "credit_card_amount": 0,
    "debit_card_amount": 0,
    "upi_amount": 0
}
```

**Response:**
```json
{
    "success": true,
    "payment_id": "uuid",
    "installment_id": "uuid",
    "plan_status": "active",
    "remaining_installments": 2
}
```

---

## 🧪 Testing Strategy

### Test Coverage Goals

| Layer | Target Coverage | Priority |
|-------|----------------|----------|
| Service Functions | >90% | Critical |
| Models | >80% | High |
| Routes | >70% | Medium |
| UI Components | >60% | Medium |
| Integration Tests | All workflows | Critical |

### Unit Test Examples

#### Test: record_payment() with approval workflow

```python
def test_record_payment_requires_approval():
    """Test payment ≥ ₹100K requires approval"""
    result = record_payment(
        hospital_id=test_hospital_id,
        invoice_id=test_invoice_id,
        payment_date=date.today(),
        cash_amount=Decimal('150000'),
        approval_threshold=Decimal('100000')
    )

    assert result['success'] is True
    assert result['workflow_status'] == 'pending_approval'
    assert result['requires_approval'] is True
    assert result['gl_posted'] is False

def test_record_payment_auto_approved():
    """Test payment < ₹100K auto-approved"""
    result = record_payment(
        hospital_id=test_hospital_id,
        invoice_id=test_invoice_id,
        payment_date=date.today(),
        cash_amount=Decimal('50000'),
        approval_threshold=Decimal('100000')
    )

    assert result['success'] is True
    assert result['workflow_status'] == 'approved'
    assert result['requires_approval'] is False
    assert result['gl_posted'] is True
```

#### Test: approve_payment()

```python
def test_approve_payment_posts_gl_entries():
    """Test approve_payment posts GL entries"""
    # Create pending payment
    payment = create_test_payment(workflow_status='pending_approval')

    # Approve
    result = approve_payment(
        payment_id=payment['payment_id'],
        approved_by='test_user'
    )

    assert result['success'] is True

    # Verify payment updated
    payment = get_payment_by_id(payment['payment_id'])
    assert payment['workflow_status'] == 'approved'
    assert payment['gl_posted'] is True
    assert payment['approved_by'] == 'test_user'

    # Verify invoice updated
    invoice = get_invoice_by_id(payment['invoice_id'])
    assert invoice['paid_amount'] > 0
    assert invoice['balance_due'] < invoice['total_amount']

    # Verify GL entries created
    gl_entries = get_gl_entries_by_transaction_id(payment['gl_entry_id'])
    assert len(gl_entries) > 0
```

#### Test: reverse_payment()

```python
def test_reverse_payment_creates_reversing_entries():
    """Test reverse_payment creates reversing GL entries"""
    # Create approved payment with GL posted
    payment = create_test_payment(workflow_status='approved', gl_posted=True)
    original_gl_entry_id = payment['gl_entry_id']

    # Reverse
    result = reverse_payment(
        payment_id=payment['payment_id'],
        reversed_by='test_user',
        reason='Duplicate payment'
    )

    assert result['success'] is True

    # Verify payment updated
    payment = get_payment_by_id(payment['payment_id'])
    assert payment['is_reversed'] is True
    assert payment['workflow_status'] == 'reversed'
    assert payment['reversal_gl_entry_id'] is not None

    # Verify reversing GL entries created
    reversing_entries = get_gl_entries_by_transaction_id(payment['reversal_gl_entry_id'])
    original_entries = get_gl_entries_by_transaction_id(original_gl_entry_id)

    assert len(reversing_entries) == len(original_entries)

    # Verify amounts are opposite
    for orig, rev in zip(original_entries, reversing_entries):
        assert orig['account_id'] == rev['account_id']
        assert orig['amount'] == rev['amount']
        assert orig['debit_credit_indicator'] != rev['debit_credit_indicator']
```

### Integration Test Example

```python
def test_full_payment_workflow_with_approval():
    """Test complete workflow: Record → Approve → GL Post"""
    # 1. Record large payment (requires approval)
    payment_result = record_payment(
        hospital_id=test_hospital_id,
        invoice_id=test_invoice_id,
        payment_date=date.today(),
        cash_amount=Decimal('150000'),
        approval_threshold=Decimal('100000'),
        recorded_by='cashier_user'
    )

    assert payment_result['workflow_status'] == 'pending_approval'
    payment_id = payment_result['payment_id']

    # 2. Verify invoice NOT updated yet
    invoice = get_invoice_by_id(test_invoice_id)
    assert invoice['paid_amount'] == 0
    assert invoice['balance_due'] == invoice['total_amount']

    # 3. Approve payment
    approval_result = approve_payment(
        payment_id=payment_id,
        approved_by='manager_user'
    )

    assert approval_result['success'] is True

    # 4. Verify invoice NOW updated
    invoice = get_invoice_by_id(test_invoice_id)
    assert invoice['paid_amount'] == 150000
    assert invoice['balance_due'] == 0

    # 5. Verify GL entries posted
    payment = get_payment_by_id(payment_id)
    assert payment['gl_posted'] is True

    gl_entries = get_gl_entries_by_transaction_id(payment['gl_entry_id'])
    assert len(gl_entries) >= 2  # At least DR Cash, CR A/R

    # 6. Verify AR subledger entry
    ar_entries = get_ar_subledger_entries(entity_id=test_invoice_id)
    assert any(e['transaction_id'] == payment_id for e in ar_entries)
```

---

## 📚 Deployment Guide

### Prerequisites

- PostgreSQL 13+ with write access
- Python 3.9+
- Flask 3.1.0
- Redis (optional, for caching)
- Database backup before migration

### Deployment Steps

#### Step 1: Backup Database

```bash
# Create backup
pg_dump -h localhost -U postgres -d skinspire_dev > backups/pre_payment_receipts_$(date +%Y%m%d).sql

# Verify backup
ls -lh backups/
```

#### Step 2: Apply Database Migrations

```bash
# Apply workflow fields migration
psql -h localhost -U postgres -d skinspire_dev -f migrations/add_payment_receipt_workflow_fields.sql

# Verify migration
psql -h localhost -U postgres -d skinspire_dev -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'payment_details'
  AND column_name IN ('workflow_status', 'requires_approval', 'gl_posted');
"

# Apply view migration
psql -h localhost -U postgres -d skinspire_dev -f migrations/create_patient_payment_receipts_view.sql

# Verify view created
psql -h localhost -U postgres -d skinspire_dev -c "SELECT COUNT(*) FROM v_patient_payment_receipts;"
```

#### Step 3: Deploy Code

```bash
# Pull latest code
git pull origin master

# Install dependencies
source /path/to/venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/test_billing_service.py -v

# Restart application
sudo systemctl restart skinspire-app
# OR
supervisorctl restart skinspire-app
```

#### Step 4: Clear Caches

```bash
# Clear Redis cache
redis-cli FLUSHDB

# OR clear specific keys
redis-cli KEYS "service_cache:payment_details:*" | xargs redis-cli DEL
```

#### Step 5: Verify Deployment

```bash
# Check application logs
tail -f /var/log/skinspire/app.log

# Test payment recording API
curl -X POST http://localhost:5000/billing/payment/record \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "invoice_id": "...",
    "payment_date": "2025-01-10",
    "cash_amount": 500
  }'

# Check database
psql -h localhost -U postgres -d skinspire_dev -c "
SELECT workflow_status, COUNT(*)
FROM payment_details
GROUP BY workflow_status;
"
```

#### Step 6: Monitor

```bash
# Monitor error logs
tail -f /var/log/skinspire/error.log

# Monitor database performance
psql -h localhost -U postgres -d skinspire_dev -c "
SELECT schemaname, tablename, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE tablename IN ('payment_details', 'patient_advance_payments');
"
```

### Rollback Plan

If issues arise:

```bash
# 1. Stop application
sudo systemctl stop skinspire-app

# 2. Restore database backup
psql -h localhost -U postgres -d skinspire_dev < backups/pre_payment_receipts_YYYYMMDD.sql

# 3. Revert code
git revert <commit-hash>
git push origin master

# 4. Restart application
sudo systemctl start skinspire-app

# 5. Verify rollback
psql -h localhost -U postgres -d skinspire_dev -c "
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'payment_details'
  AND column_name = 'workflow_status';
"
# Should return 0 rows if successfully rolled back
```

---

## 📝 Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Advance Payment** | Payment received from patient before invoice is created |
| **FIFO** | First In First Out - Allocation method for advance payments |
| **GL Posting** | Creating General Ledger entries for accounting |
| **Invoice cum Receipt** | Combined document showing invoice and payment details |
| **Reversal** | Canceling a payment by creating opposite GL entries |
| **Soft Delete** | Marking record as deleted without physically removing |
| **Workflow Status** | Current state in approval workflow (draft, pending, approved, etc.) |

### B. Reference Documents

1. **Hospital Management System Master Document v4.0**
2. **SkinSpire Clinic HMS Technical Development Guidelines v3.0**
3. **Universal Engine Entity Configuration Complete Guide v6.0**
4. **Universal Engine Entity Service Implementation Guide v3.0**
5. **Entity Configuration Checklist for Universal Engine**

### C. Contact Information

| Role | Contact |
|------|---------|
| Product Owner | vinod@skinspire.com |
| Development Lead | [Name] |
| Database Administrator | [Name] |
| QA Lead | [Name] |

### D. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-10 | Claude Code | Initial design document |

### E. Future Enhancements (Post-MVP)

1. **Bulk Payment Upload** - Upload CSV of multiple payments
2. **Recurring Payments** - Auto-create payments on schedule
3. **Payment Link Generation** - Send payment links to patients via SMS/Email
4. **QR Code Payments** - Generate UPI QR codes
5. **Payment Analytics Dashboard** - Revenue trends, payment method analysis
6. **Customer Portal** - Patients view invoices and pay online
7. **WhatsApp Integration** - Send receipts via WhatsApp
8. **EMI Integration** - Partner with EMI providers
9. **Wallet Integration** - Support Paytm Wallet, Google Pay, PhonePe
10. **Auto-Reconciliation** - Match bank statements with payments

---

**END OF DOCUMENT**

---

**Document Status:** ✅ Complete
**Last Updated:** January 10, 2025
**Next Review:** After Phase 1 completion