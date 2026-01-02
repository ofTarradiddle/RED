# Using FMP Adapter for Pre-Launch ETFs

Since your ETF isn't live yet, you can't fetch holdings from FMP's ETF holdings API. However, you can still use FMP for all market data operations by providing your holdings manually.

## Option 1: Manual Holdings (Recommended for Pre-Launch)

Provide your target portfolio holdings directly:

```python
from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.core import Accounting, FundAdministration
from datetime import date

# Define your target portfolio holdings
my_holdings = [
    {
        "ticker": "AAPL",
        "cusip": "037833100",  # Optional - will be looked up if missing
        "quantity": 1000,
        "weight": 5.0,  # Percentage
        "name": "Apple Inc."  # Optional
    },
    {
        "ticker": "MSFT",
        "quantity": 800,
        "weight": 4.0
    },
    {
        "ticker": "GOOGL",
        "quantity": 500,
        "weight": 3.5
    },
    # ... more holdings
]

# Create FMP adapter with manual holdings
adapter = FMPDataSourceAdapter(
    etf_symbol="",  # Not needed for pre-launch
    manual_holdings=my_holdings,
    api_key="your_fmp_api_key"  # Still needed for market data
)

# Use with accounting and admin modules
accounting = Accounting(adapter, storage_path="./data/accounting")
admin = FundAdministration(adapter, storage_path="./data/admin")

# Calculate NAV (FMP will fetch prices for your holdings)
nav_calc = admin.calculate_nav(date.today())
print(f"NAV: ${nav_calc.nav_per_share}")

# Run daily accounting operations
accounting.daily_accounting_operations(date.today(), nav_calc)
```

## Option 2: Use File-Based Adapter for Holdings, FMP for Prices

Use a file-based adapter for holdings, but still get prices from FMP:

```python
from lib.etf.adapters import FMPDataSourceAdapter, FileBasedDataSourceAdapter
from lib.etf.functions.core import Accounting, FundAdministration

# Create file-based adapter for holdings
file_adapter = FileBasedDataSourceAdapter(data_path="./data")

# Create FMP adapter with file adapter as fallback
# FMP will be used for prices, corporate actions, dividends, etc.
# File adapter will be used for holdings
adapter = FMPDataSourceAdapter(
    etf_symbol="",
    fallback_adapter=file_adapter,
    api_key="your_fmp_api_key"
)

# Store your holdings in JSON file: data/holdings_2025-01-15.json
# Format:
# [
#   {"ticker": "AAPL", "cusip": "037833100", "quantity": 1000, "weight": 5.0},
#   ...
# ]

accounting = Accounting(adapter, storage_path="./data/accounting")
admin = FundAdministration(adapter, storage_path="./data/admin")
```

## Option 3: Hybrid Approach with FMP Workflows

Use FMP workflows but provide holdings manually:

```python
from lib.etf.functions.core import FMPEnhancedWorkflows
from datetime import date

# Define your holdings
my_holdings = [
    {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
    {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
    # ...
]

# Create FMP adapter with manual holdings
from lib.etf.adapters import FMPDataSourceAdapter
adapter = FMPDataSourceAdapter(
    manual_holdings=my_holdings,
    api_key="your_fmp_api_key"
)

# Create workflows (will use manual holdings but FMP for everything else)
workflows = FMPEnhancedWorkflows(
    etf_symbol="",  # Not needed
    fmp_client=adapter.fmp_client,
    fallback_adapter=None,
    storage_path="./data/admin"
)

# Override the adapter in workflows to use our manual holdings adapter
workflows.fmp_adapter = adapter
workflows.accounting = Accounting(adapter, storage_path="./data/admin/accounting")
workflows.admin = FundAdministration(adapter, storage_path="./data/admin")

# Run daily operations
results = workflows.run_daily_operations(
    operation_date=date.today(),
    benchmark_symbol="SPY"
)
```

## What FMP Still Provides (Even Pre-Launch)

Even though your ETF isn't live, FMP still provides:

✅ **Market Prices** - Batch quotes and historical prices for all your holdings
✅ **Corporate Actions** - Stock splits, symbol changes, mergers
✅ **Dividend Data** - Calendar and company-specific dividend information
✅ **Security Identifiers** - CUSIP, CIK, ISIN lookups
✅ **Benchmark Data** - Index performance for NAV verification
✅ **Portfolio Metrics** - Weighted P/E, dividend yield calculations
✅ **Company Profiles** - Company information for reporting

## Example: Complete Pre-Launch Setup

```python
from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.core import Accounting, FundAdministration, FMPEnhancedWorkflows
from datetime import date
import json

# 1. Define your target portfolio
target_holdings = [
    {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
    {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
    {"ticker": "GOOGL", "quantity": 500, "weight": 3.5},
    {"ticker": "AMZN", "quantity": 600, "weight": 3.0},
    # ... add all your holdings
]

# 2. Create FMP adapter with manual holdings
adapter = FMPDataSourceAdapter(
    manual_holdings=target_holdings,
    api_key="your_fmp_api_key"
)

# 3. Initialize accounting and admin
accounting = Accounting(adapter, storage_path="./data/accounting")
admin = FundAdministration(adapter, storage_path="./data/admin")

# 4. Calculate NAV (FMP fetches current prices)
nav_calc = admin.calculate_nav(date.today())
print(f"NAV per share: ${nav_calc.nav_per_share}")
print(f"Total assets: ${nav_calc.total_assets}")

# 5. Run daily accounting
accounting_results = accounting.daily_accounting_operations(date.today(), nav_calc)

# 6. Check corporate actions
corp_actions = admin.process_corporate_actions(date.today())
print(f"Corporate actions found: {len(corp_actions.get('actions', []))}")

# 7. Track dividends
accounting_data = adapter.get_accounting_data(date.today())
print(f"Dividend income: ${accounting_data.get('income', {}).get('dividend_income', 0)}")
```

## Loading Holdings from File

You can also load holdings from a JSON or CSV file:

```python
import json
import pandas as pd

# From JSON
with open("my_holdings.json", "r") as f:
    holdings = json.load(f)

# From CSV
df = pd.read_csv("my_holdings.csv")
holdings = df.to_dict("records")

# Create adapter
adapter = FMPDataSourceAdapter(
    manual_holdings=holdings,
    api_key="your_fmp_api_key"
)
```

## Holdings File Format

**JSON format:**
```json
[
  {
    "ticker": "AAPL",
    "cusip": "037833100",
    "quantity": 1000,
    "weight": 5.0,
    "name": "Apple Inc."
  },
  {
    "ticker": "MSFT",
    "quantity": 800,
    "weight": 4.0
  }
]
```

**CSV format:**
```csv
ticker,cusip,quantity,weight,name
AAPL,037833100,1000,5.0,Apple Inc.
MSFT,594918104,800,4.0,Microsoft Corporation
```

## Benefits of This Approach

1. **Test Before Launch** - Run full accounting/admin workflows with real market data
2. **Price Validation** - Verify your NAV calculations using FMP prices
3. **Corporate Actions** - Track splits, mergers, etc. for your holdings
4. **Dividend Tracking** - Automatically track dividend accruals
5. **Regulatory Prep** - Generate reports with proper security identifiers
6. **Benchmark Comparison** - Compare your NAV to benchmarks

## Next Steps

1. Define your target portfolio holdings
2. Create FMP adapter with `manual_holdings` parameter
3. Run daily operations to test your workflows
4. When ETF launches, switch to FMP ETF holdings API (or keep manual if preferred)

The system will automatically use FMP for all market data operations while using your manual holdings for portfolio composition.

