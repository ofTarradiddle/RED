"""
Backtest Innovation Factor Portfolio with R&D/Market Cap Pre-filtering
Two-step filtering:
1. Top 100 by average R&D / Market Cap over past 5 years
2. Top 50 by innovation coefficient from those 100
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

from lib.etf.functions.research.core.factors import rolling_ols
from lib.etf.functions.research.core.backtesting import FMPClient

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
TOP_N_RD_MCAP = 100  # First filter: top 100 by R&D/Market Cap
TOP_N_INNOVATION = 50  # Second filter: top 50 by innovation coefficient
RD_MCAP_YEARS = 5  # Years to average R&D/Market Cap over


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


def load_fundamentals_data() -> Dict[str, pd.DataFrame]:
    """Load all fundamentals data (income statements) for S&P 500 tickers."""
    logger.info("Loading fundamentals data...")
    
    fundamentals = {}
    income_files = list(FUNDAMENTALS_DIR.glob("*_income_annual.csv"))
    
    logger.info(f"Found {len(income_files)} income statement files")
    
    for file in income_files:
        try:
            ticker = file.stem.replace('_income_annual', '')
            df = pd.read_csv(file)
            
            # Ensure date column exists and is datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                fundamentals[ticker] = df
        except Exception as e:
            logger.warning(f"Error loading {file}: {e}")
            continue
    
    logger.info(f"Loaded fundamentals for {len(fundamentals)} tickers")
    return fundamentals


def calculate_rd_sales_ratio_weighted(ticker: str, 
                                     rebalance_date: pd.Timestamp,
                                     fundamentals: Dict[str, pd.DataFrame]) -> Optional[float]:
    """
    Calculate weighted average R&D / Sales ratio over past 5 years.
    More weight is given to recent observations.
    
    Args:
        ticker: Ticker symbol
        rebalance_date: Date of rebalance (use only data before this date)
        fundamentals: Dictionary of fundamentals data
        
    Returns:
        Weighted average R&D / Sales ratio or None if cannot calculate
    """
    if ticker not in fundamentals:
        return None
    
    df = fundamentals[ticker].copy()
    
    # Filter to data before rebalance date
    df = df[df['date'] < rebalance_date].copy()
    
    if len(df) < RD_MCAP_YEARS:
        return None
    
    # Get most recent RD_MCAP_YEARS years
    df = df.tail(RD_MCAP_YEARS).copy()
    df = df.sort_values('date')  # Ensure chronological order
    
    # Find R&D and Sales columns
    rd_col = None
    sales_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'research' in col_lower or 'rd' in col_lower or 'r&d' in col_lower:
            if rd_col is None:
                rd_col = col
        if 'revenue' in col_lower or 'sales' in col_lower:
            if sales_col is None:
                sales_col = col
    
    if rd_col is None or sales_col is None:
        return None
    
    # Calculate R&D/Sales ratio for each year
    ratios = []
    for _, row in df.iterrows():
        rd = row[rd_col]
        sales = row[sales_col]
        
        if pd.isna(rd) or pd.isna(sales) or rd <= 0 or sales <= 0:
            continue
        
        ratio = rd / sales
        ratios.append(ratio)
    
    if len(ratios) < RD_MCAP_YEARS:
        return None
    
    # Apply weights: more weight to recent observations
    # Linear weights: [0.1, 0.15, 0.2, 0.25, 0.3] for years 5, 4, 3, 2, 1 (most recent)
    # Or exponential: weights increase exponentially for recent years
    n = len(ratios)
    if n == RD_MCAP_YEARS:
        # Linear weights summing to 1.0
        weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])
    else:
        # If we have fewer than 5 years, use proportional weights
        # Most recent gets highest weight
        weights = np.linspace(0.1, 0.3, n)
        weights = weights / weights.sum()  # Normalize to sum to 1.0
    
    # Calculate weighted average
    weighted_avg = np.average(ratios, weights=weights)
    
    return weighted_avg


def calculate_innovation_factor_point_in_time(ticker: str, 
                                              rebalance_date: pd.Timestamp,
                                              fundamentals: Dict[str, pd.DataFrame]) -> Optional[float]:
    """
    Calculate innovation factor using only data BEFORE the rebalance date (point-in-time).
    
    Args:
        ticker: Ticker symbol
        rebalance_date: Date of rebalance (use only data before this date)
        fundamentals: Dictionary of fundamentals data
        
    Returns:
        Innovation factor or None if cannot calculate
    """
    if ticker not in fundamentals:
        return None
    
    df = fundamentals[ticker].copy()
    
    # CRITICAL: Filter to only data BEFORE the rebalance date (point-in-time)
    df = df[df['date'] < rebalance_date].copy()
    
    if len(df) < 8:  # Need at least 8 years for rolling window
        return None
    
    # Extract sales and R&D columns
    sales_col = None
    rd_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'revenue' in col_lower or 'sales' in col_lower:
            if sales_col is None:
                sales_col = col
        if 'research' in col_lower or 'rd' in col_lower or 'r&d' in col_lower:
            if rd_col is None:
                rd_col = col
    
    if sales_col is None or rd_col is None:
        return None
    
    # Prepare data
    df_prep = df.copy()
    df_prep['year'] = df_prep['date'].dt.year
    df_prep['ticker'] = ticker
    df_prep = df_prep[[sales_col, rd_col, 'year', 'ticker']].copy()
    df_prep = df_prep.dropna()
    df_prep = df_prep[(df_prep[sales_col] > 0) & (df_prep[rd_col] > 0)]
    
    if len(df_prep) < 8:
        return None
    
    try:
        # Run rolling OLS
        results = rolling_ols(
            df=df_prep,
            firm_col='ticker',
            year_col='year',
            sales_col=sales_col,
            rd_col=rd_col
        )
        
        if results.empty:
            return None
        
        # Get the most recent available year (up to but not including rebalance year)
        rebalance_year = rebalance_date.year
        available_years = []
        for idx in results.index:
            if isinstance(idx, tuple) and len(idx) == 2:
                t, y = idx
                if t == ticker and y < rebalance_year:
                    available_years.append(y)
        
        if not available_years:
            return None
        
        # Use the most recent year
        most_recent_year = max(available_years)
        row = results.loc[(ticker, most_recent_year)]
        
        # Get the 5 lag coefficients
        lag_coefs = [row.get(f'lag{i}', np.nan) for i in range(1, 6)]
        
        # Calculate average (excluding NaN)
        valid_coefs = [c for c in lag_coefs if pd.notna(c)]
        if len(valid_coefs) >= 3:  # Need at least 3 valid coefficients
            return np.mean(valid_coefs)
        
        return None
    except Exception as e:
        logger.debug(f"Error calculating innovation factor for {ticker} at {rebalance_date}: {e}")
        return None


def run_backtest(constituents_by_date: Dict[str, List[str]], 
                 returns_df: pd.DataFrame,
                 fundamentals: Dict[str, pd.DataFrame],
                 fmp_client: Optional[FMPClient] = None) -> pd.DataFrame:
    """
    Run innovation factor backtest with R&D/Market Cap pre-filtering.
    """
    logger.info("="*70)
    logger.info("Running Innovation Factor Backtest (R&D/Sales Pre-filtered)")
    logger.info("="*70)
    logger.info(f"Step 1: Filter to top {TOP_N_RD_MCAP} by weighted R&D/Sales (past {RD_MCAP_YEARS} years, recent weighted more)")
    logger.info(f"Step 2: Filter to top {TOP_N_INNOVATION} by innovation coefficient")
    logger.info("="*70)
    
    portfolio_returns = []
    portfolio_composition = []
    
    sorted_dates = sorted(constituents_by_date.keys())
    
    for i, rebalance_date_str in enumerate(sorted_dates):
        rebalance_date = pd.to_datetime(rebalance_date_str)
        constituents = constituents_by_date[rebalance_date_str]
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            logger.info(f"Processing {rebalance_date_str} ({i+1}/{len(sorted_dates)})...")
        
        # Step 1: Calculate weighted average R&D/Sales for all constituents
        rd_sales_scores = {}
        for ticker in constituents:
            score = calculate_rd_sales_ratio_weighted(ticker, rebalance_date, fundamentals)
            if score is not None:
                rd_sales_scores[ticker] = score
        
        if len(rd_sales_scores) < TOP_N_RD_MCAP:
            if (i + 1) % 12 == 0 or (i + 1) <= 5:
                logger.warning(f"Only {len(rd_sales_scores)} stocks with R&D/Sales data, need {TOP_N_RD_MCAP}, using all available")
            # Use all available if we have at least TOP_N_INNOVATION
            if len(rd_sales_scores) < TOP_N_INNOVATION:
                continue
            # Use all available stocks
            sorted_by_rd_sales = sorted(rd_sales_scores.items(), key=lambda x: x[1], reverse=True)
            top_rd_sales_tickers = [ticker for ticker, _ in sorted_by_rd_sales]
        else:
            # Get top TOP_N_RD_MCAP by weighted R&D/Sales
            sorted_by_rd_sales = sorted(rd_sales_scores.items(), key=lambda x: x[1], reverse=True)
            top_rd_sales_tickers = [ticker for ticker, _ in sorted_by_rd_sales[:TOP_N_RD_MCAP]]
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            logger.info(f"  Step 1: Selected {len(top_rd_sales_tickers)} stocks by weighted R&D/Sales (past {RD_MCAP_YEARS} years)")
        
        # Step 2: Calculate innovation factors for top R&D/Sales stocks
        innovation_scores = {}
        for ticker in top_rd_sales_tickers:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_scores[ticker] = factor
        
        if len(innovation_scores) < TOP_N_INNOVATION:
            logger.warning(f"Only {len(innovation_scores)} stocks with innovation factors, need {TOP_N_INNOVATION}")
            continue
        
        # Get top TOP_N_INNOVATION by innovation coefficient
        sorted_by_innovation = sorted(innovation_scores.items(), key=lambda x: x[1], reverse=True)
        selected_tickers = [ticker for ticker, _ in sorted_by_innovation[:TOP_N_INNOVATION]]
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            logger.info(f"  Step 2: Selected {len(selected_tickers)} stocks by innovation coefficient")
        
        # Store composition
        portfolio_composition.append({
            'date': rebalance_date_str,
            'tickers': ','.join(selected_tickers),
            'num_stocks': len(selected_tickers)
        })
        
        # Calculate returns for the next month
        if i < len(sorted_dates) - 1:
            next_date_str = sorted_dates[i + 1]
            next_date = pd.to_datetime(next_date_str)
            
            # Get returns for the month
            month_returns = returns_df[
                (returns_df.index >= rebalance_date) & 
                (returns_df.index <= next_date)
            ]
            
            if month_returns.empty:
                continue
            
            # Filter to available tickers
            available_tickers = [t for t in selected_tickers if t in month_returns.columns]
            if not available_tickers:
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
                logger.warning(f"No valid daily returns for {next_date_str}")
                continue
            
            portfolio_return = (1 + pd.Series(daily_portfolio_returns)).prod() - 1
            
            portfolio_returns.append({
                'date': next_date_str,
                'return': portfolio_return
            })
    
    # Convert to DataFrame
    results_df = pd.DataFrame(portfolio_returns)
    if not results_df.empty:
        results_df = results_df.set_index('date')
        results_df.index = pd.to_datetime(results_df.index)
    
    # Save composition
    composition_df = pd.DataFrame(portfolio_composition)
    if not composition_df.empty:
        composition_df = composition_df.set_index('date')
        composition_file = OUTPUT_DIR / 'rd_mcap_innovation_portfolio_composition.csv'
        composition_df.to_csv(composition_file)
        logger.info(f"Saved portfolio composition to {composition_file}")
    
    return results_df


def plot_results(results_df: pd.DataFrame):
    """Plot backtest results."""
    if results_df.empty:
        logger.warning("No results to plot")
        return
    
    # Load equal-weighted benchmark
    ew_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'
    if ew_file.exists():
        ew_df = pd.read_csv(ew_file, index_col=0, parse_dates=True)
        if ew_df.index.tz is not None:
            ew_df.index = ew_df.index.tz_localize(None)
        
        # Convert daily to monthly if needed
        if 'return' in ew_df.columns:
            ew_returns = ew_df['return']
        else:
            ew_returns = ew_df.iloc[:, 0]
        
        # Align dates
        common_dates = results_df.index.intersection(ew_returns.index)
        if len(common_dates) > 0:
            ew_aligned = ew_returns.loc[common_dates]
        else:
            ew_aligned = pd.Series(dtype=float)
    else:
        ew_aligned = pd.Series(dtype=float)
    
    # Calculate cumulative returns
    innovation_cum = (1 + results_df['return']).cumprod()
    if not ew_aligned.empty:
        ew_cum = (1 + ew_aligned).cumprod()
    
    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.plot(innovation_cum.index, innovation_cum.values, 
            label=f'R&D/Sales + Innovation Factor (Top {TOP_N_RD_MCAP}→{TOP_N_INNOVATION})', 
            linewidth=2, color='#2E86AB')
    
    if not ew_aligned.empty:
        ax.plot(ew_cum.index, ew_cum.values, 
                label='S&P 500 Equal-Weighted', 
                linewidth=2, color='#A23B72', linestyle='--')
    
    ax.set_title(f'Innovation Factor Portfolio (R&D/Sales Pre-filtered)\n'
                 f'Top {TOP_N_RD_MCAP} by Weighted R&D/Sales → Top {TOP_N_INNOVATION} by Innovation', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Cumulative Return', fontsize=12)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'rd_mcap_innovation_backtest.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"Saved plot to {plot_file}")
    plt.close()


def main():
    logger.info("="*70)
    logger.info("R&D/Sales + Innovation Factor Portfolio Backtest")
    logger.info("="*70)
    
    # Load data
    constituents_by_date = load_monthly_constituents()
    returns_df = load_returns()
    fundamentals = load_fundamentals_data()
    
    if not constituents_by_date or returns_df.empty or not fundamentals:
        logger.error("Failed to load required data")
        return
    
    # Run backtest (no longer need fmp_client since we're using R&D/Sales, not R&D/MCap)
    results_df = run_backtest(constituents_by_date, returns_df, fundamentals, None)
    
    if results_df.empty:
        logger.error("Backtest produced no results")
        return
    
    # Save results
    results_file = OUTPUT_DIR / 'rd_mcap_innovation_backtest_results.csv'
    results_df.to_csv(results_file)
    logger.info(f"Saved results to {results_file}")
    
    # Calculate performance metrics
    total_return = (1 + results_df['return']).prod() - 1.0
    years = len(results_df) / 12.0
    cagr = ((1 + results_df['return']).prod() ** (1.0 / years)) - 1.0 if years > 0 else np.nan
    vol = results_df['return'].std() * np.sqrt(12) if len(results_df) > 1 else np.nan
    sharpe = (results_df['return'].mean() * 12.0) / vol if vol and vol != 0 else np.nan
    
    cum = (1 + results_df['return']).cumprod()
    running_max = cum.expanding().max()
    drawdown = (cum - running_max) / running_max
    max_dd = drawdown.min()
    
    logger.info("="*70)
    logger.info("Performance Metrics")
    logger.info("="*70)
    logger.info(f"Total Return: {total_return:.2%}")
    logger.info(f"CAGR: {cagr:.2%}")
    logger.info(f"Volatility: {vol:.2%}")
    logger.info(f"Sharpe Ratio: {sharpe:.4f}")
    logger.info(f"Max Drawdown: {max_dd:.2%}")
    logger.info("="*70)
    
    # Plot results
    plot_results(results_df)
    
    logger.info("Backtest complete!")


if __name__ == '__main__':
    main()

