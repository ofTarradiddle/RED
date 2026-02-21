"""
Create comprehensive comparison plots for all RQ lagged versions.
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

OUTPUT_DIR = Path('./data/research/sp500_backtest')
RD_LAGS = [1, 3, 5]


def load_results():
    """Load all lagged RQ backtest results."""
    results = {}
    
    for lag in RD_LAGS:
        file = OUTPUT_DIR / f'rq_factor_lag{lag}_backtest_results.csv'
        if file.exists():
            df = pd.read_csv(file, index_col=0, parse_dates=True)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            results[lag] = df.iloc[:, 0]  # Get returns column
            print(f"Loaded lag {lag}: {len(df)} monthly returns")
        else:
            print(f"Warning: {file} not found")
    
    return results


def load_benchmarks():
    """Load benchmark results for comparison."""
    benchmarks = {}
    
    # S&P 500 EW
    ew_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'
    if ew_file.exists():
        ew_df = pd.read_csv(ew_file, index_col=0, parse_dates=True)
        if ew_df.index.tz is not None:
            ew_df.index = ew_df.index.tz_localize(None)
        
        # Convert daily to monthly
        ew_monthly = ew_df.groupby([ew_df.index.year, ew_df.index.month]).apply(
            lambda x: (1 + x.iloc[:, 0]).prod() - 1
        )
        ew_monthly.index = pd.to_datetime([f'{y}-{m:02d}-01' for y, m in ew_monthly.index])
        benchmarks['S&P 500 EW'] = ew_monthly
        print(f"Loaded S&P 500 EW: {len(ew_monthly)} monthly returns")
    
    # Original RQ (no lag)
    rq_file = OUTPUT_DIR / 'rq_factor_backtest_results.csv'
    if rq_file.exists():
        rq_df = pd.read_csv(rq_file, index_col=0, parse_dates=True)
        if rq_df.index.tz is not None:
            rq_df.index = rq_df.index.tz_localize(None)
        # Convert daily to monthly if needed
        if len(rq_df) > 500:  # Likely daily
            rq_monthly = rq_df.groupby([rq_df.index.year, rq_df.index.month]).apply(
                lambda x: (1 + x.iloc[:, 0]).prod() - 1
            )
            rq_monthly.index = pd.to_datetime([f'{y}-{m:02d}-01' for y, m in rq_monthly.index])
            benchmarks['RQ (No Lag)'] = rq_monthly
        else:
            benchmarks['RQ (No Lag)'] = rq_df.iloc[:, 0]
        print(f"Loaded RQ (No Lag): {len(benchmarks['RQ (No Lag)'])} monthly returns")
    
    return benchmarks


def calculate_metrics(returns: pd.Series) -> dict:
    """Calculate performance metrics."""
    if returns.empty:
        return {}
    
    cum_returns = (1 + returns).cumprod()
    total_return = cum_returns.iloc[-1] - 1.0
    
    years = (returns.index.max() - returns.index.min()).days / 365.25
    cagr = (cum_returns.iloc[-1] ** (1.0 / years)) - 1.0 if years > 0 else np.nan
    
    vol = returns.std() * np.sqrt(12)
    sharpe = (returns.mean() * 12) / vol if vol > 0 else np.nan
    
    # Max drawdown
    running_max = cum_returns.expanding().max()
    drawdown = (cum_returns - running_max) / running_max
    max_dd = drawdown.min()
    
    return {
        'total_return': total_return,
        'cumulative_return': cum_returns.iloc[-1],
        'cagr': cagr,
        'volatility': vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'num_periods': len(returns),
        'years': years
    }


def create_comprehensive_plots(results: dict, benchmarks: dict):
    """Create comprehensive comparison plots."""
    if not results:
        print("No results to plot!")
        return
    
    # Align all series to common date range
    all_series = {**results, **benchmarks}
    if not all_series:
        return
    
    # Find common date range
    min_date = max(s.index.min() for s in all_series.values())
    max_date = min(s.index.max() for s in all_series.values())
    
    print(f"\nPlotting date range: {min_date} to {max_date}")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # Colors
    lag_colors = {1: '#1f77b4', 3: '#2ca02c', 5: '#9467bd'}  # blue, green, purple
    benchmark_colors = {'S&P 500 EW': '#ff7f0e', 'RQ (No Lag)': '#d62728'}  # orange, red
    
    # Plot 1: Cumulative Returns (Main)
    ax1 = fig.add_subplot(gs[0, :])
    
    for lag in RD_LAGS:
        if lag in results:
            returns = results[lag]
            returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
            if not returns_aligned.empty:
                cum_returns = (1 + returns_aligned).cumprod()
                ax1.plot(cum_returns.index, cum_returns.values,
                        label=f'RQ Factor (R&D Lag {lag})', linewidth=2.5, color=lag_colors[lag])
    
    for name, returns in benchmarks.items():
        returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
        if not returns_aligned.empty:
            cum_returns = (1 + returns_aligned).cumprod()
            ax1.plot(cum_returns.index, cum_returns.values,
                    label=name, linewidth=2.5, color=benchmark_colors.get(name, 'gray'),
                    linestyle='--' if name == 'S&P 500 EW' else '-')
    
    ax1.set_title('RQ Factor Portfolio: Comparison of R&D Lag Structures\n'
                 'Top 50 by Research Quotient (Pooled Fixed Effects)', 
                 fontsize=16, fontweight='bold', pad=20)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend(fontsize=11, loc='upper left', ncol=2)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('linear')
    
    # Plot 2: Monthly Returns
    ax2 = fig.add_subplot(gs[1, 0])
    
    for lag in RD_LAGS:
        if lag in results:
            returns = results[lag]
            returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
            if not returns_aligned.empty:
                ax2.plot(returns_aligned.index, returns_aligned.values * 100,
                        label=f'Lag {lag}', linewidth=1.5, color=lag_colors[lag], 
                        alpha=0.7, marker='o', markersize=2)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    ax2.set_title('Monthly Returns: Lagged RQ Versions', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=11)
    ax2.set_ylabel('Monthly Return (%)', fontsize=11)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling Sharpe Ratio (12-month)
    ax3 = fig.add_subplot(gs[1, 1])
    
    for lag in RD_LAGS:
        if lag in results:
            returns = results[lag]
            returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
            if not returns_aligned.empty:
                rolling_sharpe = returns_aligned.rolling(12).apply(
                    lambda x: (x.mean() * 12) / (x.std() * np.sqrt(12)) if x.std() > 0 else np.nan
                )
                ax3.plot(rolling_sharpe.index, rolling_sharpe.values,
                        label=f'Lag {lag}', linewidth=2, color=lag_colors[lag])
    
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    ax3.set_title('Rolling 12-Month Sharpe Ratio', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=11)
    ax3.set_ylabel('Sharpe Ratio', fontsize=11)
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Drawdown
    ax4 = fig.add_subplot(gs[2, 0])
    
    for lag in RD_LAGS:
        if lag in results:
            returns = results[lag]
            returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
            if not returns_aligned.empty:
                cum_returns = (1 + returns_aligned).cumprod()
                running_max = cum_returns.expanding().max()
                drawdown = (cum_returns - running_max) / running_max
                ax4.fill_between(drawdown.index, drawdown.values, 0,
                                alpha=0.3, color=lag_colors[lag])
                ax4.plot(drawdown.index, drawdown.values,
                        label=f'Lag {lag}', linewidth=1.5, color=lag_colors[lag])
    
    ax4.set_title('Drawdown', fontsize=13, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=11)
    ax4.set_ylabel('Drawdown', fontsize=11)
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(bottom=-0.6)
    
    # Plot 5: Performance Metrics Comparison (Bar Chart)
    ax5 = fig.add_subplot(gs[2, 1])
    
    all_metrics = {}
    for lag in RD_LAGS:
        if lag in results:
            returns = results[lag]
            returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
            if not returns_aligned.empty:
                all_metrics[f'Lag {lag}'] = calculate_metrics(returns_aligned)
    
    for name, returns in benchmarks.items():
        returns_aligned = returns[(returns.index >= min_date) & (returns.index <= max_date)]
        if not returns_aligned.empty:
            all_metrics[name] = calculate_metrics(returns_aligned)
    
    # Create bar chart for CAGR
    if all_metrics:
        labels = list(all_metrics.keys())
        cagrs = [all_metrics[m].get('cagr', 0) * 100 for m in labels]
        colors_list = [lag_colors.get(int(l.split()[1]), benchmark_colors.get(l, 'gray')) 
                       if l.startswith('Lag') else benchmark_colors.get(l, 'gray') 
                       for l in labels]
        
        bars = ax5.bar(labels, cagrs, color=colors_list, alpha=0.7, edgecolor='black', linewidth=1)
        ax5.set_title('CAGR Comparison (%)', fontsize=13, fontweight='bold')
        ax5.set_ylabel('CAGR (%)', fontsize=11)
        ax5.tick_params(axis='x', rotation=45)
        ax5.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}%', ha='center', va='bottom', fontsize=9)
    
    plt.suptitle('RQ Factor Backtest: Comprehensive Analysis of R&D Lag Structures', 
                fontsize=18, fontweight='bold', y=0.995)
    
    plot_file = OUTPUT_DIR / 'rq_factor_lagged_comprehensive_comparison.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved comprehensive plot to {plot_file}")
    plt.close()
    
    # Print performance summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    
    for name, metrics in all_metrics.items():
        print(f"\n{name}:")
        print(f"  Cumulative Return: {metrics.get('cumulative_return', 0):.4f}x")
        print(f"  Total Return: {metrics.get('total_return', 0):.2%}")
        print(f"  CAGR: {metrics.get('cagr', 0):.2%}")
        print(f"  Volatility: {metrics.get('volatility', 0):.2%}")
        print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.4f}")
        print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
        print(f"  Periods: {metrics.get('num_periods', 0)} months")


def main():
    """Main execution."""
    print("=" * 80)
    print("RQ Lagged Backtest: Comprehensive Comparison Plotting")
    print("=" * 80)
    
    # Load results
    results = load_results()
    benchmarks = load_benchmarks()
    
    if not results:
        print("No results found! Make sure the backtest has completed.")
        return
    
    # Create plots
    create_comprehensive_plots(results, benchmarks)
    
    print("\n" + "=" * 80)
    print("Plotting Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()

