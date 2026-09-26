"""Build Hetzerk's original Section 351 educational guide.

Install requirements-guides.txt and run from the repository root. The editable
content and layout live here; no text or graphics are copied from the
third-party background paper. The guide cites governing primary sources.
"""
from pathlib import Path
from io import BytesIO
import shutil

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output/pdf/hetzerk-section-351-guide.pdf'
PUBLIC = ROOT / 'assets/guides/section-351-contributions.pdf'
INK, PAPER, RED = map(HexColor, ('#171617', '#f3eee5', '#8b0000'))
MUTED, RULE, LIGHT = map(HexColor, ('#615851', '#d7cdc1', '#c88e86'))
W, H, M = 612, 792, 48
WIDTH = W - 2 * M

FONTS = {'Inter': 'a699af1dea30.ttf', 'InterBold': '87e867b52640.ttf',
         'Playfair': '5ae86d38cfa3.ttf'}
for name, filename in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, ROOT / 'assets/fonts' / filename))
pdfmetrics.registerFontFamily('Inter', normal='Inter', bold='InterBold', italic='Inter', boldItalic='InterBold')

SOURCES = {
    1: ('26 USC 351(a), (b), (e)', 'https://www.law.cornell.edu/uscode/text/26/351'),
    2: ('26 CFR 1.351-1(c)(5)-(6)', 'https://www.ecfr.gov/current/title-26/section-1.351-1'),
    3: ('26 USC 368(a)(2)(F), (c)', 'https://www.law.cornell.edu/uscode/text/26/368'),
    4: ('26 USC 358, 362 and 1223', 'https://www.law.cornell.edu/uscode/text/26/358'),
    5: ('26 USC 852(b)(6)', 'https://www.law.cornell.edu/uscode/text/26/852'),
    6: ('IRS Publication 550', 'https://www.irs.gov/publications/p550'),
    7: ('26 USC 851(b)(3)', 'https://www.law.cornell.edu/uscode/text/26/851'),
    8: ('26 CFR 1.351-3', 'https://www.ecfr.gov/current/title-26/section-1.351-3'),
}


class Guide:
    def __init__(self):
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        self.c = canvas.Canvas(str(OUTPUT), pagesize=(W, H))
        self.c.setTitle('ETF Taxation and Section 351 Contributions | Hetzerk Asset Management')
        self.c.setAuthor('Hetzerk Asset Management')
        self.c.setSubject('An educational guide to portfolio contributions, diversification and tax deferral')
        self.page = 0
        self.y = 0

    def p(self, text, *, size=10.4, leading=15.4, color=None, gap=10, x=M, width=WIDTH, font='Inter'):
        style = ParagraphStyle('body', fontName=font, fontSize=size, leading=leading,
                               textColor=color or (PAPER if self.dark else INK))
        item = Paragraph(text, style)
        _, height = item.wrap(width, H)
        if self.y - height < 68:
            raise ValueError(f'Page {self.page} overflow at y={self.y:.1f}, height={height:.1f}: {text[:70]}')
        item.drawOn(self.c, x, self.y - height)
        self.y -= height + gap

    def rule(self, gap=18):
        self.c.setStrokeColor(HexColor('#463a3c') if self.dark else RULE)
        self.c.setLineWidth(.6)
        self.c.line(M, self.y, W-M, self.y)
        self.y -= gap

    def start(self, label, title, *, dark=False):
        if self.page:
            self.c.showPage()
        self.page += 1
        self.dark = dark
        self.c.setFillColor(INK if dark else PAPER)
        self.c.rect(0, 0, W, H, fill=1, stroke=0)
        svg = (ROOT/'assets/hetzerk-mark-still.svg').read_text().replace('<path ', f'<path fill="{"#c88e86" if dark else "#8b0000"}" ')
        mark = svg2rlg(BytesIO(svg.encode()))
        mark.scale(38/480, 38/480)
        renderPDF.draw(mark, self.c, M-10, H-61)
        self.c.setFillColor(PAPER if dark else INK)
        self.c.setFont('Inter', 10)
        self.c.drawString(M+26, H-47, 'Hetzerk Asset Management')
        self.c.setFont('Inter', 8)
        self.c.setFillColor(LIGHT if dark else MUTED)
        self.c.drawRightString(W-M, H-47, 'RESEARCH & INVESTOR EDUCATION')
        self.y = H-92
        self.p(label.upper(), size=8.5, leading=12, color=LIGHT if dark else RED, gap=13, font='InterBold')
        self.p(title, size=32, leading=37, font='Playfair', gap=22)
        self.c.setStrokeColor(HexColor('#463a3c') if dark else RULE)
        self.c.line(M, 55, W-M, 55)
        self.c.setFillColor(LIGHT if dark else MUTED)
        self.c.setFont('Inter', 7.3)
        self.c.drawString(M, 39, 'SECTION 351 CONTRIBUTIONS  /  SEPTEMBER 26, 2026')
        self.c.drawRightString(W-M, 39, f'{self.page:02} / 07')

    def heading(self, title):
        self.p(title, size=14, leading=18, font='InterBold', gap=8)

    def sources(self, numbers):
        self.y -= 3
        self.rule(12)
        refs = ' &nbsp; / &nbsp; '.join(f'<a href="{SOURCES[n][1]}" color="#{(LIGHT if self.dark else RED).hexval()[2:]}">[{n}] {SOURCES[n][0]}</a>' for n in numbers)
        self.p(refs, size=7.5, leading=11, color=LIGHT if self.dark else MUTED, gap=0)

    def table(self, headings, rows, widths):
        sty = ParagraphStyle('cell', fontName='Inter', fontSize=9, leading=13, textColor=INK)
        head = ParagraphStyle('head', parent=sty, fontName='InterBold', textColor=PAPER)
        data = [[Paragraph(v, head) for v in headings]]
        data += [[Paragraph(v, sty) for v in row] for row in rows]
        tab = Table(data, colWidths=widths, hAlign='LEFT')
        tab.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), INK),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 11), ('RIGHTPADDING', (0,0), (-1,-1), 11),
            ('TOPPADDING', (0,0), (-1,-1), 9), ('BOTTOMPADDING', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#faf6ef'), HexColor('#e9e0d3')]),
            ('LINEBELOW', (0,1), (-1,-1), .5, RULE),
        ]))
        _, height = tab.wrap(WIDTH, H)
        if self.y-height < 76:
            raise ValueError(f'Table overflow on page {self.page}')
        tab.drawOn(self.c, M, self.y-height)
        self.y -= height+14


def build():
    g = Guide()
    g.start('A guide for prospective contributors', 'ETF taxation &amp;<br/>Section 351 contributions', dark=True)
    g.p('Start with the portfolio<br/>you already own.', size=26, leading=32, color=LIGHT, font='Playfair', gap=22)
    g.p('A qualifying contribution can move an eligible portfolio into ETF shares while deferring recognition of embedded gains. The result depends on the assets, their tax owners and the complete transaction.', size=12, leading=18, gap=25)
    g.rule()
    for label, text in [
        ('01 / Before the exchange', 'Test each proposed contribution. Diversification is not measured only after everyone\'s assets reach the ETF.'),
        ('02 / At the exchange', 'Confirm the ownership, control, consideration and transaction plan. Preserve the records supporting basis and holding periods.'),
        ('03 / After the exchange', 'ETF distributions and later sales can still create tax liabilities. Deferral does not erase the original gain.'),
    ]:
        g.p(label, size=10, leading=14, color=LIGHT, font='InterBold', gap=5)
        g.p(text, gap=17)
    g.p('Prepared for discussion of the Hetzerk Innovation Factor ETF (REDI), an equity-only strategy. This guide describes a potential contribution process; it does not establish an available exchange, an accepted asset list or a launch date.', size=9, leading=13, color=HexColor('#c4b7ad'))
    g.p('General U.S. federal tax information, not individual tax, legal or investment advice. Consult your tax adviser. This is not a prospectus or an offer to invest.', size=8.5, leading=12, color=HexColor('#c4b7ad'), gap=0)

    g.start('01 / The contributed portfolio', 'Two limits. Each contributor.')
    g.p('For the already-diversified-portfolio route commonly used in multi-investor ETF formations, each proper tax transferor must contribute a portfolio that satisfies both concentration tests. Pooling unrelated contributors does not cure a failed test. [2, 3]')
    y = g.y
    for x, number, label in [(M, '25%', 'Maximum in one issuer'), (M+270, '50%', 'Maximum in any five or fewer issuers')]:
        g.y = y
        g.p(number, size=49, leading=54, color=RED, font='Playfair', x=x, width=246, gap=9)
        g.p(label, size=10, leading=15, font='InterBold', x=x, width=246, gap=12)
    g.y -= 7
    g.rule()
    g.heading('Calculate the right portfolio value')
    g.p('Use fair market value and the prescribed test denominator, not historical cost. Aggregate securities of the same issuer. Members of a controlled group under Section 1563(a) count as one issuer. [3]')
    g.heading('Cash is not a concentration repair')
    g.p('Cash and cash items, including receivables, are excluded from the denominator. Assets acquired for the purpose of meeting the tests are also excluded under the applicable rules. A cash top-up therefore does not dilute an oversized stock position for these tests. [2, 3]')
    g.heading('Look through qualifying funds')
    g.p('Interests in regulated investment companies, REITs and other qualifying investment companies generally require proportionate underlying-asset treatment. Combine overlapping direct and indirect issuer exposures. A holding called an ETF is not an automatic pass. [3]')
    g.heading('Government securities have a specific rule')
    g.p('Government securities ordinarily enter the denominator but not issuer numerators, unless acquired to meet the tests. This can change the percentages. It does not mean government securities are acceptable assets for REDI\'s equity strategy. [2]')
    g.p('These limits address a particular investment-company exception. They are not the ETF\'s separate ongoing RIC diversification tests, and they do not establish complete transaction eligibility. [1, 7]', size=9, leading=13)
    g.sources([2,3,7])

    g.start('02 / Original worked examples', 'Diversification in numbers.')
    g.p('Each scenario is a separate $1,000,000 portfolio of ordinary stocks from unrelated issuers, with no cash, borrowing, fund look-through or controlled-group adjustments. The arithmetic is illustrative, not a recommended portfolio or tax opinion.')
    g.table(['Proposed contribution', 'Largest issuer', 'Largest five', 'Numerical result'], [
        ['12 equally weighted issuers', '8.33%', '41.67%', 'Meets both limits'],
        ['One issuer at 30%; ten others at 7% each', '30%', '58%', 'Fails both limits'],
        ['20%, 10%, 8%, 7%, 6%; ten others at 4.9% each', '20%', '51%', 'Fails the 50% limit'],
        ['10 equally weighted issuers', '10%', '50%', 'Meets both;<br/>no buffer at 50%'],
    ], [230,82,83,121])
    g.heading('Why a cash top-up does not solve it')
    g.p('In the second example, adding $200,000 in cash leaves the test denominator at $1,000,000. The $300,000 issuer remains 30% for the test, even though the full account balance becomes $1,200,000. [2, 3]')
    g.heading('Why counting holdings can mislead')
    g.p('Two share classes can represent the same issuer. A stock held directly and through a qualifying fund can create overlapping exposure. Conversely, a qualifying fund may represent many underlying issuers. Review economic issuer exposure after the required adjustments. [3]')
    g.heading('Leave room for market movement')
    g.p('The statutory wording permits exactly 25% and exactly 50%. A portfolio sitting at a limit can cross it as prices move. Revalue the approved basket before closing and use the transaction\'s documented review process. Do not trade or borrow solely to manufacture qualification.')
    g.p('The holding count alone does not establish eligibility or fund acceptance.', size=9, leading=13)
    g.sources([2,3])

    g.start('03 / The complete transaction', 'The gain carries forward.')
    g.heading('Property, stock and collective control')
    g.p('Section 351(a) generally covers qualifying property exchanged solely for stock when the transferors collectively control the corporation immediately afterward. Control requires at least 80% of combined voting power and at least 80% of the shares of all other stock classes. Each investor need not independently own 80%. [1, 3]')
    g.p('The investment-company exception must also be addressed. Cash or other property received can trigger gain recognition. Liabilities, built-in losses, planned dispositions and entity-specific rules require separate analysis. A written closing plan should identify the participants, assets, consideration and timing. [1, 2, 4]')
    g.heading('A simplified basis example')
    g.table(['Stage', 'Market value / proceeds', 'Adjusted tax basis'], [
        ['Eligible stocks before contribution', '$1,000,000', '$400,000'],
        ['ETF shares received in a qualifying stock-only exchange', '$1,000,000', '$400,000'],
        ['Later sale of all ETF shares', '$1,100,000', '$400,000'],
    ], [255,140,121])
    g.p('Assuming full qualification, no boot, liabilities, basis adjustments or intervening events, the exchange recognizes no gain. The later sale produces a $700,000 gain before transaction costs. The $600,000 embedded gain at contribution was deferred, not forgiven. These dollar amounts are hypothetical. [1, 4]')
    g.heading('Preserve tax lots and holding periods')
    g.p('Investor and fund basis generally carry over, subject to statutory adjustments. Holding periods carry where requirements are met. Preserve lot-level acquisition dates and basis, and reconcile their allocation to ETF shares with the custodian and tax adviser. [4]')
    g.p('A Section 351 launch transaction does not create a standing right to contribute stocks later. Ordinary exchange purchases, AP creations and investor sales must be evaluated under their own facts and tax rules.', size=9, leading=13)
    g.sources([1,2,3,4])

    g.start('04 / Preparing a proposed contribution', 'A review process for REDI.')
    g.p('REDI\'s intended investment exposure is equities. A tax-eligible asset is not automatically an acceptable portfolio holding. Portfolio fit, transferability, valuation, custody and the final fund documents require review before any contribution is accepted.')
    for label, body in [
        ('Identify the tax owner', 'Confirm the person or entity treated as the transferor. Multiple accounts, joint ownership, trusts, partnerships, corporate owners, retirement accounts and non-U.S. persons need their own analysis. Do not combine accounts just because one adviser manages them.'),
        ('Provide the proposed lots', 'Record account ownership, security identifiers, issuer, quantity, current value, acquisition date, adjusted basis and any restrictions or liabilities. Supply underlying holdings where look-through is required. Keep sensitive records out of a general website interest form.'),
        ('Review the basket and transaction', 'Check concentration limits and all other qualification requirements, then assess the securities against REDI\'s strategy and operational capabilities. Restricted, illiquid or hard-to-value positions need specific attention. Interest registration is not acceptance.'),
        ('Agree the closing instructions', 'Use the final legal and custody instructions for signatures, settlement, valuation, share allocation and any cash adjustments. Reconcile dividends, pending corporate actions and changes in ownership before transfer. Do not assume a universal timetable or an immediate-sale safe harbor.'),
        ('Reconcile after closing', 'Match securities delivered, ETF shares received, cash items and basis records to custodian statements. Retain transaction documents and determine which tax-return statements are required, including the rules for significant transferors. [8]'),
    ]:
        g.heading(label)
        g.p(body, gap=13)
    g.p('Any rebalancing before contribution can itself realize gains or create other tax consequences. Discuss alternatives with your adviser before selling or rearranging positions.', size=9, leading=13)
    g.sources([1,2,8])

    g.start('05 / After the contribution', 'The ETF wrapper has limits.')
    g.heading('Fund tax efficiency')
    g.p('An ETF taxed as a regulated investment company may deliver securities in kind when redeeming its shares. Section 852(b)(6) can prevent fund-level gain recognition on a qualifying redemption distribution. This may reduce the need for taxable portfolio sales, but it does not promise zero capital-gain distributions. Cash redemptions and portfolio activity can change the outcome. [5]')
    g.heading('Shareholder taxation')
    g.p('In a taxable account, dividends and capital-gain distributions may be taxable even when reinvested. Their character depends on the applicable rules and the fund\'s reporting. Selling ETF shares can realize a gain or loss. Tax rates depend on the investor\'s circumstances; state, local and non-U.S. consequences may differ. [6]')
    g.table(['Rule or event', 'What it addresses'], [
        ['Section 351 contribution tests', 'Whether a particular contribution transaction qualifies for nonrecognition.'],
        ['Ongoing RIC diversification', 'The fund\'s separate quarterly asset-diversification conditions. [7]'],
        ['Section 852(b)(6)', 'Fund-level treatment of qualifying in-kind redemption distributions.'],
        ['Investor distributions and sales', 'The shareholder\'s own taxable income, gains, losses and reporting.'],
    ], [205,311])
    g.heading('Investment suitability remains a separate decision')
    g.p('Contributing a portfolio changes what you own and how it is managed. Consider REDI\'s investment objective, risks, fees, trading costs, liquidity and the loss of direct control over individual holdings. A possible tax deferral should not substitute for that analysis.')
    g.p('Review current offering documents if and when available. This guide does not confirm fund registration, transaction availability, service-provider arrangements or acceptance of any asset. Ask your own tax and legal advisers to assess the complete facts.', size=9, leading=13)
    g.sources([5,6,7])

    g.start('Sources & scope', 'Read the rules behind the guide.')
    g.p('Prepared September 26, 2026. The primary sources below support this original educational discussion. Statutes, regulations, interpretations and personal circumstances can change the result. Consult current law and your advisers before acting.', size=10, leading=15, gap=18)
    descriptions = {
        1: 'General nonrecognition rule, other consideration and the investment-company exception.',
        2: 'Diversification, the already-diversified-portfolio route, government securities and planned transactions.',
        3: '25% / 50% limits, issuer grouping, look-through, exclusions and the definition of control.',
        4: 'Investor and fund basis; holding-period carryover. Also review Section 357 for liabilities.',
        5: 'Fund-level rule for qualifying redemption distributions.',
        6: 'Investor treatment of investment income, distributions, gains and losses.',
        7: 'Separate quarterly asset-diversification requirements for regulated investment companies.',
        8: 'Information and recordkeeping requirements for Section 351 transactions.',
    }
    for n, (name, url) in SOURCES.items():
        g.p(f'<a href="{url}" color="#8b0000"><b>[{n}] {name}</b></a><br/>{descriptions[n]}', size=9, leading=13, gap=12)
        if n == 4:
            g.p('<a href="https://www.law.cornell.edu/uscode/text/26/362" color="#8b0000">Section 362</a> &nbsp; / &nbsp; <a href="https://www.law.cornell.edu/uscode/text/26/1223" color="#8b0000">Section 1223</a> &nbsp; / &nbsp; <a href="https://www.law.cornell.edu/uscode/text/26/357" color="#8b0000">Section 357</a>', size=8, leading=11, gap=12)
    g.rule(14)
    background = 'https://etfarchitect.com/wp-content/uploads/compliance/etfarchitect/Intro%20to%20ETF%20Taxation%20and%20351%20Conversions.pdf'
    g.p(f'<b>Further reading</b><br/><a href="{background}" color="#8b0000">ETF Architect, Introduction to ETF Taxation and 351 Conversions</a>. This third-party background paper is not a statement of Hetzerk\'s policies or an endorsement of Hetzerk. Provider-specific procedures and acceptance rules should not be treated as universal tax requirements.', size=8.5, leading=12)
    g.p('Hetzerk\'s text, organization and worked examples were developed for this guide. No affiliation with the third-party publisher is implied.', size=8, leading=11, color=MUTED, gap=0)
    g.c.save()
    PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT, PUBLIC)
    print(f'Created {OUTPUT} and published asset {PUBLIC}')


if __name__ == '__main__':
    build()
