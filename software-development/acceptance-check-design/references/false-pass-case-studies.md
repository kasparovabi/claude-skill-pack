# False-pass case studies

Three real false passes from a single web-infrastructure remediation checker.
All three were caught by one baseline run and would otherwise have shipped as
"the vendor already fixed these."

Context: an audit documented 15 defects across an organisation's web estate.
A Python checker was written, one function per defect, printing PASS/FAIL.
The baseline run — executed deliberately *before* the vendor touched anything —
reported **3 of 15 passing**. Every one of those three was a bug in the probe.

Corrected baseline: **0 of 15**. That is the number that should be recorded as
the "before" evidence.

---

## Case 1 — probe never reached the server

**Defect:** the server's default virtual host was bound to one country's site,
so any request for an unconfigured hostname returned that country's content.

**Broken probe:**

```python
def p0_01():
    for host in ["tanimsiz.example.org", "buboyle-bir-alan-yok.example.org"]:
        h = fetch(f"https://{host}/")
        if "ethiopia" in title(h).lower():
            return False, "still serving wrong country"
        elif not h.strip():
            notes.append(f"{host}: empty response (correct)")   # <-- FALSE PASS
```

**Why it passed:** those hostnames were invented on the spot. There was no
wildcard DNS record, so they never resolved. `curl` exited with rc=6 (could
not resolve host) and an empty body. The probe read the empty body as the
server correctly refusing unknown hosts. In reality no packet ever left the
machine.

Diagnostic that exposed it:

```
tanimsiz.example.org        rc=6  size=0       DNS=DOES-NOT-RESOLVE
et.example.org              rc=0  size=149812  DNS=152.89.36.67
```

**Corrected probe:** use hostnames that genuinely resolve but are not
configured on the server — in this estate, the duplicate-spelling twins. Check
resolution explicitly, and never let unresolvable collapse into pass:

```python
for host in ["ro.example-plural.org", "hu.example-plural.org", ...]:
    dns = run(["dig", "+short", host]).strip()
    if not dns:
        notes.append(f"{host}: not in DNS (skipped)")
        continue                      # neither pass nor fail
    kontrol_edildi += 1
    if "ethiopia" in title(fetch(f"https://{host}/")).lower():
        tamam = False
if kontrol_edildi == 0:
    return False, "no measurable host found — check manually"
```

Corrected result: 5 of 5 twins still serving the wrong country. FAIL.

**Generalisation:** any probe built on a deliberately-invalid identifier needs
a reachability assertion, or it measures your own resolver.

---

## Case 2 — probe sampled the healthy population

**Defect:** the duplicate-spelling hostnames served a `robots.txt` whose
`Sitemap:` line pointed at a *different country's* sitemap.

**Broken probe:** sampled `ro.example.org`, `hu.example.org`, `gm.example.org`
— i.e. the **canonical** spellings. Those had always been correct.

```
ro.example.org         sitemap=https://ro.example.org/sitemap.xml     ✓ always was
ro.example-plural.org  sitemap=https://et.example.org/sitemap.xml     ✗ the actual defect
```

Nine hosts sampled, nine correct, "9 sites all point at their own sitemap",
PASS. The defect was untouched.

**Corrected probe:** derive the sample from the finding's own wording. The
finding said *"the second spelling of these countries"* — so the probe iterates
the second spelling:

```python
def p1_04():
    """...
    CRITICAL: the defect is in the PLURAL twin, not the canonical singular.
    Canonical hosts have always been correct; sampling them always passes.
    """
    ikizler = ["ro", "hu", "gm", "gh", "sl", "tn", "tz", "ge", "so", "pk", "et"]
    for a in ikizler:
        host = f"{a}.example-plural.org"
        ...
```

**Generalisation:** re-read the defect sentence and extract the population from
it literally. Convenient lists are usually the healthy ones.

---

## Case 3 — instrument was more tolerant than the real client

**Defect:** three sites presented certificates that failed validation, so
browsers showed a full-page security warning.

**Broken probe:** issued the request with certificate verification **disabled**
(`curl -k`, inherited from a shared helper) and asserted `HTTP 200`. Naturally
200 came back — the whole point of `-k` is to proceed despite the bad
certificate. It also read the expiry date, which was in the future, and
reported PASS with a reassuring `(expires Oct 28 2026)`.

**Corrected probe:** verification **enabled** for the verdict, plus an identity
assertion, because "connects" and "presents the right certificate" are
different claims:

```python
kod = http_kodu(f"https://{host}/", takip=True)      # verification ON
p = run(f"echo | openssl s_client -servername {host} -connect {host}:443 "
        f"2>/dev/null | openssl x509 -noout -subject -enddate", shell=True)
cn = re.search(r"CN\s*=\s*([^\s,]+)", p.stdout)
ad_uyuyor = cn.group(1) == host or cn.group(1) == f"*.{host.split('.', 1)[1]}"
if kod != "200" or not ad_uyuyor:
    tamam = False
```

**Interesting wrinkle:** after correction, three of the four hosts genuinely
passed with matching CNs and future expiry — the certificates really had been
renewed between the audit and the check, days apart. The fourth timed out and
failed the item. This is explanation (3) from the skill's "real pass vs
suspicious pass" list, and the honest handling is a docstring note saying the
item may have closed itself, plus corroboration from the certificate dates
rather than a bare assertion.

**Generalisation:** the check must use the same trust settings as the consumer
whose experience the defect describes. Use a tolerant fetch only as a
*secondary* read of what sits behind the broken certificate, alongside a strict
primary probe.

---

## Baseline table (corrected checker)

```
KALDI  P0-01  default vhost still serving wrong country     5/5 twins affected
KALDI  P0-02  two countries unreachable                     TLS error + wrong content
KALDI  P0-03  certificates                                  3 renewed, 1 timeout
KALDI  P0-04  empty page titles                             7 sites, all empty
KALDI  P0-05  domain redirect                               TLS error persists
...
SONUC: 0/5 verified
```

A believable baseline for a freshly-written defect list is *near-total
failure*. When the first run comes back cheerful, the checker is the thing
that is broken.
