"""Keep one premium/discount history beside its fund trading disclosures."""
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
def test_single_premium_history_uses_current_fund_data(pages, route):
    page = BeautifulSoup(pages[route], 'html.parser')
    trading = page.select_one('#trading #premium-chart')
    assert trading and trading['role'] == 'img'
    assert len(page.select('#premium-chart')) == 1
    assert not page.select('#premium-overview-chart, #premiumChart, #premium-value, .premium-indicator')
    overview = page.find(id='overview')
    assert 'Premium/Discount' not in overview.get_text()
    prices = next(h for h in overview.find_all('h3') if h.get_text(strip=True) == 'Fund Prices')
    assert len(prices.parent.parent.find_all('div', recursive=False)) == 1
    assert page.select_one('#performance-chart')
    assert len(page.select('[data-period]')) == 6
    assert page.select_one('script[src="/assets/site.js"][defer]')
    fund = json.loads(page.find(id='page-data').string)
    for row in fund['daily']:
        assert row['premium_discount'] == pytest.approx(row['market_price'] / row['nav'] - 1)
    last = fund['daily'][-1]
    panel = trading.parent
    assert panel.find('strong').get_text() == f'{last["premium_discount"]:+.2%}'
    assert [cell.get_text(strip=True) for cell in panel.select('thead th')] == [
        'Completed period', 'Premium days', 'Discount days', 'At NAV']
    expected = [[str(period[key]) for key in ('period', 'premium_days', 'discount_days', 'at_nav_days')]
                for period in fund['disclosure_periods']]
    assert [[cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])]
            for row in panel.select('tbody tr')] == expected
    assert panel.find('details').find('summary').get_text(strip=True) == 'Premium / discount exception disclosures'


def test_premium_input_is_a_decimal_fraction_with_correct_sign():
    rows = [dict(date=d, nav=100, market_price=p, distribution_per_share=0, benchmark_index=100)
            for d, p in [('2026-01-02', 101), ('2026-01-05', 99), ('2026-01-06', 100)]]
    daily, _ = performance(rows)
    assert [row['premium_discount'] for row in daily] == pytest.approx([.01, -.01, 0])
