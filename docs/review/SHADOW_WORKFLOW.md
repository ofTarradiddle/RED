# Running an equity shadow comparison

## Personal local page

With `python3 serve.py --port 8080` running, click **Perspective** in the website footer. This plain-text entry is activated only by the loopback server; neither the route nor its HTML is included in the static release.

The page uses the latest published REDI workbook snapshot for 59 equities, cash and shares. A constructed provider baseline retains the workbook prices. The price control adjusts ABT's closing price for the shadow side; the fee control adds a new accrued liability. Matching both sides yields a zero unrounded NAV difference. The 45 bps expense estimate uses one calendar day on an ACT/365 basis and is applied only when selected. Provider cent rounding is shown separately from the tolerance check. These controls never change the workbook or public fund NAV.

Yahoo and real administrator records are not connected to this page. Use the evidence-preserving CLI below for received accounting inputs and external quotes. The private route is local-only, not password authentication.

The future service provider remains the authoritative source for official NAV and operational records. This workflow produces internal diagnostic reports; it never changes the provider's records or website data.

## Offline example

From the repository root:

```sh
python3 -m lib.etf.shadow \
  --snapshot examples/shadow/snapshot.json \
  --quotes examples/shadow/quotes.json \
  --provider examples/shadow/provider.json
```

The example uses fictional prices and accounts. Its $0.01/share difference comes from one $0.10 security-price difference on 100 shares divided by 1,000 fund shares. Reports are written under `data/shadow_reports/<date>/` and are excluded from website builds and Git by default.

Omit `--provider` to compute only the shadow estimate. The report will say `unavailable`, not matched. `--tolerance-bps 1` is the default comparison tolerance, configurable to your approved policy. A “within tolerance” result refers only to the supplied snapshots, not legal or operational approval.

## Required inputs

Use the example files as the contract. Replace every synthetic value with independently obtained, dated records:

1. Position snapshot: stable security ID, Yahoo symbol mapping, currency, actual quantity. Only equities; cash is in balances.
2. All balance categories, explicitly including zero: cash, dividend receivables, unsettled trade receivables/payables, other receivables, accrued fees and other liabilities.
3. Actual fund shares outstanding; creation/redemption activity must already be reflected consistently.
4. Corporate-action review: splits, distributions, mergers and entitlement changes must be reflected in share quantities and receivables/cash exactly once. The boolean is an input assertion, not independent evidence that the code verified those events.
5. Exact-session prices, currency, price/share basis and FX if needed.
6. Separate provider snapshot with provider name, official NAV, its reporting precision (`official_nav_decimals`), net assets, shares, positions with prices/FX and corresponding balances.

Reconcile the source records first. Never substitute an ETF's market price for NAV or a security execution price. Never treat a Yahoo dividend calendar as a custody receivable ledger.

## Optional Yahoo fetch

After reviewing data rights and your valuation policy:

```sh
python3 -m lib.etf.shadow \
  --snapshot path/to/actual-dated-snapshot.json \
  --fetch-yahoo \
  --provider path/to/actual-provider-snapshot.json
```

`yfinance` is an optional runtime dependency listed in `requirements-shadow.txt`. No API key is assumed. Live service access is external and may fail or change; failures do not become zero prices.

The fetcher requests `auto_adjust=False`, `back_adjust=False`, `repair=False`, verifies a unique exact date, verifies an equity instrument and USD currency, and refuses subsequent reported splits that would make a historical close incompatible with dated quantities. Same-day unfinished sessions are refused. This does not prove Yahoo's reported corporate actions are complete. Preserve daily reviewed quotes for historical comparison.

The live fetch helper is limited to USD-quoted equities. The offline quote contract can carry other currencies with a same-date FX source. Foreign trading calendars, close-time alignment, unavailable quotes and fair-value decisions require policy/provider support; they are not inferred.

Yahoo is not the source for the 30-day median NBBO spread or a public official-NAV feed. Confirm licensing for business use; yfinance's personal-use notice does not grant commercial data rights. See [the library review](ETF_LIBRARY_REVIEW.md) for sources and remaining gaps.

## Review the breaks

Reports retain signed differences for each security's quantity, price and FX; each cash/accrual/liability category; share-count effects; and unexplained provider residuals. Investigate a difference rather than automatically changing your books to make it disappear. Correct an input with evidence and rerun: changed inputs create a distinct report. Identical inputs against the same engine preserve the original complete report.

The raw difference from published NAV remains visible, including its rounding residual in the attribution. Economic comparison status uses the provider's unrounded net assets divided by shares (`unrounded_difference_bps`). Published NAV consistency is checked separately against half of its stated reporting unit. This distinguishes ordinary rounding from real accounting differences, including differences on opposite sides of the same rounded cent. The provider adapter must supply its actual approved reporting precision.

Production work still needed: feed adapters, independently maintained event ledger, corporate-action processing, approved calendars, data licenses, review ownership, exception workflow, durable retention and live provider reconciliation scenarios.
