"""
Fetch All S&P 500 Data
1. Extract unique tickers from monthly constituents
2. Fetch fundamental data (income, balance, cash flow) for each ticker
3. Fetch total returns for all tickers
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import List, Set
import time

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import research modules
from lib.etf.functions.research.core.data_fetcher import FinancialDataFetcher
from lib.etf.functions.research.core.backtesting import YahooPriceLoader

# Output directories
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents.csv')
FUNDAMENTALS_DIR = Path('./data/research/sp500_fundamentals')
RETURNS_DIR = Path('./data/research/sp500_returns')
RETURNS_DIR.mkdir(parents=True, exist_ok=True)
FUNDAMENTALS_DIR.mkdir(parents=True, exist_ok=True)


def get_unique_tickers() -> List[str]:
    """
    Extract unique tickers from S&P 500 monthly constituents.
    
    Returns:
        Sorted list of unique ticker symbols
    """
    logger.info("="*70)
    logger.info("Step 1: Extracting Unique Tickers")
    logger.info("="*70)
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return []
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    
    if 'symbol' not in df.columns:
        logger.error("No 'symbol' column found in constituents file")
        return []
    
    unique_tickers = sorted(df['symbol'].unique().tolist())
    
    logger.info(f"✓ Found {len(unique_tickers)} unique tickers")
    logger.info(f"  First 10: {unique_tickers[:10]}")
    logger.info(f"  Last 10: {unique_tickers[-10:]}")
    
    # Save unique tickers list
    tickers_file = RETURNS_DIR / 'sp500_unique_tickers.csv'
    tickers_df = pd.DataFrame({'ticker': unique_tickers})
    tickers_df.to_csv(tickers_file, index=False)
    logger.info(f"✓ Saved unique tickers to {tickers_file}")
    
    return unique_tickers


def fetch_fundamental_data(tickers: List[str], max_tickers: int = None):
    """
    Fetch fundamental data (income, balance, cash flow) for each ticker.
    Saves each ticker's data to its own CSV file.
    
    Args:
        tickers: List of ticker symbols
        max_tickers: Maximum number of tickers to process (for testing)
    """
    logger.info("="*70)
    logger.info("Step 2: Fetching Fundamental Data")
    logger.info("="*70)
    
    if max_tickers:
        tickers = tickers[:max_tickers]
        logger.info(f"Processing first {max_tickers} tickers (testing mode)")
    
    # Initialize data fetcher
    # Use local directory for now (external drive has permission issues)
    base_storage_path = FUNDAMENTALS_DIR
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        raise ValueError("FMP_API_KEY environment variable is required. Set it in your .env file or export it.")
    
    fetcher = FinancialDataFetcher(
        api_key=api_key,
        base_storage_path=base_storage_path
    )
    
    logger.info(f"Fetching data for {len(tickers)} tickers...")
    logger.info(f"Storage path: {base_storage_path}")
    
    successful = 0
    failed = 0
    start_time = time.time()
    
    for i, ticker in enumerate(tickers, 1):
        # Calculate progress
        percent_complete = (i / len(tickers)) * 100
        
        # Calculate time estimates
        elapsed_time = time.time() - start_time
        if i > 1:
            avg_time_per_ticker = elapsed_time / (i - 1)
            remaining_tickers = len(tickers) - i
            estimated_remaining = avg_time_per_ticker * remaining_tickers
            estimated_total = elapsed_time + estimated_remaining
            
            # Format time
            elapsed_str = f"{elapsed_time/60:.1f} min"
            remaining_str = f"{estimated_remaining/60:.1f} min"
            total_str = f"{estimated_total/60:.1f} min"
        else:
            elapsed_str = "0.0 min"
            remaining_str = "calculating..."
            total_str = "calculating..."
        
        logger.info(f"\n{'='*70}")
        logger.info(f"FUNDAMENTAL DATA PROGRESS: {percent_complete:.1f}% ({i}/{len(tickers)})")
        logger.info(f"Current: {ticker} | Elapsed: {elapsed_str} | Remaining: {remaining_str} | Est. Total: {total_str}")
        logger.info(f"{'='*70}")
        
        try:
            # Fetch all statements at once
            results = fetcher.fetch_all_statements(
                symbol=ticker,
                period='annual',
                limit=1000  # Get as much historical data as possible
            )
            
            # Check if we got data
            has_data = any(len(results.get(st, [])) > 0 for st in ['income', 'balance', 'cashflow'])
            if has_data:
                logger.info(f"  ✓ Data saved: income={len(results.get('income', []))}, "
                          f"balance={len(results.get('balance', []))}, "
                          f"cashflow={len(results.get('cashflow', []))}")
            else:
                logger.warning(f"  ⚠ No data retrieved for {ticker}")
            
            successful += 1
            
        except Exception as e:
            logger.error(f"  ✗ Failed to fetch data for {ticker}: {e}")
            failed += 1
            continue
        
        # Print progress every 10 tickers or at milestones
        if i % 10 == 0 or i == len(tickers):
            logger.info(f"\n>>> MILESTONE: {i}/{len(tickers)} tickers processed ({percent_complete:.1f}%) | "
                       f"Successful: {successful} | Failed: {failed} <<<")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Fundamental Data Fetching Complete")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"{'='*70}")


def fetch_total_returns(tickers: List[str], start_date: str = '1957-01-01', 
                        end_date: str = None) -> pd.DataFrame:
    """
    Fetch total returns for all tickers using Yahoo Finance.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date for returns
        end_date: End date (defaults to today)
        
    Returns:
        DataFrame with dates as index and tickers as columns
    """
    logger.info("="*70)
    logger.info("Step 3: Fetching Total Returns")
    logger.info("="*70)
    
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Fetching returns for {len(tickers)} tickers")
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Initialize Yahoo price loader
    price_loader = YahooPriceLoader()
    
    # Fetch returns in batches (Yahoo Finance may have rate limits)
    batch_size = 50
    all_returns = pd.DataFrame()
    
    successful_tickers = []
    failed_tickers = []
    start_time = time.time()
    
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        # Calculate progress
        percent_complete = (batch_num / total_batches) * 100
        
        # Calculate time estimates
        elapsed_time = time.time() - start_time
        if batch_num > 1:
            avg_time_per_batch = elapsed_time / (batch_num - 1)
            remaining_batches = total_batches - batch_num
            estimated_remaining = avg_time_per_batch * remaining_batches
            estimated_total = elapsed_time + estimated_remaining
            
            # Format time
            elapsed_str = f"{elapsed_time/60:.1f} min"
            remaining_str = f"{estimated_remaining/60:.1f} min"
            total_str = f"{estimated_total/60:.1f} min"
        else:
            elapsed_str = "0.0 min"
            remaining_str = "calculating..."
            total_str = "calculating..."
        
        logger.info(f"\n{'='*70}")
        logger.info(f"RETURNS PROGRESS: {percent_complete:.1f}% (Batch {batch_num}/{total_batches})")
        logger.info(f"Processing {len(batch)} tickers: {batch[0]} ... {batch[-1]}")
        logger.info(f"Elapsed: {elapsed_str} | Remaining: {remaining_str} | Est. Total: {total_str}")
        logger.info(f"{'='*70}")
        
        try:
            # Get adjusted close prices (includes dividends/splits)
            price_df = price_loader.get_adjusted_close(
                symbols=batch,
                start_date=start_date,
                end_date=end_date
            )
            
            if not price_df.empty:
                # Calculate total returns (pct_change)
                returns_df = price_loader.calculate_returns(price_df)
                
                # Merge with existing returns
                if all_returns.empty:
                    all_returns = returns_df
                else:
                    all_returns = pd.concat([all_returns, returns_df], axis=1)
                    # Remove duplicates if any
                    all_returns = all_returns.loc[:, ~all_returns.columns.duplicated()]
                
                batch_successful = [t for t in batch if t in returns_df.columns]
                successful_tickers.extend(batch_successful)
                logger.info(f"  ✓ Retrieved returns for {len(batch_successful)}/{len(batch)} tickers in batch")
            else:
                failed_tickers.extend(batch)
                logger.warning(f"  ✗ No data returned for batch")
        
        except Exception as e:
            logger.error(f"  ✗ Batch failed: {e}")
            failed_tickers.extend(batch)
            continue
        
        # Print milestone every 5 batches
        if batch_num % 5 == 0 or batch_num == total_batches:
            logger.info(f"\n>>> RETURNS MILESTONE: {batch_num}/{total_batches} batches ({percent_complete:.1f}%) | "
                       f"Successful: {len(successful_tickers)} tickers | Failed: {len(failed_tickers)} tickers <<<")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Returns Fetching Summary")
    logger.info(f"  Successful: {len(successful_tickers)} tickers")
    logger.info(f"  Failed: {len(failed_tickers)} tickers")
    logger.info(f"  Total returns DataFrame shape: {all_returns.shape}")
    
    if not all_returns.empty:
        logger.info(f"  Date range: {all_returns.index.min()} to {all_returns.index.max()}")
        logger.info(f"  Coverage: {all_returns.notna().sum().sum() / (len(all_returns) * len(all_returns.columns)) * 100:.1f}%")
    
    # Save returns
    if not all_returns.empty:
        returns_file = RETURNS_DIR / 'sp500_total_returns.csv'
        all_returns.to_csv(returns_file)
        logger.info(f"\n✓ Saved returns to {returns_file}")
        
        # Also save as parquet for efficiency
        parquet_file = RETURNS_DIR / 'sp500_total_returns.parquet'
        all_returns.to_parquet(parquet_file, engine='pyarrow')
        logger.info(f"✓ Saved returns to {parquet_file}")
        
        # Save metadata
        metadata = {
            'tickers_count': len(all_returns.columns),
            'date_range': {
                'start': str(all_returns.index.min()),
                'end': str(all_returns.index.max())
            },
            'total_observations': len(all_returns),
            'successful_tickers': len(successful_tickers),
            'failed_tickers': len(failed_tickers),
            'coverage_pct': float(all_returns.notna().sum().sum() / (len(all_returns) * len(all_returns.columns)) * 100),
            'last_updated': datetime.now().isoformat()
        }
        
        import json
        metadata_file = RETURNS_DIR / 'sp500_returns_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Saved metadata to {metadata_file}")
    
    return all_returns


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("S&P 500 Complete Data Fetching")
    logger.info("="*70)
    
    # Step 1: Get unique tickers
    tickers = get_unique_tickers()
    
    if not tickers:
        logger.error("No tickers found. Exiting.")
        return
    
    # Step 2: Fetch fundamental data
    # Note: This will take a while for 1,372 tickers
    # Set max_tickers to a small number (e.g., 10) for testing
    # Set to None to process all tickers
    logger.info("\n" + "="*70)
    logger.info("Starting fundamental data fetch...")
    logger.info("This may take a long time for all tickers.")
    logger.info("Set max_tickers in the script to limit processing for testing.")
    logger.info("="*70)
    
    # Process all tickers (set max_tickers=10 for testing)
    fetch_fundamental_data(tickers, max_tickers=None)
    
    # Step 3: Fetch total returns
    logger.info("\n" + "="*70)
    logger.info("Starting returns fetch...")
    logger.info("="*70)
    
    returns_df = fetch_total_returns(tickers, start_date='1957-01-01')
    
    logger.info("\n" + "="*70)
    logger.info("All Data Fetching Complete!")
    logger.info("="*70)
    logger.info(f"Fundamentals: {FUNDAMENTALS_DIR}")
    logger.info(f"Returns: {RETURNS_DIR}")
    logger.info("="*70)


if __name__ == "__main__":
    main()

