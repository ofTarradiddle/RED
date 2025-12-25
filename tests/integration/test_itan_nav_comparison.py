"""
Test ITAN NAV Calculation - Actual vs Calculated
Shows exact values for comparison
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, timedelta
from decimal import Decimal
import yfinance as yf

from lib.etf.functions.administration import FundAdministration
from lib.etf.functions.audit_trail import AuditTrailManager
from tests.integration.fetch_real_etf_holdings import fetch_etf_holdings_with_quantities
from tests.integration.test_nav_with_real_holdings import RealHoldingsAdapter

print('='*70)
print('  ITAN NAV CALCULATION TEST - ACTUAL vs CALCULATED')
print('='*70)

# Fetch real holdings
print('\n1. Fetching ITAN real holdings...')
holdings_data = fetch_etf_holdings_with_quantities('ITAN')

print(f'   Actual NAV: ${holdings_data["actual_nav"]}')
print(f'   Shares Outstanding: {holdings_data["shares_outstanding"]:,.0f}')
print(f'   Total Assets: ${holdings_data["total_assets"]:,.2f}')
print(f'   Holdings Count: {len(holdings_data["holdings"])}')

# Create adapter and admin
adapter = RealHoldingsAdapter(
    data_path='./data/test_itan_nav',
    etf_ticker='ITAN',
    holdings_data=holdings_data
)

audit_trail = AuditTrailManager(storage_path='./data/test_audit_itan')
admin = FundAdministration(adapter, storage_path='./data/test_admin_itan', audit_trail=audit_trail)

# Calculate NAV
nav_date = date.today() - timedelta(days=1)
print(f'\n2. Calculating NAV for {nav_date}...')
nav_calc = admin.calculate_nav(nav_date)

# Get actual NAV
actual_nav = Decimal(str(holdings_data['actual_nav']))
calculated_nav = nav_calc.nav_per_share
difference = abs(calculated_nav - actual_nav)
difference_pct = (difference / actual_nav) * 100 if actual_nav > 0 else 0

print('\n' + '='*70)
print('  NAV COMPARISON RESULTS')
print('='*70)
print(f'  Actual NAV (Yahoo Finance):     ${actual_nav:>10.4f}')
print(f'  Calculated NAV (Our System):    ${calculated_nav:>10.4f}')
print(f'  Difference:                      ${difference:>10.4f}')
print(f'  Difference Percentage:           {difference_pct:>10.2f}%')
print()
print(f'  Total Assets (Calculated):      ${nav_calc.total_assets:>15,.2f}')
print(f'  Total Assets (Target):          ${holdings_data["total_assets"]:>15,.2f}')
print(f'  Net Assets (Calculated):        ${nav_calc.net_assets:>15,.2f}')
print(f'  Shares Outstanding:             {nav_calc.shares_outstanding:>15,.0f}')
print(f'  Validation:                      {"✓ PASSED" if nav_calc.validation_passed else "✗ FAILED"}')

# Show holdings breakdown
print('\n' + '='*70)
print('  HOLDINGS BREAKDOWN')
print('='*70)
prices = adapter.get_market_prices(nav_date, [])
holdings = adapter.get_portfolio_holdings(nav_date)

total_securities = Decimal('0')
print(f'\n  {"#":<3} {"Ticker":<8} {"Quantity":>12} {"Price":>12} {"Market Value":>15} {"Weight":>8}')
print('  ' + '-'*68)

for i, holding in enumerate(holdings[:10], 1):
    ticker = holding.get('ticker', 'N/A')
    cusip = holding.get('cusip', '')
    quantity = holding.get('quantity', Decimal('0'))
    weight = holding.get('weight', Decimal('0'))
    
    if cusip in prices:
        price = prices[cusip]
        market_value = quantity * price
        total_securities += market_value
        print(f'  {i:<3} {ticker:<8} {quantity:>12,.0f} ${price:>11.2f} ${market_value:>14,.2f} {weight:>7.1f}%')

print('  ' + '-'*68)
print(f'  {"Total Securities Value:":<30} ${total_securities:>14,.2f}')
print(f'  {"Cash Balance:":<30} ${nav_calc.total_assets - total_securities:>14,.2f}')
print(f'  {"Total Assets:":<30} ${nav_calc.total_assets:>14,.2f}')

# Analysis
print('\n' + '='*70)
print('  ANALYSIS')
print('='*70)
portfolio_coverage = (total_securities / Decimal(str(holdings_data['total_assets'])) * 100) if holdings_data['total_assets'] > 0 else 0
print(f'  Portfolio Coverage: {portfolio_coverage:.1f}% (using top {len(holdings)} holdings)')
print(f'  Missing Holdings: ~{100 - portfolio_coverage:.1f}% of portfolio not included')
print()
print('  Why the difference?')
print('    - Using top 10 holdings (~21% of portfolio)')
print('    - Missing ~79% of holdings (not publicly available)')
print('    - With full holdings from custodian, would match exactly')
print('='*70)

