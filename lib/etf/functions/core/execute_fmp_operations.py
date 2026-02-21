"""
Execute FMP-Based Accounting & Administration Operations
Complete end-to-end execution of in-house ETF operations using FMP APIs

This script demonstrates how to run all accounting and admin responsibilities
using the FMP Data Source Adapter and FMP-Enhanced Workflows.
"""

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.etf.adapters.fmp_adapter import FMPDataSourceAdapter
from lib.etf.functions.core.fmp_workflows import FMPEnhancedWorkflows
from lib.etf.functions.core.orchestrator import DailyOrchestrator
from lib.etf.functions.research.core.backtesting import FMPClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fmp_operations.log')
    ]
)
logger = logging.getLogger(__name__)


def load_manual_holdings(holdings_file: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load manual holdings from file (for pre-launch ETFs or custom portfolios).
    
    Expected format (JSON or CSV):
    [
        {
            "ticker": "AAPL",
            "cusip": "037833100",
            "quantity": 1000,
            "weight": 5.0,
            "market_value": 150000.00,
            "name": "Apple Inc."
        },
        ...
    ]
    """
    if not holdings_file:
        return []
    
    holdings_path = Path(holdings_file)
    if not holdings_path.exists():
        logger.warning(f"Holdings file not found: {holdings_file}")
        return []
    
    import json
    import pandas as pd
    
    try:
        if holdings_path.suffix == '.json':
            with open(holdings_path, 'r') as f:
                holdings = json.load(f)
        elif holdings_path.suffix == '.csv':
            df = pd.read_csv(holdings_path)
            holdings = df.to_dict('records')
        else:
            logger.error(f"Unsupported file format: {holdings_path.suffix}")
            return []
        
        logger.info(f"Loaded {len(holdings)} holdings from {holdings_file}")
        return holdings
    except Exception as e:
        logger.error(f"Error loading holdings file: {e}")
        return []


def execute_daily_operations(
    operation_date: date,
    etf_symbol: str = "",
    manual_holdings_file: Optional[str] = None,
    benchmark_symbol: str = "SPY",
    storage_path: str = "./data/admin"
) -> Dict[str, Any]:
    """
    Execute all daily accounting and administration operations using FMP APIs.
    
    This function runs the complete daily workflow:
    1. Daily price import and NAV calculation
    2. Corporate actions processing
    3. Dividend accrual tracking
    4. Expense accrual and fee booking
    5. NAV verification and reconciliation
    6. Accounting entries (NAV, expenses, income)
    7. Trial balance generation
    
    Args:
        operation_date: Date to run operations for
        etf_symbol: ETF symbol (optional if using manual holdings)
        manual_holdings_file: Path to manual holdings file (for pre-launch ETFs)
        benchmark_symbol: Benchmark symbol for NAV verification
        storage_path: Path for storing operation outputs
        
    Returns:
        Dictionary with results from all operations
    """
    logger.info("=" * 80)
    logger.info(f"EXECUTING DAILY OPERATIONS FOR {operation_date}")
    logger.info("=" * 80)
    
    # Get FMP API key
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        logger.error("FMP_API_KEY not found in environment variables")
        return {"error": "FMP_API_KEY not configured"}
    
    # Load manual holdings if provided
    manual_holdings = load_manual_holdings(manual_holdings_file)
    
    try:
        # Initialize FMP client
        fmp_client = FMPClient(api_key=api_key)
        
        # Create FMP adapter
        fmp_adapter = FMPDataSourceAdapter(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            manual_holdings=manual_holdings
        )
        
        # Initialize FMP-enhanced workflows
        workflows = FMPEnhancedWorkflows(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            storage_path=storage_path,
            manual_holdings=manual_holdings
        )
        
        # Run all daily operations
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING FMP-ENHANCED DAILY OPERATIONS")
        logger.info("=" * 80)
        
        results = workflows.run_daily_operations(operation_date, benchmark_symbol)
        
        logger.info("\n" + "=" * 80)
        logger.info("DAILY OPERATIONS COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Results saved to: {storage_path}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error executing daily operations: {e}", exc_info=True)
        return {"error": str(e)}


def execute_monthly_close(
    period_end: date,
    etf_symbol: str = "",
    manual_holdings_file: Optional[str] = None,
    storage_path: str = "./data/admin"
) -> Dict[str, Any]:
    """
    Execute monthly close operations using FMP APIs.
    
    This includes:
    1. Period-end NAV calculation
    2. Financial statement generation (Balance Sheet, Income Statement)
    3. Trial balance
    4. Security identifier lookups for reporting
    
    Args:
        period_end: End date of the period
        etf_symbol: ETF symbol
        manual_holdings_file: Path to manual holdings file
        storage_path: Path for storing outputs
        
    Returns:
        Dictionary with monthly close results
    """
    logger.info("=" * 80)
    logger.info(f"EXECUTING MONTHLY CLOSE FOR {period_end}")
    logger.info("=" * 80)
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        logger.error("FMP_API_KEY not found")
        return {"error": "FMP_API_KEY not configured"}
    
    manual_holdings = load_manual_holdings(manual_holdings_file)
    
    try:
        fmp_client = FMPClient(api_key=api_key)
        workflows = FMPEnhancedWorkflows(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            storage_path=storage_path,
            manual_holdings=manual_holdings
        )
        
        results = workflows.monthly_quarterly_close(period_end, period_type="monthly")
        
        logger.info("Monthly close completed")
        return results
        
    except Exception as e:
        logger.error(f"Error in monthly close: {e}", exc_info=True)
        return {"error": str(e)}


def execute_quarterly_close(
    period_end: date,
    etf_symbol: str = "",
    manual_holdings_file: Optional[str] = None,
    storage_path: str = "./data/admin"
) -> Dict[str, Any]:
    """
    Execute quarterly close operations using FMP APIs.
    
    Similar to monthly close but for quarterly periods.
    """
    logger.info("=" * 80)
    logger.info(f"EXECUTING QUARTERLY CLOSE FOR {period_end}")
    logger.info("=" * 80)
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        return {"error": "FMP_API_KEY not configured"}
    
    manual_holdings = load_manual_holdings(manual_holdings_file)
    
    try:
        fmp_client = FMPClient(api_key=api_key)
        workflows = FMPEnhancedWorkflows(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            storage_path=storage_path,
            manual_holdings=manual_holdings
        )
        
        results = workflows.monthly_quarterly_close(period_end, period_type="quarterly")
        
        logger.info("Quarterly close completed")
        return results
        
    except Exception as e:
        logger.error(f"Error in quarterly close: {e}", exc_info=True)
        return {"error": str(e)}


def generate_monthly_factsheet(
    report_date: date,
    etf_symbol: str = "",
    manual_holdings_file: Optional[str] = None,
    storage_path: str = "./data/admin"
) -> Dict[str, Any]:
    """
    Generate monthly investor factsheet using FMP APIs.
    
    Includes:
    - NAV and AUM
    - Top 10 holdings
    - Portfolio metrics (P/E, dividend yield)
    - Sector allocations
    - Performance data
    
    Args:
        report_date: Date for factsheet
        etf_symbol: ETF symbol
        manual_holdings_file: Path to manual holdings file
        storage_path: Path for storing outputs
        
    Returns:
        Dictionary with factsheet data
    """
    logger.info("=" * 80)
    logger.info(f"GENERATING MONTHLY FACTSHEET FOR {report_date}")
    logger.info("=" * 80)
    
    api_key = os.getenv('FMP_API_KEY')
    if not api_key:
        return {"error": "FMP_API_KEY not configured"}
    
    manual_holdings = load_manual_holdings(manual_holdings_file)
    
    try:
        fmp_client = FMPClient(api_key=api_key)
        workflows = FMPEnhancedWorkflows(
            etf_symbol=etf_symbol,
            fmp_client=fmp_client,
            api_key=api_key,
            storage_path=storage_path,
            manual_holdings=manual_holdings
        )
        
        results = workflows.investor_reporting_monthly_factsheet(report_date)
        
        logger.info("Monthly factsheet generated")
        return results
        
    except Exception as e:
        logger.error(f"Error generating factsheet: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """
    Main execution function - can be run from command line or imported.
    
    Usage examples:
    
    1. Daily operations for today:
       python execute_fmp_operations.py --daily
    
    2. Daily operations for specific date:
       python execute_fmp_operations.py --daily --date 2025-01-15
    
    3. Daily operations with manual holdings:
       python execute_fmp_operations.py --daily --holdings ./data/holdings.json
    
    4. Monthly close:
       python execute_fmp_operations.py --monthly-close --date 2025-01-31
    
    5. Generate factsheet:
       python execute_fmp_operations.py --factsheet --date 2025-01-31
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Execute FMP-based accounting and administration operations'
    )
    parser.add_argument('--daily', action='store_true',
                       help='Run daily operations')
    parser.add_argument('--monthly-close', action='store_true',
                       help='Run monthly close')
    parser.add_argument('--quarterly-close', action='store_true',
                       help='Run quarterly close')
    parser.add_argument('--factsheet', action='store_true',
                       help='Generate monthly factsheet')
    parser.add_argument('--date', type=str, default=None,
                       help='Date for operations (YYYY-MM-DD, defaults to today)')
    parser.add_argument('--etf-symbol', type=str, default='',
                       help='ETF symbol (optional if using manual holdings)')
    parser.add_argument('--holdings', type=str, default=None,
                       help='Path to manual holdings file (JSON or CSV)')
    parser.add_argument('--benchmark', type=str, default='SPY',
                       help='Benchmark symbol for NAV verification')
    parser.add_argument('--storage', type=str, default='./data/admin',
                       help='Storage path for outputs')
    
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        operation_date = date.fromisoformat(args.date)
    else:
        operation_date = date.today()
    
    # Execute requested operation
    if args.daily:
        results = execute_daily_operations(
            operation_date=operation_date,
            etf_symbol=args.etf_symbol,
            manual_holdings_file=args.holdings,
            benchmark_symbol=args.benchmark,
            storage_path=args.storage
        )
        print("\n" + "=" * 80)
        print("DAILY OPERATIONS RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('operations', {}).get('nav_calculation', {}).get('status', 'unknown')}")
        
    elif args.monthly_close:
        results = execute_monthly_close(
            period_end=operation_date,
            etf_symbol=args.etf_symbol,
            manual_holdings_file=args.holdings,
            storage_path=args.storage
        )
        print("\n" + "=" * 80)
        print("MONTHLY CLOSE RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('status', 'unknown')}")
        
    elif args.quarterly_close:
        results = execute_quarterly_close(
            period_end=operation_date,
            etf_symbol=args.etf_symbol,
            manual_holdings_file=args.holdings,
            storage_path=args.storage
        )
        print("\n" + "=" * 80)
        print("QUARTERLY CLOSE RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('status', 'unknown')}")
        
    elif args.factsheet:
        results = generate_monthly_factsheet(
            report_date=operation_date,
            etf_symbol=args.etf_symbol,
            manual_holdings_file=args.holdings,
            storage_path=args.storage
        )
        print("\n" + "=" * 80)
        print("FACTSHEET RESULTS")
        print("=" * 80)
        print(f"NAV per share: ${results.get('nav_per_share', 'N/A')}")
        print(f"Total net assets: ${results.get('total_net_assets', 'N/A')}")
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

