"""Apply the animated Hetzerk initial to visible words without changing their text."""
import re

from bs4 import BeautifulSoup, Comment, NavigableString

from publishing.development_notice import add_development_notice

# Permit sentence punctuation and prose such as "Hetzerk-based", while leaving
# domains, email addresses, paths and workbook filenames as literal references.
NAME = re.compile(r'(?<![\w@./-])hetzerk(?![\w@/])(?!(?:\.[A-Za-z0-9]|-[\w-]+\.[A-Za-z0-9]))', re.I)
PLAIN_TEXT = {'script', 'style', 'title', 'textarea', 'select', 'option', 'code', 'pre', 'svg', 'math'}


def apply_branding(html):
    page = BeautifulSoup(html, 'html.parser')
    if not page.body or not page.head:
        return html
    add_development_notice(page)
    if not page.select_one('link[href="/assets/branding.css"]'):
        page.head.append(page.new_tag('link', rel='stylesheet', href='/assets/branding.css'))
    if not page.select_one('script[data-favicon-motion]'):
        page.head.append(page.new_tag('script', attrs={
            'src': '/assets/favicon-motion.js?v=1', 'defer': '', 'data-favicon-motion': '',
        }))

    # One corporate lockup, including the compact headers used on Section 351 pages.
    for mark in page.select('header .w-12.h-12, header .hetzerk-logo'):
        if 'hetzerk-logo' not in mark.get('class', []) and mark.get_text(strip=True) != 'H':
            continue
        mark.name = 'a'
        mark.clear()
        mark.attrs = {'class': ['hetzerk-logo'], 'href': '/', 'aria-label': 'Hetzerk Asset Management home'}
    for header in page.find_all('header'):
        for name in header.find_all(['div', 'a']):
            if name.find(True) or name.get_text(strip=True) != 'Hetzerk':
                continue
            if name.parent.get_text(' ', strip=True) != 'Hetzerk Asset Management':
                continue
            name['class'] = ['hetzerk-masthead-name']
            name.parent['class'] = ['hetzerk-lockup']
            subtitle = name.find_next_sibling()
            if subtitle:
                subtitle['class'] = ['hetzerk-masthead-subtitle']

    for node in list(page.body.find_all(string=NAME)):
        if isinstance(node, Comment):
            continue
        if any(parent.name in PLAIN_TEXT or parent.has_attr('hidden') or
               'hetzerk-name' in parent.get('class', []) for parent in node.parents):
            continue
        text = str(node)
        cursor = 0
        for match in NAME.finditer(text):
            node.insert_before(NavigableString(text[cursor:match.start()]))
            word = page.new_tag('span', attrs={'class': 'hetzerk-name'})
            initial = page.new_tag('span', attrs={'class': 'hetzerk-initial'})
            initial.string = match[0][0]
            word.append(initial)
            word.append(NavigableString(match[0][1:]))
            node.insert_before(word)
            cursor = match.end()
        node.insert_before(NavigableString(text[cursor:]))
        node.extract()
    return str(page)


def brand_pages(pages):
    return {route: apply_branding(html) for route, html in pages.items()}
