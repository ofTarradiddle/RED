"""
Production-Ready Accounting Function
Complete implementation with all business logic
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class AccountingEntry:
    """Accounting journal entry"""
    entry_id: str
    date: date
    account: str
    debit: Decimal
    credit: Decimal
    description: str
    reference: Optional[str] = None
    reconciled: bool = False


@dataclass
class GeneralLedger:
    """General ledger account"""
    account_code: str
    account_name: str
    account_type: str  # "asset", "liability", "equity", "income", "expense"
    balance: Decimal = Decimal('0')
    entries: List[AccountingEntry] = field(default_factory=list)


@dataclass
class TrialBalance:
    """Trial balance"""
    date: date
    accounts: List[Dict[str, Any]]
    total_debits: Decimal
    total_credits: Decimal
    balanced: bool = True


@dataclass
class FinancialStatement:
    """Financial statement"""
    statement_type: str  # "balance_sheet", "income_statement", "statement_of_cash_flows"
    period_start: date
    period_end: date
    data: Dict[str, Any]
    generated_date: date = field(default_factory=date.today)


class Accounting:
    """
    Production-ready Accounting implementation with full double-entry bookkeeping.
    
    This class provides complete accounting functionality for ETF operations including:
    - General ledger management
    - Journal entry processing with automatic balance validation
    - Trial balance generation
    - Financial statement generation (balance sheet, income statement)
    - NAV entry recording
    - Expense accrual recording
    - Income recognition
    
    All accounting data is persisted to JSON files and can be easily migrated to a database.
    
    Args:
        data_adapter: DataSourceAdapter instance for fetching accounting data
        storage_path: Path to directory for storing accounting data files
        
    Example:
        >>> from lib.etf.adapters import FileBasedDataSourceAdapter
        >>> adapter = FileBasedDataSourceAdapter(data_path="./data")
        >>> accounting = Accounting(adapter)
        >>> nav_data = {"total_assets": "1000000", "total_liabilities": "50000", "net_assets": "950000"}
        >>> results = accounting.daily_accounting_operations(date.today(), nav_data)
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/accounting",
                 audit_trail=None):
        """
        Initialize Accounting system.
        
        Args:
            data_adapter: DataSourceAdapter for fetching accounting data
            storage_path: Path for storing accounting data files
            audit_trail: Optional AuditTrailManager for audit logging
        """
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.audit_trail = audit_trail
        self.general_ledger: Dict[str, GeneralLedger] = {}
        self.journal_entries: List[AccountingEntry] = []
        self.load_ledger()
    
    def load_ledger(self):
        """Load general ledger from storage"""
        ledger_file = self.storage_path / "general_ledger.json"
        if ledger_file.exists():
            try:
                with open(ledger_file, 'r') as f:
                    data = json.load(f)
                    self.general_ledger = {
                        k: GeneralLedger(
                            account_code=v['account_code'],
                            account_name=v['account_name'],
                            account_type=v['account_type'],
                            balance=Decimal(str(v['balance'])),
                            entries=[AccountingEntry(**e) for e in v.get('entries', [])]
                        )
                        for k, v in data.items()
                    }
                logger.info(f"Loaded {len(self.general_ledger)} general ledger accounts")
            except Exception as e:
                logger.error(f"Error loading general ledger: {e}")
                self.general_ledger = {}
                self._initialize_chart_of_accounts()
        else:
            self._initialize_chart_of_accounts()
    
    def _initialize_chart_of_accounts(self):
        """Initialize chart of accounts for ETF"""
        accounts = [
            # Assets
            ("1000", "Cash and Cash Equivalents", "asset"),
            ("1100", "Investments - Securities", "asset"),
            ("1200", "Receivables", "asset"),
            ("1300", "Accrued Income", "asset"),
            
            # Liabilities
            ("2000", "Payables", "liability"),
            ("2100", "Accrued Expenses", "liability"),
            ("2200", "Distributions Payable", "liability"),
            
            # Equity
            ("3000", "Share Capital", "equity"),
            ("3100", "Retained Earnings", "equity"),
            ("3200", "Net Assets", "equity"),
            
            # Income
            ("4000", "Dividend Income", "income"),
            ("4100", "Interest Income", "income"),
            ("4200", "Realized Gains/Losses", "income"),
            ("4300", "Unrealized Gains/Losses", "income"),
            
            # Expenses
            ("5000", "Management Fees", "expense"),
            ("5100", "Administrative Expenses", "expense"),
            ("5200", "Custodial Fees", "expense"),
            ("5300", "Other Expenses", "expense"),
        ]
        
        for code, name, acc_type in accounts:
            self.general_ledger[code] = GeneralLedger(
                account_code=code,
                account_name=name,
                account_type=acc_type,
                balance=Decimal('0')
            )
    
    def save_ledger(self):
        """Save general ledger to storage"""
        ledger_file = self.storage_path / "general_ledger.json"
        try:
            data = {
                code: {
                    "account_code": gl.account_code,
                    "account_name": gl.account_name,
                    "account_type": gl.account_type,
                    "balance": str(gl.balance),
                    "entries": [
                        {
                            "entry_id": e.entry_id,
                            "date": e.date.isoformat(),
                            "account": e.account,
                            "debit": str(e.debit),
                            "credit": str(e.credit),
                            "description": e.description,
                            "reference": e.reference,
                            "reconciled": e.reconciled
                        }
                        for e in gl.entries
                    ]
                }
                for code, gl in self.general_ledger.items()
            }
            with open(ledger_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved general ledger with {len(self.general_ledger)} accounts")
        except Exception as e:
            logger.error(f"Error saving general ledger: {e}")
    
    def create_journal_entry(self, entry_date: date, entries: List[Dict[str, Any]], 
                            description: str, reference: Optional[str] = None) -> List[AccountingEntry]:
        """
        Create journal entry using double-entry bookkeeping principles.
        
        This method enforces the fundamental accounting equation: Debits = Credits.
        All journal entries must balance before being recorded in the general ledger.
        
        Args:
            entry_date: Date of the journal entry
            entries: List of entry dictionaries, each containing:
                {
                    "account": str,  # Account code (e.g., "1000")
                    "debit": Decimal,  # Debit amount (0 if credit entry)
                    "credit": Decimal  # Credit amount (0 if debit entry)
                }
            description: Description of the journal entry
            reference: Optional reference number or identifier
            
        Returns:
            List of AccountingEntry objects created
            
        Raises:
            ValueError: If debits don't equal credits (unbalanced entry)
            ValueError: If account code not found in chart of accounts
            
        Example:
            >>> entries = [
            ...     {"account": "1000", "debit": Decimal("1000"), "credit": Decimal("0")},
            ...     {"account": "3000", "debit": Decimal("0"), "credit": Decimal("1000")}
            ... ]
            >>> journal_entries = accounting.create_journal_entry(
            ...     date.today(), entries, "Initial capital contribution"
            ... )
        """
        logger.info(f"Creating journal entry for {entry_date}: {description}")
        
        # Validate debits = credits
        total_debits = sum(Decimal(str(e.get('debit', 0))) for e in entries)
        total_credits = sum(Decimal(str(e.get('credit', 0))) for e in entries)
        
        if total_debits != total_credits:
            raise ValueError(f"Journal entry unbalanced: Debits={total_debits}, Credits={total_credits}")
        
        # Create entries
        journal_entries = []
        entry_id_base = f"JE_{entry_date.isoformat()}_{len(self.journal_entries)}"
        
        for i, entry_data in enumerate(entries):
            entry_id = f"{entry_id_base}_{i}"
            account_code = entry_data['account']
            debit = Decimal(str(entry_data.get('debit', 0)))
            credit = Decimal(str(entry_data.get('credit', 0)))
            
            if account_code not in self.general_ledger:
                raise ValueError(f"Account {account_code} not found in chart of accounts")
            
            # Create accounting entry
            acc_entry = AccountingEntry(
                entry_id=entry_id,
                date=entry_date,
                account=account_code,
                debit=debit,
                credit=credit,
                description=description,
                reference=reference
            )
            
            # Update general ledger
            gl = self.general_ledger[account_code]
            gl.entries.append(acc_entry)
            
            # Update balance based on account type
            if gl.account_type in ["asset", "expense"]:
                gl.balance += debit - credit
            else:  # liability, equity, income
                gl.balance += credit - debit
            
            journal_entries.append(acc_entry)
        
        self.journal_entries.extend(journal_entries)
        self.save_ledger()
        
        # Log to audit trail
        if self.audit_trail:
            self.audit_trail.log_operation(
                record_type="journal_entry",
                record_date=entry_date,
                operation=f"Journal entry: {description}",
                data={
                    "entry_id": entry_id,
                    "description": description,
                    "reference": reference,
                    "entries": [
                        {
                            "account": e.account,
                            "account_name": self.general_ledger.get(e.account, GeneralLedger(e.account, "", "asset", Decimal('0'))).account_name,
                            "debit": str(e.debit),
                            "credit": str(e.credit),
                            "description": e.description
                        }
                        for e in journal_entries
                    ],
                    "total_debits": str(total_debits),
                    "total_credits": str(total_credits),
                    "balanced": total_debits == total_credits
                },
                related_records=[entry_id]
            )
        
        logger.info(f"Created journal entry with {len(journal_entries)} line items")
        return journal_entries
    
    def record_nav_entries(self, nav_date: date, nav_calculation: Dict[str, Any]) -> List[AccountingEntry]:
        """
        Record NAV calculation as accounting entries in the general ledger.
        
        Creates journal entries to reflect the fund's net asset value:
        - Debit: Investments (Assets)
        - Credit: Liabilities
        - Credit: Net Assets (Equity)
        
        Args:
            nav_date: Date of NAV calculation
            nav_calculation: Dictionary containing:
                {
                    "total_assets": Decimal or str,  # Total fund assets
                    "total_liabilities": Decimal or str,  # Total fund liabilities
                    "net_assets": Decimal or str  # Net assets (assets - liabilities)
                }
                
        Returns:
            List of AccountingEntry objects created
            
        Raises:
            ValueError: If journal entry is unbalanced
            
        Note:
            This should be called daily after NAV calculation to maintain
            accurate accounting records.
        """
        logger.info(f"Recording NAV entries for {nav_date}")
        
        total_assets = Decimal(str(nav_calculation.get('total_assets', 0)))
        total_liabilities = Decimal(str(nav_calculation.get('total_liabilities', 0)))
        net_assets = Decimal(str(nav_calculation.get('net_assets', 0)))
        
        entries = [
            {"account": "1100", "debit": total_assets, "credit": Decimal('0')},  # Investments
            {"account": "2000", "debit": Decimal('0'), "credit": total_liabilities},  # Liabilities
            {"account": "3200", "debit": Decimal('0'), "credit": net_assets},  # Net Assets
        ]
        
        return self.create_journal_entry(
            nav_date,
            entries,
            f"NAV calculation for {nav_date}",
            reference=f"NAV_{nav_date.isoformat()}"
        )
    
    def record_expense_accrual(self, expense_date: date, expense_data: Dict[str, Any]) -> List[AccountingEntry]:
        """Record expense accruals"""
        logger.info(f"Recording expense accruals for {expense_date}")
        
        management_fee = Decimal(str(expense_data.get('management_fee', 0)))
        admin_expenses = Decimal(str(expense_data.get('admin_expenses', 0)))
        custodial_fee = Decimal(str(expense_data.get('custodial_fee', 0)))
        other_expenses = Decimal(str(expense_data.get('other_expenses', 0)))
        
        total_expenses = management_fee + admin_expenses + custodial_fee + other_expenses
        
        entries = [
            {"account": "5000", "debit": management_fee, "credit": Decimal('0')},  # Management Fees
            {"account": "5100", "debit": admin_expenses, "credit": Decimal('0')},  # Admin Expenses
            {"account": "5200", "debit": custodial_fee, "credit": Decimal('0')},  # Custodial Fees
            {"account": "5300", "debit": other_expenses, "credit": Decimal('0')},  # Other Expenses
            {"account": "2100", "debit": Decimal('0'), "credit": total_expenses},  # Accrued Expenses
        ]
        
        return self.create_journal_entry(
            expense_date,
            entries,
            f"Expense accrual for {expense_date}",
            reference=f"EXP_{expense_date.isoformat()}"
        )
    
    def record_income(self, income_date: date, income_data: Dict[str, Any]) -> List[AccountingEntry]:
        """Record income (dividends, interest, etc.)"""
        logger.info(f"Recording income for {income_date}")
        
        dividend_income = Decimal(str(income_data.get('dividend_income', 0)))
        interest_income = Decimal(str(income_data.get('interest_income', 0)))
        
        entries = []
        
        if dividend_income > 0:
            entries.append({"account": "4000", "debit": Decimal('0'), "credit": dividend_income})  # Dividend Income
            entries.append({"account": "1300", "debit": dividend_income, "credit": Decimal('0')})  # Accrued Income
        
        if interest_income > 0:
            entries.append({"account": "4100", "debit": Decimal('0'), "credit": interest_income})  # Interest Income
            entries.append({"account": "1300", "debit": interest_income, "credit": Decimal('0')})  # Accrued Income
        
        if entries:
            return self.create_journal_entry(
                income_date,
                entries,
                f"Income recognition for {income_date}",
                reference=f"INC_{income_date.isoformat()}"
            )
        return []
    
    def generate_trial_balance(self, tb_date: date) -> TrialBalance:
        """
        Generate trial balance for the given date.
        
        A trial balance is a report that lists all accounts and their balances
        to verify that total debits equal total credits. This is a fundamental
        accounting control to ensure the books are balanced.
        
        Args:
            tb_date: Date for which to generate trial balance
            
        Returns:
            TrialBalance object containing:
            - date: Date of trial balance
            - accounts: List of account balances
            - total_debits: Sum of all debit balances
            - total_credits: Sum of all credit balances
            - balanced: Boolean indicating if debits equal credits
            
        Note:
            The trial balance is automatically saved to storage.
            A balanced trial balance (balanced=True) indicates the books are correct.
        """
        logger.info(f"Generating trial balance for {tb_date}")
        
        accounts = []
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for code, gl in sorted(self.general_ledger.items()):
            if gl.account_type in ["asset", "expense"]:
                debits = gl.balance if gl.balance > 0 else Decimal('0')
                credits = -gl.balance if gl.balance < 0 else Decimal('0')
            else:
                debits = -gl.balance if gl.balance < 0 else Decimal('0')
                credits = gl.balance if gl.balance > 0 else Decimal('0')
            
            accounts.append({
                "account_code": code,
                "account_name": gl.account_name,
                "debits": str(debits),
                "credits": str(credits),
                "balance": str(gl.balance)
            })
            
            total_debits += debits
            total_credits += credits
        
        balanced = abs(total_debits - total_credits) < Decimal('0.01')
        
        result = TrialBalance(
            date=tb_date,
            accounts=accounts,
            total_debits=total_debits,
            total_credits=total_credits,
            balanced=balanced
        )
        
        # Save trial balance
        tb_file = self.storage_path / f"trial_balance_{tb_date.isoformat()}.json"
        with open(tb_file, 'w') as f:
            json.dump({
                "date": tb_date.isoformat(),
                "accounts": accounts,
                "total_debits": str(total_debits),
                "total_credits": str(total_credits),
                "balanced": balanced
            }, f, indent=2)
        
        logger.info(f"Trial balance generated: Balanced={balanced}, Debits={total_debits}, Credits={total_credits}")
        
        return result
    
    def generate_balance_sheet(self, statement_date: date) -> FinancialStatement:
        """Generate balance sheet"""
        logger.info(f"Generating balance sheet for {statement_date}")
        
        assets = {}
        liabilities = {}
        equity = {}
        
        for code, gl in self.general_ledger.items():
            if gl.account_type == "asset" and gl.balance != 0:
                assets[code] = {"name": gl.account_name, "balance": str(gl.balance)}
            elif gl.account_type == "liability" and gl.balance != 0:
                liabilities[code] = {"name": gl.account_name, "balance": str(gl.balance)}
            elif gl.account_type == "equity" and gl.balance != 0:
                equity[code] = {"name": gl.account_name, "balance": str(gl.balance)}
        
        total_assets = sum(Decimal(v["balance"]) for v in assets.values())
        total_liabilities = sum(Decimal(v["balance"]) for v in liabilities.values())
        total_equity = sum(Decimal(v["balance"]) for v in equity.values())
        
        result = FinancialStatement(
            statement_type="balance_sheet",
            period_start=statement_date,
            period_end=statement_date,
            data={
                "assets": assets,
                "liabilities": liabilities,
                "equity": equity,
                "total_assets": str(total_assets),
                "total_liabilities": str(total_liabilities),
                "total_equity": str(total_equity)
            }
        )
        
        # Save balance sheet
        bs_file = self.storage_path / f"balance_sheet_{statement_date.isoformat()}.json"
        with open(bs_file, 'w') as f:
            json.dump({
                "statement_type": "balance_sheet",
                "date": statement_date.isoformat(),
                **result.data
            }, f, indent=2)
        
        return result
    
    def generate_income_statement(self, period_start: date, period_end: date) -> FinancialStatement:
        """Generate income statement"""
        logger.info(f"Generating income statement for {period_start} to {period_end}")
        
        income = {}
        expenses = {}
        
        for code, gl in self.general_ledger.items():
            if gl.account_type == "income" and gl.balance != 0:
                income[code] = {"name": gl.account_name, "amount": str(gl.balance)}
            elif gl.account_type == "expense" and gl.balance != 0:
                expenses[code] = {"name": gl.account_name, "amount": str(gl.balance)}
        
        total_income = sum(Decimal(v["amount"]) for v in income.values())
        total_expenses = sum(Decimal(v["amount"]) for v in expenses.values())
        net_income = total_income - total_expenses
        
        result = FinancialStatement(
            statement_type="income_statement",
            period_start=period_start,
            period_end=period_end,
            data={
                "income": income,
                "expenses": expenses,
                "total_income": str(total_income),
                "total_expenses": str(total_expenses),
                "net_income": str(net_income)
            }
        )
        
        # Save income statement
        is_file = self.storage_path / f"income_statement_{period_start.isoformat()}_{period_end.isoformat()}.json"
        with open(is_file, 'w') as f:
            json.dump({
                "statement_type": "income_statement",
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                **result.data
            }, f, indent=2)
        
        return result
    
    def daily_accounting_operations(self, operation_date: date, nav_calculation: Dict[str, Any]) -> Dict[str, Any]:
        """Run daily accounting operations"""
        logger.info(f"Running daily accounting operations for {operation_date}")
        
        results = {
            "date": operation_date.isoformat(),
            "nav_entries": [],
            "expense_entries": [],
            "income_entries": [],
            "trial_balance": None
        }
        
        try:
            # Get accounting data
            accounting_data = self.data_adapter.get_accounting_data(operation_date)
            
            # Record NAV entries
            # Handle both dict and NAVCalculation dataclass
            if hasattr(nav_calculation, 'total_assets'):
                # It's a NAVCalculation dataclass
                nav_data = {
                    "total_assets": str(nav_calculation.total_assets),
                    "total_liabilities": str(nav_calculation.total_liabilities),
                    "net_assets": str(nav_calculation.net_assets)
                }
            else:
                # It's a dict
                nav_data = nav_calculation
            results["nav_entries"] = self.record_nav_entries(operation_date, nav_data)
            
            # Record expense accruals
            expense_data = accounting_data.get('expenses', {})
            results["expense_entries"] = self.record_expense_accrual(operation_date, expense_data)
            
            # Record income
            income_data = accounting_data.get('income', {})
            results["income_entries"] = self.record_income(operation_date, income_data)
            
            # Generate trial balance
            results["trial_balance"] = self.generate_trial_balance(operation_date)
            
        except Exception as e:
            logger.error(f"Error in daily accounting operations: {e}")
            results["error"] = str(e)
        
        return results

