"""
Tests for Transfer Agent function
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.operations.transfer_agent import TransferAgent
from lib.etf.shared import ShareholderRecord, ReconciliationResult


class TestTransferAgent:
    """Test Transfer Agent function"""
    
    def test_daily_reconciliation(self, mock_adapter, temp_storage):
        """Test daily reconciliation"""
        ta = TransferAgent(mock_adapter, temp_storage)
        
        # Set up mock data
        mock_adapter.custodian_data = {
            date(2024, 12, 31): {
                "total_shares": Decimal('1000000')
            }
        }
        mock_adapter.dtc_data = {
            date(2024, 12, 31): {
                "cede_position": Decimal('800000')
            }
        }
        mock_adapter.nscc_data = {
            date(2024, 12, 31): {
                "settled_shares": Decimal('1000000')
            }
        }
        
        # Add a shareholder
        ta.shareholder_registry["ACC001"] = ShareholderRecord(
            account_number="ACC001",
            account_type="beneficial",
            shareholder_name="Test Shareholder",
            shares=Decimal('200000')
        )
        
        result = ta.daily_reconciliation(date(2024, 12, 31))
        
        assert result is not None
        assert isinstance(result, ReconciliationResult)
        assert result.date == date(2024, 12, 31)
        assert result.source1 == "TA"
        assert result.source2 == "Custodian"
    
    def test_update_cede_file(self, mock_adapter, temp_storage):
        """Test Cede & Co. file update"""
        ta = TransferAgent(mock_adapter, temp_storage)
        
        # Set up DTC data
        mock_adapter.dtc_data = {
            date(2024, 12, 31): {
                "cede_position": Decimal('800000')
            }
        }
        
        result = ta.update_cede_file(date(2024, 12, 31))
        
        assert result is not None
        assert "status" in result
        assert "cede_position" in result
        assert "CEDE0000" in ta.shareholder_registry
    
    def test_process_creation_redemption_orders(self, mock_adapter, temp_storage):
        """Test processing creation/redemption orders"""
        ta = TransferAgent(mock_adapter, temp_storage)
        
        from lib.etf.shared import APOrder
        
        # Set up AP orders
        mock_adapter.ap_orders_data = [
            APOrder(
                order_id="ORD001",
                ap_id="AP001",
                order_type="creation",
                creation_units=10,
                order_date=date(2024, 12, 31),
                status="pending"
            )
        ]
        mock_adapter.nscc_data = {
            date(2024, 12, 31): {
                "settled_shares": Decimal('0')
            }
        }
        
        result = ta.process_creation_redemption_orders(date(2024, 12, 31))
        
        assert result is not None
        assert "orders_processed" in result
        assert "total_creations" in result
        assert "AP_AP001" in ta.shareholder_registry
    
    def test_aml_screening(self, mock_adapter, temp_storage):
        """Test AML screening"""
        ta = TransferAgent(mock_adapter, temp_storage)
        
        shareholder = ShareholderRecord(
            account_number="ACC001",
            account_type="beneficial",
            shareholder_name="Test Shareholder",
            shares=Decimal('1000')
        )
        
        result = ta.aml_screening(shareholder)
        
        assert result is not None
        assert "account_number" in result
        assert "ofac_cleared" in result
        assert "aml_cleared" in result
        assert shareholder.ofac_cleared is not None
        assert shareholder.aml_cleared is not None
    
    def test_shareholder_registry_persistence(self, mock_adapter, temp_storage):
        """Test that shareholder registry persists"""
        ta = TransferAgent(mock_adapter, temp_storage)
        
        # Add shareholder
        ta.shareholder_registry["ACC001"] = ShareholderRecord(
            account_number="ACC001",
            account_type="beneficial",
            shareholder_name="Test Shareholder",
            shares=Decimal('1000')
        )
        ta.save_shareholder_registry()
        
        # Create new instance and load
        ta2 = TransferAgent(mock_adapter, temp_storage)
        
        assert "ACC001" in ta2.shareholder_registry
        assert ta2.shareholder_registry["ACC001"].shareholder_name == "Test Shareholder"

