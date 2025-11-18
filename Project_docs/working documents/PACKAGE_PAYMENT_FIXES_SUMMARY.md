# Package Payment Plan - Remaining Fixes Summary

## Completed Fixes ✅

1. **Installment Table Total Row Color** - Added `bg-secondary bg-opacity-10` to total row
2. **Overview Tab Double Column Layout** - Changed financial and sessions sections from 3 columns to 2 columns
3. **Section Icon Colors** - Changed from gray to blue (`text-blue-600 dark:text-blue-400`)
4. **Edit Buttons** - Already have `btn-warning` class (orange) - just refresh browser with Ctrl+F5

## Pending Issues to Fix

### 1. Status Field Showing HTML
**Issue**: Status badge HTML is being escaped and shown as text
**Location**: `app/templates/engine/components/layout_tabbed.html` line 80
**Fix Needed**: Add `|safe` filter for STATUS_BADGE field types

### 2. Line Item Tables - Remove Audit Fields
**Issue**: Installment and Session tables showing created_at, created_by, updated_at, updated_by
**Location**: `app/config/modules/package_payment_plan_config.py`
**Fix Needed**: Remove these fields from line item table sections

### 3. Edit Package Payment Plan Button - NoneType Error
**Issue**: Edit button giving NoneType error
**Likely Cause**: Missing action definition or URL pattern issue
**Location**: Check `PACKAGE_PAYMENT_PLAN_ACTIONS` in config

### 4. Label Change
**Issue**: "Create New Package Payment Plan" → "Create New Package Plan"
**Location**: Entity configuration `display_name` and `display_name_plural`

### 5. Performed By Dropdown Not Working
**Issue**: Staff API `/api/staff/active` returns 404
**Status**: Already handled gracefully in JS - uses current user as default
**Location**: Staff API needs to be implemented (future)

## Quick Fixes Needed Now

1. Status field HTML rendering
2. Remove audit fields from line item configs
3. Fix Edit button action
4. Change label text
