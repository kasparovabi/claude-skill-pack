# Claude Code flags that matter for Ralph Loops

Quick reference for the subset of `claude -p` flags that materially affect a long-horizon loop. For the full flag list see the `claude-code` skill.

## Required for loops

| Flag | Why |
|---|---|
| `-p "<instruction>"` | Print mode — non-interactive, one-shot, exits cleanly. **Do not** use interactive mode for loops; tmux orchestration adds fragility. |
| `--no-session-persistence` | Without this, a 500-iter loop writes 500 saved sessions to `~/.claude/projects/<...>/` — eats disk, slows future `claude` startup. |
| `--max-turns <N>` | Caps each iter's agentic loop. 80 is a reasonable default; tune by iter complexity. Without this, a confused iter can burn $5+ before timing out. |
| `--dangerously-skip-permissions` + `--permission-mode bypassPermissions` | Loops run unattended; tool-use confirmation dialogs would deadlock. Both flags together skip the runtime prompts AND the launch-time "Yes I accept" dialog. |

## Strongly recommended

| Flag | Why |
|---|---|
| `--model sonnet` | Cost/quality sweet spot. Reserve `opus` for known-hard iters via env var override. Avoid `haiku` for code-writing iters; quality drops too far. |
| `--output-format text` | Plain text per-iter log. Use `json` only if the runner needs to parse `total_cost_usd` or `session_id` for tracking. |
| `--fallback-model haiku` | Graceful degradation when sonnet is overloaded. Better than the iter failing outright. |
| `--max-budget-usd <N>` | Hard cost cap per iter. ~$0.50–$1.00 is reasonable for research+code iters. Minimum ~$0.05 (system prompt cache creation cost). |

## Optional / situational

| Flag | When |
|---|---|
| `--allowedTools "Read,Edit,Write,Bash"` | Tighten the surface if the loop only needs file + shell access. Reduces "agent goes off on a tangent" risk. |
| `--bare` | If the loop project has no `.claude/` config to load, skip hooks/plugins/MCP discovery for faster startup. Requires `ANTHROPIC_API_KEY`. |
| `--append-system-prompt-file path` | Inject loop-specific persona/constraints on top of the default. Cleaner than stuffing everything into the `-p` argument. |
| `--output-format json` + jq parsing | When the runner shell needs to track cumulative cost, session IDs, or failure modes across iters. |

## Anti-patterns

- **Model takma adı (`--model opus` / `--model sonnet`) uzun koşularda** — takma
  ad CLI'nin o günkü varsayılanına çözülür. 300 iterlik bir koşu ortasında CLI
  güncellenirse model sessizce değişir ve `logs/` bakılınca hangi sürümün
  koştuğu okunamaz; iter'lar karşılaştırılamaz hale gelir. Uzun koşularda tam
  sürüm kimliği kullan (`claude-opus-5`, `claude-sonnet-5`) ve kimliği koşudan
  önce doğrula, hatırlama:
  ```bash
  curl -sL https://platform.claude.com/docs/en/docs/about-claude/models/overview.md | grep -i -A2 "Claude API ID"
  strings ~/.local/share/claude/versions/<surum> | grep -oE "claude-(opus|sonnet|fable)-[0-9-]*" | sort -u
  ```
  Kısa/tek seferlik çağrılarda takma ad sorun değil.
- **`--continue` or `--resume <id>` inside a loop** — defeats the point of fresh sessions. Drift accumulates.
- **No `--max-turns`** — runaway loops can burn hundreds of dollars before noticed.
- **Setting `--effort max` on every iter** — 3–5× cost for marginal quality on routine iters. Reserve for known-hard iters.
- **Interactive mode + tmux for loops** — works but is far more fragile than `-p`. Use only if the user explicitly needs human-in-the-loop checkpoints.

## Sample invocation block (copy-ready)

```bash
claude -p "Read $PROMPT in full and execute exactly ONE iteration following section 4 (or section 11 BOOTSTRAP if iter_count==0). Update all state files. Then exit." \
  --dangerously-skip-permissions \
  --permission-mode bypassPermissions \
  --max-turns 80 \
  --max-budget-usd 1.50 \
  --model sonnet \
  --fallback-model haiku \
  --output-format text \
  --no-session-persistence \
  > "$ITER_LOG" 2>&1
```
