"""Conservative, local-only cleanup of the game's short SEC filing excerpts.

The source excerpt stays a quotation, not a generated investment thesis. In
particular, a clipped monetary scale is restored only from the adjacent words
of the original cached report. Quotes share a 25-word budget per filing.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import gzip
import hashlib
from pathlib import Path
import re
from urllib.parse import urlsplit


_TOPICS = {
    'Research & development': re.compile(r'research\s+and\s+development|research\s*&\s*development|product\s+development', re.I),
    'Capital investment': re.compile(r'capital\s+(?:expenditures|investments?|spending)|manufacturing\s+(?:capacity|facilities)|new\s+(?:facilities|plants|stores)', re.I),
    'Acquisitions': re.compile(r'acquisitions?\s+(?:of|and)|(?:strategic|business)\s+acquisitions|acquired\s+(?:the|a)\s+(?:business|company)', re.I),
    'Technology & infrastructure': re.compile(r'invest\w*\s+(?:in|into)\s+(?:our\s+)?(?:technology|infrastructure|software|digital)|data\s+centers|cloud\s+computing', re.I),
    'Products & expansion': re.compile(r'new\s+products|product\s+innovation|expand\w*\s+(?:our|the)\s+(?:business|capacity|operations|market)', re.I),
}
_SCALE = re.compile(r'^(?:million|billion|trillion|thousand)\b', re.I)
_ENDING_AMOUNT = re.compile(r'(?:[$£€¥]\s*[+-]?[\d,]+(?:\.\d+)?|(?<![\w.])\d[\d,]*\.\d+)\s*$', re.I)
_ENDING_NUMBER = re.compile(r'(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?\s*$')
_NEGATION = re.compile(r'\b(?:not|no|never|without)\b|n[’\']t\b', re.I)
_NOTE = 'Short automated excerpt from the annual filing; a topic mention, not a verified project budget.'
_TEXT_CACHE: OrderedDict[str, str] = OrderedDict()
_CACHE_SIZE = 32
_CLEAN_CACHE: OrderedDict[tuple, tuple] = OrderedDict()
_CLEAN_CACHE_SIZE = 4096
_C1_PATTERN = re.compile(r'[\x80-\x9f]')
_C1_TRANSLATION = {}
for _code in range(0x80, 0xA0):
    try:
        _C1_TRANSLATION[_code] = bytes([_code]).decode('cp1252')
    except UnicodeDecodeError:
        pass


def _normalize(value):
    text = str(value or '')
    # Most decoded filings have no legacy C1 characters. Translating every
    # character through a Python mapping is needlessly expensive on big reports.
    if _C1_PATTERN.search(text):
        text = text.translate(_C1_TRANSLATION)
    return ' '.join(text.split())


def _source_text(filing, cache_root):
    """Cache successful parses by the original report's verified SHA-256."""
    try:
        parsed = urlsplit(str(filing.get('url') or ''))
    except ValueError:
        return None
    match = re.match(r'^/Archives/edgar/data/(\d+)/', parsed.path)
    accession = str(filing.get('accession') or '')
    if parsed.hostname != 'www.sec.gov' or not match or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
        return None
    expected = filing.get('sha256')
    if expected is not None and not re.fullmatch(r'[a-fA-F0-9]{64}', str(expected)):
        return None
    key = str(expected).lower() if expected else None
    if key in _TEXT_CACHE:
        _TEXT_CACHE.move_to_end(key)
        return _TEXT_CACHE[key]
    path = Path(cache_root) / str(int(match.group(1))) / 'raw' / (accession + '.html.gz')
    try:
        raw = gzip.decompress(path.read_bytes())
        actual = hashlib.sha256(raw).hexdigest()
        if key and actual != key:
            return None
        key = actual
        if key in _TEXT_CACHE:
            _TEXT_CACHE.move_to_end(key)
            return _TEXT_CACHE[key]
        from lxml import etree
        # Generic Elements preserve the same text nodes, without millions of
        # Python HtmlElement class-lookup callbacks while walking annual reports.
        document = etree.fromstring(raw, parser=etree.HTMLParser())
        for node in list(document.iter('script', 'style')):
            if node.getparent() is not None:
                node.getparent().remove(node)
        # Return plain strings directly from libxml instead of materializing a
        # Python Element for every node in large XBRL reports.
        text = _normalize(' '.join(document.xpath('//text()', smart_strings=False)))
    except Exception:
        # Missing, malformed, or undecodable cached reports cannot justify
        # adding a unit. The caller drops an incomplete monetary quotation.
        return None
    _TEXT_CACHE[key] = text
    _TEXT_CACHE.move_to_end(key)
    while len(_TEXT_CACHE) > _CACHE_SIZE:
        _TEXT_CACHE.popitem(last=False)
    return text


def _trim_topic_prefix(excerpt, label):
    pattern = _TOPICS.get(label)
    match = pattern.search(excerpt) if pattern else None
    if match and match.start() and not _NEGATION.search(excerpt[:match.start()]):
        return excerpt[match.start():].strip(' ,;:')
    return excerpt


def _following_scale(text, excerpt):
    """Return a source-adjacent scale only when every matching unit agrees."""
    if not text:
        return None
    scales = {}
    found = text.find(excerpt)
    while found != -1:
        tail = text[found + len(excerpt):]
        # A substring ending mid-word must not be mistaken for a quote boundary.
        if tail and tail[0].isspace():
            scale = _SCALE.match(tail.lstrip())
            if scale:
                unit = scale.group(0)
                scales.setdefault(unit.casefold(), unit)
                if len(scales) > 1:
                    return None
        found = text.find(excerpt, found + 1)
    return next(iter(scales.values()), None)


def _budgeted(excerpt, remaining):
    words = excerpt.split()
    if len(words) <= remaining:
        return excerpt
    candidate = ' '.join(words[:remaining])
    # Never introduce a dangling amount by truncating off its scale word.
    if _incomplete_amount(candidate) or candidate.endswith(('$', '£', '€', '¥')):
        return None
    return candidate.strip(' ,;:') or None


def _incomplete_amount(excerpt):
    if _ENDING_AMOUNT.search(excerpt):
        return True
    number = _ENDING_NUMBER.search(excerpt)
    if not number:
        return False
    prefix = excerpt[:number.start()]
    # A clipped date remains a date, while "expenditures were 1800" may be
    # missing a scale even if the source did not use a currency symbol.
    if re.search(r'\b(?:in|during|since|year|years)\s*$', prefix, re.I):
        return False
    return bool(re.search(r'\b(?:expenses?|expenditures?|spent|spending|investments?|costs?|revenues?|acquisitions?|capital)\b', prefix, re.I))


def clean_filing_excerpts(filing, cache_root):
    """Return a copy with source-verified monetary suffixes and <=25 quote words.

    No network, fabricated units, inferred spending, or rewritten source claims.
    Already complete excerpts remain usable when the local report is absent;
    excerpts ending in an unverifiable amount are dropped conservatively.
    Source links, report hashes, focus labels, and all other metadata are kept.
    """
    result = deepcopy(filing)
    themes = result.get('investmentThemes')
    if not isinstance(themes, list):
        return result
    digest = str(filing.get('sha256') or '').lower()
    cache_key = (digest, tuple((str(theme.get('label') or ''), str(theme.get('excerpt') or '')) if isinstance(theme, dict) else ('', '') for theme in themes)) if re.fullmatch(r'[a-f0-9]{64}', digest) else None
    if cache_key in _CLEAN_CACHE:
        _CLEAN_CACHE.move_to_end(cache_key)
        result['investmentThemes'] = [{**themes[index], 'excerpt': excerpt, 'note': _NOTE} for index, excerpt in _CLEAN_CACHE[cache_key]]
        return result
    source = None
    source_loaded = False
    remaining = 25
    cleaned = []
    processed = []
    for index, theme in enumerate(themes):
        if not isinstance(theme, dict) or remaining <= 0:
            continue
        excerpt = _trim_topic_prefix(_normalize(theme.get('excerpt')), theme.get('label'))
        if not excerpt:
            continue
        if _ENDING_NUMBER.search(excerpt):
            if not source_loaded:
                source = _source_text(filing, cache_root)
                source_loaded = True
            scale = _following_scale(source, excerpt)
            if scale:
                excerpt += ' ' + scale
            elif _incomplete_amount(excerpt):
                continue
        excerpt = _budgeted(excerpt, remaining)
        if not excerpt:
            continue
        cleaned.append({**theme, 'excerpt': excerpt, 'note': _NOTE})
        processed.append((index, excerpt))
        remaining -= len(excerpt.split())
    result['investmentThemes'] = cleaned
    # Do not cache a failed source lookup: an in-progress local download may
    # supply that exact report later in the same process.
    if cache_key and (not source_loaded or source is not None):
        _CLEAN_CACHE[cache_key] = tuple(processed)
        _CLEAN_CACHE.move_to_end(cache_key)
        while len(_CLEAN_CACHE) > _CLEAN_CACHE_SIZE:
            _CLEAN_CACHE.popitem(last=False)
    return result
