"""
Fetch S&P 500 Historical Returns from FMP API - Using Corrected Constituent List
Fetches historical end-of-day prices for all unique tickers from the corrected constituent file
and calculates daily returns, saving them to a CSV.

This version:
- Uses the corrected constituent file to get the complete ticker list
- Fetches data in 5-year chunks going backwards from today
- Goes back as far as possible (1950 or as far as available for each ticker)
- Saves to a new file (doesn't overwrite existing)
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
import time
from typing import Optional, List
from dotenv import load_dotenv

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data paths
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents_corrected.csv')
OUTPUT_DIR = Path('./data/research/sp500_returns')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# FMP API configuration
FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_ENDPOINT = "stable/historical-price-eod/full"
FMP_API_KEY = os.getenv('FMP_API_KEY')
REQUEST_DELAY = 0.3  # Delay between requests to avoid rate limiting


def get_unique_tickers_from_corrected_constituents() -> List[str]:
    """
    Get unique tickers from the corrected constituent file.
    
    Returns:
        List of unique ticker symbols
    """
    logger.info("Loading tickers from corrected constituent file...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Corrected constituent file not found: {CONSTITUENTS_FILE}")
        return []
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    unique_tickers = sorted(df['symbol'].unique().tolist())
    
    logger.info(f"Found {len(unique_tickers)} unique tickers in corrected constituent file")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return unique_tickers


def fetch_ticker_prices(session: requests.Session, ticker: str, start_date: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Fetch historical prices for a ticker using 5-year chunking.
    
    FMP API limits data to 5 years per request, so we fetch in chunks going backwards
    from today until we reach the start_date (or 1950) or run out of data.
    
    Args:
        session: Requests session
        ticker: Ticker symbol
        start_date: Target start date (YYYY-MM-DD), defaults to 1950-01-01
        
    Returns:
        DataFrame with date index and price columns, or None if no data
    """
    url = f"{FMP_BASE_URL}/{FMP_ENDPOINT}"
    
    target_start = pd.to_datetime(start_date) if start_date else pd.to_datetime('1950-01-01')
    today = pd.Timestamp.now().normalize()
    
    all_data = []
    current_end = today
    chunk_count = 0
    max_chunks = 30  # Safety limit (30 chunks = 150 years)
    
    while chunk_count < max_chunks:
        # Calculate chunk start (5 years before current_end)
        chunk_start = current_end - pd.Timedelta(days=1825)  # Approximately 5 years
        
        # If we've gone past our target start, use target start
        if chunk_start < target_start:
            chunk_start = target_start
        
        # If chunk_start >= current_end, we're done
        if chunk_start >= current_end:
            break
        
        params = {
            'symbol': ticker,
            'from': chunk_start.strftime('%Y-%m-%d'),
            'to': current_end.strftime('%Y-%m-%d'),
            'apikey': FMP_API_KEY
        }
        
        try:
            response = session.get(url, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date').sort_index()
                    
                    # Filter to date range
                    df = df[(df.index >= chunk_start) & (df.index <= current_end)]
                    
                    if not df.empty:
                        all_data.append(df)
                        # Move to next chunk (go back in time)
                        current_end = chunk_start - pd.Timedelta(days=1)
                    else:
                        # No data in this chunk, but continue to check earlier chunks
                        # (don't break - acquired companies may have data in earlier periods)
                        current_end = chunk_start - pd.Timedelta(days=1)
                else:
                    # Empty response - continue to check earlier chunks
                    # Don't break here - acquired companies may have historical data
                    current_end = chunk_start - pd.Timedelta(days=1)
            elif response.status_code == 403:
                logger.warning(f"  API access denied for {ticker} - may require higher tier")
                break
            else:
                logger.debug(f"  API returned {response.status_code} for {ticker}")
                break
        except Exception as e:
            logger.debug(f"  Error fetching chunk for {ticker}: {e}")
            break
        
        chunk_count += 1
        time.sleep(REQUEST_DELAY)
    
    if all_data:
        # Combine all chunks
        combined_df = pd.concat(all_data)
        combined_df = combined_df.sort_index()
        # Remove duplicates (keep last)
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        return combined_df
    
    return None


def fetch_total_returns(tickers: List[str], start_date: Optional[str] = None, 
                       output_filename: str = 'sp500_total_returns_corrected.csv') -> pd.DataFrame:
    """
    Fetch total returns for all tickers and save to CSV.
    
    Args:
        tickers: List of ticker symbols
        start_date: Start date for filtering (YYYY-MM-DD)
        output_filename: Output filename
        
    Returns:
        DataFrame with daily returns
    """
    if not FMP_API_KEY:
        logger.error("FMP_API_KEY environment variable not set. Cannot fetch data.")
        return pd.DataFrame()
    
    logger.info("="*70)
    logger.info("Fetching S&P 500 Historical Returns (Corrected Constituents)")
    logger.info("="*70)
    logger.info(f"Total tickers to process: {len(tickers)}")
    logger.info(f"Output file: {output_filename}")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'REDI Research',
        'Accept': 'application/json'
    })
    
    all_returns = {}
    successful = 0
    failed = 0
    no_data = 0
    
    for i, ticker in enumerate(tickers, 1):
        logger.info(f"[{i}/{len(tickers)}] Fetching {ticker}...")
        
        try:
            prices_df = fetch_ticker_prices(session, ticker, start_date)
            
            if prices_df is not None and not prices_df.empty:
                if 'close' in prices_df.columns:
                    # Calculate daily returns
                    returns = prices_df['close'].pct_change().dropna()
                    
                    if not returns.empty:
                        all_returns[ticker] = returns
                        successful += 1
                        
                        date_range = f"{returns.index.min().date()} to {returns.index.max().date()}"
                        logger.info(f"  ✓ {ticker}: {len(returns)} returns ({date_range})")
                    else:
                        no_data += 1
                        logger.warning(f"  ✗ {ticker}: No valid returns calculated")
                else:
                    no_data += 1
                    logger.warning(f"  ✗ {ticker}: No 'close' column in data")
            else:
                no_data += 1
                logger.warning(f"  ✗ {ticker}: No data available")
        
        except Exception as e:
            failed += 1
            logger.error(f"  ✗ {ticker}: Error - {e}")
        
        # Progress update every 50 tickers
        if i % 50 == 0:
            logger.info(f"  Progress: {successful} successful, {failed} failed, {no_data} no data")
    
    logger.info("="*70)
    logger.info("Fetching Complete")
    logger.info("="*70)
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"No data: {no_data}")
    
    if not all_returns:
        logger.error("No returns data fetched. Exiting.")
        return pd.DataFrame()
    
    # Combine all returns into a DataFrame
    logger.info("\nCombining returns into DataFrame...")
    returns_df = pd.DataFrame(all_returns)
    returns_df = returns_df.sort_index()
    
    logger.info(f"✓ Combined returns DataFrame: {len(returns_df)} days, {len(returns_df.columns)} tickers")
    logger.info(f"  Date range: {returns_df.index.min().date()} to {returns_df.index.max().date()}")
    
    # Save to CSV
    output_file = OUTPUT_DIR / output_filename
    logger.info(f"\nSaving to {output_file}...")
    returns_df.to_csv(output_file)
    logger.info(f"✓ Saved {len(returns_df)} rows × {len(returns_df.columns)} columns to {output_file}")
    
    # Save metadata
    metadata = {
        'source': 'FMP API (corrected constituents)',
        'tickers': len(returns_df.columns),
        'date_range': {
            'start': str(returns_df.index.min().date()),
            'end': str(returns_df.index.max().date())
        },
        'total_observations': len(returns_df),
        'fetch_date': datetime.now().isoformat(),
        'constituent_file': str(CONSTITUENTS_FILE)
    }
    
    import json
    metadata_file = OUTPUT_DIR / output_filename.replace('.csv', '_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✓ Saved metadata to {metadata_file}")
    
    return returns_df


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch S&P 500 historical returns from FMP API (corrected constituents).")
    parser.add_argument('--start-date', type=str, default='1950-01-01',
                       help='Start date for filtering returns (YYYY-MM-DD). Default: 1950-01-01')
    parser.add_argument('--output', type=str, default='sp500_total_returns_corrected.csv',
                       help='Output filename. Default: sp500_total_returns_corrected.csv')
    args = parser.parse_args()
    
    # Get unique tickers from corrected constituent file
    tickers = get_unique_tickers_from_corrected_constituents()
    
    if not tickers:
        logger.error("No tickers found. Exiting.")
        return
    
    # Fetch returns
    returns_df = fetch_total_returns(tickers, start_date=args.start_date, output_filename=args.output)
    
    if not returns_df.empty:
        logger.info("\n" + "="*70)
        logger.info("✓ Complete!")
        logger.info("="*70)
    else:
        logger.error("Failed to fetch returns data.")


if __name__ == '__main__':
    main()

