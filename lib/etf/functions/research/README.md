# Research Module

Backtesting, data fetching, and factor analysis tools for ETF strategy development.

## Structure

```
research/
├── core/              # Core reusable modules
│   ├── backtesting.py      # FMPClient, Backtester, data loaders
│   ├── data_fetcher.py      # FinancialDataFetcher for REDI
│   └── factors.py          # Factor analysis (RQ estimation)
│
├── scripts/          # Executable scripts
│   ├── fetch_financial_data.py  # Fetch financial statements
│   ├── plot_nvda_sales.py       # Plot sales data
│   └── find_redi_folder.py      # Helper for external drive
│
├── tests/            # Test scripts
│   ├── test_nvda_returns.py     # Test Yahoo price loader
│   ├── test_nvda_sales.py       # Test sales data retrieval
│   └── test_fmp_api.py          # Test FMP API endpoints
│
└── docs/             # Documentation
    ├── data_fetcher/            # Data fetcher documentation
    └── fmp_api/                 # FMP API documentation
```

## Quick Start

### Backtesting

```python
from lib.etf.functions.research import FMPClient, HoldingsLoader, Backtester

# Initialize
fmp = FMPClient(api_key="your_key")
holdings_loader = HoldingsLoader(fmp, etf_symbol="IWB")
# ... setup backtester
```

### Data Fetching

```python
from lib.etf.functions.research import FinancialDataFetcher
from pathlib import Path

fetcher = FinancialDataFetcher(
    api_key="your_key",
    base_storage_path=Path("/path/to/storage")
)

# Fetch all statements for a symbol
results = fetcher.fetch_all_statements("NVDA", period="annual")
```

### Factor Analysis

```python
from lib.etf.functions.research import estimate_rq_mixedlm

# Estimate Research Quotient
rq_series = estimate_rq_mixedlm(
    df=your_dataframe,
    firm_col="firm_id",
    year_col="year",
    y_col="revenue",
    r_col="rd"
)
```

## Documentation

- **Data Fetcher**: See `docs/data_fetcher/` for setup and usage
- **FMP API**: See `docs/fmp_api/` for API status and testing

## Scripts

Run scripts from the project root:

```bash
# Fetch financial data
python lib/etf/functions/research/scripts/fetch_financial_data.py

# Plot sales data
python lib/etf/functions/research/scripts/plot_nvda_sales.py
```

## Tests

Run test scripts to verify functionality:

```bash
# Test Yahoo price loader
python lib/etf/functions/research/tests/test_nvda_returns.py

# Test FMP API
python lib/etf/functions/research/tests/test_fmp_api.py
```

