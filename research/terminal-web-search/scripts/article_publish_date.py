#!/usr/bin/env python3
"""Extract the authoritative publish/modify date from a fetched article's HTML.

Why: Bing/haberler/AA listing pages give aggregate, page-level date tokens
(find_dates.py) that conflate many cards. To confirm ONE headline falls inside
a freshness window, fetch that article and read its structured-data timestamp.
JSON-LD datePublished / OG article:published_time / <time datetime> are the
reliable fields; the visible "last updated" stamp on a page is NOT.

Usage:
    curl -sL "ARTICLE_URL" -A "Mozilla/5.0 ..." -o /tmp/art.html
    python3 article_publish_date.py /tmp/art.html [/tmp/art2.html ...]

Proven on: haberturk.com, trthaber.com article pages (TR news). Most TR/EN
outlets embed JSON-LD; if nothing prints, the page is JS-rendered or paywalled
-> cross-check the date from a second outlet instead of trusting the listing.
"""
import re
import sys

PATTERNS = [
    ('json-ld datePublished', r'"datePublished"\s*:\s*"([^"]+)"'),
    ('json-ld dateModified', r'"dateModified"\s*:\s*"([^"]+)"'),
    ('og published_time', r'property="article:published_time"\s+content="([^"]+)"'),
    ('meta publish-date', r'name="publish[-_]?date"\s+content="([^"]+)"'),
    ('time datetime', r'<time[^>]*datetime="([^"]+)"'),
]


def main():
    if len(sys.argv) < 2:
        print("usage: article_publish_date.py FILE [FILE ...]")
        sys.exit(1)
    for f in sys.argv[1:]:
        try:
            t = open(f, encoding='utf-8', errors='ignore').read()
        except OSError as e:
            print(f"==== {f}\n  (could not read: {e})")
            continue
        print(f"==== {f}")
        found = False
        for label, pat in PATTERNS:
            for m in re.findall(pat, t)[:2]:
                print(f"  {label:24s} -> {m}")
                found = True
        if not found:
            print("  (no structured publish date -> JS-rendered/paywalled; "
                  "cross-check date from a second outlet, do not trust listing)")


if __name__ == '__main__':
    main()
