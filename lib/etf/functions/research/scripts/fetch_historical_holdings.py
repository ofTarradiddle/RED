"""
Fetch Historical ETF Holdings for IWB (Russell 1000)
Uses FMP stable endpoint which supports date parameter for historical data.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import json

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.backtesting import FMPClient

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
ETF_SYMBOL = 'IWB'
OUTPUT_DIR = Path('./data/research/historical_holdings')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_holdings_for_date(fmp_client: FMPClient, symbol: str, date: str) -> list:
    """
    Fetch holdings for a specific date using stable endpoint.
    
    Args:
        fmp_client: FMPClient instance
        symbol: ETF symbol
        date: Date string (YYYY-MM-DD)
        
    Returns:
        List of holding dictionaries
    """
    try:
        # Use stable endpoint with date parameter
        endpoint = "stable/etf/holdings"
        params = {'symbol': symbol, 'date': date}
        
        holdings = fmp_client._get(endpoint, params)
        
        if isinstance(holdings, list):
            logger.info(f"✓ Retrieved {len(holdings)} holdings for {symbol} on {date}")
            return holdings
        else:
            logger.warning(f"Unexpected response format for {symbol} on {date}")
            return []
    except Exception as e:
        logger.error(f"Error fetching holdings for {symbol} on {date}: {e}")
        return []


def get_quarterly_dates(start_date: str, end_date: str) -> list:
    """
    Generate quarterly dates (end of quarter) between start and end dates.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        List of date strings (YYYY-MM-DD) for quarter ends
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    dates = []
    current = start
    
    # Get quarter end dates
    while current <= end:
        # Get end of quarter
        quarter_end = current + pd.offsets.QuarterEnd()
        if quarter_end <= end:
            dates.append(quarter_end.strftime('%Y-%m-%d'))
        current = current + pd.DateOffset(months=3)
    
    # Also include year-end dates
    year_ends = pd.date_range(start, end, freq='Y')  # 'Y' for year-end
    for ye in year_ends:
        date_str = ye.strftime('%Y-%m-%d')
        if date_str not in dates:
            dates.append(date_str)
    
    return sorted(dates)


def save_holdings(holdings: list, symbol: str, date: str, output_dir: Path):
    """
    Save holdings to JSON and CSV files.
    
    Args:
        holdings: List of holding dictionaries
        symbol: ETF symbol
        date: Date string
        output_dir: Output directory
    """
    if not holdings:
        return
    
    # Save as JSON
    json_file = output_dir / f"{symbol}_holdings_{date}.json"
    with open(json_file, 'w') as f:
        json.dump(holdings, f, indent=2)
    logger.info(f"✓ Saved JSON: {json_file}")
    
    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(holdings)
    
    # Extract key fields
    csv_data = []
    for item in holdings:
        csv_data.append({
            'date': date,
            'symbol': symbol,
            'asset': item.get('asset') or item.get('symbol', ''),
            'name': item.get('name', ''),
            'shares': item.get('sharesNumber', 0),
            'weight_pct': item.get('weightPercentage', 0),
            'market_value': item.get('marketValue', 0),
            'cusip': item.get('securityCusip', ''),
            'isin': item.get('isin', '')
        })
    
    csv_df = pd.DataFrame(csv_data)
    csv_file = output_dir / f"{symbol}_holdings_{date}.csv"
    csv_df.to_csv(csv_file, index=False)
    logger.info(f"✓ Saved CSV: {csv_file} ({len(csv_df)} holdings)")


def fetch_historical_holdings(symbol: str, start_date: str, end_date: str = None, 
                              quarterly: bool = True):
    """
    Fetch historical holdings for an ETF.
    
    Args:
        symbol: ETF symbol (e.g., 'IWB')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
        quarterly: If True, fetch quarterly dates; if False, fetch monthly
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info("="*70)
    logger.info(f"Fetching Historical Holdings for {symbol}")
    logger.info(f"Date Range: {start_date} to {end_date}")
    logger.info("="*70)
    
    # Initialize FMP client
    fmp = FMPClient(api_key=API_KEY)
    
    # Generate dates to fetch
    if quarterly:
        dates = get_quarterly_dates(start_date, end_date)
        logger.info(f"Fetching quarterly dates: {len(dates)} dates")
    else:
        # Monthly dates
        date_range = pd.date_range(start_date, end_date, freq='M')
        dates = [d.strftime('%Y-%m-%d') for d in date_range]
        logger.info(f"Fetching monthly dates: {len(dates)} dates")
    
    # Fetch holdings for each date
    summary = []
    for date in dates:
        logger.info(f"\nFetching holdings for {date}...")
        holdings = fetch_holdings_for_date(fmp, symbol, date)
        
        if holdings:
            save_holdings(holdings, symbol, date, OUTPUT_DIR)
            
            # Extract unique symbols
            symbols = set()
            for item in holdings:
                asset = item.get('asset') or item.get('symbol')
                if asset:
                    symbols.add(asset)
            
            summary.append({
                'date': date,
                'holdings_count': len(holdings),
                'unique_symbols': len(symbols),
                'status': 'success'
            })
        else:
            summary.append({
                'date': date,
                'holdings_count': 0,
                'unique_symbols': 0,
                'status': 'failed'
            })
    
    # Save summary
    summary_df = pd.DataFrame(summary)
    summary_file = OUTPUT_DIR / f"{symbol}_historical_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"\n✓ Summary saved to {summary_file}")
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("Summary")
    logger.info("="*70)
    print(summary_df.to_string(index=False))
    
    return summary_df


def main():
    """Main function to fetch IWB historical holdings."""
    
    # IWB launched May 15, 2000, so start from 2000-06-30 (first quarter end)
    start_date = '2000-06-30'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"Fetching historical holdings for {ETF_SYMBOL}")
    logger.info(f"From {start_date} to {end_date}")
    
    summary = fetch_historical_holdings(
        symbol=ETF_SYMBOL,
        start_date=start_date,
        end_date=end_date,
        quarterly=True  # Fetch quarterly to reduce API calls
    )
    
    logger.info(f"\n✓ Complete! Fetched {len(summary)} dates")
    logger.info(f"Files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

