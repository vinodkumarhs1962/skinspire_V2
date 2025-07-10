# ===================================================================
# COMPLETE CREDIT NOTE TRANSACTION WORKFLOW
# ===================================================================

"""
OVERVIEW:
This document explains the complete workflow of credit note transactions,
how components interact, and integration with existing system components.

BUSINESS SCENARIO:
A supplier payment was made incorrectly and needs to be credited back.
Instead of reversing the payment (which breaks audit trails), we create
a credit note that offsets the payment while maintaining complete history.
"""

# ===================================================================
# PHASE 1: PRE-CREDIT NOTE STATE (EXISTING SYSTEM)
# ===================================================================

"""
INITIAL STATE:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Supplier       │    │  Supplier       │    │  Supplier       │
│  Invoice        │◄──►│  Payment        │◄──►│  GL Entries     │
│  INV-001        │    │  PAY-001        │    │  (Dr/Cr)        │
│  Amount: 1000   │    │  Amount: 1000   │    │  Posted: Yes    │
│  Status: Paid   │    │  Status: Approved│   │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Invoice Lines  │    │  Payment Docs   │    │  AP Subledger   │
│  Medicine A: 500│    │  Receipt: PDF   │    │  Balance: 0     │
│  Medicine B: 500│    │  Bank Stmt: PDF │    │  (Paid)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘

PROBLEM DISCOVERED:
- Payment was made twice (duplicate)
- Incorrect amount paid
- Quality issue requiring refund
- Invoice dispute resolved in supplier's favor
"""

# ===================================================================
# PHASE 2: CREDIT NOTE INITIATION (NEW WORKFLOW)
# ===================================================================

"""
STEP 1: USER NAVIGATION TO PAYMENT VIEW
────────────────────────────────────────

User Flow:
1. User navigates to Supplier → Payments → View Payment (PAY-001)
2. System loads: SupplierPaymentViewController.view_payment()
3. Enhanced payment_view.html template renders with new credit note section

Component Interaction:
┌─────────────────┐
│   User          │
│   (Browser)     │
└─────────┬───────┘
          │ GET /supplier/payment/view/{payment_id}
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  supplier_views │────│  payment_view   │────│ get_supplier_   │
│  .view_payment  │    │  .html template │    │ payment_by_id() │
│  (Route)        │    │  (Enhanced)     │    │ (Service)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          │                       │                       ▼
          │                       │            ┌─────────────────┐
          │                       │            │ Enhanced Service│
          │                       │            │ Returns:        │
          │                       │            │ - Payment data  │
          │                       │            │ - Credit notes  │
          │                       │            │ - Can create?   │
          │                       │            └─────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ENHANCED PAYMENT VIEW                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Payment Info  │  │   Documents     │  │ Credit Notes    │ │
│  │   PAY-001       │  │   Receipt       │  │ [NEW SECTION]   │ │
│  │   ₹1000         │  │   Bank Stmt     │  │                 │ │
│  │   Approved      │  │                 │  │ ┌─────────────┐ │ │
│  └─────────────────┘  └─────────────────┘  │ │   Create    │ │ │
│                                           │ │ Credit Note │ │ │
│                                           │ │   Button    │ │ │
│                                           │ └─────────────┘ │ │
│                                           └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

Enhanced Service Call:
```python
payment = get_supplier_payment_by_id(
    payment_id=payment_id,
    hospital_id=current_user.hospital_id,
    include_credit_notes=True  # NEW parameter
)
# Returns enhanced data structure with credit note information
```
"""

# ===================================================================
# PHASE 3: CREDIT NOTE FORM INITIALIZATION
# ===================================================================

"""
STEP 2: CREDIT NOTE FORM SETUP
──────────────────────────────

User Action: Clicks "Create Credit Note" button

Component Flow:
┌─────────────────┐
│   User clicks   │
│ "Create Credit  │
│    Note"        │
└─────────┬───────┘
          │ GET /supplier/payment/{payment_id}/credit-note
          ▼
┌─────────────────┐
│ supplier_views  │
│.create_credit   │
│_note() route    │
└─────────┬───────┘
          │ Instantiates
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ SupplierCredit  │────│get_additional   │────│get_supplier_    │
│NoteController   │    │_context()       │    │payment_by_id()  │
│.__init__()      │    │                 │    │                 │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          │ Inherits from         │ Validates payment     │ Returns payment
          ▼ FormController        ▼ eligibility           ▼ context data
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ FormController  │    │ Validation:     │    │ Payment Data:   │
│ .handle_request │    │ - Is Approved?  │    │ - Amount        │
│ (GET request)   │    │ - Has Credits?  │    │ - Supplier      │
│                 │    │ - Permissions?  │    │ - Invoice Ref   │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│ Credit Note     │────│ setup_form_     │
│ Form Creation   │    │ defaults()      │
│                 │    │                 │
└─────────┬───────┘    └─────────────────┘
          │                       │
          │ Auto-generates        │ Pre-fills form with:
          ▼ form fields           ▼ 
┌─────────────────────────────────────────────────────────────────┐
│                    CREDIT NOTE FORM                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Credit Note Number: CN-PAY-001-20250615 [readonly]        ││
│  │  Credit Note Date:   2025-06-15                             ││
│  │  Credit Amount:      ₹1000.00 [readonly]                   ││
│  │  Reason Code:        [Payment Error ▼]                     ││
│  │  Reason Details:     [Text area for detailed explanation]   ││
│  │                                                             ││
│  │  Reference Info: [readonly section]                        ││
│  │  - Payment Ref: PAY-001                                    ││
│  │  - Invoice: INV-001                                        ││
│  │  - Supplier: ABC Medical Supplies                          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

Form Pre-filling Logic:
```python
def setup_form_defaults(self, form):
    payment = get_supplier_payment_by_id(...)
    
    # Auto-generate credit note number
    form.credit_note_number.data = f"CN-PAY-{payment['reference_no']}-{today}"
    
    # Pre-fill amounts and references
    form.credit_amount.data = float(payment['amount'])
    form.payment_reference.data = payment['reference_no']
    form.supplier_name.data = payment['supplier_name']
    
    # Hidden fields for processing
    form.payment_id.data = str(payment['payment_id'])
    form.supplier_id.data = str(payment['supplier_id'])
```
"""

# ===================================================================
# PHASE 4: CREDIT NOTE SUBMISSION & PROCESSING
# ===================================================================

"""
STEP 3: FORM SUBMISSION & VALIDATION
────────────────────────────────────

User Action: Fills form and submits

Processing Flow:
┌─────────────────┐
│   User submits  │
│   credit note   │
│      form       │
└─────────┬───────┘
          │ POST /supplier/payment/{payment_id}/credit-note
          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│SupplierCredit   │────│ Form Validation │────│ Business Rules  │
│NoteController   │    │ (WTForms)       │    │ Validation      │
│.process_form()  │    │                 │    │                 │
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          │ Calls service         │ Validates:            │ Validates:
          ▼ function              ▼ - Required fields     ▼ - Payment approved
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│create_supplier_ │    │ - Field lengths │    │ - Amount ≤ payment│
│credit_note_from_│    │ - Data types    │    │ - Reason provided │
│payment()        │    │ - Format rules  │    │ - User permissions│
└─────────┬───────┘    └─────────────────┘    └─────────────────┘
          │
          │ Service layer processing
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SERVICE LAYER PROCESSING                     │
│                                                                 │
│  Step 1: Validate Payment Eligibility                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ - Query SupplierPayment table                               ││
│  │ - Check workflow_status = 'approved'                        ││
│  │ - Verify no existing credit notes (if business rule)        ││
│  │ - Validate user permissions                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Step 2: Prepare Credit Note Data                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ - Generate unique credit note number                        ││
│  │ - Calculate negative amounts (-₹1000)                       ││
│  │ - Determine medicine_id (original or adjustment)            ││
│  │ - Set proper GL account codes                               ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Step 3: Create Database Transaction                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ BEGIN TRANSACTION                                           ││
│  │ - Create SupplierInvoice (is_credit_note=True)              ││
│  │ - Create SupplierInvoiceLine (negative amounts)             ││
│  │ - Update original payment notes                             ││
│  │ - Log audit trail                                           ││
│  │ COMMIT TRANSACTION                                          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
"""

# ===================================================================
# PHASE 5: DATABASE TRANSACTION DETAILS
# ===================================================================

"""
STEP 4: DATABASE RECORD CREATION
────────────────────────────────

Database Transaction Flow:

1. CREATE SUPPLIER INVOICE (Credit Note):
┌─────────────────────────────────────────────────────────────────┐
│                     supplier_invoice                           │
├─────────────────────┬───────────────────────────────────────────┤
│ invoice_id          │ [new UUID]                               │
│ hospital_id         │ 4ef72e18-e65d-4766-b9eb-0308c42485ca     │
│ branch_id           │ [from payment.branch_id]                 │
│ supplier_id         │ [from payment.supplier_id]               │
│ supplier_invoice_no │ CN-PAY-001-20250615                      │
│ invoice_date        │ 2025-06-15                               │
│ total_amount        │ -1000.00 ◄── NEGATIVE AMOUNT            │
│ payment_status      │ 'paid'                                   │
│ is_credit_note      │ TRUE ◄── CREDIT NOTE FLAG               │
│ original_invoice_id │ [original invoice if exists]            │
│ notes               │ 'Credit note for payment PAY-001: ...'  │
│ created_by          │ current_user_id                          │
└─────────────────────┴───────────────────────────────────────────┘

2. CREATE SUPPLIER INVOICE LINE:
┌─────────────────────────────────────────────────────────────────┐
│                  supplier_invoice_line                         │
├─────────────────────┬───────────────────────────────────────────┤
│ line_id             │ [new UUID]                               │
│ invoice_id          │ [credit note invoice_id]                 │
│ medicine_id         │ [credit adjustment medicine OR original] │
│ medicine_name       │ 'Credit Note - Payment Error'            │
│ units               │ 1.00                                     │
│ pack_purchase_price │ -1000.00 ◄── NEGATIVE AMOUNT            │
│ line_total          │ -1000.00 ◄── NEGATIVE TOTAL             │
│ gst_rate            │ 0.00 (no GST on adjustments)            │
│ created_by          │ current_user_id                          │
└─────────────────────┴───────────────────────────────────────────┘

3. UPDATE ORIGINAL PAYMENT:
┌─────────────────────────────────────────────────────────────────┐
│                    supplier_payment                            │
├─────────────────────┬───────────────────────────────────────────┤
│ payment_id          │ [original payment ID]                    │
│ notes               │ 'Payment for INV-001                     │
│                     │  Credit Note: CN-PAY-001-20250615'       │
│ updated_by          │ current_user_id                          │
│ updated_at          │ 2025-06-15 10:30:00                      │
└─────────────────────┴───────────────────────────────────────────┘

4. AUDIT LOG ENTRY:
┌─────────────────────────────────────────────────────────────────┐
│ Credit Note Created:                                            │
│ - User: current_user_id                                         │
│ - Payment: PAY-001                                              │
│ - Credit Note: CN-PAY-001-20250615                             │
│ - Amount: ₹1000.00                                              │
│ - Reason: Payment Error                                         │
│ - Timestamp: 2025-06-15 10:30:00                               │
└─────────────────────────────────────────────────────────────────┘
"""

# ===================================================================
# PHASE 6: POST-CREATION STATE & INTEGRATION
# ===================================================================

"""
STEP 5: SYSTEM STATE AFTER CREDIT NOTE CREATION
───────────────────────────────────────────────

Updated System State:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Original       │    │  Original       │    │  Credit Note    │
│  Invoice        │    │  Payment        │    │  Invoice        │
│  INV-001        │◄──►│  PAY-001        │◄──►│  CN-PAY-001     │
│  Amount: 1000   │    │  Amount: 1000   │    │  Amount: -1000  │
│  Status: Paid   │    │  Status: Approved│   │  Status: Paid   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Original Lines │    │  Enhanced Notes │    │  Credit Line    │
│  Medicine A: 500│    │  'Payment for   │    │  Adjustment:    │
│  Medicine B: 500│    │   INV-001       │    │  -1000         │
│                 │    │   Credit Note:  │    │                 │
│                 │    │   CN-PAY-001'   │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘

ENHANCED PAYMENT VIEW NOW SHOWS:
┌─────────────────────────────────────────────────────────────────┐
│                 ENHANCED PAYMENT VIEW                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Payment Info  │  │   Documents     │  │ Credit Notes    │ │
│  │   PAY-001       │  │   Receipt       │  │                 │ │
│  │   ₹1000         │  │   Bank Stmt     │  │ ┌─────────────┐ │ │
│  │   Approved      │  │                 │  │ │CN-PAY-001   │ │ │
│  └─────────────────┘  └─────────────────┘  │ │₹1000.00     │ │ │
│                                           │ │Payment Error│ │ │
│                                           │ │[View][Print]│ │ │
│                                           │ └─────────────┘ │ │
│                                           │                 │ │
│                                           │ Net Impact:     │ │
│                                           │ ₹0.00          │ │
│                                           └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

INTEGRATION WITH EXISTING REPORTS:
- Supplier statements show both payment and credit
- Account payable reports reflect net amounts
- Audit reports show complete transaction history
- Invoice aging reports exclude credited amounts
"""

# ===================================================================
# PHASE 7: ADVANCED INTEGRATION SCENARIOS
# ===================================================================

"""
STEP 6: INTEGRATION WITH EXISTING SYSTEM COMPONENTS
──────────────────────────────────────────────────

1. SUPPLIER STATEMENT INTEGRATION:
┌─────────────────────────────────────────────────────────────────┐
│              ABC Medical Supplies - Statement                  │
├─────────────┬───────────────┬─────────────┬─────────────────────┤
│ Date        │ Reference     │ Debit       │ Credit              │
├─────────────┼───────────────┼─────────────┼─────────────────────┤
│ 2025-06-01  │ INV-001       │ 1000.00     │                     │
│ 2025-06-05  │ PAY-001       │             │ 1000.00             │
│ 2025-06-15  │ CN-PAY-001    │ 1000.00     │                     │
├─────────────┼───────────────┼─────────────┼─────────────────────┤
│             │ Balance       │             │ 1000.00             │
└─────────────┴───────────────┴─────────────┴─────────────────────┘

2. GL INTEGRATION (Future Enhancement):
If/when GL integration is added for credit notes:

   Dr. Accounts Payable       1000.00
       Cr. Cash/Bank                   1000.00
   (To record credit note effect)

3. REPORTING INTEGRATION:
┌─────────────────────────────────────────────────────────────────┐
│                      Payment Analysis Report                   │
├─────────────┬───────────────┬─────────────┬─────────────────────┤
│ Payment ID  │ Amount        │ Credit Notes│ Net Amount          │
├─────────────┼───────────────┼─────────────┼─────────────────────┤
│ PAY-001     │ 1000.00       │ (1000.00)   │ 0.00                │
│ PAY-002     │ 2000.00       │ 0.00        │ 2000.00             │
│ PAY-003     │ 1500.00       │ (500.00)    │ 1000.00             │
└─────────────┴───────────────┴─────────────┴─────────────────────┘

4. SEARCH AND FILTERING:
Enhanced search in payment lists includes credit note filters:
- Show payments with credit notes
- Filter by credit note reason
- Date range for credit note creation
- Amount ranges for net payment impact
"""

# ===================================================================
# PHASE 8: COMPONENT INTERACTION SUMMARY
# ===================================================================

"""
COMPLETE COMPONENT INTERACTION MAP:
═══════════════════════════════════

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PRESENTATION  │    │    CONTROLLER   │    │    SERVICE      │
│     LAYER       │    │      LAYER      │    │     LAYER       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │ User Interaction      │ Form Processing       │ Business Logic
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ payment_view    │────│SupplierCredit   │────│create_supplier_ │
│ .html           │    │NoteController   │    │credit_note_from_│
│ (Enhanced)      │    │                 │    │payment()        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ credit_note_    │    │SupplierCredit   │    │get_supplier_    │
│ form.html       │    │NoteForm         │    │payment_by_id()  │
│ (New)           │    │ (WTForms)       │    │ (Enhanced)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ROUTING       │    │   VALIDATION    │    │   DATA LAYER    │
│    LAYER        │    │     LAYER       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│supplier_views   │    │ Form validation │    │ SupplierInvoice │
│.create_credit   │    │ Business rules  │    │ SupplierPayment │
│_note()          │    │ Permission check│    │ Models          │
└─────────────────┘    └─────────────────┘    └─────────────────┘

DATA FLOW DIRECTION:
User → View → Controller → Service → Database
Database → Service → Controller → View → User
"""

# ===================================================================
# PHASE 9: FUTURE ENHANCEMENT ROADMAP
# ===================================================================

"""
FUTURE ENHANCEMENT OPPORTUNITIES:
═════════════════════════════════

Phase 1 (Immediate): ✅ COMPLETED
- Basic credit note creation
- Form integration
- Audit trail maintenance
- Payment view integration

Phase 2 (Short-term):
- Partial credit notes (less than payment amount)
- Multiple credit notes per payment
- Credit note approval workflow
- Enhanced reporting and analytics

Phase 3 (Medium-term):
- Automatic GL posting for credit notes
- Integration with financial reporting
- Batch credit note processing
- Credit note templates/reasons

Phase 4 (Long-term):
- Advanced reconciliation features
- Integration with external accounting systems
- Automated credit note suggestions
- Machine learning for fraud detection

SCALABILITY CONSIDERATIONS:
- Component architecture supports easy enhancement
- Service layer abstraction enables different backends
- Form framework supports dynamic field addition
- Template structure allows easy UI modifications
"""

if __name__ == "__main__":
    print("Credit Note Workflow Documentation")
    print("This file contains the complete workflow explanation")
    print("for the Supplier Payment Credit Note feature.")


# ===================================================================
# CRITICAL FIX: Medicine Handling for Credit Notes
# ===================================================================

"""
ISSUE: SupplierInvoiceLine requires medicine_id, but credit notes may not 
reference specific medicines (they reference payment adjustments).

SOLUTION OPTIONS:
1. Create a special "Credit Adjustment" medicine entry
2. Use the original payment's medicine (if invoice-linked)
3. Allow NULL medicine_id for credit notes (requires model change)

RECOMMENDED: Option 1 - Create special medicine entry for credit adjustments
"""

# ===================================================================
# STEP 1: CREATE CREDIT ADJUSTMENT MEDICINE (One-time setup)
# ===================================================================

def create_credit_adjustment_medicine(hospital_id, current_user_id, session=None):
    """
    Create a special medicine entry for credit note adjustments
    This should be run once during system setup
    """
    from app.models.master import Medicine, MedicineCategory
    from app.services.database_service import get_db_session
    import uuid
    
    def _create_credit_medicine(session):
        # Check if credit medicine already exists
        existing = session.query(Medicine).filter_by(
            hospital_id=hospital_id,
            medicine_name='Credit Note Adjustment'
        ).first()
        
        if existing:
            return existing.medicine_id
        
        # Get or create "Administrative" category
        admin_category = session.query(MedicineCategory).filter_by(
            hospital_id=hospital_id,
            name='Administrative'
        ).first()
        
        if not admin_category:
            admin_category = MedicineCategory(
                hospital_id=hospital_id,
                name='Administrative',
                description='Administrative and adjustment entries',
                category_type='Misc',
                status='active',
                created_by=current_user_id
            )
            session.add(admin_category)
            session.flush()
        
        # Create credit adjustment medicine
        credit_medicine = Medicine(
            hospital_id=hospital_id,
            medicine_name='Credit Note Adjustment',
            generic_name='Credit Note Adjustment',
            category_id=admin_category.category_id,
            medicine_type='Misc',
            dosage_form='N/A',
            strength='N/A',
            unit_of_measure='Each',
            hsn_code='9999',  # Generic service code
            gst_rate=0,  # No GST on adjustments
            is_gst_exempt=True,
            prescription_required=False,
            is_consumable=False,
            status='active',
            created_by=current_user_id
        )
        
        session.add(credit_medicine)
        session.flush()
        
        return credit_medicine.medicine_id
    
    if session is not None:
        return _create_credit_medicine(session)
    
    with get_db_session() as new_session:
        result = _create_credit_medicine(new_session)
        new_session.commit()
        return result

# ===================================================================
# STEP 2: UPDATED SERVICE FUNCTION WITH MEDICINE HANDLING
# ===================================================================

def _create_supplier_credit_note_from_payment(
    session: Session,
    hospital_id: uuid.UUID,
    credit_note_data: Dict,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    UPDATED: Enhanced version with proper medicine handling
    """
    try:
        from app.models.transaction import SupplierPayment, SupplierInvoice, SupplierInvoiceLine
        from app.models.master import Supplier, Medicine
        from datetime import datetime, timezone
        from decimal import Decimal
        
        # ===================================================================
        # STEP 1: VALIDATE PAYMENT AND GET CONTEXT (SAME AS BEFORE)
        # ===================================================================
        
        payment_id = credit_note_data.get('payment_id')
        payment = session.query(SupplierPayment).filter_by(
            payment_id=payment_id,
            hospital_id=hospital_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        if payment.workflow_status != 'approved':
            raise ValueError("Only approved payments can have credit notes created")
        
        # Get supplier details
        supplier = session.query(Supplier).filter_by(
            supplier_id=payment.supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError("Supplier not found")
        
        # Get original invoice if exists
        original_invoice = None
        original_medicine_id = None
        
        if payment.invoice_id:
            original_invoice = session.query(SupplierInvoice).filter_by(
                invoice_id=payment.invoice_id,
                hospital_id=hospital_id
            ).first()
            
            # Try to get medicine from original invoice line items
            if original_invoice:
                first_line = session.query(SupplierInvoiceLine).filter_by(
                    invoice_id=original_invoice.invoice_id
                ).first()
                if first_line:
                    original_medicine_id = first_line.medicine_id
        
        # ===================================================================
        # STEP 2: GET OR CREATE CREDIT ADJUSTMENT MEDICINE
        # ===================================================================
        
        credit_medicine_id = original_medicine_id
        
        if not credit_medicine_id:
            # Get or create credit adjustment medicine
            credit_medicine = session.query(Medicine).filter_by(
                hospital_id=hospital_id,
                medicine_name='Credit Note Adjustment'
            ).first()
            
            if not credit_medicine:
                # Create it on-the-fly
                credit_medicine_id = create_credit_adjustment_medicine(
                    hospital_id, current_user_id, session
                )
            else:
                credit_medicine_id = credit_medicine.medicine_id
        
        # ===================================================================
        # STEP 3: CREATE CREDIT NOTE INVOICE (SAME AS BEFORE)
        # ===================================================================
        
        credit_amount = Decimal(str(credit_note_data.get('credit_amount')))
        credit_note_date = credit_note_data.get('credit_note_date')
        
        credit_note = SupplierInvoice(
            hospital_id=hospital_id,
            branch_id=credit_note_data.get('branch_id'),
            supplier_id=payment.supplier_id,
            supplier_invoice_number=credit_note_data.get('credit_note_number'),
            invoice_date=credit_note_date,
            
            # Credit note specific fields
            is_credit_note=True,
            original_invoice_id=credit_note_data.get('original_invoice_id'),
            
            # Copy relevant details from original invoice or payment
            supplier_gstin=original_invoice.supplier_gstin if original_invoice else supplier.gst_registration_number,
            place_of_supply=original_invoice.place_of_supply if original_invoice else supplier.state_code,
            currency_code=original_invoice.currency_code if original_invoice else 'INR',
            exchange_rate=original_invoice.exchange_rate if original_invoice else Decimal('1.0'),
            
            # Negative amounts for credit note
            total_amount=-credit_amount,
            cgst_amount=Decimal('0'),
            sgst_amount=Decimal('0'),
            igst_amount=Decimal('0'),
            total_gst_amount=Decimal('0'),
            
            # Status and control
            payment_status='paid',
            itc_eligible=False,
            
            # Audit fields
            notes=f"Credit note for payment {payment.reference_no}: {credit_note_data.get('credit_reason')}",
            created_by=current_user_id
        )
        
        session.add(credit_note)
        session.flush()
        
        # ===================================================================
        # STEP 4: CREATE CREDIT NOTE LINE ITEM WITH PROPER MEDICINE
        # ===================================================================
        
        # Get medicine name for line item
        if original_medicine_id == credit_medicine_id:
            # Using original medicine
            medicine_name = session.query(Medicine.medicine_name).filter_by(
                medicine_id=credit_medicine_id
            ).scalar() or "Credit Adjustment"
        else:
            medicine_name = f"Credit Note - {credit_note_data.get('reason_code', 'Payment Adjustment')}"
        
        credit_line = SupplierInvoiceLine(
            hospital_id=hospital_id,
            invoice_id=credit_note.invoice_id,
            
            # FIXED: Use proper medicine_id
            medicine_id=credit_medicine_id,
            medicine_name=medicine_name,
            
            # Negative quantities and amounts
            units=Decimal('1'),
            pack_purchase_price=-credit_amount,
            pack_mrp=Decimal('0'),
            units_per_pack=Decimal('1'),
            unit_price=-credit_amount,
            
            # Line totals
            taxable_amount=-credit_amount,
            line_total=-credit_amount,
            
            # GST amounts (zero for credit note)
            gst_rate=Decimal('0'),
            cgst_rate=Decimal('0'),
            sgst_rate=Decimal('0'),
            igst_rate=Decimal('0'),
            cgst=Decimal('0'),
            sgst=Decimal('0'),
            igst=Decimal('0'),
            total_gst=Decimal('0'),
            
            # Credit note specific fields
            is_free_item=False,
            discount_percent=Decimal('0'),
            discount_amount=Decimal('0'),
            
            # Audit
            created_by=current_user_id
        )
        
        session.add(credit_line)
        
        # ===================================================================
        # STEP 5: UPDATE PAYMENT REFERENCE (SAME AS BEFORE)
        # ===================================================================
        
        payment_notes = payment.notes or ''
        credit_reference = f"Credit Note: {credit_note.supplier_invoice_number}"
        
        if credit_reference not in payment_notes:
            payment.notes = f"{payment_notes}\n{credit_reference}".strip()
            payment.updated_by = current_user_id
            payment.updated_at = datetime.now(timezone.utc)
        
        session.flush()
        
        # ===================================================================
        # STEP 6: RETURN RESULT (SAME AS BEFORE)
        # ===================================================================
        
        result = {
            'credit_note_id': credit_note.invoice_id,
            'credit_note_number': credit_note.supplier_invoice_number,
            'credit_amount': float(credit_amount),
            'payment_id': payment_id,
            'supplier_id': payment.supplier_id,
            'supplier_name': supplier.supplier_name,
            'credit_note_date': credit_note_date.isoformat() if credit_note_date else None,
            'reason_code': credit_note_data.get('reason_code'),
            'medicine_used': medicine_name,
            'created_successfully': True
        }
        
        logger.info(f"Created credit note {credit_note.supplier_invoice_number} for payment {payment.reference_no}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating credit note from payment: {str(e)}")
        session.rollback()
        raise

# ===================================================================
# STEP 3: SYSTEM SETUP FUNCTION
# ===================================================================

def setup_credit_note_system(hospital_id, current_user_id):
    """
    One-time setup function to prepare system for credit notes
    Run this during system initialization or module deployment
    """
    try:
        logger.info(f"Setting up credit note system for hospital {hospital_id}")
        
        # Create credit adjustment medicine
        credit_medicine_id = create_credit_adjustment_medicine(
            hospital_id, current_user_id
        )
        
        logger.info(f"Credit adjustment medicine created: {credit_medicine_id}")
        
        return {
            'setup_successful': True,
            'credit_medicine_id': credit_medicine_id,
            'message': 'Credit note system setup completed successfully'
        }
        
    except Exception as e:
        logger.error(f"Error setting up credit note system: {str(e)}")
        return {
            'setup_successful': False,
            'error': str(e),
            'message': 'Credit note system setup failed'
        }

# ===================================================================
# STEP 4: ENHANCED FORM CONTROLLER WITH BETTER ERROR HANDLING
# ===================================================================

class SupplierCreditNoteController(FormController):
    """Enhanced controller with better error handling"""
    
    def __init__(self, payment_id):
        self.payment_id = payment_id
        super().__init__(
            form_class=SupplierCreditNoteForm,
            template_path='supplier/credit_note_form.html',
            success_url=self._get_success_url,
            success_message="Credit note created successfully",
            page_title="Create Credit Note",
            additional_context=self.get_additional_context
        )
    
    def get_form(self, *args, **kwargs):
        """Override to setup form defaults"""
        form = super().get_form(*args, **kwargs)
        
        if request.method == 'GET':
            try:
                self.setup_form_defaults(form)
            except Exception as e:
                current_app.logger.error(f"Error setting up form: {str(e)}")
                flash(f"Error loading payment details: {str(e)}", 'error')
        
        return form
    
    def process_form(self, form, *args, **kwargs):
        """Enhanced processing with better error handling"""
        try:
            from flask_login import current_user
            from app.services.supplier_service import create_supplier_credit_note_from_payment
            import uuid
            
            # Validate form data
            if not form.validate():
                raise ValueError("Form validation failed")
            
            # Prepare credit note data
            credit_note_data = {
                'payment_id': uuid.UUID(form.payment_id.data),
                'credit_note_number': form.credit_note_number.data,
                'credit_note_date': form.credit_note_date.data,
                'credit_amount': float(form.credit_amount.data),
                'reason_code': form.reason_code.data,
                'credit_reason': form.credit_reason.data,
                'branch_id': uuid.UUID(form.branch_id.data),
                'original_invoice_id': uuid.UUID(form.original_invoice_id.data) if form.original_invoice_id.data else None
            }
            
            # Create credit note
            result = create_supplier_credit_note_from_payment(
                hospital_id=current_user.hospital_id,
                credit_note_data=credit_note_data,
                current_user_id=current_user.user_id
            )
            
            return result
            
        except ValueError as ve:
            current_app.logger.warning(f"Validation error creating credit note: {str(ve)}")
            flash(f"Validation error: {str(ve)}", 'error')
            raise
        except Exception as e:
            current_app.logger.error(f"Error creating credit note: {str(e)}", exc_info=True)
            flash(f"Error creating credit note: {str(e)}", 'error')
            raise

# ===================================================================
# STEP 5: DEPLOYMENT SCRIPT
# ===================================================================

def deploy_credit_note_feature():
    """
    Deployment script to run when deploying credit note feature
    """
    print("Deploying Credit Note Feature...")
    
    # Step 1: Check database schema
    print("1. Checking database schema...")
    # Verify that SupplierInvoice has is_credit_note and credited_by_invoice_id columns
    
    # Step 2: Setup credit adjustment medicines for all hospitals
    print("2. Setting up credit adjustment medicines...")
    from app.services.database_service import get_db_session
    from app.models.master import Hospital
    
    with get_db_session() as session:
        hospitals = session.query(Hospital).all()
        
        for hospital in hospitals:
            try:
                setup_result = setup_credit_note_system(
                    hospital.hospital_id, 
                    'system_setup'
                )
                if setup_result['setup_successful']:
                    print(f"  ✓ Setup completed for {hospital.name}")
                else:
                    print(f"  ✗ Setup failed for {hospital.name}: {setup_result['error']}")
            except Exception as e:
                print(f"  ✗ Error setting up {hospital.name}: {str(e)}")
    
    print("3. Credit Note Feature Deployment Complete!")
    print("\nNext Steps:")
    print("- Test credit note creation")
    print("- Update user documentation")
    print("- Train users on new functionality")

if __name__ == "__main__":
    # Run this during deployment
    deploy_credit_note_feature()