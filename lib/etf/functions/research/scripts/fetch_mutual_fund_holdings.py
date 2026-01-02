"""
Fetch Historical Mutual Fund Holdings for Russell 1000 Funds
Mutual funds may have longer histories and better historical data than ETFs.
Also explores SEC EDGAR filings (N-CSR, N-Q) for historical holdings.
"""

import sys
from pathlib import Path
import os
import logging
from datetime import datetime
import pandas as pd
import json
import requests

# Add project root to path
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from lib.etf.functions.research.core.backtesting import FMPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv('FMP_API_KEY')
if not API_KEY:
    raise ValueError("FMP_API_KEY environment variable is required. Set it in your .env file or export it.")
OUTPUT_DIR = Path('./data/research/mutual_fund_holdings')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Russell 1000 Mutual Fund Tickers
RUSSELL_1000_FUNDS = {
    'FRUSX': 'Fidelity Russell 1000 Index Fund',
    'BRGNX': 'BlackRock Russell 1000 Index Fund',
    'RUFBX': 'Russell 1000 Index Fund',
    'RUFIX': 'Russell 1000 Index Fund',
}


def test_mutual_fund_symbol(fmp_client: FMPClient, symbol: str) -> dict:
    """
    Test if a mutual fund symbol is recognized and has data.
    
    Returns:
        Dictionary with test results
    """
    result = {
        'symbol': symbol,
        'profile_found': False,
        'holdings_found': False,
        'holdings_count': 0,
        'error': None
    }
    
    try:
        # Test profile
        endpoint = "stable/profile"
        params = {'symbol': symbol}
        profile = fmp_client._get(endpoint, params)
        
        if isinstance(profile, list) and profile:
            result['profile_found'] = True
            result['profile_data'] = profile[0]
        
        # Test holdings (try ETF endpoint - sometimes works for mutual funds)
        endpoint = "stable/etf/holdings"
        params = {'symbol': symbol}
        holdings = fmp_client._get(endpoint, params)
        
        if isinstance(holdings, list) and len(holdings) > 0:
            result['holdings_found'] = True
            result['holdings_count'] = len(holdings)
            result['sample_holdings'] = holdings[:5]
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def fetch_mutual_fund_holdings(fmp_client: FMPClient, symbol: str, date: str = None) -> list:
    """
    Fetch mutual fund holdings.
    
    Args:
        fmp_client: FMPClient instance
        symbol: Mutual fund symbol
        date: Optional date string (YYYY-MM-DD)
        
    Returns:
        List of holding dictionaries
    """
    try:
        # Try ETF holdings endpoint (sometimes works for mutual funds)
        endpoint = "stable/etf/holdings"
        params = {'symbol': symbol}
        if date:
            params['date'] = date
        
        holdings = fmp_client._get(endpoint, params)
        
        if isinstance(holdings, list):
            logger.info(f"✓ Retrieved {len(holdings)} holdings for {symbol}")
            return holdings
        else:
            logger.warning(f"No holdings found for {symbol}")
            return []
    except Exception as e:
        logger.error(f"Error fetching holdings for {symbol}: {e}")
        return []


def search_sec_edgar(fund_name: str, cik: str = None):
    """
    Search SEC EDGAR for mutual fund filings.
    Mutual funds file N-CSR (annual/semi-annual reports) and N-Q (quarterly holdings).
    
    Args:
        fund_name: Name of the fund
        cik: Optional CIK number
        
    Returns:
        Information about available filings
    """
    logger.info(f"Searching SEC EDGAR for {fund_name}...")
    
    # SEC EDGAR search URL
    # Note: This is a placeholder - actual implementation would need to:
    # 1. Search for fund CIK
    # 2. Query filing history
    # 3. Download N-Q and N-CSR filings
    # 4. Parse holdings from filings
    
    logger.info("SEC EDGAR integration not yet implemented")
    logger.info("Mutual funds file N-Q (quarterly) and N-CSR (annual) reports with holdings")
    logger.info("These can be accessed via SEC EDGAR API or web scraping")
    
    return {
        'status': 'not_implemented',
        'note': 'SEC EDGAR integration requires additional development'
    }


def main():
    """Main function to test and fetch mutual fund holdings."""
    
    logger.info("="*70)
    logger.info("Russell 1000 Mutual Fund Holdings Test")
    logger.info("="*70)
    
    fmp = FMPClient(api_key=API_KEY)
    
    # Test all known Russell 1000 mutual funds
    results = []
    for symbol, name in RUSSELL_1000_FUNDS.items():
        logger.info(f"\nTesting {symbol} - {name}...")
        result = test_mutual_fund_symbol(fmp, symbol)
        results.append(result)
        
        if result['holdings_found']:
            logger.info(f"  ✓ Found {result['holdings_count']} holdings")
            
            # Try to fetch with a historical date
            logger.info(f"  Testing historical date (2000-12-31)...")
            historical = fetch_mutual_fund_holdings(fmp, symbol, date='2000-12-31')
            if historical:
                logger.info(f"  ✓ Historical holdings available: {len(historical)} holdings")
            else:
                logger.info(f"  ✗ No historical holdings")
        else:
            logger.info(f"  ✗ No holdings found")
    
    # Save results
    results_df = pd.DataFrame([
        {
            'symbol': r['symbol'],
            'profile_found': r['profile_found'],
            'holdings_found': r['holdings_found'],
            'holdings_count': r['holdings_count'],
            'error': r.get('error', '')
        }
        for r in results
    ])
    
    results_file = OUTPUT_DIR / 'mutual_fund_test_results.csv'
    results_df.to_csv(results_file, index=False)
    logger.info(f"\n✓ Results saved to {results_file}")
    
    # Print summary
    logger.info("\n" + "="*70)
    logger.info("Summary")
    logger.info("="*70)
    print(results_df.to_string(index=False))
    
    # Check for SEC EDGAR option
    logger.info("\n" + "="*70)
    logger.info("SEC EDGAR Alternative")
    logger.info("="*70)
    logger.info("Mutual funds are required to file holdings with SEC:")
    logger.info("  - N-Q: Quarterly holdings reports")
    logger.info("  - N-CSR: Annual/semi-annual reports with holdings")
    logger.info("  - Available via SEC EDGAR: https://www.sec.gov/edgar/searchedgar/companysearch.html")
    logger.info("\nTo access historical holdings:")
    logger.info("  1. Find fund CIK number")
    logger.info("  2. Search for N-Q and N-CSR filings")
    logger.info("  3. Download and parse holdings from XML/HTML filings")
    logger.info("  4. This provides true historical snapshots")


if __name__ == "__main__":
    main()

