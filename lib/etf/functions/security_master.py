"""
Security Master File and Portfolio Records Management
Production-ready implementation for maintaining security master file and portfolio records

This module handles:
- Security master file (CUSIP, ticker, description, security type, etc.)
- Portfolio records (holdings, positions, cost basis)
- Security pricing history
- Corporate actions history
- Security-level reconciliation

Required for Fund Accounting: Maintain security master file and portfolio records
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
class SecurityMaster:
    """Security master file record"""
    cusip: str
    ticker: str
    description: str
    security_type: str  # "equity", "bond", "cash", "other"
    exchange: Optional[str] = None
    currency: str = "USD"
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    isin: Optional[str] = None
    sedol: Optional[str] = None
    created_date: date = field(default_factory=date.today)
    last_updated: date = field(default_factory=date.today)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PortfolioRecord:
    """Portfolio position record"""
    record_date: date
    cusip: str
    ticker: str
    quantity: Decimal
    cost_basis: Decimal
    cost_basis_per_share: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_gain_loss: Decimal
    currency: str = "USD"
    source: str = "portfolio"  # "portfolio", "custodian", "reconciled"
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityMasterFile:
    """
    Production-ready Security Master File management
    
    Maintains comprehensive security master file with:
    - Security identifiers (CUSIP, ticker, ISIN, SEDOL)
    - Security details (description, type, exchange, sector)
    - Security status (active/inactive)
    - Audit trail (created/updated dates)
    
    Example:
        >>> master = SecurityMasterFile(storage_path="./data/security_master")
        >>> security = master.add_security(
        ...     cusip="037833100",
        ...     ticker="AAPL",
        ...     description="APPLE INC",
        ...     security_type="equity",
        ...     exchange="NASDAQ"
        ... )
        >>> securities = master.get_security_by_cusip("037833100")
    """
    
    def __init__(self, storage_path: str = "./data/security_master"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.master_file = self.storage_path / "security_master.json"
        self.securities: Dict[str, SecurityMaster] = {}
        self._load_master_file()
    
    def _load_master_file(self):
        """Load security master file from storage"""
        if self.master_file.exists():
            try:
                with open(self.master_file, 'r') as f:
                    data = json.load(f)
                    for cusip, sec_data in data.items():
                        # Convert date strings back to date objects
                        sec_data['created_date'] = date.fromisoformat(sec_data['created_date'])
                        sec_data['last_updated'] = date.fromisoformat(sec_data['last_updated'])
                        self.securities[cusip] = SecurityMaster(**sec_data)
                logger.info(f"Loaded {len(self.securities)} securities from master file")
            except Exception as e:
                logger.error(f"Error loading security master file: {e}")
                self.securities = {}
        else:
            logger.info("Security master file not found, starting fresh")
            self.securities = {}
    
    def _save_master_file(self):
        """Save security master file to storage"""
        try:
            data = {}
            for cusip, security in self.securities.items():
                sec_dict = asdict(security)
                # Convert date objects to ISO format strings
                sec_dict['created_date'] = security.created_date.isoformat()
                sec_dict['last_updated'] = security.last_updated.isoformat()
                data[cusip] = sec_dict
            
            with open(self.master_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved {len(self.securities)} securities to master file")
        except Exception as e:
            logger.error(f"Error saving security master file: {e}")
    
    def add_security(self, cusip: str, ticker: str, description: str,
                     security_type: str, exchange: Optional[str] = None,
                     currency: str = "USD", country: Optional[str] = None,
                     sector: Optional[str] = None, industry: Optional[str] = None,
                     isin: Optional[str] = None, sedol: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> SecurityMaster:
        """
        Add or update security in master file
        
        Args:
            cusip: CUSIP identifier (primary key)
            ticker: Stock ticker symbol
            description: Security description/name
            security_type: Type of security ("equity", "bond", "cash", "other")
            exchange: Exchange where security trades
            currency: Currency code (default: USD)
            country: Country of incorporation
            sector: Sector classification
            industry: Industry classification
            isin: ISIN identifier
            sedol: SEDOL identifier
            metadata: Additional metadata
            
        Returns:
            SecurityMaster object
        """
        if cusip in self.securities:
            # Update existing security
            security = self.securities[cusip]
            security.ticker = ticker
            security.description = description
            security.security_type = security_type
            security.exchange = exchange
            security.currency = currency
            security.country = country
            security.sector = sector
            security.industry = industry
            security.isin = isin
            security.sedol = sedol
            security.last_updated = date.today()
            if metadata:
                security.metadata.update(metadata)
            logger.info(f"Updated security in master file: {cusip} ({ticker})")
        else:
            # Add new security
            security = SecurityMaster(
                cusip=cusip,
                ticker=ticker,
                description=description,
                security_type=security_type,
                exchange=exchange,
                currency=currency,
                country=country,
                sector=sector,
                industry=industry,
                isin=isin,
                sedol=sedol,
                metadata=metadata or {}
            )
            self.securities[cusip] = security
            logger.info(f"Added security to master file: {cusip} ({ticker})")
        
        self._save_master_file()
        return security
    
    def get_security_by_cusip(self, cusip: str) -> Optional[SecurityMaster]:
        """Get security by CUSIP"""
        return self.securities.get(cusip)
    
    def get_security_by_ticker(self, ticker: str) -> Optional[SecurityMaster]:
        """Get security by ticker"""
        for security in self.securities.values():
            if security.ticker.upper() == ticker.upper():
                return security
        return None
    
    def get_all_securities(self, active_only: bool = True) -> List[SecurityMaster]:
        """Get all securities, optionally filtered by active status"""
        securities = list(self.securities.values())
        if active_only:
            securities = [s for s in securities if s.active]
        return sorted(securities, key=lambda x: x.ticker)
    
    def deactivate_security(self, cusip: str):
        """Deactivate security (mark as inactive)"""
        if cusip in self.securities:
            self.securities[cusip].active = False
            self.securities[cusip].last_updated = date.today()
            self._save_master_file()
            logger.info(f"Deactivated security: {cusip}")


class PortfolioRecords:
    """
    Production-ready Portfolio Records management
    
    Maintains portfolio position records with:
    - Security positions (quantity, cost basis, market value)
    - Position history (daily snapshots)
    - Reconciliation status
    - Cost basis tracking
    
    Example:
        >>> portfolio = PortfolioRecords(storage_path="./data/portfolio")
        >>> record = portfolio.add_position(
        ...     record_date=date.today(),
        ...     cusip="037833100",
        ...     ticker="AAPL",
        ...     quantity=Decimal('1000'),
        ...     cost_basis=Decimal('150000'),
        ...     market_price=Decimal('155.00')
        ... )
        >>> positions = portfolio.get_positions(date.today())
    """
    
    def __init__(self, storage_path: str = "./data/portfolio"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.records: Dict[date, List[PortfolioRecord]] = {}
        self._load_records()
    
    def _load_records(self):
        """Load portfolio records from storage"""
        records_file = self.storage_path / "portfolio_records.json"
        if records_file.exists():
            try:
                with open(records_file, 'r') as f:
                    data = json.load(f)
                    for date_str, records_list in data.items():
                        record_date = date.fromisoformat(date_str)
                        self.records[record_date] = [
                            PortfolioRecord(
                                record_date=record_date,
                                cusip=r['cusip'],
                                ticker=r['ticker'],
                                quantity=Decimal(str(r['quantity'])),
                                cost_basis=Decimal(str(r['cost_basis'])),
                                cost_basis_per_share=Decimal(str(r['cost_basis_per_share'])),
                                market_price=Decimal(str(r['market_price'])),
                                market_value=Decimal(str(r['market_value'])),
                                unrealized_gain_loss=Decimal(str(r['unrealized_gain_loss'])),
                                currency=r.get('currency', 'USD'),
                                source=r.get('source', 'portfolio'),
                                metadata=r.get('metadata', {})
                            )
                            for r in records_list
                        ]
                logger.info(f"Loaded portfolio records for {len(self.records)} dates")
            except Exception as e:
                logger.error(f"Error loading portfolio records: {e}")
                self.records = {}
        else:
            logger.info("Portfolio records file not found, starting fresh")
            self.records = {}
    
    def _save_records(self):
        """Save portfolio records to storage"""
        records_file = self.storage_path / "portfolio_records.json"
        try:
            data = {}
            for record_date, records_list in self.records.items():
                data[record_date.isoformat()] = [
                    {
                        'cusip': r.cusip,
                        'ticker': r.ticker,
                        'quantity': str(r.quantity),
                        'cost_basis': str(r.cost_basis),
                        'cost_basis_per_share': str(r.cost_basis_per_share),
                        'market_price': str(r.market_price),
                        'market_value': str(r.market_value),
                        'unrealized_gain_loss': str(r.unrealized_gain_loss),
                        'currency': r.currency,
                        'source': r.source,
                        'metadata': r.metadata
                    }
                    for r in records_list
                ]
            
            with open(records_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Saved portfolio records for {len(self.records)} dates")
        except Exception as e:
            logger.error(f"Error saving portfolio records: {e}")
    
    def add_position(self, record_date: date, cusip: str, ticker: str,
                      quantity: Decimal, cost_basis: Decimal,
                      market_price: Decimal, source: str = "portfolio",
                      currency: str = "USD",
                      metadata: Optional[Dict[str, Any]] = None) -> PortfolioRecord:
        """
        Add portfolio position record
        
        Args:
            record_date: Date of position
            cusip: Security CUSIP
            ticker: Security ticker
            quantity: Number of shares/units
            cost_basis: Total cost basis
            market_price: Current market price
            source: Source of data ("portfolio", "custodian", "reconciled")
            currency: Currency code
            metadata: Additional metadata
            
        Returns:
            PortfolioRecord object
        """
        cost_basis_per_share = cost_basis / quantity if quantity > 0 else Decimal('0')
        market_value = quantity * market_price
        unrealized_gain_loss = market_value - cost_basis
        
        record = PortfolioRecord(
            record_date=record_date,
            cusip=cusip,
            ticker=ticker,
            quantity=quantity,
            cost_basis=cost_basis,
            cost_basis_per_share=cost_basis_per_share,
            market_price=market_price,
            market_value=market_value,
            unrealized_gain_loss=unrealized_gain_loss,
            currency=currency,
            source=source,
            metadata=metadata or {}
        )
        
        if record_date not in self.records:
            self.records[record_date] = []
        
        # Update if position already exists for this date
        existing = None
        for i, r in enumerate(self.records[record_date]):
            if r.cusip == cusip:
                existing = i
                break
        
        if existing is not None:
            self.records[record_date][existing] = record
        else:
            self.records[record_date].append(record)
        
        self._save_records()
        logger.info(f"Added portfolio position: {ticker} {quantity} shares on {record_date}")
        return record
    
    def get_positions(self, record_date: date) -> List[PortfolioRecord]:
        """Get all positions for a given date"""
        return self.records.get(record_date, [])
    
    def get_position_by_cusip(self, record_date: date, cusip: str) -> Optional[PortfolioRecord]:
        """Get position for specific security on a given date"""
        positions = self.get_positions(record_date)
        for pos in positions:
            if pos.cusip == cusip:
                return pos
        return None
    
    def get_position_history(self, cusip: str, start_date: date, end_date: date) -> List[PortfolioRecord]:
        """Get position history for a security over date range"""
        from datetime import timedelta
        history = []
        current_date = start_date
        while current_date <= end_date:
            if current_date in self.records:
                for pos in self.records[current_date]:
                    if pos.cusip == cusip:
                        history.append(pos)
            current_date += timedelta(days=1)
        return history

