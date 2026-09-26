"""Keep the overview and trading premium/discount history connected to fund data."""
import json
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from publishing.site import generate_pages
from publishing.workbook import import_workbook, performance


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def pages():
    return generate_pages(import_workbook(ROOT / 'workbooks/hetzerk-demo.xlsx'))


@pytest.mark.parametrize('route', ['etfs/redi/index.html', 'red/index.html'])
def test_both_premium_histories_use_current_fund_data(pages, route):
    page = BeautifulSoup(pages[route], 'html.parser')
    overview = page.select_one('#overview #premium-overview-chart')
    trading = page.select_one('#trading #premium-chart')
    assert overview and trading
    assert overview['role'] == trading['role'] == 'img'
    assert not page.select('#premiumChart, .premium-indicator')
    assert page.select_one('script[src="/assets/site.js"][defer]')
    fund = json.loads(page.find(id='page-data').string)
    for row in fund['daily']:
        assert row['premium_discount'] == pytest.approx(row['market_price'] / row['nav'] - 1)
    last = fund['daily'][-1]
    assert page.find(id='premium-value').get_text() == f'{last["premium_discount"]:+.2%}'
    assert '(Market Price ÷ NAV − 1) × 100' in overview.parent.parent.get_text()


def test_premium_input_is_a_decimal_fraction_with_correct_sign():
    rows = [dict(date=d, nav=100, market_price=p, distribution_per_share=0, benchmark_index=100)
            for d, p in [('2026-01-02', 101), ('2026-01-05', 99), ('2026-01-06', 100)]]
    daily, _ = performance(rows)
    assert [row['premium_discount'] for row in daily] == pytest.approx([.01, -.01, 0])
