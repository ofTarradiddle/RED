# Annual portfolio game: source edition and coverage

The first decision uses the constituent snapshot available at **December 31,
2010** and executes at the observed **January 3, 2011** close. Subsequent rounds
rebalance at the first observed trading close of each calendar year. Monthly
valuations use genuine final observed sessions, plus the exact execution and
exit sessions. The current edition ends **September 25, 2026**; its last holding
year is partial. No quotes are interpolated.

`universe.json` contains 822 historical security-era records plus SPY, 797 with
at least one observed return point, and 137,237 sampled observations. A member
without a complete selected-year path remains visible but cannot be simulated
as if its missing prices or acquisition/bankruptcy payoff were known. Merely
ending a price series does not imply a 100% loss or a sale at the last quote.

## Actual complete annual paths

The year below is the **decision cutoff year**; 2010 means the ensuing 2011
holding period. Counts include distinct listed share classes when the source
roster includes them. Historical public reconstructions sometimes contain
497 rather than 500 names; those omissions are not silently repaired using
today's constituents.

| Decision year | Complete price paths | Historical roster |
|---|---:|---:|
| 2010 | 471 | 497 |
| 2011 | 474 | 497 |
| 2012 | 485 | 497 |
| 2013 | 487 | 497 |
| 2014 | 475 | 499 |
| 2015 | 477 | 502 |
| 2016 | 485 | 506 |
| 2017 | 473 | 505 |
| 2018 | 488 | 505 |
| 2019 | 483 | 505 |
| 2020 | 491 | 505 |
| 2021 | 490 | 505 |
| 2022 | 485 | 503 |
| 2023 | 491 | 503 |
| 2024 | 490 | 503 |
| 2025 | 498 | 503 |

`coverage.json` is authoritative after each refresh and lists every unavailable
member, its number of missing observations, and first missing session. These
are price-path counts, separate from filing/financial-evidence coverage.

The compiled edition `c8032bdcf088d06b0ef0` contains 8,032 company-year
decisions. Of these, 7,954 have annual-filing topic excerpts and 7,823 have
at least one eligible standard financial figure; this does not mean every
requested metric is available. The first decision year has filing excerpts
for 494 of 497 members and financial figures for 373. Eligible standard
financial tags are less widely available in the earliest decision year.
`dataset.json` retains the exact per-year evidence counts and source dates.

## Sources and identity

- [fja05680/sp500](https://github.com/fja05680/sp500), MIT: dated historical
  constituent snapshots, most recently changed August 18, 2026. This is a
  public reconstruction, not the official licensed S&P constituent history.
  Some historical rows use later aliases, such as AABA for Yahoo.
- [lawcal/sp500-components-history](https://github.com/lawcal/sp500-components-history),
  MIT: historical symbol/name/CIK metadata. Its approximate dates and some
  overwritten issuer identities make it unsuitable as the sole historical
  roster. `membershipCrossCheck` preserves disagreements with the primary
  snapshot source.
- [SEC company ticker map](https://www.sec.gov/files/company_tickers.json):
  current ticker-to-registrant evidence, used to prevent automatic substitution
  when an old symbol now names a different issuer. Current CIKs are **not**
  assumed to have filed every historical annual report.
- Dated `filingCiks` mappings link explicitly checked predecessor registrants
  for Google/Alphabet, Apache/APA, Medtronic, Eaton, ICE, BlackRock, Disney,
  TechnipFMC, Exxon, Cigna, Walgreens, Xerox, Baker Hughes, CSC/DXC, Mylan,
  Express Scripts and Avago/Broadcom. These mappings carry
  primary source URLs. Other metadata remains explicitly unverified.
  Mylan's final predecessor annual report has an explicitly sourced
  `evidenceThrough: 2015-03-02` extension: that report covers 2014 but was filed
  just after the February 27 holding-company transition. It does not authorize
  using later subsidiary fiscal periods as parent-company evidence.
- `historicalLabels` corrects checked period names/tickers (for example
  Facebook, General Electric, WellPoint and Priceline). Other names carry
  `status: source-alias-unverified`; they must not be represented as verified
  contemporaneous names.
- Old Chubb and acquiring ACE/new Chubb, old Johnson Controls and acquiring
  Tyco/new JCI, and original Allergan and Actavis/new Allergan are kept separate.
  Original bankrupt common stock is never exchanged for a new post-bankruptcy
  ticker by name alone.
- Google's pre-2014 Class A uses the GOOGL return history and displays its
  contemporary GOOG ticker. Class C is separately eligible from 2014; Yahoo's
  synthetic earlier GOOG rows are excluded. Source-dated archive aliases also
  separate the unrelated Contura CTRA symbol from Cabot/Coterra, and retain
  checked continuity across CBS/VIAC/PARA and Ceridian/CDAY/DAY name changes.
- Discovery Class C (DISCK) uses its own archived history. A matching issuer
  CIK does not authorize substituting WBD's Class-A back history for a different
  historical share class.

Original downloaded membership/metadata bytes are hashed in
`sources/manifest.json`; the importer verifies these hashes before use.

## Return and quote sources

1. **Current Yahoo Finance daily histories**, via `yfinance` with
   `auto_adjust=False`, explicit `Adj Close`, and action data. Yahoo's `Close`
   is split adjusted; it is not silently described as the dollars an investor
   saw on that historical day. Full daily inputs are cached locally. Published
   points are sampled from actual sessions.
   `splitsStatus: complete` requires a successful maximum-history action fetch.
   `splitsFrom` and `splitsAsOf` describe that actual provider window, while
   `priceBasisAsOf` records the normalization endpoint for Yahoo's historical
   close. These can extend past the game's last observed SPY session: future
   normalization actions remain in private calculation metadata even though
   published return observations stop at the game date. The filing compiler
   must check both boundaries before applying split-adjusted P/E calculations.
2. [Frozen Quandl WIKI archive](https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites):
   127 selected security histories in this edition. The archive ends March 27,
   2018; raw ZIP SHA-256 is
   `adfd226694c6f3ec2c56b585d973764180a39a3ec516601721e90096dc1de94f`.
   `close` is an unadjusted contemporaneous quote; `adj_close` is the provider's
   adjusted-return proxy. Every daily non-unit `split_ratio` is retained, not
   only events on sampled sessions (AAPL June 9, 2014 is 7 new shares per old
   share). Split completeness ends at the archive or conservative identity
   boundary. Mirror license metadata says **Unknown**; the raw archive is not
   redistributed.
3. [April-2020 Yahoo archive](https://www.kaggle.com/datasets/jacksoncrow/stock-market-dataset),
   CC0: 18 selected histories. Individual source files are downloaded, hashed,
   and sampled; original symbol/name metadata is retained locally.
4. [April-2022 Yahoo archive](https://www.kaggle.com/datasets/hanseopark/sp-500-stocks-value-with-financial-statement),
   CC0: 9 selected histories. The CSV's actual `Adj Close` column is
   retained with its source hash; no missing return observations are inferred.
5. [Frozen December-2022 stock archive](https://www.kaggle.com/datasets/paultimothymooney/stock-market-data):
   7 selected histories. Individual CSV paths and byte hashes are retained.
   The mirror labels its license “Other (specified in description)” but the
   description supplies no further terms; raw CSVs are not redistributed.
   Final rows are excluded because some were captured intraday.

6. [September-2023 Yahoo archive](https://www.kaggle.com/datasets/tanavbajaj/yahoo-finance-all-stocks-dataset-daily-update),
   Open Database License, contents credited to their original authors:
   15 selected histories. Its adjusted `Close` is admitted only after
   at least 24 overlapping monthly return intervals agree with an independent
   adjusted-price reference (RMS difference below 0.00001 and maximum below
   0.0001 in return fractions). The final intraday session is excluded.
7. [July-2025 Yahoo archive](https://www.kaggle.com/datasets/quyuet/sp500-prices-data),
   [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/):
   6 selected histories, sampled from the CSV's explicit `Adj Close`
   field. Derived observations retain source attribution and hash. The archive
   ends July 11, 2025; its last session is excluded conservatively.

Each security uses one whole adjusted-return source path. There is **no level
stitching across providers**. The later archive is used only if it supplies
more complete actual annual paths. WIKI raw closes may independently support
historical valuation ratios on matching dates; where they are absent, the
quote remains null even if an archived adjusted return is available. Thus a
return index never masquerades as a historical market price for P/E.

Archive versions can differ in adjusted distributions. A check of the adopted
2022 ATVI series against 2020 agrees closely; the 2022 FRC series also removes
a conspicuous February–March 2017 anomaly in the 2020 archive and agrees with
WIKI for that interval. This is not a complete independent corporate-action
audit. Yahoo/WIKI adjusted close remains a **return proxy**; merger elections,
spin-off share distributions, cash-in-lieu, bankruptcies and terminal payouts
have not been reconstructed into a shareholder accounting ledger. Available
history selection still creates survivorship/availability bias.

## Bounded adjustment-quality audit

`quality_flags.json` pins seven unresolved observed-return disagreements with
the actual interval, each source's return, source URLs and archive hashes.
These concern Danaher/Fortive, Xerox/Conduent, Ventas/Care Capital Properties,
Expedia/TripAdvisor, ITT's separation, and separate unexplained archived/current
disagreements for NextEra and NiSource. For example, current Yahoo gives
Danaher +65.44% for June 30–July 29, 2016, while both independently archived
paths give approximately +6.36%. The importer does not guess a corrected value.

The seven selected dates are removed from playable `points`, retained in
`excludedObservations`, and explained in `qualityFlags`. Missing-date coverage
therefore blocks affected annual intervals. Xerox's pre-event December 30,
2016 observation is quarantined, preserving the clean January 3, 2017 entry
for the next holding period. Cold-cache rebuilds preserve this provenance.
These are specific unresolved cases, not a claim that every other corporate
action has been independently reconciled. Disagreements caused by comparing
different security eras were excluded from this audit rather than labeled
corporate-action errors.

## Reproduction and refresh

```sh
# Offline rebuild from cached inputs.
python3 scripts/annual_universe.py

# Explicitly update and re-pin membership/identity source files.
python3 scripts/annual_universe.py --refresh-sources

# Fetch missing or stale current histories, retaining successful old data
# if a refresh request fails. First refresh the SPY comparison calendar.
python3 scripts/annual_universe.py --refresh-prices --workers 5

# Optional recovery inputs for historical delisted prices.
python3 scripts/annual_universe.py --import-wiki /path/to/quandl-wiki.zip
python3 scripts/annual_universe.py --refresh-yahoo-archive
python3 scripts/annual_universe.py --import-apr2022 /path/to/FS_sp500_Value.zip
python3 scripts/annual_universe.py --refresh-2022-archive
python3 scripts/annual_universe.py --refresh-2023-archive
python3 scripts/annual_universe.py --import-jul2025 /path/to/sp500_prices_2009_2025.csv

python3 -m unittest tests.test_annual_universe -v
```

Provider caches are ignored by Git and should be persisted by the refresh
workflow's cache/artifact store: `prices.json.gz`, `wiki-prices.json.gz`,
`yahoo-2020-prices.json.gz`, `yahoo-apr2022-prices.json.gz`,
`yahoo-2022-prices.json.gz`, `yahoo-2023-prices.json.gz`, and
`yahoo-jul2025-prices.json.gz`. A cold CI rebuild may use the tracked reviewed
`universe.json` as a pinned whole-path fallback. A less complete fresh provider
path never replaces a more complete reviewed one; source fields, split basis,
and original edition provenance are retained together. No adjusted levels
are spliced across sources.

`universe.json` and `coverage.json` are the reviewed publishable snapshot;
a browser does not contact Yahoo or SEC to populate them. Source refreshes
produce a reviewable new edition before deployment.
Decision years extend only when both the observed trading calendar and dated
membership source support the next year; stale membership emits a warning.
