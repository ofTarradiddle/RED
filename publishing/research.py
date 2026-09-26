"""Research library and report, using the same shell as the main Hetzerk site."""
from copy import deepcopy
from html import escape
from math import ceil

from bs4 import BeautifulSoup

from publishing.research_report_content import (
    REPORT_TITLE, REPORT_SUBTITLE, REPORT_DESCRIPTION, report_body,
)

REPORT_ROUTE = 'research/the-measure-of-fire.html'
PDF_URL = '/assets/research/the-measure-of-fire.pdf'
SECTIONS = (
    ('r-summary', 'Executive summary'), ('r-rationale', 'Economic rationale'),
    ('r-process', 'Investment process'), ('r-evidence', 'Research evidence'),
    ('r-why-now', 'Why now'), ('r-durability', 'Durable characteristics'),
    ('r-validation', 'Research limitations'), ('r-sources', 'Source notes'),
)


def _shell(home_html, disclaimer_html, title, description, *, report=False):
    page = BeautifulSoup(home_html, 'html.parser')
    page.body['class'].extend(['research-page'] + (['report-page'] if report else []))
    page.title.string = title
    for meta in page.head.select('meta[property="og:title"],meta[name="twitter:title"]'):
        meta['content'] = title
    for meta in page.head.select('meta[name="description"],meta[property="og:description"],meta[name="twitter:description"]'):
        meta['content'] = description
    for anchor in page.select('.home-nav a'):
        if anchor['href'].startswith('#'):
            anchor['href'] = '/' + anchor['href']
        if anchor['href'] == '/research/':
            anchor['aria-current'] = 'page'
    for asset, kind in (('/assets/research.css', 'style'),
                        ('/assets/research-disclaimer.css', 'style'),
                        ('/assets/research-disclaimer.js', 'script')):
        if kind == 'style':
            page.head.append(page.new_tag('link', rel='stylesheet', href=asset))
        else:
            page.head.append(page.new_tag('script', src=asset, defer=''))
    if report:
        page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/research-print.css', media='print'))
        page.head.append(page.new_tag('link', rel='alternate', type='application/pdf', href=PDF_URL, title='Download the research report'))
    dialog = BeautifulSoup(disclaimer_html, 'html.parser').find(id='disclaimerOverlay')
    if dialog:
        page.body.append(deepcopy(dialog))
    page.find('main').clear()
    return page


def _append(page, html):
    for node in list(BeautifulSoup(html, 'html.parser').contents):
        page.find('main').append(node)
    return str(page)


def render_research_pages(home_html, existing_research):
    body = report_body()
    minutes = max(1, ceil(len(BeautifulSoup(body, 'html.parser').get_text(' ', strip=True).split()) / 220))
    library = _shell(home_html, existing_research, 'Research | Hetzerk Asset Management',
                     'Research on innovation, valuation and systematic equity investing from Hetzerk Asset Management.')
    library_html = f'''
      <section class="research-hero" aria-labelledby="research-title">
        <p class="home-eyebrow">Hetzerk / Research</p>
        <h1 id="research-title">The thinking<br><span>behind REDI.</span></h1>
        <p>Innovation, examined through the business, its valuation and the evidence.</p>
      </section>
      <section class="research-feature" aria-labelledby="featured-title">
        <div class="research-feature-copy">
          <div class="research-meta"><span>Research report</span><span>{minutes} min read</span></div>
          <h2 id="featured-title"><a href="/{REPORT_ROUTE}">{escape(REPORT_TITLE)}</a></h2>
          <p class="research-subtitle">{escape(REPORT_SUBTITLE)}</p>
          <p>How innovation value and commercial ability inform systematic equity selection. An examination of the economic case, the original research figures and the assumptions behind the results.</p>
          <div class="research-actions"><a class="home-text-link" href="/{REPORT_ROUTE}">Read the report <span aria-hidden="true">→</span></a><a class="research-download" href="{PDF_URL}" download>Download PDF <span aria-hidden="true">↓</span></a></div>
        </div>
        <figure class="research-cover"><a href="/{REPORT_ROUTE}" aria-label="Read The Measure of Fire"><img src="/assets/investment-case/long-term-characteristics.png" width="2048" height="1113" alt="Shin Chan conducting possible return paths in the presentation’s conceptual illustration of systematic investing." decoding="async"></a><figcaption>Conceptual strategy illustration; not actual or projected returns.</figcaption></figure>
      </section>
      <section class="research-topics" aria-labelledby="topics-title">
        <div><p class="home-eyebrow">Inside the research</p><h2 id="topics-title">Three questions<br>behind the portfolio.</h2></div>
        <div class="research-topic-list">
          <a href="/{REPORT_ROUTE}#r-rationale"><span>01</span><div><h3>Why innovation?</h3><p>The link between research investment, commercial progress and future cash flows.</p></div><span aria-hidden="true">↗</span></a>
          <a href="/{REPORT_ROUTE}#r-process"><span>02</span><div><h3>What do we measure?</h3><p>Innovation value, innovation ability and the role of equal weighting.</p></div><span aria-hidden="true">↗</span></a>
          <a href="/{REPORT_ROUTE}#r-evidence"><span>03</span><div><h3>What does the evidence show?</h3><p>Research paths, annual comparisons and the limits of historical results.</p></div><span aria-hidden="true">↗</span></a>
        </div>
      </section>
      <div class="research-related"><div><p class="home-eyebrow">Hetzerk Innovation Factor ETF</p><h2>Explore the investment case.</h2></div><a class="home-text-link" href="/etfs/redi/why-red.html">Explore REDI <span aria-hidden="true">→</span></a></div>
    '''
    toc = ''.join(f'<li><a href="#{key}"><span>{i:02}</span>{label}</a></li>'
                  for i, (key, label) in enumerate(SECTIONS, 1))
    report = _shell(home_html, existing_research, f'{REPORT_TITLE}: {REPORT_SUBTITLE} | Hetzerk Asset Management',
                    REPORT_DESCRIPTION, report=True)
    report_html = f'''
      <header class="report-hero" aria-labelledby="report-title">
        <a class="research-back" href="/research/">← All research</a>
        <p class="home-eyebrow">Research report / Innovation factor</p>
        <h1 id="report-title">{escape(REPORT_TITLE)}</h1>
        <p class="report-subtitle">{escape(REPORT_SUBTITLE)}</p>
        <div class="report-meta"><p class="report-byline">Hetzerk Asset Management <span>{minutes} min read</span></p><a class="research-download" href="{PDF_URL}" download>Download PDF <span aria-hidden="true">↓</span></a></div>
      </header>
      <div class="report-layout">
        <aside class="report-toc"><nav aria-label="Report contents"><p class="home-eyebrow">In this report</p><ol>{toc}</ol></nav><a class="report-fund-link" href="/etfs/redi/">Hetzerk Innovation Factor ETF <span aria-hidden="true">↗</span></a></aside>
        <article class="report-body" aria-label="The Measure of Fire research report">{body}</article>
      </div>
      <div class="research-related report-end"><div><p class="home-eyebrow">Continue exploring</p><h2>The Hetzerk Innovation Factor ETF.</h2></div><a class="home-text-link" href="/etfs/redi/why-red.html">The investment case <span aria-hidden="true">→</span></a></div>
    '''
    return {'research/index.html': _append(library, library_html), REPORT_ROUTE: _append(report, report_html)}
