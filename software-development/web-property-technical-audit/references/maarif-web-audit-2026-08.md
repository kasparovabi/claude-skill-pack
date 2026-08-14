# Case study — the client web estate audit, August 2026

Session-specific record behind `web-property-technical-audit`. Names kept
because the patterns are easier to reason about with the concrete shape.

## Task shape

Client handed over two PDFs produced by an earlier audit (a findings report and
a 16-item vendor remediation list) and asked for them to be absorbed into
memory. The useful work turned out to be everything *after* that: independently
re-measuring, finding what the report missed, producing paste-ready artifacts
for the vendor, and building a harness to verify future "we fixed it" claims.

Lesson: "store these documents" briefs frequently contain a much larger implied
task. Re-measuring the claims in a handed-over report is cheap and repeatedly
found things the report's authors missed.

## Finding 1 — a whole domain family outside the stated scope

The report scoped the estate as two near-identical spellings:
`maarifschool.org` (singular) and `maarifschools.org` (plural), 33 country
sites. Harvesting every external link from the org's own country directory page
and grouping by registrable domain produced:

```
244  maarifschools.org
 97  maarifschool.org
 67  ecolesmaarif.org      <- never mentioned in the audit report
  9  maarif.be
  4  maarifeducationfrance.fr
  3  maarif.org.au / maarif.at / maarif.ro ...
```

`ecolesmaarif.org` carried 14 Francophone-Africa countries: bf, bi, cd, cg, ci,
dj, ga, gn, ml, mr, ne, sn, td, tg. So the real estate was 47 country sites, not
33. Measuring them found defects in categories the report had already opened
items for — two empty `<title>`s (bf, td), one certificate failure (bi), one
host fully dark (mr) — meaning three existing remediation items were
under-scoped and one country was invisible on the internet entirely.

Also notable: 10 of the 14 sites in this family had *correct* per-site sitemap
declarations in robots.txt, proving the default-vhost defect was confined to the
other two families. Scope discovery narrowed the diagnosis as well as widening
the item list.

## Finding 2 — default virtual host mirror map

The report correctly diagnosed a default virtual host pointed at the Ethiopia
site. Probing every singular/plural twin pair produced the exact map:

| prefix | singular (`maarifschool.org`) | plural (`maarifschools.org`) |
|---|---|---|
| sl, et, ge, gm, hu, pk, ro, so, tn, tz, erbil | 200, correct country | TLS reject, Ethiopia content behind it |
| za | 200 but **empty `<title>`** | 200, correct "South Africa the client Schools" |
| gh | 200, correct | no title, Ethiopia does not appear — behaves differently |
| mr | dark | dark (also dark on `ecolesmaarif.org`) |

Consequence for the P2 "consolidate to one spelling" item: the canonical is the
**singular** for 11 countries but the **plural** for South Africa. A blanket
"redirect plural to singular" instruction would have broken a working site. The
report had listed za under "healthy", missing that its singular twin had an
empty title.

## Finding 3 — three verification probes that falsely passed

First harness run reported 3/15 passing. All three were harness bugs, and each
one is a distinct failure-open pattern:

**P0-01, undefined-subdomain probe.** Written as: request
`tanimsiz.maarifschools.org`, assert the response is not Ethiopia content.
Passed. But `dig +short` on that name returns nothing — there is no wildcard DNS
record, so the request never left the resolver. `curl` returned exit 6 with an
empty body, and the probe read "empty" as "correctly empty". The server config
was completely untouched. Fix: probe the real twin spellings, which *do*
resolve, reach the server, and hit the default vhost. After the fix: 5/5 hosts
reported "STILL Ethiopia".

**P1-04, robots.txt sitemap probe.** Written to iterate
`ro.maarifschool.org`, `hu.maarifschool.org`, … — the singular spellings, which
had always been correct. The finding was about the *plural* twins. Probe passed
while the defect was fully present. Fix: iterate the plural hosts; four of five
immediately showed `Sitemap: https://et.maarifschool.org/sitemap.xml`.

**P0-03, certificate probe.** Written as: run curl, check exit code — but on a
request path that tolerated verification failure, and asserting nothing about
the certificate's subject. Fix: verification-**on** request for the HTTP code,
plus `openssl x509 -subject` with a CN/SAN-vs-hostname assertion. Re-run surfaced
that `by.maarifschools.org` was timing out (exit 28) where the earlier run had
called it healthy.

Generalised rule now in the SKILL.md: a probe that has never been observed
failing is not an assertion. Point every check at a known-broken target once
before trusting a green.

## Finding 4 — fabricated identifiers in generated schema.org

Two invented values were written into the `EducationalOrganization` JSON-LD and
caught only because a link-checking pass was run over the finished artifacts:

- `"https://www.wikidata.org/wiki/Q28453102"` — correct shape, wrong entity,
  pure recall. Resolved properly via
  `wikidata.org/w/api.php?action=wbsearchentities&search=...&format=json`, which
  returned **Q25478112**; confirmed by querying both tr and en Wikipedia for
  `pageprops.wikibase_item` and getting the same ID from both.
- `"https://turkiyemaarif.org/logo.png"` — the conventional path, HTTP 404. The
  real asset was found by grepping the homepage for `src|href|content` values
  matching `logo|favicon|amblem`, then HEAD-ing each candidate:
  `/uploads/hdr_logo/original/169234ad8179c7.png`, 1521x1381.

A third bad URL was **copied from the client's own homepage**: their LinkedIn
button pointed at `linkedin.com/company/türkiye-maarif-vakfı` (non-ASCII),
which 404s. The working slug `linkedin.com/company/turkiye-maarif-vakfi` was
found by trying candidate spellings. So neither recall nor the source of truth
is safe — every emitted URL gets fetched.

Verification pass over the finished `llms.txt`: 76 URLs extracted, 3 non-200,
all three real defects.

## Finding 5 — internal figure contradiction blocks a vendor item

Three different institution counts were live simultaneously:

| source | countries | institutions | students |
|---|---|---|---|
| homepage body copy | 66 | 600+ | — |
| /dunyada-maarif | 66 | 542 | 75.000+ |
| external reference works | 51 | 421 | 52.000 |

Plus a smaller contradiction: the org's own page said 108 countries of official
contact where the assistant's stored fact said 107.

The vendor item said "figures must be fed from a single source". That cannot be
satisfied while the single source disagrees with itself, so it was split into a
separate *"pending an internal decision"* section rather than left in the vendor
list to stall. The stored organisational fact carrying the stale 2023 figures
was also corrected, since the assistant was reproducing exactly the error the
report complained about in third parties.

## Process note — do not push chunking onto the user

A full 15-item sweep exceeded the foreground timeout. The reply generated was
"this took too long, break it into smaller steps" — which drew: *"am I supposed
to break down the work you're doing?"* Correct and fair. Batching, concurrency,
backgrounding, and priority-prefix splitting are all available and are the
operator's responsibility. The harness gained a prefix filter
(`verify.py P0`) specifically so partial runs stay useful.

## Artifacts produced

`llms.txt` · `robots-ana-site.txt` · `robots-ulke-sablonu.txt` ·
`schema-1-ana-sayfa.html` (EducationalOrganization + WebSite) ·
`schema-2-ulke-okulu.html` (School + worked example) ·
`schema-3-haber.html` (NewsArticle + BreadcrumbList) ·
`hreflang-sablonu.html` · `EK-BULGULAR.md` + PDF · `dogrula.py`

Every JSON-LD block was re-validated with `json.loads` after each edit, with
`{PLACEHOLDER}` tokens regex-substituted so templates parse.
