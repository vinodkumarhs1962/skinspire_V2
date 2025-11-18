# Config to Master Sync - Technical Reference

**Date**: 2025-11-17
**Module**: `app/services/config_master_sync_service.py`

---

## Architecture Overview

### Purpose

Synchronizes currently effective pricing and GST configurations from `entity_pricing_tax_config` table to master tables (medicines, services, packages) for user convenience.

### Design Principles

1. **Read-Only for Configs**: Never modifies config table
2. **Selective Updates**: Only updates changed fields
3. **Safety First**: Dry-run mode by default
4. **Transaction Safety**: All-or-nothing updates
5. **Audit Trail**: Complete change logging

---

## Core Components

### 1. Main Sync Function

```python
def sync_config_to_masters(
    session: Session,
    hospital_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    dry_run: bool = True,
    update_pricing: bool = True,
    update_gst: bool = True,
    current_user_id: Optional[str] = None
) -> ConfigMasterSyncResult
```

**Parameters**:
- `session`: SQLAlchemy session (required)
- `hospital_id`: Filter by hospital UUID (None = all hospitals)
- `entity_type`: 'medicine', 'service', 'package' (None = all types)
- `dry_run`: Preview mode (default: True)
- `update_pricing`: Update pricing fields (default: True)
- `update_gst`: Update GST fields (default: True)
- `current_user_id`: User ID for audit trail

**Returns**: `ConfigMasterSyncResult` object with summary and changes

**Process**:
1. Find currently effective configs
2. For each config, determine entity type (medicine/service/package)
3. Call appropriate sync function
4. Collect results and errors
5. Return summary

### 2. Entity-Specific Sync Functions

#### Medicine Sync
```python
def _sync_medicine(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool
) -> None
```

**Logic**:
1. Query medicine by medicine_id
2. Build update dict with changed fields
3. Apply updates to medicine object
4. Track changes in result object
5. Flush if not dry_run

#### Service Sync
```python
def _sync_service(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool
) -> None
```

**Logic**: Similar to medicine sync, adapted for service fields

#### Package Sync
```python
def _sync_package(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool
) -> None
```

**Logic**: Similar to medicine sync, adapted for package fields

### 3. Result Tracking

```python
class ConfigMasterSyncResult:
    medicines_updated: int = 0
    services_updated: int = 0
    packages_updated: int = 0
    medicines_skipped: int = 0
    services_skipped: int = 0
    packages_skipped: int = 0
    changes: List[Dict] = []
    errors: List[Dict] = []

    @property
    def total_updated(self) -> int

    @property
    def total_skipped(self) -> int
```

**Change Record Format**:
```python
{
    'entity_type': 'medicine',
    'entity_id': 'uuid',
    'entity_name': 'Paracetamol 500mg',
    'field': 'mrp',
    'old_value': '45.00',
    'new_value': '50.00',
    'config_id': 'config-uuid'
}
```

**Error Record Format**:
```python
{
    'entity_type': 'medicine',
    'entity_id': 'uuid',
    'error': 'Medicine not found'
}
```

### 4. Report Generation

```python
def generate_sync_report(
    result: ConfigMasterSyncResult,
    format: str = 'text'  # 'text' or 'html'
) -> str
```

**Text Format**:
```
Config to Master Sync Report
============================
Summary:
- Total Updated: 25
- Total Skipped: 100
- Total Errors: 0

By Entity Type:
- Medicines: 15 updated, 60 skipped
- Services: 8 updated, 30 skipped
- Packages: 2 updated, 10 skipped

Changes:
1. Medicine: Paracetamol 500mg
   - mrp: 45.00 → 50.00
   - Config ID: uuid-here
```

**HTML Format**: Same content with HTML formatting for web display

---

## Database Queries

### Find Currently Effective Configs

```sql
SELECT *
FROM entity_pricing_tax_config
WHERE effective_from <= CURRENT_DATE
  AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
  AND is_deleted = false
  AND hospital_id = ? (if filtering by hospital)
  AND medicine_id IS NOT NULL (if filtering by entity_type='medicine')
ORDER BY effective_from DESC;
```

### Update Master Table (Example: Medicine)

```python
# ORM approach
medicine.mrp = config.mrp
medicine.gst_rate = config.gst_rate
# ... other fields
session.flush()
```

**Equivalent SQL**:
```sql
UPDATE medicines
SET mrp = ?,
    gst_rate = ?,
    cgst_rate = ?,
    sgst_rate = ?,
    igst_rate = ?,
    updated_at = CURRENT_TIMESTAMP,
    updated_by = ?
WHERE medicine_id = ?;
```

---

## Field Mappings

### Medicine Fields

**Pricing Fields**:
| Config Field | Master Field |
|--------------|--------------|
| mrp | mrp |
| pack_mrp | pack_mrp |
| selling_price | selling_price |
| cost_price | cost_price |

**GST Fields**:
| Config Field | Master Field |
|--------------|--------------|
| gst_rate | gst_rate |
| cgst_rate | cgst_rate |
| sgst_rate | sgst_rate |
| igst_rate | igst_rate |
| is_gst_exempt | is_gst_exempt |
| gst_inclusive | gst_inclusive |

### Service Fields

**Pricing Fields**:
| Config Field | Master Field |
|--------------|--------------|
| service_price | service_price |
| cost_price | cost_price |

**GST Fields**: Same as medicine

### Package Fields

**Pricing Fields**:
| Config Field | Master Field |
|--------------|--------------|
| package_price | package_price |

**GST Fields**: Same as medicine

---

## API Integration

### Endpoint

**Route**: `/api/admin/sync-config-to-masters`
**Method**: POST
**Blueprint**: `admin_bp` (app.api.routes.admin)
**Authentication**: `@login_required` (system_admin only)

### Request/Response

See `app/api/routes/admin.py` for full implementation.

**Example Request**:
```bash
curl -X POST http://localhost:5000/api/admin/sync-config-to-masters \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "medicine",
    "dry_run": true,
    "update_pricing": true,
    "update_gst": true
  }'
```

**Example Response**:
```json
{
  "success": true,
  "dry_run": true,
  "summary": {
    "total_updated": 25,
    "medicines_updated": 25,
    "services_updated": 0,
    "packages_updated": 0,
    "total_skipped": 100,
    "total_errors": 0
  },
  "changes": [...],
  "errors": [],
  "report_text": "...",
  "report_html": "..."
}
```

---

## UI Integration

### Template

**File**: `app/templates/admin/config_sync.html`
**Base Template**: `layouts/dashboard.html`

**Features**:
- Entity type filter dropdown
- Pricing/GST update checkboxes
- Dry run toggle switch
- Real-time sync progress
- Summary statistics display
- Detailed change list
- Copy report to clipboard
- Toast notifications

### Menu Integration

**File**: `app/utils/menu_utils.py`
**Location**: System Settings → Config to Master Sync
**Access**: system_admin role only
**Badge**: "Admin" (warning color)

---

## Performance Considerations

### Query Optimization

1. **Indexed Queries**: Uses indexes on effective_from, effective_to, entity_id columns
2. **Batch Processing**: Processes all configs in single transaction
3. **Selective Updates**: Only updates fields that changed (reduces DB writes)

### Scalability

**Expected Performance**:
- 1-100 configs: < 1 second
- 100-1000 configs: 1-5 seconds
- 1000+ configs: 5-30 seconds

**Bottlenecks**:
- Large number of configs to process
- Complex field comparisons
- Network latency (if remote DB)

**Optimization Strategies**:
- Run during off-peak hours for large syncs
- Filter by entity_type to reduce scope
- Use dry_run to preview before execution

---

## Error Handling

### Error Types

1. **Config Errors**:
   - Config with NULL medicine_id/service_id/package_id
   - Invalid config data (e.g., negative prices)

2. **Master Table Errors**:
   - Medicine/service/package not found
   - Constraint violations
   - Concurrent update conflicts

3. **System Errors**:
   - Database connection failures
   - Transaction deadlocks
   - Permission errors

### Error Recovery

**Dry Run**: Errors are logged but don't affect operation
**Actual Sync**:
- Individual record errors are logged in result.errors
- Transaction continues for other records
- Session is committed if no critical errors
- Session is rolled back if critical error occurs

### Logging

```python
logger.info(f"Starting sync: hospital_id={hospital_id}, entity_type={entity_type}")
logger.info(f"Found {len(configs)} currently effective configs")
logger.info(f"Synced medicine: {medicine.medicine_name}, {len(updates)} fields updated")
logger.warning(f"Medicine not found: {config.medicine_id}")
logger.error(f"Error syncing medicine {config.medicine_id}: {str(e)}")
```

---

## Testing

### Unit Tests

**Test Coverage**:
1. Sync with all entity types
2. Sync with single entity type
3. Dry run vs actual execution
4. Update pricing only
5. Update GST only
6. Update both
7. No changes scenario
8. Error handling

**Test Fixtures**:
- Sample configs (effective, expired, future)
- Sample master records (with and without configs)
- Test data with various field combinations

### Integration Tests

1. End-to-end sync via API
2. Menu navigation to sync page
3. UI interaction (form submission, results display)
4. Error scenarios (DB failure, invalid data)

### Manual Testing

**Test Cases**:
1. Add new config, verify master updates after sync
2. Change config value, verify master reflects change
3. Expire config (set effective_to), verify master unchanged
4. Future config (effective_from > today), verify not synced

---

## Security

### Authorization

- Endpoint requires `@login_required` decorator
- Menu item visible only to system_admin role
- API validates user has admin permissions

### Data Validation

- Entity type validated against allowed values
- Boolean flags sanitized
- Hospital ID validated as UUID (if provided)

### Audit Trail

- All changes logged with before/after values
- User ID recorded for accountability
- Timestamp captured for each update

---

## Monitoring

### Metrics to Track

1. **Sync Frequency**: How often syncs are run
2. **Records Updated**: Average number of updates per sync
3. **Errors**: Error rate and types
4. **Performance**: Sync duration trends

### Alerts

**Warning Conditions**:
- Large number of errors (> 10% of records)
- Sync duration > 60 seconds
- Repeated failures

**Critical Conditions**:
- All records failing to sync
- Database transaction failures
- Permission errors

---

## Future Enhancements

### Planned Features

1. **Scheduled Sync**: Cron job to run sync automatically
2. **Selective Sync**: Sync specific medicine/service/package
3. **Conflict Resolution**: Handle concurrent config/master updates
4. **History View**: Show past sync operations
5. **Rollback**: Undo a sync operation

### Extension Points

1. **Custom Sync Logic**: Hook for hospital-specific sync rules
2. **Pre/Post Sync Callbacks**: Custom actions before/after sync
3. **Notification System**: Alert users when sync completes
4. **Export Results**: Download sync report as CSV/PDF

---

## Troubleshooting

### Common Issues

#### Issue 1: No Configs Found
**Symptom**: Sync shows 0 updates
**Cause**: No currently effective configs exist
**Solution**:
1. Check config table for records with effective_from <= today
2. Verify effective_to is NULL or >= today
3. Confirm is_deleted = false

#### Issue 2: Master Not Updating
**Symptom**: Dry run shows changes, but master unchanged after sync
**Cause**: dry_run flag still true, or session not committed
**Solution**:
1. Ensure dry_run = false in request
2. Check session.commit() is called
3. Verify no transaction rollback

#### Issue 3: Partial Updates
**Symptom**: Some records updated, others not
**Cause**: Errors for specific records
**Solution**:
1. Review result.errors array
2. Fix data issues for failed records
3. Re-run sync

---

## Dependencies

### Python Packages
- `sqlalchemy`: ORM and database access
- `flask`: Web framework
- `typing`: Type hints

### Internal Modules
- `app.models.config`: EntityPricingTaxConfig model
- `app.models.master`: Medicine, Service, Package models
- `app.services.database_service`: get_db_session
- `app.security.bridge`: login_required decorator

---

## Code Examples

### Example 1: Sync All Medicines

```python
from app.services.database_service import get_db_session
from app.services.config_master_sync_service import sync_config_to_masters

with get_db_session() as session:
    result = sync_config_to_masters(
        session=session,
        entity_type='medicine',
        dry_run=False
    )
    session.commit()
    print(f"Updated {result.medicines_updated} medicines")
```

### Example 2: Dry Run for Single Hospital

```python
with get_db_session() as session:
    result = sync_config_to_masters(
        session=session,
        hospital_id='hospital-uuid-here',
        dry_run=True
    )
    for change in result.changes:
        print(f"{change['entity_name']}: {change['field']} {change['old_value']} → {change['new_value']}")
```

### Example 3: Update Only GST Rates

```python
with get_db_session() as session:
    result = sync_config_to_masters(
        session=session,
        update_pricing=False,  # Don't update pricing
        update_gst=True,       # Only update GST
        dry_run=False
    )
    session.commit()
    print(f"Updated GST for {result.total_updated} records")
```

---

## Related Files

| File | Purpose |
|------|---------|
| `app/services/config_master_sync_service.py` | Core sync service implementation |
| `app/api/routes/admin.py` | API endpoint |
| `app/templates/admin/config_sync.html` | UI template |
| `app/utils/menu_utils.py` | Menu integration |
| `CONFIG_MASTER_SYNC_USER_GUIDE.md` | User documentation |
| `IMPLEMENTATION_COMPLETE_GST_MRP_VERSIONING.md` | Overall implementation summary |

---

**Last Updated**: 2025-11-17
**Version**: 1.0
**Maintainer**: Development Team
