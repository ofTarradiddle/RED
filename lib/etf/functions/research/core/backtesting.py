"""
Backtesting Module for Factor-Based ETF Strategy Research
Production-ready implementation for backtesting factor-based investment strategies.

This module provides:
- FMPClient: API interface to Financial Modeling Prep for market data
- HoldingsLoader: Loads ETF holdings (point-in-time constituents)
- FundamentalDataLoader: Loads fundamental data and computes factor metrics
- PriceLoader: Loads historical prices and calculates returns
- Backtester: Backtesting engine for factor-based monthly rebalanced portfolios

Example:
    >>> from lib.etf.functions.research import FMPClient, HoldingsLoader, Backtester
    >>> fmp = FMPClient(api_key="your_api_key")
    >>> holdings_loader = HoldingsLoader(fmp, etf_symbol="IWB")
    >>> backtester = Backtester(fmp, holdings_loader, ...)
    >>> backtester.run_backtest()
    >>> perf = backtester.evaluate_performance()
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.getLogger(__name__).warning("requests not available - FMPClient will not work")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.getLogger(__name__).warning("yfinance not available - YahooPriceLoader will not work")

logger = logging.getLogger(__name__)


class FMPClient:
    """
    API interface to Financial Modeling Prep (FMP).
    Handles requests, caching, and data retrieval for fundamentals, prices, and ETF holdings.
    
    Args:
        api_key: FMP API key (optional, can be set via environment variable FMP_API_KEY)
        base_url: Base URL for FMP API (default: https://financialmodelingprep.com)
        cache_dir: Directory for caching API responses (default: ./data/research/cache)
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 base_url: str = "https://financialmodelingprep.com",
                 cache_dir: str = "./data/research/cache"):
        self.api_key = api_key or os.getenv('FMP_API_KEY')
        self.base_url = base_url.rstrip('/')
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.query_log: List[Dict[str, Any]] = []
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for FMPClient. Install with: pip install requests")
    
    def _cache_path(self, endpoint: str, params: Dict[str, Any]) -> Path:
        """Generate cache file path from endpoint and parameters."""
        ep = endpoint.replace('/', '_').strip('_')
        param_str = "_".join(f"{k}-{v}" for k, v in sorted(params.items()) if k != 'apikey')
        filename = f"{ep}_{param_str}.json"
        filename = filename.replace("=", "-").replace("&", "-").replace("?", "-")
        return self.cache_dir / filename
    
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Make GET request to FMP API with caching.
        
        Args:
            endpoint: API endpoint (e.g., "api/v3/income-statement/AAPL")
            params: Query parameters
            
        Returns:
            JSON response data or None if request fails
        """
        params = params or {}
        if self.api_key:
            params['apikey'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        cache_path = self._cache_path(endpoint, params)
        
        # Try to load from cache
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                logger.debug(f"Loaded from cache: {cache_path}")
                self.query_log.append({'endpoint': endpoint, 'params': params, 'cached': True})
                return data
            except Exception as e:
                logger.warning(f"Error loading cache {cache_path}: {e}")
        
        # Make API request
        try:
            logger.info(f"Fetching URL: {url} Params: {dict((k, v) for k, v in params.items() if k != 'apikey')}")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Request failed: {url} Status: {response.status_code}")
                return None
            
            data = response.json()
            
            # Save to cache
            try:
                with open(cache_path, 'w') as f:
                    json.dump(data, f, indent=2)
                logger.debug(f"Saved to cache: {cache_path}")
            except Exception as e:
                logger.warning(f"Error saving cache {cache_path}: {e}")
            
            self.query_log.append({'endpoint': endpoint, 'params': params, 'cached': False})
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception for {url}: {e}")
            return None
    
    def get_etf_holdings(self, symbol: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get ETF holdings for a given symbol and optional date.
        
        Uses stable/etf/holdings endpoint which supports date parameter for historical data.
        The api/v4 endpoints are legacy and restricted for new users.
        
        Args:
            symbol: ETF symbol (e.g., "IWB")
            date: Optional date string (YYYY-MM-DD) for historical holdings
            
        Returns:
            List of holding dictionaries
        """
        # Use stable endpoint - it supports date parameter for historical data
        endpoint = "stable/etf/holdings"
        params = {'symbol': symbol}
        if date:
            params['date'] = date
        
        result = self._get(endpoint, params)
        return result if isinstance(result, list) else []
    
    def get_etf_holding_dates(self, symbol: str) -> List[str]:
        """
        Get list of available dates for ETF holdings.
        
        Args:
            symbol: ETF symbol
            
        Returns:
            List of date strings (YYYY-MM-DD)
        """
        endpoint = "api/v4/etf-holdings/portfolio-date"
        params = {'symbol': symbol}
        data = self._get(endpoint, params)
        
        if isinstance(data, list):
            return [item.get('date') for item in data if item.get('date')]
        return []
    
    def get_enterprise_values(self, symbol: str) -> Dict[str, Any]:
        """Get enterprise value data for a symbol."""
        endpoint = "stable/enterprise-values"
        params = {'symbol': symbol}
        data = self._get(endpoint, params)
        
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}
    
    def get_market_cap(self, symbol: str) -> Dict[str, Any]:
        """Get market capitalization data for a symbol."""
        endpoint = "stable/market-capitalization"
        params = {'symbol': symbol}
        data = self._get(endpoint, params)
        
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}
    
    def get_income_statement(self, symbol: str, period: str = 'annual', limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get income statement data for a symbol.
        Uses the stable/income-statement endpoint (new API format).
        
        Args:
            symbol: Stock symbol
            period: 'annual' for FY statements, 'quarter' for quarterly
            limit: Optional limit on number of statements (None = all available, 
                   recommended: 30 for ~30 years of annual data)
            
        Returns:
            List of income statement dictionaries, sorted by date (newest first)
        """
        endpoint = "stable/income-statement"
        params = {'symbol': symbol}
        # Add limit parameter - this is important for getting historical data
        # Without limit, API may only return recent statements
        if limit:
            params['limit'] = limit
        else:
            # Default to 30 for annual to get ~30 years of data
            params['limit'] = 30
        
        result = self._get(endpoint, params)
        if isinstance(result, list):
            # Filter by period if needed (FY for annual, Q1-Q4 for quarterly)
            if period == 'annual':
                result = [item for item in result if item.get('period') == 'FY']
            elif period == 'quarter':
                result = [item for item in result if item.get('period') in ['Q1', 'Q2', 'Q3', 'Q4']]
            
            # Sort by date (newest first, which is typically how API returns it)
            result.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Apply limit if specified and not already applied by API
            # (in case we want fewer than what API returned)
            if limit and len(result) > limit:
                result = result[:limit]
            
            return result
        return []
    
    def get_cash_flow_statement(self, symbol: str, period: str = 'annual', limit: int = 1) -> List[Dict[str, Any]]:
        """
        Get cash flow statement data for a symbol.
        Uses the stable/cash-flow-statement endpoint (new API format).
        """
        endpoint = "stable/cash-flow-statement"
        params = {'symbol': symbol}
        result = self._get(endpoint, params)
        if isinstance(result, list):
            # Filter by period if needed
            if period == 'annual':
                result = [item for item in result if item.get('period') == 'FY']
            elif period == 'quarter':
                result = [item for item in result if item.get('period') in ['Q1', 'Q2', 'Q3', 'Q4']]
            # Apply limit
            if limit and len(result) > limit:
                result = result[:limit]
            return result
        return []
    
    def get_price_history(self, symbol: str, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol: Stock/ETF symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with date index and adjusted close price
        """
        endpoint = f"api/v3/historical-price-full/{symbol}"
        params = {}
        if start_date:
            params['from'] = start_date
        if end_date:
            params['to'] = end_date
        
        data = self._get(endpoint, params)
        
        if not data or not isinstance(data, dict) or 'historical' not in data:
            logger.warning(f"No price history data for {symbol}")
            return pd.DataFrame()
        
        hist = data['historical']
        if not hist:
            return pd.DataFrame()
        
        df = pd.DataFrame(hist)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
        
        # Prefer adjusted close, fall back to close
        if 'adjClose' in df.columns:
            df = df[['adjClose']].rename(columns={'adjClose': symbol})
        elif 'adjustedClose' in df.columns:
            df = df[['adjustedClose']].rename(columns={'adjustedClose': symbol})
        elif 'close' in df.columns:
            df = df[['close']].rename(columns={'close': symbol})
        else:
            logger.warning(f"No price column found for {symbol}")
            return pd.DataFrame()
        
        return df
    
    def get_multiple_price_history(self, symbols: List[str], start_date: str, 
                                  end_date: str) -> pd.DataFrame:
        """
        Get historical prices for multiple symbols.
        
        Args:
            symbols: List of symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with date index and one column per symbol
        """
        price_dfs = []
        for sym in symbols:
            df = self.get_price_history(sym, start_date, end_date)
            if not df.empty:
                price_dfs.append(df[sym])
        
        if not price_dfs:
            return pd.DataFrame()
        
        price_df = pd.concat(price_dfs, axis=1)
        return price_df


class HoldingsLoader:
    """
    Loads ETF holdings (point-in-time constituents) for the given ETF symbol.
    
    Args:
        fmp_client: FMPClient instance
        etf_symbol: ETF symbol to load holdings for
    """
    
    def __init__(self, fmp_client: FMPClient, etf_symbol: str):
        self.client = fmp_client
        self.etf_symbol = etf_symbol
    
    def get_holdings_by_date(self, date: Optional[str] = None) -> List[str]:
        """
        Get list of holding symbols for a specific date (or current if date is None).
        
        Args:
            date: Optional date string (YYYY-MM-DD). If None, gets current holdings.
            
        Returns:
            List of symbol strings
        """
        holdings_data = self.client.get_etf_holdings(self.etf_symbol, date)
        symbols = []
        
        for item in holdings_data:
            # FMP returns holdings with 'asset' field for the holding symbol
            # 'symbol' field is the ETF symbol itself
            sym = item.get('asset') or item.get('symbol') or item.get('ticker') or item.get('assetSymbol')
            if sym and sym != self.etf_symbol:  # Exclude the ETF symbol itself
                symbols.append(sym)
        
        return symbols


class FundamentalDataLoader:
    """
    Loads fundamental data and computes factor metrics for a list of stocks.
    
    Args:
        fmp_client: FMPClient instance
    """
    
    def __init__(self, fmp_client: FMPClient):
        self.client = fmp_client
    
    def get_fundamental_factors(self, symbols: List[str]) -> pd.DataFrame:
        """
        Get fundamental factors for a list of symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            DataFrame with fundamental metrics indexed by symbol
        """
        data_records = []
        
        for sym in symbols:
            try:
                income = self.client.get_income_statement(sym, period='annual', limit=1)
                cashflow = self.client.get_cash_flow_statement(sym, period='annual', limit=1)
                ev_data = self.client.get_enterprise_values(sym)
                mcap_data = self.client.get_market_cap(sym)
                
                rd = sales = capex = marketing = sgna = None
                
                if income:
                    inc = income[0]
                    rd = inc.get('researchAndDevelopment') or inc.get('RD') or None
                    sales = inc.get('revenue') or inc.get('salesRevenueNet') or None
                    sgna = inc.get('sellingGeneralAndAdministrative') or inc.get('SGA') or None
                    marketing = inc.get('marketingExpense') or inc.get('advertisingAndPromotionExpense') or None
                
                if cashflow:
                    cf = cashflow[0]
                    capex = cf.get('capitalExpenditure') or cf.get('capitalExpenditures') or None
                
                ev_val = ev_data.get('enterpriseValue') if ev_data else None
                mcap_val = mcap_data.get('marketCap') if mcap_data else None
                
                data_records.append({
                    'symbol': sym,
                    'R&D': rd,
                    'Sales': sales,
                    'MarketCap': mcap_val,
                    'EnterpriseValue': ev_val,
                    'CapEx': capex,
                    'Marketing': marketing,
                    'SG&A': sgna
                })
            except Exception as e:
                logger.warning(f"Error loading fundamentals for {sym}: {e}")
                continue
        
        if not data_records:
            return pd.DataFrame()
        
        df = pd.DataFrame(data_records).set_index('symbol')
        
        # Calculate derived metrics
        if 'R&D' in df.columns and 'Sales' in df.columns:
            df['R&D_to_Sales'] = df['R&D'] / df['Sales'].replace(0, np.nan)
        
        if 'EnterpriseValue' in df.columns and 'MarketCap' in df.columns:
            df['EV_to_MarketCap'] = df['EnterpriseValue'] / df['MarketCap'].replace(0, np.nan)
        
        return df


class PriceLoader:
    """
    Loads historical prices and calculates returns.
    
    Args:
        fmp_client: FMPClient instance
    """
    
    def __init__(self, fmp_client: FMPClient):
        self.client = fmp_client
    
    def get_adjusted_close(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get adjusted close prices for multiple symbols.
        
        Args:
            symbols: List of symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with date index and one column per symbol
        """
        price_df = self.client.get_multiple_price_history(symbols, start_date, end_date)
        price_df = price_df.sort_index().ffill().dropna(axis=1, how='all')
        return price_df
    
    def calculate_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate returns from price DataFrame.
        
        Args:
            price_df: DataFrame with prices
            
        Returns:
            DataFrame with returns
        """
        returns = price_df.pct_change().dropna(how='all')
        return returns


class YahooPriceLoader:
    """
    Loads historical prices from Yahoo Finance using yfinance (same as NAV/performance module).
    Uses auto_adjust=True to get total return (adjusted close includes dividends).
    
    Args:
        None (uses yfinance directly, no API key needed)
    """
    
    def __init__(self):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library is required for YahooPriceLoader. Install with: pip install yfinance")
    
    def get_adjusted_close(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get adjusted close prices for multiple symbols from Yahoo Finance.
        Uses auto_adjust=True to get total return (adjusted close includes dividends).
        
        Args:
            symbols: List of symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with date index and one column per symbol
        """
        if not YFINANCE_AVAILABLE:
            logger.error("yfinance not available")
            return pd.DataFrame()
        
        price_dfs = []
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                # Use auto_adjust=True to get total return (adjusted close includes dividends)
                # This matches the approach used in the performance module
                hist = ticker.history(
                    start=start_dt,
                    end=end_dt + pd.Timedelta(days=1),  # Add 1 day to include end_date
                    auto_adjust=True
                )
                
                if not hist.empty and 'Close' in hist.columns:
                    # Use adjusted close (total return)
                    price_series = hist['Close'].copy()
                    price_series.name = sym
                    price_dfs.append(price_series)
                else:
                    logger.warning(f"No price data from Yahoo for {sym} from {start_date} to {end_date}")
            except Exception as e:
                logger.warning(f"Error fetching Yahoo price data for {sym}: {e}")
                continue
        
        if not price_dfs:
            return pd.DataFrame()
        
        # Combine all series into a DataFrame
        price_df = pd.concat(price_dfs, axis=1)
        price_df = price_df.sort_index().ffill().dropna(axis=1, how='all')
        
        return price_df
    
    def get_multiple_price_history(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Alias for get_adjusted_close to match FMPClient interface.
        
        Args:
            symbols: List of symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            DataFrame with date index and one column per symbol
        """
        return self.get_adjusted_close(symbols, start_date, end_date)
    
    def calculate_returns(self, price_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate returns from price DataFrame.
        
        Args:
            price_df: DataFrame with prices
            
        Returns:
            DataFrame with returns
        """
        returns = price_df.pct_change().dropna(how='all')
        return returns


class Backtester:
    """
    Backtesting engine for factor-based monthly rebalanced portfolios.
    
    Args:
        fmp_client: FMPClient instance
        holdings_loader: HoldingsLoader instance
        price_loader: PriceLoader or YahooPriceLoader instance
        factor_loader: FundamentalDataLoader instance
        start_date: Start date for backtest (YYYY-MM-DD)
        end_date: End date for backtest (YYYY-MM-DD)
        top_n: Optional number of top stocks to select (by factor)
        storage_path: Path to store backtest results
    """
    
    def __init__(self, fmp_client: FMPClient, holdings_loader: HoldingsLoader,
                 price_loader: Any, factor_loader: FundamentalDataLoader,
                 start_date: str, end_date: str, top_n: Optional[int] = None,
                 storage_path: str = "./data/research"):
        self.client = fmp_client
        self.holdings_loader = holdings_loader
        self.price_loader = price_loader
        self.factor_loader = factor_loader
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.top_n = top_n
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Generate rebalance dates (month-end)
        self.rebalance_dates = list(pd.date_range(self.start_date, self.end_date, freq='M'))
        
        # Results storage
        self.portfolio_returns = pd.Series(dtype=float)
        self.portfolio_weights: Dict[str, Dict[str, float]] = {}
        self.turnover = pd.Series(dtype=float)
        self.factor_stats = pd.DataFrame()
    
    def run_backtest(self):
        """Run the backtest across all rebalance dates."""
        logger.info(f"Starting backtest from {self.start_date.date()} to {self.end_date.date()}")
        logger.info(f"Rebalancing on {len(self.rebalance_dates)} dates")
        
        prev_weights: Dict[str, float] = {}
        factor_stats_records = []
        
        for i, date in enumerate(self.rebalance_dates):
            date_str = date.strftime('%Y-%m-%d')
            logger.info(f"Processing rebalance {i+1}/{len(self.rebalance_dates)}: {date_str}")
            
            # Get holdings for this date
            holdings = self.holdings_loader.get_holdings_by_date(date_str)
            if not holdings:
                logger.warning(f"No holdings found for {date_str}")
                continue
            
            # Get fundamental factors
            factors = self.factor_loader.get_fundamental_factors(holdings)
            if factors.empty:
                logger.warning(f"No factor data for {date_str}")
                continue
            
            # Filter by factor and select top N
            if 'R&D_to_Sales' in factors.columns:
                factors = factors.sort_values('R&D_to_Sales', ascending=False, na_last=True)
                if self.top_n:
                    factors = factors.head(self.top_n)
            else:
                logger.warning(f"No R&D_to_Sales factor available for {date_str}")
                continue
            
            symbols = factors.index.tolist()
            n = len(symbols)
            
            if n == 0:
                logger.warning(f"No symbols selected for {date_str}")
                continue
            
            # Equal weight portfolio
            weights = {sym: 1.0 / n for sym in symbols}
            self.portfolio_weights[date_str] = weights
            
            # Calculate turnover
            if prev_weights:
                weight_changes = 0.0
                all_syms = set(prev_weights.keys()) | set(weights.keys())
                for sym in all_syms:
                    w_prev = prev_weights.get(sym, 0.0)
                    w_new = weights.get(sym, 0.0)
                    weight_changes += abs(w_new - w_prev)
                self.turnover[date_str] = weight_changes / 2.0
            else:
                self.turnover[date_str] = 1.0
            
            prev_weights = weights
            
            # Store factor statistics
            selected_df = factors.loc[symbols]
            mean_stats = selected_df.mean().to_dict()
            mean_stats['date'] = date_str
            mean_stats['num_holdings'] = n
            factor_stats_records.append(mean_stats)
        
        if factor_stats_records:
            self.factor_stats = pd.DataFrame(factor_stats_records).set_index('date')
        
        # Compute portfolio returns
        self._compute_portfolio_returns()
        logger.info("Backtest completed")
    
    def _compute_portfolio_returns(self):
        """Compute portfolio returns for each holding period."""
        returns_list = []
        
        for date_str, weights in self.portfolio_weights.items():
            entry_date = pd.to_datetime(date_str)
            next_month_date = entry_date + pd.DateOffset(months=1)
            
            if next_month_date > self.end_date:
                continue
            
            symbols = list(weights.keys())
            end_date_str = next_month_date.strftime('%Y-%m-%d')
            
            price_df = self.price_loader.get_adjusted_close(symbols, date_str, end_date_str)
            
            if price_df.empty:
                logger.warning(f"No price data for {date_str} to {end_date_str}")
                continue
            
            if len(price_df) < 2:
                logger.warning(f"Insufficient price data for {date_str}")
                continue
            
            entry_price = price_df.iloc[0]
            exit_price = price_df.iloc[-1]
            
            # Calculate asset returns
            asset_returns = {}
            for sym in symbols:
                if sym in entry_price.index and sym in exit_price.index:
                    entry_val = entry_price[sym]
                    exit_val = exit_price[sym]
                    if pd.notna(entry_val) and pd.notna(exit_val) and entry_val > 0:
                        asset_returns[sym] = (exit_val / entry_val) - 1.0
                    else:
                        asset_returns[sym] = 0.0
                else:
                    asset_returns[sym] = 0.0
            
            # Calculate portfolio return
            portfolio_return = sum(asset_returns.get(sym, 0.0) * wt for sym, wt in weights.items())
            returns_list.append((entry_date, portfolio_return))
        
        if returns_list:
            dates, vals = zip(*returns_list)
            self.portfolio_returns = pd.Series(data=vals, index=pd.to_datetime(dates))
            self.portfolio_returns.name = 'portfolio_return'
    
    def evaluate_performance(self) -> Dict[str, float]:
        """
        Evaluate backtest performance metrics.
        
        Returns:
            Dictionary with performance metrics:
            - Total Return: Cumulative return over period
            - CAGR: Compound Annual Growth Rate
            - Volatility: Annualized volatility
            - Sharpe: Sharpe ratio (assuming risk-free rate = 0)
            - Average Turnover: Average monthly turnover
        """
        if self.portfolio_returns.empty:
            logger.warning("No portfolio returns to evaluate")
            return {}
        
        df = self.portfolio_returns.to_frame('returns')
        df['cum_return'] = (1 + df['returns']).cumprod()
        
        total_return = df['cum_return'].iloc[-1] - 1.0
        num_periods = len(df)
        
        if num_periods == 0:
            return {}
        
        # CAGR (annualized)
        cagr = (df['cum_return'].iloc[-1] ** (12.0 / num_periods) - 1.0) if num_periods > 0 else np.nan
        
        # Annualized volatility
        vol = df['returns'].std() * np.sqrt(12) if num_periods > 1 else np.nan
        
        # Sharpe ratio (assuming risk-free rate = 0)
        sharpe = (df['returns'].mean() * 12.0) / vol if vol and vol != 0 and not np.isnan(vol) else np.nan
        
        # Average turnover
        avg_turnover = self.turnover.mean() if not self.turnover.empty else np.nan
        
        return {
            'Total Return': total_return,
            'CAGR': cagr,
            'Volatility': vol,
            'Sharpe': sharpe,
            'Average Turnover': avg_turnover
        }
    
    def export_results(self, filename: Optional[str] = None):
        """
        Export backtest results to CSV files.
        
        Args:
            filename: Base filename (without extension). Default: backtest_results_YYYYMMDD
        """
        if filename is None:
            filename = f"backtest_results_{datetime.now().strftime('%Y%m%d')}"
        
        # Export returns and turnover
        results_df = pd.DataFrame({
            'Return': self.portfolio_returns,
            'Turnover': self.turnover.reindex(self.portfolio_returns.index)
        })
        results_path = self.storage_path / f"{filename}.csv"
        results_df.to_csv(results_path)
        logger.info(f"Results exported to {results_path}")
        
        # Export factor stats if available
        if not self.factor_stats.empty:
            factor_path = self.storage_path / f"{filename}_factor_stats.csv"
            self.factor_stats.to_csv(factor_path)
            logger.info(f"Factor stats exported to {factor_path}")
        
        # Export query log
        if self.client.query_log:
            log_path = self.storage_path / f"{filename}_query_log.csv"
            pd.DataFrame(self.client.query_log).to_csv(log_path, index=False)
            logger.info(f"Query log exported to {log_path}")


def main():
    """Example usage of the backtesting module."""
    config = {
        'FMP_API_KEY': os.getenv('FMP_API_KEY', 'YOUR_API_KEY'),
        'start_date': '2015-01-01',
        'end_date': '2020-12-31',
        'etf_symbol': 'IWB',
        'top_n': 50,
        'use_yahoo': False  # Set to True to use Yahoo Finance instead of FMP for prices
    }
    
    # Initialize FMP client (needed for holdings and fundamentals)
    if config['FMP_API_KEY'] == 'YOUR_API_KEY':
        logger.warning("Please set FMP_API_KEY environment variable or update config")
        return
    
    fmp = FMPClient(api_key=config['FMP_API_KEY'])
    holdings_loader = HoldingsLoader(fmp, etf_symbol=config['etf_symbol'])
    factor_loader = FundamentalDataLoader(fmp)
    
    # Choose price loader: FMP or Yahoo Finance
    if config.get('use_yahoo', False) and YFINANCE_AVAILABLE:
        logger.info("Using Yahoo Finance for price data (same as NAV/performance module)")
        price_loader = YahooPriceLoader()
    else:
        logger.info("Using FMP for price data")
        price_loader = PriceLoader(fmp)
    
    backtester = Backtester(
        fmp, holdings_loader, price_loader, factor_loader,
        start_date=config['start_date'],
        end_date=config['end_date'],
        top_n=config['top_n']
    )
    
    backtester.run_backtest()
    perf = backtester.evaluate_performance()
    
    logger.info(f"Performance: {perf}")
    backtester.export_results()


if __name__ == "__main__":
    main()

