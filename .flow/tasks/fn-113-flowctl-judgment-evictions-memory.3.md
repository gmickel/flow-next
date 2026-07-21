# fn-113-flowctl-judgment-evictions-memory.3 scope suggest eviction to capture prose contract

## Description
scope suggest eviction: threshold judgment moves to the capture skill contract.

**Size:** S
**Files:** both flowctl.py copies, plugins/flow-next/skills/flow-next-capture/ (workflow.md refs ~915-920,979 - stale line refs, grep for "scope suggest"), tests

### Approach

- Delete the `scope suggest` subcommand (~53 LOC; whole logic is fire = (1 <= n < 3) on agent-supplied counts) + argparse registration.
- Capture skill: fold the threshold into prose - one sentence stating the business-pass suggestion fires when the captured spec names 1-2 distinct scopes (the same 1 <= n < 3 rule), agent-judged. Add/keep a test pinning the constant sentence (pattern: prose-contract tests) so the rule stays stated.
- Prune scope-suggest fire/no-fire test cases (fn-111 deliberately left them; they die here). scope resolve/bank/write-policy UNTOUCHED.
- Dual-copy; sync-codex x2. NO git commands, no em dashes.

### Acceptance

- [ ] scope suggest gone from CLI + argparse; scope resolve/bank/write-policy untouched
- [ ] Capture prose carries the threshold sentence; a test pins it
- [ ] Focused: --pattern "test_skill_prose_diet.py" + scope/capture-related suites green; dual-copy identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
scope suggest deleted (subcommand + argparse + ~53 LOC); the fire threshold lives in capture prose as the R25 rule (fires on 1-2 distinct R24 signal categories - delegate correctly chose signal categories over the task's looser word scopes) in SKILL.md + workflow.md Phase 6, pinned by TestR25ThresholdProseContract (sentence present in both files, no scope-suggest invocation anywhere, inline 1 <= n < 3 branch stated). 13 runtime fire/no-fire tests pruned, 3 prose-contract + re-pinned R22(d) added. scope resolve/bank/write-policy untouched (verified via CLI); optimization/capture/baseline left frozen (eval artifact). CHANGELOG rides task .4's consolidated rider. Full parallel suite 85 files / 1846 tests / 0 failures / 71.4s; dual-copy identical; sync-codex x2.
## Evidence
- Commits: 31d6b732014f47fb16446f716d61f722a531c2f1
- Tests: python3 scripts/run_tests_parallel.py (85 files, 1846 tests, 0 failures, 71.4s), test_capture_biz_routing.py 11 / test_r22_invariant.py 38 / test_skill_prose_diet.py 14 green, CLI verify: scope suggest rejected, resolve/bank/write-policy intact
- PRs: