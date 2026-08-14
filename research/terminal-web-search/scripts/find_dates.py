#!/usr/bin/env python3
"""Scan fetched HTML for publish dates to verify article freshness.

Usage:
    python3 find_dates.py FILE [FILE ...]

Why this exists:
    "This week" / dated-list roundups (e.g. the the client morning news job) must
    confirm a headline falls inside the requested window BEFORE including it.
    Bing/AA/haberler.com listing HTML rarely carries clean machine-readable
    dates, and search engines surface evergreen/stale results that read as
    fresh. This probe pulls every date-shaped token out of a page so you can
    eyerball whether the coverage is actually recent.

What it finds (per file, deduped + counted):
    - TR long dates:  "15 Mayis 2026", "3 Subat 2026" (handles ı/ş/ç/ğ variants)
    - DD.MM.YYYY:     "03.02.2026"  (haberler.com tag pages stamp each card)
    - ISO:            "2026-05-31"
    - Bing data-time: relative ("5h") — UNRELIABLE, shown but never trust alone
    - TR relative:    "2 gun once", "5 saat once"

Decision rule (see SKILL.md "honesty discipline"):
    - Only keep a headline if a confirmed date lands in the requested window.
    - If the only dates found are older than the window -> DROP the item,
      even if a search engine listed it as a top/"recent" result.
    - If NO date is found and you cannot cross-confirm freshness from a second
      source -> DROP it (or label it explicitly as undated). Never present an
      undated headline as "this week".

Pitfall — security scanner:
    Do NOT inline this logic as `python3 -c "..."` and do NOT pipe
    `curl ... | python3`. Both are blocked. Also, grepping a file for Turkish
    month names mixed with ASCII regex can trip the confusable-unicode scanner.
    Running THIS script as a file (python3 find_dates.py page.html) sidesteps
    both problems — the Turkish chars live in the file, not the shell arg.

To check a specific stale-vs-fresh candidate on a tag/index page, point this at
the saved page; to inspect the date next to one headline, grep the keyword's
char offset and slice +/-300 chars, then re-run the regexes on that slice.
"""

import html
import re
import sys
from collections import Counter
from pathlib import Path

TR_MONTHS = (
    r"Ocak|Subat|\u015eubat|Mart|Nisan|Mayis|May\u0131s|Haziran|Temmuz|"
    r"Agustos|A\u011fustos|Eylul|Eyl\u00fcl|Ekim|Kasim|Kas\u0131m|Aralik|Aral\u0131k"
)


def scan(path: str) -> None:
    try:
        t = html.unescape(Path(path).read_text(errors="ignore"))
    except Exception as e:  # noqa: BLE001
        print(f"== {path} == ERR {e}")
        return
    tr = re.findall(rf"(\d{{1,2}}\s+(?:{TR_MONTHS})\s+20\d{{2}})", t, re.I)
    dmy = re.findall(r"\d{1,2}\.\d{1,2}\.20\d{2}", t)
    iso = re.findall(r"20\d{2}-\d{2}-\d{2}", t)
    times = re.findall(r'data-time="([^"]*)"', t)
    rels = re.findall(r"\d+\s+(?:saat|gun|g\u00fcn|dakika|hafta)\s+once", t, re.I)
    print(f"== {path} ==")
    if tr:
        print("  TR-dates:", Counter(tr).most_common(8))
    if dmy:
        print("  DD.MM.YYYY:", Counter(dmy).most_common(8))
    if iso:
        print("  ISO:", Counter(iso).most_common(8))
    if times:
        print("  data-time (UNRELIABLE):", times[:8])
    if rels:
        print("  TR-relative:", rels[:8])
    if not (tr or dmy or iso or times or rels):
        print("  (no dates found -> treat as undated, do not claim 'this week')")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for f in sys.argv[1:]:
        scan(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
