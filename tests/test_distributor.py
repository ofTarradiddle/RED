"""
Tests for Distributor function
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from lib.etf.functions.operations.distributor import Distributor, DistributionRecord


class TestDistributor:
    """Test Distributor function"""
    
    def test_calculate_distribution(self, mock_adapter, temp_storage):
        """Test distribution calculation"""
        distributor = Distributor(mock_adapter, temp_storage)
        
        # Set up mock data - distribution_data should be returned by get_distribution_data
        mock_adapter.distribution_data = {
            date(2024, 12, 31): {
                "dividend_per_share": Decimal('0.005'),
                "capital_gains_per_share": Decimal('0.002'),
                "roc_per_share": Decimal('0')
            }
        }
        
        nav_data = {
            "net_assets": Decimal('1000000'),
            "shares_outstanding": Decimal('1000000')
        }
        
        distribution = distributor.calculate_distribution(
            date(2024, 12, 31),
            "dividend",
            nav_data
        )
        
        assert distribution is not None
        assert isinstance(distribution, DistributionRecord)
        assert distribution.distribution_type == "dividend"
        assert distribution.amount_per_share > 0
    
    def test_declare_distribution(self, mock_adapter, temp_storage):
        """Test distribution declaration"""
        distributor = Distributor(mock_adapter, temp_storage)
        
        distribution = DistributionRecord(
            distribution_id="DIST001",
            distribution_type="dividend",
            record_date=date(2024, 12, 31),
            ex_date=date(2025, 1, 2),
            pay_date=date(2025, 1, 15),
            amount_per_share=Decimal('0.10'),
            total_amount=Decimal('100000'),
            shares_outstanding=Decimal('1000000')
        )
        
        # Add distribution to list first (as calculate_distribution would do)
        distributor.distributions.append(distribution)
        
        result = distributor.declare_distribution(distribution)
        
        assert result is not None
        assert "distribution_id" in result
        assert distribution in distributor.distributions
        assert distribution.status == "declared"
    
    def test_process_distribution_payment(self, mock_adapter, temp_storage):
        """Test distribution payment processing"""
        distributor = Distributor(mock_adapter, temp_storage)
        
        distribution = DistributionRecord(
            distribution_id="DIST001",
            distribution_type="dividend",
            record_date=date(2024, 12, 31),
            ex_date=date(2025, 1, 2),
            pay_date=date(2025, 1, 15),
            amount_per_share=Decimal('0.10'),
            total_amount=Decimal('100000'),
            shares_outstanding=Decimal('1000000'),
            status="declared"
        )
        
        distributor.distributions.append(distribution)
        
        shareholder_data = [
            {
                "account_number": "ACC001",
                "shareholder_name": "Test Shareholder",
                "shares": Decimal('500000')
            },
            {
                "account_number": "ACC002",
                "shareholder_name": "Test Shareholder 2",
                "shares": Decimal('500000')
            }
        ]
        
        result = distributor.process_distribution_payment(distribution, shareholder_data)
        
        assert result is not None
        assert "distribution_id" in result
        assert "payments_processed" in result
        assert distribution.status == "paid"
    
    def test_generate_distribution_schedule(self, mock_adapter, temp_storage):
        """Test distribution schedule generation"""
        distributor = Distributor(mock_adapter, temp_storage)
        
        # Add some distributions
        distributor.distributions = [
            DistributionRecord(
                distribution_id="DIST001",
                distribution_type="dividend",
                record_date=date(2024, 12, 31),
                ex_date=date(2025, 1, 2),
                pay_date=date(2025, 1, 15),
                amount_per_share=Decimal('0.10'),
                total_amount=Decimal('100000'),
                shares_outstanding=Decimal('1000000')
            )
        ]
        
        schedule = distributor.generate_distribution_schedule(year=2024)
        
        assert schedule is not None
        assert "year" in schedule
        assert "distributions" in schedule
        assert len(schedule["distributions"]) > 0

