#!/usr/bin/env bash
# pack-video-for-telegram.sh
# Repack a video to fit Telegram's 50 MB sendVideo limit.
# Usage: pack-video-for-telegram.sh <input.mp4> [output.mp4] [target_mb=46] [height=480]
#
# Strategy: two-pass x264 at a duration-derived bitrate, AAC stereo audio at 48 kbps,
# faststart for inline playback. Output is 16:9 (or whatever the source aspect is) at
# the requested height. Prints the absolute output path on stdout for piping.

set -euo pipefail

IN="${1:?usage: $0 <input.mp4> [output.mp4] [target_mb=46] [height=480]}"
OUT="${2:-/tmp/$(basename "${IN%.*}")_packed.mp4}"
TARGET_MB="${3:-46}"
HEIGHT="${4:-480}"
AUDIO_K=48

# Source dimensions (for 16:9 scale math)
SRC_W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of default=nw=1:nk=1 "$IN")
SRC_H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 "$IN")
DUR_S=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$IN")
DUR_S_INT="${DUR_S%.*}"

# Target width preserving aspect, rounded to even number (x264 requires even dimensions)
TARGET_W=$(python3 -c "
w, h, dst = $SRC_W, $SRC_H, $HEIGHT
out_w = int(round(w * dst / h / 2)) * 2
print(out_w)
")

# Bitrate math: bits-per-second from target MB and duration, minus audio
TOTAL_K=$(python3 -c "print(int($TARGET_MB * 1024 * 8 / $DUR_S))")
VIDEO_K=$(( TOTAL_K - AUDIO_K ))
MAXRATE_K=$(( VIDEO_K * 130 / 100 ))
BUFSIZE_K=$(( VIDEO_K * 260 / 100 ))

if [ "$VIDEO_K" -lt 30 ]; then
  echo "WARN: video bitrate ${VIDEO_K}k is very low — output may look bad. Consider splitting." >&2
fi

echo "src=${SRC_W}x${SRC_H} dur=${DUR_S_INT}s -> ${TARGET_W}x${HEIGHT} v=${VIDEO_K}k a=${AUDIO_K}k target=${TARGET_MB}MB" >&2

PASSLOG="/tmp/ffmpeg2pass-$$"
trap "rm -f ${PASSLOG}-* /dev/null 2>&1 || true" EXIT

ffmpeg -y -i "$IN" -vf "scale=${TARGET_W}:${HEIGHT}" \
  -c:v libx264 -preset veryfast \
  -b:v ${VIDEO_K}k -maxrate ${MAXRATE_K}k -bufsize ${BUFSIZE_K}k \
  -passlogfile "$PASSLOG" -pass 1 -an -f mp4 /dev/null >&2

ffmpeg -y -i "$IN" -vf "scale=${TARGET_W}:${HEIGHT}" \
  -c:v libx264 -preset veryfast \
  -b:v ${VIDEO_K}k -maxrate ${MAXRATE_K}k -bufsize ${BUFSIZE_K}k \
  -passlogfile "$PASSLOG" -pass 2 \
  -c:a aac -b:a ${AUDIO_K}k -ac 2 \
  -movflags +faststart "$OUT" >&2

# Report final size
SZ=$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")
SZ_MB=$(python3 -c "print(f'{$SZ/1024/1024:.1f}')")
echo "done: $OUT (${SZ_MB} MB)" >&2

echo "$OUT"
