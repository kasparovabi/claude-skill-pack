# Primary-Source Verification of a Viral Claim

Playbook for: *"independently verify technique/claim X — find the original post,
extract the exact text, compare against the pattern it allegedly derives from,
find real criticism. Don't trust the video/summary. Say what you couldn't find."*

Worked end-to-end Aug 2026 (gauntlet-loop / Matt Shumer verification). Every
verified fact came from an unauthenticated JSON API. DDG Lite CAPTCHA'd 7/7.

---

## Routing: APIs first, search engines last

| Need | Endpoint | Auth |
|---|---|---|
| Exact text of an X post | `publish.twitter.com/oembed?url=https://twitter.com/USER/status/ID&omit_script=1` | none |
| Exact file from a repo | `raw.githubusercontent.com/OWNER/REPO/main/FILE.md` | none |
| Repo provenance (created_at, stars, license) | `api.github.com/repos/OWNER/REPO` | none |
| Full file listing | `api.github.com/repos/OWNER/REPO/git/trees/main?recursive=1` | none |
| Community reception + comment counts | `hn.algolia.com/api/v1/search?query=Q&tags=story` | none |
| Peer-reviewed grounding | `export.arxiv.org/api/query?search_query=ti:"X"+AND+abs:"Y"` | none |
| One paper's abstract | `export.arxiv.org/api/query?id_list=2310.01798` | none |

Search engines are only for **discovering the URL**. Once you have a repo or a
status ID, never scrape — hit the API.

### The one search that IS worth fighting for
You need exactly one successful SERP to seed every API call above. Read the
snippets, harvest the URLs, then stop searching:

```bash
curl -sL "https://lite.duckduckgo.com/lite/?q=QUERY" -A "UA" -o s.html
# decode result links out of the uddg redirects:
python: re.findall(r'href="(https?://[^"]+)"', raw)  →  unquote(uddg param)
```

DDG Lite snippets alone surfaced the canonical writeup, the repo, the GitHub
prompt file, two X status IDs, and the independent news coverage — one curl.

---

## Step order that worked

1. **Fetch the pattern it allegedly derives from FIRST** (the stable, known URL).
   Extract the verbatim definition before you look at the claim, so you compare
   against real text and not memory.
2. **Find the claim's real source.** One SERP → harvest URLs → APIs.
3. **Get the exact artifact** (`prompt.md`, not the author's prose summary of it).
   Authors paraphrase their own work; the repo file is the primary source.
4. **Grep the alleged source for the technique's own vocabulary.** See below.
5. **Read the creator's own README to the end** before hunting external critics.
6. **Check community reception** (HN points/comments) — asymmetry is a finding.
7. **Ground the criticism in literature** via arXiv.

---

## Negative evidence: proving misattribution

The single strongest finding was that the widely-cited "source" article contained
**zero** occurrences of the technique's vocabulary. Always run this before
accepting an "X wrote this in Y" chain:

```python
txt = strip_html(open('alleged_source.html').read())
for kw in ["gauntlet","loop","subagent","Call of Duty","prompt","fan-out"]:
    print(kw, len(re.findall(re.escape(kw), txt, re.I)))
# all zero → the attribution is wrong, and that IS the finding
```

Phrase it as **"I downloaded the full text and searched it; 0 matches"** — that
is citable evidence. Never phrase it as "I couldn't find it," which reads as a
retrieval failure rather than a disproof.

---

## The creator's own repo is the best critic

Press coverage is promotional; the README often is not. Grep for self-critical
headings before concluding no criticism exists:

```bash
grep -iE "honest|assessment|limitation|known issue|process note|what breaks|caveat|shortcoming" README.md
```

In the worked case the README's own `## Honest assessment` stated the technique
**failed its stated goal** ("The goal was to match a modern Call of Duty. **It does
not.**"), showed a **score regression** mid-run (4.14 → 4.05), and a `## Process
note` reported that the technique's headline mechanism (parallel fan-out) **lost
decisively** to the simpler sequential alternative on the author's own numbers.
None of that appeared in any article about it.

Also fetch `ARCHITECTURE.md` / docs listed by the trees API — you cannot grep a
file you never discovered.

---

## Engagement asymmetry as evidence

```bash
curl -sL "https://hn.algolia.com/api/v1/search?query=CLAIM&tags=story&hitsPerPage=10"
```

Millions of views on X but 4 points / 0–1 comments on HN ⇒ **no technical peer
review has happened**. Report that explicitly. A quiet HN is data, not absence
of data.

Beware the near-miss: searching the technique's name returned a decade of
unrelated results (medieval gauntlets, interview gauntlets). Confirm each hit's
URL actually points at the artifact before counting it.

---

## Grounding criticism in literature

Generic-but-authoritative papers beat nonexistent claim-specific ones. When no
paper studies the exact technique, cite the mechanism it depends on:

| Mechanism under scrutiny | Paper |
|---|---|
| Judge approves its own output | Self-Preference Bias in LLM-as-a-Judge — arXiv:2410.21819 |
| Iterative self-correction degrades quality | LLMs Cannot Self-Correct Reasoning Yet — arXiv:2310.01798 |
| Multi-agent failures are hard to attribute | Which Agent Causes Task Failures and When? — arXiv:2505.00212 (53.5% agent / 14.2% step accuracy) |

Vendor engineering blogs also carry hard numbers that function as criticism:
Anthropic's multi-agent-research-system post gives **4× tokens vs chat for
agents, ~15× for multi-agent**, plus an explicit warning that *"most coding tasks
involve fewer truly parallelizable tasks than research."*

**Be fair in the writeup**: note where the technique already mitigates a known
failure mode (e.g. fresh-context critic + blind A/B is the literature's own
remedy for self-preference bias). A verification that only prosecutes is a worse
product than one that credits what holds up.

---

## Output shape (reusable)

```
## SUMMARY: N CORRECTIONS TO THE BRIEF     ← lead with what the user got wrong
(a) EXACT TEXT + source table (URL | date | what it proves)
(b) COMPARISON — side-by-side table, verbatim quotes both sides, then a verdict
    sentence that answers "same thing or not" in plain words
(c) LIMITATIONS — ordered by evidential strength, creator's own words first
## COULDN'T FIND — explicit, itemised, no hedging
## SOURCES — numbered, full URLs
```

Order limitations by **strength of evidence, not severity of accusation**:
the creator's own data > vendor's own docs > independent journalism > academic
literature > secondary commentary.

---

## Reconcile handed-down numbers

Briefs inflate. The brief said 4.8M views; the creator's own LinkedIn said 3.8M;
his article said only "millions." Report the discrepancy, cite the lower
self-reported figure, and state you could not verify the metric directly (oembed
returns post text but no engagement counts, and X itself is not curl-reachable).

Also verify **spelling of names** against the primary source before publishing —
the brief said "Schumer," every primary artifact said "Shumer."
