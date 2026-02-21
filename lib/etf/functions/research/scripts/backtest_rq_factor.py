"""
Backtest RQ (Research Quotient) Factor Portfolio
Monthly rebalanced portfolio selecting top 50 stocks by RQ coefficient.

RQ Factor = Firm-specific output elasticity of R&D from pooled fixed effects regression
- Uses mixed-effects model (per Anne Marie Knott's RQ paper)
- Pooled regression across all firms in 7-year rolling window
- RQ = fixed gamma + firm-specific random gamma
"""

import sys
from pathlib import Path
import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.factors import estimate_rq_mixedlm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents.csv')
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
FUNDAMENTALS_DIR = Path('./data/research/sp500_fundamentals')
OUTPUT_DIR = Path('./data/research/sp500_backtest')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Backtest parameters
START_YEAR = 2004
TOP_N = 50
RQ_WINDOW_YEARS = 7  # 7-year rolling window per Knott


def load_monthly_constituents() -> Dict[str, List[str]]:
    """Load monthly S&P 500 constituents."""
    logger.info("Loading monthly constituents...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return {}
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to START_YEAR and after
    df = df[df['date'].dt.year >= START_YEAR]
    
    # Group by date
    constituents_by_date = {}
    for date, group in df.groupby('date'):
        date_str = date.strftime('%Y-%m-%d')
        constituents_by_date[date_str] = sorted(group['symbol'].unique().tolist())
    
    logger.info(f"Loaded constituents for {len(constituents_by_date)} months (from {START_YEAR})")
    logger.info(f"Date range: {min(constituents_by_date.keys())} to {max(constituents_by_date.keys())}")
    
    return constituents_by_date


def load_returns() -> pd.DataFrame:
    """Load returns data."""
    logger.info("Loading returns data...")
    
    if not RETURNS_FILE.exists():
        logger.error(f"Returns file not found: {RETURNS_FILE}")
        return pd.DataFrame()
    
    df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    
    # Ensure timezone-naive
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    logger.info(f"Loaded returns for {len(df.columns)} tickers")
    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    
    return df


def load_fundamentals_data() -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Load all fundamentals data (income statements and balance sheets) for S&P 500 tickers.
    
    Returns:
        Dictionary mapping ticker to dict with 'income' and 'balance' DataFrames
    """
    logger.info("Loading fundamentals data...")
    
    fundamentals = {}
    income_files = list(FUNDAMENTALS_DIR.glob("*_income_annual.csv"))
    balance_files = list(FUNDAMENTALS_DIR.glob("*_balance_annual.csv"))
    
    logger.info(f"Found {len(income_files)} income statement files")
    logger.info(f"Found {len(balance_files)} balance sheet files")
    
    # Load income statements
    for file in income_files:
        try:
            ticker = file.stem.replace('_income_annual', '')
            df = pd.read_csv(file)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                if ticker not in fundamentals:
                    fundamentals[ticker] = {}
                fundamentals[ticker]['income'] = df
        except Exception as e:
            logger.warning(f"Error loading {file}: {e}")
            continue
    
    # Load balance sheets
    for file in balance_files:
        try:
            ticker = file.stem.replace('_balance_annual', '')
            df = pd.read_csv(file)
            
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                if ticker not in fundamentals:
                    fundamentals[ticker] = {}
                fundamentals[ticker]['balance'] = df
        except Exception as e:
            logger.warning(f"Error loading {file}: {e}")
            continue
    
    logger.info(f"Loaded fundamentals for {len(fundamentals)} tickers")
    return fundamentals


def prepare_rq_data(
    tickers: List[str],
    rebalance_date: pd.Timestamp,
    fundamentals: Dict[str, Dict[str, pd.DataFrame]]
) -> Optional[pd.DataFrame]:
    """
    Prepare pooled data for RQ estimation at a given rebalance date.
    
    Collects firm-year observations for all tickers up to the rebalance date,
    merging income statement and balance sheet data.
    
    Returns:
        DataFrame with columns: ticker, year, revenue, ppe, labor, rd, advertising
        or None if insufficient data
    """
    all_data = []
    
    for ticker in tickers:
        if ticker not in fundamentals:
            continue
        
        ticker_data = fundamentals[ticker]
        
        # Need both income and balance sheet
        if 'income' not in ticker_data or 'balance' not in ticker_data:
            continue
        
        income_df = ticker_data['income'].copy()
        balance_df = ticker_data['balance'].copy()
        
        # Filter to data strictly before rebalance date (point-in-time)
        income_df = income_df[income_df['date'] < rebalance_date].copy()
        balance_df = balance_df[balance_df['date'] < rebalance_date].copy()
        
        if income_df.empty or balance_df.empty:
            continue
        
        # Merge income and balance sheet on date
        merged = pd.merge(
            income_df,
            balance_df,
            on='date',
            how='inner',
            suffixes=('', '_balance')
        )
        
        if merged.empty:
            continue
        
        # Extract required columns with fallbacks
        for _, row in merged.iterrows():
            year = row['date'].year
            
            # Revenue (y_col)
            revenue = row.get('revenue') or row.get('revenue_x')
            
            # PPE (k_col) - from balance sheet
            ppe = row.get('propertyPlantEquipmentNet') or row.get('propertyPlantEquipmentNet_balance')
            
            # Labor (l_col) - use SG&A as proxy
            labor = row.get('sellingGeneralAndAdministrativeExpenses') or row.get('sellingGeneralAndAdministrativeExpenses_x')
            
            # R&D (r_col)
            rd = row.get('researchAndDevelopmentExpenses') or row.get('researchAndDevelopmentExpenses_x')
            
            # Advertising (a_col, optional)
            advertising = row.get('sellingAndMarketingExpenses') or row.get('sellingAndMarketingExpenses_x')
            
            # Only include if we have all required fields
            if pd.notna(revenue) and pd.notna(ppe) and pd.notna(labor) and pd.notna(rd):
                all_data.append({
                    'ticker': ticker,
                    'year': year,
                    'revenue': revenue,
                    'ppe': ppe,
                    'labor': labor,
                    'rd': rd,
                    'advertising': advertising if pd.notna(advertising) else None
                })
    
    if not all_data:
        return None
    
    df = pd.DataFrame(all_data)
    
    # Need at least some firms with multiple years for pooled regression
    if len(df) < 20:  # Minimum observations for meaningful regression
        return None
    
    # Check if we have enough firms
    unique_firms = df['ticker'].nunique()
    if unique_firms < 5:  # Need at least 5 firms for pooled regression
        return None
    
    return df


def calculate_rq_factor_point_in_time(
    tickers: List[str],
    rebalance_date: pd.Timestamp,
    fundamentals: Dict[str, Dict[str, pd.DataFrame]]
) -> Dict[str, float]:
    """
    Calculate RQ factor for all tickers at a given rebalance date (point-in-time).
    
    Uses pooled fixed effects regression across all firms in a 7-year rolling window.
    
    Returns:
        Dictionary mapping ticker to RQ coefficient
    """
    # Prepare pooled data
    pooled_df = prepare_rq_data(tickers, rebalance_date, fundamentals)
    
    if pooled_df is None or pooled_df.empty:
        return {}
    
    # Determine end year (year of rebalance date)
    end_year = rebalance_date.year
    
    # Calculate RQ using pooled regression
    try:
        rq_series = estimate_rq_mixedlm(
            df=pooled_df,
            firm_col='ticker',
            year_col='year',
            y_col='revenue',
            k_col='ppe',
            l_col='labor',
            r_col='rd',
            a_col='advertising' if 'advertising' in pooled_df.columns and pooled_df['advertising'].notna().any() else None,
            window_years=RQ_WINDOW_YEARS,
            end_year=end_year,
            add_year_fe=True,
            full_random_slopes=False,
            reml=False
        )
        
        return rq_series.to_dict()
    
    except Exception as e:
        logger.warning(f"Error calculating RQ at {rebalance_date}: {e}")
        return {}


def run_backtest(
    constituents_by_date: Dict[str, List[str]],
    returns_df: pd.DataFrame,
    fundamentals: Dict[str, Dict[str, pd.DataFrame]],
    fmp_client=None
) -> pd.DataFrame:
    """
    Run RQ factor backtest.
    
    At each month-end:
    1. Calculate RQ coefficients for all constituents (point-in-time)
    2. Select top TOP_N stocks by RQ
    3. Hold equal-weighted portfolio for one month
    4. Calculate portfolio return
    """
    logger.info("=" * 70)
    logger.info("Running RQ Factor Backtest")
    logger.info("=" * 70)
    logger.info("Using point-in-time data (only data before each rebalance date)")
    logger.info("=" * 70)
    
    portfolio_returns = []
    portfolio_composition = []
    
    rebalance_dates = sorted(constituents_by_date.keys())
    total_months = len(rebalance_dates)
    
    _factor_cache = {}  # Cache RQ factors by (year, month) to avoid recalculation
    
    for idx, date_str in enumerate(rebalance_dates, 1):
        rebalance_date = pd.to_datetime(date_str)
        year = rebalance_date.year
        month = rebalance_date.month
        
        logger.info(f"Processing {date_str} ({idx}/{total_months})...")
        
        # Get constituents for this date
        constituents = constituents_by_date[date_str]
        
        # Check cache
        cache_key = (year, month)
        if cache_key in _factor_cache:
            rq_scores = _factor_cache[cache_key]
        else:
            # Calculate RQ factors (point-in-time)
            rq_scores = calculate_rq_factor_point_in_time(
                constituents,
                rebalance_date,
                fundamentals
            )
            _factor_cache[cache_key] = rq_scores
        
        if not rq_scores:
            logger.warning(f"  No RQ factors calculated for {date_str}")
            continue
        
        # Select top TOP_N by RQ
        sorted_tickers = sorted(rq_scores.items(), key=lambda x: x[1], reverse=True)
        selected_tickers = [ticker for ticker, _ in sorted_tickers[:TOP_N]]
        
        if len(selected_tickers) < TOP_N:
            logger.warning(f"  Only {len(selected_tickers)} stocks with RQ data, need {TOP_N}")
        
        logger.info(f"  Calculated RQ for {len(rq_scores)}/{len(constituents)} constituents")
        logger.info(f"  Selected top {len(selected_tickers)} stocks by RQ")
        
        # Calculate next month return
        next_year = year
        next_month = month + 1
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        # Get returns for next month
        next_month_start = pd.Timestamp(f"{next_year}-{next_month:02d}-01")
        next_month_end = (next_month_start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
        
        # Filter returns to next month
        month_returns = returns_df[
            (returns_df.index >= next_month_start) & 
            (returns_df.index <= next_month_end)
        ]
        
        if month_returns.empty:
            logger.warning(f"  No returns data for {next_year}-{next_month:02d}")
            continue
        
        # Filter to available tickers
        available_tickers = [t for t in selected_tickers if t in month_returns.columns]
        
        if len(available_tickers) == 0:
            logger.warning(f"  No returns available for selected tickers in {next_year}-{next_month:02d}")
            continue
        
        # Calculate daily portfolio returns (equal-weighted average of daily stock returns)
        # Then compound daily portfolio returns to get monthly return
        ticker_returns = month_returns[available_tickers]
        
        daily_portfolio_returns = []
        for date_idx in ticker_returns.index:
            day_returns = ticker_returns.loc[date_idx]
            valid_returns = day_returns.dropna()
            if len(valid_returns) > 0:
                equal_weight = 1.0 / len(valid_returns)
                daily_portfolio_return = (valid_returns * equal_weight).sum()
                daily_portfolio_returns.append(daily_portfolio_return)
        
        if len(daily_portfolio_returns) == 0:
            logger.warning(f"  No valid daily returns for {next_year}-{next_month:02d}")
            continue
        
        portfolio_return = (1 + pd.Series(daily_portfolio_returns)).prod() - 1
        
        portfolio_returns.append({
            'date': next_month_start,
            'return': portfolio_return
        })
        
        portfolio_composition.append({
            'date': rebalance_date,
            'tickers': selected_tickers
        })
        
        if idx % 12 == 0:
            logger.info(f"  ✓ Month {idx}/{total_months}: {idx} valid returns, {len(selected_tickers)} stocks in portfolio")
    
    results_df = pd.DataFrame(portfolio_returns)
    if not results_df.empty:
        results_df.set_index('date', inplace=True)
        results_df = results_df.sort_index()
    
    # Save portfolio composition
    composition_df = pd.DataFrame(portfolio_composition)
    composition_file = OUTPUT_DIR / 'rq_factor_portfolio_composition.csv'
    composition_df.to_csv(composition_file, index=False)
    logger.info(f"✓ Saved portfolio composition to {composition_file}")
    
    return results_df


def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
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
        'cagr': cagr,
        'volatility': vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'num_periods': len(returns),
        'years': years
    }


def plot_results(results_df: pd.DataFrame):
    """Plot backtest results."""
    logger.info("Creating plots...")
    
    # Load S&P 500 EW backtest for comparison
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
        
        logger.info(f"Loaded S&P 500 EW backtest: {len(ew_monthly)} monthly returns from {ew_monthly.index.min()} to {ew_monthly.index.max()}")
    else:
        ew_monthly = None
        logger.warning("S&P 500 EW backtest results not found for comparison")
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Cumulative Returns
    ax1 = axes[0]
    
    if not results_df.empty:
        returns = results_df.iloc[:, 0]
        cum_returns = (1 + returns).cumprod()
        ax1.plot(cum_returns.index, cum_returns.values, 
                label=f'RQ Factor (Top {TOP_N})', linewidth=2.5, color='purple')
    
    if ew_monthly is not None and not ew_monthly.empty:
        ew_cum = (1 + ew_monthly).cumprod()
        ax1.plot(ew_cum.index, ew_cum.values,
                label='S&P 500 Equal-Weighted', linewidth=2.5, color='orange', linestyle='--')
    
    ax1.set_title(f'RQ Factor Portfolio Backtest\n'
                 f'Top {TOP_N} by Research Quotient (Pooled Fixed Effects)', 
                 fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('linear')
    
    # Plot 2: Monthly Returns
    ax2 = axes[1]
    
    if not results_df.empty:
        returns = results_df.iloc[:, 0]
        ax2.plot(returns.index, returns.values * 100, 
                label=f'RQ Factor (Top {TOP_N})', linewidth=1.5, color='purple', alpha=0.7, marker='o', markersize=3)
    
    if ew_monthly is not None and not ew_monthly.empty:
        ax2.plot(ew_monthly.index, ew_monthly.values * 100,
                label='S&P 500 EW', linewidth=1.5, color='orange', alpha=0.7, marker='^', markersize=3)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    ax2.set_title('Monthly Returns Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Monthly Return (%)', fontsize=12)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'rq_factor_backtest.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved plot to {plot_file}")
    plt.close()


def main():
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("RQ Factor Portfolio Backtest")
    logger.info("=" * 70)
    
    # Load data
    constituents_by_date = load_monthly_constituents()
    returns_df = load_returns()
    fundamentals = load_fundamentals_data()
    
    if not constituents_by_date or returns_df.empty or not fundamentals:
        logger.error("Failed to load required data")
        return
    
    logger.info("=" * 70)
    logger.info("Running RQ Factor Backtest")
    logger.info("=" * 70)
    
    # Run backtest
    results_df = run_backtest(constituents_by_date, returns_df, fundamentals, None)
    
    if results_df.empty:
        logger.error("Backtest produced no results")
        return
    
    logger.info(f"✓ Backtest complete: {len(results_df)} monthly returns")
    
    # Save results
    results_file = OUTPUT_DIR / 'rq_factor_backtest_results.csv'
    results_df.to_csv(results_file)
    logger.info(f"✓ Saved results to {results_file}")
    
    # Calculate and print performance metrics
    returns = results_df.iloc[:, 0]
    metrics = calculate_performance_metrics(returns)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Performance Metrics")
    logger.info("=" * 70)
    for key, value in metrics.items():
        logger.info(f"  {key}: {value:.4f}")
    
    # Plot results
    plot_results(results_df)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Backtest Complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

