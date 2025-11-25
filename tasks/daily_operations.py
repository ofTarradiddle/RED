#!/usr/bin/env python3
"""
Daily Operations Task
Runs all daily operations for Accounting, Admin, TA, OM, and Distributor
"""

import sys
from pathlib import Path
from datetime import date, datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.etf import (
    Accounting,
    FundAdministration,
    TransferAgent,
    OrderManagement,
    Distributor,
    FileBasedDataSourceAdapter,
    ExampleDataSourceAdapter
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_daily_operations(operation_date: date = None, data_adapter=None):
    """Run all daily operations"""
    
    if operation_date is None:
        operation_date = date.today()
    
    if data_adapter is None:
        # Use file-based adapter for testing
        data_adapter = FileBasedDataSourceAdapter(data_path="./data")
    
    logger.info(f"Starting daily operations for {operation_date}")
    
    # Initialize all functions
    accounting = Accounting(data_adapter)
    admin = FundAdministration(data_adapter)
    ta = TransferAgent(data_adapter)
    om = OrderManagement(data_adapter)
    distributor = Distributor(data_adapter)
    
    results = {
        "date": operation_date.isoformat(),
        "accounting": {},
        "admin": {},
        "ta": {},
        "om": {},
        "distributor": {}
    }
    
    try:
        # 1. Admin: Calculate NAV (needed for other operations)
        logger.info("Step 1: Calculating NAV")
        nav_result = admin.calculate_nav(operation_date)
        results["admin"]["nav"] = {
            "nav_per_share": str(nav_result.nav_per_share),
            "net_assets": str(nav_result.net_assets),
            "validation_passed": nav_result.validation_passed,
            "pricing_exceptions": nav_result.pricing_exceptions
        }
        
        # 2. Admin: Reconcile holdings and cash
        logger.info("Step 2: Reconciling holdings and cash")
        recon_result = admin.reconcile_holdings_cash(operation_date)
        results["admin"]["reconciliation"] = recon_result
        
        # 3. TA: Daily reconciliation
        logger.info("Step 3: TA daily reconciliation")
        ta_recon = ta.daily_reconciliation(operation_date)
        results["ta"]["reconciliation"] = {
            "status": ta_recon.status,
            "difference": str(ta_recon.difference),
            "exceptions": ta_recon.exceptions
        }
        
        # 4. TA: Update Cede file
        logger.info("Step 4: Updating Cede file")
        cede_result = ta.update_cede_file(operation_date)
        results["ta"]["cede_update"] = cede_result
        
        # 5. TA: Process creation/redemption orders
        logger.info("Step 5: Processing creation/redemption orders")
        orders_result = ta.process_creation_redemption_orders(operation_date)
        results["ta"]["orders"] = orders_result
        
        # 6. OM: Generate PCF
        logger.info("Step 6: Generating PCF")
        pcf_result = om.generate_pcf(operation_date)
        results["om"]["pcf"] = {
            "securities_count": len(pcf_result.securities),
            "total_estimated_value": str(pcf_result.total_estimated_value),
            "validation_passed": pcf_result.validation_passed,
            "errors": pcf_result.errors
        }
        
        # 7. OM: Process AP orders
        logger.info("Step 7: Processing AP orders")
        ap_orders = data_adapter.get_ap_orders(operation_date)
        processed_orders = []
        for order in ap_orders:
            if order.status == "pending":
                processed_orders.append(om.process_ap_order(order, pcf_result))
        results["om"]["orders"] = processed_orders
        
        # 8. Accounting: Daily accounting operations
        logger.info("Step 8: Running accounting operations")
        nav_data = {
            "total_assets": str(nav_result.total_assets),
            "total_liabilities": str(nav_result.total_liabilities),
            "net_assets": str(nav_result.net_assets)
        }
        accounting_result = accounting.daily_accounting_operations(operation_date, nav_data)
        results["accounting"] = accounting_result
        
        # 9. Distributor: Check for pending distributions
        logger.info("Step 9: Checking distributions")
        pending_dist = distributor.get_pending_distributions(operation_date)
        due_dist = distributor.get_distributions_due(operation_date)
        results["distributor"]["pending"] = len(pending_dist)
        results["distributor"]["due"] = len(due_dist)
        
        logger.info("Daily operations completed successfully")
        
    except Exception as e:
        logger.error(f"Error in daily operations: {e}", exc_info=True)
        results["error"] = str(e)
    
    # Save results
    results_file = Path("./data") / f"daily_operations_{operation_date.isoformat()}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run daily operations")
    parser.add_argument("--date", type=str, help="Operation date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--adapter", type=str, default="file", choices=["file", "custom"],
                       help="Data adapter type")
    
    args = parser.parse_args()
    
    if args.date:
        operation_date = date.fromisoformat(args.date)
    else:
        operation_date = date.today()
    
    if args.adapter == "file":
        data_adapter = FileBasedDataSourceAdapter(data_path="./data")
    else:
        # Use custom adapter
        from lib.etf import ExampleDataSourceAdapter
        data_adapter = ExampleDataSourceAdapter(config={})
    
    results = run_daily_operations(operation_date, data_adapter)
    
    print(f"\nDaily Operations Results for {operation_date}:")
    print(f"NAV: ${results['admin']['nav']['nav_per_share']}")
    print(f"TA Reconciliation: {results['ta']['reconciliation']['status']}")
    print(f"PCF Securities: {results['om']['pcf']['securities_count']}")
    print(f"Accounting Entries: {len(results['accounting'].get('nav_entries', []))}")

