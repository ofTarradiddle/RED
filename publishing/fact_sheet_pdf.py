"""One-page printable REDI fact sheet, using the web page's shared content."""
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
        self.pdf.setSubject('Investment approach, intended terms and dated portfolio data')

    def paragraph(self, text, x, top, width=CONTENT_W, *, size=9.4, leading=13,
                  font=FONT, color=INK, markup=False, min_bottom=66):
        item = Paragraph(text if markup else _text(text), ParagraphStyle(
            'fact-sheet', fontName=font, fontSize=size, leading=leading, textColor=color))
        _, height = item.wrap(width, PAGE_H)
        bottom = top - height
        if bottom < min_bottom:
            raise ValueError(f'One-page fact sheet overflows at {text[:75]!r}')
        item.drawOn(self.pdf, x, bottom)
        return bottom

    def rule(self, y, *, x=MARGIN, width=CONTENT_W, color=RULE):
        self.pdf.setStrokeColor(color)
        self.pdf.setLineWidth(.55)
        self.pdf.line(x, y, x + width, y)

    def label(self, text, x, y, width=CONTENT_W, color=RED):
        return self.paragraph(text.upper(), x, y, width, size=7.6, leading=10.5,
                              font=BOLD, color=color)

    def header(self):
        d = self.data
        self.pdf.setFillColor(PAPER)
        self.pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        self.pdf.setFillColor(INK)
        self.pdf.rect(0, 635, PAGE_W, PAGE_H - 635, fill=1, stroke=0)
        if d['is_demo']:
            self.pdf.setFillColor(RED)
            self.pdf.rect(0, 755, PAGE_W, 37, fill=1, stroke=0)
            self.paragraph(d['demo_banner'], MARGIN, 783, size=8.1, leading=11,
                           color=PAPER, min_bottom=750)
        svg = (ROOT / 'assets/hetzerk-mark-still.svg').read_text().replace(
            '<path ', '<path fill="#d3aaa2" ')
        mark = svg2rlg(BytesIO(svg.encode()))
        mark.scale(32 / 480, 32 / 480)
        renderPDF.draw(mark, self.pdf, MARGIN - 9, 718)
        self.paragraph('Hetzerk Asset Management', MARGIN + 23, 739, 300,
                       size=9, leading=12, color=PAPER)
        self.paragraph(f"{d['ticker']} / FACT SHEET", 441, 738, 127,
                       size=7.6, leading=11, font=BOLD, color=PALE_RED)
        title = _text(d['name']).replace(' Innovation ', '<br/>Innovation ', 1)
        self.paragraph(title, MARGIN, 708, 400, size=27, leading=31,
                       font=DISPLAY, color=PAPER, markup=True)
        self.label('Annual expense ratio', 470, 706, 98, color=PALE_RED)
        self.paragraph(d['fee'], 470, 680, 98, size=25, leading=30,
                       font=DISPLAY, color=PAPER)
        self.paragraph(f"{d['bps']} basis points", 470, 650, 98,
                       size=7.6, leading=10, color=PALE_RED)

    def strategy(self):
        d = self.data
        self.label('Investment objective', MARGIN, 617)
        self.paragraph(d['objective'], MARGIN, 600, size=10.2, leading=14)
        for i, (label, value) in enumerate(d['key_facts']):
            x = MARGIN + i * 134
            self.label(label, x, 557, 122, color=MUTED)
            self.paragraph(value, x, 542, 122, size=9, leading=12, font=BOLD)
        self.rule(519)
        for i, (step, title, _question, copy) in enumerate(d['process']):
            x = MARGIN + i * 181
            self.paragraph(f'{step} / {title}', x, 506, 162,
                           size=9.8, leading=14, font=BOLD, color=RED)
            self.paragraph(copy, x, 484, 162, size=9.4, leading=12.8)
        self.rule(441)

    def holdings_table(self, top, width):
        cell = ParagraphStyle('holding', fontName=FONT, fontSize=8.7, leading=11, textColor=INK)
        heading = ParagraphStyle('holding-heading', parent=cell, fontName=BOLD,
                                 fontSize=7.3, textColor=PAPER)
        ticker = ParagraphStyle('ticker', parent=cell, fontName=BOLD)
        right = ParagraphStyle('weight', parent=cell, alignment=2)
        rows = [[Paragraph(label, heading) for label in ('TICKER', 'COMPANY', 'WEIGHT')]]
        for h in self.data['holdings']:
            rows.append([Paragraph(_text(h['ticker']), ticker),
                         Paragraph(_text(h['name']), cell), Paragraph(f"{h['weight']:.2%}", right)])
        table = Table(rows, colWidths=[55, width - 106, 51])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), INK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#faf7f1'), PAPER]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 1), (-1, -1), .35, RULE),
        ]))
        _, height = table.wrap(width, PAGE_H)
        if height > 139:
            raise ValueError('Fact sheet top five holdings exceed the reserved table space')
        table.drawOn(self.pdf, MARGIN, top - height)
        return top - height

    def snapshot(self):
        d = self.data
        self.paragraph('Portfolio snapshot', MARGIN, 426, 270, size=15, leading=20, font=DISPLAY)
        self.paragraph(f"Valuation as of {d['as_of']}", 414, 422, 154,
                       size=8, leading=11, color=MUTED)
        metrics = (('NAV', d['nav']), ('Market Price', d['market_price']),
                   ('Net assets', d['net_assets']), ('Cash allocation', d['cash_weight']))
        for i, (label, value) in enumerate(metrics):
            x = MARGIN + i * 134
            self.label(label, x, 394, 122, color=MUTED)
            self.paragraph(value, x, 378, 122, size=15, leading=20, font=DISPLAY)
        self.rule(347)
        left_w, right_x, right_w = 332, MARGIN + 356, 168
        self.paragraph('Top 5 holdings', MARGIN, 336, left_w, size=10, leading=14, font=BOLD)
        self.paragraph(f"Holdings as of {d['holdings_as_of']} · {d['equity_count']} equity positions",
                       MARGIN, 319, left_w, size=7.7, leading=10.5, color=MUTED)
        table_bottom = self.holdings_table(302, left_w)
        self.paragraph('% of net assets. Holdings may change.', MARGIN, table_bottom - 7,
                       left_w, size=7.1, leading=9.5, color=MUTED)
        allocation_bottom = self.paragraph(d['allocation_note'], MARGIN, table_bottom - 24,
                                           left_w, size=8, leading=10.5, color=MUTED)
        self.paragraph(f"Benchmark: {d['benchmark']}", MARGIN, allocation_bottom - 8,
                       left_w, size=7.7, leading=10.5, color=MUTED)
        self.label('Fund terms', right_x, 335, right_w)
        term_top = 315
        for label, value in d['terms']:
            self.paragraph(label, right_x, term_top, right_w,
                           size=7.8, leading=10.5, font=BOLD, color=MUTED)
            term_bottom = self.paragraph(value, right_x, term_top - 15, right_w,
                                         size=8.9, leading=12)
            term_top = term_bottom - 15
        self.paragraph(d['term_note'], right_x, term_top, right_w,
                       size=7.7, leading=10.5, color=MUTED)
        self.label('Important information', MARGIN, 114)
        self.paragraph(d['risk'], MARGIN, 98, size=8, leading=10.5)

    def footer(self):
        self.rule(56)
        links = (('Fund overview', '/etfs/redi/'), ('Performance', '/etfs/redi/#performance'),
                 ('All holdings', '/etfs/redi/holdings.html'),
                 ('The research', '/research/on-innovation-factor-investing.html'),
                 ('Documents & filings', '/documents/'))
        for i, (label, path) in enumerate(links):
            self.paragraph(f'<a href="{escape(self.base_url + path, quote=True)}" color="#8b0000">'
                           f'{_text(label)}</a>', MARGIN + i * 105, 45, 105,
                           size=7.6, leading=11, font=BOLD, markup=True, min_bottom=30)
        self.paragraph('HETZERK ASSET MANAGEMENT', MARGIN, 23, 370,
                       size=6.8, leading=9, color=MUTED, min_bottom=12)
        self.paragraph('01 / 01', PAGE_W - MARGIN - 35, 23, 35,
                       size=6.8, leading=9, color=MUTED, min_bottom=12)


def render_fact_sheet_pdf(fund, output_path, *, site_url=None):
    """Write a one-page LETTER fact sheet and return its path.

    ``site_url`` is the public site root, including the repository prefix.
    Longer research, performance and full holdings remain linked online.
    """
    _register_fonts()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet = _FactSheet(fact_sheet_data(fund), output_path, site_url)
    sheet.header()
    sheet.strategy()
    sheet.snapshot()
    sheet.footer()
    sheet.pdf.save()
    return output_path
