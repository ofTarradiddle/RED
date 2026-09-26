"""Public comparison boundary: illustrative REDI stays distinct from live peers."""
from copy import deepcopy
import json

import pytest

from publishing.comparison_release import comparison_payload, redi_series


@pytest.fixture
def fund():
    return dict(fund_id='redi', expense_ratio=0.0045, daily=[
        dict(date='2026-09-24', nav=25, market_price=25.01, distribution_per_share=0),
        dict(date='2026-09-25', nav=25.1, market_price=25.11, distribution_per_share=0.05),
    ])


@pytest.fixture
def live():
    return dict(id='REDI', approved_for_publication=True, is_illustrative=False,
                price_basis='split_adjusted', currency='USD', source='Official fund administrator',
                source_url='https://provider.example/redi', inception_date='2026-09-24',
                observations=[dict(date='2026-09-24', nav=25, market_price=25.01, distribution=0),
                              dict(date='2026-09-25', nav=25.1, market_price=25.11, distribution=0.05)])


def write_json(tmp_path, value, name='input.json'):
    path = tmp_path / name
    path.write_text(json.dumps(value))
    return path


def peer():
    return dict(id='SPY', name='Untrusted name', currency='USD', kind='etf', source='Yahoo Finance',
                source_url='https://wrong.example/', as_of='2026-09-25', status='ok',
                is_illustrative=False, private_accounting='must never publish',
                observations=[dict(date='2026-09-24', market_price=100, adjusted_close=99, distribution=0, split=0),
                              dict(date='2026-09-25', market_price=101, adjusted_close=101, distribution=0.5, split=0)])


def test_prelaunch_workbook_cannot_become_a_live_track_record(fund):
    output = redi_series(fund)
    assert output['is_illustrative'] is True
    assert 'not a live fund track record' in output['source']
    assert output['observations'][1]['distribution'] == 0.05
    assert 'inception_date' not in output


def test_public_payload_sanitizes_peers_and_keeps_real_vs_illustrative_separate(fund, tmp_path):
    source = dict(schema_version=1, status='ok', series=[peer()], private_balances='do not publish')
    output = comparison_payload({'funds': [fund]}, write_json(tmp_path, source))
    assert [item['id'] for item in output['series']] == ['REDI', 'SPY']
    redi, spy = output['series']
    assert redi['is_illustrative'] is True and spy['is_illustrative'] is False
    assert spy['name'] == 'SPDR S&P 500 ETF Trust'
    assert spy['source_url'] == 'https://finance.yahoo.com/quote/SPY/history/'
    assert 'private_' not in json.dumps(output)


@pytest.mark.parametrize('ticker', ['REDI', 'AAPL', 'SPY'])
def test_peer_boundary_rejects_unexpected_or_duplicate_tickers(fund, tmp_path, ticker):
    first = peer()
    second = deepcopy(first)
    second['id'] = ticker
    source = dict(schema_version=1, status='ok', series=[first, second])
    with pytest.raises(ValueError, match='Unexpected or duplicate'):
        comparison_payload({'funds': [fund]}, write_json(tmp_path, source))


def test_approved_live_input_uses_official_rows_without_blending_workbook(fund, live, tmp_path):
    live['observations'][0]['nav'] = 40
    live['private_blotter'] = [{'account': 'not public'}]
    output = redi_series(fund, write_json(tmp_path, live))
    assert output['is_illustrative'] is False
    assert output['observations'][0]['nav'] == 40
    assert output['inception_date'] == '2026-09-24'
    assert 'private_blotter' not in output


@pytest.mark.parametrize('change', ['unapproved', 'wrong_id', 'zero_nav', 'infinite_price',
                                   'negative_distribution', 'duplicate_date', 'before_inception',
                                   'empty_history', 'invalid_url'])
def test_invalid_live_input_fails_instead_of_falling_back_to_workbook(fund, live, tmp_path, change):
    if change == 'unapproved': live['approved_for_publication'] = False
    elif change == 'wrong_id': live['id'] = 'SPY'
    elif change == 'zero_nav': live['observations'][0]['nav'] = 0
    elif change == 'infinite_price': live['observations'][0]['market_price'] = float('inf')
    elif change == 'negative_distribution': live['observations'][0]['distribution'] = -1
    elif change == 'duplicate_date': live['observations'][1]['date'] = live['observations'][0]['date']
    elif change == 'before_inception': live['observations'][0]['date'] = '2026-09-23'
    elif change == 'empty_history': live['observations'] = []
    elif change == 'invalid_url': live['source_url'] = 'http://provider.example/data'
    with pytest.raises(ValueError):
        redi_series(fund, write_json(tmp_path, live))


@pytest.mark.parametrize('field', ['is_illustrative', 'price_basis'])
def test_live_feed_needs_explicit_real_split_adjusted_identity(fund, live, tmp_path, field):
    del live[field]
    with pytest.raises(ValueError):
        redi_series(fund, write_json(tmp_path, live))


def test_noncanonical_live_dates_cannot_bypass_ordering(fund, live, tmp_path):
    live['observations'][0]['date'] = '2026-09-25'
    live['observations'][1]['date'] = '20260924'
    with pytest.raises(ValueError):
        redi_series(fund, write_json(tmp_path, live))
