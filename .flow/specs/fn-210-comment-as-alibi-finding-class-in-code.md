# Comment-as-alibi finding class in code review prompts

## Goal & Context

The worker's authoring rule "Comments are not alibis" (agents/worker.md, shipped 4.8.0) forbids comments that exist to justify a workaround: fix the code, or encode the constraint as an assert/test/lint rule, then delete the prose. Nothing on the review side checks it — the impl-review and standalone-review prompts never name the pattern, so a workaround wearing a paragraph-long justification sails through review as "well documented." The authoring agent is the wrong enforcement point for its own comments; the fresh-context reviewer is the right one.

This spec adds the reviewer half: a named **comment-as-alibi** finding class in the impl-review and standalone-review prompts. The reviewer treats a justifying comment as a flag on the underlying code — the workaround is the finding, the comment is the signal. The keep-list is shared verbatim with the worker rule so author and reviewer never disagree about which comments are licensed.

## Edge Cases & Constraints

- The finding's severity is judged from the workaround, not the prose. A fix that rewrites or deletes the comment while keeping the workaround does not resolve the finding.
- Licensed comments are never flagged: license headers, external-constraint notes, lint suppressions with reasons, public API contracts, issue links (the worker rule's keep-list, verbatim).
- Prompt constants and their on-disk templates stay byte-identical (fn-112.3); this is a deliberate prompt change, so hash pins and rendered fixtures update in the same commit with the rationale in the message.

## Acceptance Criteria

- **R1:** The impl-review prompt (constant + template) names comment-as-alibi as a finding class: a comment that exists to justify a workaround or narrate around a hack flags the underlying code for review; severity is judged from the workaround, not the comment; rewriting or deleting the comment alone does not resolve the finding. The keep-list (license headers, external-constraint notes, lint suppressions with reasons, public API contracts, issue links) is stated so licensed comments are never flagged. No error surface beyond the review verdict itself.
- **R2:** The standalone-review prompt (constant + template) carries the same finding class with the identical keep-list.
- **R3:** Prompt-integrity guards stay green through the change: constant/template byte-parity holds, `test_prompt_text_pinned.py` pins and the rendered-prompt fixtures are updated in the same commit, and the codex mirror is regenerated idempotently.
- **R4:** The repo `CHANGELOG.md` gains an `## Unreleased` entry describing the finding class user-outcome-first.

## Boundaries

- No new skill, agent, or sticky comment-review overlay.
- No `.flow/criteria.md` G-ID.
- No change to the worker's authoring rule (already shipped) beyond keeping the keep-list identical.
- Plan-review and completion-review prompts untouched — they judge plans and coverage, not diff hunks.
- No version bump in this change (batched release rule).

## Decision Context

- Enforcement lives in the review rubric, not a dedicated skill: a separate always-on comment pass costs context on every run, and the authoring agent defending its own comments is the failure mode this closes.
- The keep-list is copied verbatim from the worker rule rather than referenced, because the prompts are self-contained payloads sent to external reviewer models that cannot follow a repo pointer.
- Scope is the two diff-reviewing prompts only; widening to completion review was considered and rejected (it verifies requirement coverage, not code quality).

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_review_prompt_template_parity -q
```
