"""Source-faithful quote cleanup; no network or inferred monetary units."""
import gzip
import hashlib
from copy import deepcopy

from scripts import annual_excerpt


def filing_fixture(tmp_path, text, *, excerpt='technology. Total research and development expense was $1.8'):
    raw = ('<html><head><meta charset="utf-8"></head><body><p>' + text + '</p></body></html>').encode()
    accession = '0001193125-10-238044'
    path = tmp_path / '320193' / 'raw' / (accession + '.html.gz')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(raw))
    return {
        'url': 'https://www.sec.gov/Archives/edgar/data/320193/000119312510238044/d10k.htm',
        'accession': accession,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'form': '10-K',
        'filed': '2010-10-27',
        'status': 'ok',
        'focusAreas': ['Mobile devices'],
        'focusNote': 'Topic pointers, not allocated budgets.',
        'investmentThemes': [{'label': 'Research & development', 'excerpt': excerpt, 'note': 'Original note'}],
    }


def test_restores_actual_adjacent_billion_and_preserves_source_metadata(tmp_path):
    filing = filing_fixture(tmp_path, 'The company develops technology. Total research and development expense was $1.8 billion during the year.')
    original = deepcopy(filing)
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'][0]['excerpt'] == 'research and development expense was $1.8 billion'
    assert 'automated' in result['investmentThemes'][0]['note']
    assert filing == original
    assert {key: value for key, value in result.items() if key != 'investmentThemes'} == {key: value for key, value in original.items() if key != 'investmentThemes'}


def test_already_complete_quote_does_not_require_local_raw(tmp_path):
    filing = {'investmentThemes': [{'label': 'Research & development', 'excerpt': 'research and development expense was $1.8 billion'}], 'focusAreas': ['Research'], 'url': 'https://www.sec.gov/example'}
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'][0]['excerpt'] == 'research and development expense was $1.8 billion'
    assert result['focusAreas'] == ['Research']


def test_missing_raw_drops_incomplete_amount_without_guessing_unit(tmp_path):
    filing = {
        'url': 'https://www.sec.gov/Archives/edgar/data/999/000000099910000001/report.htm',
        'accession': '0000000999-10-000001',
        'investmentThemes': [
            {'label': 'Research & development', 'excerpt': 'research and development expense was $1.8'},
            {'label': 'Products & expansion', 'excerpt': 'new products support our business'},
        ],
    }
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert [item['excerpt'] for item in result['investmentThemes']] == ['new products support our business']


def test_missing_raw_drops_unscaled_integer_amount_but_retains_year(tmp_path):
    filing = {'investmentThemes': [
        {'label': 'Capital investment', 'excerpt': 'capital expenditures were 1800'},
        {'label': 'Products & expansion', 'excerpt': 'new products launched in 2010'},
    ]}
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert [item['excerpt'] for item in result['investmentThemes']] == ['new products launched in 2010']


def test_no_units_are_borrowed_from_different_amounts(tmp_path):
    filing = filing_fixture(tmp_path, 'Total research and development expense was $18 billion during the year.')
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'] == []


def test_conflicting_adjacent_units_drop_ambiguous_clipped_quote(tmp_path):
    filing = filing_fixture(tmp_path, 'Total research and development expense was $1.8 million in one period. Total research and development expense was $1.8 billion in another period.')
    assert annual_excerpt.clean_filing_excerpts(filing, tmp_path)['investmentThemes'] == []
    # Cached ambiguity must remain omitted, while a complete source quotation
    # is still usable and has a distinct excerpt-cache key.
    assert annual_excerpt.clean_filing_excerpts(filing, tmp_path)['investmentThemes'] == []
    filing['investmentThemes'][0]['excerpt'] = 'research and development expense was $1.8 billion'
    assert annual_excerpt.clean_filing_excerpts(filing, tmp_path)['investmentThemes'][0]['excerpt'].endswith('$1.8 billion')


def test_repeated_same_unit_is_unambiguous_regardless_of_capitalization(tmp_path):
    filing = filing_fixture(tmp_path, 'Total research and development expense was $1.8 billion in one period. Total research and development expense was $1.8 BILLION in another period.')
    assert annual_excerpt.clean_filing_excerpts(filing, tmp_path)['investmentThemes'][0]['excerpt'] == 'research and development expense was $1.8 billion'


def test_total_budget_and_no_budget_cut_leaving_dangling_amount(tmp_path):
    first = ' '.join(['source'] * 19)
    filing = filing_fixture(tmp_path, 'Research and development expense was $1.8 billion during the year.', excerpt='Research and development expense was $1.8')
    filing['investmentThemes'].insert(0, {'label': 'Unclassified source', 'excerpt': first})
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert sum(len(item['excerpt'].split()) for item in result['investmentThemes']) <= 25
    assert all(not item['excerpt'].endswith('$1.8') for item in result['investmentThemes'])
    # With only six words left, the second seven-word repaired quote is omitted.
    assert len(result['investmentThemes']) == 1


def test_negation_before_topic_is_retained(tmp_path):
    filing = filing_fixture(tmp_path, 'We do not make capital investments in new plants.', excerpt='not make capital investments in new plants')
    filing['investmentThemes'][0]['label'] = 'Capital investment'
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'][0]['excerpt'].startswith('not make capital investments')


def test_report_hash_mismatch_does_not_justify_extension(tmp_path):
    filing = filing_fixture(tmp_path, 'Total research and development expense was $1.8 billion.')
    filing['sha256'] = '0' * 64
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'] == []


def test_reuses_verified_report_hash_without_reparsing(tmp_path, monkeypatch):
    from lxml import etree
    annual_excerpt._TEXT_CACHE.clear()
    annual_excerpt._CLEAN_CACHE.clear()
    filing = filing_fixture(tmp_path, 'Total research and development expense was $1.8 billion during the year.')
    original = etree.fromstring
    calls = []

    def tracked(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(etree, 'fromstring', tracked)
    for _ in range(3):
        assert annual_excerpt.clean_filing_excerpts(filing, tmp_path)['investmentThemes'][0]['excerpt'].endswith('$1.8 billion')
    assert len(calls) == 1


def test_cached_cleanup_keeps_current_filing_metadata_and_extra_theme_fields(tmp_path):
    filing = filing_fixture(tmp_path, 'Total research and development expense was $1.8 billion.')
    annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    filing['focusAreas'] = ['Updated source label']
    filing['investmentThemes'][0]['context'] = 'Current source metadata'
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['focusAreas'] == ['Updated source label']
    assert result['investmentThemes'][0]['context'] == 'Current source metadata'
    assert result['investmentThemes'][0]['excerpt'].endswith('$1.8 billion')


def test_old_windows_punctuation_is_normalized_before_verification(tmp_path):
    filing = filing_fixture(tmp_path, 'The Company’s capital expenditures were $2.6 billion during the year.', excerpt='The Company\x92s capital expenditures were $2.6')
    filing['investmentThemes'][0]['label'] = 'Capital investment'
    result = annual_excerpt.clean_filing_excerpts(filing, tmp_path)
    assert result['investmentThemes'][0]['excerpt'] == 'capital expenditures were $2.6 billion'
