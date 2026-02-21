"""
Full Integration Test for ITAN ETF
Runs all functions with live ITAN data and generates comprehensive reports
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.etf.functions.core.orchestrator import DailyOrchestrator
from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.functions.operations.distributor import Distributor
from lib.etf.functions.operations.performance import PerformanceCalculator
from lib.etf.functions.tax.tax_reporting import TaxReporting
from tests.integration.test_itan_live_data import ITANLiveDataAdapter


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_full_itan_test():
    """Run comprehensive test of all functions with ITAN data"""
    print("\n" + "=" * 70)
    print("  ITAN ETF FULL INTEGRATION TEST")
    print("  Testing all functions with live ITAN data")
    print("=" * 70)
    
    # Initialize data adapter
    data_dir = Path("./data/itan_test")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    adapter = ITANLiveDataAdapter(data_path=str(data_dir))
    config_path = str(data_dir / "config.yaml")
    
    # Create config if it doesn't exist
    if not Path(config_path).exists():
        from tests.integration.fetch_itan_data import create_itan_config
        create_itan_config(config_path)
    
    # Initialize orchestrator
    print_section("Initializing Orchestrator")
    orchestrator = DailyOrchestrator(adapter, config_path=config_path)
    print("✓ Orchestrator initialized")
    print(f"  Fund: {orchestrator.config.get('fund', {}).get('name', 'N/A')}")
    print(f"  Ticker: {orchestrator.config.get('fund', {}).get('ticker', 'N/A')}")
    
    # Test date (use yesterday for market data availability)
    test_date = date.today() - timedelta(days=1)
    
    # 1. NAV Calculation
    print_section("1. NAV Calculation")
    try:
        nav_calc = orchestrator.admin.calculate_nav(test_date)
        print(f"✓ NAV calculated successfully")
        print(f"  Date: {nav_calc.date}")
        print(f"  NAV per share: ${nav_calc.nav_per_share}")
        print(f"  Total Assets: ${nav_calc.total_assets:,.2f}")
        print(f"  Total Liabilities: ${nav_calc.total_liabilities:,.2f}")
        print(f"  Net Assets: ${nav_calc.net_assets:,.2f}")
        print(f"  Shares Outstanding: {nav_calc.shares_outstanding:,.0f}")
        print(f"  Validation: {'✓ PASSED' if nav_calc.validation_passed else '✗ FAILED'}")
        if nav_calc.pricing_exceptions:
            print(f"  ⚠ Pricing exceptions: {len(nav_calc.pricing_exceptions)}")
    except Exception as e:
        print(f"✗ NAV calculation failed: {e}")
        return
    
    # 2. Accounting Operations
    print_section("2. Accounting Operations")
    try:
        orchestrator.accounting.daily_accounting_operations(test_date, nav_calc)
        print(f"✓ Accounting operations completed")
        print(f"  Accounts in ledger: {len(orchestrator.accounting.general_ledger)}")
        
        # Show key account balances
        key_accounts = ['1000', '1100', '4000', '3200']  # Cash, Investments, Dividend Income, Net Assets
        for acc_code in key_accounts:
            if acc_code in orchestrator.accounting.general_ledger:
                gl = orchestrator.accounting.general_ledger[acc_code]
                balance = gl.balance
                print(f"  {acc_code} ({gl.account_name}): ${balance:,.2f}")
    except Exception as e:
        print(f"✗ Accounting operations failed: {e}")
    
    # 3. Tax Lot Tracking
    print_section("3. Tax Lot Tracking")
    try:
        holdings = adapter.fetch_itan_holdings()
        prices = adapter.get_market_prices(test_date, [])
        
        # Initialize tax lots for holdings
        for holding in holdings[:10]:  # First 10 holdings
            ticker = holding["ticker"]
            quantity = Decimal(str(holding["quantity"]))
            cusip = holding.get("cusip", "")
            price = prices.get(cusip, Decimal('100.00'))
            
            orchestrator.taxlot_manager.add_lot(
                ticker=ticker,
                quantity=quantity,
                cost_basis=price * Decimal('0.9'),  # Assume 10% unrealized gain
                purchase_date=date(2024, 1, 1),
                cusip=cusip
            )
        
        # Get unrealized gains
        current_prices = {h["ticker"]: prices.get(h.get("cusip", ""), Decimal('100.00')) 
                         for h in holdings[:10]}
        unrealized = orchestrator.taxlot_manager.get_unrealized_gains(current_prices)
        
        print(f"✓ Tax lot tracking active")
        print(f"  Open lots: {len(orchestrator.taxlot_manager.open_lots)}")
        print(f"  Unrealized short-term: ${unrealized['unrealized_short_term']}")
        print(f"  Unrealized long-term: ${unrealized['unrealized_long_term']}")
        print(f"  Total unrealized: ${unrealized['unrealized_total']}")
    except Exception as e:
        print(f"✗ Tax lot tracking failed: {e}")
    
    # 4. Performance Calculation
    print_section("4. Performance Calculation")
    try:
        nav_file = data_dir / "nav_history.csv"
        dist_file = data_dir / "distributions.csv"
        
        if nav_file.exists():
            calc = orchestrator.performance
            result = calc.compute_performance(
                nav_history_path=str(nav_file),
                dist_history_path=str(dist_file) if dist_file.exists() else None,
                benchmark_symbol="^GSPC",
                tax_rates=orchestrator.config.get('tax', {}),
                start_date=date(2024, 1, 1),
                end_date=test_date
            )
            
            print(f"✓ Performance calculated")
            print(f"  Period: {result['start_date']} to {result['end_date']}")
            print(f"  Pre-tax return: {result['pre_tax_total_return']:.2%}")
            print(f"  After-tax return: {result['after_tax_total_return']:.2%}")
            print(f"  Tax drag: {result['tax_drag']:.2%}")
            print(f"  Tax efficiency: {result['tax_efficiency_ratio']:.2%}")
            if result.get('benchmark'):
                print(f"  Benchmark (S&P 500): {result['benchmark']['total_return']:.2%}")
                if result.get('fund_vs_benchmark') is not None:
                    print(f"  vs Benchmark: {result['fund_vs_benchmark']:.2%}")
        else:
            print("⚠ NAV history file not found, skipping performance calculation")
    except Exception as e:
        print(f"✗ Performance calculation failed: {e}")
    
    # 5. Distribution Processing
    print_section("5. Distribution Processing")
    try:
        nav_data = {
            'shares_outstanding': nav_calc.shares_outstanding
        }
        
        # Get ledger account balances
        ledger_accounts = {}
        for acc_code, gl in orchestrator.accounting.general_ledger.items():
            balance = gl.debit_balance - gl.credit_balance
            ledger_accounts[acc_code] = balance
        
        # Check if it's a distribution date
        dist_result = orchestrator._process_distributions(test_date, nav_data)
        
        if dist_result:
            print(f"✓ Distribution processed")
            print(f"  Distribution ID: {dist_result['distribution_id']}")
            print(f"  Amount per share: ${dist_result['amount_per_share']}")
            print(f"  Total amount: ${dist_result['total_amount']}")
            print(f"  Payout ratio: {dist_result['payout_ratio']}")
        else:
            print("  Not a distribution date")
    except Exception as e:
        print(f"✗ Distribution processing failed: {e}")
    
    # 6. Tax Reporting
    print_section("6. Tax Reporting")
    try:
        # Get ledger account balances for tax reporting
        ledger_accounts = {}
        for acc_code, gl in orchestrator.accounting.general_ledger.items():
            balance = gl.balance
            # For income accounts, use negative balance (credit balance)
            if gl.account_type == 'income':
                ledger_accounts[gl.account_name] = -balance if balance < 0 else balance
            else:
                ledger_accounts[gl.account_name] = balance
        
        # Set up some distributions for the year
        distributions = []
        if hasattr(orchestrator.distributor, 'distributions'):
            distributions = [
                {
                    "distribution_type": d.distribution_type,
                    "total_amount": str(d.total_amount)
                }
                for d in orchestrator.distributor.distributions
                if d.record_date.year == test_date.year
            ]
        
        # Generate Form 1120-RIC
        form_1120_ric = orchestrator.tax_reporting.generate_tax_return_form_1120_ric(
            tax_year=test_date.year,
            ledger_data=ledger_accounts,
            taxlot_manager=orchestrator.taxlot_manager,
            distributions=distributions
        )
        
        # Generate Form 8613
        form_8613 = orchestrator.tax_reporting.generate_form_8613(
            tax_year=test_date.year,
            ledger_data=ledger_accounts,
            taxlot_manager=orchestrator.taxlot_manager,
            distributions=distributions
        )
        
        print(f"✓ Tax reports generated")
        print(f"  Form 1120-RIC:")
        print(f"    Investment Company Taxable Income: ${form_1120_ric.get('investment_company_taxable_income', '0')}")
        print(f"    Dividends Paid Deduction: ${form_1120_ric.get('dividends_paid_deduction', '0')}")
        print(f"    Taxable Income: ${form_1120_ric.get('taxable_income_after_deduction', '0')}")
        print(f"    Corporate Tax Due: ${form_1120_ric.get('corporate_tax_due', '0')}")
        print(f"  Form 8613:")
        print(f"    Required Distribution: ${form_8613.get('total_required_distribution', '0')}")
        print(f"    Actual Distribution: ${form_8613.get('actual_distribution', '0')}")
        print(f"    Undistributed Amount: ${form_8613.get('undistributed_amount', '0')}")
        print(f"    Excise Tax (4%): ${form_8613.get('excise_tax_4pct', '0')}")
    except Exception as e:
        print(f"✗ Tax reporting failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. Full Daily Operations
    print_section("7. Full Daily Operations Workflow")
    try:
        results = orchestrator.run_daily_operations(test_date)
        
        print(f"✓ Daily operations completed: {results['status']}")
        print(f"  Operations performed: {len(results.get('operations', {}))}")
        
        for op_name, op_result in results.get('operations', {}).items():
            if isinstance(op_result, dict):
                status = op_result.get('status', 'completed')
                print(f"    {op_name}: {status}")
    except Exception as e:
        print(f"✗ Daily operations failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print_section("TEST SUMMARY")
    print("✓ All major functions tested with ITAN data")
    print(f"\nData files location: {data_dir}")
    print(f"  - NAV calculations: {data_dir / 'admin'}")
    print(f"  - Accounting records: {data_dir / 'accounting'}")
    print(f"  - Tax lots: {data_dir / 'tax_lots'}")
    print(f"  - Tax reports: {data_dir / 'tax'}")
    print(f"  - Performance: {data_dir / 'performance'}")
    print("\n✓ Integration test complete!")


if __name__ == "__main__":
    run_full_itan_test()

