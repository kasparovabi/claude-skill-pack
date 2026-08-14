# DarkWake catch-up watchdog — worked example

Reference implementation from the `claude5-readiness` (c5r) job, 7 Aug 2026.
Reproduce this shape for any launchd job that must not silently skip a day.

## The incident it came from

Job `com.kasparov.c5r-daily`, scheduled 13:34, opens PRs to upstream repos via
headless `claude -p`. On 7 Aug the user reported "öğlen 13:30 civarında
çalışması gereken repolara PR atan cron çalışmadı", noting the laptop lid was
closed.

Evidence chain, in the order it was gathered:

1. Not in Hermes cron and not in `crontab -l` (empty). Found in
   `~/Library/LaunchAgents` by dumping every plist's `StartCalendarInterval` —
   the user's "13:30" was actually **13:34**.
2. `state/runs/20260807-133844.log` — 463 bytes total:
   ```
   === c5r turu 20260807-133844 ===
   claude: ~/.local/bin/claude  surum: 2.1.224 (Claude Code)
   API Error: Unable to connect to API (ENOTFOUND)
   === bitti, cikis 1 ===
   ```
3. `state/launchd.err`:
   ```
   curl: (6) Could not resolve host: api.telegram.org
   notify: HTML gonderimi basarisiz (curl 0), duz metne dusuluyor
   curl: (6) Could not resolve host: api.telegram.org
   ```
   The failure alarm needed the DNS that had just failed. Nothing reached the user.
4. Corroboration from the same morning: the 09:30 job ran 10:30, the 10:00 job
   ran 10:18. Everything was shifted — a wake-storm morning.

Neither guard existed: no network precheck, no catch-up. `RunAtLoad` was
`false`, so opening the lid later did not retry either. The day was simply lost.

## Part A — precheck, placed after the STOP/config guards

```bash
# --- AG ON KONTROLU (7 Agu 2026) ---
# Mac kapagi kapaliyken launchd isi tetikliyor ama WiFi henuz baglanmamis
# oluyor (DarkWake). O anda claude ENOTFOUND alip cikiyor, Telegram bildirimi
# de gitmiyor: is sessizce kayboluyor. 10 sn arayla 6 kez dener, cikamazsa
# hic baslamaz ve telafi damgasi birakmaz, boylece bekci sonra tekrar dener.
AG_VAR=0
for _deneme in 1 2 3 4 5 6; do
    if curl -sf --max-time 8 -o /dev/null https://api.anthropic.com/v1/models 2>/dev/null \
       || curl -sf --max-time 8 -o /dev/null https://api.github.com 2>/dev/null; then
        AG_VAR=1
        break
    fi
    sleep 10
done

if [ "$AG_VAR" -eq 0 ]; then
    echo "=== c5r turu $STAMP ===" >> "$LOG"
    echo "AG YOK (6 deneme, 60 sn). Tur baslatilmadi, telafi bekcisi tekrar deneyecek." >> "$LOG"
    exit 0
fi
```

~60 s of tolerance. Wi-Fi association after a lid-open typically completes well
inside that.

## Part B — success stamp at the end of the main script

```bash
echo "=== bitti, cikis $STATUS ===" >> "$LOG"

if [ $STATUS -eq 0 ]; then
    # Basari damgasi: telafi bekcisi bugun tur kostu mu diye buna bakar.
    date +%F > "$ROOT/state/.son-basarili-tur"
fi

if [ $STATUS -ne 0 ]; then
    TAIL="$(tail -c 400 "$LOG" | tr '\n' ' ' | tr -d '<>&')"
    "$ROOT/notify.sh" "<b>c5r turu basarisiz</b>%0Acikis kodu $STATUS%0A${TAIL}"
fi
```

## Part C — `telafi.sh`, complete

```bash
#!/bin/bash
# c5r telafi bekcisi (7 Agu 2026)
#
# NEDEN: 7 Agustos'ta 13:34 turu Mac kapagi kapaliyken tetiklendi, WiFi henuz
# baglanmamisti (DarkWake). claude ENOTFOUND aldi, Telegram bildirimi de ayni
# sebeple gitmedi. launchd kacirilan isi gun icinde TEKRAR DENEMIYOR, RunAtLoad
# da false. Sonuc: o gun hic PR atilmadi ve kimse haberdar olmadi.
#
# NE YAPAR: gun icinde belirli araliklarla bakar, bugun basarili tur kosulmamissa
# ve ag varsa turu yeniden baslatir. Gunde en fazla 3 tetik.
#
# SESSIZ CALISIR: yapacak is yoksa hicbir cikti uretmez.

set -uo pipefail

ROOT="$HOME/Developer/claude5-readiness"
DAMGA="$ROOT/state/.son-basarili-tur"
SAYAC_DOSYA="$ROOT/state/.telafi-$(date +%F)"
LOG="$ROOT/state/telafi.log"
BUGUN="$(date +%F)"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

[ -f "$ROOT/STOP" ] && exit 0

SAAT=$(date +%H%M)
[ "$SAAT" -lt 1400 ] && exit 0

if [ -f "$DAMGA" ] && [ "$(cat "$DAMGA" 2>/dev/null)" = "$BUGUN" ]; then
    exit 0
fi

if pgrep -f "claude5-readiness/run-daily.sh" >/dev/null 2>&1; then
    exit 0
fi

SAYAC=$(cat "$SAYAC_DOSYA" 2>/dev/null || echo 0)
if [ "$SAYAC" -ge 3 ]; then
    exit 0
fi

if ! curl -sf --max-time 8 -o /dev/null https://api.anthropic.com/v1/models 2>/dev/null \
   && ! curl -sf --max-time 8 -o /dev/null https://api.github.com 2>/dev/null; then
    exit 0
fi

echo $((SAYAC + 1)) > "$SAYAC_DOSYA"
echo "$(date '+%F %T') telafi tetigi #$((SAYAC + 1))" >> "$LOG"
exec /bin/bash "$ROOT/run-daily.sh"
```

Guard order is load-bearing. `STOP` first (user intent wins over everything),
time window before stamp check (otherwise it fires at 00:05 for a job not yet
due), `pgrep` before the counter (never double-run), counter before the network
probe (don't burn curls once capped).

## Part D — the plist

`StartCalendarInterval` takes an **array of dicts** for multiple daily times:

```xml
<key>StartCalendarInterval</key>
<array>
    <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>16</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>20</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>15</integer></dict>
</array>
<key>RunAtLoad</key>
<false/>
```

Install and verify:

```bash
plutil -lint ~/Library/LaunchAgents/com.kasparov.c5r-telafi.plist   # must print OK
launchctl unload ~/Library/LaunchAgents/com.kasparov.c5r-telafi.plist 2>/dev/null
launchctl load   ~/Library/LaunchAgents/com.kasparov.c5r-telafi.plist
launchctl list | grep c5r     # both daily and telafi must appear
```

### plist-writing trap actually hit

`write_file` emitted `&lt;?xml ...` literally, so `plutil -lint` failed with
`Unexpected character & at line 1`. Repair in place:

```bash
cd ~/Library/LaunchAgents && python3 -c "
import html
p='com.kasparov.c5r-telafi.plist'
s=open(p,encoding='utf-8').read()
open(p,'w',encoding='utf-8').write(html.unescape(s))
" && plutil -lint com.kasparov.c5r-telafi.plist
```

Always lint before `launchctl load`.

## Verification actually performed

```bash
bash -n run-daily.sh && bash -n telafi.sh     # syntax

# neuter only the exec line
sed 's|exec /bin/bash "$ROOT/run-daily.sh"|echo TETIKLENDI|' telafi.sh > /tmp/telafi_test.sh
```

| State driven | Result |
|---|---|
| stamp = 2026-08-06, counter cleared | `TETIKLENDI`, counter `1`, `telafi tetigi #1` logged |
| counter = 3 | silent |
| stamp = today | silent |

Then the real missed run was executed: exit 0, stamp written, and the run log
read to confirm what it actually did. It had opened **no** PR — by its own rule
("bakımcı değişiklik istedi, önce onu çöz"), with daily budget 0 PR, weekly
11/12, 7 open. That is a policy decision, not a fault; reported as such.

## Companion bug found in the same sweep

`~/.hermes/scripts/linkedin_telafi.sh` called `hermes` bare and had been dying
at 10:00 with `ModuleNotFoundError: No module named 'yaml'` — the LinkedIn
watchdog was itself broken and nobody noticed, because the primary job happened
to succeed. Interpreter survey:

| Interpreter | yaml |
|---|---|
| `/usr/bin/python3` (3.9.6) | yes |
| `/opt/homebrew/bin/python3` (3.14.6) | **no** ← where bare `hermes` landed |
| `~/miniconda3/bin/python3` (3.10.8) | yes |
| `~/.hermes/hermes-agent/venv/bin/python` (3.11.15) | yes ← what the gateway plist uses |

Fixed by pinning the venv interpreter with a fallback. Lesson: when you find one
scheduled job broken, grep the sibling scripts for the same call shape before
you close the task.
