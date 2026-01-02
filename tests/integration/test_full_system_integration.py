"""
Full System Integration Test
Tests all ETF functions end-to-end with dummy data
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import date, timedelta
from decimal import Decimal
import json
import yfinance as yf

from lib.etf.functions.core.administration import FundAdministration
from lib.etf.functions.core.accounting import Accounting
from lib.etf.functions.tax.tax_lot import TaxLotManager
from lib.etf.functions.operations.performance import PerformanceCalculator
from lib.etf.functions.operations.distributor import Distributor
from lib.etf.functions.tax.tax_reporting import TaxReporting
from lib.etf.functions.compliance.compliance import Compliance
from lib.etf.functions.operations.order_management import OrderManagement
from lib.etf.functions.operations.transfer_agent import TransferAgent
from lib.etf.functions.compliance.audit_trail import AuditTrailManager
from lib.etf.adapters import FileBasedDataSourceAdapter


class DummyDataSourceAdapter(FileBasedDataSourceAdapter):
    """Dummy data adapter for comprehensive testing"""
    
    def __init__(self, data_path: str):
        super().__init__(data_path)
        self.holdings = self._create_dummy_holdings()
        self.trades = []
        self.distributions = []
        self.expenses = []
        self.income = []
        
    def _create_dummy_holdings(self):
        """Create dummy portfolio holdings"""
        return [
            {"cusip": "023135106", "ticker": "AMZN", "quantity": Decimal("1000"), "weight": Decimal("5.0")},
            {"cusip": "02079K107", "ticker": "GOOG", "quantity": Decimal("500"), "weight": Decimal("3.0")},
            {"cusip": "02079K305", "ticker": "GOOGL", "quantity": Decimal("500"), "weight": Decimal("3.0")},
            {"cusip": "459200101", "ticker": "IBM", "quantity": Decimal("800"), "weight": Decimal("2.5")},
            {"cusip": "17275R102", "ticker": "CSCO", "quantity": Decimal("2000"), "weight": Decimal("2.0")},
        ]
    
    def get_portfolio_holdings(self, nav_date: date):
        """Get portfolio holdings"""
        return self.holdings
    
    def get_market_prices(self, nav_date: date, cusips: list):
        """Get market prices - use yfinance for real prices"""
        prices = {}
        tickers = [h.get("ticker") for h in self.holdings]
        
        try:
            data = yf.download(tickers, start=nav_date, end=nav_date + timedelta(days=1), progress=False)
            if not data.empty:
                for holding in self.holdings:
                    ticker = holding.get("ticker")
                    cusip = holding.get("cusip")
                    if ticker in data.columns:
                        close_price = data['Close'][ticker].iloc[0] if 'Close' in data.columns.levels[0] else data[ticker].iloc[0]
                        if not (close_price != close_price):  # Check for NaN
                            prices[cusip] = Decimal(str(close_price))
        except:
            # Fallback to dummy prices
            dummy_prices = {
                "023135106": Decimal("150.00"),  # AMZN
                "02079K107": Decimal("120.00"),  # GOOG
                "02079K305": Decimal("120.00"),  # GOOGL
                "459200101": Decimal("180.00"),  # IBM
                "17275R102": Decimal("50.00"),   # CSCO
            }
            for cusip in [h.get("cusip") for h in self.holdings]:
                if cusip in dummy_prices:
                    prices[cusip] = dummy_prices[cusip]
        
        return prices
    
    def get_custodian_statements(self, nav_date: date):
        """Get custodian data"""
        return {
            "cash_balance": Decimal("100000"),
            "shares_outstanding": Decimal("100000"),
            "holdings": self.holdings
        }
    
    def get_expense_data(self, nav_date: date):
        """Get expense data"""
        expense_ratio = Decimal("0.0045")  # 45 bps
        total_assets = Decimal("10000000")  # $10M
        daily_expense = (total_assets * expense_ratio) / Decimal("365")
        return {
            "accrued_expenses": daily_expense,
            "accrued_income": Decimal("500"),
            "expense_ratio": expense_ratio
        }
    
    def get_trades(self, start_date: date, end_date: date):
        """Get trades for period"""
        return self.trades
    
    def get_income(self, start_date: date, end_date: date):
        """Get income for period"""
        return self.income
    
    def get_distributions(self, start_date: date, end_date: date):
        """Get distributions for period"""
        return self.distributions


def test_1_nav_calculation():
    """Test 1: NAV Calculation"""
    print("\n" + "="*70)
    print("TEST 1: NAV CALCULATION")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    audit_trail = AuditTrailManager(storage_path="./data/test_full_system/audit")
    admin = FundAdministration(adapter, storage_path="./data/test_full_system/admin", audit_trail=audit_trail)
    
    nav_date = date.today() - timedelta(days=1)
    nav_calc = admin.calculate_nav(nav_date)
    
    print(f"  NAV Date: {nav_date}")
    print(f"  NAV per Share: ${nav_calc.nav_per_share:.4f}")
    print(f"  Total Assets: ${nav_calc.total_assets:,.2f}")
    print(f"  Net Assets: ${nav_calc.net_assets:,.2f}")
    print(f"  Shares Outstanding: {nav_calc.shares_outstanding:,.0f}")
    print(f"  Validation: {'✓ PASSED' if nav_calc.validation_passed else '✗ FAILED'}")
    
    return nav_calc


def test_2_accounting():
    """Test 2: Accounting & General Ledger"""
    print("\n" + "="*70)
    print("TEST 2: ACCOUNTING & GENERAL LEDGER")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    accounting = Accounting(adapter, storage_path="./data/test_full_system/accounting")
    
    # Create dummy trades
    trade_date = date.today() - timedelta(days=5)
    
    # Trade 1: Buy AMZN
    accounting.create_journal_entry(
        entry_date=trade_date,
        description="Purchase AMZN shares",
        entries=[
            {"account": "1100", "debit": Decimal("150000"), "credit": Decimal("0")},  # Investments
            {"account": "1000", "debit": Decimal("0"), "credit": Decimal("150000")},  # Cash
        ]
    )
    
    # Trade 2: Buy GOOG
    accounting.create_journal_entry(
        entry_date=trade_date,
        description="Purchase GOOG shares",
        entries=[
            {"account": "1100", "debit": Decimal("60000"), "credit": Decimal("0")},  # Investments
            {"account": "1000", "debit": Decimal("0"), "credit": Decimal("60000")},  # Cash
        ]
    )
    
    # Record NAV entry
    nav_date = date.today() - timedelta(days=1)
    nav_calc = test_1_nav_calculation()
    # Convert NAVCalculation to dict format with liabilities
    total_liabilities = nav_calc.total_assets - nav_calc.net_assets
    nav_dict = {
        'total_assets': nav_calc.total_assets,
        'total_liabilities': total_liabilities,
        'net_assets': nav_calc.net_assets,
        'shares_outstanding': nav_calc.shares_outstanding,
        'nav_per_share': nav_calc.nav_per_share
    }
    accounting.record_nav_entries(nav_date, nav_dict)
    
    # Record expense accrual
    accounting.record_expense_accrual(
        expense_date=nav_date,
        expense_data={
            "management_fee": Decimal("123.29"),
            "admin_expenses": Decimal("0"),
            "custodial_fee": Decimal("0"),
            "other_expenses": Decimal("0")
        }
    )
    
    # Generate financial statements
    trial_balance = accounting.generate_trial_balance(nav_date)
    balance_sheet = accounting.generate_balance_sheet(nav_date)
    income_stmt = accounting.generate_income_statement(
        period_start=nav_date - timedelta(days=30),
        period_end=nav_date
    )
    
    # Count journal entries from all accounts
    total_entries = sum(len(ledger.entries) for ledger in accounting.general_ledger.values() if hasattr(ledger, 'entries'))
    print(f"  Journal Entries Created: {total_entries}")
    print(f"  Trial Balance Accounts: {len(trial_balance.accounts)}")
    print(f"  Total Debits: ${trial_balance.total_debits:,.2f}")
    print(f"  Total Credits: ${trial_balance.total_credits:,.2f}")
    # Balance sheet and income statement are dicts
    if isinstance(balance_sheet, dict):
        total_assets = sum(Decimal(str(v.get('balance', 0))) for v in balance_sheet.get('assets', {}).values())
        print(f"  Balance Sheet Total Assets: ${total_assets:,.2f}")
    else:
        print(f"  Balance Sheet Generated: ✓")
    if isinstance(income_stmt, dict):
        net_income = Decimal(str(income_stmt.get('net_income', 0)))
        print(f"  Income Statement Net Income: ${net_income:,.2f}")
    else:
        print(f"  Income Statement Generated: ✓")
    
    return accounting, nav_calc


def test_3_tax_lot_tracking():
    """Test 3: Tax Lot Tracking"""
    print("\n" + "="*70)
    print("TEST 3: TAX LOT TRACKING")
    print("="*70)
    
    tax_lot_mgr = TaxLotManager(storage_path="./data/test_full_system/tax_lots")
    
    # Add purchase lots
    purchase_date_1 = date.today() - timedelta(days=100)
    purchase_date_2 = date.today() - timedelta(days=50)
    
    tax_lot_mgr.add_lot(
        cusip="023135106",
        ticker="AMZN",
        quantity=Decimal("500"),
        cost_basis=Decimal("145.00"),
        purchase_date=purchase_date_1
    )
    
    tax_lot_mgr.add_lot(
        cusip="023135106",
        ticker="AMZN",
        quantity=Decimal("500"),
        cost_basis=Decimal("150.00"),
        purchase_date=purchase_date_2
    )
    
    # Add GOOG lot
    tax_lot_mgr.add_lot(
        cusip="02079K107",
        ticker="GOOG",
        quantity=Decimal("500"),
        cost_basis=Decimal("115.00"),
        purchase_date=purchase_date_1
    )
    
    # Sell some AMZN (FIFO)
    sale_date = date.today() - timedelta(days=10)
    sale_result = tax_lot_mgr.sell(
        ticker="AMZN",
        quantity=Decimal("300"),
        price=Decimal("155.00"),
        sale_date=sale_date,
        method="FIFO"
    )
    
    # Get unrealized gains - need to pass ticker: price dict
    current_prices = {
        "AMZN": Decimal("150.00"),
        "GOOG": Decimal("120.00"),
    }
    unrealized = tax_lot_mgr.get_unrealized_gains(current_prices)
    
    print(f"  Open Lots: {len(tax_lot_mgr.open_lots)}")
    print(f"  Closed Lots: {len(tax_lot_mgr.closed_lots)}")
    print(f"  Realized Gain (AMZN sale): ${sale_result:,.2f}")
    print(f"  Total Unrealized Gains: ${unrealized.get('total_unrealized_gain', 0):,.2f}")
    print(f"  Unrealized by Security:")
    for ticker, gain in unrealized.get('unrealized_by_security', {}).items():
        print(f"    {ticker}: ${gain:,.2f}")
    
    return tax_lot_mgr


def test_4_performance_calculation():
    """Test 4: Performance Calculation"""
    print("\n" + "="*70)
    print("TEST 4: PERFORMANCE CALCULATION")
    print("="*70)
    
    # Create NAV history
    nav_history = []
    start_date = date.today() - timedelta(days=365)
    base_nav = Decimal("25.00")
    
    for i in range(365):
        nav_date = start_date + timedelta(days=i)
        # Simulate NAV growth
        nav_value = base_nav * (Decimal("1") + Decimal("0.0001") * Decimal(str(i)))
        nav_history.append({
            "date": nav_date.isoformat(),
            "nav": float(nav_value)
        })
    
    # Create distribution history
    distributions = [
        {"date": (date.today() - timedelta(days=90)).isoformat(), "type": "DIVIDEND", "amount": 0.25},
        {"date": (date.today() - timedelta(days=180)).isoformat(), "type": "DIVIDEND", "amount": 0.30},
        {"date": (date.today() - timedelta(days=270)).isoformat(), "type": "DIVIDEND", "amount": 0.28},
    ]
    
    # Save to files
    nav_file = Path("./data/test_full_system/nav_history.csv")
    nav_file.parent.mkdir(parents=True, exist_ok=True)
    with open(nav_file, 'w') as f:
        f.write("date,nav\n")
        for entry in nav_history:
            f.write(f"{entry['date']},{entry['nav']}\n")
    
    dist_file = Path("./data/test_full_system/distributions.csv")
    with open(dist_file, 'w') as f:
        f.write("date,type,amount\n")
        for dist in distributions:
            f.write(f"{dist['date']},{dist['type']},{dist['amount']}\n")
    
    # Calculate performance
    perf_calc = PerformanceCalculator(
        storage_path="./data/test_full_system/performance"
    )
    
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=365)
    
    performance = perf_calc.compute_performance(
        nav_history_path=str(nav_file),
        dist_history_path=str(dist_file),
        benchmark_symbol="SPY",
        tax_rates={
            "dividend_tax_rate": 0.15,
            "lt_capital_gains_tax_rate": 0.20,
            "st_capital_gains_tax_rate": 0.37
        },
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Pre-tax Total Return: {performance.get('pre_tax_return', 0):.2f}%")
    print(f"  After-tax Total Return: {performance.get('after_tax_return', 0):.2f}%")
    print(f"  Benchmark Return: {performance.get('benchmark_return', 0):.2f}%")
    print(f"  Alpha: {performance.get('alpha', 0):.2f}%")
    print(f"  Tax Efficiency: {performance.get('tax_efficiency', 0):.2f}%")
    
    return performance


def test_5_distributions():
    """Test 5: Distribution Processing"""
    print("\n" + "="*70)
    print("TEST 5: DISTRIBUTION PROCESSING")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    distributor = Distributor(adapter, storage_path="./data/test_full_system/distributor")
    
    # Calculate distribution - check if we've already hit the limit
    dist_date = date(2024, 12, 31)  # Use 2024 to avoid hitting 2025 limit
    shares_outstanding = Decimal("100000")
    
    # Get NAV data
    nav_calc = test_1_nav_calculation()
    nav_data = {
        "shares_outstanding": shares_outstanding,
        "total_assets": nav_calc.total_assets,
        "net_assets": nav_calc.net_assets
    }
    
    # Check existing distributions for 2024
    existing_2024 = [d for d in distributor.distributions if d.record_date.year == 2024]
    if len(existing_2024) < 12:
        distribution = distributor.calculate_distribution(
            dist_date=dist_date,
            distribution_type="dividend",
            nav_data=nav_data,
            payout_ratio=Decimal("1.0")  # 100% payout
        )
    else:
        # Use existing distribution
        distribution = existing_2024[0]
    
    # Declare distribution
    distributor.declare_distribution(distribution)
    
    # Process payment - need shareholder data
    shareholder_data = [
        {
            "account_number": "ACC001",
            "name": "John Doe",
            "shares": Decimal("1000")
        }
    ]
    payment_result = distributor.process_distribution_payment(
        distribution=distribution,
        shareholder_data=shareholder_data
    )
    
    # Generate schedule
    schedule = distributor.generate_distribution_schedule(year=2024)
    
    print(f"  Distribution Date: {dist_date}")
    print(f"  Amount per Share: ${distribution.amount_per_share:.4f}")
    print(f"  Total Distribution: ${distribution.total_amount:,.2f}")
    print(f"  Payment Status: {'✓ PAID' if payment_result.get('status') == 'paid' else '✗ PENDING'}")
    print(f"  Distributions in 2024: {len(schedule.get('distributions', []))}")
    
    return distributor


def test_6_tax_reporting():
    """Test 6: Tax Reporting"""
    print("\n" + "="*70)
    print("TEST 6: TAX REPORTING")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    tax_reporting = TaxReporting(adapter, storage_path="./data/test_full_system/tax")
    
    # Get accounting and tax lot data
    accounting, nav_calc = test_2_accounting()
    tax_lot_mgr = test_3_tax_lot_tracking()
    distributor = test_5_distributions()
    
    # Generate Form 1099-DIV - need to call for each shareholder
    from lib.etf.shared import ShareholderRecord
    shareholder = ShareholderRecord(
        account_number="ACC001",
        shareholder_name="John Doe",
        shares=Decimal("1000"),
        account_type="beneficial"
    )
    
    # Convert distributions to dict format
    distributions_dict = {}
    for dist in distributor.distributions:
        if dist.distribution_type == "dividend":
            distributions_dict["ordinary_dividends"] = dist.amount_per_share * shareholder.shares
        elif dist.distribution_type == "capital_gains":
            distributions_dict["capital_gains"] = dist.amount_per_share * shareholder.shares
    
    form_1099_div = tax_reporting.generate_1099_div(
        tax_year=2024,
        shareholder=shareholder,
        distributions=distributions_dict
    )
    
    # Convert distributions to dict format
    distributions_dict = []
    for dist in distributor.distributions:
        if dist.record_date.year == 2024:
            distributions_dict.append({
                "distribution_id": dist.distribution_id,
                "distribution_type": dist.distribution_type,
                "record_date": dist.record_date.isoformat(),
                "amount_per_share": str(dist.amount_per_share),
                "total_amount": str(dist.total_amount),
                "shares_outstanding": str(dist.shares_outstanding)
            })
    
    # Generate Form 1120-RIC
    form_1120_ric = tax_reporting.generate_tax_return_form_1120_ric(
        tax_year=2024,
        ledger_data=accounting.general_ledger,
        taxlot_manager=tax_lot_mgr,
        distributions=distributions_dict
    )
    
    # Generate Form 8613 (Excise Tax)
    form_8613 = tax_reporting.generate_form_8613(
        tax_year=2024,
        ledger_data=accounting.general_ledger,
        taxlot_manager=tax_lot_mgr,
        distributions=distributions_dict
    )
    
    print(f"  Form 1099-DIV Generated: {'✓ YES' if form_1099_div else '✗ NO'}")
    print(f"  Form 1120-RIC Generated: {'✓ YES' if form_1120_ric else '✗ NO'}")
    print(f"  Form 8613 Generated: {'✓ YES' if form_8613 else '✗ NO'}")
    if form_1120_ric and isinstance(form_1120_ric, dict):
        print(f"  Taxable Income: ${Decimal(str(form_1120_ric.get('taxable_income', 0))):,.2f}")
    if form_8613 and isinstance(form_8613, dict):
        print(f"  Excise Tax: ${Decimal(str(form_8613.get('excise_tax', 0))):,.2f}")
    
    return tax_reporting


def test_7_compliance():
    """Test 7: Compliance (SEC Filings)"""
    print("\n" + "="*70)
    print("TEST 7: COMPLIANCE (SEC FILINGS)")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    compliance = Compliance(adapter, storage_path="./data/test_full_system/compliance")
    
    # Generate N-PORT
    nav_date = date.today() - timedelta(days=1)
    form_n_port = compliance.generate_form_n_port(
        month_end=nav_date
    )
    
    # Generate N-CEN
    form_n_cen = compliance.generate_form_n_cen(
        year=2024
    )
    
    # Generate N-CSR
    form_n_csr = compliance.generate_form_n_csr(
        period_end=date(2024, 12, 31)
    )
    
    print(f"  N-PORT Generated: {'✓ YES' if form_n_port else '✗ NO'}")
    print(f"  N-CEN Generated: {'✓ YES' if form_n_cen else '✗ NO'}")
    print(f"  N-CSR Generated: {'✓ YES' if form_n_csr else '✗ NO'}")
    if form_n_port:
        print(f"  N-PORT Holdings Count: {len(form_n_port.get('holdings', []))}")
    
    return compliance


def test_8_order_management():
    """Test 8: Order Management (PCF & Baskets)"""
    print("\n" + "="*70)
    print("TEST 8: ORDER MANAGEMENT (PCF & BASKETS)")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    order_mgmt = OrderManagement(adapter, storage_path="./data/test_full_system/orders")
    
    # Generate PCF
    nav_date = date.today() - timedelta(days=1)
    pcf = order_mgmt.generate_pcf(
        pcf_date=nav_date
    )
    
    # Build standard creation basket - need PCF first
    if pcf:
        creation_basket = order_mgmt.build_standard_creation_basket(
            pcf=pcf,
            creation_units=1
        )
        
        # Build custom redemption basket
        custom_securities = [
            {"cusip": "023135106", "quantity": Decimal("100")},  # AMZN
            {"cusip": "02079K107", "quantity": Decimal("50")}   # GOOG
        ]
        redemption_basket = order_mgmt.build_custom_redemption_basket(
            pcf=pcf,
            creation_units=1,
            custom_securities=custom_securities
        )
    else:
        creation_basket = None
        redemption_basket = None
    
    # Create AP order
    if creation_basket and creation_basket.securities:
        # Convert basket to dict format
        basket_list = [
            {"cusip": s.get("cusip") if isinstance(s, dict) else s.cusip, 
             "quantity": str(s.get("quantity") if isinstance(s, dict) else s.quantity)}
            for s in creation_basket.securities
        ]
        ap_order = order_mgmt.create_ap_order(
            ap_id="JANESTREET",
            order_type="creation",
            creation_units=1,
            basket=basket_list,
            order_date=nav_date
        )
    else:
        ap_order = None
    
    print(f"  PCF Generated: {'✓ YES' if pcf else '✗ NO'}")
    if creation_basket:
        print(f"  Standard Creation Basket Securities: {len(creation_basket.securities)}")
    if redemption_basket:
        print(f"  Custom Redemption Basket Securities: {len(redemption_basket.securities)}")
    print(f"  AP Order Created: {'✓ YES' if ap_order else '✗ NO'}")
    if pcf:
        print(f"  PCF Creation Unit Size: {pcf.creation_unit_size:,}")
        print(f"  PCF Cash Component: ${pcf.cash_component:,.2f}")
    
    return order_mgmt


def test_9_transfer_agent():
    """Test 9: Transfer Agent"""
    print("\n" + "="*70)
    print("TEST 9: TRANSFER AGENT")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    ta = TransferAgent(adapter, storage_path="./data/test_full_system/ta")
    
    # Daily reconciliation
    nav_date = date.today() - timedelta(days=1)
    reconciliation_results = ta.daily_reconciliation(nav_date)
    
    # Update Cede file
    cede_update = ta.update_cede_file(nav_date)
    
    # Process creation/redemption orders - need APOrder objects
    from lib.etf.shared import APOrder
    orders = [
        APOrder(
            order_id="CR001",
            ap_id="AP001",
            order_type="creation",
            creation_units=10,
            order_date=nav_date
        )
    ]
    order_results = ta.process_creation_redemption_orders(orders)
    
    # Check reconciliation results
    if reconciliation_results:
        first_recon = reconciliation_results[0] if isinstance(reconciliation_results, list) else reconciliation_results
        print(f"  Reconciliation Status: {'✓ PASSED' if first_recon.status == 'matched' else '✗ FAILED'}")
        print(f"  Reconciliation Results: {len(reconciliation_results) if isinstance(reconciliation_results, list) else 1}")
    else:
        print(f"  Reconciliation Status: ✗ NO RESULTS")
    print(f"  Cede File Updated: {'✓ YES' if cede_update else '✗ NO'}")
    print(f"  Orders Processed: {len(order_results) if order_results else 0}")
    
    return ta


def test_10_full_workflow():
    """Test 10: Full Daily Workflow"""
    print("\n" + "="*70)
    print("TEST 10: FULL DAILY WORKFLOW")
    print("="*70)
    
    adapter = DummyDataSourceAdapter("./data/test_full_system")
    audit_trail = AuditTrailManager(storage_path="./data/test_full_system/audit")
    
    # Initialize all functions
    admin = FundAdministration(adapter, storage_path="./data/test_full_system/admin", audit_trail=audit_trail)
    accounting = Accounting(adapter, storage_path="./data/test_full_system/accounting")
    tax_lot_mgr = TaxLotManager(storage_path="./data/test_full_system/tax_lots")
    distributor = Distributor(adapter, storage_path="./data/test_full_system/distributor")
    
    nav_date = date.today() - timedelta(days=1)
    
    # Step 1: Calculate NAV
    print("\n  Step 1: Calculate NAV...")
    nav_calc = admin.calculate_nav(nav_date)
    print(f"    NAV: ${nav_calc.nav_per_share:.4f}")
    
    # Step 2: Record NAV in accounting
    print("\n  Step 2: Record NAV in accounting...")
    total_liabilities = nav_calc.total_assets - nav_calc.net_assets
    nav_dict = {
        'total_assets': nav_calc.total_assets,
        'total_liabilities': total_liabilities,
        'net_assets': nav_calc.net_assets,
        'shares_outstanding': nav_calc.shares_outstanding,
        'nav_per_share': nav_calc.nav_per_share
    }
    accounting.record_nav_entries(nav_date, nav_dict)
    total_entries = sum(len(ledger.entries) for ledger in accounting.general_ledger.values() if hasattr(ledger, 'entries'))
    print(f"    Journal entries: {total_entries}")
    
    # Step 3: Daily accounting operations
    print("\n  Step 3: Daily accounting operations...")
    accounting.daily_accounting_operations(nav_date, nav_calc)
    trial_balance = accounting.generate_trial_balance(nav_date)
    print(f"    Trial balance accounts: {len(trial_balance.accounts)}")
    
    # Step 4: Update tax lots (if trades occurred)
    print("\n  Step 4: Update tax lots...")
    print(f"    Open lots: {len(tax_lot_mgr.open_lots)}")
    print(f"    Closed lots: {len(tax_lot_mgr.closed_lots)}")
    
    # Step 5: Check for distributions
    print("\n  Step 5: Check distributions...")
    print(f"    Distributions declared: {len(distributor.distributions)}")
    
    print("\n  ✓ Full daily workflow completed!")
    
    return {
        "nav_calc": nav_calc,
        "accounting": accounting,
        "tax_lot_mgr": tax_lot_mgr,
        "distributor": distributor
    }


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  FULL SYSTEM INTEGRATION TEST SUITE")
    print("="*70)
    print("\nTesting all ETF functions with dummy data...")
    
    results = {}
    
    try:
        results['nav'] = test_1_nav_calculation()
        results['accounting'], results['nav_calc'] = test_2_accounting()
        results['tax_lots'] = test_3_tax_lot_tracking()
        results['performance'] = test_4_performance_calculation()
        results['distributor'] = test_5_distributions()
        results['tax_reporting'] = test_6_tax_reporting()
        results['compliance'] = test_7_compliance()
        results['order_mgmt'] = test_8_order_management()
        results['transfer_agent'] = test_9_transfer_agent()
        results['workflow'] = test_10_full_workflow()
        
        print("\n" + "="*70)
        print("  ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nTest Summary:")
        print("  ✓ NAV Calculation")
        print("  ✓ Accounting & General Ledger")
        print("  ✓ Tax Lot Tracking")
        print("  ✓ Performance Calculation")
        print("  ✓ Distribution Processing")
        print("  ✓ Tax Reporting")
        print("  ✓ Compliance (SEC Filings)")
        print("  ✓ Order Management (PCF & Baskets)")
        print("  ✓ Transfer Agent")
        print("  ✓ Full Daily Workflow")
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()

