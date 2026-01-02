"""
Fetch S&P 500 Returns using Financial Modeling Prep API
Regenerates sp500_total_returns.csv using FMP historical price data
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import List, Optional
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directories
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents.csv')
RETURNS_DIR = Path('./data/research/sp500_returns')
RETURNS_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
FMP_API_KEY = os.getenv('FMP_API_KEY')
if not FMP_API_KEY:
    raise ValueError("FMP_API_KEY environment variable is required. Set it in your .env file or export it.")
FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_ENDPOINT = "stable/historical-price-eod/full"

# Rate limiting
REQUEST_DELAY = 0.25  # seconds between requests
BATCH_SIZE = 10  # process tickers in batches


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
    
    return unique_tickers


def create_session() -> requests.Session:
    """Create a requests session with retry strategy."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_ticker_prices(session: requests.Session, ticker: str, start_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Fetch historical price data for a single ticker from FMP API.
    Fetches in 5-year chunks going backwards from today until start_date is reached.
    
    Args:
        session: requests.Session object
        ticker: Stock ticker symbol
        start_date: Optional start date (YYYY-MM-DD). If None, fetches all available data.
        
    Returns:
        DataFrame with date index and price columns, or None if failed
    """
    url = f"{FMP_BASE_URL}/{FMP_ENDPOINT}"
    
    # Parse start_date if provided, otherwise go back to 1950
    if start_date:
        target_start = pd.to_datetime(start_date)
    else:
        target_start = pd.to_datetime('1950-01-01')  # Default to 1950
    
    today = pd.Timestamp.now().normalize()
    
    all_data = []
    current_end = today
    chunk_count = 0
    max_chunks = 30  # Safety limit (30 chunks = 150 years, enough to go back to 1950)
    
    try:
        while chunk_count < max_chunks:
            # Calculate 5 years back from current_end (approximately 1825 days)
            chunk_start = current_end - pd.Timedelta(days=1825)
            
            # If we have a target start date and we've gone past it, adjust
            if target_start and chunk_start < target_start:
                chunk_start = target_start
            
            # If chunk_start >= current_end, we're done
            if chunk_start >= current_end:
                break
            
            params = {
                'symbol': ticker,
                'apikey': FMP_API_KEY,
                'from': chunk_start.strftime('%Y-%m-%d'),
                'to': current_end.strftime('%Y-%m-%d')
            }
            
            response = session.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data or not isinstance(data, list):
                    # No more data available, break
                    break
                
                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                if df.empty:
                    # No more data available, break
                    break
                
                # Parse date and set as index
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
                
                # Filter to the chunk date range (API might return more)
                df = df[(df.index >= chunk_start) & (df.index <= current_end)]
                
                if not df.empty:
                    all_data.append(df)
                    
                    # Check if we've reached the target start date
                    if target_start and df.index.min() <= target_start:
                        break
                    
                    # Move to next chunk (go back 1 day before this chunk's start)
                    current_end = chunk_start - pd.Timedelta(days=1)
                else:
                    # No data in this chunk, try next chunk
                    current_end = chunk_start - pd.Timedelta(days=1)
                
                chunk_count += 1
                
                # Rate limiting between chunks
                time.sleep(REQUEST_DELAY)
                
            elif response.status_code == 403:
                error = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                logger.error(f"  ✗ 403 Forbidden for {ticker}: {error.get('Error Message', 'Unknown error')}")
                break
            else:
                # If we get an error on first chunk, try without date parameters (fallback)
                if chunk_count == 0:
                    params = {
                        'symbol': ticker,
                        'apikey': FMP_API_KEY
                    }
                    response = session.get(url, params=params, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, list):
                            df = pd.DataFrame(data)
                            if not df.empty:
                                df['date'] = pd.to_datetime(df['date'])
                                df = df.set_index('date').sort_index()
                                all_data.append(df)
                                break
                # Otherwise, assume no more data
                break
                
        if not all_data:
            logger.warning(f"  ⚠ No data returned for {ticker}")
            return None
        
        # Combine all chunks
        combined_df = pd.concat(all_data)
        combined_df = combined_df.sort_index()
        
        # Remove duplicates (in case of overlap) - keep first occurrence
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
        
        # Filter to start_date if provided
        if target_start:
            combined_df = combined_df[combined_df.index >= target_start]
        
        # Use 'close' price for returns calculation
        if 'close' not in combined_df.columns:
            logger.warning(f"  ⚠ No 'close' column for {ticker}")
            return None
        
        # Return DataFrame with just the close price
        price_df = pd.DataFrame({'close': combined_df['close']})
        price_df.index.name = 'Date'
        
            # Logging moved to caller for better visibility
        
        return price_df
            
    except Exception as e:
        logger.error(f"  ✗ Error fetching data for {ticker}: {e}")
        return None
    finally:
        # Rate limiting
        time.sleep(REQUEST_DELAY)


def calculate_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily returns from price data.
    
    Args:
        price_df: DataFrame with 'close' column and date index
        
    Returns:
        DataFrame with returns (pct_change)
    """
    returns_df = price_df['close'].pct_change()
    return returns_df.to_frame(name=price_df.columns[0] if len(price_df.columns) == 1 else 'returns')


def fetch_total_returns(tickers: List[str], start_date: Optional[str] = None, 
                       end_date: Optional[str] = None, 
                       output_filename: str = 'sp500_total_returns.csv') -> pd.DataFrame:
    """
    Fetch total returns for all tickers using FMP API.
    
    Args:
        tickers: List of ticker symbols
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        
    Returns:
        DataFrame with dates as index and tickers as columns
    """
    logger.info("="*70)
    logger.info("Step 2: Fetching Total Returns from FMP API")
    logger.info("="*70)
    
    logger.info(f"Fetching returns for {len(tickers)} tickers")
    if start_date:
        logger.info(f"Start date filter: {start_date}")
    if end_date:
        logger.info(f"End date filter: {end_date}")
    
    # Create session
    session = create_session()
    
    # Fetch returns in batches
    all_returns = pd.DataFrame()
    successful_tickers = []
    failed_tickers = []
    start_time = time.time()
    
    total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        
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
        
        batch_returns = {}
        
        for ticker in batch:
            # Log which ticker we're processing
            logger.info(f"  Processing {ticker}...")
            
            # Fetch price data (with start_date for chunking)
            price_df = fetch_ticker_prices(session, ticker, start_date=start_date)
            
            if price_df is not None and not price_df.empty:
                logger.info(f"  ✓ {ticker}: Retrieved {len(price_df)} records ({price_df.index.min().strftime('%Y-%m-%d')} to {price_df.index.max().strftime('%Y-%m-%d')})")
                # Calculate returns
                returns = calculate_returns(price_df)
                
                # Apply date filters if provided (additional filtering after chunking)
                if start_date:
                    start_ts = pd.to_datetime(start_date)
                    returns = returns[returns.index >= start_ts]
                if end_date:
                    end_ts = pd.to_datetime(end_date)
                    returns = returns[returns.index <= end_ts]
                
                if not returns.empty:
                    # Store returns with ticker as column name
                    batch_returns[ticker] = returns.iloc[:, 0]
                    successful_tickers.append(ticker)
                else:
                    failed_tickers.append(ticker)
                    logger.warning(f"  ⚠ No returns data after filtering for {ticker}")
            else:
                failed_tickers.append(ticker)
        
        # Combine batch returns
        if batch_returns:
            batch_df = pd.DataFrame(batch_returns)
            
            # Merge with existing returns
            if all_returns.empty:
                all_returns = batch_df
            else:
                all_returns = pd.concat([all_returns, batch_df], axis=1)
                # Remove duplicates if any
                all_returns = all_returns.loc[:, ~all_returns.columns.duplicated()]
            
            logger.info(f"  ✓ Retrieved returns for {len(batch_returns)}/{len(batch)} tickers in batch")
        
        # Print milestone every 5 batches
        if batch_num % 5 == 0 or batch_num == total_batches:
            logger.info(f"\n>>> RETURNS MILESTONE: {batch_num}/{total_batches} batches ({percent_complete:.1f}%) | "
                       f"Successful: {len(successful_tickers)} tickers | Failed: {len(failed_tickers)} tickers <<<")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Returns Fetching Summary")
    logger.info(f"  Successful: {len(successful_tickers)} tickers")
    logger.info(f"  Failed: {len(failed_tickers)} tickers")
    logger.info(f"  Total returns DataFrame shape: {all_returns.shape}")
    
    if all_returns.empty:
        logger.warning("  ⚠ No returns data retrieved!")
    else:
        logger.info(f"  Date range: {all_returns.index.min()} to {all_returns.index.max()}")
        coverage = all_returns.notna().sum().sum() / (len(all_returns) * len(all_returns.columns)) * 100
        logger.info(f"  Coverage: {coverage:.1f}%")
    
    # Filter by start_date if provided
    if not all_returns.empty and start_date:
        start_ts = pd.to_datetime(start_date)
        all_returns = all_returns[all_returns.index >= start_ts]
        logger.info(f"  Filtered to dates >= {start_date}")
        logger.info(f"  Filtered date range: {all_returns.index.min()} to {all_returns.index.max()}")
        logger.info(f"  Filtered observations: {len(all_returns)}")
    
    # Save returns
    if not all_returns.empty:
        returns_file = RETURNS_DIR / output_filename
        all_returns.to_csv(returns_file)
        logger.info(f"\n✓ Saved returns to {returns_file}")
        
        # Also save as parquet for efficiency
        try:
            parquet_filename = output_filename.replace('.csv', '.parquet')
            parquet_file = RETURNS_DIR / parquet_filename
            all_returns.to_parquet(parquet_file, engine='pyarrow')
            logger.info(f"✓ Saved returns to {parquet_file}")
        except Exception as e:
            logger.warning(f"Could not save parquet file: {e}")
        
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
            'coverage_pct': float(all_returns.notna().sum().sum() / (len(all_returns) * len(all_returns.columns)) * 100) if not all_returns.empty else 0.0,
            'last_updated': datetime.now().isoformat(),
            'data_source': 'Financial Modeling Prep API',
            'api_endpoint': FMP_ENDPOINT,
            'start_date_filter': start_date if start_date else None
        }
        
        import json
        metadata_filename = output_filename.replace('.csv', '_metadata.json')
        metadata_file = RETURNS_DIR / metadata_filename
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Saved metadata to {metadata_file}")
    
    return all_returns


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch S&P 500 returns from FMP API')
    parser.add_argument('--start-date', type=str, default='1950-01-01',
                       help='Start date for filtering returns (YYYY-MM-DD). Default: 1950-01-01 to get full historical data')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date for filtering returns (YYYY-MM-DD). Default: today')
    parser.add_argument('--output', type=str, default='sp500_total_returns.csv',
                       help='Output filename (default: sp500_total_returns.csv)')
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("S&P 500 Returns Fetching (FMP API)")
    logger.info("="*70)
    
    # Step 1: Get unique tickers
    tickers = get_unique_tickers()
    
    if not tickers:
        logger.error("No tickers found. Exiting.")
        return
    
    # Step 2: Fetch total returns
    logger.info("\n" + "="*70)
    logger.info("Starting returns fetch from FMP API...")
    if args.start_date:
        logger.info(f"Will filter to dates >= {args.start_date}")
    logger.info("="*70)
    
    returns_df = fetch_total_returns(tickers, start_date=args.start_date, 
                                    end_date=args.end_date,
                                    output_filename=args.output)
    
    logger.info("\n" + "="*70)
    logger.info("Returns Fetching Complete!")
    logger.info("="*70)
    logger.info(f"Returns file: {RETURNS_DIR / args.output}")
    metadata_filename = args.output.replace('.csv', '_metadata.json')
    logger.info(f"Metadata file: {RETURNS_DIR / metadata_filename}")
    logger.info("="*70)


if __name__ == "__main__":
    main()

