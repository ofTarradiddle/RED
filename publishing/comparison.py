"""A focused, installable ETF comparison workspace in the Hetzerk visual language."""
from bs4 import BeautifulSoup
from publishing.strategy_research import render_strategy_research, attach_strategy_research_assets


def render_comparison():
    html = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#181617">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="REDI Compare">
  <meta name="description" content="Put REDI in perspective. Compare ETF price histories, distributions, drawdowns and risk in a focused Hetzerk workspace.">
  <title>REDI Compare | Hetzerk Asset Management</title>
  <link rel="icon" href="/assets/favicon.svg?v=wing-h-1" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/compare-icon-180.png">
  <link rel="manifest" href="/compare/manifest.webmanifest">
  <link rel="stylesheet" href="/assets/fonts.css">
  <link rel="stylesheet" href="/assets/branding.css">
  <link rel="stylesheet" href="/assets/comparison.css">
  <script src="/assets/comparison-math.js" defer></script>
  <script src="/assets/comparison.js" defer></script>
  <script src="/assets/comparison-install.js" defer></script>
</head>
<body class="comparison-app">
  <a class="compare-skip" href="#main">Skip to comparison</a>
  <div class="demo-strip"><div class="compare-width"><strong>Illustrative demo</strong> * REDI is an illustrative prelaunch series. Yahoo peers are historical market data. This comparison is an interface preview, not an actual REDI track record or an investment offering.</div></div>
  <header class="compare-header compare-width">
    <div class="compare-brand"><a class="hetzerk-logo" href="/" aria-label="Hetzerk Asset Management home"></a><div><a class="compare-wordmark" href="/">Hetzerk</a><span class="compare-brand-caption">Asset Management</span></div><span class="compare-product">Compare</span></div>
    <nav class="compare-header-actions" aria-label="App navigation"><a class="compare-site-link" href="/etfs/redi/">The ETF <span aria-hidden="true">↗</span></a></nav>
  </header>
  <main id="main" class="compare-width">
    <section class="compare-intro" aria-labelledby="compare-title">
      <div><p class="compare-eyebrow">Hetzerk / Compare</p><h1 id="compare-title">REDI, <em>in perspective.</em></h1><p class="compare-intro-copy">A clearer view of performance. A closer look at risk.</p></div>
      <div class="compare-data-status"><span class="compare-status-dot" aria-hidden="true"></span><div><p id="comparison-status" role="status">Loading the latest published data…</p><p id="comparison-updated">Daily closing observations</p></div><button class="compare-icon-button compare-refresh" type="button" data-refresh aria-label="Reload published comparison data"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19 8a8 8 0 1 0 1 7M19 3v5h-5"/></svg></button></div>
    </section>
    <p id="offline-status" class="compare-message" role="status" hidden>You’re offline. Showing the last available comparison.</p>
    <p id="comparison-error" class="compare-message compare-message-error" role="status" hidden></p>
    <noscript><p class="compare-message">Turn on JavaScript to use the comparison. You can also download the data below.</p></noscript>

    <section id="compare" class="compare-instrument" aria-labelledby="performance-heading">
      <div class="compare-panel-heading"><div><p class="compare-eyebrow">01 / Performance</p><h2 id="performance-heading">Growth, on equal terms.</h2></div><span class="compare-index-note">Starting value <strong>100</strong></span></div>
      <div class="compare-controls">
        <fieldset class="compare-peers"><legend>Compare REDI with <span>Choose up to 3 ETFs</span></legend><div class="compare-peer-options">
          <span class="compare-redi-chip"><span class="compare-chip-dot" aria-hidden="true"></span>REDI<span class="compare-chip-caption">Your reference</span></span>
          <label><input type="checkbox" name="peer" value="SPY" checked><span><strong>SPY</strong><small>S&amp;P 500</small></span></label>
          <label><input type="checkbox" name="peer" value="VOO"><span><strong>VOO</strong><small>S&amp;P 500</small></span></label>
          <label><input type="checkbox" name="peer" value="QQQ"><span><strong>QQQ</strong><small>Nasdaq-100</small></span></label>
          <label><input type="checkbox" name="peer" value="ITAN" checked><span><strong>ITAN</strong><small>Intangible value</small></span></label>
          <label><input type="checkbox" name="peer" value="SYLD"><span><strong>SYLD</strong><small>Shareholder yield</small></span></label>
        </div></fieldset>
        <div class="compare-selects"><label for="redi-basis">REDI series<select id="redi-basis"><option value="market_price">Market Price</option><option value="nav">NAV</option></select></label><label for="return-mode">Return calculation<select id="return-mode"><option value="price">Price change</option><option value="reinvested">Distributions reinvested</option></select></label></div>
      </div>
      <div class="compare-chart-heading"><div><p id="comparison-summary">Select your comparison.</p><p id="comparison-range">Aligning available dates…</p></div><div class="compare-periods" role="group" aria-label="Comparison period"><button type="button" data-period="1M" aria-pressed="false">1M</button><button type="button" data-period="3M" aria-pressed="false">3M</button><button type="button" data-period="6M" aria-pressed="false">6M</button><button type="button" data-period="YTD" aria-pressed="false">YTD</button><button type="button" data-period="1Y" aria-pressed="true">1Y</button><button type="button" data-period="ALL" aria-pressed="false">All</button></div></div>
      <div class="compare-chart-wrap"><svg id="comparison-chart" viewBox="0 0 960 400" role="img" aria-label="ETF comparison chart. Data is loading."></svg><p id="chart-empty" class="compare-chart-empty" hidden>No observations are available for this selection.</p></div>
      <div class="compare-chart-footer"><ul id="chart-legend" class="compare-legend" aria-label="Chart series"></ul><span class="compare-chart-unit">Indexed growth · USD</span></div>
      <div class="compare-inspector"><label for="chart-cursor">Inspect a date <span>Drag or use the arrow keys</span></label><input id="chart-cursor" type="range" min="0" max="0" value="0" aria-describedby="chart-readout" disabled><p id="chart-readout" role="status" aria-live="polite">Choose a date to inspect each series.</p></div>
    </section>

    <div class="compare-detail-grid">
      <section id="risk" class="compare-risk-panel" aria-labelledby="risk-heading"><div class="compare-section-heading"><div><p class="compare-eyebrow">02 / Risk &amp; return</p><h2 id="risk-heading">The path matters.</h2></div><span class="compare-section-aside">Same dates. Same calculation.</span></div><div class="compare-table-scroll" tabindex="0" role="region" aria-label="Risk and return comparison; scroll horizontally for all columns"><table id="risk-table"><caption class="compare-sr-only">Risk and return metrics for the selected comparison period</caption><thead><tr><th scope="col">Series</th><th scope="col">Change</th><th scope="col">Max drawdown</th><th scope="col">Volatility</th><th scope="col">Correlation<br>to REDI</th></tr></thead><tbody><tr><td colspan="5">Loading comparison metrics…</td></tr></tbody></table></div><p id="risk-status" class="compare-panel-note"></p><p class="compare-panel-note">Drawdown measures the largest fall from a previous peak. Volatility measures variation in daily returns, annualized.</p></section>
      <section id="fund" class="compare-fund-panel" aria-labelledby="fund-heading"><div class="compare-fund-topline"><p class="compare-eyebrow">03 / The reference</p><span class="compare-fund-ticker">REDI</span></div><h2 id="fund-heading">Hetzerk Innovation<br>Factor ETF</h2><p id="fund-asof" class="compare-fund-date">Latest published fund snapshot</p><dl class="compare-fund-facts"><div><dt>NAV</dt><dd id="fund-nav">—</dd></div><div><dt>Market Price</dt><dd id="fund-price">—</dd></div><div><dt>Premium / Discount</dt><dd id="fund-premium">—</dd></div><div><dt>Expense ratio</dt><dd>0.45% <small>45 bps</small></dd></div></dl><div class="compare-fund-links"><a href="/etfs/redi/holdings.html">Holdings <span aria-hidden="true">↗</span></a><a href="/etfs/redi/#documents">Fund documents <span aria-hidden="true">↗</span></a></div></section>
    </div>

    <section class="compare-method-section" aria-label="Methodology and sources"><details id="methodology"><summary><span><span class="compare-eyebrow">04 / Behind the numbers</span><span class="compare-method-title">A comparison you can examine.</span></span><span class="compare-expand" aria-hidden="true">+</span></summary><div class="compare-method-content"><div><h3>One starting point</h3><p>Each selected series starts at 100 on the first date shared by all selected series within the chosen period. Only common observation dates are used. YTD uses the final shared close of the previous year when available. Adding a fund with a shorter history can shorten the comparison.</p><h3>Price or reinvestment</h3><p>Price change excludes distributions. Distributions reinvested assumes reinvestment at the closing price on the ex-date. Split-adjusted prices and distributions are used consistently so splits are not counted twice. Peer series use market prices; they are not fund NAV returns.</p><h3>Risk, measured consistently</h3><p>Maximum drawdown is the largest peak-to-trough decline across the matched closing dates in the selected period. Volatility is the sample standard deviation of daily returns multiplied by the square root of 252. Correlation compares each series’ daily returns with REDI. At least 20 return observations are required for volatility and correlation; correlation is unavailable when either series has zero variance. Volatility and correlation are withheld when matched observations skip a trading session present in the peer histories.</p></div><div><h3>What the figures include</h3><p>Changes reflect the selected return calculation and exclude investor commissions and taxes. Fund expenses are reflected in observed prices and NAV; the expense ratio is not subtracted again. Historical performance does not guarantee future results. Investments can lose value.</p><h3>Daily data, visible dates</h3><p>This app reads a published daily dataset. Refresh reloads that dataset; it does not request live quotes. Source dates may differ from the date the app was published. Saved data remains available offline after a successful visit.</p><h3>Sources</h3><ul id="comparison-sources" class="compare-sources"><li>Source details will appear when the dataset loads.</li></ul><a id="comparison-data-link" class="compare-data-link" href="/compare/data.json" download>Download comparison data <span aria-hidden="true">↓</span></a></div></div></details></section>
  </main>
  <footer class="compare-footer compare-width"><p>Hetzerk Asset Management<span class="compare-footer-tagline">Innovation, examined.</span></p><div><a href="/">Main site</a><a href="/disclosures/">Disclosures</a><a href="/privacy/">Privacy</a></div></footer>
  <nav class="compare-dock" aria-label="Comparison sections"><a href="#compare"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 4v16h16M7 15l4-5 4 3 5-7"/></svg><span>Compare</span></a><a href="#risk"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 17h3V9H4zm7 0h3V5h-3zm7 0h3V12h-3zM3 21h19"/></svg><span>Risk</span></a><a href="#fund"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 5v14m14-14v14M5 12h14"/></svg><span>REDI</span></a><a href="#methodology"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/></svg><span>Method</span></a></nav>
</body></html>'''

    page = BeautifulSoup(html, 'html.parser')
    periods = ('1M', '3M', '6M', 'YTD', '1Y', '3Y', '5Y', '10Y', '12Y', '15Y', '18Y', '20Y', 'ALL', 'CUSTOM')
    controls = page.select_one('.compare-periods')
    controls.clear()
    for period in periods:
        button = page.new_tag('button', attrs={'type': 'button', 'data-period': period, 'aria-pressed': str(period == '1Y').lower()})
        button.string = 'All' if period == 'ALL' else 'Custom' if period == 'CUSTOM' else period
        controls.append(button)
    dates = BeautifulSoup('<form id="comparison-custom-dates" class="compare-custom-dates" hidden><label for="comparison-start-date">Start date<input id="comparison-start-date" type="date" required></label><label for="comparison-end-date">End date<input id="comparison-end-date" type="date" required></label><button type="submit">Apply range</button><p id="comparison-date-error" role="status" aria-live="polite"></p></form><p id="comparison-coverage-note" class="compare-coverage-note" role="status" hidden></p>', 'html.parser')
    heading = page.select_one('.compare-chart-heading')
    for node in reversed(list(dates.contents)):
        heading.insert_after(node)
    attach_strategy_research_assets(page)
    main = page.find('main')
    chart = main.find(id='compare')
    fund_view = page.new_tag('div', attrs={
        'id': 'comparison-etf-view', 'role': 'tabpanel',
        'aria-labelledby': 'comparison-etf-tab', 'data-comparison-view-panel': 'etf',
    })
    chart.insert_before(fund_view)
    collecting = False
    for child in list(main.contents):
        if child is chart:
            collecting = True
        if collecting:
            fund_view.append(child.extract())
    tabs = BeautifulSoup('''<div class="comparison-view-tabs" role="tablist" aria-label="Comparison view"><button type="button" role="tab" id="comparison-etf-tab" data-comparison-view="etf" aria-selected="true" aria-controls="comparison-etf-view">ETF comparison<small>NAV &amp; MARKET PRICE</small></button><button type="button" role="tab" id="comparison-research-tab" data-comparison-view="research" aria-selected="false" aria-controls="comparison-research" tabindex="-1">Strategy research<small>MONTHLY HISTORICAL BACKTESTS</small></button></div>''', 'html.parser').div
    fund_view.insert_before(tabs)
    research_view = page.new_tag('div', attrs={
        'id': 'comparison-research', 'role': 'tabpanel', 'hidden': '',
        'aria-labelledby': 'comparison-research-tab', 'data-comparison-view-panel': 'research',
    })
    research_view.append(BeautifulSoup(render_strategy_research('compare-research', mode='comparison'), 'html.parser').section)
    main.append(research_view)
    research_link = page.select_one('.compare-dock a[href="#methodology"]')
    research_link['href'] = '#comparison-research'
    research_link.find('span').string = 'Research'
    return str(page)
