# How this repository was made (Bhutan)

This file is written by the build on 2026-10-30, the day the source data was retrieved.

## Sources

| Source | Address | Retrieved | Licence |
| --- | --- | --- | --- |
| Office of the Attorney General of Bhutan, Depository of Laws | <https://oag.gov.bt/?page_id=7854> | 2026-10-28 | Official legislative texts are excluded from copyright by section 7(b) of the Copyright Act of the Kingdom of Bhutan, 2001. |

Every word of law in this repository comes from these sources. Lexifina reads them and records each act's dated versions, and the laws that made each change, in one corpus file. This repository is built from that file.

## What is in it

| Act | Title | Versions | Span |
| --- | --- | ---: | --- |
| `constitution` | The Constitution of the Kingdom of Bhutan | 1 | 2008-07-18 to 2008-07-18 |
| `penal-code` | The Penal Code of Bhutan, 2004 | 1 | 2004-08-11 to 2004-08-11 |
| `civil-criminal-procedure` | The Civil and Criminal Procedure Code of Bhutan, 2001 | 1 | 2001-07-23 to 2001-07-23 |
| `contract-act` | The Contract Act of Bhutan, 2013 | 1 | 2013-03-14 to 2013-03-14 |

The build made 4 commits:

| Commits | Kind |
| ---: | --- |
| 4 | first version of an act |
| 0 | one law on its in-force day |
| 0 | changes no amendment note explains, credited to the publisher |

Other counts:
- 0 commits on the branch `future`: laws not yet in force on 2026-10-30.
- 0 commits dated 1 January 1970: in force before 1970, with the real day in their `In-force` trailer.
- 4 laws in the record.
- 8 tags.

## Dates

Each commit is dated at noon (Asia/Thimphu) on the day the change took effect. The other dates, enacted and published, are trailers.

When a law gives no date of its own, the default rule applies: No general rule is applied: each Act is dated by the commencement or adoption date printed in its own text. https://oag.gov.bt/?page_id=7854

## How the history is built

`tools/build.py` turns the corpus into this history in one pass: one commit per law, on the day it took effect. The same corpus always gives the same commit hashes. `tools/check_repo.py` reads every version back from git and compares it with the corpus. `tools/on.py` shows the law as it stood on any date. The corpus format is described in `tools/SCHEMA.md`.

- Corpus: sha256 `0321ffc7a9862e7a48387acdc67814abd5122efcc812d227784d00bb7bebe79e` (529942 bytes).
- Builder blob hashes (`git hash-object`): `build.py` `a4faa25af85facb64b956b372f6b528aafdd7ec1`, `check.py` `3e59cb6f05eccb94a9ec14431a7f6781221e83ef`, `on.py` `644a6c0857fbcc72562032b58d57aa113fee0641`.
- Python 3.12.10; git version 2.46.0.windows.1.

## Checks

Not yet run for this build.

No second build of this corpus has been compared yet.

## Decisions made by hand

- The Constitution of the Kingdom of Bhutan: dated 2008-07-18. Preamble: adopted on the Fifteenth Day of the Fifth Month of the Male Earth Rat Year, corresponding to the Eighteenth Day of July, 2008.
- The Penal Code of Bhutan, 2004: dated 2004-08-11. Section 1(b): comes into force on the Male Wood Monkey, Sixth Month, the Third Day, corresponding to the Eleventh Day of August, 2004.
- The Civil and Criminal Procedure Code of Bhutan, 2001: dated 2001-07-23. Commencement clause: comes into force in the Female Iron Snake Year, Sixth Month, the Third Day, corresponding to the Twenty-Third day of July, 2001.
- The Contract Act of Bhutan, 2013: dated 2013-03-14. Preamble: enacted on the 20th Day of February, 2013; section 1(2): comes into force on the 3rd Day of the 2nd Month of the Water Female Snake Year, corresponding to the 14th Day of the 3rd Month of 2013.
- Each Act is one version, as enacted, read from the English PDF of the Office of the Attorney General's Depository of Laws. The Office publishes no consolidated texts and no amendment is applied: later amending Acts (for example the Penal Code Amendment Acts 2011 and 2021 and the Civil and Criminal Procedure Code Amendment Acts 2011 and 2021) exist as separate PDFs and are not built in this first pass, so the Penal Code and the Procedure Code here are the oldest versions available, not the text in force today.
- The Constitution has not been amended; it is the text adopted on 18 July 2008. The Bhutanese-calendar part of each date is not converted; only the Gregorian date the text itself gives is used.
- The Penal Code's Dzongkha text is authoritative if the two differ (Penal Code s. 514); only the English text is built here. Section 7(b) of the Copyright Act 2001 excludes official texts of a legislative, administrative or legal nature from copyright protection (see LICENSE).
- Unit headings (chapter and margin headings) are kept as heading lines inside the section that follows them. The Constitution's final article includes its glossary of terms.

## What AI did and did not do

The scripts that read the sources and build this repository were written by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`) under Lexifina's direction.

No model wrote, translated or corrected legal text. No model runs at build time. Every word of law in this repository comes from the official sources above.

The commit messages are written by `build.py` from the source data.

Model use at data-build time:
- none for the legal text. A model (Claude Sonnet 5.5, claude-sonnet-5-5) chose the four Acts and wrote Lexifina's code; the dates were read from each Act's own commencement clause.
