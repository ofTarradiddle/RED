"""A shared, explicitly labeled research chart for Compare and the REDI page."""
from html import escape


def render_strategy_research(prefix='research', *, mode='pdf', dataset_url=None):
    if mode not in ('pdf', 'comparison'):
        raise ValueError('Unsupported research display mode')
    comparison = mode == 'comparison'
    prefix = escape(prefix, quote=True)
    dataset_url = escape(dataset_url or ('/compare/comparison-research.json' if comparison else '/compare/research.json'), quote=True)
    eyebrow = 'Strategy comparison / Monthly research' if comparison else 'The strategy / Historical backtests'
    title = 'Predicted innovation.<br><em>In context.</em>' if comparison else 'Log returns.<br><em>A longer perspective.</em>'
    intro = 'Explore all nine research series alongside ETF market history. Choose any combination and compare the same monthly dates.' if comparison else 'Follow Innovation Leader, Laggard and the Market Backtest through the monthly research record.'
    coverage = '2002—2026' if comparison else '2003—2026'
    source_caption = 'Monthly research table' if comparison else 'Transcribed from the source tables'
    disclosure = ('Historical strategy research, not REDI’s NAV, Market Price or actual ETF returns. Portfolio definitions, fee treatment and the prediction method have not been independently verified.' if comparison else 'Hypothetical strategy research, not REDI’s NAV, Market Price or actual ETF returns. Source values are rounded to two decimals. Fee and trading-cost treatment is unverified.')
    selection_label = 'Research series' if comparison else 'Research cohorts'
    selection_caption = 'All nine columns are selectable · add any ETF peers' if comparison else 'Innovation Leader + up to 3 comparisons'
    reference = '' if comparison else '<span class="sr-reference-chip"><i aria-hidden="true"></i>Innovation Leader<small>REFERENCE</small></span>'
    selection_actions = ('<div class="sr-selection-actions" role="group" aria-label="Choose research comparisons"><button type="button" data-sr-select="research">All research</button><button type="button" data-sr-select="all">All series</button><button type="button" data-sr-select="reference">Predicted only</button><button type="button" data-sr-select="none">Clear</button><p data-sr-selection-status role="status"></p></div>' if comparison else '')
    legend_note = '<p class="sr-legend-note">Solid lines: research. Dashed lines: ETFs. Select a legend label to emphasize a line without changing the comparison period.</p>' if comparison else ''
    method_record = ('<h3>Observed monthly values</h3><p>The research table contains nine monthly cumulative level series, rounded to two decimals. Each selected line is rebased to 100 at the first shared month-end. No missing months are invented. Selecting an ETF with a shorter record can shorten the comparison.</p><h3>What the column names establish</h3><p>Series names follow the source table. Prediction and portfolio-construction methods are unspecified. Market and Market cap are source research series; neither is identified as SPY, the S&amp;P 500 or the Morningstar US Market Index.</p>' if comparison else '<h3>Observed monthly values</h3><p>The source tables supply monthly cumulative strategy levels, rounded to two decimals. These are transcribed observations, not values estimated from the picture. Each line is rebased to 100 at the first shared month-end. No missing months are invented.</p><h3>The Market Backtest</h3><p>Market Backtest is the source research comparison. Its index identity is unverified; it is not identified as SPY, the S&amp;P 500 or the Morningstar US Market Index.</p>')
    research_link = '<a href="/compare/research-source.tsv" download>Download the source table <span aria-hidden="true">↓</span></a>' if comparison else '<a href="/research/the-measure-of-fire.html">Read the investment research <span aria-hidden="true">↗</span></a>'
    return f'''<section class="sr-panel" data-strategy-research data-sr-mode="{mode}" aria-labelledby="{prefix}-title">
      <div class="sr-heading"><div><p class="sr-eyebrow">{eyebrow}</p><h2 class="sr-title" id="{prefix}-title">{title}</h2><p class="sr-intro">{intro}</p></div><div class="sr-source-badge"><span>MONTHLY OBSERVATIONS</span><strong data-sr-coverage>{coverage}</strong><small>{source_caption}</small></div></div>
      <div class="sr-disclosure"><span class="sr-disclosure-mark" aria-hidden="true">R</span><p>{disclosure}</p></div>
      <div class="sr-selection"><fieldset><legend>{selection_label} <span>{selection_caption}</span></legend><div class="sr-chips" data-sr-research-chips>{reference}<span class="sr-loading">Loading the research record…</span></div></fieldset><fieldset class="sr-etf-fieldset"><legend>Add an ETF <span>Distributions reinvested · shared month-ends</span></legend><div class="sr-chips sr-etf-chips" data-sr-etf-chips></div></fieldset>{selection_actions}</div>
      <div class="sr-chart-top"><div><p data-sr-status role="status">Opening the monthly observations…</p><p class="sr-range" data-sr-range>Each series starts at 100 on the first shared month-end.</p></div><div class="sr-chart-controls"><div class="sr-periods" role="group" aria-label="Research comparison period"><button type="button" data-sr-period="1Y" aria-pressed="false">1Y</button><button type="button" data-sr-period="5Y" aria-pressed="false">5Y</button><button type="button" data-sr-period="10Y" aria-pressed="false">10Y</button><button type="button" data-sr-period="ALL" aria-pressed="true">All</button></div><div class="sr-scales" role="group" aria-label="Chart scale"><button type="button" data-sr-scale="log" aria-pressed="true">Log</button><button type="button" data-sr-scale="linear" aria-pressed="false">Linear</button></div></div></div>
      <p class="sr-warning" data-sr-warning role="status" hidden></p>
      <div class="sr-chart-wrap"><svg class="sr-chart" data-sr-chart viewBox="0 0 960 360" role="img" aria-label="Strategy research chart. Data is loading."></svg><p class="sr-chart-empty" data-sr-empty hidden></p></div>
      <div class="sr-chart-bottom"><ul class="sr-legend" data-sr-legend aria-label="Research chart series"></ul><span data-sr-unit>Growth of 100 · logarithmic scale</span></div>
      {legend_note}
      <div class="sr-inspector"><label for="{prefix}-cursor">Inspect a month <span>Drag or use the arrow keys</span></label><input id="{prefix}-cursor" data-sr-cursor type="range" min="0" max="0" value="0" disabled aria-describedby="{prefix}-readout"><p id="{prefix}-readout" data-sr-readout role="status" aria-live="polite">Select a month to inspect each series.</p></div>
      <div class="sr-results"><div class="sr-results-heading"><h3>Over the shared period.</h3><span>MONTH-END OBSERVATIONS</span></div><p class="sr-table-hint" aria-hidden="true">Swipe for all metrics <span>→</span></p><div class="sr-table-scroll" tabindex="0" role="region" aria-label="Research return comparison; scroll for all columns"><table class="sr-table"><caption class="sr-visually-hidden">Returns and month-end drawdowns for the selected research comparison</caption><thead><tr><th scope="col">Series</th><th scope="col">Cumulative change</th><th scope="col">Annualized growth</th><th scope="col">Month-end drawdown</th></tr></thead><tbody data-sr-table><tr><td colspan="4">Loading monthly observations…</td></tr></tbody></table></div><p class="sr-risk-note">Drawdown uses month-end values and can understate losses within a month. Annualized growth is unavailable for periods shorter than one year.</p></div>
      <details class="sr-method"><summary><span>Read the record behind the chart.</span><span aria-hidden="true">+</span></summary><div class="sr-method-grid"><div><h3>What “Log returns” means here</h3><p>The default view plots growth of 100 on a logarithmic scale. It is not a chart of individual monthly log returns. Linear changes only the chart scale; it does not change observations or calculated returns.</p>{method_record}<h3>Research has limitations</h3><p>These are historical backtests, not live fund performance. Fee, trading-cost and distribution treatment for the research have not been independently verified. The fund’s 0.45% expense ratio is not applied to the backtests. Past performance does not guarantee future results.</p></div><div><h3>Adding market history</h3><p>ETF comparisons use Yahoo market-price observations with distributions reinvested at the ex-date close, sampled at shared month-ends. ETF inception and available history can shorten the period. The backtest’s unverified cost and distribution conventions can differ from the ETF calculation.</p><h3>Source record</h3><p data-sr-source>Source details will appear with the research dataset.</p><ul class="sr-method-notes" data-sr-method-notes></ul><div class="sr-source-links"><a data-sr-research-link href="{dataset_url}" download>Download monthly research data <span aria-hidden="true">↓</span></a><a data-sr-market-link href="/compare/data.json" download>Download ETF observations <span aria-hidden="true">↓</span></a>{research_link}</div></div></div></details>
      <noscript><p class="sr-warning">Enable JavaScript to explore these observations. Monthly research data can be downloaded above.</p></noscript>
    </section>'''


def attach_strategy_research_assets(page):
    for filename, tag in (('strategy-research.css', 'link'),
                          ('comparison-math.js', 'script'),
                          ('strategy-research-math.js', 'script'),
                          ('strategy-research.js', 'script')):
        attribute = 'href' if tag == 'link' else 'src'
        url = '/assets/' + filename
        if page.select_one(f'{tag}[{attribute}="{url}"]'):
            continue
        attrs = {attribute: url}
        attrs.update({'rel': 'stylesheet'} if tag == 'link' else {'defer': ''})
        page.head.append(page.new_tag(tag, attrs=attrs))
