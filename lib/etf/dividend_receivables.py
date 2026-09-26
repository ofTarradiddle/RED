"""Independent dividend entitlements, receipts and an explicit estimation book.

No reported dividend-receivable balance, NAV residual or aggregate net cash is an
input to the entitlement calculation. Estimated quantities never become confirmed
holdings, and scheduled payments never become confirmed cash receipts.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path

from .dividend_sources import event_rate
from .spy_reconcile import session_details

D=Decimal
CENT=D('.01')


def number(value,positive=False):
    value=D(str(value))
    if not value.is_finite() or (value<=0 if positive else value<0):raise ValueError('Invalid nonnegative financial amount')
    return value


def event_id(security_id,ex_date):
    date.fromisoformat(ex_date)
    return f'{security_id}:{ex_date}:USD:cash'


def schedule_economics(row):
    return tuple(row.get(k) for k in ('symbol','ex_date','payable_date','currency','per_share','amount_basis','estimated'))


def entitlements_from_blotter(accounting,schedules,positions):
    """Derive ex-date share counts from supplied opening positions and executions.

    The stock-quantity replay does not invent trades from holdings changes.
    Unsupported in-kind/complex actions reject, so completeness is not implied.
    """
    opening=accounting['opening'];start=opening['date'];cutoff=accounting['cutoff']
    if date.fromisoformat(cutoff)<date.fromisoformat(start):raise ValueError('Blotter cutoff precedes opening positions')
    if not opening.get('source'):raise ValueError('Opening positions need evidence')
    quantities={};identities={p['yahoo_symbol']:p['identifier'] for p in positions if p.get('yahoo_symbol')}
    for p in opening['positions']:
        if p['symbol'] in quantities:raise ValueError('Duplicate opening position')
        quantities[p['symbol']]=number(p['quantity'])
        if p.get('security_id'):identities[p['symbol']]=p['security_id']
    timeline=[];seen=set()
    harmless={'settlement','dividend','dividend_payment','fee','fee_payment','fund_distribution','fund_distribution_payment'}
    for e in accounting['events']:
        if e['id'] in seen or not e.get('source'):raise ValueError('Duplicate blotter event or missing evidence')
        seen.add(e['id'])
        date.fromisoformat(e['date'])
        if not start<e['date']<=cutoff:continue
        kind=e['type']
        if kind in ('creation','redemption') and not e.get('basket'):continue
        if kind in harmless:continue
        if kind not in ('trade','split'):raise ValueError('Unsupported position-affecting action in entitlement blotter')
        timeline.append((e['date'],0 if kind=='split' else 2,e.get('sequence',0),e['id'],e))
    seen_actions=set()
    for s in schedules:
        key=(s['symbol'],s['ex_date'])
        if s.get('estimated') or not start<s['ex_date']<=cutoff or key in seen_actions:continue
        seen_actions.add(key)
        if s['symbol'] not in identities:raise ValueError('Historical stock needs a stable security identity')
        timeline.append((s['ex_date'],1,0,s['symbol'],dict(type='entitlement',schedule=s)))
    result=[]
    for _,_,_,_,e in sorted(timeline,key=lambda x:x[:4]):
        kind=e['type']
        if kind=='entitlement':
            s=e['schedule'];sid=identities[s['symbol']]
            result.append(dict(id=event_id(sid,s['ex_date']),security_id=sid,ex_date=s['ex_date'],
                eligible_quantity=str(quantities.get(s['symbol'],D(0))),
                source=f"Opening positions and supplied execution/corporate-action replay from {start} through pre-trade {s['ex_date']}; {opening['source']}"))
        else:
            symbol=e['symbol'];q=quantities.get(symbol,D(0))
            if kind=='split':quantities[symbol]=q*number(e['ratio'],True)
            else:
                amount=number(e['quantity'],True)
                if e['side']=='buy':quantities[symbol]=q+amount
                elif e['side']=='sell' and amount<=q:quantities[symbol]=q-amount
                else:raise ValueError('Invalid side or oversell in entitlement blotter')
    return result


def replay(lots,receipts,cutoff):
    """Replay frozen entitlements. Dollar receivables never rescale with shares."""
    date.fromisoformat(cutoff);result={};journal=[];seen=set()
    for item in deepcopy(lots):
        key=item['id']
        if key in result:raise ValueError('Duplicate economic dividend entitlement')
        if item['ex_date']>cutoff:continue
        if item.get('currency')!='USD' or not item.get('source'):raise ValueError('Unsupported currency or missing entitlement evidence')
        q=number(item['eligible_quantity']);rate=number(item['per_share'],True)
        gross=(q*rate).quantize(CENT,rounding=ROUND_HALF_UP)
        withheld=number(item.get('withholding_amount','0'))
        reclaim=number(item.get('recoverable_tax','0'))
        if reclaim>withheld or withheld>gross:raise ValueError('Invalid withholding/reclaim')
        if item.get('payable_date') and item['payable_date']<item['ex_date']:raise ValueError('Due-bill dividend requires separate handling')
        net=gross-withheld
        item.update(gross=str(gross),withholding=str(withheld),recoverable_tax=str(reclaim),net=str(net),paid='0',remaining=str(net))
        result[key]=item
        postings=dict(dividend_receivable=str(net),foreign_tax_receivable=str(reclaim),withholding_expense=str(withheld-reclaim),dividend_income=str(-gross))
        journal.append(dict(id=key,date=item['ex_date'],type='dividend_accrual',postings=postings,source=item['source']))
    for receipt in sorted(receipts,key=lambda x:(x['date'],x['id'])):
        if receipt['id'] in seen:raise ValueError('Duplicate cash receipt')
        seen.add(receipt['id']);date.fromisoformat(receipt['date'])
        if receipt['date']>cutoff:continue
        if receipt.get('kind')!='confirmed' or not receipt.get('source'):raise ValueError('Cash receipt requires confirmation evidence')
        item=result.get(receipt['action_id'])
        if item is None:raise ValueError('Receipt references unknown dividend entitlement')
        paid=number(receipt['amount'],True)
        if receipt.get('currency')!='USD' or not item.get('payable_date') or receipt['date']<item['payable_date'] or paid>number(item['remaining']):
            raise ValueError('Invalid receipt date, currency or amount')
        item['paid']=str(number(item['paid'])+paid);item['remaining']=str(number(item['remaining'])-paid)
        journal.append(dict(id=receipt['id'],date=receipt['date'],type='confirmed_payment',postings=dict(cash=str(paid),dividend_receivable=str(-paid)),source=receipt['source']))
    expected_receivable=D(0);modeled_cash=D(0)
    for item in result.values():
        remainder=number(item['remaining']);past_due=bool(item.get('payable_date') and item['payable_date']<=cutoff)
        item['overdue_unconfirmed']=past_due and remainder>0
        item['expected_remaining']='0' if past_due else str(remainder)
        expected_receivable+=number(item['expected_remaining'])
        if past_due and remainder:
            modeled_cash+=remainder
            # Separate journal: these are expected transfers, never bank receipts.
            journal.append(dict(id=item['id']+':EXPECTED',date=item['payable_date'],type='modeled_payment',
                postings=dict(modeled_cash=str(remainder),modeled_dividend_receivable=str(-remainder)),
                source='Assume full payment on the published schedule; receipt is unconfirmed'))
    return dict(lots=list(result.values()),journal=journal,
                gross_accrued=str(sum((number(x['gross']) for x in result.values()),D(0))),
                confirmed_receipts=str(sum((number(x['paid']) for x in result.values()),D(0))),
                receivable_without_assumed_receipts=str(sum((number(x['remaining']) for x in result.values()),D(0))),
                expected_receivable=str(expected_receivable),modeled_receipts=str(modeled_cash))


def split_factor(history,after,through):
    if not history or history.get('error') or history['start']>after or history['through']<through:
        raise ValueError('Complete requested action window unavailable')
    factor=D(1)
    for a in history['actions']:
        if a['type']=='split' and after<a['date']<=through:
            ratio=number(a['amount'],True);inverse=1/ratio
            if ratio!=ratio.to_integral_value() and abs(inverse-inverse.to_integral_value())>D('.00000001'):
                raise ValueError('Spin-off/complex adjustment cannot be treated as an ordinary split')
            factor*=ratio
    return factor


def resolve_rate(schedule,history,primary=None):
    if schedule.get('estimated'):return None,'Estimated declaration excluded',None
    if schedule.get('currency')!='USD':return None,'USD currency not established',None
    observed,issue=event_rate(history,schedule['ex_date'])
    if primary:
        resolved=False
        if primary.get('primary_ex_date') and primary['primary_ex_date']!=schedule['ex_date']:
            resolution=primary.get('ex_date_resolution',{})
            resolved=(resolution.get('ex_date')==schedule['ex_date']==resolution.get('record_date')==primary.get('record_date')
                      and resolution.get('evidence') and schedule['symbol'] not in resolution.get('exchange_exception_symbols',[schedule['symbol']]) and not issue)
            if not resolved:return None,'Issuer and market-data ex-dates conflict',primary
        if primary['payable_date']!=schedule['payable_date']:
            return None,'Issuer and market-data payment dates conflict',primary
        if not primary.get('primary_ex_date') and issue:
            return None,'Issuer declaration lacks an ex-date and action history does not corroborate it',primary
        return number(primary['per_share'],True),'Issuer amount; NYSE-rule-derived ex-date (issuer-table conflict retained)' if resolved else 'Issuer-declared amount',primary
    if issue:return None,issue,None
    reported=number(schedule['per_share'],True) if schedule.get('per_share') else None
    if reported is None:return observed,'Yahoo event amount; schedule amount was unavailable',history.get('evidence')
    if reported==observed:return reported,'Schedule and action history agree',history.get('evidence')
    # Yahoo chart and lastDividendValue can round to three decimals. Only keep
    # the more precise declared source when the rounding explains the difference.
    if schedule.get('source')=='Nasdaq' and schedule.get('declaration_status')=='Declared' and reported.quantize(D('.001'),rounding=ROUND_HALF_UP)==observed:
        return reported,'Declared Nasdaq precision; Yahoo rounds to three decimals',history.get('evidence')
    return None,f'Conflicting amounts: schedule {reported}, action history {observed}',None


def load_snapshots(output,additional=()):
    from .daily_spy import parse_holdings
    folder=Path(output)/'holdings_archive';path=folder/'index.json';snapshots={}
    for day,item in (json.loads(path.read_text()) if path.exists() else {}).items():
        raw=(folder/item['file']).read_bytes()
        if sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Dividend inventory source hash mismatch')
        embedded,holdings=parse_holdings(raw)
        if embedded!=day:raise ValueError('Dividend inventory embedded date mismatch')
        snapshots[day]=dict(positions={h['identifier']:h for h in holdings},source=f'State Street holdings labelled {day}',sha256=item['sha256'])
    for item in additional:
        day=item['date'];date.fromisoformat(day)
        if not item.get('source') or not item.get('sha256'):raise ValueError('Additional snapshot requires source evidence')
        existing=snapshots.setdefault(day,dict(positions={},source=item['source'],sha256=item['sha256']))
        for p in item['positions']:
            number(p['quantity'])
            if p['identifier'] in existing['positions'] and D(existing['positions'][p['identifier']]['quantity'])!=D(p['quantity']):
                raise ValueError('Conflicting source-dated quantities')
            existing['positions'][p['identifier']]=p
    return snapshots


def build(report,histories,snapshots,primary_records=(),inputs=None):
    inputs=inputs or {};as_of=report['as_of'];records=deepcopy(report.get('dividend_calendar',[]))
    positions={p['yahoo_symbol']:p for p in report['positions'] if p['security_type']=='equity'}
    frozen={x['id']:x for x in inputs.get('frozen_entitlements',[])}
    if len(frozen)!=len(inputs.get('frozen_entitlements',[])):raise ValueError('Duplicate frozen entitlement')
    existing={(r['symbol'],r['ex_date']) for r in records}
    for old in frozen.values():
        if old['symbol'] not in positions:
            positions[old['symbol']]=dict(identifier=old['security_id'],quantity=old['eligible_quantity'])
        if (old['symbol'],old['ex_date']) not in existing:
            records.append(old['canonical_schedule'])
    nav_dates={r['date']:r for r in report['official_history']}
    explicit={x['id']:x for x in inputs.get('entitlements',[])}
    if len(explicit)!=len(inputs.get('entitlements',[])):raise ValueError('Duplicate supplied entitlement')
    primary={(p['symbol'],p.get('existing_calendar_ex_date') or p.get('primary_ex_date')):p for p in primary_records}
    rows=[];lots=[];seen={};missing_schedules=[]
    for raw in records:
        if raw['symbol'] not in positions or raw['ex_date']>as_of:continue
        p=positions[raw['symbol']];key=event_id(p['identifier'],raw['ex_date'])
        signature=(raw.get('per_share'),raw['payable_date'],raw.get('currency'))
        if key in seen:
            if seen[key]!=signature:raise ValueError('Conflicting duplicate schedule')
            continue
        seen[key]=signature
        # Rebuild all known dated entitlements for receipt matching; the
        # outstanding model only includes ex<=asof<scheduled payment.
        row=dict(id=key,symbol=raw['symbol'],security_id=p['identifier'],ex_date=raw['ex_date'],
                 payable_date=raw['payable_date'],currency='USD',scheduled_rate=raw.get('per_share'),
                 schedule_source=raw['source'],source_url=raw['source_url'],pending=raw['payable_date']>as_of)
        old=frozen.get(key)
        rate,rate_status,evidence=resolve_rate(raw,histories.get(raw['symbol']),primary.get((raw['symbol'],raw['ex_date'])))
        history=histories.get(raw['symbol']) or {}
        history_unavailable=bool(history.get('error') or not history or history.get('start','9999')>raw['ex_date'])
        if rate is None and old and history_unavailable and schedule_economics(old['canonical_schedule'])==schedule_economics(raw) and not primary.get((raw['symbol'],raw['ex_date'])):
            rate=number(old['per_share'],True);rate_status='Previously verified rate retained from archived evidence';evidence=old.get('rate_evidence')
        row.update(per_share=str(rate) if rate is not None else None,rate_status=rate_status,rate_evidence=evidence)
        if rate is None:
            row.update(status='Unresolved action',eligible_quantity=None,gross=None,quantity_method=None);rows.append(row);continue
        previous,_=session_details(raw['ex_date']);row['required_holdings_date']=previous
        entitlement=explicit.get(key);quantity=None;method=None;source=None
        if entitlement:
            if entitlement['security_id']!=p['identifier'] or entitlement['ex_date']!=raw['ex_date'] or not entitlement.get('source'):
                raise ValueError('Supplied entitlement identity/date/source mismatch')
            quantity=number(entitlement['eligible_quantity']);method='documented_entitlement';source=entitlement['source']
        elif old and history_unavailable:
            quantity=number(old['eligible_quantity']);method=old['quantity_method'];source=old['quantity_source']
            row['quantity_frozen_from']=old.get('first_calculated_as_of',as_of)
        elif previous in snapshots and p['identifier'] in snapshots[previous]['positions']:
            try:
                factor=split_factor(histories.get(raw['symbol']),previous,raw['ex_date'])
                quantity=number(snapshots[previous]['positions'][p['identifier']]['quantity'])*factor
                row['ex_day_share_factor']=str(factor);method='dated_holdings_snapshot';source=snapshots[previous]['source']
            except ValueError as exc:row['quantity_error']=str(exc)
            row['holdings_sha256']=snapshots[previous].get('sha256')
            row['timing_note']='Published pre-ex as-of label; source timing has not been reconciled to a trade ledger'
        elif old:
            quantity=number(old['eligible_quantity']);method=old['quantity_method'];source=old['quantity_source']
            for field in ('holdings_sha256','timing_note','pre_ex_fund_shares','anchor_fund_shares','anchor_quantity','split_factor'):
                if field in old:row[field]=old[field]
            row['quantity_frozen_from']=old.get('first_calculated_as_of',as_of)
        else:
            try:
                # Independently calculated estimate, explicitly segregated from
                # observed quantities. Fund-unit changes never rescale a lot
                # after the ex-date: this only estimates its original quantity.
                units=number(nav_dates[previous]['shares_outstanding'],True)
                baseline=number(report['official']['shares_outstanding'],True)
                factor=split_factor(histories.get(raw['symbol']),raw['ex_date'],as_of)
                quantity=number(p['quantity'])*units/baseline/factor
                method='fund_unit_scaled_estimate';source='Current constituent basket per SPY share × published pre-ex fund shares; subsequent splits reversed'
                row.update(pre_ex_fund_shares=str(units),anchor_fund_shares=str(baseline),anchor_quantity=p['quantity'],split_factor=str(factor))
            except (KeyError,ValueError) as exc:row['quantity_error']=str(exc)
        row.update(eligible_quantity=str(quantity) if quantity is not None else None,quantity_method=method,quantity_source=source,
                   gross=str((quantity*rate).quantize(CENT,rounding=ROUND_HALF_UP)) if quantity is not None else None,
                   status='Calculated estimate' if method=='fund_unit_scaled_estimate' else 'Calculated from source-dated shares' if method=='dated_holdings_snapshot' else 'Documented entitlement' if method else 'Missing entitlement')
        # USD denomination does not establish withholding or final tax character.
        row['withholding_status']='Supplied' if entitlement and 'withholding_amount' in entitlement else 'Unknown; gross entitlement only'
        tax_source=entitlement if entitlement is not None else old or {}
        row['withholding_amount']=tax_source.get('withholding_amount','0')
        row['recoverable_tax']=tax_source.get('recoverable_tax','0')
        row['withholding_assumed']=tax_source.get('withholding_assumed','withholding_amount' not in tax_source)
        row['withholding_status']='Unknown; gross entitlement only' if row['withholding_assumed'] else 'Supplied in entitlement evidence'
        row['canonical_schedule']=raw
        row['first_calculated_as_of']=old.get('first_calculated_as_of',as_of) if old else as_of
        if old and (old['eligible_quantity']!=row['eligible_quantity'] or old['per_share']!=row['per_share']):
            row['restatement']=dict(previous_quantity=old['eligible_quantity'],previous_rate=old['per_share'],previous_gross=old['gross'],new_gross=row['gross'],reason='New source evidence changes the entitlement; prior report remains archived')
        rows.append(row)
        if quantity is not None:
            lot=dict(id=key,security_id=p['identifier'],symbol=raw['symbol'],ex_date=raw['ex_date'],payable_date=raw['payable_date'],currency='USD',
                     eligible_quantity=str(quantity),per_share=str(rate),quantity_method=method,source=source,
                     withholding_amount=row['withholding_amount'],recoverable_tax=row['recoverable_tax'],
                     withholding_assumed=row['withholding_assumed'])
            lots.append(lot)
    if set(explicit)-{r['id'] for r in rows}:raise ValueError('Supplied entitlement has no matching action/security; import its schedule as well')
    for symbol,history in histories.items():
        if symbol not in positions:continue
        for action in history.get('actions',[]):
            if action['type']=='dividend' and action['date']<=as_of and event_id(positions[symbol]['identifier'],action['date']) not in seen:
                missing_schedules.append(dict(symbol=symbol,ex_date=action['date'],reason='Observed ex-date lacks a usable payment schedule; outstanding status unknown'))
    receipts=inputs.get('receipts',[])
    # Receipts tied to unresolved rates/quantities reject instead of disappearing.
    modeled=replay(lots,receipts,as_of)
    observed_lots=[x for x in lots if x['quantity_method']!='fund_unit_scaled_estimate']
    observed_ids={x['id'] for x in observed_lots}
    observed=replay(observed_lots,[x for x in receipts if x['action_id'] in observed_ids],as_of)
    pending=[r for r in rows if r['pending']]
    known_total=sum((number(r['gross']) for r in pending if r['gross'] is not None),D(0))
    archive=dict(frozen)
    for row in rows:
        if row.get('gross') is not None:archive[row['id']]=row
        elif row['id'] in archive:
            archive[row['id']]=dict(archive[row['id']],requires_review=row.get('rate_status') or row['status'])
    return dict(schema_version=1,as_of=as_of,rows=sorted(rows,key=lambda x:(not x['pending'],x['payable_date'],x['symbol'])),
                outstanding_event_count=len(pending),calculated_outstanding_count=sum(r['gross'] is not None for r in pending),
                outstanding_source_dated_count=sum(r['gross'] is not None and r['quantity_method']!='fund_unit_scaled_estimate' for r in pending),
                expected_gross_receivable=str(known_total),modeled_book=modeled,source_dated_book=observed,
                entitlement_archive=list(archive.values()),
                prior_entitlements_under_review=[x for x in archive.values() if x.get('requires_review')],
                unresolved_outstanding=[r['id'] for r in pending if r['gross'] is None],missing_payment_schedules=missing_schedules,
                action_history_coverage=sum(not x.get('error') for x in histories.values()),
                complete=False,confirmed_total_receivable=None,
                scope='Independent gross calculation. Historical basket quantities are estimates where no pre-ex snapshot exists; opening completeness, withholding, constituent changes and actual cash receipts are not established.',
                opening_balance_status='Unresolved: a finite public lookback does not prove that no older unpaid entitlements exist',
                assumptions=['Ordinary cash ex-date entitlement; special/due-bill distributions need explicit treatment',
                             'For estimated quantities, constant stock basket per fund share between source dates; index changes and trading are not reconstructed',
                             'Published fund-share and holdings capital bases may differ; proportional estimates are not confirmed entitlement',
                             'Expected book assumes payment on scheduled date; confirmed book requires receipt evidence',
                             'Gross amount is not net receivable when withholding/reclaims are unknown'])
