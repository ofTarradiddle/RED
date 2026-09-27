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

## Validation

With Xcode installed:

```sh
swift test --package-path ios/REDICore
```

The tests cover reinvestment, unmatched ex-dates, split treatment, common periods,
YTD, risk statistics and missing sessions, wire decoding, malformed observations,
and saved settings. Apple Command Line Tools alone may not supply XCTest; the
native app workflow uses the full Xcode toolchain.
