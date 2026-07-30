# fn-136-structured-review-artifact-schema-in.8 Repair and live-smoke RepoPrompt CE review setup

## Description
Repair the RepoPrompt CE implementation-review setup failure discovered while reviewing fn-136.1.

Initial diagnosis found two Flow defects:

- canonical RP workflows carried `REVIEW_SUMMARY` across conceptual phases without a durable handoff, so fresh-shell hosts could invoke setup with an empty summary;
- `flowctl rp setup-review` treated a returned context identifier as success without validating usable context.

Live semantic smoke plus RepoPrompt CE source inspection exposed the deeper compatibility boundary. Community Edition executes `context_builder` as a headless MCP tool owned by the CLI connection. For explicitly targeted/inactive workspaces it intentionally runs without visible compose-tab projection. Its direct tool result is authoritative and includes `context_id`, rewritten `prompt`, formatted `selection`, token/file counts, and—when `response_type=review`—the review reply/chat identity. The old Classic workflow instead expected builder state to be published into a visible tab, then augmented selection and sent a second chat.

Implement the smallest correct split:

- make every RP setup block self-contained so substantive instructions cannot be lost across tool calls;
- reject blank setup summaries deterministically;
- for RepoPrompt CE, invoke the named `context_builder` tool with `response_type=review`, validate and consume its direct result, and write the normal Flow review receipt without requiring visible-tab projection or a second model call;
- retain the discontinued Classic tab/selection/chat path only as the final compatibility fallback;
- never mix CE direct-result state with Classic tab state;
- add exact CE-schema and Classic-compatibility tests based on RepoPrompt CE source commit `d42c2e30`;
- update canonical docs/Unreleased notes and every canonical/Codex RP review workflow;
- propagate `flowctl.py` to `.flow/bin`, regenerate the tracker manifest, and run `scripts/sync-codex.sh` twice.

Run one final live RepoPrompt CE 1.1.0 smoke after focused/full tests and Ruff are green. It must visibly appear in MCP Server Status as CLI-owned `context_builder`, reuse window 10, return a non-empty direct prompt and selection with file/token counts, return a review verdict/chat identity, and write a valid Flow receipt. A visible compose tab is not required in CE and must not be used as the success oracle. Do not retry an unchanged slow command.
## Acceptance
- [ ] Fresh-shell execution cannot lose the substantive review summary; blank/whitespace-only setup input fails before any RepoPrompt call.
- [ ] CE uses the named `context_builder` MCP tool with `response_type=review` and validates the authoritative direct result: non-empty prompt, non-empty formatted selection, positive file/token evidence, context/chat identity, and terminal review response.
- [ ] CE review consumes that single direct result and writes the standard Flow review receipt; it does not require visible-tab projection, selection augmentation, or a second chat/model call.
- [ ] Classic remains an isolated final compatibility fallback using its published-tab selection/chat workflow; CE failures never downgrade to Classic.
- [ ] Focused tests model the exact CE direct-result schema from upstream source commit `d42c2e30`, cover empty/malformed direct results, and cover the self-contained canonical/Codex workflow contract plus Classic behavior.
- [ ] Live CE smoke is visible in MCP Server Status and proves resolver choice, numeric window reuse, direct prompt/selection/file/token evidence, review verdict/chat identity, and receipt.
- [ ] Full Python gate, Ruff 0.16.0, dogfood distribution, tracker manifest, Codex mirror twice, docs, and `## Unreleased` entry are synchronized; no version bump.
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
