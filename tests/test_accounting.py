"""
Tests for Accounting function
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.accounting import Accounting


class TestAccounting:
    """Test Accounting function"""
    
    def test_create_journal_entry(self, mock_adapter, temp_storage):
        """Test creating a journal entry"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        entries = [
            {"account": "1000", "debit": Decimal('1000'), "credit": Decimal('0')},  # Cash
            {"account": "4000", "debit": Decimal('0'), "credit": Decimal('1000')}   # Revenue
        ]
        
        journal_entries = accounting.create_journal_entry(
            entry_date=date(2024, 12, 31),
            entries=entries,
            description="Test entry"
        )
        
        assert journal_entries is not None
        assert len(journal_entries) == 2
        assert journal_entries[0].date == date(2024, 12, 31)
        assert journal_entries[0].description == "Test entry"
        assert journal_entries[0].debit == Decimal('1000')
        assert journal_entries[1].credit == Decimal('1000')
    
    def test_journal_entry_balance(self, mock_adapter, temp_storage):
        """Test that journal entries must balance"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        # Should raise error if debits != credits
        with pytest.raises(ValueError, match="unbalanced"):
            entries = [
                {"account": "1000", "debit": Decimal('1000'), "credit": Decimal('0')},
                {"account": "4000", "debit": Decimal('0'), "credit": Decimal('500')}  # Unbalanced
            ]
            accounting.create_journal_entry(
                entry_date=date(2024, 12, 31),
                entries=entries,
                description="Unbalanced entry"
            )
    
    def test_record_nav_entries(self, mock_adapter, temp_storage):
        """Test recording NAV entries"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        nav_calculation = {
            "total_assets": Decimal('1000000'),
            "total_liabilities": Decimal('50000'),
            "net_assets": Decimal('950000'),
            "shares_outstanding": Decimal('1000000'),
            "nav_per_share": Decimal('0.95')
        }
        
        entries = accounting.record_nav_entries(date(2024, 12, 31), nav_calculation)
        
        assert len(entries) > 0
        assert all(hasattr(e, 'date') for e in entries)
    
    def test_record_expense_accrual(self, mock_adapter, temp_storage):
        """Test recording expense accrual"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        entries = accounting.record_expense_accrual(
            date=date(2024, 12, 31),
            expense_type="Management Fee",
            amount=Decimal('1000'),
            description="Monthly management fee"
        )
        
        assert entries is not None
        assert len(entries) > 0
        assert entries[0].date == date(2024, 12, 31)
    
    def test_generate_trial_balance(self, mock_adapter, temp_storage):
        """Test generating trial balance"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        # Create some entries first
        entries = [
            {"account": "1000", "debit": Decimal('1000'), "credit": Decimal('0')},
            {"account": "4000", "debit": Decimal('0'), "credit": Decimal('1000')}
        ]
        accounting.create_journal_entry(
            entry_date=date(2024, 12, 31),
            entries=entries,
            description="Test entry"
        )
        
        trial_balance = accounting.generate_trial_balance(date(2024, 12, 31))
        
        assert trial_balance is not None
        assert "accounts" in trial_balance
        assert "total_debits" in trial_balance
        assert "total_credits" in trial_balance
        assert trial_balance["total_debits"] == trial_balance["total_credits"]
    
    def test_generate_balance_sheet(self, mock_adapter, temp_storage):
        """Test generating balance sheet"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        balance_sheet = accounting.generate_balance_sheet(date(2024, 12, 31))
        
        assert balance_sheet is not None
        assert "assets" in balance_sheet
        assert "liabilities" in balance_sheet
        assert "equity" in balance_sheet
        assert "total_assets" in balance_sheet
        assert "total_liabilities_equity" in balance_sheet
    
    def test_generate_income_statement(self, mock_adapter, temp_storage):
        """Test generating income statement"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        income_statement = accounting.generate_income_statement(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        assert income_statement is not None
        assert "revenue" in income_statement
        assert "expenses" in income_statement
        assert "net_income" in income_statement
    
    def test_daily_accounting_operations(self, mock_adapter, temp_storage, sample_date):
        """Test daily accounting operations"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        # Set up mock data
        mock_adapter.accounting_data = {
            "nav_data": {
                "total_assets": Decimal('1000000'),
                "total_liabilities": Decimal('50000'),
                "net_assets": Decimal('950000'),
                "shares_outstanding": Decimal('1000000')
            },
            "expenses": [
                {"type": "Management Fee", "amount": Decimal('1000')}
            ]
        }
        
        result = accounting.daily_accounting_operations(sample_date)
        
        assert result is not None
        assert "status" in result
        assert result["status"] == "success"

