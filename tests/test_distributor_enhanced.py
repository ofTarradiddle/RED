"""
Tests for Enhanced Distributor Module (Payout Ratio)
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.operations.distributor import Distributor
from tests.conftest import MockDataSourceAdapter


class TestDistributorEnhanced:
    """Test enhanced distributor functionality with payout ratio"""
    
    def test_calculate_distribution_with_payout_ratio(self, temp_storage, mock_adapter):
        """Test distribution calculation with payout ratio"""
        # Set up distribution data
        mock_adapter.distribution_data = {
            date(2024, 3, 31): {
                'dividend_per_share': Decimal('0.10')
            }
        }
        
        distributor = Distributor(mock_adapter, storage_path=str(temp_storage))
        
        nav_data = {
            'shares_outstanding': Decimal('1000000')
        }
        
        # Calculate with 95% payout ratio
        distribution = distributor.calculate_distribution(
            dist_date=date(2024, 3, 31),
            distribution_type="dividend",
            nav_data=nav_data,
            payout_ratio=Decimal('0.95')
        )
        
        assert distribution.distribution_type == "dividend"
        assert distribution.amount_per_share == Decimal('0.095')  # 0.10 * 0.95
        assert distribution.total_amount == Decimal('95000')  # 0.095 * 1M
        assert distribution.shares_outstanding == Decimal('1000000')
    
    def test_calculate_distribution_with_ledger_data(self, temp_storage, mock_adapter):
        """Test distribution calculation using ledger data"""
        distributor = Distributor(mock_adapter, storage_path=str(temp_storage))
        
        nav_data = {
            'shares_outstanding': Decimal('1000000')
        }
        
        # Ledger data with accumulated dividend income
        ledger_data = {
            'Dividend Income': -Decimal('100000')  # Credit balance (negative)
        }
        
        # Calculate with 95% payout
        distribution = distributor.calculate_distribution(
            dist_date=date(2024, 3, 31),
            distribution_type="dividend",
            nav_data=nav_data,
            payout_ratio=Decimal('0.95'),
            ledger_data=ledger_data
        )
        
        # Should distribute 95% of 100k = 95k
        # Per share = 95k / 1M = 0.095
        assert distribution.total_amount == Decimal('95000')
        assert distribution.amount_per_share == Decimal('0.095')
    
    def test_calculate_distribution_full_payout(self, temp_storage, mock_adapter):
        """Test distribution with 100% payout ratio"""
        distributor = Distributor(mock_adapter, storage_path=str(temp_storage))
        
        nav_data = {
            'shares_outstanding': Decimal('1000000')
        }
        
        ledger_data = {
            'Dividend Income': -Decimal('100000')
        }
        
        distribution = distributor.calculate_distribution(
            dist_date=date(2024, 3, 31),
            distribution_type="dividend",
            nav_data=nav_data,
            payout_ratio=Decimal('1.0'),
            ledger_data=ledger_data
        )
        
        # Should distribute 100% of 100k = 100k
        assert distribution.total_amount == Decimal('100000')
        assert distribution.amount_per_share == Decimal('0.10')

