# Package Payment Plan - Balance Showing Zero Investigation
**Date**: 2025-11-13
**Status**: 🔍 UNDER INVESTIGATION

## Database Verification ✅

Verified that database has correct balance_amount values:

```sql
SELECT plan_id, patient_name, package_name, total_amount, paid_amount, balance_amount
FROM package_payment_plans_view
LIMIT 5;
```

**Results**:
| Patient Name | Package Name | Total | Paid | Balance |
|--------------|--------------|-------|------|---------|
| Vinodkumar Seetharam | Acne Care Package | 5900.00 | 0.00 | **5900.00** ✅ |
| Ram Kumar | Acne Care Package | 5900.00 | 0.00 | **5900.00** ✅ |
| Vinodkumar Seetharam | Weight Loss Program | 9440.00 | 0.00 | **9440.00** ✅ |
| Ms Patient1 Test1 | Hair Restoration Package | 5900.00 | 0.00 | **5900.00** ✅ |
| Vinodkumar Seetharam | Weight Loss Program | 9440.00 | 0.00 | **9440.00** ✅ |

**Conclusion**: ✅ Database view has correct balance_amount values. Issue is NOT in database.

---

## Database View Definition

**File**: `app/database/view scripts/package_payment_plans_view v1.0.sql`

**Balance Calculation** (line 59):
```sql
ppp.balance_amount,  -- Calculated at table level
```

The balance_amount is stored as a computed column in the package_payment_plans table:
```sql
balance_amount = total_amount - paid_amount
```

✅ **Verified**: View correctly includes balance_amount column.

---

## Model Verification

**File**: `app/models/views.py`

**PackagePaymentPlanView Model**:
```python
class PackagePaymentPlanView(Base):
    __tablename__ = 'package_payment_plans_view'

    total_amount = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2))
    balance_amount = Column(Numeric(12, 2))  # ✅ Column defined
```

✅ **Verified**: Model has balance_amount column correctly mapped.

---

## Configuration Verification

**File**: `app/config/modules/package_payment_plan_config.py`

**Balance Field Definition** (lines 148-164):
```python
FieldDefinition(
    name='balance_amount',
    label='Balance',
    field_type=FieldType.CURRENCY,
    readonly=True,
    show_in_list=True,  # ✅ Showing in list
    show_in_detail=True,
    show_in_form=True,
    sortable=True,
    width='90px',
    css_classes='text-end align-top'
)
```

✅ **Verified**: Field configured to show in list view.

---

## Possible Causes

### 1. Service Layer Not Fetching Field 🔍
**Likelihood**: Medium

**Check**:
- Verify `PackagePaymentService.search_data()` includes balance_amount in SELECT
- Check if service transforms data and drops balance_amount
- Verify data_assembler includes balance_amount in list response

**Test**: Check browser network tab to see if API response has balance_amount

---

### 2. Caching Issue 🔍
**Likelihood**: High

**Cause**: Old cached list data without balance_amount being served

**Solution**:
```python
# In app/engine/universal_service_cache.py
from app.engine.universal_service_cache import invalidate_service_cache_for_entity

# Clear ALL package_payment_plans caches
invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
```

**Test**:
1. Restart application
2. Clear browser cache
3. Hard refresh (Ctrl+Shift+R)

---

### 3. Frontend Display Issue 🔍
**Likelihood**: Low

**Check**: Inspect element in browser to see if:
- Column exists but hidden
- Data present but CSS hiding it
- JavaScript error preventing render

---

### 4. Data Assembler Filtering 🔍
**Likelihood**: Medium

**Check**:
- `app/engine/data_assembler.py` may filter out fields not explicitly in view configuration
- Universal engine may only include fields marked as `show_in_list=True`

**Already Fixed**: We already set `show_in_list=True` for balance_amount

---

## Next Steps to Diagnose

### Step 1: Check API Response
```
1. Open browser DevTools (F12)
2. Go to Network tab
3. Navigate to package payment plans list
4. Find API call to /api/universal/package_payment_plans/search
5. Check response JSON - does it include balance_amount?
```

**If YES**: Issue is in frontend rendering
**If NO**: Issue is in service layer

---

### Step 2: Check Service Layer
```python
# In app/services/package_payment_service.py or similar

def search_data(self, filters, hospital_id, branch_id=None, page=1, per_page=20, **kwargs):
    # Check if query includes balance_amount
    query = session.query(PackagePaymentPlanView)

    # Verify fields being selected
    # Should include: .balance_amount
```

---

### Step 3: Clear Cache and Test
```bash
# Restart application
python run.py

# In browser:
# 1. Clear cache
# 2. Hard refresh (Ctrl+Shift+R)
# 3. Check list view
```

---

### Step 4: Check Universal Engine Data Assembler

**File**: `app/engine/data_assembler.py`

The data assembler might be filtering fields based on configuration. Verify that it:
1. Reads `show_in_list=True` fields
2. Includes balance_amount in list response
3. Doesn't drop currency fields

---

## Temporary Workaround

If issue persists, add explicit field to searchable_fields to force inclusion:

```python
PACKAGE_PAYMENT_PLANS_CONFIG = EntityConfiguration(
    # ... other config
    searchable_fields=['plan_id', 'patient_id', 'package_id', 'patient_name', 'package_name'],
    include_calculated_fields=[
        'balance_amount',  # Force include in responses
        'patient_name',
        'package_name'
    ]
)
```

---

## Most Likely Cause: Cache

Based on similar issues in the past, the most likely cause is **stale cached data** from before balance_amount was properly configured.

**Solution**:
1. ✅ Configuration already correct
2. ✅ Database has correct data
3. ⚠️ Need to clear cache and restart application
4. ⚠️ Need to clear browser cache

---

## User Report

**Original Issue**: "balance showing zero for all rows"

**After Fixes**: "balance issue is still there"

**Database Shows**: Balance has correct non-zero values (5900.00, 9440.00, etc.)

**Conclusion**: Issue is NOT in database, NOT in configuration. Most likely caching or service layer.

---

## Recommendation

**Immediate Action**:
1. Restart Flask application
2. Clear browser cache
3. Test list view
4. If still showing zero, check browser DevTools Network tab for API response
5. Share API response with developer to diagnose service layer issue

**Long-term Fix**:
- Add balance_amount to include_calculated_fields in config
- Verify service layer explicitly selects balance_amount
- Add cache invalidation after config changes
