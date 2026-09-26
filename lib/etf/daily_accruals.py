"""Calendar-day operating replay with one unitary fee and ex-date dividends.

The fee base comes from the replayed portfolio, never an administrator NAV or
reported liabilities. Opening books persist; daily holdings are not transactions.
"""
from calendar import isleap
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

from .ledger import replay, amount

D = Decimal
CENT = D('.01')
DEFAULT_POLICY = dict(annual_rate='0.0045', day_count='ACT/365F',
                      base='closing_net_assets_after_fee', payment_mode='scheduled')


@lru_cache(maxsize=8)
def trading_calendar(year):
    import exchange_calendars as xcals
    return xcals.get_calendar('XNYS', start=f'{year-1}-01-01', end=f'{year+1}-12-31')


def is_session(day):
    return bool(trading_calendar(date.fromisoformat(day).year).is_session(day))


def policy_for(policy, day):
    policy = dict(DEFAULT_POLICY, **policy)
    if policy['base'] != 'closing_net_assets_after_fee' or policy['day_count'] not in ('ACT/365F', 'ACT/ACT'):
        raise ValueError('Unsupported unitary fee base/day count')
    if policy['payment_mode'] not in ('scheduled', 'confirmed'):
        raise ValueError('Unsupported dividend payment mode')
    rate = amount(policy['annual_rate'])
    changes = policy.get('rate_changes', [])
    seen = set()
    for item in sorted(changes, key=lambda r: r['effective_date']):
        effective = date.fromisoformat(item['effective_date']).isoformat()
        value = amount(item['annual_rate'])
        if effective in seen or not item.get('source') or not 0 <= value < 1:
            raise ValueError('Invalid or duplicate effective fee rate')
        seen.add(effective)
        if effective <= day:
            rate = value
    if not 0 <= rate < 1:
        raise ValueError('Invalid annual unitary fee rate')
    denominator = 366 if policy['day_count'] == 'ACT/ACT' and isleap(date.fromisoformat(day).year) else 365
    return policy, rate, denominator


def daily_replay(opening, events, cutoff, price_history, policy=None):
    """Replay each day once; catch up weekends and reject missing session marks.

    price_history maps YYYY-MM-DD to the existing ledger price schema. Opening
    is EOD. Scheduled dividend cash is explicit model cash, never confirmation.
    Actual receipt events replace scheduled receipts for the entire entitlement,
    leaving any unpaid remainder outstanding instead of inventing its payment.
    """
    opening, supplied = deepcopy(opening), deepcopy(events)
    first = date.fromisoformat(opening['date']); last = date.fromisoformat(cutoff)
    if last <= first:
        raise ValueError('Daily accrual cutoff must follow opening end-of-day books')
    policy, _, _ = policy_for(policy or {}, cutoff)
    ids = set()
    for e in supplied:
        if e['id'] in ids or e['id'].startswith(('UNITARY:', 'SCHEDULED:')):
            raise ValueError('Duplicate/reserved event identity')
        ids.add(e['id'])
        if e['type'] in ('fee', 'unitary_fee'):
            raise ValueError('Single unitary fee policy replaces manual/category fee accruals')
    generated = []; days = []; previous = None
    cash_events = {e['action_id'] for e in supplied if e['type'] == 'dividend_payment' and e['date'] <= cutoff}
    prior_prices = None; price_date = None
    for day in sorted(price_history):
        if day <= opening['date']:
            prior_prices = price_history[day]; price_date = day
    for i in range(1, (last-first).days+1):
        day = (first+timedelta(days=i)).isoformat()
        if day in price_history:
            prior_prices = price_history[day]; price_date = day
        elif is_session(day):
            raise ValueError(f'Missing closing prices for trading session {day}; daily book not advanced')
        if prior_prices is None:
            raise ValueError(f'No dated prices to carry on {day}')
        prices = {}
        for symbol, quote in prior_prices.items():
            if quote['date'] != price_date or quote.get('basis') != 'as_of_share_units':
                raise ValueError('Price observation date/share basis mismatch')
            prices[symbol] = dict(quote, date=day, observed_date=price_date)
        # Never carry a pre-split mark on the new share basis, even on a closure.
        if price_date != day and any(e['type'] == 'split' and price_date < e['date'] <= day for e in supplied):
            raise ValueError('Split requires a dated price on the new share basis')
        active = [e for e in supplied if e['date'] <= day]
        # A month-end payment may include today's accrual. It posts after the
        # fee; excluding it from the pre-fee valuation is NAV-neutral.
        pre_fee_events=[e for e in active if not (e['type']=='fee_payment' and e['date']==day)]
        try:
            before = replay(opening, pre_fee_events+generated, day, prices)
        except KeyError as exc:
            if exc.args[0] not in prices:
                raise ValueError(f'Missing dated closing price or referenced accounting record: {exc.args[0]} on {day}') from exc
            raise
        scheduled_today = D(0)
        if policy['payment_mode'] == 'scheduled':
            for key, lot in sorted(before['dividends'].items()):
                if lot.get('payable_date') == day and key not in cash_events and amount(lot['remaining']) > 0:
                    paid = amount(lot['remaining']); scheduled_today += paid
                    generated.append(dict(id='SCHEDULED:'+key, date=day, type='dividend_payment',
                        action_id=key, amount=str(paid), source='MODEL: full cash payment on declared payable date; unconfirmed'))
            if scheduled_today:
                before = replay(opening, pre_fee_events+generated, day, prices)
        _, rate, denominator = policy_for(policy, day)
        # Correct the cent-posted liability to its unrounded cumulative balance
        # for the next day's exact base, avoiding systematic rounding drift.
        carry = before.get('unitary_exact', D(0))-before.get('unitary_posted', D(0))
        base = before['net_assets']-carry
        fee = dict(id='UNITARY:'+day, date=day, type='unitary_fee', base=str(base),
                   annual_rate=str(rate), year_days=denominator,
                   source=f'Single unitary expense; {policy["day_count"]}; closing net assets after current fee')
        generated.append(fee)
        state = replay(opening, active+generated, day, prices)
        entry = next(e for e in state['journal'] if e['id'] == fee['id'])
        expense = sum((amount(p['amount']) for p in entry['postings'] if p['account'] == 'expense'), D(0))
        income = -state['balances']['income']
        accrual = income - (-previous['balances']['income'] if previous else D(0))
        receipts = sum((amount(e['amount']) for e in active if e['date'] == day and e['type'] == 'dividend_payment'), D(0))
        fee_paid = sum((amount(e['amount']) for e in active if e['date'] == day and e['type'] == 'fee_payment'), D(0))
        days.append(dict(date=day, price_date=price_date, carried_prices=price_date != day,
            securities=str(state['balances']['securities']), cash=str(state['balances']['cash']),
            dividend_income=str(accrual), dividend_receivable=str(state['balances']['dividend_receivable']),
            confirmed_dividend_cash=str(receipts), scheduled_dividend_cash=str(scheduled_today),
            annual_rate=str(rate), year_days=denominator, fee_base=str(base),
            exact_fee=entry['exact_accrual'], fee_accrual=str(expense), fee_payment=str(fee_paid),
            fee_payable=str(-state['balances']['fee_payable']), cumulative_fee=str(state['unitary_posted']),
            net_assets=str(state['net_assets']), shares=str(state['shares']), nav=str(state['nav'])))
        previous = state
    return dict(schema_version=1, opening_date=opening['date'], as_of=cutoff, policy=policy,
                daily=days, generated_events=generated, state=state)
