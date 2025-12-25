# ETF Administration & Accounting: Complete Responsibilities & Implementation Guide

## Table of Contents
1. [Overview: ETF Servicer Responsibilities](#overview)
2. [Daily Operations (T+0)](#daily-operations)
3. [Weekly Operations](#weekly-operations)
4. [Monthly Operations](#monthly-operations)
5. [Quarterly Operations](#quarterly-operations)
6. [Annual Operations](#annual-operations)
7. [Ad-Hoc Operations](#ad-hoc-operations)
8. [Regulatory Compliance Mapping](#regulatory-compliance)
9. [Function Reference](#function-reference)

---

## Overview: ETF Servicer Responsibilities {#overview}

### What is ETF Administration & Accounting?

ETF administration and accounting is the complete operational infrastructure that ensures:
1. **Accurate Valuation**: Daily NAV calculation using correct pricing methodologies
2. **Financial Integrity**: Double-entry accounting with full audit trail
3. **Regulatory Compliance**: SEC filings, tax reporting, and recordkeeping
4. **Shareholder Services**: Distribution processing, tax lot tracking, performance reporting
5. **Operational Control**: Reconciliation, validation, and error detection

### Core Responsibilities

#### **Fund Administration**
- Daily NAV calculation and publication
- Portfolio holdings reconciliation
- Corporate actions processing
- Expense management and accruals
- Cash management
- Regulatory filing preparation (N-PORT, N-CEN, N-CSR)
- Board reporting and materials

#### **Fund Accounting**
- Double-entry general ledger maintenance
- Journal entry recording and validation
- Trial balance generation
- Financial statement preparation (Balance Sheet, Income Statement)
- NAV entry recording
- Expense accrual and income recognition
- Account reconciliation

#### **Tax Accounting**
- Tax lot tracking (FIFO/LIFO)
- Realized/unrealized gain/loss calculation
- Short-term vs long-term classification
- Form 1099 generation (1099-DIV, 1099-B, 1099-INT)
- Form 1120-RIC preparation
- Form 8613 (Excise Tax) calculation
- IRS electronic filing (FIRE)

#### **Performance & Reporting**
- Pre-tax and after-tax total return calculation
- Benchmark comparison
- Tax efficiency analysis
- Annual and cumulative performance reporting

---

## Daily Operations (T+0) {#daily-operations}

**Timing**: Each business day, typically after market close (4:00 PM ET)

### 1. NAV Calculation
**Responsibility**: Calculate the fund's Net Asset Value per share using closing prices

**Our Implementation**:
- **Function**: `FundAdministration.calculate_nav(date)`
- **Location**: `lib/etf/functions/administration.py`
- **What it does**:
  1. Fetches portfolio holdings from data adapter
  2. Gets market prices for all securities (via yfinance or market data provider)
  3. Calculates total assets (securities + cash)
  4. Subtracts total liabilities (accrued expenses, payables)
  5. Divides by shares outstanding to get NAV per share
  6. Validates calculation (checks for pricing exceptions, missing data)
  7. Saves NAV to history file

**Regulatory Requirement**: SEC Rule 2a-5 (Valuation), Rule 6c-11 (ETF NAV disclosure)

**Output**: `NAVCalculation` object with:
- NAV per share
- Total assets, liabilities, net assets
- Shares outstanding
- Validation status
- Pricing exceptions (if any)

**Example**:
```python
from lib.etf.functions.administration import FundAdministration
from lib.etf.adapters import FileBasedDataSourceAdapter

admin = FundAdministration(adapter, storage_path="./data/admin")
nav_calc = admin.calculate_nav(date.today())
# Result: NAV = $25.50 per share
```

---

### 2. Accounting: NAV Entry Recording
**Responsibility**: Record NAV calculation in general ledger using double-entry accounting

**Our Implementation**:
- **Function**: `Accounting.record_nav_entries(date, nav_calculation)`
- **Location**: `lib/etf/functions/accounting.py`
- **What it does**:
  1. Creates journal entry:
     - Debit: Investments - Securities (total assets)
     - Credit: Liabilities (total liabilities)
     - Credit: Net Assets (net assets = assets - liabilities)
  2. Validates entry is balanced (debits = credits)
  3. Posts to general ledger
  4. Saves to persistent storage

**Regulatory Requirement**: SEC Rule 31a-2 (Books and Records)

**Accounting Equation**: Assets = Liabilities + Net Assets

**Example**:
```python
from lib.etf.functions.accounting import Accounting

accounting = Accounting(adapter, storage_path="./data/accounting")
entries = accounting.record_nav_entries(date.today(), nav_calc)
# Creates balanced journal entry in general ledger
```

---

### 3. Accounting: Daily Operations
**Responsibility**: Record all daily accounting transactions (expenses, income, NAV)

**Our Implementation**:
- **Function**: `Accounting.daily_accounting_operations(date, nav_calculation)`
- **Location**: `lib/etf/functions/accounting.py`
- **What it does** (in order):
  1. Records NAV entries (see above)
  2. Records expense accruals (management fees, admin fees, etc.)
  3. Records income (dividends received, interest income)
  4. Generates trial balance to verify books are balanced

**Regulatory Requirement**: SEC Rule 31a-2 (Daily recordkeeping)

**Example**:
```python
accounting.daily_accounting_operations(date.today(), nav_calc)
# Automatically handles NAV, expenses, income, and trial balance
```

---

### 4. Holdings & Cash Reconciliation
**Responsibility**: Verify portfolio holdings match custodian records

**Our Implementation**:
- **Function**: `FundAdministration.reconcile_holdings_cash(date)`
- **Location**: `lib/etf/functions/administration.py`
- **What it does**:
  1. Gets portfolio holdings from data adapter
  2. Gets custodian statement for the date
  3. Compares:
     - Security quantities (portfolio vs custodian)
     - Cash balances
     - Total shares outstanding
  4. Identifies discrepancies
  5. Generates reconciliation report

**Regulatory Requirement**: SEC Rule 17f-2 (Custody verification)

**Output**: `ReconciliationResult` with:
- Matched items
- Discrepancies (if any)
- Reconciliation status

**Example**:
```python
recon_result = admin.reconcile_holdings_cash(date.today())
if not recon_result.reconciled:
    # Investigate discrepancies
    print(f"Discrepancies: {recon_result.discrepancies}")
```

---

### 5. Corporate Actions Processing
**Responsibility**: Process dividends, splits, mergers, and other corporate actions

**Our Implementation**:
- **Function**: `FundAdministration.process_corporate_actions(date)`
- **Location**: `lib/etf/functions/administration.py`
- **What it does**:
  1. Fetches corporate actions for the date (dividends, splits, etc.)
  2. For dividends:
     - Records dividend income in accounting
     - Updates tax lot cost basis (if applicable)
  3. For stock splits:
     - Adjusts share quantities
     - Adjusts cost basis per share
  4. Updates holdings records
  5. Generates corporate action report

**Regulatory Requirement**: SEC Rule 2a-5 (Valuation of corporate actions)

**Example**:
```python
ca_result = admin.process_corporate_actions(date.today())
# Processes dividends, splits, and other corporate actions
```

---

### 6. Tax Lot Tracking (Trade Processing)
**Responsibility**: Track cost basis for tax purposes when securities are bought/sold

**Our Implementation**:
- **Function**: `TaxLotManager.add_lot()` and `TaxLotManager.sell()`
- **Location**: `lib/etf/functions/tax_lot.py`
- **What it does**:
  1. **On Purchase**: Creates tax lot with:
     - Purchase date
     - Quantity
     - Cost basis
     - CUSIP/ticker
  2. **On Sale**: Uses FIFO (default) or LIFO:
     - Identifies lots to sell
     - Calculates realized gain/loss
     - Classifies as short-term (<365 days) or long-term (≥365 days)
     - Updates open lots
  3. **Unrealized Gains**: Calculates unrealized gains for open lots

**Regulatory Requirement**: IRS regulations (Section 1012 - Cost basis)

**Example**:
```python
from lib.etf.functions.tax_lot import TaxLotManager

taxlot = TaxLotManager(storage_path="./data/tax_lots")
# Add lot on purchase
taxlot.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))
# Sell shares
gain = taxlot.sell("AAPL", Decimal('50'), Decimal('160.00'), date(2024, 6, 15))
# gain = $500 (50 shares × $10 gain), classified as short-term
```

---

### 7. Daily Orchestrator (All-in-One)
**Responsibility**: Coordinate all daily operations in correct sequence

**Our Implementation**:
- **Function**: `DailyOrchestrator.run_daily_operations(date)`
- **Location**: `lib/etf/functions/orchestrator.py`
- **What it does** (in chronological order):
  1. Calculate NAV
  2. Record NAV in accounting
  3. Process scheduled trades (update tax lots, accounting)
  4. Reconcile holdings and cash
  5. Process corporate actions
  6. Check for distribution dates (quarterly)
  7. Run year-end tasks (if fiscal year end)

**Usage**:
```python
from lib.etf.functions.orchestrator import DailyOrchestrator

orchestrator = DailyOrchestrator(adapter, config_path="config.yaml")
results = orchestrator.run_daily_operations(date.today())
# Runs all daily operations automatically
```

---

## Weekly Operations {#weekly-operations}

**Timing**: Typically end of week (Friday)

### 1. Weekly Reconciliation Summary
**Responsibility**: Generate weekly summary of all reconciliations

**Our Implementation**:
- **Function**: Run daily reconciliation, then aggregate results
- **What it does**:
  - Summarizes daily reconciliation results for the week
  - Identifies recurring discrepancies
  - Generates weekly reconciliation report

---

## Monthly Operations {#monthly-operations}

**Timing**: Within 30 days after month end

### 1. Form N-PORT Filing
**Responsibility**: File monthly portfolio holdings and risk metrics with SEC

**Our Implementation**:
- **Function**: `Compliance.generate_form_n_port(month_end_date)`
- **Location**: `lib/etf/functions/compliance.py`
- **What it does**:
  1. Collects portfolio holdings as of month end
  2. Calculates risk metrics (duration, credit quality, etc.)
  3. Generates N-PORT XML file
  4. Validates against SEC schema
  5. Prepares for EDGAR filing

**Regulatory Requirement**: SEC Form N-PORT (monthly, public 60 days after filing)

**Due Date**: 30 days after month end

**Example**:
```python
from lib.etf.functions.compliance import Compliance

compliance = Compliance(adapter, storage_path="./data/compliance")
n_port = compliance.generate_form_n_port(date(2024, 3, 31))
# Generates N-PORT for March 2024
```

---

### 2. Monthly Financial Statements
**Responsibility**: Generate monthly balance sheet and income statement

**Our Implementation**:
- **Function**: `Accounting.generate_balance_sheet()` and `Accounting.generate_income_statement()`
- **Location**: `lib/etf/functions/accounting.py`
- **What it does**:
  1. **Balance Sheet**:
     - Assets (Cash, Investments, Receivables)
     - Liabilities (Payables, Accrued Expenses)
     - Net Assets (Share Capital, Retained Earnings)
  2. **Income Statement**:
     - Income (Dividends, Interest, Realized Gains)
     - Expenses (Management Fees, Admin Fees, etc.)
     - Net Investment Income

**Regulatory Requirement**: SEC Rule 31a-2 (Monthly financials for board)

**Example**:
```python
balance_sheet = accounting.generate_balance_sheet(
    period_end=date(2024, 3, 31)
)
income_stmt = accounting.generate_income_statement(
    period_start=date(2024, 3, 1),
    period_end=date(2024, 3, 31)
)
```

---

## Quarterly Operations {#quarterly-operations}

**Timing**: End of quarter (Mar 31, Jun 30, Sep 30, Dec 31)

### 1. Distribution Calculation & Declaration
**Responsibility**: Calculate and declare quarterly distributions (dividends, capital gains)

**Our Implementation**:
- **Function**: `Distributor.calculate_distribution()` and `Distributor.declare_distribution()`
- **Location**: `lib/etf/functions/distributor.py`
- **What it does**:
  1. Calculates distributable income from ledger:
     - Dividend income received
     - Interest income
     - Realized capital gains (if any)
  2. Applies payout ratio (typically 95-100% for RICs)
  3. Calculates per-share distribution amount
  4. Declares distribution (records in system)
  5. Updates accounting (Distributions Payable)

**Regulatory Requirement**: IRS Section 852 (RIC distribution requirements)

**Example**:
```python
from lib.etf.functions.distributor import Distributor

distributor = Distributor(adapter, storage_path="./data/distributor")
distribution = distributor.calculate_distribution(
    dist_date=date(2024, 3, 31),
    distribution_type="dividend",
    nav_data={"shares_outstanding": Decimal('1000000')},
    payout_ratio=Decimal('0.95'),
    ledger_data=ledger_accounts
)
# Calculates 95% of distributable income
distributor.declare_distribution(distribution)
# Records distribution declaration
```

---

### 2. Distribution Payment Processing
**Responsibility**: Process distribution payments to shareholders

**Our Implementation**:
- **Function**: `Distributor.process_distribution_payment(distribution_id)`
- **Location**: `lib/etf/functions/distributor.py`
- **What it does**:
  1. Gets distribution record
  2. Calculates total distribution amount
  3. Records payment in accounting:
     - Debit: Distributions Payable
     - Credit: Cash
  4. Updates shareholder records (via Transfer Agent)
  5. Generates payment file for custodian

**Regulatory Requirement**: SEC Rule 22c-1 (Distribution timing)

**Example**:
```python
distributor.process_distribution_payment(distribution.distribution_id)
# Processes payment and updates accounting
```

---

### 3. Form N-Q Filing (Quarterly)
**Responsibility**: File quarterly shareholder report with SEC

**Our Implementation**:
- **Function**: `Compliance.generate_form_n_q(quarter_end_date)`
- **Location**: `lib/etf/functions/compliance.py`
- **What it does**:
  1. Collects portfolio holdings as of quarter end
  2. Generates schedule of investments
  3. Includes financial statements
  4. Generates N-Q XML file
  5. Prepares for EDGAR filing

**Regulatory Requirement**: SEC Form N-Q (quarterly, public filing)

**Due Date**: 60 days after quarter end

**Example**:
```python
n_q = compliance.generate_form_n_q(date(2024, 3, 31))
# Generates N-Q for Q1 2024
```

---

## Annual Operations {#annual-operations}

**Timing**: Within deadlines after fiscal year end

### 1. Form N-CEN Filing
**Responsibility**: File annual census report with SEC

**Our Implementation**:
- **Function**: `Compliance.generate_form_n_cen(fiscal_year_end)`
- **Location**: `lib/etf/functions/compliance.py`
- **What it does**:
  1. Collects fund census data:
     - Shares outstanding
     - Total net assets
     - Number of shareholders
     - Expense ratios
  2. Generates N-CEN XML file
  3. Prepares for EDGAR filing

**Regulatory Requirement**: SEC Form N-CEN (annual)

**Due Date**: 75 days after fiscal year end

**Example**:
```python
n_cen = compliance.generate_form_n_cen(date(2024, 12, 31))
# Generates N-CEN for fiscal year 2024
```

---

### 2. Form N-CSR Filing (Annual Report)
**Responsibility**: File annual shareholder report with SEC (Tailored Shareholder Report)

**Our Implementation**:
- **Function**: `Compliance.generate_form_n_csr(fiscal_year_end, report_type="annual")`
- **Location**: `lib/etf/functions/compliance.py`
- **What it does**:
  1. Generates Tailored Shareholder Report (TSR):
     - Performance summary
     - Expense example
     - Portfolio holdings
     - Financial statements
  2. Includes Inline XBRL tagging
  3. Generates N-CSR XML file
  4. Prepares for EDGAR filing

**Regulatory Requirement**: SEC Form N-CSR (annual, Tailored Shareholder Report)

**Due Date**: 10 days after transmission to shareholders

**Example**:
```python
n_csr = compliance.generate_form_n_csr(
    date(2024, 12, 31),
    report_type="annual"
)
# Generates annual N-CSR for 2024
```

---

### 3. Tax Reporting: Form 1099 Generation
**Responsibility**: Generate Form 1099-DIV, 1099-B, 1099-INT for shareholders

**Our Implementation**:
- **Function**: `TaxReporting.generate_1099_div()`, `generate_1099_b()`, `generate_1099_int()`
- **Location**: `lib/etf/functions/tax_reporting.py`
- **What it does**:
  1. **Form 1099-DIV**:
     - Dividends paid per shareholder
     - Qualified vs non-qualified dividends
     - Capital gain distributions
  2. **Form 1099-B**:
     - Proceeds from sales (if applicable)
     - Cost basis (if reported)
  3. **Form 1099-INT**:
     - Interest income (if applicable)
  4. Generates forms for each shareholder
  5. Prepares for IRS electronic filing (FIRE)

**Regulatory Requirement**: IRS regulations (Form 1099 series)

**Due Date**: January 31 (to shareholders), March 31 (to IRS)

**Example**:
```python
from lib.etf.functions.tax_reporting import TaxReporting

tax_reporting = TaxReporting(adapter, storage_path="./data/tax")
forms = tax_reporting.generate_all_1099_forms(
    tax_year=2024,
    shareholder_data=shareholder_records
)
# Generates all 1099 forms for 2024
```

---

### 4. Tax Reporting: Form 1120-RIC
**Responsibility**: Prepare corporate tax return for Registered Investment Company

**Our Implementation**:
- **Function**: `TaxReporting.generate_tax_return_form_1120_ric(tax_year, ledger_data, taxlot_manager, distributions)`
- **Location**: `lib/etf/functions/tax_reporting.py`
- **What it does**:
  1. Calculates investment company taxable income:
     - Dividend income
     - Interest income
     - Realized capital gains
  2. Calculates dividends paid deduction
  3. Calculates taxable income after deduction
  4. Calculates corporate tax due (21% rate)
  5. Generates Form 1120-RIC data

**Regulatory Requirement**: IRS Form 1120-RIC (annual corporate tax return)

**Due Date**: March 15 (calendar year) or 15th day of 3rd month after fiscal year end

**Example**:
```python
form_1120_ric = tax_reporting.generate_tax_return_form_1120_ric(
    tax_year=2024,
    ledger_data=ledger_accounts,
    taxlot_manager=taxlot_manager,
    distributions=distributions_list
)
# Generates Form 1120-RIC for 2024
```

---

### 5. Tax Reporting: Form 8613 (Excise Tax)
**Responsibility**: Calculate and report excise tax on undistributed income

**Our Implementation**:
- **Function**: `TaxReporting.generate_form_8613(tax_year, ledger_data, taxlot_manager, distributions)`
- **Location**: `lib/etf/functions/tax_reporting.py`
- **What it does**:
  1. Calculates required distribution (98% of ordinary income, 98.2% of capital gains)
  2. Compares to actual distributions made
  3. Calculates undistributed amount (shortfall)
  4. Calculates excise tax (4% of shortfall)
  5. Generates Form 8613 data

**Regulatory Requirement**: IRS Form 8613 (Excise Tax on Regulated Investment Companies)

**Due Date**: March 15 (calendar year)

**Example**:
```python
form_8613 = tax_reporting.generate_form_8613(
    tax_year=2024,
    ledger_data=ledger_accounts,
    taxlot_manager=taxlot_manager,
    distributions=distributions_list
)
# Generates Form 8613 for 2024
```

---

### 6. Performance Calculation (Annual)
**Responsibility**: Calculate annual performance (pre-tax and after-tax)

**Our Implementation**:
- **Function**: `PerformanceCalculator.compute_performance()`
- **Location**: `lib/etf/functions/performance.py`
- **What it does**:
  1. Loads NAV history for the year
  2. Loads distribution history
  3. Calculates pre-tax total return
  4. Calculates after-tax total return (applies tax rates)
  5. Calculates tax drag and tax efficiency
  6. Compares to benchmark (S&P 500, etc.)
  7. Generates performance report

**Regulatory Requirement**: SEC Rule 482 (Performance advertising)

**Example**:
```python
from lib.etf.functions.performance import PerformanceCalculator

performance = PerformanceCalculator(storage_path="./data/performance")
result = performance.compute_performance(
    nav_history_path="./data/nav_history.csv",
    dist_history_path="./data/distributions.csv",
    benchmark_symbol="^GSPC",
    tax_rates={"dividend_tax_rate": 0.15, "lt_capital_gains_tax_rate": 0.20},
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 31)
)
# Calculates annual performance for 2024
```

---

### 7. Year-End Orchestrator Tasks
**Responsibility**: Coordinate all year-end reporting tasks

**Our Implementation**:
- **Function**: `DailyOrchestrator._run_year_end_tasks(tax_year)`
- **Location**: `lib/etf/functions/orchestrator.py`
- **What it does** (if fiscal year end):
  1. Triggers performance calculation
  2. Triggers tax reporting (Form 1120-RIC, Form 8613)
  3. Triggers regulatory reporting (N-CEN, N-CSR)
  4. Generates year-end financial statements
  5. Prepares board materials

**Example**:
```python
# Automatically triggered on fiscal year end date
# Or manually:
orchestrator._run_year_end_tasks(2024)
```

---

## Ad-Hoc Operations {#ad-hoc-operations}

### 1. Trial Balance Generation
**Responsibility**: Verify books are balanced at any point in time

**Our Implementation**:
- **Function**: `Accounting.generate_trial_balance(date)`
- **Location**: `lib/etf/functions/accounting.py`
- **What it does**:
  1. Lists all accounts and balances
  2. Calculates total debits
  3. Calculates total credits
  4. Verifies debits = credits (balanced)
  5. Generates trial balance report

**When to use**: Anytime you need to verify accounting accuracy

**Example**:
```python
trial_balance = accounting.generate_trial_balance(date.today())
if trial_balance.balanced:
    print("✓ Books are balanced")
else:
    print("✗ Books are unbalanced - investigate!")
```

---

### 2. Financial Statement Generation
**Responsibility**: Generate balance sheet or income statement for any period

**Our Implementation**:
- **Function**: `Accounting.generate_balance_sheet()` and `Accounting.generate_income_statement()`
- **Location**: `lib/etf/functions/accounting.py`
- **When to use**: For board meetings, investor requests, or internal reporting

---

### 3. Unrealized Gains Calculation
**Responsibility**: Calculate unrealized gains for open tax lots

**Our Implementation**:
- **Function**: `TaxLotManager.get_unrealized_gains(current_prices)`
- **Location**: `lib/etf/functions/tax_lot.py`
- **When to use**: For performance reporting, tax planning, or portfolio analysis

**Example**:
```python
current_prices = {"AAPL": Decimal('160.00'), "GOOGL": Decimal('120.00')}
unrealized = taxlot_manager.get_unrealized_gains(current_prices)
# Returns: unrealized_short_term, unrealized_long_term, unrealized_total
```

---

## Regulatory Compliance Mapping {#regulatory-compliance}

### SEC Rules

| Rule | Requirement | Our Implementation |
|------|-------------|-------------------|
| **Rule 2a-5** | Valuation procedures | `FundAdministration.calculate_nav()` with validation |
| **Rule 6c-11** | ETF NAV disclosure | NAV calculation and website publication |
| **Rule 17f-2** | Custody verification | `FundAdministration.reconcile_holdings_cash()` |
| **Rule 31a-2** | Books and records | `Accounting` class with persistent storage |
| **Rule 22c-1** | Pricing and distribution timing | NAV calculation and distribution processing |
| **Form N-PORT** | Monthly portfolio holdings | `Compliance.generate_form_n_port()` |
| **Form N-CEN** | Annual census | `Compliance.generate_form_n_cen()` |
| **Form N-CSR** | Shareholder reports | `Compliance.generate_form_n_csr()` |
| **Form N-Q** | Quarterly holdings | `Compliance.generate_form_n_q()` |

### IRS Requirements

| Form/Requirement | Purpose | Our Implementation |
|-----------------|---------|-------------------|
| **Form 1099-DIV** | Dividend reporting | `TaxReporting.generate_1099_div()` |
| **Form 1099-B** | Sales proceeds | `TaxReporting.generate_1099_b()` |
| **Form 1099-INT** | Interest income | `TaxReporting.generate_1099_int()` |
| **Form 1120-RIC** | Corporate tax return | `TaxReporting.generate_tax_return_form_1120_ric()` |
| **Form 8613** | Excise tax | `TaxReporting.generate_form_8613()` |
| **Cost Basis Tracking** | Tax lot accounting | `TaxLotManager` (FIFO/LIFO) |
| **Section 852** | RIC distribution requirements | `Distributor` with payout ratio |

---

## Function Reference {#function-reference}

### Administration Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `calculate_nav()` | `administration.py` | Daily | Calculate NAV per share |
| `reconcile_holdings_cash()` | `administration.py` | Daily | Reconcile portfolio vs custodian |
| `process_corporate_actions()` | `administration.py` | Daily | Process dividends, splits, etc. |
| `calculate_expense_ratio()` | `administration.py` | Monthly | Calculate expense ratio |

### Accounting Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `daily_accounting_operations()` | `accounting.py` | Daily | Run all daily accounting |
| `record_nav_entries()` | `accounting.py` | Daily | Record NAV in ledger |
| `record_expense_accrual()` | `accounting.py` | Daily | Accrue expenses |
| `record_income()` | `accounting.py` | Daily | Record income |
| `create_journal_entry()` | `accounting.py` | As needed | Create journal entry |
| `generate_trial_balance()` | `accounting.py` | As needed | Verify books balanced |
| `generate_balance_sheet()` | `accounting.py` | Monthly/Annual | Generate balance sheet |
| `generate_income_statement()` | `accounting.py` | Monthly/Annual | Generate income statement |

### Tax Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `add_lot()` | `tax_lot.py` | On purchase | Add tax lot |
| `sell()` | `tax_lot.py` | On sale | Process sale (FIFO/LIFO) |
| `get_unrealized_gains()` | `tax_lot.py` | As needed | Calculate unrealized gains |
| `get_realized_gains_summary()` | `tax_lot.py` | Annual | Get realized gains for year |
| `generate_1099_div()` | `tax_reporting.py` | Annual | Generate Form 1099-DIV |
| `generate_1099_b()` | `tax_reporting.py` | Annual | Generate Form 1099-B |
| `generate_tax_return_form_1120_ric()` | `tax_reporting.py` | Annual | Generate Form 1120-RIC |
| `generate_form_8613()` | `tax_reporting.py` | Annual | Generate Form 8613 |

### Distribution Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `calculate_distribution()` | `distributor.py` | Quarterly | Calculate distribution |
| `declare_distribution()` | `distributor.py` | Quarterly | Declare distribution |
| `process_distribution_payment()` | `distributor.py` | Quarterly | Process payment |
| `generate_distribution_schedule()` | `distributor.py` | Annual | Generate schedule |

### Compliance Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `generate_form_n_port()` | `compliance.py` | Monthly | Generate N-PORT |
| `generate_form_n_cen()` | `compliance.py` | Annual | Generate N-CEN |
| `generate_form_n_csr()` | `compliance.py` | Annual | Generate N-CSR |
| `generate_form_n_q()` | `compliance.py` | Quarterly | Generate N-Q |
| `file_sec_form()` | `compliance.py` | As needed | File form via EDGAR |

### Performance Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `compute_performance()` | `performance.py` | Annual | Calculate performance |
| `calculate_annual_returns()` | `performance.py` | Annual | Calculate annual returns |

### Orchestrator Functions

| Function | File | Frequency | Purpose |
|----------|------|-----------|---------|
| `run_daily_operations()` | `orchestrator.py` | Daily | Run all daily operations |
| `_run_year_end_tasks()` | `orchestrator.py` | Annual | Run year-end tasks |

---

## How Our Implementation Achieves ETF Servicer Responsibilities

### 1. **Accurate Valuation** ✅
- **Daily NAV calculation** using live market prices
- **Validation** to catch pricing exceptions
- **Reconciliation** to verify accuracy
- **Corporate actions** processing for accurate pricing

### 2. **Financial Integrity** ✅
- **Double-entry accounting** with balanced journal entries
- **Trial balance** generation to verify books are balanced
- **Persistent storage** for audit trail
- **Financial statements** (Balance Sheet, Income Statement)

### 3. **Regulatory Compliance** ✅
- **SEC filings** (N-PORT, N-CEN, N-CSR, N-Q) generated automatically
- **Tax reporting** (Form 1099, Form 1120-RIC, Form 8613) generated automatically
- **Books and records** maintained per SEC Rule 31a-2
- **Valuation procedures** per SEC Rule 2a-5

### 4. **Shareholder Services** ✅
- **Distribution processing** with payout ratio calculation
- **Tax lot tracking** for accurate cost basis
- **Performance reporting** (pre-tax and after-tax)
- **Tax form generation** (1099-DIV, 1099-B, 1099-INT)

### 5. **Operational Control** ✅
- **Reconciliation** to catch discrepancies
- **Validation** at every step
- **Error handling** and logging
- **Automated workflow** via orchestrator

---

## Quick Start: Running Operations

### Daily Operations (Automated)
```python
from lib.etf.functions.orchestrator import DailyOrchestrator
from lib.etf.adapters import FileBasedDataSourceAdapter

adapter = FileBasedDataSourceAdapter(data_path="./data")
orchestrator = DailyOrchestrator(adapter, config_path="config.yaml")
results = orchestrator.run_daily_operations(date.today())
```

### Monthly Operations
```python
from lib.etf.functions.compliance import Compliance

compliance = Compliance(adapter, storage_path="./data/compliance")
n_port = compliance.generate_form_n_port(month_end_date)
```

### Quarterly Operations
```python
from lib.etf.functions.distributor import Distributor

distributor = Distributor(adapter, storage_path="./data/distributor")
distribution = distributor.calculate_distribution(
    dist_date=quarter_end_date,
    distribution_type="dividend",
    nav_data=nav_data,
    payout_ratio=Decimal('0.95'),
    ledger_data=ledger_accounts
)
```

### Annual Operations
```python
from lib.etf.functions.tax_reporting import TaxReporting

tax_reporting = TaxReporting(adapter, storage_path="./data/tax")
form_1120_ric = tax_reporting.generate_tax_return_form_1120_ric(
    tax_year=2024,
    ledger_data=ledger_accounts,
    taxlot_manager=taxlot_manager,
    distributions=distributions_list
)
```

---

## Conclusion

This implementation provides **complete ETF administration and accounting** functionality that:
- ✅ Meets all regulatory requirements (SEC, IRS)
- ✅ Maintains financial integrity (double-entry accounting)
- ✅ Provides accurate valuation (daily NAV)
- ✅ Supports shareholder services (distributions, tax reporting)
- ✅ Ensures operational control (reconciliation, validation)

All functions are **production-ready** and can be run with live data once you connect your data sources (custodian, NSCC, DTC, market data provider).

