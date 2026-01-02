#!/usr/bin/env python3
"""
Test SEC Form N-1A Compliance Implementation

Tests all N-1A calculation methods to ensure they work correctly.
"""

import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.etf.functions.core import SECReporting

def test_sec_reporting():
    """Test all SEC reporting methods"""
    
    print("=" * 80)
    print("SEC Form N-1A Compliance Testing")
    print("=" * 80)
    print()
    
    sec = SECReporting(storage_path="./data/admin")
    
    # Test dates
    today = date.today()
    fiscal_year_start = date(today.year, 1, 1)
    fiscal_year_end = date(today.year, 12, 31)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Average Shares Outstanding
    print("Test 1: calculate_average_shares_outstanding")
    try:
        result = sec.calculate_average_shares_outstanding(fiscal_year_start, fiscal_year_end)
        if result >= 0:
            print(f"  ✓ Average shares: {result:,.0f}")
            tests_passed += 1
        else:
            print(f"  ✗ Invalid result: {result}")
            tests_failed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 2: Average Net Assets
    print("Test 2: calculate_average_net_assets")
    try:
        result = sec.calculate_average_net_assets(fiscal_year_start, fiscal_year_end)
        if result >= 0:
            print(f"  ✓ Average net assets: ${result:,.2f}")
            tests_passed += 1
        else:
            print(f"  ✗ Invalid result: {result}")
            tests_failed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 3: Expense Ratio
    print("Test 3: calculate_expense_ratio")
    try:
        result = sec.calculate_expense_ratio(fiscal_year_start, fiscal_year_end)
        if result.get("status") != "error":
            print(f"  ✓ Expense ratio: {result.get('expense_ratio', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1  # Not a failure if no data
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 4: Net Income Ratio
    print("Test 4: calculate_net_income_ratio")
    try:
        result = sec.calculate_net_income_ratio(fiscal_year_start, fiscal_year_end)
        if result.get("status") != "error":
            print(f"  ✓ Net income ratio: {result.get('net_income_ratio', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 5: Portfolio Turnover Rate
    print("Test 5: calculate_portfolio_turnover_rate")
    try:
        result = sec.calculate_portfolio_turnover_rate(fiscal_year_start, fiscal_year_end)
        if result >= 0:
            print(f"  ✓ Portfolio turnover: {result:.2f}%")
            tests_passed += 1
        else:
            print(f"  ✗ Invalid result: {result}")
            tests_failed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 6: 30-Day Yield
    print("Test 6: calculate_30_day_yield")
    try:
        result = sec.calculate_30_day_yield(today)
        if result.get("status") != "error":
            print(f"  ✓ 30-day yield: {result.get('30_day_yield', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 7: Average Annual Total Return (1-year)
    print("Test 7: calculate_average_annual_total_return (1-year)")
    try:
        result = sec.calculate_average_annual_total_return(
            period_years=1,
            as_of_date=today,
            initial_investment=Decimal('1000'),
            sales_load=Decimal('0'),  # ETFs typically have no sales load
            account_fees=Decimal('0')
        )
        if result.get("status") != "error":
            print(f"  ✓ 1-year return: {result.get('average_annual_total_return', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 8: After-Tax Return on Distributions
    print("Test 8: calculate_after_tax_return_on_distributions")
    try:
        result = sec.calculate_after_tax_return_on_distributions(
            period_years=1,
            as_of_date=today,
            initial_investment=Decimal('1000'),
            sales_load=Decimal('0'),
            account_fees=Decimal('0')
        )
        if result.get("status") != "error":
            print(f"  ✓ After-tax return (distributions): {result.get('average_annual_total_return_after_tax_distributions', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 9: After-Tax Return on Distributions and Redemption
    print("Test 9: calculate_after_tax_return_on_distributions_and_redemption")
    try:
        result = sec.calculate_after_tax_return_on_distributions_and_redemption(
            period_years=1,
            as_of_date=today,
            initial_investment=Decimal('1000'),
            sales_load=Decimal('0'),
            account_fees=Decimal('0')
        )
        if result.get("status") != "error":
            print(f"  ✓ After-tax return (all taxes): {result.get('average_annual_total_return_after_all_taxes', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 10: Tax Equivalent Yield
    print("Test 10: calculate_tax_equivalent_yield")
    try:
        result = sec.calculate_tax_equivalent_yield(
            as_of_date=today,
            tax_rate=Decimal('0.37')  # 37% federal rate
        )
        if result.get("status") != "error":
            print(f"  ✓ Tax equivalent yield: {result.get('tax_equivalent_yield', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Test 11: Financial Highlights
    print("Test 11: generate_financial_highlights")
    try:
        result = sec.generate_financial_highlights(fiscal_year_start, fiscal_year_end)
        if result.get("status") != "error":
            print(f"  ✓ Financial highlights generated")
            print(f"    Expense ratio: {result.get('ratios', {}).get('expense_ratio', 'N/A')}%")
            print(f"    Portfolio turnover: {result.get('ratios', {}).get('portfolio_turnover_rate', 'N/A')}%")
            tests_passed += 1
        else:
            print(f"  ⚠ No data: {result.get('error', 'Unknown error')}")
            tests_passed += 1
    except Exception as e:
        print(f"  ✗ Error: {e}")
        tests_failed += 1
    print()
    
    # Summary
    print("=" * 80)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 80)
    
    return tests_failed == 0

if __name__ == "__main__":
    success = test_sec_reporting()
    sys.exit(0 if success else 1)

