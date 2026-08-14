#!/usr/bin/env python3
"""check_dep.py — ponytail rung 4 ethics gate.

Before adding a NEW dependency, check its provenance: who ships it, what
ecosystem it belongs to, and whether it trips a banned-ecosystem flag.
Two reasons to avoid a new dep here: (1) ponytail's "a few lines beats a
package" rule, (2) this environment forbids whole tech families on ethical
grounds (the Vercel/Next.js ecosystem among them).

This is a HEURISTIC, not a verdict. A flag means "stop and verify by hand,"
never "this is definitely banned." The banned list is static and incomplete
by design — provenance moves faster than any hardcoded list.

Usage:
    python3 check_dep.py <package> [--npm | --pypi]
    # default: try both registries

Exit 0 = looks clean, 1 = flagged (verify), 2 = lookup failed.
"""
import json
import sys
import urllib.error
import urllib.request

# Known ecosystems to avoid here, with the reason. Substring match on the
# package name OR its repo/author URL. Extend as you learn more — this is a
# living list, not gospel.
FLAGS = {
    "next": "Vercel/Next.js ecosystem (banned here)",
    "@vercel": "Vercel ecosystem (banned here)",
    "vercel": "Vercel (banned here)",
    "swr": "Vercel-maintained (banned here)",
    "turbo": "Vercel Turborepo (banned here)",
    "turborepo": "Vercel Turborepo (banned here)",
    "geist": "Vercel design system (banned here)",
    "@next/": "Next.js ecosystem (banned here)",
    "sveltekit": "Rauch/Vercel-adjacent — verify before use",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ponytail-check"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def from_pypi(name):
    info = fetch(f"https://pypi.org/pypi/{name}/json")["info"]
    urls = " ".join(filter(None, [
        info.get("home_page", ""),
        info.get("author", ""),
        *(info.get("project_urls") or {}).values(),
    ]))
    return {"name": name, "registry": "pypi",
            "author": info.get("author") or "?", "haystack": (name + " " + urls).lower()}


def from_npm(name):
    d = fetch(f"https://registry.npmjs.org/{name}")
    repo = (d.get("repository") or {})
    maint = ", ".join(m.get("name", "") for m in (d.get("maintainers") or []))
    haystack = " ".join([name, repo.get("url", ""), maint]).lower()
    return {"name": name, "registry": "npm",
            "author": maint or "?", "haystack": haystack}


def flagged(haystack):
    for needle, reason in FLAGS.items():
        if needle in haystack:
            return reason
    return None


def check(name, registry=None):
    fns = {"pypi": from_pypi, "npm": from_npm}
    order = [registry] if registry else ["pypi", "npm"]
    last_err = None
    for reg in order:
        try:
            return fns[reg](name)
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as e:
            last_err = e
    raise SystemExit(f"[check_dep] lookup failed for '{name}': {last_err}") from None


def main(argv):
    if len(argv) < 1:
        print(__doc__)
        return 2
    name = argv[0]
    registry = None
    if "--npm" in argv:
        registry = "npm"
    elif "--pypi" in argv:
        registry = "pypi"
    info = check(name, registry)
    reason = flagged(info["haystack"])
    print(f"package : {info['name']} ({info['registry']})")
    print(f"author  : {info['author']}")
    if reason:
        print(f"FLAG    : {reason}")
        print("verdict : STOP — verify by hand before adding. Prefer a few lines or a clean alternative.")
        return 1
    print("verdict : no known flag. Still ask: do a few lines beat this package? (ponytail rung 4)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
