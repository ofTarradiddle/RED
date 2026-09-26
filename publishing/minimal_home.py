"""A compact homepage; fund and Section 351 pages retain their own layouts."""
from bs4 import BeautifulSoup

from publishing.site import pct
from publishing.investment_case import attach_assets, exchange_sticker, home_case


def render_home(html, fund):
    page = BeautifulSoup(html, 'html.parser')
    banner = str(page.select_one('.demo-strip'))
    page.body.clear()
    page.body['class'] = ['restored-site', 'home-minimal']
    for style in page.head.find_all('style'):
        style.decompose()
    page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/minimal-home.css'))
    attach_assets(page)
    title = 'Hetzerk Asset Management | Investing in Innovation, REDI for tomorrow'
    page.title.string = title
    for meta in page.head.select('meta[property="og:title"],meta[name="twitter:title"]'):
        meta['content'] = title
    description = 'Hetzerk Innovation Factor ETF. Explore REDI, fund expenses, the investment case and Section 351 contribution opportunities.'
    for meta in page.head.select('meta[name="description"],meta[property="og:description"],meta[name="twitter:description"]'):
        meta['content'] = description
    contents = f'''
    <a class="skip" href="#main">Skip to content</a>
    {banner}
    <header class="home-header">
      <div class="home-width home-header-row justify-between">
        <div class="home-brand">
          <a class="hetzerk-logo" href="/" aria-label="Hetzerk Asset Management home"></a>
          <div class="hetzerk-lockup"><div class="hetzerk-masthead-name">Hetzerk</div><div class="hetzerk-masthead-subtitle">Asset Management</div></div>
        </div>
        <nav class="home-nav" aria-label="Main navigation">
          <a href="/etfs/redi/">The ETF</a><a href="/#fees">Expenses</a><a href="/etfs/redi/why-red.html">Investment case</a><a href="/research/">Research</a><a href="/#contact">Section 351</a>
        </nav>
      </div>
    </header>
    <main id="main" class="home-width">
      <section class="home-hero" aria-labelledby="home-title">
        <div class="home-intro home-fund-premise" id="about">
          <p class="home-eyebrow">REDI / Systematic U.S. equities</p>
          <h1 id="home-title">Hetzerk Innovation <span>Factor ETF</span></h1>
          <p class="home-fund-objective">Seeks long-term capital appreciation through U.S. mid- and large-cap companies, selected using innovation value and innovation ability.</p>
          <p class="home-signature">Investing in Innovation,<br><em>REDI for tomorrow.</em></p>
          <nav class="home-fund-links" aria-label="REDI fund information"><a href="/etfs/redi/holdings.html">Holdings <span aria-hidden="true">↗</span></a><a href="/etfs/redi/#documents">Fund documents <span aria-hidden="true">↗</span></a><a href="/etfs/redi/why-red.html">Investment case <span aria-hidden="true">↗</span></a></nav>
        </div>
        <div id="etfs" class="home-fund">
          <a class="etf-card home-fund-card" href="/etfs/redi/" aria-label="Explore the Hetzerk Innovation Factor ETF, REDI" aria-describedby="home-card-slogan">
            <span class="home-card-top"><span>U.S. equities</span><span aria-hidden="true">↗</span></span>
            <strong class="home-ticker">REDI</strong>
            <h2>Hetzerk Innovation <br>Factor ETF</h2>
            <span class="home-card-slogan" id="home-card-slogan">Innovation is the <span class="home-slogan-accent">DIF</span>erence</span>
            <dl class="home-fund-facts"><div><dt>Annual expense ratio</dt><dd>{pct(fund['expense_ratio'])}</dd></div><div><dt>Investment universe</dt><dd>U.S. mid- &amp; large-cap</dd></div><div><dt>Portfolio approach</dt><dd>Equal weighting</dd></div><div><dt>Exposure</dt><dd>Long-only equities</dd></div></dl>
            <span class="home-card-link">Explore the ETF <span aria-hidden="true">→</span></span>
          </a>
        </div>
      </section>
      <section id="contact" class="home-solicitation" aria-labelledby="contribution-heading">
        <div class="home-solicitation-copy">
          <p class="home-eyebrow">Section 351 interest</p>
          <h2 id="contribution-heading">Start with what you own.</h2>
          <p>Explore contributing an eligible portfolio to an ETF in a potentially tax-deferred exchange.</p>
          <p class="home-fine-print">Under the usual diversified-portfolio route, each contributor’s proposed portfolio can have no more than 25% in one issuer and no more than 50% in any five or fewer issuers. Exclusions and look-through rules apply; these limits alone do not establish eligibility.</p>
          <p class="home-fine-print">Eligibility and tax treatment depend on the transaction and your circumstances. Registering interest does not create an investment commitment.</p>
          <div class="home-351-actions"><a class="home-secondary-link" href="/section-351.html">How Section 351 works <span aria-hidden="true">↗</span></a><a class="home-secondary-link" href="/351-exchanges.html">351 opportunities <span aria-hidden="true">→</span></a></div>
          <p class="home-fine-print"><a class="home-secondary-link" href="/assets/guides/section-351-contributions.pdf" type="application/pdf">Read the Hetzerk Section 351 guide (PDF) <span aria-hidden="true">↗</span></a></p>
          {exchange_sticker()}
        </div>
        <form id="register" class="home-interest-form" data-interest-form="" data-recipient="info@ofnectar.com" action="#register" method="post" aria-label="Section 351 interest">
          <div class="home-form-heading"><h3>Register your interest</h3><p>Tell us about the portfolio you have in mind.</p></div>
          <div class="home-form-row">
            <div><label for="home-name">Full name</label><input id="home-name" name="name" type="text" autocomplete="name" required placeholder="Azabov Solov"></div>
            <div><label for="home-email">Email address</label><input id="home-email" name="email" type="email" autocomplete="email" required placeholder="azabov@example.com"></div>
          </div>
          <div class="home-form-row">
            <div><label for="home-type">Investor type</label><select id="home-type" name="type" required><option value="" disabled selected>Select one</option><option value="ria">Registered Investment Advisor</option><option value="family-office">Family Office</option><option value="hnw">High Net Worth Individual</option><option value="institutional">Institutional Investor</option><option value="other">Other</option></select></div>
            <div><label for="home-fund">Interested fund</label><select id="home-fund" name="fund"><option value="REDI">REDI — Innovation Factor ETF</option></select></div>
          </div>
          <div><label for="home-notes">Notes <span>(optional)</span></label><textarea id="home-notes" name="notes" rows="2" placeholder="Concentrated positions, estimated contribution size or questions"></textarea></div>
          <button type="submit" class="home-interest-submit">Prepare interest email <span aria-hidden="true">↗</span></button>
          <p class="interest-status" aria-live="polite"></p>
        </form>
      </section>
      <section id="fees" class="home-expenses" aria-labelledby="expense-heading">
        <div><h2 id="expense-heading" class="home-eyebrow">Annual expense ratio</h2><p class="home-fee">{pct(fund['expense_ratio'])}<span>{fund['expense_ratio']*10000:g} basis points</span></p></div>
        <div class="home-fee-copy"><p>Fund operating expenses are reflected in NAV. Brokerage commissions and other transaction costs may also apply.</p><a class="home-text-link" href="/etfs/redi/#documents">Full expense details <span aria-hidden="true">↗</span></a></div>
      </section>
      {home_case()}
    </main>
    <footer class="home-footer restored-footer">
      <div class="home-width">
        <div class="home-footer-top"><p>Hetzerk Asset Management</p><nav aria-label="Footer navigation"><a href="/research/">Research</a><a href="/documents/">Fund documents</a><a href="/disclosures/">Disclosures</a><a href="/privacy/">Privacy</a></nav></div>
        <p class="home-risk">Investing involves risk, including possible loss of principal. Review the investment objective, risks, charges and expenses before investing.</p>
        <div class="home-footer-base border-t"><span>© <span class="current-year">2026</span> Hetzerk Asset Management</span><span data-perspective-word="">Perspective</span></div>
      </div>
    </footer>'''
    for node in list(BeautifulSoup(contents, 'html.parser').contents):
        page.body.append(node)
    return str(page)
