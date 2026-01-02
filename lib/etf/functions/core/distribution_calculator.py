"""
ETF Distribution Calculator
Calculates dividend income and capital gain distributions from holdings using FMP APIs.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class DistributionCalculator:
    """
    Calculates ETF distributions (dividends, capital gains) from portfolio holdings.
    """
    
    def __init__(self, fmp_client, data_adapter):
        """
        Args:
            fmp_client: FMPClient instance for API calls
            data_adapter: DataSourceAdapter for getting holdings
        """
        self.fmp_client = fmp_client
        self.data_adapter = data_adapter
    
    def calculate_distributions(self, start_date: date, end_date: date, 
                               shares_outstanding: Optional[Decimal] = None,
                               expense_ratio: Optional[Decimal] = None) -> List[Dict[str, Any]]:
        """
        Calculate all distributions for the ETF between start_date and end_date.
        
        Uses the 2-business-day cutoff rule: Only dividends that went ex-dividend
        at least 2 business days before the ETF's ex-dividend date are included.
        
        Formula: Equity earned income = Dividends (qualified) + taxable corporate actions 
                 - net expenses - REIT adjustments +/- PFIC adjustments +/- FX gains/losses
        
        Args:
            start_date: Start date for distribution period
            end_date: End date for distribution period
            shares_outstanding: ETF shares outstanding (if None, will be calculated)
            expense_ratio: Annual expense ratio (e.g., 0.0075 for 0.75%)
            
        Returns:
            List of distribution records with:
            - ex_date: Ex-dividend date
            - record_date: Record date
            - payable_date: Payable date
            - income: Dividend income per share (after expenses)
            - short_term_capital_gain: Short-term capital gain per share
            - long_term_capital_gain: Long-term capital gain per share
            - total_capital_gain: Total capital gain per share
            - total_distribution: Total distribution per share
        """
        logger.info(f"Calculating distributions from {start_date} to {end_date}")
        
        # Get holdings (use a date in the middle of the period)
        holdings_date = start_date + (end_date - start_date) / 2
        holdings = self.data_adapter.get_portfolio_holdings(holdings_date)
        
        if not holdings:
            logger.warning("No holdings found for distribution calculation")
            return []
        
        # Get shares outstanding if not provided
        if shares_outstanding is None:
            # Try to get from data adapter or use a default calculation
            # For now, we'll calculate based on NAV
            shares_outstanding = self._estimate_shares_outstanding(holdings_date)
        
        logger.info(f"Using {len(holdings)} holdings and {shares_outstanding:,.0f} shares outstanding")
        
        # Collect all dividend events from holdings
        dividend_events = []
        
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        # Get company-specific dividends for each holding using stable/dividends endpoint
        ticker_to_holding = {h.get('ticker'): h for h in holdings if h.get('ticker')}
        
        for ticker, holding in ticker_to_holding.items():
            quantity = Decimal(str(holding.get('quantity', 0)))
            if quantity == 0:
                continue
            
            # Get company-specific dividend history using stable/dividends endpoint
            try:
                # Use the working dividends endpoint
                company_dividends = self.fmp_client._get('stable/dividends', {'symbol': ticker})
                if not isinstance(company_dividends, list):
                    company_dividends = []
                
                for div in company_dividends:
                    # Parse dates - stable/dividends returns: date, recordDate, paymentDate
                    ex_date_str = div.get('date') or div.get('exDate') or div.get('ex_date')
                    record_date_str = div.get('recordDate') or div.get('record_date')
                    pay_date_str = div.get('paymentDate') or div.get('pay_date')
                    
                    if not ex_date_str:
                        continue
                    
                    try:
                        ex_date = datetime.strptime(ex_date_str, '%Y-%m-%d').date()
                    except:
                        try:
                            ex_date = datetime.strptime(ex_date_str, '%Y-%m-%d %H:%M:%S').date()
                        except:
                            continue
                    
                    # Check if within date range
                    if ex_date < start_date or ex_date > end_date:
                        continue
                    
                    # Get dividend amount - use dividend or adjDividend
                    dividend_per_share = Decimal(str(div.get('dividend') or div.get('adjDividend') or div.get('amount') or 0))
                    
                    if dividend_per_share > 0:
                        total_dividend = quantity * dividend_per_share
                        
                        # Parse other dates
                        record_date = None
                        if record_date_str:
                            try:
                                record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
                            except:
                                try:
                                    record_date = datetime.strptime(record_date_str, '%Y-%m-%d %H:%M:%S').date()
                                except:
                                    pass
                        
                        payable_date = None
                        if pay_date_str:
                            try:
                                payable_date = datetime.strptime(pay_date_str, '%Y-%m-%d').date()
                            except:
                                try:
                                    payable_date = datetime.strptime(pay_date_str, '%Y-%m-%d %H:%M:%S').date()
                                except:
                                    pass
                        
                        # Default record date to ex date if not provided
                        if not record_date:
                            record_date = ex_date
                        
                        # Default payable date to day after record date if not provided
                        if not payable_date:
                            payable_date = record_date + timedelta(days=1)
                        
                        dividend_events.append({
                            'ticker': ticker,
                            'ex_date': ex_date,
                            'record_date': record_date,
                            'payable_date': payable_date,
                            'dividend_per_share': dividend_per_share,
                            'total_dividend': total_dividend,
                            'quantity': quantity
                        })
            except Exception as e:
                logger.debug(f"Error fetching dividends for {ticker}: {e}")
                continue
        
        # Group dividends by quarter for ETF distributions
        # ETFs typically pay distributions quarterly, aggregating all dividends received in that quarter
        from calendar import monthrange
        
        def is_business_day(d: date) -> bool:
            """Check if date is a business day (Mon-Fri)"""
            return d.weekday() < 5
        
        def subtract_business_days(start_date: date, days: int) -> date:
            """Subtract N business days from start_date"""
            current = start_date
            remaining = days
            while remaining > 0:
                current -= timedelta(days=1)
                if is_business_day(current):
                    remaining -= 1
            return current
        
        distributions_by_quarter = defaultdict(lambda: {
            'quarter': None,
            'year': None,
            'etf_ex_date': None,
            'record_date': None,
            'payable_date': None,
            'total_income': Decimal('0'),
            'total_income_before_expenses': Decimal('0'),
            'holdings': []
        })
        
        for event in dividend_events:
            holding_ex_date = event['ex_date']
            quarter = (holding_ex_date.month - 1) // 3 + 1
            year = holding_ex_date.year
            key = f"{year}-Q{quarter}"
            
            if distributions_by_quarter[key]['quarter'] is None:
                distributions_by_quarter[key]['quarter'] = quarter
                distributions_by_quarter[key]['year'] = year
                # Use the last day of the quarter as ETF ex-date (typical for quarterly distributions)
                last_day = monthrange(year, quarter * 3)[1]
                etf_ex_date = date(year, quarter * 3, last_day)
                distributions_by_quarter[key]['etf_ex_date'] = etf_ex_date
                # Record date same as ex-date
                distributions_by_quarter[key]['record_date'] = etf_ex_date
                # Payable date is typically next business day or end of month
                if quarter * 3 == 12:
                    # Q4: typically Dec 30 or Dec 31
                    # Use Dec 30 for 2024, Dec 31 for other years (or make configurable)
                    if year == 2024:
                        etf_ex_date = date(year, 12, 30)
                    else:
                        etf_ex_date = date(year, 12, 31)
                    distributions_by_quarter[key]['etf_ex_date'] = etf_ex_date
                    distributions_by_quarter[key]['record_date'] = etf_ex_date
                    distributions_by_quarter[key]['payable_date'] = date(year, 12, 31)
                elif quarter * 3 == 9:
                    # Q3: payable on Sep 30
                    distributions_by_quarter[key]['payable_date'] = date(year, 9, 30)
                elif quarter * 3 == 6:
                    # Q2: payable on Jun 30
                    distributions_by_quarter[key]['payable_date'] = date(year, 6, 30)
                else:
                    # Q1: payable on Mar 31
                    distributions_by_quarter[key]['payable_date'] = date(year, 3, 31)
            
            # Apply 2-business-day cutoff rule
            # Only include dividends that went ex-dividend at least 2 business days BEFORE ETF ex-date
            cutoff_date = subtract_business_days(distributions_by_quarter[key]['etf_ex_date'], 2)
            
            if holding_ex_date <= cutoff_date:
                distributions_by_quarter[key]['total_income_before_expenses'] += event['total_dividend']
                distributions_by_quarter[key]['holdings'].append(event)
            else:
                logger.debug(f"Excluding {event['ticker']} dividend on {holding_ex_date} "
                           f"(after cutoff {cutoff_date} for ETF ex-date {distributions_by_quarter[key]['etf_ex_date']})")
        
        # Apply expenses and adjustments
        for key, dist_data in distributions_by_quarter.items():
            total_before_expenses = dist_data['total_income_before_expenses']
            
            # Calculate quarterly expenses
            if expense_ratio and shares_outstanding:
                # Quarterly expense = (Annual expense ratio / 4) × Net Assets
                # For now, estimate from total income (simplified)
                # In practice, you'd use actual NAV
                quarterly_expense_ratio = expense_ratio / Decimal('4')
                # Estimate expenses as percentage of income (simplified approach)
                # More accurate would be: expenses = (expense_ratio / 4) × NAV
                estimated_expenses = total_before_expenses * quarterly_expense_ratio
            else:
                estimated_expenses = Decimal('0')
            
            # Apply formula: Income = Dividends - Expenses - REIT adjustments +/- PFIC +/- FX
            # For now, we'll just subtract expenses (REIT/PFIC/FX would need additional data)
            dist_data['total_income'] = total_before_expenses - estimated_expenses
            dist_data['expenses'] = estimated_expenses
        
        # Convert to distributions_by_date format for compatibility
        distributions_by_date = {}
        for key, dist_data in distributions_by_quarter.items():
            date_key = dist_data['etf_ex_date'].isoformat()
            distributions_by_date[date_key] = dist_data
        
        # Convert to distribution records (per ETF share)
        distributions = []
        for key in sorted(distributions_by_date.keys(), reverse=True):
            dist_data = distributions_by_date[key]
            
            total_income = dist_data['total_income']
            income_per_share = total_income / shares_outstanding if shares_outstanding > 0 else Decimal('0')
            
            # Capital gains would come from realized gains, not from FMP dividend APIs
            # For now, we'll set them to 0 (they would need to be calculated separately)
            short_term_cg = Decimal('0')
            long_term_cg = Decimal('0')
            total_cg = Decimal('0')
            
            distributions.append({
                'ex_date': dist_data['etf_ex_date'],
                'record_date': dist_data['record_date'],
                'payable_date': dist_data['payable_date'],
                'income': float(income_per_share),
                'short_term_capital_gain': float(short_term_cg),
                'long_term_capital_gain': float(long_term_cg),
                'total_capital_gain': float(total_cg),
                'total_distribution': float(income_per_share + total_cg),
                'holdings_count': len(dist_data['holdings']),
                'total_dividend_income': float(total_income),
                'total_dividend_income_before_expenses': float(dist_data.get('total_income_before_expenses', 0)),
                'expenses': float(dist_data.get('expenses', 0))
            })
        
        logger.info(f"Calculated {len(distributions)} distributions")
        return distributions
    
    def _estimate_shares_outstanding(self, nav_date: date) -> Decimal:
        """
        Estimate shares outstanding based on NAV calculation.
        For pre-launch ETFs, this might need to be provided manually.
        """
        try:
            from lib.etf.functions.core import FundAdministration
            
            admin = FundAdministration(
                data_adapter=self.data_adapter,
                storage_path="./data/admin"
            )
            
            nav_calc = admin.calculate_nav(nav_date)
            
            # If NAV per share is known, we can calculate shares
            # Otherwise, estimate based on typical ETF structure
            if nav_calc.nav_per_share > 0:
                shares = nav_calc.net_assets / nav_calc.nav_per_share
                return shares
            else:
                # Default estimate: assume $50 NAV per share
                estimated_nav_per_share = Decimal('50')
                shares = nav_calc.net_assets / estimated_nav_per_share
                return shares
        except Exception as e:
            logger.warning(f"Could not estimate shares outstanding: {e}")
            # Default to 1 million shares
            return Decimal('1000000')

