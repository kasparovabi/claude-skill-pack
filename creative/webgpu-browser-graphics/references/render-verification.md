# Render doğrulama: yanlış pozitiften kaçınmak

## Neden ayrı bir dosya

Bu oturumda kullanıcı "html dosyası statik açıldı, animasyon yok" dedi. Ben test
ettim, "hareket var" sonucu aldım, düzelttim sandım. Test yanlıştı. İkinci turda
gerçek testi yazınca hata ortaya çıktı. Bu dosya o dersi kalıcılaştırır.

## ⚠ Geçersiz test (yaptığım hata)

```bash
# YANLIS — ?t= zamani DISARIDAN veriyor
chrome --headless=new ... --screenshot=a.png "file:///sahne.html?t=2.0"
chrome --headless=new ... --screenshot=b.png "file:///sahne.html?t=5.5"
# a ve b farkli cikar. Ama sayfanin dongusu TAMAMEN DONMUS olsa bile farkli cikar.
```

Bu test shader'ın zamana tepki verdiğini kanıtlar, **sayfanın kendi kendine
ilerlediğini kanıtlamaz**. Kullanıcının şikayeti tam olarak ikincisiydi.

## ✅ Geçerli test

Hiçbir parametre verme. Aynı URL'yi farklı `--virtual-time-budget` ile yakala.
Fark varsa döngü gerçekten dönüyordur.

```python
#!/usr/bin/env python3
"""Gercek hareket testi: parametre YOK, sadece zaman gecirip iki kare al."""
import subprocess

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SAYFA = "file:///tmp/sahne.html"


def kare_al(hedef, butce, ek=None):
    komut = [
        CHROME, "--headless=new", "--enable-unsafe-webgpu",
        "--enable-features=Vulkan,WebGPU", "--use-angle=metal",
        f"--screenshot={hedef}", "--window-size=1280,720",
        f"--virtual-time-budget={butce}",
    ]
    if ek:
        komut += ek
    komut.append(SAYFA)
    subprocess.run(komut, capture_output=True, timeout=120)


def fark(a, b):
    from PIL import Image, ImageChops
    d = ImageChops.difference(
        Image.open(a).convert("RGB"), Image.open(b).convert("RGB")).convert("L")
    px = list(d.getdata())
    return sum(px) / len(px)


senaryolar = [
    ("NORMAL", None),
    ("REDUCED-MOTION ACIK", ["--force-prefers-reduced-motion"]),
]

for ad, ek in senaryolar:
    kare_al("/tmp/gt_a.png", 2500, ek)
    kare_al("/tmp/gt_b.png", 7000, ek)
    o = fark("/tmp/gt_a.png", "/tmp/gt_b.png")
    print(f"{ad:26} fark={o:7.3f}  ->  {'HAREKET VAR' if o > 0.6 else 'STATIK'}")
```

Eşik: ortalama piksel farkı > 0.6 → hareket var. Donuk sayfada ~0.2 çıkar
(film greni gibi rastgele bileşenler küçük fark üretir).

## `--force-prefers-reduced-motion` senaryosunu MUTLAKA koş

Windows kullanıcılarının çoğunda bu ayar açık. Bu bayrakla test etmezsen hatayı
kullanıcı bulur. Gerçek ölçüm (düzeltme öncesi/sonrası):

| senaryo | önce | sonra |
|---|---|---|
| normal | 12.733 (hareket var) | 13.102 |
| reduced-motion | **0.258 (STATIK)** | 18.441 |

## Etkileşim testi

Zamanı sabitle, sadece imleci değiştir; tek değişken kalsın.

```python
kare("/tmp/im_uzak.png", "9,9")        # imlec kadraj disinda
kare("/tmp/im_uzer.png", "0.42,0.0")   # imlec nesnenin uzerinde
# fark > 0.5 -> itme/etkilesim calisiyor
```

## Görsel doğrulama de şart

Piksel farkı "bir şey değişti" der, "doğru göründü" demez. Kare dizisini
kontak sayfası hâline getirip `vision_analyze` ile bak:

```python
from PIL import Image
import glob
fs = sorted(glob.glob('/tmp/kare_*.jpg'))[:6]
ims = [Image.open(f) for f in fs]
w, h = ims[0].size
s = Image.new('RGB', (w * 2, h * 3), (12, 12, 15))
for i, im in enumerate(ims):
    s.paste(im, ((i % 2) * w, (i // 2) * h))
s.save('/tmp/akis.jpg', quality=92)
```

Sorulacak sorular: kompozisyon merkezde mi, çakışma var mı, renk dengesi,
Türkçe karakterler doğru mu, bozuk kare var mı.
