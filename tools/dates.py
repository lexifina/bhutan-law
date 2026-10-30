"""Read an Act's commencement and enactment dates from its own text (Gregorian dates only; the Bhutanese-calendar
date that usually comes first is kept as text, never converted)."""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                      'september', 'october', 'november', 'december'], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
MONTHS['sept'] = 9
ORD = {}
_units = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth']
_teens = ['tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth',
          'eighteenth', 'nineteenth']
for i, w in enumerate(_units, 1):
    ORD[w] = i
    ORD['twenty ' + w] = 20 + i
    ORD['thirty ' + w] = 30 + i
for i, w in enumerate(_teens, 10):
    ORD[w] = i
ORD['twentieth'] = 20
ORD['thirtieth'] = 30
ORD['eight'] = 8  # "the Eight Day of the Fifth Month" (Anti-Corruption Act 2006)
_ordw = '|'.join(sorted((re.escape(k).replace('\\ ', '[ -]+') for k in ORD), key=len, reverse=True))

NUM = r'(\d{1,2})\s*(?:st|nd|rd|th)?'
DAYW = rf'(?:{NUM}|({_ordw}))'
MON_NAME = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?'
MON_NUM = rf'(?:{NUM}|({_ordw}))\s+month'
_small = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
          'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'twenty one', 'twenty two',
          'twenty three', 'twenty four', 'twenty five', 'twenty six']
YEAR_WORDS = {f'two thousand and {w}': 2000 + i for i, w in enumerate(_small, 1)}
YEAR_WORDS.update({f'two thousand {w}': 2000 + i for i, w in enumerate(_small, 1)})
YEAR_WORDS['two thousand'] = 2000
_yw = '|'.join(sorted((re.escape(k).replace('\\ ', '[ -]+') for k in YEAR_WORDS), key=len, reverse=True))
YEAR = rf'((?:19|20)\d{{2}}|{_yw})'
# day [day of] [the] month[,] [of] [the year] year
P_DMY = re.compile(rf'{DAYW}\s*,?\s*(?:day\s*)?(?:of\s+)?(?:the\s+)?(?:month\s+of\s+)?(?:{MON_NAME}|{MON_NUM})\s*,?\s*(?:month\s*,?\s*)?(?:of\s+|or\s+)?(?:the\s+)?(?:year\s+)?(?:of\s+)?{YEAR}', re.I)
# month day, year
P_MDY = re.compile(rf'{MON_NAME}\s+{NUM}\s*,?\s*{YEAR}', re.I)
# dd/mm/yyyy or dd.mm.yyyy
P_NUM = re.compile(r'\b(\d{1,2})[./](\d{1,2})[./]((?:19|20)\d{2})\b')


def _ord(s: str | None) -> int | None:
    if not s:
        return None
    return ORD.get(re.sub(r'[ -]+', ' ', s.lower()).strip())


def _mon(s: str | None) -> int | None:
    if not s:
        return None
    s = s.lower().rstrip('.')
    return MONTHS.get(s) or MONTHS.get(s[:3])


def _year(s: str) -> int:
    if s.isdigit():
        return int(s)
    return YEAR_WORDS.get(re.sub(r'[ -]+', ' ', s.lower()).strip(), 0)


def find_dates(seg: str) -> list[tuple[int, str]]:
    """Every Gregorian date in seg: [(position, 'YYYY-MM-DD')]."""
    out = []
    seg = re.sub(r'\s+', ' ', seg)
    for m in P_DMY.finditer(seg):
        d = int(m.group(1)) if m.group(1) else _ord(m.group(2))
        if m.group(3):
            mo = _mon(m.group(3))
        else:
            mo = int(m.group(4)) if m.group(4) else _ord(m.group(5))
        out.append((m.start(), d, mo, _year(m.group(6))))
    for m in P_MDY.finditer(seg):
        out.append((m.start(), int(m.group(2)), _mon(m.group(1)), int(m.group(3))))
    for m in P_NUM.finditer(seg):
        out.append((m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    res = []
    for pos, d, mo, y in sorted(out):
        try:
            res.append((pos, date(y, mo, d).isoformat()))
        except (TypeError, ValueError):
            pass
    return res


TRIGGER = re.compile(r'(?:come|came|comes|coming|enter|enters) into (?:force|effect)|with effect from|shall be effective', re.I)
THIS = re.compile(r'(?:this|the present)\s+(?:Act|Code|Chathrim|Law|Thrimzhung|Constitution)|It shall|shall\s*:', re.I)


def gregorian_after_correspond(seg: str) -> str | None:
    """Prefer the date after 'corresponding to' / 'coinciding with' (the Gregorian one); else the first."""
    ds = find_dates(seg)
    if not ds:
        return None
    m = re.search(r'correspond|coincid|which corresponds', seg, re.I)
    if m:
        after = [d for p, d in ds if p >= m.start()]
        if after:
            return after[0]
    return ds[0][1]


def commencement(text: str) -> tuple[str | None, str]:
    """(date, the sentence it was read from). Only the first commencement clause is read."""
    t = re.sub(r'\s+', ' ', text)
    for m in TRIGGER.finditer(t):
        if not THIS.search(t[max(0, m.start() - 200): m.start()]):
            continue  # "came into force" of a convention, a dissolution...: not this Act's commencement
        seg = t[m.start(): m.start() + 320]
        # stop at the next numbered provision or heading-like break
        cut = re.search(r'(?<=[.;])\s+(?:\(?[a-z0-9]{1,3}[.)]\s|[A-Z][A-Za-z ]{2,40}\s\d)', seg[40:])
        if cut:
            seg = seg[:40 + cut.start() + 1]
        d = gregorian_after_correspond(seg)
        if d:
            return d, seg.strip()
        return None, seg.strip()
    return None, ''


ENACT = re.compile(r'(?:has been passed|hereby enact(?:s|ed)?|(?:passed|enacted|adopted) by (?:the )?(?:Parliament|National Assembly|Gyalyong Tshogdu|Tshogdu)|ordain and adopt|hereby adopt(?:s|ed)?)', re.I)


def enactment(text: str) -> tuple[str | None, str]:
    """The date of passing or adoption printed in the front matter: the date nearest the enacting words, within
    250 characters either side."""
    t = re.sub(r'\s+', ' ', text)
    for m in ENACT.finditer(t):
        lo = max(0, m.start() - 250)
        seg = t[lo: m.end() + 250]
        ds = find_dates(seg)
        if not ds:
            continue
        here = m.start() - lo
        # within one sentence-ish window, prefer the Gregorian (after "corresponding to") date nearest the words
        best = min(ds, key=lambda d: abs(d[0] - here))
        g = gregorian_after_correspond(seg[max(0, best[0] - 200): best[0] + 120])
        return g or best[1], seg.strip()
    return None, ''
