# fn-22-53k.3 flowctl: codex completion-review command

## Description

Add `flowctl codex completion-review` command for Codex backend integration.

**Command:**
```bash
flowctl codex completion-review fn-N [--receipt path] [--json]
```

**Implementation in `flowctl.py`:**

Follow `cmd_codex_impl_review()` pattern:

1. **Build prompt** with:
   - Epic spec content
   - All task specs for epic
   - Changed files (git diff)
   - Two-phase instruction: extract requirements, then verify coverage

2. **Call Codex** via existing `run_codex()` helper

3. **Parse verdict** from response: `SHIP` or `NEEDS_WORK`

4. **Write receipt** if `--receipt` provided:
   ```json
   {
     "type": "completion_review",
     "id": "fn-N",
     "mode": "codex",
     "timestamp": "...",
     "verdict": "SHIP|NEEDS_WORK"
   }
   ```

**Pattern reference:** `cmd_codex_impl_review()` and `cmd_codex_plan_review()` in flowctl.py

## Acceptance

- [ ] `flowctl codex completion-review fn-N` runs Codex review
- [ ] `--receipt path` writes receipt JSON with verdict
- [ ] Receipt includes `type: "completion_review"`
- [ ] Output includes verdict tag `<verdict>SHIP|NEEDS_WORK</verdict>`

## Done summary
Added `flowctl codex completion-review` command with two-phase prompt (extract requirements, verify coverage), receipt schema with type: "completion_review", and session continuity support.
## Evidence
- Commits: 9997b95, 2536786
- Tests: flowctl codex completion-review --help, flowctl codex completion-review fn-22-53k --json
- PRs: