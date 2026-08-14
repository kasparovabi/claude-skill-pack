#!/usr/bin/env python3
"""Draw platform safe-zone guides over a finished cover/banner so vision can
verify nothing critical is cropped. Outputs <input>_qa.jpg next to the input.

Usage:
    python3 qa_safezone_overlay.py /tmp/maarif_banner.jpg youtube
Platforms: youtube (2560x1440), twitter (1500x500), facebook (820x312).
The banner image MUST already be at the platform's full upload size.
"""
import sys
from PIL import Image, ImageDraw

# platform -> list of (label, w, h, color) safe boxes (centered)
SAFE = {
    # YouTube: desktop strip 2560x423 (yellow), mobile/all-device 1546x423 (green)
    "youtube": [
        ("MASAUSTU/TV serit 2560x423", 2560, 423, (255, 200, 0)),
        ("MOBIL/TUM CIHAZ GUVENLI ALAN 1546x423", 1546, 423, (0, 255, 120)),
    ],
    # Twitter/X header 1500x500; avatar overlaps bottom-left ~ keep clear
    "twitter": [
        ("TUM CIHAZ GUVENLI ~1500x360 (alt avatar bolgesi)", 1500, 360, (0, 255, 120)),
    ],
    # Facebook page cover 820x312 desktop / 640x360 mobile center-safe
    "facebook": [
        ("DESKTOP 820x312", 820, 312, (255, 200, 0)),
        ("MOBIL GUVENLI ~640x312", 640, 312, (0, 255, 120)),
    ],
}

def main():
    if len(sys.argv) < 3:
        print("usage: qa_safezone_overlay.py <image> <platform>")
        print("platforms:", ", ".join(SAFE))
        sys.exit(1)
    path, platform = sys.argv[1], sys.argv[2].lower()
    if platform not in SAFE:
        print("unknown platform:", platform, "->", list(SAFE))
        sys.exit(1)
    im = Image.open(path).convert("RGBA")
    W, H = im.size
    d = ImageDraw.Draw(im, "RGBA")
    for label, w, h, col in SAFE[platform]:
        x0, y0 = (W - w) // 2, (H - h) // 2
        x1, y1 = (W + w) // 2, (H + h) // 2
        d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=col + (255,), width=5)
        d.text((x0 + 12, y0 + 10), label, fill=col + (255,))
    out = path.rsplit(".", 1)[0] + "_qa.jpg"
    im.convert("RGB").save(out, quality=88)
    print("OK", out, "size", (W, H))

if __name__ == "__main__":
    main()
