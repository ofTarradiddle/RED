"""
Fast extraction of innovation coefficients - processes in batches with progress.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict

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

def extract_coefficients_fast():
    """Extract coefficients efficiently."""
    print("="*70)
    print("Extracting Innovation Coefficients (Fast Version)")
    print("="*70)
    
    # Load data
    print("\nLoading data...")
    constituents_by_date = load_monthly_constituents()
    fundamentals = load_fundamentals_data()
    
    print(f"  {len(constituents_by_date)} months, {len(fundamentals)} tickers")
    
    # Process in batches - every 12 months
    print("\nExtracting coefficients (processing every month)...")
    all_coefficients = []
    sorted_dates = sorted(constituents_by_date.keys())
    
    # Cache factors by (ticker, rebalance_date) to avoid recalculation
    factor_cache = {}
    
    for i, rebalance_date_str in enumerate(sorted_dates):
        rebalance_date = pd.to_datetime(rebalance_date_str)
        constituents = constituents_by_date[rebalance_date_str]
        year_month = rebalance_date.strftime('%Y-%m')
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            print(f"  Processing {rebalance_date_str} ({i+1}/{len(sorted_dates)})...")
        
        # Calculate factors for all constituents
        for ticker in constituents:
            cache_key = (ticker, rebalance_date_str)
            
            if cache_key in factor_cache:
                factor = factor_cache[cache_key]
            else:
                factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
                factor_cache[cache_key] = factor
            
            all_coefficients.append({
                'year_month': year_month,
                'rebalance_date': rebalance_date_str,
                'ticker': ticker,
                'innovation_coefficient': factor if factor is not None else np.nan,
                'has_factor': factor is not None
            })
    
    df = pd.DataFrame(all_coefficients)
    
    print(f"\n✓ Extracted {len(df)} observations")
    print(f"  Unique tickers: {df['ticker'].nunique()}")
    print(f"  Unique year-months: {df['year_month'].nunique()}")
    print(f"  With factors: {df['has_factor'].sum()} ({df['has_factor'].sum()/len(df)*100:.1f}%)")
    
    # Save full data
    output_file = OUTPUT_DIR / 'innovation_coefficients_all_constituents.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Saved full data to {output_file}")
    
    # Create pivot table
    print("\nCreating pivot table (this may take a moment)...")
    pivot_df = df.pivot_table(
        index='year_month',
        columns='ticker',
        values='innovation_coefficient',
        aggfunc='first'
    )
    
    # Sort
    pivot_df.index = pd.to_datetime(pivot_df.index, format='%Y-%m')
    pivot_df = pivot_df.sort_index()
    pivot_df.index = pivot_df.index.strftime('%Y-%m')
    
    pivot_file = OUTPUT_DIR / 'innovation_coefficients_pivot.csv'
    pivot_df.to_csv(pivot_file)
    print(f"✓ Saved pivot table to {pivot_file}")
    print(f"  Shape: {pivot_df.shape} (rows: year-months, columns: tickers)")
    
    # Statistics by year-month
    print("\nCalculating statistics...")
    stats_list = []
    for year_month in sorted(df['year_month'].unique()):
        month_data = df[df['year_month'] == year_month]
        has_factor = month_data['has_factor'].sum()
        total = len(month_data)
        
        if has_factor > 0:
            factors = month_data[month_data['has_factor']]['innovation_coefficient']
            stats_list.append({
                'year_month': year_month,
                'total_constituents': total,
                'with_factor': has_factor,
                'pct_with_factor': has_factor / total * 100,
                'mean_coefficient': factors.mean(),
                'std_coefficient': factors.std(),
                'min_coefficient': factors.min(),
                'max_coefficient': factors.max(),
                'median_coefficient': factors.median()
            })
    
    stats_df = pd.DataFrame(stats_list)
    stats_file = OUTPUT_DIR / 'innovation_coefficients_statistics.csv'
    stats_df.to_csv(stats_file, index=False)
    print(f"✓ Saved statistics to {stats_file}")
    
    # Show summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print(f"\nCoverage:")
    print(f"  Mean % with factors: {stats_df['pct_with_factor'].mean():.1f}%")
    print(f"  Range: {stats_df['pct_with_factor'].min():.1f}% to {stats_df['pct_with_factor'].max():.1f}%")
    
    all_factors = df[df['has_factor']]['innovation_coefficient']
    print(f"\nFactor values:")
    print(f"  Mean: {all_factors.mean():.4f}")
    print(f"  Std: {all_factors.std():.4f}")
    print(f"  Range: [{all_factors.min():.4f}, {all_factors.max():.4f}]")
    print(f"  Median: {all_factors.median():.4f}")
    
    # Show sample
    print("\n" + "="*70)
    print("Sample Data (first 20 rows)")
    print("="*70)
    print(df.head(20).to_string())
    
    print("\n" + "="*70)
    print("Sample Statistics (first 10 months)")
    print("="*70)
    print(stats_df.head(10).to_string())
    
    return df, pivot_df, stats_df

def main():
    df, pivot_df, stats_df = extract_coefficients_fast()
    
    print("\n" + "="*70)
    print("Extraction Complete!")
    print("="*70)
    print(f"\nFiles created:")
    print(f"  1. innovation_coefficients_all_constituents.csv")
    print(f"  2. innovation_coefficients_pivot.csv")
    print(f"  3. innovation_coefficients_statistics.csv")

if __name__ == '__main__':
    main()

