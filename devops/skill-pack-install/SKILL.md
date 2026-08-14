---
name: skill-pack-install
description: >
  Install an EXTERNAL skill pack (a GitHub repo full of SKILL.md folders, e.g.
  agent-skills collections) into BOTH this Hermes profile AND the user's global
  Claude Code CLI (~/.claude/skills/), apply the user's ethics/tech filter as an
  override note, and add a Turkish natural-language trigger router so the user
  never types a slash command. Use when the user says "şu repodaki skilleri al
  kur", "bunları kendine kur", "Claude CLI'ya da kur", "install these skills",
  or shares a GitHub URL of a skill/agent-skill pack and wants it usable.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [skills, install, claude-cli, multi-target, turkish-router, ethics-filter]
    related_skills: [skill-vetter, claude-code]
---

# Installing an external skill pack (Hermes + global Claude CLI)

The user collects skill packs from GitHub (Three.js graphics, web-motion, etc.)
and wants them usable BOTH by this Hermes agent AND by their global Claude Code
CLI, triggerable from plain Turkish without slash commands. This is a recurring
class of task — here's the proven flow.

## 0. Vet first (if untrusted source)
For a brand-new/unknown author, run the `skill-vetter` skill before installing —
check for suspicious scripts, exfil patterns, over-broad permissions. Established
MIT/CC0 packs from a readable repo are usually fine; still skim the scripts.

## 1. Clone + inspect structure
```bash
git clone --depth 1 <repo> /tmp/pack
find /tmp/pack -iname 'skill.md'        # how many real skills, where
du -sh /tmp/pack/skills                 # size (these are usually small, <1MB)
```
Each skill folder typically carries SKILL.md + examples/ + references/ +
templates/. PRESERVE that structure — copy whole folders, not just SKILL.md.
Note shared top-level dirs (rankings/, playbooks/, rubrics/) — fold them into
one skill's `references/shared/` so they stay reachable.

## 2. Install to Hermes
```bash
cp -R /tmp/pack/skills/* "$HOME/.hermes/skills/<category>/"
```
Then VERIFY with `skills_list(category=...)` — Hermes must list them with
descriptions and `readiness_status: available`. Open one with `skill_view` to
confirm linked_files (examples/references) resolve.

## 3. Install to the global Claude CLI
Claude Code reads global skills from `~/.claude/skills/` and auto-invokes them
by natural language (no slash needed — that's exactly the user's goal):
```bash
mkdir -p "$HOME/.claude/skills"
cp -R /tmp/pack/skills/* "$HOME/.claude/skills/"
```
New skills appear in a FRESH Claude session — the user must restart any open
Claude session to pick them up. Tell them this.

## 4. Apply the ethics/tech-filter override (THIS USER — critical)
Skill packs are often written for the author's own stack. This user REJECTS
Vercel/Next.js/SvelteKit (ethics) and the author's brand references mean nothing
here. Write a `YEREL_UYARLAMA.md` note INTO the pack dir (and copy to
`~/.claude/skills/_YEREL_UYARLAMA_<pack>.md`) that OVERRIDES the pack's
recommendations: use Nuxt/Astro/Hetzner/FastAPI/Supabase instead of Vercel;
read brand names as "this project"; prefer free/local generative providers
before paid APIs; apply the client visual identity where relevant. The router (next
step) must require reading this note before acting.

## 5. Add a Turkish natural-language trigger router
The pack's SKILL.md descriptions are English/technical. The user types things
like "hareketli bir site yap" / "okyanuslu 3D sahne" / "tanıtım filmi". Create
ONE router skill (description packed with the Turkish phrases that should fire
it) that maps those phrases to the right pack skill, and load the actual skill
from there. Mirror the router into `~/.claude/skills/` too. See
`templates/turkish-router.md` for the structure.

## Pitfalls
- **Don't trust "copied" = "registered".** Always `skills_list` after, and
  `skill_view` one skill to confirm linked files resolve.
- **Turkish chars + heredoc/`python3 -c`** trip the confusable-unicode scanner.
  Write files with write_file, not inline shell with Turkish content.
- **Preserve sub-dirs.** `cp -R` whole skill folders; copying only SKILL.md
  loses the example code that makes these packs valuable.
- **License/attribution:** keep each skill's own frontmatter (its title is the
  attribution). MIT/CC0 packs are reusable; note the license in your reply.
