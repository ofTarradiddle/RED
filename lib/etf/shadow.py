"""Independent equity snapshot valuation and provider break attribution.

This module does not post journals, fabricate operational balances, or publish NAV.
Yahoo is an optional quote source; data rights and valuation policy need review.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import tempfile

D = Decimal
ASSETS = ('cash', 'dividends_receivable', 'trade_receivables', 'other_receivables')
LIABILITIES = ('accrued_fees', 'trade_payables', 'other_liabilities')


def decimal(value, field, minimum=D('0')):
    if isinstance(value, bool) or value is None:
        raise ValueError(f'{field}: a numeric value is required')
    try:
        result = D(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'{field}: invalid number') from exc
    if not result.is_finite() or (minimum is not None and result < minimum):
        raise ValueError(f'{field}: must be finite and at least {minimum}')
    return result


def positive(value, field):
    value = decimal(value, field)
    if value <= 0:
        raise ValueError(f'{field}: must be positive')
    return value


def validate_snapshot(snapshot):
    date.fromisoformat(snapshot['as_of'])
    if snapshot.get('base_currency') != 'USD':
        raise ValueError('Only USD-base funds are supported by this shadow calculator')
    if snapshot.get('corporate_actions_reviewed') is not True:
        raise ValueError('Corporate-action effects on dated positions and accruals must be reviewed')
    for field in ('fund_id','positions_source','balances_source'):
        if not snapshot.get(field):
            raise ValueError(f'Missing {field}')
    shares = positive(snapshot.get('shares_outstanding'), 'shares_outstanding')
    if not isinstance(snapshot.get('positions'),list):
        raise ValueError('Explicit positions array required; an empty received array means cash-only')
    seen = set()
    for position in snapshot['positions']:
        for field in ('security_id','symbol','currency'):
            if not position.get(field):
                raise ValueError(f'Position missing {field}')
        if position.get('security_type') != 'equity':
            raise ValueError('Positions must be equities; cash belongs in balances')
        if position['security_id'] in seen:
            raise ValueError('Duplicate security_id; consolidate positions before valuation')
        seen.add(position['security_id'])
        positive(position.get('quantity'),position['security_id']+' quantity')
    balances = {k:decimal(snapshot.get('balances',{}).get(k),k) for k in ASSETS+LIABILITIES}
    return shares, balances


def value_shadow(snapshot, quotes):
    shares, balances = validate_snapshot(snapshot)
    if quotes.get('as_of') != snapshot['as_of']:
        raise ValueError('Quote set as_of does not match snapshot date')
    if not quotes.get('source') or not quotes.get('fetched_at'):
        raise ValueError('Quote source and fetched_at are required')
    fetched = datetime.fromisoformat(quotes['fetched_at'].replace('Z','+00:00'))
    if fetched.tzinfo is None:
        raise ValueError('Quote fetched_at must include a timezone')
    positions = {}
    for position in snapshot['positions']:
        symbol = position['symbol']
        quote = quotes.get('prices',{}).get(symbol)
        if quote is None:
            raise ValueError(f'Missing quote: {symbol}')
        if quote.get('date') != snapshot['as_of']:
            raise ValueError(f'Stale or mismatched quote: {symbol}')
        if quote.get('currency') != position['currency']:
            raise ValueError(f'Currency mismatch: {symbol}')
        if quote.get('price_basis') != 'as_of_share_units':
            raise ValueError(f'Unreviewed split/price basis: {symbol}')
        price = positive(quote.get('close'),symbol+' close')
        fx = positive(quote.get('fx_to_usd'),symbol+' FX')
        if position['currency'] == 'USD' and fx != 1:
            raise ValueError(f'USD FX must equal 1: {symbol}')
        if position['currency'] != 'USD' and (quote.get('fx_date') != snapshot['as_of'] or not quote.get('fx_source')):
            raise ValueError(f'Non-USD quote needs dated FX provenance: {symbol}')
        quantity = positive(position['quantity'],symbol+' quantity')
        positions[position['security_id']] = dict(symbol=symbol,currency=position['currency'],quantity=quantity,price=price,fx=fx,value=quantity*price*fx)
    securities = sum((p['value'] for p in positions.values()),D(0))
    assets = securities + sum((balances[k] for k in ASSETS),D(0))
    liabilities = sum((balances[k] for k in LIABILITIES),D(0))
    net = assets-liabilities
    if net <= 0:
        raise ValueError('Net assets must be positive; inspect the received balances')
    return dict(shares=shares,balances=balances,positions=positions,securities=securities,assets=assets,liabilities=liabilities,net_assets=net,nav=net/shares)


def compare(snapshot, quotes, provider=None, tolerance_bps='1'):
    shadow = value_shadow(snapshot, quotes)
    tolerance = decimal(tolerance_bps, 'tolerance_bps')
    report = dict(fund_id=snapshot['fund_id'],as_of=snapshot['as_of'],purpose='internal_shadow_only',
                  status='unavailable',shadow=shadow,provider=None,nav_difference=None,difference_bps=None,
                  breaks=[],tolerance_bps=tolerance,
                  limitations=['Snapshot comparison, not an accounting ledger or official NAV.',
                               'Operational positions, corporate actions, cash, accruals and capital activity require separate evidence.'])
    if provider is None:
        report['reason']='Provider NAV and accounting snapshot have not been supplied.'
        return report
    provider_shares, provider_balances = validate_snapshot(provider)
    if provider['fund_id'] != snapshot['fund_id'] or provider['as_of'] != snapshot['as_of']:
        raise ValueError('Provider fund/date does not match shadow snapshot')
    if not provider.get('provider_name'):
        raise ValueError('Independent provider_name is required')
    official = positive(provider.get('official_nav'), 'official_nav')
    official_net = positive(provider.get('net_assets'), 'provider net_assets')
    nav_decimals = provider.get('official_nav_decimals')
    if type(nav_decimals) is not int or not 0 <= nav_decimals <= 10:
        raise ValueError('Provider official_nav_decimals must specify the reporting precision (0–10)')
    nav_unit = D(1).scaleb(-nav_decimals)
    if official != official.quantize(nav_unit):
        raise ValueError('Provider official_nav exceeds its stated reporting precision')
    rounding_allowance = nav_unit / 2
    provider_positions = {}
    for p in provider['positions']:
        quantity = positive(p['quantity'],'provider quantity')
        price = positive(p.get('price'),'provider price')
        fx = positive(p.get('fx_to_usd'),'provider FX')
        if p['currency']=='USD' and fx != 1:
            raise ValueError('Provider USD FX must equal 1')
        provider_positions[p['security_id']] = dict(symbol=p['symbol'],currency=p['currency'],quantity=quantity,price=price,fx=fx,value=quantity*price*fx)
    bridge = D(0)
    for key in sorted(set(shadow['positions'])|set(provider_positions)):
        s,p = shadow['positions'].get(key),provider_positions.get(key)
        if s and p and (s['currency'] != p['currency'] or s['symbol'] != p['symbol']):
            raise ValueError(f'Security mapping differs for {key}')
        sp,pp = (s or p)['price'],(p or s)['price']
        sq,pq = (s or {}).get('quantity',D(0)),(p or {}).get('quantity',D(0))
        sf,pf = (s or p)['fx'],(p or s)['fx']
        effects = dict(quantity=(sq-pq)*pp*pf,price=sq*(sp-pp)*pf,fx=sq*sp*(sf-pf))
        delta = sum(effects.values(),D(0))
        bridge += delta
        report['breaks'].append(dict(security_id=key,symbol=(s or p)['symbol'],**effects,total=delta,
                                    position_status='both' if s and p else ('shadow_only' if s else 'provider_only')))
    balance_breaks = {}
    for key in ASSETS+LIABILITIES:
        sign=D(1) if key in ASSETS else D(-1)
        balance_breaks[key]=(shadow['balances'][key]-provider_balances[key])*sign
        bridge+=balance_breaks[key]
    reconstructed = sum((p['value'] for p in provider_positions.values()),D(0))+sum((provider_balances[k] for k in ASSETS),D(0))-sum((provider_balances[k] for k in LIABILITIES),D(0))
    residual = official_net-reconstructed
    nav_residual = official_net/provider_shares-official
    nav_difference = shadow['nav']-official
    bps = nav_difference/official*10000
    unrounded_provider_nav = official_net/provider_shares
    unrounded_difference = shadow['nav']-unrounded_provider_nav
    unrounded_bps = unrounded_difference/unrounded_provider_nav*10000
    # Attribution retains unmatched provider assets/rounding instead of hiding them.
    components = dict(position_and_balance_effect=bridge/shadow['shares'],
                      provider_net_asset_residual=-residual/shadow['shares'],
                      share_count_effect=official_net*(D(1)/shadow['shares']-D(1)/provider_shares),
                      provider_nav_rounding_or_residual=nav_residual)
    report.update(provider=dict(name=provider['provider_name'],official_nav=official,net_assets=official_net,
                                shares=provider_shares,reconstructed_net_assets=reconstructed,
                                unexplained_net_assets=residual,official_nav_decimals=nav_decimals,
                                nav_rounding_allowance=rounding_allowance,unrounded_nav=unrounded_provider_nav),
                  nav_difference=nav_difference,difference_bps=bps,balance_breaks=balance_breaks,
                  unrounded_nav_difference=unrounded_difference,unrounded_difference_bps=unrounded_bps,
                  nav_attribution=components,
                  attribution_residual=nav_difference-sum(components.values(),D(0)),
                  status='within_tolerance' if abs(unrounded_bps)<=tolerance else 'difference')
    if abs(residual)>D('.01') or abs(nav_residual)>rounding_allowance:
        report['status']='provider_data_inconsistent'
        report['reason']='Provider positions/balances/net assets/NAV do not reconcile within rounding tolerances.'
    return report


def fetch_yahoo(snapshot):
    """Explicit opt-in network operation. Never fetches fund accounting balances.

    Yahoo's historical Close can be split-adjusted even with auto_adjust=False.
    Refuse history with subsequent splits instead of silently mixing share bases.
    """
    import yfinance as yf
    validate_snapshot(snapshot)
    as_of = date.fromisoformat(snapshot['as_of'])
    today = datetime.now(timezone.utc).date()
    if as_of >= today:
        raise ValueError('Use a completed prior session, not an unfinished same-day quote')
    prices = {}
    for p in snapshot['positions']:
        if p['currency'] != 'USD':
            raise ValueError('Yahoo fetch currently supports USD quotations only; import reviewed dated FX for foreign listings')
        ticker = yf.Ticker(p['symbol'])
        hist = ticker.history(start=as_of.isoformat(),end=(today+timedelta(days=1)).isoformat(),
                              auto_adjust=False,back_adjust=False,actions=True,repair=False)
        if hist.empty:
            raise ValueError(f'Yahoo has no history for {p["symbol"]}')
        row = hist[[d.date()==as_of for d in hist.index]]
        if len(row) != 1:
            raise ValueError(f'No unique exact-session quote for {p["symbol"]} on {as_of}')
        if 'Stock Splits' not in hist:
            raise ValueError('Missing corporate-action split observations')
        later = hist[[d.date()>as_of for d in hist.index]]
        if (later['Stock Splits'] != 0).any():
            raise ValueError(f'Subsequent split affects historical share basis: {p["symbol"]}; use archived reviewed quotes')
        metadata = ticker.history_metadata
        if metadata.get('currency') != 'USD' or metadata.get('instrumentType') != 'EQUITY':
            raise ValueError(f'Unverified equity instrument or currency for {p["symbol"]}')
        close = positive(str(row['Close'].iloc[0]),p['symbol']+' Yahoo close')
        prices[p['symbol']] = dict(close=str(close),date=as_of.isoformat(),currency='USD',fx_to_usd='1',
                                  price_basis='as_of_share_units',subsequent_split_check='no split reported',
                                  exchange_timezone=metadata.get('exchangeTimezoneName'),
                                  exchange=metadata.get('exchangeName'))
    return dict(as_of=as_of.isoformat(),source='Yahoo via yfinance; non-authoritative research quotes',
                fetched_at=datetime.now(timezone.utc).isoformat(),prices=prices,
                auto_adjust=False,back_adjust=False,repair=False,
                note='Data rights and independent corporate-action/valuation review required; not public NAV.')


def encode(obj):
    return json.dumps(obj,default=lambda v:str(v) if isinstance(v,Decimal) else None,sort_keys=True,indent=2,allow_nan=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--quotes',type=Path)
    source.add_argument('--fetch-yahoo',action='store_true')
    parser.add_argument('--provider',type=Path)
    parser.add_argument('--tolerance-bps',default='1')
    parser.add_argument('--output',type=Path,default=Path('data/shadow_reports'))
    args=parser.parse_args()
    try:
        snapshot=json.loads(args.snapshot.read_text())
        quotes=fetch_yahoo(snapshot) if args.fetch_yahoo else json.loads(args.quotes.read_text())
        provider=json.loads(args.provider.read_text()) if args.provider else None
        report=compare(snapshot,quotes,provider,args.tolerance_bps)
        inputs=dict(snapshot=snapshot,quotes=quotes,provider=provider,tolerance_bps=args.tolerance_bps)
        engine_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        fingerprint=hashlib.sha256(encode(dict(engine_sha256=engine_sha,inputs=inputs)).encode()).hexdigest()
        report.update(evidence_sha256=fingerprint,engine_sha256=engine_sha,inputs=inputs,created_at=datetime.now(timezone.utc).isoformat())
        target=args.output/snapshot['as_of']/f'{fingerprint}.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        # Atomic and exclusive: repeated inputs preserve the first complete result.
        fd, tmp_name=tempfile.mkstemp(prefix='.shadow-',dir=target.parent)
        try:
            with os.fdopen(fd,'w') as handle: handle.write(encode(report)+'\n')
            try:
                os.link(tmp_name,target)
            except FileExistsError:
                pass
        finally:
            Path(tmp_name).unlink(missing_ok=True)
        print(f"{report['status']}: shadow NAV {report['shadow']['nav']:.6f}; report {target}")
    except Exception as exc:
        parser.exit(1,f'Shadow valuation failed; no successful comparison recorded. {exc}\n')


if __name__=='__main__':
    main()
