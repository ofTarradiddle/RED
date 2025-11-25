"""
Shared data structures and interfaces for all self-service functions
"""

import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ShareholderRecord:
    """Shareholder account record"""
    account_number: str
    account_type: str  # "beneficial", "registered", "street_name"
    shareholder_name: str
    tax_id: Optional[str] = None
    address: Optional[str] = None
    shares: Decimal = Decimal('0')
    creation_date: date = field(default_factory=date.today)
    last_activity_date: Optional[date] = None
    aml_cleared: bool = False
    ofac_cleared: bool = False


@dataclass
class ReconciliationResult:
    """Reconciliation result"""
    date: date
    source1: str
    source2: str
    source1_balance: Decimal
    source2_balance: Decimal
    difference: Decimal
    status: str  # "matched", "exception"
    exceptions: List[str] = field(default_factory=list)


@dataclass
class NAVCalculation:
    """NAV calculation result"""
    date: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_assets: Decimal
    shares_outstanding: Decimal
    nav_per_share: Decimal
    pricing_exceptions: List[str] = field(default_factory=list)
    validation_passed: bool = True


@dataclass
class PCFFile:
    """Portfolio Composition File"""
    date: date
    creation_unit_size: int
    securities: List[Dict[str, Any]]
    cash_component: Decimal
    estimated_cash_component: Decimal
    total_estimated_value: Decimal
    validation_passed: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class APOrder:
    """Authorized Participant Order"""
    order_id: str
    ap_id: str
    order_type: str  # "creation", "redemption"
    creation_units: int
    basket: Optional[List[Dict[str, Any]]] = None
    order_date: date = field(default_factory=date.today)
    settlement_date: Optional[date] = None
    status: str = "pending"  # "pending", "accepted", "rejected", "settled"
    rejection_reason: Optional[str] = None


class DataSourceAdapter(ABC):
    """Abstract adapter for data sources - implement these for your specific data sources"""
    
    @abstractmethod
    def get_nscc_files(self, date: date) -> Dict[str, Any]:
        """Get NSCC files for the given date"""
        pass
    
    @abstractmethod
    def get_dtc_position_file(self, date: date) -> Dict[str, Any]:
        """Get DTC position file for the given date"""
        pass
    
    @abstractmethod
    def get_custodian_statements(self, date: date) -> Dict[str, Any]:
        """Get custodian statements for the given date"""
        pass
    
    @abstractmethod
    def get_portfolio_holdings(self, date: date) -> List[Dict[str, Any]]:
        """Get portfolio holdings for the given date"""
        pass
    
    @abstractmethod
    def get_market_prices(self, date: date, cusips: List[str]) -> Dict[str, Decimal]:
        """Get market prices for given CUSIPs on the given date"""
        pass
    
    @abstractmethod
    def get_corporate_actions(self, date: date) -> List[Dict[str, Any]]:
        """Get corporate actions for the given date"""
        pass
    
    @abstractmethod
    def get_expense_data(self, date: date) -> Dict[str, Any]:
        """Get expense data for the given date"""
        pass
    
    @abstractmethod
    def get_ap_orders(self, date: date) -> List[APOrder]:
        """Get AP orders for the given date"""
        pass
    
    @abstractmethod
    def get_accounting_data(self, date: date) -> Dict[str, Any]:
        """Get accounting data for the given date"""
        pass
    
    @abstractmethod
    def get_distribution_data(self, date: date) -> Dict[str, Any]:
        """Get distribution data for the given date"""
        pass

