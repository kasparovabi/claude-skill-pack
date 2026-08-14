#!/usr/bin/env python3
"""Logo/amblem PNG'sini parcacik nokta bulutuna cevirir.

Kullanim:
    python3 logo_to_points.py <logo.png> <cikti.json> [nokta_sayisi]

Cikti: {"points": [[x, y], ...]} — koordinatlar [-1,1], merkez 0,0, y yukari.
Noktalar merkeze uzakliga gore SIRALI doner; shader'da instance_index /
toplam orani dogal bir "icten disa olusum" gecikmesi verir.

AYAR NOKTALARI (logo degisirse bunlara bak):
  IC_YARICAP_ORANI : merkez motifi dis halkadan/cerceveden ayirir.
                     0.335 dis halkayi da aliyordu; 0.268 sadece motifi birakti.
  renk esigi       : varsayilan BEYAZ motif / renkli zemin varsayar.
                     Ters durumda beyaz_mi() fonksiyonunu degistir.
"""
import json
import math
import random
import sys

from PIL import Image

IC_YARICAP_ORANI = 0.268   # motif disindaki halka/cerceve bu oranla kirpilir
ORNEKLEME_ADIMI = 2        # her N pikselde bir bak (hiz icin)


def beyaz_mi(r, g, b, a):
    """Motif rengi testi. Beyaz motif / renkli zemin varsayimi."""
    if a < 200:
        return False
    return r > 205 and g > 205 and b > 205


def cikar(kaynak, hedef, istenen=2800):
    im = Image.open(kaynak).convert("RGBA")
    W, H = im.size
    px = im.load()

    cx, cy = W / 2.0, H / 2.0
    ic_yaricap = min(W, H) * IC_YARICAP_ORANI

    adaylar = []
    for y in range(0, H, ORNEKLEME_ADIMI):
        for x in range(0, W, ORNEKLEME_ADIMI):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > ic_yaricap * ic_yaricap:
                continue
            if beyaz_mi(*px[x, y]):
                adaylar.append((x, y))

    print(f"kaynak: {W}x{H}  aday piksel: {len(adaylar)}")
    if len(adaylar) < istenen:
        raise SystemExit(
            f"yeterli piksel yok ({len(adaylar)} < {istenen}). "
            "IC_YARICAP_ORANI'ni buyut ya da beyaz_mi() esigini gevset."
        )

    random.seed(42)   # tekrarlanabilir sonuc
    secilen = random.sample(adaylar, istenen)

    noktalar = []
    for x, y in secilen:
        nx = (x - cx) / ic_yaricap
        ny = -(y - cy) / ic_yaricap     # y yukari pozitif
        noktalar.append([round(nx, 3), round(ny, 3)])

    # icten disa olusum icin merkeze uzakliga gore sirala
    noktalar.sort(key=lambda p: math.hypot(p[0], p[1]))

    with open(hedef, "w", encoding="utf-8") as f:
        json.dump({"points": noktalar}, f, separators=(",", ":"))

    print(f"yazildi: {hedef}  ({len(noktalar)} nokta)")
    return noktalar


def onizleme(noktalar, cikti="/tmp/nokta_onizleme.png", boyut=600):
    """Nokta bulutunu PNG olarak ciz — motif taniniyor mu GOZLE dogrula."""
    from PIL import ImageDraw
    im = Image.new("RGB", (boyut, boyut), (10, 12, 18))
    dr = ImageDraw.Draw(im)
    for x, y in noktalar:
        pxx = int((x * 0.85 + 1) / 2 * boyut)
        pyy = int((-y * 0.85 + 1) / 2 * boyut)
        dr.ellipse([pxx - 1, pyy - 1, pxx + 1, pyy + 1], fill=(108, 242, 13))
    im.save(cikti)
    print(f"onizleme: {cikti}  <- vision_analyze ile BAK, motif taniniyor mu?")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 2800
    pts = cikar(sys.argv[1], sys.argv[2], n)
    onizleme(pts)
