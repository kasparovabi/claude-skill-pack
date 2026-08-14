#!/usr/bin/env bash
# send-video-to-telegram.sh
# Send a packed video file via Telegram Bot API sendVideo with proper width/height/duration.
# Without these fields Telegram displays the video as a square thumbnail regardless of file aspect.
#
# Usage: send-video-to-telegram.sh <token> <chat_id> <file> [caption] [thread_id]

set -euo pipefail

TOKEN="${1:?usage: $0 <token> <chat_id> <file> [caption] [thread_id]}"
CHAT="${2:?missing chat_id}"
FILE="${3:?missing file path}"
CAPTION="${4:-}"
THREAD="${5:-}"

[ -f "$FILE" ] || { echo "file not found: $FILE" >&2; exit 1; }

WIDTH=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of default=nw=1:nk=1 "$FILE")
HEIGHT=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 "$FILE")
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FILE" | cut -d. -f1)

FORMS=(
  -F "chat_id=${CHAT}"
  -F "video=@${FILE}"
  -F "width=${WIDTH}"
  -F "height=${HEIGHT}"
  -F "duration=${DURATION}"
  -F "supports_streaming=true"
)
[ -n "$CAPTION" ] && FORMS+=(-F "caption=${CAPTION}")
[ -n "$THREAD" ]  && FORMS+=(-F "message_thread_id=${THREAD}")

curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendVideo" "${FORMS[@]}"
