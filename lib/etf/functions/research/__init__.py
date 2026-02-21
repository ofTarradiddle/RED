"""
Research Functions
Backtesting and research tools for ETF strategy development
"""

from lib.etf.functions.research.core import (
    FMPClient,
    HoldingsLoader,
    FundamentalDataLoader,
    PriceLoader,
    YahooPriceLoader,
    Backtester,
    FinancialDataFetcher,
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

