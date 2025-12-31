"""
T+1/T+2 Settlement Reconciliation

Implements reconciliation logic for trade settlement dates (T+1 and T+2).
For ETFs, trades typically settle T+2 (trade date + 2 business days).

This module handles:
- T+1 reconciliation (next-day settlement checks)
- T+2 reconciliation (standard ETF settlement)
- Settlement date calculations
- Trade settlement verification
- Cash settlement reconciliation
- Position settlement reconciliation
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class SettlementReconciliation:
    """Settlement reconciliation result"""
    reconciliation_date: date
    trade_date: date
    settlement_date: date
    settlement_type: str  # "T+1" or "T+2"
    trades_reconciled: int
    trades_pending: int
    trades_failed: int
    cash_settled: Decimal
    cash_pending: Decimal
    cash_failed: Decimal
    positions_settled: int
    positions_pending: int
    positions_failed: int
    status: str  # "complete", "partial", "failed"
    exceptions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class SettlementReconciliationManager:
    """
    Manages T+1 and T+2 settlement reconciliation for ETF trades.
    
    For ETFs:
    - Most trades settle T+2 (trade date + 2 business days)
    - Some trades may settle T+1 (next-day settlement)
    - Settlement reconciliation verifies trades settled correctly
    
    Example:
        >>> from lib.etf.functions.core.settlement_reconciliation import SettlementReconciliationManager
        >>> from lib.etf.adapters import FileBasedDataSourceAdapter
        >>> adapter = FileBasedDataSourceAdapter(data_path="./data")
        >>> settlement_mgr = SettlementReconciliationManager(adapter)
        >>> result = settlement_mgr.reconcile_t2_settlement(date(2024, 1, 5))  # Reconciles trades from Jan 3
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/settlement"):
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.default_settlement_days = 2  # T+2 for ETFs
    
    def calculate_settlement_date(self, trade_date: date, settlement_days: int = None) -> date:
        """
        Calculate settlement date from trade date.
        
        Args:
            trade_date: Date of the trade
            settlement_days: Number of business days to settlement (default: 2 for T+2)
            
        Returns:
            Settlement date (trade date + settlement_days business days)
        """
        if settlement_days is None:
            settlement_days = self.default_settlement_days
        
        settlement_date = trade_date
        days_added = 0
        
        while days_added < settlement_days:
            settlement_date += timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6)
            if settlement_date.weekday() < 5:  # Monday=0 to Friday=4
                days_added += 1
        
        return settlement_date
    
    def reconcile_t1_settlement(self, reconciliation_date: date) -> SettlementReconciliation:
        """
        Reconcile T+1 settlements (trades from previous business day).
        
        Args:
            reconciliation_date: Date to perform reconciliation (should be trade date + 1)
            
        Returns:
            SettlementReconciliation result
        """
        logger.info(f"Reconciling T+1 settlements for {reconciliation_date}")
        
        # Calculate trade date (T+1 means trade was yesterday)
        trade_date = reconciliation_date - timedelta(days=1)
        
        # Skip weekends
        while trade_date.weekday() >= 5:  # Saturday or Sunday
            trade_date -= timedelta(days=1)
        
        return self._reconcile_settlement(reconciliation_date, trade_date, "T+1")
    
    def reconcile_t2_settlement(self, reconciliation_date: date) -> SettlementReconciliation:
        """
        Reconcile T+2 settlements (standard ETF settlement).
        
        Args:
            reconciliation_date: Date to perform reconciliation (should be trade date + 2)
            
        Returns:
            SettlementReconciliation result
        """
        logger.info(f"Reconciling T+2 settlements for {reconciliation_date}")
        
        # Calculate trade date (T+2 means trade was 2 business days ago)
        trade_date = reconciliation_date
        days_back = 0
        
        while days_back < 2:
            trade_date -= timedelta(days=1)
            # Skip weekends
            if trade_date.weekday() < 5:  # Monday to Friday
                days_back += 1
        
        return self._reconcile_settlement(reconciliation_date, trade_date, "T+2")
    
    def _reconcile_settlement(self, reconciliation_date: date, trade_date: date, 
                             settlement_type: str) -> SettlementReconciliation:
        """
        Internal method to perform settlement reconciliation.
        
        Args:
            reconciliation_date: Date of reconciliation
            trade_date: Date of the trades being reconciled
            settlement_type: "T+1" or "T+2"
            
        Returns:
            SettlementReconciliation result
        """
        try:
            # Get trades from trade date
            trades = self._get_trades_for_date(trade_date)
            
            # Get custodian settlement data
            custodian_data = self.data_adapter.get_custodian_statements(reconciliation_date)
            
            # Get cash settlement data
            cash_settlements = self._get_cash_settlements(custodian_data, trade_date)
            
            # Get position settlement data
            position_settlements = self._get_position_settlements(custodian_data, trade_date)
            
            # Reconcile trades
            trades_reconciled = 0
            trades_pending = 0
            trades_failed = 0
            cash_settled = Decimal('0')
            cash_pending = Decimal('0')
            cash_failed = Decimal('0')
            positions_settled = 0
            positions_pending = 0
            positions_failed = 0
            exceptions = []
            
            for trade in trades:
                trade_id = trade.get('trade_id')
                trade_cusip = trade.get('cusip')
                trade_quantity = Decimal(str(trade.get('quantity', 0)))
                trade_price = Decimal(str(trade.get('price', 0)))
                trade_amount = trade_quantity * trade_price
                
                # Check if trade settled
                trade_settled = self._check_trade_settled(trade, cash_settlements, position_settlements)
                
                if trade_settled['status'] == 'settled':
                    trades_reconciled += 1
                    cash_settled += abs(trade_amount)
                    positions_settled += 1
                elif trade_settled['status'] == 'pending':
                    trades_pending += 1
                    cash_pending += abs(trade_amount)
                    positions_pending += 1
                    exceptions.append(f"Trade {trade_id} pending settlement")
                else:  # failed
                    trades_failed += 1
                    cash_failed += abs(trade_amount)
                    positions_failed += 1
                    exceptions.append(f"Trade {trade_id} failed settlement: {trade_settled.get('reason', 'Unknown')}")
            
            # Determine overall status
            total_trades = len(trades)
            if trades_failed > 0:
                status = "failed"
            elif trades_pending > 0:
                status = "partial"
            else:
                status = "complete"
            
            result = SettlementReconciliation(
                reconciliation_date=reconciliation_date,
                trade_date=trade_date,
                settlement_date=reconciliation_date,
                settlement_type=settlement_type,
                trades_reconciled=trades_reconciled,
                trades_pending=trades_pending,
                trades_failed=trades_failed,
                cash_settled=cash_settled,
                cash_pending=cash_pending,
                cash_failed=cash_failed,
                positions_settled=positions_settled,
                positions_pending=positions_pending,
                positions_failed=positions_failed,
                status=status,
                exceptions=exceptions,
                details={
                    "total_trades": total_trades,
                    "settlement_rate": float(trades_reconciled / total_trades) if total_trades > 0 else 0.0
                }
            )
            
            self._save_reconciliation(result)
            logger.info(f"Settlement reconciliation complete: {status}, {trades_reconciled}/{total_trades} trades settled")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in settlement reconciliation: {e}")
            return SettlementReconciliation(
                reconciliation_date=reconciliation_date,
                trade_date=trade_date,
                settlement_date=reconciliation_date,
                settlement_type=settlement_type,
                trades_reconciled=0,
                trades_pending=0,
                trades_failed=0,
                cash_settled=Decimal('0'),
                cash_pending=Decimal('0'),
                cash_failed=Decimal('0'),
                positions_settled=0,
                positions_pending=0,
                positions_failed=0,
                status="failed",
                exceptions=[f"Reconciliation error: {str(e)}"]
            )
    
    def _get_trades_for_date(self, trade_date: date) -> List[Dict[str, Any]]:
        """Get all trades for a specific trade date"""
        # TODO: Implement actual trade retrieval from data adapter
        # For now, return empty list (placeholder)
        # In production, this would query trade records from custodian or internal system
        return []
    
    def _get_cash_settlements(self, custodian_data: Dict[str, Any], trade_date: date) -> List[Dict[str, Any]]:
        """Extract cash settlement information from custodian data"""
        # TODO: Implement actual cash settlement extraction
        # For now, return empty list (placeholder)
        # In production, this would parse custodian statements for cash movements
        transactions = custodian_data.get('transactions', [])
        cash_settlements = [
            t for t in transactions 
            if t.get('trade_date') == trade_date.isoformat() and t.get('type') in ['settlement', 'trade']
        ]
        return cash_settlements
    
    def _get_position_settlements(self, custodian_data: Dict[str, Any], trade_date: date) -> List[Dict[str, Any]]:
        """Extract position settlement information from custodian data"""
        # TODO: Implement actual position settlement extraction
        # For now, return empty list (placeholder)
        # In production, this would parse custodian statements for position changes
        holdings = custodian_data.get('holdings', [])
        # Compare holdings to identify settled positions
        return holdings
    
    def _check_trade_settled(self, trade: Dict[str, Any], cash_settlements: List[Dict[str, Any]], 
                            position_settlements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if a specific trade has settled"""
        trade_id = trade.get('trade_id')
        trade_cusip = trade.get('cusip')
        trade_quantity = Decimal(str(trade.get('quantity', 0)))
        
        # Check cash settlement
        cash_settled = any(
            s.get('trade_id') == trade_id or 
            (s.get('cusip') == trade_cusip and abs(Decimal(str(s.get('quantity', 0))) - trade_quantity) < Decimal('0.01'))
            for s in cash_settlements
        )
        
        # Check position settlement
        position_settled = any(
            h.get('cusip') == trade_cusip and 
            abs(Decimal(str(h.get('quantity', 0))) - trade_quantity) < Decimal('0.01')
            for h in position_settlements
        )
        
        if cash_settled and position_settled:
            return {"status": "settled"}
        elif cash_settled or position_settled:
            return {"status": "pending", "reason": "Partial settlement"}
        else:
            return {"status": "failed", "reason": "No settlement found"}
    
    def _save_reconciliation(self, result: SettlementReconciliation):
        """Save reconciliation result to file"""
        file_path = self.storage_path / f"settlement_reconciliation_{result.reconciliation_date.isoformat()}_{result.settlement_type}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    "reconciliation_date": result.reconciliation_date.isoformat(),
                    "trade_date": result.trade_date.isoformat(),
                    "settlement_date": result.settlement_date.isoformat(),
                    "settlement_type": result.settlement_type,
                    "trades_reconciled": result.trades_reconciled,
                    "trades_pending": result.trades_pending,
                    "trades_failed": result.trades_failed,
                    "cash_settled": str(result.cash_settled),
                    "cash_pending": str(result.cash_pending),
                    "cash_failed": str(result.cash_failed),
                    "positions_settled": result.positions_settled,
                    "positions_pending": result.positions_pending,
                    "positions_failed": result.positions_failed,
                    "status": result.status,
                    "exceptions": result.exceptions,
                    "details": result.details
                }, f, indent=2)
            logger.info(f"Saved settlement reconciliation to {file_path}")
        except Exception as e:
            logger.error(f"Error saving settlement reconciliation: {e}")
    
    def reconcile_daily_settlements(self, reconciliation_date: date) -> Dict[str, Any]:
        """
        Reconcile both T+1 and T+2 settlements for a given date.
        
        This is the main method to call for daily settlement reconciliation.
        
        Args:
            reconciliation_date: Date to perform reconciliation
            
        Returns:
            Dictionary with T+1 and T+2 reconciliation results
        """
        logger.info(f"Reconciling daily settlements for {reconciliation_date}")
        
        t1_result = self.reconcile_t1_settlement(reconciliation_date)
        t2_result = self.reconcile_t2_settlement(reconciliation_date)
        
        return {
            "reconciliation_date": reconciliation_date.isoformat(),
            "t1_settlement": {
                "status": t1_result.status,
                "trades_reconciled": t1_result.trades_reconciled,
                "trades_pending": t1_result.trades_pending,
                "trades_failed": t1_result.trades_failed,
                "exceptions": t1_result.exceptions
            },
            "t2_settlement": {
                "status": t2_result.status,
                "trades_reconciled": t2_result.trades_reconciled,
                "trades_pending": t2_result.trades_pending,
                "trades_failed": t2_result.trades_failed,
                "exceptions": t2_result.exceptions
            },
            "overall_status": "complete" if (t1_result.status == "complete" and t2_result.status == "complete") else "partial"
        }

