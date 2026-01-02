#!/usr/bin/env python3
"""
Test distribution calculation for ITAN ETF
"""

import os
import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

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
from lib.etf.functions.research.core.backtesting import FMPClient
from lib.etf.functions.core.distribution_calculator import DistributionCalculator
from test_itan_fmp_workflows import ITAN_HOLDINGS, format_holdings_for_adapter

# ITAN expected distributions (from user's table)
EXPECTED_DISTRIBUTIONS = [
    {"ex_date": "2025-12-23", "record_date": "2025-12-23", "payable_date": "2025-12-24", "income": 0.10},
    {"ex_date": "2025-09-29", "record_date": "2025-09-29", "payable_date": "2025-09-30", "income": 0.14},
    {"ex_date": "2025-06-27", "record_date": "2025-06-27", "payable_date": "2025-06-30", "income": 0.09},
    {"ex_date": "2025-03-28", "record_date": "2025-03-28", "payable_date": "2025-03-31", "income": 0.02},
    {"ex_date": "2024-12-30", "record_date": "2024-12-30", "payable_date": "2024-12-31", "income": 0.08},
]

print("=" * 80)
print("ITAN DISTRIBUTION CALCULATION TEST")
print("=" * 80)
print()

# Setup
api_key = os.getenv('FMP_API_KEY')
if not api_key:
    print("ERROR: FMP_API_KEY not set")
    sys.exit(1)

fmp_client = FMPClient(api_key=api_key)

# Format holdings (exclude cash)
holdings = format_holdings_for_adapter([
    h for h in ITAN_HOLDINGS 
    if h['ticker'] not in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']
])

adapter = FMPDataSourceAdapter(
    manual_holdings=holdings,
    api_key=api_key
)

calculator = DistributionCalculator(fmp_client, adapter)

# Calculate distributions for 2024-2025
start_date = date(2024, 1, 1)
end_date = date(2025, 12, 31)

print(f"Calculating distributions from {start_date} to {end_date}...")
print(f"Using {len(holdings)} holdings")
print()

# For ITAN, estimate shares outstanding based on NAV
# From previous calculation: NAV ~$66M, assume $50/share = ~1.32M shares
# Or we can calculate it quickly
print("Estimating shares outstanding...")
from lib.etf.functions.core import FundAdministration
admin = FundAdministration(data_adapter=adapter, storage_path="./data/test_itan_admin")
nav_calc = admin.calculate_nav(date(2024, 12, 31))
if nav_calc.nav_per_share > 0:
    shares_outstanding = nav_calc.net_assets / nav_calc.nav_per_share
else:
    # Estimate: $66M NAV / $50 per share = 1.32M shares
    shares_outstanding = Decimal('1320000')
print(f"Using {shares_outstanding:,.0f} shares outstanding")
print()

distributions = calculator.calculate_distributions(start_date, end_date, shares_outstanding)

print("=" * 80)
print("CALCULATED DISTRIBUTIONS")
print("=" * 80)
print(f"{'Ex Date':<12} {'Record Date':<12} {'Payable Date':<12} {'Income':>10} {'Total Dist':>12} {'Holdings':>10}")
print("-" * 80)

for dist in distributions:
    print(f"{dist['ex_date']}  {dist['record_date']}  {dist['payable_date']}  "
          f"${dist['income']:>9.4f}  ${dist['total_distribution']:>11.4f}  {dist['holdings_count']:>9}")

print()
print("=" * 80)
print("COMPARISON WITH EXPECTED DISTRIBUTIONS")
print("=" * 80)

# Match calculated with expected by finding closest date
from datetime import timedelta

for expected in EXPECTED_DISTRIBUTIONS:
    ex_date_str = expected['ex_date']
    expected_date = date.fromisoformat(ex_date_str)
    expected_income = expected['income']
    
    # Find closest calculated distribution (within 5 days)
    best_match = None
    best_diff = timedelta(days=100)
    
    for calc in distributions:
        date_diff = abs(calc['ex_date'] - expected_date)
        if date_diff < best_diff and date_diff <= timedelta(days=5):
            best_diff = date_diff
            best_match = calc
    
    if best_match:
        calc_income = best_match['income']
        diff = calc_income - expected_income
        pct_diff = (diff / expected_income * 100) if expected_income > 0 else 0
        date_match = "✓" if best_diff.days == 0 else "≈"
        amount_match = "✓" if abs(diff) < 0.01 else "⚠"
        
        print(f"{date_match}{amount_match} {ex_date_str} (calc: {best_match['ex_date']}): "
              f"Expected ${expected_income:.2f}, Calculated ${calc_income:.4f}, "
              f"Diff: ${diff:+.4f} ({pct_diff:+.1f}%)")
    else:
        print(f"✗ {ex_date_str}: Expected ${expected_income:.2f}, but no distribution found within 5 days")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Calculated distributions: {len(distributions)}")
print(f"Expected distributions: {len(EXPECTED_DISTRIBUTIONS)}")

# Calculate total income
total_expected = sum(d['income'] for d in EXPECTED_DISTRIBUTIONS)
total_calculated = sum(d['income'] for d in distributions)

print(f"Total expected income: ${total_expected:.2f}")
print(f"Total calculated income: ${total_calculated:.4f}")
print(f"Difference: ${total_calculated - total_expected:+.4f}")

