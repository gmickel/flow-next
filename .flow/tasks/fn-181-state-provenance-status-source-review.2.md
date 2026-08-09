---
satisfies: [R2]
---
# fn-181-state-provenance-status-source-review.2 Review-skill prose: committed task status is not authoritative

## Description
Spec fn-181 item 2 (#304 half 2, the load-bearing half). Plan-review + completion-review prose: committed .flow/tasks/<id>.json status is not authoritative; lifecycle lives in git-common-dir flow-state (unreachable from a diff-scoped sandbox); task lifecycle is not the reviewer's to judge (completion review = spec compliance only). One to two sentences per skill (fn-82 budget). sync-codex twice.

Post-capture (3.19-3.21, see spec Edge Cases): routers no longer carry judgment prose; land the sentences in references/plan-review-prompt.md + references/completion-review-prompt.md. Both are SHA-pinned (test_prompt_text_pinned) and byte-mirrored as FALLBACK constants in flowctl.py (test_review_prompt_template_parity): update hash pins + fallback parity + dual copies + codex mirror, and state the prompt rationale in the commit message. Conduct checklists: agent_docs/conduct/plan-review.md + spec-completion-review.md.

**Files:** plugins/flow-next/skills/flow-next-plan-review/references/plan-review-prompt.md + plugins/flow-next/skills/flow-next-spec-completion-review/references/completion-review-prompt.md + flowctl.py FALLBACK constants (byte parity) + tests/test_prompt_text_pinned.py hash pins + dual copy + codex mirror regen

## Acceptance
R2 of the spec. Occurrence-3 shape (sidecar read while flow-state says done) is ruled out by prose a skill-following reviewer cannot miss.

## Done summary
Both shared review prompt templates (plan-review, completion-review) now bar reviewers from judging task lifecycle from committed sidecars: status fields named as snapshots, authoritative state located in git-common-dir flow-state (unreachable from a diff-scoped context), read-for-content-never-for-status. Landed inside each template's verdict-scope framing. Byte parity with both flowctl FALLBACK constants, 4 hash pins + 4 rendered fixtures rebaselined, codex mirror regenerated, prompt rationale in commit message.
## Evidence
- Commits: 7970ef64
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_review_prompt_constraints test_review_prompt_template_parity -q
- PRs: