# fn-30-memory-schema-upgrade.5 Ralph worker auto-capture rewrite + memory-scout category awareness

## Description

Update the Ralph auto-capture flow and the memory-scout agent to use the new categorized memory schema.

**Size:** S-M

**Files:**
- `plugins/flow-next/agents/worker.md` — NEEDS_WORK auto-capture section rewrite
- `plugins/flow-next/agents/memory-scout.md` — read categorized tree, return track/category-aware results
- `plugins/flow-next/skills/flow-next-ralph-init/templates/**` (if capture logic lives in Ralph templates rather than worker)
- Verify with `plugins/flow-next/scripts/ralph_smoke_test.sh`

## Worker agent changes

Locate the NEEDS_WORK auto-capture section in `worker.md`. Today it says (approximately):

> After a successful fix from NEEDS_WORK, append a brief pitfall entry to `.flow/memory/pitfalls.md`.

Rewrite to:

```markdown
## Auto-capture on successful fix (after NEEDS_WORK → SHIP)

When a fix cycle transitions NEEDS_WORK → SHIP, optionally capture the learning as a structured bug-track memory entry. Skip capture when:
- Review was trivial (triage-skip)
- Fix was mechanical (lockfile, typo)
- Same fingerprint captured in this session already

Otherwise, run:

\`\`\`bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"

$FLOWCTL memory add \
  --track bug \
  --category <inferred> \
  --title "<one-line summary>" \
  --module "<primary-affected-file-or-module>" \
  --tags "<tag1>,<tag2>" \
  --problem-type <one-of: build-error|test-failure|runtime-error|performance|security|integration|data|ui> \
  --symptoms "<what went wrong>" \
  --root-cause "<what caused it>" \
  --resolution-type fix \
  --body-file /tmp/memory-body.md
\`\`\`

Where `/tmp/memory-body.md` contains structured markdown with Problem / What Didn't Work / Solution / Prevention sections.

The overlap-detection in `memory add` handles duplicates automatically — if this pattern has been captured before, the existing entry is updated instead of a new one being created. No deduplication burden on the worker.

### Inferring category

Use the review's primary issue category:
- "build failed, import missing" → `build-errors`
- "test suite failures" → `test-failures`
- "null dereference, wrong value" → `runtime-errors`
- "N+1 query, slow request" → `performance`
- "auth bypass, SQL injection" → `security`
- "API contract mismatch, schema drift" → `integration`
- "data corruption, partial write" → `data`
- "layout broken, wrong color" → `ui`

When ambiguous, pick the most specific that fits; overlap detection will merge if similar past entries exist.
```

## memory-scout agent changes

Current memory-scout reads flat files. Update to:

1. Walk `.flow/memory/` tree first (new schema)
2. Read legacy flat files if present
3. Return results with track/category context

In the scout's output format, add category column:

```markdown
## Memory findings

| Track | Category | Entry | Relevance |
|-------|----------|-------|-----------|
| bug | runtime-errors | null-deref-in-auth-2026-05-01 | High (same module) |
| knowledge | conventions | prefer-satisfies-2026-05-02 | Medium (related pattern) |
| legacy | (pitfalls.md) | entry #2 | Medium |
```

Scout prompt guidance:
- Prefer new-schema entries over legacy when both match (newer format likely more current)
- Filter by task context: if task touches `src/auth.ts`, prioritize entries with `module: src/auth.ts*`
- Return compact summaries (title + one-sentence why-relevant), not full entry bodies

## Ralph template sync

If the Ralph `ralph.sh` template or any per-iteration script directly invokes memory commands, update those invocations. Test via:

```bash
plugins/flow-next/scripts/ralph_smoke_test.sh
```

Verify a synthetic NEEDS_WORK → SHIP cycle produces a valid new-schema entry.

## Acceptance

- **AC1:** Worker agent prompt references new `memory add --track bug --category X` form.
- **AC2:** Worker prompt includes the category inference rubric (symptom → category mapping).
- **AC3:** Worker prompt documents skip conditions (triage-skip, trivial fix, session duplicate).
- **AC4:** memory-scout reads both new tree and legacy flat files.
- **AC5:** memory-scout output includes track/category metadata in table format.
- **AC6:** Ralph smoke test produces a valid new-schema entry on NEEDS_WORK → SHIP.
- **AC7:** Scout output prioritizes entries with matching `module` over generic matches.

## Dependencies

- fn-30-memory-schema-upgrade.2 (memory add with new schema)
- fn-30-memory-schema-upgrade.3 (memory list/read/search)

## Done summary
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
