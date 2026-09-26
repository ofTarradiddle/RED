"""Shared, dismissible notice for the site's development period."""
from bs4 import BeautifulSoup


NOTICE = '''<aside class="development-notice" data-development-notice aria-label="Development notice">
  <div class="development-notice-inner">
    <span class="development-notice-stamp" lang="ja" aria-label="In development">開発中</span>
    <p class="development-notice-copy"><strong>Just for fun and development practice.</strong><span>This site is a work in progress.</span></p>
    <button class="development-notice-close" type="button" data-development-notice-close aria-label="Dismiss development notice" hidden>
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m7 7 10 10M17 7 7 17"/></svg>
    </button>
  </div>
</aside>'''


def add_development_notice(page):
    """Apply once to public pages, aliases and the local review dashboards."""
    if not page.select_one('[data-development-notice]'):
        page.body.insert(0, BeautifulSoup(NOTICE, 'html.parser').aside)
    if not page.select_one('link[data-development-notice-style]'):
        page.head.append(page.new_tag('link', attrs={
            'rel': 'stylesheet', 'href': '/assets/development-notice.css',
            'data-development-notice-style': '',
        }))
    if not page.select_one('script[data-development-notice-script]'):
        page.head.append(page.new_tag('script', attrs={
            'src': '/assets/development-notice.js', 'defer': '',
            'data-development-notice-script': '',
        }))
