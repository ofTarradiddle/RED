"""Archive dividend/action histories separately from daily valuation quotes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import requests

D=Decimal
NY=ZoneInfo('America/New_York')


def event_day(epoch):
    return datetime.fromtimestamp(epoch,timezone.utc).astimezone(NY).date().isoformat()


def extract(payload,symbol,start,through):
    results=payload.get('chart',{}).get('result') or []
    if len(results)!=1:raise ValueError('No corporate-action history')
    result=results[0];meta=result['meta']
    if (meta.get('symbol'),meta.get('currency'),meta.get('instrumentType'))!=(symbol,'USD','EQUITY'):
        raise ValueError('Action-history security or currency mismatch')
    actions=[]
    for group,kind in [('dividends','dividend'),('splits','split'),('capitalGains','capital_gain')]:
        for item in result.get('events',{}).get(group,{}).values():
            day=event_day(item['date'])
            rate=D(str(item['numerator']))/D(str(item['denominator'])) if kind=='split' else D(str(item['amount']))
            if not rate.is_finite() or rate<=0:raise ValueError('Invalid action rate')
            if start<=day<=through:actions.append(dict(date=day,type=kind,amount=str(rate)))
    return dict(symbol=symbol,currency='USD',start=start,through=through,
                actions=sorted(actions,key=lambda a:(a['date'],a['type'])),error=None,
                coverage_note='Events returned for requested window; no-event response is not proof of a nonpayer')


def fetch_one(symbol,folder,as_of):
    if not re.fullmatch(r'[A-Z0-9.-]+',symbol):raise ValueError('Invalid symbol')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    start=(date.fromisoformat(as_of)-timedelta(days=200)).isoformat()
    through=datetime.now(timezone.utc).astimezone(NY).date().isoformat()
    first=int(datetime.fromisoformat(start).replace(tzinfo=NY).timestamp())
    end=int((datetime.fromisoformat(through)+timedelta(days=1)).replace(tzinfo=NY).timestamp())
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={first}&period2={end}&interval=1d&events=div,splits,capitalGains'
    raw_path=folder/f'{symbol}-{through}.json';meta_path=folder/f'{symbol}-{through}.source.json'
    try:
        if raw_path.exists() and meta_path.exists():
            raw=raw_path.read_bytes();evidence=json.loads(meta_path.read_text())
            if sha256(raw).hexdigest()!=evidence['sha256']:raise ValueError('Action source hash mismatch')
            if evidence['start']>start:raise ValueError('Cached action window too short')
        else:
            response=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=25);response.raise_for_status()
            raw=response.content
            # Validate before caching; malformed responses are not durable inputs.
            extract(response.json(),symbol,start,through)
            raw_path.write_bytes(raw)
            evidence=dict(url=url,sha256=sha256(raw).hexdigest(),start=start,through=through,
                          fetched_at=datetime.now(timezone.utc).isoformat(),file=raw_path.name)
            meta_path.write_text(json.dumps(evidence,indent=2))
        result=extract(json.loads(raw),symbol,start,through)
        result['evidence']=evidence;return result
    except (requests.RequestException,ValueError,KeyError,TypeError,ZeroDivisionError) as exc:
        return dict(symbol=symbol,start=start,through=through,actions=[],error=str(exc)[:240])


def fetch_histories(symbols,folder,as_of,progress=print):
    result={};symbols=sorted(set(symbols))
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(fetch_one,s,folder,as_of):s for s in symbols}
        for future in as_completed(tasks):
            result[tasks[future]]=future.result()
            if len(result)%100==0:progress(f'Dividend/action histories: {len(result)}/{len(symbols)}',flush=True)
    output=dict(as_of=as_of,fetched_at=datetime.now(timezone.utc).isoformat(),securities=result)
    path=Path(folder)/'latest.json';temporary=path.with_suffix('.next.json')
    temporary.write_text(json.dumps(output,indent=2,allow_nan=False));temporary.replace(path)
    return output


def event_rate(history,ex_date):
    """Restore Yahoo's split-adjusted dividend to the event-date share basis.

    Nonintegral adjustment factors can represent spin-offs. They need explicit
    issuer evidence rather than blindly treating every price factor as a split.
    """
    if not history or history.get('error'):return None,'Action history unavailable'
    events=[a for a in history['actions'] if a['type']=='dividend' and a['date']==ex_date]
    if len(events)!=1:return None,'No unique Yahoo dividend on this ex-date'
    factor=D(1)
    for a in history['actions']:
        if a['type']=='split' and a['date']>ex_date:
            ratio=D(a['amount']);inverse=1/ratio
            if ratio!=ratio.to_integral_value() and abs(inverse-inverse.to_integral_value())>D('.00000001'):
                return None,'Subsequent spin-off/complex share-basis adjustment requires issuer review'
            factor*=ratio
    return D(events[0]['amount'])*factor,None
