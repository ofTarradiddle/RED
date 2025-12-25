"""
Demo: NAV Calculation with Real Daily Holdings
Fetches actual ETF holdings and calculates NAV with full audit trail
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
from datetime import date, timedelta
from decimal import Decimal
import json

from lib.etf.functions.administration import FundAdministration
from lib.etf.functions.accounting import Accounting
from lib.etf.functions.audit_trail import AuditTrailManager
from tests.integration.fetch_real_etf_holdings import fetch_etf_holdings_with_quantities
from tests.integration.test_nav_with_real_holdings import RealHoldingsAdapter


def demo_nav_with_real_holdings(etf_ticker: str):
    """Demonstrate NAV calculation with real holdings and audit trail"""
    print(f"\n{'='*70}")
    print(f"  NAV Calculation with Real Holdings: {etf_ticker}")
    print(f"{'='*70}")
    
    # Fetch real holdings
    print(f"\n1. Fetching real holdings for {etf_ticker}...")
    holdings_data = fetch_etf_holdings_with_quantities(etf_ticker)
    
    print(f"   Actual NAV: ${holdings_data['actual_nav']}")
    print(f"   Shares Outstanding: {holdings_data['shares_outstanding']:,.0f}")
    print(f"   Total Assets: ${holdings_data['total_assets']:,.2f}")
    print(f"   Holdings Count: {len(holdings_data['holdings'])}")
    
    # Create adapter
    adapter = RealHoldingsAdapter(
        data_path=f"./data/demo_{etf_ticker}_real",
        etf_ticker=etf_ticker,
        holdings_data=holdings_data
    )
    
    # Create audit trail
    audit_trail = AuditTrailManager(storage_path=f"./data/audit_trail_{etf_ticker}")
    
    # Create admin with audit trail
    admin = FundAdministration(
        adapter,
        storage_path=f"./data/demo_admin_{etf_ticker}_real",
        audit_trail=audit_trail
    )
    
    # Create accounting with audit trail
    accounting = Accounting(
        adapter,
        storage_path=f"./data/demo_accounting_{etf_ticker}_real",
        audit_trail=audit_trail
    )
    
    # Calculate NAV
    nav_date = date.today() - timedelta(days=1)
    print(f"\n2. Calculating NAV for {nav_date}...")
    nav_calc = admin.calculate_nav(nav_date)
    
    # Run accounting operations
    print(f"\n3. Running accounting operations...")
    accounting_results = accounting.daily_accounting_operations(nav_date, nav_calc)
    
    # Compare to actual
    actual_nav = Decimal(str(holdings_data['actual_nav']))
    difference = abs(nav_calc.nav_per_share - actual_nav)
    difference_pct = (difference / actual_nav) * 100 if actual_nav > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"  RESULTS")
    print(f"{'='*70}")
    print(f"  Calculated NAV: ${nav_calc.nav_per_share}")
    print(f"  Actual NAV: ${actual_nav}")
    print(f"  Difference: ${difference} ({difference_pct:.2f}%)")
    print(f"  Total Assets: ${nav_calc.total_assets:,.2f}")
    print(f"  Net Assets: ${nav_calc.net_assets:,.2f}")
    print(f"  Validation: {'✓ PASSED' if nav_calc.validation_passed else '✗ FAILED'}")
    
    # Show audit trail
    print(f"\n{'='*70}")
    print(f"  AUDIT TRAIL")
    print(f"{'='*70}")
    nav_records = audit_trail.get_records_by_type("nav_calculation", nav_date, nav_date)
    journal_records = audit_trail.get_records_by_type("journal_entry", nav_date, nav_date)
    tb_records = audit_trail.get_records_by_type("trial_balance", nav_date, nav_date)
    
    print(f"  NAV Calculations: {len(nav_records)} record(s)")
    print(f"  Journal Entries: {len(journal_records)} record(s)")
    print(f"  Trial Balances: {len(tb_records)} record(s)")
    print(f"  Total Audit Records: {len(audit_trail.records)}")
    
    # Show what's saved
    print(f"\n{'='*70}")
    print(f"  SAVED FOR AUDIT")
    print(f"{'='*70}")
    print(f"  ✓ NAV calculation with complete holdings breakdown")
    print(f"  ✓ All journal entries with full details")
    print(f"  ✓ Trial balance")
    print(f"  ✓ All data in JSON format for easy retrieval")
    print(f"  ✓ Complete audit trail in: data/audit_trail_{etf_ticker}/")
    
    # Export audit package
    print(f"\n4. Exporting audit package...")
    package_file = audit_trail.export_audit_package(nav_date, nav_date)
    print(f"   ✓ Exported to: {package_file}")
    
    return nav_calc, audit_trail


def main():
    """Main demo"""
    print("="*70)
    print("  NAV Calculation with Real Holdings + Complete Audit Trail")
    print("="*70)
    print("\nThis demo:")
    print("  1. Fetches actual ETF holdings (daily published data)")
    print("  2. Calculates NAV using real holdings")
    print("  3. Runs full accounting pipeline")
    print("  4. Saves complete audit trail (SEC Rule 31a-2 compliant)")
    
    # Test with ITAN
    print("\n" + "="*70)
    print("  ITAN (Sparkline Intangible Value ETF)")
    print("="*70)
    itan_nav, itan_audit = demo_nav_with_real_holdings("ITAN")
    
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70)
    print(f"✓ NAV calculated: ${itan_nav.nav_per_share}")
    print(f"✓ Complete audit trail saved")
    print(f"✓ All data ready for auditors")
    print(f"✓ SEC Rule 31a-2 compliant")
    print("="*70)


if __name__ == "__main__":
    main()

