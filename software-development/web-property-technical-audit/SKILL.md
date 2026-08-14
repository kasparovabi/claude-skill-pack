---
name: web-property-technical-audit
description: Audit web estate, verify vendor TLS/DNS/schema fixes.
---

# Web Property Technical Audit

Use when the work is *"is this organisation's web presence technically correct
and machine-readable"* — TLS, DNS, virtual hosts, robots/sitemap, schema.org,
llms.txt, hreflang, canonical duplication across near-identical domains. Also
use when a vendor reports a fix and someone has to confirm it independently,
or when asked why AI assistants describe an organisation with stale figures.

Distinct from `dogfood` (exploratory UI bug hunting) and `web-perf` (Chrome
performance profiling). This skill is about the machine-facing layer.

Deliverable shape that works: a **prioritised remediation list** (P0 broken /
P1 misrepresented / P2 structural), **ready-to-paste artifact files** the vendor
drops in without authoring anything, and a **verification script** the client
runs to close each item. Prose findings alone get argued with; a script that
prints FAIL does not.

---

## 1. Discovery before scoping — the estate is always bigger than stated

The highest-value finding in the reference case was a domain family the official
audit report never mentioned: the report scoped "two domain spellings, 33
country sites", and crawling the org's own country-listing page revealed a
**third** family covering 14 more countries — 47 sites, not 33. Four of them had
defects in categories the report had already opened items for.

Never inherit scope from the brief. Derive it:

```python
# harvest every external host the org itself links to, then group by domain
hepsi = re.findall(r"https?://([a-z0-9-]+)\.([a-z0-9.-]+\.[a-z]+)", html, re.I)
Counter(d.lower() for _, d in hepsi).most_common()   # families pop out by volume
```

Cross-check certificate transparency (crt.sh) *against* the org's own directory
page — CT shows what exists, the directory shows what they think exists. The
delta in both directions is a finding.

## 2. Two-request TLS method — separate "browser sees" from "server returns"

Request every host twice and diff the outcomes. This classifies every failure
mode without guessing:

```python
tarayici = curl(url)          # verification ON  -> what a visitor/crawler gets
sunucu   = curl(url, "-k")    # verification OFF -> what the server really serves
```

- ON fails, OFF returns another country's page → certificate mismatch *plus* a
  default virtual host catching the request. Two separate items.
- ON succeeds, body has empty `<title>` → content-management defect, not TLS.
- Both fail → host is dark; check DNS before writing it up as a TLS item.

Pull `subject` and `notAfter` with `openssl x509` and assert the CN actually
matches the host. "HTTP 200" alone does not prove the certificate is right.

## 3. Verification probes fail OPEN — design each one to fail closed

**This is the most expensive mistake in this class of work.** A harness that
reports PASS on unfixed infrastructure is worse than no harness, because it gets
forwarded to the vendor as sign-off.

Three of fifteen checks passed on the first run. All three were false:

| Probe | Why it falsely passed | Fix |
|---|---|---|
| "undefined subdomain must not return the default host" | invented hostnames have no DNS record, so the request never reached the server — empty response read as "correctly empty" | probe a host that **resolves** but is unconfigured (the real duplicate spellings) |
| "each country robots.txt must cite its own sitemap" | probed the *canonical* spelling, always correct; the broken ones were the twin spellings | probe the exact hosts the finding names, not the tidy ones |
| "certificates must be valid" | checked only the exit code of a verification-off request | assert CN/SAN match the hostname on a verification-**on** request |

Rules that generalise:

- **A probe must be able to fail.** Before trusting a PASS, point it at
  something known-broken and confirm it goes red. An assertion never observed
  failing is not an assertion.
- **Guard on reachability first.** `dig +short` the host; if it does not
  resolve, report *skipped* — never silently treat "no answer" as "clean".
- **Probe the exact entity in the finding.** If the finding says "the plural
  spelling is broken", testing the singular spelling proves nothing.
- **Empty/zero/absent is not success.** Distinguish "measured and found clean"
  from "could not measure".

`scripts/verify_remediation.py` is a working harness skeleton with these guards
built in — per-item functions returning `(bool, detail)`, a `dig` reachability
guard, the verify-on/verify-off pair, prefix filtering, and a summary line.

## 4. Every identifier you emit must be fetched before delivery

Generated schema.org / config / documentation is *exactly* where plausible
fabrications hide: the shape is right and nothing crashes. In the reference case
two invented values shipped into a JSON-LD block:

- `"https://www.wikidata.org/wiki/Q28453102"` — well-formed, wrong entity. The
  real ID was `Q25478112`, resolved via the Wikidata `wbsearchentities` API.
- `"https://example.org/logo.png"` — the conventional path, HTTP 404. The real
  asset lived under an upload-hash path found by grepping the homepage.

A third bad URL was copied from the *client's own site* (a social link with
non-ASCII characters, 404) — so lifting from the source is not safe either.

Make it mechanical: after writing any artifact, extract every URL and fetch it.

```python
urls = sorted(set(re.findall(r"https://[^\s)>\"']+", open(artifact).read())))
# fetch concurrently, print anything that is not 200
```

Do the same for non-URL identifiers (entity IDs, ISO codes) — resolve through
the authoritative API, never from recall. Then re-validate: `json.loads` every
JSON-LD block after edits, with template placeholders substituted so it parses.

## 5. Long scans: chunk them yourself

Auditing dozens of hosts sequentially will blow a foreground timeout. When it
did, telling the user to break the request into smaller pieces drew a sharp
correction — **that is the operator's job, not theirs.** Never answer your own
long-running work with "ask me in smaller steps".

Instead:
- `ThreadPoolExecutor(max_workers=6..10)` for independent host probes, with a
  per-request `--max-time` so one dead host cannot stall the batch.
- Anything still long goes `background=true`, then poll — write results to a log
  file so a timeout loses nothing.
- Split by priority prefix (P0, then P1) so partial results stay useful.

## 6. Artifacts the vendor can paste without thinking

Ship files, not instructions. Proven set:

- `llms.txt` — one-paragraph definition, current figures **each carrying a
  validity date**, legal basis, authoritative page list, canonical site list.
- `robots.txt` — one for the main site, one **template** for sub-sites with the
  sitemap host as a variable plus a comment stating it must be derived from the
  site's own hostname, never hard-coded (hard-coding caused the original defect).
- Three JSON-LD blocks — organisation, per-location, per-article — each in its
  own file with placement comments and one fully worked example so the vendor
  can see the template applied correctly.
- `hreflang` template showing **reciprocal** tagging plus `x-default`.

Mark every value that must come from a single source of truth rather than being
typed onto the page. Per-page typed figures are how section 7 happens.

## 7. Separate technical defects from decisions only the client can make

Some findings are not the vendor's to fix and must be flagged, or the list
stalls. In the reference case the org's own site stated two different
institution counts on two pages, plus a third number in body copy. No amount of
schema.org work makes "figures must come from one source" true while the source
disagrees with itself.

Put these in a closing *"pending an internal decision"* section. It stops the
vendor list blocking on something the vendor cannot resolve.

## Pitfalls

- **Reporting a baseline as an achievement.** Running the harness before any
  work gives all-fail; label it the *baseline* so a later run has a comparison.
- **`curl` exit 60 vs 28.** 60 is certificate rejection (a finding), 28 is
  timeout (possibly your network). Do not merge them into one error label.
- **`-L` follow-redirects hides the redirect you are verifying.** For any "must
  return 301 to X" check, request with `-I` and **no** `-L`, then read
  `Location` yourself.
- **A sitemap with one distinct `lastmod` equal to request time** means it is
  regenerated per request; count `len(set(lastmod))`, not field presence.
- **Menu labels are not features.** Language-switcher labels rendered in HTML
  while every `/en`, `/ar` path 404s is a broken-link defect *today*, separate
  from the translation project.

## Reference

`references/maarif-web-audit-2026-08.md` — the full case: domain families, the
default-vhost mirror map, exact false-PASS diagnoses, and the fabricated
identifier incident with how each was resolved.
