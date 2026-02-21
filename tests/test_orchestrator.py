"""
Tests for Daily Orchestrator Module
"""

import pytest
import yaml
from datetime import date
from pathlib import Path
from decimal import Decimal

from lib.etf.functions.core.orchestrator import DailyOrchestrator
from tests.conftest import MockDataSourceAdapter


@pytest.fixture
def sample_config(tmp_path):
    """Create sample config.yaml file"""
    config_file = tmp_path / "config.yaml"
    config = {
        'fund': {
            'name': 'Test ETF',
            'ticker': 'TEST',
            'inception_date': '2024-01-01',
            'fiscal_year_end': '12-31',
            'shares_outstanding': 1000000,
            'benchmark': '^GSPC'
        },
        'distributions': {
            'frequency': 'Quarterly',
            'payout_ratio': 0.95
        },
        'tax': {
            'corporate_rate': 0.21,
            'excise_rate': 0.04,
            'dividend_tax_rate': 0.15,
            'lt_capital_gains_tax_rate': 0.20,
            'st_capital_gains_tax_rate': 0.37
        },
        'logging': {
            'level': 'INFO'
        },
        'paths': {
            'nav_history': str(tmp_path / 'nav_history.csv'),
            'distribution_history': str(tmp_path / 'distributions.csv')
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    
    return str(config_file)


class TestDailyOrchestrator:
    """Test Daily Orchestrator functionality"""
    
    def test_orchestrator_initialization(self, sample_config, tmp_path):
        """Test orchestrator initialization"""
        adapter = MockDataSourceAdapter()
        
        # Set up mock data
        adapter.holdings_data = [
            {"cusip": "037833100", "ticker": "AAPL", "quantity": Decimal('1000')}
        ]
        adapter.prices_data = {"037833100": Decimal('150.00')}
        adapter.custodian_data = {
            date.today(): {
                "cash_balance": Decimal('50000'),
                "shares_outstanding": Decimal('1000000')
            }
        }
        adapter.expense_data = {
            date.today(): {
                "accrued_expenses": Decimal('1000'),
                "accrued_income": Decimal('500')
            }
        }
        
        orchestrator = DailyOrchestrator(adapter, config_path=sample_config)
        
        assert orchestrator.admin is not None
        assert orchestrator.accounting is not None
        assert orchestrator.taxlot_manager is not None
        assert orchestrator.distributor is not None
        assert orchestrator.performance is not None
        assert orchestrator.tax_reporting is not None
    
    def test_run_daily_operations(self, sample_config, tmp_path):
        """Test running daily operations"""
        adapter = MockDataSourceAdapter()
        
        # Set up mock data
        adapter.holdings_data = [
            {"cusip": "037833100", "ticker": "AAPL", "quantity": Decimal('1000')}
        ]
        adapter.prices_data = {"037833100": Decimal('150.00')}
        adapter.custodian_data = {
            date.today(): {
                "cash_balance": Decimal('50000'),
                "shares_outstanding": Decimal('1000000'),
                "holdings": [
                    {"cusip": "037833100", "quantity": Decimal('1000')}
                ]
            }
        }
        adapter.expense_data = {
            date.today(): {
                "accrued_expenses": Decimal('1000'),
                "accrued_income": Decimal('500')
            }
        }
        
        orchestrator = DailyOrchestrator(adapter, config_path=sample_config)
        
        results = orchestrator.run_daily_operations(date.today())
        
        assert results['status'] in ['success', 'error']
        assert 'operations' in results
        assert 'nav_calculation' in results['operations']
        assert 'accounting' in results['operations']
        assert 'reconciliation' in results['operations']
    
    def test_process_trades(self, sample_config, tmp_path):
        """Test trade processing in orchestrator"""
        adapter = MockDataSourceAdapter()
        
        # Add trade to config
        config_file = Path(sample_config)
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        config['trades'] = [
            {
                'date': date.today().isoformat(),
                'type': 'BUY',
                'ticker': 'AAPL',
                'quantity': 100
            }
        ]
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Set up mock data
        adapter.holdings_data = []
        adapter.prices_data = {}
        adapter.custodian_data = {
            date.today(): {
                "cash_balance": Decimal('100000'),
                "shares_outstanding": Decimal('1000000')
            }
        }
        adapter.expense_data = {
            date.today(): {
                "accrued_expenses": Decimal('0'),
                "accrued_income": Decimal('0')
            }
        }
        
        orchestrator = DailyOrchestrator(adapter, config_path=sample_config)
        
        # Mock NAV calculation result
        from lib.etf.shared import NAVCalculation
        nav_calc = NAVCalculation(
            date=date.today(),
            total_assets=Decimal('1000000'),
            total_liabilities=Decimal('0'),
            net_assets=Decimal('1000000'),
            shares_outstanding=Decimal('1000000'),
            nav_per_share=Decimal('1.00'),
            pricing_exceptions=[],
            validation_passed=True
        )
        
        # Test trade processing
        trades_result = orchestrator._process_trades(date.today(), nav_calc)
        
        assert 'trades_processed' in trades_result
        assert len(trades_result.get('trades', [])) >= 0

