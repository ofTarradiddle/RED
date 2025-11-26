"""
Tests for Fund Administration function
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.administration import FundAdministration
from lib.etf.shared import NAVCalculation


class TestFundAdministration:
    """Test Fund Administration function"""
    
    def test_calculate_nav(self, mock_adapter, temp_storage, sample_holdings, sample_prices, sample_custodian_data):
        """Test NAV calculation"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Set up mock data
        mock_adapter.holdings_data = sample_holdings
        mock_adapter.prices_data = sample_prices
        mock_adapter.custodian_data = {date(2024, 12, 31): sample_custodian_data}
        mock_adapter.expense_data = {
            "accrued_income": Decimal('0'),
            "accrued_expenses": Decimal('1000'),
            "payables": Decimal('0')
        }
        
        nav = admin.calculate_nav(date(2024, 12, 31))
        
        assert nav is not None
        assert isinstance(nav, NAVCalculation)
        assert nav.date == date(2024, 12, 31)
        assert nav.total_assets > 0
        assert nav.net_assets > 0
        assert nav.nav_per_share > 0
    
    def test_calculate_nav_with_zero_shares(self, mock_adapter, temp_storage):
        """Test NAV calculation with zero shares outstanding"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Set up mock data with zero shares
        mock_adapter.custodian_data = {
            date(2024, 12, 31): {
                "cash_balance": Decimal('0'),
                "holdings": [],
                "total_shares": Decimal('0'),
                "shares_outstanding": Decimal('0')
            }
        }
        mock_adapter.holdings_data = []
        mock_adapter.prices_data = {}
        mock_adapter.expense_data = {}
        
        nav = admin.calculate_nav(date(2024, 12, 31))
        
        assert nav is not None
        assert nav.shares_outstanding == 0
        # When shares_outstanding is 0, nav_per_share should be 0 (set in the function)
        assert nav.nav_per_share == 0
        assert not nav.validation_passed
        assert len(nav.pricing_exceptions) > 0
    
    def test_reconcile_holdings_cash(self, mock_adapter, temp_storage, sample_holdings, sample_custodian_data):
        """Test holdings and cash reconciliation"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Set up mock data
        mock_adapter.holdings_data = sample_holdings
        mock_adapter.custodian_data = {date(2024, 12, 31): sample_custodian_data}
        
        result = admin.reconcile_holdings_cash(date(2024, 12, 31))
        
        assert result is not None
        assert "status" in result
        assert "date" in result
        assert result["date"] == date(2024, 12, 31).isoformat()
    
    def test_reconcile_holdings_mismatch(self, mock_adapter, temp_storage):
        """Test reconciliation with mismatched holdings"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Set up mismatched data
        mock_adapter.holdings_data = [
            {
                "cusip": "037833100",
                "quantity": Decimal('1000')
            }
        ]
        mock_adapter.custodian_data = {
            date(2024, 12, 31): {
                "holdings": [
                    {
                        "cusip": "037833100",
                        "quantity": Decimal('500')  # Different quantity
                    }
                ],
                "cash_balance": Decimal('0')
            }
        }
        
        result = admin.reconcile_holdings_cash(date(2024, 12, 31))
        
        assert result is not None
        assert result["status"] == "exception"
        assert len(result["exceptions"]) > 0
    
    def test_process_corporate_actions(self, mock_adapter, temp_storage):
        """Test corporate actions processing"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Set up corporate actions
        mock_adapter.corporate_actions_data = [
            {
                "action_type": "dividend",
                "cusip": "037833100",
                "ex_date": "2024-12-31",
                "pay_date": "2025-01-15",
                "amount": Decimal('0.50')
            }
        ]
        
        result = admin.process_corporate_actions(date(2024, 12, 31))
        
        assert result is not None
        assert "date" in result
        assert "actions_processed" in result
        assert result["actions_processed"] > 0
        assert "actions" in result
    
    def test_calculate_expense_ratio(self, mock_adapter, temp_storage):
        """Test expense ratio calculation"""
        admin = FundAdministration(mock_adapter, temp_storage)
        
        # Create some NAV history
        nav_file = admin.storage_path / "nav_2024-12-31.json"
        nav_file.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(nav_file, 'w') as f:
            json.dump({
                "date": "2024-12-31",
                "net_assets": "1000000"
            }, f)
        
        mock_adapter.expense_data = {
            "total_expenses": Decimal('5000')
        }
        
        result = admin.calculate_expense_ratio(
            date(2024, 12, 1),
            date(2024, 12, 31)
        )
        
        assert result is not None
        assert "expense_ratio" in result
        assert "total_expenses" in result
        assert "average_net_assets" in result

