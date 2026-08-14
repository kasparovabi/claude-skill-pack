#!/usr/bin/env python3
"""gain.py — measure & remember whether ponytail actually paid off.

Ponytail's weakest spot is that its benefit is a feeling. The upstream repo
itself over-claimed (80-94%) until an issue forced it down to a measured ~54%.
So don't trust the feeling: log the real numbers and let them shape where
ponytail gets applied hard vs. skipped.

Two modes:

  log     record one task's outcome (ponytail vs. baseline LOC + deps avoided)
  summary read the log back: mean gain overall and per task-kind, plus a
          ladder-weighting hint (where ponytail earns its keep here)

The log is a JSONL file next to this script (assets/gain-log.jsonl). One line
per task. Stdlib only.

Usage:
    python3 gain.py log --kind <kind> --ponytail <loc> --baseline <loc> \
            [--deps-avoided N] [--note "..."]
    python3 gain.py summary
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "assets" / "gain-log.jsonl"


def _arg(argv, flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def log(argv):
    p = int(_arg(argv, "--ponytail"))
    b = int(_arg(argv, "--baseline"))
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": _arg(argv, "--kind", "misc"),
        "ponytail_loc": p,
        "baseline_loc": b,
        "deps_avoided": int(_arg(argv, "--deps-avoided", 0)),
        "note": _arg(argv, "--note", ""),
    }
    rec["gain_pct"] = round((1 - p / b) * 100, 1) if b else 0.0
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"logged: {rec['kind']} — {b}→{p} LOC ({rec['gain_pct']}% less), "
          f"{rec['deps_avoided']} dep(s) avoided")
    return 0


def summary(_argv):
    if not LOG.exists():
        print("no gain log yet — run `gain.py log ...` after a few tasks first.")
        return 0
    rows = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    if not rows:
        print("gain log empty.")
        return 0
    mean = sum(r["gain_pct"] for r in rows) / len(rows)
    deps = sum(r["deps_avoided"] for r in rows)
    print(f"tasks logged : {len(rows)}")
    print(f"mean gain    : {mean:.1f}% less code")
    print(f"deps avoided : {deps} total")
    print("\nby task-kind (mean gain — where ponytail earns its keep):")
    kinds = {}
    for r in rows:
        kinds.setdefault(r["kind"], []).append(r["gain_pct"])
    for kind, vals in sorted(kinds.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        m = sum(vals) / len(vals)
        hint = "go ultra" if m >= 40 else "full is right" if m >= 15 else "barely helps — lite/skip"
        print(f"  {kind:<22} {m:5.1f}%  (n={len(vals)})  → {hint}")
    return 0


def main(argv):
    if not argv or argv[0] not in ("log", "summary"):
        print(__doc__)
        return 2
    return {"log": log, "summary": summary}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
