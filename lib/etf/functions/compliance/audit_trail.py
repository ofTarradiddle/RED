"""
Audit Trail Management
Ensures all accounting and admin operations save complete audit records
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from decimal import Decimal
from pathlib import Path
from dataclasses import dataclass, field, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Individual audit record"""
    record_id: str
    record_type: str  # "nav_calculation", "journal_entry", "reconciliation", etc.
    record_date: date
    operation: str  # Description of operation
    data: Dict[str, Any]  # Complete data snapshot
    user: Optional[str] = None
    system: Optional[str] = None
    timestamp: Optional[str] = None
    related_records: List[str] = field(default_factory=list)  # Links to related records


class AuditTrailManager:
    """
    Production-ready Audit Trail Manager
    
    Ensures all operations are logged for audit purposes.
    SEC Rule 31a-2 requires maintaining complete books and records.
    
    Example:
        >>> audit = AuditTrailManager(storage_path="./data/audit_trail")
        >>> audit.log_operation(
        ...     record_type="nav_calculation",
        ...     record_date=date.today(),
        ...     operation="Daily NAV calculation",
        ...     data=nav_calculation_data
        ... )
    """
    
    def __init__(self, storage_path: str = "./data/audit_trail"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.records: List[AuditRecord] = []
        self._load_records()
    
    def _load_records(self):
        """Load audit records from storage"""
        records_file = self.storage_path / "audit_records.json"
        if records_file.exists():
            try:
                with open(records_file, 'r') as f:
                    data = json.load(f)
                    for record_data in data:
                        record_data['record_date'] = date.fromisoformat(record_data['record_date'])
                        self.records.append(AuditRecord(**record_data))
                logger.info(f"Loaded {len(self.records)} audit records")
            except Exception as e:
                logger.error(f"Error loading audit records: {e}")
                self.records = []
    
    def _save_records(self):
        """Save audit records to storage"""
        records_file = self.storage_path / "audit_records.json"
        try:
            data = []
            for record in self.records:
                record_dict = asdict(record)
                record_dict['record_date'] = record.record_date.isoformat()
                # Convert Decimal to string for JSON
                data.append(self._serialize_data(record_dict))
            
            with open(records_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved {len(self.records)} audit records")
        except Exception as e:
            logger.error(f"Error saving audit records: {e}")
    
    def _serialize_data(self, obj):
        """Recursively serialize data for JSON (handle Decimal, date, etc.)"""
        if isinstance(obj, dict):
            return {k: self._serialize_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_data(item) for item in obj]
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, date):
            return obj.isoformat()
        else:
            return obj
    
    def log_operation(self, record_type: str, record_date: date,
                     operation: str, data: Dict[str, Any],
                     user: Optional[str] = None,
                     related_records: Optional[List[str]] = None) -> AuditRecord:
        """
        Log an operation for audit trail
        
        Args:
            record_type: Type of record (nav_calculation, journal_entry, etc.)
            record_date: Date of operation
            operation: Description of operation
            data: Complete data snapshot
            user: User who performed operation
            related_records: List of related record IDs
            
        Returns:
            AuditRecord object
        """
        from datetime import datetime
        
        record_id = f"{record_type}_{record_date.isoformat()}_{len(self.records)}"
        
        record = AuditRecord(
            record_id=record_id,
            record_type=record_type,
            record_date=record_date,
            operation=operation,
            data=self._serialize_data(data),
            user=user,
            system="ETF_Admin_System",
            timestamp=datetime.now().isoformat(),
            related_records=related_records or []
        )
        
        self.records.append(record)
        self._save_records()
        
        # Also save individual record file for easy access
        record_file = self.storage_path / f"{record_type}_{record_date.isoformat()}_{record_id}.json"
        with open(record_file, 'w') as f:
            json.dump(asdict(record), f, indent=2, default=str)
        
        logger.info(f"Logged audit record: {record_id} - {operation}")
        return record
    
    def get_records_by_type(self, record_type: str, start_date: Optional[date] = None,
                           end_date: Optional[date] = None) -> List[AuditRecord]:
        """Get audit records by type and date range"""
        records = [r for r in self.records if r.record_type == record_type]
        
        if start_date:
            records = [r for r in records if r.record_date >= start_date]
        if end_date:
            records = [r for r in records if r.record_date <= end_date]
        
        return sorted(records, key=lambda x: x.record_date)
    
    def get_records_by_date(self, record_date: date) -> List[AuditRecord]:
        """Get all audit records for a specific date"""
        return [r for r in self.records if r.record_date == record_date]
    
    def export_audit_package(self, start_date: date, end_date: date,
                           output_path: Optional[Path] = None) -> Path:
        """
        Export complete audit package for date range
        
        SEC Rule 31a-2 requires maintaining complete books and records.
        This exports everything needed for an audit.
        """
        if output_path is None:
            output_path = self.storage_path / f"audit_package_{start_date.isoformat()}_{end_date.isoformat()}.json"
        
        records = [r for r in self.records 
                  if start_date <= r.record_date <= end_date]
        
        package = {
            "export_date": date.today().isoformat(),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_records": len(records),
            "records_by_type": {},
            "records": [asdict(r) for r in records]
        }
        
        # Group by type
        for record in records:
            if record.record_type not in package["records_by_type"]:
                package["records_by_type"][record.record_type] = 0
            package["records_by_type"][record.record_type] += 1
        
        with open(output_path, 'w') as f:
            json.dump(package, f, indent=2, default=str)
        
        logger.info(f"Exported audit package: {len(records)} records to {output_path}")
        return output_path

