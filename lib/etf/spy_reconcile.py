"""SPY reconciliation using a fixed inventory-date policy and sourced net cash.

The inventory alignment is an observed feed convention, independently checked
against NAV; the engine never selects a date, cash balance or mark to fit NAV.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
import struct
from zoneinfo import ZoneInfo
from functools import lru_cache

from bs4 import BeautifulSoup
import requests

D=Decimal
NY=ZoneInfo('America/New_York')
ISSUER='https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy'
PEER_HOLDINGS='https://www.ssga.com/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spy5-gy.xlsx'
CVR_IDENTITY='https://www.sec.gov/Archives/edgar/data/714364/000071436426000005/xslForm13F_X02/Ogorek_Holdings_13F_2026Q2.xml'


@lru_cache(maxsize=64)
def session_details(target):
    import exchange_calendars as xcals
    calendar=xcals.get_calendar('XNYS')
    if not calendar.is_session(target):raise ValueError('Valuation date is not an XNYS session')
    return calendar.previous_session(target).date().isoformat(),calendar.session_close(target).timestamp()


def parse_cvr_mark(raw,target):
    from .daily_spy import rows, dated
    data=rows(raw)
    if data[1][1]!='IE00B6YX5C33' or dated(data[3][1])!=target:
        raise ValueError('Peer valuation must be the identified fund and same valuation date')
    headers=list(data[5]);records=[dict(zip(headers,r)) for r in data[6:] if len(r)>=len(headers)]
    rights=[r for r in records if r.get('Security Name')=='CONTRA HOLOGIC INCORPO' and r.get('Currency')=='USD']
    if len(rights)!=1:raise ValueError('Expected exactly one mapped Hologic contingent right')
    r=rights[0];price=D(str(r['Local Price']));quantity=D(str(r['Number of Shares']));value=D(str(r['Base Market Value']))
    if not all(x.is_finite() for x in (price,quantity,value)) or price<0 or quantity<=0 or abs(price*quantity-value)>D('.01'):raise ValueError('Peer price/value check failed')
    return {'436CVR021':dict(date=target,price=str(price),source_url=PEER_HOLDINGS,source_sha256=sha256(raw).hexdigest(),
                             identity_source_url=CVR_IDENTITY,source_name='State Street SPY5 published fair-value mark',
                             security_name='CONTRA HOLOGIC INCORPO',currency='USD',peer_quantity=str(quantity),peer_market_value=str(value))}


def parse_net_cash(html):
    page=BeautifulSoup(html,'html.parser')
    sections=[s for s in page.select('section') if s.find('h2') and 'Fund Net Cash Amount' in s.find('h2').get_text()]
    if len(sections)!=1:raise ValueError('Expected one dated issuer net-cash section')
    s=sections[0]; date_text=s.select_one('.date').get_text(' ',strip=True).removeprefix('as of ')
    day=datetime.strptime(date_text,'%b %d %Y').date().isoformat()
    value=D(s.select_one('td.data').get_text(strip=True).replace('$','').replace(',',''))
    if not value.is_finite():raise ValueError('Nonfinite net cash')
    return dict(date=day,amount=str(value),source_url=ISSUER,label='Issuer-reported aggregate Net Cash Amount')


def local_date(timestamp):
    return datetime.fromtimestamp(timestamp,timezone.utc).astimezone(NY).date().isoformat()


def extract_chart(payload,symbol,as_of,url,closing_mark=None):
    _,session_close=session_details(as_of)
    results=payload.get('chart',{}).get('result')
    if not results or len(results)!=1:raise ValueError('Yahoo returned no chart')
    result=results[0];meta=result['meta']
    if meta.get('symbol')!=symbol or meta.get('currency')!='USD' or meta.get('instrumentType')!=('ETF' if symbol=='SPY' else 'EQUITY'):
        raise ValueError('Yahoo symbol, currency or instrument mismatch')
    prices=result['indicators']['quote'][0]['close'];timestamps=result.get('timestamp',[])
    observations=[(stamp,p) for stamp,p in zip(timestamps,prices) if local_date(stamp)==as_of and p is not None]
    if len(observations)!=1:raise ValueError('Missing or duplicate exact-date closing bar')
    stamp,raw=observations[0];close=D(str(raw))
    if not close.is_finite() or close<=0:raise ValueError('Invalid close')
    if datetime.now(timezone.utc).timestamp()<session_close+900:
        raise ValueError('Use a completed trading session after the closing grace period')
    field='indicators.quote[0].close';precision_note='Historical chart precision'
    market_time=meta.get('regularMarketTime');quoted=meta.get('regularMarketPrice')
    if market_time and quoted is not None and local_date(market_time)==as_of:
        decimal=D(str(quoted))
        if not decimal.is_finite():raise ValueError('Invalid metadata price')
        closing_quote=session_close<=market_time<=session_close+900
        # Preserve provider decimal precision, including valid half-cent prints.
        # The independently supplied closing bar must corroborate the float32
        # representation. Never substitute dividend-adjusted previousClose.
        encoded=struct.unpack('f',struct.pack('f',float(decimal)))[0]
        if closing_quote and decimal>0 and abs(float(raw)-encoded)<=1e-9:
            close=decimal;field='meta.regularMarketPrice';precision_note='Same-session decimal quote corroborated by daily float32 close'
        elif closing_quote and abs(float(raw)-float(decimal))>max(abs(float(raw))*2**-23,1e-6):
            rounded=decimal.quantize(D('.01'),rounding=ROUND_HALF_UP)
            encoded_cent=struct.unpack('f',struct.pack('f',float(rounded)))[0]
            confirmed=(closing_mark and closing_mark.get('symbol')==symbol and closing_mark.get('date')==as_of
                       and closing_mark.get('currency')=='USD' and D(closing_mark['price'])==decimal
                       and closing_mark.get('identifier') and closing_mark.get('source_sha256')
                       and closing_mark.get('source_url')==PEER_HOLDINGS)
            if confirmed and abs(float(raw)-encoded_cent)<=1e-9:
                close=decimal;field='meta.regularMarketPrice'
                precision_note='Fractional-cent Yahoo closing quote corroborated by same-date identified SPY5 holding; chart bar rounded to cents'
            else:
                raise ValueError('Daily bar and same-session metadata disagree; source precision requires review')
    actions=[]
    for group,kind in [('dividends','dividend'),('splits','split')]:
        for event in result.get('events',{}).get(group,{}).values():
            ratio=D(str(event['numerator']))/D(str(event['denominator'])) if kind=='split' else D(str(event['amount']))
            actions.append(dict(symbol=symbol,date=local_date(event['date']),type=kind,amount=str(ratio),payable_date=None))
    if any(a['type']=='split' and a['date']>as_of for a in actions):
        raise ValueError('Subsequent split requires an archived share-basis price')
    return dict(symbol=symbol,date=as_of,close=str(close),currency='USD',instrument_type=meta['instrumentType'],
                error=None,actions=actions,source_url=url,source_field=field,precision_note=precision_note,
                bar_timestamp=stamp,regular_market_time=market_time,raw_daily_close=str(raw),
                observations=[dict(date=as_of,close=float(close))])


def corroborate_peer_closes(quotes,raw_peer,positions,target,run,output=None):
    """Resolve only exact cent-rounding conflicts with independent dated marks.

    This never uses SPY NAV, weights or market-value-implied stock prices.
    Uncorroborated discrepancies retain their original quote exception.
    """
    from .daily_spy import rows,dated
    data=rows(raw_peer)
    if data[1][1]!='IE00B6YX5C33' or dated(data[3][1])!=target:
        return {}
    headers=list(data[5])
    identities={p['yahoo_symbol']:p['identifier'] for p in positions if p.get('yahoo_symbol')}
    records=[dict(zip(headers,row)) for row in data[6:] if len(row)>=len(headers)]
    evidence={}
    for symbol,q in list(quotes.items()):
        if 'Daily bar and same-session metadata disagree' not in (q.get('error') or ''):continue
        identifier=identities.get(symbol)
        candidates=[r for r in records if str(r.get('ISIN',''))[2:-1]==identifier and r.get('Currency')=='USD']
        if len(candidates)!=1:continue
        r=candidates[0];price=D(str(r['Local Price']))
        if not price.is_finite() or price<=0:continue
        mark=dict(symbol=symbol,identifier=identifier,isin=r['ISIN'],currency='USD',date=target,
                  price=str(price),source_url=PEER_HOLDINGS,source_sha256=sha256(raw_peer).hexdigest(),field='Local Price')
        for window in ('1d','5d'):
            path=Path(run)/'quote_sources'/f'{symbol}-{window}.json'
            if not path.exists():continue
            raw=path.read_bytes()
            url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={window}&interval=1d&events=div,splits'
            try:
                checked=extract_chart(json.loads(raw),symbol,target,url,mark)
            except (ValueError,KeyError,TypeError):continue
            checked.update(source_sha256=sha256(raw).hexdigest(),source_file=str(path.relative_to(run)),closing_price_corroboration=mark)
            quotes[symbol]=checked;evidence[symbol]=mark
            if output is not None:
                archive=Path(output)/'quote_archive'/target;archive.mkdir(parents=True,exist_ok=True)
                (archive/f'{symbol}-raw.json').write_bytes(raw)
                (archive/f'{symbol}-peer.xlsx').write_bytes(raw_peer)
                (archive/f'{symbol}.json').write_text(json.dumps(checked,indent=2))
            break
    return evidence


def fetch_quote(symbol,as_of,run):
    errors=[]
    for window in ('1d','5d'):
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={window}&interval=1d&events=div,splits'
        try:
            response=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=25);response.raise_for_status()
            raw=response.content;path=Path(run)/'quote_sources'/f'{symbol}-{window}.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            q=extract_chart(response.json(),symbol,as_of,url)
            q['source_sha256']=sha256(raw).hexdigest();q['source_file']=str(path.relative_to(run));return q
        except (requests.RequestException,ValueError,KeyError,TypeError) as exc:errors.append(str(exc)[:180])
    return dict(symbol=symbol,date=as_of,close=None,error='; '.join(errors),actions=[],observations=[])


def archive_holdings(output,raw,as_of,fetched_at):
    folder=Path(output)/'holdings_archive';folder.mkdir(parents=True,exist_ok=True)
    digest=sha256(raw).hexdigest();name=f'{as_of}-{digest[:16]}.xlsx'
    (folder/name).write_bytes(raw)
    index_path=folder/'index.json';index=json.loads(index_path.read_text()) if index_path.exists() else {}
    index[as_of]=dict(file=name,sha256=digest,fetched_at=fetched_at)
    temp=index_path.with_suffix('.next.json');temp.write_text(json.dumps(index,indent=2));temp.replace(index_path)
    return index


def select_inventory(output,nav_history,target):
    # Fixed policy, not a search for whichever portfolio minimizes the difference.
    previous,_=session_details(target)
    if previous not in nav_history:raise ValueError(f'Missing required prior-session NAV row: {previous}')
    index_path=Path(output)/'holdings_archive/index.json'
    index=json.loads(index_path.read_text()) if index_path.exists() else {}
    if previous not in index:raise ValueError(f'Awaiting archived holdings dated {previous} for the {target} valuation; run daily to retain the prior session')
    item=index[previous];path=index_path.parent/item['file'];raw=path.read_bytes()
    if sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Archived holdings hash mismatch')
    return previous,raw,item


def quote_all(symbols,as_of,run,output,progress=print):
    archive=Path(output)/'quote_archive'/as_of;archive.mkdir(parents=True,exist_ok=True)
    quotes={};pending=[]
    for s in sorted(set(symbols)):
        path=archive/f'{s}.json'
        if path.exists():
            q=json.loads(path.read_text())
            source=archive/f'{s}-raw.json'
            if q.get('date')==as_of and q.get('close') and q.get('source_sha256') and not q.get('error') and source.exists():
                raw=source.read_bytes()
                if sha256(raw).hexdigest()!=q['source_sha256']:raise ValueError(f'{s}: cached quote evidence hash mismatch')
                mark=q.get('closing_price_corroboration')
                if mark:
                    from .daily_spy import rows,dated
                    peer_raw=(archive/f'{s}-peer.xlsx').read_bytes()
                    if sha256(peer_raw).hexdigest()!=mark['source_sha256']:raise ValueError('Cached corroborating price evidence hash mismatch')
                    data=rows(peer_raw);headers=list(data[5])
                    matches=[dict(zip(headers,row)) for row in data[6:] if len(row)>=len(headers) and str(row[0])==mark['isin']]
                    if data[1][1]!='IE00B6YX5C33' or dated(data[3][1])!=as_of or mark['isin'][2:-1]!=mark['identifier'] or len(matches)!=1 or matches[0].get('Currency')!='USD' or D(str(matches[0]['Local Price']))!=D(mark['price']):
                        raise ValueError('Cached corroborating price identity/date/value mismatch')
                checked=extract_chart(json.loads(raw),s,as_of,q['source_url'],mark)
                if checked['close']!=q['close']:raise ValueError(f'{s}: cached price differs from source')
                target=Path(run)/'quote_sources'/f'{s}-cached.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                checked.update(source_sha256=q['source_sha256'],source_file=str(target.relative_to(run)))
                if mark:
                    checked['closing_price_corroboration']=mark
                    (target.parent/f'{s}-peer.xlsx').write_bytes(peer_raw)
                quotes[s]=checked;continue
        pending.append(s)
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks={pool.submit(fetch_quote,s,as_of,run):s for s in pending}
        for future in as_completed(tasks):
            s=tasks[future];q=future.result();quotes[s]=q
            if not q.get('error'):
                # Cache successful dated observations, retaining original evidence.
                source=Path(run)/q['source_file'];source_target=archive/f'{s}-raw.json';source_target.write_bytes(source.read_bytes())
                q['archived_source_file']=str(source_target.resolve())
                (archive/f'{s}.json').write_text(json.dumps(q,indent=2))
            if len(quotes)%50==0:progress(f'Yahoo {len(quotes)}/{len(set(symbols))} dated closing prices ready',flush=True)
    return quotes


def reconcile(holdings,quotes,official,net_cash,holdings_date,valuation_date,marks=None):
    if net_cash['date']!=valuation_date:raise ValueError('Net-cash and NAV dates differ')
    if official.get('date')!=valuation_date:raise ValueError('Official NAV date mismatch')
    for field in ('shares_outstanding','net_assets','nav'):
        value=D(official[field])
        if not value.is_finite() or value<=0:raise ValueError('Invalid official NAV input')
    if not D(net_cash['amount']).is_finite():raise ValueError('Invalid net cash')
    marks=marks or {};equities=D(0);rights=D(0);missing=[];positions=[]
    seen=set()
    for h in holdings:
        if h['identifier'] in seen:raise ValueError('Duplicate security')
        seen.add(h['identifier'])
        if h.get('currency')!='USD' or not D(h['quantity']).is_finite() or D(h['quantity'])<=0:raise ValueError('Invalid holding currency/quantity')
        if h['security_type']=='cash':continue # Net cash already aggregates nonsecurity items.
        p=dict(h);price=None;source=None
        if h['security_type']=='equity':
            q=quotes.get(h['yahoo_symbol'],{})
            if q.get('date')==valuation_date and q.get('currency')=='USD' and q.get('symbol')==h['yahoo_symbol'] and q.get('instrument_type')=='EQUITY' and not q.get('error') and q.get('close'):
                price=D(q['close']);source=q.get('source_url');p['source_field']=q.get('source_field')
        elif h['identifier'] in marks:
            mark=marks[h['identifier']]
            if mark['date']==valuation_date and mark.get('currency')=='USD' and mark.get('identity_source_url') and mark.get('source_url') and mark.get('source_sha256'):
                price=D(mark['price']);source=mark['source_url'];p['source_field']='Independent published fair-value mark'
        if price is not None and (not price.is_finite() or price<0 or (h['security_type']=='equity' and price==0)):
            raise ValueError('Invalid security price')
        value=D(h['quantity'])*price if price is not None else None
        if value is None:missing.append(h['identifier'])
        elif h['security_type']=='equity':equities+=value
        else:rights+=value
        p.update(price=str(price) if price is not None else None,value=str(value) if value is not None else None,price_source=source)
        positions.append(p)
    known=equities+rights+D(net_cash['amount']);shares=D(official['shares_outstanding'])
    nav=known/shares;official_nav=D(official['net_assets'])/shares;gap=known-D(official['net_assets'])
    same_cent=nav.quantize(D('.01'),rounding=ROUND_HALF_UP)==official_nav.quantize(D('.01'),rounding=ROUND_HALF_UP)
    no_equity_gaps=not any(p['security_type']=='equity' and p['value'] is None for p in positions)
    return dict(holdings_as_of=holdings_date,valuation_date=valuation_date,
                alignment_policy='Previous NAV-session holdings, current-session prices/shares/net cash; observed alignment, issuer timing contract unconfirmed',
                positions=positions,priced_equities=str(equities),priced_rights=str(rights),net_cash=net_cash,
                known_net_assets=str(known),shares=str(shares),calculated_nav=str(nav),official_nav=str(official_nav),
                difference_dollars=str(gap),difference_per_share=str(nav-official_nav),difference_bps=str(gap/D(official['net_assets'])*10000),
                matches_published_cent=same_cent and no_equity_gaps,missing_security_ids=missing,
                status='Matched to published NAV' if same_cent and not missing else 'Matches published cent; fair-value exception remains' if same_cent and no_equity_gaps else 'Difference to investigate',
                accounting_scope='Constituents independently repriced; issuer net-cash aggregate used once. Detailed daily cash ledger is not independently replayed.')
