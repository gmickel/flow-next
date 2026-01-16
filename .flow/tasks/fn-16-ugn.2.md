# fn-16-ugn.2 Update plan-sync agent for dry-run support

## Overview

Update the existing plan-sync agent to support a `DRY_RUN` mode where it reports proposed changes without actually editing files.

## Context

- Agent file: `plugins/flow-next/agents/plan-sync.md`
- This agent is spawned by both:
  - `/flow-next:work` (auto-trigger in phases.md step 3e)
  - `/flow-next:sync` (new manual trigger from fn-16-ugn.1)

## Changes Required

### 1. Add DRY_RUN Input

In the "Input from prompt" section, add:
```markdown
- `DRY_RUN` - "true" or "false" (optional, defaults to false)
```

### 2. Modify Phase 5 (Update Affected Tasks)

Current behavior edits files unconditionally. Add dry-run handling:

```markdown
## Phase 5: Update Affected Tasks

**If DRY_RUN is "true":**
Report what would be changed without using Edit tool:

```
Would update:
- fn-1.3: Change `UserAuth.login()` → `authService.authenticate()`
- fn-1.5: Change return type `boolean` → `AuthResult`
```

Do NOT use Edit tool. Skip to Phase 6.

**If DRY_RUN is "false" or not set:**
For each affected downstream task, edit only the stale references:
[...existing edit logic...]
```

### 3. Modify Phase 6 (Return Summary)

Update the summary format to indicate dry-run mode:

```markdown
## Phase 6: Return Summary

**If DRY_RUN:**
```
Drift detected: yes
- fn-1.2 used `authService` singleton instead of `UserAuth` class

Would update (DRY RUN):
- fn-1.3: Change references from `UserAuth.login()` to `authService.authenticate()`
- fn-1.4: Update expected return type from `boolean` to `AuthResult`

No files modified.
```

**If not DRY_RUN:**
[...existing summary format...]
```

## Key Points

- Don't break existing auto-trigger behavior (DRY_RUN defaults to false)
- Dry-run should still do full analysis (phases 1-4)
- Only phase 5 (Edit) and phase 6 (summary) change behavior
- Keep the same detailed reporting in dry-run mode

## Acceptance

- [ ] `DRY_RUN=true` prevents Edit tool usage
- [ ] `DRY_RUN=true` reports proposed changes clearly
- [ ] `DRY_RUN=false` or missing works exactly as before (no regression)
- [ ] Summary clearly indicates dry-run mode when active

## Done summary
Added DRY_RUN parameter to plan-sync agent. Phase 5 skips Edit tool when dry-run, Phase 6 shows "Would update (DRY RUN)" format with "No files modified" footer.
## Evidence
- Commits: 05e024af578e2d4200923574083e74e56813876b
- Tests: smoke_test.sh
- PRs:
## References

- Agent file: `plugins/flow-next/agents/plan-sync.md`
- Epic spec: `.flow/specs/fn-16-ugn.md`
