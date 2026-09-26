# REDI Compare

Open `/compare/` on the local preview or the published site. On iPhone, use
Safari → Share → Add to Home Screen → Open as Web App (if shown). The app has a
wing-H icon, saved selections, and a scoped offline cache. It is a web app;
there is no App Store binary or brokerage connection.

## Data and calculations

- REDI currently uses the explicitly illustrative workbook history. It is not
  an actual fund track record and is never extended with invented daily values.
- SPY, VOO, QQQ, ITAN and SYLD use dated Yahoo Finance closing observations.
  The committed seed was retrieved on September 26, 2026 and ends September 25.
- Every displayed series uses the same common observation dates. Consequently,
  a newer peer history does not extend a shorter REDI history. Source dates and
  comparison dates are shown separately.
- Price mode measures split-adjusted price/NAV changes. Reinvested mode chains
  `(closing value + ex-date distribution) / previous closing value` on each
  series' complete history before intersecting calendars. It does not add
  distributions to adjusted close or apply splits twice. The distribution
  field includes dividends and capital-gain distributions returned by Yahoo.
- Each path is normalized to 100 at the selected starting close. YTD uses the
  previous year's last common closing observation when available. Other date
  windows show the actual first and last included dates.
- Maximum drawdown uses the selected normalized path. Volatility is the sample
  standard deviation of daily simple returns times √252. Correlation uses those
  same matched returns. At least 20 matched return observations are required;
  missing observed peer sessions or long gaps suppress annualized risk metrics.
  Zero variance makes correlation undefined.
- Fund fees are already reflected in observed NAV/market prices; the expense
  ratio is not deducted again. Taxes and investor trading costs are excluded.
- A failed retrieval retains a validated previous peer history and labels it
  stale. An unavailable peer is identified and omitted, never filled with a
  made-up series. The app's refresh control checks the published dataset; it
  does not trigger Yahoo requests from a visitor's device.

## Refresh and publication

```sh
python -m scripts.refresh_comparison --strict
python -m publishing.build
node --test tests/comparison-math.test.cjs
python -m pytest tests/test_comparison_data.py tests/site/test_comparison_release.py -q
```

`data/etf_comparison.json` is the public peer cache. Builds validate and combine
it with the REDI input into `compare/data.json`; no accounting ledgers or private
dashboards enter that file. The Yahoo request runs on the publishing machine,
not in Safari. Each build also emits a manifest and versioned service worker
whose scope is only `/compare/` (including the GitHub Pages repository prefix).
Its allowlist includes only the app, its assets and its public dataset.

The **Daily REDI Compare updates** workflow calls the publisher on
`2026-sep-red` at 22:15 UTC on weekdays. GitHub only activates scheduled events
from the default branch, so the small `compare-daily.yml` scheduler must also
exist on `main`. App code and the publishing workflow remain on `2026-sep-red`.
Use that workflow's **Run workflow** button for an immediate server refresh.
Scheduled times are best effort and may be delayed by GitHub. Public peer data
persists through Actions cache; later website and SPY builds restore that cache.
The committed seed remains a fallback if the cache expires.

Yahoo/yfinance access does not itself grant public or commercial redistribution
rights. Confirm rights or replace the peer adapter with a licensed source before
launching a commercial fund app. The development banner remains present.

## Connecting the actual fund

The build accepts an optional **public-only** `data/redi_live.json` file. Supply
it from an approved provider export; never point it at private operating books.
The adapter requires:

```json
{
  "id": "REDI",
  "approved_for_publication": true,
  "is_illustrative": false,
  "currency": "USD",
  "price_basis": "split_adjusted",
  "source": "Actual administrator / pricing source name",
  "source_url": "https://provider.example/public-redi-history",
  "inception_date": "YYYY-MM-DD",
  "observations": [
    {
      "date": "YYYY-MM-DD",
      "nav": 0,
      "market_price": 0,
      "distribution": 0
    }
  ]
}
```

This is a schema example, not valid price data. Replace every placeholder:
NAV and market price must be positive; distributions must be nonnegative.
Dates must be canonical, sorted, unique and no earlier than live inception.
Historical prices, NAV and distributions must share a split-adjusted per-share
basis. A malformed live feed stops the build rather than silently falling back
to the illustrative workbook. Historical live REDI results are not spliced to
prelaunch simulations. Provider ingestion, approval and daily delivery must be
implemented for the provider selected at launch.

The site remains a development preview until its disclosures, data rights and
live fund information are reviewed. This adapter only prepares the comparison
data boundary; it does not automatically launch the fund or convert other
website pages to live reporting.
