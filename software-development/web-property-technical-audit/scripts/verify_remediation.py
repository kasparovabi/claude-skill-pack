#!/usr/bin/env python3
"""
Remediation verification harness — skeleton.
============================================

Copy this next to an audit, replace the KALEMLER item functions with the
findings you actually raised, and hand it to the client so they can close
items themselves.

Usage:
    python3 verify_remediation.py          # all items
    python3 verify_remediation.py P0       # only P0-prefixed items
    python3 verify_remediation.py P1-03    # a single item

DESIGN RULES (these are why the harness is trustworthy — do not remove):

 1. Every probe must be able to FAIL. Before shipping, point each one at a
    host you know is broken and confirm it goes red. A check that has never
    been observed failing is decoration, not verification.

 2. Reachability is guarded FIRST. `cozuluyor()` gates every remote probe.
    A host that does not resolve reports "skipped", never "clean" — an
    empty response must never be read as a passing result.

 3. Probe the EXACT entity named in the finding. If the finding is about
    the plural domain spelling, do not probe the singular one because it is
    tidier. That is how three checks falsely passed in the reference case.

 4. Separate "browser sees" from "server returns" with a verify-on and a
    verify-off request. The diff is what classifies the failure mode.

 5. For redirect assertions, do NOT follow redirects. `-L` swallows the
    very Location header you are trying to verify.
"""

import concurrent.futures as cf
import json
import re
import subprocess
import sys

UA = "RemediationAudit/1.0"
ZAMAN = "20"

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


# ---------------------------------------------------------------- primitives

def curl(url, insecure=False, head=False, fmt=None, follow=True):
    cmd = ["curl", "-sS", "--max-time", ZAMAN, "-A", UA]
    if insecure:
        cmd.append("-k")          # verification OFF: what the server really serves
    if follow:
        cmd.append("-L")
    if head:
        cmd.append("-I")
    if fmt:
        cmd += ["-o", "/dev/null", "-w", fmt]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout, r.returncode


def http_code(url, follow=False):
    """Verification ON. Exit 60 = certificate rejected (a finding).
    Exit 28 = timeout (possibly your own network). Never merge the two."""
    out, rc = curl(url, fmt="%{http_code}", follow=follow)
    if rc == 0:
        return out.strip()
    return {60: "TLS-REJECTED", 28: "TIMEOUT"}.get(rc, f"CURL-ERR({rc})")


def body(url, insecure=True):
    out, _ = curl(url, insecure=insecure)
    return out


def cozuluyor(host):
    """RULE 2: gate every probe on DNS. Invented or retired hostnames never
    reach the server, so their empty response proves nothing about config."""
    return bool(subprocess.run(["dig", "+short", host],
                               capture_output=True, text=True).stdout.strip())


def title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else ""


def meta_desc(html):
    m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    return m.group(1).strip() if m else ""


def html_lang(html):
    m = re.search(r'<html[^>]*lang=["\']([^"\']*)', html, re.I)
    return m.group(1).strip() if m else ""


def jsonld_types(html):
    """Returns @type of every valid JSON-LD block; 'BROKEN-JSON' for bad ones."""
    types = []
    for blok in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                           html, re.S | re.I):
        try:
            d = json.loads(blok.strip())
        except json.JSONDecodeError:
            types.append("BROKEN-JSON")
            continue
        for item in (d if isinstance(d, list) else [d]):
            if isinstance(item, dict):
                types.append(item.get("@type", "?"))
    return types


def cert_matches(host):
    """RULE 4: assert the certificate is actually FOR this host.
    HTTP 200 alone does not prove that."""
    p = subprocess.run(
        f"echo | openssl s_client -servername {host} -connect {host}:443 2>/dev/null "
        f"| openssl x509 -noout -subject -enddate",
        shell=True, capture_output=True, text=True)
    out = p.stdout.strip().replace("\n", " ")
    cn = re.search(r"CN\s*=\s*([^\s,]+)", out)
    exp = re.search(r"notAfter=(.+)", out)
    cn_s = cn.group(1) if cn else "?"
    wildcard = f"*.{host.split('.', 1)[1]}" if "." in host else ""
    return (cn_s in (host, wildcard)), cn_s, (exp.group(1).strip() if exp else "?")


# ---------------------------------------------------------------- item probes
# Each returns (passed: bool, detail: str). Replace with your real findings.

def ornek_default_vhost():
    """Undefined hostnames must not serve some other site's content.

    RULE 3: probe hosts that RESOLVE but are unconfigured (e.g. the duplicate
    domain spellings named in the finding). Inventing 'nosuchhost.example.com'
    tests DNS, not the virtual-host config, and always falsely passes.
    """
    hedefler = ["twin1.example.org", "twin2.example.org"]
    yanlis_icerik = "default site title"
    notlar, ok, olculen = [], True, 0
    for host in hedefler:
        if not cozuluyor(host):
            notlar.append(f"{host}: DNS yok (skipped)")
            continue
        olculen += 1
        t = title(body(f"https://{host}/"))
        if yanlis_icerik.lower() in t.lower():
            ok = False
            notlar.append(f"{host}: STILL serving default host")
        else:
            notlar.append(f"{host}: '{t[:35]}'")
    if olculen == 0:
        return False, "no measurable host - verify by hand"   # never silent-pass
    return ok, "; ".join(notlar)


def ornek_sertifika():
    ok, notlar = True, []
    for host in ["a.example.org", "b.example.org"]:
        if not cozuluyor(host):
            notlar.append(f"{host}: DNS yok (skipped)")
            ok = False
            continue
        kod = http_code(f"https://{host}/", follow=True)     # verification ON
        uyuyor, cn, bitis = cert_matches(host)
        if kod != "200" or not uyuyor:
            ok = False
        notlar.append(f"{host}: HTTP {kod}, CN={cn}"
                      f"{'' if uyuyor else ' <-CN MISMATCH'}, expires={bitis}")
    return ok, "; ".join(notlar)


def ornek_301():
    """RULE 5: no -L here, or the Location header you are checking disappears."""
    out, rc = curl("https://old.example.org/", head=True, follow=False)
    if rc != 0:
        return False, f"TLS/connection error (curl rc={rc})"
    kod = re.search(r"HTTP/[\d.]+ (\d{3})", out)
    loc = re.search(r"(?i)^location:\s*(\S+)", out, re.M)
    k = kod.group(1) if kod else "?"
    l = loc.group(1) if loc else "NONE"
    return (k.startswith("30") and "new.example.org" in l), f"HTTP {k}, Location: {l}"


def ornek_jsonld():
    ok, notlar = True, []
    tipler = jsonld_types(body("https://example.org/"))
    if not any("Organization" in t for t in tipler):
        ok = False
    notlar.append(f"homepage: {tipler or 'NONE'}")
    return ok, "; ".join(notlar)


def ornek_sitemap_lastmod():
    """One distinct lastmod equal to request time = regenerated per request."""
    from datetime import datetime, timezone
    xml = body("https://example.org/sitemap.xml")
    lm = re.findall(r"<lastmod>(.*?)</lastmod>", xml)
    if not lm:
        return False, "no lastmod found (could not measure)"
    farkli = len(set(lm))
    now, taze = datetime.now(timezone.utc), 0
    for d in set(lm):
        try:
            if abs((now - datetime.fromisoformat(d.replace("Z", "+00:00"))).total_seconds()) < 300:
                taze += 1
        except ValueError:
            pass
    return (farkli > 10 and taze == 0), \
           f"{len(lm)} urls, {farkli} distinct lastmod, {taze} equal to request time"


def ornek_ozel_ip():
    p = subprocess.run(["dig", "+short", "example.org", "A"], capture_output=True, text=True)
    ipler = [x.strip() for x in p.stdout.split("\n") if x.strip()]
    ozel = [i for i in ipler
            if i.startswith(("10.", "192.168."))
            or (i.startswith("172.") and i.split(".")[1].isdigit()
                and 16 <= int(i.split(".")[1]) <= 31)]
    return (not ozel and bool(ipler)), f"A records: {ipler}; private: {ozel or 'none'}"


# ---------------------------------------------------------------- registry

KALEMLER = [
    ("P0-01", "Default virtual host separated", ornek_default_vhost),
    ("P0-02", "Certificates valid and matching", ornek_sertifika),
    ("P0-03", "Legacy domain 301s to canonical", ornek_301),
    ("P1-01", "schema.org JSON-LD present", ornek_jsonld),
    ("P1-02", "sitemap lastmod is real", ornek_sitemap_lastmod),
    ("P1-03", "private IPs out of public DNS", ornek_ozel_ip),
]


def main():
    filtre = sys.argv[1].upper() if len(sys.argv) > 1 else ""
    secili = [k for k in KALEMLER if k[0].startswith(filtre)] if filtre else KALEMLER
    if not secili:
        print(f"no item matches '{filtre}'")
        return

    print(f"\nRemediation verification — {len(secili)} item(s)\n" + "=" * 96)
    gecen = 0
    for no, ad, fn in secili:
        try:
            ok, detay = fn()
        except Exception as e:
            ok, detay = False, f"PROBE ERROR: {type(e).__name__}: {e}"
        damga = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        gecen += 1 if ok else 0
        print(f"\n{damga}  {no}  {ad}")
        for parca in detay.split("; "):
            print(f"        {parca}")

    print("\n" + "=" * 96)
    renk = GREEN if gecen == len(secili) else (YELLOW if gecen else RED)
    print(f"{renk}RESULT: {gecen}/{len(secili)} verified{RESET}\n")
    print("Note: a run before any remediation work is the BASELINE, not a failure "
          "report. Label it as such when sharing.\n")


if __name__ == "__main__":
    main()
