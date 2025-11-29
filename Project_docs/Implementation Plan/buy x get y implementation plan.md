Buy X Get Y Free - Invoice Line Item Integration

 Summary of Approach:

 When user adds an item that triggers a Buy X Get Y campaign, system auto-adds the free "Y" item as a new line with:
 - Free checkbox checked (auto-managed, non-editable)
 - Price = ₹0, GST calculated on original MRP
 - Auto-removed if trigger item qty drops below threshold

 ---
 Changes Required:

 1. Database Migration (new fields for invoice_line_item)
 ALTER TABLE invoice_line_item ADD COLUMN is_free_item BOOLEAN DEFAULT FALSE;
 ALTER TABLE invoice_line_item ADD COLUMN trigger_line_item_id UUID REFERENCES invoice_line_item(line_item_id);
 ALTER TABLE invoice_line_item ADD COLUMN promotion_campaign_id UUID REFERENCES promotion_campaigns(campaign_id);

 2. Invoice Line Item JS (invoice_item.js or similar)
 - After item/qty selection, call API to check Buy X Get Y eligibility
 - If eligible, auto-add new line with:
   - is_free_item: true
   - trigger_line_item_id: <parent line id>
   - promotion_campaign_id: <campaign id>
   - Display "FREE" badge, disable editing
 - On qty change of trigger item, re-check eligibility
 - If no longer eligible, auto-remove free line

 3. New API Endpoint (discount_api.py)
 @discount_bp.route('/check-buy-x-get-y', methods=['POST'])
 def check_buy_x_get_y():
     # Input: item_type, item_id, quantity, hospital_id, patient_id
     # Output: { eligible: true/false, reward_items: [...] }

 4. Billing Service (billing_service.py)
 - Handle is_free_item lines:
   - Unit price = 0
   - GST calculated on original MRP (for tax compliance)
   - Line total = GST amount only
 - Validate trigger line exists when saving free lines

 5. Invoice UI (create_invoice.html or invoice components)
 - Show "FREE" badge for free items
 - Show link to promotion (e.g., "Buy X Get Y: Campaign Name")
 - Disable qty/price editing for free lines
 - Visual indication (different row color, gift icon)

 6. Campaign Create UI (existing gap)
 - Add fields for Buy X Get Y configuration:
   - Trigger: item selector + min qty/amount
   - Reward: item selector + qty + discount %

 ---
 Files to Modify:

 1. app/models/transaction.py - Add fields to InvoiceLineItem
 2. migrations/ - New migration file
 3. app/api/routes/discount_api.py - New endpoint
 4. app/static/js/components/invoice_item.js - Auto-add logic
 5. app/services/billing_service.py - Handle free items
 6. app/templates/billing/create_invoice.html - UI for free badge
 7. app/templates/promotions/campaigns/create.html - Buy X Get Y config UI

 Estimated Effort:

 - Database + API: Small (~1 hour)
 - Invoice JS logic: Medium (~2 hours)
 - Campaign UI: Medium (~1-2 hours)
 - Testing: Medium (~1 hour)
 - Total: ~5-6 hours