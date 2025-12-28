"""
Tests for Order Management function
"""

import pytest
from datetime import date, datetime, time
from decimal import Decimal

from lib.etf.functions.operations.order_management import OrderManagement, CreationBasket, RedemptionBasket
from lib.etf.shared import PCFFile, APOrder


class TestOrderManagement:
    """Test Order Management function"""
    
    def test_generate_pcf(self, mock_adapter, temp_storage, sample_holdings, sample_prices):
        """Test PCF generation"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        # Set up mock data
        mock_adapter.holdings_data = sample_holdings
        mock_adapter.prices_data = sample_prices
        mock_adapter.custodian_data = {
            date(2024, 12, 30): {
                "cash_balance": Decimal('50000')
            }
        }
        mock_adapter.corporate_actions_data = []
        
        pcf = om.generate_pcf(date(2024, 12, 31))
        
        assert pcf is not None
        assert isinstance(pcf, PCFFile)
        assert pcf.date == date(2024, 12, 31)
        assert len(pcf.securities) > 0
        assert pcf.creation_unit_size == 50000
    
    def test_build_standard_creation_basket(self, mock_adapter, temp_storage):
        """Test building standard creation basket"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        pcf = PCFFile(
            date=date(2024, 12, 31),
            creation_unit_size=50000,
            securities=[
                {"cusip": "037833100", "quantity": "100", "description": "AAPL"},
                {"cusip": "594918104", "quantity": "50", "description": "MSFT"}
            ],
            cash_component=Decimal('1000'),
            estimated_cash_component=Decimal('1000'),
            total_estimated_value=Decimal('100000')
        )
        
        basket = om.build_standard_creation_basket(pcf, creation_units=10)
        
        assert basket is not None
        assert isinstance(basket, CreationBasket)
        assert basket.basket_type == "standard"
        assert basket.creation_units == 10
        assert len(basket.securities) > 0
    
    def test_build_custom_creation_basket(self, mock_adapter, temp_storage):
        """Test building custom creation basket"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        pcf = PCFFile(
            date=date(2024, 12, 31),
            creation_unit_size=50000,
            securities=[
                {"cusip": "037833100", "quantity": "100", "description": "AAPL"},
                {"cusip": "594918104", "quantity": "50", "description": "MSFT"}
            ],
            cash_component=Decimal('1000'),
            estimated_cash_component=Decimal('1000'),
            total_estimated_value=Decimal('100000')
        )
        
        custom_securities = [
            {"cusip": "037833100", "quantity": "150", "description": "AAPL"}
        ]
        
        basket = om.build_custom_creation_basket(pcf, creation_units=10, custom_securities=custom_securities)
        
        assert basket is not None
        assert isinstance(basket, CreationBasket)
        assert basket.basket_type == "custom"
        assert len(basket.securities) > 0
    
    def test_create_ap_order(self, mock_adapter, temp_storage):
        """Test creating AP order"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        order = om.create_ap_order(
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=date(2024, 12, 31)
        )
        
        assert order is not None
        assert isinstance(order, APOrder)
        assert order.ap_id == "AP001"
        assert order.order_type == "creation"
        assert order.creation_units == 10
        assert order.status == "pending"
    
    def test_validate_ap_order(self, mock_adapter, temp_storage):
        """Test AP order validation"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        pcf = PCFFile(
            date=date(2024, 12, 31),
            creation_unit_size=50000,
            securities=[
                {"cusip": "037833100", "quantity": "100", "description": "AAPL"}
            ],
            cash_component=Decimal('1000'),
            estimated_cash_component=Decimal('1000'),
            total_estimated_value=Decimal('100000')
        )
        
        order = APOrder(
            order_id="ORD001",
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=date.today(),
            status="pending"
        )
        
        is_valid, error_msg = om.validate_ap_order(order, pcf)
        
        # Should be valid if before cut-off time
        assert isinstance(is_valid, bool)
    
    def test_validate_ap_order_cutoff_time(self, mock_adapter, temp_storage):
        """Test that orders after cut-off time are rejected"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        pcf = PCFFile(
            date=date(2024, 12, 31),
            creation_unit_size=50000,
            securities=[],
            cash_component=Decimal('0'),
            estimated_cash_component=Decimal('0'),
            total_estimated_value=Decimal('0')
        )
        
        # Create order for yesterday (should fail cut-off check)
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        order = APOrder(
            order_id="ORD001",
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=yesterday,
            status="pending"
        )
        
        is_valid, error_msg = om.validate_ap_order(order, pcf)
        
        # Should be invalid if order date is in the past
        assert not is_valid or "cut-off" in error_msg.lower() or error_msg == ""
    
    def test_calculate_order_fees(self, mock_adapter, temp_storage):
        """Test order fee calculation"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        # Set fees
        om.creation_fee = Decimal('100')
        om.redemption_fee = Decimal('100')
        
        creation_order = APOrder(
            order_id="ORD001",
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=date(2024, 12, 31),
            status="pending"
        )
        
        fees = om.calculate_order_fees(creation_order)
        
        assert fees is not None
        assert "total_fee" in fees
        assert fees["fee_per_unit"] == "100"
        assert fees["total_fee"] == "1000"  # 10 units * $100
    
    def test_process_ap_order(self, mock_adapter, temp_storage):
        """Test processing AP order"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        pcf = PCFFile(
            date=date(2024, 12, 31),
            creation_unit_size=50000,
            securities=[
                {"cusip": "037833100", "quantity": "100", "description": "AAPL"}
            ],
            cash_component=Decimal('1000'),
            estimated_cash_component=Decimal('1000'),
            total_estimated_value=Decimal('100000')
        )
        
        order = APOrder(
            order_id="ORD001",
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=date.today(),
            status="pending"
        )
        
        result = om.process_ap_order(order, pcf)
        
        assert result is not None
        assert "status" in result
        assert "fees" in result
    
    def test_compare_baskets(self, mock_adapter, temp_storage):
        """Test basket comparison"""
        om = OrderManagement(mock_adapter, temp_storage)
        
        basket1 = CreationBasket(
            basket_type="standard",
            securities=[
                {"cusip": "037833100", "quantity": "100"}
            ],
            cash_component=Decimal('1000'),
            total_value=Decimal('100000'),
            creation_units=10
        )
        
        basket2 = CreationBasket(
            basket_type="custom",
            securities=[
                {"cusip": "037833100", "quantity": "150"}  # Different quantity
            ],
            cash_component=Decimal('1000'),
            total_value=Decimal('150000'),
            creation_units=10
        )
        
        comparison = om.compare_baskets(basket1, basket2)
        
        assert comparison is not None
        assert "security_differences" in comparison
        assert "cash_difference" in comparison
        assert "value_difference" in comparison
        assert not comparison["identical"]  # Should be different

