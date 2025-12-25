"""
Tests for Enhanced Tax Reporting Module (Form 1120-RIC and Form 8613)
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.tax_reporting import TaxReporting
from lib.etf.functions.tax_lot import TaxLotManager


class TestTaxReportingEnhanced:
    """Test enhanced tax reporting functionality"""
    
    def test_generate_form_1120_ric(self, temp_storage, mock_adapter):
        """Test Form 1120-RIC generation"""
        tax_reporting = TaxReporting(mock_adapter, storage_path=str(temp_storage))
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Set up ledger data
        ledger_data = {
            'Dividend Income': -Decimal('100000'),  # Credit balance (negative)
            'Realized Gain': -Decimal('50000')
        }
        
        # Add some realized gains
        taxlot_manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2023, 1, 1))
        taxlot_manager.sell("AAPL", Decimal('50'), Decimal('160.00'), date(2024, 6, 15))
        
        distributions = [
            {"distribution_type": "dividend", "total_amount": "95000"},
            {"distribution_type": "capital_gains", "total_amount": "45000"}
        ]
        
        form = tax_reporting.generate_tax_return_form_1120_ric(
            tax_year=2024,
            ledger_data=ledger_data,
            taxlot_manager=taxlot_manager,
            distributions=distributions
        )
        
        assert form['form_type'] == '1120-RIC'
        assert form['tax_year'] == 2024
        assert 'investment_company_taxable_income' in form
        assert 'dividends_paid_deduction' in form
        assert 'taxable_income_after_deduction' in form
        assert 'corporate_tax_due' in form
        assert Decimal(form['total_income']) == Decimal('100000')
    
    def test_generate_form_8613(self, temp_storage, mock_adapter):
        """Test Form 8613 (Excise Tax) generation"""
        tax_reporting = TaxReporting(mock_adapter, storage_path=str(temp_storage))
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Set up ledger data
        ledger_data = {
            'Dividend Income': -Decimal('100000'),  # Credit balance
        }
        
        # Add realized gains
        taxlot_manager.add_lot("AAPL", Decimal('100'), Decimal('150.00'), date(2023, 1, 1))
        taxlot_manager.sell("AAPL", Decimal('50'), Decimal('160.00'), date(2024, 6, 15))
        
        # Distribute less than required to create shortfall
        # Required: 98% of 100k = 98k, but only distribute 95k
        distributions = [
            {"distribution_type": "dividend", "total_amount": "95000"},  # 95k (less than 98k required)
            {"distribution_type": "capital_gains", "total_amount": "400"}  # Less than 98.2% of 500
        ]
        
        form = tax_reporting.generate_form_8613(
            tax_year=2024,
            ledger_data=ledger_data,
            taxlot_manager=taxlot_manager,
            distributions=distributions
        )
        
        assert form['form_type'] == '8613'
        assert form['calendar_year'] == 2024
        assert 'ordinary_income_required_distribution' in form
        assert 'capital_gain_required_distribution' in form
        assert 'total_required_distribution' in form
        assert 'actual_distribution' in form
        assert 'undistributed_amount' in form
        assert 'excise_tax_4pct' in form
        
        # Required distribution should be 98% of income
        required = Decimal(form['ordinary_income_required_distribution'])
        assert required == Decimal('98000')  # 98% of 100k
        
        # Should have shortfall and excise tax
        shortfall = Decimal(form['undistributed_amount'])
        excise_tax = Decimal(form['excise_tax_4pct'])
        assert shortfall > 0  # Should have shortfall (98k required - 95k distributed = 3k, plus capital gains shortfall)
        assert excise_tax == shortfall * Decimal('0.04')
    
    def test_form_8613_no_shortfall(self, temp_storage, mock_adapter):
        """Test Form 8613 when distribution requirement is met"""
        tax_reporting = TaxReporting(mock_adapter, storage_path=str(temp_storage))
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        ledger_data = {
            'Dividend Income': -Decimal('100000'),
        }
        
        # Distribute 100% (more than required 98%)
        distributions = [
            {"distribution_type": "dividend", "total_amount": "100000"}
        ]
        
        form = tax_reporting.generate_form_8613(
            tax_year=2024,
            ledger_data=ledger_data,
            taxlot_manager=taxlot_manager,
            distributions=distributions
        )
        
        # Should have no shortfall
        shortfall = Decimal(form['undistributed_amount'])
        excise_tax = Decimal(form['excise_tax_4pct'])
        assert shortfall == Decimal('0')
        assert excise_tax == Decimal('0')

