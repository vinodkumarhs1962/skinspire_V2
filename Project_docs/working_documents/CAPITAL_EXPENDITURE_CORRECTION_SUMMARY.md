# Capital Expenditure Correction Summary

## Date: November 9, 2025

## Issue Identified

The original financial analysis **incorrectly calculated Capital Expenditure** by not including all components.

---

## Original vs Corrected CapEx Breakdown

### What Was Missing:

**Original Calculation (INCORRECT):**
- Only included: Capital expenses + Loan interest
- **Total**: ₹13,17,756

**Corrected Calculation (CORRECT):**
- Now includes: Capital expenses + **Capital Expenditure CASH** + Loan interest
- **Total**: ₹20,86,756

**Difference**: ₹7,69,000 (58% increase)

---

## Monthly Capital Expenditure - Corrected Values

| Month | Original (₹) | Corrected (₹) | Change (₹) |
|-------|-------------|---------------|------------|
| Jan-25 | 40,499 | 40,499 | 0 |
| Feb-25 | 184,674 | **354,674** | +170,000 |
| Mar-25 | 154,273 | **404,273** | +250,000 |
| Apr-25 | 145,188 | **395,188** | +250,000 |
| May-25 | 375,636 | **405,636** | +30,000 |
| Jun-25 | 141,317 | 141,317 | 0 |
| Jul-25 | 88,612 | **157,612** | +69,000 |
| Aug-25 | 101,979 | 101,979 | 0 |
| Sep-25 | 66,662 | 66,662 | 0 |
| Oct-25 | 18,916 | 18,916 | 0 |
| **TOTAL** | **13,17,756** | **20,86,756** | **+7,69,000** |

---

## Impact on Net Profit - Corrected Values

The increased CapEx significantly reduced net profit for several months:

| Month | Original Net Profit (₹) | Corrected Net Profit (₹) | Change (₹) |
|-------|------------------------|-------------------------|------------|
| Jan-25 | 385,901 | 385,901 | 0 |
| Feb-25 | -201,319 | **-371,319** | -170,000 |
| Mar-25 | 253,142 | **3,142** | -250,000 |
| Apr-25 | 270,615 | **20,615** | -250,000 |
| May-25 | -29,086 | **-59,086** | -30,000 |
| Jun-25 | 195,833 | 195,833 | 0 |
| Jul-25 | 908,366 | **839,366** | -69,000 |
| Aug-25 | 604,753 | 604,753 | 0 |
| Sep-25 | -40,448 | -40,448 | 0 |
| Oct-25 | 84,466 | 84,466 | 0 |
| **TOTAL** | **24,32,223** | **16,63,223** | **-7,69,000** |

---

## Key Changes to Financial Metrics

### 10-Month Performance (Jan-Oct 2025):

| Metric | Original | Corrected | Change |
|--------|----------|-----------|--------|
| **Total Revenue** | ₹93,95,272 | ₹93,95,272 | No change |
| **Gross Profit** | ₹47,11,552 | ₹47,11,552 | No change |
| **Total CapEx** | ₹13,17,756 | ₹20,86,756 | +₹7,69,000 |
| **Net Profit** | ₹24,32,223 | **₹16,63,223** | -₹7,69,000 |
| **Net Margin** | 25.89% | **17.70%** | -8.19% |

### Full Year 2025 Projection (Jan-Dec):

| Metric | Original | Corrected | Change |
|--------|----------|-----------|--------|
| **Total Revenue** | ₹1,11,45,272 | ₹1,11,45,272 | No change |
| **Total CapEx** | ₹13,17,756 | ₹20,86,756 | +₹7,69,000 |
| **Net Profit** | ₹30,94,223 | **₹23,25,223** | -₹7,69,000 |
| **Net Margin** | 27.8% | **20.9%** | -6.9% |

---

## Impact on Key Insights

### Profitable Months Analysis:

**Original**: 7 out of 10 months profitable (70%)
**Corrected**: 5 out of 10 months profitable (50%)

**Loss-Making Months:**

Original (3 months):
- February: -₹2.01L
- May: -₹0.29L
- September: -₹0.40L

Corrected (5 months):
- **February: -₹3.71L** (worse)
- **March: +₹3K** (barely break-even)
- **April: +₹21K** (barely break-even)
- **May: -₹0.59L** (worse)
- September: -₹0.40L (same)

### CapEx as % of Gross Profit:

- **Original**: 27.97%
- **Corrected**: **44.29%**

This means nearly **half of the gross profit** was consumed by capital expenditure!

---

## Revised Critical Issues

### Issue #1: High Capital Expenditure (NEW)

**Problem:**
- CapEx consumed 44.29% of gross profit
- Major equipment investments in Feb-May (₹17.3L in 4 months)
- Significantly reduced net profitability

**Impact:**
- Net margin reduced from 25.9% to 17.7%
- Only 5/10 months profitable (not 7/10)
- Feb-Apr almost break-even despite good gross margins

**Action Required:**
- Review ROI on capital investments
- Defer non-essential CapEx purchases
- Spread major investments over longer periods
- Ensure capital investments generate revenue

### Issue #2: Cash Flow Implications

**Additional Concern:**
- Cash CapEx of ₹7.69L directly impacted cash position
- February-April saw ₹6.7L cash outflow for equipment
- This explains negative bank flow in those months

---

## Updated P&L Statement (Jan-Dec 2025)

```
INCOME
  Total Revenue                      ₹1,11,45,272   100.0%

COST OF OPERATIONS
  Operating Expenses                 ₹  55,58,720    49.9%

GROSS PROFIT                         ₹  55,86,552    50.1%

OTHER EXPENSES
  Capital Expenditure*               ₹  20,86,756    18.7%
    (Equipment + Cash CapEx + Loan Interest)
  Personal Expenses                  ₹  11,36,573    10.2%

NET PROFIT                           ₹  23,25,223    20.9%

* Capital Expenditure includes:
  - Regular capital expenses: ₹10.79L
  - Cash capital expenditure: ₹7.69L
  - Loan interest: ₹2.38L
  Total: ₹20.87L
```

---

## Files Updated

1. **Presentation File**: `Skinspire_Financial_Analysis_2025_Corrected.pptx`
   - All CapEx values corrected
   - Net profit values updated
   - Charts and metrics reflect corrected data
   - P&L statement updated with note explaining CapEx components

2. **Python Script**: `generate_formatted_ppt.py`
   - Monthly data dictionary updated
   - P&L calculation corrected
   - Added footnote explaining CapEx composition

3. **Source Data**: `Clinic expenses analysis.csv`
   - Row 16 "Capital Expenditure" now correctly combines all components

---

## Recommendations (Updated)

### High Priority:

1. **Capital Expenditure Management**
   - Review all CapEx for ROI justification
   - Defer non-critical equipment purchases to FY 2026
   - Negotiate vendor financing for major equipment
   - **Savings Potential**: ₹5-8L by deferring non-essential CapEx

2. **Cash Flow Protection**
   - Major cash CapEx (Feb-Apr: ₹6.7L) created liquidity stress
   - Future equipment purchases should be:
     - Spread over multiple months
     - Financed through loans (preserve cash)
     - Justified with revenue impact analysis

3. **Profitability Improvement**
   - With corrected data, net margin is 20.9% (not 27.8%)
   - Target: Improve to 25%+ through:
     - OpEx reduction: 50% → 45% (saves ₹5L annually)
     - Revenue growth: 15-20%
     - CapEx discipline

---

## Revised FY 2026 Targets

With corrected baseline (FY 2025: 20.9% net margin):

| Metric | FY 2025 Corrected | FY 2026 Target | Change |
|--------|------------------|----------------|--------|
| Revenue | ₹1.11 Cr | ₹1.35 Cr | +22% |
| Operating Expense % | 49.9% | 45.0% | -4.9% |
| Capital Expenditure | ₹20.9L | ₹10.0L | -52% |
| Net Profit | ₹23.3L | ₹42.0L | +80% |
| Net Margin | 20.9% | 31.0% | +10.1% |

---

## Conclusion

The **corrected capital expenditure calculation** reveals:

✅ **More Accurate Picture**: True net profit is ₹16.6L (not ₹24.3L)
⚠️ **Higher CapEx Burden**: 44% of gross profit consumed by CapEx
🔴 **Lower Profitability**: Net margin 17.7% (not 25.9%)
⚠️ **More Loss Months**: 5 months with losses/break-even (not 3)

**Critical Action**: Capital expenditure discipline is now the #1 priority for improving profitability.

---

**Updated**: November 9, 2025
**Prepared By**: Financial Analysis Team
**Confidential**
