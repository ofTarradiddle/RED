#!/usr/bin/env python3
"""Point-in-time annual investment evidence from SEC EDGAR.

Public cards preserve original accession/filing dates. Raw filing caches never
enter the website. Narrative snippets are short, automated evidence pointers,
not an inferred investment thesis or a causal attribution of shareholder return.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/annual-filings'
OUTPUT = ROOT / 'data/annual-game/filings.json'
USER_AGENT = 'Hetzerk Innovation Research info@ofnectar.com'
METRICS = {
 'rd': (['ResearchAndDevelopmentExpense'], 'USD', 'duration'),
 'capex': (['PaymentsToAcquirePropertyPlantAndEquipment'], 'USD', 'duration'),
 'acquisitions': (['PaymentsToAcquireBusinessesNetOfCashAcquired','PaymentsToAcquireBusinessesGross'], 'USD', 'duration'),
 'revenue': (['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenuesNetOfInterestExpense'], 'USD', 'duration'),
 'netIncome': (['NetIncomeLoss','ProfitLoss'], 'USD', 'duration'),
 'operatingCashFlow': (['NetCashProvidedByUsedInOperatingActivities'], 'USD', 'duration'),
 'assets': (['Assets'], 'USD', 'instant'),
 'equity': (['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'], 'USD', 'instant'),
 'epsDiluted': (['EarningsPerShareDiluted'], 'USD/shares', 'duration'),
}
THEMES = [
 ('Research & development', re.compile(r'research\s+and\s+development|research\s*&\s*development|product\s+development', re.I)),
 ('Capital investment', re.compile(r'capital\s+(?:expenditures|investment|spending)|manufacturing\s+(?:capacity|facilities)|new\s+(?:facilities|plants|stores)', re.I)),
 ('Acquisitions', re.compile(r'(?:strategic|business)\s+acquisitions|acquisitions?\s+(?:of|and)|acquired\s+(?:the|a)\s+(?:business|company)', re.I)),
 ('Technology & infrastructure', re.compile(r'invest\w*\s+(?:in|into)\s+(?:our\s+)?(?:technology|infrastructure|software|digital)|data\s+centers|cloud\s+computing', re.I)),
 ('Products & expansion', re.compile(r'new\s+products|product\s+innovation|expand\w*\s+(?:our|the)\s+(?:business|capacity|operations|market)', re.I)),
]
FOCUS_AREAS = [
 ('Cloud services', r'cloud\s+(?:computing|services|infrastructure)'),
 ('Data centers', r'data\s+centers?'),
 ('Artificial intelligence', r'artificial\s+intelligence|machine\s+learning'),
 ('Mobile devices', r'smartphones?|mobile\s+(?:devices|phones)|iPhone|iPad'),
 ('Semiconductors', r'semiconductors?|chip\s+(?:design|manufacturing)|graphics\s+processors?'),
 ('Software platforms', r'software\s+(?:platforms?|development|applications?)'),
 ('New medicines', r'drug\s+(?:development|discovery)|clinical\s+(?:trials|development)|pharmaceutical\s+research'),
 ('Manufacturing capacity', r'manufacturing\s+(?:capacity|facilities|plants)|production\s+capacity'),
 ('Stores and distribution', r'new\s+stores|store\s+(?:openings|expansion)|distribution\s+centers'),
 ('Energy exploration', r'exploration\s+and\s+production|drilling\s+(?:activities|program|wells)'),
 ('Pipelines and transport', r'pipeline\s+(?:construction|projects|expansion)|transportation\s+infrastructure'),
 ('Renewable energy', r'renewable\s+energy|solar\s+(?:energy|power|projects)|wind\s+(?:power|projects|farms)'),
 ('Networks and connectivity', r'network\s+(?:infrastructure|expansion|capacity)|wireless\s+(?:networks|infrastructure)'),
 ('Electric vehicles', r'electric\s+vehicles|battery\s+(?:technology|production|manufacturing)'),
 ('Content and media', r'original\s+content|content\s+(?:production|acquisition)|streaming\s+(?:services|content)'),
]
_lock = threading.Lock()
_next_request = 0.0
_local = threading.local()
_REFRESH_METADATA = False


def load(path, default=None):
    try:
        data=path.read_bytes()
        if path.suffix == '.gz': data=gzip.decompress(data)
        return json.loads(data)
    except (OSError, ValueError): return default


def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(gzip.compress(raw,mtime=0) if path.suffix=='.gz' else raw)
    temporary.replace(path)


def request(url):
    import requests
    global _next_request
    if not hasattr(_local,'session'):
        _local.session=requests.Session()
        _local.session.headers.update({'User-Agent':USER_AGENT,'Accept-Encoding':'gzip, deflate'})
    for attempt in range(3):
        with _lock:
            delay=max(0,_next_request-time.monotonic())
            _next_request=max(_next_request,time.monotonic())+.16
        if delay: time.sleep(delay)
        try:
            response=_local.session.get(url,timeout=(15,65))
        except requests.RequestException:
            if attempt<2:
                time.sleep(2**(attempt+1));continue
            raise
        if response.status_code in (429,500,502,503,504):
            if attempt<2:
                time.sleep(2**(attempt+1));continue
        response.raise_for_status()
        return response
    raise RuntimeError('SEC response unavailable')


def cached_json(path,url,offline=False,refresh=False):
    cached=load(path)
    if cached is not None and (offline or not refresh):return cached
    if offline: raise ValueError('SEC metadata is not cached')
    try:
        result=request(url).json();save(path,result);return result
    except Exception as error:
        if cached is None:raise
        # Preserve already dated evidence if an incremental network refresh
        # fails. Surface the stale refresh separately; never erase old facts.
        if not hasattr(_local,'refresh_warnings'):_local.refresh_warnings=[]
        _local.refresh_warnings.append(f'Cached metadata retained after refresh failure: {url}: {type(error).__name__}')
        return cached


def iso(value):
    try:return isinstance(value,str) and len(value)==10 and date.fromisoformat(value).isoformat()==value
    except ValueError:return False


def filing_url(cik,accession,document=None):
    directory=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/'
    return directory+(document if document else accession+'-index.html')


def submission_rows(columns):
    output=[]
    for i, accession in enumerate(columns.get('accessionNumber',[])):
        row={key: values[i] for key,values in columns.items() if isinstance(values,list) and len(values)>i}
        if row.get('form') in ('10-K','10-K/A','20-F','20-F/A','40-F','40-F/A'):
            if iso(row.get('filingDate')) and re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession):output.append(row)
    return output


def issuer_metadata(cik,offline=False):
    folder=CACHE/str(cik)
    primary=cached_json(folder/'submissions.json.gz',f'https://data.sec.gov/submissions/CIK{cik:010d}.json',offline,_REFRESH_METADATA)
    if int(primary.get('cik',-1))!=cik:raise ValueError('SEC submission CIK mismatch')
    rows=submission_rows(primary.get('filings',{}).get('recent',{}))
    for part in primary.get('filings',{}).get('files',[]):
        if part.get('filingTo','')<'2009-01-01':continue
        name=part['name']
        if not re.fullmatch(r'CIK\d{10}-submissions-\d+\.json',name):continue
        more=cached_json(folder/name.replace('.json','.json.gz'),'https://data.sec.gov/submissions/'+name,offline,_REFRESH_METADATA)
        rows.extend(submission_rows(more))
    return primary, sorted({row['accessionNumber']:row for row in rows}.values(),key=lambda r:(r['filingDate'],r['accessionNumber']))


def select_report(rows,cutoff):
    # A late amendment may only contain an auditor/signature change; original
    # annual narrative remains the report, while numeric amendments are eligible
    # separately only after their actual filing date.
    eligible=[r for r in rows if r['filingDate']<=cutoff and r['form'] in ('10-K','20-F','40-F') and r.get('reportDate','')<=cutoff]
    if not eligible:return None
    row=max(eligible,key=lambda r:(r.get('reportDate',''),r['filingDate'],r['accessionNumber']))
    if not row.get('reportDate') or (date.fromisoformat(cutoff)-date.fromisoformat(row['reportDate'])).days>550:return None
    return row


def metric_at(facts,key,cutoff,cik):
    tags,unit,kind=METRICS[key]
    candidates=[]
    for priority,tag in enumerate(tags):
        for row in facts.get('facts',{}).get('us-gaap',{}).get(tag,{}).get('units',{}).get(unit,[]):
            if row.get('form') not in ('10-K','10-K/A') or not row.get('filed') or not row.get('end') or row['filed']>cutoff or row['end']>cutoff:continue
            if not iso(row['filed']) or not iso(row['end']):continue
            age=(date.fromisoformat(cutoff)-date.fromisoformat(row['end'])).days
            if age>550:continue
            if kind=='duration':
                if not row.get('start') or not iso(row['start']):continue
                duration=(date.fromisoformat(row['end'])-date.fromisoformat(row['start'])).days
                if not 330<=duration<=380:continue
            value=row.get('val')
            if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):continue
            if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',row.get('accn','')):continue
            candidates.append((row['end'],row['filed'],-priority,row['accn'],row,tag))
    if not candidates:return None,None
    _,_,_,_,row,tag=max(candidates,key=lambda x:x[:4])
    return row['val'],{'filed':row['filed'],'form':row['form'],'periodStart':row.get('start'),'fiscalPeriodEnd':row['end'],'accession':row['accn'],'sourceUrl':filing_url(cik,row['accn']),'tag':tag,'unit':unit}


def investment_evidence(html):
    """A bounded set of brief quotations (<=25 words total per filing).

    Choose paragraphs mentioning actual investment topics; label them as mentions,
    not claims that expenditures definitely happened or produced a return.
    """
    from lxml import html as lxml_html
    # lxml.html's shared default parser serializes parallel report work.
    # Each source worker owns its parser and keeps the SEC request throttle.
    if not hasattr(_local,'html_parser'):_local.html_parser=lxml_html.HTMLParser(no_network=True)
    document=lxml_html.fromstring(html,parser=_local.html_parser)
    for element in document.xpath('//script|//style|//table|//header|//footer|//*[local-name()="header"]'):
        if element.getparent() is not None:element.getparent().remove(element)
    paragraphs=[]
    for node in document.iter('p','div'):
        if node.tag=='div' and next(node.iterdescendants('p','div'),None) is not None:continue
        text=' '.join(' '.join(node.itertext()).split())
        if 70<=len(text)<=3500 and not re.search(r'table of contents|forward.looking statements|risk factors|incorporated by reference',text,re.I):paragraphs.append(text)
    if not paragraphs:
        paragraphs=[t.strip() for t in ' '.join(document.itertext()).split('. ') if 70<=len(t)<=1600]
    output=[];used=set();budget=25
    for label,pattern in THEMES:
        choices=[]
        for text in paragraphs:
            match=pattern.search(text)
            if not match:continue
            # Prefer issuer descriptions over generic risk/contingent statements.
            score=2*bool(re.search(r'\b(?:we|our|company)\b',text,re.I))
            score+=4*bool(re.search(r'(?:spent|invested|expenditures|expenses?)\s+(?:was|were|of|total|include|increased|decreased|for)',text,re.I))
            score+=3*bool(re.search(r'\$\s*[\d,.]+|\b[\d,.]+\s+(?:million|billion)',text,re.I))
            score+=4*bool(re.search(r'(?:research|development|investments?).{0,100}(?:focus|develop|products|technology|expand)',text,re.I))
            score-=12*bool(re.search(r'material adverse|litigation|legal proceedings|competitive position|fair value|impairment|projected cash|amortization|income tax',text,re.I))
            score-=5*bool(re.search(r'\b(?:may not|cannot|could adversely|no assurance|risk of)\b',text,re.I))
            if score<0:continue
            choices.append((score,-len(text),text,match.start()))
        if not choices or budget<7:continue
        _,_,text,offset=max(choices,key=lambda x:x[:2])
        if text in used:continue
        words=text.split();index=len(text[:offset].split())
        start=max(0,index-2);take=min(8,budget)
        snippet=' '.join(words[start:start+take]).strip(' ,;:')
        if not snippet:continue
        output.append({'label':label,'excerpt':snippet,'note':'Short excerpt from the annual filing; a topic mention, not a verified project budget.'})
        budget-=len(snippet.split());used.add(text)
        if len(output)==3:break
    focus=[]
    for label,pattern in FOCUS_AREAS:
        if any(re.search(pattern,text,re.I) and re.search(r'\b(?:invest\w*|research|develop\w*|expenditures|capital|construction|expand\w*)\b',text,re.I) for text in paragraphs):
            focus.append(label)
    return output,focus[:8]


def get_report(cik,row,offline=False):
    accession=row['accessionNumber'];folder=CACHE/str(cik)
    path=folder/'reports'/(accession+'.json')
    cached=load(path)
    if cached and cached.get('extractorVersion')==4:return cached
    base={'form':row['form'],'filed':row['filingDate'],'reportDate':row.get('reportDate'),'accession':accession,'url':filing_url(cik,accession,row.get('primaryDocument') or None)}
    try:
        rawpath=folder/'raw'/(accession+'.html.gz')
        if rawpath.exists():raw=gzip.decompress(rawpath.read_bytes())
        elif offline:raise ValueError('Annual filing text is not cached')
        else:
            doc=row.get('primaryDocument')
            if not doc or not re.fullmatch(r'[A-Za-z0-9_.-]+',doc):raise ValueError('No verified annual report document path')
            response=request(base['url']);raw=response.content
            prefix=raw[:10000].lower()
            # Some older EDGAR reports have an SGML DOCUMENT/TEXT wrapper and
            # head/body markup without an outer HTML tag.
            sgml_html=bool(re.search(rb'<type>\s*(?:10-k|20-f|40-f)\s',prefix) and b'<text>' in prefix and b'<body' in prefix)
            if len(raw)<3000 or not (b'<html' in prefix or sgml_html):raise ValueError('SEC annual filing is not a valid HTML document')
            rawpath.parent.mkdir(parents=True,exist_ok=True)
            temporary=rawpath.with_suffix('.tmp');temporary.write_bytes(gzip.compress(raw,mtime=0));temporary.replace(rawpath)
        themes,focus=investment_evidence(raw)
        result={**base,'status':'ok' if themes else 'no-extracted-mentions','investmentThemes':themes,'focusAreas':focus,'focusNote':'Topics mentioned alongside investment, research, development or expansion in this filing. These are automated evidence pointers, not independently verified allocations.','sha256':hashlib.sha256(raw).hexdigest(),'extractorVersion':4}
        save(path,result);return result
    except Exception as error:
        return {**base,'status':'unavailable','investmentThemes':[],'reason':str(error)[:200]}


def build_cards(cik,cutoffs,rows,facts,reports):
    output=[]
    for cutoff in cutoffs:
        metrics={};sources={}
        for key in METRICS:
            value,source=metric_at(facts,key,cutoff,cik);metrics[key]=value
            if source:sources[key]=source
        chosen=select_report(rows,cutoff)
        filings=[]
        if chosen:
            report=reports.get(chosen['accessionNumber'])
            if report:filings=[{k:v for k,v in report.items() if k not in ('extractorVersion',)}]
        available=[v['filed'] for v in sources.values()]+[f['filed'] for f in filings]
        fiscal=[v['fiscalPeriodEnd'] for v in sources.values()]+[f['reportDate'] for f in filings if f.get('reportDate')]
        status='ok' if filings and filings[0]['status']=='ok' and sources else 'partial' if filings or sources else 'unavailable'
        output.append({'decisionCutoff':cutoff,'availableAt':max(available) if available else None,'fiscalPeriodEnd':max(fiscal) if fiscal else None,'metrics':metrics,'metricSources':sources,'filings':filings,'valuation':None,'status':status,'reason':None if status=='ok' else 'Some annual investment evidence or standard financial tags could not be established from the filings available at this cutoff.'})
    return output


def process_issuer(cik,cutoffs,offline=False):
    errors=[]
    _local.refresh_warnings=[]
    try:_,rows=issuer_metadata(cik,offline)
    except Exception as error:rows=[];errors.append('submissions: '+str(error)[:180])
    try:
        facts=cached_json(CACHE/str(cik)/'companyfacts.json.gz',f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',offline,_REFRESH_METADATA)
        if int(facts.get('cik',-1))!=cik:raise ValueError('SEC facts CIK mismatch')
    except Exception as error:facts={};errors.append('facts: '+str(error)[:180])
    chosen={r['accessionNumber']:r for cutoff in cutoffs if (r:=select_report(rows,cutoff))}
    reports={acc:get_report(cik,row,offline) for acc,row in chosen.items()}
    cards=build_cards(cik,cutoffs,rows,facts,reports)
    result={'cik':cik,'cards':cards,'errors':errors+_local.refresh_warnings}
    save(CACHE/str(cik)/'cards.json',result)
    return result


def main():
    global _REFRESH_METADATA
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--universe',type=Path,help='JSON containing assets with CIKs (or an assets array)')
    parser.add_argument('--ciks',help='Comma-separated SEC CIKs')
    parser.add_argument('--start-year',type=int,default=2010)
    parser.add_argument('--end-year',type=int,default=datetime.now(timezone.utc).year-1)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--refresh-metadata',action='store_true',help='Refresh SEC submissions and facts; dated annual report caches remain pinned')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    _REFRESH_METADATA=args.refresh_metadata
    if args.universe:
        payload=json.loads(args.universe.read_text());assets=payload if isinstance(payload,list) else payload['assets']
        issuer_years={}
        transition_cutoffs={}
        for asset in assets:
            if asset.get('id')=='SPY':continue
            histories=asset.get('filingCiks') or [{'cik':asset.get('cik')}]
            for entry in histories:
                if not entry.get('cik'):continue
                # A predecessor's already public annual report can still be the
                # latest evidence just after a holding-company reorganization.
                last_year=int(entry['end'][:4])+2 if entry.get('end') else 9999
                years=[y for y in asset.get('membershipYears',range(args.start_year,args.end_year+1)) if args.start_year<=y<=args.end_year and entry.get('start','0000-01-01')<=f'{y}-12-31' and y<=last_year]
                issuer_years.setdefault(int(entry['cik']),set()).update(years)
                end=entry.get('evidenceThrough') or entry.get('end')
                if years and end and f'{args.start_year}-01-01'<=end<=f'{args.end_year}-12-31':
                    # Retain the original evidence known at a registrant's
                    # transition. A later amendment must not erase the older
                    # eligible value before the compiler applies lineage caps.
                    transition_cutoffs.setdefault(int(entry['cik']),set()).add(end)
        ciks={cik for cik,years in issuer_years.items() if years}
        issuer_cutoffs={cik:{f'{y}-12-31' for y in issuer_years[cik]}|transition_cutoffs.get(cik,set()) for cik in ciks}
    else:
        ciks={int(x) for x in (args.ciks or '').split(',') if x}
        issuer_years={cik:set(range(args.start_year,args.end_year+1)) for cik in ciks}
        issuer_cutoffs={cik:{f'{y}-12-31' for y in issuer_years[cik]} for cik in ciks}
    if not ciks:parser.error('Provide at least one verified issuer CIK')
    if args.start_year<2010 or args.end_year>=datetime.now(timezone.utc).year:parser.error('Annual decisions must begin in 2010 and end in a completed year')
    cutoffs=[f'{y}-12-31' for y in range(args.start_year,args.end_year+1)]
    existing=load(args.output,{});issuers=existing.get('issuers',{})
    def persist():
        save(args.output,{'schemaVersion':1,'generatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'source':'SEC EDGAR; annual reports and US-GAAP Company Facts','methodology':'Only reports and facts actually filed by each year-end cutoff; source excerpts are automated topic pointers, not a project-level spending or causal-return model. Missing tags are unknown, never zero. Financial periods and filing dates are retained for each metric.','issuers':issuers})
    started=time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1,min(args.workers,10))) as pool:
        futures={pool.submit(process_issuer,cik,sorted(issuer_cutoffs[cik]),args.offline):cik for cik in sorted(ciks)}
        for count,future in enumerate(as_completed(futures),1):
            cik=futures[future]
            try:result=future.result();issuers[str(cik)]=result
            except Exception as error:print(f'CIK {cik}: ERROR {error}',flush=True);continue
            cards=result['cards'];full=sum(c['status']=='ok' for c in cards);reports=sum(bool(c['filings'] and c['filings'][0]['status']=='ok') for c in cards)
            print(f'{count}/{len(ciks)} CIK {cik}: {full}/{len(cards)} complete cards; {reports} filing narratives; {round(time.monotonic()-started)}s',flush=True)
            # Each issuer is already persisted independently. Batch the merged
            # file to avoid rewriting tens of megabytes after every company.
            if count%10==0:persist()
    persist()
    print(f'Saved {len(issuers)} issuers to {args.output}',flush=True)

if __name__=='__main__':main()
