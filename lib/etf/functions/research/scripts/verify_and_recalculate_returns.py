"""
Verify and Recalculate Returns from Adjusted Prices
Checks if returns were calculated correctly and recalculates if needed.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import time

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.backtesting import YahooPriceLoader

logger = logging.getLogger(__name__)


def verify_return_calculation(ticker: str, date: pd.Timestamp, 
                              stored_return: float, price_loader: YahooPriceLoader,
                              tolerance: float = 0.001) -> Tuple[bool, float, str]:
    """
    Verify if a stored return matches what we get from recalculating adjusted prices.
    
    Returns:
        (is_correct, recalculated_return, error_message)
    """
    try:
        # Get prices around the date
        start = date - pd.Timedelta(days=10)
        end = date + pd.Timedelta(days=10)
        
        price_df = price_loader.get_adjusted_close(
            symbols=[ticker],
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d')
        )
        
        if price_df.empty or ticker not in price_df.columns:
            return False, np.nan, "No price data available"
        
        # Find the date
        if date not in price_df.index:
            # Find closest
            date_idx = price_df.index.get_indexer([date], method='nearest')[0]
            if date_idx == -1:
                return False, np.nan, "Date not found in price data"
            actual_date = price_df.index[date_idx]
        else:
            actual_date = date
        
        # Get previous trading day
        date_pos = price_df.index.get_loc(actual_date)
        if date_pos == 0:
            return False, np.nan, "No previous trading day"
        
        prev_date = price_df.index[date_pos - 1]
        prev_price = price_df.loc[prev_date, ticker]
        curr_price = price_df.loc[actual_date, ticker]
        
        if pd.isna(prev_price) or pd.isna(curr_price) or prev_price <= 0:
            return False, np.nan, "Invalid price data"
        
        recalc_return = (curr_price / prev_price) - 1.0
        difference = abs(stored_return - recalc_return)
        
        is_correct = difference < tolerance
        
        if not is_correct:
            error_msg = f"Difference: {difference:.4f} ({stored_return:.2%} vs {recalc_return:.2%})"
        else:
            error_msg = "Correct"
        
        return is_correct, recalc_return, error_msg
        
    except Exception as e:
        return False, np.nan, f"Error: {str(e)}"


def recalculate_all_returns_from_prices(returns_df: pd.DataFrame, 
                                       sample_size: int = None) -> pd.DataFrame:
    """
    Recalculate ALL returns from adjusted prices to ensure correctness.
    
    Args:
        returns_df: Current returns DataFrame
        sample_size: If provided, only recalculate this many tickers (for testing)
        
    Returns:
        Recalculated returns DataFrame
    """
    logger.info("="*70)
    logger.info("Recalculating ALL Returns from Adjusted Prices")
    logger.info("="*70)
    
    price_loader = YahooPriceLoader()
    
    tickers = returns_df.columns.tolist()
    if sample_size:
        tickers = tickers[:sample_size]
        logger.info(f"Testing with {len(tickers)} tickers (sample)")
    else:
        logger.info(f"Recalculating returns for {len(tickers)} tickers")
    
    date_range = (returns_df.index.min(), returns_df.index.max())
    logger.info(f"Date range: {date_range[0].date()} to {date_range[1].date()}")
    
    # Recalculate returns for each ticker
    recalculated_returns = pd.DataFrame(index=returns_df.index)
    corrections_log = []
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            logger.info(f"  Progress: {i+1}/{len(tickers)} tickers ({100*(i+1)/len(tickers):.1f}%)")
        
        try:
            # Get adjusted prices for entire period
            price_series = price_loader.get_adjusted_close(
                symbols=[ticker],
                start_date=date_range[0].strftime('%Y-%m-%d'),
                end_date=date_range[1].strftime('%Y-%m-%d')
            )
            
            if price_series.empty or ticker not in price_series.columns:
                logger.debug(f"  {ticker}: No price data")
                continue
            
            # Calculate returns
            ticker_returns = price_series[ticker].pct_change().dropna()
            
            # Align with returns_df index
            aligned_returns = pd.Series(index=returns_df.index, dtype=float)
            for date in returns_df.index:
                if date in ticker_returns.index:
                    aligned_returns.loc[date] = ticker_returns.loc[date]
            
            # Compare with stored returns and log differences
            stored_returns = returns_df[ticker]
            common_dates = stored_returns.index.intersection(aligned_returns.index)
            
            differences = (stored_returns.loc[common_dates] - aligned_returns.loc[common_dates]).abs()
            large_diffs = differences[differences > 0.01]  # >1% difference
            
            if len(large_diffs) > 0:
                logger.info(f"  {ticker}: {len(large_diffs)} dates with >1% difference")
                for date, diff in large_diffs.head(5).items():
                    stored = stored_returns.loc[date]
                    recalc = aligned_returns.loc[date]
                    corrections_log.append({
                        'ticker': ticker,
                        'date': date,
                        'stored_return': stored,
                        'recalculated_return': recalc,
                        'difference': diff
                    })
            
            recalculated_returns[ticker] = aligned_returns
            
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            logger.warning(f"  {ticker}: Error - {e}")
            continue
    
    logger.info(f"\nRecalculation complete:")
    logger.info(f"  Tickers processed: {len(recalculated_returns.columns)}")
    logger.info(f"  Corrections needed: {len(corrections_log)}")
    
    return recalculated_returns, corrections_log

