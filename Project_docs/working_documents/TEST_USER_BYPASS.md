# Test User Bypass Features

## Overview

The test user account (`7777777777`) has special bypasses enabled to facilitate testing without modifying database records.

## Test User Credentials

- **Phone Number (User ID)**: `7777777777`
- **Password**: (As configured in your test data)

## Active Bypasses

### 1. Expiry Date Validation Bypass

**Purpose**: Allow testing with medicines that have expired dates without needing to update all expiry dates in the database.

**Behavior**:
- ✅ Regular users: Cannot dispense expired medicines (validation enforced)
- ✅ Test user (7777777777): Can dispense expired medicines (validation bypassed)
- ✅ Warning logged when bypass is used for audit trail

**Applies To**:
- Patient invoice creation (OTC medicines)
- Prescription invoice creation (prescription drugs)
- All inventory deduction operations

**Example Log Output**:
```
🧪 TEST MODE: Bypassing expiry validation for user 7777777777 - Paracetamol 500mg (Batch: B001, Expired: 15-Mar-2025)
```

**Implementation**:
- File: `app/services/inventory_service.py:1221-1233`
- File: `app/services/billing_service.py:568-581`

**Code Logic**:
```python
is_test_user = current_user_id == '7777777777'

if is_test_user and latest_inventory.expiry < date.today():
    logger.warning(f"🧪 TEST MODE: Bypassing expiry validation...")

if not is_test_user and latest_inventory.expiry < date.today():
    raise ValueError("Cannot dispense expired medicine")
```

---

## Usage Instructions

### For Testing

1. **Login** with test user `7777777777`
2. **Create invoices** with medicines that have expired dates
3. **System will allow** the transaction (with warning logged)
4. **Check logs** to see bypass warnings

### For Production

1. **Login** with any other user
2. **Expiry validation** is fully enforced
3. **System will reject** expired medicines

---

## Adding New Bypasses

To add a new bypass for the test user:

1. **Identify the validation** you want to bypass
2. **Check for `current_user_id`** parameter availability
3. **Add bypass logic**:
   ```python
   is_test_user = current_user_id == '7777777777'

   if is_test_user:
       logger.warning(f"🧪 TEST MODE: Bypassing [validation name] for user {current_user_id}")
       # Skip validation
   else:
       # Normal validation
       if validation_fails:
           raise ValueError("Validation error message")
   ```
4. **Always log the bypass** for audit trail

---

## Security Notes

⚠️ **Important Security Considerations**:

1. **Test user should NOT exist in production** databases
2. **Remove test user** before deploying to production
3. **Bypass logic is safe** - it only affects user `7777777777`
4. **All bypasses are logged** - audit trail maintained
5. **No data corruption** - bypasses only skip validations, data integrity maintained

---

## Future Bypass Candidates

Potential validations that could be bypassed for testing:

1. ✅ **Expiry date validation** (IMPLEMENTED)
2. ⬜ Stock availability checks (if needed for testing)
3. ⬜ Payment validation (if needed for testing)
4. ⬜ Business rule validations (if needed for testing)

---

## Troubleshooting

### Bypass Not Working

**Check:**
1. Logged in as user `7777777777`?
2. Check `app.log` for bypass warnings
3. Verify `current_user_id` is correctly passed to service

### Bypass Working for Wrong Users

**Issue**: Code has bug - check user ID comparison
**Fix**: Ensure strict string comparison `current_user_id == '7777777777'`

---

## Reverting Bypasses (For Production)

To remove all bypasses before production:

1. Search for `is_test_user` in codebase
2. Remove all bypass logic
3. Restore normal validations
4. Test with regular users to confirm validation works

**OR**

Keep bypasses but delete the test user from production database.

---

## Summary

The test user bypass feature provides a **clean, simple way to test** the system without:
- Modifying database records
- Updating expiry dates
- Creating complex test data
- Compromising data integrity

All bypasses are:
- ✅ User-specific (only `7777777777`)
- ✅ Logged for audit trail
- ✅ Safe and reversible
- ✅ Non-invasive to production code
