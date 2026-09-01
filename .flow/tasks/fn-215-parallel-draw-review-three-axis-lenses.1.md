---
satisfies: [R1, R2, R9, R10, R11, R12, R13]
---
# fn-215-parallel-draw-review-three-axis-lenses.1 flowctl fan-out plumbing: one reservation, three draws, merged receipt

## Description
Inside the codex impl-review pipeline (_backend_impl_review at plugins/flow-next/scripts/flowctl.py:42085+, entry cmd_codex_impl_review:43274): dispatch three concurrent draws on the first round of a scope — each the rendered prompt plus one axis line (correctness-and-logic / contracts-and-consistency / integration-with-unchanged-code), injected via the template layer (references/impl-review-prompt.md + standalone-review-prompt.md gain the axis placeholder; parity constants and SHA pins in test_review_prompt_template_parity + test_prompt_text_pinned update in the SAME commit with rationale). Exactly one enforce_and_increment_review_cap call wraps the fan-out (flowctl.py:42196; standalone still reserves none); artifact hash computed once. Verdict synthesized mechanically worst-wins from the draws' verdict tags (R9). Partial failure fails open per R10; all-fail keeps today's transport-refund semantics. Merged receipt at the existing path keeps top-level schema with primary-draw session_id/model + draws[] array (axis, model, session_id, verdict, failed) per R12 (_backend_review_receipt_payload flowctl.py:41419); per-draw raw outputs persist beside it; per-draw temp paths derive from task id + axis. Re-review rounds (round 2+) resume the primary (correctness) session only, carrying merged prior findings through the existing ratchet grammar (R11) — verify the merged findings container round-trips the per-ordinal grammar (decision entry review-stall-detection-reads-resolution-2026-08-05). Cap counts merged rounds 1:1 (R13). rp/copilot/cursor paths untouched. Behavioral tests: new test_review_fanout suite (one-reservation, worst-wins, partial-fail-open, all-fail refund, draws[] schema, round-2 single-resume) + extend test_review_receipt_schema + test_review_convergence_cap. Run gen_tracker_manifest.py; sync-codex twice.

## Acceptance
R1 (dispatch mechanics), R2, R9, R10, R11, R12, R13 satisfied at the flowctl layer; judge against the parent spec's criteria directly. Quick suites green including the updated pins with rationale in the commit message; test_two_axis_audit_contract untouched and green.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
