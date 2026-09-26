"""One editorial and data source for the REDI web and PDF fact sheets."""
from html import escape


DECK = 'Investing in Innovation, REDI for tomorrow.'
OBJECTIVE = ('REDI seeks long-term capital appreciation through U.S. mid- and large-cap companies '
             'with the ability to turn research and development into commercial value. A systematic '
             'process combines innovation ability with valuation discipline.')
THESIS = ('Investment in knowledge can create new products, improve productivity and expand a '
          'business’s earning power. Endogenous growth theory supplies the economic intuition: '
          'progress can come from better ideas, even as growth in labor or physical inputs slows. '
          'For shareholders, the question is which companies can capture that value, and what price to pay.')
PROCESS = (
    ('01', 'Innovation value', 'What price for progress?',
     'Assess the price investors pay for a company’s innovation activity. Seek exposure where '
     'the valuation leaves room for research to create shareholder value.'),
    ('02', 'Innovation ability', 'What becomes of research?',
     'Use statistical models to evaluate how effectively a company turns R&D into business results. '
     'Research spending is an input; commercial execution is the characteristic of interest.'),
    ('03', 'Portfolio construction', 'Give conviction a clear role.',
     'Target 50–100 U.S. mid- and large-cap equities. Equally weight selected companies within '
     'a long-only portfolio without leverage.'),
)
FACTOR = ('REDI evaluates a company characteristic across changing industries. The process '
          'distinguishes growth supported by internal research from growth through other sources '
          'and considers commercial outcomes alongside R&D spending.')
CONVICTION = ('A focused set of economically motivated signals keeps the selection process '
              'interpretable. Innovation value and ability bring distinct questions to the same '
              'decision: whether a business’s research merits a place in the portfolio.')
TERM_NOTE = ('The 12b-1 and securities-lending terms reflect the intended structure and remain '
             'subject to final fund documents. Target portfolio characteristics are not current '
             'holdings or guarantees.')
RISK = ('Investing involves risk, including loss of principal. Innovation research may not lead '
        'to commercial success, and successful businesses can be overpriced. Models rely on '
        'imperfect data and assumptions; value, growth and sector exposures may cause periods of '
        'underperformance. Equal weighting and diversification do not prevent losses. ETF shares '
        'trade at market prices that may differ from NAV. Review the prospectus for objectives, '
        'risks, charges and expenses before investing.')


def fact_sheet_data(fund):
    """Keep dates and current positions distinct from intended portfolio construction."""
    daily = fund['daily'][-1]
    equities = sorted((h for h in fund['holdings'] if h['security_type'] == 'equity'),
                      key=lambda h: h['weight'], reverse=True)
    proxy = fund.get('holdings_source')
    allocation_note = ('The displayed allocation follows SPY holdings, rescaled to the fund snapshot. '
                       'It does not represent the intended innovation-factor selection or weighting.'
                       if proxy else 'Holdings reflect the dated fund snapshot and may change.')
    return {
        'name': fund['name'], 'ticker': fund['ticker'], 'deck': DECK, 'objective': OBJECTIVE,
        'thesis': THESIS, 'process': PROCESS, 'factor': FACTOR, 'conviction': CONVICTION,
        'fee': f"{fund['expense_ratio']:.2%}", 'bps': f"{fund['expense_ratio'] * 10000:g}",
        'as_of': daily['date'], 'holdings_as_of': fund.get('holdings_as_of', fund['as_of']),
        'nav': f"${daily['nav']:,.4f}", 'market_price': f"${daily['market_price']:,.4f}",
        'net_assets': f"${daily['net_assets']:,.0f}", 'equity_count': len(equities),
        'cash_weight': f"{fund['cash_weight']:.2%}", 'benchmark': fund['benchmark_label'],
        'holdings': equities[:10], 'allocation_note': allocation_note,
        'term_note': TERM_NOTE, 'risk': RISK,
        'terms': (
            ('Annual expense ratio', f"{fund['expense_ratio']:.2%} / {fund['expense_ratio'] * 10000:g} basis points"),
            ('Intended 12b-1 fee', 'None'),
            ('Securities lending', 'Net lending income, if any, accrues to the fund for shareholders’ benefit.'),
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
                      f'<h3>{e(title)}</h3><p class="fs-question">{e(question)}</p><p>{e(copy)}</p></article>'
                      for n, title, question, copy in d['process'])
    terms = ''.join(f'<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for label, value in d['terms'])
    key_facts = ''.join(f'<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for label, value in d['key_facts'])
    holdings = ''.join(f'<tr><td><strong>{e(h["ticker"])}</strong></td><td>{e(h["name"])}</td>'
                       f'<td>{h["weight"]:.2%}</td></tr>' for h in d['holdings'])
    return f'''<article class="fund-factsheet" aria-labelledby="fs-title">
      <nav class="fs-toolbar" aria-label="Fact sheet navigation"><a href="/etfs/redi/">← Back to REDI</a><a class="fs-download" href="/etfs/redi/fact-sheet.pdf" type="application/pdf" download>Download fact sheet <span>PDF ↓</span></a></nav>
      <header class="fs-hero"><div><p class="fs-eyebrow">{e(d['ticker'])} / Fund fact sheet</p><h1 id="fs-title">{e(d['name'])}</h1><p class="fs-deck">{e(d['deck'])}</p></div><div class="fs-fee"><span>Annual expense ratio</span><strong>{d['fee']}</strong><span>{d['bps']} basis points</span></div></header>
      <section class="fs-objective" aria-labelledby="fs-objective"><h2 id="fs-objective">Investment objective</h2><p>{e(d['objective'])}</p></section>
      <dl class="fs-key-facts">{key_facts}</dl>
      <section class="fs-process" aria-labelledby="fs-process"><div class="fs-section-heading"><p class="fs-eyebrow">The investment process</p><h2 id="fs-process">Research. Results. A price worth paying.</h2></div><div class="fs-process-grid">{process}</div></section>
      <section class="fs-thesis" aria-labelledby="fs-thesis"><div><p class="fs-eyebrow">The economic intuition</p><h2 id="fs-thesis">Growth has a source.</h2></div><div><p>{e(d['thesis'])}</p><ol class="fs-growth-chain" aria-label="Illustrative innovation cycle"><li><span>01</span>Research</li><li><span>02</span>Knowledge</li><li><span>03</span>Commercial value</li><li><span>04</span>Reinvestment</li></ol><p class="fs-note">An economic rationale, not a prediction of investment returns.</p></div></section>
      <div class="fs-perspectives"><section><p class="fs-eyebrow">Factors across industries</p><h2>Measure the business.<br>Follow the evidence.</h2><p>{e(d['factor'])}</p></section><section><p class="fs-eyebrow">Focused by design</p><h2>A few meaningful signals.<br>A clear investment thesis.</h2><p>{e(d['conviction'])}</p></section></div>
      <section class="fs-terms" aria-labelledby="fs-terms"><div><p class="fs-eyebrow">Fund structure</p><h2 id="fs-terms">Costs, made clear.</h2></div><div><dl>{terms}</dl><p class="fs-note">{e(d['term_note'])}</p></div></section>
      <section class="fs-snapshot" aria-labelledby="fs-snapshot"><div class="fs-section-heading"><div><p class="fs-eyebrow">Dated fund data</p><h2 id="fs-snapshot">Portfolio snapshot</h2></div><p class="fs-note">Valuation as of {d['as_of']}</p></div><dl class="fs-values"><div><dt>NAV</dt><dd>{d['nav']}</dd></div><div><dt>Market Price</dt><dd>{d['market_price']}</dd></div><div><dt>Net assets</dt><dd>{d['net_assets']}</dd></div><div><dt>Cash allocation</dt><dd>{d['cash_weight']}</dd></div></dl><div class="fs-holdings"><div><h3>Top 10 holdings</h3><p class="fs-note">Holdings as of {d['holdings_as_of']}</p><p>{e(d['allocation_note'])}</p><dl class="fs-snapshot-details"><div><dt>Current equity positions</dt><dd>{d['equity_count']}</dd></div><div><dt>Benchmark</dt><dd>{e(d['benchmark'])}</dd></div></dl><a class="fs-text-link" href="/etfs/redi/holdings.html">View all holdings ↗</a></div><div class="fs-table-wrap"><table><caption class="sr-only">Ten largest equity positions by portfolio weight</caption><thead><tr><th scope="col">Ticker</th><th scope="col">Company</th><th scope="col">Weight</th></tr></thead><tbody>{holdings}</tbody></table><p class="fs-note">Weights are percentages of portfolio net assets. Holdings may change.</p></div></div></section>
      <aside class="fs-risk" aria-labelledby="fs-risk"><h2 id="fs-risk">Important information</h2><p>{e(d['risk'])}</p><nav aria-label="Further fund information"><a href="/etfs/redi/#performance">Performance ↗</a><a href="/etfs/redi/why-red.html">Investment case ↗</a><a href="/documents/">Documents &amp; filings ↗</a></nav></aside>
    </article>'''
