---
name: scheduled-job-reliability
description: Use when a scheduled launchd/cron job silently didn't run.
---

# Scheduled Job Reliability (laptops that sleep)

Use when the user says **"bugünkü/dünkü X çalışmadı"**, "the cron didn't fire",
"post gelmedi", "PR atılmadı" — any recurring job that should have produced an
artifact and didn't. Also use proactively when *building* a new recurring job on
a laptop.

The single most common root cause on a MacBook is not a broken script. It is
**the machine was asleep, woke up for the timer, and had no network yet.**

## Diagnosis order (do not skip ahead)

### 1. Find the job — it may not be where you assume

**First disambiguate what "didn't run" refers to.** The user names jobs by their
*output*, not by the scheduler. "PR'lar çalışmadı" meant a launchd job that
opens PRs — not the PRs themselves, which were fine and untouched. Diagnosing
the artifacts instead of the job wastes a full round trip.

Cheap disambiguator: if the artifacts (PRs, posts, files) are unchanged since
*before* the quoted time, the producing job is the suspect. Ask for the time
window if it's still ambiguous — "13:30 civarında çalışması gereken cron" is the
answer that unblocks you.

Three separate schedulers coexist on this machine. Check all three:

```bash
# Hermes cron
# -> cronjob(action='list')
crontab -l 2>/dev/null | grep -vE '^\s*#' | grep -v '^$'   # system cron (often EMPTY)
ls ~/Library/LaunchAgents/*.plist                           # launchd (the real one, usually)
```

To find a launchd job by the time the user quoted, dump every schedule at once:

```bash
for f in ~/Library/LaunchAgents/*.plist; do
  h=$(plutil -extract StartCalendarInterval.Hour raw "$f" 2>/dev/null)
  m=$(plutil -extract StartCalendarInterval.Minute raw "$f" 2>/dev/null)
  [ -n "$h" ] && echo "$(basename $f) -> $h:$m"
done
```

The user's remembered time is approximate ("13:30 civarında" was really 13:34).
Match loosely. Then `plutil -p <plist>` to get `ProgramArguments`,
`WorkingDirectory`, `StandardOutPath`, `StandardErrorPath`.

### 2. Read the job's OWN log, not the scheduler's status
`last_status: ok` and exit code 0 are **not** evidence the work happened. Go to
the paths in the plist and to the job's run-log directory:

```bash
ls -lt state/runs/ | head -5
tail -30 state/runs/$(ls -t state/runs/ | head -1)
tail -25 state/launchd.err
```

### 3. Recognise the wake/network signature
These three together are conclusive:

- job log: `API Error: Unable to connect to API (ENOTFOUND)` (or `ENOTFOUND`,
  `Could not resolve host`, `Temporary failure in name resolution`)
- stderr: the **failure notification itself also failed** —
  `curl: (6) Could not resolve host: api.telegram.org`
- the job started within ~an hour of a wake, and other jobs that morning also
  ran late (09:30 job at 10:30, 10:00 job at 10:18)

Confirm the wake with:

```bash
pmset -g log 2>/dev/null | grep -E '^2026-08-07' | grep -E ' Sleep | Wake | DarkWake ' | head -30
```

Anchor the grep to `^<date>` — `pmset -g log` embeds future `wakeAt=` timestamps
inside *other* days' lines, so an unanchored `grep '2026-08-07'` returns matches
from days earlier and misleads you completely.

**Why this failure is invisible:** the notification channel needs the same DNS
the job just failed on. The job dies *and* cannot report dying. The user only
finds out by noticing a missing artifact, often days later.

## The fix — two independent parts, both required

Netting either one alone leaves a hole. The precheck stops the wasted burn;
the watchdog recovers the missed day.

### Part A — network precheck (fail closed, leave no stamp)

Insert **before** any real work, after the STOP/config guards:

```bash
AG_VAR=0
for _deneme in 1 2 3 4 5 6; do
    if curl -sf --max-time 8 -o /dev/null https://api.anthropic.com/v1/models 2>/dev/null \
       || curl -sf --max-time 8 -o /dev/null https://api.github.com 2>/dev/null; then
        AG_VAR=1; break
    fi
    sleep 10
done

if [ "$AG_VAR" -eq 0 ]; then
    echo "AG YOK (6 deneme, 60 sn). Tur baslatilmadi, telafi bekcisi tekrar deneyecek." >> "$LOG"
    exit 0
fi
```

Two design points that matter:
- **Probe the API you actually need**, not `8.8.8.8` — a captive portal or
  half-up VPN pings fine and still fails DNS for the real endpoint. Probe two
  hosts so one vendor's blip doesn't look like "no network".
- **Exit 0 and write NO success stamp.** Exiting non-zero triggers a failure
  alert for a condition that isn't a failure, and the missing stamp is exactly
  what tells the watchdog to retry.

### Part B — success stamp + catch-up watchdog

The job writes a stamp only on real success:

```bash
if [ $STATUS -eq 0 ]; then
    date +%F > "$ROOT/state/.son-basarili-tur"
fi
```

The watchdog checks that stamp, not the scheduler's status. Guards, in order —
each one prevents a distinct failure mode:

```bash
[ -f "$ROOT/STOP" ] && exit 0                      # user kill switch
SAAT=$(date +%H%M); [ "$SAAT" -lt 1400 ] && exit 0 # before the main run is even due
[ "$(cat "$DAMGA" 2>/dev/null)" = "$(date +%F)" ] && exit 0   # already succeeded today
pgrep -f "<job>/run-daily.sh" >/dev/null && exit 0  # main run in flight
[ "$SAYAC" -ge 3 ] && exit 0                        # daily trigger cap
# network check, then:
echo $((SAYAC + 1)) > "$SAYAC_DOSYA"
exec /bin/bash "$ROOT/run-daily.sh"
```

Schedule it hourly across the working window (14:15–21:15), `RunAtLoad=false`.
**Silent when idle** — no output at all unless it actually triggers.

Full worked example with the plist: `references/darkwake-catchup-watchdog.md`.

## Verify the watchdog before declaring done

An untested watchdog is worse than none — it creates false confidence. Test the
decision logic without running the real job by neutering only the exec line:

```bash
sed 's|exec /bin/bash "$ROOT/run-daily.sh"|echo TETIKLENDI|' telafi.sh > /tmp/telafi_test.sh
```

Then drive all three states and confirm each:

| Setup | Expected |
|---|---|
| stamp = yesterday, counter 0 | prints `TETIKLENDI`, counter → 1, log line written |
| counter = 3 | silent, no trigger |
| stamp = today | silent, no trigger |

Do **not** test by dropping a `STOP` file — `STOP` is checked first and short-
circuits the whole script, so you validate nothing downstream of it. That
mistake produced a passing-looking test that had exercised zero logic.

## Ters arıza: iş İKİ KEZ koştu

Bu skill'in geri kalanı işin *hiç* koşmamasını anlatıyor. Aynı sıklıkta görülen
ters arıza, aynı işin iki yerden birden koşmasıdır. Belirti farklı: eksik
artefakt değil, **çakışan artefakt**.

Doğrulanmış vaka (11 Ağu 2026): günlük tur hem Claude Routines görevinden hem
launchd betiğinden koştu. İki oturum aynı depoya, aynı daldan, iki dakika arayla
PR açtı; ikincisi işini çöpe atmak zorunda kaldı. Sebep: betik Routines limiti
dolduğu için kurulmuştu, limit sıfırlanınca eski görev de uyandı.

### Kullanıcı sebebi söylese bile kilidi yine de koy

Kullanıcı *"o hesabın limiti sıfırlanmış ve tekrar koşmuş ama onu kapadım"*
dedi. Kapatmak bu seferi çözer, **yapıyı çözmez**: `run-daily.sh` içinde hiçbir
eşzamanlılık koruması yoktu, dolayısıyla başka bir giriş noktası aynı anda
tetiklerse aynı şey tekrarlanırdı. Telafi bekçisinde `pgrep` kontrolü vardı ama
o yalnız kendini koruyordu, işin kendisini değil.

### Kilit: dizin, çünkü macOS'ta `flock` yok

`mkdir` atomiktir ve her yerde çalışır. PID'i içine yaz ki bayat kilit ayırt
edilebilsin:

```bash
KILIT="$ROOT/state/.kosum-kilidi"
if ! mkdir "$KILIT" 2>/dev/null; then
    SAHIP="$(cat "$KILIT/pid" 2>/dev/null || echo 0)"
    if [ "$SAHIP" -gt 0 ] && kill -0 "$SAHIP" 2>/dev/null; then
        echo "$(date '+%F %T') zaten kosuyor (pid $SAHIP), atlandi" >> "$ROOT/state/kilit.log"
        exit 0
    fi
    # sahibi olmus bayat kilit: devral, yoksa cokmus bir tur ertesi gunu bloklar
    rm -rf "$KILIT" && mkdir "$KILIT" 2>/dev/null || exit 0
fi
echo $$ > "$KILIT/pid"
trap 'rm -rf "$KILIT"' EXIT INT TERM
```

Bayat kilit devralma şart. PID kontrolü olmadan tek bir çökme işi kalıcı olarak
durdurur ve bu sessizce olur.

Yerleşim: `mkdir -p "$LOG_DIR"` sonrası, `STOP` kontrolünden **önce**. Trap'i
kilidi aldıktan hemen sonra kur, arada `exit` eden bir dal kalmasın.

### Üç durumu da test et — yazmak yeterli değil

Kilit mantığını gerçek işi çalıştırmadan doğrula: bloğu ayrı bir betiğe kopyala,
sahte PID'lerle sür.

| Kurulum | Beklenen |
|---|---|
| Kilit var, PID canlı (`sleep 300 &`) | `ATLANDI`, tetik yok |
| Kilit var, PID ölü (ör. 999999) | `BAYAT KILIT DEVRALINDI` |
| Kilit yok | `KILIT ALINDI` |

Üçü de doğrulanmadan "kilit eklendi" deme.

## Üçüncü arıza sınıfı: iş koştu ama ESKİ KURALLA koştu

İlk iki sınıf işin hiç koşmaması ve iki kez koşmasıydı. Üçüncüsü daha sinsi:
iş zamanında koşar, sıfır kodla çıkar, artefaktı üretir, ve **çıktı yanlıştır**
çünkü uyması gereken kuralı hiç okumamıştır. Hiçbir log satırı bunu göstermez.

Doğrulanmış vaka (13 Ağu 2026): kullanıcının yazım üslubu 1.120 gerçek mesajı
ölçülerek `METIN-PROTOKOLU.md` dosyasına yazıldı. Ertesi gün üretilen post eski
üslupla çıktı ve kullanıcı yakaladı: *\"bu sana dün söylediğim benim yazı
stilimle yazılmış gibi değil, önceki kurallarla yazılmış gibi duruyor\"*.

Sebep: cron işinin gömülü promptu **23.496 karakterdi** ve o dosyadan hiç
haberi yoktu. Kural dosyası güncellendi, motor okumadı. İki ayrı gerçek kaynak
oluştu ve sessizce ayrıştılar.

### Ölç, okuma

Prompt'un kuralı gerçekten taşıyıp taşımadığını göz kararı doğrulama. Kanıt
dizesini ara:

```python
pr = str(is_kaydi.get(\"prompt\", \"\"))
print(\"uzunluk:\", len(pr))
print(\"protokol referansi:\", \"METIN-PROTOKOLU\" in pr)
for iz in [\"unlem\", \"12 kelime\", \"ayrica\", \"1120\"]:
    print(\"  %-12s %s\" % (iz, iz in pr.lower()))
```

Hepsi `False` çıkıyorsa iş dünkü kuralla koşuyor demektir.

### Kalıcı düzeltme: kuralı promptun İÇİNE değil, BAŞINA bağla

Kuralı elle kopyalamak aynı ayrışmayı bir tur sonra geri getirir. Prompt'un en
başına, dosyayı **okumayı emreden** ve çatışmada dosyayı kazandıran bir blok
ekle:

```
=== YAZIM PROTOKOLU (OLCULDU, HER SEYDEN ONCE OKU) ===
~/.hermes/METIN-PROTOKOLU.md dosyasini OKU ve uygula. Asagidakiler ozeti,
catisma olursa DOSYA kazanir.
```

Özet kalabilir, ama tek gerçek kaynak dosyadır. Bloğu eklerken **aynı sınıftaki
bütün işleri** tara, sadece ana olanı değil: burada `linkedin-ai-post` ve
`linkedin-telafi` diye iki iş vardı ve telafi işi unutulsaydı eksik koşumlar
eski üslupla üretmeye devam ederdi.

```python
if \"linkedin\" not in ad.lower() and \"linkedin\" not in pr.lower()[:600]:
    continue
if \"METIN-PROTOKOLU\" in pr:          # idempotent, tekrar tekrar calistirilabilir
    continue
j[\"prompt\"] = BLOK + \"\\n\" + pr
```

`jobs.json`'u yazmadan önce yedekle ve yazdıktan sonra kanıt dizesini geri
okuyarak doğrula.

### Yön değişikliği de aynı yoldan gider

Aynı tuzak içerik stratejisi için de geçerli. Kullanıcı postların yönünü
değiştirmek istediğinde konuşmada anlaşmak yetmez; karar promptta yoksa yarınki
koşum eski sırayla üretir. Kararı gerekçesiyle birlikte yaz ve eski kuralı açıkça
ez (*\"bu liste eski KONU SECIM SIRASI kuralini EZER\"*), yoksa iki çelişen
talimat yan yana durur ve hangisinin kazandığı modele kalır.

> **Genel kural: bir zamanlanmış işin davranışını değiştiren her şey, o işin
> promptunda ya da okumaya zorlandığı bir dosyada yaşamalıdır. Sohbette verilen
> karar bir sonraki koşumda yoktur.**

## Pitfalls

- **`hermes` invoked bare from a script breaks under launchd.** Its shebang is
  `env python3`; in a scheduler's PATH that resolves to a different interpreter
  than the gateway's venv, and dependencies vanish
  (`ModuleNotFoundError: No module named 'yaml'`). Call the venv interpreter
  explicitly, with a fallback:
  ```bash
  HERMES_PY="$HOME/.hermes/hermes-agent/venv/bin/python"
  [ -x "$HERMES_PY" ] && exec "$HERMES_PY" "$HOME/.hermes/hermes-agent/hermes" cron run "$JOB_ID"
  ```
  Find the correct interpreter from the running service, never by guessing:
  `plutil -p ~/Library/LaunchAgents/<gateway>.plist | grep -A3 ProgramArguments`.
  Confirm before/after with `<interp> -c "import yaml; print(yaml.__version__)"`.
  Grep the whole script dir for the same bug: `grep -ln 'hermes-agent/hermes' ~/.hermes/scripts/*.sh`.
- **A watchdog that runs on the same trigger as the job it guards is not a
  watchdog.** It must be scheduled independently, on a different cadence.
- **Reproducing the failure in a shell usually succeeds** and proves nothing —
  your interactive PATH and network are healthy. The failure is environmental.
  Fix by construction (explicit interpreter, explicit precheck) rather than
  waiting to reproduce it.
- **`write_file` renders `&lt;`/`&gt;` literally into .plist files**, producing
  `Unexpected character & at line 1`. Always `plutil -lint` after writing a
  plist; repair with `python3 -c "import html; ..."` then reload.
  `launchctl load` can report success on a malformed plist — verify registration
  with `launchctl list | grep <label>`.
- **Exit code 0 ≠ the intended side effect happened.** After a recovery run,
  read the log and confirm the artifact (PR opened, message sent, file written).
  In one run the job exited 0 having deliberately opened no PR because its own
  policy said "resolve the open review first" — correct behaviour that would
  have been misreported as success-with-output if only the exit code were checked.
- **Distinguish "the job broke" from "the job decided not to act."** Report the
  second as a decision, not a fault, and leave it alone.
- Do not present a fix as done until you have run the real job end to end and
  read its log. "Betiği düzelttim" is not the deliverable; a green run is.
