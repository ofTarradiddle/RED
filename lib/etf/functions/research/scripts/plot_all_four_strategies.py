"""
Plot comparison of all 4 backtest strategies:
1. Innovation Factor Only
2. R&D/Sales + Innovation Factor
3. RQ Factor
4. S&P 500 Equal-Weighted
"""

import sys
from pathlib import Path
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# File paths
OUTPUT_DIR = Path('./data/research/sp500_backtest')

# Load all backtest results
innovation_file = OUTPUT_DIR / 'innovation_factor_backtest_results.csv'
rd_sales_innovation_file = OUTPUT_DIR / 'rd_mcap_innovation_backtest_results.csv'
rq_file = OUTPUT_DIR / 'rq_factor_backtest_results.csv'
ew_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'

print("Loading backtest results...")

# Load Innovation Factor
innovation_df = pd.read_csv(innovation_file, index_col=0, parse_dates=True)
if innovation_df.index.tz is not None:
    innovation_df.index = innovation_df.index.tz_localize(None)
innovation_returns = innovation_df.iloc[:, 0]

# Load R&D/Sales + Innovation Factor
rd_sales_innovation_df = pd.read_csv(rd_sales_innovation_file, index_col=0, parse_dates=True)
if rd_sales_innovation_df.index.tz is not None:
    rd_sales_innovation_df.index = rd_sales_innovation_df.index.tz_localize(None)
rd_sales_innovation_returns = rd_sales_innovation_df.iloc[:, 0]

# Load RQ Factor
rq_df = pd.read_csv(rq_file, index_col=0, parse_dates=True)
if rq_df.index.tz is not None:
    rq_df.index = rq_df.index.tz_localize(None)
rq_returns = rq_df.iloc[:, 0]

# Load S&P 500 EW (daily, convert to monthly)
ew_df = pd.read_csv(ew_file, index_col=0, parse_dates=True)
if ew_df.index.tz is not None:
    ew_df.index = ew_df.index.tz_localize(None)
ew_daily = ew_df.iloc[:, 0]

# Convert EW daily returns to monthly
ew_monthly = ew_daily.groupby([ew_daily.index.year, ew_daily.index.month]).apply(
    lambda x: (1 + x).prod() - 1
)
ew_monthly.index = pd.to_datetime([f'{y}-{m:02d}-01' for y, m in ew_monthly.index])

# Find common period
common_start = max(
    innovation_returns.index.min(),
    rd_sales_innovation_returns.index.min(),
    rq_returns.index.min(),
    ew_monthly.index.min()
)
common_end = min(
    innovation_returns.index.max(),
    rd_sales_innovation_returns.index.max(),
    rq_returns.index.max(),
    ew_monthly.index.max()
)

print(f'Common period: {common_start} to {common_end}')

# Align all to common period
innovation_aligned = innovation_returns[(innovation_returns.index >= common_start) & 
                                       (innovation_returns.index <= common_end)]
rd_sales_innovation_aligned = rd_sales_innovation_returns[(rd_sales_innovation_returns.index >= common_start) & 
                                                          (rd_sales_innovation_returns.index <= common_end)]
rq_aligned = rq_returns[(rq_returns.index >= common_start) & 
                        (rq_returns.index <= common_end)]
ew_aligned = ew_monthly[(ew_monthly.index >= common_start) & 
                       (ew_monthly.index <= common_end)]

print(f'Innovation Factor: {len(innovation_aligned)} months')
print(f'R&D/Sales + Innovation: {len(rd_sales_innovation_aligned)} months')
print(f'RQ Factor: {len(rq_aligned)} months')
print(f'S&P 500 EW: {len(ew_aligned)} months')

# Calculate cumulative returns
innovation_cum = (1 + innovation_aligned).cumprod()
rd_sales_innovation_cum = (1 + rd_sales_innovation_aligned).cumprod()
rq_cum = (1 + rq_aligned).cumprod()
ew_cum = (1 + ew_aligned).cumprod()

# Normalize all to start at 1.0 for fair comparison
innovation_cum_normalized = innovation_cum / innovation_cum.iloc[0]
rd_sales_innovation_cum_normalized = rd_sales_innovation_cum / rd_sales_innovation_cum.iloc[0]
rq_cum_normalized = rq_cum / rq_cum.iloc[0]
ew_cum_normalized = ew_cum / ew_cum.iloc[0]

# Create plot
fig, axes = plt.subplots(2, 1, figsize=(16, 11))

# Plot 1: Cumulative Returns (LINEAR SCALE)
ax1 = axes[0]
ax1.plot(innovation_cum_normalized.index, innovation_cum_normalized.values, 
         label='Innovation Factor Only', linewidth=2.5, color='blue')
ax1.plot(rd_sales_innovation_cum_normalized.index, rd_sales_innovation_cum_normalized.values,
         label='R&D/Sales + Innovation Factor', linewidth=2.5, color='green')
ax1.plot(rq_cum_normalized.index, rq_cum_normalized.values,
         label='RQ Factor', linewidth=2.5, color='purple')
ax1.plot(ew_cum_normalized.index, ew_cum_normalized.values,
         label='S&P 500 Equal-Weighted', linewidth=2.5, color='orange', linestyle='--')

ax1.set_title('Cumulative Returns Comparison: All Four Strategies', 
              fontsize=16, fontweight='bold')
ax1.set_xlabel('Date', fontsize=12)
ax1.set_ylabel('Cumulative Return (Normalized to 1.0)', fontsize=12)
ax1.legend(fontsize=11, loc='upper left')
ax1.grid(True, alpha=0.3)

# Plot 2: Monthly Returns Comparison
ax2 = axes[1]
# Align monthly returns for comparison
common_dates = innovation_aligned.index.intersection(ew_aligned.index).intersection(
    rd_sales_innovation_aligned.index.intersection(rq_aligned.index)
)

if len(common_dates) > 0:
    ax2.plot(common_dates, innovation_aligned.loc[common_dates].values * 100, 
             label='Innovation Factor Only', linewidth=1.5, color='blue', alpha=0.7, marker='o', markersize=2)
    ax2.plot(common_dates, rd_sales_innovation_aligned.loc[common_dates].values * 100,
             label='R&D/Sales + Innovation Factor', linewidth=1.5, color='green', alpha=0.7, marker='s', markersize=2)
    ax2.plot(common_dates, rq_aligned.loc[common_dates].values * 100,
             label='RQ Factor', linewidth=1.5, color='purple', alpha=0.7, marker='^', markersize=2)
    ax2.plot(common_dates, ew_aligned.loc[common_dates].values * 100,
             label='S&P 500 EW', linewidth=1.5, color='orange', alpha=0.7, marker='d', markersize=2)

ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
ax2.set_title('Monthly Returns Comparison', fontsize=14, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12)
ax2.set_ylabel('Monthly Return (%)', fontsize=12)
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3)

plt.tight_layout()

# Save plot
output_file = OUTPUT_DIR / 'all_four_strategies_comparison.png'
output_file.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f'\n✓ Saved comparison plot to {output_file}')

# Calculate performance metrics
def calc_metrics(returns, name):
    cum = (1 + returns).cumprod()
    total_return_factor = cum.iloc[-1]
    total_return_pct = (cum.iloc[-1] - 1.0) * 100
    years = (returns.index.max() - returns.index.min()).days / 365.25
    cagr = (cum.iloc[-1] ** (1.0 / years)) - 1.0 if years > 0 else np.nan
    vol = returns.std() * np.sqrt(12)
    sharpe = (returns.mean() * 12) / vol if vol > 0 else np.nan
    
    # Max drawdown
    running_max = cum.expanding().max()
    drawdown = (cum - running_max) / running_max
    max_dd = drawdown.min()
    
    return {
        'name': name,
        'total_return_factor': total_return_factor,
        'total_return_pct': total_return_pct,
        'cagr': cagr,
        'volatility': vol,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'years': years
    }

innovation_metrics = calc_metrics(innovation_aligned, 'Innovation Factor Only')
rd_sales_innovation_metrics = calc_metrics(rd_sales_innovation_aligned, 'R&D/Sales + Innovation Factor')
rq_metrics = calc_metrics(rq_aligned, 'RQ Factor')
ew_metrics = calc_metrics(ew_aligned, 'S&P 500 EW')

print('\n' + '='*70)
print('Performance Comparison (Common Period)')
print('='*70)

for metrics in [innovation_metrics, rd_sales_innovation_metrics, rq_metrics, ew_metrics]:
    print(f"\n{metrics['name']}:")
    print(f"  Cumulative Return: {metrics['total_return_factor']:.4f}x")
    print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
    print(f"  CAGR: {metrics['cagr']:.2%}")
    print(f"  Volatility: {metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe']:.4f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")

print(f"\n{'='*70}")
print("Outperformance vs S&P 500 EW:")
print(f"{'='*70}")
for metrics in [innovation_metrics, rd_sales_innovation_metrics, rq_metrics]:
    print(f"\n{metrics['name']}:")
    print(f"  Cumulative Return: +{(metrics['total_return_factor'] - ew_metrics['total_return_factor']):.4f}x")
    print(f"  CAGR: +{(metrics['cagr'] - ew_metrics['cagr']):.2%}")
    print(f"  Sharpe: +{(metrics['sharpe'] - ew_metrics['sharpe']):.4f}")

plt.close()

