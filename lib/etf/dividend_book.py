"""Integrate independently calculated dividend receivables into a local report."""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

from .dividend_receivables import build, load_snapshots, entitlements_from_blotter
from .dividend_sources import fetch_histories

ROOT=Path(__file__).resolve().parents[2]


def update(report,output,fetch=True,progress=print):
    output=Path(output);folder=output/'dividend-book';folder.mkdir(parents=True,exist_ok=True)
    seed=ROOT/'data/spy_seed'
    primary_path=seed/'dividend-confirmations.json';snapshot_path=seed/'dividend-snapshots.json'
    primary=json.loads(primary_path.read_text())['records'] if primary_path.exists() else []
    for record in primary:
        resolution=record.get('ex_date_resolution')
        if not resolution:continue
        for item in resolution['evidence']:
            raw=(seed/item['file']).read_bytes()
            if sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Exchange ex-date evidence hash mismatch')
            if item['file'].endswith('exchange-exceptions.json'):
                payload=json.loads(raw)
                if payload.get('next') or payload['count']!=len(payload['results']):raise ValueError('Incomplete exchange exception report')
                if any(r['issue_symbol']==record['symbol'] and not r.get('is_cancelled') for r in payload['results']):raise ValueError('Exchange-specific ex-date exception requires review')
    extra=json.loads(snapshot_path.read_text()) if snapshot_path.exists() else []
    for snapshot in extra:
        raw=(seed/snapshot['evidence_file']).read_bytes()
        if sha256(raw).hexdigest()!=snapshot['sha256']:raise ValueError('Historical entitlement snapshot evidence changed')
    frozen_path=folder/'entitlements.json'
    public_frozen=folder/'public-entitlements.json'
    prior=json.loads(frozen_path.read_text()) if frozen_path.exists() else json.loads(public_frozen.read_text()) if public_frozen.exists() else []
    input_path=output/'dividend-inputs.json';inputs=json.loads(input_path.read_text()) if input_path.exists() else {}
    accounting_path=output/'accounting-input.json'
    if accounting_path.exists():
        accounting=json.loads(accounting_path.read_text())
        if accounting.get('fund_id')!=report.get('source_fund','SPY'):
            raise ValueError('To use the accounting blotter in SPY entitlement calculations, set its top-level fund_id to SPY; do not mix another portfolio with this comparison')
        derived=entitlements_from_blotter(accounting,report.get('dividend_calendar',[]),report['positions'])
        explicit={r['id']:r for r in inputs.get('entitlements',[])}
        if len(explicit)!=len(inputs.get('entitlements',[])):raise ValueError('Duplicate supplied entitlement')
        for item in derived:
            if item['id'] in explicit and Decimal(explicit[item['id']]['eligible_quantity'])!=Decimal(item['eligible_quantity']):
                raise ValueError('Blotter-derived and explicitly supplied dividend entitlements conflict')
            explicit.setdefault(item['id'],item)
        inputs['entitlements']=list(explicit.values())
    if 'frozen_entitlements' in inputs:raise ValueError('Frozen model quantities are managed by the engine; supply documented entitlements to correct them')
    inputs['frozen_entitlements']=prior
    symbols={p['yahoo_symbol'] for p in report['positions'] if p['security_type']=='equity'}|{p['symbol'] for p in prior}
    from .operating_book import retained_symbols
    symbols |= retained_symbols(output)
    history_path=output/'dividend-actions/latest.json'
    histories=fetch_histories(symbols,history_path.parent,report['as_of'],progress) if fetch else json.loads(history_path.read_text())
    if histories['as_of']!=report['as_of']:raise ValueError('Action-history report date differs from valuation date')
    result=build(report,histories['securities'],load_snapshots(output,extra),primary,inputs)
    result['fetched_at']=histories['fetched_at']
    result['input_evidence']=dict(action_history_sha256=sha256(history_path.read_bytes()).hexdigest(),
        primary_declarations_sha256=sha256(primary_path.read_bytes()).hexdigest() if primary_path.exists() else None,
        snapshot_index_sha256=sha256(snapshot_path.read_bytes()).hexdigest() if snapshot_path.exists() else None,
        supplied_inputs_sha256=sha256(input_path.read_bytes()).hexdigest() if input_path.exists() else None)
    result['input_evidence']['blotter_sha256']=sha256(accounting_path.read_bytes()).hexdigest() if accounting_path.exists() else None
    result['engine_sha256']=sha256((Path(__file__).with_name('dividend_receivables.py')).read_bytes()).hexdigest()
    if report.get('reconciliation'):
        # Show an independent asset subtotal, never add receivables on top of
        # issuer aggregate net cash and never plug the other-balances residual.
        D=Decimal;v=report['reconciliation'];physical_cash=D(report['legacy_holdings_cash_diagnostic']['reported_cash'])
        modeled=D(result['expected_gross_receivable']);securities=D(v['priced_equities'])+D(v['priced_rights'])
        subtotal=securities+physical_cash+modeled
        result['component_check']=dict(securities=str(securities),holdings_cash=str(physical_cash),
            calculated_gross_receivable_subtotal=str(modeled),assets_before_other_balances=str(subtotal),
            other_net_balances_needed_to_reconcile=str(D(report['official']['net_assets'])-subtotal),
            official_net_assets=report['official']['net_assets'],
            note='Not a completed NAV: gross receivable estimates, unknown withholding, trade balances and liabilities remain. The displayed difference is diagnostic and is never booked.')
    stamp=datetime.now(timezone.utc).isoformat().replace(':','').replace('+','_')
    run=folder/'runs'/stamp;run.mkdir(parents=True)
    text=json.dumps(result,indent=2,allow_nan=False);(run/'report.json').write_text(text)
    (run/'engine.py').write_bytes(Path(__file__).with_name('dividend_receivables.py').read_bytes())
    (run/'inputs.json').write_text(json.dumps(inputs,indent=2))
    for path,value in [(folder/'latest.json',result),(frozen_path,result['entitlement_archive']),
                       (public_frozen,[r for r in result['entitlement_archive'] if r['quantity_method']!='documented_entitlement' and r['withholding_assumed']])]:
        temp=path.with_suffix('.next.json');temp.write_text(json.dumps(value,indent=2,allow_nan=False));temp.replace(path)
    report['dividend_receivables']=result
    progress(f"Independent dividend model: {result['calculated_outstanding_count']}/{result['outstanding_event_count']} outstanding events; {result['outstanding_source_dated_count']} source-dated quantities",flush=True)
    return result
