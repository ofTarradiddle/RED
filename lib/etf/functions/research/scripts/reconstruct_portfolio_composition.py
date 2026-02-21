"""
Reconstruct Innovation Factor Portfolio Composition by re-running selection logic.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import Counter

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
TOP_N = 50

def reconstruct_composition():
    """Reconstruct portfolio composition by re-running selection logic."""
    print("="*70)
    print("Reconstructing Innovation Factor Portfolio Composition")
    print("="*70)
    
    # Load data
    print("\nLoading data...")
    constituents_by_date = load_monthly_constituents()
    fundamentals = load_fundamentals_data()
    
    print(f"Constituents: {len(constituents_by_date)} months")
    print(f"Fundamentals: {len(fundamentals)} tickers")
    
    # Reconstruct portfolio for each month
    print("\nReconstructing portfolio composition...")
    portfolio_composition = []
    sorted_dates = sorted(constituents_by_date.keys())
    
    for i, rebalance_date_str in enumerate(sorted_dates):
        rebalance_date = pd.to_datetime(rebalance_date_str)
        constituents = constituents_by_date[rebalance_date_str]
        
        if (i + 1) % 24 == 0 or (i + 1) <= 5:
            print(f"Processing {rebalance_date_str} ({i+1}/{len(sorted_dates)})...")
        
        # Calculate innovation factors
        innovation_factors = {}
        for ticker in constituents:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_factors[ticker] = factor
        
        # Select top N
        if len(innovation_factors) >= TOP_N:
            sorted_factors = sorted(innovation_factors.items(), key=lambda x: x[1], reverse=True)
            selected_tickers = [t for t, _ in sorted_factors[:TOP_N]]
        elif len(innovation_factors) > 0:
            sorted_factors = sorted(innovation_factors.items(), key=lambda x: x[1], reverse=True)
            selected_tickers = [t for t, _ in sorted_factors]
        else:
            selected_tickers = []
        
        # Calculate next month date
        if rebalance_date.month == 12:
            next_year = rebalance_date.year + 1
            next_month = 1
        else:
            next_year = rebalance_date.year
            next_month = rebalance_date.month + 1
        
        next_month_start = pd.Timestamp(year=next_year, month=next_month, day=1)
        
        portfolio_composition.append({
            'date': next_month_start,
            'num_stocks': len(selected_tickers),
            'tickers': ','.join(sorted(selected_tickers))
        })
    
    df = pd.DataFrame(portfolio_composition)
    if not df.empty:
        df = df.set_index('date')
        df = df.sort_index()
    
    print(f"\n✓ Reconstructed composition for {len(df)} months")
    return df

def analyze_composition(df):
    """Analyze portfolio composition over time."""
    print("\n" + "="*70)
    print("Portfolio Composition Analysis")
    print("="*70)
    
    # Extract all unique tickers
    all_tickers = set()
    for tickers_str in df['tickers'].dropna():
        tickers = tickers_str.split(',')
        all_tickers.update(tickers)
    
    print(f"\nTotal unique tickers in portfolio over time: {len(all_tickers)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    print(f"Total rebalances: {len(df)}")
    
    # Count how often each ticker appears
    ticker_counts = Counter()
    for tickers_str in df['tickers'].dropna():
        tickers = tickers_str.split(',')
        ticker_counts.update(tickers)
    
    # Top 30 most frequently held stocks
    print(f"\n{'='*70}")
    print("Top 30 Most Frequently Held Stocks")
    print("="*70)
    top_30 = ticker_counts.most_common(30)
    for i, (ticker, count) in enumerate(top_30, 1):
        pct = count / len(df) * 100
        print(f"{i:2d}. {ticker:6s}: {count:4d} months ({pct:5.1f}% of time)")
    
    # Portfolio turnover analysis
    print(f"\n{'='*70}")
    print("Portfolio Turnover Analysis")
    print("="*70)
    
    turnovers = []
    prev_tickers = set()
    for idx, row in df.iterrows():
        if pd.isna(row['tickers']):
            continue
        current_tickers = set(row['tickers'].split(','))
        if prev_tickers:
            additions = len(current_tickers - prev_tickers)
            removals = len(prev_tickers - current_tickers)
            turnover = (additions + removals) / 2 / len(current_tickers) if current_tickers else 0
            turnovers.append(turnover)
        prev_tickers = current_tickers
    
    if turnovers:
        print(f"Average monthly turnover: {np.mean(turnovers):.2%}")
        print(f"Median monthly turnover: {np.median(turnovers):.2%}")
        print(f"Min turnover: {np.min(turnovers):.2%}")
        print(f"Max turnover: {np.max(turnovers):.2%}")
    
    return ticker_counts, turnovers

def plot_composition_over_time(df, ticker_counts):
    """Create visualizations of portfolio composition."""
    print(f"\n{'='*70}")
    print("Creating visualizations...")
    print("="*70)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Innovation Factor Portfolio Composition Over Time (2004-2025)', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Top 30 stocks by holding frequency
    ax1 = axes[0, 0]
    top_30 = ticker_counts.most_common(30)
    tickers = [t for t, _ in top_30]
    pcts = [c / len(df) * 100 for _, c in top_30]
    
    ax1.barh(range(len(tickers)), pcts, color='#2E86AB')
    ax1.set_yticks(range(len(tickers)))
    ax1.set_yticklabels(tickers, fontsize=9)
    ax1.set_xlabel('% of Time in Portfolio', fontsize=12)
    ax1.set_title('Top 30 Stocks by Holding Frequency', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.invert_yaxis()
    
    # Plot 2: Number of unique stocks over time (rolling window)
    ax2 = axes[0, 1]
    unique_counts = []
    dates = []
    window_size = 12  # 12-month rolling window
    
    for i in range(len(df)):
        if i < window_size:
            window_df = df.iloc[:i+1]
        else:
            window_df = df.iloc[i-window_size+1:i+1]
        
        all_window_tickers = set()
        for tickers_str in window_df['tickers'].dropna():
            tickers = tickers_str.split(',')
            all_window_tickers.update(tickers)
        
        unique_counts.append(len(all_window_tickers))
        dates.append(df.index[i])
    
    ax2.plot(dates, unique_counts, linewidth=2, color='#2E86AB')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel(f'Unique Stocks (rolling {window_size}-month window)', fontsize=12)
    ax2.set_title('Portfolio Diversity Over Time', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 3: Portfolio turnover over time
    ax3 = axes[1, 0]
    prev_tickers = set()
    turnovers = []
    turnover_dates = []
    
    for idx, row in df.iterrows():
        if pd.isna(row['tickers']):
            continue
        current_tickers = set(row['tickers'].split(','))
        if prev_tickers:
            additions = len(current_tickers - prev_tickers)
            removals = len(prev_tickers - current_tickers)
            turnover = (additions + removals) / 2 / len(current_tickers) if current_tickers else 0
            turnovers.append(turnover)
            turnover_dates.append(idx)
        prev_tickers = current_tickers
    
    if turnovers:
        ax3.plot(turnover_dates, [t*100 for t in turnovers], linewidth=1.5, alpha=0.7, color='#A23B72')
        ax3.axhline(y=np.mean(turnovers)*100, color='red', linestyle='--', 
                   label=f'Mean: {np.mean(turnovers):.1f}%')
        ax3.set_xlabel('Date', fontsize=12)
        ax3.set_ylabel('Monthly Turnover (%)', fontsize=12)
        ax3.set_title('Portfolio Turnover Over Time', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax3.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 4: Holding period distribution
    ax4 = axes[1, 1]
    holding_periods = list(ticker_counts.values())
    ax4.hist(holding_periods, bins=30, edgecolor='black', alpha=0.7, color='#F18F01')
    ax4.set_xlabel('Months Held', fontsize=12)
    ax4.set_ylabel('Number of Stocks', fontsize=12)
    ax4.set_title('Distribution of Holding Periods', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    if holding_periods:
        ax4.axvline(x=np.mean(holding_periods), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(holding_periods):.1f} months')
        ax4.legend()
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'innovation_factor_portfolio_composition.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved composition analysis plot to {plot_file}")
    plt.close()
    
    # Save detailed composition CSV
    composition_file = OUTPUT_DIR / 'innovation_factor_portfolio_composition.csv'
    df.to_csv(composition_file)
    print(f"✓ Saved detailed composition to {composition_file}")

def main():
    df = reconstruct_composition()
    if df.empty:
        print("ERROR: Failed to reconstruct composition")
        return
    
    ticker_counts, turnovers = analyze_composition(df)
    plot_composition_over_time(df, ticker_counts)
    
    print(f"\n{'='*70}")
    print("Analysis Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

