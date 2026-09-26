"""
Shadow Accounting Comparison Prototype
Independent NAV calculation and monitoring to detect errors in official NAV
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter
from lib.etf.functions.core.administration import FundAdministration

logger = logging.getLogger(__name__)


@dataclass
class ShadowNAVResult:
    """Shadow NAV calculation result"""
    date: date
    shadow_nav_per_share: Decimal
    official_nav_per_share: Optional[Decimal]
    difference: Optional[Decimal]
    difference_percentage: Optional[Decimal]
    status: str  # "match", "warning", "error", "unavailable"
    discrepancies: List[str]
    validation_passed: bool


class ShadowAccounting:
    """
    Shadow Accounting Comparison Prototype
    
    Provides independent NAV calculation to monitor and detect errors in official NAV.
    This is a critical control for ETF operations.
    
    Features:
    - Independent NAV calculation using same methodology as official NAV
    - Daily comparison with official NAV
    - Discrepancy detection and alerting
    - Historical tracking of differences
    - Reconciliation reports
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/shadow_accounting"):
        """
        Initialize Shadow Accounting System
        
        Args:
            data_adapter: DataSourceAdapter for fetching data
            storage_path: Path for storing shadow accounting records
        """
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Use FundAdministration for NAV calculation
        self.admin = FundAdministration(data_adapter, storage_path=str(self.storage_path / "admin"))
        
        # Thresholds for discrepancy detection
        self.warning_threshold = Decimal('0.01')  # percent: 1 basis point
        self.error_threshold = Decimal('0.1')     # percent: 10 basis points
    
    def calculate_shadow_nav(self, nav_date: date, official_nav: Optional[Decimal] = None) -> ShadowNAVResult:
        """
        Calculate shadow NAV independently and compare with official NAV
        
        Args:
            nav_date: Date for NAV calculation
            official_nav: Explicit independent official NAV; None leaves comparison unavailable
            
        Returns:
            ShadowNAVResult with comparison
        """
        logger.info(f"Calculating shadow NAV for {nav_date}")
        
        # Calculate shadow NAV using same methodology as official
        shadow_nav_calc = self.admin.calculate_nav(nav_date)
        shadow_nav_per_share = shadow_nav_calc.nav_per_share
        
        # A missing official observation is not a successful reconciliation.
        difference = None
        difference_percentage = None
        discrepancies = []
        status = "unavailable"
        if official_nav is None:
            discrepancies.append("Official NAV not supplied; comparison unavailable")
        else:
            try:
                official_nav = Decimal(str(official_nav))
                if not official_nav.is_finite() or official_nav <= 0:
                    raise ValueError("Official NAV must be a positive finite number")
            except (ValueError, ArithmeticError):
                official_nav = None
                status = "error"
                discrepancies.append("Official NAV must be a positive finite number")
            else:
                if shadow_nav_per_share.is_finite():
                    difference = abs(shadow_nav_per_share - official_nav)
                    difference_percentage = difference / official_nav * Decimal('100')
                    if difference_percentage >= self.error_threshold:
                        status = "error"
                    elif difference_percentage >= self.warning_threshold:
                        status = "warning"
                    else:
                        status = "match"
                    if status != "match":
                        discrepancies.append(f"NAV difference {difference_percentage:.4f}%: {status}")
                else:
                    status = "error"
                    discrepancies.append("Shadow NAV must be finite")

        if not shadow_nav_calc.validation_passed or not shadow_nav_per_share.is_finite():
            status = "error"
            discrepancies.append("Shadow NAV calculation validation failed")
        if shadow_nav_calc.pricing_exceptions:
            # Never downgrade an error or turn an unavailable comparison into a pass.
            if status == "match":
                status = "warning"
            discrepancies.append(f"Pricing exceptions: {shadow_nav_calc.pricing_exceptions}")

        result = ShadowNAVResult(
            date=nav_date,
            shadow_nav_per_share=shadow_nav_per_share,
            official_nav_per_share=official_nav,
            difference=difference,
            difference_percentage=difference_percentage,
            status=status,
            discrepancies=discrepancies,
            validation_passed=shadow_nav_calc.validation_passed and status in {"match", "warning"}
        )
        
        # Save shadow NAV record
        self._save_shadow_nav_record(result, shadow_nav_calc)
        
        if status == "error":
            logger.error(f"Shadow NAV error detected: {discrepancies}")
        elif status == "warning":
            logger.warning(f"Shadow NAV warning: {discrepancies}")
        elif status == "match":
            logger.info(f"Shadow NAV matches official NAV (difference: {difference_percentage:.4f}%)")
        else:
            logger.info("Official NAV comparison unavailable")
        
        return result
    
    def reconcile_shadow_vs_official(self, nav_date: date, official_nav: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Comprehensive reconciliation between shadow NAV and official NAV
        
        Args:
            nav_date: Date to reconcile
            
        Returns:
            Reconciliation report
        """
        logger.info(f"Reconciling shadow NAV vs official NAV for {nav_date}")
        
        shadow_result = self.calculate_shadow_nav(nav_date, official_nav=official_nav)
        
        # Get detailed breakdown
        shadow_nav_calc = self.admin.calculate_nav(nav_date)
        
        reconciliation = {
            "date": nav_date.isoformat(),
            "shadow_nav": {
                "nav_per_share": str(shadow_result.shadow_nav_per_share),
                "total_assets": str(shadow_nav_calc.total_assets),
                "total_liabilities": str(shadow_nav_calc.total_liabilities),
                "net_assets": str(shadow_nav_calc.net_assets),
                "shares_outstanding": str(shadow_nav_calc.shares_outstanding)
            },
            "official_nav": {
                "nav_per_share": (str(shadow_result.official_nav_per_share) if shadow_result.official_nav_per_share is not None else None),
                # TODO: Fetch official breakdown from custodian
            },
            "comparison": {
                "difference": (str(shadow_result.difference) if shadow_result.difference is not None else None),
                "difference_percentage": (str(shadow_result.difference_percentage) if shadow_result.difference_percentage is not None else None),
                "status": shadow_result.status
            },
            "discrepancies": shadow_result.discrepancies,
            "validation_passed": shadow_result.validation_passed
        }
        
        # Save reconciliation report
        recon_file = self.storage_path / f"nav_reconciliation_{nav_date.isoformat()}.json"
        with open(recon_file, 'w') as f:
            json.dump(reconciliation, f, indent=2, default=str)
        
        return reconciliation
    
    def monitor_nav_trends(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Monitor NAV trends and detect anomalies
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Trend analysis report
        """
        logger.info(f"Monitoring NAV trends from {start_date} to {end_date}")
        
        # Calculate shadow NAV for each day in range
        trends = []
        total_days = 0
        error_days = 0
        warning_days = 0
        unavailable_days = 0
        
        current_date = start_date
        while current_date <= end_date:
            try:
                result = self.calculate_shadow_nav(current_date)
                trends.append({
                    "date": current_date.isoformat(),
                    "shadow_nav": str(result.shadow_nav_per_share),
                    "official_nav": (str(result.official_nav_per_share) if result.official_nav_per_share is not None else None),
                    "difference_percentage": (str(result.difference_percentage) if result.difference_percentage is not None else None),
                    "status": result.status
                })
                
                total_days += 1
                if result.status == "error":
                    error_days += 1
                elif result.status == "warning":
                    warning_days += 1
                elif result.status == "unavailable":
                    unavailable_days += 1
            except Exception as e:
                logger.error(f"Error calculating shadow NAV for {current_date}: {e}")
            
            from datetime import timedelta
            current_date += timedelta(days=1)
        
        # Missing comparisons must not appear as zero-error observations.
        differences = [Decimal(t["difference_percentage"]) for t in trends
                       if t["difference_percentage"] is not None]
        avg_difference = sum(differences) / len(differences) if differences else None
        max_difference = max(differences) if differences else None
        min_difference = min(differences) if differences else None

        report = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_days": total_days,
            "error_days": error_days,
            "warning_days": warning_days,
            "unavailable_days": unavailable_days,
            "compared_days": len(differences),
            "match_days": total_days - error_days - warning_days - unavailable_days,
            "statistics": {
                "average_difference_percentage": (str(avg_difference) if avg_difference is not None else None),
                "max_difference_percentage": (str(max_difference) if max_difference is not None else None),
                "min_difference_percentage": (str(min_difference) if min_difference is not None else None)
            },
            "trends": trends
        }
        
        # Save trend report
        trend_file = self.storage_path / f"nav_trends_{start_date.isoformat()}_{end_date.isoformat()}.json"
        with open(trend_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report
    
    def _save_shadow_nav_record(self, result: ShadowNAVResult, nav_calc):
        """Save shadow NAV record for audit trail"""
        record = {
            "date": result.date.isoformat(),
            "shadow_nav_per_share": str(result.shadow_nav_per_share),
            "official_nav_per_share": (str(result.official_nav_per_share) if result.official_nav_per_share is not None else None),
            "difference": (str(result.difference) if result.difference is not None else None),
            "difference_percentage": (str(result.difference_percentage) if result.difference_percentage is not None else None),
            "status": result.status,
            "discrepancies": result.discrepancies,
            "validation_passed": result.validation_passed,
            "nav_calculation_details": {
                "total_assets": str(nav_calc.total_assets),
                "total_liabilities": str(nav_calc.total_liabilities),
                "net_assets": str(nav_calc.net_assets),
                "shares_outstanding": str(nav_calc.shares_outstanding)
            }
        }
        
        record_file = self.storage_path / f"shadow_nav_{result.date.isoformat()}.json"
        with open(record_file, 'w') as f:
            json.dump(record, f, indent=2, default=str)

