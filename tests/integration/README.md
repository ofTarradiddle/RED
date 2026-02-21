# ITAN ETF Integration Tests

This directory contains comprehensive integration tests using live ITAN ETF data.

## Overview

These tests validate all ETF administration and accounting functions using real market data from the ITAN ETF (Sparkline Intangible Value ETF) where available, and dummy data for unavailable sources.

## Files

- **`fetch_itan_data.py`** - Script to fetch and prepare ITAN data
- **`test_itan_live_data.py`** - Pytest integration tests
- **`run_itan_full_test.py`** - Full end-to-end test script

## Setup

1. **Fetch ITAN Data**:
   ```bash
   python tests/integration/fetch_itan_data.py
   ```

   This will:
   - Fetch ITAN's price history (last 2 years) from yfinance
   - Create distribution history
   - Generate configuration file
   - Save holdings data

2. **Run Integration Tests**:
   ```bash
   pytest tests/integration/test_itan_live_data.py -v
   ```

3. **Run Full Test**:
   ```bash
   python tests/integration/run_itan_full_test.py
   ```

## What Gets Tested

### Live Data Sources (from yfinance)
- ✅ ITAN price history (NAV history)
- ✅ Current market prices for holdings
- ✅ ITAN fund information (shares outstanding, etc.)

### Dummy Data Sources (simulated)
- ⚠️ Custodian statements (cash balances, detailed holdings)
- ⚠️ NSCC files (creation/redemption orders)
- ⚠️ DTC position files
- ⚠️ Corporate actions
- ⚠️ Distribution history (simulated quarterly)

## Test Coverage

1. **NAV Calculation** - Uses live ITAN prices
2. **Accounting Operations** - Full double-entry ledger
3. **Tax Lot Tracking** - FIFO/LIFO, realized/unrealized gains
4. **Performance Calculation** - Pre-tax and after-tax returns vs S&P 500
5. **Distribution Processing** - Quarterly distributions with payout ratios
6. **Tax Reporting** - Form 1120-RIC and Form 8613
7. **Daily Operations** - Full orchestrator workflow

## Data Files

All test data is stored in `./data/itan_test/`:

- `nav_history.csv` - ITAN price history
- `distributions.csv` - Distribution history
- `config.yaml` - ITAN configuration
- `holdings.json` - ITAN holdings
- `admin/` - NAV calculations
- `accounting/` - Accounting records
- `tax_lots/` - Tax lot data
- `tax/` - Tax reports
- `performance/` - Performance calculations

## Notes

- Tests use yesterday's date to ensure market data is available
- Some functions require dummy data as we don't have access to:
  - Custodian API
  - NSCC systems
  - DTC systems
  - Corporate actions feed

## Production Readiness

Before going live, you should:
1. ✅ Replace dummy data sources with real API connections
2. ✅ Verify all calculations match your custodian's records
3. ✅ Test with your actual fund's holdings and structure
4. ✅ Validate tax calculations with your tax advisor
5. ✅ Review all regulatory reports with compliance

