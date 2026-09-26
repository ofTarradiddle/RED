from datetime import datetime,timezone
from lib.etf.dividend_calendar import parse_nasdaq, parse_yahoo_schedule, parse_dividendhistory, review_calendar


def test_yahoo_date_fields_use_utc_and_do_not_pair_old_amount():
    epoch=lambda day:int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp())
    payload={'quoteSummary':{'result':[{'calendarEvents':{'exDividendDate':epoch('2026-10-06'),'dividendDate':epoch('2026-10-31')},'defaultKeyStatistics':{'lastDividendDate':epoch('2026-07-06'),'lastDividendValue':1.50}}]}}
    rows,_=parse_yahoo_schedule(payload,'JPM','https://example.test')
    assert rows[0]['ex_date']=='2026-10-06' and rows[0]['payable_date']=='2026-10-31'
    assert rows[0]['per_share'] is None
    payload['quoteSummary']['result'][0]['defaultKeyStatistics'].update(lastDividendDate=epoch('2026-10-06'),lastDividendValue=1.65)
    assert parse_yahoo_schedule(payload,'JPM','https://example.test')[0][0]['per_share']=='1.65'


def test_nasdaq_special_date_does_not_erase_other_valid_records():
    regular=dict(exOrEffDate='09/23/2026',paymentDate='10/14/2026',amount='$0.33',declarationDate='08/26/2026',recordDate='09/23/2026',currency='USD',type='Cash')
    unusual={**regular,'paymentDate':'09/01/2026'}
    rows,issue=parse_nasdaq({'data':{'dividends':{'rows':[regular,unusual]}}},'LRCX','https://example.test')
    assert len(rows)==1 and 'excluded' in issue
    assert rows[0]['declaration_status']=='Declared'


def test_estimates_and_historical_entitlement_not_booked():
    html='<table id="dividend-table"><thead><tr><th>Ex-Dividend Date</th><th>Payout Date</th><th>Cash Amount</th><th>Status</th></tr></thead><tbody><tr class="unconfirmed-div"><td>2026-10-06</td><td>2026-10-31</td><td>$1.65</td><td>Estimated</td></tr></tbody></table>'
    rows,_=parse_dividendhistory(html,'JPM','https://example.test')
    calendar={'securities':{'JPM':{'records':rows}}};positions=[dict(yahoo_symbol='JPM',quantity='100')]
    reviewed=review_calendar(calendar,{},positions,'2026-09-23')[0]
    assert reviewed['cashflow_at_current_quantity']=='165.00'
    assert reviewed['booked_receivable'] is None and 'not accrued' in reviewed['status']
    historical=review_calendar(calendar,{},positions,'2026-11-01')[0]
    assert historical['cashflow_at_current_quantity'] is None


def test_no_false_historical_split_basis_corroboration():
    row=dict(symbol='AAPL',ex_date='2020-08-07',payable_date='2020-08-13',per_share='.82',amount_basis='event_date_share_units',declaration_status='Declared',estimated=False)
    quote={'AAPL':{'actions':[dict(type='dividend',date='2020-08-07',amount='.205'),dict(type='split',date='2020-08-31',amount='4')]}}
    out=review_calendar({'securities':{'AAPL':{'records':[row]}}},quote,[dict(yahoo_symbol='AAPL',quantity='400')],'2020-09-01')[0]
    assert out['crosscheck']=='Not independently corroborated'
    assert out['cashflow_at_current_quantity'] is None and out['booked_receivable'] is None
