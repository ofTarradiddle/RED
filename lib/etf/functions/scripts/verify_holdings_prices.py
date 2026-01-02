#!/usr/bin/env python3
"""Verify holdings prices and market values against provided table"""

import os
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

# Load .env
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

from lib.etf.adapters import FMPDataSourceAdapter
from lib.etf.functions.research.core.backtesting import FMPClient

# Expected holdings from user's table
EXPECTED_HOLDINGS = [
    {"ticker": "AMZN", "cusip": "023135106", "shares": 12124, "expected_price": 230.82, "expected_mv": 2798462},
    {"ticker": "GOOG", "cusip": "02079K107", "shares": 5032, "expected_price": 313.80, "expected_mv": 1579042},
    {"ticker": "GOOGL", "cusip": "02079K305", "shares": 5036, "expected_price": 313.00, "expected_mv": 1576268},
    {"ticker": "IBM", "cusip": "459200101", "shares": 4405, "expected_price": 296.21, "expected_mv": 1304805},
    {"ticker": "CSCO", "cusip": "17275R102", "shares": 14958, "expected_price": 76.62, "expected_mv": 1146082},
    {"ticker": "CRM", "cusip": "79466L302", "shares": 4275, "expected_price": 264.91, "expected_mv": 1132490},
    {"ticker": "QCOM", "cusip": "747525103", "shares": 6306, "expected_price": 171.05, "expected_mv": 1078641},
    {"ticker": "T", "cusip": "00206R102", "shares": 41482, "expected_price": 24.84, "expected_mv": 1030413},
    {"ticker": "MRK", "cusip": "58933Y105", "shares": 9670, "expected_price": 105.26, "expected_mv": 1017864},
    {"ticker": "ACN", "cusip": "G1151C101", "shares": 3793, "expected_price": 268.30, "expected_mv": 1017662},
]

print("=" * 80)
print("HOLDINGS PRICE VERIFICATION")
print("=" * 80)
print()

fmp = FMPClient(api_key=os.getenv('FMP_API_KEY'))

discrepancies = []
total_expected_mv = 0
total_actual_mv = 0

for holding in EXPECTED_HOLDINGS:
    ticker = holding['ticker']
    cusip = holding['cusip']
    shares = holding['shares']
    expected_price = holding['expected_price']
    expected_mv = holding['expected_mv']
    
    # Get price from FMP
    price_data = fmp.get_historical_price_eod(ticker, date.today().isoformat())
    
    if price_data:
        actual_price = price_data.get('adjClose') or price_data.get('close')
        if actual_price:
            actual_price = float(actual_price)
            actual_mv = shares * actual_price
            price_diff = actual_price - expected_price
            mv_diff = actual_mv - expected_mv
            pct_diff = (price_diff / expected_price) * 100 if expected_price > 0 else 0
            
            total_expected_mv += expected_mv
            total_actual_mv += actual_mv
            
            if abs(price_diff) > 0.01:  # More than 1 cent difference
                discrepancies.append({
                    'ticker': ticker,
                    'expected_price': expected_price,
                    'actual_price': actual_price,
                    'price_diff': price_diff,
                    'pct_diff': pct_diff,
                    'expected_mv': expected_mv,
                    'actual_mv': actual_mv,
                    'mv_diff': mv_diff
                })
                
                print(f"⚠️  {ticker}:")
                print(f"   Expected: ${expected_price:.2f} → MV: ${expected_mv:,.2f}")
                print(f"   Actual:   ${actual_price:.2f} → MV: ${actual_mv:,.2f}")
                print(f"   Diff:     ${price_diff:.2f} ({pct_diff:+.2f}%) → MV diff: ${mv_diff:,.2f}")
                print()
        else:
            print(f"✗ {ticker}: No price in response")
    else:
        print(f"✗ {ticker}: No price data from FMP")

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total expected market value: ${total_expected_mv:,.2f}")
print(f"Total actual market value: ${total_actual_mv:,.2f}")
print(f"Total difference: ${total_actual_mv - total_expected_mv:,.2f}")
print(f"Discrepancies found: {len(discrepancies)}")
print()

if discrepancies:
    print("Possible causes:")
    print("1. Price date mismatch (table prices vs FMP EOD date)")
    print("2. FMP using adjusted close vs unadjusted close")
    print("3. Different pricing source")
else:
    print("✓ All prices match!")

