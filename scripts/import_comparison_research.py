#!/usr/bin/env python3
"""Preserve the supplied nine-series monthly comparison research table.

Source values are cumulative levels, not return increments. This importer is
independent of the original ETF/PDF research import and uses only the stdlib.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import date, datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / 'data' / 'research' / 'comparison-monthly-levels.tsv'
OUTPUT_PATH = ROOT / 'data' / 'comparison_research.json'
EXPECTED_SHA256 = '21bc39630f829b9787021590e49b09cc496b1a7c8edbf937399643a5f5cb7443'
# ID + TAB + ISO month-end + TAB + exact two-decimal level + LF, in SERIES
# order then chronological order. This pins every interior observation too.
EXPECTED_OBSERVATIONS_SHA256 = 'bd31143107978b0b5dc240122aab89eacc5422aff082a9a8ff50152c06f732db'
START, END, COUNT = '2002-08-31', '2026-08-31', 289
REFERENCE_SERIES_ID = 'PREDICTED_INNOVATION'
SERIES = [
    ('MARKET', 'Market', 'market'),
    ('MARKET_CAP', 'Market cap', 'market_cap'),
    ('NON_RD', 'Non RD', 'non_rd'),
    ('RD_OTHER', 'RD other', 'rd_other'),
    ('INNOVATION', 'Innovation', 'innovation'),
    ('PREDICTED_INNOVATION', 'Predicted innovation', 'Predicted innovation'),
    ('INNOVATION_150_75', 'Innovation 150 / 75', 'innovation_150_75'),
    ('INNOVATION_200_100', 'Innovation 200 / 100', 'innovation_200_100'),
    ('INNOVATION_250_125', 'Innovation 250 / 125', 'innovation_250_125'),
]
EXPECTED_COLUMNS = ['date'] + [s[2] for s in SERIES]
FIRST_LEVELS = dict(zip(EXPECTED_COLUMNS[1:], [1, 1, 1, 1, .99, .99, .99, .99, .99]))
LAST_LEVELS = dict(zip(EXPECTED_COLUMNS[1:], [13.97, 13.22, 11.41, 16.20, 50.62, 65.75, 41.65, 35.75, 28.29]))


def expected_dates() -> list[str]:
    result = []
    for index in range(COUNT):
        year, zero_month = divmod(2002 * 12 + 7 + index, 12)
        month = zero_month + 1
        result.append(date(year, month, calendar.monthrange(year, month)[1]).isoformat())
    return result


def _level(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Research levels must be positive finite numbers')
    if value != round(value, 2):
        raise ValueError('Research level exceeds the supplied two-decimal precision')
    return value


def validate_rows(rows: list[dict]) -> None:
    if not isinstance(rows, list) or len(rows) != COUNT:
        raise ValueError('Expected all 289 supplied monthly observations')
    for row, expected in zip(rows, expected_dates()):
        if not isinstance(row, dict) or row.get('date') != expected:
            raise ValueError('Research dates must be complete, aligned calendar month-ends')
        for column in EXPECTED_COLUMNS[1:]:
            _level(row.get(column))
    for column in EXPECTED_COLUMNS[1:]:
        if rows[0][column] != FIRST_LEVELS[column] or rows[-1][column] != LAST_LEVELS[column]:
            raise ValueError('Research endpoints differ from the supplied table')


def read_source(path: Path = SOURCE_PATH) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Source SHA-256 differs from the reviewed comparison table')
    records = list(csv.reader(io.StringIO(raw.decode('utf-8')), delimiter='\t'))
    # The original has a trailing empty tab column and one final blank row.
    header = records[0][:-1] if records[0][-1] == '' else records[0]
    if header != EXPECTED_COLUMNS:
        raise ValueError('Source column names or order changed')
    rows = []
    for record in records[1:]:
        if not any(record):
            continue
        values = record[:-1] if record[-1] == '' else record
        if len(values) != len(EXPECTED_COLUMNS):
            raise ValueError('Source row has missing or extra fields')
        d = datetime.strptime(values[0], '%m/%d/%Y').date().isoformat()
        if not all(re.fullmatch(r'[0-9]+\.[0-9]{2}', v) for v in values[1:]):
            raise ValueError('Source levels must retain their exact two-decimal format')
        rows.append(dict(zip(EXPECTED_COLUMNS, [d] + [float(v) for v in values[1:]])))
    validate_rows(rows)
    return rows, digest


def _public_metadata() -> dict:
    return {
        'schema_version': 1,
        'id': 'hetzerk-comparison-research',
        'frequency': 'monthly',
        'title': 'Hetzerk comparison research',
        'reference_series_id': REFERENCE_SERIES_ID,
        'period': {'start': START, 'end': END},
        'source': {
            'title': 'Monthly innovation comparison research',
            'sha256': EXPECTED_SHA256,
            'precision': 'Cumulative levels supplied to two decimal places',
            'provenance': 'Imported from the supplied tab-separated monthly table. Original values and source headers are preserved.',
            'url': '/compare/research-source.tsv',
        },
        'methodology': [
            'Hypothetical research series, not actual REDI ETF performance, NAV or market price.',
            'Each series contains 289 consecutive calendar month-end cumulative levels from August 31, 2002 through August 31, 2026. These are levels, not monthly percentages or logarithmic return increments.',
            'Predicted innovation is the default reference series. The five innovation columns begin at 0.99; the other four begin at 1.00. Comparisons must rebase each path to its own first common observation.',
            'Period return equals ending level / starting level - 1. A logarithmic chart changes only the axis. Two-decimal source precision limits derived return and risk statistics.',
            'Dividend reinvestment, management fees, trading costs, rebalancing rules and other backtest assumptions are unspecified. No dividends, fees or missing observations are inferred during import.',
            'Market and Market cap are source research labels with unverified definitions. They are not identified as SPY, the S&P 500 or the Morningstar US Market Index. The numeric innovation suffixes are preserved without interpreting them as portfolio weights.',
            'This table is a separate comparison research source. It is not attributed to the earlier ETF-page PDF exhibit. No daily interpolation, backfill or extension beyond the supplied endpoint is performed.',
        ],
    }


def _verify_observations(series: list[dict]) -> None:
    canonical = ''.join(
        f"{item['id']}\t{p['date']}\t{p['level']:.2f}\n"
        for item in series for p in item['observations']
    )
    if hashlib.sha256(canonical.encode('ascii')).hexdigest() != EXPECTED_OBSERVATIONS_SHA256:
        raise ValueError('Research observation SHA-256 differs from the reviewed path')


def build_payload(rows: list[dict], digest: str = EXPECTED_SHA256) -> dict:
    validate_rows(rows)
    if digest != EXPECTED_SHA256:
        raise ValueError('Unrecognized comparison source digest')
    result = _public_metadata()
    result['series'] = [
        {'id': identity, 'name': name, 'source_column': column,
         'observations': [{'date': row['date'], 'level': row[column]} for row in rows]}
        for identity, name, column in SERIES
    ]
    _verify_observations(result['series'])
    return result


def validate_payload(payload: dict) -> dict:
    """Return only reviewed schema fields, requiring the entire exact path.

    Public prose and URLs come from constants. An asserted source hash alone
    cannot authorize changed levels, labels, dates, or reference identity.
    """
    if not isinstance(payload, dict) or isinstance(payload.get('schema_version'), bool) or payload.get('schema_version') != 1:
        raise ValueError('Unknown comparison research schema')
    if payload.get('id') != 'hetzerk-comparison-research' or payload.get('frequency') != 'monthly':
        raise ValueError('Unexpected comparison identity or frequency')
    if payload.get('reference_series_id') != REFERENCE_SERIES_ID:
        raise ValueError('Comparison reference must be the supplied Predicted innovation series')
    if payload.get('period') != {'start': START, 'end': END}:
        raise ValueError('Comparison period differs from the supplied source')
    source = payload.get('source')
    if not isinstance(source, dict) or source.get('sha256') != EXPECTED_SHA256:
        raise ValueError('Unrecognized comparison source')
    supplied = payload.get('series')
    if not isinstance(supplied, list) or len(supplied) != len(SERIES):
        raise ValueError('Expected all nine comparison research series')
    by_id = {}
    for item in supplied:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in by_id:
            raise ValueError('Invalid or duplicate comparison series identity')
        by_id[item['id']] = item
    if set(by_id) != {s[0] for s in SERIES}:
        raise ValueError('Missing or unknown comparison research series')
    rows = [{'date': d} for d in expected_dates()]
    for identity, name, column in SERIES:
        item = by_id[identity]
        if item.get('name') != name or item.get('source_column') != column:
            raise ValueError('Comparison series label or source column changed')
        observations = item.get('observations')
        if not isinstance(observations, list) or len(observations) != COUNT:
            raise ValueError('Comparison series has missing or extra months')
        for row, point in zip(rows, observations):
            if not isinstance(point, dict) or point.get('date') != row['date']:
                raise ValueError('Comparison dates must be complete, aligned calendar month-ends')
            row[column] = _level(point.get('level'))
    return build_payload(rows, source['sha256'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE_PATH)
    parser.add_argument('--output', type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    rows, digest = read_source(args.source)
    payload = validate_payload(build_payload(rows, digest))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=args.output.parent, prefix='.comparison-research-', suffix='.tmp', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write('\n')
    try:
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Imported {COUNT} monthly observations for {len(SERIES)} series, {START} to {END}.')


if __name__ == '__main__':
    main()
