#!/usr/bin/env python3
"""
Bir klasoru herkese acik depoya atmadan once sizinti tarar.

SALT OKUNUR: hicbir dosyayi degistirmez, sadece ne buldugunu basar.

Kullanim:
    python3 sizinti_tara.py ~/.hermes/skills
    python3 sizinti_tara.py <klasor> --kurum "Acme,Globex" --kimlik "12345678"

Kurum adlari ve kimlikler her kullanicida farkli oldugu icin parametre.
Varsayilan desenler (anahtar, e-posta, telefon, ev dizini, ozel IP) sabit.
"""
import argparse
import re
from pathlib import Path

BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov",
          ".zip", ".tar", ".gz", ".pdf", ".woff", ".woff2", ".ttf",
          ".ico", ".so", ".dylib", ".pyc"}

BEYAZ = re.compile(
    r"example\.com|example\.org|user@|your-|<your|placeholder|noreply|"
    r"kullanici@|ornek@|000 0000|127\.0\.0\.1|localhost|100\.64\.0\.0",
    re.I,
)


def desenler(kurumlar, kimlikler):
    d = [
        ("ANAHTAR", re.compile(
            r"sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|"
            r"gho_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
            r"AIza[A-Za-z0-9_-]{25,}|\d{9,}:[A-Za-z0-9_-]{30,}|"
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
        ("EPOSTA", re.compile(r"[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
        ("TELEFON", re.compile(r"\+\d{1,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")),
        ("EV_DIZINI", re.compile(r"/Users/[a-z0-9_-]+/|/home/[a-z0-9_-]+/")),
        ("OZEL_IP", re.compile(r"\b(?:100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])|"
                               r"10\.\d{1,3}|192\.168)\.\d{1,3}\.\d{1,3}\b")),
    ]
    if kurumlar:
        kalip = "|".join(re.escape(k.strip()) for k in kurumlar if k.strip())
        if kalip:
            d.append(("KURUM", re.compile(kalip, re.I)))
    if kimlikler:
        kalip = "|".join(re.escape(k.strip()) for k in kimlikler if k.strip())
        if kalip:
            d.append(("KIMLIK", re.compile(kalip)))
    return d


def tara(kok, kurumlar, kimlikler):
    bulgular = {}
    sayac = 0
    for p in sorted(Path(kok).rglob("*")):
        if not p.is_file() or p.suffix.lower() in BINARY:
            continue
        try:
            icerik = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        sayac += 1
        bagil = str(p.relative_to(kok))
        for ad, desen in desenler(kurumlar, kimlikler):
            for m in desen.finditer(icerik):
                parca = m.group(0)
                if BEYAZ.search(parca):
                    continue
                bulgular.setdefault(ad, []).append((bagil, parca[:60]))
    return sayac, bulgular


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("klasor")
    ap.add_argument("--kurum", default="", help="virgulle ayrilmis kurum adlari")
    ap.add_argument("--kimlik", default="", help="virgulle ayrilmis kullanici/sohbet kimlikleri")
    a = ap.parse_args()

    sayac, bulgular = tara(a.klasor,
                           a.kurum.split(",") if a.kurum else [],
                           a.kimlik.split(",") if a.kimlik else [])

    print("taranan dosya:", sayac)
    print()
    sira = ["ANAHTAR", "KIMLIK", "OZEL_IP", "TELEFON", "EPOSTA", "KURUM", "EV_DIZINI"]
    toplam = 0
    for ad in sira:
        liste = bulgular.get(ad, [])
        if not liste:
            print("%-11s temiz" % ad)
            continue
        toplam += len(liste)
        dosyalar = sorted({d for d, _ in liste})
        print("%-11s %d bulgu, %d dosya" % (ad, len(liste), len(dosyalar)))
        for d, parca in liste[:6]:
            print("      %s -> %s" % (d[:58], parca))
        if len(liste) > 6:
            print("      ... %d tane daha" % (len(liste) - 6))

    print()
    if toplam:
        print("SONUC: %d bulgu. Ham klasoru YAYINLAMA." % toplam)
    else:
        print("SONUC: temiz.")


if __name__ == "__main__":
    main()
