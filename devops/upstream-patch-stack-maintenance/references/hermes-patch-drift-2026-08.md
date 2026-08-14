# Hermes patch drift — worked case, 5 August 2026

Concrete transcript behind `SKILL.md`. Load when the abstract steps need a
real example, or when this specific patch drifts again.

## The alert

```json
{
  "ts": "2026-08-05T04:01:25+03:00",
  "result": "reverted",
  "reason": "patch apply failed: 0007-anthropic-auth-token-resolver.patch",
  "base_sha": "a6defd4f1549da3fe1d08d6f746fc645c64543f0",
  "new_sha": "aec331899",
  "commits_behind_before": 400,
  "consecutive_failures": 2,
  "patches_failed": ["0007-anthropic-auth-token-resolver.patch"],
  "conflicted_files": [],
  "gateway_healthy": true
}
```

Status file: `~/.hermes/logs/update-status.json`.
Patch dir: `~/.hermes/patches/`.
Repo: `~/.hermes/hermes-agent` (NOT `~/.hermes/hermes` — that path does not
exist; a wrong guess wastes a call).

`conflicted_files: []` was the diagnosis, not an absence of one. See SKILL.md.

## What the patch does

Adds a `2b` branch to `resolve_anthropic_token()` in
`agent/anthropic_adapter.py`, so a user-owned `ANTHROPIC_AUTH_TOKEN` is honored
between `CLAUDE_CODE_OAUTH_TOKEN` (2) and the plain API key (3). Rationale in
the patch comment: `hermes update` rewrites/blanks the hermes-managed
`ANTHROPIC_TOKEN`, while this user-owned var survives `.env` rewrites, so it is
the durable home for a dedicated subscription setup-token when the Claude Code
keychain is intentionally off via `HERMES_ISOLATE_SETUP_TOKEN`.

## Step 1 — still needed? YES

```bash
git show origin/main:agent/anthropic_adapter.py | grep -n "ANTHROPIC_AUTH_TOKEN"
# → empty. Upstream never absorbed it.
```

Also worth noting the sibling `0006-reasoning-effort-max.patch.retired` — that
one WAS absorbed and got the `.retired` suffix. That is the retirement
convention in this repo.

## Step 2 — the upstream refactor

File grew 3062 → 3177 lines. Irrelevant. The real change:

```python
# OLD shape (what patch 0007 was written against)
    creds = read_claude_code_credentials()       # eager, once, top of function
    ...
    preferred = _prefer_refreshable_claude_code_token(cc_token, creds)
    ...
    # 3. Claude Code credential file
    resolved_claude_token = _resolve_claude_code_token_from_credentials(creds)

# NEW shape (origin/main aec331899)
def resolve_anthropic_token() -> Optional[str]:
    creds: Optional[Dict[str, Any]] = None
    creds_loaded = False

    def _read_creds() -> Optional[Dict[str, Any]]:
        nonlocal creds, creds_loaded
        if not creds_loaded:
            creds = read_claude_code_credentials()
            creds_loaded = True
        return creds

    # 1. ANTHROPIC_TOKEN
    # 2. CLAUDE_CODE_OAUTH_TOKEN   → _prefer_refreshable_claude_code_token(cc_token, _read_creds())
    # 3. Regular API key           ← insertion point is just BEFORE this
    # 4. Claude Code credential file
    # 5. Hermes credential_pool
```

Two independent breakages in one refactor:

1. **Numbering shifted.** Old comment `# 3. Claude Code credential file` became
   `# 4.`; the new `# 3.` is the API key. The patch's trailing context quoted
   the old `# 3.` text, which no longer follows the insertion point.
2. **Call convention changed.** `creds` is no longer a plain local in scope at
   that position — the added lines had to become `_read_creds()`.

A pure line-number rebase would have produced code referencing an
uninitialized-at-that-point `creds`. This is why Step 2 says read the function.

## Step 3 — the repaired patch

```
diff --git a/agent/anthropic_adapter.py b/agent/anthropic_adapter.py
--- a/agent/anthropic_adapter.py
+++ b/agent/anthropic_adapter.py
@@ -1388,12 +1388,24 @@ def resolve_anthropic_token() -> Optional[str]:
     # 2. CLAUDE_CODE_OAUTH_TOKEN (used by Claude Code for setup-tokens)
     cc_token = _getenv("CLAUDE_CODE_OAUTH_TOKEN").strip()
     if cc_token:
         preferred = _prefer_refreshable_claude_code_token(cc_token, _read_creds())
         if preferred:
             return preferred
         return cc_token
 
+    # 2b. ANTHROPIC_AUTH_TOKEN (Claude Code / SDK bearer slot). Unlike the
+    # hermes-managed ANTHROPIC_TOKEN (which `hermes update` rewrites and can
+    # blank), this user-owned var survives .env rewrites, so it is the durable
+    # home for a dedicated subscription setup-token when the Claude Code
+    # keychain is intentionally off via HERMES_ISOLATE_SETUP_TOKEN. (patch 0007)
+    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "").strip()
+    if auth_token:
+        preferred = _prefer_refreshable_claude_code_token(auth_token, _read_creds())
+        if preferred:
+            return preferred
+        return auth_token
+
     # 3. Regular API key. An explicit user-configured key must not be shadowed
     # by auto-discovered Claude Code or credential-pool OAuth credentials.
     api_key = _getenv("ANTHROPIC_API_KEY").strip()
     if api_key:
         return api_key
```

Note the anchor moved from the old `# 3. Claude Code credential file` to the new
`# 3. Regular API key ...` — anchored by *content*, located programmatically.

First hand-written attempt used a bare `@@` with no numbers and died with
`error: patch with only garbage at line 4`. The generator in SKILL.md Step 3
replaced it.

## Step 4 — the local-clone false negative (two wasted rounds)

Attempt A:

```bash
git clone -q --depth 1 --branch main ~/.hermes/hermes-agent patchall
# warning: --depth is ignored in local clones; use file:// instead.
# HEAD: a6defd4f1   ← the FORK's pinned commit, not upstream
```

Result: `0007 … BAŞARISIZ`. Misleading — the patch was already correct.

Attempt B:

```bash
git fetch -q origin aec331899
# fatal: couldn't find remote ref aec331899
git checkout -q origin/main      # still resolved to a6defd4f1
```

Attempt C (the one that works):

```bash
rm -rf /tmp/patchall && mkdir /tmp/patchall && cd /tmp/patchall
git init -q
git remote add origin ~/.hermes/hermes-agent
git fetch -q origin 'refs/remotes/origin/main:refs/heads/upstream'
git checkout -q upstream
git rev-parse --short HEAD        # aec331899  ✓ matches expected upstream
```

Full-stack dry run on the correct tree:

```
0001-anthropic-adapter-ht-prefix-token-isolation.patch     OK
0002-auxiliary-client-token-isolation.patch                OK
0003-chat-completion-ht-prefix-strip.patch                 OK
0005-image-routing-clamp-dimensions.patch                  OK
0007-anthropic-auth-token-resolver.patch                   OK
```

**Lesson, stated plainly:** the SHA print is not ceremony. Two rounds were spent
because a harness silently tested the wrong tree and reported a confident
`BAŞARISIZ`. Print and compare the SHA before believing any result.

## Step 5 — post-apply verification

```
agent/anthropic_adapter.py       | 26 ++++++++++++++++++++--
agent/auxiliary_client.py        | 14 +++++++++---
agent/chat_completion_helpers.py |  7 ++++++
agent/image_routing.py           | 47 ++++++++++++++++++++++++++++++++++++++++
4 files changed, 89 insertions(+), 5 deletions(-)
```

```
anthropic_adapter.py SOZDIZIMI OK
ANTHROPIC_AUTH_TOKEN geçiş sayısı: 2      (comment + code)
sıra doğru mu (2 < 2b < 3): True
_read_creds() kullanıyor: True
eski creds değişkeni KALMADI: True
```

Backup of the pre-rebase patch: `/tmp/0007-eski-yedek.patch`.

## Open follow-up

Offered but not yet built: a guard inside `hermes-update-safe.sh` that asserts
the tree it validates against is genuinely the fetched upstream SHA — the same
Step 4 trap, mechanized so the updater cannot repeat it.
