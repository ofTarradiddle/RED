# ETF System Testing Roadmap

## ✅ Already Tested

### 1. NAV Calculation (Complete)
- **Status**: ✅ Fully tested with ITAN exact holdings
- **Result**: 0.00% difference between expected and calculated NAV
- **Files**: `test_itan_exact_holdings.py`, `test_nav_with_real_holdings.py`

---

## 🧪 Ready to Test (What We Need)

### 2. **Accounting & General Ledger**
**What it does**: Double-entry bookkeeping, journal entries, financial statements

**What we need**:
- [ ] **Trades/Transactions** (CSV or JSON):
  - Date, Security (CUSIP/Ticker), Quantity, Price, Buy/Sell
  - Example: `2025-01-15, AMZN, 023135106, 100, 150.00, BUY`
- [ ] **Expenses** (optional):
  - Management fees, audit fees, legal fees, etc.
  - Date, Description, Amount, Account
- [ ] **Income** (optional):
  - Dividends received, interest income
  - Date, Security, Amount

**What we can test**:
- ✅ Journal entry creation and balancing
- ✅ General ledger updates
- ✅ Trial balance generation
- ✅ Balance sheet generation
- ✅ Income statement generation
- ✅ NAV entry recording

**Test file**: `test_accounting_integration.py` (to be created)

---

### 3. **Tax Lot Tracking**
**What it does**: Tracks cost basis, realized/unrealized gains, holding periods

**What we need**:
- [ ] **Purchase Transactions**:
  - Date, Security (CUSIP), Quantity, Price, Trade ID
- [ ] **Sale Transactions**:
  - Date, Security (CUSIP), Quantity, Price, Trade ID
  - Method: FIFO or LIFO

**What we can test**:
- ✅ Tax lot creation on purchases
- ✅ Realized gain/loss calculation on sales
- ✅ Unrealized gain/loss for open positions
- ✅ Short-term vs long-term classification
- ✅ Holding period tracking

**Test file**: `test_tax_lot_integration.py` (to be created)

---

### 4. **Performance Calculation**
**What it does**: Calculates pre-tax and after-tax total returns vs benchmark

**What we need**:
- [ ] **NAV History** (CSV):
  - Date, NAV per share
  - Can generate from daily NAV calculations
- [ ] **Distribution History** (CSV):
  - Date, Distribution Type (Dividend/Capital Gain), Amount per Share
- [ ] **Benchmark Ticker** (optional):
  - e.g., "SPY" for S&P 500 comparison

**What we can test**:
- ✅ Pre-tax total return calculation
- ✅ After-tax total return (with tax rates)
- ✅ Benchmark comparison
- ✅ Cumulative performance over time
- ✅ Annualized returns

**Test file**: `test_performance_integration.py` (to be created)

---

### 5. **Tax Reporting (Form 1120-RIC)**
**What it does**: Generates federal income tax return for RIC

**What we need**:
- [ ] **Full Year's Data**:
  - All trades (purchases/sales) for the tax year
  - All distributions paid
  - All income received (dividends, interest)
  - Expense data
- [ ] **Tax Year**: e.g., 2024

**What we can test**:
- ✅ Form 1120-RIC generation
- ✅ Form 8613 (Excise Tax) calculation
- ✅ Taxable income calculation
- ✅ Dividend paid deduction
- ✅ Capital gain distributions

**Test file**: `test_tax_reporting_integration.py` (to be created)

---

### 6. **Distributions**
**What it does**: Calculates and processes income distributions

**What we need**:
- [ ] **Income Data**:
  - Dividends received by date
  - Interest income by date
  - Total income for distribution period
- [ ] **Distribution Schedule**:
  - Distribution dates (e.g., quarterly)
  - Payout ratio (e.g., 100% of income)

**What we can test**:
- ✅ Distribution calculation (amount per share)
- ✅ Distribution declaration
- ✅ Distribution payment processing
- ✅ Distribution schedule generation
- ✅ Excise tax calculation (if applicable)

**Test file**: `test_distributor_integration.py` (to be created)

---

### 7. **Compliance (SEC Filings)**
**What it does**: Generates N-PORT, N-CEN, N-CSR reports

**What we need**:
- [ ] **Portfolio Holdings** (already have from ITAN)
- [ ] **Fund Information**:
  - Fund name, CIK, CUSIP
  - Fiscal year end
  - Share classes
- [ ] **Performance Data** (optional):
  - Returns, expenses, etc.

**What we can test**:
- ✅ N-PORT generation (monthly holdings)
- ✅ N-CEN generation (annual census)
- ✅ N-CSR generation (shareholder report)
- ✅ Form validation

**Test file**: `test_compliance_integration.py` (to be created)

---

### 8. **Transfer Agent (Reconciliation)**
**What it does**: Reconciles TA records vs Custodian vs DTC

**What we need**:
- [ ] **Custodian Statement**:
  - Shares outstanding
  - Cash balance
  - Holdings
- [ ] **DTC Statement**:
  - DTC position
  - Shareholder positions
- [ ] **TA Records**:
  - Shareholder registry
  - Creation/redemption orders

**What we can test**:
- ✅ Daily reconciliation (TA vs Custodian vs DTC)
- ✅ Cede & Co. file updates
- ✅ Shareholder registry management
- ✅ Creation/redemption order processing

**Test file**: `test_transfer_agent_integration.py` (to be created)

---

### 9. **Order Management (PCF & Baskets)**
**What it does**: Generates PCF files and processes AP orders

**What we need**:
- [ ] **Portfolio Holdings** (already have)
- [ ] **AP Orders** (optional):
  - Order ID, AP name, Order type (Create/Redeem), Quantity, Date
- [ ] **Basket Policy**:
  - Standard vs custom basket rules

**What we can test**:
- ✅ PCF file generation
- ✅ Standard basket construction
- ✅ Custom basket construction
- ✅ AP order validation
- ✅ Order fee calculation

**Test file**: `test_order_management_integration.py` (to be created)

---

### 10. **Full Daily Workflow (Orchestrator)**
**What it does**: Runs complete daily operations end-to-end

**What we need**:
- [ ] **All of the above** (or subset for testing)
- [ ] **Configuration File** (`config.yaml`):
  - Fund settings
  - Holdings
  - Scheduled trades
  - Distribution dates

**What we can test**:
- ✅ Complete daily workflow:
  1. NAV calculation
  2. Accounting operations
  3. Tax lot updates
  4. Performance calculation
  5. Distribution processing
- ✅ Year-end reporting:
  1. Tax reporting
  2. Performance reporting
  3. Regulatory filings

**Test file**: `test_orchestrator_integration.py` (to be created)

---

## 📋 Quick Start: What to Provide

### Minimum for Full Testing:
1. **Holdings** ✅ (Already have from ITAN)
2. **Trades/Transactions** (CSV or JSON) - Need this next
3. **NAV History** (can generate from daily NAV)
4. **Distributions** (CSV) - Optional, can use dummy data

### Format Examples:

**Trades CSV**:
```csv
Date,Security,Type,Quantity,Price
2025-01-15,AMZN,BUY,100,150.00
2025-02-20,AMZN,SELL,50,155.00
2025-03-10,GOOGL,BUY,200,120.00
```

**Distributions CSV**:
```csv
Date,Type,AmountPerShare
2025-03-31,DIVIDEND,0.25
2025-06-30,DIVIDEND,0.30
2025-09-30,DIVIDEND,0.28
2025-12-31,DIVIDEND,0.32
```

---

## 🎯 Recommended Testing Order

1. **Accounting** (needs trades) - Most fundamental
2. **Tax Lot Tracking** (needs trades) - Builds on accounting
3. **Performance** (needs NAV history + distributions) - Uses accounting data
4. **Distributions** (needs income data) - Can use dummy data
5. **Tax Reporting** (needs full year) - Uses all above
6. **Compliance** (needs holdings) - Can test now
7. **Order Management** (needs holdings) - Can test now
8. **Transfer Agent** (needs custodian data) - Most complex
9. **Orchestrator** (needs everything) - Full integration test

---

## 💡 What Can We Test RIGHT NOW (No Additional Data)?

1. ✅ **NAV Calculation** - Already done
2. ✅ **PCF Generation** - Can test with ITAN holdings
3. ✅ **Basket Construction** - Can test with ITAN holdings
4. ✅ **Compliance Forms** - Can generate N-PORT/N-CEN with ITAN holdings
5. ✅ **Security Master File** - Can test with ITAN holdings

Let me know which one you'd like to test next!

