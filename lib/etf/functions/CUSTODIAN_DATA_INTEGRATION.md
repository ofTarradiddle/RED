# Custodian Data Integration Guide

## Overview

Custodian data is retrieved through the **DataSourceAdapter** pattern. All ETF functions use the `DataSourceAdapter` interface to fetch data from external sources, including custodian statements from US Bank.

---

## How Custodian Data is Retrieved

### Architecture

```
ETF Functions → DataSourceAdapter.get_custodian_statements() → US Bank → Data Returned
```

### Data Flow

1. **ETF Function Calls Adapter**: Functions like `FundAdministration.calculate_nav()` call `data_adapter.get_custodian_statements(date)`
2. **Adapter Connects to Custodian**: The adapter implementation connects to US Bank via API or SFTP
3. **Data Retrieved**: Custodian statements are downloaded/retrieved
4. **Data Parsed**: Statements are parsed into structured format
5. **Data Returned**: Structured data is returned to the calling function

---

## Current Implementation Status

### ✅ Interface Defined
- **Location**: `lib/etf/shared/__init__.py` → `DataSourceAdapter.get_custodian_statements()`
- **Status**: Abstract method defined, ready for implementation

### ⚠️ Implementation Needed
- **Location**: `lib/etf/adapters/__init__.py` → `ExampleDataSourceAdapter.get_custodian_statements()`
- **Status**: Placeholder with TODO comments
- **Current**: Returns empty/default data for testing

---

## What Data is Retrieved

### Custodian Statements Include:

1. **Share Balances**:
   - Total shares outstanding
   - Shares outstanding (same as total shares)
   - Used for: NAV calculation, reconciliation

2. **Cash Positions**:
   - Cash balance
   - Portfolio cash
   - Used for: NAV calculation, cash reconciliation

3. **Holdings Positions**:
   - List of all securities held
   - Each holding includes:
     - CUSIP
     - Ticker
     - Description
     - Quantity
     - Market value
   - Used for: NAV calculation, holdings reconciliation

4. **Transaction History**:
   - Trades executed
   - Corporate actions
   - Income received
   - Used for: Accounting entries, reconciliation

---

## Implementation Guide

### Step 1: Choose Connection Method

US Bank typically provides **two methods** for data retrieval:

#### Option A: API (REST/SOAP)
- **Pros**: Real-time, programmatic access
- **Cons**: Requires API credentials, may have rate limits
- **Best for**: Real-time operations, automated workflows

#### Option B: SFTP (File Transfer)
- **Pros**: Reliable, batch processing, standard format
- **Cons**: Requires SFTP setup, file parsing needed
- **Best for**: Daily batch operations, large data volumes

### Step 2: Implement `get_custodian_statements()`

**Location**: Create a new adapter class or modify `ExampleDataSourceAdapter` in `lib/etf/adapters/__init__.py`

**Example Implementation (API)**:
```python
def get_custodian_statements(self, date: date) -> Dict[str, Any]:
    """
    Get custodian statements from US Bank via API
    """
    from decimal import Decimal
    import requests
    from datetime import date
    
    # 1. Connect to US Bank API
    api_url = self.config.get('us_bank_api_url')
    api_key = self.config.get('us_bank_api_key')
    account_id = self.config.get('us_bank_account_id')
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # 2. Request daily statement
    params = {
        'account_id': account_id,
        'statement_date': date.isoformat(),
        'include_holdings': True,
        'include_transactions': True
    }
    
    response = requests.get(
        f'{api_url}/v1/statements/daily',
        headers=headers,
        params=params
    )
    response.raise_for_status()
    statement = response.json()
    
    # 3. Parse and return structured data
    return {
        "total_shares": Decimal(str(statement['shares_outstanding'])),
        "shares_outstanding": Decimal(str(statement['shares_outstanding'])),
        "cash_balance": Decimal(str(statement['cash_balance'])),
        "portfolio_cash": Decimal(str(statement['cash_balance'])),
        "holdings": [
            {
                "cusip": h['cusip'],
                "ticker": h.get('ticker', ''),
                "description": h.get('description', ''),
                "quantity": Decimal(str(h['quantity'])),
                "market_value": Decimal(str(h.get('market_value', 0)))
            }
            for h in statement.get('holdings', [])
        ],
        "transactions": statement.get('transactions', [])
    }
```

**Example Implementation (SFTP)**:
```python
def get_custodian_statements(self, date: date) -> Dict[str, Any]:
    """
    Get custodian statements from US Bank via SFTP
    """
    from decimal import Decimal
    import paramiko
    import csv
    from datetime import date
    
    # 1. Connect to US Bank SFTP
    sftp_host = self.config.get('us_bank_sftp_host')
    sftp_user = self.config.get('us_bank_sftp_user')
    sftp_key = self.config.get('us_bank_sftp_key_path')
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(sftp_host, username=sftp_user, key_filename=sftp_key)
    sftp = ssh.open_sftp()
    
    # 2. Download daily statement file
    # US Bank typically uses naming convention: STATEMENT_YYYYMMDD.csv
    filename = f'STATEMENT_{date.strftime("%Y%m%d")}.csv'
    remote_path = f'/statements/{filename}'
    local_path = f'/tmp/{filename}'
    
    sftp.get(remote_path, local_path)
    sftp.close()
    ssh.close()
    
    # 3. Parse CSV file
    holdings = []
    with open(local_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['record_type'] == 'HOLDING':
                holdings.append({
                    "cusip": row['cusip'],
                    "ticker": row.get('ticker', ''),
                    "description": row.get('description', ''),
                    "quantity": Decimal(str(row['quantity'])),
                    "market_value": Decimal(str(row.get('market_value', 0)))
                })
    
    # 4. Extract summary data (from header or summary row)
    # This depends on US Bank's file format
    # Example: Read from summary section or calculate from holdings
    
    return {
        "total_shares": Decimal('0'),  # From summary section
        "shares_outstanding": Decimal('0'),  # From summary section
        "cash_balance": Decimal('0'),  # From summary section
        "portfolio_cash": Decimal('0'),  # From summary section
        "holdings": holdings,
        "transactions": []  # Parse from transactions section
    }
```

---

## US Bank Specific Details

### Connection Information

**Contact**: Your US Bank Global Fund Services relationship manager

**Typical Interfaces**:
- **API**: REST API (JSON)
- **SFTP**: Secure file transfer
- **Email**: For certain reports (less common)

### Data Format

US Bank typically provides:
- **Holdings File**: CSV or Excel format
- **Cash Statement**: Separate file or included in holdings file
- **Transaction File**: CSV format with trade details

### Timing

- **Available**: Typically by 5:00 PM ET daily
- **Format**: End-of-day positions as of market close
- **Frequency**: Daily (business days only)

### Required Credentials

1. **API Method**:
   - API URL
   - API Key or OAuth credentials
   - Account ID
   - Fund ID (if multiple funds)

2. **SFTP Method**:
   - SFTP hostname
   - Username
   - SSH private key or password
   - Directory path for statements

---

## Where Custodian Data is Used

### 1. NAV Calculation (`core/administration.py`)
```python
custodian_data = self.data_adapter.get_custodian_statements(nav_date)
cash = Decimal(str(custodian_data.get('cash_balance', 0)))
shares_outstanding = Decimal(str(custodian_data.get('shares_outstanding', 0)))
```

### 2. Holdings Reconciliation (`core/administration.py`)
```python
custodian_data = self.data_adapter.get_custodian_statements(rec_date)
custodian_holdings = custodian_data.get('holdings', [])
# Compare with portfolio holdings
```

### 3. Transfer Agent Reconciliation (`operations/transfer_agent.py`)
```python
custodian_data = self.data_adapter.get_custodian_statements(rec_date)
custodian_shares = Decimal(str(custodian_data.get('total_shares', 0)))
# Reconcile with TA records
```

### 4. Order Management (`operations/order_management.py`)
```python
custodian_data = self.data_adapter.get_custodian_statements(pcf_date)
cash_balance = Decimal(str(custodian_data.get('cash_balance', 0)))
# Used for PCF cash component calculation
```

---

## Testing

### Test with Mock Data

Before connecting to real US Bank, test with mock data:

```python
class MockUSBankAdapter(DataSourceAdapter):
    def get_custodian_statements(self, date: date) -> Dict[str, Any]:
        # Return test data matching US Bank format
        return {
            "total_shares": Decimal('1000000'),
            "shares_outstanding": Decimal('1000000'),
            "cash_balance": Decimal('50000'),
            "portfolio_cash": Decimal('50000'),
            "holdings": [
                {
                    "cusip": "037833100",  # AAPL
                    "ticker": "AAPL",
                    "description": "Apple Inc",
                    "quantity": Decimal('1000'),
                    "market_value": Decimal('150000')
                }
            ],
            "transactions": []
        }
```

### Test with Real Connection

Once implemented:
1. Test with a single date
2. Verify data format matches expected structure
3. Test error handling (missing files, API errors)
4. Verify reconciliation works correctly

---

## Configuration

Store US Bank credentials securely in configuration:

```yaml
# config.yaml
custodian:
  provider: "us_bank"
  method: "api"  # or "sftp"
  api:
    url: "https://api.usbank.com/v1"
    key: "${US_BANK_API_KEY}"  # Use environment variable
    account_id: "123456"
  sftp:
    host: "sftp.usbank.com"
    user: "fund_account"
    key_path: "/path/to/private/key"
    directory: "/statements"
```

---

## Error Handling

Implement robust error handling:

```python
def get_custodian_statements(self, date: date) -> Dict[str, Any]:
    try:
        # Connect and retrieve data
        statement = self._fetch_from_us_bank(date)
        return self._parse_statement(statement)
    except requests.exceptions.RequestException as e:
        logger.error(f"US Bank API error: {e}")
        # Retry logic or return cached data
        raise
    except FileNotFoundError as e:
        logger.error(f"US Bank SFTP file not found: {e}")
        # Handle missing file
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving custodian data: {e}")
        raise
```

---

## Security Best Practices

1. **Never commit credentials**: Use environment variables or secure vault
2. **Use API keys**: Prefer API keys over passwords
3. **SFTP keys**: Use SSH key-based authentication for SFTP
4. **Encrypt storage**: Encrypt credentials at rest
5. **Access logging**: Log all custodian data access for audit

---

## Next Steps

1. **Contact US Bank**: Get API/SFTP credentials and documentation
2. **Review US Bank documentation**: Understand their specific file formats
3. **Implement adapter**: Create `USBankDataSourceAdapter` class
4. **Test thoroughly**: Test with sample data before production
5. **Deploy**: Replace placeholder adapter with real implementation

---

## Related Documentation

- **DataSourceAdapter Interface**: `lib/etf/shared/__init__.py`
- **Example Implementation**: `lib/etf/adapters/__init__.py`
- **Data Source TODOs**: `tasks/DATA_SOURCE_TODOS.md`
- **Functions README**: `lib/etf/functions/README.md` (External Interfaces section)

