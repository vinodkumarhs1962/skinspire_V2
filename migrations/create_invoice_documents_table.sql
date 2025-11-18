-- Migration: Create invoice_documents table for PDF storage
-- Purpose: Store generated invoice PDFs for audit compliance and record-keeping
-- Date: 2025-11-08
-- Author: Claude Code

CREATE TABLE IF NOT EXISTS invoice_documents (
    -- Primary Keys & Relationships
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),
    invoice_id UUID NOT NULL REFERENCES invoice_header(invoice_id),

    -- Document Classification
    document_type VARCHAR(50) NOT NULL DEFAULT 'invoice_pdf',  -- invoice_pdf, revised_invoice, credit_note
    document_category VARCHAR(30) DEFAULT 'billing',  -- billing, audit, compliance
    document_status VARCHAR(20) DEFAULT 'generated',  -- generated, archived, superseded

    -- File Information
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,  -- UUID-based secure filename
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,  -- Size in bytes
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    file_extension VARCHAR(10) DEFAULT 'pdf',

    -- Version Control (for revised invoices)
    is_original BOOLEAN DEFAULT TRUE,
    parent_document_id UUID REFERENCES invoice_documents(document_id),
    version_number INTEGER DEFAULT 1,

    -- Snapshot Metadata (what was printed at the time)
    hospital_had_drug_license BOOLEAN,  -- Snapshot of hospital drug license status
    prescription_items_count INTEGER DEFAULT 0,  -- Count of prescription items
    consolidated_prescription BOOLEAN DEFAULT FALSE,  -- Whether prescription was consolidated in this print

    -- Business Metadata
    description TEXT,
    generation_trigger VARCHAR(50),  -- on_creation, manual_regenerate, revision
    tags JSONB DEFAULT '[]',

    -- Access Tracking
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    last_accessed_by VARCHAR(15) REFERENCES users(user_id),
    access_count INTEGER DEFAULT 0,

    -- Timestamps (following TimestampMixin pattern)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_by VARCHAR(15),

    -- Indexes
    CONSTRAINT fk_invoice_documents_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id),
    CONSTRAINT fk_invoice_documents_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    CONSTRAINT fk_invoice_documents_invoice FOREIGN KEY (invoice_id) REFERENCES invoice_header(invoice_id),
    CONSTRAINT fk_invoice_documents_parent FOREIGN KEY (parent_document_id) REFERENCES invoice_documents(document_id)
);

-- Indexes for performance
CREATE INDEX idx_invoice_documents_invoice ON invoice_documents(invoice_id);
CREATE INDEX idx_invoice_documents_hospital ON invoice_documents(hospital_id);
CREATE INDEX idx_invoice_documents_created_at ON invoice_documents(created_at DESC);
CREATE INDEX idx_invoice_documents_type_status ON invoice_documents(document_type, document_status);
CREATE INDEX idx_invoice_documents_original ON invoice_documents(is_original) WHERE is_original = TRUE;

-- Comments for documentation
COMMENT ON TABLE invoice_documents IS 'Stores generated invoice PDFs and documents for audit compliance and historical record-keeping';
COMMENT ON COLUMN invoice_documents.hospital_had_drug_license IS 'Snapshot of whether hospital had valid pharmacy registration at document generation time';
COMMENT ON COLUMN invoice_documents.prescription_items_count IS 'Number of prescription items in the invoice (helps audit which invoices had prescriptions)';
COMMENT ON COLUMN invoice_documents.consolidated_prescription IS 'Whether prescription items were consolidated as "Doctor''s Examination and Treatment" in this print';
COMMENT ON COLUMN invoice_documents.generation_trigger IS 'What triggered this document generation: on_creation (auto), manual_regenerate, revision';

-- Trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_invoice_documents_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_invoice_documents_timestamp
BEFORE UPDATE ON invoice_documents
FOR EACH ROW
EXECUTE FUNCTION update_invoice_documents_timestamp();
