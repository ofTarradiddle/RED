#!/usr/bin/env python3
"""Quick test with a few ITAN holdings to verify FMP API connectivity"""

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
from lib.etf.functions.core import FundAdministration

# Test with just 5 holdings
test_holdings = [
    {"ticker": "AAPL", "cusip": "037833100", "quantity": 1000, "weight": 1.0},
    {"ticker": "MSFT", "cusip": "594918104", "quantity": 800, "weight": 0.8},
    {"ticker": "GOOGL", "cusip": "02079K305", "quantity": 500, "weight": 0.5},
    {"ticker": "AMZN", "cusip": "023135106", "quantity": 600, "weight": 0.6},
    {"ticker": "TSLA", "cusip": "88160R101", "quantity": 400, "weight": 0.4},
]

print("Testing FMP API with 5 holdings...")
print(f"API Key: {'Set' if os.getenv('FMP_API_KEY') else 'NOT SET'}")

adapter = FMPDataSourceAdapter(
    manual_holdings=test_holdings,
    api_key=os.getenv('FMP_API_KEY')
)

# Test batch quotes
print("\n1. Testing batch quotes...")
tickers = [h['ticker'] for h in test_holdings]
quotes = adapter.fmp_client.get_batch_quotes(tickers)
print(f"   Retrieved quotes for {len(quotes)} tickers")
for ticker, quote in quotes.items():
    price = quote.get('price') or quote.get('close') or quote.get('last')
    print(f"   {ticker}: ${price}")

# Test NAV calculation
print("\n2. Testing NAV calculation...")
admin = FundAdministration(adapter, storage_path="./data/test_simple")
nav = admin.calculate_nav(date.today())
print(f"   NAV per share: ${nav.nav_per_share}")
print(f"   Total assets: ${nav.total_assets:,.2f}")
print(f"   Validation: {'PASSED' if nav.validation_passed else 'FAILED'}")

if nav.pricing_exceptions:
    print(f"   Pricing exceptions: {len(nav.pricing_exceptions)}")
    for exc in nav.pricing_exceptions[:3]:
        print(f"     - {exc}")

print("\n✓ Test completed!")

