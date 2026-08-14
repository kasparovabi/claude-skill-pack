#!/usr/bin/env bash
# yt-to-telegram-mp3.sh — download a YouTube (or any yt-dlp-supported) URL as audio,
# repack to a Telegram-friendly mono MP3 under 50 MB, print the final path.
#
# Usage:
#   yt-to-telegram-mp3.sh <URL> [output_basename] [target_bitrate_k]
#
# Defaults:
#   output_basename = audio_<unix_ts>
#   target_bitrate_k = 48 (mono → ~22 MB per hour, fits ~3h in 50 MB)
#
# Outputs the absolute path of the final MP3 to stdout. All yt-dlp / ffmpeg
# chatter goes to stderr so callers can capture just the path.

set -euo pipefail

URL="${1:?URL is required}"
BASENAME="${2:-audio_$(date +%s)}"
BITRATE_K="${3:-48}"

WORKDIR="$(mktemp -d -t ytmp3.XXXXXX)"
trap 'rm -rf "$WORKDIR"' EXIT

RAW="$WORKDIR/raw.mp3"
FINAL="/tmp/${BASENAME}.mp3"

# Resolve yt-dlp: PATH first, then Homebrew Cellar fallback.
if command -v yt-dlp >/dev/null 2>&1; then
    YTDLP=yt-dlp
elif compgen -G "/usr/local/Cellar/yt-dlp/*/bin/yt-dlp" >/dev/null; then
    YTDLP="$(ls -t /usr/local/Cellar/yt-dlp/*/bin/yt-dlp | head -1)"
elif compgen -G "/opt/homebrew/Cellar/yt-dlp/*/bin/yt-dlp" >/dev/null; then
    YTDLP="$(ls -t /opt/homebrew/Cellar/yt-dlp/*/bin/yt-dlp | head -1)"
else
    echo "ERR: yt-dlp not found. brew install yt-dlp" >&2
    exit 1
fi

command -v ffmpeg >/dev/null 2>&1 || { echo "ERR: ffmpeg not found. brew install ffmpeg" >&2; exit 1; }

echo ">>> Downloading audio from $URL" >&2
"$YTDLP" -x --audio-format mp3 --audio-quality 0 \
         --restrict-filenames \
         -o "$WORKDIR/raw.%(ext)s" \
         "$URL" >&2

# yt-dlp may produce raw.mp3 or raw.NUMBER.mp3 in edge cases; grab whatever's there.
SRC="$(ls -1 "$WORKDIR"/raw*.mp3 2>/dev/null | head -1 || true)"
[ -n "$SRC" ] || { echo "ERR: yt-dlp produced no mp3" >&2; exit 1; }

echo ">>> Repacking to ${BITRATE_K} kbps mono → $FINAL" >&2
ffmpeg -y -loglevel error -i "$SRC" -b:a "${BITRATE_K}k" -ac 1 "$FINAL" >&2

SIZE_MB=$(du -m "$FINAL" | cut -f1)
echo ">>> Done. Size: ${SIZE_MB} MB" >&2

if [ "$SIZE_MB" -gt 50 ]; then
    echo "WARN: file exceeds Telegram bot 50 MB limit. Lower bitrate or split." >&2
fi

echo "$FINAL"
