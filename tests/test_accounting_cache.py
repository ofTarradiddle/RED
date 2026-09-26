from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from lib.etf.daily_accruals import daily_replay
from lib.etf.operating_book import encode
from scripts.accounting_cache import export,restore,verify,PRIVATE_INPUTS
from tests.test_ledger_replay import opening,prices


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(encode(value))


@pytest.fixture
def books(tmp_path):
    output=tmp_path/'source';cache=tmp_path/'cache';seed=tmp_path/'seed.json'
    inp=dict(fund_id='REDI',source_fund='SPY',opening=opening(),events=[],
             price_history={'2026-09-15':prices('2026-09-15',100)},policy={})
    day=json.loads(encode(daily_replay(inp['opening'],[], '2026-09-15',inp['price_history'])))
    day.update(mode='Prospective holdings model',model_complete=True,status='Daily accruals calculated',
               input_sha256=sha256(encode(inp).encode()).hexdigest())
    dividends=dict(as_of='2026-09-15',input_evidence=dict(supplied_inputs_sha256=None,blotter_sha256=None),
                   modeled_book=dict(lots=[],journal=[]))
    write(seed,inp);write(output/'daily-book/public-model-inputs.json',inp)
    write(output/'daily-book/latest.json',day);write(output/'dividend-book/latest.json',dividends)
    write(output/'dividend-book/public-entitlements.json',[])
    return output,cache,seed,inp,day,dividends


def test_roundtrip_restores_journal_balances_inputs_and_replay_without_duplicates(books,tmp_path):
    source,cache,seed,inp,day,_=books
    result=export(source,cache,seed);assert result['successful'] and result['ready']
    target=tmp_path/'restored';restored=restore(target,cache,seed)
    assert restored['restored'] and restored['last_successful']=='2026-09-15'
    recovered=json.loads((target/'daily-book/latest.json').read_text())
    assert recovered['daily']==day['daily'] and recovered['state']['journal']==day['state']['journal']
    saved=json.loads((target/'daily-book/public-model-inputs.json').read_text())
    replayed=json.loads(encode(daily_replay(saved['opening'],saved['events'],'2026-09-15',saved['price_history'])))
    assert replayed['daily']==day['daily']
    assert saved['events']==[]  # generated fees/payments are never re-appended
    export(source,cache,seed)
    assert len(list((cache/'runs').iterdir()))==1


def test_incomplete_attempt_keeps_last_successful_book_and_sources(books,tmp_path):
    source,cache,seed,inp,day,_=books;export(source,cache,seed)
    failed=dict(mode='Prospective holdings model',as_of='2026-09-16',status='Daily book needs source data',
                daily=[],error='Missing closing prices')
    write(source/'daily-book/latest.json',failed)
    result=export(source,cache,seed)
    assert not result['successful'] and result['last_successful']=='2026-09-15'
    assert json.loads((cache/'daily/latest-successful.json').read_text())==day
    assert json.loads((cache/'daily/latest.json').read_text())==failed
    target=tmp_path/'restored';restore(target,cache,seed)
    assert json.loads((target/'daily-book/latest.json').read_text())['last_complete_day']==day['daily'][-1]


@pytest.mark.parametrize('name',PRIVATE_INPUTS)
def test_actual_input_files_block_export_and_restore_without_mutating_cache(books,tmp_path,name):
    source,cache,seed,*_=books;export(source,cache,seed)
    manifest=(cache/'manifest.json').read_bytes();write(source/name,{'confidential':'actual-account'})
    with pytest.raises(ValueError,match='supplied accounting inputs'):export(source,cache,seed)
    assert (cache/'manifest.json').read_bytes()==manifest
    with pytest.raises(ValueError,match='supplied accounting inputs'):restore(source,cache,seed)
    assert b'actual-account' not in b''.join(p.read_bytes() for p in cache.rglob('*') if p.is_file())


def test_private_derived_records_reject_even_without_original_input_files(books):
    source,cache,seed,inp,day,dividends=books
    day['mode']='Supplied operating records';write(source/'daily-book/latest.json',day)
    with pytest.raises(ValueError,match='Supplied operating book'):export(source,cache,seed)
    day['mode']='Prospective holdings model';write(source/'daily-book/latest.json',day)
    dividends['input_evidence']['blotter_sha256']='private-source-hash';write(source/'dividend-book/latest.json',dividends)
    with pytest.raises(ValueError,match='Supplied dividend inputs'):export(source,cache,seed)


def test_actual_opening_or_execution_cannot_masquerade_as_public_model(books):
    source,cache,seed,inp,*_=books
    changed=deepcopy(inp);changed['opening']['balances']['cash']=2000
    write(source/'daily-book/public-model-inputs.json',changed)
    with pytest.raises(ValueError,match='public model opening'):export(source,cache,seed)
    changed=deepcopy(inp);changed['events']=[dict(type='trade')];write(source/'daily-book/public-model-inputs.json',changed)
    with pytest.raises(ValueError,match='Supplied trades'):export(source,cache,seed)


def test_corrupt_or_unlisted_cache_rejected_before_writing_destination(books,tmp_path):
    source,cache,seed,*_=books;export(source,cache,seed)
    (cache/'daily/latest.json').write_text('{}')
    target=tmp_path/'restored'
    with pytest.raises(ValueError,match='path/hash'):restore(target,cache,seed)
    assert not (target/'daily-book').exists()


def test_unlisted_file_and_symlink_reject(books,tmp_path):
    source,cache,seed,*_=books;export(source,cache,seed)
    (cache/'surprise.json').write_text('{}')
    with pytest.raises(ValueError,match='inventory'):verify(cache)
    (cache/'surprise.json').unlink();(cache/'link').symlink_to(seed)
    with pytest.raises(ValueError,match='Symlinks'):verify(cache)


def test_bounded_revisions_retain_cumulative_book_and_original_opening(books):
    source,cache,seed,inp,day,_=books
    for revision in range(4):
        day['revision_note']=revision;write(source/'daily-book/latest.json',day)
        export(source,cache,seed,keep_runs=2)
    assert len(list((cache/'runs').iterdir()))==2
    assert json.loads((cache/'inputs/daily.json').read_text())['opening']==inp['opening']
    assert json.loads((cache/'daily/latest.json').read_text())['daily']==day['daily']
    assert verify(cache)['last_successful_as_of']=='2026-09-15'


def test_stale_attempt_does_not_replace_newer_cache(books):
    source,cache,seed,inp,day,_=books
    export(source,cache,seed);day['as_of']='2026-09-14';write(source/'daily-book/latest.json',day)
    with pytest.raises(ValueError,match='newer accounting cache'):export(source,cache,seed)


def test_no_cache_is_explicit_cold_start_and_does_not_create_zero_balances(tmp_path):
    target=tmp_path/'fresh';result=restore(target,tmp_path/'absent',tmp_path/'absent-seed')
    assert not result['restored'] and not target.exists()


def test_current_supplied_book_is_not_overwritten_after_input_was_moved(books,tmp_path):
    source,cache,seed,*_=books;export(source,cache,seed)
    target=tmp_path/'actual';write(target/'daily-book/latest.json',dict(mode='Supplied operating records'))
    with pytest.raises(ValueError,match='overwrite a supplied'):restore(target,cache,seed)


@pytest.mark.parametrize('evidence', ['supplied_inputs_sha256', 'blotter_sha256', 'receipt'])
def test_current_supplied_dividend_book_survives_after_input_was_moved(books,tmp_path,evidence):
    source,cache,seed,_,_,dividends=books;export(source,cache,seed)
    target=tmp_path/'actual'
    if evidence=='receipt':
        dividends['modeled_book']['journal']=[dict(type='confirmed_payment',amount='50.00')]
    else:dividends['input_evidence'][evidence]='actual-record-hash'
    path=target/'dividend-book/latest.json';write(path,dividends)
    write(target/'dividend-book/entitlements.json',[])
    before=path.read_bytes()
    with pytest.raises(ValueError,match='Supplied dividend inputs|Confirmed operating receipts'):
        restore(target,cache,seed)
    assert path.read_bytes()==before
    assert not (target/'daily-book').exists()


def test_older_cache_does_not_overwrite_newer_local_public_book(books,tmp_path):
    source,cache,seed,_,day,_=books;export(source,cache,seed)
    target=tmp_path/'newer';day['as_of']='2026-09-16'
    path=target/'daily-book/latest.json';write(path,day);before=path.read_bytes()
    with pytest.raises(ValueError,match='newer local operating book'):restore(target,cache,seed)
    assert path.read_bytes()==before
