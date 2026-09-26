"""Replay the daily operating book from cached holdings/action/price evidence."""
import argparse
import json
from pathlib import Path

from lib.etf.operating_book import update, save
from scripts.refresh_spy import refresh_lock

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through', help='Calendar cutoff YYYY-MM-DD; session marks must exist')
    args = parser.parse_args(); output = ROOT/'data/shadow_spy'
    with refresh_lock(output/'refresh.lock'):
        path = output/'latest.json'; report = json.loads(path.read_text())
        book = update(report, output, through=args.through)
        save(path, report)
        if book.get('error'):
            raise SystemExit(book['error'])


if __name__ == '__main__':main()
