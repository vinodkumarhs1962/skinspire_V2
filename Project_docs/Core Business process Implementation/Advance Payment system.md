# Advance Payment System - Design and Implementation

## 1. Business Requirements

1. **Patient Advance Payments**: Patients can make advance payments that will be used later against invoices
2. **Excess Payment Handling**: Any excess payment during invoice settlement becomes an advance
3. **Selective Application**: Billing staff can choose which invoices to apply advances against
4. **Payment Ledger**: Advances must be tracked through a payment ledger

## 2. System Design

### 2.1 Data Models

The system leverages existing database models:

* **PatientAdvancePayment**: Stores advance payment details
* **AdvanceAdjustment**: Tracks how advance payments are applied to invoices
* **PaymentDetail**: Tracks individual payments for invoices
* **InvoiceHeader**: Stores invoice details

### 2.2 Workflow Design

#### Creating Advance Payments:
1. User selects a patient
2. User enters payment details (amount, payment method, date)
3. System records the payment in PatientAdvancePayment table
4. System creates appropriate GL entries for accounting

#### Excess Payment Handling:
1. When a payment exceeds invoice amount, system identifies excess
2. Excess amount is automatically recorded as an advance payment 
3. Original payment record is properly allocated

#### Using Advance Payments:
1. When settling an invoice, available advance balance is displayed
2. User can apply any amount up to the advance balance
3. System deducts from advance balance and records against the invoice

#### Tracking & Reporting:
1. Advance balance is visible on patient profile
2. Payment ledger shows all advance transactions
3. Reports track advances by patient, date range, etc.

### 2.3 System Components

#### Service Layer:
* `create_advance_payment()`: Records a new advance payment
* `get_patient_advance_balance()`: Checks available balance
* `apply_advance_payment()`: Uses advance against an invoice
* `handle_excess_payment()`: Converts excess to advance
* `get_patient_advance_payments()`: Lists all advances for a patient

#### View Controllers:
* `create_advance_payment_view()`: Form to record an advance payment
* `view_patient_advances()`: Display advance payment history
* `apply_advance_view()`: Interface for applying advances to invoices

#### UI Components:
* Advance payment form
* Advance balance display 
* Advance payment history table
* Advance application interface

## 3. Implementation

### 3.1 Service Layer

The service layer implements the core business logic for handling advance payments:

```python
def create_advance_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    amount: Decimal,
    payment_date: datetime,
    cash_amount: Decimal = Decimal('0'),
    credit_card_amount: Decimal = Decimal('0'),
    debit_card_amount: Decimal = Decimal('0'),
    upi_amount: Decimal = Decimal('0'),
    card_number_last4: Optional[str] = None,
    card_type: Optional[str] = None,
    upi_id: Optional[str] = None,
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """Creates a new advance payment for a patient"""
    # Implementation details...
```

```python
def apply_advance_payment(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    adjustment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """Applies advance payment to an invoice"""
    # Implementation details...
```

```python
def handle_excess_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_id: uuid.UUID,
    excess_amount: Decimal,
    payment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """Handles excess payment by creating an advance payment"""
    # Implementation details...
```

### 3.2 View Controllers

The view controllers handle the user interface for advance payments:

```python
@billing_views_bp.route('/advance/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def create_advance_payment_view():
    """View for creating a new advance payment"""
    # Implementation details...
```

```python
@billing_views_bp.route('/advance/patient/<uuid:patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def view_patient_advances(patient_id):
    """View patient's advance payment history"""
    # Implementation details...
```

```python
@billing_views_bp.route('/advance/apply/<uuid:invoice_id>', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'update')
def apply_advance_view(invoice_id):
    """View for applying advance payment to an invoice"""
    # Implementation details...
```

### 3.3 UI Templates

The user interface templates provide a clean, intuitive interface for working with advance payments:

1. **advance_payment.html**: Form for recording advance payments
2. **patient_advances.html**: View of patient's advance payment history
3. **apply_advance.html**: Form for applying advance to an invoice
4. **payment_form_page.html**: Updated to show available advance balance

### 3.4 Integration Points

The advance payment system integrates with several existing components:

1. **Invoice System**: When creating or viewing invoices
2. **Payment Processing**: When handling payments and excess amounts
3. **Patient Records**: For displaying patient advance balances
4. **GL System**: For accounting entries related to advances

## 4. Testing Strategy

### 4.1 Unit Tests

* Test `create_advance_payment()` with different payment methods
* Test `get_patient_advance_balance()` with various scenarios
* Test `apply_advance_payment()` with valid and invalid amounts
* Test `handle_excess_payment()` with different excess amounts

### 4.2 Integration Tests

* Test advance payment creation through UI
* Test applying advance payments to invoices
* Test excess payment handling during invoice payment
* Test advance payment history display

### 4.3 Edge Cases

* Test with zero or negative advance amounts
* Test with advance greater than invoice amount
* Test with multiple advances for the same patient
* Test with advances in different currencies

## 5. Security Considerations

1. All advance payment operations require proper authorization
2. Transactions are logged for audit purposes
3. Only authorized users can view or modify advance payments
4. Input validation prevents SQL injection and other attacks

## 6. Implementation Phases

### Phase 1: Backend Service Functions
* Implement core service functions for advance payment handling
* Create tests to verify functionality

### Phase 2: View Controllers
* Implement view functions for creating and managing advances
* Connect view functions to service layer

### Phase 3: Frontend Templates
* Create new templates for advance management
* Update existing templates to include advance payment options

### Phase 4: Integration & Testing
* Integrate advance payment with existing invoice/payment workflow
* Comprehensive testing of the full advance payment lifecycle

## 7. Next Steps

1. **Enhanced Reporting**: Create detailed reports for advance payments and adjustments
2. **Advance Payment Refunds**: Implement functionality to refund unused advances
3. **Patient Portal Integration**: Allow patients to view their advance balances online
4. **Multi-currency Support**: Enhance the system to handle advances in multiple currencies
5. **Automatic Application**: Add option for automatic application of advances to oldest invoices
6. **Email Notifications**: Send notifications when advances are applied or about to expire

## 8. Conclusion

The Advance Payment System provides a robust solution for managing patient advance payments, enhancing the clinic's financial operations. By leveraging existing database models and integrating smoothly with the current billing system, it minimizes technical debt while providing significant business value.

The implementation is designed to be backward compatible with existing functionality while adding new capabilities that improve the user experience and financial management.