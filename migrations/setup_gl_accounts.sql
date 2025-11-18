-- ============================================================================
-- Chart of Accounts Setup for Healthcare Clinic
-- ============================================================================
-- This script creates a comprehensive GL account structure for invoice posting
--
-- Date: 2025-11-17
-- Purpose: Fix NULL gl_account_id in invoice_header by creating proper GL accounts
-- ============================================================================

-- Get the hospital_id (you may need to modify this)
-- Replace '<your-hospital-id-here>' with actual hospital_id from hospitals table

DO $$
DECLARE
    v_hospital_id UUID;
    v_revenue_group_id UUID;
    v_asset_group_id UUID;
    v_liability_group_id UUID;
    v_expense_group_id UUID;
BEGIN
    -- Get the first hospital (modify if you have multiple hospitals)
    SELECT hospital_id INTO v_hospital_id
    FROM hospitals
    ORDER BY created_at
    LIMIT 1;

    IF v_hospital_id IS NULL THEN
        RAISE EXCEPTION 'No hospital found in database';
    END IF;

    RAISE NOTICE 'Setting up GL accounts for hospital: %', v_hospital_id;

    -- ========================================================================
    -- PART 1: CREATE MAIN ACCOUNT GROUPS (Parent Accounts)
    -- ========================================================================

    -- 1. Revenue Group (Income)
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Income', '4000',
        'Revenue', NULL, FALSE, NULL, TRUE
    )
    ON CONFLICT DO NOTHING
    RETURNING account_id INTO v_revenue_group_id;

    -- Get revenue group if it already exists
    IF v_revenue_group_id IS NULL THEN
        SELECT account_id INTO v_revenue_group_id
        FROM chart_of_accounts
        WHERE hospital_id = v_hospital_id
        AND gl_account_no = '4000';
    END IF;

    -- 2. Asset Group
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Assets', '1000',
        'Current Assets', NULL, FALSE, NULL, TRUE
    )
    ON CONFLICT DO NOTHING
    RETURNING account_id INTO v_asset_group_id;

    IF v_asset_group_id IS NULL THEN
        SELECT account_id INTO v_asset_group_id
        FROM chart_of_accounts
        WHERE hospital_id = v_hospital_id
        AND gl_account_no = '1000';
    END IF;

    -- 3. Liability Group
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Liabilities', '2000',
        'Current Liabilities', NULL, FALSE, NULL, TRUE
    )
    ON CONFLICT DO NOTHING
    RETURNING account_id INTO v_liability_group_id;

    IF v_liability_group_id IS NULL THEN
        SELECT account_id INTO v_liability_group_id
        FROM chart_of_accounts
        WHERE hospital_id = v_hospital_id
        AND gl_account_no = '2000';
    END IF;

    -- 4. Expense Group
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Expense', '5000',
        'Operating Expenses', NULL, FALSE, NULL, TRUE
    )
    ON CONFLICT DO NOTHING
    RETURNING account_id INTO v_expense_group_id;

    IF v_expense_group_id IS NULL THEN
        SELECT account_id INTO v_expense_group_id
        FROM chart_of_accounts
        WHERE hospital_id = v_hospital_id
        AND gl_account_no = '5000';
    END IF;

    -- ========================================================================
    -- PART 2: CREATE REVENUE ACCOUNTS (with invoice_type_mapping)
    -- ========================================================================

    -- SERVICE REVENUE (invoice_type_mapping = 'Service')
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Income', '4100',
        'Service Revenue', v_revenue_group_id, TRUE,
        'Service', TRUE
    )
    ON CONFLICT DO NOTHING;

    -- PHARMACY/PRODUCT REVENUE (invoice_type_mapping = 'Product')
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Income', '4200',
        'Pharmacy Sales Revenue', v_revenue_group_id, TRUE,
        'Product', TRUE
    )
    ON CONFLICT DO NOTHING;

    -- PRESCRIPTION REVENUE (invoice_type_mapping = 'Prescription')
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Income', '4300',
        'Prescription Revenue', v_revenue_group_id, TRUE,
        'Prescription', TRUE
    )
    ON CONFLICT DO NOTHING;

    -- PACKAGE REVENUE (for packages - also maps to 'Service')
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Income', '4150',
        'Package & Bundle Revenue', v_revenue_group_id, TRUE,
        NULL, TRUE  -- No direct mapping, uses Service mapping
    )
    ON CONFLICT DO NOTHING;

    -- ========================================================================
    -- PART 3: CREATE ASSET ACCOUNTS
    -- ========================================================================

    -- Accounts Receivable
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Assets', '1100',
        'Accounts Receivable - Patients', v_asset_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    -- Inventory Asset
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Assets', '1200',
        'Pharmacy Inventory', v_asset_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    -- Cash/Bank
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Assets', '1010',
        'Cash on Hand', v_asset_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    -- ========================================================================
    -- PART 4: CREATE LIABILITY ACCOUNTS
    -- ========================================================================

    -- Accounts Payable
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Liabilities', '2100',
        'Accounts Payable - Suppliers', v_liability_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    -- GST Payable
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, gst_related, gst_component, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Liabilities', '2200',
        'GST Payable - Output Tax', v_liability_group_id, TRUE,
        NULL, TRUE, 'OUTPUT', TRUE
    )
    ON CONFLICT DO NOTHING;

    -- GST Input Tax Credit
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, gst_related, gst_component, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Assets', '1300',
        'GST Input Tax Credit', v_asset_group_id, TRUE,
        NULL, TRUE, 'INPUT', TRUE
    )
    ON CONFLICT DO NOTHING;

    -- ========================================================================
    -- PART 5: CREATE EXPENSE ACCOUNTS
    -- ========================================================================

    -- Cost of Goods Sold (COGS)
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Expense', '5100',
        'Cost of Medicines Sold', v_expense_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    -- Discount Given
    INSERT INTO chart_of_accounts (
        account_id, hospital_id, account_group, gl_account_no,
        account_name, parent_account_id, is_posting_account,
        invoice_type_mapping, is_active
    ) VALUES (
        gen_random_uuid(), v_hospital_id, 'Expense', '5200',
        'Discounts Given', v_expense_group_id, TRUE,
        NULL, TRUE
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'GL accounts setup completed successfully!';
    RAISE NOTICE 'Configured for hospital_id: %', v_hospital_id;

END $$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check created accounts
SELECT
    gl_account_no,
    account_name,
    account_group,
    invoice_type_mapping,
    is_posting_account,
    is_active
FROM chart_of_accounts
WHERE hospital_id = (SELECT hospital_id FROM hospitals LIMIT 1)
ORDER BY gl_account_no;

-- Check invoice type mappings specifically
SELECT
    gl_account_no,
    account_name,
    invoice_type_mapping
FROM chart_of_accounts
WHERE hospital_id = (SELECT hospital_id FROM hospitals LIMIT 1)
AND invoice_type_mapping IS NOT NULL
ORDER BY invoice_type_mapping;
