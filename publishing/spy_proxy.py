"""Temporary public holdings overlay; workbook remains the terms/history source."""
from copy import deepcopy
from decimal import Decimal
from datetime import date
from hashlib import sha256
import json
from urllib.parse import urlsplit

D=Decimal


def public_input(report):
    # No ledger, events, pricing exceptions or private runtime paths enter Pages.
    return dict(schema_version=1,as_of=report['as_of'],source_fund='SPY',
                source_url=report['manifest']['files']['holdings']['url'],
                source_sha256=report['manifest']['files']['holdings']['sha256'],
                nav_source_url=report['manifest']['files']['nav']['url'],
                nav_source_sha256=report['manifest']['files']['nav']['sha256'],
                issuer_net_assets=report['official']['net_assets'],
                holdings=[{k:h[k] for k in ('identifier','ticker','name','sector','quantity','issuer_weight','security_type')}
                          for h in report.get('publication_holdings',report['positions'])],
                methodology='Common-stock weights normalized to the workbook equity allocation; workbook cash allocation retained. '
                            'Prices inferred from rounded issuer weights and net assets, not executable quotes. '
                            'Quantities rescaled to workbook net assets. The CVR is excluded from the public equity-only allocation. '
                            'Workbook NAV, market-price and performance history remain illustrative and retain their own dates.')


def apply_proxy(snapshot, path):
    source=json.loads(path.read_text()); snapshot=deepcopy(snapshot)
    allowed={'schema_version','as_of','source_fund','source_url','source_sha256','issuer_net_assets','holdings','methodology','nav_source_url','nav_source_sha256'}
    holding_fields={'identifier','ticker','name','sector','quantity','issuer_weight','security_type'}
    if set(source)!=allowed or any(set(h)!=holding_fields for h in source['holdings']):
        raise ValueError('Unexpected fields at the public data boundary')
    if source.get('source_fund')!='SPY' or source.get('schema_version')!=1:
        raise ValueError('Unsupported public proxy')
    date.fromisoformat(source['as_of'])
    for key in ('source_url','nav_source_url'):
        url=urlsplit(source[key])
        if url.scheme!='https' or url.netloc!='www.ssga.com':
            raise ValueError('Expected an official issuer source URL')
    f=next(f for f in snapshot['funds'] if f['fund_id']=='redi')
    equities=[h for h in source['holdings'] if h['security_type']=='equity']
    if not 490<=len(equities)<=520 or len({h['identifier'] for h in equities})!=len(equities):
        raise ValueError('Incomplete or duplicate public SPY constituents')
    total=sum(D(h['issuer_weight']) for h in equities)
    if not D('.95')<total<D('1.05'): raise ValueError('Implausible issuer equity weight total')
    assets=D(str(f['daily'][-1]['net_assets'])); cash_weight=D(str(f['cash_weight']))
    holdings=[]
    for h in equities:
        weight=D(h['issuer_weight'])/total*(1-cash_weight)
        price=D(h['issuer_weight'])*D(source['issuer_net_assets'])/D(h['quantity'])
        if price<=0 or weight<=0: raise ValueError('Invalid inferred public proxy price/weight')
        mv=assets*weight
        holdings.append(dict(fund_id='redi',date=source['as_of'],ticker=h['ticker'],identifier=h['identifier'],name=h['name'],
                             sector=h['sector'],country='Not supplied',currency='USD',security_type='equity',quantity=float(mv/price),
                             price=float(price),fx_rate=1,market_value=float(mv),weight=float(weight)))
    cash=assets*cash_weight
    holdings.append(dict(fund_id='redi',date=source['as_of'],ticker='CASH',identifier='USD',name='US Dollar',sector='Cash',country='US',
                         currency='USD',security_type='cash',quantity=float(cash),price=1,fx_rate=1,market_value=float(cash),weight=float(cash_weight)))
    f['holdings']=sorted(holdings,key=lambda h:-h['market_value'])
    f['holdings_as_of']=source['as_of']; f['holdings_source']=source
    snapshot['holdings_overlay_sha256']=sha256(path.read_bytes()).hexdigest()
    return snapshot
