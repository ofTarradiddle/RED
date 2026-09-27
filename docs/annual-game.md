# REDI Play: annual portfolio research

The web game at `/play/` and native iPhone Play tab share an accounting engine
and a pinned source edition. The earlier twelve-choice game remains at
`/play/arcade/`. Annual portfolio records are separate from its rankings.

## Decision and execution clock

The first information cutoff is December 31, 2010. The player starts with $100
of fictional capital and executes at the first observed close afterward,
January 3, 2011. Each subsequent decision uses the next year-end cutoff and
first-session closing prices. This is not a simulated purchase at the prior
year's closing price. The final interval ends at the most recent supplied
observation, so the final year may be partial.

Historical constituent rosters are reconstructed from archived public sources.
All members remain visible, including multiple listed share classes. They are
not today's S&P 500 constituents projected backward. The public reconstruction
is not a licensed, certified index record; its earliest annual lists contain
497 names. See [source identities and coverage](../data/annual-game/README.md).

Choose any number of supported companies. Weights are fractions of the entire
current portfolio and must sum to no more than 100%. Unallocated cash earns
zero. The equal-weight-universe control prepares an editable draft across
all companies with complete return coverage for that interval, regardless of
the current search or page. It does not place the allocation automatically.
No leverage, shorting, fees, taxes, or trading frictions are modeled.

## Point-in-time SEC evidence

`scripts/annual_filings.py` collects SEC submissions, original annual reports,
and standard US-GAAP Company Facts. Annual-report text can come from 10-K,
20-F, or 40-F documents; standardized numerical facts currently use 10-K/10-K/A
US-GAAP tags. Missing custom or IFRS tags remain unknown. A missing R&D tag
does not establish zero R&D.

The engine and publisher both enforce availability dates. A future comparative
restatement is excluded until its actual filing date. The report narrative
comes from the original annual report available by the cutoff; a signature-only
amendment does not replace it. Fiscal periods older than 550 days are excluded.
Each numeric value retains its own fiscal period, filing date, accession, tag,
unit and direct SEC source. Do not infer that every displayed value covers the
same fiscal year. R&D/revenue is calculated only when both source periods match.

The company record distinguishes:

- Reported annual R&D expense.
- Cash payments for property, plant and equipment.
- Acquisition cash spending, with the original gross/net tag retained.
- Revenue, operating cash flow, diluted EPS, and eligible annual earnings P/E.
- Automated investment-topic pointers and brief quotations from the dated report.

These are different accounting measures and are not added into a synthetic
innovation budget. Topic mentions are navigation aids, not verified project
allocations, a complete investment thesis, or a causal explanation of returns.
Short quotations share a 25-word budget per source report. A clipped monetary
scale is restored only from the matching cached source bytes; ambiguous amounts
are removed. The source report remains available through its link.

Dated registrant transitions preserve predecessor evidence around holding
company reorganizations. A predecessor report already public at the transition
can remain eligible afterward, subject to age limits. A later filing by a former
registrant cannot override the successor's record. Unverified historical name
aliases are disclosed separately from the SEC source facts.

A verified source-specific extension can admit a predecessor's original annual
report filed just after a reorganization, but only for a fiscal period ending
before it. These exceptions retain an explicit evidence cutoff and source link;
there is no general grace period for later predecessor filings.

P/E uses the last observed close before the cutoff and the latest filed annual
diluted EPS, not forecast or trailing-twelve-month earnings. Yahoo split-adjusted
Close and WIKI unadjusted Close require different translations to the EPS share
basis. P/E is withheld without verified split coverage, when a split between
fiscal period-end and filing makes the EPS basis ambiguous, or when earnings are
nonpositive. A provider-adjusted return index is never used as a raw share price.

## Returns and attribution

Each company interval requires actual observations at every published valuation
date: month-end sessions, execution, and exit. Missing quotes are never carried
forward, interpolated, replaced by modern reused tickers, or assigned a zero
return. A series ending before a merger or bankruptcy does not establish the
terminal shareholder payoff. The affected interval is unavailable for allocation.
This availability constraint creates selection bias.

Known material disagreements between provider histories are also excluded from
playable observations. `data/annual-game/quality_flags.json` preserves the source
comparisons, affected dates and corporate-action evidence. The engine blocks the
affected annual interval even if a reviewed-out quote is accidentally restored;
other valid years remain usable. Pre-decision coverage messages do not disclose
the later event or its returns. This bounded cross-check is not an audit of every
historical distribution.

The calculations use ratios of one provider's adjusted-close series. Its dividend
and split adjustments are already included; neither is credited again. Each
security uses one continuous source history, without stitching adjusted levels
across vendors. These return proxies are not a reconstructed corporate-action
ledger of every spin-off, merger election, cash payment or cancellation.

For portfolio value `V`, firm weight `w`, and adjusted levels `A0` and `At`:

```text
Capital allocated = V × w
Return units      = (V × w) / A0
Marked value      = Return units × At
Period profit     = Marked value − Capital allocated
Portfolio value   = Sum of marked firm values + cash
```

At a rebalance, old lots close and new lots open at the same observed close.
Realized and unrealized firm profits reconcile to total portfolio profit.
Repeated allocations recycle portfolio capital; they are not external deposits.
Firm deep dives separate period returns, linked returns for owned periods,
capital deployed, and dollar contributions. An owned-period linked return excludes
years with no holding; it is not an annualized money-weighted return. SPY begins
with the same $100 and follows the same calendar as a buy-and-hold S&P 500 ETF
proxy. It is not the index itself.

Results are revealed after each committed decision. Because this is a static
historical game, an informed player or someone inspecting the downloaded dataset
can know the outcomes. Replay validation protects accounting consistency, not
against hindsight. Device records contain no invented competitors.

## Build, refresh and persist

Ordinary website builds use only the committed `dataset.json`; no SEC or Yahoo
request is required. GitHub Pages serves static files. Native builds bundle the
same edition as `annual-game.json`; they do not download executable game code.

```sh
python -m pip install -r requirements-annual.txt

# Explicit market/source refresh. Source refresh re-pins downloaded metadata.
python -m scripts.refresh_comparison --strict
python -m scripts.annual_universe --refresh-sources --refresh-prices
python -m scripts.annual_filings \
  --universe data/annual-game/universe.json --refresh-metadata --workers 10
python -m scripts.refresh_annual_game

# Recompile evidence from existing local caches without network requests.
python -m scripts.annual_filings \
  --universe data/annual-game/universe.json --offline
python -m scripts.refresh_annual_game
python -m publishing.build
```

SEC requests carry a declared research contact and a global rate limit below
seven requests per second. Raw report bytes, metadata, parsed reports and cards
are cached under `.cache/annual-filings/`. Provider source caches and intermediate
`filings.json` are also ignored by Git. Cache writes are atomic. The publisher
copies only the validated public dataset, not raw reports or internal caches.

The manual **Refresh annual game source snapshot** GitHub Actions workflow
persists source caches and produces a 90-day downloadable review artifact.
A cold SEC cache can take roughly an hour. Historical archive observations from
the committed edition remain available when an ignored provider cache is absent.
Actions cache is an optimization with retention limits, not permanent archival
storage. Keep a separate copy of local source caches for full reproducibility.

Review the artifact's per-year coverage and source changes before replacing
`data/annual-game/dataset.json`, `universe.json`, `coverage.json`, `quality_flags.json`, and applicable
source manifests on `2026-sep-red`. Committing and pushing publishes the reviewed
edition and rebuilds iOS. The refresh workflow deliberately does not automatically
change the game or its ranking edition. Retrieval timestamps alone do not change
the economic content hash; changed observations or evidence do.

## Verification

```sh
python -m pytest tests/test_annual_universe.py tests/test_annual_filings.py \
  tests/test_annual_excerpt.py tests/test_annual_release.py tests/site -q
node --test tests/annual-portfolio.test.cjs
```

Tests cover historical identities, quote coverage and split bases; dated facts
and report selection; bounded excerpts; future-information and publication guards;
multi-firm accounting, reentry, cash, rebalance timing, and deterministic replay
for hundreds of simultaneous holdings. Native simulator interaction and unsigned
device archive checks run in the iOS workflow. App Store distribution additionally
requires the publisher's Apple Developer membership and signing setup.

Primary SEC documentation: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
and [automated access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).
