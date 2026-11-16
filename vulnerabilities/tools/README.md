# Tools

The scripts behind this Bhutan-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/bhutan-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only bhutan-law and its commit.
`build_vulns.py`, `flags_chart.py`, `late_ext_select.py` and `late_ext_rebut.py` sit two folders above the scripts, next to
`config.json`.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps paths to the folders since the move (`map_moved.py`), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `map_moved.py` | Rewrites the paths in the history table to each Act's folder since the move of 10 November 2026 (`data/paths.json`, for example `anti-corruption-act-2011/` to `act/2011/anti-corruption/`), so that an Act's history is not split in two at the move; `run.sh` runs it after the history is indexed |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods (none of them had a flag here) |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (there were none here) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the README, in English, light and dark |
| `config.json` | The repository, its language (English), the category names, the paths that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `patch_detectors_vi.py` | The same for Vietnamese dates, references and amounts (found by the Vietnam run); it changes nothing here, but `redo.py` runs it on every repository |
| `patch_es.py` | The same for Spanish dates and for "marco" and "escudo" read as currencies; it changes nothing here either |
| `patch_en.py` | The English fixes made for this repository, in the same form (`python -X utf8 patch_en.py <scripts dir>`; see below); `redo.py` does not run it, so run it first |
| `redo.py` | Runs the three patches above it, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`, `map_moved.py` among them, sends every category to the model and keeps every review already made; `EMBED_FONTS` names the script that embeds the chart's fonts); not needed here, as the fixes were in place before the first run |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data|tools|vulnerabilities)/'`; it found nothing to review.

Changes made for this repository:

- `pins.json` names the corpus language as `en` (global-law's list of corpora gave none), so the detectors use the English
  month names and the English currency exceptions. `add_root.py` is unchanged: the 99 commits that make a version carry `Kind: law`,
  and the two that moved the Act folders `Kind: documentation`, which is left out.
- `detectors/placeholder_ref.py` (`patch_en.py`) no longer reads "vacation" or "vacate" ("Upon vacation of seat by a
  member", "Where a tenant wishes to vacate the rental unit") or "null and void" as the mark of a repealed section: "vacat"
  became "vacated" and "void" no longer counts after "null and". A section that says another section "is repealed" ("9. In
  the Code, Section 14.1 is repealed.") is now, like one that "repeals the …", the repealing provision, not a placeholder:
  an amending Act's own sections were read that way when its references to the Act it amends ("Section 9 (d)") were taken
  for its own sections. References to repealed placeholders went from 24 to 0; dead fines, which use the same test, stayed
  at 0.
- `config.json` counts as not law `data/`, `tools/`, `vulnerabilities/`, the root files and every `README.md` (each Act's
  list of its files, and all that the folder of a repealed Act keeps).
- `build_vulns.py` writes no second category column when the repository's language is English (`category_en` would repeat
  `category`), and `flags_chart.py` draws one set of charts, in English, instead of writing the same files twice; its title
  also reads "1 flag in one category" rather than "1 flags in one categories".
- The kit's twelfth round of `patch_detectors.py` (Croatian "brisan" as a whole word) came after the first run; applied, it
  left every count as it was.
