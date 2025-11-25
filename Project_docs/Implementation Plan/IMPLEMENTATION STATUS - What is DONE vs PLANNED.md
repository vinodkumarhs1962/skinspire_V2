# Implementation Status: DONE vs PLANNED
## Date: 21-November-2025
## Purpose: Crystal-clear status of what is actually working vs what is only designed

---

## ✅ FULLY IMPLEMENTED & WORKING

### 1. Bulk Discount System (Basic)
**Status**: ✅ **LIVE & TESTED**

**What Works**:
- ✅ User adds services to invoice
- ✅ System counts total service quantity (e.g., 1 line item × 5 sessions = 5 services)
- ✅ When quantity ≥ threshold (5 services), checkbox auto-checks
- ✅ Frontend calls `/api/discount/calculate` API
- ✅ Backend calculates bulk discount percentage from `service.bulk_discount_percent`
- ✅ Backend respects `service.max_discount` cap
- ✅ Frontend updates discount field in line item
- ✅ Frontend shows "Bulk" badge next to discount field
- ✅ Invoice totals recalculate with discount
- ✅ User can manually uncheck checkbox to remove discount
- ✅ User can re-check to reapply discount
- ✅ No infinite loops or CSRF errors

**UI Elements**:
- ✅ Single checkbox: "Apply Bulk Service Discount"
- ✅ Badge showing "✓ Eligible (5 services)" or "Add N more services"
- ✅ Blue "Bulk" badge on discounted line items

**Code Files**:
- ✅ `app/services/discount_service.py` - Fixed quantity counting
- ✅ `app/api/routes/discount_api.py` - Working API endpoints
- ✅ `app/static/js/components/invoice_bulk_discount.js` - 8 bugs fixed
- ✅ `app/static/js/components/invoice_item.js` - Event dispatch added
- ✅ `app/templates/billing/create_invoice.html` - Hospital ID field added

**Limitations**:
- ⚠️ **Only ONE discount type**: Bulk discount only, no loyalty/promotion/standard
- ⚠️ **Only Services**: Medicines and packages not supported yet
- ⚠️ **Single Checkbox**: No separate checkboxes for different discount types
- ⚠️ **Basic UI**: No patient-facing screen or print feature

---

## ❌ NOT IMPLEMENTED (ONLY DESIGNED/PLANNED)

### 2. Patient-Facing Pricing Consultation Screen
**Status**: ❌ **NOT IMPLEMENTED** (Design complete, code not written)

**What Doesn't Exist Yet**:
- ❌ No popup modal for patient viewing
- ❌ No extended screen support
- ❌ No simplified line items display
- ❌ No patient-friendly terminology ("Volume Discount" vs "Bulk Discount")
- ❌ No large-text layout for patient readability
- ❌ No discount breakdown section
- ❌ No "Print Summary" button
- ❌ No "Email to Patient" button

**Current Reality**:
- Staff sees regular invoice form
- No separate patient view
- Technical terminology shown
- No dedicated pricing consultation interface

**To Implement** (When Ready):
1. Create `pricing_consultation_modal.html` template
2. Add JavaScript to open popup
3. Format data for patient viewing
4. Add print CSS
5. Implement email functionality

---

### 3. Staff Discount Control Panel
**Status**: ❌ **NOT IMPLEMENTED** (Design complete, code not written)

**What Doesn't Exist Yet**:
- ❌ No 4-checkbox discount panel (Standard, Bulk, Loyalty, Promotion)
- ❌ No "Staff Only" section
- ❌ No toggle between "Patient View" and "Staff Controls"
- ❌ No per-discount-type eligibility indicators
- ❌ No combined discount display

**Current Reality**:
- Only 1 checkbox exists: "Apply Bulk Service Discount"
- No way to control other discount types
- No separate staff control panel
- All users see same interface

**To Implement** (When Ready):
1. Add HTML for 4 checkboxes
2. Update JavaScript to handle multiple discount types
3. Add permission checks for display
4. Implement toggle button

---

### 4. Print Pricing Summary / Draft Invoice
**Status**: ❌ **NOT IMPLEMENTED** (Design complete, code not written)

**What Doesn't Exist Yet**:
- ❌ No "Save as Draft" functionality
- ❌ No draft invoice template
- ❌ No print preview
- ❌ No "DRAFT" watermark
- ❌ No patient approval signature section
- ❌ No email delivery of draft
- ❌ Draft invoices cannot be viewed before posting

**Current Reality**:
- Can only save completed/posted invoices
- No way to show pricing to patient before committing
- No print-friendly pricing summary
- Once invoice is posted, cannot undo

**To Implement** (When Ready):
1. Create `/invoice/draft/<id>/print` route
2. Create `print_draft_invoice.html` template
3. Add "Save Draft" button to invoice form
4. Store draft data in session or temp table
5. Add print CSS with watermark
6. Add email function

---

### 5. Role-Based Discount Field Editing
**Status**: ❌ **NOT IMPLEMENTED** (Infrastructure ready, business logic not connected)

**What Doesn't Exist Yet**:
- ❌ Discount fields are not made readonly for front desk users
- ❌ No visual lock icon indicator
- ❌ No permission check before allowing manual discount edit
- ❌ Manager override not enforced

**Current Reality**:
- Discount fields are editable by all users
- No role-based restrictions
- Permission infrastructure exists but not connected to discount fields

**Partial Implementation**:
- ✅ `has_permission('billing.edit_discount')` function exists
- ✅ Role-permission tables exist
- ❌ Not connected to UI or validation

**To Implement** (When Ready):
1. Add `can_edit_discount` to template context
2. Add `readonly` attribute based on permission
3. Add client-side validation
4. Add server-side validation
5. Add visual indicators (lock icon)

---

### 6. Multi-Discount System (4 Types)
**Status**: ❌ **NOT IMPLEMENTED** (Design complete, code not written)

**What Doesn't Exist Yet**:
- ❌ No Standard Discount support
- ❌ No Loyalty Card percentage discount (card exists, but % not applied)
- ❌ No Promotion/Campaign discount
- ❌ No discount combination logic (absolute vs additional mode)
- ❌ Medicines don't have bulk/standard discount fields
- ❌ No 4-checkbox UI for discount types

**Current Reality**:
- **Only Bulk Discount** works
- Loyalty cards exist but only track membership, no auto-discount
- Promotions/campaigns not functional
- Standard discount not in database

**Database Changes Needed**:
```sql
-- NOT YET EXECUTED
ALTER TABLE medicine ADD COLUMN standard_discount_percent NUMERIC(5,2);
ALTER TABLE medicine ADD COLUMN bulk_discount_percent NUMERIC(5,2);
ALTER TABLE service ADD COLUMN standard_discount_percent NUMERIC(5,2);
ALTER TABLE hospital ADD COLUMN loyalty_discount_mode VARCHAR(20);
```

**Code Changes Needed**:
- Modify `discount_service.py` priority logic
- Add 3 new discount calculation methods
- Update API to return all discount types
- Rewrite frontend to handle 4 checkboxes

---

### 7. Loyalty Points Prepaid Wallet System
**Status**: ❌ **NOT IMPLEMENTED** (Database schema ready, code not written)

**What Doesn't Exist Yet**:
- ❌ No wallet creation functionality
- ❌ No points loading interface
- ❌ No points redemption in invoice
- ❌ No FIFO batch tracking
- ❌ No expiry management (12 months)
- ❌ No refund logic (service vs wallet closure)
- ❌ No partial payment (points + cash)
- ❌ No wallet balance display

**What IS Ready**:
- ✅ Database migration file created: `20251121_create_loyalty_wallet_system.sql`
- ✅ Tables designed: patient_loyalty_wallet, wallet_transaction, wallet_points_batch
- ✅ Views created: v_wallet_expiring_soon, v_wallet_liability_summary
- ❌ **NOT EXECUTED** - Migration needs to be run

**Current Reality**:
- No wallet functionality at all
- Patients cannot load points
- Cannot pay with points
- Database tables don't exist yet (migration not run)

**To Implement** (When Ready):
1. **Execute migration**: `psql ... -f 20251121_create_loyalty_wallet_system.sql`
2. Create `app/services/wallet_service.py` (500+ lines)
3. Create `app/api/routes/wallet_api.py`
4. Modify `billing_service.py` for wallet payment
5. Create wallet UI templates
6. Add wallet payment option in invoice form
7. Test complete flow

**Estimated Effort**: 10-12 days

---

### 8. Medicine & Package Discount Support
**Status**: ❌ **NOT IMPLEMENTED**

**What Doesn't Exist Yet**:
- ❌ Medicines don't have bulk discount
- ❌ Medicines don't have standard discount
- ❌ Packages don't have loyalty discount
- ❌ Discount calculation only handles Services

**Current Reality**:
- Bulk discount API only processes `item_type='Service'`
- Medicine line items ignored in discount calculation
- Package line items ignored

**To Implement**:
1. Add discount columns to medicine table
2. Extend `calculate_bulk_discount()` for medicines
3. Update frontend to show discount on medicine rows
4. Test medicine+service mixed invoices

---

## 📊 IMPLEMENTATION SUMMARY

| Feature | Status | Estimated Effort | Priority |
|---------|--------|------------------|----------|
| **Bulk Discount (Basic)** | ✅ DONE | - | - |
| Multi-Discount (4 types) | ❌ NOT DONE | 7 days | High |
| Patient Pricing Screen | ❌ NOT DONE | 4 days | Medium |
| Staff Control Panel | ❌ NOT DONE | 2 days | Medium |
| Print Draft Invoice | ❌ NOT DONE | 3 days | High |
| Role-Based Discount Edit | ❌ NOT DONE | 1 day | Medium |
| Loyalty Wallet System | ❌ NOT DONE | 12 days | Low |
| Medicine Discount Support | ❌ NOT DONE | 3 days | Medium |
| Package Discount Support | ❌ NOT DONE | 2 days | Low |

**Total Remaining Effort**: ~34 days of development

---

## 🎯 RECOMMENDED NEXT STEPS

### Option A: Complete Current Discount Features First
**Priority**: Print draft invoice → Multi-discount → Patient screen
**Rationale**: Finish what's started before adding wallet complexity
**Timeline**: 2-3 weeks

### Option B: Implement Wallet System First
**Priority**: Execute wallet migration → WalletService → Invoice integration
**Rationale**: Wallet is independent, can be done in parallel
**Timeline**: 2-3 weeks

### Option C: Quick Wins First
**Priority**: Role-based edit → Medicine support → Print draft
**Rationale**: Small features that deliver immediate value
**Timeline**: 1 week

---

## ⚠️ IMPORTANT NOTES

1. **Current System is LIVE**: The bulk discount system works and is being used
2. **No Regressions**: New features won't break existing functionality
3. **Incremental Approach**: Can implement features one at a time
4. **Testing Required**: Each new feature needs thorough testing
5. **User Training**: Staff need training on new features as they're released

---

## 📝 WHAT USERS CAN DO TODAY (21-Nov-2025)

**Working Features**:
✅ Create invoice with services
✅ Add multiple line items
✅ System auto-detects bulk discount eligibility
✅ Checkbox appears when 5+ services
✅ Discount applies automatically
✅ Can toggle discount on/off manually
✅ Discount shows in line item and total
✅ Invoice can be saved/posted with discount

**NOT Available**:
❌ Cannot view pricing on patient screen
❌ Cannot print draft for approval
❌ Cannot combine multiple discount types
❌ Cannot get discount on medicines
❌ Cannot use loyalty points for payment
❌ Cannot restrict discount editing by role
❌ Cannot see detailed discount breakdown

---

**Last Updated**: 21-November-2025, 11:00 PM IST
**Status**: Bulk discount LIVE, all other features PLANNED ONLY
