"""
Tests for Performance Calculation Module
"""

import pytest
import pandas as pd
from datetime import date
from pathlib import Path
from decimal import Decimal

from lib.etf.functions.operations.performance import PerformanceCalculator


@pytest.fixture
def sample_nav_history(tmp_path):
    """Create sample NAV history CSV"""
    nav_file = tmp_path / "nav_history.csv"
    data = {
        'date': pd.date_range('2024-01-01', periods=365, freq='D'),
        'nav': [100.0 + i * 0.1 for i in range(365)]
    }
    df = pd.DataFrame(data)
    df.to_csv(nav_file, index=False)
    return str(nav_file)


@pytest.fixture
def sample_dist_history(tmp_path):
    """Create sample distribution history CSV"""
    dist_file = tmp_path / "distributions.csv"
    data = {
        'date': ['2024-03-31', '2024-06-30', '2024-09-30', '2024-12-31'],
        'distribution_per_share': [0.50, 0.50, 0.50, 0.50]
    }
    df = pd.DataFrame(data)
    df.to_csv(dist_file, index=False)
    return str(dist_file)


class TestPerformanceCalculator:
    """Test PerformanceCalculator functionality"""
    
    def test_compute_performance_basic(self, sample_nav_history, tmp_path):
        """Test basic performance calculation"""
        calc = PerformanceCalculator(storage_path=str(tmp_path))
        
        result = calc.compute_performance(
            nav_history_path=sample_nav_history,
            dist_history_path=None,
            benchmark_symbol=None,
            tax_rates={"dividend_tax_rate": 0.15, "lt_capital_gains_tax_rate": 0.20}
        )
        
        assert 'pre_tax_total_return' in result
        assert 'after_tax_total_return' in result
        assert 'start_date' in result
        assert 'end_date' in result
        assert result['pre_tax_total_return'] > 0  # NAV increased
        assert result['after_tax_total_return'] < result['pre_tax_total_return']  # Tax drag
    
    def test_compute_performance_with_distributions(self, sample_nav_history, sample_dist_history, tmp_path):
        """Test performance calculation with distributions"""
        calc = PerformanceCalculator(storage_path=str(tmp_path))
        
        result = calc.compute_performance(
            nav_history_path=sample_nav_history,
            dist_history_path=sample_dist_history,
            benchmark_symbol=None,
            tax_rates={"dividend_tax_rate": 0.15, "lt_capital_gains_tax_rate": 0.20}
        )
        
        assert 'pre_tax_total_return' in result
        assert 'after_tax_total_return' in result
        assert 'tax_drag' in result
        assert 'tax_efficiency_ratio' in result
        assert result['tax_drag'] > 0  # Should have tax drag from distributions
    
    def test_compute_performance_with_benchmark(self, sample_nav_history, tmp_path):
        """Test performance calculation with benchmark (if yfinance available)"""
        calc = PerformanceCalculator(storage_path=str(tmp_path))
        
        result = calc.compute_performance(
            nav_history_path=sample_nav_history,
            dist_history_path=None,
            benchmark_symbol="^GSPC",  # S&P 500
            tax_rates={"dividend_tax_rate": 0.15, "lt_capital_gains_tax_rate": 0.20},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        assert 'benchmark' in result
        # Benchmark data may or may not be available depending on yfinance
        if result['benchmark']:
            assert 'symbol' in result['benchmark']
            assert 'total_return' in result['benchmark']
    
    def test_calculate_annual_returns(self, sample_nav_history, sample_dist_history, tmp_path):
        """Test annual returns calculation"""
        calc = PerformanceCalculator(storage_path=str(tmp_path))
        
        result = calc.calculate_annual_returns(
            nav_history_path=sample_nav_history,
            dist_history_path=sample_dist_history
        )
        
        assert 'annual_returns' in result
        assert 'years' in result
        assert len(result['annual_returns']) > 0
        assert '2024' in result['annual_returns']
    
    def test_performance_output_file(self, sample_nav_history, tmp_path):
        """Test that performance results are saved to file"""
        calc = PerformanceCalculator(storage_path=str(tmp_path))
        output_file = tmp_path / "performance_output.json"
        
        result = calc.compute_performance(
            nav_history_path=sample_nav_history,
            dist_history_path=None,
            benchmark_symbol=None,
            tax_rates={"dividend_tax_rate": 0.15},
            output_path=str(output_file)
        )
        
        assert output_file.exists()
        # Verify file can be read back
        import json
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        assert saved_data['pre_tax_total_return'] == result['pre_tax_total_return']

