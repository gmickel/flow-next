---
satisfies: [R1, R5, R6]
---

## Description
Sweep the remaining bare-`python3` sites and de-duplicate the 12 `pick_python` copies. Because task .1 makes the resolver fill a bash **array** `FLOW_PY`, this task converts every scalar interpreter call — sourcing alone is NOT enough (plan-review Major). Site classes:
1. **11 plugin-tree `pick_python` copies** (smoke/CI scripts) → source `scripts/lib/pick-python.sh` AND convert every `"$PYTHON_BIN"` call-site to `"${FLOW_PY[@]}"`.
2. **`ralph.sh` (the 12th copy) is SPECIAL** — it runs from the INSTALLED `scripts/ralph/`, not the plugin tree (cursor-review Major) — see Approach.
3. **Direct-shebang `.py` by path** → a bash wrapper: `hooks.json` (5 sites → `ralph-guard.py`) + `ralph.sh` (4 pipe sites → `watch-filter.py`).
4. **Agent-run heredocs** in qa/prospect workflow.md → resolve `$PY` once.
Then regenerate the Codex mirror via `sync-codex.sh`.

**Size:** M/L (mechanical, broad)
**Files:** 11 `plugins/flow-next/scripts/*_smoke*.sh`/`ci_test.sh`, `.../templates/ralph.sh`, `plugins/flow-next/hooks/hooks.json`, `plugins/flow-next/scripts/hooks/ralph-guard` (new bash wrapper, source of the install copy), `flow-next-qa/workflow.md`, `flow-next-prospect/workflow.md`, `plugins/flow-next/codex/**` (generated)

## Approach
- **Scalar→array conversion (plan-review Major):** in the 11 plugin-tree consumers, replace the `pick_python` def+assign with `source "$SCRIPT_DIR/lib/pick-python.sh"`, then rewrite EVERY `"$PYTHON_BIN"` call-site to `"${FLOW_PY[@]}"`. `set -u`-safe.
- **`ralph.sh` resolver path (cursor-review Major):** `ralph.sh` is a template installed to `scripts/ralph/ralph.sh`, where ralph-init (task .2) placed the resolver at `scripts/ralph/pick-python.sh` (FLAT). So `ralph.sh` sources `"$SCRIPT_DIR/pick-python.sh"` for the installed layout, with a source-tree fallback (`"$SCRIPT_DIR/../../../scripts/lib/pick-python.sh"` — templates→ralph-init→skills→flow-next, then scripts/lib; cursor-review Minor: NOT `../../`) for direct template execution — it must NOT hard-code `scripts/lib/`. Then regenerate its `ensure_flowctl_wrapper()` to source the resolver and `exec "${FLOW_PY[@]}"` (drop the scalar `PY="${PYTHON_BIN:-python3}"` that loses `-3`), and change the 4 `watch-filter.py` pipes to `"${FLOW_PY[@]}" "$SCRIPT_DIR/watch-filter.py"`.
- **hooks wrapper (plan-review + cursor-review Major, scoped):** add a bash wrapper `scripts/ralph/hooks/ralph-guard` (source under `plugins/flow-next/scripts/hooks/ralph-guard`, copied by ralph-init) — bash shebang; resolves `pick-python.sh` in BOTH layouts (installed `$SCRIPT_DIR/../pick-python.sh` [scripts/ralph/hooks→scripts/ralph] and source-tree `$SCRIPT_DIR/../lib/pick-python.sh` [scripts/hooks→scripts/lib; cursor-review Major: NOT `../../lib`]); `exec "${FLOW_PY[@]}" "$(dirname "$0")/ralph-guard.py" "$@"`. Change the 5 `hooks.json` sites (10/20/32/43/54) but **PRESERVE the not-installed no-op guard** (cursor-review Major): `[ ! -f scripts/ralph/hooks/ralph-guard ] || bash scripts/ralph/hooks/ralph-guard` — a bare `bash …` would break every non-Ralph repo where ralph-init never produced the wrapper. **Ralph mode requires Git Bash on Windows** (the harness is bash) — no native `.cmd` hook; document + test.
- **heredocs:** qa:521, prospect:63/490/740 — resolve `$PY` once; update `:16`/`:485` prose.
- **Orphan `.sh` hooks** (`ralph-guard.sh:9`, etc.): ZERO runtime refs — delete if dead, else fix. Record the decision.
- Run `scripts/sync-codex.sh`; commit the regenerated mirror.

## Investigation targets
**Required:**
- repo-scout's 12-copy table (def+assign) — **11 in `plugins/flow-next/scripts/`; `ralph.sh` handled separately (installed layout)**
- each consumer's `"$PYTHON_BIN"` CALL-sites (grep per file) → `"${FLOW_PY[@]}"`
- `plugins/flow-next/hooks/hooks.json:10,20,32,43,54` + `plugins/flow-next/scripts/hooks/ralph-guard.py:1`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:57-72` (wrapper) + `:1096,1098,1107,1109` (pipes) + `:25` — and confirm the installed `$SCRIPT_DIR` resolver path
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md` — confirm ralph-init copies `pick-python.sh` + the hook wrapper into `scripts/ralph/` (task .2)
- `flow-next-qa/workflow.md:521,485` · `flow-next-prospect/workflow.md:63,490,740,16`
- `plugins/flow-next/scripts/sync-codex.sh`

## Acceptance
- [ ] All 11 plugin-tree consumers source `scripts/lib/pick-python.sh` AND every `"$PYTHON_BIN"` call-site becomes `"${FLOW_PY[@]}"`; each passes `set -euo pipefail`, green on mac/linux, AND passes under a forced fake `py -3` resolution
- [ ] `ralph.sh` sources the resolver via the INSTALLED path `$SCRIPT_DIR/pick-python.sh` (source-tree fallback), NOT `scripts/lib/`; its generated wrapper + the 4 `watch-filter.py` pipes exec `"${FLOW_PY[@]}"`; verified in an installed `scripts/ralph/` layout
- [ ] Bash hook wrapper `scripts/ralph/hooks/ralph-guard` resolves `pick-python.sh` in both layouts (installed `../pick-python.sh`, source `../lib/pick-python.sh`); `hooks.json`'s 5 sites keep the not-installed no-op guard: `[ ! -f scripts/ralph/hooks/ralph-guard ] || bash scripts/ralph/hooks/ralph-guard` (a non-Ralph repo still no-ops cleanly); fires on a stub-configured Git-Bash Windows box; "Ralph requires Git Bash on Windows" documented
- [ ] qa + prospect heredocs resolve `$PY` once; no bare `python3 -` remains in either workflow.md
- [ ] The 3 orphan `.sh` hooks are fixed or removed (decision recorded)
- [ ] `sync-codex.sh` re-run; codex mirror reflects changes (no hand-edits)
- [ ] A targeted grep for EXECUTABLE `python3` invocations (line-start / after `|`/`(`/`$(`; excluding prose/comments/`#!`/prereq text) finds no unfixed site in the canonical tree

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
