#!/usr/bin/env python3
"""
Yayin oncesi sizinti tarayici.

Bir dizini herkese acik depoya atmadan once icinde ne oldugunu olcer.
Sir tarayicisi DEGILDIR; token degil, BIRIKMIS BAGLAM arar: musteri adlari,
sohbet kimlikleri, mutlak ev dizini yollari, ic hostname'ler.

Kullanim:
    python3 dizin_sizinti_tara.py <dizin> [--desen "Acme|IcSistem"]

Cikis kodu: bulgu varsa 1, temizse 0. Boylece CI adiminda kullanilabilir.
"""
import argparse
import re
import sys
from pathlib import Path

BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".mov",
          ".zip", ".tar", ".gz", ".bz2", ".7z", ".pdf", ".woff", ".woff2",
          ".ttf", ".otf", ".ico", ".db", ".sqlite", ".pyc", ".so", ".dylib"}

ATLA_DIZIN = {".git", "__pycache__", "node_modules", ".venv", "venv",
              "index-cache", "site-packages", ".pytest_cache", ".mypy_cache"}

TEMEL_DESENLER = [
    ("TOKEN", re.compile(
        r"sk-[A-Za-z0-9_-]{16,}"
        r"|ghp_[A-Za-z0-9]{20,}"
        r"|xox[baprs]-[A-Za-z0-9-]{10,}"
        r"|AIza[A-Za-z0-9_-]{25,}"
        r"|\d{9,}:[A-Za-z0-9_-]{30,}")),
    ("EV_DIZINI", re.compile(r"/Users/[a-z0-9._-]+/|C:\\Users\\[A-Za-z0-9._-]+\\")),
    ("SOHBET_KIMLIGI", re.compile(r"-100\d{10,}")),
    ("OZEL_IP", re.compile(r"\b(?:10|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])"
                           r"|192\.168|172\.(?:1[6-9]|2\d|3[01]))"
                           r"\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b")),
    ("TELEFON", re.compile(r"\+\d{1,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")),
    ("EPOSTA", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
]

BEYAZ = re.compile(
    r"example\.(com|org|net)|your-|<your|placeholder|dummy|sample|"
    r"noreply|user@|kullanici@|ornek@|foo@|bar@|test@|"
    r"0{3,}|1234567890|xxx+|AAAA+|127\.0\.0\.1|0\.0\.0\.0|localhost",
    re.I)


def desenleri_kur(ek_desen):
    desenler = list(TEMEL_DESENLER)
    if ek_desen:
        desenler.insert(0, ("OZEL_TERIM", re.compile(ek_desen, re.I)))
    return desenler


def tara(kok, desenler):
    bulgular = {}
    dosya_sayisi = 0
    for p in sorted(kok.rglob("*")):
        if not p.is_file():
            continue
        if any(d in ATLA_DIZIN for d in p.parts):
            continue
        if p.suffix.lower() in BINARY:
            continue
        try:
            icerik = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        dosya_sayisi += 1
        bagil = str(p.relative_to(kok))
        for ad, desen in desenler:
            for m in desen.finditer(icerik):
                parca = m.group(0)
                if BEYAZ.search(parca):
                    continue
                bulgular.setdefault(ad, []).append((bagil, parca[:60]))
    return dosya_sayisi, bulgular


def rapor(dosya_sayisi, bulgular, sira):
    print("taranan dosya:", dosya_sayisi)
    print()
    toplam = 0
    for ad in sira:
        liste = bulgular.get(ad, [])
        if not liste:
            print("%-16s temiz" % ad)
            continue
        toplam += len(liste)
        dosyalar = sorted({d for d, _ in liste})
        print("%-16s %d bulgu, %d dosya" % (ad, len(liste), len(dosyalar)))
        for d, parca in liste[:6]:
            print("      %-52s %s" % (d[:52], parca))
        if len(liste) > 6:
            print("      ... %d tane daha" % (len(liste) - 6))
    print()
    print("TOPLAM BULGU:", toplam)
    return toplam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    ap.add_argument("--desen", default="",
                    help="ek arama deseni, ornek: 'Acme|IcSistem|ProjeAdi'")
    a = ap.parse_args()

    kok = Path(a.dizin).expanduser().resolve()
    if not kok.is_dir():
        sys.exit("dizin yok: %s" % kok)

    desenler = desenleri_kur(a.desen)
    dosya_sayisi, bulgular = tara(kok, desenler)
    sira = [ad for ad, _ in desenler]
    toplam = rapor(dosya_sayisi, bulgular, sira)

    if toplam:
        print()
        print("YAYINLAMA. Once temizle, sonra kopyayi YENIDEN tara.")
    sys.exit(1 if toplam else 0)


if __name__ == "__main__":
    main()
