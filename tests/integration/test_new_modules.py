"""
Integration tests for newly implemented modules
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta
from decimal import Decimal

# Add parent directory to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from lib.etf.functions import (
    TradingExecution,
    Rule6c11Compliance,
    TaxEfficiencyOptimizer,
    LiquidityRiskManager,
    IntradayNAVMonitor,
    FairValuationManager,
    ShadowAccounting,
    OrderManagement,
    Distributor
)
from lib.etf.adapters import FileBasedDataSourceAdapter


class MockDataSourceAdapter(FileBasedDataSourceAdapter):
    """Mock adapter with test data"""
    
    def __init__(self):
        super().__init__(data_path="./data")
        # Add mock data methods if needed
    
    def get_market_prices(self, date, cusips):
        """Return mock prices"""
        return {cusip: Decimal('100.00') for cusip in cusips}
    
    def get_portfolio_holdings(self, date):
        """Return mock holdings"""
        return [
            {"cusip": "037833100", "ticker": "AAPL", "quantity": "1000"},
            {"cusip": "594918104", "ticker": "MSFT", "quantity": "500"},
            {"cusip": "30303M102", "ticker": "GOOGL", "quantity": "300"}
        ]
    
    def get_custodian_statements(self, date):
        """Return mock custodian data"""
        return {
            "total_shares": Decimal('1000000'),
            "shares_outstanding": Decimal('1000000'),
            "cash_balance": Decimal('50000'),
            "portfolio_cash": Decimal('50000'),
            "total_liabilities": Decimal('10000'),
            "holdings": [
                {"cusip": "037833100", "quantity": "1000"},
                {"cusip": "594918104", "quantity": "500"},
                {"cusip": "30303M102", "quantity": "300"}
            ]
        }


def test_1_trading_execution():
    """Test trading execution module"""
    print("\n=== Test 1: Trading Execution ===")
    adapter = MockDataSourceAdapter()
    trading = TradingExecution(adapter)
    
    # Create trade order
    trade = trading.create_trade_order(
        cusip="037833100",
        ticker="AAPL",
        order_type="buy",
        quantity=Decimal('1000'),
        limit_price=Decimal('150.00')
    )
    print(f"✓ Created trade order: {trade.trade_id}")
    
    # Route trade
    execution = trading.route_trade(trade)
    print(f"✓ Trade executed: {execution.status}, Price: {execution.execution_price}")
    
    # Process daily trades
    results = trading.process_daily_trades(date.today())
    print(f"✓ Daily trades processed: {results['trades_processed']} trades")
    
    return True


def test_2_rule_6c11_compliance():
    """Test Rule 6c-11 compliance module"""
    print("\n=== Test 2: Rule 6c-11 Compliance ===")
    compliance = Rule6c11Compliance()
    
    # Standard basket
    standard_basket = [
        {"cusip": "037833100", "quantity": "100", "price": "150.00"},
        {"cusip": "594918104", "quantity": "50", "price": "300.00"}
    ]
    
    # Custom basket (valid)
    custom_basket = [
        {"cusip": "037833100", "quantity": "95", "price": "150.00"},
        {"cusip": "594918104", "quantity": "48", "price": "300.00"}
    ]
    
    validation = compliance.validate_custom_basket(
        standard_basket=standard_basket,
        custom_basket=custom_basket,
        pcf_total_value=Decimal('30000')
    )
    print(f"✓ Validation passed: {validation.passed}")
    print(f"  Errors: {len(validation.errors)}, Warnings: {len(validation.warnings)}")
    
    # Generate disclosure
    disclosure = compliance.generate_custom_basket_disclosure(
        custom_basket=custom_basket,
        standard_basket=standard_basket,
        validation=validation
    )
    print(f"✓ Disclosure generated: {disclosure['disclosure_date']}")
    
    return True


def test_3_tax_optimization():
    """Test tax efficiency optimizer"""
    print("\n=== Test 3: Tax Efficiency Optimization ===")
    adapter = MockDataSourceAdapter()
    optimizer = TaxEfficiencyOptimizer(adapter)
    
    # Test redemption basket optimization
    pcf = {
        "securities": [
            {"cusip": "037833100", "quantity": "100"},
            {"cusip": "594918104", "quantity": "50"}
        ]
    }
    
    tax_lots = [
        {"cusip": "037833100", "quantity": Decimal('100'), "cost_basis": Decimal('140.00'), "purchase_date": date(2023, 1, 1)},
        {"cusip": "037833100", "quantity": Decimal('50'), "cost_basis": Decimal('160.00'), "purchase_date": date(2024, 1, 1)},
        {"cusip": "594918104", "quantity": Decimal('50'), "cost_basis": Decimal('280.00'), "purchase_date": date(2023, 6, 1)}
    ]
    
    optimized = optimizer.optimize_redemption_basket_for_tax(
        pcf=pcf,
        creation_units=1,
        tax_lots=tax_lots
    )
    print(f"✓ Optimized redemption basket: {len(optimized)} securities")
    
    # Test wash sale check
    recent_purchases = [
        {"purchase_date": date.today() - timedelta(days=15), "quantity": Decimal('100')}
    ]
    wash_sale = optimizer.check_wash_sale_rule(
        sale_date=date.today(),
        cusip="037833100",
        recent_purchases=recent_purchases
    )
    print(f"✓ Wash sale check: {wash_sale}")
    
    return True


def test_4_liquidity_risk():
    """Test liquidity risk manager"""
    print("\n=== Test 4: Liquidity Risk Management ===")
    adapter = MockDataSourceAdapter()
    risk_manager = LiquidityRiskManager(adapter)
    
    assessment = risk_manager.assess_daily_liquidity_risk(date.today())
    print(f"✓ Risk assessment: {assessment.overall_risk_level}")
    print(f"  Risk score: {assessment.risk_score}")
    print(f"  Compliance: {assessment.compliance_status}")
    print(f"  Risk factors: {len(assessment.risk_factors)}")
    
    return True


def test_5_intraday_nav():
    """Test intraday NAV monitor"""
    print("\n=== Test 5: Intraday NAV Monitoring ===")
    adapter = MockDataSourceAdapter()
    monitor = IntradayNAVMonitor(adapter)
    
    holdings = adapter.get_portfolio_holdings(date.today())
    prices = adapter.get_market_prices(date.today(), [h.get('cusip') for h in holdings])
    
    snapshot = monitor.calculate_intraday_nav(
        nav_date=date.today(),
        timestamp=datetime.now(),
        holdings=holdings,
        market_prices=prices
    )
    print(f"✓ Intraday NAV: {snapshot.intraday_nav_per_share}")
    print(f"  Spread: {snapshot.spread_percentage:.4f}%")
    print(f"  Premium/Discount: {snapshot.premium_discount_percentage:.4f}%")
    print(f"  Status: {snapshot.status}")
    
    # Check alerts
    alerts = monitor.check_spread_alerts(snapshot)
    print(f"✓ Alerts: {len(alerts)}")
    
    return True


def test_6_fair_valuation():
    """Test fair valuation manager"""
    print("\n=== Test 6: Fair Valuation Manager ===")
    adapter = MockDataSourceAdapter()
    valuation_manager = FairValuationManager(adapter)
    
    report = valuation_manager.apply_fair_valuation_policies(date.today())
    print(f"✓ Fair valuation report generated")
    print(f"  Total securities: {report['total_securities']}")
    print(f"  Fair valued: {report['fair_valued_securities']}")
    print(f"  Market priced: {report['market_priced_securities']}")
    print(f"  Exceptions: {len(report['exceptions'])}")
    
    return True


def test_7_shadow_accounting():
    """Test shadow accounting system"""
    print("\n=== Test 7: Shadow Accounting ===")
    adapter = MockDataSourceAdapter()
    shadow = ShadowAccounting(adapter)
    
    result = shadow.calculate_shadow_nav(date.today())
    print(f"✓ Shadow NAV: {result.shadow_nav_per_share}")
    print(f"  Official NAV: {result.official_nav_per_share}")
    print(f"  Difference: {result.difference_percentage:.4f}%")
    print(f"  Status: {result.status}")
    print(f"  Validation: {result.validation_passed}")
    
    reconciliation = shadow.reconcile_shadow_vs_official(date.today())
    print(f"✓ Reconciliation completed: {reconciliation['comparison']['status']}")
    
    return True


def test_8_order_management_with_rule_6c11():
    """Test OrderManagement with integrated Rule 6c-11"""
    print("\n=== Test 8: Order Management with Rule 6c-11 ===")
    adapter = MockDataSourceAdapter()
    om = OrderManagement(adapter)
    
    # Generate PCF
    pcf = om.generate_pcf(date.today())
    print(f"✓ PCF generated: {len(pcf.securities)} securities")
    
    # Build custom basket (should trigger Rule 6c-11 validation)
    custom_securities = [
        {"cusip": "037833100", "quantity": "95", "description": "APPLE INC"},
        {"cusip": "594918104", "quantity": "48", "description": "MICROSOFT CORP"}
    ]
    
    basket = om.build_custom_creation_basket(
        pcf=pcf,
        creation_units=1,
        custom_securities=custom_securities
    )
    print(f"✓ Custom basket built: {basket.basket_type}")
    print(f"  Validated: {basket.validated}")
    print(f"  Errors: {len(basket.errors)}")
    
    return True


def test_9_distributor_with_exchange_coordination():
    """Test Distributor with exchange coordination"""
    print("\n=== Test 9: Distributor with Exchange Coordination ===")
    adapter = MockDataSourceAdapter()
    distributor = Distributor(adapter)
    
    nav_data = {
        "shares_outstanding": Decimal('1000000')
    }
    
    distribution = distributor.calculate_distribution(
        dist_date=date.today(),
        distribution_type="dividend",
        nav_data=nav_data,
        exchange_coordination=True
    )
    print(f"✓ Distribution calculated: {distribution.distribution_id}")
    print(f"  Amount per share: ${distribution.amount_per_share}")
    print(f"  Total amount: ${distribution.total_amount}")
    
    return True


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Testing New Modules")
    print("=" * 60)
    
    tests = [
        test_1_trading_execution,
        test_2_rule_6c11_compliance,
        test_3_tax_optimization,
        test_4_liquidity_risk,
        test_5_intraday_nav,
        test_6_fair_valuation,
        test_7_shadow_accounting,
        test_8_order_management_with_rule_6c11,
        test_9_distributor_with_exchange_coordination
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, True, None))
        except Exception as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            results.append((test.__name__, False, str(e)))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed
    
    for name, success, error in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

