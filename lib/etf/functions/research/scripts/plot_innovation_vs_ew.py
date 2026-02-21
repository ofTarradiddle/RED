"""
Plot Innovation Factor Portfolio vs Equal-Weighted S&P 500 Backtest
"""

import sys
from pathlib import Path
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# File paths
OUTPUT_DIR = Path('./data/research/sp500_backtest')
INNOVATION_RESULTS = OUTPUT_DIR / 'innovation_factor_backtest_results.csv'
EW_RESULTS = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'

def load_innovation_results():
    """Load innovation factor backtest results (monthly returns)."""
    df = pd.read_csv(INNOVATION_RESULTS, index_col=0, parse_dates=True)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    # Convert index to month-end for alignment
    df.index = pd.to_datetime(df.index).to_period('M').to_timestamp('M')
    return df['return']

def load_ew_results():
    """Load equal-weighted backtest results (daily returns) and convert to monthly."""
    df = pd.read_csv(EW_RESULTS, index_col=0, parse_dates=True)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Filter to 2004 and after
    df = df[df.index >= pd.to_datetime('2004-01-01')]
    
    # Convert daily returns to monthly returns
    if 'portfolio_return' in df.columns:
        daily_returns = df['portfolio_return'].dropna()
        # Resample to month-end and compound returns
        monthly_returns = daily_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        # Convert index to month-end timestamp for alignment
        monthly_returns.index = monthly_returns.index.to_period('M').to_timestamp('M')
        return monthly_returns
    elif 'return' in df.columns:
        df.index = pd.to_datetime(df.index).to_period('M').to_timestamp('M')
        return df['return']
    else:
        return pd.Series(dtype=float)

def plot_comparison():
    """Create comparison plot."""
    print("Loading results...")
    innovation_returns = load_innovation_results()
    ew_returns = load_ew_results()
    
    print(f"Innovation Factor: {len(innovation_returns)} monthly returns")
    print(f"Equal Weight: {len(ew_returns)} monthly returns")
    
    # Calculate cumulative returns
    innovation_cum = (1 + innovation_returns).cumprod()
    ew_cum = (1 + ew_returns).cumprod()
    
    # Find common dates
    common_dates = innovation_cum.index.intersection(ew_cum.index)
    print(f"Common dates: {len(common_dates)} months")
    
    if len(common_dates) == 0:
        print("ERROR: No overlapping dates!")
        return
    
    # Align and normalize
    innovation_aligned = innovation_cum.loc[common_dates]
    ew_aligned = ew_cum.loc[common_dates]
    
    # Normalize EW to start at same value as Innovation
    normalization_factor = innovation_aligned.iloc[0] / ew_aligned.iloc[0]
    ew_aligned = ew_aligned * normalization_factor
    
    # Create plot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Innovation Factor vs Equal-Weighted S&P 500 (2004-2025)', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Cumulative Returns Comparison
    ax1 = axes[0, 0]
    ax1.plot(innovation_aligned.index, innovation_aligned.values, 
             label='Innovation Factor Portfolio', linewidth=2.5, color='#2E86AB')
    ax1.plot(ew_aligned.index, ew_aligned.values, 
             label='S&P 500 Equal-Weighted (Backtest)', linewidth=2.5, 
             color='#A23B72', linestyle='-')
    # Use linear scale (not log)
    # ax1.set_yscale('log')  # Commented out - using linear scale
    ax1.set_title('Cumulative Returns Comparison', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 2: Monthly Returns Comparison
    ax2 = axes[0, 1]
    innovation_monthly = innovation_returns.loc[common_dates]
    ew_monthly = ew_returns.loc[common_dates]
    
    ax2.plot(innovation_monthly.index, innovation_monthly.values, 
             label='Innovation Factor', linewidth=1, alpha=0.7, color='#2E86AB')
    ax2.plot(ew_monthly.index, ew_monthly.values, 
             label='S&P 500 EW', linewidth=1, alpha=0.7, color='#A23B72')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Monthly Returns Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Monthly Return', fontsize=12)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 3: Rolling Sharpe Ratio (12-month)
    ax3 = axes[1, 0]
    innovation_sharpe = innovation_monthly.rolling(12).mean() / innovation_monthly.rolling(12).std() * np.sqrt(12)
    ew_sharpe = ew_monthly.rolling(12).mean() / ew_monthly.rolling(12).std() * np.sqrt(12)
    
    ax3.plot(innovation_sharpe.index, innovation_sharpe.values, 
             label='Innovation Factor', linewidth=2, color='#2E86AB')
    ax3.plot(ew_sharpe.index, ew_sharpe.values, 
             label='S&P 500 EW', linewidth=2, color='#A23B72')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Rolling 12-Month Sharpe Ratio', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Sharpe Ratio', fontsize=12)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax3.xaxis.set_major_locator(mdates.YearLocator(2))
    
    # Plot 4: Drawdown Comparison
    ax4 = axes[1, 1]
    
    # Innovation drawdown
    innovation_running_max = innovation_aligned.expanding().max()
    innovation_drawdown = (innovation_aligned - innovation_running_max) / innovation_running_max
    
    # EW drawdown
    ew_running_max = ew_aligned.expanding().max()
    ew_drawdown = (ew_aligned - ew_running_max) / ew_running_max
    
    ax4.fill_between(innovation_drawdown.index, innovation_drawdown.values, 0, 
                     alpha=0.3, color='#2E86AB', label='Innovation Factor')
    ax4.plot(innovation_drawdown.index, innovation_drawdown.values, 
             linewidth=1.5, color='#2E86AB')
    
    ax4.fill_between(ew_drawdown.index, ew_drawdown.values, 0, 
                     alpha=0.3, color='#A23B72', label='S&P 500 EW')
    ax4.plot(ew_drawdown.index, ew_drawdown.values, 
             linewidth=1.5, color='#A23B72')
    
    ax4.set_title('Drawdown Comparison', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=12)
    ax4.set_ylabel('Drawdown', fontsize=12)
    ax4.legend(fontsize=11)
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax4.xaxis.set_major_locator(mdates.YearLocator(2))
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'innovation_factor_vs_ew_comparison.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved comparison plot to {plot_file}")
    plt.close()
    
    # Print performance metrics
    print("\n" + "="*70)
    print("Performance Metrics Comparison (2004-2025)")
    print("="*70)
    
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
    
    innovation_metrics = calc_metrics(innovation_monthly)
    ew_metrics = calc_metrics(ew_monthly)
    
    print(f"\nInnovation Factor Portfolio:")
    print(f"  Total Return: {innovation_metrics['total_return']:.2%}")
    print(f"  CAGR: {innovation_metrics['cagr']:.2%}")
    print(f"  Volatility: {innovation_metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {innovation_metrics['sharpe']:.4f}")
    print(f"  Max Drawdown: {innovation_metrics['max_drawdown']:.2%}")
    
    print(f"\nS&P 500 Equal-Weighted:")
    print(f"  Total Return: {ew_metrics['total_return']:.2%}")
    print(f"  CAGR: {ew_metrics['cagr']:.2%}")
    print(f"  Volatility: {ew_metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {ew_metrics['sharpe']:.4f}")
    print(f"  Max Drawdown: {ew_metrics['max_drawdown']:.2%}")
    
    print(f"\nOutperformance:")
    print(f"  Total Return: {(innovation_metrics['total_return'] - ew_metrics['total_return']):.2%}")
    print(f"  CAGR: {(innovation_metrics['cagr'] - ew_metrics['cagr']):.2%}")
    print(f"  Sharpe Difference: {(innovation_metrics['sharpe'] - ew_metrics['sharpe']):.4f}")
    print("="*70)

if __name__ == '__main__':
    plot_comparison()

