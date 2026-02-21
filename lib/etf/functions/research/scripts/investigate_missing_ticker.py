"""
Helper script to investigate missing returns for a specific ticker.

Usage:
    python investigate_missing_ticker.py TICKER
    python investigate_missing_ticker.py BCR
    python investigate_missing_ticker.py DOW --show-dates
"""

import sys
import pandas as pd
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Data paths
DETAILED_FILE = Path('./data/research/sp500_backtest/ticker_constituent_missing_returns_detailed.csv')
TICKER_SUMMARY_FILE = Path('./data/research/sp500_backtest/ticker_constituent_missing_returns_summary.csv')

def investigate_ticker(ticker: str, show_dates: bool = False):
    """Investigate missing returns for a specific ticker."""
    
    if not DETAILED_FILE.exists():
        print(f"❌ Detailed file not found: {DETAILED_FILE}")
        return
    
    print("="*70)
    print(f"INVESTIGATING TICKER: {ticker}")
    print("="*70)
    
    # Load data
    detailed_df = pd.read_csv(DETAILED_FILE)
    ticker_summary_df = pd.read_csv(TICKER_SUMMARY_FILE)
    
    # Get ticker data
    ticker_data = detailed_df[detailed_df['ticker'] == ticker]
    ticker_summary = ticker_summary_df[ticker_summary_df['ticker'] == ticker]
    
    if ticker_data.empty:
        print(f"\n❌ Ticker {ticker} not found in data")
        return
    
    # Show summary
    if not ticker_summary.empty:
        row = ticker_summary.iloc[0]
        print(f"\n📊 SUMMARY:")
        print(f"   First constituent period: {row['first_constituent_period']}")
        print(f"   Last constituent period: {row['last_constituent_period']}")
        print(f"   Total periods as constituent: {row['total_periods_as_constituent']:.0f}")
        print(f"   Periods with missing returns: {row['periods_with_missing_returns']:.0f}")
        print(f"   Periods with partial returns: {row['periods_with_partial_returns']:.0f}")
        print(f"   Periods with full returns: {row['periods_with_full_returns']:.0f}")
        print(f"   % periods missing: {row['pct_periods_missing']:.1f}%")
        print(f"   Total days missing: {row['total_days_missing']:.0f}")
        print(f"   % days missing: {row['pct_days_missing']:.1f}%")
    
    # Show missing periods
    missing_periods = ticker_data[ticker_data['status'] == 'Missing']
    if not missing_periods.empty:
        print(f"\n❌ MISSING PERIODS ({len(missing_periods)}):")
        print(f"   {'Period':<12} {'Returns Needed':<15} {'Days Missing':<15} {'% Missing':<12}")
        print("   " + "-"*54)
        for idx, row in missing_periods.head(20).iterrows():
            print(f"   {row['constituent_period']:<12} {row['returns_needed_period']:<15} {row['days_missing_returns']:<15.0f} {row['pct_missing']:<12.1f}%")
        if len(missing_periods) > 20:
            print(f"   ... and {len(missing_periods) - 20} more periods")
    
    # Show partial periods
    partial_periods = ticker_data[ticker_data['status'] == 'Partial']
    if not partial_periods.empty:
        print(f"\n⚠️  PARTIAL PERIODS ({len(partial_periods)}):")
        print(f"   {'Period':<12} {'Returns Needed':<15} {'Days Missing':<15} {'Days Available':<15} {'% Missing':<12}")
        print("   " + "-"*69)
        for idx, row in partial_periods.head(10).iterrows():
            print(f"   {row['constituent_period']:<12} {row['returns_needed_period']:<15} {row['days_missing_returns']:<15.0f} {row['days_with_returns']:<15.0f} {row['pct_missing']:<12.1f}%")
        if len(partial_periods) > 10:
            print(f"   ... and {len(partial_periods) - 10} more periods")
    
    # Show available periods
    available_periods = ticker_data[ticker_data['status'] == 'Available']
    if not available_periods.empty:
        print(f"\n✓ AVAILABLE PERIODS ({len(available_periods)}):")
        print(f"   All returns available for these periods")
    
    # Show missing dates if requested
    if show_dates and not missing_periods.empty:
        print(f"\n📅 MISSING DATES (first 5 periods):")
        for idx, row in missing_periods.head(5).iterrows():
            if pd.notna(row['missing_dates']) and row['missing_dates']:
                dates = str(row['missing_dates']).split(', ')
                print(f"\n   Period {row['constituent_period']} → {row['returns_needed_period']}:")
                print(f"   {', '.join(dates[:10])}")
                if len(dates) > 10:
                    print(f"   ... and {len(dates) - 10} more dates")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python investigate_missing_ticker.py TICKER [--show-dates]")
        print("Example: python investigate_missing_ticker.py BCR")
        print("Example: python investigate_missing_ticker.py DOW --show-dates")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    show_dates = '--show-dates' in sys.argv
    
    investigate_ticker(ticker, show_dates)

