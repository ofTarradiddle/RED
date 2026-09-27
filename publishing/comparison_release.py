"""Publish the comparison app's public data and its scoped offline shell."""
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
APP_ASSETS = (
    'comparison.css', 'comparison-math.js', 'comparison.js', 'comparison-install.js',
    'strategy-research.css', 'strategy-research-math.js', 'strategy-research.js',
    'branding.css', 'development-notice.css', 'development-notice.js',
    'favicon.svg?v=wing-h-1', 'favicon-motion.js?v=1', 'hetzerk-bounce.gif', 'hetzerk-mark-still.svg',
    'compare-icon-180.png', 'compare-icon-192.png', 'compare-icon-512.png',
    'fonts.css', 'fonts/ee9558be9f8a.ttf', 'fonts/a699af1dea30.ttf',
    'fonts/e45972c7e9f2.ttf', 'fonts/87e867b52640.ttf', 'fonts/6f49e1b28bce.ttf',
    'fonts/d0e784ef034d.ttf', 'fonts/7d62dda1d389.ttf', 'fonts/5ae86d38cfa3.ttf',
    'fonts/c67a6241b1e0.ttf', 'fonts/8a70c7995340.ttf',
)


def _positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive')
    return value


def redi_series(fund, live_path=None):
    """Keep the prelaunch workbook separate from an explicitly approved live feed."""
    if live_path and Path(live_path).exists():
        source = json.loads(Path(live_path).read_text())
        if source.get('approved_for_publication') is not True or source.get('id') != 'REDI' or source.get('is_illustrative') is not False:
            raise ValueError('Live REDI input needs approval and the REDI identifier')
        url = urlsplit(source.get('source_url', ''))
        if url.scheme != 'https' or not url.netloc or url.username or url.password:
            raise ValueError('Live REDI input needs a public HTTPS provider source URL')
        if not str(source.get('source', '')).strip() or source.get('currency') != 'USD':
            raise ValueError('Live REDI input needs its provider name and USD currency')
        if source.get('price_basis') != 'split_adjusted':
            raise ValueError('Live REDI history and distributions must share a split-adjusted per-share basis')
        inception = date.fromisoformat(source['inception_date'])
        if source['inception_date'] != inception.isoformat():
            raise ValueError('Live REDI inception date must use YYYY-MM-DD')
        rows = []
        for row in source['observations']:
            day = date.fromisoformat(row['date'])
            if row['date'] != day.isoformat():
                raise ValueError('Live REDI observation dates must use YYYY-MM-DD')
            if day < inception or day > datetime.now(timezone.utc).date():
                raise ValueError('Live REDI observation lies outside its live history')
            if rows and row['date'] <= rows[-1]['date']:
                raise ValueError('Live REDI dates must be unique and sorted')
            distribution = row['distribution']
            if isinstance(distribution, bool) or not isinstance(distribution, (int, float)) or not math.isfinite(distribution) or distribution < 0:
                raise ValueError('Live REDI distributions must be finite and nonnegative')
            rows.append(dict(date=day.isoformat(),
                             nav=_positive(row['nav'], 'Official NAV'),
                             market_price=_positive(row['market_price'], 'Market price'),
                             distribution=distribution, split=0))
        if not rows:
            raise ValueError('Live REDI input has no daily observations')
        return dict(id='REDI', name='Hetzerk Innovation Factor ETF', currency='USD', kind='etf',
                    source=source['source'], source_url=source['source_url'],
                    inception_date=inception.isoformat(), as_of=rows[-1]['date'],
                    status='ok', is_illustrative=False, observations=rows)
    rows = [dict(date=row['date'], nav=row['nav'], market_price=row['market_price'],
                 distribution=row['distribution_per_share'], split=0) for row in fund['daily']]
    return dict(id='REDI', name='Hetzerk Innovation Factor ETF', currency='USD', kind='etf',
                source='Illustrative workbook · not a live fund track record',
                source_url='/review/', as_of=rows[-1]['date'], status='ok',
                is_illustrative=True, observations=rows)


def comparison_payload(snapshot, peer_path=None, live_path=None):
    from publishing.comparison_data import validate_series

    fund = next(f for f in snapshot['funds'] if f['fund_id'] == 'redi')
    path = Path(peer_path or ROOT / 'data/etf_comparison.json')
    peer = json.loads(path.read_text()) if path.exists() else {}
    if peer and peer.get('schema_version') != 1:
        raise ValueError('Unsupported comparison peer schema')
    series = []
    seen = set()
    for item in peer.get('series', []):
        if item['id'] not in {'SPY', 'VOO', 'QQQ', 'ITAN', 'SYLD'} or item['id'] in seen:
            raise ValueError('Unexpected or duplicate comparison peer')
        seen.add(item['id'])
        series.append(validate_series(item))
    return dict(schema_version=1, generated_at=datetime.now(timezone.utc).isoformat(),
                market_refresh_at=peer.get('generated_at'), last_attempt_at=peer.get('last_attempt_at'),
                status=peer.get('status', 'unavailable'), expense_ratio=fund['expense_ratio'],
                series=[redi_series(fund, live_path), *series])


def publish_comparison(stage, snapshot, *, base_path='', peer_path=None, live_path=None):
    folder = stage / 'compare'
    payload = comparison_payload(snapshot, peer_path, live_path)
    for series in payload['series']:
        if series.get('source_url', '').startswith('/'):
            series['source_url'] = base_path + series['source_url']
    if not payload['series'][0]['is_illustrative']:
        from bs4 import BeautifulSoup
        path = folder / 'index.html'
        page = BeautifulSoup(path.read_text(), 'html.parser')
        banner = page.select_one('.demo-strip .compare-width')
        banner.clear()
        label = page.new_tag('strong')
        label.string = 'Development preview'
        banner.append(label)
        banner.append(' REDI uses approved provider observations. Peer series use historical Yahoo market data. Sources and dates are shown below. Not an investment offering.')
        path.write_text(str(page))
    (folder / 'data.json').write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False))
    from scripts.import_strategy_research import validate_payload
    research = validate_payload(json.loads((ROOT / 'data/strategy_research.json').read_text()))
    research['source']['url'] = base_path + research['source']['url']
    (folder / 'research.json').write_text(json.dumps(research, separators=(',', ':'), allow_nan=False))
    from scripts.import_comparison_research import SOURCE_PATH, validate_payload as validate_comparison_research
    comparison_research = validate_comparison_research(json.loads((ROOT / 'data/comparison_research.json').read_text()))
    source_bytes = SOURCE_PATH.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != comparison_research['source']['sha256']:
        raise ValueError('The downloadable comparison source does not match its reviewed dataset')
    comparison_research['source']['url'] = base_path + comparison_research['source']['url']
    (folder / 'comparison-research.json').write_text(json.dumps(comparison_research, separators=(',', ':'), allow_nan=False))
    (folder / 'research-source.tsv').write_bytes(source_bytes)
    manifest = dict(id='./', name='REDI Compare · Hetzerk', short_name='REDI Compare',
                    description='Compare REDI with selected equity ETFs.', lang='en',
                    start_url='./', scope='./', display='standalone',
                    background_color='#171617', theme_color='#171617',
                    icons=[dict(src=f'../assets/compare-icon-{size}.png', sizes=f'{size}x{size}',
                                type='image/png', purpose='any maskable') for size in (192, 512)])
    (folder / 'manifest.webmanifest').write_text(json.dumps(manifest, indent=2))
    files = [f'{base_path}/compare/', f'{base_path}/compare/index.html',
             f'{base_path}/compare/data.json', f'{base_path}/compare/research.json',
             f'{base_path}/compare/comparison-research.json', f'{base_path}/compare/research-source.tsv',
             f'{base_path}/compare/manifest.webmanifest',
             *(f'{base_path}/assets/{name}' for name in APP_ASSETS)]
    digest = hashlib.sha256()
    for url in files:
        relative = url.removeprefix(base_path + '/').split('?')[0]
        if relative.endswith('/'):
            relative += 'index.html'
        digest.update((stage / relative).read_bytes())
    worker = (ROOT / 'assets/comparison-worker.js').read_text()
    digest.update(worker.encode())
    worker = worker.replace('__APP_FILES__', json.dumps(files))
    worker = worker.replace('__APP_REVISION__', digest.hexdigest()[:16])
    (folder / 'sw.js').write_text(worker)
