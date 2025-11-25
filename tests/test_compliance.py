"""
Tests for Compliance function
"""

import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.compliance import Compliance, SECFiling


class TestCompliance:
    """Test Compliance function"""
    
    def test_generate_form_n_cen(self, mock_adapter, temp_storage):
        """Test Form N-CEN generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        n_cen = compliance.generate_form_n_cen(2024)
        
        assert n_cen is not None
        assert n_cen["form_type"] == "N-CEN"
        assert n_cen["fiscal_year"] == 2024
        assert n_cen["status"] == "draft"
    
    def test_generate_form_n_csr(self, mock_adapter, temp_storage):
        """Test Form N-CSR generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        n_csr = compliance.generate_form_n_csr(date(2024, 12, 31), is_annual=False)
        
        assert n_csr is not None
        assert n_csr["form_type"] == "N-CSR"
        assert n_csr["period_end"] == date(2024, 12, 31).isoformat()
        assert n_csr["is_annual"] == False
    
    def test_generate_form_n_port(self, mock_adapter, temp_storage):
        """Test Form N-PORT generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        # Set up mock holdings
        mock_adapter.holdings_data = [
            {
                "cusip": "037833100",
                "ticker": "AAPL",
                "description": "APPLE INC",
                "quantity": Decimal('1000')
            }
        ]
        mock_adapter.prices_data = {
            "037833100": Decimal('150.00')
        }
        
        n_port = compliance.generate_form_n_port(date(2024, 12, 31))
        
        assert n_port is not None
        assert n_port["form_type"] == "N-PORT"
        assert n_port["month_end"] == date(2024, 12, 31).isoformat()
        assert "holdings" in n_port["data"]
    
    def test_generate_form_n_mfp(self, mock_adapter, temp_storage):
        """Test Form N-MFP generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        n_mfp = compliance.generate_form_n_mfp(date(2024, 12, 31))
        
        assert n_mfp is not None
        assert n_mfp["form_type"] == "N-MFP"
        assert n_mfp["month_end"] == date(2024, 12, 31).isoformat()
    
    def test_generate_form_n_q(self, mock_adapter, temp_storage):
        """Test Form N-Q generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        # Set up mock holdings
        mock_adapter.holdings_data = [
            {
                "cusip": "037833100",
                "ticker": "AAPL",
                "description": "APPLE INC",
                "quantity": Decimal('1000')
            }
        ]
        
        n_q = compliance.generate_form_n_q(date(2024, 12, 31))
        
        assert n_q is not None
        assert n_q["form_type"] == "N-Q"
        assert n_q["quarter_end"] == date(2024, 12, 31).isoformat()
        assert "holdings" in n_q["data"]
    
    def test_generate_form_8k(self, mock_adapter, temp_storage):
        """Test Form 8-K generation"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        form_8k = compliance.generate_form_8k(
            date(2024, 12, 31),
            "change_in_custodian",
            "Changed custodian from Bank A to Bank B"
        )
        
        assert form_8k is not None
        assert form_8k["form_type"] == "8-K"
        assert form_8k["event_type"] == "change_in_custodian"
        assert form_8k["event_description"] == "Changed custodian from Bank A to Bank B"
    
    def test_file_sec_form(self, mock_adapter, temp_storage):
        """Test SEC form filing"""
        compliance = Compliance(mock_adapter, temp_storage)
        
        form_data = {
            "form_type": "N-PORT",
            "period_end": date(2024, 12, 31).isoformat()
        }
        
        result = compliance.file_sec_form(form_data)
        
        assert result is not None
        assert result["form_type"] == "N-PORT"
        assert result["status"] == "filed"
        assert "accession_number" in result
        assert len(compliance.filings) > 0

