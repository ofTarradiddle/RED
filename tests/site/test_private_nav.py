"""Economic scenarios and the local-only publication boundary."""
from decimal import Decimal
from pathlib import Path
import re
from bs4 import BeautifulSoup
import pytest

from publishing.private_nav import calculate, PRIVATE_ROUTE, render_dashboard
from publishing.site import generate_pages
from publishing.workbook import import_workbook
from publishing.documents import CATALOG

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def snapshot():
    return import_workbook(ROOT/'workbooks/hetzerk-demo.xlsx')


def redi(snapshot):
    return next(f for f in snapshot['funds'] if f['fund_id']=='redi')


def test_baseline_nav_and_rounding(snapshot):
    f=redi(snapshot)
    r=calculate(f,{'price_bps':['0']})['report']
    assert r['status']=='within_tolerance'
    assert r['unrounded_difference_bps']==0
    assert float(r['shadow']['nav'])==pytest.approx(f['daily'][-1]['nav'])
    assert r['shadow']['assets']-r['shadow']['liabilities']==r['shadow']['net_assets']
    assert r['attribution_residual']==0


def test_price_and_fee_scenario_attributes_every_dollar(snapshot):
    f=redi(snapshot)
    base=calculate(f,{'price_bps':['0']})
    model=calculate(f,{'price_bps':['100'],'fee':[str(base['fee_estimate'])]})
    report=model['report']
    abt=next(h for h in f['holdings'] if h['ticker']=='ABT')
    expected=Decimal(str(abt['quantity']))*Decimal(str(abt['price']))*Decimal('.01')-base['fee_estimate']
    delta=report['shadow']['net_assets']-base['report']['shadow']['net_assets']
    assert abs(delta-expected)<Decimal('.00000001')
    assert report['balance_breaks']['accrued_fees']==-base['fee_estimate']
    assert report['attribution_residual']==0
    assert report['status']=='difference'
    assert f['expense_ratio']==.0045
    assert base['fee_estimate']==Decimal('348.52')


@pytest.mark.parametrize('query',[{'fee':['NaN']},{'price_bps':['-10000']},{'fee':['-1']},{'tolerance':['1','2']}])
def test_rejects_invalid_scenarios(snapshot,query):
    with pytest.raises(ValueError):calculate(redi(snapshot),query)


def test_publication_has_data_documents_but_no_private_route(snapshot):
    pages=generate_pages(snapshot)
    for route,html in pages.items():
        assert PRIVATE_ROUTE not in html
        assert 'Shadow NAV' not in html
        page=BeautifulSoup(html,'html.parser')
        if route == 'innovation/index.html':
            assert page.select_one('.development-notice')
            assert 'All game money is fictional' in page.get_text()
            continue
        banner=page.select_one('.demo-strip');assert banner
        banner.decompose()
        assert not re.search(r'\bdemo\b|illustrative|fictional|synthetic',page.get_text(' ',strip=True),re.I),route
    docs=BeautifulSoup(pages['documents/index.html'],'html.parser')
    for key,_,_,url in CATALOG:
        assert docs.find(id=key).find('a',href=url)
    fund=BeautifulSoup(pages['etfs/redi/index.html'],'html.parser')
    assert '0.45%' in fund.get_text()
    assert len(fund.select('#top-holdings tbody tr'))==10
    assert len(redi(snapshot)['daily'])>500
    assert any(row['premium_discount']>0 for row in redi(snapshot)['daily'])
    assert any(row['premium_discount']<0 for row in redi(snapshot)['daily'])
    assert len(BeautifulSoup(pages['etfs/redi/holdings.html'],'html.parser').select('#holdings-table tbody tr'))==60
    private=BeautifulSoup(render_dashboard(redi(snapshot)),'html.parser')
    assert private.find('form',action=PRIVATE_ROUTE)
    assert 'Shadow NAV' in private.get_text()
