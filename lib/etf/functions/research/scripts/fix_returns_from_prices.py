"""
Fix Returns by Recalculating from Adjusted Prices
Ensures we're using the correct adjusted price series and handling splits properly.
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

from lib.etf.functions.research.core.backtesting import YahooPriceLoader, FMPClient

logger = logging.getLogger(__name__)


class ReturnsFixer:
    """
    Fix returns by recalculating from adjusted prices and handling splits correctly.
    """
    
    def __init__(self, returns_df: pd.DataFrame, fmp_client=None):
        """
        Initialize the returns fixer.
        
        Args:
            returns_df: DataFrame with current returns (may have errors)
            fmp_client: Optional FMPClient for split calendar
        """
        self.returns_df = returns_df.copy()
        self.fmp_client = fmp_client
        self.price_loader = YahooPriceLoader()
        self.corrections_log = []
        self.split_cache = {}
        
    def get_ticker_splits(self, ticker: str, date: pd.Timestamp, 
                         window_days: int = 5) -> List[Dict]:
        """Get stock splits for a ticker around a given date."""
        if not self.fmp_client:
            return []
        
        cache_key = f"{ticker}_{date.date()}"
        if cache_key in self.split_cache:
            return self.split_cache[cache_key]
        
        try:
            start_date = (date - timedelta(days=window_days)).strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=window_days)).strftime('%Y-%m-%d')
            
            splits = self.fmp_client.get_stock_splits(ticker, start_date, end_date)
            self.split_cache[cache_key] = splits
            return splits
        except Exception as e:
            logger.debug(f"Error fetching splits for {ticker} on {date.date()}: {e}")
            return []
    
    def recalculate_ticker_return(self, ticker: str, date: pd.Timestamp) -> Optional[float]:
        """
        Recalculate return for a ticker on a specific date using fresh Yahoo data.
        
        Args:
            ticker: Stock ticker
            date: Date to calculate return for
            
        Returns:
            Daily return or None if unavailable
        """
        try:
            # Get data for a window around the date
            start = date - timedelta(days=10)
            end = date + timedelta(days=10)
            
            # Use YahooPriceLoader's method
            price_df = self.price_loader.get_adjusted_close(
                symbols=[ticker],
                start_date=start.strftime('%Y-%m-%d'),
                end_date=end.strftime('%Y-%m-%d')
            )
            
            if price_df.empty or ticker not in price_df.columns:
                return None
            
            # Find the date in the price data
            if date not in price_df.index:
                # Find closest date
                date_idx = price_df.index.get_indexer([date], method='nearest')[0]
                if date_idx == -1:
                    return None
                actual_date = price_df.index[date_idx]
            else:
                actual_date = date
            
            # Get previous trading day
            date_pos = price_df.index.get_loc(actual_date)
            if date_pos == 0:
                return None
            
            prev_date = price_df.index[date_pos - 1]
            prev_price = price_df.loc[prev_date, ticker]
            curr_price = price_df.loc[actual_date, ticker]
            
            if pd.isna(prev_price) or pd.isna(curr_price) or prev_price <= 0:
                return None
            
            return (curr_price / prev_price) - 1.0
            
        except Exception as e:
            logger.debug(f"Error recalculating return for {ticker} on {date.date()}: {e}")
            return None
    
    def fix_extreme_returns(self, threshold: float = 0.15) -> pd.DataFrame:
        """
        Fix extreme returns by recalculating from adjusted prices.
        
        Args:
            threshold: Returns above this threshold will be recalculated
            
        Returns:
            Corrected returns DataFrame
        """
        logger.info("="*70)
        logger.info("Fixing Extreme Returns by Recalculating from Adjusted Prices")
        logger.info("="*70)
        
        corrections = []
        extreme_count = 0
        
        # Find all extreme returns
        for date in self.returns_df.index:
            for ticker in self.returns_df.columns:
                if pd.isna(self.returns_df.loc[date, ticker]):
                    continue
                
                ret = self.returns_df.loc[date, ticker]
                abs_ret = abs(ret)
                
                if abs_ret > threshold:
                    extreme_count += 1
                    
                    # Check for splits
                    splits = self.get_ticker_splits(ticker, date)
                    
                    # Recalculate return from adjusted prices
                    recalc_ret = self.recalculate_ticker_return(ticker, date)
                    
                    if recalc_ret is not None:
                        if abs(recalc_ret - ret) > 0.01:  # Significant difference
                            logger.info(f"  {date.date()} {ticker}: {ret:.2%} -> {recalc_ret:.2%} "
                                      f"(split: {len(splits) > 0})")
                            
                            self.returns_df.loc[date, ticker] = recalc_ret
                            
                            corrections.append({
                                'date': date,
                                'ticker': ticker,
                                'old_return': ret,
                                'new_return': recalc_ret,
                                'split_detected': len(splits) > 0
                            })
                        # Rate limiting
                        time.sleep(0.05)
                    elif abs_ret > 0.50:  # Very extreme return with no recalculation possible
                        logger.warning(f"  {date.date()} {ticker}: {ret:.2%} - setting to 0 (no verification)")
                        self.returns_df.loc[date, ticker] = 0.0
                        corrections.append({
                            'date': date,
                            'ticker': ticker,
                            'old_return': ret,
                            'new_return': 0.0,
                            'split_detected': len(splits) > 0,
                            'reason': 'Extreme return, no recalculation possible'
                        })
        
        logger.info(f"\nFixed {len(corrections)} extreme returns (found {extreme_count} total >{threshold:.0%})")
        self.corrections_log = corrections
        
        return self.returns_df
    
    def fix_returns_for_dates(self, dates: List[pd.Timestamp], 
                             threshold: float = 0.01) -> pd.DataFrame:
        """
        Fix returns for specific dates (e.g., days with >1% portfolio return).
        
        Args:
            dates: List of dates to fix
            threshold: Individual ticker return threshold to check
            
        Returns:
            Corrected returns DataFrame
        """
        logger.info(f"Fixing returns for {len(dates)} specific dates (threshold: {threshold:.0%})")
        
        corrections = []
        
        for date in dates:
            if date not in self.returns_df.index:
                continue
            
            # Get all tickers with returns on this date
            day_returns = self.returns_df.loc[date].dropna()
            
            # Check tickers with >threshold return
            tickers_to_check = day_returns[day_returns.abs() > threshold].index.tolist()
            
            if not tickers_to_check:
                continue
            
            logger.info(f"  {date.date()}: Checking {len(tickers_to_check)} tickers with >{threshold:.0%} return")
            
            for ticker in tickers_to_check:
                ret = day_returns[ticker]
                
                # Recalculate from adjusted prices
                recalc_ret = self.recalculate_ticker_return(ticker, date)
                
                if recalc_ret is not None:
                    if abs(recalc_ret - ret) > 0.005:  # 0.5% difference
                        logger.info(f"    {ticker}: {ret:.2%} -> {recalc_ret:.2%}")
                        self.returns_df.loc[date, ticker] = recalc_ret
                        corrections.append({
                            'date': date,
                            'ticker': ticker,
                            'old_return': ret,
                            'new_return': recalc_ret
                        })
                # Rate limiting
                time.sleep(0.05)
        
        logger.info(f"Fixed {len(corrections)} returns for specified dates")
        self.corrections_log.extend(corrections)
        
        return self.returns_df

