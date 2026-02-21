"""
Analyze Innovation Factor Portfolio Composition Over Time
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

OUTPUT_DIR = Path('./data/research/sp500_backtest')
RESULTS_FILE = OUTPUT_DIR / 'innovation_factor_backtest_results.csv'

def load_portfolio_composition():
    """Load portfolio composition from backtest results."""
    df = pd.read_csv(RESULTS_FILE, index_col=0, parse_dates=True)
    
    if 'tickers' not in df.columns:
        print("ERROR: 'tickers' column not found in results file.")
        print("Please re-run the backtest with the updated code that tracks tickers.")
        return None
    
    return df

def analyze_composition(df):
    """Analyze portfolio composition over time."""
    print("="*70)
    print("Innovation Factor Portfolio Composition Analysis")
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
    
    # Top 20 most frequently held stocks
    print(f"\n{'='*70}")
    print("Top 20 Most Frequently Held Stocks")
    print("="*70)
    top_20 = ticker_counts.most_common(20)
    for i, (ticker, count) in enumerate(top_20, 1):
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
            # Calculate turnover: (additions + removals) / 2 / portfolio_size
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
    
    # Stocks held for entire period
    print(f"\n{'='*70}")
    print("Stocks Held for Entire Period")
    print("="*70)
    always_held = [ticker for ticker, count in ticker_counts.items() if count == len(df)]
    if always_held:
        print(f"{len(always_held)} stocks held in every rebalance:")
        for ticker in sorted(always_held):
            print(f"  {ticker}")
    else:
        print("No stocks held for the entire period")
    
    # Stocks held only once
    print(f"\n{'='*70}")
    print("Stocks Held Only Once")
    print("="*70)
    one_timers = [ticker for ticker, count in ticker_counts.items() if count == 1]
    print(f"{len(one_timers)} stocks held in only one rebalance")
    if len(one_timers) <= 20:
        for ticker in sorted(one_timers):
            print(f"  {ticker}")
    
    return ticker_counts, turnovers

def plot_composition_over_time(df, ticker_counts):
    """Create visualizations of portfolio composition."""
    print(f"\n{'='*70}")
    print("Creating visualizations...")
    print("="*70)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Innovation Factor Portfolio Composition Over Time', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Top 20 stocks by holding frequency
    ax1 = axes[0, 0]
    top_20 = ticker_counts.most_common(20)
    tickers = [t for t, _ in top_20]
    counts = [c for _, c in top_20]
    pcts = [c / len(df) * 100 for c in counts]
    
    ax1.barh(range(len(tickers)), pcts)
    ax1.set_yticks(range(len(tickers)))
    ax1.set_yticklabels(tickers)
    ax1.set_xlabel('% of Time in Portfolio', fontsize=12)
    ax1.set_title('Top 20 Stocks by Holding Frequency', fontsize=14, fontweight='bold')
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
    ax4.hist(holding_periods, bins=20, edgecolor='black', alpha=0.7, color='#F18F01')
    ax4.set_xlabel('Months Held', fontsize=12)
    ax4.set_ylabel('Number of Stocks', fontsize=12)
    ax4.set_title('Distribution of Holding Periods', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axvline(x=np.mean(holding_periods), color='red', linestyle='--', 
               label=f'Mean: {np.mean(holding_periods):.1f} months')
    ax4.legend()
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'innovation_factor_portfolio_composition.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved composition analysis plot to {plot_file}")
    plt.close()
    
    # Create a CSV with detailed composition
    composition_data = []
    for idx, row in df.iterrows():
        if pd.isna(row['tickers']):
            continue
        tickers = row['tickers'].split(',')
        composition_data.append({
            'date': idx,
            'num_stocks': len(tickers),
            'tickers': row['tickers']
        })
    
    composition_df = pd.DataFrame(composition_data)
    composition_file = OUTPUT_DIR / 'innovation_factor_portfolio_composition.csv'
    composition_df.to_csv(composition_file, index=False)
    print(f"✓ Saved detailed composition to {composition_file}")

def main():
    # Change to project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent.parent.parent
    os.chdir(project_root)
    
    df = load_portfolio_composition()
    if df is None:
        return
    
    ticker_counts, turnovers = analyze_composition(df)
    plot_composition_over_time(df, ticker_counts)
    
    print(f"\n{'='*70}")
    print("Analysis Complete!")
    print("="*70)

if __name__ == '__main__':
    main()

