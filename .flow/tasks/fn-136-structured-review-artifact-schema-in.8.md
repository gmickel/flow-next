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
Repaired RepoPrompt CE review setup and convergence: durable full review instructions, strict direct-result validation, single-call CE review consumption, context-bound same-chat follow-ups, bounded failure accounting, and an isolated Classic compatibility path. Live RepoPrompt CE 1.1.1 smoke reused numeric window 2, returned context/chat identity plus non-empty prompt/selection and positive file/token evidence, then converged in the same chat to SHIP; receipt: `.flow/review-receipts/impl-fn-136-structured-review-artifact-schema-in.8.json`.
## Evidence
- Commits: 24504991ede36e9c2f9fa3b9917473f1e8dc88f9, c79422b83ed295d0ce043c24784e5ca0a8cf8ac1, d42a03bec3713df5976aefac32c4c4a350dae4f6, c6f54b6e6d3485474e0008ab7e215706cd622704, ccce88aadfa857a1d903585ace1ff23b299ebc20, 2be07360f1a6c75fc4df6cdad437affad65ac060, 2d238e8acb2dbd990761315b0458aee2c42b98a6, 8b35fc33f9d4a7dd9ace791e88e10d22643374c2
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_rp_wrappers test_rp_setup_workflow_contract test_review_convergence_cap.TestRpRecorderFailureFences test_tracker_distribution test_prompt_text_pinned test_backend_spec.TestPlanReviewSelectedBackendRouting.test_tracked_candidate_evidence_matches_live_routes -q (55 passed), uvx ruff@0.16.0 check ., python3 scripts/run_tests_parallel.py (158 files, 3319 tests, 0 failures, 0 errors, 4 skipped), ./scripts/sync-codex.sh (passed twice; 28 skills, 21 agents), flowctl rp setup-review live RepoPrompt CE 1.1.1 smoke (window=2, context_id=0691CA88-A675-4ACA-8AB3-F92D1CA2BD6C, chat_id=fn-136-8-rp-ce-review-re-247D11, file_count=20, total_tokens=68834, prompt_chars=14048, selection_chars=3439, review_chars=8705), flowctl rp chat-send same-chat convergence (context-bound, final verdict SHIP, 0 introduced, 0 pre_existing)
- PRs: