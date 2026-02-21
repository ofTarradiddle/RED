"""
ETF Self-Service Functions Package

Production-ready implementations for all ETF operational functions:
- Accounting
- Administration
- Transfer Agent
- Order Management
- Distributor
"""

from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.operations.transfer_agent import TransferAgent
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.functions.operations.distributor import Distributor
from lib.etf.functions.compliance.compliance import Compliance
from lib.etf.functions.tax.tax_reporting import TaxReporting

from lib.etf.adapters import (
    DataSourceAdapter,
    ExampleDataSourceAdapter,
    FileBasedDataSourceAdapter,
    FMPDataSourceAdapter
)

from lib.etf.shared import (
    ShareholderRecord,
    ReconciliationResult,
    NAVCalculation,
    PCFFile,
    APOrder
)

__all__ = [
    # Functions
    'Accounting',
    'FundAdministration',
    'TransferAgent',
    'OrderManagement',
    'Distributor',
    'Compliance',
    'TaxReporting',
    # Adapters
    'DataSourceAdapter',
    'ExampleDataSourceAdapter',
    'FileBasedDataSourceAdapter',
    'FMPDataSourceAdapter',
    # Shared
    'ShareholderRecord',
    'ReconciliationResult',
    'NAVCalculation',
    'PCFFile',
    'APOrder',
]

__version__ = '1.0.0'

