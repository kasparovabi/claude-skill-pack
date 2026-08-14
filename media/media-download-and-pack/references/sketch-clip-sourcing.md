# Sourcing sketch clips: which shows actually pay off

Field notes from repeated "find a funny scene about <work topic> and caption it"
jobs. The search step decides most of the outcome — a badly chosen candidate
costs a download, a transcription, and a screen before you find out it's unusable.

## Why scripted sitcom beats social video

Aggregated social clips are overwhelmingly dialogue-free: reaction shots, visual
gags, silent fails. There is nothing to write parody lines over. Scripted
workplace comedy gives you a full transcript's worth of back-and-forth, shot in
an office, with characters whose roles map cleanly onto work archetypes.

## Shows that consistently deliver

| Show | Strength | Watch out for |
|---|---|---|
| The Office (US) | Meeting/training scenes, dense dialogue, corporate setting | Some episodes contain graphic gags mid-scene (see below) |
| IT Crowd | Explicitly about tech dysfunction, clean, quotable | Occasional profanity — check the transcript |
| Silicon Valley | Startup/engineering specific | Frequent strong profanity |
| Parks and Recreation | Bureaucracy, process, committee comedy | Long setups, often needs cutting |
| SNL sketches | Topical, self-contained | Quality varies wildly by sketch |

## Query patterns that land

```
"The Office <topic> scene"
"The Office safety training scene"
"The Office fire drill scene"
"The Office declares bankruptcy scene"
"IT Crowd <topic> scene"
"office sketch comedy <topic>"
"SNL sketch <topic>"
"<topic> parody sketch"
```

Batch several queries in one shell call and print duration alongside title so you
can drop the 10-minute compilations before downloading anything:

```bash
for q in "The Office fire drill scene" "The Office CPR training scene"; do
  echo "### $q"
  yt-dlp --flat-playlist \
    --print "%(title)s | %(duration)s sn | %(webpage_url)s" \
    "ytsearch6:$q" 2>/dev/null
  echo
done
```

Prefer clips in the 90–300 second range. Under 60 s rarely has enough dialogue
for a full parody arc; over 300 s means the scene is a compilation and the cut
work grows.

## The known-source trap

The Office "First Aid Fail" (S5, `youtube.com/watch?v=Vmb1tqYqyII`) reads as a
completely safe pick: famous show, office setting, training-seminar premise, three
minutes long. Mid-scene, Dwight cuts the face off the CPR dummy and puts it on
while the staff scream. On a contact sheet it is unmistakably graphic.

Nothing in the title, channel, or show reputation predicts this. Screen every
candidate's frames regardless of how familiar the source is — the familiarity is
precisely what makes the check feel skippable.

That clip was still usable: the 0–47 s setup and the 161–173 s closing exchange
("this is why we have training, we start with the dummy and we learn from our
mistakes") both fit the topic, and the graphic middle was cut out entirely. See
the two-part cut recipe in SKILL.md.

## Rotation

Dedup logs that key on the *show* rather than the URL are the right shape — a
different scene from the same series still reads as "the same video" to a viewer
who saw yesterday's. Keep a rolling window (last ~7 deliveries) and pick a
different series when the window is occupied.
