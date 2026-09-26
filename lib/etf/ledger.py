"""Deterministic USD long-only accounting replay with balanced journal entries.

Opening balances and events are supplied records, never inferred trades from
holdings changes. Unsupported actions fail closed. Corrections require replaying
an explicitly corrected input file, preserving the previous report as evidence.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

D = Decimal
ACCOUNTS = ('cash', 'securities', 'dividend_receivable', 'trade_receivable',
            'trade_payable', 'fee_payable', 'distribution_payable', 'capital',
            'income', 'expense', 'realized_gain', 'unrealized_gain')


def amount(value, positive=False):
    n = D(str(value))
    if not n.is_finite() or (positive and n <= 0):
        raise ValueError('Expected a finite positive amount' if positive else 'Expected finite amount')
    return n


def replay(opening, events, cutoff, prices=None):
    """Fresh replay is atomic and repeatable; duplicate IDs always reject."""
    opening = deepcopy(opening); cutoff = date.fromisoformat(cutoff)
    start = date.fromisoformat(opening['date'])
    if cutoff < start:
        raise ValueError('Cutoff precedes opening books')
    if not opening.get('source'):
        raise ValueError('Opening books require source evidence')
    state = dict(positions={}, balances={k:D(0) for k in ACCOUNTS}, shares=amount(opening['shares'], True),
                 journal=[], blotter=[], dividends={}, trades={}, fees={}, distributions={})
    for p in opening['positions']:
        if p['symbol'] in state['positions']:
            raise ValueError('Duplicate opening security')
        q, cost = amount(p['quantity'],True), amount(p['cost'])
        carrying = amount(p['carrying_value'])
        if min(cost,carrying) < 0: raise ValueError('Negative cost or opening carrying value')
        state['positions'][p['symbol']] = dict(quantity=q,cost=cost,opening_carrying_value=carrying)
    required = ('cash','dividend_receivable','trade_receivable','trade_payable','fee_payable','distribution_payable')
    if any(k not in opening['balances'] for k in required):
        raise ValueError('Opening operating balances must be explicit, not silently zero')
    for k in required:
        val = amount(opening['balances'][k])
        if val < 0: raise ValueError('Negative opening balance')
        state['balances'][k] = -val if k.endswith('payable') else val
    state['balances']['securities'] = sum(p['opening_carrying_value'] for p in state['positions'].values())
    if 'dividend_items' in opening:
        for item in opening['dividend_items']:
            key=item['id'];remaining=amount(item['remaining']);gross=amount(item['gross']);withholding=amount(item.get('withholding',0))
            if key in state['dividends'] or not item.get('source') or item.get('currency')!='USD':
                raise ValueError('Invalid opening dividend identity/source/currency')
            if date.fromisoformat(item['ex_date'])>start or min(remaining,gross,withholding)<0 or remaining>gross-withholding:
                raise ValueError('Invalid opening dividend amount/date')
            pay=item.get('payable_date')
            if pay and date.fromisoformat(pay)<date.fromisoformat(item['ex_date']):raise ValueError('Invalid opening dividend payment date')
            state['dividends'][key]=dict(item,remaining=remaining)
        if sum((d['remaining'] for d in state['dividends'].values()),D(0))!=state['balances']['dividend_receivable']:
            raise ValueError('Opening dividend items do not reconcile to opening receivable')
    state['balances']['capital'] = -sum(state['balances'].values())
    state['journal'].append(dict(id='OPEN',date=opening['date'],type='opening',description=opening['source'],
                                 postings=[dict(account=k,amount=str(v)) for k,v in state['balances'].items() if v]))

    def post(e, entries):
        if sum(entries.values()) != 0:
            raise ValueError('Unbalanced journal')
        for k,v in entries.items(): state['balances'][k] += v
        state['journal'].append(dict(id=e['id'],date=e['date'],type=e['type'],description=e['source'],
                                     postings=[dict(account=k,amount=str(v)) for k,v in entries.items() if v]))

    ids=set(state['dividends']); ordered=[]
    for e in events:
        if e['id'] in ids or e['id']=='OPEN' or not e.get('source'):
            raise ValueError('Duplicate event ID or missing source')
        ids.add(e['id']); day=date.fromisoformat(e['date'])
        if day <= start: raise ValueError('Events must follow opening end-of-day books')
        if day <= cutoff: ordered.append(e)
    # Sequence is explicit for same-day executions; ordinary ex-date entitlements
    # are processed at start of day before trades. Special due-bill actions reject.
    priority={'split':0,'dividend':1,'trade':2,'unitary_fee':100,'fee_payment':101}
    ordered.sort(key=lambda e:(e['date'],priority.get(e['type'],3),e.get('sequence',0),e['id']))
    for e in ordered:
        t=e['type']; b=state['balances']; p=state['positions'].get(e.get('symbol'))
        if t=='trade':
            q=amount(e['quantity'],True); price=amount(e['price'],True); fees=amount(e.get('commission',0))
            if fees<0 or date.fromisoformat(e['settlement_date'])<date.fromisoformat(e['date']):
                raise ValueError('Invalid trade fees or settlement date')
            side=e['side']; gross=q*price
            if side=='buy':
                p=state['positions'].setdefault(e['symbol'],dict(quantity=D(0),cost=D(0)))
                p['quantity']+=q; p['cost']+=gross+fees
                post(e,dict(securities=gross+fees,trade_payable=-(gross+fees)))
                due=gross+fees
            elif side=='sell' and p and p['quantity']>=q:
                if fees>gross: raise ValueError('Fees exceed proceeds')
                cost=p['cost']*q/p['quantity']; p['quantity']-=q;p['cost']-=cost
                due=gross-fees
                post(e,dict(securities=-cost,trade_receivable=due,realized_gain=cost-due))
            else: raise ValueError('Invalid side or oversell')
            state['trades'][e['id']]=dict(remaining=due,side=side,settlement_date=e['settlement_date'])
            state['blotter'].append(dict(e,gross=str(gross),net_settlement=str(due)))
        elif t=='settlement':
            trade=state['trades'][e['trade_id']]; paid=amount(e['amount'],True)
            if paid>trade['remaining'] or e['date']<trade['settlement_date']:
                raise ValueError('Over-settlement or early settlement')
            trade['remaining']-=paid
            post(e,dict(cash=-paid,trade_payable=paid) if trade['side']=='buy' else dict(cash=paid,trade_receivable=-paid))
        elif t=='dividend':
            if e.get('entitlement_rule') != 'ordinary_ex_date' or e.get('currency')!='USD':
                raise ValueError('Special dividend or FX action requires explicit handling')
            q=p['quantity'] if p else D(0)
            rate=amount(e['per_share'],True); gross=(q*rate).quantize(D('.01'),rounding=ROUND_HALF_UP)
            # Withholding recorded as expense; a recoverable reclaim needs a separate account.
            withholding=amount(e.get('withholding_rate',0))
            if not 0<=withholding<=1: raise ValueError('Invalid withholding')
            tax=(gross*withholding).quantize(D('.01'),rounding=ROUND_HALF_UP); net=gross-tax
            pay=e.get('payable_date')
            if pay and pay<e['date']: raise ValueError('Dividend pay date precedes ex-date')
            state['dividends'][e['id']]=dict(symbol=e['symbol'],eligible_quantity=str(q),per_share=str(rate),gross=str(gross),
                                          withholding=str(tax),remaining=net,ex_date=e['date'],payable_date=pay)
            post(e,dict(dividend_receivable=net,expense=tax,income=-gross))
        elif t=='dividend_payment':
            dividend=state['dividends'][e['action_id']]; paid=amount(e['amount'],True)
            if not dividend['payable_date'] or e['date']<dividend['payable_date'] or paid>dividend['remaining']:
                raise ValueError('Unverified pay date or excess dividend payment')
            dividend['remaining']-=paid
            post(e,dict(cash=paid,dividend_receivable=-paid))
        elif t=='split':
            ratio=amount(e['ratio'],True)
            if not p: raise ValueError('Split has no eligible position')
            p['quantity']*=ratio
            post(e,{})  # Cost unchanged; fractional shares retained until confirmed cash-in-lieu.
        elif t=='fee':
            base=amount(e['base'],True); rate=amount(e['annual_rate']); first=date.fromisoformat(e['from_date']); last=date.fromisoformat(e['through_date'])
            if not 0<=rate<1 or first>last or first<=start or last>date.fromisoformat(e['date']):
                raise ValueError('Invalid fee dates/rate')
            fee_key=e['fee_key']
            days={(first.toordinal()+i) for i in range((last-first).days+1)}
            if days & state['fees'].get(fee_key,set()): raise ValueError('Fee period already accrued')
            state['fees'].setdefault(fee_key,set()).update(days)
            charge=(base*rate*len(days)/365).quantize(D('.01'),rounding=ROUND_HALF_UP)
            post(e,dict(expense=charge,fee_payable=-charge))
        elif t=='unitary_fee':
            # Generated by daily_accruals from independently valued books. Retain
            # fractional cents and post the cumulative rounding difference.
            base=amount(e['base'],True);rate=amount(e['annual_rate']);denominator=amount(e['year_days'],True)
            if not 0<=rate<1 or denominator not in (D(365),D(366)):
                raise ValueError('Invalid unitary fee policy')
            day=date.fromisoformat(e['date']).toordinal()
            if day in state['fees'].get('unitary',set()):raise ValueError('Unitary fee day already accrued')
            state['fees'].setdefault('unitary',set()).add(day)
            exact=base*rate/(denominator+rate)
            state['unitary_exact']=state.get('unitary_exact',D(0))+exact
            total=state['unitary_exact'].quantize(D('.01'),rounding=ROUND_HALF_UP)
            charge=total-state.get('unitary_posted',D(0));state['unitary_posted']=total
            post(e,dict(expense=charge,fee_payable=-charge))
            state['journal'][-1].update(exact_accrual=str(exact),base=str(base),annual_rate=str(rate),year_days=str(denominator))
        elif t=='fee_payment':
            paid=amount(e['amount'],True)
            if paid>-b['fee_payable']: raise ValueError('Excess fee payment')
            post(e,dict(cash=-paid,fee_payable=paid))
        elif t in ('creation','redemption'):
            units=amount(e['shares'],True); cash=amount(e['cash'],True)
            if e.get('basket'): raise ValueError('In-kind baskets require explicit security-transfer implementation')
            sign=1 if t=='creation' else -1
            if state['shares']+sign*units<=0: raise ValueError('Invalid redemption units')
            state['shares']+=sign*units; post(e,dict(cash=sign*cash,capital=-sign*cash))
        elif t=='fund_distribution':
            # Explicit entitlement record: same-day creations do not establish
            # eligibility for a distribution whose ex-date is that day.
            declared=amount(e['eligible_shares'],True)*amount(e['per_share'],True)
            if e['payable_date']<e['date']: raise ValueError('Invalid fund payable date')
            state['distributions'][e['id']]=dict(remaining=declared,payable_date=e['payable_date'])
            post(e,dict(capital=declared,distribution_payable=-declared))
        elif t=='fund_distribution_payment':
            d=state['distributions'][e['action_id']]; paid=amount(e['amount'],True)
            if e['date']<d['payable_date'] or paid>d['remaining']: raise ValueError('Invalid fund distribution payment')
            d['remaining']-=paid;post(e,dict(cash=-paid,distribution_payable=paid))
        else:
            raise ValueError(f'Unsupported event {t}; requires review, never ignored')
        if b['cash']<0: raise ValueError('Insufficient cash; financing not supported')
    if prices is not None:
        total=D(0)
        for symbol,p in state['positions'].items():
            if not p['quantity']: continue
            quote=prices[symbol]
            if quote['date']!=cutoff.isoformat() or quote.get('basis')!='as_of_share_units':
                raise ValueError('Closing price date/share basis mismatch')
            p['price']=amount(quote['price'],True);p['market_value']=p['quantity']*p['price'];total+=p['market_value']
        change=total-state['balances']['securities']
        post(dict(id='MARK',date=cutoff.isoformat(),type='valuation',source='Supplied dated closing prices'),
             dict(securities=change,unrealized_gain=-change))
    if sum(state['balances'].values()) != 0: raise ValueError('Trial balance is not balanced')
    state['book_net_assets']=sum(state['balances'][k] for k in ACCOUNTS[:7])
    state['net_assets']=state['book_net_assets'] if prices is not None else None
    if state['net_assets'] is not None and state['net_assets']<=0:
        raise ValueError('Nonpositive closing net assets require review')
    state['nav']=state['net_assets']/state['shares'] if prices is not None else None
    state['valuation_status']='Dated prices supplied' if prices is not None else 'Unvalued cost-basis books; NAV unavailable'
    state['as_of']=cutoff.isoformat()
    return state


def walkthrough_input():
    """Small explicit example, never passed off as SPY's unavailable blotter."""
    opening=dict(date='2026-09-14',source='Accounting walkthrough: assumed opening books',shares=100,
                 positions=[dict(symbol='EXAMPLE',quantity=10,cost=1000,carrying_value=1000)],
                 balances=dict(cash=1000,dividend_receivable=0,trade_receivable=0,trade_payable=0,fee_payable=0,distribution_payable=0))
    events=[
        dict(id='D1',date='2026-09-15',type='dividend',symbol='EXAMPLE',per_share=2,currency='USD',entitlement_rule='ordinary_ex_date',payable_date='2026-09-17',source='Assumed $2 ordinary dividend; 10 eligible shares'),
        dict(id='T1',date='2026-09-15',type='trade',symbol='EXAMPLE',side='buy',quantity=5,price=98,commission=0,settlement_date='2026-09-16',source='Assumed purchase on ex-date; these 5 shares do not earn D1'),
        dict(id='S1',date='2026-09-16',type='settlement',trade_id='T1',amount=490,source='Assumed settlement confirmation'),
        dict(id='P1',date='2026-09-17',type='dividend_payment',action_id='D1',amount=20,source='Assumed confirmed dividend cash receipt'),
        dict(id='CA1',date='2026-09-18',type='split',symbol='EXAMPLE',ratio=2,source='Assumed 2-for-1 split; total cost unchanged'),
        dict(id='F1',date='2026-09-18',type='fee',fee_key='advisory',base=2000,annual_rate='.0045',from_date='2026-09-15',through_date='2026-09-18',source='45 bps ACT/365, 4 calendar days, fixed $2,000 base'),
    ]
    return dict(opening=opening,events=events,cutoff='2026-09-18',prices={'EXAMPLE':dict(date='2026-09-18',price=49,basis='as_of_share_units')})


def walkthrough():
    inputs=walkthrough_input()
    return replay(inputs['opening'],inputs['events'],inputs['cutoff'],inputs['prices'])


if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    parser=argparse.ArgumentParser(description='Replay supplied accounting records without posting to external books')
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args();inputs=json.loads(args.input.read_text())
    result=replay(inputs['opening'],inputs['events'],inputs['cutoff'],inputs.get('prices'))
    print(json.dumps(result,indent=2,default=lambda value:sorted(value) if isinstance(value,set) else str(value)))
