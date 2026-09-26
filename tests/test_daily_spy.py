from copy import deepcopy
from decimal import Decimal as D
import json
from pathlib import Path
import pytest

from lib.etf.daily_spy import make_report, parse_nav, parse_holdings
from publishing.spy_proxy import public_input, apply_proxy
from publishing.workbook import import_workbook
from publishing.private_spy import render

ROOT=Path(__file__).resolve().parents[1]


def report():
    holdings=[dict(identifier='ABC',ticker='ABC',name='ABC',sector='Unclassified',yahoo_symbol='ABC',quantity='10',issuer_weight='.8',security_type='equity',currency='USD'),
              dict(identifier='RIGHT',ticker='CVR',name='Right',sector='Unclassified',yahoo_symbol=None,quantity='1',issuer_weight='.01',security_type='corporate_action_right',currency='USD'),
              dict(identifier='USD',ticker='CASH',name='Cash',sector='Cash',yahoo_symbol=None,quantity='20',issuer_weight='.2',security_type='cash',currency='USD')]
    official=dict(nav='10',net_assets='100',shares_outstanding='10')
    quote=dict(date='2026-09-22',close='8',currency='USD',error=None,actions=[])
    files={k:dict(url='https://example.com/'+k,sha256='a'*64) for k in ('holdings','nav')}
    manifest=dict(fetched_at='2026-09-23T00:00:00Z',files=files,engine_sha256='b'*64)
    return make_report('2026-09-22',holdings,official,{'ABC':quote},[],manifest)


def test_public_holdings_reprice_never_fills_missing_balances_or_cvr():
    r=report();v=r['valuation']
    assert D(v['known_assets'])==100
    assert D(v['raw_difference_per_share'])==0
    assert v['independent_nav'] is None and v['status']=='Incomplete reconciliation'
    assert r['exceptions'][0]['identifier']=='RIGHT'
    assert v['missing_balances'] and D(v['unpriced_issuer_value_estimate'])==1
    assert D(v['covered_price_effect'])==0
    html=render(r)
    assert 'not a completed NAV' in html and 'No SPY execution confirmations' in html


def test_nav_rounded_precision_and_duplicate_dates(monkeypatch):
    header=[('Fund Name:','SPY'),('Ticker Symbol:','SPY'),(),('Date','NAV','Shares Outstanding','Total Net Assets')]
    row=('22-Sep-2026',10.000001,3,30.000002)
    monkeypatch.setattr('lib.etf.daily_spy.rows',lambda _:header+[row])
    assert parse_nav(b'')['2026-09-22']['shares_outstanding']=='3'
    monkeypatch.setattr('lib.etf.daily_spy.rows',lambda _:header+[row,row])
    with pytest.raises(ValueError,match='Duplicate'):parse_nav(b'')


def test_public_boundary_rejects_extra_fields(tmp_path):
    value=public_input(report());value['accounting_private']='must not publish'
    path=tmp_path/'public.json';path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='Unexpected fields'):
        apply_proxy(import_workbook(ROOT/'workbooks/hetzerk-demo.xlsx'),path)


def test_parser_rejects_changed_issuer_schema(monkeypatch):
    monkeypatch.setattr('lib.etf.daily_spy.rows',lambda _:[('Name','SPY'),('Ticker','VOO'),('Date','As of 22-Sep-2026'),(),()])
    with pytest.raises(ValueError,match='schema changed'):parse_holdings(b'')


def test_no_nav_from_cost_books():
    from lib.etf.ledger import replay
    opening=dict(date='2026-09-14',source='Test',shares=100,positions=[],balances=dict(cash=1000,dividend_receivable=0,trade_receivable=0,trade_payable=0,fee_payable=0,distribution_payable=0))
    state=replay(opening,[],'2026-09-15')
    assert state['nav'] is None and state['net_assets'] is None


def test_chart_uses_price_series_and_legend_has_no_returns():
    from bs4 import BeautifulSoup
    from publishing.site import generate_pages
    pages=generate_pages(import_workbook(ROOT/'workbooks/hetzerk-demo.xlsx'))
    page=BeautifulSoup(pages['etfs/redi/index.html'],'html.parser')
    chart=page.select_one('#performance-chart')
    assert chart['aria-label']=='NAV, Market Price and Morningstar US Market Index history'
    assert page.select_one('.chart-legend').get_text(' ',strip=True)=='NAV Market Price Morningstar US Market Index'
    js=(ROOT/'assets/site.js').read_text()
    assert "key:'nav'" in js and "key:'market_price'" in js
    assert "key:'benchmark_index'" in js and "mode === 'indexed'" in js
    assert 'total_return' not in js and 'reinvestment' not in js


def test_proxy_build_preserves_separate_dates_and_pages_paths(tmp_path):
    from bs4 import BeautifulSoup
    from publishing.build import build
    output=tmp_path/'pages'
    data=build(ROOT/'workbooks/hetzerk-demo.xlsx',output,ROOT/'data/spy_public.json','/RED')
    f=data['funds'][0]
    assert len(f['holdings'])>=491
    assert abs(sum(h['weight'] for h in f['holdings'])-1)<1e-12
    assert all(h['country']=='Not supplied' for h in f['holdings'] if h['security_type']=='equity')
    assert f['holdings_as_of']==json.loads((ROOT/'data/spy_public.json').read_text())['as_of']
    assert f['as_of']==f['daily'][-1]['date']
    page=BeautifulSoup((output/'etfs/redi/index.html').read_text(),'html.parser')
    assert 'SPY-based' in page.select_one('.demo-strip').get_text()
    assert page.find('link',href='/RED/assets/fonts.css')
    assert not (output/'perspective-7f3c9e').exists()
    assert not (output/'data/shadow_spy').exists()
    assert 'run_directory' not in (output/'data/snapshot.json').read_text()
    assert 'accounting_private' not in (output/'data/spy-source.json').read_text()
    assert 'url(/assets/' not in (output/'assets/fonts.css').read_text()
