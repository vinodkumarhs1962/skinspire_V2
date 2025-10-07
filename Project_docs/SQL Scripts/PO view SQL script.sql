-- ============================================================================
-- CORRECTED: Add soft delete fields to existing purchase_orders_view
-- Using ACTUAL column names from master.py and transaction.py
-- ============================================================================

DROP VIEW IF EXISTS purchase_orders_view CASCADE;

CREATE OR REPLACE VIEW purchase_orders_view AS
SELECT 
    -- Primary identifiers
    po.po_id,
    po.hospital_id,
    po.branch_id,
    po.po_number,
    
    -- Dates
    po.po_date,
    po.quotation_date,
    po.expected_delivery_date,
    
    -- Date extractions
    EXTRACT(YEAR FROM po.po_date) AS po_year,
    EXTRACT(MONTH FROM po.po_date) AS po_month,
    TO_CHAR(po.po_date, 'YYYY-MM') AS po_month_year,
    TO_CHAR(po.po_date, 'Q') AS po_quarter,
    
    -- Supplier fields - using ACTUAL column names from suppliers table
    po.supplier_id,
    s.supplier_name,
    s.supplier_category,
    s.contact_person_name AS supplier_contact_person,
    s.contact_info->>'mobile' AS supplier_mobile,
    s.contact_info->>'phone' AS supplier_phone,
    s.email AS supplier_email,
    s.gst_registration_number AS supplier_gst,
    s.pan_number AS supplier_pan,
    s.payment_terms AS supplier_payment_terms,
    s.black_listed AS supplier_black_listed,
    s.status AS supplier_status,
    
    -- Branch fields - using ACTUAL column names from branches table
    b.name AS branch_name,  -- ✅ CORRECTED: Column is 'name', not 'branch_name'
    b.state_code AS branch_state_code,
    b.is_active AS branch_is_active,
    
    -- Hospital fields - using ACTUAL column names from hospitals table
    h.name AS hospital_name,  -- ✅ CORRECTED: Column is 'name', not 'hospital_name'
    h.license_no AS hospital_license_no,
    
    -- Financial fields
    po.currency_code,
    po.exchange_rate,
    po.total_amount,
    CASE 
        WHEN po.currency_code = 'INR' THEN po.total_amount
        ELSE po.total_amount * COALESCE(po.exchange_rate, 1.0)
    END AS total_amount_base_currency,
    
    -- Status fields
    po.status AS po_status,
    CASE po.status
        WHEN 'draft' THEN 1
        WHEN 'approved' THEN 2
        WHEN 'received' THEN 3
        WHEN 'cancelled' THEN 4
        ELSE 5
    END AS status_order,
    
    po.approved_by,
    
    -- Reference fields
    po.quotation_id,
    
    -- Calculated fields
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - po.po_date))::INTEGER AS days_since_po,
    CASE 
        WHEN po.expected_delivery_date IS NOT NULL THEN
            EXTRACT(DAY FROM (po.expected_delivery_date::TIMESTAMP - CURRENT_TIMESTAMP))::INTEGER
        ELSE NULL
    END AS days_until_delivery,
    CASE 
        WHEN po.expected_delivery_date IS NULL THEN 'no_date'
        WHEN po.status = 'received' THEN 'delivered'
        WHEN po.expected_delivery_date < CURRENT_DATE THEN 'overdue'
        WHEN po.expected_delivery_date = CURRENT_DATE THEN 'due_today'
        WHEN po.expected_delivery_date <= CURRENT_DATE + INTERVAL '7 days' THEN 'due_soon'
        ELSE 'on_track'
    END AS delivery_status,
    
    -- ✅ NEW: Soft delete fields
    po.is_deleted,
    po.deleted_at,
    po.deleted_by,
    
    -- ✅ NEW: Approval timestamp
    po.approved_at,
    
    -- Backward compatibility
    po.deleted_flag,
    
    -- Audit fields
    po.created_at,
    po.created_by,
    po.updated_at,
    po.updated_by,
    
    -- Search helper
    (
        COALESCE(po.po_number, '') || ' ' ||
        COALESCE(s.supplier_name, '') || ' ' ||
        COALESCE(po.quotation_id, '') || ' ' ||
        COALESCE(b.name, '')
    ) AS search_text

FROM purchase_order_header po
LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
LEFT JOIN branches b ON po.branch_id = b.branch_id  
LEFT JOIN hospitals h ON po.hospital_id = h.hospital_id;

-- ✅ Index for soft delete filtering
CREATE INDEX IF NOT EXISTS idx_po_header_is_deleted 
    ON purchase_order_header(is_deleted) 
    WHERE is_deleted = FALSE;