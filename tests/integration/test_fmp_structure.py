#!/usr/bin/env python3
"""
Structure Test for FMP Integration
Tests the structure and imports without requiring API calls.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        logger.info("✓ FMPDataSourceAdapter imported")
    except Exception as e:
        logger.error(f"✗ Failed to import FMPDataSourceAdapter: {e}")
        return False
    
    try:
        from lib.etf.functions.core import FMPEnhancedWorkflows
        logger.info("✓ FMPEnhancedWorkflows imported")
    except Exception as e:
        logger.error(f"✗ Failed to import FMPEnhancedWorkflows: {e}")
        return False
    
    try:
        from lib.etf.functions.research.core.backtesting import FMPClient
        logger.info("✓ FMPClient imported")
    except Exception as e:
        logger.error(f"✗ Failed to import FMPClient: {e}")
        return False
    
    try:
        from lib.etf.functions.core import Accounting, FundAdministration
        logger.info("✓ Accounting and FundAdministration imported")
    except Exception as e:
        logger.error(f"✗ Failed to import core modules: {e}")
        return False
    
    return True


def test_adapter_initialization():
    """Test adapter can be initialized"""
    logger.info("\nTesting adapter initialization...")
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        
        # Test with manual holdings
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
            {"ticker": "MSFT", "quantity": 800, "weight": 4.0},
        ]
        
        adapter = FMPDataSourceAdapter(
            manual_holdings=manual_holdings
        )
        logger.info("✓ FMPDataSourceAdapter initialized with manual holdings")
        
        # Test that holdings are accessible
        from datetime import date
        holdings = adapter.get_portfolio_holdings(date.today())  # Will use manual holdings
        if holdings:
            logger.info(f"✓ Retrieved {len(holdings)} manual holdings")
        else:
            logger.warning("⚠ Manual holdings not returned (may need date)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Adapter initialization failed: {e}", exc_info=True)
        return False


def test_workflow_initialization():
    """Test workflows can be initialized"""
    logger.info("\nTesting workflow initialization...")
    
    try:
        from lib.etf.functions.core import FMPEnhancedWorkflows
        
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
        ]
        
        workflows = FMPEnhancedWorkflows(
            etf_symbol="",
            manual_holdings=manual_holdings,
            storage_path="./data/test"
        )
        logger.info("✓ FMPEnhancedWorkflows initialized")
        
        # Check that adapter was created
        if hasattr(workflows, 'fmp_adapter'):
            logger.info("✓ FMP adapter created in workflows")
        else:
            logger.warning("⚠ FMP adapter not found in workflows")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflow initialization failed: {e}", exc_info=True)
        return False


def test_integration_with_accounting():
    """Test integration with accounting module"""
    logger.info("\nTesting integration with accounting module...")
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.functions.core import Accounting
        
        manual_holdings = [
            {"ticker": "AAPL", "quantity": 1000, "weight": 5.0},
        ]
        
        adapter = FMPDataSourceAdapter(manual_holdings=manual_holdings)
        accounting = Accounting(adapter, storage_path="./data/test_accounting")
        
        logger.info("✓ Accounting module initialized with FMP adapter")
        
        # Check that accounting has the adapter
        if hasattr(accounting, 'data_adapter'):
            logger.info("✓ Data adapter attached to accounting")
        else:
            logger.warning("⚠ Data adapter not found in accounting")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Integration test failed: {e}", exc_info=True)
        return False


def test_fmp_client_methods():
    """Test that FMPClient has all required methods"""
    logger.info("\nTesting FMPClient methods...")
    
    try:
        from lib.etf.functions.research.core.backtesting import FMPClient
        
        # Check for required methods
        required_methods = [
            'get_batch_quotes',
            'get_historical_price_eod',
            'get_dividends_calendar',
            'get_dividends_company',
            'get_stock_splits_calendar',
            'get_stock_split_details',
            'get_symbol_changes',
            'get_cusip_lookup',
            'get_cik_lookup',
            'get_index_market_data',
            'get_key_metrics_ttm',
            'get_etf_sector_weightings',
            'get_company_profile',
            'get_etf_info',
        ]
        
        fmp = FMPClient()  # Will use env var if available
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(fmp, method):
                missing_methods.append(method)
        
        if missing_methods:
            logger.error(f"✗ Missing methods: {missing_methods}")
            return False
        
        logger.info(f"✓ All {len(required_methods)} required methods present")
        return True
        
    except Exception as e:
        logger.error(f"✗ FMPClient method test failed: {e}", exc_info=True)
        return False


def test_adapter_methods():
    """Test that FMPDataSourceAdapter implements all required methods"""
    logger.info("\nTesting FMPDataSourceAdapter methods...")
    
    try:
        from lib.etf.adapters import FMPDataSourceAdapter
        from lib.etf.shared import DataSourceAdapter
        
        # Get all abstract methods from DataSourceAdapter
        adapter = FMPDataSourceAdapter(manual_holdings=[])
        
        required_methods = [
            'get_nscc_files',
            'get_dtc_position_file',
            'get_custodian_statements',
            'get_portfolio_holdings',
            'get_market_prices',
            'get_corporate_actions',
            'get_expense_data',
            'get_ap_orders',
            'get_accounting_data',
            'get_distribution_data',
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(adapter, method):
                missing_methods.append(method)
        
        if missing_methods:
            logger.error(f"✗ Missing methods: {missing_methods}")
            return False
        
        logger.info(f"✓ All {len(required_methods)} required methods present")
        
        # Test additional helper methods
        helper_methods = [
            'get_benchmark_data',
            'get_security_identifiers',
            'get_portfolio_metrics',
        ]
        
        for method in helper_methods:
            if not hasattr(adapter, method):
                logger.warning(f"⚠ Helper method missing: {method}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Adapter method test failed: {e}", exc_info=True)
        return False


def main():
    """Run all structure tests"""
    logger.info("=" * 60)
    logger.info("FMP INTEGRATION STRUCTURE TEST")
    logger.info("=" * 60)
    
    results = {}
    results['imports'] = test_imports()
    results['adapter_init'] = test_adapter_initialization()
    results['workflow_init'] = test_workflow_initialization()
    results['accounting_integration'] = test_integration_with_accounting()
    results['fmp_client_methods'] = test_fmp_client_methods()
    results['adapter_methods'] = test_adapter_methods()
    
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name:25s}: {status}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("🎉 All structure tests passed!")
        logger.info("\nNote: To test with real API calls, set FMP_API_KEY environment variable")
        logger.info("and run: python test_fmp_integration.py")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

