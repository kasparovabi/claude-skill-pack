#!/usr/bin/env python3
"""Bir repodaki Claude model kimliklerinin hala gecerli olup olmadigini kontrol eder.

NEDEN: Tarihli anlik goruntuler (claude-3-7-sonnet-20250219) emeklilik tarihine
kadar sorunsuz calisir, sonra her yerde AYNI ANDA patlar. Bu betik o sessiz
curumeyi kosulabilir bir kontrole cevirir.

Upstream PR'da maintainer "bir daha curumesin" dediginde takip commit'i olarak
gonderilir. Sifirdan farkli cikis kodu, zamanlanmis CI isine baglanabilmesi
icin kritik.

KULLANIM:
    python3 check_model_ids.py --offline   # sadece ne kullanildigini bas
    python3 check_model_ids.py             # canli API'ye karsi dogrula

CIKIS KODLARI:
    0  her kimlik hala sunuluyor (veya --offline)
    1  en az bir kimlik emekli olmus
    2  API'ye ulasilamadi

MUTASYON TESTI (gondermeden once ZORUNLU):
    emekli bir kimligi repoya geri koy -> cikis 1 ve dosya adi gorunmeli
    geri al -> cikis 0
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.anthropic.com/v1/models?limit=100"
API_VERSION = "2023-06-01"

# Sadece API'ye GERCEKTEN gonderilen kimlikleri yakalar.
# claude-code-action / claude-desktop gibi urun adlarini bilerek disarida birakir,
# yoksa rapor gurultuye bogulur ve kimse okumaz.
MODEL_RE = re.compile(
    r"claude-(?:opus|sonnet|haiku)-[0-9][a-z0-9-]*"
    r"|claude-[0-9][a-z0-9-]*-(?:opus|sonnet|haiku)[a-z0-9-]*"
)

SEARCH_SUFFIXES = {".py", ".yml", ".yaml", ".md", ".json", ".ts", ".js", ".toml"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}


def find_referenced_ids(root: Path) -> dict[str, list[str]]:
    """{model_id: [gectigi goreli yollar]} dondurur."""
    found: dict[str, list[str]] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SEARCH_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == Path(__file__).name:
            continue  # kendi regex orneklerimizi bulgu sanma
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in MODEL_RE.findall(text):
            rel = str(path.relative_to(root))
            found.setdefault(match, [])
            if rel not in found[match]:
                found[match].append(rel)
    return found


def fetch_served_ids(credential: str, header: str) -> set[str]:
    """header: 'x-api-key' veya 'authorization'.

    TUZAK: ANTHROPIC_AUTH_TOKEN bir OAuth token'idir ve x-api-key ile 401 verir,
    Authorization: Bearer ister. Iki bicimi de destekle yoksa kendi dogrulama
    betigin calismaz.
    """
    if header == "authorization":
        headers = {
            "authorization": f"Bearer {credential}",
            "anthropic-version": API_VERSION,
        }
    else:
        headers = {"x-api-key": credential, "anthropic-version": API_VERSION}
    req = urllib.request.Request(API_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    return {entry["id"] for entry in payload.get("data", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true",
                        help="API'yi cagirmadan sadece kullanilan kimlikleri listele")
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parent.parent,
                        help="taranacak depo koku (varsayilan: scripts/ ust dizini)")
    args = parser.parse_args()

    referenced = find_referenced_ids(args.root)
    if not referenced:
        print("No Claude model ids referenced in this repository.")
        return 0

    print(f"Referenced model ids ({len(referenced)}):")
    for model_id in sorted(referenced):
        print(f"  {model_id}")
        for location in referenced[model_id]:
            print(f"      {location}")

    if args.offline:
        return 0

    credential = os.environ.get("ANTHROPIC_API_KEY")
    header = "x-api-key"
    if not credential:
        credential = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        header = "authorization"
    if not credential:
        print("\nNeither ANTHROPIC_API_KEY nor ANTHROPIC_AUTH_TOKEN is set. "
              "Re-run with --offline to skip the live check.", file=sys.stderr)
        return 2

    try:
        served = fetch_served_ids(credential, header)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"\nCould not reach the Anthropic API: {exc}", file=sys.stderr)
        return 2

    print(f"\nAPI currently serves {len(served)} models.")

    stale = sorted(m for m in referenced if m not in served)
    if stale:
        print("\nRETIRED — these ids are referenced but no longer served:")
        for model_id in stale:
            print(f"  {model_id}")
            for location in referenced[model_id]:
                print(f"      {location}")
        return 1

    print("OK — every referenced model id is currently served.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
