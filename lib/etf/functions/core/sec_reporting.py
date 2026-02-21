"""
SEC Form N-1A Reporting Functions
Calculates standardized yield and performance metrics per SEC requirements.

This module implements all calculations required by Form N-1A:
- Item 13: Financial Highlights (portfolio turnover, expense ratios, net income ratios)
- Item 26: Performance Data (total returns, after-tax returns, 30-day yield)
- Item 27A: Shareholder Report calculations (expenses table, performance graph data)
"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from calendar import monthrange

logger = logging.getLogger(__name__)

# Federal tax rates (highest marginal rates per N-1A Instruction 4 to Item 26(b)(2))
# These are the rates used for after-tax return calculations
FEDERAL_TAX_RATES = {
    'ordinary_income': Decimal('0.37'),  # 37% for 2023-2024
    'qualified_dividend': Decimal('0.20'),  # 20% for qualified dividends
    'short_term_capital_gain': Decimal('0.37'),  # Same as ordinary income
    'long_term_capital_gain': Decimal('0.20'),  # 20% for long-term gains
    'net_investment_income_tax': Decimal('0.038')  # 3.8% NIIT on investment income
}


class SECReporting:
    """
    SEC Form N-1A reporting calculations.
    
    Per SEC instructions, Net Investment Income (NII) = 
    (Dividends + Interest Earned - Expenses Accrued) / Average Shares Outstanding
    
    All calculations follow the exact formulas specified in Form N-1A instructions.
    
    Note: Sales loads are optional parameters (default to 0) since ETFs typically
    don't have sales loads. They're included for mutual fund compatibility per N-1A.
    """
    
    def __init__(self, storage_path: str = "./data/admin", distribution_data_path: Optional[str] = None,
                 accounting: Optional[Any] = None):
        """
        Initialize SEC Reporting.
        
        Args:
            storage_path: Path to NAV and accounting data
            distribution_data_path: Optional path to distribution data (for after-tax calculations)
            accounting: Optional Accounting instance for transaction data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.distribution_data_path = Path(distribution_data_path) if distribution_data_path else None
        self.accounting = accounting  # For accessing transaction records
    
    def calculate_average_shares_outstanding(self, period_start: date, period_end: date) -> Decimal:
        """
        Calculate average shares outstanding for a period.
        
        SEC Form N-1A Instruction 4(a) to Item 13: Calculate "average net assets" 
        based on the value of the net assets determined no less frequently than 
        the end of each month.
        
        Args:
            period_start: Start date of period
            period_end: End date of period
            
        Returns:
            Average shares outstanding for the period
        """
        logger.info(f"Calculating average shares outstanding from {period_start} to {period_end}")
        
        nav_data = self._load_nav_data(period_start, period_end)
        
        if not nav_data:
            logger.warning("No NAV data found for period")
            return Decimal('0')
        
        # Per N-1A Instruction 4(a), use monthly values
        # Group by month and get month-end values
        monthly_shares = {}
        for nav in nav_data:
            nav_date = date.fromisoformat(nav.get('date', ''))
            month_key = (nav_date.year, nav_date.month)
            
            # Keep the last value for each month (month-end)
            if month_key not in monthly_shares or nav_date > date.fromisoformat(monthly_shares[month_key].get('date', '1900-01-01')):
                monthly_shares[month_key] = nav
        
        if not monthly_shares:
            return Decimal('0')
        
        # Calculate average from monthly values
        total_shares = Decimal('0')
        for nav in monthly_shares.values():
            shares = Decimal(str(nav.get('shares_outstanding', 0)))
            if shares > 0:
                total_shares += shares
        
        avg_shares = total_shares / Decimal(str(len(monthly_shares)))
        logger.info(f"Average shares outstanding: {avg_shares:,.0f} (from {len(monthly_shares)} months)")
        
        return avg_shares.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_average_net_assets(self, period_start: date, period_end: date) -> Decimal:
        """
        Calculate average net assets for a period.
        
        SEC Form N-1A Instruction 4(a) to Item 13: Calculate "average net assets" 
        based on the value of the net assets determined no less frequently than 
        the end of each month.
        
        Args:
            period_start: Start date of period
            period_end: End date of period
            
        Returns:
            Average net assets for the period
        """
        logger.info(f"Calculating average net assets from {period_start} to {period_end}")
        
        nav_data = self._load_nav_data(period_start, period_end)
        
        if not nav_data:
            logger.warning("No NAV data found for period")
            return Decimal('0')
        
        # Per N-1A Instruction 4(a), use monthly values
        monthly_net_assets = {}
        for nav in nav_data:
            nav_date = date.fromisoformat(nav.get('date', ''))
            month_key = (nav_date.year, nav_date.month)
            
            # Keep the last value for each month (month-end)
            if month_key not in monthly_net_assets or nav_date > date.fromisoformat(monthly_net_assets[month_key].get('date', '1900-01-01')):
                monthly_net_assets[month_key] = nav
        
        if not monthly_net_assets:
            return Decimal('0')
        
        # Calculate average from monthly values
        total_net_assets = Decimal('0')
        for nav in monthly_net_assets.values():
            net_assets = Decimal(str(nav.get('net_assets', 0)))
            if net_assets > 0:
                total_net_assets += net_assets
        
        avg_net_assets = total_net_assets / Decimal(str(len(monthly_net_assets)))
        logger.info(f"Average net assets: ${avg_net_assets:,.2f} (from {len(monthly_net_assets)} months)")
        
        return avg_net_assets.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def calculate_portfolio_turnover_rate(self, fiscal_year_start: date, fiscal_year_end: date,
                                         purchases: Optional[Decimal] = None,
                                         sales: Optional[Decimal] = None) -> Decimal:
        """
        Calculate portfolio turnover rate per SEC Form N-1A Instruction 4(d) to Item 13.
        
        Formula: Divide the lesser of amounts of purchases or sales of portfolio securities 
        for the fiscal year by the monthly average of the value of the portfolio securities 
        owned by the Fund during the fiscal year.
        
        Calculate the monthly average by totaling the values of portfolio securities as of 
        the beginning and end of the first month of the fiscal year and as of the end of 
        each of the succeeding 11 months and dividing the sum by 13.
        
        Args:
            fiscal_year_start: Start date of fiscal year
            fiscal_year_end: End date of fiscal year
            purchases: Optional total purchases for the year (if None, will attempt to estimate)
            sales: Optional total sales for the year (if None, will attempt to estimate)
            
        Returns:
            Portfolio turnover rate as a percentage
        """
        logger.info(f"Calculating portfolio turnover rate for fiscal year {fiscal_year_start} to {fiscal_year_end}")
        
        # Load NAV data for the fiscal year
        nav_data = self._load_nav_data(fiscal_year_start, fiscal_year_end)
        
        if not nav_data:
            logger.warning("No NAV data found for fiscal year")
            return Decimal('0')
        
        # Calculate monthly average portfolio value per Instruction 4(d)(ii)
        # Need values at: beginning of first month, end of first month, end of months 2-12
        monthly_portfolio_values = []
        
        # Get beginning of first month
        first_month_start = date(fiscal_year_start.year, fiscal_year_start.month, 1)
        nav_start = self._get_nav_for_date(first_month_start, nav_data)
        if nav_start:
            portfolio_value = Decimal(str(nav_start.get('total_securities_value', nav_start.get('total_assets', 0))))
            monthly_portfolio_values.append(portfolio_value)
        
        # Get end of each month
        current_date = first_month_start
        while current_date <= fiscal_year_end:
            # Get last day of current month
            last_day = monthrange(current_date.year, current_date.month)[1]
            month_end = date(current_date.year, current_date.month, last_day)
            if month_end > fiscal_year_end:
                month_end = fiscal_year_end
            
            nav_month_end = self._get_nav_for_date(month_end, nav_data)
            if nav_month_end:
                portfolio_value = Decimal(str(nav_month_end.get('total_securities_value', nav_month_end.get('total_assets', 0))))
                monthly_portfolio_values.append(portfolio_value)
            
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        if len(monthly_portfolio_values) < 2:
            logger.warning("Insufficient data for portfolio turnover calculation")
            return Decimal('0')
        
        # Calculate monthly average per Instruction 4(d)(ii)
        total_portfolio_value = sum(monthly_portfolio_values)
        monthly_avg_portfolio = total_portfolio_value / Decimal(str(len(monthly_portfolio_values)))
        
        # Get purchases/sales from parameters or extract from accounting
        if purchases is None or sales is None:
            # Try to extract from accounting ledger if available
            if self.accounting:
                transaction_data = self._get_transaction_totals(fiscal_year_start, fiscal_year_end)
                purchases = transaction_data.get('purchases', Decimal('0')) if purchases is None else purchases
                sales = transaction_data.get('sales', Decimal('0')) if sales is None else sales
            else:
                logger.warning("Purchase/sale data not provided and no accounting system available. Using placeholder.")
                purchases = Decimal('0')
                sales = Decimal('0')
        
        # Per Instruction 4(d)(i), use the lesser of purchases or sales
        turnover_amount = min(purchases, sales) if purchases > 0 and sales > 0 else Decimal('0')
        
        if monthly_avg_portfolio == 0:
            return Decimal('0')
        
        turnover_rate = (turnover_amount / monthly_avg_portfolio) * Decimal('100')
        
        logger.info(f"Portfolio turnover rate: {turnover_rate:.2f}%")
        
        return turnover_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _get_nav_for_date(self, target_date: date, nav_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get NAV data for a specific date, or closest available date"""
        target_date_str = target_date.isoformat()
        
        # First try exact match
        for nav in nav_data:
            if nav.get('date') == target_date_str:
                return nav
        
        # If no exact match, find closest date
        closest_nav = None
        min_diff = None
        
        for nav in nav_data:
            nav_date_str = nav.get('date', '')
            if nav_date_str:
                try:
                    nav_date = date.fromisoformat(nav_date_str)
                    diff = abs((nav_date - target_date).days)
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_nav = nav
                except:
                    continue
        
        return closest_nav
    
    def _get_transaction_totals(self, period_start: date, period_end: date) -> Dict[str, Decimal]:
        """
        Extract purchase and sale totals from accounting ledger.
        
        Looks for entries in account 1100 (Investments - Securities) that represent
        purchases (debits) and sales (credits) during the period.
        
        Args:
            period_start: Start date of period
            period_end: End date of period
            
        Returns:
            Dictionary with 'purchases' and 'sales' totals
        """
        purchases = Decimal('0')
        sales = Decimal('0')
        
        if not self.accounting:
            return {'purchases': purchases, 'sales': sales}
        
        try:
            ledger = self.accounting.get_ledger()
            investments_account = None
            
            # Find Investments - Securities account (1100)
            for account in ledger.accounts:
                if account.account_code == '1100':
                    investments_account = account
                    break
            
            if not investments_account:
                logger.warning("Investments account (1100) not found in ledger")
                return {'purchases': purchases, 'sales': sales}
            
            # Sum debits (purchases) and credits (sales) for the period
            for entry in investments_account.entries:
                entry_date = entry.date if isinstance(entry.date, date) else date.fromisoformat(entry.date)
                
                if period_start <= entry_date <= period_end:
                    # Debits represent purchases (buying securities)
                    if entry.debit > 0:
                        purchases += entry.debit
                    # Credits represent sales (selling securities)
                    if entry.credit > 0:
                        sales += entry.credit
            
            logger.info(f"Extracted transactions: Purchases=${purchases:,.2f}, Sales=${sales:,.2f}")
            
        except Exception as e:
            logger.warning(f"Error extracting transaction totals: {e}")
        
        return {'purchases': purchases, 'sales': sales}
    
    def _load_distribution_data(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Load distribution data for date range with enhanced tax character tracking.
        
        Tracks distribution tax character (ordinary income, short-term/long-term capital gains)
        for accurate after-tax calculations.
        """
        distributions = []
        
        # Try to load from distribution_data_path if provided
        if self.distribution_data_path and self.distribution_data_path.exists():
            dist_file = self.distribution_data_path / "distributions.json"
            if dist_file.exists():
                try:
                    with open(dist_file, 'r') as f:
                        dist_data = json.load(f)
                        for dist in dist_data.get('distributions', []):
                            ex_date = date.fromisoformat(dist.get('ex_date', ''))
                            if start_date <= ex_date <= end_date:
                                # Ensure tax character fields are present
                                dist.setdefault('income', 0)
                                dist.setdefault('short_term_capital_gain', 0)
                                dist.setdefault('long_term_capital_gain', 0)
                                distributions.append(dist)
                except Exception as e:
                    logger.warning(f"Error loading distribution data: {e}")
        
        # Also try loading from admin storage path
        current_date = start_date
        while current_date <= end_date:
            dist_file = self.storage_path / f"distribution_{current_date.isoformat()}.json"
            if dist_file.exists():
                try:
                    with open(dist_file, 'r') as f:
                        dist = json.load(f)
                        # Ensure tax character fields
                        dist.setdefault('income', 0)
                        dist.setdefault('short_term_capital_gain', 0)
                        dist.setdefault('long_term_capital_gain', 0)
                        distributions.append(dist)
                except Exception as e:
                    logger.warning(f"Error loading distribution file {dist_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return distributions
    
    def calculate_expense_ratio(self, fiscal_year_start: date, fiscal_year_end: date) -> Dict[str, Any]:
        """
        Calculate expense ratio per SEC Form N-1A Instruction 4(b) to Item 13.
        
        Ratio of Expenses to Average Net Assets using the amount of expenses shown 
        in the Fund's statement of operations for the relevant fiscal period, including 
        increases resulting from complying with paragraph 2(g) of rule 6-07 of Regulation 
        S-X and reductions resulting from complying with paragraphs 2(a) and (f) of rule 
        6-07 regarding fee waivers and reimbursements.
        
        Args:
            fiscal_year_start: Start date of fiscal year
            fiscal_year_end: End date of fiscal year
            
        Returns:
            Dictionary with expense ratio and related data
        """
        logger.info(f"Calculating expense ratio for fiscal year {fiscal_year_start} to {fiscal_year_end}")
        
        nav_data = self._load_nav_data(fiscal_year_start, fiscal_year_end)
        
        if not nav_data:
            return {
                "status": "error",
                "error": "No NAV data found for fiscal year"
            }
        
        # Sum expenses for the fiscal year
        # Per Regulation S-X rule 6-07, include:
        # - Increases from paragraph 2(g) (brokerage service arrangements)
        # - Reductions from paragraphs 2(a) and (f) (fee waivers/reimbursements)
        total_expenses = Decimal('0')
        fee_waivers = Decimal('0')
        brokerage_service_adjustments = Decimal('0')
        
        for nav in nav_data:
            accrued_expenses = Decimal(str(nav.get('accrued_expenses', 0)))
            total_expenses += accrued_expenses
            
            # Add brokerage service arrangement increases (rule 6-07 paragraph 2(g))
            # These represent expenses that would have been incurred if services weren't provided via brokerage
            brokerage_adj = Decimal(str(nav.get('brokerage_service_adjustment', 0)))
            if brokerage_adj > 0:
                brokerage_service_adjustments += brokerage_adj
                total_expenses += brokerage_adj
            
            # Subtract fee waivers/reimbursements (rule 6-07 paragraphs 2(a) and (f))
            fee_waiver = Decimal(str(nav.get('fee_waiver', 0)))
            if fee_waiver > 0:
                fee_waivers += fee_waiver
                total_expenses -= fee_waiver  # Expenses are net of waivers per rule 6-07
        
        # Calculate average net assets
        avg_net_assets = self.calculate_average_net_assets(fiscal_year_start, fiscal_year_end)
        
        if avg_net_assets == 0:
            return {
                "status": "error",
                "error": "Average net assets is zero"
            }
        
        # Calculate expense ratio
        expense_ratio = (total_expenses / avg_net_assets) * Decimal('100')
        
        result = {
            "fiscal_year_start": fiscal_year_start.isoformat(),
            "fiscal_year_end": fiscal_year_end.isoformat(),
            "total_expenses": str(total_expenses),
            "fee_waivers": str(fee_waivers),
            "brokerage_service_adjustments": str(brokerage_service_adjustments),
            "average_net_assets": str(avg_net_assets),
            "expense_ratio": str(expense_ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"Expense ratio: {expense_ratio:.2f}%")
        
        return result
    
    def calculate_net_income_ratio(self, fiscal_year_start: date, fiscal_year_end: date) -> Dict[str, Any]:
        """
        Calculate ratio of net income to average net assets per SEC Form N-1A Item 13.
        
        Args:
            fiscal_year_start: Start date of fiscal year
            fiscal_year_end: End date of fiscal year
            
        Returns:
            Dictionary with net income ratio and related data
        """
        logger.info(f"Calculating net income ratio for fiscal year {fiscal_year_start} to {fiscal_year_end}")
        
        nav_data = self._load_nav_data(fiscal_year_start, fiscal_year_end)
        
        if not nav_data:
            return {
                "status": "error",
                "error": "No NAV data found for fiscal year"
            }
        
        # Sum income and expenses for the fiscal year
        total_income = Decimal('0')
        total_expenses = Decimal('0')
        
        for nav in nav_data:
            accrued_income = Decimal(str(nav.get('accrued_income', 0)))
            total_income += accrued_income
            
            accrued_expenses = Decimal(str(nav.get('accrued_expenses', 0)))
            total_expenses += accrued_expenses
        
        net_income = total_income - total_expenses
        
        # Calculate average net assets
        avg_net_assets = self.calculate_average_net_assets(fiscal_year_start, fiscal_year_end)
        
        if avg_net_assets == 0:
            return {
                "status": "error",
                "error": "Average net assets is zero"
            }
        
        # Calculate net income ratio
        net_income_ratio = (net_income / avg_net_assets) * Decimal('100')
        
        result = {
            "fiscal_year_start": fiscal_year_start.isoformat(),
            "fiscal_year_end": fiscal_year_end.isoformat(),
            "total_income": str(total_income),
            "total_expenses": str(total_expenses),
            "net_income": str(net_income),
            "average_net_assets": str(avg_net_assets),
            "net_income_ratio": str(net_income_ratio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"Net income ratio: {net_income_ratio:.2f}%")
        
        return result
    
    def calculate_net_investment_income(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """
        Calculate Net Investment Income (NII) per SEC Form N-1A requirements.
        
        Formula: NII = (Dividends + Interest Earned - Expenses Accrued) / Average Shares Outstanding
        
        Args:
            period_start: Start date of period
            period_end: End date of period
            
        Returns:
            Dictionary with NII calculation results
        """
        logger.info(f"Calculating NII for period {period_start} to {period_end}")
        
        nav_data = self._load_nav_data(period_start, period_end)
        
        if not nav_data:
            return {
                "status": "error",
                "error": "No NAV data found for period"
            }
        
        # Calculate totals from daily NAV files
        total_dividends = Decimal('0')
        total_interest = Decimal('0')
        total_expenses = Decimal('0')
        
        for nav in nav_data:
            # Accrued income includes dividends and interest
            accrued_income = Decimal(str(nav.get('accrued_income', 0)))
            # For now, assume all accrued income is dividends (can be refined)
            total_dividends += accrued_income
            
            # Expenses
            accrued_expenses = Decimal(str(nav.get('accrued_expenses', 0)))
            total_expenses += accrued_expenses
        
        # Calculate average shares outstanding (monthly basis per N-1A)
        avg_shares = self.calculate_average_shares_outstanding(period_start, period_end)
        
        if avg_shares == 0:
            return {
                "status": "error",
                "error": "Average shares outstanding is zero"
            }
        
        # Calculate NII
        net_investment_income = total_dividends + total_interest - total_expenses
        
        # Calculate per-share NII
        nii_per_share = net_investment_income / avg_shares if avg_shares > 0 else Decimal('0')
        
        # Calculate annualized yield
        days_in_period = (period_end - period_start).days + 1
        if days_in_period > 0:
            annualized_nii = nii_per_share * (Decimal('365') / Decimal(str(days_in_period)))
            # Get average NAV per share for yield calculation
            avg_nav = sum(Decimal(str(n.get('nav_per_share', 0))) for n in nav_data) / len(nav_data)
            if avg_nav > 0:
                annualized_yield = (annualized_nii / avg_nav) * Decimal('100')
            else:
                annualized_yield = Decimal('0')
        else:
            annualized_yield = Decimal('0')
        
        result = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "days_in_period": days_in_period,
            "total_dividends": str(total_dividends),
            "total_interest": str(total_interest),
            "total_expenses": str(total_expenses),
            "net_investment_income": str(net_investment_income),
            "average_shares_outstanding": str(avg_shares),
            "nii_per_share": str(nii_per_share.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
            "annualized_yield": str(annualized_yield.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            "average_nav_per_share": str(avg_nav.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)) if avg_nav > 0 else "0"
        }
        
        # Save result
        result_file = self.storage_path / f"nii_calculation_{period_start.isoformat()}_{period_end.isoformat()}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"NII calculated: ${nii_per_share:.4f} per share (Annualized yield: {annualized_yield:.2f}%)")
        
        return result
    
    def calculate_30_day_yield(self, as_of_date: date) -> Dict[str, Any]:
        """
        Calculate 30-day standardized yield per SEC Form N-1A Instruction (b)(4) to Item 26.
        
        Formula: YIELD = 2[((a-b)/cd + 1)^6 - 1]
        Where:
        a = dividends and interest earned during the period
        b = expenses accrued for the period (net of reimbursements)
        c = the average daily number of shares outstanding during the period that were entitled to receive dividends
        d = the maximum offering price per share on the last day of the period
        
        Args:
            as_of_date: Date to calculate yield as of
            
        Returns:
            Dictionary with 30-day yield calculation
        """
        logger.info(f"Calculating 30-day yield as of {as_of_date}")
        
        period_end = as_of_date
        period_start = period_end - timedelta(days=30)
        
        nav_data = self._load_nav_data(period_start, period_end)
        
        if not nav_data:
            return {
                "status": "error",
                "error": "No NAV data found for 30-day period"
            }
        
        # Calculate dividends and interest earned (a)
        total_dividends_interest = Decimal('0')
        for nav in nav_data:
            accrued_income = Decimal(str(nav.get('accrued_income', 0)))
            total_dividends_interest += accrued_income
        
        # Calculate expenses accrued (b)
        total_expenses = Decimal('0')
        for nav in nav_data:
            accrued_expenses = Decimal(str(nav.get('accrued_expenses', 0)))
            total_expenses += accrued_expenses
        
        # Calculate average daily shares outstanding (c)
        # Per Instruction 1(c) to Item 26(b)(4)
        total_shares = Decimal('0')
        share_count = 0
        for nav in nav_data:
            shares = Decimal(str(nav.get('shares_outstanding', 0)))
            if shares > 0:
                total_shares += shares
                share_count += 1
        
        if share_count == 0:
            return {
                "status": "error",
                "error": "No shares outstanding data found"
            }
        
        avg_daily_shares = total_shares / Decimal(str(share_count))
        
        # Get maximum offering price on last day (d)
        # For ETFs, this is typically the NAV per share
        last_nav = nav_data[-1] if nav_data else {}
        max_offering_price = Decimal(str(last_nav.get('nav_per_share', 0)))
        
        if max_offering_price == 0:
            return {
                "status": "error",
                "error": "Maximum offering price is zero"
            }
        
        # Calculate yield per Instruction (b)(4) formula
        # YIELD = 2[((a-b)/cd + 1)^6 - 1]
        numerator = total_dividends_interest - total_expenses
        denominator = avg_daily_shares * max_offering_price
        
        if denominator == 0:
            return {
                "status": "error",
                "error": "Denominator is zero in yield calculation"
            }
        
        base = (numerator / denominator) + Decimal('1')
        yield_value = Decimal('2') * (base ** Decimal('6') - Decimal('1'))
        yield_percentage = yield_value * Decimal('100')
        
        result = {
            "as_of_date": as_of_date.isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "dividends_interest_earned": str(total_dividends_interest),
            "expenses_accrued": str(total_expenses),
            "average_daily_shares": str(avg_daily_shares),
            "max_offering_price": str(max_offering_price),
            "30_day_yield": str(yield_percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"30-day yield: {yield_percentage:.2f}%")
        
        return result
    
    def calculate_average_annual_total_return(self, period_years: int, as_of_date: date, 
                                            initial_investment: Decimal = Decimal('1000'),
                                            sales_load: Decimal = Decimal('0'),
                                            account_fees: Decimal = Decimal('0')) -> Dict[str, Any]:
        """
        Calculate average annual total return per SEC Form N-1A Instruction (b)(1) to Item 26.
        
        Formula: P(1+T)^n = ERV
        Where:
        P = a hypothetical initial payment (default $1,000)
        T = average annual total return
        n = number of years
        ERV = ending redeemable value
        
        Note: sales_load defaults to 0 since ETFs typically don't have sales loads.
        It's included for mutual fund compatibility per N-1A requirements.
        
        Args:
            period_years: Number of years (1, 5, or 10)
            as_of_date: End date for calculation
            initial_investment: Initial investment amount (default $1,000)
            sales_load: Maximum sales load as percentage (default 0 for ETFs, e.g., 0.05 for 5%)
            account_fees: Account fees as percentage
            
        Returns:
            Dictionary with average annual total return calculation
        """
        logger.info(f"Calculating {period_years}-year average annual total return as of {as_of_date}")
        
        period_end = as_of_date
        period_start = date(period_end.year - period_years, period_end.month, period_end.day)
        
        # Load NAV data for the period
        nav_data = self._load_nav_data(period_start, period_end)
        
        if not nav_data or len(nav_data) < 2:
            return {
                "status": "error",
                "error": f"Insufficient NAV data for {period_years}-year period"
            }
        
        # Get initial NAV (before first day, adjusted for sales load)
        first_nav = nav_data[0]
        initial_nav = Decimal(str(first_nav.get('nav_per_share', 0)))
        
        if initial_nav == 0:
            return {
                "status": "error",
                "error": "Initial NAV is zero"
            }
        
        # Calculate initial investment after sales load
        # For ETFs, sales_load is typically 0
        net_investment = initial_investment * (Decimal('1') - sales_load)
        
        # Calculate initial shares purchased
        initial_shares = net_investment / initial_nav
        
        # Get ending NAV
        last_nav = nav_data[-1]
        ending_nav = Decimal(str(last_nav.get('nav_per_share', 0)))
        
        if ending_nav == 0:
            return {
                "status": "error",
                "error": "Ending NAV is zero"
            }
        
        # Calculate ending value (assume reinvestment of all distributions)
        # For simplicity, we'll use NAV appreciation
        # In full implementation, would track all distributions and reinvestments
        ending_value = initial_shares * ending_nav
        
        # Apply account fees if any
        ending_value = ending_value * (Decimal('1') - account_fees)
        
        # Calculate average annual total return
        # ERV = P(1+T)^n, so T = (ERV/P)^(1/n) - 1
        if net_investment > 0:
            total_return = (ending_value / net_investment) ** (Decimal('1') / Decimal(str(period_years))) - Decimal('1')
            total_return_pct = total_return * Decimal('100')
        else:
            total_return_pct = Decimal('0')
        
        result = {
            "period_years": period_years,
            "as_of_date": as_of_date.isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "initial_investment": str(initial_investment),
            "net_investment_after_load": str(net_investment),
            "initial_nav": str(initial_nav),
            "ending_nav": str(ending_nav),
            "ending_value": str(ending_value),
            "average_annual_total_return": str(total_return_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"{period_years}-year average annual total return: {total_return_pct:.2f}%")
        
        return result
    
    def calculate_after_tax_return_on_distributions(self, period_years: int, as_of_date: date,
                                                   initial_investment: Decimal = Decimal('1000'),
                                                   sales_load: Decimal = Decimal('0'),
                                                   account_fees: Decimal = Decimal('0'),
                                                   tax_rates: Optional[Dict[str, Decimal]] = None) -> Dict[str, Any]:
        """
        Calculate average annual total return after taxes on distributions per SEC Form N-1A Instruction (b)(2) to Item 26.
        
        This calculates return after taxes on fund distributions but NOT after taxes on redemption.
        
        Formula: P(1+T)^n = ATVD
        Where ATVD = ending value after taxes on distributions but not after taxes on redemption
        
        Args:
            period_years: Number of years (1, 5, or 10)
            as_of_date: End date for calculation
            initial_investment: Initial investment amount (default $1,000)
            sales_load: Maximum sales load as percentage (default 0 for ETFs)
            account_fees: Account fees as percentage
            tax_rates: Optional custom tax rates (defaults to highest marginal federal rates)
            
        Returns:
            Dictionary with after-tax return calculation
        """
        logger.info(f"Calculating {period_years}-year after-tax return (distributions) as of {as_of_date}")
        
        if tax_rates is None:
            tax_rates = FEDERAL_TAX_RATES
        
        period_end = as_of_date
        period_start = date(period_end.year - period_years, period_end.month, period_end.day)
        
        # Load NAV and distribution data
        nav_data = self._load_nav_data(period_start, period_end)
        distributions = self._load_distribution_data(period_start, period_end)
        
        if not nav_data or len(nav_data) < 2:
            return {
                "status": "error",
                "error": f"Insufficient NAV data for {period_years}-year period"
            }
        
        # Get initial NAV
        first_nav = nav_data[0]
        initial_nav = Decimal(str(first_nav.get('nav_per_share', 0)))
        
        if initial_nav == 0:
            return {
                "status": "error",
                "error": "Initial NAV is zero"
            }
        
        # Calculate initial investment after sales load
        net_investment = initial_investment * (Decimal('1') - sales_load)
        initial_shares = net_investment / initial_nav
        
        # Track shares and basis over time
        current_shares = initial_shares
        total_basis = net_investment
        
        # Process each distribution
        for dist in distributions:
            ex_date = date.fromisoformat(dist.get('ex_date', ''))
            if period_start <= ex_date <= period_end:
                # Get distribution amounts
                income = Decimal(str(dist.get('income', 0)))
                short_term_cg = Decimal(str(dist.get('short_term_capital_gain', 0)))
                long_term_cg = Decimal(str(dist.get('long_term_capital_gain', 0)))
                total_dist = income + short_term_cg + long_term_cg
                
                if total_dist > 0:
                    # Calculate taxes on distribution
                    # Per N-1A Instruction 4, use highest marginal rates
                    # Track tax character for accurate calculations
                    tax_on_income = income * tax_rates.get('ordinary_income', FEDERAL_TAX_RATES['ordinary_income'])
                    tax_on_stcg = short_term_cg * tax_rates.get('short_term_capital_gain', FEDERAL_TAX_RATES['short_term_capital_gain'])
                    tax_on_ltcg = long_term_cg * tax_rates.get('long_term_capital_gain', FEDERAL_TAX_RATES['long_term_capital_gain'])
                    
                    # Apply Net Investment Income Tax (NIIT) to investment income
                    # NIIT applies to the lesser of: (1) net investment income, or (2) excess of AGI over threshold
                    # For N-1A calculations, we apply it to investment income
                    niit_rate = tax_rates.get('net_investment_income_tax', FEDERAL_TAX_RATES['net_investment_income_tax'])
                    niit_on_income = income * niit_rate
                    niit_on_stcg = short_term_cg * niit_rate
                    # Long-term capital gains may be subject to NIIT depending on AGI, but for simplicity we apply it
                    niit_on_ltcg = long_term_cg * niit_rate
                    
                    total_tax = tax_on_income + tax_on_stcg + tax_on_ltcg + niit_on_income + niit_on_stcg + niit_on_ltcg
                    after_tax_dist = total_dist - total_tax
                    
                    # Reinvest after-tax distribution
                    # Find NAV on ex-date
                    nav_on_ex = self._get_nav_for_date(ex_date, nav_data)
                    if nav_on_ex:
                        nav_price = Decimal(str(nav_on_ex.get('nav_per_share', 0)))
                        if nav_price > 0:
                            new_shares = (after_tax_dist * current_shares) / nav_price
                            current_shares += new_shares
                            total_basis += after_tax_dist * current_shares
        
        # Get ending NAV
        last_nav = nav_data[-1]
        ending_nav = Decimal(str(last_nav.get('nav_per_share', 0)))
        
        if ending_nav == 0:
            return {
                "status": "error",
                "error": "Ending NAV is zero"
            }
        
        # Calculate ending value (no tax on redemption)
        ending_value = current_shares * ending_nav
        
        # Apply account fees
        ending_value = ending_value * (Decimal('1') - account_fees)
        
        # Calculate after-tax return
        if net_investment > 0:
            total_return = (ending_value / net_investment) ** (Decimal('1') / Decimal(str(period_years))) - Decimal('1')
            total_return_pct = total_return * Decimal('100')
        else:
            total_return_pct = Decimal('0')
        
        result = {
            "period_years": period_years,
            "as_of_date": as_of_date.isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "initial_investment": str(initial_investment),
            "net_investment_after_load": str(net_investment),
            "ending_value_after_tax_distributions": str(ending_value),
            "average_annual_total_return_after_tax_distributions": str(total_return_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"{period_years}-year after-tax return (distributions): {total_return_pct:.2f}%")
        
        return result
    
    def calculate_after_tax_return_on_distributions_and_redemption(self, period_years: int, as_of_date: date,
                                                                  initial_investment: Decimal = Decimal('1000'),
                                                                  sales_load: Decimal = Decimal('0'),
                                                                  account_fees: Decimal = Decimal('0'),
                                                                  tax_rates: Optional[Dict[str, Decimal]] = None) -> Dict[str, Any]:
        """
        Calculate average annual total return after taxes on distributions AND redemption per SEC Form N-1A Instruction (b)(3) to Item 26.
        
        This calculates return after taxes on both fund distributions AND capital gains tax on redemption.
        
        Args:
            period_years: Number of years (1, 5, or 10)
            as_of_date: End date for calculation
            initial_investment: Initial investment amount (default $1,000)
            sales_load: Maximum sales load as percentage (default 0 for ETFs)
            account_fees: Account fees as percentage
            tax_rates: Optional custom tax rates (defaults to highest marginal federal rates)
            
        Returns:
            Dictionary with after-tax return calculation (including redemption tax)
        """
        logger.info(f"Calculating {period_years}-year after-tax return (distributions + redemption) as of {as_of_date}")
        
        # First calculate after-tax return on distributions
        after_tax_dist_result = self.calculate_after_tax_return_on_distributions(
            period_years, as_of_date, initial_investment, sales_load, account_fees, tax_rates
        )
        
        if after_tax_dist_result.get("status") == "error":
            return after_tax_dist_result
        
        # Now calculate tax on redemption
        period_end = as_of_date
        period_start = date(period_end.year - period_years, period_end.month, period_end.day)
        
        nav_data = self._load_nav_data(period_start, period_end)
        if not nav_data:
            return {"status": "error", "error": "No NAV data found"}
        
        # Get ending NAV and calculate redemption proceeds
        last_nav = nav_data[-1]
        ending_nav = Decimal(str(last_nav.get('nav_per_share', 0)))
        
        # Use ending value from after-tax distributions calculation
        ending_value_before_redemption_tax = Decimal(str(after_tax_dist_result.get('ending_value_after_tax_distributions', 0)))
        
        # Calculate capital gain on redemption
        net_investment = Decimal(str(after_tax_dist_result.get('net_investment_after_load', 0)))
        capital_gain = ending_value_before_redemption_tax - net_investment
        
        # Apply long-term capital gains tax (assuming holding period > 1 year)
        if tax_rates is None:
            tax_rates = FEDERAL_TAX_RATES
        
        capital_gains_tax_rate = tax_rates.get('long_term_capital_gain', FEDERAL_TAX_RATES['long_term_capital_gain'])
        capital_gains_tax = capital_gain * capital_gains_tax_rate if capital_gain > 0 else Decimal('0')
        
        # Calculate final after-tax value
        ending_value_after_all_taxes = ending_value_before_redemption_tax - capital_gains_tax
        
        # Calculate after-tax return
        if net_investment > 0:
            total_return = (ending_value_after_all_taxes / net_investment) ** (Decimal('1') / Decimal(str(period_years))) - Decimal('1')
            total_return_pct = total_return * Decimal('100')
        else:
            total_return_pct = Decimal('0')
        
        result = {
            "period_years": period_years,
            "as_of_date": as_of_date.isoformat(),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "initial_investment": str(initial_investment),
            "net_investment_after_load": str(net_investment),
            "ending_value_after_all_taxes": str(ending_value_after_all_taxes),
            "capital_gains_tax_on_redemption": str(capital_gains_tax),
            "average_annual_total_return_after_all_taxes": str(total_return_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"{period_years}-year after-tax return (all taxes): {total_return_pct:.2f}%")
        
        return result
    
    def calculate_tax_equivalent_yield(self, as_of_date: date, tax_rate: Decimal) -> Dict[str, Any]:
        """
        Calculate tax equivalent yield per SEC Form N-1A Instruction (b)(5) to Item 26.
        
        Formula: Tax Equivalent Yield = (Tax-Exempt Yield) / (1 - Tax Rate) + Non-Tax-Exempt Yield
        
        This is used for tax-exempt funds (e.g., municipal bond funds).
        
        Args:
            as_of_date: Date to calculate yield as of
            tax_rate: Federal income tax rate (e.g., 0.37 for 37%)
            
        Returns:
            Dictionary with tax equivalent yield calculation
        """
        logger.info(f"Calculating tax equivalent yield as of {as_of_date}")
        
        # First calculate 30-day yield
        yield_data = self.calculate_30_day_yield(as_of_date)
        
        if yield_data.get("status") == "error":
            return yield_data
        
        # For now, assume all yield is tax-exempt (can be refined)
        # In full implementation, would separate tax-exempt and taxable portions
        tax_exempt_yield = Decimal(str(yield_data.get('30_day_yield', 0))) / Decimal('100')
        taxable_yield = Decimal('0')
        
        # Calculate tax equivalent yield
        if tax_rate > 0 and tax_rate < 1:
            tax_equivalent_yield = (tax_exempt_yield / (Decimal('1') - tax_rate)) + taxable_yield
            tax_equivalent_yield_pct = tax_equivalent_yield * Decimal('100')
        else:
            tax_equivalent_yield_pct = tax_exempt_yield * Decimal('100')
        
        result = {
            "as_of_date": as_of_date.isoformat(),
            "tax_rate": str(tax_rate),
            "tax_exempt_yield": str(tax_exempt_yield * Decimal('100')),
            "taxable_yield": str(taxable_yield * Decimal('100')),
            "tax_equivalent_yield": str(tax_equivalent_yield_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }
        
        logger.info(f"Tax equivalent yield: {tax_equivalent_yield_pct:.2f}%")
        
        return result
    
    def _load_nav_data(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Load NAV data for date range"""
        nav_data = []
        current_date = start_date
        
        while current_date <= end_date:
            nav_file = self.storage_path / f"nav_{current_date.isoformat()}.json"
            if nav_file.exists():
                try:
                    with open(nav_file, 'r') as f:
                        nav = json.load(f)
                        nav['date'] = current_date.isoformat()  # Ensure date is set
                        nav_data.append(nav)
                except Exception as e:
                    logger.warning(f"Error loading NAV file {nav_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return nav_data
    
    def generate_financial_highlights(self, fiscal_year_start: date, fiscal_year_end: date) -> Dict[str, Any]:
        """
        Generate complete Financial Highlights table per SEC Form N-1A Item 13.
        
        Includes:
        - Net Asset Value (beginning and end of period)
        - Income from investment operations
        - Distributions
        - Total return
        - Ratios (expenses, net income, portfolio turnover)
        
        Args:
            fiscal_year_start: Start date of fiscal year
            fiscal_year_end: End date of fiscal year
            
        Returns:
            Dictionary with all financial highlights data
        """
        logger.info(f"Generating financial highlights for fiscal year {fiscal_year_start} to {fiscal_year_end}")
        
        nav_data = self._load_nav_data(fiscal_year_start, fiscal_year_end)
        
        if not nav_data:
            return {
                "status": "error",
                "error": "No NAV data found for fiscal year"
            }
        
        # Get beginning and ending NAV
        first_nav = nav_data[0]
        last_nav = nav_data[-1]
        
        nav_beginning = Decimal(str(first_nav.get('nav_per_share', 0)))
        nav_ending = Decimal(str(last_nav.get('nav_per_share', 0)))
        
        # Calculate income from operations
        total_income = Decimal('0')
        total_expenses = Decimal('0')
        for nav in nav_data:
            total_income += Decimal(str(nav.get('accrued_income', 0)))
            total_expenses += Decimal(str(nav.get('accrued_expenses', 0)))
        
        net_investment_income = total_income - total_expenses
        
        # Calculate net gains/losses (balancing figure)
        net_gains_losses = nav_ending - nav_beginning - net_investment_income
        
        # Calculate ratios
        expense_ratio_result = self.calculate_expense_ratio(fiscal_year_start, fiscal_year_end)
        net_income_ratio_result = self.calculate_net_income_ratio(fiscal_year_start, fiscal_year_end)
        turnover_rate = self.calculate_portfolio_turnover_rate(fiscal_year_start, fiscal_year_end)
        
        # Calculate average shares outstanding
        avg_shares = self.calculate_average_shares_outstanding(fiscal_year_start, fiscal_year_end)
        
        # Calculate per-share amounts
        if avg_shares > 0:
            net_investment_income_per_share = net_investment_income / avg_shares
            net_gains_losses_per_share = net_gains_losses / avg_shares
        else:
            net_investment_income_per_share = Decimal('0')
            net_gains_losses_per_share = Decimal('0')
        
        result = {
            "fiscal_year_start": fiscal_year_start.isoformat(),
            "fiscal_year_end": fiscal_year_end.isoformat(),
            "per_share_data": {
                "nav_beginning": str(nav_beginning.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
                "net_investment_income": str(net_investment_income_per_share.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
                "net_gains_losses": str(net_gains_losses_per_share.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),
                "nav_ending": str(nav_ending.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
            },
            "ratios": {
                "expense_ratio": expense_ratio_result.get("expense_ratio", "0.00"),
                "net_income_ratio": net_income_ratio_result.get("net_income_ratio", "0.00"),
                "portfolio_turnover_rate": str(turnover_rate)
            },
            "average_shares_outstanding": str(avg_shares)
        }
        
        # Save result
        result_file = self.storage_path / f"financial_highlights_{fiscal_year_start.isoformat()}_{fiscal_year_end.isoformat()}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info("Financial highlights generated successfully")
        
        return result
