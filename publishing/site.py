"""Shared, dependency-free static templates for every public review route."""
from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = "Illustrative demo · Not actual fund performance · Proposed terms subject to change"


def esc(value):
    return html.escape(str(value), quote=True)


def money(value, digits=2):
    return f"${value:,.{digits}f}"


def pct(value, signed=False):
    return f"{value:+.2%}" if signed else f"{value:.2%}"


def frame(title, description, body, data=None):
    payload = ("<script id=page-data type=application/json>" + json.dumps(data, allow_nan=False).replace("<", "\\u003c") + "</script>") if data else ""
    social = ''
    if title == 'Equity investing, considered.':
        social = '<meta property="og:image" content="http://localhost:8080/assets/hetzerk-social.png"><meta name="twitter:image" content="http://localhost:8080/assets/hetzerk-social.png">'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{esc(title)} | Hetzerk</title><meta name="description" content="{esc(description)}"><meta property="og:title" content="{esc(title)} | Hetzerk"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)} | Hetzerk"><meta name="twitter:description" content="{esc(description)}">{social}<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/site.css"><script src="/assets/site.js" defer></script></head><body><a class="skip" href="#main">Skip to content</a><div class="demo-strip">{DISCLAIMER}</div><header class="site-header"><a class="wordmark" href="/" aria-label="Hetzerk home">Hetzerk<span class="wordmark-dot">.</span></a><button class="menu-button" aria-expanded="false" aria-controls="main-navigation">Menu</button><nav id="main-navigation" aria-label="Main navigation"><a href="/etfs/">ETF strategies</a><a href="/research/">Perspectives</a><a href="/about/">Our approach</a><a href="/disclosures/">Disclosures</a><a class="nav-cta" href="/review/">Review guide <span aria-hidden="true">↗</span></a></nav></header><main id="main">{body}</main><footer class="site-footer"><div><a class="wordmark" href="/">Hetzerk<span class="wordmark-dot">.</span></a><p>Equity investing, considered.</p></div><div><p class="eyebrow">About this review</p><p>This is a demonstration of proposed equity strategies. No fund registration, availability, verified track record or advisory relationship is represented. Investing involves risk, including loss of principal.</p><div class="footer-links"><a href="/disclosures/">Disclosures & documents</a><a href="/privacy/">Privacy</a><a href="/form-crs.html">Form CRS status</a></div></div><small>© 2026 Hetzerk. Demo preview.</small></footer>{payload}</body></html>'''


def cards(funds):
    return '<div class="fund-grid">' + ''.join(f'''<a class="fund-card" href="/etfs/{f['fund_id']}/"><div class="card-top"><span class="ticker">{esc(f['ticker'])}</span><span class="muted">Proposed ETF</span></div><h3>{esc(f['name'].removeprefix('Hetzerk ').removesuffix(' ETF'))}</h3><p>{esc(f['strategy'])}</p><div class="card-bottom"><span>{pct(f['expense_ratio'])} illustrative annual expense ratio</span><span aria-hidden="true">↗</span></div></a>''' for f in funds) + '</div>'


def home(snapshot):
    funds = snapshot['funds']
    body = f'''<section class="hero home-hero"><div class="hero-copy"><p class="eyebrow">Independent thinking. Systematic discipline.</p><h1>Equity investing,<br><em>considered.</em></h1><p class="lede">A family of proposed equity strategies built around clear ideas, thoughtful portfolio construction and transparent data.</p><div class="actions"><a class="button" href="/etfs/">Explore the strategies <span aria-hidden="true">↗</span></a><a class="text-link" href="/about/">The thinking behind Hetzerk</a></div></div><aside class="hero-note"><span class="folio">01 / THE APPROACH</span><p>Start with an idea.<br>Examine the evidence.<br>Make the exposures clear.</p><div class="note-rule"></div><small>Five distinct perspectives on equity investing. One commitment to clarity.</small></aside></section><section class="section"><div class="section-heading"><div><p class="eyebrow">The strategy collection</p><h2>Different ideas.<br>A common discipline.</h2></div><p>Explore each proposed strategy, its illustrative portfolio and the assumptions behind its data.</p></div>{cards(funds)}</section><section class="principles section"><div><span class="folio">01</span><h3>Evidence before conviction.</h3><p>Define the investment idea, examine the inputs, and distinguish a hypothesis from a verified result.</p></div><div><span class="folio">02</span><h3>Know what you own.</h3><p>Look through to the full portfolio, concentration, sector exposure and cash allocation.</p></div><div><span class="folio">03</span><h3>Make the details visible.</h3><p>Consistent dates, downloadable records and clear distinctions between illustrative and official data.</p></div></section><section class="callout section"><p class="eyebrow">A working demonstration</p><h2>Every figure has a source.</h2><p>This review is populated from a structured Excel workbook. All prices, holdings and performance on these pages are illustrative.</p><a class="text-link" href="/review/">Explore the review guide <span aria-hidden="true">↗</span></a></section>'''
    return frame("Equity investing, considered.", "Explore Hetzerk’s proposed equity strategies in this illustrative demo.", body)


def holdings_table(holdings, table_id="holdings-table", full=False):
    headers = [("ticker", "Ticker"), ("identifier", "Identifier"), ("name", "Security"), ("sector", "Sector"), ("weight", "Weight"), ("quantity", "Shares Held")]
    if full:
        headers += [("price", "Local price"), ("currency", "Currency")]
    headers += [("market_value", "Market Value (USD)")]
    head = ''.join(f'<th scope="col" aria-sort="none"><button data-sort="{key}">{label}<span aria-hidden="true"> ↕</span></button></th>' if full else f'<th scope="col">{label}</th>' for key, label in headers)
    rows = []
    for h in holdings:
        values = [esc(h['ticker']), esc(h['identifier']), esc(h['name']), esc(h['sector']), pct(h['weight']), f"{h['quantity']:,.4f}"]
        if full:
            values += [f"{h['price']:,.2f}", esc(h['currency'])]
        values += [money(h['market_value'])]
        rows.append('<tr>' + ''.join(f'<td>{v}</td>' for v in values) + '</tr>')
    return f'<div class="table-scroll" tabindex="0" role="region" aria-label="Holdings table"><table id="{table_id}"><caption class="sr-only">Illustrative holdings. Values are in US dollars unless labeled otherwise.</caption><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def fund_page(f, snapshot, full=False):
    fid, last = f['fund_id'], f['daily'][-1]
    equities = [h for h in f['holdings'] if h['security_type'] == 'equity']
    metrics = [('NAV / share', money(last['nav'])), ('Market price', money(last['market_price'])), ('Net assets', money(last['net_assets'], 0)), ('Expense ratio', pct(f['expense_ratio']))]
    stats = '<div class="stats">' + ''.join(f'<div><span>{label}</span><strong>{value}</strong></div>' for label, value in metrics) + '</div>'
    intro = f'''<section class="fund-hero section"><a class="back-link" href="/etfs/">← All strategies</a><div class="fund-heading"><div><p class="eyebrow"><span class="ticker">{esc(f['ticker'])}</span> Proposed equity ETF</p><h1>{esc(f['name'].removeprefix('Hetzerk ').removesuffix(' ETF'))}</h1><p class="lede">{esc(f['strategy'])}</p></div><div class="fund-summary"><p>{esc(f['description'])}</p><span class="date-label">Illustrative data as of <time datetime="{f['as_of']}">{f['as_of']}</time></span><p class="freshness" data-as-of="{f['as_of']}" role="status"></p></div></div>{stats}<p class="metric-note">All values and fees are illustrative. Demo series begins {f['inception_date']}; this is not an actual fund inception date.</p></section>'''
    if full:
        sectors = sorted({h['sector'] for h in f['holdings']})
        body = intro + f'''<section class="section"><div class="section-heading"><div><p class="eyebrow">The full picture</p><h2>Portfolio holdings</h2></div><a class="button secondary" href="/etfs/{fid}/data/holdings.csv" download>Download holdings CSV ↓</a></div><p>{len(equities)} illustrative equity positions plus cash. Security identifiers beginning DEMO are placeholders. Prices and quantities are synthetic.</p><div class="filters"><label>Find a holding<input id="holding-search" type="search" placeholder="Ticker or security name"></label><label>Sector<select id="sector-filter"><option value="">All sectors</option>{''.join(f'<option>{esc(s)}</option>' for s in sectors)}</select></label><p id="holding-count" aria-live="polite">{len(f['holdings'])} positions</p></div>{holdings_table(f['holdings'],full=True)}<p id="holdings-empty" hidden>No holdings match these filters.</p><p class="metric-note">Weight uses total demo net assets including cash. Market value = quantity × local price × USD exchange rate. Download includes identifiers, country, currency and FX rate.</p><a class="text-link" href="/etfs/{fid}/#holdings">← Back to fund overview</a></section>'''
        return frame(f"{f['ticker']} holdings", f"Full illustrative holdings for {f['name']}, as of {f['as_of']}.", body, f)
    nav = '<nav class="section-nav" aria-label="Fund sections">' + ''.join(f'<a href="#{key}">{label}</a>' for key,label in [('overview','Overview'),('performance','Performance'),('holdings','Holdings'),('trading','Trading data'),('distributions','Distributions'),('documents','Documents')]) + '</nav>'
    returns = []
    for label in ('1Y','5Y','10Y','Since demo start','YTD','1M','3M','6M','3Y'):
        r = f['returns'][label]
        values = [pct(r[k], True) if r else 'Unavailable' for k in ('nav_total_return','market_total_return','benchmark_index')]
        returns.append(f'<tr><th scope="row">{label}{" <small>(annualized)</small>" if r and r["annualized"] else ""}</th>' + ''.join(f'<td>{v}</td>' for v in values) + '</tr>')
    perf = f'''<section class="section" id="performance"><div class="section-heading"><div><p class="eyebrow">Illustrative, throughout</p><h2>A view through time.</h2></div><span class="date-label">As of {f['as_of']}</span></div><p>Hypothetical demo results, not an actual track record. No claim is made that these returns could have been achieved.</p><div class="chart-panel"><div class="chart-toolbar"><span>Growth of 100 · demo total return</span><div class="periods" role="group" aria-label="Chart period">{''.join(f'<button data-period="{v}" aria-pressed="{str(v=="ALL").lower()}">{v}</button>' for v in ['1M','3M','6M','1Y','YTD','ALL'])}</div></div><div id="performance-chart" class="chart" role="img" aria-label="Illustrative total return chart">Interactive chart unavailable. Use the returns table and daily CSV below.</div><div class="chart-legend"><span class="nav-series">NAV total return</span><span class="market-series">Market total return</span><span class="benchmark-series">{esc(f['benchmark_label'])}</span></div><p id="chart-summary" class="metric-note" aria-live="polite"></p><noscript>Interactive chart requires JavaScript. The returns table and downloadable daily observations remain available.</noscript></div><div class="table-scroll"><table><caption>Illustrative total returns through {f['as_of']}</caption><thead><tr><th scope="col">Period</th><th scope="col">NAV</th><th scope="col">Market price</th><th scope="col">Demo benchmark</th></tr></thead><tbody>{''.join(returns)}</tbody></table></div><p class="metric-note">Returns assume reinvestment of the demo per-share distributions on their ex-dates. NAV series represents hypothetical values after fund expenses; investor brokerage costs and taxes are excluded. Periods longer than one year are annualized where labeled. Insufficient history is unavailable. The benchmark is synthetic and is not a licensed market index. These calculations are not approved standardized advertising performance.</p><a class="text-link" href="/etfs/{fid}/data/daily.csv" download>Download daily observations ↓</a></section>'''
    holdings = f'''<section class="section" id="holdings"><div class="section-heading"><div><p class="eyebrow">What’s inside</p><h2>Largest equity positions</h2></div><a class="text-link" href="/etfs/{fid}/holdings.html">View full holdings ↗</a></div><p>{len(equities)} equity positions in this illustrative portfolio. Cash: {pct(f['cash_weight'])}. As of {f['as_of']}.</p>{holdings_table(equities[:10],table_id='top-holdings')}<p class="metric-note">Holdings and allocations are illustrative and may change. Concentration, sector and country exposures can increase risk.</p></section>'''
    periods = ''.join(f'<tr><th scope="row">{p["period"]}</th><td>{p["premium_days"]}</td><td>{p["discount_days"]}</td><td>{p["at_nav_days"]}</td><td>{p["observations"]}</td></tr>' for p in f['disclosure_periods'])
    trading = f'''<section class="section" id="trading"><div class="section-heading"><div><p class="eyebrow">Price and value</p><h2>Trading data</h2></div><span class="date-label">Demo as of {f['as_of']}</span></div><div class="two-columns"><div class="data-card"><span>Closing premium / discount</span><strong>{pct(last['premium_discount'],True)}</strong><p>(Demo market price ÷ demo NAV) − 1</p></div><div class="data-card"><span>30-day median bid–ask spread</span><strong class="unavailable">Unavailable</strong><p>Requires reviewed intraday NBBO observations. Daily closing prices cannot supply this measure.</p></div></div><div id="premium-chart" class="chart" role="img" aria-label="Daily illustrative premium and discount history">Interactive chart unavailable. Daily premium / discount observations are included in the CSV.</div><div class="table-scroll"><table><caption>Completed calendar periods · illustrative observations</caption><thead><tr><th scope="col">Period</th><th scope="col">Premium</th><th scope="col">Discount</th><th scope="col">At NAV</th><th scope="col">Observations</th></tr></thead><tbody>{periods}</tbody></table></div><p class="metric-note">This demonstration uses fictional weekday observations, not a verified exchange-session calendar. A live release needs prior-business-day metrics, complete required historical periods and a scheduled pre-open holdings publication process.</p><details class="disclosure-details"><summary>Premium / discount exception disclosures</summary><p>No reviewed live exception register is available. A live release needs detection of deviations above 2% for more than seven consecutive trading days, a reviewed explanation when triggered, and the required retention. Absence of a record here is not evidence of no event.</p></details></section>'''
    dist_rows = ''.join(f'<tr><td>{d["ex_date"]}</td><td>{d["record_date"]}</td><td>{d["payable_date"]}</td><td>{money(d["income"],4)}</td><td>{money(d["short_term_gain"]+d["long_term_gain"],4)}</td><td>{money(d["return_of_capital"],4)}</td><td>{money(d["total"],4)}</td></tr>' for d in f['distributions'])
    dist = f'''<section class="section" id="distributions"><div class="section-heading"><div><p class="eyebrow">Income & distributions</p><h2>Distribution history</h2></div><a class="text-link" href="/etfs/{fid}/data/distributions.csv" download>Download CSV ↓</a></div><p>Illustrative amounts per share. Tax character and timing are not actual fund records.</p><div class="table-scroll"><table><caption class="sr-only">Demo distribution history</caption><thead><tr><th>Ex-date</th><th>Record date</th><th>Payable date</th><th>Income</th><th>Capital gains</th><th>Return of capital</th><th>Total</th></tr></thead><tbody>{dist_rows or '<tr><td colspan="7">No demo distributions recorded.</td></tr>'}</tbody></table></div></section>'''
    doc_items = []
    for document in f['documents']:
        status = (f'<a href="{esc(document["url"])}">View draft ↗</a>'
                  if document['url'] else '<span class="muted">Unavailable</span>')
        effective = esc(document['effective_date']) if document['effective_date'] else 'No effective document supplied'
        doc_items.append(f'<li><div><strong>{esc(document["title"])}</strong><span>{effective}</span></div>{status}</li>')
    doc_rows = ''.join(doc_items)
    docs = f'''<section class="section" id="documents"><div class="section-heading"><div><p class="eyebrow">Read the details</p><h2>Fund documents</h2></div></div><ul class="document-list">{doc_rows}</ul><p class="metric-note">This is not an offering. Actual investment decisions require the effective prospectus and other applicable fund documents. No filing, registration or distributor approval is represented by this demo.</p></section>'''
    overview = f'''<section class="section" id="overview"><div class="two-columns"><div><p class="eyebrow">The investment idea</p><h2>{esc(f['strategy'])}</h2><p class="lede">{esc(f['description'])}</p><a class="text-link" href="/research/{fid}/">Read the strategy perspective ↗</a></div><div class="editorial-note"><p class="eyebrow">Understand the trade-offs</p><p>Equity prices can fall. Active decisions may underperform the market. Concentrated portfolios can magnify individual company and sector risks. Global holdings add currency, market and political risks.</p><p>The demo portfolio illustrates the page and data workflow. It is not a portfolio recommendation or a finalized investment mandate.</p></div></div></section>'''
    return frame(f"{f['ticker']} — {f['name']}", f['description'] + ' Illustrative demo.', intro + nav + overview + perf + holdings + trading + dist + docs, f)


def article(title, kicker, paragraphs):
    return frame(title, paragraphs[0], f'<article class="article section"><p class="eyebrow">{esc(kicker)}</p><h1>{esc(title)}</h1>' + ''.join(f'<p>{p}</p>' for p in paragraphs) + '<a class="text-link" href="/research/">← All perspectives</a></article>')


def csv_text(records):
    if not records:
        return "No records\r\n"
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(records[0]))
    writer.writeheader()
    # Prevent spreadsheet formula interpretation in downloaded text columns.
    writer.writerows({k: ("'" + v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()} for row in records)
    return stream.getvalue()


def generate_pages(snapshot):
    funds = snapshot['funds']
    pages = {'index.html': home(snapshot)}
    pages['etfs/index.html'] = frame('ETF strategies', 'Five proposed equity strategies. Explore illustrative portfolios, performance and fund data.', f'<section class="section collection"><p class="eyebrow">The strategy collection</p><h1>Find the idea.<br><em>Understand the exposure.</em></h1><p class="lede">Five proposed equity strategies, each with a distinct starting point. Tickers, fees and terms remain illustrative.</p>{cards(funds)}</section>')
    for f in funds:
        fid = f['fund_id']
        pages[f'etfs/{fid}/index.html'] = fund_page(f, snapshot)
        pages[f'etfs/{fid}/holdings.html'] = fund_page(f, snapshot, full=True)
        pages[f'research/{fid}/index.html'] = article(f['strategy'], f"Perspective / {f['ticker']}", [esc(f['description']), 'An investment idea becomes useful when its definitions are explicit. The starting universe, measurement dates, portfolio constraints and rebalance rules determine which exposures a strategy actually takes.', 'A company can score well on a screen and still be a poor investment. Valuation, execution, competition and the limitations of historical data all matter. Portfolio concentration deserves the same attention as security selection.', 'This strategy is proposed and its example portfolio is illustrative. Before any launch, the mandate, risks, fees and disclosures need to agree with the effective offering documents.', f'<a href="/etfs/{fid}/">Explore the illustrative portfolio →</a>'])
        pages[f'etfs/{fid}/blog/index.html'] = pages[f'research/{fid}/index.html']
        pages[f'etfs/{fid}/document-placeholder.html'] = article('Document unavailable', 'Demo document status', ['No effective fund document has been supplied for this demo.', 'The site does not represent a registered offering. Effective prospectuses, SAI and applicable reports must be supplied and reviewed before a live release.'])
    pages['research/index.html'] = frame('Perspectives', 'Research perspectives on proposed equity strategies.', '<section class="section collection"><p class="eyebrow">Perspectives</p><h1>The thinking<br><em>behind the portfolio.</em></h1><p class="lede">Starting points for examining equity strategies, their assumptions and their trade-offs.</p><div class="article-list">' + ''.join(f'<a href="/research/{f["fund_id"]}/"><span class="eyebrow">{f["ticker"]} / Strategy perspective</span><h2>{esc(f["strategy"])}</h2><p>{esc(f["description"])}</p><span aria-hidden="true">↗</span></a>' for f in funds) + '</div></section>')
    pages['about/index.html'] = article('Clarity is part of the process.', 'The Hetzerk approach', ['Hetzerk Asset Management develops systematic equity strategies informed by fundamental research.', 'We connect investment ideas to a clear, inspectable portfolio: what is held, how it is measured, and when the information was prepared.', 'Our focus is the Hetzerk Innovation Factor ETF, combining measurable innovation characteristics, business quality and the capacity to reinvest.'])
    pages['disclosures/index.html'] = article('Investment Disclosures', 'Investor information', ['Investment entails risk, including loss of principal. Active management, concentration, liquidity, trading at a premium or discount, and global exposures can create additional risks.', 'Past performance does not guarantee future results. Returns include reinvested distributions and exclude investor brokerage costs and taxes. Periods over one year are annualized where labeled.', 'Effective offering documents and fund registration details have not been supplied. Visit the <a href="/documents/">document library</a> for fund materials, official SEC references and filing searches.', 'This website does not accept subscriptions, open investment accounts or process investments.'])
    pages['privacy/index.html'] = article('Privacy for this local demo', 'Review information', ['The generated pages contain no analytics or advertising trackers. Fonts and scripts are served locally. The interest forms prepare a draft in your email application using the details you enter; this website does not transmit or store those entries. You choose whether to send the email.', 'The local server may log page requests. Newsletter signup is not connected to a mailing list. External links and your email provider have their own policies. A production privacy notice must reflect the actual operator, hosting, processors and data practices.'])
    pages['form-crs.html'] = article('Form CRS status', 'Relationship summary', ['No filed Form CRS has been supplied or verified for this demo.', 'Form CRS applicability depends on the actual adviser or broker business and its retail investor relationships. ETF management alone does not establish that obligation. The demo makes no statements about disciplinary history or registration.'])
    tax = article('Section 351: the conditions matter.', 'Educational overview', ['Certain qualifying contributions of property to a corporation may defer recognition of gain under Section 351. Qualification is fact-specific; there is no blanket promise of a tax-free ETF exchange.', 'Control requirements, the investment-company exception and diversification rules, cash or other consideration, basis and the investor’s circumstances all need analysis. ETF creations and redemptions do not universally qualify under Section 351.', 'Any proposed transaction should be reviewed by qualified tax counsel using the actual facts. This page is educational and contains no transaction offer.', 'Primary reference: <a href="https://www.irs.gov/publications/p542">IRS Publication 542</a>.'])
    pages['section-351.html'] = pages['351-exchanges.html'] = tax
    pages['review/index.html'] = article('Fund Data Guide', 'Source and methodology', ['Fund pages, holdings tables and downloads share one validated Excel source.', 'Holdings weights use total net assets, including cash. Security market value equals quantity multiplied by local price and the USD exchange rate.', 'Total return series reinvest distributions on their ex-dates. Premium or discount equals closing market price divided by NAV, less one.', f'Snapshot fingerprint: <code>{snapshot["source_sha256"][:16]}</code>. Each fund view shows its as-of date.', '<a href="/review/hetzerk-demo.xlsx" download>Download the workbook ↓</a>', 'To update the site, edit the workbook, recalculate and save, then run the build command documented in the repository. The publisher checks dates, holdings, distributions and NAV reconciliation before updating the site.'])
    proxy=next((f.get('holdings_source') for f in funds if f.get('holdings_source')),None)
    if proxy:
        pages['review/index.html']=article('Fund Data Guide','Source and methodology',[
            'The workbook supplies fund terms, the 0.45% expense ratio, NAV, market-price history and distributions. An automated SPY input currently replaces the REDI stock allocation.',
            f'Holdings source date: {esc(proxy["as_of"])}. <a href="{esc(proxy["source_url"])}">State Street SPY holdings</a>. Stock weights are normalized to the workbook equity allocation; cash remains at the workbook allocation. The small contingent-value right is excluded from this equity-only allocation.',
            'Public position prices are inferred from rounded issuer weights × issuer net assets ÷ issuer quantities. Public quantities are rescaled to workbook net assets. These are not independent market observations. Yahoo quotes are used separately in the local valuation comparison.',
            'NAV, Market Price and Morningstar US Market Index retain the workbook dates. Holdings dates are shown separately. Each chart series is indexed to 100 for the selected period, without reinvesting fund distributions; return tables include reinvested distributions.',
            '<a href="/review/hetzerk-demo.xlsx" download>Download terms and history workbook ↓</a> · <a href="/data/spy-source.json" download>Download allocation source ↓</a>',
            'Run the SPY daily refresh workflow in GitHub Actions to update the allocation and rebuild Pages. The repository also documents a local refresh command.'])
    # Preserve old public paths without serving stale, unverified legacy copy.
    for source in (ROOT / 'legacy/site').rglob('*.html'):
        rel = source.relative_to(ROOT / 'legacy/site')
        if any(part.startswith('.') or part in ('dist','node_modules','outputs') for part in rel.parts):
            continue
        key = rel.as_posix()
        if key in pages:
            continue
        parts = rel.parts
        fid = parts[1] if len(parts)>1 and parts[0]=='etfs' and parts[1] in {f['fund_id'] for f in funds} else 'redi'
        target = f'/research/{fid}/' if 'blog' in parts or 'research' in parts or 'why-' in key else f'/etfs/{fid}/'
        if key == '404.html':
            pages[key] = article('This page could not be found.', '404', ['The page may have moved. <a href="/etfs/">Browse the strategy collection</a> or return to the <a href="/">homepage</a>.'])
        else:
            pages[key] = frame('Page moved', 'This review page has a new location.', f'<section class="section article"><h1>This page has moved.</h1><p><a class="button" href="{target}">Continue to the current page →</a></p></section>')
    from publishing.restoration import restore_pages
    from publishing.visibility import visible_pages
    from publishing.copy import polish_pages
    from publishing.branding import brand_pages
    from publishing.minimal_home import render_home
    from publishing.investment_case import decorate_exchange_page, render_case
    from publishing.research import render_research_pages
    pages = polish_pages(visible_pages(restore_pages(snapshot, pages), snapshot))
    redi = next(f for f in snapshot['funds'] if f['fund_id'] == 'redi')
    pages['index.html'] = render_home(pages['index.html'], redi)
    for route in ('section-351.html', '351-exchanges.html'):
        pages[route] = decorate_exchange_page(pages[route])
    investment_case = render_case(pages['index.html'])
    for route in ('etfs/redi/why-red.html', 'why-red.html', 'red/why-red.html'):
        pages[route] = investment_case
    pages.update(render_research_pages(pages['index.html'], pages['research/index.html']))
    for route in ('etfs/redi/blog/index.html', 'red/blog/index.html', 'research/redi/index.html'):
        pages[route] = pages['research/index.html']
    return brand_pages(pages)
