# fn-113-flowctl-judgment-evictions-memory.1 Triage-judge default bump + CLAUDE.md carve-out list

## Description
Triage-judge default bump + the CLAUDE.md sanctioned-carve-out list.

**Size:** M
**Files:** both flowctl.py copies, CLAUDE.md (AGENTS.md symlinks), tests

### Approach

- Read the fn-113 spec eviction item 1 fully (the judge STAYS - retraction recorded; only the default bumps).
- Probe the installed codex CLI for model acceptance BEFORE picking: `codex exec -m gpt-5.6-luna --skip-git-repo-check "say ok" </dev/null` and same for gpt-5.6-terra (foreground, short timeout). Pick per the spec: gpt-5.6-luna@high preferred, gpt-5.6-terra@medium fallback; adjust the default --effort to match the chosen tier. Copilot default claude-haiku-4.5 STAYS. Record which probe succeeded in your summary.
- Bump the codex triage-judge default (locate by symbol near the triage judge, audit line 27054 is stale) + its default effort; --model/--effort overrides unchanged; no new config leaf (fn-115 re-homes as the fastJudge role).
- CLAUDE.md: add a short sanctioned-exception note to the Architecture "How to spot a mistake" section (pattern: the fn-55 carve-out paragraph) naming the licensed subprocess-LLM judgment cases - review-backend dispatch, the triage-skip judge, fn-55 delegation classify - one-line rationale: cross-model verdicts about pipeline-written code must not be self-issued by the host. Purpose: stop future audits from re-flagging sanctioned cases.
- Re-pin any tests asserting the old default model/effort. Dual-copy; sync-codex x2. NO git commands, no flowctl start/done, no em dashes.

### Acceptance

- [ ] Codex triage-judge default = the probe-verified tier with matching effort; copilot default untouched; overrides work
- [ ] CLAUDE.md carries the carve-out list in the named section
- [ ] Focused: python3 scripts/run_tests_parallel.py --pattern "test_gate_classify.py" and any judge-default tests green
- [ ] Dual-copy identical; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
