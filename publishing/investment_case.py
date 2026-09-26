"""Deck-derived investment thesis, shared by the homepage and full case.

Source: DBE Innovation Factor ETF.pptx, slides 4, 6–11, 18–24.
Source images retain their original labels. Backtests are identified as research,
not fund performance. Unfinished parameters and internal notes are not fund facts.
"""
from bs4 import BeautifulSoup
from html import escape


VISUALS = {
    'longterm': {
        'file': 'long-term-characteristics.png', 'width': 2048, 'height': 1113,
        'title': 'Characteristics of fire', 'source': 'Long-term principles · Slide 9',
        'alt': 'Shin Chan conducts a range of possible return paths. The source illustration labels the strategy principles Systematic, Positive Population Mean and Constrained Tail Events, with a conceptual expected excess return above zero.',
        'caption': 'Conceptual illustration of strategy design. The paths and expected-return notation are not historical results, forecasts or a guarantee of positive returns or limited losses.',
    },
    'businesscard': {
        'file': 'redi-business-card-chart.png', 'width': 2048, 'height': 1170,
        'title': 'REDI research with Shin Chan', 'source': 'Opening business card · Slide 1',
        'alt': 'Shin Chan flies along the Innovation Leaders series on a logarithmic growth-of-one-dollar chart, beside Innovation Laggards, Market, Market Equal Weight and Non-R&D Payers. The chart labels its April 2003 to August 2026 results as a backtest.',
        'caption': 'Backtested strategy research from the opening business card, not actual ETF performance. Past performance does not guarantee future results.',
    },
    'endogenous': {
        'file': 'endogenous-growth.png', 'width': 1472, 'height': 614,
        'title': 'Investing in Innovation', 'source': 'Economic rationale · Slide 7',
        'heading': 'Investing in Innovation',
        'subtitle': 'Economic, Theoretical, & Factor Justifications',
        'alt': 'The endogenous-growth slide connects research investment and knowledge creation, with an equilibrium diagram, innovation-cohort time series, Shin Chan as a scientist, and U.S. R&D spending relative to GDP by funding source from 1953 to 2023.',
        'caption': 'The deck’s economic rationale links research investment with knowledge creation. Cohort returns are strategy research, not actual fund performance; the source figures have not been independently verified.',
    },
    'exchange': {
        'file': 'portfolio-to-redi-sticker.png', 'width': 1369, 'height': 1149,
        'title': 'Many securities. One REDI position.', 'source': 'Section 351 · Slide 1',
        'alt': 'Sticker-shaped illustration of Shin Chan carrying a portfolio across a bridge from several securities into REDI, beside red and gray research return series. Text reads Many securities. One REDI position. Section 351 exchange into REDI.',
        'caption': 'Portfolio-to-REDI exchange concept. The depicted chart is not actual ETF performance. Section 351 eligibility depends on the proposed transaction.',
    },
    'weighting': {
        'file': 'portfolio-weighting.png', 'width': 1092, 'height': 522,
        'title': 'The portfolio-weighting framework', 'source': 'Portfolio research · Slide 21',
        'alt': 'Comparison of equal weighting, inverse-volatility weighting and risk parity, showing the mathematical symmetry assumptions under which each rule is optimal. Equal weighting assigns one divided by the number of holdings to each company.',
        'caption': 'REDI’s construction uses equal weighting. The source slide compares weighting rules and the assumptions behind them; it does not establish that equal weighting is universally optimal.',
    },
    'factors': {
        'file': 'factor-comparison.png', 'width': 1408, 'height': 784,
        'title': 'The measure of fire', 'source': 'Factor comparison · Slide 13',
        'alt': 'Shin Chan stands beside research time series from 2003 to 2026 comparing Innovation, R&D Other, Market, Market EW and Non-Payers, with a close-up of 2003 to 2013.',
        'caption': 'Backtested comparisons from the deck. Source labels and endpoints are preserved; these are not actual ETF returns and have not been independently verified.',
    },
    'breadth': {
        'file': 'selection-breadth.png', 'width': 1414, 'height': 800,
        'title': 'The red thread: selection breadth', 'source': 'Selection research · Slide 13',
        'alt': 'Research growth paths from 2003 to 2026 compare the Innovation portfolio with selection variants labelled 150/75, 200/100 and 250/125, with a 2003 to 2013 inset.',
        'caption': 'Backtested selection variants from the deck, not final portfolio-size commitments or actual ETF performance. Results have not been independently verified.',
    },
    'annual': {
        'file': 'annual-comparison.png', 'width': 2048, 'height': 1070,
        'title': 'Innovation year by year', 'source': 'Annual research · Slide 17',
        'alt': 'Annual bar chart comparing Innovation with the S&P 500 from 2003 through 2026, including positive and negative years. The 2026 observation represents a partial year.',
        'caption': 'Backtested annual comparisons from the source deck. The 2026 observation is a partial year. These are not actual ETF returns; benchmark inputs and fee treatment have not been independently verified.',
    },
    'reinvestment': {
        'file': 'corporate-metabolism.png', 'width': 2048, 'height': 1170,
        'title': 'Reinvestment and the business', 'source': 'Investment case · Slide 12',
        'alt': 'Corporate metabolism illustration: reinvestment feeds business activity and future cash flows, alongside dividends, share repurchases, debt paydown and acquisitions.',
        'caption': 'The deck’s corporate-metabolism illustration connects capital allocation, reinvestment and potential future cash flows.',
    },
    'research': {
        'file': 'innovation-research.png', 'width': 2048, 'height': 946,
        'title': 'Innovation through the research lens', 'source': 'Strategy research · Slide 16',
        'alt': 'Source research chart comparing the growth of one dollar across Pred Innovation, Innovation, R&D Other, Market EW, Market and Non-payers, from September 2002 through August 2026. It includes full-period absolute and logarithmic scales and a view of the first ten years.',
        'caption': 'Backtested strategy research, not actual ETF performance. The chart does not specify fee and trading-cost treatment; the results have not been independently verified.',
    },
    'timeline': {
        'file': 'innovation-timeline.png', 'width': 2048, 'height': 1152,
        'title': 'The red thread of innovation', 'source': 'Strategy research · Slide 19',
        'alt': 'Six illustrated technology eras from 2000 through August 2026: digital infrastructure, silicon and storage, streaming and precision medicine, cloud and AI tools, platforms and data, and the physical AI stack. Each era includes selected positive and negative historical research contributors.',
        'caption': 'The deck traces changing technologies and selected contributors in its historical research portfolio. Contribution figures are backtested research, not REDI holdings or actual fund returns.',
    },
}


def case_visual(key, compact=False, prefix='', eager=False):
    visual = VISUALS[key]
    title, alt, caption = (escape(visual[k], quote=True) for k in ('title', 'alt', 'caption'))
    src = '/assets/investment-case/' + visual['file']
    caption_id = f'{prefix}visual-{key}-caption'
    heading = (f'<div class="case-source-heading"><h4>{escape(visual["heading"])}</h4><p>{escape(visual["subtitle"])}</p></div>'
               if visual.get('heading') else '')
    return f'''<figure class="case-visual{' case-visual-compact' if compact else ''}">
      {heading}
      <a class="case-visual-link" href="{src}" data-case-visual aria-label="Enlarge: {title}" aria-describedby="{caption_id}">
        <img src="{src}" width="{visual['width']}" height="{visual['height']}" alt="{alt}" loading="{'eager' if eager else 'lazy'}" decoding="async">
        <span class="case-visual-expand" aria-hidden="true">View full size <span>↗</span></span>
      </a>
      <figcaption id="{caption_id}"><div class="case-visual-meta"><strong>{title}</strong><span>{visual['source']}</span></div><p>{caption}</p></figcaption>
    </figure>'''


def business_card():
    return f'''<div class="case-business-card"><div class="case-business-brand"><strong>REDI</strong><span>Hetzerk Innovation Factor ETF</span></div>
      {case_visual('businesscard', eager=True)}
    </div>'''


def exchange_sticker():
    visual = VISUALS['exchange']
    return f'''<div class="exchange-sticker"><img src="/assets/investment-case/{visual['file']}"
      width="{visual['width']}" height="{visual['height']}" alt="{escape(visual['alt'], quote=True)}"
      loading="lazy" decoding="async"></div>'''


def decorate_exchange_page(html):
    page = BeautifulSoup(html, 'html.parser')
    page.body['class'] = page.body.get('class', []) + ['case-visual-host']
    attach_assets(page)
    intro = page.h1.parent
    wrapper = page.new_tag('div', attrs={'class': 'exchange-hero-visual'})
    intro.wrap(wrapper)
    intro['class'] = intro.get('class', []) + ['exchange-hero-copy']
    wrapper.append(BeautifulSoup(exchange_sticker(), 'html.parser').div)
    return str(page)


STEPS = (
    ('value', 'Innovation value', 'What are you paying for innovation?',
     'Assess a company’s innovation investment alongside its valuation. The aim is to identify innovation potential at a justifiable price.',
     'The investment', 'Research and development within the business.',
     'The price', 'Valuation in relation to that innovation activity.'),
    ('ability', 'Innovation ability', 'Can research become a business result?',
     'Examine a company’s record of turning research into commercial outcomes. Innovation spending is a starting point; the ability to use it matters.',
     'The research', 'A company’s commitment to developing new capabilities.',
     'The outcome', 'Evidence of commercially successful innovation.'),
    ('portfolio', 'Portfolio construction', 'Bring the research into the portfolio.',
     'Apply both lenses systematically to U.S. mid- and large-cap equities, then equally weight the selected companies.',
     'The allocation', 'Equal weighting across selected companies.',
     'The exposure', 'Long-only equities, without leverage.'),
)


def case_explorer(prefix):
    # All panels remain readable without JavaScript; JS progressively adds tab roles.
    buttons = ''.join(
        f'<button type="button" id="{prefix}-tab-{key}" aria-controls="{prefix}-panel-{key}"><span class="case-step-number">0{i}</span><span>{label}</span><span class="case-step-arrow" aria-hidden="true">↗</span></button>'
        for i, (key, label, *_) in enumerate(STEPS, 1)
    )
    visual_keys = {'value': 'reinvestment', 'ability': 'endogenous', 'portfolio': 'weighting'}
    panels = ''.join(
        f'''<article class="case-panel" id="{prefix}-panel-{key}" aria-labelledby="{prefix}-tab-{key}">
          <div class="case-panel-copy"><span class="case-kicker">0{i} / {label}</span><h3>{title}</h3><p>{body}</p>
            <dl class="case-lenses"><div><dt>{lens_a}</dt><dd>{text_a}</dd></div><div><dt>{lens_b}</dt><dd>{text_b}</dd></div></dl></div>
          {case_visual(visual_keys[key], prefix=prefix+'-')}
        </article>'''
        for i, (key, label, title, body, lens_a, text_a, lens_b, text_b) in enumerate(STEPS, 1)
    )
    return f'''<div class="case-explorer" data-case-explorer>
      <div class="case-tabs" aria-label="Explore the investment process">{buttons}</div>
      <div class="case-panels">{panels}</div>
    </div>'''


def research_charts():
    charts = (('research', 'Growth of $1'), ('factors', 'Factor comparison'),
              ('breadth', 'Selection breadth'), ('annual', 'Year by year'))
    buttons = ''.join(
        f'<button type="button" id="research-tab-{key}" aria-controls="research-panel-{key}"><span class="case-step-number">0{i}</span><span>{label}</span></button>'
        for i, (key, label) in enumerate(charts, 1)
    )
    panels = ''.join(
        f'<div class="case-chart-panel" id="research-panel-{key}" aria-labelledby="research-tab-{key}">{case_visual(key)}</div>'
        for key, _ in charts
    )
    return f'''<section class="case-research investment-case" id="research" aria-labelledby="research-heading">
      <div class="case-section-heading"><div><p class="home-eyebrow">04 / Through time</p><h2 id="research-heading">The research,<br>from different angles.</h2></div><p>Explore the deck’s time series and selection comparisons. The charts retain their original research variants, labels and sample periods.</p></div>
      <div class="case-explorer case-chart-explorer" data-case-explorer><div class="case-tabs" aria-label="Explore research charts">{buttons}</div><div class="case-panels">{panels}</div></div>
    </section>'''


def why_now_section():
    return '''<section class="case-why-now investment-case" id="why-now" aria-labelledby="why-now-title">
      <div class="case-section-heading"><div><p class="home-eyebrow">02 / The opportunity</p><h2 id="why-now-title">Why now?<br>Look at what comes next.</h2></div><p>Companies decide how much cash to return today and how much to invest in tomorrow. REDI focuses on the reinvestment that can create future earning power, with a disciplined view of its value.</p></div>
      <div class="case-now-layout">
        <div class="case-capital">
          <p class="case-kicker">Five uses of corporate cash</p>
          <h3>Where the next<br>dollar goes.</h3>
          <ol class="case-cash-uses">
            <li><span class="case-cash-number">01</span><div><strong>Dividends</strong><span>Distribute cash to shareholders.</span></div></li>
            <li><span class="case-cash-number">02</span><div><strong>Share repurchases</strong><span>Buy back the company’s shares.</span></div></li>
            <li><span class="case-cash-number">03</span><div><strong>Debt repayment</strong><span>Reduce borrowing obligations.</span></div></li>
            <li><span class="case-cash-number">04</span><div><strong>Acquisitions</strong><span>Acquire businesses and capabilities.</span></div></li>
            <li class="case-cash-focus"><span class="case-cash-number">05</span><div><strong>Reinvestment <span>REDI’s focus</span></strong><span>Develop products, knowledge and capabilities within the business.</span></div></li>
          </ol>
          <p class="case-capital-note">The research connects investment in innovation with a company’s ability to turn it into commercial results.</p>
        </div>
        <div class="case-now-reasons">
          <article><span class="case-kicker">Valuation</span><h3>Growth still has a price.</h3><p>A compelling innovation story needs a valuation test. REDI considers innovation investment alongside the price paid and evidence of commercial execution.</p></article>
          <article><span class="case-kicker">Opportunity</span><h3>Industries keep changing.</h3><p>Innovation can reshape established industries and create new ones. A factor process can reassess companies as that opportunity changes, without depending on a single technology theme.</p></article>
          <article><span class="case-kicker">Business exposure</span><h3>U.S. companies. Global customers.</h3><p>Domestic companies can earn revenue abroad. That can broaden their economic exposure; overseas sales do not turn U.S. equity holdings into an international equity allocation.</p></article>
          <article><span class="case-kicker">Portfolio role</span><h3>A long-term equity allocation.</h3><p>The strategy seeks capital appreciation through long-only equities. It is designed for consideration within a core or satellite allocation, with equal weighting and no leverage.</p></article>
        </div>
      </div>
    </section>'''


def long_term_section():
    return f'''<section class="case-long-term investment-case" id="long-term" aria-labelledby="long-term-title">
      <div class="case-section-heading"><div><p class="home-eyebrow">06 / Characteristics of fire</p><h2 id="long-term-title">Characteristics<br>you can hold forever.</h2></div><p>A durable strategy needs a process you can repeat, a reason to expect a return, and clear constraints on portfolio risk.</p></div>
      <div class="case-enduring-layout">
        {case_visual('longterm')}
        <ol class="case-enduring-principles">
          <li><span>01</span><div><h3>Systematic by design.</h3><p>Apply consistent measures and selection rules. Companies and market narratives can change while the investment process remains repeatable.</p></div></li>
          <li><span>02</span><div><h3>An economic reason to invest.</h3><p>Connect economic reasoning, theory and empirical research. Innovation’s potential contribution to future cash flows supports a return hypothesis that must continue to be tested.</p></div></li>
          <li><span>03</span><div><h3>Risk considered in construction.</h3><p>Use equity assets, equal weighting and no leverage. Portfolio constraints shape exposure to severe outcomes; they do not eliminate drawdowns or cap losses.</p></div></li>
        </ol>
      </div>
      <p class="case-enduring-note">“Hold forever” describes the intended durability of the strategy’s principles. Individual holdings can change as company characteristics and valuations change.</p>
    </section>'''


def home_case():
    return f'''<section id="innovation" class="investment-case home-investment" aria-labelledby="case-heading">
      <span id="services" class="home-anchor" aria-hidden="true"></span>
      <div class="case-section-heading"><div><p class="home-eyebrow">The investment case</p><h2 id="case-heading">Innovation at a<br>justifiable valuation.</h2></div><p>Seek the companies turning research into commercial progress. Bring a disciplined view of value to what comes next.</p></div>
      {case_explorer('home-case')}
      <div class="case-section-foot"><span>Fundamental insight. Systematic selection.</span><a class="home-text-link" href="/etfs/redi/why-red.html">Explore the investment case <span aria-hidden="true">↗</span></a></div>
    </section>'''


def attach_assets(page):
    page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/investment-case.css'))
    page.head.append(page.new_tag('script', src='/assets/investment-case.js', defer=''))


def render_case(home_html):
    """Use the homepage shell so the thesis feels like part of the same site."""
    page = BeautifulSoup(home_html, 'html.parser')
    page.body['class'].append('case-page')
    title = 'REDI Investment Case | Hetzerk Asset Management'
    description = 'The Hetzerk Innovation Factor ETF investment case: innovation value, innovation ability and systematic equity portfolio construction.'
    page.title.string = title
    for meta in page.head.select('meta[property="og:title"],meta[name="twitter:title"]'):
        meta['content'] = title
    for meta in page.head.select('meta[name="description"],meta[property="og:description"],meta[name="twitter:description"]'):
        meta['content'] = description
    for anchor in page.select('.home-nav a'):
        if anchor['href'].startswith('#'):
            anchor['href'] = '/' + anchor['href']
        if anchor['href'] == '/#innovation':
            anchor['href'] = '#investment-case'
            anchor['aria-current'] = 'page'
    main = page.find('main')
    main.clear()
    content = f'''
      <section class="case-hero investment-case" id="investment-case" aria-labelledby="investment-title">
        <a class="case-back" href="/etfs/redi/">← Hetzerk Innovation Factor ETF</a>
        <p class="home-eyebrow">REDI / The investment case</p>
        <h1 id="investment-title">Innovation at a<br><span>justifiable valuation.</span></h1>
        <div class="case-hero-bottom"><p>Seek long-term capital appreciation through companies investing in innovation—and turning it into commercial progress.</p><span class="case-signature">Investing in Innovation,<br><strong>REDI for tomorrow</strong></span></div>
        <nav class="case-jump-links" aria-label="Investment case sections"><a href="#why-now">Why now</a><a href="#process">The process</a><a href="#research">The research</a><a href="#long-term">Long-term characteristics</a><a href="#portfolio">The portfolio</a></nav>
      </section>
      <section class="case-thesis investment-case" aria-labelledby="thesis-title">
        <div><p class="home-eyebrow">01 / The idea</p><h2 id="thesis-title">Research today.<br>Business potential tomorrow.</h2></div>
        <div class="case-thesis-copy"><p>Reinvestment in research and development can create new products, capabilities and sources of future cash flow. REDI’s research asks which businesses can turn that investment into commercial success—and what investors pay for that potential.</p>
          <div class="case-cycle" aria-label="Research investment, commercial application, potential future cash flows"><span>Research<br>investment</span><span aria-hidden="true">→</span><span>Commercial<br>application</span><span aria-hidden="true">→</span><span>Potential future<br>cash flows</span></div></div>
      </section>
      {why_now_section()}
      <section class="case-method investment-case" id="process" aria-labelledby="process-title">
        <div class="case-section-heading"><div><p class="home-eyebrow">03 / The process</p><h2 id="process-title">Two lenses.<br>One repeatable process.</h2></div><p>Start with U.S. mid- and large-cap equities. Evaluate innovation value, then innovation ability, and bring the selected companies together in an equally weighted portfolio.</p></div>
        {case_explorer('full-case')}
      </section>
      {research_charts()}
      <section class="case-factor investment-case" aria-labelledby="factor-title">
        <div><p class="home-eyebrow">05 / The perspective</p><h2 id="factor-title">A factor approach<br>to a changing world.</h2><p>Technologies and industries evolve. The research focuses on company characteristics that can be assessed across those changes.</p></div>
        <dl class="case-contrast"><div><dt>Thematic lens</dt><dd>Starts with a particular technology, industry or structural trend.</dd></div><div><dt>REDI’s factor lens</dt><dd>Starts with a company’s innovation activity, commercial ability and valuation.</dd></div></dl>
        {case_visual('timeline')}
      </section>
      {long_term_section()}
      <section class="case-portfolio investment-case" id="portfolio" aria-labelledby="portfolio-title">
        <div class="case-section-heading"><div><p class="home-eyebrow">07 / The portfolio</p><h2 id="portfolio-title">Clear principles.<br>Disciplined implementation.</h2></div><p>Fundamental reasoning informs the signals. A systematic process applies them across the investment universe.</p></div>
        <dl class="case-principles"><div><dt>U.S. equities</dt><dd>Mid- and large-cap companies.</dd></div><div><dt>Equal weighting</dt><dd>Each selected company starts with the same allocation.</dd></div><div><dt>Long-only</dt><dd>Equity exposure, without leverage.</dd></div></dl>
        <details class="case-risk"><summary>Investment considerations <span aria-hidden="true">+</span></summary><p>Innovation may not lead to commercial success. Valuations can decline, and research signals or data may be incomplete or inaccurate. Equal weighting can produce different sector and company exposures from a market-cap-weighted index. The strategy may underperform, and investors can lose principal.</p></details>
      </section>
      <div class="case-return"><div><span class="home-eyebrow">Hetzerk Innovation Factor ETF</span><p>Get to know REDI.</p></div><div><a class="home-text-link" href="/etfs/redi/">Explore the ETF <span aria-hidden="true">↗</span></a><a class="case-doc-link" href="/etfs/redi/#documents">Fund documents</a></div></div>
    '''
    for node in list(BeautifulSoup(content, 'html.parser').contents):
        main.append(node)
    return str(page)
