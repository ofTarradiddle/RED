# Innovation history data

This is a historical learning exhibit, with a deliberately distinct curated
narrative layer and a larger discovery catalog. It is not an exhaustive list of
inventions, a survivorship-free backtest, or a causal model of innovation returns.

## Inputs and refresh

- `data/innovation/assets.json`: reviewed issuer identities. A manufacturer or
  developer is not automatically the original inventor. Historical ownership of
  catalog products is not independently reconstructed.
- `data/innovation/milestones.json`: curated events, original source links,
  attribution roles, editorial decision questions, and separate retrospective
  spillover explanations. Exact-day and year-only dates remain distinct.
- `data/innovation/price-cache.json.gz`: Yahoo daily Close, Adj Close and split
  events, retained for reproducible resampling. No interpolation, backfill,
  pre-IPO quotes, or synthetic terminal losses are generated.
- `data/innovation/catalog-cache.json`: Wikidata CC0 manufacturer/developer-linked
  dated products/software. Earliest eligible inception/publication date per item
  and company; original date precision retained. Repeated releases and multiple
  date claims do not inflate the count. A product family, model, software release
  or game is a catalog record, not a verified independent invention.
- `data/innovation/facts-cache.json`: annual SEC US-GAAP facts with fiscal period,
  filing date, accession and units. Missing custom tags remain unavailable.
- `data/innovation/dataset.json`: the public browser payload. It contains only
  sampled prices, eligible financial cards and public historical content.

With the project shadow-data Python environment/dependencies installed:

```sh
python scripts/refresh_innovation.py
python scripts/refresh_innovation.py --offline
python scripts/refresh_innovation.py --skip-catalog --skip-facts
```

The first command refreshes public sources and atomically persists their caches.
The second is deterministic in economic content and needs no network. The last
updates market histories while retaining the researched catalog and filed facts.
Source failures keep any prior cache, explicitly marked stale. A static GitHub
Pages visit does **not** execute this script; run it locally or in a workflow and
publish the rebuilt dataset. Keep catalog refreshes infrequent: the public
Wikidata service is shared. The script limits concurrency to two requests.

## Return calculations and security boundaries

Each security uses USD quotes for the explicitly mapped Yahoo ticker. The public
payload retains month-end quotes, the first observed quote, and genuine quotes
on every global game execution date. Ratios of Yahoo **Adj Close** provide a
vendor proxy for nominal returns with distributions reinvested. Do not add cash
dividends or stock splits to that ratio a second time. `close` is itself adjusted
for later splits and is not necessarily the unadjusted dollars-per-share quote
printed in a historical newspaper.

The series is not a separately reconstructed shareholder ledger. Spinoffs,
mergers, changing ADR ratios and vendor corrections require additional audit
before this can become research-grade attribution. IBM, GE and HP are examples
where corporate lineage and a current ticker should not be conflated with every
historical business. Foreign firms without a verified USD share-class mapping
stay visible in history but have no manufactured investment return.

Kodak's original common shares were cancelled in September 2013. Today's KODK
shares are a different claim. The Kodak case therefore has no stitched return
history and cannot be purchased in the game. This missing history is not recorded
as a zero. [Kodak's SEC-filed emergence announcement](https://www.sec.gov/Archives/edgar/data/31235/000119312513355259/d592194dex991.htm)
provides the cancellation evidence.

SPY begins only with its actual 1993 observations; the game comparator holds cash
before an available benchmark quote. Cash earns zero. No current index members
are silently projected back into the 1960s.

## Decision timing and historical financial cards

The execution date is the first actual security close **strictly after** the
reported event. This conservatively avoids assuming an announcement preceded the
same day's closing auction. A year-only event waits until after December 31.
Private research dates do not automatically make information investable. The
1966 DRAM concept, for example, waits until after the source-dated 1968 patent
year; `informationAvailableAt` can delay the decision beyond the invention date.
The payload keeps `originalDate`, canonical `eventDate`, `datePrecision`, and the
actual game `date`. Cases without a quote within seven days of the event cutoff
remain historical exhibits but are not purchasable at that milestone. No earlier
monthly close is used to trade on later information. All securities retain
quotes on every game execution date so an existing position can be rebalanced.

Only 10-K/10-K-A annual facts filed **before** the execution date are eligible;
future restatements cannot leak into an earlier decision. A fiscal period more
than 550 days old is excluded. The full-year P/E is price divided by the latest
filed annual diluted EPS; it is **not** forward P/E or necessarily trailing twelve
months. Historical quote units are translated into the EPS period's split basis
using vendor split events. If a split between fiscal end and filing makes that
basis ambiguous, the ratio is unavailable. Negative or zero earnings produce
`pe: null` and an explicit explanation, never a misleading negative multiple.

R&D is company-wide annual accounting expense, not the cost of the individual
innovation. R&D / sales is shown only for matching fiscal periods. Revenue tags
are selected from standard GAAP concepts; custom tags are not interpreted as
zero. Filing dates and links accompany each card. P/B, P/S and market
capitalization remain unknown unless separately researched; current ratios are
never backfilled into historical cards.

Decision questions and investment theses are labeled editorial reconstructions,
not quotations or archived forecasts. Retrospective outcomes are separate fields
so the game can reveal them only after a decision.

## Scope, provenance and rights

The snapshot includes an archive content hash in `version`. Saved games use the
engine’s canonical game fingerprint over prices, decision evidence, dates and
rules; retrieval timestamps alone do not invalidate a save. A changed economic
history cannot silently replace an existing game edition. `coverage` separates
curated milestones, unique catalog items, item/company records, sampled return
observations and playable cases. A price observation is never counted as an
innovation. The corpus is selected and tilted toward surviving firms and
technology products. It should not be described as "all major innovations."

Sources are linked at the event/record/financial-card level. Wikidata is a
community-maintained CC0 discovery source; those thousands of catalog records
are explicitly unreviewed individually. Company histories can be self-serving;
curated attribution avoids adopting unsupported "first ever" marketing claims.
Innovation often involves several research teams, suppliers, public research,
and later commercializers.

Yahoo data is currently used for development research. A suitable data license
and a stronger corporate-action audit are needed for a commercial data service.
Wikidata's license does not confer rights to another provider's prices.

- [Wikidata data access and CC0](https://www.wikidata.org/wiki/Wikidata:Data_access)
- [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Yahoo historical-price adjustments](https://help.yahoo.com/kb/SLN28256.html)
