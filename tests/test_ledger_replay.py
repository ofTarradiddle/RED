from copy import deepcopy
from decimal import Decimal as D
import pytest

from lib.etf.ledger import replay, walkthrough


def opening():
    return dict(date='2026-09-14',source='Test opening records',shares=100,
                positions=[dict(symbol='ABC',quantity=10,cost=1000,carrying_value=1000)],
                balances=dict(cash=1000,dividend_receivable=0,trade_receivable=0,
                              trade_payable=0,fee_payable=0,distribution_payable=0))


def event(kind, id='E1', day='2026-09-15', **kwargs):
    return dict(id=id,date=day,type=kind,source='Test source',**kwargs)


def prices(day, price):
    return {'ABC':dict(date=day,price=price,basis='as_of_share_units')}


def test_trade_settlement_preserves_nav_and_replay_is_idempotent():
    start=opening();buy=event('trade',symbol='ABC',side='buy',quantity=5,price=100,settlement_date='2026-09-16')
    settle=event('settlement','S','2026-09-16',trade_id='E1',amount=500)
    before=replay(start,[buy],'2026-09-15',prices('2026-09-15',100))
    after=replay(start,[buy,settle],'2026-09-16',prices('2026-09-16',100))
    assert before['nav']==after['nav']==20
    assert after['balances']['trade_payable']==0 and after['balances']['cash']==500
    assert after==replay(start,[buy,settle],'2026-09-16',prices('2026-09-16',100))
    assert start==opening()
    with pytest.raises(ValueError,match='Duplicate'):replay(start,[buy,buy],'2026-09-15')


def test_ex_date_entitlement_price_drop_and_payment():
    div=event('dividend',symbol='ABC',per_share=2,currency='USD',entitlement_rule='ordinary_ex_date',payable_date='2026-09-17')
    buy=event('trade','BUY',symbol='ABC',side='buy',quantity=5,price=98,settlement_date='2026-09-16')
    on_ex=replay(opening(),[buy,div],'2026-09-15',prices('2026-09-15',98))
    assert on_ex['nav']==20 and D(on_ex['dividends']['E1']['gross'])==20
    assert on_ex['dividends']['E1']['eligible_quantity']=='10'
    pay=event('dividend_payment','PAY','2026-09-17',action_id='E1',amount=20)
    paid=replay(opening(),[buy,div,pay],'2026-09-17',prices('2026-09-17',98))
    assert paid['nav']==20 and paid['balances']['dividend_receivable']==0
    assert paid['balances']['income']==-20


def test_split_preserves_cost_and_nav_and_fee_payment_does_not_recharge():
    split=event('split',symbol='ABC',ratio=2)
    fee=event('fee','F',base=2000,annual_rate='.0045',fee_key='adviser',from_date='2026-09-15',through_date='2026-09-15')
    state=replay(opening(),[split,fee],'2026-09-15',prices('2026-09-15',50))
    assert state['positions']['ABC']['cost']==1000 and state['positions']['ABC']['quantity']==20
    charge=-state['balances']['fee_payable']; assert charge==D('.02')
    pay=event('fee_payment','P','2026-09-16',amount=charge)
    paid=replay(opening(),[split,fee,pay],'2026-09-16',prices('2026-09-16',50))
    assert paid['nav']==state['nav'] and paid['balances']['fee_payable']==0
    with pytest.raises(ValueError,match='already accrued'):
        replay(opening(),[fee,dict(fee,id='F2')],'2026-09-15')


def test_creation_at_nav_and_fund_distribution():
    create=event('creation',shares=10,cash=200)
    state=replay(opening(),[create],'2026-09-15',prices('2026-09-15',100))
    assert state['nav']==20 and state['shares']==110
    dist=event('fund_distribution','DIST','2026-09-16',per_share=1,eligible_shares=110,payable_date='2026-09-17')
    pay=event('fund_distribution_payment','PAY','2026-09-17',action_id='DIST',amount=110)
    declared=replay(opening(),[create,dist],'2026-09-16',prices('2026-09-16',100))
    paid=replay(opening(),[create,dist,pay],'2026-09-17',prices('2026-09-17',100))
    assert declared['nav']==paid['nav']==19


def test_oversell_unknown_actions_missing_balances_and_bad_prices_reject():
    start=opening(); saved=deepcopy(start)
    with pytest.raises(ValueError,match='oversell'):
        replay(start,[event('trade',symbol='ABC',side='sell',quantity=11,price=100,settlement_date='2026-09-16')],'2026-09-15')
    assert start==saved
    with pytest.raises(ValueError,match='Unsupported'):
        replay(start,[event('spinoff',symbol='ABC')],'2026-09-15')
    del start['balances']['fee_payable']
    with pytest.raises(ValueError,match='explicit'):replay(start,[],'2026-09-15')
    with pytest.raises(ValueError,match='basis'):
        replay(opening(),[],'2026-09-15',prices('2026-09-14',100))


def test_unconfirmed_payment_rejects_and_weekends_accrue():
    div=event('dividend',symbol='ABC',per_share=2,currency='USD',entitlement_rule='ordinary_ex_date',payable_date=None)
    pay=event('dividend_payment','P','2026-09-16',action_id='E1',amount=20)
    with pytest.raises(ValueError,match='Unverified'):replay(opening(),[div,pay],'2026-09-16')
    fee=event('fee',day='2026-09-21',base=2000,annual_rate='.0045',fee_key='adviser',from_date='2026-09-19',through_date='2026-09-21')
    s=replay(opening(),[fee],'2026-09-21');assert s['balances']['fee_payable']==D('-.07')


def test_walkthrough_balances_every_journal_and_closing_nav():
    state=walkthrough()
    assert state['nav']==D('19.999')
    assert all(sum(D(p['amount']) for p in e['postings'])==0 for e in state['journal'])


def test_opening_appreciation_is_not_current_period_income():
    start=opening();start['positions'][0]['carrying_value']=1100
    state=replay(start,[],'2026-09-15',prices('2026-09-15',110))
    assert state['nav']==21 and state['balances']['unrealized_gain']==0
