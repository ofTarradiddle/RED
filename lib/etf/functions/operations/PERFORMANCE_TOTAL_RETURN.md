# Performance Calculation: Total Return vs Price Return

## Overview

The performance calculation correctly computes **TOTAL RETURN** (not just price return) for both the fund and benchmark.

---

## Fund Total Return Calculation

### How It Works

1. **NAV History**: Uses daily NAV per share
2. **Distribution History**: Uses distribution history CSV file
3. **Total Return Formula**: `(NAV_curr + distribution) / NAV_prev`

### Why This Works

- **NAV goes ex-dividend** on the ex-date (NAV drops by distribution amount)
- To get **total return**, we must **add back the distribution**
- This gives us the return if distributions were reinvested

### Example

```
Day 1: NAV = $25.00
Day 2: Distribution = $0.25 per share
Day 2: NAV (ex-dividend) = $24.75

Price Return = ($24.75 / $25.00) - 1 = -1.00% ❌ (wrong - doesn't include dividend)
Total Return = (($24.75 + $0.25) / $25.00) - 1 = 0.00% ✓ (correct - includes dividend)
```

### Code Reference

```python
# From performance.py
growth_factor = (nav_curr + dist) / nav_prev
pre_tax_index *= growth_factor
```

---

## Benchmark Total Return Calculation

### Method 1: auto_adjust=True (Primary Method - Industry Standard)

**How it works**:
- yfinance `auto_adjust=True` returns **adjusted close prices**
- Adjusts ALL historical prices backwards to reflect dividends and splits
- This is the industry standard method (used by Bloomberg, FactSet, etc.)
- Simply calculate: `(end_price / start_price) - 1`

**Code**:
```python
hist = bench_ticker.history(
    start=start_date,
    end=end_date,
    auto_adjust=True  # Adjusted close includes dividends
)
total_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1
```

**Advantages**:
- ✅ Industry standard (Bloomberg, FactSet, etc.)
- ✅ Simpler calculation
- ✅ Handles splits automatically
- ✅ Most accurate for total return

**Note**: This method adjusts prices backwards, so the first price in the adjusted series may differ from the unadjusted price.

### Method 2: actions=True + Manual (Fallback)

**How it works**:
- yfinance `actions=True` returns dividends in separate column
- Manually compound returns: `(price_curr + dividend) / price_prev`
- Assumes dividends are received and reinvested

**Code**:
```python
hist = bench_ticker.history(
    start=start_date,
    end=end_date,
    actions=True  # Get dividends separately
)
# Manually compound with dividends
growth_factor = (price_curr + dividend) / price_prev
```

**When used**: Fallback if `auto_adjust=True` fails

**Note**: This method may give slightly different results (typically 0.1-0.5% difference) due to:
- Timing differences in dividend recognition
- Reinvestment assumptions (reinvesting at current price vs ex-dividend price)
- Data source differences

**Important**: The `auto_adjust=True` method is preferred and is the industry standard.

---

## Verification

### Testing yfinance Dividend Data

```python
import yfinance as yf

ticker = yf.Ticker('SPY')
hist = ticker.history(period='1mo', auto_adjust=True)

# auto_adjust=True gives total return directly
first_price = hist['Close'].iloc[0]
last_price = hist['Close'].iloc[-1]
total_return = (last_price / first_price) - 1
# This is TOTAL RETURN (includes dividends) ✓
```

### Comparison

| Method | Price Return | Total Return | Includes Dividends |
|--------|--------------|--------------|-------------------|
| `Close` price only | ✓ | ✗ | ✗ |
| `auto_adjust=True` | ✗ | ✓ | ✓ |
| `actions=True` + manual | ✗ | ✓ | ✓ |

---

## Key Points

1. **Fund Calculation**: Uses NAV + distributions (NAV is ex-dividend, so we add distributions back)
2. **Benchmark Calculation**: Uses `auto_adjust=True` (adjusted close includes dividends)
3. **Both methods give TOTAL RETURN** (not just price return)
4. **After-tax calculation**: Applies tax rate to distributions before reinvestment

---

## Data Requirements

### Fund Performance

- **NAV History CSV**: Must have `date` and `nav` columns
- **Distribution History CSV**: Must have `date` and `distribution_per_share` columns
  - If missing, assumes no distributions (price return only)

### Benchmark Performance

- **yfinance**: Automatically handles dividends via `auto_adjust=True`
- **No additional data needed**: yfinance provides total return directly

---

## Example Output

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "start_nav": 25.00,
  "end_nav": 27.50,
  "pre_tax_total_return": 0.10,  // 10% total return (includes distributions)
  "after_tax_total_return": 0.085,  // 8.5% after-tax (distributions taxed)
  "benchmark": {
    "symbol": "^GSPC",
    "total_return": 0.12,  // 12% total return (includes dividends)
    "note": "Using auto_adjust=True for total return (includes dividends)"
  }
}
```

---

## References

- **yfinance Documentation**: `auto_adjust=True` provides adjusted close (total return)
- **SEC Requirements**: Performance must be reported as total return
- **Industry Standard**: Total return = price return + dividend return

