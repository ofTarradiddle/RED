"""
Check if innovation factor portfolio composition differs from equal-weighted.
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
    load_fundamentals_data,
    calculate_innovation_factor_point_in_time
)

START_YEAR = 2004
TOP_N = 50

def main():
    print("="*70)
    print("Portfolio Composition Analysis")
    print("="*70)
    
    # Load data
    constituents_by_date = load_monthly_constituents()
    fundamentals = load_fundamentals_data()
    
    # Analyze a few key dates
    sample_dates = [
        sorted(constituents_by_date.keys())[0],   # First month
        sorted(constituents_by_date.keys())[60],  # ~2009
        sorted(constituents_by_date.keys())[120], # ~2014
        sorted(constituents_by_date.keys())[-1]  # Last month
    ]
    
    for date_str in sample_dates:
        rebalance_date = pd.to_datetime(date_str)
        constituents = constituents_by_date[date_str]
        
        print(f"\n{'='*70}")
        print(f"Date: {date_str}")
        print(f"Total constituents: {len(constituents)}")
        
        # Calculate factors for ALL constituents (not just first 100)
        print("Calculating factors for all constituents...")
        innovation_factors = {}
        for ticker in constituents:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_factors[ticker] = factor
        
        print(f"Factors calculated: {len(innovation_factors)}/{len(constituents)}")
        
        if len(innovation_factors) < TOP_N:
            print(f"WARNING: Only {len(innovation_factors)} factors available, need {TOP_N}")
            continue
        
        # Select top N
        sorted_factors = sorted(innovation_factors.items(), key=lambda x: x[1], reverse=True)
        top_50_tickers = [t for t, _ in sorted_factors[:TOP_N]]
        top_50_factors = [f for _, f in sorted_factors[:TOP_N]]
        
        print(f"\nTop {TOP_N} stocks by innovation factor:")
        print(f"  Factor range: [{min(top_50_factors):.4f}, {max(top_50_factors):.4f}]")
        print(f"  Factor mean: {np.mean(top_50_factors):.4f}")
        print(f"  Factor std: {np.std(top_50_factors):.4f}")
        
        # Compare to equal-weighted (all constituents)
        print(f"\nComparison to Equal-Weighted S&P 500:")
        print(f"  Innovation portfolio: {len(top_50_tickers)} stocks")
        print(f"  Equal-weighted: {len(constituents)} stocks")
        
        # Overlap
        overlap = len(set(top_50_tickers) & set(constituents))
        overlap_pct = overlap / len(top_50_tickers) * 100
        print(f"  Overlap: {overlap}/{len(top_50_tickers)} ({overlap_pct:.1f}%)")
        
        # Show top 10
        print(f"\n  Top 10 by innovation factor:")
        for i, (ticker, factor) in enumerate(sorted_factors[:10], 1):
            print(f"    {i:2d}. {ticker:6s}: {factor:8.4f}")
        
        # Check if these are large cap stocks (would be in EW anyway)
        # This is harder to check without market cap data, but we can see
        # if the selection is meaningful
        
        # Random sample comparison
        all_with_factors = list(innovation_factors.keys())
        if len(all_with_factors) >= TOP_N:
            np.random.seed(42)  # For reproducibility
            random_50 = np.random.choice(all_with_factors, size=TOP_N, replace=False)
            random_overlap = len(set(top_50_tickers) & set(random_50))
            print(f"\n  Random 50 overlap: {random_overlap}/{TOP_N} ({random_overlap/TOP_N*100:.1f}%)")
            print(f"  This shows if selection is meaningful vs random")
    
    print(f"\n{'='*70}")
    print("Analysis Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

