#!/usr/bin/env python3
"""
Burn subtitles into a video WITHOUT libass.

Why this exists: not every ffmpeg build ships libass. When it doesn't, the
`subtitles=file.srt` and `ass=file.ass` filters are simply absent and any
attempt fails with "Error parsing filterchain" -- which looks like a syntax
error but isn't. Detect with:

    ffmpeg -hide_banner -filters | grep -E "\\b(subtitles|ass)\\b"

If that comes back empty, use this script: it renders each cue to a transparent
PNG with PIL and composites them with the always-available `overlay` filter.

Usage:
    python3 burn-subtitles-pil.py <src.mp4> <subs.srt> <out.mp4>

Video resolution is probed automatically; font size scales to the frame height.
"""
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

# Fonts that carry full Latin-Extended (Turkish ı ş ğ İ, etc.)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

TILE_DIR = "/tmp/subtiles"
LINE_GAP = 8
BOTTOM_MARGIN = 26
SIDE_MARGIN = 70


def probe_size(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit("no suitable font found -- add one to FONT_CANDIDATES")


def _ts(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path):
    raw = open(path, encoding="utf-8").read().strip()
    cues = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        m = re.match(r"([\d:,]+)\s*-->\s*([\d:,]+)", lines[1])
        if not m:
            continue
        cues.append({"start": _ts(m.group(1)), "end": _ts(m.group(2)),
                     "lines": lines[2:]})
    return cues


def wrap(text, font, draw, max_w):
    out, cur = [], ""
    for w in text.split():
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def render(cue, idx, font, W, H, font_size):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    max_w = W - 2 * SIDE_MARGIN

    lines = []
    for raw_line in cue["lines"]:
        lines.extend(wrap(raw_line, font, d, max_w))

    lh = font_size + LINE_GAP
    total_h = lh * len(lines)
    y = H - BOTTOM_MARGIN - total_h

    pad_x, pad_y = 18, 10
    widths = [d.textlength(l, font=font) for l in lines]
    box_w = max(widths) + pad_x * 2
    box_x = (W - box_w) / 2
    d.rounded_rectangle(
        [box_x, y - pad_y, box_x + box_w, y + total_h + pad_y - LINE_GAP + 4],
        radius=8, fill=(0, 0, 0, 150))

    for i, line in enumerate(lines):
        x = (W - widths[i]) / 2
        ly = y + i * lh
        # outline first, fill on top -- keeps text legible over any background
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2),
                       (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            d.text((x + dx, ly + dy), line, font=font, fill=(0, 0, 0, 235))
        d.text((x, ly), line, font=font, fill=(255, 255, 255, 255))

    path = os.path.join(TILE_DIR, f"cue_{idx:03d}.png")
    img.save(path)
    return path


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: burn-subtitles-pil.py <src.mp4> <subs.srt> <out.mp4>")
    src, srt, out = sys.argv[1:4]

    W, H = probe_size(src)
    font_size = max(22, int(H * 0.056))
    font = load_font(font_size)

    os.makedirs(TILE_DIR, exist_ok=True)
    for f in os.listdir(TILE_DIR):
        os.remove(os.path.join(TILE_DIR, f))

    cues = parse_srt(srt)
    print(f"cues: {len(cues)}  video: {W}x{H}  font: {font_size}px")
    tiles = [render(c, i, font, W, H, font_size) for i, c in enumerate(cues)]

    cmd = ["ffmpeg", "-v", "error", "-i", src]
    for t in tiles:
        cmd += ["-i", t]

    parts, prev = [], "0:v"
    for i, c in enumerate(cues):
        lbl = f"v{i}"
        parts.append(
            f"[{prev}][{i+1}:v]overlay=0:0:"
            f"enable='between(t,{c['start']:.3f},{c['end']:.3f})'[{lbl}]")
        prev = lbl

    cmd += ["-filter_complex", ";".join(parts), "-map", f"[{prev}]", "-map", "0:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", out, "-y"]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED:", r.stderr[-2000:], file=sys.stderr)
        sys.exit(1)
    print("OK:", out, os.path.getsize(out) // 1024, "KB")
    print("NOW VERIFY VISUALLY -- extract a frame grid and inspect it.")


if __name__ == "__main__":
    main()
