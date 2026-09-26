"""Keep the corporate site's original identity while focusing its offer on REDI."""
from bs4 import BeautifulSoup
from publishing.site import pct, money


def fill(tag,html):
    tag.clear()
    for node in list(BeautifulSoup(html,'html.parser').contents): tag.append(node)


def apply_home_focus(page,f):
    hero=page.find('h1').find_parent('section')
    highlight=hero.select_one('.fee-highlight')
    fill(highlight,f'<p class="text-sm font-semibold tracking-wide text-red-800 mb-3">ONE FUND. A FOCUSED INVESTMENT APPROACH.</p><h3 class="text-3xl elegant-heading font-bold mb-3">Innovation, through an equity ETF.</h3><p class="text-lg text-gray-600">The Hetzerk Innovation Factor ETF brings our research and portfolio process together in a single exchange-traded fund.</p>')
    for p in hero.find_all('p'):
        if 'Our philosophy centers' in p.get_text():
            p.string='We study innovation as a driver of business growth, combining quantitative signals with fundamental research. Our focus is the Hetzerk Innovation Factor ETF: a systematic approach to U.S. equity investing.'
    for a in hero.select('a[href]'):
        if a.get_text(strip=True)=='Get Started':a['href']='/etfs/redi/';a.string='Explore REDI'
        elif 'View Our ETF' in a.get_text():a['href']='/etfs/redi/why-red.html';a.string='Read the Investment Case'
    fees=page.find(id='fees')
    fill(fees,f'''<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"><div class="text-center mb-12"><p class="text-sm font-semibold text-red-800 mb-3">HETZERK INNOVATION FACTOR ETF</p><h2 class="text-4xl md:text-5xl font-bold elegant-heading mb-4">Fund Expenses</h2><p class="text-lg text-gray-600">A clear view of the cost of owning REDI.</p></div><div class="etf-cost-layout"><div class="etf-cost-number"><span>Annual Expense Ratio</span><strong>{pct(f['expense_ratio'])}</strong><p>{f['expense_ratio']*10000:g} basis points</p></div><div><h3>What the expense ratio covers</h3><p>The expense ratio expresses annual fund operating expenses as a percentage of fund assets. These expenses are reflected in the Fund’s NAV.</p><div class="etf-cost-example"><strong>{money(f['expense_ratio']*10000,0)}</strong><span>Annual fund expenses on a constant $10,000 investment value.</span></div><p class="etf-cost-note">Actual expenses vary with the value of your investment. Brokerage commissions, bid-ask spreads and other transaction costs may also apply.</p><a href="/etfs/redi/#documents" class="text-red-800 font-semibold">Review Fund Documents →</a></div></div></div>''')
    services=page.find(id='services')
    fill(services,'''<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"><div class="text-center mb-12"><h2 class="text-4xl md:text-5xl font-bold elegant-heading mb-4">Inside the Fund</h2><p class="text-lg text-gray-600">Research, portfolio construction and transparent fund information.</p></div><div class="grid md:grid-cols-3 gap-8"><article class="cambria-card p-8"><i data-lucide="microscope" class="w-9 h-9 text-red-800 mb-6"></i><h3 class="text-2xl font-bold mb-4 elegant-heading">Innovation Research</h3><p class="text-gray-600 leading-relaxed mb-5">We examine R&amp;D investment, intellectual property and other company characteristics to understand the sources of future business growth.</p><a href="/etfs/redi/why-red.html" class="text-red-800 font-semibold">Investment Case →</a></article><article class="cambria-card p-8"><i data-lucide="layers" class="w-9 h-9 text-red-800 mb-6"></i><h3 class="text-2xl font-bold mb-4 elegant-heading">Portfolio Construction</h3><p class="text-gray-600 leading-relaxed mb-5">REDI combines innovation signals with valuation, business quality, diversification and liquidity considerations in an equity portfolio.</p><a href="/etfs/redi/holdings.html" class="text-red-800 font-semibold">Explore Holdings →</a></article><article class="cambria-card p-8"><i data-lucide="chart-no-axes-combined" class="w-9 h-9 text-red-800 mb-6"></i><h3 class="text-2xl font-bold mb-4 elegant-heading">Fund Transparency</h3><p class="text-gray-600 leading-relaxed mb-5">Review dated NAV and market-price returns, portfolio holdings, distributions and premium/discount history in one place.</p><a href="/etfs/redi/#performance" class="text-red-800 font-semibold">Fund Performance →</a></article></div></div>''')
    about=page.find(id='about')
    for p in about.find_all('p'):
        text=p.get_text(' ',strip=True)
        if 'help clients achieve' in text:
            p.string='Our firm combines quantitative research with fundamental investment insight. We put that process to work in the Hetzerk Innovation Factor ETF, our equity investment offering.'
        elif 'In addition to our advisory services' in text:
            fill(p,'The Hetzerk Innovation Factor ETF is the expression of our investment approach. <a href="/etfs/redi/" class="text-red-800 font-semibold">Explore REDI →</a>')
    contact=page.find(id='contact')
    fill(contact,'''<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"><div class="text-center mb-12"><h2 class="text-4xl md:text-5xl font-bold elegant-heading mb-4">Connect with Hetzerk</h2><p class="text-lg text-gray-600">Fund information and potential Section 351 contributions.</p></div><div class="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto"><div class="cambria-card p-8"><h3 class="text-2xl font-bold elegant-heading mb-4">Explore REDI</h3><p class="text-gray-600 leading-relaxed mb-6">Find the investment objective, portfolio holdings, performance and fund materials for the Hetzerk Innovation Factor ETF.</p><a class="cambria-button" href="/etfs/redi/">View the Fund</a></div><div class="cambria-card p-8"><h3 class="text-2xl font-bold elegant-heading mb-4">Section 351 Inquiries</h3><p class="text-gray-600 leading-relaxed mb-6">Learn about potential tax-deferred portfolio contributions and register your interest. Eligibility depends on the transaction and your circumstances.</p><a class="cambria-button-secondary" href="/section-351.html#register">Contact the Fund Team</a></div></div></div>''')
    for a in page.select('a[href="/form-crs.html"]'):
        if not a.find(['h2','h3']):continue
        a['href']='/documents/'
        a.find(['h2','h3']).string='Fund Documents'
        paragraphs=a.find_all('p')
        if paragraphs:paragraphs[0].string='Hetzerk Innovation Factor ETF'
        if len(paragraphs)>1:paragraphs[1].string='Explore fund materials, prospectus references, shareholder reports and regulatory filing information.'
    for a in page.select('a[href="/section-351.html"]'):
        if a.find('h2'):
            paragraphs=a.find_all('p')
            if len(paragraphs)>1:paragraphs[1].string='Explore the conditions for contributing an eligible portfolio to an ETF in a potentially tax-deferred transaction.'
