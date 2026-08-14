#!/usr/bin/env python3
"""Composite Turkish/Latin text onto a text-free background with pixel-perfect glyphs.

Usage: edit the CONFIG block, then `python3 compose_text.py`.
Renders an elegant centered serif title (auto-fit to width) with an optional
gold divider line + diamond. Verified to render ı ö ü ş ç ğ İ correctly with
Didot. Always vision_analyze the output before sending.
"""
from PIL import Image, ImageDraw, ImageFont

# ---------------- CONFIG ----------------
BG_PATH    = "/tmp/zemin.jpg"          # text-free background from image_gen.py
OUT_PATH   = "/tmp/final.jpg"
LINES      = ["Kurban Bayram\u0131n\u0131z", "M\u00fcbarek Olsun"]  # use \u escapes to be bash/encoding-safe
FONT_PATH  = "/System/Library/Fonts/Supplemental/Didot.ttc"
FONT_INDEX = 0                          # 0 regular; try 1 for italic in .ttc
GOLD       = (212, 175, 110)
WIDTH_FRAC = [0.74, 0.60]               # max width per line as fraction of image W
TOP_FRAC   = 0.55                       # y of first line as fraction of H
DIVIDER    = True                       # draw thin gold line + diamond above text
DIVIDER_Y  = 0.49
# ----------------------------------------

img = Image.open(BG_PATH).convert("RGB")
W, H = img.size
draw = ImageDraw.Draw(img)


def fit_font(text, target_w, start=140):
    s = start
    while s > 20:
        f = ImageFont.truetype(FONT_PATH, s, index=FONT_INDEX)
        bb = draw.textbbox((0, 0), text, font=f)
        if (bb[2] - bb[0]) <= target_w:
            return f, s
        s -= 2
    return ImageFont.truetype(FONT_PATH, 20, index=FONT_INDEX), 20


def center(text, font, y, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    x = (W - (bb[2] - bb[0])) // 2 - bb[0]
    draw.text((x, y), text, font=font, fill=fill)


if DIVIDER:
    cy = int(H * DIVIDER_Y)
    lw = int(W * 0.16)
    draw.line([(W // 2 - lw, cy), (W // 2 + lw, cy)], fill=GOLD, width=2)
    d = 6
    draw.line([(W//2-d, cy), (W//2, cy-d), (W//2+d, cy), (W//2, cy+d), (W//2-d, cy)],
              fill=GOLD, width=2)

y = int(H * TOP_FRAC)
for i, line in enumerate(LINES):
    frac = WIDTH_FRAC[i] if i < len(WIDTH_FRAC) else WIDTH_FRAC[-1]
    f, size = fit_font(line, int(W * frac))
    center(line, f, y, GOLD)
    y += size + int(H * 0.025)

img.save(OUT_PATH, quality=95)
print("saved", OUT_PATH)
