#!/usr/bin/env python3
"""
Skill aciklamalarini toplu duzeltir: ilk 57 karaktere TETIKLEYICI tasir.

Neden: sistem promptundaki skill indeksi aciklamayi 57 karakterde kirpiyor.
Kirpilan pencerede "ne zaman kullanilir" bilgisi yoksa ajan skilli hic yuklemiyor.

Kullanim:
    python3 skill_aciklama_duzelt.py              # kuru kosum (varsayilan)
    python3 skill_aciklama_duzelt.py --uygula     # diske yazar
    python3 skill_aciklama_duzelt.py --tablo t.json --uygula

Tablo bicimi (JSON): {"kategori/skill-adi": "Use when ... . ... .", ...}

ONEMLI: yalnizca frontmatter'daki `description` alanini degistirir, govdeye
dokunmaz. Calistirmadan ONCE yedek al:
    cd ~/.hermes && tar czf /tmp/skills_yedek.tgz --exclude='*/node_modules' skills/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KOK = Path.home() / ".hermes" / "skills"

# Tetikleyici sayilan kaliplar. skillcheck yalnizca "use when" sayiyor ama
# "use whenever" / "use for" da gecerlidir; ikisini de OK kabul ediyoruz.
TETIKLEYICI = re.compile(r"\b(use when|use whenever|use for)\b", re.I)

# Sistem promptu aciklamayi bu uzunlukta kirpar.
PENCERE = 57

# skill_manage(action='create') bu siniri asan aciklamayi REDDEDER.
OLUSTURMA_SINIRI = 60


def frontmatter_sinirlari(metin: str) -> tuple[int, int] | None:
    """--- ... --- blogunun ic sinirlarini dondurur."""
    if not metin.startswith("---"):
        return None
    son = metin.find("\n---", 3)
    if son == -1:
        return None
    return 3, son + 1


def aciklama_degistir(metin: str, yeni: str) -> tuple[str | None, str | None]:
    """description alanini tek satirlik alintiya cevirir.

    Devam satiri deseni YAML blok skalarlarini (`|`, `>`) da kapsar; duz
    `^description:.*$` regex'i onlarin ilk satirini okuyup literal '|' dondurur.
    """
    sinir = frontmatter_sinirlari(metin)
    if not sinir:
        return None, "frontmatter yok"
    bas, bit = sinir
    fm = metin[bas:bit]

    m = re.search(r"^description:.*(?:\n(?:[ \t]+\S.*|[ \t]*))*", fm, re.M)
    if not m:
        return None, "description alani yok"

    kacisli = yeni.replace('"', "'")
    yeni_fm = fm[:m.start()] + f'description: "{kacisli}"\n' + fm[m.end():].lstrip("\n")
    return metin[:bas] + yeni_fm + metin[bit:], None


def govde(metin: str) -> str:
    """Frontmatter sonrasi govde — degismedigini dogrulamak icin."""
    sinir = frontmatter_sinirlari(metin)
    return metin[sinir[1]:] if sinir else metin


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tablo", type=Path, help="JSON tablo yolu")
    ap.add_argument("--uygula", action="store_true", help="diske yaz (varsayilan kuru kosum)")
    ap.add_argument("--kok", type=Path, default=KOK, help="skill kok dizini")
    a = ap.parse_args()

    if not a.tablo:
        print("HATA: --tablo gerekli. Bicim: {\"kategori/ad\": \"Use when ... .\"}")
        return 2
    if not a.tablo.exists():
        print(f"HATA: tablo bulunamadi: {a.tablo}")
        return 2

    tablo: dict[str, str] = json.loads(a.tablo.read_text(encoding="utf-8"))
    print("KURU KOSUM (yazmak icin --uygula)\n" if not a.uygula else "UYGULANIYOR\n")

    tamam = atlanan = hata = zayif = 0
    for parca, yeni in tablo.items():
        yol = a.kok / parca / "SKILL.md"
        if not yol.exists():
            print(f"  YOK      {parca}")
            atlanan += 1
            continue

        onceki = yol.read_text(encoding="utf-8")
        sonuc, hata_mesaji = aciklama_degistir(onceki, yeni)
        if sonuc is None:
            print(f"  HATA     {parca}: {hata_mesaji}")
            hata += 1
            continue

        # govde degismemis olmali
        if govde(sonuc) != govde(onceki):
            print(f"  IPTAL    {parca}: govde degisti, yazilmadi")
            hata += 1
            continue

        pencere = yeni[:PENCERE]
        if TETIKLEYICI.search(pencere):
            isaret = "OK"
        else:
            isaret = "ZAYIF"
            zayif += 1
        if len(yeni) > OLUSTURMA_SINIRI:
            isaret += "*"  # mevcut skilde sorun degil, YENI olusturmada reddedilir

        print(f"  {isaret:8s} {parca.split('/')[-1]}")
        print(f"           {PENCERE}kr: '{pencere}'")

        if a.uygula:
            yol.write_text(sonuc, encoding="utf-8")
        tamam += 1

    print(f"\nislenen: {tamam} | atlanan: {atlanan} | hata: {hata} | zayif: {zayif}")
    if zayif:
        print(f"ZAYIF = ilk {PENCERE} karakterde tetikleyici yok, yeniden yaz.")
    print("* = yeni skill olustururken reddedilir (>60 kr), mevcut skilde sorun degil.")
    if a.uygula:
        print("\nSimdi yeniden olc:  cd ~/.hermes/skills && skillcheck . --format json > /tmp/sonra.json")
    return 1 if (hata or zayif) else 0


if __name__ == "__main__":
    sys.exit(main())
