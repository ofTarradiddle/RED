"""
Production-Ready Tax Lot Accounting Function
Complete implementation for tracking cost basis and realized/unrealized gains

This module handles tax lot accounting for the fund's portfolio. Every purchase of a security
creates a tax lot with a specific cost basis and acquisition date. When the fund sells securities,
the module closes (or partially closes) those lots to calculate realized gains or losses, using
FIFO by default (first-in, first-out method).

Tax Optimization Methods:
- FIFO: Default IRS method, oldest lots first
- LIFO: Newest lots first
- LOWEST_COST: Lowest cost basis first (minimizes realized gains, tax-efficient)
- HIGHEST_COST: Highest cost basis first (maximizes gains/losses, useful for tax-loss harvesting)

References:
- Investopedia: Tax Lot Accounting
- IRS Publication 550: Investment Income and Expenses
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class TaxLot:
    """Represents a lot of purchased securities (for tax lot accounting)."""
    lot_id: str
    ticker: str
    cusip: Optional[str] = None
    quantity: Decimal = Decimal('0')  # shares currently in this lot (remaining)
    cost_basis: Decimal = Decimal('0')  # cost per share
    purchase_date: date = field(default_factory=date.today)
    sold_date: Optional[date] = None  # will be set when lot is fully sold
    original_quantity: Decimal = Decimal('0')  # original shares purchased


@dataclass
class RealizedGainRecord:
    """Record of a realized gain or loss from selling a tax lot."""
    record_id: str
    ticker: str
    quantity: Decimal
    purchase_date: date
    sale_date: date
    cost_basis: Decimal
    sale_price: Decimal
    gain: Decimal  # can be negative for losses
    term: str  # "short" or "long" (holding period < 365 days = short-term)
    lot_id: str


class TaxLotManager:
    """
    Manages tax lots for securities to track cost basis and realized/unrealized gains.
    
    Provides methods to add new lots and sell lots (closing them in FIFO order by default).
    This is crucial for accurate tax reporting and for implementing tax-efficient strategies.
    
    Example:
        >>> manager = TaxLotManager()
        >>> manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2024, 1, 15))
        >>> manager.add_lot("AAPL", Decimal('50'), Decimal('155.00'), date(2024, 2, 20))
        >>> gain = manager.sell("AAPL", Decimal('75'), Decimal('160.00'), date(2024, 3, 15))
        >>> print(f"Realized gain: ${gain}")
    """
    
    def __init__(self, storage_path: str = "./data/tax_lots"):
        """
        Initialize Tax Lot Manager.
        
        Args:
            storage_path: Path for storing tax lot data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.open_lots: List[TaxLot] = []  # list of TaxLot objects currently held
        self.closed_lots: List[TaxLot] = []  # list of TaxLot objects that have been fully sold
        self.realized_gains: List[RealizedGainRecord] = []  # list of realized gain/loss records
        self.load_tax_lots()
    
    def load_tax_lots(self):
        """Load tax lots from storage"""
        lots_file = self.storage_path / "tax_lots.json"
        if lots_file.exists():
            try:
                with open(lots_file, 'r') as f:
                    data = json.load(f)
                    self.open_lots = [
                        TaxLot(
                            lot_id=lot['lot_id'],
                            ticker=lot['ticker'],
                            cusip=lot.get('cusip'),
                            quantity=Decimal(str(lot['quantity'])),
                            cost_basis=Decimal(str(lot['cost_basis'])),
                            purchase_date=date.fromisoformat(lot['purchase_date']),
                            sold_date=date.fromisoformat(lot['sold_date']) if lot.get('sold_date') else None,
                            original_quantity=Decimal(str(lot.get('original_quantity', lot['quantity'])))
                        )
                        for lot in data.get('open_lots', [])
                    ]
                    self.closed_lots = [
                        TaxLot(
                            lot_id=lot['lot_id'],
                            ticker=lot['ticker'],
                            cusip=lot.get('cusip'),
                            quantity=Decimal('0'),
                            cost_basis=Decimal(str(lot['cost_basis'])),
                            purchase_date=date.fromisoformat(lot['purchase_date']),
                            sold_date=date.fromisoformat(lot['sold_date']) if lot.get('sold_date') else None,
                            original_quantity=Decimal(str(lot.get('original_quantity', 0)))
                        )
                        for lot in data.get('closed_lots', [])
                    ]
                    self.realized_gains = [
                        RealizedGainRecord(
                            record_id=rec['record_id'],
                            ticker=rec['ticker'],
                            quantity=Decimal(str(rec['quantity'])),
                            purchase_date=date.fromisoformat(rec['purchase_date']),
                            sale_date=date.fromisoformat(rec['sale_date']),
                            cost_basis=Decimal(str(rec['cost_basis'])),
                            sale_price=Decimal(str(rec['sale_price'])),
                            gain=Decimal(str(rec['gain'])),
                            term=rec['term'],
                            lot_id=rec['lot_id']
                        )
                        for rec in data.get('realized_gains', [])
                    ]
                logger.info(f"Loaded {len(self.open_lots)} open lots, {len(self.closed_lots)} closed lots, {len(self.realized_gains)} realized gain records")
            except Exception as e:
                logger.error(f"Error loading tax lots: {e}")
                self.open_lots = []
                self.closed_lots = []
                self.realized_gains = []
    
    def save_tax_lots(self):
        """Save tax lots to storage"""
        lots_file = self.storage_path / "tax_lots.json"
        try:
            data = {
                "open_lots": [
                    {
                        "lot_id": lot.lot_id,
                        "ticker": lot.ticker,
                        "cusip": lot.cusip,
                        "quantity": str(lot.quantity),
                        "cost_basis": str(lot.cost_basis),
                        "purchase_date": lot.purchase_date.isoformat(),
                        "sold_date": lot.sold_date.isoformat() if lot.sold_date else None,
                        "original_quantity": str(lot.original_quantity)
                    }
                    for lot in self.open_lots
                ],
                "closed_lots": [
                    {
                        "lot_id": lot.lot_id,
                        "ticker": lot.ticker,
                        "cusip": lot.cusip,
                        "quantity": "0",
                        "cost_basis": str(lot.cost_basis),
                        "purchase_date": lot.purchase_date.isoformat(),
                        "sold_date": lot.sold_date.isoformat() if lot.sold_date else None,
                        "original_quantity": str(lot.original_quantity)
                    }
                    for lot in self.closed_lots
                ],
                "realized_gains": [
                    {
                        "record_id": rec.record_id,
                        "ticker": rec.ticker,
                        "quantity": str(rec.quantity),
                        "purchase_date": rec.purchase_date.isoformat(),
                        "sale_date": rec.sale_date.isoformat(),
                        "cost_basis": str(rec.cost_basis),
                        "sale_price": str(rec.sale_price),
                        "gain": str(rec.gain),
                        "term": rec.term,
                        "lot_id": rec.lot_id
                    }
                    for rec in self.realized_gains
                ]
            }
            with open(lots_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.open_lots)} open lots, {len(self.closed_lots)} closed lots, {len(self.realized_gains)} realized gain records")
        except Exception as e:
            logger.error(f"Error saving tax lots: {e}")
    
    def add_lot(self, ticker: str, quantity: Decimal, cost_basis: Decimal, 
                purchase_date: date, cusip: Optional[str] = None) -> TaxLot:
        """
        Add a new tax lot for a purchase transaction.
        
        Args:
            ticker: Security ticker symbol
            quantity: Number of shares purchased
            cost_basis: Cost per share
            purchase_date: Date of purchase
            cusip: Optional CUSIP identifier
            
        Returns:
            TaxLot object
        """
        lot_id = f"LOT_{ticker}_{purchase_date.isoformat()}_{len(self.open_lots)}"
        lot = TaxLot(
            lot_id=lot_id,
            ticker=ticker,
            cusip=cusip,
            quantity=quantity,
            cost_basis=cost_basis,
            purchase_date=purchase_date,
            original_quantity=quantity
        )
        self.open_lots.append(lot)
        self.save_tax_lots()
        logger.info(f"Added tax lot: {ticker} {quantity} shares @ ${cost_basis} on {purchase_date}")
        return lot
    
    def sell(self, ticker: str, quantity: Decimal, price: Decimal, sale_date: date,
             method: str = 'FIFO') -> Decimal:
        """
        Sell a given quantity of a security, closing tax lots according to specified method.
        
        By default, uses FIFO (first-in, first-out) which is the most common tax lot relief method.
        Can also use LIFO (last-in, first-out), LOWEST_COST (lowest cost basis first), 
        HIGHEST_COST (highest cost basis first), or specific lot identification.
        
        Tax Optimization Strategies:
        - LOWEST_COST: Sell lowest cost basis first to minimize realized gains (tax-efficient)
        - HIGHEST_COST: Sell highest cost basis first to maximize realized gains (useful for tax-loss harvesting)
        - FIFO: Default IRS method, oldest lots first
        - LIFO: Newest lots first
        
        Args:
            ticker: Security ticker symbol
            quantity: Number of shares to sell
            price: Sale price per share
            sale_date: Date of sale
            method: Tax lot relief method:
                - 'FIFO' (default): First-in, first-out (oldest lots first)
                - 'LIFO': Last-in, first-out (newest lots first)
                - 'LOWEST_COST': Lowest cost basis first (tax-efficient, minimizes gains)
                - 'HIGHEST_COST': Highest cost basis first (maximizes gains, useful for losses)
            
        Returns:
            Total realized gain (or loss) from this sale
            
        Raises:
            ValueError: If not enough lots are available to sell the requested quantity
        """
        # Get all open lots for this ticker
        lots = [lot for lot in self.open_lots if lot.ticker == ticker]
        
        # Sort lots according to method
        method_upper = method.upper()
        if method_upper == 'LIFO':
            lots.sort(key=lambda lot: lot.purchase_date, reverse=True)  # Newest first
        elif method_upper == 'LOWEST_COST':
            # Sort by cost basis ascending (lowest first) - minimizes realized gains
            lots.sort(key=lambda lot: lot.cost_basis)
        elif method_upper == 'HIGHEST_COST':
            # Sort by cost basis descending (highest first) - maximizes realized gains/losses
            # Useful for tax-loss harvesting (selling losses first)
            lots.sort(key=lambda lot: lot.cost_basis, reverse=True)
        else:  # FIFO (default)
            lots.sort(key=lambda lot: lot.purchase_date)  # Oldest first
        
        qty_to_sell = quantity
        total_realized_gain = Decimal('0')
        
        for lot in lots:
            if qty_to_sell <= 0:
                break
            if lot.quantity <= 0:
                continue
            
            if lot.quantity > qty_to_sell:
                # Partial sale of this lot
                realized = (price - lot.cost_basis) * qty_to_sell
                total_realized_gain += realized
                holding_period = (sale_date - lot.purchase_date).days
                term = 'long' if holding_period >= 365 else 'short'
                
                record_id = f"GAIN_{ticker}_{sale_date.isoformat()}_{len(self.realized_gains)}"
                self.realized_gains.append(RealizedGainRecord(
                    record_id=record_id,
                    ticker=ticker,
                    quantity=qty_to_sell,
                    purchase_date=lot.purchase_date,
                    sale_date=sale_date,
                    cost_basis=lot.cost_basis,
                    sale_price=price,
                    gain=realized,
                    term=term,
                    lot_id=lot.lot_id
                ))
                
                lot.quantity -= qty_to_sell  # reduce lot by sold quantity
                qty_to_sell = 0
            else:
                # Sell entire lot
                realized = (price - lot.cost_basis) * lot.quantity
                total_realized_gain += realized
                holding_period = (sale_date - lot.purchase_date).days
                term = 'long' if holding_period >= 365 else 'short'
                
                record_id = f"GAIN_{ticker}_{sale_date.isoformat()}_{len(self.realized_gains)}"
                self.realized_gains.append(RealizedGainRecord(
                    record_id=record_id,
                    ticker=ticker,
                    quantity=lot.quantity,
                    purchase_date=lot.purchase_date,
                    sale_date=sale_date,
                    cost_basis=lot.cost_basis,
                    sale_price=price,
                    gain=realized,
                    term=term,
                    lot_id=lot.lot_id
                ))
                
                qty_to_sell -= lot.quantity
                # Mark lot as closed
                lot.sold_date = sale_date
                self.closed_lots.append(lot)
                self.open_lots.remove(lot)
        
        if qty_to_sell > 0:
            # If we still have quantity unsold, it means not enough holdings were available
            raise ValueError(f"Not enough lots to sell: remaining {qty_to_sell} shares of {ticker}")
        
        self.save_tax_lots()
        logger.info(f"Sold {quantity} shares of {ticker} at ${price}, realized gain: ${total_realized_gain}")
        return total_realized_gain
    
    def get_unrealized_gains(self, current_prices: Dict[str, Decimal], 
                            as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Compute total unrealized gain or loss for all open lots given current market prices.
        
        Args:
            current_prices: Dictionary mapping ticker to current market price
            as_of_date: Optional date for calculation (defaults to today)
            
        Returns:
            Dictionary with short-term and long-term unrealized gains breakdown
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        unrealized_short = Decimal('0')
        unrealized_long = Decimal('0')
        total_unrealized = Decimal('0')
        
        for lot in self.open_lots:
            price = current_prices.get(lot.ticker)
            if price is None:
                logger.warning(f"No current price for {lot.ticker}, skipping unrealized gain calculation")
                continue
            
            gain = (price - lot.cost_basis) * lot.quantity
            holding_period = (as_of_date - lot.purchase_date).days
            
            if holding_period >= 365:
                unrealized_long += gain
            else:
                unrealized_short += gain
            
            total_unrealized += gain
        
        return {
            "unrealized_short_term": str(unrealized_short),
            "unrealized_long_term": str(unrealized_long),
            "unrealized_total": str(total_unrealized),
            "as_of_date": as_of_date.isoformat()
        }
    
    def get_realized_gains_summary(self, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get summary of realized gains for a period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary with realized gains breakdown by term
        """
        gains = self.realized_gains
        
        if start_date:
            gains = [g for g in gains if g.sale_date >= start_date]
        if end_date:
            gains = [g for g in gains if g.sale_date <= end_date]
        
        short_term_gains = sum(g.gain for g in gains if g.term == 'short' and g.gain > 0)
        short_term_losses = sum(g.gain for g in gains if g.term == 'short' and g.gain < 0)
        long_term_gains = sum(g.gain for g in gains if g.term == 'long' and g.gain > 0)
        long_term_losses = sum(g.gain for g in gains if g.term == 'long' and g.gain < 0)
        
        return {
            "period_start": start_date.isoformat() if start_date else None,
            "period_end": end_date.isoformat() if end_date else None,
            "short_term_gains": str(short_term_gains),
            "short_term_losses": str(short_term_losses),
            "net_short_term": str(short_term_gains + short_term_losses),
            "long_term_gains": str(long_term_gains),
            "long_term_losses": str(long_term_losses),
            "net_long_term": str(long_term_gains + long_term_losses),
            "total_realized": str(short_term_gains + short_term_losses + long_term_gains + long_term_losses),
            "transactions_count": len(gains)
        }
    
    def get_lots_for_ticker(self, ticker: str) -> List[TaxLot]:
        """Get all open lots for a specific ticker"""
        return [lot for lot in self.open_lots if lot.ticker == ticker]
    
    def get_total_cost_basis(self, ticker: Optional[str] = None) -> Decimal:
        """
        Get total cost basis for all open lots (or for a specific ticker).
        
        Args:
            ticker: Optional ticker to filter by
            
        Returns:
            Total cost basis
        """
        lots = self.open_lots
        if ticker:
            lots = [lot for lot in lots if lot.ticker == ticker]
        
        return sum(lot.cost_basis * lot.quantity for lot in lots)

