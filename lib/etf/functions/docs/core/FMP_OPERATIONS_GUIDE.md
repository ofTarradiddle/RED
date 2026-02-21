# FMP-Based Accounting & Administration Operations Guide

## Overview

This guide explains how to execute all in-house accounting and administration responsibilities using FMP (Financial Modeling Prep) APIs. The system is **production-ready** and **plug-and-play** - most functionality is already built and working.

## What's Already Built ✅

### 1. **FMPDataSourceAdapter** (`lib/etf/adapters/fmp_adapter.py`)
Complete data source adapter that provides:
- ✅ Market prices (batch quotes, historical EOD)
- ✅ Corporate actions (splits, symbol changes)
- ✅ Dividend data (calendar, company-specific)
- ✅ Security identifiers (CUSIP, CIK, ISIN)
- ✅ Benchmark/index data
- ✅ Portfolio metrics (weighted P/E, dividend yield, sector allocations)
- ✅ ETF holdings (for live ETFs)
- ✅ Manual holdings support (for pre-launch ETFs)

### 2. **FMPEnhancedWorkflows** (`lib/etf/functions/core/fmp_workflows.py`)
Complete workflows that integrate FMP APIs:
- ✅ Daily price import & NAV calculation
- ✅ Daily corporate actions processing
- ✅ Daily dividend accrual tracking
- ✅ Daily expense accrual & fee booking
- ✅ Daily NAV verification & reconciliation
- ✅ Monthly/quarterly close & financial statement prep
- ✅ Investor reporting (monthly factsheet & portfolio metrics)

### 3. **Accounting Module** (`lib/etf/functions/core/accounting.py`)
Production-ready accounting system:
- ✅ Double-entry bookkeeping
- ✅ General ledger management
- ✅ Journal entry processing
- ✅ Trial balance generation
- ✅ Balance sheet generation
- ✅ Income statement generation
- ✅ NAV entry recording
- ✅ Expense accrual recording
- ✅ Income recognition

### 4. **Administration Module** (`lib/etf/functions/core/administration.py`)
Production-ready fund administration:
- ✅ Daily NAV calculation
- ✅ Price validation with tolerance checks
- ✅ Holdings and cash reconciliation
- ✅ Corporate actions processing
- ✅ Expense ratio calculation

### 5. **Daily Orchestrator** (`lib/etf/functions/core/orchestrator.py`)
Coordinates all operations:
- ✅ Auto-detects FMP adapters
- ✅ Runs FMP-enhanced workflows automatically
- ✅ Handles all daily operations in sequence

## Quick Start

### 1. Set Up Environment

```bash
# Set FMP API key
export FMP_API_KEY=your_api_key_here

# Or add to .env file
echo "FMP_API_KEY=your_api_key_here" >> .env
```

### 2. Run Daily Operations

#### Option A: Using the Execution Script (Recommended)

```bash
# Run daily operations for today
python lib/etf/functions/core/execute_fmp_operations.py --daily

# Run for specific date
python lib/etf/functions/core/execute_fmp_operations.py --daily --date 2025-01-15

# Run with manual holdings (for pre-launch ETFs)
python lib/etf/functions/core/execute_fmp_operations.py --daily \
    --holdings ./data/holdings.json \
    --etf-symbol ITAN

# Run with benchmark verification
python lib/etf/functions/core/execute_fmp_operations.py --daily \
    --benchmark SPY
```

#### Option B: Using Python Directly

```python
from datetime import date
from lib.etf.functions.core.execute_fmp_operations import execute_daily_operations

# Run daily operations
results = execute_daily_operations(
    operation_date=date.today(),
    etf_symbol="ITAN",  # Optional
    manual_holdings_file="./data/holdings.json",  # Optional
    benchmark_symbol="SPY",
    storage_path="./data/admin"
)

print(f"NAV: ${results['operations']['nav_calculation']['nav_per_share']}")
```

#### Option C: Using Daily Orchestrator

```python
from datetime import date
from lib.etf.adapters.fmp_adapter import FMPDataSourceAdapter
from lib.etf.functions.core.orchestrator import DailyOrchestrator

# Create FMP adapter
adapter = FMPDataSourceAdapter(
    etf_symbol="ITAN",
    manual_holdings=[...]  # Optional
)

# Create orchestrator
orchestrator = DailyOrchestrator(adapter, config_path="config.yaml")

# Run daily operations
results = orchestrator.run_daily_operations(date.today())
```

### 3. Run Monthly/Quarterly Close

```bash
# Monthly close
python lib/etf/functions/core/execute_fmp_operations.py --monthly-close --date 2025-01-31

# Quarterly close
python lib/etf/functions/core/execute_fmp_operations.py --quarterly-close --date 2025-03-31
```

### 4. Generate Monthly Factsheet

```bash
python lib/etf/functions/core/execute_fmp_operations.py --factsheet --date 2025-01-31
```

## What Gets Executed

### Daily Operations (T+0)

When you run daily operations, the system automatically:

1. **Price Import & NAV Calculation**
   - Fetches end-of-day prices for all holdings from FMP
   - Calculates total assets (securities + cash)
   - Calculates total liabilities (accrued expenses, payables)
   - Calculates NAV per share
   - Validates prices (checks for exceptions)

2. **Corporate Actions Processing**
   - Checks for stock splits
   - Checks for symbol changes
   - Updates holdings records
   - Adjusts share quantities and cost basis

3. **Dividend Accrual Tracking**
   - Fetches dividend calendar from FMP
   - Calculates dividend income based on holdings
   - Records dividend receivables on ex-dates
   - Records cash received on pay dates

4. **Expense Accrual & Fee Booking**
   - Calculates daily expense accruals
   - Verifies expense ratio from FMP (if ETF is live)
   - Records expense accruals in accounting

5. **NAV Verification & Reconciliation**
   - Compares NAV % change vs benchmark % change
   - Verifies price inputs
   - Checks for discrepancies beyond threshold (2%)

6. **Accounting Entries**
   - Records NAV entries (Debit: Investments, Credit: Net Assets)
   - Records expense accruals
   - Records income (dividends, interest)
   - Generates trial balance

### Monthly/Quarterly Close

When you run period-end close:

1. **Period-End NAV Calculation**
   - Calculates NAV using FMP historical prices

2. **Financial Statement Generation**
   - Balance Sheet (Assets, Liabilities, Equity)
   - Income Statement (Income, Expenses, Net Income)
   - Trial Balance (verifies books are balanced)

3. **Security Identifier Lookups**
   - Fetches CUSIP, CIK, ISIN for all holdings
   - Used for regulatory reporting

## Output Files

All operations save results to the storage path (default: `./data/admin`):

### Daily Operations
- `daily_nav_report_{date}.json` - NAV calculation details
- `corporate_actions_{date}.json` - Corporate actions processed
- `dividend_schedule_{date}.json` - Dividend accrual schedule
- `expense_journal_{date}.json` - Expense accrual entries
- `nav_qa_report_{date}.json` - NAV verification results
- `daily_operations_{date}.json` - Complete daily operations summary

### Accounting
- `general_ledger.json` - General ledger (persistent)
- `trial_balance_{date}.json` - Trial balance
- `balance_sheet_{date}.json` - Balance sheet
- `income_statement_{start}_{end}.json` - Income statement

### Period-End Close
- `monthly_close_{date}.json` - Monthly close results
- `quarterly_close_{date}.json` - Quarterly close results

### Reporting
- `factsheet_{date}.json` - Monthly factsheet data

## Manual Holdings Format

For pre-launch ETFs or custom portfolios, provide holdings in JSON or CSV:

### JSON Format
```json
[
    {
        "ticker": "AAPL",
        "cusip": "037833100",
        "quantity": 1000,
        "weight": 5.0,
        "market_value": 150000.00,
        "name": "Apple Inc."
    },
    {
        "ticker": "MSFT",
        "cusip": "594918104",
        "quantity": 800,
        "weight": 4.0,
        "market_value": 120000.00,
        "name": "Microsoft Corporation"
    }
]
```

### CSV Format
```csv
ticker,cusip,quantity,weight,market_value,name
AAPL,037833100,1000,5.0,150000.00,Apple Inc.
MSFT,594918104,800,4.0,120000.00,Microsoft Corporation
```

## Configuration

### Using Daily Orchestrator with Config File

Create `config.yaml`:

```yaml
fund:
  symbol: "ITAN"
  benchmark: "SPY"
  fiscal_year_end: "12-31"

paths:
  admin_storage: "./data/admin"
  accounting_storage: "./data/accounting"
  tax_lot_storage: "./data/tax_lots"
  distributor_storage: "./data/distributor"
  settlement_storage: "./data/settlement"
  performance_storage: "./data/performance"
  tax_storage: "./data/tax"

logging:
  level: "INFO"
  file: "operations.log"

distributions:
  frequency: "quarterly"  # monthly, quarterly, annual
  payout_ratio: 1.0

tax:
  lot_method: "LOWEST_COST"  # FIFO, LIFO, LOWEST_COST
```

## What's NOT Available via FMP

These require fallback adapters or manual input:

- ❌ NSCC files (creation/redemption orders)
- ❌ DTC position files
- ❌ Custodian statements (cash balances, shares outstanding)
- ❌ AP orders
- ❌ Distribution data

**Solution**: Use a fallback adapter (e.g., `FileBasedDataSourceAdapter`) for these data sources.

## API Endpoints Used

The FMP adapter uses these FMP Ultimate API endpoints:

- `stable/quote` - Batch quotes for multiple tickers
- `stable/historical-price-eod/{symbol}` - End-of-day historical prices
- `stable/stock-dividend-calendar` - Dividend calendar
- `stable/stock-split-calendar` - Stock splits calendar
- `stable/symbol-changes-list` - Symbol changes
- `stable/cusip/{cusip}` - CUSIP lookup
- `stable/cik/{cik}` - CIK lookup
- `stable/key-metrics-ttm/{symbol}` - Key metrics (P/E, yield, etc.)
- `stable/etf-sector-weightings/{symbol}` - Sector allocations
- `stable/company-profile/{symbol}` - Company information
- `stable/etf/{symbol}` - ETF information (expense ratio, etc.)
- `stable/index-market-data/{symbol}` - Benchmark index data

## Troubleshooting

### Error: "FMP_API_KEY not found"
**Solution**: Set the `FMP_API_KEY` environment variable or add it to `.env` file.

### Error: "No holdings found"
**Solution**: Provide `manual_holdings_file` or ensure ETF symbol is correct and ETF is live.

### Error: "403 Forbidden" on some endpoints
**Solution**: Some endpoints require FMP Ultimate tier. The system will fall back to alternative methods where possible.

### Error: "Missing price for CUSIP"
**Solution**: Check that ticker symbols are correct. The system will log which securities are missing prices.

## Next Steps

1. **Set up environment**: Configure `FMP_API_KEY`
2. **Prepare holdings**: Create holdings file (JSON or CSV) if using manual holdings
3. **Run daily operations**: Execute `execute_fmp_operations.py --daily`
4. **Review outputs**: Check `./data/admin` for operation results
5. **Set up automation**: Schedule daily operations via cron or systemd

## Support

For issues or questions:
- Check logs: `fmp_operations.log`
- Review operation outputs in `./data/admin`
- Check FMP API status: https://financialmodelingprep.com/developer/docs/

