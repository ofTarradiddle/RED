# ETF Self-Service Functions Package

Production-ready package for all ETF operational functions.

## Package Structure

```
lib/etf/
├── __init__.py              # Main package exports
├── functions/               # Operational functions
│   ├── __init__.py
│   ├── accounting.py       # Accounting function
│   ├── administration.py   # Fund administration function
│   ├── transfer_agent.py   # Transfer Agent function
│   ├── order_management.py # Order Management function
│   └── distributor.py      # Distributor function
├── adapters/               # Data source adapters
│   └── __init__.py         # DataSourceAdapter implementations
└── shared/                 # Shared data structures
    └── __init__.py         # Data classes and interfaces
```

## Usage

### Simple Import (Recommended)

```python
from lib.etf import (
    Accounting,
    FundAdministration,
    TransferAgent,
    OrderManagement,
    Distributor,
    FileBasedDataSourceAdapter
)

# Use functions
adapter = FileBasedDataSourceAdapter(data_path="./data")
accounting = Accounting(adapter)
admin = FundAdministration(adapter)
```

### Detailed Imports

```python
# Import specific functions
from lib.etf.functions import Accounting, FundAdministration

# Import adapters
from lib.etf.adapters import FileBasedDataSourceAdapter, ExampleDataSourceAdapter

# Import shared data structures
from lib.etf.shared import NAVCalculation, PCFFile, APOrder
```

## Functions

### Accounting (`functions/accounting.py`)
Complete accounting system with double-entry bookkeeping.

### Administration (`functions/administration.py`)
Fund administration including NAV calculation and reporting.

### Transfer Agent (`functions/transfer_agent.py`)
Shareholder recordkeeping and reconciliation (Non-Paying Agent).

### Order Management (`functions/order_management.py`)
Creation/redemption order processing and PCF publication.

### Distributor (`functions/distributor.py`)
Distribution calculation and payment processing.

## Adapters

### DataSourceAdapter
Abstract base class for data source connections.

### ExampleDataSourceAdapter
Template for implementing your data source connections.

### FileBasedDataSourceAdapter
File-based adapter for testing/development.

## Shared

Data structures and interfaces used across all functions:
- `ShareholderRecord`
- `ReconciliationResult`
- `NAVCalculation`
- `PCFFile`
- `APOrder`
- `DataSourceAdapter`

## Documentation

- Function overview: See `FUNCTIONS_OVERVIEW.md`
- Data source TODOs: See `tasks/DATA_SOURCE_TODOS.md`
- Production readiness: See `PRODUCTION_READINESS.md`
