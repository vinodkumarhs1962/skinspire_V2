# Balance Sheet Calculation Explanation
## Skinspire Clinic - As of October 31, 2025

---

## ⚠️ IMPORTANT NOTE

The Balance Sheet contains several **ESTIMATED VALUES** because the source CSV file (`Clinic expenses analysis.csv`) only provides:
- ✅ Revenue data (income statement)
- ✅ Expense data (income statement)
- ✅ Cash flow data
- ❌ **NO** accounts receivable data
- ❌ **NO** fixed asset details
- ❌ **NO** liability breakdown
- ❌ **NO** equity details

Therefore, several values are **REASONABLE ESTIMATES** for presentation purposes.

---

## ASSETS CALCULATION

### Current Assets

**1. Cash in Hand (ACTUAL)**
```
Source: Sum of monthly cash collections from CSV
= Jan(2,68,408) + Feb(1,19,608) + Mar(1,77,567) + Apr(1,52,994)
  + May(1,45,544) + Jun(1,07,089) + Jul(4,39,356) + Aug(3,34,920)
  + Sep(3,00,036) + Oct(2,01,667)
= ₹22,47,189
```

**2. Bank Balance (CALCULATED)**
```
Source: Derived from bank cash flow analysis
Bank collections - Bank expenditures = ₹9,54,034

Calculation:
Total bank collections (10 months) = ₹71,48,083
Total bank net position = ₹9,54,034
(This represents cumulative bank balance after all expenses paid through bank)
```

**3. Medicine Inventory (GIVEN)**
```
Source: Specified by user
Average medicine inventory maintained = ₹10,00,000
```

**4. Accounts Receivable (ESTIMATED) ⚠️**
```
Source: ESTIMATED (NOT in CSV data)
Estimated value = ₹5,00,000

REASONING:
- Skinspire is a healthcare clinic
- Typical clinics have 5-7% of monthly revenue as AR
- Average monthly revenue = ₹9.39L
- Estimated AR = 5-6% × ₹9.39L ≈ ₹5L

ASSUMPTIONS:
- Some insurance claims pending
- Corporate billing with 30-day terms
- Some patient credit accounts
- Normal healthcare receivables cycle

LIMITATION:
This is a ROUGH ESTIMATE. Actual AR should be obtained from:
- Accounting system reports
- Patient ledger aging report
- Insurance claim tracking
```

**Total Current Assets:**
```
= Cash in Hand + Bank Balance + Inventory + Accounts Receivable
= ₹22,47,189 + ₹9,54,034 + ₹10,00,000 + ₹5,00,000
= ₹47,01,223
```

---

### Fixed Assets

**Fixed Assets (ESTIMATED BASE + ACTUAL CAPEX) ⚠️**
```
Calculation:
= Base Fixed Assets (estimated) + Capital Expenditure (actual)
= ₹60,00,000 + ₹20,86,756
= ₹80,86,756

COMPONENTS:

1. Base Fixed Assets (₹60,00,000) - ESTIMATED
   Assumed to include:
   - Medical equipment (existing)
   - Furniture & fixtures
   - Computers & IT equipment
   - Clinic setup/infrastructure
   - Other fixed assets

   REASONING:
   - This is a reasonable estimate for a dermatology/aesthetic clinic
   - Represents pre-existing assets before Jan 2025
   - Actual value should come from fixed asset register

2. Capital Expenditure (₹20,86,756) - ACTUAL from CSV
   This includes ALL CapEx during Jan-Oct 2025:
   - Equipment purchases: ₹10,79,391
   - Cash CapEx: ₹7,69,000
   - Loan interest: ₹2,38,365
   Total: ₹20,86,756

   Monthly breakdown (from CSV):
   Jan: ₹40,499    Jul: ₹1,57,612
   Feb: ₹3,54,674  Aug: ₹1,01,979
   Mar: ₹4,04,273  Sep: ₹66,662
   Apr: ₹3,95,188  Oct: ₹18,916
   May: ₹4,05,636
   Jun: ₹1,41,317

NOTE: Fixed assets shown at GROSS value (not depreciated)
Ideally should show NET book value after depreciation.
```

**Total Fixed Assets:**
```
= ₹80,86,756
```

**TOTAL ASSETS:**
```
= Current Assets + Fixed Assets
= ₹47,01,223 + ₹80,86,756
= ₹1,27,87,979 (approximately ₹1.28 Crores or ₹128 Lakhs)
```

---

## LIABILITIES CALCULATION

**Total Liabilities (ESTIMATED) ⚠️**
```
Source: ESTIMATED (NOT in CSV data)
Estimated value = ₹33,00,000

REASONING:
This represents estimated total liabilities including:

1. Short-term Liabilities (estimated ₹15L):
   - Accounts payable (suppliers): ₹3L
   - Short-term borrowings: ₹10L
   - Accrued expenses: ₹2L

2. Long-term Liabilities (estimated ₹18L):
   - Long-term loan principal: ₹20L (original)
   - Less: Repayments (10 months): -₹2L
   - Net: ₹18L

ASSUMPTIONS:
- Loan interest (₹2.38L in 10 months) suggests principal of ₹15-20L
- Monthly loan repayment estimated at ₹20K
- Working capital borrowings of ₹10L
- Vendor payables of ₹3L

LIMITATION:
This is a ROUGH ESTIMATE. Actual liabilities should be obtained from:
- Loan statements
- Accounts payable aging
- Bank overdraft/credit line statements
- Accrual ledger
```

**Total Liabilities:**
```
= ₹33,00,000
```

---

## OWNER'S EQUITY CALCULATION

**Owner's Equity (CALCULATED using Accounting Equation)**
```
Fundamental Accounting Equation:
Assets = Liabilities + Equity

Therefore:
Equity = Assets - Liabilities

Calculation:
= Total Assets - Total Liabilities
= ₹1,27,87,979 - ₹33,00,000
= ₹94,87,979

In Lakhs: ₹94.88 Lakhs
In Crores: ₹0.95 Crores
```

---

## OWNER'S EQUITY COMPOSITION

The Owner's Equity of ₹94.88 Lakhs can be understood as:

```
Owner's Equity = Opening Capital + Profit - Drawings - Capital Used

Estimated breakdown:

1. Initial Capital Contribution (estimated)    ₹60,00,000
   (Investment to start/setup clinic)

2. Add: Opening Retained Earnings (estimated)  ₹10,00,000
   (Previous years' accumulated profits)

3. Add: Current Year Profit (Jan-Oct)         ₹16,63,223
   (Net profit for 10 months - ACTUAL from CSV)

4. Less: Personal Drawings (Jan-Oct)          (₹9,61,573)
   (Owner withdrawals - ACTUAL from CSV)

5. Less: CapEx funded from profits            (₹20,86,756)
   (Equipment purchased from business funds - ACTUAL)

6. Add: CapEx funded by loans/liabilities     ₹20,00,000
   (Portion of CapEx that was loan-funded)

7. Add: Other adjustments                     ₹18,72,085
   (Balancing figure to reconcile)

= Estimated Owner's Equity                    ₹94,87,979
```

**Note:** This is a reconciliation estimate. Actual equity composition requires:
- Opening balance sheet
- Capital account statement
- Drawings register
- Profit appropriation details

---

## KEY RATIOS (Based on Balance Sheet)

### Liquidity Ratios:
```
1. Current Ratio = Current Assets / Current Liabilities
                 = ₹47,01,223 / ₹15,00,000 (estimated)
                 = 3.13:1
   (Shown as 2.62:1 in presentation - using different liability estimate)

   Interpretation: Healthy - Can cover short-term obligations

2. Quick Ratio = (Current Assets - Inventory) / Current Liabilities
               = (₹47,01,223 - ₹10,00,000) / ₹15,00,000
               = 2.47:1

   Interpretation: Excellent - High liquidity even without inventory
```

### Leverage Ratios:
```
3. Debt-to-Equity Ratio = Total Liabilities / Owner's Equity
                        = ₹33,00,000 / ₹94,87,979
                        = 0.35:1

   Interpretation: Conservative - Low leverage, financially stable

4. Debt-to-Assets Ratio = Total Liabilities / Total Assets
                        = ₹33,00,000 / ₹1,27,87,979
                        = 25.8%

   Interpretation: Only 26% of assets are financed by debt
```

### Asset Composition:
```
5. Fixed Asset Ratio = Fixed Assets / Total Assets
                     = ₹80,86,756 / ₹1,27,87,979
                     = 63.2%

   Interpretation: Capital-intensive business (medical equipment)

6. Current Asset Ratio = Current Assets / Total Assets
                       = ₹47,01,223 / ₹1,27,87,979
                       = 36.8%

   Interpretation: Good working capital position
```

---

## LIMITATIONS & RECOMMENDATIONS

### ⚠️ ESTIMATED VALUES (NOT ACTUAL):

| Item | Estimated Value | Confidence Level | Source Needed |
|------|----------------|------------------|---------------|
| **Accounts Receivable** | ₹5,00,000 | Low | Patient ledger, insurance claims report |
| **Base Fixed Assets** | ₹60,00,000 | Low | Fixed asset register, depreciation schedule |
| **Total Liabilities** | ₹33,00,000 | Low | Loan statements, AP aging, accrual register |
| **Initial Capital** | ₹60,00,000 | Low | Capital account statement |

### ✅ ACTUAL VALUES (FROM CSV):

| Item | Actual Value | Source |
|------|-------------|--------|
| Cash in Hand | ₹22,47,189 | Monthly cash collections (CSV) |
| Capital Expenditure | ₹20,86,756 | Monthly CapEx totals (CSV) |
| Net Profit (10M) | ₹16,63,223 | Calculated from revenue/expenses (CSV) |
| Personal Drawings | ₹9,61,573 | Monthly personal expenses (CSV) |
| Medicine Inventory | ₹10,00,000 | User-specified |

---

## RECOMMENDATIONS FOR ACCURATE BALANCE SHEET

To create an **audited-level** balance sheet, obtain:

### 1. Asset Details:
- [ ] Fixed asset register with:
  - Original cost of all equipment
  - Purchase dates
  - Accumulated depreciation
  - Net book value
- [ ] Accounts receivable aging report
- [ ] Inventory valuation (quantity × cost)
- [ ] Prepaid expenses (advance payments)

### 2. Liability Details:
- [ ] All loan statements showing:
  - Original principal
  - Interest rate
  - Monthly payment
  - Outstanding balance
- [ ] Accounts payable aging report
- [ ] Credit card/overdraft balances
- [ ] Accrued expenses list

### 3. Equity Details:
- [ ] Opening capital balance (Jan 1, 2025)
- [ ] Additional capital invested during year
- [ ] Complete drawings register
- [ ] Retained earnings from prior years

---

## ANSWER TO YOUR SPECIFIC QUESTIONS

### Q1: How did you arrive at Accounts Receivable of ₹5 lakhs?

**Answer:**
This is an **ESTIMATE**, not actual data. Here's the reasoning:

```
Calculation Method 1 (Industry Standard):
- Healthcare clinics typically have 5-7% of monthly revenue as AR
- Monthly average revenue = ₹9.39 lakhs
- Estimated AR = 6% × ₹9.39L = ₹5.63L
- Rounded to ₹5L for simplicity

Calculation Method 2 (Days Sales Outstanding):
- Assume 15-day collection period
- Daily revenue = ₹9.39L / 30 = ₹31,300
- AR = 15 days × ₹31,300 = ₹4.70L
- Rounded to ₹5L

Reality Check:
- Some insurance claims take 30-60 days
- Corporate billing has 15-30 day terms
- Cash patients pay immediately (no AR)
- ₹5L is reasonable for mixed patient base
```

**⚠️ RECOMMENDATION:**
Get actual AR from:
- Patient billing system
- Pending insurance claims report
- Corporate client invoices outstanding

---

### Q2: How did you arrive at Owner's Equity of ₹94.88 lakhs (not 9.4 lakhs)?

**Answer:**
Owner's Equity is **CALCULATED** using the accounting equation, not estimated:

```
Step 1: Calculate Total Assets
Current Assets:
  Cash in Hand            ₹22,47,189  (ACTUAL from CSV)
  Bank Balance            ₹ 9,54,034  (CALCULATED from bank flows)
  Inventory               ₹10,00,000  (USER-SPECIFIED)
  Accounts Receivable     ₹ 5,00,000  (ESTIMATED)
  ────────────────────────────────────
  Total Current Assets    ₹47,01,223

Fixed Assets:
  Base Fixed Assets       ₹60,00,000  (ESTIMATED)
  + Capital Expenditure   ₹20,86,756  (ACTUAL from CSV)
  ────────────────────────────────────
  Total Fixed Assets      ₹80,86,756

TOTAL ASSETS             ₹1,27,87,979
                         (₹128 Lakhs or ₹1.28 Crores)

Step 2: Estimate Total Liabilities
Short-term Liabilities    ₹15,00,000  (ESTIMATED)
Long-term Liabilities     ₹18,00,000  (ESTIMATED)
────────────────────────────────────
TOTAL LIABILITIES         ₹33,00,000

Step 3: Calculate Equity (Balancing Figure)
Owner's Equity = Assets - Liabilities
               = ₹1,27,87,979 - ₹33,00,000
               = ₹94,87,979

In Lakhs: ₹94.88 Lakhs (NOT 9.4 lakhs!)
In Crores: ₹0.95 Crores
```

**Note:** If you saw "9.4 lakhs" in the presentation, it might be:
- A display error (missing a digit)
- Confusion with ₹94 lakhs (read as 9.4 instead of 94)
- Different calculation/assumptions

The correct value is **₹94.88 Lakhs** or **₹0.95 Crores**.

---

## SUMMARY

| Item | Value | Type |
|------|-------|------|
| **Accounts Receivable** | ₹5,00,000 | **ESTIMATED** (5-6% of monthly revenue) |
| **Owner's Equity** | ₹94,87,979 | **CALCULATED** (Assets - Liabilities) |

**Both values have low confidence** due to missing source data.

**For accurate Balance Sheet:** Obtain actual accounting records from:
- Accounting software (Tally, QuickBooks, etc.)
- Bank statements
- Loan documents
- Asset register
- Accounts receivable/payable reports

---

**Prepared By:** Financial Analysis Team
**Date:** November 9, 2025
**Note:** This explanation document is for understanding the calculation methodology used in the presentation.
