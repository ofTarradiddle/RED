"""Integrity checks for the supplied monthly research-level import."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET

from scripts.import_strategy_research import (
    COUNT, ENDPOINTS, EXPECTED_SHA256, SERIES, _cell_value, _excel_date,
    read_source, validate_payload,
)
from datetime import date

ROOT = Path(__file__).resolve().parents[1]


class StrategyResearchImportTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'data'/'strategy_research.json').read_text())

    def test_committed_payload_matches_reviewed_contract(self):
        clean = validate_payload(self.data)
        self.assertEqual(clean, self.data)
        self.assertEqual(clean['source']['sha256'], EXPECTED_SHA256)
        self.assertEqual([s['id'] for s in clean['series']], [s[0] for s in SERIES])
        self.assertEqual(sum(len(s['observations']) for s in clean['series']), COUNT*5)

    def test_source_mapping_preserves_the_selected_research_variant(self):
        series = validate_payload(self.data)['series']
        self.assertEqual(series[0]['source_column'], 'inno eb')
        for item in series:
            self.assertEqual(item['observations'][0]['level'], 1)
            self.assertEqual(item['observations'][-1]['level'], ENDPOINTS[item['source_column']])
        self.assertEqual(series[0]['observations'][1], {'date':'2003-05-31','level':1.18})
        self.assertNotEqual(series[0]['observations'][-1]['level'], 42.02)

    def test_does_not_invent_daily_returns_or_distribution_fields(self):
        for series in validate_payload(self.data)['series']:
            self.assertEqual(len(series['observations']), 281)
            self.assertTrue(all(set(p) == {'date','level'} for p in series['observations']))
        self.assertEqual(self.data['period'], {'start':'2003-04-30','end':'2026-08-31'})

    def test_missing_duplicate_unsorted_and_non_month_end_dates_fail(self):
        for replacement in ('2003-04-30','2003-07-31','2003-05-30','2003-02-29','2003-5-31'):
            with self.subTest(replacement=replacement):
                bad = deepcopy(self.data)
                bad['series'][0]['observations'][1]['date'] = replacement
                with self.assertRaises(ValueError): validate_payload(bad)

    def test_missing_or_extra_month_fails(self):
        for extra in (False, True):
            bad = deepcopy(self.data)
            observations = bad['series'][0]['observations']
            if extra: observations.append(deepcopy(observations[-1]))
            else: observations.pop(100)
            with self.assertRaises(ValueError): validate_payload(bad)

    def test_level_type_range_and_source_precision_failures(self):
        for level in (None, 0, -1, True, '1.18', float('nan'), float('inf'), 1.181):
            with self.subTest(level=level):
                bad = deepcopy(self.data)
                bad['series'][0]['observations'][1]['level'] = level
                with self.assertRaises(ValueError): validate_payload(bad)

    def test_bounds_and_reviewed_endpoints_cannot_be_changed(self):
        for mutate in (
            lambda p: p['period'].update(start='2003-01-01'),
            lambda p: p['series'][0]['observations'][0].update(level=100),
            lambda p: p['series'][0]['observations'][-1].update(level=42.02),
        ):
            bad = deepcopy(self.data); mutate(bad)
            with self.assertRaises(ValueError): validate_payload(bad)

    def test_each_series_interior_path_is_pinned_independently_of_source_metadata(self):
        for index, item in enumerate(self.data['series']):
            with self.subTest(series=item['id']):
                bad = deepcopy(self.data)
                point = bad['series'][index]['observations'][140]
                point['level'] = round(point['level'] + 0.01, 2)
                self.assertEqual(bad['source']['sha256'], EXPECTED_SHA256)
                with self.assertRaisesRegex(ValueError, 'observations SHA-256'):
                    validate_payload(bad)

    def test_integer_and_float_serialization_share_the_same_observation_digest(self):
        alternate = deepcopy(self.data)
        for item in alternate['series']:
            for point in item['observations']:
                if point['level'] == int(point['level']):
                    point['level'] = int(point['level'])
        self.assertEqual(validate_payload(alternate), self.data)

    def test_series_identity_and_source_column_cannot_be_substituted(self):
        for key, value in [('id','REDI'), ('name','<script>bad()</script>'), ('source_column','inno')]:
            bad = deepcopy(self.data); bad['series'][0][key] = value
            with self.assertRaises(ValueError): validate_payload(bad)
        bad = deepcopy(self.data); bad['series'][1] = deepcopy(bad['series'][0])
        with self.assertRaises(ValueError): validate_payload(bad)

    def test_unknown_fields_and_untrusted_prose_are_not_published(self):
        bad = deepcopy(self.data)
        bad.update(private_path='/private/local/file', title='<script>bad()</script>', methodology=['unverified claim'])
        bad['source'].update(url='javascript:bad()', title='unreviewed', private_key='do not publish')
        bad['series'][0]['observations'][0]['distribution'] = 123
        bad['series'][0]['extra'] = 'unreviewed'
        self.assertEqual(validate_payload(bad), self.data)

    def test_unknown_schema_frequency_and_source_fail(self):
        for key, value in [('schema_version', True), ('schema_version', 2), ('frequency','daily'), ('id','other')]:
            bad = deepcopy(self.data); bad[key] = value
            with self.assertRaises(ValueError): validate_payload(bad)
        bad = deepcopy(self.data); bad['source']['sha256'] = '0'*64
        with self.assertRaises(ValueError): validate_payload(bad)

    def test_wrong_workbook_hash_fails_before_reading_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.xlsx'; source.write_bytes(b'not the reviewed workbook')
            with self.assertRaisesRegex(ValueError, 'SHA-256'): read_source(source)

    def test_formula_cache_is_not_accepted_as_source_data(self):
        cell = ET.fromstring('<c xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><f>1+1</f><v>2</v></c>')
        with self.assertRaisesRegex(ValueError, 'formulas'): _cell_value(cell, [])

    def test_excel_dates_are_decoded_without_timezone_or_date_guessing(self):
        self.assertEqual(_excel_date(37741, date(1899,12,30)), '2003-04-30')
        self.assertEqual(_excel_date(0, date(1904,1,1)), '1904-01-01')
        with self.assertRaises(ValueError): _excel_date(37741.5, date(1899,12,30))
        with self.assertRaises(ValueError): _excel_date(True, date(1899,12,30))

    def test_validation_does_not_mutate_its_input(self):
        original = deepcopy(self.data)
        result = validate_payload(self.data)
        self.assertEqual(self.data, original)
        result['series'][0]['observations'][0]['level'] = 7
        self.assertEqual(self.data['series'][0]['observations'][0]['level'], 1)


if __name__ == '__main__':
    unittest.main()
