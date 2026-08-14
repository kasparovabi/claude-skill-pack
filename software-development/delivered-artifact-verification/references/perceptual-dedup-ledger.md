# Perceptual dedup ledger — case study and working code

Reference case: 4 Aug 2026. A daily cron posts a text post plus a captioned
meme video to a Telegram topic. The user reported that the video sent that
morning was the same scene as the one sent the previous evening.

## What I got wrong, in order

1. **Compared the wrong pair.** I diffed `/tmp/meme_20260803_tr.mp4` against
   `/tmp/meme_20260804_tr.mp4`. But the previous evening's delivery was a
   hand-made file, `bilissel-borc-parodi.mp4`, sitting in the outbox and
   matching no naming convention I had assumed. My comparison was precise
   and about two irrelevant files.

2. **Used a byte hash for a perceptual question.** MD5 over the first 8 MB
   returned "different", so I told the user the videos were different. Both
   clips had burned-in Turkish subtitles and different cut points, so byte
   identity was guaranteed to differ regardless of what was on screen.

3. **Kept measuring after being contradicted twice.** I produced a per-frame
   Hamming distance table as the third rebuttal. The user's reply was
   "oğlum GIF falan değil lan bu videoyu gönderdin ve bu yanlış". The
   correct move two rounds earlier: ask which file they received.

4. **Only saw it when I rendered frames side by side and looked.** A 2x3
   contact sheet of both clips made the answer obvious in one glance.

## Root cause (structural, not perceptual)

The dedup ledger held only source URLs, and it was written by a *separate
step* described in the cron prompt: "send the video, then append the URL".

- Automated runs followed the prompt and appended.
- Hand-made deliveries never ran that step.
- So the ledger was missing exactly the entries that caused the collision.

Two secondary defects: a URL-only ledger cannot tell "different clip, same
show" from "genuinely new", and one line in the file had two URLs
concatenated with no separator, so even URL matching was unreliable.

## Fix 1 — record inside the send function

```python
with urllib.request.urlopen(req, timeout=60) as r:
    result = json.loads(r.read())
    if result.get("ok"):
        hedef = f"topic={topic_id}" if topic_id else "genel akis"
        print(f"OK ({hedef})")
        # Ledger write lives HERE, in the success branch of the only
        # function that can deliver. No separate step to forget.
        try:
            import subprocess as _sp
            _sp.run([sys.executable,
                     os.path.expanduser("~/.hermes/scripts/meme_video_kaydi.py"),
                     "kaydet", file_path, caption[:60]],
                    capture_output=True, timeout=90)
        except Exception as e:
            print(f"UYARI: ledger write failed: {e}", file=sys.stderr)
    else:
        print("HATA:", result.get("description", ""), file=sys.stderr)
        sys.exit(1)
```

## Fix 2 — fingerprint frames, not bytes

Full script lives at `~/.hermes/scripts/meme_video_kaydi.py`. Core:

```python
def parmak_izi(video):
    """5 frames at PROPORTIONAL positions, caption band cropped, aHash each."""
    sure = _sure(video)                      # ffprobe format=duration
    izler = []
    for i, oran in enumerate([0.15, 0.3, 0.5, 0.7, 0.85], 1):
        gecici = f"/tmp/_mvk_{os.getpid()}_{i}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(sure * oran), "-i", video,
             "-frames:v", "1",
             # crop bottom 28%: burned-in subtitles must not dominate
             "-vf", "crop=iw:ih*0.72:0:0,scale=160:-1",
             gecici, "-y"], capture_output=True)
        if os.path.exists(gecici):
            izler.append(_ahash(gecici))
            os.remove(gecici)
    return izler

def _ahash(jpg, n=16):
    from PIL import Image
    im = Image.open(jpg).convert("L").resize((n, n))
    px = list(im.getdata())
    ort = sum(px) / len(px)
    return "".join("1" if v > ort else "0" for v in px)   # 256-bit
```

Two details that matter:

- **Proportional sampling** (`0.15 … 0.85`) not fixed seconds. Two cuts of
  the same scene with different lengths line up; absolute timestamps do not.
- **Crop before hashing.** Without the `crop=iw:ih*0.72`, re-subtitling the
  same clip changes enough pixels to read as a new video.

Comparison keeps the minimum distance across the frame cross-product, so a
match anywhere in either clip counts:

```python
def en_yakin(izler, kayitlar):
    en = (999, None)
    for k in kayitlar:
        for iz in izler:
            for eski in k.get("izler", []):
                d = sum(1 for x, y in zip(iz, eski) if x != y)
                if d < en[0]:
                    en = (d, k)
    return en
```

## Fix 3 — calibrate the threshold on real pairs

Measured on 7 real delivered videos, all 21 pairs:

| Comparison | Distance (of 256) |
|---|---|
| same file against itself | 0 |
| same scene, subtitles removed | 0–9 |
| same scene, uncut source | 10 |
| **closest known-different pair** | **58** |
| typical different pairs | 79–118 |

First guess was 55 — one unit below the closest genuine collision, which
would have fired false alarms. Final value:

```python
AYNI_ESIK = 30   # same ≤10, nearest different 58; 30 sits in the gap
```

Verified afterwards: re-sending yesterday's hand-made clip → `TEKRAR`
(distance 0); the subtitle-free variant of an already-sent clip → `TEKRAR`
(distance 0); a genuinely new clip → `TEMIZ` (distance 81).

## Fix 4 — backfill before trusting

An empty ledger approves everything already sent. Load every historical
delivery first:

```python
gecmis = sorted(
    glob.glob(os.path.expanduser("~/.pyto-outbox/**/_gonderildi/*.mp4"),
              recursive=True) +
    glob.glob("/tmp/meme_2026*_tr.mp4"),
    key=os.path.getmtime)
for p in gecmis:
    subprocess.run([PY, S, "kaydet", p, os.path.basename(p)[:40]],
                   capture_output=True, timeout=120)
```

21 videos loaded, then the three regression checks above were run.

## Content check still needs eyes

The ledger answers "have we sent this before". It does not answer "is this
usable". In the same session the first replacement candidate passed the
dedup check cleanly and was still unusable: it already carried burned-in
English captions, visible only on a rendered contact sheet. Second
candidate passed both and shipped.

Order of operations that works:

1. download candidate
2. `kontrol` → reject on `TEKRAR`, fetch another
3. render a contact sheet and **look** (right show? no burned-in text? no
   distressing content near the end?)
4. cut, transcribe, write captions, burn in
5. render again and look (diacritics intact? no overflow?)
6. send — ledger writes itself

## Sibling skill

The mirror-image problem — writing a check that verifies **someone else's**
fix landed (vendor punch list, audit remediation, deploy gate) — is covered by
`acceptance-check-design`. Same root cause as the byte-hash mistake above
(instrument not matched to the claim), plus the baseline-run discipline that
catches a probe reporting PASS while the defect is fully intact.
