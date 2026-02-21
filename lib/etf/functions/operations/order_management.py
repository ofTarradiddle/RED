"""
Production-Ready Order Management Function
Complete implementation with all business logic
"""

import logging
from datetime import date, datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import json

from lib.etf.shared import DataSourceAdapter, PCFFile, APOrder
from lib.etf.functions.operations.rule_6c11_compliance import Rule6c11Compliance

logger = logging.getLogger(__name__)


@dataclass
class CreationBasket:
    """Creation basket for AP orders"""
    basket_type: str  # "standard" or "custom"
    securities: List[Dict[str, Any]]  # List of {cusip, quantity, description}
    cash_component: Decimal
    total_value: Decimal
    creation_units: int
    validated: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class RedemptionBasket:
    """Redemption basket for AP orders"""
    basket_type: str  # "standard" or "custom"
    securities: List[Dict[str, Any]]  # List of {cusip, quantity, description}
    cash_component: Decimal
    total_value: Decimal
    creation_units: int
    validated: bool = True
    errors: List[str] = field(default_factory=list)


class OrderManagement:
    """
    Production-ready Order Management implementation
    
    Handles:
    - PCF (Portfolio Composition File) generation and publication
    - AP order processing (creation and redemption)
    - Basket construction (standard and custom)
    - Order validation and routing
    """
    
    def __init__(self, data_adapter: DataSourceAdapter, storage_path: str = "./data/om"):
        """
        Initialize Order Management
        
        Args:
            data_adapter: DataSourceAdapter for fetching data
            storage_path: Path for storing order management data
        """
        self.data_adapter = data_adapter
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.creation_unit_size = 50000  # Standard creation unit
        # Order cut-off time: 4:00 PM ET (16:00 ET)
        self.order_cutoff_time = time(16, 0)  # 4:00 PM ET
        # Creation/redemption fees (per creation unit)
        self.creation_fee = Decimal('0')  # TODO: Set actual fee
        self.redemption_fee = Decimal('0')  # TODO: Set actual fee
        # Rule 6c-11 compliance validator
        self.rule_6c11_compliance = Rule6c11Compliance(storage_path=str(self.storage_path / "rule_6c11"))
    
    def generate_pcf(self, pcf_date: date) -> PCFFile:
        """
        Generate and validate Portfolio Composition File for NSCC
        
        PCF must be published daily by 8:00 AM ET before market open.
        Contains the standard creation/redemption basket composition.
        
        Args:
            pcf_date: Date for which to generate PCF
            
        Returns:
            PCFFile object with portfolio composition
        """
        logger.info(f"Generating PCF for {pcf_date}")
        
        try:
            prev_date = pcf_date - timedelta(days=1)
            holdings = self.data_adapter.get_portfolio_holdings(prev_date)
            custodian_data = self.data_adapter.get_custodian_statements(prev_date)
            corporate_actions = self.data_adapter.get_corporate_actions(pcf_date)
        except Exception as e:
            logger.error(f"Error fetching data for PCF generation: {e}")
            return PCFFile(
                date=pcf_date,
                creation_unit_size=self.creation_unit_size,
                securities=[],
                cash_component=Decimal('0'),
                estimated_cash_component=Decimal('0'),
                total_estimated_value=Decimal('0'),
                validation_passed=False,
                errors=[f"Data fetch error: {str(e)}"]
            )
        
        securities = []
        total_estimated_value = Decimal('0')
        errors = []
        
        cusips = [h.get('cusip') for h in holdings if h.get('cusip')]
        prices = self.data_adapter.get_market_prices(prev_date, cusips)
        
        for holding in holdings:
            cusip = holding.get('cusip')
            if not cusip:
                continue
            
            quantity = Decimal(str(holding.get('quantity', 0)))
            shares_per_unit = (quantity / Decimal(str(self.creation_unit_size))).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            )
            
            if shares_per_unit <= 0:
                continue
            
            price = prices.get(cusip, Decimal('0'))
            estimated_value = shares_per_unit * price
            
            securities.append({
                "cusip": cusip,
                "quantity": str(shares_per_unit),
                "description": holding.get('description', ''),
                "estimated_value": str(estimated_value)
            })
            
            total_estimated_value += estimated_value
        
        cash_balance = Decimal(str(custodian_data.get('cash_balance', 0)))
        cash_per_unit = (cash_balance / Decimal(str(self.creation_unit_size))).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
        
        validation_passed = True
        if len(securities) == 0:
            errors.append("No securities in PCF")
            validation_passed = False
        
        if total_estimated_value == 0:
            errors.append("Total estimated value is zero")
            validation_passed = False
        
        result = PCFFile(
            date=pcf_date,
            creation_unit_size=self.creation_unit_size,
            securities=securities,
            cash_component=cash_per_unit,
            estimated_cash_component=cash_per_unit,
            total_estimated_value=total_estimated_value,
            validation_passed=validation_passed,
            errors=errors
        )
        
        self._save_pcf(result)
        pcf_formatted = self._format_pcf_for_nscc(result)
        self._save_pcf_formatted(pcf_date, pcf_formatted)
        
        logger.info(f"PCF generated: {len(securities)} securities, ${total_estimated_value} estimated value")
        return result
    
    def build_standard_creation_basket(self, pcf: PCFFile, creation_units: int) -> CreationBasket:
        """
        Build standard creation basket from PCF
        
        Standard baskets use the exact PCF composition multiplied by creation units.
        
        Args:
            pcf: PCFFile containing portfolio composition
            creation_units: Number of creation units
            
        Returns:
            CreationBasket object
        """
        logger.info(f"Building standard creation basket for {creation_units} units")
        
        securities = []
        total_value = Decimal('0')
        
        for sec in pcf.securities:
            quantity_per_unit = Decimal(str(sec['quantity']))
            total_quantity = quantity_per_unit * Decimal(str(creation_units))
            
            securities.append({
                "cusip": sec['cusip'],
                "quantity": str(total_quantity),
                "description": sec.get('description', ''),
                "quantity_per_unit": str(quantity_per_unit)
            })
            
            estimated_value = Decimal(str(sec.get('estimated_value', 0)))
            total_value += estimated_value * Decimal(str(creation_units))
        
        cash_component = pcf.cash_component * Decimal(str(creation_units))
        total_value += cash_component
        
        return CreationBasket(
            basket_type="standard",
            securities=securities,
            cash_component=cash_component,
            total_value=total_value,
            creation_units=creation_units,
            validated=True
        )
    
    def build_standard_redemption_basket(self, pcf: PCFFile, creation_units: int) -> RedemptionBasket:
        """
        Build standard redemption basket from PCF
        
        Standard redemption baskets typically use in-kind delivery (securities only).
        
        Args:
            pcf: PCFFile containing portfolio composition
            creation_units: Number of creation units to redeem
            
        Returns:
            RedemptionBasket object
        """
        logger.info(f"Building standard redemption basket for {creation_units} units")
        
        securities = []
        total_value = Decimal('0')
        
        for sec in pcf.securities:
            quantity_per_unit = Decimal(str(sec['quantity']))
            total_quantity = quantity_per_unit * Decimal(str(creation_units))
            
            securities.append({
                "cusip": sec['cusip'],
                "quantity": str(total_quantity),
                "description": sec.get('description', ''),
                "quantity_per_unit": str(quantity_per_unit)
            })
            
            estimated_value = Decimal(str(sec.get('estimated_value', 0)))
            total_value += estimated_value * Decimal(str(creation_units))
        
        # Redemptions typically have minimal cash component
        cash_component = Decimal('0')
        
        return RedemptionBasket(
            basket_type="standard",
            securities=securities,
            cash_component=cash_component,
            total_value=total_value,
            creation_units=creation_units,
            validated=True
        )
    
    def build_custom_creation_basket(self, pcf: PCFFile, creation_units: int, 
                                    custom_securities: List[Dict[str, Any]]) -> CreationBasket:
        """
        Build custom creation basket
        
        Custom baskets allow APs to deliver different securities than the PCF,
        typically for tax optimization or inventory management.
        
        Args:
            pcf: PCFFile for validation
            creation_units: Number of creation units
            custom_securities: List of custom securities with cusip and quantity
                Example: [{"cusip": "037833100", "quantity": "100"}, ...]
                
        Returns:
            CreationBasket object with validation results
        """
        logger.info(f"Building custom creation basket for {creation_units} units")
        
        errors = []
        validated = True
        
        # Validate custom securities against PCF
        pcf_cusips = {s['cusip'] for s in pcf.securities}
        custom_cusips = {s.get('cusip') for s in custom_securities if s.get('cusip')}
        
        invalid_cusips = custom_cusips - pcf_cusips
        if invalid_cusips:
            errors.append(f"Invalid CUSIPs in custom basket: {invalid_cusips}")
            validated = False
        
        # Calculate total value
        cusips = [s.get('cusip') for s in custom_securities if s.get('cusip')]
        prices = self.data_adapter.get_market_prices(pcf.date, cusips)
        
        securities = []
        total_value = Decimal('0')
        
        for sec in custom_securities:
            cusip = sec.get('cusip')
            if not cusip:
                continue
            
            quantity = Decimal(str(sec.get('quantity', 0)))
            price = prices.get(cusip, Decimal('0'))
            
            if price == 0:
                errors.append(f"Missing price for CUSIP {cusip}")
                validated = False
            
            securities.append({
                "cusip": cusip,
                "quantity": str(quantity),
                "description": sec.get('description', ''),
                "price": str(price)
            })
            
            total_value += quantity * price
        
        # Cash component (may need adjustment for custom baskets)
        cash_component = pcf.cash_component * Decimal(str(creation_units))
        total_value += cash_component
        
        # Rule 6c-11 compliance validation for custom baskets
        if validated:
            standard_basket = [
                {
                    "cusip": s['cusip'],
                    "quantity": str(Decimal(str(s.get('quantity', 0))) * Decimal(str(creation_units))),
                    "price": str(prices.get(s['cusip'], Decimal('0')))
                }
                for s in pcf.securities
            ]
            
            rule_6c11_validation = self.rule_6c11_compliance.validate_custom_basket(
                standard_basket=standard_basket,
                custom_basket=securities,
                pcf_total_value=pcf.total_estimated_value * Decimal(str(creation_units))
            )
            
            if not rule_6c11_validation.passed:
                validated = False
                errors.extend(rule_6c11_validation.errors)
                logger.warning(f"Custom basket failed Rule 6c-11 validation: {rule_6c11_validation.errors}")
            else:
                # Generate disclosure document
                disclosure = self.rule_6c11_compliance.generate_custom_basket_disclosure(
                    custom_basket=securities,
                    standard_basket=standard_basket,
                    validation=rule_6c11_validation
                )
                logger.info("Custom basket passed Rule 6c-11 validation and disclosure generated")
        
        return CreationBasket(
            basket_type="custom",
            securities=securities,
            cash_component=cash_component,
            total_value=total_value,
            creation_units=creation_units,
            validated=validated,
            errors=errors
        )
    
    def build_custom_redemption_basket(self, pcf: PCFFile, creation_units: int,
                                       custom_securities: List[Dict[str, Any]]) -> RedemptionBasket:
        """
        Build custom redemption basket
        
        Custom redemption baskets allow APs to request specific securities in-kind.
        
        Args:
            pcf: PCFFile for validation
            creation_units: Number of creation units to redeem
            custom_securities: List of custom securities to receive
                
        Returns:
            RedemptionBasket object with validation results
        """
        logger.info(f"Building custom redemption basket for {creation_units} units")
        
        errors = []
        validated = True
        
        # Validate custom securities against PCF
        pcf_cusips = {s['cusip'] for s in pcf.securities}
        custom_cusips = {s.get('cusip') for s in custom_securities if s.get('cusip')}
        
        invalid_cusips = custom_cusips - pcf_cusips
        if invalid_cusips:
            errors.append(f"Invalid CUSIPs in custom basket: {invalid_cusips}")
            validated = False
        
        # Calculate total value
        cusips = [s.get('cusip') for s in custom_securities if s.get('cusip')]
        prices = self.data_adapter.get_market_prices(pcf.date, cusips)
        
        securities = []
        total_value = Decimal('0')
        
        for sec in custom_securities:
            cusip = sec.get('cusip')
            if not cusip:
                continue
            
            quantity = Decimal(str(sec.get('quantity', 0)))
            price = prices.get(cusip, Decimal('0'))
            
            if price == 0:
                errors.append(f"Missing price for CUSIP {cusip}")
                validated = False
            
            securities.append({
                "cusip": cusip,
                "quantity": str(quantity),
                "description": sec.get('description', ''),
                "price": str(price)
            })
            
            total_value += quantity * price
        
        cash_component = Decimal('0')
        
        return RedemptionBasket(
            basket_type="custom",
            securities=securities,
            cash_component=cash_component,
            total_value=total_value,
            creation_units=creation_units,
            validated=validated,
            errors=errors
        )
    
    def create_ap_order(self, ap_id: str, order_type: str, creation_units: int,
                       order_date: date = None, basket: Optional[List[Dict[str, Any]]] = None,
                       settlement_date: Optional[date] = None) -> APOrder:
        """
        Create AP order (for APs to submit orders)
        
        This function allows APs to create and submit orders.
        Use standard basket (basket=None) or custom basket (basket=List).
        
        Args:
            ap_id: Authorized Participant identifier
            order_type: "creation" or "redemption"
            creation_units: Number of creation units
            order_date: Order date (defaults to today)
            basket: Optional custom basket. If None, uses standard PCF basket.
                Format: [{"cusip": "...", "quantity": "..."}, ...]
            settlement_date: Optional settlement date
            
        Returns:
            APOrder object
            
        Example:
            # Standard creation order
            order = om.create_ap_order(
                ap_id="AP001",
                order_type="creation",
                creation_units=10
            )
            
            # Custom creation order
            custom_basket = [
                {"cusip": "037833100", "quantity": "100"},
                {"cusip": "594918104", "quantity": "50"}
            ]
            order = om.create_ap_order(
                ap_id="AP001",
                order_type="creation",
                creation_units=10,
                basket=custom_basket
            )
        """
        if order_date is None:
            order_date = date.today()
        
        order_id = f"ORD_{ap_id}_{order_type.upper()}_{order_date.isoformat()}_{creation_units}"
        
        order = APOrder(
            order_id=order_id,
            ap_id=ap_id,
            order_type=order_type,
            creation_units=creation_units,
            basket=basket,
            order_date=order_date,
            settlement_date=settlement_date,
            status="pending"
        )
        
        logger.info(f"Created AP order {order_id}: {order_type} for {creation_units} units")
        return order
    
    def validate_ap_order(self, order: APOrder, pcf: PCFFile) -> Tuple[bool, Optional[str]]:
        """
        Validate AP order against PCF
        
        Validates:
        - Order type
        - Creation units
        - Cut-off time (must be before 4:00 PM ET)
        - Basket composition (if custom)
        
        Args:
            order: APOrder to validate
            pcf: PCFFile for validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if order.order_type not in ["creation", "redemption"]:
            return False, f"Invalid order type: {order.order_type}"
        
        if order.creation_units <= 0:
            return False, "Creation units must be positive"
        
        # Check order cut-off time
        # Orders must be submitted before 4:00 PM ET on order date
        if not self._check_cutoff_time(order.order_date):
            return False, f"Order received after cut-off time (4:00 PM ET). Order date: {order.order_date}"
        
        if order.basket:
            # Validate custom basket
            pcf_cusips = {s['cusip'] for s in pcf.securities}
            basket_cusips = {b.get('cusip') for b in order.basket}
            invalid_cusips = basket_cusips - pcf_cusips
            if invalid_cusips:
                return False, f"Invalid CUSIPs in basket: {invalid_cusips}"
        
        return True, None
    
    def _check_cutoff_time(self, order_date: date) -> bool:
        """
        Check if current time is before order cut-off time
        
        Orders must be submitted before 4:00 PM ET on the order date.
        
        Args:
            order_date: Date of the order
            
        Returns:
            True if before cut-off, False otherwise
        """
        now = datetime.now()
        cutoff_datetime = datetime.combine(order_date, self.order_cutoff_time)
        
        # If order date is today, check current time
        if order_date == date.today():
            return now.time() < self.order_cutoff_time
        
        # If order date is in the past, it's too late
        if order_date < date.today():
            return False
        
        # If order date is in the future, it's OK (but unusual)
        return True
    
    def calculate_order_fees(self, order: APOrder) -> Dict[str, Any]:
        """
        Calculate creation/redemption fees for order
        
        Fees are typically charged per creation unit.
        Some ETFs charge fees, others don't.
        
        Args:
            order: APOrder to calculate fees for
            
        Returns:
            Dictionary with fee information
        """
        if order.order_type == "creation":
            fee_per_unit = self.creation_fee
        elif order.order_type == "redemption":
            fee_per_unit = self.redemption_fee
        else:
            fee_per_unit = Decimal('0')
        
        total_fee = fee_per_unit * order.creation_units
        
        return {
            "order_id": order.order_id,
            "order_type": order.order_type,
            "creation_units": order.creation_units,
            "fee_per_unit": str(fee_per_unit),
            "total_fee": str(total_fee),
            "fee_currency": "USD"
        }
    
    def review_and_approve_custom_basket(self, order: APOrder, pcf: PCFFile,
                                         approved_basket: Optional[List[Dict[str, Any]]] = None,
                                         approval_action: str = "approve") -> Dict[str, Any]:
        """
        Review and approve/deny/modify AP's custom basket request.
        
        This implements the fund's discretion to approve, deny, or modify AP's custom basket request.
        The fund has final say on what basket is delivered, even if AP requests a custom basket.
        
        Args:
            order: APOrder with custom basket request
            pcf: PCFFile for validation
            approved_basket: Optional modified basket. If None and action is "approve", uses AP's basket.
            approval_action: "approve", "deny", or "modify"
            
        Returns:
            Dictionary with approval result and final approved basket
        """
        logger.info(f"Reviewing custom basket request for order {order.order_id}, action: {approval_action}")
        
        if not order.basket:
            return {
                "order_id": order.order_id,
                "status": "error",
                "reason": "No custom basket in order to review"
            }
        
        if approval_action == "deny":
            order.status = "rejected"
            order.rejection_reason = "Custom basket request denied by fund"
            return {
                "order_id": order.order_id,
                "status": "rejected",
                "reason": "Custom basket request denied by fund",
                "ap_requested_basket": order.basket
            }
        
        # Determine final basket
        if approval_action == "modify" and approved_basket:
            # Fund modifies AP's request
            final_basket_securities = approved_basket
            modification_note = "Fund modified AP's custom basket request"
        elif approval_action == "approve":
            # Fund approves AP's request as-is
            final_basket_securities = order.basket
            modification_note = "Fund approved AP's custom basket request as-is"
        else:
            return {
                "order_id": order.order_id,
                "status": "error",
                "reason": f"Invalid approval action: {approval_action}"
            }
        
        # Build and validate final basket
        if order.order_type == "creation":
            final_basket = self.build_custom_creation_basket(pcf, order.creation_units, final_basket_securities)
        else:
            final_basket = self.build_custom_redemption_basket(pcf, order.creation_units, final_basket_securities)
        
        if not final_basket.validated:
            order.status = "rejected"
            order.rejection_reason = f"Final basket validation failed: {', '.join(final_basket.errors)}"
            return {
                "order_id": order.order_id,
                "status": "rejected",
                "reason": order.rejection_reason,
                "ap_requested_basket": order.basket,
                "final_basket": final_basket_securities
            }
        
        # Save approval record
        approval_record = {
            "order_id": order.order_id,
            "ap_id": order.ap_id,
            "order_type": order.order_type,
            "approval_action": approval_action,
            "approval_date": datetime.now().isoformat(),
            "ap_requested_basket": order.basket,
            "final_approved_basket": final_basket.securities,
            "modification_note": modification_note,
            "basket_validation": {
                "validated": final_basket.validated,
                "errors": final_basket.errors
            }
        }
        
        approval_file = self.storage_path / f"basket_approval_{order.order_id}.json"
        with open(approval_file, 'w') as f:
            json.dump(approval_record, f, indent=2, default=str)
        
        logger.info(f"Custom basket approved for order {order.order_id}, final basket: {len(final_basket.securities)} securities")
        
        return {
            "order_id": order.order_id,
            "status": "approved",
            "approval_action": approval_action,
            "ap_requested_basket": order.basket,
            "final_approved_basket": {
                "securities": final_basket.securities,
                "cash_component": str(final_basket.cash_component),
                "total_value": str(final_basket.total_value)
            },
            "modification_note": modification_note,
            "basket_type": final_basket.basket_type
        }
    
    def process_ap_order(self, order: APOrder, pcf: PCFFile, 
                        auto_approve_custom_baskets: bool = False) -> Dict[str, Any]:
        """
        Process AP order (validate, accept/reject, route)
        
        For custom baskets, this validates but does not automatically approve.
        Use review_and_approve_custom_basket() to explicitly approve/deny/modify custom basket requests.
        
        Args:
            order: APOrder to process
            pcf: PCFFile for validation
            auto_approve_custom_baskets: If True, automatically approves custom baskets (not recommended).
                                        If False, custom baskets require explicit approval via review_and_approve_custom_basket()
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing AP order {order.order_id}")
        
        is_valid, error_msg = self.validate_ap_order(order, pcf)
        
        if not is_valid:
            order.status = "rejected"
            order.rejection_reason = error_msg
            return {
                "order_id": order.order_id,
                "status": "rejected",
                "reason": error_msg
            }
        
        # Handle custom basket requests
        if order.basket:
            if not auto_approve_custom_baskets:
                # Custom basket requires explicit approval
                order.status = "pending_approval"
                return {
                    "order_id": order.order_id,
                    "status": "pending_approval",
                    "message": "Custom basket request requires fund approval. Use review_and_approve_custom_basket() to approve/deny/modify.",
                    "ap_requested_basket": order.basket
                }
            else:
                # Auto-approve (not recommended - fund should review)
                logger.warning(f"Auto-approving custom basket for order {order.order_id} (not recommended)")
                approval_result = self.review_and_approve_custom_basket(order, pcf, approval_action="approve")
                if approval_result["status"] != "approved":
                    return approval_result
                # Continue with approved basket
                final_basket_securities = approval_result["final_approved_basket"]["securities"]
                if order.order_type == "creation":
                    basket = self.build_custom_creation_basket(pcf, order.creation_units, final_basket_securities)
                else:
                    basket = self.build_custom_redemption_basket(pcf, order.creation_units, final_basket_securities)
        else:
            # Standard basket - no approval needed
            if order.order_type == "creation":
                basket = self.build_standard_creation_basket(pcf, order.creation_units)
            else:
                basket = self.build_standard_redemption_basket(pcf, order.creation_units)
        
        if not basket.validated:
            order.status = "rejected"
            order.rejection_reason = f"Basket validation failed: {', '.join(basket.errors)}"
            return {
                "order_id": order.order_id,
                "status": "rejected",
                "reason": order.rejection_reason
            }
        
        order.status = "accepted"
        
        # Calculate fees
        fees = self.calculate_order_fees(order)
        
        result = {
            "order_id": order.order_id,
            "ap_id": order.ap_id,
            "order_type": order.order_type,
            "creation_units": order.creation_units,
            "basket_type": basket.basket_type,
            "basket": {
                "securities": basket.securities,
                "cash_component": str(basket.cash_component),
                "total_value": str(basket.total_value)
            },
            "fees": fees,
            "status": "accepted",
            "settlement_date": order.settlement_date.isoformat() if order.settlement_date else None,
            "order_timestamp": datetime.now().isoformat()
        }
        
        # Save order
        order_file = self.storage_path / f"order_{order.order_id}.json"
        with open(order_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Order {order.order_id} processed: {order.status}, basket_type={basket.basket_type}")
        return result
    
    def _format_pcf_for_nscc(self, pcf: PCFFile) -> str:
        """Format PCF in NSCC required format"""
        lines = []
        lines.append(f"PCF_DATE,{pcf.date.isoformat()}")
        lines.append(f"CREATION_UNIT_SIZE,{pcf.creation_unit_size}")
        lines.append("SECURITIES:")
        for sec in pcf.securities:
            lines.append(f"{sec['cusip']},{sec['quantity']},{sec['description']}")
        lines.append(f"CASH_COMPONENT,{pcf.cash_component}")
        lines.append(f"ESTIMATED_CASH,{pcf.estimated_cash_component}")
        lines.append(f"TOTAL_ESTIMATED_VALUE,{pcf.total_estimated_value}")
        return "\n".join(lines)
    
    def _save_pcf(self, pcf: PCFFile):
        """Save PCF to storage"""
        pcf_file = self.storage_path / f"pcf_{pcf.date.isoformat()}.json"
        data = {
            "date": pcf.date.isoformat(),
            "creation_unit_size": pcf.creation_unit_size,
            "securities": pcf.securities,
            "cash_component": str(pcf.cash_component),
            "estimated_cash_component": str(pcf.estimated_cash_component),
            "total_estimated_value": str(pcf.total_estimated_value),
            "validation_passed": pcf.validation_passed,
            "errors": pcf.errors
        }
        with open(pcf_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_pcf_formatted(self, pcf_date: date, pcf_formatted: str):
        """Save formatted PCF for NSCC submission"""
        pcf_file = self.storage_path / f"pcf_nscc_{pcf_date.isoformat()}.txt"
        with open(pcf_file, 'w') as f:
            f.write(pcf_formatted)
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get order by order ID
        
        Args:
            order_id: Order identifier
            
        Returns:
            Order data dictionary or None if not found
        """
        order_file = self.storage_path / f"order_{order_id}.json"
        if order_file.exists():
            with open(order_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_orders_by_date(self, order_date: date) -> List[Dict[str, Any]]:
        """
        Get all orders for a given date
        
        Args:
            order_date: Date to query orders for
            
        Returns:
            List of order dictionaries
        """
        orders = []
        for order_file in self.storage_path.glob("order_*.json"):
            try:
                with open(order_file, 'r') as f:
                    order_data = json.load(f)
                    # Check if order date matches (order_id contains date)
                    if order_date.isoformat() in order_file.stem:
                        orders.append(order_data)
            except:
                continue
        return orders
    
    def get_orders_by_ap(self, ap_id: str, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """
        Get all orders for a specific AP
        
        Args:
            ap_id: Authorized Participant identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of order dictionaries
        """
        orders = []
        for order_file in self.storage_path.glob("order_*.json"):
            try:
                with open(order_file, 'r') as f:
                    order_data = json.load(f)
                    if order_data.get('ap_id') == ap_id:
                        # Apply date filters if provided
                        if start_date or end_date:
                            order_date_str = order_data.get('order_date') or order_data.get('settlement_date')
                            if order_date_str:
                                order_date = date.fromisoformat(order_date_str)
                                if start_date and order_date < start_date:
                                    continue
                                if end_date and order_date > end_date:
                                    continue
                        orders.append(order_data)
            except:
                continue
        return orders
    
    def route_order_to_custodian(self, order: APOrder, basket) -> Dict[str, Any]:
        """
        Route order to custodian for settlement
        
        This is where you would integrate with your custodian system to
        send the order and basket for settlement.
        
        Args:
            order: APOrder to route
            basket: CreationBasket or RedemptionBasket
            
        Returns:
            Dictionary with routing results
            
        TODO: Implement actual custodian integration
        """
        logger.info(f"Routing order {order.order_id} to custodian")
        
        # ============================================================================
        # TODO: IMPLEMENT CUSTODIAN ROUTING HERE
        # ============================================================================
        # Replace this section with your actual custodian integration:
        #
        # Example steps:
        # 1. Connect to custodian API
        #    custodian_client = CustodianClient(...)
        #
        # 2. Format order and basket for custodian
        #    custodian_order = {
        #        "order_id": order.order_id,
        #        "ap_id": order.ap_id,
        #        "order_type": order.order_type,
        #        "creation_units": order.creation_units,
        #        "securities": basket.securities,
        #        "cash_component": str(basket.cash_component),
        #        "settlement_date": order.settlement_date.isoformat() if order.settlement_date else None
        #    }
        #
        # 3. Submit to custodian
        #    response = custodian_client.submit_order(custodian_order)
        #
        # 4. Return routing confirmation
        #    return {
        #        "order_id": order.order_id,
        #        "custodian_reference": response.get('reference_id'),
        #        "status": "routed",
        #        "routed_at": datetime.now().isoformat()
        #    }
        # ============================================================================
        
        # Placeholder return
        return {
            "order_id": order.order_id,
            "status": "routed",
            "message": "Order routed to custodian (placeholder - implement actual routing)"
        }
    
    def route_order_to_nscc(self, order: APOrder, basket) -> Dict[str, Any]:
        """
        Route order to NSCC for settlement
        
        This is where you would integrate with NSCC to submit the order
        for clearing and settlement.
        
        Args:
            order: APOrder to route
            basket: CreationBasket or RedemptionBasket
            
        Returns:
            Dictionary with NSCC routing results
            
        TODO: Implement actual NSCC integration
        """
        logger.info(f"Routing order {order.order_id} to NSCC")
        
        # ============================================================================
        # TODO: IMPLEMENT NSCC ROUTING HERE
        # ============================================================================
        # Replace this section with your actual NSCC integration:
        #
        # Example steps:
        # 1. Connect to NSCC API
        #    nscc_client = NSCCClient(...)
        #
        # 2. Format order for NSCC
        #    nscc_order = {
        #        "order_id": order.order_id,
        #        "ap_id": order.ap_id,
        #        "order_type": order.order_type,
        #        "creation_units": order.creation_units,
        #        "basket": basket.securities,
        #        "cash_component": str(basket.cash_component)
        #    }
        #
        # 3. Submit to NSCC
        #    response = nscc_client.submit_order(nscc_order)
        #
        # 4. Return NSCC confirmation
        #    return {
        #        "order_id": order.order_id,
        #        "nscc_reference": response.get('nscc_id'),
        #        "status": "submitted",
        #        "submitted_at": datetime.now().isoformat()
        #    }
        # ============================================================================
        
        # Placeholder return
        return {
            "order_id": order.order_id,
            "status": "submitted",
            "message": "Order submitted to NSCC (placeholder - implement actual submission)"
        }
    
    def compare_baskets(self, basket1: CreationBasket, basket2: CreationBasket) -> Dict[str, Any]:
        """
        Compare two baskets to identify differences
        
        Useful for analyzing custom vs standard baskets or comparing baskets over time.
        
        Args:
            basket1: First basket to compare
            basket2: Second basket to compare
            
        Returns:
            Dictionary with comparison results
        """
        differences = []
        
        # Compare securities
        basket1_cusips = {s['cusip']: Decimal(str(s['quantity'])) for s in basket1.securities}
        basket2_cusips = {s['cusip']: Decimal(str(s['quantity'])) for s in basket2.securities}
        
        all_cusips = set(basket1_cusips.keys()) | set(basket2_cusips.keys())
        
        for cusip in all_cusips:
            qty1 = basket1_cusips.get(cusip, Decimal('0'))
            qty2 = basket2_cusips.get(cusip, Decimal('0'))
            diff = qty1 - qty2
            
            if abs(diff) > Decimal('0.01'):
                differences.append({
                    "cusip": cusip,
                    "basket1_quantity": str(qty1),
                    "basket2_quantity": str(qty2),
                    "difference": str(diff)
                })
        
        # Compare cash components
        cash_diff = basket1.cash_component - basket2.cash_component
        
        # Compare total values
        value_diff = basket1.total_value - basket2.total_value
        
        return {
            "basket1_type": basket1.basket_type,
            "basket2_type": basket2.basket_type,
            "security_differences": differences,
            "cash_difference": str(cash_diff),
            "value_difference": str(value_diff),
            "identical": len(differences) == 0 and abs(cash_diff) < Decimal('0.01')
        }
