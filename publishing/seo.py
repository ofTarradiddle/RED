"""Route metadata and canonical URLs for local previews and public builds."""
from __future__ import annotations

import json
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

BRAND = 'Hetzerk Asset Management'
SOCIAL_IMAGE = '/assets/hetzerk-social.png'
# Legacy research drafts, utility pages and aliases remain reachable but are
# excluded from the sitemap of current search landing pages.
METADATA = {
    'index.html': ('Hetzerk Asset Management | Investing in Innovation, REDI for tomorrow',
                   'Explore the Hetzerk Innovation Factor ETF (REDI), its investment case, fund expenses and Section 351 contribution opportunities.'),
    'etfs/index.html': ('Our ETF — REDI | Hetzerk Asset Management',
                       'Explore REDI, the Hetzerk Innovation Factor ETF, and learn about its investment approach, expenses and potential Section 351 contributions.'),
    'etfs/redi/index.html': ('REDI — Hetzerk Innovation Factor ETF',
                            'Explore the Hetzerk Innovation Factor ETF (REDI): its strategy, annual expense ratio, holdings, NAV, market price and fund documents.'),
    'etfs/redi/why-red.html': ('REDI Investment Case | Hetzerk Asset Management',
                              'Explore the REDI investment case: innovation value, innovation ability, endogenous growth and systematic equity portfolio construction.'),
    'etfs/redi/holdings.html': ('REDI Portfolio Holdings | Hetzerk Asset Management',
                               'View and download the REDI portfolio holdings, including security names, sectors, portfolio weights and shares held.'),
    'etfs/redi/fact-sheet.html': ('REDI ETF Fact Sheet | Hetzerk Asset Management',
                                 'Review the REDI fact sheet for the Hetzerk Innovation Factor ETF, including its investment approach, expenses, portfolio data and risks.'),
    'section-351.html': ('Section 351 Exchanges | Hetzerk Asset Management',
                         'Learn about Section 351 portfolio contributions to an ETF, potential tax deferral, eligibility requirements and how to register interest.'),
    '351-exchanges.html': ('Section 351 ETF Opportunities | Hetzerk Asset Management',
                           'Explore potential Section 351 contribution opportunities for REDI, review transaction considerations and register your interest.'),
    'documents/index.html': ('REDI Documents & Filings | Hetzerk Asset Management',
                             'Find REDI fund documents, the fact sheet, holdings downloads and filing references, with the status of each document clearly identified.'),
    'about/index.html': ('Our Investment Approach | Hetzerk Asset Management',
                         'Learn about the Hetzerk Asset Management approach to systematic equity investing and the Hetzerk Innovation Factor ETF.'),
    'research/index.html': ('Research | Hetzerk Asset Management',
                            'Explore Hetzerk Asset Management research on innovation, company characteristics and systematic equity portfolio construction.'),
    'research/the-measure-of-fire.html': ('The Measure of Fire: Innovation as an Equity Factor | Hetzerk Asset Management',
                                         'Read the Hetzerk research report on innovation value, innovation ability, long-term company characteristics and the REDI portfolio framework.'),
    'research/on-innovation-factor-investing.html': ('Conviction, Measured: On Innovation Factor Investing | Hetzerk Asset Management',
                                                   'A Hetzerk research perspective on commercially successful innovation, focused factor selection and the evidence an investment signal must earn.'),
    'disclosures/index.html': ('Investment Disclosures | Hetzerk Asset Management',
                               'Review investment risks, offering status, fund data qualifications and document information for the Hetzerk Innovation Factor ETF.'),
    'privacy/index.html': ('Privacy | Hetzerk Asset Management',
                           'Learn how this website handles contact requests, browser interactions and information you choose to provide.'),
}
UTILITY_METADATA = {
    '404.html': ('Page Not Found | Hetzerk Asset Management', 'The requested page could not be found. Return to Hetzerk Asset Management or explore REDI.'),
    'review/index.html': ('Fund Data Guide | Hetzerk Asset Management', 'Review the source workbook, data fields and publishing methodology used by this website.'),
    'form-crs.html': ('Form CRS Status | Hetzerk Asset Management', 'Review the availability and status of the relationship summary for Hetzerk Asset Management.'),
}
ALIASES = {
    'red/index.html': 'etfs/redi/index.html',
    'holdings.html': 'etfs/redi/holdings.html',
    'why-red.html': 'etfs/redi/why-red.html',
    'red/why-red.html': 'etfs/redi/why-red.html',
    'etfs/redi/document-placeholder.html': 'documents/index.html',
    'etfs/redi/blog/index.html': 'research/index.html',
    'red/blog/index.html': 'research/index.html',
    'research/redi/index.html': 'research/index.html',
}
MOVED = {'redirect.html', 'standalone.html', 'index_redirect.html', 'test-data.html'}


def validate_site_url(site_url, base_path='', indexable=False):
    """Require a public HTTPS root and an exact match to asset path routing."""
    if base_path and not re.fullmatch(r'/[A-Za-z0-9_-]+', base_path):
        raise ValueError('Expected a single GitHub Pages repository path, e.g. /RED')
    if not site_url:
        if indexable:
            raise ValueError('--indexable requires --site-url for the configured public site')
        return None
    url = urlsplit(site_url)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.port or url.query or url.fragment or re.search(r'\s', site_url)
            or url.hostname in ('localhost', '127.0.0.1', '::1')
            or not re.fullmatch(r'[A-Za-z0-9.-]+', url.hostname)):
        raise ValueError('site_url must be an HTTPS public site URL without credentials, port, query or fragment')
    path = url.path.removesuffix('/')
    if path != base_path:
        raise ValueError('site_url path must match base_path exactly')
    return f'https://{url.hostname}{path}'


def canonical_route(route):
    if route in ALIASES:
        return ALIASES[route]
    if route.startswith('red/blog/'):
        return route.replace('red/blog/', 'etfs/redi/blog/', 1)
    if re.fullmatch(r'research/sample-post-[1-4]\.html', route):
        return route.replace('research/', 'etfs/redi/blog/', 1)
    return route


def route_url(site_url, route):
    path = route.removesuffix('index.html') if route == 'index.html' or route.endswith('/index.html') else route
    return site_url + '/' + path


def _meta(page, key, value, property=False):
    page.head.append(page.new_tag('meta', attrs={('property' if property else 'name'): key, 'content': value}))


def apply_seo(pages, *, site_url=None, base_path='', indexable=False):
    """Normalize final HTML before the build prefixes local assets."""
    site_url = validate_site_url(site_url, base_path, indexable)
    result = {}
    for route, html in pages.items():
        page = BeautifulSoup(html, 'html.parser')
        page.html['lang'] = 'en'
        previous = page.select_one('meta[name="description"]')
        default_description = ' '.join(previous.get('content', '').split()) if previous else f'Explore {BRAND} and REDI.'
        for tag in page.head.select('meta[charset],meta[name="viewport"],meta[name="description"],meta[name="robots"],meta[name^="twitter:"],meta[property^="og:"],link[rel="canonical"],script[type="application/ld+json"]'):
            tag.decompose()
        page.head.insert(0, page.new_tag('meta', charset='utf-8'))
        _meta(page, 'viewport', 'width=device-width, initial-scale=1')
        target = canonical_route(route)
        default_title = page.title.get_text(' ', strip=True) if page.title else BRAND
        title, description = METADATA.get(target, UTILITY_METADATA.get(route, (default_title, default_description)))
        if target not in METADATA and target.startswith(('research/', 'etfs/redi/blog/')):
            description = 'Research perspectives on innovation, company characteristics and systematic equity investing from Hetzerk Asset Management.'
        if route in MOVED:
            title, description = 'Page Moved | ' + BRAND, 'Follow the link to the current page on the Hetzerk Asset Management website.'
        titles = page.head.find_all('title')
        for duplicate in titles[1:]:
            duplicate.decompose()
        if not titles:
            page.head.append(page.new_tag('title'))
        page.title.string = title
        _meta(page, 'description', description)
        eligible = target in METADATA and route not in MOVED
        _meta(page, 'robots', 'index,follow,max-image-preview:large' if indexable and eligible else 'noindex,follow')
        is_research_report = target in ('research/the-measure-of-fire.html', 'research/on-innovation-factor-investing.html')
        for key, value in (('og:title', title), ('og:description', description), ('og:type', 'article' if is_research_report else 'website'), ('og:site_name', BRAND), ('og:locale', 'en_US')):
            _meta(page, key, value, property=True)
        for key, value in (('twitter:card', 'summary_large_image'), ('twitter:title', title), ('twitter:description', description)):
            _meta(page, key, value)
        image = (site_url or base_path) + SOCIAL_IMAGE
        _meta(page, 'og:image', image, property=True)
        _meta(page, 'og:image:width', '1200', property=True)
        _meta(page, 'og:image:height', '630', property=True)
        _meta(page, 'og:image:alt', 'Hetzerk Asset Management — Investing in Innovation, REDI for tomorrow', property=True)
        _meta(page, 'twitter:image', image)
        _meta(page, 'twitter:image:alt', 'Hetzerk Asset Management — Investing in Innovation, REDI for tomorrow')
        if site_url and route not in MOVED and route != '404.html':
            url = route_url(site_url, target)
            page.head.append(page.new_tag('link', rel='canonical', href=url))
            _meta(page, 'og:url', url, property=True)
            graph = [{
                '@type': 'WebPage', '@id': url + '#webpage', 'url': url,
                'name': title, 'description': description, 'inLanguage': 'en-US',
                'isPartOf': {'@id': site_url + '/#website'},
                'publisher': {'@id': site_url + '/#organization'},
            }]
            if route == 'index.html':
                graph.extend([
                    {'@type': 'Organization', '@id': site_url + '/#organization', 'name': BRAND, 'url': site_url + '/'},
                    {'@type': 'WebSite', '@id': site_url + '/#website', 'name': BRAND, 'url': site_url + '/', 'publisher': {'@id': site_url + '/#organization'}},
                ])
            if is_research_report:
                graph[0]['mainEntity'] = {'@id': url + '#article'}
                graph.append({
                    '@type': 'Article', '@id': url + '#article', 'url': url,
                    'headline': title.removesuffix(' | ' + BRAND),
                    'description': description,
                    'genre': 'Research report' if target == 'research/the-measure-of-fire.html' else 'Research perspective',
                    'inLanguage': 'en-US',
                    'mainEntityOfPage': {'@id': url + '#webpage'},
                    'author': {'@type': 'Organization', '@id': site_url + '/#organization', 'name': BRAND, 'url': site_url + '/'},
                    'publisher': {'@id': site_url + '/#organization'},
                })
                if target == 'research/the-measure-of-fire.html':
                    graph[-1]['encoding'] = {
                        '@type': 'MediaObject', 'encodingFormat': 'application/pdf',
                        'contentUrl': site_url + '/assets/research/the-measure-of-fire.pdf',
                    }
            script = page.new_tag('script', type='application/ld+json')
            script.string = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('<', '\\u003c')
            page.head.append(script)
        if route == 'etfs/index.html' and not page.find('h1'):
            heading = page.new_tag('h1', attrs={'class': 'sr-only'})
            heading.string = 'Hetzerk Innovation Factor ETF — REDI'
            (page.find('main') or page.body).insert(0, heading)
        for heading in page.find_all('h1')[1:]:
            heading.name = 'h2'
        if route == '404.html':
            heading = page.find('h1')
            if heading:
                heading.string = 'Page not found'
                paragraph = heading.find_next_sibling('p')
                if paragraph:
                    paragraph.clear()
                    paragraph.append('The page you requested is unavailable. ')
                    link = page.new_tag('a', href='/')
                    link.string = 'Return home →'
                    paragraph.append(link)
        for anchor in page.select('a[href]'):
            url = urlsplit(anchor['href'])
            if url.scheme or url.netloc or not url.path.startswith('/'):
                continue
            linked = url.path.lstrip('/')
            linked = linked + 'index.html' if linked.endswith('/') else linked
            canonical = canonical_route(linked)
            if canonical != linked and canonical in pages:
                anchor['href'] = route_url('', canonical) + ('?' + url.query if url.query else '') + ('#' + url.fragment if url.fragment else '')
        result[route] = str(page)
    return result


def sitemap_xml(pages, site_url, *, indexable=False):
    root = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    if indexable and site_url:
        for route in sorted(set(pages).intersection(METADATA)):
            item = ET.SubElement(root, 'url')
            ET.SubElement(item, 'loc').text = route_url(site_url, route)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'


def robots_text(site_url=None, *, indexable=False):
    # Crawlers must be allowed to fetch HTML to observe preview noindex directives.
    value = 'User-agent: *\nAllow: /\n'
    if indexable and site_url:
        value += f'Sitemap: {site_url}/sitemap.xml\n'
    return value
