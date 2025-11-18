-- Fix Payment Status Sync for Supplier Invoices
-- This script updates payment_status based on actual paid_amount and balance_amount

-- Update payment_status based on calculated values
UPDATE supplier_invoice si
SET
    payment_status = CASE
        WHEN v.balance_amount <= 0 AND v.paid_amount > 0 THEN 'paid'
        WHEN v.paid_amount > 0 AND v.balance_amount > 0 THEN 'partial'
        WHEN v.paid_amount = 0 AND si.due_date IS NOT NULL AND si.due_date < CURRENT_DATE THEN 'overdue'
        WHEN v.paid_amount = 0 THEN 'unpaid'
        ELSE si.payment_status  -- Keep current status for edge cases
    END,
    updated_at = CURRENT_TIMESTAMP
FROM supplier_invoices_view v
WHERE si.invoice_id = v.invoice_id
    AND si.payment_status != 'cancelled'  -- Don't update cancelled invoices
    AND si.is_deleted = false
    -- Only update where there's a mismatch
    AND si.payment_status != CASE
        WHEN v.balance_amount <= 0 AND v.paid_amount > 0 THEN 'paid'
        WHEN v.paid_amount > 0 AND v.balance_amount > 0 THEN 'partial'
        WHEN v.paid_amount = 0 AND si.due_date IS NOT NULL AND si.due_date < CURRENT_DATE THEN 'overdue'
        WHEN v.paid_amount = 0 THEN 'unpaid'
        ELSE si.payment_status
    END;

-- Report the changes
SELECT
    'Fixed Payment Status' as action,
    COUNT(*) as affected_rows
FROM supplier_invoice si
JOIN supplier_invoices_view v ON si.invoice_id = v.invoice_id
WHERE si.is_deleted = false
    AND si.payment_status != 'cancelled'
    AND (
        (v.balance_amount <= 0 AND v.paid_amount > 0 AND si.payment_status != 'paid') OR
        (v.paid_amount > 0 AND v.balance_amount > 0 AND si.payment_status != 'partial') OR
        (v.paid_amount = 0 AND si.payment_status NOT IN ('unpaid', 'overdue'))
    );

-- Show the current distribution after fix
SELECT
    payment_status,
    COUNT(*) as count,
    SUM(total_amount) as total_value
FROM supplier_invoice
WHERE is_deleted = false
GROUP BY payment_status
ORDER BY payment_status;
