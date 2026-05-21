---
title: "Smoke discipline: variable-form CLI, hermetic env, line-level guard scope"
date: "2026-05-09"
track: bug
category: test-failures
module: "plugins/flow-next/scripts"
tags: [smoke, env-hermeticity, variable-form-cli, line-level-guard, review-feedback]
problem_type: test-failure
symptoms: "Smoke tests pass on clean shell, fail under inherited env; rename / deprecation guards miss variable-form CLI invocations + flag args + env-var spellings"
root_cause: "Regex / env-handling / line-level guard scope all assumed too narrow on first pass — variable-form CLI not matched, env-suppression knobs not all unset, multi-line context not respected by line-level grep"
resolution_type: fix
audit_refocused_from: "fn-43 epic→spec rename smoke rewrite; refocused 2026-05-21 to extract reusable smoke-test discipline"
---

## Lesson 1 — Audit BOTH bare and variable-form CLI invocations

Scripts mix forms interchangeably:
- `scripts/flowctl verb …` (bare-binary form)
- `"$FLOWCTL" verb …` (variable expansion)

A `\bflowctl\b` regex catches the first; misses the second. Any rename / deprecation sweep must run TWO passes:

```bash
# Pass 1 — bare form
grep -rE '\bflowctl\s+<verb>\b' …
# Pass 2 — variable form
grep -rE '\$FLOWCTL"?\s+<verb>\b' …
```

Same applies to deprecation guards: the R30-style alias-vocabulary guard must match both forms or it underreports.

## Lesson 2 — Hermetic env contracts

When a smoke test asserts behavior that env vars can suppress (deprecation banners, auto-migrate prompts, Ralph blocking, receipt detection), use `env -u VAR1 -u VAR2 -u VAR3` to unset EVERY suppression knob — not just the one you remembered:

```bash
unsuppressed_flowctl() {
  env -u FLOW_NO_AUTO_MIGRATE -u FLOW_NO_DEPRECATION -u FLOW_RALPH \
      -u REVIEW_RECEIPT_PATH "$FLOWCTL" "$@"
}
```

A single missed suppression knob makes the test pass when the caller's env happens to be clean (local dev) and silently fail in CI / Ralph contexts where the knob IS exported. Wrap all banner-emit assertions in the helper.

## Lesson 3 — Line-level guard scope

`grep`-based deprecation / vocabulary guards operate one line at a time. Multi-line context (a `# legacy alias` comment ABOVE a code line) does NOT exempt the next line. When adding new alias entry points or intentional uses of deprecated tokens, add the marker comment ON the line itself:

```bash
"$FLOWCTL" epic create "$title"  # legacy alias kept through 1.x; remove in 2.0
```

Exclusions to add to any vocabulary-guard regex:
- Argparse declarations of the deprecated flags themselves: `"--<flag>",` lines.
- Task-rename refs that mention the deprecated token in prose: `\bT[0-9]+\b` or equivalent.
- Inline-marker comments: `legacy`, `alias`, `deprecated` on the same line.

## Lesson 4 — Plan for review-cycle scope creep

Rename / deprecation migrations touching 10+ files typically take 3-4 review cycles. Each cycle uncovers a layer the regex missed:
1. Bare CLI form rewritten; variable form still leaks.
2. Variable form caught; env-var spelling (`EPICS_FILE` / `EPIC_ID`) still leaks.
3. Env-var caught; argparse flag declaration still trips the guard.
4. Flag declaration excluded; prose task-references trip the guard.

Plan for this. Each cycle is normal; the recurrence is the signal that you've found another scope corner, not a sign of bad work.

## See also

- `[[fn-44-review-cycle-lessons]]` — same era + scope-creep pattern
- `[[test-production-path-not-parallel-construction]]` — related test-discipline lessons (test the production wire form, not the workaround)
- `plugins/flow-next/scripts/smoke_test.sh` — exemplar smoke test using the `env -u` hermetic pattern
