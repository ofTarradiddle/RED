# Test Suite

Comprehensive test suite for ETF self-service functions using pytest.

## Setup

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run with coverage:
```bash
pytest --cov=lib.etf --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_accounting.py
```

### Run specific test:
```bash
pytest tests/test_accounting.py::TestAccounting::test_create_journal_entry
```

### Run with verbose output:
```bash
pytest -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_accounting.py       # Accounting function tests
├── test_administration.py   # Fund Administration tests
├── test_transfer_agent.py   # Transfer Agent tests
├── test_order_management.py # Order Management tests
├── test_distributor.py      # Distributor tests
├── test_compliance.py       # Compliance tests
└── test_tax_reporting.py    # Tax Reporting tests
```

## Test Fixtures

### `mock_adapter`
Mock data adapter that provides controlled test data. Use this for unit tests.

### `file_adapter`
File-based adapter with temporary storage. Use this for integration tests.

### `temp_storage`
Temporary storage directory path. Use this when you need a clean storage location.

### `sample_date`
Sample date (2024-12-31) for testing.

### `sample_holdings`
Sample portfolio holdings with AAPL, MSFT, and GOOGL.

### `sample_prices`
Sample market prices for test securities.

### `sample_custodian_data`
Sample custodian data with holdings and cash balance.

## Writing New Tests

### Example Test Structure:

```python
import pytest
from datetime import date
from decimal import Decimal

from lib.etf.functions.accounting import Accounting

class TestAccounting:
    """Test Accounting function"""
    
    def test_create_journal_entry(self, mock_adapter, temp_storage):
        """Test creating a journal entry"""
        accounting = Accounting(mock_adapter, temp_storage)
        
        entry = accounting.create_journal_entry(
            date=date(2024, 12, 31),
            description="Test entry",
            debits=[{"account": "Cash", "amount": Decimal('1000')}],
            credits=[{"account": "Revenue", "amount": Decimal('1000')}]
        )
        
        assert entry is not None
        assert entry.date == date(2024, 12, 31)
```

## Test Coverage

Current test coverage includes:

- ✅ Accounting function (journal entries, NAV entries, financial statements)
- ✅ Fund Administration (NAV calculation, reconciliation, corporate actions)
- ✅ Transfer Agent (daily reconciliation, Cede file updates, order processing)
- ✅ Order Management (PCF generation, basket building, order validation, fees)
- ✅ Distributor (distribution calculation, declaration, payment)
- ✅ Compliance (SEC form generation)
- ✅ Tax Reporting (1099 form generation)

## Mock Data Adapter

The `MockDataSourceAdapter` in `conftest.py` provides a controlled way to set test data:

```python
def test_my_function(mock_adapter, temp_storage):
    # Set up mock data
    mock_adapter.holdings_data = [
        {"cusip": "037833100", "quantity": Decimal('1000')}
    ]
    mock_adapter.prices_data = {
        "037833100": Decimal('150.00')
    }
    
    # Run test
    result = my_function(mock_adapter)
    
    # Assert results
    assert result is not None
```

## Continuous Integration

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=lib.etf --cov-report=xml
```

## Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_function():
    pass

@pytest.mark.integration
def test_integration_function():
    pass

@pytest.mark.slow
def test_slow_function():
    pass
```

Run tests by marker:
```bash
pytest -m unit          # Run only unit tests
pytest -m "not slow"    # Run all except slow tests
```

## Troubleshooting

### Import Errors
Make sure you're running tests from the project root:
```bash
cd /Users/dbe/etf-web
pytest
```

### Module Not Found
Ensure `lib.etf` is in your Python path. The tests should work from the project root.

### Fixture Errors
Check that `conftest.py` is in the `tests/` directory and properly configured.

