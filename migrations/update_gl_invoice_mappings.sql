-- ============================================================================
-- Update GL Account Invoice Type Mappings
-- ============================================================================
-- This fixes NULL gl_account_id in invoices by mapping existing GL accounts
-- to invoice types
--
-- Date: 2025-11-17
-- ============================================================================

-- Get hospital_id
DO $$
DECLARE
    v_hospital_id UUID;
BEGIN
    SELECT hospital_id INTO v_hospital_id
    FROM hospitals
    LIMIT 1;

    RAISE NOTICE 'Updating GL account mappings for hospital: %', v_hospital_id;

    -- ========================================================================
    -- Map Revenue Accounts to Invoice Types
    -- ========================================================================

    -- SERVICE REVENUE → 'Service' invoice type
    -- This handles consultation, treatment, packages
    UPDATE chart_of_accounts
    SET invoice_type_mapping = 'Service'
    WHERE hospital_id = v_hospital_id
    AND gl_account_no = '4100'  -- Service Revenue
    AND invoice_type_mapping IS NULL;

    RAISE NOTICE 'Mapped GL 4100 (Service Revenue) → invoice_type: Service';

    -- MEDICINE REVENUE → 'Product' invoice type
    -- This handles OTC, medicines with GST, GST-exempt medicines
    UPDATE chart_of_accounts
    SET invoice_type_mapping = 'Product'
    WHERE hospital_id = v_hospital_id
    AND gl_account_no = '4300'  -- Medicine Revenue
    AND invoice_type_mapping IS NULL;

    RAISE NOTICE 'Mapped GL 4300 (Medicine Revenue) → invoice_type: Product';

    -- PRESCRIPTION SALES → 'Prescription' invoice type
    -- This handles prescription composite invoices
    UPDATE chart_of_accounts
    SET invoice_type_mapping = 'Prescription'
    WHERE hospital_id = v_hospital_id
    AND gl_account_no = '4320'  -- Prescription Sales
    AND invoice_type_mapping IS NULL;

    RAISE NOTICE 'Mapped GL 4320 (Prescription Sales) → invoice_type: Prescription';

    RAISE NOTICE 'GL account invoice type mappings completed successfully!';

END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check the mappings
SELECT
    gl_account_no,
    account_name,
    invoice_type_mapping,
    is_active
FROM chart_of_accounts
WHERE hospital_id = (SELECT hospital_id FROM hospitals LIMIT 1)
AND invoice_type_mapping IS NOT NULL
ORDER BY gl_account_no;

-- Expected result:
-- 4100 | Service Revenue     | Service      | t
-- 4300 | Medicine Revenue    | Product      | t
-- 4320 | Prescription Sales  | Prescription | t
