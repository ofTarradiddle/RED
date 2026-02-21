"""
Fetch Historical Russell 1000 Constituents via IWB ETF Holdings
Uses FMP API v4 endpoint: api/v4/etf-holdings?symbol=IWB&date=YYYY-MM-DD
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
import json
import time
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv('FMP_API_KEY')
if not API_KEY:
    raise ValueError("FMP_API_KEY environment variable is required. Set it in your .env file or export it.")
BASE_URL = "https://financialmodelingprep.com"
IWB_SYMBOL = "IWB"  # iShares Russell 1000 ETF
IWB_LAUNCH_DATE = "2000-05-15"  # IWB launched May 15, 2000

# Output directories
OUTPUT_DIR = Path('./data/research/russell1000_constituents')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_etf_holdings_stable(symbol: str, date: str, api_key: str) -> Optional[List[Dict]]:
    """
    Fetch ETF holdings using FMP stable endpoint.
    Note: This endpoint may return current holdings even for historical dates.
    
    Args:
        symbol: ETF symbol (e.g., "IWB")
        date: Date string (YYYY-MM-DD)
        api_key: FMP API key
        
    Returns:
        List of holding dictionaries or None if error
    """
    # Try stable endpoint first
    endpoint = f"{BASE_URL}/stable/etf/holdings"
    params = {
        'symbol': symbol,
        'date': date,
        'apikey': api_key
    }
    
    try:
        logger.debug(f"Fetching {endpoint} with params: symbol={symbol}, date={date}")
        response = requests.get(endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data
            elif isinstance(data, dict) and 'Error Message' in data:
                logger.warning(f"API error for {symbol} on {date}: {data['Error Message']}")
                return None
            else:
                logger.warning(f"Empty or unexpected response for {symbol} on {date}")
                return None
        elif response.status_code == 403:
            logger.warning(f"403 Forbidden for {symbol} on {date} - endpoint may require higher tier")
            return None
        else:
            logger.warning(f"HTTP {response.status_code} for {symbol} on {date}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching holdings for {symbol} on {date}: {e}")
        return None


def get_quarterly_dates(start_date: str, end_date: str = None) -> List[str]:
    """
    Generate quarterly end dates (last trading day of quarter).
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (defaults to today)
        
    Returns:
        List of date strings (YYYY-MM-DD)
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Generate quarterly dates
    dates = pd.date_range(start=start, end=end, freq='Q')
    
    # Convert to last trading day of quarter (approximate - use last day of month)
    quarterly_dates = []
    for date in dates:
        # Get last day of the quarter month
        last_day = date + pd.offsets.QuarterEnd()
        quarterly_dates.append(last_day.strftime('%Y-%m-%d'))
    
    return quarterly_dates


def fetch_historical_holdings(symbol: str, start_date: str, end_date: str = None,
                              api_key: str = None) -> Dict[str, List[str]]:
    """
    Fetch historical ETF holdings and construct monthly constituent lists.
    
    Args:
        symbol: ETF symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (defaults to today)
        api_key: FMP API key
        
    Returns:
        Dictionary mapping dates (YYYY-MM-DD) to lists of ticker symbols
    """
    logger.info("="*70)
    logger.info(f"Fetching Historical {symbol} Holdings")
    logger.info("="*70)
    
    if api_key is None:
        api_key = API_KEY
    
    # Get quarterly dates
    quarterly_dates = get_quarterly_dates(start_date, end_date)
    logger.info(f"Fetching holdings for {len(quarterly_dates)} quarterly dates")
    logger.info(f"Date range: {quarterly_dates[0]} to {quarterly_dates[-1]}")
    
    # Fetch holdings for each date
    holdings_by_date = {}
    successful = 0
    failed = 0
    
    for i, date in enumerate(quarterly_dates, 1):
        percent = (i / len(quarterly_dates)) * 100
        logger.info(f"\n[{i}/{len(quarterly_dates)}] ({percent:.1f}%) Fetching {date}...")
        
        holdings_data = get_etf_holdings_stable(symbol, date, api_key)
        
        if holdings_data and len(holdings_data) > 0:
            # Extract ticker symbols from holdings
            # Try different field names that FMP might use
            tickers = []
            for holding in holdings_data:
                ticker = (holding.get('symbol') or 
                         holding.get('ticker') or 
                         holding.get('assetSymbol') or
                         holding.get('asset'))
                if ticker and ticker not in tickers:
                    tickers.append(ticker)
            
            if tickers:
                holdings_by_date[date] = sorted(tickers)
                successful += 1
                logger.info(f"  ✓ Retrieved {len(tickers)} holdings for {date}")
            else:
                failed += 1
                logger.warning(f"  ✗ No tickers found in holdings data for {date}")
        else:
            failed += 1
            logger.warning(f"  ✗ No holdings data retrieved for {date}")
        
        # Rate limiting
        time.sleep(0.5)
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Fetching Complete")
    logger.info(f"  Successful: {successful}/{len(quarterly_dates)}")
    logger.info(f"  Failed: {failed}/{len(quarterly_dates)}")
    logger.info(f"{'='*70}")
    
    return holdings_by_date


def construct_monthly_constituents(holdings_by_date: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Construct monthly constituent lists from quarterly holdings.
    
    For months between quarters, use the most recent quarter's holdings.
    
    Args:
        holdings_by_date: Dictionary of date -> tickers from quarterly fetches
        
    Returns:
        Dictionary mapping end-of-month dates to ticker lists
    """
    logger.info("="*70)
    logger.info("Constructing Monthly Constituent Lists")
    logger.info("="*70)
    
    if not holdings_by_date:
        logger.warning("No holdings data to process")
        return {}
    
    # Get date range
    dates = sorted(holdings_by_date.keys())
    start_date = pd.to_datetime(dates[0])
    end_date = pd.to_datetime(dates[-1])
    
    # Generate all month-end dates
    monthly_dates = pd.date_range(start=start_date, end=end_date, freq='M')
    
    monthly_constituents = {}
    last_known_holdings = None
    
    for month_end in monthly_dates:
        month_str = month_end.strftime('%Y-%m-%d')
        
        # Find the most recent quarterly holdings before or on this month
        for q_date in reversed(dates):
            q_datetime = pd.to_datetime(q_date)
            if q_datetime <= month_end:
                last_known_holdings = holdings_by_date[q_date]
                break
        
        if last_known_holdings:
            monthly_constituents[month_str] = last_known_holdings
    
    logger.info(f"Constructed {len(monthly_constituents)} monthly constituent lists")
    logger.info(f"Date range: {min(monthly_constituents.keys())} to {max(monthly_constituents.keys())}")
    
    return monthly_constituents


def save_constituents(holdings_by_date: Dict[str, List[str]], 
                     monthly_constituents: Dict[str, List[str]],
                     symbol: str):
    """
    Save constituent data to CSV files.
    
    Args:
        holdings_by_date: Quarterly holdings
        monthly_constituents: Monthly constituent lists
        symbol: ETF symbol
    """
    logger.info("="*70)
    logger.info("Saving Constituent Data")
    logger.info("="*70)
    
    # Save quarterly holdings (raw data)
    quarterly_records = []
    for date, tickers in holdings_by_date.items():
        for ticker in tickers:
            quarterly_records.append({'date': date, 'symbol': ticker})
    
    if quarterly_records:
        quarterly_df = pd.DataFrame(quarterly_records)
        quarterly_file = OUTPUT_DIR / f'{symbol}_quarterly_holdings.csv'
        quarterly_df.to_csv(quarterly_file, index=False)
        logger.info(f"✓ Saved {len(quarterly_records)} quarterly holdings to {quarterly_file}")
    
    # Save monthly constituents (expanded list)
    monthly_records = []
    for date, tickers in monthly_constituents.items():
        for ticker in tickers:
            monthly_records.append({'date': date, 'symbol': ticker})
    
    if monthly_records:
        monthly_df = pd.DataFrame(monthly_records)
        monthly_file = OUTPUT_DIR / f'{symbol}_monthly_constituents.csv'
        monthly_df.to_csv(monthly_file, index=False)
        logger.info(f"✓ Saved {len(monthly_records)} monthly constituents to {monthly_file}")
    
    # Save summary (count per date)
    summary_records = []
    for date, tickers in monthly_constituents.items():
        summary_records.append({
            'date': date,
            'count': len(tickers),
            'symbols': ','.join(tickers)
        })
    
    if summary_records:
        summary_df = pd.DataFrame(summary_records)
        summary_file = OUTPUT_DIR / f'{symbol}_monthly_summary.csv'
        summary_df.to_csv(summary_file, index=False)
        logger.info(f"✓ Saved monthly summary to {summary_file}")
    
    # Save metadata
    metadata = {
        'symbol': symbol,
        'quarterly_dates': len(holdings_by_date),
        'monthly_dates': len(monthly_constituents),
        'unique_tickers': len(set(t for tickers in monthly_constituents.values() for t in tickers)),
        'date_range': {
            'start': min(monthly_constituents.keys()) if monthly_constituents else None,
            'end': max(monthly_constituents.keys()) if monthly_constituents else None
        },
        'last_updated': datetime.now().isoformat()
    }
    
    metadata_file = OUTPUT_DIR / f'{symbol}_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"✓ Saved metadata to {metadata_file}")


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("Russell 1000 Historical Constituents Fetcher")
    logger.info("="*70)
    
    # Fetch historical holdings
    holdings_by_date = fetch_historical_holdings(
        symbol=IWB_SYMBOL,
        start_date=IWB_LAUNCH_DATE,
        end_date=None,
        api_key=API_KEY
    )
    
    if not holdings_by_date:
        logger.error("No holdings data retrieved. Exiting.")
        return
    
    # Construct monthly constituents
    monthly_constituents = construct_monthly_constituents(holdings_by_date)
    
    if not monthly_constituents:
        logger.error("No monthly constituents constructed. Exiting.")
        return
    
    # Save data
    save_constituents(holdings_by_date, monthly_constituents, IWB_SYMBOL)
    
    logger.info("\n" + "="*70)
    logger.info("Complete!")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("="*70)


if __name__ == "__main__":
    main()

