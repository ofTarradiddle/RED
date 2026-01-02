#!/usr/bin/env python3
"""Compare FMP prices vs table prices for all ITAN holdings"""

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

from lib.etf.functions.research.core.backtesting import FMPClient
from test_itan_fmp_workflows import ITAN_HOLDINGS

# Filter to stocks only (exclude cash)
STOCK_HOLDINGS = [h for h in ITAN_HOLDINGS if h['ticker'] not in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']]

print("=" * 100)
print("FMP PRICE COMPARISON - All ITAN Holdings")
print("=" * 100)
print(f"Date: {date.today()}")
print(f"Holdings to check: {len(STOCK_HOLDINGS)}")
print()

fmp = FMPClient(api_key=os.getenv('FMP_API_KEY'))

matches = []
differences = []
errors = []

total_table_mv = 0
total_fmp_mv = 0

for holding in STOCK_HOLDINGS:
    ticker = holding['ticker']
    table_price = holding.get('price', 0)
    table_shares = holding.get('quantity', 0)
    table_mv = holding.get('market_value', 0)
    
    if not table_price or table_price == 0:
        continue
    
    total_table_mv += table_mv
    
    # Get price from FMP
    try:
        price_data = fmp.get_historical_price_eod(ticker, date.today().isoformat())
        
        if price_data:
            fmp_price = price_data.get('adjClose') or price_data.get('close')
            if fmp_price:
                fmp_price = float(fmp_price)
                fmp_mv = table_shares * fmp_price
                total_fmp_mv += fmp_mv
                
                price_diff = fmp_price - table_price
                mv_diff = fmp_mv - table_mv
                pct_diff = (price_diff / table_price) * 100 if table_price > 0 else 0
                
                if abs(price_diff) < 0.01:  # Within 1 cent
                    matches.append(ticker)
                else:
                    differences.append({
                        'ticker': ticker,
                        'table_price': table_price,
                        'fmp_price': fmp_price,
                        'price_diff': price_diff,
                        'pct_diff': pct_diff,
                        'table_mv': table_mv,
                        'fmp_mv': fmp_mv,
                        'mv_diff': mv_diff,
                        'shares': table_shares
                    })
            else:
                errors.append({'ticker': ticker, 'error': 'No price in FMP response'})
        else:
            errors.append({'ticker': ticker, 'error': 'No data from FMP'})
    except Exception as e:
        errors.append({'ticker': ticker, 'error': str(e)})

# Sort differences by absolute price difference
differences.sort(key=lambda x: abs(x['price_diff']), reverse=True)

print(f"✓ Matches: {len(matches)} holdings")
print(f"⚠ Differences: {len(differences)} holdings")
print(f"✗ Errors: {len(errors)} holdings")
print()

if differences:
    print("=" * 100)
    print("PRICE DIFFERENCES (sorted by largest difference)")
    print("=" * 100)
    print(f"{'Ticker':<8} {'Table Price':>12} {'FMP Price':>12} {'Diff':>10} {'% Diff':>8} {'MV Diff':>15}")
    print("-" * 100)
    
    for diff in differences[:20]:  # Show top 20
        mv_diff_str = f"${diff['mv_diff']:>14,.2f}"
        print(f"{diff['ticker']:<8} "
              f"${diff['table_price']:>11.2f} "
              f"${diff['fmp_price']:>11.2f} "
              f"${diff['price_diff']:>9.2f} "
              f"{diff['pct_diff']:>7.2f}% "
              f"{mv_diff_str}")
    
    if len(differences) > 20:
        print(f"... and {len(differences) - 20} more")
    
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total table market value: ${total_table_mv:,.2f}")
    print(f"Total FMP market value: ${total_fmp_mv:,.2f}")
    print(f"Total difference: ${total_fmp_mv - total_table_mv:,.2f}")
    print(f"Percentage difference: {((total_fmp_mv - total_table_mv) / total_table_mv * 100):.2f}%")
    print()
    
    # Analyze differences
    large_diffs = [d for d in differences if abs(d['pct_diff']) > 2]
    small_diffs = [d for d in differences if abs(d['pct_diff']) <= 2]
    
    print(f"Large differences (>2%): {len(large_diffs)}")
    print(f"Small differences (≤2%): {len(small_diffs)}")
    print()
    
    if large_diffs:
        print("Holdings with >2% price difference:")
        for diff in large_diffs[:10]:
            print(f"  {diff['ticker']}: {diff['pct_diff']:+.2f}% (${diff['price_diff']:+.2f})")

if errors:
    print()
    print("=" * 100)
    print("ERRORS")
    print("=" * 100)
    for err in errors[:10]:
        print(f"  {err['ticker']}: {err['error']}")

print()
print("=" * 100)
print("CONCLUSION")
print("=" * 100)
if len(differences) == 0:
    print("✓ All prices match!")
elif len(differences) < len(STOCK_HOLDINGS) * 0.1:  # Less than 10% different
    print(f"⚠ {len(differences)} holdings have price differences (likely due to date mismatch)")
    print("  FMP prices are for today, table prices may be from a different date")
else:
    print(f"⚠ {len(differences)} holdings have price differences")
    print("  This suggests the table prices are from a different date than FMP")

