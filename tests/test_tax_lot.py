"""
Tests for Tax Lot Accounting Module
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from lib.etf.functions.tax_lot import TaxLotManager, TaxLot, RealizedGainRecord


class TestTaxLotManager:
    """Test TaxLotManager functionality"""
    
    def test_add_lot(self, temp_storage):
        """Test adding a new tax lot"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        lot = manager.add_lot(
            ticker="AAPL",
            quantity=Decimal('100'),
            cost_basis=Decimal('150.00'),
            purchase_date=date(2024, 1, 15)
        )
        
        assert lot.ticker == "AAPL"
        assert lot.quantity == Decimal('100')
        assert lot.cost_basis == Decimal('150.00')
        assert lot.purchase_date == date(2024, 1, 15)
        assert len(manager.open_lots) == 1
    
    def test_sell_fifo(self, temp_storage):
        """Test selling shares using FIFO method"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Add two lots
        manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))
        manager.add_lot("AAPL", Decimal('50'), Decimal('155.00'), date(2024, 2, 20))
        
        # Sell 75 shares at $160
        gain = manager.sell("AAPL", Decimal('75'), Decimal('160.00'), date(2024, 3, 15))
        
        # Should sell from first lot (FIFO)
        # Gain = (160 - 150) * 75 = 750
        assert gain == Decimal('750.00')
        assert len(manager.open_lots) == 2  # First lot partially sold, second lot intact
        assert manager.open_lots[0].quantity == Decimal('25')  # 100 - 75 = 25 remaining
        assert len(manager.realized_gains) == 1
        assert manager.realized_gains[0].term == 'short'  # < 365 days
    
    def test_sell_long_term(self, temp_storage):
        """Test selling shares with long-term holding period"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Add lot from over a year ago
        manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2023, 1, 1))
        
        # Sell after 400 days (long-term)
        gain = manager.sell("AAPL", Decimal('50'), Decimal('160.00'), date(2024, 2, 5))
        
        assert len(manager.realized_gains) == 1
        assert manager.realized_gains[0].term == 'long'  # >= 365 days
        assert gain == Decimal('500.00')  # (160 - 150) * 50
    
    def test_sell_insufficient_lots(self, temp_storage):
        """Test error when trying to sell more shares than available"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))
        
        with pytest.raises(ValueError, match="Not enough lots to sell"):
            manager.sell("AAPL", Decimal('150'), Decimal('160.00'), date(2024, 3, 15))
    
    def test_get_unrealized_gains(self, temp_storage):
        """Test calculating unrealized gains"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Use dates that ensure short-term vs long-term classification
        as_of_date = date(2024, 3, 15)  # Fixed date for deterministic test
        
        manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))  # 60 days = short-term
        manager.add_lot("GOOGL", Decimal('50'), Decimal('100.00'), date(2023, 6, 1))  # 288 days = short-term (but close to long)
        
        # Use a date that makes GOOGL long-term
        as_of_date_long = date(2024, 7, 1)  # GOOGL purchased 2023-06-01, so 395 days = long-term
        
        current_prices = {
            "AAPL": Decimal('160.00'),
            "GOOGL": Decimal('110.00')
        }
        
        result = manager.get_unrealized_gains(current_prices, as_of_date=as_of_date_long)
        
        # AAPL: (160 - 150) * 100 = 1000 (short-term, 167 days)
        # GOOGL: (110 - 100) * 50 = 500 (long-term, 395 days)
        assert Decimal(result['unrealized_short_term']) == Decimal('1000.00')
        assert Decimal(result['unrealized_long_term']) == Decimal('500.00')
        assert Decimal(result['unrealized_total']) == Decimal('1500.00')
    
    def test_get_realized_gains_summary(self, temp_storage):
        """Test getting realized gains summary"""
        manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Add and sell lots
        manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2023, 1, 1))
        manager.add_lot("GOOGL", Decimal('50'), Decimal('100.00'), date(2024, 1, 1))
        
        manager.sell("AAPL", Decimal('50'), Decimal('160.00'), date(2024, 2, 1))  # Long-term
        manager.sell("GOOGL", Decimal('25'), Decimal('110.00'), date(2024, 2, 15))  # Short-term
        
        summary = manager.get_realized_gains_summary(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        assert Decimal(summary['long_term_gains']) == Decimal('500.00')  # (160-150)*50
        assert Decimal(summary['short_term_gains']) == Decimal('250.00')  # (110-100)*25
        assert summary['transactions_count'] == 2
    
    def test_persistence(self, temp_storage):
        """Test that tax lots are saved and loaded correctly"""
        manager1 = TaxLotManager(storage_path=str(temp_storage))
        manager1.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))
        manager1.save_tax_lots()
        
        # Create new manager instance - should load existing lots
        manager2 = TaxLotManager(storage_path=str(temp_storage))
        assert len(manager2.open_lots) == 1
        assert manager2.open_lots[0].ticker == "AAPL"
        assert manager2.open_lots[0].quantity == Decimal('100')

