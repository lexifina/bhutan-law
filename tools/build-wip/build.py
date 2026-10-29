"""Build the Bhutan law repository (as enacted) from the OAG PDF cache (fetch.py).

    python scripts/bhutan-law/build.py ~/Documents/bhutan-law --today YYYY-MM-DD [--only REGEX] [--push-every N]

The Office of the Attorney General publishes each Act as enacted (English and Dzongkha PDFs); amending Acts are
separate PDFs and no consolidated text exists. So (brief shape 3, "as-enacted"):
1. Each English Act with a text layer is one commit, authored by the Act itself, holding its text as enacted: one file
   per section (or per Article for the Constitution), one paragraph per line, plus front.md (title, preamble).
2. The commit is dated noon Bhutan time on the Act's commencement date as its own text gives it (the Gregorian date
   after "corresponding to"); when the Act names no date (commencement by notification, on assent) it is dated by
   the date of passing printed in it, and the basis is the `In-force-basis:` trailer. Acts with neither are listed in
   data/unreadable.csv and not built.
3. Amending Acts are Acts like any other (their own folder, as enacted). Their changes are NOT applied to the
   principal Act; each one is a row in data/amendments.csv (provision, kind, amending Act, its date). Whole-Act
   repeals printed in an Act are rows too (kind "repeal"); the repealed text stays in the tree.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
CACHE = HERE / '.cache'
PDFS = CACHE / 'pdf'
PARSED = CACHE / 'parsed'

from dates import commencement, enactment  # noqa: E402

COMMITTER = 'Lexifina <bhutan-law@lexifina.com>'
SOURCE = 'https://oag.gov.bt/?page_id=7854'

LANG_TOKENS = re.compile(r'[-_ ]*(?:both[-_ ]*)?(?:dzongkha|dzo|dz)?[-_ ]*(?:and|&)?[-_ ]*(?:english|eng)?[-_ ]*(?:version)?[-_ ]*\d?$', re.I)


def is_english_file(name: str) -> bool:
    n = name.lower()
    if re.search(r'english|eng\b|eng[-_.]|both', n):
        return True
    if re.search(r'dzongkha|dzo\b|dzo[-_.]|_dz\b|-dz\.|dzongkhag-version', n):
        return False
    return True


# ---------------------------------------------------------------------------------------------------- per act

def read_act(pdf: Path) -> dict:
    """Extract + parse one PDF; cached as JSON keyed by the PDF's sha256 and the parser sources."""
    from extract import read_pdf
    from parse import split_units, render_unit
    PARSED.mkdir(parents=True, exist_ok=True)
    code_hash = hashlib.sha256(b''.join((HERE / f).read_bytes() for f in ('extract.py', 'parse.py', 'dates.py'))).hexdigest()[:12]
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    cp = PARSED / f'{pdf.stem}.{code_hash}.json'
    if cp.exists():
        return json.loads(cp.read_text('utf-8'))
    r = read_pdf(str(pdf))
    lines = [l for _, l in r['lines']]
    text = '\n'.join(lines)
    out = {'pdf': pdf.name, 'sha256': pdf_hash, 'pages': r['pages'], 'english_pages': r['english_pages'],
           'chars': r['chars'], 'headers': r['headers'], 'dropped': sorted(r['dropped'].items())}
    if not lines:
        out['units'] = []
        cp.write_text(json.dumps(out), 'utf-8')
        return out
    scheme, front, units = split_units(lines)
    out['scheme'] = scheme
    out['front'] = render_unit([], '', front) if front else ''
    out['units'] = [{'label': u[0], 'stem': u[1], 'text': render_unit(u[2], u[3], u[4])} for u in units]
    joined = ' '.join(lines)
    out['commencement'], out['commencement_text'] = commencement(joined)
    out['enacted'], out['enacted_text'] = enactment(joined)
    m = re.search(r'(?:may|shall) be (?:cited|called|known) as[,:]?\s+(?:the\s+)?["“‘\']?(.{6,160}?)["”’\']?\s*(?:\.|;|,? and\b|\(|$)', joined, re.I)
    out['short_title'] = m.group(1).strip(' "“”‘’\'.,') if m else ''
    cp.write_text(json.dumps(out, ensure_ascii=False), 'utf-8')
    return out


def clean_file_title(t: str) -> str:
    t = re.sub(r'\.pdf$', '', t, flags=re.I)
    t = t.replace('_', ' ').replace('-', ' ')
    t = re.sub(r'\b(?:English|Eng|Dzongkha|Dzo|both|and|version|final|CONTENTFINAL)\b\s*\d?\s*$', '', t, flags=re.I)
    for _ in range(4):
        t = re.sub(r'\s*\b(?:English|Eng|Dzongkha|Dzo|both|version|final|CONTENTFINAL|and|\(|\))\s*$', '', t.strip(), flags=re.I)
    t = re.sub(r'(?<=[a-z])(?=(?:19|20)\d\d)', ' ', t)
    t = re.sub(r'(?<=[a-z])(?=English|Dzongkha)', ' ', t)
    t = re.sub(r'\s*\b(?:English|Dzongkha)\b.*$', '', t, flags=re.I)
    return re.sub(r'\s+', ' ', t).strip(' -_')


def slugify(t: str) -> str:
    t = t.lower().replace('&', ' and ')
    t = re.sub(r"[‘’']", '', t)
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:90]


def title_year(t: str) -> str:
    ys = re.findall(r'(?:18|19|20)\d\d', t)
    return ys[-1] if ys else ''


AMEND_ROW = re.compile(
    r'[Ss]ections?\s+(\d{1,3}[A-Z]?(?:\s*\(\s*[0-9a-zA-Z]{1,4}\s*\))*)(?:[^.;:]{0,60}?)\s+(?:of the [^.;:]{0,80}?\s+)?'
    r'(?:is|are|shall be)\s+(?:hereby\s+)?(?:further\s+)?(amended|inserted|repealed|substituted|deleted|renumbered|added|omitted|replaced)')
INSERT_NEW = re.compile(r'(?:new|following)\s+sections?\s+(\d{1,3}[A-Z]?(?:\s*\(\s*[0-9a-zA-Z]{1,4}\s*\))*)\s+(?:is|are|shall be)\s+(?:hereby\s+)?(inserted|added)', re.I)
REPEAL_ACT = re.compile(r'(?:^|[.;:]\s+|\(\w{1,3}\)\s+)(?:The\s+)?([A-Z][^.;:]{4,160}?\b(?:Act|Code|Chathrim|Thrimzhung|Rules|Regulations?)\b[^.;:]{0,40}?)\s+(?:is|are|shall\s+be|stands?)\s+(?:hereby\s+)?repealed', re.M)


def amendment_rows(act: dict, units: list[dict]) -> list[list[str]]:
    rows = []
    for u in units:
        for para in u['text'].splitlines():
            for rx in (AMEND_ROW, INSERT_NEW):
                for m in rx.finditer(para):
                    prov = re.sub(r'\s+', '', m.group(1))
                    rows.append([act.get('principal', ''), prov, m.group(2).lower(), act['title'], act['in_force'],
                                 f"{act['dir']}/{u['stem']}.md", para[:300]])
            for m in REPEAL_ACT.finditer(para):
                target = re.sub(r'\s+', ' ', m.group(1)).strip()
                if re.match(r'(?i)(?:section|this act|the act|sub-?section|chapter|part)\b', target):
                    continue
                rows.append([target, '(whole)', 'repeal', act['title'], act['in_force'], f"{act['dir']}/{u['stem']}.md", para[:300]])
    return rows


def base_name(t: str) -> str:
    t = t.lower()
    t = re.sub(r'\(?\bamend?ment\b\)?|\bamedment\b|\baamendment\b', ' ', t)
    t = re.sub(r'\bof (?:the )?(?:kingdom of )?bhutan\b|\bthe\b|\bof\b|\bact(?:s)?\b|\bfor\b|(?:18|19|20)\d\d|[^a-z ]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------------------------------------------------------------------------------------------------- dates

def tz_offset(day: str) -> int:
    """Bhutan: UTC+05:30 until 30 Sep 1987, UTC+06:00 from 1 Oct 1987 (no summer time). Minutes."""
    return 330 if day < '1987-10-01' else 360


def git_date(day: str, seq: int) -> str:
    off = tz_offset(day)
    sign = f"+{off // 60:02d}{off % 60:02d}"
    d = datetime.strptime(day, '%Y-%m-%d')
    if d.year < 1970:
        return f'{seq} {sign}'
    ts = int((datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=off)).timestamp())
    return f'{ts} {sign}'


# ---------------------------------------------------------------------------------------------------- catalogue

def load(only: str | None, today: str) -> tuple[list[dict], list[list[str]]]:
    listing = json.loads((CACHE / 'acts.json').read_text('utf-8'))
    acts, issues = [], []
    for item in listing:
        name = item['file']
        if only and not re.search(only, name):
            continue
        pdf = PDFS / name
        if not pdf.exists():
            issues.append([name, item['title'], 'not fetched'])
            continue
        if not is_english_file(name):
            issues.append([name, item['title'], 'Dzongkha only (this corpus is English)'])
            continue
        p = read_act(pdf)
        if not p['units']:
            issues.append([name, item['title'], 'no English text layer (a scan, or Dzongkha only)' if p['chars'] < 200 else 'no English pages found'])
            continue
        ft = clean_file_title(item['file'])
        title = p['short_title'] if 8 <= len(p['short_title']) <= 140 else ft
        title = re.sub(r'\s+', ' ', title).strip()
        if not title_year(title) and title_year(ft):
            title = f'{title} {title_year(ft)}'.strip()
        day, basis = p['commencement'], 'commencement'
        if not day:
            day, basis = p['enacted'], 'passed'
        if not day:
            issues.append([name, title, 'no Gregorian commencement or passing date printed in the English text: '
                           + (p['commencement_text'][:160] or 'no commencement clause found')])
            continue
        if day > today:
            issues.append([name, title, f'date {day} is after the build date'])
            continue
        acts.append({'file': name, 'url': item['url'], 'listed_title': item['title'], 'title': title,
                     'in_force': day, 'basis': basis, 'basis_text': p['commencement_text'] if basis == 'commencement' else p['enacted_text'],
                     'enacted': p['enacted'] or '', 'parsed': p})
    # duplicates: the same English text twice, or two files of one Act
    by_text = {}
    keep = []
    for a in sorted(acts, key=lambda a: (-len(a['parsed']['english_pages']), a['file'])):
        h = hashlib.sha256('\n'.join(u['text'] for u in a['parsed']['units']).encode()).hexdigest()
        if h in by_text:
            issues.append([a['file'], a['title'], f"same English text as {by_text[h]}; not built twice"])
            continue
        by_text[h] = a['file']
        keep.append(a)
    by_slug = {}
    acts = []
    for a in sorted(keep, key=lambda a: (-len(a['parsed']['english_pages']), a['file'])):
        slug = slugify(a['title'])
        if not title_year(slug) and a['in_force']:
            slug = f"{slug}-{a['in_force'][:4]}"
        if slug in by_slug:
            issues.append([a['file'], a['title'], f"another file of the same Act ({by_slug[slug]}) has more English pages; not built"])
            continue
        by_slug[slug] = a['file']
        a['slug'] = slug
        a['dir'] = f'acts/{slug}'
        acts.append(a)
    # amending Acts -> principal Act
    for a in acts:
        if re.search(r'amend?ment|amedment', a['title'] + ' ' + a['file'], re.I):
            a['amending'] = True
            b = base_name(a['title'])
            cands = [o for o in acts if o is not a and not re.search(r'amend?ment|amedment', o['title'], re.I)
                     and base_name(o['title']) == b and o['in_force'] <= a['in_force']]
            if cands:
                p = max(cands, key=lambda o: o['in_force'])
                a['principal'] = p['title']
                a['principal_dir'] = p['dir']
            else:
                a['principal'] = re.sub(r'\s*\(?\bAmend?ment\b\)?\s*', ' ', a['title'], flags=re.I).strip()
                a['principal_dir'] = ''
    acts.sort(key=lambda a: (a['in_force'], a['slug']))
    issues.sort()
    return acts, issues


# ---------------------------------------------------------------------------------------------------- write

def files_for(a: dict) -> dict[str, str]:
    p = a['parsed']
    files = {}
    order = []
    if p['front']:
        files[f"{a['dir']}/front.md"] = p['front']
        order.append('front.md')
    seen = {}
    for u in p['units']:
        stem = u['stem']
        if stem in seen:  # a repeated number (two "Article 3"): keep both, in order
            seen[stem] += 1
            stem = f'{stem}-{seen[stem]}'
        else:
            seen[stem] = 1
        files[f"{a['dir']}/{stem}.md"] = u['text']
        order.append(f'{stem}.md')
    files[f"{a['dir']}/index.txt"] = '\n'.join(order) + '\n'
    return files


def message(a: dict) -> tuple[str, str]:
    name = a['title']
    email = f"{a['slug']}@oag-gov-bt.invalid"
    subject = f"{name}: as enacted, in force {a['in_force']}"
    if len(subject) > 72:
        subject = f"{name[:60].rstrip()}...: as enacted"
    if a['basis'] == 'commencement':
        how = f"Dated by its commencement clause: \"{a['basis_text'][:240]}\""
    else:
        how = (f"The Act prints no commencement date that can be read (\"{(a['parsed']['commencement_text'] or 'no commencement clause')[:160]}\"), "
               f"so it is dated by the date of passing it prints: \"{a['basis_text'][:200]}\"")
    body = [f"The {name} as the Office of the Attorney General publishes it (English text), as enacted.", '',
            how, '']
    if a.get('amending'):
        body.append(f"It amends the {a['principal']}. Its changes are not applied to that Act's files here; they are listed in data/amendments.csv.")
        body.append('')
    trailers = [f"In-force: {a['in_force']}",
                f"In-force-basis: {'commencement clause' if a['basis'] == 'commencement' else 'date of passing (no commencement date printed)'}",
                'Kind: enacted', f"Law: {name}"]
    if a['enacted']:
        trailers.append(f"Passed: {a['enacted']}")
    if a.get('amending'):
        trailers.append(f"Amends: {a['principal']}")
    trailers.append(f"Source: {a['url']}")
    trailers.append(f"Source-sha256: {a['parsed']['sha256']}")
    msg = '\n'.join([subject, '', *body, *trailers]) + '\n'
    return f'{name} <{email}>', msg


class Writer:
    def __init__(self, repo: Path, ref: str = 'refs/heads/main'):
        self.p = subprocess.Popen(['git', '-C', str(repo), 'fast-import', '--quiet', '--force', '--done'],
                                  stdin=subprocess.PIPE)
        self.ref = ref
        self.mark = 0

    def commit(self, author: str, when: str, msg: str, files: dict[str, bytes]) -> None:
        w = self.p.stdin.write
        self.mark += 1
        w(f'commit {self.ref}\nmark :{self.mark}\n'.encode())
        w(f'author {author} {when}\ncommitter {COMMITTER} {when}\n'.encode())
        m = msg.encode('utf-8')
        w(f'data {len(m)}\n'.encode() + m + b'\n')
        if self.mark > 1:
            w(f'from :{self.mark - 1}\n'.encode())
        for path, data in sorted(files.items()):
            w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
        w(b'\n')

    def finish(self) -> None:
        self.p.stdin.write(b'done\n')
        self.p.stdin.close()
        if self.p.wait():
            sys.exit('git fast-import failed')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--only')
    args = ap.parse_args()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    acts, issues = load(args.only, args.today)
    amend = []
    for a in acts:
        a['units'] = len(a['parsed']['units'])
        amend += amendment_rows(a, a['parsed']['units'])
    amend.sort(key=lambda r: (r[4], r[3], r[5], r[1], r[2], r[6]))
    print(f"{len(acts)} Acts, {sum(a['units'] for a in acts)} units, {len(issues)} not built, {len(amend)} amendment rows", flush=True)

    import docs as docmod
    docs = docmod.render(acts, issues, amend, args.today)

    repo = args.repo
    if repo.exists() and any(repo.iterdir()):
        root = subprocess.run(['git', '-C', str(repo), 'log', '--format=%s', '--max-parents=0', 'HEAD'],
                              capture_output=True, text=True).stdout.strip()
        mine = subprocess.run(['git', '-C', str(repo), 'log', '-1', '--format=%ae', 'HEAD'], capture_output=True, text=True).stdout.strip()
        if not (root.endswith('sources, before any law') or mine == 'bhutan-law@lexifina.com' or root.endswith('as enacted, in force ' + (acts[0]['in_force'] if acts else ''))):
            sys.exit(f'{repo} holds something else; refusing to overwrite')
    repo.mkdir(parents=True, exist_ok=True)
    remote = None
    if (repo / '.git').exists():
        remote = subprocess.run(['git', '-C', str(repo), 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip() or None
        import os
        import shutil
        import stat

        def onerr(func, path, _):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        for child in repo.iterdir():
            shutil.rmtree(child, onerror=onerr) if child.is_dir() else child.unlink()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    for k, v in (('core.autocrlf', 'false'), ('core.longpaths', 'true')):
        subprocess.run(['git', '-C', str(repo), 'config', k, v], check=True)
    if remote:
        subprocess.run(['git', '-C', str(repo), 'remote', 'add', 'origin', remote], check=True)
    w = Writer(repo)
    seq = 0
    for a in acts:
        seq += 1
        author, msg = message(a)
        w.commit(author, git_date(a['in_force'], seq), msg, {k: v.encode('utf-8') for k, v in files_for(a).items()})
    fetched = (CACHE / 'fetched_on.txt').read_text().strip()
    msg = (f'Documentation: README, REPRODUCE, SOURCES, corpus.json, tools and data\n\n'
           f'Built from the OAG Depository of Laws as retrieved on {fetched}.\n\nIn-force: {fetched}\nKind: documentation\n')
    w.commit(COMMITTER, git_date(fetched, seq + 1), msg, docs)
    w.finish()
    subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-f', 'main'], check=True)
    head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(repo), 'rev-list', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip()
    print(f'built {repo}: {count} commits, head {head}', flush=True)


if __name__ == '__main__':
    main()
