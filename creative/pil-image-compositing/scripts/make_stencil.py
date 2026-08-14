#!/usr/bin/env python3
"""Logo PNG -> kesilebilir stencil (4 varyant).
Ada (harf ici bosluk) tespiti + otomatik ince kopru ekleme.
Kullanim: SRC ve OUTDIR yollarini ayarla, `python3 make_stencil.py` calistir.
Onemli: stdlib golgelemesine karsi ayri bir alt dizinde calistir (or. /tmp/stencil/).
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = "/tmp/stencil/logo.png"        # <-- girdi logosu
OUTDIR = "/tmp/stencil"              # <-- cikti dizini
os.makedirs(OUTDIR, exist_ok=True)

im = Image.open(SRC).convert("RGBA")
a = np.asarray(im)
H, W = a.shape[:2]

# logo maskesi: alfa>40 VE beyaz olmayan -> kesilecek (foreground) bolge
alpha = a[..., 3]
rgb = a[..., :3].astype(int)
logo = (alpha > 40) & (rgb.sum(2) < 720)

# --- ada tespiti: logo OLMAYAN bolgelerin baglantili bilesenleri ---
bg = ~logo
lbl, n = ndimage.label(bg)
# resmin kenarina degen label = dis zemin (kopru gerekmez)
edge_labels = set(lbl[0, :]) | set(lbl[-1, :]) | set(lbl[:, 0]) | set(lbl[:, -1])
edge_labels.discard(0)
islands = []
for li in range(1, n + 1):
    if li in edge_labels:
        continue
    ys, xs = np.where(lbl == li)
    if len(ys) < 30:            # cok kucuk gurultu -> atla
        continue
    islands.append((li, ys, xs))
print("ada sayisi:", len(islands))

# --- her ada icin ince dikey kopru ---
BW = max(4, int(H * 0.0065))     # kopru yari-genisligi (ince -> harf ici okunur kalsin)
bridged = logo.copy()
for li, ys, xs in islands:
    cx = int(xs.mean())
    y_top, y_bot = ys.min(), ys.max()

    def reach(direction):
        y = y_top - 1 if direction < 0 else y_bot + 1
        dist = 0
        while 0 <= y < H:
            if lbl[y, cx] in edge_labels:
                return dist
            y += direction
            dist += 1
        return 10 ** 9
    up = reach(-1)
    dn = reach(+1)
    if up <= dn:
        y0, y1 = y_top - up - 2, y_top
    else:
        y0, y1 = y_bot, y_bot + dn + 2
    y0 = max(0, y0)
    y1 = min(H, y1)
    bridged[y0:y1, max(0, cx - BW):min(W, cx + BW)] = False

def save(mask, path, fg, bgc, transparent_bg):
    out = np.zeros((H, W, 4), np.uint8)
    out[mask] = list(fg) + [255]
    if transparent_bg:
        out[~mask] = [0, 0, 0, 0]
    else:
        out[~mask] = list(bgc) + [255]
    Image.fromarray(out, "RGBA").save(path)

save(bridged, f"{OUTDIR}/stencil_bridged_transparent.png", (15, 15, 15), (255, 255, 255), True)
save(bridged, f"{OUTDIR}/stencil_bridged_white.png",       (15, 15, 15), (255, 255, 255), False)
save(bridged, f"{OUTDIR}/stencil_bridged_black.png",       (255, 255, 255), (15, 15, 15), False)
save(logo,    f"{OUTDIR}/stencil_silhouette_transparent.png", (15, 15, 15), (255, 255, 255), True)
print("uretildi: 4 varyant -", W, "x", H)
