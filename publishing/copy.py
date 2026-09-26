"""Presentation copy; consolidate sample-data context in the persistent banner."""
import re
from bs4 import BeautifulSoup, Comment

REPLACEMENTS = {
    'Our Proposed ETF': 'Our ETF',
    'Demo review': 'Investor Information',
    'Demo review guide': 'Data Guide',
    'Privacy for this local demo': 'Privacy',
    'About this demonstration': 'Investment Risks',
    'Illustrative portfolios and performance. Proposed terms are subject to change. No fund registration or availability is represented. Investing involves risk, including loss of principal.': 'Investing involves risk, including loss of principal. Review the investment objective, risks, charges and expenses before investing.',
    'Local demo preview.': 'All rights reserved.',
    'Newsletter integration is not connected in this local demo.': 'Newsletter signup is not yet available.',
    'Legal entity, registration and contact records remain to be supplied for this demo.': 'Fund registration and service-provider details are pending.',
    'Proposed investment strategies from Hetzerk Asset Management. Registration and offering details remain unverified in this demo.': 'Systematic equity strategies from Hetzerk Asset Management.',
    'The demo start date is not an actual fund inception date.': '',
    'fees and portfolio values are demo inputs.': '',
    'Not actual fund performance.': '',
    'Prices, quantities and DEMO identifiers are synthetic.': '',
    'Illustrative NAV total returns. Hypothetical demo results, not an actual track record.': 'Total returns include reinvested distributions.',
    'Returns reinvest demo distributions on their ex-dates. NAV values reflect hypothetical fund expenses; investor brokerage costs and taxes are excluded. Periods over one year are annualized where labeled. These are not approved standardized advertising results. The benchmark is synthetic.': 'Returns include reinvested distributions on their ex-dates. Investor brokerage costs and taxes are excluded. Periods over one year are annualized where labeled.',
    'Illustrative amounts per share; no invented entitlement cutoff.': 'Amounts per share, by ex-date, record date and payable date.',
    'Fictional weekday observations, not a verified exchange calendar.': 'Closing market price divided by NAV, less one.',
    'Illustrative conceptual comparison from the original investment case. Fictional values; not a backtest, actual fund return or verified index history.': 'Conceptual comparison of investment approaches.',
    'Illustrative only.': '',
    'Illustrative; replace with your study.': '',
    'The figures herein are illustrative placeholders. Past performance is not indicative of future results.': 'Past performance does not guarantee future results.',
    'Illustrative and approximate.': 'Approximate category-level costs.',
    'Proposed / unverified': 'To be confirmed',
    'Fund Inception:': 'Data Start:',
    '(demo start)': '',
    'Since demo start': 'Since data start',
    'Demo benchmark': 'Benchmark',
    'Illustrative equity benchmark': 'Equity comparison series',
    'Illustrative holdings.': 'Portfolio holdings.',
    'Illustrative conceptual comparison, not actual performance': 'Conceptual comparison of investment approaches',
    'Demo total return history': 'Total return history',
    'Daily demo premium and discount history': 'Daily premium and discount history',
    'Illustrative Factor Importance': 'Factor Importance',
    ' (Illustrative)': '',
    ' (illustrative)': '',
    ' · demo': '',
    'illustrative total return': 'total return',
    'illustrative equity positions': 'equity positions',
    'Illustrative data as of': 'As of',
    'DEMO:': '',
    'Download the demo workbook': 'Download the workbook',
    'Data source: hetzerk-demo.xlsx.': 'Source: fund data workbook.',
    'No filed Form CRS has been supplied or verified for this demo.': 'No filed Form CRS has been supplied.',
    'The demo makes no statements about disciplinary history or registration.': '',
    'Stacked fees by category; illustrative, not a guarantee': 'Stacked fees by category; actual fees vary',
    'illustrative purposes only': 'research purposes only',
}


def clean_text(text):
    for old,new in sorted(REPLACEMENTS.items(),key=lambda pair:-len(pair[0])):
        text=text.replace(old,new)
    return text


def polish_pages(pages):
    cleaned={}
    for route,html in pages.items():
        page=BeautifulSoup(html,'html.parser')
        for node in list(page.find_all(string=True)):
            if isinstance(node,Comment) or node.parent.name in ('script','style') or node.find_parent(class_='demo-strip'):
                continue
            text=clean_text(str(node))
            if text!=str(node): node.replace_with(text)
        for tag in page.find_all(True):
            for attr in ('content','aria-label','title','alt'):
                if isinstance(tag.get(attr),str): tag[attr]=clean_text(tag[attr])
        for link in page.select('footer a[href="/review/"]'):
            link['href']='/documents/'; link.string='Documents & Filings'
        for link in list(page.select('a[href="#services"],a[href="/#services"]')):
            link.decompose()
        for link in page.select('a[href="#fees"],a[href="/#fees"]'):
            if link.get_text(strip=True)=='Fees':link.string='Fund Expenses'
        # This plain footer word is a local-server hook, never a public link.
        foot=page.find('footer')
        if foot:
            last=foot.select_one('.border-t')
            if last:
                word=page.new_tag('span',attrs={'data-perspective-word':''})
                word.string='Perspective'
                last.append(' · ');last.append(word)
        cleaned[route]=str(page)
    return cleaned
