---
name: ralph-loop
description: "Use when running a long-horizon autonomous loop. Fresh session per iteration."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Autonomous, Ralph, Loop, Long-Running, State-Driven, Claude-Code]
    related_skills: [claude-code, codex, opencode, writing-plans]
---

# Ralph Loop — Long-Horizon Autonomous Iteration Pattern

A **Ralph Loop** is a self-driving research/build loop where the agent runs **N iterations** (often 100–500) toward a measurable goal, with each iteration spawning a **fresh** agent session that reads a canonical instruction file and a small set of state files to know where it left off. Named after the "Ralph Wiggum" pattern popularized by Geoff Huntley — dumb-simple, durable, append-only.

## When to use

Use when the user asks for any of:
- "Run a loop until X metric is achieved"
- "500 iterations of <research/optimization/refinement>"
- A multi-day autonomous build/research with checkpointed progress
- Scalping bot, model search, hypothesis testing, content factory, etc.

Do NOT use for one-shot tasks (`claude -p "fix bug"`), short interactive sessions, or anything that fits in a single context window.

## Core invariants

1. **Fresh session per iteration.** Each iter is a brand-new `claude -p` (or codex/opencode equivalent) invocation. No conversation context survives. State must live on disk.
2. **PROMPT.md is canonical.** Every iter re-reads this file as the source of truth for goals, constraints, workflow steps, banned approaches, and stop conditions. Never let the agent edit it without explicit human approval.
3. **State files are authoritative.** `state/progress.json`, `state/iterations.md` (append-only), `state/best.json`, `state/banned_hypotheses.md`, `state/research_index.md`. The agent reads these first, writes them last.
4. **Append-only iteration log.** `state/iterations.md` gains exactly one line per iter (`iter NNN | H-NNN | theme | result | key_metric | report_path`). Never rewritten.
5. **Stop conditions are explicit and external.** Success criterion (e.g. "3 consecutive OOS windows pass"), exhaustion (`iter_count >= MAX`), plateau, or a `state/STOP` sentinel file. The runner shell checks for the sentinel between iters so the user can stop cleanly.
6. **No destructive ops without approval.** `rm -rf`, `git reset --hard`, force-push — banned by default in PROMPT.md.

## Directory layout (canonical)

```
<project>/
├── PROMPT.md                ← canonical instruction, agent re-reads every iter
├── state/
│   ├── progress.json        ← iter_count, phase, last_metrics, best_iter
│   ├── iterations.md        ← append-only one-line summary per iter
│   ├── best.json            ← snapshot of best config so far
│   ├── banned_hypotheses.md ← falsified approaches (don't retry)
│   ├── research_index.md    ← theme → research/<file>.md
│   └── STOP                 ← (optional sentinel; runner exits on next iter)
├── research/                ← web findings, one .md per theme
├── code/                    ← the actual artifact being built
├── reports/
│   ├── iter_NNN.md          ← per-iter detailed report
│   ├── final.md             ← written on success/exhaustion
│   └── plateau.md           ← written on plateau detection
└── run_loop.sh              ← runner shell (see templates/run_loop.sh)
```

## Runner shell pattern

The runner is a thin bash loop, not part of the agent. Responsibilities:
1. Check for `state/STOP` sentinel before each iter
2. Spawn fresh `claude -p` with the canonical prompt-reading instruction
3. Log per-iter output to `logs/iter_<TS>.log`, summary to `logs/loop.log`
4. Exit on: sentinel, `reports/final.md` exists, `MAX_ITERS` reached
5. Brief sleep between iters (rate-limit hygiene)

See `templates/run_loop.sh` for a tested, ready-to-copy version.

Key flags for the agent invocation (Claude Code example):
```
claude -p "Read $PROMPT in full and execute exactly ONE iteration following section 4. Update all state files. Then exit." \
  --dangerously-skip-permissions \
  --permission-mode bypassPermissions \
  --max-turns 80 \
  --model sonnet \
  --output-format text \
  --no-session-persistence
```

- `--no-session-persistence` is critical: prevents thousands of orphan sessions piling up on disk over a 500-iter run.
- `--max-turns` caps each iter's agentic loop (80 is a reasonable starting point for research+code+backtest iters; tune per workload).
- `sonnet` is the cost/quality sweet spot for most iters; reserve `opus` for hard reasoning iters via a manual override.

## PROMPT.md structure (template)

See `templates/PROMPT.md` for a battle-tested skeleton with these sections:

1. System context & role
2. **Constraints (C1–C10+)** — working directory, banned tools/signals, stack, communication language, destructive-op rules, persistence rule (don't give up after 3 fails — pivot pattern instead)
3. Final goals (measurable, simultaneous, with validation phases — e.g. "3 consecutive OOS windows")
4. Directory layout
5. **Per-iteration workflow (sequential steps)** — context load → research → hypothesis → code → review → run → report → state update
6. Stop conditions
7. Domain-specific quality gates (e.g. backtest realism, anti-overfitting discipline)
8. Edge / approach taxonomy (prioritized list of avenues to explore)
9. Report templates (iter_NNN.md, iterations.md line, progress.json schema)
10. Agent orchestration (when to spawn subagents — reviewer, planner, etc.)
11. **Bootstrap section** (iter_count == 0 special case: venv, requirements, skeleton files, first hypothesis)
12. Ethics / live-deploy gates (don't ship to production before iter N)
13. Tone notes for user-facing reports
14. Final "START HERE" reminder

## Per-iteration workflow (the agent's job each iter)

1. **Load context** — read `progress.json`, last 5 lines of `iterations.md`, all of `banned_hypotheses.md`, `best.json`. If `iter_count == 0` → go to BOOTSTRAP.
2. **Research** — at least one new or deepened theme; output `research/<slug>.md` with source URLs and quotes (no hallucination, no "fact" without citation).
3. **Hypothesize** — one falsifiable hypothesis with explicit rejection criterion.
4. **Code** — TDD-first for new modules; vectorize; type hints; pathlib.Path everywhere (cross-platform).
5. **Code review** — spawn `code-reviewer` subagent; CRITICAL/HIGH must be fixed before closing iter.
6. **Run / validate** — backtest, walk-forward, OOS, monte carlo, multi-instrument, sensitivity, regime robustness (whichever apply to the domain).
7. **Report** — write `reports/iter_NNN.md` from template.
8. **Decide** — accept incremental / accept validation-phase-N / reject (add to banned) / inconclusive (more data).
9. **Update state** — increment `iter_count`, append `iterations.md` line, maybe update `best.json`.

## Pitfalls & gotchas

- **Forgetting `mkdir -p logs/` before runner starts** — `nohup ... > logs/runner.out` will silently fail with "No such file or directory" and the runner exits immediately. Always pre-create log dirs in the runner script itself or in bootstrap.
- **Letting the agent edit PROMPT.md mid-loop** — drift accumulates over 500 iters and goals erode. Lock it behind explicit human approval ("revision iteration").
- **Background `&` from agent tooling** — most agent terminals refuse `&` backgrounding; use the tool's proper `background=true` flag (Hermes `terminal(background=true)`, etc.) and pass `nohup ./run_loop.sh > logs/runner.out 2>&1` style commands.
- **No `state/STOP` check between iters** — without it, the user has no clean way to halt without killing PIDs and risking partial state writes. Always add the sentinel check at the top AND bottom of the runner loop.
- **Resumability assumed but not tested** — kill the runner mid-iter and restart; if `state/progress.json` is half-written or `iterations.md` got two lines for the same iter, your atomicity is broken. Write state in a single atomic rename (`tmp → final`).
- **Sessions piling up** — without `--no-session-persistence`, a 500-iter loop leaves 500 saved sessions in `~/.claude/projects/<...>/` eating disk and slowing subsequent `claude` startup.
- **Banned approaches re-tried** — the agent often re-derives a hypothesis it already falsified. Make `banned_hypotheses.md` short, scannable, and explicitly listed in the "Load context" step.
- **Platform-locked dependencies** — if PROMPT.md was authored on Windows (e.g. `MetaTrader5` Python package, `A:\` drive paths), porting to Mac/Linux requires swapping data source (Dukascopy free bi5 endpoints, ccxt, Polygon, IBKR) and replacing all `A:\...\` with `/Users/.../` + `pathlib.Path`. See `references/cross-platform-migration.md`.
- **Cost explosion** — 500 iters × $0.50/iter = $250. Set `--max-budget-usd` per iter or cap via fallback model. Monitor `total_cost_usd` in JSON output if running `--output-format json`.
- **Context degradation within an iter** — if `--max-turns` is high (80+) and the iter does heavy research+code+test, the agent's quality drops in the last turns. Prefer narrower iters (one hypothesis per iter) over fat iters that try to do everything.

## Verification checklist (before launching a loop)

- [ ] `PROMPT.md` exists and is the canonical source the agent reads first
- [ ] `state/` directory pre-created with initial `progress.json` (`iter_count: 0`)
- [ ] `logs/` directory pre-created (runner won't crash on first redirect)
- [ ] `run_loop.sh` is `chmod +x` and tested with `MAX_ITERS=2` first
- [ ] `state/STOP` sentinel mechanism documented for the user
- [ ] Stop conditions in PROMPT.md include both success and exhaustion paths
- [ ] First-iter BOOTSTRAP path is unambiguous (venv, requirements, skeleton files)
- [ ] Cost cap or fallback model configured if running unattended

## Support files

- `templates/run_loop.sh` — runner shell, copy and adapt
- `templates/PROMPT.md` — canonical instruction skeleton
- `templates/progress.json` — initial state file
- `references/cross-platform-migration.md` — porting Windows-authored prompts to Mac/Linux
- `references/claude-code-flags.md` — quick reference for the `claude -p` flags that matter for loops

## Related skills

- `claude-code` — for the underlying CLI flags, dialog handling, MCP integration
- `multi-agent-pipeline-audit` — when a *recurring scheduled* agent crew's report
  quality degrades (alarm fatigue, silent data faults, no reaper role). Ralph
  loops iterate toward a metric; that skill diagnoses standing crews.
- `writing-plans` — for the structured planning step inside iter workflows
- `subagent-driven-development` — if the loop spawns reviewer/architect subagents
