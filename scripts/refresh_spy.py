"""Refresh issuer holdings, Yahoo prices and local accounting evidence; build public Pages."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path

from lib.etf.daily_spy import refresh
from lib.etf.ledger import walkthrough
from publishing.spy_proxy import public_input

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def refresh_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    try: fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError: raise RuntimeError('A refresh is already running; inspect/remove a stale lock only after checking the process')
    try:
        os.write(fd,str(os.getpid()).encode());os.close(fd)
        yield
    finally: path.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--cached',action='store_true',help='Rebuild from latest archived report without fetching')
    parser.add_argument('--base-path',default='')
    parser.add_argument('--site-url',help='Configured public HTTPS site URL, including the repository path')
    parser.add_argument('--indexable',action='store_true',help='Allow current public pages into search; requires --site-url')
    args=parser.parse_args()
    if args.build:
        from publishing.seo import validate_site_url
        validate_site_url(args.site_url,args.base_path,args.indexable)
    with refresh_lock(ROOT/'data/shadow_spy/refresh.lock'):
        report=json.loads((ROOT/'data/shadow_spy/latest.json').read_text()) if args.cached else refresh(ROOT/'data/shadow_spy')
        public_path=ROOT/'data/spy_public.json'
        temp=public_path.with_suffix('.next.json')
        temp.write_text(json.dumps(public_input(report),indent=2,allow_nan=False));temp.replace(public_path)
        example=walkthrough()
        # Private example contains only deliberately assumed entries, not an issuer blotter.
        def encode(v):
            if isinstance(v,set):return sorted(v)
            return str(v)
        (ROOT/'data/shadow_spy/walkthrough.json').write_text(json.dumps(example,default=encode,indent=2))
        if args.build:
            from publishing.build import build
            build(ROOT/'workbooks/hetzerk-demo.xlsx',proxy_path=public_path,base_path=args.base_path,
                  site_url=args.site_url,indexable=args.indexable)
        print(f"Updated public holdings as of {report['as_of']}. Private reconciliation: {report['valuation']['status']}.")


if __name__=='__main__': main()
