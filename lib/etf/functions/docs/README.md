# ETF Functions Directory

## Current Organization

This directory contains all production-ready ETF operational functions.

## Proposed Reorganization

The functions are currently flat. We should organize them into logical subdirectories:

### Structure Proposal:

```
functions/
├── core/              # Core daily operations
│   ├── administration.py
│   ├── accounting.py
│   └── orchestrator.py
├── tax/               # Tax-related functions
│   ├── tax_lot.py
│   ├── tax_reporting.py
│   ├── tax_adjustments.py
│   ├── state_tax.py
│   ├── capital_gain_estimates.py
│   └── fbar_filing.py
├── compliance/        # Compliance & audit
│   ├── compliance.py
│   ├── audit_trail.py
│   └── audit_cooperation.py
├── operations/        # Operational functions
│   ├── transfer_agent.py
│   ├── order_management.py
│   ├── distributor.py
│   └── performance.py
├── supporting/        # Supporting functions
│   ├── security_master.py
│   └── adviser_portal.py
└── docs/              # Documentation
    ├── BASKET_USAGE.md
    ├── ORDER_MANAGEMENT_FUNCTIONS.md
    └── ...
```

## Current Files (19 Python + 5 Markdown)

### Core Operations
- `administration.py` - Daily NAV calculation, reconciliation
- `accounting.py` - General ledger, financial statements
- `orchestrator.py` - Daily workflow coordination

### Tax Functions
- `tax_lot.py` - Tax lot tracking (FIFO/LIFO)
- `tax_reporting.py` - Form 1099, 1120-RIC, 8613
- `tax_adjustments.py` - M-1 book-to-tax adjustments
- `state_tax.py` - State tax returns
- `capital_gain_estimates.py` - Capital gain dividend estimates
- `fbar_filing.py` - FBAR filing

### Compliance & Audit
- `compliance.py` - SEC filings (N-PORT, N-CEN, N-CSR)
- `audit_trail.py` - Audit logging
- `audit_cooperation.py` - Audit package preparation

### Operations
- `transfer_agent.py` - Shareholder registry, reconciliation
- `order_management.py` - PCF, baskets, AP orders
- `distributor.py` - Distribution processing
- `performance.py` - Performance calculation

### Supporting
- `security_master.py` - Security master file
- `adviser_portal.py` - Adviser information portal

### Documentation
- `BASKET_USAGE.md` - Basket creation guide
- `ORDER_MANAGEMENT_FUNCTIONS.md` - Order management reference
- `ENHANCEMENTS_SUMMARY.md` - Enhancement summary
- `ADDED_MISSING_FUNCTIONS.md` - Added functions list
- `MISSING_FUNCTIONS.md` - Missing functions checklist

