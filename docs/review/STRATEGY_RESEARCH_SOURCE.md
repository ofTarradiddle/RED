# Source audit: strategy research comparison

## Chosen monthly source

Read-only input: `/Users/dbe/Downloads/monthly_levels_complete_2003_2019 (2).xlsx`.
The `(1)` copy has the same binary hash and contents. Despite its filename, the
worksheet runs through August 2026.

SHA-256:
`e3a7fb267cc88179b1a0f5d428c7b6c12403021bdf6d60a79cd35cd79c01303f`

Worksheet: `monthly_levels`, header row 4, source observations in rows 5–285.
There are **281 complete, consecutive calendar month-end observations** from
2003-04-30 to 2026-08-31. Every source series begins at 1. These are cumulative
growth levels, not percentage returns, daily prices, or log-return increments.
The initial observation is a baseline; there are 280 monthly return intervals.

The workbook's own source note is:

> Source: uploaded screenshots; source Excel rows 2–282; 281 monthly observations; overlaps reconciled.

The two-decimal numbers are a transcription of spreadsheet cells supplied in
screenshots. They are not newly digitized from the plotted line. They are also
not an original full-precision export from the strategy's accounting or research
engine. The complete original screenshots and underlying portfolio-level run
were not available for a separate reconstruction.

## Match to the opening exhibit

`/Users/dbe/Downloads/innovation_exact_5.zip` contains `README.md` and
`performance_art_audit.json`. Both identify this precise workbook hash, date
range, count and series mapping as the source of the performance artwork. The
audit’s five final levels match the actual workbook cells exactly:

| Published ID | Label | Source column | Last level |
|---|---|---|---:|
| INNOVATION_LEADER | Innovation Leader | inno eb | 48.08 |
| LAGGARD | Laggard | rd_other | 15.73 |
| MARKET_BACKTEST | Market Backtest | mkt | 13.37 |
| MARKET_EQUAL_WEIGHT | Market Equal Weight | mkt ew | 13.04 |
| NON_RD | Non-R&D Payers | non_rd | 11.00 |

Using 280 monthly intervals, `ending_level ** (12 / 280) - 1` independently
produces 18.054947% for Innovation Leader, 12.535197% for Laggard and 11.753922%
for Market Backtest. These agree with the opening exhibit's approximate headline
CAGRs (18.05%, 12.53%, 11.75%), allowing for the exhibit’s rounding/truncation.
No headline CAGR is imported as a substitute for the actual monthly path.

The workbook has a **separate `inno` variant**, ending at 42.02 rather than 48.08.
The supplied art audit explicitly maps its Innovation line to `inno eb`, and says
`inno` was excluded. The import follows that existing exhibit mapping; it does
not select a replacement series based on a new performance search. The three
concentration variants (`150 75`, `200 100`, `250 125`) are also left out of this
five-series comparison. They remain in the original workbook.

## Other source exhibits must stay separate

`DBE Innovation Factor ETF.pptx` contains no `ppt/charts/` or
`ppt/embeddings/` files. Its plotted histories are artwork, rather than embedded
Excel chart data. Slide 17 does contain a native annual table with 24 year rows
and five series. Every one of its 120 numeric values is also present in page 17
of `DBE Innovation Factor ETF.pdf`.

Some Innovation Leader annual results closely reconcile to the rounded monthly
levels: 2025 is 22.134647% from the workbook against 22.14% in the table, and the
2026 partial period is 29.282065% against 29.28%. However, the benchmark labels
and values do not line up: workbook `mkt` gives about 9.92% in 2025 while the
native table's `MKT` is 18.03% and `MKT EW` is 9.83%. The horizon table on slide 15
also reports a different all-period strategy figure (16.8%). No benchmark
identity, extra precision or unified track record is inferred from these
inconsistencies.

`monthly_levels_2002_2026.xlsx` is another available workbook with different
headers, dates and ending values; it is not substituted for the hash-matched
opening-exhibit source. The repository's legacy innovation scripts reference
`data/research/sp500_backtest` and related source directories, but the matching
underlying outputs were not found in this checkout. Their code alone does not
establish the provenance of this exhibit's series.

## What publication establishes

Publication faithfully preserves the reviewed monthly source values. It does
**not** establish dividend treatment, gross/net fee status, trading costs,
rebalancing assumptions, constituent-history quality, point-in-time controls,
survivorship treatment or investability. The source is hypothetical research,
not actual ETF NAV, market-price or operational performance.

`Market Backtest` deliberately retains a generic research label. It is not
relabeled as SPY, S&P 500 or Morningstar US Market Index. A ratio of two source
levels can be calculated, but source rounding limits precision; daily risk
statistics cannot be inferred from this monthly data.

Only `data/strategy_research.json` is public. The raw workbook and archive are
not copied into the repository or deployment. Unknown fields and untrusted
metadata are removed by `validate_payload`; all public titles, labels, URLs and
methodology are generated from reviewed code constants. The source hash pins
this import but is not authentication for data submitted by a client.

A separate observation digest pins all 1,405 published levels, so changing an
interior month while retaining the workbook hash is also rejected. The digest
was computed directly from the hash-validated workbook import:
`72c376d4e928e624735ba98ba105c83791d2d9c7a40a18de098321270fa56e4f`.
Its canonical ASCII records contain series ID, tab, ISO date, tab, level with
exactly two decimal places, and a newline, in the table's series order and then
chronological order. Equivalent JSON numbers such as `1` and `1.0` therefore
have the same digest. This protects source preservation, not the validity of
the underlying investment methodology.

## Reproduce

The importer uses Python's standard library and never modifies the source:

```sh
python scripts/import_strategy_research.py --source '/path/to/monthly_levels_complete_2003_2019 (2).xlsx'
python -m unittest tests.test_strategy_research_import
```

A changed workbook hash is rejected pending source review. The validator checks
all five series identities, alignment, complete month-end chronology, positive
finite levels, source precision and known endpoints. Missing values are not
filled. The observation digest additionally verifies every interior source
level. No daily observations, distributions, fees or post-August-2026 returns
are generated.
