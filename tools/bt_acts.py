"""Bhutan, breadth pass: every English Act in the Office of the Attorney General's Depository of Laws that reads
cleanly, as enacted -> corpus.d/30-acts-NNN.json (gitlaw_common SCHEMA.md). Reads only .cache (no network).

    python -X utf8 bt_acts.py parse --batch 001

Parsing is build.read_act (extract.py, parse.py, dates.py), the same reader as the first four Acts in corpus.json.
Each Act is one version: its text as enacted, dated by the commencement date its own text prints (the Gregorian date
after "corresponding to"), or, when it prints none, by the date of passing it prints. The Office publishes no
consolidated texts, so an Act amended later shows its original wording from its own start (true of that wording);
amending Acts are their own folders and are not replayed.

Gate (an Act is left out unless all hold):
- an English text layer, at least 3 numbered units, and a date read from the Act's own text;
- the units are numbered without a gap (1, 2, 3 ... ; 12A after 12 allowed; 1.1, 1.2 ... 2.1 for decimal Acts);
- every word of the English text lines (running heads and page numbers dropped by the reader) is in the units, in
  order and none added: the word sequences of the source lines and of front + units are identical;
- no publisher footnote ("Added by the ... Act") is inside the units;
- the Act is not superseded: no later Act in the Depository has the same name (Tenancy Act 2004 -> 2015), and no Act
  in the Depository says it repeals it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402
from extract import read_pdf  # noqa: E402

PUBLISHER = {'name': 'Office of the Attorney General of Bhutan', 'email': 'oag@oag.gov.bt.invalid'}
DONE_FILES = {'Constitution_of_Bhutan.pdf', 'Penal-Code-of-Bhutan-2004_English-version_.pdf',
              'Civil-and-Criminal-Procedure-Code-of-Bhutan-2001English-version0.pdf', 'Contract-Act-of-Bhutan-2013.pdf'}
# Titles whose file name or short-title line is garbled in the source (spacing, a stray file suffix, capitals).
TITLE_FIX = {
    'Lhengyel Zhungtsho Act of Bhutan 1999English 1': 'Lhengyel Zhungtsho Act of Bhutan 1999',
    'Speacker Act of the National Assembly 1996': 'Speaker Act of the National Assembly 1996',
    'Financial Services ACT': 'Financial Services Act 2011',
    'National Assembly Act of the Bhutan 2008': 'National Assembly Act of Bhutan 2008',
    'Bhutan Standards Act': 'Bhutan Standards Act 2010',
    'Bhutan Education City Act': 'Bhutan Education City Act 2012',
    'Entitlement and Service ConditionsAmendmentAct for the HoldersMembers and Commission of Constitutional Offices of Bhutan 2021':
        'Entitlement and Service Conditions Amendment Act for the Holders, Members and Commission of Constitutional Offices of Bhutan 2021',
    'Entitlement and Service Conditions Act for the Holders Members Commissionners of Constitutional Offices of Bhutan 2010':
        'Entitlement and Service Conditions Act for the Holders, Members and Commissioners of Constitutional Offices of Bhutan 2010',
    'Civil Criminal Procedure Code Amedment Act of Bhutan 2021': 'Civil and Criminal Procedure Code Amendment Act of Bhutan 2021',
    'Marriage Aamendment Act of Bhutan 2009': 'Marriage Amendment Act of Bhutan 2009',
    'Sales excise and Custome amendment Act 2012': 'Sales Tax, Customs and Excise Amendment Act 2012',
    'Civil Liability act of Bhutan 2023': 'Civil Liability Act of Bhutan 2023',
}
# Repeals printed in another Act of the Depository that the name match above does not catch (read from the texts).
REPEALED = {
    'Speacker-Act-of-the-National-Assembly-1996English.pdf': 'repealed by the National Assembly Speaker Act of Bhutan 2004, s. 1(3)',
    'Bhutan-Municipal-Act-1999English-version.pdf': 'repealed by the Thromde Act of Bhutan 2007, s. 2',
    'Dzongkhag-Yargay-Tshogdu-Chathrim-2002English-version.pdf': 'repealed by the Local Government Act of Bhutan 2009, s. 2',
    'Thromde-Act-of-Bhutan-2007both-Dzongkha-English.pdf': 'repealed by the Local Government Act of Bhutan 2009, s. 2',
    'Local-Governance-Act-2007-English.pdf': 'repealed by the Local Government Act of Bhutan 2009, s. 2',
    'National-Assembly-Committees-Act-of-the-Kingdom-of-Bhutan-2004-English-version.pdf':
        'repealed by the National Assembly (Amendment) Act of Bhutan 2014, s. 2 (new s. 4 of the National Assembly Act)',
    'Office-of-the-Attorney-General-Act-of-Bhutan-2006English-version.pdf': 'repealed by the Office of the Attorney General Act 2015',
    'Tobacco-Control-Amendment-Act-2012.pdf': 'repealed by the Tobacco Control (Amendment) Act of Bhutan 2014, s. 2 (new s. 2A)',
}
NOTE = re.compile(r'\b(?:Added|Amended|Substituted|Inserted|Repealed|Omitted|Deleted|Renumbered) (?:vide|by) (?:the|Act|section)\b')
KIND_WORDS = re.compile(r'\b(Act|Code|Chathrim|Thrimzhung|Law|Constitution)\b', re.I)


def norm(s: str) -> str:
    s = s.translate(str.maketrans({'“': '"', '”': '"', '‘': "'", '’': "'", ' ': ' '}))
    return re.sub(r'[ \t]+', ' ', s).strip()


def words(s: str) -> list[str]:
    return re.findall(r'[A-Za-z0-9]+', norm(s))


def title_of(a: dict) -> str:
    st = norm(a['parsed'].get('short_title') or '')
    ft = build.clean_file_title(a['file'])
    ft = re.sub(r'(?i)(?<=\d{4})\s*(?:english|eng|both|dzongkha)\w*$', '', ft)
    ft = re.sub(r'(?i)\s+(?:english|eng)\s*\d?$', '', ft).strip()
    fw = {w.lower() for w in words(ft) if not w.isdigit()} - {'of', 'the', 'and', 'act', 'bhutan', 'kingdom'}
    sw = {w.lower() for w in words(st) if not w.isdigit()}
    good = (8 <= len(st) <= 120 and KIND_WORDS.search(st) and fw and len(fw & sw) / len(fw) >= 0.6
            and not re.search(r'corresponding|Year|Month|Day\b', st))
    t = st if good else ft
    t = TITLE_FIX.get(t, t)
    t = re.sub(r'\s+,', ',', re.sub(r'\s+', ' ', t)).strip(' ,.')
    if not build.title_year(t) and build.title_year(ft):
        t = f'{t} {build.title_year(ft)}'
    return t


def key_of(stem: str) -> str:
    m = re.fullmatch(r'(section|article)-(\d+)([a-z]*)', stem.lower())
    if m:
        return ('sec' if m.group(1) == 'section' else 'art') + f'-{int(m.group(2)):03d}' + (('-' + m.group(3)) if m.group(3) else '')
    m = re.fullmatch(r'section-(\d+)\.(\d+)', stem.lower())
    if m:
        return f'sec-{int(m.group(1)):03d}-{int(m.group(2)):03d}'
    m = re.fullmatch(r'section-([a-z]+)-(\d+)-(\d+)', stem.lower())
    if m:
        return f'sec-{int(m.group(2)):03d}-{int(m.group(3)):03d}-{m.group(1)}'
    raise ValueError('odd stem ' + stem)


def gapless(scheme: str, labels: list[str]) -> bool:
    prev = None
    for lab in labels:
        if scheme == 'int':
            m = re.fullmatch(r'(\d+)([A-Z]?)', lab)
            cur = (int(m.group(1)), m.group(2))
            ok = cur == (1, '') if prev is None else ((cur[0] == prev[0] and prev[1] < cur[1]) if cur[1]
                                                      else cur[0] == prev[0] + 1)
        elif scheme in ('dec', 'dz'):
            nums = [int(x) for x in re.findall(r'\d+', lab)][-2:]
            cur = tuple(nums)
            ok = cur == (1, 1) if prev is None else ((cur[0] == prev[0] and cur[1] == prev[1] + 1)
                                                     or (cur[0] == prev[0] + 1 and cur[1] == 1))
        elif scheme == 'article':
            cur = int(lab)
            ok = cur == 1 if prev is None else cur == prev + 1
        else:
            return False
        if not ok:
            return False
        prev = cur
    return True


def units_of(p: dict) -> dict:
    units = {}
    if p['front'].strip():
        units['front'] = {'label': 'Title and preamble', 'kind': 'preamble', 'text': '# Title and preamble\n' + norm(p['front']) + '\n'}
    for u in p['units']:
        k = key_of(u['stem'])
        if k in units:
            raise ValueError('duplicate ' + k)
        text = '\n'.join(norm(l) for l in u['text'].splitlines() if l.strip())
        if u['stem'].startswith('article-'):
            text = re.sub(r'^## (Article \d+)\n(.+)\n', r'# \1 - \2\n', text, count=1)
        else:
            text = '\n'.join(l.replace('## ', '# ') for l in text.splitlines())
        units[k] = {'label': ('Article ' if k.startswith('art') else 'Section ') + u['label'],
                    'kind': 'art' if k.startswith('art') else 'sec', 'text': text + '\n'}
    return units


def unit_words(units: dict) -> list[str]:
    out = []
    for k, u in units.items():
        body = u['text'].split('\n', 1)[1] if k == 'front' else u['text']  # front's heading line is ours
        out += words(re.sub(r'(?m)^#+ ', '', body))
    return out


def superseded(acts: list[dict], listing: list[dict]) -> dict[str, str]:
    """file -> why it is left out as no longer in force."""
    out = {}
    names = []
    for it in listing:
        t = build.clean_file_title(it['file'])
        y = build.title_year(t)
        if y and not re.search(r'amend?ment|amedment', t, re.I):
            names.append((build.base_name(t), int(y), it['file']))
    for a in acts:
        if a.get('amending'):
            continue
        t = title_of(a)
        b, y = build.base_name(t), int(a['in_force'][:4])
        later = [f for nb, ny, f in names if nb == b and ny > int(build.title_year(t) or y)]
        if b and later:
            out[a['file']] = f'superseded by a later Act of the same name ({later[0]})'
    # repeal statements: "The X Act, YYYY is hereby repealed" in another Act
    for a in acts:
        for u in a['parsed']['units']:
            for m in build.REPEAL_ACT.finditer(u['text'].replace('\n', ' ')):
                tgt = build.base_name(m.group(1))
                ty = build.title_year(m.group(1))
                for o in acts:
                    if o is a or o['file'] in out:
                        continue
                    ot = title_of(o)
                    if build.base_name(ot) == tgt and (not ty or ty == build.title_year(ot)) \
                            and o['in_force'] < a['in_force']:
                        out[o['file']] = f"repealed by {a['title']}"
    return out


def parse(batch: str) -> None:
    listing = json.loads((build.CACHE / 'acts.json').read_text('utf-8'))
    acts, issues = build.load(None, '2026-11-03')
    sup = superseded(acts, listing) | REPEALED
    have = {a['slug'] for a in json.loads((HERE / 'corpus.json').read_text('utf-8'))['acts']}
    for p in sorted((HERE / 'corpus.d').glob('*.json')) if (HERE / 'corpus.d').exists() else []:
        have |= {a['slug'] for a in json.loads(p.read_text('utf-8'))['acts']}
    out, laws, report = [], {}, []
    for a in acts:
        p = a['parsed']
        why = None
        title = title_of(a)
        slug = build.slugify(title)
        if not build.title_year(slug):
            slug = f"{slug}-{a['in_force'][:4]}"
        if a['file'] in DONE_FILES or slug in have:
            continue
        if a['file'] in sup:
            why = sup[a['file']]
        elif len(p['units']) < 3:
            why = 'fewer than 3 numbered units'
        elif not gapless(p['scheme'], [u['label'] for u in p['units']]):
            why = f"numbering has a gap ({p['scheme']})"
        if not why:
            try:
                units = units_of(p)
            except ValueError as e:
                why = str(e)
        if not why and any(NOTE.search(u['text']) for u in units.values()):
            why = 'publisher footnotes ("Added by ...") inside the units'
        if not why:
            r = read_pdf(str(build.PDFS / a['file']))
            src = []
            for _, line in r['lines']:
                src += words(line)
            got = unit_words(units)
            if src != got:
                i = next((i for i, (x, y) in enumerate(zip(src, got)) if x != y), min(len(src), len(got)))
                why = f'words differ from the source at word {i} of {len(src)} ({" ".join(src[i:i + 6])!r} vs {" ".join(got[i:i + 6])!r})'
        if why:
            report.append({'file': a['file'], 'title': title, 'left_out': why})
            continue
        lk = f'act-{slug}'
        laws[lk] = {'label': title, 'title': title, 'kind': 'law', 'enacted': a['enacted'] or a['in_force'],
                    'published': None, 'url': a['url'], 'temporary_until': None, 'restores': None, 'note': None}
        basis = ('its commencement clause' if a['basis'] == 'commencement'
                 else 'the date of passing it prints (no commencement date is printed)')
        out.append({'slug': slug, 'short': title, 'title': title, 'url': a['url'], 'first_law': lk, 'earlier_laws': [],
                    'publisher': PUBLISHER,
                    'versions': [{'from': a['in_force'], 'source_url': a['url'], 'sha256': p['sha256'], 'units': units,
                                  'credits': {},
                                  'note': f"{title} as enacted, dated {a['in_force']} by {basis}; English text of the "
                                          f"Office of the Attorney General's Depository of Laws."}]})
        report.append({'file': a['file'], 'title': title, 'slug': slug, 'from': a['in_force'], 'basis': a['basis'],
                       'units': len(units)})
        have.add(slug)
    for i in issues:
        report.append({'file': i[0], 'title': i[1], 'left_out': i[2]})
    (HERE / '.work').mkdir(exist_ok=True)
    (HERE / '.work' / f'report-{batch}.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), 'utf-8')
    if not out:
        print('no new acts')
        return
    part = {
        'laws': laws,
        'sources': [{'name': 'Office of the Attorney General of Bhutan, Depository of Laws', 'url': 'https://oag.gov.bt/?page_id=7854',
                     'retrieved': '2026-10-28', 'licence': 'Official legislative texts are excluded from copyright by section 7(b) of the Copyright Act of the Kingdom of Bhutan, 2001.',
                     'notes': f'{len(out)} Acts in this part: English PDFs with a text layer, as enacted.'}],
        'decisions': [
            'Acts in parts 30-acts-*: each Act is one version, its English text as enacted, dated by the Gregorian '
            'commencement date printed in it, or the date of passing it prints when it gives no commencement date. The '
            'Office of the Attorney General publishes no consolidated texts, so an Act amended since shows its original '
            'wording from that day; each amending Act is its own folder and its changes are not applied.',
            'Left out of parts 30-acts-*: Acts with no English text layer (scans; no OCR), Dzongkha-only files, Acts '
            'that print no Gregorian date, Acts whose numbered sections have a gap or whose words do not match the '
            'source line for line, and Acts superseded by a later Act of the same name or repealed by another Act in '
            'the Depository.',
        ],
        'ai_use': ['Claude Code (Claude Opus 5.5, claude-opus-5-5) wrote bt_acts.py, which selects and checks the Acts. '
                   'No model wrote, summarised or transformed legal text: the reader is deterministic code over the PDF '
                   'text layer.'],
        'acts': out,
    }
    dst = HERE / 'corpus.d' / f'30-acts-{batch}.json'
    dst.parent.mkdir(exist_ok=True)
    tmp = dst.with_suffix('.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + '\n', 'utf-8', newline='\n')
    tmp.replace(dst)
    print(len(out), 'acts ->', dst.name)


if __name__ == '__main__':
    if sys.argv[1:2] == ['parse']:
        parse(sys.argv[sys.argv.index('--batch') + 1] if '--batch' in sys.argv else '001')
    else:
        raise SystemExit(__doc__)
