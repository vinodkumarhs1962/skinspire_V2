-- ============================================================================
-- Create Supplier Advance GL Account
-- Date: 2025-11-02
-- Description: Create the Supplier Advance asset account for tracking advances
-- ============================================================================

-- This script creates the Supplier Advance GL account for ALL hospitals
-- If you have multiple hospitals, you need to run this for each one

DO $$
DECLARE
    hospital_rec RECORD;
    new_account_id UUID;
BEGIN
    -- Loop through all hospitals
    FOR hospital_rec IN SELECT hospital_id, name FROM hospitals
    LOOP
        RAISE NOTICE 'Creating Supplier Advance account for hospital: %', hospital_rec.name;

        -- Check if account already exists
        IF EXISTS (
            SELECT 1 FROM chart_of_accounts
            WHERE hospital_id = hospital_rec.hospital_id
            AND account_name = 'Supplier Advance'
        ) THEN
            RAISE NOTICE 'Supplier Advance account already exists for hospital: %', hospital_rec.name;
            CONTINUE;
        END IF;

        -- Generate new UUID
        new_account_id := gen_random_uuid();

        -- Insert Supplier Advance account
        INSERT INTO chart_of_accounts (
            account_id,
            hospital_id,
            account_group,
            gl_account_no,
            account_name,
            parent_account_id,
            opening_balance,
            opening_balance_date,
            is_posting_account,
            invoice_type_mapping,
            gst_related,
            gst_component,
            is_active,
            created_at,
            updated_at,
            created_by,
            updated_by
        ) VALUES (
            new_account_id,
            hospital_rec.hospital_id,
            'Assets',                          -- account_group (Assets/Liabilities/Income/Expense)
            '1250',                            -- gl_account_no (Current Asset)
            'Supplier Advance',                -- account_name
            NULL,                              -- parent_account_id (Top-level account)
            0,                                 -- opening_balance
            NULL,                              -- opening_balance_date
            TRUE,                              -- is_posting_account
            NULL,                              -- invoice_type_mapping
            FALSE,                             -- gst_related
            NULL,                              -- gst_component
            TRUE,                              -- is_active
            CURRENT_TIMESTAMP,                 -- created_at
            CURRENT_TIMESTAMP,                 -- updated_at (REQUIRED by TimestampMixin)
            'system',                          -- created_by
            'system'                           -- updated_by
        );

        RAISE NOTICE 'Successfully created Supplier Advance account (ID: %) for hospital: %',
                     new_account_id, hospital_rec.name;
    END LOOP;

    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE '============================================================================';
END $$;

-- Verification: Display created accounts
SELECT
    h.name AS hospital_name,
    coa.gl_account_no,
    coa.account_name,
    coa.account_group,
    coa.is_active
FROM chart_of_accounts coa
JOIN hospitals h ON coa.hospital_id = h.hospital_id
WHERE coa.account_name = 'Supplier Advance'
ORDER BY h.name;
