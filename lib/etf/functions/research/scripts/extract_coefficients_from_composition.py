"""
Extract Innovation Coefficients from Portfolio Composition
This uses the composition file to extract coefficients for stocks that were actually selected.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.scripts.backtest_innovation_factor import (
    load_monthly_constituents,
    load_fundamentals_data,
    calculate_innovation_factor_point_in_time
)

OUTPUT_DIR = Path('./data/research/sp500_backtest')
COMPOSITION_FILE = OUTPUT_DIR / 'innovation_factor_portfolio_composition.csv'

def extract_coefficients_from_composition():
    """Extract coefficients for stocks in the portfolio composition."""
    print("="*70)
    print("Extracting Innovation Coefficients from Portfolio Composition")
    print("="*70)
    
    # Load composition
    print("\nLoading portfolio composition...")
    composition_df = pd.read_csv(COMPOSITION_FILE, index_col=0, parse_dates=True)
    if composition_df.index.tz is not None:
        composition_df.index = composition_df.index.tz_localize(None)
    
    print(f"  Loaded {len(composition_df)} months")
    
    # Load data needed for factor calculation
    print("\nLoading fundamentals...")
    fundamentals = load_fundamentals_data()
    print(f"  Loaded fundamentals for {len(fundamentals)} tickers")
    
    # Load constituents to get rebalance dates
    print("\nLoading constituents...")
    constituents_by_date = load_monthly_constituents()
    
    # Extract coefficients
    print("\nExtracting coefficients for portfolio stocks...")
    all_coefficients = []
    
    # Create mapping from portfolio date to rebalance date
    # Portfolio date is the month we hold, rebalance date is the month-end before
    for portfolio_date, row in composition_df.iterrows():
        if pd.isna(row['tickers']):
            continue
        
        # Find the rebalance date (month-end before portfolio_date)
        portfolio_date_ts = pd.to_datetime(portfolio_date)
        # Rebalance would be the last trading day of the previous month
        if portfolio_date_ts.month == 1:
            rebalance_year = portfolio_date_ts.year - 1
            rebalance_month = 12
        else:
            rebalance_year = portfolio_date_ts.year
            rebalance_month = portfolio_date_ts.month - 1
        
        # Find closest rebalance date in constituents
        rebalance_date_str = None
        for date_str in sorted(constituents_by_date.keys(), reverse=True):
            date_ts = pd.to_datetime(date_str)
            if date_ts.year == rebalance_year and date_ts.month == rebalance_month:
                rebalance_date_str = date_str
                break
        
        if not rebalance_date_str:
            # Try to find closest
            target_date = pd.Timestamp(year=rebalance_year, month=rebalance_month, day=28)
            closest_date = min(constituents_by_date.keys(), 
                              key=lambda x: abs((pd.to_datetime(x) - target_date).days))
            rebalance_date_str = closest_date
        
        rebalance_date = pd.to_datetime(rebalance_date_str)
        tickers = row['tickers'].split(',')
        year_month = portfolio_date_ts.strftime('%Y-%m')
        
        # Calculate factors for each ticker in portfolio
        for ticker in tickers:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            
            all_coefficients.append({
                'year_month': year_month,
                'portfolio_date': portfolio_date_ts.strftime('%Y-%m-%d'),
                'rebalance_date': rebalance_date_str,
                'ticker': ticker,
                'innovation_coefficient': factor if factor is not None else np.nan,
                'in_portfolio': True,
                'has_factor': factor is not None
            })
    
    df = pd.DataFrame(all_coefficients)
    
    print(f"\n✓ Extracted {len(df)} coefficient observations")
    print(f"  Unique tickers: {df['ticker'].nunique()}")
    print(f"  Unique year-months: {df['year_month'].nunique()}")
    print(f"  With factors: {df['has_factor'].sum()}")
    
    # Save
    output_file = OUTPUT_DIR / 'innovation_coefficients_portfolio_stocks.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved to {output_file}")
    
    # Create pivot table
    print("\nCreating pivot table...")
    pivot_df = df.pivot_table(
        index='year_month',
        columns='ticker',
        values='innovation_coefficient',
        aggfunc='first'
    )
    
    # Sort by year-month
    pivot_df.index = pd.to_datetime(pivot_df.index, format='%Y-%m')
    pivot_df = pivot_df.sort_index()
    pivot_df.index = pivot_df.index.strftime('%Y-%m')
    
    pivot_file = OUTPUT_DIR / 'innovation_coefficients_portfolio_pivot.csv'
    pivot_df.to_csv(pivot_file)
    print(f"✓ Saved pivot table to {pivot_file}")
    print(f"  Shape: {pivot_df.shape}")
    
    # Show sample
    print("\n" + "="*70)
    print("Sample of Coefficients (first 20 rows)")
    print("="*70)
    print(df.head(20).to_string())
    
    # Statistics
    print("\n" + "="*70)
    print("Factor Statistics")
    print("="*70)
    factors = df[df['has_factor']]['innovation_coefficient']
    print(f"  Count: {len(factors)}")
    print(f"  Mean: {factors.mean():.4f}")
    print(f"  Std: {factors.std():.4f}")
    print(f"  Min: {factors.min():.4f}")
    print(f"  Max: {factors.max():.4f}")
    print(f"  Median: {factors.median():.4f}")
    
    # By year-month
    print("\n" + "="*70)
    print("Statistics by Year-Month")
    print("="*70)
    stats = df.groupby('year_month').agg({
        'ticker': 'count',
        'has_factor': 'sum',
        'innovation_coefficient': ['mean', 'std', 'min', 'max']
    }).round(4)
    stats.columns = ['total_stocks', 'with_factor', 'mean_coef', 'std_coef', 'min_coef', 'max_coef']
    stats['pct_with_factor'] = (stats['with_factor'] / stats['total_stocks'] * 100).round(1)
    
    stats_file = OUTPUT_DIR / 'innovation_coefficients_portfolio_stats.csv'
    stats.to_csv(stats_file)
    print(f"\n✓ Saved statistics to {stats_file}")
    print("\nFirst 10 months:")
    print(stats.head(10).to_string())
    
    return df, pivot_df, stats

def main():
    if not COMPOSITION_FILE.exists():
        print(f"ERROR: Composition file not found: {COMPOSITION_FILE}")
        return
    
    df, pivot_df, stats = extract_coefficients_from_composition()
    
    print("\n" + "="*70)
    print("Extraction Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

