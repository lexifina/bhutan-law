"""Bhutan first build: a few core Acts as enacted, from the cached OAG PDFs -> corpus.json (scripts/gitlaw_common/SCHEMA.md).

    python -X utf8 scripts/bhutan-law/make_corpus.py

Reads only .cache (fetch.py filled it). Parsing is build.read_act (extract.py, parse.py, dates.py): deterministic, no model.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

LISTING = {x["file"]: x["url"] for x in json.loads((build.CACHE / "acts.json").read_text("utf-8"))}

ACTS = [
    # slug, short, title, law key, label, file, from, enacted, date source text
    ("constitution", "Constitution", "The Constitution of the Kingdom of Bhutan", "constitution-2008",
     "Constitution 2008", "Constitution_of_Bhutan.pdf", "2008-07-18", "2008-07-18",
     "Preamble: adopted on the Fifteenth Day of the Fifth Month of the Male Earth Rat Year, corresponding to the Eighteenth Day of July, 2008."),
    ("penal-code", "Penal Code", "The Penal Code of Bhutan, 2004", "penal-code-2004",
     "Penal Code 2004", "Penal-Code-of-Bhutan-2004_English-version_.pdf", "2004-08-11", "2004-08-11",
     "Section 1(b): comes into force on the Male Wood Monkey, Sixth Month, the Third Day, corresponding to the Eleventh Day of August, 2004."),
    ("civil-criminal-procedure", "CCPC", "The Civil and Criminal Procedure Code of Bhutan, 2001", "ccpc-2001",
     "Civil and Criminal Procedure Code 2001", "Civil-and-Criminal-Procedure-Code-of-Bhutan-2001English-version0.pdf",
     "2001-07-23", "2001-07-23",
     "Commencement clause: comes into force in the Female Iron Snake Year, Sixth Month, the Third Day, corresponding to the Twenty-Third day of July, 2001."),
    ("contract-act", "Contract Act", "The Contract Act of Bhutan, 2013", "contract-act-2013",
     "Contract Act 2013", "Contract-Act-of-Bhutan-2013.pdf", "2013-03-14", "2013-02-20",
     "Preamble: enacted on the 20th Day of February, 2013; section 1(2): comes into force on the 3rd Day of the 2nd Month of the Water Female Snake Year, corresponding to the 14th Day of the 3rd Month of 2013."),
]


def norm(s):
    s = s.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", " ": " "}))
    return re.sub(r"[ \t]+", " ", s).strip()


def key_of(stem):
    m = re.fullmatch(r"(section|article)-(\d+)([a-z]*)", stem.lower())
    if not m:
        raise SystemExit("odd stem " + stem)
    return ("sec" if m.group(1) == "section" else "art") + f"-{int(m.group(2)):03d}" + (("-" + m.group(3)) if m.group(3) else "")


acts, laws, decisions = [], {}, []
for slug, short, title, lk, label, fn, frm, enacted, why in ACTS:
    p = build.read_act(build.PDFS / fn)
    units = {}
    if p["front"].strip():
        units["front"] = {"label": "Title and preamble", "kind": "preamble", "text": "# Title and preamble\n" + norm(p["front"]) + "\n"}
    for u in p["units"]:
        k = key_of(u["stem"])
        if k in units:
            raise SystemExit("duplicate " + k)
        text = "\n".join(norm(l) for l in u["text"].splitlines() if l.strip())
        if u["stem"].startswith("article-"):
            text = re.sub(r"^## (Article \d+)\n(.+)\n", r"# \1 - \2\n", text, count=1)
        else:
            text = "\n".join(l.replace("## ", "# ") for l in text.splitlines())
        units[k] = {"label": ("Article " if k.startswith("art") else "Section ") + u["label"],
                    "kind": "art" if k.startswith("art") else "sec", "text": text + "\n"}
    acts.append({"slug": slug, "short": short, "title": title, "url": LISTING[fn], "first_law": lk, "earlier_laws": [],
                 "versions": [{"from": frm, "source_url": LISTING[fn], "sha256": p["sha256"], "units": units, "credits": {}}]})
    laws[lk] = {"label": label, "title": title, "kind": "law", "enacted": enacted, "published": None, "url": LISTING[fn],
                "temporary_until": None, "restores": None, "note": None}
    decisions.append(f"{title}: dated {frm}. {why}")

decisions += [
    "Each Act is one version, as enacted, read from the English PDF of the Office of the Attorney General's Depository of Laws. The Office publishes no consolidated texts and no amendment is applied: later amending Acts (for example the Penal Code Amendment Acts 2011 and 2021 and the Civil and Criminal Procedure Code Amendment Acts 2011 and 2021) exist as separate PDFs and are not built in this first pass, so the Penal Code and the Procedure Code here are the oldest versions available, not the text in force today.",
    "The Constitution has not been amended; it is the text adopted on 18 July 2008. The Bhutanese-calendar part of each date is not converted; only the Gregorian date the text itself gives is used.",
    "The Penal Code's Dzongkha text is authoritative if the two differ (Penal Code s. 514); only the English text is built here. Section 7(b) of the Copyright Act 2001 excludes official texts of a legislative, administrative or legal nature from copyright protection (see LICENSE).",
    "Unit headings (chapter and margin headings) are kept as heading lines inside the section that follows them. The Constitution's final article includes its glossary of terms.",
]
meta = {
    "country": {"code": "BT", "name": "Bhutan", "slug": "bhutan", "lang": "en", "tz": "Asia/Thimphu", "future_branch": "future",
                "publisher": {"name": "Office of the Attorney General of Bhutan", "email": "oag@oag.gov.bt.invalid"},
                "default_in_force_rule": {"text": "No general rule is applied: each Act is dated by the commencement or adoption date printed in its own text.",
                                          "source": "https://oag.gov.bt/?page_id=7854"},
                "licence_note": "Section 7(b), Copyright Act of the Kingdom of Bhutan, 2001: no protection extends to any official text of a legislative, administrative or legal nature. Source: Office of the Attorney General, Depository of Laws."},
    "sources": [{"name": "Office of the Attorney General of Bhutan, Depository of Laws", "url": "https://oag.gov.bt/?page_id=7854",
                 "retrieved": "2026-10-28", "licence": "Official legislative texts are excluded from copyright by section 7(b) of the Copyright Act of the Kingdom of Bhutan, 2001.",
                 "notes": "English PDFs with a text layer, as enacted; no consolidated text."}],
    "laws": laws, "acts": acts, "applies": [], "decisions": decisions,
    "ai_use": ["none for the legal text: extract.py, parse.py and dates.py are deterministic code over the cached PDFs (PyMuPDF text layer). A model (Claude Sonnet 5.5, claude-sonnet-5-5) chose the four Acts and wrote make_corpus.py; the dates were read from each Act's own commencement clause."],
}
(HERE / "corpus.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", "utf-8", newline="\n")
print({a["slug"]: len(a["versions"][0]["units"]) for a in acts})
