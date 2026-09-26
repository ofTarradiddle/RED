"""Dated issuer holdings and independent Yahoo observations. No balancing plugs.

The report is a public-holdings valuation, not SPY's unavailable general ledger.
All downloaded bytes and parsed observations are retained beside each report.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import math

from openpyxl import load_workbook
import requests

BASE = 'https://www.ssga.com/library-content/products/fund-data/etfs/us/'
SOURCES = {
    'holdings': BASE + 'holdings-daily-us-en-spy.xlsx',
    'nav': BASE + 'navhist-us-en-spy.xlsx',
    'distributions': BASE + 'spdr-etf-historical-distributions.xlsx',
}
ISSUER = 'https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy'
D = Decimal


def dec(value):
    v = D(str(value))
    if not v.is_finite():
        raise ValueError('Non-finite financial value')
    return v


def dated(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    for fmt in ('%d-%b-%Y', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Unsupported issuer date: {value}')


def rows(raw):
    book = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    try:
        return list(book.active.values)
    finally:
        book.close()


def parse_holdings(raw):
    data = rows(raw)
    if data[1][1] != 'SPY' or tuple(data[4][:8]) != ('Name', 'Ticker', 'Identifier', 'SEDOL', 'Weight', 'Sector', 'Shares Held', 'Local Currency'):
        raise ValueError('SPY holdings schema changed')
    as_of = dated(str(data[2][1]).removeprefix('As of '))
    holdings, seen = [], set()
    for r in data[5:]:
        if not r[2] or not isinstance(r[6], (int, float)):
            continue
        sid = str(r[2]); quantity = dec(r[6]); weight = dec(r[4]) / 100
        if sid in seen or quantity <= 0 or weight < 0 or r[7] != 'USD':
            raise ValueError(f'Invalid or unsupported issuer holding {sid}')
        seen.add(sid)
        cash = sid == '999USDZ92' and r[0] == 'US DOLLAR'
        # A CVR is not the similarly named company's common stock.
        kind = 'cash' if cash else 'corporate_action_right' if 'CVR' in str(r[0]) or sid == '436CVR021' else 'equity'
        holdings.append(dict(identifier=sid, ticker='CASH' if cash else str(r[1]),
                             yahoo_symbol=None if kind != 'equity' else str(r[1]).replace('.', '-'),
                             name=str(r[0]), sector='Unclassified' if r[5] == '-' else str(r[5]),
                             security_type=kind, currency='USD', quantity=str(quantity), issuer_weight=str(weight)))
    if not 490 <= sum(h['security_type'] == 'equity' for h in holdings) <= 520:
        raise ValueError('Unexpected SPY constituent count; retain prior release')
    if sum(h['security_type'] == 'cash' for h in holdings) != 1:
        raise ValueError('Expected one explicit USD cash position')
    return as_of, holdings


def parse_nav(raw):
    data = rows(raw)
    if data[1][1] != 'SPY' or tuple(data[3][:4]) != ('Date', 'NAV', 'Shares Outstanding', 'Total Net Assets'):
        raise ValueError('SPY NAV schema changed')
    result = {}
    for r in data[4:]:
        if not r[0] or not all(isinstance(v, (int, float)) for v in r[1:4]):
            continue
        day = dated(r[0]); nav, shares, assets = map(dec, r[1:4])
        if day < '2024-01-01':
            continue  # This exercise starts in 2024; older source rows stay archived.
        if min(nav, shares, assets) <= 0 or abs(assets / shares - nav) > D('.005001'):
            raise ValueError(f'Invalid issuer NAV record {day}')
        if day in result:
            raise ValueError('Duplicate issuer NAV date')
        result[day] = dict(date=day, nav=str(nav), shares_outstanding=str(shares), net_assets=str(assets))
    return result


def parse_distributions(raw):
    result = []
    for r in rows(raw)[1:]:
        if r[1] != 'SPY':
            continue
        amounts = [dec(str(v if v is not None else '').strip() or '0') for v in r[6:9]]
        result.append(dict(ex_date=dated(r[3]), record_date=dated(r[4]), payable_date=dated(r[5]),
                           income=str(amounts[0]), short_term_gain=str(amounts[1]), long_term_gain=str(amounts[2]),
                           per_share=str(sum(amounts))))
    return sorted(result, key=lambda r:r['ex_date'])


def fetch_yahoo_symbol(symbol, as_of):
    import yfinance as yf
    # A multi-day window avoids Yahoo dropping a boundary row for some symbols.
    target = date.fromisoformat(as_of)
    start = target - timedelta(days=40)
    end = datetime.now(timezone.utc).date() + timedelta(days=1)
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(start=start.isoformat(), end=end.isoformat(), auto_adjust=False,
                                 back_adjust=False, repair=False, actions=True, raise_errors=True, timeout=25)
        if not {'Close','Dividends','Stock Splits'}.issubset(history.columns):
            raise ValueError('Yahoo omitted required price/action columns')
        observations, actions = [], []
        for timestamp, row in history.iterrows():
            day = timestamp.date().isoformat()
            close = float(row['Close'])
            observations.append(dict(date=day, close=close if math.isfinite(close) else None))
            for column, kind in [('Dividends','dividend'), ('Stock Splits','split'), ('Capital Gains','capital_gain')]:
                amount = float(row.get(column, 0))
                if math.isfinite(amount) and amount:
                    actions.append(dict(symbol=symbol, date=day, type=kind, amount=str(amount),
                                        payable_date=None, status='Reference event; entitlement and payment require records'))
        exact = [r for r in observations if r['date'] == as_of and r['close'] is not None and r['close'] > 0]
        later_split = any(a['type'] == 'split' and a['date'] > as_of for a in actions)
        metadata = ticker.history_metadata or {}
        valid_currency = metadata.get('currency') == 'USD'
        valid_type = metadata.get('instrumentType') == ('ETF' if symbol == 'SPY' else 'EQUITY')
        error = None if len(exact) == 1 and not later_split and valid_currency and valid_type else 'Missing exact-date USD close, unexpected instrument, or subsequent split'
        return dict(symbol=symbol, date=as_of, close=str(exact[0]['close']) if not error else None,
                    currency=metadata.get('currency'), instrument_type=metadata.get('instrumentType'),
                    error=error, observations=observations, actions=actions)
    except Exception as exc:
        return dict(symbol=symbol, date=as_of, close=None, error=str(exc)[:300], observations=[], actions=[])


def make_report(as_of, holdings, official, quotes, distributions, manifest):
    positions, exceptions = [], []
    priced = cash = covered_issuer_value = unpriced_estimate = D(0)
    total_weight = priced_weight = D(0)
    for h in holdings:
        h = dict(h); quantity = dec(h['quantity']); weight = dec(h['issuer_weight'])
        h['issuer_implied_price'] = str(weight * dec(official['net_assets']) / quantity)
        h['issuer_implied_value'] = str(weight * dec(official['net_assets']))
        if h['security_type'] == 'cash':
            cash += quantity
            h.update(price='1', value=str(quantity), price_source='Issuer USD units', status='Reported cash')
        else:
            total_weight += weight
            q = quotes.get(h['yahoo_symbol'], {})
            price = q.get('close')
            if price is not None and q.get('date') == as_of and q.get('currency') == 'USD' and not q.get('error'):
                amount = quantity * dec(price); priced += amount; priced_weight += weight
                covered_issuer_value += dec(h['issuer_implied_value'])
                h.update(price=price, value=str(amount), price_source='Yahoo unadjusted Close', status='Priced')
            else:
                reason = q.get('error') or 'Corporate-action right: issuer/custodian fair value required'
                unpriced_estimate += dec(h['issuer_implied_value'])
                h.update(price=None, value=None, price_source=None, status=reason)
                exceptions.append(dict(identifier=h['identifier'], ticker=h['ticker'], reason=reason,
                                       issuer_weight=h['issuer_weight']))
        positions.append(h)
    subtotal = priced + cash
    shares = dec(official['shares_outstanding'])
    nav = dec(official['net_assets']) / shares
    actions = [a for q in quotes.values() for a in q['actions'] if a['date'] <= as_of and a['symbol'] != 'SPY']
    return dict(schema_version=1, as_of=as_of, source_fund='SPY', fetched_at=manifest['fetched_at'],
                official=official, positions=positions, exceptions=exceptions, actions=actions,
                distributions=[d for d in distributions if d['ex_date'] <= as_of][-12:],
                manifest=manifest, market_price=quotes.get('SPY', {}).get('close'),
                valuation=dict(priced_securities=str(priced), reported_cash=str(cash), known_assets=str(subtotal),
                               covered_issuer_implied_value=str(covered_issuer_value),
                               covered_price_effect=str(priced-covered_issuer_value),
                               covered_price_effect_bps=str((priced-covered_issuer_value)/dec(official['net_assets'])*10000),
                               unpriced_issuer_value_estimate=str(unpriced_estimate),
                               known_assets_per_share=str(subtotal/shares), official_nav_unrounded=str(nav),
                               raw_difference_per_share=str(subtotal/shares-nav),
                               raw_difference_bps=str((subtotal/dec(official['net_assets'])-1)*10000),
                               unexplained_net_balance=str(dec(official['net_assets'])-subtotal),
                               price_coverage=float(priced_weight / total_weight) if total_weight else 0,
                               status='Incomplete reconciliation', independent_nav=None,
                               missing_balances=['Underlying dividend receivables','Trade receivables/payables',
                                                 'Accrued expenses','Fund distributions payable','Other assets/liabilities']),
                accounting_note='Public holdings do not disclose actual executions, cost lots or operating balances. '
                                'The residual is unexplained, not cash. Yahoo events do not supply verified pay dates or merger/spinoff completeness.')


def refresh(output, source_dir=None, progress=print):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(timezone.utc).isoformat()
    run = output / 'runs' / fetched.replace(':','').replace('+','_')
    run.mkdir(parents=True, exist_ok=False)
    manifest = dict(fetched_at=fetched, issuer=ISSUER, files={}, engine_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    (run/'engine.py').write_bytes(Path(__file__).read_bytes())
    import yfinance as yf
    manifest['yfinance_version']=yf.__version__
    blobs = {}
    for key, url in SOURCES.items():
        if source_dir:
            raw = (Path(source_dir) / f'{key}.xlsx').read_bytes()
        else:
            response = requests.get(url, timeout=60)
            response.raise_for_status(); raw = response.content
        if not raw.startswith(b'PK'):
            raise ValueError(f'{key}: issuer did not return an XLSX')
        (run / f'{key}.xlsx').write_bytes(raw); blobs[key] = raw
        manifest['files'][key] = dict(url=url, sha256=sha256(raw).hexdigest())
    as_of, holdings = parse_holdings(blobs['holdings'])
    nav_history = parse_nav(blobs['nav'])
    from . import spy_reconcile as engine
    if as_of not in nav_history or datetime.now(timezone.utc).timestamp()<engine.session_details(as_of)[1]+900:
        raise ValueError('Need a completed, matching issuer holdings/NAV date')
    latest=nav_history[as_of]
    if abs(dec(latest['net_assets'])/dec(latest['shares_outstanding'])-dec(latest['nav']))>D('.000001'):
        raise ValueError('Latest precise NAV does not reconcile to issuer shares and net assets')
    # Staleness tolerates weekends/normal holiday closures, never a silent old sample.
    if (date.today() - date.fromisoformat(as_of)).days > 5:
        raise ValueError('Issuer snapshot is more than five calendar days old')
    distributions = parse_distributions(blobs['distributions'])
    # Retain the public daily inventory independently of the valuation inventory.
    # Bootstrap from committed public source evidence and existing local runs.
    archive=output/'holdings_archive/index.json'
    if not archive.exists():
        seed=Path(__file__).resolve().parents[2]/'data/spy_seed'
        for path in sorted(seed.glob('*.xlsx'))+sorted((output/'runs').glob('*/holdings.xlsx')):
            raw=path.read_bytes();day,_=parse_holdings(raw)
            engine.archive_holdings(output,raw,day,fetched)
    engine.archive_holdings(output,blobs['holdings'],as_of,fetched)
    try:
        inventory_date,inventory_raw,inventory_evidence=engine.select_inventory(output,nav_history,as_of)
    except ValueError as exc:
        if not str(exc).startswith('Awaiting archived holdings'):raise
        # Cold starts can publish current stock allocation while accumulating
        # the prior-session file needed for a future private NAV comparison.
        report=make_report(as_of,holdings,nav_history[as_of],{},distributions,manifest)
        report['publication_holdings']=holdings
        report['valuation']['status']='Awaiting prior-session holdings archive'
        report['warmup_note']=str(exc)
        report['run_directory']=str(run.resolve())
        text=json.dumps(report,indent=2,allow_nan=False);(run/'report.json').write_text(text)
        temporary=output/'latest.next.json';temporary.write_text(text);temporary.replace(output/'latest.json')
        progress(str(exc),flush=True)
        return report
    embedded_date,inventory=parse_holdings(inventory_raw)
    if embedded_date!=inventory_date:raise ValueError('Archived holdings embedded date mismatch')
    (run/'valuation-holdings.xlsx').write_bytes(inventory_raw)
    manifest['files']['valuation_holdings']=dict(url=SOURCES['holdings'],source_date=inventory_date,sha256=sha256(inventory_raw).hexdigest())
    source_issues=[]
    for key,url,filename in [('net_cash',ISSUER,'issuer.html'),('peer_valuation',engine.PEER_HOLDINGS,'peer.xlsx')]:
        if key=='peer_valuation' and not any(h['identifier']=='436CVR021' for h in inventory+holdings):continue
        if source_dir:
            raw=(Path(source_dir)/filename).read_bytes()
        else:
            try:
                response=requests.get(url,timeout=60);response.raise_for_status();raw=response.content
            except requests.RequestException as exc:
                if key!='peer_valuation':raise
                source_issues.append('Peer CVR valuation unavailable: '+str(exc)[:200]);continue
        (run/filename).write_bytes(raw);blobs[key]=raw
        manifest['files'][key]=dict(url=url,sha256=sha256(raw).hexdigest())
    net_cash=engine.parse_net_cash(blobs['net_cash'].decode())
    marks={}
    if 'peer_valuation' in blobs:
        try:marks=engine.parse_cvr_mark(blobs['peer_valuation'],as_of)
        except (ValueError,KeyError,IndexError) as exc:source_issues.append('Peer CVR mark requires review: '+str(exc)[:200])
    from .operating_book import retained_symbols
    retained=retained_symbols(output)
    symbols = sorted({h['yahoo_symbol'] for h in inventory+holdings if h['yahoo_symbol']} | retained | {'SPY'})
    quotes=engine.quote_all(symbols,as_of,run,output,progress)
    closing_evidence=engine.corroborate_peer_closes(quotes,blobs['peer_valuation'],inventory+holdings,as_of,run,output) if 'peer_valuation' in blobs else {}
    closing_evidence.update({s:q['closing_price_corroboration'] for s,q in quotes.items() if q.get('closing_price_corroboration')})
    quote_bytes = json.dumps(quotes, indent=2, allow_nan=False).encode()
    (run/'yahoo.json').write_bytes(quote_bytes)
    manifest['files']['yahoo'] = dict(source='Yahoo Finance chart API; raw share-basis closing observations',
                                    sha256=sha256(quote_bytes).hexdigest())
    report = make_report(as_of, inventory, nav_history[as_of], quotes, distributions, manifest)
    report['operating_quotes']={s:quotes[s] for s in retained if s in quotes}
    report['closing_price_corroboration']=closing_evidence
    report['publication_holdings']=holdings
    report['holdings_as_of']=inventory_date
    report['reconciliation']=engine.reconcile(inventory,quotes,nav_history[as_of],net_cash,inventory_date,as_of,marks)
    report['valuation_marks']=marks
    report['valuation_source_issues']=source_issues
    report['legacy_pricing_exceptions']=report['exceptions']
    report['exceptions']=[p for p in report['reconciliation']['positions'] if p['value'] is None]
    report['positions']=report['reconciliation']['positions']
    report['legacy_holdings_cash_diagnostic']=report.pop('valuation')
    report['valuation']=dict(status=report['reconciliation']['status'],
        price_coverage=1-len(report['exceptions'])/len(report['positions']),
        independent_nav=report['reconciliation']['calculated_nav'] if not report['reconciliation']['missing_security_ids'] else None)
    report['accounting_note']='Stock prices and the peer-fund CVR mark are independently sourced. The issuer net-cash aggregate is included once; detailed daily operating books and execution records are not supplied.'
    # Record an explicit counter-check; never change the fixed policy based on its result.
    report['same_date_inventory_countercheck']=engine.reconcile(holdings,quotes,nav_history[as_of],net_cash,as_of,as_of,marks)
    (run/'reconciliation-engine.py').write_bytes(Path(engine.__file__).read_bytes())
    manifest['reconciliation_engine_sha256']=sha256(Path(engine.__file__).read_bytes()).hexdigest()
    from .dividend_calendar import fetch_calendar,review_calendar
    calendar_path=output/'dividend-research/calendar.json'
    calendar=json.loads(calendar_path.read_text()) if calendar_path.exists() else None
    requested={s for s in symbols if s!='SPY'}
    if calendar is None or calendar.get('as_of')!=as_of or set(calendar['securities'])!=requested or (datetime.now(timezone.utc)-datetime.fromisoformat(calendar['fetched_at'])).total_seconds()>86400:
        calendar=fetch_calendar([s for s in symbols if s!='SPY'],output/'dividend-research',as_of,progress)
    report['dividend_calendar']=review_calendar(calendar,quotes,inventory,as_of)
    report['dividend_calendar_fetched_at']=calendar['fetched_at']
    report['dividend_source_coverage']=dict(requested=len(calendar['securities']),with_schedule=sum(bool(x['records']) for x in calendar['securities'].values()))
    report['dividend_source_issues']={s:d['issues'] for s,d in calendar['securities'].items() if d['issues']}
    report['official_history'] = [v for k,v in sorted(nav_history.items()) if k >= '2024-01-01']
    from .dividend_book import update as update_dividend_book
    update_dividend_book(report,output,progress=progress)
    from .operating_book import update as update_operating_book
    update_operating_book(report,output,progress=progress)
    report['run_directory'] = str(run.resolve())
    text = json.dumps(report, indent=2, allow_nan=False)
    (run/'report.json').write_text(text)
    # A partial report is useful and explicitly incomplete; public publication has its own gate.
    temporary = output/'latest.next.json'; temporary.write_text(text); temporary.replace(output/'latest.json')
    progress(f"SPY {as_of}: {report['valuation']['price_coverage']:.6%} price coverage; {len(report['exceptions'])} exceptions", flush=True)
    return report
