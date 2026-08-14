---
name: upstream-patch-stack-maintenance
description: Use when local patches stop applying to upstream.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [git, patch, upstream, fork, maintenance, devops, hermes]
    related_skills: [systematic-debugging, dogrulama-disiplini]
---

# Maintaining a patch stack against a moving upstream

## Trigger

Load this when any of these appear:

- an auto-update run reports `patch apply failed` / `patch does not apply`
- a nightly updater keeps reverting and pinning HEAD at an old commit
- a fork is "N commits behind upstream" and not catching up
- local customizations must be rebased after upstream refactors the code they touch

A fork carries N local patches (`~/.hermes/patches/0001-*.patch` …). A nightly
job fetches upstream, replays the stack, and on any failure reverts and pins
HEAD at the last good commit. Weeks later the stack silently rots: upstream
refactors the function a patch anchors to, the patch stops applying, and the
fork stops receiving updates entirely.

Symptom shape:

```
Hermes auto-update FAILED 2 nights in a row.
Reason: patch apply failed: 0007-anthropic-auth-token-resolver.patch
Failed patches: 0007-...   Conflicts: none
HEAD pinned at a6defd4f1; 400 commits behind upstream tonight.
```

## "Conflicts: none" is not reassuring — it is the actual diagnosis

This line reads like "nothing conflicted, so something else went wrong." It
means the opposite of what people assume.

- **A conflict** = two edits to the same region. Git can show you both sides.
- **`patch does not apply` with zero conflicts** = the patch's *context lines
  no longer exist in the file at all*. There is no "other side" to show.

An empty conflict list points straight at **upstream deleted or rewrote the code
the patch anchors to**. Do not go looking for a merge problem; go read the
upstream version of the function.

## Step 1 — is the patch still needed?

Before rebasing anything, check whether upstream absorbed the feature. If they
did, the patch should be **retired**, not repaired.

```bash
cd <repo> && git fetch origin --quiet
git rev-parse --short HEAD; git rev-parse --short origin/main
git rev-list --count HEAD..origin/main            # how far behind

# does upstream already implement the thing the patch adds?
git show origin/main:path/to/file.py | grep -n "MY_FEATURE_SYMBOL"
```

Empty result → patch still needed, continue. Non-empty → retire it (this repo's
convention is renaming to `NNNN-name.patch.retired`, which is why a
`0006-*.patch.retired` sits alongside the live ones).

## Step 2 — read the upstream function, not just the line numbers

Line drift alone (`file grew by 115 lines`) is a red herring; `git apply` finds
context by content, not position. Print the upstream version of the region and
compare it to what the patch expects.

Real case: the patch appended a branch inside `resolve_anthropic_token()` using
a `creds` local that was read eagerly at the top of the function. Upstream
rewrote it to a lazy closure:

```python
# BEFORE (what the patch was written against)
creds = read_claude_code_credentials()
...
preferred = _prefer_refreshable_claude_code_token(cc_token, creds)

# AFTER (upstream now)
creds: Optional[Dict[str, Any]] = None
creds_loaded = False
def _read_creds() -> Optional[Dict[str, Any]]:
    nonlocal creds, creds_loaded
    ...
preferred = _prefer_refreshable_claude_code_token(cc_token, _read_creds())
```

Every context line the patch quoted was gone. The fix is not a line-number
bump — the patch body itself must adopt the new call convention
(`creds` → `_read_creds()`).

**Generalized:** when a patch stops applying, the question is "what shape does
this code have now?" — then port the patch to that shape. A patch is a *diff
against an API*, and the API moved.

## Step 3 — regenerate the hunk programmatically

Hand-writing `@@` headers is where this goes wrong. Two failure modes:

- `@@` with no line numbers → `error: patch with only garbage at line 4`.
- Guessed line numbers / wrong context counts → applies to the wrong place or
  fails opaquely.

Extract the upstream file, locate the anchor line by exact content, and emit
the hunk with computed counts:

```python
up = open("/tmp/up_file.py", encoding="utf-8").read().splitlines()
anchor = "    # 3. Regular API key. An explicit user-configured key must not be shadowed"
idx = next(i for i, l in enumerate(up) if l == anchor)     # 0-based

bas = idx - 7                        # 1-based start of context (tune)
ctx_once  = up[bas-1:idx]            # context BEFORE the insertion
ctx_sonra = up[idx:idx+4]            # context AFTER
eklenen   = [...]                    # the lines being added

eski_n = len(ctx_once) + len(ctx_sonra)
yeni_n = eski_n + len(eklenen)
out  = ["diff --git a/path b/path", "--- a/path", "+++ b/path",
        f"@@ -{bas},{eski_n} +{bas},{yeni_n} @@ def enclosing_function():"]
out += [" " + l for l in ctx_once]
out += ["+" + l for l in eklenen]
out += [" " + l for l in ctx_sonra]
open("new.patch", "w", encoding="utf-8").write("\n".join(out) + "\n")
```

Keep 5–8 context lines. Too few and the hunk matches the wrong site; too many
and it re-breaks on the next unrelated upstream edit.

## Step 4 — verify against the REAL upstream tree (the trap that costs rounds)

**`git clone <local-repo>` checks out that repo's current branch, not its
`origin/main`.** If the local fork is pinned 400 commits behind, your "upstream"
test tree is the *old* code, and a correctly-rebased patch reports FAILED. This
produced a false "still broken" verdict twice in one session and nearly sent a
good patch back for rework.

Depth flags make it worse (`--depth is ignored in local clones`), and
`git fetch origin <sha>` fails on a local remote (`couldn't find remote ref`).

The invocation that actually lands on upstream:

```bash
rm -rf /tmp/patchtest && mkdir /tmp/patchtest && cd /tmp/patchtest
git init -q
git remote add origin <path-to-local-fork>
git fetch -q origin 'refs/remotes/origin/main:refs/heads/upstream'
git checkout -q upstream
git rev-parse --short HEAD          # MUST equal the real origin/main sha
```

**Always print the checked-out SHA and compare it to the expected upstream SHA
before trusting any pass/fail result.** A verification harness pointed at the
wrong tree is worse than no harness — it produces confident wrong answers.

Then dry-run the whole stack, not just the repaired patch:

```bash
for p in ~/.hermes/patches/0*.patch; do
  printf "%-58s " "$(basename $p)"
  git apply --check "$p" 2>/dev/null && echo OK || echo FAILED
done
```

## Step 5 — apply-all, then check syntax AND semantics

`git apply --check` passing means the text lands. It says nothing about whether
the result is correct code.

```bash
for p in ~/.hermes/patches/0*.patch; do git apply "$p" || echo "APPLY FAIL: $p"; done
python3 -c "import ast;ast.parse(open('path/to/file.py',encoding='utf-8').read());print('SYNTAX OK')"
git diff --stat
```

Then assert the *behavioral* invariants the patch exists for. For an ordered
resolver chain that means priority order and absence of the stale symbol:

```python
blok = src[src.find('def resolve_anthropic_token()'):][:2600]
assert blok.find('# 2. ') < blok.find('# 2b. ') < blok.find('# 3. ')   # ordering
assert '_read_creds())' in blok            # adopted new convention
assert '(auth_token, creds)' not in blok   # no stale eager variable
```

Back up the old patch before overwriting (`cp 0007-*.patch /tmp/0007-old.patch`)
so a bad rebase is one copy away from reverting.

## Reporting back

Lead with the root cause in one sentence ("a local patch anchored to a function
upstream rewrote"), then what changed, then the verification evidence. Do not
narrate the failed attempts as if they were progress. If a wasted round came
from your own harness pointing at the wrong tree, say so plainly and briefly —
it is the part that stops the next session repeating it.

Offer the next action rather than performing it unasked: run the update now, or
let the nightly job pick it up.

## Pitfalls

- **Don't retry the nightly job hoping it passes.** A content-mismatch failure
  is deterministic; it fails identically every night until the patch is ported.
  Two consecutive failure notifications mean the same failure twice, not flakiness.
- **Don't diagnose from line numbers.** A file growing 3062 → 3177 lines looks
  like the cause and isn't. `git apply` matches on content.
- **Don't hand-edit `@@` headers.** Compute them.
- **A pinned HEAD is silent debt.** The updater reverting cleanly means nothing
  is visibly broken today while the fork falls hundreds of commits behind.
  Treat "N nights in a row" as the real severity signal.
- **Verify the harness before verifying the fix.** Print SHAs. See Step 4.
- **Never hand-fix the working tree instead of the patch file.** Editing the
  checked-out source makes tonight's run pass and tomorrow's revert it. The
  durable artifact is the `.patch`.

## Reference

`references/hermes-patch-drift-2026-08.md` — the full worked case: the exact
upstream refactor (eager `creds` → lazy `_read_creds()` closure), the failing
and repaired patch bodies side by side, the local-clone false-negative
transcript, and the semantic assertions used to confirm the rebase.
