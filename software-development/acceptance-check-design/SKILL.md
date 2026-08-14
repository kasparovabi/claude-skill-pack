---
name: acceptance-check-design
description: "Use when writing checks that verify a fix landed."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, acceptance, probes, remediation, false-pass, audit]
    related_skills: [systematic-debugging, test-driven-development, delivered-artifact-verification]
---

# Acceptance Check Design

## Overview

You wrote a list of defects. Someone else — a vendor, another team, a future
agent, a migration script — is going to fix them. You now need a check that
answers one question per defect: **is this actually fixed, or does it only
look fixed from where I'm standing?**

The failure mode this skill prevents is the **false pass**: a check that
reports GREEN while the defect is completely intact. A false pass is worse
than no check. No check leaves everyone appropriately uncertain. A false pass
closes the ticket, tells the stakeholder the work is done, and gets discovered
weeks later by a customer.

**Core principle: a check that cannot fail is not a check.** Before you trust
any probe, prove it can go red.

## When to Use

- Verifying a third party (vendor, agency, hosting provider, another team) did
  the remediation work you specified
- Writing acceptance criteria for an audit, punch list, or defect register
- Building CI gates, deploy smoke tests, or post-migration verification
- Any script whose output you will forward to someone as evidence
- Re-checking anything you personally previously reported as "done"

Use it *before* handing over a check, not only when the check misbehaves.

## The Iron Law

```
RUN THE CHECK AT BASELINE BEFORE ANYONE FIXES ANYTHING.
EXPECT NEAR-TOTAL FAILURE. EVERY PASS AT BASELINE IS A BUG IN YOUR CHECK.
```

This is the RED step of TDD, applied to probes against systems you do not
control. It is cheap, it takes one run, and it is the single highest-yield
habit in this skill.

In the reference case, the baseline run reported 3 of 15 items already passing
on a system where the audit had documented every one of the 15 as broken. All
three were defects in the probe, not fixes in the world. Without the baseline
run, all three would have shipped as "vendor already handled these."

Record the baseline output. It is also your before/after evidence.

## The Four Calibration Questions

Ask these of every single check before trusting it.

### 1. Did the probe actually reach the system under test?

An empty, silent, or error response is not evidence of correct behavior. It is
usually evidence that you never made contact.

The classic form: you probe with a made-up identifier to prove the system
rejects unknown input — but the made-up identifier never resolves, so the
request dies before it leaves your machine. You interpret "nothing came back"
as "the system correctly returned nothing." Green. Meanwhile the defect is
untouched.

**Rule:** assert reachability separately from correctness. Resolve the name,
check the connection, confirm you got a real response, *then* judge the
response.

```python
# WRONG: absence of a response read as correct behavior
body = fetch(f"https://{made_up_host}/")
if not body.strip():
    return True, "empty response (correct)"

# RIGHT: prove contact first, and probe something that genuinely exists
if not resolves(host):
    return False, "probe target does not resolve — cannot measure, check manually"
body = fetch(f"https://{host}/")
...
```

Never let "could not measure" collapse into "passed". Make it a third state or
a failure, never a success.

### 2. Am I measuring the population that actually exhibits the defect?

A check that samples the healthy half of the estate always passes.

In the reference case, the defect was that the *duplicate* hostnames served
another country's site map. The check sampled the *canonical* hostnames, which
had always been correct. Nine sites, all green, defect fully present.

**Rule:** derive the check's sample from the defect description, not from the
convenient or canonical list. If the finding says "the mirrored variants are
wrong", the probe targets the mirrored variants. Write the population into the
check's docstring so the next reader can see the choice was deliberate.

### 3. Does the instrument match the claim, and use the same trust settings as the real client?

Reachability is not identity. HTTP 200 is not "the certificate is valid." A
tolerant client that skips verification will happily report success on exactly
the failure you were asked to detect.

**Rule:** measure with the same strictness the real consumer uses, and assert
the property named in the defect — not a nearby proxy for it.

| Defect claim | Weak instrument (false-passes) | Right instrument |
|---|---|---|
| "certificate is invalid" | fetch with verification disabled; HTTP 200 | verification **enabled** + assert CN/SAN matches the hostname + expiry margin |
| "serves the wrong site" | status code | fetch body, assert an identifying string for the *expected* entity |
| "page metadata is empty" | page loads | parse the field, assert non-empty **and** a minimum length |
| "stale/always-now timestamps" | field is present | count *distinct* values; assert none equals request time |
| "internal addresses leak" | name resolves | enumerate all records, assert none is in a private range |
| "admin UI is exposed" | status code | fetch body, assert vendor fingerprint strings are absent |
| "redirect not configured" | follow redirects, get 200 | do **not** follow; assert 3xx status and inspect the `Location` header |

That last row is its own trap: following redirects by default turns "is there a
redirect?" into an unanswerable question, because you only ever see the
destination.

### 4. Would this check go red if the defect were reintroduced tomorrow?

If you cannot describe the concrete change that would flip it, the check is
decorative. Where cheap, actually flip it: point the probe at a known-bad
target and confirm red.

## Procedure

① **Transcribe each defect into one check with a named, falsifiable criterion.**
One defect, one check, one verdict. Do not bundle.

② **Write the check to report three states**, not two: PASS, FAIL, and
CANNOT-MEASURE. Silently folding the third into PASS is the root of most false
passes. Folding it into FAIL is merely annoying — prefer that if you must
choose two.

③ **Run at baseline.** Expect near-total failure. Investigate every pass.

④ **Fix the checks the baseline exposed**, then re-run baseline. Iterate until
the only passes are ones you can explain with independent evidence.

⑤ **Emit detail alongside the verdict.** `KALDI` / `FAIL` alone starts an
argument. `FAIL — HTTP 200 but CN=other.example, expected api.example` ends
one. The remediator should be able to act on the line without asking you
anything.

⑥ **Make it re-runnable and read-only.** The other party will run it too. It
must not mutate anything, must take a filter argument (`P0`, a single item id)
so a single fix can be re-checked in seconds, and must be safe to run from a
laptop.

⑦ **Hand over the check with the defect list.** A punch list plus its
acceptance script converts "we did it" into a shared, mechanical fact and
removes the negotiation entirely.

## Distinguishing a Real Pass from a Suspicious One

When a check passes at baseline, there are exactly three explanations. Work
through them in this order:

1. **The probe is broken** (most likely). Apply the four calibration questions.
2. **The finding was wrong** when it was written. Re-read the original
   evidence.
3. **It was genuinely fixed between the audit and now.** Plausible when days
   have passed, especially for expiring artifacts like certificates.

Never assume (3) without independent corroboration — a second instrument, a
timestamp, or a changelog. When (3) is genuinely likely, say so in the check's
docstring so the next reader is not confused, and note that the item may have
closed itself.

## Reporting the Miscalibration

If you already told someone a check passed and later discover it false-passed,
say so plainly and immediately, lead with the correction, and state the
corrected baseline. Do not bury it in a list of accomplishments and do not let
the earlier number stand uncorrected anywhere. The credibility of every other
number you produce depends on this one being volunteered rather than
discovered.

## Pitfalls

- **Probing with invented identifiers to test rejection.** They usually fail to
  resolve, so you measure your own DNS, not their server. Use a real identifier
  the system genuinely does not have configured.
- **Following redirects while testing for a redirect.** Disable redirect
  following for those checks, and inspect the status line and `Location` header.
- **Disabling certificate verification "so the check works".** That is the
  check inverting itself. Use a tolerant fetch only for a *secondary* read of
  what the server serves behind the broken certificate, and always alongside a
  strict primary probe.
- **Presence checks on fields that must have content.** Empty title tags,
  zero-length descriptions, and `null` values all "exist". Assert length and
  shape.
- **Uniform-value fields read as populated.** 1,312 rows each carrying a
  timestamp looks healthy until you count distinct values and find one.
  Cardinality is the check, not presence.
- **Trusting one instrument on a slow or flaky target.** Timeouts read as
  failure and transient successes read as passing. Re-run the individual item
  before reporting a flip in either direction.
- **Long serial probe suites blowing the tool timeout.** Parallelize with a
  bounded worker pool, keep per-request timeouts short, and support the filter
  argument so a targeted re-check is fast.
- **Deciding an item "passes" from a fact you already believed.** The check must
  derive its verdict from this run's measurement, never from the audit document
  it was written against.

## Reference Material

- `references/false-pass-case-studies.md` — three real false passes with the
  broken and corrected probe code side by side, plus the baseline table.
- `references/web-remediation-probes.md` — a worked corpus of read-only probes
  for web-infrastructure remediation (TLS, DNS, redirects, metadata, sitemaps,
  structured data), and the shape of the fix artifacts those probes verify.

## Related Skills

- `systematic-debugging` — building a red-capable loop for a bug you own. This
  skill is its counterpart for defects someone *else* will fix.
- `test-driven-development` — same RED-first instinct, applied to code under
  your control.
- `delivered-artifact-verification` — when the disputed artifact is one you
  delivered and the user says it is wrong.
