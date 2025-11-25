"""
Pytest configuration and fixtures
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import shutil

from lib.etf.shared import DataSourceAdapter
from lib.etf.adapters import FileBasedDataSourceAdapter


class MockDataSourceAdapter(DataSourceAdapter):
    """
    Mock data adapter for testing
    Provides controlled test data
    """
    
    def __init__(self):
        self.nscc_data = {}
        self.dtc_data = {}
        self.custodian_data = {}
        self.holdings_data = []
        self.prices_data = {}
        self.corporate_actions_data = []
        self.expense_data = {}
        self.ap_orders_data = []
        self.accounting_data = {}
        self.distribution_data = {}
    
    def get_nscc_files(self, date: date):
        return self.nscc_data.get(date, {
            "settled_shares": Decimal('0'),
            "creation_orders": [],
            "redemption_orders": [],
            "settlement_confirmations": []
        })
    
    def get_dtc_position_file(self, date: date):
        return self.dtc_data.get(date, {
            "cede_position": Decimal('0'),
            "total_positions": Decimal('0')
        })
    
    def get_custodian_statements(self, date: date):
        return self.custodian_data.get(date, {
            "cash_balance": Decimal('0'),
            "holdings": [],
            "total_shares": Decimal('0'),
            "shares_outstanding": Decimal('0')
        })
    
    def get_portfolio_holdings(self, date: date):
        return self.holdings_data
    
    def get_market_prices(self, date: date, cusips: list):
        return self.prices_data
    
    def get_corporate_actions(self, date: date):
        return self.corporate_actions_data
    
    def get_expense_data(self, date: date):
        return self.expense_data
    
    def get_ap_orders(self, date: date):
        return self.ap_orders_data
    
    def get_accounting_data(self, date: date):
        return self.accounting_data
    
    def get_distribution_data(self, date: date):
        return self.distribution_data


@pytest.fixture
def mock_adapter():
    """Create a mock data adapter for testing"""
    return MockDataSourceAdapter()


@pytest.fixture
def file_adapter(tmp_path):
    """Create a file-based adapter with temporary storage"""
    storage_path = tmp_path / "data"
    storage_path.mkdir(parents=True, exist_ok=True)
    return FileBasedDataSourceAdapter(str(storage_path))


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage directory"""
    storage_path = tmp_path / "storage"
    storage_path.mkdir(parents=True, exist_ok=True)
    return str(storage_path)


@pytest.fixture
def sample_date():
    """Sample date for testing"""
    return date(2024, 12, 31)


@pytest.fixture
def sample_holdings():
    """Sample portfolio holdings"""
    return [
        {
            "cusip": "037833100",
            "ticker": "AAPL",
            "description": "APPLE INC",
            "quantity": Decimal('1000'),
            "previous_price": Decimal('150.00')
        },
        {
            "cusip": "594918104",
            "ticker": "MSFT",
            "description": "MICROSOFT CORP",
            "quantity": Decimal('500'),
            "previous_price": Decimal('300.00')
        },
        {
            "cusip": "30303M102",
            "ticker": "GOOGL",
            "description": "ALPHABET INC",
            "quantity": Decimal('750'),
            "previous_price": Decimal('120.00')
        }
    ]


@pytest.fixture
def sample_prices():
    """Sample market prices"""
    return {
        "037833100": Decimal('155.00'),
        "594918104": Decimal('305.00'),
        "30303M102": Decimal('125.00')
    }


@pytest.fixture
def sample_custodian_data():
    """Sample custodian data"""
    return {
        "cash_balance": Decimal('50000'),
        "holdings": [
            {
                "cusip": "037833100",
                "quantity": Decimal('1000')
            },
            {
                "cusip": "594918104",
                "quantity": Decimal('500')
            },
            {
                "cusip": "30303M102",
                "quantity": Decimal('750')
            }
        ],
        "total_shares": Decimal('1000000'),
        "shares_outstanding": Decimal('1000000')
    }

