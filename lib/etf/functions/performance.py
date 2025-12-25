"""
Production-Ready Performance Calculation Function
Complete implementation for pre-tax and post-tax performance tracking

This module tracks the fund's NAV history and computes performance metrics, including
pre-tax and post-tax returns, and compares the fund's returns to a benchmark.

Pre-tax total return assumes all distributions are reinvested in the fund without taxes.
Post-tax total return measures the return after investors pay taxes on distributions
(and on any capital gain from selling the fund shares), giving a more realistic outcome
for a taxable investor. The difference highlights the fund's tax efficiency.

References:
- Investopedia: Total Return, After-Tax Return
- SEC: Performance Reporting Requirements
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from pathlib import Path
import json
import pandas as pd

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("yfinance not available - benchmark comparison will be limited")

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    Production-ready Performance Calculator implementation.
    
    Computes pre-tax and after-tax total returns for the fund over any period,
    and compares to a benchmark's total return.
    
    Example:
        >>> calc = PerformanceCalculator(storage_path="./data/performance")
        >>> result = calc.compute_performance(
        ...     nav_history_path="nav_history.csv",
        ...     dist_history_path="distributions.csv",
        ...     benchmark_symbol="^GSPC",
        ...     tax_rates={"dividend_tax_rate": 0.15, "lt_capital_gains_tax_rate": 0.20},
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 12, 31)
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/performance"):
        """
        Initialize Performance Calculator.
        
        Args:
            storage_path: Path for storing performance data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def compute_performance(self, nav_history_path: str, dist_history_path: Optional[str],
                          benchmark_symbol: Optional[str], tax_rates: Dict[str, float],
                          start_date: Optional[date] = None, end_date: Optional[date] = None,
                          output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute pre-tax and after-tax total returns for the fund over the period.
        
        Args:
            nav_history_path: Path to CSV file with NAV history (columns: date, nav)
            dist_history_path: Optional path to CSV file with distribution history
            benchmark_symbol: Optional benchmark symbol (e.g., "^GSPC" for S&P 500)
            tax_rates: Dictionary with tax rates:
                - dividend_tax_rate: Tax rate on ordinary dividends (default 0.15)
                - lt_capital_gains_tax_rate: Tax rate on long-term capital gains (default 0.20)
                - st_capital_gains_tax_rate: Tax rate on short-term gains (default 0.37)
            start_date: Optional start date (defaults to first NAV date)
            end_date: Optional end date (defaults to last NAV date)
            output_path: Optional path to save results JSON
            
        Returns:
            Dictionary with performance metrics
        """
        logger.info("Computing fund performance metrics")
        
        # Load NAV history
        try:
            nav_df = pd.read_csv(nav_history_path, parse_dates=['date'])
        except Exception as e:
            logger.error(f"Error loading NAV history: {e}")
            raise
        
        # Load distribution history if provided
        dist_df = None
        if dist_history_path:
            try:
                dist_df = pd.read_csv(dist_history_path, parse_dates=['date'])
            except FileNotFoundError:
                logger.warning(f"Distribution history file not found: {dist_history_path}")
                dist_df = pd.DataFrame(columns=['date', 'distribution_per_share'])
            except Exception as e:
                logger.warning(f"Error loading distribution history: {e}")
                dist_df = pd.DataFrame(columns=['date', 'distribution_per_share'])
        else:
            dist_df = pd.DataFrame(columns=['date', 'distribution_per_share'])
        
        # Sort and filter by date range
        nav_df.sort_values('date', inplace=True)
        if dist_df is not None and not dist_df.empty:
            dist_df.sort_values('date', inplace=True)
        
        if start_date:
            nav_df = nav_df[nav_df['date'] >= pd.Timestamp(start_date)]
            if dist_df is not None and not dist_df.empty:
                dist_df = dist_df[dist_df['date'] >= pd.Timestamp(start_date)]
        
        if end_date:
            nav_df = nav_df[nav_df['date'] <= pd.Timestamp(end_date)]
            if dist_df is not None and not dist_df.empty:
                dist_df = dist_df[dist_df['date'] <= pd.Timestamp(end_date)]
        
        if nav_df.empty:
            raise ValueError("No NAV data available for the specified period")
        
        start_nav = Decimal(str(nav_df['nav'].iloc[0]))
        end_nav = Decimal(str(nav_df['nav'].iloc[-1]))
        start_date_actual = nav_df['date'].iloc[0].date()
        end_date_actual = nav_df['date'].iloc[-1].date()
        
        # Calculate total growth factor for fund pre-tax and after-tax
        pre_tax_index = Decimal('1.0')
        after_tax_index = Decimal('1.0')
        
        # Merge NAV and distribution data for iteration
        data = pd.merge(nav_df, dist_df, on='date', how='left')
        data.fillna({'distribution_per_share': 0.0}, inplace=True)
        data.sort_values('date', inplace=True)
        
        prev_nav = start_nav
        
        for i in range(1, len(data)):
            prev_row = data.iloc[i-1]
            curr_row = data.iloc[i]
            
            nav_prev = Decimal(str(prev_row['nav']))
            nav_curr = Decimal(str(curr_row['nav']))
            dist = Decimal(str(curr_row.get('distribution_per_share', 0.0)))
            
            # Pre-tax growth: if distribution occurred, treat it as reinvested
            # Total value at end of period = NAV_curr + dist (because dist was reinvested)
            if nav_prev > 0:
                growth_factor = (nav_curr + dist) / nav_prev
                pre_tax_index *= growth_factor
                
                # After-tax growth: assume distribution is taxed and only remainder reinvested
                if dist > 0:
                    # Assume all distributions are from ordinary income for tax calculation
                    # (In a more detailed model, we'd track distribution composition)
                    tax_rate = Decimal(str(tax_rates.get('dividend_tax_rate', 0.15)))
                    after_tax_dist = dist * (Decimal('1.0') - tax_rate)
                else:
                    after_tax_dist = Decimal('0')
                
                after_tax_growth_factor = (nav_curr + after_tax_dist) / nav_prev
                after_tax_index *= after_tax_growth_factor
            
            prev_nav = nav_curr
        
        pre_tax_return = float(pre_tax_index - Decimal('1.0'))
        after_tax_return = float(after_tax_index - Decimal('1.0'))
        
        # Include tax on final sale for after-tax return
        # The investor sells at end_date, any gain from initial to final NAV is taxed
        overall_gain = end_nav - start_nav
        if overall_gain > 0 and start_nav > 0:
            # Assume long-term for full period
            sell_tax_rate = Decimal(str(tax_rates.get('lt_capital_gains_tax_rate', 0.20)))
            gain_ratio = overall_gain / start_nav
            after_tax_return = float((Decimal('1.0') + Decimal(str(after_tax_return))) * 
                                     (Decimal('1.0') - sell_tax_rate * Decimal(str(gain_ratio))) - Decimal('1.0'))
        
        # Compute benchmark total return for same period (pre-tax)
        bench_return = None
        bench_data = None
        
        if benchmark_symbol and YFINANCE_AVAILABLE:
            try:
                bench_ticker = yf.Ticker(benchmark_symbol)
                hist = bench_ticker.history(
                    start=start_date_actual,
                    end=end_date_actual + timedelta(days=1),
                    actions=True
                )
                
                if not hist.empty:
                    # Compute total return for benchmark
                    hist = hist.rename_axis('Date').reset_index()
                    hist.sort_values('Date', inplace=True)
                    
                    bench_index = Decimal('1.0')
                    first_price = Decimal(str(hist['Close'].iloc[0]))
                    prev_price = first_price
                    
                    for j in range(1, len(hist)):
                        prev_row = hist.iloc[j-1]
                        curr_row = hist.iloc[j]
                        
                        price_prev = Decimal(str(prev_row['Close']))
                        price_curr = Decimal(str(curr_row['Close']))
                        
                        # Check if a dividend occurred
                        div = Decimal('0')
                        if 'Dividends' in curr_row and pd.notna(curr_row['Dividends']):
                            div = Decimal(str(curr_row['Dividends']))
                        
                        # Compute growth factor including reinvested dividend
                        if price_prev > 0:
                            gf = (price_curr + div) / price_prev
                            bench_index *= gf
                        
                        prev_price = price_curr
                    
                    bench_return = float(bench_index - Decimal('1.0'))
                    bench_data = {
                        "symbol": benchmark_symbol,
                        "start_price": float(first_price),
                        "end_price": float(prev_price),
                        "total_return": bench_return
                    }
            except Exception as e:
                logger.warning(f"Error fetching benchmark data: {e}")
        
        result = {
            "start_date": start_date_actual.isoformat(),
            "end_date": end_date_actual.isoformat(),
            "start_nav": float(start_nav),
            "end_nav": float(end_nav),
            "pre_tax_total_return": pre_tax_return,
            "after_tax_total_return": after_tax_return,
            "tax_drag": pre_tax_return - after_tax_return,
            "tax_efficiency_ratio": after_tax_return / pre_tax_return if pre_tax_return != 0 else 0,
            "benchmark": bench_data,
            "fund_vs_benchmark": bench_return - pre_tax_return if bench_return is not None else None
        }
        
        # Save results to JSON
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    json.dump(result, f, indent=4)
                logger.info(f"Performance results saved to {output_path}")
            except Exception as e:
                logger.error(f"Could not save performance output: {e}")
        else:
            # Save to default location
            output_file = self.storage_path / f"performance_{start_date_actual}_{end_date_actual}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=4)
        
        logger.info(f"Performance calculated: Pre-tax={pre_tax_return:.2%}, After-tax={after_tax_return:.2%}")
        return result
    
    def calculate_annual_returns(self, nav_history_path: str, 
                                 dist_history_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate annual returns for each calendar year.
        
        Args:
            nav_history_path: Path to NAV history CSV
            dist_history_path: Optional path to distribution history CSV
            
        Returns:
            Dictionary with annual returns by year
        """
        try:
            nav_df = pd.read_csv(nav_history_path, parse_dates=['date'])
            nav_df.sort_values('date', inplace=True)
            
            annual_returns = {}
            years = nav_df['date'].dt.year.unique()
            
            for year in sorted(years):
                year_data = nav_df[nav_df['date'].dt.year == year]
                if len(year_data) > 1:
                    start_nav = Decimal(str(year_data['nav'].iloc[0]))
                    end_nav = Decimal(str(year_data['nav'].iloc[-1]))
                    
                    # Get distributions for this year
                    total_dist = Decimal('0')
                    if dist_history_path:
                        try:
                            dist_df = pd.read_csv(dist_history_path, parse_dates=['date'])
                            year_dists = dist_df[dist_df['date'].dt.year == year]
                            total_dist = Decimal(str(year_dists['distribution_per_share'].sum()))
                        except:
                            pass
                    
                    if start_nav > 0:
                        annual_return = float((end_nav + total_dist - start_nav) / start_nav)
                        annual_returns[str(year)] = annual_return
            
            return {
                "annual_returns": annual_returns,
                "years": list(annual_returns.keys())
            }
        except Exception as e:
            logger.error(f"Error calculating annual returns: {e}")
            return {"annual_returns": {}, "years": []}

