# Web remediation probes

Read-only probes for verifying web-infrastructure remediation, plus notes on
the fix artifacts they check. All are stdlib Python + `curl` / `dig` /
`openssl`; nothing mutates the target.

## Two-request pattern (the core technique)

Fetch every host **twice** — once with certificate verification on, once with
it off — and diff the outcomes. This single pattern separates three otherwise
indistinguishable failures.

```python
def olc(host):
    strict = run(["curl", "-sS", "--max-time", "20", "-A", UA,
                  "-o", "/dev/null", "-w", "%{http_code}", f"https://{host}/"])
    tolerant = run(["curl", "-skSL", "--max-time", "20", "-A", UA, f"https://{host}/"])
    return strict.stdout.strip() or f"TLS-ERROR({strict.returncode})", tolerant.stdout
```

| strict | tolerant | Meaning |
|---|---|---|
| 200 | content | healthy |
| TLS-ERROR | correct content | **certificate-only defect** — content is fine, browsers blocked |
| TLS-ERROR | *someone else's* content | certificate defect **and** wrong vhost binding |
| error | empty | host down, or never resolved — check DNS before concluding |

The second row is the one a single tolerant request hides completely.

## Probe recipes

**TLS identity, not just reachability**

```bash
echo | openssl s_client -servername "$H" -connect "$H:443" 2>/dev/null \
  | openssl x509 -noout -subject -enddate -ext subjectAltName
```

Assert CN or a SAN entry equals the hostname (or its wildcard parent), and that
`notAfter` has comfortable margin — a common acceptance bar is 60+ days.

**Redirect configured** — do *not* follow:

```bash
curl -sS -I --max-time 20 "https://$H/"     # no -L
```

Assert a 3xx status line and read the `Location` header. With `-L` you land on
the destination and can never tell whether a redirect existed.

**Private addresses leaking into public DNS**

```bash
dig +short example.org A
```

Assert no record falls in `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
Beware the `172.` test — only the second octet 16–31 is private.

**Empty metadata** — presence is not content:

```python
title  = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
desc   = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
lang   = re.search(r'<html[^>]*lang=["\']([^"\']*)', html, re.I)
ok = bool(title and title.group(1).strip()) and len(desc.group(1) if desc else "") >= 120
```

An empty `<title></title>` matches the regex and is truthy as a match object.
Assert the stripped group, and a length floor on the description.

**Stale sitemap timestamps** — cardinality, not presence:

```python
lm = re.findall(r"<lastmod>(.*?)</lastmod>", xml)
distinct = len(set(lm))
fresh = sum(1 for d in set(lm)
            if abs((now - datetime.fromisoformat(d.replace("Z", "+00:00"))).total_seconds()) < 300)
ok = distinct > 10 and fresh == 0
```

1,312 URLs each carrying a timestamp looks healthy; one distinct value equal to
request time means the file is regenerated per request and the field is noise.

**Structured data present and correct type**

```python
def jsonld(html):
    out = []
    for blok in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                           html, re.S | re.I):
        try:
            d = json.loads(blok.strip())
        except json.JSONDecodeError:
            out.append("BROKEN-JSON")
            continue
        for o in (d if isinstance(d, list) else [d]):
            if isinstance(o, dict):
                out.append(o.get("@type", "?"))
    return out
```

Report `BROKEN-JSON` distinctly — a malformed block is worse than none, and a
naive `count("ld+json") > 0` check passes on it.

**Bot policy in robots.txt**

```python
sitemap = re.findall(r"(?i)^sitemap:\s*(\S+)", txt, re.M)
ai = [b for b in ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"]
      if re.search(rf"(?i)user-agent:\s*{b}", txt)]
```

Assert the `Sitemap:` URL contains the host being probed — a templated file
often carries a hard-coded neighbour's hostname.

## Runner shape

- Each check is a function returning `(bool, detail_string)`; the detail is
  what the remediator reads, so name the observed value *and* the expected one.
- Wrap the dispatch so an exception becomes `MEASUREMENT ERROR`, never a pass:

  ```python
  try:
      ok, detail = fn()
  except Exception as e:
      ok, detail = False, f"MEASUREMENT ERROR: {type(e).__name__}: {e}"
  ```
- Accept a prefix filter (`P0`, `P1-02`) so one fixed item re-checks in seconds.
- Parallelize per-host loops with `ThreadPoolExecutor(max_workers=6..10)` and
  keep `--max-time` at ~20s. A serial suite over 40 hosts with slow TLS
  handshakes will exceed a 400s foreground tool timeout; run it backgrounded and
  poll, or filter to one group.

## Fix artifacts these probes verify

When you also produce the remediation files, verify them before handover:

- **JSON-LD blocks** — parse every block with `json.loads` after substituting
  template placeholders; ship only blocks that parse.
- **Any URL you write into a deliverable** — fetch every one. In this session
  that caught an invented logo path (404), a broken social profile URL that was
  copied from the site's own markup (the site's own button was dead), and an
  entity ID recalled from memory rather than looked up.
- **External entity IDs** — query the authoritative API rather than recalling.
  Wikidata: `wbsearchentities`, then confirm via the language wiki's
  `pageprops.wikibase_item`. A remembered ID that looks plausible is the highest
  -risk value in a structured-data block, because nothing downstream validates it.
- **Image dimensions** referenced in structured data — read them off the actual
  file rather than assuming, since schema consumers check aspect ratio and
  minimum size.

## Scope discovery

Before trusting an inventory handed to you, enumerate independently. Extracting
every external hostname from the organisation's own directory page revealed a
**third** domain family the audit had not mentioned (14 additional country
sites), changing the remediation scope from 33 sites to 47.

```python
hepsi = re.findall(r"https?://([a-z0-9-]+)\.([a-z0-9.-]*keyword[a-z0-9.-]*)", html, re.I)
Counter(d.lower() for _, d in hepsi).most_common()
```

Grouping by registrable domain and eyeballing the counts surfaces families
nobody listed. Audit scopes are inputs to verify, not givens.
