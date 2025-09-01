-- Drop view if exists for clean recreation
DROP VIEW IF EXISTS purchase_orders_view CASCADE;

-- Create comprehensive purchase orders view with PROPER date handling
CREATE OR REPLACE VIEW purchase_orders_view AS
SELECT 
    -- Primary identifiers
    po.po_id,
    po.hospital_id,
    po.branch_id,
    po.po_number,
    
    -- Dates (basic fields first)
    po.po_date,
    po.quotation_date,
    po.expected_delivery_date,
    
    -- Extract date parts for reporting
    EXTRACT(YEAR FROM po.po_date) AS po_year,
    EXTRACT(MONTH FROM po.po_date) AS po_month,
    TO_CHAR(po.po_date, 'YYYY-MM') AS po_month_year,
    TO_CHAR(po.po_date, 'Q') AS po_quarter,
    
    -- Supplier information (denormalized)
    po.supplier_id,
    COALESCE(s.supplier_name, 'Unknown Supplier') AS supplier_name,
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
    
    -- Branch information
    b.name AS branch_name,
    b.state_code AS branch_state_code,
    b.is_active AS branch_is_active,
    
    -- Hospital information
    h.name AS hospital_name,
    h.license_no AS hospital_license_no,
    
    -- Financial information
    po.currency_code,
    po.exchange_rate,
    po.total_amount,
    po.total_amount * COALESCE(po.exchange_rate, 1) AS total_amount_base_currency,
    
    -- Status and workflow
    po.status AS po_status,
    CASE 
        WHEN po.status = 'draft' THEN 1
        WHEN po.status = 'pending' THEN 2
        WHEN po.status = 'approved' THEN 3
        WHEN po.status = 'partially_received' THEN 4
        WHEN po.status = 'received' THEN 5
        WHEN po.status = 'cancelled' THEN 6
        ELSE 7
    END AS status_order,
    po.approved_by,
    
    -- Reference information
    po.quotation_id,
    
    -- Calculated fields for reporting (CORRECTED - direct date subtraction gives integer days)
    CASE 
        WHEN po.po_date IS NOT NULL 
        THEN (CURRENT_DATE - po.po_date::DATE)
        ELSE NULL 
    END AS days_since_po,
    
    CASE 
        WHEN po.expected_delivery_date IS NOT NULL 
        THEN (po.expected_delivery_date - CURRENT_DATE)
        ELSE NULL 
    END AS days_until_delivery,
    
    CASE 
        WHEN po.expected_delivery_date IS NULL THEN 'No Delivery Date'
        WHEN po.expected_delivery_date < CURRENT_DATE AND po.status NOT IN ('received', 'cancelled') THEN 'Overdue'
        WHEN po.expected_delivery_date = CURRENT_DATE AND po.status NOT IN ('received', 'cancelled') THEN 'Due Today'
        ELSE 'On Track'
    END AS delivery_status,
    
    -- Audit fields
    po.created_at,
    po.created_by,
    po.updated_at,
    po.updated_by,
    po.deleted_flag,
    
    -- Search helper field
    LOWER(
        COALESCE(po.po_number, '') || ' ' ||
        COALESCE(s.supplier_name, '') || ' ' ||
        COALESCE(po.quotation_id, '') || ' ' ||
        COALESCE(s.contact_person_name, '')
    ) AS search_text
    
FROM 
    purchase_order_header po
    LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
    LEFT JOIN branches b ON po.branch_id = b.branch_id
    LEFT JOIN hospitals h ON po.hospital_id = h.hospital_id
WHERE 
    po.deleted_flag = false;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_po_view_po_number ON purchase_order_header(po_number);
CREATE INDEX IF NOT EXISTS idx_po_view_supplier_id ON purchase_order_header(supplier_id);
CREATE INDEX IF NOT EXISTS idx_po_view_po_date ON purchase_order_header(po_date);
CREATE INDEX IF NOT EXISTS idx_po_view_status ON purchase_order_header(status);
CREATE INDEX IF NOT EXISTS idx_po_view_branch_id ON purchase_order_header(branch_id);

-- Grant permissions
GRANT SELECT ON purchase_orders_view TO PUBLIC;