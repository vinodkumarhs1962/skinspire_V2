# Database Service Methods Documentation - Added to CLAUDE.md
**Date**: 2025-11-13
**Status**: ✅ COMPLETED

## Overview

Added comprehensive documentation to CLAUDE.md about database service utility methods for working with detached SQLAlchemy sessions. This prevents future errors like the `to_dict` import error that occurred in the AR statement implementation.

## What Was Added

### New Section: "Database Service Methods for Detached Sessions"
**Location**: CLAUDE.md (lines 312-562)
**Inserted After**: Database Policy: Python-Only Business Logic section
**Inserted Before**: Universal Engine Usage Guidelines section

## Documentation Sections

### 1. Introduction
- **SQLAlchemy Session Lifecycle**: Explains that entities become detached when session closes
- **Purpose**: Two utility methods to safely work with entities outside session context

### 2. Method 1: `get_entity_dict(entity)` - Convert to Dictionary

**When to Use:**
- ✅ API JSON responses
- ✅ Template data
- ✅ Cache storage
- ✅ Dictionary representation for data manipulation

**Function Details:**
```python
from app.services.database_service import get_entity_dict

# Converts SQLAlchemy entity to dict
patient_dict = get_entity_dict(patient)

# Returns:
{
    'patient_id': '...',
    'mrn': 'PAT-00123',
    'full_name': 'John Doe',
    'contact_info': {'phone': '...', 'email': '...'},
    # ... all non-internal attributes
}
```

**Example Usage:**
- ✅ CORRECT: Convert inside session context
- ❌ WRONG: Access entity attributes after session closes

### 3. Method 2: `get_detached_copy(entity)` - Create Detached Copy

**When to Use:**
- ✅ Need entity object after session closes
- ✅ Functions expecting object attribute access
- ✅ Hybrid property access (@hybrid_property)
- ✅ Working with pre-loaded relationships

**Function Details:**
```python
from app.services.database_service import get_detached_copy

# Creates a new instance with copied attributes
detached_invoice = get_detached_copy(invoice)

# Can access attributes after session closes
print(detached_invoice.invoice_number)  # Works!
```

**Important Limitations:**
- ⚠️ Only copies **loaded** attributes
- ⚠️ Does NOT copy relationships unless explicitly loaded
- ⚠️ Does NOT support lazy loading

### 4. Comparison Table

| Scenario | Use `get_entity_dict` | Use `get_detached_copy` |
|----------|----------------------|------------------------|
| API JSON response | ✅ YES | ❌ No |
| Template data | ✅ YES | ❌ No |
| Cache storage | ✅ YES | ❌ No |
| Need object attributes | ❌ No | ✅ YES |
| Need hybrid properties | ❌ No | ✅ YES |
| Working with relationships | ❌ No | ✅ YES (if pre-loaded) |

### 5. Common Patterns

**Pattern 1: Service Layer Returns Dict**
```python
class PatientService:
    def get_patient_by_id(self, patient_id, hospital_id):
        with get_db_session() as session:
            patient = session.query(Patient).filter(...).first()
            return get_entity_dict(patient)  # Convert before returning
```

**Pattern 2: API Endpoint Returns JSON**
```python
@billing_bp.route('/api/invoice/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).filter_by(...).first()
        invoice_data = get_entity_dict(invoice)

    return jsonify({'success': True, 'data': invoice_data})
```

**Pattern 3: Multiple Entities to List of Dicts**
```python
with get_db_session() as session:
    invoices = session.query(InvoiceHeader).filter(...).all()
    invoice_list = [get_entity_dict(inv) for inv in invoices]

return jsonify({'invoices': invoice_list})
```

### 6. Verification Before Using

**ALWAYS verify function exists:**
```python
# ✅ CORRECT: Verified imports
from app.services.database_service import get_db_session, get_entity_dict, get_detached_copy

# ❌ WRONG: Non-existent function
from app.services.database_service import to_dict  # Does NOT exist!
```

**Available Functions** with line numbers:
- `get_db_session()` - Get database session context manager (line 548)
- `get_entity_dict(entity)` - Convert entity to dict (line 662)
- `get_detached_copy(entity)` - Create detached copy (line 641)
- `get_db_engine()` - Get SQLAlchemy engine (line 575)
- `initialize_database()` - Initialize database connection (line 605)
- `close_db_connections()` - Close all connections (line 683)

### 7. Session Context Manager Pattern

**ALWAYS use context manager:**
```python
# ✅ CORRECT: Context manager ensures proper cleanup
def get_patient_data(patient_id):
    with get_db_session() as session:
        patient = session.query(Patient).filter_by(patient_id=patient_id).first()
        patient_dict = get_entity_dict(patient)  # Convert BEFORE session closes

    # Session closed here, but patient_dict is still usable
    return patient_dict

# ❌ WRONG: Manual session management
session = get_db_session()  # Wrong! This is a context manager, not a session
patient = session.query(Patient).first()  # Will fail
```

## Why This Documentation Matters

### Previous Errors Prevented:

1. **ImportError: to_dict doesn't exist**
   - Error: `cannot import name 'to_dict' from 'app.services.database_service'`
   - Prevention: Documentation lists all available functions with line numbers

2. **DetachedInstanceError**
   - Error: Accessing entity attributes after session closes
   - Prevention: Documentation shows correct pattern with `get_entity_dict()`

3. **Manual Session Management**
   - Error: Trying to use `get_db_session()` directly as a session
   - Prevention: Documentation emphasizes context manager pattern

### Benefits:

1. ✅ **Clear Reference**: Lists all available database service functions
2. ✅ **Practical Examples**: Shows correct and wrong usage patterns
3. ✅ **Common Patterns**: Service layer, API, and bulk operations
4. ✅ **Comparison Guide**: When to use which method
5. ✅ **Error Prevention**: Explicit DO/DON'T examples
6. ✅ **Line Numbers**: Quick reference to actual implementations

## Real-World Application

### Fixed AR Statement Service:
**Before** (caused error):
```python
from app.services.database_service import get_db_session, to_dict  # ❌ to_dict doesn't exist!
```

**After** (correct):
```python
from app.services.database_service import get_db_session, get_entity_dict  # ✅ Verified
```

### Typical Service Pattern:
```python
class ARStatementService:
    def get_patient_ar_statement(self, patient_id, hospital_id, highlight_reference_id=None):
        with get_db_session() as session:
            # Query patient
            patient = session.query(Patient).filter(...).first()

            # Convert to dict BEFORE session closes
            patient_info = {
                'patient_id': str(patient.patient_id),
                'full_name': patient.full_name,
                'patient_number': patient.mrn or '',
                'phone_number': patient.contact_info.get('phone', '') if patient.contact_info else ''
            }

            # Query AR entries
            ar_entries = session.query(ARSubledger).filter(...).all()

            # Convert to list of dicts
            transactions = [get_entity_dict(entry) for entry in ar_entries]

        # Session closed here - all data is in dicts, safe to use
        return {
            'success': True,
            'patient_info': patient_info,
            'transactions': transactions
        }
```

## Testing Recommendation

When implementing any service that returns data from database:

1. ✅ Open session with `with get_db_session() as session:`
2. ✅ Query entities
3. ✅ Convert to dict with `get_entity_dict()` BEFORE session closes
4. ✅ Return dict/list of dicts
5. ✅ Session automatically closes on exit from `with` block
6. ✅ Data remains accessible because it's in dict form

## Files Modified

- ✅ `CLAUDE.md` (lines 312-562) - Added "Database Service Methods for Detached Sessions" section

## Status

✅ **DOCUMENTATION COMPLETE**

The database service methods are now comprehensively documented in CLAUDE.md with:
- Function signatures
- Use cases
- Correct/wrong examples
- Common patterns
- Verification checklist
- Available functions with line numbers

This should prevent future import errors and session management issues.

---

**Next Developer Actions:**
1. ALWAYS check CLAUDE.md before importing from `database_service.py`
2. ALWAYS use `get_entity_dict()` for API responses and template data
3. ALWAYS convert entities to dicts BEFORE session closes
4. ALWAYS use `with get_db_session() as session:` context manager pattern
