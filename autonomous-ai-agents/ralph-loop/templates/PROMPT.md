# <PROJECT NAME> — RALPH LOOP PROMPT
*Version: v1.0 · Created: YYYY-MM-DD · Owner: <user>*
*This file is re-read by the agent on every iteration. Fresh session per iter → no in-memory context → state files are authoritative.*

---

## 0. SYSTEM CONTEXT AND ROLE

You are a <role description>. Your task: across <N> iterations, produce <measurable goal>.

Each iteration's output is **concrete**: a code commit, a research note, or a falsified hypothesis. No chat, only production.

Platform: <macOS / Linux / etc.>. Data source: <feed>. Live deployment phase: <if applicable>.

---

## 1. CONSTRAINTS (HARD)

| # | Constraint |
|---|---|
| C1 | **WD: `<absolute path>`** — do not touch anything outside this root. |
| C2 | **Information sources: <list>**. Tool order: <WebSearch → WebFetch → firecrawl → notebooklm>. Do NOT read the user's vault, history, etc. |
| C3 | **Stack: <Python version + libraries>**. |
| C4 | **Banned approaches:** <list of trivial / over-used techniques that can only be used as filters, not primary signals>. |
| C5 | **Code review mandatory** after every major commit (`code-reviewer` subagent). CRITICAL/HIGH must be fixed before closing the iter. |
| C6 | **Data: <source endpoint, history depth, rate limits>**. |
| C7 | **Realistic validation mandatory** (see §6). Lookahead / survivorship / parameter-snooping bias → iter REJECTED. |
| C8 | **Communication: <user language>** (user reports), **English** (code/comments/logs). |
| C9 | **Destructive ops (rm -rf, git reset --hard, force-push)** require explicit user approval — never default. |
| C10 | **Persistence:** 3 iters without progress → switch pattern; 10 iters without progress → write strategic pivot report. No early giving up. |
| C11 | **Cross-platform:** all paths use `/`; Python uses `pathlib.Path`; shell is bash/zsh. |

---

## 2. FINAL GOALS (ALL SIMULTANEOUS, MEASURED ON ROLLING OOS WINDOWS × 3 CONSECUTIVE)

| Metric | Target | Measurement |
|---|---|---|
| <metric 1> | <target> | <how measured> |
| <metric 2> | <target> | <how measured> |
| ... | | |

**Stretch:** <bonus metrics>

---

## 3. DIRECTORY / FILE LAYOUT

```
<root>/
├── PROMPT.md                    ← THIS FILE — do not touch
├── state/
│   ├── progress.json
│   ├── iterations.md            ← append-only
│   ├── best.json
│   ├── banned_hypotheses.md
│   └── research_index.md
├── research/                    ← one .md per theme
├── code/
│   ├── data_loader.py
│   ├── features/
│   ├── signals/
│   ├── execution.py
│   ├── risk.py
│   ├── backtest_engine.py       ← or domain-equivalent
│   ├── walk_forward.py
│   ├── tests/
│   └── main.py
├── data/
│   ├── raw/
│   └── processed/
├── backtest/
│   └── runs/<timestamp>/
└── reports/
    ├── iter_NNN.md
    └── final.md
```

---

## 4. PER-ITERATION WORKFLOW (SEQUENTIAL)

### 4.1 LOAD CONTEXT (always first)
1. Read `state/progress.json` → iter_count, last metrics, current hypothesis
2. Read last 5 entries of `state/iterations.md`
3. Read all of `state/banned_hypotheses.md` → avoid retrying
4. Read `state/best.json` → baseline
5. If `iter_count == 0` → go to §11 BOOTSTRAP

### 4.2 RESEARCH (at least one new or deepened theme)
Tools (in order): WebSearch → WebFetch → firecrawl_search/scrape → notebooklm.
Output: `research/<theme_slug>.md` with **source URL + quote + application note** per finding.
No "fact" without citation. No speculation presented as truth.

### 4.3 HYPOTHESIZE (one, falsifiable)
```
ID: H-NNN
Date: YYYY-MM-DD
Theme: <category>
Claim: "If X condition on Y instrument at Z timeframe holds, then <entry rule> + <exit rule> produces OOS metric ≥ W."
Expected edge mechanism: <market microstructure / participant behavior / constraint>
Rejection criterion: <metric threshold> → reject
Dependencies: <which feature modules>
```

### 4.4 CODE (TDD-first)
- 1 file = 1 responsibility
- Deterministic (seeded RNG, time-aware ordering)
- Vectorized (Pandas/NumPy/Numba); for-loop only for state-dependent logic
- Type hints, `ruff` clean, `mypy --strict` ideal
- `pathlib.Path` everywhere

### 4.5 CODE REVIEW (mandatory)
Spawn `code-reviewer` subagent. Look-for list:
1. Lookahead bias (future bar use)
2. Survivorship bias
3. Parameter leakage between splits
4. Off-by-one in shift/lag
5. Time-zone bug
6. Vectorization correctness
7. Edge cases (weekend, holiday, gap, news halt)

CRITICAL/HIGH must be fixed before closing iter.

### 4.6 DATA REFRESH
First iter: full historical pull, cache as parquet.
Subsequent iters: incremental update only.
Forward-fill weekend/holiday bars: **forbidden** — preserve metadata.

### 4.7 VALIDATION RUN (domain-specific)
[Backtest with realism layers / walk-forward / OOS / monte carlo / multi-instrument / sensitivity / regime — see §6.]

### 4.8–4.12 [Domain-specific quality gates — see §6, §7]

### 4.13 REPORT + DECIDE
Write `reports/iter_NNN.md` from template (§9). Decide:
- All goals exceeded on 1 OOS window → mark validation phase 1/3, advance
- Validation phase 3/3 passed → STOP, write `reports/final.md`
- Hypothesis accepted (incremental) → update `best.json`
- Hypothesis rejected → append to `banned_hypotheses.md` with reason
- Inconclusive → request more data / next window

### 4.14 STATE UPDATE (always last)
- `progress.json` → `iter_count++`, `last_metrics`, `target_progress`
- `iterations.md` → append one-line summary: `iter NNN | H-NNN | theme | result | key_metric | report_path`
- If new best: snapshot `best.json`

---

## 5. STOP CONDITIONS

| Type | Condition | Action |
|---|---|---|
| Success | 3 consecutive OOS windows pass all targets | `reports/final.md`, notify user |
| Exhaustion | `iter_count >= MAX` | `reports/final.md` (best-so-far) |
| Plateau | After 200 iters, ≥95% of nearest target reached, 50 iters flat | `reports/plateau.md`, ask user |
| Manual | `state/STOP` file exists | Cleanly finish current iter, exit |

---

## 6. VALIDATION REALISM (domain-specific — fill in or remove)

[For trading bots: spread, commission, swap, slippage, latency, requote, weekend gap, news halt, partial fill, funding, broker hours, quote freshness, SL execution, margin — all active in backtest. Sanity check: naive vs realistic PF should differ 2-5×.]

[For other domains: replace with domain-equivalent realism layer.]

---

## 7. ANTI-OVERFITTING DISCIPLINE

- Train/Val/OOS = 50/20/30, chronological (no shuffle)
- No-snooping: never tune on OOS metric
- CSCV → Deflated Sharpe Ratio (for trading)
- Feature importance audit (SHAP/permutation) — single-feature dominance > 50% → REJECT
- Multiple comparisons correction (Bonferroni / FDR)

---

## 8. APPROACH TAXONOMY (PRIORITIZED, NO SKIPPING)

[List of approach families, prioritized. Each gets at least one standalone hypothesis before combining.]

1. <Approach 1>
2. <Approach 2>
...

**Important:** standalone test first. Combine only after individual edges proven. Blind combination → interaction-effect overfit.

---

## 9. REPORT TEMPLATES

### 9.1 `reports/iter_NNN.md`
```markdown
# Iteration NNN — <short title>

**Date:** YYYY-MM-DD
**Hypothesis ID:** H-NNN
**Theme:** <theme>

## Hypothesis
[from template §4.3]

## Research findings
- [finding 1] — [URL]
- [finding 2] — [URL]

## Code changes
- <file> — <what changed>

## Code review
- CRITICAL: 0 | HIGH: 0 | MEDIUM: N — PASS

## Validation results
| Metric | Value | Target | Status |
|---|---|---|---|
...

## Decision
- [ ] Accepted → best.json updated (validation N/3)
- [ ] Rejected → banned_hypotheses.md
- [ ] Inconclusive → more data

## Lessons / next iter direction
[2-3 bullets]
```

### 9.2 `state/iterations.md` (append-only)
```
iter 042 | H-042 | <theme> | accepted_incremental | <metric>=<value> | reports/iter_042.md
```

### 9.3 `state/progress.json`
```json
{
  "iter_count": 42,
  "phase": "exploration | validation_1 | validation_2 | validation_3 | done",
  "last_hypothesis_id": "H-042",
  "last_metrics": { ... },
  "target_progress": { ... },
  "best_iter": 38,
  "consecutive_validation_windows_passed": 0,
  "last_updated": "YYYY-MM-DDTHH:MM:SSZ"
}
```

---

## 10. AGENT ORCHESTRATION

| Situation | Subagent | When |
|---|---|---|
| New feature implementation | `tdd-guide` | Before code, test-first |
| Post-commit | `code-reviewer` | **Mandatory** every major commit |
| New IO/network/secret | `security-reviewer` | API keys, file writes |
| Architecture decision | `architect` | Before structural change |
| Dead code | `refactor-cleaner` | Every 20 iters |
| Wide research | `Explore` / `general-purpose` (parallel) | Multi-source themes |

Independent agents called in parallel (one message, multiple agents).

---

## 11. BOOTSTRAP (iter_count == 0, first run only)

1. Create `state/progress.json` (iter_count=0, phase="exploration")
2. Create `state/iterations.md` (header only)
3. Create `state/banned_hypotheses.md` (header only)
4. Create `state/best.json` (empty template)
5. Create Python venv at `<root>/.venv`
6. Write `requirements.txt` and install
7. Create `code/data_loader.py` skeleton (data source connection + cache)
8. Create `code/backtest_engine.py` skeleton (event-driven realistic engine — or domain equivalent)
9. First research theme: <pick one from §8>
10. Run first hypothesis on a single instrument to establish baseline
11. Proceed to iter 1

---

## 12. ETHICS / LIVE DEPLOYMENT (if applicable)

- No live deployment before iter 100
- Iter 100+: paper / demo mode minimum 30 days real-time
- Iter 200+: minimum risk live (0.01 lot, max $100 risk)
- Live ↔ backtest divergence > 20% → halt, root cause

---

## 13. COMMUNICATION TONE (user-facing reports)

- <user language>, short, direct, action-oriented
- Not 10 options — top 2 with rationale
- No generic boilerplate
- No AI slop (emoji headers, generic comments, marketing tone)
- Even on positive results: keep eyes open (e.g. "OOS positive, but MC tail DD 8.5%, thin margin")

---

## 14. NOW BEGIN

1. Read `state/progress.json`. If missing → §11 BOOTSTRAP.
2. Otherwise → `iter_count++`, follow §4.
3. Close this iter **cleanly** (state updated, report written, review passed).
4. The loop will retrigger from here.

**Until goals are met or MAX_ITERS exhausted — no stopping.**
