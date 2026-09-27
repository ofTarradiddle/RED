"""Public URL correctness, preview exclusion and safe metadata regression checks."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
import pytest

from publishing.build import build
from publishing.seo import METADATA, apply_seo, canonical_route, validate_site_url

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / 'workbooks/hetzerk-demo.xlsx'
NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


@pytest.fixture(scope='module')
def public(tmp_path_factory):
    output = tmp_path_factory.mktemp('seo') / 'public'
    build(BOOK, output, base_path='/RED', site_url='https://oftarradiddle.github.io/RED/', indexable=True)
    return output


def parsed(path):
    return BeautifulSoup(path.read_text(), 'html.parser')


def test_public_sitemap_matches_canonicals_and_excludes_private_archived_routes(public):
    locations = [node.text for node in ET.parse(public / 'sitemap.xml').findall('sm:url/sm:loc', NS)]
    assert len(locations) == len(set(locations))
    assert 'https://oftarradiddle.github.io/RED/' in locations
    assert 'https://oftarradiddle.github.io/RED/section-351.html' in locations
    assert 'https://oftarradiddle.github.io/RED/351-exchanges.html' in locations
    for url in locations:
        assert url.startswith('https://oftarradiddle.github.io/RED/')
        route = url.removeprefix('https://oftarradiddle.github.io/RED/')
        route = route + 'index.html' if not route or route.endswith('/') else route
        page = parsed(public / route)
        assert page.select_one('link[rel=canonical]')['href'] == url
        assert page.select_one('meta[property="og:url"]')['content'] == url
        assert page.select_one('meta[name=robots]')['content'].startswith('index,')
        assert not any(part in route for part in ('private', 'shadow', 'review', 'sample-post', 'dam1', 'meri', 'mpd', 'azoc'))
    for route in ('review/index.html', '404.html', 'research/sample-post-4.html', 'redirect.html'):
        page = parsed(public / route)
        assert page.select_one('meta[name=robots]')['content'] == 'noindex,follow'
    assert not (public / 'private').exists()
    assert (public / 'robots.txt').read_text() == 'User-agent: *\nAllow: /\nSitemap: https://oftarradiddle.github.io/RED/sitemap.xml\n'


def test_aliases_and_social_urls_follow_configured_repository_path(public):
    for route in ('red/index.html', 'why-red.html', 'red/why-red.html', 'holdings.html', 'etfs/redi/document-placeholder.html', 'etfs/redi/blog/index.html', 'red/blog/index.html', 'research/redi/index.html'):
        page = parsed(public / route)
        target = canonical_route(route)
        path = target.removesuffix('index.html') if target.endswith('index.html') else target
        assert page.select_one('link[rel=canonical]')['href'] == 'https://oftarradiddle.github.io/RED/' + path
    for html in public.rglob('*.html'):
        page = parsed(html)
        assert page.select_one('meta[property="og:image"]')['content'] == 'https://oftarradiddle.github.io/RED/assets/hetzerk-social.png'
        assert 'localhost' not in str(page.head)
        assert page.html['lang'] == 'en'
        assert len(page.select('h1')) == 1
        for selector in ('title', 'meta[charset]', 'meta[name=viewport]', 'meta[name=description]', 'meta[name=robots]', 'meta[property="og:image"]', 'meta[name="twitter:card"]'):
            assert len(page.select(selector)) == 1, (html, selector)
    page = parsed(public / 'index.html')
    assert page.select_one('link[rel=stylesheet]')['href'].startswith('/RED/assets/')
    assert page.select_one('a[href="/RED/etfs/redi/"]')
    schema = json.loads(page.select_one('script[type="application/ld+json"]').string)
    assert {node['@type'] for node in schema['@graph']} == {'Organization', 'WebSite', 'WebPage'}
    assert not any(key in json.dumps(schema) for key in ('telephone', 'address', 'FinancialProduct', 'aggregateRating'))


def test_current_research_is_indexable_with_truthful_report_metadata(public):
    locations = {node.text for node in ET.parse(public / 'sitemap.xml').findall('sm:url/sm:loc', NS)}
    root = 'https://oftarradiddle.github.io/RED'
    for route, path in (('research/index.html', '/research/'), ('research/the-measure-of-fire.html', '/research/the-measure-of-fire.html'),
                        ('research/on-innovation-factor-investing.html', '/research/on-innovation-factor-investing.html')):
        page = parsed(public / route)
        assert root + path in locations
        assert page.title.string == METADATA[route][0]
        assert page.select_one('meta[name=description]')['content'] == METADATA[route][1]
        assert page.select_one('link[rel=canonical]')['href'] == root + path
        assert page.select_one('meta[name=robots]')['content'].startswith('index,')
    report = parsed(public / 'research/the-measure-of-fire.html')
    assert report.select_one('meta[property="og:type"]')['content'] == 'article'
    graph = json.loads(report.select_one('script[type="application/ld+json"]').string)['@graph']
    article = next(node for node in graph if node['@type'] == 'Article')
    webpage = next(node for node in graph if node['@type'] == 'WebPage')
    canonical = root + '/research/the-measure-of-fire.html'
    assert article['url'] == canonical
    assert article['mainEntityOfPage'] == {'@id': canonical + '#webpage'}
    assert webpage['mainEntity'] == {'@id': canonical + '#article'}
    assert article['author']['@type'] == 'Organization'
    assert article['author']['name'] == 'Hetzerk Asset Management'
    assert article['encoding']['contentUrl'] == root + '/assets/research/the-measure-of-fire.pdf'
    assert article['encoding']['encodingFormat'] == 'application/pdf'
    assert not {'datePublished', 'dateModified', 'aggregateRating', 'award'}.intersection(article)
    perspective = parsed(public / 'research/on-innovation-factor-investing.html')
    perspective_graph = json.loads(perspective.select_one('script[type="application/ld+json"]').string)['@graph']
    perspective_article = next(node for node in perspective_graph if node['@type'] == 'Article')
    assert perspective_article['headline'].startswith('Conviction, Measured')
    assert 'encoding' not in perspective_article
    assert not perspective.select('link[rel="alternate"][type="application/pdf"]')
    for route in ('research/sample-post-1.html', 'etfs/redi/blog/sample-post-1.html'):
        page = parsed(public / route)
        assert page.select_one('meta[name=robots]')['content'] == 'noindex,follow'
        assert page.select_one('link[rel=canonical]')['href'] not in locations
    for route in ('etfs/redi/blog/index.html', 'red/blog/index.html', 'research/redi/index.html'):
        page = parsed(public / route)
        assert page.select_one('link[rel=canonical]')['href'] == root + '/research/'
        assert page.title.string == METADATA['research/index.html'][0]
        assert root + '/' + route.removesuffix('index.html') not in locations
        assert page.select_one('a[href="/RED/research/the-measure-of-fire.html"]')
        assert not page.select('a[href*="sample-post"]')


def test_local_build_remains_noindex_without_fake_canonical(tmp_path):
    output = tmp_path / 'local'
    build(BOOK, output)
    page = parsed(output / 'index.html')
    assert page.select_one('meta[name=robots]')['content'] == 'noindex,follow'
    assert not page.select('link[rel=canonical]')
    assert page.select_one('meta[property="og:image"]')['content'] == '/assets/hetzerk-social.png'
    assert not ET.parse(output / 'sitemap.xml').findall('sm:url', NS)
    assert 'Disallow: /' not in (output / 'robots.txt').read_text()


def test_strategy_research_is_separate_from_fund_data_and_cached_at_the_public_base_path(public):
    research = json.loads((public / 'compare/research.json').read_text())
    market = json.loads((public / 'compare/data.json').read_text())
    assert research['frequency'] == 'monthly'
    assert research['source']['url'] == '/RED/research/the-measure-of-fire.html'
    assert len(research['series']) == 5
    assert all(len(series['observations']) == 281 for series in research['series'])
    assert research['series'][0]['observations'][-1] == {'date': '2026-08-31', 'level': 48.08}
    assert {series['id'] for series in market['series']} == {'REDI', 'SPY', 'VOO', 'QQQ', 'ITAN', 'SYLD'}
    assert market['series'][0]['is_illustrative'] is True
    worker = (public / 'compare/sw.js').read_text()
    assert '/RED/compare/research.json' in worker
    for asset in ('strategy-research.css', 'strategy-research-math.js', 'strategy-research.js'):
        assert f'/RED/assets/{asset}' in worker
    for route in ('compare/index.html', 'etfs/redi/index.html'):
        page = parsed(public / route)
        assert len(page.select('[data-strategy-research]')) == 1
        assert page.select_one('a[href="/RED/compare/research.json"]')
        scripts = [tag.get('src') for tag in page.select('script[src]')]
        assert scripts.index('/RED/assets/comparison-math.js') < scripts.index('/RED/assets/strategy-research-math.js')


@pytest.mark.parametrize(('url', 'path', 'indexable'), [
    (None, '', True), ('http://example.com', '', True),
    ('https://localhost', '', False), ('https://example.com?x=1', '', True),
    ('https://example.com/#fragment', '', True), ('https://user:secret@example.com', '', True),
    ('https://example.com:8080', '', True), ('https://example.com/RED', '', True),
    ('https://example.com', '/RED', True), ('https://example.com/RED/other', '/RED/other', True),
])
def test_rejects_ambiguous_or_unsafe_public_urls(url, path, indexable):
    with pytest.raises(ValueError):
        validate_site_url(url, path, indexable)


def test_custom_domain_metadata_is_deduplicated_and_jsonld_safe():
    html = '''<!doctype html><html><head><title>A &lt;/script&gt;&lt;img src=x&gt;</title><meta name=description content="D"><meta name=description content="Duplicate"><meta name=robots content=noindex><meta property="og:image" content="http://localhost:8080/old.png"></head><body><h1>A</h1></body></html>'''
    page = BeautifulSoup(apply_seo({'custom.html': html}, site_url='https://www.example.com')['custom.html'], 'html.parser')
    assert len(page.select('meta[name=description]')) == 1
    assert len(page.select('meta[property="og:image"]')) == 1
    script = page.select_one('script[type="application/ld+json"]')
    assert '\\u003c/script' in script.string
    assert json.loads(script.string)['@graph'][0]['name'] == 'A </script><img src=x>'
    assert not page.select('img')
    assert page.select_one('link[rel=canonical]')['href'] == 'https://www.example.com/custom.html'
