-- =====================================================================
-- CORRECTED Supplier Payments View - FINAL VERSION
-- Fixes the workflow_status column issue WITHOUT adding non-existent columns
-- Preserves ALL denormalized fields from original view
-- =====================================================================

-- Drop view if exists
DROP VIEW IF EXISTS supplier_payments_view CASCADE;

-- Create comprehensive supplier payments view with CORRECT column mappings
CREATE OR REPLACE VIEW supplier_payments_view AS
SELECT 
    -- Primary identifiers
    sp.payment_id,
    sp.hospital_id,
    sp.branch_id,
    sp.reference_no,
    
    -- Dates
    sp.payment_date,
    EXTRACT(YEAR FROM sp.payment_date) AS payment_year,
    EXTRACT(MONTH FROM sp.payment_date) AS payment_month,
    TO_CHAR(sp.payment_date, 'YYYY-MM') AS payment_month_year,
    TO_CHAR(sp.payment_date, 'Q') AS payment_quarter,
    TO_CHAR(sp.payment_date, 'Day') AS payment_day_name,
    
    -- Invoice relationship
    sp.invoice_id,
    si.supplier_invoice_number,
    si.invoice_date,
    si.total_amount AS invoice_amount,
    si.po_id,
    po.po_number,
    
    -- Supplier information (denormalized) - PRESERVING ALL FIELDS
    sp.supplier_id,
    COALESCE(s.supplier_name, 'Unknown Supplier') AS supplier_name,
    s.supplier_category,
    s.contact_person_name AS supplier_contact_person,
    s.contact_info->>'mobile' AS supplier_mobile,
    s.contact_info->>'phone' AS supplier_phone,
    s.email AS supplier_email,
    s.gst_registration_number AS supplier_gst,
    s.payment_terms AS supplier_payment_terms,
    s.bank_details->>'bank_name' AS supplier_bank_name,
    s.bank_details->>'account_number' AS supplier_account_number,
    s.bank_details->>'ifsc_code' AS supplier_ifsc_code,
    s.status AS supplier_status,
    
    -- Branch information - PRESERVED
    b.name AS branch_name,
    b.state_code AS branch_state_code,
    b.is_active AS branch_is_active,
    
    -- Hospital information - PRESERVED
    h.name AS hospital_name,
    h.license_no AS hospital_license_no,
    
    -- Payment details
    sp.amount AS payment_amount,
    sp.payment_method,
    sp.payment_category,
    sp.payment_source,
    sp.status AS payment_status_old,  -- Original status field
    
    -- Amounts breakdown - PRESERVED
    COALESCE(sp.cash_amount, 0) AS cash_amount,
    COALESCE(sp.cheque_amount, 0) AS cheque_amount,
    COALESCE(sp.bank_transfer_amount, 0) AS bank_transfer_amount,
    COALESCE(sp.upi_amount, 0) AS upi_amount,
    
    -- Cheque details - PRESERVED
    sp.cheque_number,
    sp.cheque_date,
    sp.cheque_bank,
    sp.cheque_status,
    sp.cheque_clearance_date,
    
    -- Bank transfer details - PRESERVED
    sp.bank_name AS payment_bank_name,
    sp.bank_reference_number,
    sp.ifsc_code AS payment_ifsc_code,
    sp.transfer_mode,
    
    -- UPI details - PRESERVED
    sp.upi_transaction_id,
    sp.upi_reference_id,
    sp.upi_id,
    sp.upi_app_name,
    
    -- Notes
    sp.notes,
    
    -- Currency
    sp.currency_code,
    sp.exchange_rate,
    
    -- =====================================================================
    -- CRITICAL FIX: Status and workflow columns
    -- The Python model (views.py) expects BOTH columns to exist
    -- =====================================================================
    sp.workflow_status,                    -- The actual workflow_status from table
    sp.workflow_status AS payment_status,  -- Also expose as payment_status for compatibility
    
    -- Approval workflow fields - PRESERVED
    sp.approved_by,
    sp.approved_at,
    sp.approved_at AS approval_date,  -- Alias for compatibility
    sp.rejected_by,
    sp.rejected_at,
    sp.rejection_reason,
    sp.requires_approval,
    sp.approval_level,
    
    -- Payment method grouping for reports - PRESERVED
    CASE 
        WHEN sp.payment_method IN ('cash', 'Cash') THEN 'Cash'
        WHEN sp.payment_method IN ('cheque', 'Cheque', 'check') THEN 'Cheque'
        WHEN sp.payment_method IN ('bank_transfer', 'NEFT', 'RTGS', 'IMPS') THEN 'Electronic'
        WHEN sp.payment_method IN ('UPI', 'upi') THEN 'UPI'
        WHEN sp.payment_method IN ('credit_card', 'debit_card', 'card') THEN 'Card'
        ELSE 'Other'
    END AS payment_method_group,
    
    -- Reconciliation status - PRESERVED
    sp.reconciliation_status,
    sp.reconciliation_date,
    
    -- GL Posting - PRESERVED
    sp.gl_posted,
    sp.posting_date,
    sp.posting_reference,
    
    -- Time-based analysis - PRESERVED
    CASE 
        WHEN sp.payment_date IS NOT NULL AND si.invoice_date IS NOT NULL 
        THEN (sp.payment_date::DATE - si.invoice_date::DATE)
        ELSE NULL 
    END AS days_to_payment,
    
    CASE 
        WHEN sp.payment_date IS NOT NULL AND si.due_date IS NOT NULL 
        THEN (sp.payment_date::DATE - si.due_date)
        ELSE NULL 
    END AS days_from_due_date,
    
    CASE 
        WHEN si.due_date IS NULL THEN 'Unknown'
        WHEN sp.payment_date IS NULL THEN 'Not Paid'
        WHEN sp.payment_date::DATE <= si.due_date THEN 'On Time'
        ELSE 'Late'
    END AS payment_timeliness,
    
    -- Audit fields - PRESERVED
    sp.created_at,
    sp.created_by,
    sp.updated_at,
    sp.updated_by,
    
    -- Search helper field - PRESERVED
    LOWER(
        COALESCE(sp.reference_no, '') || ' ' ||
        COALESCE(s.supplier_name, '') || ' ' ||
        COALESCE(si.supplier_invoice_number, '') || ' ' ||
        COALESCE(po.po_number, '') || ' ' ||
        COALESCE(sp.cheque_number, '') || ' ' ||
        COALESCE(sp.bank_reference_number, '') || ' ' ||
        COALESCE(sp.upi_transaction_id, '')
    ) AS search_text
    
FROM 
    supplier_payment sp
    LEFT JOIN suppliers s ON sp.supplier_id = s.supplier_id
    LEFT JOIN supplier_invoice si ON sp.invoice_id = si.invoice_id
    LEFT JOIN purchase_order_header po ON si.po_id = po.po_id
    LEFT JOIN branches b ON sp.branch_id = b.branch_id
    LEFT JOIN hospitals h ON sp.hospital_id = h.hospital_id;
    -- No WHERE clause for deleted_at as the column doesn't exist

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sp_view_hospital_id ON supplier_payment(hospital_id);
CREATE INDEX IF NOT EXISTS idx_sp_view_branch_id ON supplier_payment(branch_id);
CREATE INDEX IF NOT EXISTS idx_sp_view_payment_date ON supplier_payment(payment_date);
CREATE INDEX IF NOT EXISTS idx_sp_view_supplier_id ON supplier_payment(supplier_id);
CREATE INDEX IF NOT EXISTS idx_sp_view_invoice_id ON supplier_payment(invoice_id);
CREATE INDEX IF NOT EXISTS idx_sp_view_workflow_status ON supplier_payment(workflow_status);
CREATE INDEX IF NOT EXISTS idx_sp_view_reference_no ON supplier_payment(reference_no);
CREATE INDEX IF NOT EXISTS idx_sp_view_payment_method ON supplier_payment(payment_method);

-- Grant permissions
GRANT SELECT ON supplier_payments_view TO PUBLIC;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- 1. Verify both columns exist:
/*
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'supplier_payments_view' 
AND column_name IN ('workflow_status', 'payment_status')
ORDER BY ordinal_position;
*/

-- 2. Verify supplier denormalized fields exist:
/*
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'supplier_payments_view' 
AND column_name LIKE 'supplier_%'
ORDER BY ordinal_position;
*/

-- 3. Test the view with sample data:
/*
SELECT 
    payment_id,
    workflow_status,
    payment_status,
    supplier_name,
    payment_amount
FROM supplier_payments_view 
LIMIT 5;
*/