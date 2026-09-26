"""Public dividend schedules with explicit source, basis and confirmation status."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
from threading import Event

from bs4 import BeautifulSoup
import requests

D=Decimal
HEADERS={'User-Agent':'Mozilla/5.0','Accept':'application/json, text/plain, */*'}


def day(value):
    if not value or value in ('N/A','--','—'):return None
    for fmt in ('%m/%d/%Y','%Y-%m-%d'):
        try:return datetime.strptime(str(value).strip(),fmt).date().isoformat()
        except ValueError:pass
    raise ValueError(f'Unrecognized dividend date {value!r}')


def amount(value):
    v=D(str(value).replace('$','').replace(',','').strip())
    if not v.is_finite() or v<=0:raise ValueError('Invalid dividend amount')
    return str(v)


def parse_nasdaq(payload, symbol, url):
    data=payload.get('data')
    if not isinstance(data,dict):raise ValueError('Nasdaq returned no company data')
    section=data.get('dividends') or {}
    rows=section.get('rows')
    if rows is None:return [],str(section.get('message') or data.get('message') or 'No dividend history supplied; not evidence of zero dividends')
    records=[];issues=[]
    for row in rows:
        ex=day(row.get('exOrEffDate'));pay=day(row.get('paymentDate'))
        if not ex or not pay:continue
        if pay<ex:
            issues.append('Payment precedes ex-date; special distribution excluded pending review');continue
        records.append(dict(symbol=symbol,ex_date=ex,payable_date=pay,record_date=day(row.get('recordDate')),
                            declaration_date=day(row.get('declarationDate')),per_share=amount(row['amount']),
                            currency=row.get('currency'),type=row.get('type'),source='Nasdaq',source_url=url,
                            estimated=False,amount_basis='event_date_share_units',
                            declaration_status='Declared' if day(row.get('declarationDate')) else 'Reported schedule'))
    return records,'; '.join(issues) or None


def parse_dividendhistory(html, symbol, url):
    page=BeautifulSoup(html,'html.parser');table=page.select_one('#dividend-table')
    if not table:return [],'No dividend table supplied; not evidence of zero dividends'
    headers=[h.get_text(' ',strip=True) for h in table.select('thead th')]
    if headers[:3]!=['Ex-Dividend Date','Payout Date','Cash Amount']:
        raise ValueError('DividendHistory table schema changed')
    records=[]
    for row in table.select('tbody tr'):
        cells=[c.get_text(' ',strip=True) for c in row.select('td')]
        if len(cells)<4:continue
        estimated='unconfirmed-div' in row.get('class',[]) or bool(re.search(r'unconfirmed|estimated',cells[3],re.I))
        ex,pay=day(cells[0]),day(cells[1])
        if not ex or not pay:continue
        if pay<ex:continue # Do not treat special/due-bill schedules as ordinary.
        records.append(dict(symbol=symbol,ex_date=ex,payable_date=pay,record_date=None,declaration_date=None,
                            per_share=amount(cells[2]),currency='USD',type='Unclassified cash distribution',
                            source='DividendHistory.org',source_url=url,estimated=estimated,
                            amount_basis='split_adjusted_at_retrieval',
                            declaration_status='Estimated; not declared' if estimated else 'Reported; issuer confirmation not supplied'))
    return records,None


def parse_yahoo_schedule(payload,symbol,url):
    data=payload.get('quoteSummary',{}).get('result') or []
    if len(data)!=1:raise ValueError('Yahoo returned no calendar')
    def raw(value):return value.get('raw') if isinstance(value,dict) else value
    def utc_day(value):
        value=raw(value)
        return datetime.fromtimestamp(value,timezone.utc).date().isoformat() if value else None
    calendar=data[0].get('calendarEvents',{});stats=data[0].get('defaultKeyStatistics',{})
    ex=utc_day(calendar.get('exDividendDate'));pay=utc_day(calendar.get('dividendDate'))
    if not ex or not pay or pay<ex:return [],'No usable ordinary Yahoo payment schedule'
    last=utc_day(stats.get('lastDividendDate'));value=raw(stats.get('lastDividendValue'))
    per_share=amount(value) if last==ex and value else None
    return [dict(symbol=symbol,ex_date=ex,payable_date=pay,record_date=None,declaration_date=None,
                 per_share=per_share,currency='USD',type='Unclassified cash distribution',
                 source='Yahoo Finance calendar',source_url=url,estimated=False,
                 amount_basis='latest_event_share_units',declaration_status='Reported schedule',
                 amount_note=None if per_share else 'Latest dividend amount belongs to a different ex-date or is unavailable')],None


def fetch_one(symbol, folder, as_of, nasdaq_blocked=None):
    if not re.fullmatch(r'[A-Z0-9.-]+',symbol):raise ValueError('Invalid dividend symbol')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    files=[];errors=[];records=[]
    url=f'https://api.nasdaq.com/api/quote/{symbol}/dividends?assetclass=stocks'
    try:
        path=folder/f'{symbol}-nasdaq.json'
        fresh=path.exists() and datetime.now(timezone.utc).timestamp()-path.stat().st_mtime<86400
        if fresh:raw=path.read_bytes()
        else:
            if nasdaq_blocked is not None and nasdaq_blocked.is_set():raise ValueError('Provider rate limit; deferred until next refresh')
            response=requests.get(url,headers=HEADERS,timeout=25)
            if response.status_code in (403,429) and nasdaq_blocked is not None:nasdaq_blocked.set()
            response.raise_for_status();raw=response.content;path.write_bytes(raw)
        files.append(dict(source_url=url,file=path.name,sha256=sha256(raw).hexdigest()))
        records,issue=parse_nasdaq(json.loads(raw),symbol,url)
        if issue:errors.append(issue)
    except (requests.RequestException,ValueError,KeyError) as exc:errors.append('Nasdaq: '+str(exc)[:160])
    if not records and (folder/f'{symbol}-dividendhistory.html').exists():
        web_symbol=symbol.replace('-','.')
        url=f'https://dividendhistory.org/payout/{web_symbol}/'
        try:
            # Use already retrieved history. Bulk scraping stopped after the
            # provider rate-limited requests; never bypass or repeatedly retry it.
            path=folder/f'{symbol}-dividendhistory.html';raw=path.read_bytes()
            files.append(dict(source_url=url,file=path.name,sha256=sha256(raw).hexdigest()))
            records,issue=parse_dividendhistory(raw.decode(),symbol,url)
            for r in records:r['source_retrieved_at']=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()
            if issue:errors.append(issue)
        except (requests.RequestException,ValueError,KeyError) as exc:errors.append('DividendHistory: '+str(exc)[:160])
    if not records:
        url=f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=calendarEvents,defaultKeyStatistics&formatted=false'
        try:
            import yfinance as yf
            path=folder/f'{symbol}-yahoo-calendar.json'
            if path.exists() and datetime.now(timezone.utc).timestamp()-path.stat().st_mtime<86400:raw=path.read_bytes();payload=json.loads(raw)
            else:
                payload=yf.Ticker(symbol)._quote._fetch(['calendarEvents','defaultKeyStatistics'])
                raw=json.dumps(payload,allow_nan=False).encode();path.write_bytes(raw)
            files.append(dict(source_url=url,file=path.name,sha256=sha256(raw).hexdigest()))
            records,issue=parse_yahoo_schedule(payload,symbol,url)
            if issue:errors.append(issue)
        except Exception as exc:errors.append('Yahoo calendar: '+str(exc)[:160])
    target=date.fromisoformat(as_of)
    first=(target-timedelta(days=180)).isoformat();last=(target+timedelta(days=120)).isoformat()
    records=[r for r in records if first<=r['ex_date']<=last]
    return dict(symbol=symbol,records=records,issues=errors,files=files,
                status='Schedule retrieved' if records else 'No usable schedule; not a zero-dividend assertion')


def fetch_calendar(symbols, folder, as_of, progress=print):
    result={}
    nasdaq_blocked=Event()
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks={pool.submit(fetch_one,s,folder,as_of,nasdaq_blocked):s for s in sorted(set(symbols))}
        for future in as_completed(tasks):
            result[tasks[future]]=future.result()
            if len(result)%50==0:progress(f'Dividend schedules {len(result)}/{len(tasks)} checked',flush=True)
    output=dict(as_of=as_of,fetched_at=datetime.now(timezone.utc).isoformat(),securities=result)
    (Path(folder)/'calendar.json').write_text(json.dumps(output,indent=2,allow_nan=False))
    return output


def review_calendar(calendar, quotes, positions, as_of):
    quantities={p['yahoo_symbol']:D(p['quantity']) for p in positions if p.get('yahoo_symbol')}
    records=[]
    for symbol,data in calendar['securities'].items():
        observations=quotes.get(symbol,{}).get('actions',[])
        for raw in data['records']:
            r=dict(raw)
            ex=r['ex_date'];scheduled=D(r['per_share']) if r.get('per_share') else None
            yahoo=[a for a in observations if a['date']==ex and a['type']=='dividend']
            split_factor=D(1)
            for a in observations:
                if a['type']=='split' and ex<a['date']:
                    split_factor*=D(a['amount'])
            # A 1d/5d quote cannot establish the complete subsequent action
            # history. Corroborate only today's event; never assume that an old
            # event amount is on today's share basis.
            matched=ex==as_of and split_factor==1 and scheduled is not None and len(yahoo)==1 and abs(D(yahoo[0]['amount'])-scheduled)<=D('.000001')
            r['crosscheck']='Exact ex-date/amount agrees with Yahoo' if matched else 'Future declared event' if ex>as_of and r['declaration_status']=='Declared' else 'Not independently corroborated'
            r['status']='Estimated schedule — not accrued' if r['estimated'] else 'Upcoming ex-date' if ex>as_of else 'Ex-date passed; scheduled payment outstanding' if r['payable_date']>as_of else 'Scheduled payment date passed; receipt unconfirmed'
            # This is a cash-flow planning amount, not a posted receivable. Past
            # entitlements need historical positions and confirmed actions.
            r['current_position_quantity']=str(quantities.get(symbol,D(0)))
            r['cashflow_at_current_quantity']=str(quantities.get(symbol,D(0))*scheduled) if scheduled is not None and ex>=as_of else None
            r['cashflow_note']='Current-quantity scenario; future holdings/actions can change entitlement' if ex>=as_of else 'Historical entitlement and share-basis history required'
            r['booked_receivable']=None
            records.append(r)
    return sorted(records,key=lambda r:(r['payable_date'],r['symbol'],r['ex_date']))
