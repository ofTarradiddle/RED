"""
List tickers that are constituents but have no returns data for each rebalance period.

This helps identify which specific stocks are missing data during each month.
"""

import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data paths
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents_corrected.csv')
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
OUTPUT_DIR = Path('./data/research/sp500_backtest')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_monthly_constituents() -> Dict[str, List[str]]:
    """
    Load monthly S&P 500 constituents.
    
    Returns:
        Dictionary mapping date (YYYY-MM-DD) to list of tickers
    """
    logger.info("Loading monthly constituents...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return {}
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    
    # Group by date
    constituents_by_date = {}
    for date_str, group in df.groupby('date'):
        tickers = group['symbol'].tolist()
        constituents_by_date[date_str] = tickers
    
    logger.info(f"Loaded constituents for {len(constituents_by_date)} months")
    return constituents_by_date


def load_returns() -> pd.DataFrame:
    """
    Load returns data.
    
    Returns:
        DataFrame with date index and ticker columns
    """
    logger.info("Loading returns data...")
    
    if not RETURNS_FILE.exists():
        logger.error(f"Returns file not found: {RETURNS_FILE}")
        return pd.DataFrame()
    
    returns_df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    
    logger.info(f"Loaded returns for {len(returns_df.columns)} tickers")
    logger.info(f"Date range: {returns_df.index.min()} to {returns_df.index.max()}")
    
    return returns_df


def get_month_end_dates(start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[pd.Timestamp]:
    """Get month-end dates between start and end."""
    dates = pd.date_range(start=start_date, end=end_date, freq='M')
    return dates.tolist()


def find_missing_tickers_by_period(constituents_by_date: Dict[str, List[str]], 
                                   returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Find tickers that are constituents but have no returns data for each period.
    
    Args:
        constituents_by_date: Dictionary of date -> tickers
        returns_df: DataFrame of returns
        
    Returns:
        DataFrame with columns: rebalance_date, ticker, total_constituents, available_tickers, missing_tickers
    """
    logger.info("="*70)
    logger.info("Finding Missing Tickers by Period")
    logger.info("="*70)
    
    # Determine date range
    returns_start = returns_df.index.min()
    returns_end = returns_df.index.max()
    
    # Ensure timezone-naive
    if isinstance(returns_start, pd.Timestamp) and returns_start.tz is not None:
        returns_start = returns_start.tz_localize(None)
    if isinstance(returns_end, pd.Timestamp) and returns_end.tz is not None:
        returns_end = returns_end.tz_localize(None)
    
    requested_start = pd.to_datetime('1990-01-01')
    start_ts = max(pd.to_datetime(min(constituents_by_date.keys())), max(returns_start, requested_start))
    end_ts = min(pd.to_datetime(max(constituents_by_date.keys())), returns_end)
    
    # Get month-end rebalance dates
    rebalance_dates = get_month_end_dates(start_ts, end_ts)
    
    logger.info(f"Analyzing {len(rebalance_dates)} rebalance periods")
    logger.info(f"Date range: {rebalance_dates[0].date()} to {rebalance_dates[-1].date()}")
    
    missing_tickers_list = []
    
    for rebalance_date in rebalance_dates:
        rebalance_date_str = rebalance_date.strftime('%Y-%m-%d')
        rebalance_month = rebalance_date.strftime('%Y-%m')
        
        # Get constituents for this month
        month_constituents = None
        for date_str in sorted(constituents_by_date.keys(), reverse=True):
            date_ts = pd.to_datetime(date_str)
            if date_ts <= rebalance_date:
                month_constituents = constituents_by_date[date_str]
                break
        
        if not month_constituents:
            continue
        
        # Find which tickers have returns data
        available_tickers = [t for t in month_constituents if t in returns_df.columns]
        missing_tickers = [t for t in month_constituents if t not in returns_df.columns]
        
        # Add each missing ticker to the list
        for ticker in missing_tickers:
            missing_tickers_list.append({
                'rebalance_date': rebalance_date_str,
                'rebalance_month': rebalance_month,
                'ticker': ticker,
                'total_constituents': len(month_constituents),
                'available_tickers': len(available_tickers),
                'missing_tickers': len(missing_tickers),
                'pct_missing': (len(missing_tickers) / len(month_constituents) * 100) if month_constituents else 0
            })
    
    missing_df = pd.DataFrame(missing_tickers_list)
    
    logger.info(f"\nFound {len(missing_df)} missing ticker-period combinations")
    logger.info(f"Unique missing tickers: {missing_df['ticker'].nunique()}")
    logger.info(f"Periods with missing tickers: {missing_df['rebalance_month'].nunique()}")
    
    return missing_df


def create_summary_statistics(missing_df: pd.DataFrame):
    """Create summary statistics about missing tickers."""
    logger.info("\n" + "="*70)
    logger.info("Missing Tickers Summary Statistics")
    logger.info("="*70)
    
    # Tickers missing most frequently
    ticker_counts = missing_df['ticker'].value_counts()
    logger.info(f"\nTop 20 Tickers Missing Most Frequently:")
    for ticker, count in ticker_counts.head(20).items():
        logger.info(f"  {ticker}: {count} periods ({count / missing_df['rebalance_month'].nunique() * 100:.1f}% of periods)")
    
    # Periods with most missing tickers
    period_counts = missing_df.groupby('rebalance_month').agg({
        'ticker': 'count',
        'pct_missing': 'first'
    }).sort_values('ticker', ascending=False)
    
    logger.info(f"\nTop 20 Periods with Most Missing Tickers:")
    for period, row in period_counts.head(20).iterrows():
        logger.info(f"  {period}: {row['ticker']} missing tickers ({row['pct_missing']:.1f}% of constituents)")
    
    # Summary by year
    missing_df['year'] = pd.to_datetime(missing_df['rebalance_month'] + '-01').dt.year
    yearly_summary = missing_df.groupby('year').agg({
        'ticker': 'count',
        'rebalance_month': 'nunique'
    })
    yearly_summary['avg_missing_per_period'] = yearly_summary['ticker'] / yearly_summary['rebalance_month']
    
    logger.info(f"\nMissing Tickers by Year:")
    for year, row in yearly_summary.iterrows():
        logger.info(f"  {year}: {row['ticker']} total missing, {row['avg_missing_per_period']:.1f} avg per period, {row['rebalance_month']} periods")


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("Missing Tickers by Period Analysis")
    logger.info("="*70)
    
    # Load data
    constituents_by_date = load_monthly_constituents()
    if not constituents_by_date:
        logger.error("Failed to load constituents. Exiting.")
        return
    
    returns_df = load_returns()
    if returns_df.empty:
        logger.error("Failed to load returns. Exiting.")
        return
    
    # Find missing tickers
    missing_df = find_missing_tickers_by_period(constituents_by_date, returns_df)
    
    if missing_df.empty:
        logger.info("No missing tickers found!")
        return
    
    # Create summary statistics
    create_summary_statistics(missing_df)
    
    # Save detailed list
    output_file = OUTPUT_DIR / 'missing_tickers_by_period.csv'
    missing_df.to_csv(output_file, index=False)
    logger.info(f"\n✓ Saved missing tickers list to {output_file}")
    
    # Save summary by ticker
    ticker_summary = missing_df.groupby('ticker').agg({
        'rebalance_month': ['count', lambda x: ', '.join(sorted(x.unique())[:10])],  # First 10 periods
        'pct_missing': 'mean'
    }).reset_index()
    ticker_summary.columns = ['ticker', 'periods_missing', 'sample_periods', 'avg_pct_missing']
    ticker_summary = ticker_summary.sort_values('periods_missing', ascending=False)
    
    ticker_summary_file = OUTPUT_DIR / 'missing_tickers_summary.csv'
    ticker_summary.to_csv(ticker_summary_file, index=False)
    logger.info(f"✓ Saved ticker summary to {ticker_summary_file}")
    
    # Save summary by period
    period_summary = missing_df.groupby('rebalance_month').agg({
        'ticker': ['count', lambda x: ', '.join(sorted(x.unique())[:20])],  # First 20 tickers
        'pct_missing': 'first',
        'total_constituents': 'first',
        'available_tickers': 'first'
    }).reset_index()
    period_summary.columns = ['rebalance_month', 'missing_count', 'sample_tickers', 'pct_missing', 'total_constituents', 'available_tickers']
    period_summary = period_summary.sort_values('missing_count', ascending=False)
    
    period_summary_file = OUTPUT_DIR / 'missing_tickers_by_period_summary.csv'
    period_summary.to_csv(period_summary_file, index=False)
    logger.info(f"✓ Saved period summary to {period_summary_file}")
    
    logger.info("\n" + "="*70)
    logger.info("Analysis Complete!")
    logger.info("="*70)


if __name__ == '__main__':
    main()

