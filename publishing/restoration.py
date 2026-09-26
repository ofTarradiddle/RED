"""Preserve the original site's layouts and editorial content; bind validated data.

Templates are the restored original pages, not disposable generated output.
Only data surfaces, shared branding/navigation and specific demo disclosures change.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, NavigableString

from publishing.site import esc, money, pct, holdings_table
from publishing.documents import library_body, fact_sheet_body, quick_document_url

ROOT = Path(__file__).resolve().parents[1]
BRAND = 'Hetzerk Asset Management'
THEMES = {'redi':'#8b0000','dam1':'#111111','azoc':'#4a0080','mpd':'#9B3A5C','meri':'#B8860B'}


def soup(html):
    return BeautifulSoup(html, 'html.parser')


def fragment(html):
    return soup(html)


def contents(tag, html):
    tag.clear()
    for child in list(fragment(html).contents):
        tag.append(child)


def text_at(page, selector, value):
    for tag in page.select(selector):
        tag.clear()
        tag.append(str(value))


def heading(page, value):
    return next((h for h in page.find_all(['h1','h2','h3','h4']) if h.get_text(' ',strip=True).rstrip(':') == value.rstrip(':')),None)


def footer():
    return fragment(f'''<footer class="cambria-footer restored-footer"><div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12"><div class="grid md:grid-cols-3 gap-10"><div><h3 class="text-xl font-bold text-white mb-4 elegant-heading">{BRAND}</h3><p class="text-gray-300 text-sm leading-relaxed">Innovation-Driven, Research-Grounded. Systematic equity investing informed by fundamental research.</p></div><div><h3 class="text-white font-bold mb-4">Explore</h3><div class="grid grid-cols-2 gap-3 text-sm text-gray-300"><a href="/">Home</a><a href="/etfs/">Our ETFs</a><a href="/research/">Research</a><a href="/section-351.html">Section 351</a><a href="/351-exchanges.html">351 Opportunities</a><a href="/review/">Excel review guide</a><a href="/disclosures/">Disclosures</a><a href="/privacy/">Privacy</a></div></div><div><h3 class="text-white font-bold mb-4">Demo review</h3><p class="text-gray-400 text-sm leading-relaxed">Illustrative portfolios and performance. Proposed terms are subject to change. No fund registration or availability is represented. Investing involves risk, including loss of principal.</p><a class="text-gray-300 text-sm underline block mt-3" href="/form-crs.html">Form CRS status</a></div></div><div class="border-t border-gray-700 mt-8 pt-5 text-xs text-gray-400">© 2026 {BRAND}. Local demo preview.</div></div></footer>''').footer


def prepare(raw, route):
    page = soup(raw)
    if not page.head or not page.body:
        return None
    # Legacy page scripts contain disconnected data fallbacks and debug overlays.
    for tag in page.find_all('script'):
        tag.decompose()
    for tag in page.find_all('meta'):
        if tag.get('http-equiv') or tag.get('name') in ('robots','description') or tag.get('property','').startswith('og:'):
            tag.decompose()
    for tag in page.find_all('link'):
        if tag.get('rel') and ('stylesheet' in tag['rel'] or 'icon' in tag['rel']):
            tag.decompose()
    for tag in page.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith('on'):
                if attr=='onclick' and 'toggleMobileMenu' in tag[attr]:
                    tag['data-menu-toggle']='mobileMenu'
                if attr=='onclick' and tag[attr] in ('nextSlide()','previousSlide()'):
                    tag['data-slide-step']='1' if tag[attr]=='nextSlide()' else '-1'
                if attr=='onclick' and tag[attr]=='handleDisclaimerAgree()':
                    tag['data-research-agree']=''
                if attr=='onclick' and tag[attr]=='handleDisclaimerCancel()':
                    tag['data-research-cancel']=''
                del tag[attr]
    disclaimer = page.find(id='disclaimerOverlay')
    if disclaimer:
        # Preserve this interaction when legacy inline scripts are removed.
        # A native dialog form also lets Agree dismiss the notice without JS.
        disclaimer.name = 'dialog'
        disclaimer['open'] = ''
        title = disclaimer.find('h2')
        title['id'] = 'research-disclaimer-title'
        title['tabindex'] = '-1'
        title['autofocus'] = ''
        disclaimer['aria-labelledby'] = title['id']
        agree = disclaimer.select_one('[data-research-agree]')
        agree['type'] = 'submit'
        agree['value'] = 'agree'
        actions = agree.parent
        actions.name = 'form'
        actions['method'] = 'dialog'
        cancel = disclaimer.select_one('[data-research-cancel]')
        cancel.name = 'a'
        cancel['href'] = '/'
    for node in list(page.find_all(string=True)):
        if node.parent.name in ('style','script'):
            continue
        value=str(node)
        value=re.sub(r'\bDAM\b',BRAND,value)
        value=value.replace('D&D',BRAND).replace('ETF ETF','ETF')
        value=value.replace('REDI Innovation Factor ETF','Hetzerk Innovation Factor ETF')
        value=value.replace('About Hetzerk','About '+BRAND)
        if value!=str(node):node.replace_with(value)
    # Keep compact logo marks while stating the full brand in page titles/footer.
    text_at(page,'.company-logo',BRAND)
    # Tiny square monograms remain readable; the full firm name is adjacent.
    for node in page.select('header span'):
        if node.get_text(strip=True)==BRAND and not node.find(True):node.string='H'
    for p in page.find_all(['p','div','strong']):
        if p.find(['p','div','section','h1','h2','h3','strong']):continue
        t=p.get_text(' ',strip=True)
        if re.search(r'(?:is a registered investment advis[oe]r|is registered with the SEC|SEC Registered|registered investment company under)',t,re.I):
            p.string='Proposed investment strategies from Hetzerk Asset Management. Registration and offering details remain unverified in this demo.'
    for node in page.find_all(string=True):
        if node.parent.name not in ('script','style'):
            t=str(node)
            t=t.replace('123 Main Street, Suite 1000, New York, NY 10001','Contact location to be confirmed')
            t=t.replace('(555) 123-4567','Contact details to be confirmed')
            if t!=str(node):node.replace_with(t)
    for a in page.select('a[href]'):
        href=a['href']
        if href.startswith('tel:') or 'hetzerk.example' in href or 'info@dbe.com' in href:
            a['href']='/#contact';a.string='Contact information'
        elif not urlsplit(href).scheme and not href.startswith('#'):
            absolute=urljoin('/'+route,href)
            if absolute=='/research':absolute='/research/'
            if absolute.startswith('/blog/'):absolute='/etfs/redi'+absolute
            if absolute in ('/#strategy','/#performance','/#blog'):
                absolute={'/#strategy':'/etfs/redi/#overview','/#performance':'/etfs/redi/#performance','/#blog':'/etfs/redi/blog/'}[absolute]
            a['href']=absolute.replace('/redetf/','/')
        elif href.startswith('#') and href[1:] in ('innovation','services','fees','about','contact') and not page.find(id=href[1:]):
            a['href']='/'+href
    for h in page.find_all(['h1','h2','h3']):
        if h.get_text(' ',strip=True)=='Section 351 Exchanges':
            subtitle=h.find_next_sibling('p')
            if subtitle and 'tax-free' in subtitle.get_text().lower():
                subtitle.string='Explore potential tax-deferred contributions to a new ETF.'
    for old in page.find_all('footer'):
        old.replace_with(footer())
    if not page.find('footer'):page.body.append(footer())
    page.body['class']=page.body.get('class',[])+['restored-site']
    title=page.title.get_text(' ',strip=True) if page.title else BRAND
    title=re.sub(r'\s*\|\s*Hetzerk(?: Asset Management)?$', '',title)
    if route=='index.html':title=BRAND+' | Innovation-Driven, Research-Grounded'
    elif BRAND not in title:title+=' | '+BRAND
    if not page.title:page.head.append(page.new_tag('title'))
    page.title.string=title
    description=next((p.get_text(' ',strip=True) for p in page.select('section p, article p') if p.get_text(strip=True)), 'Explore the investment strategies and research of '+BRAND)
    for attrs in [dict(name='description',content=description[:240]),dict(name='robots',content='noindex,nofollow'),dict(property='og:title',content=title),dict(property='og:description',content=description[:240]),dict(property='og:type',content='website'),dict(name='twitter:card',content='summary_large_image'),dict(name='twitter:title',content=title),dict(name='twitter:description',content=description[:240])]:
        page.head.append(page.new_tag('meta',attrs=attrs))
    if route=='index.html':
        for key in ('og:image','twitter:image'):
            page.head.append(page.new_tag('meta',attrs={('property' if key.startswith('og') else 'name'):key,'content':'http://localhost:8080/assets/hetzerk-social.png'}))
    # Utilities precede the original page's component styles.
    for href in reversed(['/assets/fonts.css','/assets/original-utilities.css']):
        page.head.insert(0,page.new_tag('link',attrs={'rel':'stylesheet','href':href}))
    page.head.append(page.new_tag('link',attrs={'rel':'stylesheet','href':'/assets/restored.css'}))
    page.head.append(page.new_tag('link',attrs={'rel':'icon','href':'/assets/favicon.svg?v=wing-h-1','type':'image/svg+xml'}))
    for src in ('/assets/vendor/lucide.min.js','/assets/site.js','/assets/restored.js'):
        page.head.append(page.new_tag('script',attrs={'src':src,'defer':''}))
    if disclaimer:
        page.head.append(page.new_tag('link',rel='stylesheet',href='/assets/research-disclaimer.css'))
        page.head.append(page.new_tag('script',src='/assets/research-disclaimer.js',defer=''))
    if page.find(id='innovationStoryChart'):
        for src in ('/assets/vendor/chart.umd.js','/assets/innovation-case.js'):
            page.head.append(page.new_tag('script',attrs={'src':src,'defer':''}))
        for canvas in page.find_all('canvas'):
            canvas['role']='img';canvas['aria-label']='Illustrative conceptual comparison, not actual performance'
            canvas.parent.insert_after(fragment('<p class="text-sm text-gray-500 mt-3">Illustrative conceptual comparison from the original investment case. Fictional values; not a backtest, actual fund return or verified index history.</p>').p)
    banner=fragment('<div class="demo-strip">Illustrative demo · Fund data and benchmark returns are fictional · Not an investment offering</div>').div
    page.body.insert(0,banner)
    main=page.find('main') or page.find('article') or page.find('section') or page.body.find('div')
    if main and not page.find(id='main'):
        if main.get('id'):
            marker=page.new_tag('span',id='main');main.insert(0,marker)
        else:main['id']='main'
    page.body.insert(0,fragment('<a class="skip" href="#main">Skip to content</a>').a)
    for form in page.find_all('form'):
        if form.get('id')=='newsletterForm':
            form['data-newsletter-demo']='';form['action']='#newsletter-status';form['method']='post'
            form.insert_after(fragment('<p id="newsletter-status" class="text-sm mt-4" aria-live="polite">Newsletter integration is not connected in this local demo.</p>').p)
    return page


def paragraph_under(page, name, paragraphs):
    h=heading(page,name)
    if not h:return
    targets=h.parent.find_all('p',recursive=False)
    for i,value in enumerate(paragraphs):
        if i<len(targets):targets[i].string=value
        else:
            p=page.new_tag('p',attrs={'class':'text-gray-600 leading-relaxed mb-4'});p.string=value;h.parent.append(p)


def contribution_diversification():
    return fragment('''<aside id="contribution-diversification" class="exchange-eligibility" aria-labelledby="contribution-diversification-title">
      <p class="exchange-eligibility-kicker">Before proposing assets</p>
      <h2 id="contribution-diversification-title">Diversification starts with your contribution.</h2>
      <p>For the usual already-diversified-portfolio route, assess <strong>each contributor’s proposed portfolio</strong> separately. The combined ETF portfolio and other investors’ holdings do not establish your eligibility.</p>
      <dl class="exchange-eligibility-limits">
        <div><dt>One issuer</dt><dd><span>25%</span> maximum</dd></div>
        <div><dt>Any five or fewer issuers</dt><dd><span>50%</span> maximum</dd></div>
      </dl>
      <p>These are fair-market-value tests with prescribed exclusions, issuer grouping and look-through rules. Cash and cash items are excluded, so adding cash does not cure a concentration. Assets acquired to satisfy the tests are also excluded.</p>
      <p>An appreciated single-stock position does not automatically qualify. Meeting these limits alone does not establish Section 351 qualification. Proposed holdings also require review against REDI’s equity-only investment approach and operational requirements; acceptance is not assured.</p>
      <div class="exchange-eligibility-links"><a class="exchange-guide-link" href="/assets/guides/section-351-contributions.pdf" type="application/pdf"><span>Read the Hetzerk Section 351 guide (PDF)</span><span aria-hidden="true">↗</span></a><a class="exchange-rule-link" href="https://www.ecfr.gov/current/title-26/section-1.351-1#p-1.351-1(c)(6)">Diversified-portfolio rule · 26 CFR § 1.351-1(c)(6)</a></div>
      <p class="exchange-eligibility-note">Educational information, not tax advice. Review the full transaction with your tax adviser before contributing assets.</p>
    </aside>''').aside


def restore_tax(page, route):
    for h in page.find_all('h1'):
        p=h.find_next_sibling('p')
        if p:p.string='Explore potential tax-deferred contributions to a new ETF.'
    paragraph_under(page,'What is Section 351?',[
        'Section 351 can defer recognition of gain when qualifying property is contributed to a corporation for stock and the statutory conditions are met. A proposed ETF contribution requires review of the transferors, contributed portfolio, control requirements, and investment-company exception.',
        'A qualifying contribution can provide a way to transition an eligible portfolio into ETF shares. Eligibility and tax treatment depend on the complete transaction and each investor’s circumstances.'])
    overview=heading(page,'What is Section 351?')
    if overview:
        overview.parent.insert_after(contribution_diversification())
    statements={
        'Control Requirement:':'Transferors generally must control the corporation immediately after the exchange. The statutory voting-power and nonvoting-stock tests are one part of qualification; meeting the control test alone is insufficient.',
        'Property for Stock:':'Qualifying property is contributed for stock. Cash or other property received can cause gain recognition and requires separate analysis.',
        'No Boot:':'Transfers to investment companies are subject to additional restrictions, including diversification rules. An appreciated single-stock position does not automatically qualify.',
        'Tax-Efficient Creation/Redemption:':'Potential tax deferral depends on the complete contribution transaction, investor eligibility and applicable tax rules.',
        'In-Kind Redemptions:':'Delivering securities in kind may reduce portfolio sales. It does not guarantee no capital-gain distributions or no investor tax.',
        'Basis Preservation:':'Qualifying contributions generally carry tax basis into received shares, subject to applicable adjustments. Preserve lot-level basis records for review.'}
    for strong in list(page.find_all('strong')):
        key=strong.get_text(' ',strip=True)
        if key in statements:
            label='Investment-Company Exception:' if key=='No Boot:' else key
            contents(strong.parent,f'<strong>{label}</strong> {statements[key]}')
    for label in ('Creation Process','Creation Units'):
        paragraph_under(page,label,['An authorized participant exchanges an agreed basket for a fund-specific creation unit. Routine ETF creations do not automatically qualify under Section 351; a proposed launch contribution needs separate eligibility and tax review.'])
    for label in ('Redemption Process','Redemption Units'):
        paragraph_under(page,label,['An authorized participant may exchange creation units for securities and/or cash under the fund’s procedures. Tax treatment is assessed separately for the fund and transacting investor; redemption is not universally tax-free under Section 351.'])
    for label in ('Creation Units','Redemption Units'):
        h=heading(page,label)
        if h:
            ul=h.parent.find('ul')
            if ul:contents(ul,'<li>Review transaction qualification and consideration.</li><li>Document tax basis and holding periods.</li><li>Determine applicable gain recognition.</li>')
    for label,copy in {
        'Tax Efficiency':'Potential benefits depend on the structure and qualification of the transaction. An ETF wrapper does not eliminate investment or tax risk.',
        'In-Kind Redemptions':'Delivering securities in kind may reduce the need for portfolio sales. It does not guarantee that the fund avoids capital-gain distributions or that a redeeming investor owes no tax.',
        'Basis Preservation':'Qualifying contributions generally carry tax basis into the received shares, subject to applicable adjustments. Preserve lot-level basis records for review.',
        'Custom Baskets':'A custom creation or redemption basket is an operational arrangement under the fund’s adopted procedures. It does not establish qualification for Section 351.',
        'Cash-in-Lieu':'Cash substitutions require operational and tax analysis. Cash or other consideration may cause gain recognition depending on the transaction.',
        'Individual Investors':'Ordinary exchange trading has its own tax treatment. A proposed launch contribution requires separate eligibility and transaction review.'}.items():paragraph_under(page,label,[copy])
    opportunities=page.find(id='opportunities')
    if opportunities:
        h=opportunities.find('h2')
        if h:
            intro=h.find_next_sibling('p')
            if intro:intro.string='Explore contributing an eligible portfolio of appreciated securities to a proposed Hetzerk ETF at launch. Potential tax deferral depends on Section 351 qualification and individual review.'
            h.insert_after(fragment('<p class="text-sm text-gray-500 mb-4">Illustrative pipeline. Tickers, launch dates, expenses, and targets are proposed and subject to change. Credit and multi-asset concepts below are historical pipeline ideas outside the current equity-only scope.</p>').p)
        for node in list(opportunities.find_all(string=True)):
            t=str(node)
            t=re.sub(r'No [Cc]apital [Gg]ains [Tt]oday','Potential Tax Deferral',t)
            t=t.replace('Tax-Free Diversification','Potential Tax Deferral').replace('Tax-Free Exchange','Potential Tax-Deferred Exchange')
            if t!=str(node):node.replace_with(t)
        for ticker in ('DMVP','DSCB','DSHR','DCRR'):
            title=next((t for t in opportunities.find_all(['h3','div']) if t.get_text(' ',strip=True)==ticker),None)
            if not title:continue
            card=title.find_parent(class_='launch-card') or title.find_parent(class_='cambria-card')
            if card:
                card.name='a';card['href']='#register';card['data-interest-fund']=ticker
                card['aria-label']=f'Register interest in {ticker}'
    configure_interest_form(page)
    cross='/351-exchanges.html' if route=='section-351.html' else '/section-351.html'
    first=page.find('h1')
    if first:first.parent.append(fragment(f'<p class="mt-4 text-sm"><a class="text-red-800 underline" href="{cross}">Explore the other Section 351 overview and opportunities →</a></p>').p)
    # Remove remaining categorical promises while retaining their original boxes.
    qualify_tax_copy(page)


def configure_interest_form(page):
    form=page.find('form')
    if form:
        if not page.find(id='register'):form.parent['id']='register'
        form['data-interest-form']='';form['data-recipient']='info@ofnectar.com'
        form['action']='#register';form['method']='post'
        for field in form.find_all(['input','select','textarea']):
            field['name']=field['id'].split('-',1)[-1]
        button=form.find('button',type='submit')
        if button:button.string='Prepare Interest Email'
        form.append(fragment('<p class="interest-status text-sm mt-3" aria-live="polite"></p>').p)


def qualify_tax_copy(page):
    for node in list(page.find_all(string=True)):
        if node.parent.name in ('style','script'):continue
        t=str(node)
        t=re.sub(r'no capital gains today','tax deferral requires qualification',t,flags=re.I)
        t=re.sub(r'tax-free diversification','potential tax-deferred diversification',t,flags=re.I)
        t=t.replace('tax-free exchanges','qualifying tax-deferred exchanges')
        t=t.replace('Tax-Free ETF Exchanges','Potential Tax-Deferred ETF Contributions')
        if 'Receive diversified ETF shares' in t or 'No capital gains tax' in t:
            t='Receive ETF shares if the contribution is accepted and the transaction qualifies. Tax deferral is not guaranteed.'
        if t!=str(node):node.replace_with(t)


def card(title,body):
    return f'<div class="cambria-card p-6 mb-8"><h3 class="text-lg font-semibold text-gray-900 mb-5">{title}</h3>{body}</div>'


def table_returns(f, labels):
    rows=[]
    for label in labels:
        r=f['returns'][label]
        values=[pct(r[k],True) if r else 'Unavailable' for k in ('nav_total_return','market_total_return','benchmark_index')]
        rows.append(f'<tr><th scope="row">{label}{" (annualized)" if r and r["annualized"] else ""}</th>'+''.join(f'<td>{v}</td>' for v in values)+'</tr>')
    return '<div class="table-scroll"><table><thead><tr><th>Period</th><th>NAV</th><th>Market Price</th><th>Benchmark</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def fund_performance(f):
    fid=f['fund_id']
    exception_days=sum(abs(row['premium_discount']) > .02 for row in f['daily'])
    periods=''.join(f'<button type="button" data-period="{p}" aria-pressed="{str(p=="ALL").lower()}">{p}</button>' for p in ('1M','3M','6M','1Y','YTD','ALL'))
    chart=f'''<div class="chart-toolbar"><span>Indexed to 100</span><div class="periods" role="group" aria-label="Chart period">{periods}</div></div><div id="performance-chart" class="chart" role="img" aria-label="NAV, Market Price and {esc(f['benchmark_label'])} history">Interactive chart unavailable. Use the daily CSV below.</div><div class="chart-legend"><span class="nav-series">NAV</span><span class="market-series">Market Price</span><span class="benchmark-series">{esc(f['benchmark_label'])}</span></div><p id="chart-summary" class="metric-note" aria-live="polite"></p>'''
    bars=[]
    for label in ('1M','3M','6M','YTD','1Y'):
        r=f['returns'][label]
        if r:
            value=r['nav_total_return']
            bars.append(f'<div class="return-bar-row"><span>{label}</span><div><i style="width:{min(abs(value)*200,100):.2f}%"></i></div><strong>{pct(value,True)}</strong></div>')
    summary=card('Total Returns by Period','<div class="return-bars">'+''.join(bars)+'</div><p class="metric-note">Illustrative NAV total returns. Hypothetical demo results, not an actual track record.</p>')
    returns=card('Average Annual Total Returns',table_returns(f,('1Y','5Y','10Y','Since demo start')))
    risk=card('Risk/Return Summary','<p>Equity prices can fall, and active decisions may underperform. Concentration can magnify company and sector risks. Global holdings add currency, market and political risks.</p><p class="metric-note">Returns reinvest demo distributions on their ex-dates. NAV values reflect hypothetical fund expenses; investor brokerage costs and taxes are excluded. Periods over one year are annualized where labeled. These are not approved standardized advertising results. The benchmark is synthetic.</p>')
    distrows=''.join(f'<tr><td>{d["ex_date"]}</td><td>{d["record_date"]}</td><td>{d["payable_date"]}</td><td>{money(d["income"],4)}</td><td>{money(d["short_term_gain"]+d["long_term_gain"],4)}</td><td>{money(d["return_of_capital"],4)}</td><td>{money(d["total"],4)}</td></tr>' for d in f['distributions'])
    distributions=card('Distributions',f'<p class="metric-note">Illustrative amounts per share; no invented entitlement cutoff.</p><div class="table-scroll"><table><thead><tr><th>Ex-date</th><th>Record</th><th>Payable</th><th>Income</th><th>Capital gains</th><th>Return of capital</th><th>Total</th></tr></thead><tbody>{distrows}</tbody></table></div><a class="data-download" href="/etfs/{fid}/data/distributions.csv" download>Download distributions CSV ↓</a>')
    group=''.join(f'<tr><th>{p["period"]}</th><td>{p["premium_days"]}</td><td>{p["discount_days"]}</td><td>{p["at_nav_days"]}</td></tr>' for p in f['disclosure_periods'])
    trading=card('Premium/Discount Information',f'<p>Closing premium / discount: <strong>{pct(f["daily"][-1]["premium_discount"],True)}</strong></p><div id="premium-chart" class="chart" role="img" aria-label="Daily demo premium and discount history">Daily observations are available in the CSV.</div><div class="table-scroll"><table><thead><tr><th>Completed period</th><th>Premium days</th><th>Discount days</th><th>At NAV</th></tr></thead><tbody>{group}</tbody></table></div><p class="metric-note">Fictional weekday observations, not a verified exchange calendar.</p><details><summary>Premium / discount exception disclosures</summary><p class="metric-note">Days with a closing deviation greater than 2% in the displayed history: {exception_days}.</p></details>')
    spread=card('Trading Information','<dl class="data-pairs"><dt>30-day median bid–ask spread</dt><dd>Unavailable</dd><dt>Primary exchange</dt><dd>Proposed / unverified</dd><dt>Trading volume</dt><dd>Unavailable</dd></dl><p class="metric-note">Daily closing prices cannot supply this measure. The spread requires reviewed intraday NBBO observations.</p>')
    return f'<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 restored-data"><h2 class="text-2xl font-bold text-gray-900 mb-6">Performance</h2><p class="metric-note">Illustrative data as of {f["as_of"]}. Not actual fund performance.</p>{card("Performance Comparison",chart)}<div class="grid lg:grid-cols-2 gap-6">{summary}{returns}</div>{risk}<div id="distributions">{distributions}</div><div id="trading" class="grid lg:grid-cols-2 gap-6">{trading}{spread}</div>{card("Cumulative Returns",table_returns(f,("1M","3M","6M","YTD")))}<a class="data-download" href="/etfs/{fid}/data/daily.csv" download>Download daily observations ↓</a></div>'


def bind_fund(page,f,full=False):
    fid=f['fund_id'];last=f['daily'][-1];previous=f['daily'][-2] if len(f['daily'])>1 else last
    equities=[h for h in f['holdings'] if h['security_type']=='equity']
    original_fee={'redi':'0.333%','dam1':'0.29%','azoc':'0.39%','mpd':'0.45%','meri':'0.55%'}[fid]
    for node in list(page.find_all(string=True)):
        if node.parent.name in ('style','script'):continue
        value=str(node).replace(original_fee,pct(f['expense_ratio']))
        value=re.sub(r'\b\d+(?:\.\d+)? basis points\b',f'{f["expense_ratio"]*10000:g} basis points',value)
        if value!=str(node):node.replace_with(value)
    page.body['style']=f'--fund-accent:{THEMES[fid]};--accent:{THEMES[fid]}'
    names={'quick-nav':money(last['nav']),'fund-nav':money(last['nav']),'nav-price':money(last['nav']),
           'quick-price':money(last['market_price']),'etf-price':money(last['market_price']),
           'fund-holdings':len(equities),'nav-change':pct(last['nav']/previous['nav']-1,True),
           'etf-change':pct(last['market_price']/previous['market_price']-1,True)}
    ytd=f['returns']['YTD'];names.update({'hero-ytd-return':pct(ytd['nav_total_return'],True) if ytd else 'Unavailable','quick-ytd':pct(ytd['nav_total_return'],True) if ytd else 'Unavailable'})
    for key,value in names.items():text_at(page,'#'+key,value)
    for key in ('nav-change','etf-change','hero-ytd-return','quick-ytd'):
        node=page.find(id=key)
        if node:
            node['class']=[c for c in node.get('class',[]) if not c.startswith(('text-green-','text-red-'))]
            negative=str(names[key]).startswith('-')
            color=('#fca5a5' if negative else '#86efac') if key=='quick-ytd' else ('#b91c1c' if negative else '#15803d')
            node['style']='color:'+color
    for key in ('fund-details-date','performance-date','holdings-date','holdings-disclosure-date','footer-date'):
        text_at(page,'#'+key,f.get('holdings_as_of',f['as_of']) if key.startswith('holdings') else f['as_of'])
    # Bind the original label/value cards and details grid, including fields without IDs.
    values={'Expense Ratio':pct(f['expense_ratio']),'Total Expense Ratio:':pct(f['expense_ratio']),
            'Holdings':str(len(equities)),'Fund Inception:':f['inception_date']+' (demo start)',
            'Primary Exchange:':'Proposed / unverified','Benchmark:':f['benchmark_label']}
    for el in list(page.find_all(['div','span','td'])):
        label=el.get_text(' ',strip=True)
        if label not in values or el.find(True):continue
        siblings=[x for x in el.parent.find_all(recursive=False) if x!=el and x.name not in ('i','svg')]
        if len(siblings)==1:
            siblings[0].clear();siblings[0].append(values[label])
    hero=next((section for section in page.find_all('section') if section.find(['h1','h2']) and 'ETF' in section.find(['h1','h2']).get_text()),None)
    if hero:
        title=hero.find(['h1','h2']);title.name='h1';title.string=f['name']
        hero.append(fragment(f'<p class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-sm text-gray-500 pb-4">Illustrative data as of {f["as_of"]}; fees and portfolio values are demo inputs. The demo start date is not an actual fund inception date.</p>').p)
    disclosure=heading(page,'IMPORTANT REGULATORY DISCLOSURES')
    if disclosure:
        section=disclosure.find_parent('section')
        contents(section,'<div class="max-w-7xl mx-auto px-4 text-sm"><strong>About this demonstration</strong><p>Not FDIC insured; no bank guarantee; may lose value.</p></div>')
    details=heading(page,'Fund Details')
    if details:details.find_parent('section')['id']='overview'
    info=heading(page,'Company Information')
    if info:
        parent=info.parent
        contents(parent,f'<h3 class="text-lg font-semibold text-gray-900 mb-4">Company Information</h3><p class="text-sm text-gray-600">{BRAND}</p><p class="text-sm text-gray-500 mt-4">Legal entity, registration and contact records remain to be supplied for this demo.</p><a href="/#contact" class="text-red-800 underline text-sm">Contact information</a>')
    perf=page.find(id='performance')
    if perf:contents(perf,fund_performance(f))
    # Keep a single history beside the trading disclosures, with no empty
    # overview chart shell or duplicate current-premium metric left behind.
    premium_panel=page.select_one('#overview .rounded-xl:has(#premiumChart)')
    if premium_panel:premium_panel.decompose()
    holding=page.find(id='holdings')
    if full:
        # Preserve original full-holdings header, navigation and page container.
        main=page.find('main') or next((section for section in page.find_all('section') if section.find('table')),None)
        holding=main or page.new_tag('main',attrs={'class':'py-12','id':'main'})
        if not main:page.body.insert(-1,holding)
        for section in list(page.find_all('section')):
            if section is not holding and section.find(['input','select']):section.decompose()
        sector_values={}
        for h in f['holdings']:sector_values[h['sector']]=sector_values.get(h['sector'],0)+h['weight']
        for element in page.find_all(['div','span']):
            label=element.get_text(' ',strip=True)
            if element.find(True):continue
            value=(str(len(equities)) if label=='Total Holdings' else money(last['net_assets'],0) if label=='Market Value' else pct(sector_values[label]) if label in sector_values else None)
            siblings=[x for x in element.parent.find_all(recursive=False) if x is not element]
            if value is not None and len(siblings)==1 and not siblings[0].find(['input','select']):
                siblings[0].string=value
        sector_heading=heading(page,'Sector Allocation')
        if sector_heading:
            section=sector_heading.find_parent('section')
            if section:
                bars=''.join(f'<div class="return-bar-row"><span>{esc(k)}</span><div><i style="width:{v*100:.2f}%"></i></div><strong>{pct(v)}</strong></div>' for k,v in sorted(sector_values.items(),key=lambda p:-p[1]))
                contents(section,f'<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 restored-data"><h2 class="text-2xl font-bold mb-6">Sector Allocation</h2><div class="cambria-card p-6 sector-bars">{bars}</div></div>')
    if holding:
        if full:
            sectors=sorted({h['sector'] for h in f['holdings']})
            controls=f'<div class="filters"><label>Find a holding<input id="holding-search" type="search" placeholder="Ticker or security name"></label><label>Sector<select id="sector-filter"><option value="">All sectors</option>'+''.join(f'<option>{esc(x)}</option>' for x in sectors)+'</select></label><p id="holding-count" aria-live="polite"></p></div>'
        else:controls=''
        holdings_date=f.get('holdings_as_of',f['as_of'])
        contents(holding,f'<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 restored-data"><div class="flex flex-wrap justify-between items-center gap-4 mb-6"><h2 class="text-2xl font-bold text-gray-900">{"Full Portfolio Holdings" if full else "TOP 10 HOLDINGS"}</h2><a class="cambria-button-secondary" href="/etfs/{fid}/{"data/holdings.csv" if full else "holdings.html"}">{"Download holdings CSV ↓" if full else "View All Holdings →"}</a></div><p class="metric-note">{len(equities)} equity positions plus {pct(f["cash_weight"])} cash · Holdings as of {holdings_date}.</p>{controls}{holdings_table(f["holdings"] if full else equities[:10],full=full,table_id="holdings-table" if full else "top-holdings")}<p id="holdings-empty" hidden>No holdings match these filters.</p><p class="metric-note">Market value = quantity × local price × USD exchange rate. Weights include cash and are based on total net assets.</p></div>')
    documents=page.find(id='documents')
    if documents:
        contents(documents, library_body(f, compact=True))
    for link in page.select('a[href*="document-placeholder"]'):
        link['href']=quick_document_url(link['href'],fid)
        link.attrs.pop('title',None)
    quick = page.select_one('a[href="#performance"]')
    if quick and not quick.parent.select_one('a[href="#trading"]'):
        quick.insert_after(fragment('<a href="#trading" class="text-sm text-red-800 hover:underline font-medium">Premium / Discount</a>').a)
    for banner in page.body.find_all('div',recursive=False):
        if 'registered investment company' in banner.get_text().lower():
            banner.string='Investing involves risk, including possible loss of principal. Not FDIC insured. No bank guarantee.'
    payload=page.new_tag('script',id='page-data',type='application/json')
    payload.string=json.dumps(f,allow_nan=False).replace('<','\\u003c');page.body.append(payload)


def restore_home(page,snapshot,lineup):
    redi=next(f for f in snapshot['funds'] if f['fund_id']=='redi')
    first=page.find('h1')
    first.insert_after(fragment('<p class="text-xl md:text-2xl text-red-800 font-semibold mb-5"><a href="/etfs/redi/">Hetzerk Innovation Factor ETF <span class="text-base">(REDI) →</span></a></p>').p)
    # Restore the actual original interactive selector on the home journey too.
    grid=lineup.select_one('.etf-card').parent
    section=fragment('<section id="etfs" class="py-16 bg-gray-50"><div class="max-w-7xl mx-auto px-4"><h2 class="text-4xl text-center font-bold elegant-heading mb-4">Explore Our ETFs</h2><p class="text-center text-gray-600 mb-10">Distinct strategies. A research-grounded approach.</p></div></section>').section
    section.div.append(deepcopy(grid))
    first.find_parent('section').insert_after(section)
    for style in lineup.find_all('style'):page.head.append(deepcopy(style))
    contact=page.find(id='contact')
    if contact:
        for p in contact.find_all('p'):
            t=p.get_text(' ',strip=True).lower()
            if 'registered investment' in t or 'regulatory disclosure' in t:p.string='Explore Section 351 contribution opportunities or contact us using the interest forms below.'
            elif 'form crs' in t:contents(p,'<strong>Form CRS status:</strong> No current filed relationship summary has been supplied. <a href="/form-crs.html" class="underline">Review applicability and document status</a>.')
        for node in list(contact.find_all(string=True)):
            if '123 Main Street' in str(node):node.replace_with('Contact location to be confirmed')
            elif 'New York, NY 10001' in str(node):node.replace_with('')
        contact.append(fragment('<div class="max-w-7xl mx-auto px-4 mt-6"><a class="cambria-button" href="/section-351.html#register">Section 351 interest →</a> <a class="cambria-button-secondary" href="/351-exchanges.html#register">Explore launch opportunities →</a></div>').div)
    for a in page.select('a[href="/form-crs.html"]'):
        if 'View' in a.get_text():a.string='View Form CRS status'
    from publishing.home_design import apply_home_focus
    apply_home_focus(page,redi)


def restore_pages(snapshot,fallback):
    pages=dict(fallback)
    loaded={}
    for path in sorted((ROOT/'templates').rglob('*.html')):
        route=path.relative_to(ROOT/'templates').as_posix()
        if route in ('test-data.html','standalone.html','index_redirect.html','redirect.html'):continue
        page=prepare(path.read_text(),route)
        if page:loaded[route]=page
    funds={f['fund_id']:f for f in snapshot['funds']}
    lineup=loaded['etfs/index.html']
    configure_interest_form(lineup)
    qualify_tax_copy(lineup)
    for card_tag in lineup.select('a.etf-card'):
        fid=card_tag['href'].rstrip('/').split('/')[-1]
        if fid in funds:
            card_tag['href']=f'/etfs/{fid}/'
            card_tag.find('h2').string=funds[fid]['name']
    for route,page in loaded.items():
        match=re.fullmatch(r'etfs/(redi|dam1|azoc|mpd|meri)/(index|holdings)\.html',route)
        if match:bind_fund(page,funds[match[1]],full=match[2]=='holdings')
        elif route in ('section-351.html','351-exchanges.html'):restore_tax(page,route)
        elif route=='index.html':restore_home(page,snapshot,lineup)
        elif route=='form-crs.html':continue
        elif route.startswith('red/') or route in ('holdings.html','why-red.html'):
            # Historical REDI aliases receive the same current content below.
            continue
        pages[route]=str(page)
    # Preserve each original investment case and research article at its old URL.
    for fid in funds:
        pages[f'research/{fid}/index.html']=pages[f'etfs/{fid}/blog/index.html']
    pages['red/index.html']=pages['etfs/redi/index.html']
    pages['holdings.html']=pages['etfs/redi/holdings.html']
    pages['why-red.html']=pages['etfs/redi/why-red.html']
    pages['red/why-red.html']=pages['etfs/redi/why-red.html']
    for route in list(pages):
        if route.startswith('red/blog/'):
            source=route.replace('red/blog/','etfs/redi/blog/',1)
            if source in pages:pages[route]=pages[source]
    # Review/disclosure pages share the restored header, fonts and brand as well.
    for route in set(pages)-set(loaded):
        if route.startswith(('red/','research/')):continue
        simple=soup(pages[route]);main=simple.find('main')
        if not main:continue
        main['class']=['restored-data','max-w-5xl','mx-auto','px-4','py-12']
        for section in main.select('.section'):section['class']=['review-article']
        for node in list(main.find_all(string=True)):
            if node.parent.name in ('p','h1','h2') and 'Hetzerk is the working brand' in str(node):node.replace_with(str(node).replace('Hetzerk is the working brand',BRAND+' is the working brand'))
        raw=f'<!doctype html><html lang="en"><head><title>{simple.title.get_text()}</title></head><body>{loaded["index.html"].find("header")}{main}{footer()}</body></html>'
        current=prepare(raw,route)
        pages[route]=str(current)
    # Existing CRS status is intentionally factual, while its rich shell is restored.
    if 'form-crs.html' in fallback:
        status=soup(fallback['form-crs.html']).find('main')
        status['class']=['restored-data','max-w-5xl','mx-auto','px-4','py-12']
        pages['form-crs.html']=str(prepare(f'<html><head><title>Form CRS status</title></head><body>{loaded["index.html"].find("header")}{status}{footer()}</body></html>','form-crs.html'))
    redi=funds['redi']
    for route,title,body in (
        ('documents/index.html','Documents & Filings',library_body(redi)),
        ('etfs/redi/fact-sheet.html','Innovation Factor ETF — Fact Sheet',fact_sheet_body(redi)),
    ):
        raw=f'<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title></head><body>{loaded["index.html"].find("header")}<main class="py-12">{body}</main>{footer()}</body></html>'
        pages[route]=str(prepare(raw,route))
    pages['etfs/redi/document-placeholder.html']=pages['documents/index.html']
    return pages
