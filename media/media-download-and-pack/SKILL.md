---
name: media-download-and-pack
description: Download audio/video from YouTube and other sites with yt-dlp, then repack with ffmpeg to hit a size/format target (e.g. Telegram's 50MB bot limit).
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [media, yt-dlp, ffmpeg, youtube, audio, video, telegram, transcoding, compression]
    related_skills: [youtube-content, songsee]
---

# Media download + pack

Two-step workflow that comes up constantly:

1. **Download** media from a URL with `yt-dlp` (YouTube, X/Twitter, most video sites).
2. **Pack** to a target size or format with `ffmpeg` so it fits a delivery channel.

The Telegram bot file-size limit (50 MB for `sendDocument`/`sendAudio`) is the most frequent reason to pack — anything over ~25 minutes of stereo MP3 at default quality blows past it. This skill covers the recipe end-to-end.

## When to use

- "İndir bu YouTube videosunu" / "download this video as audio" / "transcribe this YouTube link"
- Long-form audio (podcasts, press briefings, lectures) that needs to be delivered through Telegram, email, or any channel with size limits.
- Any site that yt-dlp supports — Twitter/X video, Vimeo, SoundCloud, Instagram reels, etc.

For pure transcript extraction (no audio file needed) use `youtube-content` instead — it goes straight to text via the transcript API.

## Audio-only vs video+audio — read the request carefully

Turkish speakers (and many others) distinguish between two requests that translate to similar English:

| Phrasing | Means | Use |
|---|---|---|
| "sesli indir" / "sesli bir şekilde indir" / "download with audio" | **video with sound** | full video, `-f "bv*+ba/b"` |
| "sesini indir" / "sadece ses" / "audio only" / "MP3 olarak indir" | **strip out the audio track** | `yt-dlp -x --audio-format mp3` |

If the user says "sesli indir" and you deliver an MP3, that's wrong — they wanted the video, just not silent. Re-read the request before defaulting to `-x`. When ambiguous, ask once; when not ambiguous, pick the right path the first time.

## Setup (one-time)

```bash
brew install yt-dlp ffmpeg
# or: pipx install yt-dlp  (if Homebrew Python conflicts with system Python)
```

Verify:

```bash
yt-dlp --version && ffmpeg -version | head -1
```

If `brew install yt-dlp` fails with `brew link` Python conflict (e.g. `/usr/local/bin/idle3 already exists`), the binary still installs under `/usr/local/Cellar/yt-dlp/<version>/bin/yt-dlp` and works fine — just call it by full path or run `brew link --overwrite python@3.14`.

## Download — common recipes

### Audio only, best quality MP3

```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  -o "%(title)s.%(ext)s" \
  "https://www.youtube.com/watch?v=VIDEO_ID"
```

`-x` = extract audio, `--audio-quality 0` = best (VBR ~245 kbps for MP3). `-o` template controls the output filename; `%(title)s` keeps the video title (be aware Turkish/Unicode characters and special chars like `?` / `/` will appear — sanitize if downstream tools choke).

### Audio only, smaller file from the start (skip the repack step)

```bash
yt-dlp -x --audio-format mp3 --audio-quality 9 \
  -o "%(title)s.%(ext)s" URL
# --audio-quality 9 = worst VBR (~64 kbps); fine for speech, terrible for music
```

For a deterministic bitrate, repack after download (see below) — `yt-dlp`'s quality flag is approximate.

### Video, best up to a height cap

```bash
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" \
  -o "%(title)s.%(ext)s" URL
```

### Just check what's available

```bash
yt-dlp -F URL          # list all formats
yt-dlp --get-title URL # title only
yt-dlp --get-duration URL
```

## Pack — fitting Telegram's 50 MB limit

`sendDocument` and `sendAudio` cap at 50 MB. Quick math for audio:

| Bitrate | Approx size per hour |
|---|---|
| 320 kbps stereo | 144 MB |
| 192 kbps stereo | 86 MB |
| 128 kbps stereo | 58 MB |
| 96 kbps mono | 43 MB |
| 64 kbps mono | 29 MB |
| 48 kbps mono | 22 MB |
| 32 kbps mono | 14 MB |

For speech (interviews, briefings, lectures) **mono at 48–64 kbps** is the sweet spot — fully intelligible, fits 50 MB up to ~3 hours.

### Repack to target bitrate (preferred — predictable size)

```bash
ffmpeg -y -i input.mp3 -b:a 48k -ac 1 output.mp3
# -b:a 48k = 48 kbps audio, -ac 1 = mono, -y = overwrite
```

For music, keep stereo and bump to 96k or 128k:

```bash
ffmpeg -y -i input.mp3 -b:a 96k -ac 2 output.mp3
```

### Repack with a hard size target

```bash
# Target 45 MB given duration in seconds
target_mb=45
duration_s=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.mp3)
bitrate_k=$(python3 -c "print(int($target_mb * 1024 * 8 / $duration_s))")
ffmpeg -y -i input.mp3 -b:a ${bitrate_k}k -ac 1 output.mp3
```

### Trim before repacking (if only part is needed)

```bash
ffmpeg -y -ss 00:05:00 -to 00:25:00 -i input.mp3 -b:a 64k -ac 1 output.mp3
```

## Pack video for Telegram (50 MB cap)

Sending video through `sendVideo` has the same 50 MB ceiling but adds two extra failure modes the first time around:

1. **Aspect ratio gets mangled** if you don't tell Telegram the dimensions explicitly. Default `sendVideo` calls without `width`/`height`/`duration` end up showing as a square thumbnail regardless of the file's actual aspect. ALWAYS pass `width`, `height`, and `duration` form fields — read them from `ffprobe` after the final encode.
2. **CRF mode can blow past size targets** on long videos. For predictable size on a 47-minute press briefing, use **two-pass x264 with explicit bitrate** rather than CRF.

### Reference recipe — 47-minute talking head, fits 50 MB

```bash
# Two-pass, 80 kbps video, 48 kbps stereo audio, 480p, 16:9
rm -f /tmp/ffmpeg2pass-*.log*
ffmpeg -y -i input.mp4 -vf "scale=854:480" \
  -c:v libx264 -preset veryfast \
  -b:v 80k -maxrate 110k -bufsize 220k \
  -pass 1 -an -f mp4 /dev/null

ffmpeg -y -i input.mp4 -vf "scale=854:480" \
  -c:v libx264 -preset veryfast \
  -b:v 80k -maxrate 110k -bufsize 220k \
  -pass 2 -c:a aac -b:a 48k -ac 2 \
  -movflags +faststart output.mp4
```

Resulting size: ~46 MB for ~47 minutes. Quality is bearable for press conferences and talking heads, NOT for action or music videos. For shorter content, raise `-b:v` proportionally (e.g. 250k for 15 minutes).

### Picking video bitrate from duration and target size

```bash
target_mb=46     # leave 4 MB headroom under 50 MB
duration_s=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 input.mp4)
audio_k=48
total_k=$(python3 -c "print(int($target_mb * 1024 * 8 / $duration_s))")
video_k=$(( total_k - audio_k ))
echo "video bitrate target: ${video_k}k"
```

### Common pitfalls during video pack

- **Avoid libx265** for "make it small fast" jobs — `-preset medium` runs at 1.5× realtime on a 47-min source. Use libx264 with two-pass; quality difference is negligible at these bitrates.
- **Single-pass x264 with `-crf 32`** is fast but unpredictable on size. A 47-min source can land anywhere from 35 to 60 MB. Use two-pass when you need to hit the limit reliably.
- **`scale=-2:360` produces 640×360**. If the source is 16:9, that's fine and stays 16:9. But Telegram will still square-up the thumbnail unless you pass `width`/`height` in the API call (see next section).
- **Don't pre-compress the source before pack pass**. Download the highest reasonable input (`bv*[height<=480]+ba/b[height<=480]` is enough), then do ONE pack pass to the final size. Compressing twice (download in MP3, then re-encode) wastes quality.
- **`-movflags +faststart`** is mandatory for Telegram streaming — without it, Telegram has to download the whole file before playback starts.

## Pack to a DURATION cap (e.g. "meme videos, max 60 seconds")

Size is not the only target a delivery channel imposes — a recurring one is a
hard **duration** cap set by the user or the platform. A 67-second clip that
must fit 60 seconds should be *fitted*, not discarded: cut the weakest interval
and apply a slight speed-up.

```bash
# 1. Cut an interval OUT (pick the most repetitive / least funny stretch)
ffmpeg -v error -i src.mp4 -t 5.96 -c:v libx264 -preset medium -crf 20 \
  -c:a aac -ar 48000 /tmp/pa.mp4 -y
ffmpeg -v error -ss 12.16 -i src.mp4 -c:v libx264 -preset medium -crf 20 \
  -c:a aac -ar 48000 /tmp/pb.mp4 -y
printf "file '/tmp/pa.mp4'\nfile '/tmp/pb.mp4'\n" > /tmp/concat.txt
ffmpeg -v error -f concat -safe 0 -i /tmp/concat.txt -c copy /tmp/mid.mp4 -y

# 2. Speed up slightly (1.02-1.05 is imperceptible; beyond ~1.10 audio chipmunks)
ffmpeg -v error -i /tmp/mid.mp4 \
  -filter_complex "[0:v]setpts=0.980392*PTS[v];[0:a]atempo=1.02[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 20 \
  -pix_fmt yuv420p -c:a aac -b:a 128k out.mp4 -y
```

Re-encode both halves to identical codec/params **before** the concat demuxer —
`-c copy` on the concat step only works if they match. `-ar 48000` on both keeps
the audio stream parameters aligned.

### The subtitle-drift trap

If the clip already has (or will get) subtitles, cutting the video **silently
desynchronises every cue after the cut**. Timestamps must be remapped through
the same cut + speed transform:

```python
def remap(t, cut_a, cut_b, speed):
    """Original time -> time after removing [cut_a, cut_b] and speeding up."""
    nt = t if t < cut_a else cut_a + (t - cut_b)
    return max(0.0, nt / speed)
```

Apply to both `start` and `end` of every cue; drop cues where `end <= start`
(they fell entirely inside the removed interval). `scripts/fit-video-duration.py`
does the whole cut + speed + SRT-remap in one call.

## Burning subtitles when the `subtitles=` / `ass=` filter is unavailable

Detect first — not every ffmpeg build ships libass:

```bash
ffmpeg -hide_banner -filters 2>/dev/null | grep -E "\b(subtitles|ass)\b"
# empty output => this build has no libass; `ass=file.ass` fails with
# "Error parsing filterchain", which is NOT a syntax error on your part
```

When it is missing (and reinstalling ffmpeg isn't worth it mid-task), render the
captions yourself and composite them with the always-present `overlay` filter:

**Read the error text — two different failures look alike.** Before falling back,
check which one you have, because the first is a quoting bug you should fix and
the second is the missing-filter case:

| ffmpeg says | Meaning |
|---|---|
| `Error parsing filterchain ... around:` (points at your string) | quoting/escaping problem, still fixable |
| `No option name near '/path/file.srt:force_style=...'` | the `:` in your path was read as an option separator |
| **`Filter not found`** | **libass genuinely absent — fall back to PIL** |

The middle row bites whenever the SRT path is absolute: `subtitles=` treats `:`
as its own argument delimiter. Passing the path through the shell adds a second
layer of quote mangling on top. Neither is a libass problem, so trying the PIL
fallback at that point hides a bug you could have fixed in one line — run from
the file's directory with a bare relative filename, or use
`subtitles=filename=<relative>` and escape the commas inside `force_style`.

Only after `Filter not found` should you switch strategies:

1. For each cue, draw a transparent RGBA PNG the size of the video: text bottom-
   centred, semi-transparent rounded backing box, 2 px black outline for contrast.
2. Feed every PNG as an extra input and chain one time-gated `overlay` per cue:

```
[0:v][1:v]overlay=0:0:enable='between(t,0.000,6.800)'[v0];
[v0][2:v]overlay=0:0:enable='between(t,6.800,8.000)'[v1]; ...
```

Cost is modest — 46 cues over a 2.5-minute 1280×536 clip rendered in ~40 s.
`scripts/burn-subtitles-pil.py` implements this end to end (auto-probes
resolution, scales font to `height * 0.056`, word-wraps to the safe width).

Font that reliably carries Turkish glyphs on macOS:
`/System/Library/Fonts/Supplemental/Arial Bold.ttf`.

### Resizing captions: scale BOTH knobs or the change is silently reverted

Any caption renderer worth using picks the font size in two stages — a seed size
derived from the frame (`min(H*0.048, W*0.055)`), then an **iterative shrink loop**
that keeps stepping down until the tallest cue fits under a box-height ratio
(`MAX_BOX_RATIO`, typically 0.25 of frame height).

So when the user says *"make the subtitles 1.5× bigger"*, multiplying the seed
alone does nothing: the shrink loop just claws it back to the same value. The
script exits 0, renders happily, and produces the old size. Nothing looks broken.

Scale the ratio by the same factor, and keep the factor in ONE constant:

```python
SUBTITLE_SCALE = 1.5
MAX_BOX_RATIO  = 0.25 * SUBTITLE_SCALE   # the loop's ceiling must grow too
MIN_FONT       = int(14 * SUBTITLE_SCALE)
# inside pick_font_size():
start = int(min(H * 0.048, W * 0.055) * SUBTITLE_SCALE)
start = max(MIN_FONT, min(start, int(46 * SUBTITLE_SCALE)))
```

Three separate hardcoded numbers guarantee that the next resize request updates
two of them and quietly breaks.

**Measure before rendering.** `pick_font_size` is a pure function — import the
script and call it across resolutions instead of encoding a whole video to eyeball
the result:

```python
spec = importlib.util.spec_from_file_location("bs", SCRIPT)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for W, H in [(360,640), (1080,1920), (1280,720)]:
    print(W, H, m.pick_font_size(cues, W, H))
```

Measured at 1.5×: 360×640 → 29 px (was 19), 1280×720 → 51 px (was 34),
1080×1920 → 69 px. If the ratio doesn't move, you forgot the second knob. When a
user asks for "N× bigger", prove the N — never eyeball it.

**Always verify the burn visually.** Extract a frame grid and actually look at it
before shipping — encoding succeeds happily with clipped, overflowing, or
mojibake text:

```bash
ffmpeg -v error -i out.mp4 -vf "fps=1/8,scale=520:-1" /tmp/vf/f_%02d.jpg -y
# tile the frames into one contact sheet, then inspect it with vision_analyze
```

### Don't re-send a clip you already sent — and don't use file hashes to check

On a recurring clip-delivery job the user said the video was *the same scene as
yesterday's*. It was. Three separate defects stacked, and the middle one is the
part almost everyone gets wrong.

**1. Record at send time, not as a follow-up step.** The dedup log was written
by a separate "now log it" instruction after delivery. Anything produced by hand
— outside the automated path — never reached that step, so the next day's run
treated it as unseen. Put the write **inside the send function**, right after the
API confirms success. If it can be skipped, it will be.

```python
if result.get("ok"):
    print(f"OK ({target})")
    try:
        subprocess.run([sys.executable, DEDUP_SCRIPT, "record", file_path,
                        caption[:60]], capture_output=True, timeout=90)
    except Exception as e:
        print(f"WARN: dedup record failed: {e}", file=sys.stderr)  # send still valid
```

**2. A URL is not an identity, and neither is a file hash.** Logging source URLs
misses the common case: a different clip from the same show reads as "the same
video" to a viewer while having a completely different URL. And file hashes are
actively misleading here — burned-in subtitles, a different cut point, and a
re-encode all guarantee a different hash for visually identical footage.

Compare **perceptual hashes of sampled frames**, cropping the subtitle band away
(bottom ~28%) so captions don't drive the comparison:

```python
def fingerprint(video, n=5):                 # aHash of 5 evenly-spaced frames
    for ratio in [0.15, 0.3, 0.5, 0.7, 0.85]:
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(dur * ratio),
                        "-i", video, "-frames:v", "1",
                        "-vf", "crop=iw:ih*0.72:0:0,scale=160:-1", tmp, "-y"])
        # 16x16 grayscale, bit per pixel vs. mean -> 256-bit string
```

Match = min Hamming distance across all frame pairs.

**3. Calibrate the threshold on real data; don't guess it.** Measured over 7 real
clips (21 pairs):

| relation | distance (of 256) |
|---|---|
| identical video | 0 |
| same scene, no subtitles burned | 0–9 |
| same scene, uncut source | 10 |
| **nearest genuinely-different pair** | **58** |
| typical different pairs | 79–118 |

Threshold **30** — catches re-sends comfortably, leaves 28 points of headroom
before the nearest false positive. An initial guess of 55 sat dangerously close
to 58 and would have started rejecting valid clips.

Backfill the log with everything already delivered before trusting it, then
verify the guard actually fires on a known-duplicate rather than assuming.

### Reading pixels to answer "is this the same video?" — verify visually too

Related trap from the same session: when the user says two clips are identical
and the numbers disagree, **look at frames side by side before arguing**. Frame
hashes came back 100+ apart (correctly — they were different clips), but that
number was used to push back on the user three times while the actual question
was about a *different pair of files* than the ones being measured. Build a
contact sheet of both candidates and inspect it; a wrong file pair produces
confident, useless measurements.

## Sourcing a clip to subtitle — search, then SCREEN

When the deliverable is "a short funny clip captioned to match this topic", the
download is the easy part. Two upstream steps decide whether the output is usable
at all.

### The clip belongs to the DELIVERABLE's subject, not to your last debugging session

Before searching, name the published subject in one phrase and hold it. The
companion clip is a metaphor for **that**, never a demo of the tooling you just
repaired.

Observed failure (14 Aug 2026): two bugs were found and fixed in the caption
pipeline on the way to producing a daily post. That repair became the clip — a
screen recording of the fixer running. The user's reaction: *"what is this
subtitle-fixer video, is that what I asked you for?"* Tool maintenance is
invisible work; it is not content and it is not the day's clip.

Pick the scene by asking *is this footage a metaphor for the subject?* A post
about why reusable instructions are worth writing pairs with a character who
sets out to change one lightbulb and gets pulled through six unrelated tasks —
the chain in the scene IS the argument in the post. A screen recording of your
own script is neither funny nor about the topic.

### When the usual aggregator returns nothing, switch source — don't stall

Comedy aggregators go quiet (rate limits, empty result windows, blocked JSON
endpoints). That is a signal to change source, not to stop or to substitute
something off-topic. Scripted sketch/sitcom search is the fallback and it is
usually the better source anyway.

Filter duration in the shell rather than with `--match-filter`, which is
unreliable over search results:

```bash
yt-dlp --flat-playlist \
  --print "%(duration)s|%(view_count)s|%(title).70s|%(id)s" \
  "ytsearch18:<query>" 2>/dev/null \
  | awk -F'|' '$1 != "NA" && $1 > 25 && $1 < 95'
```

`duration` of `NA` means a live stream or a restricted video — drop those rows.
Run two or three differently-angled queries before settling; a single query that
returns two weak candidates usually means the phrasing is wrong, not that no clip
exists.

### Search where dialogue actually exists

Social-video aggregators return mostly **dialogue-free** clips — nothing to write
parody lines over. Scripted sketch/sitcom comedy is far more productive. Query
patterns that reliably land:

- `"IT Crowd <topic> scene"`, `"office sketch comedy <topic>"`
- `"SNL sketch <topic>"`, `"<topic> parody sketch"`
- Corporate-meeting sketches (e.g. "The Expert") for anything about process,
  estimates, or management dysfunction

Filter by duration at search time so you never open a 74-minute reaction video:

```bash
yt-dlp --flat-playlist --no-warnings -j "ytsearch5:<query>" \
  | python3 -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l); dur = d.get('duration') or 0
    if 15 <= dur <= 300:
        print(f\"{dur:>4}s | {d.get('title','')[:66]} | {d.get('url','')}\")
"
```

`references/sketch-clip-sourcing.md` has the per-show breakdown (which series pay
off, which carry profanity), batched multi-query search, and the known-source trap
in detail.

### Screen the source BEFORE writing a single caption

Titles and subreddit/channel names do **not** tell you what is in a clip. Serious
news footage — surveillance, protest, accident, violence — sits in the same search
results as comedy, and a funny caption burned onto real footage is the kind of
mistake that gets noticed publicly.

This is a separate check from the post-burn visual QA further up: that one asks
*did my text render correctly*, this one asks *should I be captioning this clip at
all*. Do it on the **whole source**, before cutting.

`tile` chains directly onto `fps` in a single filtergraph — no need to write N
intermediate JPEGs and re-read them:

```bash
# whole-source safety screen: 8 s apart, 25 cells, ONE file to inspect
ffmpeg -v error -i CANDIDATE.mp4 -vf "fps=1/8,scale=300:-1,tile=5x5" /tmp/sheet.jpg -y
# post-burn caption QA on a ~60 s cut: 6 s apart, 10 cells is plenty
ffmpeg -v error -i OUT_tr.mp4  -vf "fps=1/6,scale=300:-1,tile=5x2" /tmp/qa.jpg -y
```

Size the grid so `cells >= ceil(duration / interval)`. Undersize it and ffmpeg
silently drops the tail — which is exactly where the dark-ending failure mode
lives. `scale=300` is small but ample for judging scene type, gore, and
surveillance imagery, and Turkish glyphs stay legible for caption QA.

Four questions, all must pass:

1. Genuinely comedy/parody, or is this a news clip?
2. Any surveillance, violence, accident, protest, death, or war imagery?
3. Any otherwise inappropriate content?
4. **Do the LAST frames turn dark or disturbing?** Clips that open innocently and
   end grim are a real failure mode — sample the full duration, not the opening.

Any doubt → skip the clip. Shipping no video beats shipping a risky one.

**A familiar show does not exempt a clip from the screen.** Classic workplace
sitcoms are the best hunting ground for dialogue-rich corporate comedy, and that
familiarity quietly turns into "this one's fine, skip the frames". It isn't. The
Office "First Aid Fail" (S5) is a CPR-training sketch that plays as pure office
comedy for two minutes and then has Dwight cut the face off the dummy and wear
it — genuinely graphic, and completely invisible from the title. The known-source
trap is the mirror image of the trust-the-subreddit trap: screen both the same way.

Also pull the audio transcript (`whisper --model small --language en
--output_format json`) before choosing your cut: it gives you both the timestamps
to build captions against and a check for profanity you need to cut around.

### Salvage by two-part cut: keep the setup and the punchline, drop the middle

A clip with a bad stretch in the *middle* usually doesn't need replacing. Scenes
of this kind carry their premise up front and their payoff in the closing lines,
and the offending section sits between them contributing nothing. Cutting to the
duration cap and cutting for content are the same operation — reuse the cut +
concat recipe from the duration section, just choose the interval by what the
screen flagged instead of by what's least funny.

```bash
cd /tmp
ffmpeg -v error -ss 0 -i src.mp4 -t 47 \
  -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 2 part_a.mp4 -y
ffmpeg -v error -ss 161.44 -i src.mp4 -t 12.16 \
  -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
  -c:a aac -ar 48000 -ac 2 part_b.mp4 -y
printf "file '/tmp/part_a.mp4'\nfile '/tmp/part_b.mp4'\n" > list.txt
ffmpeg -v error -f concat -safe 0 -i list.txt -c copy cut.mp4 -y
ffprobe -v error -show_entries format=duration -of csv=p=0 cut.mp4
```

Pin `-ar 48000 -ac 2` on **both** parts. The concat demuxer with `-c copy`
assumes identical stream parameters; mismatched sample rate or channel count
drops or garbles the audio of the second part and ffmpeg does not complain.

Read the transcript first to find where the payoff line actually is — that
timestamp determines the second cut point. Cutting before reading it throws the
punchline away and leaves you with a scene that just stops. Measure the joined
duration with `ffprobe` rather than adding the two `-t` values; `-ss` rounds to
keyframes.

### Write a parody dub, not a translation

Keep the scene's rhythm and the original segment timings, but rewrite the lines so
they land on the topic you're actually publishing about, with the punchline on the
final cue. Localize names and places — it reads as dubbing and lands better than
literal translation. Prefer generic phrasing ("the provider", "one model") over
naming real companies when the clip is going out under a work identity.

Then confirm in the post-burn frame grid that non-ASCII characters survived: caption
text written by an agent frequently degrades to ASCII (`gorunuyordu` for
`görünüyordu`). The font supports the glyphs; the failure is in the text you wrote.

For video specifically, the gateway's `MEDIA:/path` shortcut may default to `sendDocument`, which uploads the video but loses the inline player. To force the streamable player path, call `sendVideo` directly:

```bash
TOKEN="<bot-token>"
WIDTH=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of default=nw=1:nk=1 output.mp4)
HEIGHT=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 output.mp4)
DURATION=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 output.mp4 | cut -d. -f1)

curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendVideo" \
  -F "chat_id=${CHAT_ID}" \
  -F "video=@output.mp4" \
  -F "width=${WIDTH}" \
  -F "height=${HEIGHT}" \
  -F "duration=${DURATION}" \
  -F "supports_streaming=true"
```

The `width`/`height`/`duration` triple is what stops Telegram from showing the video as a square. `supports_streaming=true` enables the inline player without forcing a full download.

For audio, the equivalent is `sendAudio` with `duration` (and `title`/`performer` if known). For everything else, `sendDocument` is fine.

## End-to-end one-liner (YouTube speech → Telegram-ready MP3)

```bash
yt-dlp -x --audio-format mp3 -o "/tmp/raw.%(ext)s" URL && \
  ffmpeg -y -i /tmp/raw.mp3 -b:a 48k -ac 1 /tmp/final.mp3 && \
  ls -lh /tmp/final.mp3
```

### Reusable wrapper scripts

For the recurring "YouTube URL → Telegram-friendly MP3" task, use:

```bash
bash $SKILL_DIR/scripts/yt-to-telegram-mp3.sh "https://youtube.com/watch?v=ID" my_basename 48
# Prints the final mp3 path to stdout, progress to stderr.
# Handles: yt-dlp discovery (PATH or Homebrew Cellar), --restrict-filenames (no Unicode shell hazards),
# repack to mono 48 kbps, 50 MB warning.
```

For the "video → Telegram-friendly MP4 under 50 MB" task, use:

```bash
OUT=$(bash $SKILL_DIR/scripts/pack-video-for-telegram.sh /tmp/input.mp4)
# Optional: pack-video-for-telegram.sh <input> [output] [target_mb=46] [height=480]
# Computes bitrate from duration, runs two-pass x264, preserves aspect, faststart on.
# Prints absolute output path on stdout.
```

To upload with correct aspect (NOT square) call sendVideo with width/height/duration:

```bash
bash $SKILL_DIR/scripts/send-video-to-telegram.sh "$TOKEN" "$CHAT_ID" "$OUT" "optional caption"
# Probes ffmpeg for width/height/duration and posts to api.telegram.org/sendVideo.
# Returns the API JSON response on stdout.
```

To fit a hard duration cap (cut + speed-up, with SRT timestamps remapped):

```bash
python3 $SKILL_DIR/scripts/fit-video-duration.py in.mp4 out.mp4 \
  --cut 5.96 12.16 --speed 1.02 --srt-in in.srt --srt-out out.srt
# Prints source/after-cut/final durations and warns if still over the cap.
```

To burn subtitles on an ffmpeg build without libass:

```bash
python3 $SKILL_DIR/scripts/burn-subtitles-pil.py src.mp4 subs.srt out.mp4
# Renders each cue to a transparent PNG and composites via the overlay filter.
```

Capture the path with `OUT=$(bash .../yt-to-telegram-mp3.sh URL)` and send `MEDIA:$OUT` to the user.

## Filename sanitization

Turkish titles routinely produce filenames with `ı ö ü ş ç ğ` plus characters that confuse shells and `tirith` security scans (the `confusable_text` rule fires on mixed-script titles like "Cumhurbaşkanı … Tokayev"). When this happens:

1. Download with the original title.
2. Immediately `mv` to a plain ASCII name before any further `ffmpeg` / `curl` step:

   ```bash
   mv /tmp/*.mp3 /tmp/input.mp3
   ffmpeg -y -i /tmp/input.mp3 -b:a 48k -ac 1 /tmp/output.mp3
   ```

3. Pass `--restrict-filenames` to yt-dlp to make it strip non-ASCII at download time:

   ```bash
   yt-dlp -x --audio-format mp3 --restrict-filenames -o "/tmp/%(title)s.%(ext)s" URL
   ```

## Long-download pitfall (Hermes terminal timeout)

A 1-hour YouTube video at HD audio takes ~30–60 seconds to download. The Hermes `terminal` tool has a 60-second foreground timeout — long downloads MUST run as a background process:

```python
terminal(background=True, command="yt-dlp -x --audio-format mp3 -o /tmp/raw.%(ext)s URL",
         notify_on_complete=True)
# Then process_wait(session_id, timeout=60) one or more times until status="exited".
```

Don't keep retrying foreground — each retry restarts the whole download.

## Delivery

Once the file is at or under target size, hand it to the user. In the Pyto/Telegram bot context, return `MEDIA:/absolute/path` in your reply and the gateway uploads it as `sendDocument` (or `sendAudio` for `.mp3`). Don't pre-curl to the Bot API yourself unless the gateway is unavailable — duplicate uploads waste bandwidth and clutter the chat.

## Pitfalls

1. **Don't trust `--audio-quality` for size targets.** It's a VBR hint, not a hard bitrate. If you must hit ≤ 50 MB, repack with explicit `-b:a`.
2. **Stereo is wasted on speech.** Always go mono (`-ac 1`) for talking-head content.
3. **Default MP3 encoding from yt-dlp produces ~5× larger files than you'd guess** — it picks the highest source-compatible bitrate when `--audio-quality 0` is set.
4. **Geo-restricted / age-gated videos** fail with 403; yt-dlp can pass cookies via `--cookies-from-browser firefox` if the user is logged in there.
5. **YouTube's adaptive streams use DASH** — yt-dlp downloads in fragments (you'll see `frag 1410/1412` in the log). That's normal. Don't kill the process when you see fragment counters going past 100% — `~ 48.01MiB` is an estimate from one fragment generalized to the rest, the final count is accurate.
6. **`brew install yt-dlp` may fail with Python symlink conflicts on macOS** — the binary still installs and works; either call by full Cellar path or `brew link --overwrite python@3.14`.
7. **Telegram bot 50 MB is per-call**, not per-day. Splitting a 90-minute file into two 30 MB halves and sending sequentially is fine; the user gets two messages.
8. **A successful encode is not a correct render.** ffmpeg exits 0 on overlays that are clipped, overflowing, or showing mojibake. Whenever you composite text onto video, extract a frame grid afterwards and actually look at it before delivering.
9. **Don't discard a clip for being slightly over a duration cap.** 60-80 seconds fits 60 with one cut plus a 1.02-1.05× speed-up; hunting for a replacement clip usually costs more than fitting the one you have.
10. **Scaling caption size by touching only the seed value.** The shrink loop's box-height ratio silently undoes it — the render succeeds and looks identical. Scale the ratio too, then prove the new size by calling `pick_font_size` directly.
11. **Trusting a clip's title or channel about its content.** News footage and comedy share search results. Screen a frame grid of the FULL source (including the closing seconds) before writing captions, not just after burning them.
12. **Assuming the delivery step is enforced because a doc says it's mandatory.** A rule written only in prose gets skipped; if a video must always accompany the output, the send path has to check for it and complain when it's missing.
13. **Deduping delivered clips by URL or file hash.** Both miss the case that actually matters — a different clip of the same scene. Subtitles, cut points and re-encodes change the hash while a viewer sees the same video. Use frame perceptual hashes with the subtitle band cropped, and calibrate the threshold against real pairs before trusting it.
14. **Logging a delivery in a step separate from the delivery itself.** Anything sent outside the automated path skips the log, and the next run happily repeats it. Write the record inside the send function, immediately after the API confirms.
15. **Treating a well-known show as pre-screened.** Familiarity is not safety — a beloved workplace sitcom episode can contain a genuinely graphic beat mid-scene. Run the frame grid on every candidate regardless of source.
16. **Discarding a clip because part of it is unusable.** If the bad stretch is in the middle, two `-ss`/`-t` cuts plus a concat keeps the setup and the punchline. Read the transcript before choosing cut points or you'll amputate the payoff.
17. **Cutting before transcribing.** The transcript is what tells you where the punchline and any profanity sit. Transcribe the full source first, then cut; whisper `small` on a ~3-minute clip needs ~4 minutes on CPU, so allow a timeout of 480 s or more.

## Related skills

- `youtube-content` — transcript-only path (no audio download needed).
- `songsee` — audio spectrogram / feature analysis if you also want to inspect the file.
