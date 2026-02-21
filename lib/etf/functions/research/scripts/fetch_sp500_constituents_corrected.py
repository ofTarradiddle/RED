"""
Fetch Historical S&P 500 Constituents - Corrected Version
Constructs monthly constituent lists where each month's constituents are those
in the index on the LAST TRADING DAY of that month.

Logic:
- Constituents for year-month YYYY-MM are those in the index on the last trading day of YYYY-MM
- This list is used for portfolio construction during the next month (YYYY-MM+1)
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
import time
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path('./data/research/sp500_constituents')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_last_trading_day_of_month(year: int, month: int) -> pd.Timestamp:
    """
    Get the last trading day of a given month.
    Trading days are Monday-Friday, excluding holidays.
    
    Args:
        year: Year
        month: Month (1-12)
        
    Returns:
        Timestamp of last trading day
    """
    # Get last day of month
    if month == 12:
        last_day = pd.Timestamp(year=year + 1, month=1, day=1) - pd.Timedelta(days=1)
    else:
        last_day = pd.Timestamp(year=year, month=month + 1, day=1) - pd.Timedelta(days=1)
    
    # Go backwards to find last weekday (Mon-Fri)
    while last_day.weekday() >= 5:  # Saturday=5, Sunday=6
        last_day -= pd.Timedelta(days=1)
    
    return last_day.normalize()


def fetch_historical_constituents_from_fmp(start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
    """
    Fetch S&P 500 historical constituents from Financial Modeling Prep API.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        
    Returns:
        DataFrame with historical constituent changes
    """
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        logger.warning("FMP_API_KEY environment variable not set - cannot fetch from FMP API")
        return None
    
    try:
        base_url = "https://financialmodelingprep.com"
        endpoint = "stable/historical-sp500-constituent"
        url = f"{base_url}/{endpoint}"
        
        params = {'apikey': api_key}
        if start_date:
            params['from'] = start_date
        if end_date:
            params['to'] = end_date
        
        logger.info(f"Fetching from FMP API: {endpoint}")
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                logger.info(f"✓ Retrieved {len(df)} records from FMP")
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    logger.info(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
                    return df
        elif response.status_code == 403:
            logger.warning(f"FMP API returned 403 - may require higher tier subscription")
        else:
            logger.warning(f"FMP API returned status {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching from FMP API: {e}")
    
    return None


def build_constituents_by_last_trading_day(changes_df: pd.DataFrame, 
                                          start_year: int = 1990, 
                                          end_year: int = None) -> Dict[str, List[str]]:
    """
    Build constituent lists for each month based on last trading day.
    
    Logic:
    - For each year-month, get constituents as of the last trading day of that month
    - Process all changes up to and including that date
    - This list represents what was in the index at month-end
    - It will be used for portfolio construction during the next month
    
    Args:
        changes_df: DataFrame with historical changes (additions/removals)
        start_year: Start year (default 1990)
        end_year: End year (default: current year)
        
    Returns:
        Dictionary mapping 'YYYY-MM-DD' (last trading day) to list of tickers
    """
    if end_year is None:
        end_year = datetime.now().year
    
    logger.info("="*70)
    logger.info("Building Constituents by Last Trading Day")
    logger.info("="*70)
    logger.info(f"Processing years: {start_year} to {end_year}")
    logger.info("Logic: Constituents for YYYY-MM = index on last trading day of YYYY-MM")
    logger.info("="*70)
    
    # Sort changes by date
    changes_df = changes_df.sort_values('date')
    
    # Build constituents by last trading day of each month
    constituents_by_date = {}
    current_constituents = set()
    last_processed_date = None
    
    # Process each year-month
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Get last trading day of this month
            last_trading_day = get_last_trading_day_of_month(year, month)
            
            # Skip if in the future
            if last_trading_day > pd.Timestamp.now():
                continue
            
            # Apply all changes from last processed date up to and including the last trading day
            if last_processed_date is None:
                changes_to_apply = changes_df[changes_df['date'] <= last_trading_day]
            else:
                changes_to_apply = changes_df[
                    (changes_df['date'] > last_processed_date) & 
                    (changes_df['date'] <= last_trading_day)
                ]
            
            # Process changes chronologically
            for change_date in sorted(changes_to_apply['date'].unique()):
                day_changes = changes_df[changes_df['date'] == change_date]
                
                # Process additions (symbol column contains added tickers)
                if 'symbol' in day_changes.columns:
                    additions = day_changes[day_changes['symbol'].notna()]['symbol'].unique()
                    current_constituents.update(additions)
                
                # Process removals (removedTicker column contains removed tickers)
                if 'removedTicker' in day_changes.columns:
                    removals = day_changes[day_changes['removedTicker'].notna()]['removedTicker'].unique()
                    current_constituents.difference_update(removals)
            
            # Store constituents for this last trading day
            date_str = last_trading_day.strftime('%Y-%m-%d')
            constituents_by_date[date_str] = sorted(list(current_constituents.copy()))
            last_processed_date = last_trading_day
            
            if len(constituents_by_date) % 12 == 0:
                logger.info(f"  Processed {len(constituents_by_date)} months (up to {date_str})...")
    
    logger.info(f"✓ Built constituent lists for {len(constituents_by_date)} months")
    logger.info(f"  Date range: {min(constituents_by_date.keys())} to {max(constituents_by_date.keys())}")
    
    return constituents_by_date


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("S&P 500 Historical Constituents Fetcher (Corrected)")
    logger.info("="*70)
    logger.info("Logic: Constituents for YYYY-MM are those on the last trading day of YYYY-MM")
    logger.info("="*70)
    
    # Fetch historical changes from FMP
    changes_df = fetch_historical_constituents_from_fmp()
    
    if changes_df is None or changes_df.empty:
        logger.error("Failed to fetch historical constituents. Exiting.")
        return
    
    # Build constituents by last trading day (starting from 1970)
    constituents_by_date = build_constituents_by_last_trading_day(changes_df, start_year=1970)
    
    if not constituents_by_date:
        logger.error("Failed to build constituent lists. Exiting.")
        return
    
    # Save results to new file
    records = []
    for date_str, symbols in constituents_by_date.items():
        for symbol in symbols:
            records.append({
                'date': date_str,
                'symbol': symbol,
                'year_month': pd.to_datetime(date_str).strftime('%Y-%m')
            })
    
    output_df = pd.DataFrame(records)
    
    # Save to main file (overwrite existing)
    csv_file = OUTPUT_DIR / 'sp500_monthly_constituents.csv'
    output_df.to_csv(csv_file, index=False)
    logger.info(f"\n✓ Saved {len(output_df)} records to {csv_file}")
    
    # Save summary
    summary_records = []
    for date_str, symbols in sorted(constituents_by_date.items()):
        summary_records.append({
            'date': date_str,
            'year_month': pd.to_datetime(date_str).strftime('%Y-%m'),
            'count': len(symbols),
            'symbols': ','.join(symbols)
        })
    
    summary_df = pd.DataFrame(summary_records)
    summary_file = OUTPUT_DIR / 'sp500_monthly_summary.csv'
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"✓ Saved monthly summary to {summary_file}")
    
    # Report statistics
    logger.info(f"\n{'='*70}")
    logger.info("Summary Statistics")
    logger.info(f"{'='*70}")
    logger.info(f"Total months: {len(constituents_by_date)}")
    logger.info(f"Date range: {min(constituents_by_date.keys())} to {max(constituents_by_date.keys())}")
    logger.info(f"Average constituents per month: {sum(len(s) for s in constituents_by_date.values()) / len(constituents_by_date):.1f}")
    logger.info(f"Min constituents: {min(len(s) for s in constituents_by_date.values())}")
    logger.info(f"Max constituents: {max(len(s) for s in constituents_by_date.values())}")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()

