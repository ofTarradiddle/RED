#!/usr/bin/env python3
"""Compile the annual portfolio game from cached constituent, SEC and price evidence.

No network is used by the compiler or website publisher. Source refreshes are
explicit commands; the economic content hash changes only when evidence changes.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/annual-game'
METRICS=('revenue','netIncome','operatingCashFlow','capex','rd','acquisitions','assets','equity','epsDiluted')


def read(path):return json.loads(path.read_text())


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def economic_content(value):
    """Retrieval times are provenance, not a new economic game edition."""
    if isinstance(value,dict):return {k:economic_content(v) for k,v in value.items() if k not in ('generatedAt','retrievedAt','refreshedAt')}
    if isinstance(value,list):return [economic_content(v) for v in value]
    return value


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(canonical(value)+'\n');temp.replace(path)


def iso(value):
    try:return isinstance(value,str) and len(value)==10 and date.fromisoformat(value).isoformat()==value
    except ValueError:return False


def finite(value):return not isinstance(value,bool) and isinstance(value,(float,int)) and math.isfinite(value)


def validate_sec_link(url,accession):
    parsed=urlsplit(url)
    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession or ''):raise ValueError('Invalid SEC accession')
    expected=rf'/Archives/edgar/data/[0-9]+/{accession.replace("-", "")}/[A-Za-z0-9_.-]+'
    if parsed.scheme!='https' or parsed.netloc!='www.sec.gov' or not re.fullmatch(expected,parsed.path) or parsed.query or parsed.fragment:
        raise ValueError('Accounting evidence requires its exact SEC EDGAR accession link')


def validate_fact_source(key,source,cutoff):
    try:
        from scripts.annual_filings import METRICS as SOURCE_METRICS
    except ModuleNotFoundError:
        from annual_filings import METRICS as SOURCE_METRICS
    tags,unit,kind=SOURCE_METRICS[key]
    if source.get('form') not in ('10-K','10-K/A') or source.get('tag') not in tags or source.get('unit')!=unit:
        raise ValueError('Accounting evidence must use the correct annual form, tag and unit')
    if not iso(source.get('filed')) or not iso(source.get('fiscalPeriodEnd')) or not source['fiscalPeriodEnd']<=source['filed']<=cutoff:
        raise ValueError('A financial fact was unavailable at the decision cutoff')
    if (date.fromisoformat(cutoff)-date.fromisoformat(source['fiscalPeriodEnd'])).days>550:raise ValueError('Stale annual financial evidence')
    if kind=='duration':
        if not iso(source.get('periodStart')) or not 330<=(date.fromisoformat(source['fiscalPeriodEnd'])-date.fromisoformat(source['periodStart'])).days<=380:
            raise ValueError('Annual spending and earnings require a full annual period')
    validate_sec_link(source.get('sourceUrl',''),source.get('accession',''))


def combine_financials(asset,cutoff,issuers):
    try:
        from scripts.annual_excerpt import clean_filing_excerpts
    except ModuleNotFoundError:
        from annual_excerpt import clean_filing_excerpts
    histories=asset.get('filingCiks') or [{'cik':asset.get('cik')}]
    oldest=(date.fromisoformat(cutoff)-timedelta(days=550)).isoformat()
    candidates=[]
    for entry in histories:
        if not entry.get('cik') or entry.get('start','0000-01-01')>cutoff:continue
        for card in issuers.get(str(entry['cik']),{}).get('cards',[]):
            if card.get('decisionCutoff','9999-12-31')<=cutoff:
                candidates.append((card,entry.get('evidenceThrough') or entry.get('end') or cutoff,entry.get('end') or cutoff))
    metrics={key:None for key in METRICS};sources={}
    for key in METRICS:
        eligible=[]
        for card,known_through,period_through in candidates:
            source=card.get('metricSources',{}).get(key);value=card.get('metrics',{}).get(key)
            if source and finite(value) and source['filed']<=min(cutoff,known_through) and oldest<=source['fiscalPeriodEnd']<=min(cutoff,period_through):
                eligible.append((source['fiscalPeriodEnd'],source['filed'],source.get('accession',''),value,source))
        if eligible:
            row=max(eligible,key=lambda r:r[:3]);metrics[key]=row[3];sources[key]=row[4]
    filings=[f for c,known_through,period_through in candidates for f in c.get('filings',[]) if f['filed']<=min(cutoff,known_through) and oldest<=f.get('reportDate','')<=min(cutoff,period_through)]
    filings=sorted({f['accession']:f for f in filings}.values(),key=lambda f:(f.get('reportDate',''),f['filed']),reverse=True)[:1]
    filings=[clean_filing_excerpts(f,ROOT/'.cache/annual-filings') for f in filings]
    known=[s['filed'] for s in sources.values()]+[f['filed'] for f in filings]
    fiscal=[s['fiscalPeriodEnd'] for s in sources.values()]+[f['reportDate'] for f in filings if f.get('reportDate')]
    status='ok' if sources and filings and filings[0]['status']=='ok' else 'partial' if sources or filings else 'unavailable'
    result={'decisionCutoff':cutoff,'availableAt':max(known) if known else None,'fiscalPeriodEnd':max(fiscal) if fiscal else None,'metrics':metrics,'metricSources':sources,'filings':filings,'status':status,'valuation':None,'reason':None if status=='ok' else 'Dated SEC evidence is incomplete for this historical issuer. Missing standard tags do not mean zero spending.'}
    eps=metrics['epsDiluted'];source=sources.get('epsDiluted')
    quotes=[p for p in asset['points'] if p['date']<=cutoff and p.get('close') is not None]
    if source and quotes:
        quote=max(quotes,key=lambda p:p['date'])
        if (date.fromisoformat(cutoff)-date.fromisoformat(quote['date'])).days<=7:
            splits=asset.get('splits',[])
            ambiguous=any(source['fiscalPeriodEnd']<s['date']<=source['filed'] for s in splits)
            basis=asset.get('priceBasis')
            split_history_complete=asset.get('splitsStatus')=='complete' and bool(asset.get('splitsAsOf')) and bool(asset.get('splitsFrom')) and asset['splitsFrom']<=source['fiscalPeriodEnd']
            if not ambiguous and split_history_complete and asset.get('priceBasisAsOf') and asset['splitsAsOf']>=asset['priceBasisAsOf'] and basis in ('yahoo-split-adjusted-close','yahoo-split-adjusted','split-adjusted','Yahoo split-adjusted Close'):
                multiplier=math.prod(s['ratio'] for s in splits if source['fiscalPeriodEnd']<s['date']<=asset['priceBasisAsOf'])
            elif not ambiguous and split_history_complete and basis in ('raw','unadjusted','contemporaneous-unadjusted-close','contemporaneous-unadjusted','wiki-unadjusted') and asset['splitsAsOf']>=quote['date']:
                multiplier=math.prod(s['ratio'] for s in splits if source['fiscalPeriodEnd']<s['date']<=quote['date'])
            else:multiplier=None
            if multiplier is not None:
                result['valuation']={'pe':quote['close']*multiplier/eps if eps is not None and eps>0 else None,'asOf':quote['date'],'sourceUrl':source['sourceUrl'],'note':'Last known closing price / latest filed annual diluted EPS, translated to a consistent split basis. Not forward or trailing-twelve-month P/E.' if eps and eps>0 else 'Annual diluted earnings were nonpositive; a P/E multiple is not meaningful.'}
    return result


def validate_dataset(payload):
    if payload.get('schema_version')!=1 or payload.get('id')!='hetzerk-annual-portfolio':raise ValueError('Unsupported annual portfolio edition')
    if not iso(payload.get('asOf')) or payload['asOf']>datetime.now(timezone.utc).date().isoformat():raise ValueError('Annual-game as-of date is invalid')
    if not isinstance(payload.get('assets'),list) or not 1<=len(payload['assets'])<=2000:raise ValueError('Invalid annual universe')
    assets={}
    for a in payload['assets']:
        identity=a.get('id','')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,160}',identity) or identity in assets:raise ValueError('Duplicate/invalid security identity')
        assets[identity]=a;previous=''
        for p in a.get('points',[]):
            if not iso(p['date']) or not previous<p['date']<=payload['asOf'] or not finite(p['adjustedClose']) or p['adjustedClose']<=0:raise ValueError('Unobserved or invalid return index')
            if p.get('close') is not None and (not finite(p['close']) or p['close']<=0):raise ValueError('Invalid source quote')
            previous=p['date']
        playable={p['date'] for p in a.get('points',[])}
        for excluded in a.get('excludedObservations',[]):
            if not iso(excluded.get('date')) or not excluded.get('qualityFlagId'):raise ValueError('Excluded observation requires dated review evidence')
            if excluded['date'] in playable:raise ValueError('A reviewed-out observation cannot be published as a playable price')
        for card in a.get('financials',[]):
            cutoff=card.get('decisionCutoff')
            if not iso(cutoff):raise ValueError('Financial card needs a valid cutoff')
            if card.get('availableAt') is not None and (not iso(card['availableAt']) or card['availableAt']>cutoff):raise ValueError('Future financial card')
            if card.get('fiscalPeriodEnd') is not None and (not iso(card['fiscalPeriodEnd']) or card['fiscalPeriodEnd']>cutoff):raise ValueError('Future accounting period')
            if set(card.get('metrics',{}))-set(METRICS) or set(card.get('metricSources',{}))-set(METRICS):raise ValueError('Unknown accounting metric')
            for key in METRICS:
                value=card.get('metrics',{}).get(key);source=card.get('metricSources',{}).get(key)
                if value is None:continue
                if not finite(value) or not source:raise ValueError('An accounting value lacks source evidence')
                validate_fact_source(key,source,cutoff)
            for filing in card.get('filings',[]):
                if not iso(filing['filed']) or filing['filed']>cutoff or filing.get('reportDate','')>cutoff:raise ValueError('Future filing leaked into a decision')
                if not iso(filing.get('reportDate')) or filing['reportDate']>filing['filed'] or (date.fromisoformat(cutoff)-date.fromisoformat(filing['reportDate'])).days>550:
                    raise ValueError('Invalid or stale annual report period')
                if filing.get('form') not in ('10-K','20-F','40-F'):raise ValueError('Narrative must use an original annual filing')
                validate_sec_link(filing['url'],filing.get('accession',''))
                if sum(len(t['excerpt'].split()) for t in filing.get('investmentThemes',[]))>25:raise ValueError('Source quotation budget exceeded')
            known=[s['filed'] for s in card.get('metricSources',{}).values()]+[f['filed'] for f in card.get('filings',[])]
            fiscal=[s['fiscalPeriodEnd'] for s in card.get('metricSources',{}).values()]+[f['reportDate'] for f in card.get('filings',[])]
            if card.get('availableAt')!=(max(known) if known else None) or card.get('fiscalPeriodEnd')!=(max(fiscal) if fiscal else None):
                raise ValueError('Financial card dates do not match its included evidence')
            valuation=card.get('valuation')
            if valuation and (not iso(valuation['asOf']) or valuation['asOf']>cutoff or valuation.get('pe') is not None and (not finite(valuation['pe']) or valuation['pe']<=0)):raise ValueError('Invalid historical valuation ratio')
    previous=None;rounds=payload.get('rounds',[])
    if not rounds or rounds[0].get('year')!=2010:raise ValueError('Annual history must begin with year-end 2010')
    for rnd in rounds:
        if rnd['cutoff']!=f"{rnd['year']}-12-31" or not rnd['cutoff']<rnd['executionDate']<rnd['endDate']<=payload['asOf']:raise ValueError('Invalid annual decision/execution timing')
        if previous and (rnd['year']!=previous['year']+1 or previous['endDate']!=rnd['executionDate']):raise ValueError('Annual accounting periods must meet exactly')
        grid=rnd['valuationDates']
        if grid!=sorted(set(grid)) or grid[0]!=rnd['executionDate'] or grid[-1]!=rnd['endDate'] or any(not iso(d) for d in grid):raise ValueError('Invalid observed mark calendar')
        members=rnd['eligibleAssetIds']
        if len(members)!=len(set(members)) or any(identity not in assets for identity in members):raise ValueError('Invalid historical constituent roster')
        previous=rnd
    benchmark=assets.get(payload.get('benchmarkAssetId'))
    if not benchmark:raise ValueError('SPY benchmark missing')
    known={p['date'] for p in benchmark['points']}
    if any(d not in known for r in rounds for d in r['valuationDates']):raise ValueError('Missing observed SPY comparator marks')
    if rounds[-1]['endDate']!=payload['asOf']:raise ValueError('Incomplete final valuation period')
    return payload


def compile_dataset(universe_path=DATA/'universe.json',filings_path=DATA/'filings.json',output=DATA/'dataset.json'):
    universe=deepcopy(read(universe_path));evidence=read(filings_path) if filings_path.exists() else {'issuers':{}}
    universe.pop('sampleDates',None);universe.pop('membershipCrossCheck',None)
    rounds_by_year={r['year']:r for r in universe['rounds']}
    for asset in universe['assets']:
        if asset['id']==universe['benchmarkAssetId']:continue
        asset['financials']=[combine_financials(asset,rounds_by_year[year]['cutoff'],evidence['issuers']) for year in asset.get('membershipYears',[]) if year in rounds_by_year]
        # Future security events are not copied into the point-in-time decision
        # view. Coverage/status remains distinct from the annual issuer evidence.
    total=0;with_facts=0;with_narrative=0
    by_id={a['id']:a for a in universe['assets']}
    for rnd in universe['rounds']:
        facts=0;narratives=0
        for identity in rnd['eligibleAssetIds']:
            card=next((c for c in by_id[identity].get('financials',[]) if c['decisionCutoff']==rnd['cutoff']),None)
            facts+=bool(card and card['metricSources'])
            narratives+=bool(card and card['filings'] and card['filings'][0]['status']=='ok')
        rnd.setdefault('coverage',{}).update(filedFinancials=facts,filingNarratives=narratives)
        total+=len(rnd['eligibleAssetIds']);with_facts+=facts;with_narrative+=narratives
    universe['coverage'].update(companyDecisions=total,decisionsWithFiledFinancials=with_facts,decisionsWithFilingNarratives=with_narrative)
    universe['methodology']={
      'timing':'Decide at each calendar year end, beginning 2010. Only filings dated on or before that cutoff are presented. Trades use the first observed market close afterward; the final interval ends at the observation date and may be a partial year.',
      'allocations':'Start with $100 of fictional capital. Allocate across any number of eligible securities up to 100% in total; uninvested cash earns zero. At each rebalance old return-unit lots close and new lots open at the same observed close. No leverage, shorting, taxes, fees or trading frictions.',
      'returns':'Historical adjusted-close ratios are provider proxies for shareholder returns with splits and distributions reflected. No extra dividend or split credit is added. Valuations use actual month-end observations plus rebalance dates. Missing observations or unresolved terminal payoffs block the affected security-period; none are filled or treated as zero.',
      'filings':'Annual SEC US-GAAP facts and annual filing text are selected by actual filing date. Later comparative restatements cannot appear before their filing date. Periods more than 550 days old are excluded. Financial metrics retain their own fiscal periods, tags, accessions and source links. An annual R&D figure, PP&E cash spending and acquisition cash spending are different accounting measures, not a project-level innovation budget.',
      'narrative':'Investment focus labels are automatically extracted topic mentions from that annual report. Brief verbatim excerpts link to the report; they are evidence pointers rather than an investment recommendation or proof of spending on a named project. They do not attribute later stock returns to an innovation.',
      'attribution':'Firm deep dives show the next rebalance interval and only the investor\'s completed holding periods, with realized and unrealized profit, capital deployed and additive contribution. Repeated deployments are not mistaken for external deposits; a profit/deployed-capital ratio is not an annualized investment return.',
      'benchmark':'SPY is a separately observed S&P 500 ETF comparator, including provider distribution adjustments. It is not the index itself, and the player universe is a reconstructed historical roster, not an officially certified index replica.',
      'coverage':'All reconstructed historical members remain visible. Missing price, delisted-share or corporate-action data remains explicit. Limiting purchases to calculable histories creates selection bias; this is a learning game, not a survivorship-free strategy study.'}
    universe['filingSourceUrl']='https://www.sec.gov/search-filings/edgar-application-programming-interfaces'
    universe.pop('version',None);universe.pop('generatedAt',None)
    universe['version']=hashlib.sha256(canonical(economic_content(universe)).encode()).hexdigest()[:20]
    universe['generatedAt']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    validate_dataset(universe);save(output,universe)
    return universe


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=DATA/'dataset.json');args=parser.parse_args()
    payload=compile_dataset(output=args.output)
    print(json.dumps({'version':payload['version'],'asOf':payload['asOf'],'assets':len(payload['assets']),'companyDecisions':payload['coverage']['companyDecisions'],'decisionsWithFiledFinancials':payload['coverage']['decisionsWithFiledFinancials'],'decisionsWithFilingNarratives':payload['coverage']['decisionsWithFilingNarratives']}))

if __name__=='__main__':main()
