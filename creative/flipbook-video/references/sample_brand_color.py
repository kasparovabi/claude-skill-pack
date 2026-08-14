#!/usr/bin/env python3
"""Bir kapak/logo görselinden baskın MARKA rengini örnekle.

Flipbook zemini için marka rengini TAHMIN ETME; kullanicinin kendi belgesinin
kapagindan ornekle. Cikti: en baskin marka tonu (RGB) + radyal gradyan icin
onerilen ic/dis renkler. the client turkuazi icin dogrulanmis maske esikleri
varsayilan; baska marka renkleri icin mask() fonksiyonunu degistir.

Kullanim:
    python3 sample_brand_color.py /path/kapak.png
"""
import sys
from collections import Counter
from PIL import Image


def is_turquoise(r, g, b):
    # Turkuaz/cyan ailesi: mavi-yesil baskin, kirmizi belirgin dusuk.
    return b > 110 and g > 110 and r < g - 20 and r < b - 20


def dominant(path, mask=is_turquoise, step=2):
    im = Image.open(path).convert("RGB")
    px = im.load()
    w, h = im.size
    c = Counter()
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if mask(r, g, b):
                # 8'lik kovalara nicele -> gurultu yerine baskin ton.
                c[(r & ~7, g & ~7, b & ~7)] += 1
    if not c:
        print("Maske hicbir piksel yakalamadi; mask() esiklerini gevset.")
        return None
    base = c.most_common(1)[0][0]
    # Ortalama (genel his) ve baskin (en yogun ton) ayri raporlanir.
    tot = sum(c.values())
    avg = tuple(round(sum(k[i] * v for k, v in c.items()) / tot) for i in range(3))
    return base, avg


def gradient_pair(base):
    r, g, b = base
    inner = (min(255, r + 18), min(255, g - 18), min(255, b - 18))  # merkez biraz acik
    outer = (max(0, r - 20), max(0, g - 76), max(0, b - 70))         # kenar koyu derinlik
    return inner, outer


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    res = dominant(sys.argv[1])
    if not res:
        sys.exit(2)
    base, avg = res
    inner, outer = gradient_pair(base)
    print(f"baskin marka tonu : RGB{base}")
    print(f"ortalama (genel)  : RGB{avg}")
    print(f"gradyan ic (merkez): RGB{inner}")
    print(f"gradyan dis (kenar): RGB{outer}")
