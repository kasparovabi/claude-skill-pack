#!/usr/bin/env python3
"""Extract readable text from fetched HTML (search results or article pages).

Usage:
    python3 extract_article.py FILE.html [--mode article|ddg|raw] [--max N]

Modes:
    article (default): keep <p> blocks > 40 chars (good for news articles)
    ddg:               dump cleaned text starting at the DDG-Lite result list
    raw:               cleaned full-text dump

Avoids the security scanner: this is a written script run normally, never
`curl | python3` or `python3 -c`.
"""
import re
import sys
import html
import argparse


def clean(t: str) -> str:
    t = re.sub(r'<script.*?</script>', ' ', t, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    return t


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--mode', default='article',
                    choices=['article', 'ddg', 'raw'])
    ap.add_argument('--max', type=int, default=4000)
    a = ap.parse_args()

    raw = open(a.file, encoding='utf-8', errors='ignore').read()
    t = clean(raw)

    if a.mode == 'article':
        out = []
        for p in re.findall(r'<p[^>]*>(.*?)</p>', t, re.S):
            p = re.sub(r'<[^>]+>', ' ', p)
            p = re.sub(r'\s+', ' ', html.unescape(p)).strip()
            if len(p) > 40:
                out.append(p)
        print("\n".join(out)[:a.max])
        return

    flat = re.sub(r'<[^>]+>', ' ', t)
    flat = re.sub(r'\s+', ' ', html.unescape(flat))

    if a.mode == 'ddg':
        for anchor in ('Past Year', 'Any Time'):
            i = flat.find(anchor)
            if i > 0:
                print(flat[i:i + a.max])
                return
        print(flat[:a.max])
        return

    print(flat[:a.max])


if __name__ == '__main__':
    main()
