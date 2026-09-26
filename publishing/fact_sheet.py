"""One editorial and data source for the REDI web and PDF fact sheets."""
from html import escape


DECK = 'Investing in Innovation, REDI for tomorrow.'
OBJECTIVE = ('REDI seeks long-term capital appreciation through U.S. mid- and large-cap companies '
             'selected for innovation ability and valuation, using a systematic, equal-weight approach.')
PROCESS = (
    ('01', 'Innovation value', '', 'Assess the price paid for a company’s innovation activity.'),
    ('02', 'Innovation ability', '', 'Measure how effectively R&D translates into commercial results.'),
    ('03', 'Portfolio construction', '', 'Equally weight selected companies in a long-only equity portfolio.'),
)
TERM_NOTE = 'Intended fee and lending terms are subject to final fund documents.'
RISK = ('Investing involves risk, including loss of principal. Innovation, valuation and model risks '
        'may cause underperformance. Diversification does not prevent losses. ETF shares may trade '
        'above or below NAV. Review the prospectus for objectives, risks, charges and expenses before investing.')


def fact_sheet_data(fund):
    """Keep dates and current positions distinct from intended portfolio construction."""
    daily = fund['daily'][-1]
    equities = sorted((h for h in fund['holdings'] if h['security_type'] == 'equity'),
                      key=lambda h: h['weight'], reverse=True)
    proxy = fund.get('holdings_source')
    allocation_note = ('Displayed SPY-based holdings are not the target innovation portfolio.'
                       if proxy else 'Holdings reflect the dated fund snapshot and may change.')
    return {
        'name': fund['name'], 'ticker': fund['ticker'], 'deck': DECK, 'objective': OBJECTIVE,
        'process': PROCESS,
        'fee': f"{fund['expense_ratio']:.2%}", 'bps': f"{fund['expense_ratio'] * 10000:g}",
        'as_of': daily['date'], 'holdings_as_of': fund.get('holdings_as_of', fund['as_of']),
        'nav': f"${daily['nav']:,.4f}", 'market_price': f"${daily['market_price']:,.4f}",
        'net_assets': f"${daily['net_assets']:,.0f}", 'equity_count': len(equities),
        'cash_weight': f"{fund['cash_weight']:.2%}", 'benchmark': fund['benchmark_label'],
        'holdings': equities[:5], 'allocation_note': allocation_note,
        'term_note': TERM_NOTE, 'risk': RISK,
        'terms': (
            ('Annual expense ratio', f"{fund['expense_ratio']:.2%} / {fund['expense_ratio'] * 10000:g} basis points"),
            ('Intended 12b-1 fee', 'None'),
            ('Securities lending', 'Net income, if any, benefits fund shareholders.'),
        ),
        'key_facts': (
            ('Investment universe', 'U.S. mid- & large-cap'),
            ('Target portfolio', '50–100 equities'),
            ('Portfolio weights', 'Equal weight'),
            ('Exposure', 'Long only · No leverage'),
        ),
        'demo_banner': ('Illustrative demo · SPY-based stock allocation, rescaled quantities and inferred prices · '
                        'NAV and performance remain fictional · Not an investment offering' if proxy else
                        'Illustrative demo · Not actual fund performance · Proposed terms subject to change'),
        'is_demo': fund.get('is_demo', False),
    }


def fact_sheet_body(fund):
    d = fact_sheet_data(fund)
    e = escape
    process = ''.join(f'<article class="fs-process-card"><span class="fs-step">{n}</span>'
                      f'<h3>{e(title)}</h3><p>{e(copy)}</p></article>'
                      for n, title, question, copy in d['process'])
    terms = ''.join(f'<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for label, value in d['terms'])
    key_facts = ''.join(f'<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for label, value in d['key_facts'])
    holdings = ''.join(f'<tr><td><strong>{e(h["ticker"])}</strong></td><td>{e(h["name"])}</td>'
                       f'<td>{h["weight"]:.2%}</td></tr>' for h in d['holdings'])
    return f'''<article class="fund-factsheet" aria-labelledby="fs-title">
      <nav class="fs-toolbar" aria-label="Fact sheet navigation"><a href="/etfs/redi/">← Back to REDI</a><a class="fs-download" href="/etfs/redi/fact-sheet.pdf" type="application/pdf" download>Download fact sheet <span>PDF ↓</span></a></nav>
      <header class="fs-hero"><div><p class="fs-eyebrow">{e(d['ticker'])} / Fund fact sheet</p><h1 id="fs-title">{e(d['name'])}</h1></div><div class="fs-fee"><span>Annual expense ratio</span><strong>{d['fee']}</strong><span>{d['bps']} basis points</span></div></header>
      <section class="fs-objective" aria-labelledby="fs-objective"><h2 id="fs-objective">Investment objective</h2><p>{e(d['objective'])}</p></section>
      <dl class="fs-key-facts">{key_facts}</dl>
      <section class="fs-process" aria-label="Investment process"><div class="fs-process-grid">{process}</div></section>
      <section class="fs-snapshot" aria-labelledby="fs-snapshot"><div class="fs-section-heading"><h2 id="fs-snapshot">Portfolio snapshot</h2><p class="fs-note">Valuation as of {d['as_of']}</p></div><dl class="fs-values"><div><dt>NAV</dt><dd>{d['nav']}</dd></div><div><dt>Market Price</dt><dd>{d['market_price']}</dd></div><div><dt>Net assets</dt><dd>{d['net_assets']}</dd></div></dl><div class="fs-holdings"><div><h3>Top 5 holdings</h3><p class="fs-note">Holdings as of {d['holdings_as_of']} · {d['equity_count']} equity positions</p><p>{e(d['allocation_note'])}</p><p class="fs-note">Benchmark: {e(d['benchmark'])}</p><a class="fs-text-link" href="/etfs/redi/holdings.html">All holdings ↗</a></div><div class="fs-table-wrap"><table><caption class="sr-only">Five largest equity positions by portfolio weight</caption><thead><tr><th scope="col">Ticker</th><th scope="col">Company</th><th scope="col">Weight</th></tr></thead><tbody>{holdings}</tbody></table><p class="fs-note">% of net assets. Holdings may change.</p></div></div></section>
      <section class="fs-terms" aria-label="Fund terms"><dl>{terms}</dl><p class="fs-note">{e(d['term_note'])}</p></section>
      <aside class="fs-risk" aria-labelledby="fs-risk"><h2 id="fs-risk">Important information</h2><p>{e(d['risk'])}</p><nav aria-label="Further fund information"><a href="/etfs/redi/#performance">Performance ↗</a><a href="/research/on-innovation-factor-investing.html">The research ↗</a><a href="/documents/">Documents &amp; filings ↗</a></nav></aside>
    </article>'''
