# Wallet Payment Integration - Implementation Plan

**Date**: November 24, 2025
**Status**: Ready for Implementation
**Estimated Time**: 2-3 hours

---

## Overview

Integrate wallet point redemption into the invoice payment flow, allowing patients to:
1. See their wallet balance on payment page
2. Enter points to redeem against invoice
3. Submit mixed payment (wallet + cash/card)
4. See wallet payment reflected in invoice

---

## Components to Modify

### 1. Backend - View Layer (`billing_views.py`)

**Function**: `payment_form_view(invoice_id)`

**Current**: Fetches invoice, advance balance, related invoices
**Need to Add**: Fetch wallet balance for patient

```python
# Add after advance_balance query
wallet_balance = None
wallet_info = None
if invoice.patient_id:
    try:
        from app.services.wallet_service import WalletService
        wallet_data = WalletService.get_available_balance(
            patient_id=str(invoice.patient_id),
            hospital_id=str(invoice.hospital_id)
        )
        if wallet_data and wallet_data.get('points_balance', 0) > 0:
            wallet_balance = wallet_data['points_balance']
            wallet_info = {
                'points': wallet_balance,
                'value': wallet_balance,  # 1:1 ratio
                'tier': wallet_data.get('tier_name', 'Member'),
                'tier_code': wallet_data.get('tier_code', ''),
                'discount_percent': wallet_data.get('tier_discount_percent', 0)
            }
    except Exception as e:
        logger.warning(f"Could not fetch wallet for patient {invoice.patient_id}: {str(e)}")
```

**Pass to Template**:
```python
return render_template(
    'billing/payment_form_page.html',
    invoice=invoice,
    advance_balance=advance_balance,
    wallet_info=wallet_info,  # NEW
    related_invoices=related_invoices,
    ...
)
```

---

### 2. Backend - Payment Processing (`billing_service.py`)

**Function**: `record_payment()` or `record_invoice_payment()`

**Current Parameters**: invoice_id, payment_mode, amount, reference, etc.
**Need to Add**: `wallet_points_amount` (optional)

```python
def record_payment(
    invoice_id: uuid.UUID,
    payment_mode: str,
    amount_paid: Decimal,
    reference_number: Optional[str] = None,
    wallet_points_amount: Optional[Decimal] = None,  # NEW
    **kwargs
) -> Dict:
    """
    Record payment for invoice with optional wallet redemption
    """
    # ... existing validation ...

    # Handle wallet redemption if provided
    wallet_transaction_id = None
    if wallet_points_amount and wallet_points_amount > 0:
        from app.services.wallet_service import WalletService

        # Redeem points
        redemption_result = WalletService.redeem_points(
            patient_id=str(invoice.patient_id),
            hospital_id=str(invoice.hospital_id),
            points_to_redeem=int(wallet_points_amount),
            invoice_id=invoice_id,
            invoice_number=invoice.invoice_number,
            user_id=current_user_id
        )

        if not redemption_result['success']:
            raise ValueError(f"Wallet redemption failed: {redemption_result['message']}")

        wallet_transaction_id = redemption_result['transaction_id']

        # Create GL entries for wallet redemption
        from app.services.wallet_gl_service import WalletGLService
        WalletGLService.create_wallet_redemption_gl_entries(
            wallet_transaction_id=wallet_transaction_id,
            current_user_id=current_user_id,
            session=session
        )

    # Create PaymentDetail record
    payment = PaymentDetail(
        invoice_id=invoice_id,
        payment_mode=payment_mode,
        amount_paid=amount_paid,
        wallet_transaction_id=wallet_transaction_id,  # Link to wallet transaction
        ...
    )

    # Total payment = cash/card + wallet
    total_payment = amount_paid + (wallet_points_amount or Decimal('0'))

    # Update invoice balance
    invoice.amount_paid = invoice.amount_paid + total_payment
    invoice.balance_due = invoice.grand_total - invoice.amount_paid

    # ... rest of payment logic ...
```

---

### 3. Frontend - Payment Form HTML (`payment_form_page.html`)

**Location**: After advance payment section (line 292), replace hidden loyalty section

```html
<!-- Wallet Points Section -->
{% if wallet_info and wallet_info.points > 0 %}
<div id="wallet-points-info" class="bg-white dark:bg-gray-800 shadow-md rounded-lg p-6 mb-6">
    <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-gray-800 dark:text-white">
            <i class="fas fa-wallet text-indigo-600"></i> Wallet Points
        </h2>
        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-{{ wallet_info.tier_code|lower }}-100 text-{{ wallet_info.tier_code|lower }}-800">
            {{ wallet_info.tier }}
        </span>
    </div>

    <div class="space-y-3 mb-4">
        <div class="flex justify-between items-center">
            <span class="text-gray-700 dark:text-gray-300">Available Points:</span>
            <span class="font-bold text-indigo-600 dark:text-indigo-400">
                {{ "{:,}".format(wallet_info.points) }} points
            </span>
        </div>
        <div class="flex justify-between items-center">
            <span class="text-gray-700 dark:text-gray-300">Point Value:</span>
            <span class="font-bold text-green-600 dark:text-green-400">
                {{ invoice.currency_code }} {{ "{:,.2f}".format(wallet_info.value) }}
            </span>
        </div>
        <div class="flex justify-between items-center text-sm">
            <span class="text-gray-600 dark:text-gray-400">Loyalty Discount:</span>
            <span class="text-gray-600 dark:text-gray-400">{{ wallet_info.discount_percent }}%</span>
        </div>
    </div>

    <form method="POST" action="{{ url_for('billing_views.record_invoice_payment', invoice_id=invoice.invoice_id) }}" id="wallet-payment-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="use_wallet" value="true">

        <div class="mb-4">
            <label class="block text-gray-700 dark:text-gray-300 text-sm font-bold mb-2" for="wallet_points_amount">
                Points to Redeem
            </label>
            <input type="number" id="wallet_points_amount" name="wallet_points_amount"
                min="1" max="{{ [wallet_info.points, invoice.balance_due|int]|min }}" step="1"
                placeholder="Enter points (1 point = ₹1)"
                class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 dark:text-gray-300 dark:bg-gray-700 leading-tight focus:outline-none focus:shadow-outline">
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Maximum: {{ [wallet_info.points, invoice.balance_due|int]|min|format_number }} points
                (Balance Due: {{ invoice.currency_code }} {{ "{:,.2f}".format(invoice.balance_due) }})
            </p>
        </div>

        <!-- Real-time calculation display -->
        <div id="wallet-calculation" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 mb-4 hidden">
            <div class="flex justify-between text-sm mb-2">
                <span class="text-gray-600 dark:text-gray-400">Points:</span>
                <span id="calc-points" class="font-medium">0</span>
            </div>
            <div class="flex justify-between text-sm mb-2">
                <span class="text-gray-600 dark:text-gray-400">Wallet Payment:</span>
                <span id="calc-wallet-amount" class="font-medium text-green-600">₹0.00</span>
            </div>
            <div class="flex justify-between text-sm mb-2 border-t border-gray-300 dark:border-gray-600 pt-2">
                <span class="text-gray-700 dark:text-gray-300 font-semibold">Remaining Due:</span>
                <span id="calc-remaining" class="font-bold text-orange-600">₹{{ "{:,.2f}".format(invoice.balance_due) }}</span>
            </div>
        </div>

        <div class="flex justify-between items-center">
            <a href="{{ url_for('wallet.wallet_dashboard', patient_id=invoice.patient_id) }}"
               class="text-blue-600 hover:text-blue-800 dark:text-blue-400 text-sm"
               target="_blank">
                <i class="fas fa-external-link-alt"></i> View Wallet
            </a>
            <button type="submit" class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline">
                <i class="fas fa-check-circle"></i> Use Points
            </button>
        </div>
    </form>

    <!-- JavaScript for real-time calculation -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const pointsInput = document.getElementById('wallet_points_amount');
            const calcDiv = document.getElementById('wallet-calculation');
            const calcPoints = document.getElementById('calc-points');
            const calcWalletAmount = document.getElementById('calc-wallet-amount');
            const calcRemaining = document.getElementById('calc-remaining');

            const balanceDue = {{ invoice.balance_due|float }};
            const maxPoints = {{ [wallet_info.points, invoice.balance_due|int]|min }};

            if (pointsInput) {
                pointsInput.addEventListener('input', function() {
                    const points = parseInt(this.value) || 0;

                    if (points > 0 && points <= maxPoints) {
                        // Show calculation
                        calcDiv.classList.remove('hidden');

                        // Update values (1 point = ₹1)
                        const walletPayment = points;
                        const remaining = Math.max(0, balanceDue - walletPayment);

                        calcPoints.textContent = points.toLocaleString();
                        calcWalletAmount.textContent = '₹' + walletPayment.toFixed(2);
                        calcRemaining.textContent = '₹' + remaining.toFixed(2);

                        // Validate
                        if (points > maxPoints) {
                            this.value = maxPoints;
                        }
                    } else {
                        calcDiv.classList.add('hidden');
                    }
                });
            }
        });
    </script>
</div>
{% else %}
<div id="wallet-points-info" class="bg-white dark:bg-gray-800 shadow-md rounded-lg p-6 mb-6">
    <h2 class="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        <i class="fas fa-wallet text-gray-400"></i> Wallet Points
    </h2>
    <div class="text-center p-4 text-gray-600 dark:text-gray-400">
        <p class="mb-2">No wallet found for this patient.</p>
        <a href="{{ url_for('wallet.wallet_tier_management', patient_id=invoice.patient_id) }}"
           class="text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 inline-block">
            <i class="fas fa-plus-circle"></i> Create Wallet
        </a>
    </div>
</div>
{% endif %}
```

---

### 4. Database Model - PaymentDetail

**Check if field exists**: `wallet_transaction_id`

If not, add migration:
```sql
ALTER TABLE payment_details
ADD COLUMN wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id);

CREATE INDEX idx_payment_wallet_txn ON payment_details(wallet_transaction_id);
```

---

### 5. Invoice Display - Show Wallet Payment

**Template**: `invoice_patient_view.html` or wherever invoice details are shown

**Add to payment history**:
```html
{% for payment in payments %}
<tr>
    <td>{{ payment.payment_date.strftime('%d %b %Y') }}</td>
    <td>
        {% if payment.wallet_transaction_id %}
            <span class="badge badge-indigo">
                <i class="fas fa-wallet"></i> Wallet Points
            </span>
        {% else %}
            {{ payment.payment_mode }}
        {% endif %}
    </td>
    <td>{{ payment.amount_paid }}</td>
    <td>{{ payment.reference_number }}</td>
</tr>
{% endfor %}
```

---

## Testing Checklist

### Unit Tests:
- [ ] Wallet balance fetch on payment page
- [ ] Wallet redemption with sufficient points
- [ ] Wallet redemption with insufficient points
- [ ] Mixed payment (wallet + cash)
- [ ] GL entries created for redemption
- [ ] AR subledger updated
- [ ] FIFO batch deduction

### Integration Tests:
- [ ] Create invoice with loyalty discount
- [ ] Navigate to payment page
- [ ] See wallet balance displayed
- [ ] Enter points to redeem
- [ ] See real-time calculation
- [ ] Submit wallet payment
- [ ] Verify invoice balance updated
- [ ] Verify wallet balance reduced
- [ ] Check GL entries created
- [ ] View invoice - see wallet payment listed

### UI Tests:
- [ ] Wallet section shows if patient has wallet
- [ ] Wallet section hidden if no wallet
- [ ] Points input validates max limit
- [ ] Real-time calculation updates
- [ ] Submit button works
- [ ] Link to wallet dashboard works
- [ ] Responsive on mobile

---

## Implementation Order

1. ✅ **GL Service** - wallet_gl_service.py (DONE)
2. **Backend View** - Add wallet_info to payment_form_view
3. **Backend Service** - Add wallet_points_amount to record_payment
4. **Frontend HTML** - Add wallet section to payment_form_page.html
5. **Database** - Check/add wallet_transaction_id to payment_details
6. **Invoice View** - Display wallet payments
7. **Testing** - End-to-end test

---

## Files to Modify

1. `app/views/billing_views.py` - payment_form_view()
2. `app/services/billing_service.py` - record_payment()
3. `app/templates/billing/payment_form_page.html` - Add wallet section
4. `app/templates/billing/invoice_patient_view.html` - Show wallet payment
5. `migrations/` - Add wallet_transaction_id if missing

---

## Estimated Code Changes

- Python: ~100 lines
- HTML/JS: ~150 lines
- SQL: ~5 lines (migration if needed)
- **Total**: ~255 lines

---

## Risk Assessment

**Low Risk**:
- Wallet service already tested ✅
- GL service implemented ✅
- Similar to advance payment flow (existing pattern)
- No breaking changes to existing payment flow

**Mitigation**:
- Wallet payment is optional (won't break if not used)
- Validation at multiple levels (frontend + backend)
- Transaction-based (rollback on error)

---

## Next Steps

1. Get user approval on this plan
2. Implement backend changes (views + service)
3. Implement frontend HTML/JS
4. Test end-to-end
5. Deploy to development

---

**Ready to proceed?**
