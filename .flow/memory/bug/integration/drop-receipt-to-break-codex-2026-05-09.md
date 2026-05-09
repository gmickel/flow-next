---
title: Drop receipt to break codex confabulation in long review fix loops
date: "2026-05-09"
track: bug
category: integration
module: plugins/flow-next/scripts/flowctl.py
tags: [review, codex, confabulation, receipt, fn-43]
problem_type: integration
symptoms: "Codex review keeps surfacing the same finding across multiple cycles, citing line numbers that grep confirms don't exist"
root_cause: Receipt-resumed sessions reinforce the prior turn's hallucinated narrative; subsequent fix cycles cycle through variants of the same false claim instead of dropping it
resolution_type: fix
---

## Problem
fn-43.15 ran 5 codex review cycles. Many cycles had findings that were either (a) plausible-sounding hallucinations citing line numbers / contents that did not exist, or (b) drift between reviewer's mental model and reality (e.g. "Migration guide subsection required" when spec asked for "Two migration paths" + "Optional cleanup" verbatim, or repeated claims that flow-next-capture/SKILL.md and flow-next-make-pr/SKILL.md still had active `flowctl epic create` / `epic export-cognitive-aid` calls when grep + R30 mirror guard reported zero such refs).

## What Didn't Work
Resuming the codex session via `--receipt` for re-reviews. Once the model latched onto a hallucinated narrative ("Codex skill X uses legacy epic surface"), each subsequent NEEDS_WORK fix cycle reinforced rather than dropped the false claim. `--validate` flag did not help — it dropped some but not all variants of the same fabrication.

## Solution
**Drop the receipt path** (`rm -f $RECEIPT_PATH`) before re-running `flowctl codex impl-review`. A fresh thread breaks the confabulation cycle and the reviewer reads the actual diff with no prior-turn context. After 4 receipt-resumed cycles cycling through false positives, one fresh-receipt cycle produced a clean SHIP verdict with zero hallucinated findings.

Side benefit: the fresh-receipt cycle caught a real finding the receipt-resumed cycles missed entirely (CHANGELOG migrate-rename description was inaccurate — said `.flow/epics/<id>.md → .flow/specs/<id>.md` when reality is JSON sidecars only relocate; markdown specs already lived under `.flow/specs/` in 0.x).

## Prevention
1. After 2 consecutive review cycles where the codex reviewer cites the same finding using different file/line citations and grep confirms the cited content does not exist, treat it as confabulation, not a real defect.
2. Drop the receipt and start fresh — `rm -f $RECEIPT_PATH && flowctl codex impl-review ... --receipt $RECEIPT_PATH`.
3. Verify the model's specific line citations (`SKILL.md:N`) before fixing — false-positive findings tend to cite non-existent line numbers or attribute nearby `spec` content as `epic`.
4. The `--validate` flag helps with bounded false positives but doesn't break out of a self-reinforcing narrative. Receipt-reset is the bigger hammer.
