"""
Fetch Historical S&P 500 Constituents
Constructs monthly constituent lists keyed by end-of-month date and symbol.

Data Sources (in order of preference):
1. Financial Modeling Prep (FMP) API - if available with historical data
2. EOD Historical Data API - up to 12 years of history
3. Wikipedia - current constituents only
4. CSV files from public sources (Analyzing Alpha, etc.)

Historical Coverage:
- EODHD: Up to 12 years
- WRDS/CRSP: Back to 1957 (requires subscription)
- FMP: Varies by subscription tier
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path('./data/research/sp500_constituents')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SP500ConstituentsFetcher:
    """Fetcher for historical S&P 500 constituent data."""
    
    def __init__(self):
        """Initialize the fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'REDI Research redi@example.com',
            'Accept': 'application/json'
        })
        self.request_delay = 0.1
    
    def get_historical_constituents(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch historical S&P 500 constituents.
        
        Uses multiple data sources to get historical constituent data.
        
        Args:
            start_date: Start date (YYYY-MM-DD), defaults to earliest available
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            DataFrame with columns: date, symbol, name (if available)
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info("="*70)
        logger.info("Fetching Historical S&P 500 Constituents")
        logger.info(f"Date Range: {start_date or 'earliest'} to {end_date}")
        logger.info("="*70)
        
        # Try multiple data sources (order matters - try APIs first, then free sources)
        sources = [
            self._fetch_from_fmp,
            self._fetch_from_eodhd,
            self._fetch_from_wikipedia,
            self._fetch_from_alphavantage,
        ]
        
        all_data = []
        earliest_date = None
        latest_date = None
        
        for source_func in sources:
            try:
                logger.info(f"\nTrying data source: {source_func.__name__}")
                data = source_func(start_date, end_date)
                
                if data is not None and not data.empty:
                    logger.info(f"  ✓ Retrieved {len(data)} records")
                    if 'date' in data.columns:
                        dates = pd.to_datetime(data['date'])
                        source_earliest = dates.min()
                        source_latest = dates.max()
                        
                        if earliest_date is None or source_earliest < earliest_date:
                            earliest_date = source_earliest
                        if latest_date is None or source_latest > latest_date:
                            latest_date = source_latest
                        
                        logger.info(f"  Date range: {source_earliest.date()} to {source_latest.date()}")
                    
                    all_data.append(data)
            except Exception as e:
                logger.warning(f"  ✗ Source {source_func.__name__} failed: {e}")
                continue
        
        if all_data:
            # Combine all sources
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Remove duplicates
            if 'date' in combined_df.columns and 'symbol' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['date', 'symbol'], keep='first')
            
            # Sort by date
            if 'date' in combined_df.columns:
                combined_df['date'] = pd.to_datetime(combined_df['date'])
                combined_df = combined_df.sort_values('date')
            
            logger.info(f"\n✓ Combined data: {len(combined_df)} records")
            if earliest_date and latest_date:
                logger.info(f"  Total date range: {earliest_date.date()} to {latest_date.date()}")
            
            return combined_df
        else:
            logger.warning("No data retrieved from any source")
            return pd.DataFrame()
    
    def _fetch_from_fmp(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch S&P 500 historical constituents from Financial Modeling Prep API.
        """
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.debug("FMP_API_KEY environment variable not set - skipping FMP API")
            return None
        
        try:
            base_url = "https://financialmodelingprep.com"
            
            # Try historical S&P 500 constituents endpoint
            # The correct endpoint is: stable/historical-sp500-constituent
            endpoints_to_try = [
                "stable/historical-sp500-constituent",  # Correct endpoint - goes back to 1957!
                "api/v3/historical/sp500_constituent",
                "api/v3/sp500_constituent",
                "stable/sp500-constituents",
                "api/v4/sp500-constituents",
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    url = f"{base_url}/{endpoint}"
                    params = {'apikey': api_key}
                    
                    if start_date:
                        params['from'] = start_date
                    if end_date:
                        params['to'] = end_date
                    
                    logger.info(f"  Trying FMP endpoint: {endpoint}")
                    time.sleep(self.request_delay)
                    response = self.session.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            df = pd.DataFrame(data)
                            logger.info(f"  ✓ Retrieved {len(df)} records from FMP")
                            
                            # The historical-sp500-constituent endpoint returns changes (additions/removals)
                            # We need to process this to build the full constituent list over time
                            if 'date' in df.columns and 'symbol' in df.columns:
                                # Check date range
                                dates = pd.to_datetime(df['date'])
                                logger.info(f"  Date range: {dates.min().date()} to {dates.max().date()}")
                                logger.info(f"  ✓ Historical data available from {dates.min().date()}!")
                                
                                # Return the change data - we'll process it in construct_monthly_constituents
                                return df
                            elif 'symbol' in df.columns:
                                # Current constituents only
                                df['date'] = datetime.now().date()
                                return df[['date', 'symbol']]
                    elif response.status_code == 403:
                        logger.debug(f"  FMP endpoint {endpoint} requires higher tier")
                    else:
                        logger.debug(f"  FMP endpoint {endpoint} returned {response.status_code}")
                except Exception as e:
                    logger.debug(f"  FMP endpoint {endpoint} error: {e}")
                    continue
        except Exception as e:
            logger.debug(f"FMP fetch error: {e}")
        
        return None
    
    def _fetch_from_eodhd(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch from EOD Historical Data API (up to 12 years of history).
        """
        api_key = os.getenv('EODHD_API_KEY')
        if not api_key:
            logger.debug("EODHD API key not found - skipping")
            return None
        
        try:
            # EODHD S&P 500 historical constituents endpoint
            url = "https://eodhistoricaldata.com/api/index-constituents"
            params = {
                'SPX.INDX': '',
                'api_token': api_key,
                'fmt': 'json'
            }
            
            logger.info(f"  Fetching from EODHD...")
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list):
                    df = pd.DataFrame(data)
                    logger.info(f"  ✓ Retrieved {len(df)} records from EODHD")
                    
                    # EODHD format may vary - normalize
                    if 'Code' in df.columns:
                        df['symbol'] = df['Code']
                    if 'Date' in df.columns:
                        df['date'] = pd.to_datetime(df['Date'])
                    elif 'date' not in df.columns:
                        df['date'] = datetime.now().date()
                    
                    return df[['date', 'symbol']] if 'date' in df.columns and 'symbol' in df.columns else None
        except Exception as e:
            logger.debug(f"EODHD fetch error: {e}")
        
        return None
    
    def _fetch_from_wikipedia(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch S&P 500 historical constituents from Wikipedia.
        
        Wikipedia has a list of S&P 500 companies with addition/removal dates.
        """
        try:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            logger.info(f"  Fetching from Wikipedia...")
            
            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                # Parse HTML table
                tables = pd.read_html(response.text)
                
                # Find the main constituents table
                for table in tables:
                    if 'Symbol' in table.columns and len(table) > 100:  # S&P 500 should have ~500 companies
                        logger.info(f"  ✓ Found constituents table with {len(table)} companies")
                        
                        # Get current constituents
                        current_constituents = table[['Symbol', 'Security']].copy()
                        current_constituents.columns = ['symbol', 'name']
                        current_constituents['date'] = datetime.now().date()
                        
                        return current_constituents
        except Exception as e:
            logger.debug(f"Wikipedia fetch error: {e}")
        
        return None
    
    def _fetch_from_spindices(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch from S&P Dow Jones Indices (may require API key or have limited access).
        """
        # S&P Indices typically requires subscription/API key
        # This is a placeholder for future implementation
        logger.debug("S&P Indices API requires subscription - skipping")
        return None
    
    def _fetch_from_alphavantage(self, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch from Alpha Vantage (if API key available).
        """
        api_key = os.getenv('ALPHAVANTAGE_API_KEY')
        if not api_key:
            logger.debug("Alpha Vantage API key not found - skipping")
            return None
        
        # Alpha Vantage may have S&P 500 data
        # This is a placeholder
        logger.debug("Alpha Vantage S&P 500 endpoint not yet implemented")
        return None
    
    def construct_monthly_constituents(self, constituents_df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Construct monthly constituent lists keyed by end-of-month date.
        
        The FMP historical-sp500-constituent endpoint returns changes (additions/removals),
        so we need to build the full constituent list over time by tracking these changes.
        
        Args:
            constituents_df: DataFrame with date, symbol, and optionally removedTicker columns
            
        Returns:
            Dictionary mapping end-of-month dates (YYYY-MM-DD) to list of symbols
        """
        if constituents_df.empty or 'date' not in constituents_df.columns:
            logger.warning("Invalid constituents DataFrame")
            return {}
        
        # Ensure date is datetime
        constituents_df = constituents_df.copy()
        constituents_df['date'] = pd.to_datetime(constituents_df['date'])
        constituents_df = constituents_df.sort_values('date')
        
        logger.info(f"\nConstructing monthly constituent lists from {len(constituents_df)} change records...")
        
        # Check if this is change data (has 'removedTicker' or 'symbol' for additions)
        is_change_data = 'removedTicker' in constituents_df.columns or 'symbol' in constituents_df.columns
        
        if is_change_data:
            # Process change data to build full constituent lists over time
            # Start with initial constituents (March 4, 1957)
            current_constituents = set()
            
            # Get all unique dates
            all_dates = sorted(constituents_df['date'].unique())
            logger.info(f"  Processing {len(all_dates)} unique change dates from {all_dates[0].date()} to {all_dates[-1].date()}")
            
            # Build constituent list over time
            constituents_by_date = {}
            
            for date in all_dates:
                # Get all changes on this date
                changes = constituents_df[constituents_df['date'] == date]
                
                # Process additions
                if 'symbol' in changes.columns:
                    additions = changes[changes['symbol'].notna()]['symbol'].unique()
                    current_constituents.update(additions)
                
                # Process removals
                if 'removedTicker' in changes.columns:
                    removals = changes[changes['removedTicker'].notna()]['removedTicker'].unique()
                    current_constituents.difference_update(removals)
                
                # Store current constituents for this date
                constituents_by_date[date] = sorted(current_constituents.copy())
            
            logger.info(f"  Built constituent lists for {len(constituents_by_date)} dates")
            logger.info(f"  Final count: {len(current_constituents)} constituents")
        else:
            # Simple case: just date and symbol
            if 'symbol' not in constituents_df.columns:
                logger.warning("No symbol column found")
                return {}
            
            constituents_by_date = {}
            for date in sorted(constituents_df['date'].unique()):
                symbols = constituents_df[constituents_df['date'] == date]['symbol'].unique().tolist()
                constituents_by_date[pd.to_datetime(date)] = sorted(symbols)
        
        # Now convert to monthly lists (end of month)
        monthly_constituents = {}
        
        # Generate monthly end dates from earliest to latest
        if constituents_by_date:
            earliest_date = min(constituents_by_date.keys())
            latest_date = max(constituents_by_date.keys())
            
            # Create monthly end dates
            current_date = earliest_date.replace(day=1)
            end_date = latest_date
            
            while current_date <= end_date:
                # Get last day of month
                if current_date.month == 12:
                    month_end = current_date.replace(day=31)
                else:
                    month_end = (current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1))
                
                month_key = month_end.strftime('%Y-%m-%d')
                
                # Find the most recent constituent list on or before this month end
                available_dates = [d for d in constituents_by_date.keys() if d <= month_end]
                if available_dates:
                    latest_available = max(available_dates)
                    monthly_constituents[month_key] = constituents_by_date[latest_available]
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1, day=1)
        
        logger.info(f"✓ Constructed {len(monthly_constituents)} monthly constituent lists")
        
        # Show date range
        if monthly_constituents:
            dates = sorted(monthly_constituents.keys())
            logger.info(f"  Date range: {dates[0]} to {dates[-1]}")
            avg_count = sum(len(v) for v in monthly_constituents.values()) / len(monthly_constituents)
            logger.info(f"  Average constituents per month: {avg_count:.0f}")
        
        return monthly_constituents


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("S&P 500 Historical Constituents Fetcher")
    logger.info("="*70)
    
    fetcher = SP500ConstituentsFetcher()
    
    # Fetch historical constituents
    constituents_df = fetcher.get_historical_constituents()
    
    if constituents_df.empty:
        logger.error("No constituents data retrieved")
        return
    
    # Construct monthly lists
    monthly_constituents = fetcher.construct_monthly_constituents(constituents_df)
    
    if not monthly_constituents:
        logger.warning("No monthly constituents constructed")
        return
    
    # Save results
    # Save as CSV: date, symbol
    records = []
    for date, symbols in monthly_constituents.items():
        for symbol in symbols:
            records.append({'date': date, 'symbol': symbol})
    
    output_df = pd.DataFrame(records)
    csv_file = OUTPUT_DIR / 'sp500_monthly_constituents.csv'
    output_df.to_csv(csv_file, index=False)
    logger.info(f"\n✓ Saved {len(output_df)} records to {csv_file}")
    
    # Save monthly summary
    summary_records = []
    for date, symbols in monthly_constituents.items():
        summary_records.append({
            'date': date,
            'count': len(symbols),
            'symbols': ','.join(symbols)
        })
    
    summary_df = pd.DataFrame(summary_records)
    summary_file = OUTPUT_DIR / 'sp500_monthly_summary.csv'
    summary_df.to_csv(summary_file, index=False)
    logger.info(f"✓ Saved monthly summary to {summary_file}")
    
    # Report date range
    dates = sorted(monthly_constituents.keys())
    logger.info(f"\n{'='*70}")
    logger.info(f"Date Range: {dates[0]} to {dates[-1]}")
    logger.info(f"Total months: {len(dates)}")
    logger.info(f"{'='*70}")


if __name__ == "__main__":
    main()

