# fn-25-prompt-quality-improvements-for-flow.2 Worker: pre-implementation investigation, similar-func search, typed escalation

## Description
Add three behaviors to the worker agent prompt: read investigation targets before implementing, search for similar functionality, and use typed escalation when blocking.

**Size:** M
**Files:** `plugins/flow-next/agents/worker.md`

## Pre-implementation investigation (new Phase 1.5)

Insert between Phase 1 (Re-anchor) and Phase 2 (Implement). After re-anchor reads the task spec, the worker must:

1. **Read investigation targets** — if the task spec has `## Investigation targets`, Read every Required file before coding. Optional files read as needed during implementation.

2. **Record observations** — brief notes on what was found (patterns to follow, constraints discovered). These don't need to be persisted — they're just working notes for the implementation phase.

Add after line 58 (end of Phase 1) and before line 60 (Phase 2):

```markdown
## Phase 1.5: Pre-implementation Investigation

**If the task spec contains `## Investigation targets`:**

1. Read every **Required** file listed. Note:
   - Patterns to follow (function signatures, naming, structure)
   - Constraints discovered (validation rules, type contracts, env requirements)
   - Anything surprising that might affect your approach

2. **Similar functionality search** — before writing new code:
   ```bash
   # Search for functions/modules that do similar things
   # Use terms from the task description + acceptance criteria
   grep -r "<key domain term>" --include="*.ts" --include="*.py" -l src/
   ```
   If similar functionality exists:
   - **Reuse**: Use the existing code directly
   - **Extend**: Modify existing code to support the new case
   - **New**: Create new code (justify why existing isn't suitable)
   
   Report what you found:
   ```
   Similar code search:
   - Found: `validateEmail()` in src/utils/validation.ts:23 — reusing
   - Found: `src/routes/users.ts:45` — following this pattern
   - No existing rate limiter found — creating new
   ```

3. Continue to Phase 2 only after investigation is complete.
```

## Typed escalation (update Rules section)

Update the worker's blocking behavior. Currently worker.md has no guidance on how to structure block messages. Add to the Rules section (line 164+):

```markdown
- **Typed escalation** — when blocking a task, use this format:
  ```
  BLOCKED: <category>
  Task: <TASK_ID>
  Summary: <one line>
  Impact: <what downstream tasks are delayed>
  Suggested resolution: <actionable next step>
  ```
  Categories (use exactly one):
  - `SPEC_UNCLEAR` — requirement is ambiguous, can't proceed without clarification
  - `DEPENDENCY_BLOCKED` — waiting on another task, PR, or service
  - `DESIGN_CONFLICT` — implementation conflicts with existing architecture
  - `SCOPE_EXCEEDED` — task is larger than estimated, needs splitting
  - `TOOLING_FAILURE` — build/test/infra broken, not a code issue
  - `EXTERNAL_BLOCKED` — waiting on external API, key, or approval
```

## Key context

- Worker is at `plugins/flow-next/agents/worker.md` (172 lines)
- Phase 1 ends at line 58, Phase 2 starts at line 60
- Rules section is at lines 164-172
- Worker already parses "technical approach hints" informally in Phase 1 — investigation targets make this structured
- flowctl stores `blocked_reason` as freeform text — typed format is just prose structure, no schema change
- Ralph mode: worker is spawned identically, new phases are additive, no changed commands
## Acceptance
- [ ] Phase 1.5 added between Phase 1 and Phase 2 in worker.md
- [ ] Worker reads Required investigation targets before implementing
- [ ] Worker searches for similar functionality and reports findings
- [ ] Worker uses decision tree: reuse > extend > new (with justification)
- [ ] Typed escalation format documented in Rules section
- [ ] All 6 escalation categories defined with clear criteria
- [ ] No changes to flowctl commands (flowctl done, flowctl show, etc.)
- [ ] Phase numbering consistent (1 → 1.5 → 2 → 3 → 4 → 5 → 6)
- [ ] Ralph mode unaffected (worker still spawned same way, same env vars)
## Done summary
Added Phase 1.5 (pre-implementation investigation with required/optional file reads + similar-func search with reuse>extend>new decision tree) and typed escalation (6 categories) to worker.md Rules section.
## Evidence
- Commits: caa2108aec7d50010957c0251ffaa165a5609746
- Tests:
- PRs: