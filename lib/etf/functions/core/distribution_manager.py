"""
ETF Distribution Manager - Operational Workflow
Implements the complete distribution calculation and booking process per industry standards.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DistributionManager:
    """
    Complete ETF distribution management per operational standards.
    
    Implements the 6-step distribution workflow:
    1. Lock distribution period and cut-off
    2. Compute income available for distribution
    3. Compute capital gain available for distribution
    4. Apply distribution requirements (RIC + excise)
    5. Determine shares entitled to distribution
    6. Convert dollars to per-share rate
    """
    
    def __init__(self, accounting, storage_path: str = "./data/distributions"):
        """
        Args:
            accounting: Accounting instance for ledger access
            storage_path: Path for storing distribution records
        """
        self.accounting = accounting
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def get_unii(self, as_of_date: date) -> Decimal:
        """
        Get Undistributed Net Investment Income (UNII) as of date.
        
        UNII = Cumulative NII not yet distributed
        
        Calculated from general ledger:
        - Beginning UNII (from prior period)
        + Period NII (income - expenses)
        - Prior distributions
        
        Returns:
            UNII balance as of date
        """
        # Get account balances from general ledger
        ledger = self.accounting.get_ledger()
        
        # UNII is typically tracked in an equity account or separate UNII account
        # For now, calculate from income and distributions
        dividend_income = self._get_account_balance(ledger, '4000')
        interest_income = self._get_account_balance(ledger, '4100')
        total_expenses = abs(self._get_account_balance(ledger, '5000'))
        
        # Distributions paid (credit balance in distributions payable = liability)
        distributions_paid = abs(self._get_account_balance(ledger, '2200'))
        
        # Calculate UNII
        # NII = Income - Expenses
        nii = dividend_income + interest_income - abs(total_expenses)
        
        # UNII = NII - Distributions paid
        # Note: This is simplified - in practice, UNII is tracked in a separate account
        unii = nii - abs(distributions_paid)
        
        return max(unii, Decimal('0'))  # UNII can't be negative
    
    def calculate_income_available_for_distribution(self, period_start: date, 
                                                    period_end: date,
                                                    prior_income_distributions: Decimal = Decimal('0')) -> Dict[str, Any]:
        """
        Step 2: Compute income available for distribution.
        
        Formula:
        Income Available = Beginning UNII + Period NII - Prior Income Distributions
        
        Args:
            period_start: Start of distribution period
            period_end: End of distribution period
            prior_income_distributions: Income distributions already paid in period
            
        Returns:
            Dictionary with income available calculation
        """
        logger.info(f"Calculating income available for distribution: {period_start} to {period_end}")
        
        # Get beginning UNII (from start of period)
        beginning_unii = self.get_unii(period_start - timedelta(days=1))
        
        # Calculate period NII from general ledger entries
        # Get all entries in the period
        ledger = self.accounting.get_ledger()
        
        # Sum income entries in period
        period_dividend_income = self._sum_account_entries(ledger, '4000', period_start, period_end)
        period_interest_income = self._sum_account_entries(ledger, '4100', period_start, period_end)
        
        # Sum expense entries in period (expenses are debits, so we sum debits)
        period_expenses = self._sum_account_debits(ledger, '5000', period_start, period_end)
        
        # Period NII
        period_nii = period_dividend_income + period_interest_income - period_expenses
        
        # Income available
        income_available = beginning_unii + period_nii - prior_income_distributions
        
        result = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "beginning_unii": str(beginning_unii),
            "period_dividend_income": str(period_dividend_income),
            "period_interest_income": str(period_interest_income),
            "period_expenses": str(period_expenses),
            "period_nii": str(period_nii),
            "prior_income_distributions": str(prior_income_distributions),
            "income_available": str(income_available),
            "ending_unii": str(income_available)  # If not distributed
        }
        
        logger.info(f"Income available: ${income_available:,.2f} (Beginning UNII: ${beginning_unii:,.2f}, Period NII: ${period_nii:,.2f})")
        
        return result
    
    def calculate_capital_gain_available(self, period_start: date, period_end: date,
                                        prior_capital_gain_distributions: Decimal = Decimal('0'),
                                        in_kind_redemption_adjustment: Decimal = Decimal('0')) -> Dict[str, Any]:
        """
        Step 3: Compute capital gain available for distribution.
        
        Formula:
        Capital Gain Available = Net Realized Gains - Prior Capital Gain Distributions - In-Kind Adjustments
        
        Note: In-kind redemptions generate GAAP gains but are not taxable/distributable.
        
        Args:
            period_start: Start of distribution period
            period_end: End of distribution period
            prior_capital_gain_distributions: Capital gain distributions already paid
            in_kind_redemption_adjustment: Adjustment for in-kind redemptions (non-distributable)
            
        Returns:
            Dictionary with capital gain available calculation
        """
        logger.info(f"Calculating capital gain available: {period_start} to {period_end}")
        
        # Get realized gains from ledger
        ledger = self.accounting.get_ledger()
        
        # Realized gains are typically in account 4200 (Realized Gains/Losses)
        # Short-term and long-term may be separate accounts
        realized_gains_st = self._get_account_balance(ledger, '4500')  # Short-term (if separate)
        realized_gains_lt = self._get_account_balance(ledger, '4600')  # Long-term (if separate)
        
        # If not separate, use main realized gains account
        if realized_gains_st == 0 and realized_gains_lt == 0:
            total_realized = self._get_account_balance(ledger, '4200')
            # Assume 50/50 split if not tracked separately (simplified)
            realized_gains_st = total_realized / Decimal('2')
            realized_gains_lt = total_realized / Decimal('2')
        
        # Net realized gains (gains - losses)
        net_realized_gains = realized_gains_st + realized_gains_lt
        
        # Capital gain available (taxable, distributable)
        # Subtract in-kind adjustments (GAAP gains that aren't taxable)
        capital_gain_available = net_realized_gains - in_kind_redemption_adjustment - prior_capital_gain_distributions
        
        result = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "realized_gains_short_term": str(realized_gains_st),
            "realized_gains_long_term": str(realized_gains_lt),
            "net_realized_gains": str(net_realized_gains),
            "in_kind_redemption_adjustment": str(in_kind_redemption_adjustment),
            "prior_capital_gain_distributions": str(prior_capital_gain_distributions),
            "capital_gain_available": str(max(capital_gain_available, Decimal('0')))
        }
        
        logger.info(f"Capital gain available: ${capital_gain_available:,.2f}")
        
        return result
    
    def calculate_distribution(self, distribution_date: date,
                              distribution_type: str = "income",
                              shares_outstanding: Decimal = None,
                              payout_ratio: Decimal = Decimal('0.95'),
                              equalization_reduction: Decimal = Decimal('0')) -> Dict[str, Any]:
        """
        Complete distribution calculation workflow.
        
        Args:
            distribution_date: Distribution date (typically quarter/month end)
            distribution_type: "income", "capital_gain", or "combined"
            shares_outstanding: Shares outstanding on record date
            payout_ratio: Percentage of available income to distribute (default 95%)
            equalization_reduction: Reduction for equalization accounting
            
        Returns:
            Complete distribution calculation with per-share amounts
        """
        logger.info(f"Calculating {distribution_type} distribution for {distribution_date}")
        
        # Step 1: Determine distribution period
        # For quarterly distributions, period is the quarter
        if distribution_date.month in [3, 6, 9, 12]:
            # Quarter end
            quarter = (distribution_date.month - 1) // 3 + 1
            period_start = date(distribution_date.year, (quarter - 1) * 3 + 1, 1)
            period_end = distribution_date
        else:
            # Monthly or other
            period_start = date(distribution_date.year, distribution_date.month, 1)
            period_end = distribution_date
        
        # Step 2 & 3: Calculate available amounts
        income_calc = self.calculate_income_available_for_distribution(period_start, period_end)
        capital_gain_calc = self.calculate_capital_gain_available(period_start, period_end)
        
        # Step 4: Apply payout ratio and determine distribution amounts
        income_available = Decimal(str(income_calc['income_available']))
        capital_gain_available = Decimal(str(capital_gain_calc['capital_gain_available']))
        
        if distribution_type == "income":
            distribution_amount = income_available * payout_ratio
            capital_gain_distribution = Decimal('0')
        elif distribution_type == "capital_gain":
            distribution_amount = capital_gain_available * payout_ratio
            capital_gain_distribution = distribution_amount
        else:  # combined
            distribution_amount = (income_available + capital_gain_available) * payout_ratio
            capital_gain_distribution = capital_gain_available * payout_ratio
        
        # Apply equalization reduction
        distribution_amount = max(distribution_amount - equalization_reduction, Decimal('0'))
        
        # Step 5 & 6: Calculate per-share amount
        if shares_outstanding is None or shares_outstanding == 0:
            raise ValueError("Shares outstanding must be provided and > 0")
        
        distribution_per_share = (distribution_amount / shares_outstanding).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
        
        # Recalculate total based on rounded per-share (operational standard)
        total_distribution = distribution_per_share * shares_outstanding
        
        result = {
            "distribution_date": distribution_date.isoformat(),
            "distribution_type": distribution_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "income_available": str(income_available),
            "capital_gain_available": str(capital_gain_available),
            "payout_ratio": str(payout_ratio),
            "equalization_reduction": str(equalization_reduction),
            "distribution_amount": str(total_distribution),
            "distribution_per_share": str(distribution_per_share),
            "shares_outstanding": str(shares_outstanding),
            "capital_gain_distribution": str(capital_gain_distribution),
            "income_distribution": str(total_distribution - capital_gain_distribution)
        }
        
        # Save calculation
        calc_file = self.storage_path / f"distribution_calculation_{distribution_date.isoformat()}.json"
        with open(calc_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Distribution calculated: ${distribution_per_share:.4f} per share, Total: ${total_distribution:,.2f}")
        
        return result
    
    def record_distribution_declaration(self, distribution_date: date,
                                       distribution_calc: Dict[str, Any],
                                       ex_date: date = None,
                                       record_date: date = None,
                                       payable_date: date = None) -> Dict[str, Any]:
        """
        Record distribution declaration in accounting (Step 4.2).
        
        Accounting entries on ex-date:
        - Income distribution:
          Dr. UNII (or Dividend Income)
          Cr. Distributions Payable
        
        - Capital gain distribution:
          Dr. Accumulated Net Realized Gains
          Cr. Distributions Payable
        
        Args:
            distribution_date: Declaration date
            distribution_calc: Result from calculate_distribution()
            ex_date: Ex-dividend date (defaults to distribution_date)
            record_date: Record date (defaults to ex_date)
            payable_date: Payable date (defaults to record_date + 1)
            
        Returns:
            Journal entry details
        """
        if ex_date is None:
            ex_date = distribution_date
        if record_date is None:
            record_date = ex_date
        if payable_date is None:
            payable_date = record_date + timedelta(days=1)
        
        distribution_amount = Decimal(str(distribution_calc['distribution_amount']))
        income_distribution = Decimal(str(distribution_calc['income_distribution']))
        capital_gain_distribution = Decimal(str(distribution_calc['capital_gain_distribution']))
        
        # Create journal entries
        entries = []
        
        # Income distribution entry
        if income_distribution > 0:
            entries.append({
                "account": "1300",  # UNII or Accrued Income (debit to reduce)
                "debit": income_distribution,
                "credit": Decimal('0'),
                "description": f"Income distribution declaration - {ex_date}"
            })
            entries.append({
                "account": "2200",  # Distributions Payable (credit liability)
                "debit": Decimal('0'),
                "credit": income_distribution,
                "description": f"Income distribution payable - {ex_date}"
            })
        
        # Capital gain distribution entry
        if capital_gain_distribution > 0:
            entries.append({
                "account": "4500",  # Accumulated Net Realized Gains (debit to reduce)
                "debit": capital_gain_distribution,
                "credit": Decimal('0'),
                "description": f"Capital gain distribution declaration - {ex_date}"
            })
            entries.append({
                "account": "2200",  # Distributions Payable (credit liability)
                "debit": Decimal('0'),
                "credit": capital_gain_distribution,
                "description": f"Capital gain distribution payable - {ex_date}"
            })
        
        # Record journal entry
        journal_entry = self.accounting.create_journal_entry(
            entry_date=ex_date,
            description=f"Distribution declaration: ${distribution_calc['distribution_per_share']} per share",
            entries=entries
        )
        
        result = {
            "distribution_date": distribution_date.isoformat(),
            "ex_date": ex_date.isoformat(),
            "record_date": record_date.isoformat(),
            "payable_date": payable_date.isoformat(),
            "distribution_per_share": distribution_calc['distribution_per_share'],
            "total_distribution": str(distribution_amount),
            "journal_entry_id": journal_entry.get('entry_id'),
            "status": "declared"
        }
        
        # Save distribution record
        dist_file = self.storage_path / f"distribution_{ex_date.isoformat()}.json"
        with open(dist_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Distribution declared: ${distribution_calc['distribution_per_share']} per share on {ex_date}")
        
        return result
    
    def record_distribution_payment(self, payable_date: date,
                                   distribution_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record distribution payment (Step 4.2 - payment entry).
        
        Accounting entry on payable date:
        Dr. Distributions Payable
        Cr. Cash
        
        Args:
            payable_date: Payment date
            distribution_record: Distribution record from record_distribution_declaration()
            
        Returns:
            Payment entry details
        """
        distribution_amount = Decimal(str(distribution_record['total_distribution']))
        
        # Create payment journal entry
        payment_entry = self.accounting.create_journal_entry(
            entry_date=payable_date,
            description=f"Distribution payment: ${distribution_record['distribution_per_share']} per share",
            entries=[
                {
                    "account": "2200",  # Distributions Payable (debit to reduce liability)
                    "debit": distribution_amount,
                    "credit": Decimal('0'),
                    "description": f"Distribution payment - {payable_date}"
                },
                {
                    "account": "1000",  # Cash (credit to reduce asset)
                    "debit": Decimal('0'),
                    "credit": distribution_amount,
                    "description": f"Distribution payment - {payable_date}"
                }
            ]
        )
        
        result = {
            "payable_date": payable_date.isoformat(),
            "distribution_per_share": distribution_record['distribution_per_share'],
            "total_payment": str(distribution_amount),
            "journal_entry_id": payment_entry.get('entry_id'),
            "status": "paid"
        }
        
        # Update distribution record
        dist_file = self.storage_path / f"distribution_{distribution_record['ex_date']}.json"
        if dist_file.exists():
            with open(dist_file, 'r') as f:
                dist_data = json.load(f)
            dist_data['payment_date'] = payable_date.isoformat()
            dist_data['payment_entry_id'] = payment_entry.get('entry_id')
            dist_data['status'] = 'paid'
            with open(dist_file, 'w') as f:
                json.dump(dist_data, f, indent=2)
        
        logger.info(f"Distribution paid: ${distribution_amount:,.2f} on {payable_date}")
        
        return result
    
    def _get_account_balance(self, ledger, account_code: str) -> Decimal:
        """Get account balance from ledger"""
        for account in ledger.accounts:
            if hasattr(account, 'account_code') and account.account_code == account_code:
                # Adjust balance based on account type
                if account.account_type in ["asset", "expense"]:
                    return account.balance  # Debit balance is positive
                else:  # liability, equity, income
                    return account.balance  # Credit balance is positive
        return Decimal('0')
    
    def _sum_account_entries(self, ledger, account_code: str, start_date: date, end_date: date) -> Decimal:
        """Sum all credit entries (income) for account in period"""
        total = Decimal('0')
        for account in ledger.accounts:
            if account.account_code == account_code:
                for entry in account.entries:
                    if start_date <= entry.date <= end_date:
                        total += entry.credit  # Income is credited
        return total
    
    def _sum_account_debits(self, ledger, account_code: str, start_date: date, end_date: date) -> Decimal:
        """Sum all debit entries (expenses) for account in period"""
        total = Decimal('0')
        for account in ledger.accounts:
            if account.account_code == account_code:
                for entry in account.entries:
                    if start_date <= entry.date <= end_date:
                        total += entry.debit  # Expenses are debited
        return total

