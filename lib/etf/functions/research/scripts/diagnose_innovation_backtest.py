"""
Diagnostic script to check innovation factor backtest logic.
"""

import sys
from pathlib import Path
import os
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.scripts.backtest_innovation_factor import (
    load_monthly_constituents,
    load_returns,
    load_fundamentals_data,
    calculate_innovation_factor_point_in_time
)

# File paths
OUTPUT_DIR = Path('./data/research/sp500_backtest')
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents.csv')
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
FUNDAMENTALS_DIR = Path('./data/research/sp500_fundamentals')

START_YEAR = 2004
TOP_N = 50

def main():
    print("="*70)
    print("Innovation Factor Backtest Diagnostic")
    print("="*70)
    
    # Load data
    print("\n1. Loading data...")
    constituents_by_date = load_monthly_constituents()
    returns_df = load_returns()
    fundamentals = load_fundamentals_data()
    
    print(f"   Constituents: {len(constituents_by_date)} months")
    print(f"   Returns: {len(returns_df.columns)} tickers, {len(returns_df)} days")
    print(f"   Fundamentals: {len(fundamentals)} tickers")
    
    # Check a few specific months
    print("\n2. Checking factor calculation for sample months...")
    sample_dates = sorted(constituents_by_date.keys())[:5]  # First 5 months
    sample_dates.extend(sorted(constituents_by_date.keys())[60:65])  # Around 2009
    sample_dates.extend(sorted(constituents_by_date.keys())[120:125])  # Around 2014
    sample_dates.extend(sorted(constituents_by_date.keys())[-5:])  # Last 5 months
    
    for date_str in sample_dates:
        rebalance_date = pd.to_datetime(date_str)
        constituents = constituents_by_date[date_str]
        
        print(f"\n   Date: {date_str} ({len(constituents)} constituents)")
        
        # Calculate factors for all constituents
        innovation_factors = {}
        for ticker in constituents[:100]:  # Limit to first 100 for speed
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_factors[ticker] = factor
        
        if len(innovation_factors) == 0:
            print(f"      No factors calculated!")
            continue
        
        # Statistics
        factors_list = list(innovation_factors.values())
        print(f"      Factors calculated: {len(innovation_factors)}/{len(constituents[:100])}")
        print(f"      Factor range: [{min(factors_list):.4f}, {max(factors_list):.4f}]")
        print(f"      Factor mean: {np.mean(factors_list):.4f}")
        print(f"      Factor std: {np.std(factors_list):.4f}")
        
        # Top 10 by factor
        sorted_factors = sorted(innovation_factors.items(), key=lambda x: x[1], reverse=True)
        print(f"      Top 5 by factor:")
        for ticker, factor in sorted_factors[:5]:
            print(f"        {ticker}: {factor:.4f}")
        
        # Bottom 5
        print(f"      Bottom 5 by factor:")
        for ticker, factor in sorted_factors[-5:]:
            print(f"        {ticker}: {factor:.4f}")
        
        # Check if top 50 are different from random 50
        if len(innovation_factors) >= TOP_N:
            top_50 = [t for t, _ in sorted_factors[:TOP_N]]
            print(f"      Top {TOP_N} tickers selected")
            
            # Compare to equal-weighted (random sample)
            all_with_factors = list(innovation_factors.keys())
            random_50 = np.random.choice(all_with_factors, size=min(50, len(all_with_factors)), replace=False)
            print(f"      Random 50 tickers for comparison")
            
            # Check overlap
            overlap = len(set(top_50) & set(random_50))
            print(f"      Overlap with random 50: {overlap}/50 ({overlap/50*100:.1f}%)")
    
    # Check if factors are actually predictive
    print("\n3. Checking factor predictive power...")
    print("   (This would require forward returns analysis)")
    
    # Check factor distribution over time
    print("\n4. Factor distribution over time...")
    all_factors_by_date = {}
    for date_str in sorted(constituents_by_date.keys())[::12]:  # Every 12 months
        rebalance_date = pd.to_datetime(date_str)
        constituents = constituents_by_date[date_str]
        
        innovation_factors = {}
        for ticker in constituents[:200]:  # Sample
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_factors[ticker] = factor
        
        if len(innovation_factors) > 0:
            factors_list = list(innovation_factors.values())
            all_factors_by_date[date_str] = {
                'mean': np.mean(factors_list),
                'std': np.std(factors_list),
                'min': min(factors_list),
                'max': max(factors_list),
                'count': len(factors_list)
            }
    
    # Print summary
    print(f"   Analyzed {len(all_factors_by_date)} months")
    if all_factors_by_date:
        all_means = [v['mean'] for v in all_factors_by_date.values()]
        all_stds = [v['std'] for v in all_factors_by_date.values()]
        print(f"   Mean factor across all months: {np.mean(all_means):.4f} ± {np.std(all_means):.4f}")
        print(f"   Std of factors across all months: {np.mean(all_stds):.4f} ± {np.std(all_stds):.4f}")
    
    print("\n" + "="*70)
    print("Diagnostic Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

