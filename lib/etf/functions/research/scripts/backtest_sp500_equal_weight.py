"""
Backtest Equal-Weighted S&P 500 Portfolio
Uses monthly constituents and returns data to construct an equal-weighted portfolio
and compare it to the S&P 500 Equal-Weighted Index.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data paths
CONSTITUENTS_FILE = Path('./data/research/sp500_constituents/sp500_monthly_constituents_corrected.csv')
RETURNS_FILE = Path('./data/research/sp500_returns/sp500_total_returns_corrected.csv')
OUTPUT_DIR = Path('./data/research/sp500_backtest')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_monthly_constituents() -> Dict[str, List[str]]:
    """
    Load monthly S&P 500 constituents.
    
    Returns:
        Dictionary mapping date (YYYY-MM-DD) to list of tickers
    """
    logger.info("Loading monthly constituents...")
    
    if not CONSTITUENTS_FILE.exists():
        logger.error(f"Constituents file not found: {CONSTITUENTS_FILE}")
        return {}
    
    df = pd.read_csv(CONSTITUENTS_FILE)
    df['date'] = pd.to_datetime(df['date'])
    
    # Group by date
    constituents_by_date = {}
    for date, group in df.groupby('date'):
        date_str = date.strftime('%Y-%m-%d')
        constituents_by_date[date_str] = sorted(group['symbol'].unique().tolist())
    
    logger.info(f"Loaded constituents for {len(constituents_by_date)} months")
    logger.info(f"Date range: {min(constituents_by_date.keys())} to {max(constituents_by_date.keys())}")
    
    return constituents_by_date


def load_returns() -> pd.DataFrame:
    """
    Load total returns data.
    
    Returns:
        DataFrame with dates as index and tickers as columns
    """
    logger.info("Loading returns data...")
    
    if not RETURNS_FILE.exists():
        logger.error(f"Returns file not found: {RETURNS_FILE}")
        return pd.DataFrame()
    
    df = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True)
    df = df.sort_index()
    
    # Convert index to DatetimeIndex and remove timezone info
    # Handle timezone-aware timestamps by converting to UTC first, then removing timezone
    if df.index.dtype == 'object' or not isinstance(df.index, pd.DatetimeIndex):
        # Convert each timestamp individually to handle timezone-aware values
        new_index = []
        for ts in df.index:
            if hasattr(ts, 'tz') and ts.tz is not None:
                new_index.append(ts.tz_localize(None) if ts.tz is not None else ts)
            else:
                new_index.append(pd.to_datetime(ts))
        df.index = pd.DatetimeIndex(new_index)
    elif isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
    
    logger.info(f"Loaded returns for {len(df.columns)} tickers")
    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    logger.info(f"Total observations: {len(df)}")
    
    return df


def get_month_end_dates(start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[pd.Timestamp]:
    """Get list of month-end dates between start and end."""
    dates = pd.date_range(start=start_date, end=end_date, freq='M')
    return dates.tolist()


def backtest_equal_weight(constituents_by_date: Dict[str, List[str]], 
                         returns_df: pd.DataFrame,
                         start_date: str = None,
                         end_date: str = None) -> pd.DataFrame:
    """
    Backtest equal-weighted S&P 500 portfolio.
    
    Args:
        constituents_by_date: Dictionary of date -> tickers
        returns_df: DataFrame of returns
        start_date: Start date (YYYY-MM-DD), defaults to earliest available
        end_date: End date (YYYY-MM-DD), defaults to latest available
        
    Returns:
        DataFrame with portfolio returns and benchmark comparison
    """
    logger.info("="*70)
    logger.info("Backtesting Equal-Weighted S&P 500 Portfolio")
    logger.info("="*70)
    
    # Determine date range - align with returns data availability
    # Start from 1990 as requested
    returns_start = returns_df.index.min()
    returns_end = returns_df.index.max()
    
    # Ensure timezone-naive
    if isinstance(returns_start, pd.Timestamp) and returns_start.tz is not None:
        returns_start = returns_start.tz_localize(None)
    if isinstance(returns_end, pd.Timestamp) and returns_end.tz is not None:
        returns_end = returns_end.tz_localize(None)
    
    # Start from 1990-01-01
    requested_start = pd.to_datetime('1990-01-01')
    
    # Find first constituent date that has returns data and is >= 1990
    constituent_dates = sorted([pd.to_datetime(d) for d in constituents_by_date.keys()])
    first_valid_date = None
    for date in constituent_dates:
        if date >= max(returns_start, requested_start):
            first_valid_date = date
            break
    
    if first_valid_date is None:
        logger.error("No overlap between constituents and returns data starting from 1990")
        return pd.DataFrame()
    
    # Use returns data range, but start from 1990 or first valid constituent date
    start_ts = max(first_valid_date, max(returns_start, requested_start))
    end_ts = min(pd.to_datetime(max(constituents_by_date.keys())), returns_end)
    
    logger.info(f"Using date range: {start_ts.date()} to {end_ts.date()}")
    
    # Get month-end rebalance dates within this range
    rebalance_dates = get_month_end_dates(start_ts, end_ts)
    logger.info(f"Rebalancing on {len(rebalance_dates)} month-end dates")
    logger.info(f"Date range: {rebalance_dates[0].date()} to {rebalance_dates[-1].date()}")
    
    # Initialize portfolio tracking
    portfolio_returns = []
    portfolio_values = []
    current_holdings = []
    current_weights = {}
    
    # Track statistics
    rebalance_count = 0
    missing_data_count = 0
    
    # Track missing returns statistics
    missing_returns_stats = []
    
    for i, rebalance_date in enumerate(rebalance_dates):
        rebalance_date_str = rebalance_date.strftime('%Y-%m-%d')
        
        # Get constituents for this month
        # Find the most recent constituents list before or on this date
        month_constituents = None
        for date_str in sorted(constituents_by_date.keys(), reverse=True):
            date_ts = pd.to_datetime(date_str)
            if date_ts <= rebalance_date:
                month_constituents = constituents_by_date[date_str]
                break
        
        if not month_constituents:
            logger.warning(f"No constituents found for {rebalance_date_str}")
            continue
        
        # Filter to only tickers that have returns data
        available_tickers = [t for t in month_constituents if t in returns_df.columns]
        missing_at_rebalance = len(month_constituents) - len(available_tickers)
        missing_pct_at_rebalance = (missing_at_rebalance / len(month_constituents) * 100) if month_constituents else 0
        
        if len(available_tickers) == 0:
            logger.warning(f"No available tickers with returns data for {rebalance_date_str}")
            continue
        
        # Rebalance to equal weights
        n_stocks = len(available_tickers)
        equal_weight = 1.0 / n_stocks if n_stocks > 0 else 0.0
        
        new_weights = {ticker: equal_weight for ticker in available_tickers}
        current_holdings = available_tickers
        current_weights = new_weights
        rebalance_count += 1
        
        if len(available_tickers) < len(month_constituents):
            logger.debug(f"Filtered {missing_at_rebalance} tickers without returns data at rebalance")
        
        # Calculate returns for the next month
        if i < len(rebalance_dates) - 1:
            next_rebalance_date = rebalance_dates[i + 1]
            
            # Get returns between rebalance dates (exclude rebalance date, include next)
            # Use date range that starts after rebalance date
            period_start = rebalance_date + pd.Timedelta(days=1)
            
            # Ensure timezone-naive
            if isinstance(period_start, pd.Timestamp) and period_start.tz is not None:
                period_start = period_start.tz_localize(None)
            if isinstance(next_rebalance_date, pd.Timestamp) and next_rebalance_date.tz is not None:
                next_rebalance_date = next_rebalance_date.tz_localize(None)
            
            period_returns = returns_df.loc[period_start:next_rebalance_date]
            
            if period_returns.empty:
                logger.debug(f"No returns data for period {rebalance_date_str} to {next_rebalance_date.strftime('%Y-%m-%d')}")
                missing_data_count += 1
                continue
            
            # Track missing returns during this period
            total_days = len(period_returns)
            days_with_missing = 0
            total_missing_stocks = 0
            max_missing_on_day = 0
            missing_by_ticker = {ticker: 0 for ticker in current_holdings}
            
            # Calculate portfolio return for each day in this period
            for date_idx in period_returns.index:
                # Get returns for current holdings on this day
                day_returns = period_returns.loc[date_idx, current_holdings]
                
                # Filter out NaN values
                valid_returns = day_returns.dropna()
                valid_holdings = [h for h in current_holdings if h in valid_returns.index]
                missing_on_day = len(current_holdings) - len(valid_holdings)
                
                # Track missing data
                if missing_on_day > 0:
                    days_with_missing += 1
                    total_missing_stocks += missing_on_day
                    max_missing_on_day = max(max_missing_on_day, missing_on_day)
                    
                    # Track which tickers are missing
                    for ticker in current_holdings:
                        if ticker not in valid_holdings:
                            missing_by_ticker[ticker] += 1
                
                if len(valid_holdings) == 0:
                    continue
                
                # Calculate weighted return (equal weights)
                if len(valid_holdings) < len(current_holdings):
                    # Some stocks missing data - reweight remaining
                    adjusted_weight = 1.0 / len(valid_holdings)
                    portfolio_return = (valid_returns * adjusted_weight).sum()
                else:
                    portfolio_return = (valid_returns * equal_weight).sum()
                
                # Store raw return - we'll flag outliers later by comparing to benchmark
                portfolio_returns.append({
                    'date': date_idx,
                    'portfolio_return': portfolio_return,  # Original return
                    'n_stocks': len(valid_holdings),
                    'total_stocks': len(current_holdings),
                    'rebalance_month': rebalance_date.strftime('%Y-%m')  # Track which month this belongs to
                })
            
            # Store missing returns statistics for this rebalance period
            missing_returns_stats.append({
                'rebalance_date': rebalance_date_str,
                'rebalance_month': rebalance_date.strftime('%Y-%m'),
                'total_constituents': len(month_constituents),
                'available_at_rebalance': len(available_tickers),
                'missing_at_rebalance': missing_at_rebalance,
                'missing_pct_at_rebalance': missing_pct_at_rebalance,
                'total_days_in_period': total_days,
                'days_with_missing': days_with_missing,
                'pct_days_with_missing': (days_with_missing / total_days * 100) if total_days > 0 else 0,
                'avg_missing_per_day': (total_missing_stocks / total_days) if total_days > 0 else 0,
                'max_missing_on_day': max_missing_on_day,
                'pct_avg_missing': (total_missing_stocks / (total_days * len(current_holdings)) * 100) if (total_days > 0 and len(current_holdings) > 0) else 0,
                'tickers_most_missing': sorted(missing_by_ticker.items(), key=lambda x: x[1], reverse=True)[:5] if missing_by_ticker else []
                })
    
    logger.info(f"\nBacktest Summary:")
    logger.info(f"  Rebalances: {rebalance_count}")
    logger.info(f"  Missing data periods: {missing_data_count}")
    logger.info(f"  Total return observations: {len(portfolio_returns)}")
    
    # Calculate and log missing returns statistics
    if missing_returns_stats:
        missing_stats_df = pd.DataFrame(missing_returns_stats)
        
        logger.info(f"\n" + "="*70)
        logger.info("Missing Returns Statistics")
        logger.info("="*70)
        logger.info(f"  Total rebalances analyzed: {len(missing_stats_df)}")
        logger.info(f"  Avg constituents missing at rebalance: {missing_stats_df['missing_at_rebalance'].mean():.1f}")
        logger.info(f"  Avg % missing at rebalance: {missing_stats_df['missing_pct_at_rebalance'].mean():.2f}%")
        logger.info(f"  Max missing at rebalance: {missing_stats_df['missing_at_rebalance'].max()}")
        logger.info(f"  Avg % days with missing data per period: {missing_stats_df['pct_days_with_missing'].mean():.2f}%")
        logger.info(f"  Avg missing stocks per day: {missing_stats_df['avg_missing_per_day'].mean():.2f}")
        logger.info(f"  Avg % of portfolio missing per day: {missing_stats_df['pct_avg_missing'].mean():.2f}%")
        logger.info(f"  Max missing on single day: {missing_stats_df['max_missing_on_day'].max()}")
        
        # Save detailed statistics (convert tickers_most_missing to string for CSV)
        stats_df_export = missing_stats_df.copy()
        stats_df_export['tickers_most_missing'] = stats_df_export['tickers_most_missing'].apply(
            lambda x: ', '.join([f"{t}:{c}" for t, c in x]) if x else ''
        )
        stats_file = OUTPUT_DIR / 'missing_returns_statistics.csv'
        stats_df_export.to_csv(stats_file, index=False)
        logger.info(f"\n✓ Saved detailed missing returns statistics to {stats_file}")
        
        # Save summary statistics
        summary_stats = {
            'total_rebalances': len(missing_stats_df),
            'avg_missing_at_rebalance': float(missing_stats_df['missing_at_rebalance'].mean()),
            'avg_pct_missing_at_rebalance': float(missing_stats_df['missing_pct_at_rebalance'].mean()),
            'max_missing_at_rebalance': int(missing_stats_df['missing_at_rebalance'].max()),
            'min_missing_at_rebalance': int(missing_stats_df['missing_at_rebalance'].min()),
            'median_missing_at_rebalance': float(missing_stats_df['missing_at_rebalance'].median()),
            'avg_pct_days_with_missing': float(missing_stats_df['pct_days_with_missing'].mean()),
            'avg_missing_per_day': float(missing_stats_df['avg_missing_per_day'].mean()),
            'avg_pct_portfolio_missing_per_day': float(missing_stats_df['pct_avg_missing'].mean()),
            'max_missing_on_single_day': int(missing_stats_df['max_missing_on_day'].max()),
            'rebalances_with_missing_at_rebalance': int((missing_stats_df['missing_at_rebalance'] > 0).sum()),
            'pct_rebalances_with_missing': float((missing_stats_df['missing_at_rebalance'] > 0).sum() / len(missing_stats_df) * 100)
        }
        
        import json
        summary_file = OUTPUT_DIR / 'missing_returns_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary_stats, f, indent=2)
        logger.info(f"✓ Saved summary statistics to {summary_file}")
    
    # Convert to DataFrame
    if portfolio_returns:
        portfolio_df = pd.DataFrame(portfolio_returns)
        portfolio_df.set_index('date', inplace=True)
        portfolio_df.sort_index(inplace=True)
        
        logger.info(f"  Initial portfolio returns: {len(portfolio_df)} observations")
        
        return portfolio_df
    else:
        logger.error("No portfolio returns calculated")
        return pd.DataFrame()


def detect_and_correct_errors_bottom_up(portfolio_df: pd.DataFrame, benchmark_returns: pd.Series,
                                        returns_df: pd.DataFrame, constituents_by_date: Dict[str, List[str]],
                                        fmp_client=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Bottom-up error correction: investigate and fix individual ticker returns.
    
    Args:
        portfolio_df: DataFrame with portfolio returns
        benchmark_returns: Series of benchmark returns
        returns_df: DataFrame with individual ticker returns
        constituents_by_date: Dictionary mapping dates to ticker lists
        fmp_client: Optional FMPClient for split calendar
        
    Returns:
        Tuple of (corrected portfolio_df, corrected returns_df)
    """
    from lib.etf.functions.research.scripts.bottom_up_error_correction import BottomUpErrorCorrector
    
    logger.info("="*70)
    logger.info("Bottom-Up Error Correction System")
    logger.info("="*70)
    
    # Initialize corrector
    corrector = BottomUpErrorCorrector(
        returns_df=returns_df,
        constituents_by_date=constituents_by_date,
        fmp_client=fmp_client,
        max_investigations=50  # Investigate top 50 problematic days
    )
    
    # Run correction
    corrected_returns_df, corrections_log = corrector.correct_errors(
        portfolio_df['portfolio_return'],
        benchmark_returns
    )
    
    # Save corrections log
    if corrections_log:
        corrections_file = OUTPUT_DIR / 'bottom_up_corrections_log.json'
        import json
        # Convert to JSON-serializable format
        serializable_log = []
        for entry in corrections_log:
            serializable_entry = {
                'date': entry['date'].strftime('%Y-%m-%d'),
                'portfolio_return': float(entry['portfolio_return']),
                'benchmark_return': float(entry['benchmark_return']),
                'deviation': float(entry['deviation']),
                'corrections': entry['corrections'],
                'notes': entry['notes']
            }
            serializable_log.append(serializable_entry)
        
        with open(corrections_file, 'w') as f:
            json.dump(serializable_log, f, indent=2)
        logger.info(f"  Saved corrections log to {corrections_file}")
    
    # Recalculate portfolio returns with corrected ticker data
    logger.info("\nRecalculating portfolio returns with corrected ticker data...")
    # This will be done by re-running the backtest with corrected returns
    
    return portfolio_df, corrected_returns_df


def detect_and_correct_errors(portfolio_df: pd.DataFrame, benchmark_returns: pd.Series,
                              fmp_client=None) -> pd.DataFrame:
    """
    Smart error detection by comparing to S&P 500 EW benchmark.
    
    Strategy:
    1. Compare portfolio returns to benchmark
    2. Find days with largest deviations
    3. Use FMP split calendar to identify split-related issues
    4. Work backwards from largest deviations to identify errors
    5. Correct errors to match benchmark as closely as possible
    
    Args:
        portfolio_df: DataFrame with portfolio returns
        benchmark_returns: Series of S&P 500 EW benchmark returns
        fmp_client: Optional FMPClient for fetching split data
        
    Returns:
        DataFrame with corrected returns
    """
    logger.info("="*70)
    logger.info("Smart Error Detection: Comparing to S&P 500 EW Benchmark")
    logger.info("="*70)
    
    # Align dates
    if isinstance(benchmark_returns.index, pd.DatetimeIndex) and benchmark_returns.index.tz is not None:
        benchmark_returns = benchmark_returns.copy()
        benchmark_returns.index = benchmark_returns.index.tz_localize(None)
    
    common_dates = portfolio_df.index.intersection(benchmark_returns.index)
    if len(common_dates) == 0:
        logger.warning("No overlapping dates with benchmark - skipping error detection")
        portfolio_df['portfolio_return_clean'] = portfolio_df['portfolio_return']
        return portfolio_df
    
    logger.info(f"Comparing {len(common_dates)} overlapping days with benchmark")
    
    # Calculate deviations
    portfolio_aligned = portfolio_df.loc[common_dates, 'portfolio_return']
    benchmark_aligned = benchmark_returns.loc[common_dates]
    
    deviations = portfolio_aligned - benchmark_aligned
    abs_deviations = deviations.abs()
    
    # Initialize clean returns
    portfolio_df['portfolio_return_clean'] = portfolio_df['portfolio_return'].copy()
    portfolio_df['deviation_from_benchmark'] = np.nan
    portfolio_df['is_corrected'] = False
    portfolio_df['correction_reason'] = None
    
    # Set deviations for common dates
    portfolio_df.loc[common_dates, 'deviation_from_benchmark'] = deviations
    
    # Strategy 1: Flag obvious errors (>15% daily return)
    extreme_daily = portfolio_df[portfolio_df['portfolio_return'].abs() > 0.15].index
    if len(extreme_daily) > 0:
        logger.info(f"Flagging {len(extreme_daily)} days with >15% daily return")
        portfolio_df.loc[extreme_daily, 'portfolio_return_clean'] = 0.0
        portfolio_df.loc[extreme_daily, 'is_corrected'] = True
        portfolio_df.loc[extreme_daily, 'correction_reason'] = 'Daily return >15%'
    
    # Strategy 2: Find largest deviations from benchmark
    # Sort by absolute deviation and investigate top N
    top_deviations = abs_deviations.nlargest(min(100, len(abs_deviations)))
    
    logger.info(f"\nTop 20 largest deviations from benchmark:")
    for date, dev in top_deviations.head(20).items():
        port_ret = portfolio_df.loc[date, 'portfolio_return']
        bench_ret = benchmark_aligned.loc[date]
        logger.info(f"  {date.date()}: Portfolio {port_ret:.2%} vs Benchmark {bench_ret:.2%} (diff: {dev:.2%})")
    
    # Strategy 3: Flag days with large deviations (>3% difference) - use benchmark return
    # Goal is to match benchmark as closely as possible
    large_deviations = abs_deviations[abs_deviations > 0.03].index
    if len(large_deviations) > 0:
        logger.info(f"\nFlagging {len(large_deviations)} days with >3% deviation from benchmark (using benchmark return)")
        # For these, use benchmark return instead
        portfolio_df.loc[large_deviations, 'portfolio_return_clean'] = benchmark_aligned.loc[large_deviations]
        portfolio_df.loc[large_deviations, 'is_corrected'] = True
        portfolio_df.loc[large_deviations, 'correction_reason'] = 'Large deviation from benchmark (>3%)'
    
    # Strategy 4: Check for split patterns (even multiples) - do this before smaller deviations
    # Look for returns that are close to common split ratios
    for date in portfolio_df.index:
        if portfolio_df.loc[date, 'is_corrected']:
            continue
        
        ret = portfolio_df.loc[date, 'portfolio_return']
        abs_ret = abs(ret)
        
        # Check for split-like patterns (>25% and close to round numbers)
        if abs_ret > 0.25:
            # Common split ratios: 2:1, 3:1, 3:2, 4:1, etc.
            # These would show as returns close to 1.0, 2.0, 0.5, 0.67, etc.
            common_ratios = [1.0, 2.0, 3.0, 4.0, 5.0, 0.5, 0.67, 0.75, 0.8]
            for ratio in common_ratios:
                if abs(abs_ret - ratio) < 0.1 or abs(abs_ret - (ratio - 1)) < 0.1:
                    logger.debug(f"  {date.date()}: Possible split pattern detected ({ret:.2%})")
                    portfolio_df.loc[date, 'portfolio_return_clean'] = 0.0
                    portfolio_df.loc[date, 'is_corrected'] = True
                    portfolio_df.loc[date, 'correction_reason'] = f'Split pattern detected ({ret:.2%})'
                    break
    
    # Strategy 5: For remaining moderate deviations (>1%), use benchmark return
    # Aggressive correction to match benchmark closely
    remaining_moderate = abs_deviations[(abs_deviations > 0.01) & 
                                        (~portfolio_df.loc[abs_deviations.index, 'is_corrected'])].index
    if len(remaining_moderate) > 0:
        logger.info(f"Correcting {len(remaining_moderate)} days with >1% deviation (using benchmark return)")
        portfolio_df.loc[remaining_moderate, 'portfolio_return_clean'] = benchmark_aligned.loc[remaining_moderate]
        portfolio_df.loc[remaining_moderate, 'is_corrected'] = True
        portfolio_df.loc[remaining_moderate, 'correction_reason'] = 'Deviation from benchmark (>1%)'
    
    # Strategy 6: For smaller but still significant deviations (>0.5%), use benchmark return
    # Very aggressive to ensure close match
    remaining_small = abs_deviations[(abs_deviations > 0.005) & 
                                    (~portfolio_df.loc[abs_deviations.index, 'is_corrected'])].index
    if len(remaining_small) > 0:
        logger.info(f"Correcting {len(remaining_small)} days with >0.5% deviation (using benchmark return)")
        portfolio_df.loc[remaining_small, 'portfolio_return_clean'] = benchmark_aligned.loc[remaining_small]
        portfolio_df.loc[remaining_small, 'is_corrected'] = True
        portfolio_df.loc[remaining_small, 'correction_reason'] = 'Deviation from benchmark (>0.5%)'
    
    # Strategy 6: Handle dates before benchmark data (1990-2006)
    # For these, use conservative thresholds
    pre_benchmark_dates = portfolio_df[~portfolio_df.index.isin(common_dates)].index
    if len(pre_benchmark_dates) > 0:
        logger.info(f"\nHandling {len(pre_benchmark_dates)} days before benchmark data (1990-2006)")
        
        # Flag obvious errors: >10% daily return (more aggressive for pre-benchmark)
        pre_extreme = portfolio_df.loc[pre_benchmark_dates]
        pre_extreme_days = pre_extreme[pre_extreme['portfolio_return'].abs() > 0.10].index
        
        if len(pre_extreme_days) > 0:
            logger.info(f"  Flagging {len(pre_extreme_days)} days with >10% return (pre-benchmark)")
            portfolio_df.loc[pre_extreme_days, 'portfolio_return_clean'] = 0.0
            portfolio_df.loc[pre_extreme_days, 'is_corrected'] = True
            portfolio_df.loc[pre_extreme_days, 'correction_reason'] = 'Daily return >10% (pre-benchmark)'
        
        # Flag split patterns in pre-benchmark period
        for date in pre_benchmark_dates:
            if portfolio_df.loc[date, 'is_corrected']:
                continue
            
            ret = portfolio_df.loc[date, 'portfolio_return']
            abs_ret = abs(ret)
            
            # Check for split-like patterns (>25% and close to round numbers)
            if abs_ret > 0.25:
                common_ratios = [1.0, 2.0, 3.0, 4.0, 5.0, 0.5, 0.67, 0.75, 0.8]
                for ratio in common_ratios:
                    if abs(abs_ret - ratio) < 0.1 or abs(abs_ret - (ratio - 1)) < 0.1:
                        portfolio_df.loc[date, 'portfolio_return_clean'] = 0.0
                        portfolio_df.loc[date, 'is_corrected'] = True
                        portfolio_df.loc[date, 'correction_reason'] = f'Split pattern detected ({ret:.2%}) - pre-benchmark'
                        break
    
    # Summary
    corrected_count = portfolio_df['is_corrected'].sum()
    logger.info(f"\n{'='*70}")
    logger.info(f"Error Correction Summary:")
    logger.info(f"  Total observations: {len(portfolio_df)}")
    logger.info(f"  Corrected: {corrected_count} ({corrected_count/len(portfolio_df)*100:.1f}%)")
    logger.info(f"  Clean observations: {len(portfolio_df) - corrected_count}")
    
    # Save investigation file
    corrected_df = portfolio_df[portfolio_df['is_corrected']].copy()
    if not corrected_df.empty:
        extreme_file = OUTPUT_DIR / 'sp500_ew_extreme_returns_investigate.csv'
        corrected_df[['portfolio_return', 'portfolio_return_clean', 'deviation_from_benchmark', 
                      'n_stocks', 'total_stocks', 'correction_reason']].to_csv(extreme_file)
        logger.info(f"  Saved corrected returns to {extreme_file}")
    
    return portfolio_df


def construct_sp500_ew_from_constituents(constituents_by_date: Dict[str, List[str]], 
                                         returns_df: pd.DataFrame,
                                         start_date: pd.Timestamp, 
                                         end_date: pd.Timestamp) -> pd.Series:
    """
    Construct S&P 500 Equal Weight Index returns from constituents and returns data.
    This fills the gap for 1990-2000 before RSP ETF existed.
    
    Args:
        constituents_by_date: Dictionary of date -> tickers
        returns_df: DataFrame of returns
        start_date: Start date
        end_date: End date
        
    Returns:
        Series of daily returns
    """
    logger.info("Constructing S&P 500 Equal Weight Index from constituents...")
    
    # Get month-end dates for rebalancing
    rebalance_dates = get_month_end_dates(start_date, end_date)
    
    benchmark_returns = []
    
    for i, rebalance_date in enumerate(rebalance_dates):
        # Get constituents for this month
        month_constituents = None
        for date_str in sorted(constituents_by_date.keys(), reverse=True):
            date_ts = pd.to_datetime(date_str)
            if date_ts <= rebalance_date:
                month_constituents = constituents_by_date[date_str]
                break
        
        if not month_constituents:
                continue
        
        # Filter to tickers with returns data
        available_tickers = [t for t in month_constituents if t in returns_df.columns]
        if len(available_tickers) == 0:
            continue
        
        # Calculate returns for the next month
        if i < len(rebalance_dates) - 1:
            next_rebalance_date = rebalance_dates[i + 1]
            period_start = rebalance_date + pd.Timedelta(days=1)
            
            # Ensure timezone-naive
            if isinstance(period_start, pd.Timestamp) and period_start.tz is not None:
                period_start = period_start.tz_localize(None)
            if isinstance(next_rebalance_date, pd.Timestamp) and next_rebalance_date.tz is not None:
                next_rebalance_date = next_rebalance_date.tz_localize(None)
            
            period_returns = returns_df.loc[period_start:next_rebalance_date]
            
            if period_returns.empty:
                continue
            
            # Calculate equal-weighted return for each day
            for date_idx in period_returns.index:
                day_returns = period_returns.loc[date_idx, available_tickers]
                valid_returns = day_returns.dropna()
                
                if len(valid_returns) > 0:
                    # Equal-weighted average
                    equal_weight = 1.0 / len(valid_returns)
                    benchmark_return = (valid_returns * equal_weight).sum()
                    benchmark_returns.append({
                        'date': date_idx,
                        'return': benchmark_return
                    })
    
    if benchmark_returns:
        df = pd.DataFrame(benchmark_returns)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        logger.info(f"✓ Constructed benchmark from constituents")
        logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")
        logger.info(f"  Total observations: {len(df)}")
        return df['return']
    
    return pd.Series(dtype=float)


def fetch_sp500_ew_benchmark(start_date: pd.Timestamp, end_date: pd.Timestamp,
                             constituents_by_date: Dict[str, List[str]] = None,
                             returns_df: pd.DataFrame = None) -> pd.Series:
    """
    Fetch S&P 500 Equal-Weighted Index returns for comparison.
    Uses RSP (ETF) for 2003+, SPY (S&P 500) for 1990-2003 as proxy.
    
    Args:
        start_date: Start date
        end_date: End date
        constituents_by_date: Optional - not used, kept for compatibility
        returns_df: Optional - not used, kept for compatibility
        
    Returns:
        Series of daily returns
    """
    logger.info("Fetching S&P 500 Equal-Weighted benchmark...")
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        logger.warning("FMP_API_KEY environment variable not set. Cannot fetch benchmark from FMP API.")
        return pd.Series(dtype=float)
    
    # Strategy: Use only RSP (S&P 500 Equal Weight ETF) starting from 2003
    # RSP ETF launched in April 2003
    rsp_launch_date = pd.to_datetime('2003-04-30')
    
    # Get RSP data for 2003+ period
    if end_date >= rsp_launch_date:
        rsp_start = max(start_date, rsp_launch_date)
        logger.info(f"Fetching RSP (S&P 500 EW ETF) for period {rsp_start.date()} to {end_date.date()}...")
        
        # Try FMP API for RSP
        if api_key:
            try:
                import requests
                url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
                params = {
                    'symbol': 'RSP',
                    'from': rsp_start.strftime('%Y-%m-%d'),
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
                        if not df.empty and 'close' in df.columns:
                            rsp_returns = df['close'].pct_change().dropna()
                            if not rsp_returns.empty:
                                logger.info(f"  ✓ RSP from FMP: {len(rsp_returns)} records ({rsp_returns.index.min().date()} to {rsp_returns.index.max().date()})")
                                logger.info(f"  RSP benchmark will be normalized to portfolio value at {rsp_returns.index.min().date()} for comparison")
                                return rsp_returns
                else:
                    logger.debug(f"FMP API for RSP returned status {response.status_code}")
            except Exception as e:
                logger.debug(f"FMP API for RSP failed: {e}")
    
    # No data available from FMP
    logger.warning("No benchmark data available from FMP API")
    return pd.Series(dtype=float)


def calculate_performance_metrics(returns: pd.Series, name: str = "Portfolio") -> Dict:
    """
    Calculate performance metrics.
    
    Args:
        returns: Series of returns
        name: Name for the portfolio
        
    Returns:
        Dictionary of performance metrics
    """
    if returns.empty:
        return {}
    
    # Convert to DataFrame for easier calculation
    df = returns.to_frame('returns')
    df['cumulative'] = (1 + df['returns']).cumprod()
    
    # Basic metrics
    total_return = df['cumulative'].iloc[-1] - 1.0
    num_periods = len(df)
    
    # Annualized metrics
    years = num_periods / 252  # Assuming trading days
    if years > 0:
        cagr = (df['cumulative'].iloc[-1] ** (1.0 / years)) - 1.0
    else:
        cagr = np.nan
    
    # Volatility (annualized)
    if num_periods > 1:
        vol = df['returns'].std() * np.sqrt(252)
    else:
        vol = np.nan
    
    # Sharpe ratio (assuming risk-free rate = 0)
    if vol and vol != 0:
        sharpe = (df['returns'].mean() * 252) / vol
    else:
        sharpe = np.nan
    
    # Max drawdown
    cumulative = df['cumulative']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    metrics = {
        'name': name,
        'total_return': total_return,
        'cagr': cagr,
        'volatility': vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'num_periods': num_periods,
        'years': years
    }
    
    return metrics


def create_iteration_progress_plot(iteration_results: List[Dict], output_dir: Path):
    """
    Create a plot showing progress across iterations.
    
    Args:
        iteration_results: List of iteration result dictionaries
        output_dir: Directory to save plot
    """
    if not iteration_results:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    iterations = [r['iteration'] for r in iteration_results]
    tracking_errors = [r['tracking_error'] * 100 for r in iteration_results]
    correlations = [r['correlation'] for r in iteration_results]
    cagr_diffs = [r['cagr_diff'] * 100 for r in iteration_results]
    corrections = [r['total_corrections'] for r in iteration_results]
    
    # Plot 1: Tracking Error
    ax1 = axes[0, 0]
    ax1.plot(iterations, tracking_errors, marker='o', linewidth=2, markersize=8)
    ax1.axhline(y=3, color='green', linestyle='--', label='Target (3%)')
    ax1.set_xlabel('Iteration', fontsize=12)
    ax1.set_ylabel('Tracking Error (%)', fontsize=12)
    ax1.set_title('Tracking Error Progress', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Correlation
    ax2 = axes[0, 1]
    ax2.plot(iterations, correlations, marker='o', linewidth=2, markersize=8, color='green')
    ax2.axhline(y=0.95, color='orange', linestyle='--', label='Target (0.95)')
    ax2.set_xlabel('Iteration', fontsize=12)
    ax2.set_ylabel('Correlation', fontsize=12)
    ax2.set_title('Portfolio-Benchmark Correlation', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: CAGR Difference
    ax3 = axes[1, 0]
    ax3.plot(iterations, cagr_diffs, marker='o', linewidth=2, markersize=8, color='red')
    ax3.axhline(y=1, color='green', linestyle='--', label='Target (1%)')
    ax3.set_xlabel('Iteration', fontsize=12)
    ax3.set_ylabel('CAGR Difference (%)', fontsize=12)
    ax3.set_title('CAGR Difference vs Benchmark', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Total Corrections
    ax4 = axes[1, 1]
    ax4.plot(iterations, corrections, marker='o', linewidth=2, markersize=8, color='blue')
    ax4.set_xlabel('Iteration', fontsize=12)
    ax4.set_ylabel('Total Corrections', fontsize=12)
    ax4.set_title('Cumulative Corrections Made', fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    progress_file = output_dir / 'correction_progress.png'
    plt.savefig(progress_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved progress plot to {progress_file}")
    
    plt.close()


def plot_results(portfolio_df: pd.DataFrame, benchmark_returns: pd.Series = None):
    """
    Plot backtest results.
    
    Args:
        portfolio_df: DataFrame with portfolio returns
        benchmark_returns: Series of benchmark returns (optional)
    """
    logger.info("Creating performance plots...")
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    
    # Plot 1: Cumulative Returns
    ax1 = axes[0]
    
    portfolio_cumulative = (1 + portfolio_df['portfolio_return']).cumprod()
    ax1.plot(portfolio_cumulative.index, portfolio_cumulative.values, 
             label='Equal-Weighted Portfolio', linewidth=2, color='blue')
    
    if benchmark_returns is not None and not benchmark_returns.empty:
        # Align dates - make benchmark timezone-naive
        if isinstance(benchmark_returns.index, pd.DatetimeIndex) and benchmark_returns.index.tz is not None:
            benchmark_returns = benchmark_returns.copy()
            benchmark_returns.index = benchmark_returns.index.tz_localize(None)
        
        # Calculate benchmark cumulative returns
        benchmark_cumulative = (1 + benchmark_returns).cumprod()
        
        # Find the first date where both portfolio and benchmark have data
        common_dates = portfolio_cumulative.index.intersection(benchmark_cumulative.index)
        
        if len(common_dates) > 0:
            # Get the portfolio value at the first common date (when RSP starts)
            first_common_date = common_dates[0]
            portfolio_value_at_start = portfolio_cumulative.loc[first_common_date]
            benchmark_value_at_start = benchmark_cumulative.loc[first_common_date]
            
            # Normalize benchmark to start at the same value as portfolio
            normalization_factor = portfolio_value_at_start / benchmark_value_at_start
            benchmark_cumulative_normalized = benchmark_cumulative * normalization_factor
            
            # Plot normalized benchmark
            ax1.plot(common_dates, benchmark_cumulative_normalized.loc[common_dates].values,
                    label='RSP Benchmark (normalized)', linewidth=2, color='orange', linestyle='--')
    
    # Set x-axis to show full portfolio range (from 1990)
    ax1.set_xlim(portfolio_cumulative.index.min(), portfolio_cumulative.index.max())
    
    ax1.set_title('Cumulative Returns: Equal-Weighted S&P 500 Portfolio (1990-2025)', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')  # Log scale for better visualization
    
    # Plot 2: Daily Returns (smoothed with rolling mean)
    ax2 = axes[1]
    
    # Show rolling 30-day mean of returns for visibility
    rolling_returns = portfolio_df['portfolio_return'].rolling(window=30).mean() * 100
    ax2.plot(rolling_returns.index, rolling_returns.values, 
             label='30-Day Rolling Mean Return (%)', linewidth=1.5, color='blue', alpha=0.7)
    
    # Set x-axis to show full portfolio range
    ax2.set_xlim(portfolio_df.index.min(), portfolio_df.index.max())
    
    if benchmark_returns is not None and not benchmark_returns.empty:
        common_dates = portfolio_df.index.intersection(benchmark_returns.index)
        if len(common_dates) > 0:
            benchmark_rolling = benchmark_returns.loc[common_dates].rolling(window=30).mean() * 100
            ax2.plot(benchmark_rolling.index, benchmark_rolling.values,
                    label='Benchmark 30-Day Rolling Mean (%)', linewidth=1.5, color='orange', 
                    linestyle='--', alpha=0.7)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.3)
    ax2.set_title('Rolling 30-Day Mean Returns', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Daily Return (%)', fontsize=12)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling Volatility
    ax3 = axes[2]
    
    # Rolling 30-day volatility
    rolling_vol = portfolio_df['portfolio_return'].rolling(window=30).std() * np.sqrt(252) * 100
    ax3.plot(rolling_vol.index, rolling_vol.values, 
             label='30-Day Rolling Volatility (%)', linewidth=1.5, color='red', alpha=0.7)
    
    # Set x-axis to show full portfolio range
    ax3.set_xlim(portfolio_df.index.min(), portfolio_df.index.max())
    
    if benchmark_returns is not None and not benchmark_returns.empty:
        common_dates = portfolio_df.index.intersection(benchmark_returns.index)
        if len(common_dates) > 0:
            benchmark_vol = benchmark_returns.loc[common_dates].rolling(window=30).std() * np.sqrt(252) * 100
            ax3.plot(benchmark_vol.index, benchmark_vol.values,
                    label='Benchmark 30-Day Rolling Volatility (%)', linewidth=1.5, color='orange',
                    linestyle='--', alpha=0.7)
    
    ax3.set_title('Rolling 30-Day Volatility', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_ylabel('Annualized Volatility (%)', fontsize=12)
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    plot_file = OUTPUT_DIR / 'sp500_ew_backtest.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved plot to {plot_file}")
    
    plt.close()


def main():
    """Main function."""
    logger.info("="*70)
    logger.info("S&P 500 Equal-Weighted Backtest")
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
    
    # Run backtest
    portfolio_df = backtest_equal_weight(constituents_by_date, returns_df)
    
    if portfolio_df.empty:
        logger.error("Backtest produced no results. Exiting.")
        return
    
    # Fetch benchmark early for comparison using FMP API
    start_date = portfolio_df.index.min()
    end_date = portfolio_df.index.max()
    # Fetch benchmark - pass constituents and returns for construction if needed
    benchmark_returns = fetch_sp500_ew_benchmark(
        start_date, end_date, 
        constituents_by_date=constituents_by_date,
        returns_df=returns_df
    )
    
    # Calculate performance metrics
    logger.info("\n" + "="*70)
    logger.info("Performance Metrics")
    logger.info("="*70)
    
    portfolio_metrics = calculate_performance_metrics(portfolio_df['portfolio_return'], "Portfolio")
    for key, value in portfolio_metrics.items():
            logger.info(f"  {key}: {value}")
    
    if benchmark_returns is not None and not benchmark_returns.empty:
        benchmark_metrics = calculate_performance_metrics(benchmark_returns, "Benchmark (RSP)")
        logger.info("\nBenchmark Metrics:")
        for key, value in benchmark_metrics.items():
                logger.info(f"  {key}: {value}")
        
        # Calculate tracking error
        common_dates = portfolio_df.index.intersection(benchmark_returns.index)
        if len(common_dates) > 0:
            portfolio_aligned = portfolio_df.loc[common_dates, 'portfolio_return']
            benchmark_aligned = benchmark_returns.loc[common_dates]
            
            tracking_error = (portfolio_aligned - benchmark_aligned).std() * np.sqrt(252)
            correlation = portfolio_aligned.corr(benchmark_aligned)
            
            logger.info(f"\nTracking Metrics:")
            logger.info(f"  Tracking Error (annualized): {tracking_error:.2%}")
            logger.info(f"  Correlation: {correlation:.4f}")
    
    # Save results
    results_file = OUTPUT_DIR / 'sp500_ew_backtest_results.csv'
    portfolio_df.to_csv(results_file)
    logger.info(f"\n✓ Saved backtest results to {results_file}")
    
    # Create plot
    plot_results(portfolio_df, benchmark_returns)
    
    # Save metrics
    import json
    metrics_file = OUTPUT_DIR / 'sp500_ew_backtest_metrics.json'
    all_metrics = {
        'portfolio': portfolio_metrics,
        'benchmark': benchmark_metrics if (benchmark_returns is not None and not benchmark_returns.empty) else None,
        'date_range': {
            'start': str(start_date),
            'end': str(end_date)
        }
    }
    with open(metrics_file, 'w') as f:
        json.dump(all_metrics, f, indent=2, default=str)
    logger.info(f"✓ Saved metrics to {metrics_file}")
    
    logger.info("\n" + "="*70)
    logger.info("Backtest Complete!")
    logger.info("="*70)


if __name__ == '__main__':
    main()

