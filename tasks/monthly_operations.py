#!/usr/bin/env python3
"""
Monthly Operations Task
Runs monthly operations for all functions
"""

import sys
from pathlib import Path
from datetime import date
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.etf import (
    Accounting,
    FundAdministration,
    Distributor,
    FileBasedDataSourceAdapter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_monthly_operations(month_end_date: date = None):
    """Run monthly operations"""
    
    if month_end_date is None:
        month_end_date = date.today()
    
    month_start_date = date(month_end_date.year, month_end_date.month, 1)
    
    logger.info(f"Running monthly operations for {month_end_date.strftime('%B %Y')}")
    
    data_adapter = FileBasedDataSourceAdapter(data_path="./data")
    
    accounting = Accounting(data_adapter)
    admin = FundAdministration(data_adapter)
    distributor = Distributor(data_adapter)
    
    results = {
        "month_start": month_start_date.isoformat(),
        "month_end": month_end_date.isoformat(),
        "operations": {}
    }
    
    try:
        # Generate monthly financial statements
        logger.info("Generating monthly financial statements")
        
        # Accounting: Balance sheet and income statement
        bs = accounting.generate_balance_sheet(month_end_date)
        results["operations"]["balance_sheet"] = {
            "total_assets": bs.data["total_assets"],
            "total_liabilities": bs.data["total_liabilities"],
            "total_equity": bs.data["total_equity"]
        }
        
        is_stmt = accounting.generate_income_statement(month_start_date, month_end_date)
        results["operations"]["income_statement"] = {
            "total_income": is_stmt.data["total_income"],
            "total_expenses": is_stmt.data["total_expenses"],
            "net_income": is_stmt.data["net_income"]
        }
        
        # Distributor: Distribution schedule
        dist_schedule = distributor.generate_distribution_schedule(month_end_date.year)
        results["operations"]["distribution_schedule"] = {
            "total_distributions": dist_schedule["total_distributions"],
            "total_amount": dist_schedule["total_amount"]
        }
        
        logger.info("Monthly operations completed")
        
    except Exception as e:
        logger.error(f"Error in monthly operations: {e}", exc_info=True)
        results["error"] = str(e)
    
    # Save results
    results_file = Path("./data") / f"monthly_operations_{month_end_date.isoformat()}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run monthly operations")
    parser.add_argument("--date", type=str, help="Month end date (YYYY-MM-DD), defaults to today")
    
    args = parser.parse_args()
    
    if args.date:
        month_end_date = date.fromisoformat(args.date)
    else:
        month_end_date = date.today()
    
    results = run_monthly_operations(month_end_date)
    print(f"Monthly operations completed for {month_end_date.strftime('%B %Y')}")

