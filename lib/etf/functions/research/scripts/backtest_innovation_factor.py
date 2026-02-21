"""
Backtest Innovation Factor Portfolio
Monthly rebalanced portfolio selecting top 50 stocks by innovation factor.

Innovation Factor = Average of 5 regression coefficients from rolling OLS:
- Regress log(sales) on lagged log(R&D) (lags 1-5)
- Use 8-year rolling window
- Average the 5 coefficients (lag1 through lag5)
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


def load_monthly_constituents() -> Dict[str, List[str]]:
    """Load monthly S&P 500 constituents."""
    logger.info("Loading monthly constituents...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return {}
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to 1995 and after
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
    """
    Load all fundamentals data (income statements) for S&P 500 tickers.
    
    Returns:
        Dictionary mapping ticker to DataFrame with income statement data
    """
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


def calculate_innovation_factor(ticker: str, year: int, fundamentals: Dict[str, pd.DataFrame]) -> Optional[float]:
    """
    Calculate innovation factor for a ticker at a given year.
    
    Innovation factor = average of 5 regression coefficients (lag1 through lag5)
    from rolling OLS regression of log(sales) on lagged log(R&D).
    
    Args:
        ticker: Ticker symbol
        year: Year to calculate factor for
        fundamentals: Dictionary of fundamentals data
        
    Returns:
        Innovation factor (average of 5 coefficients) or None if cannot calculate
    """
    if ticker not in fundamentals:
        return None
    
    df = fundamentals[ticker].copy()
    
    # Filter to data up to and including the year
    df = df[df['date'].dt.year <= year].copy()
    
    if len(df) < 8:  # Need at least 8 years for rolling window
        return None
    
    # Use the most recent year available (might be less than requested year)
    actual_year = df['date'].dt.year.max()
    
    # Extract sales and R&D columns
    # Try different possible column names
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
    
    # Prepare data for rolling_ols
    # Need: firm_col, year_col, sales_col, rd_col
    df['year'] = df['date'].dt.year
    df['ticker'] = ticker
    
    # Filter out rows with missing or non-positive values
    df = df[[sales_col, rd_col, 'year', 'ticker']].copy()
    df = df.dropna()
    df = df[(df[sales_col] > 0) & (df[rd_col] > 0)]
    
    if len(df) < 8:
        return None
    
    try:
        # Run rolling OLS
        results = rolling_ols(
            df=df,
            firm_col='ticker',
            year_col='year',
            sales_col=sales_col,
            rd_col=rd_col
        )
        
        # Get results for the most recent available year (up to requested year)
        # rolling_ols returns results indexed by (firm_col, year_col)
        available_years = []
        for idx in results.index:
            if isinstance(idx, tuple) and len(idx) == 2:
                t, y = idx
                if t == ticker and y <= year:
                    available_years.append(y)
        
        if not available_years:
            return None
        
        # Use the most recent year
        actual_year = max(available_years)
        row = results.loc[(ticker, actual_year)]
        
        # Get the 5 lag coefficients
        lag_coefs = [row.get(f'lag{i}', np.nan) for i in range(1, 6)]
        
        # Calculate average (excluding NaN)
        valid_coefs = [c for c in lag_coefs if pd.notna(c)]
        if len(valid_coefs) >= 3:  # Need at least 3 valid coefficients
            return np.mean(valid_coefs)
        
        return None
    except Exception as e:
        logger.debug(f"Error calculating innovation factor for {ticker} in {year}: {e}")
        return None


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
                if t == ticker and y < rebalance_year:  # Must be before rebalance year
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
                 fundamentals: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Run innovation factor backtest.
    
    Args:
        constituents_by_date: Dictionary mapping dates to constituent lists
        returns_df: DataFrame with daily returns
        fundamentals: Dictionary of fundamentals data
        
    Returns:
        DataFrame with portfolio returns
    """
    logger.info("="*70)
    logger.info("Running Innovation Factor Backtest")
    logger.info("="*70)
    logger.info(f"Using point-in-time data (only data before each rebalance date)")
    logger.info("="*70)
    
    portfolio_returns = []
    sorted_dates = sorted(constituents_by_date.keys())
    
    for i, rebalance_date_str in enumerate(sorted_dates):
        rebalance_date = pd.to_datetime(rebalance_date_str)
        year = rebalance_date.year
        month = rebalance_date.month
        
        # Get constituents
        constituents = constituents_by_date[rebalance_date_str]
        
        # Calculate innovation factors using point-in-time data (only before rebalance date)
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            logger.info(f"Processing {rebalance_date_str} ({i+1}/{len(sorted_dates)})...")
        
        innovation_factors = {}
        factors_calculated = 0
        
        for ticker in constituents:
            factor = calculate_innovation_factor_point_in_time(ticker, rebalance_date, fundamentals)
            if factor is not None:
                innovation_factors[ticker] = factor
                factors_calculated += 1
        
        if (i + 1) % 12 == 0 or (i + 1) <= 5:
            logger.info(f"  Calculated factors for {factors_calculated}/{len(constituents)} constituents")
        
        if len(innovation_factors) < TOP_N:
            if (i + 1) % 12 == 0 or (i + 1) <= 5:
                logger.warning(f"  Only {len(innovation_factors)} tickers with innovation factors, need {TOP_N}")
            # Use all available
            selected_tickers = sorted(innovation_factors.keys(), 
                                     key=lambda x: innovation_factors[x], 
                                     reverse=True)[:len(innovation_factors)]
        else:
            # Select top N by innovation factor
            selected_tickers = sorted(innovation_factors.keys(), 
                                     key=lambda x: innovation_factors[x], 
                                     reverse=True)[:TOP_N]
        
        if not selected_tickers:
            if (i + 1) % 12 == 0 or (i + 1) <= 5:
                logger.warning(f"  No tickers selected for {rebalance_date_str}")
            continue
        
        # Calculate portfolio return for next month
        if rebalance_date.month == 12:
            next_year = rebalance_date.year + 1
            next_month = 1
        else:
            next_year = rebalance_date.year
            next_month = rebalance_date.month + 1
        
        # Get returns for next month
        next_month_start = pd.Timestamp(year=next_year, month=next_month, day=1)
        next_month_end = (next_month_start + pd.DateOffset(months=1) - pd.Timedelta(days=1))
        
        # Filter returns to next month
        month_returns = returns_df[
            (returns_df.index >= next_month_start) & 
            (returns_df.index <= next_month_end)
        ]
        
        if month_returns.empty:
            logger.warning(f"No returns data for {next_year}-{next_month:02d}")
            continue
        
        # Calculate equal-weighted portfolio return
        available_tickers = [t for t in selected_tickers if t in month_returns.columns]
        if not available_tickers:
            logger.warning(f"No available tickers with returns for {next_year}-{next_month:02d}")
            continue
        
        # Calculate daily portfolio returns (equal-weighted average of daily stock returns)
        # Then compound daily portfolio returns to get monthly return
        ticker_returns = month_returns[available_tickers]
        
        # For each day, calculate equal-weighted portfolio return
        daily_portfolio_returns = []
        for date_idx in ticker_returns.index:
            day_returns = ticker_returns.loc[date_idx]
            valid_returns = day_returns.dropna()
            if len(valid_returns) > 0:
                # Equal-weighted average of daily stock returns
                equal_weight = 1.0 / len(valid_returns)
                daily_portfolio_return = (valid_returns * equal_weight).sum()
                daily_portfolio_returns.append(daily_portfolio_return)
        
        if len(daily_portfolio_returns) == 0:
            logger.warning(f"No valid daily returns for {next_year}-{next_month:02d}")
            continue
        
        # Compound daily portfolio returns to get monthly return
        portfolio_return = (1 + pd.Series(daily_portfolio_returns)).prod() - 1
        
        portfolio_returns.append({
            'date': next_month_start,
            'return': portfolio_return,
            'num_stocks': len(available_tickers),
            'tickers': ','.join(sorted(available_tickers))  # Store tickers as comma-separated string
        })
        
        if (i + 1) % 12 == 0:
            logger.info(f"  ✓ Month {i+1}/{len(sorted_dates)}: {len(portfolio_returns)} valid returns, {len(available_tickers)} stocks in portfolio")
    
    portfolio_df = pd.DataFrame(portfolio_returns)
    if not portfolio_df.empty:
        portfolio_df = portfolio_df.set_index('date')
        portfolio_df = portfolio_df.sort_index()
    
    logger.info(f"✓ Backtest complete: {len(portfolio_df)} monthly returns")
    return portfolio_df


def fetch_benchmarks(start_date: pd.Timestamp, end_date: pd.Timestamp) -> Dict[str, pd.Series]:
    """
    Fetch benchmark returns (RSP and S&P 500 EW backtest).
    
    Returns:
        Dictionary with benchmark names and return series
    """
    benchmarks = {}
    
    # Load S&P 500 EW backtest results (daily returns)
    backtest_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'
    if backtest_file.exists():
        try:
            df = pd.read_csv(backtest_file, index_col=0, parse_dates=True)
            
            # Ensure timezone-naive
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Filter to start_date and after
            df = df[df.index >= start_date]
            
            # Check for portfolio_return column (daily returns)
            if 'portfolio_return' in df.columns:
                daily_returns = df['portfolio_return'].dropna()
                
                # Convert daily returns to monthly returns
                # Group by year-month and compound returns
                monthly_returns = daily_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
                
                # Filter to end_date
                monthly_returns = monthly_returns[monthly_returns.index <= end_date]
                
                if not monthly_returns.empty:
                    benchmarks['S&P 500 EW (Backtest)'] = monthly_returns
                    logger.info(f"Loaded S&P 500 EW backtest: {len(monthly_returns)} monthly returns from {monthly_returns.index.min()} to {monthly_returns.index.max()}")
            elif 'return' in df.columns:
                # Already monthly returns
                df = df[df.index <= end_date]
                benchmarks['S&P 500 EW (Backtest)'] = df['return']
        except Exception as e:
            logger.warning(f"Error loading S&P 500 EW backtest: {e}")
    
    # Fetch RSP from FMP
    api_key = os.getenv('FMP_API_KEY')
    if api_key:
        try:
            import requests
            url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
            params = {
                'symbol': 'RSP',
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'apikey': api_key
            }
            response = requests.get(url, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date').sort_index()
                    if 'close' in df.columns:
                        rsp_returns = df['close'].pct_change().dropna()
                        # Convert to monthly
                        rsp_monthly = rsp_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
                        benchmarks['RSP'] = rsp_monthly
        except Exception as e:
            logger.warning(f"Error fetching RSP: {e}")
    
    return benchmarks


def plot_results(portfolio_returns: pd.Series, benchmarks: Dict[str, pd.Series]):
    """Plot backtest results."""
    logger.info("Creating plots...")
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Innovation Factor Portfolio Backtest (2004-2025)', fontsize=16, fontweight='bold')
    
    # Calculate cumulative returns
    portfolio_cumulative = (1 + portfolio_returns).cumprod()
    
    # Plot 1: Cumulative Returns
    ax1 = axes[0, 0]
    ax1.plot(portfolio_cumulative.index, portfolio_cumulative.values, 
             label='Innovation Factor Portfolio', linewidth=2.5, color='#2E86AB')
    
    # Plot benchmarks with proper alignment
    for name, returns in benchmarks.items():
        if not returns.empty:
            # Align dates - find common dates
            common_dates = portfolio_cumulative.index.intersection(returns.index)
            if len(common_dates) > 0:
                benchmark_cumulative = (1 + returns.loc[common_dates]).cumprod()
                # Normalize to start at same value as portfolio
                if len(common_dates) > 0 and common_dates[0] in portfolio_cumulative.index:
                    normalization_factor = portfolio_cumulative.loc[common_dates[0]] / benchmark_cumulative.iloc[0]
                    benchmark_cumulative = benchmark_cumulative * normalization_factor
                    
                    # Choose color and style based on benchmark name
                    if 'EW' in name or 'Equal' in name:
                        color = '#A23B72'
                        linestyle = '-'
                        linewidth = 2.5
                    else:
                        color = '#F18F01'
                        linestyle = '--'
                        linewidth = 2
                    
                    ax1.plot(common_dates, benchmark_cumulative.values, 
                            label=name, linewidth=linewidth, linestyle=linestyle, color=color)
    
    ax1.set_yscale('log')
    ax1.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Monthly Returns
    ax2 = axes[0, 1]
    ax2.plot(portfolio_returns.index, portfolio_returns.values, 
             label='Innovation Factor', linewidth=1, alpha=0.7, color='blue')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title('Monthly Returns', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Monthly Return', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling Sharpe Ratio (12-month)
    ax3 = axes[1, 0]
    rolling_sharpe = portfolio_returns.rolling(12).mean() / portfolio_returns.rolling(12).std() * np.sqrt(12)
    ax3.plot(rolling_sharpe.index, rolling_sharpe.values, 
             label='Innovation Factor', linewidth=2, color='blue')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_title('Rolling 12-Month Sharpe Ratio', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Sharpe Ratio', fontsize=12)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Drawdown
    ax4 = axes[1, 1]
    running_max = portfolio_cumulative.expanding().max()
    drawdown = (portfolio_cumulative - running_max) / running_max
    ax4.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
    ax4.plot(drawdown.index, drawdown.values, linewidth=1, color='red')
    ax4.set_title('Drawdown', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=12)
    ax4.set_ylabel('Drawdown', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    plot_file = OUTPUT_DIR / 'innovation_factor_backtest.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved plot to {plot_file}")
    plt.close()


def calculate_metrics(returns: pd.Series) -> Dict:
    """Calculate performance metrics."""
    if returns.empty:
        return {}
    
    df = returns.to_frame('returns')
    df['cumulative'] = (1 + df['returns']).cumprod()
    
    total_return = df['cumulative'].iloc[-1] - 1.0
    num_periods = len(df)
    years = num_periods / 12.0
    
    if years > 0:
        cagr = (df['cumulative'].iloc[-1] ** (1.0 / years)) - 1.0
    else:
        cagr = np.nan
    
    if num_periods > 1:
        vol = df['returns'].std() * np.sqrt(12)
    else:
        vol = np.nan
    
    if vol and vol != 0:
        sharpe = (df['returns'].mean() * 12.0) / vol
    else:
        sharpe = np.nan
    
    cumulative = df['cumulative']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    return {
        'total_return': total_return,
        'cagr': cagr,
        'volatility': vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'num_periods': num_periods,
        'years': years
    }


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("Innovation Factor Portfolio Backtest")
    logger.info("="*70)
    
    # Load data
    constituents_by_date = load_monthly_constituents()
    if not constituents_by_date:
        logger.error("Failed to load constituents. Exiting.")
        return
    
    returns_df = load_returns()
    if returns_df.empty:
        logger.error("Failed to load returns. Exiting.")
        return
    
    fundamentals = load_fundamentals_data()
    if not fundamentals:
        logger.error("Failed to load fundamentals. Exiting.")
        return
    
    # Run backtest
    portfolio_df = run_backtest(constituents_by_date, returns_df, fundamentals)
    
    if portfolio_df.empty:
        logger.error("Backtest produced no results. Exiting.")
        return
    
    # Save results
    results_file = OUTPUT_DIR / 'innovation_factor_backtest_results.csv'
    portfolio_df.to_csv(results_file)
    logger.info(f"✓ Saved results to {results_file}")
    
    # Calculate metrics
    portfolio_returns = portfolio_df['return']
    metrics = calculate_metrics(portfolio_returns)
    
    logger.info("\n" + "="*70)
    logger.info("Performance Metrics")
    logger.info("="*70)
    for key, value in metrics.items():
        if isinstance(value, float):
            logger.info(f"  {key}: {value:.4f}")
        else:
            logger.info(f"  {key}: {value}")
    
    # Fetch benchmarks and plot
    start_date = portfolio_returns.index.min()
    end_date = portfolio_returns.index.max()
    benchmarks = fetch_benchmarks(start_date, end_date)
    
    plot_results(portfolio_returns, benchmarks)
    
    logger.info("\n" + "="*70)
    logger.info("Backtest Complete!")
    logger.info("="*70)


if __name__ == "__main__":
    main()

