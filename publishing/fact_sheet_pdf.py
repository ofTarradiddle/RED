"""Print-ready REDI fact sheet generated from the same content as its web page."""
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from svglib.svglib import svg2rlg

from publishing.fact_sheet import fact_sheet_data

ROOT = Path(__file__).resolve().parents[1]
PAGE_W, PAGE_H, MARGIN = 612, 792, 44
CONTENT_W = PAGE_W - 2 * MARGIN
INK, PAPER, RED = map(HexColor, ('#171617', '#f3eee5', '#8b0000'))
MUTED, RULE, PALE_RED = map(HexColor, ('#655e58', '#d8cfc4', '#d3aaa2'))
FONT, BOLD, DISPLAY = 'FactSheetInter', 'FactSheetInterBold', 'FactSheetPlayfair'


def _text(value):
    """Escape supplied text for ReportLab and use reliably printable dashes."""
    return escape(str(value).translate(str.maketrans({'\u2011': '-', '\u2013': '-', '\u2014': '-'})))


def _register_fonts():
    for name, filename in ((FONT, 'a699af1dea30.ttf'), (BOLD, '87e867b52640.ttf'),
                           (DISPLAY, '5ae86d38cfa3.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, ROOT / 'assets/fonts' / filename))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=BOLD, italic=FONT, boldItalic=BOLD)


class _FactSheet:
    def __init__(self, data, output_path, site_url):
        self.data = data
        self.base_url = (site_url or 'https://oftarradiddle.github.io/RED').rstrip('/')
        self.pdf = canvas.Canvas(str(output_path), pagesize=(PAGE_W, PAGE_H), invariant=1)
        self.pdf.setTitle(f"{data['name']} ({data['ticker']}) | Fund Fact Sheet")
        self.pdf.setAuthor('Hetzerk Asset Management')
        self.pdf.setSubject('Investment approach, proposed fund terms and dated portfolio data')
        self.page = 0

    def paragraph(self, text, x, top, width=CONTENT_W, *, size=9.4, leading=13.0,
                  font=FONT, color=INK, markup=False, min_bottom=64):
        paragraph = Paragraph(text if markup else _text(text), ParagraphStyle(
            'fact-sheet', fontName=font, fontSize=size, leading=leading, textColor=color))
        _, height = paragraph.wrap(width, PAGE_H)
        bottom = top - height
        if bottom < min_bottom:
            raise ValueError(f'Fact sheet page {self.page} overflows at {text[:75]!r}')
        paragraph.drawOn(self.pdf, x, bottom)
        return bottom

    def rule(self, y, *, x=MARGIN, width=CONTENT_W, color=RULE):
        self.pdf.setStrokeColor(color)
        self.pdf.setLineWidth(.55)
        self.pdf.line(x, y, x + width, y)

    def label(self, text, x, y, width=CONTENT_W, color=RED):
        return self.paragraph(text.upper(), x, y, width, size=7.8, leading=11,
                              font=BOLD, color=color)

    def link(self, label, path, x, y, width, *, size=8):
        return self.paragraph(
            f'<a href="{escape(self.base_url + path, quote=True)}" color="#8b0000">'
            f'{_text(label)}</a>', x, y, width, size=size, leading=12, font=BOLD, markup=True)

    def start(self, *, dark=False):
        if self.page:
            self.pdf.showPage()
        self.page += 1
        self.pdf.setFillColor(PAPER)
        self.pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        if dark:
            self.pdf.setFillColor(INK)
            self.pdf.rect(0, 596, PAGE_W, PAGE_H - 596, fill=1, stroke=0)
        if self.data['is_demo']:
            self.pdf.setFillColor(RED)
            self.pdf.rect(0, 755, PAGE_W, 37, fill=1, stroke=0)
            banner = self.data['demo_banner']
            self.paragraph(banner, MARGIN, 783, CONTENT_W, size=8.1, leading=11,
                           color=PAPER, min_bottom=750)
        svg = (ROOT / 'assets/hetzerk-mark-still.svg').read_text().replace(
            '<path ', f'<path fill="{"#d3aaa2" if dark else "#8b0000"}" ')
        mark = svg2rlg(BytesIO(svg.encode()))
        mark.scale(36 / 480, 36 / 480)
        renderPDF.draw(mark, self.pdf, MARGIN - 10, 715)
        self.paragraph('Hetzerk Asset Management', MARGIN + 25, 739, 300,
                       size=9.4, leading=12, color=PAPER if dark else INK)
        self.paragraph(f"{self.data['ticker']} / FACT SHEET", 441, 738, 127,
                       size=7.6, leading=11, font=BOLD, color=PALE_RED if dark else RED)
        self.rule(55)
        self.paragraph(self.data['name'].upper(), MARGIN, 44, 370,
                       size=7.1, leading=10, color=MUTED, min_bottom=28)
        self.paragraph(f'{self.page:02} / 02', PAGE_W - MARGIN - 35, 44, 35,
                       size=7.1, leading=10, color=MUTED, min_bottom=28)

    def strategy_page(self):
        d = self.data
        self.start(dark=True)
        title = _text(d['name']).replace(' Innovation ', '<br/>Innovation ', 1)
        self.paragraph(title, MARGIN, 700, 402, size=30, leading=35,
                       font=DISPLAY, color=PAPER, markup=True)
        self.paragraph(d['deck'], MARGIN, 622, 414, size=10, leading=14, color=PALE_RED)
        self.rule(698, x=470, width=98, color=HexColor('#5b3b3c'))
        self.label('Annual expense ratio', 472, 685, 97, color=PALE_RED)
        self.paragraph(d['fee'], 470, 654, 100, size=26, leading=32, font=DISPLAY, color=PAPER)
        self.paragraph(f"{d['bps']} basis points", 472, 614, 97, size=7.7, leading=10, color=PALE_RED)

        self.label('Investment objective', MARGIN, 576)
        objective_bottom = self.paragraph(d['objective'], MARGIN, 557, size=10, leading=14)
        key_top = objective_bottom - 16
        self.rule(key_top)
        facts = d['key_facts']
        for i, (label, value) in enumerate(facts):
            x = MARGIN + i * 134
            self.label(label, x, key_top - 12, 122, color=MUTED)
            self.paragraph(value, x, key_top - 27, 122, size=9, leading=12, font=BOLD)
        process_top = key_top - 63
        self.label('The investment process', MARGIN, process_top)
        self.rule(process_top - 19)
        bottoms = []
        for i, (step, title, question, copy) in enumerate(d['process']):
            x = MARGIN + i * 181
            self.label(step, x, process_top - 31, 162)
            self.paragraph(title, x, process_top - 48, 162, size=11.2, leading=15, font=BOLD)
            self.paragraph(question, x, process_top - 69, 162, size=8.3, leading=11, color=RED)
            bottoms.append(self.paragraph(copy, x, process_top - 88, 162, size=9.1, leading=12.3))
        theory_top = min(bottoms) - 19
        self.rule(theory_top)
        self.label('The economic intuition', MARGIN, theory_top - 13)
        theory_bottom = self.paragraph(d['thesis'], MARGIN, theory_top - 32,
                                      size=9.2, leading=12.5)
        bottom_top = theory_bottom - 20
        for x, label, content in ((MARGIN, 'Factors across industries', d['factor']),
                                   (MARGIN + 272, 'Focused by design', d['conviction'])):
            self.label(label, x, bottom_top, 252)
            self.paragraph(content, x, bottom_top - 19, 252, size=9.0, leading=12.2)

    def holdings_table(self, top, width):
        d = self.data
        cell = ParagraphStyle('holding', fontName=FONT, fontSize=8.7, leading=11, textColor=INK)
        heading = ParagraphStyle('holding-heading', parent=cell, fontName=BOLD,
                                 fontSize=7.4, textColor=PAPER)
        ticker = ParagraphStyle('ticker', parent=cell, fontName=BOLD)
        right = ParagraphStyle('weight', parent=cell, alignment=2)
        rows = [[Paragraph(label, heading) for label in ('TICKER', 'COMPANY', 'WEIGHT')]]
        for holding in d['holdings']:
            rows.append([Paragraph(_text(holding['ticker']), ticker),
                         Paragraph(_text(holding['name']), cell),
                         Paragraph(f"{holding['weight']:.2%}", right)])
        table = Table(rows, colWidths=[55, width - 106, 51])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), INK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#faf7f1'), PAPER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 1), (-1, -1), .35, RULE),
        ]))
        _, height = table.wrap(width, PAGE_H)
        if top - height < 240:
            raise ValueError('Fact sheet top holdings exceed the reserved table space')
        table.drawOn(self.pdf, MARGIN, top - height)
        return top - height

    def snapshot_page(self):
        d = self.data
        self.start()
        self.paragraph('Portfolio snapshot', MARGIN, 704, size=31, leading=38, font=DISPLAY)
        self.paragraph(f"Valuation as of {d['as_of']}", MARGIN, 657,
                       size=8.5, leading=12, color=MUTED)
        metrics = (('NAV', d['nav']), ('Market Price', d['market_price']),
                   ('Net assets', d['net_assets']), ('Cash allocation', d['cash_weight']))
        self.rule(632)
        for i, (label, value) in enumerate(metrics):
            x = MARGIN + i * 134
            self.label(label, x, 619, 122, color=MUTED)
            self.paragraph(value, x, 600, 122, size=16, leading=21, font=DISPLAY)
        self.rule(568)
        left_width = 332
        right_x, right_width = MARGIN + 356, 168
        self.paragraph('Top 10 holdings', MARGIN, 549, left_width,
                       size=14, leading=19, font=DISPLAY)
        self.paragraph(f"Holdings as of {d['holdings_as_of']}", MARGIN, 524,
                       left_width, size=8, leading=11, color=MUTED)
        table_bottom = self.holdings_table(504, left_width)
        self.paragraph('Weights are percentages of portfolio net assets. Holdings may change.',
                       MARGIN, table_bottom - 9, left_width, size=7.1, leading=10, color=MUTED)

        self.label('Fund structure', right_x, 549, right_width)
        term_top = 527
        for label, value in d['terms']:
            self.paragraph(label, right_x, term_top, right_width, size=8, leading=11,
                           font=BOLD, color=MUTED)
            term_bottom = self.paragraph(value, right_x, term_top - 18, right_width,
                                         size=9.5, leading=13)
            self.rule(term_bottom - 11, x=right_x, width=right_width)
            term_top = term_bottom - 24
        note_bottom = self.paragraph(d['term_note'], right_x, term_top,
                                    right_width, size=7.7, leading=10.6, color=MUTED)
        self.link('Fund overview', '/etfs/redi/', right_x, note_bottom - 16, right_width)
        self.link('Performance', '/etfs/redi/#performance', right_x, note_bottom - 32, right_width)
        self.link('All holdings', '/etfs/redi/holdings.html', right_x, note_bottom - 48, right_width)
        self.link('Documents & filings', '/documents/', right_x, note_bottom - 64, right_width)

        allocation_top = min(table_bottom - 39, note_bottom - 84)
        self.rule(allocation_top)
        self.label(f"Current equity positions: {d['equity_count']}", MARGIN, allocation_top - 13, 250)
        self.paragraph(f"Benchmark: {d['benchmark']}", MARGIN + 260, allocation_top - 13, 264,
                       size=7.6, leading=11, font=BOLD, color=MUTED)
        allocation_bottom = self.paragraph(d['allocation_note'], MARGIN, allocation_top - 30,
                                           size=8.4, leading=11.5, color=MUTED)
        risk_top = allocation_bottom - 16
        self.label('Important information', MARGIN, risk_top)
        self.paragraph(d['risk'], MARGIN, risk_top - 18, size=8.2, leading=11.3)


def render_fact_sheet_pdf(fund, output_path, *, site_url=None):
    """Write a two-page fact sheet with the current snapshot and return its path.

    ``site_url`` is the public site root including a repository prefix, where
    applicable. The printable sheet links to live data rather than freezing a
    separately maintained performance table.
    """
    _register_fonts()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet = _FactSheet(fact_sheet_data(fund), output_path, site_url)
    sheet.strategy_page()
    sheet.snapshot_page()
    sheet.pdf.save()
    return output_path
