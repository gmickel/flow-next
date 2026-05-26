---
title: Skill bash `set -- $ARGUMENTS` can't honor 'verbatim' passthrough
date: "2026-05-26"
track: bug
category: build-errors
module: plugins/flow-next/skills/flow-next-map/workflow.md
tags: [fn-50, skill-bash, argument-parsing, set-minus-f, codex-review, passthrough, clawpatch-wrap]
problem_type: build-error
symptoms: Skill docs claimed verbatim shell passthrough but bash word-split corrupts quoted/globbed args; dangling --source crashed under set -e
root_cause: Host hands $ARGUMENTS as a single string — word-split cannot recover shell quoting; case-arm shift past end-of-args trips set -e
resolution_type: fix
related_to: [bug/build-errors/abort-option-copy-must-reflect-pre-2026-05-18, bug/build-errors/fn-44-review-cycle-lessons-2026-05-21]
---

## Problem

When a skill takes user `$ARGUMENTS` and word-splits with `set -- $ARGUMENTS`,
**you cannot claim "verbatim passthrough"** for tokens flowing to a wrapped CLI.
The host already collapsed the user's shell quoting into a single string by the
time the skill sees it — there is no way to reconstruct embedded spaces, quotes,
or shell metacharacters from a flat string.

The first SKILL.md draft for `/flow-next:map` said extras flow "verbatim" to
`clawpatch map` (e.g. `--paths "src/my dir"`). Codex review caught this as a
Major — paths with spaces would split into separate tokens, and globs would
expand against `$PWD` before reaching clawpatch.

Separately: an `unset || crash` trap. With `set -e` and a `case` arm that does
`--source) SOURCE="$2"; shift ;;`, a dangling `--source` (end-of-args) crashes
the skill with a cryptic shell error instead of a clean `exit 2` with a
human-readable diagnostic.

## What Didn't Work

- Documenting "verbatim passthrough" in the skill prose while the bash code
  used `set -- $ARGUMENTS`. The two contradicted each other; review caught it.
- Relying on `case --source) shift ;;` to handle malformed input gracefully.
  Under `set -e`, the missing second argument silently crashes.

## Solution

**Boundary honesty.** Document the real contract: **token-level passthrough
(whitespace-separated, no embedded spaces in args)**. SKILL.md + workflow.md
both carry the same wording. Users needing complex quoting are told to invoke
the wrapped CLI directly.

**Glob protection only.** What we *can* preserve cheaply is glob expansion:
wrap the word-split in `set -f` / `set +f` so `*.py` reaches the wrapped CLI
as a literal string instead of expanding against `$PWD`:

```bash
set -f
# shellcheck disable=SC2086
set -- $ARGUMENTS
set +f
```

**Arg-consumer guards.** Every `case` arm that does `shift` past the current
token MUST check `$# -lt 2 || "$2" == "--"` first:

```bash
--source)
  if [[ $# -lt 2 || "$2" == "--" ]]; then
    echo "Error: --source requires a value (...)" >&2
    exit 2
  fi
  SOURCE="$2"
  shift
  ;;
```

**Smoke tests catch the regression.** Three cases added:
- Dangling `--source` at end-of-args → exits 2 cleanly.
- `--source --` (followed by terminator) → exits 2 cleanly.
- `-- --paths *.py` from a directory with matching files → glob reaches EXTRA
  verbatim AND fixture files (a.py / b.py) do NOT appear in EXTRA (negative
  assert proves `set -f` is effective).

## Prevention

When writing a new skill that wraps an external CLI:

1. **Never claim "verbatim" or "passthrough" in skill prose without auditing
   the bash word-split path.** If you use `set -- $ARGUMENTS`, you cannot
   honor verbatim — say "token-level (whitespace-separated)".
2. **Wrap the word-split in `set -f` / `set +f`** so users can pass globs
   without surprise expansion against `$PWD`.
3. **Every `shift` past current token needs a `$# -lt 2 || "$2" == --` guard
   with `set -e`** — otherwise the skill dies with a cryptic shell error
   instead of `exit 2 + diagnostic`.
4. **Smoke tests for arg parsing must include dangling-flag and glob-in-EXTRA
   cases** — the easy-to-miss failure modes.
