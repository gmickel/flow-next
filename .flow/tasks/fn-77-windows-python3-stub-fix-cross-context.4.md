---
satisfies: [R1, R5, R6]
---

## Description
Sweep the remaining bare-`python3` sites and de-duplicate the 12 `pick_python` copies. Because task .1 makes the resolver fill a bash **array** `FLOW_PY`, this task must convert every scalar interpreter call in the consumers — sourcing the helper alone is NOT enough (plan-review Major). Site classes:
1. **12 `pick_python` copies** (11 smoke/CI scripts + runtime `ralph.sh`) → source `scripts/lib/pick-python.sh` AND convert every `"$PYTHON_BIN"` call-site to `"${FLOW_PY[@]}"`.
2. **Direct-shebang `.py` by path** → invoke through a resolved interpreter via a committed bash wrapper: `hooks.json` (5 sites → `ralph-guard.py`) + `ralph.sh` (4 pipe sites → `watch-filter.py`).
3. **Agent-run heredocs** in qa/prospect workflow.md → resolve `$PY` once, `$PY - <<'PY'`.
Then regenerate the Codex mirror via `sync-codex.sh`.

**Size:** M/L (mechanical but broad — many call-site conversions)
**Files:** 11 `plugins/flow-next/scripts/*_smoke*.sh`/`ci_test.sh`, `.../templates/ralph.sh`, `plugins/flow-next/hooks/hooks.json`, `plugins/flow-next/scripts/hooks/ralph-guard` (new bash wrapper) + its `scripts/ralph/hooks/` copy, `flow-next-qa/workflow.md`, `flow-next-prospect/workflow.md`, `plugins/flow-next/codex/**` (generated)

## Approach
- **Scalar→array conversion (plan-review Major):** in each of the 12 consumers, replace the `pick_python` def+assign with `source "$SCRIPT_DIR/lib/pick-python.sh"`, then rewrite EVERY interpreter invocation from `"$PYTHON_BIN"` (scalar — expands only element 0, drops `-3`) to `"${FLOW_PY[@]}"`. `set -u`-safe. Confirm relative path resolves from `scripts/` and `templates/`.
- **ralph.sh child wrapper (plan-review Major):** `ensure_flowctl_wrapper()` currently generates `PY="${PYTHON_BIN:-python3}"; exec "$PY" …` — a scalar that drops `-3`. Regenerate it to SOURCE the resolver (copied into `scripts/ralph/` by task .2) and `exec "${FLOW_PY[@]}" …`. Same for the 4 `watch-filter.py` pipes: `"${FLOW_PY[@]}" "$SCRIPT_DIR/watch-filter.py"`.
- **hooks.json needs a bash wrapper (plan-review Major):** hook command strings may run under `/bin/sh` (no arrays/`source`) or native Windows — inline `source`+array in JSON is unsafe. Add a committed **`scripts/ralph/hooks/ralph-guard`** (bash shebang; sources `../pick-python.sh`; `exec "${FLOW_PY[@]}" "$(dirname "$0")/ralph-guard.py" "$@"`), copied by ralph-init. Change the 5 `hooks.json` invocations (lines 10/20/32/43/54) from `… || scripts/ralph/hooks/ralph-guard.py` to call the wrapper (or `bash scripts/ralph/hooks/ralph-guard`). Keep `ralph-guard.py`'s POSIX shebang but don't rely on it on Windows. **Wrapper resolver-path (plan-review Minor):** the wrapper must locate `pick-python.sh` in BOTH layouts — the canonical source (`plugins/flow-next/scripts/hooks/` → `../lib/pick-python.sh`) and the installed copy (`scripts/ralph/hooks/` → `../pick-python.sh`) — via a two-path fallback; tests exercise the INSTALLED layout.
- **heredocs:** qa:521, prospect:63/490/740 — resolve `$PY` once per bash block; update `:16`/`:485` prose.
- **Orphan `.sh` hooks** (`ralph-guard.sh:9`, `ralph-receipt-guard.sh:17`, `ralph-verbose-log.sh:21`): ZERO runtime refs — delete if dead, else fix. Record the decision.
- Run `scripts/sync-codex.sh`; commit the regenerated mirror.

## Investigation targets
**Required:**
- repo-scout's 12-copy table (def+assign): `smoke_test.sh:22/31`, `ci_test.sh:10/19`, `alias_smoke.sh:47/56`, `migration_smoke.sh:48/57`, `ralph_smoke_test.sh:14/23`, `make-pr_smoke_test.sh:64/73`, `audit_smoke_test.sh:33/42`, `glossary_smoke_test.sh:61/70`, `impl-review_smoke_test.sh:17/26`, `prospect_smoke_test.sh:44/53`, `strategy_smoke_test.sh:65/74`, `ralph.sh:14/23`
- **each consumer's `"$PYTHON_BIN"` CALL-sites** (not just the def) — grep `"$PYTHON_BIN"` per file to convert to `"${FLOW_PY[@]}"`
- `plugins/flow-next/hooks/hooks.json:10,20,32,43,54` + `plugins/flow-next/scripts/hooks/ralph-guard.py:1`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:57-72` (wrapper) + `:1096,1098,1107,1109` (pipes) + `:25`
- `flow-next-qa/workflow.md:521,485` · `flow-next-prospect/workflow.md:63,490,740,16`
- `plugins/flow-next/scripts/sync-codex.sh`

## Acceptance
- [ ] All 12 consumers source `scripts/lib/pick-python.sh` AND every `"$PYTHON_BIN"` call-site is converted to `"${FLOW_PY[@]}"`; each passes `set -euo pipefail`, runs green on mac/linux, AND passes under a forced fake `py -3` resolution (proves the array conversion, not just the source)
- [ ] `ralph.sh`'s generated child wrapper sources the resolver and execs `"${FLOW_PY[@]}"` (no scalar `${PYTHON_BIN:-python3}` that drops `-3`); the 4 `watch-filter.py` pipes use `"${FLOW_PY[@]}"`
- [ ] A committed bash wrapper `scripts/ralph/hooks/ralph-guard` invokes `ralph-guard.py` via the resolver; `hooks.json`'s 5 sites call the wrapper (bash-guaranteed), not the bare `.py`; it resolves `pick-python.sh` in both source-tree and installed layouts (two-path fallback), is copied into installed `scripts/ralph/hooks/`, and fires on a stub-configured Windows box (tests exercise the installed layout)
- [ ] qa + prospect heredocs resolve `$PY` once; no bare `python3 -` remains in either workflow.md
- [ ] The 3 orphan `.sh` hooks are fixed or removed (decision recorded)
- [ ] `sync-codex.sh` re-run; codex mirror reflects changes (no hand-edits)
- [ ] A targeted grep for EXECUTABLE `python3` invocations (line-start / after `|`/`(`/`$(`; excluding prose, comments, `#!` shebangs, prereq text) finds no unfixed site in the canonical tree

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
