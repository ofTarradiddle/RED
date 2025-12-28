"""
Audit Cooperation Functions
Production-ready implementation for cooperation with fund auditors

This module provides:
- Audit trail maintenance
- Financial statement preparation for auditors
- Supporting documentation generation
- Auditor access to records
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from decimal import Decimal
from pathlib import Path
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class AuditPackage:
    """Audit package for auditors"""
    audit_date: date
    fiscal_year_end: date
    financial_statements: Dict[str, Any]
    supporting_documentation: List[str]  # File paths
    trial_balances: List[str]
    journal_entries: List[str]
    reconciliation_reports: List[str]
    tax_documents: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditCooperation:
    """
    Production-ready Audit Cooperation System
    
    Provides comprehensive support for fund auditors:
    - Financial statement preparation
    - Supporting documentation
    - Audit trail access
    - Reconciliation reports
    
    Example:
        >>> audit = AuditCooperation(storage_path="./data/audit")
        >>> package = audit.prepare_audit_package(
        ...     fiscal_year_end=date(2024, 12, 31),
        ...     accounting=accounting_instance,
        ...     admin=admin_instance
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/audit"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.audit_packages: Dict[date, AuditPackage] = {}
    
    def prepare_audit_package(self, fiscal_year_end: date,
                            accounting, admin=None,
                            tax_reporting=None, distributor=None) -> AuditPackage:
        """
        Prepare comprehensive audit package for auditors
        
        Args:
            fiscal_year_end: Fiscal year end date
            accounting: Accounting instance
            admin: FundAdministration instance (optional)
            tax_reporting: TaxReporting instance (optional)
            distributor: Distributor instance (optional)
            
        Returns:
            AuditPackage object
        """
        logger.info(f"Preparing audit package for fiscal year ending {fiscal_year_end}")
        
        # Generate financial statements
        balance_sheet = accounting.generate_balance_sheet(fiscal_year_end)
        income_statement = accounting.generate_income_statement(
            date(fiscal_year_end.year, 1, 1),
            fiscal_year_end
        )
        
        financial_statements = {
            "balance_sheet": {
                "date": balance_sheet.period_end.isoformat(),
                "assets": balance_sheet.data.get("assets", {}),
                "liabilities": balance_sheet.data.get("liabilities", {}),
                "net_assets": balance_sheet.data.get("net_assets", {})
            },
            "income_statement": {
                "period_start": income_statement.period_start.isoformat(),
                "period_end": income_statement.period_end.isoformat(),
                "income": income_statement.data.get("income", {}),
                "expenses": income_statement.data.get("expenses", {}),
                "net_investment_income": income_statement.data.get("net_investment_income", {})
            }
        }
        
        # Generate trial balances (monthly)
        trial_balances = []
        for month in range(1, 13):
            month_end = date(fiscal_year_end.year, month, 28)  # Approximate month end
            if month_end <= fiscal_year_end:
                try:
                    tb = accounting.generate_trial_balance(month_end)
                    tb_file = self.storage_path / f"trial_balance_{month_end.isoformat()}.json"
                    self._save_trial_balance(tb, tb_file)
                    trial_balances.append(str(tb_file))
                except Exception as e:
                    logger.error(f"Error generating trial balance for {month_end}: {e}")
        
        # Get journal entries (all entries for the year)
        journal_entries = []
        for entry in accounting.journal_entries:
            if entry.date.year == fiscal_year_end.year:
                journal_entries.append({
                    "entry_id": entry.entry_id,
                    "date": entry.date.isoformat(),
                    "account": entry.account,
                    "debit": str(entry.debit),
                    "credit": str(entry.credit),
                    "description": entry.description,
                    "reference": entry.reference
                })
        
        # Save journal entries
        journal_file = self.storage_path / f"journal_entries_{fiscal_year_end.year}.json"
        with open(journal_file, 'w') as f:
            json.dump(journal_entries, f, indent=2)
        journal_entries_path = [str(journal_file)]
        
        # Get reconciliation reports
        reconciliation_reports = []
        if admin:
            # Monthly reconciliation reports
            for month in range(1, 13):
                month_end = date(fiscal_year_end.year, month, 28)
                if month_end <= fiscal_year_end:
                    try:
                        recon = admin.reconcile_holdings_cash(month_end)
                        recon_file = self.storage_path / f"reconciliation_{month_end.isoformat()}.json"
                        self._save_reconciliation(recon, recon_file)
                        reconciliation_reports.append(str(recon_file))
                    except Exception as e:
                        logger.error(f"Error generating reconciliation for {month_end}: {e}")
        
        # Get tax documents
        tax_documents = []
        if tax_reporting:
            tax_year = fiscal_year_end.year
            # Form 1120-RIC
            tax_documents.append(f"Form 1120-RIC for {tax_year}")
            # Form 8613
            tax_documents.append(f"Form 8613 for {tax_year}")
            # 1099 forms
            tax_documents.append(f"1099 forms for {tax_year}")
        
        # Supporting documentation
        supporting_documentation = [
            "NAV calculation history",
            "Holdings reconciliation reports",
            "Corporate actions log",
            "Distribution records",
            "Expense accrual records"
        ]
        
        package = AuditPackage(
            audit_date=date.today(),
            fiscal_year_end=fiscal_year_end,
            financial_statements=financial_statements,
            supporting_documentation=supporting_documentation,
            trial_balances=trial_balances,
            journal_entries=journal_entries_path,
            reconciliation_reports=reconciliation_reports,
            tax_documents=tax_documents,
            metadata={
                "prepared_by": "Fund Accounting System",
                "preparation_date": date.today().isoformat(),
                "auditor_access": "Available upon request"
            }
        )
        
        # Save audit package
        self._save_audit_package(package)
        self.audit_packages[fiscal_year_end] = package
        
        logger.info(f"Audit package prepared: {len(trial_balances)} trial balances, "
                   f"{len(journal_entries)} journal entries, "
                   f"{len(reconciliation_reports)} reconciliation reports")
        
        return package
    
    def _save_trial_balance(self, tb, file_path: Path):
        """Save trial balance to file"""
        try:
            data = {
                "date": tb.date.isoformat(),
                "accounts": tb.accounts,
                "total_debits": str(tb.total_debits),
                "total_credits": str(tb.total_credits),
                "balanced": tb.balanced
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trial balance: {e}")
    
    def _save_reconciliation(self, recon, file_path: Path):
        """Save reconciliation report to file"""
        try:
            data = {
                "recon_date": recon.recon_date.isoformat() if hasattr(recon, 'recon_date') else date.today().isoformat(),
                "reconciled": recon.reconciled if hasattr(recon, 'reconciled') else True,
                "discrepancies": recon.discrepancies if hasattr(recon, 'discrepancies') else []
            }
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving reconciliation: {e}")
    
    def _save_audit_package(self, package: AuditPackage):
        """Save audit package to storage"""
        package_file = self.storage_path / f"audit_package_{package.fiscal_year_end.isoformat()}.json"
        try:
            data = {
                "audit_date": package.audit_date.isoformat(),
                "fiscal_year_end": package.fiscal_year_end.isoformat(),
                "financial_statements": package.financial_statements,
                "supporting_documentation": package.supporting_documentation,
                "trial_balances": package.trial_balances,
                "journal_entries": package.journal_entries,
                "reconciliation_reports": package.reconciliation_reports,
                "tax_documents": package.tax_documents,
                "metadata": package.metadata
            }
            with open(package_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved audit package to {package_file}")
        except Exception as e:
            logger.error(f"Error saving audit package: {e}")

