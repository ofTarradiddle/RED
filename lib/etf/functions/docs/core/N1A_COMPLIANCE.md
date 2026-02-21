# SEC Form N-1A Compliance

This document outlines how our admin/accounting framework complies with SEC Form N-1A requirements.

## Overview

The `SECReporting` class in `lib/etf/functions/core/sec_reporting.py` implements **all calculations required by Form N-1A** for open-end management investment companies (mutual funds and ETFs).

**Status**: ✅ **100% COMPLETE** - All N-1A requirements and enhancements implemented.

## Implemented Requirements

### Item 13 - Financial Highlights Information

#### Average Net Assets Calculation
**Instruction 4(a)**: Calculate "average net assets" based on the value of the net assets determined no less frequently than the end of each month.

- **Method**: `calculate_average_net_assets(period_start, period_end)`
- **Implementation**: Groups NAV data by month and uses month-end values to calculate average
- **Usage**: Required for expense ratio and net income ratio calculations

#### Portfolio Turnover Rate ✅ **FULLY IMPLEMENTED**
**Instruction 4(d)**: Calculate portfolio turnover rate by dividing the lesser of purchases or sales by the monthly average portfolio value.

- **Method**: `calculate_portfolio_turnover_rate(fiscal_year_start, fiscal_year_end, purchases=None, sales=None)`
- **Formula**: 
  - Monthly average = Sum of portfolio values (beginning of first month, end of each month) / 13
  - Turnover rate = (Lesser of purchases or sales) / Monthly average × 100
- **Transaction Integration**: ✅ **FULLY IMPLEMENTED**
  - Automatically extracts purchases/sales from accounting ledger when `Accounting` instance provided
  - Uses `_get_transaction_totals()` to read from account 1100 (Investments - Securities)
  - Debits = purchases, Credits = sales
  - Falls back to placeholder if no accounting system available

#### Expense Ratio ✅ **WITH REGULATION S-X ADJUSTMENTS**
**Instruction 4(b)**: Ratio of Expenses to Average Net Assets using expenses from statement of operations.

- **Method**: `calculate_expense_ratio(fiscal_year_start, fiscal_year_end)`
- **Formula**: (Total Expenses / Average Net Assets) × 100
- **Regulation S-X Compliance**: ✅ **FULLY IMPLEMENTED**
  - Includes increases from rule 6-07 paragraph 2(g) (brokerage service arrangements)
  - Includes reductions from rule 6-07 paragraphs 2(a) and (f) (fee waivers/reimbursements)
  - Returns detailed breakdown with `fee_waivers` and `brokerage_service_adjustments`

#### Net Income Ratio
**Item 13**: Ratio of Net Income to Average Net Assets.

- **Method**: `calculate_net_income_ratio(fiscal_year_start, fiscal_year_end)`
- **Formula**: (Net Income / Average Net Assets) × 100
- **Net Income**: Total Income - Total Expenses

#### Financial Highlights Table
**Item 13**: Complete financial highlights table with per-share data and ratios.

- **Method**: `generate_financial_highlights(fiscal_year_start, fiscal_year_end)`
- **Includes**:
  - Net Asset Value (beginning and end)
  - Income from investment operations (per share)
  - Net gains/losses on securities (per share)
  - Total distributions
  - Total return
  - Expense ratio
  - Net income ratio
  - Portfolio turnover rate

### Item 26 - Calculation of Performance Data

#### Average Annual Total Return
**Instruction (b)(1)**: Calculate average annual total return using formula P(1+T)^n = ERV.

- **Method**: `calculate_average_annual_total_return(period_years, as_of_date, ...)`
- **Formula**: T = (ERV/P)^(1/n) - 1
- **Periods**: 1-year, 5-year, 10-year
- **Assumptions**:
  - Maximum sales load deducted from initial investment (defaults to 0 for ETFs)
  - All distributions reinvested
  - Account fees reflected
  - Redemption at end of period
- **Note**: `sales_load` parameter defaults to `Decimal('0')` for ETFs since ETFs typically have no sales load

#### 30-Day Yield
**Instruction (b)(4)**: Calculate 30-day standardized yield.

- **Method**: `calculate_30_day_yield(as_of_date)`
- **Formula**: YIELD = 2[((a-b)/cd + 1)^6 - 1]
  - a = dividends and interest earned during period
  - b = expenses accrued (net of reimbursements)
  - c = average daily shares outstanding
  - d = maximum offering price on last day
- **Period**: 30 days ending on as_of_date

#### Net Investment Income (NII)
**Item 26**: Calculate NII per share for yield calculations.

- **Method**: `calculate_net_investment_income(period_start, period_end)`
- **Formula**: (Dividends + Interest - Expenses) / Average Shares Outstanding
- **Average Shares**: Calculated monthly per Instruction 4(a)

#### After-Tax Returns ✅ **NEW**
**Instruction (b)(2) and (b)(3)**: Calculate average annual total return after taxes.

- **Method**: `calculate_after_tax_return_on_distributions()` - Item 26(b)(2)
  - After taxes on fund distributions but NOT after taxes on redemption
- **Method**: `calculate_after_tax_return_on_distributions_and_redemption()` - Item 26(b)(3)
  - After taxes on both distributions AND redemption
- **Tax Rates**: Uses highest marginal federal tax rates per N-1A Instruction 4
- **Includes**: Net Investment Income Tax (NIIT)
- **Tracks**: Distribution tax character (ordinary income, short-term/long-term capital gains)

#### Tax Equivalent Yield ✅ **NEW**
**Instruction (b)(5)**: Calculate tax equivalent yield for tax-exempt funds.

- **Method**: `calculate_tax_equivalent_yield(as_of_date, tax_rate)`
- **Formula**: Tax Equivalent Yield = (Tax-Exempt Yield) / (1 - Tax Rate) + Non-Tax-Exempt Yield
- **Use Case**: For tax-exempt funds (e.g., municipal bond funds)

### Average Shares Outstanding

#### Monthly Calculation
**Instruction 4(a) to Item 13**: Average shares outstanding must be calculated using monthly values.

- **Method**: `calculate_average_shares_outstanding(period_start, period_end)`
- **Implementation**: 
  - Groups NAV data by month
  - Uses month-end values
  - Calculates simple average of monthly values
- **Used for**: NII per share, yield calculations

## Data Requirements

### NAV Data Structure
Each NAV file (`nav_YYYY-MM-DD.json`) must contain:
```json
{
  "date": "YYYY-MM-DD",
  "nav_per_share": "decimal",
  "net_assets": "decimal",
  "shares_outstanding": "decimal",
  "total_assets": "decimal",
  "total_securities_value": "decimal",
  "accrued_income": "decimal",
  "accrued_expenses": "decimal",
  "fee_waiver": "decimal (optional, for Reg S-X)",
  "brokerage_service_adjustment": "decimal (optional, for Reg S-X)"
}
```

### Transaction Data (for Portfolio Turnover) ✅ **IMPLEMENTED**
For full portfolio turnover calculation, transaction records are needed:
- Purchase transactions (date, security, quantity, price)
- Sale transactions (date, security, quantity, price)

**Implementation**: ✅ **FULLY IMPLEMENTED**
- `_get_transaction_totals()` automatically extracts purchases/sales from accounting ledger
- Integrates with `Accounting` class when provided
- Reads from account 1100 (Investments - Securities)
- Debits = purchases, Credits = sales
- Portfolio turnover automatically uses transaction data when accounting system available

## Usage Examples

### Calculate Financial Highlights
```python
from lib.etf.functions.core import SECReporting
from datetime import date

sec = SECReporting(storage_path="./data/admin")

# Generate financial highlights for fiscal year
fiscal_year_start = date(2024, 1, 1)
fiscal_year_end = date(2024, 12, 31)

highlights = sec.generate_financial_highlights(fiscal_year_start, fiscal_year_end)
print(f"Expense Ratio: {highlights['ratios']['expense_ratio']}%")
print(f"Portfolio Turnover: {highlights['ratios']['portfolio_turnover_rate']}%")
```

### Calculate 30-Day Yield
```python
# Calculate yield as of today
yield_data = sec.calculate_30_day_yield(date.today())
print(f"30-Day Yield: {yield_data['30_day_yield']}%")
```

### Calculate Average Annual Total Return
```python
# Calculate 1-year, 5-year, and 10-year returns
# Note: sales_load defaults to 0 for ETFs (ETFs typically have no sales load)
for years in [1, 5, 10]:
    return_data = sec.calculate_average_annual_total_return(
        period_years=years,
        as_of_date=date.today(),
        initial_investment=Decimal('1000'),
        sales_load=Decimal('0'),  # ETFs have no sales load (default)
        account_fees=Decimal('0')
    )
    print(f"{years}-Year Return: {return_data['average_annual_total_return']}%")
```

### Calculate After-Tax Returns
```python
# After-tax return on distributions only (Item 26(b)(2))
after_tax_dist = sec.calculate_after_tax_return_on_distributions(
    period_years=1,
    as_of_date=date.today(),
    initial_investment=Decimal('1000'),
    sales_load=Decimal('0'),  # ETFs have no sales load
    account_fees=Decimal('0')
)
print(f"After-Tax Return (Distributions): {after_tax_dist['average_annual_total_return_after_tax_distributions']}%")

# After-tax return on distributions AND redemption (Item 26(b)(3))
after_tax_all = sec.calculate_after_tax_return_on_distributions_and_redemption(
    period_years=1,
    as_of_date=date.today(),
    initial_investment=Decimal('1000'),
    sales_load=Decimal('0'),
    account_fees=Decimal('0')
)
print(f"After-Tax Return (All Taxes): {after_tax_all['average_annual_total_return_after_all_taxes']}%")
```

### Calculate Tax Equivalent Yield
```python
# For tax-exempt funds (Item 26(b)(5))
tax_eq_yield = sec.calculate_tax_equivalent_yield(
    as_of_date=date.today(),
    tax_rate=Decimal('0.37')  # 37% federal rate
)
print(f"Tax Equivalent Yield: {tax_eq_yield['tax_equivalent_yield']}%")
```

### Portfolio Turnover with Transaction Integration
```python
# Initialize with accounting for transaction data
from lib.etf.functions.core import Accounting
from lib.etf.adapters import FMPDataSourceAdapter

adapter = FMPDataSourceAdapter(api_key='key', etf_symbol='REDI')
accounting = Accounting(adapter)
sec = SECReporting(storage_path='./data/admin', accounting=accounting)

# Portfolio turnover will automatically extract transactions from accounting ledger
turnover = sec.calculate_portfolio_turnover_rate(fiscal_year_start, fiscal_year_end)
print(f"Portfolio Turnover: {turnover:.2f}%")
```

### Calculate Expense Ratio (with Regulation S-X Adjustments)
```python
expense_ratio = sec.calculate_expense_ratio(fiscal_year_start, fiscal_year_end)
print(f"Expense Ratio: {expense_ratio['expense_ratio']}%")
print(f"Total Expenses: ${expense_ratio['total_expenses']}")
print(f"Fee Waivers: ${expense_ratio.get('fee_waivers', '0')}")  # Rule 6-07(2)(a) and (f)
print(f"Brokerage Service Adjustments: ${expense_ratio.get('brokerage_service_adjustments', '0')}")  # Rule 6-07(2)(g)
print(f"Average Net Assets: ${expense_ratio['average_net_assets']}")
```

## Compliance Checklist

- [x] Average net assets calculated monthly (Instruction 4(a))
- [x] Average shares outstanding calculated monthly (Instruction 4(a))
- [x] Portfolio turnover rate calculation (Instruction 4(d))
- [x] Expense ratio calculation (Instruction 4(b)) with Regulation S-X rule 6-07 adjustments
- [x] Net income ratio calculation
- [x] 30-day yield calculation (Instruction (b)(4))
- [x] Average annual total return calculation (Instruction (b)(1))
- [x] Net Investment Income calculation
- [x] Financial highlights table generation
- [x] After-tax returns on distributions (Instruction (b)(2)) - **IMPLEMENTED**
- [x] After-tax returns on distributions and redemption (Instruction (b)(3)) - **IMPLEMENTED**
- [x] Tax equivalent yield (Instruction (b)(5)) - **IMPLEMENTED**
- [x] Transaction data integration for portfolio turnover - **IMPLEMENTED**
- [x] Distribution tax character tracking - **IMPLEMENTED**
- [x] Regulation S-X rule 6-07 adjustments - **IMPLEMENTED**

## Notes

1. **Monthly Averaging**: All average calculations use monthly values as required by N-1A Instruction 4(a), not daily averages. This is **required** by SEC, not optional.

2. **Portfolio Turnover**: ✅ **FULLY IMPLEMENTED** - Automatically extracts transaction data from accounting ledger when `Accounting` instance is provided. Falls back to placeholder if no accounting system available.

3. **After-Tax Returns**: ✅ **FULLY IMPLEMENTED** - Both Item 26(b)(2) and (b)(3) are implemented:
   - Tracks distribution tax character (ordinary income, short-term/long-term capital gains)
   - Uses highest marginal federal tax rates per N-1A Instruction 4
   - Includes Net Investment Income Tax (NIIT)
   - Tracks tax basis for redemptions

4. **Regulation S-X Compliance**: ✅ **FULLY IMPLEMENTED** - Expense calculations include:
   - Increases from rule 6-07 paragraph 2(g) (brokerage service arrangements)
   - Reductions from rule 6-07 paragraphs 2(a) and (f) (fee waivers/reimbursements)
   - Returns detailed breakdown in expense ratio calculation

5. **Data Persistence**: All calculations save results to JSON files for audit trail and reporting.

6. **Sales Load Parameter**: All return calculation methods include `sales_load` parameter that defaults to `Decimal('0')` for ETFs. ETFs typically have no sales load, but the parameter is included for:
   - Mutual fund compatibility (per N-1A requirements)
   - SEC compliance (N-1A requires calculating returns with/without sales loads)
   - Flexibility if an ETF has a load in the future

## Implemented Enhancements ✅

All enhancements from the original "Future Enhancements" list are now **fully implemented**:

1. ✅ **After-Tax Returns**: Item 26(b)(2) and (b)(3) fully implemented
   - `calculate_after_tax_return_on_distributions()` - After taxes on distributions
   - `calculate_after_tax_return_on_distributions_and_redemption()` - After all taxes
   - Includes NIIT calculations
   - Tracks distribution tax character

2. ✅ **Tax Equivalent Yield**: Item 26(b)(5) fully implemented
   - `calculate_tax_equivalent_yield()` - For tax-exempt funds
   - Formula: Tax Equivalent Yield = (Tax-Exempt Yield) / (1 - Tax Rate) + Non-Tax-Exempt Yield

3. ✅ **Transaction Integration**: Fully implemented
   - `_get_transaction_totals()` - Extracts purchases/sales from accounting ledger
   - Integrates with `Accounting` class
   - Portfolio turnover automatically uses transaction data when available

4. ✅ **Distribution Tracking**: Fully implemented
   - Enhanced `_load_distribution_data()` with tax character tracking
   - Tracks: ordinary income, short-term/long-term capital gains
   - Integrates with `DistributionManager` and `DistributionCalculator`

5. ✅ **Regulation S-X Integration**: Fully implemented
   - Expense ratio includes rule 6-07 adjustments
   - Tracks fee waivers and brokerage service adjustments
   - Returns detailed breakdown in calculation results

