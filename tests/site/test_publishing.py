"""Economic, validation and public-route regression tests for workbook publishing."""
from copy import deepcopy
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from publishing import workbook as module
from publishing.build import build
from publishing.site import generate_pages, csv_text
from publishing.workbook import WorkbookError, import_workbook, read_tables, performance
from publishing.visibility import public_snapshot

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT/'workbooks/hetzerk-demo.xlsx'


@pytest.fixture(scope='module')
def snapshot():
    return import_workbook(BOOK)


def test_all_funds_reconcile(snapshot):
    assert {f['fund_id'] for f in snapshot['funds']} == {'redi','dam1','azoc','mpd','meri'}
    for f in snapshot['funds']:
        assert sum(h['weight'] for h in f['holdings']) == pytest.approx(1)
        assert sum(h['market_value'] for h in f['holdings']) == pytest.approx(f['daily'][-1]['net_assets'])
        assert f['returns']['5Y'] is None
        assert f['spread']['median_30_day'] is None
        assert {h['date'] for h in f['holdings']} == {f['as_of']}
        assert f['daily'][0]['date'] < f['as_of']


def test_total_return_reinvests_distribution_and_uses_prior_year_close():
    rows = [dict(date=d,nav=n,market_price=m,distribution_per_share=c,benchmark_index=b)
            for d,n,m,c,b in [('2024-12-31',100,100,0,100),('2025-01-02',99,100,1,101),('2025-01-03',108.9,110,0,102)]]
    daily, returns = performance(rows)
    assert daily[-1]['nav_total_return'] == pytest.approx(110)
    assert returns['YTD']['nav_total_return'] == pytest.approx(.1)
    assert returns['YTD']['market_total_return'] == pytest.approx(.111)
    assert returns['YTD']['benchmark_index'] == pytest.approx(.02)
    assert returns['1Y'] is None


@pytest.mark.parametrize('case', ['nan','missing','duplicate','date','weight','distribution','live','unknown','fx','negative'])
def test_rejects_bad_inputs(case, monkeypatch):
    tables = read_tables(BOOK)
    if case=='nan': tables['Daily Data'][0]['nav']=float('nan')
    if case=='missing': tables['Daily Data'][0]['nav']=None
    if case=='duplicate': tables['Daily Data'].append(tables['Daily Data'][0])
    if case=='date': tables['Holdings'][0]['date']='2020-01-01'
    if case=='weight': tables['Funds'][0]['cash_weight']=.5
    if case=='distribution': tables['Daily Data'][0]['distribution_per_share']=1
    if case=='live': tables['Funds'][0]['is_demo']=False
    if case=='unknown': tables['Holdings'][0]['fund_id']='absent'
    if case=='fx': tables['Holdings'][0]['fx_rate']=2
    if case=='negative': tables['Holdings'][0]['quantity']=-1
    monkeypatch.setattr(module,'read_tables',lambda path:tables)
    with pytest.raises(WorkbookError):import_workbook(BOOK)


def test_changed_workbook_reaches_every_holdings_view(tmp_path):
    changed=tmp_path/'changed.xlsx'
    found=False
    # Edit a disposable OOXML fixture while preserving all workbook structure.
    with ZipFile(BOOK) as src, ZipFile(changed,'w',ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data=src.read(item.filename)
            if item.filename.endswith('.xml') and b'Abbott Laboratories' in data:
                data=data.replace(b'Abbott Laboratories',b'Example &lt;Company&gt; &amp; Co')
                found=True
            dst.writestr(item,data)
    assert found
    new=import_workbook(changed)
    redi=next(f for f in new['funds'] if f['fund_id']=='redi')
    pages=generate_pages(new)
    assert 'Example &lt;Company&gt; &amp; Co' in pages['etfs/redi/index.html']
    assert 'Example &lt;Company&gt; &amp; Co' in pages['etfs/redi/holdings.html']
    assert 'Example <Company> & Co' in csv_text(redi['holdings'])
    assert '<Company>' not in pages['etfs/redi/index.html']


def test_failed_build_preserves_previous_release(tmp_path,monkeypatch):
    out=tmp_path/'public'
    build(BOOK,out)
    previous=out.resolve()
    content=(out/'index.html').read_bytes()
    import publishing.build as builder
    monkeypatch.setattr(builder,'import_workbook',lambda _: (_ for _ in ()).throw(WorkbookError('bad input')))
    with pytest.raises(WorkbookError):builder.build(BOOK,out)
    assert out.resolve()==previous
    assert (out/'index.html').read_bytes()==content


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.links=[];self.head=False;self.og_image=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='head':self.head=True
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'duplicate ID {attrs["id"]}'
            self.ids.add(attrs['id'])
        for key in ('href','src'):
            if key in attrs:self.links.append(attrs[key])
        if tag=='meta' and attrs.get('property')=='og:image':
            assert self.head, 'OG image metadata belongs in head'
            self.og_image=True
    def handle_endtag(self,tag):
        if tag=='head':self.head=False


def test_all_generated_routes_assets_and_anchors(snapshot):
    pages=generate_pages(snapshot)
    parsed={}
    for path,content in pages.items():
        parser=Links();parser.feed(content);parsed[path]=parser
        assert 'Illustrative demo' in content
        assert '555-' not in content
        assert 'SEC Registered' not in content
        assert 'Sample data loaded' not in content
    assert parsed['index.html'].og_image
    for path,parser in parsed.items():
        for link in parser.links:
            url=urlsplit(link)
            if url.scheme or url.netloc:continue
            route=unquote(url.path).lstrip('/') if url.path else path
            if url.path.endswith('/'):route+='index.html'
            if url.fragment and not url.path:route=path
            if route in parsed:
                if url.fragment:assert url.fragment in parsed[route].ids,(path,link)
            elif route.startswith('assets/'):
                assert (ROOT/route).exists(),(path,link)
            else:
                assert route=='review/hetzerk-demo.xlsx' or route.endswith(('/holdings.csv','/daily.csv','/distributions.csv')),(path,link)


def test_spread_and_data_labels_are_honest(snapshot):
    pages=generate_pages(snapshot)
    for f in public_snapshot(snapshot)['funds']:
        page=pages[f'etfs/{f["fund_id"]}/index.html']
        assert 'Daily closing prices cannot supply this measure' in page
        assert 'Days with a closing deviation greater than 2%' in page
        assert 'Data Start:' in page
        assert 'Illustrative demo' in page


def test_csv_formula_text_is_escaped():
    assert "'=HYPERLINK" in csv_text([{'ticker':'=HYPERLINK("x")'}])


def test_draft_document_url_is_preserved_and_escaped(snapshot):
    data=deepcopy(snapshot)
    doc=data['funds'][0]['documents'][0]
    doc['url']='https://example.org/draft.pdf?version=1&title=Fund%20Draft'
    doc['status']='draft'
    page=generate_pages(data)[f'etfs/{data["funds"][0]["fund_id"]}/index.html']
    parsed=Links();parsed.feed(page)
    assert doc['url'] in parsed.links
