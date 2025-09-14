-- Drop view if exists
DROP VIEW IF EXISTS supplier_invoices_view CASCADE;

-- Create comprehensive supplier invoices view with ACTUAL fields
CREATE OR REPLACE VIEW supplier_invoices_view AS
SELECT 
    -- Primary identifiers
    si.invoice_id,
    si.hospital_id,
    si.branch_id,
    si.supplier_invoice_number,
    
    -- Dates (only fields that actually exist)
    si.invoice_date,
    si.due_date,
    EXTRACT(YEAR FROM si.invoice_date) AS invoice_year,
    EXTRACT(MONTH FROM si.invoice_date) AS invoice_month,
    TO_CHAR(si.invoice_date, 'YYYY-MM') AS invoice_month_year,
    TO_CHAR(si.invoice_date, 'Q') AS invoice_quarter,
    
    -- Purchase Order relationship
    si.po_id,
    po.po_number,
    po.po_date,
    po.quotation_id,
    
    -- Supplier information (denormalized)
    si.supplier_id,
    COALESCE(s.supplier_name, 'Unknown Supplier') AS supplier_name,
    s.supplier_category,
    s.contact_person_name AS supplier_contact_person,
    s.contact_info->>'mobile' AS supplier_mobile,
    s.contact_info->>'phone' AS supplier_phone,
    s.email AS supplier_email,
    s.gst_registration_number AS supplier_gst,
    s.payment_terms AS supplier_payment_terms,
    s.status AS supplier_status,
    
    -- Branch information
    b.name AS branch_name,
    b.state_code AS branch_state_code,
    b.is_active AS branch_is_active,
    
    -- Hospital information
    h.name AS hospital_name,
    h.license_no AS hospital_license_no,
    
    -- Financial information (actual fields only)
    si.total_amount AS invoice_total_amount,
    si.cgst_amount,
    si.sgst_amount,
    si.igst_amount,
    si.total_gst_amount,
    
    -- NEW: Paid amount calculation - sum of all approved/completed/paid payments
    COALESCE(
        (SELECT SUM(sp.amount) 
         FROM supplier_payment sp 
         WHERE sp.invoice_id = si.invoice_id 
         AND sp.workflow_status IN ('approved', 'completed', 'paid')), 
        0
    )::NUMERIC(12,2) AS paid_amount,
    
    -- NEW: Balance amount calculation (invoice total - paid amount)
    (si.total_amount - COALESCE(
        (SELECT SUM(sp.amount) 
         FROM supplier_payment sp 
         WHERE sp.invoice_id = si.invoice_id 
         AND sp.workflow_status IN ('approved', 'completed', 'paid')), 
        0
    ))::NUMERIC(12,2) AS balance_amount,
    
    -- GST Information
    si.supplier_gstin,
    si.place_of_supply,
    si.reverse_charge,
    si.itc_eligible,
    
    -- Currency
    si.currency_code,
    si.exchange_rate,
    
    -- Payment and posting status
    si.payment_status,
    si.gl_posted,
    si.inventory_posted,
    si.posting_date,
    si.posting_reference,
    
    -- Reversal information
    si.is_reversed,
    si.is_credit_note,
    si.original_invoice_id,
    si.reversed_by_invoice_id,
    si.reversal_reason,
    
    -- Notes
    si.notes,
    
    -- Aging analysis
    CASE 
        WHEN si.invoice_date IS NOT NULL 
        THEN (CURRENT_DATE - si.invoice_date::DATE)
        ELSE NULL 
    END AS invoice_age_days,
    
    CASE 
        WHEN si.due_date IS NOT NULL 
        THEN (CURRENT_DATE - si.due_date)
        ELSE NULL 
    END AS days_overdue,
    
    CASE 
        WHEN si.payment_status = 'paid' THEN 'Paid'
        WHEN si.due_date IS NULL THEN 'No Due Date'
        WHEN si.due_date < CURRENT_DATE THEN 'Overdue'
        WHEN si.due_date = CURRENT_DATE THEN 'Due Today'
        WHEN si.due_date <= CURRENT_DATE + INTERVAL '7 days' THEN 'Due Soon'
        ELSE 'Current'
    END AS aging_status,
    
    -- Aging buckets for reports
    CASE 
        WHEN si.payment_status = 'paid' THEN 'Paid'
        WHEN si.due_date IS NULL THEN 'No Due Date'
        WHEN CURRENT_DATE <= si.due_date THEN 'Current'
        WHEN (CURRENT_DATE - si.due_date) <= 30 THEN '1-30 Days'
        WHEN (CURRENT_DATE - si.due_date) <= 60 THEN '31-60 Days'
        WHEN (CURRENT_DATE - si.due_date) <= 90 THEN '61-90 Days'
        ELSE 'Over 90 Days'
    END AS aging_bucket,
    
    -- Audit fields
    si.created_at,
    si.created_by,
    si.updated_at,
    si.updated_by,
    
    -- Search helper field
    LOWER(
        COALESCE(si.supplier_invoice_number, '') || ' ' ||
        COALESCE(s.supplier_name, '') || ' ' ||
        COALESCE(po.po_number, '')
    ) AS search_text
    
FROM 
    supplier_invoice si
    LEFT JOIN suppliers s ON si.supplier_id = s.supplier_id
    LEFT JOIN purchase_order_header po ON si.po_id = po.po_id
    LEFT JOIN branches b ON si.branch_id = b.branch_id
    LEFT JOIN hospitals h ON si.hospital_id = h.hospital_id;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_si_view_invoice_number ON supplier_invoice(supplier_invoice_number);
CREATE INDEX IF NOT EXISTS idx_si_view_supplier_id ON supplier_invoice(supplier_id);
CREATE INDEX IF NOT EXISTS idx_si_view_po_id ON supplier_invoice(po_id);
CREATE INDEX IF NOT EXISTS idx_si_view_invoice_date ON supplier_invoice(invoice_date);
CREATE INDEX IF NOT EXISTS idx_si_view_due_date ON supplier_invoice(due_date);
CREATE INDEX IF NOT EXISTS idx_si_view_payment_status ON supplier_invoice(payment_status);

-- NEW: Index for payment lookups (CORRECTED TABLE NAME)
CREATE INDEX IF NOT EXISTS idx_supplier_payment_invoice_workflow 
ON supplier_payment(invoice_id, workflow_status);

-- Grant permissions
GRANT SELECT ON supplier_invoices_view TO PUBLIC;

-- Verify the new columns were added
SELECT 
    column_name, 
    data_type,
    numeric_precision,
    numeric_scale
FROM information_schema.columns 
WHERE table_name = 'supplier_invoices_view' 
AND column_name IN ('balance_amount', 'paid_amount')
ORDER BY column_name;

-- Test query to verify calculations
SELECT 
    supplier_invoice_number,
    supplier_name,
    invoice_total_amount,
    paid_amount,
    balance_amount,
    payment_status,
    CASE 
        WHEN balance_amount = 0 THEN 'Fully Paid'
        WHEN paid_amount > 0 AND balance_amount > 0 THEN 'Partially Paid'
        WHEN paid_amount = 0 THEN 'Unpaid'
        ELSE 'Check'
    END AS calculated_status
FROM supplier_invoices_view 
ORDER BY invoice_date DESC
LIMIT 10;