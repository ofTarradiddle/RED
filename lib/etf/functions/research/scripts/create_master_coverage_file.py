"""
Create Master Coverage File
For each year-month (rows), shows tickers (columns) that were constituents
and their returns in the NEXT month.

Logic:
- Row: YYYY-MM (constituent date, e.g., 1970-01 = constituents at end of Jan 1970)
- Column: Ticker symbol
- Value: Monthly return for that ticker in the NEXT month (Feb 1970 in this example)
- Only filled if ticker was a constituent in that yr-mo
"""

import sys
from pathlib import Path
import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents.csv')
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
OUTPUT_FILE = Path('./data/research/sp500_backtest/master_coverage_file.csv')


def load_monthly_constituents() -> Dict[str, List[str]]:
    """Load monthly S&P 500 constituents."""
    logger.info("Loading monthly constituents...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return {}
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Group by date
    constituents_by_date = {}
    for date, group in df.groupby('date'):
        date_str = date.strftime('%Y-%m-%d')
        constituents_by_date[date_str] = sorted(group['symbol'].unique().tolist())
    
    logger.info(f"Loaded constituents for {len(constituents_by_date)} months")
    logger.info(f"Date range: {min(constituents_by_date.keys())} to {max(constituents_by_date.keys())}")
    
    return constituents_by_date


def load_returns() -> pd.DataFrame:
    """Load returns data."""
    logger.info("Loading returns data...")
    
    if not RETURNS_FILE.exists():
        logger.error(f"Returns file not found: {RETURNS_FILE}")
        return pd.DataFrame()
    
    df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    
    # Ensure timezone-naive
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    logger.info(f"Loaded returns for {len(df.columns)} tickers")
    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    logger.info(f"Total observations: {len(df)}")
    
    return df


def calculate_monthly_returns(daily_returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate monthly returns from daily returns.
    
    Args:
        daily_returns: DataFrame with daily returns (index: dates, columns: tickers)
        
    Returns:
        DataFrame with monthly returns (index: year-month strings, columns: tickers)
    """
    logger.info("Calculating monthly returns from daily returns...")
    
    # Group by year-month and calculate cumulative return for each month
    monthly_returns = []
    monthly_dates = []
    
    for year_month, group in daily_returns.groupby([daily_returns.index.year, daily_returns.index.month]):
        year, month = year_month
        
        # Calculate cumulative return for the month: (1 + r1) * (1 + r2) * ... - 1
        month_cumulative = (1 + group).prod() - 1
        
        # Store with year-month string as index
        monthly_returns.append(month_cumulative)
        monthly_dates.append(f"{year}-{month:02d}")
    
    monthly_df = pd.DataFrame(monthly_returns, index=monthly_dates)
    monthly_df.index.name = 'year_month'
    
    logger.info(f"Calculated monthly returns for {len(monthly_df)} months")
    logger.info(f"Date range: {monthly_df.index.min()} to {monthly_df.index.max()}")
    
    return monthly_df


def create_coverage_file(constituents_by_date: Dict[str, List[str]], 
                        returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create master coverage file.
    
    Args:
        constituents_by_date: Dictionary mapping date strings to list of tickers
        returns_df: DataFrame with daily returns
        
    Returns:
        DataFrame with yr-mo as rows, tickers as columns, next-month returns as values
    """
    logger.info("="*70)
    logger.info("Creating Master Coverage File")
    logger.info("="*70)
    
    # Calculate monthly returns
    monthly_returns = calculate_monthly_returns(returns_df)
    
    # Get all unique tickers across all constituents
    all_tickers = set()
    for tickers in constituents_by_date.values():
        all_tickers.update(tickers)
    all_tickers = sorted(list(all_tickers))
    
    logger.info(f"Total unique tickers across all constituents: {len(all_tickers)}")
    
    # Create coverage DataFrame
    coverage_records = []
    
    # Sort constituent dates and filter for 1995 and after
    sorted_dates = sorted(constituents_by_date.keys())
    filtered_dates = [d for d in sorted_dates if pd.to_datetime(d).year >= 1995]
    
    logger.info(f"Filtering to 1995 and after: {len(filtered_dates)} months (from {len(sorted_dates)} total)")
    
    for i, const_date_str in enumerate(filtered_dates):
        const_date = pd.to_datetime(const_date_str)
        year_month = const_date.strftime('%Y-%m')
        
        # Get next month for returns
        if const_date.month == 12:
            next_year = const_date.year + 1
            next_month = 1
        else:
            next_year = const_date.year
            next_month = const_date.month + 1
        
        next_year_month = f"{next_year}-{next_month:02d}"
        
        # Get constituents for this month
        constituents = constituents_by_date[const_date_str]
        
        # Create record for this year-month
        record = {'year_month': year_month}
        
        # For each ticker, fill in next month's return if it was a constituent
        for ticker in all_tickers:
            if ticker in constituents:
                # This ticker was a constituent, get its return for next month
                if next_year_month in monthly_returns.index and ticker in monthly_returns.columns:
                    return_value = monthly_returns.loc[next_year_month, ticker]
                    # Check if valid (not NaN, not inf)
                    if pd.notna(return_value) and np.isfinite(return_value):
                        record[ticker] = return_value
                    else:
                        # Was a constituent but return data is missing
                        record[ticker] = np.nan
                else:
                    # Next month's return not available (was a constituent but missing data)
                    record[ticker] = np.nan
            else:
                # Not a constituent this month, mark with "x"
                record[ticker] = "x"
        
        coverage_records.append(record)
        
        if (i + 1) % 50 == 0:
            logger.info(f"  Processed {i + 1}/{len(sorted_dates)} months...")
    
    # Create DataFrame
    coverage_df = pd.DataFrame(coverage_records)
    coverage_df = coverage_df.set_index('year_month')
    
    logger.info(f"✓ Created coverage file with {len(coverage_df)} rows and {len(coverage_df.columns)} columns")
    
    # Calculate percent missing returns for each year-month
    logger.info("Calculating percent missing returns for each year-month...")
    pct_missing = []
    for idx in coverage_df.index:
        row = coverage_df.loc[idx]
        # Count constituents (not "x")
        is_constituent = row != "x"
        total_constituents = is_constituent.sum()
        
        if total_constituents > 0:
            # Count missing returns (NaN values where ticker was a constituent)
            missing_returns = row[is_constituent].isna().sum()
            pct = (missing_returns / total_constituents) * 100
        else:
            pct = 0.0
        
        pct_missing.append(pct)
    
    # Add as first column (after index)
    coverage_df.insert(0, 'pct_missing_returns', pct_missing)
    
    # Calculate statistics
    total_cells = (len(coverage_df) * (len(coverage_df.columns) - 1))  # Exclude pct_missing_returns column
    filled_cells = coverage_df.drop('pct_missing_returns', axis=1).notna().sum().sum()
    pct_filled = (filled_cells / total_cells) * 100
    
    logger.info(f"  Total cells: {total_cells:,}")
    logger.info(f"  Filled cells: {filled_cells:,} ({pct_filled:.2f}%)")
    logger.info(f"  Empty cells: {total_cells - filled_cells:,} ({100 - pct_filled:.2f}%)")
    logger.info(f"  Average % missing returns: {coverage_df['pct_missing_returns'].mean():.2f}%")
    logger.info(f"  Max % missing returns: {coverage_df['pct_missing_returns'].max():.2f}%")
    
    return coverage_df


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("Master Coverage File Generator")
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
    
    # Create coverage file
    coverage_df = create_coverage_file(constituents_by_date, returns_df)
    
    if coverage_df.empty:
        logger.error("Failed to create coverage file. Exiting.")
        return
    
    # Save to CSV
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    coverage_df.to_csv(OUTPUT_FILE)
    logger.info(f"\n✓ Saved master coverage file to {OUTPUT_FILE}")
    logger.info(f"  Shape: {coverage_df.shape[0]} rows × {coverage_df.shape[1]} columns")
    
    # Show sample
    logger.info("\n" + "="*70)
    logger.info("Sample of Coverage File (first 5 rows, first 10 columns)")
    logger.info("="*70)
    sample_cols = coverage_df.columns[:10].tolist()
    sample_df = coverage_df[sample_cols].head(5)
    logger.info(f"\n{sample_df.to_string()}")
    
    logger.info("\n" + "="*70)
    logger.info("Complete!")
    logger.info("="*70)


if __name__ == "__main__":
    main()

