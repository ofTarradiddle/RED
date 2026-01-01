"""
Script to fetch financial data for REDI research
Fetches income statements, balance sheets, and cash flow statements using as-reported endpoints.
Stores data on external drive in organized folder structure.
"""

import sys
from pathlib import Path
import os
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.data_fetcher import FinancialDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = 'KzXIx6bXd7l7c9mIfRddOLBZY5AAgFVq'

# Storage path - update if your external drive is mounted elsewhere
# Common locations:
# - /Volumes/My Passport/REDI
# - /Volumes/Passport/REDI
# - /media/username/Passport/REDI (Linux)

# IMPORTANT: Update this path to match where you created the REDI folder
EXTERNAL_DRIVE_PATH = Path('/Volumes/My Passport/REDI')

# If external drive has permission issues, you can test with local path first:
# EXTERNAL_DRIVE_PATH = Path('./data/research/REDI')

SYMBOLS = ['GLW']  # Testing with GLW first
PERIOD = 'annual'  # Start with annual, quarterly later
LIMIT = 1000  # Max records per request

def check_external_drive():
    """Check if external drive is accessible and create REDI directory if needed."""
    drive_path = EXTERNAL_DRIVE_PATH.parent
    
    if not drive_path.exists():
        logger.error(f"External drive not found at {drive_path}")
        logger.error("Please ensure the external drive is mounted")
        logger.error(f"Current path: {EXTERNAL_DRIVE_PATH}")
        return False
    
    # Check if REDI directory exists
    if EXTERNAL_DRIVE_PATH.exists():
        logger.info(f"✓ REDI directory exists: {EXTERNAL_DRIVE_PATH}")
    else:
        # Try to create REDI directory
        logger.info(f"Creating REDI directory: {EXTERNAL_DRIVE_PATH}")
        try:
            EXTERNAL_DRIVE_PATH.mkdir(parents=True, exist_ok=True)
            logger.info("✓ Directory created successfully")
        except PermissionError:
            logger.error("✗ Permission denied creating directory")
            logger.error("Please create the directory manually:")
            logger.error(f"  mkdir -p '{EXTERNAL_DRIVE_PATH}'")
            logger.error("Or run the script with appropriate permissions")
            return False
    
    # Check write permissions
    test_file = EXTERNAL_DRIVE_PATH / '.test_write'
    try:
        test_file.write_text('test')
        test_file.unlink()
        logger.info("✓ Write permissions confirmed")
        return True
    except PermissionError:
        logger.error("✗ No write permissions on external drive")
        logger.error(f"Please check permissions for: {EXTERNAL_DRIVE_PATH}")
        return False
    except Exception as e:
        logger.error(f"✗ Error testing write permissions: {e}")
        return False

def main():
    """Main function to fetch financial data."""
    
    logger.info("="*70)
    logger.info("REDI Financial Data Fetcher")
    logger.info("="*70)
    logger.info(f"Storage location: {EXTERNAL_DRIVE_PATH}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Period: {PERIOD}")
    logger.info(f"Max records per request: {LIMIT}")
    logger.info("="*70)
    
    # Check external drive
    if not check_external_drive():
        logger.error("\nCannot proceed without external drive access.")
        logger.error("Please fix the issue above and try again.")
        return
    
    # Initialize fetcher
    try:
        fetcher = FinancialDataFetcher(
            api_key=API_KEY,
            base_storage_path=EXTERNAL_DRIVE_PATH
        )
    except Exception as e:
        logger.error(f"Error initializing fetcher: {e}")
        return
    
    # Fetch data for all symbols
    logger.info("\n" + "="*70)
    logger.info("Starting data fetch...")
    logger.info("="*70 + "\n")
    
    summary = fetcher.fetch_multiple_symbols(
        symbols=SYMBOLS,
        period=PERIOD,
        limit=LIMIT
    )
    
    # Print final summary
    logger.info("\n" + "="*70)
    logger.info("Final Summary")
    logger.info("="*70)
    for symbol, counts in summary.items():
        if 'error' not in counts:
            logger.info(f"{symbol}:")
            logger.info(f"  Income statements: {counts.get('income', 0)}")
            logger.info(f"  Balance sheets: {counts.get('balance', 0)}")
            logger.info(f"  Cash flow statements: {counts.get('cashflow', 0)}")
        else:
            logger.error(f"{symbol}: Error - {counts.get('error')}")
    
    logger.info("\n" + "="*70)
    logger.info("Data stored at:")
    for symbol in SYMBOLS:
        symbol_path = EXTERNAL_DRIVE_PATH / symbol.upper()
        logger.info(f"  {symbol}: {symbol_path}")
    logger.info("="*70)
    
    logger.info("\nNote: As-reported endpoints typically have data from ~2010+")
    logger.info("(when XBRL filing became mandatory). For earlier data,")
    logger.info("you may need to use regular endpoints or manual data entry.")

if __name__ == "__main__":
    main()
