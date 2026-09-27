"""Exact source preservation and comparison-research publication safeguards."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.import_comparison_research import (
    COUNT, END, EXPECTED_SHA256, OUTPUT_PATH, REFERENCE_SERIES_ID, SERIES,
    SOURCE_PATH, START, build_payload, expected_dates, read_source, validate_payload,
    validate_rows,
)


class ComparisonResearchImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.digest = read_source()
        cls.payload = build_payload(cls.rows, cls.digest)

    def test_original_tsv_is_pinned_byte_for_byte(self):
        self.assertEqual(hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(), EXPECTED_SHA256)
        self.assertEqual(self.digest, EXPECTED_SHA256)
        self.assertEqual(SOURCE_PATH.read_bytes().splitlines()[0].split(b'\t')[-1], b'')
        self.assertEqual(len(self.rows), 289)

    def test_all_nine_paths_match_every_source_observation(self):
        self.assertEqual(len(self.payload['series']), 9)
        for series, (_, name, column) in zip(self.payload['series'], SERIES):
            self.assertEqual(series['name'], name)
            self.assertEqual(series['source_column'], column)
            self.assertEqual(series['observations'], [
                {'date': row['date'], 'level': row[column]} for row in self.rows
            ])
        self.assertEqual(validate_payload(self.payload), self.payload)

    def test_committed_payload_reproduces_exactly_without_private_attachment(self):
        self.assertEqual(json.loads(OUTPUT_PATH.read_text()), self.payload)

    def test_months_are_complete_and_include_actual_leap_day(self):
        dates = expected_dates()
        self.assertEqual((dates[0], dates[-1], len(dates)), (START, END, COUNT))
        self.assertIn('2004-02-29', dates)
        self.assertIn('2024-02-29', dates)
        self.assertEqual([row['date'] for row in self.rows], dates)

    def test_predicted_innovation_reference_keeps_point_99_baseline(self):
        self.assertEqual(self.payload['reference_series_id'], REFERENCE_SERIES_ID)
        p = next(s for s in self.payload['series'] if s['id'] == REFERENCE_SERIES_ID)
        self.assertEqual(p['observations'][0], {'date': START, 'level': .99})
        self.assertEqual(p['observations'][-1], {'date': END, 'level': 65.75})
        self.assertAlmostEqual(p['observations'][-1]['level'] / p['observations'][0]['level'], 66.41414141414141)
        self.assertEqual(sum(b['level'] < a['level'] for a, b in zip(p['observations'], p['observations'][1:])), 104)

    def test_source_file_byte_change_is_rejected(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'changed.tsv'
            path.write_bytes(SOURCE_PATH.read_bytes().replace(b'65.75', b'65.76'))
            with self.assertRaisesRegex(ValueError, 'Source SHA-256'):
                read_source(path)

    def test_interior_observation_change_is_rejected_even_with_valid_source_hash(self):
        forged = deepcopy(self.payload)
        forged['series'][5]['observations'][143]['level'] += .01
        forged['series'][5]['observations'][143]['level'] = round(forged['series'][5]['observations'][143]['level'], 2)
        with self.assertRaisesRegex(ValueError, 'observation SHA-256'):
            validate_payload(forged)

    def test_invalid_or_excess_precision_levels_are_rejected(self):
        for value in (0, -1, True, None, '1.00', float('inf'), float('nan'), 1.001, 1.00000000001):
            with self.subTest(value=value):
                forged = deepcopy(self.payload)
                forged['series'][0]['observations'][40]['level'] = value
                with self.assertRaises(ValueError):
                    validate_payload(forged)

    def test_non_month_end_duplicate_and_missing_dates_are_rejected(self):
        for replacement in ('2004-02-28', '2004-03-31', '2024-02-29T00:00:00Z'):
            with self.subTest(replacement=replacement):
                forged = deepcopy(self.payload)
                index = expected_dates().index('2004-02-29')
                forged['series'][0]['observations'][index]['date'] = replacement
                with self.assertRaises(ValueError):
                    validate_payload(forged)
        forged = deepcopy(self.payload)
        forged['series'][0]['observations'].pop(50)
        with self.assertRaises(ValueError):
            validate_payload(forged)

    def test_missing_unknown_and_duplicate_series_are_rejected(self):
        changes = [lambda p: p['series'].pop(),
                   lambda p: p['series'][0].update(id='SPY'),
                   lambda p: p['series'][0].update(id=p['series'][1]['id'])]
        for change in changes:
            forged = deepcopy(self.payload)
            change(forged)
            with self.assertRaises(ValueError):
                validate_payload(forged)

    def test_reference_identity_and_source_column_cannot_be_relabelled(self):
        changes = [lambda p: p.update(reference_series_id='INNOVATION'),
                   lambda p: p['series'][1].update(name='Market equal weight'),
                   lambda p: p['series'][1].update(source_column='mkt ew'),
                   lambda p: p.update(id='hetzerk-innovation-research'),
                   lambda p: p.update(schema_version=True),
                   lambda p: p['source'].update(sha256='0' * 64)]
        for change in changes:
            forged = deepcopy(self.payload)
            change(forged)
            with self.assertRaises(ValueError):
                validate_payload(forged)

    def test_unknown_fields_and_supplied_prose_are_not_published(self):
        forged = deepcopy(self.payload)
        forged['title'] = '<script>unsafe</script>'
        forged['methodology'] = ['Verified actual ETF returns']
        forged['source']['url'] = 'javascript:unsafe'
        forged['extra'] = 'ignored'
        forged['series'][0]['extra'] = 'ignored'
        forged['series'][0]['observations'][0]['extra'] = 'ignored'
        self.assertEqual(validate_payload(forged), self.payload)

    def test_order_can_be_canonicalized_but_period_cannot_change(self):
        reordered = deepcopy(self.payload)
        reordered['series'].reverse()
        self.assertEqual(validate_payload(reordered), self.payload)
        forged = deepcopy(self.payload)
        forged['period']['start'] = '2003-04-30'
        with self.assertRaises(ValueError):
            validate_payload(forged)

    def test_direct_row_import_rejects_wrong_endpoints_and_gaps(self):
        rows = deepcopy(self.rows)
        rows[0]['Predicted innovation'] = 1.0
        with self.assertRaises(ValueError):
            validate_rows(rows)
        rows = deepcopy(self.rows)
        rows[100]['date'] = rows[99]['date']
        with self.assertRaises(ValueError):
            build_payload(rows)


if __name__ == '__main__':
    unittest.main()
