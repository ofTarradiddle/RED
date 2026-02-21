"""
Production-Ready Tax Efficiency Optimization Module
Portfolio-level tax optimization for ETF operations
"""

import logging
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter

logger = logging.getLogger(__name__)


@dataclass
class TaxOptimizationStrategy:
    """Tax optimization strategy"""
    strategy_id: str
    strategy_type: str  # "lot_selection", "basket_optimization", "wash_sale_avoidance"
    description: str
    expected_tax_savings: Decimal
    implementation: Dict[str, Any]


class TaxEfficiencyOptimizer:
    """
    Production-ready Tax Efficiency Optimizer
    
    Handles:
    - Tax lot selection (FIFO vs LIFO vs specific identification)
    - Custom basket optimization for tax efficiency
    - Wash sale avoidance
    - Tax loss harvesting
    - Capital gains minimization
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/tax_optimization"):
        """
        Initialize Tax Efficiency Optimizer
        
        Args:
            data_adapter: DataSourceAdapter for fetching data
            storage_path: Path for storing optimization records
        """
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def optimize_redemption_basket_for_tax(self, pcf: Dict[str, Any], 
                                           creation_units: int,
                                           tax_lots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize redemption basket for tax efficiency
        
        Strategy: Deliver securities with highest cost basis to minimize realized gains
        
        Args:
            pcf: PCF file data
            creation_units: Number of creation units to redeem
            tax_lots: List of tax lots with cost basis information
                Format: [{"cusip": "...", "quantity": Decimal, "cost_basis": Decimal, "purchase_date": date}, ...]
            
        Returns:
            Optimized redemption basket
        """
        logger.info(f"Optimizing redemption basket for {creation_units} units (tax efficiency)")
        
        # Calculate required quantities from PCF
        required_quantities = {}
        for sec in pcf.get('securities', []):
            cusip = sec.get('cusip')
            quantity = Decimal(str(sec.get('quantity', 0))) * Decimal(str(creation_units))
            required_quantities[cusip] = quantity
        
        # Build optimized basket by selecting highest cost basis lots
        optimized_basket = []
        
        for cusip, required_qty in required_quantities.items():
            # Get tax lots for this CUSIP, sorted by cost basis (highest first)
            cusip_lots = [lot for lot in tax_lots if lot.get('cusip') == cusip]
            cusip_lots.sort(key=lambda x: Decimal(str(x.get('cost_basis', 0))), reverse=True)
            
            remaining_qty = required_qty
            selected_lots = []
            
            for lot in cusip_lots:
                lot_qty = Decimal(str(lot.get('quantity', 0)))
                if remaining_qty <= 0:
                    break
                
                if lot_qty <= remaining_qty:
                    selected_lots.append(lot)
                    remaining_qty -= lot_qty
                else:
                    # Partial lot selection
                    partial_lot = lot.copy()
                    partial_lot['quantity'] = remaining_qty
                    selected_lots.append(partial_lot)
                    remaining_qty = Decimal('0')
            
            if selected_lots:
                total_cost_basis = sum(
                    Decimal(str(lot.get('quantity', 0))) * Decimal(str(lot.get('cost_basis', 0)))
                    for lot in selected_lots
                )
                avg_cost_basis = total_cost_basis / required_qty if required_qty > 0 else Decimal('0')
                
                optimized_basket.append({
                    "cusip": cusip,
                    "quantity": str(required_qty),
                    "cost_basis": str(avg_cost_basis),
                    "selected_lots": len(selected_lots),
                    "optimization_strategy": "highest_cost_basis"
                })
        
        # Calculate tax savings estimate
        current_price = Decimal('100')  # TODO: Get from market data
        total_cost_basis = sum(
            Decimal(str(sec.get('quantity', 0))) * Decimal(str(sec.get('cost_basis', 0)))
            for sec in optimized_basket
        )
        total_market_value = sum(
            Decimal(str(sec.get('quantity', 0))) * current_price
            for sec in optimized_basket
        )
        realized_gain = total_market_value - total_cost_basis
        
        logger.info(f"Optimized basket: realized gain = {realized_gain}, cost basis = {total_cost_basis}")
        
        # Save optimization record
        self._save_optimization_record(optimized_basket, realized_gain, total_cost_basis)
        
        return optimized_basket
    
    def optimize_creation_basket_for_tax(self, pcf: Dict[str, Any],
                                        creation_units: int,
                                        ap_inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize creation basket for tax efficiency (AP perspective)
        
        Strategy: Accept securities with lowest cost basis from AP to minimize their realized gains
        
        Args:
            pcf: PCF file data
            creation_units: Number of creation units
            ap_inventory: AP's inventory with cost basis
                Format: [{"cusip": "...", "quantity": Decimal, "cost_basis": Decimal}, ...]
            
        Returns:
            Optimized creation basket recommendation
        """
        logger.info(f"Optimizing creation basket for {creation_units} units (AP tax efficiency)")
        
        # Calculate required quantities from PCF
        required_quantities = {}
        for sec in pcf.get('securities', []):
            cusip = sec.get('cusip')
            quantity = Decimal(str(sec.get('quantity', 0))) * Decimal(str(creation_units))
            required_quantities[cusip] = quantity
        
        # Build optimized basket by selecting lowest cost basis from AP inventory
        optimized_basket = []
        
        for cusip, required_qty in required_quantities.items():
            # Get AP inventory for this CUSIP, sorted by cost basis (lowest first)
            cusip_inventory = [inv for inv in ap_inventory if inv.get('cusip') == cusip]
            cusip_inventory.sort(key=lambda x: Decimal(str(x.get('cost_basis', 0))))
            
            remaining_qty = required_qty
            selected_inventory = []
            
            for inv in cusip_inventory:
                inv_qty = Decimal(str(inv.get('quantity', 0)))
                if remaining_qty <= 0:
                    break
                
                if inv_qty <= remaining_qty:
                    selected_inventory.append(inv)
                    remaining_qty -= inv_qty
                else:
                    # Partial selection
                    partial_inv = inv.copy()
                    partial_inv['quantity'] = remaining_qty
                    selected_inventory.append(partial_inv)
                    remaining_qty = Decimal('0')
            
            if selected_inventory:
                total_cost_basis = sum(
                    Decimal(str(inv.get('quantity', 0))) * Decimal(str(inv.get('cost_basis', 0)))
                    for inv in selected_inventory
                )
                avg_cost_basis = total_cost_basis / required_qty if required_qty > 0 else Decimal('0')
                
                optimized_basket.append({
                    "cusip": cusip,
                    "quantity": str(required_qty),
                    "cost_basis": str(avg_cost_basis),
                    "optimization_strategy": "lowest_cost_basis_ap"
                })
        
        return optimized_basket
    
    def check_wash_sale_rule(self, sale_date: date, cusip: str, 
                            recent_purchases: List[Dict[str, Any]]) -> bool:
        """
        Check if sale would violate wash sale rule (30-day window)
        
        Args:
            sale_date: Proposed sale date
            cusip: Security CUSIP
            recent_purchases: Recent purchases of same or substantially identical security
                Format: [{"purchase_date": date, "quantity": Decimal}, ...]
            
        Returns:
            True if wash sale rule would be violated
        """
        wash_sale_window = 30  # days
        
        for purchase in recent_purchases:
            purchase_date = purchase.get('purchase_date')
            if isinstance(purchase_date, str):
                purchase_date = date.fromisoformat(purchase_date)
            
            days_between = (sale_date - purchase_date).days
            
            if -wash_sale_window <= days_between <= wash_sale_window:
                logger.warning(
                    f"Wash sale rule violation: sale on {sale_date} within 30 days of "
                    f"purchase on {purchase_date} for {cusip}"
                )
                return True
        
        return False
    
    def identify_tax_loss_harvesting_opportunities(self, holdings: List[Dict[str, Any]],
                                                  current_prices: Dict[str, Decimal]) -> List[Dict[str, Any]]:
        """
        Identify tax loss harvesting opportunities
        
        Strategy: Find positions with unrealized losses that can be harvested
        
        Args:
            holdings: Current holdings with cost basis
                Format: [{"cusip": "...", "quantity": Decimal, "cost_basis": Decimal}, ...]
            current_prices: Current market prices by CUSIP
            
        Returns:
            List of tax loss harvesting opportunities
        """
        opportunities = []
        
        for holding in holdings:
            cusip = holding.get('cusip')
            quantity = Decimal(str(holding.get('quantity', 0)))
            cost_basis = Decimal(str(holding.get('cost_basis', 0)))
            current_price = current_prices.get(cusip, Decimal('0'))
            
            if current_price > 0:
                unrealized_loss = (current_price - cost_basis) * quantity
                
                if unrealized_loss < 0:  # Loss
                    loss_percentage = (unrealized_loss / (cost_basis * quantity)) * 100 if cost_basis > 0 else 0
                    
                    opportunities.append({
                        "cusip": cusip,
                        "quantity": str(quantity),
                        "cost_basis": str(cost_basis),
                        "current_price": str(current_price),
                        "unrealized_loss": str(unrealized_loss),
                        "loss_percentage": float(loss_percentage),
                        "harvest_strategy": "sell_and_replace" if abs(loss_percentage) > 5 else "hold"
                    })
        
        # Sort by loss amount (largest losses first)
        opportunities.sort(key=lambda x: Decimal(str(x.get('unrealized_loss', 0))))
        
        logger.info(f"Identified {len(opportunities)} tax loss harvesting opportunities")
        
        return opportunities
    
    def _save_optimization_record(self, optimized_basket: List[Dict[str, Any]],
                                  realized_gain: Decimal, total_cost_basis: Decimal):
        """Save optimization record for audit trail"""
        record = {
            "optimization_date": date.today().isoformat(),
            "optimized_basket": optimized_basket,
            "realized_gain": str(realized_gain),
            "total_cost_basis": str(total_cost_basis),
            "optimization_type": "redemption_basket_tax_optimization"
        }
        
        record_file = self.storage_path / f"tax_optimization_{date.today().isoformat()}.json"
        with open(record_file, 'w') as f:
            json.dump(record, f, indent=2, default=str)

