"""
Production-Ready Distributor Function
Complete implementation with all business logic
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class DistributionRecord:
    """Distribution record"""
    distribution_id: str
    distribution_type: str  # "dividend", "capital_gains", "return_of_capital"
    record_date: date
    ex_date: date
    pay_date: date
    amount_per_share: Decimal
    total_amount: Decimal
    shares_outstanding: Decimal
    status: str = "pending"  # "pending", "declared", "paid"


class Distributor:
    """Production-ready Distributor implementation"""
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/distributor"):
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.distributions: List[DistributionRecord] = []
        self.load_distributions()
    
    def load_distributions(self):
        """Load distribution records from storage"""
        dist_file = self.storage_path / "distributions.json"
        if dist_file.exists():
            try:
                with open(dist_file, 'r') as f:
                    data = json.load(f)
                    self.distributions = [
                        DistributionRecord(
                            distribution_id=d['distribution_id'],
                            distribution_type=d['distribution_type'],
                            record_date=date.fromisoformat(d['record_date']),
                            ex_date=date.fromisoformat(d['ex_date']),
                            pay_date=date.fromisoformat(d['pay_date']),
                            amount_per_share=Decimal(str(d['amount_per_share'])),
                            total_amount=Decimal(str(d['total_amount'])),
                            shares_outstanding=Decimal(str(d['shares_outstanding'])),
                            status=d['status']
                        )
                        for d in data
                    ]
                logger.info(f"Loaded {len(self.distributions)} distribution records")
            except Exception as e:
                logger.error(f"Error loading distributions: {e}")
                self.distributions = []
    
    def save_distributions(self):
        """Save distribution records to storage"""
        dist_file = self.storage_path / "distributions.json"
        try:
            data = [
                {
                    "distribution_id": d.distribution_id,
                    "distribution_type": d.distribution_type,
                    "record_date": d.record_date.isoformat(),
                    "ex_date": d.ex_date.isoformat(),
                    "pay_date": d.pay_date.isoformat(),
                    "amount_per_share": str(d.amount_per_share),
                    "total_amount": str(d.total_amount),
                    "shares_outstanding": str(d.shares_outstanding),
                    "status": d.status
                }
                for d in self.distributions
            ]
            with open(dist_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.distributions)} distribution records")
        except Exception as e:
            logger.error(f"Error saving distributions: {e}")
    
    def calculate_distribution(self, dist_date: date, distribution_type: str, 
                             nav_data: Dict[str, Any]) -> DistributionRecord:
        """Calculate distribution amount"""
        logger.info(f"Calculating {distribution_type} distribution for {dist_date}")
        
        try:
            distribution_data = self.data_adapter.get_distribution_data(dist_date)
        except Exception as e:
            logger.error(f"Error fetching distribution data: {e}")
            raise
        
        shares_outstanding = Decimal(str(nav_data.get('shares_outstanding', 0)))
        
        if distribution_type == "dividend":
            amount_per_share = Decimal(str(distribution_data.get('dividend_per_share', 0)))
        elif distribution_type == "capital_gains":
            amount_per_share = Decimal(str(distribution_data.get('capital_gains_per_share', 0)))
        elif distribution_type == "return_of_capital":
            amount_per_share = Decimal(str(distribution_data.get('roc_per_share', 0)))
        else:
            raise ValueError(f"Unknown distribution type: {distribution_type}")
        
        total_amount = amount_per_share * shares_outstanding
        
        # Set dates (typically ex-date is record date, pay date is 1-2 days later)
        record_date = dist_date
        ex_date = dist_date
        pay_date = dist_date + timedelta(days=2)
        
        distribution_id = f"DIST_{distribution_type.upper()}_{dist_date.isoformat()}"
        
        distribution = DistributionRecord(
            distribution_id=distribution_id,
            distribution_type=distribution_type,
            record_date=record_date,
            ex_date=ex_date,
            pay_date=pay_date,
            amount_per_share=amount_per_share,
            total_amount=total_amount,
            shares_outstanding=shares_outstanding,
            status="pending"
        )
        
        self.distributions.append(distribution)
        self.save_distributions()
        
        logger.info(f"Distribution calculated: ${amount_per_share} per share, Total: ${total_amount}")
        return distribution
    
    def declare_distribution(self, distribution: DistributionRecord) -> Dict[str, Any]:
        """Declare distribution to shareholders"""
        logger.info(f"Declaring distribution {distribution.distribution_id}")
        
        distribution.status = "declared"
        self.save_distributions()
        
        # Generate distribution notice
        notice = {
            "distribution_id": distribution.distribution_id,
            "distribution_type": distribution.distribution_type,
            "record_date": distribution.record_date.isoformat(),
            "ex_date": distribution.ex_date.isoformat(),
            "pay_date": distribution.pay_date.isoformat(),
            "amount_per_share": str(distribution.amount_per_share),
            "total_amount": str(distribution.total_amount),
            "shares_outstanding": str(distribution.shares_outstanding),
            "status": distribution.status
        }
        
        # Save distribution notice
        notice_file = self.storage_path / f"distribution_notice_{distribution.distribution_id}.json"
        with open(notice_file, 'w') as f:
            json.dump(notice, f, indent=2)
        
        logger.info(f"Distribution {distribution.distribution_id} declared")
        return notice
    
    def process_distribution_payment(self, distribution: DistributionRecord, 
                                   shareholder_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process distribution payment to shareholders"""
        logger.info(f"Processing distribution payment {distribution.distribution_id}")
        
        if distribution.status != "declared":
            raise ValueError(f"Distribution {distribution.distribution_id} not declared")
        
        payment_records = []
        total_paid = Decimal('0')
        
        for shareholder in shareholder_data:
            shares = Decimal(str(shareholder.get('shares', 0)))
            payment_amount = shares * distribution.amount_per_share
            
            payment_records.append({
                "account_number": shareholder.get('account_number'),
                "shareholder_name": shareholder.get('shareholder_name'),
                "shares": str(shares),
                "amount_per_share": str(distribution.amount_per_share),
                "payment_amount": str(payment_amount)
            })
            
            total_paid += payment_amount
        
        # Verify total
        if abs(total_paid - distribution.total_amount) > Decimal('0.01'):
            logger.warning(f"Payment total mismatch: Expected={distribution.total_amount}, Actual={total_paid}")
        
        distribution.status = "paid"
        self.save_distributions()
        
        result = {
            "distribution_id": distribution.distribution_id,
            "payments_processed": len(payment_records),
            "total_paid": str(total_paid),
            "expected_total": str(distribution.total_amount),
            "payments": payment_records
        }
        
        # Save payment records
        payment_file = self.storage_path / f"payment_{distribution.distribution_id}.json"
        with open(payment_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Distribution payment processed: {len(payment_records)} payments, ${total_paid} total")
        return result
    
    def generate_distribution_schedule(self, year: int) -> Dict[str, Any]:
        """Generate distribution schedule for the year"""
        logger.info(f"Generating distribution schedule for {year}")
        
        year_distributions = [
            d for d in self.distributions
            if d.record_date.year == year
        ]
        
        schedule = {
            "year": year,
            "total_distributions": len(year_distributions),
            "total_amount": str(sum(d.total_amount for d in year_distributions)),
            "distributions": [
                {
                    "distribution_id": d.distribution_id,
                    "type": d.distribution_type,
                    "record_date": d.record_date.isoformat(),
                    "ex_date": d.ex_date.isoformat(),
                    "pay_date": d.pay_date.isoformat(),
                    "amount_per_share": str(d.amount_per_share),
                    "total_amount": str(d.total_amount),
                    "status": d.status
                }
                for d in sorted(year_distributions, key=lambda x: x.record_date)
            ]
        }
        
        # Save schedule
        schedule_file = self.storage_path / f"distribution_schedule_{year}.json"
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        return schedule
    
    def get_pending_distributions(self, as_of_date: date) -> List[DistributionRecord]:
        """Get pending distributions as of date"""
        return [
            d for d in self.distributions
            if d.status == "pending" and d.record_date <= as_of_date
        ]
    
    def get_distributions_due(self, as_of_date: date) -> List[DistributionRecord]:
        """Get distributions due for payment as of date"""
        return [
            d for d in self.distributions
            if d.status == "declared" and d.pay_date <= as_of_date
        ]

