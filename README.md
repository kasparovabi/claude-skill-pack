# Claude Skill Pack

Procedural knowledge written while doing the work, not while planning it. Every
skill here came out of a task that went wrong at least once, and the fix is in
the file.

The deployments these came out of, including what broke and what is still
running, are in [PRODUCTION-EVIDENCE.md](PRODUCTION-EVIDENCE.md).

These are Markdown skills for [Claude Code](https://claude-code.anthropic.com)
and compatible agents. Drop a folder into `~/.claude/skills/` (or your agent's
skill directory) and the agent picks it up.

## What is in here

| Category | Skills | What they cover |
|---|---|---|
| `devops` | 10 | Browser automation against real logged-in sessions, scheduled job reliability, vetting and publishing skill packs |
| `software-development` | 8 | Acceptance checks that actually verify, verification discipline, debugging agent TUIs |
| `creative` | 7 | Programmatic image and video generation, WebGPU shaders, print-ready compositing |
| `productivity` | 7 | PDF table extraction by coordinate, Turkish-language PDF generation, HTML email signatures |
| `autonomous-ai-agents` | 6 | Orchestrating agent crews, long-horizon loops, merge conflict resolution between agents |
| `research` | 3 | Terminal-based web search, hands-on tool evaluation, coordinated vulnerability disclosure |
| `apple`, `data-science`, `github`, `media`, `red-teaming` | 8 | Platform-specific and single-purpose procedures |

49 skills total.

## A few that earned their place

**`devops/authenticated-browser-automation`** — driving a browser that is
already logged in, without a headless rig. Covers the native file picker (JS
cannot fill `input[type=file]`, but a real click plus `Cmd+Shift+G` can), lazy
list scrolling that silently returns only the first screen, and why a fixed
`sleep` produces plausible-looking garbage data.

**`software-development/dogrulama-disiplini`** — what to do when a check passes
but reality disagrees. The short version: a uniform result across every item is
not a finding, it is a broken pipeline.

**`devops/skill-pack-publish`** — publishing a skill library without leaking.
Includes the measurement that force-pushing does not remove old commits: they
stay reachable by SHA until GitHub garbage-collects, so a leaked secret needs a
repo delete, not a rewrite.

**`research/hands-on-tool-evaluation`** — the rule that you do not present a
public repo you have not actually run.

## Scope and honesty

Client identifiers, personal contact details and machine-specific paths have
been removed. Skills that could not be cleanly generalised were left out rather
than published half-scrubbed — a job-search pipeline, a corporate content
workflow and a writing-voice profile among them. They would teach you nothing
and expose things that are not mine to publish.

Vendor documentation packs (cloud provider references, SDK guides) are also
excluded. They are someone else's docs summarised, not knowledge from working.

## Installing

```bash
git clone https://github.com/kasparovabi/claude-skill-pack.git
cp -r claude-skill-pack/devops/authenticated-browser-automation ~/.claude/skills/
```

Or copy the whole tree. Skills are plain Markdown with YAML frontmatter; nothing
executes on install. The `scripts/` folders inside some skills run only when the
skill tells the agent to run them, and you can read them first.

## License

MIT. See `LICENSE`.
