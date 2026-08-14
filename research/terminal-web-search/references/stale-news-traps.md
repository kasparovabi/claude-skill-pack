# Stale-news traps & verification recipes (news-roundup hardening)

Concrete cases where a search result *looked* current but was months/years old,
plus the exact recipes used to catch them. Source: a recurring the client education
news-summary cron job that repeatedly shipped stale items until these gates were
added.

## The four traps (reject signals)

| Trap | Tell | Real example | How to confirm |
|------|------|--------------|----------------|
| Anniversary / calendar day | Headline pegged to a recurring observance | Gaza "World Children's Day art exhibit" surfaced in a June roundup → really 20 Nov (prior year) | Look up the observance's fixed date; is it inside the window? |
| Title-as-date-marker | "newly-appointed / -designate / incoming / -elect" | "Karnataka CM-designate DK Shivakumar announces AI plan" → CM-designate window was May 2023 (~3 yrs old) | Is that person still in that transitional status today? |
| Recycled MoU/protocol | "X and Y signed a cooperation protocol" | TÜRGEV/the client protocol read as breaking → signed ~late March (≈2 mo stale) | Confirm signing date in article body or a 2nd outlet |
| Auto-updated page stamp | Page "last modified" = today, story is old | A TBMM committee story flagged "current" off the page's update stamp | Trust the article body / URL date, never the page chrome stamp |

## Freshness gate for a scheduled roundup
1. Read the sent-headlines dedup log first (`tail -60`) — build the
   already-covered set.
2. For every candidate, find an explicit DD/MM/YYYY publish date in at least one
   source. No confirmable date in window → drop it.
3. Apply the four traps above as hard reject signals.
4. Don't pad. If nothing genuinely fresh survives, return `[SILENT]`.
5. After sending, append today's items to the dedup log.

## Cron-prompt hardening that encodes this
When the roundup runs as a cron job, bake the gate into the job prompt itself,
not just into the agent's habits. Working clauses added to the the client job:
- "Sadece SON 7 GÜN içinde yayımlanmış haberleri al. Tarihini netleştiremiyorsan ELE."
- A YILDÖNÜMÜ/ETKİNLİK TUZAĞI clause (anniversary trap, with the 20-Kasım example).
- A KİŞİ-UNVAN TUZAĞI clause (title-as-date-marker trap).
- A TARİH ZORUNLULUĞU clause: no item without a seen day/month/year date.
- A LİNK KURALI clause: full article URL, not bare domain, with a good/bad example.
- "Yeni/taze haber azsa madde sayısını zorlamA … Hiç yeni yoksa [SILENT] dön."
Also: niche education/institutional topics genuinely don't produce fresh news
daily — schedule such roundups 2-3x/week, not daily, or the agent fills the gap
with recycled items. (the client job moved daily → Mon/Thu.)

## The anniversary trap's legitimate inverse — a milestone IN-window is a keeper
The anniversary/calendar-day trap rejects observances whose fixed date falls
OUTSIDE the window. The inverse is equally important: when an institution's
founding/anniversary date lands INSIDE the window, the milestone coverage is a
real, high-value lead, not a trap. Example: a client organisation's 10th
anniversary — the founding law passed 17 June 2016, so a 17–18 June roundup
legitimately leads with "10th year" coverage (JSON-LD datePublished 2026-06-17
confirmed across Sabah/Haber7/Ensonhaber). The discipline is the same: confirm
the milestone's anchor date is in-window via the article's structured date, then
keep it. Don't reflexively drop a story just because it's anniversary-shaped.

### One event can yield two distinct items
A single institutional milestone often spawns two separately valuable angles
worth listing as two items, not one:
  1. the milestone/recap itself (capacity figures, the "X years" framing), and
  2. concrete forward-looking news the leader announced AT that event (new
     school openings, signed agreements, expansion plans).
On the the client 10th-year story these split cleanly into a "10. YIL" recap item
and a "YENİ AÇILIMLAR" item (Brazil talks, Kazakhstan two-school agreement from
the same Özdil statement). Pull the forward news out as its own item with its own
source URL — it's the part the team can act on, vs. the recap they already know.

## the client-roundup angle-query playbook (Bing News, setmkt=tr-TR / en-US)
The four-area brief (TR/Türk dünyası education, AI-in-education, diaspora/Yunus
Emre, Türkiye general affecting the client) is best covered by running these angle
queries in parallel, each with `&qft=interval%3d%227%22` for the 7-day filter:
- `the client+Vakfi` , `the client+Vakfi+yurt+disi+okul` , `the client+okul+acilis+OR+mezuniyet`
- `the client+Kazakistan+OR+Kirgizistan+OR+Ozbekistan` , `the client+Balkanlar+OR+Afrika+okul`
- `Yusuf+Tekin+egitim` , `MEB+egitim+ogretim`
- `yapay+zeka+egitim+okul` (tr-TR) AND `AI+education+schools+policy` (en-US)
- `Yunus+Emre+Enstitusu` , `Turk+Devletleri+Teskilati+egitim` , `Turk+dunyasi+egitim+isbirligi`

Observed filter behavior (don't misread an empty filtered page as "no news"):
- The 7-day filter routinely ZERO-returns for `MEB+egitim`, `Yusuf+Tekin+egitim`,
  `Yunus+Emre+Enstitusu`, `Turk+Devletleri/dunyasi` — niche TR proper-noun
  queries the filter buries. Run the UNFILTERED version too before concluding the
  area is dead; then date-gate each candidate with `article_publish_date.py`.
- AI-in-education (`yapay+zeka...` tr-TR and `AI+education...` en-US) is the area
  most likely to yield genuinely fresh items week to week — global policy moves
  (national AI bans, university cheating/surveillance, district screen-time
  limits) recur and almost always pass the date gate. When TR/the client-specific
  news is thin, the AI-education angle reliably carries 1-2 strong the client-framed
  items (frame: "what this means for the client's central AI policy across N
  countries"). en-US Bing News surfaces these via MSN mirrors AND direct outlet
  URLs (adn.com, washingtonpost.com, sozcu.com.tr) — prefer the direct outlet URL
  over the MSN `ar-AA...` mirror (MSN often has no structured date / is JS-only).
- the client-specific fresh items beyond milestone recaps tend to be small saha
  stories on haberler.com (a youth-delegation visit to overseas the client schools, a
  local event) — found by the `the client+Balkanlar+OR+Afrika+okul` angle even though
  the headline doesn't name a region; scan the result list for "the client" anywhere.

## Dedup-exception pattern: scheduled-future-event → it-happened
The cleanest legitimate use of the "GÜNCELLEME:" dedup exception is a previously
logged scheduled event that has now occurred. Example: the 4. Millî Eğitim
Kongresi was logged weeks earlier as "24-26 Haziran'da toplanacak"; when it
actually opened, the new roundup re-listed it tagged "GÜNCELLEME:" with the
concrete new content (opening speeches, the client Modeli emphasis, the 26 June
end date) rather than dropping it as a duplicate. Rule: a logged "will happen on
DATE" item earns a GÜNCELLEME re-list ONCE, when it actually happens and you can
add real new detail — not a third time for routine follow-up coverage.

## URL-decode recipes (emit full article URLs)

**DDG Lite redirect.** Result hrefs look like
`//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.nytimes.com%2F...`. Decode:
```python
import urllib.parse
real = urllib.parse.parse_qs(urllib.parse.urlparse('https:'+href).query)['uddg'][0]
```

**Bing News cards.** Each card (`re.split(r'class="news-card', html)[1:]`) carries
`url="..."` (full article URL), `data-author="..."` (publisher), and an often
absent/unreliable `data-time="..."`. Prefer `url=""` over inner anchor text.
Cards frequently lack a usable date — that's when you must open the article and
read the body/JSON-LD `datePublished` to gate freshness.

**Article body date.** Most outlets embed `"datePublished":"2025-02-24T..."` in
JSON-LD; grep for it before trusting any listing-page relative timestamp. This is
how the "Gabon science fair = 4th edition, Feb 2025" fact was nailed down against
a user claim of a 5th edition.

## Don't-fabricate / don't-downgrade rule
If the user asserts a specific event+date and you can't find coverage: it may
simply be unindexed (niche events lag weeks). State where you looked, show the
institution's own news page and its latest-visible date, and offer to verify from
a user-supplied link / re-check later / check social accounts. Never invent a
"found it," and never silently substitute the older edition you *could* find for
the one the user named — surface the discrepancy.
