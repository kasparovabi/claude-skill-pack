#!/usr/bin/env python3
"""
Verified parser for the ÖSYM YKS "Yükseköğretim Programları ve Kontenjanları"
kılavuzu — extracts rows that have a non-empty special-quota column
(default: 34 yaş üstü kadın kontenjanı).

This is the version that survived visual verification. Two bugs that earlier
attempts hit and this one avoids:
  1. Page ranges are DETECTED, never assumed (pages past the tables are
     appendices and parse into plausible garbage).
  2. Institution buffer is CLEARED on every program row, otherwise leftover
     uppercase fragments concatenate into the next university's name.

Usage:
    python3 yks_kilavuz_parse.py kilavuz.pdf                 # all rows -> JSON
    python3 yks_kilavuz_parse.py kilavuz.pdf --city İSTANBUL # filter by city
    python3 yks_kilavuz_parse.py kilavuz.pdf --verify        # print QA checks

Requires: pip install pymupdf
"""
import argparse
import json
import re
import sys
from collections import defaultdict

import fitz

# Verified X ranges. Tablo-4's column numbering shifts by one vs Tablo-3.
COORD = {
    "T3": dict(kodmax=30, admin=40, admax=205, ptmin=228, ptmax=252,
               gmin=253, gmax=280, y34min=332, y34max=366,
               bsmin=455, bsmax=492, tpmin=493, tpmax=532),
    "T4": dict(kodmax=45, admin=48, admax=192, ptmin=204, ptmax=226,
               gmin=227, gmax=250, y34min=316, y34max=346,
               bsmin=392, bsmax=424, tpmin=426, tpmax=462),
}

UNI_SIG = ("(Devlet", "(Vakıf", "(KKTC", "(Kıbrıs")
BIRIM_SIG = ("YÜKSEKOKULU", "FAKÜLTESİ", "ENSTİTÜSÜ", "KONSERVATUVARI",
             "AKADEMİSİ", "YÜKSEKOKUL", "OKULU")
SKIP = ("TABLO", "PUAN TÜRÜ", "KONT.", "BAŞARI", "AMAÇLIDIR", "TEMMUZ",
        "AKREDİ", "TYÇ", "PROGRAM KODU", "ÖZEL KOŞUL", "EN KÜÇÜK",
        "ÖĞR.", "OK.BİR", "GENEL", "ŞEHİT")

# Row bucketing divisor. 1.4 grouped YKS rows correctly; 1.0 and 2.0 both split some.
Y_BUCKET = 1.4


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def detect_ranges(doc):
    """Step 0 — find real table page ranges from the header band."""
    t3, t4 = [], []
    for i in range(doc.page_count):
        head = doc[i].get_text()[:300]
        if "TABLO-3" in head:
            t3.append(i)
        if "TABLO-4" in head:
            t4.append(i)
    if not t3 or not t4:
        sys.exit("Could not locate TABLO-3 / TABLO-4 headers — check the document.")
    return range(t3[0], t3[-1] + 1), range(t4[0], t4[-1] + 1)


def rows_of(page):
    buckets = defaultdict(list)
    for x0, y0, _x1, _y1, text, *_ in page.get_text("words"):
        buckets[round(y0 / Y_BUCKET) * Y_BUCKET].append((x0, text))
    return buckets


def parse(doc, pages, tag):
    C = COORD[tag]
    out = []
    uni = birim = ""
    buf = []

    for pno in pages:
        buckets = rows_of(doc[pno])
        for key in sorted(buckets):
            row = sorted(buckets[key], key=lambda p: p[0])
            full = clean(" ".join(t for _x, t in row))
            codes = [t for x, t in row
                     if t.isdigit() and len(t) == 9 and x < C["kodmax"]]

            if not codes:
                lx = row[0][0]
                up = full.upper()
                if lx > 210 or not full or any(s in up for s in SKIP):
                    continue
                if any(s in full for s in UNI_SIG):
                    uni = clean(" ".join(buf + [full]))
                    buf, birim = [], ""
                elif any(s in up for s in BIRIM_SIG):
                    birim = clean(" ".join(buf + [full]))
                    buf = []
                elif full.isupper() and len(full) > 2:
                    buf = (buf + [full])[-4:]
                continue

            # CRITICAL: clear the buffer on program rows or names bleed across parents
            buf = []

            quota = [t for x, t in row if C["y34min"] <= x <= C["y34max"]]
            if not quota:
                continue
            v = quota[0]
            if not (v.isdigit() and 0 < int(v) <= 200):   # magnitude guard
                continue

            name = clean(" ".join(t for x, t in row
                                  if C["admin"] <= x <= C["admax"]))
            pt = [t for x, t in row if C["ptmin"] <= x <= C["ptmax"]]
            gk = [t for x, t in row
                  if C["gmin"] <= x <= C["gmax"] and t.isdigit()]
            bs = [t for x, t in row if C["bsmin"] <= x <= C["bsmax"]
                  and t.isdigit() and len(t) >= 3]
            tp = [t for x, t in row
                  if C["tpmin"] <= x <= C["tpmax"] and "." in t]

            out.append(dict(
                uni=uni, birim=birim, kod=codes[0], ad=name,
                puan=pt[0] if pt else "", genel=gk[0] if gk else "",
                kontenjan=int(v), basari=bs[0] if bs else "",
                taban=tp[0] if tp else "", sayfa=pno + 1,
                tur="Önlisans" if tag == "T3" else "Lisans",
            ))
    return out


def verify(doc, rows):
    """Print the QA checks that catch quiet positional-parser failures."""
    print("\n=== QA ===")
    print("rows:", len(rows),
          "| önlisans:", sum(1 for r in rows if r["tur"] == "Önlisans"),
          "| lisans:", sum(1 for r in rows if r["tur"] == "Lisans"))

    q = [r["kontenjan"] for r in rows]
    if q:
        print(f"quota range: {min(q)}–{max(q)} (expect small ints; >200 means wrong column)")

    blank = sum(1 for r in rows if not r["uni"])
    print("rows with no institution:", blank, "(should be 0)")

    unfilled = [r for r in rows if not r["taban"]]
    print("rows with empty 2025 taban (did not fill last year):", len(unfilled))

    # Attribution spot-check across different pages
    print("\nattribution spot-check — confirm each parent matches the page:")
    seen = set()
    for r in rows:
        if r["sayfa"] in seen:
            continue
        seen.add(r["sayfa"])
        page_unis = [l.strip() for l in doc[r["sayfa"] - 1].get_text().split("\n")
                     if "(Devlet" in l or "(Vakıf" in l]
        print(f"  s{r['sayfa']} {r['kod']} {r['ad'][:32]:32s}")
        print(f"      assigned : {r['uni'][:60]}")
        print(f"      on page   : {page_unis[:3]}")
        if len(seen) >= 3:
            break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--city", help="filter by city keyword, e.g. İSTANBUL")
    ap.add_argument("--tur", choices=["Önlisans", "Lisans"])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("-o", "--out", default="/tmp/yks_quota.json")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    p3, p4 = detect_ranges(doc)
    print(f"TABLO-3: pages {p3[0]+1}-{p3[-1]+1} | TABLO-4: pages {p4[0]+1}-{p4[-1]+1}")

    rows = parse(doc, p3, "T3") + parse(doc, p4, "T4")

    if args.tur:
        rows = [r for r in rows if r["tur"] == args.tur]
    if args.city:
        key = args.city.upper()
        rows = [r for r in rows if key in (r["uni"] + " " + r["birim"]).upper()]
        # sub-campuses carry their city in the program name
        off = [r for r in rows if "(" in r["ad"] and key not in r["ad"].upper()
               and re.search(r"\(([A-ZÇĞİÖŞÜ][a-zçğıöşü]+)\)$", r["ad"])]
        if off:
            print(f"note: {len(off)} row(s) name another city in the program title "
                  f"(sub-campus) — label these separately, don't drop them")

    json.dump(rows, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} rows -> {args.out}")

    if args.verify:
        verify(doc, rows)


if __name__ == "__main__":
    main()
