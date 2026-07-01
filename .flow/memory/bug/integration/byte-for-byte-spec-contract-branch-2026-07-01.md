---
title: "Byte-for-byte spec contract: branch prose into variants, don't annotate shared l"
date: "2026-07-01"
track: bug
category: integration
module: plugins/flow-next/skills/flow-next-plan-review/SKILL.md
tags: [fn-78, skill-prose, review-feedback, rp-eligibility, byte-for-byte]
problem_type: integration
symptoms: "Review NEEDS_WORK: ineligible steering still listed rp; eligible wording drifted"
root_cause: Inline conditional annotation on a shared line instead of explicit eligible/ineligible variants
resolution_type: fix
related_to: [bug/integration/rp-builder-file-slices-cause-false-2026-06-10]
---

## Problem
fn-78.1 required rp-proposal surfaces to render byte-for-byte unchanged when eligible (R5) while dropping rp when ineligible. First attempt appended conditional guidance ("when RP_ELIGIBLE=0 drop it...") onto the SHARED Backends summary and at-a-glance rp lines. Cursor impl-review flagged it: the ineligible steering text still led with "RepoPrompt (rp)", and the eligible wording was no longer the pre-change text.

## What Didn't Work
Annotating a single shared line with an inline conditional note. That mutates the eligible rendering (breaks byte-for-byte) AND leaves the suppressed option textually first in the ineligible reading.

## Solution
Branch into explicit variants: an eligible/ineligible pair for the Backends summary (`plugins/flow-next/skills/flow-next-plan-review/SKILL.md:14`), and a separate guard note ABOVE the at-a-glance list with the original rp line restored verbatim (`~:84`). Eligible text is exactly the pre-change wording; ineligible text never mentions rp as an offered option.

## Prevention
When a spec says a default/eligible rendering must stay byte-for-byte, treat every touched line as frozen: write `when FLAG=1: <original text verbatim>` / `when FLAG=0: <variant>` pairs (or a standalone guard note), never inline annotations on the shared line. Verify with `git diff` — original lines must appear only as context or as an exact-restored block.
