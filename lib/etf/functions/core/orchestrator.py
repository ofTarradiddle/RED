"""
Production-Ready Daily Operations Orchestrator
Complete implementation for coordinating all ETF operational functions

This orchestrator ties all modules together in an end-to-end daily workflow.
It coordinates NAV calculation, accounting entries, tax lot tracking, distributions,
and periodic reporting tasks.

References:
- ITAN ETF Fund Administration System
- SEC: Daily Operations Requirements for ETFs
"""

import logging
import yaml
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from decimal import Decimal

from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.functions.operations.distributor import Distributor
from lib.etf.functions.operations.performance import PerformanceCalculator
from lib.etf.functions.tax.tax_reporting import TaxReporting
from lib.etf.shared import DataSourceAdapter

logger = logging.getLogger(__name__)


class DailyOrchestrator:
    """
    Production-ready Daily Operations Orchestrator.
    
    Coordinates all ETF operational functions in a daily workflow:
    - NAV calculation
    - Accounting entries
    - Tax lot tracking
    - Distribution processing
    - Performance calculation
    - Tax and regulatory reporting
    
    Example:
        >>> from lib.etf.adapters import FileBasedDataSourceAdapter
        >>> adapter = FileBasedDataSourceAdapter(data_path="./data")
        >>> orchestrator = DailyOrchestrator(adapter, config_path="config.yaml")
        >>> orchestrator.run_daily_operations(date.today())
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, config_path: str = "config.yaml"):
        """
        Initialize Daily Orchestrator.
        
        Args:
            data_adapter: DataSourceAdapter instance
            config_path: Path to YAML configuration file
        """
        self.data_adapter = data_adapter
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Initialize all operational modules
        self.admin = FundAdministration(
            data_adapter=data_adapter,
            storage_path=self.config.get('paths', {}).get('admin_storage', './data/admin')
        )
        self.accounting = Accounting(
            data_adapter=data_adapter,
            storage_path=self.config.get('paths', {}).get('accounting_storage', './data/accounting')
        )
        self.taxlot_manager = TaxLotManager(
            storage_path=self.config.get('paths', {}).get('tax_lot_storage', './data/tax_lots')
        )
        self.distributor = Distributor(
            data_adapter=data_adapter,
            storage_path=self.config.get('paths', {}).get('distributor_storage', './data/distributor')
        )
        self.performance = PerformanceCalculator(
            storage_path=self.config.get('paths', {}).get('performance_storage', './data/performance')
        )
        self.tax_reporting = TaxReporting(
            data_adapter=data_adapter,
            storage_path=self.config.get('paths', {}).get('tax_storage', './data/tax')
        )
        
        # Set up logging
        log_level = getattr(logging, self.config.get('logging', {}).get('level', 'INFO'))
        log_file = self.config.get('logging', {}).get('file', None)
        if log_file:
            logging.basicConfig(
                filename=log_file,
                level=log_level,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        
        logger.info("Daily Orchestrator initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def run_daily_operations(self, operation_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Run all daily operations for the specified date.
        
        Args:
            operation_date: Date to run operations for (defaults to today)
            
        Returns:
            Dictionary with operation results
        """
        if operation_date is None:
            operation_date = date.today()
        
        logger.info(f"Starting daily operations for {operation_date}")
        
        results = {
            "date": operation_date.isoformat(),
            "operations": {},
            "errors": []
        }
        
        try:
            # 1. Calculate NAV
            logger.info("Step 1: Calculating NAV")
            nav_calc = self.admin.calculate_nav(operation_date)
            results["operations"]["nav_calculation"] = {
                "nav_per_share": str(nav_calc.nav_per_share),
                "total_assets": str(nav_calc.total_assets),
                "net_assets": str(nav_calc.net_assets),
                "validation_passed": nav_calc.validation_passed
            }
            
            # 2. Record NAV in accounting
            logger.info("Step 2: Recording NAV in accounting")
            nav_data = {
                "total_assets": str(nav_calc.total_assets),
                "total_liabilities": str(nav_calc.total_liabilities),
                "net_assets": str(nav_calc.net_assets),
                "shares_outstanding": str(nav_calc.shares_outstanding),
                "nav_per_share": str(nav_calc.nav_per_share)
            }
            self.accounting.daily_accounting_operations(operation_date, nav_calc)
            results["operations"]["accounting"] = {"status": "completed"}
            
            # 3. Process any scheduled trades
            logger.info("Step 3: Processing scheduled trades")
            trades_processed = self._process_trades(operation_date, nav_calc)
            results["operations"]["trades"] = trades_processed
            
            # 4. Reconcile holdings and cash
            logger.info("Step 4: Reconciling holdings and cash")
            recon_result = self.admin.reconcile_holdings_cash(operation_date)
            results["operations"]["reconciliation"] = recon_result
            
            # 5. Process corporate actions
            logger.info("Step 5: Processing corporate actions")
            ca_result = self.admin.process_corporate_actions(operation_date)
            results["operations"]["corporate_actions"] = ca_result
            
            # 6. Check for distribution dates
            logger.info("Step 6: Checking for distribution dates")
            dist_result = self._process_distributions(operation_date, nav_data)
            if dist_result:
                results["operations"]["distributions"] = dist_result
            
            # 7. Year-end reporting tasks
            fiscal_year_end = self.config.get('fund', {}).get('fiscal_year_end', '12-31')
            fy_month, fy_day = map(int, fiscal_year_end.split('-'))
            
            if operation_date.month == fy_month and operation_date.day == fy_day:
                logger.info("Step 7: Running year-end reporting tasks")
                year_end_results = self._run_year_end_tasks(operation_date.year)
                results["operations"]["year_end"] = year_end_results
            
            logger.info(f"Daily operations completed successfully for {operation_date}")
            results["status"] = "success"
            
        except Exception as e:
            logger.error(f"Error in daily operations: {e}", exc_info=True)
            results["status"] = "error"
            results["errors"].append(str(e))
        
        return results
    
    def _process_trades(self, trade_date: date, nav_calc) -> Dict[str, Any]:
        """Process any scheduled trades for the date"""
        trades = self.config.get('trades', [])
        processed = []
        
        for trade in trades:
            trade_date_str = trade.get('date')
            if not trade_date_str:
                continue
            
            try:
                trade_date_obj = date.fromisoformat(trade_date_str)
                if trade_date_obj != trade_date:
                    continue
            except:
                continue
            
            ticker = trade.get('ticker')
            qty = Decimal(str(trade.get('quantity', 0)))
            action = trade.get('type', '').upper()
            
            logger.info(f"Processing trade: {action} {qty} of {ticker}")
            
            if action == "BUY":
                # Record purchase in accounting and tax lots
                price = nav_calc.nav_per_share  # Using NAV as proxy for purchase price
                cost_total = price * qty
                
                # Add tax lot
                self.taxlot_manager.add_lot(
                    ticker=ticker,
                    quantity=qty,
                    cost_basis=price,
                    purchase_date=trade_date
                )
                
                # Record in accounting (use account codes)
                self.accounting.create_journal_entry(
                    entry_date=trade_date,
                    description=f"Buy {qty} shares of {ticker}",
                    entries=[
                        {"account": "1100", "debit": cost_total},  # Investments - Securities
                        {"account": "1000", "credit": cost_total}  # Cash and Cash Equivalents
                    ]
                )
                
                processed.append({"ticker": ticker, "action": "BUY", "quantity": str(qty), "status": "completed"})
                
            elif action == "SELL":
                # Record sale in accounting and tax lots
                price = nav_calc.nav_per_share
                
                # Calculate realized gain from tax lots
                try:
                    realized_gain = self.taxlot_manager.sell(
                        ticker=ticker,
                        quantity=qty,
                        price=price,
                        sale_date=trade_date
                    )
                    
                    proceeds = price * qty
                    cost_out = proceeds - realized_gain
                    
                    # Record in accounting (use account codes)
                    entries = [
                        {"account": "1000", "debit": proceeds},  # Cash and Cash Equivalents
                        {"account": "1100", "credit": cost_out}  # Investments - Securities
                    ]
                    if realized_gain >= 0:
                        entries.append({"account": "4200", "credit": realized_gain})  # Realized Gains/Losses
                    else:
                        entries.append({"account": "4200", "debit": abs(realized_gain)})  # Realized Gains/Losses (loss)
                    
                    self.accounting.create_journal_entry(
                        entry_date=trade_date,
                        description=f"Sell {qty} shares of {ticker}",
                        entries=entries
                    )
                    
                    processed.append({
                        "ticker": ticker,
                        "action": "SELL",
                        "quantity": str(qty),
                        "realized_gain": str(realized_gain),
                        "status": "completed"
                    })
                except Exception as e:
                    logger.error(f"Error processing sell trade: {e}")
                    processed.append({
                        "ticker": ticker,
                        "action": "SELL",
                        "quantity": str(qty),
                        "status": "error",
                        "error": str(e)
                    })
        
        return {"trades_processed": len(processed), "trades": processed}
    
    def _process_distributions(self, dist_date: date, nav_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process distributions if it's a distribution date"""
        dist_config = self.config.get('distributions', {})
        dist_freq = dist_config.get('frequency', '').lower()
        payout_ratio = Decimal(str(dist_config.get('payout_ratio', 1.0)))
        
        need_dist = False
        
        if dist_freq == "quarterly":
            # Quarterly: Mar, Jun, Sep, Dec end-of-month
            if dist_date.month in (3, 6, 9, 12):
                # Check if it's end of month
                next_day = dist_date + timedelta(days=1)
                if next_day.month != dist_date.month:
                    need_dist = True
        elif dist_freq == "annual":
            # Annual: fiscal year end
            fiscal_year_end = self.config.get('fund', {}).get('fiscal_year_end', '12-31')
            fy_month, fy_day = map(int, fiscal_year_end.split('-'))
            if dist_date.month == fy_month and dist_date.day == fy_day:
                need_dist = True
        elif dist_freq == "monthly":
            # Monthly: last day of month
            next_day = dist_date + timedelta(days=1)
            if next_day.month != dist_date.month:
                need_dist = True
        
        if not need_dist:
            return None
        
        logger.info(f"Processing distribution on {dist_date}")
        
        # Get ledger data for payout ratio calculation
        ledger_accounts = self.accounting.list_accounts()
        
        # Calculate dividend distribution
        distribution = self.distributor.calculate_distribution(
            dist_date=dist_date,
            distribution_type="dividend",
            nav_data=nav_data,
            payout_ratio=payout_ratio,
            ledger_data=ledger_accounts
        )
        
        # Declare distribution
        self.distributor.declare_distribution(distribution)
        
        # Record in accounting (use account codes)
        self.accounting.create_journal_entry(
            entry_date=dist_date,
            description=f"Income distribution on {dist_date}",
            entries=[
                {"account": "4000", "debit": distribution.total_amount},  # Dividend Income
                {"account": "1000", "credit": distribution.total_amount}  # Cash and Cash Equivalents
            ]
        )
        
        return {
            "distribution_id": distribution.distribution_id,
            "amount_per_share": str(distribution.amount_per_share),
            "total_amount": str(distribution.total_amount),
            "payout_ratio": str(payout_ratio)
        }
    
    def _run_year_end_tasks(self, tax_year: int) -> Dict[str, Any]:
        """Run year-end tax and regulatory reporting tasks"""
        logger.info(f"Running year-end tasks for {tax_year}")
        
        results = {}
        
        try:
            # Performance calculation
            nav_history_path = self.config.get('paths', {}).get('nav_history', 'nav_history.csv')
            dist_history_path = self.config.get('paths', {}).get('distribution_history', 'distributions.csv')
            benchmark = self.config.get('fund', {}).get('benchmark')
            tax_rates = self.config.get('tax', {})
            
            perf_result = self.performance.compute_performance(
                nav_history_path=nav_history_path,
                dist_history_path=dist_history_path,
                benchmark_symbol=benchmark,
                tax_rates=tax_rates
            )
            results["performance"] = perf_result
            
            # Tax reporting
            ledger_accounts = self.accounting.list_accounts()
            distributions = [
                {
                    "distribution_type": d.distribution_type,
                    "total_amount": str(d.total_amount)
                }
                for d in self.distributor.distributions
                if d.record_date.year == tax_year
            ]
            
            form_1120_ric = self.tax_reporting.generate_tax_return_form_1120_ric(
                tax_year=tax_year,
                ledger_data=ledger_accounts,
                taxlot_manager=self.taxlot_manager,
                distributions=distributions
            )
            results["form_1120_ric"] = form_1120_ric
            
            form_8613 = self.tax_reporting.generate_form_8613(
                tax_year=tax_year,
                ledger_data=ledger_accounts,
                taxlot_manager=self.taxlot_manager,
                distributions=distributions
            )
            results["form_8613"] = form_8613
            
            logger.info("Year-end tasks completed successfully")
            
        except Exception as e:
            logger.error(f"Error in year-end tasks: {e}", exc_info=True)
            results["error"] = str(e)
        
        return results

