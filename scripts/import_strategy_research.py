#!/usr/bin/env python3
"""Import the exact supplied monthly backtest levels; never synthesize returns.

The pinned workbook is a transcription of spreadsheet screenshots. Its hash
matches the supplied opening-exhibit artwork audit. This is source preservation,
not verification of the underlying investment backtest. Uses only stdlib.
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import posixpath
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = 'e3a7fb267cc88179b1a0f5d428c7b6c12403021bdf6d60a79cd35cd79c01303f'
# Separately pin every selected source observation, including interior months.
# Canonical records are ID + TAB + ISO date + TAB + two-decimal level + LF,
# in SERIES order followed by chronological order. Numeric 1 and 1.0 agree.
EXPECTED_OBSERVATIONS_SHA256 = '72c376d4e928e624735ba98ba105c83791d2d9c7a40a18de098321270fa56e4f'
EXPECTED_COLUMNS = ['date', 'mkt', 'mkt ew', 'non_rd', 'rd_other', 'inno', 'inno eb', '150 75', '200 100', '250 125']
SERIES = [
    ('INNOVATION_LEADER', 'Innovation Leader', 'inno eb'),
    ('LAGGARD', 'Laggard', 'rd_other'),
    ('MARKET_BACKTEST', 'Market Backtest', 'mkt'),
    ('MARKET_EQUAL_WEIGHT', 'Market Equal Weight', 'mkt ew'),
    ('NON_RD', 'Non-R&D Payers', 'non_rd'),
]
START, END, COUNT = '2003-04-30', '2026-08-31', 281
ENDPOINTS = {'inno eb': 48.08, 'rd_other': 15.73, 'mkt': 13.37, 'mkt ew': 13.04, 'non_rd': 11.0}
NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def _cell_value(cell, shared_strings):
    if cell.find('x:f', NS) is not None:
        raise ValueError('Source formulas cannot be imported as unverified cached levels')
    kind = cell.get('t', 'n')
    if kind == 'inlineStr':
        return ''.join(x.text or '' for x in cell.findall('.//x:t', NS))
    value = cell.find('x:v', NS)
    if value is None or value.text is None:
        return None
    if kind == 's':
        return shared_strings[int(value.text)]
    if kind in ('str', 'd'):
        return value.text
    if kind != 'n':
        raise ValueError('Unsupported source cell type')
    number = float(value.text)
    if not math.isfinite(number):
        raise ValueError('Non-finite source number')
    return number


def _excel_date(value, epoch):
    if isinstance(value, str):
        parsed = date.fromisoformat(value[:10])
        if parsed.isoformat() != value[:10]:
            raise ValueError('Noncanonical date')
        return parsed.isoformat()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value != int(value):
        raise ValueError('Source date must be a whole Excel date')
    return (epoch + timedelta(days=int(value))).isoformat()


def read_source(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Source SHA-256 does not match the reviewed workbook and exhibit audit')
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = workbook.findall('x:sheets/x:sheet', NS)
        sheet = next((s for s in sheets if s.get('name') == 'monthly_levels'), None)
        if sheet is None:
            raise ValueError('Expected monthly_levels worksheet is missing')
        relationship_id = sheet.get('{'+NS['r']+'}id')
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        relation = next((r for r in relationships if r.get('Id') == relationship_id), None)
        if relation is None or relation.get('TargetMode') == 'External':
            raise ValueError('Missing or external worksheet relationship')
        target = relation.get('Target', '')
        member = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
        if not member.startswith('xl/') or member not in archive.namelist():
            raise ValueError('Invalid internal worksheet path')
        properties = workbook.find('x:workbookPr', NS)
        epoch = date(1904, 1, 1) if properties is not None and properties.get('date1904') in ('1', 'true') else date(1899, 12, 30)
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = ET.fromstring(archive.read('xl/sharedStrings.xml'))
            strings = [''.join(t.text or '' for t in si.findall('.//x:t', NS)) for si in shared.findall('x:si', NS)]
        sheet_xml = ET.fromstring(archive.read(member))
        cells = {c.get('r'): _cell_value(c, strings) for c in sheet_xml.findall('.//x:sheetData/x:row/x:c', NS)}
        columns = [cells.get(f'{letter}4') for letter in 'ABCDEFGHIJ']
        if columns != EXPECTED_COLUMNS:
            raise ValueError('Source column names or order changed')
        provenance = cells.get('A2', '')
        if 'uploaded screenshots' not in provenance or '281 monthly observations' not in provenance:
            raise ValueError('The expected transcription provenance note is missing')
        rows = []
        for row_number in range(5, 286):
            values = [cells.get(f'{letter}{row_number}') for letter in 'ABCDEFGHIJ']
            values[0] = _excel_date(values[0], epoch)
            rows.append(dict(zip(columns, values)))
    validate_rows(rows)
    return rows, digest


def validate_rows(rows: list[dict]) -> None:
    if len(rows) != COUNT:
        raise ValueError('Expected all 281 monthly source observations')
    if rows[0].get('date') != START or rows[-1].get('date') != END:
        raise ValueError('Source period does not match the opening exhibit')
    previous_month = None
    for row in rows:
        value = row.get('date')
        if not isinstance(value, str):
            raise ValueError('Source date must be canonical text')
        d = date.fromisoformat(value)
        month = d.year*12+d.month
        if d.isoformat() != value or d.day != calendar.monthrange(d.year, d.month)[1]:
            raise ValueError('Source date is not a calendar month-end')
        if previous_month is not None and month != previous_month+1:
            raise ValueError('Missing, duplicate or out-of-order source month')
        for column in EXPECTED_COLUMNS[1:]:
            level = row.get(column)
            if isinstance(level, bool) or not isinstance(level, (int, float)) or not math.isfinite(level) or level <= 0:
                raise ValueError('Levels must be positive finite source numbers; missing values cannot become zero')
            if abs(level-round(level, 2)) > 1e-9:
                raise ValueError('Unexpected precision: reviewed source levels have two decimal places')
        previous_month = month
    for column, endpoint in ENDPOINTS.items():
        if rows[0][column] != 1 or rows[-1][column] != endpoint:
            raise ValueError('Source endpoints do not reconcile to the matched artwork audit')


def build_payload(rows: list[dict], digest: str = EXPECTED_SHA256) -> dict:
    validate_rows(rows)
    if digest != EXPECTED_SHA256:
        raise ValueError('Unreviewed source digest')
    result = _public_metadata()
    result['series'] = [
        {'id': identity, 'name': name, 'source_column': column,
         'observations': [{'date': row['date'], 'level': row[column]} for row in rows]}
        for identity, name, column in SERIES
    ]
    _verify_observations(result['series'])
    return result


def _verify_observations(series: list[dict]) -> None:
    """Require the exact reviewed path after structure and numeric validation."""
    canonical = ''.join(
        f"{item['id']}\t{point['date']}\t{point['level']:.2f}\n"
        for item in series for point in item['observations']
    )
    if hashlib.sha256(canonical.encode('ascii')).hexdigest() != EXPECTED_OBSERVATIONS_SHA256:
        raise ValueError('Research observations SHA-256 differs from the reviewed source path')


def _public_metadata() -> dict:
    return {
        'schema_version': 1,
        'id': 'hetzerk-innovation-research',
        'frequency': 'monthly',
        'title': 'Hetzerk strategy research',
        'period': {'start': START, 'end': END},
        'source': {
            'title': 'Monthly research workbook underlying the opening backtest exhibit',
            'sha256': EXPECTED_SHA256,
            'precision': 'Levels transcribed to two decimal places',
            'provenance': 'Transcribed from source spreadsheet screenshots; matched to the opening backtest exhibit.',
            'url': '/research/the-measure-of-fire.html',
        },
        'methodology': [
            'Hypothetical strategy research, not actual REDI ETF performance, NAV or market price.',
            'The 281 observations are calendar month-end cumulative growth levels from April 30, 2003 through August 31, 2026. They are not daily quotes or logarithmic return increments.',
            'The supplied workbook transcribes spreadsheet screenshots to two decimal places. Its file hash and ending levels match the opening backtest artwork audit; the underlying portfolio-level backtest has not been independently verified.',
            'Period returns can be calculated as ending level / starting level - 1. A logarithmic chart changes only the axis. Source rounding limits the precision of derived returns and risk statistics.',
            'Dividend reinvestment, management fees, trading costs and other backtest assumptions are not specified by the source workbook. No dividends or fees are added, removed or inferred during import.',
            'The Market Backtest is the supplied research comparison series. Its index definition is unverified; it is not identified as SPY, the S&P 500 or the Morningstar US Market Index.',
            'The opening exhibit uses the inno eb research variant. Separate annual and horizon tables in the deck contain different results and are not combined with this monthly history.',
            'No interpolation, daily backfill or extension beyond the last supplied observation is performed. The first observation is a baseline; 2003 and 2026 are partial calendar-year windows.',
        ],
    }



def validate_payload(payload: dict) -> dict:
    """Validate public monthly history and return only reviewed schema fields.

    The source digest identifies the reviewed input. It does not authenticate a
    browser submission; publication still uses the repository-owned dataset.
    All prose/labels/URLs are regenerated from reviewed constants, never trusted
    from cache input. Only canonical dates and finite numeric levels are copied.
    """
    if not isinstance(payload, dict) or isinstance(payload.get('schema_version'), bool) or payload.get('schema_version') != 1:
        raise ValueError('Unknown strategy research schema')
    if payload.get('id') != 'hetzerk-innovation-research' or payload.get('frequency') != 'monthly':
        raise ValueError('Unexpected dataset identity or frequency')
    if payload.get('period') != {'start': START, 'end': END}:
        raise ValueError('Research period does not match the reviewed source')
    source = payload.get('source')
    if not isinstance(source, dict) or source.get('sha256') != EXPECTED_SHA256:
        raise ValueError('Unrecognized research source')
    supplied = payload.get('series')
    if not isinstance(supplied, list) or len(supplied) != len(SERIES):
        raise ValueError('Expected five research series')
    by_id = {}
    for item in supplied:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in by_id:
            raise ValueError('Duplicate or invalid research series')
        by_id[item['id']] = item
    if set(by_id) != {entry[0] for entry in SERIES}:
        raise ValueError('Unknown or missing research series')
    rows = []
    for index in range(COUNT):
        month_index = 2003*12+3+index
        year, month_zero = divmod(month_index, 12)
        month = month_zero+1
        day = calendar.monthrange(year, month)[1]
        expected_date = date(year, month, day).isoformat()
        row = {'date': expected_date}
        for identity, name, column in SERIES:
            item = by_id[identity]
            if item.get('name') != name or item.get('source_column') != column:
                raise ValueError('Research series label or source-column identity changed')
            observations = item.get('observations')
            if not isinstance(observations, list) or len(observations) != COUNT:
                raise ValueError('Research series has missing or extra months')
            point = observations[index]
            if not isinstance(point, dict) or point.get('date') != expected_date:
                raise ValueError('Research dates must be aligned, complete calendar month-ends')
            level = point.get('level')
            if isinstance(level, bool) or not isinstance(level, (int, float)) or not math.isfinite(level) or level <= 0:
                raise ValueError('Invalid research level')
            if abs(level-round(level, 2)) > 1e-9:
                raise ValueError('Research level exceeds reviewed source precision')
            if index == 0 and level != 1 or index == COUNT-1 and level != ENDPOINTS[column]:
                raise ValueError('Research endpoints differ from the reviewed exhibit')
            row[column] = level
        rows.append(row)
    # Reuse the reviewed metadata without fabricating any absent source series.
    result = _public_metadata()
    result['series'] = [
        {'id': identity, 'name': name, 'source_column': column,
         'observations': [{'date': row['date'], 'level': row[column]} for row in rows]}
        for identity, name, column in SERIES
    ]
    _verify_observations(result['series'])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='The reviewed source .xlsx file; it is read only')
    parser.add_argument('--output', type=Path, default=ROOT/'data'/'strategy_research.json')
    args = parser.parse_args()
    rows, digest = read_source(args.source)
    payload = validate_payload(build_payload(rows, digest))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=args.output.parent, prefix='.strategy-research-', suffix='.tmp', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
        handle.write('\n')
    try:
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Imported {len(rows)} monthly observations for {len(SERIES)} series, {START} to {END}.')


if __name__ == '__main__':
    main()
