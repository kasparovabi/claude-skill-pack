#!/usr/bin/env bash
# airdrop_send.sh <file> <recipient_name_or_slot>
#
# Autonomous AirDrop. Opens the share picker for <file>, then clicks the
# recipient identified by name (looked up in known_recipients.json) or by
# 1-based slot index. Returns 0 on success, prints diagnostic line on stdout.
#
# Recipient lookup precedence:
#   1. If the second arg is a positive integer, treat as slot.
#   2. Otherwise look it up in <skill_dir>/known_recipients.json.
#   3. Fail with hint to add the recipient to known_recipients.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
KNOWN="$SKILL_DIR/known_recipients.json"
SWIFT_SRC="$SCRIPT_DIR/airdrop.swift"
BIN_DIR="$HOME/Library/Hermes"
BIN="$BIN_DIR/airdrop"
CLICKER="$SCRIPT_DIR/airdrop_click_slot.applescript"

if [ $# -lt 2 ]; then
    echo "ERR: usage: airdrop_send.sh <file> <recipient_name_or_slot>" >&2
    exit 64
fi
FILE_PATH="$1"
RECIPIENT="$2"

[ -f "$FILE_PATH" ] || { echo "ERR: file not found: $FILE_PATH" >&2; exit 65; }

# Resolve slot index
SLOT=""
if [[ "$RECIPIENT" =~ ^[1-9][0-9]*$ ]]; then
    SLOT="$RECIPIENT"
else
    if [ -f "$KNOWN" ]; then
        SLOT=$(/usr/bin/python3 -c "
import json, sys
try:
    d = json.load(open('$KNOWN'))
except Exception:
    sys.exit(1)
v = d.get('$RECIPIENT')
if isinstance(v, int):
    print(v)
")
    fi
    if [ -z "$SLOT" ]; then
        echo "ERR: recipient '$RECIPIENT' not in $KNOWN" >&2
        echo "HINT: either pass a numeric slot (1-based, left-to-right in the picker)," >&2
        echo "      or edit $KNOWN to add: \"$RECIPIENT\": <slot>" >&2
        if [ -f "$KNOWN" ]; then
            ORDER_HINT=$(/usr/bin/python3 -c "
import json
try:
    d = json.load(open('$KNOWN'))
except Exception:
    raise SystemExit
order = d.get('_last_observed_order') or []
if order and isinstance(order, list):
    print('Last observed picker order (UNVERIFIED — agent vision guess):')
    for entry in order:
        if isinstance(entry, dict):
            slot = entry.get('slot')
            guess = entry.get('vision_guess', '?')
            verified = entry.get('verified_by_user', False)
            tag = ' [verified]' if verified else ''
            print(f'  slot {slot}: {guess}{tag}')
" 2>/dev/null)
            [ -n "$ORDER_HINT" ] && echo "$ORDER_HINT" >&2
        fi
        exit 66
    fi
fi

# Compile picker binary if missing or stale
mkdir -p "$BIN_DIR"
if [ ! -x "$BIN" ] || [ "$SWIFT_SRC" -nt "$BIN" ]; then
    echo "info: compiling $SWIFT_SRC -> $BIN" >&2
    swiftc "$SWIFT_SRC" -o "$BIN" 2>&1 >&2
fi

# Close any stale picker first so we get a fresh window
pkill -x airdrop 2>/dev/null || true
sleep 0.3

# Launch picker in background
"$BIN" "$FILE_PATH" >/dev/null 2>&1 &
PICKER_PID=$!

# Wait for the picker window to render with recipients
# Poll up to 5 seconds
DEADLINE=$(($(date +%s) + 5))
HOST=""
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    HOST=$(osascript -e 'tell application "System Events" to set ns to name of every process whose visible is true
on listHas(L, x)
    repeat with i in L
        if (i as string) is x then return true
    end repeat
    return false
end listHas
if listHas(ns, "airdrop") then
    return "airdrop"
else if listHas(ns, "swift-frontend") then
    return "swift-frontend"
end if
return ""' 2>/dev/null || true)
    [ -n "$HOST" ] && break
    sleep 0.3
done
if [ -z "$HOST" ]; then
    kill "$PICKER_PID" 2>/dev/null || true
    echo "ERR: picker process did not appear within 5s" >&2
    exit 67
fi

# Give recipient tiles time to populate (Bluetooth/WiFi discovery)
sleep 1.5

# Click the slot
RESULT=$(osascript "$CLICKER" "$SLOT" 2>&1 || true)
echo "$RESULT"

# Wait for "Waiting..." status on the clicked tile (signal that send fired)
# This is the AXStaticText sibling that appears under a chosen recipient.
sleep 1
STATUS=$(osascript -e "
tell application \"System Events\"
    tell process \"$HOST\"
        try
            set win to first window
            set out to \"\"
            repeat with elem in (entire contents of win)
                try
                    if role of elem is \"AXStaticText\" then
                        set t to value of elem
                        if t contains \"Bekleniyor\" or t contains \"Bekliyor\" or t contains \"Waiting\" or t contains \"Sending\" then
                            set out to out & t & linefeed
                        end if
                    end if
                end try
            end repeat
            return out
        end try
    end tell
end tell
" 2>/dev/null || true)

if [ -n "$STATUS" ]; then
    echo "STATUS: $STATUS"
    exit 0
fi
# Click likely succeeded but picker may have already finished — non-fatal
echo "STATUS: clicked, no waiting label observed (could be auto-accept on same Apple ID)"
exit 0
