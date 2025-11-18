# Field Name Error - Patient Model
**Date**: 2025-11-13
**Error**: AttributeError: 'Patient' object has no attribute 'patient_number'

## What Went Wrong

**Mistake**: Used `patient.patient_number` and `patient.phone_number` without checking the actual Patient model.

**Root Cause**: Did NOT follow the documented policy in CLAUDE.md:
```
### CRITICAL: Field Name and Configuration Verification
**NEVER assume or imagine field names, configuration parameters, or model attributes!**

Before writing ANY code that references database fields:
1. Check app/models/transaction.py for transaction models
2. Check app/models/master.py for master data models
3. Check app/models/views.py for database view models
4. Check app/models/base.py for mixin fields
```

## Actual Patient Model Fields

**File**: `app/models/master.py` (lines 172-222)

```python
class Patient(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    __tablename__ = 'patients'

    # Primary Key
    patient_id = Column(UUID(as_uuid=True), primary_key=True)

    # Hospital/Branch
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'))
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))

    # ✅ MRN - Medical Record Number (THIS is the patient number!)
    mrn = Column(String(20), unique=True)

    # Name Fields
    title = Column(String(10))
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))

    # Other Fields
    blood_group = Column(String(5))

    # ✅ JSONB Fields - Data stored as JSON
    personal_info = Column(JSONB, nullable=False)  # first_name, last_name, dob, gender
    contact_info = Column(JSONB, nullable=False)   # email, phone, address
    medical_info = Column(Text)                    # Encrypted
    emergency_contact = Column(JSONB)
    documents = Column(JSONB)
    preferences = Column(JSONB)

    is_active = Column(Boolean, default=True)
```

## What Fields DON'T Exist

❌ `patient_number` - Does NOT exist! Use `mrn` instead
❌ `phone_number` - Does NOT exist! Phone is in `contact_info` JSONB field

## Correct Way to Access Fields

### Patient Number (MRN)
```python
# ❌ WRONG
patient.patient_number  # AttributeError!

# ✅ CORRECT
patient.mrn  # Medical Record Number
```

### Phone Number
```python
# ❌ WRONG
patient.phone_number  # AttributeError!

# ✅ CORRECT - Extract from JSONB
phone_number = ''
if patient.contact_info:
    if isinstance(patient.contact_info, dict):
        phone_number = patient.contact_info.get('phone', '')
    elif isinstance(patient.contact_info, str):
        import json
        contact_info = json.loads(patient.contact_info)
        phone_number = contact_info.get('phone', '')
```

## The Fix Applied

**File**: `app/services/ar_statement_service.py` (lines 95-113)

**Before** (WRONG):
```python
patient_info = {
    'patient_id': str(patient.patient_id),
    'full_name': patient.full_name,
    'patient_number': patient.patient_number or '',  # ❌ Does not exist!
    'phone_number': patient.phone_number or ''       # ❌ Does not exist!
}
```

**After** (CORRECT):
```python
# Extract phone number from contact_info JSONB field
phone_number = ''
if patient.contact_info:
    if isinstance(patient.contact_info, dict):
        phone_number = patient.contact_info.get('phone', '')
    elif isinstance(patient.contact_info, str):
        try:
            import json
            contact_info = json.loads(patient.contact_info)
            phone_number = contact_info.get('phone', '')
        except:
            pass

patient_info = {
    'patient_id': str(patient.patient_id),
    'full_name': patient.full_name,
    'patient_number': patient.mrn or '',  # ✅ MRN is the patient number
    'phone_number': phone_number
}
```

## Lesson Learned

**MANDATORY PROCESS** before writing ANY code that uses model fields:

### Step 1: Read the Model Definition
```bash
# For Patient model
Read: app/models/master.py (find class Patient)
```

### Step 2: List ALL Available Fields
Write down every Column() definition:
- patient_id
- hospital_id
- branch_id
- mrn
- title
- first_name
- last_name
- full_name
- blood_group
- personal_info (JSONB)
- contact_info (JSONB)
- medical_info
- emergency_contact (JSONB)
- documents (JSONB)
- preferences (JSONB)
- is_active

### Step 3: Check Mixins
```python
class Patient(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
```

This means Patient ALSO has:
- From TimestampMixin: created_at, updated_at, created_by, updated_by
- From TenantMixin: tenant_id property (maps to hospital_id)
- From SoftDeleteMixin: is_deleted, deleted_at, deleted_by

### Step 4: Verify JSONB Field Structure
If using JSONB fields, check existing code or database to see structure:
```python
# personal_info structure
{
    'first_name': 'John',
    'last_name': 'Doe',
    'dob': '1990-01-01',
    'gender': 'M'
}

# contact_info structure
{
    'phone': '+91-9876543210',
    'email': 'john@example.com',
    'address': {...}
}
```

### Step 5: Only Then Write Code
After completing steps 1-4, write code using ONLY verified field names.

## Reference: Common Patient Fields

**Direct Column Access**:
- `patient.patient_id` - UUID primary key
- `patient.hospital_id` - Hospital UUID
- `patient.branch_id` - Branch UUID (nullable)
- `patient.mrn` - Medical Record Number (patient number)
- `patient.full_name` - Full name (Column or hybrid_property)
- `patient.blood_group` - Blood group
- `patient.is_active` - Active status
- `patient.is_deleted` - Soft delete flag (from mixin)
- `patient.created_at` - Created timestamp (from mixin)
- `patient.updated_at` - Updated timestamp (from mixin)

**JSONB Field Access** (requires extraction):
- `patient.personal_info.get('first_name')` or `patient.first_name` (if direct column exists)
- `patient.personal_info.get('last_name')` or `patient.last_name` (if direct column exists)
- `patient.personal_info.get('dob')`
- `patient.personal_info.get('gender')`
- `patient.contact_info.get('phone')`
- `patient.contact_info.get('email')`
- `patient.contact_info.get('address')`
- `patient.emergency_contact.get('name')`
- `patient.emergency_contact.get('relation')`
- `patient.emergency_contact.get('contact')`

## Why This Matters

1. **Runtime Errors**: AttributeError crashes the application
2. **User Experience**: Feature fails when users try to use it
3. **Trust**: Repeated errors damage credibility
4. **Time Waste**: Debugging takes longer than checking upfront
5. **Policy Violation**: CLAUDE.md explicitly requires field verification

## Commitment

**Going Forward**:
1. ✅ ALWAYS read model definition BEFORE writing code
2. ✅ NEVER assume field names
3. ✅ Check CLAUDE.md verification process
4. ✅ Verify JSONB field structures
5. ✅ Test code paths that use model fields

## Status

✅ **FIXED** - ar_statement_service.py now uses correct field names:
- `patient.mrn` instead of `patient.patient_number`
- `patient.contact_info.get('phone')` instead of `patient.phone_number`

**Application should now work correctly.**
