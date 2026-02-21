# Functions Directory Structure

## Organization

Functions are organized into logical subdirectories:

```
functions/
├── core/              # Core daily operations
│   ├── __init__.py
│   ├── administration.py    # NAV calculation, reconciliation
│   ├── accounting.py        # General ledger, financial statements
│   └── orchestrator.py      # Daily workflow coordination
│
├── tax/               # Tax-related functions
│   ├── __init__.py
│   ├── tax_lot.py            # Tax lot tracking (FIFO/LIFO)
│   ├── tax_reporting.py      # Form 1099, 1120-RIC, 8613
│   ├── tax_adjustments.py    # M-1 book-to-tax adjustments
│   ├── state_tax.py          # State tax returns
│   ├── capital_gain_estimates.py  # Capital gain estimates
│   └── fbar_filing.py        # FBAR filing
│
├── compliance/        # Compliance & audit
│   ├── __init__.py
│   ├── compliance.py         # SEC filings (N-PORT, N-CEN, N-CSR)
│   ├── audit_trail.py       # Audit logging
│   └── audit_cooperation.py # Audit package preparation
│
├── operations/        # Operational functions
│   ├── __init__.py
│   ├── transfer_agent.py     # Shareholder registry, reconciliation
│   ├── order_management.py  # PCF, baskets, AP orders
│   ├── distributor.py       # Distribution processing
│   └── performance.py        # Performance calculation
│
├── supporting/        # Supporting functions
│   ├── __init__.py
│   ├── security_master.py    # Security master file
│   └── adviser_portal.py     # Adviser information portal
│
└── docs/              # Documentation
    ├── BASKET_USAGE.md
    ├── ORDER_MANAGEMENT_FUNCTIONS.md
    ├── ENHANCEMENTS_SUMMARY.md
    ├── ADDED_MISSING_FUNCTIONS.md
    └── MISSING_FUNCTIONS.md
```

## Import Examples

### Old Way (still works via __init__.py)
```python
from lib.etf.functions import FundAdministration, Accounting
```

### New Way (explicit)
```python
from lib.etf.functions.core import FundAdministration, Accounting
from lib.etf.functions.tax import TaxLotManager, TaxReporting
from lib.etf.functions.compliance import Compliance, AuditTrailManager
from lib.etf.functions.operations import TransferAgent, OrderManagement
from lib.etf.functions.supporting import SecurityMasterFile
```

## Benefits

1. **Better Organization**: Related functions grouped together
2. **Clearer Structure**: Easy to find what you need
3. **Scalability**: Easy to add new functions in appropriate category
4. **Maintainability**: Clear separation of concerns

