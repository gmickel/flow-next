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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
