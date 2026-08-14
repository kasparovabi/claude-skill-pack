#!/usr/bin/env python3
"""
Skill klasorunu herkese acik yayina hazirlar.

Uc kova mantigi:
  A) temiz  -> oldugu gibi kopyalanir
  B) kirli ama genellestirilebilir -> kurum/yol degistirilip kopyalanir,
     SONRA yeniden dogrulanir; hala kirliyse ATILIR
  C) listede -> hic alinmaz (kisiye/kuruma ozel skiller)

Olculen kacak orani: kova B'de 19 skillden 10'u ikinci taramada hala
kirli cikti. Temizlik sonrasi dogrulama ATLANMAZ.

Kullanim:
    python3 skill_pack_hazirla.py ~/.hermes/skills /tmp/paket \
        --kurum "Acme,Globex" --kimlik "12345678,-100999" \
        --disla "kurum-ici-akis,kisisel-otomasyon"
"""
import argparse
import re
import shutil
from pathlib import Path

BINARY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov",
          ".zip", ".tar", ".gz", ".pdf", ".woff", ".woff2", ".ttf",
          ".ico", ".so", ".dylib", ".pyc"}

DISLANAN_KLASOR = {".curator_backups", "index-cache", "__pycache__", ".git"}

BEYAZ = re.compile(
    r"example\.com|your-|<your|placeholder|kullanici@|000 0000|"
    r"127\.0\.0\.1|localhost|100\.64\.0\.0",
    re.I,
)


def sizinti_deseni(kurumlar, kimlikler):
    parcalar = [
        r"sk-[A-Za-z0-9_-]{16,}", r"ghp_[A-Za-z0-9]{20,}",
        r"xox[baprs]-[A-Za-z0-9-]{10,}", r"AIza[A-Za-z0-9_-]{25,}",
        r"/Users/[a-z0-9_-]+/", r"/home/[a-z0-9_-]+/",
        r"\+\d{1,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}",
        r"\b(?:10\.\d{1,3}|192\.168)\.\d{1,3}\.\d{1,3}\b",
    ]
    parcalar += [re.escape(k.strip()) for k in kurumlar if k.strip()]
    parcalar += [re.escape(k.strip()) for k in kimlikler if k.strip()]
    return re.compile("|".join(parcalar), re.I)


def temizleme_kurallari(kurumlar):
    kurallar = [
        (re.compile(r"/Users/[a-z0-9_-]+/"), "~/"),
        (re.compile(r"/home/[a-z0-9_-]+/"), "~/"),
    ]
    for ham in kurumlar:
        k = ham.strip()
        if not k:
            continue
        kurallar += [
            (re.compile(r"T[uü]rkiye\s+" + re.escape(k) + r"\s+\S+", re.I),
             "a client organisation"),
            (re.compile(re.escape(k) + r"'?[ıi]n\b", re.I), "the client's"),
            (re.compile(re.escape(k) + r"'?(e|te|de|ta|da)\b", re.I), "the client"),
            (re.compile(r"\b" + re.escape(k.upper()) + r"\b"), "CLIENT"),
            (re.compile(r"\b" + re.escape(k) + r"\b", re.I), "the client"),
        ]
    return kurallar


def kirli_mi(dizin, desen):
    for f in dizin.rglob("*"):
        if not f.is_file() or f.suffix.lower() in BINARY:
            continue
        try:
            m = desen.search(f.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if m and not BEYAZ.search(m.group(0)):
            return m.group(0)[:50], str(f.relative_to(dizin))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kaynak")
    ap.add_argument("hedef")
    ap.add_argument("--kurum", default="")
    ap.add_argument("--kimlik", default="")
    ap.add_argument("--disla", default="", help="hic alinmayacak skill adlari")
    a = ap.parse_args()

    kaynak = Path(a.kaynak)
    hedef = Path(a.hedef)
    kurumlar = a.kurum.split(",") if a.kurum else []
    kimlikler = a.kimlik.split(",") if a.kimlik else []
    dislanan = {x.strip() for x in a.disla.split(",") if x.strip()}

    desen = sizinti_deseni(kurumlar, kimlikler)
    kurallar = temizleme_kurallari(kurumlar)

    if hedef.exists():
        shutil.rmtree(hedef)
    hedef.mkdir(parents=True)

    temiz_gecen = 0
    temizlenip_gecen = 0
    liste_atlanan = 0
    kacak = []

    for skill_md in sorted(kaynak.rglob("SKILL.md")):
        bagil = skill_md.relative_to(kaynak)
        if any(p in DISLANAN_KLASOR for p in bagil.parts):
            continue

        dizin = skill_md.parent
        if dizin.name in dislanan:
            liste_atlanan += 1
            continue

        hedef_dizin = hedef / dizin.relative_to(kaynak)
        shutil.copytree(dizin, hedef_dizin,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))

        ilk = kirli_mi(hedef_dizin, desen)
        if not ilk:
            temiz_gecen += 1
            continue

        for f in hedef_dizin.rglob("*"):
            if not f.is_file() or f.suffix.lower() in BINARY:
                continue
            try:
                metin = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            yeni = metin
            for d, yerine in kurallar:
                yeni = d.sub(yerine, yeni)
            if yeni != metin:
                f.write_text(yeni, encoding="utf-8")

        kalan = kirli_mi(hedef_dizin, desen)
        if kalan:
            kacak.append((dizin.name, kalan[0], kalan[1]))
            shutil.rmtree(hedef_dizin)
        else:
            temizlenip_gecen += 1

    print("temiz gecen:        ", temiz_gecen)
    print("temizlenip gecen:   ", temizlenip_gecen)
    print("listeyle atlanan:   ", liste_atlanan)
    print("temizlenemeyen:     ", len(kacak))
    for ad, parca, dosya in kacak:
        print("   %-38s %-22s %s" % (ad[:38], parca, dosya[:40]))
    print()
    print("PAKETTEKI TOPLAM SKILL:", len(list(hedef.rglob("SKILL.md"))))
    print()
    print("Push oncesi son kontrol icin sizinti_tara.py'yi HEDEF klasorde calistir.")


if __name__ == "__main__":
    main()
