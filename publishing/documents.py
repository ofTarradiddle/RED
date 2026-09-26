"""Fund materials and clearly identified official filing references."""
from urllib.parse import parse_qs, urlsplit
from publishing.site import esc
from publishing.fact_sheet import fact_sheet_body

EDGAR = 'https://www.sec.gov/edgar/search/'
FUND_SEARCH = 'https://www.sec.gov/search-filings/mutual-funds-search'
N1A = 'https://www.sec.gov/files/form-n-1a.pdf'
NCSR = 'https://www.sec.gov/files/formn-csr.pdf'
RULE497 = 'https://www.ecfr.gov/current/title-17/chapter-II/part-230/subject-group-ECFR503bf91e47b67cd/section-230.497'
CATALOG = (
    ('prospectus', 'Statutory prospectus', 'N-1A · Part A / Rule 497', N1A),
    ('summary_prospectus', 'Summary prospectus', '497K · Rule 497(k)', RULE497),
    ('sai', 'Statement of additional information', 'N-1A · Part B', N1A),
    ('supplements', 'Prospectus & SAI supplements', 'Rule 497', RULE497),
    ('registration', 'Registration statement & amendments', 'N-1A · 485APOS · 485BPOS', N1A),
    ('annual_report', 'Annual shareholder report & financial statements', 'N-CSR', NCSR),
    ('semiannual_report', 'Semiannual shareholder report & financial statements', 'N-CSRS', NCSR),
    ('quarterly_holdings', 'First / third fiscal-quarter holdings', 'Schedule of investments · Rule 30e-1', 'https://www.ecfr.gov/current/title-17/chapter-II/part-270/section-270.30e-1'),
    ('n_port', 'Portfolio investment reports', 'N-PORT / NPORT-P', 'https://www.sec.gov/files/formn-port.pdf'),
    ('n_px', 'Proxy voting record', 'N-PX', 'https://www.sec.gov/files/formn-px.pdf'),
    ('n_cen', 'Annual regulatory census', 'N-CEN', 'https://www.sec.gov/files/formn-cen.pdf'),
    ('n_8a', 'Investment-company registration', 'N-8A · Trust level', 'https://www.sec.gov/files/formn-8a.pdf'),
    ('exchange_registration', 'Exchange registration', '8-A · As applicable', 'https://www.sec.gov/files/form8a.pdf'),
    ('registration_fee', 'Annual registration-fee notice', '24F-2 / 24F-2NT · Trust level', 'https://www.sec.gov/files/form24f-2.pdf'),
    ('xbrl', 'Structured financial data', 'Inline XBRL within applicable filings', EDGAR),
)


def document_cards(fund):
    provided = {doc['document_type']: doc for doc in fund['documents']}
    cards = []
    for key, title, form, url in CATALOG:
        doc = provided.get(key, {})
        supplied = ''
        if doc.get('url'):
            status = 'View draft document' if doc['status'] == 'draft' else 'View fund document'
            supplied = f'<a class="data-download" href="{esc(doc["url"])}">{status} ↗</a><p class="metric-note">{esc(doc.get("effective_date") or "Date not supplied")}</p>'
        cards.append(f'<article id="{key}" class="cambria-card p-6 document-card"><span class="document-form">{esc(form)}</span><h3>{esc(title)}</h3>{supplied}<div class="document-links"><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">SEC reference ↗</a><a href="{EDGAR}" target="_blank" rel="noopener noreferrer">Search EDGAR ↗</a></div></article>')
    return '<div class="document-grid">' + ''.join(cards) + '</div>'


def library_body(fund, compact=False):
    fid = fund['fund_id']
    heading = 'Documents & Filings' if compact else fund['name'] + ' — Documents & Filings'
    tag = 'h2' if compact else 'h1'
    return f'''<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 restored-data">
      <{tag} class="text-2xl font-bold mb-4">{esc(heading)}</{tag}>
      <p class="metric-note">Fund-specific filings have not been supplied. The SEC links below open official references and search tools.</p>
      <div class="document-materials">
        <a class="cambria-button" href="/etfs/{fid}/fact-sheet.html">Fund Fact Sheet</a>
        <a class="cambria-button-secondary" href="/etfs/{fid}/fact-sheet.pdf" type="application/pdf" download>Fact Sheet (PDF) ↓</a>
        <a class="cambria-button-secondary" href="/assets/guides/section-351-contributions.pdf" type="application/pdf">Section 351 Guide (PDF)</a>
        <a class="cambria-button-secondary" href="/etfs/{fid}/data/holdings.csv" download>Daily Holdings ↓</a>
        <a class="cambria-button-secondary" href="/etfs/{fid}/data/distributions.csv" download>Distributions ↓</a>
        <a class="cambria-button-secondary" href="{FUND_SEARCH}" target="_blank" rel="noopener noreferrer">SEC Fund Search ↗</a>
      </div>{document_cards(fund)}
      <p class="metric-note">Fund materials: <a href="/etfs/{fid}/why-red.html">Investment case</a> · <a href="/etfs/{fid}/#performance">Performance</a> · <a href="/etfs/{fid}/#trading">Premium / discount</a> · <a href="/form-crs.html">Adviser relationship summary</a></p>
    </div>'''


def quick_document_url(href, fid):
    key = parse_qs(urlsplit(href).query).get('doc', ['prospectus'])[0].replace('-', '_')
    if key == 'fact_sheet': return f'/etfs/{fid}/fact-sheet.html'
    if key == 'investment_case': return f'/etfs/{fid}/why-red.html'
    aliases = {'annual':'annual_report','semiannual':'semiannual_report','npx':'n_px','xbrl_filings':'xbrl'}
    key = aliases.get(key, key)
    valid = {x[0] for x in CATALOG}
    return '/documents/' + ('#'+key if key in valid else '')
