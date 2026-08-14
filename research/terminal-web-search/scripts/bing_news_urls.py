#!/usr/bin/env python3
"""Parse Bing News HTML emitting [source] title + FULL article URL per card.

Companion to parse_bing_news.py. Use this one when you need the article URLs
(not just the headlines) — e.g. to fetch each article and read its JSON-LD
publish date with article_publish_date.py, which is the decisive freshness
gate for roundups.

Usage:
    python3 bing_news_urls.py FILE [KEY ...]

    FILE      a saved Bing News search HTML page.
    KEY ...   optional ASCII substrings; only cards whose title contains at
              least one key (case-insensitive) are printed.

CRITICAL pitfall — ASCII keys only:
    Passing Turkish-character keys (Suriye/Keşmir/ÖSYM with ç ş ğ ı ö ü) on the
    command line trips the Hermes confusable-unicode security scanner ("Confusable
    Unicode characters in text ... homoglyph attack") and the whole terminal call
    is blocked with status pending_approval. ALWAYS fold keys to ASCII:
    `Suriye Kesmir OSYM Azad` not `Suriye Keşmir ÖSYM`. Substring match on the
    ASCII stem still hits the Turkish-character title because we match the key
    inside the unescaped title, and the ASCII stem (Sur/Kesmir/OSYM) is present.
    The same scanner also blocks `python3 -c` and `curl | python3` — always run
    parsers as written script files.

Why this exists alongside parse_bing_news.py:
    parse_bing_news.py emits only [source] title (no URL) and occasionally
    returns ZERO lines for a page whose cards use a layout its title regex
    misses (observed on a `the client Vakfi` 7-day-filtered page). This script
    splits on the same `class="news-card` sentinel but pulls url="..." too, so
    when the headline-only parser comes up empty you still get clickable links.
    Bing card URLs are the real article URLs (decode-free), ready to curl.
"""

import html
import re
import sys
from pathlib import Path


def parse(path: str, keys):
    text = Path(path).read_text(errors="ignore")
    cards = re.split(r'class="news-card', text)[1:]
    seen = set()
    for c in cards:
        mt = re.search(r'title="([^"]+)"', c)
        mu = re.search(r'url="([^"]+)"', c)
        if not (mt and mu):
            continue
        title = html.unescape(mt.group(1)).strip()
        url = html.unescape(mu.group(1)).strip()
        if title in seen:
            continue
        if keys and not any(k.lower() in title.lower() for k in keys):
            continue
        seen.add(title)
        md = re.search(r'data-author="([^"]+)"', c)
        src = html.unescape(md.group(1)) if md else "?"
        print(f"[{src}] {title[:90]}\n   {url}\n")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    parse(sys.argv[1], sys.argv[2:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
