# Final Implementation Plan - Supplier Payment System Phase 1

## Implementation Sequence Overview

```
1. Database Changes (30 min)
2. Model Updates (45 min)
3. Service Layer Enhancements (2-3 hours)
4. Controller Updates (1-2 hours)
5. Template Updates (2-3 hours)
6. Configuration & Testing (1 hour)
```

---

## **STEP 1: Database Migration Scripts**

### **File: `migrations/001_supplier_payment_enhancements.sql`**

```sql
-- =====================================================================
-- SAFE POSTGRESQL MIGRATIONS - Run Each Section Separately
-- Copy and paste each section individually into PostgreSQL console
-- =====================================================================

-- =====================================================================
-- STEP 0: RESET ANY ABORTED TRANSACTION (Run this first if you got the error)
-- =====================================================================
ROLLBACK;

-- =====================================================================
-- STEP 1: CHECK CURRENT SCHEMA (Optional - to see what exists)
-- =====================================================================
-- Check if supplier_payment table exists and its current columns
\d supplier_payment;

-- Check if new tables exist (they shouldn't yet)
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('payment_documents', 'payment_document_access_log');

-- =====================================================================
-- STEP 2: ADD NEW COLUMNS TO SUPPLIER_PAYMENT (Run as single block)
-- =====================================================================
DO $$ 
BEGIN
    -- Add columns only if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'bank_account_name') THEN
        ALTER TABLE supplier_payment ADD COLUMN bank_account_name VARCHAR(100);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'approval_level') THEN
        ALTER TABLE supplier_payment ADD COLUMN approval_level VARCHAR(20) DEFAULT 'none';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'next_approver_id') THEN
        ALTER TABLE supplier_payment ADD COLUMN next_approver_id VARCHAR(15);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'total_documents_count') THEN
        ALTER TABLE supplier_payment ADD COLUMN total_documents_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'documents_verified_count') THEN
        ALTER TABLE supplier_payment ADD COLUMN documents_verified_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'upi_app_name') THEN
        ALTER TABLE supplier_payment ADD COLUMN upi_app_name VARCHAR(50);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'processing_fee') THEN
        ALTER TABLE supplier_payment ADD COLUMN processing_fee NUMERIC(12,2) DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'supplier_payment' AND column_name = 'processing_status') THEN
        ALTER TABLE supplier_payment ADD COLUMN processing_status VARCHAR(20) DEFAULT 'completed';
    END IF;
END $$;

-- =====================================================================
-- STEP 3: ADD FOREIGN KEY CONSTRAINT (Run separately)
-- =====================================================================
-- Add foreign key constraint for next_approver_id (only if users table exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE constraint_name LIKE '%next_approver_id%') THEN
            ALTER TABLE supplier_payment ADD CONSTRAINT fk_next_approver FOREIGN KEY (next_approver_id) REFERENCES users(user_id);
        END IF;
    END IF;
END $$;

-- =====================================================================
-- STEP 4: ADD CHECK CONSTRAINTS (Run each constraint separately)
-- =====================================================================
-- Approval level constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_approval_level') THEN
        ALTER TABLE supplier_payment ADD CONSTRAINT chk_approval_level 
        CHECK (approval_level IN ('none', 'auto_approved', 'level_1', 'level_2'));
    END IF;
END $$;

-- Processing status constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_processing_status') THEN
        ALTER TABLE supplier_payment ADD CONSTRAINT chk_processing_status 
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));
    END IF;
END $$;

-- Documents count constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_documents_count') THEN
        ALTER TABLE supplier_payment ADD CONSTRAINT chk_documents_count 
        CHECK (documents_verified_count <= total_documents_count);
    END IF;
END $$;

-- Processing fee constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_processing_fee') THEN
        ALTER TABLE supplier_payment ADD CONSTRAINT chk_processing_fee 
        CHECK (processing_fee >= 0);
    END IF;
END $$;

-- =====================================================================
-- STEP 5: UPDATE EXISTING DATA (Run separately)
-- =====================================================================
-- Update approval levels for existing payments
UPDATE supplier_payment 
SET approval_level = CASE 
    WHEN amount <= 5000 AND cash_amount = amount THEN 'auto_approved'
    WHEN amount <= 50000 THEN 'level_1'
    ELSE 'level_2'
END
WHERE approval_level IS NULL OR approval_level = 'none';

-- Update processing status for existing payments
UPDATE supplier_payment 
SET processing_status = 'completed'
WHERE processing_status IS NULL;

-- =====================================================================
-- STEP 6: CREATE PAYMENT_DOCUMENTS TABLE (Run as single block)
-- =====================================================================
CREATE TABLE IF NOT EXISTS payment_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL,
    branch_id UUID,
    payment_id UUID NOT NULL,
    
    -- Document classification
    document_type VARCHAR(50) NOT NULL,
    document_category VARCHAR(30) DEFAULT 'payment',
    document_status VARCHAR(20) DEFAULT 'uploaded',
    
    -- File information
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    file_extension VARCHAR(10),
    
    -- Version control
    is_original BOOLEAN DEFAULT TRUE,
    parent_document_id UUID,
    version_number INTEGER DEFAULT 1,
    
    -- Verification
    verified_by VARCHAR(15),
    verified_at TIMESTAMP WITH TIME ZONE,
    verification_status VARCHAR(20) DEFAULT 'pending',
    verification_notes TEXT,
    
    -- Metadata
    description TEXT,
    required_for_approval BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    
    -- Access tracking
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    last_accessed_by VARCHAR(15),
    access_count INTEGER DEFAULT 0,
    
    -- Standard fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(15),
    updated_by VARCHAR(15),
    deleted_flag BOOLEAN DEFAULT FALSE
);

-- =====================================================================
-- STEP 7: ADD FOREIGN KEY CONSTRAINTS TO PAYMENT_DOCUMENTS (Run each separately)
-- =====================================================================
-- Add foreign key constraints if referenced tables exist
DO $$ 
BEGIN
    -- Hospital foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'hospitals') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'hospital_id') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id);
        END IF;
    END IF;
    
    -- Branch foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'branches') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'branch_id') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id);
        END IF;
    END IF;
    
    -- Payment foreign key
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'supplier_payment') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'payment_id') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_payment FOREIGN KEY (payment_id) REFERENCES supplier_payment(payment_id) ON DELETE CASCADE;
        END IF;
    END IF;
    
    -- User foreign keys
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'verified_by') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_verified_by FOREIGN KEY (verified_by) REFERENCES users(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'last_accessed_by') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_accessed_by FOREIGN KEY (last_accessed_by) REFERENCES users(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'created_by') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_created_by FOREIGN KEY (created_by) REFERENCES users(user_id);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'updated_by') THEN
            ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_updated_by FOREIGN KEY (updated_by) REFERENCES users(user_id);
        END IF;
    END IF;
    
    -- Self-referential foreign key for parent document
    IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_documents' AND column_name = 'parent_document_id') THEN
        ALTER TABLE payment_documents ADD CONSTRAINT fk_pd_parent FOREIGN KEY (parent_document_id) REFERENCES payment_documents(document_id);
    END IF;
END $$;

-- =====================================================================
-- STEP 8: ADD CHECK CONSTRAINTS TO PAYMENT_DOCUMENTS (Run each separately)
-- =====================================================================
-- File size constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_doc_file_size') THEN
        ALTER TABLE payment_documents ADD CONSTRAINT chk_doc_file_size 
        CHECK (file_size > 0 AND file_size <= 52428800);
    END IF;
END $$;

-- Version number constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_doc_version_number') THEN
        ALTER TABLE payment_documents ADD CONSTRAINT chk_doc_version_number 
        CHECK (version_number > 0);
    END IF;
END $$;

-- Access count constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = 'chk_doc_access_count') THEN
        ALTER TABLE payment_documents ADD CONSTRAINT chk_doc_access_count 
        CHECK (access_count >= 0);
    END IF;
END $$;

-- =====================================================================
-- STEP 9: CREATE PAYMENT_DOCUMENT_ACCESS_LOG TABLE (Run as single block)
-- =====================================================================
CREATE TABLE IF NOT EXISTS payment_document_access_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    user_id VARCHAR(15) NOT NULL,
    access_type VARCHAR(20) NOT NULL,
    access_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    session_id VARCHAR(100)
);

-- =====================================================================
-- STEP 10: ADD FOREIGN KEYS TO ACCESS LOG TABLE (Run each separately)
-- =====================================================================
-- Document foreign key
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_document_access_log' AND column_name = 'document_id') THEN
        ALTER TABLE payment_document_access_log ADD CONSTRAINT fk_pdal_document 
        FOREIGN KEY (document_id) REFERENCES payment_documents(document_id) ON DELETE CASCADE;
    END IF;
END $$;

-- User foreign key
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name = 'payment_document_access_log' AND column_name = 'user_id') THEN
            ALTER TABLE payment_document_access_log ADD CONSTRAINT fk_pdal_user 
            FOREIGN KEY (user_id) REFERENCES users(user_id);
        END IF;
    END IF;
END $$;

-- =====================================================================
-- STEP 11: CREATE INDEXES (Run each separately - no CONCURRENTLY needed)
-- =====================================================================
-- Supplier payment indexes
CREATE INDEX IF NOT EXISTS idx_supplier_payment_approval_level 
ON supplier_payment(approval_level);

CREATE INDEX IF NOT EXISTS idx_supplier_payment_processing_status 
ON supplier_payment(processing_status);

CREATE INDEX IF NOT EXISTS idx_supplier_payment_document_counts 
ON supplier_payment(total_documents_count, documents_verified_count);

-- Payment documents indexes
CREATE INDEX IF NOT EXISTS idx_payment_documents_payment_id 
ON payment_documents(payment_id);

CREATE INDEX IF NOT EXISTS idx_payment_documents_hospital_branch 
ON payment_documents(hospital_id, branch_id);

CREATE INDEX IF NOT EXISTS idx_payment_documents_type_status 
ON payment_documents(document_type, document_status);

CREATE INDEX IF NOT EXISTS idx_payment_documents_created_at 
ON payment_documents(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_documents_verification_status 
ON payment_documents(verification_status) WHERE verification_status != 'verified';

-- Access log indexes
CREATE INDEX IF NOT EXISTS idx_payment_document_access_log_document_id 
ON payment_document_access_log(document_id, access_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_payment_document_access_log_user_timestamp 
ON payment_document_access_log(user_id, access_timestamp DESC);

-- JSONB index for tags
CREATE INDEX IF NOT EXISTS idx_payment_documents_tags 
ON payment_documents USING GIN(tags);

-- =====================================================================
-- STEP 12: CREATE FUNCTIONS AND TRIGGERS (Run each separately)
-- =====================================================================
-- Update timestamp function
CREATE OR REPLACE FUNCTION update_payment_document_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_payment_document_updated_at ON payment_documents;
CREATE TRIGGER trg_payment_document_updated_at
    BEFORE UPDATE ON payment_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_document_timestamp();

-- =====================================================================
-- STEP 13: CREATE VIEWS (Run separately)
-- =====================================================================
CREATE OR REPLACE VIEW payment_document_summary AS
SELECT 
    p.payment_id,
    p.hospital_id,
    p.branch_id,
    COUNT(d.document_id) as total_documents,
    COUNT(CASE WHEN d.verification_status = 'verified' THEN 1 END) as verified_documents,
    COUNT(CASE WHEN d.verification_status = 'pending' THEN 1 END) as pending_documents,
    COUNT(CASE WHEN d.required_for_approval = TRUE THEN 1 END) as required_documents,
    MAX(d.created_at) as latest_document_date
FROM supplier_payment p
LEFT JOIN payment_documents d ON p.payment_id = d.payment_id AND d.deleted_flag = FALSE
GROUP BY p.payment_id, p.hospital_id, p.branch_id;

-- =====================================================================
-- STEP 14: VERIFICATION QUERIES (Run to check everything worked)
-- =====================================================================
-- Check new columns in supplier_payment
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'supplier_payment' 
  AND column_name IN (
    'bank_account_name', 'approval_level', 'next_approver_id',
    'total_documents_count', 'documents_verified_count', 'upi_app_name',
    'processing_fee', 'processing_status'
);

-- Check new tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('payment_documents', 'payment_document_access_log');

-- Check constraints exist
SELECT constraint_name, table_name 
FROM information_schema.table_constraints 
WHERE table_name IN ('supplier_payment', 'payment_documents')
  AND constraint_type = 'CHECK';

-- Check indexes exist
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('supplier_payment', 'payment_documents', 'payment_document_access_log')
  AND indexname LIKE 'idx_%';

-- Check view exists
SELECT table_name FROM information_schema.views WHERE table_name = 'payment_document_summary';

-- Test data count
SELECT COUNT(*) as total_payments FROM supplier_payment;
SELECT COUNT(*) as total_documents FROM payment_documents;

-- =====================================================================
-- SUCCESS MESSAGE
-- =====================================================================
SELECT 'MIGRATION COMPLETED SUCCESSFULLY! All tables, indexes, and constraints have been created.' as status;

---

## **STEP 2: Model Updates**

### **File: `app/models/transaction.py` - Add to existing file**

```python
# ADD these fields to existing SupplierPayment class
# Insert after existing fields, before relationships

# Enhanced fields for Phase 1
bank_account_name = Column(String(100))
approval_level = Column(String(20), default='none')
next_approver_id = Column(String(15), ForeignKey('users.user_id'))
total_documents_count = Column(Integer, default=0)
documents_verified_count = Column(Integer, default=0)
upi_app_name = Column(String(50))
processing_fee = Column(Numeric(12, 2), default=0)
processing_status = Column(String(20), default='completed')

# ADD new relationship to SupplierPayment class
documents = relationship("PaymentDocument", back_populates="payment", cascade="all, delete-orphan")
next_approver = relationship("User", foreign_keys=[next_approver_id])

# ADD these methods to SupplierPayment class
@property
def document_summary(self):
    """Get summary of attached documents"""
    if not self.documents:
        return {'total': 0, 'verified': 0, 'pending': 0, 'completion_percentage': 0}
    
    total = len(self.documents)
    verified = len([doc for doc in self.documents if doc.verification_status == 'verified'])
    pending = len([doc for doc in self.documents if doc.verification_status == 'pending'])
    
    return {
        'total': total,
        'verified': verified,
        'pending': pending,
        'completion_percentage': (verified / total * 100) if total > 0 else 0
    }

@property
def has_required_documents(self):
    """Check if all required documents are present and verified"""
    required_docs = [doc for doc in self.documents if doc.required_for_approval]
    if not required_docs:
        return True
    
    verified_required = [doc for doc in required_docs if doc.verification_status == 'verified']
    return len(verified_required) == len(required_docs)

def validate_multi_method_amounts(self):
    """Validate that sum of method amounts equals total amount"""
    method_total = (
        (self.cash_amount or 0) + 
        (self.cheque_amount or 0) + 
        (self.bank_transfer_amount or 0) + 
        (self.upi_amount or 0)
    )
    return abs(float(self.amount) - float(method_total)) <= 0.01
```

### **File: `app/models/transaction.py` - Add new PaymentDocument class**

```python
# ADD this new class to transaction.py

class PaymentDocument(Base, TimestampMixin, TenantMixin):
    """Document management for supplier payments"""
    __tablename__ = 'payment_documents'
    
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('supplier_payment.payment_id'), nullable=False)
    
    # Document classification
    document_type = Column(String(50), nullable=False)
    document_category = Column(String(30), default='payment')
    document_status = Column(String(20), default='uploaded')
    
    # File information
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    file_extension = Column(String(10))
    
    # Version control
    is_original = Column(Boolean, default=True)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey('payment_documents.document_id'))
    version_number = Column(Integer, default=1)
    
    # Verification
    verified_by = Column(String(15), ForeignKey('users.user_id'))
    verified_at = Column(DateTime(timezone=True))
    verification_status = Column(String(20), default='pending')
    verification_notes = Column(Text)
    
    # Metadata
    description = Column(Text)
    required_for_approval = Column(Boolean, default=False)
    tags = Column(JSONB, default=list)
    
    # Access tracking
    last_accessed_at = Column(DateTime(timezone=True))
    last_accessed_by = Column(String(15), ForeignKey('users.user_id'))
    access_count = Column(Integer, default=0)
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    payment = relationship("SupplierPayment", back_populates="documents")
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    last_accessed_by_user = relationship("User", foreign_keys=[last_accessed_by])
    
    # Methods
    def record_access(self, user_id: str):
        """Record document access"""
        self.last_accessed_at = datetime.now(timezone.utc)
        self.last_accessed_by = user_id
        self.access_count = (self.access_count or 0) + 1
    
    def verify_document(self, verifier_id: str, status: str, notes: str = None):
        """Mark document as verified"""
        self.verification_status = status
        self.verified_by = verifier_id
        self.verified_at = datetime.now(timezone.utc)
        if notes:
            self.verification_notes = notes
    
    def __repr__(self):
        return f"<PaymentDocument {self.document_id} - {self.document_type}>"


class PaymentDocumentAccessLog(Base, TimestampMixin):
    """Access log for payment documents"""
    __tablename__ = 'payment_document_access_log'
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey('payment_documents.document_id'), nullable=False)
    user_id = Column(String(15), ForeignKey('users.user_id'), nullable=False)
    access_type = Column(String(20), nullable=False)
    access_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String(45))
    session_id = Column(String(100))
    
    # Relationships
    document = relationship("PaymentDocument")
    user = relationship("User")
```

---

## **STEP 3: Service Layer Enhancements**

### **File: `app/services/supplier_service.py` - Replace existing functions**

```python
# REPLACE existing validate_payment_data function with this enhanced version

def validate_payment_data(payment_data: Dict, hospital_id: uuid.UUID, current_user_id: Optional[str] = None) -> Dict:
    """Enhanced payment validation with multi-method and approval support"""
    errors = []
    warnings = []
    
    try:
        # Basic validation
        if not payment_data.get('supplier_id'):
            errors.append("Supplier ID is required")
        
        if not payment_data.get('amount') or float(payment_data.get('amount', 0)) <= 0:
            errors.append("Payment amount must be greater than zero")
        
        # Multi-method validation
        method_amounts = {
            'cash_amount': float(payment_data.get('cash_amount', 0)),
            'cheque_amount': float(payment_data.get('cheque_amount', 0)),
            'bank_transfer_amount': float(payment_data.get('bank_transfer_amount', 0)),
            'upi_amount': float(payment_data.get('upi_amount', 0))
        }
        
        total_method_amount = sum(method_amounts.values())
        declared_total = float(payment_data.get('amount', 0))
        
        if total_method_amount > 0 and abs(total_method_amount - declared_total) > 0.01:
            errors.append(f"Total amount ({declared_total}) doesn't match sum of payment methods ({total_method_amount})")
        
        # Branch validation
        branch_id = payment_data.get('branch_id')
        if not branch_id:
            errors.append("Branch ID is required for payment")
        elif current_user_id:
            try:
                if not validate_branch_access(current_user_id, hospital_id, branch_id):
                    errors.append("User does not have access to specified branch")
            except Exception as e:
                logger.warning(f"Branch validation failed: {str(e)}")
        
        # Supplier validation
        if payment_data.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=uuid.UUID(payment_data['supplier_id']),
                    hospital_id=hospital_id,
                    current_user_id=current_user_id
                )
                if supplier.get('black_listed'):
                    errors.append("Cannot make payment to blacklisted supplier")
                if supplier.get('status') != 'active':
                    warnings.append("Supplier is not in active status")
            except Exception as e:
                errors.append(f"Supplier validation failed: {str(e)}")
        
        # Approval requirement determination
        requires_approval = _determine_approval_requirement(payment_data, current_user_id)
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'requires_approval': requires_approval,
            'method_amounts': method_amounts
        }
        
    except Exception as e:
        logger.error(f"Error in payment validation: {str(e)}", exc_info=True)
        return {
            'is_valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'warnings': [],
            'requires_approval': True
        }

def _determine_approval_requirement(payment_data: Dict, current_user_id: Optional[str] = None) -> bool:
    """Determine if payment requires approval"""
    try:
        amount = float(payment_data.get('amount', 0))
        
        if amount >= 50000.00:
            return True
        
        if current_user_id:
            try:
                from app.services.permission_service import has_permission
                user_obj = {'user_id': current_user_id}
                if has_permission(user_obj, 'payment', 'approve'):
                    return amount >= 200000.00
            except Exception as e:
                logger.warning(f"Role check failed: {str(e)}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error determining approval requirement: {str(e)}")
        return True

# REPLACE existing _record_supplier_payment function with this enhanced version

def _record_supplier_payment(
    session: Session,
    hospital_id: uuid.UUID,
    payment_data: Dict,
    create_gl_entries: bool = True,
    current_user_id: Optional[str] = None
) -> Dict:
    """Enhanced payment recording with multi-method support"""
    try:
        # Enhanced validation
        validation_result = validate_payment_data(payment_data, hospital_id, current_user_id)
        if not validation_result['is_valid']:
            raise ValueError(f"Payment validation failed: {'; '.join(validation_result['errors'])}")
        
        # Existing supplier validation (keep as-is)
        supplier_id = payment_data.get('supplier_id')
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        
        if supplier.black_listed:
            raise ValueError(f"Supplier '{supplier.supplier_name}' is blacklisted")
        
        # Enhanced payment record creation
        payment = SupplierPayment(
            hospital_id=hospital_id,
            branch_id=uuid.UUID(payment_data['branch_id']),
            supplier_id=supplier_id,
            invoice_id=uuid.UUID(payment_data['invoice_id']) if payment_data.get('invoice_id') else None,
            
            # Basic fields
            payment_date=payment_data.get('payment_date', datetime.now(timezone.utc)),
            payment_method=payment_data.get('payment_method', 'mixed'),
            amount=Decimal(str(payment_data.get('amount', 0))),
            reference_no=payment_data.get('reference_no'),
            notes=payment_data.get('notes'),
            
            # Enhanced multi-method fields
            cash_amount=Decimal(str(payment_data.get('cash_amount', 0))),
            cheque_amount=Decimal(str(payment_data.get('cheque_amount', 0))),
            bank_transfer_amount=Decimal(str(payment_data.get('bank_transfer_amount', 0))),
            upi_amount=Decimal(str(payment_data.get('upi_amount', 0))),
            
            # Method-specific details
            cheque_number=payment_data.get('cheque_number'),
            cheque_date=payment_data.get('cheque_date'),
            cheque_bank=payment_data.get('cheque_bank'),
            bank_account_name=payment_data.get('bank_account_name'),
            bank_reference_number=payment_data.get('bank_reference_number'),
            upi_transaction_id=payment_data.get('upi_transaction_id'),
            upi_app_name=payment_data.get('upi_app_name'),
            
            # Workflow fields
            workflow_status='draft' if validation_result['requires_approval'] else 'approved',
            requires_approval=validation_result['requires_approval'],
            approval_level=_get_approval_level(float(payment_data.get('amount', 0))),
            
            status='completed',
            reconciliation_status='pending'
        )
        
        if current_user_id:
            payment.created_by = current_user_id
            if not validation_result['requires_approval']:
                payment.approved_by = current_user_id
                payment.approved_at = datetime.now(timezone.utc)
        
        session.add(payment)
        session.flush()
        
        # Handle document uploads
        if payment_data.get('documents'):
            try:
                _process_payment_documents(payment.payment_id, payment_data['documents'], current_user_id, session)
            except Exception as e:
                logger.warning(f"Document processing failed: {str(e)}")
        
        # Create GL entries (only if approved)
        if create_gl_entries and not validation_result['requires_approval']:
            try:
                gl_result = create_supplier_payment_gl_entries(
                    payment.payment_id, current_user_id, session
                )
                logger.info("GL entries created successfully")
            except Exception as e:
                logger.error(f"Error creating GL entries: {str(e)}")
                if not payment_data.get('skip_gl_error', False):
                    raise
        
        # Return enhanced result
        result = get_entity_dict(payment)
        result['supplier_name'] = supplier.supplier_name
        result['validation_warnings'] = validation_result.get('warnings', [])
        result['requires_approval'] = validation_result['requires_approval']
        
        return result
        
    except Exception as e:
        logger.error(f"Error recording supplier payment: {str(e)}", exc_info=True)
        session.rollback()
        raise

def _get_approval_level(amount: float) -> str:
    """Get approval level based on amount"""
    if amount <= 5000:
        return 'auto_approved'
    elif amount <= 50000:
        return 'level_1'
    else:
        return 'level_2'

def _process_payment_documents(
    payment_id: uuid.UUID,
    documents: List[Dict],
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> None:
    """Process document uploads for payment"""
    try:
        import os
        from werkzeug.utils import secure_filename
        from flask import current_app
        
        base_path = current_app.config.get('PAYMENT_DOCUMENT_PATH', '/tmp/payment_documents')
        
        for doc_data in documents:
            if 'file' not in doc_data:
                continue
                
            file = doc_data['file']
            document_type = doc_data.get('document_type', 'receipt')
            
            # Validate and save file
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            if file_extension not in {'pdf', 'jpg', 'jpeg', 'png'}:
                raise ValueError(f"File type .{file_extension} not allowed")
            
            # Create storage structure
            payment_folder = os.path.join(base_path, str(payment_id))
            os.makedirs(payment_folder, exist_ok=True)
            
            unique_filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
            file_path = os.path.join(payment_folder, unique_filename)
            
            file.save(file_path)
            
            # Create document record
            from app.models.transaction import PaymentDocument
            document = PaymentDocument(
                payment_id=payment_id,
                document_type=document_type,
                original_filename=filename,
                stored_filename=unique_filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                mime_type=file.mimetype,
                file_extension=file_extension,
                description=doc_data.get('description', ''),
                required_for_approval=doc_data.get('required_for_approval', False),
                created_by=current_user_id
            )
            
            session.add(document)
            
            # Update payment document count
            session.query(SupplierPayment).filter_by(payment_id=payment_id).update({
                'total_documents_count': SupplierPayment.total_documents_count + 1
            })
        
    except Exception as e:
        logger.error(f"Error processing payment documents: {str(e)}")
        raise

# ADD new function for payment approval

def approve_supplier_payment(
    payment_id: uuid.UUID,
    hospital_id: uuid.UUID,
    current_user_id: str,
    approval_notes: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """Approve pending payment"""
    logger.info(f"Approving payment {payment_id}")
    
    if session is not None:
        return _approve_supplier_payment(session, payment_id, hospital_id, current_user_id, approval_notes)
    
    with get_db_session() as new_session:
        result = _approve_supplier_payment(new_session, payment_id, hospital_id, current_user_id, approval_notes)
        new_session.commit()
        return result

def _approve_supplier_payment(
    session: Session,
    payment_id: uuid.UUID,
    hospital_id: uuid.UUID,
    current_user_id: str,
    approval_notes: Optional[str] = None
) -> Dict:
    """Internal function for payment approval"""
    try:
        payment = session.query(SupplierPayment).filter_by(
            payment_id=payment_id,
            hospital_id=hospital_id
        ).first()
        
        if not payment:
            raise ValueError("Payment not found")
        
        if payment.workflow_status == 'approved':
            raise ValueError("Payment is already approved")
        
        # Validate approval permission
        if not _can_approve_payment(current_user_id, float(payment.amount)):
            raise ValueError("User does not have permission to approve this payment")
        
        # Update payment
        payment.workflow_status = 'approved'
        payment.approved_by = current_user_id
        payment.approved_at = datetime.now(timezone.utc)
        
        if approval_notes:
            payment.approval_notes = approval_notes
        
        session.flush()
        
        # Create GL entries
        try:
            gl_result = create_supplier_payment_gl_entries(payment_id, current_user_id, session)
            logger.info("GL entries created after approval")
        except Exception as e:
            logger.error(f"Error creating GL entries after approval: {str(e)}")
        
        return get_entity_dict(payment)
        
    except Exception as e:
        logger.error(f"Error approving payment: {str(e)}")
        session.rollback()
        raise

def _can_approve_payment(user_id: str, amount: float) -> bool:
    """Check approval permissions"""
    try:
        from app.services.permission_service import has_permission
        
        user_obj = {'user_id': user_id}
        
        if not has_permission(user_obj, 'payment', 'approve'):
            return False
        
        if amount >= 200000.00:
            return has_permission(user_obj, 'payment', 'approve_high_value')
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking approval permission: {str(e)}")
        return False
```

---

## **STEP 4: Configuration Updates**

### **File: `config.py` - Add payment configuration**

```python
# ADD to existing config.py

# Payment System Configuration
PAYMENT_CONFIG = {
    'APPROVAL_THRESHOLD_LEVEL_1': 50000.00,
    'APPROVAL_THRESHOLD_LEVEL_2': 200000.00,
    'AUTO_APPROVE_LIMIT': 5000.00,
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_FILE_TYPES': ['pdf', 'jpg', 'jpeg', 'png'],
    'DOCUMENT_STORAGE_PATH': '/secure_storage/payment_documents',
    'REQUIRE_DOCUMENTS_ABOVE': 10000.00
}

# File Upload Settings
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max request size
UPLOAD_FOLDER = PAYMENT_CONFIG['DOCUMENT_STORAGE_PATH']
```

---

## **STEP 5: Form Enhancements**

### **File: `app/forms/supplier_forms.py` - Enhance existing SupplierPaymentForm**

```python
# REPLACE existing SupplierPaymentForm with this enhanced version

class SupplierPaymentForm(FlaskForm):
    # Basic payment fields
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    invoice_id = SelectField('Invoice', choices=[('', 'Select Invoice')], required=False)
    amount = DecimalField('Total Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=datetime.now().date())
    
    # Multi-method payment amounts
    cash_amount = DecimalField('Cash Amount', validators=[Optional(), NumberRange(min=0)], default=0)
    cheque_amount = DecimalField('Cheque Amount', validators=[Optional(), NumberRange(min=0)], default=0)
    bank_transfer_amount = DecimalField('Bank Transfer Amount', validators=[Optional(), NumberRange(min=0)], default=0)
    upi_amount = DecimalField('UPI Amount', validators=[Optional(), NumberRange(min=0)], default=0)
    
    # Method-specific details
    cheque_number = StringField('Cheque Number', validators=[Optional(), Length(max=20)])
    cheque_date = DateField('Cheque Date', validators=[Optional()])
    cheque_bank = StringField('Cheque Bank', validators=[Optional(), Length(max=100)])
    bank_account_name = StringField('Account Holder Name', validators=[Optional(), Length(max=100)])
    bank_reference_number = StringField('Bank Reference Number', validators=[Optional(), Length(max=50)])
    upi_transaction_id = StringField('UPI Transaction ID', validators=[Optional(), Length(max=50)])
    upi_app_name = SelectField('UPI App', choices=[
        ('', 'Select UPI App'),
        ('gpay', 'Google Pay'),
        ('phonepe', 'PhonePe'),
        ('paytm', 'Paytm'),
        ('bhim', 'BHIM'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    # Additional fields
    reference_no = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    
    # Document upload fields
    receipt_file = FileField('Receipt Document', validators=[Optional()])
    bank_statement_file = FileField('Bank Statement', validators=[Optional()])
    authorization_file = FileField('Authorization Document', validators=[Optional()])
    
    # Branch selection (populated dynamically)
    branch_id = SelectField('Branch', validators=[DataRequired()])
    
    submit = SubmitField('Record Payment')
    
    def validate(self, extra_validators=None):
        """Enhanced validation with business rules"""
        if not super().validate(extra_validators):
            return False
        
        # Multi-method amount validation
        method_total = (
            (self.cash_amount.data or 0) +
            (self.cheque_amount.data or 0) +
            (self.bank_transfer_amount.data or 0) +
            (self.upi_amount.data or 0)
        )
        
        if method_total > 0 and abs(float(self.amount.data) - float(method_total)) > 0.01:
            self.amount.errors.append(f'Total amount ({self.amount.data}) must equal sum of payment methods ({method_total})')
            return False
        
        # Cheque-specific validation
        if self.cheque_amount.data and self.cheque_amount.data > 0:
            if not self.cheque_number.data:
                self.cheque_number.errors.append('Cheque number is required when cheque amount is specified')
                return False
            if not self.cheque_date.data:
                self.cheque_date.errors.append('Cheque date is required when cheque amount is specified')
                return False
        
        # Bank transfer validation
        if self.bank_transfer_amount.data and self.bank_transfer_amount.data > 0:
            if not self.bank_reference_number.data:
                self.bank_reference_number.errors.append('Bank reference number is required for bank transfers')
                return False
        
        # UPI validation
        if self.upi_amount.data and self.upi_amount.data > 0:
            if not self.upi_transaction_id.data:
                self.upi_transaction_id.errors.append('UPI transaction ID is required for UPI payments')
                return False
        
        return True


# ADD new form for payment approval
class PaymentApprovalForm(FlaskForm):
    approval_action = SelectField('Action', choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ], validators=[DataRequired()])
    approval_notes = TextAreaField('Approval Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit Approval')


# ADD new form for document upload
class DocumentUploadForm(FlaskForm):
    document_type = SelectField('Document Type', choices=[
        ('receipt', 'Receipt'),
        ('bank_statement', 'Bank Statement'),
        ('authorization', 'Authorization Letter'),
        ('invoice_copy', 'Invoice Copy'),
        ('cheque_image', 'Cheque Image')
    ], validators=[DataRequired()])
    file = FileField('Select File', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    required_for_approval = BooleanField('Required for Approval')
    submit = SubmitField('Upload Document')
    
    def validate_file(self, field):
        """Validate file type and size"""
        if field.data:
            filename = field.data.filename
            if not filename:
                raise ValidationError('Please select a file')
            
            # Check file extension
            allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in allowed_extensions:
                raise ValidationError(f'File type .{file_ext} not allowed. Allowed types: {", ".join(allowed_extensions)}')
            
            # Check file size (this is a basic check, actual size checking happens in view)
            # field.data.seek(0, 2)  # Seek to end
            # size = field.data.tell()
            # field.data.seek(0)  # Reset to beginning
            # if size > 10 * 1024 * 1024:  # 10MB
            #     raise ValidationError('File size must be less than 10MB')
```

---

## **STEP 6: Controller Updates**

### **File: `app/controllers/supplier_controller.py` - Add payment controller**

```python
# ADD this new controller class to existing supplier_controller.py

class SupplierPaymentController(FormController):
    """Enhanced payment controller with multi-method and document support"""
    
    def __init__(self, payment_id=None):
        self.payment_id = payment_id
        super().__init__()
    
    def get_form(self):
        """Get payment form with dynamic choices"""
        from app.forms.supplier_forms import SupplierPaymentForm
        form = SupplierPaymentForm()
        
        # Populate supplier choices
        try:
            from app.services.supplier_service import search_suppliers
            supplier_result = search_suppliers(
                hospital_id=current_user.hospital_id,
                status='active',
                current_user_id=current_user.user_id,
                page=1,
                per_page=1000
            )
            suppliers = supplier_result.get('suppliers', [])
            form.supplier_id.choices = [('', 'Select Supplier')] + [
                (str(supplier['supplier_id']), supplier['supplier_name']) 
                for supplier in suppliers
            ]
        except Exception as e:
            current_app.logger.error(f"Error loading suppliers: {str(e)}")
            form.supplier_id.choices = [('', 'No suppliers available')]
        
        # Populate branch choices
        try:
            from app.services.permission_service import get_user_accessible_branches
            branches = get_user_accessible_branches(current_user.user_id, current_user.hospital_id)
            form.branch_id.choices = [
                (branch['branch_id'], branch['branch_name']) 
                for branch in branches
            ]
            
            # Set default branch if only one accessible
            if len(branches) == 1:
                form.branch_id.data = branches[0]['branch_id']
                
        except Exception as e:
            current_app.logger.error(f"Error loading branches: {str(e)}")
            form.branch_id.choices = [('', 'No branches available')]
        
        return form
    
    def handle_request(self):
        """Handle payment recording request"""
        form = self.get_form()
        
        if request.method == 'GET':
            return self.render_form(form)
        
        if form.validate_on_submit():
            try:
                # Prepare payment data
                payment_data = {
                    'supplier_id': form.supplier_id.data,
                    'invoice_id': form.invoice_id.data if form.invoice_id.data else None,
                    'amount': float(form.amount.data),
                    'payment_date': form.payment_date.data,
                    'branch_id': form.branch_id.data,
                    
                    # Multi-method amounts
                    'cash_amount': float(form.cash_amount.data or 0),
                    'cheque_amount': float(form.cheque_amount.data or 0),
                    'bank_transfer_amount': float(form.bank_transfer_amount.data or 0),
                    'upi_amount': float(form.upi_amount.data or 0),
                    
                    # Method-specific details
                    'cheque_number': form.cheque_number.data,
                    'cheque_date': form.cheque_date.data,
                    'cheque_bank': form.cheque_bank.data,
                    'bank_account_name': form.bank_account_name.data,
                    'bank_reference_number': form.bank_reference_number.data,
                    'upi_transaction_id': form.upi_transaction_id.data,
                    'upi_app_name': form.upi_app_name.data,
                    
                    # Additional fields
                    'reference_no': form.reference_no.data,
                    'notes': form.notes.data
                }
                
                # Handle document uploads
                documents = []
                for field_name, document_type in [
                    ('receipt_file', 'receipt'),
                    ('bank_statement_file', 'bank_statement'),
                    ('authorization_file', 'authorization')
                ]:
                    file_field = getattr(form, field_name)
                    if file_field.data:
                        documents.append({
                            'file': file_field.data,
                            'document_type': document_type,
                            'description': f'{document_type.replace("_", " ").title()} for payment'
                        })
                
                if documents:
                    payment_data['documents'] = documents
                
                # Record payment
                from app.services.supplier_service import record_supplier_payment
                result = record_supplier_payment(
                    hospital_id=current_user.hospital_id,
                    payment_data=payment_data,
                    current_user_id=current_user.user_id
                )
                
                # Success handling
                if result.get('requires_approval'):
                    flash(f'Payment recorded successfully and submitted for approval. Payment ID: {result.get("payment_id")}', 'success')
                else:
                    flash(f'Payment recorded and approved successfully. Payment ID: {result.get("payment_id")}', 'success')
                
                # Show warnings if any
                for warning in result.get('validation_warnings', []):
                    flash(warning, 'warning')
                
                return redirect(url_for('supplier_views.view_payment', payment_id=result.get('payment_id')))
                
            except ValueError as ve:
                flash(str(ve), 'error')
            except Exception as e:
                current_app.logger.error(f"Error recording payment: {str(e)}", exc_info=True)
                flash(f'Error recording payment: {str(e)}', 'error')
        
        return self.render_form(form)
    
    def render_form(self, form):
        """Render payment form template"""
        return render_template(
            'supplier/payment_form.html',
            form=form,
            title='Record Supplier Payment',
            suppliers_url=url_for('supplier_views.get_supplier_api', supplier_id='SUPPLIER_ID'),
            invoices_url=url_for('supplier_views.get_supplier_invoices_api', supplier_id='SUPPLIER_ID')
        )


class PaymentApprovalController:
    """Controller for payment approval workflow"""
    
    def __init__(self, payment_id):
        self.payment_id = payment_id
    
    def handle_approval(self):
        """Handle payment approval/rejection"""
        from app.forms.supplier_forms import PaymentApprovalForm
        form = PaymentApprovalForm()
        
        # Get payment details
        try:
            from app.services.supplier_service import get_supplier_payment_by_id
            payment = get_supplier_payment_by_id(self.payment_id, current_user.hospital_id)
            if not payment:
                flash('Payment not found', 'error')
                return redirect(url_for('supplier_views.payment_list'))
        except Exception as e:
            flash(f'Error loading payment: {str(e)}', 'error')
            return redirect(url_for('supplier_views.payment_list'))
        
        if form.validate_on_submit():
            try:
                if form.approval_action.data == 'approve':
                    from app.services.supplier_service import approve_supplier_payment
                    result = approve_supplier_payment(
                        payment_id=uuid.UUID(self.payment_id),
                        hospital_id=current_user.hospital_id,
                        current_user_id=current_user.user_id,
                        approval_notes=form.approval_notes.data
                    )
                    flash('Payment approved successfully', 'success')
                else:
                    # Handle rejection (implement reject_supplier_payment function)
                    flash('Payment rejection functionality to be implemented', 'info')
                
                return redirect(url_for('supplier_views.view_payment', payment_id=self.payment_id))
                
            except Exception as e:
                flash(f'Error processing approval: {str(e)}', 'error')
        
        return render_template(
            'supplier/payment_approval.html',
            form=form,
            payment=payment,
            title='Approve Payment'
        )
```

---

## **STEP 7: View Route Updates**

### **File: `app/views/supplier_views.py` - Add payment routes**

```python
# ADD these routes to existing supplier_views.py

@supplier_views_bp.route('/payment/record', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'add')
def record_payment():
    """Record new supplier payment"""
    controller = SupplierPaymentController()
    return controller.handle_request()


@supplier_views_bp.route('/payment/list', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view')
def payment_list():
    """List supplier payments with filtering"""
    try:
        # Get filter parameters
        supplier_id = request.args.get('supplier_id')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get branch context
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        # Search payments
        from app.services.supplier_service import search_supplier_payments
        result = search_supplier_payments(
            hospital_id=current_user.hospital_id,
            supplier_id=uuid.UUID(supplier_id) if supplier_id else None,
            workflow_status=status,
            start_date=datetime.strptime(start_date, '%Y-%m-%d') if start_date else None,
            end_date=datetime.strptime(end_date, '%Y-%m-%d') if end_date else None,
            branch_id=branch_uuid,
            current_user_id=current_user.user_id,
            page=page,
            per_page=per_page
        )
        
        payments = result.get('payments', [])
        total = result.get('pagination', {}).get('total_count', 0)
        
        return render_template(
            'supplier/payment_list.html',
            payments=payments,
            page=page,
            per_page=per_page,
            total=total,
            branch_context=branch_context,
            filters={
                'supplier_id': supplier_id,
                'status': status,
                'start_date': start_date,
                'end_date': end_date
            }
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in payment_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving payments: {str(e)}", "error")
        return render_template('supplier/payment_list.html', payments=[], total=0)


@supplier_views_bp.route('/payment/view/<payment_id>', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view', branch_source='entity')
def view_payment(payment_id):
    """View payment details"""
    try:
        from app.services.supplier_service import get_supplier_payment_by_id
        payment = get_supplier_payment_by_id(
            payment_id=uuid.UUID(payment_id),
            hospital_id=current_user.hospital_id,
            include_documents=True
        )
        
        if not payment:
            flash("Payment not found", "error")
            return redirect(url_for('supplier_views.payment_list'))
        
        return render_template(
            'supplier/payment_view.html',
            payment=payment,
            title=f'Payment {payment.get("reference_no", payment_id[:8])}'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in view_payment: {str(e)}", exc_info=True)
        flash(f"Error retrieving payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))


@supplier_views_bp.route('/payment/approve/<payment_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'approve', branch_source='entity')
def approve_payment(payment_id):
    """Approve pending payment"""
    controller = PaymentApprovalController(payment_id)
    return controller.handle_approval()


@supplier_views_bp.route('/api/payment/documents/upload', methods=['POST'])
@login_required
def upload_payment_document():
    """API endpoint for document upload"""
    try:
        from app.forms.supplier_forms import DocumentUploadForm
        form = DocumentUploadForm()
        
        if form.validate_on_submit():
            payment_id = request.form.get('payment_id')
            if not payment_id:
                return jsonify({'success': False, 'error': 'Payment ID required'}), 400
            
            # Process document upload
            document_data = {
                'file': form.file.data,
                'document_type': form.document_type.data,
                'description': form.description.data,
                'required_for_approval': form.required_for_approval.data
            }
            
            from app.services.supplier_service import add_payment_document
            result = add_payment_document(
                payment_id=uuid.UUID(payment_id),
                document_data=document_data,
                current_user_id=current_user.user_id
            )
            
            return jsonify({
                'success': True,
                'document_id': str(result.get('document_id')),
                'message': 'Document uploaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'errors': form.errors
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## **STEP 8: Template Updates**

### **File: `app/templates/supplier/payment_form.html`**

```html
{% extends "base.html" %}
{% from "macros/form_macros.html" import render_field, render_file_field %}

{% block title %}{{ title }}{% endblock %}

{% block content %}
<div class="container mx-auto px-4 py-6">
    <div class="max-w-4xl mx-auto">
        <div class="bg-white shadow-lg rounded-lg overflow-hidden">
            <div class="bg-blue-600 text-white px-6 py-4">
                <h1 class="text-2xl font-bold">{{ title }}</h1>
            </div>
            
            <form method="POST" enctype="multipart/form-data" class="p-6">
                {{ form.hidden_tag() }}
                
                <!-- Basic Payment Information -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div>
                        {{ render_field(form.supplier_id, class="select2") }}
                    </div>
                    <div>
                        {{ render_field(form.branch_id) }}
                    </div>
                    <div>
                        {{ render_field(form.invoice_id, class="select2") }}
                    </div>
                    <div>
                        {{ render_field(form.payment_date) }}
                    </div>
                </div>
                
                <!-- Payment Amount Section -->
                <div class="border-t pt-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Payment Amount Details</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {{ render_field(form.amount, class="total-amount") }}
                        {{ render_field(form.cash_amount, class="method-amount") }}
                        {{ render_field(form.cheque_amount, class="method-amount") }}
                        {{ render_field(form.bank_transfer_amount, class="method-amount") }}
                        {{ render_field(form.upi_amount, class="method-amount") }}
                    </div>
                    <div id="amount-validation" class="mt-2 text-sm text-gray-600"></div>
                </div>
                
                <!-- Payment Method Details -->
                <div class="border-t pt-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Payment Method Details</h3>
                    
                    <!-- Cheque Details -->
                    <div id="cheque-details" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4" style="display: none;">
                        {{ render_field(form.cheque_number) }}
                        {{ render_field(form.cheque_date) }}
                        {{ render_field(form.cheque_bank) }}
                    </div>
                    
                    <!-- Bank Transfer Details -->
                    <div id="bank-details" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4" style="display: none;">
                        {{ render_field(form.bank_account_name) }}
                        {{ render_field(form.bank_reference_number) }}
                    </div>
                    
                    <!-- UPI Details -->
                    <div id="upi-details" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4" style="display: none;">
                        {{ render_field(form.upi_transaction_id) }}
                        {{ render_field(form.upi_app_name) }}
                    </div>
                </div>
                
                <!-- Document Upload -->
                <div class="border-t pt-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Supporting Documents</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {{ render_file_field(form.receipt_file) }}
                        {{ render_file_field(form.bank_statement_file) }}
                        {{ render_file_field(form.authorization_file) }}
                    </div>
                </div>
                
                <!-- Additional Information -->
                <div class="border-t pt-6 mb-6">
                    <h3 class="text-lg font-semibold mb-4">Additional Information</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {{ render_field(form.reference_no) }}
                        <div class="md:col-span-2">
                            {{ render_field(form.notes, rows="3") }}
                        </div>
                    </div>
                </div>
                
                <!-- Submit Section -->
                <div class="border-t pt-6">
                    <div class="flex justify-end space-x-4">
                        <a href="{{ url_for('supplier_views.payment_list') }}" 
                           class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded">
                            Cancel
                        </a>
                        {{ form.submit(class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded") }}
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    // Payment amount validation
    const amountFields = document.querySelectorAll('.method-amount input');
    const totalField = document.querySelector('.total-amount input');
    const validationDiv = document.getElementById('amount-validation');
    
    function validateAmounts() {
        const total = parseFloat(totalField.value) || 0;
        const methodTotal = Array.from(amountFields).reduce((sum, field) => {
            return sum + (parseFloat(field.value) || 0);
        }, 0);
        
        if (methodTotal > 0) {
            const difference = Math.abs(total - methodTotal);
            if (difference > 0.01) {
                validationDiv.innerHTML = `<span class="text-red-600">⚠️ Method total (${methodTotal.toFixed(2)}) doesn't match total amount (${total.toFixed(2)})</span>`;
                return false;
            } else {
                validationDiv.innerHTML = `<span class="text-green-600">✓ Amounts match</span>`;
                return true;
            }
        } else {
            validationDiv.innerHTML = '';
            return true;
        }
    }
    
    // Show/hide method details based on amounts
    function toggleMethodDetails() {
        const chequeAmount = parseFloat(document.querySelector('input[name="cheque_amount"]').value) || 0;
        const bankAmount = parseFloat(document.querySelector('input[name="bank_transfer_amount"]').value) || 0;
        const upiAmount = parseFloat(document.querySelector('input[name="upi_amount"]').value) || 0;
        
        document.getElementById('cheque-details').style.display = chequeAmount > 0 ? 'grid' : 'none';
        document.getElementById('bank-details').style.display = bankAmount > 0 ? 'grid' : 'none';
        document.getElementById('upi-details').style.display = upiAmount > 0 ? 'grid' : 'none';
    }
    
    // Add event listeners
    [...amountFields, totalField].forEach(field => {
        field.addEventListener('input', () => {
            validateAmounts();
            toggleMethodDetails();
        });
    });
    
    // Initial validation
    toggleMethodDetails();
    validateAmounts();
    
    // Form submission validation
    document.querySelector('form').addEventListener('submit', function(e) {
        if (!validateAmounts()) {
            e.preventDefault();
            alert('Please fix amount validation errors before submitting.');
        }
    });
});
</script>
{% endblock %}
```

---

## **STEP 9: Testing & Validation**

### **File: `tests/test_payment_system.py`**

```python
# CREATE new test file

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from app.services.supplier_service import (
    validate_payment_data,
    record_supplier_payment,
    approve_supplier_payment
)
from app.models.transaction import SupplierPayment, PaymentDocument


class TestPaymentSystem:
    """Test suite for enhanced payment system"""
    
    def test_multi_method_validation_success(self, db_session, sample_hospital, sample_supplier, sample_user):
        """Test successful multi-method payment validation"""
        payment_data = {
            'supplier_id': str(sample_supplier.supplier_id),
            'amount': 15000.00,
            'cash_amount': 5000.00,
            'cheque_amount': 10000.00,
            'bank_transfer_amount': 0,
            'upi_amount': 0,
            'branch_id': str(sample_hospital.default_branch_id),
            'cheque_number': 'CHQ123456',
            'cheque_date': datetime.now().date()
        }
        
        result = validate_payment_data(payment_data, sample_hospital.hospital_id, sample_user.user_id)
        
        assert result['is_valid'] == True
        assert len(result['errors']) == 0
        assert result['method_amounts']['cash_amount'] == 5000.00
        assert result['method_amounts']['cheque_amount'] == 10000.00
    
    def test_multi_method_validation_mismatch(self, db_session, sample_hospital, sample_supplier, sample_user):
        """Test validation failure when amounts don't match"""
        payment_data = {
            'supplier_id': str(sample_supplier.supplier_id),
            'amount': 15000.00,
            'cash_amount': 5000.00,
            'cheque_amount': 9000.00,  # Mismatch: should be 10000
            'branch_id': str(sample_hospital.default_branch_id)
        }
        
        result = validate_payment_data(payment_data, sample_hospital.hospital_id, sample_user.user_id)
        
        assert result['is_valid'] == False
        assert any('doesn\'t match sum of payment methods' in error for error in result['errors'])
    
    def test_payment_recording_with_approval(self, db_session, sample_hospital, sample_supplier, sample_user):
        """Test payment recording that requires approval"""
        payment_data = {
            'supplier_id': str(sample_supplier.supplier_id),
            'amount': 75000.00,  # Above approval threshold
            'cash_amount': 75000.00,
            'branch_id': str(sample_hospital.default_branch_id),
            'payment_date': datetime.now(timezone.utc),
            'notes': 'Large payment requiring approval'
        }
        
        result = record_supplier_payment(
            hospital_id=sample_hospital.hospital_id,
            payment_data=payment_data,
            current_user_id=sample_user.user_id,
            session=db_session
        )
        
        assert result['requires_approval'] == True
        assert result['workflow_status'] == 'draft'
        
        # Verify payment was created
        payment = db_session.query(SupplierPayment).filter_by(
            payment_id=result['payment_id']
        ).first()
        assert payment is not None
        assert payment.workflow_status == 'draft'
        assert payment.requires_approval == True
    
    def test_payment_approval_workflow(self, db_session, sample_hospital, sample_supplier, sample_user, sample_approver):
        """Test payment approval workflow"""
        # First create a payment requiring approval
        payment_data = {
            'supplier_id': str(sample_supplier.supplier_id),
            'amount': 75000.00,
            'cash_amount': 75000.00,
            'branch_id': str(sample_hospital.default_branch_id)
        }
        
        payment_result = record_supplier_payment(
            hospital_id=sample_hospital.hospital_id,
            payment_data=payment_data,
            current_user_id=sample_user.user_id,
            session=db_session
        )
        
        # Now approve the payment
        approval_result = approve_supplier_payment(
            payment_id=payment_result['payment_id'],
            hospital_id=sample_hospital.hospital_id,
            current_user_id=sample_approver.user_id,
            approval_notes='Approved for vendor payment',
            session=db_session
        )
        
        assert approval_result['workflow_status'] == 'approved'
        assert approval_result['approved_by'] == sample_approver.user_id
        assert approval_result['approval_notes'] == 'Approved for vendor payment'
    
    def test_document_upload_integration(self, db_session, sample_hospital, sample_supplier, sample_user):
        """Test document upload with payment"""
        # Mock file upload
        from werkzeug.datastructures import FileStorage
        from io import BytesIO
        
        mock_file = FileStorage(
            stream=BytesIO(b"fake pdf content"),
            filename="receipt.pdf",
            content_type="application/pdf"
        )
        
        payment_data = {
            'supplier_id': str(sample_supplier.supplier_id),
            'amount': 25000.00,
            'cash_amount': 25000.00,
            'branch_id': str(sample_hospital.default_branch_id),
            'documents': [{
                'file': mock_file,
                'document_type': 'receipt',
                'description': 'Payment receipt'
            }]
        }
        
        result = record_supplier_payment(
            hospital_id=sample_hospital.hospital_id,
            payment_data=payment_data,
            current_user_id=sample_user.user_id,
            session=db_session
        )
        
        # Verify document was created
        documents = db_session.query(PaymentDocument).filter_by(
            payment_id=result['payment_id']
        ).all()
        
        assert len(documents) == 1
        assert documents[0].document_type == 'receipt'
        assert documents[0].original_filename == 'receipt.pdf'


# ADD test fixtures
@pytest.fixture
def sample_approver(db_session, sample_hospital):
    """Create a sample approver user"""
    from app.models.transaction import User
    from app.models.master import Staff
    
    # Create staff record
    staff = Staff(
        hospital_id=sample_hospital.hospital_id,
        branch_id=sample_hospital.default_branch_id,
        staff_name='Approver User',
        designation='Manager',
        department='Finance'
    )
    db_session.add(staff)
    db_session.flush()
    
    # Create user record
    user = User(
        user_id='9999999999',
        hospital_id=sample_hospital.hospital_id,
        entity_type='staff',
        entity_id=staff.staff_id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    
    return user
```

---

## **STEP 10: Configuration & Environment Setup**

### **File: `.env` - Add payment configuration**

```bash
# ADD to existing .env file

# Payment System Configuration
PAYMENT_APPROVAL_THRESHOLD_L1=50000.00
PAYMENT_APPROVAL_THRESHOLD_L2=200000.00
PAYMENT_AUTO_APPROVE_LIMIT=5000.00
PAYMENT_DOCUMENT_STORAGE_PATH=/secure_storage/payment_documents
PAYMENT_MAX_FILE_SIZE=10485760
PAYMENT_ALLOWED_FILE_TYPES=pdf,jpg,jpeg,png
```

### **File: `requirements.txt` - Add any new dependencies**

```txt
# ADD if not already present
Pillow>=9.0.0  # For image processing
python-magic>=0.4.24  # For file type detection
```

---

## **STEP 11: Deployment & Migration Script**

### **File: `scripts/deploy_payment_system.sh`**

```bash
#!/bin/bash

# Payment System Deployment Script
echo "Starting Payment System Phase 1 Deployment..."

# 1. Backup current database
echo "Creating database backup..."
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Run database migrations
echo "Running database migrations..."
psql $DATABASE_URL -f migrations/001_supplier_payment_enhancements.sql
psql $DATABASE_URL -f migrations/002_document_management.sql

# 3. Create storage directories
echo "Creating storage directories..."
mkdir -p /secure_storage/payment_documents
chmod 755 /secure_storage/payment_documents
chown app:app /secure_storage/payment_documents

# 4. Update application
echo "Updating application..."
git pull origin main
pip install -r requirements.txt

# 5. Restart application
echo "Restarting application..."
systemctl restart your_app_service

# 6. Run tests
echo "Running tests..."
pytest tests/test_payment_system.py -v

echo "Deployment completed!"
```

---

## **STEP 12: Implementation Checklist**

### **Phase 1 Implementation Checklist**

```markdown
## Database Layer
- [ ] Run migration 001_supplier_payment_enhancements.sql
- [ ] Run migration 002_document_management.sql
- [ ] Verify all tables and indexes created
- [ ] Test database constraints

## Model Layer  
- [ ] Add fields to SupplierPayment class
- [ ] Add PaymentDocument class
- [ ] Add PaymentDocumentAccessLog class
- [ ] Add computed properties and methods
- [ ] Test model relationships

## Service Layer
- [ ] Update validate_payment_data function
- [ ] Update _record_supplier_payment function
- [ ] Add approve_supplier_payment function
- [ ] Add _process_payment_documents function
- [ ] Add document management functions
- [ ] Test all service functions

## Controller Layer
- [ ] Add SupplierPaymentController class
- [ ] Add PaymentApprovalController class
- [ ] Test controller request handling
- [ ] Test error handling

## Form Layer
- [ ] Update SupplierPaymentForm
- [ ] Add PaymentApprovalForm
- [ ] Add DocumentUploadForm
- [ ] Test form validation
- [ ] Test file upload validation

## View Layer
- [ ] Add payment recording routes
- [ ] Add payment list route
- [ ] Add payment view route
- [ ] Add payment approval route
- [ ] Add document upload API
- [ ] Test all routes

## Template Layer
- [ ] Create payment_form.html
- [ ] Create payment_list.html
- [ ] Create payment_view.html
- [ ] Create payment_approval.html
- [ ] Test responsive design
- [ ] Test JavaScript functionality

## Configuration
- [ ] Update config.py with payment settings
- [ ] Update .env with payment variables
- [ ] Create storage directories
- [ ] Set proper permissions

## Testing
- [ ] Run unit tests
- [ ] Run integration tests
- [ ] Test file uploads
- [ ] Test approval workflow
- [ ] Test branch permissions

## Documentation
- [ ] Update API documentation
- [ ] Create user manual
- [ ] Update deployment guide
- [ ] Create troubleshooting guide

## Deployment
- [ ] Backup production database
- [ ] Deploy to staging environment
- [ ] Run full test suite
- [ ] Deploy to production
- [ ] Monitor for errors
```

---

## **STEP 13: Quick Start Implementation Order**

### **Week 1: Foundation**
1. **Day 1**: Database migrations + Model updates
2. **Day 2**: Basic service layer functions
3. **Day 3**: Simple payment form
4. **Day 4**: Basic payment recording
5. **Day 5**: Testing and bug fixes

### **Week 2: Enhancement**  
1. **Day 1**: Multi-method payment logic
2. **Day 2**: Document upload functionality
3. **Day 3**: Approval workflow
4. **Day 4**: Payment list and view pages
5. **Day 5**: Integration testing

### **Week 3: Polish**
1. **Day 1**: UI/UX improvements
2. **Day 2**: Error handling enhancement
3. **Day 3**: Performance optimization
4. **Day 4**: Documentation
5. **Day 5**: Production deployment

---

## **Final Notes**

### **Critical Success Factors:**
1. **Run database migrations first** - Foundation must be solid
2. **Test each layer independently** - Don't skip unit tests
3. **Start simple, add complexity** - Get basic payment recording working first
4. **Document as you go** - Don't defer documentation
5. **Monitor production closely** - Watch for performance issues

### **Risk Mitigation:**
1. **Always backup before migrations**
2. **Test on staging environment first**
3. **Have rollback scripts ready**
4. **Monitor error logs during deployment**
5. **Train users on new features**

This comprehensive implementation plan gives you everything needed to successfully deploy Phase 1 of your Supplier Payment System. Each step builds on the previous one, ensuring a solid foundation for future enhancements.