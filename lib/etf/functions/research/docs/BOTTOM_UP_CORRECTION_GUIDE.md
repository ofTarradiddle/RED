# Bottom-Up Error Correction System

## Overview

The bottom-up error correction system investigates and corrects individual ticker returns to fix portfolio-level errors. Instead of simply replacing portfolio returns with benchmark returns, this system:

1. **Identifies problematic days** by comparing portfolio returns to the S&P 500 EW benchmark
2. **Investigates individual ticker returns** on those days
3. **Uses FMP stock split calendar** to detect split-related issues
4. **Verifies returns with Yahoo Finance** to get accurate data
5. **Corrects individual ticker returns** in the returns dataframe
6. **Re-runs the backtest** with corrected data

## Calibration Steps

### Step 1: Identify Problematic Days

- Compare portfolio returns to benchmark returns (2006+ when benchmark data is available)
- Calculate absolute deviations for each day
- Select top 50 days with largest deviations for investigation

### Step 2: Investigate Individual Ticker Returns

For each problematic day:

1. **Get portfolio holdings** for that date (from monthly constituents)
2. **Extract individual ticker returns** from returns dataframe
3. **Identify extreme returns**:
   - Returns >50%: Definitely errors
   - Returns 25-50%: Check for splits or verification needed
   - Returns >30%: Verify with Yahoo Finance

### Step 3: Check FMP Stock Split Calendar

- For each ticker with extreme returns, check FMP split calendar
- Look for splits within ±5 days of the problematic date
- If split detected, verify return with Yahoo Finance (which handles splits correctly)

### Step 4: Verify with Yahoo Finance

- Fetch ticker data from Yahoo Finance for the problematic date
- Compare Yahoo return to current return in dataframe
- If difference >1% (for extreme returns) or >5% (for moderate returns), use Yahoo return

### Step 5: Correct Individual Returns

- Update the returns dataframe with corrected ticker returns
- Document all corrections in the corrections log

### Step 6: Re-run Backtest

- Re-run the entire backtest using the corrected returns dataframe
- Calculate new portfolio returns from corrected ticker data
- Compare to benchmark again

## Correction Criteria

### Automatic Corrections

1. **Extreme Returns (>50%)**:
   - Always investigate
   - If Yahoo Finance data available and differs significantly, use Yahoo
   - If no Yahoo data, set to 0 (likely data error)

2. **Split-Related Returns (25-50%)**:
   - If split detected on that date, verify with Yahoo
   - Use Yahoo return if available

3. **High Returns (>30%)**:
   - Verify with Yahoo Finance
   - Use Yahoo if difference >5%

### Documentation

All corrections are logged to:
- `data/research/sp500_backtest/bottom_up_corrections_log.json`

Each entry includes:
- Date
- Portfolio return vs benchmark return
- Deviation amount
- List of ticker corrections made
- Old return → New return
- Reason for correction
- Whether split was detected

## Output Files

1. **`bottom_up_corrections_log.json`**: Complete log of all corrections
2. **`sp500_ew_backtest_results.csv`**: Portfolio returns (after correction)
3. **`sp500_ew_backtest_metrics.json`**: Performance metrics
4. **`sp500_ew_backtest.png`**: Final plot comparing portfolio to benchmark

## Performance Goals

The system aims to:
- Match S&P 500 EW benchmark CAGR within 1-2 percentage points
- Reduce tracking error to <5% annualized
- Maintain correlation >0.95 with benchmark

## Limitations

1. **Pre-Benchmark Period (1990-2006)**: No benchmark data available, so only extreme returns (>10%) are flagged
2. **API Rate Limits**: FMP and Yahoo Finance have rate limits, so investigation is limited to top 50 problematic days
3. **Data Availability**: Some tickers may not have Yahoo Finance data, especially for older dates

## Future Enhancements

1. **Iterative Correction**: Run multiple passes to catch cascading errors
2. **Batch Split Checking**: Pre-fetch all splits for S&P 500 tickers
3. **Machine Learning**: Use patterns to identify likely errors before verification
4. **Extended Investigation**: Investigate more than 50 days if needed

