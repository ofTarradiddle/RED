# Data Source Implementation TODOs

**CRITICAL: Complete these before going to production**

## Priority 1: Core Daily Operations

### 1. NSCC Files (`get_nscc_files`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** CRITICAL  
**Required for:** TA daily reconciliation, order processing

**Tasks:**
- [ ] Obtain NSCC Participant Terminal System (PTS) credentials
- [ ] Set up NSCC file transfer (SFTP/FTP) or API connection
- [ ] Download daily settlement files (typically end-of-day, ~4-5 PM ET)
- [ ] Parse NSCC file formats (fixed-width or CSV)
- [ ] Extract: settled_shares, creation_orders, redemption_orders, settlement_confirmations
- [ ] Handle file naming conventions and date formats
- [ ] Implement error handling for missing/late files
- [ ] Set up retry logic for failed downloads
- [ ] Test with sample NSCC files
- [ ] Verify data accuracy against manual checks

**Expected Return Format:**
```python
{
    "settled_shares": Decimal("1000000"),
    "creation_orders": [
        {"order_id": "...", "ap_id": "...", "units": 10, "status": "settled"}
    ],
    "redemption_orders": [...],
    "settlement_confirmations": [...]
}
```

### 2. DTC Position File (`get_dtc_position_file`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** CRITICAL  
**Required for:** TA daily reconciliation, Cede file updates

**Tasks:**
- [ ] Obtain DTC Participant Terminal System (PTS) credentials
- [ ] Set up DTC file transfer (SFTP/FTP) or API connection
- [ ] Download daily position files (typically end-of-day, ~4-5 PM ET)
- [ ] Parse DTC position file format
- [ ] Extract: cede_position, participant_positions, street_name_shares
- [ ] Handle Cede & Co. position reconciliation
- [ ] Implement error handling for missing/late files
- [ ] Test with sample DTC files
- [ ] Verify Cede position matches TA records

**Expected Return Format:**
```python
{
    "cede_position": Decimal("5000000"),  # Cede & Co. share position
    "participant_positions": [
        {"participant_id": "...", "shares": Decimal("...")}
    ],
    "street_name_shares": Decimal("5000000")
}
```

### 3. Custodian Statements (`get_custodian_statements`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** CRITICAL  
**Required for:** NAV calculation, reconciliation, holdings verification

**Tasks:**
- [ ] Obtain custodian API credentials (State Street, BNY Mellon, etc.)
- [ ] Set up API connection or file transfer
- [ ] Download daily custodian statements (typically end-of-day)
- [ ] Parse statement format (varies by custodian)
- [ ] Extract: total_shares, shares_outstanding, cash_balance, holdings, transactions
- [ ] Handle multiple account structures if applicable
- [ ] Implement reconciliation with internal records
- [ ] Test with sample custodian statements
- [ ] Verify data accuracy

**Expected Return Format:**
```python
{
    "total_shares": Decimal("10000000"),
    "shares_outstanding": Decimal("10000000"),
    "cash_balance": Decimal("50000"),
    "portfolio_cash": Decimal("50000"),
    "holdings": [
        {"cusip": "...", "quantity": Decimal("..."), "description": "..."}
    ],
    "transactions": [...]
}
```

### 4. Portfolio Holdings (`get_portfolio_holdings`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** CRITICAL  
**Required for:** NAV calculation, PCF generation

**Tasks:**
- [ ] Connect to portfolio management system (if separate from custodian)
- [ ] Or use custodian holdings data
- [ ] Get holdings as of specific date
- [ ] Extract: cusip, ticker, description, quantity, previous_price
- [ ] Handle corporate actions adjustments
- [ ] Ensure data is as-of-date accurate
- [ ] Test with sample holdings data
- [ ] Verify against custodian records

**Expected Return Format:**
```python
[
    {
        "cusip": "037833100",
        "ticker": "AAPL",
        "description": "APPLE INC",
        "quantity": Decimal("1000"),
        "previous_price": Decimal("150.00")
    },
    ...
]
```

### 5. Market Prices (`get_market_prices`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** CRITICAL  
**Required for:** NAV calculation, price validation

**Tasks:**
- [ ] Obtain market data provider API credentials (Bloomberg, Refinitiv, etc.)
- [ ] Set up API connection
- [ ] Request prices for CUSIPs on specific date
- [ ] Handle multiple price sources (last sale, bid/ask, closing price)
- [ ] Implement fallback pricing logic
- [ ] Handle missing prices (corporate actions, delisted securities)
- [ ] Cache prices to reduce API calls
- [ ] Test with sample CUSIPs
- [ ] Verify price accuracy

**Expected Return Format:**
```python
{
    "037833100": Decimal("150.25"),
    "594918104": Decimal("350.50"),
    ...
}
```

## Priority 2: Supporting Operations

### 6. Corporate Actions (`get_corporate_actions`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** HIGH  
**Required for:** NAV calculation, PCF updates, portfolio adjustments

**Tasks:**
- [ ] Connect to DTCC Corporate Actions API or custodian feed
- [ ] Get corporate actions affecting portfolio holdings
- [ ] Extract: cusip, action_type, ex_date, pay_date, amount, split_ratio, etc.
- [ ] Filter for actions affecting portfolio
- [ ] Handle different action types (dividends, splits, mergers, etc.)
- [ ] Test with sample corporate actions
- [ ] Verify action processing

**Expected Return Format:**
```python
[
    {
        "cusip": "037833100",
        "action_type": "dividend",
        "ex_date": "2024-01-15",
        "pay_date": "2024-01-20",
        "amount": Decimal("0.24")
    },
    ...
]
```

### 7. Expense Data (`get_expense_data`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** HIGH  
**Required for:** NAV calculation, accounting entries

**Tasks:**
- [ ] Connect to expense tracking system or accounting system
- [ ] Get daily expense accruals
- [ ] Extract: accrued_expenses, accrued_income, payables, management_fee, other_expenses
- [ ] Calculate daily accruals for annual expenses
- [ ] Handle one-time vs recurring expenses
- [ ] Test with sample expense data
- [ ] Verify accrual calculations

**Expected Return Format:**
```python
{
    "accrued_expenses": Decimal("1000"),
    "accrued_income": Decimal("500"),
    "payables": Decimal("2000"),
    "management_fee": Decimal("500"),
    "admin_expenses": Decimal("200"),
    "custodial_fee": Decimal("100"),
    "other_expenses": Decimal("200"),
    "total_expenses": Decimal("1000")
}
```

### 8. AP Orders (`get_ap_orders`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** HIGH  
**Required for:** Order processing, creation/redemption handling

**Tasks:**
- [ ] Set up AP order portal/API
- [ ] Or connect to NSCC order system
- [ ] Get pending creation/redemption orders for date
- [ ] Extract: order_id, ap_id, order_type, creation_units, basket, order_date
- [ ] Handle order status updates
- [ ] Implement real-time order monitoring if needed
- [ ] Test with sample orders
- [ ] Verify order processing

**Expected Return Format:**
```python
[
    APOrder(
        order_id="ORD001",
        ap_id="AP001",
        order_type="creation",
        creation_units=10,
        order_date=date.today(),
        status="pending"
    ),
    ...
]
```

## Priority 3: Additional Operations

### 9. Accounting Data (`get_accounting_data`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Required for:** Accounting journal entries

**Tasks:**
- [ ] Connect to accounting system or expense tracking
- [ ] Get daily accounting data
- [ ] Extract: expenses (management_fee, admin_expenses, custodial_fee, other_expenses)
- [ ] Extract: income (dividend_income, interest_income)
- [ ] Format for accounting entry creation
- [ ] Test with sample accounting data

**Expected Return Format:**
```python
{
    "expenses": {
        "management_fee": Decimal("500"),
        "admin_expenses": Decimal("200"),
        "custodial_fee": Decimal("100"),
        "other_expenses": Decimal("200")
    },
    "income": {
        "dividend_income": Decimal("1000"),
        "interest_income": Decimal("50")
    }
}
```

### 10. Distribution Data (`get_distribution_data`)
**Status:** ⚠️ NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Required for:** Distribution calculations

**Tasks:**
- [ ] Connect to distribution calculation system
- [ ] Get distribution amounts per share
- [ ] Extract: dividend_per_share, capital_gains_per_share, roc_per_share
- [ ] Handle different distribution types
- [ ] Get distribution dates (record, ex, pay)
- [ ] Test with sample distribution data

**Expected Return Format:**
```python
{
    "dividend_per_share": Decimal("0.10"),
    "capital_gains_per_share": Decimal("0.05"),
    "roc_per_share": Decimal("0.00"),
    "record_date": "2024-01-15",
    "ex_date": "2024-01-15",
    "pay_date": "2024-01-20"
}
```

## Testing Checklist

Before going to production, test each data source:

- [ ] Test each data source connection individually
- [ ] Verify data format matches expected structure
- [ ] Test error handling for missing data
- [ ] Test date range queries
- [ ] Verify data accuracy against manual checks
- [ ] Set up monitoring/alerts for data source failures
- [ ] Document data source credentials and connection details securely
- [ ] Test with production-like data volumes
- [ ] Verify performance (response times)
- [ ] Test retry logic for failures
- [ ] Set up backup data sources if available

## Production Readiness

- [ ] All Priority 1 data sources implemented
- [ ] All Priority 2 data sources implemented
- [ ] Error handling implemented for all sources
- [ ] Logging implemented for all sources
- [ ] Monitoring/alerts configured
- [ ] Credentials securely stored (environment variables, secrets manager)
- [ ] Documentation complete
- [ ] Tested with real data
- [ ] Performance acceptable
- [ ] Backup procedures in place

