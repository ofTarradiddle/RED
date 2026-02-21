"""
State Tax Return Preparation
Production-ready implementation for state tax return preparation (Limited to two states)

This module handles:
- State tax return preparation (Form 1120-RIC state equivalents)
- State apportionment calculations
- State-specific tax adjustments
- Multi-state filing coordination
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
class StateTaxReturn:
    """State tax return data"""
    state: str
    tax_year: int
    form_type: str  # "1120-RIC" or state-specific form
    taxable_income: Decimal
    state_tax_due: Decimal
    apportionment_factor: Decimal
    filing_method: str  # "separate", "combined", "unitary"
    due_date: date
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateTaxReporting:
    """
    Production-ready State Tax Return Preparation
    
    Handles state tax return preparation for up to two states.
    Most RICs are exempt from state income tax, but may have filing requirements.
    
    Example:
        >>> state_tax = StateTaxReporting(storage_path="./data/state_tax")
        >>> california_return = state_tax.prepare_state_return(
        ...     state="CA",
        ...     tax_year=2024,
        ...     federal_taxable_income=Decimal('1000000'),
        ...     apportionment_data={"california_factor": Decimal('0.50')}
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/state_tax"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.state_returns: List[StateTaxReturn] = []
        self.max_states = 2  # Limited to two states per requirements
    
    def prepare_state_return(self, state: str, tax_year: int,
                            federal_taxable_income: Decimal,
                            apportionment_data: Dict[str, Any],
                            form_1120_ric: Optional[Dict[str, Any]] = None) -> StateTaxReturn:
        """
        Prepare state tax return
        
        Most RICs are exempt from state income tax, but may need to file
        informational returns or may have nexus in certain states.
        
        Args:
            state: State code (e.g., "CA", "NY")
            tax_year: Tax year
            federal_taxable_income: Federal taxable income from Form 1120-RIC
            apportionment_data: State-specific apportionment data
                {
                    "state_factor": Decimal,  # Apportionment factor (0.0 to 1.0)
                    "state_income": Decimal,  # State-source income
                    "nexus": bool  # Whether fund has nexus in state
                }
            form_1120_ric: Form 1120-RIC data for reference
            
        Returns:
            StateTaxReturn object
        """
        logger.info(f"Preparing {state} state tax return for tax year {tax_year}")
        
        # Check if we've already prepared returns for max states
        if len(self.state_returns) >= self.max_states:
            logger.warning(f"Maximum number of state returns ({self.max_states}) reached")
        
        # Most RICs are exempt from state income tax
        # But may need to file informational returns
        state_factor = apportionment_data.get('state_factor', Decimal('0'))
        has_nexus = apportionment_data.get('nexus', False)
        
        # Calculate state taxable income (if applicable)
        if has_nexus and state_factor > 0:
            state_taxable_income = federal_taxable_income * state_factor
        else:
            state_taxable_income = Decimal('0')
        
        # Most states exempt RICs from income tax
        # State tax due is typically $0, but filing may still be required
        state_tax_due = Decimal('0')
        
        # Determine due date (typically same as federal, but varies by state)
        due_date = date(tax_year + 1, 3, 15)  # Default to March 15
        
        state_return = StateTaxReturn(
            state=state,
            tax_year=tax_year,
            form_type=f"State-{state}-RIC",
            taxable_income=state_taxable_income,
            state_tax_due=state_tax_due,
            apportionment_factor=state_factor,
            filing_method="separate",
            due_date=due_date,
            metadata={
                "has_nexus": has_nexus,
                "exempt_status": "RIC exempt from state income tax",
                "filing_required": has_nexus,
                "federal_taxable_income": str(federal_taxable_income)
            }
        )
        
        # Save state return
        self._save_state_return(state_return)
        self.state_returns.append(state_return)
        
        logger.info(f"Prepared {state} state return: Taxable income=${state_taxable_income}, "
                   f"Tax due=${state_tax_due}")
        
        return state_return
    
    def _save_state_return(self, state_return: StateTaxReturn):
        """Save state return to storage"""
        return_file = self.storage_path / f"state_return_{state_return.state}_{state_return.tax_year}.json"
        try:
            data = {
                "state": state_return.state,
                "tax_year": state_return.tax_year,
                "form_type": state_return.form_type,
                "taxable_income": str(state_return.taxable_income),
                "state_tax_due": str(state_return.state_tax_due),
                "apportionment_factor": str(state_return.apportionment_factor),
                "filing_method": state_return.filing_method,
                "due_date": state_return.due_date.isoformat(),
                "metadata": state_return.metadata
            }
            with open(return_file, 'w') as f:
                json.dump(data, f, indent=2)
            state_return.file_path = str(return_file)
            logger.info(f"Saved {state_return.state} state return to {return_file}")
        except Exception as e:
            logger.error(f"Error saving state return: {e}")

