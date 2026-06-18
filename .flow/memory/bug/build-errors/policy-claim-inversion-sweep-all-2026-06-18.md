---
title: "Policy-claim inversion: sweep ALL surfaces (both ceremony copies, docs, CLI head"
date: "2026-06-18"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-tracker-sync/steps.md
tags: [fn-66, tracker-sync, ceremony-duplicate, dispatch-grammar, docs-parity, steps.md, SKILL.md]
problem_type: build-error
symptoms: 3 NEEDS_WORK rounds — each surfaced the next un-updated duplicate of an inverted policy claim (completionReview/land.merged Done ownership)
root_cause: "discovery ceremony + 'owns Done' prose duplicated across SKILL.md, steps.md, 3 docs pages, github.md, and flowctl.py header; first pass touched only the primary site"
resolution_type: fix
related_to: [bug/build-errors/id-grammar-widening-must-cover-the-full-2026-06-03, bug/build-errors/status-policy-map-needs-a-matching-2026-06-18]
---

## Problem
Re-scoping the tracker-sync lifecycle touchpoints (fn-66.2) took three NEEDS_WORK rounds because a policy claim ("completionReview flips Done/verified", "the one exception is make-pr") was duplicated across MORE surfaces than the first edit pass touched. The discovery ceremony exists in TWO places (`flow-next-tracker-sync/SKILL.md:87-94` AND `steps.md:49-60`); the stale "owns Done" / "one exception" prose also lived in `docs/teams.md`, `docs/flowctl.md`, `references/github.md`, and the `flowctl.py` activation header. Each review round surfaced the next un-updated copy.

## What Didn't Work
Editing the "primary" site (SKILL.md ceremony + the three touchpoint files) and assuming the policy was now consistent. The reviewer kept (correctly) citing a stale duplicate — most notably `steps.md`'s second copy of the ceremony, which I'd missed entirely.

## Solution
- Grep the ENTIRE skill + docs tree for the policy claim's keywords BEFORE the first review, not after: `grep -rn "flip Done\|owns the Done\|one exception\|completionReview reconcile\|enabled=true does nothing"` across `skills/`, `docs/`, and `scripts/flowctl.py`.
- The discovery ceremony is mirrored in `SKILL.md` AND `steps.md` — any ceremony-seed or activation-exception change must touch BOTH.
- Lifecycle dispatch grammar must stay canonical `operation: <verb> <id>, event: <key>` — descriptors like "(In Review)", "+ link $PR_URL", "verdict + R-ID coverage" belong in surrounding prose, NEVER inside the operation token (memory mirror-regen-exposes-latent-canonical). Both the touchpoint dispatch AND its retro-fire copy carry the grammar.

## Prevention
- When inverting a policy claim, treat it as a repo-wide string sweep: enumerate every surface (canonical skills, both ceremony copies, all docs pages, the CLI header comment) before sending to review.
- A dispatch-grammar change needs a grep for the op token across the touchpoint file's main path AND its end-of-run retro-fire path.
