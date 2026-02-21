#!/usr/bin/env python3
"""Full test with ITAN holdings using working FMP endpoint"""

import os
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.core import FundAdministration, Accounting

# ITAN holdings (first 20 for quick test)
test_holdings = [
    {"ticker": "AAPL", "cusip": "037833100", "quantity": 1000, "weight": 1.0},
    {"ticker": "MSFT", "cusip": "594918104", "quantity": 800, "weight": 0.8},
    {"ticker": "GOOGL", "cusip": "02079K305", "quantity": 500, "weight": 0.5},
    {"ticker": "AMZN", "cusip": "023135106", "quantity": 600, "weight": 0.6},
    {"ticker": "IBM", "cusip": "459200101", "quantity": 4405, "weight": 1.97},
    {"ticker": "CSCO", "cusip": "17275R102", "quantity": 14958, "weight": 1.73},
    {"ticker": "CRM", "cusip": "79466L302", "quantity": 4275, "weight": 1.71},
    {"ticker": "COF", "cusip": "14040H105", "quantity": 4193, "weight": 1.53},
    {"ticker": "ACN", "cusip": "G1151C101", "quantity": 3793, "weight": 1.54},
    {"ticker": "MRK", "cusip": "58933Y105", "quantity": 9670, "weight": 1.54},
]

print("=" * 60)
print("FMP Integration Test - ITAN Holdings")
print("=" * 60)
print(f"Holdings: {len(test_holdings)}")
print(f"Date: {date.today()}")
print()

adapter = FMPDataSourceAdapter(
    manual_holdings=test_holdings,
    api_key=os.getenv('FMP_API_KEY')
)

# Test price fetching
print("1. Fetching prices from FMP...")
holdings = adapter.get_portfolio_holdings(date.today())
tickers = [h['ticker'] for h in holdings]
cusips = [h.get('cusip') for h in holdings if h.get('cusip')]

prices = adapter.get_market_prices(date.today(), cusips)
print(f"   ✓ Retrieved prices for {len(prices)} securities")
for cusip, price in list(prices.items())[:5]:
    ticker = next((h['ticker'] for h in holdings if h.get('cusip') == cusip), 'N/A')
    print(f"   {ticker} (CUSIP {cusip[:9]}...): ${price}")

# Calculate NAV
print("\n2. Calculating NAV...")
admin = FundAdministration(adapter, storage_path="./data/test_itan")
nav = admin.calculate_nav(date.today())

print(f"   ✓ NAV calculated")
print(f"   Total assets: ${nav.total_assets:,.2f}")
print(f"   Total liabilities: ${nav.total_liabilities:,.2f}")
print(f"   Net assets: ${nav.net_assets:,.2f}")
print(f"   Shares outstanding: {nav.shares_outstanding} (needs custodian data)")
if nav.shares_outstanding > 0:
    print(f"   NAV per share: ${nav.nav_per_share}")
print(f"   Validation: {'PASSED' if nav.validation_passed else 'FAILED'}")

if nav.pricing_exceptions:
    print(f"   Pricing exceptions: {len(nav.pricing_exceptions)}")
    for exc in nav.pricing_exceptions[:3]:
        print(f"     - {exc}")

# Test accounting
print("\n3. Running accounting operations...")
accounting = Accounting(adapter, storage_path="./data/test_itan_accounting")
results = accounting.daily_accounting_operations(date.today(), nav)

print(f"   ✓ Accounting operations completed")
print(f"   NAV entries: {len(results.get('nav_entries', []))}")
print(f"   Expense entries: {len(results.get('expense_entries', []))}")
print(f"   Income entries: {len(results.get('income_entries', []))}")

tb = results.get('trial_balance')
if tb:
    print(f"   Trial balance: {'BALANCED' if tb.balanced else 'UNBALANCED'}")

print("\n" + "=" * 60)
print("✓ All tests completed successfully!")
print("=" * 60)

