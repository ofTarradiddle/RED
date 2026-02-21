#!/usr/bin/env python3
"""
Weekly Operations Task
Runs weekly operations for all functions
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.etf import (
    Accounting,
    FundAdministration,
    TransferAgent,
    OrderManagement,
    Distributor,
    FileBasedDataSourceAdapter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_weekly_operations(week_end_date: date = None):
    """Run weekly operations"""
    
    if week_end_date is None:
        week_end_date = date.today()
    
    week_start_date = week_end_date - timedelta(days=6)
    
    logger.info(f"Running weekly operations for week ending {week_end_date}")
    
    data_adapter = FileBasedDataSourceAdapter(data_path="./data")
    
    accounting = Accounting(data_adapter)
    admin = FundAdministration(data_adapter)
    ta = TransferAgent(data_adapter)
    om = OrderManagement(data_adapter)
    distributor = Distributor(data_adapter)
    
    results = {
        "week_start": week_start_date.isoformat(),
        "week_end": week_end_date.isoformat(),
        "operations": {}
    }
    
    try:
        # Generate weekly reports
        logger.info("Generating weekly reports")
        
        # Accounting: Trial balance
        tb = accounting.generate_trial_balance(week_end_date)
        results["operations"]["trial_balance"] = {
            "balanced": tb.balanced,
            "total_debits": str(tb.total_debits),
            "total_credits": str(tb.total_credits)
        }
        
        # Admin: Expense ratio calculation
        er = admin.calculate_expense_ratio(week_start_date, week_end_date)
        results["operations"]["expense_ratio"] = er
        
        logger.info("Weekly operations completed")
        
    except Exception as e:
        logger.error(f"Error in weekly operations: {e}", exc_info=True)
        results["error"] = str(e)
    
    # Save results
    results_file = Path("./data") / f"weekly_operations_{week_end_date.isoformat()}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run weekly operations")
    parser.add_argument("--date", type=str, help="Week end date (YYYY-MM-DD), defaults to today")
    
    args = parser.parse_args()
    
    if args.date:
        week_end_date = date.fromisoformat(args.date)
    else:
        week_end_date = date.today()
    
    results = run_weekly_operations(week_end_date)
    print(f"Weekly operations completed for week ending {week_end_date}")

