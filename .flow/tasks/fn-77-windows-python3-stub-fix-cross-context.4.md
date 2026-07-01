---
satisfies: [R1, R5, R6]
---

## Description
Sweep the remaining bare-`python3` invocation sites the launcher fix doesn't reach, and de-duplicate the 12 copy-pasted `pick_python` bodies. Three site classes:
1. **12 `pick_python` copies** (11 smoke/CI test scripts + the runtime `ralph.sh` template) → `source` the shared `scripts/lib/pick-python.sh` from task .1 instead of redefining.
2. **Direct-shebang `.py` executed by path** (a bash launcher can't save these) → invoke through a resolved interpreter: `hooks.json` (5 sites → `ralph-guard.py`) and `ralph.sh` (4 pipe sites → `watch-filter.py`).
3. **Agent-run heredocs** in `flow-next-qa/workflow.md` + `flow-next-prospect/workflow.md` → resolve `$PY` once, invoke `$PY - <<'PY'`.
Then **regenerate the Codex mirror** via `sync-codex.sh` (never hand-edit `plugins/flow-next/codex/**`).

**Size:** M (mechanical but broad — low logical risk, uniform edits)
**Files:** 11 `plugins/flow-next/scripts/*_smoke*.sh`/`ci_test.sh`, `.../templates/ralph.sh`, `plugins/flow-next/hooks/hooks.json`, `flow-next-qa/workflow.md`, `flow-next-prospect/workflow.md`, `plugins/flow-next/codex/**` (generated), possibly `scripts/hooks/ralph-*.sh`

## Approach
- **Sourcing:** each `*.sh` has `set -euo pipefail` before its `pick_python` def (repo-scout table) — replace the def+assign with a `source "$SCRIPT_DIR/lib/pick-python.sh"` (path relative to each script's own dir) that stays `set -u`-safe. Confirm the relative path resolves from `scripts/` and from `templates/` (ralph.sh).
- **hooks.json:** the 5 invocations are `[ ! -f … ] || scripts/ralph/hooks/ralph-guard.py` (lines 10,20,32,43,54) — route through an interpreter (resolve once; a `PYTHON_BIN`/`py -3` prefix) rather than the bare `.py` path. Keep the shebang for POSIX direct-exec but don't RELY on it on Windows.
- **ralph.sh pipes (1096,1098,1107,1109):** `"$PYTHON_BIN" "$SCRIPT_DIR/watch-filter.py"` (PYTHON_BIN already exported at ralph.sh:25).
- **heredocs:** qa:521, prospect:63/490/740 — resolve `$PY` once near the top of each bash block; also update the `:16`/`:485` prose that says "python3".
- **Open question (decide in this task):** the 3 orphan `.sh` hooks (`ralph-guard.sh:9`, `ralph-receipt-guard.sh:17`, `ralph-verbose-log.sh:21`) have ZERO runtime refs (repo-scout) — fix for completeness or delete. Lean: delete if truly dead, else fix.
- Run `scripts/sync-codex.sh` and commit the regenerated mirror in the same task.

## Investigation targets
**Required:**
- repo-scout's 12-copy table (each `pick_python` def+assign line) — `smoke_test.sh:22/31`, `ci_test.sh:10/19`, `alias_smoke.sh:47/56`, `migration_smoke.sh:48/57`, `ralph_smoke_test.sh:14/23`, `make-pr_smoke_test.sh:64/73`, `audit_smoke_test.sh:33/42`, `glossary_smoke_test.sh:61/70`, `impl-review_smoke_test.sh:17/26`, `prospect_smoke_test.sh:44/53`, `strategy_smoke_test.sh:65/74`, `ralph.sh:14/23`
- `plugins/flow-next/hooks/hooks.json:10,20,32,43,54`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:1096,1098,1107,1109` + `:25` (PYTHON_BIN export)
- `flow-next-qa/workflow.md:521,485` · `flow-next-prospect/workflow.md:63,490,740,16`
- `plugins/flow-next/scripts/sync-codex.sh` — regeneration command

## Acceptance
- [ ] All 12 `pick_python` copies source `scripts/lib/pick-python.sh`; each script still passes `set -euo pipefail` and runs green on mac/linux
- [ ] `hooks.json` invokes `ralph-guard.py` through a resolved interpreter (not bare `.py` path); Ralph hooks fire on a stub-configured Windows box
- [ ] `ralph.sh` pipes to `watch-filter.py` as `"$PYTHON_BIN" watch-filter.py`
- [ ] qa + prospect heredocs resolve `$PY` once; no bare `python3 -` remains in either workflow.md
- [ ] The 3 orphan `.sh` hooks are fixed or removed (decision recorded)
- [ ] `sync-codex.sh` re-run; the codex mirror reflects the changes (no hand-edits)
- [ ] `grep -rn "python3" plugins/flow-next --include='*.sh'` shows no bare unfixed invocation in the canonical tree

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
