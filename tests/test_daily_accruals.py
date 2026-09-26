from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
import json
from pathlib import Path

import pytest

from lib.etf.daily_accruals import daily_replay, policy_for
from lib.etf.operating_book import seed_model, ingest
from tests.test_ledger_replay import opening, event, prices


def run(events=(), cutoff='2026-09-15', history=None, policy=None, start=None):
    return daily_replay(start or opening(), list(events), cutoff,
        history or {'2026-09-15': prices('2026-09-15',100)}, policy or {})


def test_daily_fee_uses_independent_post_fee_net_assets_and_balances():
    book=run();row=book['daily'][0]
    exact=D(2000)*D('.0045')/(D(365)+D('.0045'))
    assert D(row['exact_fee'])==exact
    assert D(row['fee_accrual'])==D('.02')
    assert D(row['net_assets'])==D('1999.98')
    assert all(sum(D(p['amount']) for p in e['postings'])==0 for e in book['state']['journal'])
    assert run()==book


def test_ex_date_once_then_receivable_until_payment_and_no_second_income():
    div=event('dividend',symbol='ABC',per_share=2,currency='USD',entitlement_rule='ordinary_ex_date',payable_date='2026-09-17')
    history={day:prices(day,98) for day in ['2026-09-15','2026-09-16','2026-09-17']}
    book=run([div], '2026-09-17',history,dict(annual_rate='0'))
    assert [D(r['dividend_income']) for r in book['daily']]==[20,0,0]
    assert [D(r['dividend_receivable']) for r in book['daily']]==[20,20,0]
    assert [D(r['scheduled_dividend_cash']) for r in book['daily']]==[0,0,20]
    assert {D(r['nav']) for r in book['daily']}=={20}
    confirmed=run([div],'2026-09-17',history,dict(annual_rate='0',payment_mode='confirmed'))
    assert D(confirmed['daily'][-1]['dividend_receivable'])==20
    assert D(confirmed['daily'][-1]['scheduled_dividend_cash'])==0


def test_partial_actual_receipt_replaces_modeled_receipt_and_retains_remainder():
    div=event('dividend',symbol='ABC',per_share=2,currency='USD',entitlement_rule='ordinary_ex_date',payable_date='2026-09-16')
    pay=event('dividend_payment','P','2026-09-17',action_id='E1',amount=5)
    history={day:prices(day,98) for day in ['2026-09-15','2026-09-16','2026-09-17']}
    result=run([div,pay],'2026-09-17',history)
    assert D(result['daily'][-1]['dividend_receivable'])==15
    assert sum(D(r['scheduled_dividend_cash']) for r in result['daily'])==0
    assert D(result['daily'][-1]['confirmed_dividend_cash'])==5


def test_weekends_leap_year_rate_change_and_precision_carry():
    start=opening();start['date']='2028-02-25'
    policy=dict(day_count='ACT/ACT',rate_changes=[dict(effective_date='2028-02-28',annual_rate='.009',source='Test fee amendment')])
    history={d:prices(d,100) for d in ['2028-02-25','2028-02-28','2028-02-29']}
    book=run([], '2028-02-29',history,policy,start)
    assert len(book['daily'])==4
    assert [r['carried_prices'] for r in book['daily']]==[True,True,False,False]
    assert {r['year_days'] for r in book['daily']}=={366}
    assert [D(r['annual_rate']) for r in book['daily']]==[D('.0045'),D('.0045'),D('.009'),D('.009')]
    exact=sum(D(r['exact_fee']) for r in book['daily'])
    assert sum(D(r['fee_accrual']) for r in book['daily'])==exact.quantize(D('.01'),rounding=ROUND_HALF_UP)
    assert policy_for(dict(day_count='ACT/ACT'),'2029-01-01')[2]==365
    assert policy_for({},'2028-02-29')[2]==365


def test_fee_payment_clears_payable_without_double_expensing():
    history={day:prices(day,100) for day in ['2026-09-15','2026-09-16']}
    policy=dict(rate_changes=[dict(effective_date='2026-09-16',annual_rate='0',source='Zero fee test')])
    book=run([event('fee_payment','F','2026-09-16',amount='.02')],'2026-09-16',history,policy)
    assert D(book['daily'][-1]['fee_payable'])==0
    assert D(book['daily'][-1]['fee_accrual'])==0
    assert D(book['daily'][-1]['net_assets'])==D('1999.98')
    assert book['state']['balances']['expense']==D('.02')


def test_split_precedes_dividend_and_ex_date_purchase_gets_no_entitlement():
    events=[event('split','S',symbol='ABC',ratio=2),
        event('dividend','D',symbol='ABC',per_share=1,currency='USD',entitlement_rule='ordinary_ex_date',payable_date=None),
        event('trade','T',symbol='ABC',side='buy',quantity=5,price=49,settlement_date='2026-09-16')]
    book=run(events,history={'2026-09-15':prices('2026-09-15',49)},policy=dict(annual_rate='0'))
    assert book['state']['dividends']['D']['eligible_quantity']=='20'
    assert D(book['daily'][0]['dividend_receivable'])==20
    assert D(book['daily'][0]['nav'])==20


def test_session_gaps_wrong_price_dates_extra_fees_and_duplicates_reject():
    with pytest.raises(ValueError,match='Missing closing prices'):
        run(cutoff='2026-09-16')
    with pytest.raises(ValueError,match='observation date'):
        run(history={'2026-09-15':prices('2026-09-14',100)})
    with pytest.raises(ValueError,match='Single unitary'):
        run([event('fee')])
    e=event('split',symbol='ABC',ratio=2)
    with pytest.raises(ValueError,match='Duplicate'):
        run([e,e])


def test_price_correction_restates_later_fee_and_does_not_mutate_inputs():
    history={d:prices(d,100) for d in ['2026-09-15','2026-09-16']};saved=deepcopy(history)
    before=run(cutoff='2026-09-16',history=history)
    assert saved==history
    history['2026-09-15']=prices('2026-09-15',200)
    after=run(cutoff='2026-09-16',history=history)
    assert before['daily'][0]['exact_fee']!=after['daily'][0]['exact_fee']
    assert before['daily'][1]['fee_base']!=after['daily'][1]['fee_base']


def report_fixture():
    lot=dict(id='ID:2026-09-10:USD:cash',symbol='ABC',ex_date='2026-09-10',payable_date='2026-10-01',gross='20',source='Public test')
    return dict(as_of='2026-09-15',positions=[dict(identifier='ID',ticker='ABC',yahoo_symbol='ABC',security_type='equity',quantity='10',price='100')],
        reconciliation=dict(holdings_as_of='2026-09-14'),official=dict(nav='999',shares_outstanding='100'),
        official_history=[dict(date='2026-09-14',shares_outstanding='100',net_assets='999999',nav='999')],
        legacy_holdings_cash_diagnostic=dict(reported_cash='1000'),
        manifest=dict(files=dict(valuation_holdings=dict(sha256='test'))),
        dividend_receivables=dict(modeled_book=dict(lots=[lot]),rows=[],input_evidence=dict(action_history_sha256='test')))


def test_model_ignores_reported_nav_netcash_and_statement_liabilities():
    report=report_fixture();first=seed_model(report)
    report['official']['nav']='1';report['official']['net_assets']='123'
    report['reconciliation']['net_cash']={'amount':'9999999'}
    report['historical']={'statement':{'balances':{'fees':'99999'}}}
    report['official_history'][0]['net_assets']='0';report['official_history'][0]['nav']='0'
    assert seed_model(report)==first


def test_refresh_preserves_opening_cash_holdings_units_and_handles_unscheduled_dividend():
    report=report_fixture();model=seed_model(report);before=deepcopy(model['opening'])
    report['legacy_holdings_cash_diagnostic']['reported_cash']='9999';report['positions'][0]['quantity']='500'
    history={'ABC':dict(actions=[dict(date='2026-09-15',type='dividend',amount='2')],error=None)}
    newer,issues=ingest(model,report,history)
    assert not issues and newer['opening']==before and model['events']==[]
    assert newer['events'][0]['per_share']=='2' and newer['events'][0]['payable_date'] is None
    book=daily_replay(newer['opening'],newer['events'],'2026-09-15',newer['price_history'],newer['policy'])
    assert D(book['daily'][0]['dividend_income'])==20
    assert D(book['daily'][0]['shares'])==100


def test_partial_opening_receivable_does_not_create_new_income():
    start=opening();start['balances']['dividend_receivable']=20
    start['dividend_items']=[dict(id='OLD',symbol='ABC',ex_date='2026-09-10',payable_date='2026-09-15',currency='USD',source='Opening claim',gross=20,remaining=20)]
    b=run(start=start)
    assert D(b['daily'][0]['dividend_income'])==0
    assert D(b['daily'][0]['scheduled_dividend_cash'])==20
    assert D(b['daily'][0]['dividend_receivable'])==0


def test_weekend_bootstrap_needs_a_real_opening_close():
    start=opening();start['date']='2026-09-18'
    history={'2026-09-21':prices('2026-09-21',100)}
    with pytest.raises(ValueError,match='No dated prices to carry'):
        run(cutoff='2026-09-21',history=history,start=start)
    history['2026-09-18']=prices('2026-09-18',100)
    book=run(cutoff='2026-09-21',history=history,start=start)
    assert [r['price_date'] for r in book['daily']]==['2026-09-18','2026-09-18','2026-09-21']
    assert len(book['daily'])==3


def test_unsupported_action_is_not_silently_dropped():
    report=report_fixture();model=seed_model(report)
    history={'ABC':dict(actions=[dict(date='2026-09-15',type='capital_gain',amount='2')],error=None)}
    _,issues=ingest(model,report,history)
    assert 'unsupported capital_gain' in issues[0]


def test_supplied_books_run_without_spy_valuation_or_action_inputs(tmp_path):
    from lib.etf.operating_book import update
    supplied=dict(fund_id='REDI',cutoff='2026-09-15',opening=opening(),events=[],
                  price_history={'2026-09-15':prices('2026-09-15',100)})
    (tmp_path/'daily-accounting-input.json').write_text(json.dumps(supplied))
    report=dict(as_of='2026-09-23')
    book=update(report,tmp_path,through='2026-09-15',progress=lambda *a,**k:None)
    assert book['status']=='Daily accruals calculated'
    assert book['policy']['payment_mode']=='confirmed'
    assert D(book['daily'][0]['fee_accrual'])==D('.02')
    assert not (tmp_path/'daily-book/public-model-inputs.json').exists()


def test_new_price_for_retained_security_is_used_even_after_it_leaves_spy():
    report=report_fixture();model=seed_model(report)
    report['positions']=[]
    report['operating_quotes']={'ABC':dict(close='99',date='2026-09-15',source_url='https://example.org/quote',source_field='close',error=None)}
    history={'ABC':dict(actions=[],error=None)}
    updated,issues=ingest(model,report,history)
    assert not issues and updated['price_history']['2026-09-15']['ABC']['price']=='99'


def test_private_page_primary_view_is_unitary_daily_book_and_excludes_statement_expenses():
    from publishing.private_spy import render
    from lib.etf.operating_book import encode
    book=json.loads(encode(run()))
    book.update(mode='Test supplied records',status='Daily accruals calculated')
    # Test the dedicated renderer independently of the legacy SPY source report.
    from publishing.accrual_view import render as render_accruals
    from publishing.private_spy import panel,table,cash,journals
    html=render_accruals(book,panel,table,cash,journals)
    assert '45 bps per year' in html and 'Unitary fee payable' in html
    assert 'Operating journal' in html and 'scheduled' in html
    page=render()
    assert 'unaudited' not in page and 'March 31 filed accounting' not in page


def test_same_day_fee_payment_can_settle_current_day_accrual():
    result=run([event('fee_payment','PAY',amount='.02')])
    row=result['daily'][0]
    assert D(row['fee_accrual'])==D('.02')
    assert D(row['fee_payment'])==D('.02') and D(row['fee_payable'])==0
    assert D(row['net_assets'])==D('1999.98')
    assert result['state']['balances']['expense']==D('.02')
