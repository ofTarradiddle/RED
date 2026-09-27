# REDICore

Foundation-only comparison models and calculations shared by the native iOS app.
The JSON contract is the published `compare/data.json` snapshot; the package has
no Yahoo credentials, network client, analytics, or external dependencies.

## Method

- Validate the complete snapshot before use, including unselected histories.
  Unknown or duplicate fund identifiers, non-USD prices, impossible or duplicate
  dates, and nonfinite or invalid numeric observations are rejected.
- REDI can use NAV or Market Price. Peers always use their market price.
- Price change chains closing-price ratios. With reinvestment enabled, each
  ex-date uses `(closing price + distribution) / previous closing price`.
  Reinvestment assumes execution at that day's closing price.
- The publisher supplies split-adjusted prices and compatible per-share
  distributions. Split ratios and adjusted close are retained as source fields
  and are not applied again. Fund expenses already reflected in the closing
  price or NAV are not subtracted a second time.
- Build each distribution chain before matching calendars; only shared closing
  dates are displayed. No forward filling or missing-price estimates are used.
  Every displayed series starts at 100 on the same shared closing date.
- YTD includes the last shared close before January 1 when available. Trailing
  month periods use calendar months and clamp dates at the target month's end.
- Drawdown is the largest fall from a prior displayed peak. Annualized volatility
  uses the sample variance of daily simple returns multiplied by 252. Correlation
  is Pearson correlation with REDI over those same returns.
- Volatility and correlation require 20 matched returns. Missing peer sessions or
  shared gaps longer than five calendar days withhold these daily risk measures.
  Correlation with a constant return series is unavailable, not zero.
- Missing REDI history produces no comparison. Unavailable peers are explicitly
  named in warnings, never replaced with synthetic returns.

`isIllustrative` travels from the source to every comparison result so the app
can label the current workbook series independently of real peer observations.

## Strategy research

`ResearchEngine` reads the separate monthly `data/strategy_research.json` contract.
The source is a rounded table transcribed from the opening backtest exhibit,
not actual REDI fund history or an independently reproduced portfolio backtest.
Source dividend and fee assumptions are unspecified, so the engine neither
adds distributions nor deducts fees from those levels.

- Research observations must be positive, ordered, unique calendar month ends
  matching the stated source period. Innovation Leader anchors the comparison.
- ETF overlays build their complete own-history reinvested wealth first, then
  sample the last observed session in each calendar month only if it is within
  four calendar days of month end. Each point preserves its actual session date.
  An ETF month end must also be on or before the snapshot's publication day;
  partial current months do not stand in for completed monthly observations.
- All selected series intersect before applying the requested trailing calendar
  period. No interpolation, daily backfill, pre-inception history, or splicing
  into REDI NAV occurs. Unavailable peers are explicitly excluded.
- Every displayed series rebases to $100 on the first shared observation. CAGR
  uses actual elapsed days / 365.25 and is withheld below one calendar year.
  Drawdown uses only matched month-end levels; no daily risk estimate is inferred.
- A logarithmic axis transforms the display, not the underlying wealth levels.

Research tests verify ex-date handling before calendar matching, actual session
dates, freshness limits, shared inception, leap-day period boundaries, sub-year
CAGR withholding, malformed inputs, and the audited 281-observation source.

## Validation

With Xcode installed:

```sh
swift test --package-path ios/REDICore
```

The tests cover reinvestment, unmatched ex-dates, split treatment, common periods,
YTD, risk statistics and missing sessions, wire decoding, malformed observations,
and saved settings. Apple Command Line Tools alone may not supply XCTest; the
native app workflow uses the full Xcode toolchain.
