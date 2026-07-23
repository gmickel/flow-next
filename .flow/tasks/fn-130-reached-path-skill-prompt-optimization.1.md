---
satisfies: [R1, R2, R11]
---
# fn-130-reached-path-skill-prompt-optimization.1 Build reached-path trace and fixture foundation

## Description
Create the shared production-path measurement and autoresearch substrate used by every later mutation. Record current-main baseline `B0` before canonical skill edits. The harness must prove which direct references are required or cold on a fixture path; deterministic source/reached-path size and backend telemetry remain separate.

**Size:** M
**Files:** `optimization/reached-path/**`, `agent_docs/optimizing-skills.md`, `agent_docs/optimization-log.md`, focused test fixtures under `plugins/flow-next/tests/fixtures/` when production-path assertions belong in CI.

### Reached-path character algorithm
- Normalize every counted prompt file to LF before counting Unicode characters.
- Count the complete root `SKILL.md` exactly once.
- Count the complete content of each successfully reached direct reference exactly once, deduplicated by normalized repo-relative path plus content hash. If the host reports a range/subset read, count the complete referenced file once because reference activation—not tool span size—is the measured contract.
- Exclude failed reads, repeated reads, catalog metadata, tool output, and host-injected text.
- For Codex fixtures, count the actual regenerated mirror files, not canonical proxies.
- Retain raw trace spans separately from the deterministic character calculation.

### Approach
- Extend the current optimization methodology and `optimization/worker-anchor/` comprehension-equivalence shape rather than inventing another prompt-scoring framework.
- Freeze route manifests before mutations for Version, Setup, Tracker Sync, Prime, Plan Review, Plan, Work, Strategy, Make PR, and Pilot.
- Capture required/forbidden direct reads, output/tool/write/receipt oracles, hashes, host/model/CLI provenance, normalized reached-path characters and chars/4, and backend token/cache/time telemetry as separate fields.
- Preserve authenticated Claude OAuth isolation using project/local setting sources; zero-token auth failures are invalid runs.
- Add privacy scrubs, filesystem diff, out-of-arena sentinel, instruction-leak probe, and explicit no-live-tracker boundary.
- Record explicit structural deferrals for the non-target skills and the current baseline commit.
- Produce immutable `B0`: original-main fixture inputs, file hashes, traces, metrics, oracles, and results. Task 130.2 will derive the fleet-wide version-adjusted structural baseline `V1/B1`; later structural tasks compare only against hash-verified `B1`.

### Fixture inventory
- Version: match, interactive mismatch, autonomous mismatch, missing setup, missing plugin version, plugin mode, unavailable jq.
- Setup: copy/plugin/autonomous and five-host route states.
- Tracker: inactive plus Linear/GitHub/GitLab/Jira selectors and malformed state.
- Prime: classify/report/full/fix route states plus the existing seven topology fixtures.
- Plan Review: none/export/host/codex/copilot/cursor/RP/unavailable.
- Plan, Work, Strategy, Make PR, Pilot: every optional or mutually exclusive branch named in the parent spec.

### Investigation targets
**Required**
- `agent_docs/optimizing-skills.md:42-157` — baseline, ratchet, real-backend, accuracy, and override contracts.
- `agent_docs/optimizing-skills.md:219-243` — current reached-path/progressive-disclosure doctrine.
- `optimization/worker-anchor/README.md` — deterministic superset plus comprehension proof pattern.
- `optimization/review-prompt/README.md` — real-engine risky/clean corpus pattern.
- `optimization/prime/run_agentic_eval.py` — isolation/provenance harness with the current OAuth failure mode.

**Optional**
- `.flow/specs/fn-54-eval-driven-prompt-optimization-for.md` and fn-84/fn-85 — ancestor constraints.
- `plugins/flow-next/tests/test_token_budgets.py` — chars/4 terminology.

## Acceptance
- [ ] `optimization/reached-path/README.md` freezes the LF-normalized, full-file-on-activation, once-per-path/hash character algorithm; defines production-path tracing, required/forbidden reads, provenance, metric separation, ratchet, privacy, and resume procedure.
- [ ] Sanitized frozen `B0` manifests exist for every cluster before canonical prompt mutation; fixtures never expose answer-key conclusions to the subject.
- [ ] At least one production-path Claude run proves an active direct-reference read and a cold-reference non-read; auth and instruction-leak probes pass.
- [ ] Borderline/subjective run-count rules and sealed-holdout policy are encoded; a flat or noisy result cannot be labeled keep.
- [ ] Current non-target skills and open-spec overlap risks are recorded as explicit deferrals, not silently omitted.
- [ ] Focused harness self-tests pass. Eval execution produces no unplanned side effects outside disposable arena/result paths; declared `optimization/**`, `agent_docs/**`, and focused test changes are allowed and reviewed.

## Done summary
Built and hardened the reached-path optimization foundation: deterministic full-file activation accounting, 117 hash-frozen B0 branch manifests, commit-sourced reproducible bootstrap, immutable production proof plus candidate reruns, privacy/isolation/auth controls, and a retained Claude production trace proving the active reference was read while the cold reference remained absent. Backend nonzero exits, missing CLI, auth/leak failures, timeouts, and tool-result failures now fail closed and retain only candidate evidence.
## Evidence
- Commits: 46e4e3d62d9d6403fd6600f37d64b2e4169e05e9, e4420bb916bec7cba6f13543d859dd4684d42838, e4459d96791a715e192cd0df1f96fb16781535d4, 30cbc59fc51b514d5fd883141d673c7c1d9135d0, b45a3613
- Tests: python3 -m unittest -q test_reached_path_harness (35 passed), focused fn-130 suite (581 passed), python3 optimization/reached-path/run_eval.py --self-test (passed), python3 optimization/reached-path/run_eval.py --validate-b0 (117 manifests passed), python3 optimization/reached-path/run_eval.py --all --backend claude (candidate PASS: rc=0, active read true, cold read absent), tracked B0 SHA unchanged across candidate run, git diff --check (passed)
- PRs: