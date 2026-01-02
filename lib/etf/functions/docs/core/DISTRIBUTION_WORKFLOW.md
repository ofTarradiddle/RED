# ETF Distribution Workflow - Operational Implementation

## Overview

This document describes the complete operational distribution workflow implemented per industry standards and SEC Form N-1A requirements.

## What is a Distribution?

In ETF fund accounting, a "distribution" is a per-share amount paid to shareholders that comes from:

1. **Net Investment Income (NII)**: Dividends, interest, securities lending income
2. **Net Realized Capital Gains**: Gains from selling portfolio holdings
3. **Return of Capital (ROC)**: Tax recharacterization (excess of taxable earnings)

**Key Point**: NAV already "builds up" the distribution via daily accruals. When you buy shares, NAV may reflect undistributed income/gains, and a later distribution can be taxable even if it's economically just returning part of what you paid ("buying a dividend").

## Daily Building Blocks

### Income Recognition (Increases NII)

**GAAP Policy**:
- Trades recorded trade date
- Dividend income recognized on ex-dividend date
- Distributions to shareholders recorded on ex-dividend date

**Operational Accumulation**:
- Dividend receivable (equity)
- Interest receivable (bonds)
- Securities lending receivable
- Cash interest receivable

### Expense Recognition (Reduces NII)

**Daily Expense Accrual**:
```
Daily expense = (annual expense rate × that day's net assets) ÷ day-count basis
```

### Result: Daily NII and UNII

**NII (period)** = (dividends + interest + other income) − (expenses)

**UNII (Undistributed Net Investment Income)** = Cumulative NII not yet distributed

## Complete Distribution Workflow (6 Steps)

### Step 1: Lock Distribution Period and Cut-Off

Most ETFs distribute on a schedule (monthly/quarterly/annual). The administrator sets a cut-off date/time aligned to NAV cut-off and the announced record/ex-date cycle.

**Implementation**: `DistributionManager.calculate_distribution()` automatically determines the period based on distribution date.

### Step 2: Compute Income Available for Distribution

**Formula**:
```
Income Available = Beginning UNII + Period NII - Prior Income Distributions
```

**Where**:
- Beginning UNII = Cumulative NII from prior periods not yet distributed
- Period NII = Income - Expenses for the period
- Prior Income Distributions = Income distributions already paid in period

**Implementation**: `DistributionManager.calculate_income_available_for_distribution()`

### Step 3: Compute Capital Gain Available for Distribution

**Formula**:
```
Capital Gain Available = Net Realized Gains - Prior Capital Gain Distributions - In-Kind Adjustments
```

**Important**: In-kind redemptions generate GAAP gains but are NOT taxable/distributable. These must be subtracted.

**Implementation**: `DistributionManager.calculate_capital_gain_available()`

### Step 4: Apply Distribution Requirements (RIC + Excise)

Most ETFs aim to distribute enough to avoid entity-level tax and minimize excise tax.

**Excise Tax Requirements (IRC §4982)**:
- 98% of ordinary income for calendar year
- 98.2% of capital gain net income for one-year period ending October 31
- Plus prior-year shortfalls

**Implementation**: Applied via `payout_ratio` parameter (typically 95-100%)

### Step 5: Determine Shares Entitled to Distribution

For ETFs, the shareholder of record is generally DTC/its participants. The admin uses:
- Shares outstanding as of record date (from transfer agent/DTC records)
- Ensures creations/redemptions are properly reflected as of record cut-off

**Implementation**: `shares_outstanding` parameter provided to `calculate_distribution()`

### Step 6: Convert Dollars to Per-Share Distribution Rate

**Formula**:
```
Distribution per share = Total distribution dollars / Shares outstanding on record date
```

**Operational Standard**: 
- Round per-share amount per fund convention
- Recalculate total based on rounded per-share × shares outstanding
- Ensures payable reconciles to rounded rate

**Implementation**: Automatically handled in `calculate_distribution()`

## Accounting Entries

### Declaration (Ex-Date)

**Income Distribution**:
```
Dr. UNII (or Dividend Income)          $X
Cr. Distributions Payable              $X
```

**Capital Gain Distribution**:
```
Dr. Accumulated Net Realized Gains     $X
Cr. Distributions Payable              $X
```

**Implementation**: `DistributionManager.record_distribution_declaration()`

### Payment (Payable Date)

```
Dr. Distributions Payable              $X
Cr. Cash                               $X
```

**Implementation**: `DistributionManager.record_distribution_payment()`

### NAV Effect

NAV per share should drop by the distribution per share on the ex-date (all else equal), since net assets are reduced / liability recorded.

## Usage Example

```python
from lib.etf.functions.core import Accounting, DistributionManager
from datetime import date
from decimal import Decimal

# Initialize
accounting = Accounting(adapter, storage_path="./data/accounting")
dist_manager = DistributionManager(accounting, storage_path="./data/distributions")

# Calculate distribution for quarter end
distribution_date = date(2024, 12, 31)
shares_outstanding = Decimal('20000000')  # From custodian/TA

# Step 1-6: Calculate distribution
calc = dist_manager.calculate_distribution(
    distribution_date=distribution_date,
    distribution_type="income",
    shares_outstanding=shares_outstanding,
    payout_ratio=Decimal('0.95'),  # 95% payout
    equalization_reduction=Decimal('0')
)

# Record declaration (ex-date)
ex_date = date(2024, 12, 30)
record_date = ex_date
payable_date = date(2024, 12, 31)

declaration = dist_manager.record_distribution_declaration(
    distribution_date=distribution_date,
    distribution_calc=calc,
    ex_date=ex_date,
    record_date=record_date,
    payable_date=payable_date
)

# Record payment (payable date)
payment = dist_manager.record_distribution_payment(
    payable_date=payable_date,
    distribution_record=declaration
)
```

## Complex Issues Handled

### A. Book vs Tax Differences

- Distributions determined under income tax regs may differ from GAAP
- Final tax character determined at fiscal year end
- Some pre-year-end distributions may become ROC for tax

### B. In-Kind Redemptions

- GAAP: Treated as sales (realized gain/loss)
- Tax: Not taxable under IRC §852(b)(6)
- Operational: Reclassified from accumulated net realized gain to paid-in capital at tax year end

### C. Foreign Currency / PFIC / REIT

- May require distributing income not yet received
- FX can affect distribution character
- May require sales to fund distributions

## Files

- **Distribution Manager**: `lib/etf/functions/core/distribution_manager.py`
- **Accounting**: `lib/etf/functions/core/accounting.py`
- **SEC Reporting**: `lib/etf/functions/core/sec_reporting.py`

## References

- SEC Form N-1A Instructions
- IRC §852 (RIC distribution requirements)
- IRC §4982 (Excise tax requirements)
- Industry operational standards (DST, Allspring examples)

