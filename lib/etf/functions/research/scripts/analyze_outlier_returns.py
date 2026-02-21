"""
Analyze Outlier Returns from FMP Data
Creates a CSV with outlier returns, recalculated returns from FMP prices/splits/dividends, and flags mismatches.
Uses ONLY FMP data feeds - no Yahoo Finance data.
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
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.backtesting import FMPClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_fmp_splits(fmp_client: FMPClient, ticker: str) -> List[Dict]:
    """
    Get all stock splits for a ticker from FMP.
    
    Returns:
        List of split records with date, numerator, denominator
    """
    try:
        endpoint = f"stable/splits"
        params = {'symbol': ticker}
        splits = fmp_client._get(endpoint, params)
        
        if splits and isinstance(splits, list):
            return splits
        return []
    except Exception as e:
        logger.debug(f"Error fetching splits for {ticker}: {e}")
        return []


def get_fmp_dividends(fmp_client: FMPClient, ticker: str) -> List[Dict]:
    """
    Get all dividends for a ticker from FMP.
    
    Returns:
        List of dividend records with date, adjDividend, dividend
    """
    try:
        endpoint = f"stable/dividends"
        params = {'symbol': ticker}
        dividends = fmp_client._get(endpoint, params)
        
        if dividends and isinstance(dividends, list):
            return dividends
        return []
    except Exception as e:
        logger.debug(f"Error fetching dividends for {ticker}: {e}")
        return []


def check_split_on_date(splits: List[Dict], date: pd.Timestamp) -> Optional[Dict]:
    """
    Check if there's a split on the given date, one day before, or one day after.
    
    Returns:
        Split info dict or None
    """
    if not splits:
        return None
    
    date_normalized = date.tz_localize(None) if date.tz else date
    target_dates = [
        date_normalized,
        date_normalized - pd.Timedelta(days=1),
        date_normalized + pd.Timedelta(days=1)
    ]
    
    for split in splits:
        split_date_str = split.get('date')
        if not split_date_str:
            continue
        
        split_date = pd.to_datetime(split_date_str)
        split_date_normalized = split_date.tz_localize(None) if split_date.tz else split_date
        
        for target_date in target_dates:
            if split_date_normalized.date() == target_date.date():
                numerator = split.get('numerator', 1)
                denominator = split.get('denominator', 1)
                split_ratio = numerator / denominator if denominator > 0 else None
                
                return {
                    'split_date': split_date_normalized.date(),
                    'split_ratio': split_ratio,
                    'numerator': numerator,
                    'denominator': denominator,
                    'has_split': True,
                    'days_from_target': (split_date_normalized.date() - date_normalized.date()).days
                }
    
    return {'has_split': False}


def get_fmp_prices(fmp_client: FMPClient, ticker: str, 
                   start_date: str, end_date: str) -> pd.DataFrame:
    """
    Get FMP price history using stable/historical-price-eod/full endpoint.
    
    Returns:
        DataFrame with date index and columns: 'close' (raw close price)
    """
    try:
        endpoint = "stable/historical-price-eod/full"
        params = {
            'symbol': ticker,
            'from': start_date,
            'to': end_date
        }
        
        data = fmp_client._get(endpoint, params)
        
        if not data or not isinstance(data, list):
            return pd.DataFrame()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
        
        # Return close price (raw, unadjusted)
        if 'close' in df.columns:
            return df[['close']]
        return pd.DataFrame()
        
    except Exception as e:
        logger.debug(f"Error fetching FMP prices for {ticker}: {e}")
        return pd.DataFrame()


def recalculate_adjusted_price_from_fmp(raw_price: float, splits: List[Dict], 
                                        dividends: List[Dict], 
                                        current_date: pd.Timestamp) -> float:
    """
    Recalculate adjusted price from raw price using FMP splits and dividends.
    
    This applies all splits and dividends that occurred AFTER the current date
    (going backwards in time to adjust historical prices).
    
    For splits: multiply by denominator/numerator (e.g., 2:1 split means price was half before)
    For dividends: add back the adjusted dividend (dividends reduce price on ex-date)
    """
    adjusted_price = raw_price
    
    # Get all splits and dividends after current_date (we adjust backwards)
    future_splits = [s for s in splits if pd.to_datetime(s.get('date', '1900-01-01')) > current_date]
    future_dividends = [d for d in dividends if pd.to_datetime(d.get('date', '1900-01-01')) > current_date]
    
    # Sort by date (ascending - earliest first, so we apply them in chronological order)
    future_splits.sort(key=lambda x: pd.to_datetime(x.get('date', '1900-01-01')))
    future_dividends.sort(key=lambda x: pd.to_datetime(x.get('date', '1900-01-01')))
    
    # Apply splits (multiply by denominator/numerator to adjust backwards)
    # Example: 2:1 split means 1 share becomes 2, so historical price was half
    for split in future_splits:
        numerator = split.get('numerator', 1)
        denominator = split.get('denominator', 1)
        if denominator > 0 and numerator > 0:
            # To adjust backwards: if split is 2:1, price was half before split
            adjusted_price = adjusted_price * (denominator / numerator)
    
    # Apply dividends (add back adjusted dividend to adjust backwards)
    # Dividends reduce price on ex-date, so we add them back to get pre-dividend price
    for div in future_dividends:
        # Use adjDividend if available (already adjusted for splits), otherwise use dividend
        adj_div = div.get('adjDividend')
        if adj_div is None or pd.isna(adj_div):
            adj_div = div.get('dividend', 0)
        if adj_div and adj_div > 0:
            adjusted_price = adjusted_price + adj_div
    
    return adjusted_price


def analyze_outlier_returns(returns_file: str, output_file: str, 
                           threshold: float = 0.15, start_date: str = '2000-01-01'):
    """
    Analyze outlier returns and create a CSV with Yahoo returns and split information.
    
    Args:
        returns_file: Path to returns CSV
        output_file: Path to output CSV
        threshold: Threshold for outlier returns (default 15%)
        start_date: Start date for analysis (default 2000-01-01)
    """
    logger.info("="*70)
    logger.info("Analyzing Outlier Returns")
    logger.info("="*70)
    
    # Load returns data
    logger.info(f"Loading returns from {returns_file}...")
    returns_df = pd.read_csv(returns_file, index_col=0, parse_dates=True)
    
    # Normalize timezone - remove timezone info completely
    if isinstance(returns_df.index, pd.DatetimeIndex):
        if returns_df.index.tz is not None:
            # Convert timezone-aware to naive by converting to UTC first, then removing tz
            returns_df.index = pd.to_datetime(returns_df.index.tz_convert('UTC').tz_localize(None))
        # Ensure it's a DatetimeIndex
        returns_df.index = pd.to_datetime(returns_df.index)
    
    # Filter for dates after start_date - use date() for comparison
    start_dt = pd.to_datetime(start_date)
    if start_dt.tz is not None:
        start_dt = start_dt.tz_convert('UTC').tz_localize(None)
    
    # Use date comparison to avoid timezone issues
    date_mask = pd.Series([d.date() >= start_dt.date() for d in returns_df.index], index=returns_df.index)
    returns_df = returns_df[date_mask]
    
    logger.info(f"Date range: {returns_df.index.min().date()} to {returns_df.index.max().date()}")
    logger.info(f"Total tickers: {len(returns_df.columns)}")
    logger.info(f"Total dates: {len(returns_df)}")
    
    # Find outlier returns
    logger.info(f"\nFinding outlier returns (>{threshold:.0%})...")
    outlier_mask = returns_df.abs() > threshold
    outlier_returns = returns_df[outlier_mask].stack()
    
    logger.info(f"Found {len(outlier_returns)} outlier returns")
    
    # Initialize FMP client and Yahoo price loader
    fmp_api_key = os.getenv('FMP_API_KEY')
    if not fmp_api_key:
        logger.error("FMP_API_KEY environment variable not set")
        return
    
    fmp_client = FMPClient(api_key=fmp_api_key)
    
    # Get all splits and dividends for unique tickers (cache to avoid repeated API calls)
    logger.info("\nFetching splits and dividends for all unique tickers...")
    unique_tickers = outlier_returns.index.get_level_values(1).unique().tolist()
    logger.info(f"  Found {len(unique_tickers)} unique tickers")
    
    splits_cache = {}
    dividends_cache = {}
    
    for i, ticker in enumerate(unique_tickers):
        if (i + 1) % 50 == 0:
            logger.info(f"  Progress: {i+1}/{len(unique_tickers)} tickers")
        
        splits_cache[ticker] = get_fmp_splits(fmp_client, ticker)
        dividends_cache[ticker] = get_fmp_dividends(fmp_client, ticker)
        time.sleep(0.1)  # Rate limiting
    
    logger.info(f"  ✓ Fetched splits and dividends for {len(unique_tickers)} tickers")
    
    # Process outliers
    logger.info("\nProcessing outliers and recalculating adjusted prices...")
    results = []
    
    for i, ((date, ticker), fmp_return) in enumerate(outlier_returns.items()):
        if (i + 1) % 100 == 0:
            logger.info(f"  Progress: {i+1}/{len(outlier_returns)} ({100*(i+1)/len(outlier_returns):.1f}%)")
        
        # Get splits and dividends from cache
        splits = splits_cache.get(ticker, [])
        dividends = dividends_cache.get(ticker, [])
        
        # Check for split on this date
        split_info = check_split_on_date(splits, date)
        
        # Get FMP prices around this date to recalculate adjusted close
        # fmp_return is the stored return from the outlier_returns data
        recalculated_return = None
        price_mismatch = None
        
        try:
            # Get FMP price data
            start_date_str = (date - pd.Timedelta(days=10)).strftime('%Y-%m-%d')
            end_date_str = (date + pd.Timedelta(days=10)).strftime('%Y-%m-%d')
            
            price_df = get_fmp_prices(fmp_client, ticker, start_date_str, end_date_str)
            
            if not price_df.empty and 'close' in price_df.columns:
                # Find the date
                date_found = None
                for idx in price_df.index:
                    if idx.date() == date.date():
                        date_found = idx
                        break
                
                if date_found is not None:
                    date_pos = price_df.index.get_loc(date_found)
                    
                    if date_pos > 0:
                        prev_date = price_df.index[date_pos - 1]
                        prev_close = price_df.loc[prev_date, 'close']
                        curr_close = price_df.loc[date_found, 'close']
                        
                        if pd.notna(prev_close) and pd.notna(curr_close) and prev_close > 0:
                            # Calculate return from raw prices
                            raw_return = (curr_close / prev_close) - 1.0
                            
                            # Recalculate adjusted prices using splits and dividends
                            prev_adj_price = recalculate_adjusted_price_from_fmp(
                                prev_close, splits, dividends, prev_date
                            )
                            curr_adj_price = recalculate_adjusted_price_from_fmp(
                                curr_close, splits, dividends, date_found
                            )
                            
                            if prev_adj_price > 0:
                                recalculated_return = (curr_adj_price / prev_adj_price) - 1.0
                                
                                # Compare with stored return
                                if abs(fmp_return - recalculated_return) > 0.001:  # >0.1% difference
                                    price_mismatch = {
                                        'raw_return': raw_return,
                                        'recalculated_return': recalculated_return,
                                        'stored_return': fmp_return,
                                        'difference': abs(fmp_return - recalculated_return),
                                        'has_split': split_info.get('has_split', False) if split_info else False,
                                        'has_dividend': any(
                                            pd.to_datetime(d.get('date', '1900-01-01')).date() == date.date() 
                                            for d in dividends
                                        )
                                    }
                            
                            # Note: stable/historical-price-eod/full doesn't provide adjClose
                            # We recalculate it from raw prices using splits/dividends
                                        
        except Exception as e:
            logger.debug(f"Error recalculating prices for {ticker} on {date.date()}: {e}")
        
        result = {
            'date': date.date(),
            'ticker': ticker,
            'stored_return': fmp_return,
            'recalculated_return': recalculated_return,
            'return_difference': (fmp_return - recalculated_return) if recalculated_return is not None else None,
            'has_split': split_info.get('has_split', False) if split_info else None,
            'split_date': split_info.get('split_date') if split_info else None,
            'split_ratio': split_info.get('split_ratio') if split_info else None,
            'split_numerator': split_info.get('numerator') if split_info else None,
            'split_denominator': split_info.get('denominator') if split_info else None,
            'split_days_from_target': split_info.get('days_from_target') if split_info else None,
            'price_mismatch': price_mismatch is not None,
            'raw_return': price_mismatch.get('raw_return') if price_mismatch else None,
            'fmp_adj_return': price_mismatch.get('fmp_adj_return') if price_mismatch else None,
            'mismatch_difference': price_mismatch.get('difference') if price_mismatch else None,
            'fmp_adj_difference': price_mismatch.get('fmp_adj_difference') if price_mismatch else None,
            'has_dividend': price_mismatch.get('has_dividend') if price_mismatch else None
        }
        
        results.append(result)
        
        # Rate limiting
        time.sleep(0.1)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Sort by date and ticker
    df = df.sort_values(['date', 'ticker'])
    
    # Save to CSV
    logger.info(f"\nSaving results to {output_file}...")
    df.to_csv(output_file, index=False)
    
    logger.info(f"\nSummary:")
    logger.info(f"  Total outliers: {len(df)}")
    logger.info(f"  With recalculated returns: {df['recalculated_return'].notna().sum() if 'recalculated_return' in df.columns else 0}")
    logger.info(f"  With splits: {df['has_split'].sum() if 'has_split' in df.columns else 0}")
    logger.info(f"  Price mismatches (stored vs recalculated): {df['price_mismatch'].sum() if 'price_mismatch' in df.columns else 0}")
    logger.info(f"  With dividends: {df['has_dividend'].sum() if 'has_dividend' in df.columns else 0}")
    logger.info(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Show sample
    logger.info(f"\nSample of results:")
    print(df.head(20).to_string())
    
    logger.info(f"\n✓ Complete! Results saved to {output_file}")


if __name__ == "__main__":
    returns_file = "./data/research/sp500_returns/sp500_total_returns.csv"
    output_file = "./data/research/sp500_returns/outlier_returns_analysis.csv"
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    analyze_outlier_returns(
        returns_file=returns_file,
        output_file=output_file,
        threshold=0.15,  # 15% threshold
        start_date='2000-01-01'
    )

