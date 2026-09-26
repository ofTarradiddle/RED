"""Refresh the independent dividend subledger without replacing stock valuations."""
import argparse
import json
from pathlib import Path

from lib.etf.dividend_book import update
from lib.etf.operating_book import update as update_operating_book
from scripts.refresh_spy import refresh_lock

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached',action='store_true',help='Recalculate from archived action histories')
    args=parser.parse_args();output=ROOT/'data/shadow_spy'
    with refresh_lock(output/'refresh.lock'):
        path=output/'latest.json';report=json.loads(path.read_text())
        update(report,output,fetch=not args.cached)
        update_operating_book(report,output)
        temp=path.with_suffix('.next.json');temp.write_text(json.dumps(report,indent=2,allow_nan=False));temp.replace(path)


if __name__=='__main__':main()
