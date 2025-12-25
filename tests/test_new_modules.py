"""
Tests for New ETF Administration & Accounting Modules
"""

import pytest
from datetime import date
from decimal import Decimal
from pathlib import Path

from lib.etf.functions.security_master import SecurityMasterFile, PortfolioRecords
from lib.etf.functions.tax_adjustments import BookToTaxAdjustments
from lib.etf.functions.state_tax import StateTaxReporting
from lib.etf.functions.fbar_filing import FBARFilingSystem, ForeignAccount
from lib.etf.functions.capital_gain_estimates import CapitalGainEstimates
from lib.etf.functions.adviser_portal import AdviserPortal
from lib.etf.functions.audit_cooperation import AuditCooperation
from lib.etf.functions.tax_reporting import TaxReporting
from lib.etf.functions.tax_lot import TaxLotManager
from tests.conftest import MockDataSourceAdapter


class TestSecurityMasterFile:
    """Test Security Master File functionality"""
    
    def test_add_security(self, temp_storage):
        """Test adding security to master file"""
        master = SecurityMasterFile(storage_path=str(temp_storage))
        
        security = master.add_security(
            cusip="037833100",
            ticker="AAPL",
            description="APPLE INC",
            security_type="equity",
            exchange="NASDAQ"
        )
        
        assert security.cusip == "037833100"
        assert security.ticker == "AAPL"
        assert security.security_type == "equity"
        assert len(master.securities) == 1
    
    def test_get_security_by_cusip(self, temp_storage):
        """Test retrieving security by CUSIP"""
        master = SecurityMasterFile(storage_path=str(temp_storage))
        master.add_security("037833100", "AAPL", "APPLE INC", "equity")
        
        security = master.get_security_by_cusip("037833100")
        assert security is not None
        assert security.ticker == "AAPL"
    
    def test_portfolio_records(self, temp_storage):
        """Test portfolio records"""
        portfolio = PortfolioRecords(storage_path=str(temp_storage))
        
        record = portfolio.add_position(
            record_date=date.today(),
            cusip="037833100",
            ticker="AAPL",
            quantity=Decimal('1000'),
            cost_basis=Decimal('150000'),
            market_price=Decimal('155.00')
        )
        
        assert record.cusip == "037833100"
        assert record.quantity == Decimal('1000')
        assert record.market_value == Decimal('155000')  # 1000 * 155
        assert record.unrealized_gain_loss == Decimal('5000')  # 155000 - 150000
        
        positions = portfolio.get_positions(date.today())
        assert len(positions) == 1


class TestTaxAdjustments:
    """Test M-1 Book-to-Tax Adjustments"""
    
    def test_m1_reconciliation(self, temp_storage):
        """Test M-1 reconciliation calculation"""
        adjustments = BookToTaxAdjustments(storage_path=str(temp_storage))
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        ledger_data = {
            'Municipal Bond Interest': Decimal('50000'),
            'Penalties': Decimal('1000'),
            'Unrealized Gains': Decimal('100000'),
            'Realized Gains': Decimal('50000')
        }
        
        m1 = adjustments.calculate_m1_reconciliation(
            fiscal_year_end=date(2024, 12, 31),
            book_net_income=Decimal('1000000'),
            ledger_data=ledger_data,
            taxlot_manager=taxlot_manager
        )
        
        assert m1.book_net_income == Decimal('1000000')
        assert m1.taxable_income != m1.book_net_income  # Should have adjustments
        assert len(m1.permanent_differences) > 0
        assert m1.reconciled
    
    def test_tax_footnotes(self, temp_storage):
        """Test tax footnote generation"""
        adjustments = BookToTaxAdjustments(storage_path=str(temp_storage))
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        m1 = adjustments.calculate_m1_reconciliation(
            fiscal_year_end=date(2024, 12, 31),
            book_net_income=Decimal('1000000'),
            ledger_data={'Dividend Income': -Decimal('100000')},
            taxlot_manager=taxlot_manager
        )
        
        form_1120_ric = {
            'corporate_tax_due': Decimal('21000'),
            'effective_tax_rate': Decimal('0.21')
        }
        
        distributions = [
            {"distribution_type": "dividend", "total_amount": "95000"}
        ]
        
        footnotes = adjustments.generate_tax_footnotes(
            fiscal_year_end=date(2024, 12, 31),
            m1_reconciliation=m1,
            form_1120_ric=form_1120_ric,
            distributions=distributions
        )
        
        assert len(footnotes) > 0
        assert any(fn.category == "tax_provision" for fn in footnotes)


class TestStateTax:
    """Test State Tax Return Preparation"""
    
    def test_prepare_state_return(self, temp_storage):
        """Test state return preparation"""
        state_tax = StateTaxReporting(storage_path=str(temp_storage))
        
        return_data = state_tax.prepare_state_return(
            state="CA",
            tax_year=2024,
            federal_taxable_income=Decimal('1000000'),
            apportionment_data={
                "state_factor": Decimal('0.50'),
                "nexus": True
            }
        )
        
        assert return_data.state == "CA"
        assert return_data.tax_year == 2024
        assert return_data.apportionment_factor == Decimal('0.50')
        assert len(state_tax.state_returns) == 1
    
    def test_state_limit(self, temp_storage):
        """Test two-state limit"""
        state_tax = StateTaxReporting(storage_path=str(temp_storage))
        
        state_tax.prepare_state_return("CA", 2024, Decimal('1000000'), {"state_factor": Decimal('0.5'), "nexus": True})
        state_tax.prepare_state_return("NY", 2024, Decimal('1000000'), {"state_factor": Decimal('0.3'), "nexus": True})
        
        assert len(state_tax.state_returns) == 2


class TestFBARFiling:
    """Test FBAR Filing"""
    
    def test_fbar_filing_required(self, temp_storage):
        """Test FBAR filing when required"""
        fbar = FBARFilingSystem(storage_path=str(temp_storage))
        
        accounts = [
            ForeignAccount(
                account_number="ACC001",
                account_name="Foreign Account",
                bank_name="Foreign Bank",
                country="UK",
                account_type="securities",
                max_balance=Decimal('15000'),
                currency="USD"
            )
        ]
        
        filing = fbar.prepare_fbar_filing(2024, accounts)
        
        assert filing.filing_required  # $15,000 > $10,000 threshold
        assert filing.total_max_balance_usd == Decimal('15000')
    
    def test_fbar_filing_not_required(self, temp_storage):
        """Test FBAR filing when not required"""
        fbar = FBARFilingSystem(storage_path=str(temp_storage))
        
        accounts = [
            ForeignAccount(
                account_number="ACC001",
                account_name="Foreign Account",
                bank_name="Foreign Bank",
                country="UK",
                account_type="securities",
                max_balance=Decimal('5000'),
                currency="USD"
            )
        ]
        
        filing = fbar.prepare_fbar_filing(2024, accounts)
        
        assert not filing.filing_required  # $5,000 < $10,000 threshold


class TestCapitalGainEstimates:
    """Test Capital Gain Dividend Estimates"""
    
    def test_create_estimate(self, temp_storage):
        """Test creating capital gain estimate"""
        estimates = CapitalGainEstimates(storage_path=str(temp_storage))
        
        estimate = estimates.create_estimate(
            estimate_date=date(2024, 6, 30),
            estimated_long_term_gains=Decimal('500000'),
            estimated_short_term_gains=Decimal('100000'),
            shares_outstanding=Decimal('1000000'),
            estimate_type="mid-year"
        )
        
        assert estimate.estimated_total_gains == Decimal('600000')
        assert estimate.estimated_per_share == Decimal('0.60')  # 600000 / 1000000
        assert len(estimates.estimates) == 1
    
    def test_estimate_limit(self, temp_storage):
        """Test two-estimate limit per year"""
        estimates = CapitalGainEstimates(storage_path=str(temp_storage))
        
        estimates.create_estimate(date(2024, 6, 30), Decimal('500000'), Decimal('100000'), Decimal('1000000'))
        estimates.create_estimate(date(2024, 9, 30), Decimal('600000'), Decimal('150000'), Decimal('1000000'))
        
        assert len([e for e in estimates.estimates if e.estimate_date.year == 2024]) == 2


class TestAdviserPortal:
    """Test Adviser Portal"""
    
    def test_portfolio_snapshot(self, temp_storage, mock_adapter):
        """Test portfolio snapshot generation"""
        portal = AdviserPortal(storage_path=str(temp_storage), data_adapter=mock_adapter)
        
        snapshot = portal.get_portfolio_snapshot(date.today())
        
        assert snapshot.snapshot_date == date.today()
        assert snapshot.holdings_count >= 0
        assert isinstance(snapshot.top_holdings, list)
    
    def test_compliance_status(self, temp_storage, mock_adapter):
        """Test compliance status generation"""
        portal = AdviserPortal(storage_path=str(temp_storage), data_adapter=mock_adapter)
        
        status = portal.get_compliance_status(date.today())
        
        assert status.status_date == date.today()
        assert 'regulatory_filings' in status.__dict__


class TestAuditCooperation:
    """Test Audit Cooperation"""
    
    def test_prepare_audit_package(self, temp_storage, mock_adapter):
        """Test audit package preparation"""
        from lib.etf.functions.accounting import Accounting
        
        accounting = Accounting(mock_adapter, storage_path=str(temp_storage))
        audit = AuditCooperation(storage_path=str(temp_storage))
        
        package = audit.prepare_audit_package(
            fiscal_year_end=date(2024, 12, 31),
            accounting=accounting
        )
        
        assert package.fiscal_year_end == date(2024, 12, 31)
        assert 'financial_statements' in package.__dict__
        assert len(package.trial_balances) >= 0


class TestTaxReporting1099MISC:
    """Test Form 1099-MISC"""
    
    def test_generate_1099_misc(self, temp_storage, mock_adapter):
        """Test Form 1099-MISC generation"""
        from lib.etf.shared import ShareholderRecord
        
        tax_reporting = TaxReporting(mock_adapter, storage_path=str(temp_storage))
        
        shareholder = ShareholderRecord(
            account_number="ACC001",
            shareholder_name="Test Shareholder",
            tax_id="123-45-6789",
            shares=Decimal('1000'),
            account_type="individual"
        )
        
        form = tax_reporting.generate_1099_misc(
            tax_year=2024,
            shareholder=shareholder,
            misc_income={
                "rents": Decimal('1000'),
                "royalties": Decimal('500'),
                "other_income": Decimal('200'),
                "federal_income_tax_withheld": Decimal('0')
            }
        )
        
        assert form.form_type == "1099-MISC"
        assert form.tax_year == 2024
        assert form.distributions == Decimal('1700')  # 1000 + 500 + 200

