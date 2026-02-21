# FMP Data Source Adapter Usage Guide

This guide explains how to use the FMP (Financial Modeling Prep) Data Source Adapter for ETF accounting and administration operations.

## Overview

The `FMPDataSourceAdapter` integrates FMP Ultimate APIs into the ETF operations system, providing:

- **Market Prices**: Batch quotes and historical EOD prices for NAV calculation
- **Corporate Actions**: Stock splits, symbol changes, mergers
- **Dividend Data**: Calendar and company-specific dividend information
- **Security Identifiers**: CUSIP, CIK, ISIN lookups for regulatory filings
- **Benchmark Data**: Index performance for NAV verification
- **Portfolio Metrics**: Weighted P/E, dividend yield, sector allocations

## Setup

### 1. Install Dependencies

```bash
pip install requests pandas
```

### 2. Set FMP API Key

Set the `FMP_API_KEY` environment variable:

```bash
export FMP_API_KEY=your_api_key_here
```

Or in a `.env` file:
```
FMP_API_KEY=your_api_key_here
```

### 3. Basic Usage

```python
from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.core import Accounting, FundAdministration
from datetime import date

# Create FMP adapter
adapter = FMPDataSourceAdapter(
    etf_symbol="SPY",  # Your ETF symbol
    api_key="your_api_key"  # Optional, uses env var if not provided
)

# Use with accounting and admin modules
accounting = Accounting(adapter, storage_path="./data/accounting")
admin = FundAdministration(adapter, storage_path="./data/admin")

# Calculate NAV (uses FMP batch quote API)
nav_calc = admin.calculate_nav(date.today())

# Run daily accounting operations
accounting.daily_accounting_operations(date.today(), nav_calc)
```

## Using FMP-Enhanced Workflows

The `FMPEnhancedWorkflows` class provides complete workflows that integrate FMP APIs:

```python
from lib.etf.functions.core import FMPEnhancedWorkflows
from datetime import date

# Initialize workflows
workflows = FMPEnhancedWorkflows(
    etf_symbol="SPY",
    api_key="your_api_key",  # Optional
    storage_path="./data/admin"
)

# Run all daily operations
results = workflows.run_daily_operations(
    operation_date=date.today(),
    benchmark_symbol="SPY"  # For NAV verification
)

# Or run individual workflows
nav_result = workflows.daily_price_import_and_nav(date.today())
corp_actions = workflows.daily_corporate_actions_processing(date.today())
dividends = workflows.daily_dividend_accrual_tracking(date.today())
expenses = workflows.daily_expense_accrual_and_fee_booking(date.today())
nav_verification = workflows.daily_nav_verification_and_reconciliation(
    date.today(), 
    benchmark_symbol="SPY"
)
```

## Using with Daily Orchestrator

The orchestrator automatically detects FMP adapters and uses enhanced workflows:

```python
from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.core import DailyOrchestrator

# Create FMP adapter
adapter = FMPDataSourceAdapter(etf_symbol="SPY")

# Create orchestrator (will auto-detect FMP adapter)
orchestrator = DailyOrchestrator(
    data_adapter=adapter,
    config_path="config.yaml"
)

# Run daily operations (uses FMP workflows automatically)
results = orchestrator.run_daily_operations(date.today())
```

## Configuration

Create a `config.yaml` file:

```yaml
fund:
  symbol: "SPY"
  benchmark_symbol: "SPY"
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
```

## Available Workflows

### Daily Operations

1. **Daily Price Import & NAV Calculation**
   - Uses FMP batch quote API for real-time prices
   - Historical EOD API for past dates
   - Automatically records NAV in accounting

2. **Corporate Actions Processing**
   - Stock splits (FMP splits calendar API)
   - Symbol changes (FMP symbol changes API)
   - Mergers and acquisitions

3. **Dividend Accrual Tracking**
   - Dividend calendar API for upcoming dividends
   - Company-specific dividend API for detailed data
   - Automatic income recognition in accounting

4. **Expense Accrual & Fee Booking**
   - Daily expense accrual calculation
   - FMP ETF info API for expense ratio verification

5. **NAV Verification & Reconciliation**
   - Benchmark comparison using FMP index market data
   - Price validation and discrepancy detection

### Periodic Operations

6. **Monthly/Quarterly Close**
   - Period-end financial statement generation
   - Historical price EOD API for valuations
   - Security identifier lookups for reporting

7. **Investor Reporting (Monthly Factsheet)**
   - Portfolio metrics (weighted P/E, dividend yield)
   - Sector allocations (FMP sector weightings API)
   - Top holdings and performance data

## Fallback Adapter

You can use a fallback adapter for data not available via FMP:

```python
from lib.etf.adapters import FMPDataSourceAdapter, FileBasedDataSourceAdapter

# Create fallback adapter
fallback = FileBasedDataSourceAdapter(data_path="./data")

# Create FMP adapter with fallback
adapter = FMPDataSourceAdapter(
    etf_symbol="SPY",
    fallback_adapter=fallback
)
```

The FMP adapter will automatically fall back to the fallback adapter for:
- NSCC files
- DTC position files
- Custodian statements
- AP orders
- Distribution data

## API Endpoints Used

The FMP adapter uses the following FMP Ultimate API endpoints:

- `stable/quote` - Batch quotes for multiple tickers
- `stable/historical-price-eod/{symbol}` - End-of-day historical prices
- `stable/stock-dividend-calendar` - Dividend calendar
- `stable/stock-split-calendar` - Stock splits calendar
- `stable/symbol-changes-list` - Symbol changes
- `stable/cusip/{cusip}` - CUSIP lookup
- `stable/cik/{cik}` - CIK lookup
- `stable/key-metrics-ttm/{symbol}` - Key metrics (P/E, yield, etc.)
- `stable/etf-sector-weightings/{symbol}` - Sector allocations
- `stable/profile/{symbol}` - Company profile
- `stable/etf/{symbol}` - ETF information

## Error Handling

The adapter includes comprehensive error handling:

- API failures fall back to cached data when available
- Missing data falls back to fallback adapter if provided
- All errors are logged with context
- Operations continue even if individual API calls fail

## Performance Considerations

- **Caching**: FMP adapter caches API responses to reduce API calls
- **Batch Operations**: Uses batch quote API for multiple tickers
- **Rate Limiting**: Built-in rate limiting to respect API limits

## Example: Complete Daily Operations

```python
from lib.etf.functions.core import FMPEnhancedWorkflows
from datetime import date

# Initialize
workflows = FMPEnhancedWorkflows(
    etf_symbol="SPY",
    storage_path="./data/admin"
)

# Run all daily operations
results = workflows.run_daily_operations(
    operation_date=date.today(),
    benchmark_symbol="SPY"
)

# Check results
print(f"NAV: ${results['operations']['nav_calculation']['nav_per_share']}")
print(f"Corporate Actions: {results['operations']['corporate_actions']['actions_processed']}")
print(f"Dividend Accruals: ${results['operations']['dividend_accrual']['total_accrued_income']}")
print(f"NAV Verification: {results['operations']['nav_verification']['reconciliation_status']}")
```

## Troubleshooting

### API Key Issues
- Ensure `FMP_API_KEY` environment variable is set
- Verify API key is valid and has Ultimate tier access
- Check API key in FMP dashboard

### Missing Data
- Some endpoints may require Ultimate tier subscription
- Use fallback adapter for data not available via FMP
- Check FMP API documentation for endpoint availability

### Rate Limiting
- FMP adapter includes caching to reduce API calls
- If rate limited, wait and retry
- Consider upgrading FMP subscription for higher limits

## Next Steps

1. Set up your FMP API key
2. Configure your ETF symbol in the adapter
3. Run daily operations using `FMPEnhancedWorkflows`
4. Review generated reports in the storage path
5. Integrate with your existing systems

For more information, see:
- `lib/etf/functions/core/fmp_workflows.py` - Workflow implementations
- `lib/etf/adapters/fmp_adapter.py` - Adapter implementation
- `lib/etf/functions/research/core/backtesting.py` - FMPClient implementation

