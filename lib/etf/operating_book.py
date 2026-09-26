"""Persistent, prospective portfolio model from public holdings/actions/prices.

Only the initial standalone holdings cash is imported. Later holdings and cash
observations never overwrite books or create inferred executions. User-supplied
operating records are read separately and never enter the public-input cache.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .daily_accruals import daily_replay, DEFAULT_POLICY, is_session
from .dividend_sources import event_rate
from .ledger import amount

D = Decimal
SEED_MODEL = Path(__file__).resolve().parents[2]/'data/spy_seed/daily-model-inputs.json'


def encode(value):
    return json.dumps(value, indent=2, allow_nan=False,
                      default=lambda x: sorted(x) if isinstance(x, set) else str(x))


def save(path, value):
    temp = path.with_suffix('.next.json'); temp.write_text(encode(value)); temp.replace(path)


def key(position):
    return position.get('yahoo_symbol') or position['identifier']


def retained_symbols(output):
    path=Path(output)/'daily-book/public-model-inputs.json'
    if not path.exists():path=SEED_MODEL
    if not path.exists():return set()
    model=json.loads(path.read_text())
    return {p['quote_symbol'] for p in model['opening']['positions'] if p.get('quote_symbol')}


def seed_model(report):
    """Seed once, before the first modeled accrual day; no statement balances."""
    start = report['reconciliation']['holdings_as_of']
    if start >= report['as_of']:
        raise ValueError('Opening holdings must precede the first valuation/accrual day')
    positions = []
    for p in report['positions']:
        if p.get('price') is None:
            raise ValueError('Opening model has an unpriced security')
        positions.append(dict(symbol=key(p), quote_symbol=p.get('yahoo_symbol'), security_id=p['identifier'], quantity=p['quantity'],
            cost=str(D(p['quantity'])*D(p['price'])), carrying_value=str(D(p['quantity'])*D(p['price']))))
    items = []
    for lot in report['dividend_receivables']['modeled_book']['lots']:
        if lot['ex_date'] <= start and lot.get('payable_date') and lot['payable_date'] > start:
            items.append(dict(id=lot['id'], symbol=lot['symbol'], ex_date=lot['ex_date'],
                payable_date=lot['payable_date'], currency='USD', gross=lot['gross'],
                withholding='0', remaining=lot['gross'], source='Opening gross entitlement estimate: '+lot['source']))
    shares = next((r['shares_outstanding'] for r in report['official_history'] if r['date'] == start), None)
    if shares is None:
        raise ValueError('Opening portfolio requires dated fund units')
    opening = dict(date=start, shares=shares, positions=positions, dividend_items=items,
        source='Prospective model: published holdings and standalone cash as of '+start+
            '; opening dividends are gross estimates; fee/trade/distribution balances assumed zero; initial carrying values use first model close, not historical costs',
        balances=dict(cash=report['legacy_holdings_cash_diagnostic']['reported_cash'],
            dividend_receivable=str(sum((D(r['remaining']) for r in items), D(0))),
            trade_receivable='0', trade_payable='0', fee_payable='0', distribution_payable='0'))
    return dict(schema_version=1, fund_id='REDI', source_fund='SPY', opening=opening,
                policy=dict(DEFAULT_POLICY), events=[], price_history={}, input_hashes={})


def ingest(model, report, histories):
    """Refresh market evidence without changing opening cash, units or positions."""
    model = deepcopy(model); start = model['opening']['date']; end = report['as_of']
    symbols = {p['symbol'] for p in model['opening']['positions']}
    prices = {key(p): dict(date=end, price=p['price'], basis='as_of_share_units',
                          source=p.get('price_source'), field=p.get('source_field'))
              for p in report['positions'] if p.get('price') is not None}
    prices.update({symbol:dict(date=end,price=q['close'],basis='as_of_share_units',source=q['source_url'],field=q['source_field'])
                   for symbol,q in report.get('operating_quotes',{}).items() if not q.get('error') and q.get('date')==end})
    model['price_history'][end] = prices
    model['input_hashes'][end] = dict(
        holdings=report['manifest']['files']['valuation_holdings']['sha256'],
        actions=report['dividend_receivables']['input_evidence']['action_history_sha256'])
    actions = {e['id']: e for e in model['events']}
    problems = []
    covered = set()
    for row in report['dividend_receivables']['rows']:
        if row['symbol'] not in symbols or not start < row['ex_date'] <= end:
            continue
        covered.add((row['symbol'], row['ex_date']))
        if row.get('per_share') is None:
            problems.append(f'{row["symbol"]} {row["ex_date"]}: unresolved declared dividend rate')
            continue
        # Quantity deliberately comes from the forward positions/blotter, not
        # the SPY historical basket quantity estimated by the source subledger.
        actions[row['id']] = dict(id=row['id'], date=row['ex_date'], type='dividend',
            symbol=row['symbol'], per_share=row['per_share'], payable_date=row['payable_date'],
            currency='USD', entitlement_rule='ordinary_ex_date', source=row['source_url'])
    for symbol in sorted(symbols):
        history = histories.get(symbol)
        if history is None:
            # Non-equity rights have their separate dated valuation mark.
            if symbol not in {p['identifier'] for p in report['positions'] if p.get('security_type') != 'equity'}:
                problems.append(f'{symbol}: missing corporate-action history')
            continue
        if history.get('error'):
            problems.append(f'{symbol}: corporate-action retrieval failed'); continue
        for a in history.get('actions', []):
            if not start < a['date'] <= end:
                continue
            if a['type'] == 'split':
                ratio = amount(a['amount'], True)
                if ratio != ratio.to_integral() and 1/ratio != (1/ratio).to_integral():
                    problems.append(f'{symbol} {a["date"]}: complex split/spin-off needs an explicit action'); continue
                eid = f'SPLIT:{symbol}:{a["date"]}'
                actions[eid] = dict(id=eid, date=a['date'], type='split', symbol=symbol,
                                   ratio=str(ratio), source=history.get('evidence', {}).get('url', 'Archived Yahoo corporate action'))
            elif a['type'] == 'dividend' and (symbol, a['date']) not in covered:
                # A missing payment date must not prevent ex-date income/AR.
                try:
                    rate, error = event_rate(history, a['date'])
                    if rate is None:raise ValueError(error or 'Missing rate')
                    eid = f'DIVIDEND:{symbol}:{a["date"]}'
                    actions[eid] = dict(id=eid, date=a['date'], type='dividend', symbol=symbol,
                        per_share=str(rate), payable_date=None, currency='USD', entitlement_rule='ordinary_ex_date',
                        source=history.get('evidence', {}).get('url', 'Archived Yahoo dividend; payment date unavailable'))
                except ValueError as exc:
                    problems.append(f'{symbol} {a["date"]}: {exc}')
            elif a['type'] not in ('dividend', 'split'):
                problems.append(f'{symbol} {a["date"]}: unsupported {a["type"]} corporate action')
    # If a previously undated action gets a schedule, replace its provisional
    # identity, rather than booking a second economic dividend.
    for symbol, day in covered:
        actions.pop(f'DIVIDEND:{symbol}:{day}', None)
    model['events'] = sorted(actions.values(), key=lambda e:(e['date'],e['id']))
    return model, problems


def update(report, output, through=None, progress=print):
    output = Path(output); folder = output/'daily-book'; folder.mkdir(parents=True, exist_ok=True)
    public_path = folder/'public-model-inputs.json'
    supplied_path = output/'daily-accounting-input.json'
    supplied = supplied_path.exists()
    problems=[]
    if supplied:
        inputs=json.loads(supplied_path.read_text())
        if inputs.get('fund_id') != 'REDI':
            raise ValueError('Daily accounting input must identify the REDI portfolio')
        inputs['policy']=dict(inputs.get('policy',{}))
        inputs['policy'].setdefault('payment_mode','confirmed')
    else:
        path=public_path if public_path.exists() else SEED_MODEL
        public=json.loads(path.read_text()) if path.exists() else seed_model(report)
        history_path = output/'dividend-actions/latest.json'
        history = json.loads(history_path.read_text())['securities']
        public, problems = ingest(public, report, history)
        save(public_path, public)  # Only public-derived data; never supplied books.
        inputs=public
    cutoff = through or (inputs.get('cutoff',report['as_of']) if supplied else report['as_of'])
    if through is None:
        yesterday = datetime.now(ZoneInfo('America/New_York')).date()-timedelta(days=1)
        candidate = date.fromisoformat(cutoff)+timedelta(days=1)
        while candidate <= yesterday and not is_session(candidate.isoformat()):
            cutoff = candidate.isoformat(); candidate += timedelta(days=1)
    if cutoff < report['as_of'] and not supplied:
        raise ValueError('Daily book cutoff cannot precede the current market report')
    # Beyond the last available close only known exchange closures may accrue.
    # The general replay also checks every intermediate session.
    status = dict(as_of=cutoff, source_as_of=report['as_of'], opening_date=inputs['opening']['date'],
        mode='Supplied operating records' if supplied else 'Prospective holdings model',
        complete=False, assumptions=[] if supplied else [
            'Opening cash is the standalone holdings cash row; no later cash snapshot resets the book.',
            'Opening receivables are known gross estimates; older unpaid claims and withholding remain unresolved.',
            'Opening unitary-fee, trade and fund-distribution liabilities are assumed zero.',
            'Initial holdings remain invested until an explicit trade or corporate action changes them; SPY rebalance and fund-unit changes are comparisons, not executions.',
            '45 bps is REDI’s assumed unitary expense ratio; this model is not a reproduction of SPY’s fee or complete NAV.',
            'Corporate dividends are gross; declared payment dates generate modeled cash only. Fee payments require supplied events.'])
    try:
        if problems and not supplied:
            raise ValueError('; '.join(problems[:10]))
        result = daily_replay(inputs['opening'], inputs['events'], cutoff, inputs['price_history'], inputs.get('policy'))
        status.update(result)
        status['status'] = 'Daily accruals calculated' if supplied else 'Daily accruals calculated — opening assumptions'
        status['model_complete'] = not problems if not supplied else True
        if not supplied:
            status['source_gaps'] = dict(older_dividends_without_payment_schedule=len(report['dividend_receivables']['missing_payment_schedules']),
                unresolved_source_dividends=len(report['dividend_receivables']['unresolved_outstanding']))
        latest = result['daily'][-1]
        if not supplied:
            status['comparison'] = dict(official_spy_nav=report['official']['nav'],
                nav_difference=str(D(latest['nav'])-D(report['official']['nav'])) if cutoff == report['as_of'] else None,
                observed_spy_shares=report['official']['shares_outstanding'],
                observed_holdings_cash=report['legacy_holdings_cash_diagnostic']['reported_cash'])
        status['input_sha256'] = sha256(encode(inputs).encode()).hexdigest()
        status['engine_sha256'] = sha256(Path(__file__).with_name('daily_accruals.py').read_bytes()+Path(__file__).with_name('ledger.py').read_bytes()).hexdigest()
    except (ValueError, KeyError) as exc:
        status.update(status='Daily book needs source data', complete=False, error=str(exc), daily=[])
        previous_path=folder/'latest.json'
        if previous_path.exists():
            previous=json.loads(previous_path.read_text())
            if previous.get('daily'):
                status['last_complete_day']=previous['daily'][-1]
            elif previous.get('last_complete_day'):
                status['last_complete_day']=previous['last_complete_day']
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = folder/'runs'/stamp; run.mkdir(parents=True)
    (run/'inputs.json').write_text(encode(inputs)); (run/'report.json').write_text(encode(status))
    (run/'daily_accruals.py').write_bytes(Path(__file__).with_name('daily_accruals.py').read_bytes())
    (run/'ledger.py').write_bytes(Path(__file__).with_name('ledger.py').read_bytes())
    save(folder/'latest.json', status)
    report['daily_accruals'] = json.loads(encode(status))
    progress(f'Daily operating book: {status["status"]}; through {cutoff}', flush=True)
    return report['daily_accruals']
