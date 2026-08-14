#!/usr/bin/env python3
"""Verify a WebGPU/canvas page actually ANIMATES and RESPONDS to the pointer.

Why this exists
---------------
The frozen-time query params (?t=) that make appearance checks reproducible
also make motion checks INVALID: they drive time from outside the page, so two
captures differ even when the page's own rAF loop is dead. That false pass has
shipped a frozen hero before.

So:
  * motion test      -> NO params, vary only --virtual-time-budget
  * interaction test -> freeze time, vary ONLY the pointer

Usage
-----
    python3 verify_motion.py file:///tmp/scene/index.html
    python3 verify_motion.py http://127.0.0.1:8911/v1.html --pointer 0.42,0.0

Exit code 0 if every checked branch moves, 1 otherwise.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
]

# mean abs channel diff (0-255). Tuned on real scenes: a live loop lands
# well above 1.0; a frozen page sits near 0.2 from dithering/grain alone.
ESIK = 0.6

BASE_FLAGS = [
    "--headless=new",
    "--enable-unsafe-webgpu",
    "--enable-features=Vulkan,WebGPU",
    "--use-angle=metal",
    "--hide-scrollbars",
]


def chrome_bul() -> str:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        try:
            subprocess.run([c, "--version"], capture_output=True, timeout=10, check=True)
            return c
        except Exception:
            continue
    sys.exit("Chrome/Chromium bulunamadi (CHROME_CANDIDATES listesini guncelle)")


def kare_al(chrome: str, url: str, hedef: Path, butce: int,
            boyut: str = "1280,720", ek: list[str] | None = None) -> None:
    komut = [chrome, *BASE_FLAGS,
             f"--screenshot={hedef}",
             f"--window-size={boyut}",
             f"--virtual-time-budget={butce}"]
    if ek:
        komut += ek
    komut.append(url)
    subprocess.run(komut, capture_output=True, timeout=180)


def fark(a: Path, b: Path) -> float:
    """Mean absolute luminance difference, 0-255."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        sys.exit("Pillow gerekli: pip install pillow")
    if not a.exists() or not b.exists():
        return -1.0
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L")
    px = list(d.getdata())
    return sum(px) / len(px) if px else 0.0


def ayir(url: str) -> str:
    return "&" if "?" in url else "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--pointer", default="0.0,0.0",
                    help="Interaction testi icin imlec konumu, 'x,y' (NDC)")
    ap.add_argument("--size", default="1280,720")
    ap.add_argument("--freeze-param", default="t",
                    help="Donmus zaman query parametresinin adi (varsayilan: t)")
    ap.add_argument("--pointer-param", default="m",
                    help="Imlec query parametresinin adi (varsayilan: m)")
    args = ap.parse_args()

    chrome = chrome_bul()
    tmp = Path(tempfile.mkdtemp(prefix="wgpu_verify_"))
    basarisiz = []

    # --- 1) MOTION: hicbir parametre YOK, sadece sure degisir -------------
    print("MOTION  (parametresiz, sadece virtual-time degisiyor)")
    senaryolar = [
        ("varsayilan", None),
        ("reduced-motion", ["--force-prefers-reduced-motion"]),
    ]
    for ad, ek in senaryolar:
        a, b = tmp / f"m_{ad}_a.png", tmp / f"m_{ad}_b.png"
        kare_al(chrome, args.url, a, 2500, args.size, ek)
        kare_al(chrome, args.url, b, 7000, args.size, ek)
        o = fark(a, b)
        if o < 0:
            print(f"  {ad:18} KARE ALINAMADI")
            basarisiz.append(ad)
            continue
        ok = o > ESIK
        print(f"  {ad:18} fark={o:7.3f}  ->  {'HAREKET VAR' if ok else 'STATIK'}")
        if not ok:
            basarisiz.append(ad)

    # --- 2) INTERACTION: zaman DONUK, sadece imlec degisir ----------------
    print("\nINTERACTION  (zaman donuk, sadece imlec degisiyor)")
    s = ayir(args.url)
    uzak = f"{args.url}{s}{args.freeze_param}=6.0&{args.pointer_param}=9,9"
    yakin = f"{args.url}{s}{args.freeze_param}=6.0&{args.pointer_param}={args.pointer}"
    a, b = tmp / "i_a.png", tmp / "i_b.png"
    kare_al(chrome, uzak, a, 7000, args.size)
    kare_al(chrome, yakin, b, 7000, args.size)
    o = fark(a, b)
    if o < 0:
        print("  KARE ALINAMADI")
        basarisiz.append("interaction")
    else:
        ok = o > 0.5
        print(f"  imlec uzak vs uzerinde  fark={o:7.3f}  ->  "
              f"{'ETKILESIM VAR' if ok else 'ETKILESIM YOK'}")
        if not ok:
            basarisiz.append("interaction")

    print(f"\nkareler: {tmp}")
    if basarisiz:
        print(f"BASARISIZ: {', '.join(basarisiz)}")
        return 1
    print("TUM KONTROLLER GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
