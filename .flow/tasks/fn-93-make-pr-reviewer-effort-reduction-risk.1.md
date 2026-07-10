## Description
Size: S. Pure prose in `plugins/flow-next/skills/flow-next-make-pr/workflow.md` (Phase 2). Implement spec R1-R3 EXACTLY as the epic's Architecture §1-4 defines — the contract is eval-validated verbatim (prbeval V4, 9/9/9/9); do not re-derive wording, adapt it.
## Approach
1. §2.0 order list: insert `How to review this PR` after Critical changes; replace `Where to look` entry with `Review plan`.
2. New §2.5a: the How-to-review contract (mechanically-verified summary from tasks[].evidence + review_receipts + R-ID coverage; honest-absence rule; "your job" framing; ≤ ~8 lines).
3. Rewrite the Where-to-look section (§2.5 area) into the Review plan contract: three buckets, WHY + what-to-check + symbol anchor per must-review item, focus budget ≤ ~30% with explicit carve-outs, bucket percentages, derived-file rule (always safe-to-skim, derivation named; consume fn-86 `derived`/`changed_symbols` fields opportunistically when present, degrade gracefully).
4. Hallucination guardrails section: extend with "no invented risk claims; WHY traces to payload".
5. Tiny-PR collapse rule (< ~100 lines: single honest bucket).
## Acceptance
- [ ] R1-R3 rendered per epic contract; section order updated; smoke prose contracts assert the two new section names + absence of `## Where to look`.
- [ ] Mirror regenerated + guard green. No flowctl changes.

## Done summary
Rewrote the make-pr render contract (workflow.md Phase 2) per the epic's eval-validated Architecture §1-4: added the `## How to review this PR` trust-calibration coaching block (§2.4c — mechanically-verified summary, no-overclaim/honest-absence rule, "your job" framing) and replaced both the four-bucket Review plan and the standalone `## Where to look` section with a risk-ranked three-bucket `## Review plan` (§2.4d — Must review ~X% / Spot-check / Safe to skim, per-item WHY + what-to-check + symbol anchor, ≤~30% focus budget with explicit carve-outs, derived-file rule, tiny-PR collapse). Extended hallucination guardrails with rule 11 (no invented risk claims — every WHY traces to payload data), updated all in-skill references (§2.0 order, §2.4b, omission tables, SKILL.md, phases.md, create-and-finalize.md), updated the smoke prose contracts, and regenerated the Codex mirror (guards green).
## Evidence
- Commits: 27412f07827b827f6254a1cabe15da11ca990120
- Tests: baseline: green (full unittest at base 80a595c7 — Ran 1556, OK, skipped=2), python3 -m unittest discover -s plugins/flow-next/tests (from outside repo) — Ran 1556, 0 failures on edited tree (first run had 4 flaky failures; identical rerun + base-commit baseline both OK — inherited flakiness, zero .py files touched), bash plugins/flow-next/scripts/smoke_test.sh (from outside repo) — 144 passed, 0 failed, bash plugins/flow-next/scripts/make-pr_smoke_test.sh (from outside repo) — 79 passed, 0 failed incl. new T10 prose contracts ('## How to review this PR' + '## Review plan' present, '## Where to look' absent), scripts/sync-codex.sh — mirror regenerated, all structural guards green; new §2.4c/§2.4d blocks byte-identical in mirror
- PRs: