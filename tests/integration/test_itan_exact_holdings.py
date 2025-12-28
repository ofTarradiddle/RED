"""
Test ITAN NAV with EXACT holdings provided by user
Uses the complete holdings list with exact quantities
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, timedelta
from decimal import Decimal
import json
import yfinance as yf
import pandas as pd

from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.compliance.audit_trail import AuditTrailManager
from lib.etf.adapters import FileBasedDataSourceAdapter


class ExactITANHoldingsAdapter(FileBasedDataSourceAdapter):
    """Adapter using EXACT ITAN holdings provided by user"""
    
    def __init__(self, data_path: str, holdings_file: str):
        super().__init__(data_path)
        self.holdings_file = Path(holdings_file)
        with open(self.holdings_file) as f:
            data = json.load(f)
            self.holdings = data['holdings']
        
        # Calculate total assets from holdings
        # Exclude FGXXX (money market fund) from securities, treat as cash
        self.total_securities = sum(
            Decimal(str(h.get('market_value', 0))) 
            for h in self.holdings 
            if h.get('ticker') not in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']
        )
        self.fgxxx = sum(
            Decimal(str(h.get('market_value', 0))) 
            for h in self.holdings 
            if h.get('ticker') == 'FGXXX'
        )
        self.cash = sum(
            Decimal(str(h.get('market_value', 0))) 
            for h in self.holdings 
            if h.get('ticker') == 'Cash&Other'
        )
        self.total_assets = self.total_securities + self.fgxxx + self.cash
        
        # Get actual shares from Yahoo Finance
        try:
            itan = yf.Ticker("ITAN")
            info = itan.info
            actual_nav = Decimal(str(info.get('navPrice', 0)))
            actual_total_assets = Decimal(str(info.get('totalAssets', 0)))
            if actual_nav > 0:
                self.shares_outstanding = actual_total_assets / actual_nav
            else:
                self.shares_outstanding = Decimal('1724312')  # Fallback
        except:
            self.shares_outstanding = Decimal('1724312')  # Fallback
    
    def get_portfolio_holdings(self, nav_date: date):
        """Get exact portfolio holdings"""
        formatted = []
        for h in self.holdings:
            # Exclude cash, invalid holdings, and FGXXX (money market fund)
            if h.get('ticker') in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']:
                continue
            formatted.append({
                "cusip": h.get("cusip", ""),
                "ticker": h.get("ticker", ""),
                "quantity": Decimal(str(h.get("quantity", 0))),
                "weight": Decimal(str(h.get("weight", 0))),
                "price": Decimal(str(h.get("price", 0)))
            })
        return formatted
    
    def get_market_prices(self, nav_date: date, cusips: list):
        """Get prices - use provided prices from holdings"""
        prices = {}
        for h in self.holdings:
            if h.get('ticker') in ['Cash&Other', 'BBG01SQXBKP2', 'FGXXX']:
                continue
            cusip = h.get('cusip', '')
            price = Decimal(str(h.get('price', 0)))
            if cusip and price > 0:
                prices[cusip] = price
        return prices
    
    def get_custodian_statements(self, nav_date: date):
        """Get custodian data"""
        # Include FGXXX as cash equivalent
        return {
            "cash_balance": self.cash + self.fgxxx,
            "shares_outstanding": self.shares_outstanding,
            "holdings": self.holdings
        }
    
    def get_expense_data(self, nav_date: date):
        """Get expense data"""
        expense_ratio = Decimal('0.0045')  # 45 bps
        daily_expense = (self.total_assets * expense_ratio) / Decimal('365')
        return {
            "accrued_expenses": daily_expense,
            "accrued_income": Decimal('500'),
            "expense_ratio": expense_ratio
        }


def test_itan_exact_holdings():
    """Test ITAN NAV with exact holdings"""
    print('='*70)
    print('  ITAN NAV CALCULATION - EXACT HOLDINGS')
    print('='*70)
    
    # Load exact holdings
    holdings_file = project_root / "data" / "real_holdings" / "itan_actual_holdings.json"
    
    # Create adapter
    adapter = ExactITANHoldingsAdapter(
        data_path='./data/test_itan_exact',
        holdings_file=str(holdings_file)
    )
    
    print(f'\nHoldings Loaded: {len(adapter.holdings)}')
    print(f'Total Securities Value: ${adapter.total_securities:,.2f}')
    print(f'FGXXX (Money Market): ${adapter.fgxxx:,.2f}')
    print(f'Cash & Other: ${adapter.cash:,.2f}')
    print(f'Total Assets: ${adapter.total_assets:,.2f}')
    print(f'Shares Outstanding: {adapter.shares_outstanding:,.0f}')
    
    # Calculate expected NAV
    expected_nav = adapter.total_assets / adapter.shares_outstanding
    print(f'\nExpected NAV (from holdings): ${expected_nav:.4f}')
    
    # Create admin with audit trail
    audit_trail = AuditTrailManager(storage_path='./data/test_audit_itan_exact')
    admin = FundAdministration(
        adapter,
        storage_path='./data/test_admin_itan_exact',
        audit_trail=audit_trail
    )
    
    # Calculate NAV
    nav_date = date.today() - timedelta(days=1)
    print(f'\nCalculating NAV for {nav_date}...')
    nav_calc = admin.calculate_nav(nav_date)
    
    # Compare
    difference = abs(nav_calc.nav_per_share - expected_nav)
    difference_pct = (difference / expected_nav) * 100 if expected_nav > 0 else 0
    
    print('\n' + '='*70)
    print('  NAV COMPARISON RESULTS')
    print('='*70)
    print(f'  Expected NAV (from holdings): ${expected_nav:>10.4f}')
    print(f'  Calculated NAV (our system):    ${nav_calc.nav_per_share:>10.4f}')
    print(f'  Difference:                      ${difference:>10.4f}')
    print(f'  Difference Percentage:           {difference_pct:>10.2f}%')
    print()
    print(f'  Total Assets (Calculated):      ${nav_calc.total_assets:>15,.2f}')
    print(f'  Total Assets (Expected):        ${adapter.total_assets:>15,.2f}')
    print(f'  Net Assets (Calculated):        ${nav_calc.net_assets:>15,.2f}')
    print(f'  Shares Outstanding:             {nav_calc.shares_outstanding:>15,.0f}')
    print(f'  Validation:                      {"✓ PASSED" if nav_calc.validation_passed else "✗ FAILED"}')
    
    # Show top holdings
    print('\n' + '='*70)
    print('  TOP 10 HOLDINGS')
    print('='*70)
    holdings = adapter.get_portfolio_holdings(nav_date)
    prices = adapter.get_market_prices(nav_date, [])
    
    # Sort by market value
    holdings_with_mv = []
    for h in holdings:
        cusip = h.get('cusip', '')
        if cusip in prices:
            price = prices[cusip]
            quantity = h.get('quantity', Decimal('0'))
            mv = quantity * price
            holdings_with_mv.append((h, mv))
    
    holdings_with_mv.sort(key=lambda x: x[1], reverse=True)
    
    print(f'\n  {"#":<3} {"Ticker":<8} {"Quantity":>12} {"Price":>12} {"Market Value":>15} {"Weight":>8}')
    print('  ' + '-'*68)
    
    total_mv_calc = Decimal('0')
    for i, (holding, mv) in enumerate(holdings_with_mv[:10], 1):
        total_mv_calc += mv
        ticker = holding.get('ticker', 'N/A')
        quantity = holding.get('quantity', Decimal('0'))
        price = prices.get(holding.get('cusip', ''), Decimal('0'))
        weight = holding.get('weight', Decimal('0'))
        print(f'  {i:<3} {ticker:<8} {quantity:>12,.0f} ${price:>11.2f} ${mv:>14,.2f} {weight:>7.1f}%')
    
    print('  ' + '-'*68)
    print(f'  {"Total Securities (Top 10):":<30} ${total_mv_calc:>14,.2f}')
    print(f'  {"Total Securities (All):":<30} ${adapter.total_securities:>14,.2f}')
    print(f'  {"Cash & Other:":<30} ${adapter.cash:>14,.2f}')
    print(f'  {"Total Assets:":<30} ${adapter.total_assets:>14,.2f}')
    
    # Get actual NAV from Yahoo Finance
    try:
        itan = yf.Ticker("ITAN")
        info = itan.info
        actual_nav = Decimal(str(info.get('navPrice', 0)))
        
        print('\n' + '='*70)
        print('  COMPARISON TO ACTUAL NAV (Yahoo Finance)')
        print('='*70)
        print(f'  Expected NAV (from holdings): ${expected_nav:>10.4f}')
        print(f'  Actual NAV (Yahoo Finance):   ${actual_nav:>10.4f}')
        print(f'  Calculated NAV (our system):   ${nav_calc.nav_per_share:>10.4f}')
        
        diff_expected = abs(expected_nav - actual_nav)
        diff_calculated = abs(nav_calc.nav_per_share - actual_nav)
        
        print()
        print(f'  Expected vs Actual:            ${diff_expected:>10.4f} ({(diff_expected/actual_nav*100):.2f}%)')
        print(f'  Calculated vs Actual:         ${diff_calculated:>10.4f} ({(diff_calculated/actual_nav*100):.2f}%)')
        
        if diff_calculated < Decimal('0.10'):
            print('\n  ✓ EXCELLENT MATCH! (< $0.10 difference)')
        elif diff_calculated < Decimal('1.00'):
            print('\n  ✓ Very close match! (< $1.00 difference)')
        else:
            print('\n  ⚠ Difference may be due to:')
            print('    - Timing differences (holdings date vs NAV date)')
            print('    - Expense accruals')
            print('    - Cash adjustments')
    except Exception as e:
        print(f'\n  ⚠ Could not fetch actual NAV: {e}')
    
    print('='*70)
    
    return nav_calc


if __name__ == "__main__":
    test_itan_exact_holdings()

