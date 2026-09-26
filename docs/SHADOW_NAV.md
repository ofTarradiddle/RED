# SPY shadow valuation and accounting review

The local page is opened through the plain **Perspective** word in the footer,
or at `http://localhost:8080/perspective-7f3c9e/`. It is served by `serve.py`
and is excluded from every static Pages build. A hidden word is not authentication;
the actual boundary here is that the report is only served on the loopback server.

## Daily operating book: dividends and one unitary expense

The primary private view is now a prospective **REDI operating model using the
SPY starting basket**, with a single **45 bps (0.0045)** annual expense. It does
not import SPY's reported fee liabilities, historical expense categories,
aggregate net cash, reported dividend receivable, or a NAV balancing difference.
The March financial-statement comparison has been removed from the page. Existing
SPY source research and the reported-net-cash valuation check are collapsed
separately; neither provides operating balances to this book.

The saved opening is September 22, 2026 end of day, before the first September 23
accrual. It contains the published stock quantities, standalone holdings cash,
known gross opening dividend estimates, and explicit zero assumptions for fee,
trade and fund-distribution liabilities. Historical cost was not available;
initial carrying values use the first model close and are not tax cost records.
Fund units come from the opening date and remain unchanged without supplied
capital events. This is a starting model, not an assertion of SPY's actual books.

**Dividends:** full eligible quantity × dividend per share accrues once on the
ex-date (after effective splits and before ex-day purchases). Every subsequent
calendar day carries the unpaid receivable. A declared pay date transfers it to
modeled cash in `scheduled` mode; in `confirmed` mode only supplied receipts do
so. Partial receipts leave the unpaid balance outstanding. Payment creates no
new dividend income. An observed dividend without a pay date still accrues and
remains receivable. Unsupported actions stop the forward calculation for review.

**Unitary fee:** the chosen policy is closing net assets **after** the current
day's fee, ACT/365F, including weekends and holidays. Let B be independently
calculated pre-fee net assets, already net of prior exact accrued expenses:

```
exact daily fee = B × annual_rate / (365 + annual_rate)
```

This solves `fee = (B - fee) × annual_rate / 365`. The convention is an explicit
model choice; the expense ratio alone does not prescribe the base or day count.
`ACT/ACT` is also supported (366 in leap years), as are sourced effective-dated
`rate_changes`. Decimal precision carries across days. Each journal posts rounded
cumulative expense minus expense already posted, rather than discarding a
fraction of a cent each day. Debit expense, credit fee payable. A supplied
`fee_payment` debits the payable and credits cash without a second expense.
Other manual/category fee-accrual events are rejected when this policy is active. Fee payments are sequenced after that day’s accrual, so a month-end payment can clear the current day too.

The first September 23 model day records $6,745,256.19 dividend income,
$8,476,941.79 scheduled (unconfirmed) dividend cash, $588,318,997.77 closing
dividend receivable, and $9,938,099.28 unitary expense at the full SPY-sized
opening basket. These are model amounts, not the actual small REDI fund or
confirmed SPY operating books. The September 24 refresh also calculates $9,204,012.60 new dividend income and $9,935,638.53 daily fee, bringing the two-day fee payable to $19,873,737.81.

**Forward positions and cash:** the opening is preserved across refreshes.
New issuer holdings do not fabricate trades; new issuer cash does not reset the
ledger or re-add dividends. Quantities and units change only through explicit
supported events. The public website's SPY allocation continues refreshing daily;
the private forward portfolio is a separate book. Retained equities continue to
be requested for Yahoo prices and corporate actions even if they leave SPY.
A missing trading-session mark blocks advancement. Only exchange closures may
carry the last dated marks, and a split requires prices on the new share basis.
Repeated runs replay the same inputs and never append duplicate accruals.

**Operation and persistence:**

```sh
python3 -m scripts.refresh_spy --build       # holdings, prices, actions and books
python3 -m scripts.refresh_dividends --cached # recompute dividends and books
python3 -m scripts.accrue_daily             # books from cached market evidence
python3 -m scripts.accrue_daily --through 2026-09-27
```

The final command requires all intervening session prices; it will not invent
Thursday/Friday prices from Wednesday. Normal refresh extends through completed
closed-market calendar days after the latest available close. The GitHub workflow
now runs seven days per week. An outage catches up from the saved history, subject
to available closing marks. The fixed public seed in
`data/spy_seed/daily-model-inputs.json` preserves the original opening if a cache
is evicted; missing later session history then needs restoration, not a new zero
opening. Public-derived inputs, modeled journals and calculated reports are saved
in a dedicated accounting cache and a downloadable snapshot artifact, described
below. User-supplied operating records are excluded from both.
The workflow still needs to be pushed/activated; local edits do not schedule jobs.

For your eventual actual portfolio, provide
`data/shadow_spy/daily-accounting-input.json` using
`examples/shadow/daily-accounting-input.json` as the schema. Supply explicit
opening balances, dividend items, executions/corporate actions/receipts and dated
`price_history`; `fund_id` is `REDI`. An optional `cutoff` selects a supplied-book date independently of the public SPY report. The standalone replay supports trades,
settlement, splits, cash creations/redemptions and fund distributions. Supplied
mode defaults to confirmed payments and uses its own inputs independently of
public SPY source completeness. It does not silently populate missing true cash,
withholding or unsettled trades from holdings alone. In-kind baskets and complex
corporate actions still require explicit implementation before booking.

The local page shows daily balances, fee bases, accrued amounts, modeled versus
confirmed receipts, forward quantities and the balanced journal. Each run retains
its input hash, engine hash, input snapshot and engine files under the ignored
`data/shadow_spy/daily-book/runs/` directory.

Accounting references for the chosen conventions: ex-date dividend recognition
and daily expenses appear in [this SEC accounting-policy disclosure](https://www.sec.gov/Archives/edgar/data/1618627/000139834426008691/fp0096661-5_ncsrsixbrl.htm).
A [fixed-365 agreement](https://www.sec.gov/Archives/edgar/data/1414040/000119312515237197/d844686dex99d26.htm)
and a [365/366 agreement](https://www.sec.gov/Archives/edgar/data/1500604/000119312526054888/d24816dpre14a.htm)
illustrate why day count is a configurable assumption, not inferred from the ratio.

## Refresh

```sh
python3 -m pip install -r requirements-shadow.txt
python3 -m scripts.refresh_spy --build
python3 serve.py
```

The local page also has a **Refresh holdings, prices & daily accruals** button. A refresh may take
several minutes. Reload results after it finishes. A lock prevents simultaneous
refresh jobs. A failed download/schema/date validation keeps the published site.
An incomplete Yahoo response is retained as an explicitly incomplete private report,
while the public allocation can still update from the validated issuer holdings.

`--cached --build` rebuilds using the latest archived report without making network
requests. It does not make the source data newer. `python3 -m publishing.build
--workbook-only` removes the temporary overlay for that build.

## GitHub Pages

The **Refresh ETF data and site** workflow in
`.github/workflows/python-package-conda.yml` runs on pushes to `main`, supports
**Run workflow**, and schedules a refresh at 05:35 UTC every day. It calls
`.github/workflows/refresh-spy.yml`, which runs Python 3.11 and the repository's
actual dependencies; the original generic Conda template is replaced. Closed-market
days still accrue the unitary expense. GitHub may delay scheduled jobs. Dates on
the page remain the source dates; issuer snapshots older than five calendar days
are rejected.

Each run restores market evidence and the modeled accounting cache, refreshes
sources, replays the saved opening and events, and saves a new immutable cache.
The workflow serializes refreshes to prevent concurrent books from racing.
`data/shadow_spy/accounting-cache/` contains:

| Cached path | Contents |
| --- | --- |
| `inputs/daily.json` | Fixed opening, explicit events, dated prices and fee policy |
| `inputs/entitlements.json` | Frozen public-derived dividend quantities |
| `daily/latest.json` | Latest calculation attempt, cumulative daily rows and journal |
| `daily/latest-successful.json` | Last complete daily calculation |
| `dividends/latest.json` | Modeled dividend lots, accruals and scheduled payments |
| `runs/` and `engines/` | Up to 30 revision snapshots, input hashes and engine source evidence |
| `manifest.json` | Dates, scope and file hashes checked before restore |

Inputs are restored to `daily-book/public-model-inputs.json` and
`dividend-book/public-entitlements.json`; reports return to their corresponding
`latest.json` paths. Generated fees and payments are recalculated from those
inputs, never re-appended as new input events. The current daily report retains
the full cumulative history even when old revision snapshots expire.

An incomplete replay retains its inputs and diagnostics without advancing the
last-successful checkpoint. The job then fails before deployment so the previous
public release remains live. Missing Pages configuration also does not prevent
the accounting cache and backup from being saved.

Every saved accounting checkpoint is uploaded as the **shadow-accounting-snapshot**
artifact with 90-day retention. Open the Actions run, scroll to **Artifacts**, and
download it to inspect the journal and daily balances. If the cache is missing,
the next run automatically restores the newest unexpired snapshot for that branch.
The separate public market evidence artifact has 30-day retention.

GitHub caches can be evicted, including after more than seven days without access;
they are not a permanent archive. See [GitHub's cache retention documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).
If both cache and backup are gone, the committed public seed preserves the
original opening. Missing intervening trading-day prices must be recovered before
a complete replay can advance; the book does not silently restart at zero.
The bootstrap input currently includes the locally verified public price history
through September 24, 2026, with the original opening unchanged.

For local snapshots and recovery:

```sh
python3 -m scripts.accounting_cache export
python3 -m scripts.accounting_cache verify
python3 -m scripts.accounting_cache restore
```

To recover a downloaded artifact, unzip it to an empty directory and use
`python3 -m scripts.accounting_cache restore --cache-dir /path/to/snapshot`.
Restore refuses corrupt files, supplied operating books and date rollback over a
newer local daily report. Export refuses supplied input files, actual receipts,
documented entitlements and books derived from those records.

These caches and artifacts contain **public-source modeled accounting only**;
they are accessible to repository readers. Actual operating records and the
local dashboard remain excluded. Neither the accounting cache nor its journal
is included in the public Pages output. Keep actual fund records outside this
public-repository persistence mechanism.

To activate, push the updated workflows and their supporting code to `main`.
Open [Refresh ETF data and site](https://github.com/ofTarradiddle/RED/actions/workflows/python-package-conda.yml)
and select **Run workflow** for an immediate refresh. For website deployment,
select **GitHub Actions** in **Settings → Pages → Build and deployment → Source**.
No GitHub token is embedded in the site. Local edits alone do not activate this
workflow or populate GitHub's cache.

## Public REDI allocation

The Excel workbook still supplies fund terms, 45 bp expense ratio and illustrative
NAV/market-price/performance/distribution history. `data/spy_public.json` is a
generated, strictly allowlisted allocation overlay. It replaces common-stock
names and weights using SPY's current dated holdings. Weights are normalized to
the workbook's equity allocation (currently 98%); its cash allocation stays 2%.

The public prices are **inferred** from rounded issuer weight × issuer net assets
÷ issuer quantity. Quantities are rescaled to the workbook portfolio value. They
are not Yahoo observations or actual REDI executions. This keeps the original
illustrative site history and template while changing the holdings as requested.
The banner identifies the proxy, inferred prices and fictional history. The
holdings date and historical NAV date are shown separately. The chart compares NAV, Market Price and Morningstar US Market Index, each rebased to 100 at the selected period start. Fund distributions are not reinvested in this chart. The existing workbook benchmark history is illustrative, not downloaded Morningstar observations.

The verified actual price index is **MSTAR / Morningstar US Market PR USD**, SecId XIUSA0010F; **MSTART** is the separate total-return series. [Cboe’s EOD dataset](https://datashop.cboe.com/morningstar-mstar-channel-end-of-day-summary) supplies daily history from November 2022 by purchase/subscription. Its one-day sample is not a historical series. No usable free multi-year feed was verified. Supply authorized actual MSTAR levels in the workbook’s `benchmark_index` column before presenting the chart as real performance; the public Morningstar details endpoint does not confer commercial benchmark or redistribution rights.

The small SPY contingent-value right is excluded from the public equity-only
allocation and separately valued in the private SPY comparison. Country
and sector information missing from the issuer feed are not invented.

## Independent SPY comparison

Official inputs come from State Street:

- [Full daily holdings](https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx)
- [NAV, exact shares and net-assets history](https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-spy.xlsx)
- [Fund distribution history](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx)

The September 23, 2026 reconciliation is exact in dollars:

| Component | USD |
|---|---:|
| 503 stocks, independently priced | 803,800,922,501.09 |
| 2,578,626 Hologic CVRs × $0.01 | 25,786.26 |
| Issuer aggregate Net Cash Amount | 141,915,813.06 |
| Calculated and official net assets | **803,942,864,100.41** |
| Shares outstanding | 1,047,332,116 |
| Calculated NAV | **767.610246853549** |
| Published six-decimal NAV | **767.610247** |

The fixed inventory rule uses the **September 22 holdings file**, September 23 prices,
shares and net cash. The September 23 inventory produces a materially different result.
This is an observed feed alignment, not a confirmed issuer timing contract. The engine
never searches for the inventory that minimizes the difference. `exchange_calendars`
requires the exact previous XNYS session, including holidays, and handles early closes.
Archived workbook dates and hashes are validated. The current file supplies public
allocation; the prior-session file supplies this valuation check.

Stock quotes must have the correct date, symbol, USD currency and equity instrument
identity. Same-session decimal metadata is used only when corroborated by the raw
float32 closing bar at the scheduled close. Preserve fractional cents (CPRT is $28.865).
Do not substitute `previousClose` or `chartPreviousClose`: these can be dividend-adjusted.
Contradictory closing sources remain exceptions unless an identified same-date primary SPY5 holding exactly corroborates the fractional-cent Yahoo metadata quote and the raw daily bar exactly equals its cent-rounded float32 value. On September 24, CSGP ($27.855) and ALGN ($145.625) use this explicit corroboration, with both source files and hashes retained. No NAV value is used to select a price. Cache reads verify source hashes and
re-extract fields from the original bytes. Historical quotes after a subsequent action
need an explicitly reviewed share-basis correction.

The $0.01 CVR mark comes from the same-date [State Street SPY5 holdings file](https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spy5-gy.xlsx),
with security identity mapped separately. It is another fund’s published fair value,
not a Yahoo stock quote or SPY’s own security-level mark. The issuer’s dated
[Net Cash Amount](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy)
is used **once**, replacing the standalone USD holdings row. Do not add separate
dividend receivables or expenses on top of the aggregate. This is a constituents-plus-
aggregate-cash reconciliation, not independently replayed current operating books.
No price or balance is inferred from the official NAV to force a match.

Every run archives issuer files, the net-cash page, peer valuation, raw Yahoo responses,
parsed observations, source hashes and the calculation under `data/shadow_spy/runs/`.
The latest report is replaced atomically; earlier runs are retained. A matching cent
with an unpriced right is separately labelled, never declared fully matched.

The archived **March 31, 2026 filed accounting research** is retained locally but is no longer rendered or used by the daily book: 498 Yahoo prices
plus five independent GuideStone valuations reproduce NAV $650.39666637 versus filed
book NAV $650.39666781, both $650.40. All filed cash, receivables and liabilities are
present in that historical archive. The residual is −$1,427.51 across approximately $648.5 billion. Ten subsequent
Yahoo price-basis adjustments are reversed; 12 historical name mappings retain review
flags. Filed balances use filed shares, never the differently based NAV-history share
count. This validates closing arithmetic against unaudited books, not a trade-by-trade
reconstruction. Local source evidence lives in `data/shadow_spy/historical/`.

### Dividend payment schedules

Schedules come from [Nasdaq](https://www.nasdaq.com/market-activity/stocks/aapl/dividend-history),
retrieved [DividendHistory.org](https://dividendhistory.org/) tables and Yahoo’s raw
`calendarEvents/defaultKeyStatistics` fields. As of this review, 398 of 503 securities
have a usable schedule. The report includes ex-date, payment date, per-share amount,
declaration/estimate status, source and current-quantity cash-flow scenarios.

Nasdaq 403/429 responses stop further requests to that host for the run. Already
retrieved DividendHistory pages are reused; bulk scraping is not retried after its
rate limit. Raw Yahoo dividend date epochs are interpreted in **UTC**, avoiding the
library’s local-time one-day shift. Yahoo’s last dividend amount is accepted only when
its ex-date matches the current schedule; an old amount is never attached to a new
quarter. Missing schedules do not mean zero dividends. Source evidence is retained.

A source-calendar row alone is not a booked entitlement. The new forward book combines reviewed action rates with its saved positions to post ex-date accruals; scheduled cash remains explicitly modeled. Current holdings cannot establish past entitlement. Older split-adjusted amounts need complete action
history; historical cash-flow estimates remain unavailable until that basis is known.
Estimated dates stay unbooked, and scheduled dates never prove actual receipt.

SPY's official expense ratio is distinct from REDI's 45 bps. An expense ratio alone
does not establish actual accrued expenses or contractual daily invoices.

## Legacy SPY blotter replay

Public holdings changes cannot identify trades versus creations/redemptions or
corporate actions. The dashboard therefore does not invent an SPY execution
blotter. The standalone library walkthrough remains available as a test fixture, but the page now leads with the forward daily book.

The older `data/shadow_spy/accounting-input.json` interface remains available in the collapsed SPY comparison. Use the daily-accounting input described above for REDI’s daily unitary accruals. Its top-level fields are `opening`, `events`, `cutoff`, `prices`. See
`examples/shadow/accounting-input.json` for a complete, executable example.
Opening positions require quantity, total historical cost and opening carrying
value. Opening operating balances must be explicit. The balancing opening equity
account is an aggregate; it is not a classification of paid-in capital versus
retained earnings. Closing prices are required before the engine reports a NAV.

Supported event types:

| Event | Accounting |
|---|---|
| `trade` | Buy: debit securities, credit trade payable; sell: credit cost, debit receivable, recognize realized gain/loss. Uses average cost; actual tax lots are not implemented here. |
| `settlement` | Clears a referenced trade payable/receivable against cash; partial settlement supported. |
| `dividend` | Ordinary ex-date entitlement uses pre-trade shares; debit net receivable, credit gross income, expense nonrecoverable withholding. |
| `dividend_payment` | Requires verified pay date and action ID; debit cash, credit receivable. No second income recognition. |
| `split` | Multiply quantity by ratio; total cost unchanged. Fractional quantity remains until a confirmed cash-in-lieu event is implemented. |
| `fee` | Legacy standalone replay only: named fee and supplied base. Rejected by the new daily unitary-fee replay. |
| `unitary_fee` | Generated once per calendar day from independently replayed net assets. Exact accruals accumulate; cent postings use cumulative rounding. |
| `fee_payment` | Clear the accrued liability against cash without another expense. |
| `creation` / `redemption` | Cash-only confirmed capital flows adjust ETF shares and equity. In-kind baskets reject until explicitly implemented. |
| `fund_distribution` | Explicit documented eligible ETF shares × per-share amount creates a distribution payable and reduces equity. |
| `fund_distribution_payment` | Clears that payable on/after the supplied pay date. |

Each event needs a unique `id`, ISO `date` and `source`; trades may include an
explicit same-day `sequence`. Replaying an unchanged file is deterministic.
Duplicate event IDs reject. An exception leaves the caller's inputs untouched.

Yahoo dividend records supply ex-date/amount reference observations, not verified
pay dates or historical entitlement quantities. They are never automatically
booked against today's holdings. Yahoo is not a complete corporate-action source.
Special dividends/due bills, mergers, spin-offs, tender offers, return-of-capital
reclassifications, in-kind flows, tax-lot selection and FX require additional
event implementations and source records. Unknown events reject rather than
silently pass. Opening receivables/payables can be valued but their payments need
an action/trade subledger; this initial replay only settles actions created in its
event stream, plus explicitly itemized opening dividends. It is an accounting test harness, not a replacement fund administrator.

## Verification

```sh
python3 -m pytest tests/site tests/test_shadow_equity.py tests/test_daily_spy.py tests/test_spy_reconcile.py tests/test_dividend_calendar.py tests/test_dividend_receivables.py tests/test_daily_accruals.py tests/test_ledger_replay.py -q
```

Tests cover dividend entitlement and price drops, payment neutrality, splits,
settlements, fees across weekends, duplicate events, opening carrying values,
cash creations, fund distributions, missing inputs and the public/private boundary.

## Independent constituent dividend subledger

The SPY source-research disclosure contains **Dividend receivable — independent calculation**, below the new daily operating book.
This calculation does not take reported SPY dividend receivables, aggregate net cash,
net assets or a NAV residual as an entitlement input. The original exact NAV bridge
remains separately labelled **NAV with reported net cash**.

September 23, 2026 research result:

- 118 known outstanding scheduled events; all 118 have a calculated gross amount.
- $588,318,997.77 gross model subtotal, with historical quantity estimates explicitly
  identified. This is not a verified total SPY receivable.
- Three published pre-ex-date share observations support $80,701,186.19 of that total:
  NVDA 295,823,720 × $0.25 = $73,955,930.00; LRCX 15,147,637 × $0.33 =
  $4,998,720.21; CINF 1,858,017 × $0.94 = $1,746,535.98. NVDA's dated quantity
  is a retained search-index copy of the issuer page; the other two come from the
  original September 22 XLSX. Source timing remains subject to trade/custody checks.
- All 503 stocks have separately retrieved corporate-action histories. A valid
  no-event response is not proof that a security never pays dividends. There are
  393 historical dividend observations in the requested window without usable pay
  schedules; their outstanding status is unknown. A complete opening balance cannot
  be asserted from this finite lookback.

Each lot is identified by security ID, ex-date, currency and cash component. The
engine uses documented eligible quantities when supplied, then a published immediately
pre-ex-date snapshot. If unavailable, it separately estimates initial entitlement as
current basket quantity / anchor ETF shares × pre-ex ETF shares, reversing subsequent
splits. This assumes a stable basket per fund share: index changes, trading and source
capital-basis differences can make it wrong. It is never relabelled as observed shares.
Estimated quantities are **frozen after first calculation**. Future creations,
redemptions, sales or splits do not rescale a dollar receivable already earned.
New documented evidence can restate a quantity/rate with old and new values recorded.
Removed stocks retain their outstanding lots. Conflicts quarantine calculations while
preserving the prior entitlement archive, rather than deleting or writing off claims.

The engine restores Yahoo historical dividend amounts to event-date share units using
subsequent simple splits. An ex-day split adjusts the pre-ex snapshot before multiplying
by the event-date dividend. Complex spin-off adjustment factors need review. Primary
issuer evidence corrects APH from an erroneous $0.25 to $0.125 post-split, and preserves
fractional-cent declaration precision for DOC, CCI, ES, XEL, GPC, VRT and HPE. Matching
rounded Yahoo fields alone cannot establish full declared precision.

HPE's issuer table conflicts with its record date. The engine retains that conflict
and uses an explicitly **NYSE-rule-derived September 17 ex-date**, supported by the
SEC regular-cash declaration, NYSE Rule 235/T+1 guidance and the complete September
exchange exception report (no HPE-specific exception). This is a documented derivation,
not a claim of an HPE-specific exchange notice. Evidence and hashes are retained in
`data/spy_seed/dividend-confirmations.json` and `data/spy_seed/dividend-evidence/`.

Payments have two distinct treatments:

- A confirmed partial/full receipt reduces the lot and credits its receivable; it does
  not recognize income again. Duplicate IDs, overpayments, wrong currencies, missing
  action IDs and payments before the scheduled date reject.
- The separate expected-payment book assumes the remaining amount arrives on the
  scheduled date. It never changes confirmed cash. Without a receipt, the original
  receivable remains unpaid/overdue in the book before payment assumptions.

Unknown withholding is **gross-only**, not evidence of zero tax. Supplied withholding
and recoverable tax are separate fields and survive frozen replay. Recurring cash
classification does not establish ordinary-income tax character. AP dividend-equivalent
cash/equalization is not new issuer-dividend income and is not rescaled into these lots.

### Run and provide records

```sh
python3 -m scripts.refresh_dividends          # action refresh + independent subledger
python3 -m scripts.refresh_dividends --cached # deterministic archived-input replay
python3 -m scripts.refresh_spy --build        # holdings, prices, dividends and site
```

The local refresh button and daily GitHub workflow call the dividend calculation.
Successful current-day closing data can run after the exchange close plus a 15-minute
grace period; half-days use their actual exchange-calendar close.

Supply `data/shadow_spy/dividend-inputs.json` with `entitlements` and `receipts`; see
`examples/shadow/dividend-inputs.json` for the schema (its assumed values must not be
used as SPY data). Eligible quantity is in **ex-date share units**. Entitlement IDs must
match an existing security/action. Record source references and exact withholding or
reclaim amounts, and only label receipts confirmed when supported by cash records.
The general accounting replay also accepts `opening.dividend_items`; those outstanding
items must sum to opening `dividend_receivable` and can then be settled without new income.

Private state, journal, inputs, frozen quantities and prior reports are stored under
`data/shadow_spy/dividend-book/`. GitHub persists public source histories, frozen
public-derived quantities and the modeled dividend report through the validated
accounting cache above. Supplied entitlements, confirmed receipts, tax records
and private HTML are excluded. Ex-date observations accumulate daily.
A complete independent historical SPY book still needs the missing pre-ex quantities,
opening unpaid items, corporate-action/flow details, tax treatment and receipt records.
The public sources reviewed do not provide that complete historical ledger; State
Street's full AP basket/cash files require authorized access.

The new NAV component table uses independently priced securities + standalone holdings
cash + calculated gross dividend subtotal. It then shows the remaining other balances
as a diagnostic only. It never adds these dividends to issuer aggregate net cash and
never posts the displayed residual to force NAV to match.

If `data/shadow_spy/accounting-input.json` exists, identify the portfolio with top-level
`"fund_id": "SPY"` before using it in this SPY test. The dividend engine can derive
eligible quantities from that file's opening positions, executions and supplied
splits, processing ex-date entitlement before that day's trades. Unsupported in-kind
or complex position changes reject. Explicit entitlement quantities must agree with
the derived blotter quantities. A subsequent sale does not erase a receivable already
earned. Confirmed cash receipt input remains separately documented; dates alone are
never treated as receipts.
