# Innovation Factor Backtest Logic - Step by Step

## Overview
The innovation factor portfolio selects the top 50 S&P 500 stocks by innovation factor each month and holds them equal-weighted for one month, then rebalances.

## Step-by-Step Process

### 1. **Data Loading**
- **Constituents**: Monthly S&P 500 constituents (from `sp500_monthly_constituents.csv`)
- **Returns**: Daily returns for all tickers (from `sp500_total_returns_corrected.csv`)
- **Fundamentals**: Annual income statements for each ticker (from `sp500_fundamentals/`)

### 2. **For Each Month-End Rebalance Date** (e.g., 2004-01-30)

#### 2a. **Get Constituents**
- Load the list of S&P 500 constituents for that month-end date
- Example: 458 tickers on 2004-01-30

#### 2b. **Calculate Innovation Factors** (Point-in-Time)
For each constituent ticker:
- Filter fundamentals to **only data BEFORE the rebalance date** (`df['date'] < rebalance_date`)
- Extract sales and R&D columns from income statements
- Run `rolling_ols()` function:
  - Regress `log(sales)` on 5 lagged `log(R&D)` variables (lag1 through lag5)
  - Use 8-year rolling window
  - Requires at least 4 non-missing lags
- Get the most recent available year's regression results (must be < rebalance year)
- Extract the 5 lag coefficients (lag1, lag2, ..., lag5)
- **Innovation Factor = Average of the 5 coefficients** (need at least 3 valid)

**Example (2004-01-30):**
- Only 56/458 tickers have sufficient data to calculate factors
- Factor range: [0.0167, 0.6347]
- Top stock: HPQ with factor 0.6347

#### 2c. **Select Top 50 Stocks**
- Sort all tickers with calculated factors by innovation factor (descending)
- Select top 50 (or all available if < 50)
- Example: Top 50 includes HPQ, ABT, ADBE, CPN, VIAV, etc.

#### 2d. **Calculate Portfolio Return for Next Month**
- Get the next month's date range (e.g., 2004-02-01 to 2004-02-29)
- Extract daily returns for selected tickers for that month
- For each ticker, compound daily returns to get monthly return:
  ```
  monthly_return_ticker = (1 + r_day1) * (1 + r_day2) * ... * (1 + r_dayN) - 1
  ```
- **Portfolio return = Mean of all ticker monthly returns** (equal-weighted)
  ```
  portfolio_return = mean(monthly_return_ticker1, monthly_return_ticker2, ..., monthly_return_ticker50)
  ```

### 3. **Repeat for All Months**
- Process each month-end from 2004-01-30 to 2025-12-31
- Factors update when new annual data becomes available (typically once per year)
- Portfolio rebalances monthly but factor values may stay the same until new annual data

### 4. **Calculate Performance Metrics**
- Cumulative returns: `(1 + r1) * (1 + r2) * ...`
- CAGR, volatility, Sharpe ratio, max drawdown

## Key Implementation Details

### Point-in-Time Data
- **Critical**: Only uses fundamental data that would have been available at the rebalance date
- Filters: `df['date'] < rebalance_date` (strictly before)
- This prevents look-ahead bias

### Factor Calculation
- Uses `rolling_ols()` from `factors.py`
- Requires at least 8 years of historical data
- Needs at least 4 non-missing lagged R&D values
- Innovation factor = average of lag1 through lag5 coefficients

### Portfolio Construction
- **Equal-weighted** among selected stocks
- Each stock gets weight = 1/N where N = number of stocks (typically 50, so 2% each)
- Rebalances monthly

### Return Calculation
- **Method**: Compound daily returns per ticker to monthly, then average
- This is mathematically equivalent to: equal-weighted average of daily returns, then compound
- Formula: `portfolio_return = mean([(1+r1_i)*(1+r2_i)*...-1 for i in tickers])`

## Potential Issues to Check

1. **Factor Stability**: Factors don't change month-to-month (expected with annual data)
2. **Selection Effectiveness**: Top 50 may overlap significantly with overall S&P 500
3. **Return Calculation**: Should verify the method matches equal-weighted S&P 500 calculation
4. **Data Coverage**: Only ~12-37% of constituents have factors in early years

## Comparison to Equal-Weighted S&P 500

The equal-weighted S&P 500 backtest:
- Holds **ALL** constituents (458-501 stocks) equal-weighted
- Rebalances monthly
- Calculates daily portfolio returns as equal-weighted average, then compounds

The innovation factor portfolio:
- Holds **TOP 50** by innovation factor equal-weighted
- Rebalances monthly
- Calculates monthly returns per ticker, then averages

If the top 50 stocks perform similarly to the overall S&P 500, returns would be very similar.

