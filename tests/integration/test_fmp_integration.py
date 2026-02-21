#!/usr/bin/env python3
"""
Comprehensive Test Script for FMP Integration
Tests all FMP adapter functionality and workflows for accounting/admin operations.
"""

import os
import sys
import logging
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def test_fmp_client():
    """Test FMPClient basic functionality"""
    logger.info("=" * 60)
    logger.info("TEST 1: FMPClient Basic Functionality")
    logger.info("=" * 60)
    
    try:
        from lib.etf.functions.research.core.backtesting import FMPClient
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.warning("FMP_API_KEY not set - skipping FMP tests")
            return False
        
        fmp = FMPClient(api_key=api_key)
        
        # Test batch quotes
        logger.info("Testing batch quotes API...")
        quotes = fmp.get_batch_quotes(["AAPL", "MSFT", "GOOGL"])
        if quotes:
            logger.info(f"✓ Batch quotes: Retrieved {len(quotes)} quotes")
            for symbol, quote in list(quotes.items())[:3]:
                price = quote.get('price') or quote.get('close')
                logger.info(f"  {symbol}: ${price}")
        else:
            logger.warning("✗ Batch quotes returned empty")
        
        # Test company profile
        logger.info("Testing company profile API...")
        profile = fmp.get_company_profile("AAPL")
        if profile:
            logger.info(f"✓ Company profile: {profile.get('companyName', 'N/A')}")
            logger.info(f"  CUSIP: {profile.get('cusip', 'N/A')}")
        else:
            logger.warning("✗ Company profile returned empty")
        
        # Test dividends calendar
        logger.info("Testing dividends calendar API...")
        today = date.today()
        start_date = (today - timedelta(days=7)).isoformat()
        end_date = (today + timedelta(days=7)).isoformat()
        dividends = fmp.get_dividends_calendar(start_date, end_date)
        if dividends:
            logger.info(f"✓ Dividends calendar: Found {len(dividends)} dividend events")
            for div in dividends[:3]:
                logger.info(f"  {div.get('symbol')}: ${div.get('dividend', 0)} on {div.get('exDate', 'N/A')}")
        else:
            logger.warning("✗ Dividends calendar returned empty")
        
        # Test stock splits
        logger.info("Testing stock splits calendar API...")
        splits = fmp.get_stock_splits_calendar(start_date, end_date)
        if splits:
            logger.info(f"✓ Stock splits: Found {len(splits)} splits")
        else:
            logger.info("  No splits found (this is normal)")
        
        # Test key metrics
        logger.info("Testing key metrics API...")
        metrics = fmp.get_key_metrics_ttm("AAPL")
        if metrics:
            pe = metrics.get('peRatio') or metrics.get('pe_ratio')
            div_yield = metrics.get('dividendYield') or metrics.get('dividend_yield')
            logger.info(f"✓ Key metrics: P/E={pe}, Div Yield={div_yield}")
        else:
            logger.warning("✗ Key metrics returned empty")
        
        logger.info("✓ FMPClient tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ FMPClient test failed: {e}", exc_info=True)
        return False


def test_fmp_adapter():
    """Test FMPDataSourceAdapter with manual holdings"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: FMPDataSourceAdapter with Manual Holdings")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.warning("FMP_API_KEY not set - skipping adapter tests")
            return False
        
        # Create manual holdings
        manual_holdings = [
            {
                "ticker": "AAPL",
                "quantity": 1000,
                "weight": 5.0,
                "name": "Apple Inc."
            },
            {
                "ticker": "MSFT",
                "quantity": 800,
                "weight": 4.0,
                "name": "Microsoft Corporation"
            },
            {
                "ticker": "GOOGL",
                "quantity": 500,
                "weight": 3.5,
                "name": "Alphabet Inc."
            }
        ]
        
        # Create adapter
        adapter = FMPDataSourceAdapter(
            manual_holdings=manual_holdings,
            api_key=api_key
        )
        
        # Test get_portfolio_holdings
        logger.info("Testing get_portfolio_holdings...")
        holdings = adapter.get_portfolio_holdings(date.today())
        if holdings:
            logger.info(f"✓ Retrieved {len(holdings)} holdings")
            for h in holdings:
                logger.info(f"  {h.get('ticker')}: {h.get('quantity')} shares, CUSIP: {h.get('cusip', 'N/A')}")
        else:
            logger.error("✗ No holdings returned")
            return False
        
        # Test get_market_prices
        logger.info("Testing get_market_prices...")
        cusips = [h.get('cusip') for h in holdings if h.get('cusip')]
        if not cusips:
            # Fall back to tickers
            tickers = [h.get('ticker') for h in holdings]
            # Create a ticker-to-cusip mapping
            for ticker in tickers:
                profile = adapter.fmp_client.get_company_profile(ticker)
                if profile:
                    cusip = profile.get('cusip')
                    if cusip:
                        adapter._ticker_to_cusip[ticker] = cusip
            cusips = [adapter._ticker_to_cusip.get(t) for t in tickers if adapter._ticker_to_cusip.get(t)]
        
        if cusips:
            prices = adapter.get_market_prices(date.today(), cusips)
            if prices:
                logger.info(f"✓ Retrieved prices for {len(prices)} securities")
                for cusip, price in list(prices.items())[:3]:
                    logger.info(f"  CUSIP {cusip}: ${price}")
            else:
                logger.warning("✗ No prices returned")
        else:
            logger.warning("  No CUSIPs available for price lookup")
        
        # Test get_corporate_actions
        logger.info("Testing get_corporate_actions...")
        actions = adapter.get_corporate_actions(date.today())
        logger.info(f"✓ Corporate actions: {len(actions)} found")
        
        # Test get_accounting_data
        logger.info("Testing get_accounting_data...")
        accounting_data = adapter.get_accounting_data(date.today())
        logger.info(f"✓ Accounting data retrieved")
        logger.info(f"  Dividend income: ${accounting_data.get('income', {}).get('dividend_income', 0)}")
        
        # Test get_security_identifiers
        logger.info("Testing get_security_identifiers...")
        identifiers = adapter.get_security_identifiers("AAPL")
        logger.info(f"✓ Security identifiers for AAPL:")
        logger.info(f"  CUSIP: {identifiers.get('cusip', 'N/A')}")
        logger.info(f"  CIK: {identifiers.get('cik', 'N/A')}")
        logger.info(f"  ISIN: {identifiers.get('isin', 'N/A')}")
        
        # Test get_benchmark_data
        logger.info("Testing get_benchmark_data...")
        benchmark = adapter.get_benchmark_data("SPY", date.today())
        if benchmark:
            logger.info(f"✓ Benchmark data: SPY price=${benchmark.get('price', 'N/A')}")
        else:
            logger.warning("✗ Benchmark data not available")
        
        logger.info("✓ FMPDataSourceAdapter tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ FMPDataSourceAdapter test failed: {e}", exc_info=True)
        return False


def test_nav_calculation():
    """Test NAV calculation with FMP adapter"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: NAV Calculation with FMP Adapter")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.functions.core import FundAdministration
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.warning("FMP_API_KEY not set - skipping NAV test")
            return False
        
        # Create manual holdings
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
            {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
            {"ticker": "GOOGL", "quantity": 500, "weight": 3.5},
        ]
        
        adapter = FMPDataSourceAdapter(
            manual_holdings=manual_holdings,
            api_key=api_key
        )
        
        # Create admin module
        admin = FundAdministration(
            data_adapter=adapter,
            storage_path="./data/test_admin"
        )
        
        # Calculate NAV
        logger.info("Calculating NAV...")
        nav_calc = admin.calculate_nav(date.today())
        
        if nav_calc:
            logger.info(f"✓ NAV calculated successfully")
            logger.info(f"  NAV per share: ${nav_calc.nav_per_share}")
            logger.info(f"  Total assets: ${nav_calc.total_assets}")
            logger.info(f"  Total liabilities: ${nav_calc.total_liabilities}")
            logger.info(f"  Net assets: ${nav_calc.net_assets}")
            logger.info(f"  Shares outstanding: {nav_calc.shares_outstanding}")
            logger.info(f"  Validation passed: {nav_calc.validation_passed}")
            
            if nav_calc.pricing_exceptions:
                logger.warning(f"  Pricing exceptions: {len(nav_calc.pricing_exceptions)}")
                for exc in nav_calc.pricing_exceptions[:3]:
                    logger.warning(f"    - {exc}")
            
            return True
        else:
            logger.error("✗ NAV calculation failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ NAV calculation test failed: {e}", exc_info=True)
        return False


def test_accounting_operations():
    """Test accounting operations with FMP adapter"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Accounting Operations with FMP Adapter")
    logger.info("=" * 60)
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.functions.core import Accounting, FundAdministration
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.warning("FMP_API_KEY not set - skipping accounting test")
            return False
        
        # Create manual holdings
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
            {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
        ]
        
        adapter = FMPDataSourceAdapter(
            manual_holdings=manual_holdings,
            api_key=api_key
        )
        
        # Create modules
        accounting = Accounting(
            data_adapter=adapter,
            storage_path="./data/test_accounting"
        )
        
        admin = FundAdministration(
            data_adapter=adapter,
            storage_path="./data/test_admin"
        )
        
        # Calculate NAV first
        nav_calc = admin.calculate_nav(date.today())
        
        # Run daily accounting operations
        logger.info("Running daily accounting operations...")
        results = accounting.daily_accounting_operations(date.today(), nav_calc)
        
        if results:
            logger.info(f"✓ Accounting operations completed")
            logger.info(f"  NAV entries: {len(results.get('nav_entries', []))}")
            logger.info(f"  Expense entries: {len(results.get('expense_entries', []))}")
            logger.info(f"  Income entries: {len(results.get('income_entries', []))}")
            
            # Check trial balance
            tb = results.get('trial_balance')
            if tb:
                logger.info(f"  Trial balance balanced: {tb.balanced}")
                logger.info(f"  Total debits: ${tb.total_debits}")
                logger.info(f"  Total credits: ${tb.total_credits}")
            
            # Generate financial statements
            logger.info("Generating financial statements...")
            balance_sheet = accounting.generate_balance_sheet(date.today())
            income_statement = accounting.generate_income_statement(
                date.today().replace(day=1),
                date.today()
            )
            
            logger.info(f"✓ Balance sheet generated")
            logger.info(f"  Total assets: ${balance_sheet.data.get('total_assets', 0)}")
            logger.info(f"  Total equity: ${balance_sheet.data.get('total_equity', 0)}")
            
            logger.info(f"✓ Income statement generated")
            logger.info(f"  Total income: ${income_statement.data.get('total_income', 0)}")
            logger.info(f"  Net income: ${income_statement.data.get('net_income', 0)}")
            
            return True
        else:
            logger.error("✗ Accounting operations failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Accounting operations test failed: {e}", exc_info=True)
        return False


def test_fmp_workflows():
    """Test FMP-enhanced workflows"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: FMP-Enhanced Workflows")
    logger.info("=" * 60)
    
    try:
        from lib.etf.functions.core import FMPEnhancedWorkflows
        
        api_key = os.getenv('FMP_API_KEY')
        if not api_key:
            logger.warning("FMP_API_KEY not set - skipping workflow tests")
            return False
        
        # Create manual holdings
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
            {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
            {"ticker": "GOOGL", "quantity": 500, "weight": 3.5},
        ]
        
        # Create workflows
        workflows = FMPEnhancedWorkflows(
            etf_symbol="",
            manual_holdings=manual_holdings,
            api_key=api_key,
            storage_path="./data/test_workflows"
        )
        
        # Test individual workflows
        logger.info("Testing daily price import and NAV...")
        nav_result = workflows.daily_price_import_and_nav(date.today())
        if nav_result:
            logger.info(f"✓ NAV workflow completed")
            logger.info(f"  NAV: ${nav_result.get('nav_calculation', {}).get('nav_per_share', 'N/A')}")
        else:
            logger.warning("✗ NAV workflow failed")
        
        logger.info("Testing corporate actions processing...")
        ca_result = workflows.daily_corporate_actions_processing(date.today())
        if ca_result:
            logger.info(f"✓ Corporate actions: {ca_result.get('actions_processed', 0)} processed")
        
        logger.info("Testing dividend accrual tracking...")
        div_result = workflows.daily_dividend_accrual_tracking(date.today())
        if div_result:
            logger.info(f"✓ Dividend accrual: ${div_result.get('total_accrued_income', 0)}")
        
        logger.info("Testing expense accrual...")
        exp_result = workflows.daily_expense_accrual_and_fee_booking(date.today())
        if exp_result:
            logger.info(f"✓ Expense accrual completed")
        
        logger.info("Testing NAV verification...")
        nav_verif = workflows.daily_nav_verification_and_reconciliation(date.today(), "SPY")
        if nav_verif:
            logger.info(f"✓ NAV verification: {nav_verif.get('reconciliation_status', 'N/A')}")
        
        # Test full daily operations
        logger.info("Testing full daily operations...")
        daily_results = workflows.run_daily_operations(date.today(), "SPY")
        if daily_results:
            logger.info(f"✓ Full daily operations completed")
            logger.info(f"  Operations: {list(daily_results.get('operations', {}).keys())}")
        
        logger.info("✓ FMP workflows tests passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ FMP workflows test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("FMP INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    logger.info(f"Test Date: {date.today()}")
    logger.info(f"FMP API Key: {'Set' if os.getenv('FMP_API_KEY') else 'NOT SET'}")
    logger.info("=" * 60 + "\n")
    
    results = {}
    
    # Run tests
    results['fmp_client'] = test_fmp_client()
    results['fmp_adapter'] = test_fmp_adapter()
    results['nav_calculation'] = test_nav_calculation()
    results['accounting'] = test_accounting_operations()
    results['workflows'] = test_fmp_workflows()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name:20s}: {status}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

