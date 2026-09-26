"""Protect the original site identity and journeys from another generic rewrite."""
from pathlib import Path
from bs4 import BeautifulSoup
import pytest
from publishing.site import generate_pages
from publishing.workbook import import_workbook

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def pages():
    return {key:BeautifulSoup(value,'html.parser') for key,value in generate_pages(import_workbook(ROOT/'workbooks/hetzerk-demo.xlsx')).items()}


def test_original_home_sections_and_full_names_remain(pages):
    page=pages['index.html']
    assert 'Hetzerk Asset Management' in page.title.get_text()
    assert ' '.join(page.h1.get_text().split()) == 'Hetzerk Innovation Factor ETF'
    assert 'Hetzerk Innovation Factor ETF' in page.get_text()
    assert all(page.find(id=key) for key in ('fees','innovation','services','about','contact','etfs'))
    assert len(page.select('a.etf-card'))==1
    assert page.select_one('.home-hero').find_next_sibling('section')['id'] == 'contact'
    assert not page.select('[data-innovation-journey], script[src$="innovation-journey.js"]')
    case = pages['etfs/redi/why-red.html']
    assert len(case.select('h1')) == 1
    assert case.select_one('#research-eras [data-innovation-journey]')
    assert len(case.select('[data-journey-tab]')) == 7


def test_original_etf_boxes_and_fund_specific_identity(pages):
    boxes=pages['etfs/index.html'].select('a.etf-card')
    assert len(boxes)==1
    headings={'redi':'Thematics vs Factors','dam1':'The Concentration Thesis','azoc':'The Alpha Thesis','mpd':'The Compounding Thesis','meri':'The Marriage of Quant & Fundamental'}
    for box in boxes:
        fid=box['href'].strip('/').split('/')[-1]
        assert box.select_one('.ticker-box')
        assert box.select_one('.tagline')
        page=pages[f'etfs/{fid}/index.html']
        assert headings[fid] in page.get_text()
        assert page.select_one('.home-header a[aria-label="Hetzerk Asset Management home"]')
        assert all(page.find(id=key) for key in ('overview','about','performance','holdings','documents'))
        assert {'Identifier','Shares Held','Market Value (USD)'}.issubset({th.get_text(strip=True) for th in page.select('#top-holdings th')})
    assert '#8b0000' in pages['etfs/redi/index.html'].body['style']


def test_shared_investor_navigation_preserves_direct_journeys(pages):
    expected = ['/etfs/redi/', '/#fees', '/etfs/redi/why-red.html', '/research/', '/#contact']
    for route in ('index.html', 'etfs/redi/index.html', 'etfs/redi/holdings.html',
                  'section-351.html', '351-exchanges.html', 'documents/index.html',
                  'research/index.html', 'research/the-measure-of-fire.html'):
        page = pages[route]
        assert [a['href'] for a in page.select('.home-header .home-nav a')] == expected
        assert len(page.select('.home-header')) == 1
        assert len(page.select('.home-footer [data-perspective-word]')) == 1
        assert not page.select('.sticky-banner-wrapper')
    assert pages['etfs/redi/index.html'].select_one('.home-nav a[aria-current="page"]')['href'] == '/etfs/redi/'


def test_two_distinct_351_pages_keep_their_interest_journeys(pages):
    small=pages['section-351.html'];large=pages['351-exchanges.html']
    assert small.select_one('#interest-form-s351')
    assert large.select_one('.form-section #interest-form-351')
    for page in (small,large):
        assert page.find(id='opportunities')
        assert page.find(id='register')
        assert not page.select('a[data-interest-fund]')
        form=page.select_one('[data-interest-form]')
        assert {field['name'] for field in form.select('input,select,textarea')}=={'name','email','type','fund','notes'}
        assert [o['value'] for o in form.select('select[name=fund] option')]==['REDI']
        assert 'no capital gains today' not in page.get_text().lower()
        assert not page.select('[onclick],[onsubmit]')


def test_original_research_content_survives(pages):
    case=pages['etfs/redi/why-red.html']
    case_text=case.get_text(' ',strip=True)
    for phrase in ('Innovation value','Innovation ability','Equal weighting','Innovation at a justifiable valuation'):
        assert phrase in case_text
    assert not case.find(id='innovationStoryChart')
    assert not case.select('script[src$="/innovation-case.js"]')
    for alias in ('why-red.html','red/why-red.html'):
        assert str(pages[alias]) == str(case)
    assert (ROOT/'templates/etfs/meri/blog/quants-who-read.html').exists()
    for route,page in pages.items():
        assert not any(route.startswith((f'etfs/{fid}/',f'research/{fid}/')) for fid in ('dam1','azoc','mpd','meri'))
        text=page.get_text(' ',strip=True)
        assert not any(ticker in text for ticker in ('DAM1','AZOC','MPD','MERI','DMVP','DSCB','DSHR','DCRR'))


def test_research_disclaimer_survives_inline_script_removal(pages):
    page = pages['research/index.html']
    dialog = page.select_one('dialog#disclaimerOverlay')
    assert dialog and dialog.has_attr('open')
    assert dialog.find(id=dialog['aria-labelledby'])
    agree = dialog.select_one('[data-research-agree]')
    assert agree['type'] == 'submit' and agree['value'] == 'agree'
    assert agree.find_parent('form')['method'] == 'dialog'
    assert dialog.select_one('a[data-research-cancel]')['href'] == '/'
    assert not dialog.select('[onclick]')
    assert page.select_one('script[src="/assets/research-disclaimer.js"][defer]')
    assert page.select_one('link[href="/assets/research-disclaimer.css"]')


def test_deck_visuals_follow_the_investment_case_journey(pages):
    home=pages['index.html']
    case=pages['etfs/redi/why-red.html']
    asset='/assets/investment-case/'
    process_sources={
        asset+'corporate-metabolism.png',
        asset+'endogenous-growth.png',
        asset+'portfolio-weighting.png',
    }
    for page in (home,case):
        process=page.find(attrs={'aria-label':'Explore the investment process'})
        buttons=process.find_all('button',attrs={'aria-controls':True})
        assert len(buttons)==3
        sources=[]
        for button in buttons:
            panel=page.find(id=button['aria-controls'])
            assert panel['aria-labelledby']==button['id']
            images=panel.find_all('img')
            assert len(images)==1
            sources.append(images[0]['src'])
        assert set(sources)==process_sources

    assert home.find(id='innovation').find('img',src=asset+'redi-business-card-chart-labeled.svg')
    assert not home.find(id='etfs').find('img',src=asset+'portfolio-to-redi-sticker.png')
    sticker = home.find(id='contact').find('img',src=asset+'portfolio-to-redi-sticker.png')
    assert sticker and not sticker.find_parent('a')
    for route in ('section-351.html','351-exchanges.html'):
        sticker = pages[route].find('img',src=asset+'portfolio-to-redi-sticker.png')
        assert sticker and not sticker.find_parent('a')
    for page in (home,case):
        # Buttons contain number/label spans; locate their controlled panel.
        ability=next(button for button in page.select('[aria-label="Explore the investment process"] button') if 'Innovation ability' in button.get_text())
        panel=page.find(id=ability['aria-controls'])
        assert 'Economic, Theoretical, & Factor Justifications' in panel.get_text()
        assert not page.find('img',src=asset+'innovation-ability.png')
    assert case.find('img',src=asset+'endogenous-growth.png')
    chart_tabs=case.find(attrs={'aria-label':'Explore research charts'})
    buttons=chart_tabs.find_all('button',attrs={'aria-controls':True})
    assert len(buttons)==4
    chart_sources=set()
    for button in buttons:
        panel=case.find(id=button['aria-controls'])
        assert panel['aria-labelledby']==button['id']
        images=panel.find_all('img')
        assert len(images)==1
        chart_sources.add(images[0]['src'])
    assert chart_sources=={
        asset+'innovation-research.png',
        asset+'factor-comparison.png',
        asset+'selection-breadth.png',
        asset+'annual-comparison.png',
    }
