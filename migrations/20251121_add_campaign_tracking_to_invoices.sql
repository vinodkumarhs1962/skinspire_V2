-- Migration: Add Campaign Tracking to Invoices
-- Date: 2025-11-21
-- Author: Claude Code
--
-- PURPOSE:
-- Add campaigns_applied JSONB field to invoice_header table for tracking
-- which promotions were applied to each invoice.
--
-- RELATED IMPLEMENTATION:
-- - app/models/transaction.py:473 - campaigns_applied field added to InvoiceHeader model
-- - app/services/discount_service.py:1312-1466 - Campaign tracking methods
-- - app/services/billing_service.py:864,954 - Integration in invoice creation
--
-- TRACKING STRUCTURE:
-- {
--   "applied_promotions": [
--     {
--       "promotion_id": "uuid",
--       "campaign_name": "Premium Service - Free Consultation",
--       "campaign_code": "PREMIUM_CONSULT",
--       "promotion_type": "buy_x_get_y",
--       "items_affected": ["item-id-1", "item-id-2"],
--       "total_discount": 500.00
--     }
--   ]
-- }

-- ============================================================================
-- ADD CAMPAIGN TRACKING COLUMN
-- ============================================================================

-- Add campaigns_applied JSONB column to invoice_header
ALTER TABLE invoice_header
ADD COLUMN IF NOT EXISTS campaigns_applied JSONB;

-- Add comment for documentation
COMMENT ON COLUMN invoice_header.campaigns_applied IS
'Tracks which promotion campaigns were applied to this invoice. JSON structure contains array of applied_promotions with campaign details, items affected, and total discount. Used for campaign effectiveness reporting. Added Nov 2025.';

-- ============================================================================
-- CREATE INDEX FOR PERFORMANCE
-- ============================================================================

-- Create GIN index for JSONB queries (checking if specific campaign was used)
CREATE INDEX IF NOT EXISTS idx_invoice_campaigns_applied
ON invoice_header USING GIN (campaigns_applied);

-- Create partial index for invoices WITH promotions (faster reporting queries)
CREATE INDEX IF NOT EXISTS idx_invoice_with_campaigns
ON invoice_header (invoice_date, hospital_id)
WHERE campaigns_applied IS NOT NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if column was added
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'invoice_header'
AND column_name = 'campaigns_applied';

-- Check indexes created
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'invoice_header'
AND indexname LIKE '%campaign%';

-- Count existing invoices (should all have NULL initially)
SELECT
    COUNT(*) AS total_invoices,
    COUNT(campaigns_applied) AS invoices_with_campaigns
FROM invoice_header;

-- ============================================================================
-- EXAMPLE QUERIES (For Reference)
-- ============================================================================

-- Query 1: Find all invoices with promotions applied
-- SELECT
--     invoice_number,
--     invoice_date,
--     total_discount,
--     campaigns_applied->'applied_promotions' AS promotions
-- FROM invoice_header
-- WHERE campaigns_applied IS NOT NULL
-- ORDER BY invoice_date DESC
-- LIMIT 10;

-- Query 2: Find invoices using specific campaign
-- SELECT
--     invoice_number,
--     invoice_date,
--     campaigns_applied
-- FROM invoice_header
-- WHERE campaigns_applied @> '{"applied_promotions": [{"campaign_code": "PREMIUM_CONSULT"}]}'::jsonb
-- ORDER BY invoice_date DESC;

-- Query 3: Campaign usage summary (from JSONB)
-- SELECT
--     promo->>'campaign_name' AS campaign_name,
--     promo->>'campaign_code' AS campaign_code,
--     COUNT(*) AS usage_count,
--     SUM((promo->>'total_discount')::numeric) AS total_discount_given
-- FROM invoice_header,
--      jsonb_array_elements(campaigns_applied->'applied_promotions') AS promo
-- WHERE campaigns_applied IS NOT NULL
-- GROUP BY promo->>'campaign_name', promo->>'campaign_code'
-- ORDER BY total_discount_given DESC;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

SELECT
    'MIGRATION COMPLETE' AS status,
    'campaigns_applied column added to invoice_header' AS action,
    'Campaign tracking now available on all invoices' AS note;
