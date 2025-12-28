"""
Capital Gain Dividend Estimates
Production-ready implementation for capital gain dividend estimates (Limited to two per year)

This module handles:
- Capital gain dividend estimates
- Estimated distribution calculations
- Shareholder communication
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
class CapitalGainEstimate:
    """Capital gain dividend estimate"""
    estimate_date: date
    estimate_type: str  # "mid-year", "year-end", "final"
    estimated_long_term_gains: Decimal
    estimated_short_term_gains: Decimal
    estimated_total_gains: Decimal
    estimated_per_share: Decimal
    shares_outstanding: Decimal
    estimated_total_distribution: Decimal
    distribution_date: Optional[date] = None
    final_actual_amount: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapitalGainEstimates:
    """
    Production-ready Capital Gain Dividend Estimates
    
    Handles capital gain dividend estimates (limited to two per year).
    Typically provided mid-year and year-end to help shareholders plan.
    
    Example:
        >>> estimates = CapitalGainEstimates(storage_path="./data/capital_gain_estimates")
        >>> estimate = estimates.create_estimate(
        ...     estimate_date=date(2024, 6, 30),
        ...     estimated_long_term_gains=Decimal('500000'),
        ...     estimated_short_term_gains=Decimal('100000'),
        ...     shares_outstanding=Decimal('1000000')
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/capital_gain_estimates"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.estimates: List[CapitalGainEstimate] = []
        self.max_estimates_per_year = 2
    
    def create_estimate(self, estimate_date: date,
                       estimated_long_term_gains: Decimal,
                       estimated_short_term_gains: Decimal,
                       shares_outstanding: Decimal,
                       distribution_date: Optional[date] = None,
                       estimate_type: str = "mid-year") -> CapitalGainEstimate:
        """
        Create capital gain dividend estimate
        
        Args:
            estimate_date: Date of estimate
            estimated_long_term_gains: Estimated long-term capital gains
            estimated_short_term_gains: Estimated short-term capital gains
            shares_outstanding: Shares outstanding
            distribution_date: Expected distribution date
            estimate_type: Type of estimate ("mid-year", "year-end", "final")
            
        Returns:
            CapitalGainEstimate object
        """
        logger.info(f"Creating capital gain estimate for {estimate_date}")
        
        # Check estimate limit
        year_estimates = [e for e in self.estimates if e.estimate_date.year == estimate_date.year]
        if len(year_estimates) >= self.max_estimates_per_year:
            logger.warning(f"Maximum estimates per year ({self.max_estimates_per_year}) reached for {estimate_date.year}")
        
        estimated_total_gains = estimated_long_term_gains + estimated_short_term_gains
        
        # Calculate per-share estimate
        if shares_outstanding > 0:
            estimated_per_share = estimated_total_gains / shares_outstanding
        else:
            estimated_per_share = Decimal('0')
        
        estimated_total_distribution = estimated_total_gains
        
        estimate = CapitalGainEstimate(
            estimate_date=estimate_date,
            estimate_type=estimate_type,
            estimated_long_term_gains=estimated_long_term_gains,
            estimated_short_term_gains=estimated_short_term_gains,
            estimated_total_gains=estimated_total_gains,
            estimated_per_share=estimated_per_share,
            shares_outstanding=shares_outstanding,
            estimated_total_distribution=estimated_total_distribution,
            distribution_date=distribution_date,
            metadata={
                "estimate_basis": "Based on realized gains through estimate date",
                "disclaimer": "Estimate is subject to change based on market conditions and portfolio activity"
            }
        )
        
        # Save estimate
        self._save_estimate(estimate)
        self.estimates.append(estimate)
        
        logger.info(f"Created capital gain estimate: ${estimated_total_gains} total, "
                   f"${estimated_per_share} per share")
        
        return estimate
    
    def update_estimate_with_actual(self, estimate: CapitalGainEstimate,
                                   actual_amount: Decimal):
        """
        Update estimate with actual distribution amount
        
        Args:
            estimate: CapitalGainEstimate to update
            actual_amount: Actual distribution amount
        """
        estimate.final_actual_amount = actual_amount
        estimate.variance = actual_amount - estimate.estimated_total_distribution
        
        self._save_estimate(estimate)
        
        logger.info(f"Updated estimate: Actual=${actual_amount}, "
                   f"Variance=${estimate.variance}")
    
    def _save_estimate(self, estimate: CapitalGainEstimate):
        """Save estimate to storage"""
        estimate_file = self.storage_path / f"capital_gain_estimate_{estimate.estimate_date.isoformat()}.json"
        try:
            data = {
                "estimate_date": estimate.estimate_date.isoformat(),
                "estimate_type": estimate.estimate_type,
                "estimated_long_term_gains": str(estimate.estimated_long_term_gains),
                "estimated_short_term_gains": str(estimate.estimated_short_term_gains),
                "estimated_total_gains": str(estimate.estimated_total_gains),
                "estimated_per_share": str(estimate.estimated_per_share),
                "shares_outstanding": str(estimate.shares_outstanding),
                "estimated_total_distribution": str(estimate.estimated_total_distribution),
                "distribution_date": estimate.distribution_date.isoformat() if estimate.distribution_date else None,
                "final_actual_amount": str(estimate.final_actual_amount) if estimate.final_actual_amount else None,
                "variance": str(estimate.variance) if estimate.variance else None,
                "metadata": estimate.metadata
            }
            with open(estimate_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved capital gain estimate to {estimate_file}")
        except Exception as e:
            logger.error(f"Error saving capital gain estimate: {e}")

