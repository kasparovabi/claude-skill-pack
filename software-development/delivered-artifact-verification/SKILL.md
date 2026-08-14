---
name: delivered-artifact-verification
description: Use when user says delivered output is wrong or duplicate.
---

# Delivered Artifact Verification

Load this whenever the user reports that a thing you produced is wrong:
"bu yanlış", "aynısını göndermişsin", "bu dünkü", "gelmemiş", "bozuk geldi",
"that's the same one", "wrong file". Also load it before claiming any
delivery succeeded, and before trusting your own verification script,
test, or check that reports success (see Rules 8-9 — self-written checks
fail open, and generated identifiers are where fabrications hide). Rule 7b
covers the related complaint "you only did part of what I asked".
**Rule 1b covers the user pointing at one specific sentence or value and
saying it's wrong** — read it literally before theorising about why.
**Rule 8b covers saving through someone else's web UI** — load it before
reporting that an edit in a web app was saved, because the app's own
success signal (button clicked, modal closed, no error) is not a receipt.
**Rule 8c covers repeated write failures** — try a different endpoint
before concluding the platform rejects automation.

The failure mode this skill prevents is specific and expensive: **the user
looks at what they received, you look at files on your disk, the two
disagree, and you spend three rounds building an evidence case against
them.** That is not diligence. It reads as arguing, and it is usually
wrong, because their vantage point is the actual output and yours is a
proxy for it.

## Rule 1 — the user's observation outranks your instrumentation

They saw the delivered artifact. You are inspecting an intermediate file
and *inferring* that it is the delivered artifact. When those conflict,
assume your inference is broken, not their eyes.

Concretely, when the user says "you sent the same thing twice":

- Do NOT open with a measurement that contradicts them.
- Do open by locating **which file actually left the machine**, then
  compare that.

## Rule 1b — don't invent a diagnosis for the flaw they pointed at

Rule 1 says their observation outranks your instrumentation. This one is
narrower and just as costly: when the user points at a specific sentence,
value, or element and says *\"this is wrong\"*, **do not construct a theory
about why.** Read the thing itself, literally, word by word.

Two consecutive misses in one session, both on prose the user flagged:

| User flagged | My invented diagnosis | Actual flaw |
|---|---|---|
| \"the system goes *around* the boundary\" (TR: *sınırın etrafını dolar*) | \"tautology, says nothing, hollow depth\" | **wrong verb.** *etrafını dolamak* = to wrap/encircle. To pass without touching is *etrafından dolanmak*. The sentence wasn't empty, it used the wrong word. |
| \"The author argues this. 'X' is an insult to programmers.\" | tense/evidentiality clash, nested quotation marks | **quotation scope.** Is the author defending the quoted phrase, or the whole claim? Two opposite readings were possible. |

Both times the user came back to correct the correction. A wrong diagnosis
is worse than none, because the fix it produces is also wrong — and it gets
written into rules. The first miss produced the rule *\"check meaning\"* when
the rule needed was *\"check what the word actually means\"*.

Procedure when a specific item is flagged:

1. Read it literally. For word choice, look the term up in an authoritative
   dictionary rather than reasoning from feel.
2. Before stating a diagnosis, ask: *is this a defect visible in the text,
   or a theory I generated?* Only report the former.
3. If you cannot locate a concrete defect, say so and ask which part they
   mean. \"I see two readings here, which one bothers you\" beats a confident
   wrong answer.
4. Check for **scope ambiguity** in any sentence mixing quotation and the
   author's own claim: a reader must be able to tell, in one pass, where
   the quoted material ends and the writer's assertion begins.



The single largest error in the reference case: comparing `/tmp/foo_today.mp4`
against `/tmp/foo_yesterday.mp4` when the thing actually sent yesterday was
a completely different file produced by hand and never named on that
pattern. Both measurements were correct and both were irrelevant.

Find the real delivered artifact first:

```bash
# whatever your outbox / sent / _gonderildi convention is
ls -lat ~/.pyto-outbox/**/_gonderildi/ 2>/dev/null | head
# and widen: EVERY candidate file touched in the window, not just the
# ones matching the naming scheme you expect
find /tmp ~/.hermes -name '*.mp4' -newermt '2 days ago' -print
```

Naming conventions lie. Hand-made artifacts, retries, and `_v2` variants
do not follow them.

## Rule 3 — match the instrument to the claim

Byte identity and perceptual identity are different questions. Using the
wrong one produces confident nonsense.

| User's claim | Wrong instrument | Right instrument |
|---|---|---|
| "same video/image" | file hash, byte diff, size | perceptual hash of sampled frames |
| "same text" | file hash | normalized text diff |
| "same data" | timestamp | content digest of parsed rows |
| "it looks broken" | any programmatic check | actually render it and LOOK |

A file hash answers *"is this the same file"*. It cannot answer *"does
this look the same"*. Re-encoding, different crop points, burned-in
subtitles, and different bitrates all change every byte while leaving the
artifact visually identical. If you report "hashes differ, so it's a
different video", you have answered a question nobody asked.

For anything visual, **render frames and actually look at them** before
concluding. Programmatic similarity is a prefilter, not a verdict.

## Rule 4 — two strikes and you stop measuring

If you have contradicted the user twice and they are still saying you are
wrong, stop generating evidence. The third round is where trust breaks.

Instead:
1. Say plainly that you cannot reproduce what they see.
2. Show them the specific artifacts you are comparing, so the mismatch in
   vantage point becomes visible.
3. Ask which one they actually received.

"I compared A and B, they differ, which one did you get?" ends the loop in
one message. A third Hamming distance table does not.

## Rule 5 — bookkeeping belongs inside the side-effecting call

The root cause in the reference case was structural, not perceptual: the
dedup ledger was written by a *separate follow-up step* documented in a
prompt. Automated runs performed that step. Hand-made deliveries skipped
it. So the ledger silently held only half the history, and the next
automated run happily re-picked something already sent.

**Any "record that we did X" step that lives outside the function that
does X will eventually be skipped.** Move it inside, right after the
success branch:

```python
with urlopen(req, timeout=60) as r:
    result = json.loads(r.read())
    if result.get("ok"):
        print("OK")
        try:
            record_delivery(file_path, caption)   # INSIDE, not a later step
        except Exception as e:
            print(f"WARN: ledger write failed: {e}", file=sys.stderr)
```

Wrap it so a ledger failure never invalidates a successful delivery, but
never make it optional or manual.

## Rule 6 — calibrate thresholds on real pairs, never by guess

If your check has a similarity threshold, measure actual known-same and
known-different pairs from your own corpus before picking a number.
Guessed thresholds sit too close to the boundary and produce false alarms
that train everyone to ignore the check.

Procedure: hash N real artifacts, compute all pairwise distances, find the
minimum distance among *known-different* pairs and the maximum among
*known-same* pairs, then place the threshold in the gap with margin on
both sides. Record the measured numbers in a comment so the next person
knows why the constant is what it is.

## Rule 7 — don't defer work that fits in the remaining time

Offering "let's continue tomorrow" at 11:00 when the fix is an hour of
work reads as avoidance, especially right after a sequence of mistakes.
Check the clock before proposing a stopping point. If the user has to ask
"why are you stopping, it's still morning", you misjudged it.

## Rule 7b — a multi-request message is a checklist, not a menu
Long voice notes and paragraph-length messages routinely carry three or
four separate asks. The failure is not forgetting them; it is diving into
the first one, burning the session on it, and never returning. The user
then asks *"why couldn't you handle the whole voice note?"* — and the
honest answer is that the request was not mishandled, it was **partially
handled without saying so.**

In the reference case a voice note carried: (a) rewrite a profile section,
(b) reframe the user's projects as opportunities, (c) design a trigger that
makes profile visitors reach out. Only (a) was attempted, and it consumed
every remaining turn because it was driven through the slowest possible
path.

Before starting work on a message with more than one ask:

1. **Enumerate the asks back, briefly.** One line each. This alone prevents
   the silent drop and lets the user reorder.
2. **Do the cheapest ask first if it is independent.** Order by cost, not
   by the order they were spoken.
3. **Prefer the path that ends the task over the path that is elegant.**
   Handing the user a finished block of text to paste is a completed
   deliverable. Driving a browser to paste it for them can be the right
   call, but if it starts consuming turns, switch — do not let the delivery
   mechanism eat the deliverable.
4. **If the session runs short, name what is left.** "Two of the three are
   done, the third is X" is a report. Silence reads as forgetting.

Also note the corrections inside such a message. In the same case the user
said they had *stopped* doing AI image/video work — a correction that
invalidated a recommendation made minutes earlier. Corrections buried
mid-message are easy to miss precisely because the message is long.

## Rule 7c — rejected output is reworked the SAME day

Rule 7 says don't defer work that fits the remaining time. Rework has a
stricter rule, stated explicitly by the user (10 Aug 2026):

> *\"If I tell you a post is wrong, don't make me wait for the next day for
> a new one — write it the same day.\"*

When a recurring job produces something and the user rejects it, the
tempting move is to fix the generator and let the next scheduled run
deliver. That reads as the rejection being filed rather than answered, and
it leaves the slot empty.

Do both, in this order:

1. **Fix the durable cause** — the inventory record, the prompt rule, the
   check — so the next automated run cannot repeat it.
2. **Produce the replacement now**, in the same session: new subject, full
   pipeline, linter, companion media, delivered.

Never answer a rejection with \"the corrected version will go out tomorrow\".
Ship the corrected version and let the scheduled run carry the improvement
forward.

## Rule 7d — deliver the FINISHED artifact, not the part you just fixed

Rule 7c covers rejected output. This one covers a subtler drift: you were
asked for a deliverable, you hit a defect in your own tooling on the way,
you fixed it — and then you delivered **the fix** instead of the thing.

Two consecutive misses in one session (14 Aug 2026), same root:

| Asked for | What I sent | Reaction |
|---|---|---|
| daily post + companion clip | the corrected subtitle **file** | *"why are you sending me the subtitle file, just prepare the new post and video and send those"* |
| daily post + companion clip | a video **demoing my own subtitle fixer** | *"what is this subtitle-fixer video, is that what I asked you for?"* |

The second one is the instructive failure. Two real bugs had just been found
and fixed in the subtitle tool. That felt like the day's story, so it became
the content. It wasn't the day's story — it was **maintenance**, and
maintenance is invisible by default.

Three separate errors are packed in there:

1. **Intermediate output shipped as deliverable.** A `.srt`, a corrected
   config, a patched script — these are steps. The user asked for the
   product of those steps.
2. **Own-tooling narrative substituted for the requested subject.** Your
   repair story is not the audience's content. Fix it quietly, then produce
   what was actually requested.
3. **Companion media drifted off-topic.** When a deliverable has an
   accompanying asset (clip, image, chart), that asset belongs to the
   *deliverable's* subject, not to whatever you were debugging.

Checks before sending:

- **Name the requested artifact in one noun phrase**, then confirm the thing
  in the outbox matches that phrase. "Daily post plus clip" does not match
  "video about the subtitle fixer".
- **Did I fix something on the way here?** If yes, that fix is a side effect.
  Report it in one line at most — do not promote it to the deliverable.
- **Would the user have to do a further step to use this?** Opening a file,
  running a script, converting a format — if yes, it is not finished. Do
  that step.

## Rule 7e — text deliverables go in the MESSAGE, not in an attachment

Rule 7d covers shipping the wrong artifact. This covers shipping the right
artifact in a form the user cannot use.

Same session (14 Aug 2026), two more misses:

| Sent | Reaction |
|---|---|
| the post as an `.rtf` attachment | *"you sent an rtf file again, and you didn't send the post text — you've gone stupid again"* |
| the video, with the text omitted entirely | *"you didn't send the post text"* |

Both times the artifact existed and was correct. The failure was the
channel. A document the user has to open, scroll, and copy out of is a
worse delivery than the same words sitting in the chat.

**Rule: if the deliverable is prose the user will read, paste, or publish,
its full text goes in the message body.** Not summarised, not "it's ready",
not "see attached". Binary companions (video, image, PDF report) go as
files; the text does not.

The self-check is one question, and it is cheap:

> **Can I see the first sentence of the deliverable in the message I am
> about to send?**

If no, the delivery is incomplete regardless of what is attached. This
catches both the attachment-instead-of-text case and the
forgot-the-text-entirely case, which is why it is phrased as a positive
assertion rather than "did I remember".

Watch for the specific drift: after a long stretch of tool work — writing
files, running converters, verifying output — the finishing move feels like
*"put the file in the outbox"*, because that is what every preceding step
was. It isn't. The last step is composing the answer.

### 7e-i — text the user will PASTE goes in a fenced code block

"In the message body" is necessary but not sufficient. Prose the user will
copy into another system (a post, a commit message, an email, a config)
must be delivered in a **fenced code block**, because chat clients render
one with a copy button. Bold, italics and inline links in flowing text
force a manual drag-select, and any markdown emphasis characters get copied
along with the words.

In the reference session the same post was sent three times — as `.rtf`,
then as a rich-text PDF, then as body prose with `**bold**` runs — before
the user sent a screenshot of what they had meant all along: a plain code
block. Each attempt was *more* formatted than the last, which was exactly
backwards.

| Deliverable | Form |
|---|---|
| text to be pasted elsewhere | fenced code block, no emphasis markup |
| text to be read in place | normal message prose |
| binary companion (video, image) | file attachment |

If the user's own tooling shows the target rendering, ask for or look at
that screenshot before guessing a third time.

### 7e-ii — repeating a mistake you "know better" than means the SKILL contradicts itself

The expensive signal is not one wrong delivery, it is the same wrong
delivery after you have already been corrected. That pattern almost never
means the rule was forgotten. It usually means **the governing skill states
both the rule and its opposite**, and the stale line is the one that fires
under load.

Confirmed in the reference session: the LinkedIn pipeline skill contained
an explicit *"delivery is a code block in the chat topic, PDF is no longer
used"* section — and, further down in an older format-rules block, the line
*"the post is delivered **as a PDF**, not as a plain message"*, twice. The
newer decision never removed the older bullet. Three failed deliveries came
straight out of that contradiction.

When you catch yourself re-offending:

1. **Grep the governing skill for the opposite instruction**, not for the
   rule you broke. Search the artifact nouns — `PDF`, `attachment`, `file`,
   `dosya` — and read every hit.
2. **Delete or rewrite the stale line.** Adding a third, louder copy of the
   correct rule leaves the contradiction intact.
3. **Prefer one statement of a delivery rule.** If a skill needs the rule
   in two places, the second should point at the first, not restate it.

If the governing skill is user-owned and cannot be patched, say so
explicitly and name the contradicting lines so the user can fix them —
carrying the correction only in this session guarantees the next one
repeats it.

## Rule 8 — a check that has never failed is not a check

Rules 1-7 cover *"the user says my output is wrong"*. This one covers the
inverse and equally expensive case: **your own verification says the output
is fine when it is not.**

Self-written checks fail OPEN by default. They report success when they
did not actually measure anything, and that success gets forwarded as
sign-off. In one audit, three of fifteen checks reported PASS on
infrastructure that was completely untouched:

- A probe requested an invented hostname that had no DNS record, so the
  request never reached the server. The empty response was read as
  "correctly empty".
- A probe tested the *working* variant of a resource when the finding was
  about the *broken* variant, because the working one was tidier to type.
- A probe checked only a command's exit code, asserting nothing about
  whether the returned artifact was the right one.

Before trusting any green result:

1. **Point the check at something known-broken and confirm it goes red.**
   If you cannot make it fail on demand, it is decoration.
2. **Guard on reachability first.** Distinguish *measured and found clean*
   from *could not measure*. Absent, empty, zero, and unreachable must
   report as skipped, never as passing.
3. **Assert on the exact entity in the claim.** Verifying a neighbouring,
   similar, or canonical variant proves nothing about the one that broke.
4. **Check the content, not just the exit status.** Exit 0 means the
   command ran, not that it produced the right thing.

A baseline run before any fix is expected to fail everything. Label it as
the baseline — reporting all-fail as a finding, or the first all-pass as an
achievement without step 1, both mislead.

## Rule 8b — a third-party UI's success signal is not a write receipt

Rule 8 covers checks *you* wrote failing open. The same failure arrives from
the other direction: a web app's own UI reports success and the write never
landed. Observed repeatedly in one session against a single SPA form —
the button click registered, the modal closed, **no error appeared**, the
character counter showed the new value, and the DOM held the new text. The
record was unchanged on reload, every time.

The signals that felt like confirmation and were worth nothing:

| Signal | Why it proves nothing |
|---|---|
| Click returned \"clicked\" / `AXPress` succeeded | you hit the element; the handler may reject silently |
| Modal closed | closing is a UI transition, not a server ack |
| No error toast | silent rejection is the common case, not the rare one |
| Counter/DOM shows new value | client-side state, not persisted state |
| A read-back right after saving | may serve cached or in-memory state |

**The only acceptable proof is a fresh read after a full reload**, ideally
cache-busted, asserting on a string unique to the new content:

```bash
# reload, wait, then assert the NEW text is present — not that the old is absent
<reload with ?nocache=$RANDOM>; sleep 8
<read page text> | grep -q \"Event Video Production\" && echo SAVED || echo NOT_SAVED
```

Two habits follow. First, when a save is uncertain, **assert on the new
string**, never on the absence of the old one — a partially applied edit
satisfies the second test and fails the first. Second, count attempts: if
three distinct input methods each report success and the reload still shows
old data, stop varying the input method. **But do not conclude the platform
is unwritable — that conclusion was drawn in the reference session and it
was wrong.** See Rule 8c.

This is also the strongest available material for content about AI tooling:
the gap between *\"the tool said it worked\"* and *\"I went and looked\"* is a
real, demonstrable class of failure.

## Rule 8c — when writes are rejected, change the ENDPOINT, not the keystroke

Rule 8b's original advice was to give up after three input methods and hand
the content to the user. A later session proved that premature. **Eight**
input methods failed against one form (native value setter, clipboard +
real keyboard, `AXPress`, pixel click, dirty-the-field-then-save, JS
`.click()`, foreground escalation, accessibility index). The user pasted it
manually — and it worked, which seemed to confirm the platform was fine and
only automation was blocked. It wasn't. The **edit** endpoint was rejecting
writes; the **add** endpoint accepted them on the first try.

Varying how you press the key answers the same question eight times. Ask a
different question instead:

**The decisive probe: create a throwaway record.**

```
1. Add a new record with an obvious sentinel name (ZZTEST ...).
2. Reload the list.
   - Sentinel VISIBLE  -> the read path is fresh; your EDIT write is being
                          rejected server-side. Switch to delete + re-add.
   - Sentinel MISSING  -> the problem is on the read side (cache, locale
                          variant, permissions). Stop trying to write.
3. Delete the sentinel immediately.
```

Three calls, and it splits the two hypotheses that eight write attempts
could not. Run it **before** trying a fourth input method, not after the
eighth.

When the edit path is the blocked one, the delete-and-recreate loop is the
fix. Before running it:

- **Back up everything first** — deletion is irreversible. Save current
  titles, bodies, and any structured fields (dates, dropdown selections) to
  disk. Re-adding a record without its dates silently loses them.
- **Halt the loop on any unexpected step result**, so a record is never
  left deleted-but-not-recreated.
- **Verify the delete confirmation dialog visually** each time — it names
  the record being destroyed.
- **Run the full cycle on ONE record and verify from a reloaded list**
  before batching the rest.

Full recipe, harness script and the `<select>`-field handling live in
`authenticated-browser-automation` →
`references/yaz-oku-ucurumu-ve-sil-ekle.md`.

Generalised: *before declaring a write impossible, check whether a
**different write path to the same data** succeeds.* Repeated failure of
one mechanism is evidence about that mechanism, not about the system.

## Rule 9 — fetch every identifier you emit

Generated artifacts (config, structured data, docs, citations) are where
plausible fabrications hide, because the shape is right and nothing
crashes. Two invented values once shipped into a generated metadata block:
a well-formed entity ID for the wrong entity, and a conventional-looking
asset path that returned 404. Both looked correct in review.

A third bad URL in the same file was copied *from the client's own site* —
so lifting from the source is not protection either.

Make it mechanical, not a judgement call: after writing any artifact,
extract every URL and fetch it; resolve every non-URL identifier through
its authoritative API rather than from recall.

```python
urls = sorted(set(re.findall(r"https?://[^\s)>\"']+", open(artifact).read())))
# fetch concurrently, print anything that is not 200
```

Then re-parse the file after every edit — a late find-and-replace is a
common way to break JSON or YAML that validated earlier.

## Rule 9b — attribution and lived detail are facts, not colour

Rule 9 covers invented *identifiers*. The same fabrication reflex operates
one level up, on prose, and is harder to see because nothing is malformed:
**who a piece of work was built for, and what people experienced while using
it, are verifiable claims.** They cannot be inferred from context to make a
narrative flow.

Observed (10 Aug 2026): a post was drafted about a rendering engine the user
had built. Two fabrications went in, neither flagged by any check:

| Written | Reality |
|---|---|
| \"events keep coming in from the foundation's schools\" | the product was the user's **own**, not client work at all |
| \"the editors were suffering decision fatigue\" | **no such scene ever happened** |

The user caught both: *\"we never built such an automation — I built it for
myself, not for the foundation.\"* The draft was going out under their name
with an unverifiable claim about an organisation attached. One question from
a reader — *which team, which editors?* — and it collapses.

Why it happens: a concrete-sounding origin story and a human moment of pain
both make prose better, so the drafting reflex supplies them. The check for
\"is this well written\" passes. There is no check for \"did this occur\".

**Before writing about any piece of work:**

1. **Read the attribution field, do not recall it.** Keep an inventory with
   an explicit ownership marker per item and consult it every time:

   | Value | Meaning |
   |---|---|
   | `CLIENT` | real client work — but see the naming rules for that client |
   | `PERSONAL` | the user's own product. Never write \"I built this for X\" |
   | `UNVERIFIED` | **ask before publishing any affiliation claim** |

   Reference implementation: `~/.hermes/state/otomasyon_envanteri.json`,
   printed into automated runs by `otomasyon_envanteri_bas.py`.

2. **Never invent a scene.** \"The team complained\", \"everyone was talking
   about it\", \"the editors were exhausted\" — if it did not happen, it does
   not go in. Describe the concrete situation; do not stage an emotion.

3. **Separate the two failure directions.** Claiming personal work was done
   for a client inflates credentials. Claiming client work was personal
   erases a real credential. Both are wrong; the first is the dangerous one.

The generalisation: *any sentence a reader could challenge with \"says who?\"
is a factual claim.* Prose fluency is not evidence, and a fabricated origin
story is the same defect as a fabricated URL — it just fails at a meeting
instead of at a fetch.

## Working reference implementation

`references/perceptual-dedup-ledger.md` — the full case study behind these
rules, plus a working `kaydet` / `kontrol` ledger script for video, the
measured calibration table, and the frame-crop trick for artifacts that
carry burned-in overlays.

## Pitfalls

- **Sampling at fixed timestamps across differently-cut clips** makes
  identical scenes look different. Sample at proportional positions
  (15%, 30%, 50%, 70%, 85%) instead of absolute seconds.
- **Burned-in captions dominate a perceptual hash.** Crop the caption band
  (e.g. bottom 28%) before hashing, or the same scene with new subtitles
  reads as new.
- **A ledger that stores only a source URL is not a dedup ledger.** A
  different clip from the same source, or the same clip re-fetched from a
  mirror, both defeat it. Store a content fingerprint.
- **Backfill the ledger when you introduce it.** An empty ledger green-lights
  everything already sent. Load history first, then trust it.
