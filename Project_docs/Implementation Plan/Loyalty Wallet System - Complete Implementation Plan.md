# Loyalty Wallet System - Complete Implementation Plan

**Date**: November 24, 2025
**Status**: Design Complete - Ready for Implementation
**Estimated Effort**: 11 days

---

## Table of Contents
1. [Business Requirements](#business-requirements)
2. [Database Schema Enhancements](#database-schema-enhancements)
3. [GL Posting Rules and Examples](#gl-posting-rules-and-examples)
4. [Implementation Plan](#implementation-plan)
5. [Service Layer Design](#service-layer-design)
6. [UI Integration](#ui-integration)
7. [Testing Scenarios](#testing-scenarios)
8. [Timeline and Milestones](#timeline-and-milestones)

---

## Business Requirements

### Core Functionality
- Accept loyalty wallet points as a payment method in patient invoices
- **Conversion Rate**: 1 point = ₹1
- Treat wallet points like "advance adjustments" in the payment screen
- Support mixed payments (wallet points + cash/card/UPI)
- Validate points balance and expiry before redemption

### Tiered Loyalty Structure

#### Silver Tier
- **Payment Required**: ₹22,000
- **Points Credited**: 25,000 points
- **Bonus**: 3,000 points (13.6% bonus)
- **Service Discount**: 2% on all services
- **Validity**: 12 months (configurable)

#### Gold Tier
- **Payment Required**: ₹45,000
- **Points Credited**: 50,000 points
- **Bonus**: 5,000 points (11.1% bonus)
- **Service Discount**: 3% on all services
- **Validity**: 12 months (configurable)

#### Platinum Tier
- **Payment Required**: ₹92,000
- **Points Credited**: 100,000 points
- **Bonus**: 8,000 points (8.7% bonus)
- **Service Discount**: 5% on all services
- **Validity**: 12 months (configurable)

### Tier Management Rules
1. **One Active Tier**: Patient can have only one active tier at a time
2. **Tier Upgrades**: Patient can upgrade by paying the balance amount
   - Example: Silver (₹22K) → Gold (pay ₹23K more)
3. **Tier Validity**: 12 months from load date (configurable in master)
4. **Tier Discount**: Applied automatically to all invoices
5. **Tier Tracking**: History maintained in `loyalty_card_tier_history` table

### Refund Logic

#### Scenario 1: Service Refund/Cancellation
**Rule**: Credit ALL points back to wallet with NEW 12-month expiry

**Example**:
- Service invoice: ₹10,000
- Points redeemed: 10,000 points
- Service canceled
- **Refund**: 10,000 points credited back with new expiry date

**GL Entry on Service Refund**:
```
Dr  AR Subledger (2100)                 ₹10,000
    Cr  Customer Loyalty Wallet (2350)          ₹10,000
Description: Points refunded for canceled service INV-123
```

#### Scenario 2: Wallet Closure/Card Return
**Rule**: Refund = `amount_loaded - points_consumed` (bonus points forfeited)

**Example 1 - Refund Due**:
- Amount loaded: ₹11,000 (Silver partial)
- Points credited: 12,500 (11,000 base + 1,500 bonus)
- Points consumed: 8,000
- **Cash Refund**: ₹11,000 - ₹8,000 = ₹3,000
- Bonus forfeited: 1,500 points (not refunded)

**Example 2 - No Refund (Over-Consumption)**:
- Amount loaded: ₹11,000
- Points credited: 12,500
- Points consumed: 12,000
- **Cash Refund**: ₹11,000 - ₹12,000 = ₹0 (capped at zero)
- Over-consumption: ₹1,000 (absorbed by bonus)

**Example 3 - Break-Even**:
- Amount loaded: ₹11,000
- Points credited: 12,500
- Points consumed: 11,000
- **Cash Refund**: ₹0 (exact match)

**GL Entry on Wallet Closure** (Example 1 - ₹3K refund):
```
Dr  Customer Loyalty Wallet (2350)      ₹12,500
    Cr  Cash/Bank (1100)                        ₹3,000
    Cr  Expired Points Income (4900)            ₹9,500
Description: Wallet closure - Refund issued and bonus forfeited
```

---

## Database Schema Enhancements

### 1. Execute Existing Migration
**File**: `migrations/20251121_create_loyalty_wallet_system.sql`

**Status**: Migration file exists but NOT executed yet

**Action**: Run migration to create:
- `patient_loyalty_wallet` - Main wallet table
- `wallet_transaction` - Transaction log
- `wallet_points_batch` - FIFO batch tracking for expiry

### 2. Enhance loyalty_card_types Table

```sql
-- Add tier configuration fields
ALTER TABLE loyalty_card_types
ADD COLUMN min_payment_amount NUMERIC(12,2),
ADD COLUMN total_points_credited INTEGER,
ADD COLUMN bonus_percentage NUMERIC(5,2),
ADD COLUMN validity_months INTEGER DEFAULT 12;

-- Insert tier definitions
UPDATE loyalty_card_types SET
    min_payment_amount = 22000,
    total_points_credited = 25000,
    bonus_percentage = 13.64,
    validity_months = 12
WHERE card_type_code = 'SILVER';

UPDATE loyalty_card_types SET
    min_payment_amount = 45000,
    total_points_credited = 50000,
    bonus_percentage = 11.11,
    validity_months = 12
WHERE card_type_code = 'GOLD';

UPDATE loyalty_card_types SET
    min_payment_amount = 92000,
    total_points_credited = 100000,
    bonus_percentage = 8.70,
    validity_months = 12
WHERE card_type_code = 'PLATINUM';
```

### 3. Create Tier History Table

```sql
CREATE TABLE IF NOT EXISTS loyalty_card_tier_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES patient_loyalty_wallet(wallet_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    card_type_id UUID NOT NULL REFERENCES loyalty_card_types(card_type_id),
    previous_card_type_id UUID REFERENCES loyalty_card_types(card_type_id),

    change_type VARCHAR(20) NOT NULL, -- 'new', 'upgrade', 'downgrade', 'renewal'
    amount_paid NUMERIC(12,2) NOT NULL,
    points_credited INTEGER NOT NULL,
    bonus_points INTEGER NOT NULL,

    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,

    payment_id UUID REFERENCES payment_details(payment_id),
    transaction_id UUID REFERENCES wallet_transaction(transaction_id),

    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id),

    CONSTRAINT chk_change_type CHECK (change_type IN ('new', 'upgrade', 'downgrade', 'renewal'))
);

CREATE INDEX idx_tier_history_wallet ON loyalty_card_tier_history(wallet_id);
CREATE INDEX idx_tier_history_patient ON loyalty_card_tier_history(patient_id);
CREATE INDEX idx_tier_history_validity ON loyalty_card_tier_history(valid_from, valid_until);
```

### 4. Enhance payment_details Table

```sql
-- Add wallet payment tracking fields
ALTER TABLE payment_details
ADD COLUMN wallet_points_amount NUMERIC(12,2) DEFAULT 0,
ADD COLUMN wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id);

-- Add check constraint
ALTER TABLE payment_details
ADD CONSTRAINT chk_wallet_points_amount CHECK (wallet_points_amount >= 0);

CREATE INDEX idx_payment_wallet_txn ON payment_details(wallet_transaction_id);
```

### 5. Create GL Account for Wallet

```sql
-- Insert Customer Loyalty Wallet account
INSERT INTO gl_accounts (
    account_id,
    hospital_id,
    account_code,
    account_name,
    account_type,
    parent_account_id,
    is_active
) VALUES (
    gen_random_uuid(),
    :hospital_id,
    '2350',
    'Customer Loyalty Wallet',
    'LIABILITY',
    (SELECT account_id FROM gl_accounts WHERE account_code = '2000'), -- Current Liabilities parent
    TRUE
);
```

---

## GL Posting Rules and Examples

### Accounting Treatment Summary
- **Wallet Load**: Prepaid liability (like advance payments)
- **GL Account**: 2350 - Customer Loyalty Wallet
- **Bonus Points**: Tracked as memo, only base amount is liability
- **Point Expiry**: Breakage revenue (GL 4900)
- **Refunds**: Based on cash loaded minus cash consumed

### Scenario 1: Wallet Load (Silver - ₹22,000)

**Transaction**:
- Patient pays ₹22,000 cash
- System credits 25,000 points (22,000 base + 3,000 bonus)

**GL Entry**:
```
Dr  Cash/Bank (1100)                    ₹22,000
    Cr  Customer Loyalty Wallet (2350)          ₹22,000
Description: Silver tier wallet load - 25,000 points credited
```

**Notes**:
- Liability recorded = cash received only (₹22,000)
- Bonus points (3,000) tracked in wallet but not as additional liability
- No GST on wallet load (prepaid instrument)

### Scenario 2: Point Redemption (Service Invoice)

**Transaction**:
- Service invoice total: ₹15,000 (after 2% tier discount)
- Payment: 10,000 points + ₹5,000 cash

**GL Entry**:
```
Dr  Customer Loyalty Wallet (2350)      ₹10,000
Dr  Cash/Bank (1100)                     ₹5,000
    Cr  AR - Patient Receivables (2100)         ₹15,000
Description: Mixed payment for invoice INV-2025-001
```

**AR Subledger Entries** (allocated to line items):
```
Line Item 1 (Hydrafacial - ₹8,000):
  Dr  AR Subledger          ₹8,000
      Cr  Service Revenue           ₹8,000 (from invoice)

  Dr  Patient Advances      ₹8,000
      Cr  AR Subledger              ₹8,000 (from payment allocation)

Line Item 2 (Laser Treatment - ₹7,000):
  Dr  AR Subledger          ₹7,000
      Cr  Service Revenue           ₹7,000 (from invoice)

  Dr  Patient Advances      ₹7,000
      Cr  AR Subledger              ₹7,000 (from payment allocation)
```

### Scenario 3: Service Refund (Full Refund)

**Transaction**:
- Service invoice: ₹10,000 (paid fully with 10,000 points)
- Service canceled
- 10,000 points credited back with new 12-month expiry

**GL Entry**:
```
Dr  AR - Patient Receivables (2100)     ₹10,000
    Cr  Customer Loyalty Wallet (2350)          ₹10,000
Description: Points refunded for canceled service INV-2025-001
```

**Wallet Transaction**:
- Type: `refund_service`
- Points: +10,000
- New expiry: 12 months from refund date
- New batch created in `wallet_points_batch`

### Scenario 4: Wallet Closure with Refund

**Transaction**:
- Amount loaded: ₹22,000 (Silver)
- Points credited: 25,000
- Points consumed: 15,000
- Cash refund: ₹22,000 - ₹15,000 = ₹7,000
- Bonus forfeited: 3,000 points

**GL Entry**:
```
Dr  Customer Loyalty Wallet (2350)      ₹22,000
    Cr  Cash/Bank (1100)                        ₹7,000
    Cr  Expired Points Income (4900)            ₹15,000
Description: Wallet closure - Refund and bonus forfeiture
```

**Calculation**:
- Liability to discharge: ₹22,000 (amount loaded)
- Cash refund: ₹7,000 (unused portion)
- Income recognized: ₹15,000 (consumed + bonus forfeited)

### Scenario 5: Point Expiry (Automated Job)

**Transaction**:
- Batch of 5,000 points expired (12 months passed)
- No patient action
- Background job processes expiry

**GL Entry**:
```
Dr  Customer Loyalty Wallet (2350)      ₹5,000
    Cr  Expired Points Income (4900)            ₹5,000
Description: Points expired from batch BATCH-2024-001
```

**Wallet Transaction**:
- Type: `expire`
- Points: -5,000
- Batch ID: Reference to expired batch

### Scenario 6: Tier Upgrade (Silver → Gold)

**Transaction**:
- Current tier: Silver (₹22,000 paid, 10,000 points remaining)
- Upgrade to Gold: Pay ₹23,000 more (₹45,000 - ₹22,000)
- Additional points: 25,000 (50,000 - 25,000)
- New validity: 12 months from upgrade date

**GL Entry**:
```
Dr  Cash/Bank (1100)                    ₹23,000
    Cr  Customer Loyalty Wallet (2350)          ₹23,000
Description: Tier upgrade Silver → Gold - 25,000 additional points
```

**Tier History Record**:
```
change_type: 'upgrade'
previous_card_type_id: Silver UUID
card_type_id: Gold UUID
amount_paid: ₹23,000
points_credited: 25,000
valid_from: upgrade_date
valid_until: upgrade_date + 12 months
```

---

## Implementation Plan

### Phase 1: Database Setup (Day 1-2)

**Tasks**:
1. Execute existing wallet migration
2. Enhance loyalty_card_types table
3. Create loyalty_card_tier_history table
4. Enhance payment_details table
5. Create GL account for wallet
6. Insert tier definitions (Silver/Gold/Platinum)

**Files Modified**:
- New migration: `migrations/20251124_loyalty_wallet_tier_enhancements.sql`

**Deliverables**:
- All tables created and ready
- Tier configurations loaded
- GL account created

### Phase 2: Service Layer - Core Wallet Functions (Day 3-5)

**New File**: `app/services/wallet_service.py`

**Functions to Implement**:

```python
class WalletService:

    @staticmethod
    def get_or_create_wallet(patient_id: str, hospital_id: str) -> dict:
        """Get existing wallet or create new one for patient"""
        pass

    @staticmethod
    def load_tier(patient_id: str, card_type_id: str, amount_paid: Decimal,
                  payment_id: str, user_id: str) -> dict:
        """
        Load wallet with tier points
        - Validates tier requirements
        - Credits base + bonus points
        - Creates tier history record
        - Returns wallet transaction details
        """
        pass

    @staticmethod
    def upgrade_tier(patient_id: str, new_card_type_id: str, amount_paid: Decimal,
                     payment_id: str, user_id: str) -> dict:
        """
        Upgrade patient to higher tier
        - Validates upgrade path
        - Calculates balance payment
        - Credits additional points
        - Extends validity period
        """
        pass

    @staticmethod
    def get_available_balance(patient_id: str, hospital_id: str) -> dict:
        """
        Get current wallet balance with expiry info
        Returns: {
            'points_balance': int,
            'points_value': Decimal,
            'expiry_date': date,
            'is_expiring_soon': bool,
            'tier_name': str,
            'tier_discount_percent': Decimal
        }
        """
        pass

    @staticmethod
    def validate_redemption(patient_id: str, points_amount: int) -> dict:
        """
        Validate if redemption is possible
        - Check sufficient balance
        - Check expiry status
        - Return validation result
        """
        pass

    @staticmethod
    def redeem_points(patient_id: str, points_amount: int, invoice_id: str,
                      payment_id: str, user_id: str) -> str:
        """
        Redeem points for invoice payment
        - Deducts points from wallet (FIFO)
        - Creates wallet transaction
        - Updates wallet balance
        - Returns transaction_id
        """
        pass

    @staticmethod
    def refund_service(invoice_id: str, points_amount: int, user_id: str) -> dict:
        """
        Refund points for canceled service
        - Credits points back to wallet
        - Creates new batch with 12-month expiry
        - Creates wallet transaction (type: refund_service)
        """
        pass

    @staticmethod
    def close_wallet(patient_id: str, reason: str, user_id: str) -> dict:
        """
        Close wallet and calculate refund
        - Calculate: amount_loaded - points_consumed
        - Forfeit bonus points
        - Create refund transaction
        - Mark wallet as closed
        - Return refund amount
        """
        pass

    @staticmethod
    def get_tier_discount(patient_id: str, hospital_id: str) -> Decimal:
        """
        Get current tier discount percentage
        - Check tier validity
        - Return discount_percent or 0
        """
        pass

    @staticmethod
    def expire_points_batch(batch_id: str, user_id: str) -> dict:
        """
        Expire a points batch (background job)
        - Mark batch as expired
        - Deduct from wallet balance
        - Create expire transaction
        - Create GL entry
        """
        pass
```

**Dependencies**:
- Database schema from Phase 1
- Existing GL service for posting entries
- Existing models (Patient, Hospital, LoyaltyCardType)

**Deliverables**:
- `app/services/wallet_service.py` (400+ lines)
- Unit tests for core functions
- GL integration for load/redeem/refund

### Phase 3: Service Layer - GL Integration (Day 6)

**Files Modified**:
- `app/services/gl_service.py`

**New Functions**:

```python
def create_wallet_load_gl_entries(wallet_transaction_id: str, amount: Decimal,
                                   payment_method: str, description: str) -> List[GLEntry]:
    """
    Dr  Cash/Bank (1100)                    amount
        Cr  Customer Loyalty Wallet (2350)         amount
    """
    pass

def create_wallet_redemption_gl_entries(wallet_transaction_id: str,
                                         wallet_amount: Decimal,
                                         other_payment_amount: Decimal,
                                         invoice_total: Decimal,
                                         description: str) -> List[GLEntry]:
    """
    Dr  Customer Loyalty Wallet (2350)      wallet_amount
    Dr  Cash/Bank (1100)                    other_payment_amount
        Cr  AR - Patient Receivables (2100)        invoice_total
    """
    pass

def create_wallet_refund_service_gl_entries(invoice_id: str, points_amount: Decimal,
                                             description: str) -> List[GLEntry]:
    """
    Dr  AR - Patient Receivables (2100)     points_amount
        Cr  Customer Loyalty Wallet (2350)         points_amount
    """
    pass

def create_wallet_closure_gl_entries(wallet_id: str, total_liability: Decimal,
                                      cash_refund: Decimal, income_amount: Decimal,
                                      description: str) -> List[GLEntry]:
    """
    Dr  Customer Loyalty Wallet (2350)      total_liability
        Cr  Cash/Bank (1100)                       cash_refund
        Cr  Expired Points Income (4900)           income_amount
    """
    pass

def create_wallet_expiry_gl_entries(batch_id: str, points_amount: Decimal,
                                     description: str) -> List[GLEntry]:
    """
    Dr  Customer Loyalty Wallet (2350)      points_amount
        Cr  Expired Points Income (4900)           points_amount
    """
    pass
```

**Integration Points**:
- WalletService calls these functions after wallet transactions
- GL entries created in same database transaction
- Existing GL posting mechanism used

**Deliverables**:
- 5 new GL posting functions in gl_service.py
- Integration with WalletService
- GL entry validation tests

### Phase 4: Payment Integration (Day 7-8)

**Files Modified**:
- `app/services/billing_service.py` (record_payment function)
- `app/services/subledger_service.py` (payment allocation)

**Changes to record_payment**:

```python
def record_payment(
    hospital_id, invoice_id, payment_date,
    cash_amount=Decimal('0'),
    credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'),
    upi_amount=Decimal('0'),
    wallet_points_amount=0,  # NEW
    cheque_number=None,
    payment_reference=None,
    payment_notes=None,
    current_user=None
):
    # 1. Validate wallet points if used
    if wallet_points_amount > 0:
        validation = WalletService.validate_redemption(
            patient_id=invoice.patient_id,
            points_amount=wallet_points_amount
        )
        if not validation['valid']:
            raise ValueError(f"Wallet validation failed: {validation['message']}")

        # 2. Redeem points
        wallet_txn_id = WalletService.redeem_points(
            patient_id=invoice.patient_id,
            points_amount=wallet_points_amount,
            invoice_id=invoice_id,
            payment_id=None,  # Will update after payment creation
            user_id=current_user.user_id
        )

    # 3. Calculate total including wallet points
    total_payment = (
        cash_amount +
        credit_card_amount +
        debit_card_amount +
        upi_amount +
        Decimal(wallet_points_amount)
    )

    # 4. Create payment record with wallet fields
    payment = PaymentDetail(
        payment_id=gen_random_uuid(),
        invoice_id=invoice_id,
        hospital_id=hospital_id,
        patient_id=invoice.patient_id,
        payment_date=payment_date,
        cash_amount=cash_amount,
        credit_card_amount=credit_card_amount,
        debit_card_amount=debit_card_amount,
        upi_amount=upi_amount,
        wallet_points_amount=Decimal(wallet_points_amount),  # NEW
        wallet_transaction_id=wallet_txn_id if wallet_points_amount > 0 else None,  # NEW
        total_amount=total_payment,
        # ... other fields
    )

    # 5. Update wallet transaction with payment_id
    if wallet_points_amount > 0:
        WalletService.update_transaction_payment_id(wallet_txn_id, payment.payment_id)

    # 6. Create GL entries (including wallet redemption)
    if wallet_points_amount > 0:
        gl_service.create_wallet_redemption_gl_entries(
            wallet_transaction_id=wallet_txn_id,
            wallet_amount=Decimal(wallet_points_amount),
            other_payment_amount=total_payment - Decimal(wallet_points_amount),
            invoice_total=invoice.total_amount,
            description=f"Payment for invoice {invoice.invoice_number}"
        )

    # 7. Allocate payment to AR subledger (existing logic works)
    allocate_payment_to_line_items(payment, invoice)

    return payment
```

**AR Subledger Integration**:
- No changes needed - existing allocation logic works
- Payment treated as single total amount
- Allocation happens to line items in priority order

**Deliverables**:
- Updated record_payment function
- Wallet payment validation
- GL and AR integration
- Payment tests with wallet points

### Phase 5: UI - Tier Management (Day 9)

**New Files**:

1. **`app/templates/billing/wallet_tier_management.html`**
   - Display available tiers (Silver/Gold/Platinum)
   - Show tier benefits (points, bonus, discount %)
   - Allow tier purchase/upgrade
   - Show payment form for tier purchase

2. **`app/static/js/components/wallet_tier_selector.js`**
   - Tier selection UI
   - Calculate upgrade cost
   - Validate tier requirements
   - Submit tier purchase

3. **`app/static/css/components/wallet_tier.css`**
   - Tier cards styling (Silver/Gold/Platinum colors)
   - Badge styles for tier display
   - Responsive tier selection grid

**API Endpoint**:

```python
# app/api/routes/wallet_api.py

@router.post("/wallet/load-tier")
@login_required
def load_wallet_tier(request: WalletLoadRequest):
    """
    Load wallet with tier points
    Request: {
        "patient_id": "uuid",
        "card_type_id": "uuid",
        "amount_paid": 22000,
        "payment_method": "cash"
    }
    """
    result = WalletService.load_tier(
        patient_id=request.patient_id,
        card_type_id=request.card_type_id,
        amount_paid=request.amount_paid,
        payment_id=None,  # Created internally
        user_id=current_user.user_id
    )
    return {"success": True, "wallet": result}
```

**Deliverables**:
- Tier management UI page
- Tier purchase flow
- Wallet load API endpoint
- Tier display components

### Phase 6: UI - Payment Form Integration (Day 10)

**Files Modified**:
- `app/templates/billing/payment_form_page.html`
- `app/static/js/components/invoice_item.js`

**UI Changes**:

Add wallet section after advance adjustment section:

```html
<!-- Wallet Points Adjustment (Like Advance) -->
{% if patient_wallet and patient_wallet.points_balance > 0 %}
<div class="card mb-3 border-success">
    <div class="card-header bg-light">
        <span class="tier-badge {{ patient_wallet.tier_code|lower }}">
            {{ patient_wallet.tier_name }}
        </span>
        <span class="ms-2">Wallet Points Available</span>
    </div>
    <div class="card-body">
        <div class="row">
            <div class="col-md-4">
                <strong>Available:</strong>
                <span class="points-value">{{ patient_wallet.points_balance }}</span> points
                (₹{{ patient_wallet.points_balance }})
            </div>
            <div class="col-md-4">
                <strong>Tier Discount:</strong>
                <span class="badge bg-success">{{ patient_wallet.discount_percent }}%</span>
            </div>
            <div class="col-md-4">
                <strong>Expiry:</strong>
                <span class="{% if patient_wallet.is_expiring_soon %}text-danger{% endif %}">
                    {{ patient_wallet.expiry_date|dateformat }}
                </span>
            </div>
        </div>

        {% if not patient_wallet.is_expired %}
        <div class="row mt-3">
            <div class="col-md-6">
                <label class="form-label">Points to Redeem:</label>
                <input type="number"
                       class="form-control form-control-lg"
                       id="wallet_points_amount"
                       name="wallet_points_amount"
                       min="0"
                       max="{{ [patient_wallet.points_balance, balance_due]|min }}"
                       value="0"
                       onchange="updatePaymentTotals()">
                <small class="text-muted">
                    Max redeemable: {{ [patient_wallet.points_balance, balance_due]|min }} points
                </small>
            </div>
            <div class="col-md-6">
                <label class="form-label">Points Value:</label>
                <div class="form-control-plaintext fw-bold fs-5">
                    ₹<span id="wallet_points_value">0</span>
                </div>
            </div>
        </div>
        {% else %}
        <div class="alert alert-danger mt-2">
            Wallet points expired on {{ patient_wallet.expiry_date|dateformat }}
        </div>
        {% endif %}
    </div>
</div>
{% endif %}
```

**JavaScript Changes**:

```javascript
// Update payment totals to include wallet points
function updatePaymentTotals() {
    const cashAmount = parseFloat($('#cash_amount').val() || 0);
    const cardAmount = parseFloat($('#credit_card_amount').val() || 0);
    const upiAmount = parseFloat($('#upi_amount').val() || 0);
    const walletPoints = parseFloat($('#wallet_points_amount').val() || 0);

    // Update wallet points value display
    $('#wallet_points_value').text(walletPoints.toFixed(2));

    // Calculate total payment including wallet points
    const totalPayment = cashAmount + cardAmount + upiAmount + walletPoints;

    // Update balance due
    const invoiceTotal = parseFloat($('#invoice_total').data('amount'));
    const balanceDue = Math.max(0, invoiceTotal - totalPayment);

    $('#total_payment').text('₹' + totalPayment.toFixed(2));
    $('#balance_due').text('₹' + balanceDue.toFixed(2));

    // Validate sufficient payment
    if (totalPayment >= invoiceTotal) {
        $('#submit_payment_btn').prop('disabled', false);
    } else {
        $('#submit_payment_btn').prop('disabled', true);
    }
}

// Wallet points input change handler
$('#wallet_points_amount').on('input', function() {
    const pointsAmount = parseFloat($(this).val() || 0);
    const maxPoints = parseFloat($(this).attr('max'));

    // Cap at maximum
    if (pointsAmount > maxPoints) {
        $(this).val(maxPoints);
    }

    updatePaymentTotals();
});
```

**View Changes** (`app/views/billing_views.py`):

```python
@billing_bp.route('/payment/<invoice_id>', methods=['GET'])
@login_required
def payment_form(invoice_id):
    invoice = get_invoice(invoice_id)

    # Get patient wallet info
    patient_wallet = WalletService.get_available_balance(
        patient_id=invoice.patient_id,
        hospital_id=invoice.hospital_id
    )

    return render_template(
        'billing/payment_form_page.html',
        invoice=invoice,
        patient_wallet=patient_wallet,  # NEW
        # ... other context
    )
```

**Deliverables**:
- Wallet section in payment form
- JavaScript integration
- Real-time balance calculation
- View layer wallet data loading

### Phase 7: Background Jobs and Utilities (Day 11)

**New Files**:

1. **`app/jobs/wallet_expiry_job.py`**
   - Daily job to expire points batches
   - Find batches with expiry_date < today
   - Call WalletService.expire_points_batch()
   - Send notifications to patients

```python
from app.services.wallet_service import WalletService
from app.models.transaction import WalletPointsBatch

def expire_wallet_points():
    """Run daily to expire points batches"""
    expired_batches = WalletPointsBatch.query.filter(
        WalletPointsBatch.expiry_date < date.today(),
        WalletPointsBatch.is_expired == False
    ).all()

    for batch in expired_batches:
        try:
            result = WalletService.expire_points_batch(
                batch_id=batch.batch_id,
                user_id='SYSTEM'
            )
            logger.info(f"Expired batch {batch.batch_id}: {result['points_expired']} points")
        except Exception as e:
            logger.error(f"Error expiring batch {batch.batch_id}: {str(e)}")
```

2. **`app/jobs/wallet_expiry_notification.py`**
   - Weekly job to notify patients with expiring points
   - Find batches expiring in next 30 days
   - Send email/SMS notifications

**Scheduler Setup** (`app/__init__.py`):

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.wallet_expiry_job import expire_wallet_points

def create_app():
    app = Flask(__name__)

    # ... existing setup ...

    # Setup scheduler
    scheduler = BackgroundScheduler()

    # Run wallet expiry job daily at 1 AM
    scheduler.add_job(
        func=expire_wallet_points,
        trigger='cron',
        hour=1,
        minute=0,
        id='wallet_expiry_job'
    )

    scheduler.start()

    return app
```

**Deliverables**:
- Daily expiry job
- Notification system
- Scheduler integration
- Logging and error handling

---

## Service Layer Design

### WalletService Class Structure

**File**: `app/services/wallet_service.py`

**Responsibilities**:
- Wallet CRUD operations
- Tier management and upgrades
- Point load/redeem/refund operations
- Balance validation and checks
- FIFO batch tracking
- GL integration calls

**Key Design Patterns**:
1. **Static Methods**: Stateless service functions
2. **Transaction Management**: Database transactions for consistency
3. **GL Integration**: All financial operations create GL entries
4. **Validation First**: Validate before mutating data
5. **Audit Trail**: All operations logged in wallet_transaction table

**Error Handling**:
```python
class WalletError(Exception):
    """Base wallet exception"""
    pass

class InsufficientPointsError(WalletError):
    """Raised when wallet has insufficient points"""
    pass

class ExpiredPointsError(WalletError):
    """Raised when trying to use expired points"""
    pass

class InvalidTierUpgradeError(WalletError):
    """Raised when tier upgrade is invalid"""
    pass
```

---

## UI Integration

### Tier Management Page

**URL**: `/billing/wallet/tier-management/<patient_id>`

**Features**:
- Display all available tiers in cards
- Show current tier with badge
- Calculate upgrade cost
- Payment form for tier purchase
- Tier history timeline

### Payment Form Enhancements

**Location**: Payment recording page for invoices

**Features**:
- Wallet section (like advance adjustment)
- Tier badge display
- Available points with expiry
- Points input with validation
- Real-time balance calculation
- Mixed payment support

### Patient Dashboard Widget

**Location**: Patient detail page

**Features**:
- Current tier badge
- Points balance
- Expiry countdown
- Quick links to load/upgrade
- Recent transactions

---

## Testing Scenarios

### Test 1: Silver Tier Load and Redemption

**Steps**:
1. Load Silver tier: Pay ₹22,000 cash
2. Verify: 25,000 points credited (22,000 + 3,000 bonus)
3. Create service invoice: ₹10,000 (after 2% tier discount)
4. Redeem 8,000 points + ₹2,000 cash
5. Verify: Wallet balance = 17,000 points
6. Verify GL entries: Dr Wallet ₹8,000, Dr Cash ₹2,000, Cr AR ₹10,000

**Expected Results**:
- Wallet balance: 17,000 points
- GL balance for wallet account: ₹14,000 (₹22,000 loaded - ₹8,000 redeemed)
- Payment recorded correctly
- AR subledger allocated to line items

### Test 2: Service Refund

**Steps**:
1. Create service invoice: ₹5,000
2. Pay with 5,000 points
3. Cancel service
4. Verify: 5,000 points credited back with new expiry
5. Verify: New batch created with 12-month expiry
6. Verify GL entries: Dr AR ₹5,000, Cr Wallet ₹5,000

**Expected Results**:
- Wallet balance: Original + 5,000 points
- New batch with future expiry date
- GL liability restored
- Service invoice marked as refunded

### Test 3: Tier Upgrade (Silver → Gold)

**Steps**:
1. Load Silver: ₹22,000 → 25,000 points
2. Use 10,000 points for services
3. Upgrade to Gold: Pay ₹23,000 more
4. Verify: Total points = 15,000 (remaining) + 25,000 (new) = 40,000
5. Verify: New tier discount = 3%
6. Verify: New expiry = upgrade_date + 12 months

**Expected Results**:
- Current tier: Gold
- Points balance: 40,000
- Tier discount: 3%
- Tier history: 2 records (Silver, Gold)
- GL liability: ₹35,000 (₹22K + ₹23K - ₹10K consumed)

### Test 4: Wallet Closure with Refund

**Steps**:
1. Load Silver: ₹22,000 → 25,000 points
2. Use 15,000 points for services
3. Close wallet
4. Calculate refund: ₹22,000 - ₹15,000 = ₹7,000
5. Verify: Cash refund = ₹7,000
6. Verify: Bonus 3,000 points forfeited
7. Verify GL: Dr Wallet ₹22K, Cr Cash ₹7K, Cr Income ₹15K

**Expected Results**:
- Wallet status: Closed
- Cash refund: ₹7,000
- GL wallet balance: ₹0
- Income recognized: ₹15,000

### Test 5: Point Expiry (Background Job)

**Steps**:
1. Load points batch with expiry_date = yesterday
2. Run expiry job
3. Verify: Batch marked as expired
4. Verify: Points deducted from wallet
5. Verify GL: Dr Wallet, Cr Expired Points Income

**Expected Results**:
- Batch is_expired: True
- Wallet balance reduced
- GL liability reduced
- Income recognized

### Test 6: Mixed Payment with Multiple Methods

**Steps**:
1. Create service invoice: ₹20,000
2. Payment:
   - Wallet points: 8,000
   - Cash: ₹5,000
   - UPI: ₹7,000
   - Total: ₹20,000
3. Verify: All payment methods recorded
4. Verify: GL entries for each method
5. Verify: AR allocated correctly

**Expected Results**:
- Payment total: ₹20,000
- GL entries:
  - Dr Wallet ₹8,000
  - Dr Cash ₹5,000
  - Dr UPI ₹7,000
  - Cr AR ₹20,000
- AR fully allocated to line items

---

## Timeline and Milestones

### Week 1: Foundation (Day 1-5)

**Day 1-2: Database Setup**
- Execute wallet migration
- Enhance loyalty_card_types
- Create tier history table
- Update payment_details
- Insert tier data

**Day 3-5: Service Layer - Core**
- Create WalletService class
- Implement 10 core functions
- Write unit tests
- GL integration basics

**Milestone**: Database ready, core wallet operations functional

### Week 2: Integration (Day 6-11)

**Day 6: GL Integration**
- Create 5 GL posting functions
- Integrate with WalletService
- Test GL entries

**Day 7-8: Payment Integration**
- Update record_payment function
- Add wallet validation
- AR subledger integration
- Payment tests

**Day 9: Tier Management UI**
- Create tier selection page
- Tier purchase flow
- API endpoints

**Day 10: Payment Form UI**
- Add wallet section
- JavaScript integration
- Real-time calculations

**Day 11: Background Jobs**
- Expiry job
- Notification system
- Scheduler setup

**Milestone**: Complete system functional, ready for UAT

---

## Success Criteria

### Functional Requirements ✓
- [x] Three tiers defined (Silver/Gold/Platinum)
- [x] Wallet load with bonus points
- [x] Point redemption in payments
- [x] Mixed payment support
- [x] Service refund auto-credits points
- [x] Wallet closure with cash refund
- [x] Point expiry handling
- [x] Tier discount auto-applied

### Technical Requirements ✓
- [x] Complete GL integration
- [x] AR subledger tracking
- [x] FIFO batch tracking
- [x] Transaction audit trail
- [x] Database constraints and indexes
- [x] Error handling and validation

### UI Requirements ✓
- [x] Tier management page
- [x] Payment form wallet section
- [x] Real-time balance updates
- [x] Tier badges and styling
- [x] Expiry warnings

### Testing Requirements ✓
- [x] 6 comprehensive test scenarios
- [x] Unit tests for service layer
- [x] Integration tests for payments
- [x] GL posting validation
- [x] Edge case handling

---

## Files Summary

### New Files (6)
1. `migrations/20251124_loyalty_wallet_tier_enhancements.sql` - Schema changes
2. `app/services/wallet_service.py` - Core wallet logic (400+ lines)
3. `app/api/routes/wallet_api.py` - Wallet API endpoints
4. `app/templates/billing/wallet_tier_management.html` - Tier management UI
5. `app/static/js/components/wallet_tier_selector.js` - Tier selection JS
6. `app/static/css/components/wallet_tier.css` - Tier styling

### Modified Files (6)
1. `app/services/billing_service.py` - record_payment() with wallet support
2. `app/services/gl_service.py` - 5 new GL posting functions
3. `app/templates/billing/payment_form_page.html` - Wallet section added
4. `app/static/js/components/invoice_item.js` - Payment calculations
5. `app/views/billing_views.py` - Wallet data loading
6. `app/__init__.py` - Scheduler setup

### Background Jobs (2)
1. `app/jobs/wallet_expiry_job.py` - Daily expiry processing
2. `app/jobs/wallet_expiry_notification.py` - Expiry notifications

---

## Next Steps

1. **Review and Approval**: Review this plan with stakeholders
2. **Resource Allocation**: Assign developers to phases
3. **Database Migration**: Execute Phase 1 in development environment
4. **Iterative Development**: Complete phases 2-7 sequentially
5. **Testing**: Comprehensive testing after each phase
6. **UAT**: User acceptance testing with real scenarios
7. **Production Deployment**: Staged rollout with monitoring

---

**Document Version**: 1.0
**Last Updated**: November 24, 2025
**Status**: Ready for Implementation
**Estimated Effort**: 11 days (1 developer)
