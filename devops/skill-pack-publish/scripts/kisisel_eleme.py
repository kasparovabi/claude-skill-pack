#!/usr/bin/env python3
"""
Yayin oncesi SAHIPLIK ve KISISELLIK elemesi.

Sizinti taramasindan AYRI bir is. Sizinti taramasi "ne aciga cikiyor" diye
sorar, bu betik iki baska soru sorar:

  1. Bu skill'i kullanici mi yazdi, yoksa kurulumla mi geldi?
  2. Yazdiysa bile, baskasi kurarsa zarar verir mi?

2026-08-14 olcumu: 115 skill yayinlanmisti, 81'i kurulumla gelen ya da
satici belgesiydi ve sizinti taramasindan TERTEMIZ gecmislerdi. Sizinti
taramasi bu soruyu cevaplamaz.

Kullanim:
    python3 kisisel_eleme.py <paket_dizini> [--uygula]

--uygula verilmezse hicbir sey silinmez, sadece rapor basar.
"""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

UPSTREAM_KOKLERI = [
    "~/.hermes/hermes-agent/skills",
    "~/.hermes/hermes-agent/optional-skills",
    "~/.hermes/plugins",
    "~/.claude/skills",
]

SES_IZI = re.compile(
    r"yazım protokol|yazim protokol|writing voice|voice calibration|"
    r"kullanıcının sesi|user'?s voice|ortanca mesaj|median message|"
    r"tone profile|üslup|uslup|kendi sesini", re.I)

AKIS_IZI = re.compile(
    r"benim kurulum|my setup|bu makinede|kendi cron|kişisel bot|"
    r"kendi tetikleyici|kendi model tercih", re.I)

BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".zip",
          ".gz", ".tar", ".pdf", ".woff", ".woff2", ".ttf", ".ico"}


def upstream_adlari():
    """Kurulumla gelen skill adlarini toplar."""
    adlar = set()
    for kok in UPSTREAM_KOKLERI:
        p = Path(kok).expanduser()
        if not p.exists():
            continue
        for s in p.rglob("SKILL.md"):
            adlar.add(s.parent.name)
    return adlar


def skill_metni(dizin):
    """Skill'in tum metin dosyalarini birlestirir."""
    parcalar = []
    for f in dizin.rglob("*"):
        if f.is_file() and f.suffix.lower() not in BINARY:
            try:
                parcalar.append(f.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return "\n".join(parcalar)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paket")
    ap.add_argument("--uygula", action="store_true")
    a = ap.parse_args()

    kok = Path(a.paket).expanduser()
    upstream = upstream_adlari()
    print("upstream skill adi:", len(upstream))
    print()

    kurulu, kisisel, kalan = [], [], []

    for p in sorted(kok.rglob("SKILL.md")):
        ad = p.parent.name
        if ad in upstream:
            kurulu.append(ad)
            continue

        metin = skill_metni(p.parent)
        ses = SES_IZI.findall(metin)
        akis = AKIS_IZI.findall(metin)

        if ses or akis:
            kisisel.append((ad, len(ses), len(akis)))
        else:
            kalan.append(ad)

    print("KURULUMLA GELEN (%d) - yayinlanmamali" % len(kurulu))
    for ad in kurulu[:10]:
        print("   ", ad)
    if len(kurulu) > 10:
        print("    ... %d tane daha" % (len(kurulu) - 10))

    print()
    print("KISISEL IZ TASIYAN (%d) - gozle karar ver" % len(kisisel))
    print("   ses izi cok ise KALDIR, sadece ad geciyorsa TEMIZLE")
    for ad, s, k in kisisel:
        print("    %-38s ses=%d akis=%d" % (ad, s, k))

    print()
    print("KULLANICININ, TEMIZ (%d)" % len(kalan))

    if not a.uygula:
        print()
        print("[rapor modu, hicbir sey silinmedi. --uygula ile calistir]")
        return

    silindi = 0
    for p in list(kok.rglob("SKILL.md")):
        if p.parent.name in kurulu:
            shutil.rmtree(p.parent)
            silindi += 1

    for d in sorted(kok.rglob("*"), reverse=True):
        if d.is_dir() and ".git" not in str(d) and not any(d.iterdir()):
            d.rmdir()

    print()
    print("silinen (kurulumla gelen):", silindi)
    print("kisisel iz tasiyanlar SILINMEDI, elle karar ver")


if __name__ == "__main__":
    main()
