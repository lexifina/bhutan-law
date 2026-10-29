"""PDF -> English lines for one OAG Act PDF (used by build.py and survey).

Reads the text layer with PyMuPDF, one page at a time. Pages are kept only when they read as English (Dzongkha pages
are either Tibetan script or legacy-font text that comes out as Latin letters, so the test counts common English
words, not scripts). Page numbers and running headers (short lines repeated on many pages) are dropped and listed.
"""
import re
from collections import Counter

import pymupdf

EN_WORDS = set('the of and to in a shall be or any by for this act which as with on is under such from may other '
               'person be an section that it not at are its'.split())
WORD = re.compile(r'[A-Za-z]+')
TIBETAN = re.compile('[ༀ-࿿]')
PAGE_NO = re.compile(r'^\s*(?:page\s+)?(?:\d{1,3}|[ivxlc]{1,6})(?:\s+of\s+\d{1,3})?\s*$', re.I)


def norm_line(s: str) -> str:
    s = (s.replace('\xa0', ' ').replace('\xad', '').replace('​', '').replace('﻿', '')
         .replace(' ', ' ').replace(' ', ' ').replace(' ', ' ').replace('\t', ' '))
    s = ''.join(ch for ch in s if ch >= ' ' or ch == '\n')
    return re.sub(r' +', ' ', s).strip()


def page_is_english(text: str) -> bool:
    if TIBETAN.search(text) and len(TIBETAN.findall(text)) > len(text) * 0.05:
        return False
    words = WORD.findall(text.lower())
    if len(words) < 3:
        return False
    hits = sum(1 for w in words if w in EN_WORDS)
    return hits >= max(2, 0.12 * len(words))


def read_pdf(path: str) -> dict:
    """{'pages': n, 'english_pages': [i...], 'lines': [(page, text)], 'dropped': Counter, 'chars': total chars}"""
    doc = pymupdf.open(path)
    pages = []
    total = 0
    for i, page in enumerate(doc):
        t = page.get_text()
        total += len(t.strip())
        pages.append(t)
    eng = [i for i, t in enumerate(pages) if page_is_english(t)]
    per_page = {i: [norm_line(l) for l in pages[i].split('\n')] for i in eng}
    per_page = {i: [l for l in ls if l] for i, ls in per_page.items()}
    # running headers: a short line seen on at least 4 pages and on a fifth of the English pages
    seen = Counter()
    for ls in per_page.values():
        for l in set(ls[:2] + ls[-2:]):  # only a page's first or last two lines can be a running header
            if len(l) <= 90:
                seen[l] += 1
    limit = max(4, len(eng) // 5)
    headers = {l for l, n in seen.items() if n >= limit and not re.match(r'^\(?[a-z0-9]{1,4}[.)]', l)}
    dropped = Counter()
    lines = []
    for i in eng:
        for j, l in enumerate(per_page[i]):
            edge = j < 2 or j >= len(per_page[i]) - 2
            if (PAGE_NO.match(l) and edge) or (l in headers and edge):
                dropped[l] += 1
                continue
            lines.append((i, l))
    return {'pages': len(pages), 'english_pages': eng, 'lines': lines, 'dropped': dropped, 'chars': total,
            'headers': sorted(headers)}
