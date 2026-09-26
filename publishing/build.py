"""Validate first, stage a complete immutable release, then atomically switch dist."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from publishing.workbook import import_workbook
from publishing.site import generate_pages, csv_text
from publishing.visibility import public_snapshot
from publishing.seo import apply_seo, robots_text, sitemap_xml, validate_site_url

ROOT = Path(__file__).resolve().parents[1]


def build(workbook, output=ROOT / "dist", proxy_path=None, base_path='', *, site_url=None, indexable=False):
    site_url = validate_site_url(site_url, base_path, indexable)
    workbook = Path(workbook).resolve()
    snapshot = import_workbook(workbook)
    if proxy_path:
        from publishing.spy_proxy import apply_proxy
        snapshot = apply_proxy(snapshot,Path(proxy_path))
    pages = generate_pages(snapshot)
    if proxy_path:
        from bs4 import BeautifulSoup
        from publishing.masthead import refine_masthead
        for route,html in pages.items():
            page=BeautifulSoup(html,'html.parser')
            banner=page.select_one('.demo-strip')
            if banner:
                banner.string='Illustrative demo · SPY-based stock allocation, rescaled quantities and inferred prices · NAV and performance remain fictional · Not an investment offering'
                refine_masthead(page)
            pages[route]=str(page)
    pages = apply_seo(pages, site_url=site_url, base_path=base_path, indexable=indexable)
    if base_path:
        import re
        if not re.fullmatch(r'/[A-Za-z0-9_-]+',base_path):
            raise ValueError('Expected a single GitHub Pages repository path, e.g. /RED')
        pages={route:re.sub(r'((?:href|src|action)=["\'])/(?!/)',lambda m:m[1]+base_path+'/',html)
               for route,html in pages.items()}
    snapshot = public_snapshot(snapshot)
    releases = ROOT / '.site-builds'
    releases.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='release-', dir=releases))
    try:
        for route, content in pages.items():
            target = stage / route
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        shutil.copytree(ROOT / 'assets', stage / 'assets')
        shutil.copyfile(workbook, stage / 'review/hetzerk-demo.xlsx')
        if hashlib.sha256((stage / 'review/hetzerk-demo.xlsx').read_bytes()).hexdigest() != snapshot['source_sha256']:
            raise ValueError('Workbook changed during the build; save it and rebuild')
        (stage / 'data').mkdir()
        (stage / 'data/snapshot.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False))
        if proxy_path:
            shutil.copyfile(proxy_path,stage/'data/spy-source.json')
        for fund in snapshot['funds']:
            target = stage / 'etfs' / fund['fund_id'] / 'data'
            target.mkdir(parents=True, exist_ok=True)
            (target / 'snapshot.json').write_text(json.dumps(fund, indent=2, allow_nan=False))
            for key in ('holdings','daily','distributions'):
                (target / f'{key}.csv').write_text(csv_text(fund[key]))
            if fund['fund_id'] == 'redi':
                from publishing.fact_sheet_pdf import render_fact_sheet_pdf
                render_fact_sheet_pdf(fund, target.parent / 'fact-sheet.pdf', site_url=site_url)
        (stage / 'robots.txt').write_text(robots_text(site_url, indexable=indexable))
        (stage / 'sitemap.xml').write_text(sitemap_xml(pages, site_url, indexable=indexable))
        output = Path(output).absolute()
        if output.exists() and not output.is_symlink():
            raise ValueError(f'{output} is an existing directory; choose a new output path')
        link = output.with_name(output.name + f'.next-{uuid4().hex}')
        link.symlink_to(stage, target_is_directory=True)
        os.replace(link, output)
        return snapshot
    except Exception:
        shutil.rmtree(stage)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook', type=Path, default=ROOT/'workbooks/hetzerk-demo.xlsx')
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    parser.add_argument('--base-path', default='')
    parser.add_argument('--site-url', help='Configured public HTTPS site URL, including the repository path')
    parser.add_argument('--indexable', action='store_true', help='Allow current public pages into search; requires --site-url')
    parser.add_argument('--workbook-only',action='store_true')
    args = parser.parse_args()
    try:
        proxy=ROOT/'data/spy_public.json'
        result = build(args.workbook, args.output, proxy if proxy.exists() and not args.workbook_only else None,args.base_path,
                       site_url=args.site_url, indexable=args.indexable)
    except Exception as exc:
        parser.exit(1, f'Build failed; previous release preserved. {exc}\n')
    print(f"Built {len(result['funds'])} demo funds from {args.workbook.name}; snapshot {result['source_sha256'][:16]}.")


if __name__ == '__main__':
    main()
