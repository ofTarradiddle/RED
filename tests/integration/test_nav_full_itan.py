#!/usr/bin/env python3
"""Full NAV test with all ITAN holdings including cash"""

import os
import sys
from pathlib import Path
from datetime import date
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
from lib.etf.functions.core import FundAdministration

# Import full ITAN holdings
from test_itan_fmp_workflows import ITAN_HOLDINGS

# Include ALL holdings (stocks + cash + money market)
ALL_HOLDINGS = ITAN_HOLDINGS  # Don't filter anything

print("=" * 60)
print("NAV Reconciliation Test - Full ITAN Holdings")
print("=" * 60)
print(f"Holdings: {len(ALL_HOLDINGS)} (including cash)")
print(f"Website NAV: $66,240,000")
print()

# Calculate expected cash from holdings
cash_items = [h for h in ALL_HOLDINGS if h['ticker'] in ['Cash&Other', 'FGXXX']]
cash_total = sum(h.get('market_value', 0) for h in cash_items)
print(f"Cash & Money Market from holdings: ${cash_total:,}")
print()

adapter = FMPDataSourceAdapter(
    manual_holdings=ALL_HOLDINGS,
    api_key=os.getenv('FMP_API_KEY')
)

admin = FundAdministration(adapter, storage_path="./data/test_nav_full")
nav = admin.calculate_nav(date.today())

print(f"Our calculated NAV: ${nav.net_assets:,.2f}")
print(f"Website NAV: $66,240,000.00")
difference = 66240000 - float(nav.net_assets)
print(f"Difference: ${difference:,.2f}")
print()
print(f"Breakdown:")
print(f"  Total securities value: ${nav.total_assets - Decimal(str(cash_total)):,.2f}")
print(f"  Cash & money market: ${cash_total:,.2f}")
print(f"  Total assets: ${nav.total_assets:,.2f}")
print(f"  Total liabilities: ${nav.total_liabilities:,.2f}")
print(f"  Net assets: ${nav.net_assets:,.2f}")
print()

if abs(difference) < 1000:
    print("✓ NAV matches website (within $1,000)")
elif abs(difference) < 50000:
    print(f"⚠ NAV close to website (difference: ${difference:,.2f})")
    print("  Possible causes:")
    print("  - Accrued income/expenses")
    print("  - Price timing differences (EOD vs real-time)")
    print("  - Rounding differences")
else:
    print(f"✗ NAV differs significantly (difference: ${difference:,.2f})")

