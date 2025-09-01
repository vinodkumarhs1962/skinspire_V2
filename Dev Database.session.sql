-- SQL Migration Script for Skinspire Database
-- Date: 2025-04-19

-- Determine the correct invoice headers table name
DO $$
DECLARE
    invoice_table_name TEXT;
BEGIN
    -- Find the invoice headers table - check common naming conventions
    SELECT table_name INTO invoice_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_headers', 'invoices', 'invoice_header', 'invoice')
    LIMIT 1;

    IF invoice_table_name IS NULL THEN
        RAISE EXCEPTION 'Could not find invoice headers table. Please specify the correct table name.';
    ELSE
        RAISE NOTICE 'Found invoice table: %', invoice_table_name;
    END IF;
END $$;

-- 1. Add cost_price column to medicines table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'medicines' 
        AND column_name = 'cost_price'
    ) THEN
        ALTER TABLE medicines ADD COLUMN cost_price NUMERIC(10, 2);
        
        -- Optional: Add comment to the column
        COMMENT ON COLUMN medicines.cost_price IS 'Cost price for profit calculation';
        
        RAISE NOTICE 'Added cost_price column to medicines table';
    ELSE
        RAISE NOTICE 'cost_price column already exists in medicines table, skipping...';
    END IF;
END $$;

-- 2. Add is_cancelled, cancellation_reason, and cancelled_at columns to invoice table
DO $$
DECLARE
    invoice_table_name TEXT;
BEGIN
    -- Find the invoice headers table
    SELECT table_name INTO invoice_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_headers', 'invoices', 'invoice_header', 'invoice')
    LIMIT 1;
    
    IF invoice_table_name IS NULL THEN
        RAISE EXCEPTION 'Could not find invoice headers table';
    END IF;
    
    -- Dynamically add columns to the invoice table
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = invoice_table_name
        AND column_name = 'is_cancelled'
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD COLUMN is_cancelled BOOLEAN NOT NULL DEFAULT FALSE', invoice_table_name);
        RAISE NOTICE 'Added is_cancelled column to % table', invoice_table_name;
    ELSE
        RAISE NOTICE 'is_cancelled column already exists in % table, skipping...', invoice_table_name;
    END IF;
    
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = invoice_table_name
        AND column_name = 'cancellation_reason'
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD COLUMN cancellation_reason VARCHAR(255)', invoice_table_name);
        RAISE NOTICE 'Added cancellation_reason column to % table', invoice_table_name;
    ELSE
        RAISE NOTICE 'cancellation_reason column already exists in % table, skipping...', invoice_table_name;
    END IF;
    
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = invoice_table_name
        AND column_name = 'cancelled_at'
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE', invoice_table_name);
        RAISE NOTICE 'Added cancelled_at column to % table', invoice_table_name;
    ELSE
        RAISE NOTICE 'cancelled_at column already exists in % table, skipping...', invoice_table_name;
    END IF;
END $$;

-- 3. Add is_consolidated_prescription column to invoice line items table
DO $$
DECLARE
    line_items_table_name TEXT;
BEGIN
    -- Find the invoice line items table
    SELECT table_name INTO line_items_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_line_items', 'invoice_lines', 'invoice_items', 'invoice_details')
    LIMIT 1;
    
    IF line_items_table_name IS NULL THEN
        RAISE NOTICE 'Could not find invoice line items table, skipping line items updates...';
        RETURN;
    END IF;
    
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = line_items_table_name
        AND column_name = 'is_consolidated_prescription'
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD COLUMN is_consolidated_prescription BOOLEAN NOT NULL DEFAULT FALSE', line_items_table_name);
        RAISE NOTICE 'Added is_consolidated_prescription column to % table', line_items_table_name;
    ELSE
        RAISE NOTICE 'is_consolidated_prescription column already exists in % table, skipping...', line_items_table_name;
    END IF;
END $$;

-- 4. Create prescription_invoice_maps table if needed and if we can find the invoice table
DO $$
DECLARE
    invoice_table_name TEXT;
BEGIN
    -- Skip if table already exists
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name = 'prescription_invoice_maps'
    ) THEN
        RAISE NOTICE 'prescription_invoice_maps table already exists, skipping...';
        RETURN;
    END IF;

    -- Find the invoice headers table
    SELECT table_name INTO invoice_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_headers', 'invoices', 'invoice_header', 'invoice')
    LIMIT 1;
    
    IF invoice_table_name IS NULL THEN
        RAISE NOTICE 'Could not find invoice headers table, skipping prescription_invoice_maps creation...';
        RETURN;
    END IF;
    
    -- Create the dynamic SQL for creating the table with the correct FK reference
    EXECUTE format('
        CREATE TABLE prescription_invoice_maps (
            map_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
            invoice_id UUID NOT NULL REFERENCES %I(invoice_id),
            medicine_id UUID NOT NULL REFERENCES medicines(medicine_id),
            medicine_name VARCHAR(100),
            batch VARCHAR(50),
            expiry_date DATE,
            quantity NUMERIC(10, 2) NOT NULL,
            unit_price NUMERIC(10, 2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            created_by VARCHAR(50),
            updated_by VARCHAR(50)
        )', invoice_table_name);
    
    -- Add indexes for better performance
    CREATE INDEX idx_prescription_maps_hospital ON prescription_invoice_maps(hospital_id);
    CREATE INDEX idx_prescription_maps_invoice ON prescription_invoice_maps(invoice_id);
    CREATE INDEX idx_prescription_maps_medicine ON prescription_invoice_maps(medicine_id);
    
    RAISE NOTICE 'Created prescription_invoice_maps table with references to % and indexes', invoice_table_name;
END $$;

-- 5. Update existing medicines with estimated cost_price (if data exists) only for those that have NULL cost_price
DO $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    -- Check if cost_price column exists before attempting update
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_schema = 'public'
        AND table_name = 'medicines' 
        AND column_name = 'cost_price'
    ) THEN
        -- First verify inventory table exists
        IF NOT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'inventory'
        ) THEN
            RAISE NOTICE 'inventory table not found, skipping cost_price updates...';
            RETURN;
        END IF;
        
        -- Verify inventory table has unit_price column
        IF NOT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'inventory'
            AND column_name = 'unit_price'
        ) THEN
            RAISE NOTICE 'unit_price column not found in inventory table, skipping cost_price updates...';
            RETURN;
        END IF;
        
        -- Update medicines with data from inventory
        WITH updates AS (
            UPDATE medicines m
            SET cost_price = (
                SELECT i.unit_price * 0.7
                FROM inventory i
                WHERE i.medicine_id = m.medicine_id
                ORDER BY i.created_at DESC
                LIMIT 1
            )
            WHERE m.cost_price IS NULL
            AND EXISTS (
                SELECT 1 FROM inventory i WHERE i.medicine_id = m.medicine_id
            )
            RETURNING m.medicine_id
        )
        SELECT COUNT(*) INTO updated_count FROM updates;
        
        RAISE NOTICE 'Updated cost_price for % medicines from inventory data', updated_count;
        
        -- For medicines with no inventory data, set default value
        WITH defaults AS (
            UPDATE medicines
            SET cost_price = 0
            WHERE cost_price IS NULL
            RETURNING medicine_id
        )
        SELECT COUNT(*) INTO updated_count FROM defaults;
        
        RAISE NOTICE 'Set default cost_price for % medicines with no inventory data', updated_count;
    ELSE
        RAISE NOTICE 'cost_price column does not exist in medicines table, skipping updates...';
    END IF;
END $$;

-- 6. Verify changes
DO $$
DECLARE
    invoice_table_name TEXT;
    line_items_table_name TEXT;
BEGIN
    RAISE NOTICE '-------------------------';
    RAISE NOTICE 'Migration completed successfully';
    RAISE NOTICE '-------------------------';
    
    -- Find table names
    SELECT table_name INTO invoice_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_headers', 'invoices', 'invoice_header', 'invoice')
    LIMIT 1;
    
    SELECT table_name INTO line_items_table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('invoice_line_items', 'invoice_lines', 'invoice_items', 'invoice_details')
    LIMIT 1;
    
    -- Output summary of current table structure
    RAISE NOTICE 'Current medicines table structure:';
    FOR col IN (
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'medicines'
        AND column_name = 'cost_price'
    ) LOOP
        RAISE NOTICE '% (% - nullable: %)', col.column_name, col.data_type, col.is_nullable;
    END LOOP;
    
    IF invoice_table_name IS NOT NULL THEN
        RAISE NOTICE '-------------------------';
        RAISE NOTICE 'Current % cancellation columns:', invoice_table_name;
        FOR col IN (
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = invoice_table_name
            AND column_name IN ('is_cancelled', 'cancellation_reason', 'cancelled_at')
        ) LOOP
            RAISE NOTICE '% (% - nullable: %)', col.column_name, col.data_type, col.is_nullable;
        END LOOP;
    END IF;
    
    IF line_items_table_name IS NOT NULL THEN
        RAISE NOTICE '-------------------------';
        RAISE NOTICE 'Current % consolidated prescription column:', line_items_table_name;
        FOR col IN (
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = line_items_table_name
            AND column_name = 'is_consolidated_prescription'
        ) LOOP
            RAISE NOTICE '% (% - nullable: %)', col.column_name, col.data_type, col.is_nullable;
        END LOOP;
    END IF;
    
    RAISE NOTICE '-------------------------';
    
    -- Check if new table was created
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'prescription_invoice_maps'
    ) THEN
        RAISE NOTICE 'prescription_invoice_maps table was created successfully';
    END IF;
    
    RAISE NOTICE '-------------------------';
END $$;