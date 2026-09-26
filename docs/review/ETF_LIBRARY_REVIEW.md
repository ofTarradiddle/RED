# ETF library review and shadow-processing boundary

Review date: 2026-09-22. Scope: site publishing, representative operational modules, source inspection, bounded offline regressions, and an independent equity snapshot comparator. This is not an exhaustive audit or a determination that the library is fit to run a fund.

**The original library was not generally correct or operationally complete.** Passing its original tests did not establish correctness: 21 relevant existing tests passed while independent examples reproduced accumulating NAV balances, partial mutation after rejected journals, false matches with no official NAV and mutated tax lots after rejected oversells.

## Corrections implemented

| Area | Correction | Behavioral consequence |
|---|---|---|
| Legacy shadow NAV | Absent official NAV remains unavailable; comparisons serialize as null. Percentage tolerance units corrected. Warnings cannot downgrade errors. | No fabricated successful reconciliation. Missing comparisons are excluded from statistics. |
| Accounting snapshots | `record_nav_entries` validates and archives a valuation snapshot; it does not post total assets/liabilities again each day. | Historical method returns an empty list. Opening balances, trades, income, expenses, capital flows and marks need proper event journals. |
| Journal integrity | All lines validated before mutation; finite nonnegative single-sided amounts; typed dates/decimals and journal history restored on load. Corrupt books are not silently reset. | Invalid entries cannot partially post; identifiers remain unique after reload. Persistence is still a prototype, not a transactional ledger service. |
| Legacy NAV | Explicit cash, shares and accrual/payable fields required; invalid/nonpositive shares and prices rejected. | Unpriced securities cannot silently become cash. Explicit zero is different from absent input. |
| Input files | Missing required files raise errors instead of becoming empty portfolios or zero financial balances. | An explicitly received empty file can represent no activity; absence is unavailable. |
| FMP adapter | Closing price instead of adjusted close; date/finite checks. Dividend recognition limited to its ex-date. | Payment clearing and idempotent event posting still need implementation. |
| Tax lots | Oversells, invalid quantities and unsupported methods rejected before mutation. | Rejected sales preserve lots and gains. Cost-basis method descriptions corrected. |
| Performance | Corrected sale-tax gain arithmetic and reinvestment basis in the simplified illustration. Aggregate same-ex-date distribution components; reject missing supplied feeds, invalid distributions and missing in-period NAV dates. Explicit `auto_adjust=False` for manual-dividend Yahoo branches. Corrected fund-minus-benchmark sign. | After-tax output is explicitly an illustration, not standardized N-1A after-tax performance. |
| Settlement | Current applicable US default T+1, historical default T+2; approved calendar required. | No empty placeholder trade feed can report complete. Trade-level provider integration remains unavailable. |
| Custom baskets | Removed fictional SEC overlap/deviation requirements and automatic purpose assumptions. | Numerical limits are optional internal policy settings. Named policy/reviewer/AP/cash evidence is required; no legal compliance certification is returned. |

**Do not reuse old saved ledger balances as if these changes repaired them.** The previous cumulative NAV posting may have inflated books. Reconcile or rebuild from independently verified opening balances and events. No historical accounting records were rewritten by this change.

## Independent equity shadow workflow

`lib/etf/shadow.py` is deliberately separate from the legacy orchestrator and from website publishing. It takes dated position/accounting snapshots and a quote set, then optionally compares an independently supplied provider snapshot.

The valuation is:

`securities + cash + dividend receivables + trade receivables + other receivables − accrued fees − trade payables − other liabilities`, divided by actual fund shares outstanding.

All balance fields are required, including explicit zeros. The current implementation supports a USD-base long-only equity portfolio. Cash is a balance, not a security. Non-USD imported quotes require a same-date FX rate and provenance. The optional Yahoo fetcher supports USD-quoted equities only; global listings require reviewed external FX and market-specific conventions.

Inputs require dates, security IDs, symbols, quantities, currencies, source labels and a corporate-action review assertion. Quotes require a matching session date, currency, source/fetch time and compatible share basis. Missing, stale, invalid or unreviewed observations block valuation. No fund accounting balance is inferred from Yahoo.

Provider comparison covers the union of security identifiers. Reports attribute differences to quantity, price, FX, each balance category and fund shares. Unexplained provider assets and NAV rounding differences stay visible. An absent official value is `unavailable`; inconsistent provider components are `provider_data_inconsistent`, not a match.

Reports embed the supplied input evidence, an engine fingerprint and a content-derived identifier. Complete records are created atomically; replaying identical inputs against the same engine preserves the first result. This is useful evidence for an internal prototype; it is not a tamper-proof archive or a retention system.

If the shadow positions and balances are copied from the provider, the check is independent only in its pricing/calculation, not a full independent reconstruction of the books. For stronger independence, derive those snapshots from your own verified fills, custody balances, capital activity and corporate-action records.

## What remains missing or unsafe in the legacy operating system

| Priority | Area | Remaining work |
|---|---|---|
| Critical | `core/orchestrator.py` | Scheduled trades can use ETF NAV instead of security execution price. Workflow order puts valuation before trade/action processing; some failures can still be summarized as completed. Do not use this orchestrator for live operations. |
| Critical | Trade and event accounting | Import real fills, fees, trade IDs, settlements and reversals. Persist event identity so repeat expense, income or capital runs cannot double-book. |
| Critical | Corporate actions | End-to-end postings for dividend ex-date accrual and payment clearing; splits; stock/cash mergers; spin-offs; return of capital; withholding; cash-in-lieu. The legacy action routines principally produce reports. |
| High | Settlement | Integrate actual trade-level cash and position settlement evidence; match amounts, quantities, fees and direction by trade ID. An aggregated holding is not settlement proof. Calendar and contractual settlement conventions must come from approved sources. |
| High | Reconciliation | Legacy holdings comparisons can be one-sided; cash comparisons may not be independent. The new comparator uses a union, but authoritative feed adapters and exception ownership are still needed. |
| High | Accounting reports | Several legacy reports use lifetime balances without properly limiting requested periods. Add dated ledger rollforwards, opening/closing controls and reconciled trial balances. |
| High | Performance | Legacy annual return aggregation and broad after-tax/tax-character assumptions remain unapproved. Use tested total-return methodology, benchmark provenance, actual inception/periods, reinvestment and approved tax treatment before public reporting. The website uses its separate demo calculation layer. |
| High | Execution/TA | Simulated fills or simplified AML responses must never be treated as real execution or clearance. Creation-unit sizes must be fund configuration, with accepted/settled shares reconciled independently. |
| High | Valuation policy | Stale/halted securities, unavailable market quotations, foreign market closes, fair-value decisions and review evidence need governed handling. A Yahoo quote alone does not establish an appropriate official NAV price. |
| High | Controls | Transactional storage, locking, access control, durable audit logs, backups, retention, exception assignment, sign-off and recovery from partial jobs. Current JSON files do not provide a complete operational control environment. |

## Yahoo-specific limits

Yahoo provides a secondary price observation, not official NAV, custody cash, expenses, fund shares, settlement confirmation or corporate-action entitlement records. `auto_adjust=False` avoids dividend adjustment, but historical `Close` can still be split-adjusted. The fetcher refuses histories with a reported split after the valuation date; archive reviewed daily quotes and validate share basis for historical replays. It cannot establish that Yahoo's corporate-action feed is complete.

Data licensing is an open business dependency. yfinance is unaffiliated with Yahoo and describes the API as intended for personal use. Calling a commercial process “internal shadow accounting” does not establish data rights. Obtain appropriate rights before operational use or redistribution. Yahoo outputs never feed the public demo publisher.

Sources: [yfinance documentation](https://ranaroussi.github.io/yfinance/), [split-adjustment discussion](https://ranaroussi.github.io/yfinance/advanced/price_repair.html), [Yahoo data guidance](https://uk.help.yahoo.com/kb/SLN2352.html), [SEC T+1 guidance](https://www.sec.gov/compliance/risk-alerts/shortening-securities-transaction-settlement-cycle), [NAV rule 2a-4](https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.2a-4), [valuation rule 2a-5](https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.2a-5).

## Validation scope

Offline tests cover the corrected economic/control failures, split value preservation, dividend receivable-to-cash payment, payable-to-cash settlement, same-date quote checks, missing provider records, security unions and a fully attributed NAV difference. They also exercise actual workbook import, changed workbook values reaching every holdings view, invalid-data rejection and preservation of the prior site release.

No live provider, NSCC, DTC, broker, custodian or fund-registration feed has been connected. No legal compliance, licensed data access, live Yahoo availability or exchange-calendar completeness is certified by these tests.
