"""
TDF FBAR Filing (Foreign Bank Account Report)
Production-ready implementation for Annual TDF FBAR filing

This module handles:
- FBAR filing requirements for foreign accounts
- Foreign account reporting
- Treasury Department filing
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
class ForeignAccount:
    """Foreign account information"""
    account_number: str
    account_name: str
    bank_name: str
    country: str
    account_type: str  # "checking", "savings", "securities", "other"
    max_balance: Decimal
    currency: str
    account_open_date: Optional[date] = None
    account_close_date: Optional[date] = None


@dataclass
class FBARFiling:
    """FBAR filing record"""
    filing_year: int
    filing_date: date
    foreign_accounts: List[ForeignAccount]
    total_max_balance_usd: Decimal
    filing_required: bool
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class FBARFilingSystem:
    """
    Production-ready TDF FBAR Filing System
    
    Handles annual FBAR (Foreign Bank Account Report) filing with Treasury Department.
    Required if fund has foreign accounts with aggregate maximum value > $10,000 USD.
    
    Example:
        >>> fbar = FBARFilingSystem(storage_path="./data/fbar")
        >>> filing = fbar.prepare_fbar_filing(
        ...     filing_year=2024,
        ...     foreign_accounts=accounts_list
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/fbar"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.fbar_filings: Dict[int, FBARFiling] = {}
        self.filing_threshold = Decimal('10000')  # $10,000 USD threshold
    
    def prepare_fbar_filing(self, filing_year: int,
                           foreign_accounts: List[ForeignAccount],
                           exchange_rates: Optional[Dict[str, Decimal]] = None) -> FBARFiling:
        """
        Prepare annual FBAR filing
        
        FBAR (FinCEN Form 114) must be filed if aggregate maximum value
        of all foreign accounts exceeds $10,000 USD at any time during the year.
        
        Args:
            filing_year: Year for which filing is prepared
            foreign_accounts: List of ForeignAccount objects
            exchange_rates: Optional exchange rates for currency conversion
                {
                    "EUR": Decimal('1.10'),
                    "GBP": Decimal('1.25'),
                    ...
                }
            
        Returns:
            FBARFiling object
        """
        logger.info(f"Preparing FBAR filing for year {filing_year}")
        
        # Default exchange rates (USD = 1.0)
        if exchange_rates is None:
            exchange_rates = {"USD": Decimal('1.0')}
        
        # Convert all account balances to USD
        total_max_balance_usd = Decimal('0')
        for account in foreign_accounts:
            if account.currency == "USD":
                account_usd = account.max_balance
            else:
                rate = exchange_rates.get(account.currency, Decimal('1.0'))
                account_usd = account.max_balance * rate
            total_max_balance_usd += account_usd
        
        # Determine if filing is required
        filing_required = total_max_balance_usd > self.filing_threshold
        
        filing = FBARFiling(
            filing_year=filing_year,
            filing_date=date.today(),
            foreign_accounts=foreign_accounts,
            total_max_balance_usd=total_max_balance_usd,
            filing_required=filing_required,
            metadata={
                "filing_threshold": str(self.filing_threshold),
                "accounts_count": len(foreign_accounts),
                "filing_deadline": date(filing_year + 1, 4, 15).isoformat(),  # April 15
                "filing_method": "Electronic (FinCEN BSA E-Filing System)"
            }
        )
        
        # Save filing
        self._save_fbar_filing(filing)
        self.fbar_filings[filing_year] = filing
        
        if filing_required:
            logger.info(f"FBAR filing required: Total max balance=${total_max_balance_usd} "
                       f"(exceeds ${self.filing_threshold} threshold)")
        else:
            logger.info(f"FBAR filing not required: Total max balance=${total_max_balance_usd} "
                       f"(below ${self.filing_threshold} threshold)")
        
        return filing
    
    def _save_fbar_filing(self, filing: FBARFiling):
        """Save FBAR filing to storage"""
        filing_file = self.storage_path / f"fbar_filing_{filing.filing_year}.json"
        try:
            data = {
                "filing_year": filing.filing_year,
                "filing_date": filing.filing_date.isoformat(),
                "total_max_balance_usd": str(filing.total_max_balance_usd),
                "filing_required": filing.filing_required,
                "foreign_accounts": [
                    {
                        "account_number": acc.account_number,
                        "account_name": acc.account_name,
                        "bank_name": acc.bank_name,
                        "country": acc.country,
                        "account_type": acc.account_type,
                        "max_balance": str(acc.max_balance),
                        "currency": acc.currency,
                        "account_open_date": acc.account_open_date.isoformat() if acc.account_open_date else None,
                        "account_close_date": acc.account_close_date.isoformat() if acc.account_close_date else None
                    }
                    for acc in filing.foreign_accounts
                ],
                "metadata": filing.metadata
            }
            with open(filing_file, 'w') as f:
                json.dump(data, f, indent=2)
            filing.file_path = str(filing_file)
            logger.info(f"Saved FBAR filing to {filing_file}")
        except Exception as e:
            logger.error(f"Error saving FBAR filing: {e}")

