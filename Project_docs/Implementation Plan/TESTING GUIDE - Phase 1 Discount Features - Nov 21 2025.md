# Testing Guide - Phase 1 Discount Features
## Date: 21-November-2025
## Status: 📋 READY FOR TESTING

---

## TESTING SCOPE

### What to Test (Phase 1 - Completed Features)
✅ **Phase 1A**: Role-based discount field editing
✅ **Phase 1B**: Medicine discount support (backend & API)
✅ **Existing**: Service bulk discount (already working)

### What NOT to Test (Phase 4 - Not Yet Implemented)
❌ Standard discount type
❌ Loyalty percentage discount
❌ Promotion/campaign discount
❌ Package discounts
❌ 4-checkbox discount UI
❌ Discount combination logic

---

## PRE-TESTING SETUP

### Step 1: Execute Database Migrations

#### Medicine Discount Fields
```bash
# Navigate to migrations directory
cd "C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\Skinspire_v2\migrations"

# Execute migration (using .env credentials)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f 20251121_add_medicine_discount_fields.sql
```

**Expected Output**:
```
ALTER TABLE
ALTER TABLE
ALTER TABLE
COMMENT
COMMENT
COMMENT
CREATE INDEX
CREATE INDEX
```

**Verification Query**:
```sql
-- Check columns added
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'medicines'
  AND column_name IN ('standard_discount_percent', 'bulk_discount_percent', 'max_discount')
ORDER BY column_name;
```

**Expected Result**:
| column_name | data_type | column_default | is_nullable |
|-------------|-----------|----------------|-------------|
| bulk_discount_percent | numeric | 0 | YES |
| max_discount | numeric | NULL | YES |
| standard_discount_percent | numeric | 0 | YES |

---

### Step 2: Verify Hospital Bulk Discount Policy

```sql
-- Check if hospital has bulk discount enabled
SELECT
    hospital_id,
    hospital_name,
    bulk_discount_enabled,
    bulk_discount_min_service_count,
    bulk_discount_effective_from
FROM hospitals
WHERE hospital_id = '<your-hospital-id>';
```

**If NOT enabled, enable it**:
```sql
UPDATE hospitals
SET bulk_discount_enabled = TRUE,
    bulk_discount_min_service_count = 5,
    bulk_discount_effective_from = '2025-01-01'
WHERE hospital_id = '<your-hospital-id>';
```

---

### Step 3: Configure Sample Services

```sql
-- Update services with bulk discount
UPDATE services
SET bulk_discount_percent = 15.00,
    max_discount = 20.00
WHERE service_name IN ('Advanced Facial', 'Laser Hair Reduction')
  AND is_active = TRUE;

-- Service with capped discount (test max_discount)
UPDATE services
SET bulk_discount_percent = 25.00,
    max_discount = 15.00  -- Cap at 15%
WHERE service_name = 'Hair Restoration Treatment'
  AND is_active = TRUE;

-- Verify changes
SELECT
    service_id,
    service_name,
    bulk_discount_percent,
    max_discount
FROM services
WHERE bulk_discount_percent > 0
  AND is_active = TRUE;
```

---

### Step 4: Configure Sample Medicines

```sql
-- Update medicines with bulk discount
UPDATE medicines
SET bulk_discount_percent = 15.00,
    max_discount = 20.00
WHERE medicine_name IN ('Paracetamol 500mg', 'Vitamin D3')
  AND is_active = TRUE;

-- Medicine with capped discount (test max_discount)
UPDATE medicines
SET bulk_discount_percent = 25.00,
    max_discount = 10.00  -- Cap at 10%
WHERE medicine_name = 'Antibiotic'
  AND is_active = TRUE;

-- Medicine with no discount allowed
UPDATE medicines
SET bulk_discount_percent = 0,
    max_discount = 0
WHERE medicine_type = 'Prescription'
  AND medicine_name LIKE '%Controlled%'
  AND is_active = TRUE;

-- Verify changes
SELECT
    medicine_id,
    medicine_name,
    medicine_type,
    bulk_discount_percent,
    max_discount,
    selling_price
FROM medicines
WHERE bulk_discount_percent > 0
  AND is_active = TRUE
LIMIT 10;
```

---

### Step 5: Configure User Roles & Permissions

```sql
-- Check current user's permissions
SELECT
    u.user_id,
    u.entity_type,
    r.role_name,
    rmb.module_name,
    rmb.can_edit
FROM users u
JOIN user_role_mapping urm ON u.user_id = urm.user_id
JOIN role_master r ON urm.role_id = r.role_id
LEFT JOIN role_module_branch_access rmb ON r.role_id = rmb.role_id
WHERE u.user_id = '<your-user-id>'
  AND rmb.module_name = 'billing';
```

**Expected for Manager**:
- `can_edit = TRUE` → Can manually edit discount fields

**Expected for Front Desk**:
- `can_edit = FALSE` → Discount fields readonly

**If permission missing, add it**:
```sql
-- Grant edit_discount permission to manager role
INSERT INTO role_module_branch_access (
    role_id,
    module_name,
    branch_id,
    can_view,
    can_create,
    can_edit,
    can_delete,
    created_by
)
VALUES (
    '<manager-role-id>',
    'billing',
    '<branch-id>',
    TRUE,
    TRUE,
    TRUE,  -- Can edit (includes discount fields)
    FALSE,
    '<admin-user-id>'
)
ON CONFLICT (role_id, module_name, branch_id) DO UPDATE
SET can_edit = TRUE;
```

---

### Step 6: Restart Application

```bash
# Stop Flask application
# (Ctrl+C or kill process)

# Restart Flask application
cd "C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\Skinspire_v2"
python run.py
```

**Check for errors in startup logs**:
- Look for migration errors
- Verify models loaded successfully
- Confirm discount_api blueprint registered

---

## TEST CASES

### 🧪 TEST GROUP 1: Service Bulk Discount (Existing Feature)

#### Test 1.1: Single Service, Quantity Meets Threshold
**Scenario**: Add 1 service with quantity = 5

**Steps**:
1. Login as any user
2. Go to Billing → Create Invoice
3. Select patient: Ram Kumar
4. Add line item:
   - Type: Service
   - Service: Advanced Facial
   - Quantity: 5
   - Unit Price: ₹1,000

**Expected Result**:
- ✅ Checkbox "Apply Bulk Service Discount" auto-checks
- ✅ Badge shows "✓ Eligible (5 services)"
- ✅ Discount field shows: 15.00
- ✅ Blue "Bulk" badge appears next to discount field
- ✅ Line total: ₹1,000 × 5 = ₹5,000 - 15% = ₹4,250
- ✅ Invoice summary shows discount amount: ₹750

**Pass Criteria**: All checkmarks above

---

#### Test 1.2: Multiple Services, Combined Quantity Meets Threshold
**Scenario**: Add 2 services with total quantity = 6

**Steps**:
1. Create invoice with:
   - Line 1: Advanced Facial × 3 @ ₹1,000
   - Line 2: Laser Hair Reduction × 3 @ ₹2,000

**Expected Result**:
- ✅ Total service count: 6 (counted correctly, not 2 line items)
- ✅ Checkbox auto-checks
- ✅ Badge shows "✓ Eligible (6 services)"
- ✅ BOTH line items get 15% discount
- ✅ Line 1 total: ₹3,000 - 15% = ₹2,550
- ✅ Line 2 total: ₹6,000 - 15% = ₹5,100
- ✅ Total discount: ₹1,350

**Pass Criteria**: Quantity counted correctly (not line items)

---

#### Test 1.3: Service Below Threshold
**Scenario**: Add service with quantity = 4 (below threshold 5)

**Steps**:
1. Add line item: Advanced Facial × 4 @ ₹1,000

**Expected Result**:
- ✅ Checkbox NOT auto-checked
- ✅ Badge shows "Add 1 more service to unlock bulk discount"
- ✅ Discount field: 0
- ✅ No "Bulk" badge
- ✅ Line total: ₹4,000 (no discount)

**Pass Criteria**: Correct threshold detection

---

#### Test 1.4: Max Discount Cap Enforcement
**Scenario**: Service with bulk_discount_percent > max_discount

**Steps**:
1. Add line item:
   - Service: Hair Restoration (bulk_discount_percent = 25%, max_discount = 15%)
   - Quantity: 5
   - Unit Price: ₹3,000

**Expected Result**:
- ✅ Checkbox auto-checks
- ✅ Discount capped at 15% (not 25%)
- ✅ Discount field shows: 15.00
- ✅ Line total: ₹15,000 - 15% = ₹12,750
- ✅ Console log shows: "Discount capped at max_discount: 15%"

**Pass Criteria**: max_discount cap enforced

---

### 🧪 TEST GROUP 2: Medicine Bulk Discount (New Feature)

#### Test 2.1: Single Medicine, Quantity Meets Threshold
**Scenario**: Add 1 medicine with quantity = 10

**Steps**:
1. Add line item:
   - Type: Medicine
   - Medicine: Paracetamol 500mg
   - Quantity: 10 strips
   - Unit Price: ₹50

**Expected Result**:
- ✅ Medicine count: 10 (≥ threshold 5)
- ✅ Medicine eligible for bulk discount
- ✅ Discount field shows: 15.00
- ✅ "Bulk" badge appears
- ✅ Line total: ₹500 - 15% = ₹425
- ✅ Summary shows medicine discount

**Pass Criteria**: Medicine discount applies correctly

---

#### Test 2.2: Multiple Medicines, Combined Quantity
**Scenario**: Add 2 medicines with total quantity = 15

**Steps**:
1. Add line items:
   - Medicine 1: Paracetamol × 10 @ ₹50
   - Medicine 2: Vitamin D3 × 5 @ ₹100

**Expected Result**:
- ✅ Total medicine count: 15
- ✅ BOTH medicines get bulk discount
- ✅ Line 1 total: ₹500 - 15% = ₹425
- ✅ Line 2 total: ₹500 - 15% = ₹425
- ✅ Total medicine discount: ₹150

**Pass Criteria**: All medicines discounted

---

#### Test 2.3: Medicine Below Threshold
**Scenario**: Add medicine with quantity = 3 (below threshold)

**Steps**:
1. Add line item: Antibiotic × 3 @ ₹200

**Expected Result**:
- ✅ No discount applied
- ✅ Discount field: 0
- ✅ Message: "Add 2 more medicines..."
- ✅ Line total: ₹600 (no discount)

**Pass Criteria**: Threshold enforced for medicines

---

#### Test 2.4: Medicine Max Discount Cap
**Scenario**: Medicine with capped discount

**Steps**:
1. Add line item:
   - Medicine: Antibiotic (bulk_discount_percent = 25%, max_discount = 10%)
   - Quantity: 10
   - Unit Price: ₹200

**Expected Result**:
- ✅ Discount capped at 10% (not 25%)
- ✅ Line total: ₹2,000 - 10% = ₹1,800

**Pass Criteria**: max_discount cap works for medicines

---

### 🧪 TEST GROUP 3: Mixed Invoices (Services + Medicines)

#### Test 3.1: Both Services and Medicines Eligible
**Scenario**: Invoice with sufficient quantity of both

**Steps**:
1. Add line items:
   - Service: Advanced Facial × 5 @ ₹1,000
   - Medicine: Paracetamol × 10 @ ₹50

**Expected Result**:
- ✅ Service count: 5 (eligible)
- ✅ Medicine count: 10 (eligible)
- ✅ Both get bulk discounts
- ✅ Service discount: ₹750 (15% of ₹5,000)
- ✅ Medicine discount: ₹75 (15% of ₹500)
- ✅ Total discount: ₹825
- ✅ Summary shows separate counts

**Pass Criteria**: Independent counting for each type

---

#### Test 3.2: Services Eligible, Medicines Not
**Scenario**: Sufficient services, insufficient medicines

**Steps**:
1. Add line items:
   - Service: Advanced Facial × 5 @ ₹1,000
   - Medicine: Vitamin D3 × 3 @ ₹100

**Expected Result**:
- ✅ Services get discount (count = 5)
- ✅ Medicines NO discount (count = 3)
- ✅ Service total: ₹4,250 (with discount)
- ✅ Medicine total: ₹300 (no discount)
- ✅ Message: "Add 2 more medicines..."

**Pass Criteria**: Types calculated independently

---

#### Test 3.3: Medicines Eligible, Services Not
**Scenario**: Sufficient medicines, insufficient services

**Steps**:
1. Add line items:
   - Service: Advanced Facial × 3 @ ₹1,000
   - Medicine: Paracetamol × 10 @ ₹50

**Expected Result**:
- ✅ Services NO discount (count = 3)
- ✅ Medicines get discount (count = 10)
- ✅ Service total: ₹3,000 (no discount)
- ✅ Medicine total: ₹425 (with discount)

**Pass Criteria**: Independent eligibility

---

### 🧪 TEST GROUP 4: Role-Based Permissions

#### Test 4.1: Manager User (Can Edit Discount)
**Scenario**: Login as manager, check discount field editability

**Steps**:
1. Login as manager user
2. Create invoice
3. Add service line item
4. Check discount field state

**Expected Result**:
- ✅ Discount field: WHITE background
- ✅ No lock icon
- ✅ Can type in discount field
- ✅ Normal cursor (not "not-allowed")
- ✅ No readonly attribute
- ✅ Can manually override discount

**Pass Criteria**: Field is editable

---

#### Test 4.2: Front Desk User (Cannot Edit Discount)
**Scenario**: Login as front desk user, check discount field

**Steps**:
1. Login as front desk user (without edit_discount permission)
2. Create invoice
3. Add service line item
4. Check discount field state

**Expected Result**:
- ✅ Discount field: GRAY background (#f3f4f6)
- ✅ Lock icon visible on right side
- ✅ Cannot type in discount field
- ✅ Cursor shows "not-allowed"
- ✅ Readonly attribute present
- ✅ Tooltip: "Auto-calculated discount (Manager can edit)"
- ✅ Auto-calculated discount still applies

**Pass Criteria**: Field is readonly, visual indicators present

---

#### Test 4.3: Manager Can Override Auto-Calculated Discount
**Scenario**: Manager manually changes discount

**Steps**:
1. Login as manager
2. Add line item with auto-calculated discount (e.g., 15%)
3. Manually change discount field to 20%
4. Save invoice

**Expected Result**:
- ✅ Can change discount value
- ✅ New discount applies to line total
- ✅ Invoice saves with manual discount
- ✅ No validation errors

**Pass Criteria**: Manual override works

---

#### Test 4.4: Front Desk Cannot Override (Readonly Enforcement)
**Scenario**: Front desk tries to change discount

**Steps**:
1. Login as front desk user
2. Add line item with auto-calculated discount
3. Try to click/type in discount field

**Expected Result**:
- ✅ Field does not respond to clicks
- ✅ Keyboard input ignored
- ✅ Field remains readonly
- ✅ Discount stays at auto-calculated value

**Pass Criteria**: Readonly enforced client-side

---

### 🧪 TEST GROUP 5: API Testing

#### Test 5.1: Discount Calculate API - Services Only
**API Endpoint**: `POST /api/discount/calculate`

**Request Payload**:
```json
{
    "hospital_id": "your-hospital-id",
    "patient_id": "patient-id",
    "line_items": [
        {
            "item_type": "Service",
            "item_id": "service-id",
            "quantity": 5,
            "unit_price": 1000.00
        }
    ]
}
```

**Expected Response**:
```json
{
    "success": true,
    "line_items": [
        {
            "item_type": "Service",
            "item_id": "service-id",
            "quantity": 5,
            "unit_price": 1000.00,
            "discount_percent": 15.00,
            "discount_amount": 750.00,
            "discount_type": "bulk",
            "discount_metadata": {
                "service_count": 5,
                "min_threshold": 5,
                "service_name": "Advanced Facial"
            }
        }
    ],
    "summary": {
        "total_services": 5,
        "service_discount_eligible": true,
        "services_needed": 0,
        "total_medicines": 0,
        "medicine_discount_eligible": false,
        "medicines_needed": 5,
        "bulk_discount_threshold": 5,
        "total_original_price": 5000.00,
        "total_discount": 750.00,
        "total_final_price": 4250.00,
        "discount_percentage": 15.0
    }
}
```

**Pass Criteria**: Correct discount calculation and summary

---

#### Test 5.2: Discount Calculate API - Medicines Only
**Request Payload**:
```json
{
    "hospital_id": "your-hospital-id",
    "patient_id": "patient-id",
    "line_items": [
        {
            "item_type": "Medicine",
            "item_id": "medicine-id",
            "quantity": 10,
            "unit_price": 50.00
        }
    ]
}
```

**Expected Response**:
```json
{
    "success": true,
    "line_items": [
        {
            "item_type": "Medicine",
            "discount_percent": 15.00,
            "discount_amount": 75.00,
            "discount_type": "bulk"
        }
    ],
    "summary": {
        "total_services": 0,
        "total_medicines": 10,
        "medicine_discount_eligible": true,
        "total_discount": 75.00
    }
}
```

**Pass Criteria**: Medicine discount calculated correctly

---

#### Test 5.3: Discount Calculate API - Mixed (Services + Medicines)
**Request Payload**:
```json
{
    "hospital_id": "your-hospital-id",
    "line_items": [
        {
            "item_type": "Service",
            "item_id": "service-id",
            "quantity": 5,
            "unit_price": 1000.00
        },
        {
            "item_type": "Medicine",
            "item_id": "medicine-id",
            "quantity": 10,
            "unit_price": 50.00
        }
    ]
}
```

**Expected Response**:
```json
{
    "success": true,
    "summary": {
        "total_services": 5,
        "service_discount_eligible": true,
        "total_medicines": 10,
        "medicine_discount_eligible": true,
        "total_original_price": 5500.00,
        "total_discount": 825.00,
        "total_final_price": 4675.00
    }
}
```

**Pass Criteria**: Both types discounted independently

---

### 🧪 TEST GROUP 6: Edge Cases

#### Test 6.1: Exactly at Threshold
**Scenario**: Quantity exactly equals threshold (5)

**Steps**:
1. Add service: Advanced Facial × 5

**Expected Result**:
- ✅ Discount applies (≥ 5, not just > 5)
- ✅ Badge shows "✓ Eligible"

**Pass Criteria**: Threshold is inclusive (≥ not >)

---

#### Test 6.2: Just Below Threshold
**Scenario**: Quantity = 4.99... rounds to 4

**Steps**:
1. Try to add fractional quantity (if allowed)

**Expected Result**:
- ✅ System prevents fractional quantities OR
- ✅ Rounds down to 4 (no discount)

**Pass Criteria**: No discount at 4.999

---

#### Test 6.3: Zero Quantity
**Scenario**: Line item with quantity = 0

**Steps**:
1. Add line item with quantity = 0

**Expected Result**:
- ✅ Line item not counted
- ✅ No discount applied
- ✅ No errors

**Pass Criteria**: Graceful handling

---

#### Test 6.4: Negative Quantity (If Possible)
**Scenario**: Try to enter negative quantity

**Expected Result**:
- ✅ Validation prevents negative quantity
- ✅ Error message shown

**Pass Criteria**: Cannot create negative quantity

---

#### Test 6.5: Service/Medicine with NULL bulk_discount_percent
**Scenario**: Entity without discount configured

**Steps**:
1. Add service/medicine with bulk_discount_percent = NULL or 0

**Expected Result**:
- ✅ No discount applied (even if threshold met)
- ✅ Discount field: 0
- ✅ No "Bulk" badge

**Pass Criteria**: Only configured entities get discount

---

#### Test 6.6: Checkbox Manual Toggle
**Scenario**: User manually checks/unchecks checkbox

**Steps**:
1. Add line items (eligible)
2. Uncheck "Apply Bulk Service Discount"
3. Re-check checkbox

**Expected Result**:
- ✅ Unchecking removes discount from all line items
- ✅ Re-checking reapplies discount
- ✅ No infinite loops
- ✅ User intent preserved (doesn't auto-toggle after manual change)

**Pass Criteria**: Manual toggle works, no loops

---

## TEST RESULT TEMPLATE

### Test Execution Log

| Test ID | Test Name | Status | Notes | Tester | Date |
|---------|-----------|--------|-------|--------|------|
| 1.1 | Single Service Threshold | ⏳ | | | |
| 1.2 | Multiple Services Combined | ⏳ | | | |
| 1.3 | Service Below Threshold | ⏳ | | | |
| 1.4 | Max Discount Cap | ⏳ | | | |
| 2.1 | Single Medicine Threshold | ⏳ | | | |
| 2.2 | Multiple Medicines Combined | ⏳ | | | |
| 2.3 | Medicine Below Threshold | ⏳ | | | |
| 2.4 | Medicine Max Discount Cap | ⏳ | | | |
| 3.1 | Mixed Invoice - Both Eligible | ⏳ | | | |
| 3.2 | Mixed - Services Only Eligible | ⏳ | | | |
| 3.3 | Mixed - Medicines Only Eligible | ⏳ | | | |
| 4.1 | Manager Can Edit | ⏳ | | | |
| 4.2 | Front Desk Readonly | ⏳ | | | |
| 4.3 | Manager Override | ⏳ | | | |
| 4.4 | Front Desk Cannot Override | ⏳ | | | |
| 5.1 | API - Services Only | ⏳ | | | |
| 5.2 | API - Medicines Only | ⏳ | | | |
| 5.3 | API - Mixed | ⏳ | | | |
| 6.1 | Exactly at Threshold | ⏳ | | | |
| 6.2 | Just Below Threshold | ⏳ | | | |
| 6.3 | Zero Quantity | ⏳ | | | |
| 6.4 | Negative Quantity | ⏳ | | | |
| 6.5 | NULL Discount Config | ⏳ | | | |
| 6.6 | Checkbox Manual Toggle | ⏳ | | | |

**Legend**:
- ⏳ Not Started
- 🔄 In Progress
- ✅ Passed
- ❌ Failed
- ⚠️ Blocked

---

## TROUBLESHOOTING GUIDE

### Issue 1: Migration Fails
**Symptom**: psql returns error when executing migration

**Possible Causes**:
- Database connection failed
- Table already has columns
- Constraint violation

**Solution**:
```sql
-- Check if columns exist
SELECT column_name FROM information_schema.columns
WHERE table_name = 'medicines'
  AND column_name IN ('standard_discount_percent', 'bulk_discount_percent', 'max_discount');

-- If columns exist, drop and re-add (or skip migration)
ALTER TABLE medicines DROP COLUMN IF EXISTS bulk_discount_percent CASCADE;
-- Then re-run migration
```

---

### Issue 2: Discount Not Applying
**Symptom**: Checkbox checks but no discount appears

**Possible Causes**:
- Service/Medicine has bulk_discount_percent = 0
- API call failing
- JavaScript error

**Debug Steps**:
1. Open browser console (F12)
2. Check for JavaScript errors
3. Check Network tab for API call to `/api/discount/calculate`
4. Verify response contains discount_percent > 0
5. Check service/medicine in database:
   ```sql
   SELECT service_name, bulk_discount_percent, max_discount
   FROM services
   WHERE service_id = '<service-id>';
   ```

---

### Issue 3: Discount Field Readonly for Manager
**Symptom**: Manager sees gray field with lock icon

**Possible Cause**: User doesn't have edit_discount permission

**Solution**:
```sql
-- Check user permissions
SELECT * FROM role_module_branch_access
WHERE role_id IN (
    SELECT role_id FROM user_role_mapping WHERE user_id = '<user-id>'
)
AND module_name = 'billing';

-- Grant permission
UPDATE role_module_branch_access
SET can_edit = TRUE
WHERE role_id = '<manager-role-id>'
  AND module_name = 'billing';
```

---

### Issue 4: Medicine Discount Not Working
**Symptom**: Medicine lines don't get discount even when eligible

**Possible Causes**:
- Migration not executed
- API not handling medicines
- Frontend not collecting medicine line items

**Debug Steps**:
1. Verify migration executed:
   ```sql
   \d medicines  -- Check columns
   ```
2. Check API logs for medicine processing
3. Check browser console for medicine line items being sent to API

---

## POST-TESTING ACTIONS

### If All Tests Pass ✅
1. Document test results
2. Deploy to production
3. Train users on new features
4. Monitor for issues in production

### If Tests Fail ❌
1. Document failed test cases
2. Create bug tickets with reproduction steps
3. Assign to developer for fixes
4. Re-test after fixes

### If Blocked ⚠️
1. Document blockers
2. Escalate to project manager
3. Adjust timeline if needed

---

## SIGN-OFF

### Tester Sign-off
- **Tested By**: ___________________
- **Date**: ___________________
- **Overall Status**: ⏳ Not Started | 🔄 In Progress | ✅ Passed | ❌ Failed
- **Recommendation**: Proceed to Production | Needs Fixes | Blocked

### Manager Sign-off
- **Approved By**: ___________________
- **Date**: ___________________
- **Deployment Approval**: ✅ Approved | ❌ Not Approved

---

**Last Updated**: 21-November-2025, 5:00 AM IST
**Status**: Ready for Testing
**Next Review**: After test execution
