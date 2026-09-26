"""Temporary publication choices; all fund templates and workbook rows are kept."""
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment

# Uncomment a fund here to restore its pages, cards and public data together.
ACTIVE_FUND_IDS = (
    'redi',
    # 'dam1',
    # 'azoc',
    # 'mpd',
    # 'meri',
)
ALL_FUND_IDS = ('redi', 'dam1', 'azoc', 'mpd', 'meri')
# The old launch concepts are also paused while only Innovation Factor is shown.
ACTIVE_PIPELINE_TICKERS = (
    # 'DMVP',
    # 'DSCB',
    # 'DSHR',
    # 'DCRR',
)
PIPELINE_TICKERS = ('DMVP', 'DSCB', 'DSHR', 'DCRR')


def route_is_active(route):
    parts = route.strip('/').split('/')
    return not (len(parts) > 1 and parts[0] in ('etfs', 'research')
                and parts[1] in ALL_FUND_IDS and parts[1] not in ACTIVE_FUND_IDS)


def public_snapshot(snapshot):
    return {**snapshot, 'funds': [f for f in snapshot['funds'] if f['fund_id'] in ACTIVE_FUND_IDS]}


def comment_out(tag):
    tag.replace_with(Comment(' Temporarily paused; source retained.\n' + str(tag).replace('--', '—') + '\n'))


def visible_pages(pages, snapshot):
    active_funds = public_snapshot(snapshot)['funds']
    paused_tickers = {fid.upper() for fid in ALL_FUND_IDS if fid not in ACTIVE_FUND_IDS}
    paused_pipeline = set(PIPELINE_TICKERS) - set(ACTIVE_PIPELINE_TICKERS)
    published = {}
    for route, content in pages.items():
        if not route_is_active(route):
            continue
        page = BeautifulSoup(content, 'html.parser')
        for tag in list(page.select('a[href]')):
            if not route_is_active(urlsplit(tag['href']).path):
                comment_out(tag)
        for tag in list(page.select('[data-interest-fund]')):
            if tag['data-interest-fund'] in paused_pipeline:
                comment_out(tag)
        # The lineup has its own original launch-card layout and ticker badge strip.
        for title in list(page.find_all(['h3', 'h4'])):
            if title.get_text(' ', strip=True) in paused_pipeline:
                container = next((p for p in title.parents if 'group' in p.get('class', [])), None)
                if container:
                    comment_out(container)
        for tag in list(page.find_all('span')):
            if tag.get_text(' ', strip=True) in paused_tickers and not tag.find(True):
                comment_out(tag.parent)
        for select in page.select('[data-interest-form] select[name=fund]'):
            for option in list(select.find_all('option')):
                if option.get('value') not in ACTIVE_PIPELINE_TICKERS:
                    comment_out(option)
            for f in active_funds:
                option = page.new_tag('option', value=f['ticker'], style='color:#111')
                option.string = f'{f["ticker"]} — {f["name"]}'
                select.append(option)
        if not ACTIVE_PIPELINE_TICKERS:
            for tag in list(page.find_all(['h2', 'h3'])):
                if tag.get_text(' ', strip=True) == 'Upcoming Launches':
                    comment_out(tag.parent)
            for p in page.find_all('p'):
                if 'Credit and multi-asset concepts below' in p.get_text():
                    p.string = 'Current focus: Hetzerk Innovation Factor ETF (REDI). Any proposed contribution remains subject to eligibility and transaction review.'
        if len(active_funds) == 1:
            replacements = {
                'Explore Our ETFs': 'Explore Our ETF',
                'Distinct strategies. A research-grounded approach.': 'Hetzerk Innovation Factor ETF. A research-grounded approach.',
                'Our Live Funds': 'Our Proposed ETF',
                'Our ETFs': 'Our ETF',
                'View Our ETFs': 'View Our ETF',
                'All Upcoming Launches': 'Hetzerk Innovation Factor ETF',
            }
            for node in list(page.find_all(string=True)):
                if isinstance(node, Comment) or node.parent.name in ('style', 'script'):
                    continue
                if node.strip() in replacements:
                    node.replace_with(replacements[node.strip()])
        published[route] = str(page)
    return published
