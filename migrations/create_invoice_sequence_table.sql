-- Migration: Create invoice_sequences table for thread-safe invoice numbering
-- Date: 2025-01-09
-- Purpose: Prevent duplicate invoice numbers under concurrent load

-- Create invoice_sequences table
CREATE TABLE IF NOT EXISTS invoice_sequences (
    id SERIAL PRIMARY KEY,
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    prefix VARCHAR(10) NOT NULL,  -- SVC, MED, EXM, RX
    financial_year VARCHAR(10) NOT NULL,  -- 2024-2025, 2025-2026
    current_sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_by VARCHAR(15),

    -- Composite unique constraint - one sequence per hospital/prefix/year
    CONSTRAINT uq_invoice_sequence UNIQUE (hospital_id, prefix, financial_year)
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_invoice_sequence_lookup
ON invoice_sequences(hospital_id, prefix, financial_year);

-- Add comment
COMMENT ON TABLE invoice_sequences IS 'Thread-safe invoice sequence tracking to prevent duplicate invoice numbers';
COMMENT ON COLUMN invoice_sequences.prefix IS 'Invoice type prefix: SVC (Service), MED (GST Medicines), EXM (GST Exempt), RX (Prescription)';
COMMENT ON COLUMN invoice_sequences.financial_year IS 'Financial year in format YYYY-YYYY (e.g., 2024-2025)';
COMMENT ON COLUMN invoice_sequences.current_sequence IS 'Current sequence number for this prefix/year combination';

-- Populate existing sequences from invoice_header table
INSERT INTO invoice_sequences (hospital_id, prefix, financial_year, current_sequence)
SELECT
    ih.hospital_id,
    SPLIT_PART(ih.invoice_number, '/', 1) as prefix,
    SPLIT_PART(ih.invoice_number, '/', 2) as financial_year,
    MAX(CAST(SPLIT_PART(ih.invoice_number, '/', 3) AS INTEGER)) as current_sequence
FROM invoice_header ih
WHERE ih.invoice_number SIMILAR TO '[A-Z]{2,3}/[0-9]{4}-[0-9]{4}/[0-9]{5}'  -- Match format: PREFIX/YYYY-YYYY/NNNNN
GROUP BY ih.hospital_id, prefix, financial_year
ON CONFLICT (hospital_id, prefix, financial_year)
DO UPDATE SET current_sequence = EXCLUDED.current_sequence
WHERE invoice_sequences.current_sequence < EXCLUDED.current_sequence;

-- Verify migration
DO $$
DECLARE
    sequence_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO sequence_count FROM invoice_sequences;
    RAISE NOTICE 'Invoice sequences table created successfully. Populated % sequence records.', sequence_count;
END $$;
