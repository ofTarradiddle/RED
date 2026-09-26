# Hetzerk Asset Management local review site

A demo equity ETF website populated by one validated Excel workbook. The original site structure, ETF selector boxes, individual fund themes, investment cases, research articles and both Section 351 pages are preserved. The firm brand is Hetzerk Asset Management; REDI is the Hetzerk Innovation Factor ETF. All fund prices, portfolios, distributions, returns, fees and offering terms are illustrative; no legal registration is asserted.

## Run locally

```sh
python3 -m pip install -r requirements-site.txt
python3 -m publishing.build
python3 serve.py
```

Open <http://localhost:8080/>. The server binds only to loopback and serves `dist/` plus a local review calculator, never the source repository or internal accounting records. `sh start.sh` builds and serves in one command. The existing `npm run dev` / `npm run build` aliases also call this Python workflow; Node is not required for the site itself.

Click the plain word **Perspective** in the footer to open the personal shadow NAV calculator. The local server activates that word; static builds contain no private route or dashboard. It compares the REDI workbook portfolio with a constructed provider baseline, supports a security-price difference and new accrued fee, and attributes every difference through `lib/etf/shadow.py`. It does not fetch Yahoo prices or represent an actual administrator report. The page is available to users of this machine; the hidden entry is not password authentication.

REDI's expense ratio is **0.45% (45 bps)** in the canonical workbook. `/documents/` contains the populated fact sheet, data downloads and SEC filing references. Fund-specific document URLs can be supplied through the Documents sheet; reference links are not represented as filed fund documents.

The themed fact sheet is available at `/etfs/redi/fact-sheet.html`, with a matching
two-page download at `/etfs/redi/fact-sheet.pdf`. Each build regenerates the PDF
from the same fund snapshot, so scheduled data refreshes update both formats.
`publishing/fact_sheet.py` holds their shared investment narrative and intended
terms; `publishing/fact_sheet_pdf.py` handles print layout. The 50–100 stock target
is shown separately from current SPY-derived positions, and valuation and holdings
carry their own dates. The PDF dependencies are included in `requirements-site.txt`.

The corporate site offers REDI only. Shared public navigation and footer markup are applied by `publishing/institutional.py`; the scoped `assets/institutional*.css` styles give the fund, research and Section 351 pages a consistent presentation while preserving their content and data bindings. `assets/tactile.css` adds warm ceramic surfaces, raised burgundy cards and inset controls; `assets/tactile.js` progressively enhances selected clickable cards with pointer lighting and a subtle tilt, respecting reduced-motion and touch preferences. Its compact homepage uses warm light surfaces and blood-red accents, rendered by `publishing/minimal_home.py`, with scoped styles in `assets/minimal-home.css`. The Section 351 interest form follows the ETF introduction, ahead of expenses and the investment case; it prepares an email draft using the existing interest-form flow. The ETF page retains the original layout rendered by `publishing/restoration.py`, including its fund-detail panels, performance cards and document grid. The chart has NAV, Market Price and Morningstar US Market Index series, each indexed to 100 for the selected period, without reinvesting fund distributions. The workbook history remains fictional and covered by the illustrative banner. A verified actual Morningstar price-index history requires an authorized MSTAR data source; see `docs/SHADOW_NAV.md`.

The homepage leads with REDI’s objective, innovation value and ability, fund
details and investor resources; `assets/fund-home.css` styles this introduction.
The homepage and ETF overview include three interactive objective chapters:
the intuition behind innovation, what a lasting strategy requires and why now.
`publishing/objective_journey.py` translates the source arguments into native
explanations, with conceptual SVG diagrams in `publishing/objective_scenes.py`.
Selectable perspectives and diagram hotspots connect the explanation to the
knowledge network, range of possible outcomes and corporate reinvestment loop.
These diagrams do not encode measured returns or forecasts. Original slide images
retain their captions and full-size viewer inside source-material disclosures.
The matching CSS and JavaScript support keyboard controls, touch, reduced motion
and readable content without JavaScript. The shared masthead and
illustrative disclosure are refined by `publishing/masthead.py` and
`assets/masthead.css`, including the SPY-data build variant.
The investment case contains an interactive innovation journey derived from
slide 19 of the source presentation. `publishing/innovation_journey.py` holds its six
historical research eras, while `assets/innovation-journey.css` and
`assets/innovation-journey.js` provide the responsive timeline, keyboard controls
and optional touch navigation. Original SVG illustrations live in
`assets/innovation-objects.svg`. All chapters remain readable without JavaScript;
the eras are explicitly separated from live fund holdings and returns.

## Search metadata and public URLs

Local builds stay `noindex,follow`. They have current page titles, descriptions,
social previews and semantic headings, but do not assert a production canonical
URL. The local sitemap is empty. Crawlers are allowed to read the `noindex` tags.

GitHub Pages uses **GitHub Actions**, with `2026-sep-red` as the publishing
branch. `.github/workflows/pages.yml` checks and builds the website on each push
to that branch, then publishes only the generated output. Its root `index.html`
is the homepage; the repository README and source tree are not the website.
The `dist` symlink is materialized into `.pages` before uploading. Publication
uses the committed public data and does not wait for Yahoo or daily accounting
replay. The separate refresh workflow retains its accounting cache and can
publish refreshed public data when run on the same publishing branch.

The Pages workflow uses the actual `actions/configure-pages` `base_url` and
`base_path` outputs, and enables indexing for current public pages. It generates
absolute canonical URLs, social-image URLs, Organization/WebSite/WebPage data,
and a canonical-only `sitemap.xml`. Old URL aliases point to their current pages;
review utilities, errors and archived research drafts stay out of the sitemap
and retain `noindex`. The private accounting dashboard never enters the build.

To review a public configuration without deploying it:

```sh
python3 -m publishing.build --output /tmp/hetzerk-public-preview \
  --base-path /RED --site-url https://oftarradiddle.github.io/RED --indexable
```

Use the URL configured in Pages, including any repository path. For a custom
domain rooted at `/`, omit `--base-path`. The build rejects mismatched paths,
non-HTTPS URLs and indexing without a public URL. These settings prepare search
metadata; a local build does not deploy the site or submit it to search engines.
Search engines read `robots.txt` at the domain root. On a project URL such as
`/RED/`, the generated page-level directives and canonical URLs still apply;
the domain owner's root robots policy controls crawling, and the sitemap can be
submitted using its full `/RED/sitemap.xml` URL.

## Edit the workbook

The canonical input is **`workbooks/hetzerk-demo.xlsx`**. It is also available in the site's Review guide. Save edits to the canonical input, then run:

```sh
python3 -m publishing.build --workbook workbooks/hetzerk-demo.xlsx
```

Refresh the browser. The running server follows the new complete release without restarting.

| Sheet | Rows and units |
|---|---|
| Funds | One row per fund. Stable lowercase `fund_id`; rates as fractions (`0.0045` = 0.45%); `is_demo` must remain TRUE. |
| Daily Data | One row per fund/date. NAV, market price, synthetic benchmark index, net assets, fund shares, ex-date distribution/share. NAV × shares must equal net assets. |
| Holdings | One dated full portfolio per fund including cash. Actual typed quantities, local prices, USD FX and market values. Value = quantity × price × FX. Demo portfolio values must sum to demo net assets. |
| Distributions | One row per fund/ex-date, amounts/share split by character. Must agree with Daily Data. |
| Documents | Document type, title, HTTPS URL if a draft is available, effective date and status. Missing documents stay unavailable. |

Keep exact headers. Dates may be typed Excel dates or ISO `YYYY-MM-DD`; numeric values must be numeric cells. Blank and zero are different. Holdings and the latest daily observation must share a date. Recalculate formula cells in Excel and save before importing; the importer reads saved results and rejects missing formula caches. It does not calculate Excel formulas.

The validator rejects unknown/duplicate keys, missing fields, invalid dates, nonfinite values, inconsistent quantities/values, unreconciled assets and distribution mismatches. Validation/build failure leaves the prior release intact. `convert_data.py` is a compatibility entry point for the same publisher; it no longer writes disconnected root JSON files.

Each build generates one snapshot and renders the enabled fund pages, top holdings, full holdings, charts and CSVs from it. A source SHA-256 fingerprint connects them to the workbook. Releases are staged under `.site-builds/` and the `dist` symlink switches atomically. Old releases are retained locally for review; remove only known obsolete generated releases when no longer needed.

Only **Hetzerk Innovation Factor ETF (REDI)** is currently published. The other entries are commented out in `publishing/visibility.py`; their templates and workbook data remain intact. Uncomment the relevant fund ID to restore its pages, cards and data exports. The downloadable source workbook still retains all demo rows for future use.

## Project map

```text
workbooks/hetzerk-demo.xlsx   Canonical editable demo source
publishing/workbook.py       Workbook contract, validation and demo calculations
publishing/site.py           Shared static page templates
publishing/restoration.py    Original layouts, branding and workbook data binding
templates/                  Restored original pages and investment/research content
publishing/build.py          Complete release generation and atomic switch
assets/site.css              Shared responsive design
assets/site.js               Charts, periods, holdings search/filter/sort, mobile menu
assets/restored.css          Original red and theme/interaction refinements
assets/restored.js           Original navigation, interest forms and article controls
dist/                       Current public release (generated symlink)
serve.py                    Local public-directory-only server
lib/etf/shadow.py            Independent equity snapshot comparison
examples/shadow/             Fictional offline shadow/provider input examples
docs/review/                Regulatory review, library findings and workflow notes
legacy/                     Superseded HTML, Next.js and data scripts; never served
```

The old JSON in `etfs/*/data/` is retained only as seed/reference data. Editing it does not update the site. The former Next.js components are archived in `legacy/next/`. Historic operational documentation and historical test outputs do not override the current review findings.

`templates/` is the source for the restored page structure and editorial content. The publisher binds workbook values into data surfaces and applies targeted disclosure corrections. Preserve the original design when editing it. Tailwind utilities, Inter/Playfair fonts, icons and investment-case chart assets are served locally. Compiled styles are included; ordinary Excel updates require only the Python build. After changing utility classes in templates, run `npm install` then `npm run styles` (Tailwind 3.4.17), or use that version's official standalone CLI with the same configuration/input/output arguments.

Both `/section-351.html` and `/351-exchanges.html` retain their distinct opportunity cards and interest forms. The ETF collection has its original interest panel too. These forms prepare an email draft to the original `info@ofnectar.com` recipient for the visitor to review and send; the site does not transmit or store submissions. The other ETF cards, pages and launch concepts are temporarily paused; all three interest forms currently offer REDI only. Newsletter integration remains explicitly unavailable.

## Shadow the provider

Install optional library/quote dependencies with `python3 -m pip install -r requirements-shadow.txt` in your environment, then:

```sh
python3 -m lib.etf.shadow \
  --snapshot examples/shadow/snapshot.json \
  --quotes examples/shadow/quotes.json \
  --provider examples/shadow/provider.json
```

This example is entirely synthetic. See [the shadow workflow](docs/review/SHADOW_WORKFLOW.md) for the input contract and optional `--fetch-yahoo`. Reports are internal and never published by the site. Data rights, valuation policy and provider integration remain open requirements.

## Review findings and checks

The SPY allocation refresh and local accounting dashboard are documented in
[Shadow NAV](docs/SHADOW_NAV.md). Run `python3 -m scripts.refresh_spy --build` or use
the local dashboard's refresh button. **Refresh ETF data and site** in
`python-package-conda.yml` calls the refresh workflow on daily schedules, pushes to
`main`, and **Run workflow** after the supporting changes are pushed. It restores
and saves modeled accounting inputs, daily accruals and journals in Actions cache,
with a 90-day **shadow-accounting-snapshot** artifact for recovery and download.
Pages configuration is needed for site deployment, not cache persistence.
Only public-source modeled records enter these snapshots; supplied operating
records and the accounting page stay local. See the Shadow NAV guide for recovery
commands and cache-retention limits.

- [ETF library correctness and remaining gaps](docs/review/ETF_LIBRARY_REVIEW.md)
- [ETF website regulatory gaps and primary sources](docs/review/REGULATORY_GAPS.md)

Run the bounded offline regression suite:

```sh
python3 -m pytest tests/site tests/test_shadow_equity.py tests/test_library_safety.py \
  tests/test_accounting.py tests/test_administration.py tests/test_tax_lot.py \
  tests/test_performance.py -k 'not with_benchmark' -q -p no:cacheprovider
```

`tests/integration/` contains legacy routines that may fetch external data and write files. Do not interpret old “production ready” or “compliant” labels as operational assurance.

Validated on 2026-09-22: 110 offline regression cases passed; the live benchmark test was excluded. The build completed for five funds, JavaScript syntax passed, 25 public URLs returned HTTP 200 and five internal paths returned 404. A scan of 691 text/workbook files found no remaining old-brand references. Workbook previews were visually inspected. Browser interaction/layout checks and live Yahoo/provider connectivity were not verified.

The demo publisher intentionally rejects live-mode workbooks. A live release needs effective offering documents, verified identities, official data, licensed feeds, approved calculations, calendars, publication monitoring and provider/compliance review. Local builds do not deploy. The configured GitHub Pages workflow publishes the static site from `2026-sep-red` with Pages set to GitHub Actions.
