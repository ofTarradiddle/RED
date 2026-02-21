"""
Core Research Modules
Reusable classes and functions for backtesting, data fetching, and factor analysis
"""

from lib.etf.functions.research.core.backtesting import (
    FMPClient,
    HoldingsLoader,
    FundamentalDataLoader,
    PriceLoader,
    YahooPriceLoader,
    Backtester
)

from lib.etf.functions.research.core.data_fetcher import (
    FinancialDataFetcher
)

from lib.etf.functions.research.core.factors import (
    estimate_rq_mixedlm,
    rolling_ols
)

__all__ = [
    # Backtesting
    'FMPClient',
    'HoldingsLoader',
    'FundamentalDataLoader',
    'PriceLoader',
    'YahooPriceLoader',
    'Backtester',
    # Data Fetching
    'FinancialDataFetcher',
    # Factor Analysis
    'estimate_rq_mixedlm',
    'rolling_ols',
]

