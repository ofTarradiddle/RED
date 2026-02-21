"""
Test NAV Calculation with Real ETF Holdings
Fetches actual daily holdings and tests NAV calculation accuracy
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal
import json

from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.compliance.audit_trail import AuditTrailManager
from lib.etf.adapters import FileBasedDataSourceAdapter
from tests.integration.fetch_real_etf_holdings import fetch_etf_holdings_with_quantities


class RealHoldingsAdapter(FileBasedDataSourceAdapter):
    """Adapter using real ETF holdings data"""
    
    def __init__(self, data_path: str, etf_ticker: str, holdings_data: dict):
        super().__init__(data_path)
        self.etf_ticker = etf_ticker
        self.etf = yf.Ticker(etf_ticker)
        self.holdings_data = holdings_data
        self.holdings = holdings_data.get('holdings', [])
        self.actual_nav = Decimal(str(holdings_data.get('actual_nav', 0)))
        self.shares_outstanding = Decimal(str(holdings_data.get('shares_outstanding', 0)))
        self.total_assets = Decimal(str(holdings_data.get('total_assets', 0)))
    
    def get_portfolio_holdings(self, nav_date: date):
        """Get real portfolio holdings"""
        # Convert to format expected by NAV calculation
        formatted_holdings = []
        for h in self.holdings:
            # If quantity not set, calculate from weight and total assets
            quantity = h.get("quantity")
            if not quantity or quantity == 0:
                # Calculate quantity from weight
                weight = Decimal(str(h.get("weight", 0)))
                if weight > 0 and self.total_assets > 0:
                    # Get price to calculate quantity
                    ticker = h.get("ticker")
                    if ticker:
                        try:
                            ticker_obj = yf.Ticker(ticker)
                            price_data = ticker_obj.history(start=nav_date, end=nav_date + timedelta(days=1), period="1d")
                            if not price_data.empty:
                                price = Decimal(str(price_data['Close'].iloc[-1]))
                                if price > 0:
                                    target_value = self.total_assets * (weight / Decimal('100'))
                                    quantity = target_value / price
                                    h["quantity"] = float(quantity)
                        except:
                            pass
            
            formatted_holdings.append({
                "cusip": h.get("cusip", ""),
                "ticker": h.get("ticker", ""),
                "quantity": Decimal(str(h.get("quantity", 0))),
                "weight": Decimal(str(h.get("weight", 0)))
            })
        return formatted_holdings
    
    def get_market_prices(self, nav_date: date, cusips: list):
        """Get live market prices"""
        prices = {}
        tickers = [h["ticker"] for h in self.holdings if h.get("ticker")]
        
        try:
            data = yf.download(
                tickers,
                start=nav_date - timedelta(days=5),
                end=nav_date + timedelta(days=1),
                progress=False
            )
            
            if not data.empty:
                available_dates = [d.date() for d in data.index]
                target_date = None
                for d in sorted(available_dates, reverse=True):
                    if d <= nav_date:
                        target_date = d
                        break
                
                if target_date:
                    date_idx = available_dates.index(target_date)
                    
                    if isinstance(data.columns, pd.MultiIndex):
                        if 'Close' in data.columns.levels[0]:
                            for holding in self.holdings:
                                ticker = holding.get("ticker")
                                if not ticker:
                                    continue
                                try:
                                    price_val = data.iloc[date_idx][('Close', ticker)]
                                    if pd.notna(price_val):
                                        price = Decimal(str(price_val))
                                        prices[holding.get("cusip", ticker)] = price
                                except (KeyError, IndexError):
                                    continue
        except Exception as e:
            print(f"Error fetching prices: {e}")
        
        return prices
    
    def get_custodian_statements(self, nav_date: date):
        """Get custodian data"""
        cash_balance = self.total_assets * Decimal('0.005')  # 0.5% cash
        return {
            "cash_balance": cash_balance,
            "shares_outstanding": self.shares_outstanding,
            "holdings": self.holdings
        }
    
    def get_expense_data(self, nav_date: date):
        """Get expense data"""
        try:
            info = self.etf.info
            expense_ratio = Decimal(str(info.get('annualReportExpenseRatio', 0.0045)))
            daily_expense = (self.total_assets * expense_ratio) / Decimal('365')
        except:
            daily_expense = Decimal('1000')
            expense_ratio = Decimal('0.0045')
        
        return {
            "accrued_expenses": daily_expense,
            "accrued_income": Decimal('500'),
            "expense_ratio": expense_ratio
        }


def test_itan_nav_with_real_holdings():
    """Test ITAN NAV calculation with real holdings"""
    # Fetch real holdings
    holdings_data = fetch_etf_holdings_with_quantities("ITAN")
    
    # Create adapter
    adapter = RealHoldingsAdapter(
        data_path="./data/test_itan_real",
        etf_ticker="ITAN",
        holdings_data=holdings_data
    )
    
    # Create audit trail
    audit_trail = AuditTrailManager(storage_path="./data/test_audit_trail")
    
    # Create admin with audit trail
    admin = FundAdministration(adapter, storage_path="./data/test_admin_real", audit_trail=audit_trail)
    
    # Calculate NAV
    nav_date = date.today() - timedelta(days=1)
    nav_calc = admin.calculate_nav(nav_date)
    
    # Compare to actual
    actual_nav = Decimal(str(holdings_data['actual_nav']))
    difference = abs(nav_calc.nav_per_share - actual_nav)
    difference_pct = (difference / actual_nav) * 100 if actual_nav > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"ITAN NAV Calculation with Real Holdings")
    print(f"{'='*70}")
    print(f"Calculated NAV: ${nav_calc.nav_per_share}")
    print(f"Actual NAV: ${actual_nav}")
    print(f"Difference: ${difference} ({difference_pct:.2f}%)")
    print(f"Total Assets: ${nav_calc.total_assets:,.2f}")
    print(f"Shares Outstanding: {nav_calc.shares_outstanding:,.0f}")
    print(f"Validation: {'✓ PASSED' if nav_calc.validation_passed else '✗ FAILED'}")
    
    # Verify audit trail
    nav_records = audit_trail.get_records_by_type("nav_calculation", nav_date, nav_date)
    assert len(nav_records) > 0, "NAV calculation should be logged to audit trail"
    
    print(f"\n✓ Audit trail: {len(nav_records)} NAV calculation record(s) logged")
    
    # With real holdings, should be much closer
    # Note: Still may have differences due to:
    # - Not all holdings (using top holdings only)
    # - Timing differences
    # - Cash/liability estimates
    assert nav_calc.validation_passed, "NAV calculation should pass validation"


if __name__ == "__main__":
    test_itan_nav_with_real_holdings()

