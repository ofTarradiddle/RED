"""The archive publishes dated public evidence, never its source caches or services."""
import copy
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from publishing.innovation_atlas import render_innovation_atlas
from publishing.innovation_release import publish_innovation
from publishing.seo import apply_seo

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def dataset():
    return json.loads((ROOT / 'data/innovation/dataset.json').read_text())


def test_publication_is_validated_and_contains_no_cache_or_backend(tmp_path, dataset):
    publish_innovation(tmp_path, leaderboard_url='')
    assert set(p.name for p in (tmp_path / 'innovation').iterdir()) == {'data.json', 'config.json'}
    assert json.loads((tmp_path / 'innovation/data.json').read_text()) == dataset
    assert json.loads((tmp_path / 'innovation/config.json').read_text()) == {'leaderboardUrl': None}
    assert len(dataset['catalog']) > 1000
    assert dataset['coverage']['priceObservations'] > 10000


def test_future_financials_and_quotes_cannot_be_published(tmp_path, dataset):
    bad = copy.deepcopy(dataset)
    event = next(e for e in bad['opportunities'] if e['decision'].get('valuation'))
    event['decision']['valuation']['availableAt'] = '2099-01-01'
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='Future filing'):
        publish_innovation(tmp_path / 'release', dataset_path=path)
    bad = copy.deepcopy(dataset)
    bad['asOf'] = '1960-01-01'
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='cutoff'):
        publish_innovation(tmp_path / 'release', dataset_path=path)
    assert not (tmp_path / 'release').exists()


@pytest.mark.parametrize('url', ['http://example.com', 'https://user:pass@example.com', 'https://example.com/?token=x', 'javascript:alert(1)'])
def test_invalid_score_endpoints_are_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='HTTPS'):
        publish_innovation(tmp_path, leaderboard_url=url)


def test_atlas_is_a_public_canonical_route_with_accessible_controls():
    pages = apply_seo({'innovation/index.html': render_innovation_atlas()},
                      site_url='https://oftarradiddle.github.io/RED/', base_path='/RED', indexable=True)
    soup = BeautifulSoup(pages['innovation/index.html'], 'html.parser')
    assert soup.select_one('link[rel="canonical"]')['href'] == 'https://oftarradiddle.github.io/RED/innovation/'
    assert soup.select_one('meta[name="robots"]')['content'].startswith('index,')
    assert soup.select_one('#motion-toggle')['aria-label']
    assert soup.select_one('#innovation-detail')['aria-labelledby'] == 'detail-title'
    assert soup.select_one('#game-start').has_attr('disabled')
    assert 'cash before its first available 1993' in soup.get_text()
