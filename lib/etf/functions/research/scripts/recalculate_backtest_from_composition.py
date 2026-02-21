"""
Recalculate Innovation Factor Backtest from Portfolio Composition File
This validates that the backtest results match the composition.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

OUTPUT_DIR = Path('./data/research/sp500_backtest')
COMPOSITION_FILE = OUTPUT_DIR / 'innovation_factor_portfolio_composition.csv'
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
RESULTS_FILE = OUTPUT_DIR / 'innovation_factor_backtest_results.csv'
NEW_RESULTS_FILE = OUTPUT_DIR / 'innovation_factor_backtest_from_composition.csv'

def wait_for_composition_file():
    """Wait for composition file to be created."""
    import time
    print("Waiting for portfolio composition file...")
    max_wait = 3600  # 1 hour max
    waited = 0
    check_interval = 30
    
    while not COMPOSITION_FILE.exists():
        if waited >= max_wait:
            print(f"ERROR: Composition file not found after {max_wait} seconds")
            return False
        time.sleep(check_interval)
        waited += check_interval
        if waited % 300 == 0:  # Every 5 minutes
            print(f"  Still waiting... ({waited}s elapsed)")
    
    print(f"✓ Composition file found!")
    return True

def load_composition():
    """Load portfolio composition."""
    print(f"\nLoading composition from {COMPOSITION_FILE}...")
    df = pd.read_csv(COMPOSITION_FILE, index_col=0, parse_dates=True)
    
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    print(f"  Loaded {len(df)} months of composition data")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")
    
    return df

def load_returns():
    """Load returns data."""
    print(f"\nLoading returns from {RETURNS_FILE}...")
    df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    print(f"  Loaded returns for {len(df.columns)} tickers")
    print(f"  Date range: {df.index.min()} to {df.index.max()}")
    
    return df

def recalculate_backtest(composition_df, returns_df):
    """Recalculate backtest returns from composition."""
    print("\n" + "="*70)
    print("Recalculating Backtest from Composition")
    print("="*70)
    
    portfolio_returns = []
    
    for date_idx, row in composition_df.iterrows():
        if pd.isna(row['tickers']):
            continue
        
        tickers = row['tickers'].split(',')
        num_stocks = row['num_stocks']
        
        # Get returns for the month starting from this date
        month_start = date_idx
        if month_start.month == 12:
            month_end = pd.Timestamp(year=month_start.year + 1, month=1, day=1) - pd.Timedelta(days=1)
        else:
            month_end = pd.Timestamp(year=month_start.year, month=month_start.month + 1, day=1) - pd.Timedelta(days=1)
        
        # Filter returns to this month
        month_returns = returns_df[
            (returns_df.index >= month_start) & 
            (returns_df.index <= month_end)
        ]
        
        if month_returns.empty:
            continue
        
        # Filter to available tickers
        available_tickers = [t for t in tickers if t in month_returns.columns]
        if not available_tickers:
            continue
        
        # Calculate daily portfolio returns (equal-weighted)
        daily_portfolio_returns = []
        for day_idx in month_returns.index:
            day_returns = month_returns.loc[day_idx, available_tickers]
            valid_returns = day_returns.dropna()
            if len(valid_returns) > 0:
                equal_weight = 1.0 / len(valid_returns)
                daily_portfolio_return = (valid_returns * equal_weight).sum()
                daily_portfolio_returns.append(daily_portfolio_return)
        
        if len(daily_portfolio_returns) == 0:
            continue
        
        # Compound daily portfolio returns to get monthly return
        portfolio_return = (1 + pd.Series(daily_portfolio_returns)).prod() - 1
        
        portfolio_returns.append({
            'date': month_start,
            'return': portfolio_return,
            'num_stocks': len(available_tickers)
        })
    
    result_df = pd.DataFrame(portfolio_returns)
    if not result_df.empty:
        result_df = result_df.set_index('date')
        result_df = result_df.sort_index()
    
    print(f"\n✓ Recalculated {len(result_df)} monthly returns")
    return result_df

def compare_results(original_df, recalculated_df):
    """Compare original and recalculated results."""
    print("\n" + "="*70)
    print("Comparing Original vs Recalculated Results")
    print("="*70)
    
    # Align dates
    common_dates = original_df.index.intersection(recalculated_df.index)
    print(f"\nCommon dates: {len(common_dates)} months")
    
    if len(common_dates) == 0:
        print("ERROR: No overlapping dates!")
        return
    
    orig_returns = original_df.loc[common_dates, 'return']
    recalc_returns = recalculated_df.loc[common_dates, 'return']
    
    # Calculate differences
    differences = recalc_returns - orig_returns
    abs_differences = differences.abs()
    
    print(f"\nReturn Comparison:")
    print(f"  Mean absolute difference: {abs_differences.mean():.8f}")
    print(f"  Max absolute difference: {abs_differences.max():.8f}")
    print(f"  Min absolute difference: {abs_differences.min():.8f}")
    print(f"  Std of differences: {differences.std():.8f}")
    
    # Count exact matches (within rounding)
    exact_matches = (abs_differences < 1e-6).sum()
    print(f"  Exact matches (within 1e-6): {exact_matches}/{len(common_dates)} ({exact_matches/len(common_dates)*100:.1f}%)")
    
    # Performance metrics comparison
    def calc_metrics(returns):
        cum = (1 + returns).cumprod()
        total_return = cum.iloc[-1] - 1.0
        years = len(returns) / 12.0
        cagr = (cum.iloc[-1] ** (1.0 / years)) - 1.0 if years > 0 else np.nan
        vol = returns.std() * np.sqrt(12) if len(returns) > 1 else np.nan
        sharpe = (returns.mean() * 12.0) / vol if vol and vol != 0 else np.nan
        running_max = cum.expanding().max()
        drawdown = (cum - running_max) / running_max
        max_dd = drawdown.min()
        return {
            'total_return': total_return,
            'cagr': cagr,
            'volatility': vol,
            'sharpe': sharpe,
            'max_drawdown': max_dd
        }
    
    orig_metrics = calc_metrics(orig_returns)
    recalc_metrics = calc_metrics(recalc_returns)
    
    print(f"\nPerformance Metrics Comparison:")
    print(f"\n  Original:")
    for key, value in orig_metrics.items():
        print(f"    {key}: {value:.4f}")
    
    print(f"\n  Recalculated:")
    for key, value in recalc_metrics.items():
        print(f"    {key}: {value:.4f}")
    
    print(f"\n  Differences:")
    for key in orig_metrics.keys():
        diff = recalc_metrics[key] - orig_metrics[key]
        print(f"    {key}: {diff:+.6f}")
    
    # Plot comparison
    print(f"\nCreating comparison plot...")
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Original vs Recalculated Backtest Comparison', fontsize=16, fontweight='bold')
    
    # Plot 1: Cumulative returns
    ax1 = axes[0, 0]
    orig_cum = (1 + orig_returns).cumprod()
    recalc_cum = (1 + recalc_returns).cumprod()
    
    ax1.plot(orig_cum.index, orig_cum.values, label='Original', linewidth=2, color='#2E86AB')
    ax1.plot(recalc_cum.index, recalc_cum.values, label='Recalculated', linewidth=2, 
             color='#A23B72', linestyle='--')
    ax1.set_title('Cumulative Returns Comparison', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 2: Monthly returns comparison
    ax2 = axes[0, 1]
    ax2.plot(orig_returns.index, orig_returns.values, label='Original', 
             linewidth=1, alpha=0.7, color='#2E86AB')
    ax2.plot(recalc_returns.index, recalc_returns.values, label='Recalculated', 
             linewidth=1, alpha=0.7, color='#A23B72', linestyle='--')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Monthly Returns Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Monthly Return', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 3: Differences over time
    ax3 = axes[1, 0]
    ax3.plot(differences.index, differences.values, linewidth=1, alpha=0.7, color='red')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Return Differences (Recalculated - Original)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Difference', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax3.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 4: Scatter plot
    ax4 = axes[1, 1]
    ax4.scatter(orig_returns.values, recalc_returns.values, alpha=0.5, s=20)
    min_val = min(orig_returns.min(), recalc_returns.min())
    max_val = max(orig_returns.max(), recalc_returns.max())
    ax4.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect match')
    ax4.set_title('Return Scatter: Original vs Recalculated', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Original Returns', fontsize=12)
    ax4.set_ylabel('Recalculated Returns', fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'backtest_validation_comparison.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved comparison plot to {plot_file}")
    plt.close()

def main():
    print("="*70)
    print("Recalculate Innovation Factor Backtest from Composition")
    print("="*70)
    
    # Wait for composition file
    if not wait_for_composition_file():
        return
    
    # Load data
    composition_df = load_composition()
    returns_df = load_returns()
    
    # Recalculate backtest
    recalculated_df = recalculate_backtest(composition_df, returns_df)
    
    if recalculated_df.empty:
        print("ERROR: Recalculation produced no results")
        return
    
    # Save recalculated results
    recalculated_df.to_csv(NEW_RESULTS_FILE)
    print(f"\n✓ Saved recalculated results to {NEW_RESULTS_FILE}")
    
    # Load original results for comparison
    if RESULTS_FILE.exists():
        original_df = pd.read_csv(RESULTS_FILE, index_col=0, parse_dates=True)
        if original_df.index.tz is not None:
            original_df.index = original_df.index.tz_localize(None)
        
        compare_results(original_df, recalculated_df)
    else:
        print(f"\nWARNING: Original results file not found: {RESULTS_FILE}")
        print("Skipping comparison.")
    
    print("\n" + "="*70)
    print("Recalculation Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

