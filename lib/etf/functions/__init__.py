"""
ETF Operational Functions
Production-ready implementations of all ETF operational functions.

Organized into logical modules:
- core: Daily operations (NAV, accounting, workflow)
- tax: Tax-related functions (tax lots, reporting, adjustments)
- compliance: SEC filings and audit functions
- operations: Transfer agent, order management, distributions, performance
- supporting: Security master, adviser portal
- research: Backtesting and research tools
"""

# Core Operations
from lib.etf.functions.core import (
    FundAdministration,
    Accounting,
    DailyOrchestrator,
    ShadowAccounting
)

# Tax Functions
from lib.etf.functions.tax import (
    TaxLotManager,
    TaxReporting,
    BookToTaxAdjustments,
    M1Reconciliation,
    TaxFootnote,
    StateTaxReturn,
    StateTaxReporting,
    CapitalGainEstimates,
    FBARFiling,
    FBARFilingSystem
)

# Compliance & Audit
from lib.etf.functions.compliance import (
    Compliance,
    AuditTrailManager,
    AuditCooperation
)

# Operations
from lib.etf.functions.operations import (
    TransferAgent,
    OrderManagement,
    Distributor,
    PerformanceCalculator,
    TradingExecution,
    Rule6c11Compliance,
    TaxEfficiencyOptimizer,
    LiquidityRiskManager,
    IntradayNAVMonitor,
    FairValuationManager
)

# Supporting
from lib.etf.functions.supporting import (
    SecurityMasterFile,
    PortfolioRecords,
    AdviserPortal
)

# Research
from lib.etf.functions.research import (
    FMPClient,
    HoldingsLoader,
    FundamentalDataLoader,
    PriceLoader,
    YahooPriceLoader,
    Backtester,
    estimate_rq_mixedlm
)

__all__ = [
    # Core
    'FundAdministration',
    'Accounting',
    'DailyOrchestrator',
    'ShadowAccounting',
    # Tax
    'TaxLotManager',
    'TaxReporting',
    'BookToTaxAdjustments',
    'M1Reconciliation',
    'TaxFootnote',
    'StateTaxReturn',
    'StateTaxReporting',
    'CapitalGainEstimates',
    'FBARFiling',
    'FBARFilingSystem',
    # Compliance
    'Compliance',
    'AuditTrailManager',
    'AuditCooperation',
    # Operations
    'TransferAgent',
    'OrderManagement',
    'Distributor',
    'PerformanceCalculator',
    'TradingExecution',
    'Rule6c11Compliance',
    'TaxEfficiencyOptimizer',
    'LiquidityRiskManager',
    'IntradayNAVMonitor',
    'FairValuationManager',
    # Supporting
    'SecurityMasterFile',
    'PortfolioRecords',
    'AdviserPortal',
    # Research
    'FMPClient',
    'HoldingsLoader',
    'FundamentalDataLoader',
    'PriceLoader',
    'YahooPriceLoader',
    'Backtester',
    'estimate_rq_mixedlm',
]
