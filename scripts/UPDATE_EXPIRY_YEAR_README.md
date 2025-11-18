# Update Inventory Expiry Year - Complete Guide

This guide explains how to update expiry years for **ALL inward inventory records** from 2025 to 2026.

## ⚠️ IMPORTANT: Tables Updated

The scripts update expiry dates in **4 tables**:

### 🔴 PRIMARY Tables (Inward Inventory)
1. **supplier_invoice_line** - Supplier invoice line items (goods received)
2. **inventory** - Inventory movements (stock transactions)

### 🔵 REFERENCE Tables (For Consistency)
3. **invoice_line_item** - Patient invoice line items (outward sales)
4. **prescription_invoice_maps** - Prescription mappings

**Use `update_expiry_year_complete.py` for all tables!**

---

## Two Options Available

### Option 1: Complete Python Script (Recommended)
- ✅ Updates ALL 4 tables
- ✅ Safe and interactive
- ✅ Shows preview before updating
- ✅ Built-in confirmation prompts
- ✅ Detailed summary and logging

### Option 2: Complete SQL Script
- ✅ Updates ALL 4 tables
- ✅ Direct database access
- ✅ Full control over transaction
- ✅ Easy to modify for custom scenarios
- ✅ Includes backup instructions

---

## Option 1: Complete Python Script

### Step 1: Preview Changes (Dry Run)

```bash
# See what will be changed in ALL tables WITHOUT making any changes
python scripts/update_expiry_year_complete.py --dry-run
```

**Example Output:**
```
================================================================================
COMPLETE Inventory Expiry Year Update Script
================================================================================
From Year: 2025
To Year:   2026
Mode:      DRY RUN (preview only)
================================================================================

================================================================================
🔴 PRIMARY: Supplier Invoice Line Items (INWARD INVENTORY)
Table: supplier_invoice_line
================================================================================
Found 75 record(s) with expiry year 2025

Sample records (first 10):
--------------------------------------------------------------------------------
1. Amoxicillin 500mg                     Batch: B001           2025-03-15 → 2026-03-15
2. Paracetamol 500mg                     Batch: B002           2025-06-20 → 2026-06-20
...
--------------------------------------------------------------------------------
Total: 75 records in supplier_invoice_line

================================================================================
🔴 PRIMARY: Inventory Movements
Table: inventory
================================================================================
Found 120 record(s) with expiry year 2025
...

================================================================================
SUMMARY
================================================================================
Table                               Found      Status
--------------------------------------------------------------------------------
🔴 supplier_invoice_line              75         Preview only
🔴 inventory                          120        Preview only
🔵 invoice_line_item                  45         Preview only
🔵 prescription_invoice_maps          10         Preview only
--------------------------------------------------------------------------------
Total records across all tables: 250
================================================================================

✓ DRY RUN MODE - No changes made
  Remove --dry-run flag to apply changes
```

### Step 2: Apply Changes

```bash
# Apply the changes to ALL tables (will ask for confirmation)
python scripts/update_expiry_year_complete.py
```

**Confirmation Prompt:**
```
Commit 250 updates to database? (yes/no): yes

✓ Successfully updated 250 records
  Expiry year changed from 2025 to 2026

🔴 PRIMARY tables (inward inventory): supplier_invoice_line, inventory
🔵 REFERENCE tables (for consistency): invoice_line_item, prescription_invoice_maps
```

### Advanced Usage

```bash
# Update different years
python scripts/update_expiry_year_complete.py --from-year 2024 --to-year 2025

# Preview different years
python scripts/update_expiry_year_complete.py --from-year 2024 --to-year 2025 --dry-run
```

---

## Option 2: Complete SQL Script

### Step 1: Open Database Client

```bash
# Connect to database
psql -h localhost -U postgres -d skinspire_dev
```

### Step 2: Review the SQL File

Open `scripts/update_expiry_year_complete.sql` in a text editor to review the script.

### Step 3: Run Preview Queries

```sql
-- See summary of changes
SELECT
    medicine_name,
    batch,
    expiry AS old_expiry,
    (expiry + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS transaction_count,
    SUM(current_stock) AS total_stock
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025
GROUP BY medicine_name, batch, expiry
ORDER BY medicine_name, batch;

-- Count total records
SELECT COUNT(*) FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2025;
```

### Step 4: Create Backup (IMPORTANT!)

```sql
-- Create backup table
CREATE TABLE inventory_backup_20250109 AS
SELECT * FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Verify backup
SELECT COUNT(*) FROM inventory_backup_20250109;
```

### Step 5: Apply Update

```sql
-- Start transaction
BEGIN;

-- Update expiry year
UPDATE inventory
SET
    expiry = (expiry + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Verify changes
SELECT COUNT(*) FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2026;

-- If everything looks good:
COMMIT;

-- If something went wrong:
-- ROLLBACK;
```

### Step 6: Verify Results

```sql
-- Should return 0
SELECT COUNT(*) FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Should return number of updated records
SELECT COUNT(*) FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2026;
```

---

## Safety Features

### Python Script
- ✅ Dry-run mode shows preview without changes
- ✅ Confirmation prompt before updating
- ✅ Detailed summary of changes
- ✅ Updates `updated_at` timestamp
- ✅ Error handling with rollback

### SQL Script
- ✅ Preview queries to see changes first
- ✅ Automatic backup table creation
- ✅ Transaction-wrapped updates
- ✅ Verification queries
- ✅ Rollback procedure included

---

## Troubleshooting

### Python Script Issues

**ImportError:**
```bash
# Make sure you're in the project directory
cd "C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\Skinspire_v2"

# Activate virtual environment if needed
source ../skinspire-env/Scripts/activate  # Git Bash
```

**Database Connection Error:**
```bash
# Check database is running
# Verify .env file has correct database URL
```

### SQL Script Issues

**Permission Denied:**
```bash
# Make sure you're connected with sufficient privileges
# Use postgres user or database owner
```

**Transaction Too Large:**
```sql
-- Update in batches
UPDATE inventory
SET expiry = (expiry + INTERVAL '1 year')::date
WHERE EXTRACT(YEAR FROM expiry) = 2025
  AND stock_id IN (
      SELECT stock_id FROM inventory
      WHERE EXTRACT(YEAR FROM expiry) = 2025
      LIMIT 1000
  );
```

---

## Important Notes

1. **Always run dry-run/preview first** to see what will change
2. **Take a backup** before applying changes
3. **Verify results** after update
4. The script updates the `updated_at` timestamp for audit trail
5. Both scripts handle the date addition correctly (preserves month and day)

---

## Examples

### Scenario 1: Update 2025 → 2026 (All Tables)
```bash
python scripts/update_expiry_year_complete.py --dry-run  # Preview ALL tables
python scripts/update_expiry_year_complete.py            # Apply to ALL tables
```

### Scenario 2: Update 2024 → 2025 (All Tables)
```bash
python scripts/update_expiry_year_complete.py --from-year 2024 --to-year 2025 --dry-run
python scripts/update_expiry_year_complete.py --from-year 2024 --to-year 2025
```

### Scenario 3: Rollback Changes (SQL)
```sql
-- Restore from backup table
BEGIN;

UPDATE inventory i
SET expiry = b.expiry, updated_at = b.updated_at
FROM inventory_backup_20250109 b
WHERE i.stock_id = b.stock_id;

COMMIT;
```

---

## Support

If you encounter any issues:
1. Check the error message carefully
2. Verify database connection
3. Ensure you have write permissions
4. Check the app.log file for detailed errors
5. Try the SQL script as an alternative

For questions, refer to the inline documentation in both script files.
