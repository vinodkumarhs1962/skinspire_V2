# Config to Master Sync - User Guide

**Date**: 2025-11-17
**Status**: ✅ IMPLEMENTED AND DEPLOYED

---

## Overview

The Config to Master Sync feature keeps your master tables (medicines, services, packages) aligned with currently effective pricing and GST configurations from the `entity_pricing_tax_config` table.

### Why This Feature Exists

1. **Invoice Creation**: Uses date-based configs for historical accuracy (primary source of truth)
2. **Master Tables**: Display current rates for user convenience
3. **Alignment**: This sync keeps master tables up-to-date with current effective configs

---

## When to Use

### Recommended Scenarios

1. **After Adding New Rate Changes**: When you've added new GST or MRP configs that are now effective
2. **Periodic Maintenance**: Monthly sync to ensure alignment
3. **After Bulk Config Changes**: When multiple configs have been updated
4. **Before Reports**: To ensure master tables show current values for reporting

### Not Needed When

- **Creating Invoices**: Invoice creation automatically uses date-based configs (no sync needed)
- **Viewing History**: Config table has complete history regardless of master table values
- **Daily Operations**: System works fine without frequent syncing

---

## Access the Sync Tool

### Navigation

1. Log in as **System Admin**
2. Click **System Settings** in the main menu
3. Click **Config to Master Sync** (marked with "Admin" badge)

### URL

Direct access: `http://your-domain/api/admin/config-sync`

---

## Using the Sync Interface

### Step 1: Configure Sync Options

#### Entity Type Filter
- **All Types**: Syncs medicines, services, and packages (default)
- **Medicines Only**: Syncs only medicine master table
- **Services Only**: Syncs only service master table
- **Packages Only**: Syncs only package master table

**Recommendation**: Start with "All Types" unless you have a specific need.

#### Update Options

**Update Pricing** (checked by default):
- MRP
- Pack MRP
- Selling Price
- Cost Price
- Service Price
- Package Price

**Update GST** (checked by default):
- GST Rate
- CGST Rate
- SGST Rate
- IGST Rate
- GST Inclusive flag
- GST Exempt flag

**Recommendation**: Keep both checked unless you want to update only pricing or only GST.

#### Dry Run Mode

**Enabled (default)**:
- Shows what would be changed
- No actual database updates
- Safe to run anytime
- **ALWAYS run dry run first**

**Disabled**:
- Actually updates master tables
- Permanent changes
- Only use after reviewing dry run results

---

### Step 2: Run Dry Run (Preview)

1. Ensure "Dry Run Mode" is **ENABLED** (checked)
2. Click **Run Sync** button
3. Wait for results (usually 1-5 seconds)

### Step 3: Review Results

#### Summary Card

Shows:
- **Total Updated**: Number of records that would be changed
- **Total Skipped**: Records with no changes needed
- **Total Errors**: Any errors encountered
- **By Entity Type**: Breakdown (medicines, services, packages)

#### Change Details Card

Shows each change:
- **Entity Type**: Medicine/Service/Package
- **Entity Name**: Name of the item
- **Field**: Which field will change (e.g., "mrp", "gst_rate")
- **Old Value → New Value**: Current value vs config value
- **Config ID**: Reference to config record

### Step 4: Execute Sync (If Needed)

If dry run results look correct:

1. **UNCHECK** "Dry Run Mode" switch
2. Click **Run Sync** button again
3. Review updated summary
4. Changes are now permanent

---

## Understanding Results

### What Gets Updated

The sync **ONLY** updates fields where:
1. A currently effective config exists (effective_to = NULL or ≥ today)
2. The config value differs from the master table value

### What Doesn't Get Updated

- Records with no corresponding config (master table value unchanged)
- Fields where config value matches master value (no change needed)
- Historical configs (effective_to < today)

### Example

**Config Table**:
```
Medicine: Paracetamol 500mg
Effective From: 2025-11-01
Effective To: NULL (currently effective)
MRP: 50.00
GST Rate: 12.00
```

**Master Table Before Sync**:
```
Medicine: Paracetamol 500mg
MRP: 45.00  (old value)
GST Rate: 12.00  (already matches)
```

**Sync Result**:
- MRP: 45.00 → 50.00 (UPDATED)
- GST Rate: 12.00 (SKIPPED - no change)

---

## Use Cases

### Use Case 1: GST Rate Change

**Scenario**: Government increased medicine GST from 12% to 18% on Nov 1, 2025

**Steps**:
1. Add new config with effective_from = 2025-11-01, gst_rate = 18
2. Wait until Nov 1 or later
3. Run sync with dry run enabled
4. Review: Should show medicines updating from 12% to 18%
5. Execute sync (disable dry run)
6. Master tables now show 18% for current operations

**Benefit**: Master tables show current rate while invoices use historical rates based on invoice date

### Use Case 2: MRP Increase

**Scenario**: Manufacturer increased MRP from ₹500 to ₹550 on July 1, 2025

**Steps**:
1. Add new config with effective_from = 2025-07-01, mrp = 550
2. Run sync on or after July 1
3. Master table MRP updates to ₹550

**Benefit**: Staff see current MRP when creating new orders/prescriptions

### Use Case 3: Monthly Maintenance

**Scenario**: Monthly alignment check

**Steps**:
1. First day of month, run dry run
2. Review changes (should show configs that became effective last month)
3. Execute sync if changes make sense
4. Document in change log

**Benefit**: Keeps master tables aligned without manual updates

---

## Safety Features

### 1. Dry Run Default
- Always defaults to dry run mode
- Forces conscious decision to execute

### 2. Change Tracking
- Every change is logged
- Before/after values recorded
- Config ID reference preserved

### 3. No Historical Changes
- Only syncs currently effective configs
- Past configs are never used
- Future configs (effective_from > today) are ignored

### 4. Field-Level Updates
- Only updates fields that changed
- Preserves other fields
- Atomic updates (all or nothing)

---

## Common Questions

### Q: Will this affect historical invoices?
**A**: No. Invoices always use the config effective on their invoice_date. This only updates master tables for current operations.

### Q: What if I don't have configs for some medicines?
**A**: Master table values remain unchanged. The system uses master table as fallback.

### Q: Can I sync only specific medicines?
**A**: Not in the UI currently. Use entity_type filter to sync all medicines. For specific items, run SQL update manually or contact admin.

### Q: How often should I run this?
**A**:
- After adding new configs: Once they become effective
- Routine maintenance: Monthly
- Ad-hoc: When master tables seem out of sync

### Q: What if sync fails?
**A**:
- Dry run: No harm, just shows error
- Actual sync: Transaction is rolled back, no partial updates
- Check error message and contact technical support

### Q: Can I undo a sync?
**A**:
- No automatic undo
- Review dry run carefully before executing
- Manual SQL update required to revert

---

## Troubleshooting

### Issue: No Changes Shown in Dry Run

**Possible Causes**:
1. No currently effective configs exist
2. Master tables already match configs
3. Effective_from is in the future

**Resolution**:
- Check config table for effective configs
- Verify effective_from <= today
- Confirm config values differ from master

### Issue: Sync Shows Errors

**Possible Causes**:
1. Database constraint violation
2. Invalid config data (e.g., NULL in required field)
3. Concurrent updates

**Resolution**:
- Review error message
- Check config data integrity
- Retry after resolving data issues

### Issue: Some Records Updated, Some Skipped

**This is Normal**:
- Skipped = no config or no change
- Updated = config exists with different value

---

## Technical Details

### Database Operations

```sql
-- Example: What the sync does internally
UPDATE medicines
SET mrp = config.mrp,
    gst_rate = config.gst_rate
FROM entity_pricing_tax_config config
WHERE medicines.medicine_id = config.medicine_id
  AND config.effective_from <= CURRENT_DATE
  AND (config.effective_to IS NULL OR config.effective_to >= CURRENT_DATE)
  AND config.is_deleted = false;
```

### API Endpoint

**POST** `/api/admin/sync-config-to-masters`

**Request Body**:
```json
{
  "entity_type": "medicine",  // or "service", "package", null for all
  "dry_run": true,  // false to execute
  "update_pricing": true,
  "update_gst": true
}
```

**Response**:
```json
{
  "success": true,
  "dry_run": true,
  "summary": {
    "total_updated": 25,
    "medicines_updated": 15,
    "services_updated": 8,
    "packages_updated": 2,
    "total_skipped": 100,
    "total_errors": 0
  },
  "changes": [
    {
      "entity_type": "medicine",
      "entity_name": "Paracetamol 500mg",
      "field": "mrp",
      "old_value": "45.00",
      "new_value": "50.00",
      "config_id": "uuid-here"
    }
  ]
}
```

---

## Best Practices

### 1. Always Dry Run First
Never execute without reviewing dry run results.

### 2. Document Changes
Keep a log of when syncs were run and what changed.

### 3. Schedule Regular Syncs
Monthly sync as part of month-end close process.

### 4. Verify After Sync
Spot-check a few master records to confirm updates.

### 5. Backup Before Large Syncs
Take database backup before syncing 100+ records.

---

## Related Documentation

- **Implementation Guide**: `IMPLEMENTATION_COMPLETE_GST_MRP_VERSIONING.md`
- **GST/MRP Versioning Guide**: `GST_MRP_VERSIONING_IMPLEMENTATION_GUIDE.md`
- **Design Document**: `Project_docs/PRICING_AND_GST_VERSIONING_DESIGN.md`
- **Service Documentation**: `app/services/config_master_sync_service.py` (code comments)

---

## Support

For technical issues or questions:
1. Check this documentation
2. Review dry run results carefully
3. Contact system administrator
4. Email technical support with:
   - Screenshot of results
   - Entity types affected
   - Expected vs actual behavior

---

**Last Updated**: 2025-11-17
**Feature Version**: 1.0
**Minimum Admin Role**: system_admin
