# Self-Service Functions Overview

Production-ready implementations for all ETF operational functions.

## Functions

### 1. Accounting (`lib/accounting.py`)
**Purpose**: Complete accounting system with double-entry bookkeeping

**Features:**
- General ledger management
- Journal entry processing
- Trial balance generation
- Balance sheet generation
- Income statement generation
- NAV entry recording
- Expense accrual recording
- Income recognition

**Key Methods:**
- `create_journal_entry()` - Create double-entry journal entries
- `record_nav_entries()` - Record NAV calculations
- `record_expense_accrual()` - Record expense accruals
- `record_income()` - Record income
- `generate_trial_balance()` - Generate trial balance
- `generate_balance_sheet()` - Generate balance sheet
- `generate_income_statement()` - Generate income statement
- `daily_accounting_operations()` - Run daily accounting

### 2. Administration (`lib/administration.py`)
**Purpose**: Fund administration including NAV calculation and reporting

**Features:**
- Daily NAV calculation
- Price validation with tolerance checks
- Holdings and cash reconciliation
- Corporate actions processing
- Expense ratio calculation

**Key Methods:**
- `calculate_nav()` - Calculate daily NAV per share
- `reconcile_holdings_cash()` - Reconcile with custodian
- `process_corporate_actions()` - Process corporate actions
- `calculate_expense_ratio()` - Calculate expense ratio

### 3. Transfer Agent (`lib/transfer_agent.py`)
**Purpose**: Shareholder recordkeeping and reconciliation (Non-Paying Agent)

**Features:**
- Shareholder registry management
- Daily reconciliation (TA vs Custodian vs DTC)
- Cede & Co. file updates
- Creation/redemption order processing
- AML screening framework

**Key Methods:**
- `daily_reconciliation()` - Reconcile TA vs Custodian vs DTC
- `update_cede_file()` - Update Cede & Co. position
- `process_creation_redemption_orders()` - Process orders
- `aml_screening()` - Perform AML screening

### 4. Order Management (`lib/order_management.py`)
**Purpose**: Creation/redemption order processing and PCF publication

**Features:**
- PCF (Portfolio Composition File) generation
- AP order validation
- Basket construction and validation
- NSCC-compliant formatting

**Key Methods:**
- `generate_pcf()` - Generate PCF for NSCC
- `validate_ap_order()` - Validate AP orders
- `process_ap_order()` - Process AP orders

### 5. Distributor (`lib/distributor.py`)
**Purpose**: Distribution calculation and payment processing

**Features:**
- Distribution calculation (dividends, capital gains, ROC)
- Distribution declaration
- Payment processing
- Distribution schedule generation

**Key Methods:**
- `calculate_distribution()` - Calculate distribution amounts
- `declare_distribution()` - Declare distribution
- `process_distribution_payment()` - Process payments
- `generate_distribution_schedule()` - Generate schedule

## Shared Components

### Data Structures (`lib/shared.py`)
- `ShareholderRecord` - Shareholder account record
- `ReconciliationResult` - Reconciliation result
- `NAVCalculation` - NAV calculation result
- `PCFFile` - Portfolio Composition File
- `APOrder` - Authorized Participant Order
- `DataSourceAdapter` - Abstract data source interface

### Data Adapter (`lib/data_adapter_example.py`)
Template for implementing your data source connections:
- `ExampleDataSourceAdapter` - Template with TODO comments
- `FileBasedDataSourceAdapter` - File-based adapter for testing

## Tasks

### Daily Operations (`tasks/daily_operations.py`)
Runs all daily operations:
1. Calculate NAV
2. Reconcile holdings/cash
3. TA reconciliation
4. Update Cede file
5. Process creation/redemption orders
6. Generate PCF
7. Process AP orders
8. Accounting operations
9. Check distributions

### Weekly Operations (`tasks/weekly_operations.py`)
Runs weekly reporting:
- Trial balance
- Expense ratio calculation
- Weekly reconciliation reports

### Monthly Operations (`tasks/monthly_operations.py`)
Runs monthly reporting:
- Balance sheet
- Income statement
- Distribution schedule

## Usage

### Basic Usage

```python
from lib.accounting import Accounting
from lib.administration import FundAdministration
from lib.transfer_agent import TransferAgent
from lib.order_management import OrderManagement
from lib.distributor import Distributor
from lib.data_adapter_example import FileBasedDataSourceAdapter
from datetime import date

# Create data adapter
adapter = FileBasedDataSourceAdapter(data_path="./data")

# Initialize functions
accounting = Accounting(adapter)
admin = FundAdministration(adapter)
ta = TransferAgent(adapter)
om = OrderManagement(adapter)
distributor = Distributor(adapter)

# Run operations
today = date.today()
nav = admin.calculate_nav(today)
recon = ta.daily_reconciliation(today)
pcf = om.generate_pcf(today)
```

### Running Tasks

```bash
# Daily operations
python tasks/daily_operations.py

# Weekly operations
python tasks/weekly_operations.py

# Monthly operations
python tasks/monthly_operations.py
```

## Data Storage

All functions store data in JSON files:
- `./data/accounting/` - Accounting data
- `./data/admin/` - Administration data
- `./data/ta/` - Transfer Agent data
- `./data/om/` - Order Management data
- `./data/distributor/` - Distributor data

## Production Deployment

1. **Implement Data Adapter**: Connect to your actual data sources
2. **Configure Storage**: Use database instead of files if needed
3. **Schedule Tasks**: Set up cron jobs or task scheduler
4. **Monitor**: Set up monitoring for exceptions
5. **Backup**: Implement backup strategy for data

## Key Features

- ✅ **Production Ready**: Full business logic, error handling, logging
- ✅ **No Shortcuts**: All operations fully implemented
- ✅ **DIY Cost**: Near $0 - just your infrastructure
- ✅ **Extensible**: Easy to customize and extend
- ✅ **Well Documented**: Clear interfaces and examples

