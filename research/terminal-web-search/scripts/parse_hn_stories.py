#!/usr/bin/env python3
"""
Parse a Hacker News Algolia API response into a ranked, timestamped story list.

Fetch first (see SKILL.md "Hacker News Algolia API"):
    NOW=$(date -u +%s); SINCE=$((NOW - 86400))
    curl -sL "https://hn.algolia.com/api/v1/search_by_date?tags=story\
&numericFilters=created_at_i%3E${SINCE},points%3E60&hitsPerPage=70" -o hn.json

Then:
    python3 parse_hn_stories.py hn.json
    python3 parse_hn_stories.py hn.json --min-points 150
    python3 parse_hn_stories.py hn.json --match ai,llm,model --urls-only

Output: `points | MM-DD HH:MM UTC | title` with the URL indented beneath.
Sorted by points descending so the highest-signal stories are read first.
"""

import argparse
import datetime
import json
import sys


def load_hits(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("hits", [])
    return data if isinstance(data, list) else []


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("path", help="saved Algolia JSON response")
    ap.add_argument("--min-points", type=int, default=0)
    ap.add_argument("--match", default="",
                    help="comma-separated keywords; keep titles containing any "
                         "(case-insensitive). Use ASCII stems to avoid the "
                         "confusable-unicode scanner blocking the call.")
    ap.add_argument("--urls-only", action="store_true")
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()

    try:
        hits = load_hits(a.path)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR reading {a.path}: {e}", file=sys.stderr)
        return 2

    keys = [k.strip().lower() for k in a.match.split(",") if k.strip()]
    rows = []
    for h in hits:
        pts = h.get("points") or 0
        if pts < a.min_points:
            continue
        title = (h.get("title") or h.get("story_title") or "").strip()
        if not title:
            continue
        if keys and not any(k in title.lower() for k in keys):
            continue
        ts = h.get("created_at_i")
        when = (datetime.datetime.utcfromtimestamp(ts).strftime("%m-%d %H:%M")
                if ts else "??-?? ??:??")
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
        rows.append((pts, when, title, url, h.get("num_comments") or 0))

    rows.sort(key=lambda r: r[0], reverse=True)
    rows = rows[: a.limit]

    if not rows:
        print("No stories matched. Widen --min-points / --match, or the time "
              "window in the curl (created_at_i bound) may be too narrow.")
        return 1

    for pts, when, title, url, ncom in rows:
        if a.urls_only:
            print(url)
            continue
        print(f"{pts:5d} | {when} UTC | {title[:112]}")
        print(f"        {url[:135]}   ({ncom} comments)")

    if not a.urls_only:
        print(f"\n{len(rows)} stories. NOTE: the timestamp is the HN SUBMISSION "
              "time, not the article's publish date -- confirm the story's own "
              "date with article_publish_date.py before citing it as fresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
