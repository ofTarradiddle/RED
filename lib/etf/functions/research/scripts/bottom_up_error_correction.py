"""
Bottom-Up Error Correction System
Investigates and corrects individual ticker returns to fix portfolio-level errors.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import time

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class BottomUpErrorCorrector:
    """
    Investigates and corrects errors in individual ticker returns to fix portfolio-level issues.
    """
    
    def __init__(self, returns_df: pd.DataFrame, constituents_by_date: Dict[str, List[str]], 
                 fmp_client=None, max_investigations: int = 50):
        """
        Initialize the error corrector.
        
        Args:
            returns_df: DataFrame with ticker returns (columns = tickers, index = dates)
            constituents_by_date: Dictionary mapping dates to ticker lists
            fmp_client: Optional FMPClient for split calendar
            max_investigations: Maximum number of days to investigate
        """
        self.returns_df = returns_df.copy()
        self.constituents_by_date = constituents_by_date
        self.fmp_client = fmp_client
        self.max_investigations = max_investigations
        self.corrections_log = []
        self.split_cache = {}  # Cache split data by ticker
        
    def identify_problematic_days(self, portfolio_returns: pd.Series, 
                                   benchmark_returns: pd.Series) -> pd.Series:
        """
        Identify days with largest deviations from benchmark AND days with >1% portfolio returns.
        
        User requirement: investigate any daily return >1%
        
        Returns:
            Series of dates sorted by priority (largest deviations + >1% returns)
        """
        # Align dates - ensure both are timezone-naive
        benchmark_returns = benchmark_returns.copy()
        if isinstance(benchmark_returns.index, pd.DatetimeIndex) and benchmark_returns.index.tz is not None:
            benchmark_returns.index = benchmark_returns.index.tz_localize(None)
        
        portfolio_returns = portfolio_returns.copy()
        if isinstance(portfolio_returns.index, pd.DatetimeIndex) and portfolio_returns.index.tz is not None:
            portfolio_returns.index = portfolio_returns.index.tz_localize(None)
        
        common_dates = portfolio_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) == 0:
            # No benchmark overlap - check for >1% returns in portfolio
            high_returns = portfolio_returns[portfolio_returns.abs() > 0.01]
            logger.info(f"No benchmark overlap. Found {len(high_returns)} days with >1% portfolio return")
            return high_returns.abs().nlargest(self.max_investigations)
        
        portfolio_aligned = portfolio_returns.loc[common_dates]
        benchmark_aligned = benchmark_returns.loc[common_dates]
        
        # Strategy 1: Days with >1% portfolio return (user requirement)
        high_return_days = portfolio_aligned[portfolio_aligned.abs() > 0.01]
        
        # Strategy 2: Days with large deviations from benchmark
        deviations = (portfolio_aligned - benchmark_aligned).abs()
        large_deviation_days = deviations.nlargest(self.max_investigations)
        
        # Combine both sets
        all_problematic = set(high_return_days.index) | set(large_deviation_days.index)
        
        # Create priority scores: deviation + high return flag
        priority_scores = {}
        for date in all_problematic:
            port_ret = portfolio_aligned.loc[date]
            bench_ret = benchmark_aligned.loc[date]
            dev = abs(port_ret - bench_ret)
            
            # Priority = deviation + bonus for >1% return
            priority = dev
            if abs(port_ret) > 0.01:
                priority += 0.10  # Bonus for >1% return
            
            priority_scores[date] = priority
        
        # Sort by priority
        problematic_series = pd.Series(priority_scores).nlargest(self.max_investigations)
        
        logger.info(f"Identified {len(problematic_series)} problematic days for investigation")
        logger.info(f"  - {len(high_return_days)} days with >1% portfolio return")
        logger.info(f"  - {len(large_deviation_days)} days with large deviations")
        logger.info(f"Top 10 by priority:")
        for date in problematic_series.head(10).index:
            port_ret = portfolio_aligned.loc[date]
            bench_ret = benchmark_aligned.loc[date]
            dev = abs(port_ret - bench_ret)
            logger.info(f"  {date.date()}: Portfolio {port_ret:.2%} vs Benchmark {bench_ret:.2%} (diff: {dev:.2%})")
        
        return problematic_series
    
    def get_holdings_for_date(self, date: pd.Timestamp) -> List[str]:
        """Get tickers in portfolio on a given date."""
        # Find the most recent rebalance date before or on this date
        date_str = date.strftime('%Y-%m-%d')
        
        # Try to find exact match or most recent
        rebalance_dates = sorted([pd.to_datetime(d) for d in self.constituents_by_date.keys()])
        
        for rebalance_date in reversed(rebalance_dates):
            if rebalance_date <= date:
                rebalance_key = rebalance_date.strftime('%Y-%m-%d')
                return self.constituents_by_date.get(rebalance_key, [])
        
        return []
    
    def get_ticker_splits(self, ticker: str, date: pd.Timestamp, 
                         window_days: int = 5) -> List[Dict]:
        """
        Get stock splits for a ticker around a given date.
        
        Args:
            ticker: Stock ticker
            date: Date to check around
            window_days: Days before/after to check
            
        Returns:
            List of split records
        """
        if not self.fmp_client:
            return []
        
        # Check cache first
        cache_key = f"{ticker}_{date.date()}"
        if cache_key in self.split_cache:
            return self.split_cache[cache_key]
        
        try:
            start_date = (date - timedelta(days=window_days)).strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=window_days)).strftime('%Y-%m-%d')
            
            splits = self.fmp_client.get_stock_splits(ticker, start_date, end_date)
            
            # Cache result
            self.split_cache[cache_key] = splits
            
            return splits
        except Exception as e:
            logger.debug(f"Error fetching splits for {ticker} on {date.date()}: {e}")
            return []
    
    def verify_ticker_return_yahoo(self, ticker: str, date: pd.Timestamp) -> Optional[float]:
        """
        Verify ticker return using Yahoo Finance.
        
        Args:
            ticker: Stock ticker
            date: Date to check
            
        Returns:
            Daily return from Yahoo Finance, or None if unavailable
        """
        if not YFINANCE_AVAILABLE:
            return None
        
        try:
            # Get data for a window around the date
            start = date - timedelta(days=5)
            end = date + timedelta(days=5)
            
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start=start, end=end)
            
            if hist.empty or date not in hist.index:
                return None
            
            # Find the date in the history (may be timezone-aware)
            hist_dates = hist.index
            if hist_dates.tz is not None:
                hist_dates = hist_dates.tz_localize(None)
            
            # Find closest date
            date_idx = hist_dates.get_indexer([date], method='nearest')[0]
            if date_idx == -1:
                return None
            
            actual_date = hist_dates[date_idx]
            
            # Get previous day
            if date_idx > 0:
                prev_date = hist_dates[date_idx - 1]
                prev_close = hist.loc[prev_date, 'Close']
                curr_close = hist.loc[actual_date, 'Close']
                
                return (curr_close / prev_close) - 1.0
            
            return None
        except Exception as e:
            logger.debug(f"Error verifying {ticker} return on {date.date()}: {e}")
            return None
    
    def investigate_day(self, date: pd.Timestamp, portfolio_return: float, 
                       benchmark_return: float, deviation: float) -> Dict:
        """
        Investigate a single day to find and correct problematic ticker returns.
        
        Returns:
            Dictionary with investigation results and corrections made
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Investigating {date.date()}: Portfolio {portfolio_return:.2%} vs Benchmark {benchmark_return:.2%} (diff: {deviation:.2%})")
        logger.info(f"{'='*70}")
        
        # Get holdings for this date
        holdings = self.get_holdings_for_date(date)
        if not holdings:
            logger.warning(f"  No holdings found for {date.date()}")
            return {'date': date, 'corrections': [], 'notes': 'No holdings found'}
        
        # Get returns for holdings on this day
        if date not in self.returns_df.index:
            logger.warning(f"  Date {date.date()} not in returns dataframe")
            return {'date': date, 'corrections': [], 'notes': 'Date not in returns'}
        
        # Filter holdings to only those present in returns dataframe
        # Handle both list and single value cases
        available_tickers = []
        for ticker in holdings:
            if ticker in self.returns_df.columns:
                available_tickers.append(ticker)
        
        if len(available_tickers) < len(holdings):
            logger.debug(f"  {len(holdings) - len(available_tickers)} tickers not in returns dataframe (out of {len(holdings)} total)")
        
        if not available_tickers:
            logger.warning(f"  No available tickers for {date.date()} (had {len(holdings)} holdings)")
            return {'date': date, 'corrections': [], 'notes': f'No available tickers (had {len(holdings)} holdings)'}
        
        # Get returns - handle both single column and multiple columns
        try:
            if len(available_tickers) == 1:
                day_returns = pd.Series({available_tickers[0]: self.returns_df.loc[date, available_tickers[0]]})
            else:
                day_returns = self.returns_df.loc[date, available_tickers]
            
            # Convert to Series if needed and drop NaN
            if isinstance(day_returns, pd.Series):
                day_returns = day_returns.dropna()
            else:
                day_returns = day_returns.dropna()
        except KeyError as e:
            logger.warning(f"  Error accessing returns for {date.date()}: {e}")
            return {'date': date, 'corrections': [], 'notes': f'Error accessing returns: {e}'}
        
        logger.info(f"  Holdings: {len(holdings)}, Valid returns: {len(day_returns)}")
        
        corrections = []
        notes = []
        
        # Check ALL returns >1% - user requirement: investigate any daily return >1%
        investigation_threshold = 0.01  # 1% daily return threshold
        returns_to_check = day_returns[day_returns.abs() > investigation_threshold]
        
        if len(returns_to_check) > 0:
            logger.info(f"  Found {len(returns_to_check)} tickers with >1% daily return (investigating all):")
            
            for ticker, ret in returns_to_check.items():
                abs_ret = abs(ret)
                logger.info(f"    {ticker}: {ret:.2%}")
                
                # Check for splits first
                splits = self.get_ticker_splits(ticker, date)
                split_detected = len(splits) > 0
                if split_detected:
                    logger.info(f"      ✓ Split detected: {splits}")
                    notes.append(f"{ticker}: Split on {date.date()}")
                
                # Always verify with Yahoo Finance for returns >1%
                yahoo_ret = self.verify_ticker_return_yahoo(ticker, date)
                
                if yahoo_ret is not None:
                    logger.info(f"      Yahoo return: {yahoo_ret:.2%} vs Current: {ret:.2%}")
                    
                    # If difference is significant OR if current return is extreme (>15%), use Yahoo
                    if abs(yahoo_ret - ret) > 0.005 or abs_ret > 0.15:  # 0.5% difference or >15% return
                        logger.info(f"      ✓ Correcting {ticker} return from {ret:.2%} to {yahoo_ret:.2%}")
                        
                        # Correct in returns dataframe
                        self.returns_df.loc[date, ticker] = yahoo_ret
                        
                        corrections.append({
                            'ticker': ticker,
                            'old_return': ret,
                            'new_return': yahoo_ret,
                            'reason': 'Yahoo Finance verification (>1% return)',
                            'split_detected': split_detected
                        })
                    else:
                        logger.debug(f"      Yahoo return matches current ({ret:.2%} vs {yahoo_ret:.2%})")
                else:
                    # No Yahoo data available
                    if abs_ret > 0.15:  # >15% return with no verification - definitely wrong
                        logger.warning(f"      No Yahoo data for {ticker} with {ret:.2%} return - setting to 0")
                        self.returns_df.loc[date, ticker] = 0.0
                        
                        corrections.append({
                            'ticker': ticker,
                            'old_return': ret,
                            'new_return': 0.0,
                            'reason': 'Extreme return (>15%) with no verification data',
                            'split_detected': split_detected
                        })
                    elif abs_ret > 0.05:  # 5-15% return - suspicious but not extreme
                        # Try to estimate: if it's a split pattern, set to 0
                        if split_detected:
                            logger.warning(f"      Split detected but no Yahoo data - setting to 0")
                            self.returns_df.loc[date, ticker] = 0.0
                            corrections.append({
                                'ticker': ticker,
                                'old_return': ret,
                                'new_return': 0.0,
                                'reason': 'Split detected but no Yahoo verification',
                                'split_detected': True
                            })
                        else:
                            logger.warning(f"      No Yahoo data for {ticker} with {ret:.2%} - flagging but keeping")
                            notes.append(f"{ticker}: {ret:.2%} return, no Yahoo data available")
                    # For 1-5% returns without Yahoo data, keep as-is (might be legitimate)
        
        
        result = {
            'date': date,
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'deviation': deviation,
            'corrections': corrections,
            'notes': notes
        }
        
        if corrections:
            logger.info(f"  ✓ Made {len(corrections)} corrections")
        else:
            logger.info(f"  No corrections needed")
        
        return result
    
    def correct_errors(self, portfolio_returns: pd.Series, 
                      benchmark_returns: pd.Series) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Main correction function: identifies problematic days and corrects them.
        
        Returns:
            Tuple of (corrected returns dataframe, corrections log)
        """
        logger.info("="*70)
        logger.info("Bottom-Up Error Correction System")
        logger.info("="*70)
        logger.info("Investigating individual ticker returns to fix portfolio-level errors")
        logger.info("")
        
        # Identify problematic days
        problematic_days = self.identify_problematic_days(portfolio_returns, benchmark_returns)
        
        if len(problematic_days) == 0:
            logger.info("No problematic days identified")
            return self.returns_df, []
        
        # Ensure benchmark is timezone-naive for lookups
        benchmark_returns = benchmark_returns.copy()
        if isinstance(benchmark_returns.index, pd.DatetimeIndex) and benchmark_returns.index.tz is not None:
            benchmark_returns.index = benchmark_returns.index.tz_localize(None)
        
        portfolio_returns = portfolio_returns.copy()
        if isinstance(portfolio_returns.index, pd.DatetimeIndex) and portfolio_returns.index.tz is not None:
            portfolio_returns.index = portfolio_returns.index.tz_localize(None)
        
        # Investigate each problematic day
        all_corrections = []
        for date, deviation in problematic_days.items():
            portfolio_ret = portfolio_returns.loc[date]
            benchmark_ret = benchmark_returns.loc[date]
            
            result = self.investigate_day(date, portfolio_ret, benchmark_ret, deviation)
            all_corrections.append(result)
            
            # Rate limiting
            time.sleep(0.1)
        
        self.corrections_log = all_corrections
        
        # Summary
        total_corrections = sum(len(r['corrections']) for r in all_corrections)
        logger.info(f"\n{'='*70}")
        logger.info(f"Correction Summary:")
        logger.info(f"  Days investigated: {len(problematic_days)}")
        logger.info(f"  Total ticker corrections: {total_corrections}")
        logger.info(f"  Days with corrections: {sum(1 for r in all_corrections if r['corrections'])}")
        
        return self.returns_df, all_corrections

