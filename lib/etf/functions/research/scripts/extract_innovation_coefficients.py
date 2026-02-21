"""
Extract Innovation Coefficients for All Constituents by Year-Month
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
START_YEAR = 2004

def extract_all_coefficients():
    """Extract innovation coefficients for all constituents at each rebalance."""
    print("="*70)
    print("Extracting Innovation Coefficients for All Constituents")
    print("="*70)
    
    # Load data
    print("\nLoading data...")
    constituents_by_date = load_monthly_constituents()
    fundamentals = load_fundamentals_data()
    
    print(f"Constituents: {len(constituents_by_date)} months")
    print(f"Fundamentals: {len(fundamentals)} tickers")
    
    # Extract coefficients for each rebalance date
    print("\nExtracting coefficients...")
    all_coefficients = []
    sorted_dates = sorted(constituents_by_date.keys())
    
    for i, rebalance_date_str in enumerate(sorted_dates):
        rebalance_date = pd.to_datetime(rebalance_date_str)
        constituents = constituents_by_date[rebalance_date_str]
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            print(f"Processing {rebalance_date_str} ({i+1}/{len(sorted_dates)})...")
        
        # Calculate factors for ALL constituents
        for ticker in constituents:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            
            # Store result (even if None)
            all_coefficients.append({
                'year_month': rebalance_date.strftime('%Y-%m'),
                'rebalance_date': rebalance_date_str,
                'ticker': ticker,
                'innovation_coefficient': factor if factor is not None else np.nan,
                'has_factor': factor is not None
            })
    
    df = pd.DataFrame(all_coefficients)
    
    print(f"\n✓ Extracted {len(df)} coefficient observations")
    print(f"  Total unique tickers: {df['ticker'].nunique()}")
    print(f"  Total unique year-months: {df['year_month'].nunique()}")
    print(f"  Observations with factors: {df['has_factor'].sum()}")
    print(f"  Observations without factors: {(~df['has_factor']).sum()}")
    
    # Save to CSV
    output_file = OUTPUT_DIR / 'innovation_coefficients_all_constituents.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved to {output_file}")
    
    # Create pivot table: year_month x ticker
    print("\nCreating pivot table (year_month x ticker)...")
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
    
    pivot_file = OUTPUT_DIR / 'innovation_coefficients_pivot.csv'
    pivot_df.to_csv(pivot_file)
    print(f"✓ Saved pivot table to {pivot_file}")
    print(f"  Shape: {pivot_df.shape} (rows: year-months, columns: tickers)")
    
    # Statistics by year-month
    print("\n" + "="*70)
    print("Statistics by Year-Month")
    print("="*70)
    
    stats_by_month = []
    for year_month in sorted(df['year_month'].unique()):
        month_data = df[df['year_month'] == year_month]
        has_factor = month_data['has_factor'].sum()
        total = len(month_data)
        pct = has_factor / total * 100 if total > 0 else 0
        
        if has_factor > 0:
            factors = month_data[month_data['has_factor']]['innovation_coefficient']
            stats_by_month.append({
                'year_month': year_month,
                'total_constituents': total,
                'with_factor': has_factor,
                'pct_with_factor': pct,
                'mean_factor': factors.mean(),
                'std_factor': factors.std(),
                'min_factor': factors.min(),
                'max_factor': factors.max(),
                'median_factor': factors.median()
            })
    
    stats_df = pd.DataFrame(stats_by_month)
    stats_file = OUTPUT_DIR / 'innovation_coefficients_statistics.csv'
    stats_df.to_csv(stats_file, index=False)
    print(f"\n✓ Saved statistics to {stats_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("Summary Statistics")
    print("="*70)
    print(f"\nCoverage over time:")
    print(f"  Mean % with factors: {stats_df['pct_with_factor'].mean():.1f}%")
    print(f"  Min % with factors: {stats_df['pct_with_factor'].min():.1f}%")
    print(f"  Max % with factors: {stats_df['pct_with_factor'].max():.1f}%")
    
    print(f"\nFactor values (across all months):")
    all_factors = df[df['has_factor']]['innovation_coefficient']
    print(f"  Mean: {all_factors.mean():.4f}")
    print(f"  Std: {all_factors.std():.4f}")
    print(f"  Min: {all_factors.min():.4f}")
    print(f"  Max: {all_factors.max():.4f}")
    print(f"  Median: {all_factors.median():.4f}")
    
    # Show sample of pivot table
    print("\n" + "="*70)
    print("Sample of Pivot Table (first 5 year-months, first 10 tickers)")
    print("="*70)
    print(pivot_df.iloc[:5, :10].to_string())
    
    # Show tickers with most frequent factors
    print("\n" + "="*70)
    print("Top 20 Tickers by Factor Frequency")
    print("="*70)
    ticker_counts = df[df['has_factor']]['ticker'].value_counts().head(20)
    for ticker, count in ticker_counts.items():
        pct = count / len(sorted_dates) * 100
        print(f"  {ticker:6s}: {count:4d} months ({pct:5.1f}%)")
    
    return df, pivot_df, stats_df

def main():
    df, pivot_df, stats_df = extract_all_coefficients()
    
    print("\n" + "="*70)
    print("Extraction Complete!")
    print("="*70)
    print(f"\nFiles created:")
    print(f"  1. innovation_coefficients_all_constituents.csv - Full data")
    print(f"  2. innovation_coefficients_pivot.csv - Pivot table (year_month x ticker)")
    print(f"  3. innovation_coefficients_statistics.csv - Statistics by year-month")

if __name__ == '__main__':
    main()

