"""
Analyze the impact of missing returns data on backtest performance.

This script:
1. Visualizes missing data trends over time
2. Analyzes correlation between missing data and performance
3. Compares portfolio vs benchmark during high/low missing data periods
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path('./data/research/sp500_backtest')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load backtest results and missing returns statistics."""
    logger.info("Loading data...")
    
    # Load missing returns statistics
    missing_stats_file = OUTPUT_DIR / 'missing_returns_statistics.csv'
    if not missing_stats_file.exists():
        logger.error(f"Missing returns statistics file not found: {missing_stats_file}")
        return None, None, None
    
    missing_stats_df = pd.read_csv(missing_stats_file)
    missing_stats_df['rebalance_date'] = pd.to_datetime(missing_stats_df['rebalance_date'])
    
    # Load portfolio returns
    portfolio_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'
    if not portfolio_file.exists():
        logger.error(f"Portfolio results file not found: {portfolio_file}")
        return None, None, None
    
    portfolio_df = pd.read_csv(portfolio_file, index_col=0, parse_dates=True)
    
    # Load metrics
    metrics_file = OUTPUT_DIR / 'sp500_ew_backtest_metrics.json'
    benchmark_returns = None
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
        # Note: benchmark returns would need to be loaded separately if available
    
    logger.info(f"Loaded {len(missing_stats_df)} rebalance periods")
    logger.info(f"Loaded {len(portfolio_df)} portfolio return observations")
    
    return missing_stats_df, portfolio_df, benchmark_returns


def create_missing_data_trends_plot(missing_stats_df: pd.DataFrame):
    """Create visualization of missing data trends over time."""
    logger.info("Creating missing data trends visualization...")
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    
    # Plot 1: Missing constituents at rebalance over time
    ax1 = axes[0]
    ax1.plot(missing_stats_df['rebalance_date'], missing_stats_df['missing_at_rebalance'], 
             alpha=0.6, linewidth=1, color='red', label='Missing at Rebalance')
    ax1.fill_between(missing_stats_df['rebalance_date'], 0, missing_stats_df['missing_at_rebalance'], 
                     alpha=0.3, color='red')
    ax1.axhline(y=missing_stats_df['missing_at_rebalance'].mean(), color='darkred', 
                linestyle='--', linewidth=2, label=f'Mean: {missing_stats_df["missing_at_rebalance"].mean():.1f}')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Number of Missing Constituents', fontsize=12)
    ax1.set_title('Missing Constituents at Rebalance Over Time', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: % Missing at rebalance over time
    ax2 = axes[1]
    ax2.plot(missing_stats_df['rebalance_date'], missing_stats_df['missing_pct_at_rebalance'], 
             alpha=0.6, linewidth=1, color='orange', label='% Missing at Rebalance')
    ax2.fill_between(missing_stats_df['rebalance_date'], 0, missing_stats_df['missing_pct_at_rebalance'], 
                     alpha=0.3, color='orange')
    ax2.axhline(y=missing_stats_df['missing_pct_at_rebalance'].mean(), color='darkorange', 
                linestyle='--', linewidth=2, label=f'Mean: {missing_stats_df["missing_pct_at_rebalance"].mean():.2f}%')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('% Missing', fontsize=12)
    ax2.set_title('% Missing Constituents at Rebalance Over Time', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Average % portfolio missing per day during holding periods
    ax3 = axes[2]
    ax3.plot(missing_stats_df['rebalance_date'], missing_stats_df['pct_avg_missing'], 
             alpha=0.6, linewidth=1, color='purple', label='Avg % Portfolio Missing/Day')
    ax3.fill_between(missing_stats_df['rebalance_date'], 0, missing_stats_df['pct_avg_missing'], 
                     alpha=0.3, color='purple')
    ax3.axhline(y=missing_stats_df['pct_avg_missing'].mean(), color='darkviolet', 
                linestyle='--', linewidth=2, label=f'Mean: {missing_stats_df["pct_avg_missing"].mean():.2f}%')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('% Portfolio Missing', fontsize=12)
    ax3.set_title('Average % of Portfolio Missing Per Day During Holding Periods', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'missing_data_trends.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved missing data trends plot to {plot_file}")
    
    plt.close()


def analyze_correlation_with_performance(missing_stats_df: pd.DataFrame, portfolio_df: pd.DataFrame):
    """Analyze correlation between missing data and portfolio performance."""
    logger.info("Analyzing correlation between missing data and performance...")
    
    # Merge missing stats with portfolio returns by rebalance month
    portfolio_df['rebalance_month'] = pd.to_datetime(portfolio_df['rebalance_month'] + '-01')
    
    # Calculate monthly returns for portfolio
    portfolio_monthly = portfolio_df.groupby('rebalance_month').agg({
        'portfolio_return': lambda x: (1 + x).prod() - 1,  # Compound return
        'n_stocks': 'mean',
        'total_stocks': 'mean'
    }).reset_index()
    
    # Merge with missing stats
    missing_stats_df['rebalance_month'] = pd.to_datetime(missing_stats_df['rebalance_month'] + '-01')
    merged = portfolio_monthly.merge(
        missing_stats_df[['rebalance_month', 'missing_at_rebalance', 'missing_pct_at_rebalance', 
                         'pct_avg_missing', 'avg_missing_per_day']],
        on='rebalance_month',
        how='inner'
    )
    
    # Calculate correlations
    correlations = {
        'missing_at_rebalance_vs_return': merged['missing_at_rebalance'].corr(merged['portfolio_return']),
        'missing_pct_at_rebalance_vs_return': merged['missing_pct_at_rebalance'].corr(merged['portfolio_return']),
        'pct_avg_missing_vs_return': merged['pct_avg_missing'].corr(merged['portfolio_return']),
        'avg_missing_per_day_vs_return': merged['avg_missing_per_day'].corr(merged['portfolio_return'])
    }
    
    logger.info("\n" + "="*70)
    logger.info("Correlation Analysis: Missing Data vs Performance")
    logger.info("="*70)
    for key, value in correlations.items():
        logger.info(f"  {key}: {value:.4f}")
    
    # Create scatter plots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Missing at rebalance vs monthly return
    ax1 = axes[0, 0]
    ax1.scatter(merged['missing_at_rebalance'], merged['portfolio_return'] * 100, 
               alpha=0.5, s=30, color='red')
    ax1.set_xlabel('Missing Constituents at Rebalance', fontsize=12)
    ax1.set_ylabel('Monthly Return (%)', fontsize=12)
    ax1.set_title(f'Missing at Rebalance vs Monthly Return\n(Correlation: {correlations["missing_at_rebalance_vs_return"]:.4f})', 
                 fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    
    # Plot 2: % Missing at rebalance vs monthly return
    ax2 = axes[0, 1]
    ax2.scatter(merged['missing_pct_at_rebalance'], merged['portfolio_return'] * 100, 
               alpha=0.5, s=30, color='orange')
    ax2.set_xlabel('% Missing at Rebalance', fontsize=12)
    ax2.set_ylabel('Monthly Return (%)', fontsize=12)
    ax2.set_title(f'% Missing at Rebalance vs Monthly Return\n(Correlation: {correlations["missing_pct_at_rebalance_vs_return"]:.4f})', 
                 fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    
    # Plot 3: Avg % missing per day vs monthly return
    ax3 = axes[1, 0]
    ax3.scatter(merged['pct_avg_missing'], merged['portfolio_return'] * 100, 
               alpha=0.5, s=30, color='purple')
    ax3.set_xlabel('Avg % Portfolio Missing Per Day', fontsize=12)
    ax3.set_ylabel('Monthly Return (%)', fontsize=12)
    ax3.set_title(f'Avg % Missing Per Day vs Monthly Return\n(Correlation: {correlations["pct_avg_missing_vs_return"]:.4f})', 
                 fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    
    # Plot 4: Avg missing per day vs monthly return
    ax4 = axes[1, 1]
    ax4.scatter(merged['avg_missing_per_day'], merged['portfolio_return'] * 100, 
               alpha=0.5, s=30, color='blue')
    ax4.set_xlabel('Avg Missing Stocks Per Day', fontsize=12)
    ax4.set_ylabel('Monthly Return (%)', fontsize=12)
    ax4.set_title(f'Avg Missing Per Day vs Monthly Return\n(Correlation: {correlations["avg_missing_per_day_vs_return"]:.4f})', 
                 fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'missing_data_correlation_analysis.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved correlation analysis plot to {plot_file}")
    
    plt.close()
    
    return correlations, merged


def compare_high_low_missing_periods(missing_stats_df: pd.DataFrame, portfolio_df: pd.DataFrame):
    """Compare performance during high vs low missing data periods."""
    logger.info("Comparing performance during high vs low missing data periods...")
    
    # Identify high and low missing data periods
    median_missing = missing_stats_df['pct_avg_missing'].median()
    high_missing = missing_stats_df[missing_stats_df['pct_avg_missing'] >= median_missing]
    low_missing = missing_stats_df[missing_stats_df['pct_avg_missing'] < median_missing]
    
    # Get portfolio returns for each period
    # Convert rebalance_month to datetime if it's a string
    if portfolio_df['rebalance_month'].dtype == 'object':
        portfolio_df['rebalance_month'] = pd.to_datetime(portfolio_df['rebalance_month'] + '-01')
    if missing_stats_df['rebalance_month'].dtype == 'object':
        missing_stats_df['rebalance_month'] = pd.to_datetime(missing_stats_df['rebalance_month'] + '-01')
    
    # Merge
    portfolio_with_missing = portfolio_df.merge(
        missing_stats_df[['rebalance_month', 'pct_avg_missing']],
        on='rebalance_month',
        how='left'
    )
    
    high_missing_returns = portfolio_with_missing[
        portfolio_with_missing['pct_avg_missing'] >= median_missing
    ]['portfolio_return']
    
    low_missing_returns = portfolio_with_missing[
        portfolio_with_missing['pct_avg_missing'] < median_missing
    ]['portfolio_return']
    
    # Calculate statistics
    high_stats = {
        'count': len(high_missing_returns),
        'mean_return': high_missing_returns.mean() * 100,
        'std_return': high_missing_returns.std() * 100,
        'total_return': ((1 + high_missing_returns).prod() - 1) * 100,
        'sharpe': (high_missing_returns.mean() / high_missing_returns.std() * np.sqrt(252)) if high_missing_returns.std() > 0 else 0
    }
    
    low_stats = {
        'count': len(low_missing_returns),
        'mean_return': low_missing_returns.mean() * 100,
        'std_return': low_missing_returns.std() * 100,
        'total_return': ((1 + low_missing_returns).prod() - 1) * 100,
        'sharpe': (low_missing_returns.mean() / low_missing_returns.std() * np.sqrt(252)) if low_missing_returns.std() > 0 else 0
    }
    
    logger.info("\n" + "="*70)
    logger.info("Performance Comparison: High vs Low Missing Data Periods")
    logger.info("="*70)
    logger.info(f"\nHigh Missing Data Periods (≥{median_missing:.2f}% avg missing):")
    logger.info(f"  Observations: {high_stats['count']}")
    logger.info(f"  Mean Daily Return: {high_stats['mean_return']:.4f}%")
    logger.info(f"  Std Dev: {high_stats['std_return']:.4f}%")
    logger.info(f"  Total Return: {high_stats['total_return']:.2f}%")
    logger.info(f"  Sharpe Ratio: {high_stats['sharpe']:.4f}")
    
    logger.info(f"\nLow Missing Data Periods (<{median_missing:.2f}% avg missing):")
    logger.info(f"  Observations: {low_stats['count']}")
    logger.info(f"  Mean Daily Return: {low_stats['mean_return']:.4f}%")
    logger.info(f"  Std Dev: {low_stats['std_return']:.4f}%")
    logger.info(f"  Total Return: {low_stats['total_return']:.2f}%")
    logger.info(f"  Sharpe Ratio: {low_stats['sharpe']:.4f}")
    
    # Create comparison plot
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    
    # Plot 1: Cumulative returns comparison
    ax1 = axes[0]
    high_cumulative = (1 + high_missing_returns).cumprod()
    low_cumulative = (1 + low_missing_returns).cumprod()
    
    ax1.plot(range(len(high_cumulative)), high_cumulative.values, 
             label=f'High Missing Data (≥{median_missing:.1f}%)', linewidth=2, color='red', alpha=0.7)
    ax1.plot(range(len(low_cumulative)), low_cumulative.values, 
             label=f'Low Missing Data (<{median_missing:.1f}%)', linewidth=2, color='green', alpha=0.7)
    ax1.set_xlabel('Observation Number', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.set_title('Cumulative Returns: High vs Low Missing Data Periods', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    # Plot 2: Return distribution comparison
    ax2 = axes[1]
    ax2.hist(high_missing_returns * 100, bins=50, alpha=0.6, label=f'High Missing (≥{median_missing:.1f}%)', 
            color='red', density=True)
    ax2.hist(low_missing_returns * 100, bins=50, alpha=0.6, label=f'Low Missing (<{median_missing:.1f}%)', 
            color='green', density=True)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    ax2.set_xlabel('Daily Return (%)', fontsize=12)
    ax2.set_ylabel('Density', fontsize=12)
    ax2.set_title('Return Distribution: High vs Low Missing Data Periods', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'high_low_missing_comparison.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved high/low missing comparison plot to {plot_file}")
    
    plt.close()
    
    return high_stats, low_stats


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("Missing Returns Impact Analysis")
    logger.info("="*70)
    
    # Load data
    missing_stats_df, portfolio_df, benchmark_returns = load_data()
    
    if missing_stats_df is None or portfolio_df is None:
        logger.error("Failed to load required data. Exiting.")
        return
    
    # Create visualizations
    create_missing_data_trends_plot(missing_stats_df)
    
    # Analyze correlations
    correlations, merged = analyze_correlation_with_performance(missing_stats_df, portfolio_df)
    
    # Compare high vs low missing periods
    high_stats, low_stats = compare_high_low_missing_periods(missing_stats_df, portfolio_df)
    
    # Save summary
    summary = {
        'correlations': correlations,
        'high_missing_periods': high_stats,
        'low_missing_periods': low_stats,
        'analysis_date': datetime.now().isoformat()
    }
    
    summary_file = OUTPUT_DIR / 'missing_data_impact_analysis.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"\n✓ Saved impact analysis summary to {summary_file}")
    
    logger.info("\n" + "="*70)
    logger.info("Analysis Complete!")
    logger.info("="*70)


if __name__ == '__main__':
    main()

