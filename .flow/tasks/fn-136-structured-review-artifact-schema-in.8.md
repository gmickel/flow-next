# fn-136-structured-review-artifact-schema-in.8 Repair and live-smoke RepoPrompt CE review setup

## Description
Repair the RepoPrompt CE implementation-review setup failure discovered while reviewing fn-136.1.

The canonical RP workflow carries `REVIEW_SUMMARY` across conceptual phases without a durable handoff, so fresh-shell hosts can invoke `flowctl rp setup-review` with an empty summary. The wrapper currently accepts that input and treats a returned window/tab identifier as success even when Context Builder leaves an empty prompt and selection.

Implement the smallest root-cause fix:

- make the atomic setup block self-contained or use a durable summary handoff;
- reject blank setup summaries deterministically;
- verify the builder produced usable context before reporting setup success, without introducing a duplicate/retry path;
- add focused regressions and update canonical documentation/Unreleased notes where behavior changed;
- propagate `flowctl.py` to the dogfood copy, regenerate the tracker manifest, and run `scripts/sync-codex.sh` twice.

Run a live RepoPrompt CE 1.1.0 smoke step by step against this branch. It must prove the CE-first executable wins, the same numeric window is reused, task instructions reach Context Builder, the resulting selection and prompt are non-empty, changed files can be augmented, chat/review returns a session/verdict, and the receipt path is written. One deliberate live builder run only after focused tests are green; do not retry a slow command.

## Acceptance
- [ ] Fresh-shell execution cannot lose `REVIEW_SUMMARY`; the atomic RP setup receives substantive task instructions.
- [ ] `flowctl rp setup-review` rejects blank/whitespace-only summaries and does not report success for unusable empty builder state.
- [ ] Focused tests cover the previously false-green context-id-only case and the self-contained canonical/Codex workflow contract.
- [ ] Live CE smoke proves executable choice, window reuse, non-empty builder instructions/selection/prompt, augmentation, review/chat session, and receipt.
- [ ] Canonical flowctl, dogfood copy, tracker manifest, Codex mirror, docs, and `## Unreleased` entry remain synchronized; no version bump.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
