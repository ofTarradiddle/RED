"""Add native SVG chart labels while retaining the original backtest artwork.

The embedded PNGs and plotted paths are unmodified. Masks hide only old text;
the new labels are selectable SVG text and also appear in the enlarged viewer.
Run from any directory with Python's standard library.
"""
from base64 import b64encode
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / 'assets/investment-case'


def text(x, y, value, *, size=29, color='#655f5d', weight=600):
    return (f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}">{escape(value)}</text>')


def build(source, destination, width, height, background, masks, labels):
    artwork = b64encode((ASSETS / source).read_bytes()).decode('ascii')
    mask = ''.join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="black"/>'
                   for x, y, w, h in masks)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">REDI backtests - Log returns</title>
<desc id="description">Cumulative growth of one dollar on a logarithmic scale. Innovation Leader, Laggard, Market Backtest, Market Equal Weight and Non-R&amp;D Payers. Hypothetical research, not actual ETF performance. Original plotted paths are unchanged.</desc>
<defs><mask id="source-label-mask" maskUnits="userSpaceOnUse"><rect width="{width}" height="{height}" fill="white"/>{mask}</mask></defs>
<rect width="{width}" height="{height}" fill="{background}"/>
<image width="{width}" height="{height}" href="data:image/png;base64,{artwork}" mask="url(#source-label-mask)"/>
<g>{''.join(labels)}</g>
</svg>'''
    (ASSETS / destination).write_text(svg)


def main():
    light_labels = [
        text(109, 56, 'LOG RETURNS · BACKTEST', size=29, color='#544d4b'),
        text(109, 94, 'Growth of $1 · logarithmic scale · Apr 2003–Aug 2026', size=25, weight=400),
        text(1690, 73, 'END LABELS: CAGR', size=26, color='#544d4b'),
    ]
    for y, name, cagr, color in (
        (207, 'Innovation Leader', '18.05% CAGR', '#af071b'),
        (482, 'Laggard', '12.53% CAGR', '#ad780e'),
        (639, 'Market Backtest', '11.75% CAGR', '#34485c'),
        (777, 'Market Equal Weight', '11.63% CAGR', '#2e7189'),
        (929, 'Non-R&D Payers', '10.82% CAGR', '#707d8e'),
    ):
        light_labels.extend((text(1598, y, name, size=33, color=color),
                             text(1598, y + 46, cagr, size=43, color=color)))
    build('redi-business-card-chart.png', 'redi-business-card-chart-labeled.svg', 2048, 1170,
          '#f3eee5', [(100, 20, 1000, 95), (1645, 35, 403, 62), (1590, 151, 458, 840)], light_labels)

    dark_labels = [
        text(196, 41, 'LOG RETURNS · BACKTEST', size=31, color='#d1c4ba'),
        text(196, 81, 'Growth of $1 · logarithmic scale · Apr 2003–Aug 2026', size=25,
             color='#a99c92', weight=400),
    ]
    for y, name, color in (
        (220, 'Innovation Leader', '#da182b'),
        (366, 'Laggard', '#e4a01c'),
        (444, 'Market Backtest', '#8191a7'),
        (522, 'Market Equal Weight', '#4d9db4'),
        (600, 'Non-R&D Payers', '#b3bdca'),
    ):
        dark_labels.append(text(1543, y, name, size=26, color=color))
    build('redi-business-card-dark.png', 'redi-business-card-dark-labeled.svg', 1865, 1079,
          '#000000', [(185, 3, 1070, 51), (1539, 329, 326, 176)], dark_labels)


if __name__ == '__main__':
    main()
