#!/usr/bin/env python3
"""Reproduce historical annual rosters and observed Yahoo return-proxy coverage.

Historical membership is never inferred from today's constituents. Missing
security identities and delisted prices remain in the roster with explicit gaps.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date, datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'annual-game'
SOURCE = DATA / 'sources'
YEAR_START = 2010
MEMBERSHIP_URL = 'https://github.com/fja05680/sp500'
METADATA_URL = 'https://github.com/lawcal/sp500-components-history'
SEC_URL = 'https://www.sec.gov/files/company_tickers.json'
GOOGLE_CLASS_SOURCE='https://www.sec.gov/Archives/edgar/data/1288776/000128877615000008/goog2014123110-k.htm'
ARCHIVE_ALIAS_GROUPS=[
    {'cik':858470,'symbols':('COG','CTRA'),'wiki':'COG','eras':(('1900-01-01','COG'),('2021-10-04','CTRA')),
     'sourceUrl':'https://www.sec.gov/Archives/edgar/data/858470/000110465921122041/tm2129019d1_8k.htm'},
    {'cik':813828,'symbols':('CBS','VIAC','PARA'),'wiki':'CBS','eras':(('1900-01-01','CBS'),('2019-12-05','VIAC'),('2022-02-17','PARA')),
     'sourceUrl':'https://www.sec.gov/Archives/edgar/data/813828/000081382823000005/para-20221231.htm'},
    {'cik':1725057,'symbols':('CDAY','DAY'),'wiki':'CDAY','eras':(('1900-01-01','CDAY'),('2024-02-01','DAY')),
     'sourceUrl':'https://www.sec.gov/Archives/edgar/data/1725057/000095017024009619/day-20240131.htm'},
]
SOURCE_URLS={
 'components_history.csv':'https://raw.githubusercontent.com/lawcal/sp500-components-history/main/data/components_history.csv',
 'components_current.csv':'https://raw.githubusercontent.com/lawcal/sp500-components-history/main/data/sp500_components.csv',
 'components_README.md':'https://raw.githubusercontent.com/lawcal/sp500-components-history/main/README.md',
 'components_LICENSE.txt':'https://raw.githubusercontent.com/lawcal/sp500-components-history/main/LICENSE',
 'historical_snapshots.csv.gz':'https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv',
 'historical_LICENSE.txt':'https://raw.githubusercontent.com/fja05680/sp500/master/LICENSE',
 'sec_company_tickers.json':SEC_URL,
}
# Aliases are used only to locate historical issuer evidence, never to stitch
# a bankrupt common share to a newly issued security bearing a similar ticker.
METADATA_ALIASES = {'AABA':'YHOO','ANRZQ':'ANR','ATGE':'DV','BTUUQ':'BTU',
                    'HSH':'SLE','RSHCQ':'RSH','SUNEQ':'WFR','VIAV':'JDSU','WYND':'WYN'}
BLOCKED_REISSUES = {'BTUUQ','ANRZQ','RSHCQ','SUNEQ','EKDKQ','CHK'}
WIKI_ALIASES={'AABA':'YHOO','ANRZQ':'ANR','BTUUQ':'BTU','RSHCQ':'RSH','SUNEQ':'SUNE',
              'WYND':'WYN','VIAV':'JDSU','ATGE':'DV','BF.B':'BFB','BRK.B':'BRK_B','ANDV':'TSO'}
VERIFIED_YAHOO_ALIASES={
    ('BK',1390777):('BNY','https://www.bny.com/corporate/global/en/about-us/newsroom/press-release/bny-announces-planned-change-of-stock-ticker-symbol-to-bny-130465.html'),
    ('TMK',320335):('GL','https://www.sec.gov/Archives/edgar/data/320335/000032033520000008/gl-20191231.htm'),
    ('SYMC',849399):('GEN','https://www.sec.gov/Archives/edgar/data/849399/000084939922000026/gen-20220930.htm'),
    ('NLOK',849399):('GEN','https://www.sec.gov/Archives/edgar/data/849399/000084939922000026/gen-20220930.htm'),
}
# Verified later corporate events let an original member remain invested after
# its index removal. These are identity boundaries only, never inferred exits.
ARCHIVE_END_OVERRIDES={
    'AKS':('2020-03-13','https://www.sec.gov/Archives/edgar/data/764065/000076406520000089/ex991-202003138xk.htm'),
    'CPWR':('2014-12-15','https://www.thomabravo.com/press-releases/thoma-bravo-completes-take-private-acquisition-of-compuware-corporation-in-2.4b-deal'),
    'JNS':('2017-05-30','https://www.globenewswire.com/news-release/2017/05/30/999918/0/en/Janus-Capital-Group-Inc-and-Henderson-Group-plc-complete-Merger-of-Equals.html'),
    'MWW':('2016-11-01','https://www.randstad.com/press/2016/randstad-completes-acquisition-monster-worldwide-to-accelerate-its-digital-human/'),
    'QLGC':('2016-08-16','https://www.sec.gov/Archives/edgar/data/1175609/000119312516682627/d239663dex992.htm'),
    'RSHCQ':('2015-02-02','https://www.sec.gov/Archives/edgar/data/96289/000119312515338728/d38755dex22.htm'),
    'SUNEQ':('2016-04-21','https://www.sec.gov/Archives/edgar/data/1599947/000159994716000244/terp201510-k.htm'),
    'MDP':('2021-12-01','https://www.globenewswire.com/news-release/2021/12/01/2344524/0/en/GRAY-TELEVISION-CLOSES-ON-ACQUISITION-OF-MEREDITH-CORPORATION-S-LOCAL-MEDIA-GROUP.html'),
}
# Filing-issuer transitions are independent of a provider's adjusted price
# lineage. These dated predecessor mappings prevent future parent CIKs from
# standing in for the registrant that had actually filed at a decision cutoff.
FILING_TRANSITIONS = {
    'GOOGL':(1288776,1652044,'2015-10-02','https://www.sec.gov/Archives/edgar/data/1288776/000119312515336550/d56649d8k.htm'),
    'GOOG':(1288776,1652044,'2015-10-02','https://www.sec.gov/Archives/edgar/data/1288776/000119312515336550/d56649d8k.htm'),
    'APA':(6769,1841666,'2021-03-01','https://www.sec.gov/Archives/edgar/data/1841666/000187113321000007/apa-20210630.htm'),
    'MDT':(64670,1613103,'2015-01-26','https://www.sec.gov/Archives/edgar/data/64670/000119312515020704/0001193125-15-020704-index.htm'),
    'ETN':(31277,1551182,'2012-11-30','https://www.sec.gov/divisions/corpfin/cf-noaction/14a-8/2013/qubeinvestmenteaton122413-14a8-incoming.pdf'),
    'ICE':(1174746,1571949,'2013-11-13','https://www.sec.gov/Archives/edgar/data/1571949/000157194914000006/ice2013123110k.htm'),
    'BLK':(1364742,2012383,'2024-10-01','https://www.sec.gov/Archives/edgar/data/1364742/000119312524229654/d856279d8k.htm'),
    'DIS':(1001039,1744489,'2019-03-20','https://www.sec.gov/Archives/edgar/data/1744489/000095015719000301/form8k-12b.htm'),
    'FTI':(1135152,1681459,'2017-01-16','https://www.sec.gov/Archives/edgar/data/1681459/000119312517010409/d320389d8k.htm'),
    'CI':(701221,1739940,'2018-12-20','https://www.sec.gov/Archives/edgar/data/701221/000114036118045478/form8k.htm'),
    'WBA':(104207,1618921,'2014-12-31','https://www.sec.gov/Archives/edgar/data/1618921/000119312514457671/d843789d8k12b.htm'),
    'XRX':(108772,1770450,'2019-07-31','https://www.sec.gov/Archives/edgar/data/1770450/000119312519208837/d767474d8k12b.htm'),
    'BHGE':(808362,1701605,'2017-07-03','https://www.sec.gov/Archives/edgar/data/808362/000080836218000006/bhgellcfy2017form10xk.htm'),
    'BKR':(808362,1701605,'2017-07-03','https://www.sec.gov/Archives/edgar/data/808362/000080836218000006/bhgellcfy2017form10xk.htm'),
    'DXC':(23082,1688568,'2017-04-01','https://www.sec.gov/Archives/edgar/data/23082/000119312517113607/d371672d8k.htm'),
    'MYL':(69499,1623613,'2015-02-27','https://www.sec.gov/Archives/edgar/data/69499/000006949915000003/myl10k_20141231xdoc.htm'),
    'ESRX':(885721,1532063,'2012-04-02','https://www.sec.gov/Archives/edgar/data/1532063/000153206314000006/esrx-12312013x10k.htm'),
}


def filing_ciks(symbol,cik):
    if symbol=='AVGO':
        url='https://www.sec.gov/Archives/edgar/data/1730168/000173016818000084/avgo-11042018x10k.htm'
        return [{'cik':1441634,'start':'1900-01-01','end':'2016-01-31','sourceUrl':url},
                {'cik':1649338,'start':'2016-02-01','end':'2018-04-04','sourceUrl':url},
                {'cik':1730168,'start':'2018-04-05','end':None,'sourceUrl':url}]
    if symbol in FILING_TRANSITIONS:
        old,new,transition,url=FILING_TRANSITIONS[symbol]
        from datetime import timedelta
        end=(date.fromisoformat(transition)-timedelta(days=1)).isoformat()
        history=[{'cik':old,'start':'1900-01-01','end':end,'sourceUrl':url},
                 {'cik':new,'start':transition,'end':None,'sourceUrl':url}]
        if symbol=='MYL':
            # The final old-issuer annual report covers 2014 but was filed
            # after the holding-company transition. Pin only this known case.
            history[0].update(evidenceThrough='2015-03-02',evidenceSourceUrl=url)
        return history
    if symbol=='XOM':
        # Every game decision ends by 2025, before the 2026 holding-company CIK.
        return [{'cik':34088,'start':'1900-01-01','end':'2025-12-31',
                 'sourceUrl':'https://investor.exxonmobil.com/sec-filings/all-sec-filings/content/0000034088-26-000026/0000034088-26-000026.pdf'}]
    return []


def historical_label(symbol,cutoff,record):
    """Dated, sourced overrides; unverified source aliases stay explicit."""
    label={'ticker':record['symbol'] if record else symbol,'name':record['name'] if record else symbol,
           'note':'Historical name/ticker not independently verified; source metadata may reflect a later alias.',
           'status':'source-alias-unverified'}
    def set_label(ticker,name,url):
        label.update(ticker=ticker,name=name,sourceUrl=url,status='dated-source-verified',
                     note='Name and ticker aligned to the decision cutoff using the linked corporate history.')
    if symbol in ('GOOG','GOOGL'):
        name='Google Inc.' if cutoff<'2015-10-02' else 'Alphabet Inc.'
        name+=' (Class A)' if symbol=='GOOGL' else ' (Class C)'
        set_label('GOOG' if cutoff<'2014-04-03' else symbol,name,GOOGLE_CLASS_SOURCE if cutoff<'2015-10-02' else FILING_TRANSITIONS[symbol][3])
    elif symbol in ('META','FB'):
        set_label('FB' if cutoff<'2022-06-09' else 'META','Facebook, Inc.' if cutoff<'2021-10-28' else 'Meta Platforms, Inc.',
                  'https://www.sec.gov/Archives/edgar/data/1326801/000132680121000071/fb-20211028.htm' if cutoff<'2022-01-01' else 'https://www.sec.gov/Archives/edgar/data/1326801/000132680122000070/fb-20220531.htm')
    elif symbol=='GE':
        set_label('GE','General Electric Company' if cutoff<'2024-04-02' else 'GE Aerospace','https://www.geaerospace.com/news/press-releases/ge-aerospace-launches-independent-investment-grade-public-company-following-0')
    elif symbol=='SPGI':
        ticker,name=('MHP','The McGraw-Hill Companies, Inc.') if cutoff<'2013-05-01' else ('MHFI','McGraw Hill Financial, Inc.') if cutoff<'2016-04-27' else ('SPGI','S&P Global Inc.')
        set_label(ticker,name,'https://investor.spglobal.com/contact-investor-relations/investor-faq/')
    elif symbol in ('ANTM','ELV'):
        ticker,name=('WLP','WellPoint, Inc.') if cutoff<'2014-12-02' else ('ANTM','Anthem, Inc.') if cutoff<'2022-06-28' else ('ELV','Elevance Health, Inc.')
        set_label(ticker,name,'https://www.sec.gov/Archives/edgar/data/1156039/000115603915000003/antm-20141231x10k.htm' if cutoff<'2022-01-01' else 'https://www.elevancehealth.com/newsroom/anthem-announces-subsidiary-brands-under-elevance-health')
    elif symbol=='WELL':
        set_label('HCN' if cutoff<'2018-02-28' else 'WELL','Health Care REIT, Inc.' if cutoff<'2015-09-30' else 'Welltower Inc.',
                  'https://welltower.com/investors/investors-press-releases/' if cutoff<'2018-01-01' else 'https://www.prnewswire.com/news-releases/welltower-to-change-nyse-ticker-symbol-to-well-300600036.html')
    elif symbol=='WBA':
        set_label('WAG' if cutoff<'2014-12-31' else 'WBA','Walgreen Co.' if cutoff<'2014-12-31' else 'Walgreens Boots Alliance, Inc.',FILING_TRANSITIONS['WBA'][3])
    elif symbol=='BKNG':
        name='priceline.com Incorporated' if cutoff<'2014-04-01' else 'The Priceline Group Inc.' if cutoff<'2018-02-21' else 'Booking Holdings Inc.'
        set_label('PCLN' if cutoff<'2018-02-27' else 'BKNG',name,'https://www.sec.gov/Archives/edgar/data/1075531/000107553118000015/pcln-20171231_10k.htm')
    elif symbol=='AVGO':
        name='Avago Technologies Limited' if cutoff<'2016-02-01' else 'Broadcom Limited' if cutoff<'2018-04-05' else 'Broadcom Inc.'
        set_label('AVGO',name,'https://www.sec.gov/Archives/edgar/data/1730168/000173016818000084/avgo-11042018x10k.htm')
    elif symbol=='CI':
        set_label('CI','Cigna Corporation' if cutoff<'2023-02-01' else 'The Cigna Group','https://www.sec.gov/Archives/edgar/data/1739940/000110465923033907/tm239628d1_ars.pdf')
    elif symbol=='XRX':
        set_label('XRX','Xerox Corporation' if cutoff<'2019-07-31' else 'Xerox Holdings Corporation',FILING_TRANSITIONS['XRX'][3])
    elif symbol in ('BHGE','BKR') and cutoff<'2019-01-01':
        set_label('BHI' if cutoff<'2017-07-03' else 'BHGE','Baker Hughes Incorporated' if cutoff<'2017-07-03' else 'Baker Hughes, a GE company',FILING_TRANSITIONS[symbol][3])
    elif symbol=='DXC':
        set_label('CSC' if cutoff<'2017-04-01' else 'DXC','Computer Sciences Corporation' if cutoff<'2017-04-01' else 'DXC Technology Company',FILING_TRANSITIONS['DXC'][3])
    elif symbol=='MYL':
        set_label('MYL','Mylan Inc.' if cutoff<'2015-02-27' else 'Mylan N.V.',FILING_TRANSITIONS['MYL'][3])
    elif symbol=='ESRX':
        set_label('ESRX','Express Scripts, Inc.' if cutoff<'2012-04-02' else 'Express Scripts Holding Company',FILING_TRANSITIONS['ESRX'][3])
    elif symbol in ('FI','FISV'):
        set_label('FISV' if cutoff<'2023-06-07' or cutoff>='2025-11-11' else 'FI','Fiserv, Inc.',
                  'https://investors.fiserv.com/news-releases/news-release-details/fiserv-completes-listing-transfer-new-york-stock-exchange' if cutoff<'2025-01-01' else 'https://investors.fiserv.com/news-releases/news-release-details/fiserv-announces-transfer-stock-exchange-listing-nasdaq')
    elif symbol in ('COG','CTRA'):
        set_label('COG' if cutoff<'2021-10-04' else 'CTRA','Cabot Oil & Gas Corporation' if cutoff<'2021-10-01' else 'Coterra Energy Inc.',
                  'https://www.sec.gov/Archives/edgar/data/858470/000110465921122041/tm2129019d1_8k.htm')
    elif symbol in ('CBS','VIAC','PARA'):
        ticker,name=('CBS','CBS Corporation') if cutoff<'2019-12-05' else ('VIAC','ViacomCBS Inc.') if cutoff<'2022-02-17' else ('PARA','Paramount Global')
        set_label(ticker,name,ARCHIVE_ALIAS_GROUPS[1]['sourceUrl'])
    elif symbol in ('CDAY','DAY'):
        set_label('CDAY' if cutoff<'2024-02-01' else 'DAY','Ceridian HCM Holding Inc.' if cutoff<'2024-01-31' else 'Dayforce, Inc.',ARCHIVE_ALIAS_GROUPS[2]['sourceUrl'])
    elif symbol=='ANDV':
        set_label('TSO' if cutoff<'2017-08-01' else 'ANDV','Tesoro Corporation' if cutoff<'2017-08-01' else 'Andeavor',
                  'https://www.sec.gov/Archives/edgar/data/50104/000005010417000180/andvnamechange8-k.htm')
    elif symbol in ('SYMC','NLOK','GEN'):
        ticker,name=('SYMC','Symantec Corporation') if cutoff<'2019-11-04' else ('NLOK','NortonLifeLock Inc.') if cutoff<'2022-11-07' else ('GEN','Gen Digital Inc.')
        set_label(ticker,name,'https://www.sec.gov/Archives/edgar/data/849399/000110465919059239/tm1921662d1_8k.htm' if cutoff<'2022-01-01' else 'https://www.sec.gov/Archives/edgar/data/849399/000084939922000026/gen-20220930.htm')
    elif symbol in ('TMK','GL'):
        set_label('TMK' if cutoff<'2019-08-08' else 'GL','Torchmark Corporation' if cutoff<'2019-08-08' else 'Globe Life Inc.',VERIFIED_YAHOO_ALIASES[('TMK',320335)][1])
    elif symbol=='CLF':
        set_label('CLF','Cliffs Natural Resources Inc.' if cutoff<'2017-08-15' else 'Cleveland-Cliffs Inc.',
                  'https://www.sec.gov/Archives/edgar/data/764065/000076406517000148/a20170815-8xkxex991.htm')
    elif symbol in ('FOX','FOXA') and cutoff<'2019-03-19':
        set_label(('NWS' if symbol=='FOX' else 'NWSA') if cutoff<'2013-06-28' else symbol,
                  'News Corporation' if cutoff<'2013-06-28' else 'Twenty-First Century Fox, Inc.',
                  'https://www.sec.gov/Archives/edgar/data/1308161/000119312513235936/d543738dex992.htm')
    elif symbol=='ARNC' and record and record['cik']=='0000004281':
        set_label('AA' if cutoff<'2016-11-01' else 'ARNC','Alcoa Inc.' if cutoff<'2016-11-01' else 'Arconic Inc.',
                  'https://www.sec.gov/Archives/edgar/data/4281/000000428121000049/arnc-20201231.htm')
    return label


def read(path, default=None):
    try:
        raw=path.read_bytes()
        return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    except (OSError, ValueError): return default


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(gzip.compress(raw,mtime=0) if path.suffix=='.gz' else raw)
    temp.replace(path)


def refresh_sources():
    import requests
    SOURCE.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,url in SOURCE_URLS.items():
        response=requests.get(url,headers={'User-Agent':'Hetzerk research info@ofnectar.com'},timeout=60)
        response.raise_for_status();raw=response.content
        (SOURCE/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
        manifest.append({'file':name,'url':url,'sha256':hashlib.sha256(raw).hexdigest(),
                         'retrievedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),'bytes':len(raw)})
    write(SOURCE/'manifest.json',manifest)


def load_sources():
    manifest=read(SOURCE/'manifest.json',[])
    for entry in manifest:
        raw=(SOURCE/entry['file']).read_bytes()
        if entry['file'].endswith('.gz'):raw=gzip.decompress(raw)
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('Cached source hash changed: '+entry['file'])
    history=list(csv.DictReader(io.StringIO(gzip.decompress((SOURCE/'historical_snapshots.csv.gz').read_bytes()).decode())))
    metadata=list(csv.DictReader(io.StringIO((SOURCE/'components_history.csv').read_text())))
    current=read(SOURCE/'sec_company_tickers.json',{})
    if not history or not metadata or not current:raise ValueError('Historical source caches are required')
    return history,metadata,current,manifest


def import_wiki(archive_path,universe=None):
    """Retain only observed sample sessions, not the 1.8GB historical archive."""
    universe=universe or read(DATA/'universe.json')
    dates=set(universe['sampleDates'])
    cache={};counts=Counter();first={};last={};splits=defaultdict(list);split_gaps=defaultdict(list)
    with ZipFile(archive_path) as archive:
        with archive.open('WIKI_PRICES.csv') as binary:
            reader=csv.DictReader(io.TextIOWrapper(binary,encoding='utf-8'))
            for row in reader:
                ticker=row['ticker'];d=row['date']
                counts[ticker]+=1;first.setdefault(ticker,d);last[ticker]=d
                try:split=float(row['split_ratio'])
                except (ValueError,TypeError):
                    split=None
                    if row.get('close') and row['close'].lower()!='nan':split_gaps[ticker].append(d)
                if split is not None and math.isfinite(split) and split>0 and split!=1:
                    splits[ticker].append({'date':d,'ratio':split})
                if d not in dates:continue
                try:close=float(row['close']);adjusted=float(row['adj_close'])
                except (ValueError,TypeError):continue
                if not all(math.isfinite(v) and v>0 for v in (close,adjusted)):continue
                cache.setdefault(ticker,[]).append({'date':d,'close':close,'adjustedClose':adjusted})
    with Path(archive_path).open('rb') as source_file:
        archive_hash=hashlib.file_digest(source_file,'sha256').hexdigest()
    result={'source':'Quandl WIKI frozen archive, public Kaggle mirror',
            'sourceUrl':'https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites',
            'archiveSha256':archive_hash,
            'archiveLastDate':max(last.values()),'license':'Mirror metadata states Unknown; source observation extracts only; raw archive is not redistributed.',
            'sampleDates':sorted(dates),'series':{k:{'points':v,'firstDate':first[k],'lastDate':last[k],'dailyObservationCount':counts[k],'splits':splits[k],'splitsStatus':'unavailable' if split_gaps[k] else 'complete-through-archive-end','splitGaps':split_gaps[k]} for k,v in cache.items()},
            'tickerInventory':{k:{'firstDate':first[k],'lastDate':last[k],'dailyObservationCount':v} for k,v in counts.items()}}
    write(DATA/'wiki-prices.json.gz',result)
    print(f'Archived WIKI: {len(result["series"])} sampled tickers; {sum(len(v) for v in cache.values())} observed points',flush=True)
    return result


def refresh_yahoo_archive(universe,workers=5):
    """Read specific files from a CC0 April-2020 Yahoo archive, retaining proof."""
    import requests
    from urllib.parse import quote
    cache=read(DATA/'yahoo-2020-prices.json.gz',{})
    root_url='https://www.kaggle.com/api/v1/datasets/download/jacksoncrow/stock-market-dataset'
    if not (SOURCE/'yahoo_2020_symbols.csv').exists():
        response=requests.get(root_url+'?fileName=symbols_valid_meta.csv',timeout=60)
        response.raise_for_status();(SOURCE/'yahoo_2020_symbols.csv').write_bytes(response.content)
    names={r['Symbol']:r for r in csv.DictReader(io.StringIO((SOURCE/'yahoo_2020_symbols.csv').read_text()))}
    symbols=sorted({a['sourceTicker'].replace('.','-') for a in universe['assets'] if a['id']!='SPY' and
                    not a.get('yahooSymbol') and any(y>=2016 for y in a['membershipYears'])})
    sample=set(universe['sampleDates'])
    def fetch(symbol):
        if symbol not in names:return {'status':'unavailable','reason':'Not in the April-2020 archived symbol roster.'}
        url=root_url+'?fileName='+quote('stocks/'+symbol+'.csv',safe='')
        response=requests.get(url,timeout=60);response.raise_for_status()
        rows=list(csv.DictReader(io.StringIO(response.text)));points=[]
        for row in rows:
            if row['Date'] not in sample:continue
            try:value=float(row['Adj Close'])
            except (ValueError,TypeError):continue
            if math.isfinite(value) and value>0:points.append({'date':row['Date'],'adjustedClose':value,'close':None})
        if not points:raise ValueError('No archived sample observations')
        return {'status':'ok','symbol':symbol,'name':names[symbol].get('Security Name'),
                'points':points,'sourceUrl':'https://www.kaggle.com/datasets/jacksoncrow/stock-market-dataset',
                'downloadUrl':url,'sha256':hashlib.sha256(response.content).hexdigest(),
                'lastArchiveDate':rows[-1]['Date'],'license':'CC0: Public Domain',
                'note':'Archived Yahoo adjusted-close return path; archived split-adjusted Close is not used as a contemporaneous valuation quote.'}
    missing=[s for s in symbols if s not in cache]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(fetch,s):s for s in missing}
        for index,future in enumerate(as_completed(jobs),1):
            symbol=jobs[future]
            try:cache[symbol]=future.result()
            except Exception as exc:cache[symbol]={'status':'unavailable','reason':type(exc).__name__}
            if index%20==0:write(DATA/'yahoo-2020-prices.json.gz',cache);print(f'Yahoo archive {index}/{len(jobs)}',flush=True)
    write(DATA/'yahoo-2020-prices.json.gz',cache)
    return cache


def refresh_later_archive(universe,workers=5):
    """Read individual frozen 2022 files; do not download the bulk archive."""
    import requests
    from urllib.parse import quote
    cache=read(DATA/'yahoo-2022-prices.json.gz',{})
    source_url='https://www.kaggle.com/datasets/paultimothymooney/stock-market-data'
    root_url='https://www.kaggle.com/api/v1/datasets/download/paultimothymooney/stock-market-data'
    symbols=sorted({a['sourceTicker'].replace('.','-') for a in universe['assets'] if a['id']!='SPY' and
                    not a.get('yahooSymbol') and any(y>=2018 for y in a['membershipYears'])})
    sample=set(universe['sampleDates'])
    def fetch(symbol):
        response=None
        for folder in ('sp500','forbes2000','nasdaq','nyse'):
            url=root_url+'?fileName='+quote('stock_market_data/'+folder+'/csv/'+symbol+'.csv',safe='')
            response=requests.get(url,timeout=60)
            if response.status_code==200 and response.text.startswith('Date,Low,Open,Volume,High,Close,Adjusted Close'):break
        else:return {'status':'unavailable','reason':'No matching archived CSV in the frozen 2022 collection.'}
        rows=list(csv.DictReader(io.StringIO(response.text)));points=[];last=None
        final_source_date=datetime.strptime(rows[-1]['Date'],'%d-%m-%Y').date().isoformat() if rows else None
        for row in rows:
            d=datetime.strptime(row['Date'],'%d-%m-%Y').date().isoformat();last=d
            # The mirror's final December-2022 rows differ by download folder
            # and were captured intraday; never treat that row as a close.
            if d not in sample or d==final_source_date:continue
            try:value=float(row['Adjusted Close'])
            except (ValueError,TypeError):continue
            if math.isfinite(value) and value>0:points.append({'date':d,'adjustedClose':value,'close':None})
        if not points:raise ValueError('No archived sample observations')
        return {'status':'ok','symbol':symbol,'points':points,'sourceUrl':source_url,
                'downloadUrl':url,'sha256':hashlib.sha256(response.content).hexdigest(),
                'lastArchiveDate':last,'license':'Mirror metadata: Other (specified in description); description supplies no further license terms. Raw files are not redistributed.',
                'note':'Frozen adjusted-close observations; source split-adjusted Close is not treated as a contemporaneous valuation quote. Final source rows are excluded because some were captured intraday.'}
    missing=[s for s in symbols if s not in cache]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(fetch,s):s for s in missing}
        for index,future in enumerate(as_completed(jobs),1):
            symbol=jobs[future]
            try:cache[symbol]=future.result()
            except Exception as exc:cache[symbol]={'status':'unavailable','reason':type(exc).__name__}
            if index%20==0:write(DATA/'yahoo-2022-prices.json.gz',cache);print(f'2022 archive {index}/{len(jobs)}',flush=True)
    write(DATA/'yahoo-2022-prices.json.gz',cache)
    return cache


def import_apr2022(archive_path,universe):
    """Import the source CSV's actual adjusted closes, without filling rows."""
    source_url='https://www.kaggle.com/datasets/hanseopark/sp-500-stocks-value-with-financial-statement'
    sample=set(universe['sampleDates']);series={};last={}
    with ZipFile(archive_path) as archive:
        raw=archive.read('FS_sp500_Value.csv')
    digest=hashlib.sha256(raw).hexdigest()
    for row in csv.DictReader(io.StringIO(raw.decode())):
        symbol=row['Ticker'];d=row['Date'];last[symbol]=d
        if d not in sample:continue
        try:value=float(row['Adj Close'])
        except (ValueError,TypeError):continue
        if math.isfinite(value) and value>0:series.setdefault(symbol,[]).append({'date':d,'adjustedClose':value,'close':None})
    result={s:{'status':'ok','symbol':s,'points':p,'sourceUrl':source_url,
               'downloadUrl':'https://www.kaggle.com/api/v1/datasets/download/hanseopark/sp-500-stocks-value-with-financial-statement?fileName=data_origin%2FFS_sp500_Value.csv',
               'sha256':digest,'sourceFile':'FS_sp500_Value.csv','lastArchiveDate':last[s],
               'license':'CC0: Public Domain','note':'April-2022 Yahoo archive; source Adj Close used as the whole return proxy path. No missing observations inferred.'} for s,p in series.items()}
    write(DATA/'yahoo-apr2022-prices.json.gz',result)
    print(f'April-2022 archive: {len(result)} observed ticker histories',flush=True)
    return result


def import_jul2025(csv_path,universe):
    """Read the frozen multi-header CSV's explicit dividend-adjusted column."""
    raw=Path(csv_path).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    reader=csv.reader(io.StringIO(raw.decode()))
    tickers=next(reader);fields=next(reader);date_row=next(reader)
    if tickers[0]!='Ticker' or fields[0]!='Price' or date_row[0]!='Date':
        raise ValueError('Unexpected frozen July-2025 archive headers')
    columns={tickers[i]:i for i,f in enumerate(fields) if f=='Adj Close'}
    sample=set(universe['sampleDates']);series=defaultdict(list);last=None
    for row in reader:
        d=row[0];last=d
        if d not in sample:continue
        for symbol,index in columns.items():
            try:value=float(row[index])
            except (ValueError,IndexError):continue
            if math.isfinite(value) and value>0:series[symbol].append({'date':d,'adjustedClose':value,'close':None})
    if last!='2025-07-11':raise ValueError('Archive endpoint changed; review and pin the new edition')
    source_url='https://www.kaggle.com/datasets/quyuet/sp500-prices-data'
    result={s:{'status':'ok','symbol':s,'points':[p for p in points if p['date']<last],
               'sourceUrl':source_url,'downloadUrl':'https://www.kaggle.com/api/v1/datasets/download/quyuet/sp500-prices-data?fileName=sp500_prices_2009_2025.csv',
               'sha256':digest,'lastArchiveDate':last,'license':'CC BY-SA 4.0',
               'note':'Source CSV explicit Adj Close field; sampled observations only, no inferred prices. The final source session is excluded conservatively.'}
            for s,points in series.items()}
    write(DATA/'yahoo-jul2025-prices.json.gz',result)
    print(f'July-2025 archive: {len(result)} observed ticker histories',flush=True)
    return result


def refresh_archive_2023(universe,workers=5):
    """Verify archived adjusted Close against an independent adjusted path."""
    import requests
    from urllib.parse import quote
    prior=read(DATA/'universe.json',{})
    references={a['id']:a for a in prior.get('assets',[])}
    cache=read(DATA/'yahoo-2023-prices.json.gz',{})
    source_url='https://www.kaggle.com/datasets/tanavbajaj/yahoo-finance-all-stocks-dataset-daily-update'
    root_url='https://www.kaggle.com/api/v1/datasets/download/tanavbajaj/yahoo-finance-all-stocks-dataset-daily-update'
    sample=set(universe['sampleDates'])
    assets={archive_symbol_at(a,'2023-09-21'):a for a in universe['assets'] if a['id']!='SPY' and not a.get('yahooSymbol') and any(y>=2018 for y in a['membershipYears'])}
    def fetch(symbol,asset):
        url=root_url+'?fileName='+quote(symbol+'.csv',safe='')
        response=requests.get(url,timeout=60)
        if response.status_code==404:return {'status':'unavailable','reason':'Not in the frozen September-2023 archive.'}
        response.raise_for_status();raw=response.content
        if raw.startswith(b'PK'):
            with ZipFile(io.BytesIO(raw)) as archive:raw=archive.read(symbol+'.csv')
        rows=list(csv.DictReader(io.StringIO(raw.decode())))
        if not rows or not {'Date','Close','Dividends','Stock Splits'}<=set(rows[0]):raise ValueError('Unexpected archive schema')
        final_date=rows[-1]['Date'][:10];points=[]
        for row in rows:
            d=row['Date'][:10]
            if d not in sample or d==final_date:continue
            value=float(row['Close'])
            if math.isfinite(value) and value>0:points.append({'date':d,'adjustedClose':value,'close':None})
        reference=references.get(asset['id'],{})
        x={p['date']:p['adjustedClose'] for p in points};y={p['date']:p['adjustedClose'] for p in reference.get('points',[])}
        dates=sorted(x.keys()&y.keys())
        errors=[abs(x[b]/x[a]-y[b]/y[a]) for a,b in zip(dates,dates[1:])]
        rms=math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None
        verified=len(errors)>=24 and rms<0.00001 and max(errors)<0.0001
        if not verified:return {'status':'unavailable','reason':'Archived Close adjustment basis did not meet independent overlapping-return verification.',
                               'verification':{'matchedIntervals':len(errors),'rmsDifference':rms,'maximumDifference':max(errors) if errors else None}}
        return {'status':'ok','symbol':symbol,'points':points,'sourceUrl':source_url,'downloadUrl':url,
                'sha256':hashlib.sha256(raw).hexdigest(),'lastArchiveDate':final_date,
                'license':'Open Database License; underlying contents credited to original authors.',
                'basisVerification':{'matchedIntervals':len(errors),'rmsDifference':rms,'maximumDifference':max(errors),
                                     'referenceSource':reference.get('returnSource'),'referenceEdition':prior.get('version')},
                'note':'Archived Yahoo Close is fully adjusted: overlapping sampled returns verified against independently archived adjusted-close observations. Final intraday source row excluded. No dividends added twice.'}
    missing=[s for s in assets if s not in cache or (cache[s].get('status')!='ok' and 'verification' in cache[s])]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(fetch,s,assets[s]):s for s in missing}
        for index,future in enumerate(as_completed(jobs),1):
            symbol=jobs[future]
            try:cache[symbol]=future.result()
            except Exception as exc:cache[symbol]={'status':'unavailable','reason':type(exc).__name__}
            if index%20==0:write(DATA/'yahoo-2023-prices.json.gz',cache);print(f'2023 archive {index}/{len(jobs)}',flush=True)
    write(DATA/'yahoo-2023-prices.json.gz',cache)
    return cache


def archive_alias_group(asset):
    return next((g for g in ARCHIVE_ALIAS_GROUPS if asset.get('cik')==g['cik'] and asset['sourceTicker'] in g['symbols']),None)


def archive_symbol_at(asset,snapshot_date):
    group=archive_alias_group(asset)
    return max((e for e in group['eras'] if e[0]<=snapshot_date),key=lambda e:e[0])[1] if group else asset['sourceTicker'].replace('.','-')


def archive_identity_matches(asset,snapshot_date,metadata):
    record=choose_metadata(archive_symbol_at(asset,snapshot_date),snapshot_date,metadata)
    return record is not None and int(record['cik'])==asset.get('cik')


def source_date(value):
    return value.rstrip('*') if value else ''


def choose_metadata(symbol, cutoff, records):
    """Resolve historical identity evidence without requiring present membership."""
    source_symbol=METADATA_ALIASES.get(symbol,symbol)
    candidates=[r for r in records if r['symbol']==source_symbol]
    if not candidates:return None
    if len({r['cik'] for r in candidates})>1:
        existed=[r for r in candidates if r['created_at']<=cutoff]
        if existed:candidates=existed
    active=[r for r in candidates if source_date(r['date_added'])<=cutoff and
            (not r['date_removed'] or cutoff<source_date(r['date_removed']))]
    # Some upstream aliases are retrospective. Closest historical era is
    # retained as metadata evidence, not asserted as an exact membership date.
    pool=active or [r for r in candidates if source_date(r['date_added'])<=cutoff] or candidates
    chosen=dict(max(pool,key=lambda r:source_date(r['date_added'])))
    if symbol=='CLF':
        chosen.update(cik='0000764065',identitySourceUrl='https://www.sec.gov/Archives/edgar/data/764065/000119312509039184/d10k.htm')
    if symbol in ('FOX','FOXA') and cutoff<'2019-03-19':
        chosen.update(cik='0001308161',name='News Corporation' if cutoff<'2013-06-28' else 'Twenty-First Century Fox, Inc.',date_removed='2019-03-19',
                      identitySourceUrl='https://www.sec.gov/Archives/edgar/data/1308161/000119312513235936/d543738dex992.htm')
    # The old Chubb Corporation and the acquiring ACE are different securities.
    if symbol=='CB' and cutoff<'2016-01-14':
        chosen.update(cik='0000020171',name='The Chubb Corporation',symbol='CB')
    if symbol=='JCI' and cutoff<'2016-09-02':
        chosen.update(cik='0000053669',name='Johnson Controls Inc.',symbol='JCI',date_removed='2016-09-02',
                      identitySourceUrl='https://investors.johnsoncontrols.com/~/media/Files/J/Johnson-Controls-IR/annual-meeting-materials/fy17-jci-plc-irish-f-s.pdf')
    return chosen


def yahoo_mapping(symbol, cik, current):
    by_symbol={r['ticker'].replace('.','-'):r for r in current.values()}
    normalized=symbol.replace('.','-')
    if symbol=='DISCK':
        return None,'Discovery Class C is distinct from Class A before their April-2022 conversion. The modern WBD Class-A lineage cannot replace historical DISCK returns.'
    if symbol in BLOCKED_REISSUES:
        return None,'Original distressed common-share history and terminal payoff are unavailable; no post-bankruptcy replacement security is substituted.'
    exact=by_symbol.get(normalized)
    verified=VERIFIED_YAHOO_ALIASES.get((symbol,int(cik))) if cik else None
    if verified and str(by_symbol.get(verified[0],{}).get('cik_str')).zfill(10)==cik:
        return verified[0],'Common-stock alias verified from corporate history and matching SEC CIK; '+verified[1]
    if exact and str(exact['cik_str']).zfill(10)==cik:
        return normalized,'Current SEC ticker and historical issuer CIK agree; Yahoo adjusted history is a return proxy, not a separately reconstructed corporate-action ledger.'
    alternatives=[r['ticker'].replace('.','-') for r in current.values() if str(r['cik_str']).zfill(10)==cik]
    if len(alternatives)==1:
        return alternatives[0],'Historical alias mapped to the current SEC ticker for the same issuer CIK; corporate restructurings and historical share-class continuity are not independently reconstructed.'
    if exact:
        return None,'Ticker now identifies another issuer CIK; automatic substitution is prohibited.'
    return None,'No unique current SEC issuer/ticker mapping. Historical member is retained, but delisted or ambiguous return history needs a verified security source.'


def historical_price_bounds(symbol,record):
    """Conservative identity boundary for old archive symbols, not a payoff.

    Index removal is earlier than, or near, many terminal transactions. It is
    intentionally used only as an upper bound when no current CIK/ticker match
    supports continuity; the remaining year is missing, never liquidated there.
    """
    from datetime import timedelta
    end=source_date(record.get('date_removed')) if record else ''
    evidence=ARCHIVE_END_OVERRIDES.get(symbol)
    if evidence:end=evidence[0]
    if symbol=='CB' and record and record['cik']=='0000020171':end='2016-01-14'
    if end:end=(date.fromisoformat(end)-timedelta(days=1)).isoformat()
    start=None
    if symbol=='AGN' and record and record['cik']=='0001578845':start='2015-06-15'
    if symbol in ('DD','DOW','CEG','DELL') and record and record['created_at']>'2015-01-01':
        start=max(record['created_at'],source_date(record['date_added']))
    return {'start':start,'end':end or None,**({'sourceUrl':evidence[1],'note':'Verified later corporate event bounds the original security after index removal; no transaction proceeds are inferred.'} if evidence else {})}


def trading_calendar():
    market=read(ROOT/'data'/'etf_comparison.json',{})
    spy=next((s for s in market.get('series',[]) if s.get('id')=='SPY'),None)
    if not spy or not spy.get('observations'):raise ValueError('Observed SPY session calendar is required')
    return spy


def build_universe():
    history,metadata,current,manifest=load_sources()
    spy=trading_calendar()
    calendar=[p['date'] for p in spy['observations']]
    asof=calendar[-1]
    assets={};rounds=[];source_disagreements=[]
    last_membership=max(r['date'] for r in history)
    year_end=min(int(asof[:4])-1,int(last_membership[:4]))
    warnings=[]
    if year_end<int(asof[:4])-1:
        warnings.append('Historical membership source does not cover the next decision year. Refresh sources before extending the game.')
    if last_membership<f'{year_end}-12-31':
        warnings.append('Latest historical roster change predates the final decision cutoff; no later membership changes are inferred. Review source currency.')
    for year in range(YEAR_START,year_end+1):
        cutoff=f'{year}-12-31'
        execution=next(d for d in calendar if d>cutoff)
        next_cutoff=f'{year+1}-12-31'
        end=next((d for d in calendar if d>next_cutoff),asof)
        if execution>=end:
            warnings.append('The newest annual decision has fewer than two observed sessions and is not yet playable.')
            continue
        snapshots=[r for r in history if r['date']<=cutoff]
        snapshot=max(snapshots,key=lambda r:r['date'])
        symbols=sorted(set(snapshot['tickers'].split(',')))
        if not 450<=len(symbols)<=530:raise ValueError('Unexpected historical constituent count')
        eligible=[]
        for symbol in symbols:
            if not re.fullmatch(r'[A-Z0-9.\-]+',symbol):raise ValueError('Invalid source symbol')
            record=choose_metadata(symbol,cutoff,metadata)
            cik=record['cik'] if record else None
            identity='cik-'+cik+'-'+symbol.replace('.','-') if cik else 'unresolved-'+symbol
            if identity not in assets:
                yahoo,note=yahoo_mapping(symbol,cik,current) if cik else (None,'Historical issuer CIK is unresolved; no modern symbol is substituted.')
                assets[identity]={'id':identity,'ticker':symbol,'sourceTicker':symbol,
                    'name':record['name'] if record else symbol,'cik':int(cik) if cik else None,
                    'sector':record['sector'].replace('_',' ').title() if record else 'Unclassified',
                    'yahooSymbol':yahoo,'identityStatus':'historical-source-metadata' if cik else 'unresolved',
                    'identityNote':note,'identitySourceUrl':record.get('identitySourceUrl',METADATA_URL) if record else METADATA_URL,
                    'membershipYears':[],'historicalLabels':{},'priceStatus':'not-refreshed','points':[]}
                assets[identity]['filingCiks']=filing_ciks(symbol,int(cik)) if cik else []
                assets[identity]['archiveSymbol']=WIKI_ALIASES.get(symbol,symbol)
                assets[identity]['archiveIdentityBounds']=historical_price_bounds(symbol,record)
                if symbol=='DISCK':
                    assets[identity]['blockedPriceSources']=['Yahoo Finance adjusted close']
                    assets[identity]['identitySourceUrl']='https://www.sec.gov/Archives/edgar/data/1437107/000119312522103051/d328161d8k.htm'
                group=archive_alias_group(assets[identity])
                if group:
                    assets[identity]['archiveSymbol']=group['wiki']
                    latest=choose_metadata(group['symbols'][-1],asof,metadata)
                    if latest and int(latest['cik'])==int(cik):
                        assets[identity]['archiveIdentityBounds']=historical_price_bounds(group['symbols'][-1],latest)
                        assets[identity]['archiveIdentityBounds']['continuitySourceUrl']=group['sourceUrl']
                if symbol=='GOOG':
                    # Yahoo backcasts GOOG before this class existed. The older
                    # listed Class A is represented by GOOGL, not this path.
                    assets[identity]['securityStartDate']='2014-04-03'
                    assets[identity]['securityStartSourceUrl']=GOOGLE_CLASS_SOURCE
                    assets[identity]['archiveIdentityBounds']['start']='2014-04-03'
            asset=assets[identity]
            asset['membershipYears'].append(year)
            asset['historicalLabels'][str(year)]=historical_label(symbol,cutoff,record)
            eligible.append(identity)
        observed=[d for d in calendar if execution<=d<=end]
        last_month={d[:7]:d for d in observed}
        grid=sorted(set(last_month.values())|{execution,end})
        rounds.append({'year':year,'cutoff':cutoff,'executionDate':execution,'endDate':end,
                       'isPartial':end==asof,'eligibleAssetIds':eligible,'valuationDates':grid,
                       'membershipSourceDate':snapshot['date'],'membershipCount':len(eligible)})
        reference={r['symbol'] for r in metadata if source_date(r['date_added'])<=cutoff and r['created_at']<=cutoff and (not r['date_removed'] or cutoff<source_date(r['date_removed']))}
        source_disagreements.append({'year':year,'primaryCount':len(symbols),'metadataReconstructionCount':len(reference),
                                    'primaryOnly':sorted(set(symbols)-reference),'metadataOnly':sorted(reference-set(symbols))})
    # Predecision closes support valuation ratios; they are not future quotes.
    dates=set(d for r in rounds for d in r['valuationDates'])
    dates.update(max(d for d in calendar if d<=r['cutoff']) for r in rounds)
    benchmark={'id':'SPY','ticker':'SPY','name':'SPDR S&P 500 ETF Trust','cik':None,'sector':'Benchmark',
               'yahooSymbol':'SPY','membershipYears':[],'historicalLabels':{},'priceStatus':'ok',
               'points':[{'date':p['date'],'close':p['market_price'],'adjustedClose':p['adjusted_close']} for p in spy['observations'] if p['date'] in dates and p.get('adjusted_close') is not None],
               'splits':[],'sourceUrl':spy['source_url']}
    payload={'schema_version':1,'id':'hetzerk-annual-portfolio','version':'membership-preview','asOf':asof,
             'frequency':'monthly','benchmarkAssetId':'SPY','rounds':rounds,'assets':list(assets.values())+[benchmark],
             'sampleDates':sorted(dates),'sources':manifest,'membershipSourceUrl':MEMBERSHIP_URL,
             'sourceWarnings':warnings,'membershipLastChange':last_membership,
             'limitations':['Historical rosters are a public reconstruction, not a licensed official S&P constituent record.',
              'Upstream historical snapshots sometimes use later ticker aliases; CIK metadata has known historical inconsistencies.',
              'Every historical member is retained. Missing, delisted or ambiguous return histories are explicitly unavailable.',
              'Yahoo adjusted close is a split/dividend return proxy. Complex merger, spin-off and bankruptcy shareholder payoffs have not been independently reconstructed.',
              'Available-price selections can create survivorship bias. Coverage is disclosed for every annual roster.'],
             'membershipCrossCheck':source_disagreements}
    return payload


def fetch_price(symbol):
    import yfinance as yf
    ticker=yf.Ticker(symbol)
    frame=ticker.history(period='max',interval='1d',auto_adjust=False,actions=True,repair=False)
    meta=ticker.get_history_metadata()
    if frame.empty or 'Stock Splits' not in frame.columns or meta.get('currency')!='USD' or meta.get('symbol','').upper()!=symbol:
        raise ValueError('No verified USD Yahoo history for the mapped symbol')
    points=[];splits=[]
    for stamp,row in frame.iterrows():
        close=float(row['Close']);adjusted=float(row['Adj Close']);d=stamp.date().isoformat()
        split=float(row.get('Stock Splits',0))
        if math.isfinite(split) and split>0:splits.append({'date':d,'ratio':split})
        if not all(math.isfinite(v) and v>0 for v in (close,adjusted)) or d<'2010-01-01':continue
        points.append({'date':d,'close':close,'adjustedClose':adjusted})
    if not points:raise ValueError('Empty adjusted history')
    return {'symbol':symbol,'status':'ok','currency':'USD','points':points,'splits':splits,
            'priceBasisAsOf':frame.index[-1].date().isoformat(),
            'splitsStatus':'complete','splitsAsOf':frame.index[-1].date().isoformat(),
            'splitsFrom':frame.index[0].date().isoformat(),'splitsRequest':'Yahoo max daily history with actions=True; Stock Splits column verified.',
            'retrievedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'sourceUrl':f'https://finance.yahoo.com/quote/{symbol}/history/'}


def needs_price_refresh(source,asof):
    return source.get('status')!='ok' or not source.get('points') or source['points'][-1]['date']<asof


def refresh_prices(universe,limit=None,workers=5):
    cache=read(DATA/'prices.json.gz',{})
    existing=read(ROOT/'data'/'innovation'/'price-cache.json.gz',{})
    symbols=sorted({a['yahooSymbol'] for a in universe['assets'] if a.get('yahooSymbol') and a['id']!='SPY'})
    for value in existing.values():
        symbol=value.get('ticker')
        if symbol in symbols and value.get('status')=='ok' and value.get('points'):
            cache.setdefault(symbol,{**value,'symbol':symbol})
    missing=[s for s in symbols if needs_price_refresh(cache.get(s,{}),universe['asOf']) or
             cache.get(s,{}).get('splitsStatus')!='complete' or (cache.get(s,{}).get('splitsAsOf') or '')<universe['asOf']]
    if limit is not None:missing=missing[:limit]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs={pool.submit(fetch_price,s):s for s in missing}
        for index,future in enumerate(as_completed(jobs),1):
            symbol=jobs[future]
            try:cache[symbol]=future.result()
            except Exception as exc:
                if cache.get(symbol,{}).get('points'):
                    cache[symbol]['refreshError']=type(exc).__name__
                else:cache[symbol]={'symbol':symbol,'status':'unavailable','points':[],'error':type(exc).__name__}
            if index%20==0:write(DATA/'prices.json.gz',cache);print(f'Price cache {index}/{len(jobs)}',flush=True)
    write(DATA/'prices.json.gz',cache)
    return cache


PRICE_FIELDS=('points','splits','splitsStatus','splitsAsOf','splitsFrom','priceBasis',
              'priceBasisAsOf','returnSource','sourceUrl','archiveProvenance','valuationQuoteSource','priceStatus','priceReason','excludedObservations')


def path_coverage_score(points,asset,universe):
    known={p['date'] for p in points}
    complete=sum(set(r['valuationDates'])<=known for r in universe['rounds'] if r['year'] in asset['membershipYears'])
    return complete,len(known)


def attach_prices(universe,cache,previous=None):
    sampled=set(universe['sampleDates'])
    wiki=read(DATA/'wiki-prices.json.gz',{})
    yahoo_archive=read(DATA/'yahoo-2020-prices.json.gz',{})
    apr2022_archive=read(DATA/'yahoo-apr2022-prices.json.gz',{})
    later_archive=read(DATA/'yahoo-2022-prices.json.gz',{})
    archive_2023=read(DATA/'yahoo-2023-prices.json.gz',{})
    archive_2025=read(DATA/'yahoo-jul2025-prices.json.gz',{})
    _,identity_metadata,_,_=load_sources()
    previous=previous or {}
    prior_assets={a['id']:a for a in previous.get('assets',[])}
    retained=False
    by_id={a['id']:a for a in universe['assets']}
    for asset in universe['assets']:
        if asset['id']=='SPY':continue
        source=cache.get(asset.get('yahooSymbol'),{})
        asset['points']=[p for p in source.get('points',[]) if p['date'] in sampled and p['date']<=universe['asOf'] and
                         (not asset.get('securityStartDate') or p['date']>=asset['securityStartDate'])]
        # Yahoo historical Close is normalized through the provider's latest
        # adjustment date, even when the game's SPY calendar is older.
        asset['splits']=[s for s in source.get('splits',[]) if not asset.get('securityStartDate') or s['date']>=asset['securityStartDate']]
        asset['splitsStatus']=source.get('splitsStatus','unavailable')
        asset['splitsAsOf']=source.get('splitsAsOf')
        asset['splitsFrom']=source.get('splitsFrom')
        if asset.get('splitsFrom') and asset.get('securityStartDate'):
            asset['splitsFrom']=max(asset['splitsFrom'],asset['securityStartDate'])
        asset['priceBasisAsOf']=source.get('priceBasisAsOf') or (source['points'][-1]['date'] if source.get('points') else None)
        asset['priceBasis']='yahoo-split-adjusted-close'
        asset['returnSource']='Yahoo Finance adjusted close'
        asset['sourceUrl']=source.get('sourceUrl')
        yahoo_candidate={k:asset[k] for k in PRICE_FIELDS if k in asset}
        if wiki or yahoo_archive or apr2022_archive or later_archive or archive_2023 or archive_2025:
            archived=wiki.get('series',{}).get(asset.get('archiveSymbol'),{})
            bounds=asset.get('archiveIdentityBounds',{})
            asset['points']=[p for p in archived.get('points',[]) if p['date'] in sampled and
                (not bounds.get('start') or p['date']>=bounds['start']) and
                (not bounds.get('end') or p['date']<=bounds['end'])]
            if asset['points']:
                asset['priceBasis']='contemporaneous-unadjusted-close'
                asset['priceBasisAsOf']=None
                asset['returnSource']='Quandl WIKI archived adjusted close'
                asset['sourceUrl']=wiki['sourceUrl']
                asset['archiveProvenance']={'archiveSha256':wiki['archiveSha256'],'ticker':asset['archiveSymbol'],
                    'lastArchiveDate':wiki['archiveLastDate'],'identityBounds':bounds,
                    'note':'No Yahoo/WIKI level stitching. Archive history is bounded conservatively where a later ticker may identify a different security; absent acquisition or bankruptcy payouts remain missing.'}
                asset['splits']=[s for s in archived.get('splits',[]) if (not bounds.get('start') or s['date']>=bounds['start']) and (not bounds.get('end') or s['date']<=bounds['end'])]
                asset['splitsStatus']='complete' if archived.get('splitsStatus')=='complete-through-archive-end' else 'unavailable'
                asset['splitsAsOf']=min(wiki['archiveLastDate'],bounds.get('end') or wiki['archiveLastDate'])
                asset['splitsFrom']=max(archived.get('firstDate','9999-12-31'),bounds.get('start') or '0001-01-01')
            def score(points):
                return path_coverage_score(points,asset,universe)
            for later,return_source,snapshot_date in ((yahoo_archive.get(archive_symbol_at(asset,'2020-04-01'),{}),'Yahoo Finance April-2020 archive adjusted close','2020-04-01'),
                                        (apr2022_archive.get(archive_symbol_at(asset,'2022-04-14'),{}),'Yahoo Finance April-2022 archive adjusted close','2022-04-14'),
                                        (later_archive.get(archive_symbol_at(asset,'2022-12-12'),{}),'Frozen December-2022 archive adjusted close','2022-12-12'),
                                        (archive_2023.get(archive_symbol_at(asset,'2023-09-21'),{}),'Verified Yahoo September-2023 archive adjusted close','2023-09-21'),
                                        (archive_2025.get(archive_symbol_at(asset,'2025-07-11'),{}),'Yahoo Finance July-2025 archive adjusted close','2025-07-11')):
                if not archive_identity_matches(asset,snapshot_date,identity_metadata):continue
                later_points=[p for p in later.get('points',[]) if p['date'] in sampled and p['date']<=universe['asOf'] and (not bounds.get('start') or p['date']>=bounds['start']) and (not bounds.get('end') or p['date']<=bounds['end'])]
                if score(later_points)<=score(asset['points']):continue
                # Return history comes entirely from one archive. Independent
                # WIKI raw closes may supply valuation quotes on their dates.
                raw_quotes={p['date']:p['close'] for p in archived.get('points',[])}
                asset['points']=[{**p,'close':raw_quotes.get(p['date'])} for p in later_points]
                asset['priceBasis']='contemporaneous-unadjusted-close'
                asset['priceBasisAsOf']=None
                asset['returnSource']=return_source
                asset['sourceUrl']=later['sourceUrl']
                asset['archiveProvenance']={k:v for k,v in later.items() if k!='points'}
                asset['valuationQuoteSource']='Quandl WIKI raw close on matching dates only; absent later raw quotes are null.'
                asset['splits']=[s for s in archived.get('splits',[]) if (not bounds.get('start') or s['date']>=bounds['start']) and (not bounds.get('end') or s['date']<=bounds['end'])]
                asset['splitsStatus']='complete' if archived.get('splitsStatus')=='complete-through-archive-end' else 'unavailable'
                asset['splitsAsOf']=min(wiki.get('archiveLastDate','9999-12-31'),bounds.get('end') or '9999-12-31') if wiki.get('archiveLastDate') else None
                asset['splitsFrom']=max(archived.get('firstDate','9999-12-31'),bounds.get('start') or '0001-01-01') if archived.get('firstDate') else None
        if path_coverage_score(yahoo_candidate.get('points',[]),asset,universe)>=path_coverage_score(asset['points'],asset,universe):
            for field in PRICE_FIELDS:
                asset.pop(field,None)
                if field in yahoo_candidate:asset[field]=yahoo_candidate[field]
        asset['priceStatus']='ok' if asset['points'] else 'unavailable'
        asset['priceReason']=None if asset['points'] else asset['identityNote'] if not asset.get('yahooSymbol') else 'Mapped Yahoo history is unavailable or does not cover the game observations.'
        prior=prior_assets.get(asset['id'])
        if prior and prior.get('returnSource') not in asset.get('blockedPriceSources',[]):
            bounds=asset.get('archiveIdentityBounds',{}) if not asset.get('yahooSymbol') else {}
            old_points=[p for p in prior.get('points',[]) if p['date'] in sampled and p['date']<=universe['asOf'] and
                        (not asset.get('securityStartDate') or p['date']>=asset['securityStartDate']) and
                        (not bounds.get('start') or p['date']>=bounds['start']) and (not bounds.get('end') or p['date']<=bounds['end'])]
            if path_coverage_score(old_points,asset,universe)>path_coverage_score(asset['points'],asset,universe):
                # Cold CI may have the reviewed publication but no ignored
                # provider cache. Retain a whole pinned path, never stitch its
                # adjusted levels into a new provider's history.
                for field in PRICE_FIELDS:
                    asset.pop(field,None)
                    if field in prior:asset[field]=prior[field]
                asset['points']=old_points
                asset['priceRetainedFromVersion']=previous.get('version')
                retained=True
    if retained:
        universe['retainedSourceEditions']=[{'version':previous.get('version'),'asOf':previous.get('asOf'),'sources':previous.get('sources',[])}]
    quarantine=read(DATA/'quality_flags.json',{})
    quality_count=0
    for flag in quarantine.get('flags',[]):
        asset=by_id.get(flag['assetId'])
        if not asset or asset.get('returnSource')!=flag['selectedSource']:continue
        excluded=next((p for p in asset['points'] if p['date']==flag['excludedDate']),None)
        asset.setdefault('qualityFlags',[]).append(flag)
        if excluded:
            asset.setdefault('excludedObservations',[]).append({**excluded,'qualityFlagId':flag['id'],
                'source':asset.get('returnSource'),'sourceUrl':asset.get('sourceUrl')})
            asset['points']=[p for p in asset['points'] if p['date']!=flag['excludedDate']]
        if excluded or any(p['date']==flag['excludedDate'] for p in asset.get('excludedObservations',[])):
            quality_count+=1
    universe['qualityAudit']={'asOf':quarantine.get('asOf'),'source':'data/annual-game/quality_flags.json',
                              'quarantinedObservations':quality_count,'scope':quarantine.get('scope')}
    summary=[]
    for rnd in universe['rounds']:
        complete=[];unavailable=[];grid=set(rnd['valuationDates'])
        for identity in rnd['eligibleAssetIds']:
            a=by_id[identity];available={p['date'] for p in a['points']};missing=sorted(grid-available)
            if missing:
                flagged=[f for f in a.get('qualityFlags',[]) if f['excludedDate'] in missing]
                reason='Observed adjustment disagreement is quarantined pending corporate-action review.' if flagged else a.get('priceReason') or 'Incomplete observed return path; no missing values or terminal payoff inferred.'
                unavailable.append({'id':identity,'ticker':a['ticker'],'missingObservations':len(missing),'firstMissing':missing[0],'reason':reason})
            else:complete.append(identity)
        rnd['coverage']={'members':len(rnd['eligibleAssetIds']),'priced':len(complete),'unavailable':len(unavailable)}
        summary.append({'year':rnd['year'],**rnd['coverage'],'unavailableAssets':unavailable})
    universe['coverage']={'assets':len(universe['assets'])-1,'withCik':sum(a.get('cik') is not None for a in universe['assets']),
                         'withSampledPrices':sum(bool(a['points']) for a in universe['assets'] if a['id']!='SPY'),
                         'archiveBackedAssets':sum(a.get('returnSource')=='Quandl WIKI archived adjusted close' and bool(a['points']) for a in universe['assets']),
                         'yahoo2020BackedAssets':sum(a.get('returnSource')=='Yahoo Finance April-2020 archive adjusted close' and bool(a['points']) for a in universe['assets']),
                         'yahooApril2022BackedAssets':sum(a.get('returnSource')=='Yahoo Finance April-2022 archive adjusted close' and bool(a['points']) for a in universe['assets']),
                         'archive2022BackedAssets':sum(a.get('returnSource')=='Frozen December-2022 archive adjusted close' and bool(a['points']) for a in universe['assets']),
                         'archive2023BackedAssets':sum(a.get('returnSource')=='Verified Yahoo September-2023 archive adjusted close' and bool(a['points']) for a in universe['assets']),
                         'archive2025BackedAssets':sum(a.get('returnSource')=='Yahoo Finance July-2025 archive adjusted close' and bool(a['points']) for a in universe['assets']),
                         'quarantinedObservations':quality_count,
                         'pointCount':sum(len(a['points']) for a in universe['assets']),'rounds':summary}
    universe['version']=hashlib.sha256(json.dumps({'rounds':universe['rounds'],'assets':universe['assets']},sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]
    write(DATA/'universe.json',universe)
    write(DATA/'coverage.json',universe['coverage'])
    return universe


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-prices',action='store_true')
    parser.add_argument('--refresh-sources',action='store_true')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--workers',type=int,default=5)
    parser.add_argument('--import-wiki',type=Path)
    parser.add_argument('--refresh-yahoo-archive',action='store_true')
    parser.add_argument('--refresh-2022-archive',action='store_true')
    parser.add_argument('--import-apr2022',type=Path)
    parser.add_argument('--refresh-2023-archive',action='store_true')
    parser.add_argument('--import-jul2025',type=Path)
    args=parser.parse_args()
    previous=read(DATA/'universe.json',{})
    if args.refresh_sources:refresh_sources()
    universe=build_universe()
    if args.import_wiki:import_wiki(args.import_wiki,universe)
    if args.refresh_yahoo_archive:refresh_yahoo_archive(universe,args.workers)
    if args.refresh_2022_archive:refresh_later_archive(universe,args.workers)
    if args.import_apr2022:import_apr2022(args.import_apr2022,universe)
    if args.import_jul2025:import_jul2025(args.import_jul2025,universe)
    if args.refresh_2023_archive:refresh_archive_2023(universe,args.workers)
    cache=refresh_prices(universe,args.limit,args.workers) if args.refresh_prices else read(DATA/'prices.json.gz',{})
    result=attach_prices(universe,cache,previous)
    print(json.dumps({k:v for k,v in result['coverage'].items() if k!='rounds'}))


if __name__=='__main__':main()
