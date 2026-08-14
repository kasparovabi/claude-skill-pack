#!/usr/bin/env python3
"""Parse Bing News search result HTML into [source] title lines.

Usage:
    python3 parse_bing_news.py FILE [FILE ...]

Workflow:
    1. curl -sL "https://www.bing.com/news/search?q=QUERY&setmkt=tr-TR" \\
            -A "Mozilla/5.0 ..." -o /tmp/bing.html
       Rotate UA per file when fetching several locales (en-US, fr-FR, ar-SA, es-ES).
    2. python3 parse_bing_news.py /tmp/bing.html

Each Bing news result is wrapped in <... class="news-card ..."> with:
    - title="..."           full headline
    - data-author="..."     publisher name
    - data-time="..."       relative time (often missing / unreliable, see SKILL.md)

We split on the class="news-card sentinel because the surrounding tag varies
(div, a, news-card-body). title="" is preferred over inner anchor text because
the inner text is sometimes a truncated snippet.

Pitfalls:
    - data-time values like "5h" / "7 jours" are unreliable — do not present
      them as proof of "this week". See SKILL.md.
    - When the filtered news vertical (`&qft=interval%3d%222%22`) returns
      ZERO cards, that does NOT mean no recent coverage exists. Re-run
      WITHOUT the filter before claiming a topical gap.
    - For niche institutional queries (e.g. specific TR foundation names),
      one well-chosen Bing News query often beats fighting DDG Lite's
      duck-CAPTCHA. Try Bing News first for proper-noun lookups.
"""

import html
import re
import sys
from pathlib import Path


def parse(path: str) -> list[tuple[str, str, str]]:
    text = Path(path).read_text(errors="ignore")
    cards = re.split(r'class="news-card', text)[1:]
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for c in cards:
        m_title = re.search(r'title="([^"]+)"', c) or re.search(r">([^<]{30,200})</a>", c)
        if not m_title:
            continue
        t = html.unescape(m_title.group(1)).strip()
        if len(t) < 25 or t in seen:
            continue
        seen.add(t)
        src = (re.search(r'data-author="([^"]+)"', c) or [None, "?"])[1]
        date = (re.search(r'data-time="([^"]+)"', c) or [None, ""])[1]
        out.append((src, t, date))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    for f in sys.argv[1:]:
        print(f"\n==== {f} ====")
        for src, title, date in parse(f):
            stamp = f" ({date})" if date else ""
            print(f"[{src}]{stamp} {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
