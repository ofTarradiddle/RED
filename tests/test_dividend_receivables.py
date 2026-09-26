from copy import deepcopy
from decimal import Decimal as D
import pytest

from lib.etf.dividend_receivables import build, replay, event_id, resolve_rate


def setup_case():
    schedule=dict(symbol='ABC',ex_date='2026-09-23',payable_date='2026-10-01',per_share='.5',currency='USD',estimated=False,
                  source='Nasdaq',source_url='https://example.test/dividend',amount_basis='event_date_share_units',declaration_status='Declared')
    report=dict(as_of='2026-09-23',positions=[dict(yahoo_symbol='ABC',security_type='equity',identifier='ID',quantity='100')],
                official=dict(shares_outstanding='10'),official_history=[dict(date='2026-09-22',shares_outstanding='10')],dividend_calendar=[schedule])
    history={'ABC':dict(symbol='ABC',start='2026-03-01',through='2026-09-24',error=None,actions=[dict(type='dividend',date='2026-09-23',amount='.5')],evidence=dict(url='https://example.test/actions'))}
    snapshot={'2026-09-22':dict(positions={'ID':dict(quantity='100')},source='Dated issuer file',sha256='a'*64)}
    return report,history,snapshot


def lot():
    return dict(id='D1',symbol='ABC',security_id='ID',ex_date='2026-09-23',payable_date='2026-09-24',currency='USD',
                eligible_quantity='100',per_share='1',source='Verified pre-ex position and declaration')


def test_scheduled_date_does_not_confirm_cash_and_late_partial_payment():
    r=replay([lot()],[],'2026-09-25')
    assert D(r['receivable_without_assumed_receipts'])==100
    assert D(r['expected_receivable'])==0 and D(r['modeled_receipts'])==100
    assert r['lots'][0]['overdue_unconfirmed']
    receipt=dict(id='C1',action_id='D1',date='2026-09-25',amount='40',currency='USD',kind='confirmed',source='Custodian receipt ref123')
    r=replay([lot()],[receipt],'2026-09-25')
    assert D(r['receivable_without_assumed_receipts'])==60 and D(r['confirmed_receipts'])==40
    payment=next(e for e in r['journal'] if e['type']=='confirmed_payment')
    assert payment['postings']=={'cash':'40','dividend_receivable':'-40'}
    assert all(sum(D(v) for v in e['postings'].values())==0 for e in r['journal'])


def test_duplicates_excess_payment_and_unknown_receipts_reject():
    with pytest.raises(ValueError,match='Duplicate economic'):replay([lot(),lot()],[],'2026-09-25')
    receipt=dict(id='C1',action_id='D1',date='2026-09-25',amount='101',currency='USD',kind='confirmed',source='Bank')
    with pytest.raises(ValueError,match='Invalid receipt'):replay([lot()],[receipt],'2026-09-25')
    receipt['amount']='20'
    with pytest.raises(ValueError,match='Duplicate cash'):replay([lot()],[receipt,receipt],'2026-09-25')
    receipt['action_id']='UNKNOWN'
    with pytest.raises(ValueError,match='unknown dividend'):replay([lot()],[receipt],'2026-09-25')


def test_withholding_and_recoverable_tax_are_separate_assets():
    item=lot();item.update(withholding_amount='15',recoverable_tax='5')
    result=replay([item],[],'2026-09-23')
    assert D(result['expected_receivable'])==85
    assert result['journal'][0]['postings']==dict(dividend_receivable='85.00',foreign_tax_receivable='5',withholding_expense='10',dividend_income='-100.00')


def test_no_reported_nav_or_receivable_inputs_drive_gross_amount():
    report,history,snapshot=setup_case();a=build(report,history,snapshot)
    report['official'].update(net_assets='999999999999',reported_dividend_receivable='888888888')
    report['net_cash']='123456789'
    b=build(report,history,snapshot)
    assert a['expected_gross_receivable']==b['expected_gross_receivable']=='50.00'
    assert a['outstanding_source_dated_count']==1 and a['confirmed_total_receivable'] is None


def test_same_ex_day_split_normalizes_pre_ex_and_estimated_quantities():
    report,history,snapshot=setup_case()
    history['ABC']['actions'].append(dict(type='split',date='2026-09-23',amount='2'))
    report['positions'][0]['quantity']='200'
    assert build(report,history,snapshot)['expected_gross_receivable']=='100.00'
    assert build(report,history,{})['expected_gross_receivable']=='100.00'


def test_frozen_entitlement_survives_later_share_changes_and_removal():
    report,history,snapshot=setup_case();initial=build(report,history,{})
    report['positions'][0]['quantity']='900';report['official']['shares_outstanding']='12'
    replayed=build(report,history,{},inputs={'frozen_entitlements':initial['entitlement_archive']})
    assert replayed['expected_gross_receivable']=='50.00'
    report['positions']=[];report['dividend_calendar']=[]
    removed=build(report,history,{},inputs={'frozen_entitlements':initial['entitlement_archive']})
    assert removed['expected_gross_receivable']=='50.00'


def test_conflict_quarantines_new_calculation_but_preserves_prior_archive():
    report,history,snapshot=setup_case();initial=build(report,history,snapshot)
    history['ABC']['actions'][0]['amount']='1'
    revised=build(report,history,snapshot,inputs={'frozen_entitlements':initial['entitlement_archive']})
    assert revised['rows'][0]['gross'] is None
    assert revised['expected_gross_receivable']=='0'
    assert revised['entitlement_archive'][0]['gross']=='50.00'
    assert len(revised['prior_entitlements_under_review'])==1


def test_outage_retains_frozen_economics_despite_display_changes():
    report,history,snapshot=setup_case();initial=build(report,history,snapshot)
    history['ABC']['error']='Temporary outage';report['dividend_calendar'][0]['current_position_quantity']='900'
    revised=build(report,history,snapshot,inputs={'frozen_entitlements':initial['entitlement_archive']})
    assert revised['expected_gross_receivable']=='50.00'


def test_frozen_tax_and_unknown_opening_completeness():
    report,history,snapshot=setup_case();key=event_id('ID','2026-09-23')
    item=dict(id=key,security_id='ID',ex_date='2026-09-23',eligible_quantity='100',withholding_amount='5',recoverable_tax='2',source='Documented entitlement')
    a=build(report,history,{},inputs={'entitlements':[item]})
    b=build(report,history,{},inputs={'frozen_entitlements':a['entitlement_archive']})
    assert b['modeled_book']['expected_receivable']=='45.00'
    assert b['modeled_book']['lots'][0]['recoverable_tax']=='2'
    assert not b['complete'] and b['confirmed_total_receivable'] is None


def test_primary_split_rate_correction_and_ex_date_conflict():
    report,history,_=setup_case();s=report['dividend_calendar'][0]
    s.update(symbol='APH',per_share='.25',source='DividendHistory.org')
    h=history['ABC'];h['actions'][0]['amount']='.125'
    primary=dict(per_share='.125',payable_date=s['payable_date'],primary_ex_date=s['ex_date'])
    assert resolve_rate(s,h,primary)[0]==D('.125')
    primary['primary_ex_date']='2026-09-22'
    assert resolve_rate(s,h,primary)[0] is None


def test_rule_derived_ex_date_requires_matching_record_and_no_exchange_exception():
    report,history,_=setup_case();s=report['dividend_calendar'][0]
    primary=dict(per_share='.5',payable_date=s['payable_date'],primary_ex_date='2026-09-22',record_date=s['ex_date'])
    primary['ex_date_resolution']=dict(ex_date=s['ex_date'],record_date=s['ex_date'],evidence=['archived exchange rule and exception report'],exchange_exception_symbols=[])
    assert resolve_rate(s,history['ABC'],primary)[0]==D('.5')
    primary['ex_date_resolution']['exchange_exception_symbols']=['ABC']
    assert resolve_rate(s,history['ABC'],primary)[0] is None


def test_missing_rate_or_payment_evidence_never_implies_zero_dividend():
    report,history,snapshot=setup_case();history['ABC']['actions'].append(dict(type='dividend',date='2026-08-20',amount='.5'))
    r=build(report,history,snapshot)
    assert r['missing_payment_schedules'][0]['ex_date']=='2026-08-20'
    report['dividend_calendar'][0]['estimated']=True
    r=build(report,history,snapshot)
    assert r['calculated_outstanding_count']==0 and len(r['unresolved_outstanding'])==1


def test_opening_dividend_items_can_settle_without_income_again():
    from lib.etf.ledger import replay as ledger
    opening=dict(date='2026-09-23',source='Opening records',shares=100,positions=[],
        balances=dict(cash=1000,dividend_receivable=100,trade_receivable=0,trade_payable=0,fee_payable=0,distribution_payable=0),
        dividend_items=[dict(id='OPEN-DIV',symbol='ABC',ex_date='2026-09-22',payable_date='2026-09-24',gross=100,remaining=100,currency='USD',source='Opening dividend detail')])
    events=[dict(id='PAY',type='dividend_payment',date='2026-09-24',action_id='OPEN-DIV',amount=100,source='Confirmed payment')]
    result=ledger(opening,events,'2026-09-24',{})
    assert result['balances']['cash']==1100 and result['balances']['dividend_receivable']==0
    assert result['balances']['income']==0
    opening['dividend_items'][0]['remaining']=99
    with pytest.raises(ValueError,match='do not reconcile'):ledger(opening,events,'2026-09-24',{})


def test_blotter_derives_entitlement_before_ex_date_trades():
    from lib.etf.dividend_receivables import entitlements_from_blotter
    report,_,_=setup_case()
    accounting=dict(opening=dict(date='2026-09-21',source='Documented opening book',positions=[dict(symbol='ABC',quantity='100')]),cutoff='2026-09-24',events=[
        dict(id='BUY-BEFORE',date='2026-09-22',type='trade',symbol='ABC',side='buy',quantity='20',source='Execution1'),
        dict(id='SPLIT',date='2026-09-23',type='split',symbol='ABC',ratio='2',source='Confirmed split'),
        dict(id='BUY-EX',date='2026-09-23',type='trade',symbol='ABC',side='buy',quantity='50',source='Execution2'),
        dict(id='SELL-AFTER',date='2026-09-24',type='trade',symbol='ABC',side='sell',quantity='290',source='Execution3')])
    entitlements=entitlements_from_blotter(accounting,report['dividend_calendar'],report['positions'])
    assert entitlements[0]['eligible_quantity']=='240'
