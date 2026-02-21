"""
Analyze overlap between constituent periods and missing returns periods for each ticker.
This shows which missing returns actually matter (when ticker was in index).
"""

import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data paths
DETAILED_FILE = Path('./data/research/sp500_backtest/ticker_constituent_missing_returns_detailed.csv')
OUTPUT_DIR = Path('./data/research/sp500_backtest')
OUTPUT_FILE = OUTPUT_DIR / 'ticker_constituent_missing_overlap.csv'

def analyze_overlap():
    """Analyze overlap between constituent periods and missing returns periods."""
    logger.info("="*70)
    logger.info("Analyzing Constituent-Missing Returns Overlap")
    logger.info("="*70)
    
    # Load detailed data
    logger.info(f"Loading detailed data from {DETAILED_FILE}...")
    df = pd.read_csv(DETAILED_FILE)
    
    logger.info(f"Loaded {len(df):,} records for {df['ticker'].nunique()} unique tickers")
    
    # Filter to only periods where ticker was a constituent
    # (all records in this file are already for constituent periods)
    logger.info("\nAnalyzing overlap...")
    
    # For each ticker, calculate overlap statistics
    overlap_stats = []
    
    for ticker in sorted(df['ticker'].unique()):
        ticker_data = df[df['ticker'] == ticker].copy()
        
        # Constituent periods (all records)
        constituent_periods = sorted(ticker_data['constituent_period'].unique())
        total_constituent_periods = len(constituent_periods)
        
        # Missing returns periods
        missing_periods = sorted(ticker_data[ticker_data['status'] == 'Missing']['constituent_period'].unique())
        total_missing_periods = len(missing_periods)
        
        # Partial returns periods
        partial_periods = sorted(ticker_data[ticker_data['status'] == 'Partial']['constituent_period'].unique())
        total_partial_periods = len(partial_periods)
        
        # Available returns periods
        available_periods = sorted(ticker_data[ticker_data['status'] == 'Available']['constituent_period'].unique())
        total_available_periods = len(available_periods)
        
        # Calculate percentages
        pct_missing = (total_missing_periods / total_constituent_periods * 100) if total_constituent_periods > 0 else 0
        pct_partial = (total_partial_periods / total_constituent_periods * 100) if total_constituent_periods > 0 else 0
        pct_available = (total_available_periods / total_constituent_periods * 100) if total_constituent_periods > 0 else 0
        
        # Date ranges
        first_constituent = ticker_data['constituent_period'].min()
        last_constituent = ticker_data['constituent_period'].max()
        first_missing = missing_periods[0] if missing_periods else None
        last_missing = missing_periods[-1] if missing_periods else None
        
        # Days statistics
        total_days_missing = ticker_data[ticker_data['status'] == 'Missing']['days_missing_returns'].sum()
        total_days_in_periods = ticker_data['total_days_in_period'].sum()
        pct_days_missing = (total_days_missing / total_days_in_periods * 100) if total_days_in_periods > 0 else 0
        
        overlap_stats.append({
            'ticker': ticker,
            'first_constituent_period': first_constituent,
            'last_constituent_period': last_constituent,
            'total_constituent_periods': total_constituent_periods,
            'constituent_periods_list': ', '.join(constituent_periods),
            'first_missing_period': first_missing,
            'last_missing_period': last_missing,
            'total_missing_periods': total_missing_periods,
            'missing_periods_list': ', '.join(missing_periods) if missing_periods else '',
            'total_partial_periods': total_partial_periods,
            'partial_periods_list': ', '.join(partial_periods) if partial_periods else '',
            'total_available_periods': total_available_periods,
            'available_periods_list': ', '.join(available_periods) if available_periods else '',
            'pct_periods_missing': round(pct_missing, 2),
            'pct_periods_partial': round(pct_partial, 2),
            'pct_periods_available': round(pct_available, 2),
            'total_days_missing': int(total_days_missing),
            'total_days_in_periods': int(total_days_in_periods),
            'pct_days_missing': round(pct_days_missing, 2),
        })
    
    overlap_df = pd.DataFrame(overlap_stats)
    
    # Sort by total missing periods (descending)
    overlap_df = overlap_df.sort_values('total_missing_periods', ascending=False)
    
    logger.info(f"\n{'='*70}")
    logger.info("Summary Statistics")
    logger.info(f"{'='*70}")
    logger.info(f"Total tickers analyzed: {len(overlap_df)}")
    logger.info(f"Tickers with missing returns: {len(overlap_df[overlap_df['total_missing_periods'] > 0])}")
    logger.info(f"Tickers with partial returns: {len(overlap_df[overlap_df['total_partial_periods'] > 0])}")
    logger.info(f"Tickers with full coverage: {len(overlap_df[overlap_df['total_missing_periods'] == 0])}")
    
    # Save to CSV
    overlap_df.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"\n✓ Saved overlap analysis to {OUTPUT_FILE}")
    
    # Show top 20 tickers with most missing periods
    logger.info(f"\n{'='*70}")
    logger.info("Top 20 Tickers by Missing Periods")
    logger.info(f"{'='*70}")
    top_missing = overlap_df[overlap_df['total_missing_periods'] > 0].head(20)
    for idx, row in top_missing.iterrows():
        logger.info(f"{row['ticker']:<6} | {row['total_missing_periods']:>4} missing periods "
                   f"({row['pct_periods_missing']:>5.1f}%) | "
                   f"Constituent: {row['first_constituent_period']} to {row['last_constituent_period']} | "
                   f"Missing: {row['first_missing_period']} to {row['last_missing_period']}")
    
    return overlap_df


if __name__ == '__main__':
    overlap_df = analyze_overlap()
    print(f"\n✓ Analysis complete. Results saved to {OUTPUT_FILE}")

