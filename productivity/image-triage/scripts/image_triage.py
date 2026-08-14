#!/usr/bin/env python3
"""Image triage: characterise an image and produce recovery variants for dark shots.

Usage: python3 image_triage.py <path>
Pure PIL (no numpy — often absent in this env). Writes /tmp/_bright.png and
/tmp/_gamma.png (the most readable variant of an under-exposed photo).
"""
import sys
import collections
from PIL import Image, ImageEnhance, ImageOps


def main(path):
    im = Image.open(path)
    print(f"Size: {im.size}  Mode: {im.mode}")

    if im.mode == "RGBA":
        alpha = im.split()[3]
        ext = alpha.getextrema()
        print(f"Alpha min/max: {ext}"
              + ("  (fully opaque)" if ext == (255, 255) else "  (has transparency)"))

    # Flatten onto white
    rgb = Image.new("RGB", im.size, (255, 255, 255))
    if im.mode == "RGBA":
        rgb.paste(im, mask=im.split()[3])
    else:
        rgb.paste(im.convert("RGB"))

    # Dominant colors
    small = rgb.resize((80, 80))
    cols = collections.Counter(small.getdata())
    print("\nDominant colors (RGB -> count):")
    for c, n in cols.most_common(8):
        print(f"  {c} -> {n}")

    # 3x3 brightness map — locates the subject / bright region
    g = rgb.convert("L")
    w, h = g.size
    px = g.load()

    def blkmean(x0, x1, y0, y1):
        s = n = 0
        for y in range(y0, y1, 2):
            for x in range(x0, x1, 2):
                s += px[x, y]
                n += 1
        return s / n if n else 0

    print("\nBrightness map (3x3, 0=black 255=white):")
    for i in range(3):
        row = [f"{blkmean(j*w//3, (j+1)*w//3, i*h//3, (i+1)*h//3):5.0f}" for j in range(3)]
        print("  " + " | ".join(row))

    allv = [px[x, y] for y in range(0, h, 3) for x in range(0, w, 3)]
    mn, mx, mean = min(allv), max(allv), sum(allv) / len(allv)
    print(f"\nGlobal: min={mn} max={mx} mean={mean:.1f}"
          + ("   -> UNDER-EXPOSED, use _gamma.png for vision" if mean < 70 else ""))

    # Brightest-region centroid
    thr = sorted(allv)[int(len(allv) * 0.97)]
    xs = ys = c = 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            if px[x, y] >= thr:
                xs += x; ys += y; c += 1
    if c:
        print(f"Brightest region centroid: x={xs/c/w:.0%} width, y={ys/c/h:.0%} height")

    # Recovery variant 1: brightness x contrast + autocontrast
    b = ImageEnhance.Brightness(rgb).enhance(3.2)
    b = ImageEnhance.Contrast(b).enhance(1.6)
    b = ImageOps.autocontrast(b, cutoff=1)
    b.resize((w*3, h*3), Image.LANCZOS).save("/tmp/_bright.png")

    # Recovery variant 2: gamma 0.4 shadow lift + 4x upscale (usually the best)
    gam = 0.40
    lut = [min(255, int(((v/255.0)**gam)*255)) for v in range(256)]
    out = rgb.point(lut*3)
    out = ImageOps.autocontrast(out, cutoff=0.5)
    out.resize((w*4, h*4), Image.LANCZOS).save("/tmp/_gamma.png")
    print("\nWrote /tmp/_bright.png and /tmp/_gamma.png (hand _gamma.png to vision)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 image_triage.py <path>")
        sys.exit(1)
    main(sys.argv[1])
