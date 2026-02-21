"""
FMP-Enhanced Workflows for Accounting & Administration
These workflows integrate FMP APIs into the daily, monthly, and periodic operations.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter, NAVCalculation
from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.adapters.fmp_adapter import FMPDataSourceAdapter

logger = logging.getLogger(__name__)


class FMPEnhancedWorkflows:
    """
    Enhanced workflows that use FMP APIs for accounting and administration.
    
    This class provides workflows that integrate FMP data sources into the
    standard accounting and admin operations, following the implementation guide
    for internalizing ETF operations with FMP Ultimate.
    
    Args:
        etf_symbol: ETF symbol for holdings and data lookups
        fmp_client: Optional FMPClient instance
        api_key: Optional FMP API key
        fallback_adapter: Optional fallback adapter for data not available via FMP
        storage_path: Path for storing workflow outputs
    """
    
    def __init__(self, etf_symbol: str = "", fmp_client=None, api_key: Optional[str] = None,
                 fallback_adapter: Optional[DataSourceAdapter] = None,
                 storage_path: str = "./data/admin",
                 manual_holdings: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize FMP-Enhanced Workflows.
        
        Args:
            etf_symbol: ETF symbol (optional if using manual holdings)
            fmp_client: Optional FMPClient instance
            api_key: Optional FMP API key
            fallback_adapter: Optional fallback adapter
            storage_path: Path for storing workflow outputs
            manual_holdings: Optional manual holdings for pre-launch ETFs
        """
        self.etf_symbol = etf_symbol
        self.fmp_adapter = FMPDataSourceAdapter(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            fallback_adapter=fallback_adapter,
            manual_holdings=manual_holdings
        )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize accounting and admin with FMP adapter
        self.accounting = Accounting(self.fmp_adapter, storage_path=str(self.storage_path / "accounting"))
        self.admin = FundAdministration(self.fmp_adapter, storage_path=str(self.storage_path))
    
    def daily_price_import_and_nav(self, nav_date: date) -> Dict[str, Any]:
        """
        Daily Price Import & NAV Calculation workflow.
        
        Retrieves end-of-day prices for all ETF holdings using FMP batch quote API
        and calculates the fund's NAV. Uses official closing prices for accuracy.
        
        Frequency: Daily (each trading day)
        FMP APIs: Stock Batch Quote API, Historical Price (EOD) API
        """
        logger.info(f"Running daily price import and NAV calculation for {nav_date}")
        
        try:
            # Calculate NAV using FMP adapter (which uses batch quote API)
            nav_calc = self.admin.calculate_nav(nav_date)
            
            # Record NAV in accounting system
            nav_data = {
                "total_assets": str(nav_calc.total_assets),
                "total_liabilities": str(nav_calc.total_liabilities),
                "net_assets": str(nav_calc.net_assets)
            }
            accounting_results = self.accounting.daily_accounting_operations(nav_date, nav_data)
            
            result = {
                "date": nav_date.isoformat(),
                "nav_calculation": {
                    "nav_per_share": str(nav_calc.nav_per_share),
                    "total_assets": str(nav_calc.total_assets),
                    "total_liabilities": str(nav_calc.total_liabilities),
                    "net_assets": str(nav_calc.net_assets),
                    "shares_outstanding": str(nav_calc.shares_outstanding),
                    "validation_passed": nav_calc.validation_passed,
                    "pricing_exceptions": nav_calc.pricing_exceptions
                },
                "accounting_entries": {
                    "nav_entries": len(accounting_results.get("nav_entries", [])),
                    "expense_entries": len(accounting_results.get("expense_entries", [])),
                    "income_entries": len(accounting_results.get("income_entries", [])),
                    "trial_balance_balanced": accounting_results.get("trial_balance", {}).get("balanced", False) if accounting_results.get("trial_balance") else False
                }
            }
            
            # Save daily NAV report
            nav_report_file = self.storage_path / f"daily_nav_report_{nav_date.isoformat()}.json"
            with open(nav_report_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Daily NAV calculated: ${nav_calc.nav_per_share} per share")
            return result
            
        except Exception as e:
            logger.error(f"Error in daily price import and NAV calculation: {e}")
            return {"date": nav_date.isoformat(), "error": str(e)}
    
    def daily_corporate_actions_processing(self, action_date: date) -> Dict[str, Any]:
        """
        Daily Corporate Actions Processing workflow.
        
        Identifies and applies corporate actions affecting holdings using FMP APIs:
        - Stock splits (adjusting share counts and per-share cost)
        - Ticker symbol changes or mergers (updating symbols)
        - Name changes
        
        Frequency: Daily (on event)
        FMP APIs: Symbol Changes List API, Stock Splits Calendar API, Stock Split Details API
        """
        logger.info(f"Processing corporate actions for {action_date}")
        
        try:
            # Process corporate actions using FMP adapter
            actions_result = self.admin.process_corporate_actions(action_date)
            
            # Get detailed action log
            actions = actions_result.get("actions", [])
            
            # Create adjustment log
            adjustment_log = []
            for action in actions:
                action_type = action.get("type")
                cusip = action.get("cusip", "")
                ticker = action.get("ticker", "")
                
                adjustment_log.append({
                    "date": action_date.isoformat(),
                    "action_type": action_type,
                    "ticker": ticker,
                    "cusip": cusip,
                    "details": action,
                    "applied": True
                })
            
            result = {
                "date": action_date.isoformat(),
                "actions_processed": len(actions),
                "adjustment_log": adjustment_log,
                "status": "completed"
            }
            
            # Save corporate actions log
            ca_file = self.storage_path / f"corporate_actions_{action_date.isoformat()}.json"
            with open(ca_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Processed {len(actions)} corporate actions")
            return result
            
        except Exception as e:
            logger.error(f"Error processing corporate actions: {e}")
            return {"date": action_date.isoformat(), "error": str(e), "actions_processed": 0}
    
    def daily_dividend_accrual_tracking(self, tracking_date: date) -> Dict[str, Any]:
        """
        Daily Dividend Accrual Tracking workflow.
        
        Tracks dividends from underlying holdings for accurate income accrual.
        On ex-dividend dates, records dividend receivables; on pay dates, records cash received.
        
        Frequency: Daily (morning sweep for new events)
        FMP APIs: Dividends Calendar API, Dividends Company API
        """
        logger.info(f"Tracking dividend accruals for {tracking_date}")
        
        try:
            # Get dividend data from FMP adapter (uses dividends calendar API)
            accounting_data = self.fmp_adapter.get_accounting_data(tracking_date)
            income_data = accounting_data.get("income", {})
            
            # Get holdings to calculate total dividend income
            holdings = self.fmp_adapter.get_portfolio_holdings(tracking_date)
            
            # Get dividend calendar around this date
            start_date = (tracking_date - timedelta(days=30)).isoformat()
            end_date = (tracking_date + timedelta(days=30)).isoformat()
            
            fmp_client = self.fmp_adapter.fmp_client
            dividend_calendar = fmp_client.get_dividends_calendar(start_date, end_date)
            
            # Build dividend schedule
            dividend_schedule = []
            total_accrued = Decimal('0')
            
            for div in dividend_calendar:
                symbol = div.get('symbol') or div.get('ticker')
                ex_date = div.get('exDate') or div.get('ex_date')
                pay_date = div.get('paymentDate') or div.get('pay_date')
                amount = div.get('dividend') or div.get('amount', 0)
                
                # Check if this dividend affects our holdings
                for holding in holdings:
                    if holding.get('ticker') == symbol:
                        quantity = Decimal(str(holding.get('quantity', 0)))
                        dividend_per_share = Decimal(str(amount))
                        total_dividend = quantity * dividend_per_share
                        total_accrued += total_dividend
                        
                        dividend_schedule.append({
                            "ticker": symbol,
                            "cusip": holding.get('cusip', ''),
                            "ex_date": ex_date,
                            "payable_date": pay_date,
                            "amount_per_share": str(dividend_per_share),
                            "quantity": str(quantity),
                            "total_amount": str(total_dividend),
                            "status": "accrued" if ex_date and ex_date <= tracking_date.isoformat() else "pending"
                        })
                        break
            
            # Record income in accounting system
            if total_accrued > 0:
                income_entry = {
                    "dividend_income": str(total_accrued),
                    "interest_income": "0"
                }
                self.accounting.record_income(tracking_date, income_entry)
            
            result = {
                "date": tracking_date.isoformat(),
                "total_accrued_income": str(total_accrued),
                "dividend_schedule": dividend_schedule,
                "income_recorded": total_accrued > 0
            }
            
            # Save dividend schedule
            div_file = self.storage_path / f"dividend_schedule_{tracking_date.isoformat()}.json"
            with open(div_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Tracked dividend accruals: ${total_accrued} total")
            return result
            
        except Exception as e:
            logger.error(f"Error tracking dividend accruals: {e}")
            return {"date": tracking_date.isoformat(), "error": str(e)}
    
    def daily_expense_accrual_and_fee_booking(self, expense_date: date) -> Dict[str, Any]:
        """
        Daily Expense Accrual & Fee Booking workflow.
        
        Accrues fund expenses (management fees, custody fees) each day to incorporate into NAV.
        Uses the fund's expense ratio from FMP for verification.
        
        Frequency: Daily
        FMP APIs: ETF & Mutual Fund Information API (for expense ratio verification)
        """
        logger.info(f"Accruing expenses for {expense_date}")
        
        try:
            # Get expense data (includes FMP expense ratio verification)
            expense_data = self.fmp_adapter.get_expense_data(expense_date)
            
            # Record expense accruals in accounting
            expense_entries = self.accounting.record_expense_accrual(expense_date, expense_data)
            
            result = {
                "date": expense_date.isoformat(),
                "expense_data": {
                    k: str(v) if isinstance(v, Decimal) else v
                    for k, v in expense_data.items()
                },
                "expense_entries_recorded": len(expense_entries),
                "status": "completed"
            }
            
            # Save expense journal
            exp_file = self.storage_path / f"expense_journal_{expense_date.isoformat()}.json"
            with open(exp_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Expenses accrued for {expense_date}")
            return result
            
        except Exception as e:
            logger.error(f"Error accruing expenses: {e}")
            return {"date": expense_date.isoformat(), "error": str(e)}
    
    def daily_nav_verification_and_reconciliation(self, nav_date: date, 
                                                   benchmark_symbol: str = "SPY") -> Dict[str, Any]:
        """
        Daily NAV Verification & Reconciliation workflow.
        
        Performs quality assurance on calculated NAV by:
        - Comparing NAV % change against benchmark index % change
        - Verifying price inputs were correct
        - Checking for discrepancies beyond threshold
        
        Frequency: Daily
        FMP APIs: Index Market Data API, Batch Quote API (for price verification)
        """
        logger.info(f"Verifying NAV for {nav_date}")
        
        try:
            # Get NAV calculation
            nav_calc = self.admin.calculate_nav(nav_date)
            
            # Get previous day NAV for comparison
            prev_date = nav_date - timedelta(days=1)
            prev_nav_file = self.storage_path / f"nav_{prev_date.isoformat()}.json"
            prev_nav = None
            if prev_nav_file.exists():
                with open(prev_nav_file, 'r') as f:
                    prev_nav = json.load(f)
            
            # Calculate NAV % change
            nav_change_pct = None
            if prev_nav:
                prev_nav_per_share = Decimal(str(prev_nav.get("nav_per_share", 0)))
                if prev_nav_per_share > 0:
                    nav_change_pct = ((nav_calc.nav_per_share - prev_nav_per_share) / prev_nav_per_share) * 100
            
            # Get benchmark performance
            benchmark_data = self.fmp_adapter.get_benchmark_data(benchmark_symbol, nav_date)
            benchmark_change_pct = None
            if benchmark_data:
                benchmark_change_pct = benchmark_data.get('changePercent') or benchmark_data.get('change')
                if isinstance(benchmark_change_pct, str):
                    benchmark_change_pct = float(benchmark_change_pct.replace('%', ''))
            
            # Compare NAV vs benchmark
            discrepancy = None
            if nav_change_pct is not None and benchmark_change_pct is not None:
                discrepancy = abs(nav_change_pct - benchmark_change_pct)
            
            # Reasonableness check (threshold: 2% difference)
            threshold = Decimal('2.0')
            passed = True
            exceptions = []
            
            if discrepancy and discrepancy > threshold:
                passed = False
                exceptions.append(
                    f"NAV change ({nav_change_pct:.2f}%) differs from benchmark "
                    f"({benchmark_change_pct:.2f}%) by {discrepancy:.2f}% (threshold: {threshold}%)"
                )
            
            # Add pricing exceptions from NAV calculation
            if nav_calc.pricing_exceptions:
                exceptions.extend(nav_calc.pricing_exceptions)
                passed = False
            
            result = {
                "date": nav_date.isoformat(),
                "nav_per_share": str(nav_calc.nav_per_share),
                "nav_change_pct": float(nav_change_pct) if nav_change_pct else None,
                "benchmark_symbol": benchmark_symbol,
                "benchmark_change_pct": benchmark_change_pct,
                "discrepancy_pct": float(discrepancy) if discrepancy else None,
                "reconciliation_status": "pass" if passed else "fail",
                "exceptions": exceptions,
                "validation_passed": passed
            }
            
            # Save NAV QA report
            qa_file = self.storage_path / f"nav_qa_report_{nav_date.isoformat()}.json"
            with open(qa_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"NAV verification: {'PASSED' if passed else 'FAILED'}")
            return result
            
        except Exception as e:
            logger.error(f"Error verifying NAV: {e}")
            return {"date": nav_date.isoformat(), "error": str(e), "reconciliation_status": "error"}
    
    def monthly_quarterly_close(self, period_end: date, period_type: str = "monthly") -> Dict[str, Any]:
        """
        Monthly/Quarterly Close & Financial Statement Prep workflow.
        
        Closes the books at period-end and prepares financial reports using:
        - End-of-period market prices from FMP historical data
        - Security details (ISINs, classifications) for reporting disclosures
        
        Frequency: Monthly (internal closes); Quarterly & Annual (for external financials)
        FMP APIs: Historical Price (EOD) API, Search & Directory APIs (CUSIP/CIK), ETF Holdings API
        """
        logger.info(f"Running {period_type} close for {period_end}")
        
        try:
            # Get period start date
            if period_type == "monthly":
                period_start = period_end.replace(day=1)
            elif period_type == "quarterly":
                quarter = (period_end.month - 1) // 3 + 1
                period_start = date(period_end.year, (quarter - 1) * 3 + 1, 1)
            else:  # annual
                period_start = date(period_end.year, 1, 1)
            
            # Calculate NAV for period end using FMP historical prices
            nav_calc = self.admin.calculate_nav(period_end)
            
            # Generate financial statements
            balance_sheet = self.accounting.generate_balance_sheet(period_end)
            income_statement = self.accounting.generate_income_statement(period_start, period_end)
            trial_balance = self.accounting.generate_trial_balance(period_end)
            
            # Get security identifiers for reporting (using FMP)
            holdings = self.fmp_adapter.get_portfolio_holdings(period_end)
            security_details = []
            for holding in holdings:
                ticker = holding.get('ticker')
                if ticker:
                    identifiers = self.fmp_adapter.get_security_identifiers(ticker)
                    security_details.append({
                        "ticker": ticker,
                        "cusip": identifiers.get('cusip'),
                        "cik": identifiers.get('cik'),
                        "isin": identifiers.get('isin'),
                        "name": identifiers.get('name'),
                        "quantity": holding.get('quantity'),
                        "market_value": holding.get('market_value')
                    })
            
            result = {
                "period_type": period_type,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "nav_calculation": {
                    "nav_per_share": str(nav_calc.nav_per_share),
                    "total_assets": str(nav_calc.total_assets),
                    "net_assets": str(nav_calc.net_assets)
                },
                "financial_statements": {
                    "balance_sheet": {
                        "total_assets": balance_sheet.data.get("total_assets"),
                        "total_liabilities": balance_sheet.data.get("total_liabilities"),
                        "total_equity": balance_sheet.data.get("total_equity")
                    },
                    "income_statement": {
                        "total_income": income_statement.data.get("total_income"),
                        "total_expenses": income_statement.data.get("total_expenses"),
                        "net_income": income_statement.data.get("net_income")
                    },
                    "trial_balance": {
                        "balanced": trial_balance.balanced,
                        "total_debits": str(trial_balance.total_debits),
                        "total_credits": str(trial_balance.total_credits)
                    }
                },
                "security_details": security_details,
                "status": "completed"
            }
            
            # Save period close report
            close_file = self.storage_path / f"{period_type}_close_{period_end.isoformat()}.json"
            with open(close_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"{period_type.capitalize()} close completed for {period_end}")
            return result
            
        except Exception as e:
            logger.error(f"Error in {period_type} close: {e}")
            return {"period_end": period_end.isoformat(), "error": str(e), "status": "error"}
    
    def investor_reporting_monthly_factsheet(self, report_date: date) -> Dict[str, Any]:
        """
        Investor Reporting (Monthly Factsheet & Portfolio Metrics) workflow.
        
        Generates monthly investor factsheet with:
        - Performance data (MTD, YTD, 1-year returns)
        - Top holdings and weights
        - Sector and geographic allocation
        - Key fund metrics (P/E, dividend yield, AUM)
        
        Frequency: Monthly
        FMP APIs: Historical Price (EOD) API, Index Market Data API, ETF Sector Weightings API,
                  Key Metrics TTM API, Company Profile API
        """
        logger.info(f"Generating monthly factsheet for {report_date}")
        
        try:
            # Get portfolio metrics (uses FMP key metrics and sector APIs)
            portfolio_metrics = self.fmp_adapter.get_portfolio_metrics(report_date)
            
            # Get NAV history for performance calculation
            # Calculate returns (simplified - would need full history)
            nav_calc = self.admin.calculate_nav(report_date)
            
            # Get holdings for top 10
            holdings = self.fmp_adapter.get_portfolio_holdings(report_date)
            holdings_sorted = sorted(holdings, key=lambda x: float(x.get('weight', 0)), reverse=True)
            top_10_holdings = holdings_sorted[:10]
            
            # Get benchmark performance
            benchmark_symbol = "SPY"  # Could be configurable
            benchmark_data = self.fmp_adapter.get_benchmark_data(benchmark_symbol, report_date)
            
            result = {
                "report_date": report_date.isoformat(),
                "fund_symbol": self.etf_symbol,
                "nav_per_share": str(nav_calc.nav_per_share),
                "total_net_assets": str(nav_calc.net_assets),
                "shares_outstanding": str(nav_calc.shares_outstanding),
                "portfolio_metrics": {
                    "weighted_pe_ratio": portfolio_metrics.get('weighted_pe'),
                    "weighted_dividend_yield": portfolio_metrics.get('weighted_dividend_yield'),
                    "sector_allocations": portfolio_metrics.get('sector_allocations', {})
                },
                "top_10_holdings": [
                    {
                        "ticker": h.get('ticker'),
                        "name": h.get('name'),
                        "weight": h.get('weight'),
                        "market_value": h.get('market_value')
                    }
                    for h in top_10_holdings
                ],
                "benchmark": {
                    "symbol": benchmark_symbol,
                    "price": benchmark_data.get('price') if benchmark_data else None,
                    "change_pct": benchmark_data.get('changePercent') if benchmark_data else None
                },
                "performance": {
                    # Would calculate MTD, YTD, 1-year from NAV history
                    "nav_per_share": str(nav_calc.nav_per_share)
                }
            }
            
            # Save factsheet
            factsheet_file = self.storage_path / f"factsheet_{report_date.isoformat()}.json"
            with open(factsheet_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Monthly factsheet generated for {report_date}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating factsheet: {e}")
            return {"report_date": report_date.isoformat(), "error": str(e)}
    
    def run_daily_operations(self, operation_date: date, benchmark_symbol: str = "SPY") -> Dict[str, Any]:
        """
        Run all daily operations in sequence.
        
        This orchestrates all daily workflows:
        1. Daily price import and NAV calculation
        2. Corporate actions processing
        3. Dividend accrual tracking
        4. Expense accrual and fee booking
        5. NAV verification and reconciliation
        
        Args:
            operation_date: Date for operations
            benchmark_symbol: Benchmark symbol for NAV verification
            
        Returns:
            Dictionary with results from all daily operations
        """
        logger.info(f"Running all daily operations for {operation_date}")
        
        results = {
            "date": operation_date.isoformat(),
            "operations": {}
        }
        
        # 1. Daily price import and NAV
        results["operations"]["nav_calculation"] = self.daily_price_import_and_nav(operation_date)
        
        # 2. Corporate actions
        results["operations"]["corporate_actions"] = self.daily_corporate_actions_processing(operation_date)
        
        # 3. Dividend accrual tracking
        results["operations"]["dividend_accrual"] = self.daily_dividend_accrual_tracking(operation_date)
        
        # 4. Expense accrual
        results["operations"]["expense_accrual"] = self.daily_expense_accrual_and_fee_booking(operation_date)
        
        # 5. NAV verification
        results["operations"]["nav_verification"] = self.daily_nav_verification_and_reconciliation(
            operation_date, benchmark_symbol
        )
        
        # Save daily operations summary
        summary_file = self.storage_path / f"daily_operations_{operation_date.isoformat()}.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Daily operations completed for {operation_date}")
        return results

