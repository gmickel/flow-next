---
title: "Rename smoke rewire: variable-form CLI, hermetic env, R30 guard scope"
date: "2026-05-09"
track: bug
category: test-failures
module: plugins/flow-next/scripts
tags: [fn-43, rename, smoke, migration, review-feedback, env-hermeticity, alias-guard]
problem_type: test-failure
symptoms: "smoke tests pass on clean shell, fail under inherited env; R30 guard misses --epic / EPICS_FILE / variable-form"
root_cause: regex / env-handling / line-level guard scope all assumed too narrow on first pass
resolution_type: fix
---

## Problem
Smoke test rewrite for the fn-43 epic→spec rename surfaced three review cycles of recurring issues:

1. **`$FLOWCTL` variable-form invocations bypass `\bflowctl` regex.** A bulk sed using `\bflowctl epic` matched the bare-binary form (`scripts/flowctl epic`) but missed `"$FLOWCTL" epic` (variable expansion). 9 lines in make-pr_smoke_test.sh slipped through unrewritten.

2. **Hermetic env contracts.** Banner-suppression assertions in migration_smoke.sh inherited the caller's `FLOW_NO_AUTO_MIGRATE` / `FLOW_RALPH` / `REVIEW_RECEIPT_PATH`. Smoke ran green from a clean shell but failed under any of those exports — common in CI / Ralph contexts. `unset VAR; cmd; export VAR=1` only fixed one knob; the other two still suppressed silently.

3. **R30 alias-vocabulary guard scope.** Initial guard caught only `flowctl epic*` verbs. Reviewers found `tasks --epic` / `EPICS_FILE` / `--section epic` references in canonical prose (skill workflow.md, error messages). Widening the regex required matching exclusion regex updates: argparse declarations of the legacy flags themselves (`"--epic-title",` lines) plus task-ref tokens (`T1..T17`) describing rename semantics had to be excluded.

## What Didn't Work
- `\bflowctl epic` regex on bulk sed — assumed all CLI invocations used the bare form.
- Per-test `unset FLOW_NO_AUTO_MIGRATE` toggle — left FLOW_RALPH and REVIEW_RECEIPT_PATH untouched, so banner stayed silent.
- Initial R30 guard scoped to `flowctl epic*` only — missed the `--epic` flag, `--section epic` arg, `EPICS_FILE` env var.

## Solution
- **Variable-form regex**: separate sed pass using `\$FLOWCTL"?\s+epic\s+<subverb>` to catch `"$FLOWCTL" epic create` and similar.
- **`env -u VAR1 -u VAR2 -u VAR3` wrapper**: encapsulate banner-unsuppression as a helper function (`unsuppressed_flowctl`) used by every banner-emit assertion. Hermetic across caller envs.
- **R30 guard widening**: regex covers `flowctl epic|flowctl epics|--epic\b|--epics-file|--section epic|EPICS_FILE`. Exclusions: deprecation/legacy/alias keywords on the SAME line (line-level grep), argparse flag declarations (`^.*:\s+"--(epic|epics-file|epic-title)",?\s*$`), task-rename refs (`\bT[0-9]+\b`).

## Prevention
When implementing rename-style migrations across a CLI test suite:

- **Audit both bare and variable-form CLI invocations.** Scripts often use `"$FLOWCTL" verb` *or* `scripts/flowctl verb` interchangeably; rename regex must catch both.
- **Hermetic env contracts.** When asserting unsuppressed behavior, use `env -u VAR1 -u VAR2 ...` to clear EVERY suppression knob, not just the one you remembered. A single missed knob makes the test pass when caller env happens to be clean and silently fail in CI.
- **Two-tier vocabulary guards have line-level granularity.** Multi-line context (the comment block above a code line) does NOT register; the literal grepped line must contain the exclusion keyword. When adding new alias entry points, immediately add an inline marker comment (`# legacy fallback`, `# alias kept through 1.x`) on the line itself.
- **Argparse legacy alias declarations are the entry points, not fresh prose.** The R30 grep filter must explicitly exclude `"--<flag-name>",` argument-definition lines for the alias flags themselves.
- **Recurring scope creep through review cycles.** Plan for 3-4 review cycles when the rename touches 10+ files; each cycle uncovers a layer the regex missed (variable-form, env-var, flag arg, env hermeticity, exclusion gaps).
