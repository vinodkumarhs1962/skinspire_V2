Comprehensive Loyalty Wallet System - Complete Implementation Plan                                                                                  │
     │                                                                                                                                                     │
     │ Document Purpose                                                                                                                                    │
     │                                                                                                                                                     │
     │ This is the MASTER implementation document for the complete Loyalty Wallet Points system, including:                                                │
     │ - Tiered wallet (Silver/Gold/Platinum)                                                                                                              │
     │ - Points loading with bonus                                                                                                                         │
     │ - Points redemption as payment method                                                                                                               │
     │ - Complete refund logic (service & card return)                                                                                                     │
     │ - GL and AR posting entries                                                                                                                         │
     │ - Integration with existing billing system                                                                                                          │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 1: BUSINESS REQUIREMENTS                                                                                                                    │
     │                                                                                                                                                     │
     │ 1.1 Tiered Loyalty Wallet Structure                                                                                                                 │
     │                                                                                                                                                     │
     │ Three Tiers with Increasing Benefits:                                                                                                               │
     │                                                                                                                                                     │
     │ | Tier     | Payment Required | Points Credited | Bonus % | Discount % | Validity  |                                                                │
     │ |----------|------------------|-----------------|---------|------------|-----------|                                                                │
     │ | Silver   | ₹22,000          | 25,000          | 13.6%   | 2%         | 12 months |                                                                │
     │ | Gold     | ₹45,000          | 50,000          | 11.1%   | 3%         | 12 months |                                                                │
     │ | Platinum | ₹92,000          | 100,000         | 8.7%    | 5%         | 12 months |                                                                │
     │                                                                                                                                                     │
     │ Key Features:                                                                                                                                       │
     │ 1. One active tier per patient                                                                                                                      │
     │ 2. Patient can upgrade by paying balance amount                                                                                                     │
     │ 3. Tier discount applies automatically to invoices (already implemented)                                                                            │
     │ 4. Points redemption: 1 point = ₹1 (payment method)                                                                                                 │
     │ 5. Points valid for 12 months from purchase/load date                                                                                               │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 1.2 Points Redemption Rules                                                                                                                         │
     │                                                                                                                                                     │
     │ Usage:                                                                                                                                              │
     │ - Points can be used to pay for services, medicines, packages                                                                                       │
     │ - Works like "advance adjustment" in payment screen                                                                                                 │
     │ - Mixed payments allowed: Points + Cash/Card/UPI                                                                                                    │
     │ - Balance must be > 0 and not expired                                                                                                               │
     │                                                                                                                                                     │
     │ Validation:                                                                                                                                         │
     │ - Check points balance >= redemption amount                                                                                                         │
     │ - Check expiry date (must be future date)                                                                                                           │
     │ - Cannot redeem more than invoice balance                                                                                                           │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 1.3 Refund Logic                                                                                                                                    │
     │                                                                                                                                                     │
     │ A. Service Refund (Service Cancelled)                                                                                                               │
     │                                                                                                                                                     │
     │ Trigger: Service not performed, invoice cancelled                                                                                                   │
     │                                                                                                                                                     │
     │ Rule: Credit ALL points back to wallet with NEW expiry                                                                                              │
     │                                                                                                                                                     │
     │ Example:                                                                                                                                            │
     │ Patient used 5,000 points for laser treatment                                                                                                       │
     │ Service cancelled → Credit 5,000 points back                                                                                                        │
     │ New expiry: Today + 12 months                                                                                                                       │
     │                                                                                                                                                     │
     │ B. Card Return / Wallet Closure                                                                                                                     │
     │                                                                                                                                                     │
     │ Trigger: Patient wants to close wallet and get cash back                                                                                            │
     │                                                                                                                                                     │
     │ Formula:                                                                                                                                            │
     │ IF points_consumed < amount_loaded:                                                                                                                 │
     │     Refund = amount_loaded - points_consumed                                                                                                        │
     │ ELSE:                                                                                                                                               │
     │     Refund = ₹0                                                                                                                                     │
     │                                                                                                                                                     │
     │ Bonus Treatment: Bonus points FORFEITED (not refunded)                                                                                              │
     │                                                                                                                                                     │
     │ Examples:                                                                                                                                           │
     │                                                                                                                                                     │
     │ Example 1 - Refund Due:                                                                                                                             │
     │ Paid: ₹11,000 → Received: 15,000 points (11K base + 4K bonus)                                                                                       │
     │ Used: 8,000 points                                                                                                                                  │
     │ Refund: ₹11,000 - ₹8,000 = ₹3,000 cash back                                                                                                         │
     │ Forfeited: 7,000 remaining points                                                                                                                   │
     │                                                                                                                                                     │
     │ Example 2 - No Refund (Over-consumption):                                                                                                           │
     │ Paid: ₹11,000 → Received: 15,000 points                                                                                                             │
     │ Used: 12,000 points                                                                                                                                 │
     │ Refund: ₹0 (used ₹1,000 more than paid via bonus)                                                                                                   │
     │ Forfeited: 3,000 remaining points                                                                                                                   │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 2: DATABASE SCHEMA                                                                                                                          │
     │                                                                                                                                                     │
     │ 2.1 Schema Enhancements Required                                                                                                                    │
     │                                                                                                                                                     │
     │ Enhance: loyalty_card_types                                                                                                                         │
     │                                                                                                                                                     │
     │ ALTER TABLE loyalty_card_types                                                                                                                      │
     │ ADD COLUMN min_payment_amount NUMERIC(12,2),                                                                                                        │
     │ ADD COLUMN total_points_credited INTEGER,                                                                                                           │
     │ ADD COLUMN bonus_percentage NUMERIC(5,2),                                                                                                           │
     │ ADD COLUMN validity_months INTEGER DEFAULT 12;                                                                                                      │
     │                                                                                                                                                     │
     │ Enhance: patient_loyalty_cards                                                                                                                      │
     │                                                                                                                                                     │
     │ ALTER TABLE patient_loyalty_cards                                                                                                                   │
     │ ADD COLUMN amount_paid NUMERIC(12,2),                                                                                                               │
     │ ADD COLUMN points_granted INTEGER,                                                                                                                  │
     │ ADD COLUMN purchase_date TIMESTAMP,                                                                                                                 │
     │ ADD COLUMN upgraded_from_card_id UUID REFERENCES patient_loyalty_cards(patient_card_id);                                                            │
     │                                                                                                                                                     │
     │ Enhance: wallet_transaction                                                                                                                         │
     │                                                                                                                                                     │
     │ ALTER TABLE wallet_transaction                                                                                                                      │
     │ ADD COLUMN card_type_id UUID REFERENCES loyalty_card_types(card_type_id),                                                                           │
     │ ADD COLUMN patient_card_id UUID REFERENCES patient_loyalty_cards(patient_card_id);                                                                  │
     │                                                                                                                                                     │
     │ -- Add tier transaction types                                                                                                                       │
     │ ALTER TABLE wallet_transaction                                                                                                                      │
     │ DROP CONSTRAINT IF EXISTS check_wallet_txn_type;                                                                                                    │
     │ ALTER TABLE wallet_transaction                                                                                                                      │
     │ ADD CONSTRAINT check_wallet_txn_type CHECK (                                                                                                        │
     │     transaction_type IN ('load', 'redeem', 'refund_service', 'refund_wallet',                                                                       │
     │                          'expire', 'adjustment', 'tier_purchase', 'tier_upgrade')                                                                   │
     │ );                                                                                                                                                  │
     │                                                                                                                                                     │
     │ Create: patient_tier_history (NEW)                                                                                                                  │
     │                                                                                                                                                     │
     │ CREATE TABLE patient_tier_history (                                                                                                                 │
     │     history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),                                                                                          │
     │     patient_id UUID NOT NULL REFERENCES patients(patient_id),                                                                                       │
     │     hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),                                                                                    │
     │     from_card_type_id UUID REFERENCES loyalty_card_types(card_type_id),                                                                             │
     │     to_card_type_id UUID NOT NULL REFERENCES loyalty_card_types(card_type_id),                                                                      │
     │     patient_card_id UUID NOT NULL REFERENCES patient_loyalty_cards(patient_card_id),                                                                │
     │     amount_paid NUMERIC(12,2) NOT NULL,                                                                                                             │
     │     previous_tier_balance NUMERIC(12,2),                                                                                                            │
     │     additional_payment NUMERIC(12,2),                                                                                                               │
     │     points_granted INTEGER NOT NULL,                                                                                                                │
     │     base_points INTEGER NOT NULL,                                                                                                                   │
     │     bonus_points INTEGER NOT NULL,                                                                                                                  │
     │     wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id),                                                                       │
     │     upgrade_date TIMESTAMP DEFAULT NOW() NOT NULL,                                                                                                  │
     │     validity_start DATE NOT NULL,                                                                                                                   │
     │     validity_end DATE NOT NULL,                                                                                                                     │
     │     created_by UUID REFERENCES users(user_id),                                                                                                      │
     │     created_at TIMESTAMP DEFAULT NOW(),                                                                                                             │
     │     notes TEXT                                                                                                                                      │
     │ );                                                                                                                                                  │
     │                                                                                                                                                     │
     │ Enhance: payment_details                                                                                                                            │
     │                                                                                                                                                     │
     │ ALTER TABLE payment_details                                                                                                                         │
     │ ADD COLUMN wallet_points_amount NUMERIC(12,2) DEFAULT 0,                                                                                            │
     │ ADD COLUMN wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id);                                                                │
     │                                                                                                                                                     │
     │ Enhance: invoice_header                                                                                                                             │
     │                                                                                                                                                     │
     │ ALTER TABLE invoice_header                                                                                                                          │
     │ ADD COLUMN points_redeemed INTEGER DEFAULT 0,                                                                                                       │
     │ ADD COLUMN payment_split JSONB;                                                                                                                     │
     │ -- payment_split example: {"points": 10000, "cash": 5000, "card": 3000}                                                                             │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 2.2 Chart of Accounts Setup                                                                                                                         │
     │                                                                                                                                                     │
     │ New GL Account Required:                                                                                                                            │
     │ INSERT INTO chart_of_accounts (                                                                                                                     │
     │     hospital_id,                                                                                                                                    │
     │     account_group,                                                                                                                                  │
     │     gl_account_no,                                                                                                                                  │
     │     account_name,                                                                                                                                   │
     │     is_posting_account,                                                                                                                             │
     │     is_active                                                                                                                                       │
     │ ) VALUES (                                                                                                                                          │
     │     '<hospital_id>',                                                                                                                                │
     │     'Liabilities',                                                                                                                                  │
     │     '2350',                                                                                                                                         │
     │     'Customer Loyalty Wallet',                                                                                                                      │
     │     TRUE,                                                                                                                                           │
     │     TRUE                                                                                                                                            │
     │ );                                                                                                                                                  │
     │                                                                                                                                                     │
     │ Optional Income Account:                                                                                                                            │
     │ INSERT INTO chart_of_accounts (                                                                                                                     │
     │     hospital_id,                                                                                                                                    │
     │     account_group,                                                                                                                                  │
     │     gl_account_no,                                                                                                                                  │
     │     account_name,                                                                                                                                   │
     │     is_posting_account,                                                                                                                             │
     │     is_active                                                                                                                                       │
     │ ) VALUES (                                                                                                                                          │
     │     '<hospital_id>',                                                                                                                                │
     │     'Income',                                                                                                                                       │
     │     '4900',                                                                                                                                         │
     │     'Expired Points Income',                                                                                                                        │
     │     TRUE,                                                                                                                                           │
     │     TRUE                                                                                                                                            │
     │ );                                                                                                                                                  │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 3: GL POSTING RULES                                                                                                                         │
     │                                                                                                                                                     │
     │ 3.1 Tier Purchase (Silver - ₹22K → 25K points)                                                                                                      │
     │                                                                                                                                                     │
     │ Transaction: Patient pays ₹22,000 cash, receives 25,000 points                                                                                      │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Cash (1101)                         ₹22,000                                                                                                     │
     │     Cr. Customer Loyalty Wallet (2350)              ₹22,000                                                                                         │
     │                                                                                                                                                     │
     │ Wallet Record:                                                                                                                                      │
     │ Total Amount Loaded: ₹22,000                                                                                                                        │
     │ Total Points Loaded: 25,000                                                                                                                         │
     │ Base Points: 22,000                                                                                                                                 │
     │ Bonus Points: 3,000                                                                                                                                 │
     │                                                                                                                                                     │
     │ Note: Bonus tracked in wallet, but GL liability = cash received only                                                                                │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 3.2 Points Redemption (10K points + 8K cash for ₹18K invoice)                                                                                       │
     │                                                                                                                                                     │
     │ Transaction: Patient uses 10,000 points + ₹8,000 cash to pay ₹18,000 invoice                                                                        │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Customer Loyalty Wallet (2350)      ₹10,000                                                                                                     │
     │ Dr. Cash (1101)                         ₹8,000                                                                                                      │
     │     Cr. Accounts Receivable (1100)                  ₹18,000                                                                                         │
     │                                                                                                                                                     │
     │ AR Subledger:                                                                                                                                       │
     │ - Entry type: 'payment'                                                                                                                             │
     │ - Credit AR: ₹18,000 (allocated to line items)                                                                                                      │
     │ - Payment source: 'wallet_points' + 'cash'                                                                                                          │
     │                                                                                                                                                     │
     │ Invoice Update:                                                                                                                                     │
     │ payment_split: {"points": 10000, "cash": 8000}                                                                                                      │
     │ points_redeemed: 10000                                                                                                                              │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 3.3 Service Refund (5K points back)                                                                                                                 │
     │                                                                                                                                                     │
     │ Transaction: Service cancelled, credit 5,000 points back to wallet                                                                                  │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Accounts Receivable (1100)          ₹5,000                                                                                                      │
     │     Cr. Customer Loyalty Wallet (2350)              ₹5,000                                                                                          │
     │                                                                                                                                                     │
     │ AR Subledger:                                                                                                                                       │
     │ - Entry type: 'refund'                                                                                                                              │
     │ - Debit AR: ₹5,000 (recreate receivable)                                                                                                            │
     │                                                                                                                                                     │
     │ Wallet Transaction:                                                                                                                                 │
     │ transaction_type: 'refund_service'                                                                                                                  │
     │ points_credited_back: 5000                                                                                                                          │
     │ new_expiry_date: Today + 12 months                                                                                                                  │
     │ refund_reason: "Service cancelled by patient"                                                                                                       │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 3.4 Wallet Closure Refund (Scenario: ₹3K cash back)                                                                                                 │
     │                                                                                                                                                     │
     │ Transaction: Patient closes wallet                                                                                                                  │
     │ - Paid: ₹11,000 → Got: 15,000 points (11K base + 4K bonus)                                                                                          │
     │ - Used: 8,000 points                                                                                                                                │
     │ - Remaining: 7,000 points                                                                                                                           │
     │ - Refund: ₹11,000 - ₹8,000 = ₹3,000                                                                                                                 │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Customer Loyalty Wallet (2350)      ₹11,000                                                                                                     │
     │     Cr. Cash (1101)                                 ₹3,000                                                                                          │
     │     Cr. Expired Points Income (4900)                ₹8,000                                                                                          │
     │                                                                                                                                                     │
     │ Breakdown:                                                                                                                                          │
     │ - Total liability cleared: ₹11,000 (original amount loaded)                                                                                         │
     │ - Cash refunded: ₹3,000 (unused base points)                                                                                                        │
     │ - Income recognized: ₹8,000 (points consumed + bonus forfeited)                                                                                     │
     │                                                                                                                                                     │
     │ Wallet Transaction:                                                                                                                                 │
     │ transaction_type: 'refund_wallet'                                                                                                                   │
     │ wallet_closure_amount: 3000                                                                                                                         │
     │ points_forfeited: 7000                                                                                                                              │
     │ balance_before: 7000                                                                                                                                │
     │ balance_after: 0                                                                                                                                    │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 3.5 Wallet Closure - No Refund (Over-consumption)                                                                                                   │
     │                                                                                                                                                     │
     │ Transaction: Patient closes wallet                                                                                                                  │
     │ - Paid: ₹11,000 → Got: 15,000 points                                                                                                                │
     │ - Used: 12,000 points                                                                                                                               │
     │ - Remaining: 3,000 points                                                                                                                           │
     │ - Refund: ₹0 (consumed more than paid)                                                                                                              │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Customer Loyalty Wallet (2350)      ₹11,000                                                                                                     │
     │     Cr. Expired Points Income (4900)                ₹11,000                                                                                         │
     │                                                                                                                                                     │
     │ Explanation: All liability converted to income (no cash refund due)                                                                                 │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ 3.6 Points Expiry (2K points expire)                                                                                                                │
     │                                                                                                                                                     │
     │ Transaction: Points expire after 12 months                                                                                                          │
     │                                                                                                                                                     │
     │ GL Entry:                                                                                                                                           │
     │ Dr. Customer Loyalty Wallet (2350)      ₹2,000                                                                                                      │
     │     Cr. Expired Points Income (4900)                ₹2,000                                                                                          │
     │                                                                                                                                                     │
     │ Wallet Transaction:                                                                                                                                 │
     │ transaction_type: 'expire'                                                                                                                          │
     │ points_expired: 2000                                                                                                                                │
     │ balance_before: 7000                                                                                                                                │
     │ balance_after: 5000                                                                                                                                 │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 4: IMPLEMENTATION PLAN                                                                                                                      │
     │                                                                                                                                                     │
     │ Phase 1: Database Setup (1 day)                                                                                                                     │
     │                                                                                                                                                     │
     │ Tasks:                                                                                                                                              │
     │ 1. Execute wallet migration (if not done): 20251121_create_loyalty_wallet_system.sql                                                                │
     │ 2. Execute tier enhancement migration (new)                                                                                                         │
     │ 3. Add GL accounts (2350, 4900)                                                                                                                     │
     │ 4. Configure tier definitions (Silver/Gold/Platinum)                                                                                                │
     │                                                                                                                                                     │
     │ Deliverables:                                                                                                                                       │
     │ - All database tables created                                                                                                                       │
     │ - Tier configurations inserted                                                                                                                      │
     │ - GL accounts ready                                                                                                                                 │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 2: Wallet Service Layer (3 days)                                                                                                              │
     │                                                                                                                                                     │
     │ File: app/services/wallet_service.py (NEW)                                                                                                          │
     │                                                                                                                                                     │
     │ Functions to Implement:                                                                                                                             │
     │                                                                                                                                                     │
     │ Tier Management:                                                                                                                                    │
     │ 1. purchase_tier(patient_id, tier_code, payment_mode, user_id)                                                                                      │
     │   - Create patient loyalty card                                                                                                                     │
     │   - Create/update wallet with points                                                                                                                │
     │   - Create wallet_transaction (tier_purchase)                                                                                                       │
     │   - Create tier history record                                                                                                                      │
     │   - Post GL entries (Dr Cash, Cr Wallet Liability)                                                                                                  │
     │ 2. upgrade_tier(patient_id, new_tier_code, payment_mode, user_id)                                                                                   │
     │   - Deactivate current tier                                                                                                                         │
     │   - Calculate additional payment needed                                                                                                             │
     │   - Create new tier card                                                                                                                            │
     │   - Add additional points to wallet                                                                                                                 │
     │   - Create wallet_transaction (tier_upgrade)                                                                                                        │
     │   - Create tier history record                                                                                                                      │
     │   - Post GL entries                                                                                                                                 │
     │ 3. get_patient_tier(patient_id)                                                                                                                     │
     │   - Return current tier details                                                                                                                     │
     │   - Include expiry status                                                                                                                           │
     │ 4. get_upgrade_options(patient_id)                                                                                                                  │
     │   - Calculate upgrade costs for available tiers                                                                                                     │
     │                                                                                                                                                     │
     │ Wallet Operations:                                                                                                                                  │
     │ 5. get_wallet_balance(patient_id)                                                                                                                   │
     │ - Return points balance, expiry date, tier info                                                                                                     │
     │                                                                                                                                                     │
     │ 6. validate_points_redemption(patient_id, points)                                                                                                   │
     │   - Check balance >= points                                                                                                                         │
     │   - Check expiry date > today                                                                                                                       │
     │   - Return validation result                                                                                                                        │
     │ 7. redeem_points(patient_id, points, invoice_id, user_id)                                                                                           │
     │   - Deduct points from wallet (FIFO from batches)                                                                                                   │
     │   - Create wallet_transaction (redeem)                                                                                                              │
     │   - Return transaction_id for payment linking                                                                                                       │
     │                                                                                                                                                     │
     │ Refund Operations:                                                                                                                                  │
     │ 8. refund_service(invoice_id, user_id)                                                                                                              │
     │ - Find original redemption transaction                                                                                                              │
     │ - Credit points back to wallet                                                                                                                      │
     │ - Set new expiry = today + 12 months                                                                                                                │
     │ - Create wallet_transaction (refund_service)                                                                                                        │
     │ - Post GL entries (Dr AR, Cr Wallet Liability)                                                                                                      │
     │                                                                                                                                                     │
     │ 9. refund_wallet_closure(patient_id, user_id)                                                                                                       │
     │   - Calculate: refund = amount_loaded - points_consumed                                                                                             │
     │   - Close wallet                                                                                                                                    │
     │   - Create wallet_transaction (refund_wallet)                                                                                                       │
     │   - Post GL entries (Dr Wallet Liability, Cr Cash + Cr Income)                                                                                      │
     │   - Return refund amount                                                                                                                            │
     │ 10. expire_points_batch()                                                                                                                           │
     │   - Background job to expire old points                                                                                                             │
     │   - Post GL entries for each expiry                                                                                                                 │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 3: GL Service Integration (1 day)                                                                                                             │
     │                                                                                                                                                     │
     │ File: app/services/gl_service.py (MODIFY)                                                                                                           │
     │                                                                                                                                                     │
     │ Functions to Add:                                                                                                                                   │
     │                                                                                                                                                     │
     │ 1. create_wallet_load_gl_entries(wallet_transaction_id, user_id, session)                                                                           │
     │   - Dr Cash, Cr Customer Loyalty Wallet                                                                                                             │
     │ 2. create_wallet_redemption_gl_entries(payment_id, points, user_id, session)                                                                        │
     │   - Dr Customer Loyalty Wallet, Dr Cash/Card/UPI, Cr AR                                                                                             │
     │ 3. create_wallet_refund_gl_entries(wallet_transaction_id, user_id, session)                                                                         │
     │   - Dr AR, Cr Customer Loyalty Wallet (service refund)                                                                                              │
     │   - OR Dr Wallet Liability, Cr Cash + Cr Income (wallet closure)                                                                                    │
     │ 4. create_wallet_expiry_gl_entries(wallet_transaction_id, points, user_id, session)                                                                 │
     │   - Dr Customer Loyalty Wallet, Cr Expired Points Income                                                                                            │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 4: Payment Integration (2 days)                                                                                                               │
     │                                                                                                                                                     │
     │ File: app/services/billing_service.py (MODIFY)                                                                                                      │
     │                                                                                                                                                     │
     │ Update record_payment() function:                                                                                                                   │
     │                                                                                                                                                     │
     │ def record_payment(                                                                                                                                 │
     │     hospital_id, invoice_id, payment_date,                                                                                                          │
     │     cash_amount=Decimal('0'),                                                                                                                       │
     │     credit_card_amount=Decimal('0'),                                                                                                                │
     │     debit_card_amount=Decimal('0'),                                                                                                                 │
     │     upi_amount=Decimal('0'),                                                                                                                        │
     │     wallet_points_amount=0,  # NEW                                                                                                                  │
     │     # ... other parameters                                                                                                                          │
     │ ):                                                                                                                                                  │
     │     # 1. Validate points if used                                                                                                                    │
     │     if wallet_points_amount > 0:                                                                                                                    │
     │         validation = WalletService.validate_points_redemption(patient_id, wallet_points_amount)                                                     │
     │         if not validation['valid']:                                                                                                                 │
     │             raise ValueError(validation['message'])                                                                                                 │
     │                                                                                                                                                     │
     │         # 2. Redeem points                                                                                                                          │
     │         wallet_txn_id = WalletService.redeem_points(                                                                                                │
     │             patient_id, wallet_points_amount, invoice_id, current_user.user_id                                                                      │
     │         )                                                                                                                                           │
     │                                                                                                                                                     │
     │     # 3. Calculate total including wallet points                                                                                                    │
     │     total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount + Decimal(wallet_points_amount)                               │
     │                                                                                                                                                     │
     │     # 4. Create payment record                                                                                                                      │
     │     payment = PaymentDetail(                                                                                                                        │
     │         cash_amount=cash_amount,                                                                                                                    │
     │         # ... other fields                                                                                                                          │
     │         wallet_points_amount=wallet_points_amount,  # NEW                                                                                           │
     │         wallet_transaction_id=wallet_txn_id,  # NEW                                                                                                 │
     │         total_amount=total_payment                                                                                                                  │
     │     )                                                                                                                                               │
     │                                                                                                                                                     │
     │     # 5. Post GL entries                                                                                                                            │
     │     if should_post_gl:                                                                                                                              │
     │         if wallet_points_amount > 0:                                                                                                                │
     │             create_wallet_redemption_gl_entries(payment.payment_id, wallet_points_amount, user_id, session)                                         │
     │         else:                                                                                                                                       │
     │             create_payment_gl_entries(payment.payment_id, user_id, session)                                                                         │
     │                                                                                                                                                     │
     │     # 6. Update invoice                                                                                                                             │
     │     invoice.points_redeemed = wallet_points_amount                                                                                                  │
     │     invoice.payment_split = {                                                                                                                       │
     │         "points": wallet_points_amount,                                                                                                             │
     │         "cash": cash_amount,                                                                                                                        │
     │         "card": credit_card_amount + debit_card_amount,                                                                                             │
     │         "upi": upi_amount                                                                                                                           │
     │     }                                                                                                                                               │
     │                                                                                                                                                     │
     │ Add refund_invoice_payment() function:                                                                                                              │
     │ - Auto-refund points when invoice cancelled                                                                                                         │
     │ - Call WalletService.refund_service()                                                                                                               │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 5: UI - Tier Management (2 days)                                                                                                              │
     │                                                                                                                                                     │
     │ Routes (app/views/billing_views.py):                                                                                                                │
     │                                                                                                                                                     │
     │ 1. /wallet/tier/purchase - Admin purchases tier for patient                                                                                         │
     │ 2. /wallet/tier/upgrade/<patient_id> - Upgrade patient tier                                                                                         │
     │ 3. /wallet/tier/view/<patient_id> - View tier + wallet dashboard                                                                                    │
     │ 4. /wallet/tier/history/<patient_id> - Tier upgrade history                                                                                         │
     │                                                                                                                                                     │
     │ Templates (new files):                                                                                                                              │
     │                                                                                                                                                     │
     │ 1. wallet_tier_purchase.html                                                                                                                        │
     │   - Form: Select patient, select tier, payment method                                                                                               │
     │   - Shows: Price, points, bonus %, discount %                                                                                                       │
     │ 2. wallet_tier_upgrade.html                                                                                                                         │
     │   - Shows current tier                                                                                                                              │
     │   - Lists available upgrades with additional cost                                                                                                   │
     │   - Payment method selection                                                                                                                        │
     │ 3. wallet_tier_view.html                                                                                                                            │
     │   - Tier badge (Silver/Gold/Platinum colored)                                                                                                       │
     │   - Points balance, expiry date                                                                                                                     │
     │   - Tier benefits                                                                                                                                   │
     │   - Upgrade options                                                                                                                                 │
     │   - Transaction history table                                                                                                                       │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 6: UI - Payment Form (1 day)                                                                                                                  │
     │                                                                                                                                                     │
     │ File: app/templates/billing/payment_form_page.html (MODIFY)                                                                                         │
     │                                                                                                                                                     │
     │ Add Wallet Points Section (above payment methods):                                                                                                  │
     │                                                                                                                                                     │
     │ <!-- Wallet Points Adjustment (Like Advance) -->                                                                                                    │
     │ {% if patient_wallet and patient_wallet.points_balance > 0 %}                                                                                       │
     │ <div class="card mb-3 border-success">                                                                                                              │
     │     <div class="card-header bg-light">                                                                                                              │
     │         <span class="tier-badge {{ patient_wallet.tier_code|lower }}">                                                                              │
     │             {{ patient_wallet.tier_name }}                                                                                                          │
     │         </span>                                                                                                                                     │
     │         <span class="ms-2">Wallet Points Available</span>                                                                                           │
     │     </div>                                                                                                                                          │
     │     <div class="card-body">                                                                                                                         │
     │         <div class="row">                                                                                                                           │
     │             <div class="col-md-6">                                                                                                                  │
     │                 <strong>Available:</strong> {{ patient_wallet.points_balance }} points (₹{{ patient_wallet.points_balance }})                       │
     │             </div>                                                                                                                                  │
     │             <div class="col-md-6">                                                                                                                  │
     │                 <strong>Expiry:</strong>                                                                                                            │
     │                 <span class="{% if patient_wallet.is_expiring_soon %}text-danger{% endif %}">                                                       │
     │                     {{ patient_wallet.expiry_date|dateformat }}                                                                                     │
     │                 </span>                                                                                                                             │
     │                 {% if patient_wallet.is_expired %}                                                                                                  │
     │                 <span class="badge bg-danger">EXPIRED</span>                                                                                        │
     │                 {% endif %}                                                                                                                         │
     │             </div>                                                                                                                                  │
     │         </div>                                                                                                                                      │
     │                                                                                                                                                     │
     │         {% if not patient_wallet.is_expired %}                                                                                                      │
     │         <div class="row mt-3">                                                                                                                      │
     │             <div class="col-md-6">                                                                                                                  │
     │                 <label>Points to Redeem:</label>                                                                                                    │
     │                 <input type="number"                                                                                                                │
     │                        class="form-control"                                                                                                         │
     │                        id="wallet_points_amount"                                                                                                    │
     │                        name="wallet_points_amount"                                                                                                  │
     │                        min="0"                                                                                                                      │
     │                        max="{{ [patient_wallet.points_balance, balance_due]|min }}"                                                                 │
     │                        value="0"                                                                                                                    │
     │                        onchange="updatePaymentTotal()">                                                                                             │
     │             </div>                                                                                                                                  │
     │             <div class="col-md-6">                                                                                                                  │
     │                 <label>Tier Discount:</label>                                                                                                       │
     │                 <div class="alert alert-info mb-0">                                                                                                 │
     │                     {{ patient_wallet.discount_percent }}% discount already applied to invoice                                                      │
     │                 </div>                                                                                                                              │
     │             </div>                                                                                                                                  │
     │         </div>                                                                                                                                      │
     │         {% else %}                                                                                                                                  │
     │         <div class="alert alert-danger mt-2 mb-0">                                                                                                  │
     │             Points expired. Cannot redeem.                                                                                                          │
     │         </div>                                                                                                                                      │
     │         {% endif %}                                                                                                                                 │
     │     </div>                                                                                                                                          │
     │ </div>                                                                                                                                              │
     │ {% endif %}                                                                                                                                         │
     │                                                                                                                                                     │
     │ JavaScript Update:                                                                                                                                  │
     │ function updatePaymentTotal() {                                                                                                                     │
     │     const cash = parseFloat($('#cash_amount').val()) || 0;                                                                                          │
     │     const card = parseFloat($('#credit_card_amount').val()) || 0;                                                                                   │
     │     const upi = parseFloat($('#upi_amount').val()) || 0;                                                                                            │
     │     const points = parseFloat($('#wallet_points_amount').val()) || 0;                                                                               │
     │                                                                                                                                                     │
     │     const total = cash + card + upi + points;                                                                                                       │
     │     $('#total_payment_display').text(total.toFixed(2));                                                                                             │
     │                                                                                                                                                     │
     │     // Validate points <= available balance                                                                                                         │
     │     const maxPoints = parseFloat($('#wallet_points_amount').attr('max'));                                                                           │
     │     if (points > maxPoints) {                                                                                                                       │
     │         alert('Points exceed available balance');                                                                                                   │
     │         $('#wallet_points_amount').val(maxPoints);                                                                                                  │
     │     }                                                                                                                                               │
     │ }                                                                                                                                                   │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ Phase 7: Testing (1 day)                                                                                                                            │
     │                                                                                                                                                     │
     │ Test Scenarios:                                                                                                                                     │
     │                                                                                                                                                     │
     │ 1. Tier Purchase:                                                                                                                                   │
     │   - ✅ Purchase Silver tier (₹22K → 25K points)                                                                                                      
│
     │   - ✅ Check wallet balance, expiry date                                                                                                             
│
     │   - ✅ Verify GL entries (Dr Cash, Cr Wallet Liability)                                                                                              
│
     │ 2. Tier Upgrade:                                                                                                                                    │
     │   - ✅ Upgrade Silver → Gold (pay ₹23K, get 25K more points)                                                                                         
│
     │   - ✅ Verify tier history                                                                                                                           
│
     │   - ✅ Check GL entries                                                                                                                              
│
     │ 3. Points Redemption:                                                                                                                               │
     │   - ✅ Use 10K points + 5K cash to pay ₹15K invoice                                                                                                  
│
     │   - ✅ Check payment_split JSON                                                                                                                      
│
     │   - ✅ Verify GL: Dr Wallet + Dr Cash, Cr AR                                                                                                         
│
     │   - ✅ Check AR subledger line item allocation                                                                                                       
│
     │ 4. Service Refund:                                                                                                                                  │
     │   - ✅ Cancel service, refund 10K points                                                                                                             
│
     │   - ✅ Verify new expiry date (today + 12 months)                                                                                                    
│
     │   - ✅ Check GL: Dr AR, Cr Wallet Liability                                                                                                          
│
     │ 5. Wallet Closure:                                                                                                                                  │
     │   - ✅ Scenario 1: Refund due (paid ₹11K, used 8K, get ₹3K back)                                                                                     
│
     │   - ✅ Scenario 2: No refund (paid ₹11K, used 12K, get ₹0)                                                                                           
│
     │   - ✅ Verify GL entries for both scenarios                                                                                                          
│
     │ 6. Points Expiry:                                                                                                                                   │
     │   - ✅ Expire 2K points                                                                                                                              
│
     │   - ✅ Verify GL: Dr Wallet Liability, Cr Expired Points Income                                                                                      
│
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 5: FILES SUMMARY                                                                                                                            │
     │                                                                                                                                                     │
     │ Files to Create:                                                                                                                                    │
     │                                                                                                                                                     │
     │ 1. ✨ migrations/20251124_enhance_loyalty_wallet_tiers.sql (~400 lines)                                                                              
│
     │ 2. ✨ app/services/wallet_service.py (~600 lines)                                                                                                    
│
     │ 3. ✨ app/templates/billing/wallet_tier_purchase.html (~200 lines)                                                                                   
│
     │ 4. ✨ app/templates/billing/wallet_tier_upgrade.html (~200 lines)                                                                                    
│
     │ 5. ✨ app/templates/billing/wallet_tier_view.html (~300 lines)                                                                                       
│
     │ 6. ✨ app/models/wallet_models.py (~150 lines)                                                                                                       
│
     │                                                                                                                                                     │
     │ Files to Modify:                                                                                                                                    │
     │                                                                                                                                                     │
     │ 1. 📝 app/services/billing_service.py - Add wallet payment support (~100 lines)                                                                     │
     │ 2. 📝 app/services/gl_service.py - Add wallet GL functions (~200 lines)                                                                             │
     │ 3. 📝 app/views/billing_views.py - Add tier management routes (~200 lines)                                                                          │
     │ 4. 📝 app/templates/billing/payment_form_page.html - Add wallet section (~80 lines)                                                                 │
     │ 5. 📝 app/models/transaction.py - Add wallet fields to PaymentDetail (~30 lines)                                                                    │
     │ 6. 📝 app/models/master.py - Add wallet fields to LoyaltyCardType (~20 lines)                                                                       │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 6: IMPLEMENTATION TIMELINE                                                                                                                  │
     │                                                                                                                                                     │
     │ | Phase   | Tasks                       | Estimated Days |                                                                                          │
     │ |---------|-----------------------------|----------------|                                                                                          │
     │ | Phase 1 | Database setup, tier config | 1 day          |                                                                                          │
     │ | Phase 2 | Wallet service layer        | 3 days         |                                                                                          │
     │ | Phase 3 | GL service integration      | 1 day          |                                                                                          │
     │ | Phase 4 | Payment integration         | 2 days         |                                                                                          │
     │ | Phase 5 | Tier management UI          | 2 days         |                                                                                          │
     │ | Phase 6 | Payment form UI             | 1 day          |                                                                                          │
     │ | Phase 7 | Testing & bug fixes         | 1 day          |                                                                                          │
     │ | Total   |                             | 11 days        |                                                                                          │
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ SECTION 7: SUCCESS CRITERIA                                                                                                                         │
     │                                                                                                                                                     │
     │ Tier Management:                                                                                                                                    │
     │ - ✅ Admin can purchase tier for patient (Silver/Gold/Platinum)                                                                                      
│
     │ - ✅ Patient can upgrade to higher tier                                                                                                              
│
     │ - ✅ Tier benefits apply automatically (discount %, points bonus)                                                                                    
│
     │ - ✅ Tier history tracked completely                                                                                                                 
│
     │                                                                                                                                                     │
     │ Points Redemption:                                                                                                                                  │
     │ - ✅ Points work as payment method (like advance adjustment)                                                                                         
│
     │ - ✅ Mixed payments supported (points + cash/card)                                                                                                   
│
     │ - ✅ Expiry validation works                                                                                                                         
│
     │ - ✅ AR subledger tracks line-item allocation                                                                                                        
│
     │                                                                                                                                                     │
     │ Refunds:                                                                                                                                            │
     │ - ✅ Service refund credits all points back with new expiry                                                                                          
│
     │ - ✅ Wallet closure refunds only base amount (bonus forfeited)                                                                                       
│
     │ - ✅ Over-consumption scenario: no refund given                                                                                                      
│
     │                                                                                                                                                     │
     │ GL Posting:                                                                                                                                         │
     │ - ✅ All transactions have correct GL entries                                                                                                        
│
     │ - ✅ Wallet liability account balanced                                                                                                               
│
     │ - ✅ Expired/forfeited points recognized as income                                                                                                   
│
     │ - ✅ AR subledger in sync with GL                                                                                                                    
│
     │                                                                                                                                                     │
     │ User Experience:                                                                                                                                    │
     │ - ✅ Payment form shows wallet balance and expiry                                                                                                    
│
     │ - ✅ Real-time validation (balance, expiry)                                                                                                          
│
     │ - ✅ Tier badge displayed (colored: Silver/Gold/Platinum)                                                                                            
│
     │ - ✅ Transaction history visible to admin                                                                                                            
│
     │                                                                                                                                                     │
     │ ---                                                                                                                                                 │
     │ This comprehensive document serves as the complete blueprint for implementing the tiered loyalty wallet system with full GL integration, refund     │
     │ logic, and payment processing capabilities.    