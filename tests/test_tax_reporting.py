"""
Tests for Tax Reporting function
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.tax_reporting import TaxReporting, TaxForm1099
from lib.etf.shared import ShareholderRecord


class TestTaxReporting:
    """Test Tax Reporting function"""
    
    def test_generate_1099_div(self, mock_adapter, temp_storage):
        """Test 1099-DIV generation"""
        tax = TaxReporting(mock_adapter, temp_storage)
        
        shareholder = ShareholderRecord(
            account_number="ACC001",
            account_type="beneficial",
            shareholder_name="Test Shareholder",
            tax_id="12-3456789",
            shares=Decimal('10000')
        )
        
        distributions = {
            "ordinary_dividends": Decimal('500'),
            "qualified_dividends": Decimal('400'),
            "capital_gains": Decimal('200'),
            "return_of_capital": Decimal('100')
        }
        
        form = tax.generate_1099_div(2024, shareholder, distributions)
        
        assert form is not None
        assert isinstance(form, TaxForm1099)
        assert form.form_type == "1099-DIV"
        assert form.tax_year == 2024
        assert form.shareholder_account == "ACC001"
        assert form.dividends == Decimal('500')
    
    def test_generate_1099_b(self, mock_adapter, temp_storage):
        """Test 1099-B generation"""
        tax = TaxReporting(mock_adapter, temp_storage)
        
        shareholder = ShareholderRecord(
            account_number="ACC001",
            account_type="beneficial",
            shareholder_name="Test Shareholder",
            tax_id="12-3456789",
            shares=Decimal('10000')
        )
        
        transactions = [
            {
                "date": date(2024, 6, 15),
                "proceeds": Decimal('10000'),
                "cost_basis": Decimal('8000'),
                "wash_sale": False
            },
            {
                "date": date(2024, 9, 20),
                "proceeds": Decimal('5000'),
                "cost_basis": Decimal('4000'),
                "wash_sale": False
            }
        ]
        
        form = tax.generate_1099_b(2024, shareholder, transactions)
        
        assert form is not None
        assert isinstance(form, TaxForm1099)
        assert form.form_type == "1099-B"
        assert form.tax_year == 2024
        assert form.proceeds == Decimal('15000')
        assert form.cost_basis == Decimal('12000')
    
    def test_generate_all_1099_forms(self, mock_adapter, temp_storage):
        """Test generating all 1099 forms"""
        tax = TaxReporting(mock_adapter, temp_storage)
        
        shareholders = [
            ShareholderRecord(
                account_number="ACC001",
                account_type="beneficial",
                shareholder_name="Test Shareholder 1",
                tax_id="12-3456789",
                shares=Decimal('10000')
            ),
            ShareholderRecord(
                account_number="ACC002",
                account_type="beneficial",
                shareholder_name="Test Shareholder 2",
                tax_id="98-7654321",
                shares=Decimal('5000')
            )
        ]
        
        forms = tax.generate_all_1099_forms(2024, shareholders)
        
        assert forms is not None
        assert isinstance(forms, list)
        # Should generate forms for shareholders with distributions/transactions
    
    def test_file_1099_forms_with_irs(self, mock_adapter, temp_storage):
        """Test filing 1099 forms with IRS"""
        tax = TaxReporting(mock_adapter, temp_storage)
        
        # Add some forms
        tax.forms = [
            TaxForm1099(
                form_type="1099-DIV",
                tax_year=2024,
                shareholder_account="ACC001",
                shareholder_name="Test Shareholder",
                tax_id="12-3456789",
                distributions=Decimal('500'),
                dividends=Decimal('500'),
                capital_gains=Decimal('0'),
                return_of_capital=Decimal('0'),
                interest=Decimal('0'),
                proceeds=Decimal('0'),
                cost_basis=Decimal('0')
            )
        ]
        
        result = tax.file_1099_forms_with_irs(2024)
        
        assert result is not None
        assert result["tax_year"] == 2024
        assert result["forms_filed"] > 0
        assert result["status"] == "filed"
    
    def test_generate_tax_return_form_1120_ric(self, mock_adapter, temp_storage):
        """Test Form 1120-RIC generation"""
        from lib.etf.functions.tax_lot import TaxLotManager
        
        tax = TaxReporting(mock_adapter, temp_storage)
        taxlot_manager = TaxLotManager(storage_path=str(temp_storage))
        
        # Set up ledger data
        ledger_data = {
            'Dividend Income': -Decimal('100000'),  # Credit balance
        }
        
        distributions = [
            {"distribution_type": "dividend", "total_amount": "95000"}
        ]
        
        form_1120_ric = tax.generate_tax_return_form_1120_ric(
            tax_year=2024,
            ledger_data=ledger_data,
            taxlot_manager=taxlot_manager,
            distributions=distributions
        )
        
        assert form_1120_ric is not None
        assert form_1120_ric["form_type"] == "1120-RIC"
        assert form_1120_ric["tax_year"] == 2024
        assert 'investment_company_taxable_income' in form_1120_ric
        assert 'corporate_tax_due' in form_1120_ric

