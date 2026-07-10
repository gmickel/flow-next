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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
