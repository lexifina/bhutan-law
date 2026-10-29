"""English lines of one Act -> front matter + one unit per section (used by build.py).

Numbering schemes found in the OAG PDFs, tried in turn; the one giving the longest ordered chain wins:
  int      "1." / "12." / "12A."           (most Acts)          -> section-12.md
  dec      "1.1" / "12.3"                  (Electricity Act...) -> section-12.3.md
  article  "Article 7" with sections 1..n  (the Constitution)   -> article-7.md
  dz       "Ka 1-1" / "Ga 2.3"             (pre-1990 Acts)      -> section-ga-2-3.md
If no scheme gives at least 3 ordered units the whole text is one file, text.md.
Text before the first unit (title, preamble, enacting words) is front.md. Lines that come after a unit's last full
stop/semicolon/colon and before the next marker are the next unit's margin heading ("# Removal of ...").
"""
import re

LEADER = re.compile(r'\.{4,}|…{2,}|(?:\. ){4,}')
ITEM = re.compile(r'^(?:\d{1,3}[A-Z]?\.|\(\s*[0-9a-zA-Z]{1,5}\s*\)|[a-zA-Z]{1,4}\)|[a-z]\.|[ivxlc]{1,6}\.|\d{1,3}\))(?:\s|$)')
DZ = r'(?:Ka|Kha|Ga|Nga|Ca|Cha|Chha|Ja|Nya|Ta|Tha|Da|Na|Pa|Pha|Ba|Ma|Tsa|Tsha|Dza|Wa|Zha|Za|Ya|Ra|La|Sha|Sa|Ha)'

SCHEMES = {
    'int': re.compile(r'^(\d{1,3}[A-Z]?)\s*\.(?:\s+(\S.*))?$'),
    'dec': re.compile(r'^(\d{1,3}\.\d{1,3})\s*\.?(?:\s+(\S.*))?$'),
    'dz': re.compile(rf'^({DZ})\s*(\d{{1,2}})\s*[-.]\s*(\d{{1,3}})\s*\.?(?:\s+(\S.*))?$'),
    'article': re.compile(r'^(?:ARTICLE|Article)\s+(\d{1,3})\s*$'),
}


def _key(scheme, m):
    if scheme == 'int':
        g = m.group(1)
        n = int(re.match(r'\d+', g).group())
        return (n, g[len(str(n)):]), g, m.group(2)
    if scheme == 'dec':
        a, b = m.group(1).split('.')
        return (int(a), int(b)), m.group(1), m.group(2)
    if scheme == 'dz':
        return (int(m.group(2)), int(m.group(3))), f'{m.group(1).lower()}-{int(m.group(2))}-{int(m.group(3))}', m.group(4)
    return (int(m.group(1)),), m.group(1), None


def _next_ok(scheme, prev, cur):
    if prev is None:
        return cur in {(1, ''), (1, 1), (1,)}
    if scheme == 'int':
        (pn, ps), (cn, cs) = prev, cur
        if cs:  # 12A after 12, 12B after 12A
            return cn == pn and ps < cs
        return pn < cn <= pn + 2
    if scheme == 'dec' or scheme == 'dz':
        (pa, pb), (ca, cb) = prev, cur
        return (ca == pa and pb < cb <= pb + 2) or (pa < ca <= pa + 2 and cb == 1)
    return prev[0] < cur[0] <= prev[0] + 2


def _chain(scheme, lines, start):
    """Indexes of the markers in one ordered chain from `start`."""
    rx = SCHEMES[scheme]
    out = []
    prev = None
    for i in range(start, len(lines)):
        m = rx.match(lines[i])
        if not m:
            continue
        k = _key(scheme, m)[0]
        if _next_ok(scheme, prev, k):
            out.append(i)
            prev = k
    return out


def best_chain(lines):
    best = ('', [])
    for scheme, rx in SCHEMES.items():
        if scheme == 'article':
            continue
        starts = [i for i, l in enumerate(lines) if (m := rx.match(l)) and _key(scheme, m)[0] in {(1, ''), (1, 1), (1,)}]
        for s in starts[:12]:
            ch = _chain(scheme, lines, s)
            # a table of contents gives a chain as long as the body's: on a near-tie the later start (the body) wins
            if len(ch) * 20 >= len(best[1]) * 19 and len(ch) >= 3:
                if len(ch) > len(best[1]) or not best[1] or ch[0] > best[1][0]:
                    best = (scheme, ch)
    if True:
        # the Constitution: its Articles are the units even though each restarts at section 1
        art = []
        for s in [i for i, l in enumerate(lines) if (m := SCHEMES['article'].match(l)) and m.group(1) == '1']:
            ch = _chain('article', lines, s)
            if len(ch) * 20 >= len(art) * 19:
                art = ch
        if len(art) >= 10:
            best = ('article', art)
    return best


def paragraphs(lines):
    """Lines of a unit -> paragraphs: a new one at each list item; a lone item marker joins the next line."""
    out = []
    for l in lines:
        if LEADER.search(l):
            l = LEADER.sub(' ', l).strip()
        if not out:
            out.append(l)
        elif ITEM.match(l) or out[-1] and ITEM.fullmatch(out[-1] + ' '):
            if out[-1] and ITEM.fullmatch(out[-1] + ' '):
                out[-1] = out[-1] + ' ' + l
            else:
                out.append(l)
        else:
            prev = out[-1]
            if prev.endswith('-') and len(prev) > 1 and prev[-2].isalpha() and l[:1].islower():
                out[-1] = prev + l
            else:
                out[-1] = prev + ' ' + l
    return [re.sub(r' +', ' ', p).strip() for p in out if p.strip()]


def _split_heading(body):
    """Trailing short lines after the last line that ends a sentence are the next unit's heading."""
    end = len(body)
    i = len(body)
    while i > 0:
        l = body[i - 1]
        if re.search(r'[.;:,]$|\b(?:and|or)$', l) or ITEM.match(l) or len(l) > 100:
            break
        i -= 1
    if i == 0 or i == end or end - i > 3:
        return body, []
    return body[:i], body[i:]


def split_units(lines):
    """-> (scheme, front_lines, [(unit_id, file_stem, heading_lines, body_lines)])"""
    scheme, chain = best_chain(lines)
    if len(chain) < 3:
        return 'none', [], [('text', 'text', [], '', lines)]
    rx = SCHEMES[scheme]
    front = lines[:chain[0]]
    units = []
    pending_heading = []
    front, h = _split_heading(front)
    pending_heading = h
    for n, i in enumerate(chain):
        end = chain[n + 1] if n + 1 < len(chain) else len(lines)
        m = rx.match(lines[i])
        _, label, rest = _key(scheme, m)
        body = ([rest] if rest else []) + lines[i + 1:end]
        if n + 1 < len(chain):
            body, nxt = _split_heading(body)
        else:
            nxt = []
        stem = f'article-{label}' if scheme == 'article' else f'section-{label}'
        marker = f'Article {label}' if scheme == 'article' else (lines[i] if not rest else lines[i][:len(lines[i]) - len(rest)].strip())
        units.append((label, stem, pending_heading, marker, body))
        pending_heading = nxt
    return scheme, front, units


def render_unit(heading, marker, body):
    out = [f'# {h}' for h in heading]
    paras = paragraphs(body)
    if paras and marker and not marker.startswith('Article'):
        paras[0] = f'{marker} {paras[0]}'
    elif marker:
        out.append(f'## {marker}')
    out += paras
    return '\n'.join(out) + '\n'
