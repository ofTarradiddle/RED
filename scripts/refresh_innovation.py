#!/usr/bin/env python3
"""Refresh public innovation catalog, quoted return proxies and filed facts.

No fabricated observations, current valuation backfill, or synthetic pre-IPO
returns. A failed source retains its prior cache with explicit stale status.
"""
from __future__ import annotations
import argparse
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import hashlib
import gzip
import json
import math
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'innovation'
USER_AGENT = 'Hetzerk Innovation Research info@ofnectar.com'
TAGS = {'ResearchAndDevelopmentExpense':'USD','Revenues':'USD','RevenueFromContractWithCustomerExcludingAssessedTax':'USD','SalesRevenueNet':'USD','EarningsPerShareDiluted':'USD/shares'}


def read(path, fallback=None):
    try: return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_text())
    except (ValueError,OSError): return fallback


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    payload=(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
    temporary.write_bytes(gzip.compress(payload,compresslevel=6,mtime=0) if path.suffix=='.gz' else payload)
    temporary.replace(path)


def finite(value, positive=False):
    number=float(value)
    if not math.isfinite(number) or (positive and number<=0): raise ValueError('Invalid numeric observation')
    return number


def fetch_prices(asset):
    import yfinance as yf
    ticker=asset.get('ticker')
    if not ticker: return {**asset,'status':'unavailable','currency':'USD','points':[],'splits':[],'reason':'No verified continuous USD security identity mapped.'}
    security=yf.Ticker(ticker)
    frame=security.history(period='max',interval='1d',auto_adjust=False,actions=True,repair=False)
    meta=security.get_history_metadata()
    if meta.get('symbol','').upper()!=ticker or meta.get('currency')!='USD': raise ValueError('Unverified security identity or currency')
    if frame.empty or 'Adj Close' not in frame: raise ValueError('Missing adjusted price history')
    # Keep only completed sessions, including today's close after a buffer.
    now=datetime.now(timezone.utc)
    local_now=now.astimezone(ZoneInfo(meta.get('exchangeTimezoneName') or 'America/New_York'))
    close_epoch=meta.get('currentTradingPeriod',{}).get('regular',{}).get('end')
    close_time=datetime.fromtimestamp(close_epoch,tz=timezone.utc) if close_epoch else None
    points=[];splits=[]
    for stamp,row in frame.iterrows():
        d=stamp.date()
        if d<date(1960,1,1) or d>local_now.date(): continue
        if d==local_now.date() and (not close_time or close_time.astimezone(local_now.tzinfo).date()!=d or now<close_time+timedelta(minutes=5)):continue
        close=finite(row['Close'],True); adjusted=finite(row['Adj Close'],True)
        split=float(row.get('Stock Splits',0))
        if split and math.isfinite(split): splits.append({'date':d.isoformat(),'ratio':split})
        points.append({'date':d.isoformat(),'close':round(close,9),'adjustedClose':round(adjusted,9)})
    if not points or any(a['date']>=b['date'] for a,b in zip(points,points[1:])): raise ValueError('Invalid observation ordering')
    return {**asset,'currency':'USD','status':'ok','source':'Yahoo Finance','sourceUrl':f'https://finance.yahoo.com/quote/{ticker}/history/','retrievedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'points':points,'splits':splits}


def catalog_query(qid):
    return """SELECT ?item ?itemLabel ?rel WHERE {
      VALUES ?rel { wdt:P176 wdt:P178 } ?item ?rel wd:%s .
      ?item (wdt:P577|wdt:P571) ?date .
      FILTER(?date >= \"1960-01-01T00:00:00Z\"^^xsd:dateTime && ?date <= NOW())
      SERVICE wikibase:label { bd:serviceParam wikibase:language \"en,mul\". }
    }""" % qid


def fetch_catalog(asset):
    import requests
    def query(q):
        response=requests.get('https://query.wikidata.org/sparql',params={'query':q,'format':'json'},headers={'User-Agent':USER_AGENT,'Accept':'application/sparql-results+json'},timeout=45)
        response.raise_for_status();return response.json()['results']['bindings']
    rows=query(catalog_query(asset['wikidataId']))
    products={}
    for r in rows:
        qid=r['item']['value'].rsplit('/',1)[-1];title=r.get('itemLabel',{}).get('value',qid)
        if title==qid:continue
        role='Manufacturer' if r['rel']['value'].endswith('P176') else 'Developer'
        if qid not in products:products[qid]={'title':title,'roles':set()}
        products[qid]['roles'].add(role)
    dates={};ids=sorted(products)
    for offset in range(0,len(ids),100):
        selected=' '.join('wd:'+x for x in ids[offset:offset+100])
        for prop,meaning in [('P577','publication'),('P571','inception')]:
            q='SELECT ?item ?date ?precision WHERE { VALUES ?item { '+selected+' } ?item p:'+prop+'/psv:'+prop+' ?time . ?time wikibase:timeValue ?date ; wikibase:timePrecision ?precision . }'
            for r in query(q):
                qid=r['item']['value'].rsplit('/',1)[-1];iso=r['date']['value'].lstrip('+')[:10]
                try:parsed=date.fromisoformat(iso)
                except ValueError:continue
                precision=int(r['precision']['value'])
                if precision<9 or parsed.year<1960 or parsed>date.today():continue
                if qid not in dates or (iso,-precision)<(dates[qid][0],-dates[qid][1]):dates[qid]=(iso,precision,meaning)
    records=[]
    for qid,product in products.items():
        if qid not in dates:continue
        iso,precision,meaning=dates[qid];date_precision='day' if precision>=11 else 'month' if precision==10 else 'year'
        event=iso if date_precision=='day' else iso[:7] if date_precision=='month' else iso[:4]
        records.append({'id':qid+'-'+asset['id'],'wikidataId':qid,'assetId':asset['id'],'title':product['title'],'date':iso,'eventDate':event,'year':int(iso[:4]),'datePrecision':date_precision,'dateMeaning':meaning,'category':asset['category'],'kind':'product / software record','attributionRole':' / '.join(sorted(product['roles'])),'sourceUrl':'https://www.wikidata.org/wiki/'+qid,'reviewStatus':'catalog / not individually verified'})
    return sorted(records,key=lambda x:(x['date'],x['id']))


def fetch_facts(asset):
    import requests
    cik=asset.get('cik')
    if not cik:return {}
    response=requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',headers={'User-Agent':USER_AGENT},timeout=50)
    response.raise_for_status()
    data=response.json()
    if int(data.get('cik',-1))!=cik: raise ValueError('SEC issuer identity mismatch')
    facts=data.get('facts',{}).get('us-gaap',{})
    selected={}
    for tag,unit in TAGS.items():
        rows=[]
        for x in facts.get(tag,{}).get('units',{}).get(unit,[]):
            if x.get('form') not in ('10-K','10-K/A') or not x.get('start') or not x.get('end') or not x.get('filed'):continue
            days=(date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days
            if not 330<=days<=380:continue
            try: val=finite(x['val'])
            except (TypeError,ValueError):continue
            rows.append({k:x[k] for k in ('start','end','filed','accn','form','val')})
        selected[tag]=rows
    return {'cik':cik,'retrievedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'facts':selected}


def fact_at(facts,tag,decision):
    eligible=[x for x in facts.get('facts',{}).get(tag,[]) if x['filed']<decision and x['end']<decision]
    # A later comparative restatement is not available to earlier decision dates.
    # Reject accounting periods more than 18 months old.
    eligible=[x for x in eligible if (date.fromisoformat(decision)-date.fromisoformat(x['end'])).days<=550]
    return max(eligible,key=lambda x:(x['end'],x['filed'],x['accn'])) if eligible else None


def filing_url(cik,fact):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{fact['accn'].replace('-','')}/{fact['accn']}-index.html"


def financials(asset,facts,decision):
    by_date={p['date']:p for p in asset['points']};point=by_date.get(decision)
    if not point or not facts:return None,None
    eps=fact_at(facts,'EarningsPerShareDiluted',decision)
    valuation=None
    if eps:
        # Yahoo Close is adjusted for *all later splits*. Restore the closing
        # quote to the share units at the fiscal period-end of the filed EPS.
        # EPS is as reported in the selected filing, so later comparative
        # restatements may already incorporate intervening splits. Exclude those
        # ambiguous cases instead of guessing a unit conversion.
        ambiguous=any(eps['end']<s['date']<=eps['filed'] for s in asset.get('splits',[]))
        if not ambiguous:
            split_factor=math.prod(s['ratio'] for s in asset.get('splits',[]) if s['date']>eps['end'])
            quote_in_eps_units=point['close']*split_factor
            valuation={'pe':round(quote_in_eps_units/eps['val'],4) if eps['val']>0 else None,'ps':None,'pb':None,'asOf':decision,'availableAt':eps['filed'],'fiscalPeriodEnd':eps['end'],'dilutedEPS':eps['val'],'sourceUrl':filing_url(facts['cik'],eps),'label':'Price / latest filed full-year diluted EPS','note':'Historical quote translated to the reported EPS split basis; latest known annual earnings, not forward or current trailing-twelve-month earnings.' if eps['val']>0 else 'Annual diluted earnings were nonpositive; P/E is not meaningful.'}
    rd=fact_at(facts,'ResearchAndDevelopmentExpense',decision)
    revenues=[fact_at(facts,t,decision) for t in ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet')]
    revenues=[r for r in revenues if r and (not rd or r['end']==rd['end'] and r['start']==rd['start'])]
    revenue=max(revenues,key=lambda r:(r['end'],r['filed'])) if revenues else None
    investment=None
    if rd:
        investment={'rd':rd['val'],'revenue':revenue['val'] if revenue else None,'rdToSales':rd['val']/revenue['val'] if revenue and revenue['val']>0 else None,'availableAt':max(rd['filed'],revenue['filed'] if revenue else rd['filed']),'fiscalPeriodEnd':rd['end'],'sourceUrl':filing_url(facts['cik'],rd),'label':'Latest filed annual R&D','note':'Company-wide accounting expense; not spending attributable to this product. Missing custom tags are not treated as zero.'}
    return valuation,investment


def event_cutoff(event):
    text=event['eventDate']
    if len(text)==4:return text+'-12-31'
    if len(text)==7:
        y,m=map(int,text.split('-'));return (date(y+(m==12),1 if m==12 else m+1,1)-timedelta(days=1)).isoformat()
    return text


def build_dataset(assets,milestones,prices,catalogs,facts):
    market_calendar=sorted({p['date'] for a in prices.values() for p in a['points']})
    end=max(market_calendar) if market_calendar else date.today().isoformat()
    opportunities=[];execution_dates=set()
    for original in milestones:
        item=json.loads(json.dumps(original));cutoff=event_cutoff(item)
        item['originalDate']=item['eventDate'];item['eventDate']=cutoff
        cutoff=max(cutoff,item.get('informationAvailableAt',cutoff))
        own=prices.get(item['assetId'],{'points':[]});dates=[p['date'] for p in own['points']]
        # A verified stock close strictly after information was available. This
        # does not assume an announcement happened before the same day's close.
        i=bisect_right(dates,cutoff)
        candidate=dates[i] if i<len(dates) else None
        eligible=bool(candidate and (date.fromisoformat(candidate)-date.fromisoformat(cutoff)).days<=7)
        if not eligible:
            j=bisect_right(market_calendar,cutoff)
            candidate=market_calendar[j] if j<len(market_calendar) else end
        item['date']=candidate;item['canTrade']=eligible
        if not eligible:item['unavailableReason']='No verified contemporaneous public-share quote. No pre-IPO or missing history is manufactured.'
        item['year']=int(item['eventDate'][:4]);item['decision']['availableAt']=cutoff
        valuation,investment=financials(own,facts.get(item['assetId'],{}),candidate) if eligible else (None,None)
        item['decision']['valuation']=valuation;item['decision']['investment']=investment
        opportunities.append(item);execution_dates.add(candidate)
    opportunities.sort(key=lambda x:(x['date'],x['id']))
    output_assets=[]
    for source in assets:
        cached=prices.get(source['id'],{**source,'status':'unavailable','currency':'USD','points':[],'reason':'No verified continuous USD security identity mapped.'})
        cached={**cached,**source}
        daily=cached['points'];months={p['date'][:7]:p for p in daily}
        kept={p['date']:p for p in months.values()}
        for p in daily:
            if p['date'] in execution_dates:kept[p['date']]=p
        if daily:kept[daily[0]['date']]=daily[0]
        points=sorted(kept.values(),key=lambda p:p['date'])
        item={k:v for k,v in cached.items() if k not in ('splits','points','cik')}
        item['sourceUrls']=source.get('sourceUrls') or sorted({url for m in milestones if m['assetId']==source['id'] for url in m.get('sourceUrls',[])}) or ([f"https://www.wikidata.org/wiki/{source['wikidataId']}"] if source.get('wikidataId') else [])
        item.update(points=points,firstDate=points[0]['date'] if points else None,asOf=points[-1]['date'] if points else None,returnMethod='Yahoo dividend- and split-adjusted close ratio; vendor proxy, not an independently reconstructed shareholder cash-flow ledger.')
        output_assets.append(item)
    catalog=sorted([r for group in catalogs.values() for r in group.get('records',[])],key=lambda x:(x['date'],x['id']))
    generated=datetime.now(timezone.utc).isoformat(timespec='seconds')
    coverage={'curatedMilestones':len(opportunities),'catalogRecords':len(catalog),'uniqueCatalogItems':len({r['wikidataId'] for r in catalog}),'assets':len(output_assets),'quotedAssets':sum(bool(a['points']) for a in output_assets),'priceObservations':sum(len(a['points']) for a in output_assets),'dailySourceObservations':sum(len(a['points']) for a in prices.values()),'playableOpportunities':sum(o['canTrade'] for o in opportunities),'opportunitiesWithValuation':sum(o['decision']['valuation'] is not None for o in opportunities),'opportunitiesWithRD':sum(o['decision']['investment'] is not None for o in opportunities),'startYear':1960,'asOf':end,'catalogStatus':'ok' if catalogs and all(x.get('status')=='ok' for x in catalogs.values()) else 'partial','priceStatus':'ok' if all(a.get('status')=='ok' for a in output_assets if a.get('ticker')) else 'partial'}
    methodology={
      'returns':'Nominal USD shareholder-return proxy = adjusted close at end / adjusted close at start - 1. Yahoo adjusts for splits and cash distributions. No extra dividend or split multiplier is applied. Taxes, fees, transaction costs and inflation are excluded.',
      'sampling':'Month-end closes plus all game execution dates and each security’s first quote. Not interpolated daily data. A milestone is traded at the first verified close strictly after its announcement; year-only dates wait until after year end.',
      'causality':'Company returns include every business, valuation changes, macro conditions and later innovations. They are not an estimate of the causal payoff of an individual invention.',
      'financials':'Only annual SEC facts filed before the decision are eligible. P/E uses the latest available positive full-year diluted EPS and a historically consistent split basis. It is not forward P/E or necessarily trailing-twelve-month P/E. Missing values remain unknown.',
      'catalog':'Wikidata CC0 manufacturer/developer-linked records, with source date precision retained. Products, models and software releases are discovery records, not 1-for-1 validated inventions. Duplicate item/company records are consolidated. Corporate ownership at the event date is not independently reconstructed.',
      'selection':'A curated, survivorship-biased sample, not all major innovations or all investable firms. Delisted securities and many international share classes lack validated histories. A missing return is never a zero return. Later acquisitions, spinoffs and ADR changes may not be fully represented by the vendor proxy.',
      'game':'Educational, long-only, fractional holdings, $100 starting cash and zero cash interest. Familiar names and selected milestones create hindsight and selection advantages. Scores are not evidence of investment skill.',
      'availability':'Source dates describe historical events; editorial decision prompts reconstruct questions an investor might ask, not archival forecasts. Product catalog records are not automatically eligible game opportunities.',
      'rights':'Wikidata catalog metadata is CC0. Yahoo histories are development research data and require a suitable data license before a commercial redistribution service.'}
    payload={'schemaVersion':1,'id':'hetzerk-innovation-history','version':1,'generatedAt':generated,'asOf':end,'benchmarkAssetId':'SPY','coverage':coverage,'methodology':methodology,'assets':output_assets,'opportunities':opportunities,'catalog':catalog,'sources':[{'name':'Wikidata CC0 data access','url':'https://www.wikidata.org/wiki/Wikidata:Data_access'},{'name':'SEC EDGAR API documentation','url':'https://www.sec.gov/search-filings/edgar-application-programming-interfaces'},{'name':'Yahoo historical data adjustments','url':'https://help.yahoo.com/kb/SLN28256.html'}]}
    payload['version']=hashlib.sha256(json.dumps([output_assets,opportunities,catalog],sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    return payload


def validate_dataset(payload):
    """Fail closed on price, chronology, identity or point-in-time corruption."""
    if payload.get('schemaVersion')!=1:raise ValueError('Unknown innovation schema')
    assets={};today=datetime.now(timezone.utc).date().isoformat()
    for asset in payload['assets']:
        if asset['id'] in assets:raise ValueError('Duplicate asset')
        assets[asset['id']]=asset;previous=''
        for point in asset['points']:
            text=point['date']
            if date.fromisoformat(text).isoformat()!=text or text<=previous or text>today:raise ValueError('Invalid quote chronology')
            finite(point['close'],True);finite(point['adjustedClose'],True);previous=text
    seen=set();previous=''
    for event in payload['opportunities']:
        if event['id'] in seen or event['assetId'] not in assets:raise ValueError('Invalid opportunity identity')
        seen.add(event['id']);trade=event['date']
        if date.fromisoformat(trade).isoformat()!=trade or trade<previous:raise ValueError('Invalid opportunity ordering')
        if event['eventDate']>=trade:raise ValueError('Decision must follow historical information')
        if event['canTrade'] and trade not in {p['date'] for p in assets[event['assetId']]['points']}:raise ValueError('Trade lacks an exact observed quote')
        for key in ('valuation','investment'):
            fact=event['decision'].get(key)
            if fact and not fact['availableAt']<trade:raise ValueError('Future filing leaks into a decision')
        v=event['decision'].get('valuation')
        if v and v.get('pe') is not None:finite(v['pe'],True)
        previous=trade
    catalog_ids=set()
    for record in payload['catalog']:
        if record['id'] in catalog_ids or record['assetId'] not in assets:raise ValueError('Invalid catalog identity')
        if record['datePrecision'] not in ('year','month','day'):raise ValueError('Unknown date precision')
        catalog_ids.add(record['id'])
    if payload['coverage']['catalogRecords']!=len(catalog_ids):raise ValueError('Catalog count mismatch')
    if payload['coverage']['priceObservations']!=sum(len(a['points']) for a in assets.values()):raise ValueError('Quote count mismatch')
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Rebuild only from validated local caches')
    parser.add_argument('--skip-catalog',action='store_true')
    parser.add_argument('--skip-prices',action='store_true')
    parser.add_argument('--skip-facts',action='store_true')
    args=parser.parse_args()
    assets=read(DATA/'assets.json',[]);milestones=read(DATA/'milestones.json',[])
    prices=read(DATA/'price-cache.json.gz',{});catalogs=read(DATA/'catalog-cache.json',{});facts=read(DATA/'facts-cache.json',{})
    if not args.offline:
        for asset in ([] if args.skip_prices else assets):
            try:
                prices[asset['id']]=fetch_prices(asset)
                print('prices',asset['id'],len(prices[asset['id']]['points']),flush=True)
            except Exception as exc:
                previous=prices.get(asset['id'],{**asset,'points':[]})
                previous['status']='stale' if previous['points'] else 'unavailable';previous['reason']='Refresh failed ('+type(exc).__name__+'); no substitute prices.'
                prices[asset['id']]=previous;print('price failure',asset['id'],type(exc).__name__,flush=True)
            write(DATA/'price-cache.json.gz',prices)
        if not args.skip_catalog:
            candidates=[a for a in assets if a.get('wikidataId')]
            # Two concurrent bounded queries respect the public query service.
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs={pool.submit(fetch_catalog,a):a for a in candidates}
                for job in as_completed(jobs):
                    asset=jobs[job]
                    try:
                        records=job.result();catalogs[asset['id']]={'status':'ok','retrievedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'records':records};print('catalog',asset['id'],len(records),flush=True)
                    except Exception as exc:
                        previous=catalogs.get(asset['id'],{'records':[]});previous['status']='stale' if previous['records'] else 'unavailable';catalogs[asset['id']]=previous;print('catalog failure',asset['id'],type(exc).__name__,flush=True)
                    write(DATA/'catalog-cache.json',catalogs)
        if not args.skip_facts:
            needed={m['assetId'] for m in milestones if int(m['eventDate'][:4])>=2009}
            for asset in assets:
                if asset['id'] not in needed or not asset.get('cik'):continue
                try:facts[asset['id']]=fetch_facts(asset);print('facts',asset['id'],sum(len(v) for v in facts[asset['id']].get('facts',{}).values()),flush=True)
                except Exception as exc:print('facts failure',asset['id'],type(exc).__name__,flush=True)
                write(DATA/'facts-cache.json',facts);time.sleep(.15)
    payload=build_dataset(assets,milestones,prices,catalogs,facts)
    validate_dataset(payload)
    write(DATA/'dataset.json',payload)
    print(json.dumps(payload['coverage'],indent=2))
    if not payload['coverage']['priceObservations']:return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
