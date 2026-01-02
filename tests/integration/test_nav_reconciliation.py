#!/usr/bin/env python3
"""Test NAV reconciliation to match website value"""

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

# ITAN holdings including cash
holdings = [
    {"ticker": "AAPL", "cusip": "037833100", "quantity": 1000, "weight": 1.0, "market_value": 270940},
    {"ticker": "MSFT", "cusip": "594918104", "quantity": 800, "weight": 0.8, "market_value": 378352},
    {"ticker": "GOOGL", "cusip": "02079K305", "quantity": 500, "weight": 0.5, "market_value": 157575},
    {"ticker": "AMZN", "cusip": "023135106", "quantity": 600, "weight": 0.6, "market_value": 135900},
    {"ticker": "IBM", "cusip": "459200101", "quantity": 4405, "weight": 1.97, "market_value": 1283306},
    # Add cash positions
    {"ticker": "Cash&Other", "cusip": "", "quantity": 1, "weight": 0.05, "market_value": 34032},
    {"ticker": "FGXXX", "cusip": "31846V336", "quantity": 124451, "weight": 0.19, "market_value": 124452},
]

print("Testing NAV reconciliation...")
print(f"Website NAV: $66,240,000")
print()

adapter = FMPDataSourceAdapter(
    manual_holdings=holdings,
    api_key=os.getenv('FMP_API_KEY')
)

# Mock custodian data with cash
class MockCustodianAdapter:
    def get_custodian_statements(self, date):
        # Include cash from holdings that don't have prices
        cash_from_holdings = sum(h.get('market_value', 0) for h in holdings 
                                 if h['ticker'] in ['Cash&Other', 'FGXXX'])
        return {
            'cash_balance': cash_from_holdings,
            'shares_outstanding': 0,
            'holdings': []
        }

# Override get_custodian_statements to include cash
original_get_custodian = adapter.get_custodian_statements
def get_custodian_with_cash(rec_date):
    result = original_get_custodian(rec_date)
    # Add cash from cash holdings
    cash_holdings = [h for h in holdings if h['ticker'] in ['Cash&Other', 'FGXXX']]
    cash_total = sum(Decimal(str(h.get('market_value', 0))) for h in cash_holdings)
    result['cash_balance'] = float(cash_total)
    return result

adapter.get_custodian_statements = get_custodian_with_cash

admin = FundAdministration(adapter, storage_path="./data/test_nav_recon")
nav = admin.calculate_nav(date.today())

print(f"Our calculated NAV: ${nav.net_assets:,.2f}")
print(f"Website NAV: $66,240,000.00")
print(f"Difference: ${66240000 - float(nav.net_assets):,.2f}")
print()
print(f"Total assets: ${nav.total_assets:,.2f}")
print(f"Total liabilities: ${nav.total_liabilities:,.2f}")
print(f"Net assets: ${nav.net_assets:,.2f}")

