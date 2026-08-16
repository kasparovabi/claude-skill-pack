# What these skills came out of

Every skill in this repository was written while doing work that had to keep
running afterwards. This file is the evidence behind that claim, because a
repository of procedures is only worth reading if the procedures survived
contact with a real deployment.

The context is one organisation operating schools in 66 countries. Fourteen
internal applications built since February 2026, twelve live and used daily by
people who are not engineers. Seven of those are automations, the rest are
tools and sites. Six months in, they are still running.

I do not write the implementation layer by hand. I direct AI tools to produce
it and own the result, which means the design decision, the evaluation harness,
the gates that decide whether it ships, and the pager when it breaks.

## The pattern that repeats

In every case below, the stated request and the real problem were different
things. Finding that gap is most of the work. Building the thing is the easy
part, and the part I delegate to a model.

### Request intake

**Stated request.** A task tracker for the communications team.

**Real problem.** Work arrived by email and stayed there. Nobody types work
into a tracker, so any tracker they adopted would sit empty. The tracker was
not the missing piece, the transcription step was.

**What shipped.** A system that reads a shared mailbox, decides whether an
incoming message is a task, and assigns it to the right person. Nobody types
anything.

**What broke.** Classification was confident on messages that were not tasks
at all. Fixed by making low confidence route to a human queue instead of
guessing, which is the same rule that shows up in several skills here.

**Still running.** Yes, daily.

### Parametric signage generator

**Stated request.** A design tool for campus signage.

**Real problem.** Seven country offices were producing inconsistent signage
because each interpreted one brand guide differently. A design tool would have
given them a faster way to keep being inconsistent.

**What shipped.** A generator producing press ready output for campuses in
seven countries across three writing systems, including right to left. Correct
output is the easiest output to produce, which is the only way a standard ever
holds.

**What broke.** Arabic text rendered in the wrong direction inside mixed
strings. Latin and Arabic in one label needed separate handling, not one
pipeline. Documented in `productivity/reportlab-turkish-pdf`.

**Still running.** Yes.

### Workshop authoring platform

**Stated request.** A place to store workshop content.

**Real problem.** Content existed but reaching print meant a designer manually
rebuilding each workshop in three languages, so publishing was bounded by
designer hours rather than by content.

**What shipped.** Structured content converted to press ready InDesign output
in three languages. The designer sets up the template once, then every workshop
flows through it.

**What broke.** The first version emitted markup the InDesign importer silently
dropped. Silent is the operative word, output looked fine until a page was
missing. Now the pipeline counts elements in and elements out and fails loudly
on a mismatch.

**Still running.** Yes.

## Reliability work

The skills in `software-development/` and `devops/` come out of this part.

**A twenty check gate for agent authored changes.** Nothing an agent writes
becomes a pull request without passing it. This month two of four security
findings were rejected by the gate before reaching a maintainer, one
duplicating a published CVE and one that did not reproduce. That rejection rate
is the argument for having a gate at all. A gate that never rejects anything is
not a gate.

**A CI check that validates every model identifier against the live provider
API.** Model names get retired. A pipeline referencing a retired model fails at
the worst possible time, which is in production, after the deploy that looked
green. Now it fails at CI time instead.

**Scheduled job supervision.** A job that stops running is invisible, because
absence of output looks exactly like a quiet day. Covered in
`devops/scheduled-job-reliability`.

## Upstream contributions

A bug report to `comfyui-mcp` about skill files exceeding documented size
limits turned out to be hiding a worse defect. Two skills carried a colon and
space inside a YAML plain scalar, which the parser rejects, so the loader fell
back to an empty description and both skills shipped with no description at
all. One of them was the bug reporting skill, whose entire trigger is its
description.

A second defect surfaced while verifying the first. The generator script
matched line endings against raw bytes, so on any Windows checkout every
generated skill lost its description.

Neither was found by reading. Both were found by replaying the real loader over
the real files, which is the discipline in
`software-development/dogrulama-disiplini`.

## What this does not claim

None of this is a large engineering organisation. It is one person inside one
institution, and the systems serve hundreds of users rather than millions. The
claim is narrow and specific, which is that these procedures were written by
someone who had to keep the result working, not by someone summarising a
vendor's documentation.

Where a skill is thin, it is thin because I have only used it a few times. The
ones that go deep are the ones that cost me the most.
