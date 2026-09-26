from copy import deepcopy
from datetime import date
from decimal import Decimal as D
import json
from pathlib import Path
import pytest

from lib.etf.shadow import compare, value_shadow
from lib.etf.adapters import FileBasedDataSourceAdapter
from lib.etf.functions.core.settlement_reconciliation import SettlementReconciliationManager
from lib.etf.functions.operations.rule_6c11_compliance import Rule6c11Compliance


@pytest.fixture
def records():
    snapshot=dict(fund_id='example',as_of='2026-09-18',base_currency='USD',positions_source='independent position ledger',balances_source='independent cash/accrual ledger',corporate_actions_reviewed=True,shares_outstanding='100',
                  positions=[dict(security_id='ABC',symbol='ABC',currency='USD',security_type='equity',quantity='10')],
                  balances=dict(cash='100',dividends_receivable='2',trade_receivables='3',other_receivables='0',accrued_fees='4',trade_payables='5',other_liabilities='1'))
    quotes=dict(as_of=snapshot['as_of'],source='offline fixture',fetched_at='2026-09-18T22:00:00Z',prices={'ABC':dict(close='20',date=snapshot['as_of'],currency='USD',fx_to_usd='1',price_basis='as_of_share_units')})
    provider=deepcopy(snapshot);provider.update(provider_name='demo administrator',official_nav='2.95',official_nav_decimals=2,net_assets='295')
    provider['positions'][0].update(price='20',fx_to_usd='1')
    return snapshot,quotes,provider


def test_full_balance_equation_and_absent_provider(records):
    s,q,p=records
    report=compare(s,q)
    assert report['shadow']['assets']==D('305')
    assert report['shadow']['liabilities']==D('10')
    assert report['shadow']['nav']==D('2.95')
    assert report['status']=='unavailable'
    assert report['difference_bps'] is None


def test_independent_match_and_tolerance(records):
    s,q,p=records
    assert compare(s,q,p)['status']=='within_tolerance'
    q['prices']['ABC']['close']='20.1'
    r=compare(s,q,p)
    assert r['status']=='difference'
    assert r['breaks'][0]['price']==D('1')
    assert abs(r['attribution_residual'])<D('1e-25')


def test_position_cash_accrual_and_shares_break_bridge(records):
    s,q,p=records
    s['positions'][0]['quantity']='12';s['shares_outstanding']='110'
    s['balances']['cash']='110';s['balances']['accrued_fees']='8'
    r=compare(s,q,p)
    assert r['breaks'][0]['quantity']==40
    assert r['balance_breaks']['cash']==10
    assert r['balance_breaks']['accrued_fees']==-4
    assert r['nav_attribution']['share_count_effect']<0
    assert abs(r['attribution_residual'])<D('1e-25')


def test_union_of_positions_and_provider_inconsistency(records):
    s,q,p=records
    p['positions'][0]['security_id']='OTHER'
    p['positions'][0]['symbol']='OTHER'
    r=compare(s,q,p)
    assert {b['position_status'] for b in r['breaks']}=={'shadow_only','provider_only'}
    p['net_assets']='400'
    assert compare(s,q,p)['status']=='provider_data_inconsistent'


@pytest.mark.parametrize('precision,cash,net,nav',[(2,'100.4','295.4','2.95'),(4,'100.004','295.004','2.9500')])
def test_reported_nav_rounding_is_not_a_false_break(records,precision,cash,net,nav):
    s,q,p=records
    s['balances']['cash']=p['balances']['cash']=cash
    p.update(net_assets=net,official_nav=nav,official_nav_decimals=precision)
    r=compare(s,q,p)
    assert r['status']=='within_tolerance'
    assert r['unrounded_difference_bps']==0
    assert r['nav_difference']!=0
    assert abs(r['attribution_residual'])<D('1e-25')
    p['official_nav']='2.94'
    assert compare(s,q,p)['status']=='provider_data_inconsistent'


def test_provider_nav_precision_is_required(records):
    s,q,p=records
    del p['official_nav_decimals']
    with pytest.raises(ValueError,match='reporting precision'):compare(s,q,p)


def test_same_rounded_nav_does_not_hide_an_economic_break(records):
    s,q,p=records
    s['balances']['cash']='100.4'
    p['balances']['cash']='99.6'
    p['net_assets']='294.6'
    r=compare(s,q,p)
    assert r['status']=='difference'
    assert r['unrounded_nav_difference']==D('.008')
    assert r['unrounded_difference_bps']>27


@pytest.mark.parametrize('case',['missing_price','date','currency','split','zero_shares','missing_cash','actions','nan','duplicate','provider_date'])
def test_fail_closed(records,case):
    s,q,p=records
    if case=='missing_price':q['prices']={}
    if case=='date':q['prices']['ABC']['date']='2026-09-17'
    if case=='currency':q['prices']['ABC']['currency']='CAD'
    if case=='split':q['prices']['ABC']['price_basis']='adjusted'
    if case=='zero_shares':s['shares_outstanding']='0'
    if case=='missing_cash':del s['balances']['cash']
    if case=='actions':s['corporate_actions_reviewed']=False
    if case=='nan':q['prices']['ABC']['close']='NaN'
    if case=='duplicate':s['positions'].append(deepcopy(s['positions'][0]))
    if case=='provider_date':p['as_of']='2026-09-17'
    with pytest.raises(ValueError):compare(s,q,p)


def test_split_value_preservation_and_dividend_payment(records):
    s,q,p=records
    before=value_shadow(s,q)['net_assets']
    s['positions'][0]['quantity']='20';q['prices']['ABC']['close']='10'
    assert value_shadow(s,q)['net_assets']==before
    s['balances']['cash']='102';s['balances']['dividends_receivable']='0'
    assert value_shadow(s,q)['net_assets']==before


def test_trade_settlement_balance_transfer_preserves_nav(records):
    s,q,p=records
    before=value_shadow(s,q)['net_assets']
    s['balances']['cash']='95';s['balances']['trade_payables']='0'
    assert value_shadow(s,q)['net_assets']==before


def test_missing_files_are_not_zero_balances(tmp_path):
    adapter=FileBasedDataSourceAdapter(str(tmp_path))
    with pytest.raises(FileNotFoundError):adapter.get_portfolio_holdings(date(2026,9,18))
    (tmp_path/'holdings_2026-09-18.json').write_text('[]')
    assert adapter.get_portfolio_holdings(date(2026,9,18))==[]


def test_settlement_calendar_and_missing_evidence(tmp_path):
    calendar=lambda d:d.weekday()<5 and d!=date(2026,9,7)
    manager=SettlementReconciliationManager(object(),str(tmp_path),is_settlement_day=calendar)
    assert manager.calculate_settlement_date(date(2026,9,4))==date(2026,9,8)
    assert manager.reconcile_t1_settlement(date(2026,9,8)).status=='failed'
    with pytest.raises(ValueError):SettlementReconciliationManager(object(),str(tmp_path/'other')).calculate_settlement_date(date(2026,9,4))


def test_numeric_basket_checks_do_not_certify_law(tmp_path):
    check=Rule6c11Compliance(str(tmp_path))
    standard=[dict(cusip='ABC',quantity=10,price=20)]
    custom=[dict(cusip='XYZ',quantity=20,price=10)]
    pending=check.validate_custom_basket(standard,custom,D('200'))
    assert not pending.passed
    assert pending.validation_details['legal_compliance']=='not_determined'
    assert not any('not in PCF' in e for e in pending.errors)
    review=dict(policy_version='demo-1',designated_reviewer='demo reviewer',reviewed_at='2026-09-18T20:00:00Z',purpose='documented example',ap_id='demo-ap',cash_balancing_amount='0',approved_under_adopted_policy=True)
    assert check.validate_custom_basket(standard,custom,D('200'),review=review).passed
