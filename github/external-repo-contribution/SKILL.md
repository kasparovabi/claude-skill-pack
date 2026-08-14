---
name: external-repo-contribution
description: "Use when contributing to a stranger's repo cold."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, open-source, contribution, pull-request, networking]
    category: github
---

# Contributing to someone else's repo, cold

Someone shares a project (LinkedIn post, HN thread, a scanner hit) and the
question is **should we engage, and if so how**. This skill owns the decision
and the cold drive-by PR that follows it.

## When to Use

- Someone shares a repo and asks "katkı sağlasak mı", "should we contribute?"
- A post describes a project whose author is stuck on something
- A scanner or search surfaces a small repo with a fixable defect
- You are about to recommend *against* engaging with a project

Don't use for: security findings (`coordinated-vulnerability-disclosure`),
responding to bot review on a PR you already opened
(`upstream-pr-review-response`), or work inside your own repos.

## The decision: do NOT optimise for CV visibility alone

The correction that produced this skill. I recommended against contributing to a
3-star repo because it "won't be visible on a CV", and was told plainly:

> *"Burada mesele sadece cv değil ya. Eforu direkt ben harcamadığım ve işi sen
> arkaplanda yaptığın için boşa vakit harcamış olmayız. Ve bir repoda adam akıllı
> görünmüş oluruz ki kişinin linkedin profiline bakmadım ama entrepreneur diyor
> belki sever ve iş bağlarız belli mi olur. Sadece issue değil direkt pr yapalım
> biz katkı sunalım."*

Three things were wrong in my framing, and all three generalise:

**1. The effort budget is mine, not his.** The cost model I applied — "this will
consume time better spent elsewhere" — is the model for work *he* performs. When
the agent does the diagnosis and the patch in the background, the marginal cost
to him is reading one message. A recommendation that spends his attention and my
compute is not the same trade as one that spends his afternoon. Do not import a
human cost model into agent-performed work.

**2. Star count is not the payoff.** The payoff can be the relationship. A small
repo has an author who will actually read the PR, and who may be a founder, a
hiring manager, or simply someone worth knowing. A 3-star repo with an engaged
maintainer is a better introduction than a drive-by on a 40k-star project where
the PR joins a queue of 300.

**3. Issue is the weaker move when you can already fix it.** I offered to write
up the diagnosis as an issue. If the diagnosis is solid enough to write down, it
is usually solid enough to patch. **Default to the PR.** An issue says "here is
your problem"; a PR says "here is your problem and I already did the work".

### When declining IS right

Not everything deserves a PR. Genuine reasons to pass, none of which is star
count:

- No license, or a licence that makes contribution legally murky
- Archived, or last push many months ago with open PRs rotting
- The fix requires a design decision only the maintainer can make
- You cannot reproduce or diagnose the problem, so the PR would be a guess
- The "bug" is the platform refusing to do something it never supported, and no
  patch changes that

State the reason in one line. "Not worth it" without a reason is the failure
this skill exists to prevent.

### "Is this repo abandoned?" is a three-signal measurement, not a vibe

Asked after a batch of cold PRs sat unanswered: *"Açık PR'larda repolar artık
terk edilmiş olabilir mi?"* A single number cannot answer it, and the wrong
single number misleads in both directions. A repo can commit daily and still
never merge an outsider's work; a repo can look quiet and merge yours in a week.

Measure three things per PR:

```bash
gh api /repos/<owner>/<repo> --jq '.pushed_at'                    # still worked on?
gh api /repos/<owner>/<repo>/pulls/<n> --jq '.created_at'         # how old is OUR pr?
gh api "/repos/<owner>/<repo>/pulls?state=closed&per_page=30&sort=updated&direction=desc" \
  --jq '[.[] | select(.merged_at != null)] | length'              # merges OUTSIDE work?
```

Reading the combinations:

| pushed | merged PRs (90d) | verdict |
|---|---|---|
| > 180 days | any | abandoned, stop waiting |
| recent | 0 | alive but does not merge outsiders — your PR may never land |
| recent | > 0 | healthy; if our PR is young, waiting is correct |
| stale | > 0 | slow maintainer, still worth the wait |

Measured across nine open PRs: seven were healthy (29, 20, 20, 16 and 8 merges
in 90 days, four pushed the same day), and every PR was 0–11 days old. The
honest answer was **"not abandoned, our PRs are simply young"** — the opposite of
the assumption in the question.

The two quiet ones each failed for a different reason worth naming separately:
one had no push in 62 days and zero merged PRs; the other was at **PR number 1**,
i.e. the project's first-ever pull request, which usually means a solo author
with no habit of taking outside contributions. That is a prediction about the
wait, not a defect in the patch.

> **Do not answer a liveness question from the PR page alone.** A silent PR
> looks identical whether the repo is dead, the maintainer is slow, or the patch
> landed yesterday. Distinguish them before telling the user to give up.

When a repo does turn out to be genuinely dead, the useful next step is not a
ping but redirecting the effort. Say so plainly and point at where attention is
better spent — in that session, the one PR actually worth attention was the one
where the maintainer had already asked for changes five times and the blocker
was the repo's own broken CI check, not our code.

## Finding the repo when you only have a shortlink

LinkedIn wraps every URL in `lnkd.in`, and it does **not** resolve from the
command line — `curl -L` returns the shortlink itself, because the redirect is
served to browsers only. Name-guessing the repo also fails: the poster's display
name rarely matches their GitHub handle (here `Yusuf Demirci` → `meyusufdemirci`,
while the plausible `yusufdemirci` was a different, empty account).

Open it in a real browser and read the settled URL:

```bash
osascript -e 'tell application "Google Chrome"
  set URL of tab N of (first window whose id is <WID>) to "https://lnkd.in/XXXX"
end tell'
sleep 9
osascript -e 'tell application "Google Chrome" to return URL of tab N of (first window whose id is <WID>)'
```

Do not report "I could not find the repo" until the browser has been tried. And
never open a PR against a repo you guessed at.

## Read the code before forming an opinion about the author

I described this project as "half-finished" from the LinkedIn post alone. The
clone said otherwise: 71 Swift files, 6,005 lines, dependency injection, 134
unit tests, and commit messages written in full sentences. Adjusting that
judgement out loud mattered as much as the patch.

```bash
gh api /repos/<owner>/<repo> --jq '{stars:.stargazers_count, lang:.language,
  license:(.license.spdx_id // "NONE"), pushed:.pushed_at, issues:.open_issues_count}'
git clone --depth 20 <url> && cd <repo>
find . -name "*.<ext>" -not -path "./.git/*" | wc -l
find . -name "*.<ext>" -not -path "./.git/*" -exec wc -l {} + | tail -1
```

A repo with tests and injected seams tells you something useful: the bug is
probably **not** in the logic the tests cover. That narrows the search
immediately — see below.

## Passing tests + broken feature = the bug is outside the tested layer

The strongest diagnostic signal in this class of work. When the suite is green
and the feature still misbehaves intermittently, stop reading the logic. The
tests are exercising pure functions and injected seams; the failure lives in
what the seams deliberately abstract away — real I/O, event ordering, timing,
permissions, OS state.

Worked case: a menu-bar utility whose hide function "sometimes" worked. The
geometry was unit-tested and correct. The defect was in the synthesized input
sequence the tests mock out.

### Synthesized input events need settle time at every boundary

A reusable bug shape for anything driving a GUI by posting fake events
(`CGEvent`, `SendInput`, `XTest`, browser `dispatchEvent` chains).

Code that pauses *between* drag samples but posts the **boundaries** of the
gesture back-to-back will work on an idle machine and fail under load. Each
boundary is a point where the receiving app has work to do first:

```swift
postKey(commandKeyCode, down: true, source: eventSource)
usleep(modifierSettleDelay)     // let the bar enter rearrange mode
postMouse(.leftMouseDown, at: source, source: eventSource)
usleep(grabSettleDelay)         // let the item be picked up
for point in path { postMouse(.leftMouseDragged, at: point, ...); usleep(stepDelay) }
usleep(dropSettleDelay)         // do not let the last sample and the release merge
postMouse(.leftMouseUp, at: destination, source: eventSource)
usleep(releaseSettleDelay)      // drop must land before rearrange mode ends
postKey(commandKeyCode, down: false, source: eventSource)
```

Name each delay separately rather than reusing one constant, so the maintainer
can tune the one that still misses without touching the others. Say which one to
raise first in the PR body.

Diagnostic phrasing that identifies this class: **"intermittent" plus "passes on
an idle machine" plus "unit tests green" means ordering, not logic.**

## Verify by building and testing, then say the number

Never open a PR on someone else's project claiming a fix you did not compile.

```bash
xcodebuild -project X.xcodeproj -scheme X -destination 'platform=macOS' build
xcodebuild -project X.xcodeproj -scheme X -destination 'platform=macOS' test 2>&1 \
  | grep -cE "' passed on"
xcodebuild ... test 2>&1 | grep -cE "' failed|TEST FAILED"
```

Put the counts in the PR body ("134 tests, 0 failures"). A maintainer triaging a
stranger's PR is deciding whether you are worth the review time, and a real
number does that work.

## The PR body: state what you could NOT verify

The highest-trust move available to an outside contributor. On a patch to timing
that only manifests against a real desktop, I could not confirm on-device that
the feature now lands every time, and said so:

> I could not validate on-device that the hide now lands every time, since that
> depends on the real menu bar and Accessibility permissions on your machine. If
> it still misses under load, `dropSettleDelay` is the one to raise first.

That paragraph costs nothing and buys the maintainer a next step. Structure that
works for a cold PR:

- the mechanism, in mechanical terms, no adjectives
- a bulleted list of the specific boundaries/cases that were wrong
- **why the existing tests pass anyway** — pre-empts the first review question
- what you measured (build state, test counts)
- what you could not measure, and the one knob to turn if it is still wrong

Write it in the target repo's language. This project's code and commits were
English, so the PR was English even though the working conversation was Turkish.

## Mechanics

Fork, branch, push to the fork, PR across:

```bash
gh repo fork <owner>/<repo> --clone=false
git clone https://github.com/<you>/<repo>.git && cd <repo>
git checkout -b fix/<class-level-name>
# ... patch, build, test ...
git push -u origin fix/<class-level-name>
gh pr create --repo <owner>/<repo> --base main \
  --head <you>:fix/<class-level-name> \
  --title "..." --body-file /tmp/pr_body.md
```

Load `github-pr-workflow` for the wider PR lifecycle; this skill only covers the
cold-contribution specifics.

## Strip your own comments, leave theirs alone

Standing user directive for all code this agent writes: no `//` or `#`
narration, no `/* ... */` prose blocks. Naming carries the meaning.

> *"bundan sonra yazdığın hiçbir kodda // açıklama satırlarını yazmanı
> istemiyorum, hiçbir gerçek yazılımcı bu kadar uzun açıklama yazmaz"*

On a fork this needs care, because the rule applies to **your additions only**.
A blanket stripper over the file also deletes the maintainer's own commentary,
which reads as vandalism and gets the PR closed. Isolate your lines against the
base commit:

```bash
git diff HEAD~1 -- <file> | grep "^+" | grep -c "//"
git diff HEAD~1 -- <file> | grep "^+" | grep -v "^+++"
```

Remove those specific lines by exact-string replacement, never by running a
regex over the whole file. Measured here: a 26-line patch carried 16 lines of my
own commentary. Stripping just those took the diff to 10 lines — four constants
and four calls — and left every pre-existing comment untouched.

Rebuild and re-run the suite afterwards; deleting a line that closed a block is
the one way this bites. Then `git commit --amend` and force-push the branch so
the PR shows the clean diff rather than a follow-up "remove comments" commit.

A smaller diff is also a better cold PR. Ten lines of pure mechanism is a
five-minute review; twenty-six lines half-full of a stranger explaining the
codebase back to its author is not.

## Pitfalls

- **Applying a human effort budget to agent-performed work.** The single
  correction that created this skill. See the decision section.
- **Judging the project from the post instead of the clone.** The post said
  "stuck"; the code said 134 passing tests and a clean architecture.
- **Guessing the GitHub handle from a display name.** Resolve the real URL.
- **Recommending an issue when you already have the patch.** PR by default.
- **Claiming a fix you did not build.** Build and test before opening.
- **Hiding the limits of your verification.** Say what you could not confirm;
  it reads as competence, not weakness.
- **Reading the tested logic when the tests are green.** The bug is in the layer
  the seams abstract away.
- **Leaving your own comments in the patch.** Strip them, keep theirs, amend.
- **Calling a repo abandoned from the PR page.** Measure push date, our PR's
  age, and merged-PR count in the last 90 days before concluding anything.
