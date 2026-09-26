"""A consistent public site shell, preserving each investor journey."""
from copy import deepcopy

from bs4 import BeautifulSoup
from publishing.investment_case import attach_assets, etf_research_card
from publishing.objective_journey import objective_journey
from publishing.masthead import refine_masthead


FUND_ROUTES = {'etfs/redi/index.html', 'red/index.html'}
EXCHANGE_ROUTES = {'section-351.html', '351-exchanges.html'}


def _fund_copy(page):
    intro = page.select_one('#main .max-w-4xl > p')
    if intro:
        intro.string = ('REDI seeks long-term capital appreciation through U.S. mid- and large-cap equities. '
                        'The strategy combines innovation value—what investors pay for innovation—with '
                        'innovation ability, a company’s capacity to turn research into commercial results. '
                        'Selected companies are equally weighted.')
    for paragraph in page.select('#main p'):
        text = paragraph.get_text(strip=True)
        if text.startswith('As of ') and text.endswith(';'):
            paragraph.string = text.rstrip(';')
    for label in page.find_all(string=lambda text: text and text.strip() == 'Price'):
        if label.parent.name not in ('style', 'script'):
            label.replace_with('Market Price')
    for link in page.select('section a[href="#performance"]'):
        if link.get_text(strip=True) == 'Performance':
            premium = page.new_tag('a', href='#trading', attrs={'class': link.get('class', [])})
            premium.string = 'Premium / Discount'
            link.insert_after(premium)
    for heading in page.find_all(['h3', 'h4']):
        label = heading.get_text(strip=True)
        if label == 'Investment Objective':
            paragraphs = heading.parent.find_all('p', recursive=False)
            text = (
                'The Hetzerk Innovation Factor ETF seeks long-term capital appreciation through companies with attractive innovation characteristics in the U.S. mid- and large-cap equity universe.',
                'The selection process considers innovation investment, valuation and evidence of commercial ability. Selected companies are equally weighted.',
            )
            for paragraph, copy in zip(paragraphs, text):
                paragraph.string = copy
        elif label == 'Our Mission':
            heading.string = 'Our approach'
            paragraphs = heading.parent.find_all('p', recursive=False)
            text = (
                'Hetzerk Asset Management develops systematic equity strategies informed by fundamental research. Our focus is the Hetzerk Innovation Factor ETF: a disciplined approach to identifying innovation at a justifiable valuation.',
                'We examine both what investors pay for innovation and a company’s ability to turn research into commercial progress. Consistent selection rules bring those observations into the portfolio.',
            )
            for paragraph, copy in zip(paragraphs, text):
                paragraph.string = copy
        elif label == 'Investment Philosophy':
            paragraph = heading.find_next_sibling('p')
            if paragraph:
                paragraph.string = 'Economic reasoning, measurable company characteristics and a repeatable investment process.'
        elif label == 'Key Insight':
            heading.string = 'The investment lens'
            paragraph = heading.find_next_sibling('p')
            if paragraph:
                paragraph.string = 'Innovation spending is a starting point. Valuation and evidence of commercial execution help distinguish an investment opportunity from a compelling story.'


def refine_pages(pages):
    home = BeautifulSoup(pages['index.html'], 'html.parser')
    header, footer = home.select_one('.home-header'), home.select_one('.home-footer')
    result = {}
    for route, html in pages.items():
        page = BeautifulSoup(html, 'html.parser')
        classes = page.body.get('class', [])
        modern = 'home-minimal' in classes
        page.body['class'] = classes + ['hetzerk-site']
        if not page.select_one('link[href="/assets/minimal-home.css"]'):
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/minimal-home.css'))
        if not modern:
            old_header = page.select_one('.sticky-banner-wrapper') or page.find('header')
            if old_header:
                # The archived presentation has its own slide navigation.
                # Retain it as a compact contents disclosure within the article.
                contents = old_header.select_one('nav.toc')
                if contents and page.find('main'):
                    drawer = page.new_tag('details', attrs={'class': 'archive-contents'})
                    summary = page.new_tag('summary')
                    summary.string = 'Presentation contents'
                    drawer.append(summary)
                    drawer.append(contents.extract())
                    page.find('main').insert(0, drawer)
                old_header.replace_with(deepcopy(header))
            else:
                page.select_one('.demo-strip').insert_after(deepcopy(header))
            old_footer = page.find('footer')
            if old_footer:
                old_footer.replace_with(deepcopy(footer))
        nav = page.select_one('.home-nav')
        for link in nav.select('a[aria-current]'):
            del link['aria-current']
        current = None
        if route in FUND_ROUTES or route.startswith('etfs/redi/holdings'):
            current = '/etfs/redi/'
        elif 'case-page' in classes:
            current = '/etfs/redi/why-red.html'
        elif 'research-page' in classes or route.startswith('research/') or '/blog/' in route:
            current = '/research/'
        elif route in EXCHANGE_ROUTES:
            current = '/#contact'
        if current:
            nav.find('a', href=current)['aria-current'] = 'page'
        page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/institutional.css'))
        if route in FUND_ROUTES:
            page.body['class'].append('institutional-etf')
            _fund_copy(page)
            objective = BeautifulSoup(objective_journey('etf'), 'html.parser').section
            page.select_one('#overview').insert_after(objective)
            objective.insert_after(BeautifulSoup(etf_research_card(), 'html.parser').section)
            if not page.select_one('link[href="/assets/investment-case.css"]'):
                attach_assets(page)
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/institutional-etf.css'))
        elif route in EXCHANGE_ROUTES:
            page.body['class'].append('institutional-351')
            for link in page.select('.exchange-hero-copy a'):
                if 'other Section 351' in link.get_text():
                    link.string = ('Explore contribution opportunities →' if route == 'section-351.html'
                                   else 'Read the Section 351 overview →')
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/institutional-351.css'))
        elif not modern:
            page.body['class'].append('institutional-reference')
            article = page.body.find('article', recursive=False)
            if article:
                article.name = 'main'
                page.body['class'].append('institutional-archive')
            if page.select_one('main .slide'):
                page.body['class'].append('institutional-archive')
                floating_nav = page.find(id='floatingNav')
                if floating_nav:
                    page.find('main').insert(0, floating_nav.extract())
            if route in ('documents/index.html', 'etfs/redi/document-placeholder.html'):
                heading = page.find('h1')
                eyebrow = page.new_tag('p', attrs={'class': 'institutional-eyebrow'})
                eyebrow.string = 'Hetzerk Innovation Factor ETF / REDI'
                heading.insert_before(eyebrow)
                heading.string = 'Documents & filings'
        if page.select_one('[data-innovation-journey]'):
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/innovation-journey.css'))
            page.head.append(page.new_tag('script', src='/assets/innovation-journey.js', defer=''))
        if route == 'index.html':
            page.body['class'].append('fund-home')
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/fund-home.css'))
        if page.select_one('[data-objective-journey]'):
            page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/objective-journey.css'))
            page.head.append(page.new_tag('script', src='/assets/objective-journey.js', defer=''))
        refine_masthead(page)
        page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/atmosphere.css'))
        if route in FUND_ROUTES | EXCHANGE_ROUTES or not page.find('main'):
            # Legacy pages split content across sibling sections. Give every
            # investor journey a complete main landmark without changing its IDs.
            content = page.new_tag('main', attrs={'class': 'site-content'})
            first = page.body.find(['main', 'section'], recursive=False)
            if first is None:
                first = page.select_one('.home-header').find_next_sibling()
            if first:
                misplaced_target = page.select_one('.demo-strip#main')
                if misplaced_target:
                    del misplaced_target['id']
                    content['id'] = 'main'
                first.insert_before(content)
                for node in list(content.next_siblings):
                    if getattr(node, 'name', None) == 'footer':
                        break
                    if getattr(node, 'name', None) == 'main':
                        node.name = 'section'
                    content.append(node.extract())
        result[route] = str(page)
    return result
