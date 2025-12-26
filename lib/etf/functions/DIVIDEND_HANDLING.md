# Dividend Handling in ETF System

## Overview

Dividends are handled in **two directions**:
1. **Dividends Received** - Dividends paid by portfolio holdings to the ETF
2. **Dividends Distributed** - Dividends paid by the ETF to shareholders

---

## 1. Dividends Received (From Portfolio Holdings)

### Flow

```
Portfolio Holdings → Corporate Actions → Income Recognition → Accounting → Distribution Calculation
```

### Step-by-Step Process

#### A. Corporate Actions Processing (`core/administration.py`)

**Function**: `FundAdministration.process_corporate_actions(date)`

**What it does**:
1. Fetches corporate actions from data adapter (dividends, splits, etc.)
2. For each dividend received:
   - Identifies which holdings received dividends
   - Records dividend amount per security
   - Updates holdings records
   - Generates corporate action report

**Data Source**:
- **Custodian (US Bank)**: API or SFTP for corporate actions file
- **Corporate Actions Data Provider**: Bloomberg, DTCC, or custodian feed
- **Format**: CSV/Excel or JSON via API
- **Timing**: Available by 6:00 PM ET daily

**Example**:
```python
from lib.etf.functions.core.administration import FundAdministration

admin = FundAdministration(adapter, storage_path="./data/admin")
ca_result = admin.process_corporate_actions(date.today())
# Returns: List of corporate actions including dividends received
```

**Output**: Corporate action records with:
- Security (CUSIP/ticker)
- Action type ("dividend")
- Ex-date
- Pay date
- Amount per share
- Total amount received

---

#### B. Income Recognition (`core/accounting.py`)

**Function**: `Accounting.record_income(income_date, income_data)`

**What it does**:
1. Records dividend income in general ledger:
   - **Debit**: Accrued Income (Account 1300) - Asset account
   - **Credit**: Dividend Income (Account 4000) - Income account
2. Records interest income (if any):
   - **Debit**: Accrued Income (Account 1300)
   - **Credit**: Interest Income (Account 4100)
3. Creates balanced journal entry
4. Updates general ledger

**Accounting Entry**:
```
Debit:  Accrued Income (1300)        $10,000
Credit: Dividend Income (4000)       $10,000
```

**When**: Daily, as dividends are received (via corporate actions)

**Example**:
```python
from lib.etf.functions.core.accounting import Accounting

accounting = Accounting(adapter, storage_path="./data/accounting")
income_data = {
    "dividend_income": Decimal("10000"),  # Total dividends received
    "interest_income": Decimal("500")      # Interest from cash
}
entries = accounting.record_income(date.today(), income_data)
```

**Data Source**:
- **Custodian (US Bank)**: API or SFTP for income data
- **Format**: CSV/Excel or JSON via API
- **Timing**: Available with daily holdings file

---

#### C. NAV Calculation Impact (`core/administration.py`)

**Function**: `FundAdministration.calculate_nav(date)`

**What it does**:
1. Includes accrued income in total assets:
   - `total_assets = securities_value + cash + accrued_income`
2. Accrued income increases NAV until distributed

**Impact**: Dividends received increase NAV (as accrued income) until distributed to shareholders.

---

## 2. Dividends Distributed (To Shareholders)

### Flow

```
Accumulated Dividend Income → Distribution Calculation → Distribution Declaration → Payment → Tax Reporting
```

### Step-by-Step Process

#### A. Distribution Calculation (`operations/distributor.py`)

**Function**: `Distributor.calculate_distribution(dist_date, distribution_type="dividend", ...)`

**What it does**:
1. Gets accumulated dividend income from general ledger:
   - Reads "Dividend Income" account balance (credit balance = income)
   - Converts to positive amount for distribution
2. Applies payout ratio (typically 95-100% for RICs):
   - `distribute_amount = accumulated_income × payout_ratio`
3. Calculates per-share distribution:
   - `amount_per_share = distribute_amount / shares_outstanding`
4. Creates distribution record with dates:
   - Record date (date of declaration)
   - Ex-date (typically same as record date)
   - Pay date (typically 1-2 days after record date)

**Data Source**:
- **Internal**: Uses general ledger data (no external interface needed)
- **NAV Data**: For shares outstanding

**Example**:
```python
from lib.etf.functions.operations.distributor import Distributor

distributor = Distributor(adapter, storage_path="./data/distributor")
ledger_accounts = accounting.list_accounts()  # Get ledger balances

distribution = distributor.calculate_distribution(
    dist_date=date(2024, 3, 31),
    distribution_type="dividend",
    nav_data={"shares_outstanding": Decimal("1000000")},
    payout_ratio=Decimal("0.95"),  # 95% payout
    ledger_data=ledger_accounts
)
# Result: DistributionRecord with amount_per_share = $0.095 (if $100k income, 1M shares, 95% payout)
```

**Key Logic** (from `distributor.py`):
```python
if distribution_type == "dividend":
    if ledger_data and 'Dividend Income' in ledger_data:
        available_income = -Decimal(str(ledger_data.get('Dividend Income', 0)))  # credit balance as positive
        if available_income < 0:
            available_income = Decimal('0')
        # Apply payout ratio
        distribute_amount_total = available_income * payout_ratio
        amount_per_share = distribute_amount_total / shares_outstanding
```

---

#### B. Distribution Declaration (`operations/distributor.py`)

**Function**: `Distributor.declare_distribution(distribution)`

**What it does**:
1. Marks distribution as "declared"
2. Saves distribution record
3. Generates distribution notice
4. Updates accounting (via orchestrator):
   - **Debit**: Dividend Income (Account 4000) - Reduces income
   - **Credit**: Distributions Payable (Account 2000) - Liability

**Accounting Entry** (from `orchestrator.py`):
```python
self.accounting.create_journal_entry(
    entry_date=dist_date,
    description=f"Income distribution on {dist_date}",
    entries=[
        {"account": "4000", "debit": distribution.total_amount},  # Dividend Income (reduces income)
        {"account": "2000", "credit": distribution.total_amount}   # Distributions Payable (liability)
    ]
)
```

**When**: Quarterly (typically end of quarter)

---

#### C. Distribution Payment (`operations/distributor.py`)

**Function**: `Distributor.process_distribution_payment(distribution, shareholder_data)`

**What it does**:
1. Gets distribution record
2. Calculates payment per shareholder:
   - `payment = shares_held × amount_per_share`
3. Records payment in accounting:
   - **Debit**: Distributions Payable (Account 2000) - Reduces liability
   - **Credit**: Cash (Account 1000) - Reduces cash
4. Updates shareholder records (via Transfer Agent)
5. Generates payment file for custodian

**Accounting Entry**:
```
Debit:  Distributions Payable (2000)    $100,000
Credit: Cash (1000)                     $100,000
```

**External Interfaces**:
- **Custodian (US Bank)**: API or email for payment instructions
- **Transfer Agent (US Bank)**: API or email for shareholder records
- **Format**: CSV/Excel or JSON via API
- **Timing**: Submit payment instructions 2-3 days before pay date

**When**: On pay date (typically 1-2 days after record date)

---

## 3. Dividend Flow Summary

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DIVIDENDS RECEIVED (From Portfolio Holdings)            │
└─────────────────────────────────────────────────────────────┘
         │
         ├─→ Corporate Actions Processing
         │   (administration.py)
         │   - Receives dividend from holding (e.g., AAPL pays $0.25/share)
         │
         ├─→ Income Recognition
         │   (accounting.py)
         │   - Debit: Accrued Income (1300)
         │   - Credit: Dividend Income (4000)
         │   - Accumulates in general ledger
         │
         └─→ NAV Calculation
             (administration.py)
             - Accrued income included in total assets
             - NAV increases until distribution

┌─────────────────────────────────────────────────────────────┐
│ 2. DIVIDENDS DISTRIBUTED (To Shareholders)                 │
└─────────────────────────────────────────────────────────────┘
         │
         ├─→ Distribution Calculation
         │   (distributor.py)
         │   - Reads accumulated Dividend Income from ledger
         │   - Applies payout ratio (95-100%)
         │   - Calculates per-share amount
         │
         ├─→ Distribution Declaration
         │   (distributor.py)
         │   - Debit: Dividend Income (4000) - Reduces income
         │   - Credit: Distributions Payable (2000) - Creates liability
         │
         ├─→ Distribution Payment
         │   (distributor.py)
         │   - Debit: Distributions Payable (2000) - Reduces liability
         │   - Credit: Cash (1000) - Reduces cash
         │   - Pays shareholders via custodian
         │
         └─→ Tax Reporting
             (tax_reporting.py)
             - Generates Form 1099-DIV for shareholders
             - Reports distributions to IRS (FIRE)

┌─────────────────────────────────────────────────────────────┐
│ 3. PERFORMANCE CALCULATION                                  │
└─────────────────────────────────────────────────────────────┘
         │
         └─→ Performance Calculation
             (performance.py)
             - Uses distribution history for total return
             - Accounts for dividends in pre-tax/after-tax returns
             - Assumes dividends reinvested for total return calculation
```

---

## 4. Key Accounting Accounts

| Account | Number | Type | Purpose |
|---------|--------|------|---------|
| **Accrued Income** | 1300 | Asset | Holds dividends received but not yet distributed |
| **Dividend Income** | 4000 | Income | Records dividends received from portfolio holdings |
| **Distributions Payable** | 2000 | Liability | Holds declared but not yet paid distributions |
| **Cash** | 1000 | Asset | Cash used to pay distributions |

---

## 5. Example: Complete Dividend Cycle

### Day 1: Dividend Received

**AAPL pays $0.25/share dividend on 1,000 shares held = $250**

1. **Corporate Actions Processing**:
   ```python
   ca_result = admin.process_corporate_actions(date(2024, 3, 15))
   # Returns: [{"security": "AAPL", "type": "dividend", "amount": 250}]
   ```

2. **Income Recognition**:
   ```python
   accounting.record_income(
       date(2024, 3, 15),
       {"dividend_income": Decimal("250")}
   )
   ```
   **Journal Entry**:
   ```
   Debit:  Accrued Income (1300)        $250
   Credit: Dividend Income (4000)       $250
   ```

3. **NAV Impact**:
   - Total assets increase by $250 (accrued income)
   - NAV per share increases (if shares outstanding unchanged)

---

### Quarter End: Distribution Declaration

**Accumulated dividend income = $10,000, Shares outstanding = 1,000,000, Payout ratio = 95%**

1. **Distribution Calculation**:
   ```python
   distribution = distributor.calculate_distribution(
       dist_date=date(2024, 3, 31),
       distribution_type="dividend",
       nav_data={"shares_outstanding": Decimal("1000000")},
       payout_ratio=Decimal("0.95"),
       ledger_data=ledger_accounts
   )
   # Result: amount_per_share = $0.0095 ($10,000 × 0.95 / 1,000,000)
   ```

2. **Distribution Declaration**:
   ```python
   distributor.declare_distribution(distribution)
   ```
   **Journal Entry**:
   ```
   Debit:  Dividend Income (4000)           $9,500
   Credit: Distributions Payable (2000)     $9,500
   ```

---

### Pay Date: Distribution Payment

**Pay date = April 2, 2024**

1. **Distribution Payment**:
   ```python
   distributor.process_distribution_payment(distribution, shareholder_data)
   ```
   **Journal Entry**:
   ```
   Debit:  Distributions Payable (2000)    $9,500
   Credit: Cash (1000)                      $9,500
   ```

2. **Tax Reporting** (Annual):
   ```python
   tax_reporting.generate_1099_div(
       tax_year=2024,
       shareholder=shareholder,
       distributions={"ordinary_dividends": Decimal("9.50")}  # Per shareholder
   )
   ```

---

## 6. Performance Calculation

**Function**: `PerformanceCalculator.compute_performance(...)`

**How dividends are handled**:

1. **Pre-tax Total Return**:
   - Assumes dividends are reinvested
   - Growth factor: `(NAV_curr + distribution) / NAV_prev`
   - Dividends increase total return

2. **After-tax Total Return**:
   - Applies tax rate to distributions (typically 15% for qualified dividends)
   - After-tax distribution: `distribution × (1 - tax_rate)`
   - Growth factor: `(NAV_curr + after_tax_distribution) / NAV_prev`
   - Lower than pre-tax due to taxes

**Example** (from `performance.py`):
```python
# Pre-tax: dividend reinvested fully
growth_factor = (nav_curr + dist) / nav_prev
pre_tax_index *= growth_factor

# After-tax: dividend taxed, remainder reinvested
tax_rate = Decimal(str(tax_rates.get('dividend_tax_rate', 0.15)))
after_tax_dist = dist * (Decimal('1.0') - tax_rate)
after_tax_growth_factor = (nav_curr + after_tax_dist) / nav_prev
after_tax_index *= after_tax_growth_factor
```

---

## 7. Data Sources & Interfaces

### Dividends Received

| Source | Interface | Format | Timing |
|--------|-----------|--------|--------|
| **Custodian (US Bank)** | API or SFTP | CSV/Excel or JSON | Daily, by 6:00 PM ET |
| **Corporate Actions Provider** | API | JSON or CSV | Daily, by 6:00 PM ET |
| **Bloomberg/DTCC** | API | JSON | Real-time or daily |

### Dividends Distributed

| Source | Interface | Format | Timing |
|--------|-----------|--------|--------|
| **Internal (General Ledger)** | N/A | Internal data | On-demand |
| **Custodian (US Bank)** | API or Email | CSV/Excel or JSON | Payment instructions 2-3 days before pay date |
| **Transfer Agent (US Bank)** | API or Email | CSV/Excel or JSON | With payment instructions |
| **IRS FIRE** | API | IRS MMF/XML | By March 31 (annual) |

---

## 8. Key Points

1. **Dividends Received** are recorded as **income** (increases NAV)
2. **Dividends Distributed** are recorded as **reductions to income** and **liabilities** (reduces NAV)
3. **Payout Ratio** determines how much income to distribute (typically 95-100% for RICs)
4. **Accrued Income** holds dividends received but not yet distributed
5. **Distributions Payable** holds declared but not yet paid distributions
6. **Performance Calculation** accounts for dividends in total return (reinvested for pre-tax, taxed for after-tax)

---

## 9. Regulatory Requirements

- **RIC Distribution Requirements**: Must distribute 98% of ordinary income and 98.2% of capital gains to avoid corporate taxation
- **Form 1099-DIV**: Must be provided to shareholders by January 31
- **IRS FIRE Filing**: Must file 1099-DIV electronically with IRS by March 31
- **Distribution Limits**: Limited to 12 distributions per year (per US Bank requirements)

---

## 10. Code References

- **Corporate Actions**: `lib/etf/functions/core/administration.py` → `process_corporate_actions()`
- **Income Recognition**: `lib/etf/functions/core/accounting.py` → `record_income()`
- **Distribution Calculation**: `lib/etf/functions/operations/distributor.py` → `calculate_distribution()`
- **Distribution Declaration**: `lib/etf/functions/operations/distributor.py` → `declare_distribution()`
- **Distribution Payment**: `lib/etf/functions/operations/distributor.py` → `process_distribution_payment()`
- **Tax Reporting**: `lib/etf/functions/tax/tax_reporting.py` → `generate_1099_div()`
- **Performance**: `lib/etf/functions/operations/performance.py` → `compute_performance()`

