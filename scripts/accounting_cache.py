"""Persist public-source shadow books across ephemeral GitHub Actions runners.

The cache contains modeled accounting, never supplied operating records. Reports
stay outside Pages. Successful checkpoints advance only after a complete replay;
failed attempts retain their diagnostics alongside the last successful book.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from lib.etf.operating_book import encode

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_INPUTS = ('accounting-input.json', 'daily-accounting-input.json', 'dividend-inputs.json')
FILES = {
    'inputs/daily.json': 'daily-book/public-model-inputs.json',
    'inputs/entitlements.json': 'dividend-book/public-entitlements.json',
    'daily/latest.json': 'daily-book/latest.json',
    'dividends/latest.json': 'dividend-book/latest.json',
}
SCOPE = 'public_source_model_only'


def read(path):
    return json.loads(path.read_text())


def assert_public_workspace(output):
    present = [name for name in PRIVATE_INPUTS if (output/name).exists()]
    if present:
        raise ValueError('Public-repository cache refuses supplied accounting inputs: '+', '.join(present))


def validate_books(inputs, daily, dividends, entitlements, seed):
    if inputs.get('fund_id') != 'REDI' or inputs.get('source_fund') != 'SPY' or inputs['opening'] != seed['opening']:
        raise ValueError('Cache permits only the committed public model opening')
    if any(e.get('type') not in ('dividend', 'split') for e in inputs['events']):
        raise ValueError('Supplied trades, receipts or other operating events cannot enter the public cache')
    if daily.get('mode') != 'Prospective holdings model':
        raise ValueError('Supplied operating book cannot enter the public cache')
    digest = sha256(encode(inputs).encode()).hexdigest()
    if daily.get('input_sha256') and daily['input_sha256'] != digest:
        raise ValueError('Daily report and saved model inputs differ')
    validate_dividends(dividends, entitlements)
    return digest


def validate_dividends(dividends, entitlements=()):
    evidence = dividends.get('input_evidence', {})
    if 'supplied_inputs_sha256' not in evidence or 'blotter_sha256' not in evidence:
        raise ValueError('Missing dividend input provenance')
    if evidence['supplied_inputs_sha256'] or evidence['blotter_sha256']:
        raise ValueError('Supplied dividend inputs cannot enter the public cache')
    lots = dividends.get('modeled_book', {}).get('lots', [])
    for row in list(lots) + list(entitlements):
        if row.get('quantity_method') == 'documented_entitlement' or row.get('withholding_assumed') is not True:
            raise ValueError('Documented entitlement or supplied tax record cannot enter the public cache')
    if any(e['type'] == 'confirmed_payment' for e in dividends.get('modeled_book', {}).get('journal', [])):
        raise ValueError('Confirmed operating receipts cannot enter the public cache')


def allowed(name):
    parts = PurePosixPath(name).parts
    if not parts or PurePosixPath(name).is_absolute() or '..' in parts or '\\' in name:
        return False
    if name in FILES or name == 'daily/latest-successful.json':return True
    if len(parts) == 3 and parts[0] == 'runs' and parts[2] in ('report.json', 'inputs.json', 'dividends.json', 'metadata.json'):
        return True
    return len(parts) == 3 and parts[0] == 'engines' and parts[2] in ('daily_accruals.py', 'ledger.py', 'operating_book.py', 'dividend_receivables.py')


def verify(cache):
    manifest = read(cache/'manifest.json')
    if manifest.get('schema_version') != 1 or manifest.get('scope') != SCOPE:
        raise ValueError('Unsupported accounting cache format/scope')
    actual = set()
    for path in cache.rglob('*'):
        if path.is_symlink():raise ValueError('Symlinks are not permitted in accounting cache')
        if path.is_file() and path != cache/'manifest.json':actual.add(path.relative_to(cache).as_posix())
    if actual != set(manifest['files']):raise ValueError('Accounting cache file inventory mismatch')
    for name,digest in manifest['files'].items():
        if not allowed(name) or sha256((cache/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Accounting cache path/hash validation failed: '+name)
    if not set(FILES).issubset(actual):raise ValueError('Accounting cache is missing replay inputs/reports')
    return manifest


def restore(output, cache, seed_path):
    output, cache = Path(output), Path(cache)
    assert_public_workspace(output)
    if not (cache/'manifest.json').exists():
        if cache.exists() and any(cache.iterdir()):raise ValueError('Accounting cache has no manifest')
        return dict(restored=False, reason='No prior cache or backup; committed public opening will be used')
    manifest = verify(cache)
    validate_books(read(cache/'inputs/daily.json'),read(cache/'daily/latest.json'),
                   read(cache/'dividends/latest.json'),read(cache/'inputs/entitlements.json'),read(seed_path))
    # Validate everything before touching working books. Refuse to overwrite a
    # pre-existing actual book even if its supplied input has since been moved.
    current=output/'daily-book/latest.json'
    if current.exists():
        existing=read(current)
        if existing.get('mode') != 'Prospective holdings model':
            raise ValueError('Restoring public cache would overwrite a supplied operating book')
        if existing.get('as_of', '') > manifest['latest_attempt_as_of']:
            raise ValueError('Restoring older cache would overwrite a newer local operating book')
    dividend_current=output/'dividend-book/latest.json'
    if dividend_current.exists():validate_dividends(read(dividend_current))
    frozen=output/'dividend-book/entitlements.json'
    if frozen.exists() and any(r.get('quantity_method')=='documented_entitlement' or r.get('withholding_assumed') is not True for r in read(frozen)):
        raise ValueError('Restoring public cache would mix with supplied dividend entitlements')
    for name,target in FILES.items():
        path=output/target;path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.next.json');temporary.write_bytes((cache/name).read_bytes());temporary.replace(path)
    last=cache/'daily/latest-successful.json'
    if last.exists():
        shutil.copyfile(last,output/'daily-book/latest-successful.json')
        latest=read(current)
        if not latest.get('daily') and read(last).get('daily'):
            latest['last_complete_day']=read(last)['daily'][-1]
            current.write_text(encode(latest))
    # Replace a pre-existing public frozen archive as well; otherwise it takes
    # precedence over the just-restored public archive in dividend_book.update.
    if frozen.exists():shutil.copyfile(cache/'inputs/entitlements.json',frozen)
    # Do not restore generic entitlements.json; the engine deliberately falls
    # back to the public entitlement archive when no local private archive exists.
    return dict(restored=True, as_of=manifest['latest_attempt_as_of'], last_successful=manifest.get('last_successful_as_of'))


def export(output, cache, seed_path, keep_runs=30):
    output,cache=Path(output),Path(cache)
    assert_public_workspace(output)
    if keep_runs < 1:raise ValueError('Retain at least one accounting run')
    if not all((output/name).exists() for name in FILES.values()):
        if (cache/'manifest.json').exists():
            verify(cache)
            return dict(ready=True, updated=False, reason='Refresh produced no new full input set; prior cache retained')
        return dict(ready=False, updated=False, reason='No calculated model available yet')
    inputs=read(output/FILES['inputs/daily.json']);daily=read(output/FILES['daily/latest.json'])
    dividends=read(output/FILES['dividends/latest.json']);entitlements=read(output/FILES['inputs/entitlements.json'])
    digest=validate_books(inputs,daily,dividends,entitlements,read(seed_path))
    successful=bool(daily.get('model_complete') is True and daily.get('daily') and not daily.get('error'))
    previous=verify(cache) if (cache/'manifest.json').exists() else None
    if previous and daily['as_of'] < previous['latest_attempt_as_of']:
        raise ValueError('Refusing to replace a newer accounting cache with older source data')
    cache.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='accounting-stage-',dir=cache.parent))
    try:
        if previous:
            shutil.copytree(cache,stage,dirs_exist_ok=True)
            (stage/'manifest.json').unlink()
        for name,target in FILES.items():
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((output/target).read_bytes())
        run_digest=sha256(encode(dict(inputs=inputs,daily=daily,dividends=dividends)).encode()).hexdigest()
        run_name=daily['as_of']+'-'+run_digest[:16];run=stage/'runs'/run_name;run.mkdir(parents=True,exist_ok=True)
        for name,value in [('report.json',daily),('inputs.json',inputs),('dividends.json',dividends)]:
            (run/name).write_text(encode(value))
        engines={name:(ROOT/'lib/etf'/name).read_bytes() for name in ('daily_accruals.py','ledger.py','operating_book.py','dividend_receivables.py')}
        engine_id=sha256(b''.join(engines.values())).hexdigest()[:16]
        engine_dir=stage/'engines'/engine_id;engine_dir.mkdir(parents=True,exist_ok=True)
        for name,raw in engines.items():(engine_dir/name).write_bytes(raw)
        (run/'metadata.json').write_text(encode(dict(engine_id=engine_id,input_sha256=digest,successful=successful)))
        last_successful=previous.get('last_successful_as_of') if previous else None
        if successful:
            (stage/'daily/latest-successful.json').write_text(encode(daily));last_successful=daily['as_of']
        # Current reports include the entire cumulative daily history and journal.
        # Retain bounded revision snapshots as well, without growing indefinitely.
        revisions=sorted((stage/'runs').iterdir(),key=lambda p:p.stat().st_mtime_ns)
        for old in revisions[:-keep_runs]:shutil.rmtree(old)
        needed={read(p/'metadata.json')['engine_id'] for p in (stage/'runs').iterdir()}
        for old in (stage/'engines').iterdir():
            if old.name not in needed:shutil.rmtree(old)
        manifest=dict(schema_version=1,scope=SCOPE,created_at=datetime.now(timezone.utc).isoformat(),
            latest_attempt_as_of=daily['as_of'],last_successful_as_of=last_successful,
            latest_run=run_name,input_sha256=digest,engine_id=engine_id,
            files={p.relative_to(stage).as_posix():sha256(p.read_bytes()).hexdigest() for p in sorted(stage.rglob('*')) if p.is_file()})
        (stage/'manifest.json').write_text(encode(manifest));verify(stage)
        backup=cache.with_name(cache.name+'.previous')
        if backup.exists():shutil.rmtree(backup)
        if cache.exists():cache.rename(backup)
        try:stage.rename(cache)
        except BaseException:
            if backup.exists():backup.rename(cache)
            raise
        if backup.exists():shutil.rmtree(backup)
        return dict(ready=True,updated=True,successful=successful,as_of=daily['as_of'],last_successful=last_successful)
    finally:
        if stage.exists():shutil.rmtree(stage)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('restore','export','verify'))
    parser.add_argument('--data-dir',type=Path,default=ROOT/'data/shadow_spy')
    parser.add_argument('--cache-dir',type=Path)
    parser.add_argument('--keep-runs',type=int,default=30)
    args=parser.parse_args();cache=args.cache_dir or args.data_dir/'accounting-cache'
    seed=ROOT/'data/spy_seed/daily-model-inputs.json'
    if args.command=='restore':result=restore(args.data_dir,cache,seed)
    elif args.command=='export':result=export(args.data_dir,cache,seed,args.keep_runs)
    else:result=verify(cache)
    print(json.dumps(result,indent=2))
    if os.environ.get('GITHUB_OUTPUT') and 'ready' in result:
        with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('ready='+str(result['ready']).lower()+'\n')


if __name__=='__main__':main()
