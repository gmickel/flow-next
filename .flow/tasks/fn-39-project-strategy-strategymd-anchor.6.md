# fn-39-project-strategy-strategymd-anchor.6 strategy_smoke_test.sh (T1-T12)

## Description
Author `plugins/flow-next/scripts/strategy_smoke_test.sh` exercising 12 cases (T1-T12) covering happy paths, husk detection, foreign-file refusal, mid-flow abandonment, forbidden-vocab pushback, downstream grounding, and Ralph block. Pure bash + Python (no LLM in the loop), refuses to run from main plugin repo, target <30s runtime.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/strategy_smoke_test.sh` (new)

Depends on Tasks 1-4 (everything with runtime behavior must be authored before tests can exercise it).

## Approach

Clone the structure of `plugins/flow-next/scripts/glossary_smoke_test.sh` (784 lines, 25 cases) — proven scaffold. Same header (refuses to run from main plugin repo), same `TEST_DIR=/tmp/strategy-smoke-$$` convention, same `KEEP_TEST_DIR=1` env opt-in, same `trash` cleanup with `rm` fallback, same `ok` / `fail` / `assert_rc` / `assert_grep` / `assert_no_grep` / `json_get` helpers.

Test cases (mapping back to gap-analyst's T1-T12 + R-IDs from the spec):

**Happy paths:**
- **T1 first-run create-from-scratch:** init empty fixture repo; manually write a populated STRATEGY.md (since the skill itself runs an interview that needs a host LLM, the smoke test simulates the on-disk artifact directly). Assert `flowctl strategy status --json | jq '.exists == true and .husk == false and .sections_filled == 5 and .generator_match == true'`. Validates R1, R6, R23.
- **T2 targeted section re-run preserves rest:** mutate one H2 section's body in-place; re-parse; assert other sections byte-identical via `diff` against original; assert `last_updated` would bump on save (skill tested separately by mid-flow check). Validates R4.
- **T3 subdirectory invocation walks up:** create `apps/web/` subdir; cd there; assert `flowctl strategy status --json | jq '.file_path | endswith("/STRATEGY.md")'` resolves to repo-root path. Validates R7, R16.

**Corner cases:**
- **T4 husk file detected:** write `STRATEGY.md` containing only `# Strategy\n` + frontmatter (no H2 sections); assert `flowctl strategy status --json | jq '.exists == true and .husk == true and .sections_filled == 0'`. Validates R6 husk semantics, R23.
- **T5 foreign-file refusal:** write hand-written STRATEGY.md without `generator: flow-next-strategy` frontmatter; assert `flowctl strategy status --json | jq '.generator_match == false'`. (Skill behavior — interactive refusal — covered by skill-level integration test elsewhere; smoke validates the JSON contract.) Validates R15.
- **T6 mid-flow abandonment + resume:** write STRATEGY.md with 2 of 5 required sections populated, 3 empty; assert `flowctl strategy status --json | jq '.sections_filled == 2'`; assert `flowctl strategy read --json | jq '(.target_problem | length) > 0 and (.approach | length) > 0 and .personas == ""'` (or whichever 2 are populated). Validates per-section atomic-write contract (R4). <!-- Updated by plan-sync: parse_strategy_file returns empty strings ("") for unfilled sections, not null — JSON jq check uses `== ""` not `== null` -->
- **T7 forbidden-vocab pushback** (CI-side, not smoke-side): assert `plugins/flow-next/scripts/ci_test.sh` exits non-zero when test SKILL.md fixture contains `synergy`. Smoke writes a fixture SKILL.md with the bad word, runs ci_test against the fixture's plugin tree, asserts non-zero RC. Validates R19.
- **T8 strategy-glossary conflict surface** (read-side): seed glossary with term "Track" definition; seed STRATEGY.md Tracks section using "Initiative" instead; manually invoke `flowctl strategy read --json` and `flowctl glossary list --json`; verify the JSON contracts allow downstream skill (interview) to detect the mismatch. (Full interview flow tested separately.) Validates R12.
- **T9 capture --override-strategy decision-record schema:** seed STRATEGY.md with active track; assert `flowctl memory add --track knowledge --category decisions --title "Override strategy: <track>" --module strategy --tags strategy-override --body-file -` accepts the input and writes a valid memory entry. Validates R13.
- **T10 prospect grounding emits verbatim approach + tracks:** seed STRATEGY.md with specific approach text; manually run the workflow.md grounding-snapshot bash block; assert output contains the verbatim approach string. (No LLM needed — the snapshot is deterministic.) Validates R10.
- **T11 plan-sync drift surfacing read-only:** assert plan-sync skill prose contains "never auto-supersedes" or equivalent invariant string for STRATEGY.md drift section; verify the agents/plan-sync.md update from Task 4. Validates R14.
- **T12 Ralph block:** in fixture, set `FLOW_RALPH=1`; invoke the slash-command forwarder simulating skill entry (or directly the Phase 0 bash block from SKILL.md); assert exit code 2 + stderr contains `[STRATEGY: user-triggered only`. Validates R17.

**Refuse-to-run-in-main-plugin-repo guard:** at top of script (mirroring `glossary_smoke_test.sh:60-63`), check if `pwd` matches the canonical plugin repo path; exit non-zero with message if so. Forces test runs into a clean fixture.

**Target <30s runtime.** Each test case <2s. Most are deterministic file / JSON checks; no LLM calls. Tests T1-T6, T9-T12 are direct flowctl + JSON assertions. T7 invokes `ci_test.sh` against a fixture (slowest — bound by ci_test runtime). T8 reads two flowctl outputs and asserts both shapes.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/glossary_smoke_test.sh` (full file, 784 lines) — direct template
- `plugins/flow-next/scripts/audit_smoke_test.sh` (528 lines) — secondary reference for assertion patterns
- `plugins/flow-next/scripts/prospect_smoke_test.sh` (756 lines) — pattern for skill-Phase-0 simulation in smoke

**Optional:**
- `plugins/flow-next/scripts/ci_test.sh` — invocation shape for T7 fixture-mode

## Key context

- Smoke tests don't invoke LLMs — they exercise flowctl plumbing + skill bash blocks directly. Skill interview flow (with AskUserQuestion) is not covered here; that's an integration concern.
- T1 simulates what a completed skill run would leave on disk. The on-disk artifact is what downstream skills consume; that's what needs verification.
- Refuse-to-run guard prevents accidentally polluting the main repo with test artifacts. Same pattern in every flow-next smoke.
- `KEEP_TEST_DIR=1` env opt-in keeps fixtures around for debugging. Default cleans up via `trash` (with `rm` fallback per existing flow-next convention).
- Each helper (`ok` / `fail` / `assert_*`) prefixed with case ID (e.g., `T1: ok ...`) for grep-friendly failure output.
## Acceptance
- [ ] `plugins/flow-next/scripts/strategy_smoke_test.sh` created, executable (`chmod +x`), follows the structure of `glossary_smoke_test.sh` (header, TEST_DIR convention, helpers).
- [ ] Refuse-to-run-in-main-plugin-repo guard: top-of-script check exits non-zero if `pwd` matches the canonical plugin repo path. Mirrors `glossary_smoke_test.sh:60-63`.
- [ ] `KEEP_TEST_DIR=1` env opt-in honored. Default cleanup via `trash` with `rm` fallback (per existing flow-next convention).
- [ ] All 12 test cases T1-T12 implemented:
      - T1 first-run on-disk shape (R1, R6, R23): full populated STRATEGY.md → status reports `exists, !husk, sections_filled==5, generator_match`
      - T2 targeted section re-run preservation (R4): byte-identical untouched sections via diff
      - T3 subdir walk-up (R7, R16): `file_path` resolves to repo root from `apps/web/` cwd
      - T4 husk detection (R6, R23): bare H1 + frontmatter → `husk: true, sections_filled: 0`
      - T5 foreign-file refusal contract (R15): missing `generator: flow-next-strategy` → `generator_match: false`
      - T6 mid-flow partial state (R4): 2-of-5 populated → `sections_filled: 2`, populated bodies non-empty, others `""` (empty string, not null) <!-- Updated by plan-sync: empty-string semantics, see T6 description -->
      - T7 forbidden-vocab CI guard (R19): fixture SKILL.md with banned word → `ci_test.sh` non-zero RC
      - T8 strategy/glossary JSON contract (R12): both reads return parseable JSON for downstream conflict detection
      - T9 decision-record schema (R13): `flowctl memory add` with strategy-override tags accepts and writes valid entry
      - T10 prospect grounding determinism (R10): snapshot bash emits verbatim approach string
      - T11 plan-sync read-only invariant (R14): grep `agents/plan-sync.md` for "never auto-supersedes" or equivalent
      - T12 Ralph block (R17): with `FLOW_RALPH=1`, Phase 0 bash exits 2 + stderr contains `[STRATEGY: user-triggered only`
- [ ] Each test case prints `Tn: ok ...` on pass or `Tn: FAIL ...` on failure (grep-friendly).
- [ ] Total runtime <30s on a typical dev machine (T7 is the slowest — bound by `ci_test.sh` startup).
- [ ] Script exits 0 on full pass, non-zero on any failure (sums per-case status).
- [ ] No external network calls. No LLM invocations. All tests deterministic.
- [ ] Smoke runs cleanly after Tasks 1-5 ship: `plugins/flow-next/scripts/strategy_smoke_test.sh` returns 0.
- [ ] No accidental writes outside `$TEST_DIR`. Verified by `git status` post-run reporting clean tree (after `KEEP_TEST_DIR` cleanup).
## Done summary
Authored plugins/flow-next/scripts/strategy_smoke_test.sh (751 LOC) exercising the 12 cases T1-T12 from spec — full populated state, targeted re-run preservation, subdir walk-up, husk detection, foreign-file refusal, mid-flow partial state with empty-string semantics, R19 fluff guard, strategy+glossary JSON contract, decision-record memory add, prospect grounding determinism, plan-sync read-only invariant, and Ralph-block exit-2. Pure shell + Python harness, refuses to run from main plugin repo (mirrors glossary_smoke_test.sh:60-63), KEEP_TEST_DIR=1 opt-in honored, total runtime 4.3s (well under 30s budget). Final smoke results: strategy_smoke_test.sh 56/0, ci_test.sh 57/0, smoke_test.sh 130/0, glossary_smoke_test.sh 80/0 — all four exit 0.
## Evidence
- Commits: d045fbb96428356c6be2d2f4c4c70fa8f4ad30ca
- Tests: cd /tmp && plugins/flow-next/scripts/strategy_smoke_test.sh (56/0 pass, T1-T12 all green, 4.3s, rc=0); cd /tmp && plugins/flow-next/scripts/ci_test.sh (57/0 pass, 10.5s, rc=0); cd /tmp && plugins/flow-next/scripts/smoke_test.sh (130/0 pass, 99s, rc=0); cd /tmp && plugins/flow-next/scripts/glossary_smoke_test.sh (80/0 pass, 6.8s, rc=0); refuse-to-run guard verified (invocation from main plugin repo exits rc=1 with refusal message); KEEP_TEST_DIR=1 verified (leaves /tmp/strategy-smoke-<pid> on disk); hygiene check confirms no STRATEGY.md leaked into plugin tree
- PRs: