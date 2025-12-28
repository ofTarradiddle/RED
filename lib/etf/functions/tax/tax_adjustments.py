"""
M-1 Book-to-Tax Adjustments and Tax Footnotes
Production-ready implementation for book-to-tax reconciliation and audit support

This module handles:
- M-1 reconciliation (book income vs taxable income)
- Book-to-tax adjustments
- Tax footnotes for fiscal year-end audit
- Permanent and temporary differences
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
class BookToTaxAdjustment:
    """Book-to-tax adjustment record"""
    adjustment_type: str  # "permanent" or "temporary"
    description: str
    book_amount: Decimal
    tax_amount: Decimal
    adjustment_amount: Decimal
    category: str  # "income", "expense", "gain", "loss"
    reference: Optional[str] = None


@dataclass
class M1Reconciliation:
    """M-1 reconciliation (book income to taxable income)"""
    fiscal_year_end: date
    book_net_income: Decimal
    taxable_income: Decimal
    permanent_differences: List[BookToTaxAdjustment]
    temporary_differences: List[BookToTaxAdjustment]
    total_adjustments: Decimal
    reconciled: bool = False


@dataclass
class TaxFootnote:
    """Tax footnote for audit"""
    footnote_number: str
    category: str  # "income", "expense", "distribution", "tax_provision"
    description: str
    amount: Decimal
    details: Dict[str, Any] = field(default_factory=dict)


class BookToTaxAdjustments:
    """
    Production-ready M-1 Book-to-Tax Adjustments
    
    Handles reconciliation between book accounting and tax accounting,
    including permanent and temporary differences.
    
    Example:
        >>> adjustments = BookToTaxAdjustments(storage_path="./data/tax_adjustments")
        >>> m1 = adjustments.calculate_m1_reconciliation(
        ...     fiscal_year_end=date(2024, 12, 31),
        ...     book_net_income=Decimal('1000000'),
        ...     ledger_data=ledger_accounts
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/tax_adjustments"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.adjustments: List[BookToTaxAdjustment] = []
        self.m1_reconciliations: Dict[date, M1Reconciliation] = {}
    
    def calculate_m1_reconciliation(self, fiscal_year_end: date,
                                    book_net_income: Decimal,
                                    ledger_data: Dict[str, Decimal],
                                    taxlot_manager=None) -> M1Reconciliation:
        """
        Calculate M-1 reconciliation (book income to taxable income)
        
        M-1 reconciles book net income (GAAP) to taxable income (tax basis).
        Common adjustments:
        - Permanent differences: Municipal bond interest (tax-exempt), penalties, etc.
        - Temporary differences: Depreciation, unrealized gains/losses, etc.
        
        Args:
            fiscal_year_end: Fiscal year end date
            book_net_income: Book net income from income statement
            ledger_data: General ledger account balances
            taxlot_manager: TaxLotManager for realized gains calculation
            
        Returns:
            M1Reconciliation object
        """
        logger.info(f"Calculating M-1 reconciliation for fiscal year ending {fiscal_year_end}")
        
        permanent_differences = []
        temporary_differences = []
        
        # 1. Permanent Differences
        
        # Municipal bond interest (tax-exempt, included in book income but not taxable)
        municipal_interest = ledger_data.get('Municipal Bond Interest', Decimal('0'))
        if municipal_interest > 0:
            permanent_differences.append(BookToTaxAdjustment(
                adjustment_type="permanent",
                description="Municipal bond interest (tax-exempt)",
                book_amount=municipal_interest,
                tax_amount=Decimal('0'),
                adjustment_amount=-municipal_interest,
                category="income",
                reference="IRC Section 103"
            ))
        
        # Penalties and fines (not deductible for tax)
        penalties = ledger_data.get('Penalties', Decimal('0'))
        if penalties > 0:
            permanent_differences.append(BookToTaxAdjustment(
                adjustment_type="permanent",
                description="Penalties and fines (non-deductible)",
                book_amount=-penalties,
                tax_amount=Decimal('0'),
                adjustment_amount=penalties,
                category="expense",
                reference="IRC Section 162(f)"
            ))
        
        # 2. Temporary Differences
        
        # Unrealized gains/losses (included in book income but not taxable until realized)
        unrealized_gains = ledger_data.get('Unrealized Gains', Decimal('0'))
        if unrealized_gains != 0:
            temporary_differences.append(BookToTaxAdjustment(
                adjustment_type="temporary",
                description="Unrealized gains/losses (not taxable until realized)",
                book_amount=unrealized_gains,
                tax_amount=Decimal('0'),
                adjustment_amount=-unrealized_gains,
                category="gain" if unrealized_gains > 0 else "loss",
                reference="Mark-to-market accounting"
            ))
        
        # Realized gains (from tax lot manager if provided)
        if taxlot_manager:
            realized_summary = taxlot_manager.get_realized_gains_summary(
                start_date=date(fiscal_year_end.year, 1, 1),
                end_date=fiscal_year_end
            )
            realized_gains = Decimal(str(realized_summary.get('long_term_gains', 0))) + \
                            Decimal(str(realized_summary.get('short_term_gains', 0)))
            
            # Check if book income includes realized gains
            book_realized = ledger_data.get('Realized Gains', Decimal('0'))
            if realized_gains != book_realized:
                temporary_differences.append(BookToTaxAdjustment(
                    adjustment_type="temporary",
                    description="Realized gains (tax basis vs book basis)",
                    book_amount=book_realized,
                    tax_amount=realized_gains,
                    adjustment_amount=realized_gains - book_realized,
                    category="gain",
                    reference="Tax lot accounting"
                ))
        
        # Calculate total adjustments
        total_permanent = sum(adj.adjustment_amount for adj in permanent_differences)
        total_temporary = sum(adj.adjustment_amount for adj in temporary_differences)
        total_adjustments = total_permanent + total_temporary
        
        # Calculate taxable income
        taxable_income = book_net_income + total_adjustments
        
        m1 = M1Reconciliation(
            fiscal_year_end=fiscal_year_end,
            book_net_income=book_net_income,
            taxable_income=taxable_income,
            permanent_differences=permanent_differences,
            temporary_differences=temporary_differences,
            total_adjustments=total_adjustments,
            reconciled=True
        )
        
        self.m1_reconciliations[fiscal_year_end] = m1
        self._save_m1_reconciliation(m1)
        
        logger.info(f"M-1 reconciliation complete: Book income=${book_net_income}, "
                   f"Taxable income=${taxable_income}, Adjustments=${total_adjustments}")
        
        return m1
    
    def _save_m1_reconciliation(self, m1: M1Reconciliation):
        """Save M-1 reconciliation to storage"""
        m1_file = self.storage_path / f"m1_reconciliation_{m1.fiscal_year_end.isoformat()}.json"
        try:
            data = {
                "fiscal_year_end": m1.fiscal_year_end.isoformat(),
                "book_net_income": str(m1.book_net_income),
                "taxable_income": str(m1.taxable_income),
                "total_adjustments": str(m1.total_adjustments),
                "reconciled": m1.reconciled,
                "permanent_differences": [
                    {
                        "description": adj.description,
                        "book_amount": str(adj.book_amount),
                        "tax_amount": str(adj.tax_amount),
                        "adjustment_amount": str(adj.adjustment_amount),
                        "category": adj.category,
                        "reference": adj.reference
                    }
                    for adj in m1.permanent_differences
                ],
                "temporary_differences": [
                    {
                        "description": adj.description,
                        "book_amount": str(adj.book_amount),
                        "tax_amount": str(adj.tax_amount),
                        "adjustment_amount": str(adj.adjustment_amount),
                        "category": adj.category,
                        "reference": adj.reference
                    }
                    for adj in m1.temporary_differences
                ]
            }
            with open(m1_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved M-1 reconciliation to {m1_file}")
        except Exception as e:
            logger.error(f"Error saving M-1 reconciliation: {e}")
    
    def generate_tax_footnotes(self, fiscal_year_end: date,
                               m1_reconciliation: M1Reconciliation,
                               form_1120_ric: Dict[str, Any],
                               distributions: List[Dict[str, Any]]) -> List[TaxFootnote]:
        """
        Generate tax footnotes for fiscal year-end audit
        
        Tax footnotes provide detailed explanations of tax-related items
        for the financial statements audit.
        
        Args:
            fiscal_year_end: Fiscal year end date
            m1_reconciliation: M1Reconciliation object
            form_1120_ric: Form 1120-RIC data
            distributions: List of distribution records
            
        Returns:
            List of TaxFootnote objects
        """
        logger.info(f"Generating tax footnotes for fiscal year ending {fiscal_year_end}")
        
        footnotes = []
        
        # Footnote 1: Tax Provision
        tax_provision = Decimal(str(form_1120_ric.get('corporate_tax_due', '0')))
        footnotes.append(TaxFootnote(
            footnote_number="1",
            category="tax_provision",
            description="Income Tax Provision",
            amount=tax_provision,
            details={
                "federal_income_tax": str(tax_provision),
                "effective_tax_rate": str(form_1120_ric.get('effective_tax_rate', '0')),
                "statutory_rate": "21%",
                "reconciliation": "See M-1 reconciliation"
            }
        ))
        
        # Footnote 2: M-1 Reconciliation Summary
        footnotes.append(TaxFootnote(
            footnote_number="2",
            category="income",
            description="Reconciliation of Book Income to Taxable Income (M-1)",
            amount=m1_reconciliation.total_adjustments,
            details={
                "book_net_income": str(m1_reconciliation.book_net_income),
                "permanent_differences": str(sum(adj.adjustment_amount for adj in m1_reconciliation.permanent_differences)),
                "temporary_differences": str(sum(adj.adjustment_amount for adj in m1_reconciliation.temporary_differences)),
                "taxable_income": str(m1_reconciliation.taxable_income)
            }
        ))
        
        # Footnote 3: Distributions
        total_distributions = sum(Decimal(str(d.get('total_amount', '0'))) for d in distributions)
        footnotes.append(TaxFootnote(
            footnote_number="3",
            category="distribution",
            description="Distributions to Shareholders",
            amount=total_distributions,
            details={
                "dividend_distributions": str(sum(Decimal(str(d.get('total_amount', '0'))) for d in distributions if d.get('distribution_type') == 'dividend')),
                "capital_gain_distributions": str(sum(Decimal(str(d.get('total_amount', '0'))) for d in distributions if d.get('distribution_type') == 'capital_gains')),
                "distribution_policy": "Distributes substantially all net investment income and net realized capital gains"
            }
        ))
        
        # Footnote 4: Tax-Exempt Income (if applicable)
        tax_exempt_income = sum(adj.adjustment_amount for adj in m1_reconciliation.permanent_differences 
                               if "municipal" in adj.description.lower() or "tax-exempt" in adj.description.lower())
        if tax_exempt_income < 0:  # Negative because it reduces taxable income
            footnotes.append(TaxFootnote(
                footnote_number="4",
                category="income",
                description="Tax-Exempt Income",
                amount=-tax_exempt_income,
                details={
                    "municipal_bond_interest": str(-tax_exempt_income),
                    "tax_status": "Excluded from taxable income per IRC Section 103"
                }
            ))
        
        # Save footnotes
        self._save_tax_footnotes(fiscal_year_end, footnotes)
        
        logger.info(f"Generated {len(footnotes)} tax footnotes for audit")
        return footnotes
    
    def _save_tax_footnotes(self, fiscal_year_end: date, footnotes: List[TaxFootnote]):
        """Save tax footnotes to storage"""
        footnotes_file = self.storage_path / f"tax_footnotes_{fiscal_year_end.isoformat()}.json"
        try:
            data = {
                "fiscal_year_end": fiscal_year_end.isoformat(),
                "footnotes": [
                    {
                        "footnote_number": fn.footnote_number,
                        "category": fn.category,
                        "description": fn.description,
                        "amount": str(fn.amount),
                        "details": fn.details
                    }
                    for fn in footnotes
                ]
            }
            with open(footnotes_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved tax footnotes to {footnotes_file}")
        except Exception as e:
            logger.error(f"Error saving tax footnotes: {e}")

