-- Add Buy X Get Y Free support fields to invoice_line_item
-- Date: 2025-11-30

-- Add is_free_item flag
ALTER TABLE invoice_line_item 
ADD COLUMN IF NOT EXISTS is_free_item BOOLEAN DEFAULT FALSE;

-- Add trigger_line_id to reference the line item that triggered this free item
ALTER TABLE invoice_line_item 
ADD COLUMN IF NOT EXISTS trigger_line_id UUID;

-- Add promotion_campaign_id to track which campaign granted the free item
ALTER TABLE invoice_line_item 
ADD COLUMN IF NOT EXISTS promotion_campaign_id UUID REFERENCES promotion_campaigns(campaign_id);

-- Add free_item_reason for display purposes
ALTER TABLE invoice_line_item 
ADD COLUMN IF NOT EXISTS free_item_reason VARCHAR(100);

-- Add index for faster lookup of free items by trigger
CREATE INDEX IF NOT EXISTS idx_invoice_line_item_trigger_line 
ON invoice_line_item(trigger_line_id) 
WHERE trigger_line_id IS NOT NULL;

-- Add index for promotion tracking
CREATE INDEX IF NOT EXISTS idx_invoice_line_item_promotion 
ON invoice_line_item(promotion_campaign_id) 
WHERE promotion_campaign_id IS NOT NULL;

COMMENT ON COLUMN invoice_line_item.is_free_item IS 'True if this is a promotional free item from Buy X Get Y campaign';
COMMENT ON COLUMN invoice_line_item.trigger_line_id IS 'Reference to the line item that triggered this free item';
COMMENT ON COLUMN invoice_line_item.promotion_campaign_id IS 'Campaign that granted the free item';
COMMENT ON COLUMN invoice_line_item.free_item_reason IS 'Display text explaining why item is free, e.g., Buy 5 Get 1 Free - DIWALI2025';
