# Research Module Structure

## Directory Organization

```
research/
├── README.md                    # Main module documentation
├── __init__.py                  # Public API exports
│
├── core/                        # Core reusable modules
│   ├── __init__.py              # Core module exports
│   ├── backtesting.py          # FMPClient, Backtester, data loaders
│   ├── data_fetcher.py          # FinancialDataFetcher for REDI
│   └── factors.py               # Factor analysis (RQ estimation)
│
├── scripts/                     # Executable scripts
│   ├── fetch_financial_data.py  # Fetch financial statements
│   ├── plot_nvda_sales.py       # Plot sales data
│   └── find_redi_folder.py      # Helper for external drive
│
├── tests/                       # Test scripts
│   ├── test_nvda_returns.py      # Test Yahoo price loader
│   ├── test_nvda_sales.py       # Test sales data retrieval
│   └── test_fmp_api.py          # Test FMP API endpoints
│
└── docs/                        # Documentation
    ├── README.md                # Documentation index
    ├── data_fetcher/            # Data fetcher docs
    │   ├── DATA_FETCHER_SUMMARY.md
    │   ├── SETUP_INSTRUCTIONS.md
    │   └── TICKER_CHANGES_GUIDE.md
    └── fmp_api/                 # FMP API docs
        ├── AS_REPORTED_VS_REGULAR_COMPARISON.md
        ├── FMP_TESTING_SUMMARY.md
        ├── FMP_ULTIMATE_TIER_SETUP.md
        ├── fmp_api_status.md
        └── IWB_HISTORICAL_HOLDINGS_ANALYSIS.md
```

## Import Paths

### Public API (Recommended)
```python
from lib.etf.functions.research import (
    FMPClient,
    HoldingsLoader,
    Backtester,
    FinancialDataFetcher,
    estimate_rq_mixedlm
)
```

### Direct Core Imports (If Needed)
```python
from lib.etf.functions.research.core.backtesting import FMPClient
from lib.etf.functions.research.core.data_fetcher import FinancialDataFetcher
from lib.etf.functions.research.core.factors import estimate_rq_mixedlm
```

## Module Responsibilities

### Core Modules
- **backtesting.py**: Backtesting engine, FMP API client, data loaders
- **data_fetcher.py**: Financial statement fetching and storage
- **factors.py**: Factor analysis and research quotient estimation

### Scripts
- **fetch_financial_data.py**: Main script to fetch and store financial data
- **plot_nvda_sales.py**: Example plotting script
- **find_redi_folder.py**: Utility to locate external drive

### Tests
- **test_*.py**: Test scripts for various components

### Documentation
- Organized by topic (data_fetcher, fmp_api)
- Includes setup guides, API status, and usage examples

## Migration Notes

All imports from the old flat structure continue to work through the main `__init__.py`:
- `from lib.etf.functions.research import FMPClient` ✓
- `from lib.etf.functions.research import FinancialDataFetcher` ✓

Scripts have been updated to use the new structure internally.
