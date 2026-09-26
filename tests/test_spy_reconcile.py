from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from hashlib import sha256
import json
import struct

import pytest

from lib.etf.spy_reconcile import extract_chart, reconcile, session_details, select_inventory, quote_all, parse_net_cash


def bridge_inputs():
    holdings=[dict(identifier='ABC',ticker='ABC',yahoo_symbol='ABC',security_type='equity',currency='USD',quantity='10'),
              dict(identifier='RIGHT',ticker='CVR',security_type='corporate_action_right',currency='USD',quantity='1'),
              dict(identifier='CASH',ticker='CASH',security_type='cash',currency='USD',quantity='1000000')]
    quotes={'ABC':dict(symbol='ABC',date='2026-09-23',currency='USD',instrument_type='EQUITY',close='8',source_url='https://example.test/quote')}
    official=dict(date='2026-09-23',nav='10',net_assets='100',shares_outstanding='10')
    cash=dict(date='2026-09-23',amount='19.99')
    marks={'RIGHT':dict(date='2026-09-23',price='.01',currency='USD',identity_source_url='https://example.test/id',source_url='https://example.test/mark',source_sha256='a'*64)}
    return holdings,quotes,official,cash,marks


def calc(inputs):
    h,q,o,c,m=inputs
    return reconcile(h,q,o,c,'2026-09-22','2026-09-23',m)


def test_net_cash_once_and_no_balancing_plug():
    inputs=bridge_inputs();r=calc(inputs)
    assert r['status']=='Matched to published NAV'
    assert D(r['known_net_assets'])==100 and D(r['difference_dollars'])==0
    inputs[0][-1]['quantity']='999999999'
    assert calc(inputs)['known_net_assets']==r['known_net_assets']
    inputs[2]['net_assets']='101';inputs[2]['nav']='10.1'
    assert D(calc(inputs)['known_net_assets'])==100
    assert D(calc(inputs)['difference_dollars'])==-1


def test_missing_or_wrong_date_prices_and_marks_remain_exceptions():
    inputs=bridge_inputs();inputs[1]['ABC']['date']='2026-09-22'
    assert calc(inputs)['missing_security_ids']==['ABC']
    inputs=bridge_inputs();inputs[4]['RIGHT']['date']='2026-09-22'
    assert calc(inputs)['missing_security_ids']==['RIGHT']
    assert calc(inputs)['status']!='Matched to published NAV'
    inputs=bridge_inputs();inputs[3]['date']='2026-09-22'
    with pytest.raises(ValueError,match='dates differ'):calc(inputs)


@pytest.mark.parametrize('field,value',[('currency','EUR'),('symbol','WRONG'),('instrument_type','ETF')])
def test_wrong_quote_identity_cannot_price_equity(field,value):
    inputs=bridge_inputs();inputs[1]['ABC'][field]=value
    assert calc(inputs)['missing_security_ids']==['ABC']


def chart(price='28.865',day='2026-09-23',symbol='CPRT'):
    _,stamp=session_details(day)
    raw=struct.unpack('f',struct.pack('f',float(price)))[0]
    return {'chart':{'result':[dict(meta=dict(symbol=symbol,currency='USD',instrumentType='EQUITY',regularMarketTime=int(stamp),regularMarketPrice=float(price),previousClose=900,chartPreviousClose=901),timestamp=[int(stamp)],indicators={'quote':[{'close':[raw]}]})]}}


@pytest.mark.parametrize('price',['28.865','8070.42'])
def test_decimal_close_preserves_half_cent_and_float32_precision(price):
    q=extract_chart(chart(price),'CPRT','2026-09-23','https://example.test')
    assert D(q['close'])==D(price)
    assert q['source_field']=='meta.regularMarketPrice'


def test_conflicting_closing_sources_fail_and_previous_close_never_fills():
    payload=chart();payload['chart']['result'][0]['indicators']['quote'][0]['close']=[28.87]
    with pytest.raises(ValueError,match='disagree'):extract_chart(payload,'CPRT','2026-09-23','https://example.test')
    payload=chart();payload['chart']['result'][0]['timestamp']=[]
    with pytest.raises(ValueError,match='exact-date'):extract_chart(payload,'CPRT','2026-09-23','https://example.test')


def test_calendar_holidays_early_closes_and_missing_nav_row(tmp_path):
    assert session_details('2026-09-08')[0]=='2026-09-04'
    prior,stamp=session_details('2026-11-27')
    assert prior=='2026-11-25'
    assert datetime.fromtimestamp(stamp,timezone.utc).hour==18
    with pytest.raises(ValueError,match='not an XNYS session'):session_details('2026-11-26')
    with pytest.raises(ValueError,match='Missing required prior-session'):select_inventory(tmp_path,{'2026-09-21':{}},'2026-09-23')


def test_cached_evidence_is_hashed_and_derived_fields_rebuilt(tmp_path):
    archive=tmp_path/'quote_archive/2026-09-23';archive.mkdir(parents=True)
    raw=json.dumps(chart()).encode();(archive/'CPRT-raw.json').write_bytes(raw)
    q=extract_chart(json.loads(raw),'CPRT','2026-09-23','https://example.test')
    q.update(source_sha256=sha256(raw).hexdigest(),actions=[dict(type='dividend',amount='10000')])
    (archive/'CPRT.json').write_text(json.dumps(q))
    result=quote_all(['CPRT'],'2026-09-23',tmp_path/'run',tmp_path)
    assert result['CPRT']['actions']==[]
    (archive/'CPRT-raw.json').write_bytes(raw+b' ')
    with pytest.raises(ValueError,match='hash mismatch'):quote_all(['CPRT'],'2026-09-23',tmp_path/'run2',tmp_path)


def test_dated_net_cash_parser():
    html='<section><h2>Fund Net Cash Amount</h2><span class="date">as of Sep 23 2026</span><table><td class="data">$141,915,813.06</td></table></section>'
    assert parse_net_cash(html)['amount']=='141915813.06'


def test_same_day_close_allowed_only_after_exchange_grace(monkeypatch):
    _,close=session_details('2026-09-23');clock={'timestamp':close+899}
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromtimestamp(clock['timestamp'],timezone.utc)
    monkeypatch.setattr('lib.etf.spy_reconcile.datetime',Clock)
    with pytest.raises(ValueError,match='closing grace'):extract_chart(chart(),'CPRT','2026-09-23','https://example.test')
    clock['timestamp']=close+901
    assert extract_chart(chart(),'CPRT','2026-09-23','https://example.test')['close']=='28.865'


def test_current_report_renderer_uses_reconciliation():
    from tests.test_daily_spy import report
    from publishing.private_spy import render
    r=report();r['reconciliation']=calc(bridge_inputs())
    r['valuation_marks']={};r['reconciliation']['positions'][0]['source_field']='Yahoo'
    html=render(r)
    assert 'Matched to published NAV' in html
    assert 'Net-assets difference' in html
    assert 'Priced assets + reported cash / share' not in html


def test_half_cent_chart_rounding_requires_same_date_identified_primary_mark():
    from lib.etf.spy_reconcile import PEER_HOLDINGS
    payload=chart('27.855',symbol='CSGP')
    payload['chart']['result'][0]['indicators']['quote'][0]['close']=[struct.unpack('f',struct.pack('f',27.86))[0]]
    mark=dict(symbol='CSGP',date='2026-09-23',currency='USD',price='27.855',identifier='22160N109',source_url=PEER_HOLDINGS,source_sha256='a'*64)
    confirmed=extract_chart(payload,'CSGP','2026-09-23','https://example.test',mark)
    assert D(confirmed['close'])==D('27.855') and 'corroborated' in confirmed['precision_note']
    for field,value in [('date','2026-09-22'),('price','27.86'),('symbol','ALGN'),('currency','EUR')]:
        with pytest.raises(ValueError,match='disagree'):
            extract_chart(payload,'CSGP','2026-09-23','https://example.test',dict(mark,**{field:value}))
    payload['chart']['result'][0]['indicators']['quote'][0]['close']=[28.86]
    with pytest.raises(ValueError,match='disagree'):
        extract_chart(payload,'CSGP','2026-09-23','https://example.test',mark)


def test_corroborated_quote_cache_revalidates_both_raw_sources(tmp_path):
    from io import BytesIO
    from openpyxl import Workbook
    from lib.etf.spy_reconcile import corroborate_peer_closes
    workbook=Workbook();ws=workbook.active
    for row in [('Fund','SPY5'),('ISIN','IE00B6YX5C33'),('Unused',''),('Holdings As Of:','23-Sep-2026'),('Unused',''),
                ('ISIN','Currency','Local Price'),('US22160N1090','USD',27.855)]:ws.append(row)
    buffer=BytesIO();workbook.save(buffer);peer=buffer.getvalue()
    payload=chart('27.855',symbol='CSGP');payload['chart']['result'][0]['indicators']['quote'][0]['close']=[struct.unpack('f',struct.pack('f',27.86))[0]]
    run=tmp_path/'first';(run/'quote_sources').mkdir(parents=True)
    (run/'quote_sources/CSGP-1d.json').write_text(json.dumps(payload))
    quotes={'CSGP':dict(error='Daily bar and same-session metadata disagree')}
    marks=corroborate_peer_closes(quotes,peer,[dict(yahoo_symbol='CSGP',identifier='22160N109')],'2026-09-23',run,tmp_path)
    assert marks['CSGP']['price']=='27.855'
    cached=quote_all(['CSGP'],'2026-09-23',tmp_path/'second',tmp_path)
    assert cached['CSGP']['close']=='27.855' and cached['CSGP']['closing_price_corroboration']==marks['CSGP']
    path=tmp_path/'quote_archive/2026-09-23/CSGP-peer.xlsx';path.write_bytes(peer+b' ')
    with pytest.raises(ValueError,match='corroborating price evidence hash mismatch'):
        quote_all(['CSGP'],'2026-09-23',tmp_path/'third',tmp_path)
