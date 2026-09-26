# ETF website regulatory review

Review date: 2026-09-22. US proposed equity ETF context. The review uses current primary sources; applicability and final language require the actual offering facts and qualified review. The site is an illustrative demo, not an approved financial promotion or registered offering.

## Changes made in the local review

- Persistent demo labeling, no claimed actual fund track record, and source dates on all data views.
- Removed unverified SEC/adviser-registration assertions, fictitious contact details, purported SIPC protection and invented distribution-entitlement cutoffs from the generated site.
- Missing prospectuses, SAI and reports are unavailable; no misleading PDF links.
- Synthetic benchmark labeled as such. Distinct NAV/market total-return calculations with reinvestment, explicit missing periods and annualization labels.
- Full holdings and downloads share one validated dataset, with identifiers, quantities, country/currency and weights. Synthetic identifiers are explicit.
- Premium/discount line history and counts for completed calendar periods. Spread unavailable because no intraday NBBO feed is supplied. No unsupported assertion that a deviation event never occurred.
- Conditional Section 351 educational text replacing blanket tax-deferral promises.
- No manufactured Form CRS, disciplinary-history statements or legal-entity identity.
- Public release limited to `dist/`; internal code, source data and shadow reports are excluded.

These changes remove misleading demo behaviors. They do not make the site ready for a live offering.

## Live publication dependencies

| Topic | Requirement or decision | Current status |
|---|---|---|
| Offering and identity | Confirm adviser legal name/registration, trust and series, ticker/exchange, offering stage, distributor and approved contact details. | Unverified. Hetzerk is the requested display brand; no legal name change is inferred. |
| Daily holdings | For a transparent ETF relying on Rule 6c-11, disclose prior-close portfolio holdings each business day before regular exchange opening, including ticker/identifier, description, quantity and weight as applicable. | Demo template has fields. Provider feed, completeness checks, exchange calendar, cutoff, publication monitor and historical archive remain needed. |
| Daily trading metrics | Prior-business-day NAV, market price and premium/discount under an approved market-price convention. | Synthetic demo only; no official administrator/exchange feed. |
| History | Premium/discount table counts and line graph for last completed calendar year and completed quarters thereafter, or shorter fund life. | Demo period grouping implemented. Real session completeness and required-history retention unverified. |
| Bid–ask spread | 30-calendar-day median relative NBBO spread using 10-second observations, with prescribed calculation/rounding. | Unavailable. Daily Yahoo OHLC cannot compute this requirement. Obtain approved intraday observations or reviewed provider output. |
| Deviation explanations | A deviation over 2% for more than seven consecutive trading days triggers explanation/publication and at least one-year retention. | No reviewed live exception register. Detection across trading sessions, explanation approval, publication and expiry controls remain needed. |
| Advertising performance | Determine Rule 482 applicability; actual inception/history, standardized periods/prominence, reinvestment methodology, expenses, legends, dates and current month-end access. After-tax requirements may apply alongside tax-management claims. | Demo calculations are explicitly unapproved. A banner is not a substitute for offering-stage requirements, including applicable “Subject to Completion” wording. |
| Benchmark | Appropriate broad-based market index and total-return convention; licensed source and consistent naming. | Clearly synthetic benchmark. No licensed Morningstar data represented. |
| Documents | Current applicable prospectuses, SAI, annual/semiannual reports, additional N-CSR information and required quarterly complete holdings. | Unavailable until actual documents, effective dates, hosting/delivery requirements and update owners are verified. |
| Adviser retail business | Determine whether Form CRS is required for the actual retail investor relationships; if applicable link the current filed document prominently. | No invented CRS. Managing an ETF alone does not establish applicability. |
| Distributor review | Establish applicable FINRA-member approval, recordkeeping and filing arrangements. | No distributor approval represented. |
| IIV | Confirm particular listing/exemptive requirements. Rule 6c-11 itself does not universally require IIV. | No invented mandatory 15-second feed. |
| Section 351 | Control, investment-company/diversification exceptions, consideration, basis and taxpayer facts require transaction-specific tax review. | Educational wording only; no exchange or tax-deferral offer. |

### Primary sources

- [17 CFR 270.6c-11](https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.6c-11): definitions and `(c)(1)` website conditions; `(c)(3)` custom baskets; `(d)` records.
- [SEC ETF compliance guide](https://www.sec.gov/investment/exchange-traded-funds-small-entity-compliance-guide): accessible summary of reliance conditions and custom-basket policies.
- [SEC adopting release](https://www.sec.gov/files/rules/final/2019/33-10695.pdf): spread calculation, premium/discount event explanation timing (p.104 n.355), and IIV discussion (pp.61–65).
- [Rule 482](https://www.ecfr.gov/current/title-17/chapter-II/part-230/section-230.482): prospectus/advertising legends, performance presentation, currency and after-tax requirements.
- [Form N-1A](https://www.sec.gov/files/form-n-1a.pdf): Items 4, 26 and 27A. Prospectus bar-chart obligations are not a blanket requirement to label every website chart “SEC-required.”
- [Rule 498](https://www.ecfr.gov/current/title-17/section-230.498): website availability and format when relying on summary-prospectus delivery.
- [Rule 30e-1](https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.30e-1): shareholder reports and related website information, including fiscal-quarter portfolio holdings. EDGAR alone is not the prescribed website substitute.
- [Form CRS instructions](https://www.sec.gov/files/formcrs.pdf) and [SEC staff observations](https://www.sec.gov/newsroom/speeches-statements/staff-statement-form-crs-disclosures-121721).
- [FINRA Rule 2210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2210): communication requirements for applicable FINRA members, not a universal direct obligation on every adviser website.
- [IRS Publication 542](https://www.irs.gov/publications/p542) and [26 CFR 1.351-1](https://www.ecfr.gov/current/title-26/section-1.351-1): qualifications/exceptions for contributions. Ordinary ETF creations/redemptions are not universally tax-free under Section 351.

## Custom-basket library

The old library treated fixed overlap/value thresholds, membership in a standard PCF and a presumed tax-optimization purpose as regulatory tests. That was incorrect. The revised module records configurable internal checks and explicit adopted-policy/designated-review evidence. It returns `legal_compliance: not_determined`. Actual procedures, designated roles, deviations, AP agreements and required basket records/retention must be implemented with the provider and compliance team.

## Release boundary

The workbook publisher currently rejects `is_demo=FALSE`. A live release is a separate implementation requiring the records and controls above, plus an approved factual/legal content review. No live site was published by this work.
