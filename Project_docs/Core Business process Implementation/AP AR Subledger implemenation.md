AP/AR Subledger Implementation Summary
Overview
This document summarizes the implementation of Accounts Payable (AP) and Accounts Receivable (AR) subledgers for the Skinspire Clinic Hospital Management System. The subledgers provide detailed tracking of receivables and payables while integrating with the existing General Ledger (GL), invoice, and payment systems.
Architecture Highlights
1. Design Principles

Branch-aware accounting structure
Support for advance payments and adjustments
Seamless integration with existing GL system
Backward compatibility with current billing system
Business logic maintained in Python layer
Adheres to project development guidelines

2. Database Schema
AR Subledger Table
sqlCREATE TABLE ar_subledger (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_type VARCHAR(20) NOT NULL,
    reference_id UUID NOT NULL,
    reference_type VARCHAR(20) NOT NULL,
    reference_number VARCHAR(50),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    debit_amount NUMERIC(12, 2) DEFAULT 0,
    credit_amount NUMERIC(12, 2) DEFAULT 0,
    current_balance NUMERIC(12, 2),
    gl_transaction_id UUID REFERENCES gl_transaction(transaction_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(15),
    updated_by VARCHAR(15)
);
AP Subledger Table
sqlCREATE TABLE ap_subledger (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_type VARCHAR(20) NOT NULL,
    reference_id UUID NOT NULL,
    reference_type VARCHAR(20) NOT NULL,
    reference_number VARCHAR(50),
    supplier_id UUID NOT NULL REFERENCES suppliers(supplier_id),
    debit_amount NUMERIC(12, 2) DEFAULT 0,
    credit_amount NUMERIC(12, 2) DEFAULT 0,
    current_balance NUMERIC(12, 2),
    gl_transaction_id UUID REFERENCES gl_transaction(transaction_id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(15),
    updated_by VARCHAR(15)
);
3. Service Layer Components
Core Service Functions (subledger_service.py)

Balance Calculation Functions

get_patient_ar_balance() - Calculate AR balance for a patient (branch-aware)
get_supplier_ap_balance() - Calculate AP balance for a supplier (branch-aware)


Entry Creation Functions

create_ar_subledger_entry() - Create AR subledger entries
create_ap_subledger_entry() - Create AP subledger entries
create_advance_payment_ar_entry() - Handle advance payment entries
create_advance_adjustment_ar_entries() - Handle advance payment adjustments


Reporting Functions

get_ar_aging_by_branch() - Generate AR aging report by branch
get_ap_aging_by_branch() - Generate AP aging report by branch
get_patient_advance_balances() - Get patients with advance balances



4. Integration Points
Invoice Creation (billing_service.py)

Modified _create_invoice() to create AR subledger entries
Supports both GST and non-GST invoices
Handles branch assignment automatically

Payment Recording (billing_service.py)

Modified _record_payment() to create AR subledger entries
Supports payment distribution across multiple invoices
Handles excess payments and advances

Advance Payments (billing_service.py)

Modified _create_advance_payment() to create AR entries
Tracks advance balance by patient and branch
Supports advance payment adjustments against invoices

Void Invoice

Modified _void_invoice() to reverse AR entries
Maintains audit trail of voided transactions

Transaction Flow
1. Invoice Creation Flow
1. Invoice created → AR Debit (increases receivables)
2. GL entry created → Link to AR entry
3. Patient balance updated → Running balance maintained
2. Payment Recording Flow
1. Payment received → AR Credit (reduces receivables)
2. GL entry created → Link to AR entry
3. Patient balance updated → Running balance maintained
4. Excess payment → Convert to advance (credit balance)
3. Advance Payment Flow
1. Advance received → AR Credit (negative balance)
2. GL entry created → Link to AR entry
3. When applied to invoice:
   - AR Debit (reduce advance)
   - AR Credit (reduce invoice balance)
Key Features
1. Branch-Specific Accounting

All entries include branch_id
Balance calculations can be filtered by branch
Reporting supports branch-level analysis

2. Advance Payment Management

Tracks patient advances as credit balances
Supports application of advances to invoices
Maintains proper double-entry accounting

3. Running Balance Maintenance

Each entry stores current balance
Efficient balance queries without recalculation
Historical balance tracking

4. Integration with GL

All subledger entries linked to GL transactions
Maintains referential integrity
Supports reconciliation

Implementation Approach
Phase 1: Core Infrastructure

Database table creation
Basic service functions
Balance calculation utilities

Phase 2: Integration with Existing Systems

Modified invoice creation process
Updated payment recording
Enhanced advance payment handling

Error Handling

Non-blocking subledger operations
Comprehensive logging
Graceful fallbacks for backward compatibility

Best Practices Followed

Minimal Invasive Integration

Subledger operations added after primary transactions
Failures don't block core functionality
Existing code structure preserved


Database Design

Proper foreign key constraints
Indexed columns for performance
Automatic timestamp updates


Code Organization

Centralized service layer (subledger_service.py)
Clear separation of concerns
Consistent error handling patterns



Future Enhancements

Reporting Capabilities

Customer statements
Supplier statements
Detailed aging analysis


Reconciliation Features

GL to subledger reconciliation
Automated balance verification
Exception reporting


Performance Optimization

Batch processing for historical data
Cached balance calculations
Asynchronous entry creation



Migration Support
A utility function create_subledger_entries_for_existing_transactions() is provided to:

Process historical invoices and payments
Create subledger entries for existing data
Maintain chronological order

This implementation provides a robust foundation for detailed receivables and payables tracking while maintaining the flexibility and extensibility required for future enhancements.